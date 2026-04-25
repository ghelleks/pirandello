# System Plan: Pirandello End-to-End Integration

**Status:** evaluated (system SDD pass, metrics S-01–S-10 + UC1–UC10, T1–T8)  
**Date:** 2026-04-24  
**Authoritative design:** `docs/design.md`  
**Spec:** `docs/SPEC.md` · **Scenarios:** `docs/SCENARIOS.md`

This document is the **single system-level build plan**: how all thirteen units integrate, how hard constraints are **enforced** (not merely described), and how cross-Role custody and data flows behave in production.

---

## 1. Architecture snapshot

Pirandello splits into:

- **`pirandello/`** — public framework (AGENTS.md, hooks, `masks` CLI, skills, extension). **No personal content** ever lands here (S-01). Scheduled OODA (guards, `beckett run`) ships in the **`beckett`** package.
- **`[base]/`** — user-owned Desktop (or configured) tree: symlinked global `AGENTS.md`, per-Role git repos (`personal/`, `work/`, …), shared `.env` for infra keys.

**Session root invariant:** Interactive work assumes the **Role directory** is the workspace root. Wrong root → hooks emit a stderr banner and skip destructive git work; agents must not treat subfolders as repo roots (S-05 session-hooks validation).

**Two interactive runtimes:** Cursor / Claude Code use **shell hooks**. **OODA** uses **`beckett run <role-dir-or-name>`** (no session hooks); context is **`OODA.md` only** for that subprocess.

---

## 2. Thirteen-unit integration map

| # | Unit | Delivers | Upstream consumers |
|---|------|----------|-------------------|
| 1 | **session-hooks** | `start.sh`, `end.sh`, `post-commit.sh` | Cursor extension installs wiring; `masks setup` installs git post-commit |
| 2 | **masks-cli-core** | `setup`, `add-role`, `sync`, `status`, `doctor` | Every other unit assumes base resolution, hook install, symlinks |
| 3 | **`beckett`** | Heartbeat runner, guard loop, LLM spawn | Cron; `OODA.md` agendas |
| 4 | **masks-index** | `masks index <role> [--rebuild]` | post-commit hook; manual repair |
| 5 | **masks-reflect** | `masks reflect` — git/PR only in `personal/` | reflect skill JSON |
| 6 | **ooda-orient-synthesis** | Weekly synthesis → `personal/Memory/Synthesis/` | reflect skill; never `work/OODA.md` |
| 7 | **onboarding-skill** | SELF/ROLE/OODA bootstrap | Extension launch; `masks setup` phase |
| 8 | **reflect-skill** | Pattern detection, diff + PR text | `masks reflect` subprocess |
| 9 | **add-role-skill** | Credential conversation | `masks add-role --interactive` |
| 10 | **archive-skill** | Archive folders + `Archive/INDEX.md` | Session-end commit bundles |
| 11 | **reference-refresh-skill** | Drive → `Reference/` + INDEX | OODA Act; manual |
| 12 | **cursor-extension** | Clone, `uv`, `masks setup`, hook registration | First-day install path |
| 13 | **project-blog** | `LICENSE` (MIT), `README.md`, `site/` Jekyll + GitHub Pages | Public clone path; spec `docs/specs/project-blog/` |

**Dependency edges (build order hint):** hooks + cli-core + index before extension; **`beckett`** is its own install for cron/OODA; skills can ship in parallel once `skills/` layout exists; reflect CLI depends on reflect skill entrypoint contract. **project-blog** is documentation and static web surface only — no hooks or Role custody; ship when `LICENSE` / `README` / site are ready, and keep **README** aligned with `docs/design.md` as other units land (see §11.4).

**Repo root files (constraints 10–11 / S-09–S-10):** `LICENSE` and `README.md` live at the **pirandello** repo root. They are **not** session-hook or `masks` concerns; enforcement is **inspection** (release review, optional CI file-presence checks), with content owned by the **project-blog** proposal.

---

## 3. Cross-unit data flows

### 3.1 Interactive session (hooks path)

1. **Cursor/Claude session start** → `start.sh`: `git pull --ff-only` active Role + `personal/` (latest `SELF.md`), source `.env`, emit prompt stack (see §6 for token gate).
2. **Agent work** → writes under **active Role only** (`Memory/`, `CONTEXT.md`, tasks, etc.); reads `personal/Memory/` per global-read rule (AGENTS.md + design).
3. **Session end** → `end.sh`: `git add -A`, single conventional commit if needed, `git push` (silent failure).
4. **Post-commit** (git inside Role) → if `Memory/` changed → `masks index <role>` incremental update to shared SQLite DB (files canonical, S-02).

### 3.2 OODA path (`beckett run <role-dir-or-name>`)

1. Load `$BASE/.env` + `$ROLE/.env`; parse `OODA.md` agenda; run **all** guards in order.
2. If every guard fails → log line with **`OODA_OK`**, **no LLM** (UC1, T7).
3. If any guard passes → one LLM invocation with **only** `OODA.md` text as the Pirandello document stream; skills pull Memory/Reference/Archive via progressive disclosure inside the run.
4. Observations route per design: work-scoped tools → `work/Memory/`; personal-scoped → `personal/Memory/`; cross-cutting synthesis **only** from `ooda-orient-synthesis` running under `personal/` workspace → `personal/Memory/Synthesis/`.

### 3.3 Synthesis → reflect → PR

1. **`ooda-orient-synthesis`** (weekly, `personal/` only): scans all Roles’ `Memory/**` (excluding `personal/Memory/Synthesis/` for *mining*), applies evidence + cross-role gates, writes/updates `personal/Memory/Synthesis/<pattern>.md`, updates `personal/Memory/INDEX.md`, appends `personal/.synthesis.log`.
2. User or schedule runs **`masks reflect`** → **`reflect` skill** reads synthesis files + Role Memory + `SELF.md`, emits JSON (`proposed_diff`, `pr_title`, `pr_description`, …).
3. **`masks reflect`** applies patch on new `reflect/YYYY-MM-DD` branch in **`personal/` repo only**, push + `gh pr create`, append **`REFLECT_PR`** URL to `personal/.reflect.log` (UC4).
4. Human merges → `main` updated; T2 satisfied if **no direct commits** to `SELF.md` on `main` outside merge commits.

### 3.4 mcp-memory

- **Write path:** markdown file in `Memory/` → git commit → post-commit → `masks index`.
- **Read path:** semantic search scoped by `role:<role>` tags; **rebuild** = `masks index <role> --rebuild` per Role (UC3, T3).
- **Forbidden path:** any tool writing **only** to DB without a file (anti-pattern; S-02).

### 3.5 Public repo surface (`pirandello/`)

- **LICENSE** and **README.md** at repo root satisfy **constraints 10–11** and **S-09 / S-10**. No OODA, session hook, or Role repo involvement.
- **GitHub Pages** (`site/`) is optional discoverability; content must stay **S-01**-clean (no personal data). Factual claims in README, landing page, and posts must match **`docs/design.md`** (project-blog M-05 aligns with system README accuracy).

---

## 4. Custody model (Role remotes end-to-end)

| Mechanism | How separation is preserved |
|-----------|------------------------------|
| **Git remotes** | Each Role is its own repo; `origin` points to GitHub (personal) vs GitLab (work), etc. Session-end hook runs **`cd "$BASE/$ROLE"`** — only that repo receives session commits (UC2, UC8, T1, T4). |
| **push** | Never aggregates Roles into one remote; no submodule of personal inside work. |
| **`masks reflect`** | `cwd` = `$BASE/personal`; only `SELF.md` PRs on personal remote (UC4). |
| **`ooda-orient-synthesis`** | Writes only under `personal/Memory/`; never writes `work/Memory/` (S-04, T8). |
| **`masks index`** | `delete_by_tag(role:…)` scoped; rebuild of work does not wipe personal index rows. |
| **Company access** | If they have only work remote, they see only work repo history — **no** `personal/Memory/` paths in that history (UC8). |

**Write-local enforcement:** Not cryptographically enforced — **contract + hooks + AGENTS**. Work session’s `end.sh` only commits inside `work/`. Agent instructions explicitly forbid writing to `../personal/Memory`; violations are process/policy (anti-pattern signal). Optional hardening: pre-commit hook in each Role rejecting paths outside that repo (future).

---

## 5. Enforcement matrix: hook vs agent vs CLI

| Responsibility | Hook-enforced | CLI-enforced | Agent-instructed |
|----------------|---------------|--------------|------------------|
| Pull at session start | ✅ `start.sh` | `masks sync` optional | — |
| Inject prompt stack order | ✅ `start.sh` | — | Progressive disclosure policy in AGENTS.md |
| Commit + push session end | ✅ `end.sh` | `masks sync` | — |
| mcp-memory incremental index | ✅ `post-commit.sh` | `masks index` manual | — |
| OODA pre-flight / no LLM | — | ✅ `beckett run` | — |
| DB rebuild from files | — | ✅ `masks index --rebuild` | — |
| SELF.md only via PR | — | ✅ `masks reflect` | reflect skill never runs `git` |
| SELF ≤500 tokens post-merge | — | validate in skill + optional `masks doctor` | skill algorithm |
| ROLE.md ≤500 | — | `masks doctor` **warn** | synthesis + curation |
| **Combined always-loaded ~1,500 tokens (warn threshold; constraint 9 / S-08)** | ⚠️ **§6 warning banner** in `start.sh` | `masks doctor` **`always_loaded_budget` WARN** | CONTEXT / ROLE curation guidance in AGENTS (does not replace hook warning) |
| Memory INDEX / Archive INDEX updates | — | — | ✅ skills + AGENTS |
| README in task folders | — | — | ✅ AGENTS |
| Write-local (no personal Memory from work) | partial (repo boundary) | — | ✅ AGENTS |
| Idempotent `masks setup` / add-role | — | ✅ masks-cli-core | — |
| **MIT `LICENSE` at repo root (constraint 10 / S-09)** | — | — | ✅ release review / optional CI (file presence) |
| **`README.md` at repo root — describes project, states license, links `docs/design.md`, ≤100 lines, no personal content (constraint 11 / S-10)** | — | — | ✅ release review / optional CI + human accuracy vs `docs/design.md` |

**S-09 / S-10 are not hook- or CLI-enforced.** They are **repo conventions**: verify by **inspection** at release (files exist, README meets spec), optional **CI** (e.g. assert `LICENSE` and `README.md` exist, line count cap on README). Primary implementation owner: **project-blog** unit (`docs/specs/project-blog/`).

**Principle (S-03):** Anything that **must** happen every session is in **shell hooks** or **`masks`**, not AGENTS.md alone. **S-09 and S-10 are explicitly out of scope for session hooks** — they are static artifacts, not per-session lifecycle behavior.

---

## 6. Token budget enforcement (S-07, S-08, UC9, T6)

**Problem:** Earlier unit prose treated combined always-loaded size as purely “editorial.” `docs/SPEC.md` **constraint 9** and **S-08** require infrastructure for the **combined** `SELF + ROLE + CONTEXT` **warned threshold** (1,500 tokens): the system must surface a breach without hiding it, and **must not** truncate or withhold injected content (UC9, T6).

**Design decision:** **Hard limits** remain per-file only (**constraint 8 / S-07**): `SELF.md` ≤500, `ROLE.md` ≤500. The **1,500-token combined figure is not a truncation point** — it is a **warn threshold** (**constraint 9 / S-08**). Truncating `CONTEXT.md` (or any always-loaded file) at injection time is rejected: silent content removal produces unpredictable agent behaviour. The mechanism is **warn, not truncate**: the hook surfaces the breach visibly; the full files are always injected.

### 6.1 System requirements (aligned with constraints 8–9)

1. **Per-file caps (hard / S-07):** `SELF.md` ≤500, `ROLE.md` ≤500 — enforced by **reflect skill** (tiktoken) for SELF proposals; **synthesis / reflect ROLE suggestions** + human review for ROLE; **`masks doctor`** reports per-file breaches with `WARN` (non-blocking but visible).
2. **Combined threshold (warn / S-08):** At session start, the hook computes `tokens(SELF) + tokens(ROLE) + tokens(CONTEXT)` for `personal/SELF.md`, `[role]/ROLE.md`, and `[role]/CONTEXT.md`. If the sum exceeds 1,500, the hook emits a **visible** warning. All three bodies are injected **in full** — nothing is truncated or withheld. The user shortens `CONTEXT.md` or curates ROLE/SELF in response (or accepts the warning).

**Cross-unit note (onboarding-skill):** During onboarding, the skill may **author** a shorter `CONTEXT.md` so the stack starts near the 1,500-token target. That is **content creation**, not injection-time truncation. Steady-state sessions always follow §6.2 (warn + full inject).

### 6.2 Mechanism (hook + small helper)

- Add **`cli/masks/token_budget.py`** using **tiktoken `cl100k_base`** (same as reflect skill).
- **`start.sh`** (after validation, before printing `=== CONTEXT ===`):
  1. Compute `tokens(SELF) + tokens(ROLE) + tokens(CONTEXT)`.
  2. If sum > 1,500: emit a **warning banner to stderr** (visible in the session preamble):
     `WARNING: always-loaded context is N tokens (budget: 1500). Run masks doctor for remediation.`
  3. Inject all three files in full — **no truncation**.
- **`masks doctor`:** Recompute the same three-file metric; if over budget → **WARN** check `always_loaded_budget` with specific remediation ("shorten CONTEXT.md to ~X tokens" / "curate ROLE.md").

**Stress T6 pass:** With a three-file combination totaling **>1,500** tokens, the session preamble must include the budget **warning**; token-counting the injected `=== SELF ===`, `=== ROLE ===`, and `=== CONTEXT ===` bodies confirms **all content is present** (no truncation). Pass **does not** require constraining or clipping content.

**Metric split (spec):** **S-07** = per-file budgets only (≤500 / ≤500). **S-08** = combined always-loaded warning at session start + `masks doctor` visibility; **no** truncation. Session-hooks and masks-cli-core unit plans already carry matching S-08 self-checks.
---

## 7. Use-case Q&A (must answer)

### UC1 — First day: fresh machine → working session → cron

| Question | Answer |
|----------|--------|
| Session-end commits/pushes work without user action? | ✅ **`end.sh`** auto-commit + push when workspace is valid Role root. |
| Post-commit updates DB for new Memory files? | ✅ **`post-commit.sh`** → `masks index <role>` when `Memory/` changed. |
| First `beckett run work` (or path to `work/`): guards fail, OODA_OK, no LLM? | ✅ **`beckett run`** runs all guards; all fail → log **`OODA_OK`**, exit 0, no subprocess (`beckett` `docs/specs/beckett-run/`). |
| User never runs terminal / configures hooks? | ✅ **Cursor extension** performs clone, `uv tool install`, `masks setup`, writes `.cursor/hooks.json`; user completes onboarding in chat. |

### UC2 — Write-local (Frank example)

| Question | Answer |
|----------|--------|
| New fact lands in `work/Memory/...` not `personal/...`? | ✅ Policy in AGENTS + agent; work **`end.sh`** only touches work repo. |
| personal `git log` clean; work log has commit? | ✅ Yes when session opened at `work/`. |
| Two Frank files (personal historical + work contextual)? | ✅ Expected steady state. |

### UC3 — DB lost → rebuild

| Question | Answer |
|----------|--------|
| `masks index work --rebuild` restores work Memory? | ✅ Deletes `role:work` rows, re-ingests all `Memory/**/*.md`. |
| personal rebuild same? | ✅ |
| Semantic query parity after rebuild? | ✅ All knowledge came from files; **no** DB-only fields (S-02). |

### UC4 — Full reflection pipeline

| Question | Answer |
|----------|--------|
| Synthesis files contain evidence for reflect? | ✅ `ooda-orient-synthesis` template: Pattern + Evidence bullets with Role + dates. |
| PR diff matches skill output? | ✅ `masks reflect` applies **`proposed_diff`** with `git apply` after `git apply --check`. |
| PR only on personal remote? | ✅ All git mutating commands use **`cwd = personal/`**; `gh pr create` targets personal origin. |
| Merged `SELF.md` reflects edits? | ✅ Human merges edited PR; file matches merge result. |
| `.reflect.log` records PR URL? | ✅ **`REFLECT_PR`** line (masks-reflect PLAN). |

### UC5 — ROLE.md isolated named commit

| Question | Answer |
|----------|--------|
| Distinct commit for ROLE.md? | ✅ Agent (or tooling) runs **`git commit` for ROLE.md only** when synthesis proposes update — **before** or **between** session work so it is not lumped ambiguously; message format `role(work): [description] — pattern from [session range]`. |
| `masks status` surfaces it? | ✅ Show last commit touching `ROLE.md` / flag from log parser (status_cmd enhancement if needed). |
| SELF unchanged? | ✅ Single-role patterns routed to ROLE suggestions in reflect skill; not SELF PR. |

### UC6 — Multi-machine CONTEXT.md LWW

| Question | Answer |
|----------|--------|
| Laptop start pulls desktop’s CONTEXT? | ✅ `start.sh` **`git pull --ff-only`** on active Role. |
| Laptop end pushes without manual? | ✅ **`end.sh`**. |
| Desktop gets laptop version next pull? | ✅ Standard git LWW on fast-forward pulls. |
| Merge conflict: `pull --ff-only` fails silently? | ✅ `2>/dev/null || true` — hook does not crash session (scenario). User resolves out-of-band. |

### UC7 — `pirandello/` stays clean

| Question | Answer |
|----------|--------|
| No commits in pirandello from session? | ✅ Session hooks run with cwd Role under base; never `git` inside framework. |
| Memory only in Role repos? | ✅ |
| SELF/ROLE/.env visible in pirandello tree? | ✅ No; they live under base. |
| Clone of pirandello leaks identity? | ✅ S-01 maintained. |

### UC8 — Custody / dual remotes

| Question | Answer |
|----------|--------|
| Work commits only on company remote? | ✅ work repo remote. |
| Personal only on GitHub? | ✅ personal repo remote. |
| No cross-contamination of Memory trees in wrong remotes? | ✅ |

### UC9 — Always-loaded budget

| Question | Answer |
|----------|--------|
| When SELF + ROLE + injected CONTEXT exceed 1,500 tokens at session start, does the system warn? | ✅ **`start.sh`** computes the three-file sum; if **>1,500**, emits the §6 **stderr warning banner** before emitting the prompt stack. |
| Is the warning noticeable (not silently swallowed)? | ✅ Written to **stderr** with explicit `WARNING:` text; Cursor/Claude surfaces hook stderr in the session preamble. |
| Is any content truncated or withheld from the agent because of the budget breach? | **No** — scenario pass: all three files are emitted in full (`cat`); no clipping or omission at injection time. |
| Does `masks doctor` surface a budget alert and indicate how many tokens to trim from CONTEXT.md? | ✅ **`always_loaded_budget`** WARN with remediation text (e.g. shorten CONTEXT by ~N tokens, or curate ROLE). |
| Is budget monitoring implemented in infrastructure (hook + CLI), not only AGENTS.md? | ✅ **Hook + `masks doctor`** implement counting and warnings; AGENTS may reinforce curation but cannot be the sole signal (S-03, S-08). |

### UC10 — Progressive disclosure

| Question | Answer |
|----------|--------|
| Identify folder from INDEX alone when possible? | ✅ Archive INDEX row includes summary + folder key. |
| Stop at Level 1 if enough? | ✅ Agent instruction (AGENTS). |
| Level 2 README before other files? | ✅ Policy. |
| Level 3 only when needed? | ✅ Policy. |
| Session injects indexes only, not deep archive/reference bodies? | ✅ **`start.sh`** cats **INDEX.md** files only — not arbitrary Level 2/3 (T7 injection scope). |

---

## 8. Stress tests

| ID | Pass strategy |
|----|----------------|
| **T1** | Session commits only in Role repo; pirandello never dirty. |
| **T2** | `git log personal/SELF.md` shows exactly two commit classes: one `onboarding: bootstrap SELF.md` commit and zero or more reflect PR merge commits. No other commit messages are acceptable. |
| **T3** | Dual `masks index … --rebuild` restores query results from files. |
| **T4** | `alice.md` only in work git history. |
| **T5** | Idempotent `masks` commands per masks-cli-core + reflect skip rules + index no-op. |
| **T6** | Combined **>1,500** → visible **`start.sh` warning**; verify full injection of SELF + ROLE + CONTEXT bodies; **`masks doctor`** aligns (§6). |
| **T7** | All per-session behaviors listed in design’s reliability table implemented in hooks / **`beckett run`** — not AGENTS-only. |
| **T8** | Cross-role patterns → SELF via reflect; single-role → ROLE.md + work/personal Memory only; synthesis cross-role filter + reflect filter. |

---

## 9. Anti-pattern regression (prevention)

| Signal | Mitigation |
|--------|------------|
| Session-critical only in AGENTS | Hooks + **`beckett run`** own OODA lifecycle (§5). |
| Work session writes `personal/Memory/` | AGENTS + code review; optional pre-commit path guard. |
| Direct `SELF.md` commit | Only `masks reflect` applies SELF patch on branch; hooks never add SELF. |
| DB as source of truth | Indexer only reads files; no “memory_store without file” API in skills. |
| Personal content in pirandello | Workspace discipline; extension writes only under base + `~/Code/pirandello` public files. |
| Always-loaded **>1,500 without warning** | §6 hook + `masks doctor` must emit warnings; silent breach → S-08 (and S-03 if only AGENTS). |
| Non-idempotent masks | Setup/add-role guards per masks-cli-core proposal. |
| Missing root `LICENSE` / `README` or README contradicts design | **project-blog** deliverables + release inspection (S-09, S-10); README tracks `docs/design.md` (§11.4). |

---

## 10. Static evaluation (S-01–S-10)

| ID | System assurance |
|----|------------------|
| **S-01** | Framework repo policy + hook validation + extension never copies Role content into pirandello. |
| **S-02** | File-first Memory; index is derived; rebuild story documented. |
| **S-03** | Pull/inject/commit/push/index triggers in hooks; OODA guards in **`beckett`**. |
| **S-04** | Repo boundaries + synthesis workspace rule + reflect git scope. |
| **S-05** | Idempotent setup/sync/index/reflect skip per unit plans. |
| **S-06** | SELF changes only on reflect branches + PR merge. |
| **S-07** | Per-file hard caps (SELF ≤500, ROLE ≤500): reflect skill + doctor + human merge review; no produced document exceeds per-file budget. |
| **S-08** | Combined always-loaded **warning** when SELF+ROLE+CONTEXT **>1,500** at session start (`start.sh`); full injection always; `masks doctor` **`always_loaded_budget`** remediation; **no** truncation (constraint 9). |
| **S-09** | Repo root **`LICENSE`** present with MIT license text (constraint 10). Verified by inspection / release checklist; not hook-enforced (§5). |
| **S-10** | Repo root **`README.md`** present: describes Pirandello, states license, links **`docs/design.md`**, ≤100 lines, no personal content (constraint 11). Verified by inspection; **accuracy** must track `docs/design.md` as units ship (§11.4). |

---

## 11. Implementation clarifications (cross-unit)

1. **`REFLECT_OK` log ownership:** `masks-reflect` PLAN says CLI appends all log lines; `reflect-skill` PLAN sometimes mentions skill appending `REFLECT_OK`. **Canonical:** **CLI appends exactly one line per non–dry-run** (`REFLECT_OK` / `REFLECT_PR` / `REFLECT_SKIP`) to avoid double writes; skill emits JSON only.
2. **`beckett run` guard path:** Resolve bundled guards via **`beckett`’s** `resolve_framework_root()` → packaged `_data/guards/`, not a hardcoded repo path, for relocatable installs.
3. **Onboarding initial SELF — resolved:** The onboarding skill makes exactly one direct commit to `personal/SELF.md` on `main` with message `onboarding: bootstrap SELF.md`. This is the **sole documented exception** to the PR-only rule (S-06, constraint 7). After onboarding, every `SELF.md` change must go through a `masks reflect` PR. T2 accepts commits matching `onboarding: bootstrap SELF.md` or reflect PR merge commits only.
4. **`README.md` and cross-unit accuracy (S-10):** The root README is a **summary** of what Pirandello is and how to learn more (`docs/design.md`). It must **not** promise features that no unit implements. When a unit ships user-visible capability (e.g. extension install path, `masks` subcommands, `site/` blog), **project-blog** (or a coordinated doc PR) should update README so newcomers are not misled. Jekyll pages and posts are subject to the same **design accuracy** rule (project-blog M-05). README line budget (≤100 lines) implies **link out** rather than duplicating the full unit list — but the **high-level** architecture (Roles, hooks, `masks`, OODA, public vs base) should remain true to the design doc.

---

## 12. Deliverables checklist

- [ ] Implement §6 **S-08 combined budget warning** (not truncation) in `start.sh` + shared token helper + `masks doctor` `always_loaded_budget` check.
- [ ] Align reflect logging single-writer (§11.1).
- [ ] Ensure `ooda-orient-synthesis` only in `personal/OODA.md` Orient section.
- [ ] **S-09 / S-10:** Repo root `LICENSE` (MIT) and `README.md` per constraints 10–11 — track under **project-blog** unit; verify by inspection or light CI (§5).
- [ ] Golden tests: T1/T4/T6/T7 smoke scripts in CI (future).

---

*End of system plan.*
