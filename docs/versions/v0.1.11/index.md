# v0.1.11 — the walkthrough codes stay out of the indexed bulk file too

/admin/ is noindex and out of sitemap.xml because the walkthrough prints working discount codes, and the page says so in those words. llms-full.txt — the whole site as one document, linked from the footer and indexed — carried the same codes, which made that sentence false. It now omits /admin/ and says at the end that it does, llms.txt still lists both pages with their addresses, and the check that keeps codes off every other page no longer exempts the bulk file. Public and advertised are different things, and a claim about which one a page is should be true of every file that renders it.

- Released: 2026-09-15
- Built from commit: ``
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
