"""
app.py — точка входа Streamlit-приложения.

Сценарии:
    * Бот №1 — Stateless
    * Бот №2 — Session (short-term)
    * Бот №3 — Hybrid (session + FAISS long-term)

Архитектура (см. README.md):
    src/
      config.py        — конфигурация и пути
      llm/             — клиент OpenAI, реестр моделей
      memory/          — стратегии памяти (Stateless / Session / Vector)
      bots/            — реализации ботов (наследники BaseBot)
      ui/              — sidebar и переиспользуемые компоненты
      utils/           — потоковая генерация и хелперы
"""

from __future__ import annotations

import streamlit as st

from src.llm.client import get_openai_client
from src.ui.components import build_bot_registry, render_header
from src.ui.sidebar import render_sidebar


def _init_session_defaults() -> None:
    defaults = {
        "bot1_messages": [],
        "bot2_messages": [],
        "bot3_messages": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def main() -> None:
    st.set_page_config(
        page_title="Мультибот-платформа | LLM Memory Demo",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _init_session_defaults()
    client = get_openai_client()
    model, temperature = render_sidebar()
    render_header()

    tab1, tab2, tab3 = st.tabs(
        ["Бот №1 (Без памяти)", "Бот №2 (Контекстный)", "Бот №3 (Гибридная память)"]
    )

    bots = build_bot_registry()
    with tab1:
        bots["bot1_messages"].render(client, model, temperature)
    with tab2:
        bots["bot2_messages"].render(client, model, temperature)
    with tab3:
        bots["bot3_messages"].render(client, model, temperature)


if __name__ == "__main__":
    main()
