"""
Application settings, loaded from environment variables / .env.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = "llama3.1"
    ollama_embed_model: str = "nomic-embed-text"

    chunk_size: int = 800
    chunk_overlap: int = 150
    retrieval_k: int = 4

    # Section-aware chunking: detect heading-like lines (numbered sections,
    # ALL CAPS short lines, Markdown-style #headers) and never let a chunk
    # span across a detected boundary. Falls back to pure character
    # splitting if no headings are detected in the document.
    section_aware_chunking: bool = True

    # Reranking: FAISS retrieves a wider candidate pool (rerank_candidate_k),
    # then a local cross-encoder re-scores those candidates against the exact
    # question and the top retrieval_k survive. Pure embedding similarity
    # often returns "topically close" chunks that aren't actually the best
    # answer; a cross-encoder reads question+chunk together and corrects that.
    rerank_enabled: bool = True
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    rerank_candidate_k: int = 12

    # Answer caching: identical (index_name, question) pairs skip the LLM call
    # entirely. Cache is invalidated whenever that index is re-ingested.
    cache_enabled: bool = True
    cache_dir: str = "answer_cache"

    faiss_index_dir: str = "faiss_index"
    max_file_size_mb: int = 50

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
