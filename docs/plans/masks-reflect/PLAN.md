# Proposal: `masks reflect` — Reflection CLI

**Unit:** `masks-reflect`  
**Deliverable:** `cli/masks/reflect.py` (wired from the `masks` Typer entrypoint)  
**Date:** 2026-04-23

---

## 1. Overview

**Division of responsibility**

- `**reflect` skill (separate unit):** All LLM work — scanning `Memory/` across Roles (scoped by the optional `[role]` argument), evaluating evidence thresholds, synthesizing cross-role patterns, drafting the **exact unified diff** for `SELF.md`, and authoring the **full PR title and body** (evidence, rationale, per-change narrative). It emits a **single structured payload** (see §2) and performs no git writes.
- `**masks reflect` (this unit):** Deterministic orchestration only — resolve base path, load environment, invoke the skill subprocess, interpret JSON, enforce guardrails, run **all git operations inside the `personal/` repository only**, call `gh pr create`, and append **one line** to `personal/.reflect.log` on every non–dry-run invocation.

The CLI **never** composes, edits, or templatizes PR title or body text. Anything shown on GitHub comes from `pr_title` and `pr_description` in the skill output (M-02, T2).

**Flow summary**

1. Source env from `$BASE/.env` then `$BASE/personal/.env` (M-08).
2. Invoke skill with base path, personal `SELF.md` path, optional role scope, and paths to all Role `Memory/` trees under `$BASE` (read-only inputs).
3. If `patterns_found` is false → append `REFLECT_OK` line, print a short user-facing message to stdout, exit 0 (M-03).
4. If true → verify `gh` (M-04), verify `personal/` has at least one git remote (M-05), enforce **no existing `reflect/*` branch** (M-09), validate `branch_name` format (M-06), apply diff on a new branch, commit, push, `gh pr create`, append `REFLECT_PR` with URL (M-01, M-07, M-10).

**Key design decision:** Git operations use `**cwd = $BASE/personal/`** (the personal Role repo root). File paths in git commands are **repo-relative** (`SELF.md`, `.reflect.log`), not `personal/SELF.md`, matching how a normal git repo is used. The unit spec’s illustrative `git add personal/SELF.md` is treated as documentation drift; implementation uses `git add SELF.md`.

---

## 2. Skill invocation

**Environment (M-08)** — Before the skill subprocess or any other work, load variables from `$BASE/.env` then `$BASE/personal/.env` into the CLI process environment (same key semantics as shell `source`; implement via a small shell wrapper or a dotenv parser that does not print values).

**Mechanism**

- `masks reflect` runs a **headless subprocess** that packages the same logic as the interactive `reflect` skill, exposed as a CLI entrypoint implemented in the `reflect-skill` / `pirandello` package (exact module path owned by the reflect-skill spec). Invocation shape:
  ```text
  uv run python -m masks_reflect_entry \
    --base "$BASE" \
    --scope-role "${ROLE:-personal}" \
    --output-json "$TMPFILE"
  ```
- The entrypoint **writes only** `$TMPFILE` (or writes JSON to **stdout** after all logs on stderr — implementation choice: **prefer `--output-json` file** to avoid interleaving with progress logs).
- Parent process reads and parses **strict JSON** matching the schema below. Parse errors → log clear error, exit non-zero; **no** git mutations.

**Inputs the skill receives (arguments / env)**


| Input             | Source                                                                                                                                                      |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Base directory    | `$BASE` from `MASKS_BASE` or default `~/Desktop`                                                                                                            |
| Scope role        | CLI arg `[role]` defaulting to `personal` — forwarded for Memory/ scan focus                                                                                |
| `SELF.md` path    | `$BASE/personal/SELF.md`                                                                                                                                    |
| Memory roots      | For each immediate child `$BASE/<name>/` that is a Role directory containing `Memory/`, pass `$BASE/<name>/Memory/`                                         |
| Prior reflect PRs | CLI reads last **50 lines** of `$BASE/personal/.reflect.log`, extracts URLs from `REFLECT_PR` lines, passes as list for disposition lookup inside the skill |


**Structured output schema (JSON)**

```json
{
  "patterns_found": true,
  "proposed_diff": "--- a/SELF.md\n+++ b/SELF.md\n...",
  "pr_title": "Reflect: ...",
  "pr_description": "…markdown body…",
  "branch_name": "reflect/2026-04-23",
  "target_remote": "git@github.com:USER/personal.git"
}
```

- `target_remote`: Skill echoes `git -C "$BASE/personal" remote get-url origin` (or first remote) for traceability; **CLI does not trust it for pushes** — it uses the repo’s configured `origin` when pushing.
- If `patterns_found` is false, other fields may be null or omitted; CLI ignores them.

`**--dry-run`:** Skill still runs fully so the user sees real model output; CLI skips all mutating steps (§6).

---

## 3. Branch and commit flow

All commands below assume `**cd "$BASE/personal"`** unless noted.

**Preflight when `patterns_found` is true (order matters)**

Stress test **T4** requires `**gh` before any `git` subprocess** (and before branch/diff). After `gh` is confirmed, use **filesystem inspection of `.git/`** for the next two guards so **no-remote** and **duplicate-branch** paths never invoke the `git` binary (scenario 4: no git operations when personal has no remote).

1. `**gh` on PATH (M-04)** — `shutil.which("gh")` is the **first** step. If missing: stderr message includes install hint (`https://cli.github.com/`), exit non-zero — **no** `git`, **no** branch/diff/commit.
2. **Remote present (M-05)** — Parse `$BASE/personal/.git/config` (or equivalent) for any `[remote "..."]` section. If none → stderr:
  `warning: no remote configured for personal/ — cannot open PR`  
   append `REFLECT_SKIP` (§5), exit 0 — **no** `git` subprocess, **no** diff applied.
3. **Duplicate `reflect/`* guard (M-09)** — Without calling `git`, scan:
  - `$BASE/personal/.git/refs/heads/reflect/`* (local branch refs)
  - `$BASE/personal/.git/refs/remotes/*/reflect/*` (remote-tracking refs, any remote name)
  - `$BASE/personal/.git/packed-refs` for lines beginning with commit hash and `refs/heads/reflect/` or `refs/remotes/` containing `/reflect/`
   If any exist → stderr:  
   `reflect: a reflect/* branch already exists — resolve or delete it before running reflect again`  
   append `REFLECT_SKIP` log line (§5), exit 0 — **no** mutating git yet.
  - *Rationale:* Stress test T7; scenario 5 (prior reflect branch still present).
4. `**branch_name` validation (M-06)** — Must match `^reflect/\d{4}-\d{2}-\d{2}$`. If not: stderr error, exit non-zero (do not silently rename — forces skill contract).

**Branch creation**

```bash
git fetch origin --prune
git checkout main
git pull --ff-only origin main
git checkout -b "$BRANCH"
```

**Apply diff**

1. Write `proposed_diff` bytes to a temp file `$patch` **without** line-ending alteration.
2. Ensure working tree clean on `main` (`git status --porcelain` empty) before mutating; else abort non-zero.
3. On `main`: `git apply --check "$patch"`. On failure: stderr explains malformed patch, exit non-zero.
4. `git checkout -b "$BRANCH"`
5. `git apply "$patch"`

If `git apply` fails after branch creation: `git reset --hard`, `git checkout main`, `git branch -D "$BRANCH"`, exit non-zero.

**Commit**

```bash
git add SELF.md
git commit -m "reflect: proposed SELF.md update $(date +%Y-%m-%d)"
```

Commit message date uses **local** `YYYY-MM-DD` (same as branch date convention).

**Push**

```bash
git push -u origin "$BRANCH"
```

- Auth/network failures: **non-zero exit**, stderr from git reproduced — no silent swallow (unit hard constraint 9).
- **Never** commit on `main` (M-01): the only commit containing the diff is on `reflect/`*.

---

## 4. PR creation

**Invocation**

- Body passed via file to preserve bytes and avoid shell escaping:
  ```bash
  gh pr create \
    --repo "$(git remote get-url origin)" \
    --base main \
    --head "$BRANCH" \
    --title "$(cat "$TITLE_FILE")" \
    --body-file "$BODY_FILE"
  ```
- `pr_title` and `pr_description` from JSON are written to `$TITLE_FILE` / `$BODY_FILE` with **UTF-8, newline `\n`**; no trimming unless the skill output is invalid empty (empty title → CLI error, exit non-zero before `gh`).
- `--repo` flag ensures correct target even if `gh` default repo differs.

**Capture URL**

- Parse stdout of `gh pr create` (last line is typically the URL). Regex: `^https://github\.com/.+/pull/[0-9]+$`.
- Optionally run `gh pr view --json number,url` for confirmation — if URL missing, exit non-zero.

**Logging**

- Append to `$BASE/personal/.reflect.log`:  
`REFLECT_PR [ISO-8601 UTC timestamp] [URL]`  
Optionally extend with PR number as third field for simpler tooling:  
`REFLECT_PR [timestamp] [URL] [number]`  
Skill disposition logic can parse URL or number for `gh pr view` (M-10, scenario 7).

---

## 5. Log format

**Location:** `$BASE/personal/.reflect.log` (append-only text, one line per **non–dry-run** invocation).


| Prefix         | When                                            | Line format                                                                        |
| -------------- | ----------------------------------------------- | ---------------------------------------------------------------------------------- |
| `REFLECT_OK`   | `patterns_found == false`                       | `REFLECT_OK [ISO-8601 UTC]`                                                        |
| `REFLECT_PR`   | PR opened successfully                          | `REFLECT_PR [ISO-8601 UTC] [PR URL]` optional `[PR_NUMBER]`                        |
| `REFLECT_SKIP` | Exit 0 without PR (no remote, duplicate branch) | `REFLECT_SKIP [ISO-8601 UTC] reason=<no_personal_remote|duplicate_reflect_branch>` |


**Notes**

- **Dry-run (`--dry-run`):** **No** log line appended — matches stress test T8 and scenario 6; stdout-only preview. This is the explicit exception to the narrow reading of M-07 (“every run”) documented in §7.
- **User-facing stdout:** Always print a one-line summary: e.g. `OK: no changes proposed`, `SKIP: duplicate reflect branch`, `CREATED: <url>`.

---

## 6. Failure modes


| Condition                                          | Behavior                                                                                                                            |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Skill JSON missing / invalid                       | Stderr: parse error; exit non-zero; no git                                                                                          |
| `patterns_found: false`                            | Log `REFLECT_OK`; message to stdout; exit 0                                                                                         |
| `--dry-run`                                        | Print `branch_name`, full `proposed_diff`, `pr_title` (and optionally first ~500 chars of body note); **no** git, **no** log append |
| `gh` not on PATH (and patterns true)               | Stderr install hint; exit non-zero **before** branch creation (M-04, T4)                                                            |
| No git remote in `personal/`                       | Stderr warning exact text per spec; log `REFLECT_SKIP`; exit 0; **no** git (M-05, scenario 4)                                       |
| Any `reflect/`* local or `origin/reflect/*` exists | Stderr warning; log `REFLECT_SKIP` duplicate; exit 0 (M-09)                                                                         |
| `branch_name` invalid format                       | Stderr; exit non-zero                                                                                                               |
| Working tree dirty on `main` before run            | Stderr: abort; exit non-zero (avoid committing unrelated changes)                                                                   |
| `git apply --check` / `git apply` fails            | Stderr shows git/apply output; restore branch state; exit non-zero; `SELF.md` must match pre-run content                            |
| `git push` fails                                   | Stderr; exit non-zero; branch may exist locally — user resolves network/auth                                                        |
| `gh pr create` fails                               | Stderr; exit non-zero; branch pushed but no PR — user may open manually (document in error)                                         |
| `git pull --ff-only` fails                         | Stderr; exit non-zero                                                                                                               |


**Contrast with hooks:** Non-critical failures here are **not** silently ignored (unit hard constraint 9). Only the **no-remote** case uses exit 0 by design (M-05).

---

## 7. Open decisions


| Topic                                                  | Resolution                                                                                                                                                                                                                                         |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Poll PR merge/close status in `masks reflect`?         | **No.** Unit hard constraint 10 — human merges or closes; no monitoring loop.                                                                                                                                                                      |
| Record PR ID for disposition?                          | **Yes** — log line includes URL and optionally number (M-10).                                                                                                                                                                                      |
| How does `reflect` skill learn PR was closed unmerged? | **Skill-owned:** On subsequent runs, skill reads `REFLECT_PR` lines from `.reflect.log`, runs `gh pr view <url                                                                                                                                     |
| Malformed `proposed_diff`?                             | `**git apply --check*`* gate; failure → non-zero exit, no commit, working tree restored.                                                                                                                                                           |
| Timezone for `YYYY-MM-DD` in branch?                   | **Local system date** at invocation (`datetime.date.today()` in local TZ) — matches user expectation in T5.                                                                                                                                        |
| Idempotent double-run after successful PR?             | Second run while `reflect/`* still exists hits **REFLECT_SKIP** duplicate guard (M-09). After merge + branch delete, second run may open a new PR if skill still finds patterns — skill must use disposition signals to avoid duplicate proposals. |
| M-07 vs dry-run                                        | **Explicit exception:** `--dry-run` writes **no** log line (T8). All other invocations append exactly one line.                                                                                                                                    |


---

## 8. Self-check table

### Unit metrics (`docs/specs/masks-reflect/SPEC.md`)


| ID   | Result      | Evidence in proposal                                                                                                                                                |
| ---- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| M-01 | Pass        | Diff applied only on `reflect/`* branch after `main` fast-forward; never commit on `main` (§3).                                                                     |
| M-02 | Pass        | `gh pr create` uses only skill `pr_title` / `pr_description` files (§4).                                                                                            |
| M-03 | Pass        | `patterns_found` false → `REFLECT_OK` + exit 0, no git (§5–6).                                                                                                      |
| M-04 | Pass        | `gh` checked before branch/diff when patterns true (§3 order).                                                                                                      |
| M-05 | Pass        | No remote → warning string per spec, exit 0, no git (§3, §6).                                                                                                       |
| M-06 | Pass        | Regex validation `reflect/YYYY-MM-DD` (§3).                                                                                                                         |
| M-07 | Conditional | Pass for all non–dry-run runs (one line). **Exception:** `--dry-run` appends nothing (§5, §7) — aligns with T8; narrow M-07 text superseded by dry-run stress test. |
| M-08 | Pass        | `$BASE/.env` then `$BASE/personal/.env` loaded first (§1–2).                                                                                                        |
| M-09 | Pass        | Any `reflect/`* local or `origin/reflect/*` blocks with warning + exit 0 (§3).                                                                                      |
| M-10 | Pass        | `REFLECT_PR` logs URL + optional number for `gh pr view` (§4–5, §7).                                                                                                |


### Top-level metrics (`docs/SPEC.md`)


| ID   | Result | Evidence                                                                                                                                                                            |
| ---- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S-01 | Pass   | Proposal contains no personal data or credentials.                                                                                                                                  |
| S-02 | Pass   | No mcp-memory / DB as truth; reflect touches `SELF.md` file only.                                                                                                                   |
| S-03 | Pass   | On-demand CLI; not a “must happen every session” hook behavior.                                                                                                                     |
| S-04 | Pass   | Git writes only in `personal/` repo; skill given read paths to other Roles’ Memory/ only (reflect skill obeys read-only cross-role reads; CLI never writes other Roles’ `Memory/`). |
| S-05 | Pass   | Re-running is safe: duplicate branch → REFLECT_SKIP exit 0; REFLECT_OK idempotent; failed mid-run may leave branch — user-facing error, not corruption of `main`.                   |
| S-06 | Pass   | Only PR path updates `SELF.md`; no agent direct commit to `main` (§3).                                                                                                              |
| S-07 | Pass   | Proposal does not expand `SELF.md` beyond skill diff; skill unit must enforce ≤500 tokens — CLI does not alter content.                                                             |


---

## Implementation notes for `reflect.py`

- **CLI flags:** `masks reflect [role] [--dry-run]` — `role` optional, default `personal`.
- **Dependencies:** stdlib + `typer` (or click) consistent with rest of `masks` CLI; subprocess for skill; `shutil.which` for `gh`.
- **Testing hooks:** Allow `MASKS_REFLECT_SKILL_CMD` env override for tests to mock JSON output without LLM.

---

*End of proposal.*