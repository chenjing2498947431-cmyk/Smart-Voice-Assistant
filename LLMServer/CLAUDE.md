# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**LLM RAG Server** is a Python FastAPI service that implements a retrieval-augmented generation (RAG) pipeline, integrating Volcano Knowledge Base for semantic search and Doubao Ark for LLM inference. It provides OpenAI-compatible `/v1/chat/completions` endpoints for integration with RTC voice services and frontend applications.

### Key Architecture Components

**RAG Pipeline Flow:**
1. User query → `/v1/chat/completions` endpoint
2. Extract latest user message
3. Retrieve relevant knowledge chunks from Volcano Knowledge Base (top_k=4 by default)
4. Dynamically construct system prompt with retrieved context
5. Stream response via Doubao Ark API (using OpenAI SDK wrapper)

**Two Interaction Modes:**
- **Session Mode** (recommended): Client calls `/v1/context/create` to get `context_id`, then includes it in subsequent requests. Server maintains session state via `SessionManager` and Volcano Responses API handles conversation history server-side.
- **Stateless Mode** (fallback): No session ID; client manages full conversation history in `messages` array. Graceful degradation if context creation fails.

**Module Structure:**
- `llm/router.py` - Main API routes (`/v1/chat/completions`, `/v1/context/create`)
- `llm/ark_client.py` - Doubao Ark streaming client (wraps OpenAI SDK)
- `llm/session_manager.py` - In-memory session storage with `sid → latest_response_id` mapping
- `knowledge_base/viking_kb.py` - Volcano Knowledge Base SearchKnowledge API with V4 request signing
- `rag/pipeline.py` - Core orchestration: query extraction, retrieval, prompt assembly
- `rag/prompt.py` - System prompt templates (hit/no-hit branches for zero-result strategy)
- `storage/sqlite.py` - SQLite backing (for conversation logs, can be extended)
- `debug_routes.py` - `/debug/rag` and `/debug/search` endpoints (zero-token cost validation)

## Development Commands

**Setup:**
```bash
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Unix:
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with ARK_API_KEY, ARK_CHAT_ENDPOINT_ID, VIKING_KB_* credentials
```

**Run Server:**
```bash
# Option 1: Direct
python app.py

# Option 2: With uvicorn (allows --reload for dev)
uvicorn app:app --host 0.0.0.0 --port 3000 --reload
```

**Validate & Debug:**
```bash
# Full RAG pipeline (retrieval + prompt assembly)
curl "http://localhost:3000/debug/rag?q=product%20refund%20policy"

# Search only (no LLM, no prompt assembly)
curl "http://localhost:3000/debug/search?q=refund&top_k=3"

# Health check
curl http://localhost:3000/health

# Interactive API docs
open http://localhost:3000/docs
```

**Create Knowledge Base Collection (one-time):**
```bash
python -m scripts.create_collection my_kb_name
```

## Type Checking & Linting

**Type checking** (Pyright via Pylance):
```bash
# Configured in pyproject.toml [tool.pyright]
# Validate with: pyright . (if installed)
```

**Linting** (Ruff):
```bash
# Check syntax/style
ruff check .

# Auto-fix issues
ruff check . --fix
```

## Configuration (`.env`)

Critical variables:
- `ARK_API_KEY` - Doubao API key
- `ARK_CHAT_ENDPOINT_ID` - Chat endpoint ID (format: `ep-xxxxx`)
- `VIKING_KB_AK` / `VIKING_KB_SK` - Volcano account credentials
- `VIKING_KB_COLLECTION_NAME` - Knowledge base collection
- Optional: `ARK_BASE_URL`, `VIKING_KB_HOST`, `VIKING_KB_REGION`, `VIKING_KB_TOP_K`, `SERVER_PORT`

See README.md table for full details.

## Known Limitations & Design Decisions

- **Session Storage:** In-memory dict + asyncio.Lock. Server restart loses all sessions. Production should use Redis/SQLite.
- **Responses API vs Context API:** Using Responses API (`previous_response_id` chaining) for broader model compatibility (Lite/Seed series not supported by Context API).
- **Zero-Result Strategy:** If retrieval fails, still invoke LLM with "no data found" system prompt to reduce hallucinations rather than hard rejection.
- **RAG + Session Coexistence:** System prompt set once at context creation; retrieval happens per-turn and content is injected as "reference materials" in user message to keep persona separate.
- **Not Implemented:** Reranking, authentication, session TTL cleanup.

## Quick Integration Examples

**Stateless (no session):**
```bash
curl -X POST http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"question"}],"stream":false}'
```

**Session Mode:**
```bash
# 1. Create context
CTX=$(curl -s -X POST http://localhost:3000/v1/context/create \
  -H "Content-Type: application/json" -d '{}' | jq -r .context_id)

# 2. Multi-turn with context
curl -X POST http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{\"context_id\":\"$CTX\",\"messages\":[{\"role\":\"user\",\"content\":\"question\"}],\"stream\":false}"
```

## Testing

No automated test suite currently. Validation done via:
1. `/debug/rag?q=...` endpoint (full pipeline, zero LLM cost)
2. `/debug/search?q=...` endpoint (retrieval only)
3. Manual cURL requests to `/v1/chat/completions` (see README.md examples)
