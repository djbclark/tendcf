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

Sections are identified the way the corpus writes them, which is three
ways:

  - `## 7. Title`            -> 7
  - `### 9.2 Title`          -> 9.2      (already dotted, taken as-is)
  - `### A. Title` under 16  -> 16.A     (composed with its parent)
  - `**8.8 Title**`          -> 8.8      (the paper's open questions are
                                          bold pseudo-headings, not ATX)

Exit 1 on any finding. No dependencies: this must run in a bare checkout.
"""

from __future__ import annotations

import re
import sys
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
    docs = sorted(DOCS.rglob("*.md"))
    index = {p: sections(p) for p in docs}
    qualified = {
        k: (DOCS / v) for k, v in QUALIFIERS.items() if (DOCS / v).exists()
    }
    findings: list[str] = []

    for path in docs:
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
    print(
        f"\n{len(docs)} documents, "
        f"{sum(len(s) for s in index.values())} sections, "
        f"{len(findings)} finding(s)."
    )
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
