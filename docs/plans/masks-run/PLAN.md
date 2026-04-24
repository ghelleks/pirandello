# Proposal: `masks run` — Heartbeat Runner

**Unit:** `docs/specs/masks-run/SPEC.md`  
**Status:** proposal  
**Date:** 2026-04-23  

---

## 1. Overview

`masks run <role>` is implemented as a Python 3.10+ module at `cli/masks/run.py`, exposed as the `masks run` Typer/Click subcommand alongside other `masks` commands. The runner is **purely mechanical**: it resolves the Role from the **first positional CLI argument** (never from `$PWD`), resolves `$BASE` from `MASKS_BASE` with fallback to `$HOME/Desktop`, sources environment files in a fixed order, parses `$BASE/<role>/OODA.md` to produce an ordered list of skill names, executes each corresponding guard script under `<PIRANDELLO_ROOT>/guards/<skill>.sh` in that order (where `PIRANDELLO_ROOT` is resolved via `resolve_framework_root()`, not hardcoded), logs one structured line per invocation to `$BASE/<role>/.ooda.log`, and **only if at least one guard exits 0** starts a single LLM subprocess whose **only** user-visible instruction payload is the UTF-8 text of `OODA.md` (no `SELF.md`, `ROLE.md`, `CONTEXT.md`, or index files).

If every guard exits non-zero (including guards treated as non-zero because the script is missing or not executable), the runner appends a log line that includes the token `OODA_OK` and exits 0 without spawning an LLM.

If `OODA.md` is absent, the runner logs a warning line and exits 0 without running guards or an LLM.

The runner **never** short-circuits guard execution early: all guards listed in the agenda always run in document order, even after one has already exited 0. This keeps logs complete and preserves predictable side effects (e.g. lightweight metrics) if guards are later extended.

---

## 2. OODA.md parsing

### 2.1 Algorithm

Parsing is implemented in Python (same module as the runner) using a **single forward scan** with a small state machine so **document order is preserved** (required for M-04).

1. Normalize newlines to `\n` and read the file as UTF-8 with replacement for invalid bytes (invalid sequences never crash the run; they may yield odd skill names and are surfaced via guard failures, not parser exceptions).
2. Track `phase ∈ {none, observe, orient, act}`.
3. For each line:
   - If the line matches `^###\s+(Observe|Orient|Act)\s*$` (case-sensitive heading text), set `phase` to the corresponding value.
   - Else if `phase != none` and the line matches the **numbered agenda pattern**  
     `^\s*(\d+)\.\s+(.+?)\s*$`  
     capture group 2 as `raw_item`:
     - Strip surrounding ASCII whitespace.
     - Strip one pair of surrounding `` ` `` characters if both the first and last non-space characters are backticks.
     - Strip trailing comment segments starting at ` — `, ` -- `, or ` # ` (em dash / double hyphen / hash) so prose after the skill name does not pollute the name.
     - The result must match `^[a-z0-9][a-z0-9-]*$` (skill slug). If it does, append it to `agenda_skills`. If it does not, append a **warning** to the run log (see §5) `WARN_SKIP_AGENDA_LINE` with the line number and raw line text, and continue.
   - Lines that are bullets (`^\s*-\s+`) or other non-numbered shapes under an active phase are **not** treated as skills: log `WARN_MALFORMED_AGENDA_LINE` with line number, continue without adding a skill.
4. Headings `### Foo` other than Observe/Orient/Act set `phase = none` until another recognized phase heading appears (so random `###` sections do not inherit a stale phase).
5. If no `### Observe`, `### Orient`, or `### Act` section exists, `agenda_skills` may be empty: the runner proceeds to guard execution with an empty list (no guards run); it then logs `OODA_OK` with an empty guard list (all-fail degenerates to “no work” — no LLM).

### 2.2 Malformed or partial documents

- **Missing file:** handled before parsing (§1): warning + exit 0.
- **Unreadable path:** if `OODA.md` exists but is not a file (symlink to directory, permission denied), log `WARN_OODA_NOT_READABLE`, exit 0 (same “cron-safe” posture as missing file; avoids stderr stack traces from the CLI).
- **Mixed valid and invalid lines:** valid numbered entries are still collected; invalid lines produce warnings only.

This behavior satisfies scenario 6: malformed entries never crash the runner; they are warned and skipped; well-formed lines still run.

---

## 3. Guard execution

### 3.1 Paths and discovery

- `ROLE` = CLI argument `<role>` (directory name under `$BASE`, e.g. `work`).
- `ROLE_DIR` = `$BASE/<role>` (absolute path after `os.path.realpath`).
- Guard path for skill `S`: `GUARDS_DIR/S.sh` where `GUARDS_DIR` = `resolve_framework_root() / "guards"`.
- `resolve_framework_root()` walks upward from `__file__` (i.e. `cli/masks/run.py`) until it finds a directory containing `guards/` and `AGENTS.md`, falling back to `Path(os.environ.get("PIRANDELLO_ROOT", Path(__file__).parents[2]))`. This makes the framework relocatable — no dependency on `$HOME/Code/pirandello`.

### 3.2 Environment visible to guards

Before **any** guard runs, the runner:

1. Loads `$BASE/.env` then `$ROLE_DIR/.env` into the runner process environment (see §3.3).
2. Sets **runner-supplied** variables (may override same-named keys from `.env` intentionally):
   - `MASKS_BASE` = absolute base path  
   - `MASKS_ROLE` = role name  
   - `MASKS_ROLE_DIR` = absolute `$BASE/<role>`  
   - `MASKS_OODA_PATH` = absolute path to `OODA.md` (guards should not read it for decision logic per design; exported for rare diagnostics only)

Guard contract remains: **exit 0 = work to do; exit non-zero = nothing to do.**

### 3.3 Sourcing `.env` files

Implemented in Python without invoking a shell `source` for portability:

- Parse `.env` using a **minimal dotenv subset**: `KEY=VALUE` lines, ignore blank lines and `#` comments, strip optional single/double quotes around `VALUE`, no export keyword required.
- Apply keys in order: base file first, then role file (role **wins** on duplicate keys) — satisfies M-02 / stress T2.
- If a file is missing, skip silently. If unreadable, log `WARN_ENV_UNREADABLE` to `.ooda.log` once per file and continue.

### 3.4 Invocation loop

For each skill name `S` in `agenda_skills` order:

1. Let `G = GUARDS_DIR + "/" + S + ".sh"`.
2. If `G` is not a regular file **or** not executable by the current user (`os.access(..., X_OK)`):
   - Append `(S, None, "missing_or_not_executable")` to results.
   - Log inline warning token in the summary line (see §5).
   - **Treat as non-zero** for trigger logic.
3. Else:
   - Run `subprocess.run([G], env=environ_copy, cwd=ROLE_DIR, capture_output=True, text=True, timeout=5)`  
     - Timeout → log `WARN_GUARD_TIMEOUT S`, treat exit code as non-zero for trigger purposes.
   - Record `(S, returncode, None)`.

**No guard output is forwarded to stderr** by default (cron cleanliness); if a guard emits stderr, the runner may append a single-line `WARN_GUARD_STDERR name=...` entry **only if** stderr is non-empty and shorter than 2 KiB (truncated) to avoid log flooding.

### 3.5 Trigger rule

- Let `trigger = any(code == 0 for code in codes where code is not None)`.
- Missing / non-exec / timeout → not in the `any(...)` as 0; they are non-triggering.

This matches M-05, M-09, scenario 4, and stress T4.

---

## 4. LLM invocation

### 4.1 Command selection

- If `MASKS_LLM_CMD` is **unset** or empty, the default is the argv sequence:  
  `claude --print --output-format text`  
  (Claude Code CLI; reads the user message from **stdin** only.)

- If `MASKS_LLM_CMD` is **set**, the runner executes it via:  
  `["/bin/sh", "-c", MASKS_LLM_CMD]`  
  with the same merged environment as guards, **and** with:
  - `MASKS_OODA_PATH` = absolute path to `OODA.md`

  The contract for custom commands: they **must** treat `OODA.md` as the sole Pirandello document for context — typically `claude --print --output-format text < "$MASKS_OODA_PATH"` or equivalent. The runner **does not** pass `SELF.md` / `ROLE.md` / indexes in any form.

### 4.2 Feeding OODA.md (default path)

For the default argv (no `MASKS_LLM_CMD`), the runner opens `OODA.md` and passes its bytes decoded as UTF-8 (replace) to the subprocess **stdin**. Stdout/stderr of the LLM process are **discarded** to `/dev/null` for cron hygiene unless `MASKS_LLM_DEBUG=1` is set, in which case stderr is copied into `.ooda.log` as a single bounded block (max 16 KiB) prefixed `LLM_STDERR`.

### 4.3 Working directory

The LLM subprocess uses `cwd=ROLE_DIR` so relative paths **inside** `OODA.md` (if the model or tool layer resolves them) refer to the Role root — still consistent with “session root is the Role directory” at the system level. The injected **text** remains only `OODA.md` content.

### 4.4 Failure handling

Non-zero exit from the LLM command is logged as `LLM_EXIT code=N` on the same run’s log block (see §5) but **does not** change the runner’s exit code from 0 (cron should not retry storm). A future `masks doctor` enhancement may surface repeated LLM failures.

---

## 5. Log format

All log lines are appended to `$BASE/<role>/.ooda.log` as **single lines** (no embedded raw newlines; replace `\n` in messages with `\n` escape in warnings if needed).

### 5.1 Primary record (every run)

```
ts=<ISO-8601-offset> role=<role> guards=<guard1>:<code>|<guard2>:<code>|... trigger=<yes|no> llm=<yes|no> [OODA_OK]
```

- `<ISO-8601-offset>`: `datetime.now().astimezone().isoformat(timespec="seconds")` (Python 3.10+), e.g. `2026-04-23T09:15:00-05:00`.
- `<code>`: decimal exit status, or `X` for missing/non-executable, `T` for timeout.
- `trigger=yes` iff any guard returned 0.
- `llm=yes` iff an LLM subprocess was spawned this run.
- **`OODA_OK` token** appears **iff** `llm=no` **and** parsing produced at least one guard slot **or** the agenda was empty after successful parse — i.e. “this heartbeat cycle did not start an LLM.” For missing `OODA.md`, use the warning format below instead.

This satisfies requirement 9 always (M-08 / T7) and requirement 7’s `OODA_OK` expectation when all guards fail (M-06 / scenario 1).

### 5.2 Missing OODA.md

```
ts=<ISO-8601-offset> role=<role> WARN=OODA_MISSING path=<abs-path> llm=no
```

### 5.3 Auxiliary warnings (same file, prior or following the primary line)

Optional lines for debugging (still single-line):

```
ts=... role=... WARN_SKIP_AGENDA_LINE line=<n> text=<escaped>
ts=... role=... WARN_MALFORMED_AGENDA_LINE line=<n> text=<escaped>
ts=... role=... WARN_ENV_UNREADABLE file=<abs>
ts=... role=... WARN_GUARD_TIMEOUT skill=<name>
```

The **primary record** remains mandatory every run where `OODA.md` was parsed.

### 5.4 Cron redirection

The documented crontab continues to append stderr:  
`*/15 * * * 1-5 masks run work 2>> $BASE/work/.ooda.log`  
The Python runner writes only via explicit log calls (stdout may be silent), so normal success produces **no stderr**.

---

## 6. Example guard scripts

All scripts: `#!/usr/bin/env bash`, `set -euo pipefail`, finish in under 5 seconds, **no LLM**. Exit code contract: **0 = run skill**.

### 6.1 `guards/ooda-observe.sh`

Aggregates cheap “any signal” checks. Any one positive yields exit 0.

```bash
#!/usr/bin/env bash
set -euo pipefail

# Work Gmail: any unread inbox messages (uses gws if installed and WORK account configured).
if command -v gws >/dev/null 2>&1; then
  if gws gmail triage --account work 2>/dev/null | grep -q .; then
    exit 0
  fi
fi

# Fallback: optional marker file listing pending observer items
OBS_MARKER="${MASKS_ROLE_DIR:-.}/.ooda-pending/observer.txt"
if [[ -f "$OBS_MARKER" ]] && grep -q '[^[:space:]]' "$OBS_MARKER" 2>/dev/null; then
  exit 0
fi

exit 1
```

The marker file path is a **concrete extension point** for installations without `gws` in cron `PATH`; the observe skill may maintain it. If neither path applies, the guard correctly returns non-zero.

### 6.2 `guards/email-classifier.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

command -v gws >/dev/null 2>&1 || exit 1

# Pass when there is at least one triage row for work account (unread / needs classification).
if gws gmail triage --account work 2>/dev/null | grep -q .; then
  exit 0
fi

exit 1
```

### 6.3 `guards/daily-briefer.sh`

Encodes **all** time-window and “already ran today” logic; `masks run` has **no** clock awareness.

```bash
#!/usr/bin/env bash
set -euo pipefail

ROLE_DIR="${MASKS_ROLE_DIR:?MASKS_ROLE_DIR not set by masks run}"

# Machine local TZ (cron default).
now_h=$(date +%H)
now_m=$(date +%M)
now_total=$((10#$now_h * 60 + 10#$now_m))
target=$((6 * 60 + 45)) # 06:45
delta=$((now_total - target))
if [[ $delta -lt 0 ]]; then delta=$(( -delta )); fi
[[ $delta -le 15 ]] || exit 1

mkdir -p "$ROLE_DIR/.ooda-state"
stamp="$ROLE_DIR/.ooda-state/daily-briefer-$(date +%Y-%m-%d)"
[[ ! -f "$stamp" ]] || exit 1

exit 0
```

**Pairing contract:** the `daily-briefer` skill (Act phase) runs `touch "$ROLE_DIR/.ooda-state/daily-briefer-$(date +%Y-%m-%d)"` on successful completion so subsequent heartbeats the same day exit non-zero.

### 6.4 `guards/ooda-act.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

command -v td >/dev/null 2>&1 || exit 1

# Todoist: agent/decision-tagged actionable work present today or overdue.
if td find-tasks --filter '(today | overdue) & (@agent | @decision)' 2>/dev/null | grep -q .; then
  exit 0
fi

exit 1
```

---

## 7. Open decisions

| Topic | Decision for v1 | Follow-up |
|-------|-----------------|-----------|
| LLM subprocess lifetime | **Synchronous:** `masks run` blocks until the LLM CLI exits; cron spacing (15 min) limits overlap. | If runs exceed 15 minutes, add `timeout(900)` wrapper or external job queue. |
| Concurrent overlapping crons | Not prevented; second run may start while first LLM still runs. | File lock `$ROLE_DIR/.ooda.lock` optional future hardening. |
| Default Claude flags | `--print --output-format text` assumes non-interactive automation. | If Anthropic changes CLI flags, pin version in `pyproject` docs. |
| `gws` / `td` availability in cron | Guards assume tools on `PATH` after login-equivalent cron setup (`PATH=...` in crontab or wrapper). | `masks doctor` warns when binaries missing. |

Nothing in v1 is left “TBD” for implementers: the above table picks defaults.

---

## 8. Self-check table

### Unit metrics (`docs/specs/masks-run/SPEC.md`)

| ID | Result | Evidence in proposal |
|----|--------|----------------------|
| M-01 | **pass** | §1, §3.1: role from CLI arg; paths built from `$BASE/<role>`. |
| M-02 | **pass** | §3.3: base `.env` then role `.env`; role overrides. |
| M-03 | **pass** | §2.1: extracts numbered items under Observe/Orient/Act; warns on malformed. |
| M-04 | **pass** | §1, §2.1, §3.4: single forward scan preserves order; all guards run in sequence. |
| M-05 | **pass** | §3.5: `any` guard 0 triggers LLM; §1 no early exit. |
| M-06 | **pass** | §1, §5.1: all-fail yields `OODA_OK` token, `llm=no`, no subprocess. |
| M-07 | **pass** | §4: stdin-only OODA.md for default CLI; custom cmd contract uses only `MASKS_OODA_PATH`. |
| M-08 | **pass** | §5.1 primary line every run with ts, guard codes, `llm` flag. |
| M-09 | **pass** | §3.4: missing/non-exec yields warn plus treat as non-zero plus continue. |
| M-10 | **pass** | §2.2, §5.2: missing OODA yields warning log, exit 0, no LLM. |

### Top-level static metrics (`docs/SPEC.md`)

| ID | Result | Evidence |
|----|--------|----------|
| S-01 | **pass** | Proposal contains no personal data, credentials, or Role content for `pirandello/`. |
| S-02 | **pass** | No mcp-memory or DB as truth; runner does not write `Memory/`. |
| S-03 | **pass** | Heartbeat reliability is CLI plus guards, not AGENTS.md. |
| S-04 | **pass** | Runner never writes another Role’s `Memory/`; guards only read env/APIs. |
| S-05 | **pass** | `masks run` twice causes duplicate log lines and duplicate LLM if guards still pass — acceptable; no corrupting side effects in runner itself (append-only log, no destructive ops). |
| S-06 | **pass** | No code path touches `SELF.md`. |
| S-07 | **pass** | No token-budget documents produced by this unit. |

---

## Implementation checklist (developer-facing)

1. Add `run.py` with Typer command `run(role: str)`.
2. Implement dotenv subset loader plus env merge.
3. Implement OODA parser per §2.
4. Implement guard loop per §3.
5. Implement LLM spawn per §4.
6. Add `guards/*.sh` for default work agenda skills (at minimum the four in §6; remainder as separate PRs follow same contract).
7. Unit tests: parser golden files (valid/malformed), guard ordering, env precedence, trigger logic with fake guard dir.
