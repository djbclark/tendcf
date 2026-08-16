#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "jsonschema>=4.21", "rfc3339-validator"]
# ///
"""Lint the tendcf Site Model and goal-file contracts.

Five layers, cheapest first:

  1. every schema/*.schema.json is itself a valid JSON Schema 2020-12;
  2. every schema is paired with an example and every example with a
     schema, derived from the filesystem — a new schema with no fixture
     is a finding, not a convention someone has to remember. Examples are
     bilingual: `.yml` for the Site Model, `.json` for the goal-file
     family, whose canonical form IS JSON (reconciliation §13);
  3. every happy-path examples/*.{yml,json} instance validates against its
     schema;
  4. cross-file rules JSON Schema cannot express on its own — domain and
     bundle references resolve, service names are unique, launchd labels
     fall under a declared writer prefix, no writer prefix nests inside
     another; on the goal-file side, every interlock's bundle is used by
     at least one service, comprehensive-domain services fall under a
     `cfengine`-writer unit-writer prefix, and goal-file.schema.json
     itself never `$ref`s a def whose defaults would reintroduce
     ignore-unknown (reconciliation §13, Grok 8.6);
  5. each of the forty-three deliberately broken fixtures in
     examples/broken/ is caught. A lint that only accepts good input is
     not a check.

Layer 4 is the point. Layers 1-3 catch a broken or unpaired schema; layer
4 is what keeps a valid-but-wrong Site Model out of a render (map §0 rule
6: prefer machine-checkable to conventional). Layer 5 is why we believe
layer 4.

What this does NOT yet do (reconciliation §18 item 5, not built here):
the byte-class fixture mechanism (raw-byte comparison before parsing, for
canonicalization violations like non-NFC strings or a `15.0` spelling of
`15`), JCS idempotence checking, and projector-goldens — the last needs
an actual projector implementation, which does not exist yet.

Exit 0 clean, 1 findings, 2 cannot read/parse.
Run from repo root:  bin/schema_lint.py
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

REPO = Path(__file__).resolve().parent.parent
SCHEMA_DIR = REPO / "schema"
EXAMPLE_DIR = REPO / "examples"
BROKEN_DIR = EXAMPLE_DIR / "broken"
EXPECTED_BROKEN = 43

# example file -> schema file. report-rows.yml is a sequence of rows, each
# validated individually against the row schema. goal-file.json is JSON
# because that IS the goal file's canonical wire form (reconciliation §13);
# everything else here is YAML authoring shape.
EXAMPLES: dict[str, tuple[str, bool]] = {
    "services.yml": ("services.schema.json", False),
    "roles.yml": ("roles.schema.json", False),
    "launchd-writers.yml": ("launchd-writers.schema.json", False),
    "report-rows.yml": ("report-row.schema.json", True),
    "goal-file.json": ("goal-file.schema.json", False),
    "goal-diff.json": ("goal-diff.schema.json", False),
    "approval-record.json": ("approval-record.schema.json", False),
}

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
    check_goal_file_cross_file(loaded)


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
        fail("examples/broken/ is missing — the twelve negative fixtures are gone")
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
        for overlay in overlays:
            if overlay.name not in EXAMPLES:
                fail(
                    f"examples/broken/{case.name}: {overlay.name} is not a Site Model file"
                )
                continue
            loaded[overlay.name] = load_any(overlay)
        with capture_findings(silent=True) as case_findings:
            validate_loaded(
                loaded, schemas, registry, label_prefix=f"examples/broken/{case.name}"
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


def check_goal_file_cross_file(loaded: dict[str, Any]) -> None:
    """Cross-entry rules goal-file.schema.json cannot express alone.

    The goal file has no separate Site Model to check against — domain,
    bundle, and writer-prefix facts all live inside the one document, at
    its map-of-maps shape, so this mirrors check_cross_file()'s Site
    Model rules rather than sharing code with it (reconciliation §13).
    """
    goal_file = loaded.get("goal-file.json")
    if not isinstance(goal_file, dict):
        return
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
                fail(f"goal-file: unit-writer prefix {prefix!r} declared twice")
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
                    f"goal-file: domains/{domain_name}/entries/interlock/{interlock_id} "
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
                    f"goal-file: unit-writer prefix {inner!r} nests inside {outer!r} — "
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
                    f"goal-file: domains/{domain_name}/entries/service/{service_id} "
                    "falls under no declared unit-writer prefix — the two-writers rail, "
                    "applied to the goal file"
                )
            elif not any(w == "cfengine" for _, w in matched):
                fail(
                    f"goal-file: domains/{domain_name}/entries/service/{service_id} "
                    "falls under a unit-writer prefix whose writer is not cfengine"
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
    caught = 0
    if not args.schemas_only:
        check_pairing(schemas)
        loaded = load_happy_examples()
        validate_loaded(loaded, schemas, registry)
        if not findings:
            caught = check_negative_fixtures(loaded, schemas, registry)

    if findings:
        print(f"schema-lint: {len(findings)} finding(s)")
        return 1
    extra = f", {caught} negative fixtures" if caught else ""
    print(f"schema-lint: OK ({len(schemas)} schemas{extra})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
