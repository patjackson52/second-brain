import re
from pathlib import Path

from tools.vault_write import append_processing_log, move_file, update_frontmatter


class TestMoveFile:
    def test_moves_file(self, tmp_vault):
        src = tmp_vault / "0_inbox" / "note.md"
        src.write_text("# Test")
        dest_dir = tmp_vault / "2_areas" / "Health"
        move_file(tmp_vault, "0_inbox/note.md", "2_areas/Health/note.md")
        assert not src.exists()
        assert (dest_dir / "note.md").exists()
        assert (dest_dir / "note.md").read_text() == "# Test"

    def test_creates_destination_directory(self, tmp_vault):
        src = tmp_vault / "0_inbox" / "note.md"
        src.write_text("# Test")
        move_file(tmp_vault, "0_inbox/note.md", "3_resources/NewTopic/note.md")
        assert (tmp_vault / "3_resources" / "NewTopic" / "note.md").exists()

    def test_move_nonexistent_raises(self, tmp_vault):
        try:
            move_file(tmp_vault, "0_inbox/nope.md", "2_areas/Health/nope.md")
            assert False, "Should have raised"
        except FileNotFoundError:
            pass


class TestUpdateFrontmatter:
    def test_adds_frontmatter_to_file_without(self, tmp_vault):
        note = tmp_vault / "0_inbox" / "bare.md"
        note.write_text("# No frontmatter\n\nJust content.")
        update_frontmatter(note, {"para": "area", "status": "triaged"})
        content = note.read_text()
        assert content.startswith("---\n")
        assert "para: area" in content
        assert "status: triaged" in content
        assert "# No frontmatter" in content

    def test_merges_into_existing_frontmatter(self, tmp_vault):
        note = tmp_vault / "0_inbox" / "existing.md"
        note.write_text(
            "---\n"
            "captured_at: 2026-02-19T10:00:00-0800\n"
            "source: telegram\n"
            "---\n"
            "# Content\n"
        )
        update_frontmatter(note, {"para": "project", "triage_confidence": 0.9})
        content = note.read_text()
        assert "captured_at: 2026-02-19T10:00:00-0800" in content  # preserved
        assert "source: telegram" in content  # preserved
        assert "para: project" in content  # added
        assert "triage_confidence: 0.9" in content  # added


class TestAppendProcessingLog:
    def test_appends_entry(self, tmp_vault):
        append_processing_log(
            tmp_vault,
            source_path="0_inbox/note.md",
            destination_path="2_areas/Health/note.md",
            confidence=0.85,
            agent="pydantic-ai/triage",
            warnings="",
        )
        content = (tmp_vault / "_system" / "processing-log.md").read_text()
        assert "pydantic-ai/triage" in content
        assert "0_inbox/note.md" in content
        assert "2_areas/Health/note.md" in content
        assert "0.85" in content
