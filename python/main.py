"""메인 실행 파일.

실행 방법:
  python main.py              # 이번 주 (KST 기준 오늘)
  REPORT_DATE=2026-05-06 python main.py   # 특정 날짜가 속한 주
"""
import os
import sys
from datetime import datetime

from config import get_kst_today, get_week_range, DAY_NAMES


def log(msg: str) -> None:
    ts = datetime.now().strftime('%H:%M:%S')
    print(f'[{ts}] {msg}')


def build_report_title(monday: str) -> str:
    dt = datetime.strptime(monday, '%Y-%m-%d')
    return f'주간 리포트 {dt.year}.{dt.month:02d}.{dt.day:02d}'


def main() -> None:
    log('=== 주간 리포트 생성 시작 ===')

    # 1. 날짜 범위 결정
    today = os.getenv('REPORT_DATE') or get_kst_today()
    week = get_week_range(today)
    log(f'분석 기간: {week["monday"]} (월) ~ {week["sunday"]} (일)')

    # 2. Google Calendar 데이터 수집
    log('구글 캘린더 이벤트 수집 중...')
    try:
        from google_auth import get_calendar_service
        from google_calendar import get_events_for_week
        service = get_calendar_service()
        cal_by_date = get_events_for_week(service, week['monday'], week['sunday'])
        total_cal = sum(len(v) for v in cal_by_date.values())
        log(f'구글 캘린더: {total_cal}건')
    except Exception as err:
        log(f'[오류] 구글 캘린더 수집 실패: {err}')
        log('credentials.json이 python/ 폴더에 있는지 확인하고, python google_auth.py로 인증하세요.')
        sys.exit(1)

    # 3. Notion Inbox 데이터 수집
    log('Notion Inbox 데이터 수집 중...')
    try:
        from notion_reader import get_inbox_for_week, summarize_inbox
        inbox_items = get_inbox_for_week(week['monday'], week['sunday'])
        inbox_summary = summarize_inbox(inbox_items)
        log(f'Inbox: {inbox_summary["total"]}건 (처리완료 {inbox_summary["processed"]}건, 미처리 {inbox_summary["unprocessed"]}건)')
    except Exception as err:
        log(f'[오류] Notion Inbox 수집 실패: {err}')
        sys.exit(1)

    # 4. Claude AI 분석
    log('Claude AI 분석 중...')
    try:
        from analyzer import analyze
        analysis = analyze(week, cal_by_date, inbox_items, inbox_summary)
    except Exception as err:
        log(f'[오류] AI 분석 실패: {err}')
        sys.exit(1)

    # 5. Notion 블록 생성
    log('Notion 블록 빌드 중...')
    from blocks import build_report_blocks
    blocks = build_report_blocks(week, cal_by_date, inbox_items, inbox_summary, analysis)
    log(f'블록 {len(blocks)}개 생성')

    # 6. Notion 업로드
    log('Notion에 업로드 중...')
    try:
        from notion_writer import upsert_report
        title = build_report_title(week['monday'])
        page_id = upsert_report(title, blocks, today)
        log(f'업로드 완료 → 페이지 ID: {page_id}')
    except Exception as err:
        log(f'[오류] Notion 업로드 실패: {err}')
        sys.exit(1)

    log('=== 주간 리포트 생성 완료 ===')
    log(f'리포트 제목: {build_report_title(week["monday"])}')


if __name__ == '__main__':
    main()
