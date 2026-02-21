#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Second Brain — VM Deployment Script
#
# Deploys the full second-brain system onto a VM:
#   - System configuration (timezone, directories)
#   - Vault directory structure (PARA folders)
#   - Operational scripts
#   - Claude Code slash commands
#   - Systemd services and timers
#
# Usage:
#   sudo ./install.sh                    # Uses defaults
#   sudo VAULT_DIR=/path/to/vault ./install.sh  # Custom vault location
#
# This script must be run FROM the repository directory.
# Requires root/sudo privileges.
# Idempotent — safe to run multiple times.
# ==============================================================================

# --- Configurable Paths (override via environment variables) -----------------

# Detect the user who invoked sudo (for systemd services)
RUN_USER="${RUN_USER:-$(logname 2>/dev/null || echo "${SUDO_USER:-ubuntu}")}"
RUN_HOME="${RUN_HOME:-$(eval echo "~$RUN_USER")}"

# Core paths - all configurable
VAULT_DIR="${VAULT_DIR:-$RUN_HOME/second-brain-vault}"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="${DATA_DIR:-$RUN_HOME/.second-brain}"
SCRIPTS_DIR="${SCRIPTS_DIR:-$DATA_DIR/scripts}"
LOCK_DIR="${LOCK_DIR:-$DATA_DIR/locks}"
STATE_DIR="${STATE_DIR:-$DATA_DIR/state}"

# --- Pre-flight checks --------------------------------------------------------

if [[ $EUID -ne 0 ]]; then
  echo "ERROR: This script must be run as root (or with sudo)."
  exit 1
fi

echo "=============================================="
echo " Second Brain — VM Deployment"
echo "=============================================="
echo ""
echo "  Repo directory:    $REPO_DIR"
echo "  Vault directory:   $VAULT_DIR"
echo "  Data directory:    $DATA_DIR"
echo "  Scripts directory: $SCRIPTS_DIR"
echo "  Lock directory:    $LOCK_DIR"
echo "  State directory:   $STATE_DIR"
echo "  Run as user:       $RUN_USER"
echo "  User home:         $RUN_HOME"
echo ""

# ==============================================================================
# 1. System Configuration
# ==============================================================================

echo "--- [1/8] System Configuration ---"

echo "  Setting timezone to America/Los_Angeles..."
timedatectl set-timezone America/Los_Angeles

echo "  Creating directories..."
mkdir -p "$VAULT_DIR"
mkdir -p "$DATA_DIR"
mkdir -p "$SCRIPTS_DIR"
mkdir -p "$LOCK_DIR"
mkdir -p "$STATE_DIR"

# Set ownership to the run user
chown -R "$RUN_USER:$RUN_USER" "$VAULT_DIR"
chown -R "$RUN_USER:$RUN_USER" "$DATA_DIR"

# Lock directory needs to be writable
chmod 755 "$LOCK_DIR"

echo "  Done."
echo ""

# ==============================================================================
# 2. Vault Directory Structure
# ==============================================================================

echo "--- [2/8] Vault Directory Structure ---"

VAULT_DIRS=(
  "0_inbox"
  "1_projects/active"
  "1_projects/waiting"
  "1_projects/archived"
  "2_areas"
  "3_resources"
  "4_archive/projects"
  "4_archive/areas"
  "4_archive/resources"
  "4_archive/inbox"
  "5_people/family"
  "5_people/work"
  "5_people/community"
  "5_people/vendors"
  "_assets/images"
  "_assets/audio"
  "_assets/video"
  "_assets/pdf"
  "_assets/other"
  "_system/prompts"
  "_system/summaries/daily/auto"
  "_system/summaries/daily/manual"
  "_system/summaries/weekly/auto"
  "_system/summaries/weekly/manual"
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
# 3. Deploy System Templates
# ==============================================================================

echo "--- [3/8] Deploy System Templates ---"

TEMPLATES_DIR="$REPO_DIR/_system_templates"

if [[ -d "$TEMPLATES_DIR" ]]; then
  # Copy routes.yaml if not already customized
  if [[ ! -f "$VAULT_DIR/_system/routes.yaml" ]]; then
    cp "$TEMPLATES_DIR/routes.yaml" "$VAULT_DIR/_system/routes.yaml"
    echo "  Copied routes.yaml"
  else
    echo "  Skipped routes.yaml (already exists)"
  fi

  # Copy file_ops_contract.md if not already customized
  if [[ ! -f "$VAULT_DIR/_system/file_ops_contract.md" ]]; then
    cp "$TEMPLATES_DIR/file_ops_contract.md" "$VAULT_DIR/_system/file_ops_contract.md"
    echo "  Copied file_ops_contract.md"
  else
    echo "  Skipped file_ops_contract.md (already exists)"
  fi

  # Copy prompts
  if [[ -d "$TEMPLATES_DIR/prompts" ]]; then
    for prompt in "$TEMPLATES_DIR/prompts"/*.md; do
      if [[ -f "$prompt" ]]; then
        basename=$(basename "$prompt")
        if [[ ! -f "$VAULT_DIR/_system/prompts/$basename" ]]; then
          cp "$prompt" "$VAULT_DIR/_system/prompts/$basename"
          echo "  Copied prompts/$basename"
        else
          echo "  Skipped prompts/$basename (already exists)"
        fi
      fi
    done
  fi
else
  echo "  WARNING: $TEMPLATES_DIR not found, skipping template deployment."
fi

echo "  Done."
echo ""

# ==============================================================================
# 4. Deploy Scripts
# ==============================================================================

echo "--- [4/8] Deploy Scripts ---"

SCRIPTS=(
  "claude-lock.sh"
  "daily-summary.sh"
  "weekly-summary.sh"
  "inbox-watcher.sh"
  "inbox-triage.sh"
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
chown -R "$RUN_USER:$RUN_USER" "$SCRIPTS_DIR"
echo "  Set +x and ownership on all scripts in $SCRIPTS_DIR"

echo "  Done."
echo ""

# ==============================================================================
# 5. Python Environment Setup
# ==============================================================================

echo "--- [5/8] Python Environment Setup ---"

# Create virtual environment if it doesn't exist
if [[ ! -d "${DATA_DIR}/venv" ]]; then
    echo "  Creating Python virtual environment..."
    sudo -u "$RUN_USER" python3 -m venv "${DATA_DIR}/venv"
else
    echo "  Virtual environment already exists."
fi

# Upgrade pip and install/upgrade dependencies
echo "  Installing Python dependencies..."
sudo -u "$RUN_USER" "${DATA_DIR}/venv/bin/pip" install --quiet --upgrade pip
sudo -u "$RUN_USER" "${DATA_DIR}/venv/bin/pip" install --quiet -e "${REPO_DIR}"

# Initialize database schema
echo "  Initializing agents.db schema..."
sudo -u "$RUN_USER" bash -c "
  cd '$REPO_DIR'
  SECOND_BRAIN_STATE_DB='$STATE_DIR/agents.db' '${DATA_DIR}/venv/bin/python3' -c '
import sys
sys.path.insert(0, \".\")
from state.db import get_connection, init_schema
conn = get_connection()
init_schema(conn)
conn.close()
print(\"    Schema initialized successfully.\")
'
"

echo "  Done."
echo ""

# ==============================================================================
# 6. Deploy Claude Code Slash Commands
# ==============================================================================

echo "--- [6/8] Deploy Claude Code Slash Commands ---"

COMMANDS_DIR="$DATA_DIR/claude/commands"
mkdir -p "$COMMANDS_DIR"

COMMANDS=(
  "note.md"
  "triage.md"
  "search.md"
  "daily.md"
  "weekly.md"
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

chown -R "$RUN_USER:$RUN_USER" "$DATA_DIR/claude"

echo "  Done."
echo ""

# ==============================================================================
# 7. Deploy Systemd Units
# ==============================================================================

echo "--- [7/8] Deploy Systemd Units ---"

SYSTEMD_SRC="$REPO_DIR/systemd"

if [[ ! -d "$SYSTEMD_SRC" ]]; then
  echo "  WARNING: $SYSTEMD_SRC directory not found, skipping systemd deployment."
else
  # Copy all .service and .timer files, replacing placeholders
  for unit in "$SYSTEMD_SRC"/*.service "$SYSTEMD_SRC"/*.timer; do
    if [[ ! -f "$unit" ]]; then
      continue
    fi

    # Replace all placeholders
    sed -e "s|{{VAULT_DIR}}|${VAULT_DIR}|g" \
        -e "s|{{DATA_DIR}}|${DATA_DIR}|g" \
        -e "s|{{SCRIPTS_DIR}}|${SCRIPTS_DIR}|g" \
        -e "s|{{LOCK_DIR}}|${LOCK_DIR}|g" \
        -e "s|{{STATE_DIR}}|${STATE_DIR}|g" \
        -e "s|{{RUN_USER}}|${RUN_USER}|g" \
        -e "s|{{RUN_HOME}}|${RUN_HOME}|g" \
        "$unit" > "/etc/systemd/system/$(basename "$unit")"

    echo "  Deployed $(basename "$unit") -> /etc/systemd/system/"
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

  systemctl enable --now happy-inbox-watcher.service
  echo "    happy-inbox-watcher.service: enabled + started"
fi

echo "  Done."
echo ""

# ==============================================================================
# 8. Verification
# ==============================================================================

echo "--- [8/8] Verification ---"
echo ""

echo "  Timezone:"
echo "    $(timedatectl show --property=Timezone --value 2>/dev/null || timedatectl | grep 'Time zone')"
echo ""

echo "  Systemd units:"
for unit in happy-interactive.service happy-automation-daily.timer happy-automation-weekly.timer happy-inbox-watcher.service; do
  status=$(systemctl is-active "$unit" 2>/dev/null || echo "not found")
  echo "    $unit: $status"
done
echo ""

echo "  Python environment:"
if [[ -f "${DATA_DIR}/venv/bin/python3" ]]; then
  echo "    venv — OK"
  echo "    Python: $("${DATA_DIR}/venv/bin/python3" --version)"
else
  echo "    venv — MISSING"
fi
echo ""

echo "  State database:"
if [[ -f "$STATE_DIR/agents.db" ]]; then
  echo "    agents.db — OK"
else
  echo "    agents.db — MISSING"
fi
echo ""

echo "  Lock directory writable:"
if sudo -u "$RUN_USER" touch "$LOCK_DIR/.write-test" 2>/dev/null; then
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
echo "  Data:      $DATA_DIR"
echo "  Scripts:   $SCRIPTS_DIR"
echo "  Locks:     $LOCK_DIR"
echo "  State:     $STATE_DIR"
echo "  Commands:  $COMMANDS_DIR"
echo "  Run user:  $RUN_USER"
echo ""
echo "  Environment variables for scripts:"
echo "    export VAULT_DIR=\"$VAULT_DIR\""
echo "    export SECOND_BRAIN_VAULT=\"$VAULT_DIR\""
echo "    export SECOND_BRAIN_STATE_DB=\"$STATE_DIR/agents.db\""
echo ""
echo "=============================================="
echo " Deployment complete."
echo "=============================================="
