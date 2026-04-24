# Proposal: `reflect` Skill

**Unit:** `docs/specs/reflect-skill/SPEC.md`  
**Deliverable:** `skills/reflect/SKILL.md` (plus conventions referenced there)  
**Date:** 2026-04-23

---

## 1. Overview

The `reflect` skill is the **LLM-only** half of the reflection ritual. It gathers evidence from markdown memory files across Roles, compares them to the current `SELF.md` draft in the personal Role, and decides whether any **cross-role behavioral patterns** merit a revision to `SELF.md`. When they do, it emits a **unified diff** for `SELF.md`, a **complete PR body** (with evidence, rationale, and trim plan), and **structured metadata** (`patterns_found`, `branch_name`, `target_remote`, `pr_title`) for `masks reflect` to turn into a branch, commit, push, and `gh pr create`.

**Division of labor (hard boundary):**

| Responsibility | Owner |
|----------------|--------|
| Discover `$BASE`, enumerate Role directories, list `Memory/**/*.md`, read `personal/SELF.md` | Skill (via paths supplied by invoker or resolved from `MASKS_BASE`) |
| Pattern clustering, threshold checks, cross-role filter, token budget, diff + PR text generation | Skill |
| Parse `personal/.git/config` for `remote "origin" url` (no `git` subprocess for remotes) | Skill — file read only |
| Signal `no_patterns` outcome in JSON (`{"patterns_found":false,"reason":"…"}`); log write is CLI responsibility | Skill (JSON only) |
| Create branch, apply diff, commit, push, `gh pr create`, log `REFLECT_PR` | `masks reflect` CLI only |

The skill **never** runs `git`, `gh`, writes `SELF.md` on disk, or writes to `personal/.reflect.log`. It has **no filesystem side effects** — all log writes are owned by `masks reflect` CLI, which appends exactly one line per non–dry-run run.

**Invocation:**

- **`masks reflect [role]`:** CLI runs the skill headlessly; structured result is JSON on stdout (or a temp file path agreed with `reflect.py`). No chat confirmation.
- **Direct user request** (“reflect on my sessions”): Skill follows the **confirmation path** (Section 5): plain-language summary first, then full artifact after explicit user go-ahead.

**Inputs the CLI must pass** (environment or flags), so the skill does not depend on workspace root guessing:

- `MASKS_BASE` — base directory (default `~/Desktop` resolved by CLI).
- `REFLECT_SCOPE_ROLE` — optional; if set (e.g. `work`), the skill **reads only** `[base]/[role]/Memory/**` plus always `personal/Memory/**` and `personal/SELF.md` for diff baseline. If unset, it reads **every** Role directory under `$BASE` that contains `Memory/` (excluding non-Role clutter).

**Prior editorial decisions:** The skill reads **`$BASE/personal/.reflect-dispositions.json`** if present (see Overview addendum below). That file is the canonical “memory of outcomes” for reflect PRs. **Population of this file is owned by `masks reflect`** (after PR creation and when PR status is recorded); the skill only **consumes** it so it never silently re-proposes declined patterns.

**Addendum — `.reflect-dispositions.json` schema (contract with CLI):**

```json
{
  "version": 1,
  "entries": [
    {
      "pattern_fingerprint": "sha256:…",
      "pr_url": "https://github.com/…",
      "state": "open" | "merged" | "closed_unmerged",
      "closed_at": "2026-01-15T…Z",
      "summary": "short human label for the pattern"
    }
  ]
}
```

Fingerprints are computed by the skill as **SHA-256 of normalized UTF-8 text**: lowercase, collapse whitespace, strip punctuation except hyphens, of the **proposed SELF.md bullet sentence** (the core claim), not the whole file. When evaluating a candidate pattern, if a **closed_unmerged** entry exists with the same fingerprint, the skill **must not** emit that pattern as a silent new addition; it either **drops** it or **includes** it only inside the PR description under **“Previously declined”** with PR URL, close date, and a fresh rationale for why the user should reconsider (scenario 8 / stress T10).

---

## 2. Pattern detection logic

### 2.1 Corpus construction

1. Resolve `$BASE` from `MASKS_BASE`.
2. Enumerate target Roles per `REFLECT_SCOPE_ROLE` / all Roles.
3. For each Role `R`, read all `R/Memory/**/*.md` (skip `INDEX.md`).
4. Read `personal/SELF.md` in full (baseline for diff).

Memory files are **canonical**; mcp-memory is not consulted (top-level spec S-02).

### 2.2 What counts as a “session”

A **session instance** supporting a pattern is a pair **`(role_name, session_date)`** where `session_date` is a calendar date `YYYY-MM-DD` derived in this order:

1. **YAML frontmatter** `sessions:` list if present:

   ```yaml
   sessions:
     - role: work
       date: 2026-04-10
   ```

2. Else **inline tag** in the body: a line matching `**Session:** YYYY-MM-DD` or `**Observed:** YYYY-MM-DD` (case-insensitive `Session`/`Observed`), scoped to the file’s Role `R`.

3. Else **git fallback** (only when the skill is run with `REFLECT_ALLOW_GIT_META=1` by CLI — optional): last author commit dates touching that file in `R`’s repo, one date = one session per Role per file. If git is disallowed, missing dates mean **that file cannot contribute session counts** (still usable for thematic clustering with 0 session weight — effectively excluded from threshold).

**Distinct session count** for a pattern = count of **unique** `(role_name, session_date)` tuples across all memory snippets that support the pattern.

**Distinct Role count** = count of unique `role_name` among those tuples.

### 2.3 Pattern clustering (LLM + structure)

1. **Extract** atomic observations from the corpus (bullet-level: behaviors, preferences, recurring decisions). Attach each observation with its `(role, path relative to Memory/, session dates from that file)`.

2. **Cluster** observations into **candidate patterns** — one-sentence behavioral claims suitable for `SELF.md` (e.g. “You tend to restructure long documents into a short summary before sharing.”).

3. **Threshold filter (hard):** A candidate is **eligible for SELF.md** only if  
   **sessions ≥ 3** OR **roles ≥ 2**  
   using the distinct-session and distinct-role definitions above.

4. **One-off filter:** Observations that cannot be grouped with any other observation in the same cluster **and** fail the threshold are discarded.

5. **Cross-role filter (hard):** Among eligible clusters, **SELF.md additions** are only those with **≥ 2 distinct Roles** in evidence.  
   If a cluster has **≥ 3 sessions** but **only one Role** (e.g. six work sessions, zero personal), it is **not** proposed for `SELF.md`; it is routed to **`role_md_suggestion`** output: proposed bullet(s) for **`[that_role]/ROLE.md`** only, with the same evidence table in the PR description under a subsection **“ROLE.md suggestions (not part of SELF.md merge)”** so the human can edit ROLE.md separately (no automatic ROLE commit in this skill — text only). This satisfies M-02 and scenario 5.

6. **Disposition filter:** Apply `.reflect-dispositions.json` rules from Section 1 for `closed_unmerged` fingerprints.

### 2.4 Distinguishing patterns from noise

- **Contradictory clusters** (e.g. “prefers async” vs “prefers live meetings” with equal weight): **do not** propose either for SELF until one dominates by session count; if tied, **omit** both and log a single line in PR description “Conflicting signals on X — no automated proposal.”
- **Employer/tool-specific** phrasing in the cluster text triggers **ROLE routing** even if multi-role (e.g. product names) — rewrite test: *If the user changed jobs tomorrow, would this sentence still be true?* No → ROLE.md suggestion only.

---

## 3. SELF.md diff construction

### 3.1 Target shape

`SELF.md` follows the design template: `# Self`, then `## Identity`, `## Values`, `## How I communicate`, `## How I think`. Proposed edits **only** touch those sections — no new top-level sections.

### 3.2 Addition format

Each addition is **one or two short bullets** or a **single clause** appended to the most appropriate section (model chooses: communication habit → `How I communicate`, decision style → `How I think`, etc.). Wording must contain **no employer names, tools, or credentials** (design + M-02).

### 3.3 Deletions

Any trim **must** reference exact removed text (line-based unified diff). Triggers for deletion proposals:

- **Superseded:** new pattern contradicts old bullet.
- **Stale:** bullet’s support sessions are all older than 180 days **and** no memory in the last 90 days references the idea.
- **Budget enforcement** (below).

### 3.4 Token budget (hard)

- **Tokenizer:** `tiktoken` encoding `cl100k_base` (same family as common GPT-4 class models) counting **post-merge** full `SELF.md` body.
- **Procedure:**
  1. Start from current `SELF.md`.
  2. Apply proposed deletions first (always frees space).
  3. Apply proposed additions in **priority order**: higher cross-role session count first.
  4. After each addition, re-count; if **> 500 tokens**, **stop** further additions and **either** expand deletions **or** drop lowest-priority addition until ≤ 500.
- **Trim priority when cutting for budget:**
  1. Remove bullets with **weakest evidence** (fewest supporting sessions) among existing SELF content.
  2. Then oldest-supported content (by last memory reference date).
  3. Never delete `Identity` name line unless user explicitly marked optional (default: never propose deleting the opening identity sentence).

**M-04:** Any PR that adds net tokens **must** include an explicit **“Proposed deletions”** subsection in the PR body listing each removal with rationale, even if some deletions are purely budgetary (“make room for higher-signal cross-role pattern”).

### 3.5 Diff artifact

Output `proposed_diff` is a **unified diff** relative to `personal/SELF.md` as of read time, valid for `patch -p1` from `personal/` repo root, with standard `--- a/SELF.md` / `+++ b/SELF.md` paths (CLI strips prefix as needed).

---

## 4. PR description content

The skill generates **`pr_description`** as GitHub-flavored Markdown with **this exact section order and headings:**

1. **`## Summary`** — One paragraph: why this PR exists and how many patterns met the bar.

2. **`## Scope: Memory reviewed`** — Bulleted list of **relative paths** `role/Memory/...` (machine-facing; this section is for the reviewer). **Time period** sentence: earliest and latest **session dates** seen in the corpus (min–max `YYYY-MM-DD`).

3. **`## Evidence threshold`** — Short statement that every **SELF.md** addition satisfies **≥3 sessions OR ≥2 Roles**, and every SELF addition has **≥2 Roles** (cross-role).

4. **`## Proposed additions to SELF.md`** — For each addition:
   - **Pattern:** one-sentence claim.
   - **Evidence:** bullet list of **`Role` + `YYYY-MM-DD`** pairs (and Memory path references allowed here).
   - **Rationale:** why this belongs in cross-role identity per design (“earns a place in the draft”).

5. **`## Proposed deletions from SELF.md`** — For each deletion:
   - **Removed text:** short quote.
   - **Evidence:** which Roles/dates showed absence or contradiction (or “budget trim”).
   - **Rationale:** stale, superseded, or space-making.

6. **`## ROLE.md suggestions (optional)`** — Only if single-role patterns were promoted for ROLE editing; each with evidence (may be single-role).

7. **`## Previously declined patterns`** — Only if this run **re-opens** a previously `closed_unmerged` fingerprint; must cite PR URL and date.

8. **`## Token check`** — Post-merge token count (number) and encoder name.

**Branch / title:** Skill outputs `branch_name: reflect/YYYY-MM-DD` (UTC date at generation time) and `pr_title: reflect: SELF.md update YYYY-MM-DD` (soft alignment with masks-reflect).

**`target_remote`:** Parsed from `personal/.git/config` `[remote "origin"] url = …` via config file read. If missing, return empty string and `patterns_found: false` with reason in stderr for CLI to handle.

**Structured JSON** (stdout for CLI):

```json
{
  "patterns_found": true,
  "target_remote": "git@github.com:user/personal.git",
  "branch_name": "reflect/2026-04-23",
  "pr_title": "reflect: SELF.md update 2026-04-23",
  "proposed_diff": "--- …",
  "pr_description": "# …",
  "role_md_suggestions": [
    { "role": "work", "markdown_block": "…" }
  ]
}
```

When `patterns_found` is false, emit **only** minimal JSON `{"patterns_found":false,"reason":"…"}` after logging (no `proposed_diff` / `pr_description`).

---

## 5. No-pattern path

### 5.1 JSON output (no-pattern)

Emit minimal JSON to stdout:

```json
{"patterns_found": false, "reason": "…"}
```

Include a human-readable `reason` string (e.g. "No pattern met the ≥3-session or cross-role threshold"). **No `proposed_diff`, `pr_title`, `pr_description`, or `branch_name` fields.**

The skill does **not** write to `personal/.reflect.log`. The `REFLECT_OK` log line is written by `masks reflect` CLI after it receives `patterns_found: false` in the JSON response. (System plan §11.1: CLI is the single writer for `.reflect.log`.)

### 5.2 Direct user invocation

Plain-language message only, e.g.:

> I reviewed recent memory across your roles against your current self draft. Nothing met the bar yet (patterns need either three different days of notes or the same theme in two roles). No update is proposed. When you’re ready, you can run the reflect command again later.

**No** mention of log files, memory folders, or git. State that **no pull request** will be opened.

### 5.3 Headless CLI

JSON `patterns_found: false`; CLI mirrors spec by exiting 0 without PR.

### 5.4 Confirmation path (direct invocation, patterns found)

Before emitting JSON or full diff to the orchestrator:

1. Show **two** patterns max in prose, with **how many times** seen (not file paths).
2. Ask: **“Want me to generate the formal diff and PR text for the reflect command?”**
3. Only after **yes** / explicit confirmation, output the full structured artifact. Explain in one sentence: **opening the pull request is done by your reflect automation, not inside this chat.**

---

## 6. Self-check table

### Unit metrics (`docs/specs/reflect-skill/SPEC.md`)

| ID | Result | Note |
|----|--------|------|
| M-01 | Pass | Threshold enforced in §2.3; single-session / single-role clusters cannot reach SELF additions. |
| M-02 | Pass | SELF additions require ≥2 Roles; single-role high-count patterns go to ROLE suggestions only (§2.3.5). |
| M-03 | Pass | tiktoken count enforced ≤500 post-merge (§3.4). |
| M-04 | Pass | Deletions always paired when budget demands; PR documents trims (§3.4, §4). |
| M-05 | Pass | Skill outputs diff + description only; no git write to SELF (§1). |
| M-06 | Pass | PR sections require Role + YYYY-MM-DD per change (§4). |
| M-07 | Pass | Explicit rationale subsection for every addition/deletion (§4). |
| M-08 | Pass | `REFLECT_OK` logged; no PR body/diff in JSON when no patterns (§5). |
| M-09 | Pass | `target_remote` in JSON from `personal/.git/config` parse (§1, §4). |

### Cross-cutting metrics (`docs/SPEC.md`)

| ID | Result | Note |
|----|--------|------|
| S-01 | Pass | Proposal uses placeholders (`user/personal`); no real personal data. |
| S-02 | Pass | Skill reads markdown Memory files only (§2.1). |
| S-03 | Pass | No “every session” behavior delegated to hooks; skill is on-demand. |
| S-04 | Pass | Skill only reads cross-role Memory; writes are log append in `personal/` and structured text — no writes to other Roles’ Memory trees. |
| S-05 | Pass | Skill idempotent in effect: re-run re-analyzes; log appends are acceptable audit trail (CLI may dedupe if desired). |
| S-06 | Pass | No commit path to `SELF.md` (§1). |
| S-07 | Pass | 500-token cap enforced (§3.4). |

---

## Soft constraints coverage

- **Branch naming:** `reflect/YYYY-MM-DD` in structured output (§4).
- **Compact evidence:** Role + date pairs; no long quotations (§4).
- **Direct invocation:** Confirmation and plain language (§5.4, §5.2).
- **User-facing language:** Chat path avoids filesystem jargon (§5).

---

## Implementation note for `SKILL.md`

The runnable skill document in `pirandello/skills/reflect/SKILL.md` should embed: threshold rules, section template for PR body, JSON schema, session definition, token procedure, disposition file contract, and the confirmation path — so an agent executing the skill has a single source of truth consistent with this proposal.
