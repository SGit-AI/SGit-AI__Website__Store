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
    "t1": ("£10", 1000, 1000),
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
    """Every page allowed to open a connection, and there are exactly two kinds.

    NARROWED TWICE NOW, LOOSENED NEVER, AND THE SECOND ONE IS 16 SEPTEMBER.

      1. A review OF a vault embeds that vault. Added when the reviews became a
         register: a critique of a vault that a reader cannot open is a critique
         asking to be taken on trust.

      2. A page a buyer reaches AFTER PAYING embeds one published example vault.
         Added because "when you have sold a vault, you should just see the vault"
         — and because at the moment somebody pays there is nothing of theirs to
         show yet, so what they see is a published one, said to be an example in
         its first sentence.

    WHAT STAYED ABSOLUTE ACROSS BOTH: every page that SELLS anything opens no
    connection at all. That is the half the whole claim rests on, it has not moved,
    and /paid/ pages are on the other side of a purchase rather than in front of
    one. The pack level is not in this set either — it has no vault to show, so it
    does not get the component that can open a connection, which is the difference
    between a narrow exception and a wide one."""
    out = set()
    root = ROOT / "data" / "reviews"
    if root.is_dir():
        for f in root.glob("*.json"):
            if f.stem == "_register":
                continue
            if json.loads(f.read_text()).get("vault"):
                out.add(f"admin/reviews/{f.stem}/index.html")
    for oid in ("t2", "t3", "t4"):
        out.add(f"paid/{oid}/index.html")
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
            fail(f"{rel}: loads the vault embed. Only a review of a vault, or a page reached after "
                 "paying, may — and a page that sells anything never may")
        if 'class="sgv-uiembed"' in text and rel not in may:
            fail(f"{rel}: carries an embed mount and is neither a review with a vault nor a page "
                 "reached after paying")
        # The half that does not move. A page that asks for money opens nothing.
        if rel.startswith(("d/", "offers/", "cart/", "pay/", "p/", "are/", "compare/")) or rel == "index.html":
            if EMBED_COMPONENT in text or 'class="sgv-uiembed"' in text:
                fail(f"{rel}: is a page that sells something and it carries an embed. That half of "
                     "the claim has never moved and is not the builder's to spend")
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
        # THE SENTENCE CHANGED ON 16 SEPTEMBER BECAUSE THE FACT DID. It used to
        # require "the one place on this site that opens a connection", which was
        # exactly true while a review of a vault was the only such page. A page
        # reached after paying now embeds one too, so "the one place" became false
        # — and this check is what caught it, on the release that made it false,
        # before either page shipped saying it.
        #
        # What is required now is the same account of the mechanism, said in words
        # that are true of both: this page opens a connection, the key does not
        # travel in the address, and selling pages still open none.
        for needed in ("opens a connection",
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
    #
    # NARROWED ONCE, ON 16 SEPTEMBER, AND SAY EXACTLY HOW FAR. The pattern was any
    # absolute URL with a provider's name anywhere in it, which was right while no
    # page here had a provider's name in its own address. /admin/rails/stripe/ does,
    # so the check started failing the release over this site linking to itself.
    # A false positive is how a check gets deleted, so it is narrowed instead.
    #
    # WHAT STAYS ABSOLUTE: an off-site URL naming a provider is still a checkout and
    # still has to be declared, on any page, in any file. The exception is ONE
    # origin, this one, and what makes it safe is a fact rather than a convenience —
    # nothing on store.sgit.ai takes a payment, so a URL on store.sgit.ai cannot be
    # a payment destination. check_no_forms is what keeps that true.
    own = f"https://{DOMAIN}/"
    for rel, text in texts():
        for m in re.finditer(r'href="(https?://[^"]*stripe[^"]*)"', text, re.I):
            url = m.group(1)
            if url.startswith(own):
                continue
            if url not in declared:
                fail(f"{rel}: links to a checkout {url!r} that no offer declares — "
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
        # The wording moved on 16 September and this moved with it. What a page
        # taking typing owes the reader is that nothing they type is sent — which
        # is still absolutely true and is a stronger sentence than the one about
        # connections, because a review page DOES open one to embed its vault.
        for needed in ("nothing here sends anything about a reader",
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
# The five prototypes of the CONFIGURATOR. They all render one model and produce
# one brief, which is what makes them an experiment rather than five drafts.
EXPECTED_LAB_VIEWS = {"interview", "ladder", "board", "delta", "scenario"}
# Other prototypes living in the same protected surface. They are not
# configurators and the configurator assertions do not apply to them — but
# LAB_WARNING does, absolutely, and that is the reason they are here at all: /lab/
# is the one place on this site that already says "nothing here can be bought" on
# its own face and has a check refusing any page that stops saying it.
EXPECTED_LAB_OTHER = {"product", "agent-canvas", "agent-sequence"}


def lab_pages_built():
    return sorted((OUT / "lab").glob("*/index.html")) if (OUT / "lab").exists() else []


def check_lab_is_marked():
    """THE WARNING IS ABSOLUTE AND APPLIES TO EVERY PAGE IN THE LAB. The rest of
    these assertions are about the configurator, and stopped applying to every
    page on 16 September when a prototype that is not one moved in."""
    built = {p.parent.name for p in lab_pages_built()}
    if built != EXPECTED_LAB_VIEWS | EXPECTED_LAB_OTHER:
        fail(f"the prototype set changed: expected "
             f"{sorted(EXPECTED_LAB_VIEWS | EXPECTED_LAB_OTHER)}, built {sorted(built)}")
    for p in lab_pages_built():
        name = p.parent.name
        rel = f"lab/{name}/index.html"
        flat = strip_tags(p.read_text())
        # Every page in the lab, whatever kind it is. This is the rule the whole
        # surface exists for and it does not take exceptions.
        if LAB_WARNING not in flat:
            fail(f"{rel}: does not say {LAB_WARNING!r} — a page that looks like a checkout and "
                 "takes no money has to say which of the two it is before anybody reads on")
        for m in re.finditer(r'href="(https?://[^"]*stripe[^"]*)"', p.read_text(), re.I):
            fail(f"{rel}: carries a payment destination {m.group(1)!r}. Nothing in the lab is "
                 "buyable, so nothing in it may link to a checkout")
        if not (p.parent / "index.md").exists():
            fail(f"{rel}: no markdown twin")
        if name not in EXPECTED_LAB_VIEWS:
            continue
        # REWORDED 16 SEPTEMBER, AND THE DISTINCTION IS THE WHOLE POINT. This used
        # to require the words "has never run", which read as "nobody has ever done
        # this work" — false, and ruled off the site. What is actually true, and is
        # what a reader of a prototype is owed, is that the SEVEN-ROLE TEAM these
        # pages describe is a specification rather than something staffed. The work
        # itself is done, today, by a named person.
        if "specification rather than something staffed" not in flat:
            fail(f"{rel}: does not say the seven-role team it describes is a specification rather "
                 "than something staffed. The prototype configures work that a person does, and "
                 "the difference between a described team and a staffed one is the first thing a "
                 "reader is owed")


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
        # The configurator prototypes only. A product-page prototype is not one and
        # has no model to ship — see EXPECTED_LAB_OTHER.
        if p.parent.name not in EXPECTED_LAB_VIEWS:
            continue
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
# Vault id -> the page prefixes its read key may appear on, and no others. A
# vault reaches this table by ruling, in the commit that says so.
PUBLISHED_VAULTS = {
    # The synthetic-users vault, on the review that is of it.
    "g2hei4u6": ("admin/reviews/2026-09-15-synthetic-users",),
    # The worked example shown after a sale, on the three levels that are a vault.
    # sgit.ai publishes this read key on that vault's own page; it opens the vault
    # and cannot write to it.
    "posrhzp3": ("paid/t2", "paid/t3", "paid/t4"),
}

KEY_SHAPES = [
    (re.compile(r"sgit_private_(?:vault|write)_[A-Za-z0-9]{6,}"),
     "an sgit vault key that can WRITE"),
    (re.compile(r"[A-Za-z0-9_-]{16,}:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"),
     "a passphrase:uuid vault key"),
]
READ_KEY = re.compile(r"sgit_private_read_[0-9a-f]{16,}:?([a-z0-9]{4,})?")


# The bare form, which is what sgit.ai's own catalogue prints beside every vault
# and therefore the shape most likely to arrive here by a careless copy. It was
# NOT caught site-wide until 16 September — only inside data/evidence.yml — so a
# bare read key for an unpublished vault could have gone onto any page here and
# nothing would have said a word.
BARE_READ_KEY = re.compile(r"\b([0-9a-f]{64}):([a-z0-9]{4,12})\b")


def check_read_keys_are_only_for_published_vaults():
    """A read key is a share link for a vault somebody decided to publish, and it
    is still a mistake anywhere else.

    Both forms are checked: the prefixed `sgit_private_read_…` one and the bare
    `<64 hex>:<vault id>` one that sgit.ai's catalogue prints. Each may appear only
    on the pages its vault is allowed on — a key loose on a selling page is a key
    nobody decided to publish, whichever shape it arrived in."""
    # THE SHAPE THE EMBED ACTUALLY USES, AND IT WAS NOT CAUGHT UNTIL 16 SEPTEMBER.
    # The component takes its key and its vault id in two separate attributes, so
    # neither the prefixed pattern nor the colon-joined one matched a key sitting
    # in live markup. A deliberate break walked straight through. It is the exact
    # shape a careless copy would produce, because it is the shape this site's own
    # pages carry.
    mount = re.compile(r'data-vault="([a-z0-9]{4,12})"\s+data-readkey="([0-9a-f]{64})"')
    for rel, text in texts():
        seen = [(m.group(1), m.group(0)) for m in READ_KEY.finditer(text)]
        seen += [(m.group(2), m.group(0)) for m in BARE_READ_KEY.finditer(text)]
        seen += [(m.group(1), m.group(0)) for m in mount.finditer(text)]
        for vault, _raw in seen:
            where = PUBLISHED_VAULTS.get(vault or "")
            if not vault:
                fail(f"{rel}: a read key with no vault id beside it. A key that cannot be traced "
                     "to a vault cannot be checked against the list of vaults meant to be public")
            elif where is None:
                fail(f"{rel}: publishes a read key for vault {vault!r}, which is not in the frozen "
                     "list of vaults meant to be public. Publishing a vault is a ruling")
            elif not rel.startswith(tuple(where)):
                fail(f"{rel}: carries the read key for {vault!r}, which belongs on "
                     f"{' or '.join('/' + w + '/' for w in where)} and nowhere else")


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
        # WHAT A DEPOSIT IS FOR, RESTATED 16 SEPTEMBER. This used to allow a deposit
        # only on something that had not run yet, which read the split as a hedge
        # against an unproven thing. That was never the main reason and it is not a
        # reason at all now: a deposit is how SCHEDULED PROFESSIONAL WORK is sold,
        # everywhere, because the thing being reserved is somebody's calendar and
        # the balance falls due when the work is in the buyer's hands.
        #
        # What stays barred is the case the rule was really written for: a thing
        # that is produced the moment you pay, taking a deposit. That is a store
        # holding money for no reason, and it is still refused.
        if pct < 100 and o.get("state") not in ("person", "spec", "unlocated", "absent", "booking"):
            fail(f"offer {oid}: takes a deposit but its state is {o.get('state')!r}. A deposit "
                 "reserves somebody's time, or holds a place for something not yet built; a thing "
                 "produced the moment you pay takes its price")


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
    # Leaked on purpose, on two named journeys, and held to the two levels that
    # are produced the moment you pay — see
    # check_a_leaked_code_cannot_buy_somebody_s_day, which is the half that
    # carries the risk.
    "doors-open":  (100, True),
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
        # NARROWED 16 SEPTEMBER. This refused any printed code once a rail could
        # take money, on the reasoning that a published hundred-per-cent code and a
        # live rail is free product. That stays true of a code that can reach a
        # level somebody has to WORK on — a person's day cannot be given away by a
        # typo. It is not true of the two levels produced the moment you pay out of
        # material already published free under CC BY: there the code gives away
        # the packaging and the licence, which is the reasoning the project lead
        # gave on 16 September for not needing redemption caps at all.
        worked = {"custom", "session"}
        loose = [c for c in printed
                 if set(discount_levels(c["id"])) & worked or discount_levels(c["id"]) == ["all"]]
        if loose:
            names = ", ".join(c["id"] for c in loose)
            fail(f"a payment rail has a URL ({live[0]}) and these printed codes can reach a level "
                 f"that is somebody's work: {names}. A person's day cannot be given away by a typo "
                 "\u2014 hold them to the produced levels, or set printable: false, in the commit "
                 "that turns the rail on")
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
        journeys = discount_journeys(c["id"])
        if journeys:
            # A leaked code lives on the journeys it names, not on /admin/try/.
            for j in journeys:
                f = OUT / j.strip("/") / "index.html"
                if not f.exists():
                    fail(f"discount {c['id']}: names journey {j!r} and no page is built there")
                elif c["code"] not in f.read_text():
                    fail(f"discount {c['id']}: names journey {j!r} and is not on it. A code "
                         "allowed onto a page and on none is a code nobody can use")
        elif c["code"] not in text:
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
            if not re.search(re.escape(c["code"]), body, re.I):
                continue
            # NARROWED 16 SEPTEMBER, AND EXACTLY THIS FAR. A printed code used to
            # be allowed under /admin/ and nowhere else. The ask was to publish one
            # on the main site on specific journeys, so a code may now also appear
            # on the journeys IT ITSELF DECLARES — and on no others, because a code
            # that leaked onto every page would be a price change nobody decided.
            #
            # What makes that survivable is not this rule. It is the levels half:
            # a leaked code cannot reach a level that is somebody's time, which
            # check_a_leaked_code_cannot_buy_somebody_s_day holds absolutely.
            journeys = discount_journeys(c["id"])
            allowed = {j.strip("/") + "/index.html" for j in journeys}
            allowed |= {j.strip("/") + "/index.md" for j in journeys}
            if rel in allowed:
                continue
            fail(f"{rel}: carries code {c['id']!r}, which is not one of its journeys "
                 f"({', '.join(journeys) or 'none — it is a walkthrough code'}). A code loose on a "
                 "page that did not ask for it is a price change nobody decided")


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
    """WHERE A BUYER LANDS AFTER PAYING, AND WHY IT MOVED.

    Until 16 September the success address was riskmandate.ai's page for the
    level, and this check held the store to the contract they published — two
    optional plain-text parameters, `order` everywhere and `shape` at level one.
    That contract was kept honestly and the reasoning for it was good: their
    level-one page IS the download, and copying a size and a sha256 over here
    would mean two of each.

    It moved because of what it cost. A synthetic buyer did a whole purchase on
    this site and was dropped onto another one, in a different interface, at the
    moment they had just paid. So the buyer lands here now.

    WHAT STAYS ABSOLUTE. The parameters are unchanged, because they are still the
    right two and because a printed link cannot be recalled. What is new is that
    the destination must be ON THIS SITE and must be a page this build actually
    emits — a success address pointing at a 404 is the single worst dead link a
    store can have, and it is the one nobody clicks until a stranger has paid.

    And the old destination is not deleted: every level keeps `post_upstream`, so
    the page that holds the artefact stays one named link away rather than
    becoming a thing somebody has to go and find in git history."""
    index = json.loads((OUT / "assets" / "site-index.json").read_text())
    offers = {o["id"]: o for o in index["offers"]}
    expect = {"t1": "[order, shape]", "t2": "[order]", "t3": "[order]", "t4": "[order]"}
    for oid, carries in expect.items():
        b = offer_block(oid)
        m = re.search(r'(?m)^  post_url: "(.*?)"$', b)
        url = m.group(1) if m else ""
        want = f"https://{DOMAIN}/paid/{oid}/"
        if url != want:
            fail(f"offer {oid}: hands the buyer over to {url!r}. Since 16 September a buyer lands "
                 f"on this site, and the page for this level is {want}")
        elif not (OUT / "paid" / oid / "index.html").exists():
            fail(f"offer {oid}: its success address is {url!r} and this build emits no page there. "
                 "A success address pointing at a 404 is the one dead link nobody clicks until a "
                 "stranger has paid")
        up = re.search(r'(?m)^  post_upstream: "(.*?)"$', b)
        want_up = f"https://riskmandate.ai/paid-{oid}.html"
        if not up or up.group(1) != want_up:
            fail(f"offer {oid}: has no post_upstream, or it is not {want_up}. The page that holds "
                 "the artefact stays one named link away rather than disappearing into git history")
        m = re.search(r"(?m)^  post_carries: (.*)$", b)
        if not m or m.group(1).strip() != carries:
            fail(f"offer {oid}: the handover carries "
                 f"{m.group(1).strip() if m else 'nothing'}; the contract is {carries}, and "
                 "nothing else is read at the other end")
        page = OUT / "paid" / oid / "index.html"
        if page.exists():
            flat = strip_tags(page.read_text())
            if offers[oid]["eta"] not in flat:
                fail(f"paid/{oid}: does not say when it arrives. That is the one thing somebody "
                     "who has just paid is looking for")
            if "noindex" not in page.read_text():
                fail(f"paid/{oid}: is not noindex. A page that says 'you bought' has no business "
                     "in a search result")

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


# ------------------------------------------- the queue, the board, the catalogue ---
# THREE FILES FEED THE CONSOLE AND NONE OF THEM IS CHECKED BY ANYTHING ELSE.
# data/admin/memos.json is the queue, data/admin/work.json is the board, and the
# Stripe catalogue is generated from the offers. A board is only worth having if
# it cannot quietly disagree with itself, so what these hold is exactly that:
# every reference resolves, every status is one the board can draw, and the price
# list handed to a payment provider says what data/offers.yml says.
WORK_COLUMNS = ("queued", "next", "in-progress", "done")


def _admin_json(name):
    return json.loads((ROOT / "data" / "admin" / name).read_text())


def check_the_board_is_whole():
    work = _admin_json("work.json")
    memos = _admin_json("memos.json")
    cols = tuple(c["key"] for c in work["columns"])
    if cols != WORK_COLUMNS:
        fail(f"the board's columns are {cols}, and the four it is drawn with are {WORK_COLUMNS} — "
             "a fifth column is a design change, not a data edit")
    ws_ids = {w["id"] for w in work["workstreams"]}
    memo_ids = {m["id"] for m in memos["memos"]}
    seen = set()
    for w in work["workstreams"]:
        if w.get("memo") and w["memo"] not in memo_ids:
            fail(f"workstream {w['id']}: names memo {w['memo']!r}, which is not in the queue")
        if not w["tasks"]:
            fail(f"workstream {w['id']}: has no units of work. An empty workstream is a heading "
                 "pretending to be a plan")
        for task in w["tasks"]:
            if task["id"] in seen:
                fail(f"task {task['id']}: appears twice on the board")
            seen.add(task["id"])
            if task["status"] not in cols:
                fail(f"task {task['id']}: status {task['status']!r} is not a column on this board, "
                     "so the card would be built and never drawn")
            if task.get("memo") and task["memo"] not in memo_ids:
                fail(f"task {task['id']}: names memo {task['memo']!r}, which is not in the queue")
            if task.get("source") and task["source"] not in work["sources"]:
                fail(f"task {task['id']}: source {task['source']!r} is not one this board names")
    # A memo that produced no work is a memo that was filed and not acted on. That
    # is the exact failure this queue exists to make impossible.
    for m in memos["memos"]:
        if not m["workstreams"]:
            fail(f"memo {m['id']}: names no workstream — captured and never broken into work")
        for wid in m["workstreams"]:
            if wid not in ws_ids:
                fail(f"memo {m['id']}: names workstream {wid!r}, which is not on the board")


def check_the_board_pages_agree_with_the_board():
    """The rendered board is generated, so this checks the arithmetic rather than
    the wiring: a workstream is drawn in the column its own tasks put it in."""
    work = _admin_json("work.json")
    for w in work["workstreams"]:
        ts = [t["status"] for t in w["tasks"]]
        want = ("done" if all(s == "done" for s in ts)
                else "in-progress" if "in-progress" in ts
                else "next" if "next" in ts else "queued")
        want = w.get("status", want)
        page = OUT / "admin" / "work" / "index.md"
        if not page.exists():
            fail("admin/work/index.md: the board has no markdown twin")
            return
        if f"## {w['title']} — {want}" not in page.read_text():
            fail(f"workstream {w['id']}: its tasks put it in {want!r} and the board's twin does not "
                 "say so — the summary and the detail have come apart")


def check_the_stripe_catalogue_is_the_offers():
    """The reconciliation. Six products exist in the dashboard now, so this is no
    longer a check on a plan — it is the thing standing between two copies of the
    same price list and the day they disagree.

    THE SITE CANNOT ASK STRIPE ANYTHING. It opens no connection and that rule is
    not moving for this. So the other side is the dashboard's own CSV export,
    committed to the repository, plus the amounts read off the product list on the
    same day. That is weaker than an API call and it is the honest strongest thing
    available to a static site: it catches a price changed HERE and not there,
    which is the direction that actually happens, and it goes stale in the other
    direction until somebody re-exports."""
    f = OUT / "admin" / "rails" / "stripe" / "catalogue.json"
    if not f.exists():
        fail("admin/rails/stripe/catalogue.json: the generated Stripe catalogue is missing")
        return
    cat = json.loads(f.read_text())
    index = json.loads((OUT / "assets" / "site-index.json").read_text())
    offers = {o["id"]: o for o in index["offers"]}
    by_offer = {}
    for row in cat["prices"]:
        o = offers.get(row["offer"])
        if not o:
            fail(f"the Stripe catalogue prices offer {row['offer']!r}, which this site does not sell")
            continue
        if row["currency"] != "gbp":
            fail(f"Stripe catalogue {row['code']}: currency {row['currency']!r}, not gbp")
        if row["part"] == "full" and row["label"] != o["price"]:
            fail(f"Stripe catalogue {row['code']}: says {row['label']!r} and the offer says "
                 f"{o['price']!r} — data/offers.yml is the only place a price exists")
        by_offer.setdefault(row["offer"], []).append(row)

        # The reconciliation itself.
        if not row.get("stripe_id"):
            fail(f"Stripe catalogue {row['code']}: nothing in the dashboard export answers "
                 "to it. Either the product has not been created or the export is stale, and a "
                 "price list that cannot say which is worse than no price list")
        elif not row.get("agrees"):
            # Both halves have to match. A product at the right price under the
            # wrong code is a line item no handler can map back to a level, and
            # that failure only surfaces after somebody has already paid.
            fail(f"Stripe catalogue {row['code']}: this site says {row['unit_amount']}p under "
                 f"{row['code']!r} and the dashboard export says "
                 f"{row.get('stripe_code')!r} at an amount that does not match. One of the two is "
                 "wrong and neither of them knows which")

    for oid, rows in by_offer.items():
        parts = {r["part"] for r in rows}
        if parts not in ({"full"}, {"deposit", "delivery"}):
            fail(f"offer {oid}: has Stripe parts {sorted(parts)}. A level is one product, or it is "
                 "a deposit and a delivery that add up. There is no third arrangement")

    # AND THE DASHBOARD'S OWN AMOUNTS HAVE TO ADD UP TO THE PRICE ON THE PAGE.
    #
    # Read from data/admin/stripe-products.json rather than from the generated
    # catalogue, and that is the whole point of the assertion. The generated rows
    # are derived from data/offers.yml, so they sum correctly by construction and
    # checking them against each other proves nothing — an earlier version of this
    # did exactly that and a deliberate break walked straight through it.
    #
    # What a buyer pays is the sum of what is in the dashboard. If that stops
    # matching the price this site prints, somebody is charged the wrong total and
    # finds out afterwards.
    live = json.loads((ROOT / "data" / "admin" / "stripe-products.json").read_text())
    totals = {}
    for pr in live["products"]:
        totals[pr["offer"]] = totals.get(pr["offer"], 0) + pr["amount"]
    for oid, total in sorted(totals.items()):
        o = offers.get(oid)
        if not o:
            fail(f"the dashboard export carries products for {oid!r}, which this site does not sell")
            continue
        want = EXPECTED_PRICES[oid][1]
        if total != want:
            fail(f"offer {oid}: the products in the dashboard come to {total}p and this site "
                 f"prints {want}p. A buyer adding every line for this level pays the wrong total")

    for bad in ("sk_live", "sk_test", "whsec_", "pk_live", "pk_test"):
        if bad in json.dumps(cat):
            fail(f"the Stripe catalogue carries {bad!r}. It is a price list; a key is never in one")


def check_a_hundred_per_cent_coupon_is_capped():
    """RULED ON 16 SEPTEMBER: NO CAP IS REQUIRED, AND THE REASONING IS RECORDED.

    This check used to fail the release that turned a rail on with an uncapped
    hundred-per-cent coupon still in the account. The project lead overruled it,
    and the reasons are good ones rather than a shrug:

      · every purchase is managed directly, so a redemption is seen rather than
        discovered in a monthly total;
      · abuse would be obvious, because the volume that makes it worth doing is
        the volume that makes it visible;
      · and the thing a hundred-per-cent code gets you is ALREADY FREE. The
        templates are published with read keys. A code at a hundred per cent
        skips a payment for material somebody could have downloaded anyway —
        what it does not skip is the work at the upper levels, and that is done
        by a person who would notice.

    So the check reports rather than fails. It still runs, because the state is
    worth seeing on every release, and because the day the first reason stops
    being true is a day somebody should be reminded this was a decision."""
    live = json.loads((ROOT / "data" / "admin" / "stripe-products.json").read_text())
    for c in live.get("coupons", []):
        if c["pct"] != 100:
            continue
        if not c.get("max_redemptions"):
            note(f"coupon {c['name']!r} is 100% off with no cap and no expiry. Ruled acceptable on "
                 "16 September: purchases are managed directly, abuse at a useful volume would be "
                 "visible, and what the code skips paying for is already published free")
        if c.get("times_redeemed"):
            note(f"coupon {c['name']!r} has been redeemed {c['times_redeemed']} time(s). The "
                 "dashboard export is dated — re-export before reading anything into that")


def check_the_coupons_cover_every_discount():
    """Every percentage this store honours has a coupon, and no coupon exists at a
    percentage the store does not use.

    THREE COUPONS ONTO SEVEN CODES IS CORRECT AND IS NOT A SHORTFALL. Five of the
    seven are at a hundred per cent and exist as five so that an order record says
    which one produced it. That distinction lives in the promotion code, which is
    a different object; the coupon only ever needs to carry the percentage."""
    src = (ROOT / "data" / "admin" / "stripe-products.json")
    live = json.loads(src.read_text())
    coupons = live.get("coupons", [])
    if not coupons:
        return
    have = {c["pct"] for c in coupons}
    want = {pct for pct, _printable in EXPECTED_DISCOUNTS.values()}
    for pct in sorted(want - have):
        fail(f"this store honours a {pct}% code and no coupon exists at that percentage. A code "
             "recognised in the browser and unknown to the rail is a code that works until the "
             "moment it is worth money")
    for pct in sorted(have - want):
        fail(f"a {pct}% coupon exists on the account and no code on this store is at that "
             "percentage. Either a code was removed here and not there, or a discount exists that "
             "nothing on this site can explain")
    if len(coupons) != len({c["id"] for c in coupons}):
        fail("two coupons in the dashboard export share an id")


def check_a_withheld_term_is_declared():
    """Hard rule 12 has no allowlist, so a memo quoting a barred word renders a
    marker in its place. A marker without the sentence that explains it would be
    a silent edit of somebody's words, which is the thing the marker exists to
    prevent."""
    for p in pages():
        rel = str(p.relative_to(OUT)).replace(os.sep, "/")
        text = p.read_text()
        if "\u27e6withheld" in text or "⟦withheld" in text:
            if "withheld and marked" not in text and "withheld in place" not in text:
                fail(f"{rel}: a term is withheld in place and the page does not say so. A quotation "
                     "that has been altered says it has been altered")


# --------------------------------------------------- when each level arrives ---
# GIVEN BY THE PROJECT LEAD ON 16 SEPTEMBER, AND FROZEN HERE LIKE A PRICE. A
# delivery estimate is a promise to a buyer, so it is not the builder's to soften,
# round, or quietly drop when a page is rewritten.
#
# The second value is the one that matters and is the one most likely to be lost:
# at £500 and £1,500 the clock starts when the buyer sends their details, not when
# they pay, because until then there is nothing to work on. A page that says "1 to
# 3 days" without saying from what has made a promise nobody can keep.
EXPECTED_ETA = {
    "t1": ("Immediately", "the moment the payment goes through"),
    "t2": ("1 to 2 days", "from your payment"),
    "t3": ("1 to 3 days", "from your reply, not from your payment"),
    "t4": ("1 to 5 days", "from your reply, not from your payment"),
    "add-formats": ("With the level it attaches to", "same clock"),
    "add-opinion": ("With the level it attaches to", "same clock"),
}


def check_delivery_estimates():
    index = json.loads((OUT / "assets" / "site-index.json").read_text())
    got = {o["id"]: o for o in index["offers"]}
    for oid, (eta, frm) in EXPECTED_ETA.items():
        o = got.get(oid)
        if not o:
            fail(f"offer {oid}: missing from the built index")
            continue
        if o.get("eta") != eta:
            fail(f"offer {oid}: delivery estimate is {o.get('eta')!r}, and the one given is "
                 f"{eta!r} — a date promised to a buyer is not the builder's to change")
        if o.get("eta_from") != frm:
            fail(f"offer {oid}: the clock reads {o.get('eta_from')!r} and it starts {frm!r}. "
                 "An estimate with no start is a promise nobody can keep")
    # Every level page carries it. A number in a data file that no page prints is
    # a number that was never given to anybody.
    for oid in ("t1", "t2", "t3", "t4"):
        f = OUT / "d" / oid / "index.html"
        if f.exists() and EXPECTED_ETA[oid][0] not in f.read_text():
            fail(f"d/{oid}: the delivery page does not say when it arrives")


# ------------------------------------ the evidence that this work has been done ---
# THE CLAIM THIS CHECK PROTECTS IS THE MOST LOAD-BEARING ONE ON THE SITE. Until 16
# September the store said the upper levels had never run for a paying buyer and
# said nothing about the work behind them, so a reader concluded nobody had ever
# done it. data/evidence.yml is the correction: six published vaults, quoted from
# the catalogue that generates them, linked rather than described.
#
# Three things have to stay true or the correction becomes a worse problem than the
# thing it fixed:
#   · every entry points at a real published page, on the domain that publishes it;
#   · no read key is printed here, because that surface stays at one vault;
#   · the home page actually prints them. Evidence in a data file nobody renders is
#     evidence nobody has been shown.
EVIDENCE_HOST = "https://sgit.ai/demos/vaults/"


def check_the_evidence_is_real():
    src = (ROOT / "data" / "evidence.yml").read_text()
    urls = re.findall(r'^\s+url: "([^"]+)"', src, re.M)
    if len(urls) < 4:
        fail(f"data/evidence.yml carries {len(urls)} works. The claim it backs says six")
    for u in urls:
        if not u.startswith(EVIDENCE_HOST):
            fail(f"evidence {u!r} is not on {EVIDENCE_HOST} — the evidence for this work is the "
                 "published vault, not a page about it somewhere else")
    # Read keys AND write keys. The catalogue this file is quoted from prints a read
    # key beside every entry, so the bare <64 hex>:<vault id> form is the exact thing
    # most likely to arrive here by a careless copy — which is why it is named
    # rather than left to the generic shapes, none of which match it.
    BARE_READ = re.compile(r"\b[0-9a-f]{64}:[a-z0-9]{4,12}\b")
    for rx, what in list(KEY_SHAPES) + [(READ_KEY, "an sgit read key"),
                                        (BARE_READ, "a bare read key and vault id")]:
        if rx.search(src):
            fail(f"data/evidence.yml carries {what}. Every vault there publishes its own read key "
                 "on its own page, which is where a reader gets it — keeping them off this domain "
                 "keeps this store's key surface at one vault")
    home = (OUT / "index.html").read_text()
    missing = [u for u in urls if u not in home]
    if missing:
        fail(f"the home page does not link {len(missing)} of the {len(urls)} published works. "
             "Evidence nobody is shown is evidence nobody has")
    if "the-work-has-been-done" not in home:
        fail("index.html: the home page does not cite the claim that this work has been done. That "
             "sentence is the correction of 16 September and it is not optional furniture")


# The states a chip can render. Kept here rather than imported, because a check
# that reads the thing it is checking proves nothing — if build.py renames a state
# and this list is not updated, that IS the finding.
CHIP_STATES = {"exists", "measured", "docs", "projected", "spec", "person", "unlocated",
               "booking", "partial", "absent"}


def check_every_claim_state_is_real():
    """Every claim carries a state this site can draw.

    THIS EXISTS BECAUSE THE FALLBACK WAS SILENT. A state was renamed on 16
    September and two claims kept pointing at the old name. Nothing failed: the
    ledger rendered them as `unknown` with an empty tooltip, in production, on the
    page whose entire job is saying how true each sentence is. The build now
    raises on an unknown state; this catches it one step earlier, in the data,
    where the fix is one line."""
    src = (ROOT / "data" / "claims.yml").read_text()
    seen = {}
    cid = None
    for line in src.splitlines():
        if line.startswith("- id: "):
            cid = line[6:].strip()
        elif line.startswith("  state: ") and cid:
            seen[cid] = line[9:].strip()
    if not seen:
        fail("data/claims.yml: no claim states could be read at all")
        return
    for c, st in sorted(seen.items()):
        if st not in CHIP_STATES:
            fail(f"claim {c!r} has state {st!r}, which is not one this site can draw. It would "
                 f"render as 'unknown' with no tooltip on the ledger. The states are: "
                 f"{', '.join(sorted(CHIP_STATES))}")
    index = json.loads((OUT / "assets" / "site-index.json").read_text())
    for o in index["offers"]:
        if o["state"] not in CHIP_STATES:
            fail(f"offer {o['id']!r} has state {o['state']!r}, which is not one this site can draw")
    out = (OUT / "ledger" / "index.html")
    if out.exists() and 'class="chip st-u" title=""' in out.read_text():
        fail("ledger/index.html: a chip rendered with the unknown fallback and an empty tooltip")


EXPECTED_AUDIENCES = {
    # id            leads with   quieted
    "founder":     ("t2", {"t4"}),
    "investor":    ("t4", {"t1"}),
    "exec":        ("t3", {"t1"}),
    "security":    ("t1", set()),
    "governance":  ("t3", {"t1"}),
}


def check_the_five_audiences_hide_nothing():
    """Five views over the same four levels, and every level reachable from each.

    THIS IS THE CHECK THAT KEEPS AN HONEST ANSWER HONEST. The ask was that not
    every product is shown to every audience — an investor is not sold a
    ten-pound licence. The tempting implementation is to drop the cheap levels
    out of their view. That would make this site show different catalogues to
    different readers, which is a thing that has to be said out loud before it is
    built, and nobody has said it.

    So the implementation is: lead with what fits, quiet the rest, hide nothing.
    This check is what stops `quiet` quietly becoming `absent` — because that
    change is one CSS rule away and would look like a tidy-up in a diff."""
    src = (ROOT / "data" / "audiences.yml").read_text()
    ids = re.findall(r"^- id: (\S+)", src, re.M)
    if set(ids) != set(EXPECTED_AUDIENCES):
        fail(f"the audience set changed: expected {sorted(EXPECTED_AUDIENCES)}, built {sorted(ids)}")
        return
    index = json.loads((OUT / "assets" / "site-index.json").read_text())
    levels = [o["id"] for o in index["offers"] if o["id"].startswith("t")]
    for aid, (leads, quiet) in EXPECTED_AUDIENCES.items():
        f = OUT / "are" / aid / "index.html"
        if not f.exists():
            fail(f"are/{aid}: the audience page was not built")
            continue
        page = f.read_text()
        for lvl in levels:
            if f'href="../../d/{lvl}/index.html"' not in page and f'/d/{lvl}/' not in page:
                fail(f"are/{aid}: level {lvl} is not reachable from this view. Leading with what "
                     "fits is a view; removing a level is a different catalogue, and this site "
                     "does not show different people different catalogues")
        if "display:none" in page:
            fail(f"are/{aid}: something on this page is display:none. A quieted level is present "
                 "and reachable; a hidden one is a claim nobody made")
        if f'<div class="skus skus-one"><div class="sku" id="sku-' not in page:
            fail(f"are/{aid}: does not lead with a single level. The whole point of the view is "
                 "that it opens on one")
        md = OUT / "are" / aid / "index.md"
        if not md.exists():
            fail(f"are/{aid}: has no markdown twin")


def check_the_comparison_agrees_with_the_offers():
    """The comparison table cannot say something the offer data does not.

    A TABLE IS WHERE AN UNPROVEN CLAIM IS HARDEST TO NOTICE. Fourteen rows of
    ticks read as fact at a glance, and nobody cross-checks a tick against the
    page it came from. So: every column names a real offer, every price in the
    header is the price that offer carries, every delivery cell is the estimate
    that offer carries, and every row fills every column — a missing cell renders
    as nothing and reads as a no.

    What this check cannot do is prove a capability row is true; that is what the
    rule about not putting a promise in a column is for, and it is enforced by
    whoever adds a row rather than by a script."""
    src = (ROOT / "data" / "comparison.yml").read_text()
    col_ids = re.findall(r"^  - id: (\S+)", src, re.M)
    if not col_ids:
        fail("data/comparison.yml: no columns could be read")
        return
    index = json.loads((OUT / "assets" / "site-index.json").read_text())
    offers = {o["id"]: o for o in index["offers"]}
    for cid in col_ids:
        if cid != "free" and cid not in offers:
            fail(f"the comparison table has a column {cid!r} that is not an offer on this site")
    page = OUT / "compare" / "index.html"
    if not page.exists():
        fail("compare/index.html: the comparison page was not built")
        return
    html_text = page.read_text()
    # THE PRICES CANNOT DRIFT AND ARE NOT CHECKED HERE. The header reads each one
    # straight out of data/offers.yml at build time, so asserting they match would
    # be asserting a variable equals itself — an earlier version of this check did
    # exactly that and a deliberate break walked through it.
    #
    # THE DELIVERY CELLS ARE TYPED BY HAND IN data/comparison.yml, and those can.
    # A table that says one to two days next to a level whose own page says one to
    # three is the failure this file exists to make impossible, and it is the row a
    # buyer times their decision on.
    for cid in col_ids:
        if cid == "free":
            continue
        o = offers[cid]
        cell = re.search(rf"^      - label: Delivery$(.*?)^      - ", src,
                         re.M | re.S)
        if cell and not re.search(rf"^        {re.escape(cid)}: \"?{re.escape(o['eta'])}",
                                  cell.group(1), re.M):
            fail(f"compare: the delivery cell for {cid} does not start with {o['eta']!r}, which is "
                 "what data/offers.yml says. A table that disagrees with the level page beside it "
                 "is the one place a buyer will not think to check")
        if o["price"] not in html_text:
            fail(f"compare: {o['price']!r} does not appear on the built table at all")
    # Every row fills every column. A missing cell renders as nothing, and nothing
    # in a comparison table reads as a no — which is a claim nobody made.
    rows = re.findall(r"^      - label: (.+)$", src, re.M)
    blocks = re.split(r"^      - label: ", src, flags=re.M)[1:]
    for label, blk in zip(rows, blocks):
        for cid in col_ids:
            if not re.search(rf"^        {re.escape(cid)}: ", blk, re.M):
                fail(f"comparison row {label.strip()!r} has no cell for column {cid!r}. An empty "
                     "cell renders as nothing and reads as a no, which is a claim nobody made")
        if not re.search(r"^        why: ", blk, re.M):
            fail(f"comparison row {label.strip()!r} has no `why`. A table of bare ticks teaches "
                 "nothing \u2014 the sentence under the label is what the reader is buying")


EXPECTED_REVIEWERS = {"dinis-cruz": {"t3", "t4"}}


def check_every_reviewer_line_is_sourced():
    """A biography this store composed would be the worst thing on it.

    THIS IS THE CHECK THAT MATTERS MOST ON THIS SITE. Everything else here is
    checked because it is a price or a capability; this is checked because it is a
    PERSON standing next to a £1,500 price, and the temptation to round a date up
    or add a line nobody published is exactly the temptation this whole site
    exists to refuse. If the argument stops applying the moment a sentence is
    flattering, it was never an argument.

    So: every reviewer page names the published pages it was read from, with the
    date, above the record rather than under it; every reviewer runs the levels
    the register says; and the pages carry no count of years, because what is
    published is a record starting in 2008 and a round number nobody can verify is
    weaker than a date anybody can."""
    src = (ROOT / "data" / "reviewers.yml").read_text()
    ids = re.findall(r"^  - id: (\S+)", src, re.M)
    if set(ids) != set(EXPECTED_REVIEWERS):
        fail(f"the reviewer set changed: expected {sorted(EXPECTED_REVIEWERS)}, built {sorted(ids)}."
             " Adding one is deliberate and the frozen list moves with it")
        return
    sources = re.findall(r'^  - url: "([^"]+)"', src, re.M)
    if not sources:
        fail("data/reviewers.yml: carries no _sources. Every line of a record is read off a "
             "published page or it does not go on the page")
    reads = re.findall(r'^    read: "([^"]+)"', src, re.M)
    if len(reads) != len(sources):
        fail("data/reviewers.yml: a source has no date it was read on. A citation without a date "
             "is a citation nobody can re-check")

    for rid, offers in EXPECTED_REVIEWERS.items():
        f = OUT / "who" / rid / "index.html"
        if not f.exists():
            fail(f"who/{rid}: the reviewer page was not built")
            continue
        page = f.read_text()
        flat = strip_tags(page)
        for u in sources:
            if u not in page:
                fail(f"who/{rid}: does not name the published page {u!r} it was read from")
        if "Nothing here is written from what anybody told us" not in flat:
            fail(f"who/{rid}: does not say that nothing on it was written from what somebody told "
                 "us. On the one page of this site that describes a person, that sentence is the "
                 "whole guarantee")
        for oid in offers:
            if f"/d/{oid}/" not in page:
                fail(f"who/{rid}: does not link the level {oid} they run")
        # No count of years anywhere. The record starts in 2008 and a reader can do
        # the arithmetic; a round number nobody can verify is weaker than a date.
        m = re.search(r"(\d+|twenty|thirty|fifteen|ten)\+?\s+years", flat, re.I)
        if m:
            fail(f"who/{rid}: claims {m.group(0)!r}. The published record starts in 2008 and a "
                 "reader can do that arithmetic and check every step of it; a round number nobody "
                 "can verify is weaker than a date anybody can")
        if not (OUT / "who" / rid / "index.md").exists():
            fail(f"who/{rid}: has no markdown twin")

    # The levels that are somebody's work say whose, on their own page.
    index = json.loads((OUT / "assets" / "site-index.json").read_text())
    for o in index["offers"]:
        if o["state"] != "person":
            continue
        f = OUT / "d" / o["id"] / "index.html"
        if not f.exists():
            continue
        # NOT a search for "/who/" — the nav links it from every page on the site,
        # so that assertion was true of a page with nothing on it and a deliberate
        # break walked straight through. The section id is what only this page has.
        page = f.read_text()
        if 'id="who-does-it"' not in page:
            fail(f"d/{o['id']}: is delivered by a person and has no section naming one. A buyer at "
                 "this price is buying somebody's time and the page has to say whose")
        elif not any(f"/who/{rid}/" in page for rid in EXPECTED_REVIEWERS):
            fail(f"d/{o['id']}: has a who-does-it section that links no reviewer")


def _discount_block(cid):
    src = (ROOT / "data" / "discounts.yml").read_text()
    m = re.search(rf"(?ms)^- id: {re.escape(cid)}$(.*?)(?=^- id: |\Z)", src)
    return m.group(1) if m else ""


def discount_journeys(cid):
    """The pages a printed code is allowed to appear on. Empty means /admin/ only."""
    m = re.search(r"(?m)^  journeys: \[(.*?)\]$", _discount_block(cid))
    return [x.strip() for x in m.group(1).split(",") if x.strip()] if m else []


def discount_levels(cid):
    """The levels a code applies to. ["all"] means every one of them."""
    b = _discount_block(cid)
    m = re.search(r"(?m)^  levels: \[(.*?)\]$", b)
    if m:
        return [x.strip() for x in m.group(1).split(",") if x.strip()]
    return ["all"] if re.search(r"(?m)^  levels: all$", b) else []


def check_a_leaked_code_cannot_buy_somebody_s_day():
    """THE RULE THAT MAKES PUBLISHING A CODE SURVIVABLE, AND IT IS ABSOLUTE.

    A code published where anybody can read it may only reach levels that are
    PRODUCED the moment you pay, out of material that is already published free.
    It may never reach a level that is somebody's time. The difference is not a
    matter of degree: the packaging and the licence can be given away by a
    stranger with a browser, and a person's day cannot.

    This is the half that carries the risk. Everything else about a leaked code —
    where it appears, what it says, when it expires — is presentation."""
    worked = {"custom", "session"}
    src = (ROOT / "data" / "discounts.yml").read_text()
    for cid in re.findall(r"(?m)^- id: (\S+)$", src):
        if not discount_journeys(cid):
            continue
        levels = discount_levels(cid)
        if levels == ["all"]:
            fail(f"discount {cid!r} is published on a journey and applies to every level. A code "
                 "anybody can read must be held to the levels that are produced the moment you "
                 "pay — a person's day cannot be given away by a typo")
            continue
        bad = sorted(set(levels) & worked)
        if bad:
            fail(f"discount {cid!r} is published on a journey and reaches {', '.join(bad)}, which "
                 "is somebody's time. That is the one thing a leaked code may never do")
        for j in discount_journeys(cid):
            f = OUT / j.strip("/") / "index.html"
            if f.exists() and "and to nothing else" not in strip_tags(f.read_text()):
                fail(f"{j}: publishes a code and does not say what it does not apply to. A reader "
                     "who assumes it covers everything has been misled by omission")


# The unqualified sentence, which has been false since a review page first embedded
# a vault and is now false twice over. It read well and it was never quite true;
# the qualified one is the claim this site can actually keep.
UNQUALIFIED_NETWORK = re.compile(
    r"no page (?:here |on this site )?opens a network connection", re.I)


def check_the_network_claim_is_qualified():
    """The claim has to carry its own exception or it is not a claim.

    "No page here opens a network connection" is the sentence everybody wants to
    write. It stopped being true the day a review page embedded the vault it was
    reviewing, and it is now untrue on a second kind of page as well. The accurate
    version — no page that SELLS anything opens one — is the one this site can
    keep, and it is the one that is worth something, because it is the half a
    buyer actually cares about.

    This fails the release if the comfortable version comes back."""
    for rel, text in texts():
        if not rel.endswith((".html", ".md", ".txt", ".yml")):
            continue
        flat = strip_tags(text)
        for m in UNQUALIFIED_NETWORK.finditer(flat):
            before = flat[max(0, m.start() - 60):m.start()].lower()
            if "sells anything" in m.group(0).lower() or "that sells" in before:
                continue
            # A QUOTED SENTENCE IS A REPORT, NOT AN ASSERTION. The v0.1.17 release
            # note quotes the old claim in order to explain that it was rewritten,
            # and a rule that forbade that would force this site to describe its
            # own corrections without saying what it had corrected.
            if flat[max(0, m.start() - 1):m.start()] in ('"', "\u201c", "'", "\u2018"):
                continue
            ctx = flat[max(0, m.start() - 70):m.start() + 70].replace("\n", " ")
            fail(f"{rel}: says {m.group(0)!r} without its exception. Two kinds of page here open "
                 f"one and each says so; the claim that is true is about pages that SELL. \u2026{ctx}\u2026")


def check_the_capability_vocabulary_is_promoted_not_invented():
    """THE ONE THING THIS PAGE MUST NOT DO IS MAKE UP WORDS.

    "Describe your agent" produces the grant and hands it to a model session that
    turns it into a vault. If the palette used this store's own vocabulary, a
    buyer would describe their agent in one set of words and receive a document
    written in another — which is the worst outcome available to a page whose
    entire job is producing an input to that document.

    So every primitive rendered on a prototype has to be one that came out of
    riskmandate.ai's own template vault, the file has to carry the hash of the
    bytes it was promoted from, and the count has to match. The promotion is done
    by tools/promote_capabilities.py, by hand, because the build opens no
    connection."""
    f = ROOT / "data" / "capabilities.json"
    if not f.exists():
        fail("data/capabilities.json is missing and the agent prototypes render from it")
        return
    v = json.loads(f.read_text())
    prov = v.get("_promoted_from", {})
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", prov.get("content_hash", "")):
        fail("data/capabilities.json: no sha256 of the bytes it was promoted from. A promoted file "
             "without a content hash is a file that can drift silently")
    if not prov.get("vault") or not prov.get("page"):
        fail("data/capabilities.json: does not name the vault and the page it came from")
    # WHAT THIS CHECK CANNOT DO, SAID PLAINLY. It cannot tell a promoted file from
    # a hand-edited one: the content hash is self-reported, so anybody editing the
    # file could edit the hash beside it. A deliberate break proved exactly that.
    # Detecting a hand-edit means re-fetching, which means opening a connection,
    # which the build does not do — `tools/promote_capabilities.py --check` is the
    # thing that does it, by hand. What IS checked here is every invariant that
    # survives offline, which is most of them.
    caps = v.get("capabilities", [])
    if len(caps) != v.get("count"):
        fail(f"data/capabilities.json: says {v.get('count')} and carries {len(caps)}")
    # WHAT THE GRAMMAR ACTUALLY GUARANTEES, CORRECTED AFTER READING THE DATA.
    #
    # The first version of this rebuilt the id from verb.object.reach and demanded
    # it match. Five real primitives failed, and they were right and the check was
    # wrong: the id uses a SHORT FORM — `endpoint` for the object `network-endpoint`
    # — and its last segment is sometimes a discriminator rather than the reach
    # (`send.endpoint.allowed` has reach `tenant`; `read.record.browsing` has reach
    # `host`). Two primitives can share a verb, an object and a reach and still be
    # different things, which is what the last segment is for.
    #
    # So what is asserted is what holds: three segments, the first is the verb, and
    # the reach field is one the file defines. Anything tighter would be this
    # store's opinion about somebody else's vocabulary.
    grammar = v.get("grammar", "")
    n_parts = len(grammar.split("."))
    for c in caps:
        bits = str(c.get("id", "")).split(".")
        if len(bits) != n_parts:
            fail(f"capability {c.get('id')!r} has {len(bits)} segments and the grammar "
                 f"{grammar!r} has {n_parts}")
        elif bits[0] != c.get("verb"):
            fail(f"capability {c.get('id')!r} starts with {bits[0]!r} and its verb is "
                 f"{c.get('verb')!r}")
        if c.get("verb") not in v.get("verbs", []):
            fail(f"capability {c.get('id')!r} uses verb {c.get('verb')!r}, which the file does "
                 "not define")
        if c.get("reach") not in v.get("reaches", {}):
            fail(f"capability {c.get('id')!r} has reach {c.get('reach')!r}, which the file does "
                 "not define")
        if c.get("undo") not in ("yes", "no", "with-effort"):
            fail(f"capability {c.get('id')!r} has undo {c.get('undo')!r}, which is not one of the "
                 "three the upstream set uses")
        if c.get("family") not in v.get("families", {}):
            fail(f"capability {c.get('id')!r} is in family {c.get('family')!r}, which the file "
                 "does not define")
    ids = {c.get("id") for c in caps}
    # Every chip on every prototype is one of them, and there are no others.
    for page in (OUT / "lab").glob("agent-*/index.html"):
        rel = f"lab/{page.parent.name}/index.html"
        shown = set(re.findall(r'data-cap="([^"]+)"', page.read_text()))
        extra = shown - ids
        if extra:
            fail(f"{rel}: renders {sorted(extra)}, which is not in the promoted vocabulary. The "
                 "words on this page are riskmandate.ai's, not this store's")
        if shown != ids:
            fail(f"{rel}: renders {len(shown)} of {len(ids)} primitives. The page says how many "
                 "there are, so a partial palette makes the page wrong about itself")
        flat = strip_tags(page.read_text())
        if "It produces the grant" not in flat:
            fail(f"{rel}: does not say it produces the grant. A reader who thought this was the "
                 "whole document would be taking three quarters of the \u00a3500 level for "
                 "nothing in their own head")
    js = OUT / "assets" / "agent.js"
    if js.exists():
        src = js.read_text()
        for bad in ("fetch(", "XMLHttpRequest", "navigator.sendBeacon", "new WebSocket"):
            if bad in src:
                fail(f"assets/agent.js: uses {bad}. What somebody describes about their own agent "
                     "does not leave their browser")


def check_every_done_unit_points_at_something():
    """"Done" with nothing to open is the one status that can be wrong without
    anybody noticing.

    Every other state on the board is a statement about the future and is
    unfalsifiable by design. `done` is a claim about the past, and it is the claim
    a reader of the status page is actually relying on — so a unit marked done has
    to name the release it went out in and at least one page it produced or
    changed, both of which can be opened.

    The version has to be one this site has released. The pages have to be pages
    this build emits. A done unit pointing at a 404 is a status page that is worse
    than no status page, because it looks like evidence."""
    work = json.loads((ROOT / "data" / "admin" / "work.json").read_text())
    rel = json.loads((ROOT / "data" / "releases.json").read_text())
    versions = {r["version"] for r in rel["releases"]}
    for ws in work["workstreams"]:
        for task in ws["tasks"]:
            if task["status"] != "done":
                if task.get("shipped"):
                    fail(f"unit {task['id']}: is {task['status']!r} and carries a shipped record. "
                         "A thing that has not shipped cannot say where it landed")
                continue
            sh = task.get("shipped") or {}
            if not sh.get("version"):
                fail(f"unit {task['id']}: is done and names no release. Done with nothing to open "
                     "is the one status that can be wrong without anybody noticing")
                continue
            if sh["version"] not in versions:
                fail(f"unit {task['id']}: names release {sh['version']!r}, which this site has "
                     "never released")
            urls = sh.get("urls") or []
            if not urls:
                fail(f"unit {task['id']}: is done and points at no page")
            for u in urls:
                path = u.split("#")[0].strip("/")
                f = (OUT / path / "index.html") if path else (OUT / "index.html")
                if not f.exists():
                    fail(f"unit {task['id']}: says it landed at {u!r} and this build emits no page "
                         "there. A done unit pointing at a 404 is worse than no status page, "
                         "because it looks like evidence")
                elif "#" in u:
                    anchor = u.split("#", 1)[1]
                    if f'id="{anchor}"' not in f.read_text():
                        fail(f"unit {task['id']}: points at {u!r} and that page has no section "
                             f"with id {anchor!r}")
    page = OUT / "admin" / "status" / "index.html"
    if not page.exists():
        fail("admin/status/: the page joining memos to what they became was not built")
    else:
        # EVERY UNIT ON THE BOARD IS ON THE STATUS PAGE. It is organised by memo,
        # and one workstream predates the queue — so a page built only from memos
        # would have left it off while its units still counted on the board. A
        # status page that is silently incomplete is worse than one that says
        # where its own edges are.
        body = page.read_text()
        missing = [task["id"] for ws in work["workstreams"] for task in ws["tasks"]
                   if f'<code>{task["id"]}</code>' not in body]
        if missing:
            fail(f"admin/status/: {len(missing)} unit(s) on the board are not on the status page "
                 f"({', '.join(missing[:5])}). A status page that is silently incomplete is worse "
                 "than one that says where its own edges are")
        if not (OUT / "admin" / "status" / "index.md").exists():
            fail("admin/status/: has no markdown twin")


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
        check_delivery_estimates,
        check_every_claim_state_is_real,
        check_the_five_audiences_hide_nothing,
        check_the_comparison_agrees_with_the_offers,
        check_every_reviewer_line_is_sourced,
        check_a_leaked_code_cannot_buy_somebody_s_day,
        check_the_network_claim_is_qualified,
        check_the_capability_vocabulary_is_promoted_not_invented,
        check_every_done_unit_points_at_something,
        check_the_evidence_is_real,
        check_the_board_is_whole, check_the_board_pages_agree_with_the_board,
        check_the_stripe_catalogue_is_the_offers, check_a_withheld_term_is_declared,
        check_a_hundred_per_cent_coupon_is_capped, check_the_coupons_cover_every_discount,
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
