# Pirandello

Pirandello is a **file- and git-first** system for AI-assisted memory and configuration: multiple **Roles** (contexts), one cognitive model, hooks and a `masks` CLI so reliability lives in infrastructure—not chat promises.

## What you get

- A `**masks` CLI** (`cli/`) for setup, health checks, git sync, mcp-memory indexing, and an OODA heartbeat runner.
- **Session hooks** (`hooks/`) that pull repos, inject a fixed prompt stack, commit on session end, and re-index memory after commits.
- **Guard scripts** (`guards/`) used by `masks run` to decide when a scheduled LLM pass is warranted.
- **Agent skills** (`skills/`) for onboarding, archiving, reference refresh, synthesis, and reflection—see each `SKILL.md`.
- A **Cursor / VS Code extension** (`extension/`) that bridges the editor’s JSON hook protocol to the shell hooks (optional install).

Full system design: `[docs/design.md](docs/design.md)`. Unit specs live under `[docs/specs/](docs/specs/)`.

## Requirements

- **Cursor** or **Claude Code** for interactive sessions (hooks target both).
- **Python 3.10+** and **[uv](https://github.com/astral-sh/uv)** to install the `masks` package from `cli/`.
- **git** (each Role is its own repository under a configurable base directory).
- Optional `**gh`** when using GitHub-based `masks reflect` flows.

## Quick start

1. Clone this repository.
2. `cd cli && uv tool install .`
3. Run `masks setup` (optionally `masks setup --base /path/to/base`).
4. Open a **Role directory** (e.g. `…/personal` or `…/work`) as the workspace root in your editor.
5. Configure `[base]/.env` with `MCP_MEMORY_DB_PATH` and other keys from `.env.example`.

## Documentation

- `[docs/design.md](docs/design.md)` — authoritative architecture and custody model.
- `[docs/specs/](docs/specs/)` — SDD specs per component.

## License

This project is released under the **MIT License**; see `[LICENSE](LICENSE)`.

## Disclaimer

This repository is **public infrastructure and documentation** only. Personal Role content (memory files, credentials, agendas) belongs in private Role repos—not here.

## Blog

Project pages (Jekyll under `site/`) build via **GitHub Actions** when Pages “Build and deployment” is set to **GitHub Actions** in repository settings. Set `url` and `baseurl` in `site/_config.yml` to match your GitHub Pages host before publishing.