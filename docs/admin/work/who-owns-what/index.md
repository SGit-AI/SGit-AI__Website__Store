# Who owns what

Two sites, one purchase. The store owns e-commerce — cart, workflow, redirections, payments. riskmandate.ai owns the products, the policies, the information and the screenshots. Written down where both sides' agents can read it, because a boundary nobody published is a boundary that moves.

**3 of 4 done.** Status: `next`.

From the memo *Never leave the site — and write down who owns what* (2026-09-16) — https://store.sgit.ai/admin/memos/2026-09-16-one-site-one-flow/

- **WO-1 · Publish the ownership boundary as a page both agents can read** — `done` — Shipped in v0.3.2 at /boundary/ — indexed, with a markdown twin, in llms.txt, so another team's agent can find it. The store owns e-commerce; riskmandate.ai owns the products and the material; the reader never crosses the seam.
- **WO-2 · Brief the RiskMandate team to do the reverse** — `done` — Shipped in v0.3.2 as the second half of /boundary/: four asks in the order that makes each one useful on its own, and an explicit list of what is NOT being asked for — no callback, no session, no shared state, no account. Status open, and it will be recorded there when it is answered including if the answer is no, because a brief that only appears when it succeeds is a brief nobody should trust.
- **WO-3 · Mark the files that are on the wrong side** — `done` — Done in v0.3.2. The one file on the wrong side is named on /boundary/ with what makes it survivable: data/abp-catalogue.json is promoted at build time with the source URL, the retrieval time and a sha256, so it cannot drift silently. It is still the wrong arrangement and the page says so.
- **WO-4 · Agree the contract for the shared files** — `next` — Both directions need a stable address, a stable shape and a version field — three different promises, all three needed. CORS makes the read possible; it does not make it safe to depend on. Asked for as item four of the brief on /boundary/. _Blocked on: The RiskMandate team's answer._

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
