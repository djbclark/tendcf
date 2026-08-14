#!/usr/bin/env python3
"""D27: diffs to the implementer map need an Approved-change trailer.

Fails (exit 1) when a commit that touches
docs/architecture/architecture-DEFINITIVE-v3.md does not contain a line
matching ``Approved-change: <non-empty>``.

Usage:
  bin/check_protected_docs.py                  # check HEAD
  bin/check_protected_docs.py --range A B      # commits in A..B (git log range)
  bin/check_protected_docs.py --commit-msg FILE  # commit-msg hook (staged diff)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROTECTED = "docs/architecture/architecture-DEFINITIVE-v3.md"
TRAILER = re.compile(r"^Approved-change:\s+\S", re.MULTILINE)


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(
            f"protected-docs: git {' '.join(args)} failed: {result.stderr.strip()}",
            file=sys.stderr,
        )
        sys.exit(2)
    return result.stdout


def fail(msg: str) -> None:
    print(f"protected-docs: FAIL: {msg}")
    sys.exit(1)


def require_trailer(body: str, label: str) -> None:
    if not TRAILER.search(body):
        fail(
            f"{label} touches {PROTECTED} but has no "
            "'Approved-change: <reason>' trailer in the commit message"
        )


def files_in_commit(sha: str) -> set[str]:
    out = git("diff-tree", "--no-commit-id", "--name-only", "-r", "-z", sha)
    return {p for p in out.split("\0") if p}


def check_head() -> None:
    sha = git("rev-parse", "HEAD").strip()
    if PROTECTED not in files_in_commit(sha):
        return
    require_trailer(git("log", "-1", "--format=%B", sha), sha[:12])


def check_range(a: str, b: str) -> None:
    shas = git("log", "--format=%H", f"{a}..{b}").split()
    for sha in shas:
        if PROTECTED in files_in_commit(sha):
            require_trailer(git("log", "-1", "--format=%B", sha), sha[:12])


def check_commit_msg(path: Path) -> None:
    staged = git("diff", "--cached", "--name-only", "-z")
    names = {p for p in staged.split("\0") if p}
    if PROTECTED not in names:
        return
    require_trailer(path.read_text(), "this commit")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--range",
        nargs=2,
        metavar=("FROM", "TO"),
        help="check commits in FROM..TO (git log range)",
    )
    parser.add_argument(
        "--commit-msg",
        type=Path,
        help="commit-msg hook: path to the message file; inspects the index",
    )
    args = parser.parse_args()
    if args.commit_msg is not None:
        check_commit_msg(args.commit_msg)
    elif args.range is not None:
        check_range(args.range[0], args.range[1])
    else:
        check_head()
    print("protected-docs: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
