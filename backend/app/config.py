"""Application configuration, loaded from environment / .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # OpenAI-compatible endpoint. Ollama locally, or RunPod/vLLM in the cloud —
    # same code, just a different URL + model name.
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "llama3.1:8b"
    # API key; "ollama" is a placeholder Ollama ignores. Set to your RunPod key
    # in the cloud.
    llm_api_key: str = "ollama"

    # Optional separate endpoint for embeddings (cloud LLM-only setups like
    # RunPod vLLM, which serve chat but not embeddings). Empty -> fall back to
    # llm_base_url (the local case, where Ollama serves both).
    embedding_base_url: str = ""

    embedding_model: str = "nomic-embed-text"
    embedding_api_key: str = "ollama"
    embedding_dim: int = 768  # must match schema.sql vector(N)

    database_url: str = "postgresql://secanswer:secanswer@localhost:5432/secanswer"

    retrieval_top_k: int = 5

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
