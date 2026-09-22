from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Engineering Interview Platform"
    environment: str = "development"
    # Task 48: the level `app.*` loggers emit at (see app/core/logging_config.py).
    # An unrecognized value falls back to INFO at configure_logging() time
    # rather than failing startup — deliberately not validated here, to
    # keep this settings model free of the custom-validator pattern the
    # rest of it doesn't otherwise use.
    log_level: str = "INFO"
    # Task 50: bounds each individual dependency check inside GET /ready
    # (database, Redis) — short and deliberately separate from any other
    # timeout in this file, since this endpoint must respond quickly even
    # when a dependency is genuinely hung, not just erroring.
    readiness_timeout_seconds: float = 3.0
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
    # Task 49: shorter than llm_timeout_seconds (30s) deliberately — a
    # single embedding call is a much simpler/faster operation than a chat
    # completion, and it sits on the RAG retrieval path a candidate is
    # actively waiting on for their next question, not a background job.
    embedding_timeout_seconds: int = 10

    # Task 20: how many knowledge chunks `retrieve_knowledge` asks for per
    # graph turn. Kept small and bounded — the LLM prompt receives at most
    # this many chunks, never the whole matching set.
    knowledge_retrieval_limit: int = 5

    # Task 25A: browser origins allowed to call this API via CORS. Defaults
    # to the local Vite dev server only — override per environment (e.g. a
    # deployed frontend origin) via the CORS_ALLOWED_ORIGINS env var, given
    # as a JSON array, without touching this code.
    cors_allowed_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Task 40: Azure Speech TTS. Credentials are backend-only and must
    # never be exposed to the frontend. Left unset, `/api/v1/voice/tts`
    # fails clearly with VOICE_SERVICE_MISCONFIGURED on first use — the
    # rest of the app starts and runs fine without them, same as
    # `llm_api_key` above.
    tts_provider: str = "azure"
    azure_speech_key: str | None = None
    azure_speech_region: str | None = None
    azure_speech_voice: str = "en-IN-PrabhatNeural"
    tts_timeout_seconds: int = 15

    # Task 41: Deepgram streaming STT. The backend only ever exchanges this
    # permanent key for a short-lived token (POST /api/v1/voice/stt/token)
    # — it never streams audio itself; the browser streams directly to
    # Deepgram using that token. Left unset, the token endpoint fails
    # clearly with VOICE_SERVICE_MISCONFIGURED on first use, same as the
    # Azure settings above.
    stt_auth_provider: str = "deepgram"
    deepgram_api_key: str | None = None
    stt_auth_timeout_seconds: int = 10

    # Task 46: per-client (IP-based) abuse protection for the four
    # endpoints reachable with no existing interview session to scope a
    # rate limit by — this app has no authentication, so these are the
    # only protection against unbounded paid-API usage (LLM calls via
    # interview creation/start, Azure TTS, Deepgram token issuance).
    interview_creation_rate_limit: int = 10
    interview_creation_rate_window_seconds: int = 60
    interview_start_rate_limit: int = 5
    interview_start_rate_window_seconds: int = 60
    voice_tts_rate_limit: int = 30
    voice_tts_rate_window_seconds: int = 60
    voice_stt_token_rate_limit: int = 10
    voice_stt_token_rate_window_seconds: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
