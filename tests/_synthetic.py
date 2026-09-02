# -*- coding: utf-8 -*-
"""Синтетическая страница-ответ: повторяет типовую сетку движка расписаний.

Используется ТОЛЬКО для самопроверки логики разбора (grid, дни, cell_to_lesson),
не как настоящий снимок live-ответа (его отсюда достать нельзя — нет доступа из
РФ). После получения реального HTML по тесту в РФ положите его в
tests/fixtures/live.html и запустите python tests/run_tests.py — разбор
проверится и на живых данных (fixture live.html опционален).
"""

HTML = """
<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"></head><body>
<div class="container">
  <div class="card-header"><h5>РАСПИСАНИЕ УЧЕБНЫХ ЗАНЯТИЙ</h5></div>
  <div class="card-body"><div id="res">
    <div class="period">Группа М-211 · неделя с 07.04.2025 по 13.04.2025</div>
    <table class="table table-bordered">
      <tr class="head">
        <th>№</th>
        <th>Время</th>
        <th>Пн 07.04</th><th>Вт 08.04</th><th>Ср 09.04</th>
        <th>Чт 10.04</th><th>Пт 11.04</th>
      </tr>
      <tr>
        <td>1.</td><td>08:30-10:05</td>
        <td>Математика (лекция)<br/>каб. 320</td>
        <td>Физика (лекция)<br/>ауд. 215</td>
        <td></td><td>Английский (практика)<br/>каб. 108</td><td></td>
      </tr>
      <tr>
        <td>2.</td><td>10:15-11:50</td>
        <td></td>
        <td>История (семинар)<br/>Б к. 415</td>
        <td>Математика (практика)<br/>каб. 320</td>
        <td></td><td>Физкультура<br/>спортзал</td>
      </tr>
      <tr>
        <td>3.</td><td>12:00-13:35</td>
        <td>Химия (лаб)<br/>ауд. 1-05</td>
        <td></td><td></td>
        <td>Информатика (лекция)<br/>каб. 218</td><td></td>
      </tr>
    </table>
  </div></div>
</div></body></html>
"""
