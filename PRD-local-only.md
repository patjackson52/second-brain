# Product Requirements Document (PRD) — Local-Only

## Personal Second Brain (Markdown, Local-First, Claude Code)

---

## 1. Overview

### Product Name

**Personal Second Brain**

### Summary

A local-only, Markdown-based personal knowledge and execution system designed to maximize **trust, reliability, and fast retrieval**. The system emphasizes **remembering and executing**, with AI-assisted capture and classification via Claude Code slash commands, while avoiding dependency on proprietary tools or databases.

All information is stored as plain Markdown files in a small set of **semantic directories**, versioned locally with Git, and searchable in full via Claude Code.

---

## 2. Problem Statement

Human memory is unreliable, and many modern "second brain" tools introduce fragility through:

* Proprietary databases
* SaaS lock-in
* Opaque syncing behavior
* Tool abandonment risk

The user needs a system that can be **trusted long-term**, where:

* Information is easy to capture
* Knowledge is easy to retrieve
* Execution context is preserved
* No single tool failure causes loss of data or confidence

---

## 3. Goals & Success Criteria

### Primary User

* Single user (solo-only)

### Primary Jobs to Be Done

1. **Remembering** — durable storage and retrieval of knowledge
2. **Executing** — tracking projects, decisions, and next actions

### Success Criteria

* The user trusts the system more than their memory
* Information can be found quickly via `/search`
* Capture is frictionless via `/note`
* Classification happens automatically via `/triage`
* The system remains usable even if Claude Code disappears (plain Markdown + Git)

---

## 4. Non-Goals

This system is **not** intended to be:

* A full task-management app
* A calendar or scheduling system
* A real-time collaboration platform
* A publishing platform
* A UI-heavy consumer notes product
* A mobile-accessible system
* A synced multi-device system

---

## 5. Core Constraints & Principles

### Hard Requirements

* Local-only data storage (single machine)
* Global full-text search across all notes
* Works without any specific editor installed
* Survives tool abandonment (plain Markdown + Git)
* Near-zero recurring cost

### Nice-to-Have

* Encryption at rest

---

## 6. Platform

### Editing Surface

* **Claude Code** on local macOS laptop
* All interaction via three slash commands: `/note`, `/triage`, `/search`
* Direct Markdown editing always available as a fallback

### Runtime

* macOS laptop
* Local Git repository for version history
* No remote push required

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

* Entry point for all new information
* No classification required at capture time

**Rules**

* Nothing is created outside `inbox/`
* Files are expected to move out
* Messy is acceptable

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

### 8.2 `ideas/` — Concepts & Thinking

**Purpose**

* Atomic ideas
* Mental models
* Insights and hypotheses

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

* Work with a defined outcome
* Active or paused execution

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

* Context and history about people
* Follow-ups and relationship memory

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

* Life administration
* System notes
* Processes and logistics

---

## 9. Slash Commands

### 9.1 `/note <content>`

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

* `ai_generated: false` because the content originates from the user
* `ai_generated: true` is reserved for AI-synthesized notes (e.g., summaries, connections generated from existing notes)

---

### 9.2 `/triage [file|all]`

**Purpose**: AI-assisted classification and routing of inbox items.

**Behavior**:

* If a specific file path is given, classifies that file
* If `all` or no argument is provided, processes all files in `inbox/`

**Classification output** (per file):

| Field | Description |
|-------|-------------|
| Target bucket | One of: `ideas`, `projects`, `people`, `admin` |
| `type` value | Appropriate type for the target bucket |
| Suggested tags | List of relevant tags |
| Confidence score | Float 0.0–1.0 |

**Routing logic**:

* High confidence (> 0.6): auto-filed to target bucket, frontmatter updated with classification results
* Low confidence (<= 0.6): added to review queue — presents suggestion to user, asks for confirmation or override

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

### 9.3 `/search <query>`

**Purpose**: Full-text retrieval across the entire knowledge base.

**Behavior**:

* Searches across all files: contents, filenames, and YAML frontmatter
* Returns matching files with relevant context snippets
* Ordered by relevance

**Scope**: All directories (`inbox/`, `ideas/`, `projects/`, `people/`, `admin/`)

---

## 10. Metadata Schema

### Required (all notes)

```yaml
---
type: unknown | idea | project | person | admin
captured_at: ISO-8601 timestamp
---
```

### Optional (recommended)

```yaml
source: claude-code
tags: []
status: active | paused | done
confidence: 0.0–1.0
ai_generated: true | false
```

### AI Provenance Rule

If a note is AI-created or AI-synthesized, it **must** include:

```yaml
ai_generated: true
```

User-authored content captured via `/note` is marked `ai_generated: false`.

---

## 11. Search & Retrieval

* Global full-text search across file contents, filenames, and YAML frontmatter
* Search is the primary retrieval mechanism
* Invoked via the `/search` slash command

---

## 12. Versioning & Safety

* Local Git repository for version history
* Commits after significant operations (note creation, triage moves)
* No remote push required (user may optionally configure a remote)
* Version history enables recovery of any previous state

---

## 13. Failure Tolerance

Tolerated failures:

* Tool abandonment (Claude Code disappears)
* Git corruption (files remain as plain Markdown)

Mitigation:

* Plain-text recoverability — all data is readable Markdown
* Local Git history — provides point-in-time recovery
* Standard macOS backup (Time Machine or equivalent) for hardware failure

---

## 14. Guiding Principles

* Files over databases
* Buckets over rigid hierarchies
* Metadata over schemas
* Explicit movement over hidden automation
* **Trust over convenience**
