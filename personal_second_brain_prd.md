# Product Requirements Document (PRD)
## Personal Second Brain (Markdown, Local-First)

---

## 1. Overview

### Product Name
**Personal Second Brain**

### Summary
A local-first, Markdown-based personal knowledge and execution system designed to maximize **trust, reliability, and fast retrieval**. The system emphasizes **remembering and executing**, with AI-assisted capture and classification, while avoiding dependency on proprietary tools or databases.

All information is stored as plain Markdown files in a small set of **semantic directories**, synced periodically across devices, and searchable in full.

---

## 2. Problem Statement

Human memory is unreliable, and many modern “second brain” tools introduce fragility through:

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
- Single user (solo-first), with optional future expansion

### Primary Jobs to Be Done
1. **Remembering** — durable storage and retrieval of knowledge
2. **Executing** — tracking projects, decisions, and next actions

### Success Criteria
- The user trusts the system more than their memory
- Information can be found quickly via search
- The system remains usable even if individual tools disappear

---

## 4. Non-Goals

This system is **not** intended to be:
- A full task-management app
- A calendar or scheduling system
- A real-time collaboration platform
- A publishing platform
- A UI-heavy consumer notes product

---

## 5. Core Constraints & Principles

### Hard Requirements
- Local-first data storage
- Global full-text search across all notes
- Works without any specific editor installed
- Survives tool abandonment
- Offline editing on laptop
- Periodic (not real-time) sync acceptable
- Near-zero recurring cost

### Nice-to-Have
- Encryption at rest
- Offline mobile access (not required for v1)

---

## 6. Platforms & Topology

### Editing Surfaces

**Primary**
- AI-assisted authoring via Happy Coder / Claude Code
- Used for:
  - Creating notes
  - Editing notes
  - Summarization and refactoring

**Secondary**
- Local laptop (macOS)
- Direct Markdown editing
- Fully offline capable

### Mobile Access
- Android
- Access via Happy Coder / Claude Code
- Optional Obsidian mobile for browsing (non-authoritative)

### Always-On Node
- Linux VM
- Acts as:
  - Sync hub
  - Claude Code access point
  - Optional automation host

### Authority Model
- **True peer-to-peer**
- No single conceptual source of truth
- VM acts as a long-lived convergence node
- Eventual consistency is acceptable

---

## 7. Canonical Directory Structure

The entire system is organized using **only five semantic buckets**:

```
second-brain/
├── inbox/
├── ideas/
├── projects/
├── people/
├── admin/
```

---

## 8. Directory Semantics

### 8.1 `inbox/` — Unprocessed Capture

**Purpose**
- Entry point for all new information
- No classification required at capture time

**Rules**
- Nothing is created outside `inbox/`
- Files are expected to move out
- Messy is acceptable

**Minimum required metadata**
```yaml
---
type: unknown
captured_at: 2026-01-22T15:34:00Z
source: happy-coder | laptop
---
```

---

### 8.2 `ideas/` — Concepts & Thinking

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

### 8.3 `projects/` — Execution & Outcomes

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

### 8.4 `people/` — Humans as First-Class Entities

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

### 8.5 `admin/` — Operational & Meta Notes

**Purpose**
- Life administration
- System notes
- Processes and logistics

---

## 9. Data Flow

```
Capture
  ↓
inbox/
  ↓ (AI + human classification)
ideas/ | projects/ | people/ | admin/
```

---

## 10. Metadata Schema

### Required (all notes)
```yaml
---
type: idea | project | person | admin
captured_at: ISO-8601 timestamp
---
```

### Optional (recommended)
```yaml
source: happy-coder | laptop
tags: []
status: active | paused | done
confidence: 0.0–1.0
ai_generated: true | false
```

### AI Provenance Rule
If a note is AI-created or AI-modified, it **must** include:
```yaml
ai_generated: true
```

---

## 11. Search & Retrieval

- Global full-text search across file contents, filenames, and YAML frontmatter
- Search is the primary retrieval mechanism

---

## 12. Sync, Versioning & Safety

- Sync is periodic and eventual
- Acceptable mechanisms:
  - Peer-to-peer sync
  - Optional Obsidian Sync (non-authoritative)
  - Periodic Git backups
- Version history is required
- Conflicts are surfaced explicitly and resolved manually

---

## 13. Failure Tolerance

Tolerated failures:
- Laptop loss
- VM loss
- Tool abandonment
- Partial sync failure

Mitigation:
- Multiple replicas
- Plain-text recoverability
- No single point of failure

---

## 14. Networking & Relay Architecture

### Purpose
The Happy Coder relay provides a secure, low-friction communication path between client devices (laptop, mobile) and the always-on VM without exposing the VM directly to the public internet.

The relay is responsible for:
- Encrypted message relay
- Session coordination and pairing
- Connection resilience across NATs and mobile networks

The relay **does not** interpret, store, or understand note contents beyond transient, encrypted transport.

---

### Private-First Deployment Model (v1)

The system is deployed in **private mode** by default, with no public ingress.

#### Characteristics
- No public DNS
- No public inbound ports
- VM initiates or accepts connections only over a private network
- Cost: $0/month

#### Network Topology
```
Client Devices (Laptop / Android)
        │
        │ Private Network (e.g. Tailscale)
        ▼
Happy Coder Relay (Linux VM)
        │
        ▼
Local Filesystem / Second Brain Repo
```

#### Private Networking Layer
A private overlay network (e.g. Tailscale or WireGuard) provides:
- Stable private IP or hostname for the VM
- Encrypted transport
- Device-level access control

Example relay URLs:
- `http://100.x.y.z:3000`
- `http://happycoder-vm.tailnet.ts.net:3000`

These URLs are persistent across VM reboots.

---

### Relay Hosting

The relay runs on the Linux VM and is composed of:
- Happy Coder relay service
- Local persistence (e.g. Postgres, Redis)

Operational requirements:
- Persistent VM disk
- Persistent container volumes
- Automatic restart on reboot

These guarantees ensure:
- Pairing survives VM restarts
- No repeated QR-code or token friction

---

### Client Configuration

All Happy Coder clients must be explicitly configured to use the self-hosted relay.

#### VM / Laptop (CLI)
- Configure relay URL via environment variable or config

#### Mobile App
- Set **Relay Server URL** to the private relay address

Once configured, all session pairing and reconnection flows use the private relay.

---

### Upgrade Path to Public Access (Future)

The private-first design allows a clean upgrade to public access if desired.

#### Upgrade Steps
- Add a reverse proxy (e.g. Caddy, Nginx)
- Add a domain name
- Enable HTTPS
- Optionally add authentication

#### Invariants (Do Not Change)
- Relay service
- Relay database
- VM disk
- Client pairing state

As long as the relay identity remains unchanged, no re-pairing is required.

---

### Security Posture

- End-to-end encryption between clients
- Relay cannot read note contents
- No public attack surface in v1
- Explicit, auditable networking configuration

---

## 15. Guiding Principles

- Files over databases
- Buckets over rigid hierarchies
- Metadata over schemas
- Explicit movement over hidden automation
- **Trust over convenience**

