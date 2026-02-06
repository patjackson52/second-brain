# Update script with correct happy notify syntax
sudo tee /srv/scripts/test-summary.sh > /dev/null << 'SCRIPT'
#!/bin/bash
set -euo pipefail

export PATH="/home/ubuntu/.npm-global/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export HOME="/home/ubuntu"

VAULT_DIR="${VAULT_DIR:-$HOME/second-brain}"
NOW="$(date '+%Y-%m-%d %H:%M:%S')"
OUTPUT_FILE="${VAULT_DIR}/archive/daily/auto/test-summary-$(date +%Y%m%d-%H%M).md"
SESSION_FILE="${HOME}/.claude-automation-session"

mkdir -p "$(dirname "$OUTPUT_FILE")"

happy notify -p "🧠 Starting test summary at ${NOW}"

# First run creates session, subsequent runs resume it
if [[ -f "$SESSION_FILE" ]]; then
    SESSION_ID=$(cat "$SESSION_FILE")
    claude -p --resume "$SESSION_ID" \
        "Test periodic summary at ${NOW}. Briefly describe a daily vault summary. End with: 'Test successful at ${NOW}'" \
        > "$OUTPUT_FILE" 2>&1 || {
        happy notify -p "❌ Test summary failed"
        exit 1
    }
else
    SESSION_ID=$(uuidgen)
    echo "$SESSION_ID" > "$SESSION_FILE"
    claude -p \
        "You are Second Brain automation. Test summary at ${NOW}. End with: 'Test successful at ${NOW}'" \
        > "$OUTPUT_FILE" 2>&1 || {
        happy notify -p "❌ Test summary failed"
        exit 1
    }
fi

PREVIEW=$(head -c 100 "$OUTPUT_FILE" | tr '\n' ' ')
happy notify -p "✅ Test complete: ${PREVIEW}..."
SCRIPT

sudo chmod +x /srv/scripts/test-summary.sh
sudo systemctl daemon-reload

# Test it
/bin/bash /srv/scripts/test-summary.sh
