#!/usr/bin/env python3
"""refs.py — read the reference docs and briefs this site is built against.

    tools/refs.py fetch            # pull every source in data/refs.yml into refs/
    tools/refs.py fetch guidance   # …or just the ones you name
    tools/refs.py list             # what is cached, how big, when, and its sha256
    tools/refs.py read guidance    # print a cached document (fetching if missing)
    tools/refs.py grep "read key"  # search the cache, with the id and line number
    tools/refs.py links guidance   # the .md links inside it that the manifest lacks
    tools/refs.py check            # re-fetch and diff against the recorded hashes

WHY A SCRIPT AND NOT A BOOKMARK

The guidance at sgit.ai is load-bearing here: the version convention this repo
follows, the read-key rule its secret scan implements, "anything rendered stays
one click from the bytes it was rendered from" — which is why every page of this
site has a `.md` twin — and "state the gap rather than papering over it", which is
the whole reason /ledger/ exists. Guidance that is only ever read once, by whoever
happened to be there, is guidance that gets quietly dropped by the next person.

So it is fetched, hashed and dated, and `check` says when upstream moved.

WHAT IT FETCHES

The `.md` twin, never the HTML. sgit.ai generates both from the same content and
says so on every page: "this file is generated from the same content as the page,
so the two cannot drift." Scraping the rendered page would be re-deriving what is
already published — rung 0 of that site's own what-not-to-build ladder.

WHERE IT PUTS IT

`refs/`, which is gitignored, and which is NOT under docs/. That second part is
not tidiness. Hard rule 1 bars one word from every byte this site publishes, and
11 of the 19 documents in this repository's own pack carry it. Fetched text is not
ours to edit, so it never enters the build tree and the gate never has to hold an
opinion about it. Nothing in refs/ is published, and nothing here writes to docs/.

No dependencies, same as the rest of this repository. urllib honours https_proxy
and the system trust store, which is all a fetch of a public markdown file needs.
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from build import yaml_load  # noqa: E402  — one YAML subset in this repository, not two

MANIFEST = yaml_load((ROOT / "data" / "refs.yml").read_text())
SOURCES = MANIFEST["sources"]
BY_ID = {s["id"]: s for s in SOURCES}
CACHE = ROOT / MANIFEST["meta"].get("cache", "refs")
INDEX = CACHE / "index.json"
UA = "store.sgit.ai refs.py (+https://store.sgit.ai/) - fetches published .md twins"
TIMEOUT = 30


# ----------------------------------------------------------------- the fetch ---
def fetch_one(url, attempts=4):
    """Fetch a URL as text. Retries on transport failure with the estate's usual
    backoff, because a reference fetch that fails once should not look like a
    document that changed."""
    last = None
    for n in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/plain, text/markdown, */*"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            # A 404 is an answer, not a transport failure. Retrying it four times
            # with backoff turns "this page moved" into thirty seconds of silence.
            if e.code < 500:
                raise RuntimeError(f"{url}: HTTP {e.code} {e.reason}") from None
            last = e
            if n + 1 < attempts:
                time.sleep(2 ** (n + 1))
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
            if n + 1 < attempts:
                time.sleep(2 ** (n + 1))
    raise RuntimeError(f"{url}: {last}")


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_index():
    if INDEX.exists():
        return json.loads(INDEX.read_text())
    return {"fetched": "", "base": MANIFEST["meta"]["base"], "documents": {}}


def save_index(idx):
    idx["fetched"] = date.today().isoformat()
    CACHE.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(idx, indent=2, sort_keys=True) + "\n")


def path_for(sid):
    return CACHE / f"{sid}.md"


def pick(ids):
    if not ids:
        return SOURCES
    out = []
    for i in ids:
        if i not in BY_ID:
            raise SystemExit(f"refs: no source {i!r}. Known: {', '.join(sorted(BY_ID))}")
        out.append(BY_ID[i])
    return out


# -------------------------------------------------------------- the commands ---
def cmd_fetch(ids):
    idx = load_index()
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / ".gitignore").write_text("# Fetched from elsewhere. Never committed, never published.\n*\n")
    failed = 0
    for s in pick(ids):
        try:
            text = fetch_one(s["url"])
        except RuntimeError as e:
            print(f"  !! {s['id']:<19} {e}")
            failed += 1
            continue
        before = idx["documents"].get(s["id"], {}).get("sha256")
        digest = sha(text)
        path_for(s["id"]).write_text(text)
        idx["documents"][s["id"]] = {
            "url": s["url"], "title": s["title"], "kind": s.get("kind", ""),
            "bytes": len(text.encode("utf-8")), "sha256": digest,
            "fetched": date.today().isoformat(),
            "file": str(path_for(s["id"]).relative_to(ROOT)),
        }
        mark = "  " if before is None else ("~ " if before != digest else "= ")
        print(f"  {mark}{s['id']:<19} {len(text.encode('utf-8')):>7,} B  {digest[:12]}  {s['url']}")
    save_index(idx)
    print(f"\nrefs: {len(idx['documents'])} cached in {CACHE.relative_to(ROOT)}/"
          + (f", {failed} unreachable" if failed else "")
          + "   (= unchanged  ~ changed  blank = new)")
    return 1 if failed else 0


def cmd_list(ids):
    idx = load_index()
    if not idx["documents"]:
        print("refs: nothing cached yet. Run: tools/refs.py fetch")
        return 1
    print(f"{'id':<19} {'kind':<9} {'bytes':>8}  {'sha256':<12}  fetched     title")
    for s in pick(ids):
        d = idx["documents"].get(s["id"])
        if not d:
            print(f"{s['id']:<19} {s.get('kind',''):<9} {'—':>8}  {'—':<12}  —           {s['title']}  (not fetched)")
            continue
        print(f"{s['id']:<19} {d['kind']:<9} {d['bytes']:>8,}  {d['sha256'][:12]}  {d['fetched']}  {d['title']}")
    print(f"\nEvery document is the .md twin of a published page. "
          f"What this repository took from each is in data/refs.yml.")
    return 0


def cmd_read(ids):
    if not ids:
        raise SystemExit("refs: read needs at least one id. Try: tools/refs.py list")
    for s in pick(ids):
        p = path_for(s["id"])
        if not p.exists():
            cmd_fetch([s["id"]])
        print(f"\n{'=' * 78}\n{s['id']}  —  {s['title']}\n{s['url']}\n{'=' * 78}\n")
        print(p.read_text().rstrip())
        print(f"\n--- took from this: {s.get('took', '')}")
    return 0


def cmd_grep(args):
    if not args:
        raise SystemExit("refs: grep needs a pattern")
    rx = re.compile(args[0], re.I)
    hits = 0
    for s in SOURCES:
        p = path_for(s["id"])
        if not p.exists():
            continue
        for n, line in enumerate(p.read_text().splitlines(), 1):
            if rx.search(line):
                hits += 1
                print(f"{s['id']}:{n}: {line.strip()[:160]}")
    if not hits:
        print(f"refs: no match for {args[0]!r} in {len(list(CACHE.glob('*.md')))} cached documents")
    return 0 if hits else 1


def cmd_links(ids):
    """Which markdown links inside a cached document point at something the
    manifest does not carry. The guidance's own instruction is to follow the edge —
    this is the list of edges not yet followed."""
    known = {s["url"] for s in SOURCES}
    for s in pick(ids):
        p = path_for(s["id"])
        if not p.exists():
            print(f"{s['id']}: not fetched")
            continue
        text = p.read_text()
        base = s["url"].rsplit("/", 1)[0]
        found = {}
        for m in re.finditer(r"\[([^\]]{1,80})\]\(([^)\s]+\.md|[^)\s]*llms[^)\s]*\.txt)\)", text):
            label, target = m.group(1), m.group(2)
            if target.startswith("http"):
                url = target
            elif target.startswith("/"):
                url = MANIFEST["meta"]["base"] + target
            else:
                url = os.path.normpath(f"{base}/{target}")
                url = re.sub(r"^(https?:/)([^/])", r"\1/\2", url)
            found.setdefault(url, label)
        new = {u: l for u, l in found.items() if u not in known}
        print(f"\n{s['id']}: {len(found)} markdown links, {len(new)} not in data/refs.yml")
        for u, l in sorted(new.items()):
            print(f"   {u}\n       {l}")
    return 0


def cmd_check(ids):
    """Re-fetch and compare against the recorded hash. Exits non-zero when a
    document moved, because a reference that changed under a decision is a thing
    somebody has to read, not a thing to notice a year later."""
    idx = load_index()
    changed, gone, same = [], [], 0
    for s in pick(ids):
        rec = idx["documents"].get(s["id"])
        try:
            text = fetch_one(s["url"], attempts=2)
        except RuntimeError as e:
            gone.append((s["id"], str(e)))
            continue
        if not rec:
            changed.append((s["id"], "not cached yet"))
        elif sha(text) != rec["sha256"]:
            changed.append((s["id"], f"{rec['sha256'][:12]} → {sha(text)[:12]}, "
                                     f"{rec['bytes']:,} → {len(text.encode('utf-8')):,} B"))
        else:
            same += 1
    for i, why in changed:
        print(f"  CHANGED  {i:<19} {why}")
        print(f"           took: {BY_ID[i].get('took', '')}")
    for i, why in gone:
        print(f"  UNREACHABLE  {i:<19} {why}")
    print(f"\nrefs check: {same} unchanged, {len(changed)} changed, {len(gone)} unreachable")
    if changed:
        print("Run `tools/refs.py fetch` to take the new bytes, then re-read what this "
              "repository took from each (the `took:` line in data/refs.yml).")
    return 1 if changed or gone else 0


COMMANDS = {"fetch": cmd_fetch, "list": cmd_list, "read": cmd_read, "show": cmd_read,
            "grep": cmd_grep, "links": cmd_links, "check": cmd_check}


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd not in COMMANDS:
        print(__doc__)
        return 2
    return COMMANDS[cmd](rest)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except BrokenPipeError:
        # `refs.py grep … | head` is the normal way to use this. Dying with a
        # traceback because the reader stopped reading is noise, not an error.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        raise SystemExit(0)
