# -*- coding: utf-8 -*-
"""
Семантический парсинг HTML-таблиц расписания ВГУИТ (timetable.vsuet.ru).

Форма и общая вёрстка подтверждены по архивным live-копиям (2022 и 2025 —
идентичны): POST index.php одним из полей select_prepod / select_group /
select_aud. Разметку самой таблицы результата браузерный архив не хранит
(форма уходит в JS-submit), поэтому парсер построен УСТОЙЧИВО и не завязан на
конкретный HTML: разворачивает таблицу в прямоугольную сетку с учётом
rowspan/colspan, находит строку дней недели по словарю имён, а каждую ячейку
разбирает эвристиками на предмет/тип/преподв/аудиторию.

Если живой ответ из РФ покажет иную структуру (например, дни в отдельной
таблице на неделю) — правятся только функции ниже, публичная модель данных
(Lesson / DaySlots / WeekEntry / ParsedSchedule) остаётся неизменной.
"""
import re
from dataclasses import dataclass, field

WEEKDAYS_RU = ["понедельник", "вторник", "среда", "четверг",
               "пятница", "суббота", "воскресенье"]

# --------------------------------------------------------------------------- #
#  Модель данных
# --------------------------------------------------------------------------- #
@dataclass
class Lesson:
    num: str = ""        # «1», «2», «3-4»
    time: str = ""       # «08:30-10:05»
    subject: str = ""
    type: str = ""       # лек/пр/лаб/семинар/зачёт/…
    teacher: str = ""    # для расписания группы
    groups: list = field(default_factory=list)  # для расписания преподавателя
    room: str = ""       # «320», «1-05»
    building: str = ""   # корпус-буква, если стоит рядом с номером
    subgroup: str = ""
    week: str = ""
    comment: str = ""

    def to_dict(self):
        return {"num": self.num, "time": self.time, "subject": self.subject,
                "type": self.type, "teacher": self.teacher,
                "groups": list(self.groups), "room": self.room,
                "building": self.building, "subgroup": self.subgroup,
                "week": self.week, "comment": self.comment}


@dataclass
class DaySlots:
    weekday: int
    label: str
    date_label: str = ""
    lessons: list = field(default_factory=list)

    def to_dict(self):
        return {"weekday": self.weekday, "label": self.label,
                "date_label": self.date_label,
                "lessons": [l.to_dict() for l in self.lessons]}


@dataclass
class WeekEntry:
    label: str = ""
    days: list = field(default_factory=list)

    def to_dict(self):
        return {"label": self.label, "days": [d.to_dict() for d in self.days]}


@dataclass
class ParsedSchedule:
    period: str = ""
    weeks: list = field(default_factory=list)

    def to_dict(self):
        return {"period": self.period,
                "weeks": [w.to_dict() for w in self.weeks]}


# --------------------------------------------------------------------------- #
#  Примитивы текста
# --------------------------------------------------------------------------- #
_DAY_ALIAS = {
    "пн": 0, "пон": 0, "понедельник": 0,
    "вт": 1, "втор": 1, "вторник": 1,
    "ср": 2, "сред": 2, "среда": 2,
    "чт": 3, "чет": 3, "четверг": 3,
    "пт": 4, "пят": 4, "пятница": 4,
    "сб": 5, "суб": 5, "суббота": 5,
    "вс": 6, "воск": 6, "воскресенье": 6,
}


def norm_day_token(tok):
    t = re.sub(r"[^а-яёa-z]", "", (tok or "").lower())
    if len(t) < 2:
        return None
    for k, v in _DAY_ALIAS.items():
        if t == k or (len(t) <= 4 and k.startswith(t)):
            return v
    m = re.match(r"(пн|вт|ср|чт|пт|сб|вс)", t)
    return _DAY_ALIAS[m.group(1)] if m else None


_TIME_SPAN = re.compile(
    r"(\d{1,2})[:.](\d{2})\s*[-–—]\s*(\d{1,2})[:.](\d{2})")
_TIME_SPAN_PREFIX = re.compile(
    r"^\s*\d{1,2}[:.]\d{2}\s*[-–—]\s*\d{1,2}[:.]\d{2}\s+")


def norm_time_field(text):
    m = _TIME_SPAN.search(text or "")
    if m:
        return ((int(m.group(1)), int(m.group(2))),
                (int(m.group(3)), int(m.group(4))))
    return None


def _fmt_time(b):
    return f"{b[0][0]:02d}:{b[0][1]:02d}-{b[1][0]:02d}:{b[1][1]:02d}"


def subject_and_type(text):
    """«МАТЕМАТИКА (лекция)» -> ('МАТЕМАТИКА', 'лекция'); иначе ("",'') при пусто."""
    text = re.sub(r"\s+", " ", text or "").strip()
    m = re.search(r"^(.*?)\s*\(([^)]*)\)\s*$", text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return text, ""


# --------------------------------------------------------------------------- #
#  Разбор клетки -> Lesson(details)
# --------------------------------------------------------------------------- #
_ROOM_KW = ["каб", "ауд", "комп", "к"]
_ROOM_RE = re.compile(
    r"(?P<kw>каб\.?|комп\.?|ауд\.?|к\.)\s*(?P<num>[0-9][0-9a-zа-яё-]{0,5})",
    re.I)
_TEACH_WORD = re.compile(r"([А-ЯЁ][а-яё]{2,}(?:\s+[А-ЯЁ]\.[А-ЯЁ]?\.?)?)\s*$")
_SUBJ_TRAILER = re.compile(
    r"^(.*?)\s*[,;–—|·]\s+(.*)$")  # «тема: деталь»
_RE_META_WORD = re.compile(
    r"(лекция|лекции|лабораторная|лабораторн|лаб|практика|практическ|"
    r"практ|семинар|зачёт|зачет|экзамен|консультация|курсовая|ч\s*н\b|"
    r"нечётная|чётная)", re.I)


def _only_letters(s):
    return re.sub(r"[^А-ЯЁа-яёA-Za-z0-9]", "", s or "")


def carve_lesson(text):
    """Сырой текст ячейки -> (subject, teacher, room, building)."""
    t = re.sub(r"\s+", " ", (text or "")).strip()
    teacher = room = building = ""

    # ---- аудитория + корпус -----------------------------------------------
    rm = _ROOM_RE.search(t)
    if rm:
        room = rm.group("num")
        pre = t[: rm.start()]
        post = t[rm.end():]
        # корпус-буква сразу перед маркером/номером: «Б к. 415», «Б415»
        bm = re.search(r"([А-ЯЁ])\s*[- ]?$", pre) or \
             re.search(r"([А-ЯЁ])$", pre)
        if bm and len(_only_letters(pre[: bm.start()])) <= 1:
            building = bm.group(1)
            pre = pre[: bm.start()]
        t = f"{pre} {post}".strip()
    # форма «Б415» без маркера (номер слитно) — ауд уже распознана как token нет;
    # здесь оставляем subject прежним, а корпус ловим в subject ниже.

    # ---- преподаватель (в конце) ------------------------------------------
    while True:
        tm = _TEACH_WORD.search(t)
        if not tm:
            break
        cand = tm.group(1)
        lastword = cand.split()[0]
        # отбрасываем очевидно-терминологические хвосты
        if _RE_META_WORD.search(cand):
            break
        teacher = cand
        t = t[: tm.start()].strip(" \t,;–—|·")
        break
    subject = t.strip(" \t,;–—|·")
    # если и препод, и ауд остаются на своём — после первого прохода типовой
    # subject уже чист.
    return subject, teacher, room, building


def cell_to_lesson(cell_text, num="", bounds=None):
    """Одна ячейка -> Lesson либо None."""
    t = re.sub(r"\s+", " ", cell_text or "").strip()
    if not t or t.lower() in ("-", "—", ""):
        return None
    # вынести время из начала, если оно есть только в ячейке (не в колонке)
    if bounds is None:
        mt = norm_time_field(t)
        if mt:
            bounds = mt
            t = _TIME_SPAN_PREFIX.sub("", t).strip()
    subject, teacher, room, building = carve_lesson(t)
    les = Lesson(num=num,
                 time=_fmt_time(bounds) if bounds else "",
                 subject="", teacher=teacher, room=room, building=building)
    if subject:
        les.subject, mtype = subject_and_type(subject)
        if mtype:
            les.type = mtype
    les.comment = t
    if not (les.subject or les.teacher or les.room):
        return None
    return les


# --------------------------------------------------------------------------- #
#  Таблица -> прямоугольная сетка
# --------------------------------------------------------------------------- #
def celltext(tag):
    # get_text + концы строк для block-элементов нам не даёт bs4 по умолчанию,
    # поэтому разделяем текст участков на строки «сверху вниз», как в визуале:
    parts = []
    for s in tag.strings:
        s = re.sub(r"\s+", " ", s).strip()
        if s:
            parts.append(s)
    joined = " ".join(parts)
    # опустим деталь: объединяем, две строки разделялись бы пробелом — этого
    # достаточно для эвристик на разделение «предмет (тип) каб».
    return re.sub(r"\s+", " ", joined).strip()


def grid_from_table(table):
    """Развернуть <table> (bs4) в прямоугольную сетку текстов (rowspan/colspan
    учтены). list[list[str]]."""
    rows = []
    for tr in table.find_all("tr"):
        cells = tr.find_all(["td", "th"], recursive=False)
        rows.append([(c, int(c.get("rowspan", 1) or 1),
                      int(c.get("colspan", 1) or 1)) for c in cells])
    H = len(rows)
    W = max((sum(cs for _, _, cs in row) for row in rows),
            default=0)
    grid = [[""] * W for _ in range(H)]
    for ri, row in enumerate(rows):
        col = 0
        for cell, rs, cs in row:
            while col < W and grid[ri][col]:
                col += 1
            txt = celltext(cell)
            for dr in range(rs):
                for dc in range(cs):
                    if ri + dr < H and col + dc < W:
                        grid[ri + dr][col + dc] = txt
            col += cs
    while W and all(grid[r][W - 1] == "" for r in range(H)):
        for r in range(H):
            grid[r].pop()
        W -= 1
    return grid


# --------------------------------------------------------------------------- #
#  Поиск таблиц-«сеток днями»
# --------------------------------------------------------------------------- #
def extract_timetable(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    out = []
    for table in soup.find_all("table"):
        g = grid_from_table(table)
        if not g:
            continue
        has_day = any(norm_day_token(c) is not None for row in g for c in row)
        has_time = any(norm_time_field(c) for row in g for c in row)
        # сетка расписания: широкий (>=3 колонки), дни недели и/или время
        wide = max(len(r) for r in g) >= 3
        if has_day and wide:
            out.append(table)
        elif has_time and has_day:
            out.append(table)
        elif has_time and wide:
            out.append(table)
    return out


def looks_like_timetable(html):
    return bool(extract_timetable(html))


# --------------------------------------------------------------------------- #
#  Полный разбор
# --------------------------------------------------------------------------- #
def parse_full_schedule(html):
    res = ParsedSchedule()
    for table in extract_timetable(html):
        _absorb(res, table)
    return res


def _header_daycols(grid):
    """Найти строку заголовка дней; вернуть (row_idx, [(col, weekday)])."""
    best = None
    for ri, row in enumerate(grid):
        pairs = [(ci, norm_day_token(c)) for ci, c in enumerate(row)
                 if norm_day_token(c) is not None]
        if len(pairs) >= 3:
            # заголовок дней почти всегда единственная строка со столькими именами
            if best is None or len(pairs) > len(best[1]):
                best = (ri, pairs)
    return best or (None, [])


def _absorb(result, table):
    grid = grid_from_table(table)
    if not grid:
        return
    hrow, day_pairs = _header_daycols(grid)
    if hrow is None:
        return
    period = _try_period(table)
    week = WeekEntry(label=period)
    # колонка на день: берём первый распознан. день за индекс места в строке
    week_by_idx = {ci: wd for ci, wd in day_pairs}
    sorted_cols = sorted(week_by_idx.keys())

    # Время на пару ищется в тех же строках ниже: колонка-время обычно первая/
    # через 'Время'. Пробуем сопоставить время по строкам, где это имеет смысл.
    # Для простоты читаем строки построчно и время берём из первой колонки,
    # имеющей диапазон (норма движка: колонка времени следует за № пары).
    cols_of_time = [ci for ci in range(len(grid[hrow]))
                    if ci not in week_by_idx
                    and any(norm_time_field(grid[r][ci])
                            for r in range(hrow + 1, len(grid)))]

    for d in sorted(set(week_by_idx.values())):  # гарантия всех дней в порядке
        col = next(ci for ci, wd in week_by_idx.items() if wd == d)
        _fill_day_cell(week, grid, hrow, col, d, cols_of_time)
    result.weeks.append(week)


def _fill_day_cell(week, grid, hrow, col, weekday, cols_time):
    day = _ensure_day(week, weekday)
    cur_num = ""
    cur_bounds = None
    for ri in range(hrow + 1, len(grid)):
        rowval = grid[ri][col] if col < len(grid[ri]) else ""
        # № пары и время из всей строки (обычно колонки слева)
        for tci in cols_time:
            b = norm_time_field(grid[ri][tci]) if tci < len(grid[ri]) else None
            if b:
                cur_bounds = b
                break
        mm = None
        for ci in range(0, col):
            mm = re.match(r"\s*(\d{1,2}(?:[-–—]\d{1,2})?|пер|вт|тр|чет|пят)\s*[.)]",
                          grid[ri][ci] or "")
            if mm:
                cur_num = mm.group(1)
                break
        cell = rowval or ""
        if cell and cell not in ("-", "—"):
            les = cell_to_lesson(cell, cur_num, cur_bounds)
            if les:
                day.lessons.append(les)


def _ensure_day(week, weekday):
    for d in week.days:
        if d.weekday == weekday:
            return d
    day = DaySlots(weekday=weekday,
                   label=WEEKDAYS_RU[weekday % 7].capitalize())
    week.days.append(day)
    week.days.sort(key=lambda x: x.weekday)
    return day


def _try_period(table):
    cap = table.find("caption")
    if cap and cap.get_text(strip=True):
        return re.sub(r"\s+", " ", cap.get_text(" ", strip=True)).strip()
    for cell in table.find_all(["th"]):
        tx = re.sub(r"\s+", " ", cell.get_text(" ", strip=True)).strip()
        if re.search(r"(недел|с \d{1,2}\.\d{1,2}|период)", tx, re.I):
            return tx
    return ""
