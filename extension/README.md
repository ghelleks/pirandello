# Pirandello VS Code / Cursor extension

TypeScript extension that:

- Verifies `uv` is installed.
- Ensures a `pirandello` framework checkout exists (clone if missing).
- Installs the `masks` CLI via `uv tool install` when absent.
- Runs `masks setup` once (tracked in global state).
- Copies Cursor **sessionStart** / **sessionEnd** wrapper scripts into `.cursor/hooks/` for valid Role workspaces.

## Build

```bash
npm install
npm run compile
```

Load the `extension/` folder with **Run Extension** from VS Code.
