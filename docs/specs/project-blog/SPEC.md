# SDD Spec: Project Blog

**Context:** See `docs/design.md` for full system design. This spec covers the public-facing web presence for the Pirandello project: a GitHub Pages site built with Jekyll containing a landing page and a blog. It also covers the two static files every public repo requires: `LICENSE` and `README.md`.

**Deliverables:**
- `LICENSE` — MIT license at the repo root
- `README.md` — project overview at the repo root
- `site/` — Jekyll source for the GitHub Pages site
  - `site/_config.yml`
  - `site/Gemfile`
  - `site/index.md` — landing page
  - `site/_posts/` — at least one inaugural post

---

## Requirements

### Hard constraints

1. **No personal content.** `LICENSE`, `README.md`, and all files under `site/` must contain no personal identifiers, credentials, employer names, or role-specific details. The blog writes about the *design* of Pirandello, not about the author's job or personal life. S-01 applies fully.
2. **MIT license text must be exact.** The `LICENSE` file must contain the standard MIT license text with the copyright year and the placeholder `[year] [author]` filled in with `2026 Gunnar Hellekson`. No other license text may appear.
3. **README accuracy.** The `README.md` must not describe features that do not exist or are not specified. It may describe the design intent and link to `docs/design.md` for the full picture.
4. **Jekyll site must build without errors** using `bundle exec jekyll build`. No broken internal links on the landing page or first post.
5. **Site source lives in `site/`.** GitHub Pages is configured to serve from `site/` on the `main` branch (not from `docs/`, which is reserved for design documentation). The `site/` directory must contain a complete, self-contained Jekyll project.
6. **Blog posts must be accurate representations of the design.** Any factual claim about how Pirandello works must be consistent with `docs/design.md`. A post that contradicts the design document fails M-05.
7. **The site must not require JavaScript to read.** Progressive enhancement is fine; core content must be accessible without JS.

### Soft constraints

- Use the Jekyll Minima theme (v2) or another theme available on GitHub Pages without a custom plugin. No custom Jekyll plugins that require `--unsafe` or that GitHub Pages does not support natively.
- Keep `README.md` under 100 lines. Link to `docs/design.md` for depth rather than duplicating it.
- Posts should be written in the same voice as `docs/design.md` — direct, philosophical where the subject calls for it, never breathless or promotional.
- The landing page should be comprehensible to a technically literate person who has never heard of Pirandello.

---

## Proposal format

### 1. LICENSE
The exact MIT license text to use, with year and author filled in.

### 2. README.md structure
Section-by-section outline: what each section covers, roughly how long it should be, and which links it must include.

### 3. Jekyll site structure
Directory layout of `site/`. Which theme, which `_config.yml` settings (title, description, baseurl, plugins, exclude list). How `site/` is excluded from Jekyll processing the rest of the repo.

### 4. Landing page (`site/index.md`)
What the landing page covers: the one-paragraph pitch, the key concepts (Roles, SELF.md, the reflect ritual), how to get started, links.

### 5. Inaugural post
Title, date, scope, and outline of the first blog post. The post should introduce the philosophical premise (Pirandello's novel, the masks metaphor) and explain why it shaped the design — drawing from `docs/design.md` § "A note on Pirandello" and § "World Model" without copying them verbatim.

### 6. GitHub Pages configuration
How GitHub Pages is pointed at `site/` on `main`. What the `_config.yml` `baseurl` and `url` values should be. Whether a custom domain is needed or the default `*.github.io` URL suffices.

### 7. Open decisions
Anything left unresolved: custom domain vs. github.io URL, theme customization beyond Minima defaults, future post cadence.

### 8. Self-check table
See Static Evaluation Metrics.

---

## Static evaluation metrics

| ID   | Name                    | Pass condition                                                                                                   |
|------|-------------------------|------------------------------------------------------------------------------------------------------------------|
| M-01 | LICENSE present         | `LICENSE` exists at repo root with exact MIT text, correct year and author                                       |
| M-02 | README present          | `README.md` exists at repo root, ≤100 lines, links to `docs/design.md`, contains no personal content            |
| M-03 | Jekyll builds           | `bundle exec jekyll build` in `site/` exits 0 with no errors or warnings                                        |
| M-04 | No broken links         | All internal links on the landing page and inaugural post resolve to existing anchors or pages                   |
| M-05 | Design accuracy         | No factual claim in any blog post or landing page contradicts `docs/design.md`                                   |
| M-06 | No JS required          | Landing page and posts render full content with JavaScript disabled                                              |
| M-07 | site/ self-contained    | `site/` contains `_config.yml`, `Gemfile`, at least one post, and an `index.md`; no required files outside `site/` |
| M-08 | No personal content     | No post, page, or config file contains personal identifiers, credentials, or employer names (S-01)               |
