# Proposal: Cursor Extension (Pirandello Distribution)

**Unit:** `docs/specs/cursor-extension/SPEC.md`  
**Authoritative design:** `docs/design.md`  
**Deliverable location:** `extension/` in the `pirandello` repository (TypeScript VS Code extension targeting Cursor).

---

## 1. Overview

The extension is a **thin orchestration layer** with three lifecycles:

| Phase | When it runs | What runs |
| ----- | ------------ | --------- |
| **Install / activation** | First time the extension activates on a machine (or until bootstrap succeeds) | Pre-flight `uv` check → `git clone` (if needed) → `uv tool install` for `masks` (if needed) → `masks setup` (if needed) → optional onboarding launch |
| **Workspace open** | Whenever Cursor fires `onDidOpenWorkspaceFolder` / window focus with a single-folder workspace | Synchronous **Role validation** on the workspace root; if valid, **ensure** `.cursor/hooks.json` matches the canonical Pirandello hook definitions (write or no-op) |
| **Session boundaries** | Agent session start / end in Cursor | **No extension code** — Cursor invokes command hooks declared in `.cursor/hooks.json`, which delegate to the canonical shell scripts in `~/Code/pirandello/hooks/` |

**No daemon:** After bootstrap completes, the extension only wakes on Cursor events (activation, workspace changes). There is no `setInterval`, no `fs.watch` on the Desktop tree, and no long-running child processes owned by the extension.

**Cursor hook JSON contract:** Pirandello’s `start.sh` / `end.sh` emit plain text and shell semantics, while Cursor command hooks expect **JSON on stdin and JSON on stdout**. The extension therefore writes `.cursor/hooks.json` entries that point to **small wrapper scripts** checked into each Role’s `.cursor/hooks/` (created on first validation). Wrappers drain stdin, `cd` to `CURSOR_PROJECT_DIR`, run the framework scripts, and map stdout to `{"additional_context": "..."}` for `sessionStart` and `{}` for `sessionEnd`.

---

## 2. Install flow

All steps run via `child_process.spawn` / `execFile` from the extension host (Node). Progress streams to a dedicated **Output Channel** named `Pirandello` and to **progress notifications** (`window.withProgress`) with step labels. User-facing strings never quote internal paths (per top-level soft constraint in `docs/SPEC.md`); logs in the Output Channel may contain paths for support.

### Step 0 — `uv` pre-flight

- **Detection:** `spawnSync('uv', ['--version'], { encoding: 'utf-8' })` with `shell: false`. If `ENOENT` or non-zero exit → **halt**.
- **User-visible error (exact copy):**  
  *“Pirandello needs the `uv` Python tool installer. Install it from the official Astral guide, then reload Cursor.”*  
  Button: **Open install instructions** → `env.openExternal('https://docs.astral.sh/uv/getting-started/installation/')`.  
- No clone, install, setup, or onboarding runs after failure.

### Step 1 — Clone framework repo

- **Canonical path:** `~/Code/pirandello` (resolved with `os.homedir()`).
- **URL:** `https://github.com/pirandello-org/pirandello.git` (placeholder org; see §7).
- **Success predicate:** Directory exists **and** contains `.git` **and** `cli/pyproject.toml`.
- **If missing:** `git clone --depth 1 <url> <dest>`; failure → show error notification, stop.
- **If present and valid:** skip clone.

### Step 2 — Install `masks` CLI

- **Success predicate:** `spawnSync('masks', ['--help'], …)` exits 0 **or** `uv tool list` includes `masks` (implementation picks one stable check; primary is `masks --help`).
- **If missing:** `uv tool install ~/Code/pirandello/cli` (absolute path from step 1).
- **If present:** skip.

### Step 3 — `masks setup`

- **Invocation:** `masks setup` with cwd `homedir()`, env `PATH` inherited (so `uv` user shims are visible).
- **Skip predicate (any → skip this step):** Extension `globalState` key `pirandello.bootstrap.setupComplete === true` **or** disk probe finds `~/Desktop/personal/ROLE.md` **and** `~/Desktop/AGENTS.md` exists (symlink or file). The disk probe uses **resolved base** = `process.env.MASKS_BASE` if set, else `path.join(homedir(), 'Desktop')`.
- **Rationale for skip:** Satisfies **M-02** (no touching files when already configured). `masks setup` remains idempotent top-level (**S-05**), but the extension must not re-run it when already complete to avoid timestamp noise.
- **On success:** set `globalState` + `pirandello.bootstrap.setupComplete = true` and `pirandello.bootstrap.masksBase` to the base path used.

### Step 4 — Onboarding launch

- **Skip if:** `globalState.pirandello.bootstrap.onboardingComplete === true` **or** `personal/SELF.md` exists under `masksBase` **and** is non-empty (post–phase 1 marker).
- **Else:** invoke onboarding launcher (§4).
- **Resume:** If `globalState.pirandello.bootstrap.onboardingPhase` is `phase1_identity_done` or `phase2_roles_in_progress`, show `showInformationMessage` *“Continue Pirandello setup?”* **Continue / Later** — **Continue** runs launcher with resume hint only (does **not** re-run steps 1–3).

### Idempotency summary (M-02)

| Condition | Clone | `uv tool install` | `masks setup` | Onboarding |
| --------- | ----- | ----------------- | ------------- | ---------- |
| Valid repo + `masks` + `setupComplete` + onboarding complete | no | no | no | no |
| Valid repo + `masks` + `setupComplete` + onboarding incomplete | no | no | no | resume offer only |
| Partial (repo only) | no | maybe | maybe | after setup |

---

## 3. Hook registration

### Valid Role directory

A workspace folder root `R` is valid **iff all** hold:

1. **File:** `path.join(R, 'ROLE.md')` exists.
2. **Git:** `path.join(R, '.git')` exists (file or directory).
3. **Base child:** `dirname(R)` equals the resolved masks **base** path:
   - `masksBase = process.env.MASKS_BASE` if a non-empty string, else `path.join(os.homedir(), 'Desktop')`.
4. **Optional sanity (non-blocking):** `path.join(dirname(R), 'AGENTS.md')` exists — if missing, still treat as valid Role (user may have moved AGENTS.md); hooks still register.

**Non-Role workspaces:** If any check fails, the extension **returns silently** — no `hooks.json`, no warnings (**M-03** scenario 4).

### What gets written

**Path:** `<Role>/.cursor/hooks.json`  
**Path:** `<Role>/.cursor/hooks/pirandello-session-start.sh`  
**Path:** `<Role>/.cursor/hooks/pirandello-session-end.sh`

**`hooks.json` (canonical content):**

```json
{
  "version": 1,
  "hooks": {
    "sessionStart": [
      {
        "command": ".cursor/hooks/pirandello-session-start.sh",
        "timeout": 120
      }
    ],
    "sessionEnd": [
      {
        "command": ".cursor/hooks/pirandello-session-end.sh",
        "timeout": 120
      }
    ]
  }
}
```

Paths are relative to the Role root per Cursor project-hook rules.

**`pirandello-session-start.sh` (substantive behavior):**

- `#!/usr/bin/env bash`
- `cat >/dev/null` to consume hook JSON stdin.
- `cd "${CURSOR_PROJECT_DIR:-.}"` or fail soft with `{}`.
- `PIRANDELLO_HOME="${PIRANDELLO_HOME:-$HOME/Code/pirandello}"`
- `OUT="$(bash "$PIRANDELLO_HOME/hooks/start.sh" 2>/dev/null)"`
- Emit **one line** JSON: `python3 -c 'import json,sys; print(json.dumps({"additional_context": sys.argv[1]}))' "$OUT"` — if `python3` missing, fallback `node -e '...'` in implementation.

**`pirandello-session-end.sh`:**

- Drain stdin, `cd` to project dir, `bash "$PIRANDELLO_HOME/hooks/end.sh"`, then `echo '{}'`.

**Executable bit:** After write, `fs.chmod(path, 0o755)`.

### Idempotent write

- Compute SHA-256 of intended `hooks.json` and wrapper bodies.
- If on-disk files exist with **identical** content → **no write** (M-03 “already correct”).
- If `hooks.json` exists with different Pirandello-managed content → **overwrite** to restore contract (user manual edits to Pirandello hooks are replaced; document in README).

### Re-registration trigger

- **Only** `onDidOpenWorkspaceFolder` and **window focus** handlers that re-run validation when the active workspace root changes — **no** background watcher (**M-05**).
- New Role from `masks add-role` appears when the user opens that folder → same code path registers hooks (**scenario 8**).

---

## 4. Onboarding launch

**Surface:** Cursor **Agent / Chat** (Cmd+I style composer), not a webview.

**Mechanism (ordered):**

1. **Try** `vscode.commands.executeCommand` with a Cursor-specific chat-open command discovered during implementation (candidate family: `workbench.action.chat.open`, `aichat.newchataction`, or Cursor-documented equivalent). If the command accepts an `initialQuery` / `message` argument, pass the **onboarding seed** string below.
2. **If no programmatic submit API exists** in the pinned Cursor version:  
   - `env.clipboard.writeText(SEED)`  
   - `showInformationMessage` with localized text only: *“Your setup message is copied. Open Agent chat and paste to begin.”* (no raw paths)  
   - `commands.executeCommand` to focus the chat panel.

**Onboarding seed (single user message, ≤ ~400 English words):**

> You are helping me finish Pirandello onboarding. Open and follow the onboarding skill at `skills/onboarding/SKILL.md` in the Pirandello repo (already on this machine). Start at Phase 1 — Identity. Ask me questions one at a time; write files only as that skill specifies. Do not skip phases.

**Resume hint appended when `onboardingPhase !== not_started`:**

> We paused mid-setup; continue from the current phase recorded in my workspace without re-running machine setup.

**Skill invocation:** The extension does **not** embed the full onboarding dialogue — it delegates to the **`onboarding` skill** in-tree (**unit spec hard constraint**). The extension only opens the chat surface and supplies the first user turn.

---

## 5. Uninstall safety

On uninstall, VS Code / Cursor removes the extension package only. This extension **does not** contribute an `uninstall` hook script.

**Explicitly never touched by uninstall:**

- All Role directories under the user’s base path  
- `SELF.md`, `ROLE.md`, `Memory/`, `Archive/`, `Reference/`  
- Any `.env` or git history  
- `~/Code/pirandello` clone  

**`hooks.json` and wrappers:** **Left in place** (M-04). They are functional project files; removing them would break Pirandello for users who uninstalled only the extension. Users may delete `.cursor/` manually if they want hooks gone.

**Extension-owned state:** `globalState` / `workspaceState` in Cursor storage may remain as orphan prefs; harmless.

---

## 6. `uv` dependency

| Check | Implementation |
| ----- | --------------- |
| Before any network or git | `uv --version` |
| On failure | Modal notification + external link to Astral docs (see §2) |
| Auto-install `uv` | **Not offered** — enterprise proxies and user consent vary; scope stays support-only |

---

## 7. Open decisions

| Topic | Status |
| ----- | ------ |
| Marketplace display name, icon, README excerpt | Deferred to release prep; working title **“Pirandello”**. |
| Publisher ID & signing | Deferred (requires org Cursor marketplace account). |
| GitHub org in clone URL | **Hardcoded constant** `PIRANDELLO_REPO_URL` in `src/config.ts` for v1; add **hidden** `pirandello.experimental.repoUrl` setting only if fork testing demands it. |
| Exact Cursor command ID for chat automation | Determined in implementation spike against Cursor ≥ target version; clipboard fallback always shipped. |
| `python3` vs `node` for JSON escaping in wrappers | Prefer `python3` on macOS; CI tests both. |

---

## 8. Self-check table

### Unit metrics (`docs/specs/cursor-extension/SPEC.md`)

| ID | Result | Evidence |
| -- | ------ | -------- |
| M-01 | **Pass** | All steps use Node `child_process`; user never opens Terminal. |
| M-02 | **Pass** | Skip gates: repo present, `masks` present, `setupComplete` + onboarding flags; no duplicate writes; hooks compare-hash before IO. |
| M-03 | **Pass** | Role predicate explicit; auto-write `hooks.json` + wrappers on workspace open; silent for non-Roles. |
| M-04 | **Pass** | Uninstall touches nothing under base or `~/Code/pirandello`; hooks left intentionally. |
| M-05 | **Pass** | No watchers; event-driven only. |
| M-06 | **Pass** | `uv` checked first; link + halt. |
| M-07 | **Pass** | Fresh macOS with Cursor + `uv`: clone → install → setup → onboarding seed delivered. |

### Top-level Pirandello metrics (`docs/SPEC.md`)

| ID | Result | Evidence |
| -- | ------ | -------- |
| S-01 | **Pass** | Extension code only references public repo URLs and generic examples; no personal data in `pirandello/`. |
| S-02 | **Pass** | Extension never writes mcp-memory DB or treats it as canonical. |
| S-03 | **Pass** | Session start/end reliability remains in **shell hooks** + `hooks.json`; extension only installs them, does not replace hook enforcement with AGENTS prose. |
| S-04 | **Pass** | Extension does not write `Memory/` at all; onboarding skill runs in user session under correct Role workspace. |
| S-05 | **Pass** | Skips redundant `masks setup`; when run, underlying CLI remains idempotent per masks unit spec. |
| S-06 | **Pass** | No code path commits `SELF.md`; onboarding follows reflect ritual via skill instructions. |
| S-07 | **Pass** | Extension does not author `SELF.md`/`ROLE.md` content; seed message kept under always-loaded budget if ever injected as a doc (skill enforces budgets). |

---

## Implementation notes (repository layout)

```
extension/
├── package.json
├── src/
│   ├── extension.ts          # activate(), workspace listeners
│   ├── bootstrap.ts          # clone / uv / setup orchestration
│   ├── roleWorkspace.ts      # valid Role detection, hooks sync
│   ├── onboarding.ts         # chat launch + globalState resume
│   ├── config.ts             # URLs, base path resolution
│   └── hooks/
│       ├── session-start.sh.template
│       └── session-end.sh.template
└── README.md
```

`post-commit` hook installation remains **`masks setup`** responsibility (git hook inside each Role), not the extension — extension only guarantees Cursor session hooks via `.cursor/hooks.json`.
