# v0.1.15 — a partner's review, published in full, and the one rule that moved to let it be answered

A partner walked the whole store and sent back a critique. It is at /review/, verbatim and unedited, including the parts that say the entry is built the wrong way round and the £5 price may be a mistake. Under it: sixteen points sorted into keep, friction and recommendation; two drawings; and eleven proposals, each carrying what it would cost, what it touches, and a stance — two of which are “won’t do” and three of which need a ruling that is not the builder’s to make.

IT IS PUBLISHED FOR THE REASON THE LEDGER IS. A critique only the seller has read is a critique that changes nothing, and a review held back because it is unflattering would be the one thing on this domain kept off it for that reason.

THE RULE THAT MOVED, AND HOW FAR. Until this release there was no form, input, textarea or select anywhere in docs/, and a check refused any release that grew one. Asking somebody to answer a review with no way to answer it would have been the joke version of this site’s whole argument, so the rule moved by ruling — and it moved as little as it could. <form> is still barred everywhere, because it is the element that submits. <input> and <select> are still barred everywhere, because that is where a card number would be typed. <textarea> is allowed on one named page and nowhere else, and check_no_forms says which page by name.

check_no_network did not move an inch, so the one page that takes typing still cannot send it. A second check holds the boxes to carrying no name attribute — a name is what a field is called when it is submitted — to carrying an id so they can be labelled, to the page saying in those words where what you type goes, and to review.js containing no fetch, XHR, beacon or socket. Five deliberate breaks were run against those checks before this shipped.

The pages that said “no form, no input, no field” now say what is actually true, and the ledger carries the ruling with the reasoning. The markdown twin renders the whole review rather than the shortcode, because an agent reads the twin and a twin with the critique missing is a page about nothing.

Two things the gate found while this shipped. A release note that named the form element put a real one into its own version page, because inline() passes anything tag-shaped straight through for trusted content — right for a page whose author writes markup on purpose, wrong for a prose field in a JSON file. Release notes now render as data: escaped, no shortcode run, links held to safe schemes. And blank lines in a note now make paragraphs, which they did not, so every multi-paragraph note since v0.1.9 had been rendering as one wall of text on its own page.

- Released: 2026-09-15
- Built from commit: `06267775cd11172569f639a1ecfe7c5e530ad7fc`
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
