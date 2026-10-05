"""
src.ui.sidebar
~~~~~~~~~~~~~~
Боковая панель: выбор модели, temperature, глобальный сброс историй.
"""

from __future__ import annotations

import streamlit as st

from src.bots.base_bot import BaseBot
from src.config import API_KEY, DEFAULT_TEMPERATURE
from src.llm.models import MODELS


def _bots_registry() -> dict[str, BaseBot]:
    """Реестр ак��ивных ботов (ленивая инициализация в session_state)."""
    if "_bots" not in st.session_state:
        from src.bots.stateless_bot import StatelessBot
        from src.bots.session_bot import SessionBot
        from src.bots.hybrid_bot import HybridBot

        st.session_state["_bots"] = {
            "bot1_messages": StatelessBot("bot1_messages"),
            "bot2_messages": SessionBot("bot2_messages"),
            "bot3_messages": HybridBot("bot3_messages"),
        }
    return st.session_state["_bots"]


def render_sidebar() -> tuple[str, float]:
    """
    Рисует sidebar и возвращает выбранные (model, temperature).
    """
    with st.sidebar:
        st.title("⚙️ Настройки")
        st.markdown("---")

        model = st.selectbox(
            "Модель",
            options=MODELS,
            index=0,
            help="Выберите модель через AiTunnel",
        )

        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=DEFAULT_TEMPERATURE,
            step=0.1,
            help="Степень случайности генерации",
        )

        st.markdown("---")
        st.markdown("### Управление историей")
        target = st.selectbox(
            "Какую историю очистить?",
            options=["Бот №1", "Бот №2", "Бот №3 (сессия)", "Бот №3 (долгосрочная)"],
            index=0,
        )
        if st.button("🗑 Очистить выбранную историю", use_container_width=True):
            bots = _bots_registry()
            if target == "Бот №1":
                bots["bot1_messages"].clear_session()
            elif target == "Бот №2":
                bots["bot2_messages"].clear_session()
            elif target == "Бот №3 (сессия)":
                bots["bot3_messages"].clear_session()
            elif target == "Бот №3 (долгосрочная)":
                bots["bot3_messages"].memory.clear()
            st.success(f"Очищено: {target}")
            st.rerun()
        st.caption("Также кнопки очистки есть внутри каждой вкладки.")

        st.markdown("---")
        st.caption("Ключ API загружается из `.env`")
        if not API_KEY:
            st.warning("⚠️ AITUNNEL_API_KEY не найден. Создайте файл `.env`.")
        else:
            st.success("✅ API-ключ загружен")

        st.markdown("---")
        st.markdown(
            "**Бот №1** — без памяти (stateless)  \n"
            "**Бот №2** — контекстная (сессия)  \n"
            "**Бот №3** — гибридная (векторная + сессия)"
        )

    return model, temperature
