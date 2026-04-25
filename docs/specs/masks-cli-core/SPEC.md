# SDD Spec: `masks` CLI — Core Commands

**Context:** See `docs/spec.md` for full system design. This spec covers the infrastructure commands of the `masks` CLI: `setup`, `add-role`, `sync`, `status`, and `doctor`, plus the thin CLI entrypoint for `reference-refresh`. The heartbeat runner (`run`), indexer (`index`), and reflection (`reflect`) are covered in separate specs.

**Deliverables:** `cli/pyproject.toml`, `cli/masks/__init__.py`, `cli/masks/setup.py`, `cli/masks/role.py`, `cli/masks/sync.py`, `cli/masks/status.py`, `cli/masks/doctor.py`, `cli/masks/reference_refresh_cmd.py`.

---

## Requirements

### Hard constraints

1. The package is managed by `uv`. It must be installable via `uv tool install` from `pirandello/cli/` and invocable as `masks <command>` or `uvx masks <command>`.
2. All commands read the base directory from the `MASKS_BASE` environment variable, falling back to `~/Desktop`. A `--base PATH` flag on `masks setup` overrides and persists the value to `$BASE/.env` as `MASKS_BASE`.
3. **`masks setup [--base PATH] [--role-env|--no-role-env]`** must:
   - Create `$BASE/personal/` and `$BASE/work/` if they do not exist.
   - Create `Memory/`, `Reference/`, `Archive/` subdirectories in each Role, each containing an empty `INDEX.md`.
   - Deploy hook scripts (`start.sh`, `end.sh`, `post-commit.sh`) and guard scripts from the bundled package data (`masks/_data/hooks/`, `masks/_data/guards/`) to `~/.pirandello/hooks/` and `~/.pirandello/guards/` respectively. These are the stable paths that role hook configuration files reference.
   - Copy `AGENTS.md` from bundled package data to `$BASE/AGENTS.md` and to each Role directory.
   - Copy `.env.example` from bundled package data to `$BASE/.env` — only if the target does not already exist.
   - Role `.env` files are optional:
     - In default `--no-role-env` mode, do not create `$BASE/personal/.env` or `$BASE/work/.env`.
     - In `--role-env` mode, copy `.env.example` to role `.env` files if absent.
   - Seed sensible defaults into `.env` files without overwriting existing non-empty values:
     - `$BASE/.env`: `MASKS_BASE=$BASE`, `MCP_MEMORY_DB_PATH=~/.pirandello/memory.db`, `GWS_ACCOUNT_WORK=work`, `GWS_ACCOUNT_PERSONAL=personal`
     - When role `.env` files exist (`--role-env`): role-local defaults (`MASKS_BASE`, plus role account label for personal/work)
   - Copy `.gitignore` template from bundled package data to each Role directory — only if not already present.
   - Copy `OODA.md` template from bundled package data to each Role directory — only if not already present.
   - Run `git init` in each Role directory if not already a git repo.
   - Install hooks (start, end, post-commit) to each Role directory, pointing `.cursor/hooks.json` and the git post-commit hook at the deployed `~/.pirandello/hooks/` scripts.
   - **When any copy operation targets a file that already exists, create a timestamped backup (`<filename>.bak.<YYYYMMDD_HHMMSS>`) before overwriting.** This applies to `AGENTS.md` and hook scripts; it does not apply to new-only files (`.env`, `.gitignore`, `OODA.md`) which are only copied when absent.
   - Be idempotent: running twice on a fully set-up machine must produce no errors. Re-running does update hook scripts and `AGENTS.md` in-place (creating backups of the previous versions).
4. **`masks add-role <name> [--remote URL] [--interactive] [--role-env|--no-role-env]`** must:
   - Create `$BASE/<name>/` directory.
   - Create `Memory/`, `Reference/`, `Archive/` with `INDEX.md` in each.
   - In `--role-env` mode (or when `--interactive` is used), copy `.env.example` from bundled package data to `$BASE/<name>/.env` (if not exists); in `--no-role-env` mode without interactive, role `.env` is optional and may be absent.
   - When role `.env` exists, seed sensible defaults into `$BASE/<name>/.env` without overwriting existing non-empty values (at minimum `MASKS_BASE=$BASE`).
   - Copy `OODA.md` template from bundled package data to `$BASE/<name>/OODA.md` (if not exists).
   - Copy `AGENTS.md` from bundled package data to `$BASE/<name>/AGENTS.md` (with backup if exists).
   - Run `git init` in `$BASE/<name>/` if not already a git repo.
   - Install hooks to the new Role directory, pointing at `~/.pirandello/hooks/` (assumed already deployed by `masks setup`).
   - If `--remote URL` is provided, wire it as the git remote (`origin`).
   - If `--interactive`, invoke the `add-role` skill for conversational credential and signal source setup.
5. **`masks sync [role]`** must: for each Role (or the specified Role), run `git pull --ff-only` then `git push`. Roles with no remote configured must be skipped with a warning, not an error.
6. **`masks status`** must: for each Role directory under `$BASE`, print: Role name, last session commit timestamp (from `git log -1 --format='%ci'`), last `OODA_OK` timestamp (last matching line in `.ooda.log`), last git push timestamp (from `git log -1 --format='%ci' origin/main` or equivalent), and any guard failures logged since the last OODA_OK.
7. **`masks doctor`** must check each of the following and print pass/fail for each:
   - `$BASE/AGENTS.md` exists as a regular file (not a symlink) and is readable.
   - Environment config is available for each Role via either:
     - a non-empty `$BASE/.env`, or
     - a non-empty `[role]/.env` (for role-local overrides).
     Role `.env` is optional when base `.env` is populated.
   - Each Role's git remote is reachable (if configured): `git ls-remote` returns 0.
   - mcp-memory server is responding: `MCP_MEMORY_DB_PATH` is set and the file exists.
   - Each Role's `OODA.md` is parseable by the same agenda parser used by `masks run`: at least one numbered skill name can be extracted from the `### Observe`, `### Orient`, or `### Act` sections. A file that exists but yields zero extractable skills is flagged as a failure.
   - Each Role's pre-flight guard scripts (deployed to `~/.pirandello/guards/`) are executable.
8. **`masks reference-refresh [--role ROLE] [--non-interactive] [--dry-run]`** must:
   - Resolve base via the same `MASKS_BASE` logic as all other commands.
   - Resolve target role from `--role` when provided; otherwise infer role from current working directory under `$BASE` (first path segment under base). If role inference fails, exit non-zero with a clear message requiring `--role`.
   - Validate that the target Role directory exists and `Reference/INDEX.md` exists before invoking skill execution.
   - Invoke the `mask-reference-refresh` skill through the configured LLM CLI (`claude -p ...`) with cwd set to the target role directory.
   - Set `PIRANDELLO_NONINTERACTIVE=1` when `--non-interactive` is passed.
   - Set `PIRANDELLO_REFERENCE_REFRESH_DRY_RUN=1` and instruct no writes when `--dry-run` is passed.
   - Exit with the delegated process exit code and perform no direct git operations itself.

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
For each command (`setup`, `add-role`, `sync`, `status`, `doctor`, `reference-refresh`): the function signature, the ordered list of operations it performs, and any significant logic decisions (e.g., how idempotency is checked in `setup`).

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
| M-02 | setup idempotent | Running `masks setup` twice on an initialized system exits 0 without error; re-runnable files (AGENTS.md, hooks) are updated with backups; new-only files (.env, .gitignore, OODA.md) are left untouched except for filling missing default `.env` values |
| M-03 | setup creates all structure | After first run, all required dirs, INDEX.md files, copied AGENTS.md, hook scripts in `~/.pirandello/hooks/`, and role hook config files exist; no symlinks are created; role `.env` files are created only in `--role-env` mode |
| M-04 | add-role complete | After `masks add-role foo`, `$BASE/foo/` contains Memory/, Reference/, Archive/, each with INDEX.md, plus `.gitignore`, `OODA.md`, `AGENTS.md`, and installed hooks pointing at `~/.pirandello/hooks/`; role `.env` exists only in `--role-env` mode (or interactive mode) and is seeded with defaults when present |
| M-05 | sync skips remoteless roles | `masks sync` on a Role with no git remote prints a warning and exits 0 (does not error) |
| M-06 | doctor structured output | `masks doctor` prints a clearly labelled pass/fail/warn line for each of the 7 checks; checks 1–6 are blocking (non-zero exit on failure); check 7 (`always_loaded_budget`) is warn-only and never drives a non-zero exit; the OODA.md check passes only when the agenda parser can extract at least one skill name; the role_env check passes when base `.env` is non-empty or each role has a non-empty `.env` |
| M-07 | doctor non-zero on failure | `masks doctor` exits non-zero if any check fails |
| M-08 | Base path resolution | All commands resolve base from `MASKS_BASE` env var, then `~/Desktop`, never hardcode a path |
| M-09 | Hooks deployed to user dir | After `masks setup`, `~/.pirandello/hooks/` contains start.sh, end.sh, post-commit.sh; `~/.pirandello/guards/` contains all guard scripts; all are executable; role `.cursor/hooks.json` references these paths |
| M-10 | Copy-with-backup | When `masks setup` overwrites a file that already exists (AGENTS.md, hook scripts), a backup named `<file>.bak.<YYYYMMDD_HHMMSS>` is created in the same directory before the new version is written |
| M-11 | Framework root from package | `masks.paths.resolve_framework_root()` returns the `_data/` directory bundled inside the installed package; it does not walk the filesystem or hardcode `~/Code/pirandello`; setting `PIRANDELLO_ROOT` overrides |
| M-12 | reference-refresh entrypoint | `masks reference-refresh` resolves a role via `--role` or workspace inference, validates `Reference/INDEX.md`, supports `--non-interactive` and `--dry-run`, delegates to skill execution, and performs no direct git operations |
