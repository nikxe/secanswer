"""LLM completion via the OpenAI-compatible endpoint (Ollama llama3.1:8b)."""
from openai import OpenAI

from .config import settings

_client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)


def generate(messages: list[dict]) -> str:
    resp = _client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        temperature=0.0,  # deterministic for a Q&A/grounding task
    )
    return resp.choices[0].message.content
