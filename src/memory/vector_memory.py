"""
src.memory.vector_memory
~~~~~~~~~~~~~~~~~~~~~~~~
Долгосрочная память на базе FAISS + локальные эмбеддинги
(sentence-transformers). Семантический поиск top-k фактов из прошлых
диалогов, плюс короткая сессия как у SessionMemory.
"""

from __future__ import annotations

import json
from typing import List, Dict, Any, Tuple

import numpy as np
import streamlit as st

from src.config import (
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    INDEX_PATH,
    META_PATH,
    TOP_K,
)
from src.memory.session_memory import SessionMemory


@st.cache_resource(show_spinner=False)
def _get_embedder():
    """Ленивая загрузка локальной модели эмбеддингов (без расхода токенов API)."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL)


def _load_index():
    """Загружает FAISS-индекс и метаданные; создаёт пустой, если файлов нет."""
    import faiss

    if INDEX_PATH.exists() and META_PATH.exists():
        index = faiss.read_index(str(INDEX_PATH))
        with open(META_PATH, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        return index, metadata
    return faiss.IndexFlatIP(EMBEDDING_DIM), []


def _save_index(index, metadata: list) -> None:
    import faiss
    faiss.write_index(index, str(INDEX_PATH))
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


class VectorMemory(SessionMemory):
    """
    Гибридная память: top-k фактов из FAISS (как system-контекст) +
    полная история текущей сессии.
    """

    name = "vector"

    def __init__(self, session_messages: List[Dict[str, str]], top_k: int = TOP_K):
        super().__init__(session_messages)
        self.top_k = top_k

    # ---- Поиск и сохранение ----
    def _search(self, query: str) -> List[Dict[str, Any]]:
        index, metadata = _load_index()
        if index.ntotal == 0:
            return []
        embedder = _get_embedder()
        q = np.array(embedder.encode([query], normalize_embeddings=True), dtype=np.float32)
        k = min(self.top_k, index.ntotal)
        scores, indices = index.search(q, k)
        out: List[Dict[str, Any]] = []
        for score, idx in zip(scores[0], indices[0]):
            if 0 <= idx < len(metadata):
                item = metadata[idx].copy()
                item["score"] = float(score)
                out.append(item)
        return out

    def remember(self, user_text: str, assistant_text: str) -> None:
        embedder = _get_embedder()
        embeddings = np.array(
            embedder.encode([user_text, assistant_text], normalize_embeddings=True),
            dtype=np.float32,
        )
        index, metadata = _load_index()
        index.add(embeddings)
        metadata.append({"role": "user", "content": user_text})
        metadata.append({"role": "assistant", "content": assistant_text})
        _save_index(index, metadata)

    # ---- Контекст для LLM ----
    def build_context(self, prompt: str, session_messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        relevant = self._search(prompt)
        system_lines = [
            "Ты полезный ассистент.",
            "Используй следующие фак��ы из прошлых бесед с пользователем,",
            "если они релевантны текущему запросу:\n",
        ]
        if relevant:
            for i, item in enumerate(relevant, 1):
                system_lines.append(f"{i}. [{item['role']}]: {item['content']}")
        else:
            system_lines.append("(пока нет релевантных фактов из прошлых бесед)")

        history = super().build_context(prompt, session_messages)
        return [{"role": "system", "content": "\n".join(system_lines)}] + history

    def stats(self) -> Dict[str, Any]:
        _, metadata = _load_index()
        return {"type": self.name, "long_term_items": len(metadata), "top_k": self.top_k}

    # ---- Управление ----
    def clear(self) -> None:
        """Полностью очищает д��лгосрочное хранилище."""
        import faiss
        _save_index(faiss.IndexFlatIP(EMBEDDING_DIM), [])
