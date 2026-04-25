---
layout: post
title: "One, no one, and one hundred thousand: drafts, not truths"
date: 2026-04-24
author: Pirandello
---

Luigi Pirandello’s novel *One, No One, and One Hundred Thousand* turns on a moment of estrangement: the sense that others hold countless partial versions of “you,” and that a single fixed self-image is hard to defend. This project borrows only the metaphor—**masks** and **drafts**—not a plot summary.

## Discomfort as a feature

If it feels odd to keep a living `SELF.md`, that friction is intentional. The architecture treats identity narrative as **editable text**: agents may surface patterns; humans decide what becomes the next draft. Nothing silently overwrites cross-role narrative after bootstrap—proposed changes flow through review (`masks reflect` as designed in `docs/design.md`).

## Whole person, split custody

The layout centers one person across multiple contexts, not a single employer-shaped profile. Git remotes and directories reflect legitimate separation of custody (for example personal versus work-like roles) without pretending those boundaries do not exist.

## Files over databases; git as backbone

Human-owned memory lives in markdown under git: readable, diffable, portable. A semantic index may accelerate search, but **files remain canonical**; losing the database must be recoverable by re-indexing from disk.

## Infrastructure over instructions

Hooks and the `masks` CLI enforce what must happen on session start, end, and post-commit. Documentation still matters—but reliability does not rest on the model “remembering” to commit.

## Simplicity for sharing

If a colleague cannot onboard in one session, the system is too complex. That bar is explicit design debt: fewer moving parts, clearer defaults, and specs that stay honest about what is automated versus manual.

For mechanisms (Roles, OODA, memory write-local rules, token budgets), see **`docs/design.md`** in the repository—this post stays at the level of intent, not implementation trivia.
