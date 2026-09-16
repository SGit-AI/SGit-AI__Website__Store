# v0.2.6 — SumUp comes off the store for the first end-to-end MVP, and the plan for it is parked rather than deleted

Stripe works: six products priced, three coupons, and a reconciliation running on every release. A second rail that is half set up is a second thing to explain on a selling page and a second thing to keep true, and the first end-to-end store needs neither. So SumUp is off data/checkout.yml, off /paying/, off /how-it-works/ and out of the cart.

Nothing is deleted. /admin/rails/sumup/ keeps the whole plan behind a banner that says it is parked and why, because the argument for running two rails is a good one and it will be worth reading again the day the first rail has taken money — which is exactly when it stops being hypothetical. That is queued rather than forgotten.

The finding that came out of writing the SumUp plan up — that check_checkout_links pinned every destination to Stripe's hosts and would have refused a SumUp URL with a message about Stripe — is now moot rather than fixed, and stays written down because it will be true again the day the rail comes back.

One walkthrough caption corrected rather than restaged. The screenshot at step four is from v0.1.11 and shows four rails including SumUp. The caption now says so and the picture is left as it was taken, because a walkthrough whose images are quietly re-shot is a walkthrough nobody can date.

And one comment in data/checkout.yml that had gone stale is now true: it still said no product catalogue goes inside the providers, sixty-two SKUs maintained twice is sixty-two SKUs that will disagree. That reversed on 16 September and the file now says so — the objection was sized wrong, because a price here does not vary by shape, so Stripe needs six products rather than sixty-two, and what the catalogue buys is a buyer who becomes a customer with an email rather than an anonymous card charge.

- Released: 2026-09-16
- Built from commit: ``
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
