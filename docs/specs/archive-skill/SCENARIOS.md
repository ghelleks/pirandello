# SDD Scenarios: `archive` Skill

**Companion spec:** `docs/specs/archive-skill/spec.md`  
**Date:** 2026-04-23

---

## Use Cases

### 1. Task folder with a complete, valid README.md

A user says "archive the `summit-2026-prep` folder." The folder contains `README.md` with all required fields: heading, Date, Role, Status, Tags, Summary, Key Outputs, and Key Decisions. Today's date is 2026-04-23, so the target archive path is `Archive/2026-04/`.

Questions the proposal must answer:
- Does the skill read the existing README.md without generating a replacement?
- Does it append exactly one row to `Archive/INDEX.md` with columns: Date, Folder, Summary (first sentence of the README Summary section), Tags, Status (`complete`)?
- Does it move the folder to `Archive/2026-04/summit-2026-prep/`?
- Does it report what it did in plain language?
- Does it call any git commands (add, commit, push)?

Metric cross-references: M-01, M-02, M-03, M-04, M-05, M-06, M-07

---

### 2. Task folder with no README.md

A user says "archive the `quick-analysis` folder." The folder contains three markdown files and a spreadsheet but no `README.md`.

Questions the proposal must answer:
- Does the skill generate a README.md before proceeding with archival?
- For the `## Summary` section and `## Key Decisions` section, does it ask the user to confirm the generated content before writing?
- For `## Key Outputs`, does it infer the file list from the folder contents without requiring user confirmation?
- Does the generated README.md still contain all seven required fields?
- Does archival proceed after README.md is confirmed — not before?

Metric cross-references: M-01, M-02, M-03

---

### 3. `Archive/YYYY-MM/` directory does not exist yet

Today is the first day of April 2026. A user archives the first task of the month. `Archive/2026-04/` does not yet exist in the Role directory.

Questions the proposal must answer:
- Does the skill create `Archive/2026-04/` before attempting the move?
- Does the move succeed after the directory is created?
- Is the folder correctly placed at `Archive/2026-04/<folder-name>/`?

Metric cross-references: M-05, M-06

---

### 4. Target folder is already inside Archive/

A user accidentally asks to archive `Archive/2026-03/old-task`, which is already archived.

Questions the proposal must answer:
- Does the skill detect that the target folder is inside `Archive/` and exit with the specific error "This folder is already archived."?
- Does it not modify `Archive/INDEX.md` or move any files?
- Is the error message in plain language — not a stack trace?

Metric cross-references: M-08

---

### 5. README.md is present but missing some required fields

A user archives a task folder whose README.md exists but is missing `**Tags:**` and `## Key Decisions`. The file was created informally.

Questions the proposal must answer:
- Does the skill detect the missing fields?
- Does it generate the missing fields (inferring Tags from content; asking the user to confirm Key Decisions) before proceeding?
- Does the archival not proceed until all required fields are present?
- Does it treat this as a generation scenario (fill gaps) rather than rejecting the folder?

Metric cross-references: M-01, M-02

---

### 6. Naming conflict in the target month directory

The user archives a folder named `analysis`. But `Archive/2026-04/analysis/` already exists from a previous task with the same name.

Questions the proposal must answer:
- Does the proposal address naming conflicts in the Move section?
- What is the resolution strategy — rename with a suffix, ask the user, or refuse?
- Is the resolution non-destructive (never overwrites the existing archived folder)?

Metric cross-references: M-05, M-06

---

### 7. Folder with no outputs

A user archives a research task that produced no files — it was a reading and thinking session. The folder only contains `README.md`. `## Key Outputs` is empty.

Questions the proposal must answer:
- Does the skill accept an empty `## Key Outputs` list as valid?
- Does it not block archival or generate a warning because of empty Key Outputs?
- Is the archived README.md correctly formatted with an empty Key Outputs section?

Metric cross-references: M-02

---

### 8. Agent uses Archive/INDEX.md to locate relevant past work — episodic memory retrieval

During a `work/` session, the user asks: "Did we look at the vCPU pricing model last year?" The agent has not read any archived folders. `work/Archive/INDEX.md` is injected at session start and contains 47 rows of archived tasks spanning 14 months.

Questions the proposal must answer:
- Can the agent identify the relevant folder (`vcpu-hour-prfaq`) by scanning the one-line INDEX.md summary row alone — without opening any README.md or folder contents?
- Is the INDEX.md summary produced by the archive skill specific enough to distinguish this folder from other pricing or analysis tasks? (E.g., "PRFAQ proposing vCPU/hour universal pricing model" vs. a generic "pricing analysis.")
- If the INDEX.md summary is sufficient to answer the user's question at a high level, does the progressive disclosure model hold — Level 1 (index) answered the question without reaching Level 2 (README) or Level 3 (full files)?
- If the agent decides more detail is needed, does it go to the README.md `## Summary` section next, before reading the full folder contents?
- Would a proposal that produces INDEX.md summaries like "Analysis of business opportunity" — indistinguishable from a dozen other rows — fail the episodic memory retrieval use case?

Metric cross-references: M-04 (INDEX.md row appended), design intent: Archive as episodic memory; progressive disclosure (Level 1 index → Level 2 README → Level 3 files)

---

## Stress Tests

**T1 Archive does not proceed until a valid README.md exists.**  
Whether the README.md was present before or generated by the skill, the folder is not moved until a README.md with all required fields is written and (for Summary and Key Decisions) confirmed by the user.  
Pass: a run where the skill moves the folder before confirming the README.md content fails this test.

**T2 README.md contains all required fields.**  
The README.md present at archival time contains: a heading matching the folder name, `**Date:**` (YYYY-MM-DD), `**Role:**`, `**Status:** complete`, `**Tags:**`, `## Summary`, `## Key Outputs`, and `## Key Decisions`.  
Pass: all eight field types are present in the README.md; missing any one fails this test.

**T3 `**Status:**` field is set to `complete`.**  
The README.md `**Status:**` field is exactly `complete` at archival — not `active`, `superseded`, or blank.  
Pass: `grep "Status" README.md` returns `**Status:** complete`.

**T4 Exactly one row is appended to `Archive/INDEX.md`.**  
The `Archive/INDEX.md` file gains exactly one new row with all required columns (Date, Folder, Summary, Tags, Status).  
Pass: `Archive/INDEX.md` line count increases by exactly one after archival; the new row contains all five columns (Date, Folder, Summary, Tags, Status).

**T5 Folder moved to `Archive/YYYY-MM/` matching the current calendar month.**  
The folder is moved to the subdirectory matching today's date — not last month, not a hardcoded path.  
Pass: the archived folder is at `Archive/2026-04/<folder-name>/` when archived in April 2026.

**T6 `Archive/YYYY-MM/` is created if it does not exist.**  
If the current month's archive subdirectory does not exist, the skill creates it before moving the folder.  
Pass: a run on the first archival of a new month creates the directory and completes successfully.

**T7 No git commands called.**  
The skill does not call `git add`, `git commit`, or `git push` at any point.  
Pass: the skill source contains no git commit or push calls; the session-end hook handles committing.

**T8 Already-archived folder produces an error, not a double-archive.**  
Attempting to archive a folder already inside `Archive/` exits with the error "This folder is already archived." without modifying any files.  
Pass: `Archive/INDEX.md` is unchanged; no new subdirectory is created; exit is non-zero with the specified message.

**T9 INDEX.md one-line summaries are distinct and decision-quality.**  
The first sentence of each README.md Summary section — which becomes the INDEX.md row summary — is specific enough that a reader scanning the index can distinguish between similar tasks without opening any folder.  
Pass: given a 20-row INDEX.md containing two pricing-related tasks and two strategy tasks, a reader can identify the correct folder from the summary alone; summaries that could apply interchangeably to multiple rows fail this test.

---

## Anti-Pattern Regression Signals

**Archival proceeds before README.md is confirmed.** The skill moves the folder and updates INDEX.md before asking the user to confirm the generated Summary or Key Decisions. Symptom: archived folders have machine-generated summaries that are factually wrong; the user has no way to correct them without re-reading the archived content. Indicates: move operation happens before user confirmation step. Maps to: M-01.

**README.md fields missing after archival.** The archived README.md is missing `**Tags:**` or `## Key Decisions`. Symptom: `Archive/INDEX.md` rows are missing tag data; search and discovery of archived work is degraded. Indicates: M-02 field check not implemented or incomplete. Maps to: M-02.

**Skill commits or pushes.** The skill calls `git add -A && git commit` after archiving. Symptom: archival creates a commit separate from the session-end commit, producing erratic git history and potential double-push race conditions. Indicates: M-07 violation; skill misunderstands the no-commit contract. Maps to: M-07.

**INDEX.md Summary uses wrong sentence.** The Index row Summary is populated with the folder name, a tag, or a generated sentence rather than the first sentence of the README.md `## Summary` section. Symptom: Archive/INDEX.md rows don't reflect the actual work done; progressive disclosure breaks because the one-line summary is meaningless. Indicates: incorrect extraction of the Summary field from README.md. Maps to: M-04.

**Double-archive not detected.** Archiving `Archive/2026-03/old-task` silently moves it to `Archive/2026-04/Archive/2026-03/old-task` and adds a second INDEX.md row. Symptom: archive structure becomes nested incorrectly; INDEX.md has duplicate entries. Indicates: already-archived guard (M-08) not implemented. Maps to: M-08.

**INDEX.md summaries are too generic for retrieval.** Archive/INDEX.md rows read "Analysis of business opportunity" or "Research and planning work" — phrases that could describe any of a dozen archived folders. Symptom: agents and users must open multiple README.md files to find the relevant task; the progressive disclosure model breaks down at Level 1; the episodic memory value of the archive is lost. Indicates: skill wrote the first sentence of a boilerplate or machine-generated README.md Summary instead of a task-specific one; Summary generation lacked a quality check. Maps to: M-04.
