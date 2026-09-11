---
title: All six, side by side
description: "The four tiers and the two add-ons in one table: the question each answers, its price, what is true of the thing behind it today, how it is paid, and the stable offer identifier a printed code redirects to."
lead: "**Four tiers and two add-ons.** Four prices are set, one range is deliberately wide, and the add-ons are banded rather than priced. Every number on this page comes from one file, and a build check holds each of them against the pack that set it — because these prices go onto **printed cards**, and a printed price cannot be corrected from a conference floor."
order: 2
toc: true
wide: true
---

## The table

{{offer-table}}

## The same six, by who each one was built for

**This page is the price ladder. [The other way in](/audiences/) is by who is
climbing it** — which is the question somebody actually arrives with, and the
reason the home page asks it first.

{{offers-by-buyer}}

## The six, in full

{{offers}}

## Why each number is that number

**No price on this site was invented, and none of them is positioning.** Three of
the six are arithmetic and the workings are here.

{{prices-why}}

The floor is the clearest of them: **at £5 the fixed card fee alone is about four
per cent of the transaction**, so £10 is the floor and £5 is not a cheaper version
of it — it is a worse one. At the other end, **at £10,000 a card costs up to about
£250**, which is why tier 4 does not take one. {{claim:card-fee-floor}}

**Prices are in pounds.** Pricing in euros while settling in pounds adds about two
per cent, and that two per cent buys nothing. {{claim:pricing-in-pounds}}

## The offer identifier is the stable part

A printed code redirects to `/d/<id>/` and nothing else about it is load-bearing.
Not the host, not the path above it, not a word of the copy.

That is deliberate, and it is the one piece of engineering this site does purely
because of a disagreement. **A ruling of 10 September placed a storefront under the
risk product rather than on the platform domain.** The instruction in hand
overrode it and named this host. The ruling stands on the record, unedited, and
the build treats the host as moveable: every internal link here is relative, the
host appears in no sentence of copy, and the identifiers above do not change.
**If the site moves, it costs a DNS record and no reprinting.**
{{claim:domain-ruling-overruled}}

## How each one is paid for

**A standing payment link carries exactly one price, and only one offer on this
page has one.** Tier 1 is £10 and could hold a link tomorrow. Tiers 2 and 3 are
bands, so their link is issued once the band is fixed for the case; tier 4 is
above the threshold where a card makes sense at all; and the two add-ons are
priced against the depth band of whatever they attach to. **That is arithmetic
about how a fixed-price link works, not a policy about who may pay.**
{{claim:checkout-bands-have-no-standing-link}}

**No link has been created for any of them.** Every offer carries an empty
checkout field, so every card above shows its code and its delivery page rather
than a button, and this page says which of the five reasons applies to each.
Issuing one is a single pasted line, and the build holds whatever lands there to
the payment provider's own checkout hosts over HTTPS.
{{claim:checkout-links-not-issued}} [How the rails work, and why they never
meet](/paying/).

## What is not on this page

**Eight further offers are specified and none of them is for this week.** The
amendment subscription, the divergence report, the rendering diff as a
verification service, crosswalk resolution, the write-only vault link, the vault
as a data room, the threat-model estate, and the infographic generator with a
purchase page. [They are listed here](/catalogue/) so that nobody proposes them as
new.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
