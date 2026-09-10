#!/usr/bin/env bash
# Syntax-check every piece of JavaScript this site ships: the files under assets/,
# AND the inline <script> blocks in every built page.
#
# The inline half exists because of a real escape. /estate/ shipped a picker script
# with a blank line in it; build.py's raw-html branch stopped at that blank line and
# rendered the rest as markdown, injecting <p> tags mid-function and escaping
# `i < all.length` to `i &lt; all.length`. The page was broken and this script still
# said "all scripts parse" — because it only ever read assets/*.js, while the code
# that takes a credential and opens a frame lives inline in the page. A gate that
# cannot see where the code lives is not a gate.
#
# build.py now passes <script> blocks through verbatim. This is what checks that it
# did, on every build, rather than trusting it.
set -euo pipefail
cd "$(dirname "$0")/.."
shopt -s nullglob
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
fail=0
found=0

for f in assets/*.js docs/assets/*.js; do
  found=$((found+1))
  node --check "$f" || { echo "check-js: $f does not parse"; fail=1; }
done

pages=$(find docs -name '*.html' | sort)
if [ -n "$pages" ]; then
  # shellcheck disable=SC2086
  while IFS= read -r blk; do
    [ -n "$blk" ] || continue
    found=$((found+1))
    node --check "$blk" || { echo "check-js: inline block $blk does not parse"; fail=1; }
  done < <(python3 tools/extract_inline_js.py "$tmp" $pages)
fi

if [ "$fail" = 0 ]; then
  echo "check-js: all $found script(s) parse — files and inline blocks."
fi
exit $fail
