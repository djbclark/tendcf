---
schema_version: 1
handoff_id: 0b22
parent_handoff_ids: [7b18]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 063e4e585eb803581493a05e5db53cb2596f03b8
created_at: 2026-08-15T23:48:53-0400
writer: claude-code
---

# Handoff — reconciliation §18 item 5, the two new lint layers

## The Goal

`goal-file-schema-reconciliation-2026-08-15.md` §18 item 5: "Extend
`bin/schema_lint.py` per §13 (`.json` pairing, byte-class fixtures, JCS
idempotence, goal-file cross-file rules, no-`$ref`-of-defaulted-defs
rule)." Three of those five landed in earlier sessions (`9fdf437` and
before). This session resumed via `/baton` from handoff `7b18` to build
the remaining two, plus the goal-file/goal-diff hunk-consistency check
§13 states alongside them.

Item 5 is now closed **except projector goldens**, which §13 also names
and which cannot be built: they need an actual projector, and none exists.

## Where We Are

Clean tree, `master` at `063e4e5`, pushed. One commit this session:

- `063e4e5` — "schema: byte-class fixtures and family consistency,
  closing §18 item 5". 24 files: `bin/schema_lint.py` (+~420 lines),
  `examples/goal-file-baseline.json` (new), rewritten
  `examples/goal-diff.json` and `examples/approval-record.json`, 5 new
  byte-class fixtures, 7 new negative-fixture directories, and
  `examples/broken/README.md`.

`uv run bin/schema_lint.py` → `schema-lint: OK (8 schemas, 50 negative
fixtures, 5 byte-class fixtures)`. `python3 bin/xref_lint.py | grep -vE
'reviews/|deprecated/|handoffs/'` → the same 3 pre-existing findings named
in `7b18` and `4a48`, confirmed unchanged.

What landed, in the shape the code now has:

**Layer 3, the byte layer** (`check_canonical_bytes`, run on every `.json`
fixture before the parse). Duplicate keys refused via `object_pairs_hook`;
every key and string NFC-checked; the raw bytes compared against
`rfc8785.dumps(parsed)`. `rfc8785` is a new dependency in the script's uv
header — §2.1 explicitly says not to use `json.dumps(sort_keys=True)`,
which is not JCS for non-BMP strings. Five fixtures live in the new
`examples/broken-bytes/` (44-48) and are run through *only* this layer.

**Layer 5's family half** (`check_goal_file_family`, `apply_diff`,
`derive_ceremony_class`, `canonical_sha256`). The diff's two hashes must
name the two goal-file fixtures; applying its hunks to the baseline must
reproduce the proposed file byte for byte; the record's asserted
`ceremony_class` must equal the derived one. Seven negatives (49-55).

`validate_loaded()` gained an `overlaid: frozenset[str]` parameter; the
family layer stands down when the case under test replaces
`goal-file.json`. `check_goal_file_cross_file()` gained a `name` parameter
and now runs over both goal files, not just the proposed one.

## What We Tried

- **A verification of my own that was simply wrong, and the review caught
  it.** The commit originally claimed, in the `check_byte_class_fixtures`
  docstring and in `examples/broken/README.md`, that all five byte-class
  fixtures produce zero findings in every other layer — "nothing
  downstream of the parse can see any of them." I had "verified" this by
  running each fixture through `validate_loaded(...,
  overlaid=frozenset({"goal-file.json"}))`, which is exactly the argument
  that **gates the family layer off**. I tested the claim with the layer
  that would refute it disabled. Fable 5 re-ran it with the layer active:
  case 47's NFD path is a *different document*, so the family layer fires
  two findings on it (`proposed_sha256` mismatch, apply-does-not-
  reproduce). Confirmed independently before fixing. The corrected text is
  narrower and stronger: four of the five are invisible downstream; 47 is
  visible only as an unexplained hash disagreement, and turning that into
  "this string is not NFC" is precisely why §2.1 puts NFC in the lint.
  **Lesson for the next session: when a check has a gate, verifying the
  gated behavior requires turning the gate off.**
- **The existing fixture pair was inconsistent, and reading it was not
  enough to find that.** `goal-diff.json` carried
  `baseline_sha256: sha256:e5e5…` — a placeholder naming nothing on disk —
  and a single hunk while its `coverage_changes` claimed `supervision`
  went `undeclared → comprehensive`. Under §4.1 ("a domain absent from the
  map is undeclared") the baseline therefore had no `supervision` domain
  at all, so one add-hunk could not possibly reproduce a domain with four
  entries. Nothing in the repo could see this until the check existed.
- No approach was abandoned. The design settled before code: the ordering
  question (fixtures first or lint first) turned out not to matter, and
  the generate-then-validate discipline `4a48` established was used
  throughout — every canonical-byte fixture in this change was produced by
  a script in the scratchpad, never hand-authored.

## Key Decisions

- **A new `examples/goal-file-baseline.json`, rather than deriving the
  baseline by reverse-applying the hunks.** §13 says "applying hunks to
  old yields new," which presupposes an *old* artifact. Reverse-applying
  would have made the check near-tautological and would have left
  `baseline_sha256` a permanent placeholder — and "baseline-hash mismatch"
  is the first item on §13's own diff-class floor list. The baseline is
  `device-trust` only, which is exactly §4.1's undeclared silence class
  for `supervision`.
- **Rewriting the two placeholder hashes rather than leaving them.** This
  was the change's one real judgment call about touching decided artifacts.
  It papers over nothing: the record-must-carry-`baseline_sha256`-when-a-
  diff-exists rule encodes §11's actual sentence rather than foreclosing
  R22 (first adoption), which stays open.
- **The `overlaid` gate — kept, with its asymmetry documented.** Measured,
  not assumed: with the gate off the family layer alone fires on **31 of
  31** of cases 13-43, so every §10 schema rule would become deletable
  without a red lint. Fable's counter-argument is recorded and agreed
  with: the *clean* design is a targeted harness where each case declares
  its rule class (the README's "Caught by" column, machine-read) and
  `fail()` tags findings with a category. That subsumes the gate and closes
  the baseline asymmetry, but it is a real refactor — a category enum
  through every `fail()` call site plus 55 declarations. Named as a
  follow-on, not a precondition. The gate is safe today because all seven
  family cases are single-finding and therefore self-targeting.
- **Rejected: making `load_any()` reject duplicate keys.** It would have
  had to `die()` (exit 2) rather than produce a finding, turning a negative
  fixture into a crash. The byte layer owns I-JSON duplicate rejection
  because it is the layer that sees bytes at all.
- **Cases 54 and 55 go one step past §13's floor**, refusing the no-op
  hunk and the no-op coverage change — operator-approved (below), not a
  unilateral extension. §13 calls its list a floor, not a ceiling.

## Evidence & Data

- `uv run bin/schema_lint.py` → `schema-lint: OK (8 schemas, 50 negative
  fixtures, 5 byte-class fixtures)`, exit 0.
- **Every one of the twelve new fixtures produces exactly one finding, and
  its text names the rule the case is named for.** Verified by an ad-hoc
  probe running `validate_loaded` per case with `capture_findings`. The
  harness itself only requires ≥ 1 finding; this is the sharper property it
  cannot check.
- **31/31** — the family layer alone, gate off, fires on all of cases
  13-43. Verified independently after Fable reported it; the number is now
  a comment in `validate_loaded()`.
- Byte-class fixtures through every *other* layer, family layer ACTIVE:
  44, 45, 46, 48 → 0 findings each; **47 → 2 findings**. This is the
  corrected measurement.
- The five `apply_diff` branches no fixture covers (`no-coverage-change`,
  `phantom-domain`, `retreat-with-entries`, `add-over-existing`,
  `stale-old`) were smoke-tested by hand; all five fire with the right
  message. No dead code.
- Real hashes now in the fixtures:
  `goal-file.json` → `sha256:ad0cb7c024dce9e6f80b388d47f7893bcc1f69c0ccd9ede36aeca095eae19867`;
  `goal-file-baseline.json` → `sha256:a425d236cf58e785cd12fcbe603ef1b8721ba315b48c04367d8a5334de4cf5cc`.
- Behavioral facts confirmed empirically before writing any rule:
  `rfc8785.dumps({"x": 15.0})` → `b'{"x":15}'`; JCS idempotence does NOT
  catch a non-NFC string (RFC 8785 takes NFC as a precondition and passes
  anything else through); `json.loads(b'{"a":1,"a":2}')` → `{'a': 2}`,
  silently.
- Scratchpad generators (session-local, not in the repo):
  `gen_family.py`, `gen_negatives.py` under the session scratchpad.

## Operator Feedback

- **"Remember to use fable 5 as appropriate."** Interpreted as: implement
  inline (I had the corpus loaded; this is in-repo tooling, not the
  PR-bound upstream code the standing rule covers), then spend Fable 5 at
  xhigh on the adversarial review of the finished diff against §2/§4/§6/
  §11/§13. That was the right split — the review found a claim I had
  verified incorrectly and would have shipped.
- **No-op hunks: "Add the refusal + fixture 54 now."** Asked via
  `AskUserQuestion` because it goes past §13's decided floor. Consistent
  with `7b18`'s recorded pattern: finish small, well-scoped items when
  asked, rather than deferring by default. Landed as cases 54 *and* 55
  (hunk and coverage change) to keep one-rule-one-fixture.
- **Reject-with-annotations fixture: "Record it in the handoff only."**
  See item 2 below.

## Where We're Going

1. **THE NEXT ACTION — pick one of the three carried items below with the
   operator; nothing in this repo is blocked or broken.** §18 is now fully
   closed except projector goldens. There is no forced next step.
2. **Carried debt, §18 item 1, not item 5:** §11 says "Fixtures must
   include a reject-with-annotations and a wrong-ceremony-class negative."
   The wrong-ceremony-class half is now paid by cases 52/53. The reject
   half is **unmet corpus-wide** — every `approval-record.json` in the repo
   is `verdict: "accept"`, and `approval-record.schema.json`'s
   refused-iff-reject `if/then` has no fixture in either direction. Sits
   next to the goal-diff/approval-record adversarial fixture set `7b18`
   already listed as a candidate; the byte-class harness now exists to
   reuse.
3. **Follow-on named in this session's review: make the negative harness
   targeted.** Tag `fail()` findings with a rule class, have each case
   declare the class that must catch it, and assert that — machine-reading
   the README's existing "Caught by" column. Subsumes the `overlaid` gate
   and closes its baseline asymmetry (an overlaid *baseline* does NOT
   stand the family layer down, because 52/53 need it live; a future schema
   negative written as a broken baseline would be masked. Write such a
   case against `goal-file.json` instead until this lands). Cost: a
   category enum through every `fail()` call site plus 55 declarations.
4. **Projector goldens** unblock only when a projector exists (§13:
   `project(goal-file.json)` byte-equal to a checked-in
   `host_specific.json`; a projection with any top-level key but `vars` is
   a negative).
5. Unrelated, low-priority, carried from `7b18`/`4a48`/`b0ff`: confirm
   `track-issue-activity.yml`'s Discussion path fires in site-djbclark —
   last scheduled run predates PR #158's merge, so it has never run live.
6. Unrelated to this repo: `~/src/cfengine-core` still shows a dirty
   `libntech` submodule — do **not** commit it. The three CFEngine PRs
   (`libntech#291`, `cfengine/core#6293`, `#6294`) are independent and all
   filed; no action needed.

## Quick Start

```bash
cd ~/src/tendcf
git log --oneline -3   # confirm HEAD is 063e4e5 or a descendant
uv run bin/schema_lint.py
# expect: schema-lint: OK (8 schemas, 50 negative fixtures, 5 byte-class fixtures)
python3 bin/xref_lint.py | grep -vE 'reviews/|deprecated/|handoffs/'
# expect: the same 3 pre-existing findings, unrelated

# The two new layers and what governs them:
sed -n '/^## 13\./,/^## 14\./p' docs/architecture/goal-file-schema-reconciliation-2026-08-15.md
sed -n '/^## 11\./,/^## 12\./p' docs/architecture/goal-file-schema-reconciliation-2026-08-15.md
cat examples/broken/README.md          # all 55 + 5 cases, with what catches each

# Verify any per-case claim in this handoff (the harness only checks >= 1
# finding; this checks WHICH finding):
uv run --with jsonschema --with rfc3339-validator --with referencing \
       --with rfc8785 --with pyyaml python - <<'PY'
import importlib.util, sys, copy
from pathlib import Path
REPO = Path("/Users/djbclark/src/tendcf")
spec = importlib.util.spec_from_file_location("sl", REPO/"bin"/"schema_lint.py")
sl = importlib.util.module_from_spec(spec); sys.modules["sl"]=sl; spec.loader.exec_module(sl)
schemas, registry = sl.load_schemas(); happy = sl.load_happy_examples()
for case in sorted(p for p in sl.BROKEN_DIR.iterdir() if p.is_dir()):
    loaded = {k: copy.deepcopy(v) for k, v in happy.items()}; ov=set()
    for f in sorted(case.glob("*.yml")) + sorted(case.glob("*.json")):
        loaded[f.name] = sl.load_any(f); ov.add(f.name)
    with sl.capture_findings(silent=True) as fs:
        sl.validate_loaded(loaded, schemas, registry, label_prefix=case.name,
                           overlaid=frozenset(ov))
    print(f"{case.name}: {len(fs)} finding(s)")
PY
```
