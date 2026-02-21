#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Second Brain — Client Vault + Syncthing Setup
#
# Sets up the vault directory structure and Syncthing on a client machine
# (macOS or Linux). This is the CLIENT counterpart to install.sh (server).
#
# Usage:
#   bash setup-vault.sh                              # Uses defaults
#   VAULT_DIR=/path/to/vault bash setup-vault.sh     # Custom vault location
#
# Does not require sudo on macOS. Linux needs sudo only for apt installs.
# Idempotent — safe to run multiple times.
# ==============================================================================

VAULT_DIR="${VAULT_DIR:-$HOME/second-brain-vault}"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

# Detect platform
case "$(uname -s)" in
  Darwin) PLATFORM="macos" ;;
  Linux)  PLATFORM="linux" ;;
  *)
    echo "ERROR: Unsupported platform: $(uname -s)"
    exit 1
    ;;
esac

echo "=============================================="
echo " Second Brain — Client Setup"
echo "=============================================="
echo ""
echo "  Platform:        $PLATFORM"
echo "  Vault directory: $VAULT_DIR"
echo "  Repo directory:  $REPO_DIR"
echo ""

# ==============================================================================
# 1. Create Vault Directory Structure
# ==============================================================================

echo "--- [1/5] Create Vault Directory Structure ---"

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
  if [[ ! -f "$VAULT_DIR/$dir/.gitkeep" ]]; then
    touch "$VAULT_DIR/$dir/.gitkeep"
  fi
  echo "  $VAULT_DIR/$dir/"
done

echo "  Done."
echo ""

# ==============================================================================
# 2. Deploy System Templates
# ==============================================================================

echo "--- [2/5] Deploy System Templates ---"

TEMPLATES_DIR="$REPO_DIR/_system_templates"

if [[ -d "$TEMPLATES_DIR" ]]; then
  if [[ ! -f "$VAULT_DIR/_system/routes.yaml" ]]; then
    cp "$TEMPLATES_DIR/routes.yaml" "$VAULT_DIR/_system/routes.yaml"
    echo "  Copied routes.yaml"
  else
    echo "  Skipped routes.yaml (already exists)"
  fi

  if [[ ! -f "$VAULT_DIR/_system/file_ops_contract.md" ]]; then
    cp "$TEMPLATES_DIR/file_ops_contract.md" "$VAULT_DIR/_system/file_ops_contract.md"
    echo "  Copied file_ops_contract.md"
  else
    echo "  Skipped file_ops_contract.md (already exists)"
  fi

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
  echo "  (Run this script from the repo directory to deploy templates.)"
fi

echo "  Done."
echo ""

# ==============================================================================
# 3. Install Syncthing
# ==============================================================================

echo "--- [3/5] Install Syncthing ---"

if command -v syncthing &> /dev/null; then
  echo "  Syncthing already installed: $(syncthing --version | head -1)"
else
  if [[ "$PLATFORM" == "macos" ]]; then
    if ! command -v brew &> /dev/null; then
      echo "  ERROR: Homebrew not installed. Install from https://brew.sh first."
      exit 1
    fi
    echo "  Installing via Homebrew..."
    brew install syncthing
  else
    echo "  Installing via apt..."
    sudo apt update -qq
    sudo apt install -y syncthing
  fi
  echo "  Installed: $(syncthing --version | head -1)"
fi

echo "  Done."
echo ""

# ==============================================================================
# 4. Configure Syncthing Auto-Start & Add Vault Folder
# ==============================================================================

echo "--- [4/5] Configure Syncthing ---"

# --- Start Syncthing service ---

if [[ "$PLATFORM" == "macos" ]]; then
  PLIST_DIR="$HOME/Library/LaunchAgents"
  PLIST_FILE="$PLIST_DIR/com.syncthing.syncthing.plist"

  if [[ -f "$PLIST_FILE" ]]; then
    echo "  Launch agent already exists."
  else
    mkdir -p "$PLIST_DIR"
    SYNCTHING_BIN="$(which syncthing)"
    cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.syncthing.syncthing</string>
    <key>ProgramArguments</key>
    <array>
        <string>${SYNCTHING_BIN}</string>
        <string>-no-browser</string>
        <string>-no-restart</string>
    </array>
    <key>KeepAlive</key>
    <true/>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${HOME}/Library/Logs/syncthing.log</string>
    <key>StandardErrorPath</key>
    <string>${HOME}/Library/Logs/syncthing-error.log</string>
</dict>
</plist>
EOF
    echo "  Created $PLIST_FILE"
  fi

  if launchctl list com.syncthing.syncthing &> /dev/null; then
    echo "  Syncthing already running."
  else
    launchctl load "$PLIST_FILE" 2>/dev/null || true
    echo "  Started Syncthing via launchctl."
  fi

else
  # Linux: use systemd user service
  echo "  Enabling Syncthing systemd user service..."
  systemctl --user enable --now syncthing.service
  echo "  Syncthing service enabled and started."
fi

# --- Wait for Syncthing API ---

echo "  Waiting for Syncthing API..."
API_READY=false
for i in {1..15}; do
  if curl -s http://localhost:8384/rest/system/status > /dev/null 2>&1; then
    API_READY=true
    break
  fi
  sleep 2
done

if [[ "$API_READY" != "true" ]]; then
  echo "  WARNING: Syncthing API not responding at http://localhost:8384"
  echo "  Skipping folder configuration. Configure manually via the web UI."
  echo ""
  echo "  Done (with warnings)."
  echo ""
else
  echo "  API ready."

  # --- Extract API key ---

  if [[ "$PLATFORM" == "macos" ]]; then
    SYNCTHING_CONFIG="$HOME/Library/Application Support/Syncthing/config.xml"
  else
    # Linux: check both common locations
    if [[ -f "$HOME/.local/state/syncthing/config.xml" ]]; then
      SYNCTHING_CONFIG="$HOME/.local/state/syncthing/config.xml"
    elif [[ -f "$HOME/.config/syncthing/config.xml" ]]; then
      SYNCTHING_CONFIG="$HOME/.config/syncthing/config.xml"
    else
      SYNCTHING_CONFIG=""
    fi
  fi

  if [[ -z "$SYNCTHING_CONFIG" || ! -f "$SYNCTHING_CONFIG" ]]; then
    echo "  WARNING: Syncthing config file not found."
    echo "  Configure the vault folder manually via http://localhost:8384"
  else
    API_KEY=$(sed -n 's/.*<apikey>\(.*\)<\/apikey>.*/\1/p' "$SYNCTHING_CONFIG")

    if [[ -z "$API_KEY" ]]; then
      echo "  WARNING: Could not extract API key from config."
      echo "  Configure the vault folder manually via http://localhost:8384"
    else
      # --- Add vault folder if not already configured ---

      FOLDER_EXISTS=$(curl -s -H "X-API-Key: $API_KEY" \
        http://localhost:8384/rest/config/folders | \
        python3 -c "import sys,json; folders=json.load(sys.stdin); print('yes' if any(f['id']=='second-brain' for f in folders) else 'no')" 2>/dev/null || echo "no")

      if [[ "$FOLDER_EXISTS" == "yes" ]]; then
        echo "  Vault folder already configured in Syncthing (id: second-brain)."
      else
        curl -s -X POST -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
          http://localhost:8384/rest/config/folders \
          -d "{
            \"id\": \"second-brain\",
            \"label\": \"Second Brain\",
            \"path\": \"$VAULT_DIR\",
            \"type\": \"sendreceive\",
            \"rescanIntervalS\": 60,
            \"fsWatcherEnabled\": true,
            \"fsWatcherDelayS\": 10
          }" > /dev/null
        echo "  Added vault folder to Syncthing:"
        echo "    Folder ID: second-brain"
        echo "    Path:      $VAULT_DIR"
        echo "    Type:      Send & Receive"
      fi
    fi
  fi

  echo "  Done."
  echo ""
fi

# ==============================================================================
# 5. Display Pairing Info
# ==============================================================================

echo "--- [5/5] Pairing Info ---"

# Try to get device ID if API is available
DEVICE_ID=""
if [[ "${API_READY:-false}" == "true" && -n "${API_KEY:-}" ]]; then
  DEVICE_ID=$(curl -s -H "X-API-Key: $API_KEY" \
    http://localhost:8384/rest/system/status | \
    python3 -c "import sys,json; print(json.load(sys.stdin)['myID'])" 2>/dev/null || true)
fi

echo ""
echo "=============================================="
echo "  SETUP COMPLETE"
echo "=============================================="
echo ""
echo "  Syncthing UI: http://localhost:8384"
echo "  Vault path:   $VAULT_DIR"
echo "  Folder ID:    second-brain"
echo ""

if [[ -n "$DEVICE_ID" ]]; then
  echo "  This device's ID:"
  echo "  $DEVICE_ID"
  echo ""
fi

echo "=============================================="
echo ""
echo "NEXT STEPS — Pair with the server VM:"
echo ""
echo "  1. On the VM, open Syncthing UI (via SSH tunnel):"
echo "     ssh -L 8385:localhost:8384 ubuntu@<TAILSCALE_IP>"
echo "     Then open http://localhost:8385"
echo ""
echo "  2. On the VM's Syncthing UI:"
echo "     - Add Remote Device -> paste this device's ID above"
echo "     - Share the 'second-brain' folder with the new device"
echo ""
echo "  3. On this device's Syncthing UI (http://localhost:8384):"
echo "     - Accept the VM's device connection request"
echo "     - Accept the shared folder (confirm path is $VAULT_DIR)"
echo ""
echo "  4. Verify sync:"
echo "     Create a test file on one device, confirm it appears on the other."
echo ""
