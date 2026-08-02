"""월간 리포트용 Notion 블록 빌더 (주간 블록 빌더를 재사용)."""
from datetime import date

from blocks import (
    rt, divider, heading1, heading2, heading3, callout, bullet, numbered,
    paragraph, table, toggle_heading2, build_rehab_section, build_diary_section,
)
from config import DAY_NAMES


def build_monthly_report_blocks(
    month: dict,
    cal_by_date: dict,
    inbox_items: list[dict],
    inbox_summary: dict,
    weekly_breakdown: list[dict],
    analysis: dict,
    rehab_items: list[dict] | None = None,
    rehab_summary: dict | None = None,
    diary_items: list[dict] | None = None,
    diary_summary: dict | None = None,
    generated_diary: dict | None = None,
) -> list[dict]:
    year, mon = month['year'], month['month']
    blocks: list[dict] = []

    # ── 헤더 ──────────────────────────────────────────────────────
    metrics = analysis.get('metrics', {})
    cal_total = metrics.get('total_calendar_events', 0)
    inbox_total = metrics.get('total_inbox_items', 0)
    inbox_rate = inbox_summary.get('process_rate', 0)

    blocks.append(callout(
        [
            rt(f'{year}년 {mon}월  월간 활동 분석 리포트\n', bold=True),
            rt(f'캘린더 일정 {cal_total}건  |  Inbox 캡처 {inbox_total}건  |  처리율 {inbox_rate}%'),
        ],
        '🗓️', 'blue_background',
    ))
    blocks.append(divider())

    # ── 월간 요약 ─────────────────────────────────────────────────
    blocks.append(heading1('📋 월간 요약'))
    overview = analysis.get('monthly_overview', '')
    if overview:
        blocks.append(callout(overview, '💬', 'gray_background'))

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

    # ── 주차별 흐름 ───────────────────────────────────────────────
    blocks.append(heading1('📈 주차별 흐름'))

    trend_map = {t.get('week_start'): t.get('insight', '') for t in analysis.get('weekly_trend', [])}
    week_rows = [
        [w['monday'], f'{w["cal_count"]}건', f'{w["inbox_total"]}건', f'{w["inbox_process_rate"]}%']
        for w in weekly_breakdown
    ]
    if week_rows:
        blocks.append(table(['주 시작일', '캘린더', 'Inbox', '처리율'], week_rows))

    for w in weekly_breakdown:
        insight = trend_map.get(w['monday'])
        if insight:
            blocks.append(bullet([rt(f'{w["monday"]} 주: ', bold=True), rt(insight)]))

    blocks.append(divider())

    # ── 계획 vs 실행 ──────────────────────────────────────────────
    blocks.append(heading1('📅 계획 vs 실행 분석'))

    pve = analysis.get('plan_vs_execution', {})

    executed = pve.get('executed_as_planned', [])
    blocks.append(heading2(f'✅ 계획대로 실행된 것 (대표 {len(executed)}건)'))
    if executed:
        rows = [[e.get('date', ''), e.get('calendar_event', ''), e.get('inbox_item', ''), e.get('note', '')] for e in executed]
        blocks.append(table(['날짜', '캘린더(계획)', 'Inbox(실행)', '연관성'], rows))
    else:
        blocks.append(paragraph([rt('직접 매칭되는 항목이 없거나 확인 불가합니다.', color='gray')]))

    unplanned = pve.get('unplanned_captures', [])
    blocks.append(heading2(f'🆕 계획에 없었지만 캡처된 것 (대표 {len(unplanned)}건)'))
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

    not_captured = pve.get('planned_not_captured', [])
    blocks.append(heading2(f'❌ 계획했지만 캡처되지 않은 것 (대표 {len(not_captured)}건)'))
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
        inbox_children.append(paragraph('이번 달 Inbox 항목 없음'))
    blocks.append(toggle_heading2(f'📋 Inbox 전체 목록 ({inbox_total}건)', inbox_children))

    blocks.append(divider())

    # ── 구글 캘린더 일정 (주차별 토글) ────────────────────────────
    blocks.append(heading1('📆 이번 달 구글 캘린더 일정'))

    cal_week_children: list[dict] = []
    for w in weekly_breakdown:
        week_children: list[dict] = []
        for d in w['dates']:
            events = cal_by_date.get(d, [])
            day_name = DAY_NAMES[date.fromisoformat(d).weekday()]
            if events:
                day_rows = [
                    ['종일' if ev['is_all_day'] else f'{ev["start"][11:16]}~{ev["end"][11:16]}', ev['title'], ev['calendar']]
                    for ev in events
                ]
                week_children.append(heading3(f'{day_name} {d} ({len(events)}건)'))
                week_children.append(table(['시간', '이벤트', '캘린더'], day_rows))
            else:
                week_children.append(bullet(f'{day_name} {d} — 일정 없음'))
        cal_week_children.append(toggle_heading2(f'{w["monday"]} 주 ({w["cal_count"]}건)', week_children))
    blocks.append(toggle_heading2(f'📅 주차별 캘린더 ({cal_total}건)', cal_week_children))

    blocks.append(divider())

    # ── 인사이트 & 패턴 ──────────────────────────────────────────
    blocks.append(heading1('💡 인사이트 & 패턴'))

    for insight in analysis.get('insights', []):
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

    # ── 다음 달 제안 ──────────────────────────────────────────────
    blocks.append(heading1('🚀 다음 달 제안'))

    for sug in analysis.get('next_month_suggestions', []):
        blocks.append(numbered(sug))

    # ── 재활 기록 ─────────────────────────────────────────────────
    if rehab_items is not None and rehab_summary is not None:
        blocks.extend(build_rehab_section(rehab_items, rehab_summary, period_label='이번 달'))
        blocks.append(divider())

    # ── 일기 ─────────────────────────────────────────────────────
    if diary_items is not None and diary_summary is not None:
        blocks.extend(build_diary_section(diary_items, diary_summary, generated_diary, period_label='이번 달'))
        blocks.append(divider())

    blocks.append(callout('Claude AI가 분석한 월간 리포트입니다.', '🤖', 'gray_background'))

    return blocks
