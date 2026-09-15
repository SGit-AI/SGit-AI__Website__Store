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
    # The store proper, first: fifteen shapes, four levels, and an order.
    ("The policies", "/policies/", [
        ("Which agent do you run?", "/policies/"),
        ("The four levels", "/policies/#the-four-levels"),
        ("Something not on the list", "/p/your-own/"),
        ("The price list", "/offers/"),
        ("Your order", "/cart/"),
    ]),
    ("How buying works", "/how-it-works/", [
        ("The three steps", "/how-it-works/"),
        ("The two rails", "/paying/"),
        ("What a session is", "/booking/"),
        ("What happens after you pay", "/order/"),
    ]),
    ("Who it is for", "/audiences/", [
        ("The three buyers", "/audiences/"),
        ("You run agents today", "/for/agents/"),
        ("You are backing a company", "/for/investors/"),
        ("You are a startup", "/for/startups/"),
    ]),
    ("Evidence", "/ledger/", [
        ("The claim ledger", "/ledger/"),
        ("What we do not say, and why", "/disclosures/"),
        ("What is not for sale yet", "/catalogue/"),
        ("The dev packs", "/dev-packs/"),
        ("The purchase lab", "/lab/"),
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

# The three buyers, and which offers each one buys. A SECOND INDEX over the same
# six records above — it introduces no offer and no price, and check_buyer_groups
# holds it to that. What it changes is the question the site answers first: not
# "what does it cost" but "which of these was built for me".
BUYERS = sorted(yaml_load((DATA / "buyers.yml").read_text()), key=lambda b: b["order"])
BUYERS_BY_ID = {b["id"]: b for b in BUYERS}
OFFERS_BY_ID = {o["id"]: o for o in OFFERS}

# Checked once, here, rather than at each of the four places that resolve an id.
# The mistake this catches has exactly one cause — somebody put a product on a
# buyer page — so the build says that rather than dying of a KeyError forty frames
# down in whichever block happened to render first.
for _b in BUYERS:
    _missing = [i for i in (list(_b["primary"]) + list(_b["also"]) + list(_b["addons"])
                            + [_b["entry"]]) if i not in OFFERS_BY_ID]
    if _missing:
        raise SystemExit(
            f"build: buyer {_b['id']!r} names {', '.join(_missing)}, which is not in "
            "data/offers.yml. A buyer group is an index over the offer list and may not introduce "
            "an offer: if this is a new thing to sell it is priced in offers.yml first, with a "
            "state in the ledger, or it is not real.")

RAILS = {
    "link": ("Payment link", "A link, and a printed code beside it. An online payment, "
                             "so no cross-border rule applies to it."),
    "invoice": ("Deposit by link, balance by invoice", "Above about £1,000 a card stops making "
                                             "sense, so the engagement is invoiced. The deposit "
                                             "is below that threshold. It starts with a conversation."),
    "none": ("Not for sale yet", "There is no code behind this one."),
}


# How each offer can be paid for. Derived from the price rather than chosen: a
# standing payment link carries ONE price, so only the single-priced tier can ever
# have one, a band takes a link issued once the band is fixed, and above about
# £1,000 a card stops making sense at all.
#
# The label a reader sees when no link exists is the honest one rather than a
# greyed-out button that looks broken. `data/offers.yml` carries an empty
# `checkout_url` for every offer today, so today every one of these is the second
# string. Pasting a link into that file is the whole of turning a checkout on.
# (the label on a live button, the label where there is no button). The second is
# short because it sits inside a card that has already said how the offer is paid
# for — repeating the rail sentence under itself is the shell showing through.
# The full reason lives in CHECKOUT_WHY, on the page read with a card in hand.
CHECKOUT = {
    "fixed": ("Pay {price}", "The payment link has not been issued yet"),
    "banded": ("Pay {price}", "A link is issued once the band is fixed"),
    "attached": (None, "Priced against the offer it attaches to"),
    "deposit": ("Pay the {deposit} deposit", "The deposit link has not been issued yet"),
    "conversation": (None, "Start with a conversation"),
    "none": (None, "No code behind this one yet"),
}

# The only hosts a checkout URL may point at. A payment link is a URL printed on a
# card and opened by a stranger's phone, which makes it exactly the kind of thing
# that is worth pinning: a checkout that could be edited into a redirect through
# somewhere else is a phishing page with our prices on it. check_checkout_links
# holds the built output to the same two hosts.
CHECKOUT_HOSTS = ("https://buy.stripe.com/", "https://checkout.stripe.com/")

# One sentence per mode, for the page somebody reads with a card already in hand.
# It answers "why is there no button" before they have to ask it, which is the
# whole reason the control is a sentence rather than a greyed-out rectangle.
CHECKOUT_WHY = {
    "fixed": "One price means one standing payment link, printable on a card.",
    "banded": "A fixed-price link carries one price, and this one is a band — so the link is "
              "issued once the band is fixed for the case.",
    "attached": "This attaches to another offer and is priced against its depth band, so it has "
                "no checkout of its own.",
    "deposit": "The engagement goes by invoice and bank transfer, because above about £1,000 a "
               "card stops making sense. The deposit is below that threshold, so the deposit is a "
               "payment link and the balance is not.",
    "conversation": "Above about £1,000 a card stops making sense, so this one goes by invoice "
                    "and bank transfer after a conversation.",
    "none": "There is no code behind this one.",
}


def checkout_html(o, ctx):
    """The checkout control for one offer: a live button where a link exists, and
    a sentence saying which of the six reasons there is no button where it does
    not. Never both, and never an empty element pretending to be a button.

    A deposit offer is the only one where the button's amount is NOT the offer's
    price, and that is the whole point of the mode: the engagement is invoiced and
    the deposit is a link. The label has to say which of the two it is taking, or
    somebody pays £500 believing they have bought a £10,000 assessment."""
    live, dead = CHECKOUT[o["checkout_mode"]]
    url = (o.get("checkout_url") or "").strip()
    if url and live:
        label = live.format(price=o["price_label"], deposit=o.get("deposit_label", ""))
        return (f'<a class="buy" href="{html.escape(url)}" rel="noopener">'
                f'{html.escape(label)} &rarr;</a>')
    if o["checkout_mode"] == "conversation":
        return f'<a class="buy buy-alt" href="/booking/">{html.escape(dead)} &rarr;</a>'
    return f'<span class="buy buy-off">{html.escape(dead)}</span>'


def offer_card(o, ctx, link=True, anchor_prefix=""):
    # The state chip is built from the offer record rather than from a {{claim:}}
    # shortcode, so nothing registered it as used and the ledger's "where it is
    # said" column stayed blank for every offer claim. Register it here.
    ctx["claim_uses"].setdefault(o["claim"], set()).add(ctx["page"])
    tier = o["tier"]
    label = f"Tier {tier}" if tier != "add-on" else "Add-on"
    rail_name, rail_why = RAILS[o["rail"]]
    href = f"/d/{o['id']}/" if o["rail"] != "none" else ""
    cta = (f'<a class="offer-cta" href="{href}">What arrives, and what does not &rarr;</a>'
           if link and href else
           '<span class="offer-cta offer-cta-off">Nothing to read yet: no wording, no code</span>')
    return (
        f'<div class="offer" id="{anchor_prefix}offer-{o["id"]}">'
        f'<div class="offer-head"><span class="offer-tier">{label}</span>'
        f'<span class="offer-price">{html.escape(o["price_label"])}</span></div>'
        f'<h3 class="offer-q">{html.escape(o["question"])}</h3>'
        f'<p class="offer-gets">{inline(o["gets"], ctx)}</p>'
        f'<p class="offer-state">{chip(o["state_badge"], claim_id=o["claim"])} '
        f'{inline(o["state"], ctx)}</p>'
        f'<p class="offer-rail"><b>{html.escape(rail_name)}.</b> {html.escape(rail_why)}</p>'
        + (f'<p class="offer-deposit"><b>{html.escape(o["deposit_label"])} deposit</b> '
           f'{html.escape(o["deposit_why"])}.</p>' if o.get("deposit_label") else "")
        + f'<p class="offer-foot">{checkout_html(o, ctx)}{cta}</p>'
        "</div>"
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


# ------------------------------------------------------------- the buyers ----
# Three doors on the home page, a routing table on the offer page, and one page
# per buyer at /for/<id>/. All three render from data/buyers.yml and join to
# data/offers.yml, so a group cannot list an offer that does not exist and an
# offer cannot quietly belong to a group the ledger has not seen.

def buyer_offer_ids(b):
    """Every offer this buyer is shown, in the order it is shown: the tiers built
    for them, then the tiers that serve them anyway, then the add-ons."""
    return list(b["primary"]) + list(b["also"]) + list(b["addons"])


def block_buyers(ctx):
    doors = []
    for b in BUYERS:
        tiers = [OFFERS_BY_ID[i] for i in (b["primary"] or b["also"])]
        prices = " &middot; ".join(
            f'<b>{"Tier " + o["tier"] if o["tier"] != "add-on" else "Add-on"}</b> '
            f'{html.escape(o["price_label"])}' for o in tiers)
        built = ("" if b["primary"] else
                 '<span class="door-warn">Nothing here was built pointing this way</span>')
        doors.append(
            f'<a class="door" href="/for/{b["id"]}/">'
            f'<span class="door-n">{b["order"]}</span>'
            f'<h3>{html.escape(b["name"])}</h3>'
            f'<p class="door-q">&ldquo;{html.escape(b["arrives_with"])}&rdquo;</p>'
            f'<p class="door-who">{inline(b["who"], ctx)}</p>'
            f'<p class="door-offers">{prices}</p>{built}'
            f'<span class="go">What this one buys &rarr;</span></a>'
        )
    return '<div class="doors">' + "".join(doors) + "</div>"


def block_offers_by_buyer(ctx):
    """The same six offers, indexed by who is buying rather than by what they
    cost. A table rather than cards, because the cards are on the buyer's own page
    and one id cannot be rendered twice on one page."""
    rows = []
    for b in BUYERS:
        offers = [OFFERS_BY_ID[i] for i in buyer_offer_ids(b)]
        listed = ", ".join(
            f'<a href="/d/{o["id"]}/"><code>{o["id"]}</code></a>' if o["rail"] != "none"
            else f'<code>{o["id"]}</code>' for o in offers)
        built = (", ".join(f'<code>{i}</code>' for i in b["primary"])
                 if b["primary"] else '<span class="dim">none &mdash; see the page</span>')
        # Register the market claim against the page that renders this table, so the
        # ledger's "where it is said" column joins on a page a reader can click
        # rather than on a data file they cannot.
        cid = b["opportunity_claim"]
        ctx["claim_uses"].setdefault(cid, set()).add(ctx["page"])
        rows.append(
            f'<tr><td><a href="/for/{b["id"]}/"><b>{html.escape(b["short"])}</b></a>'
            f'<br><span class="small dim">&ldquo;{html.escape(b["arrives_with"])}&rdquo;</span></td>'
            f'<td class="small">{listed}</td><td class="small">{built}</td>'
            f'<td class="small">{chip(ctx["claims_by_id"][cid]["state"], claim_id=cid)}</td></tr>'
        )
    return (
        '<div class="tablewrap"><table><thead><tr><th>Who is buying</th>'
        '<th>What they are shown</th><th>Built for them</th><th>The market, evidenced</th>'
        '</tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>"
        '<p class="small dim">Three groups, six offers, and no seventh: this is an index over '
        'the price list, not an extension of it. The middle column is what each group is shown; '
        'the third is what was actually built pointing at them, which for one of the three is '
        'nothing.</p>'
    )


def block_lab_views(ctx):
    """The five prototypes, with what each one is testing and what is wrong with
    it. The third column is the load-bearing one: five options presented with only
    their strengths is a menu, not an experiment."""
    rows = []
    for v in LAB_VIEWS:
        rows.append(
            f'<tr><td><a href="/lab/{v["id"]}/"><b>{html.escape(v["name"])}</b></a>'
            f'<br><span class="small dim">{html.escape(v["one_line"])}</span></td>'
            f'<td class="small">{html.escape(v["tests"])}</td>'
            f'<td class="small">{html.escape(v["risk"])}</td></tr>')
    return ('<div class="tablewrap"><table><thead><tr><th>The prototype</th>'
            '<th>What it is testing</th><th>What is wrong with it</th>'
            '</tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>")


def block_brief_model(ctx):
    """The option model itself, rendered from the same file the configurator reads.
    Published because a page that asks somebody twenty questions owes them the list
    of questions before they start, and because the weights are what move the
    price — a weighting a reader cannot see is a price a reader cannot check."""
    rows = []
    for s in BRIEF["sections"]:
        rows.append(
            f'<tr><td><b>{s["n"]}. {html.escape(s["title"])}</b>'
            f'<br><span class="small dim">{html.escape(s["question"])}</span></td>'
            f'<td class="num">{len(s["options"])}</td>'
            f'<td class="num">{"pick one" if s["kind"] == "single" else "×" + str(s["weight"])}</td>'
            f'<td class="small">{html.escape(s["why"])}</td></tr>')
    bands = "".join(
        f'<tr><td class="num">{("up to " + str(b["up_to"])) if b["up_to"] < 999 else "above that"}</td>'
        f'<td><code>{b["offer"]}</code> &mdash; <b>{html.escape(OFFERS_BY_ID[b["offer"]]["price_label"])}</b></td>'
        f'<td class="small">{html.escape(b["says"])}</td></tr>' for b in BRIEF["bands"])
    scen = "".join(
        f'<tr><td><b>{html.escape(s["label"])}</b><br>'
        f'<span class="small dim">{html.escape(s["note"])}</span></td>'
        f'<td class="small">{html.escape(BUYERS_BY_ID[s["track"]]["short"])}</td>'
        f'<td class="small num">{len(s["surfaces"])} / {len(s["grants"])} / {len(s["mandates"])}</td></tr>'
        for s in BRIEF["scenarios"])
    return (
        '<div class="tablewrap"><table><thead><tr><th>Section</th><th class="num">Options</th>'
        '<th class="num">Weight</th><th>Why it is asked</th></tr></thead><tbody>'
        + "".join(rows) + "</tbody></table></div>"
        '<h3 id="where-a-total-lands">Where a total lands</h3>'
        '<div class="tablewrap"><table><thead><tr><th class="num">Weighted total</th>'
        '<th>The tier it names</th><th>What that band is</th></tr></thead><tbody>'
        + bands + "</tbody></table></div>"
        '<h3 id="the-five-prebaked-starts">The five prebaked starts</h3>'
        '<div class="tablewrap"><table><thead><tr><th>Scenario</th><th>Track</th>'
        '<th class="num">Surfaces / grants / mandates</th></tr></thead><tbody>'
        + scen + "</tbody></table></div>")


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
    "buyers": block_buyers,
    "offers-by-buyer": block_offers_by_buyer,
    "lab-views": block_lab_views,
    "brief-model": block_brief_model,
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

def _money(pence):
    return "£" + format(pence / 100, ",.2f").rstrip("0").rstrip(".")


def delivery_pages(out_dir, ctx_shared):
    made = {}
    for o in OFFERS:
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
            + f"<ul>{withheld}</ul>"
            # The deposit is a SECOND amount on this page, so it gets a section of
            # its own with both halves. A page that takes £500 against a £10,000
            # engagement and only says what the deposit buys is the half that gets
            # somebody into trouble — the same rule the offer body already follows.
            + ('' if not o.get("deposit_label") else
               '<h2 id="the-deposit">The deposit</h2>'
               f'<p><b>{html.escape(o["deposit_label"])}, by payment link.</b> '
               f'{inline(o["deposit_why"], ctx)}.</p>'
               '<h3 id="what-the-deposit-does">What the deposit does</h3><ul>'
               + "".join(f"<li>{inline(x, ctx)}</li>" for x in o["deposit_says"]) + "</ul>"
               '<h3 id="what-it-does-not-do">What it does not do</h3><ul>'
               + "".join(f"<li>{inline(x, ctx)}</li>" for x in o["deposit_not"]) + "</ul>")
            # What comes off the card now, and what is owed when the work lands. Only
            # on the levels that take a deposit, because on the others there is one
            # amount and a second row saying "£0 later" is noise.
            + ('' if (o.get("pay_now_pct") or 100) >= 100 else
               '<h2 id="what-is-taken-when">What is taken, and when</h2>'
               '<div class="tablewrap"><table><tbody>'
               '<tr><th>On the order</th><td><b>'
               + _money(o["price_min"] * o["pay_now_pct"] // 100)
               + '</b> &mdash; a fifth</td></tr>'
               '<tr><th>On delivery</th><td>'
               + _money(o["price_min"] - o["price_min"] * o["pay_now_pct"] // 100)
               + ', invoiced when the work is in your hands</td></tr>'
               "</tbody></table></div>"
               '<p class="small dim">This level has never run for a paying buyer, and a deposit is '
               'how that is sold honestly from a card: neither side carries the whole amount before '
               'anybody has done anything. <b>The split belongs to the offer and not to the rail</b> '
               '&mdash; a card tapped at the stand takes the same deposit as a link on a phone.</p>')
            # Gap 2 of the 15 September brief: this page said "corrected against your
            # situation" and never said how the situation reaches us, while telling the
            # buyer nobody would interview them — which left them with no route at all.
            + ('' if o["id"] != "t3" else
               '<h2 id="what-you-do">What you do</h2>'
               '<p><b>Nobody needs access to your environment and you send us no credentials.</b> '
               'We send a prompt, <b>you run it where the agent runs</b>, and you send back what it '
               'printed. The mandate is corrected against that.</p>'
               '<div class="tablewrap"><table><tbody>'
               '<tr><th>1</th><td>You buy this level. Nothing is scheduled and nobody waits.</td></tr>'
               '<tr><th>2</th><td>You paste the prompt to the agent, in the environment it actually '
               'runs in. It reads its own configuration and prints a table.</td></tr>'
               '<tr><th>3</th><td>You send back what it printed. One table &mdash; no credentials, '
               'no logs, no access.</td></tr>'
               '<tr><th>4</th><td>The corrected vault comes back, with a written note of what '
               'changed and why.</td></tr>'
               "</tbody></table></div>"
               '<p class="small dim">The result is computed on your own machine and sent back in '
               'bands rather than as raw counts, because a connector list on its own is '
               'identifying. <b>The prompt reads and prints; it does not act</b>, and its last line '
               'says so. The whole of it is on '
               '<a href="/how-it-works/">the page that explains buying</a>, and again on your own '
               'page after you pay.</p>')
            + '<h2 id="how-to-buy-this">How to buy this</h2>'
            f'<p class="offer-foot">{checkout_html(o, ctx)}</p>'
            f'<p class="small dim">The code on the card redirects here, and this page says what '
            f'arrives before anything is paid. {html.escape(CHECKOUT_WHY[o["checkout_mode"]])} '
            f'<a href="/paying/">The two rails, and why they never meet</a>.</p>' 
            '<div class="note"><p><b>Everything on this page is model generated unless it '
            'says otherwise, and it is marked as such where it is delivered.</b> '
            'Nothing here is a compliance assessment and nothing here is a mark of conformity &mdash; '
            'neither word applies and neither appears on the deliverable. '
            'Where a finding reaches you, it has been reproduced first: '
            'recall-optimised agents run at 0.388 precision, so what is sold is triage '
            'and never raw findings. {{claim:precision-0388}}</p></div>'
            # No pagenav here: page_html already appends one, and two identical
            # rows of arrows at the foot of a page is the shell showing through.
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
                f"- How it is paid: {rail_name}\n"
                f"- Checkout: {(o.get('checkout_url') or '').strip() or CHECKOUT_WHY[o['checkout_mode']]}\n"
                + (f"- Deposit: {o['deposit_label']} by payment link, balance invoiced\n"
                   if o.get("deposit_label") else "")
                + f"- What is true of it today: {o['state']}\n\n"
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


# ------------------------------------------------------------------ the shop ----
# The store proper: fifteen Agent Behaviour Policy shapes, four levels each, a
# cart and two payment rails.
#
# WHERE THE CATALOGUE COMES FROM. riskmandate.ai publishes the shapes; this site
# promotes them at build time into data/abp-catalogue.json with the source URL, a
# retrieval time and a content hash. It is not fetched at runtime because no page
# here opens a network connection — so a push to riskmandate.ai is live here on
# the next build rather than on the next page load, and `tools/promote_abp.py`
# is the one command that moves it.
#
# WHAT IS SOLD, AND WHAT IS NOT. The templates are free and public on
# riskmandate.ai, with published read keys, and this site says so rather than
# pretending otherwise. What is priced here is a template with the mandate
# corrected, a name on the licence and no public key — and at the two upper levels,
# the correction done with you rather than by you.

ABP = json.loads((DATA / "abp-catalogue.json").read_text())
# The prompt a level-three buyer runs, kept as a text file rather than a YAML
# string: it is the thing they paste, and a paste-able artefact should live
# somewhere it can be read and diffed without a parser in the way.
LEVEL3_PROMPT = (DATA / "level3-prompt.txt").read_text().rstrip()
PRODUCTS = yaml_load((DATA / "products.yml").read_text())
CHECKOUT_RAILS = yaml_load((DATA / "checkout.yml").read_text())
# Each level names the offer it is; the price is joined from data/offers.yml so
# that file stays the only place a price exists.
LEVELS = []
for _l in PRODUCTS["levels"]:
    _o = OFFERS_BY_ID.get(_l["offer"])
    if not _o:
        raise SystemExit(f"build: level {_l['id']!r} names offer {_l['offer']!r}, which is not in "
                         "data/offers.yml. A level is an offer with a description; it cannot name "
                         "a price that does not exist.")
    LEVELS.append(dict(_l, price_label=_o["price_label"], price=_o["price_min"],
                       rail=_o["rail"], state=_o["state_badge"],
                       pay_now_pct=_o.get("pay_now_pct", 100),
                       post_when=_o.get("post_when", ""), post_does=_o.get("post_does", ""),
                       post_key=_o.get("post_key", ""), post_done=_o.get("post_done", ""),
                       post_check=_o.get("post_check", ""),
                       post_url=(_o.get("post_url") or "").strip(),
                       post_carries=_o.get("post_carries") or [],
                       # only the corrected level asks the buyer to run anything
                       prompt=LEVEL3_PROMPT if _l["id"] == "custom" else ""))
LEVELS_BY_ID = {l["id"]: l for l in LEVELS}

# The discount codes. The code itself NEVER reaches the built site: what ships is
# sha256 of the upper-cased code, and the browser hashes what it was handed and
# compares. data/discounts.yml says at length why, and tools/check_site.py greps
# the built output for every code below so that this stays a fact.
DISCOUNTS = yaml_load((DATA / "discounts.yml").read_text())
_seen_codes = set()
for _d in DISCOUNTS:
    _c = str(_d["code"]).strip().upper()
    if _c != _d["code"] or not re.fullmatch(r"[A-Z0-9]{4,24}", _c):
        raise SystemExit(f"build: discount {_d['id']!r} has code {_d['code']!r}. A code is typed "
                         "into an address bar off a printed card, so it is upper case, four to "
                         "twenty-four characters, letters and digits only.")
    if _c in _seen_codes:
        raise SystemExit(f"build: discount code {_d['id']!r} is a duplicate of another code. Two "
                         "records sharing a code means the discount taken cannot be said.")
    _seen_codes.add(_c)
    if not 1 <= int(_d["pct"]) <= 100:
        raise SystemExit(f"build: discount {_d['id']!r} is {_d['pct']} per cent, which is not a "
                         "discount between one and a hundred.")
    _d["hash"] = hashlib.sha256(_c.encode()).hexdigest()
    _bad = [x for x in (_d.get("levels") if isinstance(_d.get("levels"), list) else [])
            if x not in LEVELS_BY_ID]
    if _bad:
        raise SystemExit(f"build: discount {_d['id']!r} names level(s) {', '.join(_bad)}, which "
                         "are not in data/products.yml.")

SHAPE_CODES = PRODUCTS["shape_codes"]
CUSTOM_SHAPE = PRODUCTS["custom_shape"]

# Every promoted shape needs a SKU code, and a code with no shape behind it is a
# code somebody forgot to delete. Checked at load, because a shape that arrives
# upstream without one would otherwise render a tile whose buttons produce
# "ABP-???-V" and nobody would notice until an order arrived.
_uncoded = [s["slug"] for s in ABP["shapes"] if s["slug"] not in SHAPE_CODES]
if _uncoded:
    raise SystemExit(
        f"build: {', '.join(_uncoded)} arrived in the promoted catalogue with no SKU code in "
        "data/products.yml. A shape without a code cannot be ordered: give it one (three "
        "characters, unique) before it reaches a page.")
_orphans = [c for c in SHAPE_CODES if c not in {s["slug"] for s in ABP["shapes"]}]
if _orphans:
    raise SystemExit(f"build: data/products.yml carries SKU codes for {', '.join(_orphans)}, "
                     "which are not in the promoted catalogue. Either the shape was withdrawn "
                     "upstream or the code is stale.")
_dupes = [c for c in set(SHAPE_CODES.values()) if list(SHAPE_CODES.values()).count(c) > 1]
if _dupes:
    raise SystemExit(f"build: duplicate SKU code(s) {', '.join(_dupes)} — two shapes sharing a "
                     "code means an order cannot say which was bought.")


def shop_shapes():
    """Every purchasable shape: the promoted catalogue, plus the one for a
    deployment nobody has profiled. The last one carries its own level list,
    because the first two levels deliver an existing template and for it there is
    not one — which is a fact about the product rather than a packaging choice."""
    out = []
    for s in ABP["shapes"]:
        out.append(dict(s, code=SHAPE_CODES[s["slug"]],
                        levels=[l["id"] for l in LEVELS]))
    out.append({
        "slug": CUSTOM_SHAPE["slug"], "code": CUSTOM_SHAPE["code"],
        "title": CUSTOM_SHAPE["title"], "summary": CUSTOM_SHAPE["summary"],
        "glyph": CUSTOM_SHAPE["glyph"], "family": CUSTOM_SHAPE["family"],
        "url": None, "counts": None, "open_questions": 0,
        "levels": CUSTOM_SHAPE["levels"], "note": CUSTOM_SHAPE["note"],
    })
    return out


SHOP_SHAPES = shop_shapes()


def shop_model(prefix):
    """The model the cart renders from. Every URL is already relative to the page,
    because the site has to work on the custom domain, on a project path, from a
    local directory and inside a frame with no origin."""
    return {
        "schema": 1,
        "storage": "sgit.store.order.v1",
        "root": prefix,
        "sku_prefix": PRODUCTS["meta"]["sku_prefix"],
        "order_prefix": PRODUCTS["meta"]["order_prefix"],
        "levels": [{"id": l["id"], "code": l["code"], "n": l["n"], "name": l["name"],
                    "offer": l["offer"], "price_label": l["price_label"], "price": l["price"],
                    "lede": l["lede"], "pay_now_pct": l["pay_now_pct"],
                    "post_when": l["post_when"], "post_does": l["post_does"],
                    "post_key": l["post_key"], "post_done": l["post_done"],
                    "post_check": l["post_check"], "prompt": l["prompt"],
                    "post_url": l["post_url"], "post_carries": l["post_carries"]}
                   for l in LEVELS],
        # The code is not here and is not anywhere in docs/. See data/discounts.yml.
        "codes": [{"id": d["id"], "hash": d["hash"], "pct": int(d["pct"]),
                   "label": d["label"], "levels": d.get("levels", "all"),
                   "until": str(d["until"])}
                  for d in DISCOUNTS],
        "code_storage": "sgit.store.code.v1",
        "shapes": [{"slug": s["slug"], "code": s["code"], "title": s["title"],
                    "summary": s["summary"], "glyph": s["glyph"], "family": s["family"],
                    "counts": s["counts"], "open_questions": s["open_questions"],
                    "levels": s["levels"]}
                   for s in SHOP_SHAPES],
        "rails": [{"id": r["id"], "n": r["n"], "name": r["name"],
                   "url": (r.get("url") or "").strip(),
                   "ref_param": r["ref_param"], "amount_param": (r.get("amount_param") or ""),
                   "simulated": bool(r.get("simulated")),
                   "kind": r["kind"], "takes": r["takes"], "note": r["note"]}
                  for r in sorted(CHECKOUT_RAILS["rails"], key=lambda r: r["n"])],
    }


def shop_island(prefix):
    return (f'<script type="application/json" id="shop-model">'
            f'{json.dumps(shop_model(prefix), separators=(",", ":"))}</script>')


# Registered here rather than in the BLOCKS literal above, which is defined before
# this section and cannot name a function that does not exist yet.
def block_catalogue(ctx):
    """The grid, rendered by the cart engine. The server-rendered fallback is the
    whole catalogue as a list, because a store that shows nothing without
    JavaScript is a store that shows nothing to a crawler either."""
    rows = "".join(
        f'<li><a href="/p/{s["slug"]}/"><b>{html.escape(s["title"])}</b></a> &mdash; '
        f'{html.escape(s["summary"])}'
        + ("" if not s["counts"] else
           f' <span class="small dim">{s["counts"]["grant"]} it can do, '
           f'{s["counts"]["wanted"]} wanted, {s["counts"]["unbounded"]} with nothing in the way.</span>')
        + "</li>"
        for s in SHOP_SHAPES)
    return (shop_island(rel_prefix(ctx["page_url"]))
            + '<div id="catalogue"><noscript-fallback>'
            + f'<ul class="small">{rows}</ul>'
            + '</noscript-fallback></div>')


def block_levels_table(ctx):
    rows = "".join(
        f'<tr><td class="num">{l["n"]}</td>'
        f'<td><b>{html.escape(l["name"])}</b><br>'
        f'<span class="small dim">{html.escape(l["who"])}</span></td>'
        f'<td class="num"><b>{html.escape(l["price_label"])}</b></td>'
        f'<td class="small">{inline(l["lede"], ctx)}</td>'
        f'<td class="small">{html.escape(l["fulfilment"])}</td></tr>' for l in LEVELS)
    return ('<div class="tablewrap"><table><thead><tr><th class="num"></th><th>Level</th>'
            '<th class="num">Price</th><th>What it is</th><th>Who does it</th>'
            '</tr></thead><tbody>' + rows + "</tbody></table></div>"
            '<p class="small dim">Every level is the same document. What changes is the form it '
            'arrives in and who does the correcting &mdash; and the line between the third and the '
            'fourth is the line between a thing agents do and a thing a person signs.</p>')


BLOCKS["catalogue"] = block_catalogue
BLOCKS["levels-table"] = block_levels_table


# ------------------------------------------------------------------- the lab ----
# Five prototypes of one purchase flow, at /lab/<id>/.
#
# WHAT IS BEING CONFIGURED. The consulting work is two things: a map of the grants
# and mandates of the agents a company already runs, and the policy set that would
# close the gap between them. A team fulfils it — none of it is automated today.
# What these pages do is take the half a buyer already knows and turn it into a
# brief that team can start from, rather than spending a first call assembling it.
#
# SO THE OUTPUT IS A FILE, AND THE FILE IS THE POINT. Everything on these pages
# exists to make one JSON document specific enough to be worth handing over. The
# checkout is downstream of it.
#
# FIVE INTERFACES, ONE MODEL. Every view renders data/brief.yml, runs the same
# arithmetic and emits the same document, which is what makes them an experiment
# rather than five drafts: what is learned from one transfers, and choosing
# between them is choosing an interface rather than a product.
#
# AND NONE OF THEM SELLS ANYTHING. A page that looks like a checkout and is not
# one is the single most dangerous thing this site could publish, so every lab
# page opens by saying what it is, the ledger carries it, and check_lab_is_marked
# fails the release if that sentence goes missing from any of them.

BRIEF = yaml_load((DATA / "brief.yml").read_text())

# Checked at load, like the buyer groups, and for the same reason: every `offer:`
# in the model — in a band, on a deliverable — points at the frozen offer list, and
# an id that does not stops the build with a sentence rather than a KeyError from
# whichever renderer happened to reach it first. This is the one that matters most
# on this site: a band naming an offer nobody priced is a configurator quoting a
# number that exists in no file.
for _sec in BRIEF["sections"] + BRIEF["bands"]:
    for _o in (_sec.get("options") or [_sec]):
        _oid = _o.get("offer")
        if _oid and _oid not in OFFERS_BY_ID:
            raise SystemExit(
                f"build: data/brief.yml refers to offer {_oid!r}, which is not in "
                "data/offers.yml. The configurator prices against the offer list and may not "
                "add to it: a band or a deliverable names a price that was set elsewhere, or "
                "it names nothing.")
for _sc in BRIEF["scenarios"]:
    if _sc["track"] not in BUYERS_BY_ID:
        raise SystemExit(f"build: scenario {_sc['id']!r} is on track {_sc['track']!r}, which is "
                         "not one of the three buyers in data/buyers.yml")
    for _sec in BRIEF["sections"]:
        _known = {_o["id"] for _o in _sec["options"]}
        _named = [_sc[_sec["id"]]] if _sec["kind"] == "single" else (_sc.get(_sec["id"]) or [])
        _bad = [x for x in _named if x not in _known]
        if _bad:
            raise SystemExit(f"build: scenario {_sc['id']!r} selects {', '.join(_bad)} in "
                             f"{_sec['id']!r}, which is not an option there")

LAB_VIEWS = [
    {
        "id": "interview",
        "n": 1,
        "name": "The interview",
        "one_line": "One question per screen, in the order somebody would ask them out loud.",
        "tests": "Whether the story carries. The estate is described in the order a person "
                 "would actually describe it, and the price moves while they talk.",
        "risk": "Five screens is five chances to leave. It hides how much is left, and a buyer "
                "who cannot see the whole shape cannot tell whether it is worth starting.",
    },
    {
        "id": "ladder",
        "n": 2,
        "name": "The ladder",
        "one_line": "Everything on one page, in order, with the ticket pinned beside it.",
        "tests": "Whether seeing the whole thing at once beats being walked through it. "
                 "Closest to an ordinary cart, and the cheapest to be wrong about.",
        "risk": "It looks like a form, and a long page of choices is a page people skim to "
                "the bottom of and price without reading.",
    },
    {
        "id": "board",
        "n": 3,
        "name": "The estate board",
        "one_line": "One card per surface, each carrying what it permits and what it is expected to do.",
        "tests": "Whether the map is the sale. This is the only view where the deliverable and "
                 "the configurator are the same object, so the buyer is already holding a "
                 "rough version of what they would be buying.",
        "risk": "It is the most work to fill in, and an empty board is a worse first screen "
                "than an empty list.",
    },
    {
        "id": "delta",
        "n": 4,
        "name": "The delta",
        "one_line": "Permitted on the left, expected on the right, and the gap filling itself in between.",
        "tests": "Whether the product explains itself. The middle column is the thing being "
                 "sold, computed live from two lists the buyer ticks, so nobody has to be told "
                 "what excess authority means.",
        "risk": "It asks for both halves before it shows anything, and the honest answer to the "
                "right-hand column is often that nothing is written down.",
    },
    {
        "id": "scenario",
        "n": 5,
        "name": "The scenario",
        "one_line": "Start from the shape that looks most like you, then correct it.",
        "tests": "Whether starting from a guess beats starting from nothing. The corrections "
                 "are the signal: what somebody removes from a prefilled estate says more than "
                 "what they add to an empty one.",
        "risk": "A scenario that is nearly right gets accepted whole. The brief records which "
                "one it started from for exactly that reason, and it is still a risk.",
    },
]


def lab_model(prefix):
    """The model the browser gets: the sections, the tracks, the bands, the
    scenarios, and the six offers a band can point at. Compiled here so the page
    and the configurator cannot disagree about what is on sale — and with every
    URL already relative to the page, because the site has to work on a project
    path and inside a frame with no origin."""
    offers = {}
    for o in OFFERS:
        caveat = ""
        if o["state_badge"] in ("absent", "partial", "spec", "unrun", "unlocated"):
            caveat = f'"{o["question"]}" — {o["state"]}'
        offers[o["id"]] = {
            "label": f"Tier {o['tier']}" if o["tier"] != "add-on" else "Add-on",
            "price": o["price_label"],
            "rail": o["rail"],
            "state": o["state_badge"],
            "chip": STATES[o["state_badge"]][0],
            "caveat": caveat,
            "delivery": f"d/{o['id']}/index.html" if o["rail"] != "none" else None,
            # The one offer where the first payable amount is not the price. A brief
            # that lands in the top band should say what actually gets paid first,
            # or the number in the ticket reads as the number on the card.
            "deposit": o.get("deposit_label") or None,
        }
    return {
        "version": SITE["version"],
        "root": prefix,
        "meta": BRIEF["meta"],
        "tracks": BRIEF["tracks"],
        "sections": BRIEF["sections"],
        "bands": BRIEF["bands"],
        "scenarios": BRIEF["scenarios"],
        "offers": offers,
    }


PAY_NOTE = (
    '<h2 id="the-deposit-is-the-offer">Why two of the four take a deposit</h2>'
    '<p><b>Two of the four levels are produced without anybody being scheduled</b>, so they take '
    'the whole price. The other two are somebody\u2019s work, and neither has run for a paying '
    'buyer yet \u2014 so they take <b>a fifth on the order and the rest when the work is in your '
    'hands</b>. £100 of £500; £300 of £1,500.</p>'
    '<p><b>The split belongs to the offer and not to the rail.</b> A card tapped on a terminal at '
    'the stand takes the same deposit as a link opened on a phone, because what is being split is '
    'the risk on a thing that has never run, and that does not change with how the card is read.</p>'
    '<h2 id="a-discount-code">A discount code, and why there is nowhere to type one</h2>'
    '<p><b>A code arrives in the address, not in a field.</b> There is no text input anywhere in '
    'this site\u2019s output and the gate refuses one, so a code is handed over the way a printed '
    'card or a QR at a stand hands it over anyway \u2014 '
    '<code>store.sgit.ai/policies/?code=\u2026</code>. The store recognises it, shows it as a chip '
    'that can be removed, and takes it back out of the address bar, because a screenshot of a '
    'checkout should not carry one.</p>'
    '<p><b>What ships is the hash of the code and never the code.</b> A page that recognised a '
    'code by carrying it would be publishing it the moment it was built, so the browser hashes '
    'what it was handed and compares. That is worth what it is worth and no more: a short code can '
    'be ground out of a hash, and the thing that actually stops a stranger paying nothing is that '
    'a browser does not take money \u2014 a code changes the amount a payment link is issued '
    '<em>for</em>, and the rail decides what is charged.</p>'
    '<p><b>It comes off the price, and the deposit is then taken on what is left.</b> Half off the '
    '\u00a3500 level is \u00a3250, of which \u00a350 is taken now and \u00a3200 on delivery. A '
    'code never moves the split, which is a property of the offer. <b>A code at a hundred per cent '
    'still places an order</b> and still lands on the page that says what happens next \u2014 '
    'which is the whole use of one: the flow can be walked end to end before a single real payment '
    'link exists.</p>'
    '<h2 id="what-the-store-never-sees">What the store never sees</h2>'
    '<p>No name, no contact, no card. There is <b>no form, input, textarea or select anywhere in '
    'this site\u2019s output</b> and a build check holds that line; the provider takes all three '
    'on its own pages and hands back nothing. What travels is the amount and an order reference '
    'carrying the product codes.</p>'
)

POST_SALE_NOTE = (
    '<h2 id="the-key-is-never-on-this-page">The key is never on this page</h2>'
    '<p><b>A vault key is never published and never committed</b>, and a page on this site is a '
    'committed file. So this page says <em>how</em> a key reaches you and never carries one. '
    'Anything that looks like a key on a page like this is a security incident rather than a '
    'convenience, and a build check refuses the release if one lands here.</p>'
    '<h2 id="the-page-after-this-one">The page after this one is not on this site</h2>'
    '<p><b>riskmandate.ai publishes one page per level</b> \u2014 <code>paid-t1</code> to '
    '<code>paid-t4</code> \u2014 and since its v1.19.2 <b>the level-one page is the download '
    'itself</b>: the zip, its size, its sha256, and a check that hashes the file in your own '
    'browser against the hash that shape publishes. Your order above carries a link to the page '
    'for each line you bought.</p>'
    '<p><b>What the link carries is two things and nothing else.</b> Your order reference, which '
    'that page shows back to you and puts in the subject line of every message it offers; and, at '
    'level one only, the shape you bought \u2014 the same slug this store uses at '
    '<code>/p/&lt;slug&gt;/</code>, which is why the two sites keep their slugs in step. Nothing '
    'is posted, there is no callback and no session, and the page is a static file that works with '
    'no parameters at all.</p>'
    '<p><b>Twenty-four hours is the commitment at the three vault levels</b>, and it is theirs '
    'rather than ours: a person follows up within a day of the payment landing. The store said '
    '\u201cone working day\u201d until v0.1.9, which was a day slower than the page the buyer '
    'actually lands on \u2014 two sites promising different things about the same follow-up is '
    'the drift that a shared brief exists to stop, and the number that stands is the one that is '
    'committed to in public.</p>'
    '<h2 id="done-is-a-commit">Done is a commit</h2>'
    '<p>Every level has a definition of done you can check yourself, and at the three vault levels '
    'it is <b>a commit in your own history</b> rather than somebody\u2019s word: the licence file '
    'with your name in it, the corrected mandate and the recomputed delta with the note beside '
    'them, or the record and the sign-off file with a name and a date. <b>You do not have to take '
    'anybody\u2019s word for whether the thing you bought was delivered.</b></p>'
)


# The sentence every lab page has to carry, above the tool. check_lab_is_marked
# holds each page to it: a page that looks like a checkout and takes no money has
# to say which of the two it is before anybody reads further.
LAB_WARNING = "Nothing on this page can be bought"


def lab_note():
    return (
        '<div class="labnote">'
        f'<p><b>{LAB_WARNING}.</b> This is a prototype of a purchase flow, not a purchase '
        'flow. No brief reaches us, no payment link is behind anything here, and which of '
        'the five (if any) becomes the real one is not decided. {{claim:lab-is-a-prototype}}</p>'
        '<p>The work it configures is done by <b>people</b>, and the team specified for it '
        'has never run. Which parts of it could later be done without them is a decision '
        'nobody has taken. {{claim:lab-fulfilment-is-people}}</p>'
        "</div>"
    )


def lab_pages(out_dir, ctx_shared):
    made = {}

    # --- the five prototypes
    for v in LAB_VIEWS:
        url = f"/lab/{v['id']}/"
        prefix = rel_prefix(url)
        ctx = dict(ctx_shared)
        ctx.update({"page": f"lab/{v['id']}", "page_url": url, "fm": {}, "toc": []})
        others = "".join(
            f'<a href="/lab/{x["id"]}/">{html.escape(x["name"])} &rarr;</a>'
            for x in LAB_VIEWS if x["id"] != v["id"])
        body = (
            f'<p class="lead">{html.escape(v["one_line"])}</p>'
            + shortcodes_inline(lab_note(), ctx) +
            '<div class="tablewrap"><table><tbody>'
            f'<tr><th>What it is testing</th><td>{html.escape(v["tests"])}</td></tr>'
            f'<tr><th>What is wrong with it</th><td>{html.escape(v["risk"])}</td></tr>'
            '<tr><th>What it produces</th><td>One JSON brief, identical across all five '
            'prototypes. The interface is the variable; the document is not.</td></tr>'
            "</tbody></table></div>"
            f'<script type="application/json" id="lab-model">'
            f'{json.dumps(lab_model(prefix), separators=(",", ":"))}</script>'
            f'<div id="lab" data-view="{v["id"]}">'
            '<p class="dim">This prototype needs JavaScript. Everything it does happens in '
            'this browser: there is no form on this site and no page here opens a network '
            'connection, so with scripting off there is nothing to fall back to except '
            '<a href="/lab/">the description of what it would do</a>.</p></div>'
            f'<p class="pagenav">{others}<a href="/lab/">All five, compared &rarr;</a></p>'
        )
        page = {
            "fm": {"title": f"{v['name']} — a purchase prototype",
                   "description": f"{v['one_line']} A prototype of the purchase flow for the "
                                  f"grant-and-mandate mapping work. Nothing on it can be bought.",
                   "head_css": "/assets/lab.css", "head_js": "/assets/lab.js",
                   "wide": True},
            "url": url,
            "crumb": f' / <a href="/lab/">lab</a> / {html.escape(v["id"])}',
            "nav_match": "/lab/",
            "src_md": (
                f"# {v['name']}\n\n{v['one_line']}\n\n"
                f"**{LAB_WARNING}.** This is a prototype of a purchase flow, not a purchase "
                "flow. The work it configures is done by people, and the team specified for it "
                "has never run.\n\n"
                f"- What it is testing: {v['tests']}\n- What is wrong with it: {v['risk']}\n"
                "- What it produces: one JSON brief, identical across all five prototypes\n\n"
                "## The model behind all five\n\n"
                + "".join(
                    f"- **{s['title']}** ({s['kind']}, weight {s['weight']}): {s['question']} "
                    f"{len(s['options'])} options\n" for s in BRIEF["sections"])
                + "\n## Where a total lands\n\n"
                + "".join(
                    f"- up to {b['up_to']} weighted: `{b['offer']}` "
                    f"{OFFERS_BY_ID[b['offer']]['price_label']} — {b['says']}\n"
                    for b in BRIEF["bands"])
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


def shape_pages(out_dir, ctx_shared):
    """One page per shape at /p/<slug>/, and the order at /cart/.

    Generated rather than written for the same reason the delivery pages are: a
    hand-written product page is a page that will one day price a level the
    catalogue no longer carries, or promise a template that was withdrawn
    upstream."""
    made = {}
    for s in SHOP_SHAPES:
        url = f"/p/{s['slug']}/"
        prefix = rel_prefix(url)
        ctx = dict(ctx_shared)
        ctx.update({"page": f"p/{s['slug']}", "page_url": url, "fm": {}, "toc": []})
        c = s["counts"]
        counts = ("" if not c else
                  '<div class="tablewrap"><table><thead><tr>'
                  '<th class="num">It can do</th><th class="num">You wanted</th>'
                  '<th class="num">Not wanted</th><th class="num">Nothing in the way</th>'
                  '</tr></thead><tbody><tr>'
                  f'<td class="num">{c["grant"]}</td><td class="num">{c["wanted"]}</td>'
                  f'<td class="num">{c["excess"]}</td><td class="num">{c["unbounded"]}</td>'
                  '</tr></tbody></table></div>'
                  '<p class="small dim">Counts, not a score. An Agent Behaviour Policy describes '
                  'and does not judge: the same policy is dangerous in one deployment and harmless '
                  'in another, so there is no rating on it here or anywhere. The last column is the '
                  'one a control moves.</p>')
        openq = ("" if not s["open_questions"] else
                 '<div class="labnote"><p><b>' + str(s["open_questions"]) +
                 ' open question' + ('' if s["open_questions"] == 1 else 's') + '.</b> '
                 'This shape is read from the vendor&rsquo;s own published pages on a date, not '
                 'measured on the thing itself. The questions those pages could not settle travel '
                 'with the vault rather than being guessed at.</p></div>')
        note = ("" if not s.get("note") else
                f'<div class="labnote"><p>{inline(s["note"], ctx)}</p></div>')
        free = ("" if not s.get("url") else
                '<p>The template for this shape is <b>free and public</b>, with a published read '
                f'key, at <a href="{html.escape(s["url"])}" rel="noopener">riskmandate.ai</a>. '
                'Go and read it before you buy anything here. <b>What is priced below is that '
                'template with the mandate corrected, a name on the licence and no public key</b> '
                '&mdash; and at the upper two levels, the correction done with you rather than by '
                'you.</p>')
        body = (
            f'<p class="lead">{html.escape(s["summary"])}</p>'
            f'{note}{counts}{openq}{free}'
            '<h2 id="the-four-levels">The four levels</h2>'
            + shop_island(prefix) +
            f'<div id="shape-levels" data-shape="{html.escape(s["slug"])}">'
            '<p class="dim">The levels need JavaScript to add to an order. '
            '<a href="/policies/">The catalogue</a> lists what each one is.</p></div>'
            '<p class="pagenav"><a href="/cart/">Your order &rarr;</a>'
            '<a href="/policies/">Every shape &rarr;</a>'
            '<a href="/how-it-works/">How buying works &rarr;</a></p>'
        )
        page = {
            "fm": {"title": s["title"],
                   "description": f"An Agent Behaviour Policy for {s['title']}: "
                                  f"{s['summary'][:120]}",
                   "head_css": "/assets/shop.css"},
            "url": url,
            "crumb": f' / <a href="/policies/">policies</a> / {html.escape(s["slug"])}',
            "nav_match": "/policies/",
            "src_md": (
                f"# {s['title']}\n\n{s['summary']}\n\n"
                + ("" if not c else
                   f"- It can do: {c['grant']}\n- You wanted: {c['wanted']}\n"
                   f"- Not wanted: {c['excess']}\n- Nothing in the way: {c['unbounded']}\n"
                   "\nCounts, not a score.\n")
                + ("" if not s.get("url") else f"\nFree public template: {s['url']}\n")
                + "\n## The four levels\n\n"
                + "".join(
                    f"- `{PRODUCTS['meta']['sku_prefix']}-{s['code']}-{LEVELS_BY_ID[lid]['code']}` "
                    f"\u2014 {LEVELS_BY_ID[lid]['price_label']} \u2014 "
                    f"{LEVELS_BY_ID[lid]['name']}: {LEVELS_BY_ID[lid]['lede']}\n"
                    for lid in s["levels"])
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

    # ------------------------------------------------------------ the order
    url = "/cart/"
    prefix = rel_prefix(url)
    ctx = dict(ctx_shared)
    ctx.update({"page": "cart", "page_url": url, "fm": {}, "toc": []})
    body = (
        '<p class="lead">Everything you have picked, what it costs, and the two ways to pay. '
        '<b>Nothing on this page is collected by us</b> &mdash; your order lives in this browser, '
        'and your name, your contact and your card are taken by the payment provider on its own '
        'pages.</p>'
        + shop_island(prefix) +
        '<div id="cart"><p class="dim">Your order needs JavaScript. '
        '<a href="/policies/">The catalogue</a> lists everything and what it costs.</p></div>'
        '<h2 id="what-reaches-the-provider">What reaches the payment provider</h2>'
        '<p><b>The amount, and your order reference. Nothing else.</b> The reference carries the '
        'codes for what you picked, so matching it against the name and contact the provider '
        'captured gives the whole order. There is no account here, no cookie, and '
        '<b>no form, input or field anywhere on this site</b> &mdash; a build check holds that, '
        'which is what makes it a fact rather than a promise.</p>'
        '<p>The catalogue is not duplicated inside either provider. Sixty-two codes maintained '
        'twice is sixty-two codes that will one day disagree, so the provider takes an amount and '
        'a reference and neither side has to know about the other.</p>'
        '<p class="pagenav"><a href="/policies/">Every shape &rarr;</a>'
        '<a href="/how-it-works/">How buying works &rarr;</a></p>'
    )
    page = {
        "fm": {"title": "Your order",
               "description": "What you have picked, what it costs, your order reference, and the "
                              "two payment rails. Nothing on this page is collected by us.",
               "head_css": "/assets/shop.css"},
        "url": url,
        "crumb": " / your order",
        "nav_match": "/policies/",
        "src_md": ("# Your order\n\nYour order lives in your own browser. The payment provider "
                   "takes your name, your contact and your card on its own pages; what this site "
                   "hands it is the amount and an order reference carrying the codes for what you "
                   "picked.\n\n## The levels\n\n"
                   + "".join(f"- `{l['code']}` \u2014 {l['price_label']} \u2014 {l['name']}\n"
                             for l in LEVELS)),
    }
    target = out_dir / "cart" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page_html(page, ctx, body))
    twin = page["src_md"] + f"\n---\n\n{LICENCE_STAMP}\n"
    (target.parent / "index.md").write_text(twin)
    made[url] = page["fm"]["title"]

    # ------------------------------------------------------------ paying
    for slug, title, desc, crumb, mount, intro, tail_md in (
        ("pay", "Paying",
         "What is due now, what is due on delivery, and the rails. Nothing is collected here: "
         "the provider takes your name and card on its own pages.",
         " / paying",
         "pay",
         '<p class="lead">What is due now, and what is due when the work is in your hands. '
         '<b>Nothing on this page collects anything</b> \u2014 there is no form, no field and no '
         'account, and a card is typed on the provider\u2019s own pages.</p>',
         "# Paying\n\nThe amount due now and the amount due on delivery, and the rails that "
         "take them. The store collects nothing: the provider takes the name, the contact and the "
         "card on its own pages, and what reaches it is the amount and an order reference.\n"),
        ("order", "What happens now",
         "Read after paying: the order reference, what arrives and when, what you do next, how a "
         "key reaches you, and what done means for each level.",
         " / what happens now",
         "order",
         '<p class="lead">Your order, and <b>what happens now</b> \u2014 which is a different '
         'question from what you were buying, and so this is a different page from the one you '
         'read before paying.</p>',
         "# What happens now\n\nRead after paying. Per line: what arrives and when, what you do "
         "next, how a key reaches you, and what done means.\n\n**A vault key never appears on "
         "this page.** A key is never published and never committed, and a page is a committed "
         "file, so the page says how the key arrives and never carries it.\n"),
    ):
        u2 = f"/{slug}/"
        pre2 = rel_prefix(u2)
        c2 = dict(ctx_shared)
        c2.update({"page": slug, "page_url": u2, "fm": {}, "toc": []})
        b2 = (intro + shop_island(pre2) +
              f'<div id="{mount}"><p class="dim">This page needs JavaScript. '
              '<a href="/policies/">The catalogue</a> lists everything and what it costs.</p></div>'
              + (POST_SALE_NOTE if slug == "order" else PAY_NOTE))
        pg2 = {
            "fm": {"title": title, "description": desc,
                   "head_css": "/assets/shop.css"},
            "url": u2, "crumb": crumb, "nav_match": "/policies/",
            "src_md": tail_md,
        }
        t2 = out_dir / slug / "index.html"
        t2.parent.mkdir(parents=True, exist_ok=True)
        t2.write_text(page_html(pg2, c2, b2))
        (t2.parent / "index.md").write_text(tail_md + f"\n---\n\n{LICENCE_STAMP}\n")
        made[u2] = title
    return made


# ----------------------------------------------------------- buyer pages ----
# One page per buyer at /for/<id>/. The offer page is the price ladder; these are
# the same six offers read by who is climbing it, which is the question somebody
# actually arrives with. Generated rather than written for the same reason the
# delivery pages are: a hand-written buyer page is a page that will one day offer
# a tier the offer list no longer contains, or soften a state the ledger holds.
#
# The third page is the one worth reading. Its `primary` list is empty, so it says
# on its own face that nothing here was built pointing at that buyer, and it says
# it above the offers rather than below them.

def buyer_pages(out_dir, ctx_shared):
    made = {}
    for b in BUYERS:
        url = f"/for/{b['id']}/"
        ctx = dict(ctx_shared)
        ctx.update({"page": f"for/{b['id']}", "page_url": url, "fm": {}, "toc": []})
        offers = [OFFERS_BY_ID[i] for i in buyer_offer_ids(b)]
        entry = OFFERS_BY_ID[b["entry"]]
        others = "".join(
            f'<a href="/for/{x["id"]}/">{html.escape(x["short"])} &rarr;</a>'
            for x in BUYERS if x["id"] != b["id"])

        not_built = ("" if b["primary"] else
                     '<div class="warnbox"><p><b>Nothing on the offer list was built pointing '
                     'this way.</b> Everything below was built for one of the other two buyers, '
                     'and what is on offer here is the same work run in the opposite direction. '
                     'That is a real gap and it is stated here rather than papered over with a '
                     'heading: there is no seventh product behind this page. '
                     '{{claim:startup-offer-is-reverse-only}}</p></div>')
        market_chip = chip(ctx["claims_by_id"][b["opportunity_claim"]]["state"],
                           claim_id=b["opportunity_claim"])
        ctx["claim_uses"].setdefault(b["opportunity_claim"], set()).add(ctx["page"])

        groups = []
        if b["primary"]:
            groups.append(("Built for this question", [OFFERS_BY_ID[i] for i in b["primary"]]))
        if b["also"]:
            groups.append(("Built for somebody else, and it still answers yours",
                           [OFFERS_BY_ID[i] for i in b["also"]]))
        if b["addons"]:
            groups.append(("Attaches to whichever of those you buy",
                           [OFFERS_BY_ID[i] for i in b["addons"]]))
        cards = "".join(
            f'<h2 id="{slugify(label)}">{html.escape(label)}</h2>'
            '<div class="offers">'
            + "".join(offer_card(o, ctx, anchor_prefix=f"{b['id']}-") for o in group)
            + "</div>"
            for label, group in groups)

        body = (
            f'<p class="lead">{inline(b["who"], ctx)} '
            f'You arrive asking: <b>&ldquo;{html.escape(b["arrives_with"])}&rdquo;</b></p>'
            f'{not_built}'
            '<h2 id="what-the-market-looks-like">What the market looks like here</h2>'
            f'<p>{market_chip} {inline(b["opportunity"], ctx)}</p>'
            '<h2 id="what-you-are-actually-buying">What you are actually buying</h2>'
            f'<p>{inline(b["buying"], ctx)}</p>'
            f'<p class="small dim">Start at <a href="/d/{entry["id"]}/">'
            f'{"tier " + entry["tier"] if entry["tier"] != "add-on" else "the add-on"} '
            f'&mdash; {html.escape(entry["price_label"])}</a> unless you already know you need '
            'more than it. Every card below says what arrives and what does not before it says '
            'how to pay.</p>'
            f'{cards}'
            '<h2 id="what-you-are-not-buying">What you are not buying</h2>'
            '<ul>' + "".join(f"<li>{inline(x, ctx)}</li>" for x in b["not_buying"]) + "</ul>"
            '<div class="note"><p><b>Nothing on this page is a compliance assessment, and no '
            'page here claims conformity to any standard.</b> Outputs are model generated and '
            'marked as such where they are delivered. Where a finding reaches you it has been '
            'reproduced first &mdash; recall-optimised agents run at 0.388 precision, so what is '
            'sold is triage and never raw findings. {{claim:precision-0388}}</p></div>'
            f'<p class="pagenav">{others}<a href="/offers/">All six, side by side &rarr;</a></p>'
        )
        body = shortcodes_inline(body, ctx)
        page = {
            "fm": {"title": b["name"],
                   "description": f"{b['who']} What this buyer is shown, what was built for them, "
                                  f"what was not, and what none of it is."},
            "url": url,
            "crumb": f' / <a href="/audiences/">who it is for</a> / {html.escape(b["id"])}',
            "nav_match": "/audiences/",
            "src_md": (
                f"# {b['name']}\n\n{b['who']}\n\nYou arrive asking: \u201c{b['arrives_with']}\u201d\n\n"
                + ("" if b["primary"] else
                   "**Nothing on the offer list was built pointing this way.** Everything below was "
                   "built for one of the other two buyers and is run in the opposite direction. "
                   "There is no seventh product behind this page.\n\n")
                + f"## What the market looks like here\n\n{b['opportunity']}\n\n"
                + f"## What you are actually buying\n\n{b['buying']}\n\n"
                + "## The offers you are shown\n\n"
                + "".join(
                    f"- `{o['id']}` \u2014 {'Tier ' + o['tier'] if o['tier'] != 'add-on' else 'Add-on'}"
                    f" \u2014 {o['price_label']} \u2014 {o['question']}"
                    f" \u2014 {(o.get('checkout_url') or '').strip() or CHECKOUT_WHY[o['checkout_mode']]}\n"
                    for o in offers)
                + "\n## What you are not buying\n\n"
                + "".join(f"- {x}\n" for x in b["not_buying"])
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
        '<a class="cartlink" href="/cart/">Your order '
        '<b data-cart-count hidden></b><span data-cart-total></span></a>'
        '<a class="gh" href="https://github.com/SGit-AI/SGit-AI__Website__Store" rel="noopener">&#9733; Source</a>'
        "</div></nav>"
    )


def footer_html():
    return f"""<footer class="site"><div class="cols">
  <div>
    <div class="brandline">store<span>.sgit.ai</span></div>
    <p class="nonaff"><b>{LICENCE_TO_OPERATE.capitalize()}.</b> This is where you buy one.
       Six offers, four of them with a price and a code, two of them listed and not yet buyable,
       grouped by which of three buyers each was built for.
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
    <a href="/catalogue/">What is not for sale yet</a>
  </div>
  <div>
    <h4>Who it is for</h4>
    <a href="/audiences/">The three buyers</a>
    <a href="/for/agents/">You run agents today</a>
    <a href="/for/investors/">You are backing a company</a>
    <a href="/for/startups/">You are a startup</a>
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
{f'<link rel="stylesheet" href="{fm["head_css"]}">' if fm.get('head_css') else ''}
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<script src="/assets/site.js" defer></script>
<!-- shop.js is on EVERY page because the nav carries an order badge on every page.
     So a shop page must NOT name it again in head_js: two tags is two copies of the
     cart engine running against one document, and the second one undoes what the
     first one did. check_site holds every page to loading each script once. -->
<script src="/assets/shop.js" defer></script>
{f'<script src="{fm["head_js"]}" defer></script>' if fm.get('head_js') else ''}
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
<p class="pagenav"><a href="/policies/">Which agent do you run? &rarr;</a>
<a href="/how-it-works/">How buying works &rarr;</a>
<a href="/ledger/">Every claim, with its state &rarr;</a></p>
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
    extra.update(buyer_pages(out_dir, ctx_shared))
    extra.update(lab_pages(out_dir, ctx_shared))
    extra.update(shape_pages(out_dir, ctx_shared))
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
             "buyer": o["buyer"], "also_for": o["also_for"],
             "checkout_mode": o["checkout_mode"],
             # the share taken when the order is placed; the rest is due on delivery
             "pay_now_pct": o.get("pay_now_pct", 100),
             # The link itself, or null. Never a placeholder string: a consumer of
             # this index has to be able to tell "no checkout" from "a checkout
             # whose URL somebody typed the word TODO into".
             "checkout_url": (o.get("checkout_url") or "").strip() or None,
             # Two amounts on one offer: the engagement, and the deposit that is
             # payable by card because it sits below the threshold the other one
             # does not. A consumer of this index has to be able to tell them apart.
             "deposit": ({"label": o["deposit_label"], "amount": o["deposit_amount"]}
                         if o.get("deposit_label") else None),
             "delivery": f"/d/{o['id']}/" if o["rail"] != "none" else None}
            for o in OFFERS
        ],
        "buyers": [
            {"id": b["id"], "order": b["order"], "name": b["name"],
             "question": b["arrives_with"], "url": f"/for/{b['id']}/",
             "built_for_them": b["primary"], "serves_them": b["also"],
             "addons": b["addons"], "entry": b["entry"],
             "market_claim": b["opportunity_claim"]}
            for b in BUYERS
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
    lines += ["", "## Who each offer was built for",
              "Three buyers, ordered by opportunity rather than presented as three equal doors. The",
              "grouping is a second index over the same six offers: it adds no offer and no price.",
              ""]
    for b in BUYERS:
        built = ", ".join(b["primary"]) or "NOTHING — every offer shown there was built for another buyer"
        lines.append(f"- `{b['id']}` — {b['name']} — asks \"{b['arrives_with']}\" — "
                     f"built for them: {built} — also shown: "
                     f"{', '.join(b['also'] + b['addons']) or 'none'} — {SITE['base']}/for/{b['id']}/")
    lines += ["", "## Offers, and where each code lands"]
    for o in OFFERS:
        where = f"{SITE['base']}/d/{o['id']}/" if o["rail"] != "none" else "no code behind it yet"
        url = (o.get("checkout_url") or "").strip()
        pay = url or f"no payment link ({o['checkout_mode']}) — {CHECKOUT_WHY[o['checkout_mode']]}"
        dep = (f" — deposit: {o['deposit_label']} by payment link, balance invoiced"
               if o.get("deposit_label") else "")
        lines.append(f"- `{o['id']}` — {o['price_label']} — {o['question']} — for: {o['buyer']}"
                     f" — {where} — checkout: {pay}{dep}")
    lines += [
        "",
        "No payment link has been created for any offer on this site: every checkout_url in",
        "data/offers.yml is empty, so each offer shows its code and its delivery page rather than a",
        "button. A standing payment link carries one price, so only the single-priced tier can ever",
        "have one; the two banded tiers take a link issued once the band is fixed, and the top tier",
        "goes by invoice after a conversation. Any URL that does land there is held by the build to",
        "the payment provider's own checkout hosts over HTTPS.",
    ]
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
