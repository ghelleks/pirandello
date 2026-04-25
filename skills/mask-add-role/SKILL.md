# Skill: mask-add-role

Complete **interactive** Role setup after `masks add-role <name>` created directories, templates, git, and hooks.

## Rules

1. **One credential question per model turn** — never batch keys.
2. Never paste full `.env` / `.env.example` contents; name each official `KEY` once in plain language.
3. After each answer, rewrite the Role `.env` entirely: keys in **exact order** from Pirandello `templates/role.env.example`, each key exactly once, empty values as `KEY=`.
4. Re-invocation is safe: re-read `.env` and continue from the next unanswered key.

## Key catalog (keep synced with repo `templates/role.env.example`)

| Key | Human label | Hint if stuck |
|-----|-------------|---------------|
| `MASKS_BASE` | Base directory | Usually auto-set by `masks setup`; confirm absolute path. |
| `GWS_PROFILE` | gws account profile | Short label passed to `gws --account` for Calendar/Gmail in this Role. Must match a profile you configured in **gws** (OAuth lives in gws config, not here). |
| `MCP_MEMORY_DB_PATH` | Memory search database file | Defaults to `~/.pirandello/memory.db`; safe to leave blank. |
| `PIRANDELLO_ROOT` | Framework checkout | Path to this repo clone (hooks, templates). |
| `MASKS_INTERACTIVE_CMD` | Interactive runner | Optional; used by `masks add-role -i`. |
| `TODOIST_API_TOKEN` | Todoist API token | Todoist → Settings → Integrations → Developer. |
| `WORKBOARD_API_KEY` | WorkBoard API key | Skip if this role doesn't use WorkBoard OKRs. |
| `GITLAB_TOKEN` | GitLab personal access token | Skip if this role doesn't use GitLab automation. |
| `GITHUB_TOKEN` | GitHub personal access token | Skip if this role doesn't use GitHub APIs or PR automation. |

If new keys appear in `templates/role.env.example`, add a row here before release.

## Signal sources merge

After the **last** key is confirmed:

1. Ask once: *“What signal sources should this role monitor?”*
2. Normalize the answer to **3–8 bullets** (calendars, mail, Todoist scopes, feeds, etc.).
3. If `OODA.md` exists, replace the body of the `## Signal Sources` section in `OODA.md` (from the heading through the line before the next `---` or `##`), preserving other sections untouched. Skip if there is no `OODA.md`.

## Git remote (optional)

If the user supplies a remote URL and `origin` is unset, run `git remote add origin <url>`. Never overwrite an existing `origin` URL silently.

## Confirmation line

After each persisted key emit: `Saved <KEY> for this role.`
