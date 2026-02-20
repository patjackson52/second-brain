import sqlite3
from pathlib import Path

import pytest

from state.db import get_connection, init_schema
from state.runs import log_run_complete, log_run_error, log_run_start


class TestDatabase:
    def test_get_connection_creates_file(self, tmp_db):
        conn = get_connection(tmp_db)
        assert tmp_db.exists()
        conn.close()

    def test_get_connection_wal_mode(self, tmp_db):
        conn = get_connection(tmp_db)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"
        conn.close()

    def test_get_connection_foreign_keys(self, tmp_db):
        conn = get_connection(tmp_db)
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1
        conn.close()

    def test_init_schema_creates_table(self, tmp_db):
        conn = get_connection(tmp_db)
        init_schema(conn)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        assert "agent_runs" in table_names
        conn.close()

    def test_init_schema_idempotent(self, tmp_db):
        conn = get_connection(tmp_db)
        init_schema(conn)
        init_schema(conn)  # should not raise
        conn.close()


class TestRunLogging:
    def test_log_run_start(self, tmp_db):
        conn = get_connection(tmp_db)
        init_schema(conn)
        run_id = log_run_start(conn, "test-run-1", "triage", "note1.md, note2.md")
        assert run_id == "test-run-1"
        row = conn.execute(
            "SELECT run_id, agent_type, status, input_summary FROM agent_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        assert row[0] == "test-run-1"
        assert row[1] == "triage"
        assert row[2] == "running"
        assert row[3] == "note1.md, note2.md"
        conn.close()

    def test_log_run_complete(self, tmp_db):
        conn = get_connection(tmp_db)
        init_schema(conn)
        log_run_start(conn, "test-run-2", "triage", "note.md")
        log_run_complete(
            conn,
            run_id="test-run-2",
            output_summary='{"decisions": []}',
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.001,
            duration_ms=1500,
        )
        row = conn.execute(
            "SELECT status, tokens_in, tokens_out, cost_usd, duration_ms, completed_at "
            "FROM agent_runs WHERE run_id = ?",
            ("test-run-2",),
        ).fetchone()
        assert row[0] == "completed"
        assert row[1] == 100
        assert row[2] == 50
        assert row[3] == pytest.approx(0.001)
        assert row[4] == 1500
        assert row[5] is not None  # completed_at set
        conn.close()

    def test_log_run_error(self, tmp_db):
        conn = get_connection(tmp_db)
        init_schema(conn)
        log_run_start(conn, "test-run-3", "triage", "note.md")
        log_run_error(conn, "test-run-3", "API timeout")
        row = conn.execute(
            "SELECT status, output_summary FROM agent_runs WHERE run_id = ?",
            ("test-run-3",),
        ).fetchone()
        assert row[0] == "error"
        assert "API timeout" in row[1]
        conn.close()
