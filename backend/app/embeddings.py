"""Embeddings via the OpenAI-compatible endpoint (Ollama nomic-embed-text).

Kept behind two small functions so the provider can be swapped (e.g. to a local
sentence-transformers BGE model) without touching retrieval or ingestion.
"""
from openai import OpenAI

from .config import settings

_client = OpenAI(
    base_url=settings.embedding_base_url or settings.llm_base_url,
    api_key="ollama",  # key ignored by Ollama
)


def embed(text: str) -> list[float]:
    resp = _client.embeddings.create(model=settings.embedding_model, input=text)
    return resp.data[0].embedding


def embed_many(texts: list[str]) -> list[list[float]]:
    resp = _client.embeddings.create(model=settings.embedding_model, input=texts)
    return [d.embedding for d in resp.data]
