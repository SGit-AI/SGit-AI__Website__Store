---
title: A partner reviewed this store, and here is the whole thing
description: "A partner walked the entire store and wrote it up. Their note is published here verbatim, with eleven proposals drawn out of it — two we will not do, three that need a ruling — and a verdict box on each. Nothing you type leaves your browser."
lead: "**A partner went through the whole workflow and sent back a critique.** It is below in full, unedited, including the parts that say the entry is built the wrong way round and the £5 price may be a mistake. Under it: what we read in it, what each point would cost to act on, and a stance on every one — **including the ones we think we should not do.**"
order: 12
toc: true
head_css: /assets/review.css
head_js: /assets/review.js
---

## Why this is a page and not a document

**A critique only the seller has read is a critique that changes nothing.** This site
already publishes what it has not built, what it has never sold, and the arguments it
lost — [the claim ledger](/ledger/) exists for that. A review that goes into a drive
instead of onto the site would be the one thing on this domain held back because it was
unflattering, and it is not going to be.

So it is here in full, with the reviewer's name off it and not one of their words
changed. **Every proposal under it carries our stance, and two of those stances are "won't do".**
That is the half of a review which normally never gets written down, and the half a
reviewer most deserves an answer on.

### This page can be typed into, and nothing else on this site can

**Until v0.1.15 there was no form, input, textarea or select anywhere in this site's
output**, and a build check refused any release that grew one. That rule moved, by
ruling, to make room for this page — because asking somebody to answer a review with no
way to answer it would be the joke version of the whole argument here.

**It moved narrowly, and what stayed absolute stayed absolute.** There is no `<form>`
element on this page or any other, because that is the element that submits. There is no
`<input>` and no `<select>` anywhere on this domain, because that is where a card number
or an email address gets typed. **No page here opens a network connection**, this one
included, and that check did not move at all. The boxes below carry no `name` attribute,
because a name is what a field is called when it is submitted and these are never
submitted.

**What you type stays in your own browser.** It reaches us when you paste it to us, and
by no other route. {{claim:review-is-the-one-typing-surface}}

## The note, verbatim

Reproduced exactly as sent. Nothing trimmed, reordered or paraphrased.

> I went through the full workflow. Overall, I think there is a lot to like here. The underlying product thinking is actually really strong.
> 
> What I really like is the core idea of comparing what an agent can do versus what you actually want it to do, what you don't want it to do, and what's actually stopping it. That feels like the most powerful part of the product. The Gmail example makes this pretty obvious. I may only want an agent reading certain emails, but the credential I've given it could technically allow it to read everything.
> 
> I also like the different levels of service. There is a natural progression from downloading something yourself, to having a working version, to getting something customized, to having professional review and sign-off. I think that ladder makes sense.
> 
> The transparency is also great. You're very clear about what has and hasn't been proven, what isn't live yet, and what the product does and doesn't claim to do. For a security product, that actually builds a lot of trust. I also really like that the store itself follows the security philosophy of the product. No accounts, forms, analytics, cookies, etc.
> 
> There are a lot of concepts to learn before I really understand what I'm buying. Shape, Agent Behaviour Policy, grant, mandate, vault, correction, levels, licence to operate, and so on. I wouldn't necessarily simplify what's happening underneath, but I would simplify the jargon and visualization.
> 
> I also think the experience starts a little too much from how you've built the product rather than how the customer thinks about the problem. "Which agent do you run?" is fine, but I think the more interesting question is something like:
> 
> "What can your AI agent do that you didn't actually authorize?"
> 
> Then let me pick ChatGPT, Claude Code, Gmail, GitHub, n8n, etc.
> 
> Once I choose one, show me something really simple:
> 
>     Your agent can do 4 things.
>     You intended 1.
>     3 are outside its mandate.
>     2 have nothing effectively stopping them.
> 
> Then let me click in and actually see those capabilities.
> 
> That would be a much stronger aha moment for me. Right now you're telling me there is a problem and then selling me the policy. I'd rather discover the problem myself and then have you offer me the solution.
> 
> I'd also simplify the four levels. Something along the lines of Template, Live Policy, Deployment Review, and Professional Sign-off is much easier for me to immediately understand than having to figure out what each level means.
> 
> I'm also not sure about the £5 price point. I understand the logic because it makes trying the product almost frictionless, but there is a risk that it makes something pretty sophisticated feel like a commodity template. Since you're already making the public template available, I'd experiment with making that free and charging more once someone wants to actually operationalize it.
> 
> The £500 experience could also be more interactive. Instead of buying first and then figuring out what information I need to send you, let me describe my deployment first. What agent am I using? What systems does it touch? What data does it have access to? What should it be allowed to do? What should it absolutely never do?
> 
> Then show me a preliminary mandate and say, "We can validate this against your actual deployment."
> 
> I think I'd be much more likely to buy at that point because I've already seen the value.
> 
> The other idea I'd play with is some kind of Agent Passport or Agent Authorization Record. Basically a persistent record for every agent that says who owns it, what systems it touches, what it's authorized to do, what it's not authorized to do, what the underlying credentials technically allow, where the gaps are, what controls exist, and when it was last reviewed.
> 
> That starts to feel much bigger than selling policies. It could eventually become the system of record for which AI agents are actually authorized to do what inside an organization.
> 
> So overall, I wouldn't change the rigor underneath. I actually think that's one of the strongest parts. I'd just hide more of that complexity from the buyer.
> 
> The experience I'd ultimately try to get to is really simple:
> 
>     Pick your agent -> see what it can do -> see what you actually authorized
>     -> identify the gaps -> fix them -> continuously prove the agent
>     is operating within its mandate.

## What is in the note

### Keep

- **K-1 — The delta itself.** Can-do against want-to-do against don’t-want against what actually stops it. Named “the most powerful part of the product”. The Gmail example is what made it land.
- **K-2 — The ladder.** Download it yourself, have a working one, have it customised, have it reviewed and signed. The shape of the progression is right.
- **K-3 — The disclosure.** Clear about what has and has not been proven, what is not live, what is not claimed. For a security product that builds trust rather than costing it.
- **K-4 — The store practises it.** No accounts, no forms, no analytics, no cookies. The shop is built the way the product argues you should build things.

### Friction

- **F-1 — Too much vocabulary, too early.** Shape, Agent Behaviour Policy, grant, mandate, vault, correction, levels, licence to operate — before you know what you are buying.
- **F-2 — Entry is our shape, not theirs.** “Which agent do you run?” is how the catalogue is built. The buyer’s question is what their agent can do that they never authorised.
- **F-3 — No discovery moment.** We assert the problem and then sell the policy. Nothing lets the buyer find the problem in their own deployment first.
- **F-4 — The rungs are unlabelled.** Each level has to be decoded before it can be compared with the one above it.
- **F-5 — £5 may read as commodity.** Frictionless, but it can make something sophisticated feel like a template with a price tag on it.
- **F-6 — £500 is buy-then-discover.** You pay, and only then find out what you have to send. The value arrives after the money.

### Recommendation

- **R-1 — Lead with the question.** “What can your AI agent do that you didn’t authorize?” then pick a vendor, then four numbers, then click into the capabilities.
- **R-2 — Rename the levels.** Template, Live Policy, Deployment Review, Professional Sign-off.
- **R-3 — Free template, charge to operationalise.** The public template is already free; let the money start where the work starts.
- **R-4 — Describe before you buy.** Describe the deployment, get a preliminary mandate, then be offered validation against the real one.
- **R-5 — Agent Authorization Record.** A persistent per-agent record: owner, systems, authorised, not authorised, what the credential allows, the gaps, the controls, when it was last reviewed.
- **R-6 — The whole loop.** Pick, see, compare, find the gaps, fix, keep proving it.

## Six frictions, four levers

Four changes carry all six recommendations, and one carries half of them on its own: put the free diagnostic in front of the sale. `MAP-A-GRANT.md` already exists, is already free, already ships in every public template zip, and prints exactly the four numbers the note asks for — it is only surfaced after a £500 purchase. Moving it is a re-ordering, not a build.

## The 11 proposals

Two are *won't do* and three need a ruling. Each carries what it would cost.

### P-1 — Keep the delta exactly as it is

- **Our stance:** Won't do
- **Answers:** K-1 · F-3
- **Cost:** Effort none · Touches nothing · Risk none

> The core idea of comparing what an agent can do versus what you actually want it to do, what you don't want it to do, and what's actually stopping it. That feels like the most powerful part of the product.

Nothing changes underneath. The four-way comparison, the barrier on every row, and the fact that the delta is computed rather than stored are the product, and the note agrees.

But the counts are already on every catalogue tile and nobody reads them. Every tile carries what the agent can do, what was wanted, what is unwanted, and what has nothing in the way. A synthetic run last week had a staff engineer skim past them and never come back, because the explainer sits further down the page than the tiles do. So the asset the note calls the most powerful part of the product is already on the page and is not landing.

This is a placement problem, not a product problem, and it is fixed by P-6 rather than by touching anything here.

### P-2 — Keep the disclosure, including the parts that cost us sales

- **Our stance:** Won't do
- **Answers:** K-3
- **Cost:** Effort one paragraph · Touches /d/t3/, /d/t4/ · Risk none

> You're very clear about what has and hasn't been proven, what isn't live yet, and what the product does and doesn't claim to do. For a security product, that actually builds a lot of trust.

No change, and it is worth saying why out loud. The claim ledger, the “never sold once” chips on the two upper levels, and the page refusing to call a professional sign-off a signed opinion each cost a sale in testing and each bought the credibility back. The investor persona in last week’s run stayed to the end because of that refusal and said she would buy second but not first.

One gap it opens that we have not closed. Disclosing that a level has never run raises an obvious question — what happens to my money if I am the first and it goes badly — and nothing on the site answers it. That is a real hole created by the honesty, and it should be filled rather than used as a reason to be less honest.

### P-3 — No accounts and no forms is the constraint everything else has to fit

- **Our stance:** Needs a ruling
- **Answers:** K-4 · R-1 · R-4
- **Cost:** Effort a ruling, then 1–3 days · Touches the no-forms check, the footer claim · Risk a claim on every page

> I also really like that the store itself follows the security philosophy of the product. No accounts, forms, analytics, cookies, etc.

This is the asset and the design problem at the same time, and it is worth being explicit about the trade. There is no <form>, <input>, <textarea> or <select> anywhere in the built site and a check refuses any release that grows one. That is why filtering is chips, quantity is a pair of buttons, and a discount code arrives in the address bar.

Both of the interactive things the note asks for need somewhere to type. R-1 wants a capability list pasted back; R-4 wants a deployment described. Neither is possible under the rule as written.

Three ways out, and this is the one decision on this page that is not ours to make:

- **Keep it whole.** The buyer runs the diagnostic in their own agent and reads the answer there. We publish the prompt and the scoring, and never see or receive anything. Ships this week, weakest experience.
- **One editable page.** An editable region on the diagnostic page only, marked as such, writing to the reader's own browser and posting nowhere. Keeps “collects nothing” literally true; makes “no field” need a footnote.
- **Move it into the vault.** A bought vault already has an app that can take input. Best experience, but it sits behind a purchase, which is exactly the wrong side of the paywall for a diagnostic.

### P-4 — A plain sentence first, the precise word one click away

- **Our stance:** Do now
- **Answers:** F-1
- **Cost:** Effort copy, ~1 release · Touches every content page · Risk low

> There are a lot of concepts to learn before I really understand what I'm buying… I wouldn't necessarily simplify what's happening underneath, but I would simplify the jargon and visualization.

Agreed, with one boundary: gloss the vocabulary, do not rename it. Grant, mandate and delta have exact meanings, the ledger is keyed on them, and the barrier column only makes sense if the three stay distinct. Renaming them to something friendlier would make the site easier to read and harder to check, and checkability is the whole argument.

So: every page leads with the plain sentence and carries the precise term as a link. “Your setup” before “shape”. “What it is allowed to do” before “mandate”. “The gap” before “delta”. The precise word appears in the same sentence, once, linked.

A glossary page is not the fix. If a reader has to leave to understand the page they are on, the page failed. One exception worth flagging: licence to operate is already constrained by an open naming collision on this estate — a second phrase in the same vocabulary means the opposite thing — so that one is not free to re-word until the collision closes.

### P-5 — Rename the four rungs, keep the identifiers

- **Our stance:** Do now
- **Answers:** F-4 · R-2
- **Cost:** Effort copy + 4 SKU letters · Touches products.yml, every level label · Risk low

> I'd also simplify the four levels. Something along the lines of Template, Live Policy, Deployment Review, and Professional Sign-off is much easier for me to immediately understand.

Agreed, and there is already a mechanism for it. Level one was renamed from “the pack, by email” to “the pack, downloaded” two releases ago and its SKU letter moved with it. The codes on printed cards are t1–t4 and they do not change, which is what makes a rename cost no reprinting.

One quibble with the proposed names. Live Policy reads as something that watches the agent at runtime, and £50 does not do that — it is the same document as £5 as a vault you hold the keys to, with your name on the licence. Calling it live would promise the thing that only exists after lever D. Suggested instead: Template · Your Vault · Deployment Review · Professional Sign-off.

Worth your view on that one specifically — if Live Policy is what a buyer actually wants to hear, the honest response is to build the thing rather than to borrow the name.

### P-6 — Put the free diagnostic at the front door

- **Our stance:** Do now
- **Answers:** F-2 · F-3 · R-1 · R-6
- **Cost:** Effort 1 release for the shippable form · Touches a new page, the home page, /policies/ · Risk depends on P-3

> Right now you're telling me there is a problem and then selling me the policy. I'd rather discover the problem myself and then have you offer me the solution.

This is the biggest thing in the note and it is mostly a re-ordering. MAP-A-GRANT.md is a prompt that reads an agent’s own configuration and prints exactly the four numbers the note asks for. It already exists, it is already free, and it already ships inside every public template zip. Today it is only surfaced on the page a buyer reaches after paying £500.

The new front door. A page headed with the note’s own question, a row of vendor tiles, and then: copy this prompt, paste it where your agent runs, read what it prints. It asks for no credential, it does not act, and its last line says so. The buyer discovers their own gap, in their own deployment, before anything is sold to them.

Then the offer lands differently. Instead of “here is a policy for the agent you run”, it becomes “you have three capabilities outside your mandate and two with nothing stopping them — here is the document that fixes that”. Same product, and the buyer wrote the first half of the pitch.

What it depends on. How far this goes depends entirely on P-3. Publishing the prompt and the scoring is shippable this week with no ruling at all; rendering the buyer’s numbers on our page needs somewhere to paste them.

### P-7 — The £5 — and it is not ours to move

- **Our stance:** Needs a ruling
- **Answers:** F-5 · R-3
- **Cost:** Effort 0 to 1 release · Touches the frozen price table · Risk a ruling, not a build

> I'm also not sure about the £5 price point… there is a risk that it makes something pretty sophisticated feel like a commodity template.

Two independent reports now say the same thing. Yours, and a synthetic staff-engineer run last week that said “five pounds is almost too cheap — it made me assume it was a lead magnet and I nearly did not click. The price made me trust it less, not more.” Two readers arriving at the same reaction from different directions is the strongest signal in the note.

But the £5 is doing a job. The same persona bought at £5 specifically to find out whether the thing was real, and the purchase is what produces an order reference, which is what makes the handover to riskmandate.ai work at all. Removing the price removes a qualification step and a tested flow.

A price is the project lead’s to set and not the builder’s. The four prices are frozen in a table that only moves by a ruling in the commit that says so. So this is a recommendation with three options and no decision:

- **Recommended.** Free diagnostic (P-6), £5 pack stays. The free thing becomes the answer; the £5 becomes the artefact. The commodity reading goes away because the free tier is now worth more than the paid one used to be, and nothing already built is thrown away.
- **Template free, start at £50.** Closest to what the note proposes. Costs the frictionless first transaction and the order-reference flow that is built and tested, and makes £50 the first thing anybody ever pays, which is a much harder first yes.
- **Raise it.** £25 or so. Fixes nothing about the perception and loses the only frictionless entry we have.

### P-8 — Let them describe the deployment before they pay for it

- **Our stance:** Do now
- **Answers:** F-6 · R-4
- **Cost:** Effort 2–3 releases · Touches /lab/, /d/t3/, the buyer pages · Risk medium — new output, no new mechanism

> Instead of buying first and then figuring out what information I need to send you, let me describe my deployment first… Then show me a preliminary mandate and say, "We can validate this against your actual deployment."

Agreed, and two thirds of it is already on the site in the wrong clothes. There is a tool at /lab/ that takes a described deployment — entirely through chips, so it survives the no-forms rule — and turns it into a depth band. It is currently framed as a pricing instrument and is explicitly marked as something you cannot buy from.

What has to change is the output and the framing, not the mechanism. Instead of emitting a band, it emits a draft mandate: here is what you have told us this agent should and should never be allowed to do, written in the form the product actually ships. Then the offer: we can validate this against what the credential really permits.

It also closes a hole a synthetic run found last week. The £500 page described its own process two ways and the post-sale page a third, and carried no duration at all. That is now fixed, but the deeper problem is the one you named: the buyer is asked to commit before they can see what they are committing to.

### P-9 — The Authorization Record — most of it is already the vault

- **Our stance:** Do next
- **Answers:** R-5
- **Cost:** Effort a quarter · Touches a new org-level surface · Risk medium

> Some kind of Agent Passport or Agent Authorization Record. Basically a persistent record for every agent that says who owns it, what systems it touches, what it's authorized to do, what it's not authorized to do, what the underlying credentials technically allow, where the gaps are, what controls exist, and when it was last reviewed.

Held against what a £50 vault already contains, this is about seventy per cent shipped. A vault already carries the grant, the mandate, the delta, the barrier on every row, a licence with the holder’s name, its own version history and a read key that can be handed to anybody who asks how an agent is governed. That is most of the list.

Three things are genuinely missing. An organisation-level index — the vault is per agent, and nothing says which agents exist or who owns them. A last reviewed date and a cadence. And the re-run that compares today’s grant against the committed mandate, which is the only part that is a new build rather than a new view.

Naming. “Passport” implies issuance by an authority, which is the same trap licence to operate is already caught in on this estate — there is an open collision on exactly that idea and a build check keeps the phrase off every page until it closes. Agent Authorization Record is both safer and more accurate, and is the name we would use.

Marked do next rather than do now only because P-6 and P-8 change who arrives and what they arrive knowing, and this should be designed against that rather than against today’s traffic.

### P-10 — “Continuously prove” is a different business, not a feature

- **Our stance:** Needs a ruling
- **Answers:** R-5 · R-6
- **Cost:** Effort a business decision first · Touches the model, not the site · Risk high — a promise that has to hold

> …continuously prove the agent is operating within its mandate.

Five of the six steps in your target loop are a re-ordering of things that exist. The sixth is not. Pick, see, compare, find the gaps, fix — all of that is the current product in a better order. Keep proving it is a recurring comparison of a live credential against a committed mandate, which means a schedule, a re-run, a diff, and somebody who notices when it changes.

That is a subscription. Different delivery, different pricing, different support obligation, and a different promise: today we sell a document that is true when it is written, and that would be selling a claim that stays true. It is almost certainly where the value is, and it should be decided as a business question rather than arrived at by adding features.

One thing worth noting. The mechanism already half exists in a direction nobody has used yet: a vault has history, and a re-run of the diagnostic produces a comparable artefact. What is missing is the cadence and the person, not the maths.

### P-11 — Lead with the question, but not on the home page yet

- **Our stance:** Do next
- **Answers:** F-2 · R-1
- **Cost:** Effort copy, after P-6 · Touches the home page, /policies/ · Risk low, if sequenced

> "Which agent do you run?" is fine, but I think the more interesting question is something like: "What can your AI agent do that you didn't actually authorize?"

The question is better and we would use it — on the diagnostic, not yet on the home page. It is a promise: ask it and the next screen has to answer it. Putting it on the front page before P-6 ships means the reader is asked a question and then handed a catalogue, which is worse than the catalogue on its own.

So the order matters. P-6 first, the question as the heading of that page, and only once it works does it move up to the home page. If P-3 lands on the weakest option and we never render the numbers ourselves, the question has to be softened to match what the page can actually deliver.

One thing already true that we do not say. The vendor tiles the note asks for are already the catalogue — ChatGPT, Claude Code, Gmail, GitHub Actions, n8n and eleven more, one per real deployment shape. What is missing is not the tiles; it is the question above them.

## Send it back

The page at https://store.sgit.ai/review/ carries a verdict control and a reason box on every proposal, and copies the result out as markdown or JSON. Nothing typed there is submitted anywhere: no page on this site opens a network connection.


---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
