"""Reuse HTTPS connections across hosted auth and database requests."""

import io
import base64
import hashlib
import json
import threading
import time
import urllib.error
from collections import OrderedDict

import httpx

# A warm function keeps the pool; credentials remain on individual requests.
client = httpx.Client(timeout=20, limits=httpx.Limits(max_connections=20, max_keepalive_connections=10))
_identity_cache = OrderedDict()
_identity_lock = threading.Lock()
_IDENTITY_CACHE_TTL = 20
_IDENTITY_CACHE_SIZE = 256


def request_json(url, headers, method='GET', data=None):
    response = client.request(method, url, headers=headers, content=data)
    if response.is_error:
        # Keep the existing auth error contract without exposing response bodies.
        raise urllib.error.HTTPError(url, response.status_code, response.reason_phrase,
                                     response.headers, io.BytesIO(response.content))
    return response.json() if response.content else None


def cached_user(token, url, headers, requester):
    """Reuse a freshly verified identity briefly on a warm function instance."""
    try:
        payload = token.split('.')[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))
        token_expiry = float(claims['exp'])
    except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        token_expiry = 0
    cache_key = (url, hashlib.sha256(token.encode()).digest())
    now = time.monotonic()
    with _identity_lock:
        cached = _identity_cache.get(cache_key)
        if cached and cached[0] > now:
            _identity_cache.move_to_end(cache_key)
            return dict(cached[1])
        _identity_cache.pop(cache_key, None)

    user = requester(url, headers)
    # Never extend identity past the JWT's signed expiry. The auth service still
    # validates each new token before it enters this short warm-process cache.
    ttl = min(_IDENTITY_CACHE_TTL, token_expiry - time.time())
    if ttl > 0 and isinstance(user, dict) and user.get('id'):
        with _identity_lock:
            _identity_cache[cache_key] = (time.monotonic() + ttl, dict(user))
            _identity_cache.move_to_end(cache_key)
            while len(_identity_cache) > _IDENTITY_CACHE_SIZE:
                _identity_cache.popitem(last=False)
    return user


def clear_identity_cache():
    """Clear cached identities, primarily for isolated tests."""
    with _identity_lock:
        _identity_cache.clear()
