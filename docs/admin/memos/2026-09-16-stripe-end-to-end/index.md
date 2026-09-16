# Stripe end to end, with their SKUs — and a customer even at 100% off

*2026-09-16 · Voice memo, transcribed*

Run the real Stripe purchase flow rather than an amount-only link, so a buyer handed a hundred-per-cent code still becomes a customer with an email. Then leak codes on specific journeys. And start capturing the work as units on a board.

## The memo, word for word

> Okay, so just some quick comments on the Stripe and um, sum up integration. Um, let's now create a workflow where we basically do an end-to-end flow with Stripe uh, using their SKUs and using their um, their workflows. But with the um, still the purchasing workflow, because we at least want to capture their emails and their contacts and have them as a client in Stripe. Stripe supports payments with 100% discount, which is what we want to do. So let's just figure out that workflow. Um, and basically then what we do is we start using discount codes, which we can leak on the main site uh, on specific journeys. But um, I really want to have that sort of end-to-end flow with, with Stripe. Um, yeah, but so that's now a task. And what I'm going to do next is I'm going to do a brain dump of tons of tasks and tons of activities, which I want to do, but can you capture them as units of work in our admin environment and actually even create a Kanban board, which I'll give you the link below for where to be inspired. And, um, and then let's start capturing all these workloads so that we're ready for the event.

## What we read in it

### The ask is the customer record, not the discount

A hundred-per-cent code is a means. What it buys is somebody standing at a stand going through a real purchase and coming out the other side as a row in Stripe with an email on it. That reading is what makes the rest of the memo coherent — SKUs, their workflows, capture the contacts, and only then the discount.

### It reverses a position this store had published

The rails plan said in as many words that neither provider gets a product list, a price list or a shape, and gave a good reason: a catalogue in two places will one day disagree. That is now overruled for Stripe. The overrule is written on the rails page above the old reasoning rather than instead of it, and the drift it re-opens is a named task rather than a risk somebody remembered.

### Sixty-two SKUs turned out to be eight prices

The objection was sized wrong. A price on this store does not vary by shape — level two is £50 whether the subject is a browser agent or a payments bot — so Stripe needs four levels, two add-ons and two deposits. Eight rows that move when a price moves is a duplication worth living with; sixty-two would not have been.

### One finding came out of writing it down

A hundred-per-cent order creates no charge, so a webhook keyed on a succeeded payment would see every paid order and none of the free ones — exactly the set this rail exists to capture. Listen to the session, not the payment.

## What this does not decide

### Which journeys carry a leaked code

The memo says specific journeys and does not say which. A code on a first screen discounts a decision nobody has made yet; a code at the end of a level page discounts one somebody is in the middle of making. That is the project lead's call and it is a queued task.

### What the buyer lands on

A standing Stripe link cannot fill in the ?order= the handover contract documents. Resolving it needs the RiskMandate team.

## The work it produced

- **Take money at all** — https://store.sgit.ai/admin/work/take-money/
- **Leak the codes on purpose** — https://store.sgit.ai/admin/work/leak-the-codes/
- **Keep the record** — https://store.sgit.ai/admin/work/the-record/

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
