# Take money at all

No payment rail is live. Every checkout_url in data/checkout.yml is empty, so the store can be walked end to end and cannot be bought from. This is the workstream that ends that, and the shape of it changed on 16 September: the rail is no longer an amount-only link, it is Stripe's own catalogue and a real customer record behind every order including the free ones.

**1 of 10 done.** Status: `next`.

From the memo *Stripe end to end, with their SKUs — and a customer even at 100% off* (2026-09-16) — https://store.sgit.ai/admin/memos/2026-09-16-stripe-end-to-end/

- **TM-1 · Create six Stripe products and eight prices** — `next` — GBP, one-off, lookup keys SG-T1 to SG-ADD-OPINION. Copied from the generated catalogue file rather than typed out by hand. A price does not vary by shape, which is why this is eight rows and not sixty-two.
- **TM-2 · Set customer creation to always, and prove it on a £0 order** — `next` — The single setting most likely to be missed. Without it a hundred-per-cent order completes, the buyer sees a confirmation, and no customer record exists — which is the exact opposite of why this rail was chosen. Proof is a Customer visible in the dashboard after one free order, not a screenshot of the toggle.
- **TM-3 · Create three coupons and seven promotion codes over them** — `queued` — 25, 50 and 100 per cent. The seven strings are the ones data/discounts.yml already holds, so a code printed on a PDF at v0.1.11 still works. Every promotion code gets a redemption cap and an expiry.
- **TM-4 · Enable promotion codes on every link, prefill where a code was leaked** — `queued` — A link with the field switched off refuses a valid code with no explanation and the buyer blames themselves. Where a page publishes a code as part of a journey, the link on that page carries it already applied.
- **TM-5 · Bring the return address onto this site** — `next` — Superseded by the later memo the same day. This was “settle the ?order= contract with the RiskMandate team” and it was blocked on them. The buyer no longer leaves the store, so the success address is ours to render and the block is gone. What survives from the original is the real constraint: a standing Stripe link substitutes a session id and nothing else, so the landing page has to work from that.
- **TM-6 · Stand up the checkout.session.completed webhook** — `queued` — The step that unblocks a first paid order at £50, £500 and £1,500. Listen to the session, not the payment: a hundred-per-cent order creates no charge, so a handler keyed on a succeeded payment sees every paid order and none of the free ones. _Blocked on: Runs off this site. This site is static and opens no connection._
- **TM-7 · Take one real £10 payment and read the receipt** — `queued` — Every sentence on the rails page about what a receipt says is unverified. This is the task that makes them checkable. _Blocked on: TM-1 and TM-6._
- **TM-8 · Retire the browser-side discount arithmetic** — `queued` — A code is honoured in the browser today and the page says it is a demonstration. Once a promotion code exists on the rail there are two implementations of one rule, and the browser one can be edited by the person it is discounting. _Blocked on: TM-3._
- **TM-9 · Take SumUp's hosts from the rails, not from a constant** — `next` — check_checkout_links pins every destination to Stripe's two hosts. data/checkout.yml has declared SumUp's hosts since the rail was added and the check has never read them, so a SumUp URL pasted in today is refused by the gate with a message about Stripe. Five lines.
- **TM-10 · Write the two rails up as plans rather than intentions** — `done` — Shipped in v0.1.18 at /admin/rails/stripe/ and /admin/rails/sumup/, generated from data/admin/rails.json.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
