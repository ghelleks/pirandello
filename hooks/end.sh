#!/usr/bin/env bash
# Pirandello session end — stage, conditional commit, push.
set +e
cd "$PWD" 2>/dev/null || exit 0
git add -A 2>/dev/null || true
if ! git diff --cached --quiet 2>/dev/null; then
  git commit -m "session: $(date '+%Y-%m-%d %H:%M')" 2>/dev/null || true
fi
git push 2>/dev/null || true
exit 0
