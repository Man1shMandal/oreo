"""Pooled requests retain auth errors and isolate per-request credentials."""

import unittest
import tomllib
from pathlib import Path
import urllib.error
from unittest.mock import patch

import httpx
from api import network


class NetworkTests(unittest.TestCase):
    def test_vercel_and_ci_dependencies_match(self):
        root = Path(__file__).resolve().parent.parent
        deployed = tomllib.loads((root / 'pyproject.toml').read_text())['project']['dependencies']
        tested = (root / 'requirements.txt').read_text().splitlines()
        self.assertEqual(set(deployed), set(tested))

    def test_credentials_do_not_leak_between_calls(self):
        seen = []
        def respond(request):
            seen.append(request.headers.get('authorization'))
            return httpx.Response(200, json={'ok': True})
        with httpx.Client(transport=httpx.MockTransport(respond)) as client, patch.object(network, 'client', client):
            network.request_json('https://example.test/auth', {'Authorization': 'Bearer first'})
            network.request_json('https://example.test/auth', {'Authorization': 'Bearer second'})
            network.request_json('https://example.test/public', {})
        self.assertEqual(seen, ['Bearer first', 'Bearer second', None])

    def test_expired_auth_preserves_error_status(self):
        with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401))) as client, patch.object(network, 'client', client):
            with self.assertRaises(urllib.error.HTTPError) as error:
                network.request_json('https://example.test/auth', {})
        self.assertEqual(error.exception.code, 401)
        error.exception.close()

    def test_empty_write_response(self):
        with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(204))) as client, patch.object(network, 'client', client):
            self.assertIsNone(network.request_json('https://example.test/db', {}, 'POST', b'{}'))
