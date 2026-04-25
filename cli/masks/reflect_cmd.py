"""``masks reflect`` — apply reflect skill JSON to git/gh (personal repo only)."""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional

import typer

from masks.env_util import apply_env_file
from masks.paths import resolve_base_path

_BRANCH_RE = re.compile(r"^reflect/\d{4}-\d{2}-\d{2}$")
_PR_URL_RE = re.compile(r"^https://github\.com/.+/pull/\d+$")


def _utc_ts() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Optional[Path], use_stdin: bool) -> dict[str, Any]:
    if path:
        raw = path.read_text(encoding="utf-8")
    elif use_stdin:
        if sys.stdin.isatty():
            raise ValueError("Provide --json-file PATH or pipe JSON on stdin")
        raw = sys.stdin.read()
    else:
        raise ValueError("Provide --json-file PATH or pipe JSON on stdin")
    return json.loads(raw)


def _append_reflect_log(personal: Path, line: str, dry_run: bool) -> None:
    if dry_run:
        return
    logf = personal / ".reflect.log"
    with open(logf, "a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")


def _has_gh() -> bool:
    return shutil.which("gh") is not None


def _personal_has_remote(personal: Path) -> bool:
    cfg = personal / ".git" / "config"
    if not cfg.is_file():
        return False
    text = cfg.read_text(encoding="utf-8", errors="replace")
    return bool(re.search(r"^\s*\[remote\s+\"", text, re.MULTILINE))


def _reflect_branches_exist(personal: Path) -> bool:
    refs = personal / ".git" / "refs" / "heads" / "reflect"
    if refs.is_dir() and any(refs.iterdir()):
        return True
    for remote in (personal / ".git" / "refs" / "remotes").glob("*"):
        rdir = remote / "reflect"
        if rdir.is_dir() and any(rdir.iterdir()):
            return True
    packed = personal / ".git" / "packed-refs"
    if packed.is_file():
        for line in packed.read_text(encoding="utf-8", errors="replace").splitlines():
            if "refs/heads/reflect/" in line or "/reflect/" in line:
                return True
    return False


def reflect_command(
    role: str = typer.Argument("personal", help="Scope role for Memory scan metadata (skill concern)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Parse JSON and print plan; no git/gh/log"),
    json_file: Optional[Path] = typer.Option(
        None,
        "--json-file",
        help="Strict JSON output from the mask-reflect skill (stdin if omitted and piped)",
    ),
) -> None:
    """Orchestrate SELF.md reflect PR from skill JSON (see skills/mask-reflect/SKILL.md)."""
    _ = role  # reserved for future skill scope wiring
    base = resolve_base_path()
    personal = (base / "personal").resolve()
    env = dict(os.environ)
    apply_env_file(base / ".env", env)
    apply_env_file(personal / ".env", env)

    try:
        data = _load_json(json_file, use_stdin=json_file is None)
    except (json.JSONDecodeError, ValueError) as e:
        typer.secho(f"reflect: invalid JSON input: {e}", err=True, fg=typer.colors.RED)
        raise typer.Exit(1)

    patterns = bool(data.get("patterns_found"))
    if not patterns:
        _append_reflect_log(personal, f"REFLECT_OK {_utc_ts()}", dry_run)
        typer.echo("OK: no changes proposed")
        raise typer.Exit(0)

    if not _has_gh():
        typer.secho(
            "reflect: `gh` is required before any git operations. Install from https://cli.github.com/",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    if not _personal_has_remote(personal):
        typer.echo("warning: no remote configured for personal/ — cannot open PR", err=True)
        _append_reflect_log(personal, f"REFLECT_SKIP {_utc_ts()} reason=no_personal_remote", dry_run)
        typer.echo("SKIP: no personal remote")
        raise typer.Exit(0)

    if _reflect_branches_exist(personal):
        typer.echo(
            "reflect: a reflect/* branch already exists — resolve or delete it before running reflect again",
            err=True,
        )
        _append_reflect_log(personal, f"REFLECT_SKIP {_utc_ts()} reason=duplicate_reflect_branch", dry_run)
        typer.echo("SKIP: duplicate reflect branch")
        raise typer.Exit(0)

    branch = data.get("branch_name") or ""
    if not _BRANCH_RE.match(branch):
        typer.secho("reflect: branch_name must match reflect/YYYY-MM-DD", err=True, fg=typer.colors.RED)
        raise typer.Exit(1)

    diff = data.get("proposed_diff") or ""
    title = (data.get("pr_title") or "").strip()
    body = data.get("pr_description") or ""
    if not title:
        typer.secho("reflect: pr_title required", err=True, fg=typer.colors.RED)
        raise typer.Exit(1)

    if dry_run:
        typer.echo(f"branch: {branch}")
        typer.echo(f"title: {title}")
        typer.echo("--- diff ---")
        typer.echo(diff[:8000])
        raise typer.Exit(0)

    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(personal), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    fetch = git("fetch", "origin", "--prune")
    if fetch.returncode != 0:
        typer.secho(fetch.stderr or fetch.stdout or "git fetch failed", err=True)
        raise typer.Exit(1)
    co = git("checkout", "main")
    if co.returncode != 0:
        typer.secho(co.stderr or co.stdout or "git checkout main failed", err=True)
        raise typer.Exit(1)
    pull = git("pull", "--ff-only", "origin", "main")
    if pull.returncode != 0:
        typer.secho(pull.stderr or pull.stdout or "git pull failed", err=True)
        raise typer.Exit(1)
    st2 = git("status", "--porcelain")
    if st2.stdout.strip():
        typer.secho("reflect: personal/ not clean after update", err=True)
        raise typer.Exit(1)

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".patch") as tmp:
        tmp.write(diff)
        patch_path = tmp.name

    try:
        chk = git("apply", "--check", patch_path)
        if chk.returncode != 0:
            typer.secho(chk.stderr or "malformed patch", err=True)
            raise typer.Exit(1)
        cb = git("checkout", "-b", branch)
        if cb.returncode != 0:
            typer.secho(cb.stderr or "branch create failed", err=True)
            raise typer.Exit(1)
        ap = git("apply", patch_path)
        if ap.returncode != 0:
            typer.secho(ap.stderr or "git apply failed; resetting", err=True)
            subprocess.run(["git", "-C", str(personal), "reset", "--hard"], check=False)
            subprocess.run(["git", "-C", str(personal), "checkout", "main"], check=False)
            subprocess.run(["git", "-C", str(personal), "branch", "-D", branch], check=False)
            raise typer.Exit(1)
    finally:
        Path(patch_path).unlink(missing_ok=True)

    day = _dt.datetime.now().strftime("%Y-%m-%d")
    cm = git("add", "SELF.md")
    if cm.returncode != 0:
        typer.secho(cm.stderr, err=True)
        raise typer.Exit(1)
    cmt = git("commit", "-m", f"reflect: proposed SELF.md update {day}")
    if cmt.returncode != 0:
        typer.secho(cmt.stderr or cmt.stdout or "commit failed", err=True)
        raise typer.Exit(1)
    ps = git("push", "-u", "origin", branch)
    if ps.returncode != 0:
        typer.secho(ps.stderr or ps.stdout or "push failed", err=True)
        raise typer.Exit(1)

    rv = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        cwd=str(personal),
        capture_output=True,
        text=True,
    )
    repo_slug = rv.stdout.strip() if rv.returncode == 0 else ""
    if not repo_slug:
        typer.secho("reflect: could not resolve GitHub repo slug via gh", err=True)
        raise typer.Exit(1)

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".md") as bf:
        bf.write(body)
        body_path = bf.name
    try:
        gh = subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--repo",
                repo_slug,
                "--base",
                "main",
                "--head",
                branch,
                "--title",
                title,
                "--body-file",
                body_path,
            ],
            cwd=str(personal),
            capture_output=True,
            text=True,
        )
        if gh.returncode != 0:
            typer.secho(gh.stderr or gh.stdout or "gh pr create failed", err=True)
            raise typer.Exit(1)
        url = ""
        for line in (gh.stdout or "").splitlines():
            line = line.strip()
            if _PR_URL_RE.match(line):
                url = line
                break
        if not url:
            typer.secho("reflect: could not parse PR URL from gh output", err=True)
            raise typer.Exit(1)
    finally:
        Path(body_path).unlink(missing_ok=True)

    _append_reflect_log(personal, f"REFLECT_PR {_utc_ts()} {url}", dry_run=False)
    typer.echo(f"CREATED: {url}")
    raise typer.Exit(0)
