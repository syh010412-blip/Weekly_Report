#!/bin/bash
# 주간 리포트 자동화 초기 세팅 스크립트

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================"
echo "  주간 리포트 자동화 세팅"
echo "======================================"
echo ""

# 1. Python 버전 확인
echo "[1/5] Python 버전 확인..."
python3 --version || { echo "Python3가 없습니다. 설치 후 다시 실행하세요."; exit 1; }

# 2. 패키지 설치
echo ""
echo "[2/5] 패키지 설치 중..."
pip3 install -r requirements.txt -q
echo "패키지 설치 완료"

# 3. .env 파일 확인 및 생성
echo ""
echo "[3/5] .env 파일 확인..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ".env 파일 생성됨 → .env를 열어 API 키를 입력하세요"
    echo ""
    echo "  필수 항목:"
    echo "    NOTION_API_KEY=<.env.example에 있는 값 입력>"
    echo "    ANTHROPIC_API_KEY=<Anthropic Console에서 발급>"
    echo ""
    echo "  .env 편집 후 이 스크립트를 다시 실행하세요."
    exit 0
else
    echo ".env 파일 존재 확인"
fi

# 4. credentials.json 확인
echo ""
echo "[4/5] Google credentials.json 확인..."
if [ ! -f "credentials.json" ]; then
    echo ""
    echo "  ⚠️  credentials.json 파일이 없습니다."
    echo ""
    echo "  Google Cloud Console 설정 방법:"
    echo "    1) https://console.cloud.google.com 접속"
    echo "    2) 프로젝트 생성 (또는 기존 프로젝트 선택)"
    echo "    3) API 및 서비스 → 라이브러리 → 'Google Calendar API' 활성화"
    echo "    4) API 및 서비스 → 사용자 인증 정보 → 사용자 인증 정보 만들기"
    echo "       → OAuth 클라이언트 ID → 데스크톱 앱 선택"
    echo "    5) JSON 다운로드 → 이 폴더(python/)에 credentials.json으로 저장"
    echo ""
    echo "  파일 저장 후 이 스크립트를 다시 실행하세요."
    exit 0
fi
echo "credentials.json 확인 완료"

# 5. Google 인증 (token.json 생성)
echo ""
echo "[5/5] Google Calendar 인증..."
if [ ! -f "token.json" ]; then
    echo "  브라우저가 열립니다. 구글 계정으로 로그인 후 권한을 허용하세요."
    python3 google_auth.py
else
    echo "  기존 token.json 사용 (재인증 불필요)"
fi

# cron 등록 안내
echo ""
echo "======================================"
echo "  ✅ 기본 세팅 완료!"
echo "======================================"
echo ""
echo "  수동 실행 테스트:"
echo "    cd $SCRIPT_DIR && python3 main.py"
echo ""
echo "  자동화 설정 (cron):"
echo "    crontab -e 명령 실행 후 아래 줄 추가"
echo ""
echo "    # 매주 일요일 오후 9시 리포트 생성"
echo "    0 21 * * 0 cd $SCRIPT_DIR && python3 main.py >> $SCRIPT_DIR/report.log 2>&1"
echo ""
echo "  또는 아래 명령으로 자동 등록:"
echo "    bash $SCRIPT_DIR/cron_register.sh"
echo ""
