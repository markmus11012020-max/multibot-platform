"""
src.utils.search
~~~~~~~~~~~~~~~~
Обёртка над DuckDuckGo для актуализации контекста LLM свежими данными
из открытого веба. Используется ботом №4 (WebSearchBot).

Функция `search_web()` намеренно простая и устойчивая к сбоям сети:
любая ошибка возвращает пустой список, чтобы не ломать UX чата.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

# Количество сниппетов по умолчанию. Можно переопределить через .env.
DEFAULT_MAX_RESULTS: int = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5"))


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
        # Локальный импорт: duckduckgo-search опционален, без него бот
        # просто работает без web-augmentation.
        from duckduckgo_search import DDGS
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
