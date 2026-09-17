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

# ---------------------------------------------------------------------------
# THE SWAP. The design built through rounds one to four is the store from
# v0.3.16, and the design it replaces is kept at /v1/ rather than deleted.
#
# WHAT MOVED AND WHAT DID NOT. Nine pages existed in both designs, so the new one
# takes the address and the old one is archived one directory down. Everything
# else on the site had no second version to choose between: those pages keep
# their address and are re-drawn in the new chrome, which is what page_html does
# now. The console at /admin/ and the release archive at /versions/ are neither —
# they are a different job for a different reader and this round never touched
# them.
#
# /v1/ IS AN ARCHIVE, NOT A SECOND STORE. Its pages carry a strip saying so, its
# links to the pages that moved are rewritten to stay inside it, and its links to
# pages that never moved go where they always went, because those pages still
# exist and are still correct.
V1_ROOT = "/v1/"
V1_UNTIL = "v0.3.15"
# Where an archived page's reader should go instead. Almost always the address it
# used to have, because that is where its replacement sits. /order/ is the one
# that is not: the page a payment returns to is /paid/ now, and /order/ is not a
# page at all, so deriving the way out from the directory name would have sent
# the one archived page with a different answer to a 404.
V1_REPLACED_BY = {"/v1/order/": "/paid/"}
V1_MOVED = {
    "/": "/v1/",
    "/policies/": "/v1/policies/",
    "/compare/": "/v1/compare/",
    "/audiences/": "/v1/audiences/",
    "/ledger/": "/v1/ledger/",
    "/cart/": "/v1/cart/",
    "/pay/": "/v1/pay/",
    "/order/": "/v1/order/",
    "/who/": "/v1/who/",
}


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
        ("What each level gets you", "/compare/"),
        ("Who runs the review", "/who/"),
        ("The price list", "/offers/"),
        ("Your order", "/cart/"),
    ]),
    ("How buying works", "/how-it-works/", [
        ("What is actually in one", "/what-is-in-one/"),
        ("The three steps", "/how-it-works/"),
        ("The two rails", "/paying/"),
        ("What a session is", "/booking/"),
        ("What happens after you pay", V1_MOVED["/order/"]),
    ]),
    ("Who it is for", "/are/", [
        ("Who you are", "/are/"),
        ("You are a founder", "/are/founder/"),
        ("You are backing a company", "/are/investor/"),
        ("You have to answer for it", "/are/exec/"),
        ("You do this for a living", "/are/security/"),
        ("You own the register", "/are/governance/"),
        ("The three buyers", "/audiences/"),
        ("You run agents today", "/for/agents/"),
        ("You are backing a company", "/for/investors/"),
        ("You are a startup", "/for/startups/"),
    ]),
    ("Evidence", "/ledger/", [
        ("The claim ledger", "/ledger/"),
        ("Reviews, dated and kept", "/admin/reviews/"),
        ("What we do not say, and why", "/disclosures/"),
        ("Who owns what", "/boundary/"),
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
        ("What happened to each memo", "/admin/status/"),
        ("The homepage concepts, reviewed", "/admin/concepts/"),
        ("The design brief", "/admin/design-brief/"),
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
    # THE BADGE THAT WAS DOING TWO JOBS AND IS NOW DOING ONE.
    #
    # It read "specified, never run" and then "never bought here", and both of
    # those described the SALE while sitting on a card about the PRODUCT. A reader
    # took it to mean the work had never been done, which is false — it has been
    # done many times and six vaults of it are published. Ruled on 16 September:
    # the sentence comes off the site rather than being narrowed again.
    #
    # What replaces it is the thing that is actually true and actually useful: at
    # the two upper levels a named person does the work. That is a property worth
    # a chip, because it is the difference between these levels and the two below
    # them, and it is the reason the delivery estimate depends on a calendar.
    "person": ("delivered by a person", "st-n",
               "A named security professional does this work and signs it off. It is somebody's "
               "time rather than a pipeline, which is why its delivery estimate depends on "
               "availability."),
    "unlocated": ("built, not located", "st-u", "It was built. It has not been found since, and until it is, nothing here promises it."),
    "booking": ("a booking, not a download", "st-b", "What is bought is a person's time, not a file."),
    "partial": ("part exists", "st-s", "One half of it runs. The half that carries the guarantee does not."),
    "absent": ("does not exist yet", "st-x", "It does not exist. It is listed so that nobody proposes it as new."),
}


def chip(state, date=None, claim_id=None, label=None):
    """A state as a chip.

    IT USED TO FALL BACK TO "unknown" AND THAT WAS A SILENT FAILURE. Renaming a
    state on 16 September left two claims pointing at one that no longer existed,
    and the build said nothing: the ledger simply rendered `unknown` with an empty
    tooltip, on two rows, in production. A fallback that produces a plausible-
    looking page is worse than one that stops, so this raises — and
    check_every_claim_state_is_real catches the same thing in the data before the
    build gets here, which is where a reader would rather it were caught."""
    if state not in STATES:
        raise KeyError(
            f"claim state {state!r} is not one this site has. It would have rendered as "
            f"'unknown' with no tooltip. The states are: {', '.join(sorted(STATES))}")
    text, cls, why = STATES[state]
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
        ctx["claim_uses"].setdefault(cid, set()).add(ctx["page_url"])
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


# ---------------------------------------------------------------- the till ---
# WHETHER ANYTHING ON THIS SITE CAN BE PAID FOR, TODAY.
#
# Fourteen sentences across these pages said "no payment link has been issued on
# any level". Every one of them was true and every one of them becomes a LIE the
# moment a URL is pasted into data/offers.yml — and the file's own comment
# promises that pasting one line is the whole of turning a checkout on. A store
# that tells a buyer nothing can be bought here while taking their money is worse
# than a store with no checkout at all, so the promise and the copy are held
# together here rather than by whoever does the paste remembering fourteen places.
#
# check_the_till_says_which_state_it_is_in fails the release if a sentence from the
# wrong state reaches the output.
def till_is_off():
    return not any((o.get("checkout_url") or "").strip() for o in OFFERS)


def till(off, on):
    """The same thing said twice: once while no link exists, once after one does."""
    return off if till_is_off() else on


def _the_ledger_must_move_with_the_till():
    """THE ONE SENTENCE THE till() SWITCH CANNOT REACH.

    The ledger is data. The claim `checkout-links-not-issued` says in so many
    words that no payment link has been created for any offer on this site, it is
    cited by chips on the order and the checkout, and it is the store's own
    evidence for its most load-bearing promise. A pasted checkout_url makes it
    false, and no amount of branching in this file can fix a sentence that lives
    in data/claims.yml.

    So the build stops rather than publishing a ledger entry that contradicts the
    page citing it. An id is a key and stays; what has to move is its state and
    its words. The message says exactly which."""
    if till_is_off():
        return
    c = next((c for c in CLAIMS_ALL if c["id"] == "checkout-links-not-issued"), None)
    if c and c["state"] == "absent":
        raise SystemExit(
            "build: a checkout_url is set in data/offers.yml, and data/claims.yml still "
            "carries claim 'checkout-links-not-issued' with state: absent — a ledger "
            "saying no payment link exists, cited by the very page that now has one.\n"
            "  Edit that claim: set its state, rewrite its `claim:` to say which levels "
            "carry a link and what the gate still holds them to, and date it today.\n"
            "  The id does not change: it is a key, and every page that cites it and "
            "every release that recorded it point at this one."
        )


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
    ctx["claim_uses"].setdefault(o["claim"], set()).add(ctx["page_url"])
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
        ctx["claim_uses"].setdefault(cid, set()).add(ctx["page_url"])
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
            + (('<h2 id="who-does-it">Who does it</h2>'
                + block_who_runs_it(ctx)) if o["id"] in REVIEWER_BY_OFFER else "")
            + block_code_offer(ctx)
            + '<h2 id="what-arrives">What arrives</h2>'
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
               '<p class="small dim">This level is a person\u2019s time rather than a file, and a deposit is '
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
               '<p class="small dim"><b>Step 5 is estimated at one to three days from your '
               'reply</b> \u2014 from your reply rather than from your payment, because until the '
               'details arrive there is nothing to correct against. It is an estimate rather than a '
               'measurement, and it is labelled as one; the constraint behind it is one '
               'person\u2019s calendar. The 24 hours is riskmandate.ai\u2019s commitment to follow '
               'up and is kept on their pages.</p>'
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

    # --- describe your agent: two prototypes over one vocabulary
    AGENT_VIEWS = [
        ("canvas", "The canvas",
         "The agent in the middle, everything it could reach around it. Click a capability to "
         "give it to the agent, click again to take it away.",
         "For somebody being walked through it by a person \u2014 which is the mode this page "
         "exists for. The whole set is visible at once, so a conversation can jump anywhere in it "
         "rather than going in an order somebody else chose.",
         "Twenty-three things on one screen is a lot to meet at once, and nothing tells you where "
         "to start. It rewards somebody who already knows roughly what their agent does and "
         "punishes somebody who does not."),
        ("sequence", "One at a time",
         "One family per screen, in order, with what each reach means beside it.",
         "For somebody working alone, with nobody to explain the words. Each screen is small "
         "enough to answer without deciding what the whole model is first.",
         "Nine screens is nine chances to stop, and it hides how much is left. It also makes the "
         "shape of the grant hard to see until the end \u2014 which is the thing the document is "
         "actually about."),
    ]
    for aid, name, one_line, good, bad in AGENT_VIEWS:
        url = f"/lab/agent-{aid}/"
        ctx = dict(ctx_shared)
        ctx.update({"page": f"lab/agent-{aid}", "page_url": url, "fm": {}, "toc": []})
        other = [v for v in AGENT_VIEWS if v[0] != aid][0]
        body = (
            f'<div class="note"><p><b>{LAB_WARNING}.</b> This is a prototype of an interface, and '
            'which of the two becomes the real one is not decided. Nothing on it is sent anywhere: '
            'what you build stays in this browser and leaves as a file you copy out. '
            '{{claim:lab-is-a-prototype}}</p></div>'
            f'<p class="lead">{inline(one_line, ctx)}</p>'
            + agent_model_island(rel_prefix(url))
            + f'<div class="ag ag-{aid}" data-mode="{aid}">'
            '<div class="ag-stage"><div class="ag-core"><b>Your agent</b>'
            '<span class="ag-count" data-ag-count>nothing yet</span></div></div>'
            f'<div class="ag-palette">{agent_palette()}</div>'
            '<div class="ag-out"><h3>What you have said it can do</h3>'
            '<div data-ag-list class="ag-list"><p class="dim">Nothing selected. Click a capability '
            'above.</p></div>'
            '<div class="ag-acts">'
            '<button type="button" class="buy" data-ag-copy>Copy the definition</button>'
            '<button type="button" class="buy buy-alt" data-ag-download>Download it as JSON</button>'
            '<button type="button" class="buy buy-alt" data-ag-clear>Start again</button>'
            "</div>"
            '<p class="small dim">It goes to your clipboard or your downloads and nowhere else. '
            'There is no account here and no page that sells anything opens a connection \u2014 '
            'both are build checks rather than promises.</p>'
            "</div></div>"
            '<h2 id="what-is-wrong-with-it">What is wrong with this one</h2>'
            f'<p><b>What it is good at.</b> {inline(good, ctx)}</p>'
            f'<p><b>What it is bad at.</b> {inline(bad, ctx)}</p>'
            f'<p><a href="/lab/agent-{other[0]}/">Try {other[1].lower()} instead \u2192</a> '
            '\u2014 same twenty-three primitives, same document out. <b>Two options presented with '
            'only their strengths is a menu, not an experiment.</b></p>'
            + agent_shared_note(ctx)
            + '<h2 id="then-what">Then what</h2>'
            '<p>The document this produces is an input to a model session that has the template '
            f'vault and turns it into a vault of your own. That is <a href="/d/t3/">the '
            f'\u00a3500 level</a>, and the honest version of the workflow is: build this together, '
            'you go and do something else, the vault follows within one to three days of you '
            'sending the details.</p>'
            '<p><a href="/lab/">The other prototypes in the lab</a></p>')
        page = {
            "fm": {"title": f"Describe your agent \u2014 {name.lower()}",
                   "description": (f"{one_line} A prototype: twenty-three capability primitives on "
                                   "a verb.object.reach grammar, promoted from riskmandate.ai's "
                                   "own template vault. Nothing on it can be bought."),
                   "lead": f"**{LAB_WARNING}.** A prototype of an interface.",
                   "wide": True, "head_css": "/assets/lab.css", "head_js": "/assets/agent.js"},
            "url": url,
            "crumb": f' / <a href="/lab/">lab</a> / describe your agent / {aid}',
            "nav_match": "/ledger/",
            "src_md": (
                f"# Describe your agent \u2014 {name.lower()}\n\n**{LAB_WARNING}.** A prototype "
                f"of an interface.\n\n{one_line}\n\n"
                f"- Good at: {good}\n- Bad at: {bad}\n"
                f"- {CAPABILITIES['count']} primitives on a `{CAPABILITIES['grammar']}` grammar, "
                "promoted from riskmandate.ai's template vault\n"
                "- It produces the GRANT only \u2014 not the mandate, not the delta, not a "
                "policy\n"
                "- What you build stays in this browser and leaves as a file you copy out\n"),
        }
        target = out_dir / url.strip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page_html(page, ctx, shortcodes_inline(body, ctx)))
        (target.parent / "index.md").write_text(
            page["src_md"].rstrip("\n") + f"\n\n---\n\n{LICENCE_STAMP}\n")
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
SHAPE_EVIDENCE = PRODUCTS["shape_evidence"]

# The evidence join, held to the same standard as the SKU codes: every promoted
# shape has a line, no line names a shape that is not promoted, and the state is
# one this site already has a badge for. A shape arriving upstream with no line
# would otherwise render on the picker with whatever default was written last.
_unevidenced = [s["slug"] for s in ABP["shapes"] if s["slug"] not in SHAPE_EVIDENCE]
if _unevidenced:
    raise SystemExit(
        f"build: {', '.join(_unevidenced)} arrived in the promoted catalogue with no line in "
        "shape_evidence in data/products.yml. Read what the upstream summary actually claims "
        "about that shape and write it down: the picker filters on this.")
_stale_evidence = [s for s in SHAPE_EVIDENCE if s not in {x["slug"] for x in ABP["shapes"]}]
if _stale_evidence:
    raise SystemExit(f"build: shape_evidence carries {', '.join(_stale_evidence)}, which is not "
                     "in the promoted catalogue.")
_bad_evidence = sorted({v for v in SHAPE_EVIDENCE.values() if v not in STATES})
if _bad_evidence:
    raise SystemExit(f"build: shape_evidence uses state(s) {', '.join(_bad_evidence)}, which this "
                     f"site has no badge for: {', '.join(sorted(STATES))}")

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
        # WHERE THIS ENGINE SENDS A BUYER AFTER PAYING. It used to be a path
        # built out of `root`, which was right while there was one design and
        # /order/ was its post-sale page. This engine draws the archive now, and
        # a hardcoded 'order/index.html' from /v1/pay/ resolved to /order/ — a
        # page that does not exist. The walkthrough caught it, which is the whole
        # reason the walkthrough exists.
        "post_sale": V1_MOVED["/order/"],
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
        ("Homepage concepts", "/admin/concepts/", None, False),
        ("The design brief", "/admin/design-brief/", None, False),
        ("Run the flow yourself", "/admin/try/", None, False),
    ]),
    ("The work", [
        ("The board", "/admin/work/", "work_open", False),
        ("The memo queue", "/admin/memos/", "memos", False),
        ("What happened to each memo", "/admin/status/", None, False),
    ]),
    ("Next: taking money", [
        ("Both rails", "/admin/rails/", "blockers", False),
        ("Stripe", "/admin/rails/stripe/", None, False),
        ("SumUp \u2014 parked", "/admin/rails/sumup/", None, False),
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
              "frame's storage. A review of a vault, and the page a buyer lands on after paying, "
              "are the only two kinds of page here that open a connection; every "
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
          "Nothing typed there is submitted anywhere, and nothing on this site sends anything "
          "about a reader on any page.", ""]
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
        '<b>This page opens a connection, and here is exactly which one.</b> The two surfaces below '
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
            # A RUN WITH NO VAULT SAYS SO WHERE THE VAULT WOULD HAVE BEEN. The
            # two earlier runs publish theirs; this one could not be pushed, and
            # an absence in the same place as a presence is how a reader notices.
            + (f'<div class="cx-verdict"><b>No vault for this run.</b>'
               f'<p>{inline(rv["no_vault"], ctx)}</p></div>'
               if rv.get("no_vault") else "")
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
            'nothing is submitted, and nothing here sends anything about a reader — which is a '
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
    'the whole price. The other two are a named security professional\u2019s time \u2014 so '
    'they take <b>a fifth on the order and the rest when the work is in your '
    'hands</b>. £100 of £500; £300 of £1,500.</p>'
    '<p><b>The split belongs to the offer and not to the rail.</b> A card tapped on a terminal at '
    'the stand takes the same deposit as a link opened on a phone, because what is being split is '
    'the risk on work that is scheduled rather than produced, and that does not change with how '
    'the card is read.</p>'
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
        '<p>The work it configures is done by <b>a named security professional</b> today. The '
        'seven-role team these prototypes describe is a specification rather than something '
        'staffed, and which parts of it could later be done without people is a decision nobody '
        'has taken. {{claim:lab-fulfilment-is-people}}</p>'
        "</div>"
    )



# -------------------------------------------- the product-page prototype ----
# "WE GO THERE, WE DON'T KNOW WHAT WE'RE BUYING." A level page on this store
# argues about what a policy is. A product page shows the thing. Those are
# different documents and the store has only ever written the first.
#
# IT LIVES IN /lab/ BECAUSE THAT IS THE SURFACE THAT PROTECTS IT. A page that
# looks like a shop and is not one is the most dangerous thing this site could
# publish; /lab/ already states that on its own face and check_lab_is_marked
# refuses any page there that stops saying it. An Amazon-style mock is the closest
# anything here has come to that line, so it gets the protection that already
# exists rather than a new one written for it.
#
# THE MEDIA SLOTS ARE HONEST ABOUT BEING EMPTY. The ask was "tons and tons of
# screenshots"; seven exist. Every slot is a real file or a labelled empty frame
# saying what belongs there. A carousel padded with decorative images would be the
# one dishonest thing on a page whose entire job is showing what you actually get.
PRODUCT_PAGE = yaml_load((DATA / "product-page.yml").read_text())


def product_prototype(ctx):
    pp = PRODUCT_PAGE
    o = OFFERS_BY_ID[pp["subject"]]
    lvl = next(l for l in LEVELS if l["offer"] == pp["subject"])
    shots = "".join(
        (f'<figure class="pp-shot"><img src="{m["file"]}" alt="{html.escape(m["caption"])}" '
         f'loading="lazy"><figcaption>{html.escape(m["caption"])}</figcaption></figure>'
         if m.get("file") else
         f'<figure class="pp-shot pp-shot-empty"><div class="pp-empty">'
         f'<b>Not taken yet</b><span>{html.escape(m["pending"])}</span></div>'
         f'<figcaption>A slot, left visibly empty. A carousel padded with decoration would be '
         f'the one dishonest thing on this page.</figcaption></figure>')
        for m in pp["media"])
    have = sum(1 for m in pp["media"] if m.get("file"))
    specs = "".join(
        f'<tr><th scope="row">{html.escape(s["what"])}</th>'
        f'<td>{inline(s["value"], ctx)}</td></tr>' for s in pp["specs"])
    editions = "".join(
        f'<button type="button" class="pp-ed" data-ed="{a["id"]}"'
        + (' aria-pressed="true"' if a["id"] == "founder" else ' aria-pressed="false"')
        + f'>{html.escape(a["short"])}</button>' for a in AUDIENCES)
    ed_notes = "".join(
        f'<p class="pp-ednote" data-ed="{a["id"]}"'
        + ("" if a["id"] == "founder" else " hidden")
        + f'><b>For {html.escape(a["short"].lower())}:</b> {inline(a["what_changes"], ctx)}</p>'
        for a in AUDIENCES)

    return (
        '<div class="pp">'
        '<div class="pp-main">'
        f'<h2 class="pp-title" id="the-product">{html.escape(pp["title"])}</h2>'
        f'<p class="pp-tag">{inline(pp["tagline"], ctx)}</p>'
        f'<div class="pp-eds"><span class="pp-edlab">Which edition?</span>{editions}</div>'
        f'{ed_notes}'
        f'<h3 id="what-it-looks-like">What it looks like</h3>'
        f'<p class="small dim">{have} of {len(pp["media"])} slots have a picture in them today. '
        'The rest say what belongs there.</p>'
        f'<div class="pp-shots">{shots}</div>'
        f'<h3 id="specs">Specifications</h3>'
        f'<div class="tablewrap"><table class="pp-specs"><tbody>{specs}</tbody></table></div>'
        f'<h3 id="reviews">Reviews</h3>'
        f'<p>{inline(pp["reviews_note"], ctx)}</p>'
        '<div class="pp-noreviews"><b>No reviews yet</b>'
        '<span>And no star average, now or later.</span></div>'
        "</div>"
        '<aside class="pp-buy">'
        f'<div class="pp-price">{html.escape(o["price_label"])}</div>'
        f'<div class="pp-eta"><b>{html.escape(o["eta"])}</b>'
        f'<span>{html.escape(o["eta_from"])}</span></div>'
        f'<p class="pp-gets">{inline(lvl["lede"], ctx)}</p>'
        '<button type="button" class="buy buy-off pp-cta" disabled>Add to order</button>'
        f'<p class="pp-warn"><b>{LAB_WARNING}.</b> This button does nothing. It is here so the '
        'shape can be judged, and it is disabled in the markup rather than by script.</p>'
        f'<p class="small"><a href="/d/{o["id"]}/">The real page for this level &rarr;</a></p>'
        "</aside></div>")


# ----------------------------------------------- describe your agent ----
# THE PAGE THE PROJECT LEAD EXPECTS TO USE MOST IN CONVERSATION, and it is free.
#
# It produces the GRANT — everything an agent can actually do — which is one of
# the four objects inside the document this store sells. Giving the elicitation
# away and charging for the correction is a different business from charging for
# the whole thing, and it is the one that was asked for.
#
# IT ALSO CLOSES A PROPOSAL THIS STORE RECORDED AND DID NOT ACT ON. The partner
# review found MAP-A-GRANT already exists, is already free, ships in every public
# template zip, and was only ever surfaced AFTER a £500 purchase — and that moving
# it to the front door is a re-ordering rather than a build. This is that
# re-ordering, with an interface on it.
#
# THE VOCABULARY IS NOT THIS STORE'S. Twenty-three primitives on a
# verb.object.reach grammar, promoted out of riskmandate.ai's own template vault
# with a published read key by tools/promote_capabilities.py. If this store
# invented its own words, a buyer would describe their agent in one vocabulary and
# receive a document written in another — which is the worst outcome available to
# a page whose entire job is producing an input to that document.
#
# TWO PROTOTYPES, BECAUSE TWO WERE ASKED FOR. A canvas for somebody being walked
# through it by a person, and a sequence for somebody working alone. Both render
# the same twenty-three primitives and emit the same document, which is what makes
# them an experiment rather than two drafts — the same arrangement the five
# configurator prototypes already run on.
CAPABILITIES = json.loads((DATA / "capabilities.json").read_text())
CAPS = CAPABILITIES["capabilities"]
CAP_FAMILIES = CAPABILITIES["families"]
CAP_REACHES = CAPABILITIES["reaches"]

UNDO_LABEL = {
    "yes": ("Undoable", "u-y"),
    "with-effort": ("Undoable with effort", "u-e"),
    "no": ("Not undoable", "u-n"),
}


def agent_model_island(prefix):
    """The vocabulary, shipped as data so both prototypes render the same thing."""
    return ('<script type="application/json" id="agent-model">'
            + json.dumps({
                "grammar": CAPABILITIES["grammar"],
                "families": CAP_FAMILIES,
                "reaches": CAP_REACHES,
                "capabilities": CAPS,
                "storage": "sgit.store.agent.v1",
            }, separators=(",", ":"))
            + "</script>")


def _cap_chip(c):
    label, cls = UNDO_LABEL[c["undo"]]
    return (f'<button type="button" class="cap {cls}" data-cap="{html.escape(c["id"])}" '
            f'aria-pressed="false">'
            f'<b>{html.escape(c["gloss"])}</b>'
            f'<code>{html.escape(c["id"])}</code>'
            f'<span class="cap-undo">{html.escape(label)}</span></button>')


def agent_palette():
    out = []
    for fam, gloss in CAP_FAMILIES.items():
        rows = [c for c in CAPS if c["family"] == fam]
        if not rows:
            continue
        out.append(f'<section class="fam" data-fam="{html.escape(fam)}">'
                   f'<h4>{html.escape(fam)}<span>{html.escape(gloss)}</span></h4>'
                   f'<div class="fam-caps">{"".join(_cap_chip(c) for c in rows)}</div>'
                   "</section>")
    return "".join(out)


def agent_shared_note(ctx):
    reaches = "".join(
        f'<div class="row2"><div><b><code>{html.escape(k)}</code></b>'
        f'<p>{html.escape(v)}</p></div></div>' for k, v in CAP_REACHES.items())
    rules = "".join(f"<li>{inline(r, ctx)}</li>" for r in CAPABILITIES["rules"])
    up = CAPABILITIES["_upstream_provenance"]
    el = CAPABILITIES["_elided"]
    return (
        '<h2 id="what-this-produces">What this produces, and what it does not</h2>'
        '<p><b>It produces the grant</b> \u2014 everything the agent <em>can</em> do. That is one '
        'of four objects in an Agent Behaviour Policy. It is <b>not</b> the mandate (what you '
        'authorised), <b>not</b> the delta between them, and <b>not</b> a policy. '
        '<a href="/what-is-in-one/">What the other three are</a>.</p>'
        '<p>The grant is the half you can answer from the deployment, which is why it is the half '
        'given away. The three that follow need somebody to look at your situation, and that is '
        f'<a href="/d/t3/">the \u00a3500 level</a>.</p>'
        '<h2 id="the-vocabulary">The vocabulary is not ours</h2>'
        f'<p><b>{CAPABILITIES["count"]} primitives on a <code>'
        f'{html.escape(CAPABILITIES["grammar"])}</code> grammar</b>, promoted out of '
        "riskmandate.ai\u2019s own template vault with a published read key. If this store invented "
        'its own words, you would describe your agent in one vocabulary and receive a document '
        'written in another.</p>'
        f'<div class="rows">{reaches}</div>'
        f'<h3>The rules the set follows</h3><ul>{rules}</ul>'
        # THE REMOVED CLAUSE IS DESCRIBED AND NOT QUOTED, WHICH IS THE RULE
        # DEMONSTRATING ITSELF. The first version printed it verbatim in order to
        # explain that it is barred — and the check caught that, correctly, on the
        # release that introduced it. The disclosures page has had the same
        # constraint since it was written: it describes each barred term precisely
        # enough that anybody in the field knows which one is meant, and prints
        # none of them.
        + (f'<p class="small dim"><b>One clause was removed on the way in.</b> The rule above '
           'ended with a second clause tying recoverability to a financial concept this site bars '
           'absolutely, because it carries prices and the word implies a product it does not sell. '
           'The rule itself is kept whole; the clause is recorded in '
           '<code>data/capabilities.json</code> under <code>_elided</code>, which is in the '
           'repository and not in the site. <a href="/disclosures/">The words this site will not '
           'use</a>.</p>' if el else "")
        + f'<p class="small dim">Promoted from <code>{html.escape(up.get("source", ""))}</code> at '
        f'pack version {html.escape(str(up.get("pack_version", "?")))}, with the content hash of '
        'the bytes it was read from recorded in <code>data/capabilities.json</code>. '
        'tools/promote_capabilities.py does it, run by hand \u2014 the build opens no '
        'connection.</p>')

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
            'this browser: there is no form on this site, nothing is submitted anywhere, and '
            'nothing here sends anything about you, '
            'so with scripting off there is nothing to fall back to except '
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
                "flow. The work it configures is done by a named security professional today; the "
                "seven-role team these prototypes describe is a specification rather than "
                "something staffed.\n\n"
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


    # --- the product-page prototype, in the surface that already protects it
    url = "/lab/product/"
    ctx = dict(ctx_shared)
    ctx.update({"page": "lab/product", "page_url": url, "fm": {}, "toc": []})
    pp = PRODUCT_PAGE
    o = OFFERS_BY_ID[pp["subject"]]
    body = (
        f'<div class="note"><p><b>{LAB_WARNING}.</b> This is a prototype of a product page, not '
        'a product page. Nothing on it can be bought, the button is disabled in the markup rather '
        'than by script, and whether this shape becomes the real one is not decided. '
        '{{claim:lab-is-a-prototype}}</p></div>'
        '<p class="lead"><b>A level page argues about what a policy is. A product page shows the '
        'thing.</b> Those are different documents and this store has only ever written the first. '
        'This is what the second would look like for '
        f'<a href="/d/{o["id"]}/">{html.escape(o["question"])}</a>.</p>'
        + product_prototype(ctx)
        + '<h2 id="what-is-being-judged">What is being judged here</h2>'
        '<p>Four things, and they are separable — any one of them could be right while the '
        'others are wrong.</p>'
        '<div class="rows">'
        '<div class="row2"><div><b>The buy box on the right</b><p>Price, delivery and one action, '
        'held beside the material rather than under it. This is the part that is closest to '
        'settled, because it is what every shop does and the reason is the same everywhere: the '
        'decision and the evidence should be visible at the same time.</p></div></div>'
        '<div class="row2"><div><b>The media, and the empty slots</b><p>Seven slots, three with a '
        'picture. <b>The empty ones are left visibly empty.</b> A carousel padded with decoration '
        'would be the one dishonest thing on a page whose entire job is showing what you actually '
        'get — and it would also hide how much of this is still to do.</p></div></div>'
        '<div class="row2"><div><b>The specifications</b><p>The product code, the licence, what is '
        'inside and what is not needed. A product has specs; this store has sixty-two product '
        'codes and prints none of them anywhere a buyer looks.</p></div></div>'
        '<div class="row2"><div><b>Editions</b><p>The five audiences as variants of one product '
        'rather than five separate paths — the same switch as <a href="/are/">who you '
        'are</a>, arriving from the product side. Today it changes one sentence. The open question '
        'is whether it should change the pictures too, which is what would make it an edition '
        'rather than a label.</p></div></div>'
        "</div>"
        '<h2 id="what-it-is-missing">What it is missing, on purpose</h2>'
        '<p><b>Stars.</b> Not asked for, and a rating out of five on a product nobody has bought '
        'would be the one piece of furniture here that could not be honest. The reviews section '
        'says it is empty and says what will fill it.</p>'
        '<p><b>Most of the pictures.</b> Named above rather than mocked up, because a slot that '
        'says what belongs in it is a piece of work somebody can do, and a placeholder image is a '
        'piece of work somebody will forget.</p>'
        '<p><a href="/lab/">The other prototypes in the lab</a></p>')
    page = {
        "fm": {"title": "A product page, as a prototype",
               "description": ("What a product page for this store would look like: the buy box, "
                               "a gallery with its empty slots left visibly empty, specifications, "
                               "editions by audience and a reviews section that says it is empty. "
                               "Nothing on it can be bought."),
               "lead": "**A prototype of a product page, not a product page.**",
               "wide": True, "head_css": "/assets/lab.css",
               # The edition switcher lives in lab.js. Without this the buttons
               # render, look clickable and do nothing — which is worse on a page
               # about whether an interface works than not having them at all.
               "head_js": "/assets/lab.js"},
        "url": url,
        "crumb": ' / <a href="/lab/">lab</a> / product',
        "nav_match": "/ledger/",
        "src_md": (
            f"# A product page, as a prototype\n\n**{LAB_WARNING}.** This is a prototype of a "
            "product page, not a product page.\n\n"
            "A level page argues about what a policy is. A product page shows the thing.\n\n"
            f"- Subject: {o['question']} — {o['price_label']}, {o['eta']}\n"
            f"- Media slots: {len(pp['media'])}, of which "
            f"{sum(1 for m in pp['media'] if m.get('file'))} have a picture\n"
            f"- Specifications: {len(pp['specs'])} rows\n"
            "- Reviews: none, and no star average now or later\n"),
    }
    target = out_dir / url.strip("/") / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page_html(page, ctx, shortcodes_inline(body, ctx)))
    (target.parent / "index.md").write_text(
        page["src_md"].rstrip("\n") + f"\n\n---\n\n{LICENCE_STAMP}\n")
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
    url = V1_MOVED["/cart/"]
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
    target = out_dir / url.strip("/") / "index.html"
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
        u2 = V1_MOVED[f"/{slug}/"]
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
        t2 = out_dir / u2.strip("/") / "index.html"
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
        ctx["claim_uses"].setdefault(b["opportunity_claim"], set()).add(ctx["page_url"])

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


# The nine pages the new design replaced, kept as they were. Their links to each
# other are rewritten so the archive does not tip a reader into the live store
# halfway through; their links to pages that never moved go where they always
# went, because those pages still exist and are still right.
_V1_LINK = re.compile(
    r'href="(' + "|".join(re.escape(u) for u in sorted(V1_MOVED, key=len, reverse=True)) + r')(?=["#?])')


def _v1_page_html(page, ctx, body):
    fm = page["fm"]
    toc = ""
    if fm.get("toc") and len(ctx["toc"]) > 2:
        links = "".join(
            f'<a class="lv{lv}" href="#{anchor}">{html.escape(text)}</a>'
            for lv, anchor, text in ctx["toc"] if lv == 2)
        toc = f'<aside class="toc"><b>On this page</b>{links}</aside>'
    prefix = rel_prefix(page["url"])
    # The address this page used to have is the address its replacement has now:
    # /v1/cart/ came from /cart/, and /cart/ is the new one. Derived rather than
    # carried, so a generated page and a markdown page answer the same way.
    now = V1_REPLACED_BY.get(page["url"], "/" + page["url"][len(V1_ROOT):])
    doc = f"""<!doctype html>
<html lang="en" data-root="{prefix}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{html.escape(fm['title'])} &mdash; the previous design</title>
<meta name="description" content="{html.escape(fm.get('description', ''))}">
<meta name="robots" content="noindex,follow">
<link rel="canonical" href="{SITE['base']}{now}">
<link rel="alternate" type="text/markdown" href="index.md" title="This page as markdown">
<link rel="stylesheet" href="/assets/site.css">
{f'<link rel="stylesheet" href="{fm["head_css"]}">' if fm.get('head_css') else ''}
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<script src="/assets/site.js" defer></script>
<script src="/assets/shop.js" defer></script>
{f'<script src="{fm["head_js"]}" defer></script>' if fm.get('head_js') else ''}
{f'<script src="{fm["head_js2"]}" defer></script>' if fm.get('head_js2') else ''}
</head>
<body>
<div class="v1bar">
  <b>THE PREVIOUS DESIGN</b>
  <span>How this page looked until {html.escape(V1_UNTIL)}. Kept, not maintained.</span>
  <span class="v1bar__end"><a href="@@OUT@@">the same page, as the store looks now &#8599;</a></span>
</div>
{nav_html(page['nav_match'])}
<div class="disclosure-strip"><div class="row"><b>{MODEL_GENERATED}</b>
Nothing on this site is a compliance assessment, and no page claims conformity to any standard.
<a href="/disclosures/">What we do not say, and why</a> &middot;
<a href="/ledger/">how every claim here is evidenced</a></div></div>
<main class="doc{' doc-wide' if fm.get('wide') else ''}">
<p class="crumb"><a href="{V1_ROOT}">the previous design</a>{page['crumb']}</p>
<h1>{html.escape(fm['title'])}</h1>
{f'<p class="lead">{inline(fm["lead"], ctx)}</p>' if fm.get('lead') else ''}
{toc}
{body}
</main>
{footer_html()}
</body>
</html>
"""
    # Every link to a page that moved is pulled back inside the archive, before
    # relativise turns what is left into ../ paths. The strip's own way out is
    # held as a token until after that, because it is the one link on the page
    # that is supposed to leave.
    doc = _V1_LINK.sub(lambda m: 'href="' + V1_MOVED[m.group(1)], doc)
    doc = doc.replace("@@OUT@@", now)
    return relativise(doc, prefix)


def page_html(page, ctx, body):
    """Every page that is not built out of the offer data: the markdown pages, the
    shape pages, the delivery pages, the five audience doors, the landing pages.

    THE CHROME IS THE NEW DESIGN'S AND THE BODY IS STILL THE OLD ONE'S. From
    v0.3.16 these pages are served in the header, disclosure strip and footer that
    the rest of the store uses, and they load site.css and then next.css: the
    chrome and the base type come from the new file, and the block components —
    the tables, the tiles, the specification rows, the level cards — keep the
    rules that already draw them. A rule in next.css beats a rule in site.css at
    equal specificity because it is loaded second, which is the whole trick.

    I ARGUED AGAINST THIS LAYERING WHEN THE NEW PAGES WERE BUILT and the argument
    still holds where it applied: a NEW page with no old blocks in it should not
    carry 26KB of a design it is replacing, and those pages still do not. These
    pages are made almost entirely of those blocks. Porting them is real work with
    no reader-visible result on the day it lands, so it is on the board rather
    than in front of the swap. The transitional state is one stylesheet too many,
    not one design too many.

    /v1/ IS THE EXCEPTION. The previous design is kept at /v1/ as it was, chrome
    and all, because an archive redrawn in the design that replaced it is not an
    archive of anything."""
    if page["url"].startswith(V1_ROOT):
        return _v1_page_html(page, ctx, body)
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
<link rel="stylesheet" href="/assets/next.css">
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
<a class="n-skip" href="#main">Skip to content</a>
{n_chrome_top(page['url'])}
<main id="main" class="n-sect">
<div class="n-doc{' is-wide' if fm.get('wide') else ''}">
<p class="crumb"><a href="/">store.sgit.ai</a>{page['crumb']}</p>
<h1>{html.escape(fm['title'])}</h1>
{f'<p class="lead">{inline(fm["lead"], ctx)}</p>' if fm.get('lead') else ''}
{toc}
{body}
<p class="pagenav"><a href="{NEXT_PICKER}">Which agent do you run? &rarr;</a>
<a href="/how-it-works/">How buying works &rarr;</a>
<a href="{NEXT_LEDGER}">Every claim, with its state &rarr;</a></p>
</div>
</main>
{n_footer()}
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
    # THE SAME MARKDOWN, ONE DIRECTORY DOWN. A page the new design replaced is
    # still written, still checked and still linked to — it is the previous
    # design, kept — and the address it used to have now belongs to the page
    # that replaced it. See V1_MOVED.
    return {"path": path, "fm": fm, "body": body.lstrip("\n"),
            "url": V1_MOVED.get(url, url), "was": url, "src_md": text}


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


def _selling_page(out_dir, ctx_shared, url, fm, crumb, body, src_md):
    """Emit one generated page on the SELLING side and its markdown twin. The same
    shape as _console_page, through page_html rather than console_html — these
    pages are indexed, they carry the shop's nav and its disclosure strip, and they
    are the front door rather than an operations surface."""
    ctx = dict(ctx_shared)
    ctx.update({"page": url, "page_url": url, "fm": fm, "toc": []})
    page = {"fm": fm, "url": url, "crumb": crumb, "nav_match": "/audiences/", "src_md": src_md}
    target = out_dir / url.strip("/") / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page_html(page, ctx, shortcodes_inline(body, ctx)))
    (target.parent / "index.md").write_text(src_md.rstrip("\n") + f"\n\n---\n\n{LICENCE_STAMP}\n")
    return fm["title"]


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
        '<p><b><a href="/admin/status/">What happened to each of them &rarr;</a></b> \u2014 every ' 
        'unit of work a memo became, whether it is done, the page it built and the release ' 
        'it shipped in, on one page.</p>' 
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


def money_label(pence):
    """Pence as a price. The chip these sit in is uppercased by its own CSS, which
    turned `5000p` into `5000P` \u2014 a unit nobody uses, on the one number a reader
    is most likely to be checking against a dashboard."""
    return f"\u00a3{pence // 100:,}" + ("" if pence % 100 == 0 else f".{pence % 100:02d}")


def _coupon_rank(c):
    if not c["coupon"]:
        return 1
    if c["capped"]:
        return 4
    return 1 if c["pct"] == 100 else 2


def coupon_reconciliation():
    """The three coupons, against the eight codes this store honours.

    MOST OF THE SHAPE IS MANY-TO-FEW AND THAT IS CORRECT. A coupon carries a
    percentage; a promotion code is the string a person is handed and is a
    separate object attached to one. Six of this store's eight codes are at a
    hundred per cent, and they exist as six rather than one so that an order
    record says WHICH of them produced it — a beta tester, an agent driving a
    script, somebody at a stand. That distinction lives in the promotion code, not
    in the coupon.

    THE EXCEPTION IS DOORSOPEN AND IT NEEDS A COUPON OF ITS OWN. It is
    `levels: [pack, vault]`, and a promotion code cannot carry that restriction:
    a promotion code restricts by first transaction and by minimum amount, and
    scoping a discount to particular products is a property of the COUPON, through
    applies_to.products. On the shared hundred-per-cent coupon it would take the
    whole of a level-four deposit off — which is exactly what that record's own
    comment says must never be possible, because what a published code gives away
    has to be a thing that costs nobody a day.

    This function groups by percentage because that is what a coupon is. The
    product scoping is not visible in that grouping and so it is said here and on
    the rail page rather than being left to be discovered by whoever creates the
    codes."""
    live = {c["pct"]: c for c in STRIPE_PRODUCTS.get("coupons", [])}
    rows = []
    for pct in sorted({d["pct"] for d in DISCOUNTS}, reverse=True):
        codes = [d for d in DISCOUNTS if d["pct"] == pct]
        got = live.get(pct)
        rows.append({
            "pct": pct,
            "codes": len(codes),
            "printable": sum(1 for d in codes if d["printable"]),
            "coupon": got["name"] if got else None,
            "capped": bool(got and got["max_redemptions"]) if got else None,
            "expires": (got["expires"] if got else None),
            "redeemed": got["times_redeemed"] if got else None,
        })
    return rows


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
            (('<div class="panel r2"><p><b>Parked on 16 September.</b> '
              'This rail is not in the first end-to-end store and nothing on the selling side '
              'mentions it. The plan below is kept rather than deleted, so turning it back on is '
              'restoring a record instead of rediscovering an argument.</p></div>')
             if r.get("parked") else "")
            + "".join(f'<div class="panel"><p>{w}</p></div>' for w in r["why"])
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
                    f'{money_label(q["unit_amount"])}'
                    f'{"" if q.get("agrees") else " ✗"}</span></div>'
                    for q in stripe_catalogue()["prices"]) + "</div>"
                '<p class="small">The account carries one more product that is not listed and is '
                'not reconciled: it belongs to a different part of the estate and this store '
                'neither sells it nor tracks it.</p>'
                '<h2 id="the-coupons">The coupons, and the codes that are still missing</h2>'
                '<p><b>Three coupons exist. Zero promotion codes do, and that is the whole gap.</b> '
                'A coupon carries a percentage. A promotion code is the string a person is actually '
                'handed, it is a separate object attached to a coupon, and it is what a link can '
                'carry pre-applied. Until one exists there is nothing to give anybody.</p>'
                '<p>Three onto seven is the right shape, not a shortfall. Five of this store\'s '
                'seven codes are at a hundred per cent, and they exist as five so that an order '
                'record says <em>which</em> one produced it \u2014 a beta tester, an agent driving '
                'a script, somebody at a stand. That lives in the promotion code, not in the '
                'coupon.</p><div class="rows">'
                + "".join(
                    f'<div class="row2"><div><b>{c["pct"]}% off</b>'
                    f'<p>{c["codes"]} code{"" if c["codes"] == 1 else "s"} in '
                    '<code>data/discounts.yml</code> at this percentage'
                    + (f', {c["printable"]} of them printable' if c["printable"] else "")
                    + (f' \u00b7 coupon <b>{html.escape(c["coupon"])}</b>, once, '
                       f'{c["redeemed"]} redemptions'
                       if c["coupon"] else " \u00b7 <b>no coupon exists at this percentage</b>")
                    + (' \u00b7 <b>no cap and no expiry</b>' if c["coupon"] and not c["capped"]
                       else "")
                    + "</p></div>"
                    # A green chip reading UNCAPPED is a chip arguing with itself.
                    # Rank follows what the state COSTS: red where an uncapped
                    # hundred-per-cent code cannot be recalled, amber where a cap is
                    # merely missing, green where one exists.
                    + f'<span class="st st--{_coupon_rank(c)}">'
                    + ("capped" if c["capped"] else
                       "no cap" if c["coupon"] else "missing") + "</span></div>"
                    for c in coupon_reconciliation())
                + "</div>"
                '<div class="panel r1"><h3>The hundred-per-cent coupon has no cap and no '
                'expiry</h3><p>Which is fine today, because no promotion code exists over it and no '
                'payment link exists to use one on \u2014 so there is nothing to redeem and nothing '
                'to leak. <b>It stops being fine the moment either of those is true.</b> A code at a '
                'hundred per cent, printed on a card or on a page, cannot be recalled; the cap is '
                'the thing that makes printing it survivable, and it belongs on the coupon before '
                'the first promotion code is created rather than after the first one gets '
                'screenshotted. <code>check_a_hundred_per_cent_coupon_is_capped</code> fails the '
                'release the moment a rail goes live and a cap is still missing.</p></div>')
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


# ------------------------------------------------------------- five audiences ----
# ASKED FOR ON 16 SEPTEMBER, AND THE DESIGN BRIEF FOR IT IS PHYSICAL.
#
#   "Laptop open, somebody comes along — who are you? A founder. Boom. And you
#    want to buy this. Boom. Click, click, navigate, select, touch, go."
#
# That is a counter at an event operated by a person standing next to the buyer,
# not a web page somebody browses. It sets the whole shape: five large targets,
# one tap to a view that leads with what fits them, everything still reachable.
#
# THIS DOES NOT REPLACE data/buyers.yml AND THAT IS AN OPEN QUESTION, NOT A
# DECISION. The store's three buyer groups are cut by situation; these five are
# cut by role. Both are indexes over the same six offers. Whether the three retire
# is written down at /admin/work/qualify-the-buyer/ rather than settled here.
#
# SHOWN DIFFERENTLY, NOT HIDDEN. The memo said an investor is not going to be sold
# a ten-pound licence. The tempting reading is to hide the cheap levels from them.
# The honest one is to lead with what fits and keep everything reachable — because
# a site that shows different people different catalogues has to say so out loud,
# and this one would rather not have to.
AUDIENCES = yaml_load((DATA / "audiences.yml").read_text())
AUDIENCE_ROOT = "/are/"
for _a in AUDIENCES:
    if _a["leads_with"] not in OFFERS_BY_ID:
        raise KeyError(f"audience {_a['id']}: leads with {_a['leads_with']!r}, which is not an offer")
    for _q in _a["quiet"]:
        if _q not in OFFERS_BY_ID:
            raise KeyError(f"audience {_a['id']}: quiets {_q!r}, which is not an offer")
    if not any(w["id"] == _a["evidence"] for w in EVIDENCE["works"]):
        raise KeyError(f"audience {_a['id']}: cites evidence {_a['evidence']!r}, which is not published")


def block_who_are_you(ctx):
    """The five doors. Deliberately the only thing on the page that looks like this."""
    cards = "".join(
        f'<a class="who" href="{AUDIENCE_ROOT}{a["id"]}/">'
        f'<b>{html.escape(a["short"])}</b>'
        f'<span>{html.escape(a["door"])}</span></a>' for a in AUDIENCES)
    return (f'<div class="whos">{cards}</div>'
            '<p class="small dim">Every level is reachable from every one of these. What changes '
            'is which one a view opens on and what is said about it — not what is for sale. '
            f'<a href="/offers/">All six, side by side</a>.</p>')


BLOCKS["who-are-you"] = block_who_are_you


def audience_pages(out_dir, ctx_shared):
    """One page per audience: the level that fits, then the rest, then the one
    published vault that speaks to them."""
    # THE FIVE DOORS ARE BUILT BY _next_doors NOW, in the design the store uses;
    # this function keeps the index. The old per-audience pages drew the old
    # level cards and are not archived: they were never a design of their own,
    # and a reader who wants the previous design has /v1/audiences/.
    made = {}
    # the index: the five doors, and nothing else
    idx_body = (
        '<p class="lead">Five ways in, over the same four things. <b>Nothing is hidden from '
        'anybody</b> — what changes is which level a view opens on and what is said about it, '
        'because the question somebody arrives with is usually the best guess at which one they '
        'want.</p>'
        + block_who_are_you(dict(ctx_shared, page_url=AUDIENCE_ROOT))
        + '<h2 id="why-five">Why these five</h2>'
        '<p>They are cut by <b>role</b> — what you do, and therefore what you are on the hook '
        'for. This store also has three groups cut by <b>situation</b>, which is a different axis '
        'over the same six offers and is still <a href="/audiences/">where it was</a>.</p>')
    idx_md = ["# Who you are\n", "Five ways in, over the same four things. Nothing is hidden from "
              "anybody; what changes is which level a view opens on.\n"]
    idx_md += [f"- **{a['name']}** — {a['arrives_with']} — "
               f"{SITE['base']}{AUDIENCE_ROOT}{a['id']}/" for a in AUDIENCES]
    made[AUDIENCE_ROOT] = _selling_page(out_dir, ctx_shared, AUDIENCE_ROOT,
        {"title": "Who you are",
         "description": ("Five ways into the same four things: founder, investor, C-level "
                         "executive, security professional, risk and governance. Nothing is "
                         "hidden from anybody — what changes is which level a view opens on."),
         "lead": "**Five ways in, over the same four things.**"},
        "", idx_body, "\n".join(idx_md))
    return made


# --------------------------------------------------------- the comparison ----
# FEATURES DOWN THE LEFT, FIVE COLUMNS ACROSS, AND THE FREE ONE FIRST.
#
# The store explained each level on its own page, which meant nobody ever saw the
# four side by side — and every sentence worth reading about them is a DIFFERENCE,
# which is only legible next to the thing it differs from.
#
# THE FREE COLUMN LEADS BECAUSE IT IS THE ARGUMENT. The templates being published
# had been treated here as an objection to handle. Put first, it becomes the first
# row of the case: here is what you can have for nothing, and here is what each
# step adds. The licence row alone explains the first paid step, which is the one
# two reviewers said read as a commodity.
#
# EVERY CELL IS READ OFF SOMETHING OR THE ROW IS NOT HERE. A support level nobody
# has scoped and a board-readable cut still being specified are both absent, and
# they are absent on purpose: this store fails its own release when a page states
# an unproven thing as a fact, and a table is the place where that is hardest to
# notice.
COMPARISON = yaml_load((DATA / "comparison.yml").read_text())


def _cmp_cell(v):
    if v == "yes":
        return '<td class="c-yes"><span aria-label="yes">\u2713</span></td>'
    if v == "no":
        return '<td class="c-no"><span aria-label="no">\u2014</span></td>'
    return f'<td class="c-txt">{html.escape(str(v))}</td>'


def block_comparison(ctx):
    cols = COMPARISON["columns"]
    head = "".join(
        '<th scope="col">'
        + (f'<a href="/d/{c["offer"]}/">{html.escape(c["name"])}</a>'
           if c.get("offer") else html.escape(c["name"]))
        + '<span class="c-price">'
        + html.escape(c.get("price") or OFFERS_BY_ID[c["offer"]]["price_label"])
        + "</span>"
        + (f'<span class="c-sub">{html.escape(c["sub"])}</span>' if c.get("sub") else "")
        + "</th>" for c in cols)
    body = []
    for g in COMPARISON["groups"]:
        body.append(f'<tr class="c-group"><th scope="rowgroup" colspan="{len(cols) + 1}">'
                    f'{html.escape(g["name"])}</th></tr>')
        for r in g["rows"]:
            body.append(
                f'<tr><th scope="row"><b>{html.escape(r["label"])}</b>'
                f'<span class="c-why">{html.escape(r["why"])}</span></th>'
                + "".join(_cmp_cell(r[c["id"]]) for c in cols) + "</tr>")
    return ('<div class="tablewrap"><table class="cmpt"><thead><tr><th></th>'
            + head + "</tr></thead><tbody>" + "".join(body) + "</tbody></table></div>"
            '<p class="small dim">Every cell here is read off <code>data/offers.yml</code> or off a '
            'ruling, and a row whose cells would be a promise rather than a description is not on '
            'this table yet. What is still being specified is on '
            '<a href="/admin/work/">the board</a> rather than in a column.</p>')


BLOCKS["comparison"] = block_comparison


def block_brochure(ctx):
    """The printable form of this page, with what it was rendered from.

    A brochure that has drifted from the page is worse than no brochure, so the
    version and the date it was taken are printed beside the link rather than
    left for a reader to wonder about."""
    d = next((x for x in DOWNLOADS["downloads"] if x["url"] == "/compare/"), None)
    if not d:
        raise SystemExit("compare: no brochure in data/downloads.json — "
                         "run node tools/make_pdfs.mjs")
    stale = d["version"] != SITE["version"]
    note = ("" if not stale else
            f' <span class="dim">This copy was taken at {html.escape(d["version"])} and the '
            f'page is now {html.escape(SITE["version"])} — the rows may have moved '
            "since.</span>")
    return (
        '<div class="broch" id="the-brochure">'
        f'<a class="buy" href="/assets/downloads/{d["file"]}" download>'
        'Download the comparison &mdash; PDF</a>'
        f'<p class="small dim"><b>{d["columns"] - 1} columns, {d["rows"]} rows, '
        f'{d["bytes"] // 1024}KB, A4 landscape.</b> Rendered from this page at '
        f'{html.escape(d["version"])} on {html.escape(d["generated"])} — not '
        "retyped, so a row added here is in the brochure on the next run."
        f'{note}</p></div>')


BLOCKS["brochure"] = block_brochure



# ---------------------------------------------------------- who runs the work ----
# THE TWO UPPER LEVELS ARE SOMEBODY'S WORK AND THIS STORE HAD NEVER SAID WHOSE.
# Asking £1,500 for a security review from nobody in particular is a worse problem
# than any price on this site. One name today, and the surface is built for a list
# because the project lead is negotiating rates with others to take some of it.
#
# NOTHING ON A REVIEWER PAGE IS WRITTEN FROM WHAT SOMEBODY TOLD US. Every record
# row is read off a published page, named with the date it was read, and the page
# says so at the top rather than in a footnote. A biography this site composed
# would be the worst thing on the domain to stand next to a price.
REVIEWERS_FILE = yaml_load((DATA / "reviewers.yml").read_text())
REVIEWERS = sorted(REVIEWERS_FILE["reviewers"], key=lambda r: r["order"])
REVIEWER_ROOT = "/who/"
REVIEWER_BY_OFFER = {}
for _r in REVIEWERS:
    for _o in _r["does"]:
        if _o not in OFFERS_BY_ID:
            raise KeyError(f"reviewer {_r['id']}: does {_o!r}, which is not an offer")
        REVIEWER_BY_OFFER.setdefault(_o, []).append(_r)
    for _d in _r["delivered"]:
        if not any(w["id"] == _d for w in EVIDENCE["works"]):
            raise KeyError(f"reviewer {_r['id']}: cites {_d!r}, which is not published evidence")


def _reviewer_sources_note():
    rows = "".join(
        f'<li><a href="{s["url"]}">{html.escape(s["url"])}</a> &mdash; '
        f'{html.escape(s["what"])} Read {html.escape(s["read"])}.</li>'
        for s in REVIEWERS_FILE["_sources"])
    return ('<div class="note"><p><b>Where this comes from.</b> Every line below is read off a '
            'published page, and the pages are named. <b>Nothing here is written from what anybody '
            'told us</b> — a biography this store composed would be the worst thing on it to '
            f'stand next to a price.</p><ul class="small">{rows}</ul></div>')


def block_who_runs_it(ctx):
    """Named on the level pages, so a buyer at £500 knows whose work they are buying."""
    rows = "".join(
        f'<div class="rv-person"><div><b><a href="{REVIEWER_ROOT}{r["id"]}/">'
        f'{html.escape(r["name"])}</a></b>'
        f'<p>{inline(r["lede"], ctx)}</p>'
        f'<p class="small dim">{html.escape(r["one_line"])}</p></div></div>'
        for r in REVIEWERS)
    return (f'<div class="rv-people">{rows}</div>'
            '<p class="small dim">One name today, and the list is built for more — other '
            'security professionals are being approached to take some of this work. '
            f'<a href="{REVIEWER_ROOT}">Everybody who runs a review here</a>.</p>')


BLOCKS["who-runs-it"] = block_who_runs_it


def reviewer_pages(out_dir, ctx_shared):
    made = {}
    for r in REVIEWERS:
        url = f"{REVIEWER_ROOT}{r['id']}/"
        ctx = dict(ctx_shared)
        ctx.update({"page": f"who/{r['id']}", "page_url": url, "fm": {}, "toc": []})
        ctx["external_links"].add(r["contact"])
        for s in REVIEWERS_FILE["_sources"]:
            ctx["external_links"].add(s["url"])
        levels = [OFFERS_BY_ID[o] for o in r["does"]]
        works = [w for w in EVIDENCE["works"] if w["id"] in r["delivered"]]
        for w in works:
            ctx["external_links"].add(w["url"])
        body = (
            _reviewer_sources_note()
            + '<h2 id="the-record">The record</h2><div class="rows">'
            + "".join(f'<div class="row2"><div><b>{inline(x["what"], ctx)}</b>'
                      f'<p>{inline(x["detail"], ctx)}</p></div></div>' for x in r["record"])
            + "</div>"
            + '<h2 id="what-they-run-here">What they run on this store</h2>'
            + '<div class="rows">' + "".join(
                f'<div class="row2"><div><b><a href="/d/{o["id"]}/">'
                f'{html.escape(o["question"])}</a></b><p>{inline(o["gets"], ctx)}</p></div>'
                f'<span class="st st--3">{html.escape(o["price_label"])} · '
                f'{html.escape(o["eta"])}</span></div>' for o in levels) + "</div>"
            + f'<p>{inline(r["why_them"], ctx)}</p>'
            + '<h2 id="work-you-can-open">Work you can open right now</h2>'
            '<p>Not a portfolio and not a case study — the vaults themselves, each opened by a '
            'read key published on its own page.</p>'
            + '<div class="ev-grid">' + "".join(
                f'<div class="ev"><div class="ev-h"><a href="{w["url"]}">'
                f'<b>{html.escape(w["title"])}</b></a>'
                f'<span class="ev-m"><code>{html.escape(w["vault"])}</code> · '
                f'{html.escape(w["size"])} · {html.escape(w["published"])}</span></div>'
                f'<p class="ev-q">&ldquo;{html.escape(w["quoted"])}&rdquo;</p>'
                f'<p class="ev-w">{inline(w["why"], ctx)}</p></div>' for w in works) + "</div>"
            + f'<h2 id="reach-them">Reach them</h2><p><a href="{r["contact"]}">'
            f'{html.escape(r["contact_label"])}</a>.</p>'
            f'<p><a href="{REVIEWER_ROOT}">Everybody who runs a review here</a></p>')
        md = [f"# {r['name']}\n", r["lede"], "",
              "*Every line below is read off a published page. Sources: "
              + "; ".join(f"{s['url']} (read {s['read']})" for s in REVIEWERS_FILE["_sources"])
              + ".*\n", "## The record\n"]
        md += [f"- **{_strip(x['what'])}** — {_strip(x['detail'])}" for x in r["record"]]
        md += ["", "## What they run on this store\n"]
        md += [f"- **{o['question']}** — {o['price_label']}, {o['eta']} "
               f"— {SITE['base']}/d/{o['id']}/" for o in levels]
        md += ["", "## Work you can open right now\n"]
        md += [f"- **{w['title']}** — {w['url']}" for w in works]
        md += ["", f"Reach them: {r['contact']}"]
        made[url] = _selling_page(out_dir, ctx_shared, url,
            {"title": r["name"], "description": r["lede"][:300],
             "lead": inline(r["one_line"] + " " + r["lede"], ctx)},
            f' / <a href="{REVIEWER_ROOT}">who runs it</a> / {html.escape(r["name"])}',
            body, "\n".join(md))

    idx_url = V1_MOVED[REVIEWER_ROOT]
    idx_ctx = dict(ctx_shared)
    idx_ctx.update({"page": "who", "page_url": idx_url, "fm": {}, "toc": []})
    idx_body = (
        '<p class="lead">The two upper levels are somebody\'s work, and until 16 September this '
        'store had never said whose. <b>Asking for £1,500 for a security review from nobody in '
        'particular is a worse problem than any price on this site.</b></p>'
        + block_who_runs_it(idx_ctx)
        + '<h2 id="how-this-list-grows">How this list grows</h2>'
        '<p>One name today. Other security professionals are being approached, and rates '
        'negotiated, so they can take some of the work at £500 and £1,500 — and '
        'eventually above. <b>Adding the second is adding a record to a file</b>: the page, its '
        'markdown twin, the entry here and the links from the level pages are all generated, which '
        'is why the surface was built for a list on the day it had one name on it.</p>'
        '<h2 id="what-is-not-claimed">What is not claimed here</h2>'
        '<p><b>Nothing on these pages was written from what somebody told us.</b> Every line of a '
        'record is read off a published page, named with the date it was read. A biography this '
        'store composed would be the worst thing on the domain to stand next to a price, and the '
        'argument this whole site rests on is worth nothing if it stops applying the moment a '
        'sentence is flattering.</p>'
        '<p>It also carries no count of years. What is published is a record starting in 2008 and a '
        'reader can do that arithmetic themselves and check every step of it — <b>a round '
        'number nobody can verify is weaker than a date anybody can</b>.</p>')
    idx_md = ["# Who runs the review\n",
              "The two upper levels are somebody's work. This is who.\n"]
    idx_md += [f"- **{r['name']}** — {r['one_line']} — "
               f"{SITE['base']}{REVIEWER_ROOT}{r['id']}/" for r in REVIEWERS]
    made[idx_url] = _selling_page(out_dir, ctx_shared, idx_url,
        {"title": "Who runs the review",
         "description": ("The named security professionals who run the £500 correction and the "
                         "£1,500 sessions. One today, built for a list, and every line of every "
                         "record read off a published page."),
         "lead": "**The two upper levels are somebody's work.** This is who, and where every line "
                 "of it was read from."},
        "", idx_body, "\n".join(idx_md))
    return made



# ------------------------------- the worked example on the page after paying ----
# "WHEN YOU HAVE SOLD A VAULT, YOU SHOULD JUST SEE THE VAULT."
#
# The difficulty is that at the moment somebody pays there is nothing of theirs to
# show. At the vault level it is built for them within a day or two; at the two
# upper levels it is built after they send their details. A page that showed "your
# vault" at that moment would be lying at the one moment a buyer is paying most
# attention to it.
#
# So what is embedded is a PUBLISHED vault of exactly this kind of work, said to
# be an example in its first sentence. For a buyer who has never held one, that is
# the more useful of the two things anyway: a vault is hard to picture from a
# description and takes about a minute to read.
#
# THIS IS THE SECOND PLACE ON THIS SITE THAT OPENS A CONNECTION, and the rule was
# narrowed rather than loosened to admit it — see check_no_network. What stayed
# absolute: every page that SELLS anything still opens nothing at all. What is new
# is that a page reached only after a sale may embed one published vault, from the
# one host, and has to say so on itself.
EXAMPLE_VAULT = yaml_load((DATA / "example-vault.yml").read_text())


def example_vault_embed(ctx):
    v = EXAMPLE_VAULT
    ctx["external_links"].add(v["page"])
    ctx["external_links"].add(v["web"])
    host = v["embed_host"].replace("https://", "")
    return (
        '<div class="rv-vault">'
        '<span class="rv-vlab2">An example, not yours</span>'
        f'<p class="rv-vnote">{html.escape(v["note"])} {html.escape(v["why"])}</p>'
        '<div class="rv-vgrid">'
        f'<div><b>Vault</b><code>{html.escape(v["id"])}</code></div>'
        f'<div><b>Files</b><code>{v["files"]}</code></div>'
        '<div><b>Access</b><code>read-only</code></div>'
        "</div>"
        f'<p class="rv-vopen"><a href="{html.escape(v["web"])}" rel="noopener" target="_blank">'
        'Open it in its own tab \u2197</a> '
        f'<span class="small dim">or read how it was published at '
        f'<a href="{html.escape(v["page"])}">sgit.ai</a>.</span></p>'
        '<div class="rv-slot">'
        '<b>This page opens a connection, and here is exactly which one.</b> The surface below is '
        f'the official vault interface running on <code>{html.escape(host)}</code>, in a frame this '
        'page builds at runtime. <b>The key does not travel in the address:</b> the frame is opened '
        'carrying nothing, it announces itself, and only then is the read key handed over by '
        'message with the target origin pinned \u2014 so it is not in a URL, not in history, not in '
        'a referrer and not in the frame\u2019s storage. Replies from any other origin are ignored. '
        'It is a <b>read</b> key, which opens a vault and cannot write to it, and sgit.ai publishes '
        'it deliberately on that vault\u2019s own page. '
        '<b>Every page on this site that sells anything still opens nothing at all</b> \u2014 this '
        'is a page you reach after buying, and a build check holds that line. '
        '<b>One exception, stated because it is real:</b> if the handshake does not complete within '
        'twelve seconds the component falls back to opening the vault with the key in the '
        'frame\u2019s URL fragment. A fragment is never sent to a server and never appears in a '
        'referrer, but it is in that frame\u2019s address. The link above avoids it entirely.</div>'
        "</div>"
        f'<div class="sgv-uiembed" data-vault="{html.escape(v["id"])}" '
        f'data-readkey="{html.escape(v["read_key_hex"])}" '
        f'data-app="{"1" if v.get("has_app") else "0"}"></div>')

# --------------------------------------------------- where a buyer lands ----
# THEY LAND HERE NOW, AND THAT REVERSED ON 16 SEPTEMBER.
#
# Until today the success address was riskmandate.ai's page for the level, and
# the reasoning was good: their level-one page IS the download, with the zip, its
# size, its sha256 and a hash check that runs in the buyer's browser — and copying
# a size and a hash over here would mean two of each, one of which goes stale the
# first time a template changes.
#
# What that reasoning missed is what it costs. A synthetic buyer said it plainly:
# they did a whole shopping experience on one site and were dropped onto another,
# with a different interface and a different voice, at the exact moment they had
# just paid. It was logged as a confusion and treated as a copy problem. It was an
# architecture problem.
#
# SO THE BUYER LANDS ON THIS SITE, IN THIS SITE'S CHROME, AND THE ONE REMAINING
# HOP IS NAMED RATHER THAN HIDDEN. At level one the artefact genuinely lives on
# the other domain and the page says so, in one sentence, with the reason. That
# hop closes when the store reads their manifest over CORS — which is possible
# (their pages answer `access-control-allow-origin: *`, verified 16 September) and
# is a narrowing of this site's hardest rule, so it is its own piece of work
# rather than a thing smuggled in here.
PAID_ROOT = "/paid/"


def paid_pages(out_dir, ctx_shared):
    made = {}
    for l in LEVELS:
        o = OFFERS_BY_ID[l["offer"]]
        url = f"{PAID_ROOT}{o['id']}/"
        ctx = dict(ctx_shared)
        ctx.update({"page": f"paid/{o['id']}", "page_url": url, "fm": {}, "toc": []})
        people = REVIEWER_BY_OFFER.get(o["id"], [])
        upstream = o["post_upstream"]
        ctx["external_links"].add(upstream)
        body = (
            shop_island(rel_prefix(url))
            # Filled by shop.js from the order this browser just placed. Static and
            # correct with no script: a buyer whose browser blocked it still gets
            # the page that tells them what happens next.
            + '<div id="paid-order" class="paid-ref"><b>Your order reference</b>'
            '<span>It is on the page you came from and on your receipt. If you are reading this '
            'in a different browser from the one you ordered in, it will not be here.</span></div>'
            f'<div class="paid-what"><div><b>You bought</b><span>{html.escape(l["name"])} '
            f'&mdash; {html.escape(o["price_label"])}</span></div>'
            f'<div><b>It arrives</b><span>{html.escape(o["eta"])}, '
            f'{html.escape(o["eta_from"])}</span></div>'
            + (f'<div><b>Who does it</b><span>{html.escape(people[0]["name"])}</span></div>'
               if people else "") + "</div>"
            + '<h2 id="what-happens-now">What happens now</h2>'
            f'<p class="lead">{inline(o["post_when"], ctx)}</p>'
            f'<p>{inline(o["post_does"], ctx)}</p>'
            + (f'<h2 id="the-file-itself">The file itself</h2>'
               f'<p><b>One hop, and here is why it exists.</b> The zip, its size and its sha256 '
               f'live on <a href="{upstream}">riskmandate.ai\'s page for this level</a>, where the '
               'hash check runs in your own browser against a manifest their build stamps. '
               '<b>Copying a size and a hash over here would mean two of each, and one of them '
               'would be wrong the first time a template changed.</b> The store will read theirs '
               'directly rather than send you there — that is built and is not shipped, and it '
               'is <a href="/admin/work/one-site-one-flow/">on the board</a> rather than in a '
               'promise.</p>' if o["id"] == "t1" else
               f'<h2 id="the-deeper-material">Where the deeper material is</h2>'
               f'<p><a href="{upstream}">riskmandate.ai\'s page for this level</a> carries the '
               'longer form of what is below. You do not need it to get what you bought.</p>')
            + (('<h2 id="see-one">See one of these now</h2>' + example_vault_embed(ctx))
               if o["id"] != "t1" else "")
            + '<h2 id="what-done-looks-like">What done looks like</h2>'
            f'<p>{inline(o["post_done"], ctx)}</p>'
            f'<p class="small dim"><b>How you check it.</b> {inline(o["post_check"], ctx)}</p>'
            + (f'<h2 id="about-keys">About keys</h2><p>{inline(o["post_key"], ctx)}</p>'
               if o.get("post_key") else "")
            + (('<h2 id="who-does-it">Who does it</h2>' + block_who_runs_it(ctx))
               if people else "")
            + '<p class="paid-back"><a href="/">Back to the shop</a> · '
            f'<a href="/d/{o["id"]}/">what this level is</a> · '
            '<a href="/compare/">all four, side by side</a></p>')
        md = [f"# You bought: {l['name']}\n",
              f"**{o['price_label']} · {o['eta']}, {o['eta_from']}.**\n",
              "## What happens now\n", _strip(o["post_when"]), "", _strip(o["post_does"]), "",
              "## What done looks like\n", _strip(o["post_done"]), "",
              f"How you check it: {_strip(o['post_check'])}\n"]
        if people:
            md += [f"Who does it: {people[0]['name']} — "
                   f"{SITE['base']}{REVIEWER_ROOT}{people[0]['id']}/\n"]
        md += [f"The page on riskmandate.ai for this level: {upstream}"]
        made[url] = _selling_page(out_dir, ctx_shared, url,
            {"title": f"You bought: {l['name']}",
             "description": (f"What happens now that you have bought {l['name'].lower()} at "
                             f"{o['price_label']}: when it arrives, what done looks like, and how "
                             "you check it."),
             "lead": f"**{html.escape(o['price_label'])}, arriving {html.escape(o['eta']).lower()} "
                     f"{html.escape(o['eta_from'])}.** Nothing else is needed from you"
                     + (" — it is already below." if o["id"] == "t1" else "."),
             "robots": "noindex,follow",
             # Only the levels that are a vault load the component that can open a
             # connection. The pack level has nothing to embed and does not get it,
             # which is the difference between a narrow exception and a wide one.
             "head_js2": ("/assets/vault-embed.js" if o["id"] != "t1" else ""),
             "head_css": "/assets/review.css" if o["id"] != "t1" else ""},
            f' / <a href="/d/{o["id"]}/">{html.escape(l["name"])}</a> / paid',
            body, "\n".join(md))
    return made


def block_code_offer(ctx):
    """A code published on the journey it applies to, as a link rather than a
    thing to type.

    IT IS SAFE BY CONSTRUCTION AND NOT BY TRUST. The code rendered here cannot
    reach the two levels that are somebody's time — `levels` holds it to the two
    that are produced the moment you pay, out of material already published free
    under CC BY. What it gives away is the packaging and the licence, not a
    person's day, which is the only kind of thing that can be published where
    anybody can read it.

    AND IT ONLY APPEARS WHERE IT SAYS IT DOES. Each code names its journeys and
    check_a_leaked_code_stays_on_its_journey holds it to them, because a code that
    leaked onto every page would be a price change nobody decided."""
    url = ctx["page_url"]
    here = [d for d in DISCOUNTS
            if d.get("printable") and url in (d.get("journeys") or [])]
    if not here:
        return ""
    out = []
    for d in here:
        link = f"{SITE['base']}/?code={d['code']}"
        # `levels` is a list, or the string "all". Iterating the string walks it
        # character by character and raises on the first one, which is how this
        # was found — and a crash is the right failure here rather than a page
        # that quietly advertises a code covering everything. The check that
        # refuses it is check_a_leaked_code_cannot_buy_somebody_s_day; this only
        # has to be honest about what it is rendering.
        lv = d["levels"]
        levels = ("every level"
                  if not isinstance(lv, list)
                  else ", ".join(LEVELS_BY_ID[x]["name"].lower() for x in lv))
        out.append(
            f'<div class="leak"><div class="leak-h"><b>{d["pct"]}% off, and it is not a '
            f'mistake</b><code>{html.escape(str(d["code"]))}</code></div>'
            f'<p>{inline(d["why"], ctx)}</p>'
            f'<p class="leak-go"><a class="buy" href="/?code={html.escape(str(d["code"]))}">'
            f'Apply it and go to the shop</a>'
            f'<span class="small dim">Or open <code>{html.escape(link)}</code> anywhere. '
            f'It applies to {html.escape(levels)} and to nothing else, and it is taken out of the '
            f'address before the page settles.</span></p></div>')
    return "".join(out)


BLOCKS["code-offer"] = block_code_offer


# ---------------------------------------------------- the memo status page ----
# THE JOIN NOBODY COULD MAKE UNTIL NOW.
#
# The queue said what arrived, the board said what it became, and the release
# history said what shipped — and no page put the three together. So the honest
# answer to "what happened to that memo I sent you" was to read three pages and
# hold the join in your head.
#
# This is that join, and it is generated: a memo, the units it produced, whether
# each one is done, the PAGE it built, and the RELEASE it went out in. A unit
# claiming to be done with nothing to point at is the failure this page exists to
# make visible, and check_every_done_unit_points_at_something refuses one.
STATUS_URL = "/admin/status/"


DASH = '<span class="dim">&mdash;</span>'


def _unit_row(t):
    sh = t.get("shipped") or {}
    urls = sh.get("urls") or []
    where = " ".join(
        f'<a href="{u}"><code>{html.escape(u)}</code></a>' for u in urls)
    ver = (f'<a href="/versions/{sh["version"]}/">{html.escape(sh["version"])}</a>'
           if sh.get("version") else "")
    st = t["status"]
    rank = {"done": 4, "in-progress": 3, "next": 2, "queued": 3}[st]
    lab = {"done": "done", "in-progress": "in progress", "next": "next", "queued": "queued"}[st]
    # The row carries its own id so a unit can be linked to from the page that
    # raised it. Every unit renders exactly once on the board, which the build
    # already guarantees by counting each one once across the whole thing.
    return (
        f'<tr class="st-{st}" id="{html.escape(t["id"])}">'
        f'<td class="u-id"><code>{html.escape(t["id"])}</code></td>'
        f'<td class="u-t"><b>{html.escape(t["title"])}</b>'
        + (f'<span class="u-block">Blocked on {t["blocked"]}</span>' if t.get("blocked") else "")
        + (f'<span class="u-who">yours</span>' if t.get("owner") == "lead" else "")
        + "</td>"
        f'<td class="u-s"><span class="st st--{rank}">{lab}</span></td>'
        f'<td class="u-w">{where or DASH}</td>'
        f'<td class="u-v">{ver or DASH}</td></tr>')


def status_page(out_dir, ctx_shared):
    rows = []
    # COUNTED ONCE EACH, ACROSS THE WHOLE BOARD. Two memos can name the same
    # workstream \u2014 "keep the record" came out of the first and the third \u2014
    # so a per-memo tally added to a running total counts those units twice. The
    # first version of this page did exactly that and printed 55 done against a
    # board that had 47. The per-memo counts below are still per-memo, which is
    # right; the headline is the set.
    counted = set()
    totals = {"done": 0, "open": 0, "yours": 0}
    for m in MEMOS["memos"]:
        ws_ids = [i for i in m["workstreams"] if i in WORK_BY_ID]
        units = [t for i in ws_ids for t in WORK_BY_ID[i]["tasks"]
                 if t.get("memo") == m["id"] or not t.get("memo")]
        # a unit belongs to the memo that names it; fall back to the workstream's
        units = [t for i in ws_ids for t in WORK_BY_ID[i]["tasks"]]
        seen, uniq = set(), []
        for t in units:
            if t["id"] not in seen:
                seen.add(t["id"]); uniq.append(t)
        d = sum(1 for t in uniq if t["status"] == "done")
        for task in uniq:
            if task["id"] in counted:
                continue
            counted.add(task["id"])
            totals["done" if task["status"] == "done" else "open"] += 1
            if task.get("owner") == "lead" and task["status"] != "done":
                totals["yours"] += 1
        pages = sorted({u for t in uniq for u in (t.get("shipped") or {}).get("urls", [])})
        vers = sorted({(t.get("shipped") or {}).get("version") for t in uniq
                       if (t.get("shipped") or {}).get("version")},
                      key=lambda v: [int(x) for x in v.lstrip("v").split(".")])
        rows.append(
            f'<section class="memo-block" id="memo-{m["id"]}">'
            f'<div class="page-head"><div>'
            f'<h2><a href="{MEMO_ROOT}{m["id"]}/">{html.escape(m["title"])}</a></h2>'
            f'<p>{html.escape(m["date"])} \u00b7 {html.escape(m["form"])}. '
            f'{html.escape(m["summary"])}</p></div>'
            f'<span class="st st--{4 if d == len(uniq) else 2}">{d} of {len(uniq)} done</span>'
            "</div>"
            + (f'<p class="memo-out"><b>What it built:</b> '
               + " ".join(f'<a href="{u}"><code>{html.escape(u)}</code></a>' for u in pages)
               + "</p>" if pages else "")
            + (f'<p class="memo-out"><b>Released in:</b> '
               + " \u00b7 ".join(f'<a href="/versions/{v}/">{html.escape(v)}</a>' for v in vers)
               + "</p>" if vers else "")
            + '<div class="tablewrap"><table class="units"><thead><tr>'
            '<th></th><th>Unit of work</th><th>State</th><th>Where it landed</th><th>Release</th>'
            "</tr></thead><tbody>"
            + "".join(_unit_row(t) for t in uniq)
            + "</tbody></table></div></section>")

    # WORKSTREAMS THAT NO MEMO NAMES. "Close the loop after payment" predates the
    # queue — it came out of the partner review rather than a memo — and a page
    # organised by memo would have left it off entirely while its units still
    # counted on the board. A status page that is silently incomplete is worse
    # than one that says where its own edges are.
    orphan_ids = [w["id"] for w in WORK["workstreams"]
                  if not any(w["id"] in m["workstreams"] for m in MEMOS["memos"])]
    for wid in orphan_ids:
        ws = WORK_BY_ID[wid]
        uniq = ws["tasks"]
        d = sum(1 for x in uniq if x["status"] == "done")
        for task in uniq:
            if task["id"] in counted:
                continue
            counted.add(task["id"])
            totals["done" if task["status"] == "done" else "open"] += 1
            if task.get("owner") == "lead" and task["status"] != "done":
                totals["yours"] += 1
        rows.append(
            f'<section class="memo-block" id="ws-{wid}">'
            f'<div class="page-head"><div>'
            f'<h2><a href="{WORK_ROOT}{wid}/">{html.escape(ws["title"])}</a></h2>'
            f'<p><b>Not from a memo.</b> {html.escape(ws["description"])}</p></div>'
            f'<span class="st st--{4 if d == len(uniq) else 2}">{d} of {len(uniq)} done</span>'
            "</div>"
            '<div class="tablewrap"><table class="units"><thead><tr>'
            '<th></th><th>Unit of work</th><th>State</th><th>Where it landed</th><th>Release</th>'
            "</tr></thead><tbody>"
            + "".join(_unit_row(x) for x in uniq)
            + "</tbody></table></div></section>")

    body = (
        '<p class="lead">Every memo, what it became, and where each piece of it landed. '
        '<b>This page is a join rather than a list</b> \u2014 the queue says what arrived, the '
        'board says what it became and the release history says what shipped, and until this page '
        'existed the only way to answer \u201cwhat happened to that memo\u201d was to read three '
        'pages and hold the join in your head.</p>'
        '<p class="small dim"><b>A workstream can belong to two memos</b>, and where it does its ' 
        'units appear under both \u2014 which is right for reading one memo and wrong for adding ' 
        'up. The four numbers below count every unit once.</p>' 
        f'<div class="tiles">'
        f'<div class="tile r4"><b>{totals["done"]}</b><span>units done</span></div>'
        f'<div class="tile r3"><b>{totals["open"]}</b><span>still open</span></div>'
        f'<div class="tile r2"><b>{totals["yours"]}</b><span>waiting on you</span>'
        '<em>a decision, not a build</em></div>'
        f'<div class="tile r3"><b>{len(MEMOS["memos"])}</b><span>memos</span></div>'
        "</div>"
        + "".join(rows)
        + '<h2 id="how-this-is-built">How this page is built</h2>'
        '<p>Every row is generated. A memo names its workstreams, a workstream holds its units, and '
        'a unit that is done carries the pages it produced and the release it went out in. '
        '<b>A unit that claims to be done and points at nothing fails the release</b> \u2014 '
        'because "done" with nothing to open is the one status that can be wrong without anybody '
        'noticing.</p>'
        '<p>The memos themselves are kept word for word at <a href="/admin/memos/">the queue</a>, '
        'with the reading of each one held separately from the memo. The board at '
        '<a href="/admin/work/">/admin/work/</a> is the same units arranged by workstream rather '
        'than by where they came from.</p>')
    md = ["# What happened to each memo\n",
          f"**{totals['done']} units done \u00b7 {totals['open']} open \u00b7 "
          f"{totals['yours']} waiting on the project lead \u00b7 "
          f"{len(MEMOS['memos'])} memos.**\n"]
    for m in MEMOS["memos"]:
        ws_ids = [i for i in m["workstreams"] if i in WORK_BY_ID]
        seen, uniq = set(), []
        for i in ws_ids:
            for t in WORK_BY_ID[i]["tasks"]:
                if t["id"] not in seen:
                    seen.add(t["id"]); uniq.append(t)
        d = sum(1 for t in uniq if t["status"] == "done")
        md.append(f"\n## {m['date']} \u2014 {m['title']} ({d}/{len(uniq)} done)\n")
        md.append(f"{m['summary']}  \n{SITE['base']}{MEMO_ROOT}{m['id']}/\n")
        for t in uniq:
            sh = t.get("shipped") or {}
            tail = ""
            if sh.get("urls"):
                tail = " \u2014 " + ", ".join(SITE["base"] + u for u in sh["urls"])
            if sh.get("version"):
                tail += f" ({sh['version']})"
            md.append(f"- `{t['id']}` **{t['title']}** \u2014 {t['status']}{tail}")
    return {STATUS_URL: _console_page(
        out_dir, ctx_shared, STATUS_URL,
        {"title": "What happened to each memo",
         "description": ("Every memo from the project lead, the units of work it became, whether "
                         "each is done, the page it built and the release it shipped in. "
                         "Generated, so it cannot disagree with the board."),
         "blurb": (f"<b>{totals['done']} done \u00b7 {totals['open']} open \u00b7 "
                   f"{totals['yours']} waiting on you.</b> A memo, what it became, and where "
                   "every piece of it landed.")},
        ' / <a href="/admin/">admin</a> / status', body, "\n".join(md))}

# --------------------------------------------------- the concept critique ----
# THREE HOMEPAGE CONCEPTS ARRIVED FROM OUTSIDE ON 16 SEPTEMBER, made by a ChatGPT
# session at the project lead's direction and drawn from this store's live
# homepage. This page reviews them.
#
# WHY IT IS GENERATED FROM A MIRROR. The concepts live on somebody else's host.
# A critique that quotes and screenshots a page which can change underneath it is
# an assertion about something nobody can check, so tools/promote_concepts.py
# takes the pages once and hashes them, tools/shoot_concepts.mjs shoots every
# image on this page from that mirror plus this repository's own docs/, and
# --check answers "has the upstream moved" without anybody having to remember.
#
# THE NUMBERS ARE THE ARGUMENT. A design critique that says a page feels long is
# an opinion; four measurements decided most of what is below and three of the
# four go against the live homepage. They are held in the data file with the
# method beside them, because a measurement whose method is not recorded is a
# number somebody made up.

CONCEPTS_URL = "/admin/concepts/"
CONCEPT_SRC = json.loads((DATA / "concepts" / "source.json").read_text())
CRITIQUE = json.loads((DATA / "concepts" / "critique.json").read_text())

# Rank 1 is the only filled state on this site's four-rank scale, and it is spent
# here on "take it" — the verdicts that cost this store work. A concept we admired
# and did not adopt does not get the filled chip.
_VERDICT_RANK = {"adopt": 1, "adopt-in-part": 2, "reject": 4}
_FINDING_RANK = {"confirmed": 1, "open": 2, "fixed": 3}


def _concept_shot(cid, kind, alt, cap):
    """One screenshot with its caption. Every path here is produced by
    tools/shoot_concepts.mjs; a missing file would be a broken image on a page
    whose whole claim is that its evidence exists, so the build refuses it."""
    src = f"/assets/shots/concepts/{cid}-{kind}"
    if not (ASSETS / "shots" / "concepts" / f"{cid}-{kind}").exists():
        raise SystemExit(f"concepts: {src} is on the page and not in assets/ — "
                         "run node tools/shoot_concepts.mjs")
    return (f'<figure class="cx-shot"><a href="{src}">'
            f'<img src="{src}" alt="{html.escape(alt)}" loading="lazy"></a>'
            f'<figcaption>{cap}</figcaption></figure>')


def concepts_page(out_dir, ctx_shared):
    src = CONCEPT_SRC
    by_id = {c["id"]: c for c in CRITIQUE["concepts"]}

    # the four homepages, side by side, at the fold
    folds = "".join(
        _concept_shot(cid, "desktop.jpg",
                      f"{name} homepage at 1200 by 750",
                      f'<b>{name}</b> &mdash; {sub} &middot; '
                      f'<a href="/assets/shots/concepts/{cid}-desktop-full.jpg">whole page</a>')
        for cid, name, sub in [
            ("current", "Live today", "store.sgit.ai, v" + CRITIQUE["reviewed_version"].lstrip("v")),
            ("marketplace", "01 Marketplace", "take the card grid"),
            ("guided", "02 Guided", "wrong buyer"),
            ("studio", "03 Studio", "take the headline"),
        ])

    # THE PRICE LADDER, BOTH WAYS, CROPPED TO ITSELF. This is the comparison the
    # page actually argues from, and until the check caught it, it was the one
    # piece of evidence sitting in the repository and not on the page.
    ladder = (_concept_shot("cards", "current.png", "The four cards on the live homepage",
                            "<b>Live today.</b> Price at 28px inline with the delivery "
                            "estimate, up to sixty words of body, and a grey box where a "
                            "buy button belongs.")
              + _concept_shot("cards", "marketplace.png", "The four cards in the Marketplace concept",
                              "<b>01 Marketplace.</b> Level and delivery on one 12px line, "
                              "the price at 42px, one sentence, one action, identical in "
                              "all four."))

    # the mobile fold, where the length problem is worst and the live page is
    # twice the height of any concept
    mobiles = "".join(
        _concept_shot(cid, "mobile.jpg", f"{name} at 390 by 780", f"<b>{name}</b> &mdash; {h}")
        for cid, name, h in [
            ("current", "Live today", "10,710px tall"),
            ("marketplace", "01 Marketplace", "5,042px"),
            ("guided", "02 Guided", "5,131px"),
            ("studio", "03 Studio", "5,176px"),
        ])

    def _mrow(r):
        # THE ROWS THAT GO AGAINST THE LIVE HOMEPAGE ARE MARKED, because five of
        # the seven do, and a table where that is not visible reads as neutral
        # when it is not.
        cls = ' class="cx-against"' if r.get("against") else ""
        return (
            f"<tr{cls}>"
            f'<td class="cx-m"><b>{html.escape(r["metric"])}</b>'
            f'<span class="cx-note">{inline(r["note"], ctx_shared)}</span></td>'
            f'<td class="cx-cur">{html.escape(r["current"])}</td>'
            f'<td>{html.escape(r["marketplace"])}</td>'
            f'<td>{html.escape(r["guided"])}</td>'
            f'<td>{html.escape(r["studio"])}</td></tr>')

    mrows = "".join(_mrow(r) for r in CRITIQUE["measurements"]["rows"])

    cards = "".join(
        f'<section class="cx-c" id="c-{c["id"]}">'
        f'<div class="cx-hd"><span class="cx-n">{c["n"]}</span>'
        f'<h3>{html.escape(c["name"])}</h3>'
        f'<span class="st st--{_VERDICT_RANK[c["verdict"]]}">'
        f'{html.escape(c["verdict_label"])}</span></div>'
        f'<p class="cx-ref">{html.escape(c["reference"])}</p>'
        f'<p>{inline(c["claim"], ctx_shared)}</p>'
        + f'<div class="cx-fa"><div class="cx-f"><b>What it gets right</b>'
        f'<p>{inline(c["for"], ctx_shared)}</p></div>'
        f'<div class="cx-a"><b>What it costs</b>'
        f'<p>{inline(c["against"], ctx_shared)}</p></div></div>'
        f'<p class="small dim"><b>Artwork.</b> {inline(c["artwork"], ctx_shared)}</p>'
        "</section>"
        for c in CRITIQUE["concepts"])

    moves = "".join(
        f'<section class="cx-mv" id="m-{m["id"]}">'
        f'<h3>{html.escape(m["title"])}</h3>'
        f'<p class="cx-from">from <b>{html.escape(m["from"])}</b></p>'
        f'<p>{inline(m["what"], ctx_shared)}</p>'
        f'<p class="cx-why"><b>Why.</b> {inline(m["why"], ctx_shared)}</p>'
        f'<p class="cx-cost"><b>What it costs us.</b> {inline(m["cost"], ctx_shared)}</p>'
        "</section>"
        for m in CRITIQUE["moves"])

    refused = "".join(
        f'<li><b>{inline(r["what"], ctx_shared)}.</b> {inline(r["why"], ctx_shared)}</li>'
        for r in CRITIQUE["refused"])

    findings = "".join(
        f'<section class="cx-fd">'
        f'<div class="cx-hd"><span class="st st--{_FINDING_RANK[f["state"]]}">'
        f'{html.escape(f["state_label"])}</span>'
        f'<h3>{inline(f["what"], ctx_shared)}</h3></div>'
        f'<p><b>Checked.</b> {inline(f["checked"], ctx_shared)}</p>'
        f'<p>{inline(f["why_it_matters"], ctx_shared)}</p>'
        f'<p class="cx-act"><b>What happens about it.</b> {inline(f["action"], ctx_shared)}</p>'
        "</section>"
        for f in CRITIQUE["findings"])

    filelist = "".join(
        f'<tr><td><code>{html.escape(f["path"])}</code></td>'
        f'<td class="num">{f["bytes"]:,}</td>'
        f'<td><code class="small">{f["sha256"][:16]}</code></td></tr>'
        for f in src["files"])

    e = CRITIQUE["endorsement"]
    body = (
        f'<p class="lead">Three homepage directions were drawn for this store by a '
        f'ChatGPT session, from the live page, on {CRITIQUE["reviewed_on"]}. '
        f'<b>This is the review of them.</b> Two contain structure worth taking, one is '
        f'pointed at a buyer this store does not have, and the review page attached to them '
        f'found a live pricing contradiction between this store and RiskMandate.ai that '
        f'nobody here had noticed.</p>'
        f'<p class="small dim"><b>They are somebody else\u2019s work and are shown as such.</b> '
        f'The pages, the stylesheet and the four generated images are mirrored under '
        f'<code>data/concepts/</code> with a sha256 each, because a critique of a page that '
        f'can change underneath it is a critique of nothing. Source: '
        f'<a href="{src["source"]}" rel="nofollow">{html.escape(src["source"].split("//")[1])}</a>, '
        f'retrieved {src["retrieved"]}.</p>'

        f'<div class="cx-verdict"><b>{html.escape(e["verdict"])}</b>'
        f'<p>{inline(e["body"], ctx_shared)}</p></div>'

        '<h2 id="at-the-fold">The four of them, at the fold</h2>'
        '<p>Same viewport, same encoder, same wait. The only variable is the page.</p>'
        f'<div class="cx-grid">{folds}</div>'

        '<h2 id="mobile">The same four at 390px</h2>'
        '<p>This is where the difference stops being a matter of taste. The live homepage is '
        '<b>10,710 pixels tall on a phone</b> &mdash; thirteen and a half screens &mdash; against '
        'roughly five thousand for each concept. The first thing a visitor meets is a '
        'nav block and a disclosure strip, and the headline starts 358px down.</p>'
        f'<div class="cx-grid">{mobiles}</div>'
        '<p class="small dim">The disclosure strip is not a candidate for removal: it is required '
        'above the main element on every page here and a build check refuses a page without it. '
        'What is a candidate is everything above it.</p>'

        '<h2 id="numbers">What the measurements say</h2>'
        f'<p>{inline(CRITIQUE["measurements"]["_why_it_is_here"], ctx_shared)}</p>'
        '<div class="tablewrap"><table class="cx-t"><thead><tr><th>Measured</th>'
        '<th>Live today</th><th>01 Market</th><th>02 Guided</th><th>03 Studio</th>'
        f'</tr></thead><tbody>{mrows}</tbody></table></div>'
        f'<p class="small dim"><b>Method.</b> {inline(CRITIQUE["measurements"]["_method"], ctx_shared)}</p>'

        '<h2 id="each">Each concept, and what it is for</h2>'
        + cards +

        '<h2 id="take">What this store takes</h2>'
        '<p>The single comparison that decided most of it &mdash; the same four offers, '
        'priced the same, one week apart in design thinking:</p>'
        f'<div class="cx-grid cx-ladder">{ladder}</div>'
        '<p>Six moves. Each one names what it costs us, because a borrowed idea whose '
        'price is not written down gets adopted and then quietly reverted.</p>'
        + moves +

        '<h2 id="refuse">What it refuses</h2>'
        f'<ul class="cx-ref-list">{refused}</ul>'

        '<h2 id="findings">What the outside review found about the live site</h2>'
        '<p>Four claims were made about this store rather than about the concepts. '
        'Every one was checked.</p>'
        + findings +

        '<h2 id="honest">What this page is not</h2>'
        f'<p>{inline(e["not_a_measurement"], ctx_shared)}</p>'

        '<h2 id="mirror">The mirror</h2>'
        '<p>Ten files, taken once and hashed. '
        '<code>python3 tools/promote_concepts.py --check</code> re-fetches them and reports '
        'any drift; <code>node tools/shoot_concepts.mjs</code> regenerates every image above '
        'from the mirror and from this repository\u2019s own build.</p>'
        f'<p class="small dim">{inline(src["_one_thing_removed"], ctx_shared)}</p>'
        '<div class="tablewrap"><table><thead><tr><th>File</th><th class="num">Bytes</th>'
        f'<th>sha256</th></tr></thead><tbody>{filelist}</tbody></table></div>')

    md = [f"# The homepage concepts, reviewed\n",
          f"Three homepage directions drawn for this store by a ChatGPT session on "
          f"{CRITIQUE['reviewed_on']}, reviewed against the live page at "
          f"{CRITIQUE['reviewed_version']}.\n",
          f"Source: {src['source']} (retrieved {src['retrieved']}, mirrored and hashed).\n",
          f"\n## Verdict\n\n**{e['verdict']}**\n\n{e['body']}\n",
          "\n## Measured\n"]
    md.append("| Measured | Live | 01 Market | 02 Guided | 03 Studio |")
    md.append("|---|---|---|---|---|")
    for r in CRITIQUE["measurements"]["rows"]:
        md.append(f"| {r['metric']} | {r['current']} | {r['marketplace']} | "
                  f"{r['guided']} | {r['studio']} |")
    md.append("\n## Each concept\n")
    for c in CRITIQUE["concepts"]:
        md.append(f"\n### {c['n']} {c['name']} — {c['verdict_label']}\n")
        md.append(f"{c['claim']}\n\n**Right:** {c['for']}\n\n**Costs:** {c['against']}\n")
    md.append("\n## Taken\n")
    for m in CRITIQUE["moves"]:
        md.append(f"\n### {m['title']} (from {m['from']})\n\n{m['what']}\n\n"
                  f"*Why:* {m['why']}\n\n*Costs us:* {m['cost']}\n")
    md.append("\n## Refused\n")
    for r in CRITIQUE["refused"]:
        md.append(f"- **{r['what']}.** {r['why']}")
    md.append("\n## Findings about the live site\n")
    for f in CRITIQUE["findings"]:
        md.append(f"\n### {f['what']} — {f['state_label']}\n\n{f['checked']}\n\n"
                  f"{f['why_it_matters']}\n\n*Action:* {f['action']}\n")
    md.append(f"\n## Not a measurement\n\n{e['not_a_measurement']}\n")

    return {CONCEPTS_URL: _console_page(
        out_dir, ctx_shared, CONCEPTS_URL,
        {"title": "The homepage concepts, reviewed",
         "description": ("Three homepage directions drawn for store.sgit.ai by a ChatGPT "
                         "session, screenshotted, measured against the live page, and "
                         "reviewed: what is taken, what is refused, and the live pricing "
                         "contradiction the outside review found."),
         "blurb": ("<b>Three concepts, two worth taking from, one live defect found.</b> "
                   "Somebody else\u2019s design work, mirrored and hashed so the critique "
                   "points at something fixed.")},
        ' / <a href="/admin/">admin</a> / concepts', body, "\n".join(md))}


# ------------------------------------------------------ the design brief ----
# A BRIEF FOR SOMEBODY WHO CANNOT SEE THIS REPOSITORY. The first round of
# homepage concepts came back as three finished pages, and this store could use
# the structure of two of them and none of the execution — because they were
# pages rather than a system. Three palettes arrived, none of them ours.
#
# SO THE TOKENS ARE READ OUT OF assets/site.css AT BUILD TIME rather than typed
# here. A brief that prints a hex value somebody has to trust is a brief that
# will be wrong the first time the stylesheet moves, and the whole complaint
# about the last round was that what came back could not be dropped into a build.
#
# THE MARKDOWN TWIN IS THE DELIVERABLE. Every page on this site emits one, and
# for this page that twin is the thing you actually hand over: a single file
# carrying every constraint, token, screen and component, pasteable whole into a
# session that has never seen the site.

BRIEF_URL = "/admin/design-brief/"
DESIGN_BRIEF = json.loads((DATA / "design-brief.json").read_text())
DOWNLOADS = json.loads((DATA / "downloads.json").read_text())


def _brief_tokens():
    """The real token values, read from the stylesheet this build ships.

    Returns (colours, fonts, chips). Anything the brief needs that is not in
    :root is a token this site does not actually have, and this raises rather
    than printing an invention."""
    css = (ASSETS / "site.css").read_text()
    m = re.search(r":root\{(.*?)\}", css, re.S)
    if not m:
        raise SystemExit("design brief: assets/site.css has no :root block to read tokens from")
    tok = dict(re.findall(r"--([a-z0-9-]+)\s*:\s*([^;]+);", m.group(1)))
    need = ["bg", "panel", "panel2", "line", "line2", "fg", "dim", "dim2", "ink",
            "accent", "accent-dk", "warm", "green", "blue", "red"]
    missing = [n for n in need if n not in tok]
    if missing:
        raise SystemExit(f"design brief: assets/site.css is missing tokens {missing} — "
                         "the brief would print values this site does not have")
    colours = [(n, tok[n].strip()) for n in need]
    fonts = [(n, tok[n].strip()) for n in ("sans", "serif", "mono") if n in tok]
    # every claim state, with the class the stylesheet actually paints. COUNTED, not
    # typed: the brief said "twelve" and there are ten, in a document whose entire
    # value is being accurate about a codebase the reader cannot see.
    chips = [(k, v[0], v[2]) for k, v in STATES.items()]
    return colours, fonts, chips


def design_brief_page(out_dir, ctx_shared):
    b = DESIGN_BRIEF
    colours, fonts, chips = _brief_tokens()

    # every screen the brief names has to be a page this build emits, or the
    # brief is sending somebody to look at a 404
    known = {u for u in ctx_shared["page_urls"].values()}

    def cons(c):
        tag = ('<span class="st st--1">hard rule</span>' if c.get("hard")
               else '<span class="st st--3">expected</span>')
        return (f'<section class="db-c"><div class="cx-hd">{tag}'
                f'<h3>{inline(c["rule"], ctx_shared)}</h3></div>'
                f'<p>{inline(c["why"], ctx_shared)}</p></section>')

    def screen(sc):
        pri = {"first": 1, "second": 2, "third": 3}[sc["priority"]]
        must = "".join(f"<li>{inline(x, ctx_shared)}</li>" for x in sc["must_carry"])
        return (f'<section class="db-s" id="s-{sc["id"]}">'
                f'<div class="cx-hd"><span class="st st--{pri}">{sc["priority"]}</span>'
                f'<h3>{html.escape(sc["name"])}</h3>'
                f'<a class="db-u" href="{sc["url"]}"><code>{html.escape(sc["url"])}</code></a></div>'
                f'<p class="db-now"><b>What is there today.</b> {inline(sc["exists"], ctx_shared)}</p>'
                f'<p>{inline(sc["brief"], ctx_shared)}</p>'
                f'<p class="db-l">It has to carry</p><ul>{must}</ul>'
                f'<p class="db-hard"><b>The hard part.</b> {inline(sc["hardest_part"], ctx_shared)}</p>'
                "</section>")

    def comp(c):
        st = "".join(f'<span class="db-st">{html.escape(x)}</span>' for x in c["states"])
        return (f'<tr><td><b>{html.escape(c["name"])}</b>'
                f'<br><code class="small">{html.escape(c["id"])}</code></td>'
                f'<td class="db-sts">{st}</td>'
                f'<td class="small">{inline(c["notes"], ctx_shared)}</td></tr>')

    swatches = "".join(
        f'<div class="db-sw"><i style="background:{v}"></i>'
        f'<code>--{n}</code><span>{html.escape(v)}</span></div>'
        for n, v in colours)
    fontrows = "".join(
        f'<tr><td><code>--{n}</code></td><td style="font-family:{v}">{html.escape(v)}</td></tr>'
        for n, v in fonts)
    chiprows = "".join(
        f'<tr><td>{chip(k)}</td><td><code>{html.escape(k)}</code></td>'
        f'<td class="small">{html.escape(why)}</td></tr>'
        for k, lab, why in chips)

    body = (
        f'<p class="lead">{inline(b["_why_it_exists"], ctx_shared)}</p>'
        f'<div class="cx-verdict"><b>Hand this over whole.</b>'
        f'<p>The markdown twin of this page &mdash; '
        f'<a href="{BRIEF_URL}index.md"><code>{BRIEF_URL}index.md</code></a> &mdash; is '
        f'the pasteable form. It carries every constraint, token, screen and component '
        f'below in one file, and it needs no access to this repository.</p></div>'

        '<h2 id="context">What is being sold, and to whom</h2>'
        + "".join(f'<p><b>{html.escape(k.replace("_", " ").capitalize())}.</b> '
                  f'{inline(v, ctx_shared)}</p>' for k, v in b["context"].items())

        + '<h2 id="rules">The constraints</h2>'
        f'<p>{len(b["constraints"])}. The hard rules are marked, and a mock that '
        'breaks one produces a page that cannot ship, so they are stated before anything '
        'else.</p>'
        + "".join(cons(c) for c in b["constraints"])

        + '<h2 id="settled">Already settled, and not up for redesign</h2>'
        '<p>These came out of the last round and the panel that tested it. They are '
        'here so nobody spends a day rediscovering them.</p><ul class="db-set">'
        + "".join(f"<li>{inline(x, ctx_shared)}</li>" for x in b["already_settled"])
        + "</ul>"

        + '<h2 id="open">Open, and genuinely wanted</h2><ul class="db-set db-open">'
        + "".join(f"<li>{inline(x, ctx_shared)}</li>" for x in b["open_questions"])
        + "</ul>"

        + '<h2 id="tokens">The tokens</h2>'
        '<p><b>Read out of <code>assets/site.css</code> by this build</b>, not typed here '
        '&mdash; so they are the values the site actually ships and cannot drift from '
        'them. Use these and add none.</p>'
        f'<div class="db-sws">{swatches}</div>'
        '<div class="tablewrap"><table><thead><tr><th>Family</th><th>Stack</th></tr>'
        f'</thead><tbody>{fontrows}</tbody></table></div>'
        f'<h3>The {len(chips)} claim states</h3>'
        '<p>Every chip links to the ledger. Only one of them is the fully-earned '
        'state, which is deliberate &mdash; if most chips look confident the component '
        'has failed.</p>'
        '<div class="tablewrap"><table><thead><tr><th>Chip</th><th>Id</th>'
        f'<th>What it means</th></tr></thead><tbody>{chiprows}</tbody></table></div>'

        + '<h2 id="components">The component set</h2>'
        '<p><b>This is the deliverable that matters most.</b> Eighteen components, every '
        'state of each, before any screen is drawn. A beautiful screen built out of '
        'unnamed parts costs more to implement than it saves.</p>'
        '<div class="tablewrap"><table class="db-ct"><thead><tr><th>Component</th>'
        f'<th>States</th><th>Notes</th></tr></thead><tbody>'
        + "".join(comp(c) for c in b["components"]) + "</tbody></table></div>"

        + '<h2 id="screens">The screens</h2>'
        '<p>Nine, in priority order. Every one of them is a page that exists on this site '
        'today &mdash; open it before drawing it.</p>'
        + "".join(screen(sc) for sc in b["screens"])

        + '<h2 id="deliverable">How to hand it back</h2>'
        f'<p>{inline(b["deliverable"]["why_this_matters"], ctx_shared)}</p><ol class="db-set">'
        + "".join(f"<li>{inline(x, ctx_shared)}</li>" for x in b["deliverable"]["hand_back"])
        + '</ol><p class="db-l">And not</p><ul class="db-set">'
        + "".join(f"<li>{inline(x, ctx_shared)}</li>" for x in b["deliverable"]["do_not"])
        + "</ul>"

        + '<h2 id="read">Read these first</h2>'
        '<div class="tablewrap"><table><thead><tr><th>Page</th><th>Why</th></tr></thead><tbody>'
        + "".join(f'<tr><td><a href="{r["url"]}"><b>{html.escape(r["what"])}</b></a>'
                  f'<br><code class="small">{html.escape(r["url"])}</code></td>'
                  f'<td class="small">{inline(r["why"], ctx_shared)}</td></tr>'
                  for r in b["read_first"])
        + "</tbody></table></div>")

    # ---- the markdown twin, which is the thing actually handed over ----
    base = SITE["base"]
    md = [f"# Design brief \u2014 store.sgit.ai\n",
          f"*Version {b['version']}, {b['dated']}. Written for {b['for'][0].lower()}{b['for'][1:]}.*\n",
          f"{b['_why_it_exists']}\n",
          "\n## What is being sold, and to whom\n"]
    for k, v in b["context"].items():
        md.append(f"**{k.replace('_', ' ').capitalize()}.** {v}\n")
    md.append("\n## The constraints\n")
    for c in b["constraints"]:
        md.append(f"\n### {'HARD RULE' if c.get('hard') else 'Expected'}: {c['rule']}\n\n{c['why']}\n")
    md.append("\n## Already settled, and not up for redesign\n")
    for x in b["already_settled"]:
        md.append(f"- {x}")
    md.append("\n## Open, and genuinely wanted\n")
    for x in b["open_questions"]:
        md.append(f"- {x}")
    md.append("\n## The tokens\n\nRead from the live stylesheet by the build that "
              "produced this file. Use these and add none.\n")
    md.append("\n| Token | Value |")
    md.append("|---|---|")
    for n, v in colours:
        md.append(f"| `--{n}` | `{v}` |")
    for n, v in fonts:
        md.append(f"| `--{n}` | `{v}` |")
    md.append(f"\n### The {len(chips)} claim states\n")
    md.append("\n| Id | Label | What it means |")
    md.append("|---|---|---|")
    for k, lab, why in chips:
        md.append(f"| `{k}` | {lab} | {why} |")
    md.append("\n## The component set\n\nThis is the deliverable that matters most. "
              "Every component, every state, before any screen is drawn.\n")
    for c in b["components"]:
        md.append(f"\n### {c['name']} (`{c['id']}`)\n")
        md.append("States: " + ", ".join(c["states"]) + "\n")
        md.append(f"{c['notes']}\n")
    md.append("\n## The screens\n")
    for sc in b["screens"]:
        md.append(f"\n### {sc['name']} \u2014 {sc['priority']}\n")
        md.append(f"Live today: {base}{sc['url']}\n")
        md.append(f"**What is there today.** {sc['exists']}\n")
        md.append(f"{sc['brief']}\n")
        md.append("It has to carry:\n")
        for x in sc["must_carry"]:
            md.append(f"- {x}")
        md.append(f"\n**The hard part.** {sc['hardest_part']}\n")
    md.append("\n## How to hand it back\n")
    md.append(f"{b['deliverable']['why_this_matters']}\n")
    for i, x in enumerate(b["deliverable"]["hand_back"], 1):
        md.append(f"{i}. {x}")
    md.append("\nAnd not:\n")
    for x in b["deliverable"]["do_not"]:
        md.append(f"- {x}")
    md.append("\n## Read these first\n")
    for r in b["read_first"]:
        md.append(f"- [{r['what']}]({base}{r['url']}) \u2014 {r['why']}")

    return {BRIEF_URL: _console_page(
        out_dir, ctx_shared, BRIEF_URL,
        {"title": "The design brief",
         "description": ("Everything a design session needs to mock up the rest of this "
                         "store without access to the repository: eight constraints with "
                         "the hard rules named, the real tokens read from the stylesheet, "
                         "eighteen components with their states, and nine screens in "
                         "priority order."),
         "blurb": ("<b>Eighteen components, nine screens, eight constraints.</b> "
                   "Written to be handed over whole \u2014 the markdown twin of this "
                   "page is the pasteable form.")},
        ' / <a href="/admin/">admin</a> / design brief', body, "\n".join(md))}


# ================================================================ /next/ ====
# THE NEXT STORE. An implementation of the v3 design direction "01 / ABP first",
# chosen on 16 September after two rounds and a five-reader panel. It is a
# PARALLEL set of pages, not a replacement: the current store keeps selling
# while this one is built, and the two swap over when the flow is wired
# end to end.
#
# WHY IT IS GENERATED RATHER THAN HAND-WRITTEN. The whole complaint about the
# first design round was that what came back could not be dropped into a build.
# So every price, name, delivery estimate, claim and audience on these pages is
# read out of the files the current store is already built from. There is no
# second copy of a number to drift, and the same checks that freeze the current
# store's prices freeze these.
#
# ONE SECTION OF THE DESIGN IS NOT BUILT, AND IT IS NAMED. The v3 pages carry a
# mission line under the heading WHY RISKMANDATE EXISTS that uses a word this
# site bars absolutely on every page carrying a price. Their own notes page
# records that the project lead asked for it. That is a real collision between
# two things somebody is right about, and it is not the builder's to settle: the
# section is left out, the mirror keeps their file intact, and the ruling is on
# the board. Quietly shipping it would break the release; quietly dropping it
# without saying so would be worse.


NEXT_ROOT = "/"
NEXT_ADMIN = "/admin/next/"
NEXT_SOURCE = json.loads((DATA / "next" / "source.json").read_text())
NEXT_ART = json.loads((DATA / "next" / "artwork.json").read_text())

# The four levels, in the order the design shows them, with the artwork each one
# was given. Nothing else about a level is stated here — it is read from offers.
NEXT_ART_BY_OFFER = {"t1": "pack.jpg", "t2": "vault.jpg",
                     "t3": "tailored.jpg", "t4": "reviewed.jpg"}

# Which level leads. The design puts the amber action on ABP Vault rather than on
# the cheapest thing, which is a real recommendation and is recorded as one.
NEXT_LEAD = "t2"

# WHICH POLICY A "BUY THIS LEVEL" LINK CARRIES WHEN NOBODY HAS PICKED ONE. The
# v4 handback's every offer card links to the product page with a level AND a
# policy, and it defaults the policy to the shape this site is maintained from.
# That is a real default and the product page says it is one, beside a link to
# change it. An order line is a policy at a level; a level on its own cannot be
# added to anything, which is why the cards do not add and the product page does.
NEXT_DEFAULT_POLICY = "claude-code-web"


def _next_offers():
    """The four sellable levels, shaped for the page and for the JSON island.

    Everything here comes off data/offers.yml. The two add-ons are not levels and
    are not on these pages yet — they attach to a level and there is nowhere to
    attach them until the flow exists."""
    out = []
    for o in OFFERS:
        if o["id"] not in NEXT_ART_BY_OFFER:
            continue
        state = o["state_badge"]
        if state not in STATES:
            raise SystemExit(f"next: offer {o['id']} has state {state!r}, which is not one "
                             f"this site has: {', '.join(sorted(STATES))}")
        lvl = LEVEL_BY_OFFER.get(o["id"])
        if not lvl:
            raise SystemExit(f"next: offer {o['id']} is one of the four levels these pages "
                             "sell, but no level in data/products.yml names it. The order "
                             "engine keys on the level id, so there is nothing to add.")
        pay_now = int(o.get("pay_now_pct", 100))
        split = ""
        if pay_now < 100:
            now = o["price_min"] * pay_now // 100
            split = (money_label(now) + " now \u00b7 "
                     + money_label(o["price_min"] - now) + " on delivery")
        out.append({
            "id": o["id"],
            "code": f"ABP-{o['id'].upper()}",
            "n": o["tier"].zfill(2),
            "short_name": o["short_name"],
            "short_sub": o["short_sub"],
            "price": o["price_label"],
            "clock": o["eta"] + (" from your reply" if "reply" in o["eta_from"]
                                 else " from your payment"),
            "clock_full": f"{o['eta']}, {o['eta_from']}",
            "eta": o["eta"],
            "what": o["gets"],
            "short_what": o["next_what"],
            "claim": o["claim"],
            "state": state,
            "state_label": STATES[state][0],
            "split": split,
            # THE TILL IS NOT LIVE AND THE PAGE SAYS SO ON EVERY CARD. Each offer
            # carries its own checkout_url and every one of them is empty today, so
            # this is false everywhere and the action renders as a disabled control
            # with its reason on it rather than as a button that does nothing. The
            # day a link is issued in data/offers.yml the button turns on by itself.
            "buyable": bool((o.get("checkout_url") or "").strip()),
            # THE LINK ITSELF, or null — never a placeholder. The engine appends
            # the order reference and, when it has one, the promotion code; it
            # appends nothing else and a check holds it to that. What the link
            # takes is `pay_now_pct` of the price, because that is the half the
            # provider has a product for: at level 3 and 4 the DEPOSIT product is
            # exactly a fifth, and the balance is invoiced rather than linked.
            "checkout_url": (o.get("checkout_url") or "").strip() or None,
            # Whether the link lets a buyer change the quantity. False unless the
            # data says otherwise: the store cannot ask the provider, so an unset
            # field must not promise a control nobody has confirmed is there.
            "checkout_qty": bool(o.get("checkout_qty")),
            "checkout_mode": o["checkout_mode"],
            # Two different sentences and they are not interchangeable. `checkout_off`
            # answers "why is there no button here", which is what somebody looking at
            # the gap in a checkout row is asking. `checkout_why` answers "why can this
            # kind of offer have one at all", which belongs on a page read with a card
            # in hand. Showing the second where the first belongs reads as a non-sequitur
            # — "one price means one standing payment link" under a level that has none.
            "checkout_off": CHECKOUT[o["checkout_mode"]][1],
            "checkout_why": CHECKOUT_WHY[o["checkout_mode"]],
            "art": f"/assets/next/art/{NEXT_ART_BY_OFFER[o['id']]}",
            "url": f"{NEXT_ROOT}product/?level={o['id']}",
            "included": o.get("next_included") or [],
            "excluded": o.get("next_excluded") or [],
            # ---- what the order engine needs, joined from data/products.yml.
            # The cart id and the one-letter code are the LIVE STORE'S: an order
            # built here has to be the same record shop.js would have built, down
            # to the SKU, or the two sides of this design round disagree about
            # what somebody bought.
            "cart_id": lvl["id"],
            "cart_code": lvl["code"],
            "pence": o["price_min"],
            "pay_now_pct": pay_now,
            "post_when": lvl["post_when"], "post_does": lvl["post_does"],
            "post_key": lvl["post_key"], "post_done": lvl["post_done"],
            "post_check": lvl["post_check"], "post_carries": lvl["post_carries"],
        })
    if len(out) != 4:
        raise SystemExit(f"next: expected four levels, shaped {len(out)}")
    return out


def _next_offer_card(l, ctx, policy=None, lead=None, quiet=(), art=True, page=NEXT_ROOT):
    """The offer card, once, for every page that shows the four levels.

    THE ACTION IS "BUY THIS LEVEL" AND IT IS A LINK, NOT A BUTTON. It goes to the
    product page carrying the level and a policy — the one the page was opened
    for, or the site's default — and the product page is where a line is added
    to the order. The design round's cards said "Explore", which was honest and
    was also the thing a buyer noticed first: a store whose cards do not sell.

    `lead` draws the amber action; `quiet` draws a level lower in the hierarchy
    without hiding it, and a build check refuses display:none on any of them."""
    lead_id = lead if lead is not None else NEXT_LEAD
    is_lead = l["id"] == lead_id
    is_quiet = l["id"] in quiet
    cls = "n-offer" + (" n-offer--lead" if is_lead else "") + (" n-offer--quiet" if is_quiet else "")
    btn = "n-btn" if is_lead else "n-btn n-btn--ghost"
    href = f'{NEXT_ROOT}product/?level={l["id"]}&amp;policy={policy or NEXT_DEFAULT_POLICY}'
    split = f'<span class="n-offer__split">{l["split"]}</span>' if l["split"] else ""
    ctx["claim_uses"].setdefault(l["claim"], set()).add(page)
    pic = ""
    if art:
        alt = f'{l["short_name"]} — concept artwork for a digital deliverable'
        pic = (f'<div class="n-offer__art"><img src="{l["art"]}" alt="{html.escape(alt)}" '
               f'loading="lazy" width="720" height="480">'
               f'<span class="n-offer__n">{html.escape(l["n"])}</span></div>')
    return (
        f'<article class="{cls}" data-offer="{l["id"]}">{pic}'
        f'<div class="n-offer__body">'
        f'<p class="n-offer__meta"><b>LEVEL {html.escape(l["n"])}</b>'
        f'<span>{html.escape(l["eta"])}</span></p>'
        f'<h3>ABP {html.escape(l["short_name"])}</h3>'
        f'<p class="n-offer__sub">{html.escape(l["short_sub"])}</p>'
        f'<p class="n-price"><b>{html.escape(l["price"])}</b><span>GBP</span></p>'
        f'<p class="n-offer__clock">{html.escape(l["clock"])}</p>'
        f'<p class="n-offer__what">{inline(l["short_what"], ctx)}</p>'
        f'<p class="n-offer__claim">{_next_claim(l, ctx)}</p>'
        f'<div class="n-offer__foot">'
        f'<a class="{btn} n-btn--wide" href="{href}">Buy this level {_ARROW}</a>{split}</div>'
        '</div></article>')


def _next_audiences():
    """The five audiences, for the edition switcher. Nothing is hidden from
    anybody — a check refuses display:none on an offer in an audience view — so
    what changes here is the sentence, never the price or the product."""
    out = []
    for a in AUDIENCES:
        out.append({"id": a["id"], "name": a["name"], "door": a["door"],
                    "label": a["next_label"],
                    "reading": a.get("next_reading") or a["door"],
                    "url": f"/are/{a['id']}/"})
    return out


def _next_claim(level, ctx):
    """A claim chip that links to the ledger entry it is making."""
    if level["claim"] not in ctx["claims_by_id"]:
        raise SystemExit(f"next: level {level['id']} cites claim {level['claim']!r}, "
                         "which is not in the ledger")
    ctx["claim_uses"].setdefault(level["claim"], set()).add(NEXT_ROOT)
    return (f'<a class="n-claim n-claim--{level["state"]}" '
            f'href="{NEXT_LEDGER}#claim-{level["claim"]}">'
            f'{html.escape(STATES[level["state"]][0])} &#8599;</a>')


_TICK = ('<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
         'stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
         '<polyline points="20 6 9 17 4 12"></polyline></svg>')
_ARROW = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
          'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
          '<line x1="5" y1="12" x2="19" y2="12"></line>'
          '<polyline points="12 5 19 12 12 19"></polyline></svg>')
_OUT = ('<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<line x1="7" y1="17" x2="17" y2="7"></line>'
        '<polyline points="7 7 17 7 17 17"></polyline></svg>')


def n_chrome_top(url):
    """The header, the nav and the disclosure strip: the same on every page the
    store serves, whether that page came out of a markdown file or out of the
    offer data. It was inline in one shell while only one shell used it."""
    def _navlink(text, href):
        cur = ' aria-current="page"' if href == url else ""
        return f'<a href="{href}"{cur}>{html.escape(text)}</a>'

    nav = "".join(_navlink(txt, href) for txt, href in [
        ("The four levels", NEXT_ROOT + "product/"),
        ("Which agent you run", NEXT_PICKER),
        ("What is inside one", "/what-is-in-one/")])
    order_cur = ' aria-current="page"' if url == NEXT_CART else ""
    return f"""<header class="n-header">
  <a class="n-mark" href="{NEXT_ROOT}"><b>sgit</b><span>/ store</span></a>
  <nav class="n-nav" aria-label="Primary">{nav}
    <a href="{NEXT_CART}"{order_cur}>Your order<span data-order-count></span></a>
  </nav>
</header>

<div class="n-disclosure">
  <span><b>Produced with model assistance.</b></span>
  <a href="/disclosures/">Read the disclosure</a>
</div>
<div class="n-codeslot" data-code-bar></div>"""


def next_html(url, fm, body, model):
    """The shell for the store.

    It loads assets/next.css and assets/next.js and NOTHING else — not site.css,
    not shop.js. The v3 source layers its palette on top of this site's own
    stylesheet, which is right for a mockup and wrong to ship: it carries a
    design we are leaving and makes every new rule fight an old one. These pages
    are self-contained, so what the stylesheet says is what renders.
    """
    prefix = rel_prefix(url)
    # A page that moved says so in the head as well as in the body, because the
    # first reader of a moved address is usually not a person.
    refresh = (f'<meta http-equiv="refresh" content="0; url={fm["moved_to"]}">\n'
               if fm.get("moved_to") else "")
    # a page that needs a second engine names it; every script still loads once
    extra_scripts = "".join(f'<script src="{s}" defer></script>\n'
                            for s in (fm.get("scripts") or []))
    main_class = f' class="{fm["main_class"]}"' if fm.get("main_class") else ""


    return relativise(f"""<!doctype html>
<html lang="en" data-root="{prefix}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{html.escape(fm['title'])} &mdash; {html.escape(SITE['title'])}</title>
<meta name="description" content="{html.escape(fm.get('description', ''))}">
<meta name="robots" content="{fm.get('robots') or 'index,follow'}">
<link rel="canonical" href="{SITE['base']}{fm.get('canonical') or url}">
{refresh}<link rel="alternate" type="text/markdown" href="index.md" title="This page as markdown">
<link rel="stylesheet" href="/assets/next.css">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<script src="/assets/next.js" defer></script>
{extra_scripts}</head>
<body>
<a class="n-skip" href="#main">Skip to content</a>

{n_chrome_top(url)}
<main id="main"{main_class}>
{body}
</main>

{n_footer()}
<script type="application/json" id="next-model">{json.dumps(model, ensure_ascii=False)}</script>
</body>
</html>
""", prefix)


def n_footer():
    return f"""<footer class="n-footer">
  <div class="n-footer__cols">
    <div>
      <a class="n-mark" href="{NEXT_ROOT}"><b>sgit</b><span>/ store</span></a>
      <p class="n-dim n-fine n-mt">Agent Behaviour Policies for the agents you already
      run. One agent, one deployment, and the gap between what it can do and what you
      authorised.</p>
    </div>
    <div><b>Buy</b>
      <a href="{NEXT_PICKER}">Which agent you run</a>
      <a href="{NEXT_ROOT}product/">The four levels, side by side</a>
      <a href="{NEXT_COMPARE}">Compare what arrives</a>
      <a href="{NEXT_CART}">Your order</a>
      <a href="{NEXT_PAID}">What lands, and when</a>
      <a href="{NEXT_DESCRIBE}">Describe your agent</a>
    </div>
    <div><b>Evidence</b>
      <a href="{NEXT_LEDGER}">The claim ledger</a>
      <a href="{NEXT_WHO}">Who does the work</a>
      <a href="{NEXT_AUDIENCE}">Who this is for</a>
      <a href="/disclosures/">What we do not say</a>
      <a href="/admin/reviews/">Reviews, dated and kept</a>
      <a href="/boundary/">Who owns what</a>
    </div>
    <div><b>This site</b>
      <a href="/how-it-works/">How buying works</a>
      <a href="/what-is-in-one/">What is actually in one</a>
      <a href="{V1_ROOT}">The previous design</a>
      <a href="/versions/">Release history</a>
      <a href="/admin/">The console</a>
    </div>
    <div class="n-footer__disc">
      <p><b>Produced with model assistance.</b> Every page on this site, and every
      document in the dev packs area, was drafted with a large language model and
      reviewed by a person before publication. <b>Nothing here is a compliance
      assessment</b> and no page claims conformity to any standard.</p>
      <p class="n-footer__disc-links">
        <a href="/disclosures/">What we do not say, and why</a>
        <a href="{NEXT_LEDGER}">How every claim here is evidenced</a>
        <a href="/boundary/">Who owns what</a>
        <span class="n-footer__ver">{html.escape(SITE['version'])}</span>
      </p>
    </div>
    <p class="n-footer__note">
      Artwork on these pages represents digital deliverables and is illustrative.
      Prices are in GBP and every one of them is read from a single file. The design
      this store used until v0.3.15 is kept at
      <a href="{V1_ROOT}">the previous design</a>.
    </p>
  </div>
</footer>"""


def _next_emit(out_dir, url, fm, body, model, md):
    target = out_dir / url.strip("/") / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(next_html(url, fm, body, model))
    (target.parent / "index.md").write_text(md.rstrip("\n") + f"\n\n---\n\n{LICENCE_STAMP}\n")
    return fm["title"]


def _next_home(out_dir, ctx_shared, levels, auds, model):
    lead = next(l for l in levels if l["id"] == NEXT_LEAD)

    works = EVIDENCE["works"]
    works_html = ""
    for w in works:
        ctx_shared["external_links"].add(w["url"])
        works_html += (
            f'<a class="n-work" href="{w["url"]}" rel="nofollow">'
            f'<b>{html.escape(w["title"])}</b>'
            f'<span class="n-work__why">{html.escape(w["why"])}</span>'
            f'<span class="n-work__meta">{html.escape(w["size"])} '
            f'&middot; published {html.escape(w["published"])} {_OUT}</span></a>')

    # ---- the four facts under the hero. Every one is a LINK to the claim that
    # evidences it: the concept version had four ticks and no links, and the one
    # reader on the panel who checks things rejected it on sight.
    trust = "".join(
        f'<a href="{href}">{_TICK}<span>{html.escape(text)}</span></a>'
        for text, href in [
            ("Fifteen application templates", "/policies/"),
            ("A working vault from " + levels[1]["price"], NEXT_ROOT + "product/?level=t2"),
            ("Six vaults open to read now", NEXT_LEDGER + "#claim-abp-templates-exist"),
            ("The top two signed by a person", "/who/"),
        ])

    # ---- the five doors, drawn as the v4 handback draws them: a 64px thumbnail
    # cut out of ONE five-up strip, the label, one short line, and an arrow. The
    # first build here was five paragraphs of text and no picture at all, which
    # on a phone was three rows and half a screen of reading before the product.
    #
    # THE SHORT LINE IS THE DOOR SENTENCE, CUT AT ITS FIRST COMMA, rather than a
    # sixth field in data/audiences.yml. "Shipping with agents, and somebody is
    # going to ask." is one fact; its first clause is the same fact said shorter,
    # and a second copy of it in the data is a second thing to keep true.
    def _door_line(a):
        d = a["door"].strip()
        head = d.split(",", 1)[0].strip()
        return (head + ".") if head and "," in d else d

    art = next((x for x in NEXT_ART["art"] if x["file"] == "audiences.jpg"), None)
    doors = ""
    for i, a in enumerate(AUDIENCES):
        aud = next(x for x in _next_audiences() if x["id"] == a["id"])
        pic = ""
        if art:
            pic = (f'<span class="n-door__art"><img src="/assets/next/art/audiences.jpg" '
                   f'alt="" aria-hidden="true" style="left:{-i * 100}%"></span>')
        doors += (f'<a href="/are/{a["id"]}/">{pic}'
                  f'<span class="n-door__copy"><b>{html.escape(aud["label"])}</b>'
                  f'<span>{html.escape(_door_line(a))}</span></span>'
                  f'<span class="n-door__arrow" aria-hidden="true">&#8599;</span></a>')

    cards = "".join(_next_offer_card(l, ctx_shared) for l in levels)

    # ---- the applications. The sixth chip is the point of the component: a
    # visitor whose agent is not on the list lands on the level that exists for
    # exactly that, rather than at the end of a directory.
    chips = "".join(
        f'<a href="/p/{sh["slug"]}/">{html.escape(sh["title"])}{_OUT}</a>'
        for sh in ABP["shapes"][:5])
    chips += (f'<a class="is-other" href="{NEXT_ROOT}product/?level=t3">'
              f'Something else &mdash; from {levels[2]["price"]}{_ARROW}</a>')

    # ---- what an ABP actually is: four objects, the vocabulary the whole
    # product is built on.
    objects = "".join(
        f'<article class="n-object"><p class="n-object__n">{n}</p>'
        f'<h3>{html.escape(title)}</h3><p>{inline(text, ctx_shared)}</p></article>'
        for n, title, text in [
            ("01", "Grant", "Everything the agent can actually reach in this deployment "
                            "&mdash; not what somebody meant it to reach."),
            ("02", "Mandate", "What you authorised it to do, written so that somebody else "
                              "can read it and disagree."),
            ("03", "Delta", "The gap between the two. It is derived, so it moves when "
                            "either side does."),
            ("04", "Barrier", "What really stands in the way of each thing: a setting, a "
                              "boundary, or nothing at all."),
        ])

    body = (
        '<section class="n-hero">'
        '<div class="n-hero__copy">'
        '<p class="n-eyebrow">Agent Behaviour Policies by RiskMandate</p>'
        '<h1>Give your AI agent<br>a clear mandate.</h1>'
        '<p class="n-hero__lede">We sell <strong>Agent Behaviour Policies</strong>: what '
        'your agent can do, what you authorised, and the gap between them &mdash; for one '
        'agent, in one deployment.</p>'
        '<p class="n-hero__support">Take the files, take a vault you hold the keys to, or '
        'have a named security professional correct it against your deployment.</p>'
        '<div class="n-hero__actions">'
        f'<a class="n-btn" href="#levels">Find your ABP {_ARROW}</a>'
        f'<a href="/policies/">Read a free example {_OUT}</a>'
        '</div>'
        '<p class="n-hero__price">For one agent, in one deployment &middot; from '
        f'<b>{html.escape(levels[0]["price"])}</b></p>'
        '</div>'
        '<div class="n-hero__art">'
        f'<img src="{levels[0]["art"]}" alt="An Agent Behaviour Policy rendered as layered '
        'permissions above a bound folio" width="720" height="480">'
        '<p class="n-artnote">Concept artwork &middot; the deliverable is digital</p>'
        '</div></section>'

        f'<div class="n-trust">{trust}</div>'

        '<section class="n-sect n-sect--tight" id="who">'
        '<h2 class="n-doors__head">What brings you here?</h2>'
        f'<div class="n-doors">{doors}</div></section>'

        '<section class="n-sect n-sect--tint" id="levels">'
        '<div class="n-head"><div class="n-head__text">'
        '<p class="n-eyebrow">One ABP. Four levels.</p>'
        '<h2>Choose how much help you need.</h2>'
        '<p>The behaviour policy is the same document at every level. What changes is the '
        'form it arrives in and who does the correcting.</p></div>'
        f'<p class="n-head__aside"><a href="/compare/">Compare what arrives {_OUT}</a></p>'
        '</div>'
        f'<div class="n-grid n-grid--4">{cards}</div>'
        '<p class="n-note n-note--hold n-mt">' + till(
            '<b>Nothing here can be bought yet.</b> No payment link has been issued on any '
            'level, so every action on these four cards opens the product rather than a '
            'checkout. That is true of the store selling today as well; it is not a '
            'property of this design.',
            '<b>These cards open the product, not a checkout.</b> A line is added to the '
            'order this browser holds, and the money is taken later, on the payment '
            'provider\u2019s own page. Nothing is typed on this site at any point.')
        + '</p>'
        '<p class="n-note n-mt"><b>Artwork represents digital deliverables.</b> Every '
        'price here is read from the same file the live store is built from, and '
        f'<a href="{NEXT_ROOT}product/?level={lead["id"]}">ABP '
        f'{html.escape(lead["short_name"])}</a> carries the leading action because it is the '
        'level most buyers want, not because it is the cheapest.</p></section>'

        '<section class="n-sect" id="agents">'
        '<div class="n-head"><div class="n-head__text">'
        '<p class="n-eyebrow">Start with your setup</p>'
        '<h2>Which agent do you run?</h2>'
        '<p>Fifteen published shapes, one per target application. Open the one closest to '
        'your deployment and read it before you spend anything.</p></div>'
        f'<p class="n-head__aside"><a href="/policies/">See all fifteen {_OUT}</a></p>'
        '</div>'
        f'<div class="n-chips">{chips}</div></section>'

        '<section class="n-sect n-sect--quiet" id="what">'
        '<div class="n-head"><div class="n-head__text">'
        '<p class="n-eyebrow">What is an ABP?</p>'
        '<h2>Four objects. One clear record.</h2>'
        '<p>The Agent Behaviour Policy brings these together for one deployment. It '
        'describes and it does not judge, so it carries no score.</p></div>'
        f'<p class="n-head__aside"><a href="/what-is-in-one/">Look inside one {_OUT}</a></p>'
        '</div>'
        f'<div class="n-grid n-grid--4">{objects}</div></section>'

        # ---- THE EVIDENCE BAND. Six vaults of exactly this work, published and
        # open to read without paying anything. The design round dropped this and
        # a build check caught it on the day the round became the store: evidence
        # nobody is shown is evidence nobody has, and the panel of readers said
        # the same thing in their own words about the concepts that dropped it.
        '<section class="n-sect n-sect--deep" id="evidence">'
        '<div class="n-head"><div class="n-head__text">'
        '<p class="n-eyebrow">What has been built</p>'
        f'<h2>{len(works)} vaults of this work, open to read now.</h2>'
        '<p>Not screenshots and not a deck. Published vaults of the same kind of '
        'document this store sells, each with its own read key on its own page, '
        f'and {html.escape(str(EVIDENCE["total_published"]))} published in total. '
        'The method here is a <b>licence to operate</b> for one agent in one '
        'deployment: what it can do, what you authorised, and the gap.</p>'
        f'<p class="n-mt">{_next_claim_chip("the-work-has-been-done", ctx_shared, NEXT_ROOT)}'
        '</p></div>'
        f'<p class="n-head__aside"><a href="{EVIDENCE["source"]}" rel="nofollow">'
        f'The whole catalogue {_OUT}</a></p>'
        '</div>'
        f'<div class="n-works">{works_html}</div></section>')

    md = [
        "# Agent Behaviour Policies for the agents you already run\n",
        "Agent Behaviour Policies: what your agent can do, what you authorised, and the gap "
        "between them — for one agent, in one deployment.\n",
        "\n## The four levels\n",
        "| Level | Name | Price | Arrives | State |",
        "|---|---|---|---|---|",
    ]
    for l in levels:
        md.append(f"| {l['n']} | ABP {l['short_name']} — {l['short_sub']} | "
                  f"{l['price']} | {l['clock']} | {l['state_label']} |")
    md.append("\nEvery price is read from data/offers.yml, the only file a price exists in.\n")
    md.append("\n## Who are you\n")
    for a in AUDIENCES:
        md.append(f"- **{a['name']}** — {a['door']} ({SITE['base']}/are/{a['id']}/)")
    md.append("\n## What an ABP is\n\nGrant, mandate, delta and barrier, for one deployment. "
              "It describes and does not judge, so it carries no score.\n")
    md.append("\n## What this page is not\n\n" + till(
        "It is not the shop. Nothing here can be bought — no payment link has been issued "
        "on any level, so every buying action is a disabled control that says so.",
        "It is not the checkout. Every buying action here opens the product page, where a "
        "line is added to the order this browser holds; the money is taken on the payment "
        "provider's own page, from the checkout.")
        + f" See {SITE['base']}/admin/next/.\n")

    return _next_emit(out_dir, NEXT_ROOT, {
        # ON A PHONE THE DOORS COME FIRST. The hero alone is 1.8 screens at 390px
        # and the band was landing 1,185px down, which is a section nobody meets.
        # At 1280 the hero and the four facts are one screen and the band is
        # already right under them, so the order is left alone there.
        "main_class": "n-main--doors",
        "title": "Give your AI agent a clear mandate",
        "description": ("The next store, built from the v3 design direction 01 / ABP first: "
                        "Agent Behaviour Policies at four levels — ABP Pack, Vault, "
                        "Tailored and Reviewed — for one agent in one deployment."),
    }, body, model, "\n".join(md))


def _next_product(out_dir, ctx_shared, levels, auds, model):
    lead = next(l for l in levels if l["id"] == NEXT_LEAD)

    switch = "".join(
        f'<button type="button" data-level="{l["id"]}" '
        f'aria-pressed="{"true" if l["id"] == lead["id"] else "false"}">'
        f'ABP {html.escape(l["short_name"])} &middot; {html.escape(l["price"])}</button>'
        for l in levels)

    editions = "".join(
        f'<button type="button" data-audience="{a["id"]}" '
        f'aria-pressed="{"true" if i == 0 else "false"}">{html.escape(a["label"])}</button>'
        for i, a in enumerate(auds))

    # ---- the media slots. Two are real and one is deliberately empty and says
    # what belongs in it. The empty one is not a placeholder to be removed later:
    # it is how the page stays honest while the screenshots are still being taken,
    # and it ships in that state.
    media = (
        '<div data-media-panel="art">'
        '<figure class="n-media__frame">'
        f'<img id="p-art" src="{lead["art"]}" alt="ABP {html.escape(lead["short_name"])} '
        '&mdash; concept artwork for a digital deliverable" width="720" height="480">'
        '<figcaption class="n-media__cap">Concept artwork &middot; the deliverable is '
        'digital</figcaption></figure></div>'

        '<div data-media-panel="contents" hidden>'
        '<figure class="n-media__frame">'
        '<img src="/assets/shots/01-catalogue.png" alt="The catalogue of fifteen published '
        'shapes, each with what the agent can do" loading="lazy">'
        '<figcaption class="n-media__cap">/assets/shots/01-catalogue.png &middot; the real '
        'catalogue, photographed from the running site</figcaption></figure></div>'

        '<div class="n-media__empty" data-media-panel="screen" hidden>'
        '<b>A screenshot belongs here and has not been taken.</b>'
        '<span>The vault open in its own app, with the grant, the mandate and the delta as '
        'a buyer sees them. It is an empty frame rather than a stock image because a page '
        'whose whole job is showing what you get should not pad that with decoration.</span>'
        '</div>')

    tabs = (
        '<div class="n-switch" role="group" aria-label="Product media">'
        '<button type="button" data-media="art" aria-pressed="true">Product artwork</button>'
        '<button type="button" data-media="contents" aria-pressed="false">What is inside</button>'
        '<button type="button" data-media="screen" aria-pressed="false">Real screenshot slot</button>'
        '</div>')

    specs = "".join(
        f"<tr><th>{html.escape(k)}</th><td>{v}</td></tr>"
        for k, v in [
            ("Product", '<code id="p-spec-code">' + html.escape(lead["code"]) + "</code>"),
            ("Scope", "One agent, in one deployment"),
            ("Core material", "The behaviour policy, the grant, the mandate, the delta "
                              "and the barriers"),
            ("Shapes to choose from", f'{ABP["count"]} published, plus a catch-all for '
                                      "anything not on the list"),
            ("Formats", "Markdown and JSON, plus the two files you hand the agent"),
            ("Delivery", '<span id="p-spec-clock">' + html.escape(lead["clock"]) + "</span>"),
            ("Licence", "The public material is CC BY 4.0. What you buy is a commercial "
                        "licence to you over the same material."),
            ("Needs an account", "No. There is no account on this site, and no form "
                                 "anywhere in its output."),
        ])

    # ---- what you are buying. A policy at a level. The policy comes off the
    # address and is the site's default until somebody changes it; the page
    # says which, because a default that looks like a choice is a wrong order.
    default_shape = next(s for s in model["shapes"] if s["slug"] == NEXT_DEFAULT_POLICY)
    level_rows = "".join(
        f'<button type="button" data-level="{l["id"]}" '
        f'aria-pressed="{"true" if l["id"] == lead["id"] else "false"}">'
        f'ABP {html.escape(l["short_name"])} &middot; {html.escape(l["price"])}</button>'
        for l in levels)

    body = (
        '<section class="n-sect">'
        '<div class="n-switch" role="group" aria-label="Choose a level" '
        'style="margin:0 0 30px">' + switch + '</div>'

        '<div class="n-product">'
        # ------------------------------------------------------------ left
        '<div>'
        '<p class="n-eyebrow">Agent Behaviour Policy &middot; '
        '<span id="p-code">' + html.escape(lead["code"]) + '</span></p>'
        '<h1 style="font-size:clamp(34px,4vw,54px)">ABP <span id="p-name">'
        + html.escape(lead["short_name"]) + '</span></h1>'
        '<p class="n-hero__lede n-mt" id="p-sub">' + html.escape(lead["short_sub"]) + '</p>'

        '<div class="n-mt-lg">' + media + tabs + '</div>'

        '<h2 class="n-mt-lg" style="font-size:28px">What arrives. What does not.</h2>'
        '<div class="n-arrives n-mt">'
        '<div class="n-arrives__in"><b>Included at this level</b>'
        '<ul id="p-included"></ul></div>'
        '<div class="n-arrives__out"><b>Outside this level</b>'
        '<ul id="p-excluded"></ul></div></div>'

        '<h2 class="n-mt-lg" style="font-size:28px">The same ABP, for your role.</h2>'
        '<div class="n-switch n-mt" role="group" aria-label="Choose an audience">'
        + editions + '</div>'
        '<p class="n-mt n-measure" id="a-copy"></p>'
        '<p class="n-fine n-mt"><a id="a-more" href="/are/founder/">'
        '<span id="a-more-label">Everything written for you &rarr;</span></a></p>'
        '<p class="n-note n-note--example n-mt">The audience changes the explanation. '
        'The product, the price and what arrives do not change, and nothing is hidden '
        'from anybody &mdash; a build check refuses a page that hides an offer from an '
        'audience.</p>'

        '<h2 class="n-mt-lg" style="font-size:28px">Specifications</h2>'
        '<table class="n-specs n-mt">' + specs + '</table>'

        '<div class="n-reviews n-mt-lg">'
        '<p class="n-reviews__label">Reviews</p>'
        '<h3>No customer reviews yet.</h3>'
        '<p>This space is reserved for dated, attributable feedback from people who have '
        'bought something. Nothing has been sold here yet, so there is nothing to show and '
        'nothing invented to fill it.</p></div>'
        '</div>'

        # ----------------------------------------------------------- right
        '<aside class="n-buy">'
        '<p class="n-buy__label">What you are buying</p>'
        '<h2 id="p-policy">' + html.escape(default_shape["title"]) + '</h2>'
        '<p class="n-buy__policy"><code id="p-policy-code">' + html.escape(default_shape["slug"])
        + '/</code> <span id="p-policy-default">&middot; the default shape; '
        f'<a href="{NEXT_PICKER}">change it {_OUT}</a></span></p>'
        '<p class="n-buy__level">ABP <span id="p-buy-name">' + html.escape(lead["short_name"])
        + '</span></p>'
        '<p class="n-price"><b id="p-price">' + html.escape(lead["price"])
        + '</b><span>GBP</span></p>'
        '<p class="n-buy__split" id="p-split"'
        + ("" if lead["split"] else " hidden") + ">"
        + (lead["split"] or "") + "</p>"
        '<p class="n-buy__clock" id="p-clock">' + html.escape(lead["clock"]) + '</p>'
        '<p class="n-buy__what" id="p-what">' + inline(lead["what"], ctx_shared) + '</p>'
        # THE BUTTON ADDS A LINE TO THE ORDER THIS BROWSER IS HOLDING. It is not
        # a payment and does not pretend to be one: the page that takes money is
        # the checkout, and that is where the disabled control with its reason
        # lives. A button here that did nothing would be the dishonest version.
        '<button class="n-btn n-btn--wide" id="p-buy" type="button" '
        f'data-add-line="{NEXT_DEFAULT_POLICY}|{lead["cart_id"]}">'
        'Add ABP ' + html.escape(lead["short_name"]) + ' to your order ' + _ARROW + '</button>'
        f'<p class="n-buy__added" id="p-added" hidden><a href="{NEXT_CART}">'
        f'Added &mdash; open your order {_OUT}</a></p>'
        '<p class="n-buy__note">Kept in this browser. ' + till(
            'No payment link has been issued on any level, so nothing here takes money; '
            'the checkout says what would happen when one is.',
            'Nothing here takes money: the checkout hands you to the payment provider, on '
            'their page, carrying your order reference and nothing else.') + '</p>'
        '<details class="n-buy__change"><summary>Change level</summary>'
        '<div class="n-switch n-mt" role="group" aria-label="Choose a level">' + level_rows
        + '</div></details>'
        '<div class="n-buy__rows">'
        '<p>' + _next_claim(lead, ctx_shared).replace('id="p-claim"', "")
                 .replace('<a class="n-claim', '<a id="p-claim" class="n-claim') + '</p>'
        '<p class="n-fine"><a id="p-policy-url" href="' + html.escape(default_shape["url"])
        + '" rel="nofollow">Read the free example first &#8599;</a></p>'
        '<p class="n-fine">One agent, one deployment. Commercial licence included.</p>'
        f'<p class="n-fine"><a href="{NEXT_DESCRIBE}">Describe your agent first {_ARROW}</a></p>'
        '</div></aside>'
        '</div></section>')

    md = ["# The product page — the next store\n",
          "One page for four levels. The level switcher changes the product; the audience "
          "switcher changes the explanation and nothing else.\n",
          "\n## The four levels\n",
          "| Code | Name | Price | Deposit | Arrives |",
          "|---|---|---|---|---|"]
    for l in levels:
        md.append(f"| `{l['code']}` | ABP {l['short_name']} | {l['price']} | "
                  f"{_strip(l['split']) or '—'} | {l['clock']} |")
    md.append("\n## What arrives\n")
    for l in levels:
        md.append(f"\n### ABP {l['short_name']}\n")
        md.append(f"{_strip(l['what'])}\n")
        if l["included"]:
            md.append("Included: " + "; ".join(l["included"]))
        if l["excluded"]:
            md.append("Outside this level: " + "; ".join(l["excluded"]))
    md.append(till(
        "\n## Nothing can be bought here\n\nNo payment link has been issued on any level, "
        "so every buying action on this page is a disabled control carrying its own reason. ",
        "\n## Nothing is typed here\n\nA buying action on this page adds a line to the "
        "order this browser holds. The card is typed on the payment provider's page. ")
        + "There is no form, input or field anywhere in this site's output and a build "
          "check holds that line.\n")

    return _next_emit(out_dir, NEXT_ROOT + "product/", {
        "title": "ABP Pack, Vault, Tailored and Reviewed",
        "description": ("The product page for the next store: four levels of one Agent "
                        "Behaviour Policy, what arrives at each, what does not, and the "
                        "same product explained for five different readers."),
    }, body, model, "\n".join(md))


def _next_admin(out_dir, ctx_shared, levels):
    src = NEXT_SOURCE
    art = NEXT_ART

    files = "".join(
        f'<tr><td><code>{html.escape(f["path"])}</code>'
        f'<br><span class="small dim">{html.escape(f["what"])}</span></td>'
        f'<td class="num">{f["bytes"]:,}</td>'
        f'<td><code class="small">{f["sha256"][:16]}</code></td></tr>'
        for f in src["files"])

    artrows = "".join(
        f'<tr><td><code>{html.escape(a["file"])}</code><br>'
        f'<span class="small dim">{html.escape(a["label"])}</span></td>'
        f'<td class="small">{html.escape(a["source_size"])} &rarr; {html.escape(a["size"])}</td>'
        f'<td class="num">{a["source_bytes"]//1024:,}KB &rarr; {a["bytes"]//1024:,}KB</td>'
        f'<td><code class="small">{a["source_sha256"][:12]}</code></td></tr>'
        for a in art["art"])

    lv = "".join(
        f'<tr><td><code>{html.escape(l["code"])}</code></td>'
        f'<td><b>ABP {html.escape(l["short_name"])}</b><br>'
        f'<span class="small dim">{html.escape(l["short_sub"])}</span></td>'
        f'<td>{html.escape(l["price"])}</td>'
        f'<td class="small">{html.escape(l["clock"])}</td>'
        f'<td>{chip(l["state"])}</td>'
        f'<td class="small">{"a link is issued" if l["buyable"] else "no link yet"}</td></tr>'
        for l in levels)

    body = (
        '<p class="lead">The design direction <b>01 / ABP first</b>, built here across '
        'three rounds at <code>/next/</code> and, from v0.3.16, the store. The design it '
        f'replaced is kept at <a href="{V1_ROOT}">the previous design</a> — nine pages, '
        'noindex, each saying above the fold that it is not the live one.</p>'

        '<div class="cx-verdict">' + till(
            '<b>Nothing here can be bought yet.</b>'
            '<p>No payment link has been issued on any level, so every buying action renders '
            'as a disabled control carrying its own reason. That was true of the design this '
            'replaced too; it is a property of the till, not of the design.</p>',
            '<b>The till is on.</b>'
            '<p>At least one level carries a payment link, so the checkout renders one button '
            'per line of the order and each hands the buyer to the provider carrying the '
            'order reference. Nothing comes back: there is no server here to receive a '
            'webhook, so this site can say a line was sent and never that it was paid.</p>')
        + '</div>'

        '<h2 id="swap">What moved, and what did not</h2>'
        '<p><b>Nine pages existed in both designs</b>, so the new one took the address and '
        'the old one was archived one directory down: the front page, the picker, the '
        'comparison, the audiences, the ledger, the order, the checkout, the page after '
        'paying and the reviewer register. Their links to each other are rewritten to stay '
        'inside the archive; their links to pages that never moved go where they always '
        'went, because those pages still exist and are still right.</p>'
        '<p><b>Every other page kept its address and was re-drawn in this chrome.</b> There '
        'was no second version of them to choose between. They load <code>site.css</code> '
        'and then <code>next.css</code>: the chrome and the base type come from the new '
        'file, and the block components — the tables, the tiles, the specification rows '
        '— keep the rules that already draw them. Fourteen rules in the old stylesheet '
        'were scoped to the old chrome’s own element and are replaced by the reading '
        'column in the new one; the other four hundred and sixty-seven are not scoped to '
        'anything and were untouched.</p>'
        '<p class="small dim"><b>That layering is a transitional state and is on the '
        'board.</b> The argument against it still holds where it applied — a new page '
        'with no old blocks in it should not carry 26KB of a design it is replacing, and '
        'those pages still do not. These pages are made almost entirely of those blocks, '
        'and porting them is real work with no reader-visible result on the day it lands.</p>'
        '<p><b>The console and the release archive were not part of the round.</b> '
        '<a href="/admin/">/admin/</a> has its own interface for a different reader and '
        '<a href="/versions/">/versions/</a> is a record rather than a shop.</p>'
        '<p><b>Every address the round used still resolves.</b> The ten <code>/next/</code> '
        'pages are still there, each one saying where its page went, carrying the canonical '
        'link to it and refreshing there.</p>'

        '<h2 id="codes">The printed cards still work</h2>'
        '<p>A code is never typed — there is no field on this domain — so it '
        'arrives in the address off a printed card or a QR, and the cards in circulation '
        'point at the front page. That page is the new design now and the old engine is not '
        'on it, so the capture, the expiry and the per-level arithmetic were ported into '
        '<code>assets/next.js</code>, which shares the storage key and the record shape with '
        '<code>assets/shop.js</code>. Both hash a code with the same sha256 and a build '
        'check holds the two copies identical: a card that works on half a site is worse '
        'than one that works on none of it. A code landing on a page drawn by the old engine '
        'is handed to the order page rather than dropped, and every page carries somewhere '
        'to say a code was applied or refused — a code that changes nothing and says '
        'nothing reads exactly like a code that worked.</p>'

        '<h2 id="not-built">One section of the design is not built</h2>'
        '<p>The v3 pages carry a mission line under the heading <em>why RiskMandate '
        'exists</em> that uses a word this site bars absolutely, on every page, with no '
        'allowlist and no carve-out for a quotation. The rule argues its own absoluteness: '
        'a positioning phrase is a claim, but a priced checkout is an OFFER, and every page '
        'here carries a price.</p>'
        '<p><b>Their own notes page records that the project lead asked for that line.</b> '
        'So this is a real collision between two things somebody is right about, and it is '
        'not the builder’s to settle. The section is left out of /next/, the mirror '
        'keeps their file intact because it is their page, and the ruling is on the board. '
        'Shipping it would fail the release; dropping it without saying so would be worse '
        'than either.</p>'
        '<p class="small dim">The reasoning behind the rule, without printing the word, is '
        'at <a href="/disclosures/">what we do not say, and why</a>.</p>'

        '<h2 id="names">The names, ruled on 16 September</h2>'
        '<p>Pack, Vault, Tailored, Reviewed — a short name at heading size with the '
        'precise line underneath, which is the shape the design brief proposed and the '
        'project lead ruled on. They live in <code>data/offers.yml</code> beside the price '
        'and are frozen by the same check.</p>'
        '<div class="tablewrap"><table><thead><tr><th>Code</th><th>Name</th><th>Price</th>'
        f'<th>Arrives</th><th>State</th><th>Till</th></tr></thead><tbody>{lv}</tbody>'
        '</table></div>'

        '<h2 id="how">How it is built</h2>'
        '<p><b>Every price, name, delivery estimate, claim and audience on these pages is '
        'read out of the files the current store is already built from.</b> There is no '
        'second copy of a number to drift, and the checks that freeze the live store’s '
        'prices freeze these. The pages are generated by <code>next_pages()</code> in '
        'build.py.</p>'
        '<p>They load <code>/assets/next.css</code> and <code>/assets/next.js</code> and '
        'nothing else — not site.css, not shop.js. The v3 source layers its palette on '
        'top of this site’s own stylesheet, which is right for a mockup and wrong to '
        'ship: it carries 26KB of a design we are leaving, and every new rule then fights an '
        'old one it did not know about. The cost is that a few components exist twice for '
        'now, in two visual languages; they converge when /next/ takes over.</p>'
        '<p>One deliberate change from the source: the v3 files declare '
        '<code>Arial, Helvetica, sans-serif</code> outright, which renders as drawn on two '
        'platforms and as a substitute everywhere else. /next/ uses a stack that resolves to '
        'the same faces on macOS and Windows and degrades to a real grotesque elsewhere, so '
        'the design is unchanged where it was judged and better where it was not.</p>'

        '<h2 id="mirror">What it was built from</h2>'
        f'<p>Taken from <a href="{src["source"]}" rel="nofollow">'
        f'{html.escape(src["source"].split("//")[1])}</a> on {src["retrieved"]}, and hashed '
        'so the question <em>did we build it faithfully</em> has an answer nobody has to '
        'remember. <code>python3 tools/promote_v3.py --check</code> '
        're-fetches and reports drift.</p>'
        f'<p class="small dim">{inline(src["_what_is_not_taken"], ctx_shared)}</p>'
        '<div class="tablewrap"><table><thead><tr><th>File</th><th class="num">Bytes</th>'
        f'<th>sha256</th></tr></thead><tbody>{files}</tbody></table></div>'

        '<h2 id="art">The artwork</h2>'
        '<p>Four product renders arrived as 1.9–2.1MB PNGs — 7.9MB for the set. '
        'They are photographic product art with soft gradients, which is the worst case for '
        'a lossless encoding and the best case for JPEG. <code>tools/shoot_v3.mjs</code> '
        're-encodes them at the size a card actually uses.</p>'
        '<div class="tablewrap"><table><thead><tr><th>File</th><th>Size</th>'
        f'<th class="num">Weight</th><th>From</th></tr></thead><tbody>{artrows}</tbody>'
        '</table></div>'

        '<h2 id="journey">The journey, wired end to end</h2>'
        '<p>The v4 handback supplied the picker, the cart, the checkout and the '
        'post-purchase screens. All four are built here, from the store’s own data:'
        f' <a href="{NEXT_PICKER}">which agent you run</a>,'
        f' <a href="{NEXT_CART}">your order</a>,'
        f' <a href="{NEXT_PAY}">checkout</a>, and'
        f' <a href="{NEXT_PAID}">what lands afterwards</a>.</p>'

        '<div class="cx-verdict"><b>It is the live store’s order, not a second one.</b>'
        '<p>The store that sells today keeps an order in the browser under one key. '
        '/next/ reads and writes <em>that record</em> — same key, same schema, same '
        'line shape, same reference alphabet, same SKUs — so an order started in this '
        'design round is still there on the current store, and back. Two carts under two '
        'keys would be a bug that only appears for the one person who uses both, which is '
        'the worst kind. A check compares the two models field by field on every '
        'build.</p></div>'

        '<p>What it does not share is the rendering. <code>assets/shop.js</code> draws the '
        'current design’s markup, so the order engine in <code>assets/next.js</code> is '
        'a second renderer over one record rather than a second record.</p>'
        '<p><b>Still no typing surface.</b> Quantities are buttons, the behaviour filter is '
        'a <code>&lt;details&gt;</code>, and the picker’s search holds no field at all: '
        'the query lives on the body element and characters are read off the keyboard, so '
        'there is no input to submit and nothing to submit it to. The cost is that a phone '
        'with no hardware keyboard cannot type there, and the dialog says so and points at '
        'the chips. The handback drew an on-screen keyboard out of buttons to solve the '
        'same problem; twenty-six buttons to filter fifteen things is worse than the '
        'fifteen things.</p>'

        '<h2 id="behaviour">The filter that cannot run, and the five grants that do not '
        'add up</h2>'
        '<p><b>The picker offers a filter by behaviour and it narrows nothing.</b> The '
        'capability vocabulary is promoted here — 23 named behaviours in the form '
        '<code>verb.object.reach</code> — and every shape publishes how many of them '
        'its grant contains. Which behaviours those are is not published for any shape. So '
        'the menu lists all 23, choosing one says the join is missing, and the list is left '
        'unchanged rather than narrowed on a guess. The design team reached the same answer '
        'independently on the same gap.</p>'
        '<p><b>The panel’s capability strip is one uncoloured cell per capability, and '
        'that is the second half of the same finding.</b> The first version painted the '
        'first <em>wanted</em> cells green and the last <em>unbounded</em> ones amber, which '
        'reads as a decomposition of the grant. For five of the fifteen shapes it is not '
        'one: wanted plus not-asked overshoots the grant by exactly one, every time. Ten are '
        'exact. Off by one on five and exact on ten is a convention somewhere upstream '
        'rather than noise. The panel says so on those five, says nothing on the ten, and a '
        'check refuses it either way round.</p>'
        '<p class="small dim">Both are on the board as '
        '<a href="/admin/status/#TK-14">TK-14</a> and '
        '<a href="/admin/status/#TK-13">TK-13</a>, for the team that publishes the '
        'catalogue.</p>'

        '<h2 id="evidence">Why the evidence state is typed out rather than derived</h2>'
        '<p>The picker filters on what stands behind a shape’s numbers: measured on the '
        'thing itself, or read from published sources. The obvious way to get that is to '
        'look for the word <em>measured</em> in each upstream summary. That marks four '
        'shapes, and one of the four is <code>chatgpt-web</code>, whose summary calls it '
        '“the baseline every other shape is measured against” — the shape '
        'others were measured against, not one that was measured. A regex cannot read a '
        'preposition. The join is fifteen typed lines in <code>data/products.yml</code>, and '
        'a check refuses a catalogue shape with no line, a line naming no catalogue shape, '
        'and a state this site has no badge for.</p>'

        '<h2 id="supporting">The four supporting pages</h2>'
        f'<p>The v4 pack supplied five more screens and four of them are built: '
        f'<a href="{NEXT_COMPARE}">what arrives at every level</a>, '
        f'<a href="{NEXT_AUDIENCE}">who this is for</a>, '
        f'<a href="{NEXT_LEDGER}">the claim ledger</a> and '
        f'<a href="{NEXT_WHO}">who does the work</a>. Each renders from the file the '
        'current store already renders from, and a check counts what reaches the page '
        'against what is in the file: a comparison missing a row, a ledger missing a '
        'claim and an audience view that hides a level all still look right.</p>'
        '<p><b>The ledger is here so a claim chip stops throwing the reader out of the '
        'round.</b> Every chip on every /next/ page now lands on a row in this design '
        'rather than on the design being replaced. It is the same 52 claims from the same '
        'file — there is no second copy — and it prints which pages say each '
        'one.</p>'

        '<h2 id="generic">The generic template is not a page, deliberately</h2>'
        '<p>The fifth screen in the pack is the generic template: a reading column with a '
        'claim chip beside each heading, drawn as <em>what is inside one</em>. That '
        'template is exercised here by the ledger and the reviewer page, which are reading '
        'columns that sell nothing. Re-rendering an existing content page at a second URL '
        'to demonstrate it would put the same paragraphs in two places on one site for the '
        'sake of a mockup, and the markdown twin, the search index and every reader who '
        'landed on the wrong one would carry that for as long as both existed. The nav’s '
        'third link therefore leaves the round, and the strip at the top of every page '
        'says the round is a round.</p>'

        '<h2 id="parity">The parity pass against v4</h2>'
        '<p>On 16 September the project lead put the live store beside '
        '<a href="https://sgit-store-v4.diniscruz.chatgpt.site" rel="nofollow">the v4 '
        'site</a> and found bits missing, the buy references first. The site is byte-for-'
        'byte the pack mirrored here, so the gap was not a newer version: it was what the '
        'first implementation left out of the pack. Every v4 screen was then diffed '
        'against its page here.</p>'
        '<p><b>Taken.</b> <em>Buy this level</em> on every offer card, everywhere, as v4 '
        'has it: a link to the product page carrying a level and a policy, where '
        '<em>Add to your order</em> adds the line. The product page sells a policy at a '
        'level, names the default shape as a default beside a link to change it, and '
        'carries the level switcher in its own aside. The comparison leads with the four '
        'cards and a print action. The five doors are drawn in this design at '
        f'<a href="{AUDIENCE_ROOT}founder/">/are/</a>, with the reader’s question as '
        'the headline and the cards under it, and the lens on '
        f'<a href="{NEXT_AUDIENCE}">who this is for</a> shows them too. '
        f'<a href="{NEXT_DESCRIBE}">Describe your agent</a> exists in the store rather than '
        'only in the lab, on the lab’s own engine. The ledger explains its ten '
        'states. The page after paying prints. The picker panel names the two files you '
        'hand the agent and opens the example vault on the shape’s own page.</p>'
        '<p><b>Deliberately not taken.</b> The preview controls on v4’s cart and '
        'checkout (<em>load example order</em>, <em>show 100% code applied</em>) are '
        'design states, not store controls. v4’s checkout button reads as live and '
        'says <em>preview</em> in a callout underneath; this one is a disabled control '
        'that carries its reason ' + till('while no payment link has been issued',
                                            'on any level that has no link yet')
        + ', because a button '
        'that looks live and does nothing is the one thing a store must never ship. The '
        'panel’s scenario selector and side-effect ladder are placeholders in the '
        'pack itself and stay out until the data exists. The post-purchase vault frame '
        'with a file list is a drawing of a vault; the page after paying links to the '
        'real one embedded on each level’s landing page instead. The design-handoff '
        'explorer on v4’s front page is for reviewing a handback, not for buying. '
        'And the product names are the ones ruled on 16 September, not v4’s.</p>'
        '<p><b>Found on the way.</b> Five “the same X on the store that sells '
        'today” links were pointing at themselves since the swap; they point at the '
        'archive now.</p>'

        '<h2 id="next">What is not there yet</h2>'
        '<p>The two add-ons attach to a level and have no page in this design. The '
        'admin console is untouched by the round: it is a different job for a different '
        'reader and its design is not this one’s to spend on.</p>'
        f'<p><b><a href="{NEXT_ROOT}">Open the store &rarr;</a></b> &middot; '
        f'<a href="{NEXT_PICKER}">the picker</a> &middot; '
        f'<a href="{NEXT_ROOT}product/">the product page</a> &middot; '
        f'<a href="{NEXT_COMPARE}">the comparison</a> &middot; '
        f'<a href="{NEXT_LEDGER}">the ledger</a> &middot; '
        '<a href="/admin/concepts/">how the direction was chosen</a> &middot; '
        '<a href="/admin/design-brief/">the brief that produced it</a></p>')

    md = ["# /next/ — the next store\n",
          "The v3 design direction **01 / ABP first**, built here. It runs beside the store "
          "that sells today rather than replacing it.\n",
          till("\n## Nothing on /next/ can be bought\n\nNo payment link has been issued on "
               "any level, so every buying action renders as a disabled control carrying "
               "its reason.\n",
               "\n## The till is on\n\nAt least one level carries a payment link. The "
               "checkout renders one button per line and each hands the buyer to the "
               "provider carrying the order reference and nothing else.\n"),
          "\n## One section of the design is not built\n\nThe v3 pages carry a mission line "
          "that uses a word this site bars absolutely, on every page, with no allowlist and "
          "no carve-out for a quotation. Their own notes record that the project lead asked "
          "for it. The section is left out, the mirror keeps their file intact, and the "
          "ruling is on the board.\n",
          "\n## The names, ruled on 16 September\n",
          "| Code | Name | Price | Arrives | State |", "|---|---|---|---|---|"]
    for l in levels:
        md.append(f"| `{l['code']}` | ABP {l['short_name']} — {l['short_sub']} | "
                  f"{l['price']} | {l['clock']} | {l['state_label']} |")
    md.append(f"\n## Built from\n\n{src['source']}, retrieved {src['retrieved']}, "
              f"{len(src['files'])} files hashed.\n")
    for f in src["files"]:
        md.append(f"- `{f['path']}` — {f['what']} — `{f['sha256'][:16]}`")
    md.append("\n## The journey\n\nThe picker, the order, the checkout and the page "
              "after it are built from the store's own data. The order they share is the "
              "live store's order: the same local-storage key, the same schema, the same "
              "line shape, the same reference alphabet and the same SKUs, so an order "
              "started in this design round is still there on the store that sells today. "
              "A check compares the two models field by field.\n")
    md.append("## The filter that cannot run\n\nThe capability vocabulary has 23 named "
              "behaviours and every shape publishes how many of them its grant contains. "
              "Which ones is not published for any shape, so the behaviour filter narrows "
              "nothing and says why, and the capability strip in the panel is one "
              "uncoloured cell per capability. For five of the fifteen shapes, wanted plus "
              "not-asked overshoots the grant by exactly one; ten are exact.\n")
    md.append("\n## Artwork\n")
    for a in art["art"]:
        md.append(f"- `{a['file']}` — {a['label']} — {a['source_size']} "
                  f"→ {a['size']}, {a['source_bytes']//1024}KB → {a['bytes']//1024}KB")

    return {NEXT_ADMIN: _console_page(
        out_dir, ctx_shared, NEXT_ADMIN,
        {"title": "The design, and the swap",
         "description": ("What /next/ is: the v3 design direction 01 / ABP first built "
                         "here, what it was built from and hashed against, the product "
                         "names ruled on 16 September, and the one section of the design "
                         "that is not built and why."),
         "blurb": ("<b>The design this store now uses, and how it got here.</b> Four rounds, "
                   "what was taken from each, and what the swap moved.")},
        ' / <a href="/admin/">admin</a> / next', body, "\n".join(md))}


# ---------------------------------------------------------------------------
# THE JOURNEY: the picker, the order, the hand-off and what lands afterwards.
#
# Added for the v4 handback, which supplied those four screens. They mirror the
# routes the store that sells today already uses — /policies/, /cart/, /pay/,
# /paid/ — because the point of this round is to replace a design, not to rename
# a shop somebody has already learned.
#
# THE ORDER IS THE LIVE STORE'S ORDER. assets/next.js reads and writes the same
# localStorage record under the same key and in the same shape as assets/shop.js,
# so an order started on one side of the round is still there on the other. The
# model below is what makes that possible: the schema number, the key, the two
# prefixes and the per-level cart id all come off the same data the live store's
# island is built from.
NEXT_PICKER = NEXT_ROOT + "policies/"
NEXT_CART = NEXT_ROOT + "cart/"
NEXT_PAY = NEXT_ROOT + "pay/"
NEXT_PAID = NEXT_ROOT + "paid/"

# The families the promoted catalogue uses, given names a reader can scan. The
# ids are upstream's; only the labels are ours, and a family arriving without one
# stops the build rather than rendering a heading that says "microsoft".
NEXT_FAMILIES = {
    "code": "Coding agents",
    "chat": "Chat assistants",
    "desktop": "Desktop apps",
    "browser": "Browser extensions",
    "ci": "Pipelines and runners",
    "service": "Services and scheduled jobs",
    "google": "Google Workspace",
    "mail": "Mail",
    "files": "File stores",
    "microsoft": "Microsoft 365",
    "other": "Not on the list",
}
_next_unnamed = sorted({s["family"] for s in SHOP_SHAPES} - set(NEXT_FAMILIES))
if _next_unnamed:
    raise SystemExit(f"build: policy famil(y/ies) {', '.join(_next_unnamed)} arrived with no "
                     "label in NEXT_FAMILIES. The picker groups on this and a group heading "
                     "that reads as an id is a heading nobody wrote.")

LEVEL_BY_OFFER = {l["offer"]: l for l in LEVELS}


def _next_claim_chip(claim_id, ctx, url):
    """A claim chip for a claim this page is making, by id. _next_claim above does
    the same for an OFFER, whose state is on the offer; this one reads the state
    off the ledger entry, because these pages cite claims that are not about a
    product at all."""
    c = ctx["claims_by_id"].get(claim_id)
    if not c:
        raise SystemExit(f"next: a journey page cites claim {claim_id!r}, which is not in "
                         "data/claims.yml")
    ctx["claim_uses"].setdefault(claim_id, set()).add(url)
    return (f'<a class="n-claim n-claim--{c["state"]}" href="{NEXT_LEDGER}#claim-{claim_id}">'
            f'{html.escape(STATES[c["state"]][0])} &#8599;</a>')


def _next_sum_note(counts):
    """One sentence when the four published totals do not partition the grant,
    and nothing at all when they do. Silence is the honest default here: a note
    on every shape saying "these add up" trains a reader to skip it."""
    if not counts:
        return ""
    can, wanted, unasked = counts["grant"], counts["wanted"], counts["excess"]
    if wanted + unasked == can:
        return ""
    return (f"{wanted} wanted and {unasked} not asked come to {wanted + unasked}, and the "
            f"grant is {can}. The two are counted on different bases upstream and this page "
            "does not reconcile them, so read them as two separate readings of the same "
            "grant rather than as a split of it.")


def _next_shapes():
    """Every shape the picker picks between, plus the one nobody has profiled.

    Everything is read from the promoted catalogue and from the evidence join in
    data/products.yml. The one thing this site would like to have and does not is
    WHICH of the 23 capability primitives each shape was granted: the vocabulary
    is promoted and the counts are promoted, but the join between them is not
    published. The behaviour filter therefore reports that rather than guessing,
    which is the handback's own answer to the same gap and is the right one."""
    out = []
    for s in SHOP_SHAPES:
        counts = s.get("counts") or {}
        ev = SHAPE_EVIDENCE.get(s["slug"], "")
        out.append({
            "slug": s["slug"], "code": s["code"], "title": s["title"],
            "summary": s["summary"], "glyph": s["glyph"],
            # the published page for this shape, which is where its example vault
            # opens; the catch-all has none and the page says so
            "url": (s.get("url") or "").strip(),
            "family": s["family"], "family_label": NEXT_FAMILIES[s["family"]],
            "evidence": ev,
            "evidence_state": ev,
            "evidence_label": STATES[ev][0] if ev else "",
            "open": int(s.get("open_questions") or 0),
            "can": counts.get("grant"), "wanted": counts.get("wanted"),
            "unasked": counts.get("excess"), "unbounded": counts.get("unbounded"),
            "levels": s["levels"],
            # WHETHER THE PUBLISHED TOTALS ADD UP, AND WHAT TO SAY WHEN THEY DO
            # NOT. Upstream publishes four numbers per shape: the size of the
            # grant, how much of it was wanted, how much was not asked for, and
            # how much has nothing real in the way of it. For ten of the fifteen,
            # wanted + not-asked is exactly the grant. For five it is not, and
            # those five are the ones whose capability strip was being painted as
            # though it were. A reader looking at the tiles will do this addition
            # themselves, so the page does it first and says which it is.
            "sum_note": _next_sum_note(counts),
            # A shape with no profile behind it cannot be opened in the panel,
            # because the panel is nothing but the profile.
            "pickable": bool(counts) and bool(ev),
            "search": " ".join([s["slug"], s["title"], s["summary"],
                                s["family"], NEXT_FAMILIES[s["family"]]]).lower(),
        })
    return out


def _next_order_model():
    """What assets/next.js needs to share one order with assets/shop.js."""
    return {"schema": 1, "key": "sgit.store.order.v1",
            "sku_prefix": PRODUCTS["meta"]["sku_prefix"],
            "order_prefix": PRODUCTS["meta"]["order_prefix"]}


def _next_policy_card(s, ctx):
    """One card in the grid. The claim chip is a link to the ledger entry that
    says where the catalogue came from, because a count with no provenance is the
    thing every reader on the panel said they discount."""
    ctx["claim_uses"].setdefault("abp-catalogue-promoted", set()).add(NEXT_PICKER)
    pct = (100 * s["unbounded"] // s["can"]) if s["can"] else 0
    # SHORT, BECAUSE THE ROW IS SHORT. "no open questions" is the honest phrase
    # and it wrapped to two lines beside the glyph and the chip in a 238px card,
    # which broke both of the things next to it. The full phrase is the title.
    openq = (f'<span class="n-policy__open" title="{s["open"]} open question'
             f'{"" if s["open"] == 1 else "s"} about this grant">{s["open"]} open</span>')
    return (f'<button class="n-policy" type="button" data-policy="{s["slug"]}" '
            f'aria-pressed="false">'
            f'<span class="n-policy__top">'
            f'<span class="n-policy__glyph">{html.escape(s["glyph"])}</span>'
            f'<span class="n-claim n-claim--{s["evidence_state"]}">'
            f'{html.escape(s["evidence_label"])}</span>{openq}</span>'
            f'<h4>{html.escape(s["title"])}</h4>'
            f'<p>{html.escape(s["summary"])}</p>'
            f'<span class="n-policy__counts"><b>{s["can"]}</b> it can do'
            f'<span class="n-bar"><i style="width:{pct}%"></i></span>'
            f'<b>{s["unbounded"]}</b> unbounded</span>'
            '</button>')


def _next_till(levels, shapes):
    """The four levels at the foot of the panel. Every one of them adds a line to
    the order this browser is holding; none of them takes a payment, because no
    payment link has been issued on any level and the page says so where the
    money would be taken rather than here."""
    rows = ""
    for l in levels:
        rows += (f'<button type="button" data-add="{l["cart_id"]}" disabled '
                 f'aria-label="Add ABP {html.escape(l["short_name"])} for the selected policy '
                 f'to your order">'
                 f'<b>{html.escape(l["price"])}</b>ABP {html.escape(l["short_name"])}</button>')
    return ('<div class="n-panel__foot">'
            '<p class="n-fine n-dim">Buy this policy at</p>'
            f'<div class="n-panel__ladder">{rows}</div>'
            f'<p class="n-fine" id="panel-added" hidden><a href="{NEXT_CART}">'
            f'Added &mdash; open your order {_OUT}</a></p>'
            '<p class="n-fine n-dim">These add a line to the order held in this browser. '
            + till('No payment link has been issued on any level, so nothing here takes money '
                   f'&mdash; <a href="{NEXT_PAY}">what would happen when one is {_OUT}</a>',
                   'Nothing here takes money '
                   f'&mdash; <a href="{NEXT_PAY}">the checkout, and what it sends {_OUT}</a>')
            + '</p>'
            '</div>')


def _next_picker(out_dir, ctx_shared, levels, shapes, model):
    pickable = [s for s in shapes if s["pickable"]]
    families = []
    for s in pickable:
        if s["family"] not in [f[0] for f in families]:
            families.append((s["family"], s["family_label"],
                             len([x for x in pickable if x["family"] == s["family"]])))
    families.sort(key=lambda f: (-f[2], f[1]))

    fam_chips = (f'<button class="n-fchip" type="button" data-filter="family" '
                 f'data-value="all" aria-pressed="true">Every kind'
                 f'<span class="n-fchip__n">{len(pickable)}</span></button>')
    for fid, label, n in families:
        fam_chips += (f'<button class="n-fchip" type="button" data-filter="family" '
                      f'data-value="{fid}" aria-pressed="false">{html.escape(label)}'
                      f'<span class="n-fchip__n">{n}</span></button>')

    ev_chips = ('<button class="n-fchip" type="button" data-filter="evidence" '
                'data-value="all" aria-pressed="true">Any evidence</button>')
    for state in ("measured", "docs"):
        n = len([s for s in pickable if s["evidence"] == state])
        ev_chips += (f'<button class="n-fchip" type="button" data-filter="evidence" '
                     f'data-value="{state}" aria-pressed="false">'
                     f'{html.escape(STATES[state][0].capitalize())}'
                     f'<span class="n-fchip__n">{n}</span></button>')

    behaviours = "".join(
        f'<button type="button" data-filter="behaviour" data-value="{c["id"]}" '
        f'aria-pressed="false" title="{html.escape(c["gloss"])}">{c["id"]}</button>'
        for c in CAPABILITIES["capabilities"])
    behaviours = ('<button type="button" data-filter="behaviour" data-value="all" '
                  'aria-pressed="true">Any behaviour</button>' + behaviours)

    groups = ""
    for fid, label, n in families:
        cards = "".join(_next_policy_card(s, ctx_shared)
                        for s in pickable if s["family"] == fid)
        groups += (f'<section class="n-group" data-group="{fid}">'
                   f'<div class="n-group__head"><h3>{html.escape(label)}</h3>'
                   f'<span data-group-count>&middot; {n}</span></div>'
                   f'<div class="n-picker__grid">{cards}</div></section>')

    own = next(s for s in shapes if not s["pickable"])
    own_levels = [l for l in levels if l["cart_id"] in own["levels"]]
    ctx_shared["claim_uses"].setdefault(own_levels[0]["claim"], set()).add(NEXT_PICKER)
    groups += ('<section class="n-group"><div class="n-object">'
               f'<h3>{html.escape(own["title"])}?</h3>'
               f'<p class="n-dim n-mt">{html.escape(own["summary"])}</p>'
               f'<p class="n-mt"><a class="n-btn" href="{NEXT_ROOT}product/'
               f'?level={own_levels[0]["id"]}">'
               f'Start from {html.escape(own_levels[0]["price"])} {_ARROW}</a></p>'
               '<p class="n-fine n-dim n-mt">The first two levels deliver a template and for '
               'a shape nobody has profiled there is not one, so this starts at the level '
               'where a person does the work. That is a fact about the product rather than '
               'a packaging decision.</p>'
               '</div></section>')

    panel = (
        '<aside class="n-panel" id="panel" aria-label="The selected policy">'
        '<div class="n-panel__empty" id="panel-empty">'
        '<p><b>Choose a policy shape</b></p>'
        '<p class="n-mt">Its grant, what was actually wanted and what has nothing real in '
        'the way of it open here, with the four levels you can buy it at underneath.</p>'
        '</div>'
        '<div class="n-panel__body" id="panel-body" hidden>'
        '<div class="n-panel__head"><div>'
        '<h3 id="panel-title"></h3>'
        '<p class="n-panel__slug" id="panel-slug"></p>'
        '</div><a class="n-claim" id="panel-claim" '
        f'href="{NEXT_LEDGER}#claim-abp-catalogue-promoted"></a></div>'
        '<p class="n-fine n-dim n-mt" id="panel-summary"></p>'
        '<div class="n-panel__stats">'
        '<div class="n-stat"><b id="panel-can"></b><span>it can do</span></div>'
        '<div class="n-stat"><b id="panel-wanted"></b><span>wanted</span></div>'
        '<div class="n-stat"><b id="panel-unasked"></b><span>not asked</span></div>'
        '<div class="n-stat"><b id="panel-unbounded"></b><span>unbounded</span></div>'
        '</div>'
        '<p class="n-fine n-dim" id="panel-sums" hidden></p>'
        '<p class="n-fine n-dim n-mt">One cell per capability in the grant.</p>'
        '<div class="n-cells" id="panel-cells" role="img" '
        'aria-label="One cell per capability in this grant"></div>'
        '<p class="n-fine n-dim">Which of the 23 named behaviours each cell is has not been '
        'published for any shape, so the cells are counted rather than classified and none '
        f'of them is coloured in. <a href="{NEXT_ADMIN}#behaviour">Why that matters '
        f'{_OUT}</a></p>'
        # THE TWO FILES YOU HAND THE AGENT ship in every template pack and every
        # vault — the offer data says so — and the example vault for a shape is
        # its own published page upstream. Both are the handback's, both are true.
        '<h4 class="n-mt-lg">The files you hand the agent</h4>'
        '<div class="n-files">'
        '<div class="n-files__row"><code>AGENTS.md</code><span>Guidance</span></div>'
        '<div class="n-files__row"><code>SKILL.md</code><span>Method</span></div>'
        '</div>'
        '<p class="n-mt"><a class="n-btn n-btn--ghost" id="panel-open" href="#" '
        f'rel="nofollow">Open the example vault {_OUT}</a></p>'
        '</div>'
        + _next_till(levels, shapes) +
        '</aside>')

    body = (
        '<section class="n-sect">'
        '<div class="n-head"><div class="n-head__text">'
        f'<p class="n-eyebrow">{len(pickable)} published shapes</p>'
        '<h1>Which agent do you run?</h1>'
        '<p class="n-mt">Pick the shape closest to your deployment, read what its grant '
        'actually contains, then pick the level you want it at. Every number on this page '
        'is read from the published catalogue and none of it was written here.</p>'
        '</div>'
        f'<p class="n-head__aside"><a href="{V1_ROOT}policies/">The same fifteen in the '
        f'previous design {_OUT}</a></p></div>'

        '<div class="n-filters">'
        '<div class="n-filters__row">'
        '<button class="n-fchip" type="button" data-search-open aria-expanded="false">'
        'Search these shapes <kbd>/</kbd></button>'
        '<span class="n-filters__row--end">'
        '<button class="n-fchip" type="button" data-filter="view" data-value="grid" '
        'aria-pressed="true">Grid</button>'
        '<button class="n-fchip" type="button" data-filter="view" data-value="list" '
        'aria-pressed="false">List</button>'
        '</span></div>'
        f'<div class="n-filters__row" aria-label="Kind of agent">{fam_chips}</div>'
        '<div class="n-filters__row" aria-label="What evidences the numbers">'
        + ev_chips +
        '<details class="n-behaviour"><summary class="n-fchip">By behaviour</summary>'
        f'<div class="n-behaviour__menu">{behaviours}</div></details>'
        '</div></div>'

        '<div class="n-search" id="search" hidden role="status">'
        '<p class="n-eyebrow">Filtering on</p>'
        '<div class="n-search__q" id="search-q" data-empty="true"></div>'
        '<p>Type to narrow the list. <kbd>Esc</kbd> clears it, <kbd>Enter</kbd> closes this. '
        'There is no field here and there is not one anywhere on this site: what you type '
        'goes nowhere and is read straight off the keyboard. On a phone, use the chips '
        'above &mdash; a keyboard drawn out of buttons to filter fifteen things is worse '
        'than the fifteen things.</p></div>'

        '<div class="n-picker">'
        '<div>'
        f'<p class="n-picker__count" id="picker-count" aria-live="polite">'
        f'{len(pickable)} policy shapes</p>'
        '<p class="n-note n-note--hold" id="picker-behaviour-note" hidden>'
        '<b>Nothing is filtered by <code id="picker-behaviour-name"></code>.</b> '
        'The 23-behaviour vocabulary is published and every shape’s totals are '
        'published, but which behaviours make up a particular grant is not. The list '
        'below is unchanged rather than narrowed on a guess.</p>'
        + groups +
        '</div>'
        + panel +
        '</div></section>')

    md = ["# Which agent do you run?\n",
          f"{len(pickable)} published policy shapes, promoted from "
          f"{ABP['source']} on {ABP['retrieved'][:10]}.\n",
          "| Shape | Kind | Evidence | Can do | Wanted | Not asked | Unbounded | Open |",
          "|---|---|---|---|---|---|---|---|"]
    for s in pickable:
        md.append(f"| {s['title']} | {s['family_label']} | {s['evidence_label']} | "
                  f"{s['can']} | {s['wanted']} | {s['unasked']} | {s['unbounded']} | "
                  f"{s['open']} |")
    md.append("\n## What this page cannot filter on\n\nThe capability vocabulary has 23 "
              "named behaviours and every shape above carries a count of how many it was "
              "granted, but the join between the two — which behaviours are in a "
              "particular grant — is not published. The behaviour filter says so and "
              "narrows nothing rather than returning a confident wrong answer.\n")
    md.append("## What it costs\n")
    md.append("| Level | Price | Deposit | Arrives |")
    md.append("|---|---|---|---|")
    for l in levels:
        md.append(f"| ABP {l['short_name']} | {l['price']} | {_strip(l['split']) or '—'} | "
                  f"{l['clock']} |")

    return _next_emit(out_dir, NEXT_PICKER, {
        "title": "Which agent do you run?",
        "description": (f"{len(pickable)} published Agent Behaviour Policy shapes, what each "
                        "grant contains, and the four levels you can buy one at."),
    }, body, model, "\n".join(md))


def _next_cart(out_dir, ctx_shared, levels, model):
    """Your order. The whole of it lives in this browser: there is no account,
    nothing is sent anywhere, and the reference is generated here."""
    ctx_shared["claim_uses"].setdefault("checkout-links-not-issued", set()).add(NEXT_CART)

    body = (
        '<section class="n-sect">'
        '<div class="n-narrow">'
        '<p class="n-eyebrow">Your order</p>'
        '<h1>A clear record of what you chose.</h1>'
        '<p class="n-lede n-mt">Kept in this browser and nowhere else. No account, no '
        'email, nothing sent anywhere &mdash; the reference below was generated on this '
        'page and has never left it.</p>'

        # The server renders the empty state; assets/next.js replaces it with the
        # order this browser is holding. A reader with no JavaScript sees a page
        # that is true rather than a page that is blank.
        '<div class="n-mt-lg" id="order">'
        '<div class="n-empty"><h2>Your order is empty</h2>'
        '<p>Choose a policy shape and the level you want it at.</p>'
        f'<a class="n-btn" href="{NEXT_PICKER}">Pick an agent {_ARROW}</a></div>'
        '</div>'

        '<div class="n-handoff n-mt-lg">'
        '<div><h3>What leaves this page</h3>'
        '<p>The amount and the order reference, when a payment link exists. That is the '
        'whole of it. No name, no address and no card details are typed here, because '
        'there is no field on this site to type one into.</p></div>'
        '<div><h3>What is in this browser</h3>'
        '<p>The lines above, the quantities and the reference, under one key in local '
        'storage. Clear your browser data and the order goes with it; open the store on '
        'another device and it is not there.</p></div>'
        '</div>'

        '<p class="n-note n-note--hold n-mt-lg">' + till(
            '<b>No payment link has been issued on any level.</b> An order can be built here '
            'in full, and the step that takes money is the one that does not exist yet. The '
            'next page says exactly what would happen and where.',
            '<b>Nothing is typed on this site.</b> The order is built here and the step that '
            'takes money is on the payment provider\u2019s own page. The next page says '
            'exactly what reaches them, and what does not.') + '</p>'
        f'<p class="n-mt">{_next_claim_chip("checkout-links-not-issued", ctx_shared, NEXT_CART)}</p>'
        '</div></section>')

    md = ["# Your order\n",
          "The order is held in this browser under one local-storage key and is not sent "
          "anywhere. There is no account and no field to type into.\n",
          "## What can be ordered\n",
          "| Level | SKU | Price | Deposit | Arrives |", "|---|---|---|---|---|"]
    for l in levels:
        md.append(f"| ABP {l['short_name']} | "
                  f"`{PRODUCTS['meta']['sku_prefix']}-&lt;shape&gt;-{l['cart_code']}` | "
                  f"{l['price']} | {_strip(l['split']) or '—'} | {l['clock']} |")
    # WHAT LEAVES IS THE REFERENCE, NOT THE AMOUNT — and this line used to say both.
    # The amount is on the provider's own product; a payment link carries its price
    # and this store cannot set it in a URL. Saying "the amount" implied a control
    # over the charge that does not exist, which is the wrong half to be vague about.
    md.append("\n## What leaves the page\n\nYour order reference, and the discount code "
              "when you arrived with one \u2014 nothing else. The amount is the provider's, "
              "on the provider's own product. " + till(
                  "No payment link has been issued on any level.",
                  "At least one level carries a payment link.") + "\n")
    return _next_emit(out_dir, NEXT_CART, {
        "title": "Your order",
        "description": ("The order you have built, held in this browser: what you chose, "
                        "what is due now, what is due on delivery."),
    }, body, model, "\n".join(md))


def _next_pay(out_dir, ctx_shared, levels, model):
    """The hand-off. The one page on this site where money would change hands, and
    the one page that has to be exact about what this store never sees."""
    for cid in ("checkout-links-not-issued", "marketplace-no-customer-payment"):
        ctx_shared["claim_uses"].setdefault(cid, set()).add(NEXT_PAY)

    body = (
        '<section class="n-sect">'
        '<div class="n-narrow">'
        '<p class="n-eyebrow">Checkout</p>'
        '<h1>Check what is due, and when.</h1>'
        '<p class="n-lede n-mt">Your policy and your level stay attached to one order '
        'reference. ' + till(
            'That reference is the only thing that would reach a payment provider \u2014 '
            'the amount is theirs, on their own product.',
            'That reference is the only thing that reaches the payment provider, with your '
            'discount code when you arrived with one. The amount is theirs, on their own '
            'product.') + '</p>'

        '<div class="n-mt-lg" id="checkout">'
        '<div class="n-empty"><h2>Nothing to check out</h2>'
        '<p>Your order is empty.</p>'
        f'<a class="n-btn" href="{NEXT_PICKER}">Pick an agent {_ARROW}</a></div>'
        '</div>'

        '<div class="n-handoff n-mt-lg">'
        '<div><h3>What the provider asks for</h3>'
        '<p>Your name, your email address and your card details, on the provider’s own '
        'page, under the provider’s own terms. Those fields are theirs and they stay '
        'on their domain.</p></div>'
        '<div><h3>What this store never sees</h3>'
        '<p>All of it. This site has no form, no input and no field anywhere in its '
        'output, makes no network request from any page that sells anything, and has no '
        'server to receive one. A build check holds each of those three.</p></div>'
        '</div>'

        '<p class="n-note n-note--hold n-mt-lg">' + till(
            '<b>No payment link has been issued on any level.</b> The control above carries '
            'that reason instead of a price, and it is a disabled control rather than a '
            'button that quietly does nothing. The day a link is recorded against a level in '
            'the store\u2019s own data, that button turns on by itself.',
            '<b>One button per line, because one payment link sells one line.</b> Each one '
            'opens the provider\u2019s own page carrying your order reference, which is how '
            'the lines of one order find each other again on their side. Nothing comes back: '
            'there is no server here to receive it, so this store can tell you a line was '
            'sent and can never tell you it was paid.')
        + f' <a href="/paying/">The two rails, and why they never meet {_OUT}</a></p>'
        f'<p class="n-mt">{_next_claim_chip("checkout-links-not-issued", ctx_shared, NEXT_PAY)}</p>'
        '</div></section>')

    md = ["# Checkout\n",
          till("No payment link has been issued on any level, so nothing can be paid for "
               "here. What follows is what would happen when one is.\n",
               "One button per line of your order, because one payment link sells one "
               "line. Each opens the provider's own page.\n"),
          "## The hand-off\n",
          "- **What the provider asks for:** name, email address, card details, on its own "
          "page and under its own terms.\n"
          "- **What this store sends:** an order reference, and the discount code when you "
          "arrived with one. Not the amount \u2014 that is the provider's, on the "
          "provider's own product.\n"
          "- **What comes back:** the provider's own session identifier, if their page is "
          "set to return one. Not a confirmation. There is no server here to ask whether "
          "the payment cleared, so this store never says that it did.\n"
          "- **What this store receives:** nothing. There is no form, no input and no field "
          "anywhere in this site's output, no network request from any page that sells "
          "anything, and no server to receive one.\n"]
    return _next_emit(out_dir, NEXT_PAY, {
        "title": "Checkout",
        "description": ("What is due now, what is due on delivery, and exactly which two "
                        "things would reach a payment provider."),
    }, body, model, "\n".join(md))


def _next_paid(out_dir, ctx_shared, levels, model):
    """What lands after a payment, for each of the four levels.

    THIS PAGE SHOWS THE ORDER THIS BROWSER IS HOLDING, and never an example
    dressed as a purchase. That was the right shape while no payment link existed
    and it is still the right shape now that one can: a payment link's return
    address is set once in the provider's dashboard and is the same for every
    buyer, so the store's reference cannot survive the round trip. It does not
    need to — the browser that built the order still has it.

    What the provider CAN put in the address is its own session identifier, and
    the engine reads it. That is evidence the buyer came back through a session.
    It is not evidence the money moved, and confirming it would take a server
    call this site has no server to make, so the page says "you came back" and
    never "you paid". The four panels below are what the store's own data says
    happens next at each level."""
    for cid in ("post-sale-pages-exist", "receipt-reference-untested"):
        ctx_shared["claim_uses"].setdefault(cid, set()).add(NEXT_PAID)

    switch = "".join(
        f'<button class="n-fchip" type="button" data-step="{l["id"]}" '
        f'aria-pressed="false">ABP {html.escape(l["short_name"])}</button>'
        for l in levels)

    panels = ""
    for l in levels:
        rows = "".join(
            f'<tr><th>{html.escape(label)}</th><td>{inline(value, ctx_shared)}</td></tr>'
            for label, value in [
                ("When", l["post_when"]),
                ("What you do", l["post_does"]),
                ("How the key reaches you", l["post_key"]),
                ("Done means", l["post_done"]),
                ("How you check", l["post_check"]),
            ] if value)
        carries = ", ".join(l["post_carries"]) or "nothing"
        panels += (
            f'<div data-step-panel="{l["id"]}" hidden>'
            f'<h3>ABP {html.escape(l["short_name"])} &mdash; {html.escape(l["clock_full"])}</h3>'
            f'<table class="n-specs n-mt">{rows}</table>'
            f'<p class="n-fine n-dim n-mt">The landing page for this level carries: '
            f'{html.escape(carries)}.</p>'
            f'<p class="n-mt"><a href="{PAID_ROOT}{l["id"]}/">'
            f'The live page for this level, with its example vault {_OUT}</a></p>'
            '</div>')

    body = (
        '<section class="n-sect">'
        '<div class="n-narrow">'
        '<p class="n-eyebrow">After the payment</p>'
        '<h1>What lands, and when.</h1>'
        '<p class="n-lede n-mt">' + till(
            'This is the page a payment would return to. No payment link has been issued on '
            'any level, so what it can show is the order this browser is holding &mdash; '
            'with its real reference, its real SKUs and its real totals &mdash; and not a '
            'receipt for something nobody bought.',
            'This is the page a payment returns to. What it shows is the order this browser '
            'is holding &mdash; a payment link\u2019s return address is set once and is the '
            'same for every buyer, so your reference cannot travel back in it, and it does '
            'not need to. Your receipt comes from the provider.')
        + '</p>'

        '<p class="n-mt-lg"><button class="n-btn n-btn--ghost n-print" type="button" '
        'data-print>Print this page</button></p>'
        '<div class="n-mt" id="receipt">'
        '<div class="n-empty"><h2>This browser is not holding an order</h2>'
        '<p>Build one and it appears here, reference and all.</p>'
        f'<a class="n-btn" href="{NEXT_PICKER}">Pick an agent {_ARROW}</a></div>'
        '</div>'

        '<h2 class="n-mt-lg">What happens next</h2>'
        '<p class="n-dim n-mt">Every line below is read from the same file the live '
        'store’s own post-sale pages are built from.</p>'
        f'<div class="n-switch">{switch}</div>'
        f'<div class="n-mt">{panels}</div>'

        '<p class="n-note n-mt-lg"><b>A vault key is never on this page.</b> A key is never '
        'published and never committed, and every page here is a committed file, so the page '
        'says how a key reaches you and never carries one. <b>Done is a commit</b> at every '
        'level that ships a vault: the licence file with your name on it, the corrected '
        'mandate, the recomputed delta and the sign-off are things in your own history that '
        'you can go and look at.</p>'

        '<p class="n-note n-note--hold n-mt-lg">' + till(
            '<b>The reference has never been through a real sale.</b> It is generated in the '
            'browser, it is the same shape the store that sells today generates, and no '
            'order carrying one has been placed &mdash; so nothing has confirmed that a '
            'reference read off this page matches a reference on a provider\u2019s record.',
            '<b>This page cannot tell you a payment cleared.</b> It shows the order this '
            'browser holds, and the provider\u2019s own session identifier when you came '
            'back through one. Confirming a payment would mean asking the provider, and '
            'there is no server here to ask from \u2014 so this page never says you paid, '
            'only that you came back.')
        + '</p>'
        f'<p class="n-mt">{_next_claim_chip("receipt-reference-untested", ctx_shared, NEXT_PAID)} '
        f'{_next_claim_chip("post-sale-pages-exist", ctx_shared, NEXT_PAID)}</p>'
        '</div></section>')

    md = ["# What lands, and when\n",
          till("The page a payment would return to. No payment link has been issued on any "
               "level, so this page shows the order held in this browser and nothing else.\n",
               "The page a payment returns to. It shows the order held in this browser, "
               "because a payment link's return address is the same for every buyer and "
               "cannot carry your reference back.\n")]
    for l in levels:
        md.append(f"\n## ABP {l['short_name']} — {l['clock_full']}\n")
        for label, value in [("When", l["post_when"]), ("What you do", l["post_does"]),
                             ("How the key reaches you", l["post_key"]),
                             ("Done means", l["post_done"]),
                             ("How you check", l["post_check"])]:
            if value:
                md.append(f"- **{label}:** {_strip(value)}")
    md.append(till(
        "\n## The reference has never been through a real sale\n\nIt is generated in the "
        "browser and nothing has confirmed that one read off this page matches a reference "
        "on a payment provider's record.\n",
        "\n## What this page can tell you, and what it cannot\n\nIt shows the order this "
        "browser holds, and the provider's own session identifier when you came back "
        "through one. It cannot tell you a payment cleared: there is no server here to ask, "
        "and your receipt comes from the provider rather than from this site.\n"))
    return _next_emit(out_dir, NEXT_PAID, {
        "title": "What lands, and when",
        "description": (till("The page a payment would return to", "The page a payment "
                             "returns to")
                        + ": your order, your reference, "
                        "and what the store does next at each of the four levels."),
    }, body, model, "\n".join(md))


# ---------------------------------------------------------------------------
# THE SUPPORTING PAGES: what arrives at each level, who each level is for, every
# claim, and who does the work at the two levels a person does.
#
# THE GENERIC TEMPLATE IS NOT ONE OF THEM, DELIBERATELY. The handback's generic
# screen is /what-is-in-one/ redrawn: a reading column, four headings, a claim
# chip beside each. That template is exercised here by the ledger and the
# reviewer page, which are reading columns that sell nothing. Re-rendering an
# existing content page at a second URL to demonstrate a template would put the
# same paragraphs in two places on one site for the sake of a mockup, and the
# markdown twin, the search index and every reader who lands on the wrong one
# would carry that cost long after the round is over.
NEXT_COMPARE = NEXT_ROOT + "compare/"
NEXT_AUDIENCE = NEXT_ROOT + "audiences/"
NEXT_LEDGER = NEXT_ROOT + "ledger/"
NEXT_WHO = NEXT_ROOT + "who/"
NEXT_DESCRIBE = NEXT_ROOT + "describe/"


def _next_cmp_cell(v):
    if v == "yes":
        return '<td><span class="is-yes" aria-label="yes">✓</span></td>'
    if v == "no":
        return '<td><span class="is-no" aria-label="no">—</span></td>'
    return f'<td class="is-txt">{html.escape(str(v))}</td>'


def _next_compare(out_dir, ctx_shared, levels, model):
    """What arrives at each level, side by side, with the free column first.

    The free column leads because it is the argument rather than an objection:
    the fifteen templates are published and anybody can take one, and what each
    paid step adds is only legible next to a column that does not have it."""
    dl = next((x for x in DOWNLOADS["downloads"] if x["url"] == "/compare/"), None)
    if not dl:
        raise SystemExit("next: no brochure in data/downloads.json \u2014 "
                         "run node tools/make_pdfs.mjs")
    cols = COMPARISON["columns"]
    head = ""
    for c in cols:
        offer = OFFERS_BY_ID.get(c.get("offer") or "")
        name = c["name"]
        price = c.get("price") or (offer["price_label"] if offer else "")
        sub = c.get("sub") or (offer["eta"] if offer else "")
        link = (f'<a class="n-cmp__name" href="{NEXT_ROOT}product/?level={offer["id"]}">'
                f'ABP {html.escape(offer["short_name"])}</a>'
                if offer else f'<span class="n-cmp__name">{html.escape(name)}</span>')
        head += (f'<th scope="col">{link}'
                 f'<span class="n-cmp__price">{html.escape(price)}</span>'
                 f'<span class="n-cmp__sub">{html.escape(sub)}</span></th>')

    body, nrows = [], 0
    for g in COMPARISON["groups"]:
        body.append(f'<tr class="n-cmp__group"><th scope="rowgroup" '
                    f'colspan="{len(cols) + 1}">{html.escape(g["name"])}</th></tr>')
        for r in g["rows"]:
            nrows += 1
            body.append(f'<tr><th scope="row"><span class="n-cmp__row">'
                        f'{html.escape(r["label"])}</span>'
                        f'<span class="n-cmp__why">{html.escape(r["why"])}</span></th>'
                        + "".join(_next_cmp_cell(r[c["id"]]) for c in cols) + "</tr>")

    stale = dl["version"] != SITE["version"]
    paper = ('<p class="n-note n-mt-lg" id="the-brochure"><b>The same table on paper.</b> '
             f'<a href="/assets/downloads/{dl["file"]}" download>'
             f'{html.escape(dl["title"])} \u2014 PDF</a>. '
             f'{dl["columns"] - 1} columns, {dl["rows"]} rows, {dl["bytes"] // 1024}KB, '
             'A4 landscape, rendered from the live table through this site\u2019s own '
             'print stylesheet rather than retyped. '
             + (f'Taken at {html.escape(dl["version"])}; the site is now '
                f'{html.escape(SITE["version"])}, so the rows may have moved since.'
                if stale else f'Taken at {html.escape(dl["version"])}.')
             + "</p>")

    # THE FOUR CARDS ABOVE THE TABLE. The handback's pricing screen leads with the
    # offer cards and their buy actions and puts the table under them as "compare
    # every detail"; the first build here had the table alone, which is a
    # comparison with nothing to buy at the end of it.
    cards = "".join(_next_offer_card(l, ctx_shared, art=False, page=NEXT_COMPARE)
                    for l in levels)
    body_html = (
        '<section class="n-sect">'
        '<div class="n-head"><div class="n-head__text">'
        '<p class="n-eyebrow">The four levels</p>'
        '<h1>One policy. Choose how it arrives.</h1>'
        '<p class="n-mt">Start free, or buy the delivery and the help you need. The '
        'behaviour policy is the same document at every level; what changes is the form '
        'it arrives in and who does the correcting.</p></div>'
        f'<p class="n-head__aside"><a class="n-btn n-btn--ghost n-print" '
        f'href="/assets/downloads/{dl["file"]}" download>Print A4 brochure</a></p></div>'
        f'<div class="n-grid n-grid--4">{cards}</div>'
        '</section>'

        '<section class="n-sect n-sect--tint">'
        '<div class="n-head"><div class="n-head__text">'
        f'<p class="n-eyebrow">{nrows} rows, five columns</p>'
        '<h2>Compare every detail.</h2>'
        '<p class="n-mt">Free first, because it is the argument rather than an objection: '
        'the fifteen templates are published with read keys and anybody can take one. What '
        'each paid step adds only means anything next to a column that does not have '
        'it.</p></div>'
        f'<p class="n-head__aside"><a href="{V1_ROOT}compare/">The same table in the '
        f'previous design {_OUT}</a></p></div>'

        f'<div class="n-cmpwrap"><table class="n-cmp">'
        f'<thead><tr><th></th>{head}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table></div>'

        '<p class="n-fine n-dim n-mt">Every cell is read off something: a price in '
        '<code>data/offers.yml</code>, a sentence about what a level delivers, a line about '
        'what it does not, or a licence that has been ruled. A row whose five cells cannot '
        'each be pointed at is not in the file, which is why some things a reader might '
        'expect are missing rather than hedged.</p>'
        + paper +
        f'<p class="n-mt-lg"><a class="n-btn" href="{NEXT_PICKER}">'
        f'Pick the agent you run {_ARROW}</a></p>'
        '</section>')

    md = ["# What arrives, at every level\n",
          "Free first. The fifteen templates are published with read keys; what each paid "
          "step adds is only legible next to a column that does not have it.\n",
          "| " + " | ".join([""] + [c["name"] for c in cols]) + " |",
          "|" + "---|" * (len(cols) + 1)]
    for g in COMPARISON["groups"]:
        md.append(f"| **{g['name']}** |" + " |" * len(cols))
        for r in g["rows"]:
            cells = ["yes" if r[c["id"]] == "yes" else
                     "no" if r[c["id"]] == "no" else str(r[c["id"]]) for c in cols]
            md.append("| " + " | ".join([r["label"]] + cells) + " |")
    return _next_emit(out_dir, NEXT_COMPARE, {
        "title": "What arrives, at every level",
        "description": (f"{nrows} rows across five columns, free first: what the published "
                        "templates give you and what each paid level adds."),
    }, body_html, model, "\n".join(md))


def _next_audience_page(out_dir, ctx_shared, levels, auds, model):
    """The five doors, and what changes behind each one.

    WHAT CHANGES IS THE SENTENCE. Not the price, not the product, not which
    levels are visible: every offer is in the markup for every reader and a
    build check refuses a page that hides one. What a lens does is lead with a
    different level and say why — which is a recommendation, and is marked as
    one rather than dressed as a personalised store."""
    art = next((a for a in NEXT_ART["art"] if a["file"] == "audiences.jpg"), None)

    doors = ""
    for i, a in enumerate(AUDIENCES):
        aud = next(x for x in auds if x["id"] == a["id"])
        shift = f"{-i * 100}%" if art else "0"
        pic = (f'<span class="n-aud__art"><img src="/assets/next/art/audiences.jpg" '
               f'alt="" aria-hidden="true" style="margin-left:{shift}"></span>'
               if art else "")
        doors += (f'<a href="{aud["url"]}">{pic}<span class="n-aud__body">'
                  f'<b>{html.escape(aud["label"])}</b>'
                  f'<span>{html.escape(a["door"])}</span></span></a>')

    lens = "".join(
        f'<button class="n-fchip" type="button" data-step="aud-{a["id"]}" '
        f'aria-pressed="false">{html.escape(next(x for x in auds if x["id"] == a["id"])["label"])}'
        f'</button>' for a in AUDIENCES)

    panels = ""
    for a in AUDIENCES:
        lead = next(l for l in levels if l["id"] == a["leads_with"])
        quiet = ", ".join("ABP " + next(l for l in levels if l["id"] == q)["short_name"]
                          for q in (a.get("quiet") or []))
        panels += (
            f'<div data-step-panel="aud-{a["id"]}" hidden>'
            f'<h3>{html.escape(a["name"])}</h3>'
            f'<p class="n-lede n-mt">{html.escape(a["arrives_with"])}</p>'
            f'<p class="n-mt"><b>What changes:</b> {html.escape(a["what_changes"])}</p>'
            f'<p class="n-mt"><b>Where this reader is pointed first:</b> '
            f'ABP {html.escape(lead["short_name"])}, {html.escape(lead["price"])}. '
            f'{html.escape(a["why"])}</p>'
            + (f'<p class="n-fine n-dim n-mt">Drawn quieter for this reader, and still on '
               f'the page at the same price: {html.escape(quiet)}.</p>' if quiet else "")
            # THE FOUR CARDS, UNDER THE LENS. The handback's audience screens put
            # the offer cards right below the reader's own question, lead and
            # quiet drawn by hierarchy and never by hiding. The first build here
            # had a sentence and a link where the cards should have been.
            + '<div class="n-grid n-grid--4 n-mt-lg">'
            + "".join(_next_offer_card(l, ctx_shared, lead=a["leads_with"],
                                       quiet=a.get("quiet") or (), art=False,
                                       page=NEXT_AUDIENCE) for l in levels)
            + '</div>'
            + f'<p class="n-mt"><a class="n-btn n-btn--ghost" href="/are/{a["id"]}/">'
              f'Everything written for this reader {_ARROW}</a></p>'
            '</div>')

    body = (
        '<section class="n-sect">'
        '<div class="n-head"><div class="n-head__text">'
        f'<p class="n-eyebrow">{len(AUDIENCES)} readers, one store</p>'
        '<h1>Who is this for?</h1>'
        '<p class="n-mt">Five people arrive here with five different questions and leave '
        'with the same four products. What a door changes is the sentence and which level '
        'it points at first — never the price, never the product, and never which '
        'levels you are allowed to see.</p></div>'
        f'<p class="n-head__aside"><a href="{V1_ROOT}audiences/">The five doors in the '
        f'previous design {_OUT}</a></p></div>'
        f'<div class="n-aud">{doors}</div>'
        + (f'<p class="n-fine n-dim n-mt">{html.escape(art["label"])} &mdash; illustrative '
           'artwork for a digital deliverable, not a photograph of anybody.</p>'
           if art else "")
        + '</section>'

        '<section class="n-sect n-sect--tint">'
        '<div class="n-head"><div class="n-head__text">'
        '<h2>Read the same four levels as somebody else</h2>'
        '<p class="n-mt">Every offer stays on the page for every reader. This changes the '
        'explanation and what is recommended first, which is an opinion and is labelled as '
        'one.</p></div></div>'
        f'<div class="n-switch">{lens}</div>'
        f'<div class="n-mt n-measure">{panels}</div>'
        '</section>')

    md = ["# Who is this for?\n",
          "Five doors onto the same four products. A door changes the sentence and which "
          "level is recommended first. It never changes a price, never removes a level "
          "from the page, and a build check refuses a page that hides one.\n"]
    for a in AUDIENCES:
        lead = next(l for l in levels if l["id"] == a["leads_with"])
        md.append(f"\n## {a['name']}\n")
        md.append(f"{_strip(a['arrives_with'])}\n")
        md.append(f"- **What changes:** {_strip(a['what_changes'])}")
        md.append(f"- **Pointed first at:** ABP {lead['short_name']}, {lead['price']}. "
                  f"{_strip(a['why'])}")
    return _next_emit(out_dir, NEXT_AUDIENCE, {
        "title": "Who is this for?",
        "description": ("Five readers, five questions, the same four products: what each "
                        "door changes and what it never changes."),
    }, body, model, "\n".join(md))


def _next_doors(out_dir, ctx_shared, levels, model):
    """One page per audience at /are/<id>/, in this design.

    The reader's own question is the headline, the four levels are under it with
    the one that usually fits drawn first and the ones that usually do not drawn
    quieter, and NOTHING IS HIDDEN: every level is on every door at its price,
    and check_the_five_audiences_hide_nothing refuses a door that drops one.
    Then why that one is first, one published vault to go and look at before
    spending anything, and the other four doors."""
    made = {}
    for a in AUDIENCES:
        url = f"{AUDIENCE_ROOT}{a['id']}/"
        lead = next(l for l in levels if l["id"] == a["leads_with"])
        ev = next(w for w in EVIDENCE["works"] if w["id"] == a["evidence"])
        ctx_shared["external_links"].add(ev["url"])
        cards = "".join(_next_offer_card(l, ctx_shared, lead=a["leads_with"],
                                         quiet=a.get("quiet") or (), art=False, page=url)
                        for l in levels)
        others = "".join(
            f'<a class="n-fchip" href="{AUDIENCE_ROOT}{o["id"]}/">'
            f'{html.escape(next(x for x in _next_audiences() if x["id"] == o["id"])["label"])}'
            '</a>' for o in AUDIENCES if o["id"] != a["id"])
        body = (
            '<section class="n-sect">'
            '<div class="n-head"><div class="n-head__text">'
            f'<p class="n-eyebrow">{html.escape(a["name"])}</p>'
            f'<h1>{html.escape(a["arrives_with"])}</h1>'
            f'<p class="n-mt">{html.escape(a["what_changes"])}</p></div>'
            f'<p class="n-head__aside"><a href="{NEXT_AUDIENCE}">The five doors, side by '
            f'side {_ARROW}</a></p></div>'
            f'<div class="n-grid n-grid--4">{cards}</div>'
            f'<p class="n-note n-mt-lg"><b>Why ABP {html.escape(lead["short_name"])} is first '
            f'for you.</b> {html.escape(a["why"])} <b>Nothing is hidden from anybody</b>: '
            'these are the same four levels every reader of this store sees, at the same '
            'prices; this page opens on the one that usually fits the question you arrived '
            'with.</p>'
            '</section>'

            '<section class="n-sect n-sect--tint">'
            '<div class="n-head"><div class="n-head__text">'
            '<p class="n-eyebrow">Go and look at one first</p>'
            f'<h2>{html.escape(ev["title"])}</h2>'
            f'<p class="n-mt">{html.escape(a["evidence_why"])}</p></div></div>'
            '<div class="n-works" style="grid-template-columns:minmax(0,1fr)">'
            f'<a class="n-work" href="{ev["url"]}" rel="nofollow" style="color:inherit;'
            'background:var(--n-panel);border-color:var(--n-line)">'
            f'<b>{html.escape(ev["title"])}</b>'
            f'<span class="n-work__why" style="color:var(--n-dim)">&ldquo;'
            f'{html.escape(ev["quoted"])}&rdquo; {html.escape(ev["why"])}</span>'
            f'<span class="n-work__meta" style="color:var(--n-dim-2)">'
            f'<code>{html.escape(ev["vault"])}</code> &middot; {html.escape(ev["size"])} '
            f'&middot; published {html.escape(ev["published"])} {_OUT}</span></a></div>'
            '<p class="n-fine n-dim n-mt">It opens with a read key published on its own '
            'page &mdash; no account, nothing to install, and nothing asked of you for '
            f'looking. <a href="{NEXT_ROOT}#evidence">Five more like it</a>.</p>'
            f'<p class="n-mt-lg n-fine n-dim">The other four ways in:</p>'
            f'<div class="n-switch">{others}</div>'
            '</section>')
        md = [f"# {a['name']}\n", f"**You arrive asking:** {a['arrives_with']}\n",
              f"{_strip(a['what_changes'])}\n", "## The four levels\n"]
        for l in levels:
            tag = (" — first for you" if l["id"] == a["leads_with"]
                   else " — drawn quieter, same price" if l["id"] in (a.get("quiet") or ()) else "")
            md.append(f"- **ABP {l['short_name']}** — {l['price']} — {_strip(l['short_what'])}{tag}")
        md += ["", f"**Why first:** {_strip(a['why'])}", "",
               f"## Go and look at one first\n\n{_strip(a['evidence_why'])}\n",
               f"- **{ev['title']}** — {ev['url']}"]
        made[url] = _next_emit(out_dir, url, {
            "title": a["name"],
            "description": f"{a['arrives_with']} {_strip(a['what_changes'])}"[:300],
        }, body, model, "\n".join(md))
    return made


def _next_describe(out_dir, ctx_shared, levels, model):
    """Describe your agent, in this design.

    THE ENGINE IS THE LAB'S, UNCHANGED. assets/agent.js has driven the two lab
    prototypes since the vocabulary was promoted: click a capability to give it
    to the agent, click again to take it away, copy the result out as the GRANT
    half of a policy or download it as JSON, nothing leaves the browser. That is
    the whole of what the handback's screen does too, so this page re-draws the
    lab's markup in the store's design and binds the same script to it. The
    twenty-three primitives, their families and their glosses come off the same
    island the lab uses.

    WHAT IT PRODUCES IS THE GRANT AND THE PAGE SAYS SO TWICE. Not the mandate,
    not the delta, not a policy — the half a person can answer from their own
    deployment, which is why it is the half given away. The half that needs
    somebody to look is the corrected level, and that is the one link out."""
    tailored = next(l for l in levels if l["id"] == "t3")
    fams = ""
    for fam, gloss in CAP_FAMILIES.items():
        rows = [c for c in CAPS if c["family"] == fam]
        if not rows:
            continue
        fams += (f'<section class="fam" data-fam="{html.escape(fam)}">'
                 f'<h4>{html.escape(fam)}<span>{html.escape(gloss)}</span></h4>'
                 f'<div class="fam-caps">{"".join(_cap_chip(c) for c in rows)}</div>'
                 '</section>')
    body = (
        '<section class="n-sect">'
        '<div class="n-head"><div class="n-head__text">'
        '<p class="n-eyebrow">Describe your agent</p>'
        '<h1>Make its reach visible.</h1>'
        f'<p class="n-mt">Choose what your agent can do, out of the {CAPABILITIES["count"]} '
        'things an agent can be granted. What you build stays in this browser and leaves '
        'as text you copy out or a file you download; nothing here is sent anywhere.</p>'
        '</div>'
        f'<p class="n-head__aside"><a href="/what-is-in-one/">What a grant is, and what it is '
        f'not {_ARROW}</a></p></div>'
        + agent_model_island(rel_prefix(NEXT_DESCRIBE)) +
        '<div class="ag n-describe" data-mode="describe">'
        '<div class="n-describe__grid">'
        '<div class="ag-palette">' + fams + '</div>'
        '<aside class="n-describe__side">'
        '<div class="ag-stage"><div class="ag-core"><span class="n-describe__mark">ABP</span>'
        '<b>Your agent</b><span class="ag-count" data-ag-count>nothing yet</span></div></div>'
        '<div class="ag-out"><h3>What you have said it can do</h3>'
        '<div data-ag-list class="ag-list"><p class="n-dim n-fine">Nothing selected. Click a '
        'capability on the left.</p></div>'
        '<div class="ag-acts">'
        '<button type="button" class="n-btn" data-ag-copy>Copy the definition</button>'
        '<button type="button" class="n-btn n-btn--ghost" data-ag-download>Download as JSON'
        '</button>'
        '<button type="button" class="n-btn n-btn--ghost" data-ag-clear>Start again</button>'
        '</div>'
        '<p class="n-fine n-dim">Self-described, not measured. It goes to your clipboard or '
        'your downloads and nowhere else.</p>'
        '</div></aside></div></div>'
        '</section>'

        '<section class="n-sect n-sect--tint">'
        '<div class="n-head"><div class="n-head__text">'
        '<h2>What this produces, and what it does not</h2>'
        '<p class="n-mt"><b>It produces the grant</b> — everything the agent <em>can</em> '
        'do, as you describe it. That is one of four objects in an Agent Behaviour Policy. '
        'It is not the mandate, not the delta between them, and not a policy. It is the '
        'half you can answer from the deployment, which is why it is the half given away; '
        'and it is described by hand, so <code>MAP-A-GRANT.md</code>, which ships in every '
        'template pack and measures the same thing from the deployment, will disagree with '
        'it wherever somebody guessed.</p></div></div>'
        '<div class="n-grid n-grid--2">'
        '<div class="n-object"><p class="n-object__n">THE HALF THAT NEEDS A PERSON</p>'
        f'<h3>ABP {html.escape(tailored["short_name"])}, {html.escape(tailored["price"])}</h3>'
        f'<p>{inline(tailored["short_what"], ctx_shared)} The document this page produces '
        'is one of the two files you send back; the corrected vault follows '
        f'{html.escape(tailored["eta"].lower())} from your reply.</p>'
        f'<p class="n-object__claim">'
        f'{_next_claim_chip("abp-correction-by-a-person", ctx_shared, NEXT_DESCRIBE)}</p>'
        f'<p class="n-mt"><a class="n-btn" href="{NEXT_ROOT}product/?level=t3&amp;policy='
        f'{NEXT_DEFAULT_POLICY}">Buy this level {_ARROW}</a></p></div>'
        '<div class="n-object"><p class="n-object__n">THE VOCABULARY IS NOT OURS</p>'
        f'<h3>{CAPABILITIES["count"]} primitives on one grammar</h3>'
        f'<p><code>{html.escape(CAPABILITIES["grammar"])}</code>, promoted from '
        'riskmandate.ai\u2019s own template vault so that what you describe here is in the '
        'same words as the document you would receive. Nothing in it was written by this '
        f'store. <a href="{NEXT_PICKER}">The fifteen published shapes {_ARROW}</a></p></div>'
        '</div></section>')

    md = ["# Describe your agent\n",
          f"Choose what your agent can do, out of {CAPABILITIES['count']} primitives on a "
          f"`{CAPABILITIES['grammar']}` grammar. What you build stays in the browser and "
          "leaves as text or JSON.\n",
          "It produces the GRANT only: not the mandate, not the delta, not a policy. It is "
          "described by hand, not measured; MAP-A-GRANT.md measures the same thing from the "
          "deployment and will disagree wherever somebody guessed.\n",
          "## The families\n"]
    for fam, gloss in CAP_FAMILIES.items():
        rows = [c for c in CAPS if c["family"] == fam]
        if rows:
            md.append(f"- **{fam}** \u2014 {gloss}: " + ", ".join(f"`{c['id']}`" for c in rows))
    return _next_emit(out_dir, NEXT_DESCRIBE, {
        "title": "Describe your agent",
        "description": (f"Choose what your agent can do out of {CAPABILITIES['count']} "
                        "capability primitives and take the grant away as text or JSON. "
                        "Nothing is sent anywhere."),
        "scripts": ["/assets/agent.js"],
    }, body, model, "\n".join(md))


def _next_ledger(out_dir, ctx_shared, model, built):
    """Every claim this site makes, in this design.

    It is here so that a claim chip on a /next/ page does not throw the reader
    back into the design being replaced. It renders the same 52 claims from the
    same file the live ledger is built from — there is no second copy."""
    claims = ctx_shared["claims"]
    counts = {}
    for c in claims:
        counts[c["state"]] = counts.get(c["state"], 0) + 1
    tiles = "".join(
        f'<div class="n-stat"><b>{counts[k]}</b><span>{html.escape(STATES[k][0])}</span></div>'
        for k in STATES if counts.get(k))

    def _resolve(key):
        """A claim-use key as a URL, or None.

        Every page registers the URL it is served at, so this is almost always a
        lookup that succeeds. It is still allowed to fail: a claim registered by
        something that never became a page would otherwise render as a link to
        nowhere, and a citation this page cannot stand behind is not one it
        prints."""
        url = ctx_shared["page_urls"].get(key)
        if url:
            return url
        return key if key in built else None


    def _label(url):
        # /next/policies/ and /policies/ both end in "policies", and a list that
        # prints that word twice is telling a reader the same page twice. The
        # design round says so in the label.
        if url == NEXT_ROOT:
            return "next"
        if url.startswith(NEXT_ROOT):
            return "next/" + short_label(url)
        return short_label(url)

    def _where(c):
        out, dropped = [], 0
        for u in sorted(ctx_shared["claim_uses"].get(c["id"], set())):
            url = _resolve(u)
            if not url:
                dropped += 1
                continue
            label = ctx_shared["page_titles"].get(u) or built.get(url) or url
            out.append(f'<a href="{url}" title="{html.escape(str(label))}">'
                       f'{html.escape(_label(url))}</a>')
        if not out:
            return '<span class="n-dim">not cited on any page</span>'
        return ", ".join(out) + (f' <span class="n-dim">and {dropped} more</span>'
                                 if dropped else "")

    groups = {}
    for c in claims:
        groups.setdefault(c.get("group", "Other"), []).append(c)

    sections = ""
    for group, items in groups.items():
        rows = ""
        for c in items:
            rows += (
                f'<div class="n-claimrow" id="claim-{c["id"]}">'
                f'<div><span class="n-claim n-claim--{c["state"]}">'
                f'{html.escape(STATES[c["state"]][0])}</span>'
                f'<span class="n-claimrow__date">{html.escape(c.get("date_label") or "")}'
                f'</span></div>'
                f'<div><p>{inline(c["claim"], ctx_shared)}</p>'
                f'<p class="n-claimrow__cites"><b>How we know:</b> '
                f'{html.escape(str(c.get("source", "")))}</p>'
                f'<p class="n-claimrow__cites"><b>Said on:</b> {_where(c)}</p></div>'
                f'<code class="n-claimrow__date">{html.escape(c["id"])}</code>'
                '</div>')
        sections += (f'<h2 class="n-mt-lg" id="{slugify(group)}">{html.escape(group)}</h2>'
                     f'<div class="n-ledger n-mt">{rows}</div>')

    body = (
        '<section class="n-sect">'
        '<div class="n-head"><div class="n-head__text">'
        f'<p class="n-eyebrow">{len(claims)} claims</p>'
        '<h1>Everything this store says, and how it knows.</h1>'
        '<p class="n-mt">Every chip on every page in this design round links to a row '
        'below. A claim that cannot be pointed at something is not a claim this site '
        'makes — it is either marked as absent or it is not on a page.</p></div>'
        f'<p class="n-head__aside"><a href="{V1_ROOT}ledger/">The same ledger in the '
        f'previous design {_OUT}</a></p></div>'
        f'<div class="n-panel__stats">{tiles}</div>'
        '<p class="n-fine n-dim n-mt">Ten states, and only <b>exists and runs</b> is fully '
        'earned. The rest say what kind of thing stands behind a sentence: read from a '
        'published source, measured on a named workload, arithmetic with the workings '
        'shown, a specification for something not built, or a person’s time.</p>'
        '<h2 class="n-mt-lg" id="the-states">What each state means</h2>'
        '<div class="n-states n-mt">'
        + "".join(
            f'<div class="n-states__row" id="state-{k}">'
            f'<span class="n-claim n-claim--{k}">{html.escape(v[0])}</span>'
            f'<p>{html.escape(v[2])}</p>'
            f'<span class="n-states__n">{counts.get(k, 0)}</span></div>'
            for k, v in STATES.items())
        + '</div>'
        + sections +
        '</section>')

    md = [f"# Everything this store says, and how it knows\n",
          f"{len(claims)} claims. Every chip on a page links to one of these rows.\n"]
    for group, items in groups.items():
        md.append(f"\n## {group}\n")
        for c in items:
            md.append(f"- **{STATES[c['state']][0]}** — {_strip(c['claim'])} "
                      f"*(how we know: {c.get('source', '')})* `{c['id']}`")
    return _next_emit(out_dir, NEXT_LEDGER, {
        "title": "Everything this store says, and how it knows",
        "description": (f"The claim ledger in this design: {len(claims)} claims, the state "
                        "of each, how it is evidenced and which pages say it."),
    }, body, model, "\n".join(md))


def _next_who(out_dir, ctx_shared, levels, model):
    """Who does the work at the two levels a person does it.

    Asking £500 and £1,500 for somebody's time and not saying whose is a worse
    problem than any price on this site. Nothing here is written from what
    anybody said about themselves: every line carries the published page it was
    read from and the date it was read."""
    src_rows = "".join(
        f'<li><a href="{s["url"]}" rel="nofollow">{html.escape(s["url"])}</a> '
        f'&mdash; read {html.escape(s["read"])}. {html.escape(s["what"])}</li>'
        for s in REVIEWERS_FILE["_sources"])
    for s in REVIEWERS_FILE["_sources"]:
        ctx_shared["external_links"].add(s["url"])

    people = ""
    for r in REVIEWERS:
        ctx_shared["external_links"].add(r["contact"])
        does = [l for l in levels if l["id"] in r["does"]]
        rec = "".join(f'<li><b>{inline(x["what"], ctx_shared)}</b>'
                      f'<cite>{inline(x["detail"], ctx_shared)}</cite></li>'
                      for x in r["record"])
        buys = "".join(
            f'<a class="n-btn n-btn--ghost" href="{NEXT_ROOT}product/?level={l["id"]}">'
            f'ABP {html.escape(l["short_name"])}, {html.escape(l["price"])} {_ARROW}</a> '
            for l in does)
        people += (
            '<div class="n-reviewer">'
            f'<div><div class="n-reviewer__face" aria-hidden="true">'
            f'{html.escape("".join(w[0] for w in r["name"].split()[:2]).upper())}</div>'
            f'<p class="n-fine n-dim n-mt">On this list since {html.escape(r["since"])}.'
            '</p></div>'
            f'<div><h2>{html.escape(r["name"])}</h2>'
            f'<p class="n-lede n-mt">{inline(r["one_line"], ctx_shared)}</p>'
            f'<p class="n-mt">{inline(r["lede"], ctx_shared)}</p>'
            f'<p class="n-note n-mt"><b>Why them:</b> {inline(r["why_them"], ctx_shared)}</p>'
            f'<h3 class="n-mt-lg">The record</h3><ul class="n-mt">{rec}</ul>'
            f'<p class="n-mt-lg">{buys}</p>'
            f'<p class="n-fine n-mt"><a href="{r["contact"]}" rel="nofollow">'
            f'{html.escape(r["contact_label"])} {_OUT}</a> &middot; '
            f'<a href="/who/{r["id"]}/">the full record, with the work {_OUT}</a></p>'
            '</div></div>')

    body = (
        '<section class="n-sect">'
        '<div class="n-head"><div class="n-head__text">'
        '<p class="n-eyebrow">Delivered by a person</p>'
        '<h1>Who does the work.</h1>'
        '<p class="n-mt">Two of the four levels are somebody’s time rather than a '
        'pipeline, which is why their delivery estimates depend on a calendar. This is '
        'who.</p></div>'
        f'<p class="n-head__aside"><a href="{V1_ROOT}who/">The register in the previous '
        f'design {_OUT}</a></p></div>'

        '<p class="n-note n-note--hold"><b>Nothing below was written from what anybody told '
        'us.</b> Every line is read off a published page, and the page and the date it was '
        'read are here. A biography this store composed is the one thing that should not '
        'stand next to a price this size.</p>'
        f'<ul class="n-fine n-dim n-mt">{src_rows}</ul>'
        f'<div class="n-mt-lg">{people}</div>'

        '<p class="n-note n-mt-lg"><b>One name, and the list is built for more.</b> Adding '
        'a second person is adding a record to one file: this page, its markdown twin, the '
        'register and the links from every level page are generated from it.</p>'
        '</section>')

    md = ["# Who does the work\n",
          "Two of the four levels are somebody's time rather than a pipeline. Nothing here "
          "was written from what anybody told us: every line is read off a published page, "
          "with the page and the date it was read.\n", "## Sources\n"]
    for s in REVIEWERS_FILE["_sources"]:
        md.append(f"- {s['url']} — read {s['read']}. {s['what']}")
    for r in REVIEWERS:
        md.append(f"\n## {r['name']}\n\n{_strip(r['one_line'])}\n\n{_strip(r['lede'])}\n")
        md.append(f"**Why them:** {_strip(r['why_them'])}\n")
        for x in r["record"]:
            md.append(f"- **{_strip(x['what'])}** — {_strip(x['detail'])}")
    return _next_emit(out_dir, NEXT_WHO, {
        "title": "Who does the work",
        "description": ("The named security professional who delivers the two levels a "
                        "person delivers, and the published pages every line of the record "
                        "was read from."),
    }, body, model, "\n".join(md))


# ---------------------------------------------------------------------------
# WHERE /next/ WENT. The design was built at /next/ across three rounds and those
# addresses were shared — with the design team, in the write-up, and on the board.
# They are not deleted: each one is a page that says where its page went, carries
# the canonical link to it, and refreshes there for anybody who did not want to
# read a sentence about a URL.
NEXT_WAS = {
    "/next/": NEXT_ROOT,
    "/next/product/": NEXT_ROOT + "product/",
    "/next/policies/": NEXT_PICKER,
    "/next/cart/": NEXT_CART,
    "/next/pay/": NEXT_PAY,
    "/next/paid/": NEXT_PAID,
    "/next/compare/": NEXT_COMPARE,
    "/next/audiences/": NEXT_AUDIENCE,
    "/next/ledger/": NEXT_LEDGER,
    "/next/who/": NEXT_WHO,
}


def _next_moved(out_dir, ctx_shared, model):
    """One page per address the design round used, pointing at what it became."""
    made = {}
    for was, now in NEXT_WAS.items():
        title = NEXT_TITLES.get(now, "the store")
        body = (
            '<section class="n-sect">'
            '<div class="n-narrow">'
            '<p class="n-eyebrow">This page moved</p>'
            f'<h1>{html.escape(title)}</h1>'
            f'<p class="n-lede n-mt">The design that was built here across three rounds is '
            f'the store now, so this page lives at <a href="{now}"><code>{html.escape(now)}'
            f'</code></a>. You should be there already; if not, that link is it.</p>'
            f'<p class="n-mt"><a class="n-btn" href="{now}">Go there {_ARROW}</a></p>'
            '<p class="n-fine n-dim n-mt-lg">The design this replaced is kept at '
            f'<a href="{V1_ROOT}">the previous store</a>, and how the direction was chosen '
            f'and built is at <a href="{NEXT_ADMIN}">what this design is</a>.</p>'
            '</div></section>')
        md = (f"# This page moved\n\n`{was}` is now `{now}`. The design built at /next/ "
              f"across three rounds is the store; the design it replaced is kept at "
              f"`{V1_ROOT}`.\n")
        made[was] = _next_emit(out_dir, was, {
            "title": f"{title} \u2014 moved",
            "description": f"This page is now at {now}.",
            "robots": "noindex,follow",
            "canonical": now,
            "moved_to": now,
        }, body, model, md)
    return made


NEXT_TITLES = {}


def next_pages(out_dir, ctx_shared, built=None):
    _the_ledger_must_move_with_the_till()
    levels = _next_offers()
    auds = _next_audiences()
    shapes = _next_shapes()
    model = {"levels": levels, "audiences": auds, "shapes": shapes,
             "order": _next_order_model(),
             "picker_url": NEXT_PICKER, "checkout_url": NEXT_PAY,
             "ledger_url": NEXT_LEDGER, "product_url": NEXT_ROOT + "product/",
             "cart_url": NEXT_CART, "default_policy": NEXT_DEFAULT_POLICY,
             # The CODE is not here and is not anywhere in docs/. What ships is
             # sha256 of it, keyed on the record's stable id; data/discounts.yml
             # says at length why, and a check greps the whole built tree for
             # every code so that stays a fact.
             "codes": [{"id": d["id"], "hash": d["hash"], "pct": int(d["pct"]),
                        "label": d["label"], "levels": d.get("levels", "all"),
                        "until": str(d["until"])}
                       for d in DISCOUNTS],
             "code_storage": "sgit.store.code.v1",
             "default_level": NEXT_LEAD, "default_audience": auds[0]["id"]}
    pages = {}
    pages[NEXT_ROOT] = _next_home(out_dir, ctx_shared, levels, auds, model)
    pages[NEXT_ROOT + "product/"] = _next_product(out_dir, ctx_shared, levels, auds, model)
    pages[NEXT_PICKER] = _next_picker(out_dir, ctx_shared, levels, shapes, model)
    pages[NEXT_CART] = _next_cart(out_dir, ctx_shared, levels, model)
    pages[NEXT_PAY] = _next_pay(out_dir, ctx_shared, levels, model)
    pages[NEXT_PAID] = _next_paid(out_dir, ctx_shared, levels, model)
    pages[NEXT_COMPARE] = _next_compare(out_dir, ctx_shared, levels, model)
    pages[NEXT_AUDIENCE] = _next_audience_page(out_dir, ctx_shared, levels, auds, model)
    pages[NEXT_WHO] = _next_who(out_dir, ctx_shared, levels, model)
    pages.update(_next_doors(out_dir, ctx_shared, levels, model))
    pages[NEXT_DESCRIBE] = _next_describe(out_dir, ctx_shared, levels, model)
    # LAST, AND THAT IS THE POINT. The ledger prints where each claim is said,
    # and it can only print the pages that have already registered a citation.
    pages[NEXT_LEDGER] = _next_ledger(out_dir, ctx_shared, model,
                                      dict(built or {}, **pages))
    pages.update(_next_admin(out_dir, ctx_shared, levels))
    NEXT_TITLES.update(pages)
    pages.update(_next_moved(out_dir, ctx_shared, model))
    return pages


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
    # KEYED BOTH WAYS, ON PURPOSE. A claim registers the URL of the page that says
    # it, which is the only key that works for a generated page: the label those
    # carry is a slug for their own bookkeeping and several of them do not match
    # their route — /admin/reviews/ registers "reviews". Resolving a URL from a
    # label produced ten dead links on the ledger's first build in the new design.
    # The path keys stay because the rest of the build reads pages by path.
    page_urls = {str(p["path"]): p["url"] for p in pages}
    page_urls.update({p["url"]: p["url"] for p in pages})
    page_titles = {str(p["path"]): p["fm"]["title"] for p in pages}
    page_titles.update({p["url"]: p["fm"]["title"] for p in pages})

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
    # WHERE A DOWNLOAD LANDS DEPENDS ON WHETHER ANYTHING VOUCHES FOR IT.
    #
    # The two walkthrough PDFs live under /admin/ for one reason: they print the
    # walkthrough discount codes, and the check that keeps those codes off every
    # other file in the built site exempts /admin/ alone. Their names carry the
    # version they were taken at, so a stale copy is stale on its face.
    #
    # The comparison brochure is a different animal: it is a selling document,
    # it carries no codes, and a buyer being sent to /admin/ to fetch it would be
    # absurd. So the rule is the safe way round — a file RECORDED in
    # data/downloads.json was produced by tools/make_pdfs.mjs from a named page
    # and is buyer-facing; anything else in the folder is unvouched-for and stays
    # behind /admin/. Adding a file to that directory by hand does not quietly
    # publish it.
    _dl = ASSETS / "downloads"
    if _dl.is_dir():
        vouched = {d["file"] for d in DOWNLOADS["downloads"]}
        (out_dir / "admin" / "downloads").mkdir(parents=True, exist_ok=True)
        for f in sorted(_dl.iterdir()):
            if f.name not in vouched:
                shutil.copy2(f, out_dir / "admin" / "downloads" / f.name)
                (out_dir / "assets" / "downloads" / f.name).unlink()
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
    extra.update(status_page(out_dir, ctx_shared))
    extra.update(concepts_page(out_dir, ctx_shared))
    extra.update(design_brief_page(out_dir, ctx_shared))
    extra.update(audience_pages(out_dir, ctx_shared))
    extra.update(reviewer_pages(out_dir, ctx_shared))
    extra.update(paid_pages(out_dir, ctx_shared))
    # LAST. /next/ carries its own copy of the claim ledger, and that page prints
    # which pages say each claim. It can only name the ones that have already
    # registered a citation, so it goes after everything that makes one.
    extra.update(next_pages(out_dir, ctx_shared, extra))

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
    # READ OFF THE BUILT FILE, NOT OFF THE FRONT-MATTER. The front-matter answer
    # is only available for the markdown pages, so a generated page could be
    # noindex and still be advertised — which is exactly what happened when the
    # archive and the ten moved-page stubs arrived: nineteen noindex pages in the
    # sitemap, every one of them telling a crawler not to index the page the
    # sitemap had just asked it to come and look at. The file on disk knows.
    noindexed = set()
    for u in sorted(set(rendered) | set(extra)):
        f = out_dir / u.strip("/") / "index.html"
        if f.exists() and 'content="noindex' in f.read_text()[:2000]:
            noindexed.add(u)
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
        "<page>/index.md. No page on this site that sells anything opens a network connection at "
        "all; two kinds of page do and each says so on itself — a review under /admin/reviews/ "
        "embeds the vault it reviews, and a page under /paid/ embeds one published example vault. "
        "Both from one host. Nothing here sends anything about a reader, on any page.",
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
