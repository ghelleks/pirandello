# Pirandello — agent conventions

This file is the **global** `AGENTS.md`. It is copied into the base directory and each Role directory by `masks setup`. A Role may add a **local** `AGENTS.md` in its directory for role-specific behavior; global rules always apply first.

## Workspace and roles

- **Base** — Parent directory holding all Roles (default: `~/Desktop`). Configured via `masks setup --base`.
- **Role** — A context (e.g. `personal`, `work`). Each Role is its own git repository under the base path.
- **Task folders** — Active work lives in kebab-case folders inside a Role directory. Each task folder has a `README.md` with title, status (active / complete / stale), summary, key outputs, and key decisions.

## Memory

### Reading from memory

When personal context is referenced without full details (my projects, my team, my priorities, stakeholders, etc.), search the MCP memory system using `memory_search` before responding. Examples:

- "my active projects" → search for project information
- "my team" → search for direct reports and team structure
- "this stakeholder" → search for stakeholder context
- "my priorities" → search for strategic priorities

Only search memory when context appears to be missing. Do not search if:
- The information is already in the conversation
- The question is general or hypothetical
- The user is asking you to store new information

### Writing to memory

Store persistent facts using `memory_store`. Tag memories by project, topic, and person so they are retrievable later. **Write-local:** facts discovered in a work session are stored with the role name as a tag; do not overwrite personal-context memories from a work session.

Never write to local `Memory/` markdown files as a substitute for memory storage. When the user asks you to remember something, confirm it was stored.

## Activity history

Git is the record of activity. Use `git log` to look up past work in a Role or task folder. Do not duplicate commit history into memory.

## Session lifecycle

`masks setup` installs session hooks. On session start, `start.sh` pulls the latest git changes and prompts you to retrieve context from MCP memory before proceeding. On session end, `end.sh` commits staged changes and pushes.

Before ending a session with meaningful work, write a descriptive final commit message rather than relying on the timestamped default.

## Credentials

Never commit `.env` files or credentials. Secrets stay in `.env` files that are gitignored.

## Further reading

Full system design and custody model: **`docs/design.md`**.
