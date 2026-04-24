# SDD Scenarios: Pirandello (System Level)

**Companion spec:** `docs/SPEC.md`  
**Date:** 2026-04-23

These scenarios test properties that span multiple units. No single unit spec can cover them because they require the full system to be running — hooks firing, multiple repos, the mcp-memory database, and the synthesis-to-reflect pipeline working end-to-end. Each scenario references the system-level constraints (S-01 through S-10) from `docs/SPEC.md`.

---

## Use Cases

### 1. First day: fresh machine to working session

A colleague installs the Cursor extension on a new machine. They have no prior Pirandello installation. They complete onboarding (SELF.md, personal/ROLE.md, work/ROLE.md, credentials, first commits), open their first work session in Cursor, work for 90 minutes writing two Memory files and archiving a completed task folder, and close Cursor. That evening, `masks run work` fires from cron for the first time.

Questions the proposal must answer:
- After the first session closes, does the session-end hook commit and push to the work remote — without any user action?
- Does the post-commit hook fire and update the mcp-memory database for the two new Memory files — without any user action?
- Does `masks run work` at the next cron interval evaluate guards, determine nothing to do (inbox empty, no briefer window), log OODA_OK, and exit — without invoking any LLM?
- At no point in this sequence does the user need to run a terminal command, configure a hook, or manually trigger any system behavior?

System constraint references: S-03 (hook-enforced reliability), S-05 (idempotent setup from extension)

---

### 2. Write-local in practice: work session writes to work, not personal

A user is in a `work/` session. They ask the agent about a colleague, Frank Zdarsky, whose profile is in `personal/Memory/People/frank-zdarsky.md`. The agent reads the file (global-read). The agent then learns Frank has taken a new role and records this fact. The session ends; the hook commits.

Questions the proposal must answer:
- Does the new fact about Frank land in `work/Memory/People/frank-zdarsky.md` (write-local), not in `personal/Memory/People/frank-zdarsky.md`?
- Does `git log` on the personal repo show no new commits from this session?
- Does `git log` on the work repo show the new Memory file as part of the session-end commit?
- Is there now a Frank file in both repos — the personal one (owned by the person, predating this employment) and the work one (owned by the work context, capturing work-specific facts)?

System constraint references: S-04 (write-local)

---

### 3. Files are canonical: database lost and rebuilt

A user's mcp-memory SQLite-vec database file is accidentally deleted (disk cleanup, migration). They run `masks index work --rebuild` followed by `masks index personal --rebuild`. After the rebuild, they open a work session and ask a semantic query: "What do I know about vCPU pricing?"

Questions the proposal must answer:
- Does `masks index work --rebuild` regenerate all work Memory entries from the markdown files on disk, with no data loss?
- Does `masks index personal --rebuild` do the same for personal Memory?
- After both rebuilds, does the semantic query return the correct Memory files — the same results that would have appeared before the database was lost?
- Is there any information that was in the database but not in the markdown files — i.e., any information that is now permanently lost?

System constraint references: S-02 (files canonical, database regenerable)

---

### 4. The full reflection pipeline: synthesis → skill → CLI → PR → merge

Over three months, `ooda-orient-synthesis` has accumulated five synthesis observation files in `personal/Memory/Synthesis/`, two of which have strong evidence (≥3 sessions across ≥2 Roles). On a Sunday, synthesis runs, finds the two qualifying patterns, and updates their files. The following Monday, the user runs `masks reflect`. The `reflect` skill reads the synthesis files, produces a proposed SELF.md diff and PR description. `masks reflect` opens the PR on `github.com/user/personal`. The user reviews, edits one sentence, and merges.

Questions the proposal must answer:
- After synthesis runs, do the two qualifying pattern files in `personal/Memory/Synthesis/` contain the evidence and dates the reflect skill needs?
- Does `masks reflect` produce a PR whose diff exactly matches what the skill proposed?
- Does the PR land on `personal/` remote only — not the work remote, not the pirandello repo?
- After the user edits and merges, does `personal/SELF.md` on `main` reflect the merged content — neither the original nor the unedited diff?
- Does `personal/.reflect.log` record the PR URL so the next reflect run can query its disposition?

System constraint references: S-06 (SELF.md PR-only), S-07 (size budget enforced at merge)

---

### 5. ROLE.md update ceremony: isolated named commit

The synthesis pass identifies a pattern specific to the work Role — not a cross-role pattern. The pattern: the user consistently writes a one-paragraph executive summary before any longer document, across seven work sessions but no personal sessions. The agent writes this to `work/ROLE.md` in an isolated, named commit with an evidence note.

Questions the proposal must answer:
- Is this update committed separately from the session-end commit — i.e., does the work repo's git log show a distinct commit for the ROLE.md change?
- Does the commit message follow the prescribed format: `role(work): [description] — pattern from [session range]`?
- Does `masks status` surface this ROLE.md update for the user to review at their next role check-in?
- Is the SELF.md unchanged — the work-specific pattern correctly stayed in ROLE.md and was not promoted to SELF.md?

System constraint references: S-06 (SELF.md unchanged), S-04 (work pattern stays in work), design intent: update ceremony for ROLE.md

---

### 6. Multi-machine sync: CONTEXT.md last-write-wins

A user has two machines — a desktop and a laptop. On Monday morning they update `work/CONTEXT.md` on the desktop (session end hook pushes). That afternoon, they open a work session on the laptop; the session-start hook pulls and injects the updated CONTEXT.md. They make further edits to CONTEXT.md on the laptop. The laptop's session-end hook pushes. The next day the desktop session-start hook pulls.

Questions the proposal must answer:
- Does the session-start hook on the laptop get the desktop's CONTEXT.md version via `git pull`?
- Does the laptop's session-end hook push its changes to the remote without requiring manual intervention?
- When the desktop pulls the next morning, does it get the laptop's CONTEXT.md — last-write-wins?
- If there is a git merge conflict in CONTEXT.md (both machines pushed without the other pulling first), does `git pull --ff-only` fail silently rather than crashing the session-start hook?

System constraint references: S-03 (hook-enforced sync)

---

### 7. `pirandello/` repo stays clean across a full session

A user opens a work session, writes three Memory files, archives a task folder, and closes Cursor. The session-end hook commits and pushes to the work remote. The post-commit hook updates the mcp-memory database.

Questions the proposal must answer:
- Does `git log` on `~/Code/pirandello/` show no new commits from this session?
- Do the three new Memory files appear only in the work repo's git history, not in pirandello's?
- Is any part of `personal/SELF.md`, `work/ROLE.md`, or any `.env` file visible in pirandello's working tree?
- Could a person who clones pirandello from GitHub find any identifying information about the user in any commit?

System constraint references: S-01 (no personal content in pirandello/)

---

### 8. Custody model: correct remotes for each Role

A user has `personal/` pointing to `github.com/user/personal` and `work/` pointing to `gitlab.company.com/user/work`. After a week of sessions and OODA runs:

Questions the proposal must answer:
- Do all session-end commits from work sessions appear only in the company GitLab repo?
- Do all session-end commits from personal sessions appear only in the personal GitHub repo?
- Does `personal/Memory/` never appear in the company GitLab history?
- Does `work/Memory/` never appear in personal GitHub history?
- Could the company access only their designated remote and find only work-relevant content?

System constraint references: S-01, S-04, design intent: "Memory is unified in the mind, but has different custody in the world"

---

### 9. Always-loaded budget respected end-to-end

A user's system has been running for six months. `reflect` has run twice; SELF.md is at 490 tokens. The most recent work Role onboarding produced a ROLE.md at 480 tokens. During a session, the agent is asked to update CONTEXT.md with a very detailed status report — which would produce a 1,200-token document.

Questions the proposal must answer:
- When SELF.md (490) + ROLE.md (480) + a 1,200-token CONTEXT.md are injected at session start, does the system warn that the combined budget is exceeded?
- Is the warning surfaced to the user in a way they will notice — not silently swallowed?
- Is any content truncated or withheld from the agent as a result of the budget breach?
- Does `masks doctor` surface a budget alert and tell the user specifically how many tokens to trim from CONTEXT.md?
- Is budget monitoring implemented in infrastructure (hook + CLI), not only in AGENTS.md instructions?

System constraint references: S-07 (per-file size budgets), S-08 (combined budget warning), S-03 (infrastructure enforces)

---

### 10. Progressive disclosure end-to-end

During a work session, the user asks: "What happened with the vCPU pricing proposal last year?" The agent has `work/Archive/INDEX.md` injected (Level 1). It contains 50 rows.

Questions the proposal must answer:
- Can the agent identify the relevant folder (`vcpu-hour-prfaq`) from the INDEX.md summary alone — without reading any archived files?
- If the INDEX.md summary is sufficient to answer the question at a high level, does the agent stop at Level 1?
- If more detail is needed, does the agent read `Archive/2026-03/vcpu-hour-prfaq/README.md` (Level 2) before opening any other files in the folder?
- Does the agent reach Level 3 (full folder contents) only when neither the index nor the README answers the question?
- Does the session inject the indexes at session start without injecting any Level 2 or Level 3 content?

System constraint references: S-03 (hook-enforced injection), design intent: context window discipline

---

## Stress Tests

**T1 `pirandello/` gains no new commits after any session.**  
Running a complete session — Memory writes, task folder archival, CONTEXT.md update — produces commits in the Role repo and zero commits in `~/Code/pirandello/`.  
Pass: `git log ~/Code/pirandello/` is unchanged before and after any session; all session output lands in Role repos.

**T2 SELF.md on `main` is changed only by the onboarding bootstrap or a merged reflect PR.**  
`git log --format="%H %ai %s" personal/SELF.md` shows exactly two classes of commit: one initial commit with message `onboarding: bootstrap SELF.md`, and zero or more merge commits from `reflect/*` branches. No other commit messages are acceptable.  
Pass: every entry in `git log personal/SELF.md` has a message matching either `onboarding: bootstrap SELF.md` or a merge commit from a `reflect/*` branch.

**T3 Database rebuild restores full search capability.**  
Deleting the mcp-memory database file and running `masks index <role> --rebuild` for every Role produces a database that returns the same semantic search results as before deletion.  
Pass: a set of test queries run before deletion and after rebuild return the same Memory file paths.

**T4 Work Memory files appear only in the work git history.**  
After a work session that creates `work/Memory/People/alice.md`, the file appears in `git log` for the work repo and does not appear anywhere in `git log` for the personal repo.  
Pass: `git log --all --full-history -- "**/alice.md"` run from the personal repo returns zero results.

**T5 Every `masks` subcommand exits 0 when run twice on a configured system.**  
Running `masks setup`, `masks sync`, `masks status`, `masks doctor`, `masks index <role>`, and `masks reflect` (when no patterns qualify) twice in a row on a fully configured system produces no errors and no unintended side effects.  
Pass: a diff of all affected directories before and after the second run of each command shows zero changes; exit codes are 0.

**T6 Always-loaded budget breach triggers a warning.**  
When the combined token count of SELF.md + ROLE.md + CONTEXT.md injected at session start exceeds 1,500 tokens, `start.sh` emits a visible warning. All content is still injected in full.  
Pass: with a SELF.md + ROLE.md + CONTEXT.md combination that totals >1,500 tokens, the session preamble contains the budget warning; token-counting the injected `=== SELF ===`, `=== ROLE ===`, and `=== CONTEXT ===` sections confirms all content is present.

**T7 Every "must happen every session" behavior has a hook implementation.**  
All behaviors that the design doc describes as occurring at every session start or session end — pulling repos, injecting context, committing, pushing, updating the mcp-memory index — are implemented in shell hooks, not only in AGENTS.md instructions.  
Pass: for each required session behavior, the corresponding logic exists in `hooks/start.sh`, `hooks/end.sh`, or `hooks/post-commit.sh`; no required behavior exists only as an AGENTS.md instruction.

**T8 Cross-role patterns stay in `personal/` custody; role-specific patterns stay in their Role.**  
After a full reflect cycle, SELF.md contains only patterns that appeared in ≥2 Roles; ROLE.md files contain only patterns specific to that Role; no role-specific pattern has migrated into SELF.md; no cross-role pattern sits only in a ROLE.md.  
Pass: every entry in SELF.md is traceable to evidence in ≥2 Role's Memory files; every entry in any ROLE.md exists in that Role's Memory only.

---

## Anti-Pattern Regression Signals

**Session-critical behavior implemented only in AGENTS.md.** A behavior that must happen every session (context injection, auto-commit, credential sourcing) is described in AGENTS.md as an instruction rather than implemented in a shell hook. Symptom: sessions work when the agent follows instructions but silently fail when the agent is distracted or when a new agent runtime doesn't read AGENTS.md. Indicates: S-03 violated; infrastructure-enforcement principle not applied. Maps to: S-03.

**Memory written to `personal/` from a work session.** A work session writes a new memory file to `personal/Memory/` — a fact about a colleague, a decision, an observation. Symptom: personal repo accumulates work content; after an employment change, the personal GitHub repo contains company-specific facts; custody separation breaks down. Indicates: write-local rule (S-04) not enforced; agent instructions alone are insufficient. Maps to: S-04.

**`SELF.md` committed directly during a session.** An agent writes and commits `personal/SELF.md` without a PR — perhaps in response to a user saying "update my self-narrative." Symptom: the PR-as-ritual is bypassed; proposed changes are never reviewed; the `git log personal/SELF.md` shows session commits interspersed with reflect commits; the authorial record is contaminated. Indicates: S-06 violated; agent or skill not scoped correctly. Maps to: S-06.

**mcp-memory database treated as source of truth.** A workflow writes observations directly to the mcp-memory database without creating a markdown file first — perhaps for speed or convenience. Symptom: database entries exist with no corresponding file; `masks index <role> --rebuild` cannot restore them; after a database loss, that knowledge is permanently gone. Indicates: S-02 violated; file-first invariant broken. Maps to: S-02.

**Personal content committed to `pirandello/`.** A SELF.md draft, a ROLE.md, a Memory file, or a `.env` value is committed to `~/Code/pirandello/` — perhaps during a session opened at the wrong workspace root. Symptom: personal or confidential content appears in the public `pirandello` repo; colleagues who clone the framework inherit identifying information. Indicates: S-01 violated; session rooted in pirandello/ instead of a Role directory, or a skill wrote to the wrong path. Maps to: S-01.

**Always-loaded context exceeds 1,500 tokens without warning.** SELF.md grows to 600 tokens over successive reflect merges, or CONTEXT.md is written without a size constraint, and the session-start hook fails to emit the budget warning. Symptom: the effective context window available for work shrinks; quality degrades with no obvious cause; the user has no signal to act on. Indicates: S-07 or S-08 violated; hook budget check not implemented or silently suppressed. Maps to: S-07, S-08.

**`masks` commands not idempotent.** Re-running `masks setup` or `masks add-role` on an existing system overwrites credentials, duplicates hooks, or re-inits git repos. Symptom: `.env` files containing real credentials are replaced with empty templates; hook scripts accumulate duplicate entries; git repos are left in a conflicted state. Indicates: S-05 violated; idempotency guards not implemented. Maps to: S-05.
