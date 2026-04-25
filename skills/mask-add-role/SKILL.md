# Skill: mask-add-role

Complete **interactive** Role setup after `masks add-role <name>` created directories, templates, git, and hooks.

## Rules

1. **One credential question per model turn** — never batch keys.
2. Never paste full `.env` / `.env.example` contents; name each official `KEY` once in plain language.
3. After each answer, rewrite the Role `.env` entirely: keys in **exact order** from Pirandello `/.env.example`, each key exactly once, empty values as `KEY=`.
4. Re-invocation is safe: re-read `.env` and continue from the next unanswered key.

## Key catalog (keep synced with repo `/.env.example`)

| Key | Human label | Hint if stuck |
|-----|-------------|---------------|
| `MASKS_BASE` | Base directory | Usually auto-set by `masks setup`; confirm absolute path. |
| `MCP_MEMORY_DB_PATH` | Memory search database file | Defaults to `~/.pirandello/memory.db`; safe to leave blank. |
| `PIRANDELLO_ROOT` | Framework checkout | Path to this repo clone (hooks, guards, templates). |
| `MASKS_LLM_CMD` | Heartbeat LLM command | Optional override for `masks run`. |
| `MASKS_INTERACTIVE_CMD` | Interactive runner | Optional; used by `masks add-role -i`. |
| `GWS_ACCOUNT_WORK` | Work Google account label | Short name used with `gws --account`, e.g. `work`. |
| `GWS_ACCOUNT_PERSONAL` | Personal Google account label | Often `personal`. |
| `GMAIL_REFRESH_TOKEN` | Gmail OAuth refresh token | Run your Google auth helper; skip if this role doesn't use Gmail. |
| `TODOIST_API_TOKEN` | Todoist API token | Todoist → Settings → Integrations → Developer. |
| `WORKBOARD_API_KEY` | WorkBoard API key | Skip if this role doesn't use WorkBoard OKRs. |
| `GITLAB_TOKEN` | GitLab personal access token | Skip if this role doesn't use GitLab automation. |
| `GITHUB_TOKEN` | GitHub personal access token | Skip if this role doesn't use GitHub APIs or PR automation. |

If new keys appear in `/.env.example`, add a row here before release.

## Signal sources merge

After the **last** key is confirmed:

1. Ask once: *“What signal sources should this role monitor?”*
2. Normalize the answer to **3–8 bullets** (calendars, mail, Todoist scopes, feeds, etc.).
3. Replace the body of the `## Signal Sources` section in `OODA.md` (from the heading through the line before the next `---` or `##`), preserving other sections untouched.

## Git remote (optional)

If the user supplies a remote URL and `origin` is unset, run `git remote add origin <url>`. Never overwrite an existing `origin` URL silently.

## Confirmation line

After each persisted key emit: `Saved <KEY> for this role.`
