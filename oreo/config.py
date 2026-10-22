"""Models, defaults and Oreo's personality. Edit freely."""

import json
import os
from pathlib import Path


def provider_setting(name, default=""):
    """Read deployment overrides or private local provider configuration."""
    variable = {"base_url": "OREO_API_BASE_URL", "usage_header": "OREO_USAGE_HEADER",
                "keychain_service": "OREO_KEYCHAIN_SERVICE"}[name]
    if variable in os.environ:
        return os.environ[variable]
    path = Path.home() / ".oreo" / "provider.json"
    return json.loads(path.read_text()).get(name, default) if path.exists() else default


BASE_URL = provider_setting("base_url")
KEYCHAIN_SERVICE = provider_setting("keychain_service", "oreo-api")
KEYCHAIN_ACCOUNT = "usage"

# short name -> API model id
MODELS = {
    "opus": "claude-5.5-opus",
    "sonnet5": "claude-5-sonnet",
    "sonnet": "claude-4.6-sonnet",
    "haiku": "claude-4.5-haiku",
    "gpt": "gpt-6-luna",
    "gemini": "gemini-3.8-flash",
}
DEFAULT_MODEL = "sonnet"

DEFAULTS = {"temperature": 0.7, "max_tokens": 1024}   # sent to the API with every request

# Token saving (see lean.py)
CONTEXT_TOKENS = 1500                # history sent per request; older turns get summarized
SUMMARY_MODEL = "claude-4.5-haiku"   # Claude models used the fewest tokens per request in tests
VISION_MODEL = "claude-4.6-sonnet"   # used for messages with images when a GPT/Gemini model is picked (they can't see them via the gateway)

OWNER = "Manish"   # the terminal user; web visitors give their own name

# Kept short on purpose: it's sent with every request.
PERSONA = """You are Oreo, an AI assistant. You're talking with {name}. Be brief and direct: answer first, \
no preamble, no restating the question, no closing offers. Say when unsure or when an idea is bad. \
For code, give minimal working code in their style and show only what changed. \
If a request is truly ambiguous, ask one short question. Markdown is fine; no emoji."""
