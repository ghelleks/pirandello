# SDD Spec: `archive` Skill

**Context:** See `docs/spec.md` for full system design. This spec covers the skill that moves a completed task folder from the Role root into `Archive/YYYY-MM/`, updating indexes along the way.

**Deliverables:** `skills/archive/SKILL.md`.

---

## Requirements

### Hard constraints

1. Input: a task folder path within the current Role directory.
2. **Step 1 — README.md:** Read `README.md` from the task folder. If `README.md` is missing, generate one from the folder's contents (file list and any discoverable metadata). Do not skip archiving because README.md is missing.
3. A valid `README.md` must contain all of the following fields:
   - `# [task-name]` — heading matching the folder name
   - `**Date:**` — YYYY-MM-DD (use today's date if generating)
   - `**Role:**` — the Role this folder lives in
   - `**Status:** complete`
   - `**Tags:**` — space-separated topic tags (infer from content if generating)
   - `## Summary` — one paragraph describing what was done and why
   - `## Key Outputs` — bulleted list of files with descriptions (may be empty if no outputs)
   - `## Key Decisions` — bulleted list of decisions made (may be empty)
4. **Step 2 — INDEX.md:** Append exactly one row to `Archive/INDEX.md` with columns: Date, Folder, Summary, Tags, Status. Summary is the first sentence of the README.md Summary section. Status is `complete`.
5. **Step 3 — Move:** Move the task folder to `Archive/YYYY-MM/` where YYYY-MM is the current calendar month. If `Archive/YYYY-MM/` does not exist, create it first.
6. The skill does not commit or push. The session-end hook handles that.
7. If the folder is already inside `Archive/`, the skill exits with an error: "This folder is already archived."

### Soft constraints

- When generating a README.md, ask the user to confirm the Summary and Key Decisions before writing — these require human judgment. Key Outputs can be inferred from the file list without confirmation.
- The skill should report what it did: "Archived `[folder]` to `Archive/YYYY-MM/` and updated INDEX.md."

---

## Proposal format

### 1. Overview
The three-step flow and the no-commit principle.

### 2. README.md generation logic
How the skill generates a README.md when one is missing. Which fields are inferred from content and which require user input.

### 3. INDEX.md update
The exact row format appended to `Archive/INDEX.md`. How the Summary is extracted from README.md.

### 4. Move operation
How the folder is moved. How `Archive/YYYY-MM/` is created if absent. How naming conflicts are handled (folder already exists in target).

### 5. Self-check table
See Static Evaluation Metrics.

---

## Static evaluation metrics

| ID | Name | Pass condition |
|---|---|---|
| M-01 | README.md always present | Archive does not proceed until a valid README.md exists (generated if missing) |
| M-02 | README.md fields complete | README.md contains all 8 required fields (heading, Date, Role, Status, Tags, Summary, Key Outputs, Key Decisions) |
| M-03 | Status is complete | README.md `**Status:**` field is set to `complete` |
| M-04 | INDEX.md row appended | Exactly one new row added to `Archive/INDEX.md` with all five columns (Date, Folder, Summary, Tags, Status) |
| M-05 | Correct archive path | Folder moved to `Archive/YYYY-MM/` matching current calendar month |
| M-06 | Archive dir created | `Archive/YYYY-MM/` is created if it does not exist before the move |
| M-07 | No commit | Skill does not call `git add`, `git commit`, or `git push` |
| M-08 | Already-archived guard | Skill exits with an error if the target folder is already inside `Archive/` |
