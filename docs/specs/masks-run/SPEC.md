# SDD Spec: `masks run` — Heartbeat Runner

**Context:** See `docs/spec.md` for full system design. This spec covers the OODA heartbeat runner: the command that fires every 15 minutes from cron, evaluates pre-flight guards, and conditionally invokes an LLM session.

**Deliverables:** `cli/masks/run.py`, `guards/` directory with pre-flight guard contract, example guard scripts for all skills listed in the default work OODA agenda.

---

## Requirements

### Hard constraints

1. Entry point: `masks run <role>`. Role is the argument, not derived from `$PWD`.
2. Base directory is resolved from `MASKS_BASE` environment variable, falling back to `~/Desktop`.
3. Before any guard execution, sources `$BASE/.env`, then sources `$BASE/<role>/.env` only if present (role env overrides base env when provided).
4. Reads `$BASE/<role>/OODA.md` to discover the agenda. The agenda lists skills in order under `### Observe`, `### Orient`, and `### Act` sections. Each numbered item is a skill name.
5. For each skill in the agenda, executes `~/.pirandello/guards/<skill-name>.sh` (deployed there by `masks setup`). Guards are executed in agenda order.
6. Each guard script must exit 0 if its condition is met (LLM work needed) or non-zero if not (nothing to do). Guard scripts are fast, deterministic, and have zero LLM cost.
7. If **all** guards exit non-zero: log `OODA_OK [ISO timestamp]` to `$BASE/<role>/.ooda.log` and exit 0. No LLM is invoked.
8. If **any** guard exits 0: invoke an LLM session with `$BASE/<role>/OODA.md` as the **only** injected context. The full interactive prompt stack (SELF.md, ROLE.md, CONTEXT.md, indexes) is not injected for OODA sessions.
9. Every run is logged to `$BASE/<role>/.ooda.log` with: timestamp, list of guards run with their exit codes, and whether an LLM session was invoked.
10. If `OODA.md` is missing, log a warning and exit 0. Do not error.
11. If a guard script is missing or not executable, log a warning for that guard, treat it as failed (non-zero), and continue. Do not abort the run.
12. Designed for cron: `*/15 * * * 1-5 masks run work 2>> $BASE/work/.ooda.log`.

### Guard contract

Each guard script at `guards/<skill-name>.sh`:
- Receives no arguments.
- Has access to the environment sourced in step 3 (credentials, paths).
- Must complete in under 5 seconds.
- Must not invoke an LLM.
- Exits 0 = condition met (run this skill). Exits non-zero = nothing to do.

> **Convention note:** This deliberately inverts the standard Unix shell convention (where 0 = success and typically means "nothing went wrong / nothing to do"). In the guard contract, 0 means "yes, there is work to do." This framing makes guards express intent positively — `exit 0` reads as "go ahead." Implementers accustomed to Unix conventions must be careful not to reverse this.

### Soft constraints

- The LLM invocation command (e.g., `claude --no-cache`) should be configurable via `MASKS_LLM_CMD` environment variable.
- Guard scripts that include a time-of-day check (e.g., `daily-briefer`) self-contain that logic — `masks run` does not interpret time conditions.

---

## Proposal format

### 1. Overview
How the runner reads OODA.md, evaluates guards, and decides whether to invoke the LLM.

### 2. OODA.md parsing
How agenda items are extracted from OODA.md. What happens with malformed OODA.md.

### 3. Guard execution
How guards are discovered, invoked, and their results recorded. The exact exit-code contract.

### 4. LLM invocation
The exact command used to start an LLM session with OODA.md as sole context. How OODA.md content is passed (file path, stdin, or embedded in prompt).

### 5. Log format
The exact log line format written to `.ooda.log` for both OODA_OK and LLM-invoked cases.

### 6. Example guard scripts
Complete, working guard scripts for: `ooda-observe`, `email-classifier`, `daily-briefer`, `ooda-act`.

### 7. Open decisions
Anything the spec does not fully define (e.g., whether the LLM session is synchronous or backgrounded, how long to wait for it).

### 8. Self-check table
See Static Evaluation Metrics.

---

## Static evaluation metrics

| ID | Name | Pass condition |
|---|---|---|
| M-01 | Role from argument | Role resolved from CLI argument, not `$PWD` |
| M-02 | Env sourcing order | `$BASE/.env` sourced first; `$BASE/<role>/.env` is optional and, when present, overrides base env |
| M-03 | OODA.md parse | All skill names extracted correctly from numbered agenda items under all three phase headings |
| M-04 | Guard order | Guards executed in the order they appear in OODA.md |
| M-05 | Any-pass trigger | A single guard exiting 0 is sufficient to trigger LLM invocation; not all guards need to pass |
| M-06 | All-fail no-op | When all guards exit non-zero, no LLM is invoked and `OODA_OK` is logged |
| M-07 | OODA.md sole context | LLM session receives OODA.md content only — no SELF.md, ROLE.md, CONTEXT.md, or indexes |
| M-08 | Log completeness | Every run produces a log entry with timestamp, guard results, and LLM invocation status |
| M-09 | Missing guard graceful | Missing or non-executable guard script is logged as a warning and treated as non-zero (skipped) |
| M-10 | Missing OODA graceful | Missing OODA.md produces a warning log entry and clean exit 0 |
