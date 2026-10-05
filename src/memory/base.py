"""
src.memory.base
~~~~~~~~~~~~~~~
Абстрактная память бота. Все стратегии памяти (Stateless / Session /
Vector / б��дущие — Graph, Summary, ...) реализуют этот интерфейс,
что позволяет подменять их без правок в ботах.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseMemory(ABC):
    """Базовый интерфейс памяти."""

    name: str = "base"

    @abstractmethod
    def build_context(self, prompt: str, session_messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Возвращает список сообщений для отправки в LLM,
        учитывая текущий запрос и сессионную историю.
        """

    @abstractmethod
    def remember(self, user_text: str, assistant_text: str) -> None:
        """Сохраняет пару user/assistant во внешнее хранилище (если нужно)."""

    @abstractmethod
    def stats(self) -> Dict[str, Any]:
        """Произв��льная диагностическая информация для UI."""

    def clear(self) -> None:  # noqa: D401
        """Опциональный сброс хранилища. По умолчанию — no-op."""
        return None


class StatelessMemory(BaseMemory):
    """Никакой памяти: в LLM уходит только текущий prompt."""

    name = "stateless"

    def build_context(self, prompt: str, session_messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        return [{"role": "user", "content": prompt}]

    def remember(self, user_text: str, assistant_text: str) -> None:
        return

    def stats(self) -> Dict[str, Any]:
        return {"type": self.name, "items": 0}
