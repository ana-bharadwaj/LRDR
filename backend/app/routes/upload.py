import logging
import os
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..config import get_settings
from ..models.schemas import UploadResponse
from ..services import cache as answer_cache
from ..services.ingestion import build_and_save_index, load_and_chunk

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...), index_name: str = "default"):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    settings = get_settings()
    max_bytes = settings.max_file_size_mb * 1024 * 1024

    contents = await file.read()
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.max_file_size_mb}MB limit.",
        )

    # Write to a temp file since PyPDFLoader expects a filesystem path.
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        chunks = load_and_chunk(tmp_path, settings)
        chunk_count = build_and_save_index(chunks, index_name, settings)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Ingestion failed")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc
    finally:
        os.unlink(tmp_path)

    if settings.cache_enabled:
        answer_cache.invalidate_cache(index_name, settings.cache_dir)

    return UploadResponse(
        filename=file.filename,
        chunks_indexed=chunk_count,
        index_name=index_name,
    )
