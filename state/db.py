from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from config.agent_config import STATE_DB_PATH


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Get a SQLite connection with WAL mode and foreign keys enabled."""
    path = db_path or STATE_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist. Idempotent."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agent_runs (
            run_id          TEXT PRIMARY KEY,
            agent_type      TEXT NOT NULL,
            goal_id         TEXT,
            status          TEXT NOT NULL,
            input_summary   TEXT,
            output_summary  TEXT,
            tokens_in       INTEGER,
            tokens_out      INTEGER,
            cost_usd        REAL,
            duration_ms     INTEGER,
            started_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at    DATETIME
        );
        CREATE INDEX IF NOT EXISTS idx_runs_agent_date
            ON agent_runs(agent_type, started_at);
    """)
