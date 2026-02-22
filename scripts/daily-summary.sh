#!/usr/bin/env bash
# daily-summary.sh — Generate a daily summary using PydanticAI agent.
# Invoked by systemd timer daily at 07:30 America/Los_Angeles.
set -euo pipefail

VAULT_DIR="${VAULT_DIR:-/home/ubuntu/second-brain}"
LOCK_FILE="${LOCK_FILE:-/srv/locks/claude-exec.lock}"
TODAY="$(date +%Y-%m-%d)"
OUTPUT_FILE="${VAULT_DIR}/_system/summaries/daily/auto/daily-summary-${TODAY}.md"

# Error trap: notify on failure.
cleanup_on_error() {
    happy notify -p "Failed: daily summary generation error for ${TODAY}" 2>/dev/null || true
}
trap cleanup_on_error ERR

# Idempotency check: skip if already generated today.
if [[ -f "$OUTPUT_FILE" ]]; then
    happy notify -p "Skipped: daily summary already exists for ${TODAY}" 2>/dev/null || true
    exit 0
fi

# Acquire lock (non-blocking).
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    happy notify -p "Skipped: interactive session active" 2>/dev/null || true
    exit 0
fi

# Activate virtual environment
if [[ -f "${VAULT_DIR}/.venv/bin/activate" ]]; then
    source "${VAULT_DIR}/.venv/bin/activate"
else
    echo "daily-summary: ERROR — .venv not found at ${VAULT_DIR}/.venv"
    happy notify -p "Daily summary failed: .venv not found" 2>/dev/null || true
    exit 1
fi

# Run PydanticAI summary agent
cd "$VAULT_DIR"
python3 "${VAULT_DIR}/agents/run_summary.py" daily
RESULT=$?

case $RESULT in
    0)
        echo "daily-summary: complete"
        happy notify -p "Daily summary written for ${TODAY}" 2>/dev/null || true
        ;;
    *)
        echo "daily-summary: failed (exit code $RESULT)"
        happy notify -p "Daily summary failed for ${TODAY}" 2>/dev/null || true
        exit 1
        ;;
esac
