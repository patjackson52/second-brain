#!/usr/bin/env bash
# weekly-summary.sh — Generate a weekly summary using PydanticAI agent.
# Invoked by systemd timer Sundays at 08:00 America/Los_Angeles.
set -euo pipefail

VAULT_DIR="${VAULT_DIR:-/home/ubuntu/second-brain-vault}"
CODE_DIR="${CODE_DIR:-/home/ubuntu/second-brain}"
LOCK_FILE="${LOCK_FILE:-/home/ubuntu/.second-brain/locks/claude-exec.lock}"
WEEK="$(date +%Y-W%V)"
OUTPUT_FILE="${VAULT_DIR}/_system/summaries/weekly/auto/weekly-summary-${WEEK}.md"

# Error trap: notify on failure.
cleanup_on_error() {
    happy notify -p "Failed: weekly summary generation for ${WEEK}" 2>/dev/null || true
}
trap cleanup_on_error ERR

# Idempotency check.
if [[ -f "$OUTPUT_FILE" ]]; then
    happy notify -p "Skipped: weekly summary already exists for ${WEEK}" 2>/dev/null || true
    exit 0
fi

# Acquire lock (non-blocking).
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    happy notify -p "Skipped: interactive session active" 2>/dev/null || true
    exit 0
fi

# Activate virtual environment
if [[ -f "${CODE_DIR}/.venv/bin/activate" ]]; then
    source "${CODE_DIR}/.venv/bin/activate"
else
    echo "weekly-summary: ERROR — .venv not found at ${CODE_DIR}/.venv"
    happy notify -p "Weekly summary failed: .venv not found" 2>/dev/null || true
    exit 1
fi

# Run PydanticAI summary agent
cd "$CODE_DIR"
python3 "${CODE_DIR}/agents/run_summary.py" weekly
RESULT=$?

case $RESULT in
    0)
        echo "weekly-summary: complete"
        happy notify -p "Weekly summary written for ${WEEK}" 2>/dev/null || true
        ;;
    *)
        echo "weekly-summary: failed (exit code $RESULT)"
        happy notify -p "Weekly summary failed for ${WEEK}" 2>/dev/null || true
        exit 1
        ;;
esac
