# Instructions for the implementing agent

Implement from this pack. Do not scrape the published design site.

## Authority and approved direction

1. The user's latest decisions in `IMPLEMENTATION-BRIEF.md` take precedence.
2. Use the supplied HTML, CSS, assets and component sheet as the visual source of truth.
3. The original brief is context and data constraints, not authority to undo later user changes.

The chosen direction is **01 / ABP first**, in the **01 Marketplace** navy-and-amber language. The store brand is **sgit / store**; RiskMandate is the ABP provider. This work is a design/layout/messaging handoff, not production-ready commerce software.

## Start here

- `site/index.html`: approved homepage, including the newly illustrated audience doors.
- `site/handback/components/index.html`: named component specimens at 390px and 1200px.
- `site/handback/index.html#review`: screen/variant directory.
- `site/handback/manifest.json`: component states, variant axes, source datasets and gaps.
- `IMPLEMENTATION-BRIEF.md`: build boundaries, current decisions and wiring checklist.

The HTML files are the source, not compiled framework output. The site has no build step. CSS and JS are shared local files, and the complete seven-file data snapshot is included. Port to the production repository's existing stack; do not introduce a new stack merely to match this prototype.

## Do not silently change

- Merchant branding, navy/amber palette, ABP-first message or the main headline.
- Prices, delivery clocks, deposit split or free/commercial licensing distinction.
- Disclosure placement above main and evidence chips on factual product claims.
- The explicit removal of read-not-run chips from audience navigation cards.
- Honest empty media/review states and missing-source labels.
- No input, textarea or select fields in the store; provider-owned pages collect buyer details.

Preserve V2 and V3. Do not overwrite or delete them when integrating V4.

## Production boundary

The JavaScript is demonstration code. Replace example-order controls, simulated provider hand-off and mock return states with the production contracts. Do not infer a successful payment from a URL, localStorage or this UI. Do not treat the example vault as the customer's private vault. No live provider credentials or private vault keys are included.

Where the original brief has alternatives, the pack preserves them for review. The user selected the overall ABP-first direction; they did not select winners for every A/B/C interaction axis. See the defaults and unresolved choices in the implementation brief.
