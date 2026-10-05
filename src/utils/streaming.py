"""
src.utils.streaming
~~~~~~~~~~~~~~~~~~~
Потоковая генерация ответов от LLM с единообразной обработкой ошибок.
"""

from __future__ import annotations

from typing import Iterator, List, Dict, Optional, Callable

import streamlit as st
from openai import APIConnectionError, APIError, AuthenticationError, OpenAI


ErrorRenderer = Callable[[str], None]


def stream_response(
    client: OpenAI,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    error_fn: Optional[ErrorRenderer] = None,
) -> Optional[Iterator[str]]:
    """
    Запускает stream chat-completions.
    Возвращает генератор строк для st.write_stream или None при ошибке.
    """
    if error_fn is None:
        error_fn = st.error

    try:
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            stream=True,
        )

        def _gen() -> Iterator[str]:
            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content

        return _gen()
    except AuthenticationError:
        error_fn("❌ Ошибка аутентификации. Проверьте AITUNNEL_API_KEY в файле .env")
        return None
    except APIConnectionError:
        error_fn("❌ Ошибка сети. Не удалось подключиться к AiTunnel API.")
        return None
    except APIError as e:
        msg = getattr(e, "message", str(e))
        error_fn(f"❌ Ошибка API: {msg}")
        return None
    except Exception as e:  # noqa: BLE001
        error_fn(f"❌ Непредв��денная ошибка: {e}")
        return None
