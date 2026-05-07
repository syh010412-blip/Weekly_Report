"""Google Calendar OAuth2 인증 모듈."""
import os
import sys

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config import GOOGLE_TOKEN_PATH

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

_IN_GITHUB_ACTIONS = os.environ.get('GITHUB_ACTIONS') == 'true'


def _get_ssl_session():
    import ssl
    import urllib3
    import requests as req_lib
    from requests.adapters import HTTPAdapter
    from urllib3.util.ssl_ import create_urllib3_context

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    ssl._create_default_https_context = ssl._create_unverified_context

    class _NoSSLAdapter(HTTPAdapter):
        def init_poolmanager(self, *args, **kwargs):
            ctx = create_urllib3_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            kwargs['ssl_context'] = ctx
            super().init_poolmanager(*args, **kwargs)

    s = req_lib.Session()
    s.mount('https://', _NoSSLAdapter())
    s.verify = False
    return s


def _refresh_creds(creds: Credentials) -> None:
    if _IN_GITHUB_ACTIONS:
        from google.auth.transport.requests import Request
        creds.refresh(Request())
    else:
        import google.auth.transport.requests as google_requests
        creds.refresh(google_requests.Request(session=_get_ssl_session()))


def get_calendar_service():
    creds = None

    if os.path.exists(GOOGLE_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            _refresh_creds(creds)
            with open(GOOGLE_TOKEN_PATH, 'w') as f:
                f.write(creds.to_json())
        else:
            print('[오류] 인증이 필요합니다: python3 auth_manual.py url')
            sys.exit(1)

    if _IN_GITHUB_ACTIONS:
        return build('calendar', 'v3', credentials=creds, cache_discovery=False)

    import httplib2
    from google_auth_httplib2 import AuthorizedHttp
    http = httplib2.Http(disable_ssl_certificate_validation=True)
    authed_http = AuthorizedHttp(creds, http=http)
    return build('calendar', 'v3', http=authed_http, cache_discovery=False)
