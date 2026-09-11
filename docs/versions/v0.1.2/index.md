# v0.1.2 — the six offers are grouped by which of three buyers each was built for, and the checkout is wired to payment links

The offer list gains a second index: three buyers — a team running agents, an investor backing a company, a startup about to meet diligence — with a page each at /for/<id>/, rendered from data/buyers.yml. It adds no offer and no price, and the gate holds it to that: a group may name offer ids only, every tier belongs to exactly one group, and the one group with nothing built for it says so above its offers rather than below them. The checkout is wired at the same time — a checkout_url per offer, a live button where a link exists and a sentence where one does not, every URL pinned to the payment provider's own hosts, and the mode of each checkout frozen against the price it follows from. No payment link has been issued for any offer, which is what the site now says. Plus tools/refs.py and data/refs.yml: the sgit.ai guidance and briefs this site is built against, fetched as their markdown twins, hashed, dated, and re-checkable when one moves.

- Released: 2026-09-11
- Built from commit: ``
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
