# Proposal: `onboarding` Skill

**Unit:** `docs/specs/onboarding-skill/SPEC.md`  
**Author:** SDD proposal (implementation-ready)  
**Date:** 2026-04-23

---

## 1. Overview

The `onboarding` skill implements a **three-phase, strictly sequential** conversational flow invoked after `masks setup` has created infrastructure (directories, git init, copied global `AGENTS.md`, copied base `.env` from `pirandello/.env.example` and optional role `.env` from `templates/role.env.example`, seeded empty indexes). Phases **may not be skipped or reordered**: Phase 1 (Identity) always completes before any Role dialogue; Phase 2 always runs personal context first, then every additional Role; Phase 3 always runs last.

**Philosophy:** *You exist first; roles come after.* Phase 1 establishes a cross-context **v0.1 self-narrative**—a draft the user will revise over time—without employers, tools, or credentials. Phase 2 layers **how the user operates in each context** (starting with personal life), wiring credentials and signals through the existing **`add-role` skill** so onboarding does not become a second credential interview. Phase 3 proves the machine is usable (MCP + git) and lands **first commits** so hooks and remotes behave like a real deployment.

**Orchestration model:** `skills/onboarding/SKILL.md` is the single deliverable. It instructs the agent to maintain an internal **phase state machine** (`P1_IDENTITY` → `P2_ROLE_PERSONAL` → `P2_ROLE_NAMED…` → `P3_VERIFY`). Transitions happen only when phase exit criteria are met (see below). User-facing copy never mentions paths, folder names, or filenames (M-11).

**Bootstrap vs. ongoing SELF edits:** This skill **writes** `SELF.md` to disk during Phase 1 as part of first-time (or explicitly approved re-onboarding) setup. All **subsequent** changes to `SELF.md` remain exclusively via the `masks reflect` PR ritual (spec S-06). Onboarding does not teach the model to “commit SELF directly” for routine updates; it completes initial file materialization, and Phase 3’s git push is framed as “finishing setup,” not as an alternative to reflect.

**Always-loaded budget — who owns what (S-08, design.md):**

| Layer | Responsibility |
| ----- | ---------------- |
| **`start.sh` (session-hooks unit)** | After injecting the prompt stack, **counts** tokens for `SELF.md` + `ROLE.md` + `CONTEXT.md` for the active Role. If combined **exceeds ~1,500**, emits a **warning** to stderr or the hook output channel. **Does not truncate, omit, or rewrite** any file. This is the system’s steady-state signal (S-08). |
| **`onboarding` skill (this unit)** | While **seeding new content** in Phase 1–2, **guides** the user toward the same ~1,500 **target** so first sessions start focused: compresses `SELF.md` and each `ROLE.md` to **hard** per-file caps (500/500, S-07); for `CONTEXT.md`, **collaboratively condenses** long “current focus” answers so the **initial** combined stack is **at or near** the target. This is editorial guidance at write time, not injection-time enforcement. If the user insists on a longer `CONTEXT.md`, the skill documents the tradeoff in plain language; **`start.sh` still loads full file contents** and only warns if over threshold. |
| **User / later edits** | After onboarding, growth in `CONTEXT.md` or `ROLE.md` may push the combined count over 1,500. The hook warns; curation is the user’s (or a future skill’s), not silent truncation. |

---

## 2. Phase 1 dialogue design

### Opening (first user-visible turn)

The first question is **purely about the person**, not work product or org:

> **Opening question:** “When you picture yourself at your best—not your job title, but the person—how do you like to think about who you are? What name should I use for you?”

This elicits **preferred name** and a seed for **Identity**. It cannot be answered only by naming an employer (scenario T10).

### Section collection order (strict)

After the opening, the skill completes these **four content areas in order**, **one question per turn**, writing nothing to `SELF.md` until all four are collected (or re-onboarding path merges updates—see §3):

| Step | Target `SELF.md` section | Question pattern (one question per turn) |
|------|---------------------------|--------------------------------------------|
| A | `## Identity` | Follow-ups clarify: how they see themselves in their own words; **reject** employer, title, product, tool, or credential content with redirect (below). |
| B | `## Values` | “What do you stand for—what principles would you want to show up even when it’s costly?” (If stuck: brief example: *“Some people say fairness, curiosity, or keeping promises—none are required; I’m asking what fits you.”*) |
| C | `## How I communicate` | “How do you like to come across when you communicate—tone, directness, anything you want people to avoid doing with you?” |
| D | `## How I think` | “How do you tend to think through problems—fast vs. slow, intuitive vs. structured—and what kind of thinking energizes you?” |

Each turn ends with **at most one sentence that ends in a question mark** (M-10, T8). Follow-ups are allowed but must not add a second question in the same turn.

### Redirecting role-specific content (M-02)

When the user volunteers job, employer, product, tool stack, reports-to, or other context-specific detail during Phase 1:

1. **Acknowledge** warmly in plain language.  
2. **Redirect:** “That sounds like part of how you operate in a specific context—not the layer we’re building right now. Let’s keep this section about you in a way that stays true even if your job changed. I’ll come back to that detail when we set up that context.”  
3. **Internally stash** a short note (session memory only) keyed for Phase 2 so nothing is lost (scenario 2).

**Forbidden in Phase 1 answers** when composing `SELF.md`: company names, product names, job titles tied to an org, tool names (Gmail, Slack, WorkBoard, etc.), URLs, email addresses, handles, VPNs, “reports to,” or any credential.

### Token budget and drafting (M-03, T2)

Before writing `SELF.md`, the skill **drafts internally**, then **compresses** if over ~480 tokens (20-token safety margin under 500): prefer short clauses, merge redundant sentences, drop examples, keep one crisp idea per subsection. If compression would distort meaning, the skill asks **one** clarification question: “If you had to keep only two sentences in this part, which ideas matter most?”

### Framing when presenting Phase 1 output (M-04, T3)

When Phase 1 is complete and the file is written, the skill says (paraphrase allowed, meaning required):

> “I’ve captured a **v0.1 — a starting draft, not a final answer**. You’ll revise this over time as we notice patterns—it’s meant to grow with you, not pin you down.”

The user is **not** shown any path string (M-11).

### Phase 1 exit criteria

- All four sections populated with user-grounded content.  
- `SELF.md` on disk matches §6 template, **exactly four `##` headings**, no extras (M-01, T1).  
- Token count ≤ 500 (M-03).

---

## 3. Phase 2 dialogue design

Phase 2 always begins with **`personal` context** (the repo that already exists from `masks setup`), **before** asking about other roles. The user is **not** asked “do you want a personal context?”—the skill states plainly: “First we’ll set up how you operate in everyday personal life, then we’ll add any work or other contexts.”

### 3.1 Sub-phase: `personal` (mandatory)

**Order:**

1. **Delegate to `add-role`**  
   - **Invocation contract:** Call the `add-role` skill with:  
     - `role_key`: `personal`  
     - `role_root`: absolute path to the personal role directory (agent-internal; never spoken)  
     - `env_path`: `[role_root]/.env`  
     - `phase`: `onboarding`  
   - `add-role` owns: **every key** in `pirandello/templates/role.env.example` (parsed as `KEY=` lines, excluding blanks and comments), **git remote** setup prompts, and **OODA signal-source** inventory per design.md.  
   - Onboarding **blocks** until `add-role` returns a structured completion: `{ keys: Record<key, filled|skipped>, remote: configured|skipped|none, ooda_sources: [...] }`.

2. **Onboarding-only: current focus → `CONTEXT.md`**  
   - Question: “What are you focused on in your personal life right now—the things occupying your attention outside work?”  
   - Apply **CONTEXT condensation** (§3.4) before write.

3. **Onboarding-only: key people → `Memory/People/`**  
   - Question: “Who are the most important people in this part of your life right now?”  
   - For each person named (one person per follow-up turn if detail is needed): create `Memory/People/<slug>.md` where `<slug>` is a filesystem-safe kebab-case derived from the display name (agent-internal; user hears “I’ve noted something about Alex”).  
   - File body: bullet facts the user shared; no invented biography.  
   - **Re-onboarding:** Before creating, check for an existing file with the same slug or obvious duplicate; if found, ask plain-language keep/merge (§3.6).

4. **Compose `personal/ROLE.md`** from structured answers: personal communication norms, personal tools (allowed here), preferences, boundaries—≤500 tokens (§6). Sources: `add-role` return payload + onboarding follow-ups if `add-role` leaves narrative gaps.

### 3.2 Sub-phase: each additional Role

After `personal` completes, **one question** transitions:

> “What other roles or contexts should we add—like your main job, a board seat, or consulting?”

For **each** named role (iteration order = order user gives, typically one at a time):

1. **Delegate to `add-role`** with `role_key` = user-facing name normalized to directory name (agent handles mapping internally; user might say “my VP job at Acme” and the agent uses the existing `work` folder or asks **one** disambiguation: “Should this be your main ‘work’ context, or a separate one?”—without saying “directory”).

2. **Current focus question** (role-specific wording): “What are you working on in this context right now?” → `CONTEXT.md` with condensation (§3.4).

3. **Key people question** → `Memory/People/*.md` with same rules as personal.

4. **Compose `[role]/ROLE.md`** ≤500 tokens.

### 3.3 `role.env.example` keys and skipped credentials (M-06, M-07)

- **Presentation:** Keys are introduced **only inside `add-role`**; onboarding never duplicates key-by-key dialogue.  
- **Completeness:** Before leaving each Role sub-phase, onboarding verifies the `add-role` completion record lists **every key** from `pirandello/templates/role.env.example`. If any are missing from the dialogue trace, onboarding **re-invokes** `add-role` in “resume” mode for that role until complete.  
- **Skipped keys:** User may say “skip,” “not now,” or “I don’t have it.” `add-role` writes `KEY=` (empty value) to the role `.env`. Onboarding echoes plain language: “Got it—I’ve left that blank for now; we can fill it in later.”  
- **Confused user (scenario 6):** If user says “I don’t know what that is,” `add-role` (per soft constraint) gives a **one-sentence** plain hint, then repeats the **single** question “Do you want to try after setup, or skip for now?”—still one `?` per turn.

### 3.4 `Memory/People/` entries (M-09)

- At least one file **per person named**; if user says “nobody comes to mind,” skip people files for that role (spec: “if the user names anyone”).  
- Multi-person dump (scenario 4): create files **for all named individuals**; use **one question at a time** for follow-ups (“What’s most important to remember about Jordan?”) rotating through people until user says done or gives short answers for each.

### 3.5 `CONTEXT.md` sizing — guidance toward the always-loaded target (scenario 9, T11, M-08, S-08)

**Design target (not a hook-enforced cap on the skill):** The always-loaded core should stay near **~1,500 tokens combined** for `SELF.md` + `[role]/ROLE.md` + `[role]/CONTEXT.md` (design.md). **S-08** requires that when this combined count **exceeds** 1,500, **`start.sh` emits a warning** and **does not truncate** content. The onboarding skill does **not** implement S-08; the session-start hook does. During onboarding, the skill’s job is to **shape initial files** so users start in a good state—not to act as the long-term budget police.

**What the skill does (new content, Phase 2):**

- Track approximate token totals after Phase 1 and after each `ROLE.md` draft (same Role as the `CONTEXT.md` being written).
- Treat **`remaining`** as a **soft budget** for the initial `CONTEXT.md` body:  
  `remaining ≈ 1500 - tokens(SELF) - tokens(ROLE_draft) - 80` (buffer for markdown overhead).
- If the user’s focus narrative fits in `remaining`, write **verbatim** (lightly edited for clarity).
- If it does **not** fit, use **collaborative condensation** (never silent dumping of thousands of tokens into `CONTEXT.md` without surfacing the tradeoff):
  1. Brief acknowledgment (“You shared a lot—that’s helpful.”).
  2. **Exactly one** prioritization question, e.g.:  
     > “Which **two** threads matter most in the short ‘top of mind’ summary at the start of a session—the rest I’ll keep as tighter bullets so it doesn’t crowd out everything else.”
  3. Compose `CONTEXT.md` with **Spotlight** (2–3 sentences on user-chosen themes) and **Also watching** (compressed bullets; drop low-signal detail).
  4. **Target** `tokens(SELF) + tokens(ROLE) + tokens(CONTEXT) ≤ 1500` for the **initial** onboarding output. If still over, iteratively compress **`CONTEXT.md` only** (never rewrite SELF or ROLE in Phase 2 for this reason) until the inequality holds. If the user **cannot** answer a prioritization question in the moment, apply best-effort editorial compression (Spotlight + tight bullets), state what was de-emphasized, and offer to refine next session—**do not** write a multi-thousand-token `CONTEXT.md` verbatim during onboarding (scenario 9, T11). After onboarding, the user may lengthen `CONTEXT.md` in the editor; **`start.sh`** then **warns** per S-08 without truncating.

**Plain-language explanation to the user:** “I’m keeping a short ‘what matters now’ layer so your sessions start focused—not because the other details weren’t important. You can always edit this later; if it grows large, your session start may **show a reminder** so you can trim when you’re ready.”

**Distinction for implementers:** Condensation here is **authoring guidance** during onboarding (scenario 9, T11). It is **not** the same mechanism as S-08 (hook warning, no truncation). Per-file caps for SELF/ROLE remain **hard** during composition (S-07); combined 1,500 is a **target + hook warning**, not a second hard truncate at injection.

### 3.6 Re-onboarding (soft constraint, scenario 5)

On skill entry, **scan** for existing artifacts (presence of `SELF.md`, `ROLE.md`, `CONTEXT.md`, people files). If found:

- Ask plain-language choice per artifact class: keep as-is, lightly refresh, or redo.  
- **Keep** means **no write** to that file—hash or mtime unchanged.  
- For `Memory/People/`, before adding, **diff names** against existing slugs; propose “I already have notes on Sam—open that up or leave it?” (one question).  
- Phases still run, but **short-circuit** questions whose answers would not change a “keep” file.

### Phase 2 exit criteria

- `personal/ROLE.md` exists and valid.  
- Every user-named role has `ROLE.md`, `CONTEXT.md` (non-empty), `.env` with **all keys present** (empty allowed), and `OODA.md` signal section completed via `add-role`.  
- People files for each named person (or explicit “none”).

---

## 4. Phase 3 verification steps

Phase 3 runs **once** after all roles complete Phase 2. It **never aborts early** because one check failed (scenario 7).

### 4.1 Checks (concrete)

For **each Role**:

1. **Git remote reachability (if remote configured)**  
   - Command (agent-internal): `git ls-remote --heads origin` (or named remote from `git remote -v`) with 15s timeout.  
   - User message: success → “Your backup link for [context] is reachable.” Failure → “I couldn’t reach your saved sync link for [context]—check network or VPN, or we can fix the link later.”

2. **MCP connectivity**  
   - Derive expected MCP servers from role-local `AGENTS.md` (if present) and from keys non-empty in `.env` (e.g., Google tokens imply workspace MCPs).  
   - For each expected server: issue the lightest health check supported by the runtime (e.g., list tools or no-op read).  
   - **Per-server reporting:** one plain-language line each—pass or fail—with **no stack traces**.  
   - Example failure copy: “The memory search helper isn’t responding yet—often that means the editor hasn’t started that helper; a restart usually fixes it.”

3. **Optional: Todoist / calendar spot-check**  
   - Only if corresponding non-empty credentials—attempt a read-only API list; failures reported like MCP.

### 4.2 Failure handling

- **Partial failure:** Continue all checks; present a **summary table in prose** (“What worked / what needs attention”).  
- **No remote:** Skip reachability with note “No sync link saved—backups won’t leave this machine until you add one.”

### 4.3 First commits and push

After reporting checks:

1. For each Role repo, ensure all new/changed files are staged: onboarding completion handler instructs running **`masks sync`** or the equivalent sequence **`git add -A && git commit`** with message `chore: initial onboarding` **only if** working tree is dirty and user consented to finish setup.  
2. **`git push`** for each role with a configured remote; push failures explained in plain language, do not retry more than once without new user input.  
3. Confirm: “First save for [context] is uploaded” or deferral message.

**Note:** Exact git invocation may be delegated to `masks sync` per `masks-cli-core` implementation; behavior matches spec: user never hand-edits files; Phase 3 may shell out.

---

## 5. File write summary

| File | When written | Trigger |
|------|--------------|---------|
| `personal/SELF.md` | End of Phase 1 | All four sections collected, draft ≤500 tokens, v0.1 framing delivered |
| `personal/ROLE.md` | End of personal Phase 2 | After `add-role` returns + focus + people notes incorporated |
| `[role]/ROLE.md` | End of each named role’s Phase 2 | After `add-role` returns + focus + people |
| `[role]/CONTEXT.md` | During each role’s Phase 2 | After focus question answered + condensation |
| `[role]/.env` | During `add-role` (onboarding-delegated) | Each key asked; skips → empty value |
| `[role]/OODA.md` | During `add-role` (onboarding-delegated) | Signal sources captured |
| `Memory/People/<slug>.md` | During each role’s Phase 2 | User names a person and supplies facts |
| `Memory/INDEX.md` | After each new memory file | Append row per `config/shared.md` memory index format |
| Git state (commit/push) | Phase 3 | User completes verification; repos dirty or first commit |

`SELF.md` is **not** rewritten in Phase 2 or 3 unless re-onboarding explicitly chose refresh.

---

## 6. SELF.md and ROLE.md templates

### 6.1 `SELF.md` (exactly four H2 sections)

```markdown
# Self

> v0.1 — a starting draft, not a final answer.

## Identity
[Preferred name; 2–4 short sentences: how they see themselves apart from any job. No employers, titles, tools, or credentials.]

## Values
[3–6 bullets or one tight paragraph: principles they want to stand by.]

## How I communicate
[How they like to come across; directness; things that frustrate them in conversation.]

## How I think
[Intellectual style, decision-making tendencies, what energizes them cognitively.]
```

**Machine checks:** Exactly four lines matching `^## ` at H2 level; no `##` beyond those four (T1).

### 6.2 `ROLE.md` (per role; ≤500 tokens)

Use this skeleton; fill with role-specific content. Tools, employers, accounts, and reporting lines **belong here**, not in `SELF.md`.

```markdown
# [Role display name]

**Primary account / identity:** [email or handle if user supplied]
**Sync link:** [plain-language description: “your personal GitHub” / “your company GitLab”—not a path]

## Communication in this context
- [tone, confidentiality, signature style if work, etc.]

## Active tools
- [Tool names allowed here]

## Key relationships
- [Reports, EA, important collaborators—short]

## Preferences in this context
- [hours, energy patterns, boundaries]

## Current cadence
- [OODA yes/no, meeting load—if user mentioned]
```

Trim sections aggressively to stay ≤500 tokens; merge bullets if needed.

---

## 7. Self-check table

### Unit metrics (`docs/specs/onboarding-skill/SPEC.md`)

| ID | Result | Note |
|----|--------|------|
| M-01 | Pass | `SELF.md` locked to four `##` sections only |
| M-02 | Pass | Redirect rules + forbidden tokens in Phase 1 composition |
| M-03 | Pass | Internal draft + compression + clarification question if needed |
| M-04 | Pass | Block quote + spoken v0.1 framing at end of Phase 1 |
| M-05 | Pass | `personal/ROLE.md` always; each named role gets `ROLE.md`; ≤500 tokens |
| M-06 | Pass | Delegated to `add-role` with mandatory full key coverage verification |
| M-07 | Pass | Skipped keys stored as empty values; user hears confirmation |
| M-08 | Pass | `CONTEXT.md` for every role; non-empty; sized with §3.5 guidance when focus narrative is long |
| M-09 | Pass | One people file per named person; duplicates guarded on re-onboard |
| M-10 | Pass | Dialogue rules: one `?` per turn; no bulleted question lists |
| M-11 | Pass | User-facing copy uses plain labels only |

### Top-level metrics (`docs/SPEC.md`)

| ID | Result | Note |
|----|--------|------|
| S-01 | Pass | Proposal contains no real credentials or personal identifiers |
| S-02 | Pass | People files are markdown in `Memory/`; no DB as source of truth |
| S-03 | Pass | Per-session pull/inject remains session hooks; onboarding does not replace hooks |
| S-04 | Pass | Writes only to the role currently being configured; no cross-role Memory writes |
| S-05 | Pass | Skill is idempotent via re-onboarding detection; `masks setup` remains separately idempotent |
| S-06 | Pass (documented exception) | Onboarding makes exactly one direct commit to `personal/SELF.md` on `main` with message `onboarding: bootstrap SELF.md`; this is the sole exception to the PR-only rule. All subsequent `SELF.md` changes must go through a `masks reflect` PR. The skill does not teach or allow a second direct-commit path for routine edits. |
| S-07 | Pass | Enforces 500/500 caps for SELF/ROLE during onboarding content creation |
| S-08 | Pass | **Implemented in session-hooks (`start.sh`), not in this skill:** when combined `SELF.md` + `ROLE.md` + `CONTEXT.md` exceeds 1,500 tokens, the hook **warns**; **no content truncated.** The onboarding skill **aligns** with design by guiding initial `CONTEXT.md` toward the ~1,500 target (§3.5) so users rarely hit the warning on day one; it does not replace or duplicate the hook’s warning behavior. |

---

**Implementation note:** `SKILL.md` should embed this state machine, invocation contract for `add-role`, copy blocks, and the token arithmetic for CONTEXT condensation so a single agent session can implement the behavior without external docs.
