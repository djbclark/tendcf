#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Is every rule in `check_projection()` guarded by a fixture that trips it alone?

Run on demand, not from `bin/schema_lint.py`. It neuters one `flag()` call
site at a time and runs the whole lint against each, so it costs ~20 lint
runs; the lint itself is on every commit and must stay fast.

WHY IT EXISTS. `schema-lint: OK` means every fixture was caught. It does not
mean every rule was exercised: a rule with no fixture that trips it *alone*
can be deleted and the gate stays green. That is not hypothetical — it is F8
of `docs/paper/reviews/2026-08-16_opus-5-high_projector-gate-review.md`, which
measured 8 of 19 sites guarded and found that the closed-container rule and
the trust-shaped-key rule masked each other: every fixture reaching either
tripped both, so neither was independently guarded, including the one M7
credited with catching a tombstone split.

Read the output as: SURVIVES means deleting that rule breaks nothing, so
either it needs a fixture or it is genuinely unfixturable and belongs in
`check_projector_properties()` as a property over synthesised bytes (which is
where N-8's 5 MiB ceiling went).

A NOTE ON METHOD, from the review that found this: run with bytecode caching
off. A stale `__pycache__` silently masked their first pass, which reports as
"the rule is guarded" — the exact false negative this tool exists to prevent.
`PYTHONDONTWRITEBYTECODE` is set for the child below.

    bin/flag_coverage.py
"""

from __future__ import annotations

import ast
import os
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
TARGET = REPO / "bin" / "projector.py"
FUNCTION = "check_projection"
LINT = REPO / "bin" / "schema_lint.py"


def flag_sites(source: str) -> list[int]:
    """Line numbers of every `flag(...)` call inside FUNCTION."""
    tree = ast.parse(source)
    try:
        fn = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == FUNCTION
        )
    except StopIteration:
        print(f"flag-coverage: ERROR: no {FUNCTION}() in {TARGET}", file=sys.stderr)
        raise SystemExit(2)
    return sorted(
        {
            node.lineno
            for node in ast.walk(fn)
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "flag"
        }
    )


def main() -> int:
    original = TARGET.read_text()
    lines = original.splitlines(keepends=True)
    sites = flag_sites(original)
    print(f"flag-coverage: {len(sites)} flag() call sites in {FUNCTION}()\n")

    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    survivors: list[int] = []
    try:
        for lineno in sites:
            mutated = list(lines)
            mutated[lineno - 1] = re.sub(
                r"\bflag\(", "(lambda *a, **k: None)(", mutated[lineno - 1], count=1
            )
            if mutated[lineno - 1] == lines[lineno - 1]:
                # A no-op "mutation" reads exactly like a guarded rule. Refuse
                # to report rather than report a number that means nothing.
                print(
                    f"flag-coverage: ERROR: line {lineno} did not mutate — the "
                    "call is spelled in a way this tool cannot neuter",
                    file=sys.stderr,
                )
                return 2
            TARGET.write_text("".join(mutated))
            result = subprocess.run(
                [str(LINT)], capture_output=True, text=True, cwd=REPO, env=env
            )
            caught = result.returncode != 0
            if not caught:
                survivors.append(lineno)
            print(
                f"  line {lineno:4d}  {'CAUGHT  ' if caught else 'SURVIVES'}  "
                f"{lines[lineno - 1].strip()[:60]}"
            )
    finally:
        TARGET.write_text(original)

    guarded = len(sites) - len(survivors)
    print(f"\nflag-coverage: {guarded}/{len(sites)} rules independently guarded")
    if survivors:
        print(f"flag-coverage: unguarded at line(s) {survivors}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
