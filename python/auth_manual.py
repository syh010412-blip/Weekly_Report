"""Google OAuth2 인증 — 원격/브라우저 없는 환경용.

사용법:
  python3 auth_manual.py url     # 인증 URL 출력
  python3 auth_manual.py token <붙여넣은 URL>  # 토큰 저장
"""
import json
import sys
import os
import requests
from urllib.parse import urlparse, parse_qs, urlencode

CREDENTIALS_PATH = 'credentials.json'
TOKEN_PATH = 'token.json'
SCOPE = 'https://www.googleapis.com/auth/calendar.readonly'
REDIRECT_URI = 'http://localhost'


def load_client():
    with open(CREDENTIALS_PATH) as f:
        data = json.load(f)
    info = data.get('installed') or data.get('web')
    return info['client_id'], info['client_secret']


def get_url():
    client_id, _ = load_client()
    params = {
        'client_id': client_id,
        'redirect_uri': REDIRECT_URI,
        'scope': SCOPE,
        'response_type': 'code',
        'access_type': 'offline',
        'prompt': 'consent',
    }
    url = 'https://accounts.google.com/o/oauth2/auth?' + urlencode(params)
    print('\n' + '=' * 60)
    print('  [1단계] 아래 URL을 브라우저에서 여세요')
    print('=' * 60)
    print(f'\n{url}\n')
    print('[2단계] 구글 계정 로그인 → "허용" 클릭')
    print('[3단계] 브라우저 주소창에 "localhost 연결 불가" 오류가 뜹니다.')
    print('        괜찮습니다! 주소창의 URL을 전체 복사하세요.')
    print('        (http://localhost/?code=4/0Ac... 형태)\n')
    print('[4단계] 아래 명령어 실행:')
    print('  python3 auth_manual.py token "복사한_URL_붙여넣기"\n')


def save_token(redirect_url: str):
    client_id, client_secret = load_client()

    parsed = urlparse(redirect_url)
    params = parse_qs(parsed.query)
    code = params.get('code', [None])[0]
    if not code:
        print('[오류] URL에서 code를 찾을 수 없습니다.')
        print('http://localhost/?code=... 형태의 전체 URL을 붙여넣어 주세요.')
        sys.exit(1)

    resp = requests.post('https://oauth2.googleapis.com/token', data={
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'grant_type': 'authorization_code',
    })
    token_data = resp.json()

    if 'error' in token_data:
        print(f'[오류] 토큰 교환 실패: {token_data}')
        sys.exit(1)

    # google-auth 형식으로 저장
    creds_json = {
        'token': token_data.get('access_token'),
        'refresh_token': token_data.get('refresh_token'),
        'token_uri': 'https://oauth2.googleapis.com/token',
        'client_id': client_id,
        'client_secret': client_secret,
        'scopes': [SCOPE],
    }
    with open(TOKEN_PATH, 'w') as f:
        json.dump(creds_json, f, indent=2)

    print(f'\n✅ 인증 완료! {TOKEN_PATH} 저장됨')

    # 캘린더 목록 확인
    headers = {'Authorization': f'Bearer {token_data["access_token"]}'}
    r = requests.get('https://www.googleapis.com/calendar/v3/users/me/calendarList', headers=headers)
    cals = r.json().get('items', [])
    print(f'\n연결된 캘린더 ({len(cals)}개):')
    for cal in cals:
        print(f'  - {cal["summary"]}')


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] == 'url':
        get_url()
    elif sys.argv[1] == 'token' and len(sys.argv) >= 3:
        save_token(sys.argv[2])
    else:
        print('사용법:')
        print('  python3 auth_manual.py url')
        print('  python3 auth_manual.py token "http://localhost/?code=..."')
