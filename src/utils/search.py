"""
src.utils.search
~~~~~~~~~~~~~~~~
Обёртка над DuckDuckGo для актуализации контекста LLM свежими данными
из открытого веба. Используется ботом №4 (WebSearchBot).

Функция `search_web()` намеренно простая и устойчивая к сбоям сети:
любая ошибка возвращает пустой список, чтобы не ломать UX чата.
"""

from __future__ import annotations

import datetime as _dt
import os
import re
from typing import Any, Dict, List

# Количество сниппетов по умолчанию. Можно переопределить через .env.
DEFAULT_MAX_RESULTS: int = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5"))


# ---------------------------------------------------------------------------
# Дата и время на сервере
# ---------------------------------------------------------------------------
_WEEKDAYS_RU = {
    0: "понедельник",
    1: "вторник",
    2: "среда",
    3: "четверг",
    4: "пятница",
    5: "суббота",
    6: "воскресенье",
}
_MONTHS_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}

# Слова/фразы, при которых DuckDuckGo нужно «освежить» годом и месяцем,
# чтобы сниппеты были актуальными (а не за прошлые годы).
_TIME_HINTS = re.compile(
    r"\b(сегодня|вчера|сейчас|сейчас\.|на\s+этой\s+неделе|"
    r"на\s+прошлой\s+неделе|в\s+этом\s+месяце|в\s+прошлом\s+месяце|"
    r"в\s+этом\s+году|текущ\w*|актуальн\w*|последн\w*|новост[ьи])\b",
    re.IGNORECASE,
)


def get_server_date_info(now: _dt.datetime | None = None) -> str:
    """
    Возвращает человекочитаемую строку с текущей датой/временем на сервере.

    Пример: ``"Сегодня понедельник, 5 октября 2026 года. Текущее время: 14:32."``
    """
    now = now or _dt.datetime.now()
    weekday = _WEEKDAYS_RU[now.weekday()]
    month = _MONTHS_RU[now.month]
    return (
        f"Сегодня {weekday}, {now.day} {month} {now.year} года. "
        f"Текущее время: {now.strftime('%H:%M')}."
    )


def augment_query_with_date(query: str, now: _dt.datetime | None = None) -> str:
    """
    Если в запросе есть «сегодня/вчера/сейчас/…», подмешивает год и месяц,
    чтобы DuckDuckGo возвращал свежие сниппеты, а не архивные.
    """
    if not query or not _TIME_HINTS.search(query):
        return query
    now = now or _dt.datetime.now()
    month = _MONTHS_RU[now.month]
    return f"{query} ({now.year}, {month} {now.year})"


def search_web(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> List[Dict[str, Any]]:
    """
    Выполняет текстовый поиск в DuckDuckGo и возвращает список сниппетов.

    Каждый элемент списка — dict с ключами:
        * ``title``  — заголовок результата;
        * ``href``   — URL источника;
        * ``body``   — текстовый сниппет (краткое описание страницы).

    При любой ошибке (нет сети, библиотека не установлена, бан от DDG)
    функция возвращает ``[]`` — вызывающий код решает, как жить дальше.
    """
    if not query or not query.strip():
        return []

    try:
        # Локальный импорт: ddgs (бывший duckduckgo-search) опционален,
        # без него бот просто работает без web-augmentation.
        from ddgs import DDGS
    except Exception:  # noqa: BLE001
        return []

    results: List[Dict[str, Any]] = []
    try:
        with DDGS() as ddgs:
            # ``text`` — обычный веб-поиск (не изображения, не новости).
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    {
                        "title": r.get("title", ""),
                        "href": r.get("href", ""),
                        "body": r.get("body", ""),
                    }
                )
    except Exception:  # noqa: BLE001
        # Сеть недоступна, DDG забанил, таймаут — для UX это не критично.
        return []

    return results


def format_snippets_for_prompt(snippets: List[Dict[str, Any]]) -> str:
    """
    Превращает список сниппетов в блок текста, пригодный для вставки
    в system-промпт. Пустой ввод → пустая строка.
    """
    if not snippets:
        return ""

    lines: List[str] = []
    for i, s in enumerate(snippets, 1):
        title = (s.get("title") or "").strip()
        body = (s.get("body") or "").strip()
        href = (s.get("href") or "").strip()
        lines.append(f"{i}. {title}\n   {body}\n   Источник: {href}")
    return "\n\n".join(lines)
