# RunPod Serverless — LLM endpoint (vLLM)

This is the GPU half of the cloud deployment. It serves an **OpenAI-compatible**
chat endpoint running an open-weights model via vLLM, which our `LLM_BASE_URL`
points at — same code as local, different URL.

## Cost notes (you have ~$10)

- Serverless bills **per request + per second of GPU**, with **scale-to-zero**:
  no idle cost, but the first request after idle pays a cold start.
- `min_workers=0` saves credits; `min_workers=1` removes cold starts but idles
  the GPU (burns credits continuously). For a demo, use `0`.

## Create the endpoint (console)

1. RunPod → **Serverless** → **New Endpoint**.
2. Choose the **vLLM** template (`runpod/worker-vllm`).
3. Model — use an *ungated* Llama 3.1 8B Instruct mirror (Meta's original is
   gated on Hugging Face):
   - `NousResearch/Meta-Llama-3.1-8B-Instruct`
4. GPU: **24GB** (A40 / L40S / RTX 4090) — 8B fits comfortably.
5. Workers: `min=0`, `max=1` (or 2 if you want concurrency).
6. Create → copy the **Endpoint ID**.

The OpenAI-compatible base URL is:

```
https://api.runpod.ai/v2/<ENDPOINT_ID>/openai/v1
```

## Verify

```bash
python scripts/verify_llm.py \
  --base-url https://api.runpod.ai/v2/<ENDPOINT_ID>/openai/v1 \
  --llm-model NousResearch/Meta-Llama-3.1-8B-Instruct
```

Then point the app at it:

```bash
# backend/.env
LLM_BASE_URL=https://api.runpod.ai/v2/<ENDPOINT_ID>/openai/v1
LLM_MODEL=NousResearch/Meta-Llama-3.1-8B-Instruct
# leave EMBEDDING_BASE_URL empty (or point at local Ollama)
```

> **Note:** RunPod vLLM serves chat only, not embeddings — which is why the app
> now separates `EMBEDDING_BASE_URL` from `LLM_BASE_URL`. Keep embeddings local
> (Ollama) for now; that's the cheapest and most reliable split.
