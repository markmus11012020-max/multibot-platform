"""
src.llm.client
~~~~~~~~~~~~~~
Фабрика клиента OpenAI-совместимого API (используется с AiTunnel).
Клиент кэшируется через Streamlit cache_resource, чтобы не плодить
TCP-соединения при rerun'ах.
"""

from __future__ import annotations

from typing import Optional

import streamlit as st
from openai import OpenAI

from src.config import API_KEY, BASE_URL


@st.cache_resource(show_spinner=False)
def get_openai_client() -> Optional[OpenAI]:
    """Возвращает синглтон OpenAI-клиента или None, если ключ не задан."""
    if not API_KEY:
        return None
    return OpenAI(api_key=API_KEY, base_url=BASE_URL)
