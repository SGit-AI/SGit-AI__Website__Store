# v0.1.17 — the vault is embedded, and the claim it costs is rewritten to be exactly true

The synthetic-users vault is embedded on its own review page, using the estate's component vendored byte for byte from sgit.ai/assets/vault-ui-embed.js with its source, date and sha256 in the header. Two surfaces, stacked: the vault's own app, then the file browser.

THE MECHANISM IS BETTER THAN AN EMBED AND IS WORTH READING. The frame is built at RUNTIME, which is why no page here has an iframe in its markup and why a check that only read HTML could not have seen this at all. It is opened carrying no credential; it announces itself with a message; only then is the read key posted to it with the target origin pinned, and replies from any other origin are ignored. So the key is not in a URL, not in history, not in a referrer and not in the frame's storage. It is a READ key, which opens a vault and cannot write to it.

THE CLAIM IT COSTS IS REWRITTEN RATHER THAN QUIETLY BROKEN. “No page here opens a network connection at all” was in the footer of every page, in llms.txt and on three content pages, and an embed makes it false. It now reads: every page that sells anything opens no connection at all, one kind of page embeds the vault it reviews from one host and says so on itself, and nothing anywhere sends anything about a reader. All three halves are checked.

Two checks, seven deliberate breaks. check_no_network now refuses the embed on any page that is not a review with a vault, and refuses any other script on the site from building a frame at all. check_the_embed_is_what_it_says holds the component to one host, to checking e.origin, to pinning targetOrigin, to keeping the credential out of a frame src, and holds the page carrying it to saying so in the reader's words.

The twelve-second fallback is stated rather than glossed: if the handshake does not complete the component opens the vault with the key in the frame's URL fragment, which is never sent to a server and never in a referrer but is in that frame's address. The page says so.

One thing found on the way. site.css already carried the estate's embed rules with a comment saying the surface is deliberately wider than the text column — and `.sgv-uiembed iframe` at (0,1,1) beat the component's own `.sgv-breakout` at (0,1,0), so the frame had always been exactly the width of the column and the comment described something that was not happening. The breakout moved to the container, and review.css stopped keeping a second copy of rules site.css owns.

- Released: 2026-09-16
- Built from commit: ``
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
