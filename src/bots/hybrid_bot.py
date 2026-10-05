"""
src.bots.hybrid_bot
~~~~~~~~~~~~~~~~~~~
Бот №3: гибридная память (сессия + FAISS top-k).
"""

from __future__ import annotations

import streamlit as st
from openai import OpenAI

from src.bots.base_bot import BaseBot
from src.memory.vector_memory import VectorMemory


class HybridBot(BaseBot):
    bot_id = "hybrid"
    title = "Бот №3"
    description = (
        "💡 **Гибридная память.** Краткосрочная (сессия) + долгосрочная "
        "(векторный поиск по прошлым диалогам, top-k=3). "
        "Данные сохраняются на диск между перезапусками."
    )

    def __init__(self, session_key: str = "bot3_messages"):
        super().__init__(memory=VectorMemory([]), session_key=session_key)

    def render(self, client: OpenAI, model: str, temperature: float) -> None:
        self.memory = VectorMemory(self.session_messages)

        self._info()
        col_a, col_b = st.columns([1, 1])
        with col_a:
            if st.button("🗑 Очистить историю сессии", key="clear_bot3"):
                self.clear_session()
                st.rerun()
        with col_b:
            if st.button("🗑 Очистить долгосрочную память", key="clear_longterm"):
                self.memory.clear()
                st.success("Долгосрочная память очищена.")
                st.rerun()

        st.caption(f"📚 Записей в долгосрочной памяти: **{self.memory.stats()['long_term_items']}**")
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
