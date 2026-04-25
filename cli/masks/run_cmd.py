"""``masks run`` — OODA heartbeat: guards then optional LLM."""

from __future__ import annotations

import datetime as _dt
import os
import subprocess
from pathlib import Path
from typing import Optional

import typer

from masks.env_util import merge_env_for_role
from masks.ooda_parse import extract_agenda_skills
from masks.paths import resolve_base_path, resolve_framework_root


def _ts() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _one_line(s: str, max_len: int = 2000) -> str:
    return s.replace("\n", "\\n")[:max_len]


def _append_log(role_dir: Path, line: str) -> None:
    with open(role_dir / ".ooda.log", "a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")


def run_command(role: str = typer.Argument(..., help="Role name under base")) -> None:
    """Evaluate OODA.md guards; spawn LLM only if any guard exits 0."""
    base = resolve_base_path()
    fw = resolve_framework_root()
    role_dir = (base / role).resolve()
    ooda = role_dir / "OODA.md"

    if not role_dir.is_dir():
        typer.secho(f"Role directory not found: {role}", err=True, fg=typer.colors.RED)
        raise typer.Exit(2)

    if not ooda.is_file():
        _append_log(
            role_dir,
            f"ts={_ts()} role={role} WARN=OODA_MISSING path={ooda.resolve()} llm=no",
        )
        raise typer.Exit(0)

    warnings: list[str] = []

    def _warn(kind: str, line_no: int, text: str) -> None:
        esc = _one_line(text, 500)
        warnings.append(f"ts={_ts()} role={role} {kind} line={line_no} text={esc}")

    skills = extract_agenda_skills(ooda, warn=_warn)
    for w in warnings:
        _append_log(role_dir, w)

    env = merge_env_for_role(base, role_dir)
    env["MASKS_BASE"] = str(base)
    env["BASE"] = str(base)
    env["MASKS_ROLE"] = role
    env["MASKS_ROLE_DIR"] = str(role_dir)
    env["MASKS_OODA_PATH"] = str(ooda.resolve())

    guards_dir = fw / "guards"
    results: list[tuple[str, Optional[int], Optional[str]]] = []
    for s in skills:
        g = guards_dir / f"{s}.sh"
        if not g.is_file() or not os.access(g, os.X_OK):
            results.append((s, None, "missing_or_not_executable"))
            continue
        try:
            proc = subprocess.run(
                [str(g)],
                cwd=role_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=5,
            )
            results.append((s, proc.returncode, None))
            if proc.stderr and proc.stderr.strip():
                chunk = _one_line(proc.stderr, 2048)
                _append_log(role_dir, f"ts={_ts()} role={role} WARN_GUARD_STDERR name={s} msg={chunk}")
        except subprocess.TimeoutExpired:
            results.append((s, None, "timeout"))
            _append_log(role_dir, f"ts={_ts()} role={role} WARN_GUARD_TIMEOUT skill={s}")

    codes: list[str] = []
    trigger = False
    for name, code, err in results:
        if err == "missing_or_not_executable":
            codes.append(f"{name}:X")
        elif err == "timeout":
            codes.append(f"{name}:T")
        elif code is not None:
            codes.append(f"{name}:{code}")
            if code == 0:
                trigger = True
        else:
            codes.append(f"{name}:X")

    guard_part = "|".join(codes) if codes else ""
    llm_spawned = False
    llm_cmd = os.environ.get("MASKS_LLM_CMD", "").strip()
    text = ooda.read_text(encoding="utf-8", errors="replace")
    debug = os.environ.get("MASKS_LLM_DEBUG", "").strip() == "1"

    if trigger:
        llm_spawned = True
        if not llm_cmd:
            argv = ["claude", "--print", "--output-format", "text"]
        else:
            argv = ["/bin/sh", "-c", llm_cmd]
        run_kw: dict = {
            "cwd": role_dir,
            "env": env,
            "input": text,
            "text": True,
        }
        if debug:
            run_kw["capture_output"] = True
        else:
            run_kw["stdout"] = subprocess.DEVNULL
            run_kw["stderr"] = subprocess.DEVNULL
        r = subprocess.run(argv, **run_kw)
        if debug and getattr(r, "stderr", None) and r.stderr.strip():
            _append_log(
                role_dir,
                f"ts={_ts()} role={role} LLM_STDERR {_one_line(r.stderr, 16384)}",
            )
        if r.returncode != 0:
            _append_log(role_dir, f"ts={_ts()} role={role} LLM_EXIT code={r.returncode}")

    ooda_ok = ""
    if not llm_spawned:
        ooda_ok = " OODA_OK"

    primary = (
        f"ts={_ts()} role={role} guards={guard_part} trigger={'yes' if trigger else 'no'} "
        f"llm={'yes' if llm_spawned else 'no'}{ooda_ok}"
    )
    _append_log(role_dir, primary)
    raise typer.Exit(0)
