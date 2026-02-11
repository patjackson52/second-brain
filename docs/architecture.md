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
    A->>A: Atomic write to _system/summaries/
    A->>A: happy notify "Success"
    A->>L: Release lock
    deactivate A
```

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
