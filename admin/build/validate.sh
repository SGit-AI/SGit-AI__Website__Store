#!/usr/bin/env bash
# The pre-release gate, in one command — the same place and name as on every
# sibling site in this estate, so that moving between them means learning nothing.
#
# Order matters: build first (everything downstream reads docs/), then the checks
# that can stop a release. Any failure exits non-zero: no tag, no publish.
#
#   1. the build is reproducible  — docs/ must match content/
#   2. the site gate              — version agreement, internal links, canonical
#                                   host vs CNAME, the key tripwire, and the
#                                   fifteen hard rules of the store pack, run as
#                                   machine assertions rather than trusted
#   3. the secret scan            — API keys, vault keys, private keys, whole tree
#   4. the scripts                — every inline <script> and asset .js parses
#
# The site gate is the long one here, and deliberately so. This is the first site
# in the estate that carries a price, and a page with a price is an offer. The
# rules that constrain it are in the pack at /dev-packs/store/; check_site.py is
# where each of them stops being advice.
set -euo pipefail
cd "$(dirname "$0")/../.."

echo "── 1/4  build"
python3 build.py --check

echo "── 2/4  site gate"
python3 tools/check_site.py

echo "── 3/4  secrets"
tools/secret-scan.sh

echo "── 4/4  scripts"
tools/check-js.sh

echo
echo "validate: OK — $(cat admin/build/version.txt) on $(cat docs/CNAME)"
