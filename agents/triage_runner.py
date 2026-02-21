from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

from config.agent_config import VAULT_DIR
from models.triage import TriageBatch

if TYPE_CHECKING:
    from pydantic_ai.run import AgentRunResult

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


def _has_dbos() -> bool:
    """Check if DBOS + PydanticAI DBOS integration are both available."""
    try:
        from dbos import DBOS  # noqa: F401
        from pydantic_ai.durable_exec.dbos import DBOSAgent  # noqa: F401
        return True
    except (ImportError, ModuleNotFoundError):
        return False


async def triage_inbox(
    files: list[Path],
    vault_dir: Optional[Path] = None,
) -> "AgentRunResult[TriageBatch]":
    """Run the triage agent on a list of inbox files.

    Returns the full RunResult so callers can access .output, .usage(), etc.

    Uses DBOS for durable execution when available (Python 3.11+).
    Falls back to direct agent call on older Python versions.
    """
    from agents.triage_agent import triage_agent

    vault = vault_dir or VAULT_DIR
    prompt = build_triage_prompt(files, vault)

    if _has_dbos():
        from dbos import DBOS, DBOSConfig
        from pydantic_ai.durable_exec.dbos import DBOSAgent

        from config.agent_config import STATE_DB_PATH

        _dbos_config: DBOSConfig = {
            "name": "second_brain_agents",
            "system_database_url": f"sqlite:///{STATE_DB_PATH}",
        }
        DBOS(config=_dbos_config)
        DBOS.launch()
        durable_triage = DBOSAgent(triage_agent)
        result = await durable_triage.run(prompt)
    else:
        result = await triage_agent.run(prompt)

    return result
