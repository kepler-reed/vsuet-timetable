# Расписание ВГУИТ — парсер (`timetable.vsuet.ru`)

Python-парсер расписания Воронежского государственного университета инженерных
технологий. Форма-сайт — не API: отправляется POST на `index.php` одним из полей
`select_prepod` / `select_group` / `select_aud`, возвращается HTML-таблица.

## Быстрый старт

```bash
pip install requests beautifulsoup4 lxml     # единственные зависимости

python vs_rasp.py -g "М-211"                  # текстом: группа
python vs_rasp.py -a "320"                    # по аудитории
python vs_rasp.py -p "Иванов И.И."            # по преподавателю

python vs_rasp.py -g "М-211" -o json          # JSON для бота/своих скриптов
python vs_rasp.py --list groups               # список доступных групп
python vs_rasp.py --list prepods              # или преподавателей / auds
```

`#providerid` не требуется — это открытая форма. Список точных значений для
`-g / -p / -a` всегда берёте через `--list`, т.к. движок требует точного `value`.

## ВАЖНО о доступности

Сервер `timetable.vsuet.ru` (93.88.139.15) с хостов **вне РФ**, как правило,
недоступен (гео/фаервол вуза) — соединение уходит в таймаут. Парсер рассчитан
на запуск **с российского хоста** либо через прокси:

```bash
HTTPS_PROXY="http://user:pass@host:port" python vs_rasp.py -g "М-211"
```

Переменные окружения `HTTPS_PROXY`/`HTTP_PROXY` подхватываются автоматически.

## Что умеет разбор

| Вход                          | Результат                                                |
|-------------------------------|----------------------------------------------------------|
| `опции селектов`              | `--list groups/prepods/auds`                             |
| `HTML ответа POST`            | структура `ParsedSchedule` (недели → дни → занятия)      |
| `-o json`                     | валидный JSON на выход                                    |

Модель занятия: `num, time, subject, type, teacher, room, building, week,
subgroup, comment`.

## Структура проекта

```
vs-rasp/
  vs_rasp.py            # CLI: сеть (GET списков / POST выбора) + вывод
  schedules/
    parse.py            # таблица -> сетка(с учётом rowspan/colspan) -> Lesson
    form.py             # чтение опций select_prepod/select_group/select_aud
    text.py             # человекочитаемый рендер
  tests/
    _synthetic.py       # fixture: типовая сетка расписания
    run_tests.py        # самопроверка (без сети)
```

## Самопроверка (без интернета)

```bash
cd vs-rasp
python tests/run_tests.py     # ожидаем "12 ok, 0 fail"
```

## Про реальную разметку (почему парсер «устойчивый», а не на коленке)

Спокойный факт: форма и общая вёрстка подтверждены архивными live-копиями
(2022 и 2025 идентичны). Саму таблицу-результат архив браузеров не сохраняет
(форма — JS-submit), поэтому парсер разворачивает любую таблицу в
прямоугольную сетку, находит строку дней недели по словарю имён (Пн..Вс),
а колонки-«предметы» бьёт эвристиками (тип в скобках, `каб./ауд./к.` + номер,
корпус-буква рядом, ФИО в конце). Это не привязано к конкретному HTML и
переживает мелкие правки движка.

**Если после запуска из РФ разметка окажется иной** (например, дни в отдельных
таблицах по неделям), не надо переписывать потребителя — правки только внутри
`cell_to_lesson`/`carve_lesson`/`_absorb`. Снимите сырой HTML:

```bash
python -c "import requests,sys; \
r=requests.post('https://timetable.vsuet.ru/index.php', \
data={'select_group':'М-211','submit':''},headers={'User-Agent':'Mozilla/5.0'}); \
open('live.html','w').write(r.text)"   # затем: cp live.html tests/fixtures/live.html
python tests/run_tests.py              # добавит проверку на живом снепшоте
```

Положите снимок в `tests/fixtures/live.html` — тест автоматически распознает и
разберёт реальные данные.
