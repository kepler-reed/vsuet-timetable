# -*- coding: utf-8 -*-
"""Самопроверка парсера на синтетике + (опционально) на живом снапшоте.

Запуск:  cd /home/hermes/vs-rasp && python tests/run_tests.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schedules.parse import (extract_timetable, parse_full_schedule,
                             grid_from_table)  # noqa: E402
from schedules.text import render_text  # noqa: E402
from schedules.form import options_of, list_groups  # noqa: E402

PASS = 0
FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok  - {name}")
    else:
        FAIL += 1
        print(f"FAIL  - {name}  {extra}")


def main():
    print("== 1. Синтетическая таблица (проверка логики разбора) ==")
    from tests import _synthetic  # fixture
    html = _synthetic.HTML

    tables = extract_timetable(html)
    check("найдена ровно 1 таблица расписания", len(tables) == 1,
          f"len={len(tables)}")

    sch = parse_full_schedule(html)
    check("получены недели", len(sch.weeks) >= 1, f"weeks={len(sch.weeks)}")

    # соберём все занятия
    all_lessons = []
    day_index = {}  # (week_idx, weekday) -> [lessons]
    for wi, wk in enumerate(sch.weeks):
        for d in wk.days:
            day_index[(wi, d.weekday)] = d.lessons
            all_lessons.extend(d.lessons)
    check("есть занятия", len(all_lessons) > 0, f"lessons={len(all_lessons)}")

    # Пн пара 1 — Математика
    mon = day_index.get((0, 0), [])
    check("Пн: 1 пара", any("Математика" == l.subject and l.num == "1" for l in mon),
          str([(l.num, l.subject) for l in mon]))
    math_les = next((l for l in mon if l.num == "1"), None)
    if math_les:
        check("Пн 1: тип лекция", math_les.type.lower().startswith("лекц"),
              f"type={math_les.type!r}")
        check("Пн 1: время", math_les.time == "08:30-10:05",
              f"time={math_les.time!r}")
        check("Пн 1: аудитория 320", math_les.room == "320",
              f"room={math_les.room!r}")

    # Ср пара 2 — Математика практика
    wed = day_index.get((0, 2), [])
    check("Ср: 2 пара практика",
          any(l.num == "2" and l.subject == "Математика" and
              l.type.lower().startswith("практ") for l in wed),
          str([(l.num, l.subject, l.type) for l in wed]))

    # Вт пара 3 у нас пусто; Химия в Пн пара 3
    check("Пн 3: Химия", any(l.num == "3" and l.subject == "Химия"
                             for l in day_index.get((0, 0), [])))
    # 6-й день (Сб) не объявлялся в заголовке — будет пропущен
    sats = day_index.get((0, 5), [])
    check("Сб не изобретаем лишних занятий", len(sats) == 0)

    print("\n== 2. Рендер ==")
    txt = render_text(sch)
    check("рендер непустой", len(txt) > 20)
    print("---- начало текстового вывода ----")
    print("\n".join(txt.splitlines()[:22]))

    print("\n== 3. URL-кодированный логин формы и списки ==")
    # Псевдо-форма (те же name, что в архиве) для list_groups
    form_html = ('<select name="select_group"><option value="">x</option>'
                 '<option value="М-211">М-211</option>'
                 '<option value="1 КУРС\n">1 КУРС</option>'
                 '<option value="Т-312">Т-312</option></select>')
    gl = list_groups(form_html)
    check("list_groups фильтрует КУРС и пустые", gl == ["М-211", "Т-312"], str(gl))

    print("\n== (опционально) живой snapshot ==")
    live = os.path.join(os.path.dirname(__file__), "fixtures", "live.html")
    if os.path.exists(live) and os.path.getsize(live) > 500:
        raw = open(live, encoding="utf-8", errors="replace").read()
        tables = extract_timetable(raw)
        check("live: найдена таблица", len(tables) >= 1, f"len={len(tables)}")
        if tables:
            sch = parse_full_schedule(raw)
            n = sum(len(d.lessons) for w in sch.weeks for d in w.days)
            check("live: есть занятия", n > 0, f"lessons={n}")
            if n:
                print("Сырой рендер:\n" + render_text(sch)[:1500])
    else:
        print("  (нет live.html — не проверяю)")

    print(f"\nИТОГ: {PASS} ok, {FAIL} fail")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
