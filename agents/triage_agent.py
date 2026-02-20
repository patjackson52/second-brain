from __future__ import annotations

from pathlib import Path

from pydantic_ai import Agent

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
    defer_model_check=True,
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
