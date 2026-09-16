# v0.3.11 — the vault contract, learned the hard way

The synthetic-panel vault shipped yesterday rendered every one of its ten screenshots as a broken image, and the same files served over plain HTTP were perfect — which is exactly why a local check passed it and only opening the vault itself showed the fault.

A vault app runs inside an iframe loaded from a blob: URL, so the browser fetches anything declarative before the vault bridge can install. The app built its figures as innerHTML strings carrying an image tag with a src attribute, which the parser treats as markup: the fetch resolved against the frame's opaque origin and found nothing.

The vault is fixed and re-pushed. One helper now creates the element and assigns .src as a property, after the bridge is up, and the app posts sg-app-ready, which it never did. The read key is unchanged, so the review page needs nothing.

The vault written on 15 September got this right and carried a comment saying so. The knowledge was in that vault and not in this repository, so it is now a ninth constraint in the design brief and a note on the vault-embed component. Two of this store's four products are vaults and one prototype produces them, so it is not an edge case here.

- Released: 2026-09-16
- Built from commit: `d93cfcd0531223439df35c15a02b95ae383035d9`
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
