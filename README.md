# Speak Home — AI Exercise Tutor

A real-time voice AI fitness coach powered by LiveKit. Talk to Alex, your personal trainer, via voice — get exercise plans, coaching, and post-session summaries.

## Architecture

```
frontend/          Next.js (voice UI, session management)
backend/
  api/             FastAPI (auth, session CRUD, LiveKit tokens)
  agent/           LiveKit Agent Worker (voice pipeline, AI tutor)
  shared/          SQLAlchemy models, config (shared by api + agent)
e2e/               Playwright end-to-end tests
```

Both the API and the Agent Worker share the same SQLite database. They do not call each other — the DB is the contract between them.

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

### 6. Run (3 terminals)

```bash
# Terminal 1: FastAPI
source .venv/bin/activate
cd backend && uvicorn api.main:app --reload --port 8000

# Terminal 2: LiveKit Agent Worker
source .venv/bin/activate
cd backend && python -m agent.worker dev   # use 'start' in production

# Terminal 3: Frontend
cd frontend && npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

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
