# Second Brain — System Architecture

## Device Topology

```mermaid
graph TB
    subgraph "Devices"
        Laptop["MacBook<br/>(Claude Code + Obsidian)"]
        Phone["Android<br/>(HappyCoder App)"]
    end

    subgraph "Oracle VM (Always-On)"
        Relay["HappyCoder Relay<br/>:3000"]
        Claude["Claude Code<br/>(--continue session)"]
        Auto["Automation<br/>(systemd timers)"]
        Watcher["Inbox Watcher<br/>(Syncthing Event API)"]
        ST_VM["Syncthing"]
    end

    Phone <-->|"Tailscale<br/>(encrypted)"| Relay
    Laptop <-->|"Tailscale<br/>(SSH + HappyCoder)"| Relay
    Relay <--> Claude
    Auto -->|"07:30 daily<br/>08:00 Sun weekly"| Claude
    Watcher -->|"on inbox sync"| Claude

    subgraph "Vault (/home/ubuntu/second-brain/)"
        Vault[("Markdown Files")]
    end

    Claude --> Vault
    ST_VM <--> Vault

    Laptop <-->|"Syncthing<br/>(own protocol)"| ST_VM
    Phone <-->|"Syncthing<br/>(own protocol)"| ST_VM
    Laptop <-->|"Syncthing<br/>(own protocol)"| Phone
```

## Data Flow

```mermaid
flowchart TD
    User([User]) -->|"/note content"| Note["/note command"]
    Note -->|"creates file"| Inbox["0_inbox/"]
    Inbox -->|"/triage"| Classify{"Confidence<br/>above 0.7?"}
    Classify -->|"Yes - auto-file"| Route["PARA Decision Tree"]
    Classify -->|"No - ask user"| Confirm([User Confirms])
    Confirm --> Route

    Route --> Projects["1_projects/active/"]
    Route --> Areas["2_areas/"]
    Route --> Resources["3_resources/"]
    Route --> Archive["4_archive/"]
    Route --> People["5_people/"]

    DailyTimer["daily.timer<br/>07:30 Pacific"] -->|"flock"| Lock{"Lock<br/>available?"}
    WeeklyTimer["weekly.timer<br/>Sun 08:00"] -->|"flock"| Lock
    Lock -->|"Yes"| Generate["Claude generates<br/>summary"]
    Lock -->|"No"| Skip["Skip + notify"]
    Generate -->|"atomic write"| DailyAuto["_system/summaries/daily/auto/"]
    Generate -->|"atomic write"| WeeklyAuto["_system/summaries/weekly/auto/"]

    Query([User]) -->|"/search query"| Search["/search command"]
    Search -.->|"searches"| Inbox
    Search -.->|"searches"| Projects
    Search -.->|"searches"| Areas
    Search -.->|"searches"| Resources
    Search -.->|"searches"| People
    Search -.->|"searches"| DailyAuto
    Search -.->|"searches"| WeeklyAuto
```

## Inbox Watcher — Sync-Triggered Triage

The inbox watcher automatically triages new files dropped into `0_inbox/` from any device. Rather than polling the filesystem, it uses the Syncthing Event API to detect exactly when a file finishes syncing.

### Sync Flow

```mermaid
sequenceDiagram
    participant D as Any Device
    participant S as Syncthing
    participant API as Syncthing Event API<br/>localhost:8384
    participant W as inbox-watcher.sh
    participant T as inbox-triage.sh
    participant L as /srv/locks/claude-exec.lock
    participant C as Claude Code

    D->>S: New file in 0_inbox/
    S->>S: Sync to VM
    S->>API: ItemFinished event<br/>(action: update)

    W->>API: Long-poll /rest/events<br/>(since=LAST_ID, timeout=60s)
    API-->>W: Events batch (JSON)
    W->>W: Filter: type==ItemFinished<br/>folder==second-brain<br/>item starts with 0_inbox/<br/>action==update

    Note over W: Debounce check (10s)
    W->>T: Execute triage script

    T->>L: flock -n (non-blocking)
    alt Lock available
        L-->>T: Acquired
        T->>T: Find *.md in 0_inbox/
        T->>C: claude --print "/triage all"
        C->>C: PARA decision tree<br/>(routes.yaml + triage_para.md)
        C-->>T: Files routed
        T->>T: happy notify "processed N file(s)"
    else Lock held
        L-->>T: FAIL
        T->>T: happy notify "skipped: session active"
    end
```

### Event Processing Pipeline

```mermaid
flowchart LR
    Poll["Long-poll<br/>/rest/events"] --> Parse["Parse JSON<br/>(jq)"]
    Parse --> Filter{"ItemFinished?<br/>folder=second-brain?<br/>0_inbox/*?<br/>action=update?"}
    Filter -->|No| Advance["Advance LAST_ID<br/>continue polling"]
    Filter -->|Yes| Debounce{"Elapsed ><br/>10s?"}
    Debounce -->|No| Skip["Skip<br/>(accumulate)"]
    Debounce -->|Yes| Triage["Run<br/>inbox-triage.sh"]
    Triage --> Advance
    Skip --> Advance
    Advance --> Poll

    style Filter fill:#ffd,stroke:#aa0
    style Triage fill:#dfd,stroke:#0a0
```

### Configuration

| Variable | Default | Source |
|----------|---------|--------|
| `VAULT_DIR` | `/home/ubuntu/second-brain` | systemd Environment |
| `LOCK_FILE` | `/srv/locks/claude-exec.lock` | systemd Environment |
| `SYNCTHING_API` | `http://localhost:8384` | script default |
| `SYNCTHING_FOLDER` | `second-brain` | script default |
| `DEBOUNCE_SECONDS` | `10` | script default |
| `TRIAGE_SCRIPT` | `/srv/scripts/inbox-triage.sh` | systemd Environment |
| `SYNCTHING_API_KEY` | auto-resolved from config.xml | script resolution |

API key resolution searches (in order):
1. `$HOME/.local/state/syncthing/config.xml`
2. `$HOME/.config/syncthing/config.xml`
3. `/etc/syncthing/config.xml`

## Concurrency & Locking

```mermaid
sequenceDiagram
    participant I as Interactive Session
    participant L as /srv/locks/claude-exec.lock
    participant A as Automation Timer
    participant W as Inbox Watcher

    Note over I: User starts session
    I->>L: flock (blocking)
    activate I
    L-->>I: Lock acquired

    Note over A: Timer fires 07:30
    A->>L: flock -n (non-blocking)
    L-->>A: FAIL (lock held)
    A->>A: happy notify "Skipped"

    Note over W: Inbox file synced
    W->>L: flock -n (non-blocking)
    L-->>W: FAIL (lock held)
    W->>W: happy notify "Triage skipped"

    Note over I: User ends session
    I->>L: Release lock
    deactivate I

    Note over W: Next inbox file synced
    W->>L: flock -n (non-blocking)
    L-->>W: Lock acquired
    activate W
    W->>W: claude --print "/triage all"
    W->>W: happy notify "processed N file(s)"
    W->>L: Release lock
    deactivate W

    Note over A: Next day timer fires
    A->>L: flock -n (non-blocking)
    L-->>A: Lock acquired
    activate A
    A->>A: Generate summary
    A->>A: Atomic write to _system/summaries/
    A->>A: happy notify "Success"
    A->>L: Release lock
    deactivate A
```

All three consumers — interactive sessions, scheduled timers, and the inbox watcher — share the same lock file. Only one Claude Code process runs at a time. Interactive sessions always win (blocking lock); automation and watcher skip gracefully (non-blocking).

## Directory Structure

```mermaid
graph LR
    Root["second-brain/"] --> Inbox["0_inbox/<br/><i>unprocessed capture</i>"]
    Root --> Projects["1_projects/<br/><i>active, waiting, archived</i>"]
    Root --> Areas["2_areas/<br/><i>ongoing responsibilities</i>"]
    Root --> Resources["3_resources/<br/><i>reference & knowledge</i>"]
    Root --> Archive["4_archive/<br/><i>completed items</i>"]
    Root --> People["5_people/<br/><i>relationship memory</i>"]
    Root --> Assets["_assets/<br/><i>images, audio, pdf</i>"]
    Root --> System["_system/<br/><i>config & automation</i>"]

    System --> Summaries["summaries/"]
    Summaries --> Daily["daily/"]
    Summaries --> Weekly["weekly/"]
    Daily --> DA["auto/<br/><i>automation output</i>"]
    Daily --> DM["manual/<br/><i>human reflections</i>"]
    Weekly --> WA["auto/<br/><i>automation output</i>"]
    Weekly --> WM["manual/<br/><i>human reflections</i>"]

    style Inbox fill:#ffd,stroke:#aa0
    style DA fill:#dfd,stroke:#0a0
    style WA fill:#dfd,stroke:#0a0
```

## Sync Topology

```mermaid
graph LR
    M["MacBook<br/>(primary editing)"] <-->|"Syncthing<br/>Send & Receive"| VM["Oracle VM<br/>(convergence node)"]
    VM <-->|"Syncthing<br/>Send & Receive"| A["Android<br/>(mobile access)"]
    M <-->|"Syncthing<br/>Send & Receive"| A

    style VM fill:#def,stroke:#06c
```

All peers are equal — no single source of truth. The VM acts as an always-on convergence point but is not authoritative.

## Systemd Services

| Unit | Type | Schedule | Purpose |
|------|------|----------|---------|
| `happy-interactive.service` | forking | always-on | tmux session for interactive Claude Code |
| `happy-automation-daily.timer` | oneshot | 07:30 daily | daily vault summary |
| `happy-automation-weekly.timer` | oneshot | Sun 08:00 | weekly vault summary |
| `happy-inbox-watcher.service` | simple | always-on | Syncthing event poller for auto-triage |

All services use `{{VAULT_DIR}}` template placeholders, stamped by `install.sh` via `sed` at deploy time.

## Reliability & SLA

### Inbox Watcher

| Metric | Target | Mechanism |
|--------|--------|-----------|
| Detection latency | < 75s from sync completion | 60s long-poll timeout + jq processing |
| Restart on crash | Automatic, 15s delay | `Restart=always`, `RestartSec=15` |
| Event continuity | No missed events | `since=LAST_ID` tracks position in event stream |
| Startup behavior | Ignores history | Fetches latest event ID on start, only processes new events |
| Debounce | 10s between triggers | Prevents rapid-fire triage on bulk syncs |
| Concurrent safety | Single Claude process | flock on `/srv/locks/claude-exec.lock` |
| Graceful degradation | Skip on lock contention | Non-blocking flock; notifies and exits cleanly |
| API failure recovery | Retry after 10s | curl failure triggers sleep + continue |

### Scheduled Summaries

| Metric | Target | Mechanism |
|--------|--------|-----------|
| Daily summary | 07:30 Pacific | systemd `OnCalendar`, `Persistent=true` |
| Weekly summary | Sunday 08:00 Pacific | systemd `OnCalendar`, `Persistent=true` |
| Missed timer catchup | Run on next boot | `Persistent=true` fires missed timers |
| Idempotency | One summary per day/week | Checks if output file already exists |
| Atomic writes | No partial files | Write to `.tmp`, then `mv` to final path |
| Failure notification | Always | `trap cleanup_on_error ERR` + `happy notify` |

### Known Limitations

- **Syncthing Event API subscriptions**: The `events=` URL filter uses per-subscription IDs that drift from the global stream. The watcher fetches all events and filters client-side with `jq` to avoid this.
- **No persistent cursor**: If the watcher restarts, it starts from the latest event ID. Events that occurred between crash and restart are not replayed. Files already synced will be triaged on the next sync event or manual `/triage` run.
- **Claude Code availability**: Triage depends on Claude Code being installed and authenticated on the VM. If the API key expires or Claude is unavailable, `inbox-triage.sh` will fail and notify.

## Logging & Observability

### Log Locations

| Component | Command | Notes |
|-----------|---------|-------|
| Inbox watcher | `journalctl -u happy-inbox-watcher.service` | Long-lived; logs every detected file |
| Inbox triage | `journalctl -u happy-inbox-watcher.service` | Runs as subprocess of watcher |
| Daily summary | `journalctl -u happy-automation-daily.service` | One-shot; check after 07:30 |
| Weekly summary | `journalctl -u happy-automation-weekly.service` | One-shot; check after Sunday 08:00 |
| Interactive session | `journalctl -u happy-interactive.service` | tmux session lifecycle |
| Timer schedules | `systemctl list-timers --all` | Next/last fire times |
| Triage audit log | `_system/processing-log.md` | Append-only log of PARA routing decisions |
| Syncthing | `journalctl -u syncthing@ubuntu.service` | Sync events, conflicts, errors |

### Log Format

The inbox watcher outputs structured log lines:

```
inbox-watcher: started
  vault:    /home/ubuntu/second-brain
  folder:   second-brain
  api:      http://localhost:8384
  debounce: 10s
  starting from event ID: 8280
  synced: 0_inbox/my-new-note.md
  triggering triage for 1 file(s)
inbox-triage: processing 1 file(s)
inbox-triage: complete
```

### Happy Notifications

All automation sends notifications via `happy notify`:

| Event | Message |
|-------|---------|
| Triage success | `Inbox triage: processed N file(s)` |
| Triage skipped (lock) | `Inbox triage skipped: session active` |
| Triage failed | `Inbox triage failed` |
| Daily summary written | `Daily summary written for YYYY-MM-DD` |
| Daily summary skipped | `Skipped: daily summary already exists for YYYY-MM-DD` |
| Daily summary failed | `Failed: daily summary generation error for YYYY-MM-DD` |

## Debug Guide

### Inbox watcher not detecting files

```bash
# 1. Check service is running
systemctl status happy-inbox-watcher.service

# 2. Check recent logs
journalctl -u happy-inbox-watcher.service -n 50 --no-pager

# 3. Verify Syncthing API is reachable
curl -sf -H "X-API-Key: $(grep -oP '(?<=<apikey>).*(?=</apikey>)' \
    ~/.local/state/syncthing/config.xml)" \
    "http://localhost:8384/rest/events?limit=1" | jq .

# 4. Check for recent ItemFinished events
curl -sf -H "X-API-Key: YOUR_KEY" \
    "http://localhost:8384/rest/events?limit=20&timeout=1" | \
    jq '.[] | select(.type=="ItemFinished") | {id, item: .data.item, action: .data.action}'

# 5. Verify Syncthing folder ID matches
curl -sf -H "X-API-Key: YOUR_KEY" \
    "http://localhost:8384/rest/config/folders" | jq '.[].id'
```

### Triage not running after detection

```bash
# 1. Check lock contention — who holds it?
fuser /srv/locks/claude-exec.lock

# 2. Verify triage script is executable
ls -la /srv/scripts/inbox-triage.sh

# 3. Check lock directory permissions
ls -la /srv/locks/

# 4. Manually test triage
/srv/scripts/inbox-triage.sh

# 5. Verify Claude Code is available
which claude && claude --version
```

### Service keeps restarting

```bash
# 1. Check exit code and error
systemctl status happy-inbox-watcher.service
journalctl -u happy-inbox-watcher.service -n 20 --no-pager

# 2. Common causes:
#    - HOME unbound: check Environment=HOME in service unit
#    - API key not found: set SYNCTHING_API_KEY or check config.xml path
#    - curl/jq not installed: which curl jq
#    - Syncthing not running: systemctl status syncthing@ubuntu.service

# 3. Test script manually as ubuntu user
sudo -u ubuntu /srv/scripts/inbox-watcher.sh
```

### Verifying end-to-end flow

```bash
# 1. Create test file on any device
echo "# Test" > /path/to/second-brain/0_inbox/test-triage.md

# 2. Watch watcher logs in real-time
journalctl -u happy-inbox-watcher.service -f

# 3. Expected output (within ~60s of sync):
#    synced: 0_inbox/test-triage.md
#    triggering triage for 1 file(s)
#    inbox-triage: processing 1 file(s)
#    inbox-triage: complete

# 4. Verify file was routed
ls 0_inbox/test-triage.md  # should be gone
# Check 1_projects/, 2_areas/, 3_resources/, etc. for routed file

# 5. Clean up if still in inbox
rm 0_inbox/test-triage.md
```

### Redeploying after changes

```bash
# From the repo directory on the VM:
sudo bash install.sh

# Or to redeploy just the watcher:
sudo cp scripts/inbox-watcher.sh /srv/scripts/
sudo cp scripts/inbox-triage.sh /srv/scripts/
sudo chmod +x /srv/scripts/inbox-*.sh
sudo sed 's|{{VAULT_DIR}}|/home/ubuntu/second-brain|g' \
    systemd/happy-inbox-watcher.service > /tmp/watcher.service
sudo mv /tmp/watcher.service /etc/systemd/system/happy-inbox-watcher.service
sudo systemctl daemon-reload
sudo systemctl restart happy-inbox-watcher.service
```
