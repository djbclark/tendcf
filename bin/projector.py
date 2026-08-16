#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["rfc8785"]
# ///
r"""Project a goal file into `host_specific.json` — the reference projector.

The mapping this implements was decided in
`docs/architecture/projector-reconciliation-2026-08-16.md`, whose P-1..P-7
are the specification and whose §8 golden is the oracle. Nothing here is a
design decision; where a choice looks arbitrary the reason is in that
document, cited by clause.

WHY THIS FILE EXISTS AT ALL. The projector runs device-side, inside
tendcf-agent, after approval — and tendcf-agent does not exist. This repo is
contract-only, so §13's "CI invokes the agent's own projector" has nothing to
invoke. This is the normative implementation that gate runs today and that
tendcf-agent must reproduce byte-for-byte when it is written (R22). That
makes this a second implementation site, which is a real cost carried
knowingly: two implementations can drift. `examples/host_specific.json` is
the shared oracle, and drift is exactly what a byte comparison catches.

WHAT PROJECTS, AND WHY SO LITTLE. `supervision`'s `service` and `interlock`
entries, and nothing else — not `device-trust`, not `unit-writer`, not
`coverage`, not `host`, not `schema_version` (P-1). The filter is structural:
it keys on domain class and kind, positions whose vocabularies are closed and
disjoint in `goal-file.schema.json`, never on an entry's values. That
distinction is R21's tripwire, and N-1 makes it mechanical.

The exclusion of `device-trust` is not tidiness. On CFEngine 3.27.1 every
projected byte lands at `data:variables.<key>` (E-1), readable by every
bundle and dumped by `cf-promises --show-vars`; projecting the trust domain
would publish the advisor public key, the consent tier, the agent binary pin
and the policy-tree digest into the mutation engine's readable namespace,
creating a second read path for the one region
`goal-file.schema.json:232` reserves to the validator and agent.

WHY CONTAINERS AND NOT FLAT KEYS. Measurement, not taste (P-2). A dotted flat
key is parsed as a scope path — `com.tendcf.caddy.main` would install as
scope `com` (E-3) — and entry ids are reverse-DNS by construction, so this is
every service rather than a corner case. Booleans and integers also survive
typed only inside a container (E-4); flat, `keep_alive: true` and
`expect_exit: 0` would silently stringify. Ids are copied verbatim, never
canonified: the id is the promiser and the launchd label, and rewriting it
would be a second spelling of identity.

WHY TOMBSTONES STAY PUT. An entry with `state: "absent"` sits in its kind
container like any other entry, with its `state` copied (P-3, C-1). There
is no parallel absent-list and nothing is dropped for being absent: dropping
it would mean "stop managing" where the goal file says "converge to absent",
which in a comprehensive domain leaves a removal with no actuated path. The
`.cf` policy renders the negative promise from `state` at evaluation time;
the projector does not branch on it.

WHY THE BYTES ARE THE CONTRACT. Output is `rfc8785.dumps` — JCS, RFC 8785 —
with no trailing newline (P-6.1, P-6.2), matching `examples/goal-file.json`'s
§13 exemption from the newline-at-EOF convention. `json.dumps(sort_keys=True)`
is not a substitute: it agrees on member order and on nothing else. `project()`
is a pure function of the goal-file document — no clock, no environment, no
filesystem, no subprocess — so two runs over identical input are identical
bytes (N-11), which is the only reason a golden can be an oracle.

`validate_projection()` is the other half, and it is deliberately NOT a
checker for what this projector produces. It takes arbitrary projection bytes
and enforces the reconciliation's N-series against them, which is what makes
those negatives testable by hand-written bad projections that no projector
would ever emit. `project()` runs it over its own output before returning, so
a mapping bug becomes a refusal rather than a file on a device.

Two limits of that checker, stated here rather than discovered later:

  - N-5 is enforced as "no container but the two, and no object key spelled
    like a digest". Trust content pasted into a *value* inside an otherwise
    legal service body is not distinguishable from legitimate content without
    re-reading the schema, which these bytes do not carry.
  - N-9 is enforced by id shape, and shape only catches what no goal file
    could spell. Interlock ids are kebab, so canonification (`_`) is visible;
    the service-id pattern admits `_`, so a canonified service id is NOT
    visible in projection bytes alone. The lint closes that half by checking
    the corpus goal file's ids round-trip through `project()`.

The id patterns below restate `goal-file.schema.json`'s, which is a second
spelling and is accepted as one: a projection carries no schema and no goal
file, and an on-device checker will not have either. The restatement is
narrow (two patterns and two lengths) and drift in it can only make the
checker weaker than the schema, never stricter than the goal file it came
from. That weakness was real and not hypothetical: the patterns were first
written with `$`, which in Python also matches before a trailing newline
while JSON Schema's ECMA-262 `$` does not, so an id ending in `\n` passed
(F5). Fixed to `\Z` and fixtured three times over, once per pattern, since
a revert of any one of them alone is otherwise invisible.

Run it:  bin/projector.py examples/goal-file.json
         bin/projector.py --check examples/host_specific.json
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, NamedTuple

import rfc8785

# P-1: the one domain and the two kinds that project. A future kind decides
# whether it projects at schema-authoring time, in the open, by editing this
# tuple — that editorial surface is the accepted price of not shipping an
# interpreter (reconciliation §1).
PROJECTING_DOMAIN = "supervision"
PROJECTING_KINDS = ("service", "interlock")

# P-2: the only synthesised token in the output. The kind is lowercased with
# `-` -> `_` as convention ONLY: hyphens are legal in a `vars` key on 3.27.1
# and expand correctly (R23). The rule is vacuous today — neither projecting
# kind has a hyphen — and exists so a future hyphenated kind does not have to
# relitigate it. Do not re-derive a mechanical justification for it.
CONTAINER_PREFIX = "tendcf_"

# E-9: `HOST_SPECIFIC_DATA_MAX_SIZE` in libpromises/cmdb.c:38. A file past it
# is truncated on read and then fails to parse — a hard load failure, not a
# warning, and not per-key.
MAX_PROJECTION_BYTES = 5 * 1024 * 1024

# E-5: one of these anywhere in `vars` fails the ENTIRE CMDB load, not merely
# the key carrying it (var_expressions.h:90-97, cmdb.c:182). That is why N-3
# is a refusal and not a lint style rule.
EXPANSION_SEQUENCES = ("$(", "${", "@(", "@{")

# The two rule classes this module's checker can emit. `bin/schema_lint.py`
# imports them, so the vocabulary has one spelling: the byte class is what is
# measurable without understanding the mapping (canonical form, parse,
# size), the other is the mapping's own invariants.
RULE_PROJECTION = "projection"
RULE_PROJECTION_BYTES = "projection bytes"

# Restated from goal-file.schema.json — see the module docstring's last
# paragraph for why that is deliberate here and nowhere else.
#
# `\Z`, NOT `$`. JSON Schema `pattern` is ECMA-262, where `$` without the `m`
# flag matches end-of-input and nothing else; Python's `$` also matches just
# before a final `\n`. F5: that difference made N-9 evadable — an interlock id
# "caddy-config-valid\n", a promiser and launchd label no goal file can spell,
# was accepted. `\Z` is the faithful restatement of the schema's `$`.
ENTRY_ID_PATTERNS = {
    "service": re.compile(r"^[A-Za-z0-9][A-Za-z0-9@._-]*\Z"),
    "interlock": re.compile(r"^[a-z0-9][a-z0-9-]*\Z"),
}
ENTRY_ID_MAX_LENGTH = {"service": 128, "interlock": 64}

# common.schema.json's env_map: key and value are both secretspec key NAMES.
# A value outside this class is a resolved secret, which is the whole of N-4.
# `\Z` for the same reason as above, and it matters more here: `$` admitted a
# value ending in a newline, which is a value and not a name.
SECRETSPEC_NAME = re.compile(r"^[A-Z][A-Z0-9_]*\Z")

# device-trust's ids and digests are key-position in the goal file: an
# `ed25519:` advisor-key id, a `sha256:` digest. A key spelled this way in a
# projection is trust content that reached `vars` (N-5).
TRUST_SHAPED_KEY = re.compile(r"^(ed25519|sha256):")


class ProjectionRefused(Exception):
    """`project()` will not emit these bytes, and says why.

    Refusal rather than normalisation is the rule the reconciliation states
    twice: a duplicate id across kinds is refused instead of resolved
    last-wins (P-6.7), and a non-conforming input is refused instead of
    laundered into a conforming one (P-6.6). Both would otherwise be an
    interpreter making a decision nobody wrote down.
    """


class ProjectionFinding(NamedTuple):
    rule: str
    msg: str


def container_name(kind: str) -> str:
    """The `vars` key a kind projects into (P-2)."""
    return CONTAINER_PREFIX + kind.lower().replace("-", "_")


# container name -> kind, the closed set P-2 fixes.
CONTAINERS = {container_name(kind): kind for kind in PROJECTING_KINDS}


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """`object_pairs_hook` refusing I-JSON's silent last-wins.

    Deliberately a copy of `bin/schema_lint.py`'s, not an import of it: this
    module is the thing tendcf-agent reproduces, and it may not depend on the
    repo's linter to be correct.
    """
    seen: set[str] = set()
    for key, _ in pairs:
        if key in seen:
            raise ValueError(f"duplicate key {key!r}")
        seen.add(key)
    return dict(pairs)


def _walk(node: Any, path: str = "") -> Any:
    """Yield `(pointer, value)` for every node, keys included as values.

    Keys are yielded as their own nodes because three of the checks below —
    expansion sequences, NFC, trust-shaped keys — are about strings wherever
    they sit, and a key is where two of the three actually appear.
    """
    yield path or "<root>", node
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{path}/{key}" if path else key
            yield f"{here} (key)", key
            yield from _walk(value, here)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _walk(value, f"{path}/{i}" if path else str(i))


def project(goal_file: dict) -> bytes:
    """The goal file's supervision entries as `host_specific.json` bytes.

    Pure: the only input is the document, and the only output is bytes. The
    result is checked against `check_projection()` before it is returned, so
    the projector cannot emit a projection the negatives forbid — a mapping
    bug surfaces here as a refusal instead of on a device as a silently
    disabled CMDB load.
    """
    if not isinstance(goal_file, dict):
        raise ProjectionRefused("goal file is not a JSON object")

    domains = goal_file.get("domains")
    if domains is not None and not isinstance(domains, dict):
        raise ProjectionRefused("domains is not an object")
    domain = (domains or {}).get(PROJECTING_DOMAIN)
    if domain is not None and not isinstance(domain, dict):
        raise ProjectionRefused(f"domains/{PROJECTING_DOMAIN} is not an object")
    entries = (domain or {}).get("entries")
    if entries is not None and not isinstance(entries, dict):
        raise ProjectionRefused(f"domains/{PROJECTING_DOMAIN}/entries is not an object")
    entries = entries or {}

    containers: dict[str, dict[str, Any]] = {}
    # P-6.7: an id in two projecting kinds is refused, never last-wins. The
    # two containers are one id space because CFEngine's addressing makes
    # them one: `getindices()` over either returns the same string.
    origin: dict[str, str] = {}

    for kind in PROJECTING_KINDS:
        bucket = entries.get(kind)
        if bucket is None:
            continue
        if not isinstance(bucket, dict):
            raise ProjectionRefused(
                f"domains/{PROJECTING_DOMAIN}/entries/{kind} is not an object"
            )
        if not bucket:
            # P-6.4: omission is the goal file's own spelling of "none"; an
            # empty container would be a second one.
            continue
        name = container_name(kind)
        container: dict[str, Any] = {}
        for entry_id, body in bucket.items():
            if not isinstance(body, dict):
                raise ProjectionRefused(
                    f"domains/{PROJECTING_DOMAIN}/entries/{kind}/{entry_id} "
                    "is not an object"
                )
            prior = origin.get(entry_id)
            if prior is not None:
                raise ProjectionRefused(
                    f"entry id {entry_id!r} appears in both {prior} and {kind} — "
                    "refused rather than resolved last-wins (P-6.7)"
                )
            origin[entry_id] = kind
            # P-2/P-6.5: the body verbatim, id not canonified, nothing
            # reordered or renumbered. Deep-copied so the returned bytes can
            # never depend on a later mutation of the caller's document.
            container[entry_id] = copy.deepcopy(body)
        containers[name] = container

    # P-6.3: `vars` is always present, even with no container under it.
    # Same F1 hazard as in check_projection(): the goal file is copied
    # verbatim, so a value JCS cannot represent reaches here intact, and an
    # uncaught FloatDomainError device-side is not the refusal this
    # docstring promises.
    try:
        raw = rfc8785.dumps({"vars": containers})
    except Exception as exc:  # noqa: BLE001 - rfc8785 raises several types
        raise ProjectionRefused(
            f"the goal file carries a value JCS cannot represent: "
            f"{type(exc).__name__}: {exc} (N-6, P-6.1)"
        ) from exc

    refusals = check_projection(raw)
    if refusals:
        raise ProjectionRefused(
            "the projection this goal file produces violates the mapping: "
            + "; ".join(f"{f.rule}: {f.msg}" for f in refusals)
        )
    return raw


def check_projection(raw: bytes) -> list[ProjectionFinding]:
    """Every N-series violation in `raw`, each under the class that found it.

    Takes ARBITRARY bytes rather than a document this projector produced.
    That is the whole point: a negative is testable only if a hand-written
    bad projection — one no correct projector would emit — can be handed to
    the same checker CI runs over the real thing.
    """
    found: list[ProjectionFinding] = []

    def flag(rule: str, msg: str) -> None:
        found.append(ProjectionFinding(rule, msg))

    # --- the byte layer, before the parse ---------------------------------
    if len(raw) > MAX_PROJECTION_BYTES:
        flag(
            RULE_PROJECTION_BYTES,
            f"{len(raw)} bytes exceeds the {MAX_PROJECTION_BYTES}-byte "
            "host_specific.json limit — CFEngine truncates the read and the "
            "whole CMDB load then fails (N-8, E-9)",
        )

    try:
        doc = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        flag(RULE_PROJECTION_BYTES, f"not JSON: {exc}")
        return found
    except ValueError as exc:  # _reject_duplicate_keys
        flag(RULE_PROJECTION_BYTES, f"not canonical JSON: {exc}")
        return found

    # F1: `json` accepts several things JCS cannot represent — NaN, Infinity,
    # 1e999, integers outside the IEEE-754 double domain, lone surrogates —
    # and rfc8785 raises on every one. Raising here would break two contracts
    # at once: this function is documented to RETURN findings, and
    # bin/schema_lint.py calls it in a loop, so one such fixture aborted the
    # whole lint before the coverage checks ran. Un-canonicalizable bytes are
    # a refusal like any other, not a crash.
    try:
        canonical = rfc8785.dumps(doc)
    except Exception as exc:  # noqa: BLE001 - rfc8785 raises several types
        flag(
            RULE_PROJECTION_BYTES,
            f"not representable in JCS: {type(exc).__name__}: {exc}. "
            "`json` accepts NaN, Infinity, oversized integers and lone "
            "surrogates; JCS represents none of them, so bytes carrying one "
            "can never be a projection (N-6, P-6.1)",
        )
        return found
    if canonical != raw:
        why = (
            "leading or trailing whitespace, which JCS emits neither of"
            if raw.strip() != raw
            else "member order, insignificant whitespace, or a number "
            "spelling JCS collapses"
        )
        flag(
            RULE_PROJECTION_BYTES,
            f"bytes are not their own JCS canonical form — {why}. The bytes "
            "are the contract, so a projection that merely parses to the "
            "right document is still the wrong file (N-6, P-6.1)",
        )

    # --- the mapping ------------------------------------------------------
    if not isinstance(doc, dict):
        flag(RULE_PROJECTION, "top level is not an object — a projection is "
             "`{\"vars\": {…}}` and nothing else")
        return found

    for key in doc:
        if key == "vars":
            continue
        extra = ""
        if key in ("variables", "classes"):
            # E-6/E-7: these are LEGAL to CFEngine, which is exactly why the
            # negative exists — `variables` loads after `vars` and overwrites
            # the same name, so a checker that only asks "is `vars` right?"
            # never sees the document that replaced it.
            extra = (
                " — legal to CFEngine, loaded after `vars` and overwriting the "
                "same names, which is why envelope-shape checking misses it"
            )
        flag(
            RULE_PROJECTION,
            f"top-level key {key!r} beside `vars`{extra} (N-2)",
        )

    if "vars" not in doc:
        flag(
            RULE_PROJECTION,
            "no top-level `vars` — it is always present, even with every "
            "container empty (P-6.3)",
        )
        return found

    containers = doc["vars"]
    if not isinstance(containers, dict):
        flag(RULE_PROJECTION, "vars is not an object")
        return found

    origin: dict[str, str] = {}
    for name, container in containers.items():
        if name not in CONTAINERS:
            flag(
                RULE_PROJECTION,
                f"vars/{name} names no projecting kind — only "
                f"{', '.join(sorted(CONTAINERS))} project. device-trust, "
                "unit-writer, coverage, host and schema_version do not, and a "
                "verbatim copy of the goal file under `vars` is the shape that "
                "passes a naive `vars`-only check (N-5, N-12, P-1)",
            )
            continue
        kind = CONTAINERS[name]
        if not isinstance(container, dict):
            flag(RULE_PROJECTION, f"vars/{name} is not an object")
            continue
        if not container:
            flag(
                RULE_PROJECTION,
                f"vars/{name} is empty — a kind container with no entries is "
                "omitted entirely, because omission is already the goal "
                "file's spelling of none (P-6.4)",
            )
            continue
        for entry_id, body in container.items():
            where = f"vars/{name}/{entry_id}"
            if not ENTRY_ID_PATTERNS[kind].match(entry_id) or len(
                entry_id
            ) > ENTRY_ID_MAX_LENGTH[kind]:
                flag(
                    RULE_PROJECTION,
                    f"{where}: no goal file can spell this {kind} id, so it has "
                    "been canonified, truncated or otherwise rewritten. The id "
                    "is the promiser and the launchd label; a second spelling "
                    "of it is a second identity (N-9)",
                )
            prior = origin.get(entry_id)
            if prior is not None:
                flag(
                    RULE_PROJECTION,
                    f"{where}: entry id also appears in {prior} — one id space "
                    "across the projecting kinds, and a collision is refused "
                    "rather than resolved last-wins (N-10, P-6.7)",
                )
            else:
                origin[entry_id] = name
            if not isinstance(body, dict):
                flag(RULE_PROJECTION, f"{where}: entry body is not an object")
                continue
            env = body.get("env")
            # F2: this guard used to be the whole check, so an `env` that was
            # not a dict skipped N-4 entirely — and `project()` copies bodies
            # verbatim without schema-validating them, so
            # `env: ["TOKEN=<real secret>"]` reached the output bytes with
            # ZERO findings. The schema forbids that shape, but N-4 exists
            # precisely for the case where something upstream did not hold,
            # and a check that only runs on well-formed input is not a check.
            if env is not None and not isinstance(env, dict):
                flag(
                    RULE_PROJECTION,
                    f"{where}/env: {type(env).__name__}, not an object of "
                    "NAME -> secretspec-key-NAME. Any other shape is refused "
                    "rather than skipped: skipping it is how a resolved "
                    "secret reaches $(sys.workdir)/data/ unnoticed (N-4, P-4)",
                )
            if isinstance(env, dict):
                for env_key, env_value in env.items():
                    if SECRETSPEC_NAME.match(env_key) and isinstance(
                        env_value, str
                    ) and SECRETSPEC_NAME.match(env_value):
                        continue
                    flag(
                        RULE_PROJECTION,
                        f"{where}/env/{env_key}: {env_value!r} is not a "
                        "secretspec key NAME. env carries names, never values "
                        "and never a reference: the projector has no resolver "
                        "and no call site for one (N-4, P-4)",
                    )

    # --- string-shaped hazards, wherever they sit -------------------------
    for pointer, node in _walk(doc):
        if isinstance(node, bool):
            continue
        if isinstance(node, float):
            flag(
                RULE_PROJECTION,
                f"{pointer}: {node!r} is a float. The goal file admits none "
                "(its only numerics are integers), and CFEngine installs a "
                "float as a string — 3.5 arrives as \"3.50\" (N-7, E-8)",
            )
            continue
        if not isinstance(node, str):
            continue
        if not unicodedata.is_normalized("NFC", node):
            flag(
                RULE_PROJECTION_BYTES,
                f"{pointer} is not NFC-normalized. JCS takes NFC as an input "
                "precondition and passes anything else straight through, so "
                "canonicalization cannot see this class at all (N-6)",
            )
        for sequence in EXPANSION_SEQUENCES:
            if sequence in node:
                flag(
                    RULE_PROJECTION,
                    f"{pointer}: contains {sequence!r}. One occurrence "
                    "anywhere in `vars` fails the ENTIRE CMDB load — not that "
                    "key, every projected variable on the host (N-3, E-5)",
                )
                break
        if pointer.endswith(" (key)") and TRUST_SHAPED_KEY.match(node):
            flag(
                RULE_PROJECTION,
                f"{pointer}: a device-trust digest or key id. Every projected "
                "byte is readable by every bundle and dumped by --show-vars, "
                "so trust content here is a second read path for the one "
                "region the validator and agent read alone (N-5, P-1, E-1)",
            )

    return found


def validate_projection(raw: bytes) -> list[str]:
    """The N-series findings against `raw`, as strings. Empty means OK.

    The string form is the public contract; `check_projection()` is the same
    check with the rule class kept, which is what the lint needs to hold a
    fixture to the rule it declares.
    """
    return [f"{finding.rule}: {finding.msg}" for finding in check_projection(raw)]


def load_goal_file(path: Path) -> Any:
    return json.loads(path.read_bytes(), object_pairs_hook=_reject_duplicate_keys)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", help="a goal file, or a projection with --check")
    parser.add_argument(
        "--check",
        action="store_true",
        help="treat PATH as a projection and print the N-series findings "
        "against it instead of projecting a goal file",
    )
    args = parser.parse_args()

    path = Path(args.path)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        print(f"projector: ERROR: cannot read {path}: {exc}", file=sys.stderr)
        return 2

    if args.check:
        findings = validate_projection(raw)
        for finding in findings:
            print(f"projector: FAIL: {finding}")
        if findings:
            print(f"projector: {len(findings)} finding(s)")
            return 1
        print(f"projector: OK ({len(raw)} bytes)")
        return 0

    try:
        goal_file = load_goal_file(path)
    except ValueError as exc:
        print(f"projector: ERROR: {path} is not canonical JSON: {exc}", file=sys.stderr)
        return 2
    try:
        # No trailing newline: the bytes are the contract (P-6.2), so a shell
        # redirect of this output is the file, not a file that needs trimming.
        sys.stdout.buffer.write(project(goal_file))
    except ProjectionRefused as exc:
        print(f"projector: REFUSED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
