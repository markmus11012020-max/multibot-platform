"""
src.memory.session_memory
~~~~~~~~~~~~~~~~~~~~~~~~~
Краткосрочная память сессии. Хранит список сообщений,
передаваемых в LLM целиком при каждом запросе.
"""

from __future__ import annotations

from typing import List, Dict, Any

from src.memory.base import BaseMemory


class SessionMemory(BaseMemory):
    name = "session"

    def __init__(self, session_messages: List[Dict[str, str]]):
        self._session = session_messages

    def build_context(self, prompt: str, session_messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        # Вся сессия + текущее сообщение (если его ещё нет в сессии).
        history = [{"role": m["role"], "content": m["content"]} for m in session_messages]
        if not history or history[-1] != {"role": "user", "content": prompt}:
            history.append({"role": "user", "content": prompt})
        return history

    def remember(self, user_text: str, assistant_text: str) -> None:
        # Сессия пополняется в UI-слое (st.session_state), этот слой
        # только читает её.
        return

    def stats(self) -> Dict[str, Any]:
        return {"type": self.name, "items": len(self._session)}
