---
title: The three buyers, and what each one buys
description: "Three buyers, ordered by opportunity rather than presented as three equal doors: a team running agents they already granted credentials to, an investor backing a company, and a startup about to meet diligence. Which of the six offers each one is shown, which were actually built for them, and — for one of the three — that none were."
lead: "**Order matters here, and the page reflects it.** Three buyers, and they are not equally served by what is on this site. One has a market above it and nothing underneath. One has nothing at any price. One has two funded incumbents and a free tier already sitting under it, and is here only as a **reverse sale**. The grouping below adds no offer and no price: it is a second index over the same six, and **the third group has nothing built pointing at it at all.**"
order: 3
toc: true
wide: true
---

## The routing, in one table

{{offers-by-buyer}}

Each row has a page of its own. The offers on it are the same records the
[offer page](/offers/) renders — the same prices, the same states, the same
delivery pages — sorted by whose question they were built to answer instead of by
what they cost.

## 1. You run agents today

**The market anchors between eight and one hundred and fifty thousand dollars, and
nothing sits underneath it.** {{claim:agent-market-gap}}

That gap is the whole opportunity. Somebody running an agent today, who wants to
know what they actually granted it, has a choice between a five-figure engagement
and nothing. [Tier 1](/d/t1/) is ten pounds and answers the smaller version of the
question; [tier 2](/d/t2/) is the version with the regulation attached.

**What they are buying is the delta**: the union of what a credential permits,
against what the holder is authorised and expected to do, and the excess authority
between the two. **That delta is computed and never stored.** It is not a thing we
keep about you.

[Everything this buyer is shown &rarr;](/for/agents/)

## 2. You are backing a company, and want somebody to look

**No productised, affordable, signed investor review exists at any price
— and every component of one is already written.** {{claim:investor-review-absent}}

That is the emptiest quadrant on this page, and the one the top two tiers point
at. [Tier 3](/d/t3/) is a person reading a situation. [Tier 4](/d/t4/) is a team.

**It is also where the constraint bites hardest.** Selling buyers the question,
selling suppliers the answer, and selling an opinion that vouches for the
suppliers is the combination two industries have already regulated. So:

- **The company issues every opinion**, with an express non-assumption of personal responsibility on its face. A product sold on a named individual's judgement runs at the test for assumed personal responsibility.
- **The people who sell do not sign.** That constrains this site's own layout: the signature block and the checkout must not name the same person, and on this site neither names anyone at all.
- The **signed opinion is a separate add-on with separate wording**, and that wording does not exist yet. {{claim:opinion-wording-absent}}

[Everything this buyer is shown &rarr;](/for/investors/)

## 3. You are a startup, and only as the reverse sale

**Two funded incumbents, a free tier beneath them, and both already publish the
answer.** Selling a founder a security posture document is selling into a
commoditised tier. {{claim:founder-tier-commoditised}}

**The unoccupied offer is the reverse one: telling a founder what diligence will
find, before it runs.** Same components, opposite direction, and it is the only
version of this that is not already free somewhere.

**And it is not on the price list.** The startup page is assembled entirely out of
tiers built for the other two buyers — you buy [tier 3](/d/t3/) or
[tier 4](/d/t4/) and say which direction you want it run in. There is no seventh
product behind that sentence, the page says so above its offers rather than below
them, and this row is why the grouping is called an index rather than a range.
{{claim:startup-offer-is-reverse-only}}

[Everything this buyer is shown &rarr;](/for/startups/)

## Why the groups are a view and not a range

**Because the alternative is how an offer list grows without anybody deciding to
grow it.** Three audiences, three pages, and within a month each page has a thing
of its own on it that nobody priced, nobody specified, and nobody can say the
state of.

So the grouping is mechanical. `data/buyers.yml` names offer ids and nothing else;
the build joins them to `data/offers.yml`; and the gate fails the release if a
group names an offer that does not exist, if an offer belongs to no group, or if
the set of groups changes. **A buyer page cannot contain a product**, in the same
way [the eight further offers](/catalogue/) cannot quietly widen the four that are
for sale.

## What none of the three is buying

**Raw findings.** Recall-optimised agents run at 0.388 precision — about three
findings in five are wrong {{claim:precision-0388}}. A list of findings at that
precision is not a product, it is a homework assignment with a bill attached.
**What is sold is triage**: every finding that reaches a buyer has been reproduced
first, not reviewed.

**A verdict about a third party.** Where this estate names a competitor, a vendor,
a standards body or a platform, it publishes the record — facts, dates, sources —
and never the verdict, with no evaluative adjective attached to anybody's name.
That rule holds on the pages you can read and it is [the reason the documents area
is still closed](/dev-packs/).

**A mark of conformity to a standard.** Nothing here is one, nothing here claims to
be one, and the language of conformity marking is kept off this site entirely —
it raises the standard of care beyond ordinary negligence for no benefit to a
buyer.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
