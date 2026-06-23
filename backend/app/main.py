"""
FastAPI entrypoint: wires up CORS and routes for the offline PDF RAG backend.

Run with: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routes import chat, health, upload

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

settings = get_settings()

app = FastAPI(
    title="Local RAG Document Assistant",
    description="Fully offline PDF Q&A — LangChain + FAISS + Ollama, zero cloud dependency.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(upload.router)
app.include_router(chat.router)


@app.get("/")
def root():
    return {
        "name": "Local RAG Document Assistant",
        "llm_model": settings.ollama_llm_model,
        "embed_model": settings.ollama_embed_model,
    }
