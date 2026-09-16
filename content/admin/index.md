---
title: The console
description: "The operations surface for this store: what is blocking a first paid order, the units of work in flight, the memo queue behind them, the payment rails, the reviews and the walkthrough. Public, like every page here, and kept out of the sitemap because it is not a selling surface."
lead: ""
order: 90
robots: "noindex,follow"
console: true
blurb: "<b>Everything here is public</b>, because every page on this site is — no login, no account, nothing gated. What is different is that it is not <em>advertised</em>: noindex, out of the sitemap, out of <code>llms-full.txt</code>. Anybody handed the address reads every word."
---

{{console-dash}}

## The queue, and how work gets here

**[The memo queue →](/admin/memos/)** — a memo from the project lead arrives
spoken, is kept here word for word, is read into a brief, and the brief is broken
into units of work. The reading is kept separate from the memo on purpose: what
somebody said and what we made of it are two different objects, and only one of
them is allowed to be wrong.

**[The board →](/admin/work/)** — those units, in four columns, grouped into
workstreams. A workstream never moves by hand; it moves because a task inside it
moved, so the summary cannot contradict the detail.

## Hand somebody a code

A code is a link, not something to type. Open one on the laptop you are holding,
or send it, and the shop comes up with the discount already on it and the four
prices repainted.

{{code-links}}

## Next: taking money

**[Both rails →](/admin/rails/)** — no payment rail is live, which is the single
fact that most shapes this store. {{claim:checkout-links-not-issued}}

| | |
|---|---|
| [Stripe](/admin/rails/stripe/) | The rail that turns a buyer into a customer, including a buyer who pays nothing. Six products, eight prices, three coupons — and a webhook that has to listen to the session rather than the payment, because a hundred-per-cent order creates no charge at all. |
| [SumUp — parked](/admin/rails/sumup/) | Taken off the store on 16 September for the first end-to-end MVP. The plan is kept rather than deleted, so turning it back on is restoring a record instead of rediscovering an argument. |

## Run it yourself

**[The walkthrough →](/admin/try/)** — a beta tester or an agent goes from the
catalogue to the page after payment in about four minutes, for nothing, with a
discount code printed on the page. Screenshots of every step, and a script an
agent can follow without a person in the loop.

The same thing as PDFs, for sharing or for reading away from a screen —
[by hand](/admin/downloads/store-walkthrough-by-hand-v0.1.11.pdf) (11 pages, every
screenshot) and [as an agent](/admin/downloads/store-walkthrough-as-an-agent-v0.1.11.pdf)
(7 pages, the assertions). Both are snapshots; the page is the source of truth.

## The record

| | |
|---|---|
| [Reviews, dated and kept](/admin/reviews/) | Every review of this store, newest first. A review is a moment locked: the version it was taken against, the screenshots, and a stance on every proposal in it. |
| [What happened to each memo](/admin/status/) | The join: every memo from the project lead, the units of work it became, the page each one built and the release it shipped in. |
| [The homepage concepts, reviewed](/admin/concepts/) | Three homepage directions drawn for this store from outside, screenshotted and measured against the live page — what is taken, what is refused, and the live pricing contradiction the review found. |
| [The claim ledger](/ledger/) | Every factual claim this site makes, with the state it earned and the date. Pages cite a claim and the chip links back here. |
| [What we do not say, and why](/disclosures/) | The words this site will not use, the sentence it will not print, and the naming collision that is still open. |
| [The dev packs](/dev-packs/) | The working documents behind the store, and the manifest of which of them are held back and why. |
| [Release history](/versions/) | Every release, what changed, and the commit it is. |
| [The purchase lab](/lab/) | The tool that turns a described deployment into a depth band. Nothing on it can be bought. |
| [What is not for sale yet](/catalogue/) | The offers that exist as specifications and have not been built. |
