---
title: Five prototypes of one purchase
description: "Five interfaces over the same configurator for the grant-and-mandate mapping work: an interview, a ladder, an estate board, a delta matrix and a scenario start. Each produces the same JSON brief. Nothing on any of them can be bought."
lead: "**Nothing in this area can be bought.** These are five prototypes of a purchase flow for work that is fulfilled by people — mapping what the agents a company already runs were **granted**, what they are **expected** to do, and writing the **policies** that would close the gap. Five interfaces, one model, and **one JSON brief that every one of them produces identically**. The interface is the variable. The document is not."
order: 4
toc: true
wide: true
head_css: /assets/lab.css
---

## What is actually being sold here

**Two things, and neither of them is a scan.**

**A map.** Every agent surface a company runs, the credential behind it, and what
that credential permits. Then the other half: what each one is actually authorised
and expected to do. **The gap between the two lists is the product** — permitted,
and nothing anybody wrote down would need it.

**A policy set that would close it.** Written against the estate that was just
described, one policy per gap, each naming the grant it constrains. Not a template
with a company name substituted in.

**A named security professional does this work.** Nothing in it runs by itself
today, the seven-role team these prototypes describe is a specification rather
than something staffed, and which parts of it could later be done without people
is a decision nobody has taken. {{claim:lab-fulfilment-is-people}} So what these
pages produce is **the brief that team starts from** — the thing a first call
would otherwise be spent assembling.

## The same question, from three sides

The three buyers on this site arrive at the same map from different directions,
and the configurator changes its frame accordingly. [Who each one is
for](/audiences/).

| | Arrives asking | What the map is drawn for |
|---|---|---|
| **[You are a startup](/for/startups/)** | What does our estate look like to somebody who is about to ask? | **Map it upwards.** Diligence is coming, the questions are the same every time, and the difference is whether the answers already exist in writing |
| **[You are an investor](/for/investors/)** | What is the agent in this company actually doing, and what was it allowed to do? | **Map both sides** of a company you do not operate: the permitted half from its credentials, the expected half from its own account |
| **[You run agents today](/for/agents/)** | What did we actually grant the things we are already running? | **Map your own estate.** The credentials were issued over months by different people, and no document says what their union permits |

## The five

{{lab-views}}

Each one is a hypothesis about how somebody would rather describe their estate,
and each has a column saying what is wrong with it — **five options presented with
only their strengths is a menu, not an experiment.** Which of them becomes the
real one, if any, is not decided. {{claim:lab-is-a-prototype}}

## The model all five render

Every prototype reads one file. The sections below are the questions, the weight
column is what moves the price, and both are published here because **a page that
asks somebody twenty questions owes them the list before they start**, and a
weighting a reader cannot see is a price a reader cannot check.

{{brief-model}}

**The configurator does not compute a price.** Weighted selections add up, the
total lands in a band, and **the band names one of the four tiers that already
exist and its price.** Nothing here invents a number — a price is the first thing
[the pack](/dev-packs/) says may not be invented, and a checkout that emitted
"£347" would be inventing one with extra steps. A build check fails the release if
a band names an offer that is not on [the offer list](/offers/).
{{claim:lab-price-is-a-band}}

**The prebaked starts are hypotheses.** Nobody has counted how common any of those
five shapes is. Each brief records which one it started from, so the team reading
it can tell what was assumed from what was answered — which is the only thing that
makes starting from a guess safe rather than fast.
{{claim:lab-scenarios-are-hypotheses}}

## What a brief carries, including what it does not know

The output is one JSON document. Beside the estate, the grants, the mandates and
the deliverables, every brief carries two fields that most configurators would not
emit:

- **`excess_authority`** — the grants you ticked that no mandate on the brief would need. Computed from edges published in the model, so a reader can disagree with a specific edge rather than with a verdict.
- **`unknowns`** — what this brief could not establish. An empty expected column. A deliverable whose thing does not exist yet. A grant that a named surface normally carries and you removed. **A brief that names its own gaps is worth more to the team reading it than one that reads as complete and is not**, and this is the same discipline [the ledger](/ledger/) applies to the rest of the site.

## What happens to it

**Nothing, unless you send it.** A brief is written to your browser's own local
storage and reaches nothing else. There is **no form, input, textarea or select
anywhere in this site's output**, and **no page that sells anything opens a network connection** —
both are build checks rather than intentions — so exporting a brief hands the file
to you. {{claim:lab-brief-stays-local}}

**What the deliverables look like is a separate question**, and it is not answered
here. This area is the purchasing half. Examples of what comes out the other end
belong on their own pages and do not exist yet.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
