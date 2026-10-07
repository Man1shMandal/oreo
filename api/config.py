"""Public configuration required by the hosted OREO browser client."""

import json
import os
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps(
            {
                "supabaseUrl": os.environ.get("SUPABASE_URL", ""),
                "supabasePublishableKey": os.environ.get("SUPABASE_PUBLISHABLE_KEY", ""),
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "public, max-age=300")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
