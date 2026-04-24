# Proposal: Session Hooks

**Unit:** session-hooks  
**Spec:** `docs/specs/session-hooks/SPEC.md`  
**Date:** 2026-04-24

---

## 1. Overview

The session-hooks unit delivers three role-agnostic Bash scripts under `pirandello/hooks/`: **`start.sh`** syncs the active Role repo and `personal/`, loads environment variables, validates that the workspace root is a real Role directory, checks the **always-loaded token budget** (`SELF.md` + `ROLE.md` + `CONTEXT.md`) via a small Python helper and emits a **stderr warning** when the combined count exceeds **1,500 tokens** (no truncation — all sections are still injected in full), then prints the prompt stack to stdout in a fixed order; **`end.sh`** returns to the Role root, stages all changes, creates at most one timestamped commit when there is something to commit, and pushes without surfacing network or configuration failures; **`post-commit.sh`** runs after each successful commit, diffs `Memory/` between the new commit and its parent (or lists `Memory/` paths on the root commit), and invokes `masks index <role>` only when files under `Memory/` were added, modified, or deleted. Together they enforce pull-then-inject ordering, silent git failure semantics, conditional commits, incremental mcp-memory indexing, and **infrastructure-visible** combined budget signaling per **S-08**, while keeping file-backed `Memory/` canonical.

---

## 2. Script implementations

### Combined budget warning (S-08) — contract

- **Helper:** `cli/masks/token_budget.py` (delivered with **`masks` CLI**; same encoder as the reflect skill: **tiktoken `cl100k_base`**). It exposes a CLI entry point that prints a single integer: the sum of token counts for the three always-loaded paths. If `CONTEXT.md` is missing, that path contributes **0** tokens (file not read).
- **Invocation from `start.sh`:** Resolve framework root as `PIRANDELLO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"`. After validation, pulls, and `.env` sourcing — and **before any prompt-stack output on stdout** — run the helper (prefer **`uv run python ...`** from `"$PIRANDELLO_ROOT"` so `tiktoken` resolves; fall back to `python3` on `PATH` if the installer documents that).
- **When it fires:** If the integer **strictly exceeds 1500**, print **exactly** (to **stderr**):

  `WARNING: always-loaded context is N tokens (budget: 1500). Run masks doctor for remediation.`

  where `N` is the computed total. **Do not** truncate, omit, or shorten `SELF`, `ROLE`, or `CONTEXT` body text on stdout.
- **If the helper fails** (missing deps, import error): emit a **stderr** line that budget checking failed and suggest running `masks doctor` / fixing the install — then continue with full injection so the session is not blocked.

### `hooks/start.sh`

```bash
#!/usr/bin/env bash
# Pirandello session-start hook. Role = basename("$PWD"), base = dirname("$PWD").
# No arguments. POSIX-oriented Bash; do not use set -e.
# Cursor: set PIRANDELLO_CURSOR_JSON=1 in hooks.json so stdout is JSON with additional_context.

# Cursor sessionStart passes JSON on stdin; drain it so it cannot block or pollute output.
if [ ! -t 0 ]; then
  cat >/dev/null 2>&1 || true
fi

BASE=$(dirname "$PWD")
ROLE=$(basename "$PWD")
PIRANDELLO_ROOT=$(cd "$(dirname "$0")/.." && pwd)

# Valid Role workspace: ROLE.md here, global AGENTS at base, personal SELF present.
if [ ! -f "$PWD/ROLE.md" ] || [ ! -f "$BASE/AGENTS.md" ] || [ ! -f "$BASE/personal/SELF.md" ]; then
  printf '%s\n' "=== PIRANDELLO HOOK ERROR ===" "Open your Role folder as the Cursor or Claude Code workspace root (the directory that contains ROLE.md), not the Desktop base or a task subfolder." "" >&2
  exit 0
fi

# Pull before any context output (active Role repo, then personal/ for latest SELF.md).
git pull --ff-only 2>/dev/null || true
git -C "$BASE/personal" pull --ff-only 2>/dev/null || true

# Cross-role infra first, then Role-specific overrides.
[ -f "$BASE/.env" ] && . "$BASE/.env"
[ -f "$PWD/.env" ] && . "$PWD/.env"

# S-08: warn on combined always-loaded budget; never truncate injection.
pirandello_warn_always_loaded_budget() {
  _ctx=""
  [ -f "$PWD/CONTEXT.md" ] && _ctx="$PWD/CONTEXT.md"
  _sum=""
  if _sum=$(cd "$PIRANDELLO_ROOT" && uv run python cli/masks/token_budget.py always-loaded-sum \
      "$BASE/personal/SELF.md" "$PWD/ROLE.md" "$_ctx" 2>/dev/null); then
    :
  elif _sum=$(python3 "$PIRANDELLO_ROOT/cli/masks/token_budget.py" always-loaded-sum \
      "$BASE/personal/SELF.md" "$PWD/ROLE.md" "$_ctx" 2>/dev/null); then
    :
  else
    printf '%s\n' "WARNING: could not compute always-loaded token budget (helper failed). Run masks doctor after fixing the masks install." >&2
    return 0
  fi
  if [ "${_sum:-0}" -gt 1500 ] 2>/dev/null; then
    printf 'WARNING: always-loaded context is %s tokens (budget: 1500). Run masks doctor for remediation.\n' "$_sum" >&2
  fi
}
pirandello_warn_always_loaded_budget

pirandello_emit_prompt_stack() {
  # Always-emitted sections (no per-section file guard; validation ensured these exist).
  echo "=== GLOBAL AGENTS ===" && cat "$BASE/AGENTS.md"
  echo "=== SELF ===" && cat "$BASE/personal/SELF.md"
  echo "=== ROLE ===" && cat "$PWD/ROLE.md"
  # Conditional sections: header and body only when the file exists.
  if [ -f "$PWD/AGENTS.md" ]; then
    echo "=== ROLE AGENTS ===" && cat "$PWD/AGENTS.md"
  fi
  if [ -f "$PWD/CONTEXT.md" ]; then
    echo "=== CONTEXT ===" && cat "$PWD/CONTEXT.md"
  fi
  if [ -f "$PWD/Archive/INDEX.md" ]; then
    echo "=== ARCHIVE INDEX ===" && cat "$PWD/Archive/INDEX.md"
  fi
  if [ -f "$PWD/Memory/INDEX.md" ]; then
    echo "=== MEMORY INDEX ===" && cat "$PWD/Memory/INDEX.md"
  fi
  if [ -f "$PWD/Reference/INDEX.md" ]; then
    echo "=== REFERENCE INDEX ===" && cat "$PWD/Reference/INDEX.md"
  fi
}

if [ "${PIRANDELLO_CURSOR_JSON:-}" = 1 ]; then
  pirandello_emit_prompt_stack | python3 -c 'import json,sys; print(json.dumps({"additional_context": sys.stdin.read()}))'
else
  pirandello_emit_prompt_stack
fi

exit 0
```

**Note:** The `always-loaded-sum` subcommand is illustrative; the implementer may use an equivalent module interface (`python -m masks.token_budget`, etc.) as long as the **encoder**, **three paths**, **missing CONTEXT = 0 tokens**, **stderr warning text**, and **no truncation** match this contract.

### `hooks/end.sh`

```bash
#!/usr/bin/env bash
# Pirandello session-end hook.

if [ ! -t 0 ]; then
  cat >/dev/null 2>&1 || true
fi

BASE=$(dirname "$PWD")
ROLE=$(basename "$PWD")

if [ ! -f "$BASE/$ROLE/ROLE.md" ] || [ ! -f "$BASE/AGENTS.md" ] || [ ! -f "$BASE/personal/SELF.md" ]; then
  printf '%s\n' "=== PIRANDELLO HOOK ERROR ===" "Session end skipped: workspace root is not a Role directory." >&2
  exit 0
fi

cd "$BASE/$ROLE" 2>/dev/null || exit 0

git add -A 2>/dev/null || true
git diff --cached --quiet 2>/dev/null || git commit -m "session: $(date '+%Y-%m-%d %H:%M')" 2>/dev/null || true
git push 2>/dev/null || true

exit 0
```

### `hooks/post-commit.sh`

```bash
#!/usr/bin/env bash
# Pirandello git post-commit hook: incremental mcp-memory index when Memory/ changes.

TOP=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
BASE=$(dirname "$TOP")
ROLE=$(basename "$TOP")

if git -C "$TOP" rev-parse --verify HEAD~1 >/dev/null 2>&1; then
  CHANGED=$(git -C "$TOP" diff --name-only HEAD~1 HEAD -- Memory/ 2>/dev/null || true)
  DELETED=$(git -C "$TOP" diff --name-status HEAD~1 HEAD -- Memory/ 2>/dev/null | awk '/^D/{print $2}' || true)
else
  # First commit: no HEAD~1; treat all Memory/ paths in this commit as changes.
  CHANGED=$(git -C "$TOP" diff-tree --no-commit-id --name-only -r HEAD -- Memory/ 2>/dev/null || true)
  DELETED=""
fi

[ -z "$CHANGED" ] && [ -z "$DELETED" ] && exit 0

[ -f "$BASE/.env" ] && . "$BASE/.env"

masks index "$ROLE" 2>/dev/null || true
exit 0
```

---

## 3. Installation targets

`masks setup` (and `masks add-role`) materialize hook wiring for every Role. The canonical scripts stay in the Pirandello clone; install paths embed the absolute path to that clone recorded at setup time (e.g. from `realpath` on the `masks` entrypoint or a `PIRANDELLO_ROOT` written into `[base]/.masks-framework`).


| Hook               | Runtime     | Installed to                    | Mechanism                                                                                                                                                                                                                                          |
| ------------------ | ----------- | ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **start.sh**       | Cursor      | `[role]/.cursor/hooks.json`     | `hooks.sessionStart` → `{ "command": "env PIRANDELLO_CURSOR_JSON=1 bash <PIRANDELLO_ROOT>/hooks/start.sh" }` so stdout is a single JSON object with `additional_context` (plain-text stack). Optional `timeout` 120s. Same pattern for every Role. |
| **end.sh**         | Cursor      | `[role]/.cursor/hooks.json`     | `hooks.sessionEnd` → `<PIRANDELLO_ROOT>/hooks/end.sh`.                                                                                                                                                                                             |
| **start.sh**       | Claude Code | `[role]/CLAUDE.md`              | Lifecycle section (e.g. “On session start”) runs `bash <PIRANDELLO_ROOT>/hooks/start.sh` and appends stdout to the session context per Claude Code’s documented lifecycle hook pattern.                                                            |
| **end.sh**         | Claude Code | `[role]/CLAUDE.md`              | “On session end” runs `bash <PIRANDELLO_ROOT>/hooks/end.sh`.                                                                                                                                                                                       |
| **post-commit.sh** | git         | `[role]/.git/hooks/post-commit` | Executable file: `#!/bin/sh` + `exec bash <PIRANDELLO_ROOT>/hooks/post-commit.sh` (or a copy of the script) so the repo’s post-commit always calls the canonical logic.                                                                            |


**Note:** `.cursor/hooks.json` and `CLAUDE.md` fragments are **per-Role** files living in the user’s base directory (not committed to `pirandello/`). Only the three scripts in `pirandello/hooks/` are framework deliverables.

---

## 4. Edge cases addressed

- **Missing optional prompt files (`AGENTS.md`, `CONTEXT.md`, indexes):** Headers for those sections are omitted entirely; no empty labelled blocks (avoids token waste and matches M-03).
- **Missing always-loaded files after validation:** Validation requires `AGENTS.md`, `personal/SELF.md`, and `ROLE.md` before emitting context, so `cat` on those paths does not fail in normal use.
- **S-08 combined budget:** After pulls and `.env` sourcing, `start.sh` sums tokens for `personal/SELF.md`, `[role]/ROLE.md`, and `[role]/CONTEXT.md` (missing `CONTEXT.md` → **0** tokens for that leg). If sum **> 1500**, emit the **stderr** warning line above; stdout still contains full file bodies for all sections. **`masks doctor`** repeats the same metric for offline remediation (see `docs/plans/system/PLAN.md` §6).
- **No staged changes at session end:** `git diff --cached --quiet` prevents `git commit`; no empty “session:” commits; `post-commit` does not run.
- **No git remote / push errors:** `git push 2>/dev/null || true`; commit still succeeds locally.
- **Pull errors / offline:** `git pull --ff-only 2>/dev/null || true` on both repos; session continues with local files.
- **First commit (no `HEAD~1`):** `post-commit.sh` uses `diff-tree -r HEAD -- Memory/` so new `Memory/` files in the initial commit still trigger `masks index`.
- **Deleted `Memory/` files:** `DELETED` uses `git diff --name-status HEAD~1 HEAD -- Memory/ | awk '/^D/{print $2}'` as required; `masks index` receives the Role name so the indexer can evict by tag (see `masks index` unit).
- **`.env` missing at base or Role:** `[ -f ... ] && .` guards; no startup failure.
- **Base `.env` then Role `.env`:** Sourcing order matches spec; Role keys override base.
- **`masks index` or DB temporarily broken:** `masks index ... || true` avoids breaking git’s post-commit chain.
- **Cursor `sessionStart` JSON:** When `PIRANDELLO_CURSOR_JSON=1`, the stack is wrapped with `python3`’s `json.dumps`; Python 3 must be on `PATH` in the hook environment (same expectation as other Cursor command hooks).
- **Workspace root = base directory or task subfolder:** `start.sh` and `end.sh` detect missing `ROLE.md` / misplaced `SELF` path and print a **stderr** banner (`=== PIRANDELLO HOOK ERROR ===`) with user-facing wording (no filesystem paths), then exit **0** so the IDE session is not aborted—meeting T9’s “observable failure” without silent wrong identity injection. `end.sh` skips git when validation fails so a task folder is not treated as its own repo.
- **Global-read / write-local (work session, colleague in `personal/Memory/`):** The hook only injects `[role]/Memory/INDEX.md`, not `personal/Memory/INDEX.md`. The agent learns the global-read rule from **global `AGENTS.md`** (system design); new facts about Frank created in a work session are written under `work/Memory/` and committed only to the work repo by `end.sh`, preserving S-04.

---

## 5. Self-check table

### Unit metrics (`docs/specs/session-hooks/SPEC.md`)


| ID   | Result | Note                                                                                                          |
| ---- | ------ | ------------------------------------------------------------------------------------------------------------- |
| M-01 | Pass   | `BASE`/`ROLE` from `dirname`/`basename` of `$PWD` only; no parameters.                                        |
| M-02 | Pass   | Order: GLOBAL AGENTS → SELF → ROLE → optional five in listed sequence.                                        |
| M-03 | Pass   | Five conditional blocks wrapped in `-f` tests; three always-emitted use unconditional `cat` after validation. |
| M-04 | Pass   | Both pulls precede any `echo`/`cat` context lines; `.env` sourced before stack; S-08 check runs after sourcing, before stack stdout. |
| M-05 | Pass   | Commit only when `git diff --cached --quiet` fails (staged diff exists).                                      |
| M-06 | Pass   | Pull/push/add/commit/diff wrapped with silent-failure patterns; token helper failures emit stderr notice and continue (no hook abort). |
| M-07 | Pass   | Early exit when `CHANGED` and `DELETED` both empty.                                                           |
| M-08 | Pass   | `DELETED` from `--name-status` + `awk '/^D/'`.                                                                |
| M-09 | Pass   | Root commit path uses `diff-tree` without `HEAD~1`.                                                           |


### Top-level SPEC metrics (`docs/SPEC.md`)


| ID   | Result | Note                                                                                                                             |
| ---- | ------ | -------------------------------------------------------------------------------------------------------------------------------- |
| S-01 | Pass   | Proposal text contains no credentials or personal data; scripts only reference structural names (`Memory/`, `personal/SELF.md`). |
| S-02 | Pass   | Indexing is triggered by git diff over files; DB remains derived.                                                                |
| S-03 | Pass   | Per-session pull, inject, combined-budget warning, commit, push, and index triggers are all hook/CLI infrastructure — not AGENTS.md-only. |
| S-04 | Pass   | Hooks never write `Memory/`; `end.sh` only touches the active Role repo; cross-role policy is AGENTS-level.                      |
| S-05 | Pass   | No new `masks` subcommands defined here beyond dependency on shared `token_budget` helper; setup idempotency is masks-cli responsibility. |
| S-06 | Pass   | Hooks do not touch `SELF.md` except read in `start.sh`.                                                                          |
| S-07 | Pass   | Hooks do not author `SELF.md`/`ROLE.md`; per-file caps (≤500 tokens each) remain **hard limits** for producers (`masks reflect`, synthesis, onboarding) and **`masks doctor` WARN**. Hooks do not enforce per-file counts at inject time. |
| S-08 | Pass   | `start.sh` calls **`cli/masks/token_budget.py`** (tiktoken `cl100k_base`) to sum `SELF + ROLE + CONTEXT`; if **> 1500**, emits **`WARNING: always-loaded context is N tokens (budget: 1500). Run masks doctor for remediation.`** to **stderr**; **no** truncation or withholding on stdout. |

