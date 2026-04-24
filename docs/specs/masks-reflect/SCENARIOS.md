# SDD Scenarios: `masks reflect` — Reflection CLI

**Companion spec:** `docs/specs/masks-reflect/SPEC.md`  
**Date:** 2026-04-23

---

## Use Cases

### 1. Normal PR opened — qualifying patterns found

A user runs `masks reflect`. The `reflect` skill finds two qualifying cross-role patterns, produces a proposed SELF.md diff and a complete PR description, and returns its structured output. The `personal/` Role has a remote configured at `git@github.com:user/personal.git`.

Questions the proposal must answer:
- Does `masks reflect` create and checkout `reflect/YYYY-MM-DD` (using today's date) in the `personal/` repo?
- Does it apply the proposed diff to `personal/SELF.md` on that branch?
- Does it commit with a message in the format `reflect: proposed SELF.md update YYYY-MM-DD`?
- Does it push the branch and call `gh pr create` with the skill's title and body?
- Does it log `REFLECT_PR [ISO timestamp] [PR URL]` to `personal/.reflect.log`?
- Is `main` in the personal repo unchanged — no direct commit to SELF.md?

Metric cross-references: M-01, M-02, M-06, M-07, M-10

---

### 2. No qualifying patterns — REFLECT_OK and clean exit

A user runs `masks reflect` on a system that has been active for only two weeks. The `reflect` skill finds no patterns meeting the evidence threshold and returns `patterns_found: false`.

Questions the proposal must answer:
- Does `masks reflect` log `REFLECT_OK [ISO timestamp]` to `personal/.reflect.log` and exit 0?
- Is no branch created in the personal repo?
- Is no PR opened on GitHub?
- Is the clean exit observable to the user — does the command communicate that there was nothing to propose?

Metric cross-references: M-03, M-07

---

### 3. `gh` not installed

A user runs `masks reflect` on a machine where the GitHub CLI (`gh`) is not installed. The skill has already run and returned qualifying patterns. The command discovers `gh` is absent before attempting git operations.

Questions the proposal must answer:
- Does the command detect the absence of `gh` before creating any branch or applying any diff?
- Does it log a clear, human-readable error explaining that `gh` is required and how to install it?
- Does it exit non-zero?
- Is `personal/SELF.md` unchanged — no partial diff applied?

Metric cross-references: M-04

---

### 4. `personal/` has no git remote configured

A user has a local-only `personal/` Role with no remote. The skill returns qualifying patterns. `masks reflect` detects that there is no origin remote in the personal repo.

Questions the proposal must answer:
- Does the command log a warning ("no remote configured for personal/ — cannot open PR") and exit 0, not non-zero?
- Is the user's situation communicated clearly — the absence of a remote is a configuration gap, not an error?
- Is no branch created, no diff applied, no git operations performed?
- Does `personal/.reflect.log` still gain an entry for this run?

Metric cross-references: M-05, M-07

---

### 5. Reflect branch already exists — previous run was abandoned

A user ran `masks reflect` last week, which created `reflect/2026-04-16` and opened a PR. The PR has not yet been merged or closed. The user runs `masks reflect` again today.

Questions the proposal must answer:
- Does the command detect that `reflect/2026-04-16` (or `reflect/2026-04-23`) already exists in the personal repo?
- Does it log a warning ("a reflect branch already exists — resolve the open PR before running reflect again") and exit 0?
- Does it not create a duplicate branch or open a second PR?
- Does the log entry make it clear what the user should do next?

Metric cross-references: M-09

---

### 6. `--dry-run` flag — inspect without committing

A user runs `masks reflect --dry-run` to preview what the command would do before committing to it. The skill runs normally and returns its structured output.

Questions the proposal must answer:
- Does the command print the proposed branch name, the SELF.md diff, and the PR title to stdout?
- Does it perform no git operations — no branch created, no commit, no push, no `gh pr create`?
- Is `personal/.reflect.log` unchanged after a dry run?
- Is the dry-run output clear enough for the user to decide whether to proceed?

Metric cross-references: M-01, M-07 (dry run produces no log entry by design)

---

### 7. PR disposition recorded for future reflect runs

A user runs `masks reflect`, which opens a PR and logs `REFLECT_PR [timestamp] https://github.com/user/personal/pull/12`. Three weeks later the user closes the PR without merging. The `reflect` skill (on its next invocation) needs to know about this closure to avoid re-proposing the same patterns.

Questions the proposal must answer:
- Does `masks reflect` record the PR URL (and optionally the PR number) in `personal/.reflect.log` in a format that the `reflect` skill can later query via the GitHub API or `gh` CLI to determine PR disposition?
- Does the proposal's Open Decisions section address how PR closure is detected by the `reflect` skill on subsequent runs?
- Is the PR ID in the log sufficient for `gh pr view <number> --json state` to return the PR's current status?

Metric cross-references: M-10

---

## Stress Tests

**T1 SELF.md is never committed on main.**  
After any successful `masks reflect` run that opens a PR, `git log main -- personal/SELF.md` shows no new commits. The diff is present only on the `reflect/*` branch.  
Pass: `git diff main..reflect/YYYY-MM-DD -- personal/SELF.md` shows the proposed change; `git log main -- personal/SELF.md` is unchanged.

**T2 All PR content comes from the reflect skill's output.**  
The PR title and body opened by `masks reflect` are identical to what the `reflect` skill returned in its structured output. The CLI adds no text of its own.  
Pass: the PR body on GitHub matches the `pr_description` field in the skill's output byte-for-byte (modulo newline normalization).

**T3 REFLECT_OK logged and no git operations performed when no patterns found.**  
When the reflect skill returns `patterns_found: false`, the command performs no git operations and logs REFLECT_OK.  
Pass: `git log personal/` shows no new commits or branches; `personal/.reflect.log` gains exactly one REFLECT_OK line.

**T4 `gh` absence detected before any git operation.**  
If `gh` is not installed, the command fails before creating a branch, applying a diff, or running any git command.  
Pass: `personal/SELF.md` is unchanged; no new branch exists in the personal repo; error message mentions `gh` specifically.

**T5 Branch follows `reflect/YYYY-MM-DD` naming.**  
The created branch is named `reflect/` followed by the ISO date of the run (YYYY-MM-DD).  
Pass: `git branch -a` in the personal repo shows `reflect/YYYY-MM-DD` with today's date; no other naming convention is used.

**T6 Log is written on every run.**  
Every invocation of `masks reflect` — whether it opens a PR, logs REFLECT_OK, or exits due to a missing remote — appends exactly one line to `personal/.reflect.log`.  
Pass: after five runs (two PRs, two REFLECT_OKs, one missing-remote warning), the log has five entries.

**T7 Duplicate branch causes clean exit, not a crash or second PR.**  
When a `reflect/*` branch already exists in the personal repo, `masks reflect` logs a warning and exits 0 without creating a second branch or a second PR.  
Pass: `gh pr list` shows at most one open reflect PR; the personal repo has at most one `reflect/*` branch at any time.

**T8 Dry run produces no file or git changes.**  
`masks reflect --dry-run` produces console output describing what would happen but makes no changes to any file, any git repo, or the reflect log.  
Pass: a `diff` of all affected directories before and after `--dry-run` shows zero changes.

---

## Anti-Pattern Regression Signals

**SELF.md committed directly on main.** `masks reflect` applies the diff and commits to `main` instead of creating a branch. Symptom: SELF.md changes are immediately live with no review opportunity; the PR-as-ritual pattern is broken; the user loses the ability to reject the proposed change. Indicates: branch creation step missing or skipped; diff committed in place. Maps to: M-01.

**CLI authors PR content.** `masks reflect` writes its own PR title or body text rather than using the reflect skill's output. Symptom: the PR contains a generic template instead of the evidence and rationale the skill produced; the PR ceases to be a record of deliberate synthesis. Indicates: structured output from skill not used; CLI fell back to hardcoded text. Maps to: M-02.

**`gh` absence not caught before git operations.** `masks reflect` creates a branch and commits the diff before discovering that `gh` is unavailable. Symptom: a stale reflect branch exists in the personal repo with a committed SELF.md change but no corresponding PR; the branch must be deleted manually. Indicates: `gh` check not run at entry before any git operations. Maps to: M-04.

**No PR URL in reflect log.** `masks reflect` opens the PR but does not record the PR URL in `personal/.reflect.log`. Symptom: subsequent reflect runs cannot query PR disposition; the reflect skill re-proposes patterns that the user already rejected via a closed PR; the authorial consent record is lost. Indicates: log write does not capture `gh pr create` output. Maps to: M-07, M-10.

**Second PR opened when a reflect branch already exists.** Running `masks reflect` while a previous reflect PR is still open creates a second branch and a second PR with conflicting or duplicate content. Symptom: two open reflect PRs with overlapping diffs; merging either one may create conflicts; the user is confused about which to act on. Indicates: existing-branch check not implemented. Maps to: M-09.
