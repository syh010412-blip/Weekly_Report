"""Notion 블록 빌더 모듈."""
from typing import Any

# ── 리치텍스트 헬퍼 ──────────────────────────────────────────────

def rt(content: str, bold: bool = False, italic: bool = False,
       code: bool = False, color: str = 'default') -> dict:
    return {
        'type': 'text',
        'text': {'content': content, 'link': None},
        'annotations': {
            'bold': bold, 'italic': italic,
            'strikethrough': False, 'underline': False,
            'code': code, 'color': color,
        },
    }


# ── 블록 빌더 ────────────────────────────────────────────────────

def divider() -> dict:
    return {'object': 'block', 'type': 'divider', 'divider': {}}


def heading1(text: str) -> dict:
    return {
        'object': 'block', 'type': 'heading_1',
        'heading_1': {'rich_text': [rt(text)], 'is_toggleable': False},
    }


def heading2(text: str) -> dict:
    return {
        'object': 'block', 'type': 'heading_2',
        'heading_2': {'rich_text': [rt(text)], 'is_toggleable': False},
    }


def heading3(text: str) -> dict:
    return {
        'object': 'block', 'type': 'heading_3',
        'heading_3': {'rich_text': [rt(text)], 'is_toggleable': False},
    }


def callout(rich_texts: list[dict] | str, emoji: str = '📌', color: str = 'default') -> dict:
    if isinstance(rich_texts, str):
        rich_texts = [rt(rich_texts)]
    return {
        'object': 'block', 'type': 'callout',
        'callout': {
            'rich_text': rich_texts,
            'icon': {'type': 'emoji', 'emoji': emoji},
            'color': color,
        },
    }


def bullet(rich_texts: list[dict] | str) -> dict:
    if isinstance(rich_texts, str):
        rich_texts = [rt(rich_texts)]
    return {
        'object': 'block', 'type': 'bulleted_list_item',
        'bulleted_list_item': {'rich_text': rich_texts},
    }


def numbered(rich_texts: list[dict] | str) -> dict:
    if isinstance(rich_texts, str):
        rich_texts = [rt(rich_texts)]
    return {
        'object': 'block', 'type': 'numbered_list_item',
        'numbered_list_item': {'rich_text': rich_texts},
    }


def paragraph(rich_texts: list[dict] | str) -> dict:
    if isinstance(rich_texts, str):
        rich_texts = [rt(rich_texts)]
    return {
        'object': 'block', 'type': 'paragraph',
        'paragraph': {'rich_text': rich_texts},
    }


def table(headers: list[str], rows: list[list[str]]) -> dict:
    header_row = {
        'object': 'block', 'type': 'table_row',
        'table_row': {'cells': [[rt(h, bold=True)] for h in headers]},
    }
    data_rows = [
        {
            'object': 'block', 'type': 'table_row',
            'table_row': {'cells': [[rt(str(cell))] for cell in row]},
        }
        for row in rows
    ]
    return {
        'object': 'block', 'type': 'table',
        'table': {
            'table_width': len(headers),
            'has_column_header': True,
            'has_row_header': False,
            'children': [header_row, *data_rows],
        },
    }


def toggle_heading2(text: str, children: list[dict]) -> dict:
    return {
        'object': 'block', 'type': 'heading_2',
        'heading_2': {
            'rich_text': [rt(text)],
            'is_toggleable': True,
            'children': children,
        },
    }


# ── 재활 섹션 빌더 ──────────────────────────────────────────────

def build_rehab_section(rehab_items: list[dict], rehab_summary: dict) -> list[dict]:
    blocks: list[dict] = []
    blocks.append(heading1('🏥 재활 기록'))

    total = rehab_summary.get('total', 0)
    if total == 0:
        blocks.append(paragraph([rt('이번 주 재활 기록 없음.', color='gray')]))
        return blocks

    avg_pain = rehab_summary.get('avg_pain')
    avg_arm = rehab_summary.get('avg_arm_mobility')
    summary_rows = [
        ['기록 일수', f'{total}일'],
        ['평균 통증', f'{avg_pain}/10' if avg_pain is not None else '-'],
        ['평균 왼팔 움직임', f'{avg_arm}/10' if avg_arm is not None else '-'],
    ]

    cond_counts = rehab_summary.get('condition_counts', {})
    if cond_counts:
        summary_rows.append(['컨디션 분포', ' / '.join(f'{k} {v}일' for k, v in cond_counts.items())])

    mood_counts = rehab_summary.get('mood_counts', {})
    if mood_counts:
        summary_rows.append(['기분 분포', ' / '.join(f'{k} {v}일' for k, v in mood_counts.items())])

    blocks.append(table(['항목', '내용'], summary_rows))

    detail_rows = [
        [
            item['date'],
            item['condition'] or '-',
            f'{item["pain"]}/10' if item['pain'] is not None else '-',
            f'{item["arm_mobility"]}/10' if item['arm_mobility'] is not None else '-',
            item['mood'] or '-',
            item['exercises'][:50] + ('…' if len(item['exercises']) > 50 else '') if item['exercises'] else '-',
            item['memo'][:60] + ('…' if len(item['memo']) > 60 else '') if item['memo'] else '-',
        ]
        for item in rehab_items
    ]
    blocks.append(toggle_heading2(
        f'📋 재활 일별 상세 ({total}건)',
        [table(['날짜', '컨디션', '통증', '왼팔', '기분', '오늘 한 운동', '메모'], detail_rows)],
    ))

    return blocks


# ── 일기 섹션 빌더 ──────────────────────────────────────────────

def build_diary_section(
    diary_items: list[dict], diary_summary: dict, generated: dict | None = None
) -> list[dict]:
    blocks: list[dict] = []
    blocks.append(heading1('📔 일기'))

    total = diary_summary.get('total', 0)
    if total == 0:
        if generated and generated.get('entries'):
            blocks.append(callout(
                'Notion 일기 기록이 없어 캘린더·재활·Inbox 데이터를 바탕으로 AI가 정리한 회고입니다.',
                '📝', 'gray_background',
            ))
            for entry in generated['entries']:
                label = f"{entry.get('date', '')} {entry.get('day_name', '')}".strip()
                mood = entry.get('mood', '')
                text = entry.get('text', '')
                if mood:
                    text = f'{text} 기분: {mood}'
                blocks.append(paragraph([rt(f'{label} — ', bold=True), rt(text)]))
            if generated.get('weekly_summary'):
                blocks.append(callout(
                    [rt('이번 주 총평\n', bold=True), rt(generated['weekly_summary'])],
                    '💬', 'gray_background',
                ))
        else:
            blocks.append(paragraph([rt('이번 주 일기 기록 없음.', color='gray')]))
        return blocks

    summary_rows = [['작성 일수', f'{total}일']]
    mood_counts = diary_summary.get('mood_counts', {})
    if mood_counts:
        summary_rows.append(['기분/태그 분포', ' / '.join(f'{k} {v}일' for k, v in mood_counts.items())])
    blocks.append(table(['항목', '내용'], summary_rows))

    diary_children: list[dict] = []
    for item in diary_items:
        title = item['title'] or '(제목 없음)'
        mood_str = f" · {item['mood']}" if item.get('mood') else ''
        content = item.get('content') or '(본문 없음)'
        entry_children = [paragraph([rt(line)]) for line in content.split('\n') if line.strip()]
        if not entry_children:
            entry_children = [paragraph([rt('(본문 없음)', color='gray')])]
        diary_children.append(toggle_heading2(f'{item["date"]} {title}{mood_str}', entry_children))
    blocks.append(toggle_heading2(f'📋 일기 전체 목록 ({total}건)', diary_children))

    return blocks


# ── 메인 리포트 빌더 ─────────────────────────────────────────────

def build_report_blocks(
    week: dict,
    cal_by_date: dict,
    inbox_items: list[dict],
    inbox_summary: dict,
    analysis: dict,
    rehab_items: list[dict] | None = None,
    rehab_summary: dict | None = None,
    diary_items: list[dict] | None = None,
    diary_summary: dict | None = None,
    generated_diary: dict | None = None,
) -> list[dict]:
    monday, sunday = week['monday'], week['sunday']
    blocks: list[dict] = []

    # ── 헤더 ──────────────────────────────────────────────────────
    metrics = analysis.get('metrics', {})
    cal_total = metrics.get('total_calendar_events', 0)
    inbox_total = metrics.get('total_inbox_items', 0)
    inbox_rate = inbox_summary.get('process_rate', 0)

    blocks.append(callout(
        [
            rt(f'{monday} ~ {sunday}  주간 활동 분석 리포트\n', bold=True),
            rt(f'캘린더 일정 {cal_total}건  |  Inbox 캡처 {inbox_total}건  |  처리율 {inbox_rate}%'),
        ],
        '📊', 'blue_background',
    ))
    blocks.append(divider())

    # ── 주간 요약 ─────────────────────────────────────────────────
    blocks.append(heading1('📋 주간 요약'))
    overview = analysis.get('weekly_overview', '')
    if overview:
        blocks.append(callout(overview, '💬', 'gray_background'))

    # 수치 요약 테이블
    blocks.append(table(
        ['항목', '수치'],
        [
            ['캘린더 일정 수', f'{cal_total}개'],
            ['Inbox 총 항목', f'{inbox_total}개'],
            ['→ 처리 완료', f'{inbox_summary["processed"]}개'],
            ['→ 미처리', f'{inbox_summary["unprocessed"]}개'],
            ['Inbox 처리율', f'{inbox_rate}%'],
            ['캘린더 캡처율', f'{metrics.get("capture_rate_note", "-")}'],
        ],
    ))
    blocks.append(divider())

    # ── 계획 vs 실행 ──────────────────────────────────────────────
    blocks.append(heading1('📅 계획 vs 실행 분석'))

    pve = analysis.get('plan_vs_execution', {})

    # 계획대로 실행된 것
    executed = pve.get('executed_as_planned', [])
    blocks.append(heading2(f'✅ 계획대로 실행된 것 ({len(executed)}건)'))
    if executed:
        rows = [[e.get('date', ''), e.get('calendar_event', ''), e.get('inbox_item', ''), e.get('note', '')] for e in executed]
        blocks.append(table(['날짜', '캘린더(계획)', 'Inbox(실행)', '연관성'], rows))
    else:
        blocks.append(paragraph([rt('직접 매칭되는 항목이 없거나 확인 불가합니다.', color='gray')]))

    # 계획에 없었지만 캡처된 것
    unplanned = pve.get('unplanned_captures', [])
    blocks.append(heading2(f'🆕 계획에 없었지만 캡처된 것 ({len(unplanned)}건)'))
    if unplanned:
        rows = [
            [u.get('date', ''), u.get('inbox_item', ''),
             '✅ 처리완료' if u.get('processed') else '⏳ 미처리',
             u.get('insight', '')]
            for u in unplanned
        ]
        blocks.append(table(['날짜', 'Inbox 항목', '상태', '의미'], rows))
    else:
        blocks.append(paragraph([rt('캘린더 외 별도 캡처 없음.', color='gray')]))

    # 계획했지만 캡처 안 된 것
    not_captured = pve.get('planned_not_captured', [])
    blocks.append(heading2(f'❌ 계획했지만 캡처되지 않은 것 ({len(not_captured)}건)'))
    if not_captured:
        rows = [[n.get('date', ''), n.get('calendar_event', ''), n.get('reason', '')] for n in not_captured]
        blocks.append(table(['날짜', '캘린더 이벤트', '미캡처 이유'], rows))
    else:
        blocks.append(paragraph([rt('없음', color='gray')]))

    blocks.append(divider())

    # ── Inbox 출처별 분석 ─────────────────────────────────────────
    blocks.append(heading1('📥 Inbox 현황'))

    source_rows = [[src, str(cnt)] for src, cnt in inbox_summary.get('by_source', {}).items()]
    if source_rows:
        blocks.append(table(['출처', '건수'], source_rows))

    # Inbox 전체 목록 (토글)
    inbox_children: list[dict] = []
    if inbox_items:
        item_rows = [
            [
                item['date'], item['time'],
                item['title'],
                item['memo'][:40] + ('…' if len(item['memo']) > 40 else '') if item['memo'] else '',
                '✅' if item['processed'] else '⏳',
                item['source'] or '기타',
            ]
            for item in inbox_items
        ]
        inbox_children.append(table(['날짜', '시간', '제목', '메모', '처리', '출처'], item_rows))
    else:
        inbox_children.append(paragraph('이번 주 Inbox 항목 없음'))
    blocks.append(toggle_heading2(f'📋 Inbox 전체 목록 ({inbox_total}건)', inbox_children))

    blocks.append(divider())

    # ── 구글 캘린더 일정 요약 ─────────────────────────────────────
    blocks.append(heading1('📆 이번 주 구글 캘린더 일정'))
    from config import DAY_NAMES
    cal_children: list[dict] = []
    for i, d in enumerate(week['dates']):
        events = cal_by_date.get(d, [])
        day_name = DAY_NAMES[i]
        if events:
            day_rows = [
                ['종일' if ev['is_all_day'] else f'{ev["start"][11:16]}~{ev["end"][11:16]}', ev['title'], ev['calendar']]
                for ev in events
            ]
            cal_children.append(heading3(f'{day_name} {d} ({len(events)}건)'))
            cal_children.append(table(['시간', '이벤트', '캘린더'], day_rows))
        else:
            cal_children.append(bullet(f'{day_name} {d} — 일정 없음'))
    blocks.append(toggle_heading2(f'📅 일별 캘린더 ({cal_total}건)', cal_children))

    blocks.append(divider())

    # ── 인사이트 & 패턴 ──────────────────────────────────────────
    blocks.append(heading1('💡 인사이트 & 패턴'))

    insights = analysis.get('insights', [])
    for insight in insights:
        blocks.append(bullet(insight))

    patterns = analysis.get('patterns', {})
    if patterns:
        if patterns.get('strong_points'):
            blocks.append(callout(
                [rt('잘 하고 있는 점\n', bold=True), rt(patterns['strong_points'])],
                '🟢', 'green_background',
            ))
        if patterns.get('weak_points'):
            blocks.append(callout(
                [rt('개선이 필요한 점\n', bold=True), rt(patterns['weak_points'])],
                '🔴', 'red_background',
            ))
        if patterns.get('inbox_health'):
            blocks.append(callout(
                [rt('Inbox 상태\n', bold=True), rt(patterns['inbox_health'])],
                '📥', 'yellow_background',
            ))

    blocks.append(divider())

    # ── 다음 주 제안 ──────────────────────────────────────────────
    blocks.append(heading1('🚀 다음 주 제안'))

    suggestions = analysis.get('next_week_suggestions', [])
    for i, sug in enumerate(suggestions, 1):
        blocks.append(numbered(sug))

    # ── 재활 기록 ─────────────────────────────────────────────────
    if rehab_items is not None and rehab_summary is not None:
        blocks.extend(build_rehab_section(rehab_items, rehab_summary))
        blocks.append(divider())

    # ── 일기 ─────────────────────────────────────────────────────
    if diary_items is not None and diary_summary is not None:
        blocks.extend(build_diary_section(diary_items, diary_summary, generated_diary))
        blocks.append(divider())

    blocks.append(callout('Claude AI가 분석한 주간 리포트입니다.', '🤖', 'gray_background'))

    return blocks
