# Pirandello — agent conventions

This file is the **global** `AGENTS.md`. It is symlinked from each Role's base directory so any workspace under that base discovers these rules. A Role may add a **local** `AGENTS.md` in the Role directory for tool-specific behavior; global rules always apply first.

## Workspace root

The **session root is the Role directory** (e.g. the folder named `work` or `personal` under your configured base). Do **not** treat the base directory or a task subfolder as the git root for Pirandello lifecycle behavior.

If the workspace root is wrong, session hooks skip destructive work and print a clear message — fix the opened folder, not the hooks.

## Roles model

- **Role** — A context (personal, work, etc.). Each Role is its own git repository under the base path.
- **Base** — Parent directory holding all Roles. Default base is the user's Desktop unless configured via `masks setup --base`.
- **SELF.md** — Cross-role working draft; lives only under `personal/`. Loaded in every Role session. Changes after onboarding go through the `masks reflect` pull-request ritual only (never direct commits from a session).
- **ROLE.md** — Per-role behavioral delta (tools, norms, custody). Required in every Role including `personal/`.
- **Memory/** — Curated markdown facts for that Role. **Write-local:** new facts discovered in a work session are written under **that Role's** `Memory/`, not under another Role's tree. Reading another Role's Memory for context is allowed when the user asks (global-read); writing there is not.

## Prompt stack (session start)

Hooks inject context in a fixed order. See `docs/design.md` § "The Prompt Stack" for the full list. Level-1 indexes (`Archive/INDEX.md`, `Memory/INDEX.md`, `Reference/INDEX.md`) may be injected; deeper archive and reference bodies use **progressive disclosure** — read the README or summary before opening whole folders.

## Task folders and archive

Active task folders live at the Role root (kebab-case). Each should have a `README.md` with title, status, summary, and key sections per `docs/design.md`. Completed work moves to `Archive/YYYY-MM/<folder>/` via the `mask-archive` skill; `Archive/INDEX.md` is updated first, then the folder is moved.

## OODA heartbeat (`beckett`)

Non-interactive OODA uses **`beckett run <path-to-role>`**. It reads `OODA.md`, runs pre-flight guards, and may invoke an LLM with OODA-only context. See `docs/design.md` (OODA section) and the `beckett` package docs for setup and cron.

## Tools and reliability

- **Infrastructure enforces; instructions guide.** Commits, pushes, and index updates are owned by hooks and the `masks` CLI — not by promises in chat.
- **`masks` CLI** — Install from this repository's `cli/` with `uv`. Commands include `setup`, `add-role`, `sync`, `status`, `doctor`, `index`, `reflect`, `reference-refresh` as implemented.
- **Credentials** — Never commit `.env` files. Base keys: `.env.example`. Per-role keys (including `GWS_PROFILE` for **gws**): `templates/role.env.example`.

## Size and context discipline

- **SELF.md** and **ROLE.md** each target ≤500 tokens (per-file hard limit in product specs).
- **Combined** `SELF.md` + `ROLE.md` + `CONTEXT.md` targets ≤1500 tokens; when exceeded, session start **warns** — it does not truncate injected content.

## Further reading

Full system design, custody model, and examples: **`docs/design.md`**.
