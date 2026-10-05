"""
src.bots.stateless_bot
~~~~~~~~~~~~~~~~~~~~~~
Бот №1: каждый запрос — изолированный, LLM не получает историю.
"""

from __future__ import annotations

from openai import OpenAI
import streamlit as st

from src.bots.base_bot import BaseBot


class StatelessBot(BaseBot):
    bot_id = "stateless"
    title = "Бот №1"
    description = (
        "💡 **Без памяти.** Модель видит только последнее сообщение пользователя. "
        "История отображается в UI, но не передаётся в API."
    )

    def render(self, client: OpenAI, model: str, temperature: float) -> None:
        self._info()
        col_a, _ = st.columns([1, 1])
        with col_a:
            if st.button("🗑 Очистить историю", key="clear_bot1"):
                self.clear_session()
                st.rerun()

        self._display()

        if not (prompt := st.chat_input("Сообщение для Бота №1...", key="input_bot1")):
            return
        if client is None:
            st.error("Клиент API не инициализирован. Проверьте .env")
            return

        # UI
        self.session_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # API: только prompt
        from src.utils.streaming import stream_response
        with st.chat_message("assistant"):
            stream = stream_response(
                client, model,
                [{"role": "user", "content": prompt}],
                temperature,
            )
            if stream:
                response = st.write_stream(stream)
                self.session_messages.append({"role": "assistant", "content": response})
