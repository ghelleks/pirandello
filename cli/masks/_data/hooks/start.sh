#!/usr/bin/env bash
# Pirandello session start — pull, optional token-budget warning, inject prompt stack.
# Role = basename($PWD), Base = dirname($PWD). POSIX bash.

set +e

BASE="$(cd "$(dirname "$PWD")" && pwd)" 2>/dev/null || BASE="$(dirname "$PWD")"
ROLE="$(basename "$PWD")"

# Optional: Cursor passes JSON on stdin — drain so downstream does not see it.
if [ -n "${PIRANDELLO_CURSOR_JSON:-}" ]; then
  cat >/dev/null 2>&1 || true
fi

if [ ! -f "$PWD/ROLE.md" ] || [ ! -f "$BASE/personal/SELF.md" ] || [ ! -f "$BASE/AGENTS.md" ]; then
  echo "Pirandello: workspace does not look like a Role (missing ROLE.md, personal/SELF.md, or base AGENTS.md). Open the Role directory as the workspace root." >&2
  exit 0
fi

if [ -f "$BASE/.env" ]; then
  # shellcheck disable=SC1090
  . "$BASE/.env" 2>/dev/null || true
fi
if [ -f "$PWD/.env" ]; then
  # shellcheck disable=SC1090
  . "$PWD/.env" 2>/dev/null || true
fi

git pull --ff-only 2>/dev/null || true
if [ -d "$BASE/personal/.git" ]; then
  git -C "$BASE/personal" pull --ff-only 2>/dev/null || true
fi

_sum=""
if command -v masks >/dev/null 2>&1; then
  _sum="$(masks token-budget always-loaded --base "$BASE" --role-dir "$PWD" 2>/dev/null)" || _sum=""
elif command -v python3 >/dev/null 2>&1; then
  _sum="$(python3 -m masks.token_budget always-loaded --base "$BASE" --role-dir "$PWD" 2>/dev/null)" || _sum=""
fi
if [ -n "$_sum" ] && [ "$_sum" -gt 1500 ] 2>/dev/null; then
  echo "WARNING: always-loaded context is ${_sum} tokens (budget: 1500). Run masks doctor for remediation." >&2
fi

emit() {
  _hdr="$1"
  _file="$2"
  _req="$3"
  echo "$_hdr"
  if [ -f "$_file" ]; then
    cat "$_file" 2>/dev/null || true
  elif [ "$_req" = "1" ]; then
    :
  fi
  echo ""
}

emit "=== GLOBAL AGENTS ===" "$BASE/AGENTS.md" 1
emit "=== SELF ===" "$BASE/personal/SELF.md" 1
emit "=== ROLE ===" "$PWD/ROLE.md" 1
emit "=== ROLE AGENTS ===" "$PWD/AGENTS.md" 0
emit "=== CONTEXT ===" "$PWD/CONTEXT.md" 0
emit "=== ARCHIVE INDEX ===" "$PWD/Archive/INDEX.md" 0
emit "=== MEMORY INDEX ===" "$PWD/Memory/INDEX.md" 0
emit "=== REFERENCE INDEX ===" "$PWD/Reference/INDEX.md" 0

exit 0
