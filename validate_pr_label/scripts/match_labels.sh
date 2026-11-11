#!/usr/bin/env bash
# Filters pull request labels by glob patterns.
#
# Usage: match_labels.sh '<patterns>' < labels.txt
#   labels    one label per line on stdin
#   patterns  glob patterns (*, ?, [...]), separated by commas or newlines.
#             Empty = every label counts. Matching ignores case, like GitHub does for label names.
#
# Prints every label that matches at least one pattern, one per line.
# Exit code: 0 = at least one label matched, 1 = none matched.

set -euo pipefail
shopt -s nocasematch

patterns=()
while IFS= read -r p; do
  # trim surrounding whitespace
  p="${p#"${p%%[![:space:]]*}"}"
  p="${p%"${p##*[![:space:]]}"}"
  [ -n "$p" ] && patterns+=("$p")
done < <(printf '%s\n' "${1:-}" | tr ',' '\n')
[ ${#patterns[@]} -gt 0 ] || patterns=('*')

found=1
while IFS= read -r label || [ -n "$label" ]; do
  [ -n "$label" ] || continue
  for p in "${patterns[@]}"; do
    # shellcheck disable=SC2053 # the pattern is unquoted on purpose, so it is matched as a glob
    if [[ "$label" == $p ]]; then
      printf '%s\n' "$label"
      found=0
      break
    fi
  done
done

exit "$found"
