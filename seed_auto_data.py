"""
seed_auto_data.py
~~~~~~~~~~~~~~~~~

Скрипт для seed-наполнения долгосрочной памяти (FAISS-индекс)
20 уникальными фактами на тему «Автомобили и автотехнологии».

Использует существующую инфраструктуру проекта:
    * ``src.config.EMBEDDING_MODEL`` / ``EMBEDDING_DIM`` (all-MiniLM-L6-v2, 384)
    * ``src.memory.vector_memory._load_index`` / ``_save_index``
    * ``sentence_transformers.SentenceTransformer`` (локальные эмбеддинги,
      без расхода токенов внешнего API)

После заполнения делает 3 семантических поисковых запроса и печатает
в консоль top-k результатов с ID, текстом найденной фразы и score.

Запуск из корня проекта:
    python seed_auto_data.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

# Гарантируем UTF-8 в stdout/stderr (на Windows-консоли по умолчанию cp1251).
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass



# ---------------------------------------------------------------------------
# Данные: 20 уникальных фактов об автомобилях и автотехнологиях.
# ---------------------------------------------------------------------------
AUTO_FACTS: List[str] = [
    "Tesla Autopilot использует восемь камер и нейросети для автономного вождения.",
    "Двигатель V8 - это восьмицилиндровый мотор с V-образным расположением цилиндров.",
    "Замена моторного масла рекомендуется каждые 10 000-15 000 км или раз в год.",
    "Шины-липучки (фрикционные) обеспечивают сцепление без шипов за счёт мягкого состава.",
    "Zeekr - премиальный электромобильный бренд китайской компании Geely.",
    "LiXiang (Li Auto) специализируется на гибридных кроссоверах с увеличенным запасом хода.",
    "Электромобили на батарейках не требуют замены масла в двигателе внутреннего сгорания.",
    "Замена тормозных колодок обычно требуется при пробеге 30 000-50 000 км.",
    "Полный привод (AWD) распределяет крутящий момент на все четыре колеса автомобиля.",
    "Спорткары Ferrari традиционно оснащаются атмосферными двигателями V8 и V12.",
    "Bugatti Chiron оснащён 8-литровым двигателем W16 с четырьмя турбинами.",
    "Китайский бренд BYD стал крупнейшим производителем электромобилей в мире.",
    "Аккумуляторы Tesla формата 4680 обещают на 50% больше ёмкости при меньшей цене.",
    "Регламент технического обслуживания включает замену фильтров и проверку тормозов.",
    "Каталитический нейтрализатор снижает токсичность выхлопных газов бензинового двигателя.",
    "Шипованные шины показывают лучший результат на обледенелой дороге, чем фрикционные.",
    "Tesla Model S Plaid разгоняется до 100 км/ч менее чем за 2 секунды.",
    "Гибридные кроссоверы LiXiang L9 оснащены системой помощи водителю уровня L2+.",
    "Давление в шинах рекомендуется проверять каждые 2-4 недели для безопасной езды.",
    "Современные автомобили оснащаются системами ABS, ESP и множеством подушек безопасности.",
]

# Три смысловых запроса для проверки семантического поиска.
SEARCH_QUERIES: List[str] = [
    "машины на батарейках",
    "как часто обслуживать двигатель",
    "быстрый спорткар из Италии",
]

# Чтобы запускать скрипт напрямую: ``python seed_auto_data.py``
PROJECT_ROOT: Path = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import EMBEDDING_DIM, EMBEDDING_MODEL, META_PATH, TOP_K  # noqa: E402
from src.memory.vector_memory import _load_index, _save_index  # noqa: E402

# ---------------------------------------------------------------------------
# Хелперы: эмбеддинг + FAISS.
# ---------------------------------------------------------------------------
def _get_embedder():
    """Ленивая загрузка локальной модели эмбеддингов (вне Streamlit-контекста)."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL)


def _ensure_index() -> Tuple[Any, List[Dict[str, str]]]:
    """
    Гарантирует корректный FAISS-индекс нужной размерности.
    Если файл индекса отсутствует - создаёт пустой IndexFlatIP.
    Если размерность не совпадает с EMBEDDING_DIM - пересоздаёт индекс.
    """
    import faiss

    index, metadata = _load_index()
    if getattr(index, "d", EMBEDDING_DIM) != EMBEDDING_DIM:
        index = faiss.IndexFlatIP(EMBEDDING_DIM)
        metadata = []
    return index, metadata


def seed_long_term(facts: List[str], reset: bool = False) -> int:
    """
    Кодирует список фраз в 384-мерные векторы и добавляет их в FAISS-индекс.
    Метаданные сохраняются в vector_store/metadata.json.

    Args:
        facts: список фраз для эмбеддинга.
        reset: если True, перед добавлением полностью очищает долгосрочную память
               (включая ранее сохранённые факты из диалогов). По умолчанию False -
               факты добавляются к существующему индексу.

    Returns:
        Количество успешно добавленных фактов.
    """
    if not facts:
        return 0

    if reset:
        import faiss
        index = faiss.IndexFlatIP(EMBEDDING_DIM)
        metadata: List[Dict[str, str]] = []
    else:
        index, metadata = _ensure_index()

    embedder = _get_embedder()
    vectors = np.array(
        embedder.encode(facts, normalize_embeddings=True, show_progress_bar=False),
        dtype=np.float32,
    )
    index.add(vectors)
    for fact in facts:
        metadata.append({"role": "user", "content": fact})
    _save_index(index, metadata)
    return len(facts)



def search(query: str, k: int = TOP_K) -> List[Dict[str, Any]]:
    """
    Семантический поиск top-k ближайших фактов к запросу.
    Возвращает список словарей: rank, id, text, score.
    """
    index, metadata = _ensure_index()
    if index.ntotal == 0 or not metadata:
        return []

    embedder = _get_embedder()
    q = np.array(
        embedder.encode([query], normalize_embeddings=True, show_progress_bar=False),
        dtype=np.float32,
    )
    k = min(k, index.ntotal)
    scores, indices = index.search(q, k)

    results: List[Dict[str, Any]] = []
    for rank, (score, idx) in enumerate(zip(scores[0], indices[0]), start=1):
        if 0 <= idx < len(metadata):
            results.append(
                {
                    "rank": rank,
                    "id": int(idx),
                    "text": metadata[idx]["content"],
                    "score": float(score),
                }
            )
    return results



# ---------------------------------------------------------------------------
# Точка входа.
# ---------------------------------------------------------------------------
def main() -> None:
    # CLI: ``python seed_auto_data.py [--reset]``
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed долгосрочной памяти фактами об автомобилях."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Перед добавлением полностью очистить FAISS-индекс и metadata.json.",
    )
    args = parser.parse_args()

    print("=" * 72)
    print("  Seed долгосрочной памяти: «Автомобили и автотехнологии»")
    print(f"  Эмбеддинг: {EMBEDDING_MODEL} (dim={EMBEDDING_DIM})")
    print(f"  Хранилище: {META_PATH.parent}")
    print("=" * 72)

    # 1) Добавляем факты в индекс.
    print(f"\n[1/2] Добавляю {len(AUTO_FACTS)} фактов в FAISS-индекс (reset={args.reset})...")
    added = seed_long_term(AUTO_FACTS, reset=args.reset)
    print(f"      OK: добавлено {added} векторов.")

    index, metadata = _ensure_index()
    print(f"      Размер индекса после seed: {index.ntotal} векторов.")
    print(f"      Записей в metadata.json:    {len(metadata)}")

    # 2) Семантический поиск.
    print(f"\n[2/2] Семантический поиск по {len(SEARCH_QUERIES)} запросам (top_k={TOP_K})...")
    for query in SEARCH_QUERIES:
        print()
        print(f"  Запрос: «{query}»")
        print("  " + "-" * 68)
        results = search(query, k=TOP_K)
        if not results:
            print("    (нет результатов - индекс пуст)")
            continue
        for r in results:
            print(
                f"    #{r['rank']}  id={r['id']:<3}  score={r['score']:.4f}  "
                f"text={r['text']}"
            )

    print()
    print("=" * 72)
    print("  Готово. Данные записаны в vector_store/faiss.index + metadata.json.")
    print("=" * 72)


if __name__ == "__main__":
    main()

