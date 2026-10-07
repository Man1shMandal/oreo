"""Talks to the ABB API. Swap this file to support another provider."""

import json
import os
import subprocess
import urllib.request

from openai import OpenAI

from . import config


def api_key():
    key = os.environ.get("ABBY_API_KEY")
    if key:
        return key
    try:
        return subprocess.run(
            ["security", "find-generic-password", "-s", config.KEYCHAIN_SERVICE,
             "-a", config.KEYCHAIN_ACCOUNT, "-w"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        raise SystemExit("No API key. Run ~/Desktop/ABBY_API/'Replace Key.command' or set ABBY_API_KEY.")


class Provider:
    def __init__(self):
        self.key = api_key()
        self.client = OpenAI(api_key=self.key, base_url=config.BASE_URL)

    def stream(self, model, messages, **params):
        """Yield text chunks; the final served model name is stored on self.last_model."""
        self.last_model = model
        resp = self.client.chat.completions.create(
            model=model, messages=messages, stream=True, **params
        )
        for chunk in resp:
            if chunk.model:
                self.last_model = chunk.model
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def usage(self):
        req = urllib.request.Request(
            config.BASE_URL + "/usage",
            headers={"X-ABBY-API-Key": self.key, "User-Agent": "oreo/0.1"},
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
