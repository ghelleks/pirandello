# SDD Scenarios: Session Hooks

**Companion spec:** `docs/specs/session-hooks/spec.md`  
**Date:** 2026-04-23

---

## Use Cases

### 1. Normal work session with all optional files present

A user opens `~/Desktop/work/` in Cursor. The directory has `ROLE.md`, `AGENTS.md`, `CONTEXT.md`, `Archive/INDEX.md`, `Memory/INDEX.md`, and `Reference/INDEX.md`. The user works for 90 minutes, writes two Memory files, and closes Cursor.

Questions the proposal must answer:
- Does start.sh pull from both the role repo and `personal/` before injecting any context?
- Are all 8 context sections output in the specified order, each preceded by its exact label?
- Does end.sh commit exactly once (the staged changes) with a timestamp message and then push?
- Does post-commit.sh detect the two new Memory files and invoke `masks index work`?

Metric cross-references: M-01, M-02, M-03, M-04, M-05, M-06, M-07, M-08

---

### 2. Session in a role with no optional files

A user opens `~/Desktop/consulting/` as workspace root. The directory has `ROLE.md` but no `AGENTS.md`, no `CONTEXT.md`, no `Archive/INDEX.md`, no `Memory/INDEX.md`, no `Reference/INDEX.md`. The user makes no file changes and closes Cursor.

Questions the proposal must answer:
- Does start.sh skip each missing optional section without error, emitting no blank or empty-headed output for them?
- Are the required sections (`=== GLOBAL AGENTS ===`, `=== SELF ===`, `=== ROLE ===`) still emitted for files that do exist?
- Does end.sh detect no staged changes and skip the commit entirely?
- Does post-commit.sh not fire (no commit was made)?

Metric cross-references: M-02, M-03, M-05, M-07

---

### 3. No remote configured — push fails silently

A user has a local-only Role with no git remote. The session ends normally with modified files. The session-end hook commits and then attempts to push.

Questions the proposal must answer:
- Does the push failure produce no error output, no exit code propagation, and no disruption to the user's Cursor session?
- Does the commit still succeed even though push fails?
- Does the hook exit 0 even when push errors?

Metric cross-references: M-06

---

### 4. First commit in the role repo — no HEAD~1

A user runs `masks setup` on a new role and then starts their very first session. The session produces a Memory file. When the session ends, end.sh commits (creating the first commit), and post-commit.sh fires.

Questions the proposal must answer:
- Does post-commit.sh handle the absence of `HEAD~1` without crashing or producing a shell error?
- Does it correctly detect the Memory file as a change and invoke `masks index`?
- What behavior does the proposal define for this case specifically?

Metric cross-references: M-09

---

### 5. Memory file deleted during session

A user deletes a Memory file during a session (e.g., merging two People files). The session-end hook commits the deletion, and post-commit.sh fires.

Questions the proposal must answer:
- Does post-commit.sh detect deleted Memory files separately from modified ones, using the `--name-status` diff with the `awk '/^D/'` pattern?
- Does it still invoke `masks index` to synchronize the deletion to the database?
- Would a proposal that only checks `--name-only` (and misses deletions) fail this case?

Metric cross-references: M-07, M-08

---

### 6. Both `$BASE/.env` and role `.env` exist

A user has credentials in both `~/Desktop/.env` and `~/Desktop/work/.env`. The role-level `.env` contains an override for a variable also present in the base `.env`.

Questions the proposal must answer:
- Does start.sh source base `.env` first and then role `.env`, allowing role-level values to override?
- Are both sourced before any context output begins?
- What happens if either `.env` does not exist — does the script error, or does it skip silently?

Metric cross-references: M-04 (env sourcing implied by start.sh requirements)

---

### 7. Session where no files change

A user opens a role directory, reads context, asks questions, makes no file changes, and closes Cursor. No new commits are generated.

Questions the proposal must answer:
- Does end.sh detect no staged changes via `git diff --cached --quiet` and exit without creating an empty commit?
- Does post-commit.sh not fire at all (since there is no new commit)?
- Does start.sh still pull and inject context normally?

Metric cross-references: M-05

---

### 8. User opens the base directory as workspace root

A user opens `~/Desktop/` in Cursor — the base directory, not a Role directory. `start.sh` fires with `$PWD = ~/Desktop`. `basename "$PWD"` resolves to `Desktop`; `dirname "$PWD"` resolves to `/Users/user`. There is no `ROLE.md` at `~/Desktop/ROLE.md`. `SELF.md` would be sought at `/Users/user/personal/SELF.md` — which does not exist.

Questions the proposal must answer:
- What does start.sh output? Does it emit `=== GLOBAL AGENTS ===` (the symlink at `~/Desktop/AGENTS.md` exists) but then fail on `=== SELF ===` and `=== ROLE ===` because neither file is at the derived paths?
- Does the proposal define explicit behavior for this failure mode — a warning, an error, or silent partial output?
- Does end.sh attempt to commit to `~/Desktop/` as a git repo — and what happens when it isn't one?
- Is there any observable signal to the user that the session is broken?

Metric cross-references: M-01, M-02, M-03

---

### 9. User opens a task folder as workspace root

A user opens `~/Desktop/work/vcpu-analysis/` in Cursor — a task folder inside a Role, not the Role directory itself. `basename "$PWD"` resolves to `vcpu-analysis`; `dirname "$PWD"` resolves to `~/Desktop/work`. There is no `ROLE.md` in `vcpu-analysis/`. `SELF.md` would be sought at `~/Desktop/work/personal/SELF.md` — which does not exist.

Questions the proposal must answer:
- Does start.sh silently inject wrong or empty always-emitted sections — or does it produce a visible failure?
- Does end.sh attempt to commit inside `vcpu-analysis/`, which is not its own git repo?
- Would a user in this session receive any work identity, credentials, or context from the prompt stack?
- Does the proposal address this failure mode in the edge cases section, and what is the recommended user-facing behavior?

Metric cross-references: M-01, M-02, M-03

---

### 10. Work session reads from personal memory, writes to work memory

During a `work/` session the user asks about a colleague, Frank Zdarsky, whose profile was written during a personal session and lives at `personal/Memory/People/frank-zdarsky.md`. The work session's prompt stack does not inject `personal/Memory/INDEX.md` — only `work/Memory/INDEX.md` is injected at session start. Later in the session, the agent learns Frank has moved to a new role and records this new fact.

Questions the proposal must answer:
- How does the agent in a work session know to look in `personal/Memory/` for Frank's file? Does it rely on AGENTS.md instructions, on the Memory/INDEX.md injected at start, or on another mechanism?
- When the agent writes the update about Frank's new role, does it write to `work/Memory/People/frank-zdarsky.md` (write-local, correct) or to `personal/Memory/People/frank-zdarsky.md` (write-to-personal from work session, violation)?
- Does the session-end hook commit the new `work/Memory/` file to the work repo, not the personal repo?
- Does the proposal's AGENTS.md or hook design make the global-read / write-local rule visible to the agent at session start?

Metric cross-references: S-04 (system-level write-local), M-04 (pull includes personal/ for SELF.md — but not personal/Memory/)

---

## Stress Tests

**T1 Role/base always from `$PWD`, never hardcoded.**  
The proposal must derive `ROLE` as `basename "$PWD"` and `BASE` as `dirname "$PWD"` in all three scripts. No paths are constructed from hardcoded strings or environment variables other than the derivation from `$PWD`.  
Pass: no script contains a literal path string for base or role name.

**T2 Context injection order is exact.**  
start.sh emits all eight labelled headers in this exact sequence: GLOBAL AGENTS, SELF, ROLE, ROLE AGENTS, CONTEXT, ARCHIVE INDEX, MEMORY INDEX, REFERENCE INDEX.  
Pass: a grep of the output or the script's cat order matches this sequence; no reordering is present.

**T3 Conditional sections are guarded; always-emitted sections are not.**  
The 5 conditional sections (`=== ROLE AGENTS ===`, `=== CONTEXT ===`, `=== ARCHIVE INDEX ===`, `=== MEMORY INDEX ===`, `=== REFERENCE INDEX ===`) appear in output only when the corresponding file exists. The 3 always-emitted sections (`=== GLOBAL AGENTS ===`, `=== SELF ===`, `=== ROLE ===`) are not wrapped in a file-existence guard.  
Pass: the script uses `[[ -f ... ]]` (or equivalent) before each of the 5 conditional sections; the 3 always-emitted sections use an unconditional `cat`; no always-emitted section is silently skipped.

**T4 Pull before inject.**  
start.sh pulls both repos before any `echo` or `cat` context output. The pull commands appear before the first context injection line.  
Pass: in the script source, both `git pull` lines precede any `echo "=== ..."` or `cat` line.

**T5 Commit only when staged changes exist.**  
end.sh's commit is guarded by `git diff --cached --quiet` or an equivalent that suppresses the commit when nothing is staged.  
Pass: the script does not call `git commit` unconditionally; an empty-cache session produces no commit.

**T6 Every git operation in all three scripts fails silently.**  
All git calls in start.sh, end.sh, and post-commit.sh are followed by `2>/dev/null || true` or equivalent.  
Pass: no git operation can propagate a non-zero exit code or print to stderr unconditionally.

**T7 Post-commit is a no-op when no Memory files changed.**  
When neither `CHANGED` nor `DELETED` lists any Memory file, post-commit.sh exits 0 immediately and does not invoke `masks index`.  
Pass: the script contains a guard that exits 0 before the `masks index` call when both diff outputs are empty.

**T8 Post-commit detects deletions via `--name-status | awk '/^D/'`.**  
The proposal uses the `git diff --name-status ... | awk '/^D/{print $2}'` pattern (or functionally equivalent logic that specifically identifies deleted files) rather than relying solely on `--name-only`.  
Pass: deleted-file detection uses status-based parsing, not presence in the changed-file list alone.

**T9 Wrong workspace root produces an observable failure, not silent wrong output.**  
When start.sh fires from a non-Role directory (base directory or task subfolder), the proposal defines a behavior — warning output, error message, or at minimum the absence of always-emitted sections — that makes the misconfiguration visible rather than silently injecting wrong context.  
Pass: the proposal's edge cases section explicitly addresses this case; a proposal that silently emits `=== GLOBAL AGENTS ===` and nothing else with no indication of failure does not pass this test.

**T10 Memory files written during a work session land in the work repo.**  
Files written to `work/Memory/` during a work session are committed and pushed by the session-end hook to the work git remote, not the personal remote. The personal repo receives no new commits.  
Pass: after a work session that creates a Memory file, `git log` on the personal repo shows no new commits; the new file appears only in the work repo history.

---

## Anti-Pattern Regression Signals

**Hook aborts on git failure.** Any git operation in a hook causes the entire script to exit non-zero, aborting the session lifecycle. Symptom: users see error output in Cursor when git push fails; session-end hook sometimes does not complete. Indicates: missing `|| true` or `set -e` left active. Maps to: M-06.

**Missing optional files produce empty labelled sections.** start.sh emits `=== CONTEXT ===` followed by blank output when `CONTEXT.md` does not exist, rather than skipping the section. Symptom: prompt stack contains empty-headed sections that consume tokens with no value. Indicates: unconditional `cat` without file-existence check. Maps to: M-03.

**Role or base derived from a parameter instead of `$PWD`.** Scripts accept a role name argument or read from an environment variable rather than computing from `$PWD`. Symptom: hooks behave correctly only when the environment matches the workspace; mismatch causes wrong context to be injected. Indicates: spec constraint M-01 violated. Maps to: M-01.

**Pull after context injection.** start.sh outputs context before completing the `git pull` calls. Symptom: sessions start with stale context that is only corrected after the pull completes in the background. Indicates: wrong ordering in script source. Maps to: M-04.

**Empty commit created when no changes staged.** end.sh calls `git commit` unconditionally, creating empty "session:" commits that pollute the role's git history. Symptom: `git log work/` shows dozens of session commits with no diff. Indicates: missing `git diff --cached --quiet` guard. Maps to: M-05.

**Wrong workspace root fails silently.** When start.sh fires from the base directory or a task subfolder, the script runs to completion without error but injects broken or empty context — no SELF.md, no ROLE.md, wrong role name. Symptom: the session starts with empty identity and role context; the agent has no behavioral grounding; errors are attributed to the agent rather than to the wrong workspace. Indicates: always-emitted sections have no existence check and no warning when they silently fail. Maps to: M-01, M-02, M-03.
