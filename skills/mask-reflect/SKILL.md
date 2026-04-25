# Skill: mask-reflect

Cross-role reflection: read `Memory/` trees, detect stable patterns, propose a **unified diff** for `personal/SELF.md`, and author PR metadata. **No git writes** — output strict JSON only.

## Inputs

- `SELF.md` at `BASE/personal/SELF.md`
- Each Role’s `Memory/` directory under `BASE/<role>/Memory/`
- Last ~50 lines of `personal/.reflect.log` to avoid duplicate PR themes (parse `REFLECT_PR` URLs)

## Eligibility heuristics

- Prefer patterns supported by **≥3 distinct session dates** OR **≥2 Roles**.
- `SELF.md` suggestions require evidence spanning **≥2 Roles**; single-role patterns belong in that Role’s `ROLE.md` / `Memory/` only.

## Output contract (stdout **only** — single JSON object, no prose)

```json
{
  "patterns_found": true,
  "proposed_diff": "--- a/SELF.md\n+++ b/SELF.md\n@@ ...",
  "pr_title": "Reflect: ...",
  "pr_description": "Markdown body for GitHub PR",
  "branch_name": "reflect/YYYY-MM-DD",
  "target_remote": "echo of `git remote get-url origin` from personal/",
  "role_md_suggestions": ["optional bullets"]
}
```

- When nothing meets thresholds: `{ "patterns_found": false }` (other fields omitted).
- `branch_name` must match `reflect/YYYY-MM-DD` (local date).
- `proposed_diff` must be a **unified diff** applicable from repo root of `personal/` with path `SELF.md`.

## Side effects

**None** on disk for this skill run — the `masks reflect` CLI performs all git/gh operations and `.reflect.log` writes.

## Invocation

Typically run inside an LLM session with repository context; for automation, the parent CLI may spawn a headless model runner that loads this skill specification verbatim.
