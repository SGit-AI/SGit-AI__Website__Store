#!/usr/bin/env python3
"""Write every inline <script type="application/json"> data island to a directory,
one file per block, and print the paths.

The twin of extract_inline_js.py. That one skips these blocks because `node
--check` on a bare object literal fails at the first colon; this one hands them to
a JSON parser instead, so a data island still gets checked rather than falling
through the gap between the two tools. The /lab/ pages ship their whole option
model this way, and a page whose model does not parse renders a configurator with
nothing in it."""
import re
import sys
from pathlib import Path

BLOCK = re.compile(
    r'<script(?![^>]*\bsrc=)[^>]*\btype="application/(?:ld\+)?json"[^>]*>(.*?)</script>',
    re.S | re.I)


def main(argv):
    if len(argv) < 3:
        sys.exit("usage: extract_inline_json.py <out-dir> <html> [html…]")
    out = Path(argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for path in argv[2:]:
        p = Path(path)
        for n, m in enumerate(BLOCK.finditer(p.read_text(encoding="utf-8")), 1):
            body = m.group(1)
            if not body.strip():
                continue
            f = out / f"{str(p).replace('/', '_')}.{n}.json"
            f.write_text(body, encoding="utf-8")
            print(f)


if __name__ == "__main__":
    main(sys.argv)
