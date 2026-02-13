#!/usr/bin/env bash
# inbox-triage.sh — Run Claude Code triage on inbox files.
# Called by inbox-watcher.sh when new files are detected.
# Respects the same lock as other automation to avoid conflicts.
set -euo pipefail

VAULT_DIR="${VAULT_DIR:-/home/ubuntu/second-brain}"
LOCK_FILE="${LOCK_FILE:-/srv/locks/claude-exec.lock}"

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

# --- Run Claude Code triage ---
cd "$VAULT_DIR"
claude --print "/triage all" || {
    echo "inbox-triage: claude triage failed"
    happy notify "Inbox triage failed" 2>/dev/null || true
    exit 1
}

echo "inbox-triage: complete"
happy notify "Inbox triage: processed $FILE_COUNT file(s)" 2>/dev/null || true
