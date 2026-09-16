# sgit / store — V4 implementation briefing

## What this pack is

A complete visual and messaging handoff for the team implementing store.sgit.ai. It contains the actual HTML/CSS/JS source of the design prototype, all referenced image assets, seven canonical data files, component specimens, screen variants, implementation notes and the original supplied brief. Nothing needs to be scraped or downloaded from the design site.

This is design work. The prototype interactions communicate intent; the production team owns commerce, state, integrations, validation and operational behaviour.

## Latest user decisions

- Use **01 / ABP first** as the direction.
- Preserve the **01 Marketplace** look: navy, amber, pale blue, strong sans-serif type, clear prices.
- Keep **sgit / store** as the merchant brand; this is the store for RiskMandate's ABPs.
- Keep the core headline **Give your AI agent a clear mandate.**
- Say immediately that what is sold today is an **Agent Behaviour Policy (ABP)** from RiskMandate.
- Keep the purchase journey self-contained; do not require a RiskMandate-site detour.
- Prioritise design, layout and messaging. Another agentic team will wire it up.
- The V4 design publication is now public.
- Improve the top **What brings you here?** section with imagery for each audience and remove its **read, not run** badges. This is implemented in this pack. The original brief's badge-on-every-card instruction is superseded for these audience-navigation cards only.

## Find the files

| Location | Purpose |
|---|---|
| `site/index.html` | Homepage entry point |
| `site/handback/index.html` | Same homepage with relative references within handback |
| `site/handback/tokens.css` | Every declared design token; new audience tokens use `--aud-*` |
| `site/handback/assets/system.css` | Shared component and responsive CSS |
| `site/handback/assets/app.js` | Prototype interactions; replace production-sensitive parts |
| `site/handback/assets/data.js` | Local data snapshot for the prototype, no fetch required |
| `site/handback/data/*.json` | Seven unchanged canonical datasets |
| `site/handback/assets/marketplace.png` | Approved hero artwork |
| `site/handback/assets/audience-strip.png` | New five-part audience artwork, 2172 × 724 |
| `site/handback/assets/shots/` | All seven supplied real product screenshots |
| `site/handback/components/` | Component sheet, type studies and individual specimens |
| `site/handback/screens/` | All design screens and named variants |
| `site/handback/notes/` | Screen-specific decisions, differences and limitations |
| `site/handback/manifest.json` | Machine-readable design inventory |
| `briefing/original/` | Original brief, README and handback schema for context |
| `FILE-MANIFEST.json` | SHA256, size and purpose of each packed source file |

Open `site/index.html` in a browser, or serve the `site` directory with a simple static server. There is no install, build or framework requirement. All assets are local. Fonts are system stacks. Print buttons use browser printing.

## Visual system

- Navy `#142c42`; amber `#f5ae42`; pale-blue `#edf3f8`; body ink `#142632`; muted ink `#536573`.
- Arial/Helvetica remains the actual screen typeface. The component sheet also demonstrates a grotesk stack and Georgia headings; the user has not separately approved either typography alternative.
- Prices on offer cards are **42px**, including phone width.
- Four offer cards use the same anatomy: level/delivery, short name, exact description, price, payment split, delivery clock, evidence chip, action.
- One simple outlined ABP mark provides product identity. It is interface typography, not an external stamp.
- Design targets are 390px and 1200px. Existing media-query thresholds are 700px and 1050px.
- Disclosure remains above main. The quiet version label identifies this as V4; replace it with the production release identifier during integration.

## New audience section

Five image-led doors: Founder, Investor, C-level executive, Security professional, Risk & governance. Every card links to its matching audience page. Short text establishes the perspective without repeating the full rationale. No evidence badge is shown on these navigation choices.

Artwork is one coherent AI-generated strip of conceptual objects, left to right: laptop/launch arrow; folio/growth bars; executive chair/document; shield/magnifier; policy binder/checklist. These are decorative metaphors, not customers, endorsements or named reviewers. The `<img>` is decorative (`alt=""`), while the link text supplies the accessible name.

The CSS displays one fifth of the strip per card using `width:500%` and horizontal offsets. It is centred vertically within a 64px square. You can keep this technique or export individual crops without redrawing the art. The original strip is included. Desktop uses five columns; intermediate widths use three; phone width uses a horizontal snap row with a partial next card visible. Maintain keyboard navigation and visible focus.

## Screen map and choices

| Area | Files | Axis / current homepage routing |
|---|---|---|
| Pricing | `screens/pricing/A.html`, `B.html`, `C.html` | Sticky-column scroll / two-column picker / expandable feature rows. Header routes to A. |
| Audiences | `screens/audiences/A.html`, `B.html`, `C.html` plus five named pages | Separate pages / persistent switch / local lens. Homepage uses named pages, i.e. A. |
| Policy picker | `screens/picker/A.html`, `B.html`, `C.html` | Till below evidence / in header / persistent dock. Homepage routes to C. |
| Product | `screens/product/A.html` | Description/media left, sticky buy rail right; level × policy identity |
| Cart | `screens/cart/A.html` | Empty, populated, deposits, applied-code example |
| Checkout | `screens/checkout/A.html` | Due-now/balance, provider notice and simulated hand-off |
| Post-purchase | `screens/post-purchase/A.html`, `B.html`, `C.html` | Receipt strip / split rail / vault-first. Demo return uses A. |
| Generic | `screens/generic/A.html` | Reading-column template and disclosures |
| Describe agent | `screens/describe-your-agent/A.html`, `B.html` | Click/drag canvas / sequential capability interview |
| Reviewer | `screens/reviewer/A.html` | List-ready person/responsibility anatomy; identity missing |
| Ledger | `screens/ledger/A.html` | Source-linked subset; not an invented copy of the entire live ledger |
| Print | `screens/pricing/print.html`, `screens/post-purchase/receipt.html` | Comparison brochure / sample order receipt |
| Headline studies | `screens/hero-headline/short.html`, `long.html` | Additional studies only; main homepage retains approved headline |

These routing defaults are not a claim that the user separately chose all variant winners. Keep alternatives available for review until that decision is made.

## Product facts to preserve

| Level | Price | Delivery | Payment |
|---|---:|---|---|
| 01 — The pack, downloaded | £10 | Immediately on payment | £10 now |
| 02 — A working vault | £50 | 1 to 2 days from payment | £50 now |
| 03 — Corrected for your situation | £500 | 1 to 3 days from reply | £100 now, £400 on delivery |
| 04 — Two sessions and a custom vault | £1,500 | 1 to 5 days from reply | £300 now, £1,200 on delivery |

The free comparison column comes first. Public material is CC BY and requires attribution. Paid levels supply a commercial licence over the same material. Level 04 includes professional sign-off; do not extend that claim to level 03. Add-ons are not active purchasable offers: use their supplied partial/absent states. Prices and all qualified comparison cells come from the JSON files, not this prose.

## What to wire

1. **Canonical data:** replace the frozen local snapshot with the production repository's authoritative data model while keeping the design's field mapping. Reconcile current prices rather than trusting a visual screenshot.
2. **Picker:** supply the policy-to-capability join, tool/scope fields, scenario records, grant dates, shortfall and side-effect evidence. The supplied pack has aggregate counts only. Do not fabricate joins or infer missing values from counts.
3. **Product:** preserve selected policy and level. Audience changes only the explanation, never SKU or price. Complete specifications for levels other than 02.
4. **Order:** replace example-order controls and demo discount handling. Maintain no-form purchase UX and one level per selected policy. Generate the real order reference through the production contract.
5. **Provider hand-off:** integrate the actual payment products, including distinct deposit and delivery amounts. The prototype does not charge anything. A real £0 order follows the provider customer-record route.
6. **Payment return:** validate payment/provider state using the production architecture. Populate receipt, dates, balance and next steps from the real order. Show the purchased policy, not a hardcoded template.
7. **Delivery:** connect real downloads with byte size and SHA256 and the buyer's actual vault. Label any temporary public example in its first sentence. Keep private keys out of static HTML, URLs, analytics and source assets.
8. **People/evidence:** supply the actual named reviewer record, contact route and review approval. The design does not assert human approval has happened.
9. **Operational copy:** remove design preview notices only after corresponding functionality is real. Do not remove honest product limitations.

## Prototype-only behaviour to replace or remove

`assets/app.js` stores example cart state using `sgit-v4-*` localStorage keys. Buttons labelled Load example order, Show 100% code applied, Show £0 order, and the simulated provider dialog are review aids. The sample `discount=sample-100` path is a design state, not a production promotion. Payment-return screens and sample receipt values are not proof of purchase.

The example vault is a local reading shell with aggregate data and labelled unavailable file contents. It does not connect to a live vault. If porting an app that runs inside a blob URL, follow the original brief's asset-loading bridge requirements; this mock is the surrounding store surface.

## Content gaps and empty states

Keep the four missing product media slots labelled until the specified images exist. No customer reviews, star ratings, reviewer identities or third-party marks have been fabricated. The one/several-review specimens are placeholders, not testimonials. Human-review status, exact delivery dates and download hashes remain placeholders until sourced. The two typography alternatives and supplied headline alternatives are design studies, not approved production defaults.

## Verification before production

The design pack passed static link/anchor checks, field prohibition checks, source-data identity checks, token checks and JavaScript syntax checks. It has not passed browser visual QA.

Before launch, review the actual port at 390px and 1200px, 200% text size, keyboard-only navigation, image loading, mobile picker sheet focus, comparison modes, reduced motion and print layout. Then validate the real commerce and vault contracts separately. Check totals/deposits and delivery clock origins against authoritative production data. Ensure no example controls or placeholder identities look like live operational promises.

## Handoff completeness

All referenced design assets are local. `FILE-MANIFEST.json` can verify integrity. The existing source ZIP in `site/` is included because the design links to it. The new implementation pack itself is intentionally not nested recursively inside its own `site` folder. No credentials, private keys, customer records or external dependencies are required to inspect these designs.
