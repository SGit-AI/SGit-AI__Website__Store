---
title: The two rails, and why they never meet
description: "Payment links with printed codes for everything at the event and everything below about a thousand pounds; the cloud marketplace for business buyers above it, after a conversation. They are strictly separated, and the separation is a rule rather than a preference."
lead: "**Both rails exist. They must never appear as a choice on one transaction.** One is a payment link with a printed code beside it. The other is a cloud marketplace, above roughly a thousand pounds, after a conversation. The reason they are kept apart is not taste — it is that the marketplace's seller terms say a seller is **not permitted to collect customer payment information at any time**."
order: 4
toc: true
---

## The two rails

| | **Payment link, with a printed code** | **The cloud marketplace** |
|---|---|---|
| **For** | Everything at the event, and everything below about £1,000 | Business buyers above roughly £1,000, after a conversation |
| **Why** | A payment link is an online payment, so no cross-border rule applies | The buyer already holds the marketplace's legal terms |
| **What it removes** | The card reader, and the declined tap | The master agreement, the vendor onboarding, the new purchase order |
| **What it costs** | The provider's ordinary card fee | **0.5 per cent**, falling to zero inside a qualifying multi-product solution |
| **State** | {{claim:card-reader-refused}} | {{claim:marketplace-registration}} |

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

Four codes, one per tier. Each is a payment link, and each redirects after payment
to a delivery page that says **what arrives and what does not**:

- [`t1`](/d/t1/) — £10
- [`t2`](/d/t2/) — £50 to £100
- [`t3`](/d/t3/) — £150 to £1,000
- [`t4`](/d/t4/) — £5,000 to £10,000, and this one starts with [a conversation](/booking/)

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
