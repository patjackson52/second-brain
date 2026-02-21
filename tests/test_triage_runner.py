from pathlib import Path

import pytest
from pydantic_ai.models.test import TestModel

from agents.triage_agent import triage_agent
from agents.triage_runner import build_triage_prompt, triage_inbox
from models.triage import TriageBatch


class TestBuildTriagePrompt:
    def test_includes_file_contents(self, tmp_vault):
        note = tmp_vault / "0_inbox" / "test.md"
        note.write_text("# Test Note\n\nSome content.")
        prompt = build_triage_prompt([note], tmp_vault)
        assert "test.md" in prompt
        assert "Test Note" in prompt

    def test_caps_file_content(self, tmp_vault):
        note = tmp_vault / "0_inbox" / "big.md"
        note.write_text("x" * 5000)
        prompt = build_triage_prompt([note], tmp_vault)
        # Content should be capped, prompt should not be enormous
        assert len(prompt) < 10000

    def test_includes_multiple_files(self, tmp_vault):
        for i in range(3):
            note = tmp_vault / "0_inbox" / f"note-{i}.md"
            note.write_text(f"# Note {i}")
        files = list((tmp_vault / "0_inbox").glob("*.md"))
        prompt = build_triage_prompt(files, tmp_vault)
        assert "note-0.md" in prompt
        assert "note-1.md" in prompt
        assert "note-2.md" in prompt


class TestTriageInbox:
    async def test_returns_triage_batch(self, tmp_vault, monkeypatch):
        monkeypatch.setenv("SECOND_BRAIN_VAULT", str(tmp_vault))
        note = tmp_vault / "0_inbox" / "test.md"
        note.write_text("# Plan Hawaii Trip\n\nBook flights by March.")

        with triage_agent.override(model=TestModel()):
            result = await triage_inbox([note], vault_dir=tmp_vault)
            assert isinstance(result.output, TriageBatch)
            # Verify usage data is accessible
            usage = result.usage()
            assert usage.input_tokens is not None
