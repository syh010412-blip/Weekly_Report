import os
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

# Notion
NOTION_API_KEY = os.getenv('NOTION_API_KEY', '')
INBOX_DB_ID = os.getenv('NOTION_INBOX_DB_ID') or '81c6e06c-3979-4922-a591-58dd1cd46b34'
REPORT_DB_ID = os.getenv('NOTION_REPORT_DB_ID') or '34da3bd9-3958-8007-82ee-efb717e2658f'
# 월간 리포트 전용 DB를 따로 두고 싶으면 설정. 비우면 주간 리포트와 같은 DB를 사용.
MONTHLY_REPORT_DB_ID = os.getenv('NOTION_MONTHLY_REPORT_DB_ID') or REPORT_DB_ID
REHAB_DB_ID = os.getenv('NOTION_REHAB_DB_ID') or 'e6462d82-a461-419f-bd95-db0207ea7198'
DIARY_DB_ID = os.getenv('NOTION_DIARY_DB_ID', '')

# Anthropic
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

# Google Calendar
GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
GOOGLE_TOKEN_PATH = os.getenv('GOOGLE_TOKEN_PATH', 'token.json')
CALENDAR_EXCLUDE = [x.strip() for x in os.getenv('CALENDAR_EXCLUDE', '').split(',') if x.strip()]


def get_kst_today() -> str:
    """KST 기준 오늘 날짜 (YYYY-MM-DD)"""
    from datetime import timezone, datetime
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst).strftime('%Y-%m-%d')


def get_week_range(today_str: str) -> dict:
    """해당 날짜가 속한 주 월~일 계산"""
    today = date.fromisoformat(today_str)
    day_of_week = today.weekday()  # 0=월, 6=일
    monday = today - timedelta(days=day_of_week)
    dates = [str(monday + timedelta(days=i)) for i in range(7)]
    return {
        'monday': dates[0],
        'sunday': dates[6],
        'dates': dates,
    }


def get_month_range(today_str: str) -> dict:
    """해당 날짜가 속한 월의 시작일~종료일 계산"""
    today = date.fromisoformat(today_str)
    year, month = today.year, today.month
    start = date(year, month, 1)
    end = (date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)) - timedelta(days=1)
    dates = [str(start + timedelta(days=i)) for i in range((end - start).days + 1)]
    return {'year': year, 'month': month, 'start': str(start), 'end': str(end), 'dates': dates}


def group_dates_by_week(dates: list[str]) -> list[dict]:
    """날짜 목록을 (월요일 시작) 주 단위로 묶는다. 월 경계에 걸친 주는 해당 월에 속한 날짜만 포함한다."""
    buckets: dict[date, list[str]] = {}
    for d_str in dates:
        d = date.fromisoformat(d_str)
        monday = d - timedelta(days=d.weekday())
        buckets.setdefault(monday, []).append(d_str)
    return [
        {'monday': str(monday), 'dates': sorted(ds)}
        for monday, ds in sorted(buckets.items())
    ]


DAY_NAMES = ['월', '화', '수', '목', '금', '토', '일']
