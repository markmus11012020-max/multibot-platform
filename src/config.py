"""
src.config
~~~~~~~~~~
Централизованная конфигурация приложения: переменные окружения,
пути и константы. Импортируется из любых модулей без побочных эффектов
(кроме однократной загрузки .env).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Загружаем .env ровно один раз при импорте модуля.
load_dotenv()

# ---------------------------------------------------------------------------
# Корень проекта
# ---------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
VECTOR_STORE_DIR: Path = PROJECT_ROOT / "vector_store"
VECTOR_STORE_DIR.mkdir(exist_ok=True)
INDEX_PATH: Path = VECTOR_STORE_DIR / "faiss.index"
META_PATH: Path = VECTOR_STORE_DIR / "metadata.json"

# Хронологическая история диалогов (SQLite, локальный файл).
DB_PATH: Path = PROJECT_ROOT / "history.db"

# ---------------------------------------------------------------------------
# LLM / API
# ---------------------------------------------------------------------------
API_KEY: str | None = os.getenv("AITUNNEL_API_KEY")
BASE_URL: str = os.getenv("AITUNNEL_BASE_URL", "https://aitunnel.ru")

EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "384"))

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
TOP_K: int = int(os.getenv("TOP_K", "3"))
DEFAULT_TEMPERATURE: float = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
