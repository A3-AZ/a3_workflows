#!/usr/bin/env bash
# Unit tests for scripts/next_tag.sh. Run: bash publish_draft/tests/test_next_tag.sh

set -uo pipefail
script="$(dirname "$0")/../scripts/next_tag.sh"
failures=0

# check <name> <existing tags, one per line> <expected exit code> <expected output> <args...>
check() {
  local name="$1" tags="$2" want_code="$3" want_out="$4" out code
  shift 4
  out=$(printf '%s' "$tags" | bash "$script" "$@" 2>/dev/null)
  code=$?
  if [ "$code" = "$want_code" ] && [ "$out" = "$want_out" ]; then
    echo "ok   - $name"
  else
    echo "FAIL - $name"
    echo "       exit $code (want $want_code), output '$out' (want '$want_out')"
    failures=$((failures + 1))
  fi
}

nl=$'\n'
old="v1.2.3"

check "release, keep"                     "$old"                                   0 "v1.2.4"       v1.2.4 release keep
check "release, minor"                    "$old"                                   0 "v1.3.0"       v1.2.4 release minor
check "release, major"                    "$old"                                   0 "v2.0.0"       v1.2.4 release major
check "release, no tags at all"           ""                                       0 "v0.0.1"       v0.0.1 release keep
check "release after its pre-releases"    "$old${nl}v1.2.4-rc.1${nl}v1.2.4-rc.2"   0 "v1.2.4"       v1.2.4 release keep
check "release, tag without v"            "1.2.3"                                  0 "1.2.4"        1.2.4 release keep
check "release, suffix of draft ignored"  "$old"                                   0 "v1.2.4"       v1.2.4-rc.7 release keep
check "release, leading zeros"            ""                                       0 "v1.9.0"       v1.08.09 release minor
check "release, version already exists"   "$old${nl}v1.2.4"                        1 ""             v1.2.4 release keep
check "first pre-release"                 "$old"                                   0 "v1.2.4-rc.1"  v1.2.4 pre-release keep
check "next pre-release"                  "$old${nl}v1.2.4-rc.1${nl}v1.2.4-rc.2"   0 "v1.2.4-rc.3"  v1.2.4 pre-release keep
check "pre-release numbers sort numeric"  "v1.2.4-rc.9${nl}v1.2.4-rc.10"           0 "v1.2.4-rc.11" v1.2.4 pre-release keep
check "pre-release of other version"      "v1.2.4-rc.3"                            0 "v1.3.0-rc.1"  v1.2.4 pre-release minor
check "pre-release, major"                "$old"                                   0 "v2.0.0-rc.1"  v1.2.4 pre-release major
check "pre-release, other identifier"     "v1.2.4-rc.2"                            0 "v1.2.4-beta.1" v1.2.4 pre-release keep beta
check "pre-release, foreign suffix"       "v1.2.4-rc.x${nl}v1.2.4-rc1"             0 "v1.2.4-rc.1"  v1.2.4 pre-release keep
check "pre-release, version released"     "v1.2.4"                                 1 ""             v1.2.4 pre-release keep
check "invalid draft tag"                 ""                                       1 ""             next release keep
check "invalid type"                      ""                                       1 ""             v1.2.4 stable keep
check "invalid bump"                      ""                                       1 ""             v1.2.4 release patch
check "invalid identifier"                ""                                       1 ""             v1.2.4 pre-release keep "r c"

if [ "$failures" -gt 0 ]; then
  echo "$failures test(s) failed"
  exit 1
fi
echo "All tests passed"
