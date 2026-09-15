---
title: How buying works
description: "Pick shapes, pick levels, and pay on the provider's own page. Your order lives in your browser, the payment provider takes your name and card, and what reaches it is an amount and an order reference carrying the codes for what you bought."
lead: "**Three steps, and this site does not collect anything in any of them.** You build an order in your own browser, you get a reference, and you pay on the payment provider's own page — which is the only place a card number should ever be typed. **There is no form, input or field anywhere on this site**, and a build check holds that line."
order: 3
toc: true
---

## The three steps

**1 · Pick.** Choose an application from [the catalogue](/policies/) and a level.
Add as many as you like — different agents, different levels, more than one of the
same thing. Your order lives in this browser and nowhere else.

**2 · Get your reference.** [Your order](/cart/) carries a reference like
`SG-K7M3QB` and an order line listing the product code for everything in it. Copy
it. It is not an account and it is not stored anywhere but your browser.

**3 · Pay.** Two rails, and you pick one. The provider takes your name, your
contact and your card on **its own pages**. What this site hands it is the amount
and your reference.

## What a product code looks like

`ABP-GML-V`

- `ABP` — an Agent Behaviour Policy.
- `GML` — the shape. Gmail, read-only scope, in this case.
- `V` — the level. `P` is the pack, downloaded on the page you land on after paying; `V` a working vault; `C` corrected for your situation; `S` two sessions with a professional signing it.

**A quantity above one is written `ABP-GML-V*2`.** The whole order line is your
reference followed by one code per item, which is short enough to fit in a
payment reference field and specific enough to say exactly what was bought.

## Why the catalogue is not inside the payment provider

**Sixty-two product codes maintained in two places is sixty-two codes that will one
day disagree.** The catalogue lives here, in one file, checked on every build. The
provider takes an amount and a reference. Neither side has to know about the
other, and there is no synchronisation to get wrong.

It also means **adding a product is a build**, not a build plus a console.

## Two rails, on purpose

Both are payment links on the provider's own pages. **Running two is deliberate:
which one gives a better workflow is a thing to find out rather than to assume**,
and the loser costs nothing to drop because neither holds the catalogue.

| | What it is | What it takes from you |
|---|---|---|
| **Stripe** | A payment link that takes the amount you enter | Name, email and card, on Stripe's own pages |
| **SumUp** | A payment link that takes the amount on the address | Name, email and card, on SumUp's own pages |

**Neither link has been created yet.** [Your order](/cart/) says so on the button
rather than showing something that looks live — a greyed-out button is a lie about
which half of the work is done.

## What happens after you pay

**The first two levels are produced without anybody being scheduled**, so they do
not wait on a conversation. The upper two do: the corrected level needs the details
of your situation, and the two-session level needs a time in a calendar.

**What arrives, at every level, says what it does not cover as well as what it
does.** That is on each level's own description rather than in a paragraph
somewhere, because a page that only says what you get is the half that gets
somebody into trouble.

## What this site never has

**No account.** There is nothing to sign into and nothing that remembers you.

**No form.** Not a search box, not a newsletter, not a contact field. Filtering is
buttons, quantity is buttons, and everything a payment needs is taken by the
payment provider. A build check refuses the release if a `form`, an `input`, a
`textarea` or a `select` reaches any page.

**No network call.** No page here opens a connection at all: no analytics, no
cookies, no fonts from anywhere else, no catalogue fetched while you read. Every
byte is served from this domain, and the catalogue is promoted at build time with
the hash of what it was read from.
