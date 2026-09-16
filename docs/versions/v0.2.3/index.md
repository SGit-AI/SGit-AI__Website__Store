# v0.2.3 — three coupons exist, zero promotion codes do, and that is the whole gap

The coupons were created on 16 September at 25, 50 and 100 per cent, all once, and they reconcile exactly against the percentages this store honours. The reconciliation now covers them alongside the products: every percentage in data/discounts.yml has a coupon, no coupon exists at a percentage nothing here explains, and two deliberate breaks were run against each direction.

THE GAP IS PROMOTION CODES, AND THE DISTINCTION IS WORTH STATING. A coupon carries a percentage. A promotion code is the string a person is actually handed, it is a separate object attached to a coupon, and it is what a link can carry pre-applied. Until one exists there is nothing to give anybody, so /admin/rails/stripe/ says that in those words rather than showing three green ticks.

Three coupons onto seven codes is the right shape and not a shortfall. Five of this store's seven codes are at a hundred per cent and exist as five so that an order record says which one produced it — a beta tester, an agent driving a script, somebody at a stand. That distinction lives in the promotion code; the coupon only ever needs to carry the percentage.

THE HUNDRED-PER-CENT COUPON HAS NO CAP AND NO EXPIRY. Harmless today, because no promotion code exists over it and no link exists to use one on, so there is nothing to redeem. It stops being harmless the moment either changes, and a code at a hundred per cent cannot be recalled once it is on a card. check_a_hundred_per_cent_coupon_is_capped notes it on every release now and FAILS the release that turns a rail on with the cap still missing — which is the release where somebody will be thinking about twelve other things. It is the same rule check_printable_codes_need_a_dead_rail already makes, moved to the provider's side.

The coupon ids are in the repository because the reconciliation has to point at a row, and are on no page. A coupon id is not what a buyer applies — a promotion code is — so publishing it would most likely be harmless, and not publishing it costs nothing, and this store does not spend a maybe on a convenience.

TWO DISPLAY BUGS FOUND BY LOOKING AT THE PAGE. The state chips are uppercased by their own CSS, which turned 5000p into 5000P — a unit nobody uses, on the one number a reader is most likely to be checking against a dashboard; they read as money now. And the coupon chips rendered green while saying UNCAPPED, which is a chip arguing with itself; rank now follows what the state costs, red where an uncapped hundred-per-cent code cannot be recalled and amber where a cap is merely missing.

- Released: 2026-09-16
- Built from commit: ``
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
