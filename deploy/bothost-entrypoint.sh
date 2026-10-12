#!/bin/bash
set -eu
: "${PORT:=3000}"
export PORT
python -m bot.main &
BOT_PID=$!
uvicorn backend.app:app --host 0.0.0.0 --port "$PORT" &
API_PID=$!
cleanup() {
  kill "$BOT_PID" "$API_PID" 2>/dev/null || true
  wait "$BOT_PID" "$API_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT
# If either process exits, stop the container so Bothost can restart it.
wait -n "$BOT_PID" "$API_PID"
exit_code=$?
cleanup
exit "$exit_code"
