# v0.3.16 — the new design is the store, and the one it replaced is kept at /v1/

The design built across four rounds at /next/ is now what store.sgit.ai serves.
Nine pages existed in both designs, so the new one takes the address and the old
one is archived one directory down: the front page, the picker, the comparison,
the audiences, the ledger, the order, the checkout, the page after paying and the
reviewer register. Every /v1/ page carries a strip saying it is not the live one,
is noindex, and has its links to the other moved pages rewritten so the archive
does not tip a reader into the store halfway through.

Every other public page kept its address and is re-drawn in the new chrome. They
load site.css and then next.css: the chrome and the base type come from the new
file, the block components keep the rules that already draw them. Fourteen rules
in the old stylesheet were scoped to the old chrome's own element and are
replaced by the reading column in the new one; the other four hundred and
sixty-seven were untouched. That layering is transitional and is on the board.

**Every address the design round used still resolves.** Ten pages at /next/, each
saying where its page went, carrying the canonical link and refreshing there.

**The printed cards still work.** A code arrives in the address off a card or a
QR, and the cards in circulation point at the front page — which is the new
design, where the old engine is not. The capture, the expiry and the per-level
arithmetic are ported into next.js, sharing shop.js's storage key, record shape
and sha256, with a check holding the two copies of the hash identical. A code
landing on a page drawn by the old engine is handed to the order page rather than
dropped, and every page has somewhere to say a code was applied or refused.

The homepage regained the evidence band it had lost: six published vaults, linked,
with the claim that the work has been done. Two build checks caught that on the
day the round became the store, which is what they were written for.

New rule: the sitemap advertises nothing it hides. Nineteen noindex pages were
listed in it for the length of one build.

- Released: 2026-09-16
- Built from commit: ``
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
