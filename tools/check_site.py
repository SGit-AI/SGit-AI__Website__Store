#!/usr/bin/env python3
"""check_site.py — the acceptance assertions for store.sgit.ai.

Runs over the BUILT output in docs/, not over the sources, because what ships is
the built output and a rule that checks the source checks the wrong thing.

Half of what is below is the estate's usual gate: the version agrees everywhere,
internal links resolve, no URL is root-absolute, the canonical host matches CNAME,
every page has a markdown twin, no page contacts anything.

The other half exists because this is the first site in the estate that carries a
price, and a page with a price is an offer rather than an argument. The fifteen
hard rules of the store pack constrain what an offer page may say. They are
written down in a document nobody is obliged to read, so each one that a script
can check is checked here, and each check names the rule it enforces.

Three of them are absolute and worth stating plainly, because they are the ones
somebody will eventually try to relax:

  * hard rule 1  — the word this site may never print appears NOWHERE in docs/,
                   not in copy, not in a heading, not in a filename, not in an
                   attribute. The rule argues its own absoluteness: a positioning
                   phrase is a claim, but a priced checkout is an offer, and every
                   page here carries a price.
  * hard rule 13 — the sentence about what a provider can read is not printable
                   until six questions about what leaks are answered. A regulator
                   acted on exactly this claim in November 2020 and the settlement
                   ran for twenty years.
  * the collision — one phrase in this vocabulary was ruled on 8 September to
                   block any public page until a naming collision is closed. It is
                   not closed.

A check that only fires on the source, or only on a page somebody remembered to
list, is not a gate. Every one below walks all of docs/.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs"
DOMAIN = "store.sgit.ai"

failures = []
notes = []


def fail(msg):
    failures.append(msg)


def note(msg):
    notes.append(msg)


def pages():
    return sorted(OUT.rglob("index.html"))


def texts():
    """Every built file that a reader or a crawler can reach, as (rel, text)."""
    for p in sorted(OUT.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".zip", ".ico"}:
            continue
        rel = str(p.relative_to(OUT)).replace(os.sep, "/")
        try:
            yield rel, p.read_text()
        except UnicodeDecodeError:
            continue


def offer_block(oid, src=None):
    """One record out of data/offers.yml, as raw text. Nothing in this file imports
    build.py: a gate that asks the thing it is checking what it did is not a gate,
    so the sources are read the way a stranger would read them."""
    src = (ROOT / "data" / "offers.yml").read_text() if src is None else src
    m = re.search(rf"(?ms)^- id: {re.escape(oid)}\n(.*?)(?=^- id: |\Z)", src)
    return m.group(1) if m else ""


def yml_records(name, *fields):
    """Every `- id:` record in one of the one-line-per-value data files, as dicts of
    strings. Enough to check a table against a ruling and no more."""
    src = (ROOT / "data" / name).read_text()
    out = []
    for block in re.split(r"(?m)^- id: ", src)[1:]:
        rec = {"id": block.split("\n", 1)[0].strip()}
        for k in fields:
            m = re.search(rf'(?m)^  {re.escape(k)}: "?(.*?)"?$', block)
            if m:
                rec[k] = m.group(1).strip()
        out.append(rec)
    return out


def shop_model_island():
    """The cart's model as it SHIPS, read out of a built page. The island is the
    artefact a browser gets, so it is the thing worth checking."""
    for p in (OUT / "cart" / "index.html", OUT / "pay" / "index.html",
              OUT / "order" / "index.html"):
        if not p.exists():
            continue
        m = re.search(r'<script type="application/json" id="shop-model">(.*?)</script>',
                      p.read_text(), re.S)
        if m:
            return json.loads(m.group(1))
    return {}


def strip_tags(text):
    text = re.sub(r"(?s)<(script|style)\b.*?</\1>", " ", text)
    return re.sub(r"<[^>]+>", " ", text)


# ------------------------------------------------ hard rule 1: the one word ---
# "The word insurance never appears anywhere on this site." Three standing
# rulings, the newest dated 6 September. The reason is not squeamishness: a
# positioning phrase is a claim, but a priced checkout is an OFFER, and an offer is
# what the regulated perimeter is about. Every page of this site carries a price,
# so there is no page where the word is safe — which is why this check takes no
# allowlist, no per-page exception and no "but it is in a quotation" carve-out.
#
# It is also the check that closed the dev packs area. 11 of the 19 documents in
# the store pack carry the word, one of them in its own title, so republishing them
# raw would fire this on the first build. That is a ruling somebody has to make,
# not a check to loosen.
BARRED_WORD = re.compile(r"insur", re.I)


def check_barred_word():
    for rel, text in texts():
        if BARRED_WORD.search(text) or BARRED_WORD.search(rel):
            m = BARRED_WORD.search(text) or BARRED_WORD.search(rel)
            ctx = text[max(0, m.start() - 60):m.start() + 60].replace("\n", " ") if BARRED_WORD.search(text) else rel
            fail(f"{rel}: hard rule 1 — the barred word appears on a site that carries prices: …{ctx}…")


# ------------------------------- hard rule 2: no conformity-marking language ---
# "Nothing claims to be a compliance assessment, and no form of the word certify
# appears." Presenting this as a compliance assessment would be dishonest, and
# conformity-marking language raises the standard of care beyond ordinary
# negligence — which is a cost with no matching benefit to a buyer.
#
# The negation is not a loophole here. "Nothing here is certified" still puts the
# word on the page, so the copy says what it IS rather than which word it avoids,
# and this check stays absolute.
CERTIFY = re.compile(r"\bcertif", re.I)
COMPLIANCE_ASSESSMENT = re.compile(r"compliance assessment", re.I)


def check_no_conformity_language():
    for rel, text in texts():
        m = CERTIFY.search(text)
        if m:
            ctx = text[max(0, m.start() - 70):m.start() + 70].replace("\n", " ")
            fail(f"{rel}: hard rule 2 — conformity-marking language: …{ctx}…")


def check_compliance_assessment_only_denied():
    """The phrase may appear only where it is being denied."""
    for rel, text in texts():
        flat = strip_tags(text)
        for m in COMPLIANCE_ASSESSMENT.finditer(flat):
            before = flat[max(0, m.start() - 90):m.start()].lower()
            if not re.search(r"\b(not|nothing|never|no|neither|without)\b", before):
                ctx = flat[max(0, m.start() - 80):m.start() + 60].replace("\n", " ")
                fail(f"{rel}: hard rule 2 — 'compliance assessment' not in a denial: …{ctx}…")


# ------------------------------------ hard rule 12: the three contested words ---
# Ruled 10 September, with the evidence in the pack. The primary term is "end to
# end encrypted", the mechanical one is "client side encryption", and "durable" is
# the word for the property that the contested one implies badly.
#
# There is no allowlist, not even for the disclosures page that exists to say the
# words are not used. Two reasons, and the second is the load-bearing one. An
# allowance is a thing that widens: one section becomes one page becomes "in
# context". And a disclosures page that cannot print the word it avoids is the
# rule demonstrating itself — it describes each term precisely enough that anybody
# in the field knows exactly which one is meant, which is what the rule was for.
#
# This is a judgement, not a quotation from the pack. Rule 12's own scope is
# "customer facing copy", and a meta-discussion of vocabulary is arguably not copy.
# If that reading is preferred, this check takes an allowlist and the disclosures
# page names all three — one edit, in one place, on somebody's ruling rather than
# on a builder's preference.
BANNED_WORDS = [
    (re.compile(r"\bzero[- ]knowledge\b", re.I), "the contested encryption term"),
    (re.compile(r"\bmemory\b", re.I), "the contested durability term"),
    (re.compile(r"\bagentic\b", re.I), "the contested autonomy term"),
]
def check_banned_words():
    for rel, text in texts():
        for rx, label in BANNED_WORDS:
            m = rx.search(text)
            if m:
                ctx = text[max(0, m.start() - 60):m.start() + 60].replace("\n", " ")
                fail(f"{rel}: hard rule 12 — {label} appears: …{ctx}…")


# ---------------------- hard rule 13: the sentence that is not printable yet ---
# "Do not print the sentence that the provider cannot read customer data until
# somebody has answered what leaks." It is a factual claim about system
# architecture and it is enforceable: in November 2020 a regulator acted against a
# company for claiming end-to-end encryption while its servers held the keys, and
# the settlement imposed twenty years of third-party assessments.
#
# Six questions decide it — filenames, directory structure, object sizes, commit
# timing, recovery or escrow, support access. None is answered. If any of them
# leaks, the sentence gets a CARVE-OUT rather than a softer adjective, so this
# check looks for the assertion shapes rather than for a keyword: a hedge is
# exactly what it must not accept.
CANNOT_READ = [
    re.compile(r"\bwe (?:cannot|can'?t|are unable to) (?:read|decrypt|see)\b", re.I),
    re.compile(r"\bthat we (?:cannot|can'?t) read\b", re.I),
    re.compile(r"\b(?:cannot|can'?t) (?:read|decrypt|see) your (?:data|files|vault|folder)\b", re.I),
    re.compile(r"\b(?:nobody|no one|not even we|no-one) (?:can|could) (?:read|decrypt)\b", re.I),
    re.compile(r"\bthe provider (?:cannot|can'?t) (?:read|decrypt)\b", re.I),
]


def check_cannot_read_sentence_absent():
    for rel, text in texts():
        flat = strip_tags(text)
        for rx in CANNOT_READ:
            m = rx.search(flat)
            if m:
                ctx = flat[max(0, m.start() - 70):m.start() + 90].replace("\n", " ")
                fail(f"{rel}: hard rule 13 — the unanswered architecture claim is printed: …{ctx}…")


# ------------------------------------------ hard rule 14: tamper, and witness ---
# "Say tamper evident, never tamper proof, and append only as a policy rather than
# a property." A rewritten hash chain verifies against itself; tampering is
# detectable only when another party already holds an older hash. So the claim is
# incomplete without the witness, and this check requires them within sight of each
# other rather than merely both present somewhere on the site.
def check_tamper_wording():
    for rel, text in texts():
        flat = strip_tags(text)
        for m in re.finditer(r"tamper[- ]proof", flat, re.I):
            fail(f"{rel}: hard rule 14 — 'tamper proof' is false; say tamper evident, given a witness")
        for m in re.finditer(r"tamper[- ]evident", flat, re.I):
            window = flat[max(0, m.start() - 200):m.start() + 400].lower()
            if "witness" not in window:
                fail(f"{rel}: hard rule 14 — 'tamper evident' appears without its witness within sight")


# ---------------------------------- the open naming collision (check 5, 8 Sep) ---
# Two phrases in this vocabulary mean opposite things and both are in use. The
# collision was recorded on 8 September, is open on 10 September, and was ruled to
# BLOCK ANY PUBLIC PAGE that uses either phrase without qualification. The
# resolution proposed — retiring the second — is a proposal and not a ruling, so
# the build refuses the second phrase and requires the first, which is the approved
# replacement for the word hard rule 1 bars.
COLLIDING_PHRASE = re.compile(r"mandate to operate", re.I)
APPROVED_PHRASE = "licence to operate"


def check_naming_collision():
    for rel, text in texts():
        if COLLIDING_PHRASE.search(text):
            fail(f"{rel}: the open naming collision (8 Sep) — the colliding phrase must not appear "
                 "on any public page until the collision is closed")
    home = (OUT / "index.html").read_text().lower()
    if APPROVED_PHRASE not in home:
        fail(f"index.html: the approved replacement phrase '{APPROVED_PHRASE}' is missing — it is "
             "what stands in for the word hard rule 1 bars, and it is defined, implemented and running")


# ------------------------------------------- the prices, held against the pack ---
# 01__WHAT-TO-BUILD.md sets four prices and bands the two add-ons. "Do not invent a
# price" is the first thing the pack says about what may not be invented.
#
# These numbers go onto PRINTED CARDS carried to a conference floor. A printed
# price cannot be corrected, so the check is a frozen table rather than a range: to
# move a price you edit this file, in a commit that says so, beside the copy that
# changes with it.
#
# RE-POINTED 15 SEPTEMBER 2026, BY RULING. The four tiers of the 10 September pack
# were replaced by the project lead with four levels of one product: the pack by
# pack downloaded, a working vault, corrected for your situation, and two sessions with a
# professional signing it. The check did not loosen — it was re-pointed at the new
# numbers, in the commit that says so, which is exactly the mechanism this table
# exists for. The previous table is in the history and in the ledger.
EXPECTED_PRICES = {
    "t1": ("£5", 500, 500),
    "t2": ("£50", 5000, 5000),
    "t3": ("£500", 50000, 50000),
    "t4": ("£1,500", 150000, 150000),
    "add-formats": ("By depth band", 0, 0),
    "add-opinion": ("By depth band", 0, 0),
}


def check_prices():
    index = json.loads((OUT / "assets" / "site-index.json").read_text())
    got = {o["id"]: o for o in index["offers"]}
    if set(got) != set(EXPECTED_PRICES):
        fail(f"the offer set changed: expected {sorted(EXPECTED_PRICES)}, built {sorted(got)}")
        return
    for oid, (label, _lo, _hi) in EXPECTED_PRICES.items():
        if got[oid]["price"] != label:
            fail(f"offer {oid}: price is {got[oid]['price']!r}, the pack sets {label!r} — "
                 "a price is not the builder's to invent")
    src = (ROOT / "data" / "offers.yml").read_text()
    for oid, (label, lo, hi) in EXPECTED_PRICES.items():
        block = re.search(rf"(?ms)^- id: {re.escape(oid)}\n(.*?)(?=^- id: |\Z)", src)
        if not block:
            fail(f"offers.yml: no record for {oid}")
            continue
        b = block.group(1)
        for field, want in (("price_min", lo), ("price_max", hi)):
            m = re.search(rf"^\s*{field}: (\d+)$", b, re.M)
            if not m or int(m.group(1)) != want:
                fail(f"offers.yml: {oid}.{field} is {m.group(1) if m else 'missing'}, expected {want}")


def check_delivery_pages():
    """Every offer with a rail has the page its printed code lands on, and the page
    names the id — because the id is the whole contract between a printed code and
    this site, and the host is explicitly assumed to be moveable."""
    index = json.loads((OUT / "assets" / "site-index.json").read_text())
    for o in index["offers"]:
        if o["rail"] == "none":
            if o["delivery"]:
                fail(f"offer {o['id']}: has no rail but claims a delivery page")
            continue
        p = OUT / "d" / o["id"] / "index.html"
        if not p.exists():
            fail(f"offer {o['id']}: no delivery page at /d/{o['id']}/ — a printed code would 404")
            continue
        text = p.read_text()
        if o["id"] not in text:
            fail(f"/d/{o['id']}/: the page does not name its own offer id")
        for needed in ("What arrives", "What this is not"):
            if needed not in text:
                fail(f"/d/{o['id']}/: the page does not say '{needed}' — a delivery page that only "
                     "says what arrives is the half that gets somebody into trouble")


# ------------------------------------------------- the correction, carried on ---
# Brief 2 corrects an earlier claim: professional services listings do NOT retire
# committed spend on the cloud provider, and three independent sources state the
# exclusion. The pack says plainly: do not put the old claim on the page.
#
# So every mention of committed spend on this site has to be within sight of the
# negation. A correction that is only remembered is a correction that comes back.
def check_committed_spend_correction():
    seen = False
    for rel, text in texts():
        flat = strip_tags(text)
        for m in re.finditer(r"committed spend", flat, re.I):
            seen = True
            window = flat[max(0, m.start() - 160):m.start() + 160].lower()
            if not re.search(r"do not draw down|does not draw down|not draw down|exclusion", window):
                ctx = flat[max(0, m.start() - 90):m.start() + 90].replace("\n", " ")
                fail(f"{rel}: the marketplace correction — 'committed spend' without the negation "
                     f"in sight: …{ctx}…")
    if not seen:
        note("the committed-spend correction is not mentioned anywhere; it is only load-bearing "
             "if somebody repeats the old version in a room")


# -------------------------------------- the two rails never meet on one offer ---
# The marketplace seller terms say a seller is not permitted to collect customer
# payment information at any time. A card checkout sitting beside a marketplace
# button, for one transaction, walks straight into that — so the separation is a
# rule and not a layout preference, and the rendered offer cards are where it would
# break first.
def check_rails_not_a_choice():
    for p in pages():
        rel = str(p.relative_to(OUT)).replace(os.sep, "/")
        for card in re.findall(r'(?s)<div class="offer"[^>]*>.*?</div>\s*(?=<div class="offer"|</div>)', p.read_text()):
            flat = strip_tags(card).lower()
            if "marketplace" in flat and ("payment link" in flat or "card" in flat):
                fail(f"{rel}: an offer card presents the marketplace and a card rail together — "
                     "they must never appear as a choice on one transaction")


# ------------------------------------------ hard rule 5: the model disclosure ---
# The transparency article has applied since 2 August 2026 and reaches a
# third-country party whose output is used in the Union. The pack is specific that
# the disclosure belongs on the face of the thing rather than only in a site
# footer, so this check requires it ABOVE <main> — a disclosure found at the bottom
# does the opposite of its job.
def check_model_generated_disclosure():
    for p in pages():
        rel = str(p.relative_to(OUT)).replace(os.sep, "/")
        text = p.read_text()
        i = text.find("Produced with model assistance")
        j = text.find("<main")
        if i < 0:
            fail(f"{rel}: hard rule 5 — no model-generated disclosure")
        elif j >= 0 and i > j:
            fail(f"{rel}: hard rule 5 — the model-generated disclosure is below the fold")


# ------------------------------------ hard rule 7 and 8: triage, and no verdict ---
def check_triage_not_raw_findings():
    """0.388 precision means three findings in five are wrong. If this site ever
    offers findings, it has to be saying triage in the same breath."""
    for rel, text in texts():
        if not rel.endswith((".html", ".md")):
            continue
        flat = strip_tags(text).lower()
        if "raw findings" in flat and "triage" not in flat:
            fail(f"{rel}: hard rule 7 — 'raw findings' appears without 'triage' on the same page")


# -------------------------------------------------- the estate's usual gate ---
def check_version_agreement():
    ver = (ROOT / "admin" / "build" / "version.txt").read_text().strip()
    if not re.fullmatch(r"v\d+\.\d+\.\d+", ver):
        fail(f"version.txt does not carry a vX.Y.Z version: {ver!r}")
        return
    releases = json.loads((ROOT / "data" / "releases.json").read_text())
    if releases["current"] != ver:
        fail(f"releases.json says current is {releases['current']}, version.txt says {ver}")
    known = [r["version"] for r in releases["releases"]]
    if ver not in known:
        fail(f"releases.json has no record for {ver}")
    if len(known) != len(set(known)):
        fail("releases.json records the same version twice")
    # Every release EXCEPT the newest must carry the commit it was built from. A
    # commit cannot contain its own hash, so the newest one's sha lands with the
    # next bump — and bin/bump.py refuses to bump while it is still missing, which
    # is what stops "later" becoming "never".
    for r in releases["releases"][1:]:
        if not re.fullmatch(r"[0-9a-f]{40}", r.get("commit", "")):
            fail(f"{r['version']} has no commit recorded, and it is not the newest release")
    idx = json.loads((OUT / "assets" / "site-index.json").read_text())
    if idx["version"] != ver:
        fail(f"site-index.json says {idx['version']}, version.txt says {ver}")
    if f"site {ver}" not in (OUT / "llms.txt").read_text():
        fail(f"llms.txt does not carry {ver}")
    for p in pages():
        if ver not in p.read_text():
            fail(f"{p.relative_to(OUT)}: does not carry the version badge {ver}")


def check_links():
    have = set()
    for p in OUT.rglob("*"):
        if p.is_file():
            rel = str(p.relative_to(OUT)).replace(os.sep, "/")
            have.add(rel)
            if rel.endswith("/index.html"):
                have.add(rel[: -len("index.html")])
    have.add("")
    for p in pages():
        rel = str(p.relative_to(OUT)).replace(os.sep, "/")
        base = rel.rsplit("/", 1)[0] if "/" in rel else ""
        for m in re.finditer(r'\b(?:href|src)="([^"#:]+)(?:#[^"]*)?"', p.read_text()):
            target = m.group(1)
            if target.startswith(("http://", "https://", "mailto:", "//")):
                continue
            # A query is read by the page, not by the file system. The walkthrough
            # links to /policies/?code=… and this used to call that dead, which is
            # the check being wrong about the site rather than the other way round.
            path_part = target.split("?", 1)[0]
            if not path_part:
                continue                      # a link to this same page with a query
            joined = os.path.normpath(os.path.join(base, path_part))
            if joined == ".":
                joined = ""
            if joined not in have and joined + "/index.html" not in have:
                fail(f"{rel}: dead internal link {target!r}")


def check_relative_urls():
    """The site has to serve from the custom domain, a project path, a local
    directory or a frame with no origin at all. Root-absolute URLs work in exactly
    one of those, and a sibling site spent its first deploy unstyled proving it."""
    for rel, text in texts():
        if not rel.endswith(".html"):
            continue
        for m in re.finditer(r'\b(href|src)="(/[^"]*)"', text):
            fail(f"{rel}: root-absolute URL {m.group(2)!r} — every internal link must be relative")


def check_canonical_host():
    for p in pages():
        rel = str(p.relative_to(OUT)).replace(os.sep, "/")
        m = re.search(r'<link rel="canonical" href="([^"]+)"', p.read_text())
        if not m:
            fail(f"{rel}: no canonical URL")
        elif not m.group(1).startswith(f"https://{DOMAIN}/"):
            fail(f"{rel}: canonical {m.group(1)} is not on {DOMAIN}, which is what CNAME says")


def check_cname():
    cname = (OUT / "CNAME").read_text().strip()
    if cname != DOMAIN:
        fail(f"CNAME is {cname!r}, expected {DOMAIN!r}")


def check_markdown_twins():
    for p in pages():
        if not (p.parent / "index.md").exists():
            fail(f"no markdown twin beside {p.relative_to(OUT)}")


def check_licence_stamp():
    stamp = "Creative Commons Attribution 4.0"
    for p in OUT.rglob("index.md"):
        if stamp not in p.read_text():
            fail(f"{p.relative_to(OUT)}: no licence stamp on the markdown twin")


def check_shortcodes():
    """HTML only. The markdown twins are the SOURCE served beside each page, so a
    shortcode in one is the document as written — that is the point of the twin."""
    for rel, text in texts():
        if not rel.endswith(".html"):
            continue
        for m in re.finditer(r"\{\{[a-z][a-z0-9:_-]*\}\}", text):
            fail(f"{rel}: unexpanded shortcode {m.group(0)}")


def check_no_unrendered_markdown():
    """A real escape on a sibling site: a block stopped rendering halfway and the
    page shipped with literal asterisks in it, and every check still passed. If
    markdown syntax reaches the rendered text, the renderer lost."""
    for p in pages():
        rel = str(p.relative_to(OUT)).replace(os.sep, "/")
        raw = p.read_text()
        flat = strip_tags(raw)
        for pat, what, hay in ((r"\*\*", "bold markers", flat),
                               (r"\]\(", "a markdown link", flat),
                               # On the RAW html, because a stripped table cell of "#"
                               # looks exactly like an unrendered heading and is not one.
                               # No line of real HTML begins with a hash.
                               (r"^#{1,6}\s+\S", "a markdown heading", raw)):
            if re.search(pat, hay, re.M):
                fail(f"{rel}: {what} reached the rendered page — the renderer lost a block")


# THE CLAIM MOVED, AND A CHECK THAT ONLY READ HTML COULD NOT HAVE SEEN IT.
#
# Every page here used to open no connection at all. Review pages now embed the
# vault they review, using the estate's own component, and that is a real
# connection to a real other host. So the claim is narrower and still exact:
#
#   * EVERY PAGE THAT SELLS ANYTHING OPENS NOTHING. No exception, no ruling, no
#     page. That half is the one that matters and it did not move.
#   * A REVIEW PAGE WITH A VAULT embeds it, from ONE host named below, through
#     ONE vendored component, and says so on itself in those words.
#   * Nothing is sent about a reader anywhere on this site: no fetch, no XHR, no
#     beacon, no socket, no analytics, no cookie of ours. That did not move either.
#
# The frame is built by script, so `<iframe` never appears in the markup and the
# old check would have passed a page that embedded anything at all. That is the
# hole this pair closes: one reads the HTML, the other reads the script that makes
# the frame.
EMBED_HOST = "https://dev.vault.sgraph.ai"
EMBED_COMPONENT = "assets/vault-embed.js"


def _may_embed():
    """Review pages that carry a vault, and nothing else."""
    root = ROOT / "data" / "reviews"
    if not root.is_dir():
        return set()
    out = set()
    for f in root.glob("*.json"):
        if f.stem == "_register":
            continue
        if json.loads(f.read_text()).get("vault"):
            out.add(f"admin/reviews/{f.stem}/index.html")
    return out


def check_no_network():
    """No page here opens a connection except the one kind that says it does, and
    the footer says which. This is what makes that a fact rather than a sentence."""
    may = _may_embed()
    for p in pages():
        rel = str(p.relative_to(OUT)).replace(os.sep, "/")
        text = p.read_text()
        for m in re.finditer(r'\b(?:src|srcset|data-src)="(https?:)?//([^"/]+)', text):
            fail(f"{rel}: loads a resource from {m.group(2)} — every byte must come from this domain")
        if "<iframe" in text.lower():
            fail(f"{rel}: contains an iframe in its markup. The vault embed builds its frame at "
                 "runtime through assets/vault-embed.js, which is the only route there is")
        for bad in ("fetch(", "XMLHttpRequest", "navigator.sendBeacon", "new WebSocket"):
            if bad in text:
                fail(f"{rel}: inline script uses {bad} — nothing on this site sends anything")
        if EMBED_COMPONENT in text and rel not in may:
            fail(f"{rel}: loads the vault embed. Only a review page that carries a vault may, and "
                 "a page that sells anything never may")
        if 'class="sgv-uiembed"' in text and rel not in may:
            fail(f"{rel}: carries an embed mount and is not a review page with a vault")
    for js in (OUT / "assets").glob("*.js"):
        text = js.read_text()
        for bad in ("fetch(", "XMLHttpRequest", "navigator.sendBeacon", "new WebSocket"):
            if bad in text:
                fail(f"assets/{js.name}: uses {bad}")
        if "createElement('iframe')" in text.replace('"', "'") and js.name != "vault-embed.js":
            fail(f"assets/{js.name}: builds an iframe. assets/vault-embed.js is the only file on "
                 "this site allowed to, so that there is one place to read and one place to check")


def check_the_embed_is_what_it_says():
    """The one component that opens a connection, held to the four things the page
    claims about it: one host, the key never in a URL, the target origin pinned, and
    replies from anywhere else ignored. Each is a line of code, and each is the
    difference between an embed and a leak."""
    f = OUT / EMBED_COMPONENT
    if not f.exists():
        if _may_embed():
            fail(f"{EMBED_COMPONENT} is missing and a review page expects to embed a vault")
        return
    src = f.read_text()
    # Comments name the upstream this was vendored from, which is a fact about where
    # the file came from and not a host it talks to. The scan reads the code.
    code = re.sub(r"(?s)/\*.*?\*/", " ", src)
    code = re.sub(r"(?m)^\s*//.*$", " ", code)
    for h in sorted(set(re.findall(r"https?://[a-zA-Z0-9.-]+", code))):
        if h != EMBED_HOST:
            fail(f"{EMBED_COMPONENT}: names {h}. One host, pinned, or the frame is a hole rather "
                 "than an embed")
    if f"'{EMBED_HOST}'" not in code and f'"{EMBED_HOST}"' not in code:
        fail(f"{EMBED_COMPONENT}: does not pin {EMBED_HOST} in a constant")
    if "e.origin !== ORIGIN" not in code:
        fail(f"{EMBED_COMPONENT}: does not check the origin of messages it receives. A frame that "
             "believes anybody is a frame that can be impersonated")
    if ", ORIGIN)" not in code:
        fail(f"{EMBED_COMPONENT}: posts the key without pinning targetOrigin. That is the whole "
             "reason the key does not travel in the address")
    for m in re.finditer(r"\.src\s*=\s*([^;]+);", code):
        line = m.group(1)
        if "cred" in line and "#" not in line:
            fail(f"{EMBED_COMPONENT}: puts the credential in a frame src — {line.strip()[:70]}")
    for bad in ("fetch(", "XMLHttpRequest", "navigator.sendBeacon", "new WebSocket"):
        if bad in code:
            fail(f"{EMBED_COMPONENT}: uses {bad}. It opens a frame and sends nothing else")
    for rel in sorted(_may_embed()):
        page = OUT / rel
        if not page.exists():
            continue
        flat = " ".join(strip_tags(page.read_text()).split())
        for needed in ("the one place on this site that opens a connection",
                       "The key does not travel in the address",
                       "still opens nothing at all"):
            if needed not in flat:
                fail(f"{rel}: embeds a vault and does not say {needed!r}. The page that opens the "
                     "connection is the page that owes the reader the account of it")


def check_each_script_loads_once():
    """Two <script> tags for one file is two copies of it running against one
    document, and the second undoes what the first did. It happened: shop.js is on
    every page for the order badge, and the shop pages named it a second time —
    which quietly broke the one branch of the discount bar that nothing had
    clicked yet. A duplicate script tag is a bug that hides until it doesn't."""
    for p in pages():
        rel = str(p.relative_to(OUT)).replace(os.sep, "/")
        srcs = re.findall(r'<script[^>]+src="([^"]+)"', p.read_text())
        seen = [s.rsplit("/", 1)[-1] for s in srcs]
        for name in set(seen):
            if seen.count(name) > 1:
                fail(f"{rel}: loads {name} {seen.count(name)} times. One document, one copy of "
                     "a script — the second run starts from an empty state and undoes the first")


def check_no_credentials_in_output():
    """A second pass over the built site for the shape a payment credential takes.
    tools/secret-scan.sh covers the whole tree; this one covers what SHIPS, because
    the built output is the thing a stranger reads."""
    for rel, text in texts():
        for rx, what in ((r"sk_(?:live|test)_[A-Za-z0-9]{8,}", "a payment secret key"),
                         (r"whsec_[A-Za-z0-9]{8,}", "a webhook signing secret"),
                         (r"sgit_private_(?:vault|write)_", "an sgit vault write key")):
            if re.search(rx, text):
                fail(f"{rel}: {what} is in the BUILT OUTPUT")


def check_pack_area_is_honest():
    """The dev packs area publishes a manifest and holds its documents. If a
    document ever lands in docs/, it has to have come through the five checks —
    and two of those checks are already failing, mechanically, above."""
    pack = json.loads((OUT / "dev-packs" / "pack.json").read_text())
    state = pack["pack"]["state"]
    held = [d for d in pack["documents"] if d["barred_word"] or d["collision"]]
    published = list((OUT / "dev-packs").rglob("*.md"))
    published = [p for p in published if p.name != "index.md"]
    if state == "held" and published:
        fail("dev-packs: documents are published while the pack state is 'held': "
             + ", ".join(str(p.relative_to(OUT)) for p in published[:5]))
    if state != "held" and held:
        fail(f"dev-packs: the pack state is {state!r} but {len(held)} document(s) still carry a "
             "blocker a script can see — hard rule 1 or the open naming collision")
    if pack["pack"]["documents"] != len(pack["documents"]):
        fail("dev-packs: pack.json's document count disagrees with its own document list")
    if not all(re.fullmatch(r"[0-9a-f]{64}", d["sha256"]) for d in pack["documents"]):
        fail("dev-packs: a document in the manifest has no usable sha256 — the manifest is the "
             "only thing this area publishes, so it is the only thing that has to be right")


# ------------------------------------------- the checkout, and where it points ---
# This is the estate's first site with a checkout on it, and a checkout URL is the
# one string here that a stranger's phone will open with a card in their hand. Two
# things are held.
#
# THE HOST. A payment link may point at the payment provider's own checkout hosts
# and nowhere else. A link that can be edited into a redirect through somewhere
# else is a phishing page carrying our prices, and the codes are PRINTED — a card
# handed out on a conference floor cannot be recalled, so the check is a host
# allowlist rather than a review.
#
# THE MODE. How an offer can be paid for is derived from its price, not chosen: a
# fixed-price link carries one price, so only the single-priced tier can ever hold
# a standing one. The table below is frozen for the same reason EXPECTED_PRICES is
# — if a band silently becomes a fixed price, the site starts offering a standing
# link for a number nobody set.
CHECKOUT_HOSTS = ("https://buy.stripe.com/", "https://checkout.stripe.com/")
EXPECTED_CHECKOUT = {
    # Every level is now a single price, so every one of them can hold a standing
    # link. The banded modes and the deposit belonged to the tiers that were
    # replaced: there is no band left to fix and no engagement left to deposit
    # against.
    "t1": "fixed",            # £5
    "t2": "fixed",            # £50
    "t3": "fixed",            # £500
    "t4": "fixed",            # £1,500
    "add-formats": "attached",
    "add-opinion": "none",
}
# The modes that cannot have a link at all, whatever anybody pastes into the file.
# "deposit" is NOT among them: the whole point of that mode is that one part of the
# offer is payable by card even though the offer is not.
NO_LINK_MODES = ("attached", "conversation", "none")

# ---------------------------------------------------------------- the deposit ---
# Tier 4 is the one offer with TWO amounts: an engagement that is invoiced, and a
# deposit against it that is payable by link. The deposit is frozen here exactly as
# the prices are, and for the same reason — it goes onto the same printed cards and
# a printed number cannot be corrected from a conference floor.
#
# Two further things are held, and both are the site's own published arithmetic
# turned into an assertion rather than left as prose:
#
#   1. A deposit must sit BELOW the threshold this site's copy names as the point
#      where a card stops making sense. If it ever rises above it, the page argues
#      against its own checkout in the paragraph next to it.
#   2. A deposit must be smaller than the thing it is a deposit against. A deposit
#      at or above the engagement's floor is not a deposit, it is the price.
# Empty since 15 September 2026. The deposit was against a £5,000 to £10,000
# engagement that the new product line does not carry, so there is nothing left
# for it to be a deposit against. The machinery stays: it is four lines, it is
# tested, and the next offer above the card threshold will want it.
EXPECTED_DEPOSITS = {}
CARD_THRESHOLD = 100000   # £1,000, the number the copy names on /paying/ and /booking/


def check_checkout_links():
    index = json.loads((OUT / "assets" / "site-index.json").read_text())
    offers = {o["id"]: o for o in index["offers"]}
    declared = set()
    for oid, mode in EXPECTED_CHECKOUT.items():
        o = offers.get(oid)
        if not o:
            fail(f"offer {oid}: missing from the built index")
            continue
        if o["checkout_mode"] != mode:
            fail(f"offer {oid}: checkout_mode is {o['checkout_mode']!r}, expected {mode!r} — "
                 "how an offer is paid for follows from its price and is not the builder's to "
                 "change on its own")
        url = o.get("checkout_url")
        if not url:
            continue
        declared.add(url)
        if not url.startswith(CHECKOUT_HOSTS):
            fail(f"offer {oid}: checkout URL {url!r} is not on {' or '.join(CHECKOUT_HOSTS)} — "
                 "a printed code cannot be recalled, so the destination is pinned")
        if (o.get("deposit") is not None) != (mode == "deposit"):
            fail(f"offer {oid}: mode is {mode!r} and deposit is {o.get('deposit')!r} — a deposit "
                 "offer carries a deposit and nothing else does, or the card shows an amount the "
                 "button does not take")
        if mode in NO_LINK_MODES:
            fail(f"offer {oid}: mode {mode!r} carries a checkout URL. "
                 + {"attached": "An add-on is priced against the offer it attaches to and is not bought alone.",
                    "conversation": "Above about £1,000 a card stops making sense; this one goes by invoice.",
                    "none": "There is no code behind this one."}[mode])

    # Nothing may link to a checkout that is not one of the declared ones. A payment
    # destination typed into a paragraph is a payment destination no data file knows
    # about and no check can hold to a price.
    for rel, text in texts():
        for m in re.finditer(r'href="(https?://[^"]*stripe[^"]*)"', text, re.I):
            if m.group(1) not in declared:
                fail(f"{rel}: links to a checkout {m.group(1)!r} that no offer declares — "
                     "every payment destination comes from data/offers.yml or it does not exist")
        for m in re.finditer(r"\bpk_(?:live|test)_[A-Za-z0-9]{8,}", text):
            fail(f"{rel}: a publishable payment key is in the output. Nothing on this site talks "
                 "to a payment API, so there is no reason for one to be here")


# THE RULE THAT MOVED, AND EXACTLY HOW FAR.
#
# Until v0.1.15 there was no form, input, textarea or select anywhere in docs/, full
# stop. A partner's review asked for things that need somewhere to type, and the
# page that answers that review had to be answerable — so the rule moved by ruling,
# and it moved as little as it could.
#
# <form> is still barred EVERYWHERE, because it is the element that submits.
# <input> and <select> are still barred EVERYWHERE, because a card number, a name
# and an address are typed into a single-line field and there is not one on this
# domain. <textarea> is allowed on ONE named page and nowhere else.
#
# Those three sentences are the whole of that change. check_no_network has since
# moved too, for the vault embed on a review page — narrowly, and never for a page
# that sells anything — but not for THIS: a reason box still sends nothing, because
# there is no fetch, no XHR, no beacon and no socket anywhere on this site.
# check_the_typing_
# surface_is_inert below holds the boxes to carrying no name and sitting in no form.
# A rule that loosens without a check loosens again next time nobody is looking.
def typing_surfaces():
    """The pages allowed a reason box: one per review, and nothing else. It was a
    single named file while there was one review; it is derived now because there
    will be a lot of them, and hardcoding a list that grows is how a list goes
    stale. The index page is NOT one — it lists reviews and takes no answers."""
    root = OUT / "admin" / "reviews"
    if not root.is_dir():
        return set()
    return {f"admin/reviews/{d.name}/index.html" for d in sorted(root.iterdir()) if d.is_dir()}


def check_no_forms():
    """Every page here says this site collects nothing from anybody. This is what
    makes that a fact rather than a sentence. A checkout that is a link to somebody
    else's page and a checkout that is a form on ours are different products with
    different obligations, and the difference is one tag."""
    for rel, text in texts():
        if not rel.endswith(".html"):
            continue
        low = text.lower()
        for tag in ("<form", "<input", "<select"):
            if tag in low:
                fail(f"{rel}: contains {tag}> — this site collects nothing, from anybody, ever, "
                     "and these are the tags that would collect it")
        if "<textarea" in low and rel not in typing_surfaces():
            fail(f"{rel}: contains <textarea>. The ruling of v0.1.15 allows a reason box on a "
                 "review page under /admin/reviews/ and on no other page; a typing surface "
                 "anywhere else is a second ruling, not a second file")


def check_the_review_register_is_whole():
    """A review is a moment locked, so the register has to hold. Every record is
    reachable from the index, the index is in date order newest first, every review
    names the version it was taken against, and every screenshot it cites exists.

    The failure this guards is quiet: a review file with no register entry is written
    and never linked, and a register entry with no file is a dead card. Both read as
    fine on the page that does not mention them."""
    root = ROOT / "data" / "reviews"
    if not root.is_dir():
        return
    reg = json.loads((root / "_register.json").read_text())
    ids = reg["order"]
    files = {f.stem for f in root.glob("*.json") if f.stem != "_register"}
    for rid in ids:
        if rid not in files:
            fail(f"the review register names {rid!r} and data/reviews/{rid}.json does not exist")
    for f in sorted(files - set(ids)):
        fail(f"data/reviews/{f}.json is not in the register, so it is written and never linked")

    idx = OUT / "admin" / "reviews" / "index.html"
    if not idx.exists():
        fail("there is no review register page at /admin/reviews/")
        return
    idx_text = idx.read_text()
    seen = re.findall(r'<time datetime="(\d{4}-\d{2}-\d{2})"', idx_text)
    if seen != sorted(seen, reverse=True):
        fail(f"/admin/reviews/: the cards are dated {seen} and are not newest first. The order of "
             "a register is the only thing that makes it a register")
    for rid in ids:
        rv = json.loads((root / f"{rid}.json").read_text())
        if rid not in idx_text:
            fail(f"/admin/reviews/: does not link {rid!r}")
        page = OUT / "admin" / "reviews" / rid / "index.html"
        if not page.exists():
            fail(f"review {rid!r} has no page")
            continue
        if not rv.get("reviewed_version"):
            fail(f"review {rid!r} does not name the version it was taken against. A review that "
                 "does not say what it reviewed is not a moment locked, it is an opinion")
        if rv.get("date") not in rid:
            fail(f"review {rid!r} is dated {rv.get('date')!r}; the id carries the date so the "
                 "directory sorts the same way the register does")
        for src, _cap in rv.get("evidence", []):
            if not (ROOT / "assets" / "reviews" / rid / src).is_file():
                fail(f"review {rid!r} cites evidence {src!r} that does not exist. A review without "
                     "its screenshots is a claim about a moment nobody can check")


def check_the_typing_surface_is_inert():
    """The one page that can be typed into, held to what the ruling actually allowed:
    boxes that carry no name, sit in no form, and belong to a page that — like every
    other page here — opens no connection at all. The claim on the page is that what
    a reader types reaches us only when they paste it to us. This is that claim."""
    surfaces = typing_surfaces()
    if not surfaces:
        fail("no review page exists, so the ruling that moved the no-forms rule is buying nothing")
        return
    for rel in sorted(surfaces):
        page = OUT / rel
        if not page.exists():
            continue
        text = page.read_text()
        boxes = re.findall(r"<textarea\b[^>]*>", text, re.I)
        if not boxes:
            fail(f"{rel}: a review page with no reason box. The verdict register is the reason "
                 "the rule moved at all")
        for b in boxes:
            if re.search(r"\bname\s*=", b, re.I):
                fail(f"{rel}: a box carries a name attribute — {b[:80]}. A name is what a field "
                     "is called when it is SUBMITTED, and nothing here is ever submitted")
            if not re.search(r"\bid\s*=", b, re.I):
                fail(f"{rel}: a box carries no id — {b[:80]}. Without one it cannot be labelled, "
                     "and an unlabelled box is unusable with a screen reader")
        flat = " ".join(strip_tags(text).split())
        for needed in ("no page here opens a network connection",
                       "lives in this browser only"):
            if needed not in flat:
                fail(f"{rel}: does not say {needed!r}. A page that takes typing owes the reader "
                     "the clearest possible account of where it goes")
    js = (OUT / "assets" / "review.js")
    if not js.exists():
        fail("assets/review.js is missing, so the register on /review/ does nothing")
        return
    src = js.read_text()
    for bad in ("fetch(", "XMLHttpRequest", "sendBeacon", "new WebSocket", "<form"):
        if bad in src:
            fail(f"assets/review.js: uses {bad} — the one page that takes typing is the one page "
                 "that must most obviously not send it")


# ------------------------------------------- the buyer groups are a VIEW, not a range ---
# The three groups are a second index over the same six offers. The failure this
# check exists for is specific and it is how offer lists grow without anybody
# deciding to grow them: a buyer page acquires a thing of its own, nobody priced
# it, nobody specified it, and the ledger has no state for it.
#
# So a group may name offer ids and nothing else, every tier belongs to exactly one
# group, and the group set is frozen. The third entry is empty ON PURPOSE — nothing
# on the offer list was built pointing at a startup — and the check requires that
# page to say so, because an empty list that renders as a confident page is worse
# than no page.
EXPECTED_BUYERS = {"agents": ["t1", "t2"], "investors": ["t3", "t4"], "startups": []}
NOT_BUILT_SENTENCE = "Nothing on the offer list was built pointing this way"


def check_buyer_groups():
    index = json.loads((OUT / "assets" / "site-index.json").read_text())
    buyers = {b["id"]: b for b in index["buyers"]}
    offer_ids = {o["id"] for o in index["offers"]}
    if set(buyers) != set(EXPECTED_BUYERS):
        fail(f"the buyer set changed: expected {sorted(EXPECTED_BUYERS)}, built {sorted(buyers)}")
        return
    if [b["id"] for b in sorted(index["buyers"], key=lambda b: b["order"])] != list(EXPECTED_BUYERS):
        fail("the buyers are not in the order the evidence puts them in — the ordering is by "
             "opportunity and it is argued on /audiences/, so it is not a layout preference")

    primary_owner = {}
    for bid, b in buyers.items():
        if b["built_for_them"] != EXPECTED_BUYERS[bid]:
            fail(f"buyer {bid}: built for {b['built_for_them']}, expected {EXPECTED_BUYERS[bid]} — "
                 "a group cannot acquire a tier without somebody deciding that it did")
        named = list(b["built_for_them"]) + list(b["serves_them"]) + list(b["addons"])
        for oid in named + [b["entry"]]:
            if oid not in offer_ids:
                fail(f"buyer {bid}: names offer {oid!r}, which is not on the offer list — a buyer "
                     "page may index offers and may not introduce one")
        if not named:
            fail(f"buyer {bid}: shows no offers at all")
        for oid in b["built_for_them"]:
            if oid in primary_owner:
                fail(f"offer {oid}: built for both {primary_owner[oid]!r} and {bid!r}")
            primary_owner[oid] = bid

        page = OUT / "for" / bid / "index.html"
        if not page.exists():
            fail(f"buyer {bid}: no page at /for/{bid}/")
            continue
        text = page.read_text()
        if bid not in text:
            fail(f"/for/{bid}/: the page does not name its own group id")
        if not b["built_for_them"] and NOT_BUILT_SENTENCE not in strip_tags(text):
            fail(f"/for/{bid}/: nothing on the offer list was built for this buyer and the page "
                 "does not say so. An empty group rendered as a confident page is the exact "
                 "widening the catalogue page exists to prevent")
        if b["built_for_them"] and NOT_BUILT_SENTENCE in strip_tags(text):
            fail(f"/for/{bid}/: says nothing was built for this buyer, but {b['built_for_them']} was")

    for o in index["offers"]:
        if o["tier"] != "add-on" and o["id"] not in primary_owner:
            fail(f"offer {o['id']}: belongs to no buyer group. Every tier is on somebody's page, "
                 "or it is on the offer list for a reason nobody has written down")
        if o["buyer"] != "any" and o["buyer"] not in buyers:
            fail(f"offer {o['id']}: buyer {o['buyer']!r} is not one of the three")


# ------------------------------------------- the lab is a prototype, and says so ---
# Five pages at /lab/ look like a checkout and are not one. That is the single most
# dangerous thing this site could publish — a page carrying prices, option lists and
# a running total, for work that is done by people and that nobody has run yet.
#
# So the marking is a gate rather than a paragraph somebody remembers to keep. Every
# prototype page says what it is above the tool, no lab page carries a payment
# destination, and the bands the configurator prices against may only name offers
# that are on the frozen offer list. A configurator that could name an offer nobody
# priced would be inventing a price with extra steps, which is the first thing the
# pack says may not be invented.
LAB_WARNING = "Nothing on this page can be bought"
EXPECTED_LAB_VIEWS = {"interview", "ladder", "board", "delta", "scenario"}


def lab_pages_built():
    return sorted((OUT / "lab").glob("*/index.html")) if (OUT / "lab").exists() else []


def check_lab_is_marked():
    built = {p.parent.name for p in lab_pages_built()}
    if built != EXPECTED_LAB_VIEWS:
        fail(f"the prototype set changed: expected {sorted(EXPECTED_LAB_VIEWS)}, built {sorted(built)}")
    for p in lab_pages_built():
        rel = f"lab/{p.parent.name}/index.html"
        flat = strip_tags(p.read_text())
        if LAB_WARNING not in flat:
            fail(f"{rel}: does not say {LAB_WARNING!r} — a page that looks like a checkout and "
                 "takes no money has to say which of the two it is before anybody reads on")
        if "has never run" not in flat:
            fail(f"{rel}: does not say the team behind this work has never run. The prototype "
                 "configures consulting that people do, and the state of that team is the "
                 "first thing a buyer is owed")
        for m in re.finditer(r'href="(https?://[^"]*stripe[^"]*)"', p.read_text(), re.I):
            fail(f"{rel}: carries a payment destination {m.group(1)!r}. Nothing in the lab is "
                 "buyable, so nothing in it may link to a checkout")
        if not (p.parent / "index.md").exists():
            fail(f"{rel}: no markdown twin")


def check_lab_bands():
    """Every band the configurator can land in names an offer that exists and is
    priced elsewhere, and the bands ascend. A gap or an overlap here is a price
    that depends on which row was written first."""
    index = json.loads((OUT / "assets" / "site-index.json").read_text())
    offer_ids = {o["id"] for o in index["offers"]}
    src = (ROOT / "data" / "brief.yml").read_text()
    bands = re.findall(r"^  - id: (\S+)\n    up_to: (\d+)\n    offer: (\S+)$", src, re.M)
    if not bands:
        fail("data/brief.yml: no bands found — the configurator has nothing to price against")
        return
    last = -1
    for bid, up_to, offer in bands:
        if offer not in offer_ids:
            fail(f"brief.yml band {bid}: names offer {offer!r}, which is not on the offer list. "
                 "A band may point at a price that was set elsewhere; it may not invent one")
        if int(up_to) <= last:
            fail(f"brief.yml band {bid}: up_to {up_to} does not ascend past the band before it")
        last = int(up_to)
    # Every `offer:` anywhere in the model, not only in the bands.
    for m in re.finditer(r"^\s*offer: (\S+)$", src, re.M):
        if m.group(1) not in offer_ids:
            fail(f"brief.yml: references offer {m.group(1)!r}, which is not on the offer list")


def check_lab_model_is_shipped():
    """The configurator renders from a model written into the page by the build. If
    the page and the model could disagree about what is on sale, the running total
    beside somebody's estate would be priced against a list nobody published."""
    index = json.loads((OUT / "assets" / "site-index.json").read_text())
    offer_ids = {o["id"] for o in index["offers"]}
    prices = {o["id"]: o["price"] for o in index["offers"]}
    for p in lab_pages_built():
        rel = f"lab/{p.parent.name}/index.html"
        text = p.read_text()
        m = re.search(r'<script type="application/json" id="lab-model">(.*?)</script>', text, re.S)
        if not m:
            fail(f"{rel}: ships no model, so the configurator on it has nothing to render")
            continue
        try:
            model = json.loads(m.group(1))
        except ValueError as e:
            fail(f"{rel}: the model is not valid JSON ({e})")
            continue
        if set(model.get("offers", {})) != offer_ids:
            fail(f"{rel}: the model's offer set {sorted(model.get('offers', {}))} differs from "
                 f"the site's {sorted(offer_ids)}")
        for oid, o in model.get("offers", {}).items():
            if oid in prices and o.get("price") != prices[oid]:
                fail(f"{rel}: the model prices {oid} at {o.get('price')!r}, the site at "
                     f"{prices[oid]!r} — a running total priced against a second list")
        for key in ("sections", "tracks", "bands", "scenarios"):
            if not model.get(key):
                fail(f"{rel}: the model carries no {key}")
        if model.get("root") is None:
            fail(f"{rel}: the model carries no root prefix, so every link the configurator "
                 "builds would be root-absolute and break off the custom domain")


def check_deposits():
    """The deposit is a second amount on one offer, and the failure it guards is
    specific: somebody paying the deposit while believing they bought the
    engagement. So the amount is frozen, it is held below the threshold the copy
    names, it is held below the price it is a deposit against, and the page has to
    say both halves."""
    index = json.loads((OUT / "assets" / "site-index.json").read_text())
    offers = {o["id"]: o for o in index["offers"]}
    src = (ROOT / "data" / "offers.yml").read_text()

    for oid, o in offers.items():
        dep = o.get("deposit")
        if dep is None:
            if oid in EXPECTED_DEPOSITS:
                fail(f"offer {oid}: the pack sets a deposit of {EXPECTED_DEPOSITS[oid][0]} and the "
                     "built offer carries none")
            continue
        if oid not in EXPECTED_DEPOSITS:
            fail(f"offer {oid}: carries a deposit of {dep['label']!r} that is not in the frozen "
                 "table — a deposit is a number on a printed card and is not the builder's to invent")
            continue
        label, amount = EXPECTED_DEPOSITS[oid]
        if dep["label"] != label or dep["amount"] != amount:
            fail(f"offer {oid}: deposit is {dep['label']!r}/{dep['amount']}, the pack sets "
                 f"{label!r}/{amount}")
        if dep["amount"] >= CARD_THRESHOLD:
            fail(f"offer {oid}: the deposit is {dep['label']} and this site's own copy says a card "
                 f"stops making sense above about £{CARD_THRESHOLD // 100:,}. A deposit at or above "
                 "that argues against the checkout in the paragraph beside it")
        block = re.search(rf"(?ms)^- id: {re.escape(oid)}\n(.*?)(?=^- id: |\Z)", src)
        m = re.search(r"^\s*price_min: (\d+)$", block.group(1), re.M) if block else None
        if m and dep["amount"] >= int(m.group(1)):
            fail(f"offer {oid}: the deposit ({dep['amount']}) is not smaller than the engagement's "
                 f"floor ({m.group(1)}). A deposit that is not smaller than the thing is the price")

        page = OUT / "d" / oid / "index.html"
        if page.exists():
            flat = strip_tags(page.read_text())
            for needed in ("What the deposit does", "What it does not do"):
                if needed not in flat:
                    fail(f"/d/{oid}/: the deposit section does not say '{needed}' — a page that "
                         "takes a deposit and only says what it buys is the half that gets "
                         "somebody into trouble")
            if dep["label"] not in flat:
                fail(f"/d/{oid}/: does not name the deposit amount")


def check_deposit_not_beside_the_marketplace():
    """The marketplace's seller terms say a seller is not permitted to collect
    customer payment information at any time. A card deposit and a marketplace
    route are therefore ALTERNATIVES for one engagement and never a combination, so
    neither an offer card nor a delivery page may present both."""
    deposit_ids = set(EXPECTED_DEPOSITS)
    for p in pages():
        rel = str(p.relative_to(OUT)).replace(os.sep, "/")
        text = p.read_text()
        for oid in deposit_ids:
            if not (rel == f"d/{oid}/index.html" or f'id="offer-{oid}"' in text
                    or f'-offer-{oid}"' in text):
                continue
            if rel != f"d/{oid}/index.html":
                continue
            if re.search(r"marketplace", strip_tags(text), re.I):
                fail(f"{rel}: presents the marketplace on a page that takes a card deposit. "
                     "They are alternatives for one engagement, never a combination")


def check_offer_claims_exist():
    """Every offer's state chip links to a claim in the ledger. The chip is built
    from the offer record rather than from a shortcode, so an offer naming a claim
    nobody wrote renders a live-looking badge pointing at a dead anchor — which is
    what happened when the offer line was replaced and four new claims were cited
    a commit before they existed."""
    index = json.loads((OUT / "assets" / "site-index.json").read_text())
    known = {c["id"] for c in index["claims"]}
    src = (ROOT / "data" / "offers.yml").read_text()
    for m in re.finditer(r"(?ms)^- id: (\S+)\n(.*?)(?=^- id: |\Z)", src):
        oid, block = m.group(1), m.group(2)
        cm = re.search(r"^\s*claim: (\S+)$", block, re.M)
        if not cm:
            fail(f"offer {oid}: cites no claim, so its state badge is an assertion with nothing "
                 "behind it")
            continue
        if cm.group(1) not in known:
            fail(f"offer {oid}: cites claim {cm.group(1)!r}, which is not in the ledger. The badge "
                 "would link to an anchor that does not exist")


# ------------------------------------------- the deposit split, and the key rule ---
# Two of the four levels take a fifth on the order and the rest on delivery. That
# share is frozen exactly as a price is, because it IS a price: it decides what
# comes off a card, and it goes onto the same printed material.
#
# The second check here is the load-bearing one on this whole site. A vault key is
# never published and never committed; a page under docs/ is a committed file; so
# a key on the page a buyer lands on after paying is a security incident rather
# than a convenience. The post-sale page says HOW a key arrives and never carries
# one, and this refuses the release if anything key-shaped lands there.
EXPECTED_SPLIT = {"t1": 100, "t2": 100, "t3": 20, "t4": 20}

# A VAULT KEY AND A VAULT READ KEY ARE DIFFERENT OBJECTS, and the rule now says so.
#
# sgit_private_vault_ and sgit_private_write_ open a vault for WRITING. They are
# credentials, they are never published, they are never committed, and there is no
# page, no directory and no ruling that makes one of them acceptable in this output.
# That half did not move and will not.
#
# sgit_private_read_ opens a vault for reading and cannot write to it — verified by
# cloning with one, which reports "read-only (no commit/push)". For a vault that is
# deliberately published, that is a share link rather than a credential, the same way
# riskmandate.ai prints the read keys of its fifteen public templates on purpose.
#
# So a read key may appear, for a vault id in the frozen list below, and nowhere
# else. A second published vault is a second entry here, in the commit that says so.
# Two things worth knowing before adding one: a read key cannot be revoked without
# rekeying the vault, and everything in that vault is then public to anyone holding
# the address.
PUBLISHED_VAULTS = {
    "g2hei4u6": "admin/reviews/2026-09-15-synthetic-users",   # the synthetic-users vault
}

KEY_SHAPES = [
    (re.compile(r"sgit_private_(?:vault|write)_[A-Za-z0-9]{6,}"),
     "an sgit vault key that can WRITE"),
    (re.compile(r"[A-Za-z0-9_-]{16,}:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"),
     "a passphrase:uuid vault key"),
]
READ_KEY = re.compile(r"sgit_private_read_[0-9a-f]{16,}:?([a-z0-9]{4,})?")


def check_read_keys_are_only_for_published_vaults():
    """A read key is a share link for a vault somebody decided to publish, and it is
    still a mistake anywhere else. It may appear on the review page of a vault in the
    frozen list and on no other page — a key loose on a selling page is a key nobody
    decided to publish."""
    for rel, text in texts():
        for m in READ_KEY.finditer(text):
            vault = m.group(1)
            where = PUBLISHED_VAULTS.get(vault or "")
            if not vault:
                fail(f"{rel}: a read key with no vault id beside it. A key that cannot be traced "
                     "to a vault cannot be checked against the list of vaults meant to be public")
            elif where is None:
                fail(f"{rel}: publishes a read key for vault {vault!r}, which is not in the frozen "
                     "list of vaults meant to be public. Publishing a vault is a ruling")
            elif not rel.startswith(where):
                fail(f"{rel}: carries the read key for {vault!r}, which belongs on /{where}/ and "
                     "nowhere else")


def check_payment_split():
    index = json.loads((OUT / "assets" / "site-index.json").read_text())
    offers = {o["id"]: o for o in index["offers"]}
    for oid, pct in EXPECTED_SPLIT.items():
        got = offers.get(oid, {}).get("pay_now_pct")
        if got != pct:
            fail(f"offer {oid}: takes {got}% on the order, the ruling sets {pct}% — what comes off "
                 "a card is a price, and a price is not the builder's to move")
    for oid, o in offers.items():
        pct = o.get("pay_now_pct")
        if pct is None:
            continue
        if not (0 < pct <= 100):
            fail(f"offer {oid}: pay_now_pct is {pct}, which is not a share of a price")
        if pct < 100 and o.get("state") not in ("unrun", "spec", "unlocated", "absent", "booking"):
            fail(f"offer {oid}: takes a deposit but its state is {o.get('state')!r}. A deposit is "
                 "how a thing that has not run yet is sold honestly; a thing that runs takes its "
                 "price")


def check_post_sale_page():
    """The page a buyer lands on after paying: it exists, it says how a key
    arrives, and it carries no key."""
    page = OUT / "order" / "index.html"
    if not page.exists():
        fail("there is no post-sale page at /order/ — a payment's success address would land on "
             "the page the buyer already read before paying, which is the wrong page at the "
             "wrong moment")
        return
    flat = strip_tags(page.read_text())
    for needed in ("never on this page", "Done is a commit"):
        if needed not in flat:
            fail(f"/order/: does not say {needed!r}")
    for rel, text in texts():
        for rx, what in KEY_SHAPES:
            m = rx.search(text)
            if m:
                fail(f"{rel}: {what} is in the built output. A key is never published and never "
                     "committed, and every page here is a committed file")


def check_wallet_is_marked():
    """The simulated rail is never dressed to look live, and it is never the only
    rail on the page: a checkout that did not admit to being a demonstration would
    be the one dishonest thing on a site whose argument is checkability."""
    src = (ROOT / "data" / "checkout.yml").read_text()
    sim = re.findall(r"^\s*simulated: true$", src, re.M)
    if not sim:
        return  # no simulated rail is a fine state
    if len(sim) > 1:
        fail("data/checkout.yml: more than one rail is marked simulated")
    if len(re.findall(r"^  - id: ", src, re.M)) < 2:
        fail("data/checkout.yml: the simulated rail is the only rail. A demonstration wallet "
             "beside nothing real reads as the checkout rather than as a stand-in")
    js = (OUT / "assets" / "shop.js").read_text()
    for needed in ("charges nothing", "Simulated"):
        if needed not in js:
            fail(f"assets/shop.js: the simulated rail does not say {needed!r} on the screen it "
                 "appears on")


# THE DISCOUNT CODES, AND THE THING THAT MAKES THEM SAFE TO HAVE.
#
# A percentage off a price is a price, so it is frozen here the way the prices and
# the deposit shares are, keyed on the record's stable id. The id rather than the
# code, deliberately: a frozen table naming SUMMIT50 would put the code in a file
# that is read far more often than data/discounts.yml, and the whole point is that
# the code lives in exactly one place.
#
# The second check is the load-bearing one. What ships is sha256 of the code, and
# the browser hashes what it was handed and compares — so the built site must not
# contain any code anywhere, in any casing, in a page or in a script or in a JSON
# island. That is the same rule as "no vault key on any page" and it is here for
# the same reason: a static site publishes everything it carries, so what it must
# not give away it must not carry.
# pct, and whether the code may be PRINTED. Both are rulings: one decides what
# comes off a price, the other decides whether a stranger can read the code off a
# page. The three walkthrough codes are printed on purpose — a beta tester or a
# synthetic user cannot walk the flow without one — and the check below is what
# keeps that from becoming free product the day a rail is switched on.
EXPECTED_DISCOUNTS = {
    "summit-25":   (25,  False),
    "summit-50":   (50,  False),
    "summit-100":  (100, False),
    "loop-check":  (100, False),
    "beta-human":  (100, True),
    "synth-agent": (100, True),
    "demo-stand":  (100, True),
}


def check_discount_percentages():
    got = {c["id"]: (int(c["pct"]), c.get("printable") == "true")
           for c in yml_records("discounts.yml", "pct", "printable")}
    for cid, (pct, printable) in EXPECTED_DISCOUNTS.items():
        if cid not in got:
            fail(f"discount {cid}: in the frozen table and not in data/discounts.yml. A code that "
                 "was printed on something and then deleted is a code somebody will try")
            continue
        if got[cid][0] != pct:
            fail(f"discount {cid}: takes {got[cid][0]}% off, the ruling sets {pct}% — what comes "
                 "off a price is a price")
        if got[cid][1] != printable:
            fail(f"discount {cid}: printable is {got[cid][1]}, the ruling sets {printable}. "
                 "Whether a code may be read off a page is not the builder's to flip")
    for cid in got:
        if cid not in EXPECTED_DISCOUNTS:
            fail(f"discount {cid}: in data/discounts.yml and not in the frozen table. A discount "
                 "arrives by ruling, in the commit that says so")


def check_discount_codes_are_not_printed():
    """No code reaches the built site. Every byte of docs/ — pages, scripts, JSON
    islands, the markdown twins — against every code, in any casing."""
    codes = [c for c in yml_records("discounts.yml", "code", "printable")
             if c.get("printable") != "true"]
    everything = list(OUT.rglob("*"))
    for c in codes:
        rx = re.compile(re.escape(str(c["code"])), re.I)
        for f in everything:
            if not f.is_file():
                continue
            try:
                text = f.read_text()
            except (UnicodeDecodeError, OSError):
                continue
            if rx.search(text):
                rel = str(f.relative_to(OUT)).replace(os.sep, "/")
                fail(f"{rel}: carries discount code {c['id']!r} in plain text. What ships is the "
                     "hash and only the hash — a code in the built output is a code published")
    js = (OUT / "assets" / "shop.js").read_text()
    if "sha256" not in js:
        fail("assets/shop.js: does not hash anything, so it cannot be recognising a code by its "
             "hash — check what it is comparing instead")
    model = shop_model_island()
    if not model.get("codes"):
        fail("the shipped model carries no discount codes, so no code can be recognised")
    for c in model.get("codes", []):
        if not re.fullmatch(r"[0-9a-f]{64}", c.get("hash", "")):
            fail(f"discount {c.get('id')!r} ships {c.get('hash')!r}, which is not a sha256")
        if "code" in c:
            fail(f"discount {c.get('id')!r} ships the code itself in the model")


def check_printable_codes_need_a_dead_rail():
    """A published code at a hundred per cent and a rail that can take money must
    never be in the same build. Today every checkout_url is empty and the only rail
    that completes is a wallet that charges nothing, so a printed code costs nobody
    anything and the walkthrough is self-service. The day somebody pastes a real
    payment link in, this fails the release until the printed codes are gone.

    Left to a person to remember, this is the mistake that is made once."""
    printed = [c for c in yml_records("discounts.yml", "code", "printable", "pct")
               if c.get("printable") == "true"]
    if not printed:
        return
    src = (ROOT / "data" / "checkout.yml").read_text()
    live = [m for m in re.findall(r'^\s*url: "(.+)"$', src, re.M) if m.strip()]
    if live:
        names = ", ".join(c["id"] for c in printed)
        fail(f"a payment rail has a URL ({live[0]}) and these discount codes are printed on a "
             f"page: {names}. A published code and a live rail is free product. Remove the codes "
             "or set printable: false on them, in the commit that turns the rail on")
    for c in printed:
        if int(c.get("pct", 0)) != 100:
            fail(f"discount {c['id']}: printed on a page at {c['pct']}%. A printed code is a "
                 "walkthrough code and a walkthrough takes no money — a printed code at less "
                 "than a hundred per cent is a discount anybody can read")
    page = OUT / "admin" / "try" / "index.html"
    if not page.exists():
        fail("codes are marked printable and there is no /admin/try/ to print them on")
        return
    text = page.read_text()
    for c in printed:
        if c["code"] not in text:
            fail(f"discount {c['id']} is marked printable and is not on /admin/try/. A code that "
                 "is allowed onto a page and is on none is a code nobody can use")
    for f in OUT.rglob("*"):
        if not f.is_file() or f.suffix.lower() in {".png", ".jpg", ".svg", ".ico"}:
            continue
        rel = str(f.relative_to(OUT)).replace(os.sep, "/")
        # /admin/ is where they are printed. Everything else — including
        # llms-full.txt, which IS indexed — must not carry one, or the reason
        # printed on /admin/ for being noindex would not be true.
        if rel.startswith("admin/"):
            continue
        try:
            body = f.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        for c in printed:
            if re.search(re.escape(c["code"]), body, re.I):
                fail(f"{rel}: carries walkthrough code {c['id']!r}. These are printed on "
                     "/admin/try/ and nowhere else — a code loose on a selling page is a code "
                     "somebody finds without reading why it exists")


def check_the_build_reads_nothing_git_ignores():
    """A file the build reads, or writes, that git ignores passes every check here
    and fails on a clean checkout — because the gate builds from the working tree
    and CI builds from a clone. It has now happened twice on this estate, both times a
    language template's rule matching a directory of this estate's own: `build/`
    swallowed admin/build/ on a sibling site and shipped a release without its gate,
    and `downloads/` swallowed assets/downloads/ here and shipped two dead links.

    So this asks git, rather than asking the filesystem."""
    src = [ROOT / "assets", ROOT / "content", ROOT / "data", OUT]
    files = [f for d in src if d.is_dir() for f in d.rglob("*") if f.is_file()]
    if not files:
        return
    rels = [str(f.relative_to(ROOT)) for f in files]
    try:
        r = subprocess.run(["git", "check-ignore", "--stdin"], cwd=ROOT, text=True,
                           input="\n".join(rels), capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        note(f"could not ask git what it ignores ({e}); the build-inputs check did not run")
        return
    ignored = [x for x in r.stdout.split("\n") if x.strip()]
    for rel in ignored:
        what = ("the build WRITES this and git ignores it, so it would never reach the deployed "
                "site" if rel.startswith("docs/") else
                "the build reads this and git ignores it")
        fail(f"{rel}: {what}. It would be absent from a clean "
             "checkout, so the release would build differently in CI than it does here — "
             "un-ignore it in .gitignore, the way admin/build/ and assets/downloads/ are")


def check_the_shape_count_agrees_with_itself():
    """Fifteen published templates. The copy says 'fifteen' in words, the promoted
    catalogue carries fifteen records, and the catalogue's own count line says
    fifteen — and the sixteenth tile, the one for a deployment with no template, is
    counted separately because it is a different kind of thing.

    It disagreed: the copy said fifteen and the catalogue rendered '16 of 16
    shapes'. Found by walking the store as a synthetic user, which is the only way
    it WOULD be found — nothing on either side is wrong on its own, and the two
    numbers are four pages apart."""
    promoted = json.loads((ROOT / "data" / "abp-catalogue.json").read_text())["count"]
    model = shop_model_island()
    shapes = model.get("shapes", [])
    published = [s for s in shapes if s["slug"] != "your-own"]
    catchall = [s for s in shapes if s["slug"] == "your-own"]
    if len(published) != promoted:
        fail(f"the shipped model carries {len(published)} published shapes and the promoted "
             f"catalogue carries {promoted}")
    if len(catchall) != 1:
        fail(f"{len(catchall)} catch-all shapes in the model; there is exactly one deployment "
             "with no template and it is 'your-own'")
    words = {15: "fifteen", 16: "sixteen", 14: "fourteen", 17: "seventeen"}
    want = words.get(promoted)
    wrong = words.get(promoted + 1)
    if want:
        for rel, text in texts():
            if rel.startswith(("versions/", "ledger/", "admin/")):
                continue          # a record may quote the number it corrected
            m = re.search(rf"\b{wrong}\s+(?:applications|shapes|templates)\b", text, re.I)
            if wrong and m:
                fail(f"{rel}: says {m.group(0)!r}. {promoted} templates are published, so the "
                     f"word is {want!r} — the catch-all tile is counted separately because it is "
                     "a deployment with no template rather than one more template")
    js = (OUT / "assets" / "shop.js").read_text()
    if "your-own" not in js or "shapes'" not in js:
        fail("assets/shop.js: the catalogue count no longer separates the published shapes from "
             "the catch-all, which is how the two numbers disagreed in the first place")


def check_handover_contract():
    """riskmandate.ai publishes one page per level and its level-one page IS the
    download. The contract it published is two optional plain-text parameters —
    `order` everywhere, `shape` at level one — and this holds the store to it,
    because a success address that carries the wrong thing lands a paying buyer on
    a page that cannot tell them what they bought."""
    index = json.loads((OUT / "assets" / "site-index.json").read_text())
    offers = {o["id"]: o for o in index["offers"]}
    expect = {"t1": "[order, shape]", "t2": "[order]", "t3": "[order]", "t4": "[order]"}
    for oid, carries in expect.items():
        b = offer_block(oid)
        m = re.search(r'(?m)^  post_url: "(.*?)"$', b)
        url = m.group(1) if m else ""
        want = f"https://riskmandate.ai/paid-{oid}.html"
        if url != want:
            fail(f"offer {oid}: hands the buyer over to {url!r}, and the page riskmandate.ai "
                 f"publishes for that level is {want}")
        m = re.search(r"(?m)^  post_carries: (.*)$", b)
        if not m or m.group(1).strip() != carries:
            fail(f"offer {oid}: the handover carries "
                 f"{m.group(1).strip() if m else 'nothing'}; the contract is {carries}, and "
                 "nothing else is read at the other end")
    model = shop_model_island()
    for lv in model.get("levels", []):
        if not lv.get("post_url"):
            fail(f"level {lv['id']}: the shipped model has no page to hand the buyer to, so the "
                 "flow stops at this store and the buyer never reaches the download")
    js = (OUT / "assets" / "shop.js").read_text()
    for needed in ("post_carries", "order=", "shape="):
        if needed not in js:
            fail(f"assets/shop.js: does not build {needed!r} into the handover")


def check_follow_up_is_twenty_four_hours():
    """Two sites promising different things about the same follow-up is the drift
    the shared brief exists to stop. riskmandate.ai commits to twenty-four hours on
    its own pages, so that is the number here, and 'one working day' — which was a
    day behind it — must not come back."""
    for rel, text in texts():
        # The release history is a RECORD, and a record that cannot name the thing
        # it corrected is a record that quietly drops the correction — which is the
        # failure mode this site has a whole section about. So the version pages may
        # quote the old promise; no page that is selling anything may make it.
        if rel.startswith("versions/"):
            continue
        m = re.search(r"\bwithin (?:one|1) working day\b", text, re.I)
        if m:
            fail(f"{rel}: promises a follow-up 'within one working day'. The page the buyer lands "
                 "on says twenty-four hours, and the slower of two promises is the one that gets "
                 "quoted back")
    for oid in ("t2", "t3", "t4"):
        m = re.search(r'(?m)^  post_when: "(.*?)"$', offer_block(oid))
        if not m or "24 hours" not in m.group(1):
            fail(f"offer {oid}: does not say a person follows up within 24 hours. That sentence "
                 "is the whole of what is bought at this level until the vault arrives")
    m = re.search(r'(?m)^  post_when: "(.*?)"$', offer_block("t1"))
    if not m or "Immediately" not in m.group(1):
        fail("offer t1: since riskmandate.ai v1.19.2 the page a level-one buyer lands on IS the "
             "download, so nothing is waited for and this store must not say anything is")


def main():
    if not OUT.exists():
        print("docs/ not built — run python3 build.py first", file=sys.stderr)
        sys.exit(2)
    for fn in [
        # the estate's usual gate
        check_version_agreement, check_links, check_relative_urls, check_canonical_host,
        check_cname, check_markdown_twins, check_licence_stamp, check_shortcodes,
        check_no_unrendered_markdown, check_no_network, check_the_embed_is_what_it_says,
        check_no_credentials_in_output,
        check_each_script_loads_once,
        # the store pack's hard rules
        check_barred_word, check_no_conformity_language, check_compliance_assessment_only_denied,
        check_banned_words, check_cannot_read_sentence_absent, check_tamper_wording,
        check_naming_collision, check_prices, check_delivery_pages,
        check_committed_spend_correction, check_rails_not_a_choice,
        check_checkout_links, check_no_forms, check_the_typing_surface_is_inert,
        check_read_keys_are_only_for_published_vaults, check_the_review_register_is_whole,
        check_buyer_groups,
        check_deposits, check_deposit_not_beside_the_marketplace, check_offer_claims_exist,
        check_payment_split, check_post_sale_page, check_wallet_is_marked,
        check_discount_percentages, check_discount_codes_are_not_printed,
        check_printable_codes_need_a_dead_rail,
        check_handover_contract, check_follow_up_is_twenty_four_hours,
        check_the_shape_count_agrees_with_itself,
        check_the_build_reads_nothing_git_ignores,
        check_lab_is_marked, check_lab_bands, check_lab_model_is_shipped,
        check_model_generated_disclosure, check_triage_not_raw_findings,
        check_pack_area_is_honest,
    ]:
        fn()
    if failures:
        print(f"check_site: {len(failures)} problem(s)\n", file=sys.stderr)
        for f in failures:
            print("  ✗ " + f, file=sys.stderr)
        sys.exit(1)
    print(f"check_site: {len(list(pages()))} pages pass every acceptance assertion "
          "(the estate's gate, plus the store pack's hard rules).")
    for n in notes:
        print("  · " + n)


if __name__ == "__main__":
    main()
