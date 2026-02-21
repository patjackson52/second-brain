from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


def move_file(vault_dir: Path, source_rel: str, dest_rel: str) -> None:
    """Move a file within the vault. Creates destination directory if needed."""
    source = vault_dir / source_rel
    dest = vault_dir / dest_rel
    if not source.exists():
        raise FileNotFoundError(f"Source not found: {source_rel}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(dest))


def update_frontmatter(file_path: Path, fields: dict) -> None:
    """Merge fields into a file's YAML frontmatter. Creates frontmatter if absent."""
    content = file_path.read_text()

    # Parse existing frontmatter
    fm_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if fm_match:
        existing_fm = fm_match.group(1)
        body = content[fm_match.end():]
    else:
        existing_fm = ""
        body = content

    # Parse existing fields into dict (simple key: value lines)
    existing = {}
    for line in existing_fm.split("\n"):
        if ": " in line:
            key, _, value = line.partition(": ")
            existing[key.strip()] = value.strip()

    # Merge new fields (new fields override)
    existing.update({k: str(v) for k, v in fields.items()})

    # Rebuild frontmatter
    fm_lines = [f"{k}: {v}" for k, v in existing.items()]
    new_content = "---\n" + "\n".join(fm_lines) + "\n---\n" + body
    file_path.write_text(new_content)


def append_processing_log(
    vault_dir: Path,
    source_path: str,
    destination_path: str,
    confidence: float,
    agent: str = "pydantic-ai/triage",
    warnings: str = "",
) -> None:
    """Append an entry to _system/processing-log.md."""
    log_path = vault_dir / "_system" / "processing-log.md"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    warning_str = f" | {warnings}" if warnings else ""
    entry = (
        f"- **{timestamp}** | {agent} | `{source_path}` → "
        f"`{destination_path}` | {confidence}{warning_str}\n"
    )
    with open(log_path, "a") as f:
        f.write(entry)
