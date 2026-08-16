---
schema_version: 1
handoff_id: 7c19
parent_handoff_ids: [c60a]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: f51f31b9751d3d4542dc5c6b7ee22d62f50eaf79
created_at: 2026-08-16T13:00:52-0400
writer: claude-code
---

# Handoff — all seven open gate findings closed

## The Goal

`c60a` left seven adversarial-review findings open (F3–F9) and named F3 as
THE next action. This session resumed from it via `/baton` and closed all
seven. The operator's instruction was exactly "Do the resume plan" — no
scope was added by them and none was asked for.

The one claim the whole session turns on: **before F3 landed, "the projector
gate is mutation-verified" was false.** `c60a` says so explicitly and told
the next session not to repeat it. It is true now.

## Where We Are

master `f51f31b`, clean, everything pushed. Seven commits since `159628e`:

| SHA | Finding | What |
|---|---|---|
| `dceb03f` | F3 | NFC fixture 78; `EXPECTED_PROJECTION` 12→13 |
| `5ec85aa` | F4 | N-1 compares differing pointers; `_shape()` deleted |
| `21a4ef5` | F5 | `\Z` not `$`, ×3, with fixtures 79–81 |
| `dac29dd` | F7 | N-5 reads value position; fixtures 82–83 |
| `849326b` | F6 | innermost `$ref` only; `items` out of `APPLICATORS` |
| `6700be2` | F8 | fixtures 84–92, N-8 as a property, `bin/flag_coverage.py` |
| `f51f31b` | F9 | canonical-bytes claim made true again |

19 files, +352/−54. One new tool (`bin/flag_coverage.py`), 15 new fixtures
(78–92), `bin/projector.py` and `bin/schema_lint.py` modified,
`examples/broken/README.md` extended.

Gate state, all re-measured at `f51f31b`:

```
schema-lint: OK (8 schemas, 59 negative, 6 byte-class, 27 projection)
xref_lint:   0 findings, 28 live / 57 frozen, 561 sections / 85 documents
flag-coverage: 21/21 rules independently guarded
golden:      645 bytes, byte-identical
```

**Blockers: none.** F1/F2 were closed by `c60a`'s session in `4971e05`;
F3–F9 are closed here, so nothing is open from the review.

**Open questions, both design rather than defect:** (1) device-trust's
destination, §11 — see Where We're Going item 1; (2) F7's fourth trust body,
which is genuinely undecidable from projection bytes and is recorded as a
stated limit in `bin/projector.py`'s docstring rather than as a TODO. Neither
blocks anything; both are named so the next session does not rediscover them
as surprises.

## What We Tried

### Every fix was reproduced first, then committed, then mutated

This is `c60a`'s stated discipline and it held for all seven. No fix was
written on the strength of reading the review.

**F3 (HIGH) — the ninth mutation.** Confirmed the NFC guard was live, then
neutered it and confirmed the gate stayed green:

```
schema-lint: OK (…, 12 projection fixtures)      LINT EXIT=0
project(goal file with working_dir "/srv/café") → b'/srv/cafe\xcc\x81'
```

Fixture 78 is the golden with `working_dir` set to `"/srv/cafe" + U+0301`.
It is deliberately its OWN JCS canonical form — JCS takes NFC as an input
precondition and passes anything else through untouched — so the byte
compare agrees with it and the NFC check is the only thing that dissents.
Exactly one finding. M11 (neuter the NFC check, against the committed fix)
now reports `78-…: was not caught`.

**F4 (HIGH) — `_shape()`.** Reproduced with the review's own mutation:

```
schema-lint: OK (…, 13 projection fixtures)      LINT EXIT=0
argv before flip: ['/opt/homebrew/bin/caddy', 'run', '--config', '/etc/caddy/Caddyfile']
argv after  flip: ['/etc/caddy/Caddyfile', '--config', 'run', '/opt/homebrew/bin/caddy']
golden unchanged: True
```

N-1 now computes the exact set of differing JSON pointers between the two
projections and requires it to be precisely
`[vars/tendcf_service/<target>/state]`. That subsumes the structural check,
so `_shape()` was deleted rather than kept alongside.

**F5 (MEDIUM) — `$` vs `\Z`.** All three restated patterns accepted a
trailing newline. The service-id case was NOT in the review's list:

```
interlock id with \n : ACCEPTED — no findings
service  id with \n : ACCEPTED — no findings
env value with \n   : ACCEPTED — no findings
```

**F7 (MEDIUM) — N-5 key-only.** Measured each of the corpus's four
device-trust bodies pasted into a legal service body, before and after:

| body | before | after |
|---|---|---|
| `advisor-key` | CAUGHT | CAUGHT |
| `agent` (the binary pin) | MISSED | CAUGHT |
| `policy-tree` | MISSED | CAUGHT |
| `trust-policy` | MISSED | **still MISSED** |

**F6 (MEDIUM).** All three of the review's swaps reproduced green, then red.

**F8 (LOW).** Re-measured coverage before touching anything: 11/21, not the
review's 8/19 — F5 and F7 had already moved it, and the trust-key site was
by then independently guarded by fixtures 82/83. The closed-container site
still was not.

**F9 (LOW).** Confirmed by reading: docstring says "every `.json` fixture
on disk", loop iterates `EXAMPLES`, `OUTPUT_ONLY_EXAMPLES` removes
`host_specific.json` from that set.

### Failed / cost time

1. **Two mutations silently did not apply.** M19/M20 (dropping one branch
   from `TRUST_SHAPED_VALUE`'s alternation) were written as `python3 -c`
   inside a bash function; the shell ate the `\Z` in the anchor string, the
   anchor matched 0 times, and one of the two had no assert. It printed
   `schema-lint: OK` — **which reads exactly like "the check survives".**
   Caught because the *other* one did assert. Redone from a script file
   with the anchor passed as `argv`; both then bit correctly.
   **This is the single most important process note in this document.** An
   unapplied mutation and a surviving check are indistinguishable in the
   output. `bin/flag_coverage.py` refuses to report a number if any
   mutation fails to apply, for exactly this reason.
2. **A README swap anchor matched 3 times** (`` schema (`const`) | `` is
   not unique in `examples/broken/README.md`). The assert caught it; redone
   with the full row as the anchor. Same class of error as (1), caught the
   same way.
3. **`\Z` and `\n` in the projector's module docstring were read as escape
   sequences** — `SyntaxWarning: invalid escape sequence '\Z'`, and `\n`
   silently inserted a real newline. The docstring is now `r"""`. It
   contained no other backslashes, verified by grep before converting.

## Key Decisions

- **Went past F8's ask, deliberately.** It asked for independent fixtures
  for two mutually-masking rules. Delivered 21/21 on every `flag()` site in
  `check_projection()`, plus a tool that measures it. Rationale: the repo's
  whole thesis is that a check which is not mutation-guarded is not a check,
  and "8/19" was a number nobody could re-derive. Rejected the smaller fix
  because it would have left ten sites deletable in silence.
- **`bin/flag_coverage.py` stays OUT of `schema_lint`.** It runs the whole
  lint once per site — ~21 runs, ~18s, against a lint that takes 0.86s and
  runs on every commit. Measured both numbers before deciding. Rejected
  wiring it in.
- **N-8 became a property, not a fixture.** Expressing a 5 MiB ceiling as a
  file means checking in a 5 MiB file. It joined N-1 and N-11 in
  `check_projector_properties()`, over bytes synthesised in memory.
  Rejected leaving the site unguarded, which would have made 21/21
  unreachable and the count flattering.
- **F9 fixed by making the claim TRUE, not by weakening it.** The review
  accepted "it's the comment that's wrong" as sufficient. Iterating
  `sorted(set(EXAMPLES) | OUTPUT_ONLY_EXAMPLES)` restores the induction for
  one line. Being output-only describes where a file comes from, never a
  licence for its bytes to be non-canonical.
- **F7 stops at 3 of 4, and says so as a number.** `trust-policy`'s body is
  `{"local_yes_required": true, "state": "present", "tier": "consented"}` —
  no digest anywhere, and nothing in projection bytes distinguishes it from
  a legal service body without the schema, which a projection does not
  carry. Rejected a heuristic on field names as exactly the kind of
  undocumented interpreter §1 refuses. The docstring previously said "trust
  in a value is not caught", which understated a one-of-four to sound like
  an edge case; it now states the fraction.
- **Values held to the schema's FULL digest pattern, keys to a bare
  prefix.** `TRUST_SHAPED_VALUE` is `^(ed25519|sha256):[0-9a-f]{64}\Z`;
  `TRUST_SHAPED_KEY` stays `^(ed25519|sha256):`. A projection key is a
  variable name and nothing legitimate is named `sha256:…`; a value is free
  text where a prefix alone is weak evidence. Restating the full pattern
  keeps the checker from being stricter than the goal file — same
  discipline as `ENTRY_ID_PATTERNS`.
- **`prefixItems` and `contains` stay in `APPLICATORS`; `items` goes.**
  Those two reject (a tuple position's schema, an at-least-one-match
  requirement); `items` only descends, which is the objection the code's own
  comment already raises against `properties`.
- **Fixture 93 was written and then deleted.** It tripped the same `flag()`
  site as 92 with a different type. Redundant fixtures inflate the count
  without adding a guard.

## Evidence & Data

**Mutations run this session** (M11 onward; M1–M10 are in `d699fd6` and
`4971e05`). Every one applied against a COMMITTED fix, restored with
`git checkout` afterwards, tree verified clean each time.

| # | Mutation | Result |
|---|---|---|
| M11 | neuter the NFC check | `78-decomposed-string-in-projection.json: was not caught` |
| M12 | `state` branch reverses `command` | N-1 names `command/0..3` |
| M13 | `state` branch drops `bundle` | N-1 names the entry |
| M14 | projector stops copying `state` | N-1: "did not change … at all" (+ golden) |
| M15 | service id pattern `\Z`→`$` | `80-newline-in-service-id.json: was not caught` |
| M16 | interlock id pattern `\Z`→`$` | `79-newline-in-interlock-id.json: was not caught` |
| M17 | `SECRETSPEC_NAME` `\Z`→`$` | `81-newline-in-env-value.json: was not caught` |
| M18 | neuter the trust value branch | 82 AND 83 not caught |
| M19 | drop `ed25519` from the alternation | `83-…: was not caught` |
| M20 | drop `sha256` from the alternation | `82-…: was not caught` |

M15/M16/M17 each bit **only their own fixture** — no masking. M19/M20 are
the pair that silently no-opped on the first attempt (see What We Tried).

**F6 evidence-set narrowing**, measured with a probe that re-runs
`validate_loaded()` per case and unions `finding.evidence`:

| case | before | after |
|---|---|---|
| 43 `float-timeout` | 5: `interlock_entry, interlock_map, state_domain, state_entries, type` | 2: `interlock_entry, type` |
| 34 `silenced-interlock-report` | 5 | 2: `const, interlock_entry` |
| 5 `macos-no-launchd` | 4 | 3: `if/then, required, service` |
| 24 `dot-dot-path` | 10 | 7 |
| 27 `two-unit-flavors` | 10 | 7 |

All 59 negative fixtures still pass with their existing parentheticals, so
no cell was leaning on the loose evidence. The `oneOf` looseness is
deliberately kept and is now most of the remaining width.

**`flag()` coverage of `check_projection()`**, `bin/flag_coverage.py`:

- review measured 8/19 · re-measured at session start 11/21 · **now 21/21**
- the ten that survived at session start: lines 341, 351, 354, 391, 414,
  423, 429, 440, 443, 473 — i.e. N-8, six parse/type guards, no-top-level-
  `vars` (P-6.3), closed-container (N-5/N-12/P-1), empty-container (P-6.4)
- line 429 (closed container) is the one that mattered: `d699fd6`'s M7
  credited it with catching a tombstone split, and until fixture 84 every
  fixture reaching it (69, 75) also tripped the trust-key rule beside it

**Fixtures added:** 78–92, fifteen in all, `EXPECTED_PROJECTION` 12→27.
Every one verified to produce **exactly one** finding, which is `c60a`'s
fixture-76 lesson: a fixture carrying a second defect lets the check under
test stop firing unnoticed.

**Timing measured before the flag_coverage placement decision:**
`bin/schema_lint.py` 0.86s real; `bin/flag_coverage.py` ~18s (21 lint runs).

## Operator Feedback

- Session opened with `/baton`, then **"Do the resume plan."** — no
  elaboration, no added scope. The resume plan was stated back before any
  file was touched, per the reader protocol.
- Asked at the end: "what's next? should we do a handoff first?" — the
  handoff was recommended and run.
- Standing authorization to commit and push (auto-memory
  `commit-and-push-without-asking`) was exercised: pushed at the F3/F4/F5
  milestone and again at the end.
- `docs/handoffs/` push-in-place exception (this repo's `CLAUDE.md`,
  operator instruction 2026-08-15) applies to this document.

## Where We're Going

1. **THE NEXT ACTION: device-trust's destination.** The top open DESIGN
   question — `docs/architecture/projector-reconciliation-2026-08-16.md`
   §11. P-1 removed device-trust from the projection; R21's third arrow
   names "the agent's own config", a file whose format is specified
   nowhere. **F7 just handed this concrete new evidence it did not have
   before:** N-5 now catches 3 of the corpus's 4 trust bodies, and the 4th
   is provably undecidable from projection bytes alone. Settle it while the
   projector reasoning is still on the record.
2. **The generic bundle** — the `.cf` that reads `tendcf_service` and
   renders promises from `state`. C-1 makes this load-bearing: the
   negative-promise lists are the bundle's to iterate, not the projector's
   to emit. This is the biggest remaining deliverable and wants a full
   session.
3. **nix2cf** — in the operator's approved scope for two sessions now and
   still never touched. Worth explicitly deciding whether it is still in
   scope rather than letting it ride a third time.
4. **Run `bin/flag_coverage.py` after any change to `check_projection()`.**
   It must stay 21/21. It is NOT part of `schema_lint` (see Key Decisions).
5. Unrelated, carried from `c60a`/`ad4c`/`0b22`/`7b18`/`4a48`/`b0ff`:
   confirm `track-issue-activity.yml`'s Discussion path fires in
   site-djbclark.
6. Unrelated: `~/src/cfengine-core` still shows ` M libntech` — do NOT
   commit it. libntech#291, cfengine/core#6293, #6294 are filed.

## Quick Start

```bash
cd /Users/djbclark/src/tendcf && git log --oneline -8

# All three gates. These are the numbers to expect at f51f31b:
bin/schema_lint.py     # OK (8 schemas, 59 negative, 6 byte-class, 27 projection)
bin/xref_lint.py       # 0 findings, 28 live / 57 frozen
bin/flag_coverage.py   # 21/21 rules independently guarded  (~18s, on demand only)
bin/projector.py examples/goal-file.json | cmp - examples/host_specific.json

# The design question that is next (§11):
sed -n '/^## 11/,/^## 12/p' docs/architecture/projector-reconciliation-2026-08-16.md

# What F7 left open, in the projector's own words:
sed -n '/Two limits of that checker/,/^The id patterns/p' bin/projector.py

# The review this chain has now fully answered (all nine findings closed):
sed -n '1,20p' docs/paper/reviews/2026-08-16_opus-5-high_projector-gate-review.md
```

**Mutation discipline — the rule, and the trap under it.**

```bash
git add -A && git commit -m "..."   # 1. commit the fix FIRST
python3 mutate.py "<anchor>" "<replacement>"   # 2. mutate — ASSERT the anchor
bin/schema_lint.py                             #    matched exactly once
git checkout bin/projector.py                  # 3. restore
```

Pass anchors as `argv` from a script file, never inside a `python3 -c`
string in a bash function — the shell ate a `\Z` this session and two
mutations no-opped while printing `schema-lint: OK`. **An unapplied
mutation and a surviving check produce identical output.** Assert, or the
number you report means nothing.
