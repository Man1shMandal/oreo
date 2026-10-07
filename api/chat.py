"""A small authenticated chat endpoint for the hosted OREO v1."""

import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler

from openai import OpenAI


SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")


def request_json(url, headers, method="GET", data=None):
    request = urllib.request.Request(url, headers=headers, method=method, data=data)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


class handler(BaseHTTPRequestHandler):
    def reply(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            message = str(payload.get("message", "")).strip()
            if not message or len(message) > 6000:
                self.reply(400, {"error": "Send a message under 6,000 characters."})
                return

            token = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            if not token:
                self.reply(401, {"error": "Please sign in."})
                return

            publishable_key = os.environ["SUPABASE_PUBLISHABLE_KEY"]
            user = request_json(
                f"{SUPABASE_URL}/auth/v1/user",
                {"apikey": publishable_key, "Authorization": f"Bearer {token}"},
            )
            service_key = os.environ["SUPABASE_SECRET_KEY"]
            profiles = request_json(
                f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user['id']}&select=approved",
                {"apikey": service_key, "Authorization": f"Bearer {service_key}"},
            )
            if not profiles or not profiles[0]["approved"]:
                self.reply(403, {"error": "Your account is waiting for approval."})
                return

            client = OpenAI(api_key=os.environ["ABBY_API_KEY"], base_url="https://api.abby.abb.com/api/v1/developers")
            completion = client.chat.completions.create(
                model="claude-4.5-haiku",
                messages=[
                    {"role": "system", "content": "You are Oreo, Manish's personal AI. Be brief, direct, and useful. No emoji."},
                    {"role": "user", "content": message},
                ],
                max_tokens=700,
                temperature=0.7,
            )
            self.reply(200, {"reply": completion.choices[0].message.content or "No reply returned."})
        except urllib.error.HTTPError:
            self.reply(401, {"error": "Your sign-in has expired. Please sign in again."})
        except Exception:
            self.reply(500, {"error": "Oreo is unavailable right now. Try again shortly."})
