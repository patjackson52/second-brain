#!/usr/bin/env bash
# inbox-triage.sh — Run PydanticAI triage agent on inbox files.
# Called by inbox-watcher.sh when new files are detected.
# Respects the same lock as other automation to avoid conflicts.
set -euo pipefail

VAULT_DIR="${VAULT_DIR:-$HOME/second-brain-vault}"
LOCK_FILE="${LOCK_FILE:-$HOME/.second-brain/locks/claude-exec.lock}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# --- Acquire lock (non-blocking). If interactive or other automation holds it, skip. ---
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    echo "inbox-triage: skipped (lock held by another session)"
    happy notify "Inbox triage skipped: session active" 2>/dev/null || true
    exit 0
fi

# --- Check inbox for actual files ---
INBOX="$VAULT_DIR/0_inbox"
FILES=$(find "$INBOX" -maxdepth 1 -type f -name '*.md' ! -name '.gitkeep' 2>/dev/null)

if [[ -z "$FILES" ]]; then
    echo "inbox-triage: no files to process"
    exit 0
fi

FILE_COUNT=$(echo "$FILES" | wc -l)
echo "inbox-triage: processing $FILE_COUNT file(s)"

# --- Run PydanticAI triage agent ---
cd "$VAULT_DIR"

# Activate virtual environment
DATA_DIR="${DATA_DIR:-$HOME/.second-brain}"
if [[ -f "${DATA_DIR}/venv/bin/activate" ]]; then
    source "${DATA_DIR}/venv/bin/activate"
else
    echo "inbox-triage: ERROR — venv not found at ${DATA_DIR}/venv"
    happy notify "Inbox triage failed: venv not found" 2>/dev/null || true
    exit 1
fi

# Run the Python triage agent
python3 -m agents.run_triage --all
RESULT=$?

case $RESULT in
    0)
        echo "inbox-triage: complete"
        happy notify "Inbox triage: processed $FILE_COUNT file(s)" 2>/dev/null || true
        ;;
    2)
        echo "inbox-triage: complete (some items need review)"
        happy notify "Inbox triage: $FILE_COUNT file(s) processed, some need review" 2>/dev/null || true
        ;;
    *)
        echo "inbox-triage: failed (exit code $RESULT)"
        happy notify "Inbox triage failed" 2>/dev/null || true
        exit 1
        ;;
esac
