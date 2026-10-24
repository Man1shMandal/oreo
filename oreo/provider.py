"""Talks to the configured model API. Swap this file to support another provider."""

import json
import urllib.request

from openai import OpenAI

from . import config


class Provider:
    def __init__(self, key):
        self.set_key(key)

    def set_key(self, key):
        self.key = key
        base_url = config.provider_setting("base_url")
        if not base_url:
            raise ValueError("Set OREO_API_BASE_URL or base_url in ~/.oreo/provider.json first.")
        self.client = OpenAI(api_key=key, base_url=base_url, timeout=60, max_retries=0)

    def stream(self, model, messages, tries=3, **params):
        """Yield text chunks; the final served model name is stored on self.last_model.
        Recover empty streams with an ordinary completion. Never replay partial answers."""
        self.last_model = model
        for attempt in range(max(1, tries)):
            if attempt == max(1, tries) - 1:
                resp = self.client.chat.completions.create(
                    model=model, messages=messages, stream=False, **params
                )
                if resp.model:
                    self.last_model = resp.model
                text = resp.choices[0].message.content if resp.choices else ""
                if text and text.strip():
                    yield text
                    return
                break
            resp = self.client.chat.completions.create(
                model=model, messages=messages, stream=True, **params
            )
            got = False
            pending = ""
            try:
                for chunk in resp:
                    if chunk.model:
                        self.last_model = chunk.model
                    if chunk.choices and chunk.choices[0].delta.content:
                        piece = chunk.choices[0].delta.content
                        if got:
                            yield piece
                        else:
                            pending += piece
                            if pending.strip():
                                got = True
                                yield pending
            finally:
                resp.close()
            if got:
                return
        raise RuntimeError("The model service returned an empty reply. Try again in a minute.")

    def usage(self):
        header = config.provider_setting("usage_header", "Authorization")
        credential = "Bearer " + self.key if header == "Authorization" else self.key
        req = urllib.request.Request(
            config.provider_setting("base_url").rstrip("/") + "/usage",
            headers={header: credential, "User-Agent": "oreo/0.1"},
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
