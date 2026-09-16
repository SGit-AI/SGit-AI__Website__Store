# Keep the record

The reviews, the ledger, the console and this board. The part of the store that exists so a decision taken today can be argued with in a month.

**5 of 8 done.** Status: `in-progress`.

- **TR-1 · Give the admin surface its own console UI** — `done` — Shipped in v0.1.18. Rail, counts read from the same files the pages are built from, and a shell that is not the shop's.
- **TR-2 · Build this board** — `done` — Shipped in v0.1.18 at /admin/work/, modelled on the workstreams board at sgraph.ai. Three boards: this one authored, and two generated from the reviews and the ledger so they cannot drift.
- **TR-3 · Link the admin console from the main site's top-level nav** — `done` — It was reachable only by knowing the address. Public and unadvertised was the intent; unfindable by the people building it was not.
- **TR-6 · Build the memo queue** — `done` — Shipped in v0.1.18 at /admin/memos/. A memo is kept verbatim, read into a brief, broken into units of work, and the units appear on the board carrying the memo they came from. Set as the process by the memo it is generated from, and applied backwards to the two before it.
- **TR-4 · Operationalise the review proposals** — `in-progress` — Eighteen proposals across two reviews, each with a stance. The ones marked do-now are units of work and were not tracked anywhere until this board existed. The generated proposals board is the join.
- **TR-5 · Capture the next review** — `queued` — The register takes a file and a line. The interesting one to run next is a second synthetic pass after the rail is live, because every finding in the first one stopped at a checkout that did not exist. _Blocked on: TM-7._
- **TR-7 · Execute the memos in sequence, pushing often** — `in-progress` — Set as the working method: catalogue each memo exactly, plan, then execute bit by bit and keep pushing to production. Minor versions for most of it; a major version where a change is big enough to deserve one.
- **TR-8 · Join the memos to what they became** — `done` — Shipped in v0.3.6 at /admin/status/. The queue said what arrived, the board said what it became and the release history said what shipped — and no page put the three together, so the only way to answer “what happened to that memo” was to read three pages and hold the join in your head. Every done unit now carries the pages it produced and the release it went out in, and a check refuses one that claims to be done and points at nothing.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
