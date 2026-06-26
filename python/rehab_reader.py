"""재활 기록 DB에서 주간 기록을 읽어오는 모듈."""
import requests

from config import NOTION_API_KEY, REHAB_DB_ID

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

    def rich_text(key: str) -> str:
        return ''.join(t['plain_text'] for t in (props.get(key) or {}).get('rich_text', []))

    def select(key: str) -> str:
        return ((props.get(key) or {}).get('select') or {}).get('name', '')

    def number(key: str) -> float | None:
        v = (props.get(key) or {}).get('number')
        return v

    date_val = ((props.get('Date') or {}).get('date') or {}).get('start', '')

    return {
        'name': ''.join(t['plain_text'] for t in (props.get('Name') or {}).get('title', [])),
        'date': date_val,
        'condition': select('컨디션'),
        'exercises': rich_text('오늘 한 재활 운동'),
        'pain': number('통증 수준 (0~10)'),
        'mood': select('기분'),
        'arm_mobility': number('왼팔 움직임 (0~10)'),
        'memo': rich_text('나아진 점 / 메모'),
    }


def get_rehab_for_week(monday: str, sunday: str) -> list[dict]:
    """월~일 기간의 재활 기록 반환 (Date 기준)."""
    results = []
    cursor = None
    while True:
        body: dict = {
            'filter': {
                'and': [
                    {'property': 'Date', 'date': {'on_or_after': monday}},
                    {'property': 'Date', 'date': {'on_or_before': sunday}},
                ]
            },
            'sorts': [{'property': 'Date', 'direction': 'ascending'}],
            'page_size': 100,
        }
        if cursor:
            body['start_cursor'] = cursor
        res = _req(f'databases/{REHAB_DB_ID}/query', 'POST', body)
        results.extend(res['results'])
        if res.get('has_more'):
            cursor = res['next_cursor']
        else:
            break

    items = [_parse_page(p) for p in results]
    print(f'[Rehab] {len(items)}건 ({monday} ~ {sunday})')
    return items


def summarize_rehab(items: list[dict]) -> dict:
    if not items:
        return {
            'total': 0,
            'avg_pain': None,
            'avg_arm_mobility': None,
            'condition_counts': {},
            'mood_counts': {},
        }

    pain_vals = [i['pain'] for i in items if i['pain'] is not None]
    arm_vals = [i['arm_mobility'] for i in items if i['arm_mobility'] is not None]

    condition_counts: dict[str, int] = {}
    mood_counts: dict[str, int] = {}
    for item in items:
        if item['condition']:
            condition_counts[item['condition']] = condition_counts.get(item['condition'], 0) + 1
        if item['mood']:
            mood_counts[item['mood']] = mood_counts.get(item['mood'], 0) + 1

    return {
        'total': len(items),
        'avg_pain': round(sum(pain_vals) / len(pain_vals), 1) if pain_vals else None,
        'avg_arm_mobility': round(sum(arm_vals) / len(arm_vals), 1) if arm_vals else None,
        'condition_counts': condition_counts,
        'mood_counts': mood_counts,
    }
