"""
src.bots.session_bot
~~~~~~~~~~~~~~~~~~~~
Бот №2: контекстная память в пределах сессии Streamlit.
"""

from __future__ import annotations

from openai import OpenAI

from src.bots.base_bot import BaseBot
from src.memory.session_memory import SessionMemory


class SessionBot(BaseBot):
    bot_id = "session"
    title = "Бот №2"
    description = (
        "💡 **Контекстная память.** Вся история текущей сессии браузера "
        "передаётся в API при каждом запросе. Стирается при F5 или очистке."
    )

    def __init__(self, session_key: str = "bot2_messages"):
        super().__init__(memory=SessionMemory([]), session_key=session_key)

    def render(self, client: OpenAI, model: str, temperature: float) -> None:
        # подменим memory на актуальную (нужна ссылка на живую сессию)
        self.memory = SessionMemory(self.session_messages)
        self._chat_loop(
            client, model, temperature,
            input_key="input_bot2", clear_key="clear_bot2",
        )
