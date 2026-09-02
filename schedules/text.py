# -*- coding: utf-8 -*-
"""Человекочитаемый вывод ParsedSchedule."""
from datetime import date

_WD = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def _lesson_line(l):
    head = ""
    if l.time:
        head = l.time + "  "
    s = l.subject
    if l.type:
        s = f"{s} ({l.type})"
    mid = " " if head else ""
    extras = []
    if l.teacher:
        extras.append(l.teacher)
    if l.room:
        extras.append(f"ауд. {l.room}" + (f" ({l.building})" if l.building else ""))
    elif l.building:
        extras.append(f"(корп. {l.building})")
    if l.groups:
        extras.append("гр. " + ",".join(l.groups))
    if l.subgroup:
        extras.append(l.subgroup)
    if l.week:
        extras.append(f"[{l.week}]")
    if extras:
        return head + mid + s + " — " + ", ".join(extras)
    return head + mid + s


def render_text(sch, group_label=None):
    lines = []
    if group_label:
        lines.append(f"Расписание: {group_label}")
    for wk in sch.weeks:
        if wk.label:
            lines.append("")
            lines.append(wk.label)
        for day in wk.days:
            head = f"{_WD[day.weekday % 7]}"
            if day.date_label:
                head += f" ({day.date_label})"
            lines.append("")
            lines.append(head)
            if not day.lessons:
                lines.append("   —")
            for l in day.lessons:
                num = l.num + "." if l.num else "·"
                lines.append(f" {num:<3} {_lesson_line(l)}")
    return "\n".join(lines)


def current_isoweek():
    return date.today().isocalendar()[:2]
