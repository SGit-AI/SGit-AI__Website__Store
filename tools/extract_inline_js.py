#!/usr/bin/env python3
"""Write every inline <script> block in the given HTML files to a directory, one
file per block, and print the paths.

WHY THIS EXISTS. /estate/ shipped a picker script with a blank line in it.
build.py's raw-html branch stopped at that blank line and rendered the remainder as
markdown: `<p>` tags injected into the middle of a function and `i < all.length`
escaped to `i &lt; all.length`. The page was broken, and tools/check-js.sh reported
"all scripts parse" — because it only ever read `assets/*.js`, and the code that
actually took a credential and opened a frame lived inline in the page.

A gate that cannot see where the code lives is not a gate. So the blocks are
extracted to real files here, and `node --check` is run over each one, which also
gives a usable line number when something is wrong.

Blocks with a `src=` attribute are skipped: those are files, and check-js.sh reads
assets/*.js directly.

Blocks with a non-JavaScript `type=` are skipped too, and that exclusion is narrow
on purpose: only the data types below, never an unrecognised one. A <script> whose
type says `application/json` is a DATA ISLAND — the /lab/ pages ship their option
model that way — and `node --check` on a bare object literal fails at the first
colon, which would report a broken page that is not broken. Anything else with a
type attribute is still checked, because the failure this file exists to catch was
a script nobody thought to look at."""
import re
import sys
from pathlib import Path

BLOCK = re.compile(r"<script(?![^>]*\bsrc=)([^>]*)>(.*?)</script>", re.S | re.I)
# Script types that are data rather than code. A block carrying one of these is not
# JavaScript and is not parsed as JavaScript.
DATA_TYPES = ("application/json", "application/ld+json", "importmap", "speculationrules")


def main(argv):
    if len(argv) < 3:
        sys.exit("usage: extract_inline_js.py <out-dir> <html> [html…]")
    out = Path(argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for path in argv[2:]:
        p = Path(path)
        for n, m in enumerate(BLOCK.finditer(p.read_text(encoding="utf-8")), 1):
            attrs, body = m.group(1), m.group(2)
            ty = re.search(r'\btype="([^"]*)"', attrs, re.I)
            if ty and ty.group(1).strip().lower() in DATA_TYPES:
                continue
            if not body.strip():
                continue
            f = out / f"{str(p).replace('/', '_')}.{n}.js"
            f.write_text(body, encoding="utf-8")
            print(f)


if __name__ == "__main__":
    main(sys.argv)
