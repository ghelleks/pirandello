# SDD Scenarios: `reference-refresh` Skill

**Companion spec:** `docs/specs/reference-refresh-skill/spec.md`  
**Date:** 2026-04-23

---

## Use Cases

### 1. Standard refresh — mix of Drive documents and written-directly entries

`work/Reference/INDEX.md` has five entries: three reference Google Drive document IDs, and two marked as `Written directly`. The user invokes the skill to refresh all Drive-backed documents.

Questions the proposal must answer:
- Does the skill export each of the three Drive documents to Markdown?
- Does it generate or update a summary header for each, ≤500 words, placed before any body content?
- Does it preserve the full document body below the summary header?
- Does it skip the two `Written directly` entries without exporting or overwriting them?
- Does it update the `Refreshed` column in `Reference/INDEX.md` for the three successfully refreshed documents?
- Does it report how many were refreshed, skipped, and (if any) failed?

Metric cross-references: M-01, M-02, M-03, M-04, M-05, M-07, M-08

---

### 2. One Drive export fails — permission denied

The skill is refreshing four Drive documents. The third one (`charters/pods/data-charter.md`) fails with a 403 permission denied error — the sharing settings changed since it was last imported.

Questions the proposal must answer:
- Does the skill log the failure for that document and continue processing the fourth document?
- Does it update `Refreshed` timestamps for the documents that succeeded?
- Does it not abort on the third document's failure?
- Does the completion report clearly name which document failed and why?

Metric cross-references: M-06

---

### 3. Document source is a full Drive URL, not a bare ID

Some rows in `Reference/INDEX.md` have a Source column containing a full Drive URL (`https://docs.google.com/document/d/1aBcDeFgHiJkL/edit`) rather than a bare document ID.

Questions the proposal must answer:
- Does the skill correctly extract the document ID from the full URL?
- Does the export succeed the same way as for a bare ID?
- Is the source column in INDEX.md left unchanged (URL is preserved, not replaced with a bare ID)?

Metric cross-references: M-08 (INDEX.md structure preserved)

---

### 4. `Written directly` document — summary header may be updated, body must not be overwritten

`Reference/INDEX.md` has an entry for `org/extended-staff.md` with `Source: Written directly`. The document body was written by a human and is not in Google Drive.

Questions the proposal must answer:
- Does the skill not export anything from Drive for this document?
- Does the document body remain exactly as written — no changes?
- If the skill optionally regenerates the summary header by re-reading the existing body, does it only update the summary header and leave everything below the delimiter untouched?
- Is the `Refreshed` column NOT updated for this document (since no Drive export occurred)?

Metric cross-references: M-03, M-04

---

### 5. Invoked directly by user — recently-refreshed document

A user manually invokes the skill. One document in INDEX.md was refreshed 3 days ago (within the 7-day recency window).

Questions the proposal must answer:
- Does the skill ask the user to confirm before overwriting the recently-refreshed document?
- Does it clearly communicate when the document was last refreshed?
- If the user says "skip it," does it proceed with the other documents?
- When invoked from the OODA loop (not directly), does it run without asking this confirmation?

Metric cross-references: M-06 (failure continues → by extension, skip-on-recent also continues)

---

### 6. Summary header grows beyond 500 words on re-generation

A very dense strategy document produces a machine-generated summary that is 640 words on the first refresh. On a subsequent refresh, the summary must be updated.

Questions the proposal must answer:
- Is the ≤500-word limit enforced during generation, producing a condensed summary when needed?
- When the summary header is updated on a subsequent refresh, is the old header replaced (not appended to)?
- Is the delimiter between summary header and body clear enough that the proposal can reliably identify where the old header ends?

Metric cross-references: M-02

---

### 7. INDEX.md has no rows — empty Reference directory

A newly set-up Role has a `Reference/INDEX.md` with only the header row and no document entries. The user runs the reference-refresh skill.

Questions the proposal must answer:
- Does the skill exit cleanly (0 documents refreshed, 0 failed) without errors?
- Is `Reference/INDEX.md` left unchanged (the header row preserved, no rows modified)?
- Does the completion report indicate zero documents were processed?

Metric cross-references: M-07, M-08

---

## Stress Tests

**T1 Summary header appears before document body.**  
In every refreshed file, the summary header section comes before any content from the exported document body.  
Pass: the first non-blank line of every refreshed document is part of the summary header, not part of the document body.

**T2 Summary header is ≤500 words.**  
The summary header generated for any document is 500 words or fewer.  
Pass: a word count of the summary header section (from start to delimiter) returns ≤500 for every refreshed document.

**T3 Full document body is present below the summary header.**  
After refresh, the complete exported document body is present below the summary header delimiter — no content is truncated or omitted.  
Pass: the document body below the delimiter is not shorter than the exported content; no sentences are cut off.

**T4 `Written directly` files are not exported from Drive.**  
No Drive API call is made for documents with `Source: Written directly`.  
Pass: a network trace of a run that includes written-directly entries shows no Drive export request for those entries.

**T5 `Refreshed` column updated only for successfully refreshed documents.**  
The `Refreshed` column in INDEX.md is updated to today's date for documents that were exported successfully. It is not updated for failed exports or written-directly entries.  
Pass: after a run where one export failed, the failed document's `Refreshed` date is unchanged; the succeeded documents' dates are updated.

**T6 A Drive export failure does not stop processing of remaining documents.**  
When one document fails to export, the skill logs the failure and continues processing the next document in the index.  
Pass: all other documents are refreshed (or attempted) regardless of the failure; the completion report lists all results.

**T7 Skill does not call git add, commit, or push.**  
The skill performs no git operations.  
Pass: no git command appears in the skill's implementation; `git log` shows no new commits after a refresh run.

**T8 INDEX.md structure is preserved.**  
After a refresh run, `Reference/INDEX.md` has the same number of columns and the same rows as before; only the `Refreshed` column values change.  
Pass: every row in INDEX.md that existed before the run still exists after; no rows are added, removed, or reordered; no column is added or removed.

---

## Anti-Pattern Regression Signals

**Summary header appended instead of replaced.** On a subsequent refresh, the new summary is appended below the old one rather than replacing it. Symptom: files gradually accumulate stacked summary blocks; the document grows with each refresh; the summary no longer reflects the current document state. Indicates: header update logic adds content instead of identifying and replacing the existing header. Maps to: M-01, M-02.

**Document body truncated.** The refreshed file contains only the summary header and the first few paragraphs of the exported document. Symptom: agents reading past the summary find incomplete reference documents; decisions are made on partial information. Indicates: export or write step cuts off at a length limit instead of preserving the full body. Maps to: M-03.

**`Written directly` files overwritten with Drive export.** The skill exports a Drive document for an entry marked `Written directly`, replacing the human-authored body. Symptom: manually curated content is silently destroyed; the user discovers their org chart or extended staff doc has been replaced with an outdated Drive document. Indicates: `Written directly` check not implemented in the source-routing logic. Maps to: M-04.

**`Refreshed` timestamp updated for failed exports.** After a 403 error, the skill updates the `Refreshed` column to today's date, masking the failure. Symptom: the next refresh cycle skips the document because it appears recently refreshed; the document stays stale indefinitely without anyone knowing. Indicates: timestamp update happens before export success is confirmed. Maps to: M-05, M-06.

**Skill aborts entire run on first failure.** One failed Drive export causes the skill to exit early, leaving remaining documents unprocessed. Symptom: if one high-traffic document loses its sharing permissions, all reference documents in the Role stop refreshing. Indicates: exception handling not per-document; top-level try/catch aborts the loop. Maps to: M-06.
