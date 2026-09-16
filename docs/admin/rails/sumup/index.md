# SumUp

**Parked on 16 September. Not in the first end-to-end store.** — Planned, half set up, and taken off the store for the MVP — the plan is kept rather than deleted.

## Why

It came off on 16 September, and the reason is not that it was a bad idea. Stripe works: six products priced, three coupons, a reconciliation running on every release. A second rail that is half set up is a second thing to explain on a selling page and a second thing to keep true, and the first end-to-end store needs neither. Everything below is preserved rather than deleted — the argument for running two rails is a good one and it will be worth reading again the day the first one has taken money, which is exactly when it stops being hypothetical.

Running two rails is deliberate and it is a question, not a hedge. Which one gives the better workflow is a thing to find out rather than to assume. The cost of dropping one is no longer symmetric, though, and that is new: Stripe now holds eight catalogue rows and the customer records behind them, and SumUp holds nothing but amounts. Dropping SumUp costs a line in a config file. Dropping Stripe costs the customer list.

SumUp takes the amount on the URL, which is the opposite trade from Stripe. A link can be built for an exact amount without the buyer typing one — better at a stand, worse for a cart whose total the seller does not know in advance. The store already knows how to build either, because amount_param is a field in data/checkout.yml rather than a branch in the code.

And it cannot do the thing Stripe was just chosen for. An amount-only link has no product to discount and no customer to create. That does not make it the wrong rail — it makes it the rail for a tap at a stand, where the interaction is a payment and the contact was collected by a person standing there. Naming that now stops the two rails being compared on a test only one of them was built to pass.

And it is the rail with a card reader behind it. The store lists contactless as a fourth rail for the tap at a stand. The deposit split works there exactly as it does online: what is taken on the tap is the amount due now and the rest is invoiced on delivery. The rail changes; the offer does not.

## What this rail is handed

- **What the link carries** — reference for the order line and amount for what is due now, both on the URL. The pay page already builds exactly that shape.
- **Where it lands** — The same four success addresses as Stripe. Nothing about the handover is per-rail, which is the point of the handover being a contract rather than an integration.
- **Where the URL goes** — The same one line in data/checkout.yml, which already declares pay.sumup.com and checkout.sumup.com as this rail's hosts.
- **The cross-border limit, restated** — A United Kingdom card account cannot tap in Portugal and the terminal says so in public. The reader is for a seller standing where their account is; the link is for everywhere else, and at the Lisbon event the link is the rail.

## The steps, in order

1. **Finish the account** — It is the half-done one. Stripe is set up and this is not, which is the only reason Stripe is first rather than a judgement that it is better.
2. **Fix the host check before pasting a URL, not after** — check_checkout_links pins every destination to buy.stripe.com or checkout.stripe.com — Stripe's hosts only. data/checkout.yml has declared SumUp's two hosts since the rail was added, and the check has never read them. A SumUp URL pasted in today is refused by the gate with a message about Stripe. The check should take its allowed hosts from the rails rather than from a constant. _Blocked on: Blocked on nothing. It is a five-line change and it is this page's first finding._
3. **Build the link with the amount on it** — amount is computed here from the cart and the deposit split, which means a link is per-order rather than standing. That is a different flow from Stripe's one-link-many-prices and the pay page already renders both correctly — what is untested is whether a per-order link can be generated without a person in the loop.
4. **Decide what the reader is for** — Contactless is listed as a rail and has never been used. If the answer is “the tap at a stand, for the amount due now” then the receipt has to carry the order reference — written on it by hand if the terminal will not — or the buyer lands on a page that cannot tell them what they bought.
5. **Compare the two rails on one real sale each** — The reason both exist. What to compare: whether the reference survives to the receipt, what the buyer sees at the moment they pay, what the refund path looks like, and what the fee actually was. _Blocked on: Blocked on a first real payment on each, which is blocked on the webhook above._

## Still open

- **Which rail wins?** — Unanswerable until one real sale has gone through each. Writing a preference down now would be the assumption this whole arrangement was built to avoid.
- **Does the terminal ever make sense for this product?** — Every level is bought by somebody looking at a screen, including at an event. A reader may turn out to be a thing the store carries because it was easy rather than because anybody used it.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
