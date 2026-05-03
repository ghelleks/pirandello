# SDD Spec: Session Hooks

**Context:** See `docs/spec.md` for full system design. This spec covers the two shell scripts that wire Pirandello's lifecycle into the agent runtime. `post-commit.sh` is removed — the MCP memory server is the persistence layer; `masks index` is available as an on-demand command only.

**Deliverables:** `cli/masks/_data/hooks/start.sh`, `cli/masks/_data/hooks/end.sh` — bundled inside the installed Python package and deployed to `~/.pirandello/hooks/` by `masks setup`.

---

## Requirements

### Hard constraints

1. The canonical source for both scripts is `cli/masks/_data/hooks/` inside the installed Python package. `masks setup` deploys them to `~/.pirandello/hooks/` — a stable, user-owned location that role hook configuration files reference. They are not role-specific; the Role is derived from `$PWD` at runtime.
2. Role is always `basename "$PWD"`. Base is always `dirname "$PWD"`. No parameters accepted.
3. **start.sh** must do `git pull --ff-only` on the current Role repo, and `git -C "$BASE/personal" pull --ff-only` if `$BASE/personal/.git` exists, before emitting any output. Both pulls must fail silently (`2>/dev/null || true`).
4. **start.sh** must emit a structured memory-retrieval prompt to stdout after the pull completes. The prompt must instruct the agent to search MCP memory for: identity and values context, current role priorities and active work, and any relevant project or task context — before responding to any user request.
5. **end.sh** must: `cd` to the Role directory; run `git add -A`; commit only if staged changes exist (`git diff --cached --quiet || git commit -m "session: $(date '+%Y-%m-%d %H:%M')"`); push (`git push 2>/dev/null || true`).
6. All git operations must fail silently — never abort a hook with an unhandled error.

### Soft constraints

- start.sh and end.sh are referenced by `.cursor/hooks.json` (pointing to `~/.pirandello/hooks/`). The proposal should address both installation targets.
- Hook scripts should be POSIX-compatible bash (not zsh-specific).

---

## Proposal format

The proposal must contain the following sections:

### 1. Overview
One paragraph describing the two hooks and how they interact.

### 2. Script implementations
Full shell script source for each hook, with inline comments on non-obvious logic only.

### 3. Installation targets
A table showing each hook, which runtimes it targets (Cursor, Claude Code), and the file path it is installed to.

### 4. Edge cases addressed
A bulleted list of edge cases the implementation handles: no staged changes, no remote configured, personal/ repo absent, etc.

### 5. Self-check table
See Static Evaluation Metrics.

---

## Static evaluation metrics

| ID | Name | Pass condition |
|---|---|---|
| M-01 | Role/base derivation | Both scripts derive role as `basename "$PWD"` and base as `dirname "$PWD"` with no parameters |
| M-02 | Pull before prompt | start.sh completes both git pull operations before emitting any output |
| M-03 | Memory-retrieval prompt | start.sh emits a prompt that names at least: identity/values, current priorities, and task-relevant context as search targets |
| M-04 | Conditional commit | end.sh commits only when `git diff --cached --quiet` returns non-zero |
| M-05 | Silent failures | Every git operation in both scripts uses `2>/dev/null || true` or equivalent |
