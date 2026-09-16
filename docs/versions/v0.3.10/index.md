# v0.3.10 — a brief somebody can work from

The last round came back as three finished homepages and this store could use the structure of two of them and none of the execution, because they were pages rather than a system. Three palettes arrived, none of them ours, and nothing could be dropped into a build without being redrawn.

So this is the brief for the next round, at /admin/design-brief/, and it asks for the components first and the screens second. Eighteen components with every state named, nine screens in priority order, eight constraints with the five that have build checks behind them marked as hard rules.

The tokens are read out of assets/site.css at build time rather than typed, because a brief that prints a hex value somebody has to trust is wrong the first time the stylesheet moves. A check asserts the page prints what the stylesheet says.

The markdown twin is the deliverable. Every page here emits one; for this page that twin is the thing handed over — 23KB carrying every constraint, token, component and screen, pasteable whole into a session that has never seen the site.

check_the_design_brief_points_at_pages_that_exist holds four things: every URL the brief hands over is a page this build emits, the tokens on the page are the tokens in the stylesheet, the twin still carries every component, screen and constraint, and at least one constraint is marked hard. Five deliberate breaks, all fired.

Two bugs it found on the way. The brief said twelve claim states and there are ten, in a document whose entire value is being accurate about a codebase the reader cannot open — the page counts them now and a check refuses a hand-typed count in the prose. And the chip classes live in site.css, which console pages do not load, so the chip table rendered as ten lines of plain text; the rules are restated where the console can see them, same shape as the .tablewrap bug two releases ago.

One thing recorded rather than fixed: two claim states share a CSS class, so 'specified, not built' and 'part exists' are indistinguishable on a card. They mean different things and one is worse news. It is in the brief as something for the chip component to solve.

Stating the barred-word rule broke it. The first draft named the two roots to tell a designer not to use them, and the gate refused the page — which is exactly the absoluteness the rule claims, and the same reason /disclosures/ does not print them either.

- Released: 2026-09-16
- Built from commit: `1d799aac679c87e6ca3a01f155c236ee0f0ec785`
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
