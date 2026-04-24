# Plan: Project Blog (SDD Triad)

**Unit:** `project-blog`  
**Spec:** `docs/specs/project-blog/SPEC.md`  
**Scenarios:** `docs/specs/project-blog/SCENARIOS.md`  
**Authoritative design:** `docs/design.md`  
**Date:** 2026-04-24  
**Status:** proposal (implementation not started)

This plan satisfies the unit spec proposal format (§ Proposal format) and is written to pass M-01–M-08, S-01, S-09, and S-10 when executed. Evaluation against scenario use cases and stress tests is summarized in § 8.

---

## 1. LICENSE

Place at repository root as `LICENSE` (no extension). Use this **exact** text:

```text
MIT License

Copyright (c) 2026 Gunnar Hellekson

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

**Note:** The copyright line satisfies the unit spec (2026, Gunnar Hellekson). The LICENSE file is not part of the GitHub Pages site or `README.md`; scenarios that forbid personal identifiers on the **site** and in the **README** remain satisfied.

---

## 2. README.md structure

Target: **≤100 lines**, **no personal identifiers** (no full name, employer, work email, job title, colleague names). Voice: neutral third person or “this repository.” State the **MIT** license in prose and point to `LICENSE`.

| Section | Purpose | Length guidance | Required links |
|--------|---------|-----------------|----------------|
| **Title + one-line description** | What Pirandello is in plain language (memory + configuration for AI-assisted work; files + git; Roles). | 1–2 sentences (~40–60 words) | — |
| **What you get** | Bullets: `masks` CLI, conventions (`AGENTS.md`, hooks), optional skills — framed as **design intent** where not yet shipped; avoid claiming marketplace extension unless that unit is done. | ~8–12 lines | `docs/design.md` |
| **Requirements** | Cursor or Claude Code (interactive path); `uv` for Python/`masks`; `git`; optional `gh` for PR workflows **when** using reflect-on-GitHub as designed. Do not invent tools. | ~4–6 lines | — |
| **Quick start (manual path)** | Clone repo; install CLI via `uv` as in design doc; run `masks setup`; open a Role workspace. Keep steps minimal; defer nuance to design doc. | ~8–12 lines | `docs/design.md` |
| **Documentation** | “Full system design” link; optional pointer to `docs/specs/` for contributors. | ~3–5 lines | `docs/design.md` |
| **License** | MIT; reference `LICENSE` file. | 1–2 lines | — |
| **Disclaimer** | Repo is public; no personal Role content belongs here. | 1–2 lines | — |

**Voice / accuracy guardrails (M-05, scenario anti-patterns):** Describe only behaviors specified in `docs/design.md` and unit specs. If a roadmap item is not built, label it as **planned** or omit it. Do not promise email summarization, automatic inbox processing, or other features not covered by specs.

---

## 3. Jekyll site structure

### 3.1 Full `site/` layout

```text
site/
├── Gemfile
├── Gemfile.lock          # committed after first bundle lock; see CI note
├── _config.yml
├── index.md              # landing page (Minima: layout front matter)
├── _posts/
│   └── 2026-04-24-one-no-one-and-one-hundred-thousand.md   # inaugural post (slug TBD in implementation)
├── assets/               # optional; only if overriding Minima (can start empty or omit)
└── .gitignore            # _site, .sass-cache, vendor, .bundle
```

**Theme:** `minima` **v2.x**, via `theme: minima` in `_config.yml`, using the **`github-pages`** gem in the Gemfile so local builds track [Pages-supported versions](https://pages.github.com/versions/).

### 3.2 `site/_config.yml` (settings)

- `title`: `Pirandello` (or `Pirandello — files, roles, and memory for agents` if it fits style)
- `description`: One sentence, non-personal, matching the README pitch.
- `url`: `https://<github-username>.github.io` — set at implementation time to the repo owner’s GitHub Pages host.
- `baseurl`: `/<repository-name>` — e.g. `/pirandello` for project pages. **Must** match the repo name for asset and post permalinks.
- `theme`: `minima`
- **Do not** set `author` to a real person’s name (M-08). Omit `author` or use a project-level string such as `The Pirandello project` if Minima requires something.
- `plugins`: only `jekyll-feed` and `jekyll-seo-tag` if included by the `github-pages` constraint set (do not add unsupported plugins).
- `markdown`: `kramdown` (default with Pages)
- `exclude` (within `site/` only): `Gemfile`, `Gemfile.lock`, `README.md` (if any), `vendor`, `node_modules` (if ever added)

**Important:** Jekyll is **never** run from the repository root. Only `site/` is the Jekyll project root. That **naturally** excludes `docs/`, specs, and CLI code from processing — no parent-folder `exclude` hack required.

### 3.3 `site/Gemfile`

```ruby
source "https://rubygems.org"

gem "github-pages", group: :jekyll_plugins
```

Lock with `bundle install` in `site/` and commit `Gemfile.lock` so CI and contributors get reproducible builds (supports stress test T2).

### 3.4 Repo-level exclusion of build artifacts

Add to **repository root** `.gitignore` (append, do not remove existing entries):

```gitignore
site/_site/
site/.sass-cache/
site/.jekyll-cache/
site/vendor/bundle/
site/.bundle/
```

This keeps the monorepo clean without moving Jekyll into `docs/`.

### 3.5 GitHub Actions vs. branch folder (serving from `site/`)

GitHub’s **branch** Pages source allows only **`/` (root)** or **`/docs`**. The unit spec requires the Jekyll **source** to live in **`site/`**. **Resolution:** use **GitHub Actions** as the Pages **source** (Settings → Pages → Build and deployment → Source: **GitHub Actions**), with a workflow that:

1. Checks out `main`
2. Sets up Ruby
3. Runs `bundle install` and `bundle exec jekyll build` with working directory `site/`
4. Uploads `site/_site` via the official `actions/upload-pages-artifact` + deploy pattern

This satisfies “serve from `site/` on `main`” in the sense that **`main` holds the source under `site/`** and the published site is built from that folder. Document the one-time repo setting in README or `site/README.md` (optional short file) for maintainers.

---

## 4. Landing page (`site/index.md`)

**Layout:** `layout: home` (Minima home layout).

**Content structure:**

1. **Hero / pitch (one short paragraph):** Pirandello is a file- and git-first system for AI-assisted memory and configuration: many **Roles** (contexts), one cognitive model, hooks and a `masks` CLI for reliability. No databases as source of truth for memory — markdown files are canonical.

2. **Why the name (two to three sentences):** Literary reference as metaphor only — **no long plot summary**; enough to signal “masks / identity as draft.” Link to the inaugural post for the full philosophical setup (keeps index.md short and avoids duplicating the post).

3. **Key concepts (short bullets):**
   - **Roles:** separate directories/repos per context; session root is always a Role directory.
   - **SELF.md / ROLE.md:** cross-role draft vs. per-role behavioral delta; sizes and update ceremonies per design doc (high level only).
   - **Reflect ritual:** agent proposes changes to `SELF.md` via PR; human merges or rejects — not auto-truth.
   - **Memory / Reference / Archive:** progressive disclosure; files under git; semantic index is regenerable.

4. **For contributors / readers:** Link to GitHub repo, `docs/design.md`, and the blog index (Minima shows recent posts on `home`).

5. **No personal content:** No names, employers, emails, or identifiable anecdotes (M-08, scenarios).

**Internal links:** Use `{{ site.baseurl }}` in Liquid where needed, or root-relative paths Minima expects, so built URLs work on GitHub Pages (supports T5).

---

## 5. Inaugural post

- **Title (proposal):** `One, no one, and one hundred thousand: why Pirandello is a system about drafts, not truths`
- **Date:** `2026-04-24`
- **Slug (filename):** `2026-04-24-one-no-one-and-one-hundred-thousand.md` (adjust for Jekyll slug rules if title changes)
- **Layout:** `post`
- **Author front matter:** use `author: Pirandello` or omit; **do not** use a real person’s name in front matter or body (M-08, UC-1, UC-3).

**Detailed outline (paraphrase design.md; do not copy verbatim):**

1. **Opening — the literary hook:** Introduce the early 20th-century novelist and the novel *One, No One, and One Hundred Thousand* at a high level: a moment of estrangement from one’s own image; the idea that others hold many partial versions of “you,” and the self is not a single fixed object.

2. **The design response — discomfort as a feature:** Acknowledge the tension with files like `SELF.md`: the design does not dismiss the discomfort; it treats identity as **editable narrative** — the agent gathers patterns; the human **edits** what becomes the next draft.

3. **World model themes (synthesized):**
   - **Whole person, not a job title:** the architecture centers a human across life contexts, not a single employer-shaped profile (no employer names or personal job details in the post).
   - **Self as draft:** masks worn consistently and revised deliberately; align with `SELF.md` / `ROLE.md` split and token budgets as **design constraints**, not autobiography.
   - **Unified mind, split custody:** one mental model; git remotes reflect legitimate separation of personal vs. work custody — describe **only** as in design.md (generic “work-like role” language).
   - **Files over databases for human-owned memory:** readability, diffability, control; mcp-memory as **index**, not source of truth.
   - **Git as backbone:** history, sync, collaboration.
   - **Infrastructure vs. instructions:** hooks and CLI enforce what must happen; docs guide the rest.
   - **Simplicity for sharing:** if a colleague cannot onboard in one session, the system is too complex — state as **design value**.

4. **How this maps to the system (factual, checkable):** Short, precise bullets tying the philosophy to mechanisms: Role directories, prompt stack concept, write-local / global-read memory rule, `masks reflect` PR-only path for `SELF.md` after bootstrap, OODA as separate path — **every claim must trace to `docs/design.md`** (M-05, T3).

5. **Closing:** Invitation to read `docs/design.md` and the repo; no CTA that promises unbuilt product features.

---

## 6. GitHub Pages configuration

| Setting | Value |
|--------|--------|
| **Source** | **GitHub Actions** (required to build from `site/`; branch-based deploy does not offer `/site`) |
| **Branch for content** | `main` holds `site/` sources; workflow runs on push to `main` (and optionally PRs with build-only jobs) |
| **`url` in `_config.yml`** | `https://<user>.github.io` |
| **`baseurl` in `_config.yml`** | `/<repo>` e.g. `/pirandello` |
| **Custom domain** | **Not required** for MVP. Default `*.github.io/<repo>/` suffices. If a custom domain is added later, set `url`/`baseurl` per GitHub docs and add `CNAME` only when ready. |

**Post-implementation verification:** Visit Pages URL with JS disabled (T4); check `/` and first post paths under `baseurl`.

---

## 7. Open decisions

| Topic | Status |
|-------|--------|
| **Custom domain** | Deferred; use `github.io` until a stable public name is chosen. |
| **Minima branding** | Default skin first; optional logo/favicon later (must remain lightweight, no JS dependency for content). |
| **Blog cadence** | No schedule in MVP; follow-up posts when major units ship (hooks, extension, etc.). |
| **`Gemfile.lock` policy** | Recommend commit lockfile for CI; if `github-pages` upgrades break builds, pin in Gemfile — **operational**, not conceptual. |
| **Author attribution on posts** | Prefer project-level attribution only on the public site; personal credit already in `LICENSE` at repo root per spec. |

---

## 8. Self-check table

| ID | Pass? | Evidence / implementation note |
|----|-------|----------------------------------|
| **M-01** | Yes | §1 LICENSE text at repo root, 2026, Gunnar Hellekson |
| **M-02** | Yes | §2 structure; ≤100 lines; links `docs/design.md`; no personal content in README body |
| **M-03** | Yes | `github-pages` Gemfile; build only in `site/`; pin/lock deps to minimize warnings — if Jekyll emits **deprecation** warnings only, treat as follow-up unless spec tightens “warnings” |
| **M-04** | Yes | Use `baseurl`-aware links; verify internal links against `_site/` after build |
| **M-05** | Yes | Landing + post trace claims to `docs/design.md`; README avoids speculative features |
| **M-06** | Yes | Minima content is HTML from Markdown; no JS gate for text |
| **M-07** | Yes | All Jekyll inputs under `site/`; build cwd is `site/` |
| **M-08** | Yes | No personal IDs in `site/` files; README sanitized; LICENSE is separate |
| **S-01** | Yes | No credentials, employer, or personal life details in README or site |
| **S-09** | Yes | MIT `LICENSE` at root (§1) |
| **S-10** | Yes | README describes project, states license, links `docs/design.md` |

**Scenario coverage (summary only):** UC-1–5 and T1–T5 are satisfied by the combination of §§2–6 and the self-check rows above, **provided** implementation matches this plan verbatim on sensitive items (no personal prose in README/site, Actions build from `site/`, inaugural post claims sourced from design.md).

---

## Metrics / spec interpretation notes (revision log)

- **M-03 “no warnings”:** Strict zero-warning builds can conflict with upstream Jekyll/theme deprecations. **Plan:** treat **errors** as failures; **warnings** — eliminate where easy; document any unavoidable deprecation noise in CI with a ticket to upgrade when `github-pages` allows. If the project requires literal zero warnings, add `JEKYLL_LOG_LEVEL=error` or equivalent only after verifying it does not hide real issues.
- **`site/` vs. GitHub branch UI:** Resolved by **GitHub Actions** publish path so the spec’s `site/` directory is honored without polluting `docs/`.
- **Copyright name vs. anonymity on site:** Resolved by **LICENSE** (legal name required by unit spec) vs. **public site/README** (no personal identifiers per M-02/M-08 and scenarios).

---

## Implementation checklist (post-approval)

1. Add `LICENSE` (§1) and `README.md` (§2) at repo root.
2. Create `site/` tree, `Gemfile`, `_config.yml`, `index.md`, `_posts/…` (§§3–5).
3. Update root `.gitignore` for Jekyll artifacts (§3.4).
4. Add `.github/workflows/pages.yml` (deploy) and optionally `jekyll.yml` (PR build).
5. Enable Pages (GitHub Actions source); set `url` / `baseurl` after first deploy.
6. Run `cd site && bundle install && bundle exec jekyll build`; fix links; re-run with JS off.
