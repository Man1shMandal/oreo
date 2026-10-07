"""Oreo in the browser: a small local server around the same provider, chats and settings."""

import json
import os
import re
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import config, files, settings, store
from .provider import Provider

PAGE = Path(__file__).with_name("web.html")
CHAT_ID = re.compile(r"^[\w-]+$")


class App:
    """State shared by all requests."""

    def __init__(self):
        self.settings = settings.load()
        key = os.environ.get("ABBY_API_KEY") or settings.get_key()
        self.provider = Provider(key) if key else None

    def system_prompt(self):
        s = config.PERSONA.replace("running in his terminal", "running in his browser")
        s += f"\nCurrent directory: {os.getcwd()}"
        if self.settings["instructions"]:
            s += f"\n\nStanding instructions from the user:\n{self.settings['instructions']}"
        return s


def chat_path(cid):
    if not CHAT_ID.match(cid or ""):
        raise ValueError("bad chat id")
    return store.DIR / f"{cid}.json"


class Handler(BaseHTTPRequestHandler):
    app = None
    port = 0

    def log_message(self, *a):
        pass

    # --- plumbing

    def local_only(self):
        """Block other websites from poking the local server (DNS rebinding, CSRF)."""
        ok_hosts = {f"127.0.0.1:{self.port}", f"localhost:{self.port}"}
        if self.headers.get("Host") not in ok_hosts:
            return False
        origin = self.headers.get("Origin")
        return origin is None or origin.split("//", 1)[-1] in ok_hosts

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
        if not self.local_only():
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
        self.send(200, {
            "models": config.MODELS,
            "settings": {k: st[k] for k in ("model", "temperature", "max_tokens", "instructions")},
            "has_key": self.app.provider is not None,
        })

    def get_chats(self, cid=None):
        if cid:
            c = store.Chat.load(chat_path(cid))
            return self.send(200, {"id": cid, "title": c.title, "messages": c.messages})
        chats = store.recent(50)
        self.send(200, [{"id": c.path.stem, "title": c.title} for c in chats])

    def delete_chats(self, cid):
        chat_path(cid).unlink(missing_ok=True)
        self.send(200, {"ok": True})

    def post_settings(self):
        b, st = self.body(), self.app.settings
        if b.get("model") in config.MODELS.values():
            st["model"] = b["model"]
        if "temperature" in b:
            st["temperature"] = min(2.0, max(0.0, float(b["temperature"])))
        if "max_tokens" in b:
            st["max_tokens"] = max(64, int(b["max_tokens"]))
        if "instructions" in b:
            st["instructions"] = str(b["instructions"]).strip()
        settings.save(st)
        self.get_state()

    def post_key(self):
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
        if not self.app.provider:
            return self.send(400, {"error": "no API key yet"})
        try:
            self.send(200, self.app.provider.usage())
        except Exception as e:
            self.send(502, {"error": str(e)})

    def post_test(self):
        app = self.app
        if not app.provider:
            return self.send(400, {"error": "no API key yet"})
        try:
            app.provider.client.chat.completions.create(
                model=app.settings["model"], max_tokens=5,
                messages=[{"role": "user", "content": "hi"}])
            d = app.provider.usage()
            self.send(200, {"ok": True, "message": f"connected · {d['percentage']} of monthly tokens used"})
        except Exception as e:
            self.send(502, {"error": str(e)})

    def post_chat(self):
        """Stream a reply as server-sent events: {chat}, then {text}..., then {done} or {error}."""
        app, b = self.app, self.body()
        if not app.provider:
            return self.send(400, {"error": "no API key yet"})
        chat = store.Chat.load(chat_path(b["id"])) if b.get("id") else store.Chat()
        model = b.get("model") or app.settings["model"]
        text, attached, errors = files.expand(str(b.get("text", "")))
        chat.messages.append({"role": "user", "content": text})
        chat.save()

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        def event(d):
            self.wfile.write(f"data: {json.dumps(d)}\n\n".encode())
            self.wfile.flush()

        reply = ""
        try:
            event({"chat": chat.path.stem, "title": chat.title, "attached": attached, "errors": errors})
            params = {k: app.settings[k] for k in config.DEFAULTS}
            msgs = [{"role": "system", "content": app.system_prompt()}] + chat.messages
            for piece in app.provider.stream(model, msgs, **params):
                reply += piece
                event({"text": piece})
            chat.messages.append({"role": "assistant", "content": reply})
            chat.save()
            event({"done": app.provider.last_model})
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


    @staticmethod
    def drop_last(chat):
        chat.messages.pop()
        if chat.messages:
            chat.save()
        else:
            chat.path.unlink(missing_ok=True)


def main(argv=()):
    port = next((int(a) for a in argv if a.isdigit()), 4747)
    Handler.app, Handler.port = App(), port
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"oreo web · {url} · Ctrl-C to stop")
    if "--no-open" not in argv:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
