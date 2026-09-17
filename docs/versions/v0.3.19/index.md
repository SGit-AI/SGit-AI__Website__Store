# v0.3.19 — the five doors, drawn the way v4 draws them

"What brings you here?" on the front page was five paragraphs of text in a grid
with no picture in it. On a phone that was three rows, 549 pixels, and it landed
1,185 pixels down — a section nobody meets. It is now the v4 handback's band: a
64px thumbnail, a label, one short line and an arrow.

**One strip, five cards.** The same five-up image already banner-cropped on
/audiences/ is cropped square here: laid out five squares wide inside a 64px box
and pulled left by a whole square per position, so each card shows its own fifth.

**On a phone the band comes first and scrolls.** A flex row with scroll-snap,
255px cards, 112px tall, the second card half-visible as the affordance — 247px
instead of 549, above the hero instead of below it. At 1280 the hero and the four
facts are one screen and the band is already under them, so the order is left
alone there; 1050 and below drops to three columns.

**The labels are shorter.** "Founder" rather than "You are a founder", and
"Shipping with agents." — the door sentence cut at its first comma rather than a
sixth field in the data, because the first clause is the same fact said shorter.

New rule: five doors, five thumbnails, five different fifths, and the short line
has to be the real sentence's own opening. It holds the load-bearing
`max-width: none` too — the reset's `img { max-width: 100% }` silently beat
`width: 500%` when this crop was first built on /audiences/ and left four of five
cards showing an empty box, with every other check passing.

- Released: 2026-09-16
- Built from commit: `c77fa621c3d0311d9eff6d0c79b052e1c39eacd2`
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
