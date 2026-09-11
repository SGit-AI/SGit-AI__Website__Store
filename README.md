# SGit-AI__Website__Store

The source for **[store.sgit.ai](https://store.sgit.ai/)** — the estate's first site
that carries a price. Six offers: four tiers with a printed code behind them, and two
add-ons that are listed and not yet buyable — **grouped by which of three buyers each
one was built for**, because "which of these is mine" is the question somebody arrives
with and "what does it cost" is not.

> **The paid thing is not access and it is not customisation. It is independence.**
> The free public library belongs to the registry and stays free. Every paid thing
> here is an instance.

## What it sells, and what is true of each

| Tier | Price | State of the thing behind the price |
|---|---|---|
| **1** | £10 | The application that computes the delta **was built in August and has not been located** |
| **2** | £50 to £100 | Specified 28 July. The graph exists at 1,523 nodes. **The pipeline does not exist** |
| **3** | £150 to £1,000 | A booking. It overlaps the opinion add-on, and **the overlap is unresolved** |
| **4** | £5,000 to £10,000 | A booking with a deposit. The seven-role team is specified and **has never run** |
| **Add-on** | By depth band | The generator runs. **The fact diff does not**, so the guarantee is not printed |
| **Add-on** | By depth band | **The wording does not exist**, so there is no code behind it |

Two of the six do not exist yet and say so on their own row, on the offer page, on
their delivery page and in [the ledger](https://store.sgit.ai/ledger/). None of those
sentences is softened anywhere, and a build check holds that line.

## Who each one is for

| Buyer | Arrives asking | Built for them | Also shown |
|---|---|---|---|
| **[You run agents today](https://store.sgit.ai/for/agents/)** | What did I actually grant it? | `t1` `t2` | `add-formats` |
| **[You are backing a company](https://store.sgit.ai/for/investors/)** | What would somebody who knows what they are doing find? | `t3` `t4` | `add-opinion` `add-formats` |
| **[You are a startup](https://store.sgit.ai/for/startups/)** | What is diligence going to find, before it finds it? | **nothing** | `t3` `t4` `t2` `add-formats` |

The third row is the point of the table. **Nothing on the offer list was built pointing
at a startup** — two funded incumbents and a free tier already sit under that tier — so
that page says so *above* its offers rather than below them, and the reverse-direction
offer is a framing of tiers 3 and 4 rather than a seventh thing on the price list.

`data/buyers.yml` may name offer ids and nothing else. The build joins them to
`data/offers.yml`, and the gate fails the release if a group names an offer that does not
exist, if a tier belongs to no group or to two, or if the group set changes. **A buyer
page cannot contain a product**, which is the specific way an offer list grows without
anybody deciding to grow it.

## The checkout

**Payment links, on the payment provider's own pages. No form, no script, no key.**
Every offer carries a `checkout_url` in `data/offers.yml`; the build renders a live
button where a URL exists and a sentence saying why there is none where it does not.
**Every one of those fields is empty today**, so pasting one line is the whole of
turning a checkout on — and a greyed-out button would be a lie about which half of the
work is done.

Two things are held mechanically, and both are because **the codes are printed**:

- **The host.** A checkout URL must be on `buy.stripe.com` or `checkout.stripe.com`, over HTTPS. A link that can be edited into a redirect through somewhere else is a phishing page carrying our prices, and a card handed out on a conference floor cannot be recalled.
- **The mode.** How an offer is paid for follows from its price and is frozen beside it. A fixed-price link carries one price, so **only tier 1 can ever hold a standing link**; tiers 2 and 3 are bands, tier 4 is above the threshold where a card makes sense, and the add-ons are priced against whatever they attach to.

`<form>`, `<input>`, `<textarea>` and `<select>` appear nowhere in `docs/` and a check
keeps it that way: three pages say this site collects nothing from anybody, and a
checkout that is a link to somebody else's page and a checkout that is a form on ours
are different products with different obligations.

## Layout

```
  .github/workflows/   validate → tag → deploy
  admin/build/         version.txt (owns the version) and validate.sh (the gate)
  assets/              site.css, site.js, favicon.svg — no web fonts, no CDN
  bin/                 bump.py — the only thing that moves the version
  content/             the markdown sources, with YAML front-matter
  data/                offers.yml (the ONLY place a price exists), buyers.yml (a second
                       index over it, and no prices), claims.yml, pack.yml (the dev-pack
                       manifest), refs.yml (the guidance this is built against),
                       releases.json
  docs/                THE BUILT OUTPUT. GitHub Pages serves this. COMMITTED
  refs/                fetched reference docs. NOT committed, NOT under docs/
  tools/               check_site.py, refs.py, secret-scan.sh, check-js.sh
  build.py             the whole build system. No dependencies
```

## The reference docs this is built against

The guidance at [sgit.ai](https://sgit.ai/llms.txt) is load-bearing here — the version
convention this repo follows, the read-key rule its secret scan implements, *anything
rendered stays one click from the bytes it was rendered from* (which is why every page
has a `.md` twin), and *state the gap rather than papering over it* (which is why
[the ledger](https://store.sgit.ai/ledger/) exists at all). Guidance read once by
whoever happened to be there is guidance the next person drops.

```bash
tools/refs.py fetch            # pull every source in data/refs.yml into refs/
tools/refs.py list             # what is cached, how big, when, and its sha256
tools/refs.py read guidance    # print one, and what this repo took from it
tools/refs.py grep "read key"  # search the cache, with id and line number
tools/refs.py links guidance   # the .md links in it that data/refs.yml lacks
tools/refs.py check            # re-fetch, diff the hashes, exit 1 if one moved
```

It fetches the **`.md` twin**, never the HTML: sgit.ai generates both from the same
content, so scraping the page would be re-deriving something already published. Each
entry in `data/refs.yml` records **what this repository actually took from it**, so
`check` can say not only that a document moved but which decision here rests on it.

`refs/` is gitignored and is **not under `docs/`** — that second part is not tidiness.
Hard rule 1 bars one word from every byte this site publishes, and 11 of the 19
documents in this repo's own pack carry it. Fetched text is not ours to edit, so it
never enters the build tree and the gate never has to hold an opinion about it.

## Build

```bash
python3 build.py              # build docs/
python3 build.py --check      # build to a temp dir and diff against docs/ (CI)
admin/build/validate.sh       # the full pre-release gate
```

Python 3.11+, **no external dependencies**. A site that sells checkability should not
ask a reader to trust forty transitive packages.

## Release

```bash
bin/bump.py "what changed in this release"
python3 build.py
admin/build/validate.sh
git commit -am "site v0.1.1: what changed in this release"
git push -u origin dev
bin/bump.py --commit <the sha that release landed as>   # recorded with the next bump
```

`admin/build/version.txt` owns the version, `bin/bump.py` moves it, the release
commit's subject repeats it, and **CI refuses to tag if the two disagree.** `dev` is
the release branch and the default.

## The gate, and why it is longer than a sibling's

This is the first site in the estate where **a page carries a price**, which makes it
an offer rather than an argument. Fifteen hard rules constrain what an offer page may
say. `tools/check_site.py` runs the ones a script can run, and each check names the
rule it enforces:

- **One word never appears anywhere in `docs/`** — not in copy, not in a heading, not
  in a filename. The rule argues its own absoluteness: a positioning phrase is a
  claim, but a priced checkout is an offer.
- **No conformity-marking language in any form**, and *compliance assessment* only
  ever inside a denial.
- **Three contested terms** — one for encryption, one for recall, one for autonomy —
  reach no page, including [the page that explains why](https://store.sgit.ai/disclosures/).
- **The sentence about what an operator can read is absent** until six questions about
  what leaks are answered. A regulator acted on that claim in November 2020 and the
  settlement ran twenty years.
- **The absolute form of the tamper claim never appears**, and the honest form never
  appears without its witness in sight.
- **One phrase is blocked** by a naming collision that is open.
- **Every price matches a frozen table**, to the penny, because these numbers go onto
  printed cards that cannot be corrected from a conference floor.
- **Every mention of committed spend carries the negation**, because the old version
  of that claim was wrong and three sources say so.
- **Every checkout URL is on the payment provider's own host**, every checkout mode
  matches the price it follows from, and nothing links to a payment destination that no
  offer declares. There is no form, no input and no key anywhere in the output.
- **The buyer groups are an index and not a range**: a group names offer ids only, every
  tier belongs to exactly one group, and the group whose list is empty says so on its
  own page.

Each of those checks has been run against a deliberate break — a checkout pointed off
host, a band silently turned into a fixed price, a tier dropped out of every group, an
empty group claiming one, a buyer page inventing a seventh offer — and each failed the
way it is supposed to. A check that has never failed is not a check.

## Two things this repository does not do

**The dev packs area publishes no documents.** The instruction was to publish them;
the same document named five checks that run first and recorded that who runs them is
not decided. Two of the five are measurable, and the measurement is that **11 of the
19 documents carry the word hard rule 1 bars from every page of this site**, one of
them in its own title. So the area publishes its manifest — every document, its size,
its sha256 — and holds the text. [What that looks like](https://store.sgit.ai/dev-packs/).

**It does not argue with the domain ruling.** A ruling of 10 September placed a
storefront under the risk product rather than on the platform domain. The instruction
in hand overrode it and named this host. The ruling stands on the record, unedited,
and the build treats the host as moveable: internal links are relative, the host is in
no sentence of copy, and the offer identifiers (`t1`…`t4`, `add-formats`,
`add-opinion`) are stable — so a printed code survives a move.

## Licences

- **Content** (`content/`, `docs/`) — CC BY 4.0
- **Build code** (`build.py`, `assets/`, `bin/`, `tools/`) — Apache-2.0

Independent work by SGit-AI.
