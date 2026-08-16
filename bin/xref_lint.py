#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Lint the cross-references in tendcf's prose corpus.

This corpus is pointer-dense — the guide, the implementer map, the paper,
the adjudications and GLOSSARY.md all navigate by `§N` and by relative
link — and nothing has ever checked that those pointers land.

Two layers, cheapest first:

  1. every relative markdown link resolves to a file that exists;
  2. every `§N` reference resolves to a section that exists — in the
     document that makes it, or, when the reference is qualified
     ("guide §4", "E1 §5.6", "map §13"), in the document it names.

WHAT THIS CANNOT DO, stated up front so nobody trusts it further than it
goes: it catches *dangling* references, not *mis-aimed* ones. A `§14`
that should have been `§7` resolves fine and passes silently — both
sections exist. That class is only caught by reading the target, and it
is the class that has actually bitten this repo. This lint is a floor,
not a substitute for checking what you cite.

Sections are identified the way the corpus writes them, which is four
ways:

  - `## 7. Title`            -> 7
  - `### 9.2 Title`          -> 9.2      (already dotted, taken as-is)
  - `### A. Title` under 16  -> 16.A     (composed with its parent)
  - `**8.8 Title**`          -> 8.8      (the paper's open questions are
                                          bold pseudo-headings, not ATX)

A fifth notation is deliberately NOT modelled: the guide's §19 open
questions are an ordered markdown list, and the 2026-08-15 reviews cite
them as `§19.8`. Those references are correct — item 8 exists — but the
linter reports them as dangling. Teaching it to read `8. **Question?**`
as §19.8 was tried and measured: applied corpus-wide it invents 279 ids
and silently resolves `E1 §1.4` and `§6.6`, which are genuinely dangling.
The false positive is cheaper than the false negative, so it stays. Every
instance today is in a frozen document (see FROZEN below); if a live
document ever cites `guide §19.N`, that finding is this gap, not a defect.

Exit 1 on any finding. No dependencies: this must run in a bare checkout.
"""

from __future__ import annotations

import argparse
import re
import sys
from fnmatch import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

# Qualifiers the corpus uses when pointing at a sibling document.
QUALIFIERS = {
    "guide": "paper/tendcf-architecture-guide.md",
    "paper": "paper/tendcf-architecture-paper.md",
    "map": "architecture/architecture-DEFINITIVE-v3.md",
    "e1": "architecture/e1-adjudication-xhigh-2026-08-15.md",
    "fable": "architecture/goal-file-schema-opinion-fable.md",
    "grok": "architecture/goal-file-schema-opinion-grok.md",
    "gemini": "architecture/goal-file-schema-opinion-gemini.md",
}

# Documents the default run does not lint, each paired with the policy that
# freezes it. This is a SCOPE rule, not a suppression list.
#
# The reason is that these documents are not allowed to change. A dangling
# `§19.8` in a dated review is an accurate record of what that reviewer
# wrote on that day; a dangling `§9.12` in a handoff is that session
# correctly reporting the defect it went on to fix. Editing either one to
# satisfy a linter would falsify a historical record, so the finding can
# never be actioned — and a finding nobody may act on is noise that buries
# the ones somebody must. The linter's subject is the LIVE corpus.
#
# Two properties keep this from being a way to hide work:
#
#   - Frozen documents are skipped as *sources* of references, never as
#     *targets*. They stay in the section index, because live documents
#     cite `E1 §5.6` and `Grok §9.2` and those must still resolve.
#   - `--all` lints them anyway. Nothing here becomes unmeasurable.
#
# The README.md inside each archival directory is NOT frozen. It is the
# live index describing the archive, edited whenever the corpus moves, and
# its links are the ones most likely to rot. Those stay in scope.
FROZEN: tuple[tuple[str, str], ...] = (
    (
        "docs/handoffs/*",
        "append-only session memory. docs/handoffs/README.md: 'These files "
        "are archival session artifacts ... Do not rewrite these files to "
        "bring them up to date.' CLAUDE.md: 'never rewritten'.",
    ),
    (
        "docs/paper/reviews/*",
        "dated review artifacts, each pinned to the commit it reviewed. "
        "docs/architecture/deprecated/README.md: 'The papers and reviews in "
        "docs/paper/ likewise describe whatever draft they were written "
        "against; correct the living docs, not these snapshots.'",
    ),
    (
        "docs/architecture/deprecated/*",
        "superseded designs. Its README.md: 'Do not edit files in this "
        "directory to bring them up to date.'",
    ),
    (
        "docs/architecture/goal-file-schema-opinion-*.md",
        "frozen inputs to the reconciliation, which records them as "
        "'inputs and ... superseded by this document'. The session that "
        "wrote the reconciliation verified them byte-untouched as a scope "
        "guarantee.",
    ),
    (
        "docs/architecture/projector-opinion-*.md",
        "frozen inputs to projector-reconciliation-2026-08-16.md, on the "
        "same footing as the goal-file-schema opinions above: each is one "
        "model's unedited stdout from a single cold pass, superseded by the "
        "reconciliation that adjudicates them. Two of their citations are "
        "recorded as refuted in that document's §0 and are left standing "
        "here — correcting an opinion in place would destroy the evidence "
        "that the audit caught it.",
    ),
    (
        "docs/architecture/e1-adjudication-*.md",
        "frozen adjudications, corrected in the reconciliation's §15 "
        "corrections register rather than in place, and verified "
        "byte-untouched by the same scope guarantee.",
    ),
)

# `§5.x` is a literal placeholder ("references of the form E1 §5.x"), not a
# pointer at a section called "x".
PLACEHOLDER = re.compile(r"\.x$", re.IGNORECASE)

ATX = re.compile(r"^(#{1,6})\s+([0-9]+(?:\.[0-9A-Za-z]+)*|[A-Z])\.?\s+\S")
BOLD = re.compile(r"^\*\*([0-9]+\.[0-9A-Za-z]+)\s+\S")
# `- **§14.2** Title` — the map defines its residue subsections as list items.
ITEM = re.compile(r"^\s*[-*]\s+\*\*§?([0-9]+\.[0-9A-Za-z]+)\*\*")
# A §ref, qualified only when a document name IMMEDIATELY precedes it.
# The window must stay tight: "E1 R4/§9.8" cites the map's §9.8, not E1's.
REF = re.compile(
    r"(?:\b(guide|paper|map|E1)\s+)?§\s?([0-9]+(?:\.[0-9A-Za-z]+)*)",
    re.IGNORECASE,
)
LINK = re.compile(r"\[[^\]]*\]\(([^)#\s]+)(?:#[^)]*)?\)")
FENCE = re.compile(r"^\s*```")


def sections(path: Path) -> set[str]:
    """Every section id the document defines."""
    found: set[str] = set()
    parent = None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = ATX.match(line)
        if m:
            label = m.group(2)
            if label.isdigit():
                parent = label
                found.add(label)
            elif "." in label:
                found.add(label)
                parent = label.split(".")[0]
            elif parent:  # a bare letter: `### A.` under `## 16.`
                found.add(f"{parent}.{label}")
            continue
        b = BOLD.match(line)
        if b:
            found.add(b.group(1))
            continue
        i = ITEM.match(line)
        if i:
            found.add(i.group(1))
    return found


def frozen_reason(rel: str) -> str | None:
    """The policy freezing `rel`, or None if it is a live document."""
    if rel.rsplit("/", 1)[-1] == "README.md":
        return None  # the archive's live index, not one of its artifacts
    for pattern, why in FROZEN:
        if fnmatch(rel, pattern):
            return why
    return None


def prose_lines(path: Path):
    """Yield (lineno, text), skipping fenced code so examples aren't linted."""
    in_fence = False
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield n, line


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--all",
        action="store_true",
        help="also lint the frozen documents (handoffs, dated reviews, "
        "deprecated designs, the opinions and adjudications). They are "
        "records that may not be edited, so their findings are not "
        "actionable — but they stay measurable.",
    )
    ap.add_argument(
        "--why-frozen",
        action="store_true",
        help="print the frozen paths and the policy behind each, then exit.",
    )
    args = ap.parse_args()

    if args.why_frozen:
        for pattern, why in FROZEN:
            print(f"{pattern}\n    {why}\n")
        print("README.md inside these directories is linted: it is the "
              "live index, not an archived artifact.")
        return 0

    # Every document is INDEXED. Only live ones are LINTED — a frozen
    # document is still a legitimate target of a live reference.
    docs = sorted(DOCS.rglob("*.md"))
    index = {p: sections(p) for p in docs}
    qualified = {
        k: (DOCS / v) for k, v in QUALIFIERS.items() if (DOCS / v).exists()
    }
    linted = [
        p
        for p in docs
        if args.all or not frozen_reason(p.relative_to(ROOT).as_posix())
    ]
    findings: list[str] = []

    for path in linted:
        rel = path.relative_to(ROOT)
        own = index[path]
        for n, line in prose_lines(path):
            for target in LINK.findall(line):
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                if not (path.parent / target).exists():
                    findings.append(f"{rel}:{n}: dead link -> {target}")

            for qual, ref in REF.findall(line):
                if PLACEHOLDER.search(ref):
                    continue
                q = qual.lower()
                if q and q in qualified:
                    where, name = index[qualified[q]], f"{qual} §{ref}"
                else:
                    where, name = own, f"§{ref}"
                if ref in where:
                    continue
                # An unqualified ref that lands in some sibling document is
                # ambiguous prose, not a dangling pointer. Only report refs
                # that resolve nowhere at all.
                if not q and any(ref in s for s in index.values()):
                    continue
                findings.append(f"{rel}:{n}: {name} resolves nowhere")

    for f in findings:
        print(f)
    skipped = len(docs) - len(linted)
    scope = (
        f"{len(linted)} documents linted"
        if args.all
        else f"{len(linted)} live documents linted, {skipped} frozen "
        f"skipped (--all to include, --why-frozen for the policy)"
    )
    print(
        f"\n{scope}, "
        f"{sum(len(s) for s in index.values())} sections indexed across "
        f"{len(docs)} documents, "
        f"{len(findings)} finding(s)."
    )
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
