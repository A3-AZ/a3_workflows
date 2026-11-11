#!/usr/bin/env bash
# Unit tests for scripts/match_labels.sh. Run: bash validate_pr_label/tests/test_match_labels.sh

set -uo pipefail
script="$(dirname "$0")/../scripts/match_labels.sh"
failures=0

# check <name> <labels, one per line> <patterns> <expected exit code> <expected output>
check() {
  local name="$1" labels="$2" patterns="$3" want_code="$4" want_out="$5" out code
  out=$(printf '%s' "$labels" | bash "$script" "$patterns")
  code=$?
  if [ "$code" = "$want_code" ] && [ "$out" = "$want_out" ]; then
    echo "ok   - $name"
  else
    echo "FAIL - $name"
    echo "       exit $code (want $want_code), output '${out//$'\n'/|}' (want '${want_out//$'\n'/|}')"
    failures=$((failures + 1))
  fi
}

nl=$'\n'

check "no labels, any label counts"        ""                              ""                1 ""
check "one label, any label counts"        "bug"                           ""                0 "bug"
check "several labels, any label counts"   "bug${nl}pr/feature"            ""                0 "bug${nl}pr/feature"
check "label without trailing newline"     "enhancement"                   ""                0 "enhancement"
check "blank lines are ignored"            "${nl}${nl}"                    ""                1 ""
check "whitespace-only pattern = any"      "bug"                           "  "              0 "bug"
check "prefix pattern matches"             "bug${nl}pr/feature"            "pr/*"            0 "pr/feature"
check "prefix pattern, no match"           "bug${nl}documentation"         "pr/*"            1 ""
check "exact pattern"                      "bug${nl}bugfix"                "bug"             0 "bug"
check "case is ignored"                    "PR/Fix"                        "pr/*"            0 "PR/Fix"
check "comma-separated patterns"           "bug${nl}type: fix${nl}other"   "bug, type:*"     0 "bug${nl}type: fix"
check "newline-separated patterns"         "bug${nl}type: fix${nl}other"   "bug${nl}type:*"  0 "bug${nl}type: fix"
check "label with spaces"                  "help wanted"                   "help *"          0 "help wanted"
check "character class"                    "prio-1${nl}prio-x"             "prio-[0-9]"      0 "prio-1"
check "question mark"                      "v1${nl}v10"                    "v?"              0 "v1"
check "label is not expanded as a glob"    "*"                             "bug"             1 ""

if [ "$failures" -gt 0 ]; then
  echo "$failures test(s) failed"
  exit 1
fi
echo "All tests passed"
