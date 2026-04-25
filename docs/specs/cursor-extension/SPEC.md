# SDD Spec: Cursor Extension

**Context:** See `docs/spec.md` for full system design. This spec covers the Cursor extension that installs Pirandello on a fresh machine without the user touching a terminal.

**Deliverables:** A publishable Cursor extension in `extension/` within the pirandello repo.

---

## Requirements

### Hard constraints

1. The extension must be installable from the Cursor extension marketplace without terminal access.
2. On first install (fresh machine), the extension must perform the following in order, with visible progress:
   - Clone `https://github.com/[org]/pirandello` to `~/Code/pirandello/` if not already present.
   - Install `masks` via `uv tool install ~/Code/pirandello/cli/`.
   - Run `masks setup` to create the base directory structure, copy AGENTS.md from bundled package data, deploy hook scripts, and seed credential templates.
   - Launch the `onboarding` skill conversationally inside Cursor's chat interface.
3. The extension must be idempotent: if `~/Code/pirandello/` already exists and `masks` is already installed, re-installing or reloading the extension must produce no changes and not re-launch onboarding.
4. The extension must register session-start and session-end hooks (`.cursor/hooks.json`) for any workspace whose root directory is a valid Role directory. A valid Role directory is defined as: contains `ROLE.md`, is a direct child of the base directory (`$MASKS_BASE` or `~/Desktop`), and is a git repository.
5. Hook registration must be automatic — the user must not manually configure hooks.
6. Uninstalling the extension must not delete, modify, or otherwise affect: Role directories, SELF.md, Memory/ files, Archive/ contents, git history, or any `.env` files.
7. The extension must not run a background process after the initial setup is complete.
8. `uv` must be available for the install step. If `uv` is not installed, the extension must display a clear error with installation instructions and halt.

### Soft constraints

- The installation progress should be visible to the user (e.g., output panel or notification).
- If onboarding is interrupted (user closes Cursor mid-flow), the extension should offer to resume onboarding on next launch.
- The extension should work on macOS. Linux and Windows support is a future consideration, not a requirement for Phase 6.

---

## Proposal format

### 1. Overview
Extension architecture: what runs at install time, what runs at workspace-open time, and what runs at session boundaries.

### 2. Install flow
The exact sequence of operations on first install. How each step's success/failure is detected before proceeding to the next. How the idempotency check is implemented.

### 3. Hook registration
How the extension detects that a workspace root is a valid Role directory. The format of `.cursor/hooks.json` it writes. What triggers re-registration (e.g., new Role added via `masks add-role`).

### 4. Onboarding launch
How the `onboarding` skill is invoked from within the Cursor extension context. Whether it runs in a Cursor chat panel, a webview, or another surface.

### 5. Uninstall safety
What the extension explicitly does not touch on uninstall. Whether any extension-written files (hooks.json) are cleaned up or left in place.

### 6. `uv` dependency
How the extension checks for `uv`. The error message shown when `uv` is absent. Whether the extension offers to install `uv` or only links to instructions.

### 7. Open decisions
Significant decisions the design doc does not resolve: exact marketplace metadata, extension ID and publisher, whether the pirandello repo URL is hardcoded or configurable, how onboarding resume state is stored.

### 8. Self-check table
See Static Evaluation Metrics.

---

## Static evaluation metrics

| ID | Name | Pass condition |
|---|---|---|
| M-01 | No terminal required | Full install completes on a fresh machine without the user opening a terminal |
| M-02 | Idempotent | Re-installing on an existing setup produces no file changes, no git operations, and does not re-launch onboarding |
| M-03 | Hook auto-registration | Opening any valid Role directory as workspace root automatically results in hooks.json being present with correct start/end hooks |
| M-04 | Uninstall safe | After uninstalling the extension, all Role directories, Memory/ files, SELF.md, and git history remain intact |
| M-05 | No background process | No extension process is running between Cursor sessions |
| M-06 | uv missing handled | If `uv` is not installed, the extension shows a clear error with installation instructions and does not attempt further steps |
| M-07 | Fresh machine complete | On a machine with only Cursor and uv installed, the full flow (clone → install → setup → onboarding) completes without error |
