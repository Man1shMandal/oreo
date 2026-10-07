"""Chats are plain JSON files in ~/.oreo/chats."""

import json
import time
from pathlib import Path

DIR = Path.home() / ".oreo" / "chats"


class Chat:
    def __init__(self, path=None, messages=None, title=""):
        self.path = path or DIR / f"{time.strftime('%Y%m%d-%H%M%S')}.json"
        self.messages = messages or []
        self.title = title

    def save(self):
        if not self.messages:
            return
        if not self.title:
            first = next((m["content"] for m in self.messages if m["role"] == "user"), "")
            self.title = first.splitlines()[0][:60] if first else "untitled"
        DIR.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"title": self.title, "messages": self.messages}, indent=1))

    @classmethod
    def load(cls, path):
        d = json.loads(path.read_text())
        return cls(path, d["messages"], d.get("title", ""))


def recent(n=10):
    if not DIR.exists():
        return []
    files = sorted(DIR.glob("*.json"), reverse=True)[:n]
    return [Chat.load(f) for f in files]
