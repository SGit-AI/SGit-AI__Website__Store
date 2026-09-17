# v0.3.23 — the page a buyer lands on after paying can find their order

The redirect on level one's payment link points at /paid/t1/, which wears the
previous design's chrome and runs shop.js. That engine looked for the order
reference under two keys only the old place-an-order step ever wrote — and the
store that sells today has no such step, because a buyer goes from the checkout
straight to the provider. So the page a buyer lands on after paying could not
find their reference, and told them instead that they must have ordered in a
different browser: false, and said to the one person least able to argue.

shop.js now falls back to the shared order record both engines read, and reads
the provider's session id out of the address the way the store's own engine
does. A check holds the two readers identical.

- Released: 2026-09-17
- Built from commit: `5cbeb893aa350175544abea899b0720eb1195d54`
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
