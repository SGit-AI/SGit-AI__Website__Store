#!/usr/bin/env python3
"""Promote the Agent Behaviour Policy capability vocabulary into this repository.

WHY THIS IS PROMOTED RATHER THAN WRITTEN. The "describe your agent" page produces
the GRANT — everything an agent can actually do — and hands it to a model session
that turns it into a vault. If this store invented its own words for that, a buyer
would describe their agent in one vocabulary and receive a document written in
another. That is the worst available outcome for a page whose entire job is
producing an input to that document, so the vocabulary is taken rather than made.

WHERE IT COMES FROM. riskmandate.ai's template vaults carry
`data/vocabulary/capabilities.json`, which is itself promoted from the capability
map at what-can-it-do.games.sgit.ai. This script reads it out of a published vault
with a published READ key — which opens a vault and cannot write to it — and
writes it here with its own provenance intact plus ours on top.

RUN IT BY HAND, NOT IN THE BUILD. The build opens no connection. This is the same
arrangement as tools/promote_abp.py: a person runs it, the result is committed,
and the content hash is what makes a silent drift impossible.

    pip install sgit-ai
    python3 tools/promote_capabilities.py

ONE THING IS DROPPED ON THE WAY IN, AND IT IS NAMED. One sentence of the upstream
`rules` array uses a word this site bars absolutely, because this site carries
prices and that word implies a financial product it does not sell. The rule is
kept with the clause removed and the removal recorded in `_elided`, rather than
the whole rule being dropped or the word being quietly tolerated.
"""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "capabilities.json"

# The template vault for one shape, and the read key riskmandate.ai publishes for
# it on that shape's own page. A read key cannot write.
VAULT = "ruj286tr"
READ_KEY = "6042edc39e0bcb1f17af1da0cf9d4ded6f89a7bb6a5394aa9554bb76913a249c"
PATH = "data/vocabulary/capabilities.json"
SOURCE_PAGE = "https://riskmandate.ai/abp-vault-claude-code-web.html"

# Cut the CLAUSE, not the sentence. The first version of this matched from the
# previous full stop, and the rule it was aimed at has none before the barred word
# — so it removed the whole rule while the note beside it said the rest was
# intact. A tool that describes its own output wrongly is worse than one that
# fails, so this cuts at the last clause boundary and refuses to leave nothing.
BARRED_WORD = re.compile(r"\binsurab\w*", re.I)
CLAUSE_END = re.compile(r"\s*(?:\u2014|\u2013|--|,|;|\band\b)\s*$")


def main(sgit="sgit", check_only=False):
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "v"
        r = subprocess.run([sgit, "clone", f"{READ_KEY}:{VAULT}", str(d)],
                           capture_output=True, text=True)
        if r.returncode:
            print(r.stdout + r.stderr, file=sys.stderr)
            return 1
        raw = subprocess.run([sgit, "cat", PATH], cwd=d, capture_output=True, text=True)
        if raw.returncode:
            print(raw.stdout + raw.stderr, file=sys.stderr)
            return 1
        body = raw.stdout

    src = json.loads(body)
    elided = []
    rules = []
    for rule in src.get("rules", []):
        m = BARRED_WORD.search(rule)
        if m:
            head = rule[:m.start()]
            # walk back to the last clause boundary so what is kept reads as a
            # sentence rather than as a sentence with its end bitten off
            while head and not CLAUSE_END.search(head):
                head = head[:-1]
            cut = CLAUSE_END.sub("", head)
            # and again for the punctuation the boundary itself left behind — the
            # first pass removed " and" and left the em-dash it was attached to,
            # which printed as "a loss \u2014."
            cut = cut.strip().rstrip(",;\u2014\u2013- ").strip()
            if not cut:
                print(f"removing the barred clause leaves nothing of rule {rule!r} — it would have "
                      "to be dropped whole, which is a judgement rather than a substitution",
                      file=sys.stderr)
                return 1
            if not cut.endswith("."):
                cut += "."
            elided.append({
                "kept": cut,
                "removed": rule[len(head):].strip(),
                "removed_because":
                    "this clause uses a word this site bars absolutely, because the site carries "
                    "prices and that word implies a financial product it does not sell. The rule "
                    "itself is kept.",
            })
            rule = cut
        rules.append(rule)

    out = {
        "_what_this_is": (
            "The Agent Behaviour Policy capability vocabulary, promoted into this repository so "
            "that a buyer describing their agent here uses the same words as the document they "
            "receive. Nothing in it was written by this store."),
        "_promoted_from": {
            "vault": VAULT,
            "path": PATH,
            "read_with": "a published read key, which opens a vault and cannot write to it",
            "page": SOURCE_PAGE,
            "content_hash": "sha256:" + hashlib.sha256(body.encode()).hexdigest(),
            "by": "tools/promote_capabilities.py, run by hand. The build opens no connection.",
        },
        "_upstream_provenance": src.get("provenance", {}),
        "_elided": elided,
        "grammar": src["grammar"],
        "verbs": src["verbs"],
        "reaches": src["reaches"],
        "families": src["families"],
        "rules": rules,
        "count": src["count"],
        "capabilities": src["capabilities"],
    }
    if len(out["capabilities"]) != out["count"]:
        print(f"count says {out['count']} and there are {len(out['capabilities'])}", file=sys.stderr)
        return 1
    body_out = json.dumps(out, indent=2, ensure_ascii=False) + "\n"
    if check_only:
        # THE ONLY THING THAT CAN TELL A PROMOTED FILE FROM A HAND-EDITED ONE.
        # The gate cannot: the content hash in the file is self-reported, so
        # anybody editing the rows could edit the hash beside them. This re-fetches
        # and compares, and it needs a connection, which is why it is a person's
        # command rather than a build step.
        have = OUT.read_text() if OUT.exists() else ""
        if have == body_out:
            print(f"unchanged: {OUT.relative_to(ROOT)} is what the vault currently holds")
            return 0
        print(f"DRIFTED: {OUT.relative_to(ROOT)} is not what the vault currently holds.",
              file=sys.stderr)
        print("  Either upstream moved, or this file was edited by hand. Re-run without --check "
              "to take the upstream version.", file=sys.stderr)
        return 1
    OUT.write_text(body_out)
    print(f"promoted {out['count']} capabilities -> {OUT.relative_to(ROOT)}")
    print(f"  content hash {out['_promoted_from']['content_hash']}")
    if elided:
        print(f"  {len(elided)} rule(s) had a barred clause removed, recorded in _elided")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--check"]
    raise SystemExit(main(args[0] if args else "sgit", "--check" in sys.argv[1:]))
