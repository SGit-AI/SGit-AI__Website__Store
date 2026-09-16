# Describe your agent

A free page where somebody builds their agent by clicking or dragging capabilities onto it, and what comes out is a definition of what that agent could do — a document a model session can turn into a vault. It is the elicitation half of the £500 level, given away, and the project lead expects it to be the page they use most in conversation.

**5 of 8 done.** Status: `next`.

From the memo *Describe your agent — the page that gets used in the room* (2026-09-16) — https://store.sgit.ai/admin/memos/2026-09-16-describe-your-agent/

- **DA-1 · Get the real capability vocabulary** — `done` — Got, rather than invented. Twenty-three primitives on a verb.object.reach grammar, read out of riskmandate.ai's own template vault with its published read key and promoted by tools/promote_capabilities.py with the hash of the bytes. The ultimate source is what-can-it-do.games.sgit.ai — one of the games the memo was pointing at.
- **DA-2 · Prototype the canvas — agent in the centre, capabilities around it** — `done` — Shipped in v0.3.5 at /lab/agent-canvas/. All nine families on one screen, click to give a capability to the agent, click again to take it away.
- **DA-3 · Prototype the sequence — one question at a time** — `done` — Shipped in v0.3.5 at /lab/agent-sequence/. Same twenty-three primitives, one family per screen, with what each reach means.
- **DA-4 · Decide whether a capability has degrees** — `next` — Partly answered by the vocabulary itself, and the rest is still open. Degrees are not on the capability — send.endpoint.allowed and send.endpoint.world are two separate primitives, which is how “partially connect to the internet” is already expressed. What is not decided is whether the interface should also carry the barrier taxonomy, where only one of four kinds of restraint is actually a control.
- **DA-5 · Emit the definition as a document a model can act on** — `done` — Shipped in v0.3.5. Markdown to the clipboard or JSON to your downloads, carrying the grammar and the reach glossary with it so the session reading it does not have to guess what world means. Nothing is sent anywhere and a check refuses a fetch in that file.
- **DA-6 · Write the prompt that turns the definition into a vault** — `queued` — A model session with the template vault takes the document and produces the buyer's vault. The store already ships a level-three prompt; this is its front half. _Blocked on: DA-8, and a decision on which of the two interfaces is real._
- **DA-7 · Say on the page what it is and is not** — `done` — Shipped in v0.3.5, and held by a check: every prototype has to say it produces the grant only. A reader who thought this was the whole document would be taking three quarters of the £500 level for nothing in their own head.
- **DA-8 · Put it in front of the £500 level and in the walk-through flow** — `queued` — Free, in front of the paywall, and the thing a conversation at a stand is run from: build it together, they leave, the vault follows. _Blocked on: DA-5._

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
