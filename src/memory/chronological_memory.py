"""
src.memory.chronological_memory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Краткосрочная память, хранящая хронологию диалога в SQLite.

Используется Ботом №2 (SessionBot) как замена ``SessionMemory``:
    * ``build_context`` подтягивает последние N реплик из БД;
    * ``remember``      пишет обе реплики (user + bot) в БД;
    * ``clear``         стирает историю сессии в БД.

Это решает проблему «векторная база не сохраняет хронологию»: SQLite —
источник правды по порядку сообщений, FAISS — только для семантического
поиска архивных фактов.
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.memory.base import BaseMemory
from src.utils.db_history import (
    clear_chat_history,
    get_chat_history,
    get_stats,
    save_message,
)


class ChronologicalDBMemory(BaseMemory):
    """Хронологическая память на SQLite."""

    name = "chronological_db"

    def __init__(self, session_key: str, history_limit: int = 20):
        self.session_key = session_key
        self.history_limit = history_limit

    # ---- Контекст для LLM ----
    def build_context(
        self,
        prompt: str,
        session_messages: List[Dict[str, str]] | None = None,  # noqa: ARG002
    ) -> List[Dict[str, str]]:
        """
        Возвращает последние ``history_limit`` реплик из SQLite +
        текущий ``prompt`` (если его ещё нет в последней записи).
        """
        history = get_chat_history(self.session_key, limit=self.history_limit)
        if not history or history[-1] != {"role": "user", "content": prompt}:
            history.append({"role": "user", "content": prompt})
        return history

    # ---- Сохранение ----
    def remember(self, user_text: str, assistant_text: str) -> None:
        save_message(self.session_key, "user", user_text)
        save_message(self.session_key, "bot", assistant_text)

    # ---- Управление ----
    def clear(self) -> None:
        """Стирает хронологическую историю сессии в SQLite."""
        clear_chat_history(self.session_key)

    # ---- Диагностика ----
    def stats(self) -> Dict[str, Any]:
        return get_stats(self.session_key)
