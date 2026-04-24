# SDD Scenarios: `masks index` — mcp-memory Incremental Indexer

**Companion spec:** `docs/specs/masks-index/spec.md`  
**Date:** 2026-04-23

---

## Use Cases

### 1. Single Memory file added during a session

A session ends, and the post-commit hook detects that `work/Memory/People/alice-chen.md` was added. The hook calls `masks index work`. This is a normal incremental run.

Questions the proposal must answer:
- Does the command connect to `SqliteVecMemoryStorage` using `MCP_MEMORY_DB_PATH` from the environment?
- Does it diff `HEAD~1..HEAD` in `$BASE/work/` scoped to `Memory/` to find the added file?
- Does it create a `Memory` object with `role:work` and `file:Memory/People/alice-chen.md` as tags?
- Does it call `storage.store(memory)` exactly once for this file?
- Does it close the storage connection after completion?
- Does it output a summary line (e.g., "1 added, 0 deleted, 0 skipped")?

Metric cross-references: M-01, M-02, M-04, M-07

---

### 2. Memory file modified — old entry must be evicted before re-ingestion

A session modifies `work/Memory/Projects/summit-2026.md`. The existing database entry for this file is stale and must be removed before the new content is stored.

Questions the proposal must answer:
- Does the command call `storage.delete_by_tag("file:Memory/Projects/summit-2026.md")` before calling `storage.store()`?
- Would a proposal that only stores the new entry (without deleting the old) fail this case, given that content hash deduplication does not catch updated content?
- Is the sequence delete-then-store, not store-then-delete?

Metric cross-references: M-03

---

### 3. Memory file deleted — entry evicted, nothing stored

A session deletes `work/Memory/People/former-colleague.md`. The database has an existing entry for this file.

Questions the proposal must answer:
- Does the command detect the deletion via `git diff --name-status HEAD~1 HEAD -- Memory/` with the `awk '/^D/'` pattern?
- Does it call `storage.delete_by_tag("file:Memory/People/former-colleague.md")`?
- Does it not attempt to read or store a `Memory` object for the deleted file?
- Is the exit clean even though the file no longer exists on disk?

Metric cross-references: M-03

---

### 4. First commit in the repo — no `HEAD~1`

A new Role directory has its very first commit (initial commit). `post-commit.sh` fires and calls `masks index consulting`. The `HEAD~1..HEAD` diff command fails because `HEAD~1` does not exist.

Questions the proposal must answer:
- Does `masks index` detect that `HEAD~1` does not exist and fall back to treating all files in `Memory/` as Added?
- Does it ingest all Memory files in the directory on this fallback path?
- Does it exit 0 without producing a shell error about the missing `HEAD~1`?

Metric cross-references: M-08

---

### 5. No Memory files changed — diff is empty

A session end produces a commit that only changes task folder files and `CONTEXT.md` — no files under `Memory/`. The `post-commit.sh` guard exits early for this case, but `masks index` is also called directly by a user curious about the state.

Questions the proposal must answer:
- When the diff is empty (no Added, Modified, or Deleted Memory files), does the command exit 0 with no database operations?
- Are `storage.store()` and `storage.delete_by_tag()` never called in this case?
- Is the connection to the database still opened and closed, or skipped entirely? (Either is acceptable — the proposal must define which.)

Metric cross-references: M-05

---

### 6. `--rebuild` on an existing Role

A user's mcp-memory database was corrupted or lost. They run `masks index work --rebuild` to regenerate all entries from the filesystem.

Questions the proposal must answer:
- Does the command call `storage.delete_by_tag("role:work")` first, removing all existing entries for this Role?
- Does it then walk all files under `$BASE/work/Memory/` recursively?
- Does it ingest each file as a single `Memory` object with `role:work` and `file:<relative-path>` tags?
- Does it not affect entries for other Roles (e.g., `role:personal`)?

Metric cross-references: M-06

---

### 7. `MCP_MEMORY_DB_PATH` is not set

A user runs `masks index work` on a machine where `$BASE/.env` does not set `MCP_MEMORY_DB_PATH` — perhaps the `.env` file was just created from `.env.example` and not yet filled in.

Questions the proposal must answer:
- Does the command exit with a clear, human-readable error message (not a Python stack trace) explaining that `MCP_MEMORY_DB_PATH` is unset?
- What is the exit code — non-zero?
- Does it avoid creating or modifying any file before detecting the missing configuration?

Metric cross-references: M-09

---

### 8. Storage connection closed after an exception

During a `masks index work` run, `storage.store()` raises an exception (e.g., disk full, database locked by another process).

Questions the proposal must answer:
- Does the proposal use `try/finally` or a context manager to ensure `storage.close()` is called even when an exception occurs?
- Does the command exit with a non-zero code and an informative error message?
- Is the database left in a consistent state (no half-written entries from the failed operation)?

Metric cross-references: M-07

---

## Stress Tests

**T1 No dependency on the mcp-memory MCP server process.**  
`masks index work` completes successfully on a machine where the mcp-memory MCP server process is not running.  
Pass: the command uses `SqliteVecMemoryStorage` directly via the Python library; it does not shell out to `memory` CLI or require a live server.

**T2 Every stored entry has exactly the two mandatory tags.**  
Every `Memory` object stored by the command has `role:<role>` and `file:<relative-path>` in its tags. No mandatory tag is missing; the proposal does not omit either.  
Pass: inspection of stored entries shows both tags present on every object; entries without both tags fail this test.

**T3 Modified files have old entries deleted before new entries stored.**  
For a file appearing in the Modified set, `delete_by_tag("file:<path>")` is called before `store()` is called for that same file in the same run.  
Pass: the implementation processes Modified files in delete-then-store order; store-first implementations fail.

**T4 Each file produces exactly one `Memory` object.**  
Regardless of file length or content, every Memory file is stored as a single entry — no chunking, no splitting.  
Pass: after indexing a 5,000-word Memory file, the database contains exactly one entry for that file path.

**T5 Empty diff produces zero database operations.**  
When `HEAD~1..HEAD` shows no changes in `Memory/`, the command performs no calls to `storage.store()` or `storage.delete_by_tag()`.  
Pass: a run on a commit with only non-Memory changes produces a database with identical state before and after.

**T6 `--rebuild` clears only the specified Role's entries.**  
`masks index work --rebuild` deletes entries tagged `role:work` but leaves entries tagged `role:personal` untouched.  
Pass: after a work rebuild, personal entries are still present and queryable in the database.

**T7 Storage connection is closed in all exit paths.**  
`storage.close()` is called whether the command exits normally, exits on an error, or encounters an exception mid-run.  
Pass: a proposal that omits `close()` in the exception path fails this test; `try/finally` or context manager usage is required.

**T8 First-commit edge case handled without error.**  
`masks index <role>` on a repo with only one commit (no `HEAD~1`) does not produce a git error; it falls back to treating all Memory files as Added and exits 0.  
Pass: running on a freshly initialized Role repo with one Memory file ingests that file and exits 0.

**T9 Missing `MCP_MEMORY_DB_PATH` produces a readable error, not a stack trace.**  
When `MCP_MEMORY_DB_PATH` is unset, the command's error output is a plain-language sentence, not a Python exception traceback.  
Pass: the error output does not contain `Traceback`, `File "`, or `Error:` from an uncaught exception.

---

## Anti-Pattern Regression Signals

**Modified file stored without deleting old entry.** When a Memory file is updated, the new content is stored but the old entry (different content hash) is not removed. Symptom: semantic search returns both the old and new version of the same file; search results are duplicated and contradictory. Indicates: Modified files processed only via `store()`, with no preceding `delete_by_tag()`. Maps to: M-03.

**Files chunked into multiple database entries.** The proposal splits Memory files at paragraph or section boundaries, creating multiple entries per file. Symptom: `delete_by_tag("file:<path>")` only removes some entries for the file, leaving stale chunks after updates. The "one file = one entry" invariant breaks. Indicates: chunking logic imported from a document pipeline and applied to Memory files. Maps to: M-04.

**MCP server process required.** The command uses the `memory` CLI or HTTP API instead of the `SqliteVecMemoryStorage` Python library directly. Symptom: `masks index` fails silently when the mcp-memory server is not running; post-commit hook exits non-zero and confuses users. Indicates: architectural misunderstanding of the spec's isolation requirement. Maps to: M-01.

**Connection not closed after exception.** An exception during `store()` leaves the SQLite connection open. Symptom: subsequent runs fail with "database is locked" errors; the lock persists until the process is killed. Indicates: `storage.close()` is only in the happy-path branch, not in a `finally` block. Maps to: M-07.

**`--rebuild` drops the entire database, not just the Role's entries.** The command uses `DELETE FROM memories` or equivalent instead of `delete_by_tag("role:<role>")`. Symptom: rebuilding the work Role destroys all personal Memory entries from the shared database. Indicates: implementer misread the role-scoped delete requirement. Maps to: M-06.
