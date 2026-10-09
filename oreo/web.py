"""Oreo in the browser, for anyone on the local network.

Visitors say who they are on first visit and get their own chats. Only the owner (a browser on
this Mac) can change settings or the key, see usage, attach files with @path, or open the
terminal's chats.
"""

import ipaddress
import json
import os
import queue
import re
import signal
import socket
import subprocess
import sys
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from . import attach, code_agent, config, files, lean, research, settings, store
from .provider import Provider

PAGE = Path(__file__).with_name("web.html")
MARKDOWN = PAGE.parents[1] / "public" / "markdown.js"
MASCOT = PAGE.parents[1] / "public" / "mascot.js"
PEOPLE = Path.home() / ".oreo" / "people"   # one chat folder per visitor
CHAT_ID = re.compile(r"^[\w-]+$")
UPLOAD = re.compile(r"^[0-9a-f]{24}\.(png|jpg|pdf)$")
NAME = "oreo.local"   # announced on the network with Bonjour


class App:
    """State shared by all requests."""

    def __init__(self, workspace=None):
        self.settings = settings.load()
        key = os.environ.get("ABBY_API_KEY") or settings.get_key()
        self.provider = Provider(key) if key else None
        self.agent_lock = threading.Lock()
        self.agent_pending = {}
        self.workspace = Path(workspace or Path.cwd()).expanduser().resolve(strict=True)
        if not self.workspace.is_dir():
            raise ValueError("The Code workspace must be an existing directory.")


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
        """A browser on this Mac, whether it came in via localhost or oreo.local (our own LAN address)."""
        ip = self.client_address[0]
        return ipaddress.ip_address(ip).is_loopback or ip == self.connection.getsockname()[0]

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
        if not port.isdigit():   # no port in the URL means 80
            hostname, port = host, "80"
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
            if method == "GET" and path == "/oreo.svg":
                return self.send(200, PAGE.with_name("logo.svg").read_bytes(), "image/svg+xml")
            if method == "GET" and path == "/markdown.js":
                return self.send(200, MARKDOWN.read_bytes(), "text/javascript; charset=utf-8")
            if method == "GET" and path == "/mascot.js":
                return self.send(200, MASCOT.read_bytes(), "text/javascript; charset=utf-8")
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
            **({"workspace": str(self.app.workspace)} if self.owner else {}),
        })

    def get_chats(self, cid=None):
        if cid:
            c = store.Chat.load(self.chat_path(cid))
            return self.send(200, {"id": cid, "title": c.title, "messages": c.messages})
        chats = store.recent(50, self.folder())
        self.send(200, [{"id": c.path.stem, "title": c.title} for c in chats])

    def get_uploads(self, name):
        if not UPLOAD.match(name):
            raise ValueError("bad file name")
        data = (self.folder() / "uploads" / name).read_bytes()
        self.send(200, data, {"png": "image/png", "jpg": "image/jpeg", "pdf": "application/pdf"}[name[-3:]])

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
        uploads = b.get("files") or []
        blocks, images, bad = attach.process(uploads, folder / "uploads")
        errors += bad
        if not chat.title:
            chat.title = (text.strip().splitlines() or [""])[0][:60] or ", ".join(u.get("name", "") for u in uploads)[:60]
        msg = {"role": "user", "content": lean.squeeze("\n\n".join([text.strip()] + blocks))}
        if images:
            msg["images"] = images
        if not msg["content"] and not images:
            return self.send(400, {"error": "; ".join(errors) or "empty message"})
        chat.messages.append(msg)
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
            event({"chat": chat.path.stem, "title": chat.title, "attached": attached, "errors": errors,
                   "images": images})
            params = {k: app.settings[k] for k in config.DEFAULTS}
            system = lean.system_prompt(app.settings, name=self.name, owner=self.owner)
            sources = self.research(chat, str(b.get("text", ""))) if b.get("web") else []
            if sources:
                event({"sources": [{"title": x["title"], "url": x["url"]} for x in sources]})
            msgs = lean.build(chat, system, app.settings["context"])
            if sources:   # pages go with this request only; the chat keeps just the links
                last = msgs[-1]["content"]
                web = research.block(sources)
                if isinstance(last, str):
                    msgs[-1]["content"] = last + web
                else:
                    last[0]["text"] += web
            if not isinstance(msgs[-1]["content"], str) and not model.startswith("claude"):
                model = config.VISION_MODEL   # only Claude can see pictures through the gateway
            for piece in lean.stream(app.provider, model, msgs, params, info):
                reply += piece
                event({"text": piece})
            answer = {"role": "assistant", "content": reply}
            if sources:
                answer["sources"] = [{"title": x["title"], "url": x["url"]} for x in sources]
            if not reply.strip():
                raise RuntimeError("the model sent back an empty reply, try again")
            chat.messages.append(answer)
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

    def post_agent(self):
        """Run a local coding-agent turn. Workspace access is limited to the owner."""
        self.need_owner()
        app, b = self.app, self.body()
        if not app.provider:
            return self.send(400, {"error": "Oreo isn't set up yet (no API key)"})
        text = str(b.get("text", "")).strip()
        if not text:
            return self.send(400, {"error": "Write a coding request."})
        folder = self.folder()
        chat = store.Chat.load(self.chat_path(b["id"])) if b.get("id") else store.Chat(folder=folder)
        if not chat.title:
            chat.title = text.splitlines()[0][:60]
        chat.messages.append({"role": "user", "content": text})
        chat.save()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        def event(payload):
            self.wfile.write(f"data: {json.dumps(payload)}\n\n".encode())
            self.wfile.flush()

        model = b.get("model") if b.get("model") in config.MODELS.values() else app.settings["model"]
        event({"chat": chat.path.stem, "title": chat.title})
        event({"status": "Reading project instructions…"})
        tool_text = "\n".join(f"- {name}: {doc}" for name, doc in code_agent.TOOL_DOCS.items())
        system = code_agent.GUIDE.format(root=str(app.workspace), tools=tool_text)
        try:
            system += "\n\nInitial project context:\n" + code_agent.project_context(app.workspace)
        except Exception:
            pass
        completed_tools = 0
        try:
            for step in range(16):
                history = chat.messages[-32:]
                # Keep recent context bounded while preserving whole messages.
                used, bounded = 0, []
                for row in reversed(history):
                    content = row["content"]
                    if used + len(content) > 60_000 and bounded:
                        break
                    bounded.append(row)
                    used += len(content)
                bounded.reverse()
                messages = [{"role": "system", "content": system}] + bounded
                raw, shown = "", 0
                event({"status": "Thinking…"})
                for piece in app.provider.stream(model, messages, max_tokens=4096, temperature=0.2):
                    raw += piece
                    visible, call = code_agent.parse_call(raw)
                    limit = len(visible) if call else code_agent.visible_length(raw)
                    if limit > shown:
                        event({"text": raw[shown:limit]})
                        shown = limit
                visible, call = code_agent.parse_call(raw)
                if not call:
                    if not raw.strip():
                        raise RuntimeError("The model sent back an empty reply. Try again shortly.")
                    chat.messages.append({"role": "assistant", "content": raw})
                    chat.save()
                    event({"done": lean.footer({}, messages, raw), "reply": raw, "conversation_id": chat.path.stem,
                           "model": app.provider.last_model})
                    return

                name, args = call
                summary = {key: args[key] for key in ("path", "destination", "command", "url") if key in args}
                event({"tool": {"name": name, "args": summary}})
                if name not in code_agent.TOOL_DOCS:
                    result = "Error: unknown tool. Use only one of the available project tools."
                else:
                    try:
                        plan = code_agent.execute(app.workspace, name, args)
                        if name in code_agent.WRITE_TOOLS:
                            approval_id = uuid.uuid4().hex
                            decision = queue.Queue(maxsize=1)
                            with app.agent_lock:
                                app.agent_pending[approval_id] = decision
                            preview = plan if isinstance(plan, dict) else {"result": str(plan)}
                            event({"approval": {"id": approval_id, "name": name, "args": summary,
                                                 "preview": preview}})
                            try:
                                accepted = decision.get(timeout=180)
                            except queue.Empty:
                                accepted = False
                            finally:
                                with app.agent_lock:
                                    app.agent_pending.pop(approval_id, None)
                            if accepted:
                                result = code_agent.apply(app.workspace, name, args)
                            else:
                                result = "The user declined this action. Do not retry it; continue with a safe alternative or ask what they prefer."
                        else:
                            result = plan
                    except Exception as error:
                        result = f"Error: {type(error).__name__}: {error}"
                # Keep tool requests and results in context, but only render normal prose.
                prefix = raw[:raw.find("</tool>") + len("</tool>")]
                chat.messages.append({"role": "assistant", "content": prefix})
                result_text = result.get("result", "") if isinstance(result, dict) else str(result)
                chat.messages.append({"role": "user", "content": f'<result tool="{name}">\n{result_text}\n</result>'})
                chat.save()
                completed_tools += 1
                event({"tool_result": {"name": name, "result": result_text[:1000]}})
                event({"status": "Using " + name.replace("_", " ") + "…"})
            raise RuntimeError("Stopped after 16 tool steps. Ask Oreo to continue.")
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as error:
            if not completed_tools and chat.messages and chat.messages[-1] == {"role": "user", "content": text}:
                chat.messages.pop()
                if chat.messages:
                    chat.save()
                else:
                    chat.path.unlink(missing_ok=True)
            try:
                event({"error": str(error)})
            except OSError:
                pass

    def post_agent_decision(self):
        self.need_owner()
        b = self.body()
        approval_id = str(b.get("id", ""))
        with self.app.agent_lock:
            decision = self.app.agent_pending.get(approval_id)
            if decision is None:
                return self.send(404, {"error": "That approval has expired."})
            try:
                decision.put_nowait(b.get("approved") is True)
            except queue.Full:
                return self.send(409, {"error": "That approval was already answered."})
        self.send(200, {"ok": True})

    def research(self, chat, text):
        """Search and read the web when the question needs it. Progress goes to the page as {status}."""
        step = lambda s: self.wfile.write(f"data: {json.dumps({'status': s})}\n\n".encode()) or self.wfile.flush()
        links = research.URL.findall(text)[:3]   # pasted links are read directly
        try:
            queries = [] if links else research.plan(self.app.provider, chat)
        except Exception:
            return []
        if not queries and not links:
            return []
        sources = research.gather(queries, links, research.keywords(text + " " + " ".join(queries)), step)
        step("writing")
        return sources

    @staticmethod
    def drop_last(chat):
        chat.messages.pop()
        if chat.messages:
            chat.save()
        else:
            chat.path.unlink(missing_ok=True)


def announce(port, ip):
    """Publish oreo.local on the network via Bonjour (macOS dns-sd), so nobody needs the IP."""
    try:
        return subprocess.Popen(["dns-sd", "-P", "Oreo", "_http._tcp", "local", str(port), NAME, ip],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return None


def main(argv=()):
    """Port 80 by default so the link is just http://oreo.local; falls back to 4747 if 80 is taken."""
    local = "--local" in argv
    asked = next((int(a) for a in argv if a.isdigit()), None)
    workspace = None
    for index, arg in enumerate(argv):
        if arg == "--workspace" and index + 1 < len(argv):
            workspace = argv[index + 1]
        elif arg.startswith("--workspace="):
            workspace = arg.split("=", 1)[1]
    for port in [asked] if asked else [80, 4747]:
        try:
            server = ThreadingHTTPServer(("127.0.0.1" if local else "0.0.0.0", port), Handler)
            break
        except OSError:
            if asked or port == 4747:
                raise
    Handler.app, Handler.port = App(workspace), port
    print(f"           Oreo Code workspace: {Handler.app.workspace}")
    suffix = "" if port == 80 else f":{port}"
    print(f"oreo web · on this Mac: http://localhost{suffix}")
    bonjour = None
    if not local:
        ip = lan_ip()
        bonjour = announce(port, ip) if ip else None
        print(f"           on your network: http://{NAME if bonjour else ip or socket.gethostname()}{suffix}")
        if ip:
            print(f"           (or http://{ip}{suffix} on devices that don't know .local names)")
    print("           Ctrl-C to stop")
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))   # so `kill` also runs the cleanup below
    if "--no-open" not in argv:
        webbrowser.open(f"http://localhost{suffix}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if bonjour:
            bonjour.terminate()
