# Phase 1: Structured Triage — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace `claude --print "/triage all"` with a PydanticAI agent returning validated, typed triage decisions. Introduce SQLite `agent_runs` tracking and DBOS durable execution.

**Architecture:** Bottom-up build in dependency order: models → state → tools → agent → CLI → bash. Agent decides (returns `TriageBatch`), CLI executes (moves files, updates frontmatter). Existing bash orchestration (flock, systemd, Syncthing watcher) stays unchanged.

**Tech Stack:** Python 3.11+, pydantic-ai[dbos] (with anthropic), dbos-transact, pytest, SQLite

**Repo:** `/Users/patrick/workspace/second-brain`
**Design doc:** `docs/plans/2026-02-19-pydantic-ai-phase1-design.md`

---

### Task 1: Project Setup

**Files:**
- Create: `pyproject.toml`
- Create: `config/__init__.py`
- Create: `config/agent_config.py`
- Create: `models/__init__.py`
- Create: `agents/__init__.py`
- Create: `state/__init__.py`
- Create: `tools/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "second-brain-agents"
version = "0.1.0"
description = "PydanticAI agents for Second Brain triage and automation"
requires-python = ">=3.11"
dependencies = [
    "pydantic-ai[anthropic,dbos]>=0.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
]

[build-system]
requires = ["setuptools>=75.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Step 2: Create config/agent_config.py**

```python
import os
from pathlib import Path

VAULT_DIR = Path(os.environ.get("SECOND_BRAIN_VAULT", "/home/ubuntu/second-brain"))
STATE_DB_PATH = Path(os.environ.get("SECOND_BRAIN_STATE_DB", "/home/ubuntu/second-brain-state/agents.db"))

TRIAGE_MODEL = os.environ.get("TRIAGE_MODEL", "anthropic:claude-sonnet-4-5")

# Token pricing (USD per token) — Claude Sonnet 4.5
INPUT_PRICE = 3.0 / 1_000_000   # $3/MTok
OUTPUT_PRICE = 15.0 / 1_000_000  # $15/MTok
```

**Step 3: Create empty `__init__.py` files**

Create empty `__init__.py` in: `config/`, `models/`, `agents/`, `state/`, `tools/`, `tests/`

**Step 4: Create tests/conftest.py**

```python
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_vault(tmp_path):
    """Create a temporary vault with PARA directory structure."""
    dirs = [
        "0_inbox",
        "1_projects/active",
        "1_projects/waiting",
        "2_areas/Health",
        "2_areas/Family",
        "3_resources/Technology",
        "3_resources/Vendors",
        "4_archive",
        "5_people/family",
        "_system",
    ]
    for d in dirs:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)

    # Create routes.yaml
    routes_content = Path(os.environ.get(
        "SECOND_BRAIN_VAULT", "/home/ubuntu/second-brain"
    )).parent  # not used, we inline a minimal version
    (tmp_path / "_system" / "routes.yaml").write_text(
        "version: 1\n"
        "folders:\n"
        '  inbox: "0_inbox"\n'
        '  projects: "1_projects"\n'
        '  areas: "2_areas"\n'
        '  resources: "3_resources"\n'
        '  archive: "4_archive"\n'
        '  people: "5_people"\n'
        "uncertainty:\n"
        "  keep_in_inbox_below_confidence: 0.7\n"
        "areas:\n"
        "  allowed:\n"
        '    - "Health"\n'
        '    - "Family"\n'
        "resources:\n"
        "  allowed:\n"
        '    - "Technology"\n'
        '    - "Vendors"\n'
    )

    # Create processing-log.md
    (tmp_path / "_system" / "processing-log.md").write_text(
        "# Processing Log\n\n"
    )

    yield tmp_path


@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary SQLite database path."""
    db_path = tmp_path / "test_agents.db"
    yield db_path


@pytest.fixture
def sample_inbox_file(tmp_vault):
    """Create a sample inbox markdown file."""
    content = (
        "---\n"
        "captured_at: 2026-02-19T10:00:00-0800\n"
        "source: telegram\n"
        "---\n"
        "# Plan Hawaii Trip\n\n"
        "Book flights for April. Need to reserve hotel by March 1.\n"
        "Budget: $3000. Deadline: April 15.\n"
    )
    path = tmp_vault / "0_inbox" / "2026-02-19T100000-0800__telegram.md"
    path.write_text(content)
    yield path
```

**Step 5: Create virtual environment and install**

Run: `cd /Users/patrick/workspace/second-brain && python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"`

**Step 6: Verify pytest runs**

Run: `.venv/bin/pytest tests/ -v`
Expected: "no tests ran" (0 collected), exit 0 (or 5 for no tests)

**Step 7: Commit**

```bash
git add pyproject.toml config/ models/__init__.py agents/__init__.py state/__init__.py tools/__init__.py tests/
git commit -m "feat: project setup for PydanticAI triage agent

Add pyproject.toml with pydantic-ai[anthropic,dbos] and pytest deps.
Create package structure: config, models, agents, state, tools, tests.
Add conftest.py with tmp_vault, tmp_db, and sample_inbox_file fixtures."
```

---

### Task 2: Data Models

**Files:**
- Create: `models/triage.py`
- Create: `tests/test_models.py`

**Step 1: Write the failing test**

```python
# tests/test_models.py
import pytest
from pydantic import ValidationError

from models.triage import PARADestination, TriageBatch, TriageDecision


class TestPARADestination:
    def test_valid_destinations(self):
        assert PARADestination.PROJECTS_ACTIVE == "1_projects/active"
        assert PARADestination.AREAS == "2_areas"
        assert PARADestination.RESOURCES == "3_resources"
        assert PARADestination.ARCHIVE == "4_archive"
        assert PARADestination.PEOPLE == "5_people"

    def test_all_destinations_are_strings(self):
        for dest in PARADestination:
            assert isinstance(dest.value, str)


class TestTriageDecision:
    def test_valid_decision(self):
        decision = TriageDecision(
            filename="test-note.md",
            destination=PARADestination.AREAS,
            subdirectory="Health",
            confidence=0.85,
            reasoning="Ongoing health tracking",
            suggested_rename="health-checkup.md",
            tags=["health", "routine"],
        )
        assert decision.filename == "test-note.md"
        assert decision.destination == PARADestination.AREAS
        assert decision.confidence == 0.85

    def test_minimal_decision(self):
        decision = TriageDecision(
            filename="note.md",
            destination=PARADestination.ARCHIVE,
            subdirectory=None,
            confidence=0.9,
            reasoning="Old note",
            suggested_rename=None,
            tags=[],
        )
        assert decision.subdirectory is None
        assert decision.suggested_rename is None

    def test_confidence_bounds_low(self):
        with pytest.raises(ValidationError):
            TriageDecision(
                filename="note.md",
                destination=PARADestination.AREAS,
                subdirectory=None,
                confidence=-0.1,
                reasoning="test",
                suggested_rename=None,
                tags=[],
            )

    def test_confidence_bounds_high(self):
        with pytest.raises(ValidationError):
            TriageDecision(
                filename="note.md",
                destination=PARADestination.AREAS,
                subdirectory=None,
                confidence=1.1,
                reasoning="test",
                suggested_rename=None,
                tags=[],
            )

    def test_invalid_destination(self):
        with pytest.raises(ValidationError):
            TriageDecision(
                filename="note.md",
                destination="invalid_folder",
                subdirectory=None,
                confidence=0.5,
                reasoning="test",
                suggested_rename=None,
                tags=[],
            )


class TestTriageBatch:
    def test_valid_batch(self):
        batch = TriageBatch(
            decisions=[
                TriageDecision(
                    filename="note1.md",
                    destination=PARADestination.PROJECTS_ACTIVE,
                    subdirectory="hawaii-2026",
                    confidence=0.9,
                    reasoning="Has deadline and deliverable",
                    suggested_rename="hawaii-trip-planning.md",
                    tags=["travel", "project"],
                ),
            ],
            skipped=["binary-file.pdf"],
        )
        assert len(batch.decisions) == 1
        assert len(batch.skipped) == 1

    def test_empty_batch(self):
        batch = TriageBatch(decisions=[], skipped=[])
        assert len(batch.decisions) == 0

    def test_skipped_defaults_empty(self):
        batch = TriageBatch(decisions=[])
        assert batch.skipped == []
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'models.triage'`

**Step 3: Write minimal implementation**

```python
# models/triage.py
from enum import Enum

from pydantic import BaseModel, Field


class PARADestination(str, Enum):
    PROJECTS_ACTIVE = "1_projects/active"
    PROJECTS_WAITING = "1_projects/waiting"
    AREAS = "2_areas"
    RESOURCES = "3_resources"
    ARCHIVE = "4_archive"
    PEOPLE = "5_people"


class TriageDecision(BaseModel):
    filename: str = Field(description="Original filename in 0_inbox/")
    destination: PARADestination = Field(description="Target PARA directory")
    subdirectory: str | None = Field(
        default=None,
        description="Subdirectory within destination (e.g., 'Health' under 2_areas)",
    )
    confidence: float = Field(ge=0, le=1, description="Triage confidence 0.0-1.0")
    reasoning: str = Field(description="Explanation of routing decision")
    suggested_rename: str | None = Field(
        default=None,
        description="Suggested canonical filename (lowercase-hyphenated.md)",
    )
    tags: list[str] = Field(default_factory=list, description="Suggested tags")


class TriageBatch(BaseModel):
    decisions: list[TriageDecision] = Field(description="Triage decisions for each file")
    skipped: list[str] = Field(
        default_factory=list,
        description="Filenames that could not be processed",
    )
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_models.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add models/triage.py tests/test_models.py
git commit -m "feat: add triage data models with validation

TriageBatch, TriageDecision, PARADestination with confidence bounds,
enum validation, and optional fields matching existing frontmatter."
```

---

### Task 3: State Layer

**Files:**
- Create: `state/db.py`
- Create: `state/runs.py`
- Create: `tests/test_state_db.py`

**Step 1: Write the failing tests**

```python
# tests/test_state_db.py
import sqlite3
from pathlib import Path

import pytest

from state.db import get_connection, init_schema
from state.runs import log_run_complete, log_run_error, log_run_start


class TestDatabase:
    def test_get_connection_creates_file(self, tmp_db):
        conn = get_connection(tmp_db)
        assert tmp_db.exists()
        conn.close()

    def test_get_connection_wal_mode(self, tmp_db):
        conn = get_connection(tmp_db)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"
        conn.close()

    def test_get_connection_foreign_keys(self, tmp_db):
        conn = get_connection(tmp_db)
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1
        conn.close()

    def test_init_schema_creates_table(self, tmp_db):
        conn = get_connection(tmp_db)
        init_schema(conn)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        assert "agent_runs" in table_names
        conn.close()

    def test_init_schema_idempotent(self, tmp_db):
        conn = get_connection(tmp_db)
        init_schema(conn)
        init_schema(conn)  # should not raise
        conn.close()


class TestRunLogging:
    def test_log_run_start(self, tmp_db):
        conn = get_connection(tmp_db)
        init_schema(conn)
        run_id = log_run_start(conn, "test-run-1", "triage", "note1.md, note2.md")
        assert run_id == "test-run-1"
        row = conn.execute(
            "SELECT run_id, agent_type, status, input_summary FROM agent_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        assert row[0] == "test-run-1"
        assert row[1] == "triage"
        assert row[2] == "running"
        assert row[3] == "note1.md, note2.md"
        conn.close()

    def test_log_run_complete(self, tmp_db):
        conn = get_connection(tmp_db)
        init_schema(conn)
        log_run_start(conn, "test-run-2", "triage", "note.md")
        log_run_complete(
            conn,
            run_id="test-run-2",
            output_summary='{"decisions": []}',
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.001,
            duration_ms=1500,
        )
        row = conn.execute(
            "SELECT status, tokens_in, tokens_out, cost_usd, duration_ms, completed_at "
            "FROM agent_runs WHERE run_id = ?",
            ("test-run-2",),
        ).fetchone()
        assert row[0] == "completed"
        assert row[1] == 100
        assert row[2] == 50
        assert row[3] == pytest.approx(0.001)
        assert row[4] == 1500
        assert row[5] is not None  # completed_at set
        conn.close()

    def test_log_run_error(self, tmp_db):
        conn = get_connection(tmp_db)
        init_schema(conn)
        log_run_start(conn, "test-run-3", "triage", "note.md")
        log_run_error(conn, "test-run-3", "API timeout")
        row = conn.execute(
            "SELECT status, output_summary FROM agent_runs WHERE run_id = ?",
            ("test-run-3",),
        ).fetchone()
        assert row[0] == "error"
        assert "API timeout" in row[1]
        conn.close()
```

**Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_state_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'state.db'`

**Step 3: Write implementation**

```python
# state/db.py
import sqlite3
from pathlib import Path

from config.agent_config import STATE_DB_PATH


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Get a SQLite connection with WAL mode and foreign keys enabled."""
    path = db_path or STATE_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist. Idempotent."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agent_runs (
            run_id          TEXT PRIMARY KEY,
            agent_type      TEXT NOT NULL,
            goal_id         TEXT,
            status          TEXT NOT NULL,
            input_summary   TEXT,
            output_summary  TEXT,
            tokens_in       INTEGER,
            tokens_out      INTEGER,
            cost_usd        REAL,
            duration_ms     INTEGER,
            started_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at    DATETIME
        );
        CREATE INDEX IF NOT EXISTS idx_runs_agent_date
            ON agent_runs(agent_type, started_at);
    """)
```

```python
# state/runs.py
import sqlite3


def log_run_start(
    conn: sqlite3.Connection,
    run_id: str,
    agent_type: str,
    input_summary: str,
) -> str:
    """Insert a new agent run with status='running'."""
    conn.execute(
        "INSERT INTO agent_runs (run_id, agent_type, status, input_summary) VALUES (?, ?, 'running', ?)",
        (run_id, agent_type, input_summary),
    )
    conn.commit()
    return run_id


def log_run_complete(
    conn: sqlite3.Connection,
    run_id: str,
    output_summary: str,
    tokens_in: int,
    tokens_out: int,
    cost_usd: float,
    duration_ms: int,
) -> None:
    """Mark a run as completed with usage data."""
    conn.execute(
        "UPDATE agent_runs SET status='completed', output_summary=?, tokens_in=?, "
        "tokens_out=?, cost_usd=?, duration_ms=?, completed_at=CURRENT_TIMESTAMP "
        "WHERE run_id=?",
        (output_summary, tokens_in, tokens_out, cost_usd, duration_ms, run_id),
    )
    conn.commit()


def log_run_error(
    conn: sqlite3.Connection,
    run_id: str,
    error_message: str,
) -> None:
    """Mark a run as failed with error details."""
    conn.execute(
        "UPDATE agent_runs SET status='error', output_summary=?, completed_at=CURRENT_TIMESTAMP WHERE run_id=?",
        (f"ERROR: {error_message}", run_id),
    )
    conn.commit()
```

**Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_state_db.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add state/db.py state/runs.py tests/test_state_db.py
git commit -m "feat: add SQLite state layer for agent run tracking

get_connection with WAL mode, init_schema idempotent, run logging
with start/complete/error state transitions."
```

---

### Task 4: Vault Read Tools

**Files:**
- Create: `tools/vault_read.py`
- Create: `tests/test_vault_read.py`

**Step 1: Write the failing tests**

```python
# tests/test_vault_read.py
from pathlib import Path

from tools.vault_read import list_directory, read_file, read_routes


class TestReadFile:
    def test_reads_markdown(self, tmp_vault):
        note = tmp_vault / "0_inbox" / "test.md"
        note.write_text("# Hello\n\nSome content here.")
        result = read_file(tmp_vault, "0_inbox/test.md")
        assert "# Hello" in result
        assert "Some content here." in result

    def test_caps_at_3kb(self, tmp_vault):
        note = tmp_vault / "0_inbox" / "big.md"
        note.write_text("x" * 5000)
        result = read_file(tmp_vault, "0_inbox/big.md")
        assert len(result) <= 3072 + 50  # 3KB + truncation message

    def test_missing_file(self, tmp_vault):
        result = read_file(tmp_vault, "0_inbox/nonexistent.md")
        assert "not found" in result.lower() or "error" in result.lower()


class TestListDirectory:
    def test_lists_vault_root(self, tmp_vault):
        result = list_directory(tmp_vault, "")
        assert "0_inbox" in result
        assert "1_projects" in result
        assert "2_areas" in result

    def test_lists_subdirectory(self, tmp_vault):
        result = list_directory(tmp_vault, "2_areas")
        assert "Health" in result

    def test_caps_at_100_entries(self, tmp_vault):
        many_dir = tmp_vault / "0_inbox"
        for i in range(120):
            (many_dir / f"note-{i:03d}.md").write_text(f"Note {i}")
        result = list_directory(tmp_vault, "0_inbox")
        # Should mention truncation or cap entries
        lines = [l for l in result.strip().split("\n") if l.strip()]
        assert len(lines) <= 101  # 100 entries + possible header


class TestReadRoutes:
    def test_reads_routes_yaml(self, tmp_vault):
        result = read_routes(tmp_vault)
        assert "0_inbox" in result
        assert "Health" in result
        assert "Technology" in result
```

**Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_vault_read.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.vault_read'`

**Step 3: Write implementation**

```python
# tools/vault_read.py
from pathlib import Path

MAX_FILE_SIZE = 3072  # 3KB cap per file
MAX_DIR_ENTRIES = 100


def read_file(vault_dir: Path, relative_path: str) -> str:
    """Read a file from the vault, capped at 3KB."""
    path = vault_dir / relative_path
    if not path.exists():
        return f"Error: file not found: {relative_path}"
    try:
        content = path.read_text(errors="replace")
        if len(content) > MAX_FILE_SIZE:
            return content[:MAX_FILE_SIZE] + "\n\n[... truncated at 3KB ...]"
        return content
    except Exception as e:
        return f"Error reading {relative_path}: {e}"


def list_directory(vault_dir: Path, relative_path: str) -> str:
    """List directory contents, capped at 100 entries."""
    path = vault_dir / relative_path if relative_path else vault_dir
    if not path.is_dir():
        return f"Error: not a directory: {relative_path}"
    entries = sorted(path.iterdir())
    lines = []
    for entry in entries[:MAX_DIR_ENTRIES]:
        suffix = "/" if entry.is_dir() else ""
        lines.append(f"{entry.name}{suffix}")
    if len(entries) > MAX_DIR_ENTRIES:
        lines.append(f"[... {len(entries) - MAX_DIR_ENTRIES} more entries truncated ...]")
    return "\n".join(lines)


def read_routes(vault_dir: Path) -> str:
    """Read the _system/routes.yaml file."""
    return read_file(vault_dir, "_system/routes.yaml")
```

**Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_vault_read.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add tools/vault_read.py tests/test_vault_read.py
git commit -m "feat: add vault read tools (read_file, list_directory, read_routes)

Read-only vault tools with 3KB file cap and 100-entry directory cap.
These are registered as PydanticAI tools on the triage agent."
```

---

### Task 5: Vault Write Tools

**Files:**
- Create: `tools/vault_write.py`
- Create: `tests/test_vault_write.py`

**Step 1: Write the failing tests**

```python
# tests/test_vault_write.py
import re
from pathlib import Path

from tools.vault_write import append_processing_log, move_file, update_frontmatter


class TestMoveFile:
    def test_moves_file(self, tmp_vault):
        src = tmp_vault / "0_inbox" / "note.md"
        src.write_text("# Test")
        dest_dir = tmp_vault / "2_areas" / "Health"
        move_file(tmp_vault, "0_inbox/note.md", "2_areas/Health/note.md")
        assert not src.exists()
        assert (dest_dir / "note.md").exists()
        assert (dest_dir / "note.md").read_text() == "# Test"

    def test_creates_destination_directory(self, tmp_vault):
        src = tmp_vault / "0_inbox" / "note.md"
        src.write_text("# Test")
        move_file(tmp_vault, "0_inbox/note.md", "3_resources/NewTopic/note.md")
        assert (tmp_vault / "3_resources" / "NewTopic" / "note.md").exists()

    def test_move_nonexistent_raises(self, tmp_vault):
        try:
            move_file(tmp_vault, "0_inbox/nope.md", "2_areas/Health/nope.md")
            assert False, "Should have raised"
        except FileNotFoundError:
            pass


class TestUpdateFrontmatter:
    def test_adds_frontmatter_to_file_without(self, tmp_vault):
        note = tmp_vault / "0_inbox" / "bare.md"
        note.write_text("# No frontmatter\n\nJust content.")
        update_frontmatter(note, {"para": "area", "status": "triaged"})
        content = note.read_text()
        assert content.startswith("---\n")
        assert "para: area" in content
        assert "status: triaged" in content
        assert "# No frontmatter" in content

    def test_merges_into_existing_frontmatter(self, tmp_vault):
        note = tmp_vault / "0_inbox" / "existing.md"
        note.write_text(
            "---\n"
            "captured_at: 2026-02-19T10:00:00-0800\n"
            "source: telegram\n"
            "---\n"
            "# Content\n"
        )
        update_frontmatter(note, {"para": "project", "triage_confidence": 0.9})
        content = note.read_text()
        assert "captured_at: 2026-02-19T10:00:00-0800" in content  # preserved
        assert "source: telegram" in content  # preserved
        assert "para: project" in content  # added
        assert "triage_confidence: 0.9" in content  # added


class TestAppendProcessingLog:
    def test_appends_entry(self, tmp_vault):
        append_processing_log(
            tmp_vault,
            source_path="0_inbox/note.md",
            destination_path="2_areas/Health/note.md",
            confidence=0.85,
            agent="pydantic-ai/triage",
            warnings="",
        )
        content = (tmp_vault / "_system" / "processing-log.md").read_text()
        assert "pydantic-ai/triage" in content
        assert "0_inbox/note.md" in content
        assert "2_areas/Health/note.md" in content
        assert "0.85" in content
```

**Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_vault_write.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.vault_write'`

**Step 3: Write implementation**

```python
# tools/vault_write.py
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


def move_file(vault_dir: Path, source_rel: str, dest_rel: str) -> None:
    """Move a file within the vault. Creates destination directory if needed."""
    source = vault_dir / source_rel
    dest = vault_dir / dest_rel
    if not source.exists():
        raise FileNotFoundError(f"Source not found: {source_rel}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(dest))


def update_frontmatter(file_path: Path, fields: dict) -> None:
    """Merge fields into a file's YAML frontmatter. Creates frontmatter if absent."""
    content = file_path.read_text()

    # Parse existing frontmatter
    fm_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if fm_match:
        existing_fm = fm_match.group(1)
        body = content[fm_match.end():]
    else:
        existing_fm = ""
        body = content

    # Parse existing fields into dict (simple key: value lines)
    existing = {}
    for line in existing_fm.split("\n"):
        if ": " in line:
            key, _, value = line.partition(": ")
            existing[key.strip()] = value.strip()

    # Merge new fields (new fields override)
    existing.update({k: str(v) for k, v in fields.items()})

    # Rebuild frontmatter
    fm_lines = [f"{k}: {v}" for k, v in existing.items()]
    new_content = "---\n" + "\n".join(fm_lines) + "\n---\n" + body
    file_path.write_text(new_content)


def append_processing_log(
    vault_dir: Path,
    source_path: str,
    destination_path: str,
    confidence: float,
    agent: str = "pydantic-ai/triage",
    warnings: str = "",
) -> None:
    """Append an entry to _system/processing-log.md."""
    log_path = vault_dir / "_system" / "processing-log.md"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    warning_str = f" | {warnings}" if warnings else ""
    entry = (
        f"- **{timestamp}** | {agent} | `{source_path}` → "
        f"`{destination_path}` | {confidence}{warning_str}\n"
    )
    with open(log_path, "a") as f:
        f.write(entry)
```

**Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_vault_write.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add tools/vault_write.py tests/test_vault_write.py
git commit -m "feat: add vault write tools (move_file, update_frontmatter, append_processing_log)

Write tools called by run_triage.py (not by the agent). Atomic moves,
frontmatter merge, processing-log append matching existing format."
```

---

### Task 6: System Prompt

**Files:**
- Create: `config/prompts/triage_system.md`

**Step 1: Create the system prompt**

This is derived from `_system/prompts/triage_para.md` but adapted for structured output. The agent returns `TriageDecision` objects instead of executing file operations.

```markdown
You are a triage agent for a PARA-based knowledge management system.

Your job is to classify inbox files into the correct PARA destination and return structured decisions. You do NOT move files — you only decide where they should go.

## PARA Decision Tree (strict order)

Answer these questions in order for each file:

### Q1: Tied to a specific outcome with a deadline or finishable deliverable?
If yes → PROJECT (1_projects/active or 1_projects/waiting)
- Projects are time-bounded outcomes with a definition of "done".
- Examples: "Ship feature X", "Plan April trip", "Buy new smoker"

### Q2: Ongoing responsibility/role/standard with no end date?
If yes → AREA (2_areas)
- Areas persist over time.
- Examples: Health, Family, Home, Finance, Work, Learning

### Q3: Reference material or topic of interest, no commitment?
If yes → RESOURCE (3_resources)
- Resources are "useful someday" libraries.
- Examples: Recipes, vendor info, how-to guides, tech tips

### Q4: Inactive, completed, obsolete, or purely historical?
If yes → ARCHIVE (4_archive)

### Q5: None of the above confidently applies?
Keep in INBOX — set confidence below 0.7

## People handling
If the note is primarily about a person or relationship, route to PEOPLE (5_people) regardless of PARA category.

## Rules

- Use the `read_routes` tool to get allowed area/resource names and keyword hints
- Use the `list_vault_directories` tool to see existing directory structure
- Pick `subdirectory` from allowed names in routes.yaml when routing to areas/resources
- Set `confidence` between 0.0 and 1.0. Below 0.7 means the item stays in inbox.
- Set `suggested_rename` to a lowercase-hyphenated slug if the original filename is not descriptive
- Include relevant `tags` for the note
- Provide clear `reasoning` explaining which question (Q1-Q5) determined the routing
- If a file cannot be processed (binary, empty, etc.), add it to the `skipped` list
```

**Step 2: Commit**

```bash
mkdir -p config/prompts
git add config/prompts/triage_system.md
git commit -m "feat: add triage agent system prompt

PARA decision tree adapted for structured output. Agent decides,
does not execute. Derived from _system/prompts/triage_para.md."
```

---

### Task 7: Triage Agent

**Files:**
- Create: `agents/triage_agent.py`
- Create: `tests/test_triage_agent.py`

**Step 1: Write the failing tests**

```python
# tests/test_triage_agent.py
import pytest
from pydantic_ai.models.test import TestModel

from agents.triage_agent import triage_agent
from models.triage import PARADestination, TriageBatch


class TestTriageAgentDefinition:
    def test_agent_has_correct_name(self):
        assert triage_agent.name == "triage"

    def test_agent_output_type(self):
        assert triage_agent._output_type == TriageBatch

    def test_agent_has_retries(self):
        assert triage_agent._max_result_retries == 2


class TestTriageAgentRun:
    async def test_agent_returns_triage_batch(self, tmp_vault, monkeypatch):
        """TestModel generates data matching TriageBatch schema."""
        monkeypatch.setenv("SECOND_BRAIN_VAULT", str(tmp_vault))

        # Create a sample inbox file
        inbox_file = tmp_vault / "0_inbox" / "test-note.md"
        inbox_file.write_text("# Plan Hawaii Trip\n\nBook flights for April.")

        with triage_agent.override(model=TestModel()):
            result = await triage_agent.run(
                "Route these inbox files:\n\n## File: test-note.md\n\n# Plan Hawaii Trip\nBook flights."
            )
            assert isinstance(result.output, TriageBatch)

    async def test_agent_tools_registered(self):
        """Verify the agent has read_routes and list_vault_directories tools."""
        # Get tool names from the agent
        # PydanticAI stores tools internally
        tool_names = []
        for tool in triage_agent._function_tools.values():
            tool_names.append(tool.name)
        assert "read_routes" in tool_names
        assert "list_vault_directories" in tool_names
```

**Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_triage_agent.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.triage_agent'`

**Step 3: Write implementation**

```python
# agents/triage_agent.py
from pathlib import Path

from pydantic_ai import Agent, RunContext

from config.agent_config import TRIAGE_MODEL, VAULT_DIR
from models.triage import TriageBatch
from tools.vault_read import list_directory, read_routes


def _load_system_prompt() -> str:
    """Load the triage system prompt from config/prompts/."""
    prompt_path = Path(__file__).parent.parent / "config" / "prompts" / "triage_system.md"
    return prompt_path.read_text()


triage_agent = Agent(
    TRIAGE_MODEL,
    output_type=TriageBatch,
    instructions=_load_system_prompt(),
    name="triage",
    retries=2,
)


@triage_agent.tool_plain
def read_routes_tool() -> str:
    """Read PARA routing rules from _system/routes.yaml."""
    return read_routes(VAULT_DIR)


@triage_agent.tool_plain
def list_vault_directories() -> str:
    """List the top-level vault directory structure."""
    lines = [list_directory(VAULT_DIR, "")]
    # Also list key subdirectories
    for subdir in ["1_projects", "2_areas", "3_resources", "5_people"]:
        sub_listing = list_directory(VAULT_DIR, subdir)
        if "error" not in sub_listing.lower():
            lines.append(f"\n## {subdir}/\n{sub_listing}")
    return "\n".join(lines)
```

**Step 4: Update test to match actual tool names**

The tool names come from the function names. After creating the agent, verify what names PydanticAI assigns and adjust the test assertion if needed. The tool function `read_routes_tool` will be registered as `"read_routes_tool"` and `list_vault_directories` as `"list_vault_directories"`.

Update the test assertion:
```python
assert "read_routes_tool" in tool_names
assert "list_vault_directories" in tool_names
```

**Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_triage_agent.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add agents/triage_agent.py tests/test_triage_agent.py
git commit -m "feat: add PydanticAI triage agent with read-only vault tools

Agent returns TriageBatch, uses claude-sonnet-4-5 with 2 retries.
Tools: read_routes_tool, list_vault_directories. Agent decides only."
```

---

### Task 8: Triage Runner Function (with DBOS)

**Files:**
- Create: `agents/triage_runner.py`
- Create: `tests/test_triage_runner.py`

This module contains the `triage_inbox()` function that wraps the agent with DBOS and builds the prompt from file contents.

**Step 1: Write the failing tests**

```python
# tests/test_triage_runner.py
from pathlib import Path

import pytest
from pydantic_ai.models.test import TestModel

from agents.triage_agent import triage_agent
from agents.triage_runner import build_triage_prompt, triage_inbox
from models.triage import TriageBatch


class TestBuildTriagePrompt:
    def test_includes_file_contents(self, tmp_vault):
        note = tmp_vault / "0_inbox" / "test.md"
        note.write_text("# Test Note\n\nSome content.")
        prompt = build_triage_prompt([note], tmp_vault)
        assert "test.md" in prompt
        assert "Test Note" in prompt

    def test_caps_file_content(self, tmp_vault):
        note = tmp_vault / "0_inbox" / "big.md"
        note.write_text("x" * 5000)
        prompt = build_triage_prompt([note], tmp_vault)
        # Content should be capped, prompt should not be enormous
        assert len(prompt) < 10000

    def test_includes_multiple_files(self, tmp_vault):
        for i in range(3):
            note = tmp_vault / "0_inbox" / f"note-{i}.md"
            note.write_text(f"# Note {i}")
        files = list((tmp_vault / "0_inbox").glob("*.md"))
        prompt = build_triage_prompt(files, tmp_vault)
        assert "note-0.md" in prompt
        assert "note-1.md" in prompt
        assert "note-2.md" in prompt


class TestTriageInbox:
    async def test_returns_triage_batch(self, tmp_vault, monkeypatch):
        monkeypatch.setenv("SECOND_BRAIN_VAULT", str(tmp_vault))
        note = tmp_vault / "0_inbox" / "test.md"
        note.write_text("# Plan Hawaii Trip\n\nBook flights by March.")

        with triage_agent.override(model=TestModel()):
            result = await triage_inbox([note], vault_dir=tmp_vault)
            assert isinstance(result, TriageBatch)
```

**Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_triage_runner.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.triage_runner'`

**Step 3: Write implementation**

```python
# agents/triage_runner.py
from pathlib import Path

from config.agent_config import VAULT_DIR
from models.triage import TriageBatch

MAX_FILE_CONTENT = 3072  # 3KB per file


def build_triage_prompt(files: list[Path], vault_dir: Path) -> str:
    """Build the triage prompt from inbox file contents."""
    file_sections = []
    for f in files:
        try:
            content = f.read_text(errors="replace")
            if len(content) > MAX_FILE_CONTENT:
                content = content[:MAX_FILE_CONTENT] + "\n[... truncated ...]"
            file_sections.append(f"## File: {f.name}\n\n{content}")
        except Exception as e:
            file_sections.append(f"## File: {f.name}\n\nError reading file: {e}")

    return (
        "Route these inbox files using the PARA decision tree.\n"
        "Use the read_routes_tool to get routing rules and "
        "list_vault_directories to see the current structure.\n\n"
        "### Files to Triage\n\n"
        + "\n\n---\n\n".join(file_sections)
    )


async def triage_inbox(
    files: list[Path],
    vault_dir: Path | None = None,
) -> TriageBatch:
    """Run the triage agent on a list of inbox files. Returns decisions only."""
    from agents.triage_agent import triage_agent

    vault = vault_dir or VAULT_DIR
    prompt = build_triage_prompt(files, vault)
    result = await triage_agent.run(prompt)
    return result.output
```

Note: DBOS wrapping is added in a later step after the basic flow works, to keep this testable with `TestModel` first.

**Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_triage_runner.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add agents/triage_runner.py tests/test_triage_runner.py
git commit -m "feat: add triage runner with prompt builder

build_triage_prompt formats inbox files for the agent.
triage_inbox calls agent and returns TriageBatch."
```

---

### Task 9: CLI Entry Point

**Files:**
- Create: `agents/run_triage.py`
- Create: `tests/test_run_triage.py`

**Step 1: Write the failing tests**

```python
# tests/test_run_triage.py
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from agents.run_triage import execute_decisions, find_inbox_files
from models.triage import PARADestination, TriageBatch, TriageDecision


class TestFindInboxFiles:
    def test_finds_md_files(self, tmp_vault):
        (tmp_vault / "0_inbox" / "note1.md").write_text("# Note 1")
        (tmp_vault / "0_inbox" / "note2.md").write_text("# Note 2")
        files = find_inbox_files(tmp_vault)
        assert len(files) == 2
        names = {f.name for f in files}
        assert "note1.md" in names
        assert "note2.md" in names

    def test_excludes_gitkeep(self, tmp_vault):
        (tmp_vault / "0_inbox" / ".gitkeep").write_text("")
        (tmp_vault / "0_inbox" / "note.md").write_text("# Note")
        files = find_inbox_files(tmp_vault)
        assert len(files) == 1

    def test_empty_inbox(self, tmp_vault):
        files = find_inbox_files(tmp_vault)
        assert len(files) == 0


class TestExecuteDecisions:
    def test_high_confidence_moves_file(self, tmp_vault):
        note = tmp_vault / "0_inbox" / "trip.md"
        note.write_text("---\ncaptured_at: 2026-02-19\n---\n# Hawaii Trip")
        batch = TriageBatch(
            decisions=[
                TriageDecision(
                    filename="trip.md",
                    destination=PARADestination.PROJECTS_ACTIVE,
                    subdirectory="hawaii-2026",
                    confidence=0.9,
                    reasoning="Has deadline",
                    suggested_rename="hawaii-trip.md",
                    tags=["travel"],
                ),
            ],
            skipped=[],
        )
        stats = execute_decisions(batch, tmp_vault)
        assert stats["moved"] == 1
        assert stats["kept"] == 0
        # File should be at new location
        dest = tmp_vault / "1_projects" / "active" / "hawaii-2026" / "hawaii-trip.md"
        assert dest.exists()
        # Original should be gone
        assert not note.exists()

    def test_low_confidence_keeps_in_inbox(self, tmp_vault):
        note = tmp_vault / "0_inbox" / "vague.md"
        note.write_text("---\ncaptured_at: 2026-02-19\n---\n# Something")
        batch = TriageBatch(
            decisions=[
                TriageDecision(
                    filename="vague.md",
                    destination=PARADestination.AREAS,
                    subdirectory="Health",
                    confidence=0.4,
                    reasoning="Uncertain",
                    suggested_rename=None,
                    tags=[],
                ),
            ],
            skipped=[],
        )
        stats = execute_decisions(batch, tmp_vault)
        assert stats["moved"] == 0
        assert stats["kept"] == 1
        # File should still be in inbox
        assert note.exists()
        # Should have needs_triage in frontmatter
        content = note.read_text()
        assert "needs_triage" in content

    def test_processing_log_updated(self, tmp_vault):
        note = tmp_vault / "0_inbox" / "note.md"
        note.write_text("# Test")
        batch = TriageBatch(
            decisions=[
                TriageDecision(
                    filename="note.md",
                    destination=PARADestination.RESOURCES,
                    subdirectory="Technology",
                    confidence=0.85,
                    reasoning="Reference material",
                    suggested_rename=None,
                    tags=["tech"],
                ),
            ],
            skipped=[],
        )
        execute_decisions(batch, tmp_vault)
        log = (tmp_vault / "_system" / "processing-log.md").read_text()
        assert "pydantic-ai/triage" in log
        assert "note.md" in log
```

**Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_run_triage.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.run_triage'`

**Step 3: Write implementation**

```python
# agents/run_triage.py
"""CLI entry point for PydanticAI triage agent.

Usage:
    python3 agents/run_triage.py --all
    python3 agents/run_triage.py --files note1.md note2.md

Exit codes:
    0 = success (all items routed)
    1 = error
    2 = some items need review (low confidence)
"""
import argparse
import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

from config.agent_config import INPUT_PRICE, OUTPUT_PRICE, STATE_DB_PATH, VAULT_DIR
from models.triage import TriageBatch, TriageDecision
from tools.vault_write import append_processing_log, move_file, update_frontmatter

CONFIDENCE_THRESHOLD = 0.7


def find_inbox_files(vault_dir: Path) -> list[Path]:
    """Find all .md files in 0_inbox/ (excluding .gitkeep)."""
    inbox = vault_dir / "0_inbox"
    if not inbox.is_dir():
        return []
    return sorted(
        f
        for f in inbox.glob("*.md")
        if f.name != ".gitkeep"
    )


def execute_decisions(batch: TriageBatch, vault_dir: Path) -> dict:
    """Execute triage decisions: move files or mark for review."""
    stats = {"moved": 0, "kept": 0, "skipped": len(batch.skipped)}

    for decision in batch.decisions:
        source_rel = f"0_inbox/{decision.filename}"
        source_path = vault_dir / source_rel

        if not source_path.exists():
            print(f"  WARNING: {decision.filename} not found in inbox, skipping")
            stats["skipped"] += 1
            continue

        if decision.confidence >= CONFIDENCE_THRESHOLD:
            # Build destination path
            dest_parts = [decision.destination.value]
            if decision.subdirectory:
                dest_parts.append(decision.subdirectory)
            filename = decision.suggested_rename or decision.filename
            dest_parts.append(filename)
            dest_rel = "/".join(dest_parts)

            # Update frontmatter before moving
            update_frontmatter(source_path, {
                "para": decision.destination.value.split("_")[-1].split("/")[0],
                "status": "triaged",
                "triage_confidence": decision.confidence,
                "triage_notes": decision.reasoning,
                "tags": json.dumps(decision.tags) if decision.tags else "[]",
            })

            # Move file
            move_file(vault_dir, source_rel, dest_rel)
            stats["moved"] += 1

            # Log to processing log
            append_processing_log(
                vault_dir,
                source_path=source_rel,
                destination_path=dest_rel,
                confidence=decision.confidence,
            )
            print(f"  MOVED: {decision.filename} -> {dest_rel} ({decision.confidence:.0%})")

        else:
            # Low confidence: keep in inbox, mark needs_triage
            update_frontmatter(source_path, {
                "needs_triage": "true",
                "triage_confidence": decision.confidence,
                "triage_notes": decision.reasoning,
            })
            stats["kept"] += 1

            append_processing_log(
                vault_dir,
                source_path=source_rel,
                destination_path=f"{source_rel} (kept)",
                confidence=decision.confidence,
                warnings="needs_triage: low confidence",
            )
            print(f"  KEPT:  {decision.filename} in inbox ({decision.confidence:.0%} < threshold)")

    return stats


async def _run(files: list[Path], vault_dir: Path) -> int:
    """Run the triage agent and execute decisions."""
    from agents.triage_runner import triage_inbox
    from state.db import get_connection, init_schema
    from state.runs import log_run_complete, log_run_error, log_run_start

    run_id = str(uuid.uuid4())
    input_summary = ", ".join(f.name for f in files)

    # Initialize state
    conn = get_connection()
    init_schema(conn)
    log_run_start(conn, run_id, "triage", input_summary)

    start_time = time.monotonic()
    try:
        batch = await triage_inbox(files, vault_dir=vault_dir)
        duration_ms = int((time.monotonic() - start_time) * 1000)

        stats = execute_decisions(batch, vault_dir)

        # Log completion (token counts from result not available via triage_inbox,
        # will be enhanced when we wire up result.usage() directly)
        log_run_complete(
            conn,
            run_id=run_id,
            output_summary=batch.model_dump_json(),
            tokens_in=0,  # TODO: wire up from result.usage()
            tokens_out=0,
            cost_usd=0.0,
            duration_ms=duration_ms,
        )
        conn.close()

        print(f"\nTriage complete: {stats['moved']} moved, {stats['kept']} kept, {stats['skipped']} skipped")

        return 2 if stats["kept"] > 0 else 0

    except Exception as e:
        duration_ms = int((time.monotonic() - start_time) * 1000)
        log_run_error(conn, run_id, str(e))
        conn.close()
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(description="Run PydanticAI triage on inbox files")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Process all files in 0_inbox/")
    group.add_argument("--files", nargs="+", help="Specific files to process")
    args = parser.parse_args()

    vault_dir = VAULT_DIR

    if args.all:
        files = find_inbox_files(vault_dir)
    else:
        files = [vault_dir / "0_inbox" / f for f in args.files]

    if not files:
        print("inbox-triage: no files to process")
        sys.exit(0)

    print(f"inbox-triage: processing {len(files)} file(s)")
    exit_code = asyncio.run(_run(files, vault_dir))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
```

**Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_run_triage.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add agents/run_triage.py tests/test_run_triage.py
git commit -m "feat: add CLI entry point for triage agent

run_triage.py: --all or --files mode, executes decisions (move/keep),
updates frontmatter, appends processing-log, logs to SQLite.
Exit codes: 0=success, 1=error, 2=needs review."
```

---

### Task 10: DBOS Integration

**Files:**
- Modify: `agents/triage_runner.py`
- Create: `tests/test_dbos_integration.py`

**Step 1: Write a test that verifies DBOS wrapping**

```python
# tests/test_dbos_integration.py
import pytest

from agents.triage_runner import triage_inbox


class TestDBOSIntegration:
    def test_triage_inbox_is_callable(self):
        """Verify triage_inbox exists and is an async function."""
        import asyncio
        assert asyncio.iscoroutinefunction(triage_inbox)
```

Note: Full DBOS crash recovery testing is deferred to Phase 3 (P3.11). For Phase 1 we verify the wrapping doesn't break the basic flow.

**Step 2: Run test to verify it passes (it should already)**

Run: `.venv/bin/pytest tests/test_dbos_integration.py -v`
Expected: PASS

**Step 3: Add DBOS wrapping to triage_runner.py**

Update `agents/triage_runner.py` to use `DBOSAgent`:

```python
# agents/triage_runner.py — updated with DBOS
from pathlib import Path

from dbos import DBOS, DBOSConfig

from config.agent_config import STATE_DB_PATH, VAULT_DIR
from models.triage import TriageBatch

MAX_FILE_CONTENT = 3072

# Configure DBOS
_dbos_config: DBOSConfig = {
    "name": "second_brain_agents",
    "system_database_url": f"sqlite:///{STATE_DB_PATH}",
}
DBOS(config=_dbos_config)


def build_triage_prompt(files: list[Path], vault_dir: Path) -> str:
    """Build the triage prompt from inbox file contents."""
    file_sections = []
    for f in files:
        try:
            content = f.read_text(errors="replace")
            if len(content) > MAX_FILE_CONTENT:
                content = content[:MAX_FILE_CONTENT] + "\n[... truncated ...]"
            file_sections.append(f"## File: {f.name}\n\n{content}")
        except Exception as e:
            file_sections.append(f"## File: {f.name}\n\nError reading file: {e}")

    return (
        "Route these inbox files using the PARA decision tree.\n"
        "Use the read_routes_tool to get routing rules and "
        "list_vault_directories to see the current structure.\n\n"
        "### Files to Triage\n\n"
        + "\n\n---\n\n".join(file_sections)
    )


async def triage_inbox(
    files: list[Path],
    vault_dir: Path | None = None,
) -> TriageBatch:
    """Run the triage agent on a list of inbox files. Returns decisions only.

    Wrapped with DBOS for crash-resilient durable execution.
    """
    from pydantic_ai.durable_exec.dbos import DBOSAgent

    from agents.triage_agent import triage_agent

    vault = vault_dir or VAULT_DIR
    prompt = build_triage_prompt(files, vault)

    durable_triage = DBOSAgent(triage_agent)
    DBOS.launch()

    result = await durable_triage.run(prompt)
    return result.output
```

**Step 4: Run all tests to verify nothing broke**

Run: `.venv/bin/pytest tests/ -v`
Expected: All tests PASS

Note: If DBOS initialization causes issues in tests (e.g., trying to create DB at the VM path), you may need to set `SECOND_BRAIN_STATE_DB` env var in conftest.py. Add this to `conftest.py`:

```python
@pytest.fixture(autouse=True)
def set_test_env(tmp_path, monkeypatch):
    """Set environment variables for test isolation."""
    monkeypatch.setenv("SECOND_BRAIN_STATE_DB", str(tmp_path / "test_agents.db"))
    monkeypatch.setenv("SECOND_BRAIN_VAULT", str(tmp_path))
```

If `DBOS()` and `DBOS.launch()` cause issues when called multiple times across tests, move the DBOS initialization behind a guard or into `run_triage.py`'s `_run()` function instead of at module level.

**Step 5: Commit**

```bash
git add agents/triage_runner.py tests/test_dbos_integration.py tests/conftest.py
git commit -m "feat: add DBOS durable execution wrapping

triage_inbox now uses DBOSAgent for crash-resilient execution.
DBOS configured with SQLite at STATE_DB_PATH."
```

---

### Task 11: Bash Integration

**Files:**
- Modify: `scripts/inbox-triage.sh`

**Step 1: Save backup**

Run: `cp /Users/patrick/workspace/second-brain/scripts/inbox-triage.sh /Users/patrick/workspace/second-brain/scripts/inbox-triage.sh.bak`

**Step 2: Modify inbox-triage.sh**

Replace the Claude Code call with the Python agent call. The modified script:

```bash
#!/usr/bin/env bash
# inbox-triage.sh — Run PydanticAI triage agent on inbox files.
# Called by inbox-watcher.sh when new files are detected.
# Respects the same lock as other automation to avoid conflicts.
set -euo pipefail

VAULT_DIR="${VAULT_DIR:-/home/ubuntu/second-brain}"
LOCK_FILE="${LOCK_FILE:-/srv/locks/claude-exec.lock}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# --- Acquire lock (non-blocking). If interactive or other automation holds it, skip. ---
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    echo "inbox-triage: skipped (lock held by another session)"
    happy notify "Inbox triage skipped: session active" 2>/dev/null || true
    exit 0
fi

# --- Check inbox for actual files ---
INBOX="$VAULT_DIR/0_inbox"
FILES=$(find "$INBOX" -maxdepth 1 -type f -name '*.md' ! -name '.gitkeep' 2>/dev/null)

if [[ -z "$FILES" ]]; then
    echo "inbox-triage: no files to process"
    exit 0
fi

FILE_COUNT=$(echo "$FILES" | wc -l)
echo "inbox-triage: processing $FILE_COUNT file(s)"

# --- Run PydanticAI triage agent ---
cd "$VAULT_DIR"

# Activate virtual environment
if [[ -f "${VAULT_DIR}/.venv/bin/activate" ]]; then
    source "${VAULT_DIR}/.venv/bin/activate"
else
    echo "inbox-triage: ERROR — .venv not found at ${VAULT_DIR}/.venv"
    happy notify "Inbox triage failed: .venv not found" 2>/dev/null || true
    exit 1
fi

# Run the Python triage agent
python3 "${VAULT_DIR}/agents/run_triage.py" --all
RESULT=$?

case $RESULT in
    0)
        echo "inbox-triage: complete"
        happy notify "Inbox triage: processed $FILE_COUNT file(s)" 2>/dev/null || true
        ;;
    2)
        echo "inbox-triage: complete (some items need review)"
        happy notify "Inbox triage: $FILE_COUNT file(s) processed, some need review" 2>/dev/null || true
        ;;
    *)
        echo "inbox-triage: failed (exit code $RESULT)"
        happy notify "Inbox triage failed" 2>/dev/null || true
        exit 1
        ;;
esac
```

**Step 3: Verify the script is syntactically valid**

Run: `bash -n /Users/patrick/workspace/second-brain/scripts/inbox-triage.sh`
Expected: No output (valid syntax)

**Step 4: Commit**

```bash
git add scripts/inbox-triage.sh scripts/inbox-triage.sh.bak
git commit -m "feat: modify inbox-triage.sh to call PydanticAI agent

Replaces 'claude --print /triage all' with Python agent call.
Activates .venv, handles exit codes (0=success, 2=review, 1=error).
Backup saved as inbox-triage.sh.bak for rollback."
```

---

### Task 12: Install Script Updates

**Files:**
- Modify: `install.sh`

**Step 1: Add Python setup section to install.sh**

Add a new section between the existing "Deploy Scripts" and "Deploy Claude Code Slash Commands" sections (after section 3, before section 4). Renumber subsequent sections.

Insert after the `echo "  Done."` line at the end of section 3:

```bash
# ==============================================================================
# 3b. Python Environment Setup
# ==============================================================================

echo "--- [3b/7] Python Environment Setup ---"

# Create virtual environment if it doesn't exist
if [[ ! -d "${VAULT_DIR}/.venv" ]]; then
    echo "  Creating Python virtual environment..."
    python3 -m venv "${VAULT_DIR}/.venv"
else
    echo "  Virtual environment already exists."
fi

# Install/upgrade dependencies
echo "  Installing Python dependencies..."
"${VAULT_DIR}/.venv/bin/pip" install --quiet -e "${VAULT_DIR}"

# Create state directory
STATE_DIR="/home/ubuntu/second-brain-state"
echo "  Creating state directory: $STATE_DIR"
mkdir -p "$STATE_DIR"

# Initialize database schema
echo "  Initializing agents.db schema..."
"${VAULT_DIR}/.venv/bin/python3" -c "
from state.db import get_connection, init_schema
conn = get_connection()
init_schema(conn)
conn.close()
print('    Schema initialized successfully.')
"

echo "  Done."
echo ""
```

Also add to the verification section:

```bash
echo "  Python environment:"
if [[ -f "${VAULT_DIR}/.venv/bin/python3" ]]; then
    echo "    .venv — OK"
    echo "    Python: $("${VAULT_DIR}/.venv/bin/python3" --version)"
else
    echo "    .venv — MISSING"
fi

echo "  State database:"
if [[ -f "$STATE_DIR/agents.db" ]]; then
    echo "    agents.db — OK"
else
    echo "    agents.db — MISSING"
fi
```

**Step 2: Verify syntax**

Run: `bash -n /Users/patrick/workspace/second-brain/install.sh`
Expected: No output (valid syntax)

**Step 3: Commit**

```bash
git add install.sh
git commit -m "feat: add Python venv setup and schema init to install.sh

Creates .venv, installs pydantic-ai deps, creates state directory,
initializes agents.db schema. Adds verification checks."
```

---

### Task 13: Integration Test

**Files:**
- Create: `tests/test_triage_flow.py`

**Step 1: Write the integration test**

This test exercises the full flow: inbox files → agent decisions → file moves → frontmatter → processing log → SQLite.

```python
# tests/test_triage_flow.py
import json

import pytest
from pydantic_ai.models.test import TestModel

from agents.run_triage import execute_decisions, find_inbox_files
from agents.triage_agent import triage_agent
from agents.triage_runner import triage_inbox
from models.triage import PARADestination, TriageBatch, TriageDecision
from state.db import get_connection, init_schema
from state.runs import log_run_complete, log_run_start


class TestFullTriageFlow:
    """Integration test: full triage flow with temp vault and TestModel."""

    def test_high_confidence_file_moves_to_destination(self, tmp_vault):
        """A high-confidence decision moves the file and updates everything."""
        # Setup: create inbox file
        note = tmp_vault / "0_inbox" / "hawaii-planning.md"
        note.write_text(
            "---\n"
            "captured_at: 2026-02-19T10:00:00-0800\n"
            "source: telegram\n"
            "---\n"
            "# Plan Hawaii Trip\n\n"
            "Book flights for April. Budget $3000. Deadline April 15.\n"
        )

        # Simulate agent output (we test execute_decisions directly
        # since TestModel can't produce semantically correct decisions)
        batch = TriageBatch(
            decisions=[
                TriageDecision(
                    filename="hawaii-planning.md",
                    destination=PARADestination.PROJECTS_ACTIVE,
                    subdirectory="hawaii-2026",
                    confidence=0.9,
                    reasoning="Q1: Has deadline (April 15) and deliverable (trip booked)",
                    suggested_rename="hawaii-trip.md",
                    tags=["travel", "project"],
                ),
            ],
            skipped=[],
        )

        stats = execute_decisions(batch, tmp_vault)

        # Verify file moved
        dest = tmp_vault / "1_projects" / "active" / "hawaii-2026" / "hawaii-trip.md"
        assert dest.exists()
        assert not note.exists()

        # Verify frontmatter updated
        content = dest.read_text()
        assert "captured_at: 2026-02-19T10:00:00-0800" in content  # preserved
        assert "status: triaged" in content
        assert "triage_confidence: 0.9" in content

        # Verify processing log
        log = (tmp_vault / "_system" / "processing-log.md").read_text()
        assert "hawaii-planning.md" in log
        assert "pydantic-ai/triage" in log

        # Verify stats
        assert stats["moved"] == 1
        assert stats["kept"] == 0

    def test_low_confidence_stays_in_inbox(self, tmp_vault):
        """A low-confidence decision keeps the file and marks needs_triage."""
        note = tmp_vault / "0_inbox" / "vague-note.md"
        note.write_text("---\ncaptured_at: 2026-02-19\n---\n# Something\n\nUnclear.")

        batch = TriageBatch(
            decisions=[
                TriageDecision(
                    filename="vague-note.md",
                    destination=PARADestination.AREAS,
                    subdirectory="Health",
                    confidence=0.4,
                    reasoning="Q5: Cannot confidently classify",
                    suggested_rename=None,
                    tags=[],
                ),
            ],
            skipped=[],
        )

        stats = execute_decisions(batch, tmp_vault)

        # File stays in inbox
        assert note.exists()
        content = note.read_text()
        assert "needs_triage: true" in content

        assert stats["moved"] == 0
        assert stats["kept"] == 1

    def test_state_db_records_run(self, tmp_db):
        """SQLite logs the agent run."""
        conn = get_connection(tmp_db)
        init_schema(conn)
        log_run_start(conn, "integration-test-1", "triage", "note1.md, note2.md")
        log_run_complete(
            conn,
            run_id="integration-test-1",
            output_summary='{"decisions": [], "skipped": []}',
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.001,
            duration_ms=2500,
        )

        row = conn.execute(
            "SELECT status, tokens_in, cost_usd FROM agent_runs WHERE run_id=?",
            ("integration-test-1",),
        ).fetchone()
        assert row[0] == "completed"
        assert row[1] == 100
        conn.close()

    async def test_agent_produces_valid_batch_with_testmodel(self, tmp_vault, monkeypatch):
        """Agent returns a valid TriageBatch when using TestModel."""
        monkeypatch.setenv("SECOND_BRAIN_VAULT", str(tmp_vault))

        note = tmp_vault / "0_inbox" / "test.md"
        note.write_text("# Test note\n\nSome content for triage.")

        with triage_agent.override(model=TestModel()):
            batch = await triage_inbox([note], vault_dir=tmp_vault)
            assert isinstance(batch, TriageBatch)

    def test_find_inbox_files_integration(self, tmp_vault):
        """find_inbox_files returns correct files from a realistic vault."""
        (tmp_vault / "0_inbox" / "note-a.md").write_text("# A")
        (tmp_vault / "0_inbox" / "note-b.md").write_text("# B")
        (tmp_vault / "0_inbox" / "image.jpg").write_bytes(b"\xff\xd8")  # not .md
        (tmp_vault / "0_inbox" / ".gitkeep").write_text("")

        files = find_inbox_files(tmp_vault)
        names = {f.name for f in files}
        assert names == {"note-a.md", "note-b.md"}
```

**Step 2: Run all tests**

Run: `.venv/bin/pytest tests/ -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/test_triage_flow.py
git commit -m "feat: add integration tests for full triage flow

Tests: high-confidence move, low-confidence keep, SQLite logging,
TestModel agent run, inbox file discovery."
```

---

### Task 14: Final Verification & Cleanup

**Step 1: Run full test suite**

Run: `.venv/bin/pytest tests/ -v --tb=short`
Expected: All tests PASS

**Step 2: Verify directory structure matches design**

Run: `find agents models state tools config tests -type f | sort`
Expected output:
```
agents/__init__.py
agents/run_triage.py
agents/triage_agent.py
agents/triage_runner.py
config/__init__.py
config/agent_config.py
config/prompts/triage_system.md
models/__init__.py
models/triage.py
state/__init__.py
state/db.py
state/runs.py
tests/__init__.py
tests/conftest.py
tests/test_dbos_integration.py
tests/test_models.py
tests/test_run_triage.py
tests/test_state_db.py
tests/test_triage_agent.py
tests/test_triage_flow.py
tests/test_vault_read.py
tests/test_vault_write.py
tools/__init__.py
tools/vault_read.py
tools/vault_write.py
```

**Step 3: (Optional) Run a real API test locally**

Set `SECOND_BRAIN_VAULT` to the local vault and run:

```bash
export SECOND_BRAIN_VAULT=/Users/patrick/workspace/second-brain
export SECOND_BRAIN_STATE_DB=/tmp/test-agents.db
.venv/bin/python3 agents/run_triage.py --all
```

Verify:
- Agent returns valid decisions
- Files are moved correctly (or kept for low confidence)
- `_system/processing-log.md` is updated
- `/tmp/test-agents.db` has a row in `agent_runs`

**Step 4: Final commit if any cleanup needed**

```bash
git add -A
git commit -m "chore: final cleanup for Phase 1 triage agent"
```

---

## Summary

| Task | What | Files | Test File |
|------|------|-------|-----------|
| 1 | Project setup | pyproject.toml, config/, __init__.py files, conftest.py | — |
| 2 | Data models | models/triage.py | tests/test_models.py |
| 3 | State layer | state/db.py, state/runs.py | tests/test_state_db.py |
| 4 | Vault read tools | tools/vault_read.py | tests/test_vault_read.py |
| 5 | Vault write tools | tools/vault_write.py | tests/test_vault_write.py |
| 6 | System prompt | config/prompts/triage_system.md | — |
| 7 | Triage agent | agents/triage_agent.py | tests/test_triage_agent.py |
| 8 | Triage runner | agents/triage_runner.py | tests/test_triage_runner.py |
| 9 | CLI entry point | agents/run_triage.py | tests/test_run_triage.py |
| 10 | DBOS integration | agents/triage_runner.py (modify) | tests/test_dbos_integration.py |
| 11 | Bash integration | scripts/inbox-triage.sh | — (manual test) |
| 12 | Install script | install.sh | — (manual test on VM) |
| 13 | Integration tests | — | tests/test_triage_flow.py |
| 14 | Final verification | — | Full suite |

**Total: 14 tasks, ~14 commits, estimated 2-3 sessions**
