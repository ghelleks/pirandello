# SDD Scenarios: Cursor Extension

**Companion spec:** `docs/specs/cursor-extension/spec.md`  
**Date:** 2026-04-23

---

## Use Cases

### 1. Fresh machine — only Cursor and `uv` installed

A colleague installs the Pirandello Cursor extension from the marketplace on a laptop that has Cursor and `uv` but nothing else relevant. `~/Code/pirandello/` does not exist, `masks` is not on PATH, and `~/Desktop/` has no Role directories.

Questions the proposal must answer:
- Does the extension clone `pirandello` to `~/Code/pirandello/`?
- Does it run `uv tool install ~/Code/pirandello/cli/` to install `masks`?
- Does it run `masks setup` to create the base directory structure, copy AGENTS.md from bundled package data, deploy hook scripts to `~/.pirandello/hooks/`, and seed credential templates?
- Does it launch the `onboarding` skill in Cursor's chat interface?
- Is progress visible to the user during each step?
- Does the user never need to open a terminal?

Metric cross-references: M-01, M-07

---

### 2. Re-installing the extension on an already-configured machine

A user re-installs or reloads the extension on a machine where `~/Code/pirandello/` already exists and `masks` is already installed. All Roles are configured. Onboarding was completed months ago.

Questions the proposal must answer:
- Does the extension detect the existing pirandello installation and skip cloning?
- Does it detect that `masks` is already installed and skip the `uv tool install` step?
- Does it detect that `masks setup` has already been run and skip that step?
- Does it NOT re-launch onboarding?
- Is the overall result no file changes and no errors?

Metric cross-references: M-02

---

### 3. User opens a valid Role directory as workspace root

A user opens `~/Desktop/work/` in Cursor. The directory has `ROLE.md`, is a direct child of the base directory, and is a git repository. This is a valid Role directory.

Questions the proposal must answer:
- Does the extension automatically detect this as a valid Role workspace?
- Does it write (or verify) `.cursor/hooks.json` in `~/Desktop/work/` with the correct start and end hook configurations?
- Does this happen without the user manually configuring anything?
- If hooks.json already exists with correct content, is no change made?

Metric cross-references: M-03

---

### 4. User opens a non-Role directory — a regular project folder

A user opens `~/Code/my-python-project/` in Cursor. This directory has no `ROLE.md`, is not a direct child of the base directory, and is not a Pirandello Role.

Questions the proposal must answer:
- Does the extension do nothing for this workspace?
- Is no hooks.json written to this directory?
- Does the extension not produce errors or warnings for non-Role workspaces?
- Is the valid-Role detection logic clearly defined so non-Role directories are reliably excluded?

Metric cross-references: M-03

---

### 5. User uninstalls the extension

A user uninstalls the Pirandello extension from Cursor's extension manager.

Questions the proposal must answer:
- Do all Role directories remain intact — no files deleted or modified?
- Does `SELF.md` remain exactly as it was?
- Do all Memory/ files remain?
- Does git history in all Role repos remain intact?
- Do `.env` files remain unchanged?
- Does the proposal explicitly state what happens to `hooks.json` — is it cleaned up or left in place? (Either is acceptable, but the proposal must define which.)

Metric cross-references: M-04

---

### 6. `uv` is not installed

A colleague installs the extension on a machine where Cursor is present but `uv` has not been installed.

Questions the proposal must answer:
- Does the extension detect that `uv` is not available before attempting any install steps?
- Does it display a clear error message with installation instructions for `uv`?
- Does it halt and not attempt the remaining steps (clone, setup, onboarding)?
- Is the error message actionable — does it tell the user exactly where to get `uv`?

Metric cross-references: M-06

---

### 7. Onboarding interrupted mid-flow

A user starts onboarding (launched by the extension after fresh install) but closes Cursor partway through Phase 2, before Role setup is complete.

Questions the proposal must answer:
- Does the extension detect that onboarding was incomplete on the next Cursor launch?
- Does it offer to resume onboarding from where the user left off?
- How is onboarding resume state stored — and where?
- Does the extension not re-run `masks setup` or `uv tool install` when resuming (since those completed successfully)?

Metric cross-references: M-02 (idempotency of prior steps), M-07 (fresh machine complete)

---

### 8. New Role added via `masks add-role` after extension install

A user adds a new `consulting` Role using `masks add-role consulting` in a terminal after the extension is installed. They then open `~/Desktop/consulting/` in Cursor.

Questions the proposal must answer:
- Does the extension detect `~/Desktop/consulting/` as a valid Role directory on workspace open?
- Does it register hooks.json for this new Role automatically?
- Does this not require re-installing or reloading the extension?
- What triggers re-registration — workspace-open detection or a background watcher?

Metric cross-references: M-03

---

## Stress Tests

**T1 Full install completes on a fresh machine without a terminal.**  
On a machine with only Cursor and uv installed, the extension completes the full flow (clone → uv install → masks setup → onboarding launch) without the user opening a terminal.  
Pass: the entire sequence completes through Cursor's UI; no terminal interaction is required at any step.

**T2 Re-install is a complete no-op.**  
Re-installing or reloading the extension on an existing setup produces zero file changes, zero git operations, and does not re-launch onboarding.  
Pass: a diff of all affected directories before and after re-install shows no changes; onboarding does not open.

**T3 Hook auto-registration for valid Role directories.**  
Opening any valid Role directory (contains ROLE.md, is a direct child of base, is a git repo) as workspace root results in `.cursor/hooks.json` being present and correct without user action.  
Pass: opening a valid Role directory that previously had no hooks.json produces a valid hooks.json; opening a non-Role directory produces no hooks.json.

**T4 Uninstall leaves all data intact.**  
After uninstalling the extension, Role directories, Memory/ files, SELF.md, git history, and .env files are byte-for-byte identical to their pre-uninstall state.  
Pass: a checksum of all Role directory contents before and after uninstall shows no differences.

**T5 No background process after setup.**  
After initial setup completes, no extension process is running between Cursor sessions.  
Pass: checking the process list between Cursor sessions shows no Pirandello extension process.

**T6 `uv` absence handled with clear error.**  
When `uv` is not installed, the extension shows a human-readable error with installation instructions and takes no further action.  
Pass: the error message includes a URL or command for installing uv; no clone, no install, no setup is attempted.

**T7 Fresh machine end-to-end flow completes without error.**  
On a machine with only Cursor and uv, the complete flow — clone → install → setup → onboarding — completes without errors or manual intervention.  
Pass: at the end of onboarding, `personal/SELF.md` exists, `work/ROLE.md` exists, git repos are initialized, and hooks.json is present in each Role.

---

## Anti-Pattern Regression Signals

**Terminal required for any step.** One or more install steps (clone, uv install, masks setup) require the user to open a terminal and run a command manually. Symptom: a non-technical colleague fails to complete onboarding because they don't know how to open a terminal or run shell commands. Indicates: spec M-01 violated; step not implemented in the extension's UI flow. Maps to: M-01.

**Onboarding re-launches on already-configured machine.** Re-installing the extension triggers the onboarding skill even though SELF.md and ROLE.md already exist. Symptom: existing SELF.md is overwritten with a new v0.1; months of reflect-based refinements are lost. Indicates: idempotency check not implemented; extension always launches onboarding after install. Maps to: M-02.

**Valid Role directories not detected automatically.** Opening `~/Desktop/work/` in Cursor does not trigger hooks.json registration. Symptom: session-start and session-end hooks never run; context injection and auto-commit don't work; the entire Pirandello lifecycle is broken silently. Indicates: workspace-open event handler not implemented or Role detection logic too narrow. Maps to: M-03.

**Data destroyed on uninstall.** Uninstalling the extension removes Role directories or clears hooks.json. Symptom: user loses months of Memory files and git history when they try to clean up the extension. Indicates: extension's uninstall handler performs cleanup that was not scoped to extension-managed files only. Maps to: M-04.

**Background process left running.** After initial setup, the extension leaves a file watcher or polling process active between Cursor sessions. Symptom: battery drain; CPU usage visible in Activity Monitor; system performance degrades over time; spec M-05 violated. Indicates: extension uses a persistent watcher rather than workspace-open event for Role detection. Maps to: M-05.
