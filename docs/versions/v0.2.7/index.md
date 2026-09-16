# v0.2.7 — five audiences, five doors, and nothing hidden from anybody

Asked for on 16 September, and the design brief for it is physical rather than visual: a laptop turned round at a stand, somebody says what they are, one tap, and the view opens on the level that fits. So /are/ is five large targets — founder, investor, C-level executive, security professional, risk and governance — five across on a laptop, two on a tablet, one on a phone, and they are on the home page above the four things for sale.

Each view leads with one level, says what changes for that reader, then shows the rest of the ladder, then points at the one published vault that speaks to them: an investor gets the eleven-step risk-acceptance walk, an executive gets the standard turned into conformance rows, a security professional gets the risk graph explorer.

SHOWN DIFFERENTLY, NOT HIDDEN, AND THAT WAS THE DECISION. The ask was that not every product is shown to every audience — an investor is not sold a ten-pound licence. The tempting implementation is to drop the cheap levels out of their view. That would make this site show different catalogues to different readers, which is a thing that has to be said out loud before it is built and nobody has said it. So: lead with what fits, quiet the rest at 72% opacity, hide nothing. check_the_five_audiences_hide_nothing holds every level reachable from every view and refuses display:none anywhere on one, because quiet becoming absent is one CSS rule away and would look like a tidy-up in a diff. Both breaks were run.

THIS DOES NOT REPLACE THE THREE BUYER GROUPS AND THAT IS OPEN, NOT DECIDED. The existing three are cut by situation; these five are cut by role. Both are indexes over the same six offers, neither invents a seventh thing to sell, and whether the three retire is on the board rather than settled in a commit.

- Released: 2026-09-16
- Built from commit: ``
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
