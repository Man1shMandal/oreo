"""User settings in ~/.oreo/settings.json, plus the key in the macOS Keychain."""

import json
import subprocess
from pathlib import Path

from . import config

PATH = Path.home() / ".oreo" / "settings.json"


def load():
    s = {"model": config.MODELS[config.DEFAULT_MODEL], "instructions": "", **config.DEFAULTS}
    if PATH.exists():
        s.update(json.loads(PATH.read_text()))
    return s


def save(s):
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(s, indent=1))


def get_key():
    try:
        return subprocess.run(
            ["security", "find-generic-password", "-s", config.KEYCHAIN_SERVICE,
             "-a", config.KEYCHAIN_ACCOUNT, "-w"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        return None


def set_key(key):
    subprocess.run(
        ["security", "add-generic-password", "-U", "-s", config.KEYCHAIN_SERVICE,
         "-a", config.KEYCHAIN_ACCOUNT, "-w", key],
        check=True, capture_output=True,
    )
