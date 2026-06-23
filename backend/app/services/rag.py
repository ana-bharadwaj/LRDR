"""
RAG service: load a FAISS index, retrieve and rerank relevant chunks for a
question, and generate a grounded answer using a local Ollama chat model.

Pipeline per question:
  1. Check answer cache (index_name + normalized question) -> return early if hit.
  2. FAISS similarity search -> a wider candidate pool (rerank_candidate_k).
  3. Cross-encoder reranks that pool against the literal question -> top retrieval_k.
  4. Those chunks become the prompt context for the local Ollama LLM.
  5. Cache the result before returning.
"""

import logging
import os
import time

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama, OllamaEmbeddings

from ..config import Settings
from . import cache as answer_cache
from .rerank import rerank as rerank_candidates

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are a careful assistant answering questions about a document.
Use ONLY the context below. If the answer is not contained in the context,
say exactly: "I cannot find this information in the document." Do not guess
or rely on outside knowledge.

Context:
{context}

Question: {question}

Answer:"""


def load_index(index_name: str, settings: Settings) -> FAISS:
    index_path = os.path.join(settings.faiss_index_dir, index_name)
    if not os.path.exists(os.path.join(index_path, "index.faiss")):
        raise FileNotFoundError(f"No index named '{index_name}'. Upload a PDF first.")

    embeddings = OllamaEmbeddings(
        model=settings.ollama_embed_model,
        base_url=settings.ollama_base_url,
    )
    return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)


def _format_context(docs: list[Document]) -> str:
    parts = []
    for doc in docs:
        page = doc.metadata.get("page", "?")
        section = doc.metadata.get("section")
        label = f"[Page {page}{f' - {section}' if section else ''}]"
        parts.append(f"{label}\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


def _retrieve(question: str, vectorstore: FAISS, settings: Settings) -> list[Document]:
    """FAISS candidate retrieval, optionally narrowed by cross-encoder reranking."""
    if settings.rerank_enabled:
        candidate_k = max(settings.rerank_candidate_k, settings.retrieval_k)
        candidates = vectorstore.similarity_search(question, k=candidate_k)
        return rerank_candidates(question, candidates, settings.rerank_model, settings.retrieval_k)

    return vectorstore.similarity_search(question, k=settings.retrieval_k)


def answer_question(question: str, index_name: str, settings: Settings):
    """
    Returns (answer, model_used, sources, processing_time_seconds).
    sources is a list of {"page": ..., "snippet": ...} dicts.
    """
    start = time.time()

    if settings.cache_enabled:
        cached = answer_cache.get_cached_answer(question, index_name, settings.cache_dir)
        if cached:
            logger.info("Cache hit for index '%s'", index_name)
            return cached.answer, cached.model_used, cached.sources, time.time() - start

    vectorstore = load_index(index_name, settings)
    retrieved = _retrieve(question, vectorstore, settings)

    if not retrieved:
        answer = "I cannot find this information in the document."
        return answer, settings.ollama_llm_model, [], time.time() - start

    context = _format_context(retrieved)
    llm = ChatOllama(
        model=settings.ollama_llm_model,
        base_url=settings.ollama_base_url,
        temperature=0,
    )
    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"context": context, "question": question})

    sources = [
        {"page": doc.metadata.get("page", "?"), "snippet": doc.page_content[:200]}
        for doc in retrieved
    ]
    took = time.time() - start

    if settings.cache_enabled:
        answer_cache.set_cached_answer(
            question, index_name, settings.cache_dir, answer, settings.ollama_llm_model, sources, took
        )

    return answer, settings.ollama_llm_model, sources, took
