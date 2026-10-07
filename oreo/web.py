"""Oreo in the browser, for anyone on the local network.

Visitors say who they are on first visit and get their own chats. Only the owner (a browser on
this Mac) can change settings or the key, see usage, attach files with @path, or open the
terminal's chats.
"""

import ipaddress
import json
import os
import re
import socket
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from . import config, files, lean, settings, store
from .provider import Provider

PAGE = Path(__file__).with_name("web.html")
PEOPLE = Path.home() / ".oreo" / "people"   # one chat folder per visitor
CHAT_ID = re.compile(r"^[\w-]+$")


class App:
    """State shared by all requests."""

    def __init__(self):
        self.settings = settings.load()
        key = os.environ.get("ABBY_API_KEY") or settings.get_key()
        self.provider = Provider(key) if key else None


def clean_name(raw):
    name = re.sub(r"[^\w .'-]", "", unquote(raw or "")).strip()
    return re.sub(r"\s+", " ", name)[:30]


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))   # picks the LAN interface; nothing is sent
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


class Handler(BaseHTTPRequestHandler):
    app = None
    port = 0

    def log_message(self, *a):
        pass

    # --- who is asking

    @property
    def owner(self):
        return ipaddress.ip_address(self.client_address[0]).is_loopback

    @property
    def name(self):
        return clean_name(self.headers.get("X-Oreo-User"))

    def folder(self):
        if self.owner:
            return store.DIR
        if not self.name:
            raise PermissionError("tell Oreo who you are first")
        slug = re.sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-") or "guest"
        return PEOPLE / slug

    def chat_path(self, cid):
        if not CHAT_ID.match(cid or ""):
            raise ValueError("bad chat id")
        return self.folder() / f"{cid}.json"

    def need_owner(self):
        if not self.owner:
            raise PermissionError("only available on Oreo's own computer")

    # --- plumbing

    def trusted(self):
        """Only answer to our own address (blocks DNS rebinding) and our own pages (blocks CSRF)."""
        host = self.headers.get("Host", "")
        hostname, _, port = host.rpartition(":")
        if port != str(self.port):
            return False
        hostname = hostname.strip("[]").lower()
        try:
            ipaddress.ip_address(hostname)
        except ValueError:
            if hostname not in ("localhost", socket.gethostname().lower()) and not hostname.endswith(".local"):
                return False
        origin = self.headers.get("Origin")
        return origin is None or origin.split("//", 1)[-1] == host

    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def body(self):
        if self.headers.get("Content-Type") != "application/json":
            raise ValueError("expected JSON")
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def route(self, method):
        if not self.trusted():
            return self.send(403, {"error": "forbidden"})
        path = self.path.split("?")[0].rstrip("/") or "/"
        parts = path.strip("/").split("/")
        try:
            if method == "GET" and path == "/":
                return self.send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            if parts[0] != "api" or len(parts) < 2:
                return self.send(404, {"error": "not found"})
            fn = getattr(self, f"{method.lower()}_{parts[1]}", None)
            if not fn:
                return self.send(404, {"error": "not found"})
            return fn(*parts[2:])
        except PermissionError as e:
            return self.send(403, {"error": str(e)})
        except (ValueError, TypeError, FileNotFoundError) as e:
            return self.send(400, {"error": str(e)})

    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")

    def do_DELETE(self):
        self.route("DELETE")

    # --- api

    def get_state(self):
        st = self.app.settings
        keys = ("model", "temperature", "max_tokens", "context", "instructions") if self.owner else ("model",)
        self.send(200, {
            "models": config.MODELS,
            "settings": {k: st[k] for k in keys},
            "has_key": self.app.provider is not None,
            "owner": self.owner,
        })

    def get_chats(self, cid=None):
        if cid:
            c = store.Chat.load(self.chat_path(cid))
            return self.send(200, {"id": cid, "title": c.title, "messages": c.messages})
        chats = store.recent(50, self.folder())
        self.send(200, [{"id": c.path.stem, "title": c.title} for c in chats])

    def delete_chats(self, cid):
        self.chat_path(cid).unlink(missing_ok=True)
        self.send(200, {"ok": True})

    def post_settings(self):
        self.need_owner()
        b, st = self.body(), self.app.settings
        if b.get("model") in config.MODELS.values():
            st["model"] = b["model"]
        if "temperature" in b:
            st["temperature"] = min(2.0, max(0.0, float(b["temperature"])))
        if "max_tokens" in b:
            st["max_tokens"] = max(64, int(b["max_tokens"]))
        if "context" in b:
            st["context"] = max(200, int(b["context"]))
        if "instructions" in b:
            st["instructions"] = str(b["instructions"]).strip()
        settings.save(st)
        self.get_state()

    def post_key(self):
        self.need_owner()
        key = str(self.body().get("key", "")).strip()
        if not key.startswith("sk-"):
            return self.send(400, {"error": "that doesn't look right — the key starts with sk-"})
        settings.set_key(key)
        if self.app.provider:
            self.app.provider.set_key(key)
        else:
            self.app.provider = Provider(key)
        self.send(200, {"ok": True})

    def get_usage(self):
        self.need_owner()
        if not self.app.provider:
            return self.send(400, {"error": "no API key yet"})
        try:
            self.send(200, self.app.provider.usage())
        except Exception as e:
            self.send(502, {"error": str(e)})

    def post_test(self):
        self.need_owner()
        app = self.app
        if not app.provider:
            return self.send(400, {"error": "no API key yet"})
        try:
            app.provider.client.chat.completions.create(
                model=app.settings["model"], max_tokens=1,
                messages=[{"role": "user", "content": "hi"}])
            d = app.provider.usage()
            self.send(200, {"ok": True, "message": f"connected · {d['percentage']} of monthly tokens used"})
        except Exception as e:
            self.send(502, {"error": str(e)})

    def post_chat(self):
        """Stream a reply as server-sent events: {chat}, then {text}..., then {done} or {error}."""
        app, b = self.app, self.body()
        if not app.provider:
            return self.send(400, {"error": "Oreo isn't set up yet (no API key)"})
        folder = self.folder()
        chat = store.Chat.load(self.chat_path(b["id"])) if b.get("id") else store.Chat(folder=folder)
        model = b.get("model") if b.get("model") in config.MODELS.values() else app.settings["model"]
        text, attached, errors = str(b.get("text", "")), [], []
        if self.owner:   # @path reads files on this Mac, so only the owner gets it
            text, attached, errors = files.expand(text)
        chat.messages.append({"role": "user", "content": lean.squeeze(text)})
        chat.save()

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        def event(d):
            self.wfile.write(f"data: {json.dumps(d)}\n\n".encode())
            self.wfile.flush()

        reply, info = "", {}
        try:
            event({"chat": chat.path.stem, "title": chat.title, "attached": attached, "errors": errors})
            params = {k: app.settings[k] for k in config.DEFAULTS}
            system = lean.system_prompt(app.settings, name=self.name, owner=self.owner)
            msgs = lean.build(chat, system, app.settings["context"])
            for piece in lean.stream(app.provider, model, msgs, params, info):
                reply += piece
                event({"text": piece})
            chat.messages.append({"role": "assistant", "content": reply})
            chat.save()
            event({"done": lean.footer(info, msgs, reply)})
        except (BrokenPipeError, ConnectionResetError):
            # user hit Stop: keep what arrived
            if reply:
                chat.messages.append({"role": "assistant", "content": reply})
            else:
                self.drop_last(chat)
            chat.save()
        except Exception as e:
            self.drop_last(chat)
            try:
                event({"error": str(e)})
            except OSError:
                pass
            return
        # fold old turns into a summary once they no longer fit the memory budget
        if reply and lean.needs_compact(chat, app.settings["context"]):
            try:
                lean.compact(app.provider, chat)
                chat.save()
            except Exception:
                pass  # next message just sends a shorter window

    @staticmethod
    def drop_last(chat):
        chat.messages.pop()
        if chat.messages:
            chat.save()
        else:
            chat.path.unlink(missing_ok=True)


def main(argv=()):
    port = next((int(a) for a in argv if a.isdigit()), 4747)
    local = "--local" in argv
    Handler.app, Handler.port = App(), port
    server = ThreadingHTTPServer(("127.0.0.1" if local else "0.0.0.0", port), Handler)
    print(f"oreo web · on this Mac: http://127.0.0.1:{port}")
    if not local:
        ip = lan_ip()
        print(f"           on your network: http://{ip or socket.gethostname()}:{port}")
    print("           Ctrl-C to stop")
    if "--no-open" not in argv:
        webbrowser.open(f"http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
