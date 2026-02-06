#!/usr/bin/env bash
# daily-summary.sh — Generate a daily automation summary of vault changes.
# Invoked by systemd timer daily at 07:30 America/Los_Angeles.
set -euo pipefail

VAULT_DIR="${VAULT_DIR:-/srv/workspace/second-brain}"
LOCK_FILE="${LOCK_FILE:-/srv/locks/claude-exec.lock}"
TODAY="$(date +%Y-%m-%d)"
OUTPUT_FILE="${VAULT_DIR}/archive/daily/auto/daily-summary-${TODAY}.md"
TEMP_FILE="${OUTPUT_FILE}.tmp"

# Error trap: clean up temp file and notify on failure.
cleanup_on_error() {
    rm -f "$TEMP_FILE"
    happy notify "Failed: daily summary generation error for ${TODAY}"
}
trap cleanup_on_error ERR

# Idempotency check: skip if already generated today.
if [[ -f "$OUTPUT_FILE" ]]; then
    happy notify "Skipped: daily summary already exists for ${TODAY}"
    exit 0
fi

# Acquire lock (non-blocking). If an interactive session holds it, skip.
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    happy notify "Skipped: interactive session active"
    exit 0
fi

# Generate summary using Claude.
claude --continue --print \
    "Read the vault at ${VAULT_DIR} and identify what changed today (${TODAY}). \
Generate a daily summary in Markdown with these sections: \
1. What changed today \
2. Open loops / TODO \
3. Next actions for tomorrow \
4. Risks / blockers \
5. Questions for Patrick \
\
Include the following YAML frontmatter at the top of the file: \
--- \
type: daily-summary \
date: ${TODAY} \
generated_by: happy-automation \
ai_generated: true \
---" \
    > "$TEMP_FILE"

# Validate: ensure temp file exists and is non-empty.
if [[ ! -s "$TEMP_FILE" ]]; then
    happy notify "Failed: daily summary output is empty for ${TODAY}"
    rm -f "$TEMP_FILE"
    exit 1
fi

# Atomic rename.
mv "$TEMP_FILE" "$OUTPUT_FILE"

# Notify success.
happy notify "Daily summary written for ${TODAY}"
