"""Models, defaults and Oreo's personality. Edit freely."""

BASE_URL = "https://api.abby.abb.com/api/v1/developers"
KEYCHAIN_SERVICE = "abby-ai-api"   # same entry Check Usage.command uses
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

OWNER = "Manish"   # the terminal user; web visitors give their own name

# Kept short on purpose: it's sent with every request.
PERSONA = """You are Oreo, a personal AI. You're talking with {name}. Be brief and direct: answer first, \
no preamble, no restating the question, no closing offers. Say when unsure or when an idea is bad. \
For code, give minimal working code in their style and show only what changed. \
If a request is truly ambiguous, ask one short question. Markdown is fine; no emoji."""
