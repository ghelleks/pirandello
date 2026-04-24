# SDD Scenarios: `reflect` Skill

**Companion spec:** `docs/specs/reflect-skill/spec.md`  
**Date:** 2026-04-23

---

## Use Cases

### 1. Strong cross-role pattern — PR description produced with clear evidence

Over the past two months, Memory files across `work/Memory/` and `personal/Memory/` document a recurring behavior: the user consistently restructures proposals before presenting them, across at least four sessions in the work Role and two in the personal Role. This pattern does not currently appear in `SELF.md`.

Questions the proposal must answer:
- Does the skill identify this pattern as meeting the ≥3-session OR ≥2-Role threshold?
- Does the PR description name the specific session dates and Role names where the pattern appeared?
- Does the proposed SELF.md addition capture a cross-role pattern, not a work-specific behavior?
- Does the PR include a rationale for why this earns a place in SELF.md?

Metric cross-references: M-01, M-02, M-06, M-07, M-09

---

### 2. Candidate pattern appears in only one session of one Role

A Memory file from a single `work/` session documents the user giving direct feedback in a performance review. No other Memory files across any Role reference anything similar.

Questions the proposal must answer:
- Does the skill exclude this from the proposed SELF.md additions?
- Does the PR (if opened) not mention this pattern as a proposed change?
- Is the evidence threshold (≥3 sessions OR ≥2 Roles) enforced before any pattern reaches the PR?

Metric cross-references: M-01

---

### 3. Additions would push SELF.md past 500 tokens

The skill identifies two strong cross-role patterns that should be added to SELF.md. Adding both would bring the document to 620 tokens — 120 tokens over budget.

Questions the proposal must answer:
- Does the PR propose what to trim to make room (not just what to add)?
- Does the PR ensure the proposed SELF.md after additions and trims is ≤500 tokens?
- How does the proposal decide what gets trimmed — oldest content, least-evidenced content, or another criterion?
- Are both the additions and the trims described in the PR description with rationale?

Metric cross-references: M-03, M-04

---

### 4. No patterns meet the evidence threshold

The skill runs on a system that has only been in use for three weeks. No pattern appears in ≥3 distinct sessions or ≥2 distinct Roles. Nothing qualifies for SELF.md.

Questions the proposal must answer:
- Does the skill log `REFLECT_OK` with an ISO timestamp to `$BASE/personal/.reflect.log` and exit without opening a PR?
- If invoked directly (not via `masks reflect`), does it communicate to the user that no qualifying patterns were found — in plain language?
- Is the absence of a PR the correct outcome here, not an error condition?

Metric cross-references: M-08

---

### 5. Pattern is specific to the work Role only

The skill finds a pattern that appears in six work sessions: the user always writes a one-paragraph summary before any longer document. This pattern has never appeared in personal Role sessions.

Questions the proposal must answer:
- Does the skill correctly classify this as a Role-specific pattern rather than a cross-role pattern?
- Does it propose adding this to `work/ROLE.md` or note it as a work pattern, rather than adding it to `SELF.md`?
- Is the proposal's cross-role filter enforced before content reaches the PR?

Metric cross-references: M-02

---

### 6. PR description targets the personal GitHub remote

The skill has identified two qualifying patterns and produces its output. The `personal/` Role's git remote is `git@github.com:user/personal.git`.

Questions the proposal must answer:
- Does the skill's structured output identify the personal Role's remote as the PR destination (for use by `masks reflect` CLI)?
- Does the output specify a branch name following the `reflect/YYYY-MM-DD` pattern?
- Does the PR description contain all required sections: which Memory files were read, the time period, a per-addition rationale, and a per-deletion rationale?

Metric cross-references: M-05, M-06, M-07, M-09

---

### 7. Skill invoked directly by user — confirmation before producing output

A user types "reflect on my sessions" in a Cursor session. The skill identifies two qualifying patterns.

Questions the proposal must answer:
- Does the skill present what it found and what it proposes before producing the final diff and PR description?
- Does it wait for user confirmation (or present the summary for review) rather than immediately emitting output without review?
- Is the communication in plain language, not technical references to Memory file paths or git operations?
- Does the skill communicate clearly that the actual PR will be opened by `masks reflect`, not by the skill itself?

Metric cross-references: M-05, M-07 (user-direct invocation path)

---

### 8. Second reflect run after a previous PR was closed without merging

Three months ago, the reflect skill produced a PR proposing to add "consistently restructures proposals before presenting them" to SELF.md. The user reviewed the PR and closed it without merging — a deliberate editorial decision. The same behavioral pattern has continued to appear across work and personal Memory files in the intervening sessions. The reflect skill now runs again.

Questions the proposal must answer:
- Does the skill detect that a PR proposing this same pattern was previously opened and closed without merging?
- How does the proposal track PR disposition — via the reflect log, the git branch history, a closed-PRs record, or another mechanism?
- Does the skill treat the closed PR as editorial feedback — either omitting the pattern from the new PR entirely, or explicitly surfacing the prior rejection ("this pattern was previously proposed and declined on YYYY-MM-DD") and asking for a deliberate re-decision?
- Would a proposal that blindly re-proposes the same patterns on every run, regardless of prior PR dispositions, violate the design's authorial consent model?
- If the pattern re-appears in the new PR, does the PR description note the previous proposal and its outcome so the user can make an informed decision?

Metric cross-references: M-01 (evidence threshold), M-06 (PR description evidence), M-07 (rationale per change), design intent: "The PR history — accepted proposals, rejected ones, your pre-merge edits — is itself a record of deliberate authorship over time"

---

## Stress Tests

**T1 No proposed change is based on fewer than 3 sessions or fewer than 2 Roles of evidence.**  
Every item in the PR's proposed additions cites ≥3 distinct session dates OR ≥2 distinct Role names as evidence.  
Pass: each proposed change in the PR description names its evidence; any change with only one session or one Role of evidence fails this test.

**T2 All proposed additions are cross-role patterns.**  
No proposed addition to SELF.md describes behavior observed only in one Role.  
Pass: for every proposed addition, the evidence section names at least two Roles; single-Role patterns are absent from the PR.

**T3 Proposed SELF.md is ≤500 tokens after all changes applied.**  
Taking the current SELF.md, applying the PR's proposed additions, and applying the PR's proposed deletions produces a document of ≤500 tokens.  
Pass: token count of the projected post-merge SELF.md is ≤500; the PR fails this test if no trims are proposed when additions would exceed the budget.

**T4 Any PR proposing additions also proposes trims.**  
When SELF.md additions would cause the document to exceed 500 tokens, the PR must propose specific deletions to make room.  
Pass: a PR where additions alone would push SELF.md past 500 tokens includes a Proposed Deletions section; a PR that simply ignores the budget constraint fails.

**T5 Skill produces a diff and PR description; it does not write, commit, or push.**  
The skill's output is a proposed diff and a PR description — not a git branch, not a PR on GitHub. No code path writes to, commits, or pushes `personal/SELF.md` or any branch. The `masks reflect` CLI handles those steps.  
Pass: after running the reflect skill in isolation, `git log personal/SELF.md` shows no new commits and no new remote branches exist; the skill's output is a structured text artifact only.

**T6 PR description names specific evidence for every proposed change.**  
For each addition and deletion, the PR description includes specific session dates or Role names — not vague claims like "observed over time."  
Pass: each entry in the PR's per-change evidence section includes at least one specific date (YYYY-MM-DD format) or Role name.

**T7 Every proposed change has an explicit rationale.**  
The PR description for each addition and deletion includes a rationale statement — why this earns a place in (or should be removed from) SELF.md.  
Pass: no addition or deletion entry in the PR is missing a rationale; entries with only evidence and no rationale fail this test.

**T8 REFLECT_OK logged and no output produced when no patterns qualify.**  
When the skill finds no patterns meeting the threshold, `REFLECT_OK [ISO timestamp]` is written to `$BASE/personal/.reflect.log` and no diff or PR description is produced.  
Pass: the log file contains the REFLECT_OK entry; the skill produces no diff output and no PR description text.

**T9 Skill output identifies the personal Role's remote as the PR destination.**  
The skill's structured output specifies the git remote configured for the `personal/` Role directory — not the work remote, not the pirandello repo — so that `masks reflect` CLI opens the PR in the correct location.  
Pass: the output identifies the personal remote; the skill itself makes no git remote calls.

**T10 Previously closed PR patterns are not silently re-proposed.**  
When a pattern was proposed in a previous PR and that PR was closed without merging, the next reflect run either (a) omits the pattern entirely, or (b) explicitly cites the prior rejection in the PR description and presents a deliberate re-decision opportunity. Silent re-proposal is not acceptable.  
Pass: a reflect run that finds a pattern with a corresponding closed PR either excludes it from the new output or labels it as previously declined; a run that re-proposes the identical change with no reference to the prior PR fails this test.

---

## Anti-Pattern Regression Signals

**Single-session patterns in SELF.md.** A behavior observed only once — in one session of one Role — appears as a proposed SELF.md addition. Symptom: SELF.md begins to fill with one-off observations that contradict each other across successive reflect runs; the document oscillates rather than converging. Indicates: evidence threshold check not implemented or bypassed. Maps to: M-01.

**Role-specific content added to SELF.md.** The PR proposes adding work-specific behaviors (e.g., "Uses WorkBoard to track OKRs") to SELF.md rather than ROLE.md. Symptom: SELF.md becomes a mirror of ROLE.md; after a job change, SELF.md is full of false statements. Indicates: cross-role filter not applied to proposed additions. Maps to: M-02.

**Additions proposed without trims when budget would be exceeded.** The PR adds 200 tokens of new content to a 450-token SELF.md without proposing any deletions. Symptom: SELF.md grows unconstrained, eventually reaching 800–1000 tokens; context window budget is violated; curation incentive disappears. Indicates: 500-token budget enforced at document creation but not at each reflect pass. Maps to: M-03, M-04.

**Skill attempts git operations.** The skill writes and commits `personal/SELF.md` directly, creates a branch, or calls `gh pr create` itself. Symptom: the skill/CLI boundary is violated; PR creation logic lives in two places; the skill cannot be invoked from a session without triggering a PR. Indicates: `git commit` or `gh pr create` called from within the skill instead of being delegated to `masks reflect` CLI. Maps to: M-05.

**REFLECT_OK not logged when no patterns found.** The skill exits silently with no log entry when no qualifying patterns are found. Symptom: `masks status` shows no last REFLECT_OK timestamp; the system appears to never have reflected even after many runs. Indicates: log write only in the PR-opened path, not in the no-patterns path. Maps to: M-08.

**Closed PRs re-proposed without acknowledgment.** The skill re-proposes patterns that the user previously rejected by closing the PR, with no reference to the prior decision. Symptom: users who close reflect PRs find the same changes re-proposed in every subsequent run; the editorial "no" is ignored; the authorial consent ritual loses meaning over time. Indicates: PR disposition not tracked or checked before proposing changes. Maps to: design intent (authorial consent); M-07 (rationale should include prior history).
