# The work

The units of work for this store, as a board. Two levels, like the board this one is modelled on at sgraph.ai/en-gb/dev/workstreams/: the top board has one card per workstream and the column it sits in is derived from its own tasks, and opening a card gives that workstream's tasks in the same four columns. A workstream is never dragged — it moves because a task in it moved, which means the summary cannot disagree with the detail.

**16 workstreams · 92 units of work · 54 not done.**


## Take money at all — next

No payment rail is live. Every checkout_url in data/checkout.yml is empty, so the store can be walked end to end and cannot be bought from. This is the workstream that ends that, and the shape of it changed on 16 September: the rail is no longer an amount-only link, it is Stripe's own catalogue and a real customer record behind every order including the free ones.

- **TM-1 · Create the products in Stripe** — `done` — Done by the project lead on 16 September. Six products, GBP, and the shape is theirs rather than the one this plan first guessed: the two upper levels are a DEPOSIT and a DELIVERY that sum to the price, so a buyer paying in full adds both lines and a buyer starting adds one. That is the store's own “a fifth now and the rest on delivery” as two rows instead of a rule somebody has to apply. The dashboard's CSV export is committed and the build reconciles against it every release.
- **TM-2 · Set customer creation to always, and prove it on a £0 order** — `next` — The single setting most likely to be missed. Without it a hundred-per-cent order completes, the buyer sees a confirmation, and no customer record exists — which is the exact opposite of why this rail was chosen. Proof is a Customer visible in the dashboard after one free order, not a screenshot of the toggle.
- **TM-3 · Create the promotion codes over the three coupons** — `next` — The coupons are done — 25, 50 and 100 per cent, created 16 September, all once, all reconciling against the percentages this store honours. Zero promotion codes exist, and that is the gap. A coupon carries the percentage; a promotion code is the string a person is handed and the thing a link can carry pre-applied. The seven strings in data/discounts.yml map onto these three — five at a hundred per cent, kept separate so an order record says which one produced it.
- **TM-4 · Enable promotion codes on every link, prefill where a code was leaked** — `queued` — A link with the field switched off refuses a valid code with no explanation and the buyer blames themselves. Where a page publishes a code as part of a journey, the link on that page carries it already applied.
- **TM-5 · Bring the return address onto this site** — `done` — Shipped in v0.3.0. The success address is this site's own page for the level, so there is nothing to settle with another team. The two parameters are unchanged; what moved is the origin.
- **TM-6 · Stand up the checkout.session.completed webhook** — `queued` — The step that unblocks a first paid order at £50, £500 and £1,500. Listen to the session, not the payment: a hundred-per-cent order creates no charge, so a handler keyed on a succeeded payment sees every paid order and none of the free ones. _Blocked on: Runs off this site. This site is static and opens no connection._
- **TM-7 · Take one real £10 payment and read the receipt** — `queued` — Every sentence on the rails page about what a receipt says is unverified. This is the task that makes them checkable. _Blocked on: TM-1 and TM-6._
- **TM-8 · Retire the browser-side discount arithmetic** — `queued` — A code is honoured in the browser today and the page says it is a demonstration. Once a promotion code exists on the rail there are two implementations of one rule, and the browser one can be edited by the person it is discounting. _Blocked on: TM-3._
- **TM-9 · SumUp — parked for the MVP** — `done` — Taken off the store on 16 September. The finding that produced this task — that check_checkout_links pinned every destination to Stripe's hosts and would have refused a SumUp URL with a message about Stripe — is now moot rather than fixed, and stays written down because it will be true again the day the rail comes back. The plan is kept at /admin/rails/sumup/ rather than deleted.
- **TM-10 · Write the two rails up as plans rather than intentions** — `done` — Shipped in v0.1.18 at /admin/rails/stripe/ and /admin/rails/sumup/, generated from data/admin/rails.json.
- **TM-11 · Get the codes into Price.lookup_key, not just the description** — `next` — The six codes exist as ABP-T1, ABP-T3-DEPOSIT and the rest — in the price description, because the dashboard's product view surfaces no lookup key. That works for a person reading the dashboard. Price.lookup_key is a different field, it exists on the API, and it is the one a webhook uses to map a line item back to a level. Without it the handler has a product id and a free-text string, which is workable and is not the same as queryable.
- **TM-12 · Re-export the product CSV whenever the dashboard changes** — `next` — The reconciliation reads a committed export, because this site opens no connection and that rule is not moving. It catches a price changed here and not there, which is the direction that happens; it goes stale in the other direction until somebody re-exports. That is the known weakness and it is written on the page rather than left to be discovered.
- **TM-13 · Decide what a DELIVERY-only purchase means** — `next` — The split makes a new thing possible that no page describes: somebody buying the delivery line without ever having bought the deposit. Either the pages say what that is, or the link only ever offers the pair.
- **TM-14 · Caps on the hundred-per-cent coupon — ruled not needed** — `done` — Ruled on 16 September: no cap, and the reasoning is recorded rather than the concern being dropped. Purchases are managed directly, so a redemption is seen rather than discovered in a total. Abuse at a volume worth doing is abuse at a volume that shows. And what the code skips paying for is already published free — it removes a payment for material anybody could download, and it does not remove the work at the upper levels, which a person does and would notice. The gate now reports the state every release instead of failing on it.
- **TM-15 · Bring SumUp back once Stripe has taken money** — `queued` — The argument for running two rails is a good one and it is preserved on the parked plan. It stops being hypothetical the day the first rail has taken a real payment, which is the point at which there is something to compare against. _Blocked on: TM-7 — a first real payment._


## The entry price, and what it buys — next

Two reviewers independently said the entry level reads as a commodity at £5 — one human partner and one invented buyer who had never met them. The answer ruled on 16 September is not a larger number for the same thing: the level goes to £10 and gains a commercial licence, which is a different product rather than a dearer one.

- **PL-1 · Move the entry level from £5 to £10** — `done` — Shipped in v0.2.0. £10, with all three moves of the price kept on the page.
- **PL-2 · Dual-licence the pack: CC BY public, commercial to the buyer** — `done` — Shipped in v0.2.0. The public files stay CC BY; the buyer gets a commercial licence over the same material. The wording is not drafted and the ledger says so.
- **PL-3 · Research the cleanest way to grant it** — `next` — The licence is to the buyer and does not name them, which is the interesting part: a grant to an unnamed holder has to be worded so it is clearly a grant and not a public re-licence of the same bytes. Open questions: does it travel with the file or with the order reference, what happens on resale, and does it survive the buyer's company changing name.
- **PL-4 · Put the licence text where the buyer reads it before paying** — `queued` — Not in the pack, not in a footer. The difference between the free version and the paid one is now the main thing the entry level sells, so it belongs on the card and on the level page above the fold. _Blocked on: PL-2._
- **PL-5 · Record the price arc as one claim, not three** — `queued` — The ledger already carries £10 → £5 with the card-fee arithmetic. Adding £5 → £10 as a separate claim would leave a reader assembling the story from three entries. One claim, three dates, all the reasoning kept. _Blocked on: PL-1._


## Who runs the review — next

The two upper levels are somebody's work and the store has never said whose. A buyer spending £1,500 on a security review is buying a person, and the site asks them to buy it from nobody in particular. First reviewer named 16 September; the surface is built for several, because there will be.

- **WD-1 · Build the reviewer register and a page per reviewer** — `done` — Shipped in v0.2.9 as data/reviewers.yml and /who/. Built for a list on the day it had one name on it — adding the second is adding a record; the page, the twin, the register entry and the links from the level pages are generated.
- **WD-2 · Write the first reviewer's page** — `done` — Shipped in v0.2.9 at /who/dinis-cruz/. Every line read off open-source.sgit.ai's published author page and the vault catalogue, both named on the page with the date they were read. No count of years: the published record starts in 2008 and a reader can do that arithmetic and check every step of it.
- **WD-3 · Let the buyer choose their reviewer at £500 and £1,500** — `queued` — A selection, carried in the order reference the way the shape already is. With one reviewer it is a statement rather than a choice, and it is already on both level pages, because what it says is that there is a name behind the work. _Blocked on: WD-4 — a second name._
- **WD-4 · Recruit the rest** — `next` — The project lead is contacting security professionals they know and negotiating rates, so they can take some of the work at £500 and £1,500 and eventually above. The page is worth being listed on now, which was the whole reason WD-2 came first. Adding one is adding a record to data/reviewers.yml; the frozen list in the gate moves with it, on purpose, so a reviewer cannot appear by accident.
- **WD-5 · Say what happens when the chosen reviewer cannot take the work** — `queued` — Both upper levels already disclose they have never been sold. A named reviewer adds a second thing that can fail and the pages do not cover it. _Blocked on: WD-3._


## Leak the codes on purpose — done

Seven discount codes exist and only the walkthrough page prints any of them. The ask is to publish codes on the main site on specific journeys — a code is a reason to complete a purchase, and a purchase is how a visitor becomes a customer record.

- **LC-1 · Decide which journeys carry a code** — `done` — Answered by what the code can reach rather than by where it sits. The journeys are the two level pages the code applies to — /d/t1/ and /d/t2/ — because a code at the end of a level page discounts a decision somebody is in the middle of making, and a code on a first screen discounts one nobody has made yet. Not the home page.
- **LC-2 · Print the code on the journey, with the link carrying it applied** — `done` — Shipped in v0.3.1. The code is printed and the same code is a one-click link that applies it and lands on the shop with the two prices repainted.
- **LC-3 · Give every leaked code a cap and an expiry before it is printed** — `done` — Superseded by the ruling of 16 September: no caps, because purchases are managed directly and what this code gives away is already published free. What replaces a cap is stronger than one — the code cannot reach a level that is somebody's time, held by check_a_leaked_code_cannot_buy_somebody_s_day, which is absolute.
- **LC-4 · Keep the codes out of the built site except where they are meant to be** — `done` — check_discount_codes_are_not_printed fails the release if a code appears anywhere outside /admin/. Extending it to a named set of journeys is a change to that check, not a hole in it.


## Close the loop after payment — next

The store hands a buyer to riskmandate.ai and promises a person within 24 hours. Nothing carries the sale to that person, and nobody owns the mailbox it would arrive in.

- **CL-1 · Name the owner of the follow-up mailbox** — `next` — Open since the 24-hour promise was written. It is one name and it is blocking nothing technical, which is exactly why it has stayed open.
- **CL-2 · Route the level-3 brief back to a person** — `queued` — At £500 the buyer writes a brief. It is a file they keep and there is no route by which the person doing the work receives it. _Blocked on: CL-1._
- **CL-3 · Verify the handover contract against a real landing** — `queued` — The store builds the address riskmandate.ai's pages document. Nobody has watched a real buyer arrive on one. _Blocked on: TM-5, TM-7._


## Keep the record — in-progress

The reviews, the ledger, the console and this board. The part of the store that exists so a decision taken today can be argued with in a month.

- **TR-1 · Give the admin surface its own console UI** — `done` — Shipped in v0.1.18. Rail, counts read from the same files the pages are built from, and a shell that is not the shop's.
- **TR-2 · Build this board** — `done` — Shipped in v0.1.18 at /admin/work/, modelled on the workstreams board at sgraph.ai. Three boards: this one authored, and two generated from the reviews and the ledger so they cannot drift.
- **TR-3 · Link the admin console from the main site's top-level nav** — `done` — It was reachable only by knowing the address. Public and unadvertised was the intent; unfindable by the people building it was not.
- **TR-6 · Build the memo queue** — `done` — Shipped in v0.1.18 at /admin/memos/. A memo is kept verbatim, read into a brief, broken into units of work, and the units appear on the board carrying the memo they came from. Set as the process by the memo it is generated from, and applied backwards to the two before it.
- **TR-4 · Operationalise the review proposals** — `in-progress` — Eighteen proposals across two reviews, each with a stance. The ones marked do-now are units of work and were not tracked anywhere until this board existed. The generated proposals board is the join.
- **TR-5 · Capture the next review** — `queued` — The register takes a file and a line. The interesting one to run next is a second synthetic pass after the rail is live, because every finding in the first one stopped at a checkout that did not exist. _Blocked on: TM-7._
- **TR-7 · Execute the memos in sequence, pushing often** — `in-progress` — Set as the working method: catalogue each memo exactly, plan, then execute bit by bit and keep pushing to production. Minor versions for most of it; a major version where a change is big enough to deserve one.


## Qualify who is reading — next

The store shows four paid levels identically to whoever arrives, which sells to everybody and therefore to nobody. Five audiences — founders, investors, C-level executives, cybersecurity professionals, and risk and governance or GRC professionals — each with its own path and its own subset of the offers. The front door stays exactly as it is.

- **QB-1 · Decide what happens to the three buyer groups** — `next` — The store already has three, cut by situation rather than by role, each with a page in the nav and in the sitemap and claims citing them. Five new ones is a replacement and the memo does not say whether the old three are retired, re-cut or kept alongside. Nothing else in this workstream can start without the answer.
- **QB-2 · Write the five audiences down as data** — `done` — Shipped in v0.2.7 as data/audiences.yml. One record per audience: who they are, what they arrive asking, which level the view leads with, which are quieted, and the one published vault that speaks to them.
- **QB-3 · Hidden, or shown differently — answered** — `done` — Shown differently. Nothing is hidden from anybody. Each view leads with the level that usually fits the question somebody arrived with and quiets the ones that usually do not; every level stays present, reachable and priced on every view. The alternative would have meant this site showing different catalogues to different readers, which is a thing that has to be said out loud before it is built. check_the_five_audiences_hide_nothing is what stops quiet quietly becoming absent — that change is one CSS rule away and would look like a tidy-up in a diff.
- **QB-4 · Build the five paths** — `done` — Shipped in v0.2.7. Five paths at /are/, generated — a sixth audience is a file.
- **QB-5 · Run a synthetic pass over the five paths** — `queued` — Named in the memo as the feedback loop for this work. The method exists and has been run once; the second run is the one that tells us whether it generalises. _Blocked on: QB-4._


## The version the board can read — next

“Can I have this in a form my board can read?” Every vault should already contain one — the policy re-cut for the people who have to sign it off. Not a paid extra and not an add-on: every vault, including the ones anybody can download for nothing.

- **BR-1 · Specify what a board-readable cut actually is** — `next` — Length, what it leads with, what it leaves out, and what a reader is expected to do with it. It is the whole deliverable, so specifying it badly is worse than not shipping it.
- **BR-2 · Decide who writes it, per vault** — `next` — Fifteen shapes. Generated, written once per shape, or written per sale — the answer changes what the entry level costs to fulfil and therefore whether £10 is the right number.
- **BR-3 · Say on the site what is inside a vault** — `next` — The memo's own diagnosis: the store never explains this well. It is the gap the board-readable cut sits in, and it is worth closing on its own even if BR-1 takes a while.
- **BR-4 · Put it in the free vaults first** — `queued` — “Including the ones you can download for free.” Doing the free ones first is the harder order and the right one: it proves the cut is generated rather than hand-finished for a paying customer. _Blocked on: BR-1, BR-2._
- **BR-5 · Re-read the entry level once it carries one** — `queued` — A £10 pack that contains a version the board can read is a different argument from a £10 pack that does not. It also earns a row on the comparison table, which is where the difference between the levels is now legible — and it is kept off that table until it exists. _Blocked on: BR-4, PL-2._


## Decouple the views — in-progress

Five audiences across the surfaces they touch is not writeable by hand. The store is already data-driven at the content layer and hand-written at the view layer, and that seam is what the memo is pointing at: JSON configuration, components, and the same generate-and-check discipline coding.sgit.ai and nfrs.sgit.ai both teach.

- **DV-1 · Read the two guidance sites properly and write down what applies** — `in-progress` — coding.sgit.ai measures its conventions by counting the code rather than asserting them; nfrs.sgit.ai runs one rule — link the measurement, never restate it, generate or date every number — and fails its build otherwise. This store already runs both of those; what is not yet written down is which of their component conventions apply to a site that ships no framework.
- **DV-2 · Settle: custom elements at runtime, or generated partials at build?** — `next` — This is the decision the rest depends on and it has a hard constraint on it. Every selling page on this site opens no connection and a build check fails the release if one does. Components that fetch their own configuration would negotiate with that rule. Components that are rendered at build from the same JSON would not, and would still give the memo what it asked for.
- **DV-3 · Lift the view layer out of build.py into declared blocks** — `queued` — Three thousand lines, of which the page shells and the block renderers are the part five audiences would multiply. Extract those first; leave the markdown renderer and the gate alone. _Blocked on: DV-2._
- **DV-4 · One JSON file per view, and a check that fails on an unused one** — `queued` — The store's own idiom, applied to views: a register with no file and a file with no register entry both fail the build, the way the reviews already do. _Blocked on: DV-3._
- **DV-5 · Prove it by adding the sixth audience as a file** — `queued` — The acceptance test for the whole workstream. If adding an audience is still a code change, the refactor did not land. _Blocked on: DV-4, QB-4._


## Never leave the site — next

A buyer does the whole thing here — catalogue, cart, payment, receipt, and the vault they just bought, embedded on the page they land on. Today the store hands them to another domain at the moment they pay, which a synthetic buyer called out as the point they got confused.

- **OS-1 · Narrow the no-network rule before the first cross-origin read** — `done` — Done in v0.3.3, with a consumer rather than on spec. The no-network rule was narrowed a second time to admit the vault embed on the page a buyer lands on. The half that carries the claim did not move: every page that SELLS anything opens nothing at all, and there is now a check that refuses an embed on one by name. Five deliberate breaks run.
- **OS-2 · Move the post-sale page onto this site** — `done` — Shipped in v0.3.0. /paid/t1/ to /paid/t4/ are on this site: the order reference filled from the browser that placed it, what was bought, when it arrives, who does it, what done looks like and how to check it. Every page noindex, and correct with no script at all — a browser that blocked it still reads what happens next.
- **OS-3 · Embed the bought vault on the page they land on** — `done` — Shipped in v0.3.3. The three levels that are a vault embed a published one on the page after payment, labelled an example, not yours in its first sentence — because at the moment somebody pays there is nothing of theirs to show yet, and a page that pretended otherwise would be lying at the one moment a buyer is paying most attention.
- **OS-4 · Read riskmandate.ai's manifest over CORS and close the last hop** — `next` — Blocked on the brief, and now for a named reason. Their manifest exists — fifteen entries with bytes and a sha256 — and it lives inside a JavaScript const DIST = /*__DIST__*/[…] in paid-t1.html, not at a JSON address. Reading it means regex-ing their JS out of their HTML at runtime, which is exactly the fragility item one of the brief on /boundary/ asks them to remove. CORS is confirmed; the shape is the gap. _Blocked on: The RiskMandate team publishing a manifest as JSON — item 1 of the brief._
- **OS-5 · Make the store feel like a shop** — `queued` — “Fundamentally like Amazon.” More detail is coming from the project lead. Several pages here are an essay with a buy button under them, which is the gap. _Blocked on: More information from the project lead._
- **OS-6 · Re-run the synthetic buyer who got confused** — `queued` — The finding has a name and a persona attached. The same walk, after the flow is one site, is the only way to know this worked. _Blocked on: OS-2, OS-3._


## Who owns what — next

Two sites, one purchase. The store owns e-commerce — cart, workflow, redirections, payments. riskmandate.ai owns the products, the policies, the information and the screenshots. Written down where both sides' agents can read it, because a boundary nobody published is a boundary that moves.

- **WO-1 · Publish the ownership boundary as a page both agents can read** — `done` — Shipped in v0.3.2 at /boundary/ — indexed, with a markdown twin, in llms.txt, so another team's agent can find it. The store owns e-commerce; riskmandate.ai owns the products and the material; the reader never crosses the seam.
- **WO-2 · Brief the RiskMandate team to do the reverse** — `done` — Shipped in v0.3.2 as the second half of /boundary/: four asks in the order that makes each one useful on its own, and an explicit list of what is NOT being asked for — no callback, no session, no shared state, no account. Status open, and it will be recorded there when it is answered including if the answer is no, because a brief that only appears when it succeeds is a brief nobody should trust.
- **WO-3 · Mark the files that are on the wrong side** — `done` — Done in v0.3.2. The one file on the wrong side is named on /boundary/ with what makes it survivable: data/abp-catalogue.json is promoted at build time with the source URL, the retrieval time and a sha256, so it cannot drift silently. It is still the wrong arrangement and the page says so.
- **WO-4 · Agree the contract for the shared files** — `next` — Both directions need a stable address, a stable shape and a version field — three different promises, all three needed. CORS makes the read possible; it does not make it safe to depend on. Asked for as item four of the brief on /boundary/. _Blocked on: The RiskMandate team's answer._


## The comparison table — next

Features down the left, five columns across — free, £10, £50, £500, £1,500. The page that makes the differences between the levels legible, and the one that finally explains the entry price, because a licence is only a difference next to a column that does not have it.

- **CT-1 · Decide what every cell is allowed to say** — `done` — Answered by building it the other way round. A row goes on the table only when each of its five cells can be pointed at — a price in data/offers.yml, a gets sentence, a not-promised line, or a ruling. A row whose cells would be a promise is not on the table at all. Fourteen rows qualified.
- **CT-2 · Write the feature list as data** — `done` — Shipped in v0.2.8 as data/comparison.yml. Fourteen rows in four groups, each carrying the sentence that says what the reader is actually buying.
- **CT-3 · Settle whether £10 includes a vault** — `done` — Settled by reading what the level already says. £10 is explicitly not a vault — its own page has said so since it was written — and £50 is where a vault starts. It was never a proposal; it was already true.
- **CT-4 · Decide what support means, and who answers** — `next` — Deliberately kept off the comparison table until it is decided. Email support on the paid levels was floated in the memo and never scoped. What is true today and could be said instead: every purchase is managed directly by the person who does the work. That is stronger than a support tier and it is also a different promise, so it needs saying on purpose rather than by default.
- **CT-5 · Build the page, free column first** — `done` — Shipped in v0.2.8 at /compare/, free column first.
- **CT-6 · Render it as a PDF** — `queued` — Asked for as a brochure. The store already generates PDFs from built HTML, so this is a build target rather than a second artefact. _Blocked on: CT-5._


## Product pages that show the product — next

“We go there, we don’t know what we’re buying.” Description, price and a buy button, a carousel of what you actually get, specs and SKUs, and a place for reviews. Prototyped in the lab first, reviewed, then wired in.

- **PP-1 · Prototype one product page in the lab** — `next` — Asked for explicitly: prototypes on the side, reviewed, then wired up. /lab/ is already that surface and every page on it states on its own face that nothing there can be bought — which an Amazon-style prototype needs more than anything else the lab has held.
- **PP-2 · Find out which screenshots exist and which have to be taken** — `next` — The synthetic run alone produced 43, and the review pages embed a live vault. Before commissioning anything, count what is already here.
- **PP-3 · Put a version on every piece of product media** — `queued` — A product page is where a store goes stale first. The walkthrough PDFs already carry the version in the filename for exactly this reason. _Blocked on: PP-2._
- **PP-4 · Print the specs and the SKUs** — `queued` — The store has 62 and shows none. The same data the Stripe rail is about to need. _Blocked on: TM-1._
- **PP-5 · Add the review section, and say it is empty** — `queued` — Reviews are coming, given away in exchange for comment. An empty section that says it is empty is this site's house style — it is what the two upper levels already do about never having been sold. No stars: a rating on a product nobody has bought is the one piece of furniture here that could not be honest. _Blocked on: PP-1._
- **PP-6 · Make the page switchable by audience** — `queued` — Framed in the memo as editions of one product rather than separate paths — the same switch the five-audience memo asked for, arriving from the other side. One mechanism serves both. _Blocked on: PP-1, QB-2._


## What has actually been done — next

The store says the upper levels have never run for a paying buyer. True, and it reads as “nobody has ever done this”, which is false. The work has been done many times and published; what has not happened is a sale through this checkout. Lead with the first, keep the second, stop letting one stand for the other.

- **WH-1 · Re-read every claim against “the work has been done”** — `done` — Fifty-two claims re-read one at a time in v0.2.1. The offer states, the ledger's own legend for specified-never-run and the home page's headline sentence were wrong as written; the rest were precise and were being misread.
- **WH-2 · Link the published evidence** — `done` — Shipped in v0.2.1. data/evidence.yml carries six published vaults, quoted from the catalogue that generates them, on the home page. Every URL returns 200 and a check holds them to the domain that publishes them.
- **WH-3 · Narrow the disclosure to what is genuinely undone** — `done` — Shipped in v0.2.1. The disclosure now says what is true: a first buyer is the first through this checkout, not the first to have the work done.
- **WH-4 · Put a name and a track record on the delivery** — `next` — Twenty years of cybersecurity, in the project lead's voice with a source rather than asserted in the shop's. Same page as the reviewer work. _Blocked on: WD-2._
- **WH-5 · Decide what to do about testimonials** — `queued` — Asked for, and there are none. The review pages are critiques, which is a different object. A placeholder saying it is empty is the house style; an invented one would undo the rest of this workstream.


## Say when it arrives — queued

Every level gets an estimated delivery, because a shop that will not say when something arrives is a shop people leave. The numbers were given: immediate, one to two days, one to three days from receiving the customisation, one to five days.

- **DT-1 · Put a delivery estimate on every level** — `done` — Shipped in v0.2.0, frozen in the gate beside the prices.
- **DT-2 · Replace the it-has-never-run non-answer about timing** — `done` — Shipped in v0.2.0. The claim that said there was no measurement to quote now carries an estimate labelled as one.
- **DT-3 · Say what the constraint really is** — `done` — Shipped in v0.2.0. The constraint is named as one person's calendar.
- **DT-4 · Start measuring the moment there is something to measure** — `queued` — An estimate becomes a record the first time an order runs. The ledger is built for exactly this. _Blocked on: TM-7._


## The homepage sells — next

A counter at an event, not an essay with a buy button. Laptop or tablet turned round: who are you, here is your thing, buy it. Products up front, big targets, few of them, and everything about the mechanism moved to the admin side.

- **SF-1 · Move the mechanism and the meta off the front page** — `next` — The home page opens by explaining what an Agent Behaviour Policy is. A shop opens with what is for sale. The explanation does not get deleted — it moves.
- **SF-2 · Put the four products up front, with prices and delivery** — `next` — The thing being sold, visible without scrolling, with what it costs and when it arrives. _Blocked on: DT-1._
- **SF-3 · Build the who-are-you entry** — `done` — Shipped in v0.2.7. Five doors on the home page and at /are/, five across on a laptop, two on a tablet, one on a phone. One tap to a view that opens on the level that fits.
- **SF-4 · Make a discount code a link, never a thing to type** — `next` — “Click a link, apply the discount code.” The store already reads a code off the address and strips it from history; what is missing is the links.
- **SF-5 · Add the sections a shop front has** — `queued` — Feature sets, articles, end-to-end flows, testimonials. Asked for by name. Testimonials are blocked on there being any. _Blocked on: SF-1, WH-5._
- **SF-6 · Test it the way it will be used** — `queued` — On a tablet, held, by somebody standing next to a stranger. Not in a desktop browser at 1440px. _Blocked on: SF-3._
- **SF-7 · Rename level four to match the product** — `done` — Done in v0.2.4. The store now says “Two sessions and a custom vault”, following the project lead's rename in Stripe — it says what the buyer ends up holding rather than what happens to it. The professional signing it is on the level's own page, where it is a property of the thing rather than the name of it.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
