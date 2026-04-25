"""``masks sync`` — pull and push each Role (non-fatal errors)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

import typer

from masks.paths import resolve_base_path
from masks.roles import iter_role_dirs


def sync_cmd(role: Optional[str] = None) -> None:
    """Pull --ff-only then push for each Role (or one)."""
    base = resolve_base_path()
    targets: list[Path]
    if role:
        rp = base / role
        if not rp.is_dir():
            typer.secho(f"Unknown role: {role}", err=True, fg=typer.colors.RED)
            raise typer.Exit(2)
        targets = [rp]
    else:
        targets = list(iter_role_dirs(base))

    for role_path in targets:
        name = role_path.name
        git_dir = role_path / ".git"
        if not git_dir.exists():
            typer.echo(f"WARN: {name} is not a git repository; skipping")
            continue
        r = subprocess.run(
            ["git", "-C", str(role_path), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            typer.echo(f"WARN: skipping {name}: no git remote configured", err=True)
            continue
        pr = subprocess.run(
            ["git", "-C", str(role_path), "pull", "--ff-only"],
            capture_output=True,
            text=True,
        )
        if pr.returncode != 0:
            typer.echo(f"WARN: {name} pull failed", err=True)
        ps = subprocess.run(
            ["git", "-C", str(role_path), "push"],
            capture_output=True,
            text=True,
        )
        if ps.returncode != 0:
            typer.echo(f"WARN: {name} push failed", err=True)
