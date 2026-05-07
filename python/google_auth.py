"""Google Calendar OAuth2 인증 모듈."""
import json
import os
import sys
from datetime import datetime, timezone, timedelta

from googleapiclient.discovery import build

from config import GOOGLE_TOKEN_PATH

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

_IN_GITHUB_ACTIONS = os.environ.get('GITHUB_ACTIONS') == 'true'


def _get_creds_github():
    """GitHub Actions: Workload Identity Federation via ADC."""
    import google.auth
    creds, _ = google.auth.default(scopes=SCOPES)
    return creds


def _get_creds_local():
    """로컬: token.json에서 읽고 만료 시 직접 HTTP로 갱신."""
    import requests
    from google.oauth2.credentials import Credentials

    if not os.path.exists(GOOGLE_TOKEN_PATH):
        print('[오류] 인증이 필요합니다: python3 auth_manual.py url')
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
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
            creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_PATH, SCOPES)
        else:
            print('[오류] 인증이 필요합니다: python3 auth_manual.py url')
            sys.exit(1)

    return creds


def get_calendar_service():
    creds = _get_creds_github() if _IN_GITHUB_ACTIONS else _get_creds_local()
    return build('calendar', 'v3', credentials=creds, cache_discovery=False)
