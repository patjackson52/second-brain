# Phase 2: Daily/Weekly Summary Agents — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace `claude --continue --print` in daily/weekly summary scripts with PydanticAI agents producing structured, typed output with token/cost tracking.

**Architecture:** Single `summary_agent` with no tools. Python pre-computes changed files via filesystem timestamps and passes contents in prompt. Agent returns `DailySummary` or `WeeklySummary` (structured Pydantic models), which get rendered to markdown and written to vault files. Bash scripts simplified to: flock + call Python + notify.

**Tech Stack:** PydanticAI, Pydantic, pytest, SQLite (existing agents.db), Python 3.9+ (local) / 3.12 (VM)

---

### Task 1: Set Up Worktree

**Files:**
- Modify: `.worktrees/` (git worktree directory)

**Step 1: Create worktree**

Use `superpowers:using-git-worktrees` to create an isolated worktree on branch `feature/summary-agents-phase2`.

**Step 2: Verify tests pass in worktree**

Run: `cd .worktrees/summary-agents-phase2 && pip install -e . && pytest tests/ -v`
Expected: 52 tests pass (all Phase 1 tests)

**Step 3: Commit .gitignore if needed**

If worktree directory wasn't already ignored, commit the change.

---

### Task 2: Data Models

**Files:**
- Create: `models/summary.py`
- Create: `tests/test_summary_models.py`

**Step 1: Write the failing tests**

```python
# tests/test_summary_models.py
from __future__ import annotations

import pytest

from models.summary import DailySummary, SummarySection, ThemeProgress, WeeklySummary


class TestSummarySection:
    def test_valid_section(self):
        s = SummarySection(items=["Item one", "Item two"])
        assert len(s.items) == 2

    def test_empty_section(self):
        s = SummarySection(items=[])
        assert s.items == []


class TestThemeProgress:
    def test_valid_theme(self):
        t = ThemeProgress(theme="hawaii-2026", updates=["Booked flights"])
        assert t.theme == "hawaii-2026"
        assert len(t.updates) == 1


class TestDailySummary:
    def test_valid_daily(self):
        section = SummarySection(items=["Changed file X"])
        summary = DailySummary(
            what_changed=section,
            open_loops=section,
            next_actions=section,
            risks_blockers=section,
            questions_for_patrick=section,
        )
        assert isinstance(summary, DailySummary)

    def test_render_markdown_has_frontmatter(self):
        section = SummarySection(items=["Item"])
        summary = DailySummary(
            what_changed=section,
            open_loops=section,
            next_actions=section,
            risks_blockers=section,
            questions_for_patrick=section,
        )
        md = summary.render_markdown("2026-02-21")
        assert "type: daily-summary" in md
        assert "date: 2026-02-21" in md
        assert "generated_by: happy-automation" in md
        assert "ai_generated: true" in md

    def test_render_markdown_has_sections(self):
        summary = DailySummary(
            what_changed=SummarySection(items=["File A updated"]),
            open_loops=SummarySection(items=["TODO X"]),
            next_actions=SummarySection(items=["Do Y"]),
            risks_blockers=SummarySection(items=[]),
            questions_for_patrick=SummarySection(items=["Q1?"]),
        )
        md = summary.render_markdown("2026-02-21")
        assert "## What Changed Today" in md
        assert "- File A updated" in md
        assert "## Open Loops / TODO" in md
        assert "## Next Actions for Tomorrow" in md
        assert "## Risks / Blockers" in md
        assert "## Questions for Patrick" in md

    def test_render_markdown_empty_section_shows_none(self):
        section = SummarySection(items=[])
        summary = DailySummary(
            what_changed=section,
            open_loops=section,
            next_actions=section,
            risks_blockers=section,
            questions_for_patrick=section,
        )
        md = summary.render_markdown("2026-02-21")
        assert "- No items" in md or "- None" in md


class TestWeeklySummary:
    def test_valid_weekly(self):
        section = SummarySection(items=["Item"])
        summary = WeeklySummary(
            highlights=section,
            progress_by_theme=[ThemeProgress(theme="test", updates=["Did thing"])],
            open_loops=section,
            next_actions=section,
            questions_for_patrick=section,
        )
        assert isinstance(summary, WeeklySummary)

    def test_render_markdown_has_frontmatter(self):
        section = SummarySection(items=["Item"])
        summary = WeeklySummary(
            highlights=section,
            progress_by_theme=[],
            open_loops=section,
            next_actions=section,
            questions_for_patrick=section,
        )
        md = summary.render_markdown("2026-W08")
        assert "type: weekly-summary" in md
        assert "week: 2026-W08" in md
        assert "generated_by: happy-automation" in md

    def test_render_markdown_has_theme_progress(self):
        section = SummarySection(items=["Item"])
        summary = WeeklySummary(
            highlights=section,
            progress_by_theme=[
                ThemeProgress(theme="hawaii-2026", updates=["Booked flights", "Reserved hotel"]),
                ThemeProgress(theme="second-brain", updates=["Added triage agent"]),
            ],
            open_loops=section,
            next_actions=section,
            questions_for_patrick=section,
        )
        md = summary.render_markdown("2026-W08")
        assert "## Progress by Theme" in md
        assert "### hawaii-2026" in md
        assert "- Booked flights" in md
        assert "### second-brain" in md
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_summary_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'models.summary'`

**Step 3: Write the implementation**

```python
# models/summary.py
from __future__ import annotations

from pydantic import BaseModel, Field


class SummarySection(BaseModel):
    """A single summary section with bullet points."""
    items: list[str] = Field(description="Concise bullet points for this section")

    def render_bullets(self) -> str:
        if not self.items:
            return "- None\n"
        return "".join(f"- {item}\n" for item in self.items)


class ThemeProgress(BaseModel):
    """Progress update grouped by project or area."""
    theme: str = Field(description="Project or area name, e.g. 'hawaii-2026'")
    updates: list[str] = Field(description="What happened on this theme")


class DailySummary(BaseModel):
    """Structured daily summary of vault activity."""
    what_changed: SummarySection = Field(description="Files created or modified today")
    open_loops: SummarySection = Field(description="Pending items and unresolved work")
    next_actions: SummarySection = Field(description="Concrete next steps for tomorrow")
    risks_blockers: SummarySection = Field(description="Anything stalled or at risk")
    questions_for_patrick: SummarySection = Field(description="Decisions needed or clarifications")

    def render_markdown(self, date: str) -> str:
        return (
            f"---\n"
            f"type: daily-summary\n"
            f"date: {date}\n"
            f"generated_by: happy-automation\n"
            f"ai_generated: true\n"
            f"---\n\n"
            f"## What Changed Today\n\n{self.what_changed.render_bullets()}\n"
            f"## Open Loops / TODO\n\n{self.open_loops.render_bullets()}\n"
            f"## Next Actions for Tomorrow\n\n{self.next_actions.render_bullets()}\n"
            f"## Risks / Blockers\n\n{self.risks_blockers.render_bullets()}\n"
            f"## Questions for Patrick\n\n{self.questions_for_patrick.render_bullets()}"
        )


class WeeklySummary(BaseModel):
    """Structured weekly summary of vault activity."""
    highlights: SummarySection = Field(description="Key accomplishments and notable events")
    progress_by_theme: list[ThemeProgress] = Field(description="Updates grouped by project/area")
    open_loops: SummarySection = Field(description="Unresolved items carried forward")
    next_actions: SummarySection = Field(description="Priority actions for the coming week")
    questions_for_patrick: SummarySection = Field(description="Decisions needed or clarifications")

    def render_markdown(self, week: str) -> str:
        theme_section = ""
        if self.progress_by_theme:
            for tp in self.progress_by_theme:
                theme_section += f"### {tp.theme}\n\n"
                theme_section += "".join(f"- {u}\n" for u in tp.updates)
                theme_section += "\n"
        else:
            theme_section = "- None\n\n"

        return (
            f"---\n"
            f"type: weekly-summary\n"
            f"week: {week}\n"
            f"generated_by: happy-automation\n"
            f"ai_generated: true\n"
            f"---\n\n"
            f"## Highlights\n\n{self.highlights.render_bullets()}\n"
            f"## Progress by Theme\n\n{theme_section}"
            f"## Open Loops / TODO\n\n{self.open_loops.render_bullets()}\n"
            f"## Next Actions\n\n{self.next_actions.render_bullets()}\n"
            f"## Questions for Patrick\n\n{self.questions_for_patrick.render_bullets()}"
        )
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_summary_models.py -v`
Expected: All pass

**Step 5: Commit**

```bash
git add models/summary.py tests/test_summary_models.py
git commit -m "feat: add DailySummary and WeeklySummary data models with render_markdown"
```

---

### Task 3: Vault Scan Tools

**Files:**
- Create: `tools/vault_scan.py`
- Create: `tests/test_vault_scan.py`

**Step 1: Write the failing tests**

```python
# tests/test_vault_scan.py
from __future__ import annotations

import os
import time

import pytest

from tools.vault_scan import find_recent_files, read_daily_summaries


class TestFindRecentFiles:
    def test_finds_recently_modified_files(self, tmp_vault):
        note = tmp_vault / "1_projects" / "active" / "test.md"
        note.write_text("# Test")
        files = find_recent_files(tmp_vault, since_hours=1)
        assert note in files

    def test_excludes_venv(self, tmp_vault):
        venv_dir = tmp_vault / ".venv" / "lib"
        venv_dir.mkdir(parents=True)
        (venv_dir / "pkg.py").write_text("x = 1")
        files = find_recent_files(tmp_vault, since_hours=1)
        names = [f.name for f in files]
        assert "pkg.py" not in names

    def test_excludes_assets(self, tmp_vault):
        assets_dir = tmp_vault / "_assets" / "images"
        assets_dir.mkdir(parents=True)
        (assets_dir / "photo.jpg").write_bytes(b"\xff\xd8")
        files = find_recent_files(tmp_vault, since_hours=1)
        names = [f.name for f in files]
        assert "photo.jpg" not in names

    def test_excludes_summary_output(self, tmp_vault):
        summ_dir = tmp_vault / "_system" / "summaries" / "daily" / "auto"
        summ_dir.mkdir(parents=True)
        (summ_dir / "daily-summary-2026-02-21.md").write_text("# Summary")
        files = find_recent_files(tmp_vault, since_hours=1)
        names = [f.name for f in files]
        assert "daily-summary-2026-02-21.md" not in names

    def test_excludes_old_files(self, tmp_vault):
        note = tmp_vault / "0_inbox" / "old.md"
        note.write_text("# Old")
        # Set mtime to 48 hours ago
        old_time = time.time() - (48 * 3600)
        os.utime(note, (old_time, old_time))
        files = find_recent_files(tmp_vault, since_hours=24)
        assert note not in files

    def test_returns_sorted(self, tmp_vault):
        (tmp_vault / "0_inbox" / "b.md").write_text("# B")
        (tmp_vault / "0_inbox" / "a.md").write_text("# A")
        files = find_recent_files(tmp_vault, since_hours=1)
        md_names = [f.name for f in files if f.suffix == ".md"]
        assert md_names == sorted(md_names)


class TestReadDailySummaries:
    def test_reads_existing_summaries(self, tmp_vault):
        summ_dir = tmp_vault / "_system" / "summaries" / "daily" / "auto"
        summ_dir.mkdir(parents=True)
        (summ_dir / "daily-summary-2026-02-20.md").write_text("# Feb 20")
        (summ_dir / "daily-summary-2026-02-21.md").write_text("# Feb 21")
        results = read_daily_summaries(tmp_vault, days=7)
        assert len(results) == 2
        # Sorted chronologically
        assert results[0][0] <= results[1][0]

    def test_returns_empty_if_no_summaries(self, tmp_vault):
        results = read_daily_summaries(tmp_vault, days=7)
        assert results == []

    def test_limits_to_days_window(self, tmp_vault):
        summ_dir = tmp_vault / "_system" / "summaries" / "daily" / "auto"
        summ_dir.mkdir(parents=True)
        # Create summary with old date in filename
        (summ_dir / "daily-summary-2025-01-01.md").write_text("# Old")
        (summ_dir / "daily-summary-2026-02-21.md").write_text("# Today")
        results = read_daily_summaries(tmp_vault, days=7)
        # Should only include recent one (within 7 days of most recent)
        dates = [r[0] for r in results]
        assert "2025-01-01" not in dates
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_vault_scan.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.vault_scan'`

**Step 3: Write the implementation**

```python
# tools/vault_scan.py
from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

# Directories to exclude when scanning for recent changes
EXCLUDE_DIRS = {".venv", ".git", "__pycache__", "_assets", "node_modules"}
EXCLUDE_PREFIXES = ("_system/summaries",)

MAX_FILE_CONTENT = 3072  # 3KB per file, consistent with triage


def find_recent_files(vault_dir: Path, since_hours: int = 24) -> List[Path]:
    """Walk vault, return files modified within since_hours.

    Excludes: .venv/, .git/, _assets/, _system/summaries/, __pycache__/
    """
    cutoff = time.time() - (since_hours * 3600)
    results = []

    for path in vault_dir.rglob("*"):
        if not path.is_file():
            continue
        # Check exclusions
        rel = path.relative_to(vault_dir)
        parts = rel.parts
        if any(part in EXCLUDE_DIRS for part in parts):
            continue
        rel_str = str(rel)
        if any(rel_str.startswith(prefix) for prefix in EXCLUDE_PREFIXES):
            continue
        if path.name.startswith("."):
            continue
        # Check modification time
        if path.stat().st_mtime >= cutoff:
            results.append(path)

    return sorted(results)


def read_daily_summaries(
    vault_dir: Path, days: int = 7
) -> List[Tuple[str, str]]:
    """Read recent daily summaries for weekly rollup.

    Returns list of (date_str, content) tuples sorted chronologically.
    Only includes summaries within `days` of the most recent one.
    """
    summ_dir = vault_dir / "_system" / "summaries" / "daily" / "auto"
    if not summ_dir.is_dir():
        return []

    files = sorted(summ_dir.glob("daily-summary-*.md"))
    if not files:
        return []

    # Parse dates from filenames
    entries = []
    for f in files:
        # Extract date from "daily-summary-YYYY-MM-DD.md"
        stem = f.stem  # "daily-summary-2026-02-21"
        date_str = stem.replace("daily-summary-", "")
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            entries.append((date_str, f))
        except ValueError:
            continue

    if not entries:
        return []

    # Filter to within `days` of the most recent entry
    entries.sort(key=lambda x: x[0])
    most_recent = datetime.strptime(entries[-1][0], "%Y-%m-%d")
    cutoff = most_recent - timedelta(days=days)

    results = []
    for date_str, f in entries:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        if d >= cutoff:
            results.append((date_str, f.read_text()))

    return results
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_vault_scan.py -v`
Expected: All pass

**Step 5: Commit**

```bash
git add tools/vault_scan.py tests/test_vault_scan.py
git commit -m "feat: add vault scan tools for change detection"
```

---

### Task 4: Summary Agent Definition

**Files:**
- Create: `agents/summary_agent.py`
- Create: `config/prompts/summary_system.md`
- Create: `tests/test_summary_agent.py`

**Step 1: Write the system prompt**

```markdown
<!-- config/prompts/summary_system.md -->
You are a summary agent for a PARA-based personal knowledge management system.

You analyze recent vault activity and produce structured summaries.

## For Daily Summaries

Analyze the changed files provided and produce a summary with:
- **What Changed Today**: List files that were created, modified, or moved. Describe the changes concisely.
- **Open Loops / TODO**: Identify pending items, unfinished tasks, or items marked needs_triage.
- **Next Actions for Tomorrow**: Suggest concrete next steps based on current state.
- **Risks / Blockers**: Note anything stalled, overdue, or at risk.
- **Questions for Patrick**: Flag decisions needed, ambiguities, or strategic questions.

## For Weekly Summaries

Analyze the daily summaries and changed files for the week and produce:
- **Highlights**: Key accomplishments and notable events.
- **Progress by Theme**: Group updates by project or area name. Use existing project/area directory names as theme names.
- **Open Loops / TODO**: Unresolved items carried forward from the week.
- **Next Actions**: Priority actions for the coming week.
- **Questions for Patrick**: Decisions needed or clarifications.

## Rules

- Be concise — each bullet should be one clear sentence.
- Focus on actionable information, not filler.
- If no items exist for a section, return an empty items list.
- Use project/area names from the vault structure (e.g., "hawaii-2026", "Health").
- For weekly themes, only include themes that had actual activity.
```

**Step 2: Write the failing tests**

```python
# tests/test_summary_agent.py
from __future__ import annotations

import pytest
from pydantic_ai.models.test import TestModel

from agents.summary_agent import summary_agent
from models.summary import DailySummary, WeeklySummary


class TestSummaryAgentDefinition:
    def test_agent_has_correct_name(self):
        assert summary_agent.name == "summary"

    def test_agent_has_retries(self):
        assert summary_agent._max_result_retries == 2

    def test_agent_has_no_tools(self):
        tools = summary_agent._function_toolset.tools
        assert len(tools) == 0


class TestSummaryAgentRun:
    async def test_agent_returns_daily_summary(self):
        with summary_agent.override(model=TestModel(), output_type=DailySummary):
            result = await summary_agent.run("Summarize today's changes.")
            assert isinstance(result.output, DailySummary)

    async def test_agent_returns_weekly_summary(self):
        with summary_agent.override(model=TestModel(), output_type=WeeklySummary):
            result = await summary_agent.run("Summarize this week's changes.")
            assert isinstance(result.output, WeeklySummary)
```

**Step 3: Run tests to verify they fail**

Run: `pytest tests/test_summary_agent.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.summary_agent'`

**Step 4: Write the implementation**

```python
# agents/summary_agent.py
from __future__ import annotations

from pathlib import Path

from pydantic_ai import Agent

from config.agent_config import TRIAGE_MODEL
from models.summary import DailySummary


def _load_system_prompt() -> str:
    """Load the summary system prompt from config/prompts/."""
    prompt_path = Path(__file__).parent.parent / "config" / "prompts" / "summary_system.md"
    return prompt_path.read_text()


summary_agent = Agent(
    TRIAGE_MODEL,
    output_type=DailySummary,  # default; overridden per-call for weekly
    instructions=_load_system_prompt(),
    name="summary",
    retries=2,
    defer_model_check=True,
)
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/test_summary_agent.py -v`
Expected: All pass

**Step 6: Commit**

```bash
git add agents/summary_agent.py config/prompts/summary_system.md tests/test_summary_agent.py
git commit -m "feat: add summary agent definition with system prompt"
```

---

### Task 5: Summary Runner (Prompt Builder)

**Files:**
- Create: `agents/summary_runner.py`
- Create: `tests/test_summary_runner.py`

**Step 1: Write the failing tests**

```python
# tests/test_summary_runner.py
from __future__ import annotations

import pytest
from pydantic_ai.models.test import TestModel

from agents.summary_agent import summary_agent
from agents.summary_runner import build_daily_prompt, build_weekly_prompt, run_summary
from models.summary import DailySummary, WeeklySummary


class TestBuildDailyPrompt:
    def test_includes_file_contents(self, tmp_vault):
        note = tmp_vault / "0_inbox" / "test.md"
        note.write_text("# Test Note\n\nSome content.")
        prompt = build_daily_prompt([note], "2026-02-21")
        assert "test.md" in prompt
        assert "Test Note" in prompt
        assert "2026-02-21" in prompt

    def test_handles_empty_file_list(self, tmp_vault):
        prompt = build_daily_prompt([], "2026-02-21")
        assert "no files" in prompt.lower() or "No recent changes" in prompt


class TestBuildWeeklyPrompt:
    def test_includes_daily_summaries(self, tmp_vault):
        summ_dir = tmp_vault / "_system" / "summaries" / "daily" / "auto"
        summ_dir.mkdir(parents=True)
        (summ_dir / "daily-summary-2026-02-20.md").write_text("# Feb 20 summary")
        daily_summaries = [("2026-02-20", "# Feb 20 summary")]
        prompt = build_weekly_prompt([], daily_summaries, "2026-W08")
        assert "Feb 20 summary" in prompt
        assert "2026-W08" in prompt

    def test_includes_changed_files(self, tmp_vault):
        note = tmp_vault / "1_projects" / "active" / "test.md"
        note.write_text("# Project update")
        prompt = build_weekly_prompt([note], [], "2026-W08")
        assert "test.md" in prompt


class TestRunSummary:
    async def test_daily_returns_result(self, tmp_vault, monkeypatch):
        monkeypatch.setenv("SECOND_BRAIN_VAULT", str(tmp_vault))
        note = tmp_vault / "0_inbox" / "test.md"
        note.write_text("# Test note")

        with summary_agent.override(model=TestModel(), output_type=DailySummary):
            result = await run_summary("daily", [note], [], vault_dir=tmp_vault, date_str="2026-02-21")
            assert isinstance(result.output, DailySummary)

    async def test_weekly_returns_result(self, tmp_vault, monkeypatch):
        monkeypatch.setenv("SECOND_BRAIN_VAULT", str(tmp_vault))

        with summary_agent.override(model=TestModel(), output_type=WeeklySummary):
            result = await run_summary("weekly", [], [], vault_dir=tmp_vault, date_str="2026-W08")
            assert isinstance(result.output, WeeklySummary)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_summary_runner.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.summary_runner'`

**Step 3: Write the implementation**

```python
# agents/summary_runner.py
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

from models.summary import DailySummary, WeeklySummary

if TYPE_CHECKING:
    from pydantic_ai.run import AgentRunResult

MAX_FILE_CONTENT = 3072  # 3KB per file


def _read_file_content(path: Path) -> str:
    """Read file content, capped at MAX_FILE_CONTENT."""
    try:
        content = path.read_text(errors="replace")
        if len(content) > MAX_FILE_CONTENT:
            content = content[:MAX_FILE_CONTENT] + "\n[... truncated ...]"
        return content
    except Exception as e:
        return f"Error reading file: {e}"


def build_daily_prompt(files: List[Path], date_str: str) -> str:
    """Build the daily summary prompt from recently changed files."""
    if not files:
        return (
            f"Generate a daily summary for {date_str}.\n\n"
            "No recent changes detected in the vault. "
            "Note this in the summary and focus on any known open loops."
        )

    file_sections = []
    for f in files:
        rel = f.name
        content = _read_file_content(f)
        file_sections.append(f"### {rel}\n\n{content}")

    return (
        f"Generate a daily summary for {date_str}.\n\n"
        f"The following {len(files)} file(s) were recently changed:\n\n"
        + "\n\n---\n\n".join(file_sections)
    )


def build_weekly_prompt(
    files: List[Path],
    daily_summaries: List[Tuple[str, str]],
    week_str: str,
) -> str:
    """Build the weekly summary prompt from daily summaries and changed files."""
    parts = [f"Generate a weekly summary for {week_str}.\n"]

    if daily_summaries:
        parts.append(f"\n## Daily Summaries ({len(daily_summaries)} days)\n")
        for date_str, content in daily_summaries:
            parts.append(f"### {date_str}\n\n{content}\n\n---\n")

    if files:
        parts.append(f"\n## Additional Changed Files ({len(files)} files)\n")
        for f in files:
            content = _read_file_content(f)
            parts.append(f"### {f.name}\n\n{content}\n\n---\n")

    if not daily_summaries and not files:
        parts.append(
            "\nNo daily summaries or file changes found for this week. "
            "Note this in the summary."
        )

    return "".join(parts)


async def run_summary(
    mode: str,
    files: List[Path],
    daily_summaries: List[Tuple[str, str]],
    vault_dir: Optional[Path] = None,
    date_str: str = "",
) -> "AgentRunResult[DailySummary] | AgentRunResult[WeeklySummary]":
    """Run the summary agent. Returns full result for usage tracking."""
    from agents.summary_agent import summary_agent

    if mode == "daily":
        prompt = build_daily_prompt(files, date_str)
        with summary_agent.override(output_type=DailySummary):
            return await summary_agent.run(prompt)
    else:
        prompt = build_weekly_prompt(files, daily_summaries, date_str)
        with summary_agent.override(output_type=WeeklySummary):
            return await summary_agent.run(prompt)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_summary_runner.py -v`
Expected: All pass

**Step 5: Commit**

```bash
git add agents/summary_runner.py tests/test_summary_runner.py
git commit -m "feat: add summary runner with prompt builders"
```

---

### Task 6: CLI Entry Point

**Files:**
- Create: `agents/run_summary.py`
- Create: `tests/test_run_summary.py`

**Step 1: Write the failing tests**

```python
# tests/test_run_summary.py
from __future__ import annotations

import time

import pytest

from agents.run_summary import determine_output_path, write_summary_file
from models.summary import DailySummary, SummarySection, WeeklySummary, ThemeProgress


class TestDetermineOutputPath:
    def test_daily_path(self, tmp_vault):
        path = determine_output_path(tmp_vault, "daily", "2026-02-21")
        assert str(path).endswith("_system/summaries/daily/auto/daily-summary-2026-02-21.md")

    def test_weekly_path(self, tmp_vault):
        path = determine_output_path(tmp_vault, "weekly", "2026-W08")
        assert str(path).endswith("_system/summaries/weekly/auto/weekly-summary-2026-W08.md")


class TestWriteSummaryFile:
    def test_writes_daily_markdown(self, tmp_vault):
        output_dir = tmp_vault / "_system" / "summaries" / "daily" / "auto"
        output_dir.mkdir(parents=True)
        output_path = output_dir / "daily-summary-2026-02-21.md"

        section = SummarySection(items=["Item"])
        summary = DailySummary(
            what_changed=section,
            open_loops=section,
            next_actions=section,
            risks_blockers=section,
            questions_for_patrick=section,
        )

        write_summary_file(summary, output_path, "2026-02-21")
        assert output_path.exists()
        content = output_path.read_text()
        assert "type: daily-summary" in content
        assert "date: 2026-02-21" in content

    def test_writes_weekly_markdown(self, tmp_vault):
        output_dir = tmp_vault / "_system" / "summaries" / "weekly" / "auto"
        output_dir.mkdir(parents=True)
        output_path = output_dir / "weekly-summary-2026-W08.md"

        section = SummarySection(items=["Item"])
        summary = WeeklySummary(
            highlights=section,
            progress_by_theme=[],
            open_loops=section,
            next_actions=section,
            questions_for_patrick=section,
        )

        write_summary_file(summary, output_path, "2026-W08")
        assert output_path.exists()
        content = output_path.read_text()
        assert "type: weekly-summary" in content

    def test_atomic_write_no_partial_file_on_error(self, tmp_vault):
        """If render fails, no file should exist."""
        output_dir = tmp_vault / "_system" / "summaries" / "daily" / "auto"
        output_dir.mkdir(parents=True)
        output_path = output_dir / "daily-summary-2026-02-21.md"
        # Pass None to trigger error
        try:
            write_summary_file(None, output_path, "2026-02-21")
        except Exception:
            pass
        assert not output_path.exists()
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_run_summary.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.run_summary'`

**Step 3: Write the implementation**

```python
# agents/run_summary.py
"""CLI entry point for PydanticAI summary agent.

Usage:
    python3 agents/run_summary.py daily
    python3 agents/run_summary.py weekly

Exit codes:
    0 = success
    1 = error
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Union

from config.agent_config import INPUT_PRICE, OUTPUT_PRICE, VAULT_DIR
from models.summary import DailySummary, WeeklySummary
from tools.vault_scan import find_recent_files, read_daily_summaries


def determine_output_path(vault_dir: Path, mode: str, date_str: str) -> Path:
    """Determine the output file path for a summary."""
    if mode == "daily":
        return vault_dir / "_system" / "summaries" / "daily" / "auto" / f"daily-summary-{date_str}.md"
    else:
        return vault_dir / "_system" / "summaries" / "weekly" / "auto" / f"weekly-summary-{date_str}.md"


def write_summary_file(
    summary: Union[DailySummary, WeeklySummary],
    output_path: Path,
    date_str: str,
) -> None:
    """Render summary to markdown and write atomically."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    md = summary.render_markdown(date_str)
    tmp_path = output_path.with_suffix(".tmp")
    tmp_path.write_text(md)
    tmp_path.rename(output_path)


async def _run(mode: str, vault_dir: Path) -> int:
    """Run the summary agent and write output."""
    from agents.summary_runner import run_summary
    from state.db import get_connection, init_schema
    from state.runs import log_run_complete, log_run_error, log_run_start

    # Determine date/week string
    now = datetime.now()
    if mode == "daily":
        date_str = now.strftime("%Y-%m-%d")
    else:
        date_str = now.strftime("%Y-W%V")

    # Idempotency check
    output_path = determine_output_path(vault_dir, mode, date_str)
    if output_path.exists():
        print(f"summary: {mode} summary already exists for {date_str}, skipping")
        return 0

    # Gather context
    if mode == "daily":
        files = find_recent_files(vault_dir, since_hours=24)
        daily_summaries = []
    else:
        files = find_recent_files(vault_dir, since_hours=168)
        daily_summaries = read_daily_summaries(vault_dir, days=7)

    run_id = str(uuid.uuid4())
    input_summary = f"{mode} summary for {date_str}, {len(files)} changed files"

    conn = get_connection()
    init_schema(conn)
    log_run_start(conn, run_id, f"summary-{mode}", input_summary)

    start_time = time.monotonic()
    try:
        result = await run_summary(mode, files, daily_summaries, vault_dir=vault_dir, date_str=date_str)
        duration_ms = int((time.monotonic() - start_time) * 1000)

        summary = result.output
        write_summary_file(summary, output_path, date_str)

        usage = result.usage()
        tokens_in = usage.input_tokens or 0
        tokens_out = usage.output_tokens or 0
        cost_usd = (tokens_in * INPUT_PRICE) + (tokens_out * OUTPUT_PRICE)

        log_run_complete(
            conn,
            run_id=run_id,
            output_summary=summary.model_dump_json(),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
        )
        conn.close()

        print(f"summary: {mode} summary written to {output_path}")
        return 0

    except Exception as e:
        duration_ms = int((time.monotonic() - start_time) * 1000)
        log_run_error(conn, run_id, str(e))
        conn.close()
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(description="Generate vault summary")
    parser.add_argument("mode", choices=["daily", "weekly"], help="Summary type")
    args = parser.parse_args()

    exit_code = asyncio.run(_run(args.mode, VAULT_DIR))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_run_summary.py -v`
Expected: All pass

**Step 5: Run all tests**

Run: `pytest tests/ -v`
Expected: All pass (Phase 1 + Phase 2 tests)

**Step 6: Commit**

```bash
git add agents/run_summary.py tests/test_run_summary.py
git commit -m "feat: add summary CLI entry point with atomic write and cost tracking"
```

---

### Task 7: Integration Test

**Files:**
- Create: `tests/test_summary_flow.py`
- Modify: `tests/conftest.py` (add summary-related fixtures)

**Step 1: Add fixture to conftest.py**

Add to `tests/conftest.py`:

```python
@pytest.fixture
def tmp_vault_with_recent_files(tmp_vault):
    """Temp vault with some recently modified files for summary testing."""
    # Create some recent files
    (tmp_vault / "0_inbox" / "new-note.md").write_text(
        "---\ncaptured_at: 2026-02-21\n---\n# New Note\n\nSome content."
    )
    (tmp_vault / "1_projects" / "active" / "test-project.md").write_text(
        "# Test Project\n\nStatus: active\n"
    )
    # Create summaries directory
    summ_dir = tmp_vault / "_system" / "summaries" / "daily" / "auto"
    summ_dir.mkdir(parents=True)
    (tmp_vault / "_system" / "summaries" / "weekly" / "auto").mkdir(parents=True)
    yield tmp_vault
```

**Step 2: Write the integration tests**

```python
# tests/test_summary_flow.py
from __future__ import annotations

import pytest
from pydantic_ai.models.test import TestModel

from agents.run_summary import determine_output_path, write_summary_file, _run
from agents.summary_agent import summary_agent
from agents.summary_runner import run_summary
from models.summary import DailySummary, SummarySection, WeeklySummary
from state.db import get_connection, init_schema
from tools.vault_scan import find_recent_files


class TestFullSummaryFlow:
    def test_daily_summary_writes_file(self, tmp_vault_with_recent_files):
        """Daily summary renders and writes correctly."""
        vault = tmp_vault_with_recent_files
        section = SummarySection(items=["Updated test-project.md"])
        summary = DailySummary(
            what_changed=section,
            open_loops=SummarySection(items=["Review new note"]),
            next_actions=SummarySection(items=["Continue project"]),
            risks_blockers=SummarySection(items=[]),
            questions_for_patrick=SummarySection(items=[]),
        )

        output_path = determine_output_path(vault, "daily", "2026-02-21")
        write_summary_file(summary, output_path, "2026-02-21")

        assert output_path.exists()
        content = output_path.read_text()
        assert "type: daily-summary" in content
        assert "## What Changed Today" in content
        assert "- Updated test-project.md" in content

    def test_weekly_summary_writes_file(self, tmp_vault_with_recent_files):
        """Weekly summary renders and writes correctly."""
        vault = tmp_vault_with_recent_files
        section = SummarySection(items=["Shipped feature"])
        summary = WeeklySummary(
            highlights=section,
            progress_by_theme=[],
            open_loops=SummarySection(items=[]),
            next_actions=SummarySection(items=["Plan next sprint"]),
            questions_for_patrick=SummarySection(items=[]),
        )

        output_path = determine_output_path(vault, "weekly", "2026-W08")
        write_summary_file(summary, output_path, "2026-W08")

        assert output_path.exists()
        content = output_path.read_text()
        assert "type: weekly-summary" in content
        assert "week: 2026-W08" in content

    def test_find_recent_files_in_vault(self, tmp_vault_with_recent_files):
        """Vault scan finds recently modified files."""
        files = find_recent_files(tmp_vault_with_recent_files, since_hours=1)
        names = {f.name for f in files}
        assert "new-note.md" in names
        assert "test-project.md" in names

    async def test_agent_produces_daily_with_testmodel(self, tmp_vault_with_recent_files, monkeypatch):
        """Agent returns valid DailySummary with TestModel."""
        monkeypatch.setenv("SECOND_BRAIN_VAULT", str(tmp_vault_with_recent_files))
        files = find_recent_files(tmp_vault_with_recent_files, since_hours=1)

        with summary_agent.override(model=TestModel(), output_type=DailySummary):
            result = await run_summary("daily", files, [], vault_dir=tmp_vault_with_recent_files, date_str="2026-02-21")
            assert isinstance(result.output, DailySummary)

    def test_state_db_records_run(self, tmp_db):
        """SQLite logs the summary agent run."""
        from state.runs import log_run_complete, log_run_start

        conn = get_connection(tmp_db)
        init_schema(conn)
        log_run_start(conn, "summary-test-1", "summary-daily", "daily summary for 2026-02-21")
        log_run_complete(
            conn,
            run_id="summary-test-1",
            output_summary='{"what_changed": {"items": []}}',
            tokens_in=200,
            tokens_out=100,
            cost_usd=0.002,
            duration_ms=5000,
        )

        row = conn.execute(
            "SELECT status, agent_type, tokens_in FROM agent_runs WHERE run_id=?",
            ("summary-test-1",),
        ).fetchone()
        assert row[0] == "completed"
        assert row[1] == "summary-daily"
        assert row[2] == 200
        conn.close()
```

**Step 3: Run tests to verify they pass**

Run: `pytest tests/test_summary_flow.py -v`
Expected: All pass

**Step 4: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests pass (Phase 1 + Phase 2)

**Step 5: Commit**

```bash
git add tests/conftest.py tests/test_summary_flow.py
git commit -m "feat: add integration tests for summary flow"
```

---

### Task 8: Update Bash Scripts

**Files:**
- Modify: `scripts/daily-summary.sh`
- Modify: `scripts/weekly-summary.sh`

**Step 1: Back up existing scripts**

```bash
cp scripts/daily-summary.sh scripts/daily-summary.sh.bak
cp scripts/weekly-summary.sh scripts/weekly-summary.sh.bak
```

**Step 2: Update daily-summary.sh**

Replace the `claude --continue --print` block with:

```bash
#!/usr/bin/env bash
# daily-summary.sh — Generate a daily summary using PydanticAI agent.
# Invoked by systemd timer daily at 07:30 America/Los_Angeles.
set -euo pipefail

VAULT_DIR="${VAULT_DIR:-/home/ubuntu/second-brain}"
LOCK_FILE="${LOCK_FILE:-/srv/locks/claude-exec.lock}"
TODAY="$(date +%Y-%m-%d)"
OUTPUT_FILE="${VAULT_DIR}/_system/summaries/daily/auto/daily-summary-${TODAY}.md"

# Error trap: notify on failure.
cleanup_on_error() {
    happy notify -p "Failed: daily summary generation error for ${TODAY}" 2>/dev/null || true
}
trap cleanup_on_error ERR

# Idempotency check: skip if already generated today.
if [[ -f "$OUTPUT_FILE" ]]; then
    happy notify -p "Skipped: daily summary already exists for ${TODAY}" 2>/dev/null || true
    exit 0
fi

# Acquire lock (non-blocking).
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    happy notify -p "Skipped: interactive session active" 2>/dev/null || true
    exit 0
fi

# Activate virtual environment
if [[ -f "${VAULT_DIR}/.venv/bin/activate" ]]; then
    source "${VAULT_DIR}/.venv/bin/activate"
else
    echo "daily-summary: ERROR — .venv not found at ${VAULT_DIR}/.venv"
    happy notify -p "Daily summary failed: .venv not found" 2>/dev/null || true
    exit 1
fi

# Run PydanticAI summary agent
cd "$VAULT_DIR"
python3 "${VAULT_DIR}/agents/run_summary.py" daily
RESULT=$?

case $RESULT in
    0)
        echo "daily-summary: complete"
        happy notify -p "Daily summary written for ${TODAY}" 2>/dev/null || true
        ;;
    *)
        echo "daily-summary: failed (exit code $RESULT)"
        happy notify -p "Daily summary failed for ${TODAY}" 2>/dev/null || true
        exit 1
        ;;
esac
```

**Step 3: Update weekly-summary.sh**

Same pattern, `daily` → `weekly`, `TODAY` → `WEEK="$(date +%Y-W%V)"`.

```bash
#!/usr/bin/env bash
# weekly-summary.sh — Generate a weekly summary using PydanticAI agent.
# Invoked by systemd timer Sundays at 08:00 America/Los_Angeles.
set -euo pipefail

VAULT_DIR="${VAULT_DIR:-/home/ubuntu/second-brain}"
LOCK_FILE="${LOCK_FILE:-/srv/locks/claude-exec.lock}"
WEEK="$(date +%Y-W%V)"
OUTPUT_FILE="${VAULT_DIR}/_system/summaries/weekly/auto/weekly-summary-${WEEK}.md"

# Error trap: notify on failure.
cleanup_on_error() {
    happy notify -p "Failed: weekly summary generation for ${WEEK}" 2>/dev/null || true
}
trap cleanup_on_error ERR

# Idempotency check.
if [[ -f "$OUTPUT_FILE" ]]; then
    happy notify -p "Skipped: weekly summary already exists for ${WEEK}" 2>/dev/null || true
    exit 0
fi

# Acquire lock (non-blocking).
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    happy notify -p "Skipped: interactive session active" 2>/dev/null || true
    exit 0
fi

# Activate virtual environment
if [[ -f "${VAULT_DIR}/.venv/bin/activate" ]]; then
    source "${VAULT_DIR}/.venv/bin/activate"
else
    echo "weekly-summary: ERROR — .venv not found at ${VAULT_DIR}/.venv"
    happy notify -p "Weekly summary failed: .venv not found" 2>/dev/null || true
    exit 1
fi

# Run PydanticAI summary agent
cd "$VAULT_DIR"
python3 "${VAULT_DIR}/agents/run_summary.py" weekly
RESULT=$?

case $RESULT in
    0)
        echo "weekly-summary: complete"
        happy notify -p "Weekly summary written for ${WEEK}" 2>/dev/null || true
        ;;
    *)
        echo "weekly-summary: failed (exit code $RESULT)"
        happy notify -p "Weekly summary failed for ${WEEK}" 2>/dev/null || true
        exit 1
        ;;
esac
```

**Step 4: Commit**

```bash
git add scripts/daily-summary.sh scripts/daily-summary.sh.bak scripts/weekly-summary.sh scripts/weekly-summary.sh.bak
git commit -m "feat: update summary scripts to use PydanticAI agent"
```

---

### Task 9: Final Verification

**Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests pass (Phase 1 + Phase 2)

**Step 2: Verify directory structure**

Check that all new files exist:
- `models/summary.py`
- `tools/vault_scan.py`
- `agents/summary_agent.py`
- `agents/summary_runner.py`
- `agents/run_summary.py`
- `config/prompts/summary_system.md`
- `scripts/daily-summary.sh.bak`
- `scripts/weekly-summary.sh.bak`
- `tests/test_summary_models.py`
- `tests/test_vault_scan.py`
- `tests/test_summary_agent.py`
- `tests/test_summary_runner.py`
- `tests/test_run_summary.py`
- `tests/test_summary_flow.py`

**Step 3: Finish branch**

Use `superpowers:finishing-a-development-branch` to complete the work.

---

### Task 10: Deploy to VM

**Step 1: Rsync updated code to VM**

```bash
for dir in agents config models state tools tests scripts; do
    rsync -av --delete "$dir/" ubuntu@second-brain-vm:/home/ubuntu/second-brain/$dir/
done
```

**Step 2: Run tests on VM**

```bash
ssh ubuntu@second-brain-vm 'cd /home/ubuntu/second-brain && .venv/bin/python -m pytest tests/ -v'
```

**Step 3: Create summary directories on VM**

```bash
ssh ubuntu@second-brain-vm 'mkdir -p /home/ubuntu/second-brain/_system/summaries/{daily,weekly}/auto'
```

**Step 4: Deploy updated scripts**

```bash
ssh ubuntu@second-brain-vm 'sudo cp /home/ubuntu/second-brain/scripts/daily-summary.sh /srv/scripts/ && sudo cp /home/ubuntu/second-brain/scripts/weekly-summary.sh /srv/scripts/ && sudo chmod +x /srv/scripts/daily-summary.sh /srv/scripts/weekly-summary.sh'
```

**Step 5: Test daily summary with real API**

```bash
ssh ubuntu@second-brain-vm 'export ANTHROPIC_API_KEY="..." && cd /home/ubuntu/second-brain && .venv/bin/python agents/run_summary.py daily'
```

**Step 6: Verify output and cost tracking**

```bash
ssh ubuntu@second-brain-vm 'cat /home/ubuntu/second-brain/_system/summaries/daily/auto/daily-summary-$(date +%Y-%m-%d).md'
ssh ubuntu@second-brain-vm 'sqlite3 /home/ubuntu/second-brain-state/agents.db "SELECT agent_type, status, tokens_in, tokens_out, cost_usd FROM agent_runs ORDER BY started_at DESC LIMIT 3;"'
```

Expected: Summary file exists with correct frontmatter and sections, agents.db shows token/cost data.
