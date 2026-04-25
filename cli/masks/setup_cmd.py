"""``masks setup`` — scaffold base, default roles, hooks, and AGENTS symlink."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

import typer

from masks.hooks import copy_with_backup, deploy_shared_hooks, install_hooks_for_role
from masks.paths import default_memory_db_path, merge_env_file, resolve_base_path, resolve_framework_root

DEFAULT_ROLES = ("personal", "work")


def _touch_index(path: Path) -> str:
    if path.is_file():
        return "EXISTS"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    return "CREATED"


def _ensure_role_scaffold(base: Path, role: str, fw: Path) -> None:
    role_path = base / role
    role_path.mkdir(parents=True, exist_ok=True)
    role_md = role_path / "ROLE.md"
    if not role_md.exists():
        role_md.write_text(
            f"# Role: {role}\n\n"
            "**Google account:** \n"
            "**Git remote:** \n\n"
            "## Communication in this role\n\n"
            "## Active tools\n\n"
            "## Preferences in this role\n\n",
            encoding="utf-8",
        )
        typer.echo("  ROLE.md: CREATED")
    else:
        typer.echo("  ROLE.md: EXISTS")
    if role == "personal":
        self_md = role_path / "SELF.md"
        if not self_md.exists():
            self_md.write_text(
                "# Self\n\n"
                "## Identity\n\n"
                "## Values\n\n"
                "## How I communicate\n\n"
                "## How I think\n\n",
                encoding="utf-8",
            )
            typer.echo("  SELF.md: CREATED")
        else:
            typer.echo("  SELF.md: EXISTS")
    for sub in ("Memory", "Reference", "Archive"):
        idx = role_path / sub / "INDEX.md"
        typer.echo(f"  {sub}/INDEX.md: {_touch_index(idx)}")

    tpl_gi = fw / "templates" / ".gitignore"
    if tpl_gi.is_file():
        gi = role_path / ".gitignore"
        if not gi.exists():
            typer.echo(f"  .gitignore: {copy_with_backup(tpl_gi, gi)}")
        else:
            typer.echo("  .gitignore: EXISTS")

    agents_src = fw / "AGENTS.md"
    if agents_src.is_file():
        typer.echo(f"  AGENTS.md: {copy_with_backup(agents_src, role_path / 'AGENTS.md')}")

    tpl_ooda = fw / "templates" / "OODA.md"
    ooda = role_path / "OODA.md"
    if tpl_ooda.is_file() and not ooda.exists():
        text = tpl_ooda.read_text(encoding="utf-8")
        text = text.replace("[role-name]", role).replace("[role]", role)
        ooda.write_text(text, encoding="utf-8")
        typer.echo("  OODA.md: CREATED")
    else:
        typer.echo("  OODA.md: EXISTS")

    env_ex = fw / ".env.example"
    role_env = role_path / ".env"
    if env_ex.is_file() and not role_env.exists():
        typer.echo(f"  .env: {copy_with_backup(env_ex, role_env)}")
    elif role_env.is_file():
        typer.echo("  .env: EXISTS")

    git_dir = role_path / ".git"
    if not git_dir.exists():
        subprocess.run(
            ["git", "init", "-q"],
            cwd=role_path,
            check=True,
        )
        typer.echo("  git: CREATED")
    else:
        typer.echo("  git: EXISTS")
    install_hooks_for_role(role_path, fw)
    typer.echo("  hooks: INSTALLED")


def setup_command(base: Optional[Path] = None) -> None:
    """Create base layout, default roles, copied assets, and hook wiring."""
    fw = resolve_framework_root()
    if base is not None:
        base_path = Path(base).expanduser().resolve()
        base_path.mkdir(parents=True, exist_ok=True)
        merge_env_file(base_path / ".env", "MASKS_BASE", str(base_path))
    else:
        base_path = resolve_base_path()
    typer.echo(f"Base: {base_path}")
    typer.echo(f"Framework: {fw}")

    typer.echo("Deploying shared hooks:")
    deploy_shared_hooks(fw)

    for role in DEFAULT_ROLES:
        typer.echo(f"Role {role}:")
        _ensure_role_scaffold(base_path, role, fw)

    base_env = base_path / ".env"
    tpl_root_env = fw / ".env.example"
    if tpl_root_env.is_file() and not base_env.exists():
        typer.echo(f"Base .env: {copy_with_backup(tpl_root_env, base_env)}")
        merge_env_file(base_env, "MASKS_BASE", str(base_path))
    elif base_env.is_file():
        typer.echo("Base .env: EXISTS")

    agents_src = fw / "AGENTS.md"
    if agents_src.is_file():
        typer.echo(f"Base AGENTS.md: {copy_with_backup(agents_src, base_path / 'AGENTS.md')}")

    db_default = default_memory_db_path()
    if not db_default.parent.is_dir():
        db_default.parent.mkdir(parents=True, exist_ok=True)
        typer.echo(f"Memory DB dir: CREATED {db_default.parent}")
    else:
        typer.echo(f"Memory DB dir: EXISTS {db_default.parent}")
    base_env = base_path / ".env"
    if base_env.is_file():
        from masks.env_util import apply_env_file
        existing = {}
        apply_env_file(base_env, existing)
        if not existing.get("MCP_MEMORY_DB_PATH", "").strip():
            merge_env_file(base_env, "MCP_MEMORY_DB_PATH", str(db_default))
            typer.echo(f"MCP_MEMORY_DB_PATH: defaulted to {db_default}")
