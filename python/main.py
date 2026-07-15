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
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            log('Workload Identity Federation 인증 실패로 보입니다. GCP IAM에서 서비스 계정에 '
                'roles/iam.workloadIdentityUser 권한이 부여되어 있는지 확인하세요.')
        else:
            log('credentials.json이 python/ 폴더에 있는지 확인하고, python auth_manual.py로 인증하세요.')
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

    # 3.5. 재활 기록 수집
    log('재활 기록 수집 중...')
    try:
        from rehab_reader import get_rehab_for_week, summarize_rehab
        rehab_items = get_rehab_for_week(week['monday'], week['sunday'])
        rehab_summary = summarize_rehab(rehab_items)
        log(f'재활 기록: {rehab_summary["total"]}건')
    except Exception as err:
        log(f'[경고] 재활 기록 수집 실패 (계속 진행): {err}')
        rehab_items = []
        rehab_summary = {'total': 0, 'avg_pain': None, 'avg_arm_mobility': None, 'condition_counts': {}, 'mood_counts': {}}

    # 3.6. 일기 기록 수집
    log('일기 기록 수집 중...')
    try:
        from diary_reader import get_diary_for_week, summarize_diary
        diary_items = get_diary_for_week(week['monday'], week['sunday'])
        diary_summary = summarize_diary(diary_items)
        log(f'일기 기록: {diary_summary["total"]}건')
    except Exception as err:
        log(f'[경고] 일기 기록 수집 실패 (계속 진행): {err}')
        diary_items = []
        diary_summary = {'total': 0, 'mood_counts': {}}

    # 3.7. 건강 기록 수집 (iOS 단축어 자동화 → Notion)
    log('건강 기록 수집 중...')
    try:
        from health_reader import get_health_for_week, summarize_health
        health_items = get_health_for_week(week['monday'], week['sunday'])
        health_summary = summarize_health(health_items)
        log(f'건강 기록: {health_summary["total"]}건')
    except Exception as err:
        log(f'[경고] 건강 기록 수집 실패 (계속 진행): {err}')
        health_items = []
        health_summary = {'total': 0, 'metrics': {}}

    # 4. Claude AI 분석
    log('Claude AI 분석 중...')
    try:
        from analyzer import analyze
        analysis = analyze(week, cal_by_date, inbox_items, inbox_summary)
    except Exception as err:
        log(f'[오류] AI 분석 실패: {err}')
        sys.exit(1)

    # 4.5. 일기 기록이 없으면 재활/Inbox/캘린더 데이터로 회고 대신 생성
    generated_diary = None
    if diary_summary['total'] == 0:
        try:
            from analyzer import generate_diary_reflection
            generated_diary = generate_diary_reflection(week, rehab_items, inbox_items, cal_by_date)
        except Exception as err:
            log(f'[경고] 일기 자동 생성 실패 (계속 진행): {err}')

    # 5. Notion 블록 생성
    log('Notion 블록 빌드 중...')
    from blocks import build_report_blocks
    blocks = build_report_blocks(
        week, cal_by_date, inbox_items, inbox_summary, analysis,
        rehab_items, rehab_summary, diary_items, diary_summary, generated_diary,
        health_items, health_summary,
    )
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
