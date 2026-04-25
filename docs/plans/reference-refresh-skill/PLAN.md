# Proposal: `reference-refresh` Skill

**Unit:** `reference-refresh` skill  
**Deliverable:** `skills/reference-refresh/SKILL.md` (plus optional thin helper in `pirandello` only if needed; no secrets, no personal content)  
**Date:** 2026-04-23

---

## 1. Overview

The skill runs **only** in the context of the **current Role directory** (session workspace root = `[role]/`). It does **not** read other Roles’ `Reference/` trees.

**End-to-end flow:**

1. **Locate input:** Read `[role]/Reference/INDEX.md` (required). If the file is missing, exit with a clear error; do not create it automatically.
2. **Parse the index table:** Treat `Reference/INDEX.md` as a GitHub-flavored markdown table with exactly these header columns (per `docs/design.md`): `File`, `Summary`, `Source`, `Refreshed`. Preserve byte-for-byte everything except `Refreshed` cell edits (see §4).
3. **Classify each data row’s `Source` cell** (after trim):
   - **Written directly:** Case-sensitive exact match to `Written directly` after trimming outer whitespace.
   - **Drive-backed:** Anything else that yields a non-empty document ID via §2’s extraction rules (including `Google Drive: <id>` prose prefixes and full URLs).
   - **Unrecognized:** Neither written-directly nor a parsable Drive doc ID (log as failed, do not mutate the row’s `Refreshed`).
4. **For each Drive-backed row (sequential order of rows in the table):**
   - Optionally apply the **7-day interactive guard** (§5) when not in non-interactive mode.
   - **Export** the Google Doc to Markdown (§2) → full body string `B`.
   - **Generate** summary text `S` with `wordcount(S) ≤ 500` (§3).
   - **Resolve local path:** `Reference/<File cell>` (e.g. `strategy/foo.md` → `Reference/strategy/foo.md`). Create parent directories if missing.
   - **Write file:** Replace entire file content with `render(S, B)` (§3). Never truncate `B`.
   - **Only after a successful export+write**, stage an update to that row’s `Refreshed` cell to **today’s local date** `YYYY-MM-DD` (§4). If export fails, **leave `Refreshed` unchanged** for that row.
5. **For each Written-directly row:** No Drive API calls. Optionally regenerate summary from existing body only (§3). **Never** change `Refreshed` for that row.
6. **Rewrite `Reference/INDEX.md`** once at the end with all staged `Refreshed` updates applied (§4).
7. **Emit completion report** (soft constraint): counts refreshed, skipped written-directly, failed; name each failure with reason (§5).
8. **No git:** Do not run `git add`, `git commit`, or `git push` (session-end hook or OODA Act handles commits).

**Empty index:** If the table has a header row but **zero** data rows, exit successfully with `0 refreshed, 0 skipped, 0 failed` and do not modify the file.

---

## 2. Drive export

### API and format

**Primary method:** Google **Drive API v3** `files.export` on the Google Doc file ID, requesting **`text/html`**, then convert HTML → **GitHub-flavored Markdown** using a deterministic library (**`markdownify`** with heading style `ATX`, bullets standardized). This path is universally available for Google Docs and produces stable Markdown suitable for `Reference/`.

**Rationale:** Native `text/markdown` export is not consistently available across all Workspace configurations; HTML export is reliable. The conversion step is local and reproducible.

**Authentication:** Use the **same OAuth/service account path** already configured for the Role’s Google workspace (e.g. Application Default Credentials or the existing `gws`/Google MCP credential flow the agent uses for work). The skill text in `SKILL.md` will name the **work vs personal** account selector convention already used in this environment (`gws --account work` pattern from `docs/design.md`), without embedding secrets.

**Output:** A single Markdown string representing the **full** document body (no arbitrary max length; no truncation).

### Document ID extraction from `Source` cell

Apply rules **in order**; first match wins:

1. If the cell contains a Google Docs URL, extract with regex  
   `\/document\/d\/([a-zA-Z0-9_-]+)`  
   (covers `/edit`, `/view`, query strings, and fragments).
2. Else if the cell matches `Google Drive:\s*([a-zA-Z0-9_-]+)` (case-insensitive on the label only), capture the ID group.
3. Else if the entire cell (after trim) matches `^[a-zA-Z0-9_-]{10,}$`, treat the whole cell as a bare document ID.
4. Else: **no ID** → treat row as failed for Drive processing (log), do not guess.

**INDEX preservation (M-08):** The `Source` cell string in `Reference/INDEX.md` is **never rewritten**—only `Refreshed` values change. URLs stay URLs; bare IDs stay bare IDs.

### Errors (per document)

Map HTTP/API failures to user-visible messages: **401/403** → permission/auth; **404** → not found; timeouts → timeout. Continue to next row (§5).

---

## 3. Summary header generation

### Delimiter format (machine-parsable, replace-not-append)

Every refreshed file begins with this structure:

```markdown
<!-- pirandello-ref-summary:start -->
## Reference summary

[summary prose here — no HTML except markdown]

<!-- pirandello-ref-summary:end -->

```

Immediately after `end` comment **one blank line**, then the **full document body** Markdown (`B`) begins.

**Rules:**

- The block **including** both comment lines and the `## Reference summary` heading is the **summary header region**.
- The **document body** for written-directly optional regeneration is defined as: all content **after** the line `<!-- pirandello-ref-summary:end -->`, including that single following blank line’s separation, through EOF.
- On **subsequent refreshes**, locate `<!-- pirandello-ref-summary:start -->` … `<!-- pirandello-ref-summary:end -->`; **delete only that region** and insert the newly generated region; **leave everything after `end` untouched** when only the summary is regenerated (written-directly path).

For **Drive-backed** refresh, the implementation **rewrites the entire file** as: `new_summary_block + "\n\n" + B` (ensuring no accidental partial merge). That guarantees the body matches the latest export and prevents stacked summaries (anti-pattern regression).

### Word limit enforcement

- **Count words** in the summary prose **inside** the header region only (exclude the comment lines and the `## Reference summary` line from the count—those are fixed scaffolding; the **prose paragraph(s)** must be ≤500 words).
- **Generation:** The LLM (when the skill runs in an agent) is instructed to produce ≤450 words to leave margin; a **deterministic post-pass** truncates at the last complete sentence before the 500-word boundary if the model overshoots.
- **Written-directly optional regen:** Same limit and truncation when summarizing from the existing body only.

### Content requirements

The summary prose (the part under `## Reference summary`) must answer: **key points**, **key decisions**, **current status** of the document, in neutral third person. It must not duplicate the entire body.

---

## 4. INDEX.md update

- **Column updated:** Only `Refreshed`.
- **Date format:** `YYYY-MM-DD` in the Role’s **local timezone** (use the same “today” as the user’s machine running the agent, not UTC, unless the runtime only exposes UTC—in that case document UTC in the skill and use `YYYY-MM-DD` in UTC consistently; **default assumption: local date**).
- **Which rows update:** Only rows where a **Drive export completed successfully** and the markdown file was written successfully.
- **Which rows never update `Refreshed`:** `Written directly` rows; failed exports; rows skipped by user confirmation; unrecognized Source.
- **Structure preservation (M-08):** Parse the markdown table into rows/cells without reordering. Do not add/remove columns or rows. Do not reformat unrelated cells. Writing back should preserve each cell’s original text except the `Refreshed` cell for rows that succeeded in this run.

**Implementation note for implementers:** Prefer a small table-aware parser (e.g. split lines on `|`, respect outer pipes) rather than regex on the whole file, so pipe characters inside cells (rare) can be handled if present; if a row is malformed, log failure for that row and skip mutating it.

---

## 5. Failure handling

### Per-document try/catch

Wrap each Drive-backed row in an isolated failure domain:

- On failure: append to an in-memory **`failures[]`** list: `{ file: <File cell>, source: <verbatim Source cell>, reason: <short technical + human message> }`.
- **Do not** update `Refreshed` for that row.
- **Continue** processing subsequent rows (M-06).

### Logging and surfacing

- **During run:** Print or stream each failure to the user-visible transcript as it happens (`stderr`-equivalent in CLI terms).
- **Completion report (required):**  
  - `Refreshed: N`  
  - `Skipped (written directly): K`  
  - `Failed: F`  
  - If `F > 0`, enumerate each failure with **file path + reason** (e.g. `charters/pods/data-charter.md — Drive export failed: 403 permission denied`).

### Interactive vs OODA (soft constraint)

- **Non-interactive mode:** When the environment variable **`PIRANDELLO_NONINTERACTIVE=1`** is set (convention: `beckett run` / OODA Act sets this before invoking the agent), **never** prompt; always proceed with exports.
- **Interactive mode:** When `PIRANDELLO_NONINTERACTIVE` is unset and the runtime supports user prompts, **before** exporting a Drive-backed document whose existing `Refreshed` date parses as **within the last 7 calendar days** (compare parsed `Refreshed` to local today), ask:  
  *“`<File>` was refreshed on `<date>`. Re-export from Google Drive? (y/N/skip-all-remaining-recency-prompts)”*  
  - **N** or empty → skip that document (no export, **no** `Refreshed` change).  
  - **skip-all** → disable further recency prompts for this run.  
  - **y** → proceed.

Recency skips are **not** counted as failures; report them under a separate line `Skipped (recent, user declined): R` in the completion summary.

### Ordering of operations (M-05 anti-pattern)

**Never** write a new `Refreshed` date until export **and** file write succeed. Timestamp updates are **post-success** only.

---

## 6. Self-check table

### Unit metrics (`docs/specs/reference-refresh-skill/SPEC.md`)

| ID | Pass / Fail | Evidence in this proposal |
|----|-------------|---------------------------|
| M-01 | Pass | Summary block is always written first in file; Drive body follows delimiter comments (§3). |
| M-02 | Pass | ≤500-word enforcement on summary prose with truncation pass (§3). |
| M-03 | Pass | Full export `B` appended intact after summary block; full-file rewrite on Drive success (§1, §3). |
| M-04 | Pass | Written-directly: no export, optional summary-only regen (§1, §3). |
| M-05 | Pass | `Refreshed` only after successful Drive export+write; never for written-directly or failures (§1, §4, §5). |
| M-06 | Pass | Per-row isolation; continue on failure (§5). |
| M-07 | Pass | Explicit prohibition on git commands (§1). |
| M-08 | Pass | Only `Refreshed` cells change; Source untouched; no row/column add/remove (§2, §4). |

### Top-level metrics (`docs/SPEC.md`)

| ID | Pass / Fail | Evidence |
|----|-------------|----------|
| S-01 | Pass | Proposal contains no personal data; `SKILL.md` will use placeholders only. |
| S-02 | Pass | No mcp-memory / database as truth; files in `Reference/` remain canonical. |
| S-03 | Pass | No “every session” behavior claimed; commits remain hooks’ job. |
| S-04 | Pass | Only current Role `Reference/` is touched. |
| S-05 | Pass | N/A to this unit (no new `masks` subcommand); skill is idempotent in the sense re-run re-exports safely. |
| S-06 | Pass | Does not touch `SELF.md`. |
| S-07 | Pass | Summary header ≤500 words; does not expand SELF/ROLE or always-loaded stack. |

---

## SKILL.md outline (implementation target)

The actual `skills/reference-refresh/SKILL.md` will encode: triggers (“refresh reference”, OODA `reference-refresh` agenda item), prerequisites (Google auth, `Reference/INDEX.md` schema), the algorithm above, delimiter constants, regexes, failure report format, `PIRANDELLO_NONINTERACTIVE` behavior, and explicit **“do not run git”** instruction to the agent.

---

## Scenario coverage notes (non-normative)

- **Mix of Drive + written-directly:** Handled by row classification (§1).  
- **403 on one doc:** Logged, others continue (§5).  
- **Full URL in Source:** Extracted, URL preserved in INDEX (§2, §4).  
- **Written-directly body immutability:** Optional regen only rewrites bounded summary region (§3).  
- **Interactive 7-day guard:** §5.  
- **Oversized summary:** Truncation pass (§3).  
- **Empty INDEX:** §1.
