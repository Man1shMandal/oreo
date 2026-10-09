"""Account and history authorization checks with a fake database."""

import io
import json
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from api.hosted import HostedHandler

USER = '00000000-0000-0000-0000-000000000001'
OTHER = '00000000-0000-0000-0000-000000000002'


class Request(HostedHandler):
    def __init__(self, path='/api/conversations', payload=None):
        body = json.dumps(payload).encode()
        self.headers = {'Content-Length': str(len(body))}
        self.rfile = io.BytesIO(body)
        self.path = path

    def reply(self, status, payload):
        self.result = status, payload


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.identity = patch('api.hosted.identity', return_value=(
            {'id': USER, 'email': 'user@example.test'},
            {'id': USER, 'daily_token_limit': 20000},
        )).start()
        self.database = patch('api.hosted.database', return_value=[]).start()
        self.addCleanup(patch.stopall)

    def test_history_list_is_scoped_to_authenticated_owner(self):
        request = Request()
        request.hosted_GET('/api/conversations')
        self.assertEqual(request.result[0], 200)
        self.assertIn('user_id=eq.' + USER, self.database.call_args.args[0])

    def test_unowned_chat_never_reads_messages(self):
        request = Request('/api/conversations?id=' + OTHER)
        request.hosted_GET('/api/conversations')
        self.assertEqual(request.result[0], 404)
        self.assertEqual(self.database.call_count, 1)
        self.assertIn('user_id=eq.' + USER, self.database.call_args.args[0])

    def test_signed_in_account_can_read_history(self):
        request = Request()
        request.hosted_GET('/api/conversations')
        self.assertEqual(request.result[0], 200)

    def test_profile_is_unlimited_without_reading_daily_usage(self):
        request = Request()
        request.hosted_GET('/api/profile')
        self.assertTrue(request.result[1]['unlimited'])
        self.assertNotIn('usage', request.result[1])
        self.database.assert_not_called()


class RemovedAdminRouteTests(unittest.TestCase):
    def test_admin_route_is_unavailable_for_both_methods(self):
        from api.index import handler
        for method in ('do_GET', 'do_POST'):
            with self.subTest(method=method):
                request = object.__new__(handler)
                request.path = '/api/admin'
                request.reply = Mock()
                getattr(request, method)()
                request.reply.assert_called_once_with(404, {'error': 'Not found.'})


class InstallableAppTests(unittest.TestCase):
    def get(self, path):
        from api.index import handler
        request = object.__new__(handler)
        request.path = path
        request.headers = {}
        request.send_response, request.send_header, request.end_headers = Mock(), Mock(), Mock()
        request.wfile = io.BytesIO()
        request.do_GET()
        request.send_response.assert_called_once_with(200)
        return dict(call.args for call in request.send_header.call_args_list), request.wfile.getvalue()

    def test_app_files_are_served_with_their_types(self):
        for path, kind in (('/manifest.webmanifest', 'application/manifest+json'), ('/sw.js', 'text/javascript; charset=utf-8'),
                           ('/theme.css', 'text/css; charset=utf-8'),
                           ('/icon-192.png', 'image/png'), ('/icon-512.png', 'image/png'),
                           ('/icon-maskable-512.png', 'image/png'), ('/apple-touch-icon.png', 'image/png')):
            with self.subTest(path=path):
                headers, body = self.get(path)
                self.assertEqual(headers['Content-Type'], kind)
                self.assertTrue(body)

    def test_settings_controls_remain_connected_to_preferences(self):
        from pathlib import Path
        page = (Path(__file__).resolve().parent.parent / 'public' / 'index.html').read_text()
        for control in ('settings-form', 'open-settings', 'close-settings', 's-instructions',
                        's-model', 's-style', 's-context', 's-temperature', 's-files',
                        's-web', 's-enter', 's-efficient', 's-reset'):
            with self.subTest(control=control):
                self.assertIn(f'id="{control}"', page)

    def test_header_character_is_decorative_and_tracks_chat_activity(self):
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        page = (root / 'public' / 'index.html').read_text()
        script = (root / 'public' / 'chat.js').read_text()
        styles = (root / 'public' / 'theme.css').read_text()
        self.assertIn('class="oreo-character desktop-character" aria-hidden="true"', page)
        self.assertIn('class="oreo-character mobile-character" aria-hidden="true"', page)
        self.assertEqual(page.count('class="oreo-eye-dot"'), 4)
        self.assertEqual(page.count('class="oreo-smile"'), 2)
        self.assertIn("document.querySelectorAll('.oreo-character')", script)
        self.assertIn("eye.classList.toggle('working', active)", script)
        self.assertIn("eye.classList.toggle('attentive', !active && ready && Boolean(composer.value.trim()))", script)
        self.assertIn('@media (prefers-reduced-motion: reduce)', styles)
        self.assertIn('@keyframes oreo-dot-blink', styles)
        self.assertIn('@keyframes oreo-idle', styles)

    def test_manifest_icons_exist(self):
        _, body = self.get('/manifest.webmanifest')
        for icon in json.loads(body)['icons']:
            with self.subTest(icon=icon['src']):
                self.get(icon['src'])

    def test_service_worker_never_caches_the_api(self):
        _, body = self.get('/sw.js')
        self.assertIn("!url.pathname.startsWith('/api/')", body.decode())
        self.assertIn("request.method !== 'GET'", body.decode())

    def test_offline_shell_has_every_script_the_page_imports(self):
        # A module missing from the shell list stops the installed app from starting offline.
        _, worker = self.get('/sw.js')
        shell = json.loads(re.search(r"const SHELL = (\[.*?\]);", worker.decode()).group(1).replace("'", '"'))
        _, script = self.get('/chat.js')
        for module in re.findall(r"from '\./([\w.-]+)'", script.decode()):
            self.assertIn('/' + module, shell)
        for path in shell:
            with self.subTest(path=path):
                self.get(path)

    def test_ios_gets_install_steps(self):
        # iOS never fires beforeinstallprompt, so the button must not depend on it there.
        _, page = self.get('/')
        _, script = self.get('/chat.js')
        self.assertIn('id="ios-install"', page.decode())
        self.assertIn('Add to Home Screen', page.decode())
        self.assertIn("if (ios && !installed) $('#install').classList.remove('hidden');", script.decode())

    def test_voice_module_is_served_and_unavailable_mic_stays_explained(self):
        headers, body = self.get('/voice.js')
        self.assertEqual(headers['Content-Type'], 'text/javascript; charset=utf-8')
        self.assertIn('export function listen', body.decode())
        _, page = self.get('/')
        self.assertIn('<button id="mic" type="button" class="mic"', page.decode())
        self.assertIn('Web: Off', page.decode())
        _, script = self.get('/chat.js')
        self.assertIn('const voiceAvailable = voiceSupported && globalThis.isSecureContext !== false;', script.decode())
        self.assertIn("$('#mic').disabled = blocked || !voiceAvailable;", script.decode())
        self.assertIn('function syncWebButton()', script.decode())


@unittest.skipUnless(shutil.which('node'), 'Node is needed to run the voice module')
class VoiceCommandTests(unittest.TestCase):
    def test_spoken_commands_and_ordinary_questions(self):
        cases = {
            'New chat.': 'new-chat', 'Hey Oreo, start a new chat': 'new-chat',
            'Turn on web search': 'web-on', 'Turn web on.': 'web-on', 'switch off the web': 'web-off',
            'Open settings': 'settings', 'Read that again': 'repeat', 'Stop.': 'stop',
            'What is a new chat app?': None, 'How do I turn on web hosting?': None, 'Stop the war in poems': None,
        }
        script = ("const { command } = await import('./public/voice.js');"
                  "console.log(JSON.stringify(Object.fromEntries(JSON.parse(process.argv[1]).map(s => [s, command(s)]))));")
        result = subprocess.run(['node', '--input-type=module', '-e', script, json.dumps(list(cases))],
                                capture_output=True, text=True, cwd=Path(__file__).resolve().parent.parent, check=True)
        self.assertEqual(json.loads(result.stdout), cases)

    def test_cancelled_listening_discards_late_results_and_reports_mic_errors(self):
        script = r"""
          const { readFileSync } = await import('node:fs');
          const source = readFileSync('./public/voice.js', 'utf8');
          Object.defineProperty(globalThis, 'navigator', { value: { language: 'en-US' }, configurable: true });
          globalThis.SpeechRecognition = class {
            constructor() { globalThis.recognition = this; }
            start() {}
            abort() { this.aborted = true; }
          };
          const { listen } = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
          let transcript = '', completed = 0, error = '';
          const cancel = listen({ onText: value => transcript = value, onDone: () => completed++, onError: value => error = value });
          cancel();
          recognition.onresult({ results: [{ 0: { transcript: 'late words' } }] });
          recognition.onend();
          if (transcript || completed) throw new Error('cancelled recognition delivered a late result');
          listen({ onText() {}, onDone() {}, onError: value => error = value });
          recognition.onerror({ error: 'audio-capture' });
          recognition.onend();
          if (!error.includes('No microphone')) throw new Error('microphone failure was not explained');
        """
        result = subprocess.run(['node', '--input-type=module', '-e', script], capture_output=True,
                                text=True, cwd=Path(__file__).resolve().parent.parent)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
