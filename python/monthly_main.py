"""월간 리포트 메인 실행 파일.

실행 방법:
  python monthly_main.py                        # 지난달 (KST 기준 오늘이 속한 달의 전월)
  REPORT_DATE=2026-05-06 python monthly_main.py  # 특정 날짜가 속한 달을 명시적으로 지정

REPORT_DATE를 지정하지 않으면 '지난달' 리포트를 만든다. 매월 1일에 자동 실행되는
스케줄은 이제 막 시작한 이번 달이 아니라 방금 끝난 지난달을 다뤄야 하기 때문이다.
특정 달을 다시 만들고 싶을 때는 REPORT_DATE로 그 달에 속하는 날짜를 명시하면 된다.
"""
import os
import sys
from datetime import datetime

from config import get_kst_today, get_month_range, get_previous_month_range, group_dates_by_week, MONTHLY_REPORT_DB_ID


def log(msg: str) -> None:
    ts = datetime.now().strftime('%H:%M:%S')
    print(f'[{ts}] {msg}')


def build_report_title(year: int, month: int) -> str:
    return f'월간 리포트 {year}.{month:02d}'


def main() -> None:
    log('=== 월간 리포트 생성 시작 ===')

    # 1. 날짜 범위 결정
    explicit_date = os.getenv('REPORT_DATE')
    today = get_kst_today()
    month = get_month_range(explicit_date) if explicit_date else get_previous_month_range(today)
    log(f'분석 기간: {month["start"]} ~ {month["end"]} ({month["year"]}년 {month["month"]}월)')
    weeks = group_dates_by_week(month['dates'])

    # 2. Google Calendar 데이터 수집
    log('구글 캘린더 이벤트 수집 중...')
    try:
        from google_auth import get_calendar_service
        from google_calendar import get_events_for_week
        service = get_calendar_service()
        cal_by_date = get_events_for_week(service, month['start'], month['end'])
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
        inbox_items = get_inbox_for_week(month['start'], month['end'])
        inbox_summary = summarize_inbox(inbox_items)
        log(f'Inbox: {inbox_summary["total"]}건 (처리완료 {inbox_summary["processed"]}건, 미처리 {inbox_summary["unprocessed"]}건)')
    except Exception as err:
        log(f'[오류] Notion Inbox 수집 실패: {err}')
        sys.exit(1)

    # 3.5. 재활 기록 수집
    log('재활 기록 수집 중...')
    try:
        from rehab_reader import get_rehab_for_week, summarize_rehab
        rehab_items = get_rehab_for_week(month['start'], month['end'])
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
        diary_items = get_diary_for_week(month['start'], month['end'])
        diary_summary = summarize_diary(diary_items)
        log(f'일기 기록: {diary_summary["total"]}건')
    except Exception as err:
        log(f'[경고] 일기 기록 수집 실패 (계속 진행): {err}')
        diary_items = []
        diary_summary = {'total': 0, 'mood_counts': {}}

    # 4. 주차별 요약 (흐름 파악용)
    weekly_breakdown = []
    for w in weeks:
        week_dates = set(w['dates'])
        cal_count = sum(len(cal_by_date.get(d, [])) for d in w['dates'])
        week_inbox = [i for i in inbox_items if i['date'] in week_dates]
        week_inbox_summary = summarize_inbox(week_inbox)
        weekly_breakdown.append({
            'monday': w['monday'],
            'dates': w['dates'],
            'cal_count': cal_count,
            'inbox_total': week_inbox_summary['total'],
            'inbox_process_rate': week_inbox_summary['process_rate'],
        })

    # 5. Claude AI 분석
    log('Claude AI 분석 중...')
    try:
        from monthly_analyzer import analyze_month
        analysis = analyze_month(month, cal_by_date, inbox_items, inbox_summary, weekly_breakdown)
    except Exception as err:
        log(f'[오류] AI 분석 실패: {err}')
        sys.exit(1)

    # 5.5. 일기 기록이 없으면 재활/Inbox/캘린더 데이터로 회고 대신 생성
    generated_diary = None
    if diary_summary['total'] == 0:
        try:
            from monthly_analyzer import generate_monthly_diary_reflection
            generated_diary = generate_monthly_diary_reflection(month, rehab_items, inbox_items, cal_by_date)
        except Exception as err:
            log(f'[경고] 일기 자동 생성 실패 (계속 진행): {err}')

    # 6. Notion 블록 생성
    log('Notion 블록 빌드 중...')
    from monthly_blocks import build_monthly_report_blocks
    blocks = build_monthly_report_blocks(
        month, cal_by_date, inbox_items, inbox_summary, weekly_breakdown, analysis,
        rehab_items, rehab_summary, diary_items, diary_summary, generated_diary,
    )
    log(f'블록 {len(blocks)}개 생성')

    # 7. Notion 업로드
    log('Notion에 업로드 중...')
    try:
        from notion_writer import upsert_report
        title = build_report_title(month['year'], month['month'])
        page_id = upsert_report(title, blocks, today, MONTHLY_REPORT_DB_ID)
        log(f'업로드 완료 → 페이지 ID: {page_id}')
    except Exception as err:
        log(f'[오류] Notion 업로드 실패: {err}')
        sys.exit(1)

    log('=== 월간 리포트 생성 완료 ===')
    log(f'리포트 제목: {build_report_title(month["year"], month["month"])}')


if __name__ == '__main__':
    main()
