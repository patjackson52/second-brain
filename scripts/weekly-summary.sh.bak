#!/usr/bin/env bash
set -euo pipefail

# --- Configuration ---
VAULT_DIR="${VAULT_DIR:-$HOME/second-brain-vault}"
LOCK_FILE="${LOCK_FILE:-$HOME/.second-brain/locks/claude-exec.lock}"
WEEK="$(date +%Y-W%V)"
OUTPUT_FILE="${VAULT_DIR}/_system/summaries/weekly/auto/weekly-summary-${WEEK}.md"
TEMP_FILE="${OUTPUT_FILE}.tmp"

# --- Error trap: clean up temp file and notify on failure ---
cleanup_on_error() {
    rm -f "$TEMP_FILE"
    happy notify -p "Failed: weekly summary generation for ${WEEK}"
}
trap cleanup_on_error ERR

# --- Idempotency check ---
if [[ -f "$OUTPUT_FILE" ]]; then
    happy notify -p "Skipped: weekly summary already exists for ${WEEK}"
    exit 0
fi

# --- Acquire lock (non-blocking) ---
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    happy notify -p "Skipped: interactive session active"
    exit 0
fi

# --- Ensure output directory exists ---
mkdir -p "$(dirname "$OUTPUT_FILE")"

# --- Generate summary using Claude ---
claude --continue --print \
    "Read the vault at ${VAULT_DIR} and review the past week's changes. \
Look at daily summaries from the past week (in _system/summaries/daily/auto/) for context. \
Generate a weekly summary in markdown with the following frontmatter and sections:

---
type: weekly-summary
week: ${WEEK}
generated_by: happy-automation
ai_generated: true
---

## Highlights

## Progress by theme

## Open loops / TODO

## Next actions

## Questions for Patrick

Fill in each section based on what happened this week. Be concise but thorough." \
    > "$TEMP_FILE"

# --- Validate output ---
if [[ ! -s "$TEMP_FILE" ]]; then
    happy notify -p "Failed: weekly summary generation produced empty output for ${WEEK}"
    rm -f "$TEMP_FILE"
    exit 1
fi

# --- Atomic rename ---
mv "$TEMP_FILE" "$OUTPUT_FILE"

# --- Notify success ---
happy notify -p "Weekly summary written for ${WEEK}"
