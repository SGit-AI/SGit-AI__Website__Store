# Leak the codes on purpose

Seven discount codes exist and only the walkthrough page prints any of them. The ask is to publish codes on the main site on specific journeys — a code is a reason to complete a purchase, and a purchase is how a visitor becomes a customer record.

**4 of 4 done.** Status: `done`.

From the memo *Stripe end to end, with their SKUs — and a customer even at 100% off* (2026-09-16) — https://store.sgit.ai/admin/memos/2026-09-16-stripe-end-to-end/

- **LC-1 · Decide which journeys carry a code** — `done` — Answered by what the code can reach rather than by where it sits. The journeys are the two level pages the code applies to — /d/t1/ and /d/t2/ — because a code at the end of a level page discounts a decision somebody is in the middle of making, and a code on a first screen discounts one nobody has made yet. Not the home page.
- **LC-2 · Print the code on the journey, with the link carrying it applied** — `done` — Shipped in v0.3.1. The code is printed and the same code is a one-click link that applies it and lands on the shop with the two prices repainted.
- **LC-3 · Give every leaked code a cap and an expiry before it is printed** — `done` — Superseded by the ruling of 16 September: no caps, because purchases are managed directly and what this code gives away is already published free. What replaces a cap is stronger than one — the code cannot reach a level that is somebody's time, held by check_a_leaked_code_cannot_buy_somebody_s_day, which is absolute.
- **LC-4 · Keep the codes out of the built site except where they are meant to be** — `done` — check_discount_codes_are_not_printed fails the release if a code appears anywhere outside /admin/. Extending it to a named set of journeys is a change to that check, not a hole in it.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
