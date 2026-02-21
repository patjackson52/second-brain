#!/usr/bin/env bash
# inbox-watcher.sh — Watch for new files in 0_inbox/ via Syncthing Event API.
# Triggers triage when files finish syncing to the inbox.
# Runs as a long-lived systemd service.
set -euo pipefail

VAULT_DIR="${VAULT_DIR:-$HOME/second-brain-vault}"
LOCK_FILE="${LOCK_FILE:-$HOME/.second-brain/locks/claude-exec.lock}"
SYNCTHING_API="${SYNCTHING_API:-http://localhost:8384}"
SYNCTHING_FOLDER="${SYNCTHING_FOLDER:-qekfe-h4e7x}"
DEBOUNCE_SECONDS="${DEBOUNCE_SECONDS:-10}"
TRIAGE_SCRIPT="${TRIAGE_SCRIPT:-$HOME/.second-brain/scripts/inbox-triage.sh}"

# --- Resolve API key from Syncthing config ---
resolve_api_key() {
    local config_paths=(
        "$HOME/.local/state/syncthing/config.xml"
        "$HOME/.config/syncthing/config.xml"
        "/etc/syncthing/config.xml"
    )
    for cfg in "${config_paths[@]}"; do
        if [[ -f "$cfg" ]]; then
            grep -oP '(?<=<apikey>).*(?=</apikey>)' "$cfg" 2>/dev/null && return 0
        fi
    done
    echo "" && return 1
}

API_KEY="${SYNCTHING_API_KEY:-$(resolve_api_key)}"
if [[ -z "$API_KEY" ]]; then
    echo "ERROR: Cannot resolve Syncthing API key. Set SYNCTHING_API_KEY or check config.xml."
    exit 1
fi

echo "inbox-watcher: started"
echo "  vault:    $VAULT_DIR"
echo "  folder:   $SYNCTHING_FOLDER"
echo "  api:      $SYNCTHING_API"
echo "  debounce: ${DEBOUNCE_SECONDS}s"

# --- Get current last event ID (start from now, don't process history) ---
LAST_ID=$(curl -sf -H "X-API-Key: $API_KEY" \
    "${SYNCTHING_API}/rest/events?limit=1" | jq -r '.[0].id // 0')
echo "  starting from event ID: $LAST_ID"

# --- Track debounce state ---
last_trigger=0
pending_files=()

trigger_triage() {
    local now
    now=$(date +%s)
    local elapsed=$((now - last_trigger))

    if [[ $elapsed -lt $DEBOUNCE_SECONDS ]]; then
        echo "  debounce: skipping (${elapsed}s < ${DEBOUNCE_SECONDS}s)"
        return
    fi

    last_trigger=$now
    local file_count=${#pending_files[@]}
    echo "  triggering triage for $file_count file(s)"

    if [[ -x "$TRIAGE_SCRIPT" ]]; then
        "$TRIAGE_SCRIPT" "${pending_files[@]}" || true
    else
        echo "  WARNING: triage script not found or not executable: $TRIAGE_SCRIPT"
    fi

    pending_files=()
}

# --- Main event loop ---
while true; do
    # Long-poll for events (blocks up to 60s if no events)
    EVENTS=$(curl -sf -H "X-API-Key: $API_KEY" \
        "${SYNCTHING_API}/rest/events?since=${LAST_ID}&timeout=60" 2>/dev/null) || {
        echo "  WARNING: API request failed, retrying in 10s..."
        sleep 10
        continue
    }

    # Skip empty responses
    EVENT_COUNT=$(echo "$EVENTS" | jq 'length')
    if [[ "$EVENT_COUNT" == "0" || "$EVENT_COUNT" == "null" ]]; then
        continue
    fi

    # Update last event ID
    NEW_LAST_ID=$(echo "$EVENTS" | jq -r '.[-1].id')
    if [[ "$NEW_LAST_ID" != "null" && -n "$NEW_LAST_ID" ]]; then
        LAST_ID="$NEW_LAST_ID"
    fi

    # Filter for completed inbox file syncs in our folder
    INBOX_FILES=$(echo "$EVENTS" | jq -r --arg folder "$SYNCTHING_FOLDER" \
        '.[] | select(.type == "ItemFinished" and .data.folder == $folder and (.data.item | startswith("0_inbox/")) and .data.action == "update") | .data.item')

    if [[ -z "$INBOX_FILES" ]]; then
        continue
    fi

    # Accumulate files and trigger
    while IFS= read -r file; do
        echo "  synced: $file"
        pending_files+=("$file")
    done <<< "$INBOX_FILES"

    trigger_triage
done
