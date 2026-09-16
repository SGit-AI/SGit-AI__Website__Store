# v0.2.5 — the never-done language comes off the site, because it was describing the sale and reading as the work

Ruled by the project lead: remove it, do not narrow it again. The previous release had softened these sentences rather than removing them, and the reasoning behind keeping them was wrong — every one of them described whether this STORE had taken an order, while sitting on a card about the PRODUCT, and what a reader took from it was that nobody had ever done the work. That is false. It has been done many times, six vaults of it are published, and the person who does it is the one selling it.

So the chip that said specified, never run and then never bought here now says delivered by a person, and its tooltip says what that means: a named security professional does this work and signs it off, which is why its delivery estimate depends on a calendar rather than a queue. That is a property worth a chip, because it is the real difference between the top two levels and the two below them.

Every claim that carried the old framing was rewritten rather than deleted. The ledger keeps its job — the £500 and £1,500 rows now say what is true of them, which is that they are somebody's work and that work is published and open to read.

ONE RULE HAD ITS PREMISE CORRECTED. A check refused a deposit on anything whose state was not unrun, on the reasoning that a deposit is how an unproven thing is sold honestly. That was never the main reason and it is not a reason now: a deposit is how scheduled professional work is sold, because what it reserves is somebody's calendar. What stays barred is the case the rule was really for — a thing produced the moment you pay, taking a deposit.

AND THE RENAME EXPOSED A SILENT FAILURE THAT HAD ALREADY SHIPPED. chip() fell back to unknown with an empty tooltip for a state it did not recognise, so two claims pointing at the retired name rendered as unknown in production, on the page whose entire job is saying how true each sentence is, and nothing failed. A fallback that produces a plausible-looking page is worse than one that stops: chip() now raises, and check_every_claim_state_is_real catches it one step earlier in the data. Two deliberate breaks were run against both.

Also found: st-p was already the class for projected, and the new person chip had taken it — a second meaning on one class is how a chip quietly starts lying about a different claim. It is st-n now.

- Released: 2026-09-16
- Built from commit: `c0fbe75497c00eed217d4fdab3b7a1432a39610c`
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
