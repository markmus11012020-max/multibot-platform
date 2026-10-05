"""
src.llm.models
~~~~~~~~~~~~~~
Реестр доступных моделей. Легко расширяется — просто добавьте
строку в MODELS или подгрузите список из внешнего источника.
"""

from __future__ import annotations

MODELS: list[str] = [
    "gpt-6-luna-pro",
    "mimo-v2.6-flash",
    "deepseek-v4.1-flash",
    "qwen3.8-flash",
    "gemini-2.5-flash-lite",
    "minimax-m3",
]


def get_default_model() -> str:
    return MODELS[0]
