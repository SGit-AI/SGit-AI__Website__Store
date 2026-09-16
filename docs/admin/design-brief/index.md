# Design brief — store.sgit.ai

*Version 1, 16 September 2026. Written for a design session with no access to this repository.*

The first round produced three handsome homepages and this store could only use parts of them, for one reason: they were pages, not a system. Three palettes arrived, none of them ours, and nothing that came back could be dropped into a build without being redrawn. This brief asks for the components first and the screens second, and says exactly what shape the answer has to come back in.


## What is being sold, and to whom

**What is sold.** Agent Behaviour Policy documents: for one AI agent, in one deployment, what it can do, what you authorised it to do, and the gap between them. Fifteen application templates, four service levels.

**Who buys.** Five audiences, and they do not want the same page. A founder shipping with agents; an investor backing companies that run them; a C-level exec who has to answer to a board; a security professional who does this for a living; a risk-and-governance lead who owns the register.

**Levels.** £10 the pack downloaded, immediately. £50 a working vault, 1 to 2 days. £500 corrected for your situation, 1 to 3 days from your reply. £1,500 two sessions and a custom vault, 1 to 5 days from your reply. The top two are a named security professional's actual work and are signed off.

**The state of it.** Six products are priced in Stripe and reconcile to the penny on every release. No checkout link has been issued, so every card on the live site shows a disabled box where a buy button belongs. That is the next release and this brief assumes it has happened: DRAW THE BUY BUTTON.

**What happened last time.** Three homepage concepts were drawn on 16 September and reviewed at /admin/concepts/. Two carry structure this store adopted. The same four folds were then shown to five synthetic readers at /admin/reviews/2026-09-16-four-homepages/. Read both before starting — they are short, and between them they say which moves are already settled.


## The constraints


### HARD RULE: Use the tokens below and add none.

The last round produced navy-and-amber, forest green and cobalt. All three are handsome and none of them is this brand or riskmandate.ai's, and a buyer is meant to move between the two properties without noticing. If a colour is genuinely missing, say which and why, rather than picking one.


### HARD RULE: The model-assistance strip stays above the main element on every screen. It never moves to the footer.

A build check refuses any page without it, so a mock that relocates it cannot be implemented. It is also the single element that won the two readers who would spend the most. It may get quieter — one line on a phone with the rest behind a link — but it stays where it is.


### HARD RULE: No star ratings, no testimonials, no customer counts, no standards-body marks, no logos of companies that have not bought anything.

Nothing has been sold here yet. A review section is wanted and is in scope — as an EMPTY STATE that says so. The review attached to the last round reached this conclusion independently, which is why it is stated as a rule rather than a preference.


### HARD RULE: Never invent a price, a delivery time, a capacity, a number of customers, or a claim about what has been delivered. Use the numbers in this brief exactly. Where a real value is missing, write [PLACEHOLDER] and say what belongs there.

Every price on this site is frozen by a build check against one file, and a mock carrying a different number produces a page that cannot ship. Two concepts last round carried a price the store had already changed.


### HARD RULE: Two word-roots never appear anywhere on this site, in any form, including inside a denial. Do not write copy that implies this store sells a regulated financial product, or that anything here carries a conformity mark or a third-party stamp of approval.

This site carries prices, and a priced page making either kind of claim is making an offer it is not allowed to make. The two roots are not printed here for the same reason they are not printed on the page that explains them: an exception for the page explaining a rule is how a rule stops applying. /disclosures/ sets out the full reasoning, without printing them either. In practice this costs a designer nothing — write about what the product IS rather than what it is not, and if a phrase does trip the check we will say so and it takes one word to fix. This brief's own first draft tripped it, by stating the rule.


### Expected: Where a slot has no content yet — a screenshot, a review, a logo — draw the empty frame with a line saying what belongs there. Do not fill it with decoration.

The product page prototype already does this: three of seven media slots are real files and four are labelled frames. A carousel padded with stock art on a page whose whole job is showing what you actually get would be the one dishonest thing on the site.


### Expected: Every screen must be drawn at 390px as well as at 1200px, and the phone version is the one to get right first.

The live homepage is 10,710px tall on a phone — thirteen and a half screens — against roughly 5,000 for each concept. Phone is where this is lost.


### Expected: One primary action per screen, repeated down it. Not three competing buttons.

Standard, and the last round got it right; it is here so it stays right.


### HARD RULE: Anything that will live inside a vault sets every image, stylesheet and script from JavaScript, never as markup.

A vault app is served from a blob: URL and the browser resolves declarative resources against an opaque origin before the vault bridge exists. An image tag carrying a src in markup — including markup assembled in a string and handed to innerHTML — is a broken image for every reader, and it looks perfect when the same folder is served over HTTP, so a local check will not catch it. Two of this store's products are vaults and one of its prototypes produces them, so this is not an edge case here.


## Already settled, and not up for redesign

- The price sits at 42px on a card, not 28px inline with the delivery estimate. Every reader used the prices when they were set large and two reported seeing none when they were set at 12px in a caption colour.
- A four-fact trust strip sits under the hero, and every fact is a link to the claim that evidences it. The concept version had four ticks and no links, which the one reader who checks things rejected on sight.
- Applications are chips, not a list, with a sixth chip reading 'something else — from £500' so a visitor whose agent is missing lands on the level that exists for them rather than at the end of a directory.
- The header carries three destinations and the order. Everything else goes to the footer or the console. It currently carries forty-eight.
- The persona doors stay, and stay above the product. All three concepts routed by application and dropped them; the brief for this store was explicit about wanting 'who are you' first.

## Open, and genuinely wanted

- Product naming. 'Professional review' reads out loud in a board meeting; 'two sessions and a custom vault' is more honest about what arrives. The proposal is a short name at heading size with the precise description as the line beneath. Draw the anatomy that supports both and leave the words to us.
- The headline. 'Every agent needs a licence to operate' was not misread by any reader, and an outside review flagged that 'licence to operate' can be taken as regulatory permission. 'Powerful agents. Clear boundaries.' was the only line every reader understood on sight. Not settled. Show the hero working with a long headline and a short one.

## The tokens

Read from the live stylesheet by the build that produced this file. Use these and add none.


| Token | Value |
|---|---|
| `--bg` | `#faf9f5` |
| `--panel` | `#ffffff` |
| `--panel2` | `#f2f0e9` |
| `--line` | `#e5e1d5` |
| `--line2` | `#d5d0c2` |
| `--fg` | `#1c1d21` |
| `--dim` | `#5c5f66` |
| `--dim2` | `#8a8d94` |
| `--ink` | `#34363c` |
| `--accent` | `#0f766e` |
| `--accent-dk` | `#115e59` |
| `--warm` | `#b45309` |
| `--green` | `#15803d` |
| `--blue` | `#0369a1` |
| `--red` | `#b91c1c` |
| `--sans` | `ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif` |
| `--serif` | `ui-serif,Georgia,"Times New Roman",serif` |
| `--mono` | `ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace` |

### The 10 claim states


| Id | Label | What it means |
|---|---|---|
| `exists` | exists and runs | Built, and it runs today. |
| `measured` | measured | Measured by our own pipeline on a named workload and date. |
| `docs` | read, not run | Read from a published source on this date. Never executed by us. |
| `projected` | projected | Arithmetic, not an invoice. The workings are shown. |
| `spec` | specified, not built | A specification. The thing it specifies does not exist yet. |
| `person` | delivered by a person | A named security professional does this work and signs it off. It is somebody's time rather than a pipeline, which is why its delivery estimate depends on availability. |
| `unlocated` | built, not located | It was built. It has not been found since, and until it is, nothing here promises it. |
| `booking` | a booking, not a download | What is bought is a person's time, not a file. |
| `partial` | part exists | One half of it runs. The half that carries the guarantee does not. |
| `absent` | does not exist yet | It does not exist. It is listed so that nobody proposes it as new. |

## The component set

This is the deliverable that matters most. Every component, every state, before any screen is drawn.


### Button (`button`)

States: primary, secondary, disabled with a reason, destructive — none exist yet

The disabled state is real and shipping today: 'the payment link has not been issued yet'. It needs to look deliberate rather than broken, because it is on every card until the next release.


### Price block (`price`)

States: single price, deposit split — a fifth now, the rest on delivery, free, from £N

42px, with the delivery estimate and the clock it runs from. The split is two Stripe products that sum to the price, so it is a real thing to draw and not a presentational trick.


### Offer card (`offer-card`)

States: level 01 to 04, free, leading in an audience view, quieted in an audience view, add-on

The one component that appears on the most screens. Anatomy: level and delivery on one line, name, one line of who it is for, price, one sentence, claim chip, action.


### Claim chip (`claim-chip`)

States: one per claim state — the page lists them, with what each means

Links to the ledger. Only one state is the fully-earned one, which is deliberate: if most chips look confident the component has failed. ONE THING TO FIX WHILE YOU ARE IN HERE — two states currently share a CSS class and therefore render identically, so 'specified, not built' and 'part exists' are indistinguishable on a card. They mean different things and one of them is worse news than the other. Give the set enough visual range that ten of them stay legible at chip size.


### Persona door (`persona-door`)

States: five audiences, current, on a phone

Five across at 1200px. At 390px five stacked cards is 500px of screen before anything is for sale, so this needs a real phone answer.


### Application chip (`app-chip`)

States: one of fifteen, the catch-all, from £500, selected

The catch-all chip is the point of the component.


### Trust strip item (`trust-item`)

States: linked to a claim, four across, two-by-two on a phone

Never unlinked.


### Media frame (`media-frame`)

States: a real screenshot with a caption, a labelled empty frame naming what belongs there, in a carousel, expanded

Both states ship together. The empty one is not a placeholder to be removed later — it is how the page stays honest while the screenshots are taken.


### Specification row (`spec-row`)

States: plain, with a chip, on a phone

Label and value. Reads as a datasheet, not as prose.


### Disclosure strip (`disclosure`)

States: desktop, two lines, phone, one line with the rest behind a link

Above main, always. See the constraint.


### Version badge (`version-badge`)

States: current, in the console

How a reader knows which build they are quoting. Quiet, not absent.


### Section header (`section-head`)

States: with an action on the right, centred, on a phone

Eyebrow, heading, one line of subheading, optional action. Used on every screen and currently inconsistent.


### Vault frame (`vault-embed`)

States: loading, open, an example, labelled, failed

An iframe opened with a read key. The labelled-example state is the one that matters — see the after-the-sale screen.<br><br><b>If you are drawing anything that will live INSIDE a vault rather than beside one</b>, the authoring contract is not the web's. A vault app runs in an iframe loaded from a <code>blob:</code> URL, so the browser fetches anything declarative before the vault bridge installs: no stylesheet link, no script src, and no <code>&lt;img&gt;</code> written as markup, including markup you build in a string and assign to <code>innerHTML</code>. Create the element and assign <code>.src</code> as a property instead. This store shipped a vault on 16 September that broke exactly that rule and rendered ten broken images to every reader, while the same files served over plain HTTP were perfect — which is why it survived a local check.


### Reviews, empty (`review-empty`)

States: no reviews yet, one review, several

The empty state is the one shipping. Draw the other two so the page does not have to be redesigned the day somebody writes one.


### Edition switcher (`edition-switch`)

States: five audiences, one selected, on a phone

Changes the argument in place, without a page load and without changing the product.


### Callout (`callout`)

States: a ruling, a caveat, a hold, an example

Four kinds and they must not all look the same, because one of them means 'this is not what you think it is'.


### Header and footer (`nav`)

States: header at four links, footer carrying eleven, phone menu, console rail

The header goes from forty-eight to four. The footer takes the evidence apparatus. Both need drawing, because the footer is now load-bearing.


### Comparison table (`table`)

States: five columns, row group, a yes, a no, a qualified yes, on a phone

The qualified yes is the hard one — most of the interesting rows are not a tick or a cross.


## The screens


### The product page — first

Live today: https://store.sgit.ai/lab/product/

**What is there today.** A prototype, in the lab, marked unbuyable on its own face.

The one the store most needs and has never had. A level page argues about what a policy is; a product page shows the thing. Amazon-shaped: description left, price and buy on the right, a screenshot carousel, specifications, and a reviews section that is honest about being empty.

It has to carry:

- A media carousel with many slots, of which only some have a real image — the rest are labelled frames naming what belongs there.
- A right-hand rail that stays with the reader: price at 42px, delivery estimate and the clock it runs from, the buy button, and for the top two levels the deposit split (a fifth now, the rest on delivery).
- A specifications table — product code, what it is, how many shapes, delivered in, licence, formats, whether an account is needed.
- A reviews section as an empty state.
- An edition switcher: the same product described five ways, one per audience, switching in place without a page load.

**The hard part.** The edition switcher has to change the argument without changing the product. Five audiences, one SKU, one price, five reasons.


### The comparison table — first

Live today: https://store.sgit.ai/compare/

**What is there today.** Fourteen rows in four groups across five columns, including a free one.

Features down the left, five columns across — free, then the four levels. It has to work as a page, as something printable, and as a thing a reader screenshots and sends to somebody else.

It has to carry:

- Five columns including the free one, which comes first.
- Row groups with headings, so a reader can find the row they care about.
- A phone version that does not become a horizontal scroll nobody uses.
- A print-shaped version: this is explicitly wanted as a brochure and a PDF.

**The hard part.** Five columns at 390px. Most comparison tables give up here and become five stacked cards, which loses the comparison — which is the entire point of the page.


### The level page — first

Live today: https://store.sgit.ai/d/t2/

**What is there today.** One per level, plus two add-ons.

The page a buyer lands on from a card. What this level is, what arrives, what does not, who does the work, and the way to buy it. Shorter than the product page and pointed at one decision.

It has to carry:

- What arrives and what does not, as two lists rather than a paragraph.
- For the top two: who does the work, with the professional's name and face.
- The delivery estimate and the clock it runs from — from your payment for the first two, from your reply for the top two.
- The buy button, and the deposit split where there is one.

**The hard part.** 'What does not arrive' has to be as prominent as what does, and has to not read as an apology.


### The order and the payment hand-off — second

Live today: https://store.sgit.ai/cart/

**What is there today.** An order built in the reader's own browser, no account, nothing stored anywhere else.

Everything up to the moment the reader leaves for the payment provider. No form fields — the provider's page collects the name, the email and the card, and this store never sees any of them. There is no input, textarea or select anywhere in this site's output and a check holds that line, so draw a cart made of buttons.

It has to carry:

- The order reference, generated in the browser and shown on the page.
- A discount code applied and its effect visible.
- The hand-off explained before it happens: what the provider will ask for, and what this store will never see.

**The hard part.** A checkout with no form. It is a real constraint, not a stylistic one, and it is the thing this store can say that most stores cannot.


### After the sale — second

Live today: https://store.sgit.ai/paid/t2/

**What is there today.** One per level.

The instruction was 'when you have sold a vault, you should just see the vault'. So the screen after payment is not a receipt with a link on it — the thing bought is on the screen, open, with the receipt beside it.

It has to carry:

- The vault itself, embedded and open, above anything congratulatory.
- For a buyer whose own vault does not exist yet, a published example labelled as an example in its first sentence.
- What happens next and when, with the date.
- For the top two levels: who is doing the work, and how they will make contact.

**The hard part.** The reader has paid and is now looking at somebody else's example vault. That has to be obviously an example without feeling like a bait and switch.


### The audience landing — second

Live today: https://store.sgit.ai/are/founder/

**What is there today.** Five of them, one per audience.

Where a persona door leads. The same four levels, led with the one that fits this reader and the rest quieted rather than hidden.

It has to carry:

- Nothing hidden. A check refuses display:none on an offer in an audience view — every level stays reachable from every audience, and what changes is which one leads and what is said about it.
- The reader's own question in their own words, at the top.
- One level foregrounded, the others at reduced emphasis and still clickable.

**The hard part.** 'Quieted, not hidden' is a visual problem. Opacity alone reads as broken; a different treatment entirely reads as a different product.


### Describe your agent — second

Live today: https://store.sgit.ai/lab/agent-canvas/

**What is there today.** Two prototypes in the lab — a canvas and a sequence.

A free page, and the one the project lead expects to use most in conversation. The agent sits in the centre; the things it can reach sit around it — a database, the internet, part of the internet, a file system, the ability to send email. The reader clicks or drags them onto the agent and builds up a description of what it can actually do.

It has to carry:

- The agent at the centre and its capabilities around it, clickable and draggable.
- Twenty-three capability primitives on a verb.object.reach grammar, which exist already and are not to be invented.
- A running description of what has been assembled, in plain words.
- An export at the end: the description, in a form that can be handed to a model session with a template vault, which then produces the buyer's own vault.
- It has to work on a phone and in a room, over somebody's shoulder.

**The hard part.** This is a toy that has to produce a document. Show at least two different interactions for it — the canvas and something else entirely — because which one works in a live conversation is not known yet.


### The professional's page — third

Live today: https://store.sgit.ai/who/dinis-cruz/

**What is there today.** One, for the person doing the work today.

Who does the £500 and £1,500 work. Built for a list: more professionals are being recruited, so it is a template with one entry today, not a personal page.

It has to carry:

- Enough for a buyer to decide whether this person's signature is worth £1,500.
- Every biographical line sourced, because a check refuses one that is not.
- An index that works with one entry and with twelve.

**The hard part.** A page of one person's credentials that does not read as a CV.


### The claim ledger — third

Live today: https://store.sgit.ai/ledger/

**What is there today.** Fifty-two claims, each with a state and a date, cited from the pages that make them.

Every factual claim this site makes, the state it has earned, and the date. Pages cite a claim and the chip links back here. It is the store's whole argument for being believed, and it currently looks like a table.

It has to carry:

- Every claim state visually distinct and legible at chip size. The page lists them; two currently share a class and render identically.
- The join in both directions: from a claim to the pages citing it, and from a page's chip to the claim.
- It should be possible to skim for the claims that are weakest, not just the ones that are strongest.

**The hard part.** Making a page of caveats feel like confidence rather than hedging.


## How to hand it back

Last round came back as three finished pages and this store could use the structure of two of them and none of the execution. What makes a mock implementable is not more polish, it is the system underneath it named and specified.

1. ONE COMPONENT SHEET FIRST, before any screen. Every component in the list above, every state, at both widths, on one page. This is the deliverable that matters most; a beautiful screen built from unnamed parts costs more to implement than it saves.
2. THEN THE SCREENS, in the priority order given. Each at 1200px and 390px.
3. A TOKEN TABLE of everything actually used, so any value that is not in the set below is visible at a glance rather than discovered later.
4. A SHORT NOTE PER SCREEN: what you changed from the brief and why. Disagreement is wanted — the last round's disagreements are on the board. Silent substitutions are not.
5. PLAIN HTML AND CSS, one file per screen, no build step, no framework, no external requests except a font. It does not need to be production code — it needs to be readable, because it is going to be read and re-implemented rather than pasted.

And not:

- Do not produce a design system document with principles and no pixels.
- Do not use a component library's defaults. The whole exercise is this store's own vocabulary.
- Do not fill an empty state with sample data unless it is labelled as sample in the mock itself.

## Read these first

- [The review of the last round](https://store.sgit.ai/admin/concepts/) — What was taken from the three concepts, what was refused, and the seven measurements that decided it.
- [Five readers on the same four folds](https://store.sgit.ai/admin/reviews/2026-09-16-four-homepages/) — Eight findings, including the three nobody was looking for.
- [The product page prototype](https://store.sgit.ai/lab/product/) — The starting point for the first screen, and the source of the media-frame component.
- [What each level gets you](https://store.sgit.ai/compare/) — The five columns, and the rows as they stand.
- [What we do not say, and why](https://store.sgit.ai/disclosures/) — The barred words, in full, with the reasoning.
- [The claim ledger](https://store.sgit.ai/ledger/) — Every claim state, and what each one means. The chip set is one of the eighteen components.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
