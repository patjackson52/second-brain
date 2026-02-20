from __future__ import annotations

from pathlib import Path

MAX_FILE_SIZE = 3072  # 3KB cap per file
MAX_DIR_ENTRIES = 100


def read_file(vault_dir: Path, relative_path: str) -> str:
    """Read a file from the vault, capped at 3KB."""
    path = vault_dir / relative_path
    if not path.exists():
        return f"Error: file not found: {relative_path}"
    try:
        content = path.read_text(errors="replace")
        if len(content) > MAX_FILE_SIZE:
            return content[:MAX_FILE_SIZE] + "\n\n[... truncated at 3KB ...]"
        return content
    except Exception as e:
        return f"Error reading {relative_path}: {e}"


def list_directory(vault_dir: Path, relative_path: str) -> str:
    """List directory contents, capped at 100 entries."""
    path = vault_dir / relative_path if relative_path else vault_dir
    if not path.is_dir():
        return f"Error: not a directory: {relative_path}"
    entries = sorted(path.iterdir())
    lines = []
    for entry in entries[:MAX_DIR_ENTRIES]:
        suffix = "/" if entry.is_dir() else ""
        lines.append(f"{entry.name}{suffix}")
    if len(entries) > MAX_DIR_ENTRIES:
        lines.append(f"[... {len(entries) - MAX_DIR_ENTRIES} more entries truncated ...]")
    return "\n".join(lines)


def read_routes(vault_dir: Path) -> str:
    """Read the _system/routes.yaml file."""
    return read_file(vault_dir, "_system/routes.yaml")
