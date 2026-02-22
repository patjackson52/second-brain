from __future__ import annotations

import os
import time

import pytest

from tools.vault_scan import find_recent_files, read_daily_summaries


class TestFindRecentFiles:
    def test_finds_recently_modified_files(self, tmp_vault):
        note = tmp_vault / "1_projects" / "active" / "test.md"
        note.write_text("# Test")
        files = find_recent_files(tmp_vault, since_hours=1)
        assert note in files

    def test_excludes_venv(self, tmp_vault):
        venv_dir = tmp_vault / ".venv" / "lib"
        venv_dir.mkdir(parents=True)
        (venv_dir / "pkg.py").write_text("x = 1")
        files = find_recent_files(tmp_vault, since_hours=1)
        names = [f.name for f in files]
        assert "pkg.py" not in names

    def test_excludes_assets(self, tmp_vault):
        assets_dir = tmp_vault / "_assets" / "images"
        assets_dir.mkdir(parents=True)
        (assets_dir / "photo.jpg").write_bytes(b"\xff\xd8")
        files = find_recent_files(tmp_vault, since_hours=1)
        names = [f.name for f in files]
        assert "photo.jpg" not in names

    def test_excludes_summary_output(self, tmp_vault):
        summ_dir = tmp_vault / "_system" / "summaries" / "daily" / "auto"
        summ_dir.mkdir(parents=True)
        (summ_dir / "daily-summary-2026-02-21.md").write_text("# Summary")
        files = find_recent_files(tmp_vault, since_hours=1)
        names = [f.name for f in files]
        assert "daily-summary-2026-02-21.md" not in names

    def test_excludes_old_files(self, tmp_vault):
        note = tmp_vault / "0_inbox" / "old.md"
        note.write_text("# Old")
        # Set mtime to 48 hours ago
        old_time = time.time() - (48 * 3600)
        os.utime(note, (old_time, old_time))
        files = find_recent_files(tmp_vault, since_hours=24)
        assert note not in files

    def test_returns_sorted(self, tmp_vault):
        (tmp_vault / "0_inbox" / "b.md").write_text("# B")
        (tmp_vault / "0_inbox" / "a.md").write_text("# A")
        files = find_recent_files(tmp_vault, since_hours=1)
        md_names = [f.name for f in files if f.suffix == ".md"]
        assert md_names == sorted(md_names)


class TestReadDailySummaries:
    def test_reads_existing_summaries(self, tmp_vault):
        summ_dir = tmp_vault / "_system" / "summaries" / "daily" / "auto"
        summ_dir.mkdir(parents=True)
        (summ_dir / "daily-summary-2026-02-20.md").write_text("# Feb 20")
        (summ_dir / "daily-summary-2026-02-21.md").write_text("# Feb 21")
        results = read_daily_summaries(tmp_vault, days=7)
        assert len(results) == 2
        # Sorted chronologically
        assert results[0][0] <= results[1][0]

    def test_returns_empty_if_no_summaries(self, tmp_vault):
        results = read_daily_summaries(tmp_vault, days=7)
        assert results == []

    def test_limits_to_days_window(self, tmp_vault):
        summ_dir = tmp_vault / "_system" / "summaries" / "daily" / "auto"
        summ_dir.mkdir(parents=True)
        # Create summary with old date in filename
        (summ_dir / "daily-summary-2025-01-01.md").write_text("# Old")
        (summ_dir / "daily-summary-2026-02-21.md").write_text("# Today")
        results = read_daily_summaries(tmp_vault, days=7)
        # Should only include recent one (within 7 days of most recent)
        dates = [r[0] for r in results]
        assert "2025-01-01" not in dates
