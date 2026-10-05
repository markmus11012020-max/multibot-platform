"""
src.bots.session_bot
~~~~~~~~~~~~~~~~~~~~
Бот №2: контекстная память в пределах сессии Streamlit.

Использует ``ChronologicalDBMemory``: история хранится в SQLite
(``history.db``), поэтому переживает F5 и перезапуск приложения.
"""

from __future__ import annotations

from openai import OpenAI

from src.bots.base_bot import BaseBot
from src.memory.chronological_memory import ChronologicalDBMemory


class SessionBot(BaseBot):
    bot_id = "session"
    title = "Бот №2"
    description = (
        "💡 **Контекстная память.** Последние реплики диалога берутся из "
        "SQLite (``history.db``) и передаются в API при каждом запросе. "
        "История переживает F5 и перезапуск приложения."
    )

    def __init__(self, session_key: str = "bot2_messages"):
        super().__init__(
            memory=ChronologicalDBMemory(session_key=session_key),
            session_key=session_key,
        )

    def render(self, client: OpenAI, model: str, temperature: float) -> None:
        # Подменим memory на актуальную (нужна ссылка на живой session_key).
        self.memory = ChronologicalDBMemory(session_key=self.session_key)
        # Подтянем историю из SQLite, если локальная сессия пуста.
        self.hydrate_from_db()
        self._chat_loop(
            client, model, temperature,
            input_key="input_bot2", clear_key="clear_bot2",
        )
