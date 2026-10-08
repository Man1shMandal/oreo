"""Hosted conversation storage and owned context."""

import json
import os
from uuid import UUID

from api.messages import prompt_content, unpack
from api.preferences import validate, STYLE
from api.context import select_history
from api.network import request_json


SYSTEM_PROMPT = "You are Oreo, a personal AI assistant. Be direct and useful. No emoji. Do not add creator attribution to replies."


def conversation_id(value):
    if value is None:
        return None
    return str(UUID(value))


def database(path, method="GET", payload=None):
    key = os.environ["SUPABASE_SECRET_KEY"]
    headers = {"Prefer": "return=representation", "apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    data = None if payload is None else json.dumps(payload).encode()
    return request_json(f"{os.environ['SUPABASE_URL'].rstrip('/')}/rest/v1/{path}",
                        headers, method, data)


def prepare(user_id, chat_id, message, settings=None):
    preferences = validate(settings)
    history = []
    current = unpack(message)
    reuse = preferences['reuse_files'] and not (current.get('documents') or current.get('images'))
    if chat_id:
        owned = database(
            f"conversations?id=eq.{chat_id}&user_id=eq.{user_id}"
            "&select=id,messages(role,content)"
            "&messages.order=created_at.desc,id.desc&messages.limit=100"
        )
        if not owned:
            raise LookupError("Conversation not found.")
        rows = owned[0].get('messages') or []
        history = select_history(rows, current['text'], preferences, reuse)
    system = SYSTEM_PROMPT + "\n" + STYLE[preferences['reply_style']]
    if preferences['instructions'].strip():
        system += "\nUser's standing instructions:\n" + preferences['instructions'].strip()
    messages = [{"role": "system", "content": system}, *history, {"role": "user", "content": prompt_content(message)}]
    new_title = None
    if not chat_id:
        files = current.get('files', [])
        title = current['text'] or ', '.join(f['name'] for f in files) or 'New chat'
        new_title = title[:80]
    return messages, {'conversation_id': chat_id, 'unlimited': True, 'new_conversation_title': new_title}


def create_conversation(user_id, title):
    created = database('conversations', 'POST', {'user_id': user_id, 'title': title})
    return created[0]['id']


def save_turn(user_id, chat_id, message, reply):
    database("rpc/save_chat_turn", "POST", {
        "p_user": user_id, "p_conversation": chat_id,
        "p_message": message, "p_reply": reply,
    })


def acquire(user_id):
    return database("rpc/acquire_chat", "POST", {"p_user": user_id})


def release(user_id, lease):
    database("rpc/release_chat", "POST", {"p_user": user_id, "p_lease": lease})


def activate_profile(user_id):
    """Make sign-in sufficient while supporting the original database schema."""
    rows = database(f"profiles?id=eq.{user_id}&select=id,email,approved,daily_token_limit,created_at")
    if not rows:
        raise LookupError("Account setup is incomplete. Please sign in again.")
    profile = rows[0]
    # The deployed lease/save functions still inspect the legacy flag. Nobody waits
    # for approval: every authenticated account is enabled by the server.
    if not profile['approved']:
        database(f"profiles?id=eq.{user_id}", "PATCH", {"approved": True})
    return {key: value for key, value in profile.items() if key not in ('approved', 'daily_token_limit')}
