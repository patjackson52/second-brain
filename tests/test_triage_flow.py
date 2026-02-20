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
