"""Agent run logging functions."""

import sqlite3
from datetime import datetime


def log_run_start(
    conn: sqlite3.Connection,
    run_id: str,
    agent_type: str,
    input_summary: str,
) -> str:
    """Log the start of an agent run.

    Args:
        conn: Active database connection.
        run_id: Unique identifier for this run.
        agent_type: Type of agent (e.g., 'triage', 'summary').
        input_summary: Brief description of input (e.g., file names).

    Returns:
        The run_id for reference.
    """
    conn.execute(
        """
        INSERT INTO agent_runs (run_id, agent_type, status, input_summary, started_at)
        VALUES (?, ?, 'running', ?, ?)
        """,
        (run_id, agent_type, input_summary, datetime.utcnow().isoformat()),
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
    """Log the successful completion of an agent run.

    Args:
        conn: Active database connection.
        run_id: The run identifier from log_run_start.
        output_summary: Brief description of output (e.g., JSON decisions).
        tokens_in: Input tokens consumed.
        tokens_out: Output tokens generated.
        cost_usd: Estimated cost in USD.
        duration_ms: Total duration in milliseconds.
    """
    conn.execute(
        """
        UPDATE agent_runs
        SET status = 'completed',
            output_summary = ?,
            tokens_in = ?,
            tokens_out = ?,
            cost_usd = ?,
            duration_ms = ?,
            completed_at = ?
        WHERE run_id = ?
        """,
        (
            output_summary,
            tokens_in,
            tokens_out,
            cost_usd,
            duration_ms,
            datetime.utcnow().isoformat(),
            run_id,
        ),
    )
    conn.commit()


def log_run_error(
    conn: sqlite3.Connection,
    run_id: str,
    error_message: str,
) -> None:
    """Log an error during an agent run.

    Args:
        conn: Active database connection.
        run_id: The run identifier from log_run_start.
        error_message: Description of the error.
    """
    conn.execute(
        """
        UPDATE agent_runs
        SET status = 'error',
            output_summary = ?,
            completed_at = ?
        WHERE run_id = ?
        """,
        (f"Error: {error_message}", datetime.utcnow().isoformat(), run_id),
    )
    conn.commit()
