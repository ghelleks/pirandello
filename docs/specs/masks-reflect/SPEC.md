# SDD Spec: `masks reflect` — Reflection CLI

**Context:** See `docs/design.md` for full system design. This spec covers the CLI command that owns the infrastructure side-effects of the reflection ritual: invoking the `reflect` skill, then translating its structured output into a git branch, a committed SELF.md diff, a push, and a GitHub pull request. The `reflect` skill handles all LLM reasoning; `masks reflect` handles all git and GitHub operations.

**Deliverables:** `cli/masks/reflect.py`. Depends on `gh` (GitHub CLI) being installed and authenticated.

---

## Requirements

### Hard constraints

1. Entry point: `masks reflect [role]`. `role` defaults to `personal` if not provided; this argument is passed to the `reflect` skill to scope Memory/ scanning if desired, but the PR always targets the `personal/` remote.
2. Base directory resolved from `MASKS_BASE` environment variable, falling back to `~/Desktop`.
3. Before any operations, sources `$BASE/.env` then `$BASE/personal/.env`.
4. Invokes the `reflect` skill with the paths it needs to read Memory/ content. The skill returns a structured result containing:
   - `patterns_found`: boolean
   - `proposed_diff`: the exact unified diff to apply to `personal/SELF.md`
   - `pr_title`: a short title string
   - `pr_description`: the full PR body (evidence, rationale, per-change sections)
   - `branch_name`: the branch name to create, in the format `reflect/YYYY-MM-DD`
   - `target_remote`: the git remote URL from `personal/`'s git config
5. If `patterns_found` is false: log `REFLECT_OK [ISO timestamp]` to `$BASE/personal/.reflect.log` and exit 0. No branch is created, no PR is opened.
6. If `patterns_found` is true:
   a. Verify that `gh` is installed and on `$PATH`. If not: log a clear error and exit non-zero.
   b. Verify that `personal/` has a git remote configured. If not: log a warning ("no remote configured for personal/ — cannot open PR") and exit 0.
   c. In `$BASE/personal/`, create and checkout the branch named in `branch_name`.
   d. Apply `proposed_diff` to `personal/SELF.md`.
   e. Run `git add personal/SELF.md` and `git commit -m "reflect: proposed SELF.md update YYYY-MM-DD"`.
   f. Run `git push -u origin <branch_name>`.
   g. Run `gh pr create --title <pr_title> --body <pr_description> --base main`.
   h. Capture the PR URL from `gh pr create` output.
   i. Log `REFLECT_PR [ISO timestamp] [PR URL]` to `$BASE/personal/.reflect.log`.
7. **SELF.md is never committed directly on `main`.** The diff is applied only on a `reflect/*` branch. No code path in `masks reflect` commits to `main`.
8. If the branch already exists (a previous reflect run was abandoned without the PR being merged or closed): log a warning and exit 0 without creating a duplicate branch or PR.
9. All git operations that can fail non-critically must fail with a clear error message and non-zero exit, not a silent swallow. (Unlike the interactive hooks, `masks reflect` is an on-demand command where the user expects to know about failures.)
10. `masks reflect` does not merge the PR and does not monitor its status. The human merging or closing the PR is the authorial act.

### Soft constraints

- Designed for on-demand use or a scheduled cadence (monthly is the recommended cadence in the design doc). Not called from cron directly — it is too consequential.
- If the `reflect` skill runs interactively (direct user invocation from a session), the skill may have already summarized findings and received confirmation. `masks reflect` does not re-confirm with the user — it proceeds directly to git operations based on the skill's structured output.
- The `--dry-run` flag (optional) prints the proposed branch name, diff, and PR title without making any git changes. Useful for inspecting what reflect would do.

---

## Proposal format

### 1. Overview
The division of responsibility: skill (LLM reasoning) vs. CLI (git + GitHub operations). How the structured output from the skill drives every CLI action.

### 2. Skill invocation
How `masks reflect` invokes the `reflect` skill. What context paths are passed. How the structured output is received (e.g., stdout as JSON, a temp file, a structured return value).

### 3. Branch and commit flow
The exact git commands run in the personal/ directory. How the branch name is constructed if `branch_name` is not provided by the skill. How the diff is applied (`git apply`, `patch`, direct file write + diff).

### 4. PR creation
The exact `gh pr create` invocation. How the PR title and body are passed (heredoc, temp file, stdin). How the PR URL is captured and logged.

### 5. Log format
The exact format of entries written to `personal/.reflect.log`: the REFLECT_OK line and the REFLECT_PR line.

### 6. Failure modes
What happens for each failure: `gh` not installed, no personal remote, branch already exists, `git push` fails (auth error, branch conflict), `gh pr create` fails.

### 7. Open decisions
Anything the design doc does not fully specify: whether `masks reflect` polls for PR status later, whether it records PR ID for disposition tracking (to support the closed-PR behavior required by the reflect skill), what happens if `proposed_diff` is malformed.

### 8. Self-check table
See Static Evaluation Metrics.

---

## Static evaluation metrics

| ID   | Name                    | Pass condition                                                                                                   |
|------|-------------------------|------------------------------------------------------------------------------------------------------------------|
| M-01 | SELF.md not on main     | No code path in `masks reflect` commits `personal/SELF.md` to the `main` branch                                 |
| M-02 | PR content from skill   | All PR title and body text comes from the reflect skill's structured output; CLI authors no PR content           |
| M-03 | REFLECT_OK on no patterns | When `patterns_found` is false, `REFLECT_OK` is logged and exit 0; no branch, no PR                           |
| M-04 | gh required             | If `gh` is not on `$PATH`, a clear error is logged and the command exits non-zero before any git operation       |
| M-05 | Personal remote required | If `personal/` has no git remote, a warning is logged and the command exits 0 (not an error)                   |
| M-06 | Branch naming           | The created branch always follows `reflect/YYYY-MM-DD` format                                                   |
| M-07 | Log always written      | `personal/.reflect.log` gains one new entry on every run — either `REFLECT_OK` or `REFLECT_PR [URL]`            |
| M-08 | Env sourced             | `$BASE/.env` and `$BASE/personal/.env` are sourced before any operations                                        |
| M-09 | Duplicate branch guard  | If the reflect branch already exists, the command logs a warning and exits 0 without creating a duplicate        |
| M-10 | PR ID recorded          | The PR URL (and optionally the PR number) is written to `personal/.reflect.log` so that disposition tracking (closed vs. merged) is possible for future reflect runs |
