#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер расписания ВГУИТ — точка входа.

Режимы CLI:
  1) Скачать и показать текстом расписание группы / преподавателя / аудитории
       python vs_rasp.py -g "М-211"
       python vs_rasp.py -p "Иванов И.И."
       python vs_rasp.py -a "320"
  2) Вывести JSON (для своих скриптов/telegram-бота):
       python vs_rasp.py -g "М-211" -o json
  3) Показать доступные значения селекта (для выбора перед запросом):
       python vs_rasp.py --list groups
       python vs_rasp.py --list prepods
       python vs_rasp.py --list auds

Протокол: это не API, а PHP-форма. POST index.php одним полем (select_group или
select_prepod или select_aud) + стабильный value. Один запрос = одна ось.

NB. timetable.vsuet.ru часто недоступен с хостов вне РФ (гео/фаервол). Скрипт
рассчитан на запуск с РФ-хоста либо через прокси — переменные окружения
HTTPS_PROXY / HTTP_PROXY requests подхватывает автоматически.
"""
import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

BASE_URL = "https://timetable.vsuet.ru/index.php"
FIELDNAME = {"group": "select_group", "prepod": "select_prepod",
             "aud": "select_aud"}
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def _headers():
    return {"User-Agent": UA, "Referer": BASE_URL}


def get_form(session):
    r = session.get(BASE_URL, headers={"User-Agent": UA}, timeout=40)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def post_choice(session, field, value):
    data = {FIELDNAME[field]: value, "submit": ""}
    r = session.post(BASE_URL, data=data, headers=_headers(), timeout=60)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def main():
    import requests
    from schedules.form import list_groups, list_prepods, list_auds
    from schedules.parse import extract_timetable, parse_full_schedule
    from schedules.text import render_text

    p = argparse.ArgumentParser(prog="vs_rasp", description="Расписание ВГУИТ.")
    sel = p.add_mutually_exclusive_group()
    sel.add_argument("-g", "--group", metavar="ГРУППА")
    sel.add_argument("-p", "--prepod", metavar="ФИО")
    sel.add_argument("-a", "--aud", metavar="АУД")
    p.add_argument("-o", "--out", choices=["text", "json"], default="text")
    p.add_argument("--list", choices=["groups", "prepods", "auds"],
                   help="список значений селекта по GET и выход")
    args = p.parse_args()

    s = requests.Session()
    try:
        if args.list:
            html = get_form(s)
            fn = {"groups": list_groups, "prepods": list_prepods,
                  "auds": list_auds}[args.list]
            for v in fn(html):
                print(v)
            return 0

        if args.group:
            field, value = "group", args.group
        elif args.prepod:
            field, value = "prepod", args.prepod
        elif args.aud:
            field, value = "aud", args.aud
        else:
            p.error("укажите одно из -g/-p/-a  (или --list)")
        html = post_choice(s, field, value)
    except requests.exceptions.RequestException as e:
        print(f"Сетевая ошибка: {e}", file=sys.stderr)
        print("Подсказка: endpoint скорее всего открыт только из РФ; "
              "с зарубежных хостов — таймаут. Задайте HTTPS_PROXY при СВОЁМ "
              "РФ-прокси.", file=sys.stderr)
        return 2

    if not extract_timetable(html):
        print("Не вижу таблицы расписания в ответе (разметка могла "
              "измениться или это ошибка сервера).", file=sys.stderr)
        print("Первые 800 симв. сырого ответа:\n" + html[:800], file=sys.stderr)
        return 3

    sch = parse_full_schedule(html)
    if args.out == "json":
        payload = {"query": {field: value}, "source": BASE_URL,
                   "period": sch.period,
                   "weeks": [w.to_dict() for w in sch.weeks]}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if args.group:
            label = f"группа {args.group}"
        elif args.prepod:
            label = f"преподаватель {args.prepod}"
        else:
            label = f"аудитория {args.aud}"
        print(render_text(sch, group_label=label))
    return 0


if __name__ == "__main__":
    sys.exit(main())
