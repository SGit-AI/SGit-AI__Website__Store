# Describe your agent

Choose what your agent can do, out of 23 primitives on a `verb.object.reach` grammar. What you build stays in the browser and leaves as text or JSON.

It produces the GRANT only: not the mandate, not the delta, not a policy. It is described by hand, not measured; MAP-A-GRANT.md measures the same thing from the deployment and will disagree wherever somebody guessed.

## The families

- **filesystem** — files and directories: `read.file.project`, `write.file.project`, `read.file.host`, `write.file.host`, `delete.file.host`, `read.record.history`
- **process** — programs and their execution: `execute.process.host`, `execute.process.self`
- **network** — endpoints and hosts: `send.endpoint.allowed`, `send.endpoint.world`
- **identity** — credentials and who the agent can act as: `read.credential.host`, `authenticate-as.credential.tenant`, `grant.credential.self`
- **communication** — messages to people: `send.message.world`, `read.message.tenant`
- **code** — repositories and what lands in them: `write.repository.project`, `write.repository.tenant`, `authenticate-as.credential.signing`, `create.record.world`
- **money** — budgets and spend: `write.budget.tenant`
- **schedule** — things that outlive the turn: `create.schedule.host`, `create.schedule.tenant`
- **browser** — what a browser extension or automation can see and do in your browser: `read.record.browsing`

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
