"""
src.memory.hybrid_db_memory
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Гибридная память: хронология из SQLite + долгосрочные факты из FAISS.

Используется Ботами №3 (HybridBot) и №4 (WebSearchBot):
    * system-промпт насыщается top-k релевантными фактами из FAISS;
    * в LLM уходит последние ``history_limit`` реплик строго по хронологии
      из SQLite (а не из временного ``st.session_state``);
    * ``remember`` пишет реплики и в SQLite, и в FAISS;
    * ``clear`` стирает только хро��ологию (SQLite);
    * ``clear_long_term`` стирает только FAISS.
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.config import TOP_K
from src.memory.vector_memory import VectorMemory
from src.utils.db_history import (
    clear_chat_history,
    get_chat_history,
    get_stats,
    save_message,
)


class HybridDBMemory(VectorMemory):
    """Гибрид: SQLite (хронология) + FAISS (top-k фактов)."""

    name = "hybrid_db"

    def __init__(
        self,
        session_messages: List[Dict[str, str]],
        session_key: str,
        top_k: int = TOP_K,
        history_limit: int = 10,
    ):
        super().__init__(session_messages, top_k=top_k)
        self.session_key = session_key
        self.history_limit = history_limit

    # ---- Контекст для LLM ----
    def build_context(
        self,
        prompt: str,
        session_messages: List[Dict[str, str]] | None = None,  # noqa: ARG002
    ) -> List[Dict[str, str]]:
        # 1) system-промпт из FAISS (top-k архивных фактов).
        relevant = self._search(prompt)
        system_lines = [
            "Ты полезный ассистент.",
            "Используй следующие факты из прошлых бесед с пользователем,",
            "если они релевантны текущему запросу:",
            "",
        ]
        if relevant:
            for i, item in enumerate(relevant, 1):
                system_lines.append(f"{i}. [{item['role']}]: {item['content']}")
        else:
            system_lines.append("(пока нет релевантных фактов из прошлых бесед)")

        # 2) хронологическая история из SQLite.
        history = get_chat_history(self.session_key, limit=self.history_limit)
        if not history or history[-1] != {"role": "user", "content": prompt}:
            history.append({"role": "user", "content": prompt})

        return [{"role": "system", "content": "\n".join(system_lines)}] + history

    # ---- Сохранение ----
    def remember(self, user_text: str, assistant_text: str) -> None:
        # Хронология (SQLite) — источник правды по порядку.
        save_message(self.session_key, "user", user_text)
        save_message(self.session_key, "bot", assistant_text)
        # Долгосрочная семантическая память (FAISS).
        super().remember(user_text, assistant_text)

    # ---- Управление ----
    def clear(self) -> None:
        """Стирает хронологию (SQLite), FAISS не трогает."""
        clear_chat_history(self.session_key)

    def clear_long_term(self) -> None:
        """Стирает только FAISS-хранилище (долгосрочная память)."""
        super().clear()

    # ---- Диагностика ----
    def stats(self) -> Dict[str, Any]:
        chrono = get_stats(self.session_key)
        # Дополняем родительскую статистику количеством FAISS-векторов.
        base = super().stats()
        return {
            "type": self.name,
            "long_term_items": base.get("long_term_items", 0),
            "top_k": base.get("top_k", self.top_k),
            "chronological_items": chrono.get("items", 0),
        }
