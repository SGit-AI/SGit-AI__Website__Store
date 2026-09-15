# v0.1.9 — the handover to the page after payment, and a discount code that arrives in the address

The loop closes. riskmandate.ai published the contract for what happens after the money moves — one page per level, and since its v1.19.2 the £5 page IS the download, with the zip's size and sha256 stamped by their build and a hash check that runs in the buyer's own browser. This release hands the buyer over to it: every line of an order carries a link to the page for its level, with the store's order reference and, at level one, the shape's slug — the two plain-text parameters that contract allows, and nothing else. Nothing is copied here, because two copies of a hash is one hash that will go stale.

Three things that were wrong are right. The follow-up said “within one working day”, a day slower than the twenty-four hours their pages commit to in public, and a check now refuses the phrase. Level one said the pack arrives by email; it is a download on the page you land on, so the level is renamed and its SKU letter moves from E to P. Level three said “send back what it printed” and named no route; it now names MAP-A-GRANT.md, grant.json, mandate.json and the session record, with no secret in them and the order reference on the message.

Discount codes, at 25, 50 and 100 per cent. A code arrives in the address rather than in a field, because this site has no text input and the gate refuses one — which is how a printed card or a QR hands one over anyway. What ships is sha256 of the code and never the code, and a check reads every byte of the built site against every code to keep it that way. It comes off the price of every line and the deposit is taken on what is left; a code at a hundred per cent still places an order and still lands on the page that says what happens next, which is how the whole flow gets walked before a rail exists.

What the handover still owes is on the ledger rather than in somebody's head: nothing carries a sale from this store to the person who follows up, no receipt has ever been issued, the level-three files come back by email until a write-only vault exists, the follow-up mailbox has no named owner, and the opinion add-on is listed here with no page there. The first of those gates the first paid order at £50, £500 and £1,500.

One bug found by driving it: shop.js was loaded twice on the cart, paying and order pages — the cart engine running twice against one document, the second copy undoing what the first did. A check now holds every page to one copy of each script.

- Released: 2026-09-15
- Built from commit: `00a03b81cfd5e1d990587ce34f9d5b3ae0c7e4b2`
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
