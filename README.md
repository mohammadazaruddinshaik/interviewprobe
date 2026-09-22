# InterviewProbe

InterviewProbe is a role-agnostic, adaptive technical interview practice platform. A candidate picks a role, a difficulty, and one or more topics; the backend runs an adaptive interview loop — powered by an LLM behind a provider-neutral abstraction and a [LangGraph](https://github.com/langchain-ai/langgraph) workflow — that asks a question, analyzes the answer, and decides whether to follow up, move to a new topic, ask a clarifying question, or end the interview. At the end, a separate evaluation service scores the transcript and produces a result report. An optional voice mode lets the candidate hear questions spoken aloud and answer by speaking instead of typing.

High-level flow:

```
create interview → start (first question) → adaptive question/answer loop → complete → evaluation → result
```

## Core architecture

- **Frontend** — React + Vite (React Router for navigation), talking to the backend over a plain JSON REST API.
- **Backend** — FastAPI.
- **PostgreSQL** — the durable source of truth for every interview session, question, message, topic, and evaluation. Every mutation is committed here before anything else happens.
- **Redis** — runtime coordination only, never the source of truth: distributed locks around interview mutations, a fixed-window rate limiter (both per-session and per-client), an idempotency-key store for answer submissions, and a best-effort mirror of current interview runtime state. If Redis is unavailable, the app returns a clear `503`/`REDIS_UNAVAILABLE` for the operations that require it rather than silently skipping a safety guarantee — it never lets stale Redis state override PostgreSQL.
- **LangGraph workflow** — orchestrates the adaptive interview loop (initial question, answer analysis, next-action decision, follow-up/new-topic question generation) as a graph of nodes, with a deterministic fallback whenever the LLM's proposed next action is invalid.
- **LLM abstraction** — a provider-neutral interface (`app/llm/`) with OpenAI and Gemini implementations; the app is configured to use one at a time via `LLM_PROVIDER`.
- **Knowledge / RAG** — an optional retrieval layer (`app/knowledge/`) backed by Qdrant and a provider-neutral embedding abstraction (OpenAI embeddings today). Retrieval is scoped by role/topic/(optional concept) so one role's questions can't be grounded in another role's material. Retrieval is entirely optional and fails safe: if Qdrant or the embedding provider is unreachable, slow, or unconfigured, question generation continues ungrounded rather than failing the turn.
- **Evaluation** — a separate service (`app/evaluation/`) that scores a completed interview's transcript once, persists the result, and serves it idempotently afterward (a second request never re-runs the LLM call).
- **Voice** — an optional voice interview mode. `POST /api/v1/voice/tts` synthesizes a question via Azure Speech; `POST /api/v1/voice/stt/token` issues a short-lived Deepgram token so the browser can stream the candidate's microphone audio directly to Deepgram. Both are backend-gated behind their own configuration and both fall back to the browser's own Web Speech API when the "remote" providers aren't enabled — see [Voice architecture](#voice-architecture) below.

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite, React Router, Tailwind CSS, Vitest |
| Backend | FastAPI, Pydantic / pydantic-settings, SQLAlchemy, Alembic |
| Database | PostgreSQL (via `psycopg`) |
| Cache / coordination | Redis |
| Workflow orchestration | LangGraph |
| LLM providers | OpenAI, Google Gemini (`google-genai`) |
| Vector store | Qdrant |
| Voice | Azure Cognitive Services Speech (TTS), Deepgram (STT), browser Web Speech API (fallback) |
| Testing | pytest / pytest-asyncio (backend), Vitest + Testing Library (frontend) |

## Repository structure

```
backend/
  app/
    api/            # FastAPI routes and dependency wiring
    core/           # settings, logging, readiness checks
    domain/         # roles/topics/enums shared across the app
    evaluation/      # post-interview scoring service
    knowledge/       # RAG: embedding provider, Qdrant store, retrieval service
    llm/             # provider-neutral LLM abstraction (OpenAI, Gemini)
    models/          # SQLAlchemy models
    redis/           # locks, rate limiting, idempotency, runtime-state mirror
    repositories/    # DB access for interview data
    schemas/         # Pydantic request/response models
    services/        # interview lifecycle, result assembly
    voice/           # Azure TTS + Deepgram STT-auth providers
    workflows/       # the LangGraph interview graph and its nodes
  alembic/           # database migrations
  requirements.txt   # pinned backend dependencies
  .env.example
  .python-version
frontend/
  src/
    api/             # backend API client
    components/      # interview UI, including the voice room
    pages/           # top-level routed pages
    voice/           # voice state machine + TTS/STT provider abstraction
  vercel.json         # SPA rewrite for Vercel
  .env.example
render.yaml           # backend Render Blueprint (see Deployment)
```

## Local development

### Prerequisites

- Python matching `backend/.python-version` (currently `3.12.12`)
- Node.js (for `npm`) and a recent `npm`
- A local PostgreSQL instance
- A local Redis instance
- (Optional, for RAG) A local or cloud Qdrant instance
- (Optional) An OpenAI or Gemini API key — the app starts and most of the API works without one; only the LLM-backed endpoints (`/start`, `/answers`) fail with a clear error until it's set
- (Optional) Azure Speech and/or Deepgram credentials — only needed for the "remote" voice providers; the browser fallback needs neither

### Environment configuration

Copy the example files and fill in what you need:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

`backend/.env.example` is the authoritative list of backend settings. The most important ones:

| Variable | Required? | Purpose |
|---|---|---|
| `DATABASE_URL` | required for anything DB-backed | PostgreSQL connection string. Defaults to a local `postgres:postgres@localhost:5432/ai_interview`. |
| `REDIS_URL` | required for locking/rate-limiting/idempotency | Redis connection string. Defaults to local `redis://localhost:6379/0`. |
| `LLM_PROVIDER` / `LLM_MODEL` / `LLM_API_KEY` | `LLM_API_KEY` required to actually generate questions/evaluations | Selects `openai` or `gemini` and the model; the app starts fine with no key, only LLM-backed calls fail. |
| `QDRANT_URL` / `QDRANT_COLLECTION` / `QDRANT_API_KEY` | optional | RAG vector store connection. Qdrant connectivity is lazy — the app starts fine even if it's unreachable. |
| `EMBEDDING_PROVIDER` / `EMBEDDING_MODEL` / `EMBEDDING_API_KEY` | optional (falls back to `LLM_API_KEY` if unset) | Embedding provider used for RAG queries. |
| `EMBEDDING_TIMEOUT_SECONDS` (default `10`) | optional | Bounds a single embedding call; a timeout degrades to ungrounded generation, it never fails the turn. |
| `KNOWLEDGE_RETRIEVAL_LIMIT` (default `5`) | optional | Max knowledge chunks retrieved per graph turn. |
| `CORS_ALLOWED_ORIGINS` | required in production if the frontend is on a different origin | JSON array of allowed browser origins. Defaults to the local Vite dev server only (`http://localhost:5173`, `http://127.0.0.1:5173`) — a deployed frontend origin must be added explicitly. |
| `LOG_LEVEL` (default `INFO`) | optional | Level `app.*` loggers emit at; an unrecognized value falls back to `INFO` rather than failing startup. |
| `READINESS_TIMEOUT_SECONDS` (default `3`) | optional | Bounds each dependency check inside `GET /ready`. |
| `AZURE_SPEECH_KEY` / `AZURE_SPEECH_REGION` / `AZURE_SPEECH_VOICE` / `TTS_TIMEOUT_SECONDS` | optional, backend-only | Azure Speech TTS. Left blank, `POST /voice/tts` fails with a clear `VOICE_SERVICE_MISCONFIGURED` — everything else keeps working. |
| `DEEPGRAM_API_KEY` / `STT_AUTH_TIMEOUT_SECONDS` | optional, backend-only | Deepgram token issuance for STT. Left blank, `POST /voice/stt/token` fails the same way. |

`frontend/.env.example` covers the frontend's much smaller surface:

| Variable | Required? | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | required | Backend base URL, e.g. `http://localhost:8000/api/v1` locally. No fallback — if unset in a production build, every API call breaks loudly rather than silently hitting `localhost`. |
| `VITE_TTS_MODE` (default `browser`) | optional | `browser` uses the Web Speech API directly; `remote` calls the backend's Azure TTS endpoint. Never a credential — only ever a mode switch, and `VITE_*` variables ship into the public bundle, so no credential could safely live here anyway. |
| `VITE_STT_MODE` (default `browser`) | optional | Same idea for speech-to-text: `browser` uses Web Speech API `SpeechRecognition`; `remote` streams the microphone directly to Deepgram, authorized by a short-lived token the backend issues. |

Real credentials never belong in `.env.example` — every value there is a placeholder or a safe local default. Never commit a real `.env` file (both `backend/.gitignore` and `frontend/.gitignore` already exclude it).

### Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Apply migrations before starting the app for the first time (and after pulling any change that adds one):

```bash
alembic upgrade head
```

Migrations do **not** run automatically on a local `uvicorn` start — you have to run this yourself. (In production, Render's start command runs it automatically before `uvicorn` starts — see [Deployment](#deployment).)

Start Redis and PostgreSQL locally however you normally do (e.g. `redis-server`, `pg_ctl`/a package-manager service, or your own Postgres/Redis install) so they're reachable at the URLs in `backend/.env`.

Qdrant is optional for local development — the app runs fine without it, with RAG-grounded question generation degrading to ungrounded. If you want it, point `QDRANT_URL` at a running instance (a local `docker run qdrant/qdrant` or Qdrant Cloud both work — the app doesn't care which). There is no CLI seeding command; `app/knowledge/seed_data.py` exposes `seed_knowledge_store(store, embedding_provider)` as an importable helper (used by the opt-in Qdrant integration test) for manually seeding a small deterministic dataset — there's no packaged script that runs it for you.

Start the backend:

```bash
uvicorn app.main:app --reload
```

### Frontend setup

```bash
cd frontend
npm install
npm run dev
```

### Running tests

Backend:

```bash
cd backend
pytest
```

A handful of tests are gated behind explicit opt-in env vars and are skipped otherwise: `RUN_LLM_INTEGRATION_TESTS=true` (needs a real `LLM_API_KEY`) and `RUN_QDRANT_INTEGRATION_TESTS=true` (needs a real reachable Qdrant). Redis-integration tests skip automatically if Redis isn't reachable rather than failing.

Frontend:

```bash
cd frontend
npm test        # vitest run
npm run lint     # oxlint
npm run build    # production build
```

## API overview

All application routes are mounted under `/api/v1`. This is an overview, not a full spec — see the actual route/schema modules (`app/api/routes/`, `app/schemas/`) for exact request/response fields.

| Endpoint | Purpose | Notes |
|---|---|---|
| `POST /api/v1/interviews` | Create a new interview session | role, difficulty, topics, question limit |
| `POST /api/v1/interviews/{id}/start` | Start a `CREATED` session, generate the first question | one real LLM call |
| `POST /api/v1/interviews/{id}/answers` | Submit an answer, get the next action/question | requires an `Idempotency-Key` header; a repeated request with the same key and the same answer replays the original response rather than re-mutating |
| `GET /api/v1/interviews/{id}` | Current interview state | topics, current question, progress |
| `POST /api/v1/interviews/{id}/complete` | Mark an interview complete | |
| `GET /api/v1/interviews/{id}/evaluation` | Get (generating on first call, then cached) the scored evaluation | only valid once the interview is `COMPLETED` |
| `GET /api/v1/interviews/{id}/result` | Full result report: session, topics, questions/answers, evaluation | |
| `POST /api/v1/voice/tts` | Synthesize speech for a question via Azure | text capped at 2,000 characters |
| `POST /api/v1/voice/stt/token` | Issue a short-lived Deepgram token for browser-direct STT | the permanent Deepgram key never leaves the backend |
| `GET /health` | Liveness | see [Health & readiness](#health--readiness) |
| `GET /ready` | Readiness | see [Health & readiness](#health--readiness) |

### Rate limiting

The app has no authentication, so every endpoint that can trigger paid third-party usage (an LLM call, Azure TTS, or Deepgram token issuance) is rate-limited — per interview session where one already exists, per client IP otherwise (`request.client.host`, never a client-supplied header like `X-Forwarded-For`). Current defaults (all Redis-backed fixed windows, all configurable — see `app/core/config.py`):

| Endpoint | Limit | Scope |
|---|---:|---|
| `POST /interviews` | 10 / 60s | client IP |
| `POST /interviews/{id}/start` | 5 / 60s | client IP |
| `POST /interviews/{id}/answers` | 10 / 60s | interview session |
| `POST /voice/tts` | 30 / 60s | client IP |
| `POST /voice/stt/token` | 10 / 60s | client IP |

A rejected request gets `429` with `{"error": {"code": "RATE_LIMITED", "message": "..."}}` and a `Retry-After` header. If Redis itself is unavailable, the app returns `503`/`REDIS_UNAVAILABLE` rather than silently letting the request through unthrottled.

## Health & readiness

- **`GET /health`** — a lightweight liveness check. Always returns `200 {"status": "ok"}` and touches no dependency. Confirms only that the process is up.
- **`GET /ready`** — a readiness check. Verifies the process can actually reach PostgreSQL (`SELECT 1`) and Redis (`PING`), each bounded by `READINESS_TIMEOUT_SECONDS` (default `3`s) so a hung dependency can't hang the response. Returns `200 {"status": "ready", "checks": {"database": "ok", "redis": "ok"}}` when both are reachable, `503 {"status": "not_ready", "checks": {...}}` (naming which one failed as `"unavailable"`) otherwise. Neither check mutates any state, and the response never includes connection strings, credentials, or exception text.

`render.yaml`'s `healthCheckPath` currently still points at `/health`, not `/ready` — Render's deploy-gating/monitoring is unaffected by `/ready`'s existence unless that's changed deliberately (a real operational tradeoff: pointing ongoing monitoring at a dependency-aware check means a brief Redis blip could be treated as an unhealthy instance).

## Deployment

### Backend — Render

- Root directory: `backend`.
- Build: `pip install -r requirements.txt` (pinned exact versions — see `backend/requirements.txt`).
- Start: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` — migrations always run before the new code that depends on them goes live.
- Python version: `backend/.python-version` (`3.12.12`).
- `render.yaml` at the repo root describes this as a Render Blueprint, but **a Blueprint file existing in the repo does not mean it's active** — Render only adopts it after an explicit "New Blueprint"/"Sync" action in the dashboard, and every credential-bearing environment variable in it is declared `sync: false` so nothing in the file can overwrite a value already set manually. Until that dashboard step happens (or if the service was created manually, as is typical), the actual build/start command, environment variables, and Python version in effect are whatever the Render dashboard has configured directly — treat the dashboard as authoritative, and `render.yaml` as a reproducible description of what it's meant to match.

### Frontend — Vercel

- Framework: Vite (React).
- `frontend/vercel.json` adds an explicit SPA rewrite (`/(.*) → /index.html`) so client-side routes (e.g. `/interview/:sessionId`) resolve correctly on direct navigation/refresh rather than 404ing at the edge.
- `VITE_API_BASE_URL` must be set in the Vercel project's environment variables to the deployed backend's `/api/v1` URL — there's no fallback, so a missing value breaks the whole app loudly (not a silent `localhost` call).

## Voice architecture

Voice is an optional interview mode, not a separate product surface — the same interview lifecycle and API drive both text and voice mode.

- **Text-to-speech**: `POST /api/v1/voice/tts` synthesizes a question via Azure Speech (backend-only credentials, never exposed to the frontend). A small, deterministic speech-presentation layer (`frontend/src/voice/speechPresentation.js`) cleans up markdown and expands a short list of technical-term pronunciations before handing text to any TTS provider — it never changes the question the candidate actually sees.
- **Speech-to-text**: `POST /api/v1/voice/stt/token` exchanges the backend's permanent Deepgram key for a short-lived token; the browser then streams the microphone directly to Deepgram over that token — audio never passes through the backend. The temporary token is held only in memory for the duration of one connection, never persisted.
- **Browser fallback**: when the "remote" providers aren't enabled (`VITE_TTS_MODE`/`VITE_STT_MODE` left at their `browser` default, or the remote provider errors), the frontend falls back to the browser's own Web Speech API (`SpeechSynthesis`/`SpeechRecognition`). Support varies significantly by browser — Chrome and Edge are the most reliable; Safari and Firefox have limited or no `SpeechRecognition` support.
- **State machine**: `frontend/src/voice/useVoiceInterviewSession.js` + `voiceReducer.js` own the whole TTS/STT lifecycle (automatic question playback, automatic listening after natural playback completion, manual replay/stop, error recovery) behind a single, race-protected state machine — every async provider callback carries an attempt id so a stale/cancelled callback can never corrupt a newer attempt's state.
- **Current status**: as of this writing, no real Azure Speech or Deepgram credentials are configured in this deployment's environment. Both remote providers and their error paths are covered by tests against mocked/faked SDKs, and the full voice interaction flow (state machine, automatic TTS→STT handoff, error recovery) has been verified live in a real browser against the **browser-fallback** providers — but **not** against the real Azure/Deepgram services, which remains a genuine deployment step, not something already verified.

## Security notes

- Never commit a real `.env` file or any credential — both `backend/.gitignore` and `frontend/.gitignore` already exclude `.env`.
- Every third-party API credential (LLM, Qdrant, Azure Speech, Deepgram) lives backend-side only; the frontend bundle never contains one. `VITE_*` variables are mode switches or URLs only.
- Deepgram's browser-facing credential is always a short-lived, single-connection token, never the permanent key — and it's never persisted anywhere (not `localStorage`, not a cookie).
- `CORS_ALLOWED_ORIGINS` must include the actual deployed frontend origin in production; it defaults to the local Vite dev server only.
- **This application has no authentication or ownership model.** Any interview `session_id` (a UUID) that reaches someone — via a shared link, browser history, a referrer header, or a log — functions as a bearer credential for that interview's full transcript, evaluation, and result. UUIDv4 makes brute-force guessing impractical, but a leaked link is not.
- Rate limiting (see above) is the primary defense against unbounded resource/cost abuse of LLM, Azure TTS, and Deepgram usage, given the lack of authentication.

## Known limitations

- No authentication or per-user ownership model exists anywhere in the app; a session ID is effectively a bearer credential (see [Security notes](#security-notes)).
- Real Azure Speech / Deepgram production credentials are not currently configured in this environment — remote voice providers are implemented and tested against mocks, but not yet verified against the live third-party services.
- Browser-fallback speech recognition/synthesis quality and availability depend entirely on the candidate's browser (best on Chrome/Edge; limited or absent on Safari/Firefox).
- There is no recruiter/admin dashboard — result data is only accessible via the API/frontend result page for a given session ID.
- There is no in-browser coding IDE or code-execution environment; answers are free-text (typed or spoken), not executed code.
- RAG grounding is best-effort: Qdrant and the embedding provider are both optional and fail open (ungrounded generation), so retrieval quality depends on whether they're configured and reachable.
