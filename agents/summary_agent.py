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
