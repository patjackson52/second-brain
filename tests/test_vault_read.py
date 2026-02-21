from pathlib import Path

from tools.vault_read import list_directory, read_file, read_routes


class TestReadFile:
    def test_reads_markdown(self, tmp_vault):
        note = tmp_vault / "0_inbox" / "test.md"
        note.write_text("# Hello\n\nSome content here.")
        result = read_file(tmp_vault, "0_inbox/test.md")
        assert "# Hello" in result
        assert "Some content here." in result

    def test_caps_at_3kb(self, tmp_vault):
        note = tmp_vault / "0_inbox" / "big.md"
        note.write_text("x" * 5000)
        result = read_file(tmp_vault, "0_inbox/big.md")
        assert len(result) <= 3072 + 50  # 3KB + truncation message

    def test_missing_file(self, tmp_vault):
        result = read_file(tmp_vault, "0_inbox/nonexistent.md")
        assert "not found" in result.lower() or "error" in result.lower()


class TestListDirectory:
    def test_lists_vault_root(self, tmp_vault):
        result = list_directory(tmp_vault, "")
        assert "0_inbox" in result
        assert "1_projects" in result
        assert "2_areas" in result

    def test_lists_subdirectory(self, tmp_vault):
        result = list_directory(tmp_vault, "2_areas")
        assert "Health" in result

    def test_caps_at_100_entries(self, tmp_vault):
        many_dir = tmp_vault / "0_inbox"
        for i in range(120):
            (many_dir / f"note-{i:03d}.md").write_text(f"Note {i}")
        result = list_directory(tmp_vault, "0_inbox")
        # Should mention truncation or cap entries
        lines = [l for l in result.strip().split("\n") if l.strip()]
        assert len(lines) <= 101  # 100 entries + possible header


class TestReadRoutes:
    def test_reads_routes_yaml(self, tmp_vault):
        result = read_routes(tmp_vault)
        assert "0_inbox" in result
        assert "Health" in result
        assert "Technology" in result
