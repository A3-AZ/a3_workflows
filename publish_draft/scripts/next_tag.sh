#!/usr/bin/env bash
# Calculates the tag a draft release is published under.
#
# Usage: next_tag.sh <draft-tag> <type> <bump> [identifier] < existing_tags.txt
#   draft-tag   tag of the draft, e.g. v1.2.4. Must start with [v]MAJOR.MINOR.PATCH; a suffix is ignored.
#   type        'release' or 'pre-release'
#   bump        'keep' (the draft's version), 'minor' (x.Y+1.0) or 'major' (X+1.0.0)
#   identifier  pre-release identifier, default 'rc' -> v1.2.4-rc.1, v1.2.4-rc.2, ...
#   stdin       every tag that already exists in the repository, one per line
#
# Prints the new tag. Exit code 1 with an error on stderr if the tag cannot be used.

set -euo pipefail
fail() { echo "$1" >&2; exit 1; }

draft="${1:-}" type="${2:-}" bump="${3:-}" ident="${4:-rc}"

[[ "$draft" =~ ^(v?)([0-9]+)\.([0-9]+)\.([0-9]+) ]] \
  || fail "Draft tag '$draft' does not start with MAJOR.MINOR.PATCH, e.g. v1.2.3."
prefix="${BASH_REMATCH[1]}" major="${BASH_REMATCH[2]}" minor="${BASH_REMATCH[3]}" patch="${BASH_REMATCH[4]}"
# Force base 10, so a part like 08 is not read as octal
major=$((10#$major)) minor=$((10#$minor)) patch=$((10#$patch))

case "$bump" in
  keep) ;;
  minor) minor=$((minor + 1)); patch=0 ;;
  major) major=$((major + 1)); minor=0; patch=0 ;;
  *) fail "Bump must be 'keep', 'minor' or 'major', got '$bump'." ;;
esac
[[ "$ident" =~ ^[0-9A-Za-z-]+$ ]] || fail "Pre-release identifier '$ident' may only contain letters, digits and '-'."

version="$prefix$major.$minor.$patch"
existing=()
while IFS= read -r t || [ -n "$t" ]; do
  [ -n "$t" ] && existing+=("$t")
done

has() { local t; for t in "${existing[@]+"${existing[@]}"}"; do [ "$t" = "$1" ] && return 0; done; return 1; }

has "$version" && fail "$version is already released. Choose a bump, or delete the tag first."

case "$type" in
  release)
    echo "$version"
    ;;
  pre-release)
    last=0
    for t in "${existing[@]+"${existing[@]}"}"; do
      if [[ "$t" == "$version-$ident."* ]]; then
        n="${t#"$version-$ident."}"
        [[ "$n" =~ ^[0-9]+$ ]] && (( 10#$n > last )) && last=$((10#$n))
      fi
    done
    echo "$version-$ident.$((last + 1))"
    ;;
  *) fail "Type must be 'release' or 'pre-release', got '$type'." ;;
esac
