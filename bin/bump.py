#!/usr/bin/env python3
"""Bump the site version, exactly once per release, in the two places that own it.

    bin/bump.py "what changed in this release"      # next minor
    bin/bump.py --major "what changed"              # vR.M+1.0

Does three things and stops:
  1. admin/build/version.txt  -> the next version
  2. data/releases.json       -> a record for it, RECORDED rather than reconstructed
  3. prints the commit subject CI requires

The release history table, the per-version pages and /versions/index.json are all
rendered from that one record, so they cannot disagree. The commit is filled in by
`bin/bump.py --commit <sha>` at the START of the NEXT release, because the sha does
not exist until the release is committed and amending the commit to record it would
change the very sha being recorded. This script refuses to bump while the previous
release still has none, and check_version_agreement fails the build for any release
that is not the newest and has no commit — so it cannot be forgotten and it cannot
be wrong.

The pipeline enforces all of this from the other side: tag-release reads
version.txt, finds the commit whose subject carries the same version, and refuses
to tag if the two disagree or if the bump was not the next minor. Doing it by hand
is how a release ends up with a duplicated row in the table or a tag pointing at
the wrong commit, both of which have happened on sibling sites. So it is a script.

Run `python3 build.py` afterwards — it propagates the new version to every page's
badge, the footer and llms.txt, and the gate fails if any of them disagree.
"""
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "admin/build/version.txt"
RELEASES = ROOT / "data/releases.json"


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--commit":
        return set_commit(sys.argv[2])
    args = [a for a in sys.argv[1:] if a != "--major"]
    major = "--major" in sys.argv[1:]
    if len(args) != 1:
        print(__doc__)
        return 2
    summary = args[0]

    cur = VERSION_FILE.read_text().strip()
    m = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", cur)
    if not m:
        print(f"version.txt does not carry a vX.Y.Z version: {cur!r}", file=sys.stderr)
        return 1
    rel, maj, mnr = (int(x) for x in m.groups())
    new = f"v{rel}.{maj + 1}.0" if major else f"v{rel}.{maj}.{mnr + 1}"

    data = json.loads(RELEASES.read_text())
    # The previous release must have had its commit recorded before this one starts.
    # A commit cannot contain its own hash, so the sha lands one commit later; this
    # is what stops "later" becoming "never".
    prev = data["releases"][0] if data["releases"] else None
    if prev and not re.fullmatch(r"[0-9a-f]{40}", prev.get("commit", "")):
        print(f"{prev['version']} still has no commit recorded. Run:\n"
              f"  bin/bump.py --commit $(git rev-parse HEAD)\n"
              f"and commit that, before bumping again.", file=sys.stderr)
        return 1
    if any(r["version"] == new for r in data["releases"]):
        print(f"data/releases.json already records {new} — the version was not bumped",
              file=sys.stderr)
        return 1

    data["releases"].insert(0, {
        "version": new,
        "date": date.today().isoformat(),
        # Filled in by --commit once the release is committed; the gate refuses to
        # ship a release that still has none.
        "commit": "",
        "site": "store.sgit.ai",
        "title": summary,
        "summary": summary,
        "changes": sorted({f.split("/")[0] for f in subprocess.run(
            ["git", "diff", "--name-only", "HEAD"], capture_output=True, text=True,
            cwd=ROOT).stdout.split() if not f.startswith("docs/")})[:12],
        # Written at release time from the release itself, so it is a record.
        "reconstructed": False,
        "basis": [],
    })
    data["current"] = new
    RELEASES.write_text(json.dumps(data, indent=2) + "\n")
    VERSION_FILE.write_text(new + "\n")

    print(f"{cur} -> {new}")
    print("  · admin/build/version.txt")
    print("  · data/releases.json (record added, commit still blank)")
    print()
    print("next:")
    print("  python3 build.py")
    print("  admin/build/validate.sh")
    print(f'  git commit -am "site {new}: {summary}"')
    print("  git push -u origin dev")
    print()
    print(f"then, at the start of the NEXT release (never by amending this one —")
    print(f"an amend changes the sha you are trying to record):")
    print(f"  bin/bump.py --commit $(git rev-parse HEAD)")
    return 0


def set_commit(sha):
    """Record the sha a release was built from. Separate from the bump because the
    commit does not exist until the release is committed, and an amend to add it
    would change the sha it is adding."""
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        print(f"not a full git sha: {sha!r}", file=sys.stderr)
        return 1
    data = json.loads(RELEASES.read_text())
    cur = data["current"]
    for r in data["releases"]:
        if r["version"] == cur:
            r["commit"] = sha
            RELEASES.write_text(json.dumps(data, indent=2) + "\n")
            print(f"{cur} -> commit {sha[:10]}")
            print("next: bin/bump.py \"what changed in the release you are starting\"")
            return 0
    print(f"no record for {cur} in data/releases.json", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
