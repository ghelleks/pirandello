#!/usr/bin/env bash
# After a commit touching Memory/, re-index into mcp-memory.
set +e
REPO="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$REPO" || exit 0
if ! git rev-parse HEAD~1 >/dev/null 2>&1; then
  exit 0
fi
CHANGED="$(git diff --name-only HEAD~1 HEAD -- Memory/ 2>/dev/null)"
DELETED="$(git diff --name-status HEAD~1 HEAD -- Memory/ 2>/dev/null | awk '/^D/{print $2}')"
if [ -z "$CHANGED" ] && [ -z "$DELETED" ]; then
  exit 0
fi
BASE="$(cd "$(dirname "$REPO")" && pwd 2>/dev/null)" || BASE="$(dirname "$REPO")"
if [ -f "$BASE/.env" ]; then
  # shellcheck disable=SC1090
  . "$BASE/.env" 2>/dev/null || true
fi
ROLE="$(basename "$REPO")"
if command -v masks >/dev/null 2>&1; then
  masks index "$ROLE" 2>/dev/null || true
fi
exit 0
