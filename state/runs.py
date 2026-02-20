from __future__ import annotations

import sqlite3


def log_run_start(
    conn: sqlite3.Connection,
    run_id: str,
    agent_type: str,
    input_summary: str,
) -> str:
    """Insert a new agent run with status='running'."""
    conn.execute(
        "INSERT INTO agent_runs (run_id, agent_type, status, input_summary) VALUES (?, ?, 'running', ?)",
        (run_id, agent_type, input_summary),
    )
    conn.commit()
    return run_id


def log_run_complete(
    conn: sqlite3.Connection,
    run_id: str,
    output_summary: str,
    tokens_in: int,
    tokens_out: int,
    cost_usd: float,
    duration_ms: int,
) -> None:
    """Mark a run as completed with usage data."""
    conn.execute(
        "UPDATE agent_runs SET status='completed', output_summary=?, tokens_in=?, "
        "tokens_out=?, cost_usd=?, duration_ms=?, completed_at=CURRENT_TIMESTAMP "
        "WHERE run_id=?",
        (output_summary, tokens_in, tokens_out, cost_usd, duration_ms, run_id),
    )
    conn.commit()


def log_run_error(
    conn: sqlite3.Connection,
    run_id: str,
    error_message: str,
) -> None:
    """Mark a run as failed with error details."""
    conn.execute(
        "UPDATE agent_runs SET status='error', output_summary=?, completed_at=CURRENT_TIMESTAMP WHERE run_id=?",
        (f"ERROR: {error_message}", run_id),
    )
    conn.commit()
