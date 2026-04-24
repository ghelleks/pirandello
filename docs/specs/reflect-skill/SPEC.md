# SDD Spec: `reflect` Skill

**Context:** See `docs/spec.md` for full system design. This spec covers the synthesis and reflection skill that reads Memory/ files across Roles, identifies cross-role patterns, and produces a SELF.md diff and PR description. The skill's output is content and text — not git operations. The `masks reflect` CLI (spec: `docs/specs/masks-reflect/`) owns the infrastructure side-effects: creating the branch, committing the diff, pushing, and calling `gh pr create`.

**Deliverables:** `skills/reflect/SKILL.md`. Invoked by `masks reflect [role]` and directly by the user.

---

## Requirements

### Hard constraints

1. The skill reads `Memory/` files from all Roles under `$BASE` (or a specified Role if `masks reflect <role>` is called).
2. The skill reads `personal/SELF.md` as the current draft to diff against.
3. A **pattern** is valid input for a SELF.md change only if it appears in ≥3 distinct sessions OR ≥2 distinct Roles. Evidence must be citeable (specific session dates or Role names).
4. Proposed additions to SELF.md must be cross-role. Content that is specific to one Role belongs in that Role's ROLE.md, not SELF.md.
5. The proposed SELF.md must be ≤500 tokens after all additions and deletions are applied. If additions would exceed the budget, the PR must also propose what is trimmed to make room.
6. The skill must produce: (a) a proposed SELF.md diff (the exact text changes), and (b) a PR description containing all required sections. It writes these to a structured output that `masks reflect` uses to open the PR. It does not commit directly to `SELF.md`, create a git branch, or call `gh pr create`.
7. The PR description must include:
   - Which Memory/ files were read and over what time period.
   - For each proposed addition: the pattern observed, which sessions/Roles it appeared in, and the rationale.
   - For each proposed deletion: what is being removed and why it is no longer accurate or no longer earning its place.
8. If no patterns meeting the ≥3-session or ≥2-Role threshold are found, the skill logs `REFLECT_OK` and exits without opening a PR.
9. `REFLECT_OK` is written to `$BASE/personal/.reflect.log` with an ISO timestamp.

### Soft constraints

- The PR branch name should follow the pattern `reflect/YYYY-MM-DD`.
- The skill should cite evidence compactly — session dates and Role names, not full quotes from Memory files.
- If the user invokes the skill directly (not via `masks reflect`), it should confirm what it found before opening the PR.

---

## Proposal format

### 1. Overview
How the skill reads across Roles, identifies patterns, and converts them into a PR.

### 2. Pattern detection logic
The algorithm for identifying cross-role patterns. What counts as a "session" for the ≥3-session threshold. How patterns are distinguished from one-off observations.

### 3. SELF.md diff construction
How proposed additions and deletions are structured. How the 500-token budget is enforced. How trimming decisions are made when additions exceed the budget.

### 4. PR description content
The exact sections of the PR description the skill produces: which Memory/ files were read, the time period covered, per-addition evidence and rationale, per-deletion evidence and rationale. Branch naming and PR title are `masks reflect` CLI concerns — this section covers only the text content the skill outputs.

### 5. No-pattern path
What `REFLECT_OK` looks like in the log. How the skill communicates a no-op to the user when invoked directly.

### 6. Self-check table
See Static Evaluation Metrics.

---

## Static evaluation metrics

| ID | Name | Pass condition |
|---|---|---|
| M-01 | Evidence threshold | No proposed change is based on fewer than 3 sessions or fewer than 2 Roles of evidence |
| M-02 | Cross-role only | No proposed addition is specific to a single Role; all additions are cross-role patterns |
| M-03 | Token budget | Proposed SELF.md is ≤500 tokens after all additions and deletions applied |
| M-04 | Trim proposed with additions | Any PR that proposes additions also proposes what is trimmed to stay within budget |
| M-05 | No direct commit | The skill produces a diff and PR description; it does not write, commit, branch, or push to `SELF.md` or any git remote |
| M-06 | PR description evidence | PR description names specific sessions (dates) or Roles for every proposed change |
| M-07 | Rationale per change | Every proposed addition and deletion has an explicit rationale in the PR description |
| M-08 | REFLECT_OK on no patterns | When no qualifying patterns are found, REFLECT_OK is logged and no PR description is produced |
| M-09 | Output targets personal remote | The structured output identifies the `personal/` Role's git remote as the PR destination (used by `masks reflect` CLI) |
