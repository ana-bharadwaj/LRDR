"""
Reranking: FAISS similarity search uses embedding distance, which captures
topical closeness but not actual relevance to a specific question — a chunk
that *mentions* the right keywords can outrank the chunk that *answers* the
question. A cross-encoder reads the (question, chunk) pair jointly and scores
relevance directly, which is more accurate but too slow to run on the whole
index — so it's only used to re-score a small candidate pool that FAISS has
already narrowed down.

Model is loaded once per process (it's a real, if small, neural net) and
reused across requests.
"""

import logging
from functools import lru_cache

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


@lru_cache(maxsize=4)
def _load_cross_encoder(model_name: str):
    from sentence_transformers import CrossEncoder

    logger.info("Loading cross-encoder reranker: %s", model_name)
    return CrossEncoder(model_name)


def rerank(
    question: str,
    candidates: list[Document],
    model_name: str,
    top_k: int,
) -> list[Document]:
    """Re-score candidates against the question and return the top_k, best-first."""
    if not candidates:
        return []

    try:
        model = _load_cross_encoder(model_name)
    except Exception as exc:
        logger.warning("Reranker unavailable (%s), falling back to FAISS order", exc)
        return candidates[:top_k]

    pairs = [(question, doc.page_content) for doc in candidates]
    scores = model.predict(pairs)

    ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
    return [doc for _, doc in ranked[:top_k]]
