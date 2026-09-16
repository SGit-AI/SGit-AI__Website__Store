# Never leave the site — and write down who owns what

*2026-09-16 · Voice memo, transcribed*

The whole purchase, and everything after it, happens on store.sgit.ai. The store owns e-commerce; riskmandate.ai owns the products and the policies; the two read each other's files over CORS rather than sending each other's visitors away. Do the store first, then brief the other side.

## The memo, word for word

> Okay, so this is now a very important concept, which there's two elements to this. So um, what I think we need to do here is let's do it all on the store docket. And then can you create a brief for the risk mandate to do also the reverse there? And the key here is that we now have two very distinct paths to experience the shopping cart experience and the sale. And I think what's important is to define very clearly, and again in guidelines and in pages that both agents can access, who owns what. So the point here is we have the store.eskit.ai, which is basically the e-commerce store, and we have the riskmandate.ai, which is the sort of the main commercialization path into it. Um, the store needs to look, and I have some more information about that coming soon, really like an e-commerce store, right? It's fundamentally like Amazon, right? Um, uh, that's the that's the vibe that we have. The risk mandate is going to be very focused on the risk, the, the structure, the, the guidance, the information, even showing the policies, showing it work, et cetera. The point is that you should be able to have the whole flow without leaving the site. So remember that all these sites have cores enabled. So cores, C-R-R-S, which is the cross-site um, origin in the browser. So um, that means that we can reuse the files and the JSON files from both. So the point here is that everything to do with e-commerce, everything to do with shopping cart, everything to do with the logic and the functionality of e-commerce and the workflows, and the redirections and the payments and all that stuff has to happen inside store.eskit.ai and everything that comes from the, the products, the lists, the, the, the, the, the access behavior policies that we have, the information, a lot of even some screenshots, etc. that comes from riskmandate.ai. So what I want to start with is that when you are in one of those websites, you never go to the other website, which is one of the findings that we had from our users where they correctly says, oh, I'm confused. Suddenly I just did a whole shopping experience in store.eskit and now it's suddenly I jump into risk mandate, which is a completely different UI, different briefing. So we should not do that. So what we want is to make sure that all of that and also all the branding elements and all the stuff in the CSS should come from the respective site, right? So we, first of all, let's do this for the store. Let's get the whole flow there. And then let's brief the risk mandate. And it might be okay in the short term to have a couple of files that on store that eventually will move to risk mandate, but eventually let's do this refactoring. But first, let's get the full experience end-to-end inside the store, right? Which basically means that when you get to the point of selling and you sold A vault, you should just see the link, you should see the vault, you should see everything because of me just embedding stuff, right? And actually, the vaults all come from public keys anyway, exposed keys. So this is quite um, a big element here.

## What we read in it

### The handover was a finding, and this is the fix

A synthetic buyer said it plainly: they did a whole shopping experience on one site and were dropped onto another with a different interface and a different voice at the exact moment they had just paid. That was logged as a confusion and treated as a copy problem. It was an architecture problem, and this memo says so.

### The boundary is stated as ownership, not as a link list

The store owns the cart, the e-commerce logic and workflows, the redirections and the payments. riskmandate.ai owns the products, the lists, the Agent Behaviour Policies, the information and the screenshots. Everything else follows from that sentence, including which side a file that exists in the wrong place has to move to.

### CORS is the mechanism, and it is already on

“All these sites have CORS enabled… that means we can reuse the files and the JSON files from both.” So the store does not copy the product data — it reads it from the side that owns it, and the same holds in reverse once the other side is briefed.

### The branding stays with the site the reader is on

Reading somebody else's data is not wearing their interface. The store renders riskmandate.ai's products in the store's own CSS, which is the whole reason the reader never notices the seam.

### After the sale, show them the thing

“When you sold a vault, you should just see the link, you should see the vault, you should see everything.” The vaults are opened with published read keys, so there is nothing to gate — and the store already has a working embed on the review pages, built at runtime with the key handed over by message and never in a URL. The hard part is already solved and is in the repository.

### The order is explicit, and it is the store first

Do the whole flow here, then write the brief for the other side. It is acceptable, for now, for a few files to live on the store that will eventually move — named as temporary rather than discovered as debt later.

### And the target feel is named

“Fundamentally like Amazon.” That is a shop, with a cart and a catalogue and a receipt, rather than an essay with a buy button under it — which is close to what several of the existing pages are.

## What this does not decide

### <b>It contradicts the memo from earlier the same day</b>

The Stripe memo has the buyer land on riskmandate.ai's page for their level, and the whole handover contract is built for that. This memo says they never leave the store. Both were given on 16 September and the later one wins, but the change is not free: the success address moves to this site, the ?order= contract becomes ours to render, and the task that was blocked on another team stops being blocked at all. That is written into the work rather than left for somebody to notice.

### It runs into this store's hardest rule

Every selling page on this site opens no connection, and a build check fails the release if one does. Reading a catalogue from riskmandate.ai over CORS is opening a connection on a selling page. The rule has been narrowed before and never loosened — the review pages embed one vault from one named host and the check names that exception. The same discipline applies here and the narrowing has to be written before the first fetch, not after.

### Where the product data lives while the other side is unbriefed

The store holds the shapes today. The memo permits that in the short term. What it does not say is how a reader can tell which side owns a file they are looking at, which is the thing that makes the debt visible instead of permanent.

### What “like Amazon” means here, concretely

More information is coming. Until it does, the risk of guessing is real: a store that sells four things is not improved by a mega-menu, and the site's whole argument is that it says what it does not know.

## The work it produced

- **Never leave the site** — https://store.sgit.ai/admin/work/one-site-one-flow/
- **Who owns what** — https://store.sgit.ai/admin/work/who-owns-what/

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
