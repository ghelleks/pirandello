# SDD Spec: `onboarding` Skill

**Context:** See `docs/spec.md` for full system design. This spec covers the conversational onboarding experience that produces SELF.md, ROLE.md(s), and seeds Memory/People/ and CONTEXT.md for each Role.

**Deliverables:** `skills/onboarding/SKILL.md`. Invoked by `masks setup` (post-infrastructure) and directly by the user.

---

## Requirements

### Hard constraints

1. The skill runs in three sequential phases. Phases must not be skipped.
2. **Phase 1 — Identity (once, ever):**
   - Must collect: name or preferred name; values (what the user stands for); communication style (tone, what to avoid, how directness shows up); thinking style (intellectual approach, decision-making, what energizes them).
   - Must produce a `personal/SELF.md` containing exactly four sections: `## Identity`, `## Values`, `## How I communicate`, `## How I think`.
   - `SELF.md` must contain no employer names, product names, credentials, tool names, or role-specific content. If the user offers role-specific content, redirect: "That sounds like something for your work ROLE.md — let's put it there."
   - `SELF.md` must be ≤500 tokens.
   - Must frame the document as "v0.1 — a starting draft, not a final answer."
3. **Phase 2 — Role setup (once per Role):**
   - **`personal/ROLE.md` is always set up first**, before any user-named Roles. The `personal/` Role is mandatory (required by the system) and always exists. The skill collects personal-context behavioral content (personal credentials, personal tools, informal communication norms) and writes `personal/ROLE.md`. This step is not optional and must not be skipped even if the user does not name `personal` as a Role.
   - After `personal/ROLE.md` is written, the skill asks: "What other roles do you play?" and proceeds through each user-named Role in the same sequence.
   - For each Role (and for `personal/` in the first pass), the onboarding skill **delegates credential and signal-source collection to the `add-role` skill**. It does not re-implement that dialogue. The `add-role` skill owns: per-key credential questions, git remote configuration, and OODA signal-source collection. The onboarding skill passes the Role name and `.env` path as context and resumes when the `add-role` skill returns.
   - After the `add-role` skill returns for a given Role, the onboarding skill collects two onboarding-specific items not covered by `add-role`:
     - Collect current focus: "What are you working on in this role right now?" → seeds `CONTEXT.md`.
     - Collect key people: "Who are the most important people in this role?" → seeds one `Memory/People/<name>.md` per person with whatever the user shares.
   - Must produce a valid `ROLE.md` for each Role (≤500 tokens).
4. **Phase 3 — Verification:**
   - Confirm that MCP connections defined in each Role's config are live.
   - Confirm that git remotes (if configured) are reachable.
   - Report the result of each check to the user.
   - Push all first commits for all configured Roles.
5. The skill must ask exactly one question at a time. It must not present a list of questions.
6. The user must never be asked to edit a file manually during onboarding. All file writes happen as a side effect of the conversation.
7. The skill must never use directory structure terminology with the user (e.g., do not say "I'm writing to `personal/SELF.md`"). Describe what is happening in plain language.

### Soft constraints

- The skill should feel like meeting someone, not configuring software.
- If the user seems uncertain about a question, offer a brief example before moving on.
- Re-onboarding (running on an already-configured system) should detect existing files and ask whether to update or keep them.

---

## Proposal format

### 1. Overview
The three-phase flow and the philosophy of "you exist first, Roles come after."

### 2. Phase 1 dialogue design
The opening question, follow-up patterns for each SELF.md section, and how to redirect role-specific content.

### 3. Phase 2 dialogue design
The per-Role question sequence. How `.env.example` keys are presented. How to handle skipped credentials. How Memory/People/ entries are created.

### 4. Phase 3 verification steps
What checks are run, how results are presented, and what happens when a check fails.

### 5. File write summary
A table of every file the skill writes, when it is written, and what triggers the write.

### 6. SELF.md and ROLE.md templates
The exact section structure the skill uses for each document, with placeholder language.

### 7. Self-check table
See Static Evaluation Metrics.

---

## Static evaluation metrics

| ID | Name | Pass condition |
|---|---|---|
| M-01 | SELF.md sections | Produced SELF.md contains exactly: `## Identity`, `## Values`, `## How I communicate`, `## How I think` |
| M-02 | SELF.md clean | SELF.md contains no employer names, credentials, tool names, or role-specific content |
| M-03 | SELF.md size | SELF.md is ≤500 tokens |
| M-04 | SELF.md framing | SELF.md is introduced to the user as "v0.1 — a starting draft" |
| M-05 | ROLE.md per role | A valid ROLE.md (≤500 tokens) is produced for every Role the user configures, including `personal/ROLE.md` which is always produced regardless of what Roles the user names |
| M-06 | All .env keys asked | Every key in `.env.example` is asked about; none silently skipped |
| M-07 | Skipped credentials | Keys the user skips are written as empty strings, not omitted from `.env` |
| M-08 | CONTEXT.md seeded | `CONTEXT.md` is written for each Role with the user's stated current focus |
| M-09 | People seeded | At least one `Memory/People/<name>.md` is created per Role if the user names anyone |
| M-10 | One question at a time | The skill never presents a list of questions; each turn ends with exactly one question |
| M-11 | No file path exposure | The skill never mentions file paths or directory names to the user |
