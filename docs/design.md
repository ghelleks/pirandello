# Pirandello

**Status:** draft  
**Date:** 2026-04-22  
**Author:** Gunnar Hellekson  
**Inspired by:** OpenClaw, Hermes Agent (Nous Research)

---

## A note on Pirandello

Luigi Pirandello was an Italian playwright and novelist who won the Nobel Prize in 1934. He is best known for *Six Characters in Search of an Author*, but the work most relevant here is his 1926 novel *One, No One, and One Hundred Thousand* (*Uno, nessuno e centomila*). In it, the protagonist Vitangelo Moscarda has a small revelation: his wife mentions that his nose tilts slightly to the right. He had never noticed. He begins to wonder: if he does not know his own face, what does he know about himself? And if every person who knows him sees a slightly different person — one Vitangelo to his wife, another to his banker, another to his employees — then which one is real?

Pirandello's answer: none of them, and all of them. You are "one" to yourself (a self-image, always incomplete), "no one" in the sense that the self you know does not exist for anyone else, and "one hundred thousand" in the aggregate of everyone else's perceptions. The novel ends with Moscarda dissolving his fixed sense of identity — selling his house, abandoning his name, living among strangers who make no prior assumptions about him — and finding it liberating. There is no stable, knowable self beneath the masks. The masks go all the way down.

This is a deliberately uncomfortable premise for a system that asks you to write a file called "`SOUL.md`". The response to that discomfort is not to pretend Pirandello is wrong, but to take his insight seriously and let it shape the design. If the self is not a truth to be revealed but a draft to be revised — the accumulating synthesis of roles worn consistently over time — then a "`SELF.md`" is not a description of who you *are* but a working draft of who you are *choosing to be*. The agent's job is research: it observes patterns across your sessions and surfaces them as raw material. Your job is editorial: you decide what earns a place in the next draft. And the ritual of revision — through evidence, proposal, and deliberate authorial consent — is itself the practice.

---

## World Model

This system is built on a specific set of beliefs about people, memory, and software. These beliefs drive every design decision. If you disagree with any of them, the design will feel wrong.

**A person is not their job.** The system centers the whole person, not any particular role. Memory, identity, and configuration exist to serve a human being — one who has a career, a family, interests, and a life that cannot be cleanly partitioned.

**The self is a draft, not a truth.** You behave differently at work than at home. You use different tools, different credentials, different communication norms. The roles accumulate into something we call a self — but that synthesis is never finished and never fully knowable. There is no face behind the masks; the masks, worn consistently and revised deliberately over time, *become* the face. (Pirandello: *one, no one, and one hundred thousand.*) `SELF.md` is not a truth to be revealed but a working draft — bootstrapped at onboarding, revised as patterns accumulate, never final.

**Memory is unified in the mind, but has different custody in the world.** Your knowledge of a colleague is yours — it predates and survives your employment. But your employer may have a legitimate interest in the record of your work decisions. The system respects this: one cognitive system for thinking, different git remotes for custody.

**Files are a more honest medium for memory than databases.** A markdown file can be read, edited, corrected, version-controlled, and understood without special tooling. A database cannot. When memory is files, a human is always in control of their own knowledge.

**Git is the universal backing store.** History, backup, multi-instance sync, and collaboration are all solved problems once memory is under git control. 

**Infrastructure enforces what matters; instructions guide everything else.** Hooks commit. Git pushes. Skills have defined steps. AGENTS.md asks nicely. The system is reliable not because the agent always remembers, but because the infrastructure catches what it misses.

**Simplicity is a feature.** Every tool, file, and convention must earn its place. If a colleague cannot understand the system in one onboarding session, it is too complex to share.

---

## Goals

1. A memory and configuration system that works reliably across two runtimes: interactive (Cursor/Claude) and non-interactive (OODA / Claude Code).
2. Simple enough to share with colleagues — minimal dependencies, obvious structure, installable from within Cursor or Claude without ever touching a terminal.
3. Uses files, folders, and git as the primary substrate — all human-readable, no special tooling required.
4. Context window discipline: a small always-loaded core plus progressive disclosure for everything else.
5. Reflects how human memory actually works: one cognitive system that serves multiple roles, not siloed databases per context.

---

## Key Concepts

The nouns used throughout this spec.

**Role** — a context in which a person operates: `personal`, `work`, a board seat, a consulting engagement. Each Role is a directory under the base path, a git repository, and a behavioral delta on top of the shared self-narrative. A remote is recommended for backup and multi-machine sync but not required. A person has at least two Roles: `personal` and one work-like role.

**Base** — the root directory under which all Roles live. Default: `~/Desktop`. Configurable via `masks setup --base`. The base holds a copy of the global `AGENTS.md` (placed there by `masks setup`), the cross-role `.env`, and nothing else — all substantive content lives in Role directories.

**Task Folder** — a working directory inside a Role for a specific piece of work (a proposal, an analysis, an investigation). Named in kebab-case. Contains a `README.md` and whatever artifacts the work produces. Active task folders live directly in the Role directory; completed ones move to `Archive/YYYY-MM/`.

**Session** — a single interactive conversation with the agent. The intended experience is to open the appropriate Role directory as the workspace root in Cursor or Claude Code — not the base directory, not a subdirectory. The Role directory is the unit of context: hooks fire relative to it, credentials are sourced from it, and the prompt stack is assembled from its contents. Opening the wrong directory means the wrong identity, the wrong tools, and no hook lifecycle. The session-start hook loads context; the session-end hook commits and pushes.

**Heartbeat** — a single OODA loop cycle. Runs every 15 minutes during active hours via `masks run <role>`. Pre-flight guards determine whether an LLM is invoked; most heartbeats are no-ops.

**Hook** — a shell script that fires at a lifecycle event. Three hooks: session-start (pulls, injects context), session-end (commits, pushes), post-commit (updates mcp-memory index if `Memory/` changed). Hooks are role-agnostic; the Role is derived from `$PWD`.

**Prompt Stack** — the ordered set of documents injected at session start: global `AGENTS.md`, `SELF.md`, `ROLE.md`, optional Role-local `AGENTS.md`, `CONTEXT.md`, and the three Level 1 indexes. Everything else is retrieved on demand via progressive disclosure.

**Memory** — curated facts stored as markdown files in `[role]/Memory/`. One file per subject (person, project, decision). Written by the agent during or after a session; never chunked; indexed in mcp-memory for semantic search.

**Archive** — completed task folders, moved from the Role root into `Archive/YYYY-MM/` by the archive skill. Each archived folder has a `README.md`; each Role has an `Archive/INDEX.md` summarizing what's there.

**Reference** — foundational documents in `[role]/Reference/`: strategy docs, charters, org context. Larger and more stable than Memory files. Each document opens with a ~500-word summary header; the full body is read only when the summary confirms it is needed.

`**masks`** — the CLI that owns system maintenance: setup, role management, heartbeat execution, git sync, synthesis, database indexing, and health checks. Managed by `uv`; no installation required beyond cloning `pirandello`.

---

## The Roles Model

A person wears many masks in life — professional, parent, board member, consultant. Each role has different credentials, different tools, and different behavioral norms. This system models that reality directly.

### The three documents

`**SELF.md`** — the working self-narrative. Lives in the personal Role. Read by every Role at session start. Contains the cross-role synthesis: values, communication style, how you think, what you stand for — not as fixed truths but as the current draft you've chosen to operate from. Bootstrapped at onboarding; revised over time through the `masks reflect` ritual. Belongs to you, not to any employer or project. Versioned under git on your personal remote.

`**ROLE.md`** — the behavioral delta for a specific context. Required for every Role, including `personal/`. Contains what changes when operating in that role: credentials, tools, communication norms, key relationships, constraints. Like `SELF.md`, `ROLE.md` is a working draft — bootstrapped at role setup, revised by the synthesis pass as patterns accumulate. `SELF.md` is the layer beneath all roles; `ROLE.md` is what each role adds on top of it.

`**AGENTS.md`** — system conventions, in two layers. The global copy lives at `[base]/AGENTS.md`, copied from the bundled package data by `masks setup`; placing it at the base directory ensures agent runtimes (Cursor, Claude Code) discover it automatically via workspace root traversal for any session rooted anywhere under the base. It defines how the whole system works — the Roles model, file organization, README.md format, progressive disclosure policy, hook behavior, git workflow — and is identical across all Roles, never modified per-Role. An optional Role-local `AGENTS.md` lives in the Role directory and extends the global copy with role-specific tool behavior: which MCP servers are active, which Todoist filters apply, role-specific workflow steps. The global copy is always loaded first; the local one adds on top.

### Directory layout

The default base directory is `~/Desktop`. This is configurable via `masks setup --base /path/to/base`.

```
~/Desktop/                  ← base directory (configurable)
├── AGENTS.md               ← global system conventions (copied from package by masks setup)
├── .env                    ← cross-role infrastructure credentials (gitignored)
├── personal/               ← the core. SELF.md lives here. (→ personal GitHub)
│   ├── SELF.md             ← working self-narrative (versioned; revised via masks reflect PR)
│   ├── ROLE.md             ← personal behavioral delta (required)
│   ├── AGENTS.md           ← personal-specific tool behavior (optional)
│   ├── CONTEXT.md          ← personal current focus
│   ├── OODA.md             ← autonomous loop config and heartbeat agenda (optional; only if role runs OODA) (optional; only if personal role runs OODA)
│   ├── .env                ← personal role credentials (gitignored)
│   ├── .gitignore          ← ignores .env
│   ├── Memory/             ← base memory: people, facts, decisions
│   │   ├── INDEX.md
│   │   ├── People/
│   │   ├── Projects/
│   │   └── Decisions/
│   ├── Reference/          ← foundational documents (optional)
│   │   └── INDEX.md
│   ├── Archive/            ← personal episodic memory
│   │   ├── INDEX.md
│   │   └── YYYY-MM/
│   └── [active task folders]/
│       └── README.md
└── work/                   ← a role. (→ company GitLab)
    ├── ROLE.md             ← work behavioral delta (required)
    ├── AGENTS.md           ← work-specific tool behavior (optional)
    ├── CONTEXT.md          ← work current focus
    ├── OODA.md             ← autonomous loop config and heartbeat agenda
    ├── .env                ← work role credentials (gitignored)
    ├── .gitignore          ← ignores .env
    ├── Memory/             ← work-specific memory
    │   ├── INDEX.md
    │   ├── People/
    │   ├── Projects/
    │   └── Decisions/
    ├── Reference/          ← foundational documents: strategy, plans, charters
    │   ├── INDEX.md
    │   ├── Strategy/
    │   ├── Charters/
    │   └── Org/
    ├── Archive/            ← work episodic memory
    │   ├── INDEX.md
    │   └── YYYY-MM/
    └── [active task folders]/
        └── README.md
```

`.env` files are never committed. `.env.example` is bundled inside the installed package and is the canonical template documenting every expected key with empty values. `masks setup` copies it to `[base]/.env` and to each Role directory as `.env`; `masks add-role` copies it to new Role directories. Each Role's `.gitignore` explicitly ignores `.env`.

**What lives where:**


| Location      | Contents                                                                                  |
| ------------- | ----------------------------------------------------------------------------------------- |
| `[base]/.env` | Cross-role infrastructure: mcp-memory DB path, shared API keys                            |
| `[role]/.env` | Role-specific credentials: Google account tokens, git remote auth, role-specific API keys |


### Minimum Role definition

Every Role requires exactly two things:

1. A directory under the base path
2. A `ROLE.md`

A git remote is strongly recommended but not required. Without one there is no off-machine backup and no multi-machine sync — the session-end hook will push silently, doing nothing. `masks add-role` prompts for a remote during setup; `masks doctor` warns on any Role missing one. Local-only Roles are a valid choice for ephemeral or sensitive work where remote custody is unwanted.

The `personal/` Role additionally requires `SELF.md` — the cross-role draft that is loaded by every Role but custodied here. `SELF.md` is not the personal `ROLE.md`; it sits beneath all roles. The personal role still needs its own `ROLE.md` for personal-context behavioral content: personal credentials, personal tools, how you communicate with family versus colleagues.

Everything else — `AGENTS.md`, `Memory/`, `Archive/`, skills directory — is optional. A lightweight Role (a consulting engagement, a board seat) may have only a `ROLE.md` and a few task folders. It grows structure as it needs it.

### Additional Roles

New Roles follow the same pattern as `work/`. Each gets:

- A directory at `[base]/[role-name]/`
- A `ROLE.md`
- Its own credentials in `.env`
- A git remote appropriate to the custody of that Role's data (recommended; required for backup and multi-machine sync)

A new Role does not require a separate mcp-memory database, a new AGENTS.md, or new skills unless those are specifically needed.

---

## SELF.md and ROLE.md Content

### `SELF.md` (lives in `personal/`, loaded by every Role)

```markdown
# Self

## Identity
[Name, how you think of yourself — a working description, not a fixed truth]

## Values
[What you stand for — honesty, curiosity, openness, specific principles]

## How I communicate
[Recurring style observed across contexts. What to avoid. How directness shows up.]

## How I think
[Intellectual approach, decision-making style, what energizes you]
```

Does not reference any employer, credential, tool, or role. If something would change if you changed jobs, it does not belong here — it belongs in `ROLE.md`.

`SELF.md` is a working draft, not a revealed truth. The agent's role is research: it observes patterns across roles and sessions and surfaces them as raw material for revision. Your role is editorial: you review the proposed diff, decide what earns a place in the next draft, and merge or close. The PR history — accepted proposals, rejected ones, your pre-merge edits — is itself a record of deliberate authorship over time. Agents never commit directly to `SELF.md`; revisions arrive only through the `masks reflect` PR ritual.

Size budget: ~500 tokens. When something is added, something is trimmed. The constraint keeps the document sharp.

### `ROLE.md` (every Role, including `personal/`)

Every role has a `ROLE.md` — the behavioral delta for that context on top of `SELF.md`. `SELF.md` contains what is true across all roles; `ROLE.md` contains what changes when you step into this one.

Example `personal/ROLE.md`:

```markdown
# Personal Role

**Google account:** gunnar@gmail.com
**Git remote:** github.com/gunnar (personal)
**Todoist scope:** personal projects (no prefix)

## Communication in this context
- Informal tone with family and friends
- No confidentiality constraints

## Active tools
- Personal Google Calendar and Gmail
- Personal Todoist

## Preferences in this context
- Personal work: evenings and weekends
- No meeting blocks; async by default
```

Example `work/ROLE.md`:

```markdown
# Work Role: VP & GM, Red Hat Enterprise Linux

**Google account:** gunnar@redhat.com
**Git remote:** gitlab.cee.redhat.com
**Todoist scope:** work projects (💼 prefix)

## Communication in this role
- Sign emails with single lowercase "g", no valediction
- Reports to: Ashesh Badhani (abadhani@redhat.com)
- EA: Nicole Mahoney (nmahoney@redhat.com)
- Red Hat confidentiality applies

## Active tools
- WorkBoard (OKRs and workstreams)
- Red Hat LDAP (people lookup, requires VPN)
- Work Google Calendar and Gmail

## Preferences in this role
- Work hours: 8am–4pm CST
- Deep work in mornings; rote tasks and calls in afternoons
```

---

## The Prompt Stack

The prompt stack is assembled by the session-start hook and injected at the top of every interactive session. It only works correctly when the workspace root is the Role directory — `~/Desktop/work/`, not `~/Desktop/` and not `~/Desktop/work/some-task/`. Everything in the stack is relative to that root.

For a work session:

```
1. AGENTS.md (global)          ← how this system works (always first)
2. personal/SELF.md            ← the self-narrative (cross-role, always loaded)
3. work/ROLE.md                ← how I operate in this role
4. work/AGENTS.md (optional)   ← work-specific tool behavior
5. work/CONTEXT.md             ← current work focus (injected by hook)
   + work/Archive/INDEX.md     ← work history index (injected by hook)
   + work/Memory/INDEX.md      ← memory index; full files retrieved on demand
   + work/Reference/INDEX.md   ← reference index; full docs retrieved on demand
```

For a personal session:

```
1. AGENTS.md (global)               ← how this system works
2. personal/SELF.md                 ← the self-narrative (cross-role, always loaded)
3. personal/ROLE.md                 ← personal behavioral delta
4. personal/AGENTS.md (optional)    ← personal-specific tool behavior
5. personal/CONTEXT.md              ← current personal focus (injected by hook)
   + personal/Archive/INDEX.md      ← personal history index (injected by hook)
   + personal/Memory/INDEX.md       ← memory index; full files retrieved on demand
   + personal/Reference/INDEX.md    ← reference index; full docs retrieved on demand
```

---

## Memory and the Global-Read / Write-Local Rule

Human memory doesn't partition. This system reflects that.

**Global-read:** any session can read from `personal/Memory/`. Facts that belong to the person — key relationships, patterns, values, family context — live there regardless of whether they have work relevance.

**Write-local:** sessions write only to their own Role's memory. A work session writes to `work/Memory/`. It does not write back into `personal/Memory/`. You remain in control of what enters the personal layer.

The privacy boundary: work memory (backed up to company GitLab) contains work-specific facts. Personal memory (backed up to personal GitHub) contains your full knowledge, including some work-relevant facts that belong to you regardless of employer.

### Memory tiers


| Tier          | What it is             | Location                               | Read when                |
| ------------- | ---------------------- | -------------------------------------- | ------------------------ |
| **Identity**  | Who I am               | `personal/SELF.md`                     | Always (session start)   |
| **Role**      | How I operate here     | `[role]/ROLE.md`                       | Always (session start)   |
| **Working**   | What's happening now   | `[role]/CONTEXT.md`, Todoist, calendar | Session start (injected) |
| **Reference** | Foundational documents | `[role]/Reference/`                    | On demand, via index     |
| **Semantic**  | Curated facts          | `[role]/Memory/` + `personal/Memory/`  | On demand, by topic      |
| **Episodic**  | What was done          | `[role]/Archive/`                      | On demand, via index     |


### Update policy

The three writable tiers — `Memory/`, `ROLE.md`, and `SELF.md` — have different update ceremonies that match the weight of what is being changed.


| Document  | What it contains              | Trigger                                              | Who writes      | Commit style                        | Human review                                        |
| --------- | ----------------------------- | ---------------------------------------------------- | --------------- | ----------------------------------- | --------------------------------------------------- |
| `Memory/` | Facts about the world         | New person, decision, or observation                 | Agent, directly | Bundled in session-end commit       | None required                                       |
| `ROLE.md` | Behavioral patterns in a role | Synthesis pass identifies pattern across 3+ sessions | Agent, directly | Isolated named commit with evidence | `masks status` surfaces it; review at role check-in |
| `SELF.md` | Cross-role self-narrative     | Synthesis pass identifies cross-role pattern         | Agent opens PR  | PR on personal GitHub remote        | Human merges or closes                              |


**Memory/** updates are factual and high-frequency. The agent records what it observed; no ceremony needed. If a fact is wrong, correcting it is low-stakes.

**ROLE.md** updates are pattern-based. The synthesis pass notices recurring behavior across sessions in a specific role and proposes a refinement. The agent commits directly but in an isolated, named commit — e.g. `role(work): update communication style — pattern from Q1 sessions` — so `git log work/ROLE.md` is a readable revision history of how the role narrative evolved. Size budget: ~500 tokens; every addition includes a curation pass to trim what's no longer accurate.

**SELF.md** updates are the highest-ceremony act. The agent never commits directly to `SELF.md`. Instead, it opens a pull request on your personal GitHub remote with:

- A description explaining what cross-role patterns were observed, across which sessions and roles, over what time period
- A diff showing exactly what it proposes to add and what it proposes to trim
- A rationale for each change

You review the PR as an editor, not a fact-checker — there is no external truth to verify against. The question is not "is this accurate?" but "does this earn a place in the next draft?" You merge it, edit it before merging, or close it. The PR history — accepted proposals, rejected ones, your pre-merge edits — is itself a record of deliberate authorship over time.

Size budget: ~500 tokens. When something is added, the PR must also propose what gets trimmed. The constraint is a creative one: it forces a hierarchy of what matters most.

### The `Reference/` tier

`Reference/` holds foundational documents — material that is larger, more stable, and more authoritative than individual memory files, but which shapes decisions and behavior over a long period:

- **Strategy documents:** company strategy, departmental strategy, annual operating plans
- **Charters:** team charters, Pod charters, program constitutions
- **Org context:** org structure, key relationship maps, RACI documents
- **Persona documents:** leadership principles, communication guides, handbook entries

`Reference/` is distinct from `Memory/` in three ways:

1. Documents are **maintained in place** — updated when superseded, not archived
2. Documents can be **large** — an operational plan may be many pages; summary headers make them navigable
3. The source of truth is often **Google Drive** — a refresh skill pulls and converts them; the local copy is the working copy for agent use

**Summary header standard:** every document in `Reference/` opens with a summary block (~500 words) capturing key points, decisions, and current status. The agent reads this to decide whether the full document is needed. The summary header is the Level 2 entry point for reference material.

**How reference documents are introduced:**

- Large documents from Google Drive: the `reference-refresh` skill pulls, converts to markdown, generates a summary header, writes to `Reference/`, and updates `Reference/INDEX.md`
- Documents written directly: agent or human writes them into `Reference/` with a summary header; onboarding seeds the initial set

### Bounded always-loaded memory

The always-loaded tiers (`SELF.md` + `ROLE.md` + `CONTEXT.md`) should have an explicit size budget. Target: ~1,500 tokens combined. Above that, progressive disclosure handles retrieval.

If `SELF.md` or `ROLE.md` grows beyond ~500 tokens, it needs curation, not expansion.

---

## OODA

Each Role with autonomous operation gets an `OODA.md`. It is the complete specification for that Role's background loop: what signals to watch, what agents to run, and when to run them. The agents stay generic; the Role supplies the configuration.

The loop runs on a single cadence — every 15 minutes during active hours. There is no separate "scheduled jobs" concept. Skills that should only run at a specific time (e.g. `daily-briefer` at 06:45) self-guard on the clock: the pre-flight runner checks the condition before invoking any LLM.

### The pre-flight guard layer

Every heartbeat cycle runs a lightweight shell pre-flight before starting any LLM session. Guards are CLI invocations — fast, deterministic, zero LLM cost. If all guards fail (nothing to do), the runner logs `OODA_OK` and exits. No LLM is started.

Guard conditions are defined per skill in the framework, not in `OODA.md`. Examples:

- `ooda-observe`: are there any unread items across signal sources? (cheap API count calls)
- `email-classifier`: is work Gmail unread count > 0?
- `daily-briefer`: is current time within 15 min of 06:45 and not already run today?
- `ooda-act`: are there any Todoist items labeled `agent` or `decision`?

Guard logic never appears in `OODA.md`. A reader of `OODA.md` sees only what runs and in what order.

### Write routing

Observation destination follows the tool that produced the signal:

- **Work-scoped tools** (work Gmail, work Calendar, WorkBoard, work Todoist projects) → write to `work/Memory/`
- **Personal-scoped tools** (personal Gmail, personal Calendar, personal Todoist projects) → write to `personal/Memory/`
- **Cross-cutting synthesis** (patterns spanning both contexts) → write to `personal/Memory/`

### The synthesis pass

`ooda-orient-synthesis` is the one agent that reads across all Roles' `Memory/` files and writes cross-cutting patterns to `personal/Memory/`. It runs once weekly from `personal/` as its workspace root, self-guarding on the day of week. It is the deliberate exercise of the global-read rule. Because it requires access to all Roles' memory and writes back to `personal/Memory/`, it lives in `personal/OODA.md` — not in any work or other Role's OODA.

### `OODA.md` standard

```markdown
# OODA — [role-name]

**Active hours:** HH:MM–HH:MM TZ, weekdays

---

## Signal Sources

- Calendar: `gws --account [account]`
- Gmail: `gws --account [account]`
- Todoist: projects labeled `#[role]`
- [additional sources]

**Observations write to:** Memory/ (tag: `[role]`)
**Cross-cutting synthesis writes to:** personal/Memory/

---

## Agenda

Runs every 15 minutes during active hours.
Pre-flight guards run before any LLM is invoked — if all fail, logs OODA_OK and exits.

### Observe
1. `ooda-observe`

### Orient
2. [orient skills in order — synthesis and classification only]

### Act
3. `ooda-act`
4. [scheduled housekeeping tasks: reference-refresh, meeting-summary, etc.]

Convention: Orient is for synthesizing observations into understanding or decisions. Scheduled maintenance tasks that fetch, refresh, or output content — even if they run on a time guard — belong in Act.

---

## Excluded

- [signal sources this Role's loop must not touch]
```

### Example: `work/OODA.md`

```markdown
# OODA — work

**Active hours:** 07:00–19:00 ET, weekdays

---

## Signal Sources

- Calendar: `gws --account work`
- Gmail: `gws --account work`
- Todoist: projects labeled `#work`
- WorkBoard: primary account
- Feedly: RHEL-BU folder

**Observations write to:** Memory/ (tag: `work`)
**Cross-cutting synthesis writes to:** personal/Memory/

---

## Agenda

Runs every 15 minutes during active hours.
Pre-flight guards run before any LLM is invoked — if all fail, logs OODA_OK and exits.

### Observe
1. `ooda-observe`

### Orient
2. `email-classifier`
3. `email-todo-forwarder`
4. `ooda-orient-meeting-prep`
5. `ooda-orient-decisions`

### Act
6. `ooda-act`
7. `daily-briefer`
8. `meeting-summary`
9. `reference-refresh`

---

## Excluded

- Personal Gmail, Calendar, Todoist projects
- Any credential not in .env
```

---

## The mcp-memory Database

The SQLite-vec mcp-memory database is an **ephemeral search index** built from the files in `Memory/` directories. The files are canonical; the database is regenerable.

**One database indexes all Roles** — simple to configure, no sharding. The files carry the custody separation (different git remotes); the database is just a search accelerator.

**The database does not need git backup.** If lost, it is rebuilt by re-ingesting all `Memory/` files across all Roles via `masks index <role> --rebuild` for each Role.

Role and scope are captured in the tags of each memory entry. The mcp-memory database is scoped by querying with role-specific tags.

### When to use the database vs. the files

**Direct file reads** handle the common case: scan `Memory/INDEX.md`, identify the relevant file from the one-line summary, read it. This works whenever you know — or can infer from the index — what you are looking for. It is always current, requires no database, and involves no embedding overhead.

**Database search** earns its keep in two scenarios the file approach handles poorly:

1. **Fuzzy / semantic queries.** "What do I know about containerization strategy?" or "Have I worked with anyone at $company?" — the index cannot answer these. The database matches by meaning across potentially hundreds of files.
2. **OODA orient passes.** Orient agents need context for a decision or meeting prep without knowing which memory files are relevant. The database is a fast first-pass filter before the agent decides what to actually read.

The division: **direct reads when you have a pointer; database search when you don't.**

### Tag schema

Every memory entry carries two mandatory tags:


| Tag         | Format                       | Purpose                                             |
| ----------- | ---------------------------- | --------------------------------------------------- |
| Role scope  | `role:work`, `role:personal` | Filters search to one Role's memory                 |
| Source file | `file:people/frank-zdarsky`  | Enables precise eviction on file change or deletion |


Optional tags (added by the agent when writing the memory file) narrow further: `type:person`, `type:decision`, `topic:pricing`, etc.

### Indexing: hook-based, incremental

The database is maintained by a **post-commit git hook** in each Role directory, installed by `masks setup`. It fires after the session-end commit and calls `masks index <role>`. The hook exits immediately if no `Memory/` files changed — most commits involve no memory writes.

`masks index` uses the `mcp_memory_service` Python library directly (the same library that backs the running MCP server). No subprocess, no dependency on the MCP server process being alive.

```bash
#!/bin/bash
# ~/.pirandello/hooks/post-commit.sh (also wired as .git/hooks/post-commit in each Role)

REPO="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
CHANGED=$(git diff --name-only HEAD~1 HEAD -- Memory/)
DELETED=$(git diff --name-status HEAD~1 HEAD -- Memory/ | awk '/^D/{print $2}')

[[ -z "$CHANGED" && -z "$DELETED" ]] && exit 0

BASE=$(dirname "$REPO")
ROLE=$(basename "$REPO")
[[ -f "$BASE/.env" ]] && source "$BASE/.env"

masks index "$ROLE"
```

`masks index` logic:

1. Diffs `HEAD~1..HEAD` in the Role's `Memory/` directory to get added, modified, and deleted files
2. For **modified and deleted** files: calls `storage.delete_by_tag("file:<path>")` to evict stale entries — required before re-ingesting modifications because content hash deduplication only blocks exact duplicates, not updated content
3. For **added and modified** files: reads the file, creates a `Memory` object with `role:<role>` and `file:<path>` tags, calls `storage.store()` directly — no chunker, no document pipeline; `Memory/` files are short by design, one file = one memory entry
4. Closes the storage connection

**Full rebuild:** `masks index <role> --rebuild` clears all `role:<role>` entries and re-ingests all `Memory/` files from scratch. Used after a lost database or a Role migration.

### Library dependency

`masks` adds `mcp-memory-service` as a Python dependency. The relevant surface:

```python
from mcp_memory_service.storage.sqlite_vec import SqliteVecMemoryStorage
from mcp_memory_service.models.memory import Memory
from mcp_memory_service.utils.hashing import generate_content_hash

storage = SqliteVecMemoryStorage(db_path=db_path)
await storage.initialize()
await storage.store(memory)           # upsert with hash dedup
await storage.delete_by_tag(tag)      # evict by file path or role
await storage.retrieve(query, tags=[f"role:{role}"])  # semantic search scoped to Role
await storage.close()
```

The database path is read from `MCP_MEMORY_DB_PATH` in `[base]/.env`.

---

## Two Repos

### `pirandello` (public / shareable)

Contains the system — conventions, skills, templates, and the `masks` CLI. No personal content.

```
~/Code/pirandello/
├── .env.example            ← canonical credential template (committed; no secrets)
├── .gitignore              ← ignores .env
├── hooks/                  ← hook scripts (source of truth; mirrored into cli/masks/_data/)
│   ├── start.sh
│   ├── end.sh
│   └── post-commit.sh
├── guards/                 ← pre-flight guard scripts (mirrored into cli/masks/_data/)
├── templates/
│   ├── AGENTS.md           ← global conventions template (mirrored into cli/masks/_data/)
│   ├── OODA.md             ← starter OODA.md; onboarding fills in the blanks
│   └── .gitignore          ← gitignore template copied to each Role on setup
├── skills/                 ← shared skills (global to all Roles)
├── cli/                    ← the `masks` CLI (Python, managed by uv)
│   ├── pyproject.toml
│   └── masks/
│       ├── __init__.py
│       ├── _data/          ← bundled framework assets (hooks, guards, templates, AGENTS.md)
│       ├── setup_cmd.py    ← `masks setup`
│       ├── role_cmd.py     ← `masks add-role`
│       ├── run_cmd.py      ← `masks run` (heartbeat runner with pre-flight guards)
│       ├── reflect_cmd.py  ← `masks reflect`
│       ├── reference_refresh_cmd.py ← `masks reference-refresh`
│       ├── status_cmd.py   ← `masks status`
│       ├── sync_cmd.py     ← `masks sync`
│       ├── index_cmd.py    ← `masks index`
│       └── doctor_cmd.py   ← `masks doctor`
└── README.md               ← how to adopt this system
```

### Role directories (private, per-Role remotes)

Each Role is its own git repo. `masks setup` copies `AGENTS.md` from the bundled package data (`masks/_data/AGENTS.md`) to `[base]/AGENTS.md` and to each Role directory — no symlinks. Personal content never enters the framework repo.

---

## The `masks` CLI

The `masks` command is the system maintenance tool. It replaces the ad-hoc `install.sh`. Managed by `uv` — no installation required beyond cloning `pirandello`.

```bash
uvx masks <command>
# or, after `uv tool install`:
masks <command>
```

### Commands

`**masks setup [--base PATH]**`
First-time setup. Deploys hook scripts to `~/.pirandello/hooks/` and guard scripts to `~/.pirandello/guards/` from the bundled package data. Creates the base directory structure, seeds index files, copies `AGENTS.md` from bundled package data to `[base]/AGENTS.md` and each Role directory, copies `.env.example` to `[base]/.env` and to each Role directory as `.env`, copies `.gitignore` template to each Role directory, copies `OODA.md` template into roles, initializes git repos. When re-run, overwrites `AGENTS.md` and hook scripts in-place (creating timestamped `.bak` backups of any prior versions); leaves `.env`, `.gitignore`, and `OODA.md` untouched. Default base: `~/Desktop`.

`**masks add-role <name> [--remote URL]**`
Adds a new Role directory under the base path with the standard reserved structure (`Memory/`, `Reference/`, `Archive/`, `OODA.md`). Copies `.env.example` to `[role]/.env` and `.gitignore` template to `[role]/.gitignore`. Optionally wires a git remote. When run interactively, delegates to the `add-role` skill for the conversational part — asks for each credential by name, explains what it is and where to find it, and writes the values into `[role]/.env` directly so the user never has to edit the file manually. Prompts for signal sources at the same time. Also invokable as a standalone skill from inside a session.

`**masks run <role>**`
The heartbeat runner. Sources `$BASE/.env` and `[role]/.env`, executes pre-flight guards for every skill in `[role]/OODA.md`, and invokes an LLM session with `OODA.md` as the only injected context if any guard passes. If all guards fail, logs `OODA_OK` and exits — no LLM is started. Designed to be called from cron every 15 minutes. See the Hooks section for crontab entries and the full OODA invocation sequence.

`**masks sync [role]**`
Pulls then pushes all Role repos (or one specified Role). Equivalent to the session-end hook but callable on demand. Safe to run from cron nightly.

`**masks status**`
Prints a summary of all Roles: last heartbeat, last `OODA_OK`, last git sync, any guard failures.

`**masks reflect [role]**`
Entry point for the synthesis and reflection ritual. Delegates LLM work to the `reflect` skill, which reads `Memory/` files across all Roles (or a specified Role), identifies cross-role patterns accumulated since the last reflection, drafts a `SELF.md` diff, and writes the PR description. `masks reflect` then opens the pull request on the personal GitHub remote. If no meaningful patterns are found, logs `REFLECT_OK` and exits without opening a PR. Designed to be run on demand or on a scheduled cadence (e.g. monthly). The act of merging or closing the PR is the reflection ritual. Also invokable as a standalone skill from inside a session.

`**masks reference-refresh [--role ROLE] [--non-interactive] [--dry-run]**`
Runs the `mask-reference-refresh` skill for one Role. If `--role` is omitted, the command infers the Role from the current workspace path under `$BASE`; if inference fails, it exits with an explicit error requiring `--role`. `--non-interactive` sets `PIRANDELLO_NONINTERACTIVE=1` for unattended runs (for example, OODA or cron-driven invocations). `--dry-run` plans and reports refresh actions without writing files.

`**masks index <role> [--rebuild]**`
Updates the mcp-memory database for a Role. Without `--rebuild`, diffs `HEAD~1..HEAD` in the Role's `Memory/` directory — evicts stale entries for modified and deleted files, ingests added and modified files. With `--rebuild`, clears all `role:<role>` entries and re-ingests everything from scratch. Called automatically by the post-commit hook; also callable on demand after a lost database or a Role migration. Reads `MCP_MEMORY_DB_PATH` from `[base]/.env`.

`**masks doctor**`
Checks system health: git remotes reachable, MCP servers responding, credential files present, OODA.md valid against schema, guard scripts executable.

### CLI commands and skills

`masks` commands split into two kinds based on whether they need an LLM.

**Infrastructure commands** do their work entirely in shell or Python — no LLM involved, no skill equivalent needed. Running them from inside a session means shelling out directly.


| Command        | Work done                         |
| -------------- | --------------------------------- |
| `masks setup`  | File creation, hook deployment, git init |
| `masks sync`   | `git pull` + `git push`           |
| `masks index`  | Database upsert/evict             |
| `masks status` | Data aggregation from logs        |
| `masks doctor` | Shell health checks               |


**LLM-powered commands** delegate their reasoning work to a skill. The CLI handles the entry point and infrastructure side-effects (commits, PRs, file writes); the skill handles reading, pattern recognition, and language.


| Command                          | Skill        | What the skill does                                                                                                     |
| -------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------- |
| `masks reflect`                  | `reflect`    | Reads Memory/ files across roles and sessions, identifies cross-role patterns, drafts `SELF.md` diff and PR description |
| `masks reference-refresh`        | `mask-reference-refresh` | Reads `Reference/INDEX.md`, refreshes Drive-backed reference docs, updates `Refreshed` dates post-write; supports dry-run |
| `masks add-role` (interactive)   | `add-role`   | Guides credential collection conversationally, explains each key, writes `.env`                                         |
| `masks setup` (onboarding phase) | `onboarding` | Conversational SELF.md + ROLE.md + OODA.md construction                                                                 |


The skills are also directly invokable from inside a session — a user can ask the agent to "reflect on this session" or "add a new role" without knowing the CLI command exists. The CLI and the skill are two entry points to the same work.

---

## Distribution

The current installation path — clone `pirandello`, run `masks setup`, go through onboarding — is fine for a technical adopter but too high a bar for sharing with colleagues. The goal is installation from within tools the user already has, without ever opening a terminal.

### Cursor extension

A Cursor extension is the primary distribution target. When installed from the Cursor extension marketplace, it:

1. Clones `pirandello` to `~/Code/pirandello/` if not already present
2. Installs `masks` via `uv tool install`
3. Runs `masks setup` to create the base directory structure, copy `AGENTS.md` from bundled package data, deploy hook scripts, and seed credential templates
4. Launches the onboarding skill conversationally inside Cursor — the user never sees the file system

The extension also registers the session-start and session-end hooks for any workspace rooted in a Role directory. A user who opens `~/Desktop/work/` in Cursor gets the full hook lifecycle without manual configuration.

Post-install, the extension is passive. It does not require a running background process. Everything it sets up is just files, hooks, and the `masks` CLI — all of which work without the extension present.

### Claude plugin

A Claude.ai plugin (or Claude Code MCP extension) provides an equivalent path for users whose primary tool is Claude rather than Cursor. It:

1. Installs `pirandello` and `masks` the same way
2. Launches onboarding as a Claude project skill
3. Registers the MCP server configuration for mcp-memory

The Claude plugin is a secondary target — same outcome, different entry point.

### Design constraints

- **The plugin is not required.** `masks setup` remains the manual installation path and must always work independently. Users who prefer terminal setup should not be blocked.
- **The plugin does not own the data.** Everything it installs is standard files and git repos. Uninstalling the plugin changes nothing about the user's Roles or memory.
- **One-time setup only.** Re-running the extension on a machine that already has `pirandello` installed is a no-op (idempotent, same as `masks setup`).

---

## Onboarding

`masks setup` is for machines. Onboarding is for people.

Onboarding is a guided conversational experience. The agent asks; the human answers; files are written as a side effect. The new user never needs to understand the directory structure.

**The philosophy of the sequence matters: you exist first, Roles come after.**

### Phase 1 — Identity (once, ever)

*"Let's build a starting model of your voice."*

Collects name, values, communication style, how you think. Writes `personal/SELF.md` as a v0.1 — an initial construction, not a final answer. The onboarding doesn't have to get it right; it has to get you started. This file belongs to you permanently and predates any role. It will be refined over time through the `masks reflect` ritual as the agent observes patterns across sessions.

### Phase 2 — Role setup (once per Role)

*"What roles do you play?"*

For each Role:

1. Name it, create the directory
2. *"What's the git remote?"* → configures remote, first push
3. *"What credentials does this Role use?"* → populates the Role's `.env` (already created from `.env.example` by `masks setup`)
4. *"What tools are active?"* → configures MCP servers
5. *"What are you focused on right now?"* → seeds `CONTEXT.md`
6. *"Who are the key people?"* → seeds `Memory/People/`

### Phase 3 — Verification

Confirms MCP connections are live. Pushes all first commits.

### Re-onboarding

Run again to adopt the framework fresh, or to refresh when a Role changes significantly.

### Inspired by

OpenClaw's `openclaw onboard` and Hermes Agent's profile creation: onboarding should feel like meeting someone, not configuring software.

---

## Progressive Disclosure

Never load everything. Reveal detail only as it becomes relevant.

**Level 1 — Index (scan):** `Archive/INDEX.md`, `Memory/INDEX.md`, and `Reference/INDEX.md`. One line per entry. ~2–5k tokens to survey the full history of a Role. `Reference/INDEX.md` lists stable documents with one-line descriptions.

**Level 2 — Summary (decide):** The `README.md` in a specific folder, the relevant memory file, or the summary header at the top of a reference document. ~200–500 tokens. Read only when the index suggests relevance.

**Level 3 — Full content (use):** The actual documents. Read only when the summary confirms they are needed.

An agent touches Level 3 for at most 2–3 items per session. For reference documents this means reading past the summary header into the full document body — uncommon and intentional.

---

## README.md Standard

Every task folder in any Role:

```markdown
# [task-name]
**Date:** YYYY-MM-DD
**Role:** personal | work | [role-name]
**Status:** active | complete | superseded by [folder-name] | stale
**Tags:** [space-separated topic tags]

## Summary
One paragraph: what was done and why.

## Key Outputs
- filename.md — description

## Key Decisions
- Decision 1
```

---

## Indexes

### `[role]/Archive/INDEX.md`

One row per archived task. Updated by the archive skill.

```
| Date       | Folder                     | Summary                                       | Tags                    | Status   |
|------------|----------------------------|-----------------------------------------------|-------------------------|----------|
| 2026-03-15 | vcpu-hour-prfaq            | PRFAQ proposing vCPU/hour universal pricing   | pricing, vcpu, strategy | complete |
| 2026-04-02 | frontier-model-threat-sbar | SBAR on AI frontier model threat to RHEL      | ai, sbar, strategy      | complete |
```

### `[role]/Memory/INDEX.md`

One row per memory file. Updated when files are added or modified.

```
| File                        | Summary                                     | Tags                    |
|-----------------------------|---------------------------------------------|-------------------------|
| people/frank-zdarsky.md     | Frank Zdarsky, OCTO, mentoring relationship | person, octo, mentoring |
| projects/summit-2026.md     | Red Hat Summit 2026 planning context        | summit, event, q2       |
| decisions/vcpu-pricing.md   | Decision to pursue vCPU/hour model in CY27  | pricing, decision       |
```

### `[role]/Reference/INDEX.md`

One row per reference document. Updated by the `reference-refresh` skill when documents are added or refreshed. The Source column shows the canonical location; the Local column shows the working copy path.

```
| File                              | Summary                                         | Source                          | Refreshed  |
|-----------------------------------|-------------------------------------------------|---------------------------------|------------|
| strategy/rhel-strategy-2026.md    | RHEL BU 3-year strategy; key bets and OKR frame | Google Drive: [doc ID]          | 2026-04-20 |
| charters/pods/platform-charter.md | Platform Pod charter; mission, members, cadence  | Google Drive: [doc ID]          | 2026-03-15 |
| org/extended-staff.md             | Extended staff roles and responsibilities        | Written directly                | 2026-04-01 |
```

The `reference-refresh` skill:

1. Reads the Drive document URL from `Reference/INDEX.md`
2. Exports it to Markdown
3. Generates or updates the summary header (~500 words) at the top of the file
4. Writes the file to `Reference/`
5. Updates the `Refreshed` timestamp in `Reference/INDEX.md`

Run manually when documents change, or on a weekly schedule via the OODA loop.

---

## Git Strategy

Each Role is its own git repo. Custody follows the Role:


| Role             | Remote               | Rationale                                                  |
| ---------------- | -------------------- | ---------------------------------------------------------- |
| `personal/`      | Personal GitHub      | Your identity and knowledge. Yours regardless of employer. |
| `work/`          | Company GitLab       | Work outputs and decisions. Legitimately company record.   |
| Additional Roles | Appropriate per Role | Board → board org; consulting → personal or client repo    |


`SELF.md` is updated only through the `masks reflect` PR ritual — never via direct agent commit. The PR is the ceremony; merging is the authorial act.

Multi-instance: each machine clones all Roles. Session-start hook pulls. Session-end hook pushes. `CONTEXT.md` is last-write-wins.

---

## Hooks

Hooks wire Pirandello's lifecycle into the agent runtime. `masks setup` installs them for the target runtime. Hook scripts are bundled inside the installed package at `masks/_data/hooks/` and deployed to `~/.pirandello/hooks/` on first setup — a stable, user-owned location that role configuration files reference. Guard scripts are deployed to `~/.pirandello/guards/`. They are not role-specific — the role is derived from `$PWD` at runtime.

### Runtime wiring


| Runtime                   | Hook mechanism                                                         | Installed by  |
| ------------------------- | ---------------------------------------------------------------------- | ------------- |
| Cursor (interactive)      | `.cursor/hooks.json` in the role directory                             | `masks setup` |
| Claude Code (interactive) | `CLAUDE.md` lifecycle sections in the role directory                   | `masks setup` |
| OODA (headless)           | `masks run` manages its own invocation; does not use interactive hooks | cron          |


Each role directory is intended to be opened as a separate workspace. Hooks in `.cursor/hooks.json` are workspace-scoped and always know which role they're serving.

The interactive start and OODA start are **distinct code paths** with different context injection strategies. Do not conflate them.

---

### Session start — interactive

Runs when an interactive session opens in a role directory. Derives `$BASE` and `$ROLE` from `$PWD` — no parameters needed.

```bash
#!/bin/bash
# ~/.pirandello/hooks/start.sh  (deployed from masks/_data/hooks/start.sh by masks setup)

BASE=$(dirname "$PWD")   # e.g. ~/Desktop
ROLE=$(basename "$PWD")  # e.g. work

# Bail early if this doesn't look like a Role workspace
if [[ ! -f "$PWD/ROLE.md" || ! -f "$BASE/personal/SELF.md" || ! -f "$BASE/AGENTS.md" ]]; then
  echo "Pirandello: workspace does not look like a Role directory. Open the Role directory as the workspace root." >&2
  exit 0
fi

# Source credentials — cross-role infrastructure first, then role-specific
[[ -f "$BASE/.env" ]] && source "$BASE/.env"
[[ -f .env ]] && source .env

# Pull this role's repo and personal/ (for latest SELF.md)
git pull --ff-only 2>/dev/null || true
git -C "$BASE/personal" pull --ff-only 2>/dev/null || true

# Inject context stack
# AGENTS.md at $BASE/AGENTS.md may be auto-discovered by Cursor via parent-directory
# traversal. Injected here for parity with Claude Code and headless sessions.
echo "=== GLOBAL AGENTS ===" && cat "$BASE/AGENTS.md"
echo "=== SELF ===" && cat "$BASE/personal/SELF.md"
echo "=== ROLE ===" && cat ROLE.md
[[ -f AGENTS.md ]] && echo "=== ROLE AGENTS ===" && cat AGENTS.md
[[ -f CONTEXT.md ]] && echo "=== CONTEXT ===" && cat CONTEXT.md

# Level 1 indexes — surveyed at session start; full content retrieved on demand
[[ -f Archive/INDEX.md   ]] && echo "=== ARCHIVE INDEX ===" && cat Archive/INDEX.md
[[ -f Memory/INDEX.md    ]] && echo "=== MEMORY INDEX ===" && cat Memory/INDEX.md
[[ -f Reference/INDEX.md ]] && echo "=== REFERENCE INDEX ===" && cat Reference/INDEX.md
```

---

### Session end — interactive

Runs when an interactive session closes. Same `$PWD`-based role derivation.

```bash
#!/bin/bash
# ~/.pirandello/hooks/end.sh  (deployed from masks/_data/hooks/end.sh by masks setup)

cd "$PWD" 2>/dev/null || exit 0
git add -A 2>/dev/null || true
if ! git diff --cached --quiet 2>/dev/null; then
  git commit -m "session: $(date '+%Y-%m-%d %H:%M')" 2>/dev/null || true
fi
git push 2>/dev/null || true
```

---

### Post-commit — database index

Runs after the session-end commit. Exits immediately if no `Memory/` files changed — the common case. When `Memory/` was touched, calls `masks index <role>` to update the mcp-memory database incrementally.

```bash
#!/bin/bash
# ~/.pirandello/hooks/post-commit.sh  (deployed from masks/_data/hooks/post-commit.sh by masks setup)
# Also wired as .git/hooks/post-commit in each Role by masks setup.

REPO="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$REPO" || exit 0
if ! git rev-parse HEAD~1 >/dev/null 2>&1; then exit 0; fi   # initial commit: no diff

CHANGED="$(git diff --name-only HEAD~1 HEAD -- Memory/ 2>/dev/null)"
DELETED="$(git diff --name-status HEAD~1 HEAD -- Memory/ 2>/dev/null | awk '/^D/{print $2}')"

[[ -z "$CHANGED" && -z "$DELETED" ]] && exit 0

BASE="$(cd "$(dirname "$REPO")" && pwd 2>/dev/null)"
[[ -f "$BASE/.env" ]] && source "$BASE/.env"

masks index "$(basename "$REPO")" 2>/dev/null || true
```

---

### OODA invocation — `masks run`

The OODA start path is entirely distinct from the interactive hooks. `masks run <role>` is called by cron every 15 minutes during active hours. It:

1. Sources `$BASE/.env` and `$ROLE/.env`
2. Runs the pre-flight guard for every skill listed in `OODA.md`
3. If all guards fail: logs `OODA_OK` and exits — no LLM invoked
4. If any guard passes: invokes an LLM session with `**OODA.md` as the only injected context**

`OODA.md` is the sole context for OODA sessions. It lists what to run and in what order; skills load Memory/, Reference/, and Archive/ content via progressive disclosure as needed. The full interactive context stack is not injected.

```
# crontab entry — $BASE is the configured base directory (e.g. ~/Desktop)
*/15 * * * 1-5 masks run work     2>> $BASE/work/.ooda.log
*/15 * * * 1-5 masks run personal 2>> $BASE/personal/.ooda.log
```

---

### Archive (inside archive skill)

1. Read the folder's `README.md` — or generate one from contents if missing
2. Append a row to `Archive/INDEX.md`
3. Move folder to `Archive/YYYY-MM/`
4. Session-end hook handles the commit and push

---

## Reliability Stack


| What must happen                       | Mechanism             | Reliability                               |
| -------------------------------------- | --------------------- | ----------------------------------------- |
| Pull role repo on session start        | Start hook (shell)    | Very high                                 |
| Pull personal/ on session start        | Start hook (shell)    | Very high                                 |
| Source .env credentials                | Start hook (shell)    | Very high                                 |
| Inject SELF + ROLE + context + indexes | Start hook (shell)    | Very high                                 |
| Write README.md during task            | AGENTS.md instruction | ~85%                                      |
| Update Memory/INDEX.md on memory write | AGENTS.md instruction | ~85%                                      |
| Commit on session end                  | End hook (shell)      | Very high                                 |
| Push to remote on session end          | End hook (shell)      | Very high (no-op if no remote configured) |
| README.md on archive                   | Inside archive skill  | High                                      |
| Update Archive/INDEX.md                | Inside archive skill  | High                                      |
| OODA pre-flight guard (no-op exit)     | `masks run` shell     | Very high                                 |
| OODA context injection (OODA.md only)  | `masks run` shell     | Very high                                 |
| mcp-memory index updated after write   | Post-commit git hook  | Very high                                 |


---

## Roadmap

This roadmap covers system construction only. Migration of existing content (SELF.md bootstrapped from master prompt, task folders, archive, mcp-memory entries, OODA reconfiguration) is tracked separately in `transition.md` and executed once the system is built.

### Phase 1 — Framework foundation

- Initialize `pirandello` repo at `~/Code/pirandello/`
- Write global `AGENTS.md` and bundle it in `cli/masks/_data/`; `masks setup` copies it to `[base]/AGENTS.md` and each Role directory
- Write `CLAUDE.md` for OODA / Claude Code runtime
- Write `config/shared.md` with naming conventions and format standards
- Write `templates/OODA.md` starter template
- Set up session-start and session-end hooks (Role-aware)

### Phase 2 — `masks` CLI

- Build `masks setup` — deploys hook and guard scripts from bundled package data to `~/.pirandello/`; creates Role directory structure, seeds index files, copies `AGENTS.md`, copies `.env.example` and `.gitignore` template, copies OODA template, initializes git repos
- Build `masks add-role` — adds a Role with standard reserved structure
- Build `masks run` — pre-flight guard runner; owns OODA heartbeat invocation
- Build `masks sync` — git pull + push for all Roles
- Build `masks status` — last heartbeat, OODA_OK, git sync per Role
- Build `masks doctor` — checks git remotes, MCPs, credentials, OODA.md schema, guard executability

### Phase 3 — Skills

- Build or update `archive` skill to write `README.md` and append to `Archive/INDEX.md`
- Build `reference-refresh` skill (Drive export → summary header → `Reference/INDEX.md`)
- Build `onboarding` skill (conversational SELF.md + ROLE.md + OODA.md setup; frames Phase 1 as "drafting a v0.1", not revealing a truth); invoked by `masks setup` and directly
- Build `reflect` skill (reads Memory/ across Roles, identifies cross-role patterns, drafts SELF.md diff and PR description); invoked by `masks reflect` and directly
- Build `add-role` skill (conversational credential collection and signal source setup); invoked by `masks add-role --interactive` and directly
- Write pre-flight guards for all heartbeat agenda skills

### Phase 4 — OODA

- Wire `masks run <role>` into cron at 15-minute interval
- Implement `ooda-orient-synthesis` (weekly cross-Role synthesis pass; feeds `masks reflect`)
- Build `masks reflect` — synthesis pass + PR opener on personal GitHub remote
- Build `masks index` — incremental mcp-memory updater; called by post-commit hook and on demand with `--rebuild`

### Phase 5 — Share

- Write `pirandello/README.md` as a public onboarding guide
- Extract starter `SELF.md` and `ROLE.md` templates (no personal content)
- Publish `pirandello` repo
- Pilot with one colleague: `masks setup` → onboard → first session

### Phase 6 — Distribution

- Build Cursor extension: clones `pirandello`, installs `masks`, runs `masks setup`, launches onboarding skill, registers hooks for Role workspaces
- Build Claude plugin (secondary): equivalent install path for Claude.ai / Claude Code users
- Submit to Cursor extension marketplace
- Validate end-to-end: fresh machine → install extension → complete onboarding → first live session

---

## Open Questions

- **Role-specific skills:** How Role-specific skills are loaded depends on the agent runtime (Cursor vs Claude Code vs Hermes). Left open until a specific runtime makes it concrete.
- **mcp-memory rebuild:** Resolved. Hook-based, incremental. Post-commit git hook calls `masks index <role>`, which diffs `HEAD~1..HEAD` in `Memory/`, evicts stale entries via `delete_by_tag`, and upserts changed files directly via the `mcp_memory_service` Python library. Full rebuild available via `masks index <role> --rebuild`. See "The mcp-memory Database" section.
- `**OODA_OK` suppression:** `masks run` logs `OODA_OK` to `.ooda.log` and exits silently. Suppression is handled by the runner, not the LLM runtime. No further design needed unless a notification channel is added.

## See Also

- `transition.md` — migration plan for moving existing content (master prompts, Desktop task folders, archive, mcp-memory entries, my-profile skill) into the new system. Not a spec concern; executed once the system is built.

