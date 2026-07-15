"""건강 기록 DB에서 주간 데이터를 읽어오는 모듈.

iPhone Health(HealthKit) 데이터는 Apple이 클라우드 API를 제공하지 않으므로,
iOS 단축어(Shortcuts) 자동화가 매일 이 Notion DB에 걸음수·수면시간·심박수 등을
기록해두는 것을 전제로 한다.
지표(number 타입 속성) 이름을 하드코딩하지 않고 DB 스키마에서 자동으로 찾아
쓰기 때문에, Notion DB에 어떤 지표를 추가/삭제하든 코드 수정 없이 반영된다.
"""
from datetime import datetime, timezone, timedelta

import requests

from config import NOTION_API_KEY, HEALTH_DB_ID

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


def _find_prop_name(schema: dict, prop_type: str) -> str | None:
    for name, meta in schema.items():
        if meta.get('type') == prop_type:
            return name
    return None


def _parse_page(page: dict, schema: dict, date_name: str | None) -> dict:
    props = page['properties']

    date_val = ''
    if date_name:
        date_val = ((props.get(date_name) or {}).get('date') or {}).get('start', '') or ''
    if not date_val:
        created_at = page.get('created_time', '')
        if created_at:
            dt_utc = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            date_val = dt_utc.astimezone(KST).strftime('%Y-%m-%d')

    metrics: dict[str, float] = {}
    for name, meta in schema.items():
        if meta.get('type') != 'number' or name == date_name:
            continue
        val = (props.get(name) or {}).get('number')
        if val is not None:
            metrics[name] = val

    return {'date': date_val[:10], 'metrics': metrics, 'page_id': page['id']}


def get_health_for_week(monday: str, sunday: str) -> list[dict]:
    """월~일 기간의 건강 기록 반환 (Date 속성 기준, 없으면 생성일 기준)."""
    if not HEALTH_DB_ID:
        return []

    db = _req(f'databases/{HEALTH_DB_ID}')
    schema = db.get('properties', {})
    date_name = _find_prop_name(schema, 'date')

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
        res = _req(f'databases/{HEALTH_DB_ID}/query', 'POST', body)
        results.extend(res['results'])
        if res.get('has_more'):
            cursor = res['next_cursor']
        else:
            break

    items = [_parse_page(p, schema, date_name) for p in results]
    print(f'[Health] {len(items)}건 ({monday} ~ {sunday})')
    return items


def summarize_health(items: list[dict]) -> dict:
    if not items:
        return {'total': 0, 'metrics': {}}

    agg: dict[str, list[float]] = {}
    for item in items:
        for name, val in item['metrics'].items():
            agg.setdefault(name, []).append(val)

    metrics_summary = {
        name: {
            'avg': round(sum(vals) / len(vals), 1),
            'sum': round(sum(vals), 1),
            'days': len(vals),
        }
        for name, vals in agg.items()
    }

    return {'total': len(items), 'metrics': metrics_summary}
