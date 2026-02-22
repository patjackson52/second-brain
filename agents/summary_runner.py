from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

from models.summary import DailySummary, WeeklySummary

if TYPE_CHECKING:
    from pydantic_ai.result import AgentRunResult

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
) -> AgentRunResult:
    """Run the summary agent. Returns full result for usage tracking."""
    from agents.summary_agent import summary_agent

    if mode == "daily":
        prompt = build_daily_prompt(files, date_str)
        return await summary_agent.run(prompt, output_type=DailySummary)
    else:
        prompt = build_weekly_prompt(files, daily_summaries, date_str)
        return await summary_agent.run(prompt, output_type=WeeklySummary)
