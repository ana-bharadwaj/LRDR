# Local RAG Document Assistant

Fully offline generative AI pipeline for PDF document Q&A. LangChain orchestrates
ingestion and retrieval, FAISS handles embeddings-based vector search, and Ollama
runs both the embedding model and the LLM locally — zero cloud dependency, nothing
leaves your machine.

## Stack

- **Backend:** Python, FastAPI, LangChain, FAISS, Ollama
- **Frontend:** React, TypeScript, Tailwind CSS, Vite

## How it works

1. **Upload** — a PDF is loaded page-by-page (`PyPDFLoader`) and split into
   overlapping chunks with `RecursiveCharacterTextSplitter`. Chunk size and overlap
   are tuned (`backend/.env`) rather than left at library defaults: smaller chunks
   raise retrieval precision on fact-dense text at the cost of more embedding calls;
   the overlap exists specifically so a sentence split across a chunk boundary still
   appears whole in at least one chunk.
2. **Embed** — each chunk is embedded locally via Ollama's `nomic-embed-text` model
   and stored in a FAISS index, persisted to disk under `backend/faiss_index/`.
3. **Ask** — a question is embedded the same way, FAISS returns the top-k most
   similar chunks, and those chunks are passed as context to a local Ollama chat
   model (`llama3.1` by default) with a grounding prompt that refuses to answer
   outside the retrieved context.

## Prerequisites

```bash
# install Ollama: https://ollama.com
ollama pull llama3.1
ollama pull nomic-embed-text
ollama serve   # usually starts automatically; confirm it's listening on :11434
```

## Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs at `http://localhost:8000/docs`.

## Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

App at `http://localhost:5173`.

## API reference

| Method | Endpoint  | Purpose                                  |
| ------ | --------- | ----------------------------------------- |
| GET    | `/health` | Health check                               |
| POST   | `/upload` | Upload a PDF, build/persist FAISS index    |
| POST   | `/ask`    | Ask a question, get a grounded answer      |
| GET    | `/status` | Check whether an index exists              |

## Tuning chunking for your documents

Edit `backend/.env`:

```
CHUNK_SIZE=800       # characters per chunk
CHUNK_OVERLAP=150    # characters shared between consecutive chunks
RETRIEVAL_K=4        # chunks retrieved per question
```

Smaller `CHUNK_SIZE` (e.g. 400–600) works better for dense reference material with
short facts (specs, tables, glossaries). Larger chunks (1200+) preserve more
surrounding context for narrative or explanatory text, at the cost of retrieval
precision.

## Project structure

```
backend/
  app/
    main.py            # FastAPI app, CORS, route registration
    config.py           # env-driven settings
    routes/
      upload.py          # POST /upload
      chat.py            # POST /ask, GET /status
      health.py          # GET /health
    services/
      ingestion.py        # PDF -> chunks -> FAISS (build)
      rag.py               # FAISS -> retrieval -> Ollama generation
    models/
      schemas.py           # request/response Pydantic models
frontend/
  src/
    App.tsx              # layout: upload panel + chat panel
    components/
      PdfUpload.tsx        # file picker, calls /upload
      ChatWindow.tsx        # message list + input, calls /ask
    lib/
      api.ts                # typed fetch wrappers
```
