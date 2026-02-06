#!/usr/bin/env bash
set -euo pipefail

# Execution lock mechanism for Personal Second Brain automation.
# Uses flock-based concurrency control to prevent simultaneous
# interactive and automated Claude sessions.

LOCK_FILE="${CLAUDE_LOCK_FILE:-/srv/locks/claude-exec.lock}"
LOCK_DIR="$(dirname "$LOCK_FILE")"

usage() {
    echo "Usage: $0 --blocking|--non-blocking <command> [args...]"
    echo ""
    echo "Options:"
    echo "  --blocking      Block until lock is available, then run command"
    echo "  --non-blocking  Attempt lock without blocking; skip if held"
    echo ""
    echo "Environment:"
    echo "  CLAUDE_LOCK_FILE  Path to lock file (default: /srv/locks/claude-exec.lock)"
    exit 1
}

if [[ $# -lt 2 ]]; then
    usage
fi

MODE="$1"
shift

if [[ "$MODE" != "--blocking" && "$MODE" != "--non-blocking" ]]; then
    echo "Error: first argument must be --blocking or --non-blocking" >&2
    usage
fi

# Ensure lock directory exists
mkdir -p "$LOCK_DIR"

# Open lock file descriptor
exec 9>"$LOCK_FILE"

if [[ "$MODE" == "--non-blocking" ]]; then
    if ! flock -n 9; then
        echo "Skipped: interactive session active"
        happy notify "Skipped: interactive session active"
        exit 0
    fi
    # Lock acquired, run the command
    "$@"
else
    # Blocking mode: wait for lock
    flock 9
    "$@"
fi
