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
  6. each of the fifty deliberately broken fixtures in examples/broken/
     and the five byte-class fixtures in examples/broken-bytes/ is caught.
     A lint that only accepts good input is not a check.

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
import json
import sys
import unicodedata
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import rfc8785
import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

REPO = Path(__file__).resolve().parent.parent
SCHEMA_DIR = REPO / "schema"
EXAMPLE_DIR = REPO / "examples"
BROKEN_DIR = EXAMPLE_DIR / "broken"
BYTE_CLASS_DIR = EXAMPLE_DIR / "broken-bytes"
EXPECTED_BROKEN = 50
EXPECTED_BYTE_CLASS = 5

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
}

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

findings: list[str] = []
PRINT_FINDINGS = True


def fail(msg: str) -> None:
    findings.append(msg)
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
    except ValueError as exc:
        fail(f"{label}: not canonical JSON: {exc}")
        return None

    for pointer in _non_nfc_strings(doc):
        fail(f"{label}: {pointer} is not NFC-normalized")

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
        fail(f"{label}: bytes are not their own JCS canonical form — {why}")
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


def check_byte_class_fixtures() -> int:
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
        fail("examples/broken-bytes/ is missing — the byte-class fixtures are gone")
        return 0
    cases = sorted(BYTE_CLASS_DIR.glob("*.json"))
    if len(cases) != EXPECTED_BYTE_CLASS:
        fail(
            f"examples/broken-bytes/: expected {EXPECTED_BYTE_CLASS} cases, "
            f"found {len(cases)}"
        )
    caught = 0
    for case in cases:
        label = f"examples/broken-bytes/{case.name}"
        with capture_findings(silent=True) as case_findings:
            check_canonical_bytes(case.read_bytes(), label)
        if case_findings:
            caught += 1
        else:
            fail(f"{label}: was not caught (the byte layer accepted it)")
    return caught


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
            fail(f"schema/{name} is not a valid JSON Schema 2020-12: {exc}")


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
            "only shared $defs"
        )
    for name in sorted(paired_schemas - on_disk_schemas):
        fail(f"EXAMPLES pairs against schema/{name}, which does not exist")
    for name in sorted(on_disk_examples - set(EXAMPLES)):
        fail(f"examples/{name} is paired with no schema — register it in EXAMPLES")
    for name in sorted(DEFINITION_ONLY_SCHEMAS - on_disk_schemas):
        fail(f"DEFINITION_ONLY_SCHEMAS names schema/{name}, which does not exist")
    for name in sorted(DEFINITION_ONLY_SCHEMAS & paired_schemas):
        fail(f"schema/{name} is both definition-only and paired with an example")


def validate(instance: Any, schema: dict, registry: Registry, label: str) -> None:
    validator = Draft202012Validator(
        schema, registry=registry, format_checker=FormatChecker()
    )
    for error in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        where = "/".join(str(p) for p in error.path) or "<root>"
        fail(f"{label}: {where}: {error.message}")


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
            f"{label}: row_type {row_type!r} is not one of {sorted(ROW_TYPES)}"
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
            fail(f"examples/{example_name} is missing — the schema has no fixture")
            continue
        loaded[example_name] = load_any(path)
    return loaded


def validate_loaded(
    loaded: dict[str, Any],
    schemas: dict[str, dict],
    registry: Registry,
    *,
    label_prefix: str = "examples",
    overlaid: frozenset[str] = frozenset(),
) -> None:
    for example_name, (schema_name, is_sequence) in EXAMPLES.items():
        if example_name not in loaded:
            continue
        data = loaded[example_name]
        schema = schemas.get(schema_name)
        label = f"{label_prefix}/{example_name}"
        if schema is None:
            fail(f"schema/{schema_name} is missing (needed by {label})")
            continue
        if is_sequence:
            if not isinstance(data, list):
                fail(f"{label}: expected a sequence of rows")
                continue
            for i, row in enumerate(data):
                validate_row(row, schema, registry, f"{label}[{i}]")
        else:
            validate(data, schema, registry, label)
    check_cross_file(loaded)
    for goal_file in GOAL_FILES:
        check_goal_file_cross_file(loaded, goal_file)
    # The family layer takes the goal-file pair as given and asks whether the
    # diff and the record describe IT. A negative case that rewrites the
    # proposed goal file is making a claim about goal-file.schema.json, and
    # the diff's now-inevitable disagreement would let that case pass on the
    # wrong rule — so the layer stands down exactly when the file it reads
    # from is the file under test. Measured, not assumed: run the family
    # layer over cases 13-43 without this and it fires on 31 of 31, which
    # would leave every §10 schema rule deletable without a red lint.
    # Deliberately asymmetric — an overlaid BASELINE does not stand it down,
    # because cases 52 and 53 need it live. A future schema negative written
    # as a broken baseline would be masked the same way 13-43 would have
    # been; write it against goal-file.json instead.
    if "goal-file.json" not in overlaid:
        check_goal_file_family(loaded)


def check_negative_fixtures(
    happy: dict[str, Any],
    schemas: dict[str, dict],
    registry: Registry,
) -> int:
    """Each examples/broken/<case>/ overlay must be rejected.

    Overlay files replace the happy-path document of the same name; the rest
    of the Site Model stays as in examples/. Silence on the expected failures
    — a negative fixture that the lint accepts is the finding.
    """
    if not BROKEN_DIR.is_dir():
        fail(f"examples/broken/ is missing — all {EXPECTED_BROKEN} negatives are gone")
        return 0
    cases = sorted(p for p in BROKEN_DIR.iterdir() if p.is_dir())
    if len(cases) != EXPECTED_BROKEN:
        fail(
            f"examples/broken/: expected {EXPECTED_BROKEN} cases, found {len(cases)}"
        )
    caught = 0
    for case in cases:
        overlays = sorted(case.glob("*.yml")) + sorted(case.glob("*.json"))
        if not overlays:
            fail(f"examples/broken/{case.name}: no overlay .yml/.json")
            continue
        loaded = {name: copy.deepcopy(doc) for name, doc in happy.items()}
        overlaid: set[str] = set()
        for overlay in overlays:
            if overlay.name not in EXAMPLES:
                fail(
                    f"examples/broken/{case.name}: {overlay.name} is not a Site Model file"
                )
                continue
            loaded[overlay.name] = load_any(overlay)
            overlaid.add(overlay.name)
        with capture_findings(silent=True) as case_findings:
            validate_loaded(
                loaded,
                schemas,
                registry,
                label_prefix=f"examples/broken/{case.name}",
                overlaid=frozenset(overlaid),
            )
        if case_findings:
            caught += 1
        else:
            fail(
                f"examples/broken/{case.name}: was not caught "
                "(lint accepted a deliberately broken fixture)"
            )
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
            fail(f"launchd-writers: prefix {prefix} declared twice — one writer per prefix")
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
                    "two writers over one label namespace"
                )

    # --- bundles -----------------------------------------------------------
    interlock_ids: set[str] = set()
    for bundle_name, bundle in bundles.items():
        domain = bundle.get("domain")
        if domain not in domains:
            fail(f"services: bundle {bundle_name} names unknown domain {domain!r}")
        for interlock in bundle.get("interlocks") or []:
            iid = interlock.get("id")
            if iid in interlock_ids:
                fail(f"services: interlock id {iid!r} declared twice")
            interlock_ids.add(iid)

    # --- services ----------------------------------------------------------
    names: set[str] = set()
    for service in services:
        name = service.get("name", "<unnamed>")
        if name in names:
            fail(f"services: service name {name!r} declared twice")
        names.add(name)

        if service.get("domain") not in domains:
            fail(f"services: {name} names unknown domain {service.get('domain')!r}")
        if service.get("bundle") not in bundles:
            fail(f"services: {name} names unknown bundle {service.get('bundle')!r}")

        role = service.get("role")
        if role is not None and role not in roles:
            fail(f"services: {name} names unknown role {role!r} (roles.yml)")

        label = (service.get("launchd") or {}).get("label")
        if label is not None:
            matched = [p for p in prefixes if label.startswith(p.removesuffix("*"))]
            if not matched:
                fail(
                    f"services: {name} launchd label {label!r} falls under no declared "
                    "writer prefix (launchd-writers.yml) — this is the two-writers rail"
                )

    for service in services:
        for target in service.get("depends_on") or []:
            if target not in names:
                fail(
                    f"services: {service.get('name')} depends_on unknown service {target!r}"
                )

    # --- roles -------------------------------------------------------------
    for role_name, role in (roles_doc.get("roles") or {}).items():
        main = role.get("main")
        backups = role.get("backups") or []
        peers = role.get("peers") or []
        if main in backups:
            fail(f"roles: {role_name} lists its main host {main!r} as its own backup")
        overlap = set(backups) & set(peers)
        if overlap:
            fail(
                f"roles: {role_name} lists {sorted(overlap)} as both backup and peer — "
                "a peer is explicitly not a candidate for main"
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
                fail(f"{label}: unit-writer prefix {prefix!r} declared twice")
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
                    f"bundle {bundle!r} is used by no present service"
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
                    "two writers over one namespace"
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
                    "applied to the goal file"
                )
            elif not any(w == "cfengine" for _, w in matched):
                fail(
                    f"{label}: domains/{domain_name}/entries/service/{service_id} "
                    "falls under a unit-writer prefix whose writer is not cfengine"
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
                        "hunks that do"
                    )
                    ok = False
                if "old" in hunk:
                    if bucket.get(entry_id) != hunk["old"]:
                        fail(f"{label}: {where} `old` is not the baseline's entry")
                        ok = False
                elif entry_id in bucket:
                    fail(
                        f"{label}: {where} has no `old`, so it is an add, but the "
                        "baseline already carries that entry"
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
                "on both sides — that is not a transition"
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
                f"{stated_old!r}, but the baseline has {actual_old!r}"
            )
            ok = False
        if change.get("new") == "undeclared":
            leftover = (domains.get(domain_name) or {}).get("entries") or {}
            if leftover:
                fail(
                    f"{label}: coverage_changes/{domain_name} retreats to "
                    "undeclared while its entries survive — a domain leaves the "
                    "map only once the hunks have deleted everything under it"
                )
                ok = False
            domains.pop(domain_name, None)
        elif domain_name in domains:
            domains[domain_name]["coverage"] = change.get("new")
        else:
            fail(
                f"{label}: coverage_changes/{domain_name} declares a domain no "
                "hunk populates — a declared domain with no entries is not a "
                "document the schema admits"
            )
            ok = False

    for domain_name, domain in domains.items():
        if "coverage" not in domain:
            fail(
                f"{label}: hunks create domain {domain_name} with no matching "
                "coverage_changes entry — its first appearance is unreviewed"
            )
            ok = False

    return result if ok else None


def check_goal_file_family(loaded: dict[str, Any]) -> None:
    """The four family fixtures must describe one another exactly.

    Each of these is a rule the running system holds and the fixture set
    would otherwise only gesture at: the two hashes are what §9.1's
    cross-check compares, applying the hunks is what makes the diff an
    honest report of the pair rather than prose beside it, and the ceremony
    class is derived, never taken on the approver's word (§11).
    """
    goal = loaded.get("goal-file.json")
    baseline = loaded.get("goal-file-baseline.json")
    diff = loaded.get("goal-diff.json")
    record = loaded.get("approval-record.json")
    if not all(isinstance(doc, dict) for doc in (goal, baseline, diff, record)):
        return

    goal_hash = canonical_sha256(goal)
    baseline_hash = canonical_sha256(baseline)

    if diff.get("baseline_sha256") != baseline_hash:
        fail(
            "goal-diff: baseline_sha256 is not H(examples/goal-file-baseline.json) "
            f"— expected {baseline_hash}"
        )
    if diff.get("proposed_sha256") != goal_hash:
        fail(
            "goal-diff: proposed_sha256 is not H(examples/goal-file.json) "
            f"— expected {goal_hash}"
        )

    # One host across the family. A record signed for one device against a
    # diff computed for another is DC-2's per-target validity, defeated.
    hosts = {name: loaded[name].get("host") for name in EXAMPLES if name.endswith(".json")}
    if len(set(hosts.values())) > 1:
        fail(f"goal-file family: fixtures disagree on host: {hosts}")

    applied = apply_diff(baseline, diff, "goal-diff")
    if applied is not None and rfc8785.dumps(applied) != rfc8785.dumps(goal):
        fail(
            "goal-diff: applying the hunks to examples/goal-file-baseline.json "
            "does not reproduce examples/goal-file.json — the diff is not a "
            "complete report of the change between the pair"
        )

    if record.get("proposed_sha256") != diff.get("proposed_sha256"):
        fail("approval-record: proposed_sha256 does not match the diff's")
    if "baseline_sha256" not in record:
        fail(
            "approval-record: no baseline_sha256, but a goal-diff exists — only "
            "first adoption has no baseline, and first adoption has no diff (§11)"
        )
    elif record.get("baseline_sha256") != diff.get("baseline_sha256"):
        fail("approval-record: baseline_sha256 does not match the diff's")

    derived = derive_ceremony_class(diff)
    if record.get("ceremony_class") != derived:
        fail(
            f"approval-record: ceremony_class {record.get('ceremony_class')!r} is "
            f"asserted, but the validator derives {derived!r} from the diff"
        )


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
                        "the goal file must restate instead of referencing"
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
    caught = byte_caught = 0
    if not args.schemas_only:
        check_pairing(schemas)
        check_family_canonical_bytes()
        loaded = load_happy_examples()
        validate_loaded(loaded, schemas, registry)
        if not findings:
            caught = check_negative_fixtures(loaded, schemas, registry)
            byte_caught = check_byte_class_fixtures()

    if findings:
        print(f"schema-lint: {len(findings)} finding(s)")
        return 1
    extra = f", {caught} negative fixtures" if caught else ""
    if byte_caught:
        extra += f", {byte_caught} byte-class fixtures"
    print(f"schema-lint: OK ({len(schemas)} schemas{extra})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
