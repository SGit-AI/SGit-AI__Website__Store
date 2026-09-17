# What lands, and when

The page a payment returns to. It shows the order held in this browser, because a payment link's return address is the same for every buyer and cannot carry your reference back.


## ABP Pack — Immediately, the moment the payment goes through

- **When:** Immediately. The page you land on after paying IS the download, with the size and the sha256 printed beside the link.
- **What you do:** Download the zip and check the hash. The page does the hashing in your own browser, against the hash it publishes.
- **How the key reaches you:** Not applicable. There is no vault at this level and so there is no key.
- **Done means:** You hold the zip, and the hash computed in your browser matches the hash that shape publishes.
- **How you check:** The check runs on the page. Nothing is uploaded and nothing is asked for.

## ABP Vault — 1 to 2 days, from your payment

- **When:** A person follows up within 24 hours of the payment landing. The vault key comes by a separate message.
- **What you do:** Nothing until the follow-up. Then clone the vault with the key.
- **How the key reaches you:** Out of band, and never on a page. A vault key is never published and never committed, so it reaches you by a separate route agreed when the vault is made.
- **Done means:** A vault exists, the licence file in it carries your name, the public key is off it, and you have opened it with your key.
- **How you check:** Your first clone. The licence file is in the tree.

## ABP Tailored — 1 to 3 days, from your reply, not from your payment

- **When:** A person follows up within 24 hours. The corrected vault follows what the prompt produced.
- **What you do:** Run MAP-A-GRANT.md where the agent runs — it ships in every template zip and in every vault, so you have it before and after paying — and send back the two files it writes, grant.json and mandate.json, and the session record, with no secret in them and your order reference on the message.
- **How the key reaches you:** Out of band, and never on a page.
- **Done means:** The corrected mandate and the recomputed delta are committed, with the note of what changed and why committed beside them.
- **How you check:** The commit is in your history and the note names every changed row.

## ABP Reviewed — 1 to 5 days, from your reply, not from your payment

- **When:** A person follows up within 24 hours to book the first session. The vault follows the second.
- **What you do:** Reply with two or three slots and who will be in the room.
- **How the key reaches you:** Out of band, and never on a page.
- **Done means:** Both sessions have been held, the record of what was asked and answered is committed, and the sign-off file is committed with the professional's name and the date.
- **How you check:** Three files in the tree, and the sessions dated in the record.

## What this page can tell you, and what it cannot

It shows the order this browser holds, and the provider's own session identifier when you came back through one. It cannot tell you a payment cleared: there is no server here to ask, and your receipt comes from the provider rather than from this site.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
