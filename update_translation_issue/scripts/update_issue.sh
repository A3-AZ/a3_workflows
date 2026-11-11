#!/usr/bin/env bash
# Creates the open issue titled $TITLE with the body in $BODY_FILE, or edits it if its body differs.
# Lines starting with "_Coverage last changed in " are ignored when comparing, so the commit SHA
# in the body only changes together with the coverage itself.
#
# Env: GH_TOKEN, GH_REPO, TITLE, BODY_FILE, DRY_RUN ('true' = only report what would be done)
# Writes the outputs 'result' (created|updated|unchanged) and 'issue-number' to $GITHUB_OUTPUT if set.

set -euo pipefail

: "${TITLE:?TITLE is not set}"
: "${BODY_FILE:?BODY_FILE is not set}"
DRY_RUN="${DRY_RUN:-false}"

output() {
  if [ -n "${GITHUB_OUTPUT:-}" ]; then
    echo "$1=$2" >> "$GITHUB_OUTPUT"
  fi
}

# Drop the SHA line, carriage returns (bodies edited in the browser) and trailing blank lines
normalize() {
  grep -v '^_Coverage last changed in ' | sed 's/\r$//' | sed -e :a -e '/^\n*$/{$d;N;ba' -e '}'
}

# Exact title match, ignoring case. Lists issues instead of using the search API, which lags behind
# and could miss an issue created moments ago. The oldest match wins if there are duplicates.
issue=$(TITLE="$TITLE" gh issue list --state open --limit 1000 --json number,title \
  --jq '[.[] | select((.title | ascii_downcase) == (env.TITLE | ascii_downcase))] | sort_by(.number) | .[0].number // empty')

prefix=""
if [ "$DRY_RUN" = "true" ]; then
  prefix="[dry-run] "
fi

if [ -z "$issue" ]; then
  echo "${prefix}No open issue titled \"$TITLE\" in $GH_REPO - creating it"
  if [ "$DRY_RUN" != "true" ]; then
    url=$(gh issue create --title "$TITLE" --body-file "$BODY_FILE")
    issue="${url##*/}"
    echo "Created $url"
  fi
  output result created
elif [ "$(gh issue view "$issue" --json body --jq .body | normalize)" = "$(normalize < "$BODY_FILE")" ]; then
  echo "${prefix}Issue #$issue is already up to date"
  output result unchanged
else
  echo "${prefix}Updating issue #$issue"
  if [ "$DRY_RUN" != "true" ]; then
    gh issue edit "$issue" --body-file "$BODY_FILE"
  fi
  output result updated
fi

output issue-number "$issue"
