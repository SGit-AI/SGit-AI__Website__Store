# Leak the codes on purpose

Seven discount codes exist and only the walkthrough page prints any of them. The ask is to publish codes on the main site on specific journeys — a code is a reason to complete a purchase, and a purchase is how a visitor becomes a customer record.

**1 of 4 done.** Status: `next`.

From the memo *Stripe end to end, with their SKUs — and a customer even at 100% off* (2026-09-16) — https://store.sgit.ai/admin/memos/2026-09-16-stripe-end-to-end/

- **LC-1 · Decide which journeys carry a code** — `next` — Not the home page. A code on a first screen discounts a decision nobody has made yet; a code at the end of a level page discounts one somebody is in the middle of making.
- **LC-2 · Print the code on the journey, with the link carrying it applied** — `queued` — Re-typing a code you just read is a step that loses people. The published code and the prefilled link are the same fact rendered twice. _Blocked on: LC-1, TM-4._
- **LC-3 · Give every leaked code a cap and an expiry before it is printed** — `queued` — A printed code cannot be recalled. The cap is what makes printing it survivable. _Blocked on: TM-3._
- **LC-4 · Keep the codes out of the built site except where they are meant to be** — `done` — check_discount_codes_are_not_printed fails the release if a code appears anywhere outside /admin/. Extending it to a named set of journeys is a change to that check, not a hole in it.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
