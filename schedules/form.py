# -*- coding: utf-8 -*-
"""
Извлечение списка опций (групп / преподавателей / аудиторий) из HTML формы.
Селекты на live-странице:  name="select_prepod" / "select_group" / "select_aud"
(подтверждено по архивам 2022 и 2025). id вида selectvalue / selectvalueaud /
selectvalueprepod — для JS. Функции здесь читают по name независимо от id.
"""
import re


def options_of(html, name):
    """Вернуть список значений (value) для <select name=...>."""
    m = re.search(r'<select[^>]*name="' + re.escape(name) + r'"[^>]*>(.*?)</select>',
                  html, re.S | re.I)
    if not m:
        return []
    seg = m.group(1)
    out = []
    for om in re.finditer(r'<option\b[^>]*\bvalue="([^"]*)"', seg):
        val = om.group(1)
        if val.strip():
            out.append(val)
    return out


def list_groups(html):
    """Группы, пригодные для -g. Отсекаем заглушки вида '1 КУРС\n'."""
    vals = options_of(html, "select_group")
    return [v for v in vals if "КУРС" not in v.upper()]


def list_prepods(html):
    return options_of(html, "select_prepod")


def list_auds(html):
    """Аудитории: чистим возможные артефакты вроде ведущего пробела."""
    vals = options_of(html, "select_aud")
    return [v.strip() for v in vals if v.strip()]
