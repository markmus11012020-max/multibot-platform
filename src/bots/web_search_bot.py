"""
src.bots.web_search_bot
~~~~~~~~~~~~~~~~~~~~~~~
Бот №4: гибридная память (SQLite + FAISS) + актуализация данных из DuckDuckGo.

Перед отправкой запроса в LLM бот:
    1) вычисляет текущую дату/время на сервере и кладёт их в ``system``-промпт;
    2) если в запросе есть «сегодня/вчера/сейчас/...» — подмешивает год и
       месяц в запрос к DuckDuckGo, чтобы сниппеты были актуальными;
    3) делает web-поиск и подмешивает полученные сниппеты в ``system``-промпт.

Стратегия памяти и поведение long-term хранения унаследованы
от :class:`HybridBot` (теперь на базе ``HybridDBMemory``).
"""

from __future__ import annotations

import streamlit as st
from openai import OpenAI

from src.bots.hybrid_bot import HybridBot
from src.memory.hybrid_db_memory import HybridDBMemory
from src.utils.search import (
    augment_query_with_date,
    format_snippets_for_prompt,
    get_server_date_info,
    search_web,
)


class WebSearchBot(HybridBot):
    """
    Hybrid + Web-Augmented.

    Наследует:
        * гибридную память (SQLite-хронология + FAISS top-k) — ``HybridBot``
          / ``HybridDBMemory``;
        * общий UI-каркас и поведение ``BaseBot``;
        * персистентность векторного индекса и SQLite на диске.

    Добавляет:
        * переключатель «🌐 Искать в интернете»;
        * pre-LLM-поиск в DuckDuckGo (с авто-аугментацией запроса датой);
        * инъекцию текущей даты/времени сервера в ``system``-промпт;
        * инъекцию свежих сниппетов в ``system``-промпт;
        * визуальный expander со списком найденных источников.
    """

    bot_id = "web_search"
    title = "Бот №4"
    description = (
        "🌐 **Гибридная память + поиск в интернете.** Хронология диалога "
        "хранится в SQLite, архивные факты подмешиваются из FAISS. Перед "
        "каждым запросом делается свежий поиск в DuckDuckGo, а в "
        "``system``-промпт автоматически добавляется текущая дата и время."
    )

    TOGGLE_KEY = "bot4_web_search_enabled"
    SNIPPETS_KEY = "bot4_last_snippets"

    def __init__(self, session_key: str = "bot4_messages"):
        super().__init__(session_key=session_key)
        # По умолчанию поиск включён — это ключевая фича бота.
        if self.TOGGLE_KEY not in st.session_state:
            st.session_state[self.TOGGLE_KEY] = True

    # ---- UI ----
    def render(self, client: OpenAI, model: str, temperature: float) -> None:
        # Синхронизируем memory с актуальной сессией (как у HybridBot).
        self.memory = HybridDBMemory(
            session_messages=self.session_messages,
            session_key=self.session_key,
        )
        # Подтянем историю из SQLite, если локальная сессия пуста.
        self.hydrate_from_db()

        self._info()

        col_a, col_b, col_c = st.columns([1, 1, 1])
        with col_a:
            if st.button("🗑 Очистить историю сессии", key="clear_bot4"):
                self.clear_session()  # чистит st.session_state + SQLite
                st.session_state[self.SNIPPETS_KEY] = []
                st.rerun()
        with col_b:
            if st.button("🗑 Очистить долгосрочную память", key="clear_bot4_longterm"):
                self.memory.clear_long_term()  # чистит только FAISS
                st.success("Долгосрочная память очищена.")
                st.rerun()
        with col_c:
            st.session_state[self.TOGGLE_KEY] = st.toggle(
                "🌐 Искать в интернете",
                value=st.session_state[self.TOGGLE_KEY],
                key="toggle_bot4_web",
                help="Если включено — перед каждым запросом будет сделан поиск в DuckDuckGo.",
            )

        stats = self.memory.stats()
        st.caption(
            f"📚 Хронология (SQLite): **{stats.get('chronological_items', 0)}** · "
            f"Долгосрочная (FAISS): **{stats.get('long_term_items', 0)}**"
        )

        # Показываем, какие источники были подмешаны в последний ответ.
        last_snippets = st.session_state.get(self.SNIPPETS_KEY) or []
        if last_snippets:
            with st.expander(f"🔎 Источники из последнего поиска ({len(last_snippets)})", expanded=False):
                for i, s in enumerate(last_snippets, 1):
                    title = s.get("title") or "(без заголовка)"
                    href = s.get("href") or ""
                    body = s.get("body") or ""
                    if href:
                        st.markdown(f"**{i}. [{title}]({href})**")
                    else:
                        st.markdown(f"**{i}. {title}**")
                    if body:
                        st.caption(body)

        self._display()

        if not (prompt := st.chat_input("Сообщение для Бота №4...", key="input_bot4")):
            return
        if client is None:
            st.error("Клиент API не инициализирован. Проверьте .env")
            return

        # 1. user-сообщение
        self.session_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. Web-augmentation: поиск сниппетов с авто-аугментацией запроса датой.
        snippets: list = []
        if st.session_state[self.TOGGLE_KEY]:
            with st.status("🌐 Ищу в DuckDuckGo…", expanded=False) as status:
                search_query = augment_query_with_date(prompt)
                snippets = search_web(search_query)
                if snippets:
                    status.update(
                        label=f"🌐 Найдено сниппетов: {len(snippets)}",
                        state="complete",
                    )
                else:
                    status.update(
                        label="🌐 Поиск не дал результатов (или сеть недоступна)",
                        state="complete",
                    )
        st.session_state[self.SNIPPETS_KEY] = snippets

        # 3. Базовый контекст от HybridDBMemory (SQLite-хронология + FAISS top-k).
        api_messages = self.memory.build_context(prompt, self.session_messages)

        # 4. Подмешиваем текущую дату/время сервера к system-промпту.
        date_block = (
            f"Текущая дата и время на сервере: {get_server_date_info()} "
            "Используй это для ответов на временные вопросы."
        )
        if api_messages and api_messages[0].get("role") == "system":
            api_messages[0]["content"] = date_block + "\n\n" + api_messages[0]["content"]
        else:
            api_messages = [{"role": "system", "content": date_block}] + api_messages

        # 5. Подмешиваем свежие сниппеты к system-промпту.
        if snippets:
            snippet_block = format_snippets_for_prompt(snippets)
            if api_messages and api_messages[0].get("role") == "system":
                api_messages[0]["content"] = (
                    api_messages[0]["content"]
                    + "\n\n---\n\nСвежие данные из открытого веба (DuckDuckGo), "
                    "используй их как приоритетный источник фактов:\n\n"
                    + snippet_block
                )
            else:
                api_messages = [
                    {
                        "role": "system",
                        "content": (
                            "Ты полезный ассистент. Используй следующие свежие "
                            "данные из DuckDuckGo как приоритетный источник "
                            "фактов:\n\n" + snippet_block
                        ),
                    }
                ] + api_messages

        # 6. Стриминг ответа.
        from src.utils.streaming import stream_response

        with st.chat_message("assistant"):
            stream = stream_response(client, model, api_messages, temperature)
            if stream:
                response = st.write_stream(stream)
                self.session_messages.append({"role": "assistant", "content": response})
                # Долгосрочная память обновляется так же, как у HybridBot.
                self.memory.remember(prompt, response)

