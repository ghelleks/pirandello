"""Typer entrypoint for ``masks``."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from masks import __version__
from masks.doctor_cmd import doctor_cmd
from masks.index_cmd import index_main
from masks.reflect_cmd import reflect_command
from masks.role_cmd import add_role
from masks.run_cmd import run_command
from masks.setup_cmd import setup_command
from masks.status_cmd import status_cmd
from masks.sync_cmd import sync_cmd

def _version_cb(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


app = typer.Typer(help="Pirandello masks — setup, sync, doctor, and more.", no_args_is_help=True)


@app.callback()
def _main(
    _version: bool = typer.Option(
        False,
        "--version",
        callback=_version_cb,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """Pirandello CLI."""


@app.command("setup")
def setup(
    base: Optional[Path] = typer.Option(
        None,
        "--base",
        help="Absolute base path for Roles (writes MASKS_BASE into base/.env)",
    ),
) -> None:
    """Scaffold base directory, default roles, hooks, and AGENTS.md."""
    setup_command(base)


@app.command("add-role")
def add_role_cmd(
    name: str = typer.Argument(..., help="Role directory name (kebab-case)"),
    remote: Optional[str] = typer.Option(None, "--remote", help="Git remote URL for origin"),
    interactive: bool = typer.Option(False, "--interactive", "-i"),
) -> None:
    """Create a new Role with hooks and templates."""
    add_role(name, remote=remote, interactive=interactive)


@app.command("sync")
def sync(
    role: Optional[str] = typer.Option(None, "--role", help="Sync only this role directory name"),
) -> None:
    """Pull and push all Role repositories (warnings only on failure)."""
    sync_cmd(role)


@app.command("status")
def status() -> None:
    """Show last commit and OODA log markers per Role."""
    status_cmd()


@app.command("doctor")
def doctor(
    json_out: bool = typer.Option(False, "--json", help="Emit JSON report"),
) -> None:
    """Run health checks (exit 1 if any blocking check fails)."""
    doctor_cmd(json_out=json_out)


@app.command("index")
def index(
    role: str = typer.Argument(..., help="Role directory name"),
    rebuild: bool = typer.Option(False, "--rebuild", help="Rebuild all Memory/ rows for this role"),
) -> None:
    """Incremental mcp-memory index from Memory/ markdown."""
    code = index_main(role, rebuild=rebuild)
    if code:
        raise typer.Exit(code)


@app.command("run")
def run(
    role: str = typer.Argument(..., help="Role directory name"),
) -> None:
    """Run OODA guards and optionally invoke the heartbeat LLM."""
    run_command(role)


@app.command("reflect")
def reflect(
    role: str = typer.Argument("personal", help="Memory scan scope (reserved)"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    json_file: Optional[Path] = typer.Option(None, "--json-file", help="Skill JSON output"),
) -> None:
    """Open a reflect PR from strict JSON (see skills/mask-reflect/SKILL.md)."""
    reflect_command(role, dry_run=dry_run, json_file=json_file)
