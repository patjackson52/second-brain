"""CLI entry point for PydanticAI triage agent.

Usage:
    python3 agents/run_triage.py --all
    python3 agents/run_triage.py --files note1.md note2.md

Exit codes:
    0 = success (all items routed)
    1 = error
    2 = some items need review (low confidence)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, List

from config.agent_config import INPUT_PRICE, OUTPUT_PRICE, STATE_DB_PATH, VAULT_DIR
from models.triage import TriageBatch, TriageDecision
from tools.vault_write import append_processing_log, move_file, update_frontmatter

CONFIDENCE_THRESHOLD = 0.7


def find_inbox_files(vault_dir: Path) -> List[Path]:
    """Find all .md files in 0_inbox/ (excluding .gitkeep)."""
    inbox = vault_dir / "0_inbox"
    if not inbox.is_dir():
        return []
    return sorted(
        f
        for f in inbox.glob("*.md")
        if f.name != ".gitkeep"
    )


def execute_decisions(batch: TriageBatch, vault_dir: Path) -> Dict[str, int]:
    """Execute triage decisions: move files or mark for review."""
    stats = {"moved": 0, "kept": 0, "skipped": len(batch.skipped)}

    for decision in batch.decisions:
        source_rel = f"0_inbox/{decision.filename}"
        source_path = vault_dir / source_rel

        if not source_path.exists():
            print(f"  WARNING: {decision.filename} not found in inbox, skipping")
            stats["skipped"] += 1
            continue

        if decision.confidence >= CONFIDENCE_THRESHOLD:
            # Build destination path
            dest_parts = [decision.destination.value]
            if decision.subdirectory:
                dest_parts.append(decision.subdirectory)
            filename = decision.suggested_rename or decision.filename
            dest_parts.append(filename)
            dest_rel = "/".join(dest_parts)

            # Update frontmatter before moving
            update_frontmatter(source_path, {
                "para": decision.destination.value.split("_")[-1].split("/")[0],
                "status": "triaged",
                "triage_confidence": decision.confidence,
                "triage_notes": decision.reasoning,
                "tags": json.dumps(decision.tags) if decision.tags else "[]",
            })

            # Move file
            move_file(vault_dir, source_rel, dest_rel)
            stats["moved"] += 1

            # Log to processing log
            append_processing_log(
                vault_dir,
                source_path=source_rel,
                destination_path=dest_rel,
                confidence=decision.confidence,
            )
            print(f"  MOVED: {decision.filename} -> {dest_rel} ({decision.confidence:.0%})")

        else:
            # Low confidence: keep in inbox, mark needs_triage
            update_frontmatter(source_path, {
                "needs_triage": "true",
                "triage_confidence": decision.confidence,
                "triage_notes": decision.reasoning,
            })
            stats["kept"] += 1

            append_processing_log(
                vault_dir,
                source_path=source_rel,
                destination_path=f"{source_rel} (kept)",
                confidence=decision.confidence,
                warnings="needs_triage: low confidence",
            )
            print(f"  KEPT:  {decision.filename} in inbox ({decision.confidence:.0%} < threshold)")

    return stats


async def _run(files: List[Path], vault_dir: Path) -> int:
    """Run the triage agent and execute decisions."""
    from agents.triage_runner import triage_inbox
    from state.db import get_connection, init_schema
    from state.runs import log_run_complete, log_run_error, log_run_start

    run_id = str(uuid.uuid4())
    input_summary = ", ".join(f.name for f in files)

    # Initialize state
    conn = get_connection()
    init_schema(conn)
    log_run_start(conn, run_id, "triage", input_summary)

    start_time = time.monotonic()
    try:
        batch = await triage_inbox(files, vault_dir=vault_dir)
        duration_ms = int((time.monotonic() - start_time) * 1000)

        stats = execute_decisions(batch, vault_dir)

        # Log completion (token counts from result not available via triage_inbox,
        # will be enhanced when we wire up result.usage() directly)
        log_run_complete(
            conn,
            run_id=run_id,
            output_summary=batch.model_dump_json(),
            tokens_in=0,  # TODO: wire up from result.usage()
            tokens_out=0,
            cost_usd=0.0,
            duration_ms=duration_ms,
        )
        conn.close()

        print(f"\nTriage complete: {stats['moved']} moved, {stats['kept']} kept, {stats['skipped']} skipped")

        return 2 if stats["kept"] > 0 else 0

    except Exception as e:
        duration_ms = int((time.monotonic() - start_time) * 1000)
        log_run_error(conn, run_id, str(e))
        conn.close()
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(description="Run PydanticAI triage on inbox files")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Process all files in 0_inbox/")
    group.add_argument("--files", nargs="+", help="Specific files to process")
    args = parser.parse_args()

    vault_dir = VAULT_DIR

    if args.all:
        files = find_inbox_files(vault_dir)
    else:
        files = [vault_dir / "0_inbox" / f for f in args.files]

    if not files:
        print("inbox-triage: no files to process")
        sys.exit(0)

    print(f"inbox-triage: processing {len(files)} file(s)")
    exit_code = asyncio.run(_run(files, vault_dir))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
