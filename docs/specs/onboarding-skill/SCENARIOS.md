# SDD Scenarios: `onboarding` Skill

**Companion spec:** `docs/specs/onboarding-skill/spec.md`  
**Date:** 2026-04-23

---

## Use Cases

### 1. New user with a single work role

A first-time user starts onboarding. They have no `personal/SELF.md`, no Roles configured, and no credentials entered. They go through all three phases: Identity, Role setup (for `work`), and Verification.

Questions the proposal must answer:
- Does Phase 1 collect name/preferred name, values, communication style, and thinking style — in that conversational order — before Phase 2 begins?
- Does the produced `SELF.md` contain exactly the four sections `## Identity`, `## Values`, `## How I communicate`, `## How I think` and nothing else?
- Is the user never shown a file path during the process?
- Is `SELF.md` introduced as "v0.1 — a starting draft" rather than as a finished product?
- Does Phase 3 confirm the work git remote is reachable and push the first commit?

Metric cross-references: M-01, M-02, M-03, M-04, M-05, M-09, M-10, M-11

---

### 2. User offers employer name during Phase 1 (Identity)

During Phase 1, the user says "I'm a VP at Red Hat and I manage the RHEL business unit" when asked about their identity. This is role-specific content.

Questions the proposal must answer:
- Does the skill redirect this content to Phase 2 without losing it?
- Does the redirect happen with a natural, non-technical explanation (e.g., "That sounds like something for your work context — let's save it for that part")?
- Does the resulting `SELF.md` contain no employer name, no product name (`RHEL`), and no title (`VP`)?

Metric cross-references: M-02

---

### 3. User skips several credential keys during Phase 2

During the work Role setup, the user doesn't have their WorkBoard API key handy and skips it, along with two other optional credentials.

Questions the proposal must answer:
- Are skipped keys written as empty strings in `work/.env` (not omitted)?
- Does the skill confirm each skipped key with a human-readable message ("Got it — I've left that blank for now")?
- Does skipping credentials not block onboarding from progressing to the next key?
- Are all `.env.example` keys still asked about, even those the user is likely to skip?

Metric cross-references: M-06, M-07

---

### 4. User names multiple key people during Phase 2

During the work Role setup, when asked "Who are the most important people in this role?", the user names five colleagues and shares what they know about each.

Questions the proposal must answer:
- Does the skill create at least one `Memory/People/<name>.md` file for each person named?
- Does it populate each file with whatever the user shares (not just a placeholder)?
- Does it ask follow-up questions naturally (one at a time) to collect useful information for each person?

Metric cross-references: M-09, M-10

---

### 5. Re-onboarding on an already-configured system

A user who completed onboarding six months ago runs `masks setup` again (or directly invokes the onboarding skill). `personal/SELF.md` already exists, `work/ROLE.md` already exists, and `work/.env` already contains credentials.

Questions the proposal must answer:
- Does the skill detect the existing files and ask whether to update or keep them, rather than silently overwriting?
- Does "keep" mean the existing file is left completely unchanged?
- Does the skill avoid creating new `Memory/People/` entries that duplicate existing ones without asking?
- Does the user understand the choice they're being offered, in plain language?

Metric cross-references: M-01, M-05 (re-onboarding is the idempotency test for the skill)

---

### 6. User appears confused about a credential question

During Phase 2, the skill asks about the `GMAIL_REFRESH_TOKEN` key. The user responds "I have no idea what that is."

Questions the proposal must answer:
- Does the skill offer a brief, plain-language example or hint (e.g., "This is the token Google issues after you authorize the app — you'd get it by running the auth setup step") before waiting?
- Does it not abandon the question or silently skip the key?
- Does the explanation avoid technical jargon where possible, or explain jargon terms when unavoidable?

Metric cross-references: M-06 (all keys must be asked about)

---

### 7. Phase 3 verification fails for one MCP connection

A user completes Phase 1 and Phase 2. During Phase 3, the skill checks that MCP connections are live. The `mcp-memory` server is not running, but the Google Calendar connection is working fine.

Questions the proposal must answer:
- Does the skill report the mcp-memory failure clearly without aborting the entire Phase 3?
- Does it still confirm the working connections as successful?
- Does it tell the user what to do about the failed connection in plain language, not technical error messages?
- Does it still push the first commits for configured Roles after reporting the failures?

Metric cross-references: M-05 (ROLE.md per role), M-09 (Phase 3 verification)

---

### 8. Complete onboarding from blank slate — the primary experience

A new user has just installed Pirandello via the Cursor extension on a fresh machine. This is the scenario the entire onboarding skill exists to produce. They go through all three phases without interruption: Phase 1 (Identity), Phase 2 (personal/ ROLE.md first, then work Role via the add-role skill plus CONTEXT.md and key people), Phase 3 (verification and first commits).

Questions the proposal must answer:
- Does Phase 1 open with a question about the *person* — who they are, how they think of themselves — rather than their job or employer?
- After Phase 1, does the user feel that the skill understood something true about them that has nothing to do with their work?
- Does the transition from Phase 1 ("now let's talk about the contexts you operate in") feel like a natural next step, not a gear-shift into software configuration?
- After Phase 2, do both `personal/ROLE.md` and `work/ROLE.md` exist, each distinct, each ≤500 tokens?
- At the end of Phase 3, does the user have: a SELF.md, a personal/ROLE.md, a work/ROLE.md, a CONTEXT.md for each role, at least one Memory/People/ file for each role, and a confirmed first commit?
- At no point in all three phases does the user see a file path, run a terminal command, or need to understand the directory structure?

Metric cross-references: M-01 through M-11, M-05 (personal/ROLE.md mandatory)

---

### 9. User provides extensive current-focus content

During Phase 2, when asked "What are you focused on right now?" for the work Role, the user describes six active projects, three upcoming milestones, two strategic priorities, and four ongoing personnel situations in detail. The raw answer would produce a CONTEXT.md of approximately 2,000 tokens. `SELF.md` is at 450 tokens and `work/ROLE.md` is at 480 tokens, leaving roughly 570 tokens in the ~1,500-token always-loaded budget.

Questions the proposal must answer:
- Does the skill condense CONTEXT.md to fit within the remaining always-loaded budget rather than writing the user's full answer verbatim?
- If condensation requires editorial choices (which projects to foreground), does the skill ask the user what matters most, or does it decide unilaterally?
- Does the skill communicate in plain language that it's keeping the most relevant items so the document is always available at the start of every session?
- Does the proposal acknowledge that CONTEXT.md has a de facto size constraint imposed by the combined always-loaded budget, even though no explicit token limit is set for CONTEXT.md alone?

Metric cross-references: design intent: always-loaded tiers combined ≤1,500 tokens; M-08 (CONTEXT.md seeded)

---

## Stress Tests

**T1 `SELF.md` contains exactly four sections and nothing else.**  
The produced `SELF.md` has `## Identity`, `## Values`, `## How I communicate`, and `## How I think` — and no additional sections, no employer names, no credentials, no tool references.  
Pass: a structural check of the produced file finds exactly four second-level headers and no content that references an employer, tool, or role-specific information.

**T2 `SELF.md` is ≤500 tokens.**  
The produced `SELF.md` does not exceed 500 tokens regardless of how much content the user provides during Phase 1.  
Pass: token count of the produced file is ≤500; if the user provides very long answers, the skill condenses rather than appends.

**T3 `SELF.md` introduced as a draft, not a truth.**  
The skill explicitly frames `SELF.md` to the user as "v0.1 — a starting draft" (or equivalent) when producing it.  
Pass: the skill's output at the conclusion of Phase 1 includes language making clear the document is a starting point subject to revision.

**T4 A valid `ROLE.md` (≤500 tokens) is produced for every Role the user configures, plus `personal/ROLE.md` always.**  
After Phase 2 completes, every Role the user named has a `ROLE.md` present, and `personal/ROLE.md` exists regardless of whether the user named `personal` as a Role.  
Pass: for a user who names one Role (`work`), two `ROLE.md` files exist: `personal/ROLE.md` and `work/ROLE.md`; each is ≤500 tokens; a skill that only produces `ROLE.md` for user-named Roles fails this test.

**T5 Every key in `.env.example` is asked about — none skipped.**  
Phase 2 asks about every key in `.env.example` for each Role, including keys the user is likely to skip. No key is silently omitted.  
Pass: the skill asks about as many keys as `.env.example` contains; a skill that skips keys deemed "optional" fails this test.

**T6 Skipped credential keys written as empty strings in `.env`.**  
Keys the user declines to provide are written as `KEY_NAME=` (empty value) in the Role's `.env` file, not omitted from the file.  
Pass: `grep "SKIPPED_KEY" work/.env` returns a line with an empty value, not zero results.

**T7 `CONTEXT.md` is written for each Role.**  
Phase 2 asks "What are you focused on right now?" for each Role and writes a `CONTEXT.md` from the answer.  
Pass: after Phase 2, every configured Role has a non-empty `CONTEXT.md`.

**T8 Skill asks exactly one question per turn.**  
No turn in the onboarding conversation ends with more than one question. Lists of questions are never presented.  
Pass: reviewing the proposal's dialogue design, no turn includes a bulleted list of questions or multiple `?` sentences.

**T9 Skill never mentions file paths or directory names.**  
The user never sees strings like `personal/SELF.md`, `~/Desktop/work/`, `Memory/People/`, or any filesystem reference.  
Pass: the proposal's user-facing language uses plain descriptions ("your self-narrative", "your work context", "the people you mentioned") rather than technical paths.

**T10 Phase 1 opens with a question about the person, not their job.**  
The very first question in Phase 1 is about identity, values, or self-perception — not about employer, role, or tools.  
Pass: the proposal's Phase 1 opening question cannot be answered by naming a company or job title; a first question like "What company do you work for?" or "What's your job title?" fails this test.

**T11 CONTEXT.md is condensed when it would exceed the available always-loaded budget.**  
When the user's current-focus answer would produce a CONTEXT.md larger than the remaining always-loaded budget (≈1,500 tokens minus SELF.md minus ROLE.md), the skill condenses rather than writes verbatim.  
Pass: the produced CONTEXT.md, combined with SELF.md and ROLE.md, does not exceed 1,500 tokens regardless of how much the user provided.

---

## Anti-Pattern Regression Signals

**Role-specific content in `SELF.md`.** The produced `SELF.md` contains the user's employer, job title, or tool stack. Symptom: SELF.md says "VP at Red Hat, uses WorkBoard and Gmail." This content is work-specific and will be wrong or embarrassing when shared across roles or when the user changes jobs. Indicates: skill failed to redirect role-specific content to ROLE.md during Phase 1 collection. Maps to: M-02.

**Questions presented as a list.** The skill asks multiple questions in a single turn ("Tell me your name, your values, and how you like to communicate."). Symptom: user is overwhelmed; answers are rushed and shallow; SELF.md content is thin. Indicates: spec requirement M-10 violated. Maps to: M-10.

**Skipped `.env` keys omitted from the file.** Keys the user doesn't provide are simply not written to `.env`, leaving the file shorter than `.env.example` and causing silent failures when those keys are needed later. Symptom: `masks doctor` reports credential file present, but the tool requiring the skipped key fails with a confusing "variable not set" error. Maps to: M-07.

**Phase 2 proceeds without Phase 1.** The skill offers to skip `SELF.md` creation ("If you already have a self-narrative, we can skip this.") and goes straight to Role setup. Symptom: SELF.md doesn't exist; every subsequent session injects an empty `=== SELF ===` section. The foundational document is missing. Indicates: phase ordering is not enforced. Maps to: M-01 (phases must not be skipped per spec).

**File paths exposed to user.** The skill says "I've written your values to `personal/SELF.md`." Symptom: non-technical users feel like they're configuring software; the experience fails the "feels like meeting someone" test. Indicates: M-11 violation. Maps to: M-11.
