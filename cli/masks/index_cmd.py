"""``masks index`` — incremental mcp-memory indexer."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

from masks.env_util import apply_env_file
from masks.paths import resolve_base_path, resolve_memory_db_path


def _resolve_base_for_index() -> Path:
    raw = os.environ.get("MASKS_BASE", "").strip()
    if raw:
        return Path(os.path.expandvars(Path(raw).expanduser())).resolve()
    return resolve_base_path()


def _load_base_env(base: Path) -> None:
    apply_env_file(base / ".env", dict(os.environ))


def _git(role_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(role_dir), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _parse_name_status(stdout: str) -> tuple[set[str], set[str], set[str]]:
    added: set[str] = set()
    modified: set[str] = set()
    deleted: set[str] = set()
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        st = parts[0]
        if st == "A" and len(parts) >= 2:
            added.add(Path(parts[1]).as_posix())
        elif st in ("M", "T") and len(parts) >= 2:
            modified.add(Path(parts[1]).as_posix())
        elif st == "D" and len(parts) >= 2:
            deleted.add(Path(parts[1]).as_posix())
        elif st.startswith("R") and len(parts) >= 3:
            deleted.add(Path(parts[1]).as_posix())
            added.add(Path(parts[2]).as_posix())
    return added, modified, deleted


def _ls_files_memory(role_dir: Path) -> list[str]:
    r = _git(role_dir, "ls-files", "--cached", "--", "Memory/")
    if r.returncode != 0:
        return []
    return [Path(p).as_posix() for p in r.stdout.splitlines() if p.strip()]


def _collect_memory_files(role_dir: Path) -> set[str]:
    out: set[str] = set()
    mem_root = role_dir / "Memory"
    if not mem_root.is_dir():
        return out
    for p in mem_root.rglob("*"):
        if p.is_file():
            out.add(p.relative_to(role_dir).as_posix())
    return out


async def _run_index(role: str, rebuild: bool) -> int:
    if not role or "/" in role or role.startswith(".") or ".." in role:
        print("masks index: invalid role name", file=sys.stderr)
        return 2
    base = _resolve_base_for_index()
    _load_base_env(base)
    db_path = resolve_memory_db_path()
    if not db_path.parent.is_dir():
        db_path.parent.mkdir(parents=True, exist_ok=True)

    role_dir = (base / role).resolve()
    if not role_dir.is_dir():
        print("masks index: role directory does not exist", file=sys.stderr)
        return 2
    if not (role_dir / ".git").is_dir():
        print("masks index: role path is not a git repo", file=sys.stderr)
        return 2

    from mcp_memory_service.models.memory import Memory
    from mcp_memory_service.storage.sqlite_vec import SqliteVecMemoryStorage
    from mcp_memory_service.utils.hashing import generate_content_hash

    added: set[str] = set()
    modified: set[str] = set()
    deleted: set[str] = set()

    if rebuild:
        added = _collect_memory_files(role_dir)
    else:
        rv = _git(role_dir, "rev-parse", "--verify", "HEAD~1")
        if rv.returncode != 0:
            added = set(_ls_files_memory(role_dir))
        else:
            diff = _git(role_dir, "diff", "--name-status", "HEAD~1", "HEAD", "--", "Memory/")
            if diff.returncode != 0:
                print("masks index: git diff failed", file=sys.stderr)
                return 1
            added, modified, deleted = _parse_name_status(diff.stdout)
            if not added and not modified and not deleted:
                print(
                    f"masks index {role}: incremental — 0 added, 0 modified, 0 deleted, "
                    f"0 evictions, 0 stores — no Memory/ changes"
                )
                return 0

    storage: SqliteVecMemoryStorage | None = None
    try:
        storage = SqliteVecMemoryStorage(db_path=str(db_path))
        await storage.initialize()
        evictions = 0
        stores = 0

        if rebuild:
            n, _msg = await storage.delete_by_tag(f"role:{role}")
            evictions += int(n)
        else:
            for rel in sorted(modified | deleted):
                n, _msg = await storage.delete_by_tag(f"file:{rel}")
                evictions += int(n)

        for rel in sorted(added | modified):
            full = role_dir / rel
            if not full.is_file():
                print(f"masks index: expected file missing: {full}", file=sys.stderr)
                return 1
            content = full.read_text(encoding="utf-8", errors="strict")
            ch = generate_content_hash(content)
            mem = Memory(
                content=content,
                content_hash=ch,
                tags=[f"role:{role}", f"file:{rel}"],
                memory_type="observation",
                metadata={},
            )
            await storage.store(mem, skip_semantic_dedup=False)
            stores += 1

        if rebuild:
            print(f"masks index {role}: rebuild — cleared role:{role}, stored {stores} observation(s)")
        else:
            print(
                f"masks index {role}: incremental — evicted {evictions} file tag(s), "
                f"stored {stores} observation(s), skipped 0"
            )
        return 0
    except UnicodeDecodeError as e:
        print(f"masks index: unicode error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"masks index: {e}", file=sys.stderr)
        return 1
    finally:
        if storage is not None:
            await storage.close()


def index_main(role: str, rebuild: bool = False) -> int:
    """Update mcp-memory SQLite index from git-tracked Memory/ markdown."""
    return asyncio.run(_run_index(role, rebuild))
