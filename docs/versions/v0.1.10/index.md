# v0.1.10 — a walkthrough anybody can run, with the codes printed on it

A page anybody can be pointed at to walk the whole store end to end, at /admin/try/, with seven screenshots of the flow as it actually runs and two sets of instructions — one for a person, one for an agent driving a browser or reading files.

THREE DISCOUNT CODES ARE PRINTED ON IT, at a hundred per cent, and that is the point: a walkthrough somebody has to be sent a code for is not a walkthrough. Every other code on this site is still barred from the built output by a check that reads every byte of it, so a new field says which codes may be printed and the frozen table rules on it alongside the percentage. What makes printing them safe is not a promise but a build check: check_printable_codes_need_a_dead_rail fails the release if a printed hundred-per-cent code and a live payment rail are ever in the same build, and a printed code at less than a hundred per cent is refused outright.

The forty-six assertions the page tells a synthetic user to make are also a script — tools/walkthrough.mjs — and the script is what was run before the page was written. It is deliberately not in the gate: the release path is Python and node --check with nothing installed, and a browser there would make every release depend on a download. Two of the forty-six failed on the first run and both were the page's fault rather than the site's: an innerText comparison against text the CSS upper-cases, and a key-shaped pattern that matched the page printing it. Both are now written so they pass, and the first is written down as the gotcha it is.

TWO BUGS, ONE OF THEM VISIBLE ON EVERY POST-SALE PAGE. `.doc code` is more specific than `pre code`, so the inline-code chip — a white box with a border — was winning inside a code block: every line of the level-three prompt had a white box behind it. It only shows where a pre contains a code element, which on this site is the prompt the cart writes in by script, on no server-rendered page — so nothing anybody read caught it. Screenshotting the flow did. The other: the link checker called an internal link with a query string dead, which made /policies/?code=… unlinkable; a query is read by the page, not by the file system.

/admin/ is a new page and gathers the internal surfaces — the walkthrough, the ledger, the dev packs, the release history, the lab. It is public, because every page here is and a static site could not pretend otherwise, and it is noindex and out of sitemap.xml, because public and advertised are different things: somebody handed the address can read it, and nobody arrives by searching for a discount code.

- Released: 2026-09-15
- Built from commit: `456b3bddb55e3f25b0aa83a59197a99e24b38a0b`
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
