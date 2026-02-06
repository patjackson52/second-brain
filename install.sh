#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Second Brain — VM Deployment Script
#
# Deploys the full second-brain system onto a VM:
#   - System configuration (timezone, directories)
#   - Vault directory structure
#   - Operational scripts
#   - Claude Code slash commands
#   - Systemd services and timers
#
# This script must be run FROM the repository directory.
# Requires root/sudo privileges.
# Idempotent — safe to run multiple times.
# ==============================================================================

VAULT_DIR="${VAULT_DIR:-/srv/workspace/second-brain}"
LOCK_DIR="/srv/locks"
SCRIPTS_DIR="/srv/scripts"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

# --- Pre-flight checks --------------------------------------------------------

if [[ $EUID -ne 0 ]]; then
  echo "ERROR: This script must be run as root (or with sudo)."
  exit 1
fi

echo "=============================================="
echo " Second Brain — VM Deployment"
echo "=============================================="
echo ""
echo "  Repo directory:  $REPO_DIR"
echo "  Vault directory: $VAULT_DIR"
echo ""

# ==============================================================================
# 1. System Configuration
# ==============================================================================

echo "--- [1/6] System Configuration ---"

echo "  Setting timezone to America/Los_Angeles..."
timedatectl set-timezone America/Los_Angeles

echo "  Creating vault directory: $VAULT_DIR"
mkdir -p "$VAULT_DIR"

echo "  Creating lock directory: $LOCK_DIR"
mkdir -p "$LOCK_DIR"

echo "  Creating scripts directory: $SCRIPTS_DIR"
mkdir -p "$SCRIPTS_DIR"

echo "  Done."
echo ""

# ==============================================================================
# 2. Vault Directory Structure
# ==============================================================================

echo "--- [2/6] Vault Directory Structure ---"

VAULT_DIRS=(
  "inbox"
  "ideas"
  "projects"
  "people"
  "admin"
  "archive/daily/auto"
  "archive/daily/manual"
  "archive/weekly/auto"
  "archive/weekly/manual"
)

for dir in "${VAULT_DIRS[@]}"; do
  mkdir -p "$VAULT_DIR/$dir"
  # Place .gitkeep in leaf directories to preserve structure in git
  if [[ ! -f "$VAULT_DIR/$dir/.gitkeep" ]]; then
    touch "$VAULT_DIR/$dir/.gitkeep"
  fi
  echo "  $VAULT_DIR/$dir/"
done

echo "  Done."
echo ""

# ==============================================================================
# 3. Deploy Scripts
# ==============================================================================

echo "--- [3/6] Deploy Scripts ---"

SCRIPTS=(
  "claude-lock.sh"
  "daily-summary.sh"
  "weekly-summary.sh"
  "setup-tailscale.sh"
)

for script in "${SCRIPTS[@]}"; do
  src="$REPO_DIR/scripts/$script"
  if [[ ! -f "$src" ]]; then
    echo "  WARNING: $src not found, skipping."
    continue
  fi
  cp "$src" "$SCRIPTS_DIR/$script"
  echo "  Copied scripts/$script -> $SCRIPTS_DIR/$script"
done

chmod +x "$SCRIPTS_DIR"/*.sh 2>/dev/null || true
echo "  Set +x on all scripts in $SCRIPTS_DIR"

echo "  Done."
echo ""

# ==============================================================================
# 4. Deploy Claude Code Slash Commands
# ==============================================================================

echo "--- [4/6] Deploy Claude Code Slash Commands ---"

COMMANDS_DIR="$VAULT_DIR/.claude/commands"
mkdir -p "$COMMANDS_DIR"

COMMANDS=(
  "note.md"
  "triage.md"
  "search.md"
)

for cmd in "${COMMANDS[@]}"; do
  src="$REPO_DIR/.claude/commands/$cmd"
  if [[ ! -f "$src" ]]; then
    echo "  WARNING: $src not found, skipping."
    continue
  fi
  cp "$src" "$COMMANDS_DIR/$cmd"
  echo "  Copied .claude/commands/$cmd -> $COMMANDS_DIR/$cmd"
done

echo "  Done."
echo ""

# ==============================================================================
# 5. Deploy Systemd Units
# ==============================================================================

echo "--- [5/6] Deploy Systemd Units ---"

SYSTEMD_SRC="$REPO_DIR/systemd"

if [[ ! -d "$SYSTEMD_SRC" ]]; then
  echo "  WARNING: $SYSTEMD_SRC directory not found, skipping systemd deployment."
else
  # Copy all .service and .timer files
  for unit in "$SYSTEMD_SRC"/*.service "$SYSTEMD_SRC"/*.timer; do
    if [[ ! -f "$unit" ]]; then
      continue
    fi
    cp "$unit" /etc/systemd/system/
    echo "  Copied $(basename "$unit") -> /etc/systemd/system/"
  done

  echo "  Reloading systemd daemon..."
  systemctl daemon-reload

  echo "  Enabling and starting services/timers..."
  systemctl enable --now happy-interactive.service
  echo "    happy-interactive.service: enabled + started"

  systemctl enable --now happy-automation-daily.timer
  echo "    happy-automation-daily.timer: enabled + started"

  systemctl enable --now happy-automation-weekly.timer
  echo "    happy-automation-weekly.timer: enabled + started"
fi

echo "  Done."
echo ""

# ==============================================================================
# 6. Verification
# ==============================================================================

echo "--- [6/6] Verification ---"
echo ""

echo "  Timezone:"
echo "    $(timedatectl show --property=Timezone --value 2>/dev/null || timedatectl | grep 'Time zone')"
echo ""

echo "  Systemd units:"
for unit in happy-interactive.service happy-automation-daily.timer happy-automation-weekly.timer; do
  status=$(systemctl is-active "$unit" 2>/dev/null || echo "not found")
  echo "    $unit: $status"
done
echo ""

echo "  Lock directory writable:"
if touch "$LOCK_DIR/.write-test" 2>/dev/null; then
  rm -f "$LOCK_DIR/.write-test"
  echo "    $LOCK_DIR — OK"
else
  echo "    $LOCK_DIR — FAILED (not writable)"
fi
echo ""

echo "=============================================="
echo " Deployment Summary"
echo "=============================================="
echo ""
echo "  Vault:     $VAULT_DIR"
echo "  Scripts:   $SCRIPTS_DIR"
echo "  Locks:     $LOCK_DIR"
echo "  Commands:  $COMMANDS_DIR"
echo ""
echo "  Directories created:"
for dir in "${VAULT_DIRS[@]}"; do
  echo "    $VAULT_DIR/$dir/"
done
echo ""
echo "  Scripts deployed:"
for script in "${SCRIPTS[@]}"; do
  if [[ -f "$SCRIPTS_DIR/$script" ]]; then
    echo "    $SCRIPTS_DIR/$script"
  fi
done
echo ""
echo "  Slash commands deployed:"
for cmd in "${COMMANDS[@]}"; do
  if [[ -f "$COMMANDS_DIR/$cmd" ]]; then
    echo "    $COMMANDS_DIR/$cmd"
  fi
done
echo ""
echo "  Systemd units: happy-interactive.service"
echo "                  happy-automation-daily.timer"
echo "                  happy-automation-weekly.timer"
echo ""
echo "=============================================="
echo " Deployment complete."
echo "=============================================="
