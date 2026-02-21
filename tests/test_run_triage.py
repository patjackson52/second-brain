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
