---
schema_version: 1
handoff_id: 405e
parent_handoff_ids: [8671]
lineage: deterministic
chain: [standalone-3fd9]
repo: fleetopia
workspace: N/A (plain repo checkout, not an ops-worktrees task workspace)
branch: master
head_sha: ecb42a1fdb59d6aca552f99b7d14ff04b53b3ecd
created_at: 2026-08-13T13:01:54-0400
writer: claude-code
---

# Handoff — §12 Step 0 schemas, and the nix2cf repo they forced

## The Goal

Resume chain `standalone-3fd9` from handoff `8671` and execute its item 1:
**§12 Step 0 — write the Site Model JSON Schemas** for
`services.yml` / `roles.yml` / `launchd-writers.yml`, including the three
D16 fields from §4.1 and the D18 row schema from §4.7.1. The field designs
were already decided; the instruction was explicit that they must not be
re-derived.

Scope grew by exactly one thing, and it was forced rather than chosen: the
schemas had **no legal home**. D21 (§4.2) says the Site Model schemas are
`nix2cf`'s public contract, but `8671` said create `nix2cf` "when Step 3
approaches." Step 0 is what writes the schemas. That contradiction had to be
resolved before a single file could be written.

**The operator has set the next session's agenda, and it is not Step 0's
remainder — see Where We're Going item 1.**

## Where We Are

**Step 0's named next action is complete.** Two repos, both pushed.

| Repo | Commit | What |
| --- | --- | --- |
| `djbclark/nix2cf` | `f5f01e0` | New public repo. Schemas + lint + fixtures |
| `djbclark/fleetopia` | `ecb42a1` | §4.2 + §12 Step 0 record that the repo exists |
| `djbclark/fleetopia` | `8cd472b` | Handoff 8671, pushed this session (was local-only) |

`nix2cf` working tree clean at `f5f01e0`, `master` tracking
`origin/master`, in sync. `fleetopia` clean at `ecb42a1`, in sync.
Repository is public, Issues enabled by default (matches the standing
preference).

What is **not** done, and is the rest of Step 0: transcribing current
reality into instances, and automating the §8.1 worktree provenance gate.
Neither was started.

No blockers.

## What We Tried

1. **Nearly wrote the schemas without resolving where they live.** The
   obvious move on resuming was to start writing files in `fleetopia`,
   which was already checked out and clean. Reading §4.2 first showed D21
   makes that the wrong home by decision, not by taste: a schema change is
   a `nix2cf` interface change and an instance change is site data, and
   they do not move together. Staging in `fleetopia` would have guaranteed
   a `git mv` later plus a period where the boundary the document asserts
   was false on disk. **This is the same failure mode 8671 recorded — the
   log's framing of an item is not evidence about the item** — and it was
   avoided the same way, by reading the section the log pointed at before
   acting on the log's summary.

2. **Validated report rows against the bare `oneOf`; the errors were
   useless.** The row schema is three row types under a `oneOf`, and a row
   with an enforce-mode `outcome` value from the audit vocabulary produced
   only `is not valid under any of the given schemas`, dumping the whole
   row with no field pointer. That is precisely the error shape **D16(a)
   rules out for the compiler** — resolution needs a human, so the message
   must carry what a human needs. The lint now discriminates on `row_type`
   first and validates against that branch, yielding
   `outcome: 'compliant' is not one of ['success', 'repaired', 'error',
   'n-a']`. The rule was already decided for `nix2cf`; it just had not been
   applied to `nix2cf`'s own tooling.

3. **Trusted a passing lint on a valid fixture — briefly.** `schema_lint.py`
   returned `OK (5 schemas)` on the first run. A lint that passes on
   correct input demonstrates nothing about whether it catches incorrect
   input, so twelve deliberately-broken fixtures were built and each was
   confirmed to fail (numbers in Evidence). Two of the twelve exposed the
   vague-error problem above; without the negative pass, both would have
   shipped.

4. **First `session_log.py write` call was rejected.** `blockers` must be a
   **list of strings**, not a string — the helper validates and refuses.
   Trivial, but it costs a round trip every time someone rediscovers it.

## Key Decisions

### Schema home — `nix2cf` repo created now (operator, this session)

Asked as a single question with per-option practical implications, per the
standing protocol, and with the document's own assertion in play as an
option (the lesson `8671` recorded after its question was rejected for
smuggling in a premise).

**Chosen:** create `djbclark/nix2cf` immediately, holding only its contract.
D21-correct from day one, no later move, and Step 3's compiler lands into a
repo that already holds the contract it implements.

**Rejected:** (a) *stage in `fleetopia`, move at Step 3* — cheapest today,
but guarantees a move and makes `fleetopia` stop being docs-only;
(b) *put them in `site-djbclark` next to `registry_lint.py`* — enforcement
would be free since CI and pre-commit already run there, but it directly
contradicts D21 and would require an `ops-worktrees` task workspace.

**Visibility: public** (operator, this session). Consistent with R10/§11 —
the repo holds no hostname, secret, or fact by design, which is the whole
reason the generic layer is publishable.

### Decided semantics encoded as schema `const`, not prose

An interlock's `blocks: "enclosing-bundle"` and `report: true` are
**required consts**, not author-settable fields. D16(c) fixed the blast
radius and the reporting; leaving them writable would let an author narrow
either one, which is exactly how `stayturgid#289` survived as a safe default
plus a comment. Same reasoning closed the capability-token kind set
(`service|port|path|class|package|device|network|secret`): a closed set
makes `netwrok:tailnet` a schema error, where an open string makes it a
silently-unmatched inference edge — the failure mode D16(b) calls harder to
diagnose than a missing edge. §0 rule 6, machine-checkable over
conventional.

### `opt_out_reason` is forbidden when `comprehensive` is true

D16(d) requires a reason when opting out. The schema also **rejects a reason
on a comprehensive domain** — that combination is a half-finished migration,
and catching it mechanically costs one `if/then` versus relying on review.
Not stated in the architecture document; it follows from it.

### `roles.yml` deliberately carries no `domain_coverage`

Comprehensiveness (D16(d)) is a property of a domain of **device state**.
Roles are intent and assignment; nothing on a device can appear as an extra
entry against `roles.yml`. The absence is documented **in the schema's own
description** so a later reader does not read it as an oversight and "fix"
it.

### `command` is argv, never a shell string

A shell string puts quoting rules between the Site Model and every renderer.
Minor, but it is the kind of thing that is free now and a migration later.

## Evidence & Data

**Tests run: yes.** `bin/schema_lint.py` — three layers (schema validity,
fixture validation, cross-file rules).

- Baseline: `schema-lint: OK (5 schemas)`, exit 0.
- **Twelve negative fixtures, all caught.** Each was applied to a copy in
  the scratchpad, run, and reverted:

| # | Broken input | Caught by |
| --- | --- | --- |
| 1 | `comprehensive: false` with no `opt_out_reason` | schema |
| 2 | `comprehensive: true` **with** an `opt_out_reason` | schema |
| 3 | launchd label `com.rogue.caddy` under no declared prefix | cross-file |
| 4 | prefix `com.djbclark.caddy.*` nested in `com.djbclark.*` | cross-file |
| 5 | macOS service with no `launchd` block | schema (`if/then`) |
| 6 | `OPENAI_API_KEY: sk-live-abc123` (literal, not a key name) | schema |
| 7 | `netwrok:tailnet` (typo'd capability kind) | schema |
| 8 | `role: llm-gatway` (unknown role) | cross-file |
| 9 | enforce-mode row with `outcome: compliant` | schema (discriminated) |
| 10 | `release: v1.3.2` (missing `ops-` prefix) | schema |
| 11 | `domain_coverage` row missing `deliberately_unmanaged` | schema |
| 12 | `row_type: converged` (unknown row type) | lint discriminator |

Findings 9 and 10 initially reported only "not valid under any of the given
schemas"; after the `row_type` discriminator they report the offending
field and value. That change is the second entry in What We Tried.

**Files created** — all in `~/src/nix2cf` (commit `f5f01e0`):

```
schema/common.schema.json            shared defs incl. all three D16 fields
schema/services.schema.json          domains, bundles+interlocks, services
schema/roles.schema.json             role -> {main, backups[], peers[]}
schema/launchd-writers.schema.json   one writer per label prefix
schema/report-row.schema.json        D18 rows: promise_outcome,
                                     domain_coverage, device_convergence
bin/schema_lint.py                   uv-script header, exit 0/1/2, matching
                                     site-djbclark's registry_lint.py pattern
examples/{services,roles,launchd-writers,report-rows}.yml
README.md                            the contract's rationale, not a tutorial
.gitignore
```

**Files changed in `fleetopia`** (commit `ecb42a1`): one file,
`docs/architecture/architecture-DEFINITIVE-v2.md`, §4.2 and §12 Step 0 only.

**Contract details worth not re-reading the schemas for:**

- `contract_version` on every file. Bumped **only** on rename/retype/remove
  of an existing field; adding an optional field never bumps. Reused
  verbatim from `site-djbclark`'s `registry/ports.yml` rule rather than
  invented.
- `release_stamp` pattern: `^ops-v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$`
- Enforce outcomes `success|repaired|error|n-a`; audit outcomes
  `compliant|noncompliant|error|n-a` — ncf's vocabulary kept verbatim per
  §4.7.
- `promise_outcome` rows carry optional `blocked_by_interlock`: an entry
  not modified because a pre-action failed is **not** an error and must not
  be counted as one.
- `device_convergence` rows carry required `complete: bool` — a partially
  converged device must not read as converged.

## Operator Feedback

- **Chain selection:** five chains existed; the operator picked
  `standalone-3fd9` from the table rather than being asked for a path.
- **One question, answered once each time.** Two questions were asked this
  session (schema home, then visibility), both single, both with
  per-option practical implications, both answered without pushback — the
  protocol from `8671` continues to hold.
- **Standing, still in force:** auto-commit at natural checkpoints without
  asking (`feedback_auto_commit_at_checkpoints`); `~/ops` is deploy-only,
  code work happens in `~/src/ops-worktrees` (`feedback_ops_worktrees_only`);
  Issues stay enabled on all repos.
- **New directive, sets the next session's agenda:** write an academic
  paper about the architecture, in the style of the papers in
  `~/src/bcfg2/doc/papers`, **not too long**. Stated purpose: the operator
  is a friend of **Narayan Desai** — Bcfg2's author and co-author of those
  papers — who "would see holes in the plans even AI might miss."

## Where We're Going

1. **START HERE — write the architecture paper.** In the style of
   `~/src/bcfg2/doc/papers/`: `bcfg-cluster2003.pdf`, `desai_lisa05.pdf`,
   `desai_lisa06.pdf`, `19_bcfg2.pdf`. **Not too long** — those are short
   conference papers, and the operator said so explicitly. The audience is
   one specific expert reader, and the paper's job is therefore **to expose
   the design to a hole-finder, not to sell it.** A version that reads as
   advocacy wastes the review. Three consequences for how to write it:
   - **Lead with the joints where this design departs from Bcfg2, and say
     why.** The sharpest one: §4.5.1(b) builds a dependency *inference*
     stage, while Bcfg2's answer to ordering is deliberately to have no
     dependency graph at all — a fixpoint retry loop plus bundles as the
     re-verify scope (`bcfg2-papers-2026-08-13.md`). We are adding
     machinery its author chose not to build, and R13 (AI authorship) is
     our entire reason. That argument deserves to be stated in its
     strongest form and handed over, not defended.
   - **State the empirical position honestly, because it is weak and he
     will find it instantly.** Nothing is deployed. Zero devices have been
     provisioned from factory reset, so D16's rejection of the Puppet
     catalog path rests on reasoning about a cold path that has never been
     executed (§4.5, "pending confirmation by a real from-scratch
     provision"). The LISA papers report *deployment experience with
     numbers*; this paper cannot, and should say so in its own words rather
     than let the reader discover it.
   - **Credit what is borrowed, precisely.** Two-way verification and the
     `0 managed / 2308 unmanaged` framing (CLUSTER '03 §2.2); revision-
     stamped client reports mapped onto `ops-v*` tags (LISA '06);
     failing-pre-action-blocks-bundle as the interlock shape (Actions,
     booklet §A.2.1); decision transparency as the thing that buys
     administrator trust (LISA '05 §5). The mining is already done in
     `docs/architecture/bcfg2-papers-2026-08-13.md` — do not redo it.
   - Other likely-productive holes to put in front of him rather than
     around: local-first SQLite as record of truth (D18) when his systems
     centralized statistics and had a consumer for them; whether
     `not-yet-migrated` counts actually get ground down in practice or just
     accumulate; whether per-domain `comprehensive` is the right
     granularity; and whether R13's cost inversion is an argument or a
     hypothesis.
   - Suggested home: `docs/paper/` in `fleetopia`. Format is an open
     question — the sources are PDFs, so there is no LaTeX skeleton to copy
     from in that directory. Ask before committing to one.
2. **Rest of §12 Step 0 — transcribe current reality into instances.**
   `registry/services.yml`, `roles.yml`, `launchd-writers.yml` in
   `site-djbclark`, validated against `~/src/nix2cf/schema/`. **In an
   `~/src/ops-worktrees/` task workspace, never in `~/ops`.** Expect nearly
   every domain to land `comprehensive: false` /
   `opt_out_reason: not-yet-migrated`; that count is the progress metric.
3. **Wire the schemas into the existing gate.** Extend
   `site-djbclark/bin/registry_lint.py` (add a `jsonschema` dep) to validate
   the three new registry files, so they are gated in CI and pre-commit the
   way `ports.yml`/`paths.yml` already are.
4. **Automate the §8.1 worktree provenance gate** — the other half of
   Step 0, untouched this session.
5. **Then §12 Step 1 — macOS services adapter.** Render
   `com.djbclark.*` / `com.stayturgid.*` launchd services as CFEngine
   promises. Dry-run first, enforce second. Explicitly **not** nix-darwin
   or substrate (Step 7, gated on §14.1).
6. **Unchanged carries:** distro choice stays open until Step 4; §14.1 does
   not gate Step 1; `stayturgid#288/#289/#290` stay waived and should not be
   re-raised unprompted; still no architectural position on image-based
   atomic updates (RAUC / SWUpdate+hawkBit / OSTree) for appliance-class
   devices — §5.5 has an extension point, not a position.

## Quick Start

```bash
# The paper's source material (PDFs — read them, don't re-mine the notes):
ls ~/src/bcfg2/doc/papers/
#   bcfg-cluster2003.pdf  desai_lisa05.pdf  desai_lisa06.pdf  19_bcfg2.pdf
# Already-mined notes, do NOT redo:
$EDITOR ~/src/fleetopia/docs/architecture/bcfg2-papers-2026-08-13.md

# The architecture the paper describes:
$EDITOR ~/src/fleetopia/docs/architecture/architecture-DEFINITIVE-v2.md
#   §0   six things to internalize
#   §4.1 / §4.5.1  the Site Model contract + the four D16 sub-decisions
#   §12  build order, Steps 0-10
#   §15  decision register (D22 newest)

# The contract written this session:
cd ~/src/nix2cf && ./bin/schema_lint.py     # expect: OK (5 schemas), exit 0
git log --oneline -1                        # f5f01e0

cd ~/src/fleetopia && git log --oneline -3  # ecb42a1 at HEAD, clean, pushed
```

Gotcha for whoever writes the next Tier 1 entry: `session_log.py write`
requires `blockers` as a **list of strings**, not a string — it exits 1
otherwise.

Prior context in this chain, newest first:

- `docs/handoffs/HANDOFF_standalone-3fd9_r13-d16-backprop-platform-reorder_2026-08-13_8671.md` (parent)
- `docs/handoffs/HANDOFF_standalone-3fd9_nix2cf-split-communal-orchestration_2026-08-13_601f.md`
- `docs/handoffs/HANDOFF_standalone-3fd9_cfengine-nix-architecture_2026-08-13_05f4.md`
