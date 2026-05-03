# SDD Scenarios: Session Hooks

**Companion spec:** `docs/specs/session-hooks/SPEC.md`
**Date:** 2026-05-03

---

## Use Cases

### 1. Normal session start

A user opens `~/Desktop/work/` in Cursor. Both `work/` and `personal/` have git remotes. `start.sh` fires.

Questions the proposal must answer:
- Does start.sh complete both `git pull` operations before emitting any output?
- Does the emitted prompt name identity/values, current priorities, and task-relevant context as search targets?
- Does the agent receive the prompt as session-start context and search MCP memory before responding to the first user message?

Metric cross-references: M-01, M-02, M-03

---

### 2. Session where no files change

A user opens a role directory, reads context via memory search, asks questions, makes no file changes, and closes Cursor.

Questions the proposal must answer:
- Does end.sh detect no staged changes via `git diff --cached --quiet` and exit without creating an empty commit?
- Does the hook exit 0 cleanly with no side effects?

Metric cross-references: M-04

---

### 3. No remote configured — push fails silently

A user has a local-only Role with no git remote. The session ends with modified files. end.sh commits and then attempts to push.

Questions the proposal must answer:
- Does the push failure produce no error output, no exit code propagation, and no disruption to the Cursor session?
- Does the commit still succeed even though push fails?
- Does the hook exit 0 even when push errors?

Metric cross-references: M-05

---

### 4. personal/ repo absent

A user's base directory has only a `work/` role — there is no `personal/` directory. `start.sh` fires from `work/`.

Questions the proposal must answer:
- Does start.sh skip the `personal/` pull without error when `$BASE/personal/.git` does not exist?
- Does the memory-retrieval prompt still emit normally?

Metric cross-references: M-02, M-05

---

### 5. Session ends while offline

A user makes meaningful changes, closes Cursor while disconnected from the internet. `end.sh` fires.

Questions the proposal must answer:
- Does `git add -A` and `git commit` succeed locally even with no network?
- Does `git push` fail silently without aborting the hook or leaving the session in a broken state?
- Are the committed changes preserved locally for the next push?

Metric cross-references: M-04, M-05

---

## Stress Tests

**T1 Pull completes before any output.**
The two `git pull` calls in start.sh appear before any `echo`, `cat`, or heredoc output in the script source.
Pass: in the script source, both `git pull` lines precede the memory-retrieval prompt output.

**T2 Memory-retrieval prompt names correct search topics.**
The emitted prompt explicitly names at minimum: identity/values, current priorities/active work, and project/task context.
Pass: the prompt text contains all three topic categories; a prompt that mentions only one topic does not pass.

**T3 Commit only when staged changes exist.**
end.sh's commit is guarded by `git diff --cached --quiet` or equivalent that suppresses the commit when nothing is staged.
Pass: the script does not call `git commit` unconditionally; an empty-cache session produces no commit.

**T4 Every git operation fails silently.**
All git calls in start.sh and end.sh are followed by `2>/dev/null || true` or equivalent.
Pass: no git operation can propagate a non-zero exit code or print to stderr unconditionally.

---

## Anti-Pattern Regression Signals

**Hook aborts on git failure.** Any git operation causes the entire script to exit non-zero, aborting the session lifecycle. Symptom: users see error output in Cursor when git push fails. Indicates: missing `|| true` or `set -e` left active. Maps to: M-05.

**Prompt emitted before pull completes.** start.sh outputs the memory-retrieval prompt before finishing both git pulls, meaning the agent may act on stale local content. Symptom: the agent retrieves memory context before the repo is up to date. Indicates: wrong ordering in script source. Maps to: M-02.

**Empty commit created when no changes staged.** end.sh calls `git commit` unconditionally, creating empty "session:" commits that pollute the role's git history. Symptom: `git log work/` shows dozens of session commits with no diff. Indicates: missing `git diff --cached --quiet` guard. Maps to: M-04.
