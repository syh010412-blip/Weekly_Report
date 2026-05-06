"""Google Calendar OAuth2 인증 모듈."""
import os
import ssl
import sys

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

import httplib2
import google.auth.transport.requests as google_requests
import requests as req_lib
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import build
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

from config import GOOGLE_CREDENTIALS_PATH, GOOGLE_TOKEN_PATH

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


class _NoSSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = ctx
        super().init_poolmanager(*args, **kwargs)


def _requests_session() -> req_lib.Session:
    s = req_lib.Session()
    s.mount('https://', _NoSSLAdapter())
    s.verify = False
    return s


def _refresh_creds(creds: Credentials) -> Credentials:
    req = google_requests.Request(session=_requests_session())
    creds.refresh(req)
    return creds


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

    # httplib2로 SSL 검증 비활성화
    http = httplib2.Http(disable_ssl_certificate_validation=True)
    authed_http = AuthorizedHttp(creds, http=http)
    return build('calendar', 'v3', http=authed_http, cache_discovery=False)
