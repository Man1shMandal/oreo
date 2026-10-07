"""Account and history authorization checks with a fake database."""

import io
import json
import os
import unittest
from unittest.mock import patch

from api.hosted import HostedHandler, is_admin

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
            {'id': USER, 'approved': True, 'daily_token_limit': 20000},
        )).start()
        self.database = patch('api.hosted.database', return_value=[]).start()
        self.env = patch.dict(os.environ, {'ADMIN_EMAIL': 'admin@example.test'}).start()
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

    def test_pending_account_cannot_read_history(self):
        self.identity.return_value[1]['approved'] = False
        request = Request()
        request.hosted_GET('/api/conversations')
        self.assertEqual(request.result[0], 403)
        self.database.assert_not_called()

    def test_non_admin_cannot_read_accounts(self):
        request = Request()
        request.hosted_GET('/api/admin')
        self.assertEqual(request.result[0], 403)
        self.database.assert_not_called()

    def test_non_admin_cannot_approve_accounts(self):
        request = Request(payload={'user_id': OTHER, 'approved': True})
        request.admin_POST()
        self.assertEqual(request.result[0], 403)
        self.database.assert_not_called()

    def test_admin_approval_writes_only_validated_fields(self):
        self.identity.return_value[0]['email'] = 'admin@example.test'
        self.database.side_effect = [[{'id': OTHER}], None]
        request = Request(payload={'user_id': OTHER, 'approved': True,
                                   'daily_token_limit': 1000, 'email': 'ignored@example.test'})
        request.admin_POST()
        self.assertEqual(request.result[0], 200)
        self.assertEqual(self.database.call_args.args, (
            'profiles?id=eq.' + OTHER, 'PATCH', {'approved': True, 'daily_token_limit': 1000},
        ))

    def test_admin_rejects_boolean_or_out_of_range_limits(self):
        self.identity.return_value[0]['email'] = 'admin@example.test'
        for limit in [True, 0, -1, 1000001, '1000']:
            with self.subTest(limit=limit):
                request = Request(payload={'user_id': OTHER, 'approved': True, 'daily_token_limit': limit})
                request.admin_POST()
                self.assertEqual(request.result[0], 400)
        self.database.assert_not_called()

    def test_unconfigured_admin_email_never_grants_access(self):
        with patch.dict(os.environ, {'ADMIN_EMAIL': ''}):
            self.assertFalse(is_admin({'email': ''}))

    def test_usage_uses_owner_and_reports_nonnegative_remaining(self):
        self.database.return_value = [{'input_tokens': 20000, 'output_tokens': 1000}]
        request = Request()
        request.hosted_GET('/api/profile')
        self.assertEqual(request.result[1]['usage']['remaining'], 0)
        self.assertIn('user_id=eq.' + USER, self.database.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
