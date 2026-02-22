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

        with summary_agent.override(model=TestModel()):
            result = await run_summary("daily", [note], [], vault_dir=tmp_vault, date_str="2026-02-21")
            assert isinstance(result.output, DailySummary)

    async def test_weekly_returns_result(self, tmp_vault, monkeypatch):
        monkeypatch.setenv("SECOND_BRAIN_VAULT", str(tmp_vault))

        with summary_agent.override(model=TestModel()):
            result = await run_summary("weekly", [], [], vault_dir=tmp_vault, date_str="2026-W08")
            assert isinstance(result.output, WeeklySummary)
