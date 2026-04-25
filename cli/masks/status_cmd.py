"""``masks status`` — per-role git summary."""

from __future__ import annotations

import subprocess
from pathlib import Path

import typer

from masks.paths import resolve_base_path
from masks.roles import iter_role_dirs


def _last_commit(role_path: Path) -> str:
    r = subprocess.run(
        ["git", "-C", str(role_path), "log", "-1", "--format=%ci"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0 or not r.stdout.strip():
        return "never"
    return r.stdout.strip()


def _last_remote_head(role_path: Path) -> str:
    r = subprocess.run(
        ["git", "-C", str(role_path), "symbolic-ref", "refs/remotes/origin/HEAD"],
        capture_output=True,
        text=True,
    )
    ref = None
    if r.returncode == 0 and r.stdout.strip():
        ref = r.stdout.strip().replace("refs/remotes/", "")
    else:
        for guess in ("origin/main", "origin/master"):
            chk = subprocess.run(
                ["git", "-C", str(role_path), "rev-parse", "--verify", guess],
                capture_output=True,
            )
            if chk.returncode == 0:
                ref = guess
                break
    if not ref:
        return "n/a"
    lr = subprocess.run(
        ["git", "-C", str(role_path), "log", "-1", "--format=%ci", ref],
        capture_output=True,
        text=True,
    )
    if lr.returncode != 0:
        return "n/a"
    return lr.stdout.strip()


def status_cmd() -> None:
    base = resolve_base_path()
    typer.echo(f"{'ROLE':<12} {'LAST_COMMIT':<22} {'LAST_REMOTE_HEAD':<22}")
    for role_path in iter_role_dirs(base):
        name = role_path.name
        if not (role_path / ".git").exists():
            typer.echo(f"{name:<12} {'n/a':<22} {'n/a':<22}")
            continue
        typer.echo(
            f"{name:<12} {_last_commit(role_path):<22} {_last_remote_head(role_path):<22}"
        )
