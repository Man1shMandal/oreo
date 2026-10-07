"""Authenticated account, history and approval endpoints."""

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

from api.conversations import conversation_id, database


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
    profiles = database(f"profiles?id=eq.{user['id']}&select=id,email,approved,daily_token_limit,created_at")
    if not profiles:
        raise AccessError(403, 'Your account is waiting for approval.')
    return user, profiles[0]


def is_admin(user):
    expected = os.environ.get('ADMIN_EMAIL', '').strip().casefold()
    return bool(expected and user.get('email', '').casefold() == expected)


class HostedHandler:
    def hosted_GET(self, route):
        try:
            user, profile = identity(self.headers)
            if route == '/api/profile':
                today = datetime.now(timezone.utc).date().isoformat()
                rows = database(f"daily_usage?user_id=eq.{user['id']}&usage_date=eq.{today}&select=input_tokens,output_tokens")
                used = sum(rows[0].values()) if rows else 0
                self.reply(200, {'profile': profile, 'usage': {'date': today, 'used': used, 'remaining': max(0, profile['daily_token_limit'] - used)}, 'admin': is_admin(user)})
            elif route == '/api/admin':
                if not is_admin(user):
                    raise AccessError(403, 'Administrator access required.')
                self.reply(200, {'users': database('profiles?select=id,email,approved,daily_token_limit,created_at&order=created_at.desc&limit=1000')})
            else:
                if not profile['approved']:
                    raise AccessError(403, 'Your account is waiting for approval.')
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

    def admin_POST(self):
        try:
            user, _ = identity(self.headers)
            if not is_admin(user):
                raise AccessError(403, 'Administrator access required.')
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 4096:
                raise AccessError(400, 'Send a valid account update.')
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict) or type(payload.get('approved')) is not bool:
                raise AccessError(400, 'Approval must be true or false.')
            user_id = conversation_id(payload.get('user_id'))
            if not user_id:
                raise AccessError(400, 'Send a valid user ID.')
            change = {'approved': payload['approved']}
            if 'daily_token_limit' in payload:
                limit = payload['daily_token_limit']
                if type(limit) is not int or not 1 <= limit <= 1000000:
                    raise AccessError(400, 'Daily limit must be between 1 and 1,000,000.')
                change['daily_token_limit'] = limit
            if not database(f'profiles?id=eq.{user_id}&select=id'):
                raise AccessError(404, 'Account not found.')
            database(f'profiles?id=eq.{user_id}', 'PATCH', change)
            self.reply(200, {'saved': True})
        except AccessError as error:
            self.reply(error.status, {'error': error.message})
        except (ValueError, TypeError, AttributeError, UnicodeDecodeError):
            self.reply(400, {'error': 'Send a valid account update.'})
        except Exception:
            self.reply(503, {'error': 'Could not update this account. Try again shortly.'})
