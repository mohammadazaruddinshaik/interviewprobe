from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Engineering Interview Platform"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_interview"
    redis_url: str = "redis://localhost:6379/0"
    redis_interview_state_ttl_seconds: int = 86400
    redis_interview_lock_ttl_seconds: int = 30
    redis_interview_rate_limit: int = 10
    redis_interview_rate_window_seconds: int = 60
    redis_idempotency_ttl_seconds: int = 86400
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str | None = None
    llm_timeout_seconds: int = 30
    llm_max_retries: int = 2

    # Knowledge/RAG foundation (Task 19). `embedding_api_key` is optional —
    # when unset, the embedding factory falls back to `llm_api_key` so a
    # single OpenAI key can cover both, without hardcoding that fallback
    # into this settings model.
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "interview_knowledge"
    qdrant_api_key: str | None = None
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_api_key: str | None = None

    # Task 20: how many knowledge chunks `retrieve_knowledge` asks for per
    # graph turn. Kept small and bounded — the LLM prompt receives at most
    # this many chunks, never the whole matching set.
    knowledge_retrieval_limit: int = 5

    # Task 25A: browser origins allowed to call this API via CORS. Defaults
    # to the local Vite dev server only — override per environment (e.g. a
    # deployed frontend origin) via the CORS_ALLOWED_ORIGINS env var, given
    # as a JSON array, without touching this code.
    cors_allowed_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
