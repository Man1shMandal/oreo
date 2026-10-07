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

    @patch('api.chat.handler.search_web')
    def test_quota_rejected_web_chat_does_not_search(self, search):
        self.prepare.return_value = ([], {'error': 'limit'})
        self.assertEqual(self.post({'message': 'search', 'web': True})[0], 429)
        search.assert_not_called()

    @patch('api.chat.handler.search_web', return_value=[{'title': 'Source', 'url': 'https://example.com', 'text': 'Fresh fact'}])
    def test_web_sources_are_saved(self, search):
        self.assertEqual(self.post({'message': 'search', 'web': True})[0], 200)
        self.assertEqual(unpack(self.save.call_args.args[3])['sources'][0]['url'], 'https://example.com')
        self.assertEqual(self.prepare.call_args.kwargs['extra_tokens'], 4000)

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

    def test_stream_save_failure_is_an_error(self):
        self.client.return_value.chat.completions.create.return_value = iter([SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content='reply'))])])
        self.save.side_effect = RuntimeError('database unavailable')
        events = self.stream_post()
        self.assertIn('error', events[-1]); self.assertFalse(events[-1]['done'])

    @patch('api.conversations.database')
    def test_document_survives_reopened_followup(self, database):
        document = pack('Read this', documents=['<file path="notes.txt">\n' + 'x' * 12000 + '\n</file>'], files=[{'name': 'notes.txt'}])
        database.side_effect = [[{'id': CHAT}], [{'role': 'assistant', 'content': 'OK'}, {'role': 'user', 'content': document}], {'conversation_id': CHAT}]
        messages, _ = conversations.prepare(USER, CHAT, 'What was in the file?')
        self.assertIn('x' * 12000, messages[1]['content'])

    @patch('api.conversations.database')
    def test_image_survives_reopened_followup(self, database):
        writer = PdfWriter(); writer.add_blank_page(width=100, height=100); output = io.BytesIO(); writer.write(output)
        image = pack('Look', images=[{'type': 'input_file', 'file_data': base64.b64encode(output.getvalue()).decode(), 'filename': 'x.pdf'}])
        database.side_effect = [[{'id': CHAT}], [{'role': 'assistant', 'content': 'OK'}, {'role': 'user', 'content': image}], {'conversation_id': CHAT}]
        messages, _ = conversations.prepare(USER, CHAT, 'What color?')
        self.assertEqual(messages[1]['content'][1]['type'], 'input_file')
        self.assertGreater(database.call_args.args[2]['p_input'], 1800)


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
