from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

# Directories to exclude when scanning for recent changes
EXCLUDE_DIRS = {".venv", ".git", "__pycache__", "_assets", "node_modules"}
EXCLUDE_PREFIXES = ("_system/summaries",)

MAX_FILE_CONTENT = 3072  # 3KB per file, consistent with triage


def find_recent_files(vault_dir: Path, since_hours: int = 24) -> List[Path]:
    """Walk vault, return files modified within since_hours.

    Excludes: .venv/, .git/, _assets/, _system/summaries/, __pycache__/
    """
    cutoff = time.time() - (since_hours * 3600)
    results = []

    for path in vault_dir.rglob("*"):
        if not path.is_file():
            continue
        # Check exclusions
        rel = path.relative_to(vault_dir)
        parts = rel.parts
        if any(part in EXCLUDE_DIRS for part in parts):
            continue
        rel_str = str(rel)
        if any(rel_str.startswith(prefix) for prefix in EXCLUDE_PREFIXES):
            continue
        if path.name.startswith("."):
            continue
        # Check modification time
        if path.stat().st_mtime >= cutoff:
            results.append(path)

    return sorted(results)


def read_daily_summaries(
    vault_dir: Path, days: int = 7
) -> List[Tuple[str, str]]:
    """Read recent daily summaries for weekly rollup.

    Returns list of (date_str, content) tuples sorted chronologically.
    Only includes summaries within `days` of the most recent one.
    """
    summ_dir = vault_dir / "_system" / "summaries" / "daily" / "auto"
    if not summ_dir.is_dir():
        return []

    files = sorted(summ_dir.glob("daily-summary-*.md"))
    if not files:
        return []

    # Parse dates from filenames
    entries = []
    for f in files:
        # Extract date from "daily-summary-YYYY-MM-DD.md"
        stem = f.stem  # "daily-summary-2026-02-21"
        date_str = stem.replace("daily-summary-", "")
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            entries.append((date_str, f))
        except ValueError:
            continue

    if not entries:
        return []

    # Filter to within `days` of the most recent entry
    entries.sort(key=lambda x: x[0])
    most_recent = datetime.strptime(entries[-1][0], "%Y-%m-%d")
    cutoff = most_recent - timedelta(days=days)

    results = []
    for date_str, f in entries:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        if d >= cutoff:
            results.append((date_str, f.read_text()))

    return results
