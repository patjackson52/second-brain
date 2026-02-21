# Product Requirements Document (PRD)

## Personal Second Brain (Markdown, Local-First, Multi-Device)

**Status:** Approved
**Owner:** Patrick
**Audience:** Engineers / Operators
**Last Updated:** 2026-01-23

---

## 1. Overview

### Product Name

**Personal Second Brain**

### Summary

A local-first, Markdown-based personal knowledge and execution system designed to maximize **trust, reliability, and fast retrieval**. The system emphasizes **remembering and executing**, with AI-assisted capture and classification via Claude Code slash commands (`/note`, `/triage`, `/search`), while avoiding dependency on proprietary tools or databases.

All information is stored as plain Markdown files in a small set of **semantic directories**, synced across devices via Syncthing, and searchable in full. A server-resident automation system generates scheduled summaries (daily/weekly) and delivers them via push notification.

The system is **headless**, **fault-tolerant**, and **operable via systemd**, with no custom UI.

---

## 2. Problem Statement

Human memory is unreliable, and many modern "second brain" tools introduce fragility through:

- Proprietary databases
- SaaS lock-in
- Opaque syncing behavior
- Tool abandonment risk

The user needs a system that can be **trusted long-term**, where:

- Information is easy to capture
- Knowledge is easy to retrieve
- Execution context is preserved
- No single tool failure causes loss of data or confidence

---

## 3. Goals & Success Criteria

### Primary User

- Single user (solo-only)

### Primary Jobs to Be Done

1. **Remembering** — durable storage and retrieval of knowledge
2. **Executing** — tracking projects, decisions, and next actions

### Goals

- Always-on HappyCoder session for interactive mobile use
- Automation and interactive access to the **same vault**
- Clear **read/write separation** inside the vault
- Automated daily and weekly Markdown note generation
- Predictable scheduling in **America/Los_Angeles (PST/PDT)**
- Deterministic notification behavior
- Minimal locking; no filesystem contention

### Success Criteria

- The user trusts the system more than their memory
- Information can be found quickly via `/search`
- Capture is frictionless via `/note`
- Classification happens automatically via `/triage`
- The system remains usable even if individual tools disappear (plain Markdown files)
- Automation responses appear in shared chat history
- Explicit push notifications fire for every automation run
- No concurrent Claude execution observed over sustained use

---

## 4. Non-Goals

This system is **not** intended to be:

- A full task-management app
- A calendar or scheduling system
- A real-time collaboration platform
- A publishing platform
- A UI-heavy consumer notes product
- A multi-user system
- A CRDT or real-time collaborative editing system
- A server-side UI

---

## 5. Core Constraints & Principles

### Hard Requirements

- Local-first data storage
- Global full-text search across all notes
- Works without any specific editor installed
- Survives tool abandonment (plain Markdown files)
- Offline editing on laptop
- Periodic (not real-time) sync acceptable
- Near-zero recurring cost

### Nice-to-Have

- Encryption at rest
- Offline mobile access (not required for v1)

---

## 6. Canonical Directory Structure

The system is organized using **five semantic buckets** plus one **archive** directory:

```
second-brain/
├── inbox/
├── ideas/
├── projects/
├── people/
├── admin/
└── archive/
    ├── daily/
    │   ├── auto/
    │   └── manual/
    └── weekly/
        ├── auto/
        └── manual/
```

---

## 7. Directory Semantics

### 7.1 `inbox/` — Unprocessed Capture

**Purpose**

- Entry point for all new information captured interactively (human or interactive agent)
- No classification required at capture time

**Rules**

- Nothing is created outside `inbox/` by interactive/human captures
- Automation-generated outputs write directly to `archive/` (see section 11)
- Files are expected to move out of inbox
- Messy is acceptable

**Minimum required metadata**

```yaml
---
type: unknown
captured_at: 2026-01-22T15:34:00Z
source: claude-code
ai_generated: false
---
```

---

### 7.2 `ideas/` — Concepts & Thinking

**Purpose**

- Atomic ideas
- Mental models
- Insights and hypotheses

**Example metadata**

```yaml
---
type: idea
tags: [systems, reliability]
confidence: 0.82
ai_generated: false
---
```

---

### 7.3 `projects/` — Execution & Outcomes

**Purpose**

- Work with a defined outcome
- Active or paused execution

**Structure**

```
projects/
└── example-project/
    ├── overview.md
    ├── tasks.md
    └── decisions.md
```

**Example metadata**

```yaml
---
type: project
status: active
owner: self
---
```

---

### 7.4 `people/` — Humans as First-Class Entities

**Purpose**

- Context and history about people
- Follow-ups and relationship memory

**Example metadata**

```yaml
---
type: person
relationship: collaborator
last_interaction: 2026-01-20
---
```

---

### 7.5 `admin/` — Operational & Meta Notes

**Purpose**

- Life administration
- System notes
- Processes and logistics

---

### 7.6 `archive/` — Automated & Manual Summaries

**Purpose**

- Storage for daily and weekly summaries
- Partitioned into `auto/` (automation-generated) and `manual/` (human-authored) subdirectories

**Structure**

- `archive/daily/auto/` — Automation-generated daily summaries
- `archive/daily/manual/` — Human-authored daily reflections
- `archive/weekly/auto/` — Automation-generated weekly summaries
- `archive/weekly/manual/` — Human-authored weekly reflections

---

## 8. Data Flow

### Interactive Capture

```
Capture (human / interactive agent)
  ↓
inbox/
  ↓ (AI + human classification via /triage)
ideas/ | projects/ | people/ | admin/
```

### Automation Output

```
Scheduled automation run
  ↓
archive/daily/auto/ or archive/weekly/auto/
```

Automation writes directly to its designated directories. It does not pass through `inbox/`.

---

## 9. Metadata Schema

### Required (all notes)

```yaml
---
type: unknown | idea | project | person | admin | daily-summary | weekly-summary
captured_at: ISO-8601 timestamp
---
```

### Optional (recommended)

```yaml
source: claude-code | happy-coder | laptop
tags: []
status: active | paused | done
confidence: 0.0–1.0
ai_generated: true | false
generated_by: happy-automation
```

### AI Provenance Rule

If a note is AI-created or AI-synthesized, it **must** include:

```yaml
ai_generated: true
```

User-authored content captured via `/note` is marked `ai_generated: false`.

---

## 10. Agent Interface — Slash Commands

The canonical agent interface consists of three slash commands, usable on both laptop and server (via Claude Code):

### 10.1 `/note <content>`

**Purpose**: Frictionless capture of a new thought or piece of information.

**Behavior**:

1. Creates a new Markdown file in `inbox/`
2. Filename is auto-generated: timestamp-based slug (e.g., `2026-01-22-1534-quick-thought.md`) or derived from content
3. Adds required frontmatter:

```yaml
---
type: unknown
captured_at: <ISO-8601 timestamp>
source: claude-code
ai_generated: false
---
```

4. Writes user-provided `<content>` as the note body
5. Automatically invokes `/triage` on the newly created file

**Notes**:

- `ai_generated: false` because the content originates from the user
- `ai_generated: true` is reserved for AI-synthesized notes (e.g., summaries, connections generated from existing notes)

---

### 10.2 `/triage [file|all]`

**Purpose**: AI-assisted classification and routing of inbox items.

**Behavior**:

- If a specific file path is given, classifies that file
- If `all` or no argument is provided, processes all files in `inbox/`

**Classification output** (per file):

| Field | Description |
|-------|-------------|
| Target bucket | One of: `ideas`, `projects`, `people`, `admin` |
| `type` value | Appropriate type for the target bucket |
| Suggested tags | List of relevant tags |
| Confidence score | Float 0.0–1.0 |

**Routing logic**:

- High confidence (> 0.6): auto-filed to target bucket, frontmatter updated with classification results
- Low confidence (<= 0.6): presents suggestion to user, asks for confirmation or override

**Frontmatter updates on move**:

```yaml
---
type: <classified type>
captured_at: <original timestamp>
source: claude-code
tags: [<suggested tags>]
confidence: <0.0-1.0>
ai_generated: false
---
```

---

### 10.3 `/search <query>`

**Purpose**: Full-text retrieval across the entire knowledge base.

**Behavior**:

- Searches across all files: contents, filenames, and YAML frontmatter
- Returns matching files with relevant context snippets
- Ordered by relevance

**Scope**: All directories — `inbox/`, `ideas/`, `projects/`, `people/`, `admin/`, `archive/`

---

## 11. Automation System

### Session Execution Model

- Interactive and automation runs use the **same Claude session**
- Automation launches Claude using the same workspace with `--continue` to append to the existing conversation
- Every automation run produces a Claude response visible in mobile chat history

### Scheduling

**Timezone**: Server set to **America/Los_Angeles** (PST/PDT)

**Daily Automation**:
- Schedule: every day at **07:30**
- Output: `archive/daily/auto/daily-summary-YYYY-MM-DD.md`

**Weekly Automation**:
- Schedule: Sundays at **08:00**
- Output: `archive/weekly/auto/weekly-summary-YYYY-Www.md`

### Output Specifications

**Daily Summary**:

```yaml
---
type: daily-summary
date: YYYY-MM-DD
generated_by: happy-automation
ai_generated: true
---
```

Sections:
1. What changed today
2. Open loops / TODO
3. Next actions for tomorrow
4. Risks / blockers
5. Questions for Patrick

**Weekly Summary**:

```yaml
---
type: weekly-summary
week: YYYY-Www
generated_by: happy-automation
ai_generated: true
---
```

Sections:
1. Highlights
2. Progress by theme
3. Open loops / TODO
4. Next actions
5. Questions for Patrick

### Notification Semantics

- Claude responses always appear in chat
- Push notifications are **not guaranteed** for new chat messages alone
- Automation **MUST explicitly trigger notifications** using `happy notify`

| Outcome | Notification |
|---------|-------------|
| Success | "Daily/Weekly summary written …" |
| Skip | "Skipped: interactive session active" |
| Failure | "Failed: reason" |

### Reliability

**Atomic Writes**:
- Automation writes to a temp file in the target directory
- Validates file existence and non-empty content
- Atomic rename to final filename

**Idempotency**:
- If output file already exists: skip run and notify user

**Crash Recovery**:
- systemd restarts HappyCoder
- Locks released automatically on process exit
- Next scheduled run proceeds normally

---

## 12. Read/Write Boundaries

### Interactive Agent

- **READ:** entire vault
- **WRITE:** anywhere **except** `archive/daily/auto/` and `archive/weekly/auto/`
- **MUST NOT:** edit or delete automation-generated files

### Automation Agent

- **READ:** entire vault
- **WRITE:** only to `archive/daily/auto/` and `archive/weekly/auto/`
- **MUST NOT:** modify or delete any other vault files, or overwrite existing automation files

These rules are enforced by **prompt discipline and scripting**, not filesystem ACLs.

---

## 13. Locking & Concurrency

### Execution Lock

- Path: `/srv/locks/claude-exec.lock`
- Mechanism: `flock`

### Rules

1. Any Claude execution **must acquire the execution lock**
2. Interactive usage has priority
3. Automation:
   - Attempts a **non-blocking** lock
   - If lock is held → **skip execution** and notify
   - Must never wait
4. At most **one Claude Code process** may run at a time

### Rationale

Claude Code sessions are not safe for concurrent execution, even with partitioned filesystem writes.

---

## 14. Platforms & Topology

### Editing Surfaces

**Primary**
- AI-assisted authoring via Claude Code
- Slash commands (`/note`, `/triage`, `/search`) as the canonical interface
- Used for: creating notes, editing notes, summarization, classification

**Secondary**
- Local laptop (macOS): direct Markdown editing, fully offline capable
- Mobile (Android): access via HappyCoder / Claude Code

**Optional**
- Obsidian for browsing (non-authoritative)

### Always-On Node (Linux VM)

- Acts as:
  - Sync convergence point
  - Claude Code access point
  - Automation host (scheduled summaries)
  - HappyCoder relay
- Vault path: `/srv/workspace/second-brain/`

### Authority Model

- **True peer-to-peer** — no single conceptual source of truth
- VM acts as operational hub and long-lived convergence node, but is **not authoritative**
- Eventual consistency is acceptable
- Any device's copy is equally valid

---

## 15. Networking & Relay Architecture

### Purpose

The HappyCoder relay provides a secure, low-friction communication path between client devices (laptop, mobile) and the always-on VM without exposing the VM directly to the public internet.

### Private-First Deployment Model (v1)

- No public DNS
- No public inbound ports
- VM initiates or accepts connections only over a private overlay network
- Cost: $0/month

### Network Topology

```
Client Devices (Laptop / Android)
        │
        │ Private Network (Tailscale)
        ▼
Linux VM (HappyCoder Relay)
        │
        ▼
Local Filesystem / Second Brain Vault
```

### Private Networking Layer

Tailscale (or WireGuard) provides:

- Stable private IP or hostname for the VM
- Encrypted transport
- Device-level access control

Example relay URLs:
- `http://100.x.y.z:3000`
- `http://happycoder-vm.tailnet.ts.net:3000`

### Relay Hosting

The relay runs on the Linux VM:

- HappyCoder relay service
- Local persistence (e.g. Postgres, Redis)
- Persistent VM disk and container volumes
- Automatic restart on reboot
- Pairing survives VM restarts (no repeated QR-code friction)

### Client Configuration

All HappyCoder clients must be explicitly configured to use the self-hosted relay:

- **VM / Laptop (CLI):** Configure relay URL via environment variable or config
- **Mobile App:** Set Relay Server URL to the private relay address

### Upgrade Path to Public Access (Future)

- Add a reverse proxy (e.g. Caddy, Nginx)
- Add a domain name and enable HTTPS
- Optionally add authentication
- No re-pairing required as long as relay identity is unchanged

### Security Posture

- End-to-end encryption between clients
- Relay cannot read note contents
- No public attack surface in v1
- Explicit, auditable networking configuration

---

## 16. Sync & Safety

### Sync Mechanism

- **Syncthing** for cross-device file sync
- Sync is periodic and eventual (not real-time)
- Configured for the entire vault directory

### No Git

- Version history is **NOT** managed by Git
- The vault is a plain directory of Markdown files
- No `.git/` directory, no commits, no remote push

### Backups

- Device-level backup mechanisms:
  - macOS: Time Machine or equivalent
  - VM: Snapshots, disk-level backups
- Multiple replicas via Syncthing provide redundancy

### Conflict Resolution

- Conflicts are surfaced explicitly by Syncthing
- Resolved manually when detected

---

## 17. Failure Tolerance

Tolerated failures:

- Laptop loss
- VM loss
- Tool abandonment (Claude Code, HappyCoder, Obsidian)
- Partial sync failure

Mitigation:

- Multiple replicas across devices
- Plain-text recoverability — all data is readable Markdown
- No single point of failure
- Device-level backups for point-in-time recovery
- systemd restart for service failures
- Locks released automatically on process exit

---

## 18. Deployment Requirements

### Required Services

- `happy-interactive.service`
- `happy-automation-daily.service`
- `happy-automation-daily.timer`
- `happy-automation-weekly.service`
- `happy-automation-weekly.timer`

### System Configuration

- `timedatectl set-timezone America/Los_Angeles`
- HappyCoder authenticated and paired
- Claude Code authenticated
- Syncthing configured for entire vault directory
- Execution lock directory exists: `/srv/locks/`

---

## 19. Acceptance Criteria

- Interactive agent reads/writes only approved directories
- Automation writes only to `archive/daily/auto/` and `archive/weekly/auto/`
- Nothing is created outside `inbox/` by interactive/human captures
- Automation responses appear in shared chat history
- Explicit push notifications fire for every automation run
- No concurrent Claude execution observed over sustained use
- `/note` creates files in `inbox/` with correct frontmatter
- `/triage` classifies and routes inbox items with confidence scoring
- `/search` returns results from all directories including `archive/`
- Syncthing replicates vault across all configured devices
- System recovers gracefully from laptop loss, VM loss, or tool abandonment

---

## 20. Guiding Principles

- Files over databases
- Buckets over rigid hierarchies
- Metadata over schemas
- Explicit movement over hidden automation
- **Trust over convenience**
