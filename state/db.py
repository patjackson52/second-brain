"""SQLite database connection and schema management."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from config.agent_config import STATE_DB_PATH


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Create a database connection with recommended settings.

    Args:
        db_path: Path to the database file. Defaults to STATE_DB_PATH from config.

    Returns:
        SQLite connection with WAL mode and foreign keys enabled.
    """
    if db_path is None:
        db_path = STATE_DB_PATH

    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Initialize the database schema.

    Creates the agent_runs table if it doesn't exist.
    Idempotent - safe to call multiple times.

    Args:
        conn: Active database connection.
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_runs (
            run_id TEXT PRIMARY KEY,
            agent_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'running',
            input_summary TEXT,
            output_summary TEXT,
            tokens_in INTEGER,
            tokens_out INTEGER,
            cost_usd REAL,
            duration_ms INTEGER,
            started_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT
        )
    """)
    conn.commit()
