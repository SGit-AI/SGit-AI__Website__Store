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
EXPECTED_PRICES = {
    "t1": ("£10", 1000, 1000),
    "t2": ("£50 to £100", 5000, 10000),
    "t3": ("£150 to £1,000", 15000, 100000),
    "t4": ("£5,000 to £10,000", 500000, 1000000),
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
            joined = os.path.normpath(os.path.join(base, target))
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


def check_no_network():
    """No page here opens a connection, and the footer says so. This is what makes
    that a fact rather than a sentence."""
    allowed_attr = re.compile(r'\b(?:src|href)="(https?:)?//')
    for p in pages():
        rel = str(p.relative_to(OUT)).replace(os.sep, "/")
        text = p.read_text()
        for m in re.finditer(r'\b(?:src|srcset|data-src)="(https?:)?//([^"/]+)', text):
            fail(f"{rel}: loads a resource from {m.group(2)} — every byte must come from this domain")
        if "<iframe" in text.lower():
            fail(f"{rel}: contains an iframe")
        for bad in ("fetch(", "XMLHttpRequest", "navigator.sendBeacon", "new WebSocket"):
            if bad in text:
                fail(f"{rel}: inline script uses {bad} — no page on this site contacts anything")
    for js in (OUT / "assets").glob("*.js"):
        text = js.read_text()
        for bad in ("fetch(", "XMLHttpRequest", "navigator.sendBeacon", "new WebSocket"):
            if bad in text:
                fail(f"assets/{js.name}: uses {bad}")


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
    "t1": "fixed",            # £10, one price, one link
    "t2": "banded",           # £50 to £100
    "t3": "banded",           # £150 to £1,000
    "t4": "conversation",     # at £10,000 the card fee alone reaches about £250
    "add-formats": "attached",
    "add-opinion": "none",
}
# The modes that cannot have a link at all, whatever anybody pastes into the file.
NO_LINK_MODES = ("attached", "conversation", "none")


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


def check_no_forms():
    """Three pages say this site collects nothing from anybody, ever. This is what
    makes that a fact rather than a sentence. A checkout that is a link to somebody
    else's page and a checkout that is a form on ours are different products with
    different obligations, and the difference is one tag."""
    for rel, text in texts():
        if not rel.endswith(".html"):
            continue
        for tag in ("<form", "<input", "<textarea", "<select"):
            if tag in text.lower():
                fail(f"{rel}: contains {tag}> — this site collects nothing, from anybody, ever")


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


def main():
    if not OUT.exists():
        print("docs/ not built — run python3 build.py first", file=sys.stderr)
        sys.exit(2)
    for fn in [
        # the estate's usual gate
        check_version_agreement, check_links, check_relative_urls, check_canonical_host,
        check_cname, check_markdown_twins, check_licence_stamp, check_shortcodes,
        check_no_unrendered_markdown, check_no_network, check_no_credentials_in_output,
        # the store pack's hard rules
        check_barred_word, check_no_conformity_language, check_compliance_assessment_only_denied,
        check_banned_words, check_cannot_read_sentence_absent, check_tamper_wording,
        check_naming_collision, check_prices, check_delivery_pages,
        check_committed_spend_correction, check_rails_not_a_choice,
        check_checkout_links, check_no_forms, check_buyer_groups,
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
