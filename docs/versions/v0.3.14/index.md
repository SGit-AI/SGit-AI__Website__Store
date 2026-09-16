# v0.3.14 — the buying flow, end to end, and one order across both designs

The v4 handback supplied the policy picker, the cart, the checkout and the
post-purchase screens. All four are built at /next/ from the store's own data:
/next/policies/, /next/cart/, /next/pay/ and /next/paid/, mirroring the routes
the store that sells today already uses.

**It is the live store's order, not a second one.** The current store keeps an
order in the browser under one key; /next/ reads and writes that record — same
key, same schema, same line shape, same reference alphabet, same SKUs — so an
order started in this design round is still there on the current store, and
back. Two carts under two keys would be a bug that only appears for the one
person who uses both. A check compares the two models field by field on every
build.

**Still no typing surface anywhere.** Quantities are buttons, the behaviour
filter is a `<details>`, and the picker's search holds no field at all: the
query lives on the body element and characters are read off the keyboard. The
cost is that a phone with no hardware keyboard cannot type there, and the
dialog says so and points at the chips.

**Two findings about the published catalogue, both on the board.** The picker
offers a filter by behaviour that narrows nothing: the 23-behaviour vocabulary
is published and every shape's totals are published, but which behaviours make
up a particular grant is not. And for five of the fifteen shapes, wanted plus
not-asked overshoots the grant by exactly one — ten are exact. The panel's
capability strip was being painted green and amber as though those numbers
partitioned the grant; it is now one uncoloured cell per capability, and the
five shapes say so.

The evidence state behind each shape is typed out in data/products.yml rather
than derived, because deriving it got it wrong: `chatgpt-web`'s summary calls it
"the baseline every other shape is measured against", and a regex cannot read a
preposition.

New rule: check_every_anchor_a_page_points_at_is_there. check_links has always
held the file half of a link and never looked past the #. The site was clean
when the rule was added, which is the only comfortable moment to add one.

- Released: 2026-09-16
- Built from commit: ``
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
