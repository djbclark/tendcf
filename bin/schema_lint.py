#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "jsonschema>=4.21", "rfc3339-validator", "rfc8785"]
# ///
"""Lint the tendcf Site Model and goal-file contracts.

Six layers, cheapest first:

  1. every schema/*.schema.json is itself a valid JSON Schema 2020-12;
  2. every schema is paired with an example and every example with a
     schema, derived from the filesystem — a new schema with no fixture
     is a finding, not a convention someone has to remember. Examples are
     bilingual: `.yml` for the Site Model, `.json` for the goal-file
     family, whose canonical form IS JSON (reconciliation §13);
  3. every goal-file-family `.json` fixture is canonical bytes — parsed
     with duplicate keys refused, every string NFC, and byte-identical to
     its own JCS (RFC 8785) re-serialization. This layer runs on bytes,
     before the parse, because a canonicalization violation is invisible
     after one: `json.loads` last-wins on duplicate keys and turns `15.0`
     into a number that reads as `15` (reconciliation §2.1, §13);
  4. every happy-path examples/*.{yml,json} instance validates against its
     schema;
  5. cross-file rules JSON Schema cannot express on its own — domain and
     bundle references resolve, service names are unique, launchd labels
     fall under a declared writer prefix, no writer prefix nests inside
     another; on the goal-file side, every interlock's bundle is used by
     at least one service, comprehensive-domain services fall under a
     `cfengine`-writer unit-writer prefix, and goal-file.schema.json
     itself never `$ref`s a def whose defaults would reintroduce
     ignore-unknown (reconciliation §13, Grok 8.6). Across the goal-file
     family: the diff's two hashes name the two goal-file fixtures,
     applying its hunks to the baseline reproduces the proposed file byte
     for byte, and the approval record's asserted ceremony class equals
     the one the validator derives (§11);
  6. each of the fifty-nine deliberately broken fixtures in examples/broken/
     and the six byte-class fixtures in examples/broken-bytes/ is caught
     BY THE LAYER IT NAMES. A lint that only accepts good input is not a
     check; a negative harness that accepts any objection at all is barely
     one, because a fixture that rewrites a file another layer reads makes
     that layer object by construction. Each case declares its rule class
     in examples/broken/README.md's "Caught by" column, read back at run
     time, and passes only if that class fired (reconciliation §13).

Layers 3 and 5 are the point. Layers 1-2 and 4 catch a broken or unpaired
schema; 3 and 5 are what keep a parses-fine-but-wrong document out of a
render (map §0 rule 6: prefer machine-checkable to conventional). Layer 6
is why we believe them.

What this does NOT yet do: projector goldens (reconciliation §13 —
`project(goal-file.json)` byte-equal to a checked-in `host_specific.json`,
and a projection carrying any top-level key but `vars` as a negative).
That layer needs an actual projector implementation, which does not exist
yet; it is the one part of §18 item 5 still open.

Exit 0 clean, 1 findings, 2 cannot read/parse.
Run from repo root:  bin/schema_lint.py
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import sys
import unicodedata
from contextlib import contextmanager
from pathlib import Path
from typing import Any, NamedTuple

import rfc8785
import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

REPO = Path(__file__).resolve().parent.parent
SCHEMA_DIR = REPO / "schema"
EXAMPLE_DIR = REPO / "examples"
BROKEN_DIR = EXAMPLE_DIR / "broken"
BYTE_CLASS_DIR = EXAMPLE_DIR / "broken-bytes"
PROJECTION_DIR = EXAMPLE_DIR / "broken-projection"
GOLDEN = EXAMPLE_DIR / "host_specific.json"
PROJECTOR = Path(__file__).resolve().with_name("projector.py")
EXPECTED_BROKEN = 59
EXPECTED_BYTE_CLASS = 6
EXPECTED_PROJECTION = 12

# example file -> schema file. report-rows.yml is a sequence of rows, each
# validated individually against the row schema. The goal-file family is
# JSON because that IS its canonical wire form (reconciliation §13);
# everything else here is YAML authoring shape.
EXAMPLES: dict[str, tuple[str, bool]] = {
    "services.yml": ("services.schema.json", False),
    "roles.yml": ("roles.schema.json", False),
    "launchd-writers.yml": ("launchd-writers.schema.json", False),
    "report-rows.yml": ("report-row.schema.json", True),
    "goal-file.json": ("goal-file.schema.json", False),
    "goal-file-baseline.json": ("goal-file.schema.json", False),
    "goal-diff.json": ("goal-diff.schema.json", False),
    "approval-record.json": ("approval-record.schema.json", False),
    "approval-record-reject.json": ("approval-record.schema.json", False),
}

# Fixtures that are PRODUCED, not authored, so no schema pairs with them.
# examples/host_specific.json is the projector golden: its correctness is
# "project(goal-file.json) emits exactly these bytes", checked by
# check_projector_golden(), not "it conforms to a shape". Writing a schema
# for it would be a second, weaker statement of the mapping that
# projector-reconciliation-2026-08-16.md already fixes — and one that could
# drift from the projector while still passing, which is the two-spellings
# defect the corpus keeps refusing. The pairing rail still holds for
# everything else; this list is checked for existence and for overlap with
# EXAMPLES so it cannot quietly widen.
OUTPUT_ONLY_EXAMPLES = frozenset({"host_specific.json"})

# Both answers to one ceremony, held to the same rules. §11 requires a
# reject-with-annotations fixture, and one accept fixture cannot supply it:
# `refused` is present iff the verdict is reject, so the schema's
# refused-iff-reject `if/then` has no instance to exercise either branch
# against while every record in the corpus says accept. The pair differs in
# `verdict`, `refused`, and `signature` and in nothing else — deliberately,
# so that what a reviewer's choice changes is exactly what differs here.
APPROVAL_RECORDS = ("approval-record.json", "approval-record-reject.json")

# Both goal files, held to the same schema and the same cross-entry rails.
# The baseline is not a lesser artifact: it is the device's currently
# approved state, the thing §7's privileged regions are derived against,
# and the left-hand side of the diff. A rail the proposed file passes and
# the baseline does not would mean the device already approved something
# the lint would refuse today.
GOAL_FILES = ("goal-file.json", "goal-file-baseline.json")

# Defs the goal-file schema must never $ref: each carries a default, an
# optional field, or required prose that would reintroduce a second
# spelling of one meaning or an ignore-unknown reading (reconciliation
# §15 C-1, §13 Grok 8.6).
GOAL_FILE_FORBIDDEN_REFS = {
    "common.schema.json#/$defs/contract_version",
    "common.schema.json#/$defs/domain_coverage",
    "common.schema.json#/$defs/interlock",
}

# Schemas that hold only shared $defs and describe no document of their own,
# so they have no fixture. Everything NOT listed here must be paired — see
# check_pairing(). The allowlist is what makes the guide's "every schema is
# paired with an example" claim machine-checkable rather than a convention.
DEFINITION_ONLY_SCHEMAS = {"common.schema.json"}

# The rule class every finding carries. A negative fixture declares which
# class must catch it (examples/broken/README.md's "Caught by" column, read
# back at run time), so a case can no longer pass on a finding from some
# other layer that happens to fire at the same time. Without this, deleting
# a rule stays green as long as *something* still objects to the fixture —
# and every fixture that rewrites a file the family layer reads makes
# something else object by construction.
#
# These strings are the README's vocabulary, not a parallel one: whatever
# is written here is what the table must say. Heads listed in
# DETAILED_RULE_HEADS carry their parenthetical into the class, because
# `family` alone would let a hash case pass on a ceremony finding; for
# `schema` the parenthetical is the keyword or def under test, prose the
# lint cannot produce, so it is documentation and is not checked.
RULE_SCHEMA = "schema"
RULE_SCHEMA_META = "schema meta"
RULE_PAIRING = "pairing"
RULE_DISCRIMINATOR = "lint discriminator"
RULE_CROSS_FILE = "cross-file"
RULE_GOAL_CROSS_FILE = "goal cross-file"
RULE_FAMILY_HASH = "family (hash)"
RULE_FAMILY_APPLY = "family (apply)"
RULE_FAMILY_CEREMONY = "family (ceremony)"
RULE_FAMILY_HOST = "family (host)"
RULE_FAMILY_REFUSED = "family (refused)"
RULE_JCS = "JCS idempotence"
RULE_DUPLICATE_KEY = "duplicate-key parse"
RULE_NFC = "NFC check"
RULE_PARSE = "parse"
RULE_HARNESS = "harness"
# One class, not two. A golden that no longer matches and a projection that
# violates an N-series invariant are the same defect seen from two sides —
# the bytes reaching $(sys.workdir)/data/host_specific.json are not the bytes
# the ceremony approved. Splitting them would buy a second class that only
# ever fires from one call site, and would need its own fixture to satisfy
# check_class_coverage() when the golden's "fixture" is the golden itself.
RULE_PROJECTION = "projection"

RULE_CLASSES = frozenset(
    {
        RULE_SCHEMA,
        RULE_SCHEMA_META,
        RULE_PAIRING,
        RULE_DISCRIMINATOR,
        RULE_CROSS_FILE,
        RULE_GOAL_CROSS_FILE,
        RULE_FAMILY_HASH,
        RULE_FAMILY_APPLY,
        RULE_FAMILY_CEREMONY,
        RULE_FAMILY_HOST,
        RULE_FAMILY_REFUSED,
        RULE_JCS,
        RULE_DUPLICATE_KEY,
        RULE_NFC,
        RULE_PARSE,
        RULE_HARNESS,
        RULE_PROJECTION,
    }
)

DETAILED_RULE_HEADS = frozenset({"family"})

# The classes no negative fixture can declare, and why — checked by
# check_class_coverage(), which requires every OTHER class to have at least
# one case. All three are about the corpus's shape rather than a document's
# content, and the negative harness's unit is a document overlay held in
# memory: an overlay cannot unpair a schema, delete a fixture from disk, or
# break the harness that is running it. Expressing them would need a second
# fixture mechanism that replaces whole directories, which is a larger thing
# than the coverage it would buy. Naming them here keeps the exemption
# explicit and reviewable rather than implicit in a check that never runs.
CLASSES_WITHOUT_FIXTURES = frozenset({RULE_PAIRING, RULE_SCHEMA_META, RULE_HARNESS})


class Finding(NamedTuple):
    rule: str
    msg: str
    # What the validator actually objected with — keywords, `if/then` style
    # branch locators, and the $defs names the failure passed through. Carried
    # on the finding because the jsonschema error is long gone by the time
    # check_declared_class() compares it to the README's parenthetical.
    evidence: frozenset[str] = frozenset()


findings: list[Finding] = []
PRINT_FINDINGS = True


def fail(msg: str, *, rule: str, evidence: frozenset[str] = frozenset()) -> None:
    """Record a finding under the rule class that produced it.

    `rule` is keyword-only and required rather than defaulted, so a new
    check cannot be added without deciding which class it belongs to —
    a default would make the declaration a convention someone has to
    remember, which is the failure mode check_pairing() already names.
    """
    if rule not in RULE_CLASSES:
        die(f"internal: fail() called with unknown rule class {rule!r}")
    findings.append(Finding(rule, msg, evidence))
    if PRINT_FINDINGS:
        print(f"schema-lint: FAIL: {msg}")


@contextmanager
def capture_findings(*, silent: bool = True):
    global findings, PRINT_FINDINGS
    prev_findings, prev_print = findings, PRINT_FINDINGS
    findings = []
    PRINT_FINDINGS = not silent
    try:
        yield findings
    finally:
        findings = prev_findings
        PRINT_FINDINGS = prev_print


def die(msg: str) -> None:
    print(f"schema-lint: ERROR: {msg}", file=sys.stderr)
    sys.exit(2)


def load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as exc:
        die(f"cannot read {path.relative_to(REPO)}: {exc}")


def load_any(path: Path) -> Any:
    """Load a fixture by extension: raw JSON for `.json`, YAML otherwise.

    The goal-file family's canonical form is JSON (reconciliation §13);
    everything else here is authored as YAML. `json.loads` is used
    directly for `.json` rather than routing through `yaml.safe_load`, so
    a `.json` fixture that happens to be invalid YAML (arbitrary UTF-8 in
    a string, e.g.) still loads correctly.
    """
    if path.suffix == ".json":
        try:
            return json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            die(f"cannot read {path.relative_to(REPO)}: {exc}")
    return load_yaml(path)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """`object_pairs_hook` that refuses I-JSON's silent last-wins.

    Python's default keeps the last of a repeated key and says nothing, so
    a duplicate is not merely legal-but-odd input — it is a second document
    hiding inside the first, and whichever of the two the signer canonicalized
    is unknowable after the parse (reconciliation §2.1).
    """
    seen: set[str] = set()
    for key, _ in pairs:
        if key in seen:
            raise ValueError(f"duplicate key {key!r}")
        seen.add(key)
    return dict(pairs)


def _non_nfc_strings(node: Any, path: str = "") -> list[str]:
    """Every key or string value not already in NFC, as a pointer list.

    JCS does not normalize — RFC 8785 takes NFC as an input precondition and
    passes anything else straight through, so idempotence cannot see this
    class at all. It is checked here because §2.1 says the lint checks it.
    """
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{path}/{key}"
            if not unicodedata.is_normalized("NFC", key):
                found.append(f"{here} (key)")
            found.extend(_non_nfc_strings(value, here))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            found.extend(_non_nfc_strings(value, f"{path}/{i}"))
    elif isinstance(node, str) and not unicodedata.is_normalized("NFC", node):
        found.append(path or "<root>")
    return found


def check_canonical_bytes(raw: bytes, label: str) -> Any | None:
    """The byte layer: is `raw` already the canonical form of what it says?

    Run before the parse and reported in terms of bytes, because that is the
    only place three of these violations exist. The pretty-printed twin of a
    canonical file, a trailing newline, and `15.0` where the schema wants
    `15` all parse to exactly the document the happy path parses to — the
    fixture IS the canonicalization test (§13), and after `json.loads` there
    is nothing left to test. Returns the parsed document, or None if the
    bytes do not parse at all.
    """
    try:
        doc = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        # Ordered before the ValueError below because JSONDecodeError is one:
        # bytes that are not JSON at all and bytes that are two documents in
        # a trench coat arrive through the same `except`, and they are not
        # the same finding.
        fail(f"{label}: not JSON: {exc}", rule=RULE_PARSE)
        return None
    except ValueError as exc:  # _reject_duplicate_keys
        fail(f"{label}: not canonical JSON: {exc}", rule=RULE_DUPLICATE_KEY)
        return None

    for pointer in _non_nfc_strings(doc):
        fail(f"{label}: {pointer} is not NFC-normalized", rule=RULE_NFC)

    canonical = rfc8785.dumps(doc)
    if canonical != raw:
        # "These bytes are not their own canonical form" is true but leaves a
        # human diffing 1.4 kB of one-line JSON, so name the class where the
        # class is cheap to name. The `.json` fixtures are consciously exempt
        # from the newline-at-EOF convention (§13) — hence the first branch.
        why = (
            "leading or trailing whitespace, which JCS emits neither of"
            if raw.strip() != raw
            else "member order, insignificant whitespace, or a number "
            "spelling JCS collapses"
        )
        fail(
            f"{label}: bytes are not their own JCS canonical form — {why}",
            rule=RULE_JCS,
        )
    return doc


def check_family_canonical_bytes() -> None:
    """Every `.json` fixture on disk is canonical bytes, checked as bytes."""
    for name in EXAMPLES:
        if not name.endswith(".json"):
            continue
        path = EXAMPLE_DIR / name
        if not path.exists():
            continue  # load_happy_examples() reports the missing fixture
        try:
            raw = path.read_bytes()
        except OSError as exc:
            die(f"cannot read examples/{name}: {exc}")
        check_canonical_bytes(raw, f"examples/{name}")


BROKEN_README = BROKEN_DIR / "README.md"

# | 13 | `13-schema-version-bump` | `schema_version: 2` | schema (`const`) |
_README_ROW = re.compile(r"^\|\s*\d+\s*\|\s*`([^`]+)`\s*\|.*\|\s*(.+?)\s*\|\s*$")


# A backticked token inside a `schema (...)` parenthetical. Backticks are the
# notation for "this is a machine-checkable claim"; bare words beside one —
# the "pattern" in ``schema (`abs_path` pattern)``, the "def" in
# ``schema (`absent` def)`` — are prose that makes the row read as English.
_CLAIM = re.compile(r"`([^`]+)`")

# Populated by read_declared_classes(); consumed by check_declared_class().
claims: dict[str, frozenset[str]] = {}


def read_declared_classes() -> dict[str, str]:
    """Each fixture's declared rule class, read from examples/broken/README.md.

    That table is already where a reader looks to find out what catches a
    given case, and a table only a reader consults drifts from the code the
    day someone changes a rule. Reading it back makes the "Caught by" column
    load-bearing: a wrong cell is a lint failure, and so is a fixture with no
    row or a row with no fixture. It also means the declarations live next to
    the fixtures they describe rather than in a second list inside this file,
    which would be the same drift with an extra step.
    """
    if not BROKEN_README.is_file():
        fail(
            "examples/broken/README.md is missing — the negative fixtures "
            "declare nothing, so nothing can be checked against them",
            rule=RULE_HARNESS,
        )
        return {}
    declared: dict[str, str] = {}
    for line in BROKEN_README.read_text().splitlines():
        row = _README_ROW.match(line)
        if row is None:
            continue
        case, raw_cell = row.group(1), row.group(2)
        cell = raw_cell.replace("`", "")
        head = cell.split(" (", 1)[0]
        rule = cell if head in DETAILED_RULE_HEADS else head
        if head == RULE_SCHEMA:
            claims[case] = frozenset(_CLAIM.findall(raw_cell))
        if rule not in RULE_CLASSES:
            fail(
                f"examples/broken/README.md: {case} is declared {cell!r}, which "
                f"names no rule class this lint can emit ({sorted(RULE_CLASSES)})",
                rule=RULE_HARNESS,
            )
            continue
        if case in declared:
            fail(
                f"examples/broken/README.md: {case} has more than one row",
                rule=RULE_HARNESS,
            )
        declared[case] = rule
    return declared


def check_declared_class(
    label: str, case: str, declared: dict[str, str], found: list[Finding]
) -> bool:
    """Did the class this case declares actually fire?

    "Something objected" is the weaker claim the harness used to make, and
    it is weak in a way that matters: a fixture that rewrites a file another
    layer reads makes that layer object by construction, so a case could go
    on passing after the rule it exists to test was deleted.
    """
    want = declared.get(case)
    if want is None:
        fail(
            f"{label}: has no row in examples/broken/README.md — every fixture "
            "declares the class that must catch it",
            rule=RULE_HARNESS,
        )
        return False
    fired = sorted({finding.rule for finding in found})
    if want not in fired:
        fail(
            f"{label}: declares {want!r}, but the finding(s) came from {fired} — "
            "the rule this case exists to test did not fire",
            rule=RULE_HARNESS,
        )
        return False
    return check_declared_claim(label, case, found)


def check_declared_claim(label: str, case: str, found: list[Finding]) -> bool:
    """Is the `schema (...)` parenthetical supported by what actually fired?

    The "Caught by" head has been executable since dddd31b; the parenthetical
    beside it was still prose, so `schema (`const`)` could sit on a case the
    `const` rule no longer touches and nothing would notice. It is the more
    specific half of the claim and was the unchecked one.

    Checked as *supported*, not as exhaustive: a cell naming one of several
    true causes passes, because on a failing `oneOf` every branch failed and
    picking the readable branch is the point. A cell naming something the
    validator never objected with does not pass.

    The limit that buys, measured rather than guessed: on case 24, swapping
    ``schema (`abs_path` pattern)`` for ``schema (`absent` pattern)`` stays
    green, because the service entry is a `oneOf` over present/absent and the
    absent branch really did fail too. Three other swaps do go red —
    `required`->`minLength`, `if/then`->`if/else`,
    `propertyNames`->`additionalProperties`. So this catches a cell that names
    a rule the validator never reached; it does not catch a cell that names
    the wrong sibling branch of a `oneOf` it did reach. Tightening that would
    mean ranking branch failures by relevance, which is a judgement the error
    does not carry.
    """
    want = claims.get(case)
    if not want:
        return True
    evidence: set[str] = set()
    for finding in found:
        if finding.rule == RULE_SCHEMA:
            evidence |= finding.evidence
    unsupported = sorted(want - evidence)
    if unsupported:
        fail(
            f"{label}: declares {', '.join(repr(u) for u in unsupported)}, which "
            f"the validator never objected with — it reported "
            f"{sorted(evidence) or 'nothing'}",
            rule=RULE_HARNESS,
        )
        return False
    return True


def check_class_coverage(declared: dict[str, str]) -> None:
    """Every rule class this lint can emit has at least one fixture behind it.

    The declarations make each case name its class; this asks the question
    from the other end. A class with no case is a layer whose rules could all
    be deleted without a red lint — the same hole the harness was targeted to
    close, one level up. Exemptions are CLASSES_WITHOUT_FIXTURES, and they
    are named there with their reason.
    """
    covered = set(declared.values())
    for rule in sorted(RULE_CLASSES - covered - CLASSES_WITHOUT_FIXTURES):
        fail(
            f"rule class {rule!r} has no negative fixture — every class this "
            "lint can emit needs at least one case, or an entry in "
            "CLASSES_WITHOUT_FIXTURES saying why it cannot have one",
            rule=RULE_HARNESS,
        )
    # The exemption list is the escape hatch, so it is held to being the
    # smallest one that works. Adding a covered class to it would otherwise
    # be the silent way to retire this check one class at a time — the same
    # move, one level up, that the declarations exist to stop.
    for rule in sorted(CLASSES_WITHOUT_FIXTURES & covered):
        fail(
            f"rule class {rule!r} is listed in CLASSES_WITHOUT_FIXTURES but "
            "does have a fixture — drop it from the exemption list",
            rule=RULE_HARNESS,
        )


def check_declaration_coverage(declared: dict[str, str], on_disk: set[str]) -> None:
    """A README row naming no fixture is a case someone deleted quietly."""
    for case in sorted(set(declared) - on_disk):
        fail(
            f"examples/broken/README.md: row {case!r} names no fixture on disk",
            rule=RULE_HARNESS,
        )


def check_byte_class_fixtures(declared: dict[str, str]) -> int:
    """Each examples/broken-bytes/*.json must be refused at the byte layer.

    Deliberately narrower than check_negative_fixtures(): only the byte
    layer runs, so a case another layer would also reject still proves what
    it claims to prove. Four of the five need that narrowness for a blunter
    reason — run 44, 45, 46 and 48 through every other layer in this file
    and they produce zero findings between them, because each parses to
    exactly the document the happy path parses to. Nothing downstream of
    the parse can see them at all. The NFD path (47) is the one that does
    reach downstream, and only as an unexplained hash disagreement between
    the goal file and the diff that names it; the byte layer is what turns
    that into "this string is not NFC", which is why §2.1 puts NFC in the
    lint rather than leaving it to canonicalization.
    """
    if not BYTE_CLASS_DIR.is_dir():
        fail(
            "examples/broken-bytes/ is missing — the byte-class fixtures are gone",
            rule=RULE_HARNESS,
        )
        return 0
    cases = sorted(BYTE_CLASS_DIR.glob("*.json"))
    if len(cases) != EXPECTED_BYTE_CLASS:
        fail(
            f"examples/broken-bytes/: expected {EXPECTED_BYTE_CLASS} cases, "
            f"found {len(cases)}", rule=RULE_HARNESS
        )
    caught = 0
    for case in cases:
        label = f"examples/broken-bytes/{case.name}"
        with capture_findings(silent=True) as case_findings:
            check_canonical_bytes(case.read_bytes(), label)
        if not case_findings:
            fail(
                f"{label}: was not caught (the byte layer accepted it)",
                rule=RULE_HARNESS,
            )
        elif check_declared_class(label, case.name, declared, case_findings):
            caught += 1
    return caught


def load_projector() -> Any | None:
    """Import bin/projector.py as a module.

    Not a package import: both files are `uv run --script` entry points with
    their own PEP-723 metadata, and bin/ is deliberately not importable. The
    projector is loaded by path so this lint runs the SAME code a device
    would, rather than a copy of its rules restated here — a restatement
    would be the second spelling that projector-reconciliation §9 (R22)
    names as the cost of a second implementation site.
    """
    if not PROJECTOR.is_file():
        fail(
            "bin/projector.py is missing — the projector goldens of §13 have "
            "nothing to invoke",
            rule=RULE_HARNESS,
        )
        return None
    spec = importlib.util.spec_from_file_location("tendcf_projector", PROJECTOR)
    if spec is None or spec.loader is None:  # pragma: no cover - import plumbing
        fail(f"cannot load {PROJECTOR.name} as a module", rule=RULE_HARNESS)
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - report, don't crash the lint
        fail(f"bin/projector.py failed to import: {exc}", rule=RULE_HARNESS)
        return None
    return module


def check_projector_golden(projector: Any, loaded: dict[str, Any]) -> bool:
    """project(goal-file.json) must be byte-equal to the checked-in golden.

    This is §13's "CI invokes the agent's own projector" made real. The
    comparison is on BYTES, not on parsed equality: the projection is
    hash-bound on the approval record, so a reordering or a respelling that
    parses the same is still a different artifact from the one consented to.
    """
    goal = loaded.get("goal-file.json")
    if goal is None:
        return False
    if not GOLDEN.is_file():
        fail(
            "examples/host_specific.json is missing — there is no golden to "
            "compare the projection against",
            rule=RULE_HARNESS,
        )
        return False
    try:
        produced = projector.project(goal)
    except Exception as exc:  # noqa: BLE001 - a refusal here is a finding
        fail(
            f"project(examples/goal-file.json) raised {type(exc).__name__}: {exc}",
            rule=RULE_PROJECTION,
        )
        return False
    expected = GOLDEN.read_bytes()
    if produced != expected:
        fail(
            "project(examples/goal-file.json) does not match "
            f"examples/host_specific.json ({len(produced)} bytes produced, "
            f"{len(expected)} expected)",
            rule=RULE_PROJECTION,
        )
        return False
    stray = projector.validate_projection(expected)
    if stray:
        fail(
            f"examples/host_specific.json is itself refused: {stray[0]}",
            rule=RULE_PROJECTION,
        )
        return False
    return True


def check_projection_fixtures(projector: Any, declared: dict[str, str]) -> int:
    """Each examples/broken-projection/*.json must be refused as a projection.

    Raw bytes, like the byte-class fixtures and for the same reason: several
    of the N-series invariants (pretty-printing, a trailing newline, a float
    spelling) are invisible after a parse, so a fixture that went through
    json.loads first would prove nothing about them.

    Note what is NOT here. N-1 (structure must not change when only `state`
    flips) and N-11 (two runs agree) are properties of the projector over
    TWO inputs, not shapes a single projection can have, so they are checked
    in check_projector_properties() instead of pretending to be fixtures.
    """
    if not PROJECTION_DIR.is_dir():
        fail(
            "examples/broken-projection/ is missing — the projection "
            "negatives are gone",
            rule=RULE_HARNESS,
        )
        return 0
    cases = sorted(PROJECTION_DIR.glob("*.json"))
    if len(cases) != EXPECTED_PROJECTION:
        fail(
            f"examples/broken-projection/: expected {EXPECTED_PROJECTION} "
            f"cases, found {len(cases)}",
            rule=RULE_HARNESS,
        )
    caught = 0
    for case in cases:
        label = f"examples/broken-projection/{case.name}"
        with capture_findings(silent=True) as case_findings:
            for msg in projector.validate_projection(case.read_bytes()):
                fail(f"{label}: {msg}", rule=RULE_PROJECTION)
        if not case_findings:
            fail(
                f"{label}: was not caught (validate_projection accepted it)",
                rule=RULE_HARNESS,
            )
        elif check_declared_class(label, case.name, declared, case_findings):
            caught += 1
    return caught


def check_projector_properties(projector: Any, loaded: dict[str, Any]) -> None:
    """N-1 and N-11: the two invariants no single fixture can express.

    N-1 is the R21 tripwire made mechanical. Flipping one entry's `state`
    must change exactly that value and leave the key structure identical; a
    projector that grew a tombstone branch would move the entry to a
    different container and fail here. N-11 is purity: same bytes in, same
    bytes out. Both are properties over two runs, which is precisely why
    they are checked and not fixtured — see check_projection_fixtures().
    """
    goal = loaded.get("goal-file.json")
    if goal is None:
        return

    try:
        if projector.project(goal) != projector.project(goal):
            fail(
                "project() is not deterministic — two runs over identical "
                "bytes disagreed",
                rule=RULE_PROJECTION,
            )
    except Exception as exc:  # noqa: BLE001
        fail(f"project() raised on the determinism check: {exc}", rule=RULE_PROJECTION)
        return

    services = (
        goal.get("domains", {})
        .get("supervision", {})
        .get("entries", {})
        .get("service", {})
    )
    present = sorted(
        eid for eid, body in services.items() if body.get("state") == "present"
    )
    if not present:
        fail(
            "goal-file.json has no present service — N-1 cannot be checked, "
            "so the tripwire is unguarded",
            rule=RULE_HARNESS,
        )
        return

    flipped = copy.deepcopy(goal)
    target = present[0]
    flipped["domains"]["supervision"]["entries"]["service"][target]["state"] = "absent"
    try:
        before = json.loads(projector.project(goal))
        after = json.loads(projector.project(flipped))
    except Exception as exc:  # noqa: BLE001
        fail(f"project() raised on the N-1 state flip: {exc}", rule=RULE_PROJECTION)
        return

    if _shape(before) != _shape(after):
        fail(
            f"flipping {target} to absent changed the projection's structure "
            "— a value decided the shape, which is R21's tripwire (N-1)",
            rule=RULE_PROJECTION,
        )


def _shape(node: Any) -> Any:
    """The key structure of a document, with every leaf value erased."""
    if isinstance(node, dict):
        return {key: _shape(value) for key, value in sorted(node.items())}
    if isinstance(node, list):
        return [_shape(item) for item in node]
    return None


def load_schemas() -> tuple[dict[str, dict], Registry]:
    schemas: dict[str, dict] = {}
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        try:
            schemas[path.name] = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            die(f"cannot read {path.relative_to(REPO)}: {exc}")

    registry: Registry = Registry()
    for name, schema in schemas.items():
        if "$id" not in schema:
            die(f"schema/{name} has no $id — relative $refs cannot resolve without one")
        registry = registry.with_resource(
            schema["$id"], Resource.from_contents(schema)
        )
    return schemas, registry


def check_schemas_valid(schemas: dict[str, dict]) -> None:
    for name, schema in schemas.items():
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as exc:  # noqa: BLE001 - surface whatever it says
            fail(
                f"schema/{name} is not a valid JSON Schema 2020-12: {exc}",
                rule=RULE_SCHEMA_META,
            )


def check_pairing(schemas: dict[str, dict]) -> None:
    """Every schema has a fixture and every fixture a schema, from the disk.

    EXAMPLES alone cannot enforce this: a schema nobody adds to it is simply
    never looked at, so the pairing rule would hold only as long as whoever
    added the schema remembered. Reading both directories closes that.
    """
    on_disk_schemas = {p.name for p in SCHEMA_DIR.glob("*.schema.json")}
    on_disk_examples = {p.name for p in EXAMPLE_DIR.glob("*.yml")} | {
        p.name for p in EXAMPLE_DIR.glob("*.json")
    }
    paired_schemas = {schema_name for schema_name, _ in EXAMPLES.values()}

    for name in sorted(on_disk_schemas - paired_schemas - DEFINITION_ONLY_SCHEMAS):
        fail(
            f"schema/{name} has no example: add one to examples/ and register the "
            "pair in EXAMPLES, or list it in DEFINITION_ONLY_SCHEMAS if it holds "
            "only shared $defs", rule=RULE_PAIRING
        )
    for name in sorted(paired_schemas - on_disk_schemas):
        fail(
            f"EXAMPLES pairs against schema/{name}, which does not exist",
            rule=RULE_PAIRING,
        )
    for name in sorted(on_disk_examples - set(EXAMPLES) - OUTPUT_ONLY_EXAMPLES):
        fail(
            f"examples/{name} is paired with no schema — register it in EXAMPLES, "
            "or list it in OUTPUT_ONLY_EXAMPLES if it is a produced artifact "
            "rather than an authored instance",
            rule=RULE_PAIRING,
        )
    for name in sorted(OUTPUT_ONLY_EXAMPLES - on_disk_examples):
        fail(
            f"OUTPUT_ONLY_EXAMPLES names examples/{name}, which does not exist",
            rule=RULE_PAIRING,
        )
    for name in sorted(OUTPUT_ONLY_EXAMPLES & set(EXAMPLES)):
        fail(
            f"examples/{name} is both output-only and paired in EXAMPLES — "
            "one or the other",
            rule=RULE_PAIRING,
        )
    for name in sorted(DEFINITION_ONLY_SCHEMAS - on_disk_schemas):
        fail(
            f"DEFINITION_ONLY_SCHEMAS names schema/{name}, which does not exist",
            rule=RULE_PAIRING,
        )
    for name in sorted(DEFINITION_ONLY_SCHEMAS & paired_schemas):
        fail(
            f"schema/{name} is both definition-only and paired with an example",
            rule=RULE_PAIRING,
        )


BRANCH_LOCATORS = {"then": "if/then", "else": "if/else", "not": "if/not"}

# Keywords that, appearing as a step in a schema_path, name the RULE being
# applied rather than a way of navigating into a subschema. `propertyNames` is
# the case that forces this: a bad domain key reports
# `pattern` at `['properties','domains','propertyNames','pattern']`, so the
# rule a reader would name is one step above the keyword jsonschema hands
# back. `properties` and `additionalProperties` are deliberately absent —
# they are navigation on nearly every path, and admitting them would let a
# cell claim `additionalProperties` for almost any failure.
APPLICATORS = frozenset(
    {
        "propertyNames",
        "patternProperties",
        "contains",
        "prefixItems",
        "items",
        "dependentSchemas",
        "dependentRequired",
        "unevaluatedProperties",
        "unevaluatedItems",
    }
)


def _refs_along(root: Any, path: list[Any]) -> set[str]:
    """The `$defs` names a failure passed through, read off the RAW schema.

    jsonschema resolves `$ref` before reporting, so an error that is really
    "this violates the `abs_path` definition" arrives naming only `pattern`,
    and one that is really "a tombstone may carry nothing but `state`"
    arrives naming only `additionalProperties`. Those keywords are true and
    useless: they are what D16(a) rules out, a message that cannot be
    resolved without a human going and reading the schema.

    The names are still in the schema document, so walk that alongside the
    error's schema_path and collect every `$ref` stepped through. This is
    what lets examples/broken/README.md keep saying `abs_path` — a claim a
    reader can act on — instead of degrading to `pattern` to stay checkable.
    """
    node, seen = root, set()
    if not isinstance(root, dict):
        return seen
    for step in path:
        if isinstance(node, dict) and "$ref" in node:
            target = node["$ref"]
            name = target.rsplit("/", 1)[-1]
            # Only local `#/$defs/...` refs resolve here; a cross-document ref
            # would need the registry, and no cell names one.
            if target.startswith("#/$defs/"):
                seen.add(name)
                node = root.get("$defs", {}).get(name, node)
        try:
            node = node[step]
        except (KeyError, IndexError, TypeError):
            return seen
    if isinstance(node, dict) and node.get("$ref", "").startswith("#/$defs/"):
        seen.add(node["$ref"].rsplit("/", 1)[-1])
    return seen


def schema_evidence(error: Any, root: Any) -> frozenset[str]:
    """Everything the README's parenthetical is allowed to claim about `error`.

    Includes the sub-errors of a failing `oneOf`: when a oneOf fails, every
    branch failed, so naming any branch's cause is honest. That is deliberate
    looseness, and it is the reason a cell is checked for being *supported*
    rather than for being the single best description.
    """
    found: set[str] = set()

    def collect(err: Any, prefix: list[Any]) -> None:
        full = prefix + list(err.schema_path)
        if err.validator is not None:
            found.add(str(err.validator))
        for step in full:
            if isinstance(step, str) and step in BRANCH_LOCATORS:
                found.add(BRANCH_LOCATORS[step])
            if isinstance(step, str) and step in APPLICATORS:
                found.add(step)
        found.update(_refs_along(root, full))
        for sub in err.context or []:
            collect(sub, full)

    collect(error, [])
    return frozenset(found)


def error_location(error: Any) -> str:
    """Where a schema violation is, in whichever coordinate space still has it.

    jsonschema drops the instance path for a boolean subschema: `descend()`
    short-circuits on `schema is False` and yields the error without
    appending the property it descended through, so a violation that is
    genuinely about one field arrives with `error.path == []`. Case 57
    measures it — `refused` under the `else` branch of
    approval-record.schema.json's refused-iff-reject rule reports
    `path=[]`, `schema_path=['else', 'properties']` — and the finding then
    named the offending value but nowhere at all.

    `error.schema_path` survives that, so it is added when the instance
    path is empty. Added, not substituted, and labelled: an instance path
    and a schema path are different coordinate spaces, and a reader who
    took `else/properties` for a field name in the document would be worse
    off than with the bare `<root>` this replaces. `<root>` alone remains
    the answer when both are empty.
    """
    where = "/".join(str(p) for p in error.path)
    if where:
        return where
    schema_where = "/".join(str(p) for p in error.schema_path)
    return f"<root> (schema {schema_where})" if schema_where else "<root>"


def validate(instance: Any, schema: dict, registry: Registry, label: str) -> None:
    validator = Draft202012Validator(
        schema, registry=registry, format_checker=FormatChecker()
    )
    for error in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        fail(
            f"{label}: {error_location(error)}: {error.message}",
            rule=RULE_SCHEMA,
            evidence=schema_evidence(error, schema),
        )


# row_type -> the $defs branch of report-row.schema.json that describes it.
ROW_TYPES = {
    "promise_outcome": "promise_outcome",
    "domain_coverage": "domain_coverage_row",
    "device_convergence": "device_convergence",
}


def validate_row(row: Any, schema: dict, registry: Registry, label: str) -> None:
    """Validate one reporting row against the branch its row_type names.

    Validating against the bare oneOf works but reports only "is not valid
    under any of the given schemas", which is the kind of error D16(a) rules
    out for the compiler — resolution needs a human, so the message has to
    say what is wrong and where. Discriminating first buys a field pointer.
    """
    row_type = row.get("row_type") if isinstance(row, dict) else None
    branch = ROW_TYPES.get(row_type)
    if branch is None:
        fail(
            f"{label}: row_type {row_type!r} is not one of {sorted(ROW_TYPES)}",
            rule=RULE_DISCRIMINATOR,
        )
        return
    validate(
        row,
        {"$ref": f"{schema['$id']}#/$defs/{branch}"},
        registry,
        f"{label} ({row_type})",
    )


def load_happy_examples() -> dict[str, Any]:
    loaded: dict[str, Any] = {}
    for example_name in EXAMPLES:
        path = EXAMPLE_DIR / example_name
        if not path.exists():
            fail(
                f"examples/{example_name} is missing — the schema has no fixture",
                rule=RULE_PAIRING,
            )
            continue
        loaded[example_name] = load_any(path)
    return loaded


def validate_loaded(
    loaded: dict[str, Any],
    schemas: dict[str, dict],
    registry: Registry,
    *,
    label_prefix: str = "examples",
) -> None:
    for example_name, (schema_name, is_sequence) in EXAMPLES.items():
        if example_name not in loaded:
            continue
        data = loaded[example_name]
        schema = schemas.get(schema_name)
        label = f"{label_prefix}/{example_name}"
        if schema is None:
            fail(
                f"schema/{schema_name} is missing (needed by {label})",
                rule=RULE_PAIRING,
            )
            continue
        if is_sequence:
            if not isinstance(data, list):
                fail(f"{label}: expected a sequence of rows", rule=RULE_SCHEMA)
                continue
            for i, row in enumerate(data):
                validate_row(row, schema, registry, f"{label}[{i}]")
        else:
            validate(data, schema, registry, label)
    check_cross_file(loaded)
    for goal_file in GOAL_FILES:
        check_goal_file_cross_file(loaded, goal_file)
    # Every layer runs over every case, including the family layer over a
    # case that rewrites the goal file it reads. That used to be gated: the
    # family layer stood down whenever `goal-file.json` was the overlaid
    # file, because otherwise its hash disagreement — inevitable, and about
    # nothing the case claims — would let cases 13-43 pass on the wrong
    # rule, leaving every §10 schema rule deletable without a red lint. The
    # gate bought that at the price of an asymmetry: an overlaid BASELINE
    # did not stand the layer down (52 and 53 need it live), so a schema
    # negative written as a broken baseline would have been masked exactly
    # the way 13-43 would have been.
    #
    # Declared classes make the gate unnecessary in both directions. A case
    # now has to be caught by the class it names, so the family layer's
    # noise on a schema case is noise the assertion ignores, and there is no
    # longer a file whose position in the family makes it the wrong place to
    # write a negative.
    check_goal_file_family(loaded)


def check_negative_fixtures(
    happy: dict[str, Any],
    schemas: dict[str, dict],
    registry: Registry,
    declared: dict[str, str],
) -> int:
    """Each examples/broken/<case>/ overlay must be rejected, by its own rule.

    Overlay files replace the happy-path document of the same name; the rest
    of the Site Model stays as in examples/. Silence on the expected failures
    — a negative fixture that the lint accepts is the finding, and so is one
    caught by a class other than the one its README row declares.
    """
    if not BROKEN_DIR.is_dir():
        fail(
            f"examples/broken/ is missing — all {EXPECTED_BROKEN} negatives are gone",
            rule=RULE_HARNESS,
        )
        return 0
    cases = sorted(p for p in BROKEN_DIR.iterdir() if p.is_dir())
    if len(cases) != EXPECTED_BROKEN:
        fail(
            f"examples/broken/: expected {EXPECTED_BROKEN} cases, found {len(cases)}",
            rule=RULE_HARNESS,
        )
    caught = 0
    for case in cases:
        overlays = sorted(case.glob("*.yml")) + sorted(case.glob("*.json"))
        if not overlays:
            fail(
                f"examples/broken/{case.name}: no overlay .yml/.json",
                rule=RULE_HARNESS,
            )
            continue
        loaded = {name: copy.deepcopy(doc) for name, doc in happy.items()}
        for overlay in overlays:
            if overlay.name not in EXAMPLES:
                fail(
                    f"examples/broken/{case.name}: {overlay.name} is not a Site Model file",
                    rule=RULE_HARNESS,
                )
                continue
            loaded[overlay.name] = load_any(overlay)
        label = f"examples/broken/{case.name}"
        with capture_findings(silent=True) as case_findings:
            validate_loaded(loaded, schemas, registry, label_prefix=label)
        if not case_findings:
            fail(
                f"{label}: was not caught "
                "(lint accepted a deliberately broken fixture)",
                rule=RULE_HARNESS,
            )
        elif check_declared_class(label, case.name, declared, case_findings):
            caught += 1
    return caught


def check_cross_file(loaded: dict[str, Any]) -> None:
    services_doc = loaded.get("services.yml") or {}
    roles_doc = loaded.get("roles.yml") or {}
    writers_doc = loaded.get("launchd-writers.yml") or {}

    domains = set((services_doc.get("domains") or {}).keys())
    bundles: dict[str, dict] = services_doc.get("bundles") or {}
    services: list[dict] = services_doc.get("services") or []
    roles = set((roles_doc.get("roles") or {}).keys())

    # --- launchd writer prefixes -------------------------------------------
    prefixes: list[str] = []
    seen_prefixes: set[str] = set()
    for writer in writers_doc.get("writers") or []:
        prefix = writer.get("prefix", "")
        if prefix in seen_prefixes:
            fail(
                f"launchd-writers: prefix {prefix} declared twice — one writer per prefix",
                rule=RULE_CROSS_FILE,
            )
        seen_prefixes.add(prefix)
        prefixes.append(prefix)

    # A prefix nested inside another puts two writers over one namespace,
    # which is the hazard this file exists to remove.
    for outer in prefixes:
        for inner in prefixes:
            if outer == inner:
                continue
            if inner.removesuffix("*").startswith(outer.removesuffix("*")):
                fail(
                    f"launchd-writers: prefix {inner} nests inside {outer} — "
                    "two writers over one label namespace", rule=RULE_CROSS_FILE
                )

    # --- bundles -----------------------------------------------------------
    interlock_ids: set[str] = set()
    for bundle_name, bundle in bundles.items():
        domain = bundle.get("domain")
        if domain not in domains:
            fail(
                f"services: bundle {bundle_name} names unknown domain {domain!r}",
                rule=RULE_CROSS_FILE,
            )
        for interlock in bundle.get("interlocks") or []:
            iid = interlock.get("id")
            if iid in interlock_ids:
                fail(
                    f"services: interlock id {iid!r} declared twice",
                    rule=RULE_CROSS_FILE,
                )
            interlock_ids.add(iid)

    # --- services ----------------------------------------------------------
    names: set[str] = set()
    for service in services:
        name = service.get("name", "<unnamed>")
        if name in names:
            fail(
                f"services: service name {name!r} declared twice",
                rule=RULE_CROSS_FILE,
            )
        names.add(name)

        if service.get("domain") not in domains:
            fail(
                f"services: {name} names unknown domain {service.get('domain')!r}",
                rule=RULE_CROSS_FILE,
            )
        if service.get("bundle") not in bundles:
            fail(
                f"services: {name} names unknown bundle {service.get('bundle')!r}",
                rule=RULE_CROSS_FILE,
            )

        role = service.get("role")
        if role is not None and role not in roles:
            fail(
                f"services: {name} names unknown role {role!r} (roles.yml)",
                rule=RULE_CROSS_FILE,
            )

        label = (service.get("launchd") or {}).get("label")
        if label is not None:
            matched = [p for p in prefixes if label.startswith(p.removesuffix("*"))]
            if not matched:
                fail(
                    f"services: {name} launchd label {label!r} falls under no declared "
                    "writer prefix (launchd-writers.yml) — this is the two-writers rail",
                    rule=RULE_CROSS_FILE,
                )

    for service in services:
        for target in service.get("depends_on") or []:
            if target not in names:
                fail(
                    f"services: {service.get('name')} depends_on unknown service {target!r}",
                    rule=RULE_CROSS_FILE,
                )

    # --- roles -------------------------------------------------------------
    for role_name, role in (roles_doc.get("roles") or {}).items():
        main = role.get("main")
        backups = role.get("backups") or []
        peers = role.get("peers") or []
        if main in backups:
            fail(
                f"roles: {role_name} lists its main host {main!r} as its own backup",
                rule=RULE_CROSS_FILE,
            )
        overlap = set(backups) & set(peers)
        if overlap:
            fail(
                f"roles: {role_name} lists {sorted(overlap)} as both backup and peer — "
                "a peer is explicitly not a candidate for main", rule=RULE_CROSS_FILE
            )


def check_goal_file_cross_file(loaded: dict[str, Any], name: str) -> None:
    """Cross-entry rules goal-file.schema.json cannot express alone.

    The goal file has no separate Site Model to check against — domain,
    bundle, and writer-prefix facts all live inside the one document, at
    its map-of-maps shape, so this mirrors check_cross_file()'s Site
    Model rules rather than sharing code with it (reconciliation §13).
    """
    goal_file = loaded.get(name)
    if not isinstance(goal_file, dict):
        return
    label = name.removesuffix(".json")
    domains: dict[str, Any] = goal_file.get("domains") or {}

    # (domain, prefix, writer) for every unit-writer entry, plus the
    # present service ids each domain declares.
    prefixes: list[tuple[str, str, str | None]] = []
    seen_prefixes: set[str] = set()
    service_ids_by_domain: dict[str, list[str]] = {}
    bundles_in_use: set[str] = set()

    for domain_name, domain in domains.items():
        if not isinstance(domain, dict):
            continue
        entries = domain.get("entries") or {}
        for service_id, service in (entries.get("service") or {}).items():
            if isinstance(service, dict) and service.get("state") == "present":
                service_ids_by_domain.setdefault(domain_name, []).append(service_id)
                bundle = service.get("bundle")
                if bundle:
                    bundles_in_use.add(bundle)
        for prefix, writer_entry in (entries.get("unit-writer") or {}).items():
            if prefix in seen_prefixes:
                fail(
                    f"{label}: unit-writer prefix {prefix!r} declared twice",
                    rule=RULE_GOAL_CROSS_FILE,
                )
            seen_prefixes.add(prefix)
            writer = writer_entry.get("writer") if isinstance(writer_entry, dict) else None
            prefixes.append((domain_name, prefix, writer))

    # --- every interlock's bundle is used by >= 1 present service ----------
    for domain_name, domain in domains.items():
        if not isinstance(domain, dict):
            continue
        entries = domain.get("entries") or {}
        for interlock_id, interlock in (entries.get("interlock") or {}).items():
            bundle = interlock.get("bundle") if isinstance(interlock, dict) else None
            if bundle not in bundles_in_use:
                fail(
                    f"{label}: domains/{domain_name}/entries/interlock/{interlock_id} "
                    f"bundle {bundle!r} is used by no present service",
                    rule=RULE_GOAL_CROSS_FILE,
                )

    # --- no unit-writer prefix nests inside another (one label namespace) --
    all_prefixes = [p for _, p, _ in prefixes]
    for outer in all_prefixes:
        for inner in all_prefixes:
            if outer == inner:
                continue
            if inner.removesuffix("*").startswith(outer.removesuffix("*")):
                fail(
                    f"{label}: unit-writer prefix {inner!r} nests inside {outer!r} — "
                    "two writers over one namespace", rule=RULE_GOAL_CROSS_FILE
                )

    # --- comprehensive-domain services fall under a cfengine writer --------
    for domain_name, domain in domains.items():
        if not isinstance(domain, dict) or domain.get("coverage") != "comprehensive":
            continue
        domain_prefixes = [(p, w) for d, p, w in prefixes if d == domain_name]
        for service_id in service_ids_by_domain.get(domain_name, []):
            matched = [
                (p, w)
                for p, w in domain_prefixes
                if service_id.startswith(p.removesuffix("*"))
            ]
            if not matched:
                fail(
                    f"{label}: domains/{domain_name}/entries/service/{service_id} "
                    "falls under no declared unit-writer prefix — the two-writers rail, "
                    "applied to the goal file", rule=RULE_GOAL_CROSS_FILE
                )
            elif not any(w == "cfengine" for _, w in matched):
                fail(
                    f"{label}: domains/{domain_name}/entries/service/{service_id} "
                    "falls under a unit-writer prefix whose writer is not cfengine",
                    rule=RULE_GOAL_CROSS_FILE,
                )


def canonical_sha256(doc: Any) -> str:
    """The content address of a goal file: sha256 over its JCS bytes.

    Taken over the canonical serialization of the loaded document rather
    than over the file as it sits on disk, so this holds for a negative
    fixture's overlay too. That the happy fixtures' disk bytes already ARE
    those bytes is layer 3's claim, checked separately.
    """
    return "sha256:" + hashlib.sha256(rfc8785.dumps(doc)).hexdigest()


def derive_ceremony_class(diff: dict[str, Any]) -> str:
    """The validator's derivation, never the approver's assertion (§11).

    `ceremony_class` is in the approval record so the approver states what
    they believed they were signing; it is derived here so a mismatch
    between belief and structure is a refusal rather than a silent
    downgrade. Privileged iff any hunk falls under `device-trust` or any
    coverage transition touches `deliberately-unmanaged` or leaves
    `comprehensive` (§4.3's one uniform rule).

    §7 wants the derivation done against the baseline's structure, and this
    reads the diff's own stated `old`. That holds only in composition: it is
    apply_diff() pinning every stated `old` to what the baseline actually
    says that stops a lying `old` from buying a downgrade here, and both run
    inside check_goal_file_family(). Lifting this function out on its own
    would quietly drop that.
    """
    if "version_bump" in diff:
        return "baseline"  # a migration; first adoption has no diff at all
    if "device-trust" in (diff.get("hunks") or {}):
        return "privileged"
    for change in (diff.get("coverage_changes") or {}).values():
        old, new = change.get("old"), change.get("new")
        if "deliberately-unmanaged" in (old, new):
            return "privileged"
        if old == "comprehensive" and new != "comprehensive":
            return "privileged"
    return "ordinary"


def apply_diff(baseline: Any, diff: dict[str, Any], label: str) -> Any | None:
    """Apply a goal diff to a baseline goal file, or report why it will not.

    The diff carries no operation field — presence of `old`/`new` IS the
    operation (§11) — so applying one is the only way to find out whether
    it says what it claims. Both present is a replace, which is what a
    tombstone transition looks like since removal is a state (§6); `new`
    alone is an add; `old` alone is the bare entry deletion that means
    "stop managing", the case §6 singles out as the real smuggling hazard.
    Returns None once anything has been reported, because a result derived
    from an already-wrong application would only produce a second, less
    informative finding downstream. Two limits worth stating: the domain is
    non-migration diffs — `version_bump` is a header change (§5) this does
    not apply, and cannot reach today because `schema_version` is a `const`
    — and the returned document aliases the diff's `new` objects, so it is
    safe to serialize and not safe to mutate.
    """
    result = copy.deepcopy(baseline)
    baseline_domains: dict[str, Any] = baseline.get("domains") or {}
    domains: dict[str, Any] = result.setdefault("domains", {})
    ok = True

    for domain_name, kinds in (diff.get("hunks") or {}).items():
        domain = domains.setdefault(domain_name, {})
        entries = domain.setdefault("entries", {})
        for kind, ids in kinds.items():
            bucket = entries.setdefault(kind, {})
            for entry_id, hunk in ids.items():
                where = f"hunks/{domain_name}/{kind}/{entry_id}"
                if hunk.get("old") == hunk.get("new") and "old" in hunk:
                    # Not merely redundant. §11 says an empty diff is not a
                    # document at all; a hunk that changes nothing is that
                    # same nothing, smuggled past the check as volume. What
                    # it costs is attention, and attention is the scarce
                    # thing an approval ceremony spends (§16 iv).
                    fail(
                        f"{label}: {where} states the same entry as `old` and "
                        "`new` — a hunk that changes nothing is padding for the "
                        "hunks that do", rule=RULE_FAMILY_APPLY
                    )
                    ok = False
                if "old" in hunk:
                    if bucket.get(entry_id) != hunk["old"]:
                        fail(
                            f"{label}: {where} `old` is not the baseline's entry",
                            rule=RULE_FAMILY_APPLY,
                        )
                        ok = False
                elif entry_id in bucket:
                    fail(
                        f"{label}: {where} has no `old`, so it is an add, but the "
                        "baseline already carries that entry", rule=RULE_FAMILY_APPLY
                    )
                    ok = False
                if "new" in hunk:
                    bucket[entry_id] = hunk["new"]
                else:
                    bucket.pop(entry_id, None)
            if not bucket:
                del entries[kind]
        if not entries:
            del domain["entries"]

    for domain_name, change in (diff.get("coverage_changes") or {}).items():
        stated_old = change.get("old")
        if stated_old == change.get("new"):
            # §9.7 makes coverage a distinct reviewable section precisely so
            # it cannot be lost in entry noise. A transition to where it
            # already was is entry noise wearing that section's clothes.
            fail(
                f"{label}: coverage_changes/{domain_name} states {stated_old!r} "
                "on both sides — that is not a transition", rule=RULE_FAMILY_APPLY
            )
            ok = False
        # A domain absent from the map is undeclared — the third silence
        # class, and the reason a first appearance is a reviewable coverage
        # change rather than entry noise (§4.1).
        actual_old = (baseline_domains.get(domain_name) or {}).get(
            "coverage", "undeclared"
        )
        if actual_old != stated_old:
            fail(
                f"{label}: coverage_changes/{domain_name} claims old "
                f"{stated_old!r}, but the baseline has {actual_old!r}",
                rule=RULE_FAMILY_APPLY,
            )
            ok = False
        if change.get("new") == "undeclared":
            leftover = (domains.get(domain_name) or {}).get("entries") or {}
            if leftover:
                fail(
                    f"{label}: coverage_changes/{domain_name} retreats to "
                    "undeclared while its entries survive — a domain leaves the "
                    "map only once the hunks have deleted everything under it",
                    rule=RULE_FAMILY_APPLY,
                )
                ok = False
            domains.pop(domain_name, None)
        elif domain_name in domains:
            domains[domain_name]["coverage"] = change.get("new")
        else:
            fail(
                f"{label}: coverage_changes/{domain_name} declares a domain no "
                "hunk populates — a declared domain with no entries is not a "
                "document the schema admits", rule=RULE_FAMILY_APPLY
            )
            ok = False

    for domain_name, domain in domains.items():
        if "coverage" not in domain:
            fail(
                f"{label}: hunks create domain {domain_name} with no matching "
                "coverage_changes entry — its first appearance is unreviewed",
                rule=RULE_FAMILY_APPLY,
            )
            ok = False

    return result if ok else None


def check_refused_paths(
    diff: dict[str, Any], record: dict[str, Any], label: str
) -> None:
    """Every `refused` annotation names something the diff actually proposes.

    §11 makes `refused` annotation only — it does not change what was
    refused, which is all of it (§9.3's all-or-nothing rule) — but it exists
    for a purpose: telling the proposer what to re-render. A key-path that
    resolves to no hunk and no coverage change tells them to re-render
    nothing, which is the one thing an annotation must not do. It is also the
    shape a stale record takes after the diff it answers has moved on.

    The two reviewable sections are the two addressable ones: a hunk at
    `hunks/<domain>/<kind>/<id>`, and a coverage transition at
    `coverage_changes/<domain>` — a distinct section precisely so it cannot
    be lost in entry noise (§9.7), and so refusable on its own. The id is
    taken as the remainder rather than the next segment, so an id carrying a
    `/` addresses correctly.
    """
    hunks: dict[str, Any] = diff.get("hunks") or {}
    coverage: dict[str, Any] = diff.get("coverage_changes") or {}
    for path in record.get("refused") or []:
        parts = path.split("/", 3)
        if parts[0] == "hunks" and len(parts) == 4:
            if parts[3] in ((hunks.get(parts[1]) or {}).get(parts[2]) or {}):
                continue
        elif parts[0] == "coverage_changes" and len(parts) == 2:
            if parts[1] in coverage:
                continue
        fail(
            f"{label}: refused path {path!r} names no hunk and no coverage "
            "change in the diff — an annotation that tells the proposer to "
            "re-render nothing",
            rule=RULE_FAMILY_REFUSED,
        )


def check_goal_file_family(loaded: dict[str, Any]) -> None:
    """The family fixtures must describe one another exactly.

    Each of these is a rule the running system holds and the fixture set
    would otherwise only gesture at: the two hashes are what §9.1's
    cross-check compares, applying the hunks is what makes the diff an
    honest report of the pair rather than prose beside it, and the ceremony
    class is derived, never taken on the approver's word (§11).
    """
    goal = loaded.get("goal-file.json")
    baseline = loaded.get("goal-file-baseline.json")
    diff = loaded.get("goal-diff.json")
    records = {
        name: loaded[name]
        for name in APPROVAL_RECORDS
        if isinstance(loaded.get(name), dict)
    }
    if not all(isinstance(doc, dict) for doc in (goal, baseline, diff)) or not records:
        return

    goal_hash = canonical_sha256(goal)
    baseline_hash = canonical_sha256(baseline)

    if diff.get("baseline_sha256") != baseline_hash:
        fail(
            "goal-diff: baseline_sha256 is not H(examples/goal-file-baseline.json) "
            f"— expected {baseline_hash}", rule=RULE_FAMILY_HASH
        )
    if diff.get("proposed_sha256") != goal_hash:
        fail(
            "goal-diff: proposed_sha256 is not H(examples/goal-file.json) "
            f"— expected {goal_hash}", rule=RULE_FAMILY_HASH
        )

    # One host across the family. A record signed for one device against a
    # diff computed for another is DC-2's per-target validity, defeated.
    hosts = {
        name: doc.get("host")
        for name, doc in loaded.items()
        if name.endswith(".json") and isinstance(doc, dict)
    }
    if len(set(hosts.values())) > 1:
        fail(
            f"goal-file family: fixtures disagree on host: {hosts}",
            rule=RULE_FAMILY_HOST,
        )

    applied = apply_diff(baseline, diff, "goal-diff")
    if applied is not None and rfc8785.dumps(applied) != rfc8785.dumps(goal):
        fail(
            "goal-diff: applying the hunks to examples/goal-file-baseline.json "
            "does not reproduce examples/goal-file.json — the diff is not a "
            "complete report of the change between the pair", rule=RULE_FAMILY_APPLY
        )

    # Every record in the family answers this same diff, so every record is
    # held to these rules — the reject is not a lesser fixture that may drift
    # while the accept stays honest. A record whose hashes no longer name the
    # pair is the §9.1 cross-check failing, whichever way its verdict went.
    derived = derive_ceremony_class(diff)
    for name, record in records.items():
        label = name.removesuffix(".json")
        if record.get("proposed_sha256") != diff.get("proposed_sha256"):
            fail(
                f"{label}: proposed_sha256 does not match the diff's",
                rule=RULE_FAMILY_HASH,
            )
        if "baseline_sha256" not in record:
            fail(
                f"{label}: no baseline_sha256, but a goal-diff exists — only "
                "first adoption has no baseline, and first adoption has no diff (§11)",
                rule=RULE_FAMILY_HASH,
            )
        elif record.get("baseline_sha256") != diff.get("baseline_sha256"):
            fail(
                f"{label}: baseline_sha256 does not match the diff's",
                rule=RULE_FAMILY_HASH,
            )

        if record.get("ceremony_class") != derived:
            fail(
                f"{label}: ceremony_class {record.get('ceremony_class')!r} is "
                f"asserted, but the validator derives {derived!r} from the diff",
                rule=RULE_FAMILY_CEREMONY,
            )

        check_refused_paths(diff, record, label)


def check_goal_file_forbidden_refs(schemas: dict[str, dict]) -> None:
    """goal-file.schema.json must restate, never `$ref`, the forbidden defs.

    A future edit that `$ref`s `contract_version` (or `domain_coverage` /
    `interlock`) silently readopts that def's default or optional field —
    exactly the second-spelling-of-one-meaning hazard the goal file exists
    to close (reconciliation §13, Grok 8.6; §15 C-1).
    """
    schema = schemas.get("goal-file.schema.json")
    if schema is None:
        return

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str):
                normalized = ref.split("/schema/")[-1]
                if normalized in GOAL_FILE_FORBIDDEN_REFS:
                    fail(
                        f"schema/goal-file.schema.json: $ref {ref!r} reuses a def "
                        "the goal file must restate instead of referencing",
                        rule=RULE_SCHEMA_META,
                    )
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(schema)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--schemas-only",
        action="store_true",
        help="check schema validity only; skip fixtures and cross-file rules",
    )
    args = parser.parse_args()

    schemas, registry = load_schemas()
    if not schemas:
        die("no schemas found in schema/")

    check_schemas_valid(schemas)
    check_goal_file_forbidden_refs(schemas)
    caught = byte_caught = projection_caught = 0
    if not args.schemas_only:
        check_pairing(schemas)
        check_family_canonical_bytes()
        loaded = load_happy_examples()
        validate_loaded(loaded, schemas, registry)
        if not findings:
            declared = read_declared_classes()
            caught = check_negative_fixtures(loaded, schemas, registry, declared)
            byte_caught = check_byte_class_fixtures(declared)
            projector = load_projector()
            if projector is not None:
                check_projector_golden(projector, loaded)
                check_projector_properties(projector, loaded)
                projection_caught = check_projection_fixtures(projector, declared)
            on_disk: set[str] = set()
            if BROKEN_DIR.is_dir():
                on_disk |= {p.name for p in BROKEN_DIR.iterdir() if p.is_dir()}
            if BYTE_CLASS_DIR.is_dir():
                on_disk |= {p.name for p in BYTE_CLASS_DIR.glob("*.json")}
            if PROJECTION_DIR.is_dir():
                on_disk |= {p.name for p in PROJECTION_DIR.glob("*.json")}
            check_declaration_coverage(declared, on_disk)
            check_class_coverage(declared)

    if findings:
        print(f"schema-lint: {len(findings)} finding(s)")
        return 1
    extra = f", {caught} negative fixtures" if caught else ""
    if byte_caught:
        extra += f", {byte_caught} byte-class fixtures"
    if projection_caught:
        extra += f", {projection_caught} projection fixtures"
    print(f"schema-lint: OK ({len(schemas)} schemas{extra})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
