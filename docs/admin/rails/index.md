# Turning on a payment rail

How each payment rail gets turned on. One record per rail, and each is a plan rather than a description: what the store hands the provider, what the provider is never handed, what has to exist before a first real order, and in what order. Written while every checkout_url in data/checkout.yml is still empty, which is the state these pages exist to end.

- **Stripe** — Six products priced and reconciling, three coupons live, and the store's side of the hand-off built. No payment link, no promotion code, no webhook. — The rail for everything bought from a screen, and the one that turns a buyer into a customer — including a buyer who pays nothing. — https://store.sgit.ai/admin/rails/stripe/
- **SumUp** — Parked on 16 September. Not in the first end-to-end store. — Planned, half set up, and taken off the store for the MVP — the plan is kept rather than deleted. — https://store.sgit.ai/admin/rails/sumup/

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
