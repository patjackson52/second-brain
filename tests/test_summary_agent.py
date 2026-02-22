from __future__ import annotations

import pytest
from pydantic_ai.models.test import TestModel

from agents.summary_agent import summary_agent
from models.summary import DailySummary, WeeklySummary


class TestSummaryAgentDefinition:
    def test_agent_has_correct_name(self):
        assert summary_agent.name == "summary"

    def test_agent_has_retries(self):
        assert summary_agent._max_result_retries == 2

    def test_agent_has_no_tools(self):
        tools = summary_agent._function_toolset.tools
        assert len(tools) == 0


class TestSummaryAgentRun:
    async def test_agent_returns_daily_summary(self):
        with summary_agent.override(model=TestModel()):
            result = await summary_agent.run(
                "Summarize today's changes.",
                output_type=DailySummary,
            )
            assert isinstance(result.output, DailySummary)

    async def test_agent_returns_weekly_summary(self):
        with summary_agent.override(model=TestModel()):
            result = await summary_agent.run(
                "Summarize this week's changes.",
                output_type=WeeklySummary,
            )
            assert isinstance(result.output, WeeklySummary)
