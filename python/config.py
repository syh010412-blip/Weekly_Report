import os
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

# Notion
NOTION_API_KEY = os.getenv('NOTION_API_KEY', '')
INBOX_DB_ID = os.getenv('NOTION_INBOX_DB_ID') or '81c6e06c-3979-4922-a591-58dd1cd46b34'
REPORT_DB_ID = os.getenv('NOTION_REPORT_DB_ID') or '34da3bd9-3958-8007-82ee-efb717e2658f'
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


DAY_NAMES = ['월', '화', '수', '목', '금', '토', '일']
