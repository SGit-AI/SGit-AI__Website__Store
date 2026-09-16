# The comparison table

Features down the left, five columns across — free, £10, £50, £500, £1,500. The page that makes the differences between the levels legible, and the one that finally explains the entry price, because a licence is only a difference next to a column that does not have it.

**5 of 6 done.** Status: `next`.

From the memo *One table, five columns, and the free one first* (2026-09-16) — https://store.sgit.ai/admin/memos/2026-09-16-the-comparison-table/

- **CT-1 · Decide what every cell is allowed to say** — `done` — Answered by building it the other way round. A row goes on the table only when each of its five cells can be pointed at — a price in data/offers.yml, a gets sentence, a not-promised line, or a ruling. A row whose cells would be a promise is not on the table at all. Fourteen rows qualified.
- **CT-2 · Write the feature list as data** — `done` — Shipped in v0.2.8 as data/comparison.yml. Fourteen rows in four groups, each carrying the sentence that says what the reader is actually buying.
- **CT-3 · Settle whether £10 includes a vault** — `done` — Settled by reading what the level already says. £10 is explicitly not a vault — its own page has said so since it was written — and £50 is where a vault starts. It was never a proposal; it was already true.
- **CT-4 · Decide what support means, and who answers** — `next` — Deliberately kept off the comparison table until it is decided. Email support on the paid levels was floated in the memo and never scoped. What is true today and could be said instead: every purchase is managed directly by the person who does the work. That is stronger than a support tier and it is also a different promise, so it needs saying on purpose rather than by default.
- **CT-5 · Build the page, free column first** — `done` — Shipped in v0.2.8 at /compare/, free column first.
- **CT-6 · Render it as a PDF** — `done` — Done. tools/make_pdfs.mjs renders the real page through the real print stylesheet, so nothing is retyped — a row added to data/comparison.yml is in the brochure on the next run. A4 landscape, because five columns and a wide row label do not fit portrait without shrinking the body copy past reading at arm's length. Six sheets: four of table, two of the explanation under it.It is not in the gate, for the same reason as the walkthrough and the concept screenshots — it needs a browser, and the gate is Python and node --check with nothing installed. So the drift is checked instead: the file still has to hash to what the tool recorded, its version has to be one this site really released, and a copy that lags the current release is a note rather than a failure, with the page printing the version beside the link. _Blocked on: CT-5._

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
