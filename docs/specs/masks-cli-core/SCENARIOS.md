# SDD Scenarios: `masks` CLI — Core Commands

**Companion spec:** `docs/specs/masks-cli-core/spec.md`  
**Date:** 2026-04-23

---

## Use Cases

### 1. First-time setup on a fresh machine

A user has just cloned `pirandello` on a new machine. `~/Desktop` exists but has no Role directories, no `.env`, and no `AGENTS.md` symlink. They run `masks setup` for the first time.

Questions the proposal must answer:
- Does the command create `personal/` and `work/` under `~/Desktop`?
- Does it create `Memory/`, `Reference/`, and `Archive/` inside each, each containing an empty `INDEX.md`?
- Does it create the `$BASE/AGENTS.md` symlink pointing to `~/Code/pirandello/AGENTS.md`?
- Does it copy `.env.example` to `$BASE/.env`, `personal/.env`, and `work/.env`?
- Does it copy `.gitignore` template to each Role directory?
- Does it copy `OODA.md` template to each Role directory?
- Does it run `git init` in each Role directory?
- Does it install hooks (start, end, post-commit) to each Role directory?

Metric cross-references: M-01, M-02, M-03, M-08

---

### 2. Re-running setup on a fully configured machine

A user runs `masks setup` on a machine where Pirandello has been installed for three months. All directories exist, `.env` files are populated with real credentials, the symlink is in place, and hooks are installed.

Questions the proposal must answer:
- Does the command exit 0 with no file changes and no errors?
- Does it avoid overwriting existing `.env` files (which contain real credentials)?
- Does it avoid re-copying `.gitignore` and `OODA.md` if they already exist?
- Does it avoid running `git init` again in an existing git repo?
- What does the summary output say — does it clearly distinguish "already exists" from "created"?

Metric cross-references: M-02, M-03

---

### 3. Adding a new Role after initial setup

A user has a functioning `personal/` and `work/` Role and now wants to add a consulting engagement. They run `masks add-role consulting --remote git@github.com:user/consulting.git`.

Questions the proposal must answer:
- Does `$BASE/consulting/` get created with `Memory/`, `Reference/`, `Archive/`, each containing an empty `INDEX.md`?
- Is `.env.example` copied to `$BASE/consulting/.env` (only if not already present)?
- Is `.gitignore` template copied to `$BASE/consulting/.gitignore` (only if not already present)?
- Is `OODA.md` template copied to `$BASE/consulting/OODA.md` (only if not already present)?
- Is `git init` run in the new directory?
- Is the remote wired as `origin`?
- Are hooks installed to the new Role directory?

Metric cross-references: M-04

---

### 4. `masks sync` with one remoteless Role

A user runs `masks sync` across three Roles: `personal` (has remote), `work` (has remote), and `local-notes` (no remote configured). The first two sync normally; the third has no `origin` remote.

Questions the proposal must answer:
- Does `masks sync` pull and push for `personal` and `work` without error?
- Does it emit a warning for `local-notes` (not an error) and continue without aborting?
- Does `masks sync` exit 0 even though one Role has no remote?
- Is the remoteless Role explicitly named in the warning output so the user knows which one was skipped?

Metric cross-references: M-05

---

### 5. `masks doctor` on a healthy system

A user runs `masks doctor` on a fully configured, connected system. All six checks should pass: AGENTS.md symlink valid, each Role has a `.env`, all configured remotes are reachable, mcp-memory DB path exists and is set, all OODA.md files are valid, all guard scripts are executable.

Questions the proposal must answer:
- Does the command print a clearly labelled pass result for each of the six checks?
- Does it exit 0?
- Can the output be parsed by a script (or is `--json` provided)?

Metric cross-references: M-06, M-07

---

### 6. `masks doctor` with failures

A user runs `masks doctor`. The mcp-memory DB file is missing, one Role's remote is unreachable (network down), and one guard script was accidentally made non-executable. Three of the six checks fail.

Questions the proposal must answer:
- Does the command print a clear FAIL result for each of the three failing checks, naming exactly what failed?
- Does it still run all six checks even when some fail (not abort on first failure)?
- Does it exit non-zero?
- Is the passing check output still shown alongside the failures?

Metric cross-references: M-06, M-07

---

### 7. `masks setup --base /custom/path`

A user doesn't want to use `~/Desktop` as base. They run `masks setup --base ~/Roles`.

Questions the proposal must answer:
- Does the command create the directory structure under `~/Roles/` rather than `~/Desktop/`?
- Does it write `MASKS_BASE=/Users/user/Roles` to `$BASE/.env` so subsequent commands pick it up without repeating the flag?
- Does `masks setup` run idempotently on `/custom/path` when re-run?

Metric cross-references: M-08

---

### 8. `masks status` output for an active system

A user runs `masks status` on a system with three Roles. Each has had recent activity. The user wants to see a quick health summary without reading log files manually.

Questions the proposal must answer:
- For each Role, is the Role name, last session commit timestamp, last OODA_OK timestamp, and last push timestamp shown?
- Are any guard failures since the last OODA_OK surfaced in the output?
- If a Role has never had an OODA run (no `.ooda.log`), does the command handle this gracefully?

Metric cross-references: M-08 (base path resolution required for status to find all Roles)

---

## Stress Tests

**T1 Package installs and runs without error.**  
`uv tool install ./cli` completes without error, and `masks --help` prints usage information.  
Pass: both commands exit 0 in a clean environment; `masks` is on `$PATH` and invocable.

**T2 `masks setup` is fully idempotent.**  
Running `masks setup` twice on a fully initialized system produces no file changes: no files created, no files overwritten, no git operations, no errors.  
Pass: a `diff` of all affected directories before and after the second run shows zero changes; exit code is 0.

**T3 `masks setup` creates every required artifact on a fresh machine.**  
After the first run, every item in the spec's `masks setup` requirements list exists: directories, `INDEX.md` files, symlink, hook files, `.env` copies, `.gitignore`, `OODA.md`.  
Pass: a checklist script enumerating each artifact returns "present" for all items.

**T4 `masks add-role` creates complete Role structure.**  
After `masks add-role foo`, `$BASE/foo/` contains: `Memory/INDEX.md`, `Reference/INDEX.md`, `Archive/INDEX.md`, `.env`, `.gitignore`, `OODA.md`, and installed hook files.  
Pass: every file in this list exists at the correct path.

**T5 `masks sync` on a remoteless Role is a clean skip, not an error.**  
Running `masks sync` on a single Role with no `origin` remote results in a warning line and exit 0, with no stack trace and no non-zero exit code.  
Pass: exit code is 0; output contains a human-readable warning naming the skipped Role.

**T6 `masks doctor` structured output.**  
Running `masks doctor` produces exactly one clearly labelled pass/fail line per check for all six checks, regardless of whether they pass or fail.  
Pass: the output contains six labelled lines (or six JSON objects); no check is silently omitted.

**T7 `masks doctor` exits non-zero on any failure.**  
If one or more doctor checks fail, the command exits with a non-zero exit code.  
Pass: `echo $?` after a doctor run with a known failing check returns non-zero.

**T8 All commands resolve base from `MASKS_BASE` env var.**  
No command hardcodes `~/Desktop` or any other path in its source. When `MASKS_BASE=/custom/base` is set in the environment, all commands operate under `/custom/base`.  
Pass: no literal `~/Desktop` or `$HOME/Desktop` string appears in any command's implementation; all path construction flows through the `MASKS_BASE` resolution logic.

---

## Anti-Pattern Regression Signals

**`masks setup` overwrites existing `.env` files.** The command copies `.env.example` unconditionally, destroying real credentials. Symptom: after re-running `masks setup`, MCP connections fail because credential values have been replaced with empty strings. Indicates: missing file-existence guard on the `.env.example` copy step. Maps to: M-02, M-03.

**`masks sync` errors on remoteless Role and aborts.** A Role with no remote causes `masks sync` to fail with a non-zero exit and stop processing remaining Roles. Symptom: roles after the remoteless one are never pulled or pushed. Indicates: missing per-Role error isolation in the sync loop. Maps to: M-05.

**`masks doctor` only checks the first failing condition.** The command exits early on the first failed check rather than running all six checks. Symptom: users see one failure, fix it, re-run doctor, find another — never get a complete health picture in one run. Indicates: early exit on first non-zero check rather than accumulated results. Maps to: M-06.

**Base path hardcoded to `~/Desktop`.** Commands fail when a user configured a custom base via `--base`. Symptom: `masks status` or `masks sync` runs without error but operates on the wrong directory tree. Indicates: `MASKS_BASE` env var not read, fallback logic not implemented. Maps to: M-08.

**`git init` run in existing repo causes error.** `masks setup` on an already-initialized Role runs `git init` again, which may fail or produce unexpected state in some git versions. Symptom: `masks setup` exits non-zero when re-run on an initialized system. Indicates: missing check for existing `.git/` before `git init`. Maps to: M-02.
