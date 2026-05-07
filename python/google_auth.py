"""Google Calendar OAuth2 인증 모듈."""
import json
import os
import sys
from datetime import datetime, timezone, timedelta

import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config import GOOGLE_TOKEN_PATH

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


def _refresh_token_file() -> None:
    """google-auth 라이브러리 우회 — 직접 HTTP로 토큰 갱신."""
    with open(GOOGLE_TOKEN_PATH) as f:
        tok = json.load(f)

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


def get_calendar_service():
    if not os.path.exists(GOOGLE_TOKEN_PATH):
        print('[오류] 인증이 필요합니다: python3 auth_manual.py url')
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            _refresh_token_file()
            creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_PATH, SCOPES)
        else:
            print('[오류] 인증이 필요합니다: python3 auth_manual.py url')
            sys.exit(1)

    return build('calendar', 'v3', credentials=creds, cache_discovery=False)
