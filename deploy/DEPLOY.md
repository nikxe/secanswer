# Deploying SecAnswer to the Cloud (v2)

The **same code** runs locally (Ollama + local Postgres) and in the cloud — only
environment variables change. Confirmed stack:

```
Next.js (Vercel) ──► FastAPI (Railway, from backend/Dockerfile)
                       ├── LLM:        RunPod Serverless (vLLM, OpenAI-compatible)
                       ├── Embeddings: local Ollama (or a backend-side Ollama later)
                       └── Database:   Supabase (Postgres + pgvector)
```

---

## 1. GPU (LLM) — RunPod Serverless

Full steps in [`runpod/README.md`](runpod/README.md). In short:

1. RunPod → **Serverless** → **New Endpoint** → **vLLM** template.
2. Model: `NousResearch/Meta-Llama-3.1-8B-Instruct` (ungated mirror).
3. GPU: **24GB**; workers `min=0, max=1` (scale-to-zero saves credits).
4. Copy the **Endpoint ID**.

OpenAI-compatible URL:

```
https://api.runpod.ai/v2/<ENDPOINT_ID>/openai/v1
```

Verify:

```bash
python scripts/verify_llm.py \
  --base-url https://api.runpod.ai/v2/<ENDPOINT_ID>/openai/v1 \
  --llm-model NousResearch/Meta-Llama-3.1-8B-Instruct
```

> RunPod vLLM serves chat only, not embeddings — hence the app separates
> `EMBEDDING_BASE_URL` from `LLM_BASE_URL`. Keep embeddings on local Ollama.

---

## 2. Database — Supabase

1. Create a project (free tier).
2. **SQL editor** → run:
   ```sql
   create extension if not exists vector;
   ```
   then paste the contents of `backend/schema.sql` and run it.
3. **Settings → Database → Connection string** → copy the **Direct connection**
   (port 5432, not the pooler — psycopg + pgvector need a real session).
   This becomes `DATABASE_URL`.

---

## 3. Backend — Railway

The backend is a self-contained container ([`backend/Dockerfile`](../backend/Dockerfile)):

1. Railway → **New Project** → **Deploy from GitHub repo**.
2. Set **Root Directory** to `backend` (so the Dockerfile's relative `COPY`
   paths resolve against `backend/`).
3. Railway auto-detects `backend/Dockerfile` and injects `$PORT`; the image's
   `CMD` already listens on `${PORT:-8000}`.
4. Add these env vars on the service (from `.env.production.example`):

   | Var | Cloud value |
   |---|---|
   | `LLM_BASE_URL` | `https://api.runpod.ai/v2/<ID>/openai/v1` |
   | `LLM_MODEL` | `NousResearch/Meta-Llama-3.1-8B-Instruct` |
   | `EMBEDDING_BASE_URL` | *(leave empty — local Ollama)* |
   | `EMBEDDING_MODEL` | `nomic-embed-text` |
   | `DATABASE_URL` | Supabase direct connection string |

---

## 4. Frontend — Vercel

1. Import the `frontend/` directory.
2. Set `NEXT_PUBLIC_API_URL` to the Railway service URL.

---

## Why this is "same code"

Local: `LLM_BASE_URL=http://localhost:11434/v1` (Ollama), `DATABASE_URL` → local
Postgres. Cloud: `LLM_BASE_URL` → RunPod, `DATABASE_URL` → Supabase. No
application code changes — the provider abstraction (OpenAI-compatible API + env
config) is the whole point.
