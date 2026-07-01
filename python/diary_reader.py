"""일기 DB에서 주간 기록을 읽어오는 모듈.

DB 속성 이름을 하드코딩하지 않고, 데이터베이스 스키마에서
title/date/select 타입 속성을 자동으로 찾아 사용한다.
날짜 속성이 없으면 페이지 생성일(created_time) 기준으로 조회한다.
"""
from datetime import datetime, timezone, timedelta

import requests

from config import NOTION_API_KEY, DIARY_DB_ID

KST = timezone(timedelta(hours=9))
_HEADERS = {
    'Authorization': f'Bearer {NOTION_API_KEY}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json',
}
_BASE = 'https://api.notion.com/v1'


def _req(path: str, method: str = 'GET', body: dict | None = None) -> dict:
    url = f'{_BASE}/{path}'
    resp = requests.request(method, url, headers=_HEADERS, json=body or None, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _get_page_body(page_id: str) -> str:
    """페이지 본문 블록에서 텍스트 추출."""
    try:
        res = _req(f'blocks/{page_id}/children?page_size=100')
        lines = []
        for block in res.get('results', []):
            block_type = block.get('type', '')
            rich_texts = block.get(block_type, {}).get('rich_text', [])
            text = ''.join(t.get('plain_text', '') for t in rich_texts)
            if text.strip():
                lines.append(text.strip())
        return '\n'.join(lines)
    except Exception:
        return ''


def _find_prop_name(schema: dict, prop_type: str) -> str | None:
    for name, meta in schema.items():
        if meta.get('type') == prop_type:
            return name
    return None


def _parse_page(page: dict, title_name: str | None, date_name: str | None, mood_name: str | None) -> dict:
    props = page['properties']

    title = ''
    if title_name:
        title = ''.join(t.get('plain_text', '') for t in (props.get(title_name) or {}).get('title', []))

    date_val = ''
    if date_name:
        date_val = ((props.get(date_name) or {}).get('date') or {}).get('start', '') or ''
    if not date_val:
        created_at = page.get('created_time', '')
        if created_at:
            dt_utc = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            date_val = dt_utc.astimezone(KST).strftime('%Y-%m-%d')

    mood = ''
    if mood_name:
        mood = ((props.get(mood_name) or {}).get('select') or {}).get('name', '')

    return {
        'title': title.strip(),
        'date': date_val[:10],
        'mood': mood,
        'page_id': page['id'],
    }


def get_diary_for_week(monday: str, sunday: str) -> list[dict]:
    """월~일 기간의 일기 항목 반환 (날짜 속성 기준, 없으면 생성일 기준)."""
    if not DIARY_DB_ID:
        return []

    db = _req(f'databases/{DIARY_DB_ID}')
    schema = db.get('properties', {})
    title_name = _find_prop_name(schema, 'title')
    date_name = _find_prop_name(schema, 'date')
    mood_name = _find_prop_name(schema, 'select')

    if date_name:
        query_filter = {
            'and': [
                {'property': date_name, 'date': {'on_or_after': monday}},
                {'property': date_name, 'date': {'on_or_before': sunday}},
            ]
        }
        sorts = [{'property': date_name, 'direction': 'ascending'}]
    else:
        query_filter = {
            'and': [
                {'timestamp': 'created_time', 'created_time': {'on_or_after': f'{monday}T00:00:00+09:00'}},
                {'timestamp': 'created_time', 'created_time': {'on_or_before': f'{sunday}T23:59:59+09:00'}},
            ]
        }
        sorts = [{'timestamp': 'created_time', 'direction': 'ascending'}]

    results = []
    cursor = None
    while True:
        body: dict = {'filter': query_filter, 'sorts': sorts, 'page_size': 100}
        if cursor:
            body['start_cursor'] = cursor
        res = _req(f'databases/{DIARY_DB_ID}/query', 'POST', body)
        results.extend(res['results'])
        if res.get('has_more'):
            cursor = res['next_cursor']
        else:
            break

    items = [_parse_page(p, title_name, date_name, mood_name) for p in results]
    for item in items:
        item['content'] = _get_page_body(item['page_id'])

    print(f'[Diary] {len(items)}건 ({monday} ~ {sunday})')
    return items


def summarize_diary(items: list[dict]) -> dict:
    mood_counts: dict[str, int] = {}
    for item in items:
        if item['mood']:
            mood_counts[item['mood']] = mood_counts.get(item['mood'], 0) + 1
    return {
        'total': len(items),
        'mood_counts': mood_counts,
    }
