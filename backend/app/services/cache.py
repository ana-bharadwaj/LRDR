"""
Answer cache: identical questions against an unchanged index skip the LLM
entirely. Backed by flat JSON files on disk (one per index) so it survives
backend restarts without needing a database.

Cache key = sha256(normalized_question). Re-ingesting a PDF for an index
wipes that index's cache file, since the underlying chunks (and therefore
correct answers) may have changed.
"""

import hashlib
import json
import logging
import os
import re
import time
from dataclasses import asdict, dataclass

logger = logging.getLogger(__name__)


def _normalize(question: str) -> str:
    """Collapse whitespace and case so trivial phrasing differences still hit cache."""
    return re.sub(r"\s+", " ", question.strip().lower())


def _cache_path(cache_dir: str, index_name: str) -> str:
    os.makedirs(cache_dir, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", index_name)
    return os.path.join(cache_dir, f"{safe_name}.json")


@dataclass
class CachedAnswer:
    answer: str
    model_used: str
    sources: list
    processing_time_seconds: float
    cached_at: float


def get_cached_answer(question: str, index_name: str, cache_dir: str) -> CachedAnswer | None:
    path = _cache_path(cache_dir, index_name)
    if not os.path.exists(path):
        return None

    key = hashlib.sha256(_normalize(question).encode()).hexdigest()
    try:
        with open(path, encoding="utf-8") as f:
            store = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Cache read failed for %s: %s", path, exc)
        return None

    entry = store.get(key)
    if not entry:
        return None
    return CachedAnswer(**entry)


def set_cached_answer(
    question: str,
    index_name: str,
    cache_dir: str,
    answer: str,
    model_used: str,
    sources: list,
    processing_time_seconds: float,
) -> None:
    path = _cache_path(cache_dir, index_name)
    key = hashlib.sha256(_normalize(question).encode()).hexdigest()

    store = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                store = json.load(f)
        except (json.JSONDecodeError, OSError):
            store = {}

    store[key] = asdict(
        CachedAnswer(
            answer=answer,
            model_used=model_used,
            sources=sources,
            processing_time_seconds=processing_time_seconds,
            cached_at=time.time(),
        )
    )

    with open(path, "w", encoding="utf-8") as f:
        json.dump(store, f)


def invalidate_cache(index_name: str, cache_dir: str) -> None:
    """Call this whenever an index is rebuilt — its cached answers may now be stale."""
    path = _cache_path(cache_dir, index_name)
    if os.path.exists(path):
        os.remove(path)
        logger.info("Invalidated answer cache for index '%s'", index_name)
