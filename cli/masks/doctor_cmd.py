"""``masks doctor`` — five blocking checks plus token-budget WARN."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import typer

from masks.paths import resolve_base_path, resolve_memory_db_path
from masks.roles import iter_role_dirs
from masks.token_budget import combined_always_loaded


def _read_env_key(path: Path, key: str) -> str | None:
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def _has_env_entries(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False
    for line in lines:
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        if raw.startswith("export "):
            raw = raw[7:].strip()
        if "=" in raw:
            key = raw.split("=", 1)[0].strip()
            if key:
                return True
    return False


def doctor_cmd(json_out: bool = typer.Option(False, "--json", help="Emit machine-readable JSON")) -> None:
    """Run Pirandello health checks."""
    base = resolve_base_path()
    checks: list[dict[str, Any]] = []

    def add(cid: str, ok: bool, msg: str, status: str | None = None) -> None:
        st = status or ("pass" if ok else "fail")
        checks.append({"id": cid, "status": st, "message": msg})

    # 1 agents_global
    agents = base / "AGENTS.md"
    ok1 = False
    msg1 = ""
    if agents.is_symlink():
        try:
            tgt = agents.resolve()
            if tgt.is_file():
                ok1 = True
                msg1 = f"AGENTS.md -> {tgt}"
            else:
                msg1 = "symlink target missing"
        except OSError as e:
            msg1 = str(e)
    elif agents.is_file():
        ok1 = True
        msg1 = f"AGENTS.md present ({agents})"
    else:
        msg1 = "AGENTS.md missing"
    add("agents_global", ok1, msg1)

    # 2 role_env
    roles = list(iter_role_dirs(base))
    base_env = base / ".env"
    base_has_entries = _has_env_entries(base_env)
    missing_or_empty_role_env = [
        r.name for r in roles if (not (r / ".env").is_file()) or (not _has_env_entries(r / ".env"))
    ]
    if base_has_entries:
        ok2 = True
        if missing_or_empty_role_env:
            msg2 = (
                "base .env provides shared config; role .env optional/missing for: "
                + ", ".join(missing_or_empty_role_env)
            )
        else:
            msg2 = "base .env and all role .env files have entries"
    else:
        ok2 = not missing_or_empty_role_env
        msg2 = (
            "base .env empty/missing and role .env missing/empty: " + ", ".join(missing_or_empty_role_env)
            if missing_or_empty_role_env
            else "all role .env files have entries"
        )
    add("role_env", ok2, msg2)

    # 3 git_remote
    bad_remote: list[str] = []
    for r in roles:
        if not (r / ".git").is_dir():
            continue
        rr = subprocess.run(
            ["git", "-C", str(r), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
        )
        if rr.returncode != 0 or not rr.stdout.strip():
            continue  # no remote counts as pass with note per plan
        url = rr.stdout.strip()
        lr = subprocess.run(
            ["git", "-C", str(r), "ls-remote", "origin", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if lr.returncode != 0:
            bad_remote.append(f"{r.name}: ls-remote failed ({lr.stderr.strip() or lr.returncode})")
    ok3 = not bad_remote
    msg3 = "all remotes reachable" if ok3 else "; ".join(bad_remote)
    add("git_remote", ok3, msg3)

    # 4 mcp_memory_db
    db_path_resolved = resolve_memory_db_path()
    ok4 = db_path_resolved.is_file()
    msg4 = f"database {db_path_resolved}" if ok4 else f"database not found: {db_path_resolved}"
    add("mcp_memory_db", ok4, msg4)

    # 5 always_loaded_budget (WARN only)
    warn_roles: list[str] = []
    for r in roles:
        n = combined_always_loaded(base, r)
        if n > 1500:
            over = n - 1500
            warn_roles.append(f"{r.name}: {n} tokens (budget 1500, {over} over)")
    if warn_roles:
        msg7 = (
            "; ".join(warn_roles)
            + "; shorten CONTEXT.md by ~N tokens (N = overage) — or trim ROLE.md / SELF.md if CONTEXT is minimal"
        )
        add("always_loaded_budget", True, msg7, status="warn")
    else:
        add(
            "always_loaded_budget",
            True,
            "all roles ≤1500 tokens (always-loaded stack)",
            status="pass",
        )

    blocking_ok = all(c["status"] == "pass" for c in checks if c["id"] != "always_loaded_budget")

    if json_out:
        out = {"ok": blocking_ok, "checks": checks}
        typer.echo(json.dumps(out, indent=2))
    else:
        for c in checks:
            tag = c["status"].upper()
            typer.echo(f"[{tag}] {c['id']}: {c['message']}")

    if not blocking_ok:
        raise typer.Exit(1)
