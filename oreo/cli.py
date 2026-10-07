"""Oreo: the main chat loop."""

import os
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

from . import commands, config, files, store
from .provider import Provider


class Session:
    def __init__(self, provider=None):
        self.console = Console(highlight=False)
        self.provider = provider or Provider()
        self.model = config.MODELS[config.DEFAULT_MODEL]
        self.params = dict(config.DEFAULTS)
        self.extra_system = ""
        self.chat = store.Chat()

    def out(self, text):
        self.console.print(text)

    def system_prompt(self):
        s = config.PERSONA + f"\nCurrent directory: {os.getcwd()}"
        return s + (f"\n\nExtra instructions from the user:\n{self.extra_system}" if self.extra_system else "")

    def ask(self, text):
        text, attached, errors = files.expand(text)
        for e in errors:
            self.out(f"[yellow]{e}[/]")
        if attached:
            self.out(f"[dim]attached {', '.join(attached)}[/]")
        self.chat.messages.append({"role": "user", "content": text})
        msgs = [{"role": "system", "content": self.system_prompt()}] + self.chat.messages

        reply = ""
        self.out("")
        try:
            with Live(Markdown(""), console=self.console, refresh_per_second=12, vertical_overflow="visible") as live:
                for piece in self.provider.stream(self.model, msgs, **self.params):
                    reply += piece
                    live.update(Markdown(reply))
        except KeyboardInterrupt:
            self.out("[dim](stopped)[/]")
        except Exception as e:
            self.out(f"[red]{e}[/]")
            self.chat.messages.pop()
            return
        self.chat.messages.append({"role": "assistant", "content": reply})
        self.chat.save()
        self.out(f"[dim]{self.provider.last_model}[/]\n")

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
