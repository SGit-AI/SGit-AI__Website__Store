# Never leave the site

A buyer does the whole thing here — catalogue, cart, payment, receipt, and the vault they just bought, embedded on the page they land on. Today the store hands them to another domain at the moment they pay, which a synthetic buyer called out as the point they got confused.

**3 of 6 done.** Status: `next`.

From the memo *Never leave the site — and write down who owns what* (2026-09-16) — https://store.sgit.ai/admin/memos/2026-09-16-one-site-one-flow/

- **OS-1 · Narrow the no-network rule before the first cross-origin read** — `done` — Done in v0.3.3, with a consumer rather than on spec. The no-network rule was narrowed a second time to admit the vault embed on the page a buyer lands on. The half that carries the claim did not move: every page that SELLS anything opens nothing at all, and there is now a check that refuses an embed on one by name. Five deliberate breaks run.
- **OS-2 · Move the post-sale page onto this site** — `done` — Shipped in v0.3.0. /paid/t1/ to /paid/t4/ are on this site: the order reference filled from the browser that placed it, what was bought, when it arrives, who does it, what done looks like and how to check it. Every page noindex, and correct with no script at all — a browser that blocked it still reads what happens next.
- **OS-3 · Embed the bought vault on the page they land on** — `done` — Shipped in v0.3.3. The three levels that are a vault embed a published one on the page after payment, labelled an example, not yours in its first sentence — because at the moment somebody pays there is nothing of theirs to show yet, and a page that pretended otherwise would be lying at the one moment a buyer is paying most attention.
- **OS-4 · Read riskmandate.ai's manifest over CORS and close the last hop** — `next` — Blocked on the brief, and now for a named reason. Their manifest exists — fifteen entries with bytes and a sha256 — and it lives inside a JavaScript const DIST = /*__DIST__*/[…] in paid-t1.html, not at a JSON address. Reading it means regex-ing their JS out of their HTML at runtime, which is exactly the fragility item one of the brief on /boundary/ asks them to remove. CORS is confirmed; the shape is the gap. _Blocked on: The RiskMandate team publishing a manifest as JSON — item 1 of the brief._
- **OS-5 · Make the store feel like a shop** — `queued` — “Fundamentally like Amazon.” More detail is coming from the project lead. Several pages here are an essay with a buy button under them, which is the gap. _Blocked on: More information from the project lead._
- **OS-6 · Re-run the synthetic buyer who got confused** — `queued` — The finding has a name and a persona attached. The same walk, after the flow is one site, is the only way to know this worked. _Blocked on: OS-2, OS-3._

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
