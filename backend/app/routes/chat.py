import logging

from fastapi import APIRouter, HTTPException

from ..config import get_settings
from ..models.schemas import AskRequest, AskResponse, SourceSnippet, StatusResponse
from ..services.ingestion import index_exists
from ..services.rag import answer_question

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    settings = get_settings()
    try:
        answer, model_used, sources, took = answer_question(
            req.question, req.index_name, settings
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Ask failed")
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {exc}") from exc

    return AskResponse(
        answer=answer,
        model_used=model_used,
        sources=[SourceSnippet(**s) for s in sources] if req.show_sources else [],
        processing_time_seconds=took,
    )


@router.get("/status", response_model=StatusResponse)
def status(index_name: str = "default"):
    settings = get_settings()
    return StatusResponse(index_name=index_name, indexed=index_exists(index_name, settings))
