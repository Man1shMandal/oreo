"""Slash commands. Add one by decorating a function with @command."""

from datetime import datetime

from . import config, settings, store

COMMANDS = {}


def command(name, help):
    def wrap(fn):
        COMMANDS[name] = (fn, help)
        return fn
    return wrap


@command("help", "list commands")
def _help(s, arg):
    for name, (_, h) in COMMANDS.items():
        s.out(f"  [bold]/{name:<8}[/] {h}")
    s.out("  [bold]@path[/]     attach a file to your message")


@command("model", "show or switch model, e.g. /model opus")
def _model(s, arg):
    if not arg:
        for short, mid in config.MODELS.items():
            mark = "●" if mid == s.model else " "
            s.out(f"  {mark} {short:<8} [dim]{mid}[/]")
        return
    mid = config.MODELS.get(arg, arg if arg in config.MODELS.values() else None)
    if not mid:
        s.out(f"[red]unknown model '{arg}'[/] — try /model")
        return
    s.model = mid
    s.out(f"[dim]switched to {mid}[/]")


@command("new", "start a fresh chat")
def _new(s, arg):
    s.chat.save()
    s.chat = store.Chat()
    s.out("[dim]new chat[/]")


@command("resume", "list recent chats, or /resume 2 to open one")
def _resume(s, arg):
    chats = store.recent()
    if not chats:
        s.out("[dim]no saved chats yet[/]")
        return
    if not arg:
        for i, c in enumerate(chats, 1):
            s.out(f"  {i:>2}  {c.title}")
        return
    try:
        s.chat.save()
        s.chat = chats[int(arg) - 1]
    except (ValueError, IndexError):
        s.out("[red]pick a number from /resume[/]")
        return
    s.out(f"[dim]resumed: {s.chat.title} ({len(s.chat.messages)} messages)[/]")


@command("usage", "tokens used this month")
def _usage(s, arg):
    try:
        d = s.provider.usage()
    except Exception as e:
        s.out(f"[red]couldn't fetch usage: {e}[/]")
        return
    reset = datetime.fromtimestamp(d["reset_at"]).strftime("%b %d")
    s.out(f"  {d['month_usage']:,} of {d['month_limit']:,} tokens ({d['percentage']}) · resets {reset}")


@command("system", "add your own instructions for this session; /system clear to reset")
def _system(s, arg):
    if not arg:
        s.out(f"[dim]{s.extra_system or '(none)'}[/]")
    elif arg == "clear":
        s.extra_system = ""
        s.out("[dim]cleared[/]")
    else:
        s.extra_system = arg
        s.out("[dim]ok[/]")


@command("temp", "set temperature 0–2, e.g. /temp 0.2")
def _temp(s, arg):
    try:
        s.params["temperature"] = float(arg)
        s.out(f"[dim]temperature {arg}[/]")
    except ValueError:
        s.out(f"[dim]temperature is {s.params['temperature']}[/]")


@command("clear", "clear the screen")
def _clear(s, arg):
    s.console.clear()


@command("exit", "quit (Ctrl-D works too)")
def _exit(s, arg):
    raise EOFError


@command("check", "test what the API supports (tool calling, for agent mode)")
def _check(s, arg):
    tool = {"type": "function", "function": {
        "name": "get_time", "description": "Get the current time",
        "parameters": {"type": "object", "properties": {}}}}
    try:
        r = s.provider.client.chat.completions.create(
            model=s.model, max_tokens=50, tools=[tool],
            messages=[{"role": "user", "content": "What time is it? Use the tool."}])
        ok = bool(r.choices[0].message.tool_calls)
    except Exception as e:
        s.out(f"  tool calling on {s.model}: [red]error[/] {e}")
        return
    s.out(f"  tool calling on {s.model}: " + ("[green]works[/]" if ok else "[yellow]not used[/]"))


def ask_key(s):
    """Hidden prompt for the API key; saves it to the Keychain. Returns the key or None."""
    key = s.input("  key: ", password=True)
    if not key:
        return None
    if not key.startswith("sk-"):
        s.out("[red]  that doesn't look right — the key starts with sk-[/]")
        return None
    settings.set_key(key)
    if getattr(s, "provider", None):
        s.provider.set_key(key)
    s.out("[green]  saved to Keychain[/]")
    return key


def _test(s):
    try:
        s.provider.client.chat.completions.create(
            model=s.model, max_tokens=5, messages=[{"role": "user", "content": "hi"}])
        d = s.provider.usage()
        s.out(f"  [green]connected[/] · {s.model} answered · {d['percentage']} of monthly tokens used")
    except Exception as e:
        s.out(f"  [red]failed:[/] {e}")


@command("settings", "key, default model, temperature, instructions")
def _settings(s, arg):
    while True:
        st = s.settings
        short = next((k for k, v in config.MODELS.items() if v == st["model"]), st["model"])
        instr = st["instructions"].replace("\n", " ")
        rows = [
            ("API key", "saved in Keychain"),
            ("Default model", short),
            ("Temperature", st["temperature"]),
            ("Reply length", f"{st['max_tokens']} tokens"),
            ("Instructions", (instr[:40] + "…") if len(instr) > 40 else instr or "(none)"),
            ("Test connection", ""),
        ]
        s.out("\n  [bold]Settings[/]")
        for i, (name, val) in enumerate(rows, 1):
            s.out(f"  {i}  {name:<16} [dim]{val}[/]")
        choice = s.input("\n  pick 1-6, Enter to go back: ")
        if not choice:
            return
        if choice == "1":
            ask_key(s)
        elif choice == "2":
            s.out("  " + "  ".join(config.MODELS))
            m = config.MODELS.get(s.input("  model: "))
            if m:
                st["model"] = s.model = m
        elif choice == "3":
            try:
                st["temperature"] = s.params["temperature"] = min(2.0, max(0.0, float(s.input("  0–2: "))))
            except ValueError:
                s.out("  [red]enter a number like 0.7[/]")
        elif choice == "4":
            try:
                st["max_tokens"] = s.params["max_tokens"] = max(64, int(s.input("  tokens: ")))
            except ValueError:
                s.out("  [red]enter a whole number like 4096[/]")
        elif choice == "5":
            s.out("  [dim]Applies to every chat, e.g. 'I code in Python and C++; keep answers short.'[/]")
            st["instructions"] = s.input("  instructions: ", default=st["instructions"])
        elif choice == "6":
            _test(s)
            continue
        settings.save(st)
