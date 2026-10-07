"""Expand @path mentions into file contents."""

import re
from pathlib import Path

MAX_BYTES = 200_000
MENTION = re.compile(r"(?<!\S)@(\S+)")


def expand(text):
    """Return (text with files appended, list of attached paths, list of errors)."""
    attached, errors, blocks = [], [], []
    for raw in MENTION.findall(text):
        p = Path(raw).expanduser()
        if not p.is_file():
            errors.append(f"not a file: {raw}")
            continue
        if p.stat().st_size > MAX_BYTES:
            errors.append(f"too big (>200 KB): {raw}")
            continue
        try:
            body = p.read_text()
        except UnicodeDecodeError:
            errors.append(f"not a text file: {raw}")
            continue
        attached.append(raw)
        blocks.append(f'<file path="{raw}">\n{body}\n</file>')
    if blocks:
        text += "\n\n" + "\n\n".join(blocks)
    return text, attached, errors
