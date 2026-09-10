# SGit-AI__Website__Store

The source for **[store.sgit.ai](https://store.sgit.ai/)** — the estate's first site
that carries a price. Six offers: four tiers with a printed code behind them, and two
add-ons that are listed and not yet buyable.

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

## Layout

```
  .github/workflows/   validate → tag → deploy
  admin/build/         version.txt (owns the version) and validate.sh (the gate)
  assets/              site.css, site.js, favicon.svg — no web fonts, no CDN
  bin/                 bump.py — the only thing that moves the version
  content/             the markdown sources, with YAML front-matter
  data/                offers.yml (the ONLY place a price exists), claims.yml,
                       pack.yml (the dev-pack manifest), releases.json
  docs/                THE BUILT OUTPUT. GitHub Pages serves this. COMMITTED
  tools/               check_site.py, secret-scan.sh, check-js.sh
  build.py             the whole build system. No dependencies
```

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
