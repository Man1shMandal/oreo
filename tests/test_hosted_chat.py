"""Hosted release checks without a real model or user data."""

import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from http.server import HTTPServer
from types import SimpleNamespace
from unittest.mock import patch

from api.chat import handler
from api import conversations


USER = "00000000-0000-0000-0000-000000000001"
CHAT = "00000000-0000-0000-0000-000000000002"


class HostedChatTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            'SUPABASE_PUBLISHABLE_KEY': 'test', 'SUPABASE_SECRET_KEY': 'test', 'ABBY_API_KEY': 'test',
        })
        self.env.start()
        self.server = HTTPServer(('127.0.0.1', 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.auth = patch('api.chat.request_json', return_value={'id': USER}).start()
        self.activate = patch('api.chat.activate_profile', return_value={'id': USER}).start()
        self.acquire = patch('api.chat.acquire', return_value={'lease': CHAT}).start()
        self.release = patch('api.chat.release').start()
        self.prepare = patch('api.chat.prepare', return_value=(
            [{'role': 'user', 'content': 'hello'}], {'conversation_id': CHAT, 'remaining': 1000},
        )).start()
        self.save = patch('api.chat.save_turn').start()
        self.client = patch('api.chat.OpenAI').start()
        self.client.return_value.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='hello back'))],
        )

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        patch.stopall()

    def post(self, payload, token='test'):
        request = urllib.request.Request(
            f'http://127.0.0.1:{self.server.server_port}/api/chat',
            data=json.dumps(payload).encode(),
            headers={'Authorization': f'Bearer {token}' if token else ''},
        )
        try:
            response = urllib.request.urlopen(request)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.code, json.load(response)

    def test_saves_turn_and_returns_chat_id(self):
        status, data = self.post({'message': 'hello'})
        self.assertEqual(status, 200)
        self.assertEqual(data['conversation_id'], CHAT)
        self.save.assert_called_once_with(USER, CHAT, 'hello', 'hello back')

    def test_no_auth_does_not_call_model(self):
        self.assertEqual(self.post({'message': 'hello'}, token='')[0], 401)
        self.client.assert_not_called()

    def test_invalid_conversation_does_not_call_model(self):
        self.assertEqual(self.post({'message': 'hello', 'conversation_id': []})[0], 400)
        self.client.assert_not_called()

    def test_other_users_conversation_does_not_call_model(self):
        self.prepare.side_effect = LookupError()
        self.assertEqual(self.post({'message': 'hello', 'conversation_id': CHAT})[0], 404)
        self.client.assert_not_called()

    def test_empty_reply_is_not_saved(self):
        self.client.return_value.chat.completions.create.return_value.choices[0].message.content = ''
        self.assertEqual(self.post({'message': 'hello'})[0], 502)
        self.save.assert_not_called()

    def test_model_failure_is_not_saved(self):
        self.client.return_value.chat.completions.create.side_effect = RuntimeError('upstream')
        self.assertEqual(self.post({'message': 'hello'})[0], 500)
        self.save.assert_not_called()
        self.release.assert_called_once_with(USER, CHAT)

    def test_busy_request_does_not_reserve_or_release_another_lease(self):
        self.acquire.return_value = {'error': 'busy'}
        self.assertEqual(self.post({'message': 'hello'})[0], 409)
        self.prepare.assert_not_called()
        self.client.assert_not_called()
        self.release.assert_not_called()

    def test_every_signed_in_account_is_automatically_enabled(self):
        self.assertEqual(self.post({'message': 'hello'})[0], 200)
        self.activate.assert_called_once_with(USER)

    def test_legacy_pending_account_can_chat_immediately(self):
        with patch('api.chat.activate_profile', conversations.activate_profile), patch('api.conversations.database') as database:
            database.side_effect = [[{'id': USER, 'approved': False, 'daily_token_limit': 20000}], None]
            self.assertEqual(self.post({'message': 'hello'})[0], 200)
            self.assertEqual(database.call_args.args, ('profiles?id=eq.' + USER, 'PATCH', {'approved': True}))
            self.acquire.assert_called_once_with(USER)
            self.save.assert_called_once_with(USER, CHAT, 'hello', 'hello back')

    def test_missing_profile_does_not_reserve_budget(self):
        self.activate.side_effect = LookupError('Account setup is incomplete.')
        self.assertEqual(self.post({'message': 'hello'})[0], 503)
        self.prepare.assert_not_called()

    def test_expired_token_does_not_reserve_budget(self):
        self.auth.side_effect = urllib.error.HTTPError('https://auth.invalid', 401, 'expired', {}, None)
        self.assertEqual(self.post({'message': 'hello'})[0], 401)
        self.prepare.assert_not_called()

    def test_invalid_messages_do_not_touch_auth(self):
        for message in ['', '   ', None, [], 1]:
            with self.subTest(message_type=type(message).__name__):
                self.assertEqual(self.post({'message': message})[0], 400)
        self.auth.assert_not_called()

    def test_save_failure_is_not_reported_as_success(self):
        self.save.side_effect = RuntimeError('database unavailable')
        status, data = self.post({'message': 'hello'})
        self.assertEqual(status, 500)
        self.assertNotIn('reply', data)

    def test_provider_receives_prepared_context_and_output_cap(self):
        self.post({'message': 'hello'})
        kwargs = self.client.return_value.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs['messages'], self.prepare.return_value[0])
        self.assertNotIn('max_tokens', kwargs)


class ContextTests(unittest.TestCase):
    @patch('api.conversations.database')
    def test_history_is_ordered_and_owned(self, database):
        database.side_effect = [[{'id': CHAT}], [
            {'role': 'assistant', 'content': 'previous answer'},
            {'role': 'user', 'content': 'previous question'},
        ]]
        messages, result = conversations.prepare(USER, CHAT, 'next question')
        self.assertEqual([m['role'] for m in messages], ['system', 'user', 'assistant', 'user'])
        self.assertEqual(messages[1]['content'], 'previous question')
        self.assertTrue(result['unlimited'])
        self.assertFalse(any('reserve_chat' in str(call) or 'daily_usage' in str(call) for call in database.call_args_list))

    @patch('api.conversations.database', return_value=[])
    def test_unowned_history_is_never_read(self, database):
        with self.assertRaises(LookupError):
            conversations.prepare(USER, CHAT, 'hello')
        self.assertEqual(database.call_count, 1)

    @patch('api.conversations.database', return_value=[{'id': CHAT}])
    def test_new_chat_has_no_daily_quota(self, database):
        messages, result = conversations.prepare(USER, None, 'hello')
        self.assertEqual(len(messages), 2)
        database.assert_called_once_with('conversations', 'POST', {'user_id': USER, 'title': 'hello'})
        self.assertEqual(result, {'conversation_id': CHAT, 'unlimited': True})

    @patch('api.conversations.database')
    def test_context_drops_incomplete_oversize_older_turns(self, database):
        database.side_effect = [[{'id': CHAT}], [
            {'role': 'assistant', 'content': 'latest reply'},
            {'role': 'user', 'content': 'latest question'},
            {'role': 'assistant', 'content': 'orphan reply'},
            {'role': 'user', 'content': 'x' * 6001},
        ]]
        messages, _ = conversations.prepare(USER, CHAT, 'next')
        self.assertEqual([m['content'] for m in messages[1:]], ['latest question', 'latest reply', 'next'])

    @patch('api.conversations.database')
    def test_atomic_save_supplies_authenticated_owner(self, database):
        conversations.save_turn(USER, CHAT, 'question', 'answer')
        database.assert_called_once_with('rpc/save_chat_turn', 'POST', {
            'p_user': USER, 'p_conversation': CHAT, 'p_message': 'question', 'p_reply': 'answer',
        })


class ProfileCompatibilityTests(unittest.TestCase):
    @patch('api.conversations.database')
    def test_legacy_pending_account_is_enabled_without_manual_approval(self, database):
        database.side_effect = [[{'id': USER, 'approved': False, 'daily_token_limit': 20000}], None]
        profile = conversations.activate_profile(USER)
        self.assertNotIn('approved', profile)
        self.assertEqual(database.call_args.args, ('profiles?id=eq.' + USER, 'PATCH', {'approved': True}))

    @patch('api.conversations.database')
    def test_existing_account_does_not_need_another_write(self, database):
        database.return_value = [{'id': USER, 'approved': True, 'daily_token_limit': 20000}]
        profile = conversations.activate_profile(USER)
        self.assertNotIn('daily_token_limit', profile)
        self.assertNotIn('approved', profile)
        self.assertEqual(database.call_count, 1)


if __name__ == '__main__':
    unittest.main()
