# Skill: mask-reference-refresh

Refresh curated **Reference** material from Google Drive (or similar) into markdown under `Reference/`, keeping `Reference/INDEX.md` honest.

## Delimiter contract

Source docs may embed a machine region:

```markdown
<!-- pirandello-ref-summary:start -->
... editable summary markdown ...
<!-- pirandello-ref-summary:end -->
```

Only this region is overwritten on refresh. If delimiters are missing, **stop** and ask the user to add them once.

## `Refreshed` column

Update the `Refreshed` column in `Reference/INDEX.md` **only after** a successful write to disk.

## Non-interactive mode

When `PIRANDELLO_NONINTERACTIVE=1`:

- Do not prompt; skip rows that need clarification and append a single stderr-style note to the run summary for later human follow-up.

## Flow

1. Read `Reference/INDEX.md` for rows marked stale or due.
2. Export each linked Google Doc (Drive API export → markdown).
3. Merge into the delimited summary region; preserve front matter outside delimiters.
4. Write file, then bump INDEX `Refreshed` ISO date.

## Errors

Permission or export failures must not partially truncate delimiter regions—restore from git if a write began.
