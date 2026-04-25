# Skill: mask-onboarding

Guides **first-time Pirandello** setup after the extension or `masks setup` created scaffolding.

## Phases (state machine)

Track progress in the user’s workspace notes or Todoist; do **not** invent hidden global state files beyond what this skill explicitly authorizes.

### Phase 1 — Identity (`personal/`)

1. Confirm `personal/SELF.md` exists (bootstrap may have stubbed it).
2. Ask **one** question per turn about identity, values, communication defaults.
3. Write answers into `SELF.md` sections without exceeding per-file token budgets (see `docs/design.md`).
4. End Phase 1 with a **bootstrap commit** in `personal/` only: `onboarding: bootstrap SELF.md`

### Phase 2 — Roles

1. Ensure `work/` (or other Roles) have `ROLE.md` stubs upgraded with real behavioral deltas.
2. For each Role that uses scheduled OODA (`beckett run`), confirm `OODA.md` signal sources list matches reality (use `add-role` skill patterns). Skip Roles without `OODA.md`.

### Phase 3 — Infrastructure

1. Verify `masks doctor` passes blocking checks (or capture WARN-only items like token budget).
2. MCP, Google, Todoist, etc. — one integration per turn; never store secrets in chat logs.

## CONTEXT condensation

If `CONTEXT.md` exists, prefer bullets under 1,500 **combined** tokens with `SELF.md` + `ROLE.md` — enforcement is the session hook (`start.sh`), not this skill.

## Resume

If the user returns mid-phase, ask which phase to continue; **never** delete prior good content.
