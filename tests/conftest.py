import os
import sqlite3
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_vault(tmp_path):
    """Create a temporary vault with PARA directory structure."""
    dirs = [
        "0_inbox",
        "1_projects/active",
        "1_projects/waiting",
        "2_areas/Health",
        "2_areas/Family",
        "3_resources/Technology",
        "3_resources/Vendors",
        "4_archive",
        "5_people/family",
        "_system",
    ]
    for d in dirs:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)

    # Create routes.yaml
    (tmp_path / "_system" / "routes.yaml").write_text(
        "version: 1\n"
        "folders:\n"
        '  inbox: "0_inbox"\n'
        '  projects: "1_projects"\n'
        '  areas: "2_areas"\n'
        '  resources: "3_resources"\n'
        '  archive: "4_archive"\n'
        '  people: "5_people"\n'
        "uncertainty:\n"
        "  keep_in_inbox_below_confidence: 0.7\n"
        "areas:\n"
        "  allowed:\n"
        '    - "Health"\n'
        '    - "Family"\n'
        "resources:\n"
        "  allowed:\n"
        '    - "Technology"\n'
        '    - "Vendors"\n'
    )

    # Create processing-log.md
    (tmp_path / "_system" / "processing-log.md").write_text(
        "# Processing Log\n\n"
    )

    yield tmp_path


@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary SQLite database path."""
    db_path = tmp_path / "test_agents.db"
    yield db_path


@pytest.fixture
def sample_inbox_file(tmp_vault):
    """Create a sample inbox markdown file."""
    content = (
        "---\n"
        "captured_at: 2026-02-19T10:00:00-0800\n"
        "source: telegram\n"
        "---\n"
        "# Plan Hawaii Trip\n\n"
        "Book flights for April. Need to reserve hotel by March 1.\n"
        "Budget: $3000. Deadline: April 15.\n"
    )
    path = tmp_vault / "0_inbox" / "2026-02-19T100000-0800__telegram.md"
    path.write_text(content)
    yield path
