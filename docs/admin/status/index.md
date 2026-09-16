# What happened to each memo

**51 units done · 68 open · 22 waiting on the project lead · 8 memos.**


## 2026-09-16 — Stripe end to end, with their SKUs — and a customer even at 100% off (14/28 done)

Run the real Stripe purchase flow rather than an amount-only link, so a buyer handed a hundred-per-cent code still becomes a customer with an email. Then leak codes on specific journeys. And start capturing the work as units on a board.  
https://store.sgit.ai/admin/memos/2026-09-16-stripe-end-to-end/

- `TM-1` **Create the products in Stripe** — done — https://store.sgit.ai/admin/rails/stripe/ (v0.2.2)
- `TM-2` **Set customer creation to always, and prove it on a £0 order** — next
- `TM-3` **Create the promotion codes over the three coupons** — next
- `TM-4` **Enable promotion codes on every link, prefill where a code was leaked** — queued
- `TM-5` **Bring the return address onto this site** — done — https://store.sgit.ai/paid/t1/, https://store.sgit.ai/paid/t2/, https://store.sgit.ai/paid/t3/, https://store.sgit.ai/paid/t4/ (v0.3.0)
- `TM-6` **Stand up the checkout.session.completed webhook** — queued
- `TM-7` **Take one real £10 payment and read the receipt** — queued
- `TM-8` **Retire the browser-side discount arithmetic** — queued
- `TM-9` **SumUp — parked for the MVP** — done — https://store.sgit.ai/admin/rails/sumup/ (v0.2.6)
- `TM-10` **Write the two rails up as plans rather than intentions** — done — https://store.sgit.ai/admin/rails/, https://store.sgit.ai/admin/rails/stripe/, https://store.sgit.ai/admin/rails/sumup/ (v0.1.18)
- `TM-11` **Get the codes into Price.lookup_key, not just the description** — next
- `TM-12` **Re-export the product CSV whenever the dashboard changes** — next
- `TM-13` **Decide what a DELIVERY-only purchase means** — next
- `TM-14` **Caps on the hundred-per-cent coupon — ruled not needed** — done — https://store.sgit.ai/admin/rails/stripe/ (v0.2.4)
- `TM-15` **Bring SumUp back once Stripe has taken money** — queued
- `LC-1` **Decide which journeys carry a code** — done — https://store.sgit.ai/d/t1/, https://store.sgit.ai/d/t2/ (v0.3.1)
- `LC-2` **Print the code on the journey, with the link carrying it applied** — done — https://store.sgit.ai/d/t1/, https://store.sgit.ai/d/t2/ (v0.3.1)
- `LC-3` **Give every leaked code a cap and an expiry before it is printed** — done — https://store.sgit.ai/admin/rails/stripe/ (v0.2.4)
- `LC-4` **Keep the codes out of the built site except where they are meant to be** — done — https://store.sgit.ai/admin/try/ (v0.1.11)
- `TR-1` **Give the admin surface its own console UI** — done — https://store.sgit.ai/admin/ (v0.1.18)
- `TR-2` **Build this board** — done — https://store.sgit.ai/admin/work/ (v0.1.18)
- `TR-3` **Link the admin console from the main site's top-level nav** — done — https://store.sgit.ai/admin/ (v0.1.18)
- `TR-6` **Build the memo queue** — done — https://store.sgit.ai/admin/memos/ (v0.1.18)
- `TR-4` **Operationalise the review proposals** — in-progress
- `TR-5` **Capture the next review** — queued
- `TR-7` **Execute the memos in sequence, pushing often** — in-progress
- `TR-8` **Join the memos to what they became** — done — https://store.sgit.ai/admin/status/ (v0.3.6)
- `TR-9` **Write the walkthrough for the flow the store sells through** — next

## 2026-09-16 — £10, a commercial licence, and a name on the review (4/10 done)

The entry level goes to £10 and gains a commercial licence over the CC BY version anybody can download. And the two upper levels get a named reviewer, starting with the project lead, on a surface built for several.  
https://store.sgit.ai/admin/memos/2026-09-16-ten-pounds-and-a-licence/

- `PL-1` **Move the entry level from £5 to £10** — done — https://store.sgit.ai/d/t1/, https://store.sgit.ai/offers/, https://store.sgit.ai/ledger/ (v0.2.0)
- `PL-2` **Dual-licence the pack: CC BY public, commercial to the buyer** — done — https://store.sgit.ai/d/t1/, https://store.sgit.ai/offers/, https://store.sgit.ai/ledger/ (v0.2.0)
- `PL-3` **Research the cleanest way to grant it** — next
- `PL-4` **Put the licence text where the buyer reads it before paying** — queued
- `PL-5` **Record the price arc as one claim, not three** — queued
- `WD-1` **Build the reviewer register and a page per reviewer** — done — https://store.sgit.ai/who/ (v0.2.9)
- `WD-2` **Write the first reviewer's page** — done — https://store.sgit.ai/who/dinis-cruz/ (v0.2.9)
- `WD-3` **Let the buyer choose their reviewer at £500 and £1,500** — queued
- `WD-4` **Recruit the rest** — next
- `WD-5` **Say what happens when the chosen reviewer cannot take the work** — next

## 2026-09-16 — Five audiences, decoupled views, and the version the board can read (8/24 done)

The store does not qualify who is reading it. Five audiences, each with its own view and path and its own subset of the offers; the views driven by JSON and built as components rather than written out; and every vault — free ones included — carrying a version its reader’s board can read.  
https://store.sgit.ai/admin/memos/2026-09-16-five-audiences/

- `QB-1` **Decide what happens to the three buyer groups** — next
- `QB-2` **Write the five audiences down as data** — done — https://store.sgit.ai/are/ (v0.2.7)
- `QB-3` **Hidden, or shown differently — answered** — done — https://store.sgit.ai/are/investor/ (v0.2.7)
- `QB-4` **Build the five paths** — done — https://store.sgit.ai/are/founder/, https://store.sgit.ai/are/investor/, https://store.sgit.ai/are/exec/, https://store.sgit.ai/are/security/, https://store.sgit.ai/are/governance/ (v0.2.7)
- `QB-5` **Run a synthetic pass over the five paths** — queued
- `BR-1` **Specify what a board-readable cut actually is** — next
- `BR-2` **Decide who writes it, per vault** — next
- `BR-3` **Say on the site what is inside a vault** — next
- `BR-4` **Put it in the free vaults first** — queued
- `BR-5` **Re-read the entry level once it carries one** — queued
- `DV-1` **Read the two guidance sites properly and write down what applies** — in-progress
- `DV-2` **Settle: custom elements at runtime, or generated partials at build?** — next
- `DV-3` **Lift the view layer out of build.py into declared blocks** — queued
- `DV-4` **One JSON file per view, and a check that fails on an unused one** — queued
- `DV-5` **Prove it by adding the sixth audience as a file** — queued
- `TR-1` **Give the admin surface its own console UI** — done — https://store.sgit.ai/admin/ (v0.1.18)
- `TR-2` **Build this board** — done — https://store.sgit.ai/admin/work/ (v0.1.18)
- `TR-3` **Link the admin console from the main site's top-level nav** — done — https://store.sgit.ai/admin/ (v0.1.18)
- `TR-6` **Build the memo queue** — done — https://store.sgit.ai/admin/memos/ (v0.1.18)
- `TR-4` **Operationalise the review proposals** — in-progress
- `TR-5` **Capture the next review** — queued
- `TR-7` **Execute the memos in sequence, pushing often** — in-progress
- `TR-8` **Join the memos to what they became** — done — https://store.sgit.ai/admin/status/ (v0.3.6)
- `TR-9` **Write the walkthrough for the flow the store sells through** — next

## 2026-09-16 — Never leave the site — and write down who owns what (6/10 done)

The whole purchase, and everything after it, happens on store.sgit.ai. The store owns e-commerce; riskmandate.ai owns the products and the policies; the two read each other's files over CORS rather than sending each other's visitors away. Do the store first, then brief the other side.  
https://store.sgit.ai/admin/memos/2026-09-16-one-site-one-flow/

- `OS-1` **Narrow the no-network rule before the first cross-origin read** — done — https://store.sgit.ai/paid/t2/ (v0.3.3)
- `OS-2` **Move the post-sale page onto this site** — done — https://store.sgit.ai/paid/t1/, https://store.sgit.ai/paid/t2/, https://store.sgit.ai/paid/t3/, https://store.sgit.ai/paid/t4/ (v0.3.0)
- `OS-3` **Embed the bought vault on the page they land on** — done — https://store.sgit.ai/paid/t2/, https://store.sgit.ai/paid/t3/, https://store.sgit.ai/paid/t4/ (v0.3.3)
- `OS-4` **Read riskmandate.ai's manifest over CORS and close the last hop** — next
- `OS-5` **Make the store feel like a shop** — queued
- `OS-6` **Re-run the synthetic buyer who got confused** — queued
- `WO-1` **Publish the ownership boundary as a page both agents can read** — done — https://store.sgit.ai/boundary/ (v0.3.2)
- `WO-2` **Brief the RiskMandate team to do the reverse** — done — https://store.sgit.ai/boundary/#the-brief-addressed-to-the-riskmandate-team (v0.3.2)
- `WO-3` **Mark the files that are on the wrong side** — done — https://store.sgit.ai/boundary/#debt-marked-as-debt (v0.3.2)
- `WO-4` **Agree the contract for the shared files** — next

## 2026-09-16 — One table, five columns, and the free one first (5/6 done)

The comparison table every pricing page has and this store does not: features down the left, five columns across — free, £10, £50, £500, £1,500 — and a cell for every one. New page, so it can be reviewed before it is wired in.  
https://store.sgit.ai/admin/memos/2026-09-16-the-comparison-table/

- `CT-1` **Decide what every cell is allowed to say** — done — https://store.sgit.ai/compare/ (v0.2.8)
- `CT-2` **Write the feature list as data** — done — https://store.sgit.ai/compare/ (v0.2.8)
- `CT-3` **Settle whether £10 includes a vault** — done — https://store.sgit.ai/compare/ (v0.2.8)
- `CT-4` **Decide what support means, and who answers** — next
- `CT-5` **Build the page, free column first** — done — https://store.sgit.ai/compare/ (v0.2.8)
- `CT-6` **Render it as a PDF** — done — https://store.sgit.ai/compare/#the-brochure, https://store.sgit.ai/assets/downloads/abp-comparison.pdf (v0.3.12)

## 2026-09-16 — Make a product page feel like a product page (4/6 done)

Description, price and buy button, a carousel of screenshots of what you actually get, specs and SKUs, and a place for reviews. Built as prototypes first, then wired in — and eventually switchable by audience, the way a product has editions.  
https://store.sgit.ai/admin/memos/2026-09-16-product-pages/

- `PP-1` **Prototype one product page in the lab** — done — https://store.sgit.ai/lab/product/ (v0.3.4)
- `PP-2` **Find out which screenshots exist and which have to be taken** — done — https://store.sgit.ai/lab/product/ (v0.3.4)
- `PP-3` **Put a version on every piece of product media** — next
- `PP-4` **Print the specs and the SKUs** — queued
- `PP-5` **Add the review section, and say it is empty** — done — https://store.sgit.ai/lab/product/#reviews (v0.3.4)
- `PP-6` **Make the page switchable by audience** — done — https://store.sgit.ai/lab/product/ (v0.3.4)

## 2026-09-16 — The homepage sells — and the work has been done before (13/25 done)

A shop front built for a laptop turned round at an event: who are you, here is your thing, buy it. Delivery times on every level. And the correction that matters most — this work has been done many times; what has not happened is a sale through this store, and the site has been conflating the two.  
https://store.sgit.ai/admin/memos/2026-09-16-the-homepage-sells/

- `SF-1` **Move the mechanism and the meta off the front page** — next
- `SF-2` **Put the four products up front, with prices and delivery** — next
- `SF-3` **Build the who-are-you entry** — done — https://store.sgit.ai/, https://store.sgit.ai/are/ (v0.2.7)
- `SF-4` **Make a discount code a link, never a thing to type** — next
- `SF-5` **Add the sections a shop front has** — queued
- `SF-6` **Test it the way it will be used** — queued
- `SF-7` **Rename level four to match the product** — done — https://store.sgit.ai/d/t4/ (v0.2.4)
- `DT-1` **Put a delivery estimate on every level** — done — https://store.sgit.ai/d/t1/, https://store.sgit.ai/d/t2/, https://store.sgit.ai/d/t3/, https://store.sgit.ai/d/t4/ (v0.2.0)
- `DT-2` **Replace the it-has-never-run non-answer about timing** — done — https://store.sgit.ai/paying/, https://store.sgit.ai/ledger/ (v0.2.0)
- `DT-3` **Say what the constraint really is** — done — https://store.sgit.ai/d/t4/ (v0.2.0)
- `DT-4` **Start measuring the moment there is something to measure** — queued
- `WH-1` **Re-read every claim against “the work has been done”** — done — https://store.sgit.ai/ledger/ (v0.2.1)
- `WH-2` **Link the published evidence** — done — https://store.sgit.ai/ (v0.2.1)
- `WH-3` **Narrow the disclosure to what is genuinely undone** — done — https://store.sgit.ai/, https://store.sgit.ai/d/t3/, https://store.sgit.ai/d/t4/ (v0.2.1)
- `WH-4` **Put a name and a track record on the delivery** — next
- `WH-5` **Decide what to do about testimonials** — queued
- `TR-1` **Give the admin surface its own console UI** — done — https://store.sgit.ai/admin/ (v0.1.18)
- `TR-2` **Build this board** — done — https://store.sgit.ai/admin/work/ (v0.1.18)
- `TR-3` **Link the admin console from the main site's top-level nav** — done — https://store.sgit.ai/admin/ (v0.1.18)
- `TR-6` **Build the memo queue** — done — https://store.sgit.ai/admin/memos/ (v0.1.18)
- `TR-4` **Operationalise the review proposals** — in-progress
- `TR-5` **Capture the next review** — queued
- `TR-7` **Execute the memos in sequence, pushing often** — in-progress
- `TR-8` **Join the memos to what they became** — done — https://store.sgit.ai/admin/status/ (v0.3.6)
- `TR-9` **Write the walkthrough for the flow the store sells through** — next

## 2026-09-16 — Describe your agent — the page that gets used in the room (5/8 done)

A free page where somebody builds their agent by clicking or dragging capabilities onto it, and what comes out is the definition of what that agent could do. It is the front half of the £500 level, given away, and it is the page the project lead expects to use most in conversation.  
https://store.sgit.ai/admin/memos/2026-09-16-describe-your-agent/

- `DA-1` **Get the real capability vocabulary** — done — https://store.sgit.ai/lab/agent-canvas/#the-vocabulary (v0.3.5)
- `DA-2` **Prototype the canvas — agent in the centre, capabilities around it** — done — https://store.sgit.ai/lab/agent-canvas/ (v0.3.5)
- `DA-3` **Prototype the sequence — one question at a time** — done — https://store.sgit.ai/lab/agent-sequence/ (v0.3.5)
- `DA-4` **Decide whether a capability has degrees** — next
- `DA-5` **Emit the definition as a document a model can act on** — done — https://store.sgit.ai/lab/agent-canvas/ (v0.3.5)
- `DA-6` **Write the prompt that turns the definition into a vault** — queued
- `DA-7` **Say on the page what it is and is not** — done — https://store.sgit.ai/lab/agent-canvas/#what-this-produces (v0.3.5)
- `DA-8` **Put it in front of the £500 level and in the walk-through flow** — queued

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
