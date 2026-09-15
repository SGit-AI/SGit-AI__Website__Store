---
title: Admin
description: "The internal surfaces of this store in one place: the walkthrough anybody can run end to end, the claim ledger, the dev packs, the release history and the purchase lab. Public, like every page here, and kept out of the sitemap because it is not a selling surface."
lead: "**Everything here is public**, because every page on this site is — there is no login, no account and nothing to gate. What this page is, is *findable*: one address that gathers the parts of the store that are for the people building it rather than for somebody buying."
order: 90
robots: "noindex,follow"
---

## Start here

**[Run the whole flow yourself →](/admin/try/)** — the walkthrough. A beta tester
or an agent goes from the catalogue to the page after payment in about four
minutes, for nothing, with a discount code printed on the page. Screenshots of
every step, and a script an agent can follow without a person in the loop.

**The same thing as PDFs**, for sharing or for reading away from a screen —
[by hand](/admin/downloads/store-walkthrough-by-hand-v0.1.11.pdf) (11 pages, every
screenshot) and [as an agent](/admin/downloads/store-walkthrough-as-an-agent-v0.1.11.pdf)
(7 pages, the assertions). Both are snapshots; the page is the source of truth.

## The rest of it

| | |
|---|---|
| [The claim ledger](/ledger/) | Every factual claim this site makes, with the state it earned and the date. Pages cite a claim and the chip links back here. |
| [What we do not say, and why](/disclosures/) | The words this site will not use, the sentence it will not print, and the naming collision that is still open. |
| [The dev packs](/dev-packs/) | The working documents behind the store, and the manifest of which of them are held back and why. |
| [Release history](/versions/) | Every release, what changed, and the commit it is. |
| [The purchase lab](/lab/) | The tool that turns a described deployment into a depth band. Nothing on it can be bought. |
| [What is not for sale yet](/catalogue/) | The offers that exist as specifications and have not been built. |

## Why this page is noindex and not private

**Nothing here is a secret and nothing here could be.** A static site publishes
every byte it carries: there is no server to ask who you are, and a page that
pretended otherwise would be lying about how it works. So this page is not
protected — it is simply **not advertised**. It carries `noindex` and it is kept
out of `sitemap.xml` and out of `llms-full.txt` — which *is* indexed, and would
have made this paragraph false by carrying the same codes in a bulk file. Somebody
handed the address can read it; nobody arrives by searching for a discount code.
[`llms.txt`](/llms.txt) still lists both pages with their descriptions, so an
agent finds the walkthrough and reads it at
[`/admin/try/index.md`](/admin/try/index.md).

**The walkthrough codes are the one thing on this site that is deliberately
published and deliberately not linked from a selling page.** They take a hundred
per cent off, which costs nothing today because no payment rail is live and the
only checkout that completes is a demonstration wallet that charges nobody. That
is not a promise, it is a build check: `check_printable_codes_need_a_dead_rail`
fails the release the moment a real payment link and a printed hundred-per-cent
code exist in the same build.
