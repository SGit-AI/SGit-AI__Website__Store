# v0.3.13 — the next store, in the design we chose

The v3 direction 01 / ABP first, built here as a parallel set of pages at /next/. The store that sells today keeps selling; the two swap over when the buying flow is wired end to end.

Pack, Vault, Tailored, Reviewed. The project lead ruled the names out of this design round, which is the decision TK-7 had been waiting on: a short name at heading size with the precise line underneath, rather than a choice between the two. They live in data/offers.yml beside the price and are frozen by the same check.

Every price, name, delivery estimate, claim and audience on these pages is read out of the files the current store is already built from. There is no second copy of a number to drift. check_next_is_the_offer_data holds both pages to that file per page rather than over the set — its first version joined the two and asserted against the join, so a price edited on the homepage alone passed because the product page still carried the right one.

Nothing on /next/ can be bought and both pages say so. No level has a checkout link, so the product page renders a disabled control carrying its reason and the homepage says it in words. The check caught that the homepage had four priced cards and never mentioned the till was off, which is the shop-window-on-a-closed-shop problem the concept critique made its headline finding.

assets/next.css and assets/next.js are a real layer rather than an override. The v3 source loads this site's own stylesheet and overrides :root in a second file — right for a mockup, wrong to ship: it carries 26KB of a design we are leaving and makes every new rule fight an old one. These pages load those two files and nothing else. The cost is stated: a few components exist twice for now, in two visual languages, until /next/ takes over.

One deliberate change from the source. It declares Arial, Helvetica outright, which renders as drawn on two platforms and as a substitute everywhere else. /next/ uses a stack resolving to the same faces on macOS and Windows that degrades to a real grotesque elsewhere.

Four product renders arrived as 7.9MB of PNG and ship as 126KB of JPEG, re-encoded by tools/shoot_v3.mjs through Chromium because there is no image library on this machine. The source hash of each is recorded so the re-encode traces back to what arrived.

On a phone the headline lands at 334px against the live store's 358, the first real action at 690 against 784, and the page is 7,646px against 10,710. The first draft was worse than the live store on the first of those: three strips of chrome each wrapping to three lines. Each keeps its job and loses its second line.

One section of the design is not built and it is named. The v3 pages carry a mission line using a word this site bars absolutely on every page carrying a price, and their own notes record that the project lead asked for it. TK-11 is the ruling.

- Released: 2026-09-16
- Built from commit: `94fe9dc7fbe888e18087cad453164165eebfb8a7`
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
