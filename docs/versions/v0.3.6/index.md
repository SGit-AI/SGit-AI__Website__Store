# v0.3.6 — what happened to each memo, on one page

The queue said what arrived. The board said what it became. The release history said what shipped. No page put the three together, so the honest way to answer what happened to that memo I sent you was to read three pages and hold the join in your head.

/admin/status/ is that join, and it is generated: every memo, the units of work it became, whether each is done, the page it built and the release it went out in. Every done unit now carries a structured record of where it landed rather than a sentence mentioning it in passing — forty-seven of them, backfilled.

DONE IS THE ONLY STATUS THAT CAN BE WRONG WITHOUT ANYBODY NOTICING. Every other state on the board is a statement about the future and unfalsifiable by design; done is a claim about the past and it is the claim a reader of this page is actually relying on. So check_every_done_unit_points_at_something holds a done unit to naming a release this site has actually made and at least one page this build actually emits, and it checks the anchors too. A done unit pointing at a 404 is a status page that is worse than no status page, because it looks like evidence. Four deliberate breaks were run against it.

TWO THINGS THE PAGE GOT WRONG ABOUT ITSELF BEFORE IT SHIPPED. It printed 55 done against a board that had 47, because two memos can name the same workstream and a per-memo tally added to a running total counts those units twice. And it left out a workstream entirely — close the loop after payment came out of the partner review rather than a memo, so a page organised by memo had nowhere to put it while its units still counted on the board. Both are fixed, and a check now holds every unit on the board to appearing on the status page, because a status page that is silently incomplete is worse than one that says where its own edges are.

And one thing that would have stopped the gate dead: an elif attached to a block that no longer ended where it used to, which is a syntax error rather than a wrong answer. The gate refused to run at all until it was fixed, which is the right failure.

- Released: 2026-09-16
- Built from commit: `a2fa742f7a008985b14a24a7d0d989387fbe30c2`
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
