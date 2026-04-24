# SDD Spec: `reference-refresh` Skill

**Context:** See `docs/spec.md` for full system design. This spec covers the skill that keeps `Reference/` documents current by pulling from Google Drive, generating summary headers, and updating the index.

**Deliverables:** `skills/reference-refresh/SKILL.md`.

---

## Requirements

### Hard constraints

1. Input: the current Role's `Reference/INDEX.md`.
2. For each row in `Reference/INDEX.md` where the Source column contains a Google Drive document ID or URL:
   - Export the document from Google Drive as Markdown.
   - Generate or update a summary header at the top of the local file.
   - Write the full exported content below the summary header.
   - Update the `Refreshed` timestamp in `Reference/INDEX.md` to today's date (YYYY-MM-DD).
3. For rows where Source is `"Written directly"`: skip the Drive export. The skill may optionally update the summary header by re-reading the existing file body, but must not overwrite the file body. The `Refreshed` timestamp in `Reference/INDEX.md` must **not** be updated for Written-directly entries, regardless of whether the summary header was regenerated — since no Drive export occurred, the document cannot be considered "refreshed."
4. The summary header must:
   - Appear at the very top of the file, before any other content.
   - Be ≤500 words.
   - Capture: key points, key decisions, and current status of the document.
   - Be delimited so it is clearly distinct from the document body (e.g., a horizontal rule or a clearly labelled section).
5. The full document body must be preserved below the summary header. The summary header does not replace the body — it precedes it.
6. After processing all documents, `Reference/INDEX.md` must reflect the updated `Refreshed` timestamps for all successfully refreshed documents.
7. If a Drive export fails (auth error, document not found, permission denied), the skill logs the failure for that document and continues with remaining documents. It does not abort.
8. The skill does not commit or push. The session-end hook or OODA Act phase handles that.

### Soft constraints

- The skill should report a summary on completion: N documents refreshed, N skipped (written directly), N failed.
- When invoked from the OODA loop, it should run without user interaction. When invoked directly, it may ask the user to confirm before overwriting recently-refreshed documents (e.g., refreshed within the last 7 days).

---

## Proposal format

### 1. Overview
The refresh flow: read INDEX.md → export from Drive → generate summary header → write file → update INDEX.md.

### 2. Drive export
Which Google Drive export API or tool is used. What format the export produces. How the document ID is extracted from the Source column (handles both bare IDs and full Drive URLs).

### 3. Summary header generation
The prompt or logic used to generate the ≤500-word summary. The delimiter format used to separate it from the document body. How existing summary headers are updated vs. replaced.

### 4. INDEX.md update
The exact column updated (`Refreshed`) and the date format written.

### 5. Failure handling
How individual document failures are logged and surfaced to the user.

### 6. Self-check table
See Static Evaluation Metrics.

---

## Static evaluation metrics

| ID | Name | Pass condition |
|---|---|---|
| M-01 | Summary at top | Summary header appears before any document body content in every refreshed file |
| M-02 | Summary size | Summary header is ≤500 words |
| M-03 | Body preserved | Full document body is present below the summary header after refresh |
| M-04 | Written-directly skipped | Files with `Source: Written directly` are not exported from Drive |
| M-05 | Refreshed timestamp updated | `Refreshed` column updated to today's date for every successfully Drive-exported document; must not be updated for Written-directly entries or failed exports |
| M-06 | Failure continues | A Drive export failure for one document does not prevent processing of remaining documents |
| M-07 | No commit | Skill does not call `git add`, `git commit`, or `git push` |
| M-08 | INDEX.md unchanged structure | All columns and rows in INDEX.md are preserved; only the `Refreshed` column values change |
