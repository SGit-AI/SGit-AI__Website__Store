---
title: What we do not say, and why
description: "The words this site does not use, the sentence it does not print, the claims it does not make, and the reason for each one. Every entry has a source, and most of them have an enforcement precedent behind them."
lead: "**A store's disclosures page is usually a list of things it is allowed to say.** This one is a list of things it is not, and why. Four of the entries are words. One is a whole sentence that a reader might reasonably expect to find on a page like this, and it is missing on purpose — because six questions have not been answered."
order: 8
toc: true
---

## The sentence that is not on this site

**We do not tell you what we can and cannot read.**

It is the sentence a reader expects from an encryption product, and it is absent
here because it is **a factual claim about system architecture, and it is
enforceable**. In November 2020 a regulator acted against a company for claiming
end-to-end encryption while its servers held the keys. The settlement imposed
**twenty years of third-party assessments**.

**Six questions have to be answered before the sentence can be printed:**

1. Are filenames encrypted?
2. Is directory structure encrypted?
3. What do object sizes reveal?
4. What does commit timing reveal?
5. Is there any recovery or escrow path?
6. Is there any support access mechanism?

**If anything leaks, the sentence gets a carve-out — not a softer adjective.**
Until then it is not on this site in any form. {{claim:cannot-read-unanswered}}

## The words this site does not use

**This page does not print them either**, and that is not an oversight. An
exception for the page that explains the rule is exactly how a rule stops applying:
one section becomes one page becomes "in context". Each is described closely enough
that anybody in the field will know which term is meant.

| The term that is not used | What is used instead | Why it was rejected |
|---|---|---|
| **The contested encryption term** — two words, the first of them a number, widely used in storage marketing | **End-to-end encrypted** as the primary term, **client-side encryption** as the mechanical one | The company that popularised it in storage marketing retired it, a widely cited cryptographer's critique calls the usage actively harmful, and as a search term it is dominated by an unrelated meaning from cryptography |
| **The contested recall term** — the human faculty, borrowed | **Durable** — resumes exactly where it left off, losslessly | Eight or more funded vendors contest it, two claim it as a category rather than a feature, the consumer meaning was captured by the largest model providers this year and carries a privacy connotation that fights an encryption product, and it implies **lossy summarisation of a lossless product** |
| **The contested autonomy term** — the adjective everyone reached for in 2025 | Say what the thing actually does | The analyst forecast since June 2025 is that over forty per cent of such projects will be cancelled by end 2027, the practice of applying it loosely reached corporate governance disclosure commentary in April 2026, and the closest competitor pointedly avoids it |
| **The absolute form of the tamper claim** | **Tamper evident, given a witness** | A rewritten hash chain verifies against itself. Tampering is detectable only when another party already holds an older hash — **the witness is a second clone**, which makes handing somebody a read key the act that makes the claim true. Append-only is stated as a policy, not a property |

All four are checked mechanically on every build: **if any of them reaches a page
of this site, the release stops.** {{claim:three-banned-words}}
{{claim:tamper-evident-witness}}

**This is a judgement and it is reversible.** The rule's own scope is copy that
faces a customer, and a page about vocabulary is arguably not that. If naming them
here is preferred, it is one edit in one place — on somebody's ruling, not on a
builder's preference.

## The claims this site does not make

**It is not a compliance assessment.** Presenting it as one would be dishonest, and
no page here does.

**No claim of conformity to any standard is made, sought or implied**, and the
whole family of words around conformity marking is avoided outright on this site —
not softened, avoided. That language raises the standard of care beyond ordinary
negligence, and it buys a reader nothing. A build check keeps it off every page.

**No opinion here is personal.** The **company** issues every opinion, with an
express non-assumption of personal responsibility on its face. A product sold on a
named individual's judgement runs at the test for assumed personal responsibility.

**The people who sell do not sign.** Selling buyers the question, suppliers the
answer, and an opinion vouching for the suppliers is the combination two industries
have already regulated. On this site that shows up as an absence: **no individual
is named beside a price anywhere.**

**Nothing here is derived from the international management standards.** They are
not adapted, not translated, not resold as a derivative and **not fed to a model** —
prohibited twice over. The same prohibition covers the payment card standard and
the centre's controls. **The launch catalogue is the European regulation**, which
is expressly reusable commercially including adaptation. {{claim:standards-not-adaptable}}
{{claim:graph-nodes}}

**Every derived instrument carries the unofficial banner, the attribution string
and the not-responsible line on its face**, and no institutional logos, crests or
original identifiers. That is licence terms, not caution.

## What is disclosed, rather than withheld

**Outputs are model generated.** The transparency article has applied since
**2 August 2026** and reaches a third-country party whose output is used in the
Union. The disclosure is on the face of each artefact, not only in a site footer,
and it is at the top of every page here. {{claim:transparency-article}}

**Findings are triaged, never raw.** Recall-optimised agents run at **0.388
precision** — about three findings in five are wrong. Every finding that reaches a
buyer has been **reproduced**, not reviewed. {{claim:precision-0388}}

**Where a third party is named, what is published is the record and never the
verdict** — facts, dates, sources, and no evaluative adjective attached to
anybody's name. That rule is [why the documents area is built and still closed](/dev-packs/).

**One phrase is held, and it is ours.** *Licence to operate* means a permission
granted by an authority. A second phrase in this vocabulary means a description of
exposure already carried. **They mean opposite things, both are in use, and the
collision has been open since 8 September** — so the second one appears nowhere on
this site, and a build check keeps it that way. {{claim:naming-collision-open}}

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
