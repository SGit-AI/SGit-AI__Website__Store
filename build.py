#!/usr/bin/env python3
"""
build.py — the whole build system for store.sgit.ai.

Markdown in `content/` is the source of truth; this script renders it to static
HTML in `docs/`. No dependencies, no framework, no CDN: a site that argues for
checkability should not ask a reader to trust forty transitive packages.

    python3 build.py            build docs/
    python3 build.py --check    build to a temp dir and diff against docs/ (CI)

Generated, not hand-written:
  * the offer table and every offer card  — from data/offers.yml, which is the one
                                            place a price exists. A price typed
                                            twice is a price that will disagree
                                            with itself, and this site's prices
                                            are printed on cards that cannot be
                                            recalled from a conference floor
  * every delivery page                   — one per offer, from the same file, so
                                            the page a code lands on cannot
                                            promise something the offer does not
  * the claim ledger                      — from data/claims.yml, joined to every
                                            {{claim:id}} on every page
  * the release history and its pages     — from data/releases.json
  * the dev packs reader                  — from data/packs-manifest.txt, hashes
                                            and all
  * each page's markdown twin             — docs/<path>/index.md, house convention

Two rules from the pack shape the whole build.

**Offer identifiers are stable and the host is not.** `00__START-HERE.md`: the
domain may move, so every internal link is relative, the host appears in copy
nowhere, and the offer ids (`t1`…`t4`, `add-formats`, `add-opinion`) are the
things a payment link redirects to. A redirect then costs a DNS record and
nothing else.

**Compile offline into single files** (hard rule 15). The index, the manifest and
the machine indexes are compiled artefacts, not assembled in the browser.
"""

import html
import json
import os
import re
import shutil
import sys
import tempfile
import filecmp
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
ASSETS = ROOT / "assets"
FILES = ROOT / "files"
DATA = ROOT / "data"
# The dev packs, republished byte for byte from the pack as delivered.
PACKS = ROOT / "packs"
OUT = ROOT / "docs"

# The estate convention: one file owns the version, `bin/bump.py` moves it, the
# release commit's subject repeats it, and CI refuses to tag if the two disagree.
VERSION = (ROOT / "admin" / "build" / "version.txt").read_text().strip()

# The host. Recorded in one place, written to docs/CNAME, and checked against
# every canonical URL before a release.
#
# It is also the site's one open disagreement, and the pack is explicit that the
# disagreement is not the builder's to resolve: a ruling of 10 September placed a
# storefront under the risk product rather than on the platform domain, the
# instruction in hand overrode it, and the ruling stands on the record at
# /dev-packs/store/. What that costs the build is one line here and relative links
# everywhere — which is why the ruling is cheap to honour and cheap to reverse.
DOMAIN = "store.sgit.ai"

SITE = {
    "domain": DOMAIN,
    "base": f"https://{DOMAIN}",
    "title": "the store",
    "version": VERSION,
}

# The line that replaces the word this site may never print. Defined, implemented
# and running — hard rule 1, naming ruling 2.
LICENCE_TO_OPERATE = "every agent needs a licence to operate"

# Two levels, as on the sibling sites: every group label is itself a link to a real
# page, so nothing is reachable only by opening a menu.
NAV = [
    ("What is for sale", "/", []),
    ("The offers", "/offers/", [
        ("All six, side by side", "/offers/"),
        ("Who each one is for", "/audiences/"),
        ("What is not for sale yet", "/catalogue/"),
    ]),
    ("Paying", "/paying/", [
        ("The two rails", "/paying/"),
        ("Booking a person", "/booking/"),
    ]),
    ("Evidence", "/ledger/", [
        ("The claim ledger", "/ledger/"),
        ("What we do not say, and why", "/disclosures/"),
        ("The dev packs, published raw", "/dev-packs/"),
        ("Release history", "/versions/"),
    ]),
]

LICENCE_STAMP = (
    "This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0)."
)

# Hard rule 5: the transparency article has applied since 2 August 2026 and reaches
# a third-country party whose output is used in the Union. It goes on the face of
# the thing, not only in a footer — check_model_generated_disclosure holds that.
MODEL_GENERATED = (
    "Produced with model assistance. Every page on this site, and every document in "
    "the dev packs area, was drafted with a large language model and reviewed by a "
    "person before publication."
)

RELEASES = json.loads((DATA / "releases.json").read_text())
# ---------------------------------------------------------------- tiny YAML ---
# A deliberate subset: mappings, sequences, sequences of mappings, inline lists,
# quoted scalars. Anything hairier belongs in prose, not in front-matter.


def yaml_load(text):
    lines = []
    for raw in text.split("\n"):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        lines.append((indent, raw.strip()))
    val, _ = _yaml_block(lines, 0, 0)
    return val


def _scalar(s):
    s = s.strip()
    if not s:
        return ""
    if s[0] in "\"'" and s[-1] == s[0] and len(s) > 1:
        body = s[1:-1]
        if s[0] == '"':                       # only double quotes take escapes
            body = body.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
        return body
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        return [_scalar(x) for x in _split_commas(inner)] if inner else []
    if s == "true":
        return True
    if s == "false":
        return False
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d*\.\d+", s):
        return float(s)
    return s


def _split_commas(s):
    out, depth, cur, quote = [], 0, "", None
    for ch in s:
        if quote:
            cur += ch
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote, cur = ch, cur + ch
        elif ch in "[{":
            depth, cur = depth + 1, cur + ch
        elif ch in "]}":
            depth, cur = depth - 1, cur + ch
        elif ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return [x.strip() for x in out]


def _yaml_block(lines, i, indent):
    if i >= len(lines):
        return {}, i
    if lines[i][1].startswith("- "):
        return _yaml_seq(lines, i, indent)
    return _yaml_map(lines, i, indent)


def _yaml_map(lines, i, indent):
    out = {}
    while i < len(lines):
        ind, text = lines[i]
        if ind < indent:
            break
        if ind > indent:  # defensive: a stray deeper line
            i += 1
            continue
        key, _, rest = text.partition(":")
        key, rest = key.strip(), rest.strip()
        if rest:
            out[key] = _scalar(rest)
            i += 1
        else:
            i += 1
            if i < len(lines) and lines[i][0] > ind:
                out[key], i = _yaml_block(lines, i, lines[i][0])
            else:
                out[key] = None
    return out, i


def _yaml_seq(lines, i, indent):
    out = []
    while i < len(lines):
        ind, text = lines[i]
        if ind < indent or not text.startswith("- "):
            break
        body = text[2:].strip()
        if ":" in body and not body.startswith(("\"", "'")):
            # a mapping whose first pair is on the dash line
            sub_lines = [(0, body)]
            j = i + 1
            while j < len(lines) and lines[j][0] > ind:
                sub_lines.append((lines[j][0] - (ind + 2), lines[j][1]))
                j += 1
            item, _ = _yaml_map(sub_lines, 0, 0)
            out.append(item)
            i = j
        else:
            out.append(_scalar(body))
            i += 1
    return out, i


# ------------------------------------------------------------- markdown ------
# A subset of GFM: headings, paragraphs, lists, tables, fenced code, block
# quotes, rules, inline emphasis/code/links. Enough for a report; small enough
# to read in one sitting.

INLINE_CODE = re.compile(r"`([^`]+)`")
LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+\"([^\"]*)\")?\)")
BOLD = re.compile(r"\*\*([^*]+)\*\*")
EM = re.compile(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])")
STRIKE = re.compile(r"~~([^~]+)~~")


def slugify(text):
    s = re.sub(r"<[^>]+>", "", text).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "section"


def inline(text, ctx):
    """Inline markdown → HTML. Code spans are extracted first so nothing
    inside them is interpreted."""
    spans = []

    def stash(m):
        spans.append(m.group(1))
        return f"\x00{len(spans) - 1}\x00"

    # Vault content is a third party's bytes. On this surface there is no host: we
    # are the host, and a document must be able to change what is SHOWN and never
    # what the page DOES. So for republished vault files the escaper takes
    # everything — no raw tags survive, and no shortcode runs, because a vault
    # file must not be able to mint a claim chip on this site either.
    untrusted = ctx.get("untrusted")
    text = INLINE_CODE.sub(stash, text)
    if not untrusted:
        text = shortcodes_inline(text, ctx)
    # GFM autolinks. Without this, <https://example.com/x> reaches the browser as an
    # unknown tag and the URL disappears from the page entirely — which is how §4's
    # vendor citation shipped with its URL invisible. Every quote there is supposed to
    # carry the product, the URL and the date read; two of the three were arriving.
    if not untrusted:
        text = re.sub(
            r"<(https?://[^>\s]+)>",
            lambda m: f'<a href="{m.group(1)}" rel="noopener">{m.group(1)}</a>',
            text,
        )
    placeholders = {}

    def stash_html(fragment):
        placeholders[f"\x01{len(placeholders)}\x01"] = fragment
        return list(placeholders)[-1]

    # keep raw <chip …> etc. produced by shortcodes out of the escaper
    if untrusted:
        text = html.escape(text, quote=False)
    else:
        parts = re.split(r"(<[^>]+>)", text)
        text = "".join(stash_html(p) if p.startswith("<") and p.endswith(">") else html.escape(p, quote=False) for p in parts)

    text = LINK.sub(lambda m: _link(m, ctx), text)
    text = BOLD.sub(r"<strong>\1</strong>", text)
    text = EM.sub(r"<em>\1</em>", text)
    text = STRIKE.sub(r"<s>\1</s>", text)
    text = text.replace("--", "&ndash;") if False else text
    for k, v in placeholders.items():
        text = text.replace(k, v)
    for i, code in enumerate(spans):
        text = text.replace(f"\x00{i}\x00", f"<code>{html.escape(code, quote=False)}</code>")
    return text


# Schemes a link in REPUBLISHED VAULT CONTENT may use. "A link is a place a vault
# author can send your visitor" — sgit.ai's site-pages brief. A markdown link is
# enough to mint one: `[click](javascript:…)` produced a live javascript: href here,
# and `[x](data:text/html,…)` a live data: document, both confirmed in the built page
# before this list existed. Relative links and fragments are fine; everything else
# must name a scheme on this list or it is not rendered as a link at all.
SAFE_SCHEMES = ("http://", "https://", "mailto:", "/", "#", ".")


def _link(m, ctx):
    label, href, title = m.group(1), m.group(2), m.group(3)
    if ctx.get("untrusted") and not href.startswith(SAFE_SCHEMES):
        # Keep the words, drop the destination, and say so rather than silently
        # swallowing it — a reader can still see what the document meant to link.
        return (f'{label} <span class="deadlink" title="A link in republished vault '
                f'content may only use http, https or mailto">[link removed: '
                f'{html.escape(href.split(":", 1)[0])}:]</span>')
    ext = href.startswith("http") and SITE["domain"] not in href
    attrs = f' title="{html.escape(title)}"' if title else ""
    if ext:
        attrs += ' rel="noopener"'
        ctx["external_links"].add(href)
    return f'<a href="{html.escape(href)}"{attrs}>{label}</a>'


def render_markdown(md, ctx):
    lines = md.split("\n")
    out, i = [], 0
    last, spins = -1, 0
    while i < len(lines):
        if i == last:                      # every branch must consume at least one line
            spins += 1
            if spins > 1:
                raise SystemExit(f"build: parser stuck at line {i + 1}: {lines[i]!r}")
        else:
            last, spins = i, 0
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # fenced code
        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            body, i = [], i + 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                body.append(lines[i])
                i += 1
            i += 1
            cls = "shell" if lang in ("bash", "sh", "console", "shell") else (f"lang-{lang}" if lang else "")
            out.append(f'<pre class="{cls}">{html.escape(chr(10).join(body))}</pre>')
            continue

        # a block shortcode on a line of its own: {{app}}, {{ledger}}, {{comparison}}…
        if re.fullmatch(r"\{\{[a-z-]+\}\}", stripped):
            out.append(shortcodes_block(stripped, ctx))
            i += 1
            continue

        # <script> and <style> are consumed to their closing tag and emitted
        # VERBATIM, blank lines and all.
        #
        # They used to fall through to the raw-html branch below, which stops at the
        # first blank line — so a script with a blank line in it was cut in half and
        # the remainder rendered as markdown: `<p>` tags injected mid-function and
        # `i < all.length` escaped to `i &lt; all.length`. That ships a syntax error
        # into the page. It happened, on /estate/, and nothing caught it: tools/
        # check-js.sh only read assets/*.js and never the inline blocks. Both were
        # fixed together — this, and the check that would have found it.
        if re.match(r"<(script|style)\b", stripped, re.I) and not ctx.get("untrusted"):
            tag = re.match(r"<(script|style)\b", stripped, re.I).group(1).lower()
            block, close = [], f"</{tag}>"
            while i < len(lines):
                block.append(lines[i])
                done = close in lines[i].lower()
                i += 1
                if done:
                    break
            else:
                raise SystemExit(f"build: unclosed <{tag}> block")
            if close not in "\n".join(block).lower():
                raise SystemExit(f"build: unclosed <{tag}> block")
            out.append("\n".join(block))
            continue

        # raw html block (an <aside>, a stat-tile row, the app slot).
        # Never for republished vault content: there a block opening with `<` is a
        # paragraph that happens to start with an angle bracket, and it is escaped
        # like any other text. A vault file that shipped a <script> would otherwise
        # become a live script on this origin — which it did, until this line.
        if stripped.startswith("<") and not stripped.startswith("<http") and not ctx.get("untrusted"):
            block = []
            while i < len(lines) and lines[i].strip():
                block.append(lines[i])
                i += 1
            out.append(shortcodes_block("\n".join(block), ctx))
            continue

        # heading
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level, text = len(m.group(1)), m.group(2).strip()
            anchor = slugify(text)
            rendered = inline(text, ctx)
            if level >= 2:
                ctx["toc"].append((level, anchor, re.sub(r"<[^>]+>", "", rendered)))
            out.append(f'<h{level} id="{anchor}">{rendered}</h{level}>')
            i += 1
            continue

        # horizontal rule
        if re.fullmatch(r"(-{3,}|\*{3,})", stripped):
            out.append("<hr>")
            i += 1
            continue

        # table
        if "|" in stripped and i + 1 < len(lines) and re.fullmatch(r"\|?[\s:|-]+\|[\s:|-]*", lines[i + 1].strip()):
            head = _row(lines[i])
            aligns = [_align(c) for c in _row(lines[i + 1])]
            i += 2
            body = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                body.append(_row(lines[i]))
                i += 1
            th = "".join(f"<th{_style(a)}>{inline(c, ctx)}</th>" for c, a in zip(head, aligns + [None] * len(head)))
            trs = []
            for r in body:
                tds = "".join(f"<td{_style(a)}>{inline(c, ctx)}</td>" for c, a in zip(r, aligns + [None] * len(r)))
                trs.append(f"<tr>{tds}</tr>")
            out.append(
                '<div class="tablewrap"><table><thead><tr>' + th + "</tr></thead><tbody>" + "".join(trs) + "</tbody></table></div>"
            )
            continue

        # blockquote
        if stripped.startswith(">"):
            body = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                body.append(lines[i].strip()[1:].strip())
                i += 1
            out.append("<blockquote>" + render_markdown("\n".join(body), ctx) + "</blockquote>")
            continue

        # lists
        if re.match(r"^\s*([-*]|\d+\.)\s+", line):
            block, base = [], len(line) - len(line.lstrip(" "))
            while i < len(lines) and (
                re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]) or (lines[i].strip() and (len(lines[i]) - len(lines[i].lstrip(" "))) > base)
            ):
                block.append(lines[i])
                i += 1
            out.append(_list(block, base, ctx))
            continue

        # paragraph
        para = [lines[i].strip()]
        i += 1
        while i < len(lines) and lines[i].strip() and not _breaks_paragraph(lines, i):
            para.append(lines[i].strip())
            i += 1
        out.append("<p>" + inline(" ".join(para), ctx) + "</p>")
    return "\n".join(out)


def _breaks_paragraph(lines, i):
    """A paragraph ends at whatever starts another block. Note the space required
    after a bullet: `**bold at the start of a line**` is not a list item."""
    line = lines[i]
    if re.match(r"^\s*([-*]\s+|\d+\.\s+|#{1,6}\s|>|```)", line):
        return True
    if line.strip().startswith("<") and not line.strip().startswith("<http"):
        return True
    if "|" in line and i + 1 < len(lines) and re.fullmatch(r"\|?[\s:|-]+\|[\s:|-]*", lines[i + 1].strip()):
        return True
    return False


def _row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    cells, cur, esc = [], "", False
    for ch in line:
        if esc:
            cur, esc = cur + ch, False
        elif ch == "\\":
            esc = True
        elif ch == "|":
            cells.append(cur.strip())
            cur = ""
        else:
            cur += ch
    cells.append(cur.strip())
    return cells


def _align(cell):
    cell = cell.strip()
    if cell.startswith(":") and cell.endswith(":"):
        return "center"
    if cell.endswith(":"):
        return "right"
    return None


def _style(a):
    return f' style="text-align:{a}"' if a else ""


def _list(block, base, ctx):
    ordered = bool(re.match(r"^\s*\d+\.\s+", block[0]))
    items, cur = [], None
    for line in block:
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        indent = len(line) - len(line.lstrip(" "))
        if m and indent == base:
            if cur is not None:
                items.append(cur)
            cur = [m.group(3)]
        elif cur is not None:
            cur.append(line[base:] if len(line) > base else line.strip())
    if cur is not None:
        items.append(cur)
    lis = []
    for item in items:
        first, rest = item[0], [x for x in item[1:] if x.strip()]
        body = inline(first, ctx)
        if rest:
            sub_base = min(len(x) - len(x.lstrip(" ")) for x in rest)
            body += render_markdown("\n".join(x[sub_base:] if len(x) > sub_base else x for x in rest), ctx)
        lis.append(f"<li>{body}</li>")
    tag = "ol" if ordered else "ul"
    return f"<{tag}>" + "".join(lis) + f"</{tag}>"



# ------------------------------------------------------------- shortcodes ----
# The chip vocabulary. This site's states are not the sibling sites' states,
# because what it has to be honest about is different: a sibling report says how a
# number was obtained, and a store has to say whether the thing behind a price
# exists. Four of the eight below are ways of saying "not yet", and that is the
# proportion the pack describes.

STATES = {
    "exists": ("exists and runs", "st-v", "Built, and it runs today."),
    "measured": ("measured", "st-m", "Measured by our own pipeline on a named workload and date."),
    "docs": ("read, not run", "st-d", "Read from a published source on this date. Never executed by us."),
    "projected": ("projected", "st-p", "Arithmetic, not an invoice. The workings are shown."),
    "spec": ("specified, not built", "st-s", "A specification. The thing it specifies does not exist yet."),
    "unrun": ("specified, never run", "st-u", "Specified in full, and it has never been executed once."),
    "unlocated": ("built, not located", "st-u", "It was built. It has not been found since, and until it is, nothing here promises it."),
    "booking": ("a booking, not a download", "st-b", "What is bought is a person's time, not a file."),
    "partial": ("part exists", "st-s", "One half of it runs. The half that carries the guarantee does not."),
    "absent": ("does not exist yet", "st-x", "It does not exist. It is listed so that nobody proposes it as new."),
}


def chip(state, date=None, claim_id=None, label=None):
    text, cls, why = STATES.get(state, ("unknown", "st-u", ""))
    body = label or text
    if date:
        body += f" {date}"
    title = html.escape(why)
    if claim_id:
        return f'<a class="chip {cls}" href="/ledger/#claim-{claim_id}" title="{title}">{html.escape(body)}</a>'
    return f'<span class="chip {cls}" title="{title}">{html.escape(body)}</span>'


def shortcodes_inline(text, ctx):
    def claim_ref(m):
        cid = m.group(1)
        c = ctx["claims_by_id"].get(cid)
        if not c:
            raise SystemExit(f"build: unknown claim id {cid!r} referenced by {ctx['page']}")
        ctx["claim_uses"].setdefault(cid, set()).add(ctx["page"])
        return chip(c["state"], c.get("date_label"), cid)

    text = re.sub(r"\{\{claim:([a-z0-9-]+)\}\}", claim_ref, text)
    text = re.sub(
        r"\{\{badge:([a-z]+)(?:\|([^}]+))?\}\}",
        lambda m: chip(m.group(1), m.group(2)),
        text,
    )
    return text


def shortcodes_block(block, ctx):
    m = re.fullmatch(r"\s*\{\{([a-z-]+)\}\}\s*", block)
    if not m:
        # a hand-written HTML block: inline shortcodes still expand inside it, so a
        # claim chip can sit in a stat tile without going through the escaper.
        return shortcodes_inline(block, ctx)
    name = m.group(1)
    fn = BLOCKS.get(name)
    if not fn:
        raise SystemExit(f"build: unknown block shortcode {{{{{name}}}}} on {ctx['page']}")
    return fn(ctx)


# ------------------------------------------------------- generated blocks ----
# Every price, every offer card and every delivery page comes from data/offers.yml
# and is rendered here. Nothing about an offer is typed into a page.
#
# This is not tidiness. The codes are printed on cards, the cards go to a
# conference floor, and a printed price cannot be corrected afterwards. One file,
# one render, one gate that holds the numbers against the pack.

# The offers, and the only place a price exists. Read once, at module scope, so
# every block, every delivery page and every machine index render from the same
# record — a price typed twice is a price that will one day disagree with itself,
# and these prices go onto printed cards that cannot be recalled.
OFFERS = yaml_load((DATA / "offers.yml").read_text())

RAILS = {
    "link": ("Payment link", "A link, and a printed code beside it. An online payment, "
                             "so no cross-border rule applies to it."),
    "invoice": ("Invoice and bank transfer", "Above about £1,000 a card stops making sense. "
                                             "This one starts with a conversation."),
    "none": ("Not for sale yet", "There is no code behind this one."),
}


def offer_card(o, ctx, link=True):
    tier = o["tier"]
    label = f"Tier {tier}" if tier != "add-on" else "Add-on"
    rail_name, rail_why = RAILS[o["rail"]]
    href = f"/d/{o['id']}/" if o["rail"] != "none" else ""
    cta = (f'<a class="offer-cta" href="{href}">What arrives, and what does not &rarr;</a>'
           if link and href else
           '<span class="offer-cta offer-cta-off">No code behind this one yet</span>')
    return (
        f'<div class="offer" id="offer-{o["id"]}">'
        f'<div class="offer-head"><span class="offer-tier">{label}</span>'
        f'<span class="offer-price">{html.escape(o["price_label"])}</span></div>'
        f'<h3 class="offer-q">{html.escape(o["question"])}</h3>'
        f'<p class="offer-gets">{inline(o["gets"], ctx)}</p>'
        f'<p class="offer-state">{chip(o["state_badge"], claim_id=o["claim"])} '
        f'{inline(o["state"], ctx)}</p>'
        f'<p class="offer-rail"><b>{html.escape(rail_name)}.</b> {html.escape(rail_why)}</p>'
        f"{cta}</div>"
    )


def block_offers(ctx):
    tiers = [o for o in OFFERS if o["tier"] != "add-on"]
    addons = [o for o in OFFERS if o["tier"] == "add-on"]
    return (
        '<div class="offers">' + "".join(offer_card(o, ctx) for o in tiers) + "</div>"
        '<h2 id="the-two-add-ons">The two add-ons</h2>'
        '<p>Both attach to an offer above and are priced against its depth band. '
        'Neither is a tier, and neither can be bought on its own.</p>'
        '<div class="offers">' + "".join(offer_card(o, ctx) for o in addons) + "</div>"
    )


def block_offer_table(ctx):
    rows = []
    for o in OFFERS:
        tier = f"Tier {o['tier']}" if o["tier"] != "add-on" else "Add-on"
        href = f"/d/{o['id']}/" if o["rail"] != "none" else ""
        name = (f'<a href="{href}">{html.escape(o["question"])}</a>' if href
                else html.escape(o["question"]))
        rows.append(
            f'<tr><td><b>{tier}</b></td><td>{name}</td>'
            f'<td class="num">{html.escape(o["price_label"])}</td>'
            f'<td>{chip(o["state_badge"], claim_id=o["claim"])}</td>'
            f'<td class="small">{html.escape(RAILS[o["rail"]][0])}</td>'
            f'<td class="small"><code>{html.escape(o["id"])}</code></td></tr>'
        )
    return (
        '<div class="tablewrap"><table><thead><tr><th></th><th>The question it answers</th>'
        '<th class="num">Price</th><th>What is true of it today</th><th>How it is paid</th>'
        '<th>Offer id</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>"
        '<p class="small dim">The offer id is the stable part. A payment link redirects to '
        '<code>/d/&lt;id&gt;/</code>, so this site can move host without reprinting a card '
        'or reissuing a link.</p>'
    )


def block_prices_why(ctx):
    rows = "".join(
        f'<tr><td><b>{html.escape(o["price_label"])}</b><span class="small dim"> &mdash; '
        f'{html.escape(o["question"])}</span></td><td>{inline(o["price_why"], ctx)}</td></tr>'
        for o in OFFERS
    )
    return ('<div class="tablewrap"><table><thead><tr><th>The number</th>'
            "<th>Why it is that number</th></tr></thead><tbody>" + rows + "</tbody></table></div>")


def short_label(url):
    return url.strip("/").split("/")[-1] or "home"


def block_ledger(ctx):
    groups = {}
    for c in ctx["claims"]:
        groups.setdefault(c.get("group", "Other"), []).append(c)
    out = []
    for group, items in groups.items():
        out.append(f'<h3 id="{slugify(group)}">{html.escape(group)}</h3>')
        rows = []
        for c in items:
            used = sorted(ctx["claim_uses"].get(c["id"], set()), key=lambda u: ctx["page_urls"][u])
            links = ", ".join(
                f'<a href="{ctx["page_urls"][u]}" title="{html.escape(ctx["page_titles"][u])}">{short_label(ctx["page_urls"][u])}</a>'
                for u in used
            ) or '<span class="dim">&mdash;</span>'
            rows.append(
                f'<tr id="claim-{c["id"]}"><td>{inline(c["claim"], ctx)}</td>'
                f'<td>{chip(c["state"], c.get("date_label"))}</td>'
                f'<td class="small">{html.escape(str(c.get("source", "")))}</td>'
                f'<td class="small">{links}</td></tr>'
            )
        out.append(
            '<div class="tablewrap"><table class="ledger"><thead><tr><th>Claim</th><th>State</th>'
            "<th>How we know</th><th>Where it is said</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
        )
    counts = {}
    for c in ctx["claims"]:
        counts[c["state"]] = counts.get(c["state"], 0) + 1
    tiles = "".join(
        f'<div class="tile"><b>{counts.get(k, 0)}</b><span>{STATES[k][0]}</span></div>'
        for k in STATES if counts.get(k)
    )
    return f'<div class="tiles tiles-sm">{tiles}</div>' + "\n".join(out)


def block_releases(ctx):
    rows = []
    for r in RELEASES["releases"]:
        ver = r["version"]
        rows.append(
            f'<tr><td><a href="/versions/{ver}/"><code>{html.escape(ver)}</code></a>'
            f'{" &mdash; <b>current</b>" if ver == RELEASES["current"] else ""}</td>'
            f'<td class="small">{html.escape(r["date"])}</td>'
            f'<td>{inline(r["title"], ctx)}</td>'
            f'<td class="small"><code>{html.escape(r["commit"][:10] or "—")}</code></td></tr>'
        )
    return ('<div class="tablewrap"><table><thead><tr><th>Version</th><th>Released</th>'
            "<th>What changed</th><th>Commit</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


BLOCKS = {
    "offers": block_offers,
    "offer-table": block_offer_table,
    "prices-why": block_prices_why,
    "ledger": block_ledger,
    "releases": block_releases,
}


# ------------------------------------------------------------- dev packs ----
# The area exists; the documents are held. 04__THE-DEV-PACKS-AREA.md names five
# checks that run BEFORE anything is published, calls every one of them "a real
# edit or a real hold", and records that who runs them is not decided.
#
# Two of the five are measurable and are measured here. The other three need a
# person reading for tone. So what this area publishes today is the manifest —
# every document, its size, its sha256 — which is enough for a reader who was
# handed the pack to check their copy against it, and not enough to read a word
# of it here. That is the pack's own discipline pointed at the pack.

PACK = yaml_load((DATA / "pack.yml").read_text())


def block_pack_checks(ctx):
    rows = "".join(
        f'<tr><td class="num">{c["n"]}</td><td><b>{inline(c["check"], ctx)}</b>'
        f'<br><span class="small dim">{inline(c["why"], ctx)}</span></td>'
        f'<td class="small">{inline(c["who"], ctx)}</td>'
        f'<td>{chip("absent", label=c["state"])}</td></tr>'
        for c in PACK["checks"]
    )
    return ('<div class="tablewrap"><table><thead><tr><th class="num">#</th><th>The check</th>'
            "<th>Who can run it</th><th>State</th></tr></thead><tbody>"
            + rows + "</tbody></table></div>")


def block_pack_manifest(ctx):
    rows = []
    for d in PACK["documents"]:
        blocks = []
        if d["barred_word"]:
            blocks.append(f'<span class="hold">hard rule 1 &times;{d["barred_word"]}</span>')
        if d["collision"]:
            blocks.append(f'<span class="hold">check 5 &times;{d["collision"]}</span>')
        held = " ".join(blocks) or '<span class="dim small">nothing a script can see</span>'
        rows.append(
            f'<tr><td class="num"><code>{html.escape(str(d["seq"]))}</code></td>'
            f'<td class="small">{html.escape(d["kind"])}</td>'
            f'<td>{inline(d["subject"], ctx)}</td>'
            f'<td class="num small">{d["bytes"]:,}</td>'
            f'<td class="small"><code>{html.escape(d["sha256"][:16])}</code></td>'
            f"<td class=\"small\">{held}</td></tr>"
        )
    p = PACK["pack"]
    return (
        '<div class="tiles tiles-sm">'
        f'<div class="tile"><b>{p["documents"]}</b><span>documents</span></div>'
        f'<div class="tile"><b>{p["bytes"]:,}</b><span>bytes</span></div>'
        f'<div class="tile"><b>{sum(1 for d in PACK["documents"] if d["barred_word"])}</b>'
        '<span>blocked by hard rule 1</span></div>'
        f'<div class="tile"><b>{sum(1 for d in PACK["documents"] if d["collision"])}</b>'
        '<span>blocked by check 5</span></div>'
        f'<div class="tile"><b>0</b><span>published</span></div>'
        "</div>"
        '<div class="tablewrap"><table><thead><tr><th class="num">#</th><th>Kind</th>'
        '<th>Subject</th><th class="num">Bytes</th><th>sha256</th>'
        "<th>What holds it</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
        '<p class="small dim">The subjects are ours, written for this table. The documents\' own '
        'titles are held with the documents: one of them carries, in its title, the word hard '
        f'rule 1 bars from every page of this site. The full manifest is served as '
        '<a href="/dev-packs/pack.json">pack.json</a>. '
        f'The pack as delivered is {p["zip_bytes"]:,} bytes, sha256 '
        f'<code>{html.escape(p["zip_sha256"][:24])}</code>.</p>'
    )

BLOCKS.update({
    "pack-checks": block_pack_checks,
    "pack-manifest": block_pack_manifest,
})

# ------------------------------------------------------------------ shell ----


def rel_prefix(url):
    """How far a page sits below the site root: "" at /, "../" at /bench/."""
    depth = len([x for x in url.strip("/").split("/") if x])
    return "../" * depth


def relativise(doc, prefix):
    """Rewrite every root-absolute internal URL to one relative to this page.

    The site has to work wherever it is served from — the custom domain, a
    GitHub Pages project path (/<repo>/), a local directory, or inside a vault
    app frame, which has no origin at all. Root-absolute URLs work in exactly
    one of those, and the site spent its first deploy unstyled because of it.
    Directory URLs become explicit index.html so file:// works too.
    """

    def one(m):
        attr, target = m.group(1), m.group(2)
        path, _, frag = target.partition("#")
        path = path.lstrip("/")
        if path == "" or path.endswith("/"):
            path += "index.html"
        return f'{attr}="{prefix}{path}{"#" + frag if frag else ""}"'

    return re.sub(r'\b(href|src)="(/[^"]*)"', one, doc)



# ------------------------------------------------------------- delivery ----
# One page per offer, at /d/<id>/. This is where a payment code lands.
#
# The pack's ordering rule, from 00__START-HERE.md: "keep the offer identifiers
# stable so a redirect costs nothing." So the id is the whole contract between a
# printed code and this site. Everything else — the host, the path above it, the
# copy — can move.
#
# What the page must do, and the reason it is generated rather than written: it
# has to say what arrives AND what does not, from the same record the offer page
# renders. A delivery page written by hand is a delivery page that will one day
# promise something the offer no longer includes, and this one is read by somebody
# who has already paid.

def delivery_pages(out_dir, ctx_shared):
    made = {}
    for o in OFFERS:
        if o["rail"] == "none":
            continue
        url = f"/d/{o['id']}/"
        ctx = dict(ctx_shared)
        ctx.update({"page": f"d/{o['id']}", "page_url": url, "fm": {}, "toc": []})
        tier = f"Tier {o['tier']}" if o["tier"] != "add-on" else "Add-on"
        arrives = "".join(f"<li>{inline(x, ctx)}</li>" for x in o["delivery_says"])
        withheld = "".join(f"<li>{inline(x, ctx)}</li>" for x in o["not_promised"])
        rail_name, rail_why = RAILS[o["rail"]]
        body = (
            f'<p class="lead">{inline(o["gets"], ctx)}</p>'
            '<div class="tablewrap"><table><tbody>'
            f'<tr><th>Offer</th><td>{tier} &mdash; <code>{html.escape(o["id"])}</code></td></tr>'
            f'<tr><th>Price</th><td>{html.escape(o["price_label"])}</td></tr>'
            f'<tr><th>How it is paid</th><td>{html.escape(rail_name)}. {html.escape(rail_why)}</td></tr>'
            f'<tr><th>What is true of it today</th><td>{chip(o["state_badge"], claim_id=o["claim"])} '
            f'{inline(o["state"], ctx)}</td></tr>'
            "</tbody></table></div>"
            '<h2 id="what-arrives">What arrives</h2>'
            f"<ul>{arrives}</ul>"
            '<h2 id="what-this-is-not">What this is not, and will not become</h2>'
            f"<ul>{withheld}</ul>"
            '<div class="note"><p><b>Everything on this page is model generated unless it '
            'says otherwise, and it is marked as such where it is delivered.</b> '
            'Nothing here is a compliance assessment and nothing here is a mark of conformity &mdash; '
            'neither word applies and neither appears on the deliverable. '
            'Where a finding reaches you, it has been reproduced first: '
            'recall-optimised agents run at 0.388 precision, so what is sold is triage '
            'and never raw findings. {{claim:precision-0388}}</p></div>'
            '<p class="pagenav"><a href="/offers/">All six offers, side by side &rarr;</a>'
            '<a href="/paying/">How paying works &rarr;</a>'
            '<a href="/ledger/">Every claim on this site, with its state &rarr;</a></p>'
        )
        body = shortcodes_inline(body, ctx)
        page = {
            "fm": {"title": f"{tier} — {o['question']}",
                   "description": f"What arrives when you buy {tier.lower()} ({o['price_label']}), "
                                  f"and what it is not. Offer id {o['id']}."},
            "url": url,
            "crumb": f' / <a href="/offers/">offers</a> / {html.escape(o["id"])}',
            "nav_match": "/offers/",
            "src_md": (
                f"# {tier} — {o['question']}\n\n{o['gets']}\n\n"
                f"- Offer id: `{o['id']}`\n- Price: {o['price_label']}\n"
                f"- How it is paid: {rail_name}\n- What is true of it today: {o['state']}\n\n"
                "## What arrives\n\n" + "".join(f"- {x}\n" for x in o["delivery_says"]) +
                "\n## What this is not, and will not become\n\n" +
                "".join(f"- {x}\n" for x in o["not_promised"])
            ),
        }
        target = out_dir / url.strip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page_html(page, ctx, body))
        twin = page["src_md"]
        if LICENCE_STAMP not in twin:
            twin += f"\n---\n\n{LICENCE_STAMP}\n"
        (target.parent / "index.md").write_text(twin)
        made[url] = page["fm"]["title"]
    return made


# -------------------------------------------------------------- versions ----
# sgit.ai/docs/guidance: "Make it a link, and make the link go to that version's
# own details — not to a generic changelog. A reader who clicks v0.1.0 wants to
# know what v0.1.0 was." Plus: give versions a home as DATA, and record the commit
# each was built from, or a version cannot be verified later.

def release_pages(out_dir, ctx_shared):
    """One page per release, and a machine-readable index beside them."""
    made = {}
    rels = RELEASES["releases"]
    for i, r in enumerate(rels):
        ver = r["version"]
        url = f"/versions/{ver}/"
        ctx = dict(ctx_shared)
        ctx.update({"page": f"versions/{ver}", "page_url": url, "fm": {}, "toc": []})
        newer = f'<a href="/versions/{rels[i-1]["version"]}/">&larr; {rels[i-1]["version"]}</a>' if i else ""
        older = f'<a href="/versions/{rels[i+1]["version"]}/">{rels[i+1]["version"]} &rarr;</a>' if i + 1 < len(rels) else ""
        recon = ("" if not r.get("reconstructed") else
                 '<div class="note"><b>Reconstructed, not recorded.</b> This entry was assembled '
                 'after the fact from the sources below rather than written at release time. '
                 'The words are contemporaneous &mdash; the structure around them is not, and a '
                 'history assembled later is only useful if it says so.'
                 '<ul>' + "".join(f"<li>{html.escape(x)}</li>" for x in r.get("basis", [])) + "</ul></div>")
        changes = ("" if not r.get("changes") else
                   '<p class="small dim">Touched: ' +
                   " &middot; ".join(f"<code>{html.escape(c)}</code>" for c in r["changes"]) + "</p>")
        body = (
            f'<p class="lead">{inline(r["summary"] or r["title"], ctx)}</p>'
            '<div class="tablewrap"><table><tbody>'
            f'<tr><th>Version</th><td><code>{html.escape(ver)}</code>'
            f'{" &mdash; <b>current</b>" if ver == RELEASES["current"] else ""}</td></tr>'
            f'<tr><th>Released</th><td>{html.escape(r["date"])}</td></tr>'
            f'<tr><th>Built from commit</th><td><code>{html.escape(r["commit"] or "recorded one commit later")}</code></td></tr>'
            f'<tr><th>Site</th><td>{html.escape(r["site"])}</td></tr>'
            "</tbody></table></div>"
            f"{changes}{recon}"
            f'<p class="packnav">{newer}{older}</p>'
            '<p class="packfoot">Every release of this site is listed on '
            '<a href="/versions/">the release history</a>, and the same records are served as '
            '<a href="/versions/index.json">JSON</a> so a script can read them without '
            'parsing a page.</p>'
        )
        page = {
            "fm": {"title": f"{ver} — {r['title']}",
                   "description": r["summary"] or r["title"]},
            "url": url,
            "crumb": f' / <a href="/versions/">versions</a> / {html.escape(ver)}',
            "nav_match": "/ledger/",
            "src_md": (f"# {ver} — {r['title']}\n\n{r['summary']}\n\n"
                       f"- Released: {r['date']}\n- Built from commit: `{r['commit']}`\n"
                       f"- Reconstructed: {'yes' if r.get('reconstructed') else 'no'}\n"),
        }
        target = out_dir / url.strip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page_html(page, ctx, body))
        twin = page["src_md"]
        if LICENCE_STAMP not in twin:
            twin += f"\n---\n\n{LICENCE_STAMP}\n"
        (target.parent / "index.md").write_text(twin)
        made[url] = page["fm"]["title"]
    (out_dir / "versions" / "index.json").write_text(json.dumps(RELEASES, indent=2) + "\n")
    return made


def nav_html(current):
    items = []
    for label, href, subs in NAV:
        here = href == current or any(s_href == current for _, s_href in subs)
        cls = "nl here" if here else "nl"
        if not subs:
            items.append(f'<div class="ni"><a class="{cls}" href="{href}">{html.escape(label)}</a></div>')
            continue
        sub = "".join(
            f'<a class="sl{" here" if s_href == current else ""}" href="{s_href}">{html.escape(s_label)}</a>'
            for s_label, s_href in subs
        )
        items.append(
            f'<div class="ni ni-has"><a class="{cls}" href="{href}">{html.escape(label)}'
            '<span class="caret">&#9662;</span></a>'
            f'<div class="sub">{sub}</div></div>'
        )
    # The parent link points at a page, never at a domain: a domain link is a
    # referral rather than a composition, and the estate records that as its one
    # defect. check_composition_links enforces it.
    return (
        '<nav class="site"><div class="row">'
        '<a class="brand" href="/">store<span>.sgit.ai</span></a>'
        '<a class="parent" href="https://sgit.ai/llms.txt" rel="noopener" '
        'title="sgit.ai — the platform this sells instances of. The free public library lives there">'
        '&#8599; part of <b>sgit.ai</b></a>'
        '<span class="stage-pill">every offer here is an instance</span>'
        f'<a class="ver" href="/versions/{SITE["version"]}/" '
        f'title="What changed in {SITE["version"]}, and the commit it was built from">'
        f'{SITE["version"]}</a>'
        '<button class="nav-toggle" type="button" aria-expanded="false" aria-label="Menu">Menu</button>'
        '<div class="nav-items">' + "".join(items) + "</div>"
        '<a class="gh" href="https://github.com/SGit-AI/SGit-AI__Website__Store" rel="noopener">&#9733; Source</a>'
        "</div></nav>"
    )


def footer_html():
    return f"""<footer class="site"><div class="cols">
  <div>
    <div class="brandline">store<span>.sgit.ai</span></div>
    <p class="nonaff"><b>{LICENCE_TO_OPERATE.capitalize()}.</b> This is where you buy one.
       Six offers, four of them with a price and a code, two of them listed and not yet buyable.
       <b>The paid thing is not access and it is not customisation. It is independence.</b></p>
    <p>Nothing here is a compliance assessment, nothing here is a mark of conformity to any standard, and no opinion here is
       personal: <b>the company issues every opinion</b>, and the person who sells is never the
       person who signs. Outputs are model generated and marked as such.</p>
    <p class="licence">{LICENCE_STAMP} The code that builds it is Apache-2.0.</p>
    <p class="verline">site <a href="/versions/">{SITE['version']}</a> &middot;
       <a href="/ledger/">the ledger</a> &middot; <a href="/disclosures/">what we do not say</a> &middot;
       <a href="index.md" title="The same page as plain markdown">this page as markdown</a></p>
  </div>
  <div>
    <h4>The offers</h4>
    <a href="/offers/">All six, side by side</a>
    <a href="/offers/#the-two-add-ons">The two add-ons</a>
    <a href="/audiences/">Who each one is for</a>
    <a href="/catalogue/">What is not for sale yet</a>
  </div>
  <div>
    <h4>Paying</h4>
    <a href="/paying/">The two rails</a>
    <a href="/paying/#why-a-link-and-not-a-card-reader">Why a link, not a reader</a>
    <a href="/booking/">Booking a person</a>
  </div>
  <div>
    <h4>Evidence</h4>
    <a href="/ledger/">Every claim, with its state</a>
    <a href="/disclosures/">What we do not say, and why</a>
    <a href="/dev-packs/">The dev packs</a>
    <a href="/versions/">Release history</a>
  </div>
</div>
<div class="footnote"><p>No analytics. No cookies. No third-party fonts, scripts or CDN &mdash; every byte of this
site is served from this domain, and <b>no page here opens a network connection at all</b>. A build check holds that
line. Paying happens on the payment provider&rsquo;s own pages, which is the only place a card number should ever be
typed: nothing on this site collects one. Prices are in pounds &mdash; pricing in euros while settling in pounds adds
about two per cent.</p></div>
</footer>"""


def page_html(page, ctx, body):
    fm = page["fm"]
    desc = fm.get("description", "")
    toc = ""
    if fm.get("toc") and len(ctx["toc"]) > 2:
        links = "".join(
            f'<a class="lv{lv}" href="#{anchor}">{html.escape(text)}</a>'
            for lv, anchor, text in ctx["toc"] if lv == 2
        )
        toc = f'<aside class="toc"><b>On this page</b>{links}</aside>'
    prefix = rel_prefix(page["url"])
    return relativise(f"""<!doctype html>
<html lang="en" data-root="{prefix}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{html.escape(fm['title'])} &mdash; {html.escape(SITE['title'])}</title>
<meta name="description" content="{html.escape(desc)}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{SITE['base']}{page['url']}">
<meta property="og:type" content="{'website' if page['url'] == '/' else 'article'}">
<meta property="og:site_name" content="{SITE['domain']}">
<meta property="og:url" content="{SITE['base']}{page['url']}">
<meta property="og:title" content="{html.escape(fm['title'])}">
<meta property="og:description" content="{html.escape(desc)}">
<meta name="twitter:card" content="summary">
<link rel="alternate" type="text/markdown" href="index.md" title="This page as markdown">
<link rel="stylesheet" href="/assets/site.css">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<script src="/assets/site.js" defer></script>
</head>
<body>
{nav_html(page['nav_match'])}
<div class="disclosure-strip"><div class="row"><b>{MODEL_GENERATED}</b>
Nothing on this site is a compliance assessment, and no page claims conformity to any standard.
<a href="/disclosures/">What we do not say, and why</a> &middot;
<a href="/ledger/">how every claim here is evidenced</a></div></div>
<main class="doc{' doc-wide' if fm.get('wide') else ''}">
<p class="crumb"><a href="/">store.sgit.ai</a>{page['crumb']}</p>
<h1>{html.escape(fm['title'])}</h1>
{f'<p class="lead">{inline(fm["lead"], ctx)}</p>' if fm.get('lead') else ''}
{toc}
{body}
<p class="pagenav"><a href="/offers/">The six offers &rarr;</a>
<a href="/ledger/">Every claim on this site, with its state &rarr;</a>
<a href="/disclosures/">What we do not say &rarr;</a></p>
</main>
{footer_html()}
</body>
</html>
""", prefix)


# ------------------------------------------------------------------ build ----


def read_page(path):
    text = path.read_text()
    if not text.startswith("---"):
        raise SystemExit(f"build: {path} has no front-matter")
    _, fm_text, body = text.split("---", 2)
    fm = yaml_load(fm_text)
    rel = path.relative_to(CONTENT)
    slug = str(rel.with_suffix("")).replace("index", "").strip("/")
    url = "/" + (slug + "/" if slug else "")
    return {"path": path, "fm": fm, "body": body.lstrip("\n"), "url": url, "src_md": text}


def build(out_dir):
    out_dir = Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    claims = yaml_load((DATA / "claims.yml").read_text())
    for c in claims:
        c["date_label"] = c.get("date", "")
    claims_by_id = {c["id"]: c for c in claims}

    pages = sorted((read_page(p) for p in CONTENT.rglob("*.md")),
                   key=lambda p: (p["fm"].get("order", 500), p["url"]))
    page_urls = {str(p["path"]): p["url"] for p in pages}
    page_titles = {str(p["path"]): p["fm"]["title"] for p in pages}

    ctx_shared = {
        "claims": claims,
        "claims_by_id": claims_by_id,
        "claim_uses": {},
        "pages": pages,
        "page_urls": page_urls,
        "page_titles": page_titles,
        "external_links": set(),
    }

    # two passes: the first collects claim usage so the ledger can join on it.
    for _ in range(2):
        rendered = {}
        for page in pages:
            fm = page["fm"]
            crumbs = ""
            if page["url"] != "/":
                parts = [x for x in page["url"].strip("/").split("/") if x]
                parent = "/" + parts[0] + "/"
                if len(parts) > 1 and any(q["url"] == parent for q in pages):
                    crumbs = ' / <a href="' + parent + '">' + parts[0] + "</a>"
                elif len(parts) > 1:
                    crumbs = " / " + parts[0]
                crumbs += f" / {html.escape(fm['title'])}"
            page["crumb"] = crumbs
            page["nav_match"] = "/" + (page["url"].strip("/").split("/")[0] + "/" if page["url"] != "/" else "")
            ctx = dict(ctx_shared)
            ctx.update({"page": str(page["path"]), "page_url": page["url"], "fm": fm, "toc": []})
            body = render_markdown(page["body"], ctx)
            rendered[page["url"]] = (page, ctx, body)

    for url, (page, ctx, body) in rendered.items():
        target = out_dir / url.strip("/") / "index.html" if url != "/" else out_dir / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page_html(page, ctx, body))
        twin = page["src_md"].rstrip("\n")
        if LICENCE_STAMP not in twin:
            twin += f"\n\n---\n\n{LICENCE_STAMP}\n"
        (target.parent / "index.md").write_text(twin)

    # static assets, verbatim
    shutil.copytree(ASSETS, out_dir / "assets")
    if FILES.exists():
        shutil.copytree(FILES, out_dir / "files")

    extra = delivery_pages(out_dir, ctx_shared)
    extra.update(release_pages(out_dir, ctx_shared))

    # The pack manifest, machine-readable, beside the page that renders it. The
    # documents are held; the hashes are not, so a reader holding the pack can
    # check their copy without being able to read it here.
    (out_dir / "dev-packs" / "pack.json").write_text(json.dumps(PACK, indent=2) + "\n")

    (out_dir / "CNAME").write_text(SITE["domain"] + "\n")
    (out_dir / ".nojekyll").write_text("")
    (out_dir / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE['base']}/sitemap.xml\n")
    urls = "".join(f"<url><loc>{SITE['base']}{u}</loc></url>"
                   for u in sorted(set(rendered) | set(extra)))
    (out_dir / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + urls + "</urlset>\n"
    )
    (out_dir / "assets" / "site-index.json").write_text(site_index(rendered, claims))
    (out_dir / "llms.txt").write_text(llms_txt(rendered, extra))
    (out_dir / "llms-full.txt").write_text(llms_full(rendered))
    print(f"build: {len(rendered)} pages + {len(extra)} generated, {len(claims)} claims → {out_dir}")
    unused = [c["id"] for c in claims if c["id"] not in ctx_shared["claim_uses"]]
    if unused:
        print("build: claims in the ledger that no page cites: " + ", ".join(unused))
    return rendered


def site_index(rendered, claims):
    """A machine-readable index of the site, beside llms.txt: what each page is,
    every offer with the state of the thing behind it, and every claim with the
    state it earned. The hub syncs from these."""
    pages = []
    for url, (page, ctx, body) in sorted(rendered.items()):
        fm = page["fm"]
        pages.append({
            "url": url,
            "title": fm["title"],
            "description": fm.get("description", ""),
            "lead": re.sub(r"<[^>]+>", "", inline(fm.get("lead", ""), ctx)),
            "headings": [text for lv, _a, text in ctx["toc"]],
            "kind": fm.get("kind", "page"),
        })
    return json.dumps({
        "version": SITE["version"],
        "domain": SITE["domain"],
        "licence": "CC BY 4.0",
        "pages": pages,
        "offers": [
            {"id": o["id"], "tier": o["tier"], "question": o["question"],
             "price": o["price_label"], "rail": o["rail"], "state": o["state_badge"],
             "delivery": f"/d/{o['id']}/" if o["rail"] != "none" else None}
            for o in OFFERS
        ],
        "claims": [
            {"id": c["id"], "state": c["state"], "date": c.get("date", ""),
             "claim": re.sub(r"[*`]", "", c["claim"])}
            for c in claims
        ],
    }, indent=1)


def llms_txt(rendered, extra):
    lines = [
        f"# {SITE['domain']}",
        f"> site {SITE['version']}",
        "",
        f"> {LICENCE_TO_OPERATE.capitalize()}. This is where you buy one.",
        "> Six offers: four tiers with a price and a code, and two add-ons priced by depth band.",
        "> The paid thing is not access and it is not customisation. It is independence.",
        "",
        "What is sold here is an instance. The free public library lives on the platform site and is",
        "not sold. Prices are in pounds. Two of the six offers do not exist yet and say so on their",
        "own row: the signed-opinion wording has not been written, and the check that proves every",
        "rendered variant carries the same facts has not been built, so the guarantee that would make",
        "the multi-format add-on worth buying is not printed anywhere on this site.",
        "",
        "Nothing here is a compliance assessment and no page claims conformity to any standard. Outputs",
        "are model generated and marked as such. Every finding that reaches a buyer has been reproduced rather",
        "than reviewed: recall-optimised agents run at 0.388 precision, so what is sold is triage and",
        "never raw findings.",
        "",
        "Every factual claim on this site carries one of ten states — exists, measured, read-not-run,",
        "projected, specified-not-built, specified-never-run, built-not-located, a-booking, part-exists,",
        "does-not-exist-yet. The full list is at /ledger/. Every page is also served as markdown at",
        "<page>/index.md. No page on this site opens a network connection.",
        "",
        "Offer identifiers are stable and the host is not: a payment code redirects to /d/<id>/, so this",
        "site can move host without reprinting a card or reissuing a link.",
        f"Licence: {LICENCE_STAMP}",
        "",
        "## Pages",
    ]
    for url, (page, _ctx, _body) in sorted(rendered.items()):
        lines.append(f"- [{page['fm']['title']}]({SITE['base']}{url}): {page['fm'].get('description', '')}")
    lines += ["", "## Offers, and where each code lands"]
    for o in OFFERS:
        where = f"{SITE['base']}/d/{o['id']}/" if o["rail"] != "none" else "no code behind it yet"
        lines.append(f"- `{o['id']}` — {o['price_label']} — {o['question']} — {where}")
    return "\n".join(lines) + "\n"


def llms_full(rendered):
    """The whole site as one markdown document. The estate ships one of these
    beside llms.txt so an agent can read the site without crawling it — and here it
    costs nothing, because markdown is already the source of truth."""
    parts = [
        f"# {SITE['domain']} — the whole site as markdown",
        f"site {SITE['version']} · every claim's verification state is at /ledger/",
        "",
        MODEL_GENERATED,
        "",
        "The gaps are deliberate and they are the point. Two of the six offers do not exist yet; the",
        "documents area is built and holds its own documents pending five checks that have not been",
        "run; and the sentence about what a provider can and cannot read is absent from this site",
        "because six questions about what leaks have not been answered.",
        "",
        LICENCE_STAMP,
        "",
    ]
    for url, (page, _ctx, _body) in sorted(rendered.items()):
        parts += [
            "\n" + "=" * 78,
            f"PAGE {url}  —  {page['fm']['title']}",
            "=" * 78 + "\n",
            page["src_md"].strip(),
        ]
    return "\n".join(parts) + "\n"


def main():
    if "--check" in sys.argv:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "docs"
            build(target)
            diff = dircmp_report(target, OUT)
            if diff:
                print("build --check: docs/ is stale. Run `python3 build.py` and commit.", file=sys.stderr)
                for d in diff[:40]:
                    print("  " + d, file=sys.stderr)
                sys.exit(1)
            print("build --check: docs/ matches the sources.")
        return
    build(OUT)


def dircmp_report(a, b, prefix=""):
    out = []
    cmp = filecmp.dircmp(str(a), str(b))
    out += [f"only in build: {prefix}{x}" for x in cmp.left_only]
    out += [f"only in docs/: {prefix}{x}" for x in cmp.right_only]
    out += [f"differs: {prefix}{x}" for x in cmp.diff_files]
    for sub in cmp.common_dirs:
        out += dircmp_report(Path(a) / sub, Path(b) / sub, prefix + sub + "/")
    return out


if __name__ == "__main__":
    main()
