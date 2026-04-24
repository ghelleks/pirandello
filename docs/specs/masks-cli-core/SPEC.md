# SDD Spec: `masks` CLI — Core Commands

**Context:** See `docs/spec.md` for full system design. This spec covers the infrastructure commands of the `masks` CLI: `setup`, `add-role`, `sync`, `status`, and `doctor`. The heartbeat runner (`run`), indexer (`index`), and reflection (`reflect`) are covered in separate specs.

**Deliverables:** `cli/pyproject.toml`, `cli/masks/__init__.py`, `cli/masks/setup.py`, `cli/masks/role.py`, `cli/masks/sync.py`, `cli/masks/status.py`, `cli/masks/doctor.py`.

---

## Requirements

### Hard constraints

1. The package is managed by `uv`. It must be installable via `uv tool install` from `pirandello/cli/` and invocable as `masks <command>` or `uvx masks <command>`.
2. All commands read the base directory from the `MASKS_BASE` environment variable, falling back to `~/Desktop`. A `--base PATH` flag on `masks setup` overrides and persists the value to `$BASE/.env` as `MASKS_BASE`.
3. **`masks setup [--base PATH]`** must:
   - Create `$BASE/personal/` and `$BASE/work/` if they do not exist.
   - Create `Memory/`, `Reference/`, `Archive/` subdirectories in each Role, each containing an empty `INDEX.md`.
   - Symlink `$BASE/AGENTS.md` → `~/Code/pirandello/AGENTS.md`.
   - Copy `pirandello/.env.example` to `$BASE/.env`, `$BASE/personal/.env`, and `$BASE/work/.env` — only if the target does not already exist.
   - Copy `pirandello/templates/.gitignore` to each Role directory — only if not already present.
   - Copy `pirandello/templates/OODA.md` to each Role directory — only if not already present.
   - Run `git init` in each Role directory if not already a git repo.
   - Install hooks (start, end, post-commit) to each Role directory.
   - Be idempotent: running twice must produce no changes and no errors on a fully set-up machine.
4. **`masks add-role <name> [--remote URL] [--interactive]`** must:
   - Create `$BASE/<name>/` directory.
   - Create `Memory/`, `Reference/`, `Archive/` with `INDEX.md` in each.
   - Copy `.env.example` to `$BASE/<name>/.env` (if not exists) and `.gitignore` template to `$BASE/<name>/.gitignore` (if not exists).
   - Copy `OODA.md` template to `$BASE/<name>/OODA.md` (if not exists).
   - Run `git init` in `$BASE/<name>/` if not already a git repo.
   - Install hooks to the new Role directory.
   - If `--remote URL` is provided, wire it as the git remote (`origin`).
   - If `--interactive`, invoke the `add-role` skill for conversational credential and signal source setup.
5. **`masks sync [role]`** must: for each Role (or the specified Role), run `git pull --ff-only` then `git push`. Roles with no remote configured must be skipped with a warning, not an error.
6. **`masks status`** must: for each Role directory under `$BASE`, print: Role name, last session commit timestamp (from `git log -1 --format='%ci'`), last `OODA_OK` timestamp (last matching line in `.ooda.log`), last git push timestamp (from `git log -1 --format='%ci' origin/main` or equivalent), and any guard failures logged since the last OODA_OK.
7. **`masks doctor`** must check each of the following and print pass/fail for each:
   - `$BASE/AGENTS.md` symlink exists and points to a valid file.
   - Each Role has a `.env` file present.
   - Each Role's git remote is reachable (if configured): `git ls-remote` returns 0.
   - mcp-memory server is responding: `MCP_MEMORY_DB_PATH` is set and the file exists.
   - Each Role's `OODA.md` is parseable by the same agenda parser used by `masks run`: at least one numbered skill name can be extracted from the `### Observe`, `### Orient`, or `### Act` sections. A file that exists but yields zero extractable skills is flagged as a failure.
   - Each Role's pre-flight guard scripts (in `pirandello/guards/`) are executable.

### Soft constraints

- Commands should produce human-readable output with clear success/failure indicators.
- `masks setup` should print a summary of what was created vs. what already existed.
- `masks doctor` output should be structured enough for scripting (consider `--json` flag).

---

## Proposal format

### 1. Overview
Package structure and entry-point wiring. How `uv` manages the package.

### 2. Package layout
Full directory tree of `cli/` with one-line descriptions per file.

### 3. Command implementations
For each command (`setup`, `add-role`, `sync`, `status`, `doctor`): the function signature, the ordered list of operations it performs, and any significant logic decisions (e.g., how idempotency is checked in `setup`).

### 4. Shared utilities
Any shared code (base path resolution, Role enumeration, hook installation) extracted into a common module.

### 5. Open decisions
Anything the design doc does not fully specify that the implementer must decide (e.g., exact format of `masks status` output, whether `masks doctor` supports `--fix`).

### 6. Self-check table
See Static Evaluation Metrics.

---

## Static evaluation metrics

| ID | Name | Pass condition |
|---|---|---|
| M-01 | Package installable | `uv tool install ./cli` succeeds and `masks --help` runs without error |
| M-02 | setup idempotent | Running `masks setup` twice on an initialized system produces no file changes and exits 0 |
| M-03 | setup creates all structure | After first run, all required dirs, INDEX.md files, symlink, and hook files exist |
| M-04 | add-role complete | After `masks add-role foo`, `$BASE/foo/` contains Memory/, Reference/, Archive/, each with INDEX.md, plus .env, .gitignore, OODA.md, and installed hooks |
| M-05 | sync skips remoteless roles | `masks sync` on a Role with no git remote prints a warning and exits 0 (does not error) |
| M-06 | doctor structured output | `masks doctor` prints a clearly labelled pass/fail/warn line for each of the 7 checks; checks 1–6 are blocking (non-zero exit on failure); check 7 (`always_loaded_budget`) is warn-only and never drives a non-zero exit; the OODA.md check passes only when the agenda parser can extract at least one skill name |
| M-07 | doctor non-zero on failure | `masks doctor` exits non-zero if any check fails |
| M-08 | Base path resolution | All commands resolve base from `MASKS_BASE` env var, then `~/Desktop`, never hardcode a path |
