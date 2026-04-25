---
layout: home
title: Home
---

Pirandello is a file- and git-first system for AI-assisted memory and configuration: many **Roles** (contexts), one cognitive model, hooks and a `masks` CLI for reliability. Markdown files are canonical for human-owned memory; any semantic database is a **regenerable index**, not a source of truth.

## Why the name

The project borrows from Luigi Pirandello’s modernist theme of identity as something provisional—**masks** worn in different social worlds, never fully fixed. That is a metaphor for how this repository treats `SELF.md` and `ROLE.md`: drafts to edit deliberately, not auto-generated truths. For a longer philosophical setup, see the inaugural post below.

## Key concepts

- **Roles:** separate directories (each a git repo) per life context; the session workspace root is always a Role directory.
- **SELF.md / ROLE.md:** cross-role draft versus per-role behavioral delta; size budgets and update ceremonies are design constraints (see `docs/design.md`).
- **Reflect ritual:** proposed edits to `SELF.md` land as a pull request; a human merges or rejects—nothing silently becomes “truth.”
- **Memory / Reference / Archive:** progressive disclosure; markdown under git; semantic search is rebuildable from files.

## Contributors

- Browse the repository on GitHub for source, issues, and `docs/design.md` (full system design lives in the repo root, not in this Jekyll site).
