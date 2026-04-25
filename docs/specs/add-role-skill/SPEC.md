# SDD Spec: `add-role` Skill

**Context:** See `docs/spec.md` for full system design. This spec covers the conversational skill that guides a user through configuring a new Role's credentials and signal sources without editing files manually.

**Deliverables:** `skills/mask-add-role/SKILL.md`. Invoked by `masks add-role --interactive` and directly by the user.

---

## Requirements

### Hard constraints

1. The skill receives a Role name and the path to the Role's `.env` file (pre-created from `templates/role.env.example` by `masks add-role`, with setup defaults already seeded).
2. For every key defined in `templates/role.env.example`, the skill must:
   - Ask for the value with a plain-language question that names the key and explains what it is and where to find it.
   - Write the provided value to the Role's `.env`.
   - If the user skips a key, write an empty string for that key (do not omit it from the file).
3. The skill must not show the raw `templates/role.env.example` file or `.env` file to the user.
4. The skill must ask about keys one at a time. It must not present a list of keys to fill in.
5. After all credential keys are handled, the skill asks: "What signal sources should this role monitor?" and collects inputs for the Role's `OODA.md` Signal Sources section.
6. The skill asks: "What's the git remote for this role?" Git remote is optional — if the user says they don't have one or want to skip, the skill records nothing and moves on without blocking.
7. If a git remote is provided, the skill writes it to the Role's git config (`git remote add origin <url>`).
8. The skill confirms each written value back to the user before proceeding to the next key. Format: "Got it — I've set [key name] for this role."
9. The skill produces a summary at the end: which keys were set, which were skipped, and whether a remote was configured.

### Soft constraints

- Explanations of what each key is should be written for a non-technical user — avoid jargon unless unavoidable.
- If the user seems confused about where to find a credential, offer a one-sentence hint before waiting for input.
- The skill should be usable for any Role, not just `work/`. Credential questions should be framed generically, not assuming a specific Role context.

---

## Proposal format

### 1. Overview
The skill's scope: what it configures and what it leaves to `masks add-role` (directory creation, template copying).

### 2. Credential collection dialogue
How each `templates/role.env.example` key is presented to the user. The question template (key name + plain-language explanation + where to find it).

### 3. Signal source collection
How OODA signal sources are collected and what the skill does with them (e.g., writes to OODA.md or passes back to `masks add-role`).

### 4. Git remote handling
How the remote question is asked, how optionality is communicated, and how the remote is wired if provided.

### 5. Confirmation and summary
The confirmation pattern after each key and the end-of-skill summary format.

### 6. Open decisions
What the skill does if `templates/role.env.example` is not found. Whether signal source collection writes to OODA.md or returns structured data to `masks add-role` for writing.

### 7. Self-check table
See Static Evaluation Metrics.

---

## Static evaluation metrics

| ID | Name | Pass condition |
|---|---|---|
| M-01 | All keys covered | Every key in `templates/role.env.example` is asked about; none skipped silently |
| M-02 | Plain-language questions | Each key question includes a non-technical explanation of what the key is |
| M-03 | Skipped keys written | Keys the user skips are written as empty strings in `.env`, not omitted |
| M-04 | One key at a time | The skill never presents multiple keys in a single turn |
| M-05 | No file exposure | The skill never shows `.env` or `role.env.example` file contents to the user |
| M-06 | Confirmation per key | After each key is written, the skill confirms with a human-readable message |
| M-07 | Remote optional | User can skip the git remote question without blocking progress; skill does not retry |
| M-08 | End summary | Skill produces a final summary listing set keys, skipped keys, and remote status |
