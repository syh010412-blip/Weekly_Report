"""
클라우드 환경 실행용 - Notion I/O는 MCP, 나머지는 Python.

사용: python3 run_report.py
출력: report_blocks.json (Notion 블록 배열)
"""
import json
import sys
from datetime import datetime

from config import DAY_NAMES


def main():
    # ── 1. 날짜 범위 고정 ─────────────────────────────────────────
    week = {
        'monday': '2026-04-27',
        'sunday': '2026-05-03',
        'dates': [
            '2026-04-27', '2026-04-28', '2026-04-29', '2026-04-30',
            '2026-05-01', '2026-05-02', '2026-05-03',
        ],
    }
    print(f'[리포트] 분석 기간: {week["monday"]} ~ {week["sunday"]}')

    # ── 2. Google Calendar 데이터 수집 ───────────────────────────
    print('[리포트] Google Calendar 수집 중...')
    from google_auth import get_calendar_service
    from google_calendar import get_events_for_week
    service = get_calendar_service()
    cal_by_date = get_events_for_week(service, week['monday'], week['sunday'])
    total_cal = sum(len(v) for v in cal_by_date.values())
    print(f'[리포트] 캘린더 {total_cal}건 수집 완료')

    # ── 3. Notion Inbox 데이터 (MCP로 수집한 값 직접 입력) ────────
    inbox_items = [
        {
            'title': '엄마 방문',
            'memo': '커피, 샴푸, 라면,',
            'processed': True,
            'source': '머릿속',
            'date': '2026-05-03',
            'time': '08:12',
            'created_at': '2026-05-02T23:12:20.983Z',
            'page_id': '354a3bd9-3958-81b0-8071-e1e028b43a78',
        },
    ]
    inbox_summary = {
        'total': 1,
        'processed': 1,
        'unprocessed': 0,
        'process_rate': 100,
        'by_source': {'머릿속': 1},
    }
    print(f'[리포트] Inbox {inbox_summary["total"]}건 (처리율 {inbox_summary["process_rate"]}%)')

    # ── 4. Claude AI 분석 ─────────────────────────────────────────
    print('[리포트] Claude AI 분석 중...')
    from analyzer import analyze
    analysis = analyze(week, cal_by_date, inbox_items, inbox_summary)

    # ── 5. Notion 블록 빌드 ───────────────────────────────────────
    print('[리포트] 블록 빌드 중...')
    from blocks import build_report_blocks
    blocks = build_report_blocks(week, cal_by_date, inbox_items, inbox_summary, analysis)
    print(f'[리포트] 블록 {len(blocks)}개 생성')

    # ── 6. JSON으로 저장 ──────────────────────────────────────────
    out_path = 'report_blocks.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({'blocks': blocks, 'analysis': analysis, 'week': week}, f, ensure_ascii=False, indent=2)
    print(f'[리포트] → {out_path} 저장 완료')

    return blocks, analysis, week


if __name__ == '__main__':
    main()
