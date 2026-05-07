"""Notion Inbox DB에서 주간 항목을 읽어오는 모듈."""
import requests
from datetime import datetime, timezone, timedelta

from config import NOTION_API_KEY, INBOX_DB_ID

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


def _parse_page(page: dict) -> dict:
    props = page['properties']

    title = ''.join(t['plain_text'] for t in (props.get('Title') or {}).get('title', []))
    memo = ''.join(t['plain_text'] for t in (props.get('메모') or {}).get('rich_text', []))
    processed = (props.get('처리완료') or {}).get('checkbox', False)
    source = ((props.get('출처') or {}).get('select') or {}).get('name', '')

    created_at = page.get('created_time', '')
    if created_at:
        dt_utc = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        dt_kst = dt_utc.astimezone(KST)
        date_str = dt_kst.strftime('%Y-%m-%d')
        time_str = dt_kst.strftime('%H:%M')
    else:
        date_str = time_str = ''

    return {
        'title': title.strip(),
        'memo': memo.strip(),
        'processed': processed,
        'source': source,
        'date': date_str,
        'time': time_str,
        'created_at': created_at,
        'page_id': page['id'],
    }


def get_inbox_for_week(monday: str, sunday: str) -> list[dict]:
    """월~일 기간 동안 생성된 Inbox 항목 전체 반환."""
    monday_kst = f'{monday}T00:00:00+09:00'
    after_sunday_kst = f'{sunday}T23:59:59+09:00'

    results = []
    cursor = None
    while True:
        body: dict = {
            'filter': {
                'and': [
                    {'timestamp': 'created_time', 'created_time': {'on_or_after': monday_kst}},
                    {'timestamp': 'created_time', 'created_time': {'on_or_before': after_sunday_kst}},
                ]
            },
            'sorts': [{'timestamp': 'created_time', 'direction': 'ascending'}],
            'page_size': 100,
        }
        if cursor:
            body['start_cursor'] = cursor
        res = _req(f'databases/{INBOX_DB_ID}/query', 'POST', body)
        results.extend(res['results'])
        if res.get('has_more'):
            cursor = res['next_cursor']
        else:
            break

    items = [_parse_page(p) for p in results]
    print(f'[Inbox] {len(items)}건 ({monday} ~ {sunday})')
    return items


def summarize_inbox(items: list[dict]) -> dict:
    total = len(items)
    processed = sum(1 for i in items if i['processed'])
    unprocessed = total - processed
    by_source: dict[str, int] = {}
    for item in items:
        src = item['source'] or '기타'
        by_source[src] = by_source.get(src, 0) + 1
    return {
        'total': total,
        'processed': processed,
        'unprocessed': unprocessed,
        'process_rate': round(processed / total * 100) if total else 0,
        'by_source': by_source,
    }
