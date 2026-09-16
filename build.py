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
        ("What is actually in one", "/what-is-in-one/"),
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
        ("Reviews, dated and kept", "/admin/reviews/"),
        ("What we do not say, and why", "/disclosures/"),
        ("What is not for sale yet", "/catalogue/"),
        ("The dev packs", "/dev-packs/"),
        ("The purchase lab", "/lab/"),
        ("Release history", "/versions/"),
        ("Run the whole flow yourself", "/admin/try/"),
    ]),
    ("Admin", "/admin/", [
        ("The console", "/admin/"),
        ("The work", "/admin/work/"),
        ("The memo queue", "/admin/memos/"),
        ("Taking money", "/admin/rails/"),
        ("Reviews, dated and kept", "/admin/reviews/"),
        ("Run the whole flow yourself", "/admin/try/"),
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
    # RELABELLED 16 SEPTEMBER. It read "specified, never run" with the tooltip
    # "never been executed once", which was true of the SALE and false of the work,
    # and a reader had no way to tell which one a chip on an offer meant. It now
    # says the thing that is actually unrun, and the offer's own row says where to
    # go and read the work that is not.
    "unrun": ("never bought here", "st-u",
              "Never sold through this store. The work behind it has been done many times and is "
              "published \u2014 what has not happened is a purchase through this checkout."),
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
        f'<p class="offer-eta"><b>{html.escape(o["eta"])}</b>'
        f'<span>{html.escape(o["eta_from"])}</span></p>'
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
            f'<td class="small">{html.escape(o["eta"])}</td>'
            f'<td>{chip(o["state_badge"], claim_id=o["claim"])}</td>'
            f'<td class="small">{html.escape(RAILS[o["rail"]][0])}</td>'
            f'<td class="small"><code>{html.escape(o["id"])}</code></td></tr>'
        )
    return (
        '<div class="tablewrap"><table><thead><tr><th></th><th>The question it answers</th>'
        '<th class="num">Price</th><th>When it arrives</th>'
        '<th>What is true of it today</th><th>How it is paid</th>'
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
            f'<tr><th>When it arrives</th><td><b>{html.escape(o["eta"])}</b>, '
            f'{html.escape(o["eta_from"])}. {html.escape(o["eta_why"])}</td></tr>'
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
               '<b>You already have the prompt</b> \u2014 <code>MAP-A-GRANT.md</code> ships in every '
               'template zip and in every vault, so it is in your hands before you pay as well as '
               'after. You run it where the agent runs and send back what it writes. The mandate is '
               'corrected against that.</p>'
               '<div class="tablewrap"><table><tbody>'
               '<tr><th>1</th><td>You buy this level. Nothing is scheduled and nobody waits.</td></tr>'
               '<tr><th>2</th><td><b>Within 24 hours</b> a person follows up, and confirms where to '
               'send the files.</td></tr>'
               '<tr><th>3</th><td>You paste <code>MAP-A-GRANT.md</code> to the agent, in the '
               'environment it actually runs in. It reads its own configuration and prints a '
               'table.</td></tr>'
               '<tr><th>4</th><td>You send back the two files it writes &mdash; <code>grant.json</code> '
               'and <code>mandate.json</code> &mdash; and the session record, with no secret in them '
               'and your order reference on the message. No credentials, no logs, no access.</td></tr>'
               '<tr><th>5</th><td>The corrected vault comes back, with a written note of what '
               'changed and why.</td></tr>'
               "</tbody></table></div>"
               '<p class="small dim"><b>How long step 5 takes is not committed to anywhere on this '
               'site, and that is a gap rather than a policy.</b> The 24 hours is riskmandate.ai\u2019s '
               'commitment and is kept on their pages. The time from your reply to the corrected '
               'vault has never run for a paying buyer, so there is no measurement to quote and '
               'nothing is invented here in place of one.</p>'
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


# Two figures. Both are hand-authored SVG with no script and no external anything:
# structure in currentColor so they read in any future theme, and the site's accent
# reserved for the one thing each drawing is actually claiming.
REVIEW_FIG_LEVERS = '''
<figure class="rv-fig"><div class="rv-figbox">
<svg viewBox="0 0 1180 600" role="img" aria-label="Six frictions from the review map onto four levers, which satisfy the six recommendations. Lever A — putting the existing free diagnostic in front of the sale — alone satisfies F-2, F-3, R-1 and most of R-6.">
<defs>
<marker id="rvA" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="currentColor"/></marker>
<marker id="rvH" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="currentColor"/></marker>
</defs>
<text class="rv-lab" x="30" y="26">FRICTION</text>
<text class="rv-lab" x="392" y="26">LEVER</text>
<text class="rv-lab" x="790" y="26">SATISFIES</text>

<rect class="rv-node" x="30" y="46" width="270" height="44" rx="7"/>
<text class="rv-tid" x="44" y="65">F-2</text><text class="rv-t" x="80" y="65">Entry is our shape, not theirs</text>
<text class="rv-t2" x="80" y="81">&#8220;Which agent do you run?&#8221;</text>

<rect class="rv-node" x="30" y="104" width="270" height="44" rx="7"/>
<text class="rv-tid" x="44" y="123">F-3</text><text class="rv-t" x="80" y="123">No discovery moment</text>
<text class="rv-t2" x="80" y="139">told the problem, then sold the fix</text>

<rect class="rv-node" x="30" y="184" width="270" height="44" rx="7"/>
<text class="rv-tid" x="44" y="203">F-1</text><text class="rv-t" x="80" y="203">Vocabulary before value</text>
<text class="rv-t2" x="80" y="219">eight terms to decode</text>

<rect class="rv-node" x="30" y="242" width="270" height="44" rx="7"/>
<text class="rv-tid" x="44" y="261">F-4</text><text class="rv-t" x="80" y="261">The rungs are unlabelled</text>
<text class="rv-t2" x="80" y="277">each level must be decoded</text>

<rect class="rv-node" x="30" y="322" width="270" height="44" rx="7"/>
<text class="rv-tid" x="44" y="341">F-6</text><text class="rv-t" x="80" y="341">&#163;500 is buy-then-discover</text>
<text class="rv-t2" x="80" y="357">value arrives after the money</text>

<rect class="rv-node" x="30" y="400" width="270" height="44" rx="7"/>
<text class="rv-tid" x="44" y="419">F-5</text><text class="rv-t" x="80" y="419">&#163;5 may read as commodity</text>
<text class="rv-t2" x="80" y="435">two independent reports</text>

<rect class="rv-node-hot" x="392" y="46" width="290" height="102" rx="9"/>
<text class="rv-tid-hot" x="408" y="68">LEVER A</text>
<text class="rv-th" x="408" y="90">Put the diagnostic first</text>
<text class="rv-t2" x="408" y="108">MAP-A-GRANT already exists,</text>
<text class="rv-t2" x="408" y="123">already free, already in every zip.</text>
<text class="rv-tid-hot" x="408" y="139">Move it before the paywall.</text>

<rect class="rv-node" x="392" y="184" width="290" height="102" rx="9"/>
<text class="rv-tid" x="408" y="206">LEVER B</text>
<text class="rv-th" x="408" y="228">Gloss, don&#8217;t rename</text>
<text class="rv-t2" x="408" y="246">Plain sentence first, precise term</text>
<text class="rv-t2" x="408" y="261">one click away. Rename the four</text>
<text class="rv-t2" x="408" y="276">rungs; keep the vocabulary.</text>

<rect class="rv-node" x="392" y="322" width="290" height="102" rx="9"/>
<text class="rv-tid" x="408" y="344">LEVER C</text>
<text class="rv-th" x="408" y="366">Value before payment</text>
<text class="rv-t2" x="408" y="384">/lab/ already turns a described</text>
<text class="rv-t2" x="408" y="399">deployment into a band. Make it</text>
<text class="rv-t2" x="408" y="414">emit a draft mandate instead.</text>

<rect class="rv-node" x="392" y="458" width="290" height="102" rx="9"/>
<text class="rv-tid" x="408" y="480">LEVER D</text>
<text class="rv-th" x="408" y="502">Make the record re-run</text>
<text class="rv-t2" x="408" y="520">The vault is already the record.</text>
<text class="rv-t2" x="408" y="535">What is missing is an org index</text>
<text class="rv-t2" x="408" y="550">and a scheduled re-comparison.</text>

<rect class="rv-node-hot" x="790" y="46" width="360" height="44" rx="7"/>
<text class="rv-tid-hot" x="804" y="65">R-1</text><text class="rv-t" x="842" y="65">Lead with the question, then four numbers</text>
<text class="rv-t2" x="842" y="81">the aha moment, for nothing</text>

<rect class="rv-node-hot" x="790" y="104" width="360" height="44" rx="7"/>
<text class="rv-tid-hot" x="804" y="123">R-6</text><text class="rv-t" x="842" y="123">Pick &#8594; see &#8594; compare &#8594; find the gaps</text>
<text class="rv-t2" x="842" y="139">four of the six steps in the loop</text>

<rect class="rv-node" x="790" y="184" width="360" height="44" rx="7"/>
<text class="rv-tid" x="804" y="203">R-2</text><text class="rv-t" x="842" y="203">Template / Live Policy / Review / Sign-off</text>
<text class="rv-t2" x="842" y="219">copy, one release</text>

<rect class="rv-node" x="790" y="242" width="360" height="44" rx="7"/>
<text class="rv-tid" x="804" y="261">R-3</text><text class="rv-t" x="842" y="261">Free template, charge to operationalise</text>
<text class="rv-t2" x="842" y="277">answered by A, not by dropping the &#163;5</text>

<rect class="rv-node" x="790" y="322" width="360" height="44" rx="7"/>
<text class="rv-tid" x="804" y="341">R-4</text><text class="rv-t" x="842" y="341">Describe the deployment before buying</text>
<text class="rv-t2" x="842" y="357">a draft mandate, then the offer</text>

<rect class="rv-node" x="790" y="458" width="360" height="44" rx="7"/>
<text class="rv-tid" x="804" y="477">R-5</text><text class="rv-t" x="842" y="477">Agent Authorization Record</text>
<text class="rv-t2" x="842" y="493">70% shipped; the rest is a subscription</text>

<g class="rv-hot"><path class="rv-edge-hot" d="M300 68 L390 82" marker-end="url(#rvH)"/>
<path class="rv-edge-hot" d="M300 126 L390 108" marker-end="url(#rvH)"/>
<path class="rv-edge-hot" d="M300 432 C332 460, 342 170, 390 126" marker-end="url(#rvH)" stroke-dasharray="4 4" stroke-width="1.3"/>
<path class="rv-edge-hot" d="M682 78 L788 68" marker-end="url(#rvH)"/>
<path class="rv-edge-hot" d="M682 104 L788 126" marker-end="url(#rvH)"/>
<path class="rv-edge-hot" d="M682 126 C730 190, 740 248, 788 262" marker-end="url(#rvH)"/></g>

<path class="rv-edge" d="M300 206 L390 220" marker-end="url(#rvA)"/>
<path class="rv-edge" d="M300 264 L390 246" marker-end="url(#rvA)"/>
<path class="rv-edge" d="M300 344 L390 358" marker-end="url(#rvA)"/>
<path class="rv-edge" d="M300 422 C344 422, 350 392, 390 384" marker-end="url(#rvA)"/>
<path class="rv-edge" d="M682 220 L788 206" marker-end="url(#rvA)"/>
<path class="rv-edge" d="M682 370 L788 344" marker-end="url(#rvA)"/>
<path class="rv-edge" d="M682 498 L788 480" marker-end="url(#rvA)"/>
<path class="rv-edge" d="M682 530 C740 530, 752 190, 788 142" marker-end="url(#rvA)"/>

<text class="rv-tid-hot" x="30" y="512">Solid = lever A&#8217;s reach.</text>
<text class="rv-t2" x="30" y="530">Dashed = an indirect effect: a free</text>
<text class="rv-t2" x="30" y="545">diagnostic changes what &#163;5 is for.</text>
</svg>
</div>
<figcaption><b>One lever carries half the note.</b> F-2, F-3, R-1 and the first four steps of R-6 are
all the same missing thing: a way for a buyer to find their own gap before paying. That thing is
already built &mdash; <code>MAP-A-GRANT.md</code> ships free in every public template zip and prints
exactly the four numbers the note asks for. It is only surfaced <em>after</em> a &pound;500 purchase.
Moving it is a re-ordering, not a build.</figcaption></figure>
'''

REVIEW_FIG_FUNNEL = '''
<figure class="rv-fig"><div class="rv-figbox">
<svg viewBox="0 0 1040 320" role="img" aria-label="Today the free diagnostic sits after the 500 pound purchase. In the proposed funnel it moves to the front, before the catalogue, so a buyer sees their own gap before any payment.">
<defs><marker id="rvF" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="currentColor"/></marker></defs>
<text class="rv-lab" x="20" y="24">TODAY</text>
<rect class="rv-node" x="20" y="40" width="150" height="40" rx="6"/><text class="rv-t" x="95" y="64" text-anchor="middle">Catalogue</text>
<rect class="rv-node" x="210" y="40" width="150" height="40" rx="6"/><text class="rv-t" x="285" y="64" text-anchor="middle">Pick a shape</text>
<rect class="rv-node" x="400" y="40" width="150" height="40" rx="6"/><text class="rv-t" x="475" y="64" text-anchor="middle">Pay</text>
<rect class="rv-node" x="590" y="40" width="150" height="40" rx="6"/><text class="rv-t" x="665" y="64" text-anchor="middle">What happens now</text>
<rect class="rv-node-hot" x="780" y="34" width="240" height="52" rx="6"/>
<text class="rv-th" x="900" y="56" text-anchor="middle">The diagnostic prompt</text>
<text class="rv-t2" x="900" y="73" text-anchor="middle">free, and behind &#163;500</text>
<path class="rv-edge" d="M170 60 L206 60" marker-end="url(#rvF)"/>
<path class="rv-edge" d="M360 60 L396 60" marker-end="url(#rvF)"/>
<path class="rv-edge" d="M550 60 L586 60" marker-end="url(#rvF)"/>
<path class="rv-edge" d="M740 60 L776 60" marker-end="url(#rvF)"/>
<text class="rv-t2" x="475" y="106" text-anchor="middle">the buyer is told there is a gap</text>
<text class="rv-tid-hot" x="900" y="106" text-anchor="middle">and only here can they see their own</text>

<line x1="20" y1="142" x2="1020" y2="142" stroke="currentColor" stroke-opacity=".18"/>

<text class="rv-tid-hot" x="20" y="180">PROPOSED</text>
<rect class="rv-node-hot" x="20" y="196" width="240" height="52" rx="6"/>
<text class="rv-th" x="140" y="218" text-anchor="middle">The diagnostic prompt</text>
<text class="rv-t2" x="140" y="235" text-anchor="middle">free, and first</text>
<rect class="rv-node" x="300" y="202" width="150" height="40" rx="6"/><text class="rv-t" x="375" y="226" text-anchor="middle">Your four numbers</text>
<rect class="rv-node" x="490" y="202" width="150" height="40" rx="6"/><text class="rv-t" x="565" y="226" text-anchor="middle">Pick a shape</text>
<rect class="rv-node" x="680" y="202" width="150" height="40" rx="6"/><text class="rv-t" x="755" y="226" text-anchor="middle">Pay</text>
<rect class="rv-node" x="870" y="202" width="150" height="40" rx="6"/><text class="rv-t" x="945" y="226" text-anchor="middle">What happens now</text>
<g class="rv-hot"><path class="rv-edge-hot" d="M260 222 L296 222" marker-end="url(#rvF)"/>
<path class="rv-edge-hot" d="M450 222 L486 222" marker-end="url(#rvF)"/></g>
<path class="rv-edge" d="M640 222 L676 222" marker-end="url(#rvF)"/>
<path class="rv-edge" d="M830 222 L866 222" marker-end="url(#rvF)"/>
<text class="rv-tid-hot" x="375" y="274" text-anchor="middle">the buyer finds their own gap, for nothing</text>
<text class="rv-t2" x="755" y="274" text-anchor="middle">and now knows what they are buying</text>
</svg>
</div>
<figcaption><b>Nothing is built and nothing is removed.</b> One asset moves from the end of the funnel
to the front of it. That single move answers F-2, F-3, R-1, the first four steps of R-6, and changes
what the &pound;5 is <em>for</em> &mdash; which is most of the answer to F-5 and R-3 as well.</figcaption></figure>
'''

# ------------------------------------------------------- the admin console ----
# THE ADMIN PAGES ARE A CONSOLE, NOT DOCUMENTS, and until v0.1.18 they were
# wearing the shop's clothes: warm paper, serif headings, a 960px measure and a
# nav built for somebody deciding whether to buy. A page whose job is "what is
# blocking a first sale" wants the opposite of that, so it gets its own shell and
# its own stylesheet. assets/console.css says what changed and why, and credits
# the console at pt.newsroom.sgit.ai/newsroom/ that the architecture comes from.
#
# THE RAIL CARRIES COUNTS AND THE COUNTS ARE COMPUTED. A rail whose numbers are
# typed is a rail that lies within a release. Every number below is read from the
# same files the pages are built from, so a number cannot disagree with the page
# it points at.
CONSOLE_CSS = "/assets/console.css"
# claims.yml is read inside build() for the ledger; the console needs the same
# records to count with, and reading a file twice is cheaper than threading it
# through four call sites.
CLAIMS_ALL = yaml_load((DATA / "claims.yml").read_text())


def console_counts():
    """What the rail and the dashboard count. Read, never typed.

    The ranks are the console's, not the ledger's: r1 is what blocks a first paid
    order, r2 is what is waiting on a ruling nobody has made, and the rest is
    state. A claim's own state lives in data/claims.yml and is a different scale
    on purpose — one says how true a sentence is, the other says what it costs."""
    rails = CHECKOUT_RAILS["rails"]
    live_rails = [r for r in rails if (r.get("url") or "").strip()]
    real_rails = [r for r in rails if not r.get("simulated")]
    blockers = [c for c in CLAIMS_ALL if c["state"] == "absent"
                and "gates" in c["claim"].lower() or c["id"] == "sale-notification-absent"]
    rulings = sum(1 for rid in REVIEW_ORDER for p in REVIEWS[rid]["proposals"]
                  if p["stance"] == "ruling")
    proposals = sum(len(REVIEWS[rid]["proposals"]) for rid in REVIEW_ORDER)
    unrun = [o for o in OFFERS if o["state_badge"] in ("unrun", "absent", "partial")]
    return {
        "reviews": len(REVIEW_ORDER),
        "proposals": proposals,
        "rulings": rulings,
        "rails_live": len(live_rails),
        "rails_total": len(real_rails),
        "offers": len(OFFERS),
        "offers_unproven": len(unrun),
        "claims": len(CLAIMS_ALL),
        "blockers": len(blockers),
        "shapes": len(ABP["shapes"]),
        "memos": len(MEMOS["memos"]),
        "workstreams": len(WORK["workstreams"]),
        "work_total": sum(len(w["tasks"]) for w in WORK["workstreams"]),
        "work_open": sum(1 for w in WORK["workstreams"] for t in w["tasks"]
                         if t["status"] != "done"),
        "work_next": sum(1 for w in WORK["workstreams"] for t in w["tasks"]
                         if t["status"] in ("next", "in-progress")),
        # Not shapes times four: the catch-all shape has no template, so its first
        # two levels do not exist and it carries two SKUs rather than four.
        "skus": sum(len(s["levels"]) for s in SHOP_SHAPES),
        "version": SITE["version"],
    }


# The rail. One list, so a page cannot be in the console and not in the rail.
# `out` marks a link that leaves the console for a selling page — the console is
# not a second copy of the shop and says which door it is opening.
CONSOLE_RAIL = [
    ("Where it stands", [
        ("Console", "/admin/", None, False),
        ("Reviews", "/admin/reviews/", "reviews", False),
        ("Run the flow yourself", "/admin/try/", None, False),
    ]),
    ("The work", [
        ("The board", "/admin/work/", "work_open", False),
        ("The memo queue", "/admin/memos/", "memos", False),
    ]),
    ("Next: taking money", [
        ("Both rails", "/admin/rails/", "blockers", False),
        ("Stripe", "/admin/rails/stripe/", None, False),
        ("SumUp", "/admin/rails/sumup/", None, False),
    ]),
    ("The record", [
        ("Claim ledger", "/ledger/", None, True),
        ("What we do not say", "/disclosures/", None, True),
        ("Release history", "/versions/", None, True),
        ("The dev packs", "/dev-packs/", None, True),
        ("The purchase lab", "/lab/", None, True),
        ("Not for sale yet", "/catalogue/", None, True),
    ]),
]


def console_rail(current, counts):
    out = ['<nav class="rail">',
           '<a class="rail__brand" href="/admin/"><b>store<i>.sgit.ai</i></b>'
           f'<span>admin console · {html.escape(counts["version"])}</span></a>']
    for group, items in CONSOLE_RAIL:
        out.append(f'<div class="rail__group"><h3>{html.escape(group)}</h3>')
        for label, url, count_key, external in items:
            here = ' aria-current="page"' if url == current else ""
            badge = ""
            if count_key:
                n = counts.get(count_key, 0)
                cls = "count r1" if count_key == "blockers" and n else "count"
                badge = f'<span class="{cls}">{n}</span>'
            arrow = '<span class="out">↗</span>' if external else ""
            out.append(f'<a class="nav" href="{url}"{here}>{html.escape(label)}{arrow}{badge}</a>')
        out.append("</div>")
    out.append(
        '<p class="rail__note"><b>Public, and not advertised.</b> Every page here is '
        'noindex, out of <code>sitemap.xml</code> and out of <code>llms-full.txt</code>. '
        'Anybody handed the address reads every word. '
        '<a href="/">Back to the shop</a>.</p>')
    out.append("</nav>")
    return "".join(out)


def console_html(page, ctx, body):
    """The console shell. Deliberately NOT page_html: no shop nav, no disclosure
    strip built for a buyer, no footer arguing the offer. What crosses over is one
    strip that says where you are and how to get back."""
    fm = page["fm"]
    counts = console_counts()
    prefix = rel_prefix(page["url"])
    crumb = page.get("crumb") or fm.get("crumb", "")
    head_actions = fm.get("head_actions", "")
    return relativise(f"""<!doctype html>
<html lang="en" data-root="{prefix}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{html.escape(fm['title'])} · store.sgit.ai admin</title>
<meta name="description" content="{html.escape(fm.get('description', ''))}">
<meta name="robots" content="noindex,follow">
<link rel="canonical" href="{SITE['base']}{page['url']}">
<link rel="alternate" type="text/markdown" href="index.md" title="This page as markdown">
<link rel="stylesheet" href="{CONSOLE_CSS}">
{f'<link rel="stylesheet" href="{fm["head_css"]}">' if fm.get('head_css') else ''}
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
{f'<script src="{fm["head_js"]}" defer></script>' if fm.get('head_js') else ''}
{f'<script src="{fm["head_js2"]}" defer></script>' if fm.get('head_js2') else ''}
</head>
<body class="console">
<div class="c-strip"><div class="row">
<b>store.sgit.ai</b> <span class="c-sep">/</span> <a href="/admin/">admin</a>
<span class="c-sep">·</span> <a href="/">the shop</a>
<span class="c-sep">·</span> <a href="/ledger/">the ledger</a>
<span class="c-sep">·</span> <a href="index.md">this page as markdown</a>
<span class="c-noindex">noindex · not in the sitemap</span>
</div></div>
<div class="c-disc"><div class="row">{MODEL_GENERATED}</div></div>
<div class="shell">
{console_rail(page['url'], counts)}
<main class="main">
{f'<p class="crumb">{crumb}</p>' if crumb else ''}
<div class="page-head"><div>
<h1>{html.escape(fm['title'])}</h1>
{f"<p>{fm['blurb']}</p>" if fm.get('blurb') else ''}
</div>{head_actions}</div>
{body}
<div class="c-foot"><b>An operations surface</b> for the people
building this store, public because every page here is. It is not a selling page and
nothing on it is an offer. <a href="/">The shop is here</a> ·
<a href="/ledger/">every claim, with its state</a> ·
<a href="/admin/reviews/">the reviews</a></div>
</main>
</div>
</body>
</html>
""", prefix)


def review_markdown(rv):
    """A review as markdown, for the twin. Every page here is served as markdown at
    <page>/index.md and an agent reads that rather than the HTML; a twin carrying a
    shortcode and not the review would hand an agent a page about a critique with the
    critique missing."""
    strip = lambda s: html.unescape(re.sub(r"<[^>]+>", "", s))
    L = [f"# {rv['title']}", "", rv["lede"], "",
         f"- **Reviewer:** {rv['reviewer']}",
         f"- **Subject:** {rv['subject']}",
         f"- **Reviewed:** {rv['reviewed_on']}, against {rv['reviewed_version']}",
         "- " + " · ".join(f"**{n}** {lab}" for n, lab in rv["counts"]), ""]
    if rv.get("vault"):
        v = rv["vault"]
        L += ["## The vault this review is of", "", v["note"], "",
              f"- **Vault:** `{v['id']}` · {v['files']} files · read-only",
              f"- **Read key:** `{v['read_key']}:{v['id']}`",
              f"- **Open it:** {v['web']}",
              "",
              "It is embedded on the page as well as linked. The frame is built at runtime, opened "
              "carrying nothing, and handed the read key by message with the target origin pinned "
              "\u2014 so the key is not in a URL, not in history, not in a referrer and not in the "
              "frame's storage. This is the one place on this site that opens a connection; every "
              "page that sells anything still opens none at all.", ""]
    if rv.get("verbatim"):
        L += ["## The note, verbatim", "",
              "Reproduced exactly as sent. Nothing trimmed, reordered or paraphrased.", "",
              "> " + rv["verbatim"].replace("\n", "\n> ").replace(">> ", "").replace("|| ", "    "),
              ""]
    if rv.get("taxonomy"):
        L += ["## What is in the note", ""]
        for group, head in (("keep", "Keep"), ("friction", "Friction"), ("rec", "Recommendation")):
            if group not in rv["taxonomy"]:
                continue
            L += [f"### {head}", ""]
            for tid, title, body in rv["taxonomy"][group]:
                L.append(f"- **{tid} — {title}.** {strip(body)}")
            L.append("")
    if rv.get("has_figures"):
        L += ["## Six frictions, four levers", "",
              "Four changes carry all six recommendations, and one carries half of them on its own: "
              "put the free diagnostic in front of the sale. `MAP-A-GRANT.md` already exists, is "
              "already free, already ships in every public template zip, and prints exactly the four "
              "numbers the note asks for — it is only surfaced after a £500 purchase.", ""]
    for s in rv.get("sections", []):
        L += [f"## {s['h']}", ""]
        for para in s["body"]:
            L += [strip(para), ""]
    if rv.get("evidence"):
        L += ["## The evidence", "",
              "Captured by driving a browser, not written.", ""]
        for src, cap in rv["evidence"]:
            L.append(f"- `/assets/reviews/{rv['id']}/{src}` — {strip(cap)}")
        L.append("")
    L += [f"## The {len(rv['proposals'])} proposals", "",
          "Each carries what it would cost. A stance of *won't do* is written down so somebody can "
          "argue with it.", ""]
    for pr in rv["proposals"]:
        L += [f"### {pr['id']} — {strip(pr['title'])}", "",
              f"- **Our stance:** {rv['stance_labels'][pr['stance']]}",
              f"- **Answers:** {pr['refs']}",
              "- **Cost:** " + " · ".join(f"{k} {v}" for k, v in pr["cost"]), "",
              f"> {pr['quote']}", ""]
        for para in pr["what"]:
            L += [strip(para), ""]
        for name, body in pr.get("opts", []):
            L.append(f"- **{name}.** {strip(body)}")
        if pr.get("opts"):
            L.append("")
    L += ["## Send it back", "",
          f"The page at {SITE['base']}{REVIEW_REGISTER['root']}{rv['id']}/ carries a verdict control "
          "and a reason box on every proposal, and copies the result out as markdown or JSON. "
          "Nothing typed there is submitted anywhere: no page on this site opens a network "
          "connection.", ""]
    return "\n".join(L)

# ---------------------------------------------------------- the reviews ----
# A REVIEW IS A MOMENT LOCKED, so it is dated, it is kept, and it is never
# rewritten. The register in data/reviews/_register.json names them; each is a
# JSON file in the same directory; the index, the pages, the twins and the sort
# are all generated. Adding a review is adding a file and a line, which is the
# only shape that survives having a lot of them.
#
# They live under /admin/ because a review carries reason boxes a reader types
# into, and because the pricing deliberation and roadmap in one of them is not
# selling copy. Public, like every page here, and not advertised: noindex, out of
# sitemap.xml and out of llms-full.txt.
REVIEW_REGISTER = json.loads((DATA / "reviews" / "_register.json").read_text())
REVIEWS = {}
for _rid in REVIEW_REGISTER["order"]:
    _f = DATA / "reviews" / f"{_rid}.json"
    if not _f.exists():
        raise SystemExit(f"build: the review register names {_rid!r} and data/reviews/{_rid}.json "
                         "does not exist. A register that points at nothing is worse than no "
                         "register.")
    REVIEWS[_rid] = json.loads(_f.read_text())
for _f in sorted((DATA / "reviews").glob("*.json")):
    if _f.stem != "_register" and _f.stem not in REVIEWS:
        raise SystemExit(f"build: data/reviews/{_f.name} is not in the register, so it would be "
                         "written and never linked. Add it to the order list.")
# Newest first. The register's own order breaks a tie within a day.
REVIEW_ORDER = sorted(REVIEW_REGISTER["order"],
                      key=lambda i: (REVIEWS[i]["date"], -REVIEW_REGISTER["order"].index(i)),
                      reverse=True)


def _rv_letter(text):
    """A note as sent. `>>` marks a line the writer set apart; `||` marks a block
    they laid out as a list. Nothing else is interpreted and nothing is edited."""
    out, buf, flow = [], [], []

    def flush_para():
        if buf:
            out.append("<p>" + html.escape(" ".join(buf)) + "</p>")
            buf.clear()

    def flush_flow():
        if flow:
            out.append('<p class="rv-flow">' + html.escape("\n".join(flow)) + "</p>")
            flow.clear()

    for line in text.split("\n"):
        s = line.strip()
        if not s:
            flush_para(); flush_flow(); continue
        if s.startswith(">>"):
            flush_para(); flush_flow()
            out.append('<p class="rv-pull">' + html.escape(s[2:].strip()) + "</p>")
        elif s.startswith("||"):
            flush_para()
            flow.append(s[2:].strip().replace("->", "→"))
        else:
            flush_flow(); buf.append(s)
    flush_para(); flush_flow()
    return "".join(out)


def _rv_taxonomy(tax):
    out = []
    for group, head, cls in (("keep", "Keep — what was called out as working", "rv-k"),
                             ("friction", "Friction — what got in the way", "rv-f"),
                             ("rec", "Recommendation — what was proposed", "rv-r")):
        if group not in tax:
            continue
        out.append(f'<h3 class="rv-taxhead">{html.escape(head)}</h3><div class="rv-tax">')
        for tid, title, body in tax[group]:
            out.append(f'<div class="rv-tx {cls}"><span class="rv-txid">{tid}</span>'
                       f'<b>{html.escape(title)}</b><p>{body}</p></div>')
        out.append("</div>")
    return "".join(out)


def _rv_vault(v, rid):
    """The vault the review is of, embedded read-only.

    THE EMBED IS THE ESTATE'S OWN COMPONENT and the mechanism is worth stating on
    the page rather than leaving in a file: the frame is built at runtime, it is
    opened carrying no credential, it announces itself, and only then is the read
    key posted to it with the target origin pinned. The key never appears in a URL,
    in history, in a referrer or in the frame's storage — and it is a read key,
    which opens a vault and cannot write to it.

    This is the one thing on this site that opens a connection, it happens on review
    pages and nowhere else, and the pages that sell something still open none."""
    host = v["embed_host"]
    return (
        '<div class="rv-vault">'
        '<span class="rv-vlab2">The vault this review is of</span>'
        f'<p class="rv-vnote">{html.escape(v["note"])}</p>'
        '<div class="rv-vgrid">'
        f'<div><b>Vault</b><code>{html.escape(v["id"])}</code></div>'
        f'<div><b>Files</b><code>{v["files"]}</code></div>'
        '<div><b>Access</b><code>read-only</code></div>'
        "</div>"
        '<span class="rv-vlab2">The read key. It opens the vault and cannot write to it.</span>'
        f'<code class="rv-key">{html.escape(v["read_key_hex"])}:{html.escape(v["id"])}</code>'
        '<p class="rv-vopen">'
        f'<a href="{html.escape(v["web"])}" rel="noopener" target="_blank">'
        'Open it in its own tab \u2197</a> '
        f'<span class="small dim">or from the command line: '
        f'<code>sgit clone {html.escape(v["read_key_hex"][:12])}\u2026:{html.escape(v["id"])}</code>'
        "</span></p>"
        '<div class="rv-slot">'
        '<b>This is the one place on this site that opens a connection.</b> The two surfaces below '
        'are the official vault interface, running on '
        f'<code>{html.escape(host.replace("https://", ""))}</code> in a frame this page builds. '
        '<b>The key does not travel in the address.</b> The frame is opened carrying nothing, it '
        'announces itself, and only then is the read key handed over by message with the target '
        'origin pinned \u2014 so it is not in a URL, not in history, not in a referrer and not in '
        'the frame\u2019s storage. Replies from any other origin are ignored. '
        '<b>Every page on this site that sells anything still opens nothing at all</b>, and a build '
        'check holds it there. '
        '<b>One exception, stated because it is real:</b> if the handshake does not complete within '
        'twelve seconds the component falls back to opening the vault with the key in the frame\u2019s '
        'URL fragment. A fragment is never sent to a server and never appears in a referrer, but it '
        'is in that frame\u2019s address. The link above avoids it entirely.</div>'
        "</div>"
        f'<div class="sgv-uiembed" data-vault="{html.escape(v["id"])}" '
        f'data-readkey="{html.escape(v["read_key_hex"])}" '
        f'data-app="{"1" if v.get("has_app") else "0"}"></div>')


def _rv_sections(secs):
    out = []
    for s in secs:
        out.append(f'<h2 id="{slugify(s["h"])}">{html.escape(s["h"])}</h2>')
        out.append("".join(f"<p>{x}</p>" for x in s["body"]))
    return "".join(out)


def _rv_evidence(rid, shots):
    out = ['<h2 id="the-evidence">The evidence</h2>',
           '<p>Captured by driving a browser, not written. Each one is what was actually on the '
           'screen at that step, at that width, at the version named above.</p>']
    for src, cap in shots:
        out.append(
            f'<figure class="rv-shot"><img src="/assets/reviews/{rid}/{src}" loading="lazy" '
            f'alt="{html.escape(re.sub(r"<[^>]+>", "", cap))[:180]}">'
            f"<figcaption>{cap}</figcaption></figure>")
    return "".join(out)


def _rv_proposals(rv):
    labels = rv["stance_labels"]
    out = []
    for p in rv["proposals"]:
        out.append(f'<article class="rv-item" id="{p["id"].lower()}">')
        out.append(f'<div class="rv-head"><span class="rv-id">{p["id"]}</span>'
                   f'<h3>{p["title"]}</h3>'
                   f'<span class="rv-st st-{p["stance"]}">{html.escape(labels[p["stance"]])}</span></div>')
        out.append('<div class="rv-body">')
        out.append(f'<p class="rv-refs">Answers {html.escape(p["refs"])}</p>')
        out.append(f'<p class="rv-quote">“{html.escape(p["quote"])}”</p>')
        out.append('<div class="rv-block"><span class="rv-blab">What we could do</span>')
        out.append("".join(f"<p>{x}</p>" for x in p["what"]))
        if p.get("opts"):
            out.append('<div class="rv-opts">')
            for name, body in p["opts"]:
                out.append(f'<div class="rv-opt"><b>{html.escape(name)}</b><span>{body}</span></div>')
            out.append("</div>")
        out.append("</div>")
        out.append('<div class="rv-block"><div class="rv-cost">'
                   + "".join(f"<span>{html.escape(k)} <b>{html.escape(v)}</b></span>"
                             for k, v in p["cost"])
                   + "</div></div></div>")
        picks = "".join(
            f'<button type="button" class="rv-pick" data-v="{v}" aria-pressed="false">'
            f"{html.escape(label)}</button>" for v, label in rv["verdicts"])
        out.append(
            f'<div class="rv-verdict">'
            f'<div class="rv-vlab"><span>Your verdict on {p["id"]}</span>'
            f'<span class="rv-saved" data-saved="{p["id"]}">saved</span></div>'
            f'<div class="rv-picks" data-picks="{p["id"]}">{picks}</div>'
            f'<label class="visually-hidden" for="why-{p["id"]}">Why, for {p["id"]}</label>'
            f'<textarea class="rv-why" id="why-{p["id"]}" rows="3" '
            f'placeholder="Why? If you disagree, the reason is the useful part."></textarea>'
            "</div></article>")
    return "".join(out)


def _rv_model(rv):
    titles, refs, stances = {}, {}, {}
    for p in rv["proposals"]:
        titles[p["id"]] = html.unescape(re.sub(r"<[^>]+>", "", p["title"]))
        refs[p["id"]] = p["refs"]
        stances[p["id"]] = rv["stance_labels"][p["stance"]]
    return {"page": f'store.sgit.ai{REVIEW_REGISTER["root"]}{rv["id"]}/',
            "version": SITE["version"], "reviewed_on": rv["reviewed_on"],
            "storage": rv["storage"] + "." + rv["id"],
            "ids": [p["id"] for p in rv["proposals"]],
            "verdicts": rv["verdicts"], "titles": titles, "refs": refs, "stances": stances}


def _rv_counts(rv):
    return ('<div class="rv-counts">' + "".join(
        f'<div><b>{html.escape(n)}</b><span>{html.escape(lab)}</span></div>'
        for n, lab in rv["counts"]) + "</div>")


def review_pages(out_dir, ctx_shared):
    """One page per review, plus the register that lists them."""
    made = {}
    root = REVIEW_REGISTER["root"]
    kinds = REVIEW_REGISTER["kinds"]

    for rid in REVIEW_ORDER:
        rv = REVIEWS[rid]
        url = f"{root}{rid}/"
        ctx = dict(ctx_shared)
        ctx.update({"page": rid, "page_url": url, "fm": {}, "toc": []})
        n = len(rv["proposals"])
        kind_name, kind_why = kinds[rv["kind"]]

        body = (
            f'<p class="lead">{inline(rv["lede"], dict(ctx, untrusted=True))}</p>'
            + _rv_counts(rv)
            + '<div class="rv-who"><div><b>Reviewer</b>'
            f'<span>{html.escape(rv["reviewer"])}</span></div>'
            f'<div><b>Subject</b><span>{html.escape(rv["subject"])}</span></div>'
            f'<div><b>Reviewed</b><span>{html.escape(rv["reviewed_on"])}, against '
            f'{html.escape(rv["reviewed_version"])}</span></div>'
            f'<div><b>Kind</b><span>{html.escape(kind_name)} — {html.escape(kind_why)}</span></div>'
            "</div>"
            + (_rv_vault(rv["vault"], rid) if rv.get("vault") else "")
            + ('<h2 id="the-note-verbatim">The note, verbatim</h2>'
               '<p>Reproduced exactly as sent. Nothing trimmed, reordered or paraphrased — the '
               'reading of it below is ours and is kept separate from it on purpose.</p>'
               '<div class="rv-letter"><span class="rv-verb">Unedited</span>'
               + _rv_letter(rv["verbatim"]) + "</div>" if rv.get("verbatim") else "")
            + ('<h2 id="what-is-in-the-note">What is in the note</h2>'
               '<p>Sorted into three kinds. The identifiers are used for the rest of this page, so '
               'a verdict can name exactly what it is answering.</p>'
               + _rv_taxonomy(rv["taxonomy"]) if rv.get("taxonomy") else "")
            + ('<h2 id="six-frictions-four-levers">Six frictions, four levers</h2>'
               '<p>Read as six separate asks, this is a quarter’s work. Read for what actually '
               'moves, it collapses: <b>four changes carry all six recommendations, and one of the '
               'four carries half of them on its own.</b></p>' + REVIEW_FIG_LEVERS
               + '<h2 id="the-one-edge-that-moves">The one edge that moves</h2>'
               '<p>The same funnel, before and after. One thing changes position; everything else '
               'is where it already is.</p>' + REVIEW_FIG_FUNNEL if rv.get("has_figures") else "")
            + (_rv_sections(rv["sections"]) if rv.get("sections") else "")
            + (_rv_evidence(rid, rv["evidence"]) if rv.get("evidence") else "")
            + f'<h2 id="the-proposals">{n} proposals, with a stance on each</h2>'
            '<p>Every one carries what it would cost and what it touches. <b>Disagreeing is the '
            'useful answer</b>, and the reason matters more than the verdict.</p>'
            '<div class="rv-prog"><span class="rv-track"><span class="rv-fill" id="rv-fill">'
            f'</span></span><span id="rv-num">0 of {n} answered</span>'
            '<span class="dim">· kept in this browser, sent nowhere</span></div>'
            + _rv_proposals(rv)
            + '<h2 id="send-it-back">Send it back</h2>'
            '<div class="rv-export"><h3>Your verdicts, as text you can paste</h3>'
            '<p>Everything you set above lives <b>in this browser only</b>. There is no account, '
            'nothing is submitted, and no page here opens a network connection — which is a '
            'build check rather than a promise. The buttons put it on your clipboard: markdown to '
            'read in a message, JSON if it is going into a tracker.</p>'
            '<label class="rv-blab" for="rv-overall" style="margin-top:1.1rem">'
            'Anything the proposals did not cover</label>'
            '<textarea class="rv-why" id="rv-overall" rows="3" '
            'placeholder="What did we miss? What would you have led with? Anything you would drop?">'
            "</textarea>"
            '<div class="rv-exbtns">'
            '<button type="button" class="buy" id="rv-md">Copy as markdown</button>'
            '<button type="button" class="buy buy-alt" id="rv-json">Copy as JSON</button>'
            '<button type="button" class="linkish" id="rv-toggle">Show what gets copied</button>'
            '<button type="button" class="linkish" id="rv-clear">Clear everything</button>'
            '</div><pre class="rv-prev" id="rv-prev" hidden></pre></div>'
            '<div class="rv-toast" id="rv-toast" role="status" aria-live="polite">Copied</div>'
            '<script type="application/json" id="review-model">'
            + json.dumps(_rv_model(rv), separators=(",", ":")) + "</script>")

        page = {
            "fm": {"title": rv["title"], "description": rv["summary"],
                   "head_css": "/assets/review.css", "head_js": "/assets/review.js",
                   # Only a review page WITH a vault loads the embed. A page that has
                   # nothing to embed does not get the one script that can open a
                   # connection, which is the difference between a narrow exception
                   # and a wide one.
                   "head_js2": "/assets/vault-embed.js" if rv.get("vault") else "",
                   "robots": "noindex,follow"},
            "url": url,
            "crumb": f' / <a href="{root}">reviews</a> / {html.escape(rv["date"])}',
            "nav_match": "/ledger/",
            "src_md": review_markdown(rv),
        }
        target = out_dir / url.strip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(console_html(page, ctx, body))
        (target.parent / "index.md").write_text(
            page["src_md"].rstrip("\n") + f"\n\n---\n\n{LICENCE_STAMP}\n")
        made[url] = rv["title"]

    # ------------------------------------------------------------- the index
    rows = []
    for rid in REVIEW_ORDER:
        rv = REVIEWS[rid]
        kind_name, _ = kinds[rv["kind"]]
        rows.append(
            f'<a class="rv-card rv-kind-{rv["kind"]}" href="{root}{rid}/">'
            f'<div class="rv-cdate"><time datetime="{rv["date"]}">{html.escape(rv["date"])}</time>'
            f'<span class="rv-ckind">{html.escape(kind_name)}</span></div>'
            f'<h3>{html.escape(rv["title"])}</h3>'
            f'<p class="rv-csub">{html.escape(rv["subject"])}</p>'
            f'<p class="rv-csum">{html.escape(rv["summary"])}</p>'
            + '<div class="rv-cnums">' + "".join(
                f"<span><b>{html.escape(n)}</b> {html.escape(lab)}</span>" for n, lab in rv["counts"])
            + "</div></a>")

    idx_ctx = dict(ctx_shared)
    idx_ctx.update({"page": "reviews", "page_url": root, "fm": {}, "toc": []})
    idx_body = (
        '<p class="lead">Every review of this store, newest first. <b>A review is a moment '
        'locked</b> — dated, kept, never rewritten, and carrying the screenshots and the '
        'version it was taken against. A month from now this is the only record of what the store '
        'looked like today.</p>'
        f'<div class="rv-index">{"".join(rows)}</div>'
        '<h2 id="how-this-works">How this works</h2>'
        '<p><b>Each review keeps its own stance on every proposal in it</b> — do now, do next, '
        'won’t do, or needs a ruling — and carries a verdict control so the reviewer can '
        'disagree with the stance and say why. The reasons matter more than the verdicts; the whole '
        'point of writing down a <em>won’t do</em> is that somebody gets to argue with it.</p>'
        '<p><b>Adding one is adding a file.</b> A review is a JSON record in '
        '<code>data/reviews/</code> and a line in the register; the page, its markdown twin, its '
        'card here and its place in the sort are generated. The build refuses a register entry with '
        'no file and a file with no register entry, because a review nobody can reach is a review '
        'that did not happen.</p>'
        '<p><b>These pages are public and not advertised.</b> They carry reason boxes, pricing '
        'deliberation and roadmap, which is not selling copy — so they are noindex, out of '
        '<code>sitemap.xml</code> and out of <code>llms-full.txt</code>, and anybody handed the '
        'address can read every word. {{claim:review-is-the-one-typing-surface}}</p>')
    idx_page = {
        "fm": {"title": "Reviews",
               "description": ("Every review of this store, newest first, dated and kept. Each one "
                               "is a moment locked: the version it was taken against, the "
                               "screenshots, and a stance on every proposal in it."),
               "head_css": "/assets/review.css", "robots": "noindex,follow"},
        "url": root,
        "crumb": ' / <a href="/admin/">admin</a> / reviews',
        "nav_match": "/ledger/",
        "src_md": ("# Reviews\n\nEvery review of this store, newest first. A review is a moment "
                   "locked: dated, kept, never rewritten, carrying the screenshots and the version "
                   "it was taken against.\n\n"
                   + "".join(
                       f"- **{REVIEWS[r]['date']} — {REVIEWS[r]['title']}** "
                       f"({kinds[REVIEWS[r]['kind']][0]}) — {REVIEWS[r]['summary']} "
                       f"— {SITE['base']}{root}{r}/\n" for r in REVIEW_ORDER)),
    }
    target = out_dir / root.strip("/") / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(console_html(idx_page, idx_ctx, shortcodes_inline(idx_body, idx_ctx)))
    (target.parent / "index.md").write_text(
        idx_page["src_md"].rstrip("\n") + f"\n\n---\n\n{LICENCE_STAMP}\n")
    made[root] = "Reviews"
    return made


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
            'this browser: there is no form on this site, nothing is submitted anywhere, and no page '
            'here opens a network '
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
         '<b>Nothing on this page collects anything</b> \u2014 there is no form, no card field and no '
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
        # A RELEASE NOTE IS DATA, NOT MARKUP, so it renders the way republished vault
        # content does: everything escaped, no shortcode run, links held to safe schemes.
        # inline() passes anything tag-shaped straight through for trusted content, which
        # is right for a page whose author writes HTML on purpose and wrong for a prose
        # field in a JSON file. A note that named the form element put a real one into the
        # page, and the gate caught it. Bold, italic and code spans still work, which is
        # all a release note has ever wanted.
        #
        # Blank lines now make paragraphs. They did not, so every multi-paragraph note
        # since v0.1.9 rendered as one wall of text on its own version page.
        leads = "".join(
            f'<p class="lead">{inline(para, dict(ctx, untrusted=True))}</p>'
            for para in re.split(r"\n\s*\n", (r["summary"] or r["title"]).strip()))
        body = (
            leads +
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
    <a href="/admin/reviews/">Reviews, dated and kept</a>
    <a href="/disclosures/">What we do not say, and why</a>
    <a href="/dev-packs/">The dev packs</a>
    <a href="/versions/">Release history</a>
    <a href="/admin/">Admin</a>
  </div>
</div>
<div class="footnote"><p>No analytics. No cookies. No third-party fonts, scripts or CDN &mdash; every byte of this
site is served from this domain. <b>Every page that sells anything opens no network connection at all</b>, and a build
check holds that line. The one exception is named and narrow: a <a href="/admin/reviews/">review</a> of a vault embeds
that vault from one host, through one vendored component, and says so on itself. Nothing anywhere here sends anything
about you &mdash; no fetch, no beacon, no socket, on any page. Paying happens on the payment provider&rsquo;s own pages, which is the only place a card number should ever be
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
<meta name="robots" content="{fm.get('robots') or 'index,follow'}">
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
{f'<script src="{fm["head_js2"]}" defer></script>' if fm.get('head_js2') else ''}
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


# ------------------------------------------------------- the rails, the board ----
# THREE FILES, AND NONE OF THEM IS A PAGE. data/admin/rails.json is how each
# payment rail gets turned on; data/admin/work.json is the units of work;
# data/admin/memos.json is the queue the units came out of. Every page below is
# generated from one of them, so the only way to change what the console says is
# to change what the console knows.
RAIL_PLANS = json.loads((DATA / "admin" / "rails.json").read_text())
WORK = json.loads((DATA / "admin" / "work.json").read_text())
MEMOS = json.loads((DATA / "admin" / "memos.json").read_text())
STRIPE_PRODUCTS = json.loads((DATA / "admin" / "stripe-products.json").read_text())
WORK_COLS = WORK["columns"]
WORK_BY_ID = {w["id"]: w for w in WORK["workstreams"]}
MEMO_BY_ID = {m["id"]: m for m in MEMOS["memos"]}


def ws_status(ws):
    """Where a workstream sits, DERIVED from the tasks in it.

    A workstream is never moved by hand. It moves because a task moved, which is
    the only arrangement in which the summary board and the detail board cannot
    disagree — and disagreeing is the one failure that makes a board worse than
    no board. An explicit `status` on a workstream is honoured because a
    workstream can be parked for a reason that is not in its tasks; nothing in
    the file uses one today."""
    if ws.get("status"):
        return ws["status"]
    ts = [t["status"] for t in ws["tasks"]]
    if not ts:
        return "queued"
    if all(t == "done" for t in ts):
        return "done"
    for s in ("in-progress", "next"):
        if s in ts:
            return s
    return "queued"


def _pips(ts):
    n = {c["key"]: sum(1 for t in ts if t["status"] == c["key"]) for c in WORK_COLS}
    out = []
    for key, short, cls in (("queued", "Q", ""), ("next", "N", "n"),
                            ("in-progress", "P", "p"), ("done", "D", "d")):
        if n[key]:
            out.append(f'<span class="{cls}">{short}&nbsp;{n[key]}</span>')
    return f'<div class="bpips">{"".join(out)}</div>' if out else ""


def _cols(items_for):
    """The four columns, drawn once and used by both boards."""
    out = []
    for col in WORK_COLS:
        cards = items_for(col["key"])
        out.append(
            f'<div class="bcol" style="--col:{col["color"]}">'
            f'<h3><span class="dot"></span>{html.escape(col["label"])}'
            f'<span class="n">{len(cards)}</span></h3>'
            + ("".join(cards) if cards else '<p class="empty">—</p>')
            + "</div>")
    return f'<div class="board">{"".join(out)}</div>'


def work_board(root):
    """The top board: one card per workstream, in the column its tasks put it in."""
    def cards(key):
        out = []
        for ws in WORK["workstreams"]:
            if ws_status(ws) != key:
                continue
            ts = ws["tasks"]
            done = sum(1 for t in ts if t["status"] == "done")
            pct = round(done * 100 / len(ts)) if ts else 0
            out.append(
                f'<a class="bcard" href="{root}{ws["id"]}/" style="--ws:{ws["color"]}">'
                f'<b>{html.escape(ws["title"])}</b>'
                f'<div class="bbar"><i style="width:{pct}%"></i></div>'
                + _pips(ts) + "</a>")
        return out
    return _cols(cards)


def ws_board(ws, root):
    """One workstream's own board: the same four columns, carrying its tasks."""
    def cards(key):
        out = []
        for t in ws["tasks"]:
            if t["status"] != key:
                continue
            memo = t.get("memo")
            who = []
            if t.get("owner"):
                who.append(WORK["sources"].get(t["owner"], t["owner"]))
            if memo:
                who.append(f'<a href="{MEMO_ROOT}{memo}/">memo {MEMO_BY_ID[memo]["date"]}</a>')
            out.append(
                f'<div class="bcard" style="--ws:{ws["color"]}" id="{html.escape(t["id"])}">'
                f'<span class="tid">{html.escape(t["id"])}</span>'
                f'<b>{html.escape(t["title"])}</b>'
                f'<p>{t["description"]}</p>'
                + (f'<span class="blocked"><b>Blocked on</b> {t["blocked"]}</span>'
                   if t.get("blocked") else "")
                + (f'<span class="who">{" · ".join(who)}</span>' if who else "")
                + "</div>")
        return out
    return _cols(cards)


WORK_ROOT = "/admin/work/"
MEMO_ROOT = "/admin/memos/"
RAIL_ROOT = "/admin/rails/"


def _console_page(out_dir, ctx_shared, url, fm, crumb, body, src_md):
    """Emit one console page and its markdown twin. Every generated admin page
    goes through here, so none of them can quietly miss a twin — an agent reads
    the markdown and a page without one is a page it cannot see."""
    ctx = dict(ctx_shared)
    ctx.update({"page": url, "page_url": url, "fm": fm, "toc": []})
    fm.setdefault("robots", "noindex,follow")
    page = {"fm": fm, "url": url, "crumb": crumb, "nav_match": "/ledger/", "src_md": src_md}
    target = out_dir / url.strip("/") / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(console_html(page, ctx, shortcodes_inline(body, ctx)))
    (target.parent / "index.md").write_text(src_md.rstrip("\n") + f"\n\n---\n\n{LICENCE_STAMP}\n")
    return fm["title"]


def _strip(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s))



# ------------------------------------------- hard rule 12, and somebody's words ----
# The rule bars three words from this site, with NO ALLOWLIST — and the check that
# holds it says in its own comment why: an allowance is a thing that widens, one
# section becoming one page becoming "in context".
#
# A memo is somebody else's words and is kept word for word, and one of them uses a
# barred term in passing. That is a real collision between two things this site is
# right about, and there are only three ways out: edit the quotation, widen the
# rule, or say what happened.
#
# IT SAYS WHAT HAPPENED. The term is withheld in place — a visible marker where the
# word was, counted, named by which of the three it is, and linked to the page that
# explains the ruling. The source file keeps the memo intact; only the rendering
# withholds. And the promise on the page changes with it: "nothing trimmed" becomes
# "nothing trimmed, one term withheld and marked", because a promise that is nearly
# true is worse than a smaller one that is exactly true.
#
# Whether a quotation should have been in scope at all is not the builder's call.
# It is a ruling, it is on the board, and if it goes the other way this function is
# deleted rather than adjusted.
WITHHELD_TERMS = [
    (re.compile(r"\bzero[- ]knowledge\b", re.I), "the contested encryption term"),
    (re.compile(r"\bmemory\b", re.I), "the contested durability term"),
    (re.compile(r"\bagentic\b", re.I), "the contested autonomy term"),
]


def withhold(text):
    """(text with every barred term replaced by a marker, [which terms])."""
    found = []

    def swap(label):
        def f(_m):
            found.append(label)
            return f"\u27e6withheld \u2014 {label}\u27e7"
        return f

    for rx, label in WITHHELD_TERMS:
        text = rx.sub(swap(label), text)
    return text, found

def work_pages(out_dir, ctx_shared):
    """The board, and one page per workstream."""
    made = {}
    cols_note = "".join(
        f'<div class="row2"><div><b>{html.escape(c["label"])}</b><p>{html.escape(c["meaning"])}</p>'
        f"</div><span class=\"st st--{i + 1}\">{html.escape(c['key'])}</span></div>"
        for i, c in enumerate(WORK_COLS))
    total = sum(len(w["tasks"]) for w in WORK["workstreams"])
    open_n = sum(1 for w in WORK["workstreams"] for t in w["tasks"] if t["status"] != "done")

    body = (
        f'<p class="lead">{html.escape(WORK["_what_this_is"])}</p>'
        + work_board(WORK_ROOT)
        + '<h2 id="how-a-unit-of-work-gets-here">How a unit of work gets here</h2>'
        f'<p>{html.escape(WORK["_how_to_add"])}</p>'
        '<p><b>A workstream is never dragged.</b> The column a workstream card sits in is computed '
        'from the tasks inside it — all done and it is done, anything in progress and it is in '
        'progress — so the board above cannot say something the board inside a card contradicts. '
        'The progress bar is <em>done over total</em> and nothing else; it is not an estimate and it '
        'is not a percentage of effort.</p>'
        '<h2 id="the-four-columns">The four columns</h2>'
        f'<div class="rows">{cols_note}</div>'
        '<h2 id="where-this-shape-came-from">Where this shape came from</h2>'
        '<p>The two-level board — workstream cards whose column is derived, opening into that '
        'workstream’s own tasks in the same four columns — is the one running at '
        '<a href="https://sgraph.ai/en-gb/dev/workstreams/">sgraph.ai/en-gb/dev/workstreams/</a>, '
        'read on 16 September 2026. The column names and their colours are that board’s, kept '
        'deliberately, so somebody who reads both reads one scale rather than two.</p>'
        '<p><b>What is not adopted is how it is fed.</b> That board reads its JSON out of an '
        'encrypted vault at runtime with a published read key, which is the right answer for a site '
        'built to do that. This one renders at build time from a file in the repository, because '
        'every page on this store opens no connection and '
        '{{claim:lab-brief-stays-local}}</p>')

    md = [f"# The work\n\n{_strip(WORK['_what_this_is'])}\n",
          f"**{len(WORK['workstreams'])} workstreams · {total} units of work · {open_n} not done.**\n"]
    for ws in WORK["workstreams"]:
        md.append(f"\n## {ws['title']} — {ws_status(ws)}\n\n{_strip(ws['description'])}\n")
        for t in ws["tasks"]:
            md.append(f"- **{t['id']} · {t['title']}** — `{t['status']}` — {_strip(t['description'])}"
                      + (f" _Blocked on: {_strip(t['blocked'])}_" if t.get("blocked") else ""))
        md.append("")
    made[WORK_ROOT] = _console_page(
        out_dir, ctx_shared, WORK_ROOT,
        {"title": "The work",
         "description": ("Every unit of work for this store as a two-level board: nine workstreams "
                         "whose column is derived from the tasks inside them, and one page per "
                         "workstream. Generated from data/admin/work.json."),
         "blurb": (f"<b>{len(WORK['workstreams'])} workstreams · {total} units of work · "
                   f"{open_n} not done.</b> Every card is generated from one file, and a workstream "
                   "moves only because a task in it moved.")},
        ' / <a href="/admin/">admin</a> / work', body, "\n".join(md))

    for ws in WORK["workstreams"]:
        url = f"{WORK_ROOT}{ws['id']}/"
        ts = ws["tasks"]
        done = sum(1 for t in ts if t["status"] == "done")
        memo = ws.get("memo")
        wb = (
            (f'<div class="panel r2"><p><b>This workstream came out of a memo.</b> '
               f'<a href="{MEMO_ROOT}{memo}/">{html.escape(MEMO_BY_ID[memo]["title"])}</a>, '
               f'{html.escape(MEMO_BY_ID[memo]["date"])} — kept verbatim, read into a brief, and '
               f'broken into the units below.</p></div>' if memo else "")
            + ws_board(ws, WORK_ROOT)
            + f'<p><a href="{WORK_ROOT}">← every workstream</a></p>')
        m = [f"# {ws['title']}\n\n{_strip(ws['description'])}\n",
             f"**{done} of {len(ts)} done.** Status: `{ws_status(ws)}`.\n"]
        if memo:
            m.append(f"From the memo *{MEMO_BY_ID[memo]['title']}* "
                     f"({MEMO_BY_ID[memo]['date']}) — {SITE['base']}{MEMO_ROOT}{memo}/\n")
        for t in ts:
            m.append(f"- **{t['id']} · {t['title']}** — `{t['status']}` — {_strip(t['description'])}"
                     + (f" _Blocked on: {_strip(t['blocked'])}_" if t.get("blocked") else ""))
        made[url] = _console_page(
            out_dir, ctx_shared, url,
            {"title": ws["title"],
             "description": _strip(ws["description"])[:300],
             "blurb": f"<b>{done} of {len(ts)} units done.</b> {html.escape(ws['description'])}"},
            f' / <a href="{WORK_ROOT}">work</a> / {html.escape(ws["id"])}', wb, "\n".join(m))
    return made


def memo_pages(out_dir, ctx_shared):
    """The queue: one page per memo, kept verbatim, with what we read in it and
    the units of work it produced — pulled live off the board rather than listed
    here a second time."""
    made = {}
    steps = "".join(f"<li><b>{html.escape(a)}</b><p>{html.escape(b)}</p></li>"
                    for a, b in MEMOS["_the_process"])
    rows = []
    for m in MEMOS["memos"]:
        ws_ids = [i for i in m["workstreams"] if i in WORK_BY_ID]
        n = sum(len(WORK_BY_ID[i]["tasks"]) for i in ws_ids)
        done = sum(1 for i in ws_ids for t in WORK_BY_ID[i]["tasks"] if t["status"] == "done")
        rows.append(
            f'<div class="row2"><div><b><a href="{MEMO_ROOT}{m["id"]}/">'
            f'{html.escape(m["title"])}</a></b><p>{html.escape(m["summary"])}</p></div>'
            f'<span class="st st--{4 if done == n else 2}">{m["date"]} · {done}/{n}</span></div>')

    body = (
        f'<p class="lead">{html.escape(MEMOS["_what_this_is"])}</p>'
        f'<div class="rows">{"".join(rows)}</div>'
        '<h2 id="the-process">The four steps</h2>'
        f'<ol class="steps">{steps}</ol>'
        '<h2 id="why-verbatim">Why the memo is kept word for word</h2>'
        f'<p>{html.escape(MEMOS["_why_verbatim"])}</p>')
    md = ["# The memo queue\n", _strip(MEMOS["_what_this_is"]), ""]
    for m in MEMOS["memos"]:
        md.append(f"- **{m['date']} — {m['title']}** — {m['summary']} — "
                  f"{SITE['base']}{MEMO_ROOT}{m['id']}/")
    made[MEMO_ROOT] = _console_page(
        out_dir, ctx_shared, MEMO_ROOT,
        {"title": "The memo queue",
         "description": ("Every memo from the project lead, kept verbatim, read into a brief and "
                         "broken into units of work on the board. Three so far."),
         "blurb": (f"<b>{len(MEMOS['memos'])} memos.</b> Captured word for word, read into a brief, "
                   "broken into units of work. The state below is read off the board, not typed.")},
        ' / <a href="/admin/">admin</a> / memos', body, "\n".join(md))

    for m in MEMOS["memos"]:
        url = f"{MEMO_ROOT}{m['id']}/"
        ws_ids = [i for i in m["workstreams"] if i in WORK_BY_ID]
        units = "".join(
            f'<div class="row2"><div><b><a href="{WORK_ROOT}{i}/">'
            f'{html.escape(WORK_BY_ID[i]["title"])}</a></b>'
            f'<p>{html.escape(WORK_BY_ID[i]["description"])}</p></div>'
            f'<span class="st st--{4 if ws_status(WORK_BY_ID[i]) == "done" else 2}">'
            f'{sum(1 for t in WORK_BY_ID[i]["tasks"] if t["status"] == "done")}'
            f'/{len(WORK_BY_ID[i]["tasks"])}</span></div>' for i in ws_ids)
        said, held = withhold(m["verbatim"])
        verb = "".join(f"<p>{html.escape(par)}</p>"
                       for par in said.split("\n\n") if par.strip())
        held_note = ("" if not held else
                     '<p class="withheld-note"><b>Something was withheld, and this is it.</b> '
                     + ("A term" if len(held) == 1 else f"{len(held)} terms")
                     + " in the memo "
                     + ("is" if len(held) == 1 else "are")
                     + " barred from this site by a ruling \u2014 "
                     + ", ".join(sorted(set(held)))
                     + ' \u2014 so '
                     + ("it is" if len(held) == 1 else "they are")
                     + ' marked in place rather than cut quietly or the rule bent to admit '
                     + ("it" if len(held) == 1 else "them")
                     + '. The memo itself is intact in <code>data/admin/memos.json</code>. '
                     '<a href="/disclosures/">Why these words are not used here</a>.</p>')
        body = (
            '<h2 id="verbatim">The memo, word for word</h2>'
            + f'<p>{html.escape(m["form"].rstrip("."))}. Nothing trimmed, reordered or paraphrased'
            + ('.' if not held else
               f', and {len(held)} term{"" if len(held) == 1 else "s"} withheld and marked.')
            + ' The reading of it below is ours and is kept separate on purpose.</p>'
            + held_note
            + f'<div class="panel">{verb}</div>' 
            '<h2 id="what-we-read-in-it">What we read in it</h2>'
            + "".join(f'<div class="panel"><h3>{html.escape(h)}</h3><p>{t}</p></div>'
                      for h, t in m["read"])
            + '<h2 id="not-decided">What this does not decide</h2>'
            '<p>Written down rather than guessed at. A memo is a direction; these are the places it '
            'stops, and every one of them is somebody’s call rather than a gap in the transcript.</p>'
            + "".join(f'<div class="panel r2"><h3>{html.escape(h)}</h3><p>{t}</p></div>'
                      for h, t in m["not_decided"])
            + '<h2 id="the-work-it-produced">The work it produced</h2>'
            '<p>Live off the board. If a unit below moves, this moves with it.</p>'
            f'<div class="rows">{units}</div>'
            f'<p><a href="{MEMO_ROOT}">← the queue</a></p>')
        md = [f"# {m['title']}\n", f"*{m['date']} · {m['form']}*\n", m["summary"], "",
              "## The memo, word for word\n"]
        if held:
            md.append("*" + ", ".join(sorted(set(held)))
                      + f" \u2014 {len(held)} term(s) withheld in place and marked. "
                      + 'See /disclosures/.*\n')
        md += ["> " + said.replace("\n", "\n> "), "",
              "## What we read in it\n"]
        md += [f"### {h}\n\n{_strip(t)}\n" for h, t in m["read"]]
        md += ["## What this does not decide\n"]
        md += [f"### {h}\n\n{_strip(t)}\n" for h, t in m["not_decided"]]
        md += ["## The work it produced\n"]
        md += [f"- **{WORK_BY_ID[i]['title']}** — {SITE['base']}{WORK_ROOT}{i}/" for i in ws_ids]
        made[url] = _console_page(
            out_dir, ctx_shared, url,
            {"title": m["title"], "description": m["summary"],
             "blurb": f"<b>{m['date']}.</b> {html.escape(m['summary'])}"},
            f' / <a href="{MEMO_ROOT}">memos</a> / {html.escape(m["date"])}', body, "\n".join(md))
    return made


def stripe_catalogue():
    """The Stripe catalogue, as data/offers.yml implies it — beside what the
    dashboard actually holds.

    THIS STOPPED BEING A WISH-LIST ON 16 SEPTEMBER. The products exist now, so
    the file is a reconciliation: what the offers imply, what Stripe has, and
    whether the two agree. The site cannot ask Stripe anything — it opens no
    connection — so the other side comes from the dashboard's own CSV export,
    committed at data/admin/stripe-products.csv, plus the amounts read off the
    product list on the same day.

    AND THE SHAPE IS THEIRS, NOT THE ONE THIS FILE FIRST GUESSED. The two upper
    levels are two products each, DEPOSIT and DELIVERY, summing to the full
    price — rather than a full price with a deposit hung off it. A buyer paying
    in full adds both lines. The store has said "a fifth now and the rest on
    delivery" since it had prices; this is that sentence as two rows instead of
    a rule somebody has to remember to apply."""
    rows = []
    for o in OFFERS:
        # An offer priced as a band has no single number, so it has no Stripe
        # product and it is not quietly given one. Two of the six are bands.
        if not o["price_min"] or o["price_min"] != o["price_max"]:
            continue
        pct = o.get("pay_now_pct", 100)
        key = f"ABP-{o['id'].upper()}"
        if pct == 100:
            rows.append({"code": key, "offer": o["id"], "part": "full",
                         "currency": "gbp", "unit_amount": o["price_min"],
                         "label": o["price_label"], "product": o["question"]})
        else:
            dep = o["price_min"] * pct // 100
            rows.append({"code": key + "-DEPOSIT", "offer": o["id"], "part": "deposit",
                         "currency": "gbp", "unit_amount": dep,
                         "label": f"{pct}% of {o['price_label']}", "product": o["question"]})
            rows.append({"code": key + "-DELIVERY", "offer": o["id"], "part": "delivery",
                         "currency": "gbp", "unit_amount": o["price_min"] - dep,
                         "label": f"the remaining {100 - pct}%", "product": o["question"]})

    live = {(p["offer"], p["part"]): p for p in STRIPE_PRODUCTS["products"]}
    for r in rows:
        got = live.get((r["offer"], r["part"]))
        r["stripe_id"] = got["id"] if got else None
        r["stripe_name"] = got["name"] if got else None
        r["stripe_code"] = got.get("price_description") if got else None
        # Agreement is BOTH halves. A product at the right price under the wrong
        # code is a line item a handler cannot map back to a level, which is the
        # failure that only shows up after somebody has already paid.
        r["agrees"] = (bool(got) and got["amount"] == r["unit_amount"]
                       and got.get("price_description") == r["code"])

    return {"_what_this_is": ("What the Stripe catalogue should be, generated from "
                             "data/offers.yml, reconciled against what the dashboard actually "
                             "holds. Copy from here rather than by eye."),
            "_never_here": ("No key of any kind, and no shape. The fifteen shapes are a "
                            "selection carried in the order reference and resolved on this side. "
                            "A product id is not a secret and is published deliberately; a "
                            "secret key is refused everywhere in this repository."),
            "_reconciled_against": STRIPE_PRODUCTS["captured"],
            "version": SITE["version"], "currency": "gbp", "prices": rows}


def rails_pages(out_dir, ctx_shared):
    """One page per payment rail, plus the index that compares them."""
    made = {}
    shared = RAIL_PLANS["shared"]
    sh = ("<h2 id=\"what-both-rails-are-handed\">" + html.escape(shared["title"]) + "</h2>"
          f'<div class="panel r2"><p>{shared["note"]}</p></div>'
          + '<h3>Given</h3><div class="rows">'
          + "".join(f'<div class="row2"><div><b>{a}</b><p>{b}</p></div></div>'
                    for a, b in shared["given"]) + "</div>"
          + '<h3>Never given</h3><div class="rows">'
          + "".join(f'<div class="row2"><div><b>{a}</b><p>{b}</p></div></div>'
                    for a, b in shared["never_given"]) + "</div>")

    rows = "".join(
        f'<div class="row2"><div><b><a href="{r["url"]}">{html.escape(r["name"])}</a></b>'
        f'<p>{html.escape(r["one_line"])}</p></div>'
        f'<span class="st st--{r["rank"]}">{html.escape(r["state"])}</span></div>'
        for r in RAIL_PLANS["rails"])
    body = (
        '<p class="lead">Two rails, neither of them live. '
        '{{claim:checkout-links-not-issued}} These are the plans that end that — what each provider '
        'is handed, what has to exist before a first real order, and in what order.</p>'
        f'<div class="rows">{rows}</div>' + sh)
    md = ["# Turning on a payment rail\n", _strip(RAIL_PLANS["_what_this_is"]), ""]
    md += [f"- **{r['name']}** — {r['state']} — {r['one_line']} — {SITE['base']}{r['url']}"
           for r in RAIL_PLANS["rails"]]
    made[RAIL_ROOT] = _console_page(
        out_dir, ctx_shared, RAIL_ROOT,
        {"title": "Taking money",
         "description": ("How each payment rail gets turned on: what the provider is handed, what "
                         "it is never handed, and what has to exist before a first real order."),
         "blurb": "<b>Two rails. Neither is live.</b> What each one is handed, and the order the "
                  "steps have to happen in."},
        ' / <a href="/admin/">admin</a> / rails', body, "\n".join(md))

    for r in RAIL_PLANS["rails"]:
        steps = "".join(
            f"<li><b>{a}</b><p>{b}</p>"
            + (f'<p class="blocked-on"><b>Blocked on.</b> {c}</p>' if c else "")
            + "</li>" for a, b, c in r["steps"])
        body = (
            "".join(f'<div class="panel"><p>{w}</p></div>' for w in r["why"])
            + '<h2 id="the-contract">What this rail is handed</h2><div class="rows">'
            + "".join(f'<div class="row2"><div><b>{a}</b><p>{b}</p></div></div>'
                      for a, b in r["contract"]) + "</div>"
            + f'<h2 id="the-steps">The steps, in order</h2><ol class="steps">{steps}</ol>'
            + '<h2 id="still-open">Still open</h2>'
            + "".join(f'<div class="panel r2"><h3>{html.escape(a)}</h3><p>{b}</p></div>'
                      for a, b in r["open"])
            + (('<h2 id="the-catalogue">The catalogue, reconciled</h2>'
                '<p><b>The products exist.</b> Six of them, created on 16 September, and the two '
                'upper levels are split into a <code>DEPOSIT</code> and a <code>DELIVERY</code> '
                'that sum to the price — which is the store\'s own "a fifth now and the rest on '
                'delivery" as two rows rather than a rule somebody has to remember. A buyer paying '
                'in full adds both lines.</p>'
                '<p>So this table is a reconciliation rather than a shopping list: the left is what '
                '<code>data/offers.yml</code> implies, the right is what the dashboard actually '
                'holds. <b>This site cannot ask Stripe anything</b> — it opens no connection — so '
                'the other side is the dashboard\'s own CSV export, committed at '
                '<code>data/admin/stripe-products.csv</code>, with the amounts read off the product '
                'list the same day. Weaker than an API call, and the strongest thing a static site '
                'can honestly do: it catches a price changed here and not there, which is the '
                'direction that actually happens.</p>'
                f'<p>Served beside this page as '
                f'<a href="{r["url"]}catalogue.json"><code>catalogue.json</code></a>. It carries no '
                'key and no shape. A product id is not a secret and is printed on purpose.</p>'
                '<div class="rows">'
                + "".join(
                    f'<div class="row2"><div><b><code>{q["code"]}</code></b>'
                    f'<p>{html.escape(q["product"])} — {html.escape(q["label"])}'
                    + (f' · <code>{html.escape(q["stripe_id"])}</code>'
                       if q.get("stripe_id") else " · <b>not in the dashboard</b>")
                    + (f'<br><span class="dim">{html.escape(q["stripe_name"])}</span>'
                       if q.get("stripe_name") else "")
                    + "</p></div>"
                    f'<span class="st st--{4 if q.get("agrees") else 1}">'
                    f'{q["unit_amount"]}p{"" if q.get("agrees") else " ✗"}</span></div>'
                    for q in stripe_catalogue()["prices"]) + "</div>"
                '<p class="small">The account carries one more product that is not listed and is '
                'not reconciled: it belongs to a different part of the estate and this store '
                'neither sells it nor tracks it.</p>')
               if r["id"] == "stripe" else "")
            + f'<p><a href="{RAIL_ROOT}">← both rails</a></p>')
        md = [f"# {r['name']}\n", f"**{r['state']}** — {r['one_line']}\n", "## Why\n"]
        md += [_strip(w) + "\n" for w in r["why"]]
        md += ["## What this rail is handed\n"] + [f"- **{_strip(a)}** — {_strip(b)}"
                                                   for a, b in r["contract"]] + [""]
        md += ["## The steps, in order\n"]
        md += [f"{i}. **{_strip(a)}** — {_strip(b)}"
               + (f" _Blocked on: {_strip(c)}_" if c else "")
               for i, (a, b, c) in enumerate(r["steps"], 1)] + [""]
        md += ["## Still open\n"] + [f"- **{_strip(a)}** — {_strip(b)}" for a, b in r["open"]]
        made[r["url"]] = _console_page(
            out_dir, ctx_shared, r["url"],
            {"title": r["name"], "description": r["one_line"],
             "blurb": f"<b>{html.escape(r['state'])}</b> {html.escape(r['one_line'])}"},
            f' / <a href="{RAIL_ROOT}">rails</a> / {html.escape(r["id"])}', body, "\n".join(md))
        if r["id"] == "stripe":
            (out_dir / r["url"].strip("/") / "catalogue.json").write_text(
                json.dumps(stripe_catalogue(), indent=2) + "\n")
    return made


def block_console_dash(ctx):
    """The dashboard. Every number on it is computed by console_counts() from the
    same files the pages are built from, so a tile cannot disagree with the page
    it points at. Nothing here is typed."""
    c = console_counts()
    tiles = [
        ("r1", c["blockers"], "blocking a first paid order",
         "no rail is live" if not c["rails_live"] else ""),
        ("r2", c["work_next"], "units of work in flight",
         f"of {c['work_total']} across {c['workstreams']}"),
        ("r3", c["memos"], "memos in the queue", "captured, read, broken up"),
        ("r3", c["reviews"], "reviews, dated and kept", f"{c['proposals']} proposals"),
        ("r4", c["claims"], "claims in the ledger", f"{c['rulings']} awaiting a ruling"),
        ("r3", c["skus"], "things that can be bought",
         f"{c['shapes']} shapes, {c['offers']} offers"),
    ]
    tile_html = "".join(
        f'<div class="tile {r}"><b>{n}</b><span>{html.escape(lab)}</span>'
        + (f"<em>{html.escape(sub)}</em>" if sub else "") + "</div>"
        for r, n, lab, sub in tiles)

    # What is next, read off the board rather than listed here a second time.
    nxt = [(ws, task) for ws in WORK["workstreams"] for task in ws["tasks"]
           if task["status"] in ("next", "in-progress")]
    rows = "".join(
        f'<div class="row2"><div><b><a href="{WORK_ROOT}{ws["id"]}/#{t["id"]}">'
        f'{html.escape(t["title"])}</a></b>'
        f'<p>{html.escape(ws["title"])}'
        + (f' · <b>blocked on</b> {_strip(t["blocked"])}' if t.get("blocked") else "")
        + f'</p></div><span class="st st--{2 if t.get("blocked") else 3}">'
        f'{html.escape(t["id"])}</span></div>' for ws, t in nxt)

    return (f'<div class="tiles">{tile_html}</div>'
            f'<h2 id="in-flight">In flight — {len(nxt)} units of work</h2>'
            '<p>Read off <a href="/admin/work/">the board</a>. A unit is here because it is next in '
            'its workstream or being worked on now; it is not here because somebody added it to a '
            'list twice.</p>'
            f'<div class="rows">{rows}</div>')


BLOCKS["console-dash"] = block_console_dash


# ----------------------------------------------- what has actually been done ----
# THE CORRECTION OF 16 SEPTEMBER, AND WHY IT NEEDED ONE.
#
# This store's claims said the £500 and £1,500 levels had never run for a paying
# buyer. Every word of that was true. What a reader took from it was that nobody
# had ever done this work at all — and that is false, and it was costing sales to
# a site whose whole argument is that it does not print false things.
#
# The evidence was never missing. It was published on a different domain and never
# linked from here. So: the evidence leads, the disclosure narrows to the thing
# that is genuinely undone — a sale through this checkout — and nothing true gets
# deleted.
#
# NO READ KEY IS PRINTED BY THIS BLOCK. Every vault below publishes its own on its
# own page, which is where a reader gets it. That keeps this store's key surface at
# exactly one vault, and check_read_keys_are_only_for_published_vaults holds it.
EVIDENCE = yaml_load((DATA / "evidence.yml").read_text())


def block_evidence(ctx):
    ctx["external_links"].update(w["url"] for w in EVIDENCE["works"])
    rows = "".join(
        f'<div class="ev"><div class="ev-h">'
        f'<a href="{w["url"]}"><b>{html.escape(w["title"])}</b></a>'
        f'<span class="ev-m"><code>{html.escape(w["vault"])}</code> · '
        f'{html.escape(w["size"])} · {html.escape(w["published"])}</span></div>'
        f'<p class="ev-q">&ldquo;{html.escape(w["quoted"])}&rdquo;</p>'
        f'<p class="ev-w">{inline(w["why"], ctx)}</p></div>'
        for w in EVIDENCE["works"])
    return (
        f'<p class="lead">{inline(EVIDENCE["note"], ctx)} Each one opens with a read key '
        'published on its own page — no account, nothing to install, and nothing asked of you '
        'for looking.</p>'
        f'<div class="ev-grid">{rows}</div>'
        f'<p class="small dim">Quoted from <a href="{EVIDENCE["source"]}">the published '
        f'catalogue</a>, retrieved {html.escape(EVIDENCE["retrieved"])}. It is generated at '
        'sgit.ai from the same file that site\'s own table is built from, so the descriptions '
        'above are that catalogue\'s words rather than this store\'s.</p>')


BLOCKS["evidence"] = block_evidence


def block_buy_cards(ctx):
    """The four things for sale, as a shop shows them.

    THE BRIEF FOR THIS IS PHYSICAL, NOT VISUAL. A laptop or a tablet turned round
    at an event, a person standing next to the buyer: who are you, here is your
    thing, buy it. So the targets are large, there are four of them, every card
    carries the three facts somebody decides on — what it is, what it costs, when
    it arrives — and none of them is a paragraph you have to read to the end of.

    The state chip stays. It is not decoration and it is not a hedge: two of these
    have never been bought here and a shop that hides that is the thing this site
    exists not to be. What changed on 16 September is that it no longer stands in
    for whether the work has ever been done, which it was doing silently."""
    cards = []
    for l in LEVELS:
        o = OFFERS_BY_ID[l["offer"]]
        cards.append(
            f'<div class="sku" id="sku-{l["id"]}">'
            f'<div class="sku-n">{l["n"]}</div>'
            f'<h3 class="sku-name">{html.escape(l["name"])}</h3>'
            f'<p class="sku-who">{html.escape(l["who"])}</p>'
            f'<div class="sku-price"><b>{html.escape(l["price_label"])}</b>'
            f'<span>{html.escape(o["eta"])}</span></div>'
            f'<p class="sku-lede">{inline(l["lede"], ctx)}</p>'
            f'<p class="sku-state">{chip(o["state_badge"], claim_id=o["claim"])}</p>'
            f'<p class="sku-go">{checkout_html(o, ctx)}'
            f'<a class="sku-more" href="/d/{o["id"]}/">What arrives, and what does not &rarr;</a>'
            "</p></div>")
    # The island goes with the cards, because a code applied by following a link has
    # to change the price on the card the buyer is looking at. Without it shop.js
    # takes its no-model path on this page and paints only the order badge, so a
    # 100% code would leave four full prices on screen and the person holding the
    # laptop would have to explain that it had worked.
    return (shop_island(rel_prefix(ctx["page_url"]))
            + f'<div class="skus">{"".join(cards)}</div>')


BLOCKS["buy-cards"] = block_buy_cards


def block_code_links(ctx):
    """A code as a LINK, which is the only form it should ever be handed over in.

    THE POINT IS THE COUNTER. A laptop turned round at a stand: somebody says
    what they are, they pick a thing, and the price on the card should already be
    what they are going to pay. Reading a code off a card and typing it into a
    field is two steps and a typo, and the field does not exist anyway — this site
    has no input on it and a build check keeps it that way.

    So the code travels in the address. shop.js takes it, applies it, repaints the
    four prices, and strips it out of the address bar before anybody sees it —
    so the link can be sent, opened, and the page it lands on is a shop with the
    discount already on it and nothing to fill in.

    ONLY PRINTABLE CODES APPEAR HERE, and check_discount_codes_are_not_printed
    fails the release if any other one reaches the built site in plain text. The
    four that are not printable ship as a SHA-256 and nothing else."""
    rows = []
    for d in DISCOUNTS:
        if not d["printable"]:
            continue
        code = str(d["code"])
        link = f"{SITE['base']}/?code={code}"
        rows.append(
            f'<div class="row2"><div><b>{html.escape(d["label"])}</b>'
            f'<p>{html.escape(d["why"])}</p>'
            f'<p><code>{html.escape(link)}</code></p></div>'
            f'<span class="st st--4">{d["pct"]}% off</span></div>')
    hidden = sum(1 for d in DISCOUNTS if not d["printable"])
    return (
        '<div class="rows">' + "".join(rows) + "</div>"
        f'<p class="small">{hidden} more codes exist and are not on this page. They ship as a '
        'SHA-256 and never as a string, so they are not in the built site, not in the markdown '
        'twins and not in this console — a check reads every byte of the output against every '
        'code on every release. Read them out of <code>data/discounts.yml</code>, which is in the '
        'repository and not in the site.</p>'
        '<p class="small">Opening one of these lands on the shop with the discount already '
        'applied and the four prices repainted, and the code is taken out of the address before '
        'the page settles — so it is not in history, not in a bookmark and not in a referrer. '
        'Any page here takes <code>?code=</code>, not just the front one.</p>')


BLOCKS["code-links"] = block_code_links

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
        shell = console_html if page["fm"].get("console") else page_html
        target.write_text(shell(page, ctx, body))
        twin = page["src_md"].rstrip("\n")
        if LICENCE_STAMP not in twin:
            twin += f"\n\n---\n\n{LICENCE_STAMP}\n"
        (target.parent / "index.md").write_text(twin)

    # static assets, verbatim
    shutil.copytree(ASSETS, out_dir / "assets")
    # The two walkthrough PDFs live under /admin/ rather than /assets/ for one
    # reason: they print the walkthrough discount codes, and the check that keeps
    # those codes off every other file in the built site exempts /admin/ alone.
    # Their names carry the version they were taken at, so a stale copy is stale
    # on its face rather than silently.
    _dl = ASSETS / "downloads"
    if _dl.is_dir():
        shutil.copytree(_dl, out_dir / "admin" / "downloads")
        shutil.rmtree(out_dir / "assets" / "downloads")
    if FILES.exists():
        shutil.copytree(FILES, out_dir / "files")

    extra = delivery_pages(out_dir, ctx_shared)
    extra.update(buyer_pages(out_dir, ctx_shared))
    extra.update(lab_pages(out_dir, ctx_shared))
    extra.update(shape_pages(out_dir, ctx_shared))
    extra.update(release_pages(out_dir, ctx_shared))
    extra.update(review_pages(out_dir, ctx_shared))
    # The console's own generated surfaces. They come last because the memo pages
    # read the live state of the board and the board reads the offers, so nothing
    # here may be built before the thing it counts.
    extra.update(rails_pages(out_dir, ctx_shared))
    extra.update(work_pages(out_dir, ctx_shared))
    extra.update(memo_pages(out_dir, ctx_shared))

    # The pack manifest, machine-readable, beside the page that renders it. The
    # documents are held; the hashes are not, so a reader holding the pack can
    # check their copy without being able to read it here.
    (out_dir / "dev-packs" / "pack.json").write_text(json.dumps(PACK, indent=2) + "\n")

    (out_dir / "CNAME").write_text(SITE["domain"] + "\n")
    (out_dir / ".nojekyll").write_text("")
    (out_dir / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE['base']}/sitemap.xml\n")
    # /admin/ and everything under it is public — every page here is — but it is
    # not a selling surface and it carries the walkthrough codes, so it is kept out
    # of the sitemap and marked noindex. The difference between "public" and
    # "advertised" is the whole point: anybody handed the address can read it, and
    # nobody finds it by searching for a discount code.
    # A page that is noindex is out of the sitemap, whatever its address. This used
    # to be a path prefix, which was right while /admin/ was the only unadvertised
    # thing and wrong the moment a redirect stub outside it needed the same treatment.
    noindexed = {u for u, (pg, _c, _b) in rendered.items()
                 if "noindex" in (pg["fm"].get("robots") or "")}
    noindexed |= {u for u in extra if u.startswith("/admin/")}
    urls = "".join(f"<url><loc>{SITE['base']}{u}</loc></url>"
                   for u in sorted(set(rendered) | set(extra)) if u not in noindexed)
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
             # The delivery estimate and the clock it starts on. Both, always: an
             # estimate without its start is the half a consumer of this index
             # would print and the half that would make it a lie.
             "eta": o["eta"], "eta_from": o["eta_from"], "eta_why": o["eta_why"],
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
        "<page>/index.md. No page on this site that sells anything opens a network connection at all; "
        "the review pages under /admin/reviews/ embed the vault they review, from one host, and "
        "say so. Nothing here sends anything about a reader, on any page.",
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
    # /admin/ is left out, and llms.txt still lists it with its description and its
    # address. The walkthrough page is noindex because it prints working discount
    # codes and "public" and "advertised" are different things — and a bulk file
    # that IS indexed, carrying the same codes, would make that sentence false.
    # An agent that wants the walkthrough follows the link in llms.txt and reads
    # /admin/try/index.md, which is the markdown twin every page here has.
    for url, (page, _ctx, _body) in sorted(rendered.items()):
        if url.startswith("/admin/") or "noindex" in (page["fm"].get("robots") or ""):
            continue
        parts += [
            "\n" + "=" * 78,
            f"PAGE {url}  —  {page['fm']['title']}",
            "=" * 78 + "\n",
            page["src_md"].strip(),
        ]
    parts += [
        "\n" + "=" * 78,
        "NOT INCLUDED ABOVE",
        "=" * 78 + "\n",
        "/admin/ and /admin/try/ are omitted from this file on purpose. They are public and",
        "linked from llms.txt; they are noindex, out of sitemap.xml and out of this file because",
        "the walkthrough prints working discount codes. Read them at their own addresses, or as",
        "markdown at /admin/try/index.md.",
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
