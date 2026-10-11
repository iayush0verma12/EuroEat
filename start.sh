#!/usr/bin/env bash
# Starts the EuroEat backend (FastAPI :8000) and frontend (Vite :5173) on macOS / Linux.
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

if [ ! -d "$ROOT/backend/.venv" ]; then
  python3 -m venv "$ROOT/backend/.venv"
  "$ROOT/backend/.venv/bin/pip" install -r "$ROOT/backend/requirements.txt"
  "$ROOT/backend/.venv/bin/python" -m playwright install chromium
fi
[ -d "$ROOT/frontend/node_modules" ] || (cd "$ROOT/frontend" && npm install)

ollama pull llama3.2 && ollama pull nomic-embed-text

(cd "$ROOT/backend" && .venv/bin/python -m uvicorn app.main:app --port 8000) &
(cd "$ROOT/frontend" && npm run dev) &
echo "EuroEat: http://localhost:5173  (login: traveller / EuroEat@2026)"
wait
