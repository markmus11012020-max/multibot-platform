"""
src.utils.db_history
~~~~~~~~~~~~~~~~~~~~
Хронологическая история диалогов на SQLite.

Назначение:
    * ``save_message``         — записать одну реплику (user/bot);
    * ``get_chat_history``     — достать последние N реплик по хронологии;
    * ``clear_chat_history``   — стереть историю конкретной сессии (бота);
    * ``get_stats``            — диагностика для UI.

Используется Ботами №2–№4 как «источник правды» по хронологии диалога.
Файл БД: ``history.db`` в корне проекта (см. ``src.config.DB_PATH``).

Хранимые значения ``sender`` — ``"user"`` / ``"bot"`` (по требованию ТЗ).
При выдаче в LLM они автоматически превращаются в ``"user"`` / ``"assistant"``.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List

from src.config import DB_PATH


# ---------------------------------------------------------------------------
# Низкоуровневые операции
# ---------------------------------------------------------------------------
@contextmanager
def _connect():
    """Короткоживущее соединение с SQLite. Создаёт файл БД при первом обращении."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


_SCHEMA_READY = False


def init_db() -> None:
    """Создаёт таблицу ``messages`` и индекс, если их ещё нет. Идемпотентно."""
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_key TEXT    NOT NULL,
                sender      TEXT    NOT NULL,
                text        TEXT    NOT NULL,
                timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_session_ts "
            "ON messages (session_key, timestamp, id)"
        )
    _SCHEMA_READY = True


def _now_iso() -> str:
    return datetime.utcnow().isoformat(sep=" ", timespec="seconds")


# ---------------------------------------------------------------------------
# Публичный API
# ---------------------------------------------------------------------------
def save_message(session_key: str, sender: str, text: str) -> None:
    """
    Сохраняет одну реплику.

    :param session_key: ключ сессии Streamlit (``bot2_messages`` и т.п.).
    :param sender:      ``"user"`` или ``"bot"``.
    :param text:        текст реплики (пустая строка игнорируется).
    """
    if not session_key or not text:
        return
    init_db()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages (session_key, sender, text, timestamp) "
            "VALUES (?, ?, ?, ?)",
            (session_key, sender, text, _now_iso()),
        )


def get_chat_history(session_key: str, limit: int = 20) -> List[Dict[str, str]]:
    """
    Возвращает последние ``limit`` реплик сессии строго по хронологии
    (``ORDER BY timestamp ASC, id ASC``).

    Формат элемента: ``{"role": "user"|"assistant", "content": "..."}`` —
    готов к отправке в ``chat.completions``.
    """
    if not session_key:
        return []
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT sender, text FROM messages "
            "WHERE session_key = ? "
            "ORDER BY timestamp ASC, id ASC "
            "LIMIT ?",
            (session_key, max(1, int(limit))),
        ).fetchall()

    out: List[Dict[str, str]] = []
    for r in rows:
        role = "assistant" if r["sender"] == "bot" else "user"
        out.append({"role": role, "content": r["text"]})
    return out


def clear_chat_history(session_key: str) -> None:
    """Удаляет все реплики конкретной сессии (бота)."""
    if not session_key:
        return
    init_db()
    with _connect() as conn:
        conn.execute("DELETE FROM messages WHERE session_key = ?", (session_key,))


def get_stats(session_key: str) -> Dict[str, Any]:
    """Возвращает количество реплик в сессии (для UI/диагностики)."""
    if not session_key:
        return {"type": "sqlite", "items": 0}
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM messages WHERE session_key = ?",
            (session_key,),
        ).fetchone()
    return {"type": "sqlite", "items": int(row["n"]) if row else 0}
