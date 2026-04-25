# SDD Scenarios: `masks run` — Heartbeat Runner

**Companion spec:** `docs/specs/masks-run/spec.md`  
**Date:** 2026-04-23

---

## Use Cases

### 1. All guards fail — quiet no-op

Cron fires `masks run work` at 9:15am. All four guards in `work/OODA.md` exit non-zero: inbox is empty, no unread calendar items, `daily-briefer` already ran today, no `agent`-labeled Todoist tasks.

Questions the proposal must answer:
- Does the runner log `OODA_OK [ISO timestamp]` to `$BASE/work/.ooda.log` and exit 0?
- Is any LLM process invoked?
- Does the log entry include which guards were run and their exit codes?
- Is the log entry in the format specified, or does the proposal define a different format?

Metric cross-references: M-06, M-08

---

### 2. One guard passes — LLM invoked with OODA.md only

Cron fires `masks run work` at 9:30am. Three guards exit non-zero. The `email-classifier` guard exits 0 (unread work Gmail detected). The runner decides to invoke the LLM.

Questions the proposal must answer:
- Is the LLM invoked with `OODA.md` as the sole context — no SELF.md, no ROLE.md, no CONTEXT.md, no indexes?
- How does the proposal pass OODA.md to the LLM (file path argument, stdin, embedded prompt)?
- Does the runner log that an LLM session was invoked, along with which guard triggered it?
- Do the other three guards still run before the decision is made, or does the runner short-circuit on the first passing guard?

Metric cross-references: M-05, M-07, M-08

---

### 3. OODA.md is missing from the role directory

Cron fires `masks run work` but `work/OODA.md` does not exist (perhaps the file was accidentally deleted or the Role was just created and onboarding was never completed).

Questions the proposal must answer:
- Does the runner log a warning to `.ooda.log` and exit 0?
- Does it avoid invoking any LLM?
- Is the exit clean — no stack trace, no error output to stderr that would pollute the cron log?

Metric cross-references: M-10

---

### 4. A guard script is missing or not executable

`masks run work` fires and one of the guard scripts listed in OODA.md — say `guards/meeting-summary.sh` — does not exist on disk. Another guard script exists but has its execute bit unset.

Questions the proposal must answer:
- Does the runner log a warning for each missing or non-executable guard script, then treat that guard as non-zero (not triggered)?
- Does it continue processing the remaining guards in order?
- Does it not abort the entire run because of the missing guard?
- If all other guards also exit non-zero, does the runner still log OODA_OK?

Metric cross-references: M-09

---

### 5. OODA.md with guards in all three phases

`work/OODA.md` lists guards under `### Observe`, `### Orient`, and `### Act` sections. The runner should process guards in document order: Observe guards first, then Orient, then Act.

Questions the proposal must answer:
- Does the runner execute guards in the order they appear in OODA.md regardless of which phase they belong to?
- Does it read all three sections (`### Observe`, `### Orient`, `### Act`) when discovering guards?
- If a guard appears under `### Act` passes but all guards under `### Observe` and `### Orient` fail, is the LLM still invoked?

Metric cross-references: M-03, M-04, M-05

---

### 6. Malformed OODA.md — skill names unreadable

`work/OODA.md` exists but a recent manual edit left one agenda section with non-standard formatting (e.g., a skill listed as a bullet `- ooda-observe` instead of a numbered item `1. ooda-observe`).

Questions the proposal must answer:
- What parsing behavior does the proposal define for malformed entries?
- Does a malformed entry cause the runner to crash, skip that entry silently, or log a warning?
- Does the runner still process correctly-formatted entries in the same document?

Metric cross-references: M-03

---

### 7. Role resolved from argument, not `$PWD`

Cron invokes `masks run work` from a cron environment where `$PWD` is `/root` or some other unrelated directory, not the role directory.

Questions the proposal must answer:
- Does the runner resolve the role from the CLI argument `work`, not from `$PWD`?
- Does it construct `$BASE/work/.ooda.log` and `$BASE/work/OODA.md` from the argument, and optionally `$BASE/work/.env` if present, not from the current directory?
- Would a proposal that reads `$PWD` fail this case?

Metric cross-references: M-01, M-02

---

### 8. Time-of-day guard for `daily-briefer` — before, during, and after the window

`work/OODA.md` includes `daily-briefer` in the Agenda. Its guard script (`guards/daily-briefer.sh`) exits 0 only when the current time is within 15 minutes of 06:45 and the briefer has not already run today. All other guards in the agenda exit non-zero throughout. `masks run work` is called by cron three times:

1. At 05:30 — before the time window
2. At 06:48 — inside the window
3. At 08:00 — after the window, and after invocation 2 successfully ran the briefer

Questions the proposal must answer:
- In invocation 1 (05:30): does `daily-briefer.sh` exit non-zero? Does the runner continue evaluating the remaining guards before concluding all-fail and logging OODA_OK?
- In invocation 2 (06:48): does `daily-briefer.sh` exit 0? Is the LLM invoked with OODA.md as sole context?
- In invocation 3 (08:00): does `daily-briefer.sh` exit non-zero (already ran today)? Does the runner log OODA_OK again?
- Does `masks run` itself implement any time-of-day logic — or does it rely entirely on the guard script to handle time conditions?
- Does the guard contract's simplicity (exit 0 / non-zero) correctly express this multi-condition self-guard without requiring runner changes?

Metric cross-references: M-04 (guard order), M-05 (any-pass trigger), M-06 (all-fail no-op), M-08 (log completeness), design intent: "Skills that should only run at a specific time self-guard on the clock; the pre-flight runner checks the condition before invoking any LLM"

---

## Stress Tests

**T1 Role resolved from CLI argument, never from `$PWD`.**  
The runner constructs all paths — OODA.md, optional role .env, .ooda.log — from `$BASE/<role>` where role comes from the positional CLI argument.  
Pass: running `masks run work` from `/tmp` produces the same behavior as running it from `~/Desktop/work/`.

**T2 `$BASE/.env` is sourced before optional `$BASE/<role>/.env`.**  
When the same environment variable is present in both files, the role-level value wins. The runner sources base env first, then role env if it exists.  
Pass: a variable set to `base_value` in `$BASE/.env` and `role_value` in `$BASE/work/.env` resolves as `role_value` during guard execution; if role `.env` is absent, `base_value` is used.

**T3 Guards are executed in OODA.md document order.**  
The runner executes guards in the exact sequence they appear in the OODA.md file — top-to-bottom across all three phase sections.  
Pass: a test OODA.md with guards that log their execution order produces entries matching document order.

**T4 A single passing guard is sufficient to trigger the LLM.**  
When five guards are listed and only guard #3 exits 0, the LLM is invoked.  
Pass: the runner does not require a majority of guards or all guards to pass; one is enough.

**T5 All-fail condition produces no LLM invocation.**  
When every guard exits non-zero, the runner logs OODA_OK and exits without starting any LLM process.  
Pass: no LLM process is in the process list after a run where all guards return non-zero; `OODA_OK` appears in the log.

**T6 LLM session receives only OODA.md content.**  
The LLM session started by the runner does not include SELF.md, ROLE.md, CONTEXT.md, Memory/INDEX.md, Reference/INDEX.md, or Archive/INDEX.md in its injected context.  
Pass: the command or prompt passed to the LLM contains only OODA.md content; no other Pirandello document is injected.

**T7 Every run produces a log entry.**  
Each execution of `masks run` appends at least one line to `$BASE/<role>/.ooda.log` with a timestamp, guard results, and LLM invocation status.  
Pass: after any run (all-fail or any-pass), the log file contains a new entry; a run that produces no log entry fails this test.

**T8 Missing guard is logged as warning and treated as non-zero.**  
A guard script listed in OODA.md that does not exist on disk results in a warning log entry and is counted as non-zero (not triggering). The run continues.  
Pass: the runner does not crash; the warning appears in the log; the missing guard does not count as a passing condition.

**T9 Missing OODA.md produces clean warning exit.**  
`masks run work` when `work/OODA.md` is absent logs a warning and exits 0 with no LLM invoked and no stack trace.  
Pass: exit code is 0; the log contains a warning; no LLM process was started.

---

## Anti-Pattern Regression Signals

**LLM injected with full interactive context stack.** The runner passes SELF.md, ROLE.md, or CONTEXT.md to the LLM in addition to OODA.md. Symptom: OODA sessions consume many more tokens than expected; identity and role context bleeds into autonomous observation outputs. Indicates: runner reusing the interactive hook's context injection logic instead of OODA.md-only injection. Maps to: M-07.

**Guard scripts invoked out of OODA.md order.** Guards are sorted alphabetically or by phase name rather than by position in the document. Symptom: a time-sensitive guard (e.g., `daily-briefer` which checks the clock) runs in the wrong order relative to other guards, causing unexpected LLM invocations. Indicates: OODA.md parser uses a data structure that loses document order. Maps to: M-04.

**Runner aborts on missing or non-executable guard.** A single missing guard script causes the entire run to exit non-zero, halting all subsequent guard execution. Symptom: when a new skill is added to OODA.md but its guard hasn't been written yet, the OODA loop stops running entirely until the guard is created. Indicates: missing per-guard error handling; guard failure propagates to runner exit. Maps to: M-09.

**Role derived from `$PWD` in cron environment.** The runner reads `$PWD` to determine which Role to run. Symptom: `masks run work` invoked from cron (where `$PWD` may be `/root` or `/`) runs against the wrong Role or fails to find OODA.md. Indicates: `$PWD`-based role derivation instead of CLI argument. Maps to: M-01.

**`OODA_OK` not logged when all guards fail.** When no LLM is invoked, the runner exits silently without writing a log entry. Symptom: `masks status` shows no last OODA_OK timestamp even on a healthy system that has been running for days. Indicates: log write only happens on LLM-invoked path, not on all-fail path. Maps to: M-06, M-08.

**Runner implements time-of-day logic instead of delegating to guards.** `masks run` checks the current time before invoking guards or filters which guards run based on time conditions it reads from OODA.md. Symptom: adding a new time-sensitive skill requires modifying the runner, not just writing a guard script; the runner becomes a scheduler rather than a pure executor. Indicates: time-gating logic belongs in guard scripts, not in the runner. Design intent: "There is no separate scheduled jobs concept." Maps to: M-03, M-04.
