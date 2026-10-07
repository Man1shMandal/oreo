"""Slash commands. Add one by decorating a function with @command."""

from datetime import datetime

from . import config, store

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
