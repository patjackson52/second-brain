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
