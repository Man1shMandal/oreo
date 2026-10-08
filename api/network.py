"""Reuse HTTPS connections across hosted auth and database requests."""

import io
import urllib.error

import httpx

# A warm function keeps the pool; credentials remain on individual requests.
client = httpx.Client(timeout=20, limits=httpx.Limits(max_connections=20, max_keepalive_connections=10))


def request_json(url, headers, method='GET', data=None):
    response = client.request(method, url, headers=headers, content=data)
    if response.is_error:
        # Keep the existing auth error contract without exposing response bodies.
        raise urllib.error.HTTPError(url, response.status_code, response.reason_phrase,
                                     response.headers, io.BytesIO(response.content))
    return response.json() if response.content else None
