from pydantic import BaseModel


class UploadResponse(BaseModel):
    filename: str
    chunks_indexed: int
    index_name: str


class AskRequest(BaseModel):
    question: str
    index_name: str = "default"
    show_sources: bool = True


class SourceSnippet(BaseModel):
    page: int | str
    snippet: str


class AskResponse(BaseModel):
    answer: str
    model_used: str
    sources: list[SourceSnippet] = []
    processing_time_seconds: float


class StatusResponse(BaseModel):
    index_name: str
    indexed: bool
    chunk_count: int | None = None
