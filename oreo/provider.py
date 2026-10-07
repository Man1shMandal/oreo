"""Talks to the ABB API. Swap this file to support another provider."""

import json
import time
import urllib.request

from openai import OpenAI

from . import config


class Provider:
    def __init__(self, key):
        self.set_key(key)

    def set_key(self, key):
        self.key = key
        self.client = OpenAI(api_key=key, base_url=config.BASE_URL)

    def stream(self, model, messages, tries=3, **params):
        """Yield text chunks; the final served model name is stored on self.last_model.
        The gateway sometimes swallows an upstream error and streams nothing, so empty replies are retried."""
        self.last_model = model
        for attempt in range(tries):
            resp = self.client.chat.completions.create(
                model=model, messages=messages, stream=True, **params
            )
            got = False
            for chunk in resp:
                if chunk.model:
                    self.last_model = chunk.model
                if chunk.choices and chunk.choices[0].delta.content:
                    got = True
                    yield chunk.choices[0].delta.content
            if got:
                return
            time.sleep(1 + attempt)
        raise RuntimeError("the ABB server sent back nothing (it's having trouble), try again in a minute")

    def usage(self):
        req = urllib.request.Request(
            config.BASE_URL + "/usage",
            headers={"X-ABBY-API-Key": self.key, "User-Agent": "oreo/0.1"},
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
