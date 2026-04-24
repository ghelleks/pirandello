# Proposal: `masks index` — mcp-memory incremental indexer

**Unit:** `docs/specs/masks-index/SPEC.md`  
**Deliverable:** `cli/masks/index.py` (invoked by the existing `masks` CLI entrypoint)  
**Dependencies:** `mcp-memory-service` in `cli/pyproject.toml` (same version pin as any future MCP server packaging).

---

## 1. Overview

`masks index <role> [--rebuild]` keeps the shared SQLite-vec mcp-memory database aligned with markdown files under `$BASE/<role>/Memory/`. **Git history is the change detector** in incremental mode: the command compares `HEAD~1` and `HEAD` for paths under `Memory/`, classifies paths as added, modified, or deleted, then updates the database so each live file corresponds to exactly one semantic row. **The markdown files remain canonical**; the database is a disposable search accelerator, rebuilt at any time from disk + git.

The command runs **entirely in-process** via `SqliteVecMemoryStorage`: no MCP server process, no `memory` CLI, no HTTP. It is suitable for post-commit hooks and manual repair (`--rebuild`).

**Base path resolution:** `$BASE = os.environ.get("MASKS_BASE")` with `~` and env vars expanded (`os.path.expandvars(expanduser(...)))`; if unset or empty after strip, `$BASE = Path.home() / "Desktop"`. Resolve to an absolute path.

**Environment loading order:** Immediately after resolving `$BASE`, load `$BASE/.env` into the process environment **before** validating `MCP_MEMORY_DB_PATH` (using a small parser that ignores `export`, strips quotes, and skips comments — or depend on `python-dotenv` if already in the CLI stack). This satisfies “direct invocation works without the caller pre-sourcing” while still allowing `MASKS_BASE` to point at the base directory when the hook does not set it.

**Working directory for git:** All `git` subprocess calls use `-C "$BASE/<role>"` so the command does not depend on the user’s cwd.

---

## 2. Storage initialization

Use the async API exactly as in `docs/design.md`:

```python
from mcp_memory_service.storage.sqlite_vec import SqliteVecMemoryStorage

db_path = os.environ["MCP_MEMORY_DB_PATH"]  # validated after .env load
storage = SqliteVecMemoryStorage(db_path=db_path)
await storage.initialize()
```

**Constructor:** Only `db_path` is required per current library usage; no extra connection flags are passed. If the parent directory for the DB file does not exist, **fail fast** with a clear message (“directory for MCP_MEMORY_DB_PATH does not exist”) before `initialize()`, unless the library creates it — in that case, document behavior as library-defined and do not add redundant mkdir logic.

**Lifecycle:** Wrap all work after successful validation in `try` / `finally` so `await storage.close()` runs on every path once `storage` has been constructed. If validation fails before construction, there is nothing to close.

---

## 3. Incremental diff logic

**Git command (exact):**

```bash
git -C "$BASE/$role" diff --name-status HEAD~1 HEAD -- Memory/
```

**Parsing:** Read stdout line-by-line. Skip empty lines.

- **Status column:** First field is the status token (`A`, `M`, `D`, or `R` + similarity for renames).
- **Added:** Lines where status is `A` → path is the second field. Normalize to use forward slashes (git may emit backslashes on Windows; normalize with `Path.as_posix()` after parsing).
- **Modified:** Status `M` (or `T` type-change, treated as modified) → second field.
- **Deleted:** Status `D` → second field.
- **Renames:** Status starting with `R` → fields are `R123\toldpath\tnewpath`. Treat as **delete** `oldpath` and **add** `newpath` (both under `Memory/`), matching the spec’s A/M/D model and avoiding orphaned rows.

**First-commit edge case (`HEAD~1` missing):** Before running the diff, run:

```bash
git -C "$BASE/$role" rev-parse --verify HEAD~1
```

If this exits non-zero (repository has a single commit or empty history), **do not** run `git diff HEAD~1 HEAD`. Instead, build the **Added** set as all tracked files under `Memory/`:

```bash
git -C "$BASE/$role" ls-files --cached -- 'Memory/'
```

Every returned path is classified as **Added**; **Modified** and **Deleted** are empty. This ingests all memory files on the first post-commit without shell errors from an invalid `HEAD~1`.

**Empty diff:** If after classification there are zero paths in Added ∪ Modified ∪ Deleted, print the summary (`0 added, 0 modified, 0 deleted, 0 evictions, 0 stores — no Memory/ changes`) and **exit 0 without constructing `SqliteVecMemoryStorage`**, so there are zero DB operations (no `initialize`, `store`, or `delete_by_tag`).

**Non-incremental entry to rebuild:** If `--rebuild` is set, skip diff logic entirely (see §5).

---

## 4. Memory object construction

For each file path `rel` (always relative to the Role repo root, e.g. `Memory/People/alice.md`):

1. Read `full_path = $BASE/<role>/rel` as text: `encoding="utf-8"`, `errors="strict"`. On `UnicodeDecodeError`, abort the run with a clear message naming the file (non-zero exit) after `close()` in `finally`.
2. `content` = full file text (entire file, no stripping that would change meaning).
3. `content_hash` = `generate_content_hash(content)` from `mcp_memory_service.utils.hashing`.
4. `tags` = **exactly two strings, in stable order:** `[f"role:{role}", f"file:{rel}"]` where `role` is the CLI argument (e.g. `work`, `personal`). No extra tags are added by the indexer (optional tags from markdown front matter are **not** parsed — keeps M-02 unambiguous).
5. `memory_type` = `"observation"` (literal).
6. `metadata` = `{}` (empty dict). If the `Memory` model requires `None` vs `{}`, use whatever the constructor defaults to, but prefer `{}` for explicit “indexer adds no metadata.”

Construct via the library’s `Memory` model (import from `mcp_memory_service.models.memory`) with the fields the constructor accepts; if the model uses optional `id`, leave it unset so the storage layer assigns it.

**One file → one `Memory` object:** No chunking, no splitting on headings, regardless of length (M-04).

---

## 5. Rebuild logic

When `--rebuild` is passed:

1. Construct and initialize storage (after env validation).
2. Call `await storage.delete_by_tag(f"role:{role}")` once. This removes **only** rows tagged for this Role, preserving `role:personal`, `role:consulting`, etc. (M-06, S-02).
3. Walk `$BASE/<role>/Memory/` **recursively** with `os.walk` (or `pathlib.Path.rglob`). For each regular file (not directory), compute `rel` as the path relative to `$BASE/<role>/` with POSIX separators.
4. For each file, build and `store()` a `Memory` object as in §4.

**Why `delete_by_tag("role:<role>")` instead of dropping the DB file:** The database is **shared across all Roles**. A full wipe would destroy every other Role’s index and violate custody-safe regeneration (one Role’s repair must not nuke another). Role-scoped delete matches the tag schema in `docs/design.md`.

---

## 6. Error handling

| Condition | Behavior |
|-----------|----------|
| `$BASE/<role>` is not a directory | Exit non-zero, message: role directory does not exist (no stack trace). |
| Not a git repository | Exit non-zero, message: role path is not a git repo. |
| After sourcing `$BASE/.env`, `MCP_MEMORY_DB_PATH` is unset or empty | Exit non-zero, **single stderr line** to user: e.g. `masks index: MCP_MEMORY_DB_PATH is not set. Add it to <base>/.env.` No traceback (M-09). **Do not** create or write any file before this check beyond reading `.env`. |
| `delete_by_tag` or `store` raises | Log concise error to stderr; `finally` still calls `storage.close()`; exit non-zero. Rely on library/transaction semantics for consistency; the spec expects no half-applied *application-level* sequence — implement per-file ordering for incremental: complete all deletes for the batch before stores, so a failure mid-store leaves prior deletes committed (acceptable; user can re-run index). |
| File read error (permission, missing) on an **added/modified** path | If the path is in Added/Modified but file is missing (race), exit non-zero with clear message. Deleted paths are never read. |
| `--rebuild` with empty `Memory/` tree | Still delete_by_tag for role, then zero stores; exit 0 with summary. |

**Top-level `main`:** Catch unexpected exceptions, print a one-line message, exit 1 — optional `masks --verbose` flag (future) could print traceback; default must stay user-safe for M-09-style clarity.

---

## 7. Self-check table

### Unit metrics (`docs/specs/masks-index/SPEC.md`)

| ID | Result | Note |
|----|--------|------|
| M-01 | Pass | Uses `SqliteVecMemoryStorage` only; no MCP server or CLI subprocess. |
| M-02 | Pass | Tags list is exactly `role:<role>` and `file:<relpath>`; no indexer-added extras. |
| M-03 | Pass | For every path in Modified ∪ Deleted, `delete_by_tag("file:…")` runs before any `store()` for that path; Modified processed delete-then-store. |
| M-04 | Pass | One full-file read → one `Memory` → one `store()` per path. |
| M-05 | Pass | Empty classified diff → exit before storage init; no `store`/`delete_by_tag`. |
| M-06 | Pass | Rebuild begins with `delete_by_tag(f"role:{role}")` only. |
| M-07 | Pass | `try`/`finally` around all operations after storage construction ensures `await storage.close()`. |
| M-08 | Pass | `HEAD~1` missing → `ls-files Memory/` as all Added; no failing diff. |
| M-09 | Pass | Validated after `.env` load; user-facing message without traceback. |
| M-10 | Pass | `$BASE/.env` loaded before reading `MCP_MEMORY_DB_PATH`. |

### Top-level requirements (`docs/SPEC.md`)

| ID | Result | Note |
|----|--------|------|
| S-01 | Pass | Proposal introduces no personal content into `pirandello/`; indexer runs against user Role dirs only. |
| S-02 | Pass | Indexer only mirrors files; DB is derived, never authoritative. |
| S-03 | Pass | Indexing is hook-invoked / CLI; not an AGENTS.md-only convention. |
| S-04 | Pass | Command only reads/writes DB tags for the named `<role>`; does not write other Roles’ `Memory/` trees. |
| S-05 | Pass | Re-running incremental on unchanged tree is no-op; `--rebuild` is idempotent for a given filesystem state. |
| S-06 | Pass | No code path touches `SELF.md`. |
| S-07 | Pass | No always-loaded docs produced by this unit. |

### Stdout summary (soft constraint)

After a run that touched the database, print one line, for example:

`masks index work: incremental — evicted 2 file tag(s), stored 3 observation(s), skipped 0`

Rebuild:

`masks index work: rebuild — cleared role:work, stored 42 observation(s)`

---

## Implementation notes (non-normative but helpful)

- **Async entrypoint:** Implement `async def index_role(role: str, *, rebuild: bool) -> int` and expose `def main()` that calls `asyncio.run(...)`.
- **Role name validation:** Reject `role` values containing `/`, `..`, or empty string to avoid path traversal.
- **Performance:** For ≤100 files, single-process async + sqlite is well under 10s on typical hardware; avoid per-file subprocesses beyond the one `git diff` / `git ls-files` / `rev-parse`.
