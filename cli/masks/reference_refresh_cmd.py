"""``masks reference-refresh`` — run mask-reference-refresh skill for a Role."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import typer

from masks.env_util import merge_env_for_role
from masks.paths import resolve_base_path
from masks.roles import is_role_candidate


def reference_refresh_command(
    role: Optional[str] = typer.Option(None, "--role", help="Role directory name under base"),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Set PIRANDELLO_NONINTERACTIVE=1 for unattended runs",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Plan refresh actions only (no file writes)",
    ),
) -> None:
    """Refresh Reference/ docs for one Role via the mask-reference-refresh skill."""
    base = resolve_base_path()
    target_role = role
    if not target_role:
        cwd = Path.cwd().resolve()
        try:
            rel = cwd.relative_to(base)
            if rel.parts:
                candidate = rel.parts[0]
                candidate_dir = base / candidate
                if is_role_candidate(candidate_dir):
                    target_role = candidate
        except ValueError:
            target_role = None
    if not target_role:
        typer.secho(
            "Could not infer role from current workspace; pass --role <name>.",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(2)

    role_dir: Path = (base / target_role).resolve()
    index_md = role_dir / "Reference" / "INDEX.md"
    if not role_dir.is_dir():
        typer.secho(f"Role directory not found: {target_role}", err=True, fg=typer.colors.RED)
        raise typer.Exit(2)
    if not index_md.is_file():
        typer.secho(f"Missing Reference index: {index_md}", err=True, fg=typer.colors.RED)
        raise typer.Exit(2)
    if shutil.which("claude") is None:
        typer.secho("reference-refresh: `claude` CLI not found on PATH", err=True, fg=typer.colors.RED)
        raise typer.Exit(1)

    env = merge_env_for_role(base, role_dir)
    env["MASKS_BASE"] = str(base)
    env["BASE"] = str(base)
    env["MASKS_ROLE"] = target_role
    env["MASKS_ROLE_DIR"] = str(role_dir)
    env["MASKS_REFERENCE_INDEX"] = str(index_md)
    if non_interactive:
        env["PIRANDELLO_NONINTERACTIVE"] = "1"
    else:
        env.pop("PIRANDELLO_NONINTERACTIVE", None)
    if dry_run:
        env["PIRANDELLO_REFERENCE_REFRESH_DRY_RUN"] = "1"
    else:
        env.pop("PIRANDELLO_REFERENCE_REFRESH_DRY_RUN", None)

    if dry_run:
        prompt = (
            "Run the mask-reference-refresh skill for this Role directory in DRY-RUN mode. "
            "Read Reference/INDEX.md and report exactly what would be refreshed or skipped, "
            "but do not write or modify any files. Do not run git add/commit/push."
        )
    else:
        prompt = (
            "Run the mask-reference-refresh skill for this Role directory. "
            "Read Reference/INDEX.md, refresh all due Drive-backed reference documents, "
            "update Reference/INDEX.md dates only after successful writes, and do not run "
            "git add/commit/push."
        )
    proc = subprocess.run(
        ["claude", "-p", prompt],
        cwd=role_dir,
        env=env,
        text=True,
    )
    if proc.returncode != 0:
        raise typer.Exit(proc.returncode)
    raise typer.Exit(0)
