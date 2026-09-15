# v0.1.14 — the gitignore rule that swallowed the PDFs, anchored — and a check that asks git

v0.1.12 and v0.1.13 did not deploy. The Python template's `downloads/` rule — pip's download cache — is unanchored, so it matches a directory of that name at any depth. It matched assets/downloads/, where the two walkthrough PDFs live, AND docs/admin/downloads/, where the build writes them. The gate builds from the working tree, where both are on disk, so it passed here; CI builds from a clean checkout, where neither is, so /admin/downloads/ was never created and four links on two pages were dead.

THE RULE IS NOW ANCHORED. `/downloads/` is pip's cache at the repository root, which is what it was ever meant to be, and anchoring it kills the whole class rather than negating it one path at a time. The explicit un-ignores stay beside it as belt and braces.

SECOND TIME ON THIS ESTATE, same shape both times: a language template's ignore rule matching a directory of this estate's own. The first swallowed admin/build/ on a sibling site and shipped a release with no gate at all, and the comment recording it sits three lines below the rule that just failed.

So the fix is not only the anchor. check_the_build_reads_nothing_git_ignores asks GIT what it ignores, across assets/, content/, data/ and docs/, and fails the release if the build reads or writes one of them — a source file absent from a clone builds a different site in CI, and a built file git ignores never reaches the deployed one. Neither should be found by a deploy going red, a third time.

- Released: 2026-09-15
- Built from commit: ``
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
