#!/bin/bash
set -u

: "${PORT:=3000}"
export PORT

echo "[startup] Bothost entrypoint started at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "[startup] PORT=${PORT}"
echo "[startup] Starting Telegram bot..."
python -u -m bot.main &
BOT_PID=$!
echo "[startup] Telegram bot process PID=${BOT_PID}"

echo "[startup] Starting FastAPI on 0.0.0.0:${PORT}..."
python -u -m uvicorn backend.app:app --host 0.0.0.0 --port "$PORT" &
API_PID=$!
echo "[startup] API process PID=${API_PID}"

cleanup() {
  echo "[startup] Stopping child processes..."
  kill "$BOT_PID" "$API_PID" 2>/dev/null || true
  wait "$BOT_PID" "$API_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

# Do not use `set -e` here: wait -n returns non-zero if either service crashes,
# and set -e would terminate the script before we can report the exit status.
wait -n "$BOT_PID" "$API_PID"
EXIT_CODE=$?
echo "[startup] A service exited; wait status=${EXIT_CODE}. Check the traceback above."
exit "$EXIT_CODE"
