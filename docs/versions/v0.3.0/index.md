# v0.3.0 — the buyer lands on this site

Until today the success address was riskmandate.ai's page for the level, and the reasoning for that was good: their level-one page IS the download, with the zip, its size, its sha256 and a hash check that runs in the buyer's own browser — and copying a size and a hash over here would mean two of each, one of which goes stale the first time a template changes.

What that reasoning missed is what it cost. A synthetic buyer said it plainly: they did a whole shopping experience on one site and were dropped onto another, with a different interface and a different voice, at the exact moment they had just paid. It was logged as a confusion and treated as a copy problem. It was an architecture problem.

So /paid/t1/ to /paid/t4/ are on this site, in this site's chrome. Each one carries the order reference — filled from the browser that placed it, never invented, and saying plainly when it does not have yours — what was bought, when it arrives, who does it at the two upper levels, what done looks like and how you check it. They are noindex, because a page that says you bought has no business in a search result, and every one of them is correct with no script at all: a browser that blocked it still reads the part that matters.

THE ONE REMAINING HOP IS NAMED RATHER THAN HIDDEN. At level one the artefact genuinely lives on the other domain, and the page says so in one sentence with the reason. Closing it means the store reading their manifest over CORS — which is possible rather than hoped for: their pages answer access-control-allow-origin star, verified today — and that means opening a connection on a selling page, which is this site's hardest rule. So it is its own piece of work with the rule narrowing in front of it, rather than something smuggled in here.

WHAT STAYS ABSOLUTE IN THE CONTRACT. The two parameters are unchanged — order everywhere, shape at level one — because they are still the right two and a printed link cannot be recalled. What is new in the check is that the destination must be on this site AND must be a page this build actually emits: a success address pointing at a 404 is the one dead link nobody clicks until a stranger has paid. And the old destination is not deleted — every level keeps post_upstream, so the page holding the artefact stays one named link away rather than disappearing into git history.

- Released: 2026-09-16
- Built from commit: ``
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
