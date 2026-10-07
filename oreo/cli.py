"""Oreo: the main chat loop."""

import os
from pathlib import Path

from prompt_toolkit import PromptSession, prompt
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

from . import commands, config, files, lean, settings, store
from .provider import Provider


class Session:
    def __init__(self, provider=None):
        self.console = Console(highlight=False)
        self.settings = settings.load()
        self.model = self.settings["model"]
        self.params = {k: self.settings[k] for k in config.DEFAULTS}
        self.extra_system = ""
        self.chat = store.Chat()
        self.provider = provider or self.connect()

    def connect(self):
        key = os.environ.get("ABBY_API_KEY") or settings.get_key()
        if not key:
            self.out("[bold]Welcome to Oreo.[/] Paste your ABB API key to get started (starts with sk-).")
            key = commands.ask_key(self)
            if not key:
                raise SystemExit("No key, no Oreo. Run oreo again when you have it.")
        return Provider(key)

    def out(self, text):
        self.console.print(text)

    def input(self, label, password=False, default=""):
        return prompt(label, is_password=password, default=default).strip()

    def ask(self, text):
        text, attached, errors = files.expand(text)
        for e in errors:
            self.out(f"[yellow]{e}[/]")
        if attached:
            self.out(f"[dim]attached {', '.join(attached)}[/]")
        self.chat.messages.append({"role": "user", "content": lean.squeeze(text)})
        system = lean.system_prompt(self.settings, self.extra_system)
        msgs = lean.build(self.chat, system, self.settings["context"])
        info = {}

        reply = ""
        self.out("")
        try:
            with Live(Markdown(""), console=self.console, refresh_per_second=12, vertical_overflow="visible") as live:
                for piece in lean.stream(self.provider, self.model, msgs, self.params, info):
                    reply += piece
                    live.update(Markdown(reply))
        except KeyboardInterrupt:
            self.out("[dim](stopped)[/]")
        except Exception as e:
            self.out(f"[red]{e}[/]")
            self.chat.messages.pop()
            return
        self.chat.messages.append({"role": "assistant", "content": reply})
        self.out(f"[dim]{self.provider.last_model} · {lean.footer(info, msgs, reply)}[/]\n")
        if lean.needs_compact(self.chat, self.settings["context"]):
            try:
                lean.compact(self.provider, self.chat)
            except Exception as e:
                self.out(f"[dim]couldn't summarize older messages: {e}[/]")
        self.chat.save()

    def handle(self, line):
        if line.startswith("/"):
            name, _, arg = line[1:].partition(" ")
            fn = commands.COMMANDS.get(name, (None,))[0]
            if fn:
                fn(self, arg.strip())
            else:
                self.out(f"[red]unknown command /{name}[/] — try /help")
        else:
            self.ask(line)


def main():
    s = Session()
    home = str(Path.cwd()).replace(str(Path.home()), "~")
    s.out(f"[bold]oreo[/] [dim]· {s.model} · {home} · /help for commands[/]\n")
    hist = Path.home() / ".oreo" / "history"
    hist.parent.mkdir(parents=True, exist_ok=True)
    prompt = PromptSession(history=FileHistory(str(hist)))
    while True:
        try:
            line = prompt.prompt("› ").strip()
        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        if not line:
            continue
        try:
            s.handle(line)
        except EOFError:
            break
    s.chat.save()


if __name__ == "__main__":
    main()
