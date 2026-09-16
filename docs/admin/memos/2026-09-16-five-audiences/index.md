# Five audiences, decoupled views, and the version the board can read

*2026-09-16 · Voice memo, transcribed*

The store does not qualify who is reading it. Five audiences, each with its own view and path and its own subset of the offers; the views driven by JSON and built as components rather than written out; and every vault — free ones included — carrying a version its reader’s board can read.

## The memo, word for word

> Okay, so on the store, I think that one of the problems that we have with the store right now is that we're not qualifying who the user is. So if you think about it, we have the free, the, you know, basically three core products, four core products, but the positioning of those products, what we're selling, even the features, even the angle of that, I think we need to, in a way, everywhere which is relevant, we need to take into account, and I think we should have five audiences, which is the founders, the investors, the C-level exec, the cybersecurity professionals, and the risk and governance slash GRC professionals. And in a way, not all products should be visible to all. You know, you, you can argue to an investor, you know, you're not going to sell, you know, five quid, 10 quid licenses, sorry, and 50 quid. I mean, you, you want to sell the more expensive ones, right? Because they need that. In fact, they might need in quantity, right? So I think what we need to have is we need to have the view that we have right now, which is kind of like this store, you know, out of the box. And I have more comments on that in a second. But then we need to have these very specific views and very specific paths, which is why you need to have from, um, from an architecture point of view, you need to decouple um, fundamentally a lot of the functionality to like JSON configuration files. So you can just slap on that. So think of it from a refactoring and a web components point of view, which is what you should be following from the coding.sgit.ai guidance and the um, nfrs.sgit.ai uh, support, sort of guidance, sorry. And, um, You know, everything should be web components, right? So if you should be able to refactor a lot of these views and, you know, without a lot of code changes, right? Because in a way, we, in fact, we should be changing this and we should be adapting. In fact, we then, you know, we'll run our synthetic users to it and we get feedback on that. Um, so I think that's, that's very important. Um, another important comment here, which is when you say, Can I have this in a form that my board can read? So this is where I feel like we, we really are missing a good explanation of what's inside the vault, because the point is every single vault should have one of these, right? Every single vault should have an, um, basically, um, should have uh, a version of the vault, a version of the policy that is adapted and is focused. On the, um, on the board, on the execs, so multiple audiences. So that's not a special offering. Like every vault has that, including the ones you, you can download for free. Well, one more thing, by the way, all these memos that I'm doing, you need to basically put them on your queue and then process them, create a brief out of it and add them to the queue, break them into units of work and then add them to the, um, the queue of of work that we have there.

## What we read in it

### The store sells to everybody and therefore to nobody

Four paid levels shown identically to whoever arrives. The memo names five audiences — founders, investors, C-level executives, cybersecurity professionals, and risk and governance or GRC professionals — and says the positioning, the features and the angle all move with who is reading.

### This is not the three buyer groups the store already has

The store has three: you run agents today, you are backing a company, you are a startup. The memo has five, cut differently — by role rather than by situation, with the two professional audiences having no equivalent today at all. So this is a replacement, not an addition, and the old group pages have to go somewhere rather than quietly stop being linked.

### Not every product is shown to every audience

“You are not going to sell a ten-quid licence to an investor… in fact they might need the expensive ones in quantity.” That is visibility as a property of the audience, which the catalogue has no concept of. It also raises a question nobody has answered: is the entry level hidden from an investor, or shown differently?

### The current store stays

“We need the view that we have right now, which is kind of like this store, out of the box.” The audience views are additional paths into the same catalogue, not a replacement for the front door.

### The architecture ask is the load-bearing one

Five audiences times the surfaces they touch is not writeable by hand, and the memo says so before asking for it: decouple the functionality into JSON configuration, refactor to components, following coding.sgit.ai and nfrs.sgit.ai. Both of those sites teach the same discipline this store already runs — generate every number from the data, never restate a measurement, fail the build when the two drift. The store is already data-driven at the content layer and hand-written at the view layer, and that is exactly the seam the memo is pointing at.

### The board-readable version is the sharpest single idea in the memo

“Can I have this in a form my board can read?” — and the answer is that every vault should already contain one. Not a paid extra: every vault, including the free downloads, carries the policy re-cut for the audience that has to sign it off. That turns the thing being sold from a document into a document that has already been translated for the people who decide, and it is the clearest answer yet to the commodity reading of the entry level.

### And the memo sets the process this page is

“All these memos that I’m doing, you need to put them on your queue and then process them, create a brief out of it, break them into units of work.” That is what this page and the board are. It was written for this memo and applied to the two before it.

## What this does not decide

### Whether the three existing buyer groups are retired or re-cut

Three pages exist, are linked from the nav, are in the sitemap and carry claims. Replacing them is a bigger change than adding five, and the memo does not say which.

### Hidden, or shown differently

An offer absent from an audience’s view and an offer present with different words are very different promises. One of them means this site shows different prices to different readers, which is a thing that needs saying out loud before it is built.

### What web components buy on a site that ships no framework

The store is a dependency-free static build whose pages open no connection. Components are a good answer to five views over one catalogue; the question is whether they are custom elements at runtime or generated partials at build time, and the answer has to keep the no-network rule intact rather than negotiate with it.

### Who the board-readable version is written by

Every vault carrying one is a per-vault deliverable across fifteen shapes. Whether that is generated, written once per shape, or written per sale is undecided and it changes what the entry level costs to fulfil.

## The work it produced

- **Qualify who is reading** — https://store.sgit.ai/admin/work/qualify-the-buyer/
- **The version the board can read** — https://store.sgit.ai/admin/work/board-readable/
- **Decouple the views** — https://store.sgit.ai/admin/work/decouple-the-views/
- **Keep the record** — https://store.sgit.ai/admin/work/the-record/

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
