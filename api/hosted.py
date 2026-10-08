"""Authenticated account and history endpoints."""

import os
import urllib.error
from urllib.parse import parse_qs, urlsplit

from api.conversations import conversation_id, database, activate_profile
from api.network import cached_user, request_json


class AccessError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def identity(headers):
    token = headers.get('Authorization', '').removeprefix('Bearer ').strip()
    if not token:
        raise AccessError(401, 'Please sign in.')
    try:
        user = cached_user(
            token,
            os.environ['SUPABASE_URL'].rstrip('/') + '/auth/v1/user',
            {'apikey': os.environ['SUPABASE_PUBLISHABLE_KEY'], 'Authorization': 'Bearer ' + token},
            request_json,
        )
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise AccessError(401, 'Your sign-in has expired. Please sign in again.') from error
        raise
    try:
        profile = activate_profile(user['id'])
    except LookupError as error:
        raise AccessError(503, str(error)) from error
    return user, profile


class HostedHandler:
    def hosted_GET(self, route):
        try:
            user, profile = identity(self.headers)
            if route == '/api/profile':
                self.reply(200, {'profile': profile, 'unlimited': True})
            else:
                query = parse_qs(urlsplit(self.path).query)
                if 'id' not in query:
                    rows = database(f"conversations?user_id=eq.{user['id']}&select=id,title,updated_at&order=updated_at.desc&limit=100")
                    self.reply(200, {'conversations': rows})
                else:
                    chat_id = conversation_id(query['id'][0])
                    rows = database(f"conversations?id=eq.{chat_id}&user_id=eq.{user['id']}&select=id,title,updated_at")
                    if not rows:
                        raise AccessError(404, 'Conversation not found.')
                    messages = database(f'messages?conversation_id=eq.{chat_id}&select=role,content,created_at&order=created_at.asc,id.asc&limit=1000')
                    self.reply(200, {'conversation': rows[0], 'messages': messages})
        except AccessError as error:
            self.reply(error.status, {'error': error.message})
        except (ValueError, TypeError, AttributeError):
            self.reply(400, {'error': 'Send a valid conversation ID.'})
        except Exception:
            self.reply(503, {'error': 'Oreo is unavailable right now. Try again shortly.'})


    def hosted_DELETE(self, route):
        try:
            user, _profile = identity(self.headers)
            query = parse_qs(urlsplit(self.path).query)
            if 'id' not in query:
                raise AccessError(400, 'Choose a conversation to delete.')
            chat_id = conversation_id(query['id'][0])
            rows = database(
                f"conversations?id=eq.{chat_id}&user_id=eq.{user['id']}&select=id",
                'DELETE',
            )
            if not rows:
                raise AccessError(404, 'Conversation not found.')
            self.reply(200, {'deleted': True, 'id': chat_id})
        except AccessError as error:
            self.reply(error.status, {'error': error.message})
        except (ValueError, TypeError, AttributeError):
            self.reply(400, {'error': 'Send a valid conversation ID.'})
        except Exception:
            self.reply(503, {'error': 'Oreo is unavailable right now. Try again shortly.'})
