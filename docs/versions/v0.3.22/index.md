# v0.3.22 — level one can be paid for

The first payment link exists. It is level one's, created on 17 September 2026,
and the checkout renders a real button against it carrying the order reference
and, where the buyer arrived with one, the discount code. Levels two, three and
four still carry an empty checkout_url and render the reason rather than a
button. The claim ledger moved with it, which the build refused to proceed
without.

Two things the first real link taught the store. A payment link has no quantity
parameter, so a button opens at one unit: two packs rendered Pay £20 against a
link that charges £10, and the button now names the unit with the line total
beside it. And whether a buyer may change the quantity at all is the provider's
setting, which this site cannot ask about, so it is a field in the offer data
and false unless somebody has confirmed otherwise.

- Released: 2026-09-17
- Built from commit: `a01342cf4f963844636082dfcc92277f543b4587`
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
