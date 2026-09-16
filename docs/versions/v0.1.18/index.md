# v0.1.18 — the admin section becomes a console, with its own UI, the two payment rails written up as plans, a board of the work, and the queue the work comes out of

The admin pages ran on the shop's stylesheet, so a page whose job is *what is blocking a first sale* was set in the same warm paper and generous measure as a page explaining an offer slowly to somebody deciding whether to buy it. Those two want opposite things. /admin/ now has its own shell — a dark rail carrying counts, a four-rank status scale where only rank one is filled, and a page head that names the place rather than describing it. The architecture is adopted from the console at pt.newsroom.sgit.ai and credited in the stylesheet; the palette and the ranks are this store's.

Every number on it is computed from the files the pages are built from, so a tile cannot disagree with the page it points at. Admin also joins the top-level nav: it was public and unadvertised by design, and unfindable by the people building it by accident.

**Taking money, as two plans rather than two intentions.** /admin/rails/ carries what each provider is handed, what it is never handed, the steps in order, and what is still open. The Stripe plan changed shape this release on a ruling: the rail is no longer an amount-only link but Stripe's own catalogue, with a Customer created from the buyer's email even when a hundred-per-cent code means they pay nothing — which is the entire point of it. That reverses a position this store had published, and the reversal is written above the old reasoning rather than instead of it. Two findings came out of writing it down: a hundred-per-cent order creates no charge, so a webhook keyed on a succeeded payment would see every paid order and none of the free ones; and the host check pins every destination to Stripe's hosts, so a SumUp URL pasted in today is refused by the gate with a message about Stripe.

The catalogue Stripe needs is eight prices across six products, not sixty-two, because a price here does not vary by shape. It is generated from data/offers.yml and served beside the page, and a check compares the two.

**A board, and the queue behind it.** /admin/work/ is thirteen workstreams and seventy units of work in four columns, modelled on the board at sgraph.ai/en-gb/dev/workstreams/ — a workstream is never dragged; its column is computed from its own tasks, so the summary cannot contradict the detail. /admin/memos/ is where the work comes from: six memos kept word for word, each read into a brief and broken into units that carry the memo they came from. One memo contradicts another from the same day about where a buyer lands after paying, and the board says so rather than quietly resolving it.

**Hard rule twelve met a quotation, and the rule won.** A memo uses a barred word in passing. The check that holds the rule says in its own comment that an allowance is a thing that widens, so the term is withheld in place — a visible marker, counted, named, linked to the ruling — and the promise on the page changes from *nothing trimmed* to *nothing trimmed, one term withheld and marked*. The memo itself is intact in the data file. Whether a quotation should have been in scope is a ruling and it is on the board.

**One check narrowed, and exactly how far.** The stray-checkout check matched any absolute URL with a provider's name in it, which was right until a page here had a provider's name in its own address. It now exempts one origin, this one, and the reason is a fact rather than a convenience: nothing on store.sgit.ai takes a payment. Four checks added — the board is whole, the rendered board agrees with its own arithmetic, the Stripe catalogue is the offers, and a withheld term is declared. Seven deliberate breaks were run against them before shipping.

- Released: 2026-09-16
- Built from commit: ``
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
