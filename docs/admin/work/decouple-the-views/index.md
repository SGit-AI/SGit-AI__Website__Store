# Decouple the views

Five audiences across the surfaces they touch is not writeable by hand. The store is already data-driven at the content layer and hand-written at the view layer, and that seam is what the memo is pointing at: JSON configuration, components, and the same generate-and-check discipline coding.sgit.ai and nfrs.sgit.ai both teach.

**0 of 5 done.** Status: `in-progress`.

From the memo *Five audiences, decoupled views, and the version the board can read* (2026-09-16) — https://store.sgit.ai/admin/memos/2026-09-16-five-audiences/

- **DV-1 · Read the two guidance sites properly and write down what applies** — `in-progress` — coding.sgit.ai measures its conventions by counting the code rather than asserting them; nfrs.sgit.ai runs one rule — link the measurement, never restate it, generate or date every number — and fails its build otherwise. This store already runs both of those; what is not yet written down is which of their component conventions apply to a site that ships no framework.
- **DV-2 · Settle: custom elements at runtime, or generated partials at build?** — `next` — This is the decision the rest depends on and it has a hard constraint on it. Every selling page on this site opens no connection and a build check fails the release if one does. Components that fetch their own configuration would negotiate with that rule. Components that are rendered at build from the same JSON would not, and would still give the memo what it asked for.
- **DV-3 · Lift the view layer out of build.py into declared blocks** — `queued` — Three thousand lines, of which the page shells and the block renderers are the part five audiences would multiply. Extract those first; leave the markdown renderer and the gate alone. _Blocked on: DV-2._
- **DV-4 · One JSON file per view, and a check that fails on an unused one** — `queued` — The store's own idiom, applied to views: a register with no file and a file with no register entry both fail the build, the way the reviews already do. _Blocked on: DV-3._
- **DV-5 · Prove it by adding the sixth audience as a file** — `queued` — The acceptance test for the whole workstream. If adding an audience is still a code change, the refactor did not land. _Blocked on: DV-4, QB-4._

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
