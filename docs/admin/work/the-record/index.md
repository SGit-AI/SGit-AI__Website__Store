# Keep the record

The reviews, the ledger, the console and this board. The part of the store that exists so a decision taken today can be argued with in a month.

**4 of 6 done.** Status: `in-progress`.

- **TR-1 · Give the admin surface its own console UI** — `done` — Shipped in v0.1.18. Rail, counts read from the same files the pages are built from, and a shell that is not the shop's.
- **TR-2 · Build this board** — `done` — Shipped in v0.1.18 at /admin/work/, modelled on the workstreams board at sgraph.ai. Three boards: this one authored, and two generated from the reviews and the ledger so they cannot drift.
- **TR-3 · Link the admin console from the main site's top-level nav** — `done` — It was reachable only by knowing the address. Public and unadvertised was the intent; unfindable by the people building it was not.
- **TR-6 · Build the memo queue** — `done` — Shipped in v0.1.18 at /admin/memos/. A memo is kept verbatim, read into a brief, broken into units of work, and the units appear on the board carrying the memo they came from. Set as the process by the memo it is generated from, and applied backwards to the two before it.
- **TR-4 · Operationalise the review proposals** — `in-progress` — Eighteen proposals across two reviews, each with a stance. The ones marked do-now are units of work and were not tracked anywhere until this board existed. The generated proposals board is the join.
- **TR-5 · Capture the next review** — `queued` — The register takes a file and a line. The interesting one to run next is a second synthetic pass after the rail is live, because every finding in the first one stopped at a checkout that did not exist. _Blocked on: TM-7._

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
