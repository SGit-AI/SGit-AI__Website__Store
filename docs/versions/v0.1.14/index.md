# v0.1.14 — the walkthrough PDFs were never committed: a template gitignore rule swallowed them

v0.1.12 and v0.1.13 did not deploy. The two walkthrough PDFs were never committed: the Python template's `downloads/` rule — pip's download cache — matched assets/downloads/, where they live. The gate builds from the working tree, where the files are on disk, so it passed here; CI builds from a clean checkout, where they are not, so /admin/downloads/ was never created and four links on two pages were dead.

THIS IS THE SECOND TIME on this estate, and the same shape both times: a language template's ignore rule matching a directory of this estate's own. The first swallowed admin/build/ on a sibling site and shipped a release with no gate at all, and the comment recording that is three lines above the one that just failed.

So the fix is not only the un-ignore. check_the_build_reads_nothing_git_ignores asks GIT what it ignores, over every file under assets/, content/ and data/, and fails the release if the build reads one of them. A source file that is on the builder's disk and absent from a clone is a release that builds differently in CI than it does here, and it should never again be found by a deploy going red.

- Released: 2026-09-15
- Built from commit: ``
- Reconstructed: no

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
