# -*- coding: utf-8 -*-
# Пакет парсинга расписания ВГУИТ.
__all__ = ["extract_timetable", "parse_full_schedule", "looks_like_timetable",
           "ParsedSchedule"]
from .parse import (extract_timetable, looks_like_timetable,
                    parse_full_schedule, ParsedSchedule)
from .form import list_groups, list_prepods, list_auds, options_of
from .text import render_text
