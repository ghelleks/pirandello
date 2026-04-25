# SDD Spec: Session Hooks

**Context:** See `docs/spec.md` for full system design. This spec covers the three shell scripts that wire Pirandello's lifecycle into the agent runtime.

**Deliverables:** `cli/masks/_data/hooks/start.sh`, `cli/masks/_data/hooks/end.sh`, `cli/masks/_data/hooks/post-commit.sh` — bundled inside the installed Python package and deployed to `~/.pirandello/hooks/` by `masks setup`.

---

## Requirements

### Hard constraints

1. The canonical source for all three scripts is `cli/masks/_data/hooks/` inside the installed Python package. `masks setup` deploys them to `~/.pirandello/hooks/` — a stable, user-owned location that role hook configuration files reference. They are not role-specific; the Role is derived from `$PWD` at runtime.
2. Role is always `basename "$PWD"`. Base is always `dirname "$PWD"`. No parameters accepted.
3. **start.sh** must output the following context items to stdout in the order listed below, each preceded by its exact labelled header. Items are divided into two groups:

   **Always emitted** (skipped only if the file does not exist on disk — which should not occur on a correctly configured system, but the script must not error if it does):
   - `=== GLOBAL AGENTS ===` → contents of `$BASE/AGENTS.md`
   - `=== SELF ===` → contents of `$BASE/personal/SELF.md`
   - `=== ROLE ===` → contents of `ROLE.md`

   **Conditionally emitted** (only output when the file exists; silently skipped otherwise):
   - `=== ROLE AGENTS ===` → contents of `AGENTS.md`
   - `=== CONTEXT ===` → contents of `CONTEXT.md`
   - `=== ARCHIVE INDEX ===` → contents of `Archive/INDEX.md`
   - `=== MEMORY INDEX ===` → contents of `Memory/INDEX.md`
   - `=== REFERENCE INDEX ===` → contents of `Reference/INDEX.md`
4. **start.sh** must pull the current Role's repo (`git pull --ff-only`) and `personal/` (`git -C "$BASE/personal" pull --ff-only`) before injecting context. Both pulls must fail silently (`2>/dev/null || true`).
5. **start.sh** must source `$BASE/.env` (if it exists) then `.env` in `$PWD` (if it exists) before any output.
6. **end.sh** must: `cd` to the Role directory; run `git add -A`; commit only if staged changes exist (`git diff --cached --quiet || git commit -m "session: $(date '+%Y-%m-%d %H:%M')"`); push (`git push 2>/dev/null || true`).
7. **post-commit.sh** must: detect changed `Memory/` files using `git diff --name-only HEAD~1 HEAD -- Memory/`; detect deleted `Memory/` files using `git diff --name-status HEAD~1 HEAD -- Memory/ | awk '/^D/{print $2}'`; exit 0 immediately if both are empty; otherwise source `$BASE/.env` and call `masks index "$(basename "$(git rev-parse --show-toplevel)")"`.
8. All git operations must fail silently — never abort a hook with an unhandled error.
9. `masks index` is called by path and must be available on `$PATH` when the hook runs.

### Soft constraints

- start.sh and end.sh are referenced by `.cursor/hooks.json` (pointing to `~/.pirandello/hooks/`) and mentioned in `CLAUDE.md` lifecycle sections respectively, in addition to `.git/hooks/post-commit` which delegates to `~/.pirandello/hooks/post-commit.sh`. The proposal should address all three installation targets.
- Hook scripts should be POSIX-compatible bash (not zsh-specific).

---

## Proposal format

The proposal must contain the following sections:

### 1. Overview
One paragraph describing the three hooks and how they interact.

### 2. Script implementations
Full shell script source for each of the three hooks, with inline comments on non-obvious logic only.

### 3. Installation targets
A table showing each hook, which runtimes it targets (Cursor, Claude Code, git), and the file path it is installed to in each target.

### 4. Edge cases addressed
A bulleted list of edge cases the implementation handles: missing files, no staged changes, no remote configured, first commit (no HEAD~1 for post-commit diff), etc.

### 5. Self-check table
See Static Evaluation Metrics.

---

## Static evaluation metrics

| ID | Name | Pass condition |
|---|---|---|
| M-01 | Role/base derivation | Both scripts derive role as `basename "$PWD"` and base as `dirname "$PWD"` with no parameters |
| M-02 | Context injection order | start.sh outputs all 8 labelled items in the specified order; the 3 always-emitted sections precede the 5 conditional sections |
| M-03 | Conditional injection | The 5 conditional sections (`=== ROLE AGENTS ===`, `=== CONTEXT ===`, and the three index sections) are only output when the file exists; the 3 always-emitted sections (`=== GLOBAL AGENTS ===`, `=== SELF ===`, `=== ROLE ===`) are not guarded by a file-existence check |
| M-04 | Pull before inject | start.sh pulls both repos before outputting any context |
| M-05 | Conditional commit | end.sh commits only when `git diff --cached --quiet` returns non-zero |
| M-06 | Silent failures | Every git operation in all three scripts uses `2>/dev/null \|\| true` or equivalent |
| M-07 | Post-commit guard | post-commit.sh exits 0 with no side effects when no `Memory/` files changed |
| M-08 | Post-commit deleted files | Deleted `Memory/` files are detected separately from changed files using `--name-status \| awk '/^D/'` |
| M-09 | First-commit safety | post-commit.sh handles the case where HEAD~1 does not exist (initial commit) without error |
