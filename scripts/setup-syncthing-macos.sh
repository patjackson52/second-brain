#!/bin/bash
set -euo pipefail

# Syncthing Setup for macOS (Personal Second Brain)
# This script installs and configures Syncthing to sync the vault with the VM.

VAULT_DIR="${VAULT_DIR:-/Users/patrick/workspace/second-brain}"

echo "=== Syncthing Setup for macOS ==="
echo "Vault directory: $VAULT_DIR"
echo ""

# Step 1: Install Syncthing via Homebrew
echo "[1/5] Installing Syncthing..."
if command -v syncthing &> /dev/null; then
    echo "  Syncthing already installed: $(syncthing --version | head -1)"
else
    if ! command -v brew &> /dev/null; then
        echo "  ERROR: Homebrew not installed. Install from https://brew.sh first."
        exit 1
    fi
    brew install syncthing
    echo "  Installed: $(syncthing --version | head -1)"
fi

# Step 2: Set up launch agent (auto-start on login)
echo ""
echo "[2/5] Configuring launch agent..."
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_FILE="$PLIST_DIR/com.syncthing.syncthing.plist"

if [ -f "$PLIST_FILE" ]; then
    echo "  Launch agent already exists."
else
    mkdir -p "$PLIST_DIR"
    cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.syncthing.syncthing</string>
    <key>ProgramArguments</key>
    <array>
        <string>$(which syncthing)</string>
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

# Step 3: Start Syncthing
echo ""
echo "[3/5] Starting Syncthing..."
if launchctl list | grep -q com.syncthing.syncthing; then
    echo "  Already running."
else
    launchctl load "$PLIST_FILE"
    echo "  Started. Waiting for API..."
    sleep 3
fi

# Wait for Syncthing API to be ready
for i in {1..10}; do
    if curl -s http://localhost:8384/rest/system/status > /dev/null 2>&1; then
        break
    fi
    sleep 2
done

# Step 4: Get API key and configure vault folder
echo ""
echo "[4/5] Configuring vault folder..."

SYNCTHING_CONFIG="$HOME/Library/Application Support/Syncthing/config.xml"

# Wait for config file to be generated (up to 30s)
for i in {1..15}; do
    if [ -f "$SYNCTHING_CONFIG" ]; then
        break
    fi
    echo "  Waiting for Syncthing to generate config... (${i}s)"
    sleep 2
done

if [ ! -f "$SYNCTHING_CONFIG" ]; then
    echo "  ERROR: Config file not found at: $SYNCTHING_CONFIG"
    echo "  Open http://localhost:8384 in your browser to configure manually."
    exit 1
fi

# Extract API key from config (macOS-compatible sed)
API_KEY=$(sed -n 's/.*<apikey>\(.*\)<\/apikey>.*/\1/p' "$SYNCTHING_CONFIG")

if [ -z "$API_KEY" ]; then
    echo "  ERROR: Could not extract API key from config."
    echo "  Open http://localhost:8384 in your browser to configure manually."
    exit 1
fi

# Check if vault folder already configured
FOLDER_EXISTS=$(curl -s -H "X-API-Key: $API_KEY" \
    http://localhost:8384/rest/config/folders | \
    python3 -c "import sys,json; folders=json.load(sys.stdin); print('yes' if any(f['path']=='$VAULT_DIR' for f in folders) else 'no')" 2>/dev/null || echo "no")

if [ "$FOLDER_EXISTS" = "yes" ]; then
    echo "  Vault folder already configured in Syncthing."
else
    # Add the vault folder
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
    echo "  Added vault folder: $VAULT_DIR"
    echo "  Folder ID: second-brain"
    echo "  Type: Send & Receive"
    echo "  Rescan interval: 60s"
fi

# Step 5: Show device ID for pairing
echo ""
echo "[5/5] Device info for pairing..."
DEVICE_ID=$(curl -s -H "X-API-Key: $API_KEY" \
    http://localhost:8384/rest/system/status | \
    python3 -c "import sys,json; print(json.load(sys.stdin)['myID'])")

echo ""
echo "=========================================="
echo "  SETUP COMPLETE"
echo "=========================================="
echo ""
echo "  Syncthing UI: http://localhost:8384"
echo "  Vault path:   $VAULT_DIR"
echo "  Folder ID:    second-brain"
echo ""
echo "  This device's ID:"
echo "  $DEVICE_ID"
echo ""
echo "=========================================="
echo ""
echo "NEXT STEPS:"
echo ""
echo "  1. On the VM, open Syncthing UI (via SSH tunnel):"
echo "     ssh -L 8385:localhost:8384 ubuntu@<TAILSCALE_IP>"
echo "     Then open http://localhost:8385"
echo ""
echo "  2. On the VM's Syncthing UI:"
echo "     - Add Remote Device → paste this laptop's Device ID above"
echo "     - Share the 'second-brain' folder with the new device"
echo ""
echo "  3. On this laptop's Syncthing UI (http://localhost:8384):"
echo "     - Accept the VM's device connection request"
echo "     - Accept the shared folder (confirm path is $VAULT_DIR)"
echo ""
echo "  4. Verify sync:"
echo "     Create a test file on one device, confirm it appears on the other."
echo ""
