"""Keeps token use small. Every request goes through build(); see README "Token saving"."""

import hashlib
import json
import re
from pathlib import Path

from . import attach, config

CACHE = Path.home() / ".oreo" / "cache"
FILE_BLOCK = re.compile(r'<file path="([^"]*)">\n(.*?)\n</file>', re.S)


def tokens(text):
    """Rough count (~4 chars per token). The ABB API doesn't report per-request usage."""
    return len(text) // 4 + 1


def system_prompt(settings, extra="", name=None, owner=True):
    """Standing instructions are the owner's; web visitors get the bare persona."""
    s = config.PERSONA.format(name=name or config.OWNER)
    for title, text in (("Standing instructions", settings["instructions"] if owner else ""),
                        ("For this session", extra)):
        if text:
            s += f"\n{title}: {text}"
    return s


def stub_files(text):
    """Old attachments become one line; re-attach with @path if the model needs them again."""
    return FILE_BLOCK.sub(lambda m: f"[{m[1]} was attached earlier]", text)


def squeeze(text):
    """Drop trailing spaces and runs of blank lines (mostly from pasted code)."""
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def build(chat, system, budget):
    """System prompt + earlier-summary + the newest messages that fit in `budget` tokens.
    Only the newest message keeps its attached files and images."""
    if chat.summary:
        system += f"\nEarlier in this chat: {chat.summary}"
    out, used = [], 0
    for i, m in enumerate(reversed(chat.messages[chat.summarized:])):
        content = m["content"] if i == 0 else stub_files(m["content"])
        t = tokens(content)
        if out and used + t > budget:
            break
        imgs = m.get("images")
        if imgs and i == 0:
            folder = chat.path.parent / "uploads"
            content = [{"type": "text", "text": content}] + [attach.image_part(folder, n) for n in imgs]
        elif imgs:
            content += f"\n[{len(imgs)} image(s) were attached earlier]"
        out.append({"role": m["role"], "content": content})
        used += t
    out.reverse()
    while len(out) > 1 and out[0]["role"] != "user":
        out.pop(0)
    return [{"role": "system", "content": system}] + out


def needs_compact(chat, budget):
    old = chat.messages[chat.summarized:-2]
    return bool(old) and sum(tokens(stub_files(m["content"])) for m in old) > budget


def compact(provider, chat):
    """Fold everything but the last exchange into a short summary, using a cheap model."""
    old = chat.messages[chat.summarized:-2]
    convo = "\n".join(f"{m['role']}: {stub_files(m['content'])}" for m in old)
    if chat.summary:
        convo = f"(summary so far) {chat.summary}\n{convo}"
    prompt = ("Summarize this chat in under 80 words for your own memory: facts, decisions, "
              "names, open questions. No preamble.\n\n" + convo)
    chat.summary = "".join(provider.stream(
        config.SUMMARY_MODEL, [{"role": "user", "content": prompt}], max_tokens=160, temperature=0)).strip()
    chat.summarized = len(chat.messages) - 2


# --- exact-repeat cache: the same question in the same context costs nothing the second time

def _key(model, msgs, params):
    return hashlib.sha256(json.dumps([model, msgs, params], sort_keys=True).encode()).hexdigest()[:32]


def cached(model, msgs, params):
    p = CACHE / _key(model, msgs, params)
    return p.read_text() if p.exists() else None


def remember(model, msgs, params, reply):
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / _key(model, msgs, params)).write_text(reply)


def stream(provider, model, msgs, params, info):
    """provider.stream with the cache in front; sets info["cached"]. Only complete replies are cached."""
    hit = cached(model, msgs, params)
    info["cached"] = hit is not None
    if hit is not None:
        yield hit
        return
    reply = ""
    for piece in provider.stream(model, msgs, **params):
        reply += piece
        yield piece
    remember(model, msgs, params, reply)


def footer(info, msgs, reply):
    """'≈120 in · 45 out' (or 'cached, 0 tokens') shown under each reply."""
    if info.get("cached"):
        return "cached, 0 tokens"
    sent = sum(tokens(m["content"] if isinstance(m["content"], str) else m["content"][0]["text"])
               for m in msgs)
    return f"≈{sent} in · {tokens(reply)} out"
