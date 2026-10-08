"""A small authenticated chat endpoint for the hosted OREO v1."""

import json
import os
import tempfile
import urllib.error
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from openai import OpenAI

from oreo import attach, config, research
from api.messages import pack, file_metadata
from api.network import request_json
from api.preferences import validate
from api.conversations import conversation_id, prepare, save_turn, acquire, release, activate_profile


SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")


class handler(BaseHTTPRequestHandler):
    def event(self, payload):
        if self.streaming:
            self.wfile.write(("data: " + json.dumps(payload) + "\n\n").encode())
            self.wfile.flush()

    def reply(self, status, payload):
        if getattr(self, "streaming", False):
            self.event({**payload, "done": status == 200})
            return
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        self.streaming = False
        lease = None
        user_id = None
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 3_200_000:
                self.reply(400, {"error": "Message or attachments are too large. Keep the total upload under 3 MB."})
                return
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict) or not isinstance(payload.get("message", ""), str):
                self.reply(400, {"error": "Send a text message."})
                return
            message = payload.get("message", "").strip()
            try:
                chat_id = conversation_id(payload.get("conversation_id"))
            except (ValueError, TypeError, AttributeError):
                self.reply(400, {"error": "Send a valid conversation ID."})
                return
            preferences = validate(payload.get("settings"))
            uploads = payload.get("files", [])
            if not isinstance(uploads, list) or len(uploads) > 5:
                self.reply(400, {"error": "Attach up to 5 files at a time."})
                return
            if any(not isinstance(u, dict) or not isinstance(u.get("data"), str) or not isinstance(u.get("name", ""), str) for u in uploads):
                self.reply(400, {"error": "Send valid file attachments."})
                return
            if not message and not uploads:
                self.reply(400, {"error": "Write a message or attach a file."})
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
            user_id = user['id']
            wants_stream = payload.get("stream") is True
            if wants_stream:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Accel-Buffering", "no")
                self.end_headers()
                self.streaming = True
                self.event({"status": "Checking your account…"})
            try:
                activate_profile(user_id)
            except LookupError as error:
                self.reply(503, {'error': str(error)})
                return
            self.event({"status": "Preparing your chat…"})
            lock = acquire(user_id)
            if lock.get('error'):
                self.reply(409 if lock['error'] == 'busy' else 503, {'error': 'A reply is already in progress. Please wait.' if lock['error'] == 'busy' else 'Oreo is unavailable right now. Try again shortly.'})
                return
            lease = lock['lease']
            sources = []
            self.event({"status": "Reading attachments…" if uploads else "Loading conversation…"})
            try:
                with tempfile.TemporaryDirectory(prefix="oreo-uploads-") as temp_dir:
                    blocks, image_names, errors = attach.process(uploads, Path(temp_dir))
                    if errors:
                        raise ValueError(" · ".join(errors))
                    images = [attach.image_part(Path(temp_dir), name) for name in image_names]
                    stored_message = pack(message, documents=blocks, images=images,
                                          files=file_metadata(uploads))
                    messages, reservation = prepare(user_id, chat_id, stored_message, settings=preferences)
            except LookupError:
                self.reply(404, {"error": "Conversation not found."})
                return
            except ValueError as error:
                self.reply(400, {"error": str(error)})
                return
            chat_id = reservation['conversation_id']
            self.event({"conversation_id": chat_id, "status": "Searching the web…" if payload.get("web") else "Connecting to the model…"})
            warnings = []
            if payload.get("web"):
                sources = self.search_web(messages)
                if sources:
                    # Keep fetched context short so research does not dominate the prompt.
                    context = research.block(sources)[:13000]
                    content = messages[-1]["content"]
                    if isinstance(content, str):
                        messages[-1]["content"] += context
                    else:
                        content[0]["text"] += context
                else:
                    warnings.append("Web search returned no readable sources. This reply does not use fresh web results.")
                self.event({"status": "Writing…", "sources": [{"title": s["title"], "url": s["url"]} for s in sources]})
            model = payload.get("model") if payload.get("model") in config.MODELS.values() else config.MODELS[config.DEFAULT_MODEL]
            if any(isinstance(m["content"], list) for m in messages) and not model.startswith("claude"):
                model = config.VISION_MODEL
            client = OpenAI(api_key=os.environ["ABBY_API_KEY"], base_url="https://api.abby.abb.com/api/v1/developers", timeout=120, max_retries=0)
            if wants_stream:
                self.event({"status": "Waiting for the model…"})
                chunks = client.chat.completions.create(model=model, messages=messages,
                    temperature=preferences["temperature"], stream=True)
                pieces = []
                for chunk in chunks:
                    if chunk.choices and chunk.choices[0].delta.content:
                        piece = chunk.choices[0].delta.content
                        pieces.append(piece)
                        self.event({"text": piece})
                reply = "".join(pieces)
            else:
                completion = client.chat.completions.create(model=model, messages=messages,
                    temperature=preferences["temperature"])
                reply = completion.choices[0].message.content
            if not reply or not reply.strip():
                self.reply(502, {"error": "Oreo returned no answer. Try again shortly.", "conversation_id": chat_id})
                return
            save_turn(user['id'], chat_id, stored_message, pack(reply, sources=[{"title": s["title"], "url": s["url"]} for s in sources]))
            # Let an immediate follow-up acquire the lease before announcing done.
            try:
                release(user_id, lease)
                lease = None
            except Exception:
                pass  # The finally block retries; the saved answer still succeeds.
            self.reply(200, {"reply": reply, "conversation_id": chat_id, "unlimited": True, "warnings": warnings, "model": model, "attachment_errors": errors, "sources": [{"title": s["title"], "url": s["url"]} for s in sources]})
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

    def search_web(self, messages):
        # These messages have already passed ownership checks.
        rows = []
        for m in messages:
            if m["role"] != "system":
                content = m["content"]
                rows.append({"role": m["role"], "content": content if isinstance(content, str) else content[0]["text"]})
        query = rows[-1]["content"]
        links = research.URL.findall(query)[:3]

        try:
            queries = [] if links else [query[:500]] if query.strip() else []
            if not queries and not links:
                return []
            return research.gather(queries, links, research.keywords(query), lambda _status: None)
        except Exception:
            return []
