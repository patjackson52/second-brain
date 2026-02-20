# Phase 1 Design: Structured Triage with PydanticAI

> **Status:** Approved
> **Date:** 2026-02-19
> **Scope:** Phase 1 only (from pydantic-ai-integration-plan.md v3)
> **Approach:** Bottom-up (models → state → tools → agent → CLI → bash)
> **Parent Spec:** /Users/patrick/Downloads/pydantic-ai-integration-plan.md

---

## What Changes, What Stays

**Stays as-is:**
- `inbox-watcher.sh` — Syncthing event polling, debouncing, triggering
- `_system/routes.yaml` — PARA config, routing rules
- `_system/prompts/triage_para.md` — decision tree prompt (loaded by agent)
- `.claude/commands/triage.md` — interactive slash command for manual use
- Vault directory structure, frontmatter conventions, processing-log format
- `flock` concurrency, systemd timers/services

**Modified:**
- `inbox-triage.sh` — calls `python3 agents/run_triage.py` instead of `claude --print "/triage all"`
- `install.sh` — adds Python venv setup, deploys Python files, creates state dir

**New:**
- `pyproject.toml` — dependencies (pydantic-ai, dbos-transact)
- `agents/triage_agent.py` — PydanticAI agent definition
- `agents/run_triage.py` — CLI entry point
- `models/triage.py` — TriageBatch, TriageDecision, PARADestination
- `state/db.py`, `state/runs.py` — SQLite state layer
- `tools/vault_read.py`, `tools/vault_write.py` — vault operations
- `config/agent_config.py` — model selection, DBOS config, path config
- `config/prompts/triage_system.md` — agent system prompt (derived from triage_para.md)
- `tests/` — unit and integration tests

**Key decision:** The PydanticAI agent replaces Claude Code for automated triage. The `.claude/commands/triage.md` slash command remains for interactive use.

---

## Data Models

```python
# models/triage.py
from pydantic import BaseModel, Field
from enum import Enum

class PARADestination(str, Enum):
    PROJECTS_ACTIVE = "1_projects/active"
    PROJECTS_WAITING = "1_projects/waiting"
    AREAS = "2_areas"
    RESOURCES = "3_resources"
    ARCHIVE = "4_archive"
    PEOPLE = "5_people"

class TriageDecision(BaseModel):
    filename: str             # Original filename in 0_inbox/
    destination: PARADestination
    subdirectory: str | None  # e.g., "Health" under 2_areas
    confidence: float         # 0.0-1.0, threshold 0.7 from routes.yaml
    reasoning: str
    suggested_rename: str | None
    tags: list[str]

class TriageBatch(BaseModel):
    decisions: list[TriageDecision]
    skipped: list[str]        # Files that couldn't be processed
```

**Separation:** Agent returns `TriageBatch` (decisions only). `run_triage.py` executes moves, frontmatter updates, and processing-log entries. This makes agent testable with `TestModel` without touching filesystem.

---

## State Layer

```python
# state/db.py
# - get_connection() → SQLite with WAL mode, foreign keys
# - init_schema() → CREATE TABLE IF NOT EXISTS agent_runs

# state/runs.py
# - log_run_start(run_id, agent_type) → INSERT with status='running'
# - log_run_complete(run_id, output_summary, tokens_in, tokens_out, cost_usd, duration_ms)
# - log_run_error(run_id, error_message)
```

**Path handling:**

```python
# config/agent_config.py
import os
from pathlib import Path

VAULT_DIR = Path(os.environ.get("SECOND_BRAIN_VAULT", "/home/ubuntu/second-brain"))
STATE_DB_PATH = Path(os.environ.get("SECOND_BRAIN_STATE_DB", "/home/ubuntu/second-brain-state/agents.db"))
```

Env vars for local dev, defaults for VM. No code changes between environments.

**Logged per run:** run_id (UUID), agent_type ("triage"), status, input_summary (filenames), output_summary (decisions JSON), tokens_in/out, cost_usd, duration_ms.

---

## Tools & Agent

**Agent has read-only tools** (for gathering context during decision-making):

```python
# tools/vault_read.py
# - read_file(path) → file content (capped at 3KB)
# - list_directory(path) → directory listing (capped at 100 entries)
# - read_routes() → parsed routes.yaml content
```

**Write tools exist but are NOT registered on the agent** (called by run_triage.py):

```python
# tools/vault_write.py
# - move_file(source, destination) → atomic move (.tmp + mv)
# - update_frontmatter(path, fields: dict) → merge into existing frontmatter
# - append_processing_log(entry) → append to _system/processing-log.md
```

**Agent definition:**

```python
# agents/triage_agent.py
triage_agent = Agent(
    'anthropic:claude-sonnet-4-5',
    output_type=TriageBatch,
    instructions=...,  # from config/prompts/triage_system.md
    name='triage',
    retries=2,
)

# Read-only tools registered on agent
@triage_agent.tool
async def read_routes(ctx: RunContext) -> str: ...

@triage_agent.tool
async def list_vault_directories(ctx: RunContext) -> str: ...
```

**DBOS wrapping:**

```python
from pydantic_ai.durable_exec.dbos import DBOSAgent

durable_triage = DBOSAgent(triage_agent)

async def triage_inbox(files: list[Path]) -> TriageBatch:
    # Read file contents (capped at 3KB each)
    # Build prompt with routes + directory listing + file contents
    result = await durable_triage.run(prompt)
    return result.output
```

**System prompt:** Derived from `triage_para.md` but adapted for structured output — instructs agent to return `TriageDecision` objects instead of executing file moves. PARA decision tree (Q1→Q5) stays identical.

---

## CLI Entry Point & Bash Integration

**`agents/run_triage.py`:**

```
Called by: python3 agents/run_triage.py --files note1.md note2.md
Or:        python3 agents/run_triage.py --all

Flow:
1. Parse args (--files or --all to glob 0_inbox/*.md)
2. Exit 0 early if no files found
3. log_run_start()
4. Call triage_inbox(files) → TriageBatch
5. For each decision:
   - confidence >= 0.7: move file, update frontmatter, log to processing-log
   - confidence < 0.7: update frontmatter with needs_triage: true, leave in inbox
6. log_run_complete() with token/cost data
7. Exit codes: 0=success, 2=some items need review, 1=error
8. Print summary to stdout
```

**`inbox-triage.sh` change:**

```bash
# Replace: claude --print "/triage all"
# With:
source "${SCRIPT_DIR}/../.venv/bin/activate"
python3 "${SCRIPT_DIR}/../agents/run_triage.py" --all
RESULT=$?
```

Everything else in inbox-triage.sh stays: flock, notifications, error handling.

**`install.sh` additions:**

```bash
python3 -m venv "${VAULT_DIR}/.venv"
"${VAULT_DIR}/.venv/bin/pip" install -e "${VAULT_DIR}"
mkdir -p /home/ubuntu/second-brain-state
"${VAULT_DIR}/.venv/bin/python3" -c \
    "from state.db import get_connection, init_schema; init_schema(get_connection())"
```

---

## Testing Strategy

**Unit tests (no API, no filesystem):**
- `tests/test_models.py` — Pydantic model validation
- `tests/test_state_db.py` — SQLite schema init idempotent, run logging CRUD

**Agent tests (TestModel, no API):**
- `tests/test_triage_agent.py` — Agent returns valid TriageBatch, tools registered, retry behavior

**Integration tests (temp filesystem, mock or real API):**
- `tests/test_triage_flow.py` — Full flow with temp vault directory:
  - Files moved to correct destinations
  - Frontmatter updated
  - Processing-log appended
  - agent_runs row created
  - Low-confidence items stay in inbox

**Test infrastructure:**
- `conftest.py` with fixtures for temp vault, temp SQLite DB, env var overrides
- `pytest` as test runner

---

## Rollback & Deployment

**Rollback:** Save `inbox-triage.sh.bak` before modifying. Claude Code slash command always available for manual fallback. SQLite DB is additive — deleting it has zero impact.

**Deployment sequence:**
1. `git pull` on VM
2. `install.sh` (venv, deps, state dir, schema)
3. Manual test with a file in inbox
4. Verify agents.db row
5. Restart inbox-watcher service
6. Monitor 48h

**Go/no-go:**
- All tests pass locally with TestModel
- At least one successful real API run locally
- inbox-triage.sh.bak saved on VM
- ANTHROPIC_API_KEY set in systemd environment
