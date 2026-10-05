"""
src.bots.base_bot
~~~~~~~~~~~~~~~~~
Базовый класс бота. Любой бот реализует render(), внутри которого
получает клиен��а, настройки и собственную стратегию памяти.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List

import streamlit as st
from openai import OpenAI

from src.memory.base import BaseMemory
from src.utils.streaming import stream_response


class BaseBot(ABC):
    """Абстрактный бот."""

    bot_id: str = "base"
    title: str = "Bot"
    description: str = ""

    def __init__(self, session_key: str | None = None, memory: BaseMemory | None = None):
        self.session_key = session_key
        self.memory = memory

    # ---- helpers ----
    @property
    def session_messages(self) -> List[Dict[str, str]]:
        if self.session_key not in st.session_state:
            st.session_state[self.session_key] = []
        return st.session_state[self.session_key]

    def clear_session(self) -> None:
        st.session_state[self.session_key] = []
        # Если у памяти есть .clear() (SQLite/FAISS) — вызываем и его,
        # чтобы ��нопка «Очистить историю сессии» чистила все слои разом.
        if self.memory is not None and hasattr(self.memory, "clear"):
            try:
                self.memory.clear()
            except Exception:  # noqa: BLE001
                pass

    def hydrate_from_db(self, limit: int = 50) -> None:
        """
        Если локальная сессия пуста — подтягивает историю из SQLite.
        Делает UI и LLM-контекст консистентными после F5/перезапуска.
        Безопасно вызывать для ботов без DB-памяти (Stateless).
        """
        if self.session_messages:
            return
        try:
            from src.utils.db_history import get_chat_history
        except Exception:  # noqa: BLE001
            return
        history = get_chat_history(self.session_key, limit=limit)
        if history:
            st.session_state[self.session_key] = history

    def _info(self) -> None:
        st.info(self.description)

    def _display(self) -> None:
        for msg in self.session_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # ---- contract ----
    @abstractmethod
    def render(self, client: OpenAI, model: str, temperature: float) -> None:
        """Отрисовывает вкладку бота."""

    # ---- common chat loop, переиспользуется потомками ----
    def _chat_loop(
        self,
        client: OpenAI,
        model: str,
        temperature: float,
        input_key: str,
        clear_key: str,
    ) -> None:
        self._info()
        col_a, col_b = st.columns([1, 1])
        with col_a:
            if st.button("🗑 Очистить историю", key=clear_key):
                self.clear_session()
                st.rerun()

        self._display()

        if not (prompt := st.chat_input(f"Сообщение для {self.title}...", key=input_key)):
            return
        if client is None:
            st.error("Клиент API не инициализирован. Проверьте .env")
            return

        # user
        self.session_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # контекст для LLM
        api_messages = self.memory.build_context(prompt, self.session_messages)

        # assistant (stream)
        with st.chat_message("assistant"):
            stream = stream_response(client, model, api_messages, temperature)
            if stream:
                response = st.write_stream(stream)
                self.session_messages.append({"role": "assistant", "content": response})
                self.memory.remember(prompt, response)
