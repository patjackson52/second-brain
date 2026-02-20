from __future__ import annotations

from pathlib import Path
from typing import Optional

from config.agent_config import VAULT_DIR
from models.triage import TriageBatch

MAX_FILE_CONTENT = 3072  # 3KB per file


def build_triage_prompt(files: list[Path], vault_dir: Path) -> str:
    """Build the triage prompt from inbox file contents."""
    file_sections = []
    for f in files:
        try:
            content = f.read_text(errors="replace")
            if len(content) > MAX_FILE_CONTENT:
                content = content[:MAX_FILE_CONTENT] + "\n[... truncated ...]"
            file_sections.append(f"## File: {f.name}\n\n{content}")
        except Exception as e:
            file_sections.append(f"## File: {f.name}\n\nError reading file: {e}")

    return (
        "Route these inbox files using the PARA decision tree.\n"
        "Use the read_routes_tool to get routing rules and "
        "list_vault_directories to see the current structure.\n\n"
        "### Files to Triage\n\n"
        + "\n\n---\n\n".join(file_sections)
    )


async def triage_inbox(
    files: list[Path],
    vault_dir: Optional[Path] = None,
) -> TriageBatch:
    """Run the triage agent on a list of inbox files. Returns decisions only."""
    from agents.triage_agent import triage_agent

    vault = vault_dir or VAULT_DIR
    prompt = build_triage_prompt(files, vault)
    result = await triage_agent.run(prompt)
    return result.output
