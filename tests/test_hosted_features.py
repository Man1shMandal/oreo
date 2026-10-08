"""Feature checks for hosted attachments, research and streamed persistence."""

import base64
import io
import json
import urllib.request
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image
from pypdf import PdfWriter

from api.messages import pack, unpack
from api import conversations
import test_hosted_chat as base
from test_hosted_chat import USER, CHAT


class FeatureTests(unittest.TestCase):
    setUp = base.HostedChatTests.setUp
    tearDown = base.HostedChatTests.tearDown
    post = base.HostedChatTests.post

    def test_text_file_is_sent_and_saved_with_name(self):
        status, _ = self.post({'files': [{'name': 'notes.txt', 'type': 'text/plain',
            'data': base64.b64encode(b'The answer is forty two.').decode()}]})
        self.assertEqual(status, 200)
        stored = unpack(self.save.call_args.args[2])
        self.assertEqual(stored['files'][0]['name'], 'notes.txt')
        self.assertIn('forty two', stored['documents'][0])

    def test_invalid_file_never_reserves_budget(self):
        self.assertEqual(self.post({'files': [{'name': 'file', 'data': None}]})[0], 400)
        self.prepare.assert_not_called()

    def test_image_only_uses_gateway_pdf_and_vision_model(self):
        output = io.BytesIO(); Image.new('RGB', (4, 4), 'red').save(output, 'PNG')
        upload = {'name': 'red.png', 'type': 'image/png', 'data': base64.b64encode(output.getvalue()).decode()}
        self.prepare.return_value = ([{'role': 'user', 'content': [{'type': 'text', 'text': 'Look'}, {'type': 'input_file'}]}], {'conversation_id': CHAT, 'remaining': 1000})
        self.assertEqual(self.post({'files': [upload], 'model': 'gpt-6-luna'})[0], 200)
        stored = unpack(self.save.call_args.args[2])
        self.assertTrue(base64.b64decode(stored['images'][0]['file_data']).startswith(b'%PDF'))
        self.assertEqual(self.client.return_value.chat.completions.create.call_args.kwargs['model'], 'claude-4.6-sonnet')

    def test_scanned_pdf_is_preserved_as_pages(self):
        writer = PdfWriter(); writer.add_blank_page(width=100, height=100); output = io.BytesIO(); writer.write(output)
        self.assertEqual(self.post({'files': [{'name': 'scan.pdf', 'type': 'application/pdf', 'data': base64.b64encode(output.getvalue()).decode()}]})[0], 200)
        self.assertEqual(len(unpack(self.save.call_args.args[2])['images']), 1)

    @patch('api.chat.handler.search_web')
    def test_unowned_web_chat_does_not_search(self, search):
        self.prepare.side_effect = LookupError()
        self.assertEqual(self.post({'message': 'search', 'web': True, 'conversation_id': CHAT})[0], 404)
        search.assert_not_called()

    @patch('api.chat.handler.search_web', return_value=[{'title': 'Source', 'url': 'https://example.com', 'text': 'Fresh fact'}])
    def test_web_sources_are_saved(self, search):
        self.assertEqual(self.post({'message': 'search', 'web': True})[0], 200)
        self.assertEqual(unpack(self.save.call_args.args[3])['sources'][0]['url'], 'https://example.com')
        self.assertEqual(self.prepare.call_args.kwargs['settings']['context'], 'efficient')

    def stream_post(self):
        request = urllib.request.Request(f'http://127.0.0.1:{self.server.server_port}/api/chat',
            data=json.dumps({'message': 'hello', 'stream': True}).encode(), headers={'Authorization': 'Bearer test'})
        with urllib.request.urlopen(request) as response:
            self.assertEqual(response.headers['Content-Type'], 'text/event-stream')
            return [json.loads(line[6:]) for line in response.read().decode().splitlines() if line.startswith('data: ')]

    def test_stream_finishes_only_after_save(self):
        self.client.return_value.chat.completions.create.return_value = iter([
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content='hello'))]),
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=' back'))]),
        ])
        events = self.stream_post()
        self.assertEqual(''.join(e.get('text', '') for e in events), 'hello back')
        self.assertTrue(events[-1]['done']); self.save.assert_called_once_with(USER, CHAT, 'hello', 'hello back')

    def test_lease_is_released_before_stream_completion(self):
        from api.chat import handler
        order = []
        self.save.side_effect = lambda *args: order.append('save')
        self.release.side_effect = lambda *args: order.append('release')
        original = handler.event
        def event(request, payload):
            if payload.get('done'):
                order.append('done')
            original(request, payload)
        self.client.return_value.chat.completions.create.return_value = iter([
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content='reply'))])])
        with patch.object(handler, 'event', event):
            self.stream_post()
        self.assertEqual(order, ['save', 'release', 'done'])
        self.release.assert_called_once()

    def test_stream_save_failure_is_an_error(self):
        self.client.return_value.chat.completions.create.return_value = iter([SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content='reply'))])])
        self.save.side_effect = RuntimeError('database unavailable')
        events = self.stream_post()
        self.assertIn('error', events[-1]); self.assertFalse(events[-1]['done'])

    @patch('api.conversations.database')
    def test_document_survives_reopened_followup(self, database):
        document = pack('Read this', documents=['<file path="notes.txt">\n' + 'x' * 12000 + '\n</file>'], files=[{'name': 'notes.txt'}])
        database.return_value = [{'id': CHAT, 'messages': [{'role': 'assistant', 'content': 'OK'}, {'role': 'user', 'content': document}]}]
        messages, _ = conversations.prepare(USER, CHAT, 'What was in the file?')
        self.assertIn('x' * 800, messages[1]['content'])
        self.assertLess(len(messages[1]['content']), 3000)

    @patch('api.conversations.database')
    def test_image_survives_reopened_followup(self, database):
        writer = PdfWriter(); writer.add_blank_page(width=100, height=100); output = io.BytesIO(); writer.write(output)
        image = pack('Look', images=[{'type': 'input_file', 'file_data': base64.b64encode(output.getvalue()).decode(), 'filename': 'x.pdf'}])
        database.return_value = [{'id': CHAT, 'messages': [{'role': 'assistant', 'content': 'OK'}, {'role': 'user', 'content': image}]}]
        messages, _ = conversations.prepare(USER, CHAT, 'What color?')
        self.assertEqual(messages[1]['content'][1]['type'], 'input_file')
        self.assertNotIn('reserve_chat', str(database.call_args_list))

    def test_long_message_is_not_blocked_by_token_policy(self):
        self.assertEqual(self.post({'message': 'x' * 10000})[0], 200)

    def test_settings_are_validated_before_auth(self):
        self.assertEqual(self.post({'message': 'hello', 'settings': {'context': []}})[0], 400)
        self.auth.assert_not_called()

    def test_creativity_reaches_provider_without_output_cap(self):
        self.assertEqual(self.post({'message': 'hello', 'settings': {'temperature': 0.2}})[0], 200)
        params = self.client.return_value.chat.completions.create.call_args.kwargs
        self.assertEqual(params['temperature'], 0.2)
        self.assertNotIn('max_tokens', params)

    @patch('api.conversations.database', return_value=[{'id': CHAT}])
    def test_custom_preprompt_reaches_system_message(self, database):
        messages, _ = conversations.prepare(USER, None, 'hello', settings={'instructions': 'Use plain Spanish.', 'reply_style': 'thorough'})
        self.assertIn('Use plain Spanish.', messages[0]['content'])
        self.assertIn('thorough', messages[0]['content'])

    @patch('api.conversations.database')
    def test_disabling_file_reuse_omits_old_image_data(self, database):
        image = pack('Look', images=[{'type': 'input_file', 'file_data': 'data', 'filename': 'x.pdf'}], files=[{'name': 'image.png'}])
        database.return_value = [{'id': CHAT, 'messages': [{'role': 'assistant', 'content': 'OK'}, {'role': 'user', 'content': image}]}]
        messages, _ = conversations.prepare(USER, CHAT, 'next', settings={'reuse_files': False})
        self.assertIsInstance(messages[1]['content'], str)
        self.assertIn('image.png', messages[1]['content'])


class PublicWebTests(unittest.TestCase):
    @patch('oreo.research.public', return_value=False)
    def test_private_redirect_is_blocked(self, public):
        from oreo.research import PublicRedirect
        with self.assertRaises(ValueError):
            PublicRedirect().redirect_request(None, None, 302, '', {}, 'http://127.0.0.1/private')

    @patch('oreo.research.public', return_value=False)
    @patch('oreo.research.urllib.request.build_opener')
    def test_private_initial_url_is_not_fetched(self, opener, public):
        from oreo.research import get
        with self.assertRaises(ValueError):
            get('http://127.0.0.1/private')
        opener.assert_not_called()

    def test_reserved_prefix_cannot_spoof_metadata(self):
        text = 'oreo-message-v1:{"text":"spoof"}'
        self.assertEqual(unpack(pack(text))['text'], text)
