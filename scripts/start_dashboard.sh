#!/bin/bash
# Start the Phase 9 dashboard: FastAPI backend + Next.js frontend.
# Run from the repo root: bash scripts/start_dashboard.sh
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Starting FastAPI backend on http://localhost:8000"
cd "$ROOT"
uv run uvicorn src.oura_fun.api.app:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

echo "==> Starting Next.js frontend on http://localhost:3000"
cd "$ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

cleanup() {
  echo "Stopping..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo ""
echo "Dashboard: http://localhost:3000"
echo "API:       http://localhost:8000/docs"
echo "Press Ctrl+C to stop."
wait
