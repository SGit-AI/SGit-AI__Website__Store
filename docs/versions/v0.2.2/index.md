# v0.2.2 — the home page becomes a shop front, and the Stripe catalogue becomes a reconciliation

THE HOME PAGE SELLS. It opened by explaining what an Agent Behaviour Policy is; a shop opens with what is for sale. The four levels are now cards at the top — name, who it is for, the price, when it arrives, what is true of it today, and a button — four across on a laptop, two on a tablet, one on a phone, with 48px targets where there is no mouse. The brief for this was physical rather than visual: a laptop turned round at a stand, somebody says what they are, two taps to a checkout.

The essay did not get deleted. What is actually in one, why there is no score and never will be, and the argument about the free template against the paid instance moved whole to /what-is-in-one/ and into the nav.

A CODE IS A LINK NOW, NOT SOMETHING TO TYPE. Following one applies the discount, repaints all four prices with the list price struck through beside them, and takes the code out of the address before the page settles — so it is not in history, not in a bookmark and not in a referrer. The admin console has the three printable codes as ready-made links to hand out. The other four still ship as a SHA-256 and never as a string.

THE STRIPE PRODUCTS EXIST. Created by the project lead, and in a better shape than this plan had guessed: the two upper levels are a DEPOSIT and a DELIVERY that sum to the price, so a buyer paying in full adds both lines and a buyer starting adds one. That is the store's own a-fifth-now-and-the-rest-on-delivery as two rows rather than a rule somebody has to remember to apply. All six reconcile against data/offers.yml to the penny. The codes are ABP-T1, ABP-T3-DEPOSIT and so on rather than the SG- this plan proposed, and they live in the Stripe price description rather than in a lookup key, because the dashboard's product view surfaces no lookup key. That is not the same object as Price.lookup_key, which is the field a webhook would map a line item back to a level by — it works for a person reading the dashboard and it is not queryable, and the difference is written down rather than found later by a handler that cannot tell what was bought.

So catalogue.json stopped being a shopping list and became a reconciliation: the left is what this site implies, the right is what the dashboard holds. The site cannot ask Stripe anything — it opens no connection and that rule is not moving for this — so the other side is the dashboard's own CSV export, committed to the repository, with the amounts read off the product list the same day. That is weaker than an API call and it is said so on the page: it catches a price changed here and not there, which is the direction that actually happens, and it goes stale the other way until somebody re-exports.

ONE CHIP RELABELLED, BECAUSE IT WAS DOING TWO JOBS. specified, never run meant never sold through this store and read as never done at all. It now says never bought here.

AND ONE CHECK WAS PROVED DEAD AND REWRITTEN. The split-adds-up assertion compared the generated rows against each other — and they are derived from data/offers.yml, so they sum correctly by construction and a deliberate break walked straight through. It now reads the dashboard export directly, which is what a buyer actually pays. Six deliberate breaks were run across the reconciliation.

Also fixed: .buy was already the buy-button class, so every card on the new shop front inherited font-weight 700 from it. Same shape of bug as the embed width three releases ago. The cards are .sku now.

- Released: 2026-09-16
- Built from commit: ``
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
