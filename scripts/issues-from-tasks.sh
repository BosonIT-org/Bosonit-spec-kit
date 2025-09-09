#!/usr/bin/env bash
set -euo pipefail
# Usage: GH_TOKEN=... REPO=owner/name scripts/issues-from-tasks.sh path/to/tasks.md
FILE=${1:-}
REPO=${REPO:-}
if [[ -z "$FILE" || -z "$REPO" ]]; then echo "Usage: REPO=owner/name $0 path/to/tasks.md"; exit 2; fi
if [[ ! -f "$FILE" ]]; then echo "File not found: $FILE"; exit 2; fi
if [[ -z "${GH_TOKEN:-}" ]]; then echo "GH_TOKEN not set"; exit 2; fi
mapfile -t LINES < <(grep -E '^- \[ \] |^- \[x\] ' "$FILE" | sed 's/^- \[[x ]\] //')
for TITLE in "${LINES[@]}"; do
  BODY=$(jq -Rs . <<< "$TITLE")
  curl -sS -X POST \
    -H "Authorization: Bearer $GH_TOKEN" \
    -H 'Accept: application/vnd.github+json' \
    https://api.github.com/repos/$REPO/issues \
    -d "{\"title\":$BODY, \"labels\":[\"spec-task\"]}" >/dev/null
  echo "[OK] Created: $TITLE"
done
