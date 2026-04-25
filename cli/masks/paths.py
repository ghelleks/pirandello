"""Resolve base directory and Pirandello framework root."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def load_base_env_mask(base: Path) -> Optional[str]:
    """Read MASKS_BASE= from base/.env if present. Returns value or None."""
    env_path = base / ".env"
    if not env_path.is_file():
        return None
    try:
        text = env_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        if line.startswith("MASKS_BASE="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def resolve_base_path() -> Path:
    """Resolve the user's base directory (Roles parent).

    Order: ``MASKS_BASE`` env → ``$Desktop/.env`` line ``MASKS_BASE=`` → Desktop
    directory → home directory.
    """
    if os.environ.get("MASKS_BASE"):
        return Path(os.environ["MASKS_BASE"]).expanduser().resolve()
    desktop = Path.home() / "Desktop"
    if desktop.is_dir():
        masked = load_base_env_mask(desktop)
        if masked:
            return Path(masked).expanduser().resolve()
        return desktop
    return Path.home()


def resolve_framework_root() -> Path:
    """Directory containing AGENTS.md, hooks/, templates/, guards/."""
    if os.environ.get("PIRANDELLO_ROOT"):
        return Path(os.environ["PIRANDELLO_ROOT"]).expanduser().resolve()
    here = Path(__file__).resolve().parent
    for parent in [here, *here.parents]:
        if (parent / "AGENTS.md").is_file() and (parent / "templates" / "OODA.md").is_file():
            return parent
    return Path.home() / "Code" / "pirandello"


def default_memory_db_path() -> Path:
    """~/.pirandello/memory.db — the default MCP memory index location."""
    return Path.home() / ".pirandello" / "memory.db"


def resolve_memory_db_path() -> Path:
    """Prefer MCP_MEMORY_DB_PATH env; fall back to ~/.pirandello/memory.db."""
    raw = os.environ.get("MCP_MEMORY_DB_PATH", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return default_memory_db_path()


def merge_env_file(path: Path, key: str, value: str) -> None:
    """Upsert KEY=value in a dotenv-style file, preserving other lines."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if path.is_file():
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out: list[str] = []
    found = False
    prefix = f"{key}="
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            out.append(line)
            continue
        if stripped.startswith(prefix):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        if out and out[-1].strip():
            out.append("")
        out.append(f"{key}={value}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
