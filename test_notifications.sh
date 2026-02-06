#!/usr/bin/env bash
# ==============================================================================
# Test Periodic Summary - fires every minute for testing
# Copy and paste this entire block to the VM terminal
# ==============================================================================

# Create the test script
sudo tee /srv/scripts/test-summary.sh > /dev/null << 'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail

VAULT_DIR="${VAULT_DIR:-$HOME/second-brain}"
NOW="$(date '+%Y-%m-%d %H:%M:%S')"
OUTPUT_FILE="${VAULT_DIR}/archive/daily/auto/test-summary-$(date +%Y%m%d-%H%M).md"

# Create archive directory if needed
mkdir -p "$(dirname "$OUTPUT_FILE")"

# Notify start
happy notify "🧠 Starting test summary at ${NOW}"

# Generate summary using Claude Code
# Using --resume to continue in a dedicated automation session
claude --resume "second-brain-automation" --print \
    "This is a test periodic summary triggered at ${NOW}. 
Briefly (2-3 sentences) describe what you would do for a daily vault summary. 
End with: 'Test successful at ${NOW}'" \
    > "$OUTPUT_FILE" 2>&1 || {
    happy notify "❌ Test summary failed at ${NOW}"
    exit 1
}

# Notify success with preview
PREVIEW=$(head -c 100 "$OUTPUT_FILE" | tr '\n' ' ')
happy notify "✅ Test summary complete: ${PREVIEW}..."
SCRIPT

sudo chmod +x /srv/scripts/test-summary.sh

# Create the systemd service
sudo tee /etc/systemd/system/test-summary.service > /dev/null << 'SERVICE'
[Unit]
Description=Test Summary Service (every minute)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=/home/ubuntu/second-brain
ExecStart=/srv/scripts/test-summary.sh
Environment=HOME=/home/ubuntu
Environment=VAULT_DIR=/home/ubuntu/second-brain
Environment=PATH=/usr/local/bin:/usr/bin:/bin
SERVICE

# Create the timer (fires every minute)
sudo tee /etc/systemd/system/test-summary.timer > /dev/null << 'TIMER'
[Unit]
Description=Test summary timer - every minute

[Timer]
OnCalendar=*:*:00
Persistent=true

[Install]
WantedBy=timers.target
TIMER

# Create directory structure
mkdir -p ~/second-brain/archive/daily/auto

# Reload and enable
sudo systemctl daemon-reload
sudo systemctl enable --now test-summary.timer

echo ""
echo "=============================================="
echo " Test Summary Timer Installed"
echo "=============================================="
echo ""
echo "Timer status:"
systemctl list-timers test-summary.timer
echo ""
echo "To watch notifications: check your HappyCoder relay"
echo "To view logs:          journalctl -u test-summary.service -f"
echo "To disable:            sudo systemctl disable --now test-summary.timer"
echo "To cleanup:            sudo rm /etc/systemd/system/test-summary.* /srv/scripts/test-summary.sh && sudo systemctl daemon-reload"
echo ""
