"""Terminal startup, cached replies and empty gateway response recovery."""
import tempfile
import os
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from oreo import cli, config, lean, store
from oreo.provider import Provider


def chunk(text):
    return NS(model='served', choices=[NS(delta=NS(content=text))])


class Stream:
    def __init__(self, pieces):
        self.pieces = pieces
        self.closed = False

    def __iter__(self):
        yield from self.pieces

    def close(self):
        self.closed = True


class TerminalTests(unittest.TestCase):
    def test_launcher_ignores_another_checkout_in_working_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            package = Path(folder) / 'oreo'
            package.mkdir()
            (package / '__main__.py').write_text('raise RuntimeError("wrong checkout")')
            (package / '__init__.py').touch()
            env = dict(os.environ, HOME=folder, OREO_API_KEY='test',
                       OREO_API_BASE_URL='https://models.example/v1')
            launcher = Path(__file__).resolve().parents[1] / 'bin/oreo'
            result = subprocess.run([str(launcher)], cwd=folder, env=env,
                                    input='/exit\n', capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('/help for commands', result.stdout)

    def provider(self, responses):
        provider = Provider.__new__(Provider)
        provider.client = Mock()
        provider.client.chat.completions.create.side_effect = responses
        return provider

    def test_empty_streams_fall_back_and_close(self):
        streams = [Stream([chunk('  ')]), Stream([])]
        provider = self.provider(streams + [NS(model='served', choices=[NS(message=NS(content='works'))])])
        self.assertEqual(''.join(provider.stream('model', [])), 'works')
        self.assertTrue(all(s.closed for s in streams))
        self.assertFalse(provider.client.chat.completions.create.call_args.kwargs['stream'])

    def test_exhaustion_does_not_return_empty_answer(self):
        provider = self.provider([Stream([]), Stream([]), NS(model='served', choices=[])])
        with self.assertRaisesRegex(RuntimeError, 'empty reply'):
            list(provider.stream('model', []))

    def test_partial_failure_is_not_replayed(self):
        class BrokenStream(Stream):
            def __iter__(self):
                yield chunk('partial')
                raise RuntimeError('disconnected')
        stream = BrokenStream([])
        provider = self.provider([stream])
        pieces = provider.stream('model', [])
        self.assertEqual(next(pieces), 'partial')
        with self.assertRaisesRegex(RuntimeError, 'disconnected'):
            next(pieces)
        self.assertEqual(provider.client.chat.completions.create.call_count, 1)
        self.assertTrue(stream.closed)

    def test_cached_first_reply_needs_no_provider_model(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(lean, 'CACHE', Path(folder) / 'cache'), patch.object(store, 'DIR', Path(folder) / 'chats'):
            provider = NS(stream=Mock(side_effect=AssertionError('must use cache')))
            session = cli.Session(provider)
            text = 'cached question'
            system = lean.system_prompt(session.settings)
            session.chat.messages = [{'role': 'user', 'content': text}]
            messages = lean.build(session.chat, system, session.settings['context'])
            lean.remember(session.model, messages, session.params, 'cached answer')
            session.chat.messages = []
            session.ask(text)
            self.assertEqual(session.chat.messages[-1]['content'], 'cached answer')
            self.assertTrue(session.chat.path.exists())

    def test_cancelled_setup_exits_cleanly(self):
        for error in (EOFError, KeyboardInterrupt):
            with self.subTest(error=error), patch.object(cli, 'Session', side_effect=error):
                cli.main()

    def test_retired_model_uses_default(self):
        values = {'model': 'retired', 'instructions': '', 'context': 1500, **config.DEFAULTS}
        with patch.object(cli.settings, 'load', return_value=values):
            self.assertEqual(cli.Session(NS()).model, config.MODELS[config.DEFAULT_MODEL])
