# InterviewProbe

InterviewProbe is a role-agnostic, **voice-first** adaptive technical interview practice platform. A candidate picks a role, a difficulty, and one or more topics, then conducts the entire interview by voice: the AI interviewer speaks each question aloud (Azure Speech), the candidate answers by speaking (streamed live to Deepgram for transcription), and the backend runs an adaptive interview loop — powered by an LLM behind a provider-neutral abstraction and a [LangGraph](https://github.com/langchain-ai/langgraph) workflow — that analyzes the answer and decides whether to follow up, move to a new topic, ask a clarifying question, or end the interview. At the end, a separate evaluation service scores the transcript and produces a result report. There is no separate text-interview mode and no choice between text and voice — voice is the interview. (There is no video, no WebRTC, and no realtime LLM voice streaming: speech is converted to text and back through discrete TTS/STT calls, not a live audio model.)

High-level flow:

```
create interview → start (first question) → adaptive question/answer loop → complete → evaluation → result
```

## Core architecture

- **Frontend** — React + Vite (React Router for navigation), talking to the backend over a plain JSON REST API.
- **Backend** — FastAPI.
- **PostgreSQL** — the durable source of truth for every interview session, question, message, topic, and evaluation. Every mutation is committed here before anything else happens. Because current interview state (current question, current topic, progress) is always reconstructed from PostgreSQL rather than any in-memory or client-side state, an interrupted interview — a page refresh, a lost connection, a browser restart — recovers automatically: the candidate is shown the same unanswered question they left off on, with no separate "resume" step.
- **Redis** — runtime coordination only, never the source of truth: distributed locks around interview mutations, a fixed-window rate limiter (both per-session and per-client), an idempotency-key store for answer submissions, and a best-effort mirror of current interview runtime state. If Redis is unavailable, the app returns a clear `503`/`REDIS_UNAVAILABLE` for the operations that require it rather than silently skipping a safety guarantee — it never lets stale Redis state override PostgreSQL.
- **LangGraph workflow** — the adaptive interview *engine*: orchestrates the loop (initial question, answer analysis, next-action decision, follow-up/new-topic/clarification question generation) as a graph of nodes. The LLM only ever *proposes* a decision (`FOLLOW_UP`/`CLARIFY`/`NEW_TOPIC`/`END`) or a question — the backend (`decision_validator.py`) validates and is the sole authority over question limits, topic validity, session status, sequence numbers, and every database mutation; an invalid or failed proposal falls back to a deterministic backend decision instead.
- **LLM abstraction** — a provider-neutral interface (`app/llm/`) with OpenAI and Gemini implementations; the app is configured to use one at a time via `LLM_PROVIDER`. Every LLM call returns a Pydantic-validated structured output, never raw/unvalidated text.
- **Knowledge / RAG** — a *grounding layer*, not the adaptive engine itself: an optional retrieval step (`app/knowledge/`) backed by Qdrant and a provider-neutral embedding abstraction (OpenAI embeddings today) that retrieves relevant technical knowledge for the LLM to reference when generating a question. LangGraph decides *what to ask about next*; RAG only supplies *reference material* for that question, scoped by role/topic/(optional concept) so one role's questions can't be grounded in another role's material. Retrieval is entirely optional and fails safe: if Qdrant or the embedding provider is unreachable, slow, or unconfigured, question generation continues ungrounded rather than failing the turn.
- **Evaluation** — a separate service (`app/evaluation/`) that scores a completed interview's *persisted transcript* once — technical knowledge, reasoning, depth, and communication scores, a backend-computed overall score, strengths, weaknesses, and question-linked evidence — persists the result, and serves it idempotently afterward (a second request never re-runs the LLM call).
- **Voice** — the interview *is* voice; there is no text-interview mode to opt out into. `POST /api/v1/voice/tts` synthesizes each question via Azure Speech for browser playback; `POST /api/v1/voice/stt/token` issues a short-lived Deepgram token so the browser can stream the candidate's microphone audio directly to Deepgram over its own WebSocket connection — the backend never proxies that audio. See [Voice architecture](#voice-architecture) below.

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
| Voice | Azure Cognitive Services Speech (TTS), Deepgram (STT) |
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
- Azure Speech and Deepgram credentials — needed for the voice interview to actually work end-to-end (question playback and speech input). There is no browser-speech fallback: without these, the backend's `/voice/tts` and `/voice/stt/token` endpoints fail with a clear `VOICE_SERVICE_MISCONFIGURED` error, and the frontend surfaces that as a voice error state — the candidate can still type an answer into the visible answer field, but cannot hear questions or speak them

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
| `AZURE_SPEECH_KEY` / `AZURE_SPEECH_REGION` / `AZURE_SPEECH_VOICE` / `TTS_TIMEOUT_SECONDS` | required for voice output, backend-only | Azure Speech TTS — this is what speaks each question aloud. The app itself still starts without it; only `POST /voice/tts` fails, with a clear `VOICE_SERVICE_MISCONFIGURED` error. Never exposed to the frontend. |
| `DEEPGRAM_API_KEY` / `STT_AUTH_TIMEOUT_SECONDS` | required for voice input, backend-only, **secret** | The permanent Deepgram API key. The backend only ever exchanges it server-side for a short-lived browser token (`POST /voice/stt/token`, via Deepgram's `/v1/auth/grant`) — the permanent key itself never reaches the frontend. Left blank, that one endpoint fails with the same `VOICE_SERVICE_MISCONFIGURED` error; everything else keeps working. |

`frontend/.env.example` covers the frontend's much smaller surface:

| Variable | Required? | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | required | Backend base URL, e.g. `http://localhost:8000/api/v1` locally. No fallback — if unset in a production build, every API call breaks loudly rather than silently hitting `localhost`. |
| `VITE_TTS_MODE` | **required**, must be `remote` | Selects the TTS provider that plays each question aloud, via the backend's Azure TTS endpoint. `remote` is the only supported value — there is no browser-speech fallback. Any other value (unset, mistyped, or a leftover `browser` from before the voice-first migration) makes the app fail explicitly at startup rather than silently choosing a different speech engine. Never a credential — only ever a mode switch, and `VITE_*` variables ship into the public bundle, so no credential could safely live here anyway. |
| `VITE_STT_MODE` | **required**, must be `remote` | Selects the STT provider for the candidate's spoken answers: the browser streams the microphone directly to Deepgram, authorized by a short-lived token the backend issues. `remote` is the only supported value, with the same fail-explicitly behavior as `VITE_TTS_MODE` above — no browser-speech fallback exists. |

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
| `POST /api/v1/auth/google` | Exchange a Google ID token for a session cookie | body `{credential}`; returns `{data: {user}}`, sets the HttpOnly session cookie |
| `GET /api/v1/auth/me` | Current user | `401` without a valid session |
| `POST /api/v1/auth/logout` | Revoke the session, clear the cookie | `204`, safe when already logged out |
| `POST /api/v1/interviews` | Create a new interview session | role, difficulty, topics, question limit; requires authentication, owned by the caller |
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
- `VITE_TTS_MODE`/`VITE_STT_MODE` must both be set to `remote` in the Vercel project's environment variables — see [Environment configuration](#environment-configuration).

### PostgreSQL, Redis, and Qdrant

- **PostgreSQL** and **Redis** each run as their own managed instance in the same Render environment as the backend, referenced via `DATABASE_URL`/`REDIS_URL` (both dashboard-managed, `sync: false` in `render.yaml` — see above).
- **Qdrant** runs on Qdrant Cloud, referenced via `QDRANT_URL`/`QDRANT_API_KEY`. As noted under [Knowledge / RAG](#core-architecture), this is a grounding layer only — the app runs (with ungrounded question generation) even if it's unreachable.

## Voice architecture

Voice is the interview — there is no text-interview mode and no choice between text and voice. The candidate opens an interview and is talking to it: the AI interviewer speaks every question aloud, and the candidate answers by speaking. (The answer field is still visible and editable as a supporting display of the transcript, and can be typed into directly, but there is no separate "text mode" to switch to.)

The end-to-end turn looks like this:

```
question generated
      ↓
Azure Speech TTS (POST /api/v1/voice/tts)
      ↓
browser audio playback
      ↓
playback finishes → candidate speaks
      ↓
browser MediaRecorder captures microphone audio
      ↓
direct WebSocket connection, browser → Deepgram
      ↓
interim transcript (displayed live) / final transcript (committed to the answer)
      ↓
POST /api/v1/interviews/{id}/answers   (the existing, unchanged answer endpoint)
      ↓
InterviewService → LangGraph
      ↓
next question persisted
      ↓
Azure Speech TTS again
```

- **Text-to-speech**: `POST /api/v1/voice/tts` synthesizes each question via Azure Speech (backend-only credentials, never exposed to the frontend) and returns audio for the browser to play. A small, deterministic speech-presentation layer (`frontend/src/voice/speechPresentation.js`) cleans up markdown and expands a short list of technical-term pronunciations before handing text to the TTS provider — it never changes the question the candidate actually sees.
- **Speech-to-text — the backend does not proxy this audio.** `POST /api/v1/voice/stt/token` exchanges the backend's permanent Deepgram key for a short-lived, single-connection authorization token; the browser then opens its own WebSocket connection **directly to Deepgram** using that token and streams microphone audio to it over that connection. The backend is involved only in minting the token — no interview audio, of any kind, ever transits through the backend. The temporary token is held only in memory for the duration of one connection, never persisted, and the permanent key never leaves the backend.
- **No browser-speech fallback of any kind exists.** There is no `SpeechRecognition`/`webkitSpeechRecognition` or `speechSynthesis`/`SpeechSynthesisUtterance` implementation anywhere in the frontend. `VITE_TTS_MODE` and `VITE_STT_MODE` must both be set to `remote`; any other value makes the app fail explicitly at startup rather than silently falling back to a browser-native speech engine.
- **State machine**: `frontend/src/voice/useVoiceInterviewSession.js` + `voiceReducer.js` own the whole TTS/STT lifecycle (automatic question playback, automatic listening after natural playback completion, manual replay/stop, error recovery) behind a single, race-protected state machine — every async provider callback carries an attempt id so a stale/cancelled callback can never corrupt a newer attempt's state.
- **Stalled-recognition recovery**: after the candidate stops talking (Deepgram signals utterance completion), the state machine enters a brief `PROCESSING` state while it waits for the provider's final transcript or connection close. If that expected completion never arrives, a bounded timeout gives up waiting, cleans up the stalled provider connection, and returns the interface to a normal, usable state — the same recovery path a manual stop takes. **This never submits an answer on its own and is never triggered by silence alone** — it only recovers a connection that has already signaled it's done and then gone quiet; whatever transcript was already captured is preserved either way, and the candidate still submits explicitly.
- **Current status**: Azure Speech is configured and has been verified working in the production environment. Deepgram production configuration still requires `DEEPGRAM_API_KEY` to be set in the Render environment — until that's done, `POST /voice/stt/token` (and therefore live speech input) does not work in production. Production voice input should not be considered verified until that credential is configured and the flow is checked against the live Deepgram service.

## Security notes

- Never commit a real `.env` file or any credential — both `backend/.gitignore` and `frontend/.gitignore` already exclude `.env`.
- Every third-party API credential (LLM, Qdrant, Azure Speech, Deepgram) lives backend-side only; the frontend bundle never contains one. `VITE_*` variables are mode switches or URLs only.
- Deepgram's browser-facing credential is always a short-lived, single-connection token, never the permanent key — and it's never persisted anywhere (not `localStorage`, not a cookie).
- `CORS_ALLOWED_ORIGINS` must include the actual deployed frontend origin in production; it defaults to the local Vite dev server only.
- **Authentication and ownership (Google Sign-In).** The frontend obtains a Google ID token and posts it to `POST /api/v1/auth/google`. The backend verifies it with Google's official library (signature, issuer, audience = `GOOGLE_CLIENT_ID`, expiry, required claims, verified email), finds/creates the user by Google's stable `sub` (never by email), creates a server-side session and sets an **HttpOnly** cookie (`interviewprobe_session`) holding a random 256-bit token. Only the token's SHA-256 hash is stored (`auth_sessions.token_hash`); the raw token is never stored, logged or returned in JSON. `GET /api/v1/auth/me` returns the current user (401 when unauthenticated); `POST /api/v1/auth/logout` revokes the session and clears the cookie.
- **Every interview belongs to exactly one user** (`interview_sessions.user_id`, set from the authenticated session — a client-supplied user id is ignored). All `/api/v1/interviews/{id}...` routes are owner-scoped: the repository filters by `session_id AND user_id`, and a route-level guard runs before locks/idempotency/rate limiting, so another user's interview is indistinguishable from a nonexistent one (`404 INTERVIEW_NOT_FOUND`). Unauthenticated calls get `401 UNAUTHENTICATED`.
- **CSRF / CORS strategy.** Cookie auth is cross-site-attackable, so: (1) credentialed CORS is allowed only for the exact origins in `CORS_ALLOWED_ORIGINS` (a `*` value is rejected at startup); (2) a middleware validates the `Origin` header of every state-changing request (POST/PUT/PATCH/DELETE) against that same list, returning `403 ORIGIN_NOT_ALLOWED` for other origins and for cookie-bearing state-changing requests with no `Origin`; (3) the cookie uses `SameSite`. No separate CSRF token exists — a token that isn't validated would be security theater. For Vercel + Render (different sites) set `SESSION_COOKIE_SAMESITE=none` (which forces `Secure`) and `CORS_ALLOWED_ORIGINS=["https://<frontend origin>"]`.
- Rate limiting (see above) remains the defense against unbounded LLM, Azure TTS, and Deepgram usage; the voice endpoints are still unauthenticated.

## Known limitations

- Interview routes now require a Google Sign-In session (see [Security notes](#security-notes)). The legacy `frontend/` does not send credentials or have a sign-in flow, so it can no longer call the interview endpoints; the current product frontend is `client/` (only the auth API plumbing exists there so far — no sign-in UI yet).
- Interview rows created before authentication existed keep `user_id = NULL`: they are not assigned to any user, are unreachable through the API, and are not deleted. `interview_sessions.user_id` stays nullable until those legacy rows are reviewed (assigned or purged); a follow-up migration can then make it `NOT NULL`.
- Azure Speech (TTS) is configured and verified working in production. **Deepgram (STT) is not yet configured in production** — `DEEPGRAM_API_KEY` still needs to be set in the Render environment. Until that's done, question playback works in production but live speech input does not; production voice input should not be considered verified until that credential is set and the flow is checked against the real Deepgram service.
- There is no recruiter/admin dashboard — result data is only accessible via the API/frontend result page for a given session ID.
- There is no in-browser coding IDE or code-execution environment; answers are free-text (typed or spoken), not executed code.
- RAG grounding is best-effort: Qdrant and the embedding provider are both optional and fail open (ungrounded generation), so retrieval quality depends on whether they're configured and reachable.
