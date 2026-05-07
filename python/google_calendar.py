"""Google Calendar에서 주간 이벤트를 읽어오는 모듈."""
from datetime import datetime
from typing import Any

from config import CALENDAR_EXCLUDE


def _parse_event(event: dict, calendar_name: str) -> dict:
    start_raw = event['start'].get('dateTime') or event['start'].get('date')
    end_raw = event['end'].get('dateTime') or event['end'].get('date')
    is_all_day = 'dateTime' not in event['start']

    if is_all_day:
        start_hour = end_hour = None
        duration_min = None
    else:
        dt_start = datetime.fromisoformat(start_raw)
        dt_end = datetime.fromisoformat(end_raw)
        start_hour = dt_start.hour + dt_start.minute / 60
        end_hour = dt_end.hour + dt_end.minute / 60
        duration_min = int((dt_end - dt_start).total_seconds() / 60)

    return {
        'title': event.get('summary') or '(제목 없음)',
        'start': start_raw,
        'end': end_raw,
        'is_all_day': is_all_day,
        'start_hour': start_hour,
        'end_hour': end_hour,
        'duration_min': duration_min,
        'calendar': calendar_name,
        'date': start_raw[:10],
    }


_HARDCODED_CALENDAR_IDS = [
    'ko.south_korea#holiday@group.v.calendar.google.com',
    '8dffabd3d9af0a602af4aec3dcfc58a089c9efcc598602df9de02be95377dde2@group.calendar.google.com',
    'd3baf7448f00cbb1609991baf98b591ceae81f9bc48421ac76d57ec8d350dee6@group.calendar.google.com',
    'a96a79b50fb2ae4ac9250b78cb8bd484bf87df7a9df3cccddd42ede66afaff69@group.calendar.google.com',
    '53cbc3a72cda9d6c36b3e352f5d7883c2946d2b1607f9d3740ac964d52f2ce0c@group.calendar.google.com',
    'cc5b59000737dba52b9bab1f277845900c8c3592661d87aef42f9810a36e0dd5@group.calendar.google.com',
    'a4f52a05801c8476aab44d17cb7baff8646bfd4ba7ab919a72747984e2a43b78@group.calendar.google.com',
    'b53f9a9df9d20f131562cff25534c08faede09bc0b0709aee486916d38c94a4c@group.calendar.google.com',
    'syh010412@gmail.com',
    '4b11f54a0b2ba9962598a508a19bd90279298e58639271877d17a0c132401737@group.calendar.google.com',
    'b036cf357f7c32fcbbb0ceb53ee8546b31f2ab9e2c4400393604f6aa1958aa29@group.calendar.google.com',
]


def _get_calendars(service: Any) -> list[dict]:
    """calendarList 조회 — 비어있으면 하드코딩 ID로 폴백."""
    cal_list = service.calendarList().list().execute()
    items = cal_list.get('items', [])
    if items:
        return [
            cal for cal in items
            if not any(
                pat in cal.get('id', '') or pat in cal.get('summary', '')
                for pat in CALENDAR_EXCLUDE
            )
        ]
    # 서비스 계정용: 직접 ID로 캘린더 메타데이터 조회
    result = []
    for cal_id in _HARDCODED_CALENDAR_IDS:
        if any(pat in cal_id for pat in CALENDAR_EXCLUDE):
            continue
        try:
            meta = service.calendars().get(calendarId=cal_id).execute()
            result.append({'id': cal_id, 'summary': meta.get('summary', cal_id)})
        except Exception:
            result.append({'id': cal_id, 'summary': cal_id})
    return result


def get_events_for_week(service: Any, monday: str, sunday: str) -> dict[str, list[dict]]:
    """월~일 범위의 모든 캘린더 이벤트를 날짜별로 반환."""
    time_min = f'{monday}T00:00:00+09:00'
    time_max = f'{sunday}T23:59:59+09:00'

    calendars = _get_calendars(service)
    print(f'[캘린더] {len(calendars)}개 캘린더 조회 중...')

    all_events: list[dict] = []
    for cal in calendars:
        try:
            res = service.events().list(
                calendarId=cal['id'],
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime',
                maxResults=200,
            ).execute()
            events = [_parse_event(e, cal.get('summary', '')) for e in res.get('items', [])]
            if events:
                print(f'[캘린더]   {cal.get("summary")}: {len(events)}건')
            all_events.extend(events)
        except Exception as e:
            print(f'[캘린더] 오류 ({cal.get("summary")}): {e}')

    # 중복 제거 (같은 제목 + 같은 시작시간)
    seen: set[str] = set()
    unique: list[dict] = []
    for ev in all_events:
        key = f'{ev["title"]}|{ev["start"]}'
        if key not in seen:
            seen.add(key)
            unique.append(ev)

    # 날짜별 그룹핑 및 시간순 정렬
    by_date: dict[str, list[dict]] = {}
    for ev in unique:
        d = ev['date']
        by_date.setdefault(d, []).append(ev)
    for evts in by_date.values():
        evts.sort(key=lambda e: e['start_hour'] or 0)

    print(f'[캘린더] 총 {len(unique)}건 ({len(by_date)}일)')
    return by_date
