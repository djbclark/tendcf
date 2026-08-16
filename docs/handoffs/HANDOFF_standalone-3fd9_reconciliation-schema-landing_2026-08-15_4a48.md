---
schema_version: 1
handoff_id: 4a48
parent_handoff_ids: [b0ff]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 3bb0a9d2979a14fdfd721e54427a3371ef02401b
created_at: 2026-08-15T22:53:42-0400
writer: claude-code
---

# Handoff — landing the goal-file schema reconciliation's follow-on edits (§18)

## The Goal

`goal-file-schema-reconciliation-2026-08-15.md` (landed in commit
`2fcb366`, prior session) decided a design but deliberately made no
follow-on edits itself. Its §18 lists five items, operator-gated, to be
landed one at a time: (1) the goal-file/goal-diff/approval-record schema
family, (2) a `report-row.schema.json` addition, (3) seven
`architecture-DEFINITIVE-v3.md` amendments, (4) guide amendments, (5)
extending `bin/schema_lint.py`'s fixture mechanism. This session resumed
from handoff `b0ff` (which had landed the glossary and the xref linter)
and worked through items 3, 1, and 2, in that order, at the operator's
direction each time.

## Where We Are

Clean tree, `master` at `3bb0a9d`, three commits ahead of where this
session started (`466e68d`):

- `726a4ef` — the seven `architecture-DEFINITIVE-v3.md` amendments
  (§18 item 3).
- `9fdf437` — the goal-file schema family (§18 item 1).
- `3bb0a9d` — `report-row.schema.json`'s `schema_ceiling` addition
  (§18 item 2).

`bin/schema_lint.py` passes clean: 8 schemas, 43/43 negative fixtures
caught. `bin/xref_lint.py` reports only 3 pre-existing findings, all
unrelated to this session's work (two in the E1 adjudication docs, one
in the Grok opinion — `docs/architecture/e1-adjudication-2026-08-15.md:316`,
`e1-adjudication-xhigh-2026-08-15.md:49`, `goal-file-schema-opinion-grok.md:278`,
all pre-dating this session).

§18 items 4 and 5 are **not started**. Item 1's two outline schemas
(`goal-diff.schema.json`, `approval-record.schema.json`) have paired
happy fixtures but no adversarial fixture set — that was an explicit
scope decision (see Key Decisions), not an oversight.

## What We Tried

Nothing here failed outright, but two design choices took a
correction-in-place:

- **First unit-writer fixture design was wrong.** The happy goal-file
  fixture originally used service id `com.tendcf.caddy` under
  unit-writer prefix `com.tendcf.caddy.*`. The new
  `check_goal_file_cross_file` lint rule (built for this same session)
  caught it: a prefix `X.*` matches labels `X.foo`, not the bare string
  `X` itself, by the same `removesuffix("*")` + `startswith` logic the
  existing Site-Model rule already used. Fixed by renaming the service
  ids to `com.tendcf.caddy.main` / `com.tendcf.caddy.retired` (one
  present, one tombstoned) and regenerating the happy fixture, all 31
  negative fixtures, and re-verifying canonical-byte idempotence — this
  is why the fixture set was built as a generate-then-validate Python
  script rather than 31 hand-authored JSON files, specifically so a
  fixture-design bug like this was caught before 31 files needed
  hand-editing.
- **Case 35's rename got over-broad via `sed`.** A blanket
  `sed 's/com\.tendcf\.caddy/com.tendcf.caddy.main/g'` pass (done to
  propagate the id rename above into the negative-fixture generator
  script) also mangled case 35 (`malformed-writer-prefix`, which
  deliberately strips the `.*` suffix from a prefix key) into renaming
  the wrong thing. Caught by re-running the "every case must be rejected
  by exactly its own violation" verification pass before writing files,
  fixed with a scoped string replace instead of the broad `sed`.

## Key Decisions

- **Two Grok `§9.12` citations were factually wrong, not just malformed.**
  The Grok opinion has top-level sections 0–13 with no `.12` subsection
  anywhere; the actual referent is item 12 of §9's numbered "what not to
  build" list. Fixed both citations (lines 430, 1159 of the reconciliation
  doc) to read "Grok §9, cut 12" rather than "Grok §9.12" — this was
  flagged as a blocker in the parent handoff and is now resolved;
  `bin/xref_lint.py` confirms zero findings against either file it
  touched.
- **Byte-class negatives explicitly deferred to §18 item 5, not built
  now.** Reconciliation §13 names negatives that need raw pre-parse byte
  comparison (a pretty-printed twin of the happy path, duplicate keys,
  non-NFC strings, a `15.0` spelling of `15`) — `bin/schema_lint.py`
  parses fixtures with `json.loads`/`yaml.safe_load` before any
  comparison happens, so these are structurally uncatchable without a
  new mechanism. Rather than build that mechanism inline (a real feature:
  raw-byte fixture loading, a JCS re-implementation or dependency, an
  idempotence check), the 31 fixtures landed this session are exactly
  the JSON-Schema-catchable negatives from reconciliation §10's list, and
  the byte-class set stays explicitly named as future work (in the
  `bin/schema_lint.py` docstring and `examples/broken/README.md`).
  Rejected alternative: silently skip mentioning them, which would read
  as "the negative set is complete" when it isn't.
- **`goal-diff.schema.json` / `approval-record.schema.json` got outline
  treatment, not full adversarial fixtures.** Reconciliation §11 says so
  explicitly: "outline... not this document's tested surface." Built
  each with one happy canonical-JCS fixture, paired and registered in
  `bin/schema_lint.py`'s `EXAMPLES`, but no negative fixture set and no
  goal-file/goal-diff hunk-consistency cross-check ("applying hunks to
  old yields new," named in §13). Deferred alongside item 5's harness
  work, not before it — building that consistency check well needs the
  byte-class/canonicalization machinery anyway.
- **Negative-fixture case numbering continues the existing flat sequence
  (13–43), not a new namespace.** The existing `examples/broken/`
  directory already mixes cases across four different schemas under one
  flat `01`–`12` numbering (report-row, services, roles all interleaved).
  Continuing that convention rather than inventing a `gf-`-prefixed
  namespace keeps `EXPECTED_BROKEN` a single meaningful counter and
  matches how the harness already treats the directory as one flat list.
- **RFC 8785 canonicalization via the `rfc8785` PyPI package**, fetched
  on demand with `uv run --with rfc8785`, rather than hand-rolling JCS.
  Verified round-trip idempotence (`canonicalize(fixture) == fixture`)
  on every `.json` fixture written this session — this is the "the
  fixture IS the canonicalization test" property reconciliation §13
  names.
- **`schema_ceiling` required now, not optional-then-required**, per the
  reconciliation's own explicit reasoning (§12): nothing writes report
  rows yet, so there's no legacy row needing a leniency window.

## Evidence & Data

- `uv run bin/schema_lint.py` → `schema-lint: OK (8 schemas, 43 negative
  fixtures)` (confirmed after each of the three commits, most recently
  at `3bb0a9d`).
- `python3 bin/xref_lint.py | grep -vE 'reviews/|deprecated/|handoffs/'`
  → 3 findings, all pre-existing (confirmed unchanged before and after
  this session's edits — see Where We Are for the exact three).
- `examples/goal-file.json`: 1403 bytes, JCS-canonical, idempotent under
  re-canonicalization (`rfc8785.dumps(json.loads(raw)) == raw`), one
  `device-trust` domain (policy-tree, trust-policy tier `consented` with
  `local_yes_required: true`, one advisor-key, the `tendcf-agent` entry)
  plus one `supervision` domain (a present `caddy` service, a tombstoned
  one, one interlock, one unit-writer).
- `examples/broken/13`–`43`: 31 directories, each one full alternate
  `goal-file.json`, each independently verified (via a throwaway
  validation script, not by eyeballing) to be rejected by exactly one
  schema violation before being written to disk.
- `git diff --stat` across the three commits: `726a4ef` touched 2 files
  (+160/−37); `9fdf437` touched 39 files (+3625/−16, almost entirely new
  fixture files); `3bb0a9d` touched 2 files (+12/−1).

## Operator Feedback

- Asked to continue with §18 item 3 first (the map amendments), then
  explicitly said "yes" to continuing with item 1 (the schema family)
  before I'd finished describing it — a green light to proceed without
  re-confirming scope mid-task.
- When asked "what should we do next" with context already large (242K
  cached tokens per the harness's own warning), chose via
  `AskUserQuestion`: do the small item 2 now, then hand off — rather than
  either stopping immediately or pushing further into items 4/5 in an
  already-large context. That preference (finish the cheap thing, defer
  the expensive thing to a fresh session) is the operating principle
  behind this handoff's own timing.

## Where We're Going

1. **THE NEXT ACTION — §18 item 4: amend the guide.** Per reconciliation
   §18 item 4: amend `docs/paper/tendcf-architecture-guide.md` §4 (the
   YAML-input claim is false against CFEngine 3.27.1 — JSON only; C-9),
   §7 (the removals paragraph needs the same tombstone rewrite the map's
   §9.8 already got in `726a4ef` — currently the guide and map disagree,
   which is the exact blocker the parent handoff `b0ff` flagged and this
   session's map amendment fixed on the map side only), and §16.A (mark
   the `nix2cf_edges`/`host_specific.json` illustration as preview-channel
   and non-loading; C-9). Read the reconciliation's own citations first:
   `grep -n "C-9\|C-4" docs/architecture/goal-file-schema-reconciliation-2026-08-15.md`
   and re-read `docs/architecture/architecture-DEFINITIVE-v3.md` §9.8 and
   §4.1 (both amended this session in `726a4ef`) as the target shape the
   guide needs to match.
2. **§18 item 5: extend `bin/schema_lint.py` per reconciliation §13.**
   The byte-class fixture mechanism (raw bytes compared before parsing),
   JCS idempotence checking as a lint layer (not just a one-off script
   during fixture authoring), goal-file/goal-diff hunk-consistency
   cross-check, and projector goldens (blocked on an actual projector
   implementation existing — it doesn't yet). This is real engineering,
   not a doc edit; start it in a fresh session/context, not tacked onto
   item 4.
3. Once items 4 and 5 land, `goal-diff.schema.json` and
   `approval-record.schema.json` are candidates for a proper adversarial
   fixture set (currently outline-only, see Key Decisions) — not blocking,
   but worth revisiting once the byte-class harness exists to reuse.
4. Unrelated, low-priority, carried from `b0ff`: confirm
   `track-issue-activity.yml`'s Discussion path fires — last scheduled
   run predates PR #158's merge by 76 seconds, so it has never run live.
5. Unrelated to this repo: `~/src/cfengine-core` still shows a dirty
   `libntech` submodule — do not commit it. The three CFEngine PRs
   (`libntech#291`, `cfengine/core#6293`, `#6294`) are independent and
   all filed; no action needed there.

## Quick Start

```bash
cd ~/src/tendcf
git log --oneline -5   # confirm HEAD is 3bb0a9d or a descendant
uv run bin/schema_lint.py   # expect: schema-lint: OK (8 schemas, 43 negative fixtures)
python3 bin/xref_lint.py | grep -vE 'reviews/|deprecated/|handoffs/'   # expect: 3 pre-existing findings, unrelated

# Start item 4 (the guide amendments):
grep -n "C-9\|C-4" docs/architecture/goal-file-schema-reconciliation-2026-08-15.md
sed -n '1,60p' docs/paper/tendcf-architecture-guide.md   # find §4
grep -n "^## §7\|^## 7\." docs/paper/tendcf-architecture-guide.md
grep -n "16.A\|nix2cf_edges" docs/paper/tendcf-architecture-guide.md
```
