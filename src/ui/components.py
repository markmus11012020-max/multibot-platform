"""
src.ui.components
~~~~~~~~~~~~~~~~~
Переиспользуемые UI-блоки: заголовок и реестр ботов.
"""

from __future__ import annotations

from typing import Dict

import streamlit as st

from src.bots.base_bot import BaseBot
from src.bots.hybrid_bot import HybridBot
from src.bots.session_bot import SessionBot
from src.bots.stateless_bot import StatelessBot


def render_header() -> None:
    st.title("🤖 Мультибот-платформа")
    st.markdown(
        "Демонстрация трёх архитектурных подходов к управлению контекстом и памятью LLM."
    )


def build_bot_registry() -> Dict[str, BaseBot]:
    """Создаёт/возвращает инстансы ботов (по одному на session_state-ключ)."""
    if "_bots" not in st.session_state:
        st.session_state["_bots"] = (
            StatelessBot("bot1_messages"),
            SessionBot("bot2_messages"),
            HybridBot("bot3_messages"),
        )
    return {b.session_key: b for b in st.session_state["_bots"]}
