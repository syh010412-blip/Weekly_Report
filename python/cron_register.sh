#!/bin/bash
# cron 자동 등록 스크립트 (매주 일요일 21시)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRON_CMD="0 21 * * 0 cd $SCRIPT_DIR && python3 main.py >> $SCRIPT_DIR/report.log 2>&1"

# 기존 crontab에 같은 항목이 없으면 추가
(crontab -l 2>/dev/null | grep -v "silver-potato"; echo "$CRON_CMD") | crontab -

echo "✅ cron 등록 완료"
echo ""
crontab -l | grep "silver-potato" || true
echo ""
echo "매주 일요일 오후 9시에 자동 실행됩니다."
echo "로그 확인: tail -f $SCRIPT_DIR/report.log"
