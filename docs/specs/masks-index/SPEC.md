# SDD Spec: `masks index` — mcp-memory Incremental Indexer

**Context:** See `docs/spec.md` for full system design. This spec covers the command that keeps the mcp-memory SQLite-vec database synchronized with the `Memory/` files in a Role directory.

**Deliverables:** `cli/masks/index.py`. Depends on `mcp-memory-service` as a Python package dependency in `cli/pyproject.toml`.

---

## Requirements

### Hard constraints

1. Entry point: `masks index <role> [--rebuild]`.
2. Base directory resolved from `MASKS_BASE` environment variable, falling back to `~/Desktop`.
3. Before reading any environment variables, `masks index` sources `$BASE/.env` if it exists (same pattern as the post-commit hook). This ensures `MCP_MEMORY_DB_PATH` is available for both hook-invoked and direct-invocation paths without requiring the caller to pre-source the file.
4. Database path read from `MCP_MEMORY_DB_PATH` in the environment (populated in step 3). If unset after sourcing, exit with a clear error message.
5. Uses `mcp_memory_service.storage.sqlite_vec.SqliteVecMemoryStorage` directly. Does not shell out to the `memory` CLI. Does not depend on the MCP server process being alive.
6. **Incremental mode (default):**
   - Diffs `HEAD~1..HEAD` in `$BASE/<role>/` scoped to `Memory/` using `git diff --name-status HEAD~1 HEAD -- Memory/`.
   - Classifies files as Added (A), Modified (M), or Deleted (D).
   - For Modified and Deleted files: calls `storage.delete_by_tag("file:<relative-path>")` before any re-ingestion.
   - For Added and Modified files: reads file contents, creates a `Memory` object, calls `storage.store(memory)`.
   - If no files changed (diff is empty), exits 0 with no database operations.
7. **Rebuild mode (`--rebuild`):**
   - Calls `storage.delete_by_tag("role:<role>")` to clear all entries for this Role.
   - Walks all files under `$BASE/<role>/Memory/` recursively.
   - Ingests each file as a `Memory` object.
8. Every `Memory` object stored must have exactly these two mandatory tags: `role:<role>` and `file:<relative-path-from-role-root>`.
9. `memory_type` is always `"observation"`. No other memory type is used.
10. Files are stored as single entries — no chunking. One file = one `Memory` object. Content is the full file text.
11. `content_hash` is generated via `mcp_memory_service.utils.hashing.generate_content_hash(content)`.
12. Storage connection is always closed after the operation completes, including on error.
13. The initial commit edge case: when `HEAD~1` does not exist (first commit in the repo), incremental mode must fall back to treating all `Memory/` files as Added.

### Soft constraints

- Log a summary to stdout: files processed, entries added, entries deleted.
- Operation should complete in under 10 seconds for a `Memory/` directory with ≤100 files.

---

## Proposal format

### 1. Overview
How the command bridges git history, the filesystem, and the mcp-memory database.

### 2. Storage initialization
How `SqliteVecMemoryStorage` is constructed and initialized. Which constructor arguments are required.

### 3. Incremental diff logic
The exact `git diff` command used. How the output is parsed into Added/Modified/Deleted sets. How the first-commit edge case is handled.

### 4. Memory object construction
The exact fields set on each `Memory` object: `content`, `content_hash`, `tags`, `memory_type`, `metadata`.

### 5. Rebuild logic
How `--rebuild` clears and re-ingests. Why `delete_by_tag("role:<role>")` is used rather than a full database drop.

### 6. Error handling
What happens if the database path does not exist, if `delete_by_tag` fails, if a file cannot be read.

### 7. Self-check table
See Static Evaluation Metrics.

---

## Static evaluation metrics

| ID | Name | Pass condition |
|---|---|---|
| M-01 | No MCP server dependency | Command works when the mcp-memory MCP server process is not running |
| M-02 | Mandatory tags | Every stored entry has exactly `role:<role>` and `file:<path>` tags, no more as mandatory |
| M-03 | Delete before reingest | Modified files have their old entries deleted before new entries are stored |
| M-04 | No chunking | Each file produces exactly one `Memory` object regardless of file length |
| M-05 | Empty diff no-op | When no `Memory/` files changed, zero database operations are performed and command exits 0 |
| M-06 | Rebuild clears role | `--rebuild` deletes all entries tagged `role:<role>` before re-ingesting |
| M-07 | Connection closed | `storage.close()` is called in all exit paths including exceptions |
| M-08 | First-commit safety | Command does not error when `HEAD~1` does not exist; treats all Memory/ files as Added |
| M-09 | DB path required | Command exits with a clear error (not a stack trace) when `MCP_MEMORY_DB_PATH` is unset after sourcing `$BASE/.env` |
| M-10 | Env auto-sourced | Command sources `$BASE/.env` before reading any environment variables; direct invocation works without the caller pre-sourcing the file |
