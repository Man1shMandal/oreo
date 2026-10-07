"""A small authenticated chat endpoint for the hosted OREO v1."""

import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler

from openai import OpenAI

from api.conversations import MAX_OUTPUT, conversation_id, prepare, save_turn, acquire, release


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
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        lease = None
        user_id = None
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 30000:
                self.reply(400, {"error": "Send a valid message under 6,000 characters."})
                return
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict) or not isinstance(payload.get("message"), str):
                self.reply(400, {"error": "Send a text message."})
                return
            message = payload["message"].strip()
            try:
                chat_id = conversation_id(payload.get("conversation_id"))
            except (ValueError, TypeError, AttributeError):
                self.reply(400, {"error": "Send a valid conversation ID."})
                return
            if not message or len(message) > 6000:
                self.reply(400, {"error": "Send a message under 6,000 characters."})
                return

            token = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            if not token:
                self.reply(401, {"error": "Please sign in."})
                return

            publishable_key = os.environ["SUPABASE_PUBLISHABLE_KEY"]
            try:
                user = request_json(
                    f"{SUPABASE_URL}/auth/v1/user",
                    {"apikey": publishable_key, "Authorization": f"Bearer {token}"},
                )
            except urllib.error.HTTPError as error:
                if error.code in (401, 403):
                    self.reply(401, {"error": "Your sign-in has expired. Please sign in again."})
                    return
                raise
            service_key = os.environ["SUPABASE_SECRET_KEY"]
            profiles = request_json(
                f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user['id']}&select=approved",
                {"apikey": service_key, "Authorization": f"Bearer {service_key}"},
            )
            if not profiles or not profiles[0]["approved"]:
                self.reply(403, {"error": "Your account is waiting for approval."})
                return

            user_id = user['id']
            lock = acquire(user_id)
            if lock.get('error'):
                self.reply(409 if lock['error'] == 'busy' else 403, {'error': 'A reply is already in progress. Please wait.' if lock['error'] == 'busy' else 'Your account is waiting for approval.'})
                return
            lease = lock['lease']
            try:
                messages, reservation = prepare(user['id'], chat_id, message)
            except LookupError:
                self.reply(404, {"error": "Conversation not found."})
                return
            if reservation.get("error"):
                reason = reservation['error']
                status, error = {
                    "approval": (403, "Your account is waiting for approval."),
                    "conversation": (404, "Conversation not found."),
                    "limit": (429, "Your daily chat limit has been reached. Try again tomorrow (UTC)."),
                }.get(reason, (503, "Oreo is unavailable right now."))
                self.reply(status, {"error": error})
                return
            chat_id = reservation['conversation_id']
            client = OpenAI(api_key=os.environ["ABBY_API_KEY"], base_url="https://api.abby.abb.com/api/v1/developers", timeout=60, max_retries=1)
            completion = client.chat.completions.create(
                model="claude-4.5-haiku",
                messages=messages,
                max_tokens=MAX_OUTPUT,
                temperature=0.7,
            )
            reply = completion.choices[0].message.content
            if not reply or not reply.strip():
                self.reply(502, {"error": "Oreo returned no answer. Try again shortly.", "conversation_id": chat_id})
                return
            save_turn(user['id'], chat_id, message, reply)
            self.reply(200, {"reply": reply, "conversation_id": chat_id, "remaining": reservation['remaining']})
        except (ValueError, UnicodeDecodeError):
            self.reply(400, {"error": "Send a valid JSON message."})
        except Exception:
            self.reply(500, {"error": "Oreo is unavailable right now. Try again shortly."})
        finally:
            if lease:
                try:
                    release(user_id, lease)
                except Exception:
                    pass
