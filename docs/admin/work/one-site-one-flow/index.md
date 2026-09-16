# Never leave the site

A buyer does the whole thing here — catalogue, cart, payment, receipt, and the vault they just bought, embedded on the page they land on. Today the store hands them to another domain at the moment they pay, which a synthetic buyer called out as the point they got confused.

**0 of 6 done.** Status: `next`.

From the memo *Never leave the site — and write down who owns what* (2026-09-16) — https://store.sgit.ai/admin/memos/2026-09-16-one-site-one-flow/

- **OS-1 · Narrow the no-network rule before the first cross-origin read** — `next` — Every selling page opens no connection and check_no_network fails the release if one does. Reading riskmandate.ai's catalogue over CORS breaks that as written. The rule gets narrowed, never loosened — the absolute half stays absolute, the exception is named in the check, and a deliberate break is run against the new check before anything ships. That is how the vault embed was admitted and it is the only way this one gets in.
- **OS-2 · Move the post-sale page onto this site** — `next` — The success address goes from riskmandate.ai's page for the level to one here. This is what unblocks the Stripe return-address task, which was blocked on another team until this memo arrived. _Blocked on: OS-1 for anything it needs to read._
- **OS-3 · Embed the bought vault on the page they land on** — `next` — “You should see the vault.” The mechanism is already in this repository and already passing the gate: a frame built at runtime, opened carrying nothing, handed a published read key by message with the origin pinned. What is new is which page it runs on. _Blocked on: OS-2._
- **OS-4 · Read the product data from the side that owns it** — `queued` — The shapes belong to riskmandate.ai. The store reads them over CORS and renders them in the store's own CSS — somebody else's data, never somebody else's interface. _Blocked on: OS-1, and the other side publishing a stable file._
- **OS-5 · Make the store feel like a shop** — `queued` — “Fundamentally like Amazon.” More detail is coming from the project lead. Several pages here are an essay with a buy button under them, which is the gap. _Blocked on: More information from the project lead._
- **OS-6 · Re-run the synthetic buyer who got confused** — `queued` — The finding has a name and a persona attached. The same walk, after the flow is one site, is the only way to know this worked. _Blocked on: OS-2, OS-3._

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
