import pytest
from pydantic_ai.models.test import TestModel

from agents.triage_agent import triage_agent
from models.triage import TriageBatch


class TestTriageAgentDefinition:
    def test_agent_has_correct_name(self):
        assert triage_agent.name == "triage"

    def test_agent_has_retries(self):
        assert triage_agent._max_result_retries == 2

    def test_agent_tools_registered(self):
        """Verify the agent has read_routes_tool and list_vault_directories tools."""
        tool_names = list(triage_agent._function_toolset.tools.keys())
        assert "read_routes_tool" in tool_names
        assert "list_vault_directories" in tool_names


class TestTriageAgentRun:
    async def test_agent_returns_triage_batch(self, tmp_vault, monkeypatch):
        """TestModel generates data matching TriageBatch schema."""
        monkeypatch.setenv("SECOND_BRAIN_VAULT", str(tmp_vault))

        # Create a sample inbox file
        inbox_file = tmp_vault / "0_inbox" / "test-note.md"
        inbox_file.write_text("# Plan Hawaii Trip\n\nBook flights for April.")

        with triage_agent.override(model=TestModel()):
            result = await triage_agent.run(
                "Route these inbox files:\n\n## File: test-note.md\n\n# Plan Hawaii Trip\nBook flights."
            )
            assert isinstance(result.output, TriageBatch)
