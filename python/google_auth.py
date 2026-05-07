"""Google Calendar OAuth2 인증 모듈 (requests 기반, SSL 우회 지원)."""
import json
import os
import sys
from datetime import datetime, timezone, timedelta

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from config import GOOGLE_TOKEN_PATH

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
_CAL_BASE = 'https://www.googleapis.com/calendar/v3'


def _load_token() -> dict:
    if not os.path.exists(GOOGLE_TOKEN_PATH):
        print('[오류] 인증이 필요합니다: python3 auth_manual.py url')
        sys.exit(1)
    with open(GOOGLE_TOKEN_PATH) as f:
        return json.load(f)


def _refresh_token(tok: dict) -> str:
    r = requests.post(
        'https://oauth2.googleapis.com/token',
        data={
            'client_id': tok['client_id'],
            'client_secret': tok['client_secret'],
            'refresh_token': tok['refresh_token'],
            'grant_type': 'refresh_token',
        },
        verify=False,
        timeout=30,
    )
    data = r.json()
    if 'access_token' not in data:
        raise RuntimeError(f'Token refresh failed: {data}')
    tok['token'] = data['access_token']
    tok['expiry'] = (
        datetime.now(timezone.utc) + timedelta(seconds=data.get('expires_in', 3600))
    ).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    with open(GOOGLE_TOKEN_PATH, 'w') as f:
        json.dump(tok, f)
    return data['access_token']


def _get_access_token() -> str:
    tok = _load_token()
    expiry_str = tok.get('expiry', '')
    if expiry_str:
        expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
        if expiry > datetime.now(timezone.utc):
            return tok['token']
    return _refresh_token(tok)


class _CalendarService:
    """requests 기반 Google Calendar API 래퍼."""

    def __init__(self, access_token: str):
        self._token = access_token
        self._headers = {'Authorization': f'Bearer {access_token}'}

    def _get(self, path: str, params: dict | None = None) -> dict:
        r = requests.get(
            f'{_CAL_BASE}{path}',
            headers=self._headers,
            params=params or {},
            verify=False,
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def calendarList(self):
        return self

    def list(self):
        return self

    def execute(self):
        return self._get('/users/me/calendarList')

    def calendars(self):
        return _CalendarsResource(self)

    def events(self):
        return _EventsResource(self)


class _CalendarsResource:
    def __init__(self, svc: _CalendarService):
        self._svc = svc

    def get(self, calendarId: str):
        return _Request(self._svc, f'/calendars/{calendarId}')


class _EventsResource:
    def __init__(self, svc: _CalendarService):
        self._svc = svc

    def list(self, calendarId: str, **params):
        return _Request(self._svc, f'/calendars/{calendarId}/events', params)


class _Request:
    def __init__(self, svc: _CalendarService, path: str, params: dict | None = None):
        self._svc = svc
        self._path = path
        self._params = params or {}

    def execute(self):
        return self._svc._get(self._path, self._params)


def get_calendar_service() -> _CalendarService:
    token = _get_access_token()
    return _CalendarService(token)
