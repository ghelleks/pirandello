# Proposal: `ooda-orient-synthesis`

**Unit:** `ooda-orient-synthesis`  
**Spec:** `docs/specs/ooda-orient-synthesis/SPEC.md`  
**Status:** draft  
**Date:** 2026-04-23

---

## 1. Overview

`ooda-orient-synthesis` is the **Orient**-phase skill that deliberately exercises Pirandello’s **global-read** rule: it runs with the `personal/` Role as the workspace root, reads curated facts from every Role’s `Memory/` tree under the configured base, and writes **only** cross-cutting pattern summaries into `personal/Memory/Synthesis/`. Those files are the structured input that `masks reflect` / the `reflect` skill consumes when drafting `SELF.md` PRs—this skill never touches `SELF.md`, never opens PRs, and performs no git operations.

**Pipeline placement:** `masks run personal` → pre-flight guards (including `guards/ooda-orient-synthesis.sh`) → if the guard passes, an LLM session loads `personal/OODA.md` and executes the agenda item `ooda-orient-synthesis` → the skill writes/updates synthesis markdown + `personal/Memory/INDEX.md` + `personal/.synthesis.log` → the user’s **session-end hook** (or the next interactive close in `personal/`) commits and pushes `personal/` → later, `masks reflect` reads `personal/Memory/Synthesis/*.md` to build evidence-backed `SELF.md` diffs.

**Operational definition of “cross-role pattern”:** A **candidate pattern** is a recurring behavior, preference, or theme inferred from multiple atomic observations across `Memory/` files (people, projects, decisions, observations). A pattern is **eligible for a synthesis file** only if:

1. **Evidence threshold (HC4):** It is supported by **either** ≥3 distinct **session dates** **or** ≥2 distinct **Role names** in its evidence set (same Role counted once per session date in that Role).
2. **Cross-role filter (HC5):** Evidence spans **≥2 distinct Role names**. If all supporting observations come from a single Role—even ten sessions in `work/`—the pattern is **rejected for `personal/Memory/Synthesis/`** and may appear only in the run summary as a **ROLE.md candidate** for the human/`masks status` path.

This differs from a **role-specific observation**: the latter belongs in that Role’s `Memory/` (written by Observe/Orient skills in that Role). Synthesis is exclusively for **person-level** regularities that show up in more than one Role’s memory. Because every written pattern must satisfy the cross-role filter, **≥2 Roles is mandatory for any new or updated synthesis file**; the ≥3-session branch still matters for clustering strength and for satisfying the spec’s disjunctive threshold in edge cases (e.g. two Roles with only two session dates total still satisfies “≥2 Roles”).

**Soft behaviors:** Under OODA, the skill emits no prompts. Under direct invocation from an interactive `personal/` session, the agent presents a short **pre-write summary** (patterns to add/update, ROLE.md candidates, stale markers) before mutating files.

---

## 2. Guard script

**Deliverable:** `guards/ooda-orient-synthesis.sh` (POSIX-friendly bash; executable).

**Environment:**

- `BASE` — resolved by `masks run` and exported before guards run: the configured Pirandello base directory (e.g. the parent of `personal/`). The guard uses `"$BASE"` only; it does not infer base from `pwd` except optionally to validate paths.
- `SYNTHESIS_DAY` — optional in `$BASE/.env`. Integer **0–6** where **0 = Sunday** through **6 = Saturday**. Default if unset: **0** (Sunday).

**Logic (in order):**

1. **Resolve today’s weekday in local TZ:** `dow=$(date +%w)` (Sunday = 0). If `dow != SYNTHESIS_DAY` (after defaulting), `exit 1`. No log writes, no file reads.
2. **Already-ran-this-week:** Let log path be `"$BASE/personal/.synthesis.log"`. If the file does not exist, continue. If it exists, scan **all** lines matching the synthesis completion pattern (see §7). For each match, parse the **ISO 8601 UTC timestamp** immediately after the opening `SYNTHESIS ` prefix (use `date -u +%Y-%m-%dT%H:%M:%SZ` on write for unambiguous parsing). If **any** such timestamp is **strictly after** `(now - 7 days)` (use shell arithmetic with `date +%s` for comparison), `exit 1`.
3. If both checks pass, `exit 0`.

**Notes:**

- Guard performs **no** `Memory/` traversal and **no** writes—consistent with M-02/M-03 and stress T1.
- Non-synthesis days and “already ran” are **normal** outcomes: `masks run` treats all guards failing as **OODA_OK**, not as an error.

---

## 3. Memory scan

**Workspace / root enforcement (HC1, M-01):**

- When the skill runs, it requires `basename "$PWD"` (or equivalent) to equal `personal` **and** requires `ROLE.md` and `Memory/` to exist relative to `$PWD`. If not, it logs a **warning to stderr** (user-facing message avoids exposing raw paths per top-level soft constraint) and **exits before any read or write**.
- **Base resolution:** `BASE="$(dirname "$PWD")"` (parent of `personal/`). All other Roles are discovered under `"$BASE"`.

**Role discovery (M-04, T2):**

- Enumerate **every immediate child directory** of `"$BASE"` whose name does not start with `.`.
- A directory is a **Role** if it contains a file named `ROLE.md` at its root (matches `design.md` “Minimum Role definition”). This picks up `work/`, `consulting/`, etc., including Roles added after the last synthesis with **no config update**.
- **Order:** Sort Role directory names lexicographically (ASCII) for deterministic scans: `consulting`, `personal`, `work`, …

**Paths scanned per Role:**

- For each Role `R`, read the tree `"$BASE/$R/Memory/"` **recursively** for files ending in `.md`.
- **Exclusions:** Skip `personal/Memory/Synthesis/` when **ingesting raw observations** for new pattern mining—those files are **outputs**, not evidence sources. The skill still reads existing synthesis files for merge/update/stale handling (§5).
- **Symlinks:** Do not follow symlinks into other Roles (defense in depth for custody boundaries).

**Session date inference (HC4, evidence citations):**

For each observation-bearing memory file, compute a **session date** `YYYY-MM-DD` using the first available of:

1. **Front matter:** `session_date:` or `date:` in YAML front matter if present.
2. **Body conventions:** A line matching `**Session date:** YYYY-MM-DD` or `**Observed:** YYYY-MM-DD` (case-sensitive prefix).
3. **Git last modification of that file in the Role repo:** run `git -C "$BASE/$R" log -1 --format=%cs -- "Memory/…"` (path relative to Role root). This gives a defensible proxy when agents did not annotate.

**Role name** for evidence lines is the directory name `$R` (e.g. `work`, `personal`).

**Performance (soft constraint):** The implementation caps **ingestion** at the newest **5000** memory files by **mtime** across all Roles if needed, but the spec target is ≤500 files—implementation should stream and avoid loading full file contents into context at once (e.g. pass summaries + paths into the LLM in batches, or precompute a JSON manifest in a small Python helper colocated with `masks`). For v1, a **deterministic pre-pass** builds a manifest of paths, inferred dates, and one-line summaries from the first heading for the LLM.

---

## 4. Pattern detection

**Inputs:** Manifest of memory files with `{role, rel_path, session_date, summary_snippet, optional tags}`.

**Clustering algorithm (LLM-assisted with deterministic validation):**

1. **Embed / group (conceptual):** The LLM proposes **pattern clusters**: each cluster is a short **pattern name** (title case for heading, kebab-case for filename) and a list of **evidence pointers** `(role, session_date, file_id, one-sentence observation)`.
2. **Dedupe:** Normalize pattern names: lowercase, strip punctuation, collapse whitespace → **canonical key**. Merge clusters that refer to the same underlying behavior.
3. **Threshold filter (HC4, M-05, T3):** Let `S` = count of **distinct session dates** in the cluster (across all roles). Let `R` = count of **distinct Role names**. The cluster **may proceed** only if `(S ≥ 3) ∨ (R ≥ 2)`.
4. **Cross-role filter (HC5, M-06, T4):** If `R < 2`, **drop** the cluster for synthesis output. Emit a **ROLE.md candidate** bullet in the run summary naming the dominant Role and the pattern.
5. **Human-readable description:** One paragraph in cross-role terms (neutral phrasing suitable for `SELF.md` readiness).

**Distinguishing cross-role vs role-specific:** Only the `R ≥ 2` gate controls writes to `personal/Memory/Synthesis/`. A pattern with `S ≥ 3` but `R = 1` is **explicitly excluded** from synthesis files (scenario 4).

**Direct invocation:** The same algorithm runs; the only difference is optional **pre-write summary** to the user (soft constraint).

---

## 5. Synthesis file writes

**Output location:** `personal/Memory/Synthesis/<kebab-pattern-name>.md` (unique per pattern).

**File format (HC6, M-07)** — exact section order:

```markdown
# [Pattern name]

**First observed:** YYYY-MM-DD
**Last observed:** YYYY-MM-DD

## Pattern

[One paragraph — cross-role description.]

## Evidence

- [Role] — YYYY-MM-DD — [One-sentence description of the observation]
- ...
```

**Optional staleness line (HC11, §6):** When marking stale, insert immediately after `**Last observed:**` line:

```markdown
**Status:** stale
```

**Dates:**

- **First observed:** minimum session date across evidence.
- **Last observed:** maximum session date across evidence.

**Naming conflicts:**

- **Primary file name:** derived from normalized kebab of the pattern title; if collision with a **different** pattern title that would kebab the same, append a short disambiguator `-2`, `-3` based on sorted first evidence tuple. In practice, reuse the existing file if the canonical key matches stored `pattern_key` metadata (below).

**Existing files (HC7, M-08, T5):**

- Before creating a new file, load all existing `personal/Memory/Synthesis/*.md`.
- **Stable identity:** Each synthesis file includes YAML front matter at the top (machine-oriented, minimal) storing `pattern_key: <normalized-key>`. When the LLM proposes a cluster whose `pattern_key` matches an existing file, **update that file in place**: merge evidence bullets (union by `(role, session_date, description)`), recompute First/Last observed, refresh the paragraph if needed.
- If an older file lacks `pattern_key`, fall back to **kebab filename match** against the proposed kebab name.

**INDEX.md (HC8, M-09, T6):**

- After writes, update `personal/Memory/INDEX.md` (table format per `design.md`): one row per file under `Memory/Synthesis/` with summary = first sentence of `## Pattern` or the heading; tags include `synthesis`, `cross-role`.

**No git (HC10, M-11, T8):** The skill instructions and helper code for this unit must not invoke `git` for commit, push, branch, or `git add`.

---

## 6. Stale pattern handling

**Definition:** For each existing synthesis file, parse `## Evidence` bullets and determine the **latest session date** cited. If **today’s date minus latest evidence date > 90 days** **and** the current run **adds no new evidence** to that pattern, then:

- Ensure the file contains `**Status:** stale` (HC11, M-12, T9).
- If the file was previously non-stale, count this as an **update** (`M` increment) even if the evidence list is unchanged.
- **Do not delete** the file; preserve full evidence history and original **First observed** (HC11).

**Run summary:** List stale patterns explicitly, e.g. `Stale (marked): early-riser-preference`.

**Downstream (`reflect` skill):** Staleness is **informational in this unit**; the `reflect` skill should treat `**Status:** stale` as **deprioritized or excluded** from automatic `SELF.md` diff proposals unless the user explicitly requests inclusion. (Integration guidance; implemented in the `reflect` unit.)

---

## 7. Log format

**Path:** `personal/.synthesis.log` (append-only).

**Line format (HC9, M-10, T7):** Exactly **one** new line per **completed** skill run (guard bypassed on direct invoke still counts as a run if the skill finishes):

```
SYNTHESIS <ISO-8601-UTC-timestamp> — <N> patterns found, <M> updated
```

**Definitions:**

- **`N`:** Count of **new** synthesis files created this run (patterns with no prior file).
- **`M`:** Count of **existing** synthesis files **updated** this run—including evidence merges, non-stale refreshes of the paragraph, and **stale marking** updates.

**Guard interaction:** If the guard exits non-zero, **no** line is appended (scenario 2). The skill only appends after successful completion **when the skill actually runs**—if the skill aborts early (e.g. wrong workspace), **no** log line is written.

**Direct invocation:** Still appends one line when the skill completes (scenario 8 alignment with “same output”).

---

## 8. Self-check table

### Unit metrics (`docs/specs/ooda-orient-synthesis/SPEC.md`)

| ID   | Result | Note |
|------|--------|------|
| M-01 | Pass | Workspace basename must be `personal`; else warn + exit before I/O. |
| M-02 | Pass | Guard compares `date +%w` to `SYNTHESIS_DAY` (default 0). |
| M-03 | Pass | Guard parses last successful runs from `.synthesis.log`; blocks if any within 7 days. |
| M-04 | Pass | Role discovery enumerates all `$BASE/*/ROLE.md` Roles; scans each `Memory/`. |
| M-05 | Pass | Cluster must satisfy `(sessions ≥ 3) ∨ (roles ≥ 2)`; synthesis files also require cross-role `roles ≥ 2`. |
| M-06 | Pass | `roles < 2` clusters never write to `Synthesis/`; summary only. |
| M-07 | Pass | Exact template: `#`, First/Last, `## Pattern`, `## Evidence`. |
| M-08 | Pass | `pattern_key` + filename tie-break; merge into existing file. |
| M-09 | Pass | `personal/Memory/INDEX.md` updated every successful run touching synthesis files. |
| M-10 | Pass | One append to `.synthesis.log` per completed run with N/M counts. |
| M-11 | Pass | No git commands in skill instructions or helper scripts for this unit. |
| M-12 | Pass | `**Status:** stale` added; no deletions. |

### Top-level metrics (`docs/SPEC.md`)

| ID   | Result | Note |
|------|--------|------|
| S-01 | Pass | Proposal contains no personal data; only describes mechanics. |
| S-02 | Pass | Canonical store is markdown files; DB not used as SoT. |
| S-03 | Pass | “Must happen every session” not claimed here; weekly guard is `masks run` + hook stack. |
| S-04 | Pass | Writes only under `personal/Memory/` from `personal/` workspace; reads global. |
| S-05 | Pass | No new `masks` subcommands; skill/guard idempotent aside from intentional log append per run. |
| S-06 | Pass | No `SELF.md` commits; synthesis feeds `reflect` only. |
| S-07 | Pass | Synthesis paragraphs kept concise; evidence lists are not part of the always-loaded prompt stack. |

---

## Integration checklist

- **`personal/OODA.md`:** Include `ooda-orient-synthesis` only under **Orient**, after observation aggregation skills; never list in `work/OODA.md`.
- **`SKILL.md`:** Documents guard name, workspace rule, manifest generation, cluster validation pseudo-code, file templates, INDEX + log updates, stale rules, and explicit prohibition of git operations.
- **`masks run`:** Ensures `$BASE` and `SYNTHESIS_DAY` are exported before guard execution.

---

## Deliverables summary

| Path | Purpose |
|------|---------|
| `skills/ooda-orient-synthesis/SKILL.md` | Authoritative skill instructions + algorithm |
| `guards/ooda-orient-synthesis.sh` | Day-of-week + 7-day log guard |
| `personal/OODA.md` (user data) | Single Orient agenda item referencing this skill |
