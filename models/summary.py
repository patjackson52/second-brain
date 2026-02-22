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
