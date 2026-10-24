"""A small moving light for terminal waits."""

import math
import time

from rich.text import Text


class Thinking:
    def __init__(self):
        self.started = time.monotonic()

    def __rich__(self):
        elapsed = time.monotonic() - self.started
        head = (math.sin(elapsed * 2.8) + 1) * 5.5
        colors = ("bright_white", "bright_cyan", "cyan", "blue", "#303044")
        line = Text("  ")
        for index in range(12):
            distance = min(4, int(abs(index - head)))
            line.append("━", style=colors[distance])
        line.append("  Thinking", style="bold")
        line.append("…", style="dim")
        if elapsed >= 1:
            line.append(f"  {int(elapsed)}s", style="dim")
        return line
