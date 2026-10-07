"""Route the hosted page and API through Vercel's Python entrypoint."""

from pathlib import Path
from urllib.parse import urlsplit

from api.chat import handler as ChatHandler
from api.config import handler as ConfigHandler
from api.health import handler as HealthHandler
from api.hosted import HostedHandler


class handler(ChatHandler, HostedHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/health":
            HealthHandler.do_GET(self)
        elif path == "/api/config":
            ConfigHandler.do_GET(self)
        elif path in ("/api/profile", "/api/conversations", "/api/admin"):
            self.hosted_GET(path)
        elif path == "/":
            body = (Path(__file__).resolve().parent.parent / "public" / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.reply(404, {"error": "Not found."})

    def do_POST(self):
        if urlsplit(self.path).path == "/api/chat":
            super().do_POST()
        elif urlsplit(self.path).path == "/api/admin":
            self.admin_POST()
        else:
            self.reply(404, {"error": "Not found."})
