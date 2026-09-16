# The work

The units of work for this store, as a board. Two levels, like the board this one is modelled on at sgraph.ai/en-gb/dev/workstreams/: the top board has one card per workstream and the column it sits in is derived from its own tasks, and opening a card gives that workstream's tasks in the same four columns. A workstream is never dragged — it moves because a task in it moved, which means the summary cannot disagree with the detail.

**16 workstreams · 86 units of work · 72 not done.**


## Take money at all — next

No payment rail is live. Every checkout_url in data/checkout.yml is empty, so the store can be walked end to end and cannot be bought from. This is the workstream that ends that, and the shape of it changed on 16 September: the rail is no longer an amount-only link, it is Stripe's own catalogue and a real customer record behind every order including the free ones.

- **TM-1 · Create six Stripe products and eight prices** — `next` — GBP, one-off, lookup keys SG-T1 to SG-ADD-OPINION. Copied from the generated catalogue file rather than typed out by hand. A price does not vary by shape, which is why this is eight rows and not sixty-two.
- **TM-2 · Set customer creation to always, and prove it on a £0 order** — `next` — The single setting most likely to be missed. Without it a hundred-per-cent order completes, the buyer sees a confirmation, and no customer record exists — which is the exact opposite of why this rail was chosen. Proof is a Customer visible in the dashboard after one free order, not a screenshot of the toggle.
- **TM-3 · Create three coupons and seven promotion codes over them** — `queued` — 25, 50 and 100 per cent. The seven strings are the ones data/discounts.yml already holds, so a code printed on a PDF at v0.1.11 still works. Every promotion code gets a redemption cap and an expiry.
- **TM-4 · Enable promotion codes on every link, prefill where a code was leaked** — `queued` — A link with the field switched off refuses a valid code with no explanation and the buyer blames themselves. Where a page publishes a code as part of a journey, the link on that page carries it already applied.
- **TM-5 · Bring the return address onto this site** — `next` — Superseded by the later memo the same day. This was “settle the ?order= contract with the RiskMandate team” and it was blocked on them. The buyer no longer leaves the store, so the success address is ours to render and the block is gone. What survives from the original is the real constraint: a standing Stripe link substitutes a session id and nothing else, so the landing page has to work from that.
- **TM-6 · Stand up the checkout.session.completed webhook** — `queued` — The step that unblocks a first paid order at £50, £500 and £1,500. Listen to the session, not the payment: a hundred-per-cent order creates no charge, so a handler keyed on a succeeded payment sees every paid order and none of the free ones. _Blocked on: Runs off this site. This site is static and opens no connection._
- **TM-7 · Take one real £10 payment and read the receipt** — `queued` — Every sentence on the rails page about what a receipt says is unverified. This is the task that makes them checkable. _Blocked on: TM-1 and TM-6._
- **TM-8 · Retire the browser-side discount arithmetic** — `queued` — A code is honoured in the browser today and the page says it is a demonstration. Once a promotion code exists on the rail there are two implementations of one rule, and the browser one can be edited by the person it is discounting. _Blocked on: TM-3._
- **TM-9 · Take SumUp's hosts from the rails, not from a constant** — `next` — check_checkout_links pins every destination to Stripe's two hosts. data/checkout.yml has declared SumUp's hosts since the rail was added and the check has never read them, so a SumUp URL pasted in today is refused by the gate with a message about Stripe. Five lines.
- **TM-10 · Write the two rails up as plans rather than intentions** — `done` — Shipped in v0.1.18 at /admin/rails/stripe/ and /admin/rails/sumup/, generated from data/admin/rails.json.


## The entry price, and what it buys — next

Two reviewers independently said the entry level reads as a commodity at £5 — one human partner and one invented buyer who had never met them. The answer ruled on 16 September is not a larger number for the same thing: the level goes to £10 and gains a commercial licence, which is a different product rather than a dearer one.

- **PL-1 · Move the entry level from £5 to £10** — `done` — Shipped in v0.2.0. £10, with all three moves of the price kept on the page.
- **PL-2 · Dual-licence the pack: CC BY public, commercial to the buyer** — `done` — Shipped in v0.2.0. The public files stay CC BY; the buyer gets a commercial licence over the same material. The wording is not drafted and the ledger says so.
- **PL-3 · Research the cleanest way to grant it** — `next` — The licence is to the buyer and does not name them, which is the interesting part: a grant to an unnamed holder has to be worded so it is clearly a grant and not a public re-licence of the same bytes. Open questions: does it travel with the file or with the order reference, what happens on resale, and does it survive the buyer's company changing name.
- **PL-4 · Put the licence text where the buyer reads it before paying** — `queued` — Not in the pack, not in a footer. The difference between the free version and the paid one is now the main thing the entry level sells, so it belongs on the card and on the level page above the fold. _Blocked on: PL-2._
- **PL-5 · Record the price arc as one claim, not three** — `queued` — The ledger already carries £10 → £5 with the card-fee arithmetic. Adding £5 → £10 as a separate claim would leave a reader assembling the story from three entries. One claim, three dates, all the reasoning kept. _Blocked on: PL-1._


## Who runs the review — next

The two upper levels are somebody's work and the store has never said whose. A buyer spending £1,500 on a security review is buying a person, and the site asks them to buy it from nobody in particular. First reviewer named 16 September; the surface is built for several, because there will be.

- **WD-1 · Build the reviewer register and a page per reviewer** — `next` — data/reviewers/ as the register, one page each, generated — same idiom as the reviews. Built for a list from the first day so adding the second is adding a file rather than a refactor.
- **WD-2 · Write the first reviewer's page** — `next` — Dinis Cruz, who runs the £500 and £1,500 reviews today. Material exists on the open-source site, on sgit.ai and on LinkedIn. Nothing on the page gets written that is not traceable to one of those — a biography this site invented would be the worst possible thing to put next to a price. _Blocked on: Source material from the project lead._
- **WD-3 · Let the buyer choose their reviewer at £500 and £1,500** — `queued` — A selection, carried in the order reference the way the shape already is. With one reviewer it is a statement rather than a choice, and it should still be on the page, because what it says is that there is a name behind the work. _Blocked on: WD-1, WD-2._
- **WD-4 · Recruit the rest** — `queued` — The project lead is contacting people they know. The page has to be worth being listed on before anybody is asked, which is the real reason WD-2 comes first.
- **WD-5 · Say what happens when the chosen reviewer cannot take the work** — `queued` — Both upper levels already disclose they have never been sold. A named reviewer adds a second thing that can fail and the pages do not cover it. _Blocked on: WD-3._


## Leak the codes on purpose — next

Seven discount codes exist and only the walkthrough page prints any of them. The ask is to publish codes on the main site on specific journeys — a code is a reason to complete a purchase, and a purchase is how a visitor becomes a customer record.

- **LC-1 · Decide which journeys carry a code** — `next` — Not the home page. A code on a first screen discounts a decision nobody has made yet; a code at the end of a level page discounts one somebody is in the middle of making.
- **LC-2 · Print the code on the journey, with the link carrying it applied** — `queued` — Re-typing a code you just read is a step that loses people. The published code and the prefilled link are the same fact rendered twice. _Blocked on: LC-1, TM-4._
- **LC-3 · Give every leaked code a cap and an expiry before it is printed** — `queued` — A printed code cannot be recalled. The cap is what makes printing it survivable. _Blocked on: TM-3._
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
- **QB-2 · Write the five audiences down as data** — `next` — One record each: who they are, what they arrive worried about, which offers they see, and the words that change. The store's existing buyer groups are already data — this is the same file shape with visibility added, which is the field the catalogue has no concept of today. _Blocked on: QB-1._
- **QB-3 · Answer: hidden, or shown differently?** — `next` — An offer absent from an audience's view and an offer present with different words are very different promises, and one of them means this site shows a different catalogue to different readers. That needs saying out loud on the disclosures page before it is built, not after.
- **QB-4 · Build the five paths** — `queued` — A path, not a page: the entry, the offers that audience sees, the language, and where it hands over. Generated from QB-2 so a sixth audience is a file. _Blocked on: QB-2, QB-3, and the component work in decouple-the-views._
- **QB-5 · Run a synthetic pass over the five paths** — `queued` — Named in the memo as the feedback loop for this work. The method exists and has been run once; the second run is the one that tells us whether it generalises. _Blocked on: QB-4._


## The version the board can read — next

“Can I have this in a form my board can read?” Every vault should already contain one — the policy re-cut for the people who have to sign it off. Not a paid extra and not an add-on: every vault, including the ones anybody can download for nothing.

- **BR-1 · Specify what a board-readable cut actually is** — `next` — Length, what it leads with, what it leaves out, and what a reader is expected to do with it. It is the whole deliverable, so specifying it badly is worse than not shipping it.
- **BR-2 · Decide who writes it, per vault** — `next` — Fifteen shapes. Generated, written once per shape, or written per sale — the answer changes what the entry level costs to fulfil and therefore whether £10 is the right number.
- **BR-3 · Say on the site what is inside a vault** — `next` — The memo's own diagnosis: the store never explains this well. It is the gap the board-readable cut sits in, and it is worth closing on its own even if BR-1 takes a while.
- **BR-4 · Put it in the free vaults first** — `queued` — “Including the ones you can download for free.” Doing the free ones first is the harder order and the right one: it proves the cut is generated rather than hand-finished for a paying customer. _Blocked on: BR-1, BR-2._
- **BR-5 · Re-read the entry level once it carries one** — `queued` — A £10 pack that contains a version the board can read is a different argument from a £10 pack that does not. This is where the commodity finding finally gets answered rather than deflected. _Blocked on: BR-4, PL-2._


## Decouple the views — in-progress

Five audiences across the surfaces they touch is not writeable by hand. The store is already data-driven at the content layer and hand-written at the view layer, and that seam is what the memo is pointing at: JSON configuration, components, and the same generate-and-check discipline coding.sgit.ai and nfrs.sgit.ai both teach.

- **DV-1 · Read the two guidance sites properly and write down what applies** — `in-progress` — coding.sgit.ai measures its conventions by counting the code rather than asserting them; nfrs.sgit.ai runs one rule — link the measurement, never restate it, generate or date every number — and fails its build otherwise. This store already runs both of those; what is not yet written down is which of their component conventions apply to a site that ships no framework.
- **DV-2 · Settle: custom elements at runtime, or generated partials at build?** — `next` — This is the decision the rest depends on and it has a hard constraint on it. Every selling page on this site opens no connection and a build check fails the release if one does. Components that fetch their own configuration would negotiate with that rule. Components that are rendered at build from the same JSON would not, and would still give the memo what it asked for.
- **DV-3 · Lift the view layer out of build.py into declared blocks** — `queued` — Three thousand lines, of which the page shells and the block renderers are the part five audiences would multiply. Extract those first; leave the markdown renderer and the gate alone. _Blocked on: DV-2._
- **DV-4 · One JSON file per view, and a check that fails on an unused one** — `queued` — The store's own idiom, applied to views: a register with no file and a file with no register entry both fail the build, the way the reviews already do. _Blocked on: DV-3._
- **DV-5 · Prove it by adding the sixth audience as a file** — `queued` — The acceptance test for the whole workstream. If adding an audience is still a code change, the refactor did not land. _Blocked on: DV-4, QB-4._


## Never leave the site — next

A buyer does the whole thing here — catalogue, cart, payment, receipt, and the vault they just bought, embedded on the page they land on. Today the store hands them to another domain at the moment they pay, which a synthetic buyer called out as the point they got confused.

- **OS-1 · Narrow the no-network rule before the first cross-origin read** — `next` — Every selling page opens no connection and check_no_network fails the release if one does. Reading riskmandate.ai's catalogue over CORS breaks that as written. The rule gets narrowed, never loosened — the absolute half stays absolute, the exception is named in the check, and a deliberate break is run against the new check before anything ships. That is how the vault embed was admitted and it is the only way this one gets in.
- **OS-2 · Move the post-sale page onto this site** — `next` — The success address goes from riskmandate.ai's page for the level to one here. This is what unblocks the Stripe return-address task, which was blocked on another team until this memo arrived. _Blocked on: OS-1 for anything it needs to read._
- **OS-3 · Embed the bought vault on the page they land on** — `next` — “You should see the vault.” The mechanism is already in this repository and already passing the gate: a frame built at runtime, opened carrying nothing, handed a published read key by message with the origin pinned. What is new is which page it runs on. _Blocked on: OS-2._
- **OS-4 · Read the product data from the side that owns it** — `queued` — The shapes belong to riskmandate.ai. The store reads them over CORS and renders them in the store's own CSS — somebody else's data, never somebody else's interface. _Blocked on: OS-1, and the other side publishing a stable file._
- **OS-5 · Make the store feel like a shop** — `queued` — “Fundamentally like Amazon.” More detail is coming from the project lead. Several pages here are an essay with a buy button under them, which is the gap. _Blocked on: More information from the project lead._
- **OS-6 · Re-run the synthetic buyer who got confused** — `queued` — The finding has a name and a persona attached. The same walk, after the flow is one site, is the only way to know this worked. _Blocked on: OS-2, OS-3._


## Who owns what — next

Two sites, one purchase. The store owns e-commerce — cart, workflow, redirections, payments. riskmandate.ai owns the products, the policies, the information and the screenshots. Written down where both sides' agents can read it, because a boundary nobody published is a boundary that moves.

- **WO-1 · Publish the ownership boundary as a page both agents can read** — `next` — Not a note in a commit. A page with a markdown twin, in llms.txt, stating which side owns each surface and which file lives where — the estate's own convention for anything another team's agent has to act on.
- **WO-2 · Brief the RiskMandate team to do the reverse** — `next` — Asked for explicitly. Their side reads the store's e-commerce surfaces rather than re-implementing a cart, exactly as the store reads their products. The estate has a form for this already: a cross-team brief, addressed, status-tracked, and corrected in public when it turns out to be wrong. _Blocked on: WO-1._
- **WO-3 · Mark the files that are on the wrong side** — `queued` — The memo permits a few files living here that will move. Permitted debt is fine; invisible debt is not. Each one carries which side owns it, and a check counts them so the number can only go down. _Blocked on: WO-1._
- **WO-4 · Agree the contract for the shared files** — `queued` — Both directions need a stable address, a stable shape and a version. CORS makes the read possible; it does not make it safe to depend on. _Blocked on: WO-2._


## The comparison table — next

Features down the left, five columns across — free, £10, £50, £500, £1,500. The page that makes the differences between the levels legible, and the one that finally explains the entry price, because a licence is only a difference next to a column that does not have it.

- **CT-1 · Decide what every cell is allowed to say** — `next` — The hard part, and it comes first. Most of the cells in the memo are proposals rather than facts, and this store fails its own release when a page states an unproven thing as a fact. Either each cell carries a state the way every claim does, or the table waits until the cells are true. Both are defensible; publishing a confident table over unproven cells is not.
- **CT-2 · Write the feature list as data** — `next` — One row per feature, one cell per level, each cell carrying its state and the claim it rests on. Generated, so the table cannot disagree with the level pages beside it. _Blocked on: CT-1._
- **CT-3 · Settle whether £10 includes a vault** — `next` — Offered in the memo as an example and it contradicts what the level page says today. It has to be decided before the table exists, because the table is where the contradiction becomes visible.
- **CT-4 · Decide what support means, and who answers** — `next` — Email support on the paid levels is floated rather than decided. It is also the second promise on this site with no name on the mailbox.
- **CT-5 · Build the page, free column first** — `queued` — Five columns with the free one leading, because what you can have for nothing is the first row of the argument rather than an objection to be handled. _Blocked on: CT-2._
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
- **SF-3 · Build the who-are-you entry** — `next` — The actual design brief: laptop turned round, somebody says “founder”, two taps to a checkout. Big targets, works on a tablet, no dead ends. The top menu keeps the full catalogue and the individual audiences for everyone else. _Blocked on: QB-2._
- **SF-4 · Make a discount code a link, never a thing to type** — `next` — “Click a link, apply the discount code.” The store already reads a code off the address and strips it from history; what is missing is the links.
- **SF-5 · Add the sections a shop front has** — `queued` — Feature sets, articles, end-to-end flows, testimonials. Asked for by name. Testimonials are blocked on there being any. _Blocked on: SF-1, WH-5._
- **SF-6 · Test it the way it will be used** — `queued` — On a tablet, held, by somebody standing next to a stranger. Not in a desktop browser at 1440px. _Blocked on: SF-3._

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
