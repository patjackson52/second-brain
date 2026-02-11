# Oracle Cloud VM Setup for Personal Second Brain

You are helping the user create and configure an Oracle Cloud Infrastructure (OCI) free-tier VM to host their Personal Second Brain automation system. Walk through each step interactively, prompting for information as needed. Do NOT proceed to the next step until the current one is confirmed complete.

## Context

The user needs an always-on Linux VM that will run:
- HappyCoder relay (persistent Claude Code session accessible from mobile)
- Scheduled automation (daily/weekly summaries via systemd timers)
- Syncthing (file sync with laptop and mobile)
- Tailscale (private networking, no public ports)

The VM will host the vault at `/srv/workspace/second-brain/` and run automation scripts that generate daily (07:30 Pacific) and weekly (Sunday 08:00 Pacific) summaries.

## Requirements

- **Free tier eligible** (no recurring cost)
- **Always-on** (not ephemeral/preemptible)
- **ARM-based preferred** (Ampere A1 — 4 OCPU, 24GB RAM free tier) or AMD micro (1 OCPU, 1GB RAM free tier)
- **OS:** Ubuntu 22.04 or 24.04 (minimal/server)
- **Storage:** 50GB boot volume (free tier allows up to 200GB total)
- **Network:** No public ingress needed (Tailscale handles connectivity)

---

## Step 1: Oracle Cloud Account

Ask the user:
1. "Do you already have an Oracle Cloud account? (yes/no)"
   - If NO: Walk them through signup at https://cloud.oracle.com/
     - They'll need: email, name, phone, credit/debit card (for verification only, won't be charged on free tier)
     - Ask: "What home region do you want? (Recommend: us-phoenix-1 or us-ashburn-1 for US West/East)"
     - Wait for them to confirm account is created and they can log into the console
   - If YES: Ask them to confirm they can access the OCI console and which region they're in

## Step 2: Generate SSH Key

Ask the user:
1. "Do you already have an SSH key pair you want to use for this VM? (yes/no)"
   - If NO: Guide them to generate one:
     ```bash
     ssh-keygen -t ed25519 -f ~/.ssh/oracle-second-brain -C "second-brain-vm"
     ```
     Then: `cat ~/.ssh/oracle-second-brain.pub` — they'll need this for VM creation
   - If YES: Ask them to confirm the path to their public key file

## Step 3: Create the VM Instance

Guide the user through the OCI Console (https://cloud.oracle.com/ → Compute → Instances → Create Instance):

1. **Name:** `second-brain-vm`
2. **Compartment:** root compartment (default)
3. **Availability Domain:** Any available
4. **Image:** Ubuntu 22.04 or 24.04 (Canonical)
5. **Shape:**
   - Preferred: `VM.Standard.A1.Flex` (Ampere ARM) — set to 1 OCPU, 6GB RAM (well within free tier of 4 OCPU / 24GB)
   - Fallback: `VM.Standard.E2.1.Micro` (AMD, always-free, 1 OCPU / 1GB RAM)
6. **Networking:**
   - Create new VCN or use existing
   - Public IP: YES (needed for initial SSH access; Tailscale will be the long-term access method)
   - Subnet: public subnet (default)
7. **SSH Key:** Paste the public key from Step 2
8. **Boot Volume:** 50GB (default is fine)

Ask the user to confirm:
- "Have you clicked 'Create' and is the instance provisioning?"
- "What is the public IP address shown once it's running?"

## Step 4: First SSH Connection

Guide the user to connect:
```bash
ssh -i ~/.ssh/oracle-second-brain ubuntu@<PUBLIC_IP>
```

Ask: "Are you connected to the VM via SSH?"

If connection fails, troubleshoot:
- Check security list allows port 22 inbound (OCI default VCN usually allows this)
- Check the correct username (`ubuntu` for Ubuntu images, `opc` for Oracle Linux)

## Step 5: Base System Setup

Once connected, guide them to run these commands on the VM:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Set timezone
sudo timedatectl set-timezone America/Los_Angeles

# Install essentials
sudo apt install -y curl jq unzip flock

# Create directory structure
sudo mkdir -p /srv/workspace/second-brain
sudo mkdir -p /srv/scripts
sudo mkdir -p /srv/locks
sudo chown -R ubuntu:ubuntu /srv/workspace /srv/scripts /srv/locks
```

Ask: "Confirm these commands completed successfully?"

## Step 6: Install Tailscale

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

This will print an auth URL. Ask the user:
- "Open the URL it shows and authenticate with your Tailscale account"
- "What Tailscale IP was assigned? (run: tailscale ip -4)"

Note: Once Tailscale is up, they can SSH via the Tailscale IP instead of the public IP.

## Step 7: Install Syncthing

```bash
# Add Syncthing repo
sudo mkdir -p /etc/apt/keyrings
sudo curl -L -o /etc/apt/keyrings/syncthing-archive-keyring.gpg https://syncthing.net/release-key.gpg
echo "deb [signed-by=/etc/apt/keyrings/syncthing-archive-keyring.gpg] https://apt.syncthing.net/ syncthing stable" | sudo tee /etc/apt/sources.list.d/syncthing.list
sudo apt update
sudo apt install -y syncthing

# Enable as user service
systemctl --user enable --now syncthing
```

Ask: "Is Syncthing running? Check with: systemctl --user status syncthing"

Guide them to configure Syncthing to sync `/srv/workspace/second-brain/` with their laptop:
- Access Syncthing UI via SSH tunnel: `ssh -L 8384:localhost:8384 ubuntu@<TAILSCALE_IP>`
- Open http://localhost:8384 in browser
- Add the folder `/srv/workspace/second-brain/`
- Add their laptop as a device (exchange device IDs)

## Step 8: Install Claude Code

Ask the user: "How do you want to install Claude Code on the VM?"

Guide them through:
```bash
# Install Node.js (if needed)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo bash -
sudo apt install -y nodejs

# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Authenticate
claude auth
```

Ask: "Is Claude Code authenticated? (run: claude --version to verify install)"

## Step 9: Install HappyCoder

Ask the user: "Do you have HappyCoder CLI installation instructions? Provide them or paste the install command."

Guide through installation and pairing:
- Install the CLI
- Configure relay to run on the VM
- Pair with mobile device

Ask: "Is HappyCoder running and paired with your phone?"

## Step 10: Deploy the Second Brain System

Guide the user to transfer and run the install script from their laptop:

```bash
# From laptop (in the second-brain repo directory):
tar czf /tmp/second-brain-deploy.tar.gz install.sh scripts/ systemd/ .claude/commands/
scp /tmp/second-brain-deploy.tar.gz ubuntu@<TAILSCALE_IP>:/tmp/

# On the VM:
cd /tmp && tar xzf second-brain-deploy.tar.gz
sudo ./install.sh
```

Ask: "Did the install script complete without errors? Paste the verification output."

## Step 11: Remove Public IP (Optional, Recommended)

Since Tailscale now provides access, the public IP is no longer needed:

1. OCI Console → Compute → Instance Details → Attached VNICs
2. Click the VNIC → IPv4 Addresses
3. Edit the public IP → select "No public IP" or "Reserved" (can re-attach later)

Ask: "Do you want to remove the public IP for security? (Recommended — Tailscale provides all access needed)"

## Step 12: Verification

Run these checks on the VM and report results:

```bash
echo "=== Timezone ==="
timedatectl | grep "Time zone"

echo "=== Services ==="
systemctl status happy-interactive.service --no-pager
systemctl list-timers happy-automation-* --no-pager

echo "=== Tailscale ==="
tailscale status

echo "=== Syncthing ==="
systemctl --user status syncthing --no-pager

echo "=== Vault ==="
ls -la /srv/workspace/second-brain/

echo "=== Lock Dir ==="
ls -la /srv/locks/
```

Confirm all checks pass. The system is now operational.

---

## Summary of What's Running

| Component | Purpose | Access |
|-----------|---------|--------|
| happy-interactive.service | Always-on Claude session | Mobile via HappyCoder |
| happy-automation-daily.timer | Daily summaries at 07:30 | Automatic |
| happy-automation-weekly.timer | Weekly summaries Sun 08:00 | Automatic |
| Syncthing | Vault sync across devices | Automatic |
| Tailscale | Private networking | All devices |

## Ongoing Costs

- Oracle Cloud free tier: $0/month
- Tailscale free tier: $0/month
- Syncthing: $0/month (self-hosted)
- **Total: $0/month**
