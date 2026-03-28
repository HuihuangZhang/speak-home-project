# Speak Home — AI Exercise Tutor

A real-time voice AI fitness coach powered by LiveKit. Talk to Alex, your personal trainer, via voice — get exercise plans, coaching, and post-session summaries.

## Architecture

The system has three services. The **Next.js frontend** handles the voice UI and calls the **FastAPI backend** over HTTP for auth, session lifecycle, and LiveKit tokens. Once connected, all real-time audio flows exclusively through **LiveKit** — the browser publishes microphone audio via WebRTC, and the **Agent Worker** receives it, runs it through a VAD → STT → LLM → TTS pipeline, and publishes the synthesised voice back. The API and Agent Worker never call each other; they coordinate through a shared SQLite database.

```
Browser
  │  HTTP/JSON (auth, sessions, summaries)
  │◄──────────────────────────────────────► FastAPI        ──► SQLite ◄──
  │                                              │                        │
  │  WebRTC audio (via LiveKit SFU)              │ HTTPS Twirp            │
  │◄──────────────────────────────────────►  LiveKit  ◄──► Agent Worker ──┘
                                            (Cloud SFU)    VAD → STT → LLM → TTS
                                                           (Silero/Deepgram/OpenAI)
```

| Directory | Role |
|-----------|------|
| `frontend/` | Next.js — voice UI, session management |
| `backend/api/` | FastAPI — auth, session CRUD, LiveKit token minting |
| `backend/agent/` | LiveKit Agent Worker — real-time voice pipeline, AI tutor |
| `backend/shared/` | SQLAlchemy models and config shared by API + agent |
| `e2e/` | Playwright end-to-end tests |

## Setup

### 1. Prerequisites

- Python 3.11+
- Node.js 20+
- A [LiveKit Cloud](https://cloud.livekit.io) project
- OpenAI API key
- Deepgram API key

### 2. Clone and configure

```bash
git clone <repo>
cd speak-home-project
cp .env.example .env
# Fill in all values in .env
```

### 3. Python virtual environment

Create the venv at the project root (shared by the API and the agent worker):

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e "backend[test]"
```

### 4. Database

```bash
cd backend
alembic upgrade head             # creates speakhome.db
cd ..
```

### 5. Frontend

```bash
cd frontend
npm install
cd ..
```

### 6. Run

#### Development

Three processes, each with live-reload:

```bash
# Terminal 1: FastAPI (auto-reloads on code changes)
source .venv/bin/activate
cd backend && uvicorn api.main:app --reload --port 8000

# Terminal 2: LiveKit Agent Worker (dev mode — connects to LiveKit Cloud)
source .venv/bin/activate
cd backend && python -m agent.worker dev

# Terminal 3: Next.js (auto-reloads on code changes)
cd frontend && npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

#### Production

Use Docker Compose (see [Docker Deployment](#docker-deployment) below) — it handles process management, startup ordering, migrations, and shared state automatically:

```bash
cp .env.example .env   # fill in all values
docker compose up --build -d
```

If you prefer running processes directly (e.g. on a VM without Docker):

```bash
# 1. Run database migrations once
source .venv/bin/activate
cd backend && alembic upgrade head

# 2. FastAPI — run with a multi-worker production server
#    Replace 4 with your CPU core count (2× cores is a common starting point)
source .venv/bin/activate
cd backend && uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4

# 3. LiveKit Agent Worker — 'start' (not 'dev') registers with LiveKit for production dispatch
source .venv/bin/activate
cd backend && python -m agent.worker start

# 4. Next.js — build once, then serve
cd frontend && npm run build && npm start
```

> **Note:** In production, place a reverse proxy (nginx, Caddy, or a cloud load balancer) in front of the API and frontend. Configure TLS termination there. Update `allow_origins` in `backend/api/main.py` to match your production domain.

## Environment Variables

| Variable | Description |
|---|---|
| `LIVEKIT_URL` | WebSocket URL for agent (`wss://...livekit.cloud`) |
| `LIVEKIT_API_URL` | HTTP URL for REST API (`https://...livekit.cloud`) |
| `LIVEKIT_API_KEY` | LiveKit project API key |
| `LIVEKIT_API_SECRET` | LiveKit project API secret |
| `OPENAI_API_KEY` | OpenAI API key (LLM + TTS) |
| `DEEPGRAM_API_KEY` | Deepgram API key (STT) |
| `JWT_SECRET` | Secret for signing JWTs (min 32 chars) |
| `JWT_EXPIRE_HOURS` | Token expiry in hours (default: `24`) |
| `DATABASE_URL` | SQLAlchemy DB URL (default: `sqlite+aiosqlite:///./speakhome.db`) |
| `SESSION_PAUSE_TIMEOUT_MINUTES` | Minutes to wait before ending a paused session (default: `5`) |

## Docker Deployment

All three services (FastAPI, Agent Worker, Next.js) are containerised.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with the Compose plugin (`docker compose`)
- A filled-in `.env` file (see setup step 2 above)

### Build and start

```bash
# First run — builds images and starts containers
docker compose up --build

# Subsequent runs (images already built)
docker compose up

# Detached (background)
docker compose up -d
```

Open [http://localhost:3000](http://localhost:3000).

### Services

| Service | Container port → host port | Notes |
|---------|---------------------------|-------|
| `api` | 8000 → 8000 | Runs `alembic upgrade head` on startup |
| `agent` | — | Starts after `api` is healthy |
| `frontend` | 3000 → 3000 | Starts after `api` is healthy |

### Volumes

| Volume | Purpose |
|--------|---------|
| `db_data` | SQLite database file shared between `api` and `agent` at `/data/speakhome.db` |
| `agent_cache` | Silero VAD model cache — avoids re-downloading on restart |

### Tear down

```bash
docker compose down          # stop containers, keep volumes
docker compose down -v       # stop containers and delete volumes (wipes DB)
```

### Build arguments

The frontend's `NEXT_PUBLIC_*` variables are baked into the JS bundle at build time.
They are read from your `.env` file automatically by `docker compose`.
If you need to change them after building, rebuild with:

```bash
docker compose build frontend
docker compose up -d --no-deps frontend
```

---

## Testing

```bash
source .venv/bin/activate
cd backend

# Unit tests
python -m pytest tests/unit -v

# Integration tests
python -m pytest tests/integration -v

# All backend tests with coverage
python -m pytest tests/ -v --cov=api --cov=agent --cov=shared --cov-report=term-missing

# E2E tests (requires running backend + frontend)
cd ../e2e
npm install && npx playwright install chromium
npx playwright test
```

Or use the Makefile from the project root:

```bash
make test            # unit + integration
make test-e2e        # Playwright E2E
```

---

## Thinking

### 10,000 concurrent sessions

The current architecture is designed for simplicity, not scale. Supporting 10k concurrent sessions requires addressing each layer in order — fixing a downstream bottleneck without fixing upstream ones gives no benefit.

#### 1. Database: SQLite → PostgreSQL (foundational blocker)

SQLite is a file. You cannot run multiple API or agent replicas on different machines pointing at the same file, and it serializes all writes under load. Everything else below depends on this being fixed first.

Change one line in `.env` (see [Upgrading to PostgreSQL](#upgrading-to-postgresql) below). At 10k sessions, also add **PgBouncer** in front of PostgreSQL — each API and agent replica holds its own connection pool, and without a pooler you'd exhaust Postgres's connection limit quickly.

#### 2. Agent Worker: horizontal scale-out

Each active session runs a full VAD → STT → LLM → TTS pipeline in the agent worker process, which is CPU and memory intensive. A single process cannot handle thousands of concurrent pipelines.

The good news: `python -m agent.worker start` already registers with LiveKit's job dispatch system, which load-balances across all registered workers automatically. Scaling out is just running more replicas — no code changes needed.

The real bottleneck shifts to **external API rate limits**. At 10k concurrent sessions you'd be calling Deepgram (STT) and OpenAI (LLM + TTS) simultaneously at very high throughput. This requires enterprise-tier API contracts or replacing cloud providers with self-hosted models. Silero VAD runs in-process on CPU, so at high concurrency you'd also need GPU-backed worker containers or a cloud VAD service.

#### 3. API service: multiple replicas behind a load balancer

The single `uvicorn` process becomes a bottleneck for session creation bursts (e.g. all users starting sessions at once). Run multiple API replicas behind a load balancer (nginx, AWS ALB, etc.).

Additionally, session creation currently calls LiveKit's `CreateRoom` + `CreateDispatch` synchronously inside the HTTP request. Under burst traffic this creates a latency spike. Moving LiveKit provisioning into an **async task queue** (Celery, ARQ) would decouple the API response time from LiveKit's response time.

Similarly, **summary generation** runs synchronously at session end inside the agent worker. At 10k sessions completing around the same time, this creates a thundering herd of OpenAI calls. Summaries should be enqueued as background jobs instead.

#### 4. LiveKit: capacity and clustering

LiveKit Cloud scales automatically, but 10k concurrent rooms requires a paid plan that supports the needed room count and bandwidth. If self-hosting LiveKit, a single SFU node has a ceiling — you'd need a clustered deployment with a load-balanced set of SFU nodes, which is a significant infrastructure project.

#### 5. Observability

At this scale, problems cannot be debugged manually from stdout logs. You'd need:
- **Structured logging** shipped to a log aggregator (Datadog, Loki, etc.)
- **Distributed tracing** to correlate a browser request → API → LiveKit dispatch → agent job
- **Metrics** on queue depth, session creation latency, LLM response times, and error rates

#### Summary

| Layer | Current (MVP) | At 10k sessions |
|-------|--------------|-----------------|
| Database | SQLite (single file) | PostgreSQL + PgBouncer |
| Agent Worker | 1 process | N replicas, autoscaled |
| API | 1 uvicorn process | N replicas behind a load balancer |
| Session creation | Sync HTTP to LiveKit | Async task queue |
| Summary generation | Inline sync OpenAI call | Background job queue |
| LiveKit | Cloud (any tier) | Paid plan or self-hosted cluster |
| Observability | stdout logs | Structured logging + tracing + metrics |

The database and agent worker are the two foundational changes — nothing else matters until those are addressed.


## SQLite Shortcomings

SQLite is used for the MVP to eliminate infrastructure dependencies. Be aware of the following limitations before moving to production:

| Limitation | Impact |
|---|---|
| **Single writer** | Concurrent writes serialize even in WAL mode. The API and Agent Worker both write, which can cause lock contention under load. |
| **No network sharing** | SQLite is a file. You cannot run two backend instances (on different machines or containers) pointing to the same database. This prevents horizontal scaling. |
| **No connection pooling** | Each process holds its own connection. SQLAlchemy's `NullPool` is recommended for async SQLite to avoid connection reuse issues. |
| **Manual backups** | No built-in replication or point-in-time recovery. Backup = `cp speakhome.db speakhome.db.bak`. |
| **No row-level locking** | SQLite locks at the table level for writes, not the row level. |
| **WAL mode not supported for in-memory DB** | The `sqlite+aiosqlite:///:memory:` URL used in tests cannot use WAL mode. Production file-based SQLite uses WAL correctly. |

## Upgrading to PostgreSQL

Change **one line** in `.env`:

```bash
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/speakhome
```

Then run:

```bash
cd backend && alembic upgrade head
```

No code changes required. SQLAlchemy and Alembic abstract the database entirely.
