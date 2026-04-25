# Skill: mask-archive

Move a **completed** task folder from a Role root into `Archive/YYYY-MM/<folder>/` with index hygiene.

## Preconditions

- Workspace root is the Role directory.
- Target is a **kebab-case** task folder at Role root (not `Memory/`, `Reference/`, etc.).

## README schema (required before move)

The folder’s `README.md` **must** contain these headings (order flexible):

1. `# Title`
2. `## Status`
3. `## Summary`
4. `## Context`
5. `## Decisions`
6. `## Links`
7. `## Next actions`

If any are missing, **stop** and list what to add.

## Algorithm

1. Choose archive month `YYYY-MM` from completion date (user-confirmed; default current UTC month).
2. **Append one row** to `Archive/INDEX.md` *before* moving files: stable slug, title, month, link path `Archive/YYYY-MM/<folder>/`.
3. If `Archive/YYYY-MM/<folder>` already exists → **stop** (collision); do not partially move.
4. `git mv` the task folder into `Archive/YYYY-MM/`. If the filesystem move fails after INDEX write, **repair instructions**: remove the INDEX row added this session or complete the move manually; never leave INDEX pointing at a missing path without user acknowledgment.

5. Commit with message `archive: <folder-name>`.

## Custody

Never archive another Role’s content. Never move folders that are not explicit task folders the user named.
