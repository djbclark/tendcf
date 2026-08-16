---
schema_version: 1
handoff_id: c60a
parent_handoff_ids: [9229]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 1e7a006d18fe9245ab7a99a86c31a936fb76f517
created_at: 2026-08-16T12:40:04-0400
writer: claude-code
---

# Handoff — the projector gate reviewed, two holes closed, seven open

## The Goal

Continuation of `9229` (same session). That handoff was written while an
adversarial review of the projector gate was still running, and says so.
The review has since returned. **This document supersedes `9229` on that
point and carries the findings; everything else in `9229` still stands.**

The review asked the one question none of the earlier work had: *can a
projection be wrong under the reconciliation yet be accepted by
`validate_projection()`, or can `bin/projector.py` be changed to emit wrong
bytes while `bin/schema_lint.py` still reports OK?* The session had claimed
eight mutations all bit; the brief explicitly asked for a ninth that does
not.

It found one, and eight other things.

## Where We Are

master `1e7a006`, clean, everything pushed. Fourteen commits since the
chain's previous head `9325d0b`; the two added after `9229`:

| SHA | What |
|---|---|
| `4971e05` | closes F1 and F2, with fixtures 76/77 and mutations M9/M10 |
| `1e7a006` | checks in the review as dated evidence |

Linters: `schema-lint: OK (8 schemas, 59 negative fixtures, 6 byte-class
fixtures, 12 projection fixtures)`; `xref_lint` 0 findings, 28 live / 56
frozen. Reconciliation §18 remains closed.

**Two findings fixed. Seven open, and they are the substance of this
handoff.** The review is at
`docs/paper/reviews/2026-08-16_opus-5-high_projector-gate-review.md`, with
its brief at `prompt_projector-gate.txt` beside it.

## What We Tried

### Fixed, both reproduced before touching anything

**F2 (HIGH) — N-4 defeated; a real secret reached the output.** N-4 exists
to stop a resolved secret reaching
`$(sys.workdir)/data/host_specific.json`. It was guarded by
`if isinstance(env, dict)`, and `project()` copies entry bodies verbatim
without schema-validating them (P-6.5). So:

```python
svc["env"] = ["CADDY_ADMIN_TOKEN=<fabricated-probe-value>"]
project(d)  # succeeded; the value appeared in the output bytes;
            # validate_projection() == []
```

The schema forbids a list-valued `env`, which is exactly the wrong reason
to skip the check — N-4 is *for* the case where something upstream did not
hold. An `env` of any non-dict type is now itself the finding.

**F1 (HIGH) — the checker crashed instead of refusing.** `json` accepts
`NaN`, `Infinity`, `1e999`, integers outside the IEEE-754 double domain and
lone surrogates; `rfc8785` raises on all of them. Both `check_projection()`
and `project()` called `rfc8785.dumps` unguarded, so
`validate_projection()` — documented to *return* findings, "empty means
OK" — raised. Since `schema_lint` calls it in a loop with no `try/except`,
one such fixture aborted the whole lint before `check_declaration_coverage()`
and `check_class_coverage()` ran. Verified: `NaN`, `2**70` and `"\ud800"`
all raised. Now a refusal in both places.

### Failed / cost time

1. **`git checkout bin/projector.py` to undo a mutation wiped the
   uncommitted F1+F2 fixes.** This is the SECOND time this exact mistake
   happened in one session — `9229` records the first, on
   `examples/broken/README.md`. **Rule: commit the fix, THEN mutate, then
   `git checkout` to restore.** Do not mutation-test uncommitted work
   against a git restore.
2. **Two background dispatches sharing one output path.** The first
   (broken) run's `>` truncated the file the retry was writing to. Give
   every dispatch its own output file.
3. **`claude -p` in a background job waits on stdin**, emits
   `Warning: no stdin data received in 3s`, and can produce nothing. Needs
   `< /dev/null`. One review run was lost to this.
4. **The per-account cswap profile reported `Not logged in`** after the MIT
   account's 5h limit reset, while `cswap list` showed it healthy at 0%.
   Not diagnosed; fell back to the active account. (The separate, already
   known hazard — `cswap run N -- claude -p` silently dropping the prompt —
   is in `9229` and in auto-memory `cswap-run-drops-the-prompt`.)

## Key Decisions

- **Fix F1 and F2 now; leave F3–F9 for a fresh session.** Context was at
  ~350K and the harness was pushing to wrap. F2 is a secret-handling hole
  and F1 breaks the lint's own control flow, so both were worth the risk of
  a late fix; the rest are better done with room to mutation-verify each.
- **Fixture 76 is deliberately canonical bytes.** If it were
  non-canonical, N-6 would catch it first and N-4 could silently stop
  firing without any fixture noticing — the exact masking F8 describes.
- **Do not rewrite `9229`.** Handoffs are append-only per this repo's
  CLAUDE.md; a child document plus the Tier 1 log carries the correction.
- **Rejected: fixing F3–F9 by inspection without mutation.** Every fix in
  this area needs a mutation showing the gate now bites, because the whole
  class of defect here is "a check that does not fire".

## Evidence & Data

Mutations added this session (each restored, tree clean afterwards):

| # | Mutation | Result |
|---|---|---|
| M9 | disable the new `env` type guard | `76-env-not-an-object.json: was not caught` |
| M10 | disable the JCS-representability guard | lint dies with `FloatDomainError` — the F1 symptom |

`examples/broken-projection/` is now 12 fixtures (66–77);
`EXPECTED_PROJECTION = 12`.

**The seven open findings, with the review's own repros.**

- **F3 · HIGH · the ninth mutation.** There is no NFC fixture; 66–75 cover
  N-2, N-3, N-4, N-5, N-6-JCS, N-7, N-9, N-10, N-12. Neutering the NFC
  check at `bin/projector.py:448` alone leaves `schema-lint: OK` while
  `project()` emits `b"cafe\xcc\x81"` for `working_dir "/srv/café"`. The
  eight mutations in `d699fd6` never reach that check; only the golden
  guards it, and the golden is all-ASCII. **This is the specific claim
  "eight mutations, all caught" overstated — the set was incomplete.**
- **F4 · HIGH · `_shape()` is too weak for N-1.** It erases leaf values and
  reduces a list to `[None]*len`, so a `state` branch may permute a list
  whose order `goal-file.schema.json:101` calls semantic ("An array because
  order is meaning"). Their mutation at `:272` reversed `command` for
  absent entries: lint exit 0, argv reversed after the flip. The golden
  cannot see it either — the only absent entry in the example
  (`com.tendcf.caddy.retired`) is `state`-only, so it has no argv to
  permute.
- **F5 · MEDIUM · N-9 evadable.** `bin/projector.py:139-142` restates the
  schema patterns with Python `re`, where `$` matches before a final `\n`;
  JSON Schema `pattern` is ECMA-262, where it does not. An interlock id
  `"caddy-config-valid\n"` is accepted. `SECRETSPEC_NAME` (`:147`) has the
  same quirk. **Fix is `\Z`, not `$`.**
- **F6 · MEDIUM · two more holes in the parenthetical check**, distinct
  from the `oneOf`-sibling one `505393e` documents. (a) `_refs_along()`
  returns every `$defs` name stepped *through*, so ancestor container defs
  become claimable; (b) `items` is navigation, not a rule, and should not
  be in `APPLICATORS` — the same objection the code's own comment raises
  against `properties`/`additionalProperties`. Verified green: case 43
  `type`→`state_domain`, case 34 `const`→`interlock_map`, case 5
  `if/then`→`items`. Evidence sets are wide — case 24 accepts 10 tokens.
- **F7 · MEDIUM · N-5 misses 3 of the corpus's own 4 device-trust bodies.**
  `TRUST_SHAPED_KEY` (`:152`) fires only on keys spelled
  `ed25519:`/`sha256:`. Only `advisor-key` puts the digest in key position;
  `agent` and `policy-tree` use key `"sha256"` with the digest in the
  value, and `trust-policy` has no digest. So the agent binary pin projects
  with `validate_projection() == []`. A naive "project device-trust too"
  regression is caught for one entry kind, not the domain.
- **F8 · LOW · `check_projection()` mutation coverage is 8/19, and two N-5
  mechanisms mask each other.** Neutering each `flag()` site in turn, these
  survive: `:302` (>5 MiB, N-8), `:358` (no top-level `vars`), `:373`
  (container not in `CONTAINERS`), `:387` (empty container), `:449` (NFC),
  `:465` (trust-shaped key), plus six parse/type guards. `:373` and `:465`
  survive because fixtures 69 and 75 each trip **both** — so the
  closed-container rule that `d699fd6`'s M7 credits with catching the
  tombstone split is **not independently guarded by any fixture**. Note
  their method: bytecode caching had to be disabled or it silently masked
  the first run.
- **F9 · LOW · a docstring is now false.** `bin/schema_lint.py:382` says
  "Every `.json` fixture on disk is canonical bytes"; it iterates
  `EXAMPLES`, and `OUTPUT_ONLY_EXAMPLES` now removes `host_specific.json`
  from that set. Coverage is fine — `check_projector_golden()` byte-compares
  and re-runs `validate_projection()` — it is the comment that is wrong.

**Attacks that failed** (worth not repeating): `$`/`@` escapes to
hide `$(`/`@{` (caught twice, once after parse and once by the JCS byte
compare); duplicate keys; a top-level `variables` or `classes` sibling;
pretty-printing; a trailing newline; a float anywhere; a non-string `env`
value; a device-trust *container* name; the whole goal file under `vars`; a
duplicate id across kinds. Mutating `PROJECTING_KINDS`, `CONTAINER_PREFIX`,
`MAX_PROJECTION_BYTES` or the id patterns is caught by the golden or a
fixture. `_refs_along()` could not be made to walk into the wrong subtree.

## Operator Feedback

Unchanged from `9229` — the four scoping answers still bind (opinion panel
then adjudicate; `bin/projector.py` as reference implementation; the
four-item queue; scope tendcf + nix2cf, broad only if genuinely dry and
confident it is useful). Standing authorization to commit and push.

Explicitly asked for this handoff. Also, from `9229` and still true: the
operator wanted subagent-driven work while away, and permitted self-directed
`/compact`.

**The wall-clock note bears repeating because it is easy to misread the
commit timestamps:** the ~6h autonomous window was requested at 00:50; about
90 minutes of real orchestration ran, the machine slept, and the session
resumed at 12:11 the same day. Elapsed time, not work done.

## Where We're Going

1. **THE NEXT ACTION: fix F3.** It is the ninth mutation — the one hole
   where the gate stays *green* while the projector emits bytes the mapping
   forbids. Add an NFC fixture to `examples/broken-projection/` (78),
   bump `EXPECTED_PROJECTION` to 13, add its README row, then mutation-verify
   by neutering `bin/projector.py:448` and confirming the lint goes red.
   Until this lands, "the projector gate is mutation-verified" is not a
   claim anyone should make.
2. **F4** — strengthen N-1 beyond `_shape()`. It must compare list *order*,
   not just length. Consider comparing the full document with only the
   flipped entry's `state` normalised, rather than erasing all leaves.
3. **F5** — replace `$` with `\Z` in `ENTRY_ID_PATTERNS` and
   `SECRETSPEC_NAME` (`bin/projector.py:139-147`). Small and mechanical.
4. **F7** — make N-5 detect trust content in values, not only key position.
5. **F6** — narrow `_refs_along()` to the def carrying the failing keyword,
   and drop `items` from `APPLICATORS`.
6. **F8** — give `:373` and `:465` each an independent fixture so they stop
   masking each other; consider a coverage check that neuters each `flag()`
   site, since that is what found this.
7. **F9** — correct the docstring at `bin/schema_lint.py:382`.
8. **device-trust's destination** — still the top open DESIGN question
   (`projector-reconciliation-2026-08-16.md` §11). P-1 removed it from the
   projection; R21's third arrow names "the agent's own config", a file
   whose format is specified nowhere. F7 is a good reason to settle it.
9. **The generic bundle** — the `.cf` that reads `tendcf_service` and
   renders promises from `state`. C-1 makes this load-bearing: the
   negative-promise lists are the bundle's to iterate.
10. **nix2cf** was in approved scope and never touched.
11. Unrelated, carried from `ad4c`/`0b22`/`7b18`/`4a48`/`b0ff`: confirm
    `track-issue-activity.yml`'s Discussion path fires in site-djbclark.
12. Unrelated: `~/src/cfengine-core` still shows ` M libntech` — do NOT
    commit it. libntech#291, cfengine/core#6293, #6294 are filed.

## Quick Start

```bash
cd /Users/djbclark/src/tendcf && git log --oneline -6
bin/schema_lint.py    # OK (8 schemas, 59 negative, 6 byte-class, 12 projection)
bin/xref_lint.py      # 0 findings, 28 live / 56 frozen

# The seven open findings, with repros:
sed -n '/^### F3/,$p' docs/paper/reviews/2026-08-16_opus-5-high_projector-gate-review.md

# F3, the next action — confirm the hole is real before fixing it:
python3 - <<'EOF'
import importlib.util, json, copy
s=importlib.util.spec_from_file_location("p","bin/projector.py")
m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
g=json.load(open("examples/goal-file.json")); d=copy.deepcopy(g)
d["domains"]["supervision"]["entries"]["service"]["com.tendcf.caddy.main"]["working_dir"]="/srv/café"
print(m.validate_projection(m.project(d)))   # expect a finding; NFC guard is live
EOF

# Mutation discipline — commit the fix FIRST, then mutate, then restore.
# This was violated twice in one session and cost real rework.
git add -A && git commit -m "..."      # fix committed
python3 -c "...neuter one check..."    # mutate
bin/schema_lint.py                     # must go RED, for the right reason
git checkout bin/projector.py          # restore
```
