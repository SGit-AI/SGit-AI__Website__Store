#!/usr/bin/env python3
"""Mirror the chosen v3 design — "01 / ABP first" — into this repository.

WHY THIS IS MIRRORED RATHER THAN JUST LOOKED AT. /next/ is a re-implementation of
somebody else's design, and the only honest way to say "this is their design, built
here" is to pin what theirs WAS on the day it was built from. The v2 concepts were
mirrored for a critique; this is mirrored for a build, which is a stronger reason:
six weeks from now the question "did we implement it faithfully, or did we drift?"
has an answer nobody has to remember.

WHAT IS TAKEN. The chosen direction's page, the two stylesheets, the data and app
layers, and the four product renders. The two unchosen directions and the model's
own lab pages are NOT taken: they are not being built from, and mirroring them
would imply they were under consideration when the choice is already made.

THE ARTWORK IS RE-ENCODED, NOT COPIED. The four renders are 1.9–2.1MB of PNG each.
Re-encoding them to JPEG happens in tools/shoot_v3.mjs, which has a browser; this
records the originals' hashes so the re-encode can always be checked against what
arrived.

    python3 tools/promote_v3.py          # fetch and write the mirror
    python3 tools/promote_v3.py --check  # re-fetch and diff against it
"""
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys
import urllib.request

BASE = "https://abp-marketplace-v3.diniscruz.chatgpt.site"
ROOT = pathlib.Path(__file__).resolve().parent.parent
MIRROR = ROOT / "data" / "next" / "mirror"
RECORD = ROOT / "data" / "next" / "source.json"

# The chosen direction and everything it is built out of. `index.html` IS
# "01 / ABP first" — the other two directions live at vault-first.html and
# use-first.html and are deliberately not mirrored.
FILES = [
    ("index.html", "the chosen direction: 01 / ABP first"),
    ("style.css", "the base stylesheet"),
    ("marketplace.css", "the marketplace layer"),
    ("data.js", "the four levels and the vault file list, as data"),
    ("app.js", "level selection, edition switching, file explorer"),
    ("products.html", "the product page, with the level switcher"),
    ("assets/marketplace.png", "ABP Pack artwork"),
    ("assets/vault-marketplace.png", "ABP Vault artwork"),
    ("assets/toolkit-marketplace.png", "ABP Tailored artwork"),
    ("assets/reviewed-marketplace.png", "ABP Reviewed artwork"),
]

# The same per-request CDN bootstrap as the v2 mirror. It carries a fresh nonce on
# every response and would report drift within seconds of the mirror being taken.
CF_INJECT = re.compile(rb"<script>\(function\(\)\{[^<]*?__CF\$cv\$params.*?</script>", re.S)


def fetch(rel):
    req = urllib.request.Request(f"{BASE}/{rel}",
                                 headers={"user-agent": "store.sgit.ai v3 mirror"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def clean(body, rel):
    if not rel.endswith(".html"):
        return body, 0
    return CF_INJECT.subn(b"", body)


def main():
    check = "--check" in sys.argv
    if not check:
        (MIRROR / "assets").mkdir(parents=True, exist_ok=True)

    files, drift = [], []
    for rel, what in FILES:
        raw = fetch(rel)
        body, stripped = clean(raw, rel)
        entry = {"path": rel, "what": what, "bytes": len(body),
                 "sha256": hashlib.sha256(body).hexdigest()}
        if stripped:
            entry["cdn_script_removed"] = stripped
        files.append(entry)
        dest = MIRROR / rel
        if check:
            if not dest.exists():
                drift.append(f"{rel}: not in the mirror")
            elif hashlib.sha256(dest.read_bytes()).hexdigest() != entry["sha256"]:
                drift.append(f"{rel}: upstream has changed since it was mirrored")
        else:
            dest.write_bytes(body)

    if check:
        if drift:
            print("promote_v3 --check: the upstream has moved.")
            for d in drift:
                print("  " + d)
            return 1
        prev = json.loads(RECORD.read_text())
        print(f"promote_v3 --check: all {len(files)} files match the mirror "
              f"taken on {prev['retrieved']}.")
        return 0

    RECORD.write_text(json.dumps({
        "_what_this_is":
            "The v3 design this store's /next/ pages are built from: the chosen "
            "direction \"01 / ABP first\", its stylesheets, its data and app layers, "
            "and the four product renders. Somebody else's design work, made by a "
            "ChatGPT session at the project lead's direction and pinned here so the "
            "question \"did we build it faithfully\" has an answer.",
        "_what_is_not_taken":
            "The two unchosen directions (vault-first, use-first) and the model's own "
            "lab and notes pages. The choice is made; mirroring the alternatives would "
            "imply it is not.",
        "_one_thing_removed":
            "Each mirrored HTML page had the host CDN's injected bot-check bootstrap "
            "removed before hashing — it carries a fresh nonce on every response and "
            "would report drift within seconds of the mirror being taken.",
        "_one_thing_not_carried_across":
            "The v3 pages carry a mission line under the heading WHY RISKMANDATE "
            "EXISTS that uses a word this store bars absolutely, on every page that "
            "carries a price. The mirror keeps their file intact — it is their page — "
            "and /next/ does not reproduce that section. It is recorded as a ruling "
            "for the project lead rather than silently dropped.",
        "source": BASE,
        "direction": "01 / ABP first",
        "made_by": "A ChatGPT session, at the project lead's direction",
        "retrieved": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
        "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "files": files,
    }, indent=2) + "\n")
    print(f"promote_v3: {len(files)} files → data/next/mirror/")
    for f in files:
        print(f"  {f['sha256'][:12]}  {f['bytes']:>8}  {f['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
