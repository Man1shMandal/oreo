"""Provider configuration stays outside the repository and browser settings."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oreo import config
from oreo.provider import Provider


class ProviderConfigTests(unittest.TestCase):
    def test_environment_overrides_private_file(self):
        with tempfile.TemporaryDirectory() as folder, patch('oreo.config.Path.home', return_value=Path(folder)):
            path = Path(folder) / '.oreo'
            path.mkdir()
            (path / 'provider.json').write_text(json.dumps({'base_url': 'https://private.example/v1'}))
            with patch.dict(os.environ, {'OREO_API_BASE_URL': 'https://override.example/v1'}):
                self.assertEqual(config.provider_setting('base_url'), 'https://override.example/v1')
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(config.provider_setting('base_url'), 'https://private.example/v1')

    def test_missing_endpoint_fails_before_creating_client(self):
        with patch('oreo.provider.config.provider_setting', return_value=''), patch('oreo.provider.OpenAI') as client:
            with self.assertRaisesRegex(ValueError, 'OREO_API_BASE_URL'):
                Provider('test')
            client.assert_not_called()

    def test_usage_supports_bearer_and_custom_headers(self):
        for header, expected in [('Authorization', 'Bearer test'), ('X-Model-Key', 'test')]:
            with self.subTest(header=header), patch('oreo.provider.OpenAI'), patch('oreo.provider.urllib.request.urlopen') as request:
                request.return_value.__enter__.return_value.read.return_value = b'{}'
                with patch('oreo.provider.config.provider_setting', side_effect=lambda name, default='': {'base_url': 'https://models.example/v1', 'usage_header': header}[name]):
                    Provider('test').usage()
                sent = request.call_args.args[0]
                self.assertEqual(sent.full_url, 'https://models.example/v1/usage')
                self.assertEqual(sent.get_header(header.capitalize()), expected)
