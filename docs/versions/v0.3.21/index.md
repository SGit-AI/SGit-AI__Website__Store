# v0.3.21 — the checkout hands over to the provider

The store's side of the payment rail, built. The checkout renders one button
per line of the order — a payment link sells one fixed set of lines, so a cart
of several cannot be one link — and each carries client_reference_id, which is
how the lines of one order find each other on the provider's side. A discount
code travels as prefilled_promo_code, but only while the plaintext is still in
hand from the address: the store keeps the record id and never the code, so a
checkout opened without it says the code must be re-applied rather than
charging a price nobody was shown. The page after paying reads the provider's
session id and says you came back, never that you paid — there is no server
here to ask.

Seventeen sentences saying nothing can be bought here now have a second half
that is true after a link is pasted, held by a check in both directions, and
the build refuses to run while the claim ledger still says no link exists.

- Released: 2026-09-17
- Built from commit: `39585a99b452d789112368f615a75843a62a00ce`
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
