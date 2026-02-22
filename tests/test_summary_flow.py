from __future__ import annotations

import pytest
from pydantic_ai.models.test import TestModel

from agents.run_summary import determine_output_path, write_summary_file
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

        with summary_agent.override(model=TestModel()):
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
