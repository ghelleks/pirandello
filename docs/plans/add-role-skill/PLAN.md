# Proposal: `add-role` Skill

**Unit:** `add-role` skill  
**Spec:** `docs/specs/add-role-skill/SPEC.md`  
**Design:** `docs/design.md`  
**Deliverable:** `skills/mask-add-role/SKILL.md` (agent instructions only; no personal content in `pirandello/`)

---

## 1. Overview

### Scope of the skill

The `add-role` skill completes **interactive** Role setup after `masks add-role <name> --interactive` has already performed all **infrastructure** work: created `$BASE/<name>/`, copied `templates/.gitignore`, copied `templates/OODA.md`, copied `templates/role.env.example` → `$BASE/<name>/.env`, initialized git, installed hooks, and seeded `Memory/`, `Reference/`, `Archive/` with `INDEX.md` files.

The skill **owns**:

- Conversational collection of a value (or deliberate blank) for **every** `KEY=` entry in the canonical `pirandello/templates/role.env.example`, written into the Role’s `.env` in **the same key order** as the template.
- Optional `**git remote add origin <url>`** (or equivalent safe wiring) when the user supplies a URL.
- Collection of **OODA signal sources** and **merging them into** the Role’s existing `OODA.md` under the **Signal Sources** section so `beckett run` and future OODA sessions see an accurate, role-specific list.

The skill **does not** create directories, copy templates, install hooks, or run `git init` — that remains `masks add-role`.

### Invocation contexts


| Entry point                           | Inputs the agent must have                                                                                                                                                                                                                                                                   |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `masks add-role <name> --interactive` | **Role name** `<name>`, **absolute path** to `$BASE/<name>/.env`, and **absolute path** to the Role root (`$BASE/<name>/`). The CLI sets `MASKS_BASE` and may set `PIRANDELLO_ROOT` to the `pirandello` clone path before spawning the skill.                                                |
| User says “add a new role” in session | Agent asks: “What should we call this role?” then ensures infrastructure exists. If the directory is missing, agent instructs user to run `masks add-role <name>` from their environment (no filesystem paths in user-visible copy). If the directory exists, agent resolves paths as below. |


### Resolving paths without exposing paths to the user

- **Role root:** Prefer the **workspace root** when it is a Role directory (contains `ROLE.md` or `.env` seeded from setup). Otherwise use the path passed by the CLI.
- **Framework root (`pirandello/`):** Resolve in order: environment variable `PIRANDELLO_ROOT` → read `$BASE/AGENTS.md` symlink target file; the directory containing `AGENTS.md` in that target path is the framework repo root. Fallback for developers: default clone location (never print to user).
- **Canonical key list:** Parse `KEY=value` lines from the framework’s `templates/role.env.example` (ignore comments and blank lines). That ordered list is the **only** source of which keys to ask about (satisfies M-01 dynamically when keys change).

---

## 2. Credential collection dialogue

### Rules (all turns)

1. **One key per model turn:** exactly one question, one confirmation, then stop for the user (M-04).
2. **Never** paste or quote the contents of `.env`, `role.env.example`, or a bulk list of keys (M-05).
3. Each question **names** the setting in plain language and states the **official env key name** once, e.g. “Next is your **memory search database file** — the technical name is `MCP_MEMORY_DB_PATH`.” Naming the key is required; dumping the file is forbidden.
4. After each value is persisted (or skipped), emit the confirmation line (section 5).
5. If the user says they don’t know where to get a value, reply with **one** short hint (soft constraint), then repeat **the same single question** and wait (do not advance).

### Parsing and writing `.env`

- **Read** the current Role `.env` into a map.
- For each key in `templates/role.env.example` order: update map, then **rewrite the entire `.env`** with:
  - Same key order as `templates/role.env.example`.
  - Every key present exactly once.
  - Value empty string → line `KEY=` (M-03).
  - Values escaped so newlines and `#` in values cannot break the file (use quoted form only if needed; prefer simple `KEY=value` when safe).
- **Skipped** means user says “skip”, “none”, “not using”, or presses enter on an optional prompt — record `KEY=`.

### Question templates by key

The committed `pirandello/templates/role.env.example` is the source of truth. The shipped `SKILL.md` must include a **catalog** mapping each key to `{human_label, explanation, where_to_find, hint_if_stuck}`. Below is the **initial catalog** to keep in sync with the first committed template (adjust only when `role.env.example` changes).


| Key                    | Human label                  | Plain-language question (abbreviated; full prose in SKILL.md)                              | Where to find                                                                               | Hint if stuck                                                                                                                |
| ---------------------- | ---------------------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `MASKS_BASE`           | base directory               | Confirm the Pirandello base path for this machine.                                         | Usually written by `masks setup`.                                                           | Should match the parent folder that contains this Role directory.                                                            |
| `GWS_PROFILE`          | Google Workspace (gws) label | Ask for the **gws** profile name Calendar/Mail guards should use for **this** Role.        | The short account label you configured when you ran **gws** OAuth for this Google identity. | Often matches the Role folder name (`work`, `personal`); must match a profile **gws** already knows — tokens live in gws config, not in `.env`. |
| `MCP_MEMORY_DB_PATH`   | memory search database file  | Ask for the file Pirandello uses for semantic memory search.                               | Same place you chose when you first set up Pirandello; often pre-filled in your home setup. | Explain it is the local search index file (not your notes); it is safe to leave blank for a lightweight role and fill later. |
| `PIRANDELLO_ROOT`      | framework checkout path      | Optional override for hooks/guards source.                                                 | Path to the `pirandello` git clone if not using the bundled `_data/` assets.                | Most installs leave blank.                                                                                                   |
| `MASKS_INTERACTIVE_CMD`| interactive runner           | Optional command for `masks add-role -i`.                                                  | Advanced; leave blank for defaults.                                                         | Skip unless customizing.                                                                                                   |
| `TODOIST_API_TOKEN`    | Todoist API token            | Ask for the Todoist token for task integration.                                            | Todoist → settings → integrations → developer.                                              | Point to developer settings in plain language; avoid saying “REST API”.                                                      |
| `WORKBOARD_API_KEY`    | WorkBoard API key            | Ask for the WorkBoard key if this role uses OKRs and workstreams there.                    | WorkBoard account or admin-provided API credentials.                                        | “If you don’t use WorkBoard in this role, skip.”                                                                             |
| `GITLAB_TOKEN`         | GitLab personal access token | Ask for a token used to push or open merge requests to company Git if applicable.          | GitLab → preferences → access tokens.                                                       | Skip for roles that do not use GitLab automation.                                                                            |
| `GITHUB_TOKEN`         | GitHub token                 | Ask for a GitHub token if this role uses GitHub APIs or PR automation.                     | GitHub → developer settings → tokens.                                                       | Skip if unused.                                                                                                              |


**Note:** If `role.env.example` contains keys not yet in the catalog, the implementer **adds a row before release** — the skill must not invent silent omission (M-01).

---

## 3. Signal source collection

### When

Immediately **after** the last credential key is written and confirmed, the skill asks **exactly** this prompt (or a trivial variation):

> “What signal sources should this role monitor?”

One conversational turn collects the answer; **follow-up only if** the user gives an empty reply — in that case ask once: “If nothing yet, say ‘none’ and we can add later.”

### What gets stored

- The user may list calendars, mailboxes, Todoist projects, feeds, chat systems, or other sources in **natural language**.
- The skill **normalizes** them into **3–8 short bullets** (confirm wording with the user in one sentence if the list is very long).
- The skill **writes into** `$ROLE_ROOT/OODA.md` by **replacing** the body of the `## Signal Sources` section (from the heading through the line before the next `---` or `##` heading, whichever comes first) with:

```markdown
## Signal Sources

- <bullet 1>
- <bullet 2>
...
```

- Preserve the rest of `OODA.md` (Agenda, Excluded, etc.) unchanged so `beckett doctor` can parse the agenda.

### Why not return structured data to the CLI only

Direct invocation has **no** CLI consumer. Writing `OODA.md` in place keeps **one** code path for the `beckett` runner (`OODA.md` is its spec), and avoids duplicating write logic in Python.

### Integration with `masks add-role`

Non-interactive `masks add-role` leaves the template `OODA.md` untouched except initial copy. Interactive flow **ends** with an `OODA.md` that reflects user intent without requiring a second tool invocation.

---

## 4. Git remote handling

### When

**After** signal sources are written to `OODA.md`, the skill asks:

> “Do you have a git remote URL for backups and sync for this role? You can paste a link, or say skip if you don’t use one yet.”

### Optionality (M-07)

- Accept **skip**, **no**, **later**, or empty refusal **without** re-asking, nagging, or “are you sure” (M-07).
- If the user skips: **do not** run `git remote`; summary states no remote configured and that they can add one later through normal git setup (plain language, no tutorial paths).

### Wiring when provided

1. `cd` to Role root (subprocess or documented shell step).
2. If `origin` is absent: `git remote add origin '<url>'`.
3. If `origin` exists:
  - If URL matches: confirm and continue.
  - If different: ask **one** yes/no: replace existing origin with the new URL. On yes: `git remote set-url origin '<url>'`. On no: leave as-is; summary says remote unchanged.
4. On **any** `git` error (invalid URL, network, permissions): **one** plain-language failure line, mark remote as “not configured” in the summary, and **continue** to the final summary — no retry loops (anti-pattern in scenarios).

### Confirmation

After successful configuration:

> “Got it — I’ve connected git backup for this role.”

(No URL echoed if it contains embedded credentials; optional host-only echo is acceptable.)

---

## 5. Confirmation and summary

### Per-key confirmation (M-06)

After persisting each key:

- **Value provided:** `Got it — I’ve set <human label> for this role.`
- **Skipped / blank:** `Got it — I’ve left <human label> blank for this role for now.`

Use the **human label** from the catalog, not the raw value.

### Final summary (M-08)

Always produced in the **same** turn after remote handling completes, regardless of skips or git failure:

```markdown
### Role setup summary

**Saved for this role**
- <human label>
- ...

**Left blank for now**
- <human label>
- ... (or “None — everything we asked about has a value.”)

**Background loop will watch**
- <short recap of signal bullets, or “Nothing listed yet.”>

**Git backup**
- Configured / Not configured / Failed to configure (you can try again later)

You can change any of this later without re-running the whole flow.
```

No filesystem paths, no `.env` dump.

---

## 6. Open decisions (resolved)


| Question                                     | Decision                                                                                                                                                                                                                                                                                                  |
| -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| What if `role.env.example` is missing?       | Abort credential phase immediately. One user-facing message: Pirandello’s installer may be incomplete; reinstall or update Pirandello, or run `masks add-role` from a machine with a complete framework checkout. **Do not** guess keys. Implementer may log technical path in stderr for debugging only. |
| Signal sources: skill vs CLI?                | **Skill writes `OODA.md` directly** in the Role directory.                                                                                                                                                                                                                                                |
| Order: remote vs signal sources?             | **Credentials → signal sources → git remote → summary.** Matches hard constraints 5 then 6 in the unit spec (signal prompt immediately after credentials; remote follows).                                                                                                                                |
| Re-invocation on an already configured Role? | Overwrite `.env` keys in template order with newly collected answers; merge or replace Signal Sources per above; remote logic unchanged. Document in SKILL.md as “safe but re-asks all keys.”                                                                                                             |


---

## 7. Self-check table

### Unit metrics (`docs/specs/add-role-skill/SPEC.md`)


| ID   | Result | Note                                                                                   |
| ---- | ------ | -------------------------------------------------------------------------------------- |
| M-01 | Pass   | Parser iterates every `KEY=` from `templates/role.env.example`; catalog must cover all shipped keys. |
| M-02 | Pass   | Each question includes non-technical explanation + where to find + optional hint.      |
| M-03 | Pass   | Rewrites full `.env` with `KEY=` for skips.                                            |
| M-04 | Pass   | Strict one-key-per-turn; no bulleted multi-key prompts.                                |
| M-05 | Pass   | No file dumps; only intentional key **names** as labels.                               |
| M-06 | Pass   | Confirmation after every key, including skips.                                         |
| M-07 | Pass   | Remote optional; skip without retry; git failure non-blocking.                         |
| M-08 | Pass   | Summary always includes set, skipped, signals recap, remote status.                    |


### Top-level metrics (`docs/SPEC.md`)


| ID   | Result | Note                                                                                                                  |
| ---- | ------ | --------------------------------------------------------------------------------------------------------------------- |
| S-01 | Pass   | Proposal contains no real credentials or personal identifiers; only template text.                                    |
| S-02 | Pass   | Skill does not treat mcp-memory DB as canonical; only sets path in `.env`.                                            |
| S-03 | Pass   | No “every session” behavior delegated to this skill; hooks unchanged.                                                 |
| S-04 | Pass   | Writes only `$BASE/<role>/.env` and `$BASE/<role>/OODA.md` for the active Role.                                       |
| S-05 | Pass   | Idempotency remains `masks add-role` responsibility; skill is re-runnable without corrupting repo structure.          |
| S-06 | Pass   | Skill never touches `SELF.md`.                                                                                        |
| S-07 | Pass   | Skill does not expand `SELF.md` / `ROLE.md` / always-loaded stack beyond design budgets; signal bullets kept concise. |


