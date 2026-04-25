"""``masks add-role`` — scaffold an additional Role."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import typer

from masks.hooks import install_hooks_for_role
from masks.paths import resolve_base_path, resolve_framework_root
from masks.roles import is_role_layout
from masks.setup_cmd import _ensure_role_env_defaults, _ensure_role_scaffold, resolve_role_env_template

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def add_role(
    name: str,
    remote: Optional[str] = None,
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Launch interactive credential flow"),
    create_role_env: bool = typer.Option(False, "--role-env/--no-role-env", help="Create role-local .env file"),
) -> None:
    """Add a new Role directory under the base path."""
    if name in ("personal", "work"):
        typer.secho("Use `masks setup` for personal and work.", err=True, fg=typer.colors.RED)
        raise typer.Exit(2)
    if not _NAME_RE.match(name):
        typer.secho("Role name must be lowercase letters, digits, and hyphens.", err=True, fg=typer.colors.RED)
        raise typer.Exit(2)
    base = resolve_base_path()
    fw = resolve_framework_root()
    role_path = base / name
    if role_path.exists() and is_role_layout(role_path):
        typer.echo(f"Role {name} already initialized; refreshing hooks.")
        role_env = role_path / ".env"
        if create_role_env and not role_env.is_file():
            src = resolve_role_env_template(fw)
            if src.is_file():
                role_env.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
                typer.echo("  .env: CREATED")
        if role_env.is_file():
            _ensure_role_env_defaults(base, name, role_env)
        install_hooks_for_role(role_path, fw)
        raise typer.Exit(0)
    if role_path.exists():
        typer.secho("Path exists but is not a valid Role layout.", err=True, fg=typer.colors.RED)
        raise typer.Exit(2)
    role_path.mkdir(parents=True, exist_ok=True)
    typer.echo(f"Scaffolding role {name}:")
    scaffold_role_env = create_role_env or interactive
    _ensure_role_scaffold(base, name, fw, create_role_env=scaffold_role_env)
    if remote:
        r = subprocess.run(
            ["git", "-C", str(role_path), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
        )
        if r.returncode == 0 and r.stdout.strip() and r.stdout.strip() != remote:
            typer.secho("origin exists with different URL; refusing to change.", err=True, fg=typer.colors.RED)
            raise typer.Exit(2)
        if r.returncode != 0:
            subprocess.run(
                ["git", "-C", str(role_path), "remote", "add", "origin", remote],
                check=True,
            )
            typer.echo(f"git remote origin: {remote}")
    if interactive:
        if shutil.which("claude"):
            subprocess.run(
                [
                    "claude",
                    "-p",
                    "Run the mask-add-role skill for this Role directory. "
                    "Collect credentials and signal sources; write them to .env when complete. "
                    "If this Role uses scheduled OODA, keep OODA.md aligned with `beckett` docs.",
                ],
                cwd=role_path,
                check=False,
            )
        else:
            typer.echo(
                "Interactive mode: open this role in your assistant and run the mask-add-role skill "
                "to finish credential setup."
            )
