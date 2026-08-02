"""AI 주간 리포트 DB에 분석 결과 페이지를 생성/업데이트하는 모듈."""
import json

import requests

from config import NOTION_API_KEY, REPORT_DB_ID

CHUNK_SIZE = 100
# Notion blocks.children.append 요청 본문 크기 제한(약 500KB)보다 여유 있게 설정.
# 월간 리포트처럼 한 블록에 데이터가 많이 중첩되는 경우를 대비해 블록 개수뿐 아니라
# 바이트 크기 기준으로도 청크를 나눈다.
MAX_CHUNK_BYTES = 400_000
_HEADERS = {
    'Authorization': f'Bearer {NOTION_API_KEY}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json',
}
_BASE = 'https://api.notion.com/v1'


def _req(path: str, method: str = 'GET', body: dict | None = None) -> dict:
    url = f'{_BASE}/{path}'
    resp = requests.request(method, url, headers=_HEADERS, json=body or None, timeout=30)
    if not resp.ok:
        raise requests.HTTPError(f'{resp.status_code} {resp.reason}: {resp.text}', response=resp)
    return resp.json()


def _find_existing(title: str, db_id: str = REPORT_DB_ID) -> str | None:
    res = _req(f'databases/{db_id}/query', 'POST', {
        'filter': {'property': '리포트 명', 'title': {'equals': title}},
        'page_size': 1,
    })
    results = res.get('results', [])
    return results[0]['id'] if results else None


def _clear_blocks(page_id: str) -> None:
    cursor = None
    while True:
        params = {'page_size': 100}
        if cursor:
            params['start_cursor'] = cursor
        url = f'{_BASE}/blocks/{page_id}/children'
        resp = requests.get(url, headers=_HEADERS, params=params, timeout=30)
        resp.raise_for_status()
        res = resp.json()
        for block in res.get('results', []):
            try:
                requests.delete(f'{_BASE}/blocks/{block["id"]}', headers=_HEADERS, timeout=30)
            except Exception:
                pass
        if res.get('has_more'):
            cursor = res['next_cursor']
        else:
            break


def _block_size(block: dict) -> int:
    return len(json.dumps(block, ensure_ascii=False).encode('utf-8'))


def _append_blocks(page_id: str, blocks: list[dict]) -> None:
    n = len(blocks)
    i = 0
    done = 0
    while i < n:
        chunk: list[dict] = []
        chunk_bytes = 0
        while i < n and len(chunk) < CHUNK_SIZE:
            block_bytes = _block_size(blocks[i])
            if chunk and chunk_bytes + block_bytes > MAX_CHUNK_BYTES:
                break
            chunk.append(blocks[i])
            chunk_bytes += block_bytes
            i += 1
        _req(f'blocks/{page_id}/children', 'PATCH', {'children': chunk})
        done += len(chunk)
        print(f'[Notion] 블록 업로드: {done}/{n}')


def upsert_report(title: str, blocks: list[dict], analysis_date: str, db_id: str = REPORT_DB_ID) -> str:
    existing_id = _find_existing(title, db_id)

    if existing_id:
        print(f'[Notion] 기존 페이지 업데이트: "{title}"')
        _req(f'pages/{existing_id}', 'PATCH', {'icon': {'type': 'emoji', 'emoji': '📊'}})
        _clear_blocks(existing_id)
        _append_blocks(existing_id, blocks)
        print('[Notion] 업데이트 완료')
        return existing_id

    print(f'[Notion] 새 페이지 생성: "{title}"')
    page = _req('pages', 'POST', {
        'parent': {'database_id': db_id},
        'icon': {'type': 'emoji', 'emoji': '📊'},
        'properties': {
            '리포트 명': {'title': [{'text': {'content': title}}]},
            '분석 날짜': {'date': {'start': analysis_date}},
        },
    })
    _append_blocks(page['id'], blocks)
    print('[Notion] 생성 완료')
    return page['id']
