# SDD Spec: Pirandello (Top Level)

**Status:** draft  
**Date:** 2026-04-23  
**Design document:** `docs/design.md`

---

## Context

Pirandello is a memory and configuration system for AI-assisted personal productivity. It models the whole person across multiple Roles (personal, work, board, consulting), stores memory as markdown files under git, and maintains a semantic search index via mcp-memory. The system runs in two modes: interactive (Cursor / Claude Code) and autonomous (OODA heartbeat loop via cron).

A writer producing proposals from any unit spec must treat `docs/design.md` as authoritative background context. Every design decision, constraint, and convention in the unit specs derives from it.

---

## Unit specs

Each buildable unit has its own spec and (forthcoming) scenarios file in `docs/specs/`:


| Unit                      | Spec                                  | What it builds                                  |
| ------------------------- | ------------------------------------- | ----------------------------------------------- |
| Session hooks             | `docs/specs/session-hooks/`           | `start.sh`, `end.sh`, `post-commit.sh`          |
| `masks` CLI core          | `docs/specs/masks-cli-core/`          | `setup`, `add-role`, `sync`, `status`, `doctor`, `reference-refresh` entrypoint |
| `masks run`               | `docs/specs/masks-run/`               | Heartbeat runner + pre-flight guard contract    |
| `masks index`             | `docs/specs/masks-index/`             | mcp-memory incremental indexer                  |
| `masks reflect`           | `docs/specs/masks-reflect/`           | CLI PR-opener: branch, commit diff, push, `gh pr create` |
| `ooda-orient-synthesis`   | `docs/specs/ooda-orient-synthesis/`   | Weekly cross-Role synthesis pass; writes patterns to `personal/Memory/`; feeds `masks reflect` |
| `onboarding` skill        | `docs/specs/onboarding-skill/`        | Conversational Role + SELF.md setup             |
| `reflect` skill           | `docs/specs/reflect-skill/`           | Cross-role synthesis + SELF.md diff + PR description |
| `add-role` skill          | `docs/specs/add-role-skill/`          | Conversational credential collection            |
| `archive` skill           | `docs/specs/archive-skill/`           | Task folder archiving                           |
| `reference-refresh` skill | `docs/specs/reference-refresh-skill/` | Drive export + summary header                   |
| Cursor extension          | `docs/specs/cursor-extension/`        | Distribution plugin                             |
| Project blog              | `docs/specs/project-blog/`            | GitHub Pages Jekyll site + first post           |


---

## System-level requirements

These apply across all units. Any proposal that violates them is invalid regardless of unit-level metric scores.

### Hard constraints

1. **No personal content in `pirandello/`.** The repo is public and shareable. No SELF.md, ROLE.md, Memory files, credentials, or personal identifiers may be committed to it.
2. **Files are canonical; databases are regenerable.** No unit may design a workflow where the mcp-memory database is the source of truth. Every memory write starts as a file; the database is derived.
3. **Infrastructure enforces; instructions guide.** Reliability must come from shell hooks and the `masks` CLI, not from agent instructions or AGENTS.md conventions. If something must happen every session, it must be in a hook.
4. **Role isolation.** No unit may write to a Role's `Memory/` from a different Role's session context. Write-local is a hard constraint; global-read is a soft capability.
5. **Session root is the Role directory.** No unit may assume or require the workspace root to be the base directory or a subdirectory of a Role.
6. `**masks` commands are idempotent.** Every `masks` subcommand must be safe to run twice on a fully configured system with no side effects.
7. **`SELF.md` is never directly committed by an agent — with one exception.** The initial creation of `personal/SELF.md` during onboarding is a one-time bootstrap commit made directly to `main` by the onboarding skill. After that first commit, the only path to any `SELF.md` change is the `masks reflect` PR ritual. The bootstrap exception must be documented in `personal/git log` with the commit message `onboarding: bootstrap SELF.md`.
8. **Per-file size budgets are hard limits.** `SELF.md` ≤ 500 tokens. `ROLE.md` ≤ 500 tokens. Proposals that produce documents exceeding these per-file limits fail.
9. **Combined always-loaded budget is a warned threshold.** The combined token count of `SELF.md` + `ROLE.md` + `CONTEXT.md` should not exceed 1,500 tokens. The system warns when this threshold is crossed; no content is truncated or withheld. The user is responsible for keeping documents within the budget.
10. **The repo root must contain a `LICENSE` file.** MIT license. Any plan that omits it fails S-09.
11. **The repo root must contain a `README.md`.** It must explain what Pirandello is, state the license, and link to `docs/design.md`. It must contain no personal content. Any plan that omits it fails S-10.

### Soft constraints

- All shell scripts should be POSIX-compatible bash.
- Python code should target Python 3.10+ and be managed by `uv`.
- User-facing language should never expose file system paths or directory names.
- Git operations that can fail non-critically (push with no remote, pull with nothing new) must fail silently.

---

## Static evaluation metrics

These are system-wide checks. Unit-level proposals are additionally evaluated against their own metric tables.


| ID   | Name                      | Pass condition                                                                                               |
| ---- | ------------------------- | ------------------------------------------------------------------------------------------------------------ |
| S-01 | No personal content       | Proposal contains no personal data, credentials, or identifying content committed to `pirandello/`           |
| S-02 | Files canonical           | No proposed workflow makes the mcp-memory database the source of truth for any memory                        |
| S-03 | Hook-enforced reliability | Any behaviour described as "must happen every session" is implemented in a shell hook, not only in AGENTS.md |
| S-04 | Write-local respected     | No unit writes Memory/ files to a Role other than the one whose workspace is active                          |
| S-05 | Idempotent commands       | Every `masks` subcommand in the proposal can be run twice without error or unintended side effects           |
| S-06 | SELF.md PR-only           | No proposal includes a code path that commits directly to `SELF.md`, except the onboarding skill's one-time bootstrap commit (message: `onboarding: bootstrap SELF.md`); all subsequent changes must go through a `masks reflect` PR                                         |
| S-07 | Per-file size budgets     | No produced document exceeds its per-file token budget (SELF.md ≤500, ROLE.md ≤500)                           |
| S-08 | Combined budget warning   | When SELF.md + ROLE.md + CONTEXT.md exceeds 1,500 tokens, `start.sh` emits a warning; no content is truncated  |
| S-09 | LICENSE present           | The repo root contains a `LICENSE` file with MIT license text                                                    |
| S-10 | README present            | The repo root contains a `README.md` that describes the project, states the license, and links to `docs/design.md`; contains no personal content |
