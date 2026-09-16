# v0.3.12 — the comparison table, on paper

Memo 5 asked for the table and for the brochure. The table shipped in v0.2.8; this is the brochure, and it is the last unit of that memo that was mine to do.

tools/make_pdfs.mjs renders the real page through the real print stylesheet, so nothing is retyped — a row added to data/comparison.yml is in the PDF on the next run. A4 landscape, because five columns and a wide row label do not fit portrait without shrinking the body copy past reading at arm's length. Six sheets: four of table, two of the explanation under it. The header repeats on every sheet so the prices are never a page away from the ticks, and no row splits across a break, because a row that loses its label loses the only thing the table exists to show.

The disclosure strip prints. It is required above main on every surface this site produces and paper is a surface.

Where a download lands now depends on whether anything vouches for it. The two walkthrough PDFs stay behind /admin/ because they print discount codes and the code check exempts that path alone; the brochure is a selling document with no codes in it and sending a buyer to /admin/ to fetch one would be absurd. The rule is the safe way round: a file recorded in data/downloads.json was produced by the tool from a named page and is buyer-facing, and anything else in that folder is unvouched-for and stays behind /admin/. Dropping a file in by hand does not quietly publish it.

check_the_brochure_has_not_drifted holds four things and notes a fifth: the file still hashes to what the tool recorded, its version is one this site really released, it is published where the page says, nothing unvouched-for reaches a selling path — and a brochure that lags the current release is a NOTE rather than a failure, because forcing a browser render on every release would put Playwright in the gate, which this repository refuses. The page prints the version beside the link, so a stale copy is stale on its face. Four deliberate breaks, all fired.

One unit of that memo is still open and it is not mine: what support means, and who answers the mailbox.

- Released: 2026-09-16
- Built from commit: ``
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
