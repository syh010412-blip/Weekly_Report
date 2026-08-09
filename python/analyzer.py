"""Claude AI로 구글 캘린더(계획) vs Notion Inbox(실행) 비교 분석."""
import json

import anthropic

from config import ANTHROPIC_API_KEY, DAY_NAMES

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """당신은 개인 생산성 코치입니다.
사용자의 구글 캘린더(계획)와 노션 Inbox(실행 캡처)를 비교 분석하여 인사이트를 제공합니다.
반드시 유효한 JSON만 출력하세요. 마크다운 코드블록 없이.
한국어로 응답하세요. 구체적이고 실행 가능한 조언 위주로 작성하세요.
"""


def _build_prompt(week: dict, cal_by_date: dict, inbox_items: list[dict], inbox_summary: dict) -> str:
    monday, sunday = week['monday'], week['sunday']

    # 캘린더 이벤트 목록 텍스트
    cal_lines = []
    total_cal = 0
    for d in week['dates']:
        events = cal_by_date.get(d, [])
        total_cal += len(events)
        day_name = DAY_NAMES[week['dates'].index(d)]
        for ev in events:
            time_str = '종일' if ev['is_all_day'] else f'{ev["start"][11:16]}~{ev["end"][11:16]}'
            cal_lines.append(f'  {d}({day_name}) {time_str} | {ev["title"]} [{ev["calendar"]}]')
    cal_section = '\n'.join(cal_lines) if cal_lines else '  (이벤트 없음)'

    # Inbox 항목 목록 텍스트
    inbox_lines = []
    for item in inbox_items:
        proc = '✅ 처리완료' if item['processed'] else '⏳ 미처리'
        memo_str = f' / 메모: {item["memo"]}' if item['memo'] else ''
        body_str = f' / 본문: {item["body"]}' if item.get('body') else ''
        inbox_lines.append(
            f'  {item["date"]} {item["time"]} | {item["title"]}{memo_str}{body_str} | {proc} | 출처: {item["source"] or "기타"}'
        )
    inbox_section = '\n'.join(inbox_lines) if inbox_lines else '  (항목 없음)'

    return f"""아래 데이터를 분석하여 JSON으로 출력하세요.

## 분석 기간
{monday} (월) ~ {sunday} (일)

## 구글 캘린더 일정 (계획, 총 {total_cal}건)
{cal_section}

## Notion Inbox 항목 (캡처/실행, 총 {inbox_summary['total']}건)
- 처리 완료: {inbox_summary['processed']}건 ({inbox_summary['process_rate']}%)
- 미처리: {inbox_summary['unprocessed']}건
- 출처별: {json.dumps(inbox_summary['by_source'], ensure_ascii=False)}
{inbox_section}

## 분석 지침
- 캘린더 이벤트(계획)와 Inbox 항목(실행 캡처) 간의 연관성을 찾아 비교하세요.
- 연관성 기준: 제목·키워드 유사성, 같은 날 비슷한 시간대 등.
- Inbox는 GTD 수집함으로, 반드시 캘린더와 1:1 매칭이 아닐 수 있습니다.
- 생활형 루틴(식사·취침·재활치료 등)은 Inbox 캡처 대상이 아닐 수 있으므로
  "기록 없음 ≠ 실행 안 함"으로 해석하세요.
- 주간 총평은 2~3문장, 일별 인사이트는 각 1문장으로 작성하세요.

## 출력 JSON 형식
{{
  "weekly_overview": "주간 총평 (2~3문장, 캘린더 계획 대비 Inbox 실행 현황 중심)",
  "plan_vs_execution": {{
    "executed_as_planned": [
      {{"calendar_event": "캘린더 이벤트명", "inbox_item": "매칭된 Inbox 항목명", "date": "YYYY-MM-DD", "note": "연관성 설명"}}
    ],
    "unplanned_captures": [
      {{"inbox_item": "Inbox 항목명", "date": "YYYY-MM-DD", "processed": true, "insight": "이 캡처의 의미"}}
    ],
    "planned_not_captured": [
      {{"calendar_event": "캘린더 이벤트명", "date": "YYYY-MM-DD", "reason": "미캡처 가능 이유"}}
    ]
  }},
  "metrics": {{
    "total_calendar_events": {total_cal},
    "total_inbox_items": {inbox_summary['total']},
    "inbox_process_rate": {inbox_summary['process_rate']},
    "calendar_capture_rate": 0,
    "capture_rate_note": "캘린더 이벤트 중 Inbox에 캡처된 비율 (생활루틴 제외 기준)"
  }},
  "insights": [
    "인사이트 1 (구체적인 관찰)",
    "인사이트 2",
    "인사이트 3"
  ],
  "patterns": {{
    "strong_points": "잘 하고 있는 점",
    "weak_points": "개선이 필요한 점",
    "inbox_health": "Inbox 처리 상태 평가 (캡처율·처리율·패턴)"
  }},
  "next_week_suggestions": [
    "구체적 행동 제안 1",
    "구체적 행동 제안 2",
    "구체적 행동 제안 3",
    "구체적 행동 제안 4",
    "구체적 행동 제안 5"
  ]
}}"""


ANALYSIS_TOOL = {
    'name': 'submit_weekly_analysis',
    'description': '주간 계획 vs 실행 분석 결과를 제출합니다.',
    'input_schema': {
        'type': 'object',
        'properties': {
            'weekly_overview': {'type': 'string'},
            'plan_vs_execution': {
                'type': 'object',
                'properties': {
                    'executed_as_planned': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'calendar_event': {'type': 'string'},
                                'inbox_item': {'type': 'string'},
                                'date': {'type': 'string'},
                                'note': {'type': 'string'},
                            },
                            'required': ['calendar_event', 'inbox_item', 'date', 'note'],
                        },
                    },
                    'unplanned_captures': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'inbox_item': {'type': 'string'},
                                'date': {'type': 'string'},
                                'processed': {'type': 'boolean'},
                                'insight': {'type': 'string'},
                            },
                            'required': ['inbox_item', 'date', 'processed', 'insight'],
                        },
                    },
                    'planned_not_captured': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'calendar_event': {'type': 'string'},
                                'date': {'type': 'string'},
                                'reason': {'type': 'string'},
                            },
                            'required': ['calendar_event', 'date', 'reason'],
                        },
                    },
                },
                'required': ['executed_as_planned', 'unplanned_captures', 'planned_not_captured'],
            },
            'metrics': {
                'type': 'object',
                'properties': {
                    'total_calendar_events': {'type': 'integer'},
                    'total_inbox_items': {'type': 'integer'},
                    'inbox_process_rate': {'type': 'number'},
                    'calendar_capture_rate': {'type': 'number'},
                    'capture_rate_note': {'type': 'string'},
                },
                'required': [
                    'total_calendar_events', 'total_inbox_items', 'inbox_process_rate',
                    'calendar_capture_rate', 'capture_rate_note',
                ],
            },
            'insights': {'type': 'array', 'items': {'type': 'string'}},
            'patterns': {
                'type': 'object',
                'properties': {
                    'strong_points': {'type': 'string'},
                    'weak_points': {'type': 'string'},
                    'inbox_health': {'type': 'string'},
                },
                'required': ['strong_points', 'weak_points', 'inbox_health'],
            },
            'next_week_suggestions': {'type': 'array', 'items': {'type': 'string'}},
        },
        'required': [
            'weekly_overview', 'plan_vs_execution', 'metrics', 'insights',
            'patterns', 'next_week_suggestions',
        ],
    },
}


def _extract_tool_input(message, tool_name: str) -> dict:
    for block in message.content:
        if block.type == 'tool_use' and block.name == tool_name:
            return block.input
    raise ValueError(f'[{tool_name}] 응답에 tool_use 블록이 없습니다: {message.content}')


def analyze(week: dict, cal_by_date: dict, inbox_items: list[dict], inbox_summary: dict) -> dict:
    print('[AI 분석] Claude에 분석 요청 중...')
    prompt = _build_prompt(week, cal_by_date, inbox_items, inbox_summary)

    # tool-use로 강제해 스키마에 맞는 유효한 JSON만 받도록 함 (raw 텍스트 파싱 시
    # 문자열 안 이스케이프 안 된 개행/따옴표 때문에 파싱이 깨지던 문제를 원천 차단).
    message = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': prompt}],
        tools=[ANALYSIS_TOOL],
        tool_choice={'type': 'tool', 'name': ANALYSIS_TOOL['name']},
    )

    result = _extract_tool_input(message, ANALYSIS_TOOL['name'])
    print('[AI 분석] 완료')
    return result


DIARY_SYSTEM_PROMPT = """당신은 다정한 1인칭 회고 작가입니다.
사용자의 재활 기록, Notion Inbox 캡처, 캘린더 활동만을 근거로
일기 스타일의 주간 회고를 작성합니다.
주어진 데이터에 없는 사실을 지어내지 마세요.
반드시 유효한 JSON만 출력하세요. 마크다운 코드블록 없이. 한국어로 응답하세요.
"""


def _build_diary_prompt(week: dict, rehab_items: list[dict], inbox_items: list[dict], cal_by_date: dict) -> str:
    monday, sunday = week['monday'], week['sunday']

    rehab_lines = []
    for item in rehab_items:
        rehab_lines.append(
            f'  {item["date"]} | 컨디션: {item["condition"] or "-"} | 통증: {item["pain"]}/10 | '
            f'왼팔: {item["arm_mobility"]}/10 | 기분: {item["mood"] or "-"} | 메모: {item["memo"] or "-"}'
        )
    rehab_section = '\n'.join(rehab_lines) if rehab_lines else '  (기록 없음)'

    inbox_lines = []
    for item in inbox_items:
        body_str = f' / 본문: {item["body"]}' if item.get('body') else ''
        inbox_lines.append(f'  {item["date"]} {item["time"]} | {item["title"]}{body_str}')
    inbox_section = '\n'.join(inbox_lines) if inbox_lines else '  (항목 없음)'

    cal_lines = []
    for d in week['dates']:
        events = cal_by_date.get(d, [])
        titles = ', '.join(sorted({ev['title'] for ev in events})) if events else '(일정 없음)'
        cal_lines.append(f'  {d}: {titles}')
    cal_section = '\n'.join(cal_lines)

    return f"""아래 데이터를 바탕으로 {monday}~{sunday} 주간 회고 일기를 작성하세요.
Notion 일기 DB에 실제 기록이 없어서, 재활 기록·Inbox 캡처·캘린더 활동으로 대신 회고를 구성합니다.

## 재활 기록
{rehab_section}

## Inbox 캡처 (생각/감정 기록)
{inbox_section}

## 캘린더 활동 요약
{cal_section}

## 작성 지침
- 날짜별로 1인칭 일기 문체로 2~3문장씩 작성하세요 (실제 기록이 있는 날짜만).
- 재활 기록의 통증/왼팔 움직임 변화, Inbox의 감정/생각 캡처를 자연스럽게 녹여내세요.
- 데이터에 없는 사건이나 감정을 지어내지 마세요.
- 마지막에 주간 총평을 2~3문장으로 작성하세요.

## 출력 JSON 형식
{{
  "entries": [
    {{"date": "YYYY-MM-DD", "day_name": "월", "text": "일기 본문 2~3문장", "mood": "기록에 있으면 이모지+감정, 없으면 빈 문자열"}}
  ],
  "weekly_summary": "주간 총평 2~3문장"
}}"""


DIARY_TOOL = {
    'name': 'submit_diary_reflection',
    'description': '주간 회고 일기를 제출합니다.',
    'input_schema': {
        'type': 'object',
        'properties': {
            'entries': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'date': {'type': 'string'},
                        'day_name': {'type': 'string'},
                        'text': {'type': 'string'},
                        'mood': {'type': 'string'},
                    },
                    'required': ['date', 'day_name', 'text', 'mood'],
                },
            },
            'weekly_summary': {'type': 'string'},
        },
        'required': ['entries', 'weekly_summary'],
    },
}


def generate_diary_reflection(
    week: dict, rehab_items: list[dict], inbox_items: list[dict], cal_by_date: dict
) -> dict | None:
    """일기 DB 기록이 없을 때, 재활/Inbox/캘린더 데이터로 회고를 대신 생성."""
    if not rehab_items and not inbox_items:
        return None

    print('[일기 생성] 재활/Inbox 데이터로 회고 생성 중...')
    prompt = _build_diary_prompt(week, rehab_items, inbox_items, cal_by_date)

    message = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=3000,
        system=DIARY_SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': prompt}],
        tools=[DIARY_TOOL],
        tool_choice={'type': 'tool', 'name': DIARY_TOOL['name']},
    )

    result = _extract_tool_input(message, DIARY_TOOL['name'])
    print('[일기 생성] 완료')
    return result


REHAB_ANALYSIS_SYSTEM_PROMPT = """당신은 재활 전문 코치입니다.
주어진 재활 기록 데이터만을 근거로 통증·움직임 추이와 패턴을 분석합니다.
데이터에 없는 사실을 지어내지 마세요. 한국어로, 간결하고 구체적으로 작성하세요.
"""


def _build_rehab_analysis_prompt(rehab_items: list[dict], rehab_summary: dict) -> str:
    lines = []
    for item in rehab_items:
        lines.append(
            f'  {item["date"]} | 컨디션: {item["condition"] or "-"} | 통증: {item["pain"]}/10 | '
            f'왼팔: {item["arm_mobility"]}/10 | 기분: {item["mood"] or "-"} | '
            f'운동: {item["exercises"] or "-"} | 메모: {item["memo"] or "-"}'
        )
    detail_section = '\n'.join(lines)

    return f"""아래 재활 기록을 날짜 순서로 분석하세요.

## 재활 기록 ({rehab_summary.get('total', 0)}건)
{detail_section}

## 요약 수치
- 평균 통증: {rehab_summary.get('avg_pain')}
- 평균 왼팔 움직임: {rehab_summary.get('avg_arm_mobility')}

## 분석 지침
- 통증 수준과 왼팔 움직임이 기간 동안 어떻게 변했는지(호전/악화/유지) 구체적 수치와 함께 서술하세요.
- 특이사항이나 반복되는 패턴(예: 특정 요일에 통증 증가, 특정 운동 후 호전 등)을 찾으세요.
- 데이터에 없는 원인이나 사실을 추측해서 지어내지 마세요.
"""


REHAB_ANALYSIS_TOOL = {
    'name': 'submit_rehab_analysis',
    'description': '재활 기록 분석 결과를 제출합니다.',
    'input_schema': {
        'type': 'object',
        'properties': {
            'pain_trend': {'type': 'string', 'description': '통증 추이 (1~2문장)'},
            'mobility_trend': {'type': 'string', 'description': '왼팔 움직임 추이 (1~2문장)'},
            'notable_pattern': {'type': 'string', 'description': '특이사항·반복 패턴 (1~2문장)'},
            'overall_assessment': {'type': 'string', 'description': '종합 평가 (1~2문장)'},
            'suggestion': {'type': 'string', 'description': '다음 재활 관련 제안 (1문장)'},
        },
        'required': ['pain_trend', 'mobility_trend', 'notable_pattern', 'overall_assessment', 'suggestion'],
    },
}


def analyze_rehab(rehab_items: list[dict], rehab_summary: dict) -> dict | None:
    """재활 기록 데이터를 분석해 추이·패턴 요약을 생성."""
    if not rehab_items:
        return None

    print('[재활 분석] 통증/움직임 추이 분석 중...')
    prompt = _build_rehab_analysis_prompt(rehab_items, rehab_summary)

    message = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=1500,
        system=REHAB_ANALYSIS_SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': prompt}],
        tools=[REHAB_ANALYSIS_TOOL],
        tool_choice={'type': 'tool', 'name': REHAB_ANALYSIS_TOOL['name']},
    )

    result = _extract_tool_input(message, REHAB_ANALYSIS_TOOL['name'])
    print('[재활 분석] 완료')
    return result


DIARY_ANALYSIS_SYSTEM_PROMPT = """당신은 다정한 회고 코치입니다.
사용자가 실제로 쓴 일기 원문만을 근거로 감정 흐름과 주요 사건을 분석합니다.
일기에 없는 사실이나 감정을 지어내지 마세요. 한국어로 작성하세요.
"""


def _build_diary_analysis_prompt(diary_items: list[dict]) -> str:
    entry_lines = []
    for item in diary_items:
        content = item.get('content') or '(본문 없음)'
        entry_lines.append(f'### {item["date"]}\n{content}')
    entries_section = '\n\n'.join(entry_lines)

    return f"""아래는 이번 기간에 실제로 작성된 일기 원문입니다.

{entries_section}

## 분석 지침
- 한 주(기간) 동안의 감정 흐름을 시간 순서로 2~3문장으로 요약하세요.
- 일기에 등장하는 주요 사건을 짧은 항목 리스트로 뽑으세요 (일기에 없는 사건을 지어내지 마세요).
- 마지막에 전체 총평을 1~2문장으로 작성하세요.
"""


DIARY_ANALYSIS_TOOL = {
    'name': 'submit_diary_analysis',
    'description': '일기 원문에 대한 감정/사건 분석 결과를 제출합니다.',
    'input_schema': {
        'type': 'object',
        'properties': {
            'emotion_flow': {'type': 'string', 'description': '기간 동안의 감정 흐름 (2~3문장)'},
            'key_events': {'type': 'array', 'items': {'type': 'string'}, 'description': '주요 사건 목록'},
            'overall_reflection': {'type': 'string', 'description': '총평 (1~2문장)'},
        },
        'required': ['emotion_flow', 'key_events', 'overall_reflection'],
    },
}


def analyze_diary_entries(diary_items: list[dict]) -> dict | None:
    """실제 일기 기록이 있을 때, 감정 흐름·주요 사건 분석을 생성."""
    if not diary_items or not any(item.get('content') for item in diary_items):
        return None

    print('[일기 분석] 감정 흐름/주요 사건 분석 중...')
    prompt = _build_diary_analysis_prompt(diary_items)

    message = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=1500,
        system=DIARY_ANALYSIS_SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': prompt}],
        tools=[DIARY_ANALYSIS_TOOL],
        tool_choice={'type': 'tool', 'name': DIARY_ANALYSIS_TOOL['name']},
    )

    result = _extract_tool_input(message, DIARY_ANALYSIS_TOOL['name'])
    print('[일기 분석] 완료')
    return result
