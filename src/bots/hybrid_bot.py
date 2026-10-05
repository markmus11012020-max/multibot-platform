"""
src.bots.hybrid_bot
~~~~~~~~~~~~~~~~~~~
Бот №3: гибридная память (SQLite-хронология + FAISS top-k).

Хронология диалога (последние 10 реплик) берётся из SQLite —
это источник правды по порядку сообщений.
Долгосрочные факты по-прежнему подмешиваются из FAISS как system-контекст.
"""

from __future__ import annotations

import streamlit as st
from openai import OpenAI

from src.bots.base_bot import BaseBot
from src.memory.hybrid_db_memory import HybridDBMemory


class HybridBot(BaseBot):
    bot_id = "hybrid"
    title = "Бот №3"
    description = (
        "💡 **Гибридная память.** Хронология диалога хранится в SQLite "
        "(``history.db``), а архивные факты подмешиваются из FAISS "
        "(top-k=3). История переживает F5 и перезапуск приложения."
    )

    def __init__(self, session_key: str = "bot3_messages"):
        super().__init__(
            memory=HybridDBMemory(
                session_messages=[],
                session_key=session_key,
            ),
            session_key=session_key,
        )

    def render(self, client: OpenAI, model: str, temperature: float) -> None:
        # Подменим memory на актуальную (нужна ссылка на живой session_key).
        self.memory = HybridDBMemory(
            session_messages=self.session_messages,
            session_key=self.session_key,
        )
        # Подтянем историю из SQLite, если локальная сессия пуста.
        self.hydrate_from_db()

        self._info()
        col_a, col_b = st.columns([1, 1])
        with col_a:
            if st.button("🗑 Очистить историю сессии", key="clear_bot3"):
                self.clear_session()  # чистит st.session_state + SQLite
                st.rerun()
        with col_b:
            if st.button("🗑 Очистить долгосрочную память", key="clear_longterm"):
                self.memory.clear_long_term()  # чистит только FAISS
                st.success("Долгосрочная память очищена.")
                st.rerun()

        stats = self.memory.stats()
        st.caption(
            f"📚 Хронология (SQLite): **{stats.get('chronological_items', 0)}** · "
            f"Долгосрочная (FAISS): **{stats.get('long_term_items', 0)}**"
        )
        self._display()

        if not (prompt := st.chat_input("Сообщение для Бота №3...", key="input_bot3")):
            return
        if client is None:
            st.error("Клиент API не инициализирован. Проверьте .env")
            return

        self.session_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        api_messages = self.memory.build_context(prompt, self.session_messages)

        from src.utils.streaming import stream_response
        with st.chat_message("assistant"):
            stream = stream_response(client, model, api_messages, temperature)
            if stream:
                response = st.write_stream(stream)
                self.session_messages.append({"role": "assistant", "content": response})
                self.memory.remember(prompt, response)
