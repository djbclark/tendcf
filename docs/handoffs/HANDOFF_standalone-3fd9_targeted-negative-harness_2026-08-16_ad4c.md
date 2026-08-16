---
schema_version: 1
handoff_id: ad4c
parent_handoff_ids: [0b22]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 953b2ad6a55acdcebae8654482a0a0c0a6677498
created_at: 2026-08-16T00:22:30-0400
writer: claude-code
---

# Handoff — the targeted negative harness

## The Goal

Resumed via `/baton` from `0b22`, which closed reconciliation §18 item 5
and explicitly left no forced next action — its "Where We're Going" listed
four carried items and said to pick one with the operator. The operator
picked **"Both, in that order"**: the reject-fixture debt first, then the
targeted negative harness. Mid-session they approved a third piece — the
`refused`-path rule plus a fixture for every rule class.

All three landed. §18 remains closed except projector goldens, which are
still blocked on a projector that does not exist.

## Where We Are

Clean tree, `master` at `953b2ad`, pushed. Three commits:

- `eeef627` — "schema: close the refused-iff-reject branch, both
  directions". 6 files.
- `dddd31b` — "schema: make the negative harness targeted, and drop the
  overlaid gate". 7 files, `bin/schema_lint.py` +453/-103.
- `953b2ad` — "schema: require refused paths to resolve, and give every
  class a fixture". 10 files.

`uv run bin/schema_lint.py` → `schema-lint: OK (8 schemas, 59 negative
fixtures, 6 byte-class fixtures)`. `python3 bin/xref_lint.py | grep -vE
'reviews/|deprecated/|handoffs/'` → the same 3 pre-existing findings named
in `0b22`, `7b18` and `4a48`, confirmed unchanged.

### What landed, in the shape the code now has

**A second positive approval record.** `examples/approval-record-reject.json`
is a **valid** record answering the same ceremony as
`examples/approval-record.json`: same `host`, `nonce`, `approval_seq`, and
both hashes, differing in `verdict`, `refused`, and `signature` and in
nothing else. §11 requires a reject-with-annotations fixture and one accept
record cannot supply it — `refused` is present iff the verdict is reject,
so the happy path could only ever exercise one side of the rule it states.
The shared nonce and counter are deliberate: these are the two possible
answers to one device challenge, not two records a validator would persist
in sequence, so the pair is a controlled comparison. `APPROVAL_RECORDS` is
the tuple; the family layer loops over it.

**Rule classes on every finding.** `fail(msg, *, rule)` — keyword-only and
required, so a new check cannot be added without deciding its class. A
`Finding` NamedTuple replaces the bare string list. `RULE_CLASSES` holds
fourteen tokens; `DETAILED_RULE_HEADS = {"family"}` is what makes
`family (hash)` / `family (apply)` / `family (ceremony)` three distinct
classes rather than one.

**The README is executable.** `read_declared_classes()` parses
`examples/broken/README.md`'s tables with `_README_ROW` and returns
`{case_name: rule_class}`. `check_declared_class()` requires the declared
class to be among those that fired. `check_declaration_coverage()` catches
a row naming no fixture; the per-case lookup catches a fixture with no row.
`check_class_coverage()` asks it from the other end — every class needs a
case, or an entry in `CLASSES_WITHOUT_FIXTURES` — and that exemption list
is itself checked for minimality.

**The `overlaid` gate is deleted.** `validate_loaded()` no longer takes
`overlaid`, and `check_goal_file_family(loaded)` runs unconditionally.

**The `refused` rule.** `check_refused_paths()` requires every annotation
to resolve to `hunks/<domain>/<kind>/<id>` or `coverage_changes/<domain>`.
The id is `path.split("/", 3)[3]`, i.e. the remainder, so an id carrying a
`/` still addresses correctly.

**Eight new fixtures** (58–65) plus the five reject-record mirrors, and
`schema/approval-record.schema.json`'s `else` branch respelled.

## What We Tried

Chronological, including the things that did not work.

1. **First `fail()`-tagging script inserted at the wrong offset.** The
   plan was to append `, rule=RULE_X` after the last argument of each
   `fail()` call, using `ast` end positions. It produced garbage like
   `\n, rule=RULE_JCS    return doc`. **Why:** f-string (`JoinedStr`)
   `end_lineno`/`end_col_offset` are unreliable before Python 3.12, and
   nearly every `fail()` argument is an f-string. Reverted with
   `git checkout` and rewrote to insert relative to the **Call** node's own
   closing paren, walking backwards over whitespace so a trailing comma is
   respected.

2. **Second script asserted on the wrong unit.** `assert src[close] == ")"`
   failed at line 251 with `'ical form — {why}")'`. **Why:** `ast`
   `col_offset` is a **UTF-8 byte** offset, not a character offset, and
   that line contains an em dash. Fixed by doing all offset arithmetic on
   `src.encode()` and writing back with `write_bytes`.

3. **Believed the lint's first green run.** After wiring the declared-class
   assertion the lint passed immediately, which was not evidence of
   anything — an empty `declared` dict would have failed loudly, but a
   regex matching the wrong column would not. Verified by printing all 57
   parsed declarations and every case's actual fired classes before
   trusting it, then by four mutations.

4. **Assumed my own item-1 change was side-effect free.** It was not.
   Holding **both** records to the family layer cost cases 49, 51, 52, 53
   and 54 the exactly-one-finding property the previous session had
   measured and recorded in the README. Caught by measuring against a
   detached worktree at `ea5dafb` (`git worktree add --detach old-wt
   ea5dafb`) rather than assuming the property still held. Fixed the
   **fixtures**, not the claim.

5. **Case 64's first draft was case 36 in disguise.** Wrote
   `writer: launchd` to mean "a writer that is not cfengine". `launchd` is
   not in the writer enum (`cfengine`, `mise`, `nix-darwin`, `homebrew`,
   `apple`, `third-party`), so the fixture fired a `schema` finding and the
   goal cross-file rule it claimed to test could have been deleted with the
   case still red. Rewritten with `homebrew`.

6. **Case 65's first draft was unrepresentable.** Put the duplicate
   unit-writer prefix under `device-trust`, which is a `trust_domain` and
   admits no `unit-writer` kind at all. Expressing "one prefix, two
   domains" needs a third **state** domain, so the fixture grew a
   `packaging` one.

7. **The exemption list was a silent escape hatch.** Mutation M8 — adding
   `RULE_NFC` to `CLASSES_WITHOUT_FIXTURES` when it has a fixture — passed
   green. This was the only one of the four mutations against `953b2ad`
   that did not bite first time. Closed with a minimality check.

## Key Decisions

**Explicit per-call-site rule, not a scoped context manager.** A
`with rule(...)` wrapper around each checker would have been ~12 edits
instead of 56, but a `fail()` added later inside such a block silently
inherits a possibly-wrong class. Required keyword-only argument chosen for
the same reason `check_pairing()` reads both directories: a rule that holds
only while someone remembers is not a rule.

**Declared class must be PRESENT, not UNIQUE.** Asserting "the declared
class is the only class that fired" would fail cases 13–43 by construction
— each rewrites `goal-file.json`, so the family layer objects about
something the case does not claim. Presence is what makes the `overlaid`
gate unnecessary; the exactly-one property is maintained separately, by
fixture construction, for the family cases where it is achievable.

**The README is the declaration site, not a second list in the lint.**
Rejected keeping a `{case: class}` dict in `schema_lint.py`: that is the
same drift with an extra step, and the table is already where a reader
looks. Cost: markdown parsing. Failure mode is loud (every case reports
"has no row"), which made it acceptable.

**`schema (...)` parentheticals are documentation, not checked.** Only the
head token is asserted. Checking them would mean mapping jsonschema's
`error.validator` keyword onto cells deliberately more readable than the
keyword — `schema (abs_path pattern)` says which pattern; `pattern` does
not. Stated as a tradeoff in the README, not silently skipped. `family` is
the exception because its three parentheticals are already uniform and are
genuinely three different rules.

**Split `goal cross-file` out of `cross-file`.** Sharing one token let the
Site Model's three cases (3, 4, 8) stand in for `check_goal_file_cross_file`,
which had **no** fixtures at all. The split is what made
`check_class_coverage()` able to see the gap.

**Respelled the schema's `else` branch `{"refused": false}`.** Was
`{"not": {"required": ["refused"]}}` — same rule, but the `not` form
reports by printing the entire record back and saying it "should not be
valid", the message class D16(a) rules out. Rejected leaving it: case 57
existing is what made the message visible.

**Fixed the fixtures rather than downgrading the exactly-one claim.** The
alternative — rewriting the README to say "one finding per record" — was
cheaper and would have been honest, but the previous session established
that property deliberately and the declared classes do not subsume it
(a second `family (ceremony)` finding does not weaken a ceremony case,
but it does hide whether the case isolates).

**Three classes stay exempt.** `pairing`, `schema meta`, `harness` are
about the corpus's shape rather than a document's content, and this
harness's unit is an in-memory document overlay: an overlay cannot unpair
a schema, delete a fixture from disk, or break the harness running it.
Covering them needs a second fixture mechanism that replaces whole
directories — rejected as larger than the coverage it buys.

**Asked before adding the `refused` rule.** It is a new validator rule
past §13's decided floor, which is the same shape as the 54/55 no-op rules
the previous session asked about. The operator chose "Add it, plus fill
the class gaps".

## Evidence & Data

Counts: `EXPECTED_BROKEN` 50 → 52 → 59; `EXPECTED_BYTE_CLASS` 5 → 6.
56 `fail()` call sites tagged. 57 → 65 README declarations parsed.

**Pre-change baseline, measured at `ea5dafb` in a detached worktree** —
cases 49–55 each produced exactly 1 finding. Post-`eeef627` they produced
1, 1, 2, 3, 3, 2, 1. Post-mirror they are back to 1 each, and 56/57/59/60
are 1 each.

**Mutation results (the harness bites):**

| # | Mutation | Result |
| --- | --- | --- |
| M1 | case 13's README cell → `cross-file` | red: "declares 'cross-file', but the finding(s) came from ['family (apply)', 'family (hash)', 'schema']" |
| M2 | delete `goal-file.schema.json`'s `schema_version` `const` | red: case 13 "declares 'schema', but the finding(s) came from ['family (apply)', 'family (hash)']" — the exact failure the gate existed to prevent, now caught without it |
| M3 | a fixture dir with no README row | red (twice: count mismatch + no row) |
| M4 | a README row renamed away from its fixture | red (twice: no row + row names no fixture) |
| M5 | delete `check_refused_paths()` call | red: case 59 not caught |
| M6 | disable the family host check | red: case 60 not caught |
| M7 | disable the interlock-bundle-in-use rule | red: case 61 declares 'goal cross-file', got ['family (apply)', 'family (hash)'] |
| M8 | add `RULE_NFC` to `CLASSES_WITHOUT_FIXTURES` | **green — the hole.** Fixed with the minimality check; re-run red |

**Baseline-asymmetry proof.** Built a temporary case 98 overlaying
`goal-file-baseline.json` with `schema_version: 2`, declared `schema`. With
the const rule present it passes; with the rule deleted it goes red
("declares 'schema', but the finding(s) came from ['family (apply)',
'family (hash)']"). Under the old gate this case would have been masked,
because an overlaid baseline never stood the family layer down. Fixture
removed after measuring — it is not in the corpus.

**Family-layer mutation on the reject record** (proving it is not inert):
mutating `ceremony_class`, `proposed_sha256`, `baseline_sha256` each fires
exactly 1 finding naming `approval-record-reject`; mutating `host` fires 2
(schema pattern + family host).

**Line length:** 8 lines over 88 chars, against a pre-session baseline of
9. No formatter config exists in the repo (`ruff`/`pyproject`/`.editorconfig`
all absent — checked).

**Files changed this session** (`git diff --stat ea5dafb..HEAD`, 19 files,
+633/-130): `bin/schema_lint.py`, `schema/approval-record.schema.json`,
`examples/approval-record-reject.json`, `examples/broken-bytes/58-not-json.json`,
`examples/broken/README.md`, reject-record overlays in cases 49/51/52/53/54,
and new case dirs 59–65.

## Operator Feedback

- Chose **"Both, in that order"** for the two carried items — reject
  fixtures first, then the harness.
- Chose **"Add it, plus fill the class gaps"** on the `refused`-path
  question, going past the minimum on both halves.
- The standing pattern from `0b22` held: a **new validator rule past §13's
  decided floor** gets asked about rather than added unasked. Ordinary
  fixtures for an already-decided rule do not.
- Asked "what next?" at the end and was given the ranked list now in
  "Where We're Going"; the recommendation was handoff-then-projector,
  and they invoked `/handoff`.

## Where We're Going

1. **THE NEXT ACTION — build the projector, then its goldens.** This is
   the only genuinely open §18 item and the only one blocked on missing
   code rather than a decision. §13: CI invokes the agent's own projector;
   `project(examples/goal-file.json)` must byte-equal a checked-in
   `host_specific.json` golden, and a projection carrying any top-level key
   other than `vars` is a negative. Read
   `sed -n '/^## 13\./,/^## 14\./p'
   docs/architecture/goal-file-schema-reconciliation-2026-08-15.md` and
   §9's preamble on the device-side projector first. Note the harness now
   has a `parse`/`goal cross-file` vocabulary to extend — a projector layer
   should add its own rule class and fixtures, and `check_class_coverage()`
   will demand them.
2. **Small and concrete: the `<root>` instance path.** jsonschema reports
   an empty `error.path` for boolean subschemas, so case 57's finding names
   the offending value but not where it lives. Fix in `validate()` in
   `bin/schema_lint.py` — fall back to `error.schema_path` when
   `error.path` is empty. Verified empirically this session:
   `path=[] schema_path=['else','properties']`. ~15 minutes.
3. **Decision needed, not just time: make `schema (...)` parentheticals
   executable.** Requires mapping `error.validator` onto README cells that
   are deliberately more readable than the keyword. Either the cells get
   less readable or the check stays partial. Currently documented as a
   tradeoff in `examples/broken/README.md`.
4. **Fixtures for `pairing` and `schema meta`.** Needs a second fixture
   mechanism replacing whole directories on disk, since an in-memory
   overlay cannot unpair a schema. The exemption is documented in
   `CLASSES_WITHOUT_FIXTURES` and cannot now be widened silently.
5. Unrelated, low-priority, carried from `0b22`/`7b18`/`4a48`/`b0ff`:
   confirm `track-issue-activity.yml`'s Discussion path fires in
   site-djbclark — last scheduled run predates PR #158's merge, so it has
   never run live.
6. Unrelated to this repo: `~/src/cfengine-core` still shows a dirty
   `libntech` submodule — do **not** commit it. `libntech#291`,
   `cfengine/core#6293`, `#6294` are independent and all filed.

## Quick Start

```bash
cd ~/src/tendcf
git log --oneline -3   # confirm HEAD is 953b2ad or a descendant
uv run bin/schema_lint.py
# expect: schema-lint: OK (8 schemas, 59 negative fixtures, 6 byte-class fixtures)
python3 bin/xref_lint.py | grep -vE 'reviews/|deprecated/|handoffs/'
# expect: the same 3 pre-existing findings, unrelated

# What governs the open item, and the vocabulary a new layer must join:
sed -n '/^## 13\./,/^## 14\./p' docs/architecture/goal-file-schema-reconciliation-2026-08-15.md
grep -n 'RULE_\w* = \|CLASSES_WITHOUT_FIXTURES\|DETAILED_RULE_HEADS' bin/schema_lint.py
cat examples/broken/README.md          # all 65 cases; the "Caught by" column is executable
```

Per-case audit — what each fixture ACTUALLY fires, versus what its README
row declares. The harness only requires the declared class to be present,
so this is how you check isolation (note `Finding` is a NamedTuple now:
`.rule` and `.msg`, not a bare string):

```bash
uv run --with jsonschema --with rfc3339-validator --with referencing \
       --with rfc8785 --with pyyaml python - <<'PY'
import importlib.util, sys, copy
from pathlib import Path
REPO = Path("/Users/djbclark/src/tendcf")
spec = importlib.util.spec_from_file_location("sl", REPO/"bin"/"schema_lint.py")
sl = importlib.util.module_from_spec(spec); sys.modules["sl"]=sl; spec.loader.exec_module(sl)
declared = sl.read_declared_classes()
schemas, registry = sl.load_schemas(); happy = sl.load_happy_examples()
for case in sorted(p for p in sl.BROKEN_DIR.iterdir() if p.is_dir()):
    loaded = {k: copy.deepcopy(v) for k, v in happy.items()}
    for f in sorted(case.glob("*.yml")) + sorted(case.glob("*.json")):
        loaded[f.name] = sl.load_any(f)
    with sl.capture_findings(silent=True) as fs:
        sl.validate_loaded(loaded, schemas, registry, label_prefix=case.name)
    want = declared.get(case.name); fired = sorted({x.rule for x in fs})
    print(f"{'OK ' if want in fired else 'MISS'} {case.name:<42} want={want:<20} n={len(fs)} {fired}")
PY
```

Prove the harness still bites before trusting a green run — deleting a
rule must turn its case red, not just leave the lint green:

```bash
cp bin/schema_lint.py /tmp/sl.bak
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("schema/goal-file.schema.json"); s = json.loads(p.read_text())
p.with_suffix(".json.bak").write_text(p.read_text())
s["properties"]["schema_version"] = {"type": "integer"}   # const deleted
p.write_text(json.dumps(s, indent=2) + "\n")
PY
uv run bin/schema_lint.py    # expect case 13 red: "declares 'schema', but ..."
mv schema/goal-file.schema.json.bak schema/goal-file.schema.json
uv run bin/schema_lint.py    # expect OK again
```
