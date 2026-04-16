#!/usr/bin/env bash
# Start API for Playwright.
# Preference order:
# 1) backend/.venv
# 2) project-root .venv (common local setup)
# 3) uv run (last resort; may resolve heavyweight deps)
set -euo pipefail
BACKEND_DIR="$(cd "$(dirname "$0")/../../backend" && pwd)"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$BACKEND_DIR"
PORT="${PORT:-8000}"

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PY_BIN="$ROOT_DIR/.venv/bin/python"
elif [[ -x .venv/bin/python ]]; then
  PY_BIN=".venv/bin/python"
else
  PY_BIN=""
fi

# Keep e2e deterministic: reset dedicated test DB each run by default.
if [[ "${E2E_RESET_DB:-true}" == "true" ]] && [[ "${DATABASE_URL:-}" == sqlite+aiosqlite:///* ]]; then
  DB_PATH="${DATABASE_URL#sqlite+aiosqlite:///}"
  if [[ "$DB_PATH" = /* ]]; then
    DB_FILE="$DB_PATH"
  else
    DB_FILE="$BACKEND_DIR/$DB_PATH"
  fi
  rm -f "$DB_FILE" "$DB_FILE-shm" "$DB_FILE-wal"
fi

# Ensure schema is up to date before starting API.
if [[ -n "$PY_BIN" ]]; then
  ALEMBIC_BIN="$(dirname "$PY_BIN")/alembic"
  if [[ ! -x "$ALEMBIC_BIN" ]]; then
    echo "e2e: missing alembic in venv next to $PY_BIN" >&2
    exit 127
  fi
  "$ALEMBIC_BIN" upgrade head
  exec "$PY_BIN" -m uvicorn api.main:app --host 127.0.0.1 --port "$PORT"
fi

if command -v uv >/dev/null 2>&1; then
  if [[ "${E2E_RESET_DB:-true}" == "true" ]] && [[ "${DATABASE_URL:-}" == sqlite+aiosqlite:///* ]]; then
    DB_PATH="${DATABASE_URL#sqlite+aiosqlite:///}"
    if [[ "$DB_PATH" = /* ]]; then
      DB_FILE="$DB_PATH"
    else
      DB_FILE="$BACKEND_DIR/$DB_PATH"
    fi
    rm -f "$DB_FILE" "$DB_FILE-shm" "$DB_FILE-wal"
  fi
  uv run alembic upgrade head
  exec uv run uvicorn api.main:app --host 127.0.0.1 --port "$PORT"
fi

echo "e2e: install backend deps: cd backend && uv sync && uv run uvicorn ..." >&2
echo "   or: cd backend && python3 -m venv .venv && .venv/bin/pip install -e . && .venv/bin/pip install uvicorn" >&2
exit 127
