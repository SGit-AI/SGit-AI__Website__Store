---
title: Who owns what, between this store and riskmandate.ai
description: "The boundary between store.sgit.ai and riskmandate.ai, written down where both sides' agents can read it: the store owns e-commerce, riskmandate.ai owns the products and the policies, and neither sends the other's visitors away. Includes the brief asking their team to do the reverse."
lead: "**Two sites, one purchase.** This store owns the cart, the workflow, the redirections and the payments. riskmandate.ai owns the products, the policies, the information and the screenshots. Written down here rather than agreed in passing, because **a boundary nobody published is a boundary that moves**."
order: 20
toc: true
---

## The rule

**The store owns e-commerce. riskmandate.ai owns the material.**

Everything that is a cart, a workflow, a redirection or a payment happens on
`store.sgit.ai`. Everything that is a product, a list, an Agent Behaviour Policy,
an explanation or a screenshot belongs to `riskmandate.ai`. Every other question
about where something lives follows from that sentence, including which side a
file that is currently on the wrong one has to move to.

| | store.sgit.ai | riskmandate.ai |
|---|---|---|
| **Owns** | The cart, the order reference, the discount codes, the payment rails, the page a buyer lands on after paying | The fifteen template shapes, the policies themselves, the vaults, the deeper explanation, the screenshots |
| **Reads from the other** | The shape catalogue, promoted at build time today; their download manifest, which is [not built yet](/admin/work/one-site-one-flow/) | Nothing yet. That is what the brief below asks for |
| **Never does** | Explain what a policy is at length. That is their page and it is better than ours would be | Run a cart, hold a price, or issue an order reference |

## The reader never crosses the seam

**A buyer does the whole thing here, in this site's own interface.** Until
16 September they did not: the success address was riskmandate.ai's page for the
level, and a buyer who had spent ten minutes on one site was dropped onto another
one, with a different layout and a different voice, at the exact moment they had
just paid.

That was found by a synthetic buyer, logged as a confusion, and treated as a copy
problem. It was an architecture problem, and this page is the fix written down.
[The pages a buyer lands on](/admin/work/one-site-one-flow/) are now on this site.

**Reading somebody else's data is not wearing their interface.** When this store
renders riskmandate.ai's product data, it renders it in this store's own CSS. The
whole point is that a reader does not notice the seam — not that they are handed
across it politely.

## What makes it possible

**CORS is on, and it was verified rather than assumed.** On 16 September 2026,
`https://riskmandate.ai/abp-vaults.html` answered `access-control-allow-origin: *`.
So a page on this domain can read a file on that one, in the reader's browser,
with no server on either side.

**That is not yet used, and the reason is a rule rather than an oversight.** Every
page on this site that sells anything opens no network connection at all, and a
build check fails the release if one does. Reading a catalogue over CORS is opening
a connection on a selling page. That rule has been narrowed twice and loosened
never — the absolute half stayed absolute, the exception was named in the check,
and a deliberate break was run against the new check before anything shipped. The
same discipline applies here, and the narrowing comes **before** the first fetch.

## Debt, marked as debt

**The store holds product data today that belongs on the other side.** That is
allowed for now and it is written down rather than discovered later:
`data/abp-catalogue.json` is promoted from riskmandate.ai at build time with the
source URL, the retrieval time and a sha256 of the page it was read from.
{{claim:abp-catalogue-promoted}}

Promotion at build time is the honest version of the wrong arrangement: it cannot
silently drift, because the hash changes. It is still the wrong arrangement, and
the right one is reading it at runtime from the side that owns it.

## The brief, addressed to the RiskMandate team

**Asked for on 16 September: this side first, then the reverse.**

You are reading the store's half. The ask is that riskmandate.ai does the same in
the other direction — **reads this store's e-commerce surfaces rather than
re-implementing a cart.**

Concretely, and in the order that makes each one useful on its own:

1. **Publish a stable manifest for each level's artefact** — the zip, its size and
   its sha256, as JSON at a fixed address. The store's page after payment can then
   render your download in its own chrome instead of sending a buyer to you at the
   moment they have just paid. Today the store links to you with one sentence
   saying why; that sentence is the debt.
2. **Publish the shape catalogue as data**, at a stable address with a version
   field. The store already promotes it from your HTML at build time with a content
   hash, which works and is fragile in exactly the way parsing a page for data is
   always fragile.
3. **Do not build a cart.** If a reader on your side wants to buy, send them here
   with the shape already selected. One cart, one order reference, one set of
   prices — the same reason this store does not explain what a policy is.
4. **Agree the shape of what we both read**, not just the address. CORS makes the
   read possible; it does not make it safe to depend on. A stable address, a stable
   shape, and a version field are three different promises and all three are needed.

**What we are not asking for.** No callback, no session, no shared state and no
account on either side. Both of these are static sites and the whole arrangement
works because neither one needs the other to be up in order to be correct.

**Status: open.** It will be recorded here when it is answered, including if the
answer is no, because a brief that only appears when it succeeds is a brief nobody
should trust.
