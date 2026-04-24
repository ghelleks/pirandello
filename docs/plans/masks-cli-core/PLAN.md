# Proposal: `masks` CLI — Core Commands (`masks-cli-core`)

**Status:** proposal  
**Date:** 2026-04-23  
**Unit spec:** `docs/specs/masks-cli-core/SPEC.md`  
**Authoritative design:** `docs/design.md`

---

## 1. Overview

The `masks` core CLI is a single Python package under `cli/`, built and installed with **`uv`** (`[project.scripts]` entry point `masks = "masks.cli:app"` using **Typer**). Users install with `uv tool install ./cli` (or `uvx masks` from a published package) and invoke `masks <subcommand>`.

**Base directory** resolution is centralized: every subcommand calls `resolve_base_path()` which returns, in order:

1. Absolute path from environment variable `MASKS_BASE` (if set and non-empty), or  
2. If `$BASE/.env` exists and defines `MASKS_BASE`, that value (after loading with a minimal parser that does not require python-dotenv as a hard dependency—implement with stdlib line scan for `MASKS_BASE=`), or  
3. `Path.home() / "Desktop"` (constructed only via `Path.home()`; **no** `~/Desktop` or `$HOME/Desktop` string literals in source).

`masks setup --base PATH` resolves `PATH` to an absolute path, ensures `$BASE` exists, then **merges** `MASKS_BASE=<absolute>` into `$BASE/.env` (create file from `.env.example` only when missing; if `.env` already exists, upsert the `MASKS_BASE` line without touching other keys). Subsequent commands read the persisted value through step 2 above when the env var is unset.

**Framework root** (Pirandello repo containing `AGENTS.md`, `hooks/`, `templates/`, `guards/`, `.env.example`) resolves via `resolve_framework_root()`:

1. `PIRANDELLO_ROOT` environment variable if set.  
2. Walk upward from `Path(__file__).resolve().parent` until a directory contains both `AGENTS.md` and `templates/OODA.md` (supports editable installs where `cli/masks/` lives inside the repo).  
3. Fallback: `Path.home() / "Code" / "pirandello"`.

The symlink target for `$BASE/AGENTS.md` is `resolve_framework_root() / "AGENTS.md"` (absolute path stored in the symlink).

**Idempotency (top-level idempotent-commands requirement):** `setup`, `sync`, `status`, and `doctor` are safe to repeat. `add-role` treats an **already-initialized** role directory (existing `Memory/`, `Reference/`, `Archive/` with `INDEX.md`) as success: prints a short “already present” summary and exits **0** without overwriting templates or re-initing git.

---

## 2. Package layout

```
cli/
├── pyproject.toml              # project metadata, deps (typer>=0.12, tiktoken), script entrypoint masks
├── README.md                   # install: uv tool install ./cli; link to pirandello README
└── masks/
    ├── __init__.py             # package version string
    ├── __main__.py             # python -m masks → typer app
    ├── cli.py                  # Typer app: subcommands setup, add-role, sync, status, doctor
    ├── paths.py                # resolve_base_path, resolve_framework_root, ensure_env_key
    ├── roles.py                # iter_role_dirs, is_role_layout, role_display_name
    ├── ooda_parse.py           # extract_agenda_skills(OODA.md path) → list[str]; shared with masks run
    ├── hooks.py                # install_hooks_for_role(role_path, framework_root)
    ├── setup_cmd.py            # implementation of masks setup (module name avoids shadowing stdlib setup)
    ├── role_cmd.py             # masks add-role
    ├── sync_cmd.py             # masks sync
    ├── status_cmd.py           # masks status
    ├── token_budget.py         # tiktoken cl100k_base counts; shared with start.sh helper (S-08)
    └── doctor_cmd.py           # masks doctor (+ JSON output path)
```

**Note:** The unit spec names `setup.py` / `role.py` as deliverables; to avoid Python import confusion with setuptools and to keep names unambiguous, the implementation uses `setup_cmd.py` and `role_cmd.py` as filenames while exposing the same logical modules in documentation. If strict filename parity is required, use `setup.py` **inside** `masks/` only (not at repo root)—acceptable for a package subfolder.

---

## 3. Command implementations

### 3.1 `masks setup [--base PATH]`

**Entry:** `setup_command(ctx, base: Optional[Path])` in `setup_cmd.py`, registered on Typer.

**Ordered operations:**

1. Resolve optional `--base`: if provided, `base_arg = Path(base).expanduser().resolve()`; else `None`.  
2. Determine effective base: if `base_arg`: use it. Else `resolve_base_path()` using env / existing `$BASE/.env` / desktop fallback—but on **first** run `$BASE/.env` may not exist yet; in that case desktop fallback applies.  
3. If `base_arg` was provided: create directory if missing; **upsert** `MASKS_BASE=<absolute base_arg>` into `$BASE/.env` (if `.env` missing, copy from `framework/.env.example` first, then upsert).  
4. Ensure `$BASE/personal` and `$BASE/work` exist (`mkdir -parents`).  
5. For each role name in `("personal", "work")`: call `_ensure_role_scaffold(base / role)` which:  
   - Creates `Memory/`, `Reference/`, `Archive/` if missing.  
   - Creates each `INDEX.md` if missing as a **zero-byte** file (truly empty).  
   - Copies `templates/.gitignore` → `[role]/.gitignore` **only if** target does not exist.  
   - Copies `templates/OODA.md` → `[role]/OODA.md` **only if** target does not exist.  
   - Copies `.env.example` → `[role]/.env` **only if** target does not exist.  
   - Runs `git init` **only if** `[role]/.git` does not exist.  
   - Calls `install_hooks_for_role(...)`.  
6. Ensure `$BASE/.env` from `.env.example` **only if** not present (never overwrite).  
7. Ensure `$BASE/AGENTS.md` is a symlink to `framework_root / "AGENTS.md"`: if `AGENTS.md` exists and is not the correct symlink, remove file/symlink and recreate; if already correct, no-op.  
8. Print human-readable summary lines: `CREATED` vs `EXISTS` for each artifact category (dirs, INDEX files, symlink, env copies, git init skipped, hooks refreshed).

**Idempotency:** No overwrite of `.env`, `.gitignore`, or `OODA.md`. No second `git init`. Symlink corrected only if wrong. Second run yields **only** `EXISTS` lines and exit code **0**.

---

### 3.2 `masks add-role <name> [--remote URL] [--interactive]`

**Entry:** `add_role(name: str, remote: Optional[str], interactive: bool)` in `role_cmd.py`.

**Validation:** `name` must be a single path segment: match `^[a-z0-9][a-z0-9-]*$` (lowercase, hyphenated, no dots) to avoid path traversal and reserved names `personal` / `work`—if user passes `personal` or `work`, exit **2** with a message to use `masks setup`.

**Ordered operations:**

1. `base = resolve_base_path()`.  
2. `role_path = base / name`.  
3. If `role_path` exists **and** `is_role_layout(role_path)` true: print “role already initialized” summary, ensure hooks still installed (repair), exit **0**.  
4. Else if `role_path` exists but incomplete: exit **2** with “path exists but is not empty / not a role”—no destructive merge.  
5. `mkdir role_path`.  
6. Create `Memory/`, `Reference/`, `Archive/` + empty `INDEX.md` in each (same as setup).  
7. Copy `.env.example`, `.gitignore`, `OODA.md` with same existence guards as setup.  
8. `git init` if no `.git`.  
9. `install_hooks_for_role(role_path, framework_root)`.  
10. If `--remote URL`: `git -C role_path remote add origin <URL>` if `origin` missing; if `origin` exists with different URL, exit **2** (do not rewrite silently).  
11. If `--interactive`: invoke **skill runner** (see §5): `subprocess.run` of `MASKS_INTERACTIVE_CMD` if set (split with `shlex.split`), else if `shutil.which("claude")` exists run `claude -p "Run the add-role skill for this Role directory. Collect credentials and signal sources; write them to .env and document them in ROLE.md when complete."` with `cwd=role_path`, else print a single **user-facing** paragraph (no raw paths—use role display name “this role”) instructing the user to open the role in their assistant and request the add-role skill; exit **0**.

---

### 3.3 `masks sync [role]`

**Entry:** `sync_cmd(optional_role: Optional[str])` in `sync_cmd.py`.

**Loop:** Targets = `[optional_role]` if provided (validate directory exists under base), else `iter_role_dirs(base)`.

For each `role_path`:

1. If not a git repo: warn `WARN: <name> is not a git repository; skipping` (should not happen post-setup), continue.  
2. `git remote get-url origin` (or `git config --get remote.origin.url`). If empty / fails: print `WARN: skipping <name>: no git remote configured` to **stderr**, **continue** (no exception, no abort).  
3. Run `git -C role_path pull --ff-only` — on failure print warning but continue to next role (non-fatal per design “fail silently” for optional git; still user-visible warning for sync).  
4. Run `git -C role_path push` — redirect stderr, on failure print warning, continue.

**Exit code:** **0** always if the command completes the loop (matches M-05). Severe misconfiguration (invalid role arg) exits **2**.

---

### 3.4 `masks status`

**Entry:** `status_cmd()` in `status_cmd.py`.

For each `role_path` in `iter_role_dirs(base)`:

1. **Role name:** directory name (user-facing label only—no full paths in default output; optional `--verbose` may show paths for debugging, default off per soft “no paths” guidance).  
2. **Last session commit:** run `git -C role_path log -1 --format=%ci`; if empty repo, display `never`.  
3. **Last OODA_OK:** read `role_path / ".ooda.log"` if exists; scan lines **bottom-up** for first containing `OODA_OK` (substring match per spec “last matching line”); parse ISO timestamp if line format is `OODA_OK [timestamp]` else show raw line timestamp `unknown`. If file missing, `never`.  
4. **Last push / remote sync time:** determine default remote branch: `git -C role_path symbolic-ref refs/remotes/origin/HEAD 2>/dev/null` or try `origin/main` then `origin/master`; run `git -C role_path log -1 --format=%ci <remote_ref>`; if no upstream, `n/a`.  
5. **Guard failures since last OODA_OK:** parse `.ooda.log` from the line **after** the last `OODA_OK` to EOF (or entire file if no OODA_OK): collect lines matching case-insensitive `WARN`, `missing guard`, `not executable`, or `non-zero` in guard summary (concrete patterns aligned with `masks run` log format once implemented). Display condensed: `none` or semicolon-separated snippets (max 3 lines, then `+N more`).

**Output format:** stable columns with fixed headers for scripting, e.g.:

```
ROLE          LAST_COMMIT           LAST_OODA_OK          LAST_REMOTE_HEAD      GUARD_NOTES
personal      2026-04-23 12:01:00   2026-04-23 11:45:00   2026-04-23 10:00:00   none
```

Tab-separated output optional via `--tsv` flag for machines.

---

### 3.5 `masks doctor`

**Entry:** `doctor_cmd(json: bool)` in `doctor_cmd.py`.

**Runs all six blocking checks** in fixed order; accumulates results; **never** early-exit on first failure. A **seventh** line, `always_loaded_budget`, runs after the six and implements the CLI side of **S-08** (aligned with `docs/SPEC.md` and `docs/plans/system/PLAN.md` §6): same token math as `start.sh`, **WARN-only** — it does **not** contribute to M-07 non-zero exit (combined budget is a warned threshold, not a hard failure).

| # | Check ID               | Exit impact | Logic |
|---|------------------------|-------------|-------|
| 1 | `agents_symlink`       | blocking    | `$BASE/AGENTS.md` exists, `is_symlink`, `readlink` resolves to existing file. |
| 2 | `role_env`             | blocking    | Every role dir has `.env` file present (non-empty optional). |
| 3 | `git_remote`           | blocking    | For each role with `origin`, run `git ls-remote origin HEAD` with 5s timeout; skip subcheck if no remote (counts as **pass** with note `no remote`); unreachable = **fail** for that role, aggregate fail if any unreachable. |
| 4 | `mcp_memory_db`        | blocking    | After sourcing `$BASE/.env` via line parser, require `MCP_MEMORY_DB_PATH` set and `Path(path).is_file()`. |
| 5 | `ooda_agenda`          | blocking    | For each role, `skills = extract_agenda_skills(OODA.md)`; **fail** if file missing OR `len(skills)==0`; **pass** if ≥1 skill name. Uses **identical** parser as `masks run` (`ooda_parse.py`). |
| 6 | `guards_executable`    | blocking    | For each skill name returned across all roles’ OODA files (union), check `framework_root / "guards" / f"{skill}.sh"` exists and `os.access(X_OK)`; if a role’s OODA references a skill whose guard is missing, record **fail** `missing guards: …`. If `guards/` directory missing, fail check. |
| 7 | `always_loaded_budget` | **none** (WARN only) | See below. |

#### `always_loaded_budget` (S-08 / combined always-loaded stack)

**Shared implementation:** `token_budget.py` exposes functions used by **`masks doctor`** and by the small Python helper invoked from **`start.sh`** (session-hooks unit) so hook and CLI stay **bit-for-bit consistent** on counts.

**Token counting library:** **`tiktoken`** with encoding **`cl100k_base`** — same encoder as the reflect skill (`docs/plans/reflect-skill/PLAN.md`) and `docs/plans/system/PLAN.md` §6.2.

**Files read (per Role under `$BASE`):**

1. **`$BASE/personal/SELF.md`** — cross-role self draft (same file for every Role’s combined metric; if missing, **0** tokens for that leg).  
2. **`[role]/ROLE.md`** — that Role’s behavioral delta (if missing, **0** tokens).  
3. **`[role]/CONTEXT.md`** — that Role’s current focus (optional; if missing, **0** tokens).

For each `role_path` returned by `iter_role_dirs(base)`, compute:

`combined(role) = count_tokens(personal/SELF.md) + count_tokens(role/ROLE.md) + count_tokens(role/CONTEXT.md)`

where `count_tokens` reads each path as **UTF-8** with replacement for invalid bytes and uses `tiktoken` on the **file body** (no YAML front matter stripping unless later standardized — v1 counts raw markdown).

**Threshold:** **1,500** tokens. If `combined(role) > 1500` for **any** Role, the check status is **`WARN`** (not `FAIL`). Emit **one logical result** that lists every offending Role and its `combined` count.

**Human line shape (default):**

- Under budget (all roles):  
  `[PASS] always_loaded_budget: all roles ≤1500 tokens (always-loaded stack)`

- Over budget (example):  
  `[WARN] always_loaded_budget: work: 1720 tokens (budget 1500, 220 over); shorten CONTEXT.md by ~220 tokens — or trim ROLE.md / personal SELF.md if CONTEXT is already minimal`

**Remediation rule:** Let `overage = combined - 1500`. The primary user-facing remediation matches the system metric: **shorten CONTEXT.md by ~N tokens** with **N = overage** (rounded to a whole number). If multiple Roles breach, print a clause per Role. Optionally add one short hint when `CONTEXT.md` is absent or tiny: *"overage is not only CONTEXT.md; curate ROLE.md or SELF.md."*

**Unit metric note:** `docs/specs/masks-cli-core/SPEC.md` M-06 still describes **six** pass/fail checks; treat the seventh line as an **additional** structured row for the combined budget (update the unit spec in a follow-up so M-06 explicitly includes this WARN line or references S-08).

**Full human example (seven lines):**

```
[PASS] agents_symlink: AGENTS.md -> …
[PASS] role_env: all N roles have .env
[FAIL] git_remote: work: ls-remote failed (exit 128)
[PASS] mcp_memory_db: …
[PASS] ooda_agenda: all roles parseable
[FAIL] guards_executable: email-classifier.sh not executable
[WARN] always_loaded_budget: work: 1720 tokens (budget 1500, 220 over); shorten CONTEXT.md by ~220 tokens — or trim ROLE.md / personal SELF.md if CONTEXT is already minimal
```

**JSON output (`--json`):** `{"ok": <bool>, "checks": [...]}` with **seven** objects; statuses `"pass" | "fail" | "warn"` — only checks 1–6 use `"fail"`; `always_loaded_budget` uses `"warn"` or `"pass"` only.

**Exit code:** **0** if checks **1–6** all pass; **1** if any of **1–6** fail (M-07). Check **7** never affects exit code (S-08 is warn-only).

---

## 4. Shared utilities

### 4.1 `paths.py`

- `resolve_base_path() -> Path` — documented order in §1.  
- `resolve_framework_root() -> Path` — §1.  
- `load_base_env_mask(base: Path) -> Optional[str]` — read `MASKS_BASE` from `$BASE/.env` without exporting secrets.  
- `merge_env_file(path: Path, key: str, value: str)` — upsert one key preserving other lines.

### 4.2 `roles.py`

- `iter_role_dirs(base: Path) -> Iterator[Path]`: non-hidden immediate subdirs of `base` that are directories, excluding names that are clearly not roles (`Archive` none at base—none).  
- `is_role_layout(p: Path) -> bool`: has `Memory/INDEX.md` and `Reference/INDEX.md` and `Archive/INDEX.md`.

### 4.3 `ooda_parse.py`

- `extract_agenda_skills(ooda_path: Path) -> list[str]`  
  - Read text UTF-8 with replacement.  
  - State machine: only lines under headings exactly `### Observe`, `### Orient`, `### Act` (case-sensitive, at line start).  
  - Within those sections, collect lines matching `^\s*\d+\.\s+([a-z0-9-]+)` (skill slug).  
  - Stop section at next `###` heading or EOF.  
  - Return skills in document order, deduplicated preserving first occurrence.  
  - Malformed files yield empty list (doctor fails; run logs warning—run spec).

### 4.4 `hooks.py` — `install_hooks_for_role(role_path: Path, fw: Path)`

Per `docs/specs/session-hooks/SPEC.md` soft constraints:

1. **Cursor:** Write `.cursor/hooks.json` in `role_path` with **absolute** paths to `fw / "hooks/start.sh"` and `fw / "hooks/end.sh"` using the schema Cursor expects for this repo (version field + hook commands). If file exists, merge/update only the Pirandello keys (idempotent).  
2. **Claude Code:** Create or patch `role_path / "CLAUDE.md"` with fenced lifecycle blocks that invoke the same scripts with absolute paths (append if missing).  
3. **Git post-commit:** Write `role_path / ".git/hooks/post-commit"` as a **small wrapper** that `exec`s `fw / "hooks/post-commit.sh"` (or symlink if platform permits; wrapper avoids symlink issues on some filesystems). Set executable bit `0o755`.  
4. Idempotent: re-running replaces wrapper with identical content—no duplicate lines in `CLAUDE.md` (detect marker comment `<!-- pirandello-hooks -->`).

### 4.5 `token_budget.py`

- `count_tokens_file(path: Path) -> int` — UTF-8 read + `tiktoken.get_encoding("cl100k_base")`; missing file → **0**.  
- `combined_always_loaded(base: Path, role_path: Path) -> int` — `personal/SELF.md` + `role_path/ROLE.md` + `role_path/CONTEXT.md`.  
- Callable as **`python -m masks.token_budget`** (or a thin CLI entry) from **`start.sh`** so the hook does not duplicate counting logic (see `docs/plans/system/PLAN.md` §6.2).

---

## 5. Open decisions

| Topic | Decision for v1 |
|-------|------------------|
| Cursor `hooks.json` schema | Pin to the schema version Pirandello documents in root `AGENTS.md` at implementation time; add a golden-file test fixture. |
| `masks sync` pull failure | Continue with warning (not silent); push still attempted. Matches “sync all roles” expectation. |
| `add-role --interactive` without Claude | Respect `MASKS_INTERACTIVE_CMD`; otherwise friendly message—**no** failing exit if automation unavailable (user can run skill manually). |
| `status` guard note parsing | Tighten regexes once `masks run` log format is frozen; share `LOG_PATTERNS` constant between units. |
| `doctor` remote check | `git ls-remote origin HEAD` only; SSH agent must be available—timeout prevents hang. |
| S-08 / hook parity | `token_budget.py` is the single source of truth for counts; `start.sh` shells out to the same module the CLI uses. |

---

## 6. Self-check table

### Unit metrics (`docs/specs/masks-cli-core/SPEC.md`)

| ID | Result | Evidence in proposal |
|----|--------|------------------------|
| M-01 | pass | §1 Typer + `pyproject.toml` `[project.scripts]`; `uv tool install ./cli` |
| M-02 | pass | §3.1 idempotent guards: no overwrite, conditional git init |
| M-03 | pass | §3.1 lists all required artifacts and symlink |
| M-04 | pass | §3.2 scaffold + hooks + optional remote |
| M-05 | pass | §3.3 skip remoteless with WARN, exit 0 |
| M-06 | pass\* | §3.5 seven labelled lines / seven JSON checks; six blocking pass/fail + `always_loaded_budget` (WARN\|PASS). \*Unit spec text still says “six checks”; update `SPEC.md` / `SCENARIOS.md` to mention the seventh advisory row. |
| M-07 | pass | §3.5 exit **1** only if any of checks **1–6** fail; `always_loaded_budget` is never a failure |
| M-08 | pass | §1 `resolve_base_path`; no `~/Desktop` literal; `MASKS_BASE` persistence |

### Top-level metrics (`docs/SPEC.md`)

| ID | Result | Evidence |
|----|--------|----------|
| S-01 | pass | Proposal contains no personal data; only describes public templates |
| S-02 | pass | No workflow makes DB canonical; doctor only checks file exists |
| S-03 | pass | Session reliability remains in hooks (session-hooks unit); core installs them |
| S-04 | pass | Core never writes `Memory/` |
| S-05 | pass | §1 idempotency for setup/add-role; sync/status/doctor repeatable |
| S-06 | pass | No code path commits `SELF.md` |
| S-07 | pass | Core does not emit ROLE/SELF content; per-file size budgets enforced by reflect skill and synthesis, not CLI core |
| S-08 | pass | §3.5 **`always_loaded_budget`**: reads `personal/SELF.md` + each Role’s `ROLE.md` / `CONTEXT.md`; **tiktoken `cl100k_base`** via **`token_budget.py`** (same helper as `start.sh`); **`[WARN]`** line with **shorten CONTEXT.md by ~N tokens** (N = overage) when per-role combined sum **> 1,500**; no truncation; exit code unaffected (hook still owns session-time warning per S-08 table). |

### Scenario / stress cross-check (informative)

| Scenario / stress | Addressed |
|-------------------|-----------|
| Fresh setup | §3.1 |
| Re-run setup | §3.1 idempotency |
| add-role consulting | §3.2 |
| sync remoteless | §3.3 |
| doctor healthy / partial fail | §3.5 all blocking checks always run; seventh line is budget WARN only |
| custom `--base` | §1 persistence in `.env` |
| status fields | §3.4 |
| T8 no hardcoded desktop path | §1 `Path.home()` |

---

## Implementation note for Pirandello repo layout

This proposal assumes the following exist **before** or **with** this unit’s merge: `AGENTS.md`, `.env.example`, `templates/.gitignore`, `templates/OODA.md`, `hooks/*.sh`, and `guards/*.sh` as referenced by other specs. The core CLI only **copies**, **symlinks**, and **validates** them—it does not author hook bodies.
