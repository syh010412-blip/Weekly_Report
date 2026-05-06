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


def get_events_for_week(service: Any, monday: str, sunday: str) -> dict[str, list[dict]]:
    """월~일 범위의 모든 캘린더 이벤트를 날짜별로 반환."""
    time_min = f'{monday}T00:00:00+09:00'
    time_max = f'{sunday}T23:59:59+09:00'

    cal_list = service.calendarList().list().execute()
    calendars = [
        cal for cal in cal_list.get('items', [])
        if not any(
            pat in cal.get('id', '') or pat in cal.get('summary', '')
            for pat in CALENDAR_EXCLUDE
        )
    ]
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
