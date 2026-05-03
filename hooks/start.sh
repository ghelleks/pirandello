#!/usr/bin/env bash
# Pirandello session start — pull, then prompt agent to retrieve context from MCP memory.
set +e

BASE="$(cd "$(dirname "$PWD")" && pwd)" 2>/dev/null || BASE="$(dirname "$PWD")"

git pull --ff-only 2>/dev/null || true
if [ -d "$BASE/personal/.git" ]; then
  git -C "$BASE/personal" pull --ff-only 2>/dev/null || true
fi

cat <<'PROMPT'
=== SESSION START ===
Before responding to any request, search MCP memory for working context:
- Your identity and values: search query "identity values how I work"
- Current priorities and active work: search tags ["context"] combined with your role name
- Any relevant context for the project or task at hand

Use the memory_search tool proactively. Do not wait to be asked.
PROMPT

exit 0
