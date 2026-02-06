# Connecting to Oracle VM from MacBook

## Quick Connect (via Tailscale)

```bash
ssh ubuntu@second-brain-vm
```

This works when Tailscale is running on both your MacBook and the VM.

## Connection Details

| Property | Value |
|----------|-------|
| **Hostname (Tailscale)** | `second-brain-vm` |
| **Public IP** | `64.181.254.153` |
| **Username** | `ubuntu` |
| **SSH Key** | `~/.ssh/oracle-second-brain` (or in repo root) |
| **OS** | Ubuntu 24.04 |
| **Region** | Oracle Cloud US West (San Jose) |

## Alternative: Direct SSH (Public IP)

If Tailscale isn't available, connect via public IP:

```bash
ssh -i ~/.ssh/oracle-second-brain ubuntu@64.181.254.153
```

## Prerequisites

1. **Tailscale running** on your MacBook (`tailscale status` to check)
2. **SSH key** available at `~/.ssh/oracle-second-brain` or `/Users/patrick/workspace/second-brain/oracle-second-brain`

## Troubleshooting

### "Connection refused" or timeout
- Check if VM is running in Oracle Cloud Console
- Verify Tailscale is connected: `tailscale status`
- Try public IP connection as fallback

### "Permission denied (publickey)"
- Ensure correct SSH key is being used: `ssh -i /path/to/oracle-second-brain ubuntu@second-brain-vm`
- Check key permissions: `chmod 600 ~/.ssh/oracle-second-brain`

### Start Tailscale (if not running)
```bash
# macOS
sudo tailscale up

# Check status
tailscale status
```

## Oracle Cloud Console Access

- **Console URL**: https://cloud.oracle.com/compute/instances
- **Instance Name**: `second-brain-vm`
- **Cloud Shell**: Available but requires copying SSH key to access VM

## VM Details

- **Workspace**: `/srv/workspace/second-brain/`
- **Services**: `happy-interactive.service` (HappyCoder relay)
