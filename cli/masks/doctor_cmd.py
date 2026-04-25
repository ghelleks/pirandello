"""``masks doctor`` — seven health checks (six blocking + budget WARN)."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import typer

from masks.ooda_parse import extract_agenda_skills
from masks.paths import resolve_base_path, resolve_framework_root, resolve_memory_db_path
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


def doctor_cmd(json_out: bool = typer.Option(False, "--json", help="Emit machine-readable JSON")) -> None:
    """Run Pirandello health checks."""
    base = resolve_base_path()
    fw = resolve_framework_root()
    checks: list[dict[str, Any]] = []

    def add(cid: str, ok: bool, msg: str, status: str | None = None) -> None:
        st = status or ("pass" if ok else "fail")
        checks.append({"id": cid, "status": st, "message": msg})

    # 1 agents_symlink
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
    else:
        msg1 = "AGENTS.md missing or not a symlink"
    add("agents_symlink", ok1, msg1)

    # 2 role_env
    roles = list(iter_role_dirs(base))
    missing_env = [r.name for r in roles if not (r / ".env").is_file()]
    ok2 = not missing_env
    msg2 = "all roles have .env" if ok2 else f"missing .env: {', '.join(missing_env)}"
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

    # 5 ooda_agenda
    bad_ooda: list[str] = []
    for r in roles:
        skills = extract_agenda_skills(r / "OODA.md")
        if not skills:
            bad_ooda.append(r.name)
    ok5 = not bad_ooda
    msg5 = "all roles parseable" if ok5 else f"missing or empty agenda: {', '.join(bad_ooda)}"
    add("ooda_agenda", ok5, msg5)

    # 6 guards_executable
    all_skills: set[str] = set()
    for r in roles:
        all_skills.update(extract_agenda_skills(r / "OODA.md"))
    guards_dir = fw / "guards"
    bad_guards: list[str] = []
    if not guards_dir.is_dir():
        bad_guards.append("guards/ directory missing")
    else:
        for s in sorted(all_skills):
            g = guards_dir / f"{s}.sh"
            if not g.is_file():
                bad_guards.append(f"missing {s}.sh")
            elif not os.access(g, os.X_OK):
                bad_guards.append(f"{s}.sh not executable")
    ok6 = not bad_guards
    msg6 = "all guards present" if ok6 else "; ".join(bad_guards)
    add("guards_executable", ok6, msg6)

    # 7 always_loaded_budget (WARN only)
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
