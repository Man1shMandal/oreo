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
        elif path in ("/api/profile", "/api/conversations"):
            self.hosted_GET(path)
        elif path == "/oreo.svg":
            body = (Path(__file__).resolve().parent.parent / "oreo" / "logo.svg").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path in ("/chat.js", "/markdown.js", "/mascot.js", "/preferences.js", "/voice.js", "/sw.js", "/manifest.webmanifest", "/theme.css"):
            body = (Path(__file__).resolve().parent.parent / "public" / path[1:]).read_bytes()
            kind = ("application/manifest+json" if path.endswith(".webmanifest") else
                    "text/css; charset=utf-8" if path.endswith(".css") else
                    "text/javascript; charset=utf-8")
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path in ("/icon-192.png", "/icon-512.png", "/icon-maskable-512.png", "/apple-touch-icon.png"):
            body = (Path(__file__).resolve().parent.parent / "public" / path[1:]).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", "public, max-age=86400")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
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
        else:
            self.reply(404, {"error": "Not found."})


    def do_DELETE(self):
        if urlsplit(self.path).path == '/api/conversations':
            self.hosted_DELETE('/api/conversations')
        else:
            self.reply(404, {"error": "Not found."})
