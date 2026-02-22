# Phase 2 Design: Daily/Weekly Summary Agents with PydanticAI

> **Status:** Approved
> **Date:** 2026-02-21
> **Scope:** Phase 2 — Convert daily/weekly summary automation from `claude --print` to PydanticAI agents
> **Approach:** Same bottom-up pattern as Phase 1 (models → tools → agent → CLI → bash)

---

## What Changes, What Stays

**Stays as-is:**
- Systemd timers and schedules (07:30 daily, Sun 08:00 weekly)
- `.claude/commands/daily.md` and `weekly.md` slash commands for interactive use
- `happy notify` notification patterns
- flock concurrency, idempotency checks, atomic write logic in bash
- Vault directory structure and summary file locations
- `install.sh` (venv setup already handles `pip install -e`)
- Systemd service units (already have `ANTHROPIC_API_KEY` via `EnvironmentFile`)

**Modified:**
- `daily-summary.sh` — calls `python3 agents/run_summary.py daily` instead of `claude --continue --print`
- `weekly-summary.sh` — calls `python3 agents/run_summary.py weekly` instead of `claude --continue --print`

**New:**
- `models/summary.py` — DailySummary, WeeklySummary, ThemeProgress, SummarySection
- `tools/vault_scan.py` — find_recent_files, read_daily_summaries
- `agents/summary_agent.py` — single PydanticAI agent with union output type
- `agents/run_summary.py` — CLI entry point (daily|weekly)
- `config/prompts/summary_system.md` — system prompt for summary generation
- Tests for all of the above

**Key decisions:**
- Summaries write to vault files only (no HappyCoder chat visibility)
- Changed files pre-computed in Python via filesystem timestamps (no agent tools needed)
- Structured Pydantic output rendered to markdown (enables future features)
- Single agent with two output types (DailySummary | WeeklySummary), different prompts at call time

---

## Data Models

```python
# models/summary.py
from pydantic import BaseModel, Field

class SummarySection(BaseModel):
    """A single section with bullet points."""
    items: list[str] = Field(description="Concise bullet points for this section")

class ThemeProgress(BaseModel):
    """Progress update grouped by project or area."""
    theme: str = Field(description="Project or area name, e.g. 'hawaii-2026'")
    updates: list[str] = Field(description="What happened on this theme")

class DailySummary(BaseModel):
    what_changed: SummarySection
    open_loops: SummarySection
    next_actions: SummarySection
    risks_blockers: SummarySection
    questions_for_patrick: SummarySection

class WeeklySummary(BaseModel):
    highlights: SummarySection
    progress_by_theme: list[ThemeProgress]
    open_loops: SummarySection
    next_actions: SummarySection
    questions_for_patrick: SummarySection
```

Both models get a `render_markdown(date_or_week: str) -> str` method that produces the final file content including YAML frontmatter matching the existing format:

```yaml
---
type: daily-summary  # or weekly-summary
date: 2026-02-21     # or week: 2026-W08
generated_by: happy-automation
ai_generated: true
---
```

---

## Change Detection

```python
# tools/vault_scan.py

def find_recent_files(vault_dir: Path, since_hours: int = 24) -> list[Path]:
    """Walk vault, return files modified within since_hours.
    Excludes: .venv/, .git/, _assets/, _system/summaries/"""

def read_daily_summaries(vault_dir: Path, days: int = 7) -> list[tuple[str, str]]:
    """Read the last N daily summaries for weekly rollup.
    Returns list of (date, content) tuples, sorted chronologically."""
```

**Daily prompt building:**
- `find_recent_files(vault_dir, since_hours=24)` finds changed files
- Read contents (capped at 3KB each, same as triage)
- Pass file list + contents in prompt

**Weekly prompt building:**
- `read_daily_summaries(vault_dir, days=7)` grabs daily summaries as primary context
- `find_recent_files(vault_dir, since_hours=168)` supplements with any changes dailies missed
- Both passed in prompt

---

## Agent

```python
# agents/summary_agent.py
from pydantic_ai import Agent
from config.agent_config import TRIAGE_MODEL

summary_agent = Agent(
    TRIAGE_MODEL,  # reuse same model config
    output_type=...,  # set per-call via overrides or union type
    instructions=...,  # from config/prompts/summary_system.md
    name='summary',
    retries=2,
    defer_model_check=True,
)
```

The agent has **no tools** — all context is pre-computed and passed in the prompt. This keeps it fast and cheap (single LLM call, no tool round-trips).

Output type switching: use `summary_agent.override(output_type=DailySummary)` or `WeeklySummary` at call time.

**System prompt** (`config/prompts/summary_system.md`): instructs the agent to analyze vault changes and produce structured summary sections. Separate sections for daily vs weekly guidance.

---

## CLI Entry Point

```
python3 agents/run_summary.py daily    # daily summary
python3 agents/run_summary.py weekly   # weekly summary
```

**Flow:**
1. Parse args (daily|weekly)
2. Determine output path and check idempotency (skip if file exists)
3. Pre-compute changed files via `find_recent_files` / `read_daily_summaries`
4. Build prompt with file contents
5. `log_run_start()` to agents.db
6. Run agent with appropriate output type override
7. Render structured output to markdown via `render_markdown()`
8. Write to temp file, atomic rename to final path
9. `log_run_complete()` with token/cost data from `result.usage()`
10. Exit 0 on success, 1 on error

---

## Bash Integration

**`daily-summary.sh` changes:**

```bash
# Replace: claude --continue --print "Read the vault..."
# With:
source "${VAULT_DIR}/.venv/bin/activate"
python3 "${VAULT_DIR}/agents/run_summary.py" daily
RESULT=$?
```

Everything else in the bash scripts stays: idempotency check, flock, `happy notify`, error trap. Same pattern as `inbox-triage.sh`.

**`weekly-summary.sh`** — identical change, `daily` → `weekly`.

---

## Testing Strategy

**Unit tests (no API, no filesystem beyond tmp):**
- `test_summary_models.py` — Model validation, `render_markdown()` produces correct frontmatter and section headings
- `test_vault_scan.py` — `find_recent_files` respects time window and exclusions, `read_daily_summaries` reads correct files in chronological order

**Agent tests (TestModel, no API):**
- `test_summary_agent.py` — Agent definition (name, retries), output type override works, TestModel returns valid DailySummary/WeeklySummary

**Integration tests (temp filesystem):**
- `test_run_summary.py` — CLI arg parsing, atomic write, agents.db logging, idempotency skip
- `test_summary_flow.py` — Full flow with temp vault containing recent files, run agent, verify rendered markdown and db record

---

## Rollback

Save `daily-summary.sh.bak` and `weekly-summary.sh.bak` before modifying. Claude Code slash commands remain for manual fallback.
