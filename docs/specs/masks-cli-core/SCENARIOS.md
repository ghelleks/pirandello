# SDD Scenarios: `masks` CLI — Core Commands

**Companion spec:** `docs/specs/masks-cli-core/spec.md`  
**Date:** 2026-04-23

---

## Use Cases

### 1. First-time setup on a fresh machine

A user installs the `masks` CLI on a new machine via `uv tool install`. `~/Desktop` exists but has no Role directories, no `.env`, and no `AGENTS.md`. They run `masks setup` for the first time.

Questions the proposal must answer:
- Does the command create `personal/` and `work/` under `~/Desktop`?
- Does it create `Memory/`, `Reference/`, and `Archive/` inside each, each containing an empty `INDEX.md`?
- Does it deploy hook scripts to `~/.pirandello/hooks/` and guard scripts to `~/.pirandello/guards/`, sourced from the bundled package data rather than from any checkout path?
- Does it copy `AGENTS.md` from the bundled package data to `$BASE/AGENTS.md` and to each Role directory?
- Does it copy `.env.example` to `$BASE/.env`?
- In default mode (`--no-role-env`), does it skip creating `personal/.env` and `work/.env`?
- In `--role-env` mode, does it create role `.env` files and seed defaults so they are not empty?
- Does it copy `.gitignore` template to each Role directory?
- Does it copy `OODA.md` template to each Role directory?
- Does it run `git init` in each Role directory?
- Does each Role's `.cursor/hooks.json` reference `~/.pirandello/hooks/start.sh` and `~/.pirandello/hooks/end.sh` — not any path inside a source checkout?

Metric cross-references: M-01, M-02, M-03, M-08, M-09, M-11

---

### 2. Re-running setup on a fully configured machine

A user runs `masks setup` on a machine where Pirandello has been installed for three months. All directories exist, `.env` files are populated with real credentials, `AGENTS.md` copies are in place, and hooks are installed.

Questions the proposal must answer:
- Does the command exit 0 without errors?
- Does it avoid overwriting existing `.env` files (both base and role, when present, and containing real credentials)?
- Does it only fill missing default `.env` keys when blank, without replacing non-empty user values?
- Does it avoid re-copying `.gitignore` and `OODA.md` if they already exist?
- Does it avoid running `git init` again in an existing git repo?
- When it updates `AGENTS.md` and hook scripts, does it create a timestamped `.bak` file before overwriting?
- What does the summary output say — does it clearly distinguish "already exists", "created", and "updated (backup: …)"?

Metric cross-references: M-02, M-03, M-10

---

### 3. Adding a new Role after initial setup

A user has a functioning `personal/` and `work/` Role and now wants to add a consulting engagement. They run `masks add-role consulting --remote git@github.com:user/consulting.git`.

Questions the proposal must answer:
- Does `$BASE/consulting/` get created with `Memory/`, `Reference/`, `Archive/`, each containing an empty `INDEX.md`?
- In default mode (`--no-role-env`), is `$BASE/consulting/.env` not created?
- In `--role-env` (or `--interactive`) mode, is `.env.example` copied to `$BASE/consulting/.env` (only if not already present)?
- When the new Role `.env` exists, is it seeded with sensible defaults (at minimum `MASKS_BASE`) without overwriting non-empty existing values?
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

A user runs `masks doctor` on a fully configured, connected system. All seven checks should pass or warn green: AGENTS.md copy present and readable, environment config is available via base `.env` (role `.env` optional) or non-empty role `.env` files, all configured remotes are reachable, mcp-memory DB path exists and is set, all OODA.md files are valid, all guard scripts in `~/.pirandello/guards/` are executable, and the always-loaded token budget is within threshold.

Questions the proposal must answer:
- Does the command print a clearly labelled pass/warn result for each of the seven checks?
- Does it exit 0?
- Can the output be parsed by a script (or is `--json` provided)?

Metric cross-references: M-06, M-07

---

### 6. `masks doctor` with failures

A user runs `masks doctor`. The mcp-memory DB file is missing, one Role's remote is unreachable (network down), base `.env` is empty and one role has an empty `.env`, and one guard script was accidentally made non-executable. Four of the six blocking checks fail; the always-loaded budget check still runs and reports separately.

Questions the proposal must answer:
- Does the command print a clear FAIL result for each of the four failing checks, naming exactly what failed?
- Does it still run all seven checks even when some fail (not abort on first failure)?
- Does it exit non-zero?
- Is the passing check output still shown alongside the failures?

Metric cross-references: M-06, M-07

---

### 6b. `masks doctor` — always-loaded budget warning

A user's system has been running for several months. `personal/SELF.md` is 490 tokens, `work/ROLE.md` is 480 tokens, and `work/CONTEXT.md` has grown to 620 tokens after a busy quarter. The combined total is 1,590 tokens, exceeding the 1,500-token threshold.

Questions the proposal must answer:
- Does `masks doctor` report the `always_loaded_budget` check as WARN (not FAIL) for the work Role?
- Does the WARN output name the current combined total, the 1,500-token threshold, and the specific overage?
- Does the remediation message tell the user which file to shorten and by approximately how many tokens?
- Does the command still exit 0 (the warn-only check does not drive a non-zero exit)?
- If a different Role is within budget, does that Role show PASS for the same check?

Metric cross-references: M-06, S-08

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

### 9. `masks reference-refresh` from a Role workspace

A user is in `$BASE/work/strategy-review/` and runs `masks reference-refresh` with no `--role`.

Questions the proposal must answer:
- Does the command infer the Role as `work` from the workspace path under `$BASE`?
- Does it validate that `$BASE/work/Reference/INDEX.md` exists before invoking the skill?
- Does it execute the delegated skill with working directory set to `$BASE/work/`?
- Does `--dry-run` avoid writes and produce a plan-only run?
- Does `--non-interactive` set `PIRANDELLO_NONINTERACTIVE=1` for unattended execution?
- If the current directory is outside `$BASE` and `--role` is omitted, does it fail with a clear message requiring `--role`?

Metric cross-references: M-08, M-12

---

## Stress Tests

**T1 Package installs and runs without error.**  
`uv tool install ./cli` completes without error, and `masks --help` prints usage information.  
Pass: both commands exit 0 in a clean environment; `masks` is on `$PATH` and invocable.

**T2 `masks setup` is fully idempotent.**  
Running `masks setup` twice on a fully initialized system produces no file changes: no files created, no files overwritten, no git operations, no errors.  
Pass: a `diff` of all affected directories before and after the second run shows zero changes; exit code is 0.

**T3 `masks setup` creates every required artifact on a fresh machine.**  
After the first run, every item in the spec's `masks setup` requirements list exists: directories, `INDEX.md` files, `AGENTS.md` copies (not symlinks) at `$BASE` and in each Role, hook scripts in `~/.pirandello/hooks/`, guard scripts in `~/.pirandello/guards/`, base `.env` (and role `.env` only in `--role-env` mode), `.gitignore`, `OODA.md`, and `.cursor/hooks.json` pointing at `~/.pirandello/hooks/`.  
Pass: a checklist script enumerating each artifact returns "present" for all items; no item in the checklist is a symlink.

**T4 `masks add-role` creates complete Role structure.**  
After `masks add-role foo`, `$BASE/foo/` contains: `Memory/INDEX.md`, `Reference/INDEX.md`, `Archive/INDEX.md`, `.gitignore`, `OODA.md`, `AGENTS.md`, and `.cursor/hooks.json` referencing `~/.pirandello/hooks/`.  
Pass: every file in this list exists at the correct path; `.cursor/hooks.json` does not reference any path inside a source checkout or development directory; role `.env` is absent in default mode and present with default `MASKS_BASE` in `--role-env`/interactive mode.

**T5 `masks sync` on a remoteless Role is a clean skip, not an error.**  
Running `masks sync` on a single Role with no `origin` remote results in a warning line and exit 0, with no stack trace and no non-zero exit code.  
Pass: exit code is 0; output contains a human-readable warning naming the skipped Role.

**T6 `masks doctor` structured output.**  
Running `masks doctor` produces exactly one clearly labelled pass/fail/warn line per check for all seven checks, regardless of outcome.  
Pass: the output contains six labelled lines (or six JSON objects); no check is silently omitted.

**T7 `masks doctor` exits non-zero on any failure.**  
If one or more doctor checks fail, the command exits with a non-zero exit code.  
Pass: `echo $?` after a doctor run with a known failing check returns non-zero.

**T8 All commands resolve base from `MASKS_BASE` env var.**  
No command hardcodes `~/Desktop` or any other path in its source. When `MASKS_BASE=/custom/base` is set in the environment, all commands operate under `/custom/base`.  
Pass: no literal `~/Desktop` or `$HOME/Desktop` string appears in any command's implementation; all path construction flows through the `MASKS_BASE` resolution logic.

**T9 Framework root always resolves to bundled package data.**  
`masks.paths.resolve_framework_root()` returns the `_data/` directory inside the installed package, not any path derived from walking the filesystem upward or from a hardcoded development path.  
Pass: calling `resolve_framework_root()` on a machine where `~/Code/pirandello` does not exist returns a valid path that contains `hooks/start.sh`; the `PIRANDELLO_ROOT` env var overrides the result when set.

**T10 Backup created when setup is re-run over existing files.**  
Running `masks setup` a second time on a fully configured system, then running it a third time, produces two sets of `.bak.<timestamp>` files for `AGENTS.md` and hook scripts — one per overwrite. `.env`, `.gitignore`, and `OODA.md` are not touched on re-runs.  
Pass: after two re-runs, the directory contains exactly two `.bak.*` files per overwritable file; the originals are intact and readable.

**T11 `masks reference-refresh` supports workspace default and dry-run.**  
Running `masks reference-refresh` from inside a Role subtree infers the Role without requiring `--role`; adding `--dry-run` runs planning mode without mutating files; adding `--non-interactive` sets unattended mode for the delegated skill.
Pass: command exits successfully when role inference succeeds and emits no file mutations under `--dry-run`; command exits non-zero with a clear error when role inference fails and no `--role` is provided.

---

## Anti-Pattern Regression Signals

**`masks setup` overwrites existing `.env` files.** The command copies `.env.example` unconditionally, destroying real credentials. Symptom: after re-running `masks setup`, MCP connections fail because credential values have been replaced with empty strings. Indicates: missing file-existence guard on the `.env.example` copy step. Maps to: M-02, M-03.

**Hook scripts point into the source checkout or development directory.** `.cursor/hooks.json` references an absolute path like `~/Code/pirandello/hooks/start.sh` instead of `~/.pirandello/hooks/start.sh`. Symptom: hooks work for developers who have the repo cloned at that path but silently break for any user who installed the tool without cloning the source. Indicates: `resolve_framework_root()` walked the filesystem and found the development checkout rather than using the bundled `_data/` directory. Maps to: M-09, M-11.

**`AGENTS.md` deployed as a symlink.** `masks setup` creates a symlink at `$BASE/AGENTS.md` pointing to the source checkout instead of copying the file. Symptom: users without the source repo cloned get broken symlinks; the file disappears if the checkout is deleted or moved. Indicates: symlink logic not replaced with copy-with-backup. Maps to: M-03, M-10.

**Re-running setup clobbers modified files without backup.** A user who has customized their `AGENTS.md` or local hook scripts runs `masks setup` after an upgrade; the updated files overwrite their changes without any backup. Symptom: user-customized content is silently lost; no recovery path exists. Indicates: copy-with-backup pattern not applied; unconditional overwrite used instead. Maps to: M-10.

**`masks sync` errors on remoteless Role and aborts.** A Role with no remote causes `masks sync` to fail with a non-zero exit and stop processing remaining Roles. Symptom: roles after the remoteless one are never pulled or pushed. Indicates: missing per-Role error isolation in the sync loop. Maps to: M-05.

**`masks doctor` only checks the first failing condition.** The command exits early on the first failed check rather than running all seven checks. Symptom: users see one failure, fix it, re-run doctor, find another — never get a complete health picture in one run. Indicates: early exit on first non-zero check rather than accumulated results. Maps to: M-06.

**Base path hardcoded to `~/Desktop`.** Commands fail when a user configured a custom base via `--base`. Symptom: `masks status` or `masks sync` runs without error but operates on the wrong directory tree. Indicates: `MASKS_BASE` env var not read, fallback logic not implemented. Maps to: M-08.

**`git init` run in existing repo causes error.** `masks setup` on an already-initialized Role runs `git init` again, which may fail or produce unexpected state in some git versions. Symptom: `masks setup` exits non-zero when re-run on an initialized system. Indicates: missing check for existing `.git/` before `git init`. Maps to: M-02.

**`masks reference-refresh` cannot run unless `--role` is always provided.** The command ignores workspace context and fails even when run from inside a Role tree. Symptom: users in `$BASE/work/...` must pass redundant flags and unattended scripts become brittle. Indicates: missing role inference logic from cwd under `$BASE`. Maps to: M-12.
