#!/usr/bin/env python3
"""Mirror the ChatGPT-made homepage concepts into this repository, with hashes.

WHY MIRROR SOMEBODY ELSE'S PAGES AT ALL. /admin/concepts/ is a critique with
screenshots, and a critique is only checkable if the thing criticised is pinned.
These concepts live on a host this repository does not control and were generated
in a session that will not be re-run. If the page moved or changed, every
screenshot and every quotation on the critique page would become an assertion
about something nobody can look at. So the four pages, the stylesheet, the script
and the four generated images are taken once, hashed, and committed.

WHAT IS AND IS NOT CLAIMED. The mirror is evidence of what was reviewed on the
date recorded, nothing more. The concepts are somebody else's design work, made
by a model in a ChatGPT session at the project lead's direction; they are quoted
and screenshotted here under that description and the critique page says so in
its first sentence. Nothing from them is presented as this store's own.

RUN IT BY HAND, NOT IN THE BUILD. The build opens no connection — same
arrangement as tools/promote_abp.py and tools/promote_capabilities.py.

    python3 tools/promote_concepts.py          # fetch and write the mirror
    python3 tools/promote_concepts.py --check  # re-fetch and diff against it

--check is the point of the hashes: it answers "has the upstream moved since we
reviewed it?" without anybody having to remember what it looked like.
"""
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys
import urllib.request

BASE = "https://riskmandate-store-concepts.diniscruz.chatgpt.site"
BASE_V3 = "https://abp-marketplace-v3.diniscruz.chatgpt.site"
ROOT = pathlib.Path(__file__).resolve().parent.parent
MIRROR = ROOT / "data" / "concepts" / "mirror"
RECORD = ROOT / "data" / "concepts" / "source.json"

# The four pages, and what each one is. The nav calls them 01/02/03 plus a
# review; three are homepage directions and the fourth is the model's own write-up
# of them. Keeping the distinction here stops the critique page from ever
# describing the store as having been given four homepage concepts, which it
# was not.
PAGES = [
    ("index.html",   "marketplace", "concept", "01 Marketplace"),
    ("guided.html",  "guided",      "concept", "02 Guided"),
    ("studio.html",  "studio",      "concept", "03 Studio"),
    ("review.html",  "review",      "review",  "Review & artwork"),
]
ASSETS = ["style.css", "app.js",
          "assets/marketplace.png", "assets/guided.png",
          "assets/studio.png", "assets/infographic.png"]


def fetch(rel, base=None):
    """GET one path. Redirects are followed: the host serves .html at an
    extensionless URL and answers the .html form with a 307."""
    url = f"{base or BASE}/{rel}"
    req = urllib.request.Request(url, headers={"user-agent": "store.sgit.ai concept mirror"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(), r.geturl()


# THE HOST INJECTS A PER-REQUEST SCRIPT, AND IT IS STRIPPED BEFORE HASHING.
# The pages sit behind a CDN that appends a bot-check bootstrap carrying a fresh
# nonce and timestamp on every single response. Hashing that would make --check
# report drift a second after the mirror was taken and would make the recorded
# hashes worthless as a signal that the DESIGN changed. It is infrastructure
# belonging to the host rather than anything the author wrote, so it comes out —
# and the mirror says so, so nobody later wonders why the bytes differ from curl.
CF_INJECT = re.compile(rb"<script>\(function\(\)\{[^<]*?__CF\$cv\$params.*?</script>", re.S)


def clean(body, rel):
    """Remove the CDN's injected bootstrap from an HTML page. Everything else,
    including the author's own app.js, is kept byte for byte."""
    if not rel.endswith(".html"):
        return body, 0
    out, n = CF_INJECT.subn(b"", body)
    return out, n


def digest(b):
    return hashlib.sha256(b).hexdigest()


def main():
    check = "--check" in sys.argv
    if not check:
        MIRROR.mkdir(parents=True, exist_ok=True)
        (MIRROR / "assets").mkdir(exist_ok=True)

    files, drift = [], []
    for rel in [p[0] for p in PAGES] + ASSETS:
        raw, final = fetch(rel)
        body, stripped = clean(raw, rel)
        d = digest(body)
        entry = {"path": rel, "bytes": len(body), "sha256": d, "resolved": final}
        if stripped:
            entry["cdn_script_removed"] = stripped
        files.append(entry)
        dest = MIRROR / rel
        if check:
            if not dest.exists():
                drift.append(f"{rel}: not in the mirror")
            elif digest(dest.read_bytes()) != d:
                drift.append(f"{rel}: upstream has changed since it was mirrored")
        else:
            dest.write_bytes(body)

    if check:
        prev = json.loads(RECORD.read_text())
        was = {f["path"]: f["sha256"] for f in prev["files"]}
        now = {f["path"]: f["sha256"] for f in files}
        for p in sorted(set(was) - set(now)):
            drift.append(f"{p}: mirrored but no longer served")
        if drift:
            print("promote_concepts --check: the upstream has moved.")
            for d in drift:
                print("  " + d)
            return 1
        print(f"promote_concepts --check: all {len(files)} files match the mirror "
              f"taken on {prev['retrieved']}.")
        return 0

    RECORD.write_text(json.dumps({
        "_what_this_is":
            "The ChatGPT-made homepage concepts for this store, mirrored so the "
            "critique at /admin/concepts/ points at something fixed. Three "
            "homepage directions and the model's own review of them, taken from "
            "the URL below on the date below. This is somebody else's design "
            "work, quoted and screenshotted as such.",
        "_how_to_refresh":
            "python3 tools/promote_concepts.py, then node tools/shoot_concepts.mjs "
            "to regenerate every screenshot on the page from the new mirror.",
        "_one_thing_removed":
            "Each mirrored HTML page had the host CDN's injected bot-check "
            "bootstrap removed before hashing, because it carries a fresh nonce "
            "on every response and would otherwise report drift within seconds "
            "of the mirror being taken. Nothing the author wrote was touched; "
            "cdn_script_removed below counts the deletions per file.",
        "source": BASE,
        "made_by": "A ChatGPT session, at the project lead's direction",
        "retrieved": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
        "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "pages": [{"path": p, "id": i, "kind": k, "nav_label": n} for p, i, k, n in PAGES],
        "files": files,
    }, indent=2) + "\n")
    print(f"promote_concepts: {len(files)} files → data/concepts/mirror/")
    for f in files:
        print(f"  {f['sha256'][:12]}  {f['bytes']:>8}  {f['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
