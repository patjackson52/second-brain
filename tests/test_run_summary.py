from __future__ import annotations

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
