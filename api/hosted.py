"""Authenticated account and history endpoints."""

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

from api.conversations import conversation_id, database, activate_profile


class AccessError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def identity(headers):
    token = headers.get('Authorization', '').removeprefix('Bearer ').strip()
    if not token:
        raise AccessError(401, 'Please sign in.')
    request = urllib.request.Request(
        os.environ['SUPABASE_URL'].rstrip('/') + '/auth/v1/user',
        headers={'apikey': os.environ['SUPABASE_PUBLISHABLE_KEY'], 'Authorization': 'Bearer ' + token},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            user = json.load(response)
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
                today = datetime.now(timezone.utc).date().isoformat()
                rows = database(f"daily_usage?user_id=eq.{user['id']}&usage_date=eq.{today}&select=input_tokens,output_tokens")
                used = sum(rows[0].values()) if rows else 0
                self.reply(200, {'profile': profile, 'usage': {'date': today, 'used': used, 'remaining': max(0, profile['daily_token_limit'] - used)}})
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
