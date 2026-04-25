# Pirandello — contributor conventions

This is the **development repo** for the Pirandello framework. Agents working here are building and maintaining the framework itself, not using it.

## Docs must stay in sync with code

`docs/design.md` is the authoritative description of how the system works. `docs/specs/` contains the formal requirements. `docs/specs/*/SCENARIOS.md` contain the acceptance criteria.

**Any change to observable behavior must update all three layers before the work is complete.**

| You changed | You must also update |
|---|---|
| How `masks setup` behaves | `docs/design.md` § The `masks` CLI, `docs/specs/masks-cli-core/SPEC.md`, `SCENARIOS.md` |
| Hook scripts or their content | `docs/design.md` § Hooks, `docs/specs/session-hooks/SPEC.md`, `SCENARIOS.md` |
| Where framework assets are resolved from | `docs/design.md` § Two Repos + Hooks, all affected specs |
| `masks run` guard contract | `docs/specs/masks-run/SPEC.md`, `docs/design.md` § OODA |
| `masks index` or `masks doctor` behavior | Corresponding spec and `docs/design.md` |
| Any file path, env var name, or CLI flag | Every spec, scenario, and design.md section that references it |

A PR that changes behavior in `cli/` without touching `docs/` is incomplete.

## Bundled assets live in `cli/masks/_data/`

Hook scripts, guard scripts, templates, `AGENTS.md`, and `.env.example` are bundled inside the Python package at `cli/masks/_data/`. `resolve_framework_root()` returns that path. **Do not** add logic that walks the filesystem to find the framework root — it will accidentally resolve to whoever's development checkout happens to be on the machine.

The root-level `hooks/`, `guards/`, and `templates/` directories are the canonical authoring location. After editing them, copy changes into `cli/masks/_data/` so they are bundled with the next install.

## Copy, never symlink

`masks setup` copies files to user-owned locations. It does not create symlinks. Symlinks break for users who installed the tool without cloning the source. When re-running setup, existing files are backed up (`.bak.<timestamp>`) before overwriting.

## Specs are the contract

Before implementing a behavioral change, update the spec. Before closing a PR, verify the scenarios still pass. The static evaluation metrics in each `SPEC.md` are the acceptance criteria — treat a failing metric the same as a failing test.
