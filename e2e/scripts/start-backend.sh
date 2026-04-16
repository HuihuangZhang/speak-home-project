#!/usr/bin/env bash
# Start API for Playwright. Prefers backend/.venv; falls back to `uv run`.
set -euo pipefail
BACKEND_DIR="$(cd "$(dirname "$0")/../../backend" && pwd)"
cd "$BACKEND_DIR"
PORT="${PORT:-8000}"
if [[ -x .venv/bin/uvicorn ]]; then
  exec .venv/bin/uvicorn api.main:app --host 127.0.0.1 --port "$PORT"
fi
if command -v uv >/dev/null 2>&1; then
  exec uv run uvicorn api.main:app --host 127.0.0.1 --port "$PORT"
fi
echo "e2e: install backend deps: cd backend && uv sync && uv run uvicorn ..." >&2
echo "   or: cd backend && python3 -m venv .venv && .venv/bin/pip install -e . && .venv/bin/pip install uvicorn" >&2
exit 127
