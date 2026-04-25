"""Role directory discovery and layout checks."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator


def is_role_layout(p: Path) -> bool:
    """True if directory looks like an initialized Pirandello Role."""
    return (
        (p / "Memory" / "INDEX.md").is_file()
        and (p / "Reference" / "INDEX.md").is_file()
        and (p / "Archive" / "INDEX.md").is_file()
    )


def is_role_candidate(p: Path) -> bool:
    """True if this directory plausibly is a Pirandello Role (not arbitrary Desktop clutter)."""
    if not p.is_dir() or p.name.startswith("."):
        return False
    if (p / "ROLE.md").is_file():
        return True
    if (p / "OODA.md").is_file():
        return True
    return is_role_layout(p)


def iter_role_dirs(base: Path) -> Iterator[Path]:
    """Immediate subdirectories of base that look like Role workspaces."""
    if not base.is_dir():
        return
    for child in sorted(base.iterdir()):
        if is_role_candidate(child):
            yield child


def role_display_name(role_path: Path) -> str:
    return role_path.name
