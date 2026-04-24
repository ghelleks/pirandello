# SDD Scenarios: Project Blog

**Companion spec:** `docs/specs/project-blog/SPEC.md`  
**Date:** 2026-04-24

These scenarios test the public-facing deliverables: `LICENSE`, `README.md`, and the GitHub Pages Jekyll site. They check correctness, consistency with the design document, and the absence of personal content.

---

## Use Cases

### 1. A colleague discovers the repo on GitHub

A technically literate colleague — someone who uses Cursor and has heard of AI memory systems — lands on the GitHub repo page for the first time. They read the `README.md` and then visit the GitHub Pages site.

Questions the proposal must answer:
- Does `README.md` explain what Pirandello is in the first three sentences without jargon specific to this project?
- Does it tell them what they need to run it (Cursor or Claude Code, `uv`, `gh`)?
- Does it link to `docs/design.md` for the full picture?
- Does the GitHub Pages landing page give them a reason to read further — the concept, the philosophy, the key insight?
- At no point does the colleague see the author's name, employer, email, or any personal detail in the README or on the site?

System constraint references: S-01 (no personal content), M-02, M-08

---

### 2. A developer wants to install Pirandello

After reading the README, a developer wants to try Pirandello. They follow the instructions in `README.md`.

Questions the proposal must answer:
- Does the README provide the minimum install steps (or a clear pointer to where those steps live)?
- Is every instruction in the README consistent with what the specs actually describe (no features described that don't exist yet)?
- Does the README state the license clearly?

System constraint references: M-02, M-05

---

### 3. Someone reads the inaugural blog post

A reader finds the GitHub Pages site and reads the first post. They have no prior knowledge of Pirandello the novelist.

Questions the proposal must answer:
- Does the post explain the Pirandello literary reference well enough that the reader understands the name choice without needing to look it up?
- Does the post explain the "masks" metaphor and how it shapes the file/Role model?
- Does every factual claim about how the system works match `docs/design.md`?
- Is the post free of personal details about the author's specific job, employer, or personal life?

System constraint references: M-05, M-08

---

### 4. Jekyll site build in CI

A contributor clones the repo and runs `bundle exec jekyll build` inside `site/`.

Questions the proposal must answer:
- Does the build exit 0?
- Are there no missing layout or include errors?
- Does the generated site contain the landing page and at least one post?
- Is `site/` fully self-contained — no references to files outside `site/` that Jekyll needs at build time?

System constraint references: M-03, M-07

---

### 5. License audit

A legal or compliance reviewer inspects the repo for licensing.

Questions the proposal must answer:
- Is there exactly one `LICENSE` file, at the repo root?
- Does it contain standard MIT license text?
- Is the copyright year correct (2026)?
- Is the author name present and not a placeholder?

System constraint references: M-01, S-09

---

## Stress Tests

**T1 README contains no personal content.**  
`grep` the `README.md` for any email address, employer name, or personal identifier. Pass: no matches.

**T2 Site builds from a clean clone.**  
After `git clone` and `bundle install` inside `site/`, running `bundle exec jekyll build` completes without errors on a machine that has never seen the repo.  
Pass: build exit code 0; `_site/index.html` and at least one post HTML file exist.

**T3 Blog post claims are consistent with design doc.**  
For each factual claim in the inaugural post about how Pirandello works, identify the corresponding passage in `docs/design.md`. Pass: every claim has a supporting passage; no claim contradicts any passage.

**T4 No JS required.**  
Load the landing page and first post with JavaScript disabled in a browser. Pass: all text content is visible and readable; no content is hidden behind a JS wall.

**T5 Internal links resolve.**  
Parse all `[text](url)` links in `site/index.md` and any `_posts/*.md` files. For internal links (same site), verify the target page or anchor exists in the generated `_site/`. Pass: zero 404s among internal links.

---

## Anti-Pattern Regression Signals

**Personal content in a blog post.** A post mentions the author's specific employer, job title, team name, or a colleague by name. Symptom: the public repo leaks identifying information about the author's work context. Indicates: S-01 violated; the "no personal content" constraint was not applied to prose writing, only to code. Maps to: S-01, M-08.

**README describes unspecified features.** The README says Pirandello does something that no unit spec covers (e.g. "automatically summarizes your email"). Symptom: users are misled; the gap between documentation and reality erodes trust. Indicates: M-05 violated; README was written aspirationally rather than descriptively. Maps to: M-05.

**Jekyll site in `docs/` instead of `site/`.** The Jekyll source is placed inside `docs/` — either in a subdirectory or mixed with spec files — because `docs/` is the other conventional GitHub Pages source. Symptom: Jekyll build picks up spec markdown files and tries to render them as pages; `docs/` loses its clean structure as a design-document folder. Indicates: M-07 violated; separation of `docs/` (design) and `site/` (web) not maintained. Maps to: M-07.

**LICENSE file is missing or non-standard.** The repo ships without a `LICENSE` file, or uses a non-MIT license text, or leaves the author/year as a placeholder. Symptom: potential contributors cannot determine the terms under which they can use or modify the code; GitHub displays "No license" on the repo page. Indicates: M-01, S-09 violated. Maps to: M-01, S-09.
