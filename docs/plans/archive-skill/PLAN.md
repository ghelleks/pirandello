# Proposal: `archive` Skill

**Unit:** `docs/specs/archive-skill/SPEC.md`  
**Deliverable:** `skills/archive/SKILL.md` (agent skill instructions; no executable code in `pirandello/` that performs git operations)  
**Authoring note:** This skill runs inside an interactive session whose workspace root is the Role directory. The Role name is the final path segment of the workspace root (e.g. `work`, `personal`).

---

## 1. Overview

The archive skill moves a **completed** task folder from the Role root into episodic storage under `Archive/YYYY-MM/`, where `YYYY-MM` is the **current calendar month in the user’s local timezone** at the moment the skill runs.

Execution is strictly **three steps**, matching the unit spec order:

1. **README.md** — Ensure the task folder contains a valid `README.md` (read and validate, or generate/repair missing fields). Do not proceed to Step 2 until validation passes.
2. **INDEX.md** — Append exactly one new data row to `Archive/INDEX.md` (create the file with the standard header row first if it is missing).
3. **Move** — Create `Archive/YYYY-MM/` if needed, then move the entire task folder into that directory under its folder name (or a user-approved alternate name if a collision required renaming).

**Ordering note:** The unit spec fixes Step 2 before Step 3. To avoid INDEX rows for folders that never moved, the skill **must** verify the destination path is unused (§4.3) **after** README validation and **before** appending the INDEX row.

**No-commit contract:** The skill instructions must never instruct the agent to run `git add`, `git commit`, or `git push`. Version control is exclusively the session-end hook’s responsibility. The skill only renames/moves files and edits markdown under the Role tree.

**Already-archived guard (pre-flight):** Before Step 1, resolve the user-supplied folder to a path relative to the Role root. If that relative path is empty, equals `Archive`, or begins with `Archive/` (POSIX path semantics, forward slashes), stop immediately with the exact error message: `This folder is already archived.` Do not create directories, modify `Archive/INDEX.md`, or move anything.

---

## 2. README.md generation logic

### 2.1 Valid README.md definition

A README is **valid** only if it contains **all** of the following, in this semantic sense (whitespace around values is flexible; headings must exist):


| #   | Requirement   | Rule                                                                                                                                                                                                           |
| --- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Title         | First line is an ATX heading: `# <name>` where `<name>` exactly equals the task folder’s basename (kebab-case folder name).                                                                                    |
| 2   | Date          | A line `**Date:** YYYY-MM-DD` using an actual calendar date.                                                                                                                                                   |
| 3   | Role          | A line `**Role:** <role>` where `<role>` is the current Role name (workspace root basename).                                                                                                                   |
| 4   | Status        | A line `**Status:** complete` (exact value `complete` after the colon, case-sensitive).                                                                                                                        |
| 5   | Tags          | A line `**Tags:`** followed by one or more space-separated tokens (may be empty only if user explicitly confirms “no tags”; otherwise infer at least one topic tag from filenames/headings).                   |
| 6   | Summary       | A `## Summary` section containing at least one paragraph.                                                                                                                                                      |
| 7   | Key Outputs   | A `## Key Outputs` section (bulleted list; **may be empty** — valid if the section heading exists and the list is empty or contains `- None` / similar explicit empty marker chosen consistently in SKILL.md). |
| 8   | Key Decisions | A `## Key Decisions` section (bulleted list; may be empty with same convention as Key Outputs).                                                                                                                |


If an existing README is present but **any** of the above is missing or wrong (including `**Status:`** not exactly `complete`), the skill **repairs** the file by merging new content into the existing README rather than discarding user prose—treat as a “fill gaps” scenario, not a hard failure.

### 2.2 Reading vs generating

- **Full valid README:** Read it once; do not rewrite unless the user asks. Set `**Status:`** to `complete` if it is still `active` (archiving implies completion); if changing status, preserve all other fields.
- **Missing README:** Build a new file from folder inventory (non-hidden files, relative paths). **Date:** use today’s date in the user’s timezone. **Role:** current Role. **Status:** `complete`. **Tags:** infer 3–6 concrete tags from filenames, directory names, and any skimmed markdown headings—avoid generic tags like `work` or `analysis` when a more specific topic is available (supports episodic retrieval quality per design intent).
- **Partial README:** Add only missing sections/lines. For **Tags**, infer from content when absent. For **Summary** and **Key Decisions**, follow the confirmation rules below.

### 2.3 Human confirmation (soft constraint)

Per unit soft constraints:

- `**## Summary`:** If the Summary is **generated from scratch**, **expanded materially**, or **missing** and must be written, present a draft Summary paragraph to the user and **wait for explicit confirmation or edits** before writing `README.md`.
- `**## Key Decisions`:** If decisions are **generated or inferred** (not clearly copied from existing trusted prose in the folder), present a bullet list draft and **wait for explicit confirmation or edits** before writing.
- `**## Key Outputs`:** Derive from the file list (excluding `README.md` itself from “outputs” unless it is the only artifact). **No confirmation required.** If there are no non-README files, emit a valid empty list (Scenario 7).

**Ordering:** Do not perform Step 2 (INDEX) or Step 3 (Move) until README validation passes **and** any required confirmations for Summary/Key Decisions are complete (Stress test T1).

### 2.4 Summary quality for downstream INDEX rows

When drafting or repairing Summary text, the first paragraph must be **decision- and artifact-specific** (passes anti-pattern “generic summary” checks): it should name the concrete topic, deliverable type, and distinguishing angle (e.g. “PRFAQ proposing vCPU/hour universal pricing for FY27”) rather than “Completed analysis work.” This is required because the INDEX row Summary is the first sentence of this section (see §3).

---

## 3. INDEX.md update

### 3.1 File bootstrap

If `Archive/INDEX.md` does not exist, create it with this **exact header line** (matches `docs/design.md`):

```markdown
| Date       | Folder                     | Summary                                       | Tags                    | Status   |
```

Then add a separator line:

```markdown
|------------|----------------------------|-----------------------------------------------|-------------------------|----------|
```

If the file exists but lacks a header, prepend the standard header and separator before appending new rows (repair once; do not duplicate headers).

### 3.2 Row to append

Append **exactly one** new markdown table row **after** all existing data rows:

- **Date:** The `YYYY-MM-DD` value from `README.md`’s `**Date:`** line (not “today”), so the index reflects the task record date.
- **Folder:** The **basename** of the task folder **as it will exist inside** `Archive/YYYY-MM/` after the move (after any user-directed rename for collision resolution).
- **Summary:** The **first sentence** of the body under `## Summary` in `README.md`, per this extraction rule:
  - Take all text after the `## Summary` heading up to the next `##` heading or end of file.
  - Strip leading/trailing whitespace.
  - **First sentence** = substring from start through the first sentence terminator (`.`, `?`, or `!`) that is followed by whitespace or end of text; if no terminator exists in the first 500 characters, use the first line only (up to first newline).
  - Trim trailing whitespace. This string is what appears in the table cell.
- **Tags:** Copy the tag string from `**Tags:`** (same tokens, space-separated).
- **Status:** `complete` (literal).

### 3.3 Table safety

If the extracted Summary contains a pipe character `|`, replace it with `-` for the table row. If the Summary is long, **do not truncate** unless the table renderer breaks; prefer keeping full first sentence (typically under 240 characters if Summary is well-written).

### 3.4 Ordering and idempotency

- Append only **one** row per successful archive run.
- If the already-archived guard fired, **do not** modify `Archive/INDEX.md`.

---

## 4. Move operation

### 4.1 Target path

Let:

- `ROLE_ROOT` = workspace root (the Role directory).
- `MONTH_DIR` = `Archive/YYYY-MM/` where `YYYY-MM` is computed in the user’s local timezone at execution time (`date` semantics in the agent’s environment).
- `TASK_NAME` = basename of the task folder to archive (single segment; reject paths that try to escape the Role with `..`).

**Destination:** `ROLE_ROOT/MONTH_DIR/TASK_NAME/`

### 4.2 Create month directory

If `ROLE_ROOT/Archive/` does not exist, create it. If `ROLE_ROOT/MONTH_DIR` does not exist, create it (including parents). Then move the folder.

**Move primitive:** Use a single folder rename/move operation equivalent to `mv` (atomic within the same filesystem as typical for same Role repo).

### 4.3 Naming conflicts (non-destructive)

If `ROLE_ROOT/MONTH_DIR/TASK_NAME/` **already exists** before the move:

1. **Stop** before Step 2 (`Archive/INDEX.md` append) and before Step 3 (move).
2. Tell the user in **plain language** (no stack traces): an archived folder with that name already exists for this month.
3. Resolution: **Ask the user** to either rename the **active** task folder at the Role root to a new kebab-case name, **or** supply a different archive folder name. Do **not** overwrite, merge, or auto-delete the existing archive. Do **not** silently pick `-2` suffixes without user consent (suffix is allowed **only** if the user explicitly approves that exact new name).

After the user chooses a new `TASK_NAME`, re-validate uniqueness and then proceed.

### 4.4 Operation order (required for safety)

To satisfy the unit spec (INDEX before Move), M-04/M-08, and collision handling:

1. Already-archived guard.
2. README validate/repair + confirmations.
3. **Pre-check destination does not exist** (or user-approved new name is free). If collision, stop—no INDEX append.
4. **Step 2:** Append exactly one row to `Archive/INDEX.md` (values reflect the **planned** final basename and current README on disk in the source folder).
5. Create `ROLE_ROOT/MONTH_DIR` if needed (parents included).
6. **Step 3:** **Move** folder to `ROLE_ROOT/MONTH_DIR/TASK_NAME/`.

If the move fails after INDEX append (I/O error, permissions), the skill instructions must tell the agent to **repair**: remove the single appended INDEX row if the move did not complete, surface the error to the user, and do not leave INDEX and filesystem inconsistent. (This edge case is rare; the check-then-append-then-move sequence still requires recovery text so implementers do not strand bad rows.)

**Reading README for INDEX:** Read `README.md` from the **source** task folder path immediately before Step 2 so the Summary sentence matches the file about to be archived.

### 4.5 User-facing completion message

Report success without exposing full filesystem paths (aligns with system soft constraint while staying precise):

> Archived **folder-name** into this month’s archive and updated the archive index.

Optionally add: “Commit and push will run when the session ends.” Do **not** run git commands.

---

## 5. Self-check table


| ID       | Pass? | Note                                                                                                                                                                                               |
| -------- | ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **M-01** | Pass  | Move only after valid README exists (generated or repaired).                                                                                                                                       |
| **M-02** | Pass  | All eight field groups enforced; empty Key Outputs/Decisions allowed with section present.                                                                                                         |
| **M-03** | Pass  | `**Status:** complete` at archival time.                                                                                                                                                           |
| **M-04** | Pass  | One row; five columns; Summary = first sentence of `## Summary`; table sanitization for `|`.                                                                                                       |
| **M-05** | Pass  | Destination `Archive/YYYY-MM/` from local current month.                                                                                                                                           |
| **M-06** | Pass  | Create `Archive/` and month dir before move.                                                                                                                                                       |
| **M-07** | Pass  | No git commands in skill instructions.                                                                                                                                                             |
| **M-08** | Pass  | Pre-flight guard; exact error string; no file changes when triggered.                                                                                                                              |
| **S-01** | Pass  | Proposal adds only skill docs under `pirandello/`; no personal content.                                                                                                                            |
| **S-02** | Pass  | Archive touches markdown files only; mcp-memory not involved.                                                                                                                                      |
| **S-03** | Pass  | Per-session commit remains in session-end hook; skill does not claim hook duties.                                                                                                                  |
| **S-04** | Pass  | All writes under active Role workspace; no cross-Role Memory writes.                                                                                                                               |
| **S-05** | Pass  | Proposal introduces no new `masks` subcommands; nothing to double-run. Re-invoking the skill on the same folder after success fails at “folder not found”—not an idempotency violation of `masks`. |
| **S-06** | Pass  | Skill never touches `SELF.md`.                                                                                                                                                                     |
| **S-07** | Pass  | README/INDEX are episodic artifacts outside always-loaded stack; instruct agents to keep `## Summary` to one tight paragraph so first-sentence INDEX rows stay scannable (~1–3 sentences max).     |


---

## Implementation notes for `skills/archive/SKILL.md`

- Include a **checklist** mirroring §1–4 for the executing agent.
- Explicitly forbid **git** invocations.
- Document **relative-path** normalization and `Archive/` detection examples (`foo` OK; `Archive/2026-03/x` reject).
- Cross-link `docs/design.md` README template and `Archive/INDEX.md` format for authors.

