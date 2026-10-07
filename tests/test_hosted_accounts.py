"""Account and history authorization checks with a fake database."""

import io
import json
import os
import unittest
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


if __name__ == '__main__':
    unittest.main()
