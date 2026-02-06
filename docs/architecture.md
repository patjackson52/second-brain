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
        ST_VM["Syncthing"]
    end

    Phone <-->|"Tailscale<br/>(encrypted)"| Relay
    Laptop <-->|"Tailscale<br/>(SSH + HappyCoder)"| Relay
    Relay <--> Claude
    Auto -->|"07:30 daily<br/>08:00 Sun weekly"| Claude

    subgraph "Vault (/srv/workspace/second-brain/)"
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
    Note -->|"creates file"| Inbox["inbox/"]
    Inbox -->|"/triage"| Classify{"Confidence<br/>above 0.6?"}
    Classify -->|"Yes - auto-file"| Route["Route to bucket"]
    Classify -->|"No - ask user"| Confirm([User Confirms])
    Confirm --> Route

    Route --> Ideas["ideas/"]
    Route --> Projects["projects/"]
    Route --> People["people/"]
    Route --> Admin["admin/"]

    DailyTimer["daily.timer<br/>07:30 Pacific"] -->|"flock"| Lock{"Lock<br/>available?"}
    WeeklyTimer["weekly.timer<br/>Sun 08:00"] -->|"flock"| Lock
    Lock -->|"Yes"| Generate["Claude generates<br/>summary"]
    Lock -->|"No"| Skip["Skip + notify"]
    Generate -->|"atomic write"| DailyAuto["archive/daily/auto/"]
    Generate -->|"atomic write"| WeeklyAuto["archive/weekly/auto/"]

    Query([User]) -->|"/search query"| Search["/search command"]
    Search -.->|"searches"| Inbox
    Search -.->|"searches"| Ideas
    Search -.->|"searches"| Projects
    Search -.->|"searches"| People
    Search -.->|"searches"| Admin
    Search -.->|"searches"| DailyAuto
    Search -.->|"searches"| WeeklyAuto
```

## Concurrency & Locking

```mermaid
sequenceDiagram
    participant I as Interactive Session
    participant L as /srv/locks/claude-exec.lock
    participant A as Automation Timer

    Note over I: User starts session
    I->>L: flock (blocking)
    activate I
    L-->>I: Lock acquired

    Note over A: Timer fires 07:30
    A->>L: flock -n (non-blocking)
    L-->>A: FAIL (lock held)
    A->>A: happy notify "Skipped"

    Note over I: User ends session
    I->>L: Release lock
    deactivate I

    Note over A: Next day timer fires
    A->>L: flock -n (non-blocking)
    L-->>A: Lock acquired
    activate A
    A->>A: Generate summary
    A->>A: Atomic write to archive/
    A->>A: happy notify "Success"
    A->>L: Release lock
    deactivate A
```

## Directory Structure

```mermaid
graph LR
    Root["second-brain/"] --> Inbox["inbox/<br/><i>unprocessed capture</i>"]
    Root --> Ideas["ideas/<br/><i>concepts & thinking</i>"]
    Root --> Projects["projects/<br/><i>execution & outcomes</i>"]
    Root --> People["people/<br/><i>relationship memory</i>"]
    Root --> Admin["admin/<br/><i>ops & logistics</i>"]
    Root --> Archive["archive/"]

    Archive --> Daily["daily/"]
    Archive --> Weekly["weekly/"]
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
