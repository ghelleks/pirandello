#!/usr/bin/env bash
set -euo pipefail

command -v gws >/dev/null 2>&1 || exit 1

if gws gmail triage --account work 2>/dev/null | grep -q .; then
  exit 0
fi

exit 1
