"""Google Calendar OAuth2 인증 모듈.

처음 실행 시 URL이 출력됩니다. 해당 URL을 브라우저에서 열어
구글 계정으로 로그인한 후 발급되는 코드를 터미널에 붙여넣으세요.
이후 token.json에 저장되어 재인증 없이 사용됩니다.
"""
import os
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import GOOGLE_CREDENTIALS_PATH, GOOGLE_TOKEN_PATH

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


def get_calendar_service():
    creds = None

    if os.path.exists(GOOGLE_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(GOOGLE_CREDENTIALS_PATH):
                print(f'[오류] {GOOGLE_CREDENTIALS_PATH} 파일이 없습니다.')
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CREDENTIALS_PATH, SCOPES)
            # 로컬 서버 방식: URL 출력 → 브라우저에서 접속 → 자동 토큰 수신
            print('\n아래 URL을 브라우저에서 열어 구글 계정으로 로그인 후 권한을 허용해주세요.\n')
            creds = flow.run_local_server(port=0, open_browser=False)

        with open(GOOGLE_TOKEN_PATH, 'w') as f:
            f.write(creds.to_json())
        print(f'[인증] 토큰 저장: {GOOGLE_TOKEN_PATH}')

    return build('calendar', 'v3', credentials=creds)


if __name__ == '__main__':
    svc = get_calendar_service()
    calendars = svc.calendarList().list().execute()
    print('연결된 캘린더 목록:')
    for cal in calendars.get('items', []):
        print(f'  - {cal["summary"]} ({cal["id"]})')
