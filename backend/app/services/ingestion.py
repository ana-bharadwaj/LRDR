"""
Ingestion service: loads a PDF, splits it into tuned chunks, embeds each chunk
locally via Ollama, and persists a FAISS index to disk.

Chunking has two modes:
- Section-aware (default): the document is first split at detected heading
  boundaries (numbered sections, Markdown-style #headers, short ALL-CAPS
  lines), then each section is independently character-split. This stops a
  chunk from blending two unrelated sections together, which otherwise hurts
  both retrieval precision and answer coherence.
- Flat: pure character splitting across the whole page, used as a fallback
  when no headings are detected (e.g. plain-prose PDFs with no structure).
"""

import logging
import os
import re

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import Settings

logger = logging.getLogger(__name__)

_HEADING_PATTERNS = [
    re.compile(r"^#{1,6}\s+\S+"),
    re.compile(r"^(chapter|section|appendix)\s+\w+", re.IGNORECASE),
    re.compile(r"^\d+(\.\d+)*\.?\s+[A-Z][\w\s\-/]{2,80}$"),
]


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 90:
        return False
    for pattern in _HEADING_PATTERNS:
        if pattern.match(stripped):
            return True
    letters = [c for c in stripped if c.isalpha()]
    if (
        3 <= len(stripped) <= 70
        and letters
        and sum(1 for c in letters if c.isupper()) / len(letters) > 0.85
        and not stripped.endswith((".", ",", ";"))
    ):
        return True
    return False


def _make_embeddings(settings: Settings) -> OllamaEmbeddings:
    return OllamaEmbeddings(
        model=settings.ollama_embed_model,
        base_url=settings.ollama_base_url,
    )


def _split_into_sections(pages: list[Document]) -> list[dict]:
    sections: list[dict] = []
    current_title = "Untitled section"
    current_lines: list[str] = []
    current_page = pages[0].metadata.get("page", 0) if pages else 0

    def flush():
        text = "\n".join(current_lines).strip()
        if text:
            sections.append({"title": current_title, "text": text, "page": current_page})

    for page_doc in pages:
        page_num = page_doc.metadata.get("page", current_page)
        for line in page_doc.page_content.split("\n"):
            if _is_heading(line):
                flush()
                current_title = line.strip()
                current_lines = []
                current_page = page_num
            else:
                if not current_lines:
                    current_page = page_num
                current_lines.append(line)
    flush()
    return sections


def load_and_chunk(pdf_path: str, settings: Settings) -> list:
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()
    if not pages:
        raise ValueError("No extractable text found in PDF (is it scanned/image-only?)")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    if settings.section_aware_chunking:
        sections = _split_into_sections(pages)
        heading_count = sum(1 for s in sections if s["title"] != "Untitled section")

        if heading_count >= 2:
            chunks: list[Document] = []
            for section in sections:
                section_doc = Document(
                    page_content=section["text"],
                    metadata={"page": section["page"], "section": section["title"]},
                )
                chunks.extend(splitter.split_documents([section_doc]))
            logger.info(
                "Loaded %d pages, detected %d section headings, split into %d chunks "
                "(size=%d, overlap=%d)",
                len(pages), heading_count, len(chunks), settings.chunk_size, settings.chunk_overlap,
            )
            return chunks

        logger.info("No reliable section headings detected - falling back to flat chunking")

    chunks = splitter.split_documents(pages)
    logger.info(
        "Loaded %d pages, split into %d chunks (size=%d, overlap=%d, flat mode)",
        len(pages), len(chunks), settings.chunk_size, settings.chunk_overlap,
    )
    return chunks


def build_and_save_index(chunks: list, index_name: str, settings: Settings) -> int:
    embeddings = _make_embeddings(settings)
    vectorstore = FAISS.from_documents(chunks, embeddings)

    index_path = os.path.join(settings.faiss_index_dir, index_name)
    os.makedirs(index_path, exist_ok=True)
    vectorstore.save_local(index_path)
    logger.info("Saved FAISS index '%s' (%d vectors) to %s", index_name, len(chunks), index_path)
    return len(chunks)


def index_exists(index_name: str, settings: Settings) -> bool:
    index_path = os.path.join(settings.faiss_index_dir, index_name)
    return os.path.exists(os.path.join(index_path, "index.faiss"))
