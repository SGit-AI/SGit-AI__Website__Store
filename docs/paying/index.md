---
title: The two rails, and why they never meet
description: "Payment links with printed codes for everything at the event and everything below about a thousand pounds; the cloud marketplace for business buyers above it, after a conversation. They are strictly separated, the separation is a rule rather than a preference, and no link has been issued yet."
lead: "**Both rails exist. They must never appear as a choice on one transaction.** One is a payment link with a printed code beside it. The other is a cloud marketplace, above roughly a thousand pounds, after a conversation. The reason they are kept apart is not taste — it is that the marketplace's seller terms say a seller is **not permitted to collect customer payment information at any time**."
order: 5
toc: true
---

## The two rails

| | **Payment link, with a printed code** | **The cloud marketplace** |
|---|---|---|
| **For** | Everything on the price list, all four levels | Business buyers who would rather have it inside terms they already hold, after a conversation |
| **Why** | A payment link is an online payment, so no cross-border rule applies | The buyer already holds the marketplace's legal terms |
| **What it removes** | The card reader, and the declined tap | The master agreement, the vendor onboarding, the new purchase order |
| **What it costs** | The provider's ordinary card fee | **0.5 per cent**, falling to zero inside a qualifying multi-product solution |
| **State** | {{claim:card-reader-refused}} | {{claim:marketplace-registration}} |

## Who takes the card, and where

**Two rails, and both are payment links on the provider's own pages.** Stripe is
set up; SumUp is being set up. **Running both is deliberate** — which one gives a
better workflow is a thing to find out rather than to assume, and the loser costs
nothing to drop because neither one holds the catalogue.

**Nothing on this site collects anything.** No form, no input, no field, no
account, no cookie. The provider takes your name, your contact and your card on
its own pages, which is the only place a card number should ever be typed. A build
check holds every page here to that, and a second one holds every page to opening
no network connection at all.

**What reaches the provider is the amount and your order reference.** The
reference carries the product codes for everything you picked, so matching it
against the name and contact the provider captured gives the whole order.
[How that works, in three steps](/how-it-works/).

### Every level is one price, so every level can hold a link

The four levels are £5, £50, £500 and £1,500 — **single prices, not bands**, which
is what a standing payment link needs. The banded tiers and the deposit that this
page used to describe belonged to the offer line replaced on 15 September: there is
no band left to fix and no engagement left to deposit against.
{{claim:checkout-bands-have-no-standing-link}}

**No link has been created on either rail.** [Your order](/cart/) renders the
button as unissued and names the rail that is missing, rather than showing
something that looks live: **a greyed-out button is a lie about which half of the
work is done.** Pasting one line into `data/checkout.yml` turns a rail on, and the
build holds whatever lands there to that provider's own checkout hosts over HTTPS.
{{claim:checkout-links-not-issued}}

### Why the catalogue is not inside either provider

**Sixty-two product codes maintained in two places is sixty-two codes that will one
day disagree.** The catalogue lives here, in one file, checked on every build; the
provider takes an amount and a reference; neither side has to know about the other.
It also means adding a product is a build rather than a build plus a console.

## Why a link, and not a card reader

**A United Kingdom card account cannot tap in Portugal.** The provider declines the
transaction on detecting a different country, and says so in those words. A card
reader bought for the event would have been a box that says no, in public, to the
first person who tried to pay with it.

**A payment link is an online payment.** No cross-border rule applies to it. The
buyer opens their own phone, on the provider's own page, and pays. Nothing on this
site ever sees a card number, because nothing on this site ever handles one.

**So no card reader was bought**, and the four codes on the cards are four links.
{{claim:card-reader-refused}}

## Why the marketplace is a conversation and not a button

**The marketplace's seller terms state that a seller is not permitted to collect
customer payment information at any time.** {{claim:marketplace-no-customer-payment}}

A checkout button beside a marketplace button, on one page, for one transaction,
is a design that walks straight into that. So the marketplace is not a second
payment option here. **It is a different route with a different threshold**, and
you reach it by talking to somebody, not by clicking something.

**The pitch is procurement, not discount.** A buyer who already has the
marketplace's legal terms does not need a master agreement, a vendor onboarding
round, or a new purchase order. That is worth more than a percentage to the person
who has to get the purchase through, and it is the actual reason to use the rail.
The fee is **0.5 per cent**, and falls to zero inside a qualifying multi-product
solution. {{claim:marketplace-fee}}

**Registration is the long pole: four to eight weeks.** The listing is a November
surface. Nothing on this site depends on it. {{claim:marketplace-registration}}

### One correction, carried here rather than dropped

**Professional services listings do not draw down committed spend on the cloud
provider.** Three independent sources state the exclusion.

An earlier version of the marketplace argument said the opposite. That version is
on no page of this site, and this paragraph exists so that if somebody repeats the
old claim in a room, the correction is findable rather than remembered.
{{claim:no-committed-spend}}

## Where each code lands

Four codes, one per level. **The identifiers did not change when the prices did**,
which is the whole reason the pack said to keep them stable: a repricing costs no
reprinting, and a card already made still lands on the right page. Each redirects
to a delivery page that says **what arrives and what does not**:

- [`t1`](/d/t1/) — £5, the pack by email
- [`t2`](/d/t2/) — £50, a working vault you hold the keys to
- [`t3`](/d/t3/) — £500, corrected for your situation
- [`t4`](/d/t4/) — £1,500, two sessions and [a professional signs it](/booking/)

The cards the codes are printed on differ only in **the question on the front** and
**the destination of the code**, which makes the fact set identical across every
variant by construction rather than by checking.

**The codes are the only part of this with a hard date.** The event is **17 and 18
September 2026, in Lisbon**. The merchandise surface, [the eight further
offers](/catalogue/) and the marketplace listing do not depend on it, and nothing
on this site pretends otherwise. {{claim:event-dates}}

## What this site does with a payment

Nothing. It is a static site: **no page here opens a network connection at all**,
there is no form, no cookie, no analytics, and no card number ever reaches it.
Paying happens on the payment provider's own pages, which is the only place a card
number should ever be typed. A build check holds that line on every release.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
