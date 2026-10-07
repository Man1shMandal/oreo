"""Hosted conversation storage and usage reservations."""

import json
import os
import urllib.request
from uuid import UUID


SYSTEM_PROMPT = "You are Oreo, a personal AI assistant. Be brief, direct, and useful. No emoji. Do not add creator attribution to replies."
MAX_OUTPUT = 700


def conversation_id(value):
    if value is None:
        return None
    return str(UUID(value))


def database(path, method="GET", payload=None):
    key = os.environ["SUPABASE_SECRET_KEY"]
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        f"{os.environ['SUPABASE_URL'].rstrip('/')}/rest/v1/{path}",
        headers=headers, method=method, data=data,
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read()
        return json.loads(body) if body else None


def prepare(user_id, chat_id, message):
    history = []
    if chat_id:
        owned = database(f"conversations?id=eq.{chat_id}&user_id=eq.{user_id}&select=id")
        if not owned:
            raise LookupError("Conversation not found.")
        rows = database(f"messages?conversation_id=eq.{chat_id}&select=role,content&order=created_at.desc,id.desc&limit=20")
        # Keep recent complete turns within the same small context budget as local Oreo.
        size = 0
        for row in rows:
            if size + len(row["content"]) > 6000:
                break
            history.append({"role": row["role"], "content": row["content"]})
            size += len(row["content"])
        history.reverse()
        while history and history[0]["role"] != "user":
            history.pop(0)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history, {"role": "user", "content": message}]
    # The gateway omits actual usage. Budget estimates include the entire prompt
    # and reserve the full output cap before a provider call, including failures.
    estimated_input = sum((len(row["content"]) + 3) // 4 + 8 for row in messages)
    reservation = database("rpc/reserve_chat", "POST", {
        "p_user": user_id, "p_conversation": chat_id,
        "p_title": message[:80], "p_input": estimated_input, "p_output": MAX_OUTPUT,
    })
    return messages, reservation


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
    # The deployed quota functions still inspect the legacy flag. Nobody waits
    # for approval: every authenticated account is enabled by the server.
    if not profile['approved']:
        database(f"profiles?id=eq.{user_id}", "PATCH", {"approved": True})
    return {key: value for key, value in profile.items() if key != 'approved'}
