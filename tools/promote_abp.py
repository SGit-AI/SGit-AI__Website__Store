#!/usr/bin/env python3
"""promote_abp.py — pull the Agent Behaviour Policy catalogue from riskmandate.ai
into data/abp-catalogue.json, with its provenance.

    tools/promote_abp.py            # fetch, parse, write, report what moved
    tools/promote_abp.py --check    # fetch and diff only; exit 1 if it moved

WHY PROMOTED AND NOT FETCHED. The catalogue lives on riskmandate.ai and the store
has to show it. No page on this site opens a network connection — that is a build
check, not an intention, and it is most of what the site argues — so the list is
taken at BUILD time, hashed, dated, and written into the repository. A push to
riskmandate.ai is live here on the next build rather than on the next page load.
That is the same thing abp.sgit.ai does to the capability map it was promoted
from, so this copies a method rather than inventing one.

WHAT IT REFUSES TO PROMOTE. Hard rule 1 bars one word from every byte under
docs/, and riskmandate.ai's own positioning is built on that word. Promoted text
goes straight onto a page that carries prices, so this script checks every string
it is about to write and STOPS rather than letting one through to be caught later
by the site gate — a failure at the border is readable, and the same failure three
steps downstream is a mystery in a build log.

No dependencies, and no HTML parser: the tiles are generated markup with a stable
shape, and a regex that breaks loudly on a shape change is better here than a
parser that silently returns nothing.
"""
import hashlib
import html as htmllib
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "abp-catalogue.json"
SOURCE = "https://riskmandate.ai/abp-vaults.html"
UA = "store.sgit.ai promote_abp.py (+https://store.sgit.ai/)"

# The site gate's rules, applied at the border. Kept in sync with check_site.py by
# being short enough to read: if one of these ever diverges, the site gate is the
# one that decides and this script is the one that should have caught it first.
BARRED = [
    (re.compile(r"insur", re.I), "hard rule 1 — the barred word"),
    (re.compile(r"\bcertif", re.I), "hard rule 2 — conformity-marking language"),
    (re.compile(r"\bzero[- ]knowledge\b", re.I), "hard rule 12 — the contested encryption term"),
    (re.compile(r"\bagentic\b", re.I), "hard rule 12 — the contested autonomy term"),
    (re.compile(r"\bmemory\b", re.I), "hard rule 12 — the contested durability term"),
    (re.compile(r"mandate to operate", re.I), "the open naming collision"),
]

TILE = re.compile(
    r'<article class="ab-tile on">\s*'
    r'<span class="ab-glyph ([a-z0-9-]+)"[^>]*>([^<]{1,6})</span>\s*'
    r'<div class="ab-tilebody">\s*'
    r'<h3><a href="(abp-vault-[a-z0-9-]+\.html)">([^<]+)</a>.*?</h3>\s*'
    r'<p>(.*?)</p>\s*'
    # NOT [^<]*: six of the fifteen tiles carry an <em>N open questions</em>
    # inside this span, and the first pattern written here silently matched
    # only the nine that did not.
    r'<span class="ab-tilecounts">(.*?)</span>'
    r'<rm-abp-mini data-vault="([a-z0-9-]+)"></rm-abp-mini>',
    re.S)

COUNTS = re.compile(r"(\d+) it can do\s*·\s*(\d+) wanted\s*·\s*(\d+) not\s*·\s*(\d+) unbounded")
OPEN_Q = re.compile(r"(\d+) open question")
# The page states how many shapes it is publishing. Parsing fewer than it claims is
# a parser failure, not a smaller catalogue.
DECLARED = re.compile(r'<span class="tag">Available now\s*·\s*(\d+)</span>')


def text(s):
    return htmllib.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def guard(entries):
    """Nothing carrying a barred word is written. The offending row is named, and
    so is the rule, because the fix is a ruling somebody makes and not an edit."""
    bad = []
    for e in entries:
        for field in ("title", "summary", "glyph"):
            for rx, why in BARRED:
                m = rx.search(e[field] or "")
                if m:
                    bad.append(f"  {e['slug']}.{field}: {why} — …{e[field][max(0, m.start()-40):m.start()+40]}…")
    if bad:
        print("promote_abp: REFUSING to promote. The source carries text this site may not "
              "publish:\n" + "\n".join(bad) +
              "\n\nThis is a border check, not a bug. Either the row is rewritten upstream, or "
              "this store carries its own wording for it — which is a decision, not an edit.",
              file=sys.stderr)
        raise SystemExit(2)


def parse(page):
    entries = []
    for glyph_cls, glyph, href, title, summary, counts, slug in TILE.findall(page):
        c = COUNTS.search(counts)
        entries.append({
            "slug": slug,
            "title": text(title),
            "summary": text(summary),
            "glyph": text(glyph),
            "family": glyph_cls,
            "url": "https://riskmandate.ai/" + href,
            "counts": ({"grant": int(c.group(1)), "wanted": int(c.group(2)),
                        "excess": int(c.group(3)), "unbounded": int(c.group(4))}
                       if c else None),
            # Present on the shapes derived from a vendor's published page rather
            # than measured on the thing itself. It is product information, not a
            # defect: it says how much of this template is still a question.
            "open_questions": (int(q.group(1)) if (q := OPEN_Q.search(counts)) else 0),
        })
    declared = DECLARED.search(page)
    if not declared:
        raise SystemExit("promote_abp: the source no longer states how many shapes it publishes, "
                         "so there is nothing to check the parse against. Fix the pattern.")
    want = int(declared.group(1))
    if len(entries) != want:
        raise SystemExit(
            f"promote_abp: the page says it publishes {want} shapes and this parsed "
            f"{len(entries)}. The tile markup changed shape. Fix the pattern rather than "
            "shipping a short list — a catalogue that quietly loses rows is worse than one "
            "that fails, and this check exists because it already happened once.")
    return entries


def build():
    page = fetch(SOURCE)
    entries = parse(page)
    guard(entries)
    return {
        "type": "store/abp-catalogue/v1",
        "_what_this_is": "The Agent Behaviour Policy template vaults published at riskmandate.ai, "
                         "promoted into this repository at build time because no page on this site "
                         "opens a network connection. Refresh with tools/promote_abp.py.",
        "source": SOURCE,
        "retrieved": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "content_hash": "sha256:" + hashlib.sha256(page.encode("utf-8")).hexdigest(),
        "count": len(entries),
        "shapes": entries,
    }


def main(argv):
    fresh = build()
    old = json.loads(OUT.read_text()) if OUT.exists() else None
    same = old and old.get("shapes") == fresh["shapes"]

    if "--check" in argv:
        if not old:
            print("promote_abp: nothing promoted yet")
            return 1
        print(f"promote_abp --check: {'unchanged' if same else 'CHANGED'} "
              f"({len(fresh['shapes'])} shapes upstream, {len(old['shapes'])} here)")
        if not same:
            up = {s["slug"] for s in fresh["shapes"]}
            here = {s["slug"] for s in old["shapes"]}
            for s in sorted(up - here):
                print(f"  + {s}")
            for s in sorted(here - up):
                print(f"  - {s}")
        return 0 if same else 1

    if same:
        # The retrieval time still moves; the catalogue does not. Rewriting the file
        # for a timestamp alone makes `build.py --check` dirty on every run.
        print(f"promote_abp: unchanged, {len(fresh['shapes'])} shapes. File left alone.")
        return 0
    OUT.write_text(json.dumps(fresh, indent=2) + "\n")
    print(f"promote_abp: {len(fresh['shapes'])} shapes → {OUT.relative_to(ROOT)}")
    for s in fresh["shapes"]:
        c = s["counts"] or {}
        print(f"  {s['slug']:<34} {s['glyph']:<3} "
              f"{c.get('grant','?'):>3} can · {c.get('wanted','?'):>2} wanted · "
              f"{c.get('unbounded','?'):>2} unbounded  {s['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
