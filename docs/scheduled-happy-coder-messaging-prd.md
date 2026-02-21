Here’s the **PRD updated cleanly and precisely** to reflect the new **interactive vault directory structure** and to remove `notes/` entirely.

This version is internally consistent and ready to hand to an engineer.

---

```markdown
# PRD: Scheduled HappyCoder Message Creation & Delivery  
(Shared Vault, Partitioned Writes, Explicit Notifications)

## Document Status
**Status:** Approved  
**Owner:** Patrick  
**Audience:** Engineers / Operators  
**Last Updated:** 2026-01-23

---

## 1. Overview

This document defines requirements and implementation details for a **server-resident HappyCoder + Claude Code system** that:

1. Runs **continuously** so a mobile client can connect at any time.
2. Uses a **single shared workspace and Obsidian vault**.
3. Allows both interactive and automated Claude usage against the same file tree.
4. Enforces **strict write boundaries** inside the vault to prevent conflicts.
5. Generates **scheduled, proactive Claude outputs** (daily and weekly).
6. Writes automated outputs only into **designated automation directories**.
7. Ensures **Claude responses appear in the shared chat history**.
8. Sends **deterministic push notifications** for automation outcomes.
9. Prevents Claude session corruption or nondeterministic behavior.

The system is **headless**, **fault-tolerant**, and **operable via systemd**, with no custom UI.

---

## 2. Goals & Non-Goals

### Goals
- Always-on HappyCoder session for interactive mobile use
- Automation and interactive access to the **same vault**
- Clear **read/write separation** inside the vault
- Automated daily and weekly Markdown note generation
- Predictable scheduling in **America/Los_Angeles (PST/PDT)**
- Deterministic notification behavior
- Minimal locking; no filesystem contention

### Non-Goals
- Multi-user support
- iOS support
- CRDT or real-time collaborative editing
- Server-side UI
- Zero-knowledge encryption of live vault files

---

## 3. System Architecture

### High-Level Components

| Component | Responsibility |
|---------|----------------|
| HappyCoder (interactive) | Mobile-driven Claude interaction |
| HappyCoder (automation) | Scheduled Claude execution |
| Claude Code CLI | LLM execution & session persistence |
| systemd timers | Scheduling |
| Obsidian vault | Persistent Markdown store |
| Syncthing | Cross-device file sync |
| Happy push | User notifications |

---

## 4. Workspace & Vault Model

### Single Shared Workspace
- One Claude workspace directory
- One `.claude/` session store
- One Obsidian vault root
- All Claude executions append to the **same conversation history**

### Vault Root Structure

```

/srv/workspace/ObsidianVault/  
├── inbox/ # interactive READ/WRITE  
├── ideas/ # interactive READ/WRITE  
├── projects/ # interactive READ/WRITE  
├── people/ # interactive READ/WRITE  
├── admin/ # interactive READ/WRITE  
├── daily/  
│ ├── manual/ # interactive READ/WRITE  
│ └── auto/ # automation WRITE, interactive READ  
├── weekly/  
│ ├── manual/ # interactive READ/WRITE  
│ └── auto/ # automation WRITE, interactive READ  
└── .obsidian/

```

> **Note:** There is intentionally **no `notes/` directory**.  
> All interactive content lives in the domain-specific folders above.

---

## 5. Read / Write Rules (CRITICAL)

### Automation Agent
- **READ:** entire vault
- **WRITE:** only to:
  - `daily/auto/`
  - `weekly/auto/`
- **MUST NOT:**
  - Modify or delete any other vault files
  - Overwrite existing automation files

### Interactive Agent
- **READ:** entire vault (including automation output)
- **WRITE:** anywhere **except**:
  - `daily/auto/`
  - `weekly/auto/`
- **MUST NOT:**
  - Edit or delete automation-generated files

These rules are enforced by **prompt discipline and scripting**, not filesystem ACLs.

---

## 6. Claude Session Execution Model

### Shared Session Context
- Interactive and automation runs use the **same Claude session**
- Automation launches Claude using:
  - the same workspace
  - `--continue` (or equivalent) to append to the existing conversation

### Chat Visibility Guarantee
- **Every automation run produces a Claude response**
- That response is:
  - appended to the shared session
  - synced by HappyCoder
  - visible in the mobile chat history

No additional steps are required for **chat visibility**.

---

## 7. Locking & Concurrency Control

### Execution Lock
- Path: `/srv/locks/claude-exec.lock`
- Mechanism: `flock`

### Rules
1. Any Claude execution **must acquire the execution lock**
2. Interactive usage has priority
3. Automation:
   - Attempts a **non-blocking** lock
   - If lock is held → **skip execution**
   - Must never wait
4. At most **one Claude Code process** may run at a time

### Rationale
Claude Code sessions are not safe for concurrent execution, even with
partitioned filesystem writes.

---

## 8. Scheduling Requirements

### Timezone
- Server timezone set to **America/Los_Angeles**
- systemd timers follow PST/PDT automatically

### Daily Automation
- Schedule: every day at **07:30**
- Output:
```

daily/auto/daily-summary-YYYY-MM-DD.md

```

### Weekly Automation
- Schedule: Sundays at **08:00**
- Output:
```

weekly/auto/weekly-summary-YYYY-[Www.md](http://www.md/)

````

---

## 9. Output Specifications

### Daily Summary
```yaml
---
type: daily-summary
date: YYYY-MM-DD
generated_by: happy-automation
---
````

Sections:

1. What changed today
    
2. Open loops / TODO
    
3. Next actions for tomorrow
    
4. Risks / blockers
    
5. Questions for Patrick
    

### Weekly Summary

```yaml
---
type: weekly-summary
week: YYYY-Www
generated_by: happy-automation
---
```

Sections:

1. Highlights
    
2. Progress by theme
    
3. Open loops / TODO
    
4. Next actions
    
5. Questions for Patrick
    

---

## 10. Notification Semantics (MANDATORY)

### Chat Messages vs. Push Notifications

- Claude responses **always appear in chat**
    
- Push notifications are **not guaranteed** for new chat messages
    

### Notification Policy

Automation **MUST explicitly trigger notifications** using `happy notify`.

### Required Notifications

|Outcome|Notification|
|---|---|
|Success|“✅ Daily/Weekly summary written …”|
|Skip|“⚠️ Skipped: interactive session active”|
|Failure|“❌ Failed: reason”|

---

## 11. Reliability & Failure Handling

### Atomic Writes

- Automation writes to a temp file in the target directory
    
- Validates file existence and non-empty content
    
- Atomic rename to final filename
    

### Idempotency

- If output file already exists:
    
    - Skip run
        
    - Notify user
        

### Crash Recovery

- systemd restarts HappyCoder
    
- Locks released automatically on process exit
    
- Next scheduled run proceeds normally
    

---

## 12. Deployment Requirements

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
    

---

## 13. Out of Scope (Future Enhancements)

- Filesystem-level ACL enforcement
    
- Automation queueing instead of skipping
    
- Monthly / quarterly summaries
    
- Dynamic timezone detection from mobile
    
- Multi-user vaults
    

---

## 14. Acceptance Criteria

- Interactive agent reads/writes only approved directories
    
- Automation writes only to `daily/auto` and `weekly/auto`
    
- Automation responses appear in shared chat
    
- Explicit push notifications fire for every automation run
    
- No concurrent Claude execution observed over sustained use
    

---

## 15. Final Notes

This design enforces **semantic ownership of directories** rather than  
filesystem isolation.

**Directory write boundaries, single-execution locking, and explicit  
notifications are non-negotiable.**

Approved for implementation.

```

---

If you want next, I can:
- Add **example prompts** that explicitly encode these directory rules
- Produce a **preflight guard script** that fails fast if Claude writes outside allowed paths
- Generate a **README.md** that explains this vault layout to future-you

Just say which.
```