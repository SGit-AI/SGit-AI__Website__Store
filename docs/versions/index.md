---
title: Release history
description: "Every release of this site, what changed in it, and the commit it was built from. The version is owned by one file, the release commit's subject repeats it, and the pipeline refuses to tag if the two disagree."
lead: "**Every push to the release branch is a release**, and every release is tagged. The version is owned by `admin/build/version.txt`, moved only by `bin/bump.py`, repeated in the release commit's subject, and **CI refuses to tag if the two disagree**. The same records are served as [JSON](/versions/index.json)."
order: 10
toc: true
---

## Releases

{{releases}}

## The pipeline that gates each one

Three jobs, in this order, the same order as every sibling site in this estate.

**1 · validate.** `admin/build/validate.sh` — the build is reproducible against the
committed output, the version agrees everywhere it appears, internal links
resolve, every canonical URL is on the host in `CNAME`, the credential tripwire is
clean, every inline script parses, and this site's own acceptance assertions hold.
**A failure stops the release: no tag, no publish.** It runs on pull requests too,
so branch work is gated before it ever reaches the release branch.

**2 · tag-release.** The version file is read, the release commit is found by its
subject line, and the two must agree. The tag must be the next minor — or a
deliberate major — after the previous latest. Historical tags missing from the
remote are backfilled, idempotently. Then the tag is pushed.

**3 · deploy.** The site is rebuilt from `content/` and published. It never runs
when validation failed, and never from a pull request.

## What this site's gate checks that a sibling's does not

This is the first site in the estate that carries a price, and **a page with a
price is an offer.** So the gate carries the rules that constrain an offer, as
machine assertions rather than as advice in a document:

- **The word that may never appear on a site carrying prices** appears on no page, in no heading, in no filename, and in no built artefact.
- **No conformity-marking language in any form**, and no claim to be a compliance assessment.
- **The three terms ruled out on 10 September** — one for encryption, one for recall, one for autonomy — reach no page, [including the page that explains why](/disclosures/). {{claim:three-banned-words}}
- **The sentence about what a provider can read** is absent until six questions about what leaks are answered. {{claim:cannot-read-unanswered}}
- **The absolute form of the tamper claim** never appears, and the honest form never appears without its witness in sight. {{claim:tamper-evident-witness}}
- **The open naming collision** reaches no page. {{claim:naming-collision-open}}
- **Every price** matches the pack that set it, to the penny.
- **Committed spend** is never mentioned without the negation in sight: professional services do not draw down committed spend, and the old version of that claim appears nowhere. {{claim:no-committed-spend}}
- **The model-generated disclosure** is above the fold on every page, not in a footer. {{claim:transparency-article}}

**A rule that only lives in a document gets broken by the next person who has not
read it.** These live in `tools/check_site.py`, and each one names the rule it
enforces.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
