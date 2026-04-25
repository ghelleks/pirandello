"""Token counting for always-loaded stack (S-08). Shared by doctor and start.sh."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import tiktoken


def _encoding():
    return tiktoken.get_encoding("cl100k_base")


def count_tokens_file(path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        body = path.read_bytes()
        text = body.decode("utf-8", errors="replace")
    except OSError:
        return 0
    return len(_encoding().encode(text))


def combined_always_loaded(base: Path, role_path: Path) -> int:
    """SELF (personal) + ROLE + CONTEXT for one role."""
    self_md = base / "personal" / "SELF.md"
    role_md = role_path / "ROLE.md"
    ctx_md = role_path / "CONTEXT.md"
    return count_tokens_file(self_md) + count_tokens_file(role_md) + count_tokens_file(ctx_md)


def _main_argv() -> None:
    p = argparse.ArgumentParser(description="Pirandello token budget helper")
    sub = p.add_subparsers(dest="cmd", required=True)
    al = sub.add_parser("always-loaded", help="Print combined token count for SELF+ROLE+CONTEXT")
    al.add_argument("--base", type=Path, required=True)
    al.add_argument("--role-dir", type=Path, required=True)
    args = p.parse_args()
    if args.cmd == "always-loaded":
        n = combined_always_loaded(args.base.resolve(), args.role_dir.resolve())
        print(n)


if __name__ == "__main__":
    _main_argv()
