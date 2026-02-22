"""CLI entry point for PydanticAI summary agent.

Usage:
    python3 agents/run_summary.py daily
    python3 agents/run_summary.py weekly

Exit codes:
    0 = success
    1 = error
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Union

from config.agent_config import INPUT_PRICE, OUTPUT_PRICE, VAULT_DIR
from models.summary import DailySummary, WeeklySummary
from tools.vault_scan import find_recent_files, read_daily_summaries


def determine_output_path(vault_dir: Path, mode: str, date_str: str) -> Path:
    """Determine the output file path for a summary."""
    if mode == "daily":
        return vault_dir / "_system" / "summaries" / "daily" / "auto" / f"daily-summary-{date_str}.md"
    else:
        return vault_dir / "_system" / "summaries" / "weekly" / "auto" / f"weekly-summary-{date_str}.md"


def write_summary_file(
    summary: Union[DailySummary, WeeklySummary],
    output_path: Path,
    date_str: str,
) -> None:
    """Render summary to markdown and write atomically."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    md = summary.render_markdown(date_str)
    tmp_path = output_path.with_suffix(".tmp")
    tmp_path.write_text(md)
    tmp_path.rename(output_path)


async def _run(mode: str, vault_dir: Path) -> int:
    """Run the summary agent and write output."""
    from agents.summary_runner import run_summary
    from state.db import get_connection, init_schema
    from state.runs import log_run_complete, log_run_error, log_run_start

    # Determine date/week string
    now = datetime.now()
    if mode == "daily":
        date_str = now.strftime("%Y-%m-%d")
    else:
        date_str = now.strftime("%Y-W%V")

    # Idempotency check
    output_path = determine_output_path(vault_dir, mode, date_str)
    if output_path.exists():
        print(f"summary: {mode} summary already exists for {date_str}, skipping")
        return 0

    # Gather context
    if mode == "daily":
        files = find_recent_files(vault_dir, since_hours=24)
        daily_summaries = []
    else:
        files = find_recent_files(vault_dir, since_hours=168)
        daily_summaries = read_daily_summaries(vault_dir, days=7)

    run_id = str(uuid.uuid4())
    input_summary = f"{mode} summary for {date_str}, {len(files)} changed files"

    conn = get_connection()
    init_schema(conn)
    log_run_start(conn, run_id, f"summary-{mode}", input_summary)

    start_time = time.monotonic()
    try:
        result = await run_summary(mode, files, daily_summaries, vault_dir=vault_dir, date_str=date_str)
        duration_ms = int((time.monotonic() - start_time) * 1000)

        summary = result.output
        write_summary_file(summary, output_path, date_str)

        usage = result.usage()
        tokens_in = usage.input_tokens or 0
        tokens_out = usage.output_tokens or 0
        cost_usd = (tokens_in * INPUT_PRICE) + (tokens_out * OUTPUT_PRICE)

        log_run_complete(
            conn,
            run_id=run_id,
            output_summary=summary.model_dump_json(),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
        )
        conn.close()

        print(f"summary: {mode} summary written to {output_path}")
        return 0

    except Exception as e:
        duration_ms = int((time.monotonic() - start_time) * 1000)
        log_run_error(conn, run_id, str(e))
        conn.close()
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(description="Generate vault summary")
    parser.add_argument("mode", choices=["daily", "weekly"], help="Summary type")
    args = parser.parse_args()

    exit_code = asyncio.run(_run(args.mode, VAULT_DIR))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
