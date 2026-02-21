#!/bin/bash
set -euo pipefail

# Tailscale Setup for Personal Second Brain VM
# This script configures private networking for the always-on Linux VM.
#
# Prerequisites:
# - Linux VM with root/sudo access
# - Internet connection for initial setup
#
# After setup:
# - VM accessible via Tailscale IP (100.x.y.z) or MagicDNS hostname
# - HappyCoder relay at http://<tailscale-ip>:3000
# - No public DNS or inbound ports required
# - Cost: $0/month (Tailscale free tier)

echo "=== Tailscale Setup for Second Brain VM ==="

# Step 1: Install Tailscale
if ! command -v tailscale &> /dev/null; then
    echo "Installing Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
else
    echo "Tailscale already installed."
fi

# Step 2: Authenticate and connect
echo "Connecting to tailnet..."
echo "You will be prompted to authenticate via a URL."
sudo tailscale up

# Step 3: Show connection info
echo ""
echo "=== Connection Info ==="
tailscale ip -4
echo "Hostname: $(tailscale status --self --json | jq -r '.Self.DNSName')"
echo ""
echo "=== Client Configuration ==="
echo "Set HappyCoder relay URL to:"
echo "  http://$(tailscale ip -4):3000"
echo ""
echo "Configure this URL on:"
echo "  - Laptop CLI: export HAPPY_RELAY_URL=http://$(tailscale ip -4):3000"
echo "  - Mobile app: Settings > Relay Server URL"
echo ""
echo "=== Verification ==="
echo "From another device on the tailnet, run:"
echo "  ping $(tailscale ip -4)"
echo "  curl http://$(tailscale ip -4):3000/health"
