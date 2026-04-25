"""Install session hooks into a Role directory."""

from __future__ import annotations

import datetime
import json
import shutil
import stat
from pathlib import Path

PIRANDELLO_MARKER = "<!-- pirandello-hooks -->"
_HOOKS_INSTALL_DIR = Path.home() / ".pirandello" / "hooks"
_GUARDS_INSTALL_DIR = Path.home() / ".pirandello" / "guards"


def copy_with_backup(src: Path, dst: Path) -> str:
    """Copy *src* to *dst*, backing up *dst* first if it already exists.

    Returns a short status string suitable for CLI output.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = dst.with_name(dst.name + f".bak.{ts}")
        if dst.is_symlink():
            backup.unlink(missing_ok=True)
            backup.symlink_to(dst.resolve())
            dst.unlink()
        else:
            shutil.copy2(dst, backup)
        shutil.copy2(src, dst)
        return f"UPDATED (backup: {backup.name})"
    shutil.copy2(src, dst)
    return "CREATED"


def deploy_shared_hooks(fw: Path) -> None:
    """Copy hook and guard scripts from the bundled package data to
    ``~/.pirandello/hooks/`` and ``~/.pirandello/guards/``.

    These stable user-owned paths are what role-level hook configuration
    files point at, so they remain valid regardless of where the package
    was installed from.
    """
    _HOOKS_INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    _GUARDS_INSTALL_DIR.mkdir(parents=True, exist_ok=True)

    for script in (fw / "hooks").glob("*.sh"):
        dst = _HOOKS_INSTALL_DIR / script.name
        status = copy_with_backup(script, dst)
        dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"  hook {script.name}: {status}")

    for script in (fw / "guards").glob("*.sh"):
        dst = _GUARDS_INSTALL_DIR / script.name
        status = copy_with_backup(script, dst)
        dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"  guard {script.name}: {status}")


def install_hooks_for_role(role_path: Path, fw: Path) -> None:  # noqa: ARG001
    """Install Cursor hooks, Claude lifecycle snippets, and git post-commit.

    Hook scripts are expected to already be deployed to
    ``~/.pirandello/hooks/`` by :func:`deploy_shared_hooks`.
    """
    start_sh = _HOOKS_INSTALL_DIR / "start.sh"
    end_sh = _HOOKS_INSTALL_DIR / "end.sh"
    post_sh = _HOOKS_INSTALL_DIR / "post-commit.sh"

    _install_cursor_hooks(role_path, start_sh, end_sh)
    _install_claude_snippets(role_path, start_sh, end_sh)
    _install_git_post_commit(role_path, post_sh)


def _install_cursor_hooks(role_path: Path, start_sh: Path, end_sh: Path) -> None:
    cursor_dir = role_path / ".cursor"
    cursor_dir.mkdir(parents=True, exist_ok=True)
    hooks_path = cursor_dir / "hooks.json"
    start_cmd = f"bash {start_sh}"
    end_cmd = f"bash {end_sh}"
    data: dict = {"version": 1, "hooks": {}}
    if hooks_path.is_file():
        try:
            data = json.loads(hooks_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {"version": 1, "hooks": {}}
    if "hooks" not in data or not isinstance(data["hooks"], dict):
        data["hooks"] = {}
    data["hooks"]["sessionStart"] = [{"command": start_cmd}]
    data["hooks"]["sessionEnd"] = [{"command": end_cmd}]
    hooks_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _install_claude_snippets(role_path: Path, start_sh: Path, end_sh: Path) -> None:
    claude = role_path / "CLAUDE.md"
    block = (
        f"{PIRANDELLO_MARKER}\n\n"
        "## Pirandello lifecycle\n\n"
        "On session start, the environment runs:\n\n"
        f"```bash\nbash {start_sh}\n```\n\n"
        "On session end:\n\n"
        f"```bash\nbash {end_sh}\n```\n"
    )
    if claude.is_file():
        existing = claude.read_text(encoding="utf-8", errors="replace")
        if PIRANDELLO_MARKER in existing:
            return
        claude.write_text(existing.rstrip() + "\n\n" + block + "\n", encoding="utf-8")
    else:
        claude.write_text(block + "\n", encoding="utf-8")


def _install_git_post_commit(role_path: Path, post_sh: Path) -> None:
    git_dir = role_path / ".git"
    if not git_dir.is_dir():
        return
    hook_path = git_dir / "hooks" / "post-commit"
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    script = f"#!/bin/sh\nexec bash {post_sh}\n"
    hook_path.write_text(script, encoding="utf-8")
    mode = hook_path.stat().st_mode
    hook_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
