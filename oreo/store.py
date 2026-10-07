"""Chats are plain JSON files in ~/.oreo/chats (web visitors get a subfolder each)."""

import json
import time
from pathlib import Path

DIR = Path.home() / ".oreo" / "chats"


class Chat:
    def __init__(self, path=None, messages=None, title="", summary="", summarized=0, folder=None):
        self.path = path or (folder or DIR) / f"{time.strftime('%Y%m%d-%H%M%S')}.json"
        self.messages = messages or []
        self.title = title
        self.summary = summary          # recap of messages[:summarized], see lean.py
        self.summarized = summarized

    def save(self):
        if not self.messages:
            return
        if not self.title:
            first = next((m["content"] for m in self.messages if m["role"] == "user"), "")
            self.title = first.splitlines()[0][:60] if first else "untitled"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"title": self.title, "summary": self.summary,
                                         "summarized": self.summarized, "messages": self.messages}, indent=1))

    @classmethod
    def load(cls, path):
        d = json.loads(path.read_text())
        return cls(path, d["messages"], d.get("title", ""), d.get("summary", ""), d.get("summarized", 0))


def recent(n=10, folder=None):
    folder = folder or DIR
    if not folder.exists():
        return []
    files = sorted(folder.glob("*.json"), reverse=True)[:n]
    return [Chat.load(f) for f in files]
