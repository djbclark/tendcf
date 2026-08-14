---
schema_version: 1
handoff_id: 8671
parent_handoff_ids: [601f]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: N/A (plain repo checkout, not an ops-worktrees task workspace)
branch: master
head_sha: 94cbff0e760c0a492ba4d24c377d3121407f2924
created_at: 2026-08-13T12:44:44-0400
writer: claude-code
---

# Handoff — R13/D16 back-propagation + the D22 platform reorder

## The Goal

Resume chain `standalone-3fd9` and make `architecture-DEFINITIVE-v2.md`
internally consistent after D16 was decided across four commits that
recorded their conclusions in only two places (§4.5.1 and the register
row), leaving the rest of the document describing the pre-decision state.

Scope grew mid-session. It started as two items the operator selected from
the resume plan — audit R13/D16 back-propagation (item 1) and fold the
Bcfg2-derived items into scope (item 4) — with items 2 (stayturgid issue
triage) and 3 (augments validation) explicitly waived. After the first
pass the operator asked to "fix all of that and make it consistent,"
which pulled in the §12 build order, and then reordered the platform
sequence outright, which became D22.

## Where We Are

**Done and consistent.** Three commits, all pushed to `origin/master`.
The architecture document is now internally consistent; verified
mechanically, not by eye (see Evidence).

| Commit | What |
| --- | --- |
| `2923935` | R13/D16 back-propagation — nine fixes |
| `51d2ae3` | Bcfg2 items folded in as schema, not deferred |
| `94cbff0` | D22 platform reorder, macOS → Android → Linux |

Working tree clean at `94cbff0`, `master` in sync with `origin/master`
**except for this handoff commit**, which is local-only by policy (see
Quick Start).

D16 is fully decided (all four sub-decisions). D22 is new this session.
No open blockers on this chain.

## What We Tried

Chronological. This session's failures were scoping and framing errors,
not technical dead ends — worth recording precisely because a future
session will hit the same two.

1. **Nearly deferred the Bcfg2 items on the session log's own
   instruction — wrong, caught by reading the source.** The Tier 1 log
   said "consider folding the Bcfg2-derived items into nix2cf scope when
   it gets a repo," and the obvious move was to file them as future work.
   Reading `bcfg2-papers-2026-08-13.md` §3 first showed the opposite:
   both surviving items are *schema* decisions, and the paper's own
   argument is that they are "one column now and a migration later."
   Deferring them to a repo that does not exist would have guaranteed the
   expensive version. **Lesson: the log's framing of an item is not
   evidence about the item.** Read the doc the log is pointing at.

2. **Scoped the first pass too narrowly and had to be told.** After the
   nine-fix commit I deliberately stopped short of rewriting §12, on the
   reasoning that reordering the build order was beyond a
   back-propagation audit, and flagged it as a next step instead. The
   operator's response was to ask for full consistency. The judgment call
   was defensible but wrong for this operator: when a consistency pass
   surfaces a section that is *wholly* stale (§12 had zero mentions of
   nix2cf across Steps 1–7), flagging it is not a substitute for fixing
   it.

3. **Asked a question that encoded the assumption it should have
   tested — rejected by the operator.** I asked "which platform is
   adapter #2?", offering Android / macOS / don't-fix-the-order, all
   three of which silently assumed Ubuntu stayed adapter #1 because §12
   said so. The operator rejected the question and answered a different
   one: macOS first, Android second, Linux third. **Lesson: when asking
   about an ordering the document already asserts, put the document's own
   assertion in play as an option, or the question inherits the bias the
   audit is supposed to find.**

4. **Considered reordering signed releases earlier; rejected.** The
   macOS-first sequence converges the operator's daily driver — the
   machine §5.2 itself calls the one you cannot easily reimage — before
   the signed-release + typed-executor rollback machinery exists. The
   tempting fix was to move that step earlier. Rejected as scope the
   operator did not ask for; mitigated inside Step 1 instead with a
   dry-run-first posture and the `launchd-writers.yml` lint as the safety
   rail. **This risk is accepted, not solved** — see Where We're Going.

## Key Decisions

### D22 — platform sequence: macOS, Android, Linux (operator, this session)

The decision that made it *cheap* is a distinction the document was
blurring. The pre-mortem correction §12 carried — "prove the Ubuntu path
before investing in Mac Nix" — was reasoning about the nix-darwin
**substrate**, but was being applied to the macOS **adapter**. §5.3
(services are CFEngine-owned on every platform) and §5.2 (nix-darwin owns
substrate only) make those separable.

**Consequence worth not re-deriving: macOS can go first without resolving
§14.1.** Had they not been separable, Step 1 would have been blocked on a
premium-token multi-AI decision. The substrate stays at Step 7 and stays
gated, so the original caution is preserved exactly where it applies.

Two consequences accepted, both stated in the doc rather than buried:

- The adoptability keystone (Linux) is now proven **third**, so the
  portability claim goes longest unvalidated.
- The first machine converged is the hardest to reimage.

**Rejected alternatives:** macOS-second (drags the unresolved §14.1 fork
forward and contradicts §12's own retained rule); "gate on any two
adapters, don't fix the order" (leaves the compiler positionally vague,
reintroducing exactly the indefiniteness the pass was removing).

### R5 split into two halves of different strength

Operator softened one half ("Ubuntu, or maybe a different distro"). Now
recorded as: no-bare-metal-Nix and must-resemble-a-stranger's-box are
**hard and binding**; Ubuntu Server LTS specifically is the **default
answer, not the requirement**, open until §12 Step 4. NixOS stays excluded
by the first half regardless. §5.1 is still written against Ubuntu
throughout and nothing before Step 4 depends on the choice.

### Bcfg2 items land as schema, not deferred work

Contra the session log. New §4.7.1 (release-stamped D18 rows; managed /
`not-yet-migrated` / `deliberately-unmanaged` counted separately) and the
`bcfg2-info buildfile` affordance into §4.4 as Step 3's item (0). The
third item (interlock-as-precondition) was already §4.5.1(c).

### §14 vs R13 reconciled rather than changed

They read as opposed — R13 says design for cheap-model authorship, §14
says four things need premium models — but act on different variables. R13
governs how the system is *designed* so cheap authorship succeeds by
construction; §14 governs where the design is still *undetermined*, where
a cheap model's failure is an unmade decision being improvised, not an
authorship error a schema could catch. Recorded in §14 rather than
altering either.

## Evidence & Data

**Tests: none run.** `tendcf` is documentation-only at this stage —
there is no build, no test suite, and no code to exercise. Verification
was mechanical grep sweeps, listed below.

The nine back-propagation findings in `2923935`, three load-bearing:

1. **§4.1 had none of the three Site Model fields D16 mandates**
   (`provides`/`requires`, `interlocks`,
   `comprehensive`/`opt_out_reason`). Since §12 Step 0 is what builds the
   schemas, the decisions had no implementation path at all.
2. **§4.5.1(b) forward-referenced a mitigation that did not exist** — it
   cited §7.3's ChangePlan as where inferred-edge visibility was "already
   decided," but §7.3's operation fields (`capability`, `resources`,
   `target`, `rollback`, `expiry`, `nonce`) had no notion of edges.
   Ordering provenance added as a required field; exact encoding left
   inside §14.2's scope, since §7.3 is flagged NEEDS-FABLE-5 and
   improvising the IR there is precisely what the doc forbids.
3. **§12 was entirely pre-D13** — `grep -c nix2cf` over Steps 1–7
   returned zero.

The other six: §4.5.1's header still said "three are decided; one remains
open" after (b) landed below it; R13's application list named (d) as its
first application when (b) was decided in the same commit R13 was added
(`78d642a`) and (d) only later (`560f030`), with (b) omitted entirely
despite being the larger application; §7.5 kept the compile-target-only
scope R13 explicitly generalizes and listed the completed `fleet.yml`
audit as prospective work; §0 lacked R13's local-vs-global rule; §1's
diagram showed CFEngine consuming the Site Model with no compile layer;
four §16 entries described D16 as pending, D17 as needing a fix that had
already landed (`2dd3264`), and D18 as rationale-less after it was
re-decided.

Plus one unrelated live defect found in sweep: **§4.1's `adapter` enum
still offered `ansible`** as a legal per-host value after D13 removed
Ansible entirely.

Verification sweeps run at the end, all clean:

```
grep -c "Step 1.5"                          -> 0
grep -n 'adapter.*ansible'                  -> no match
grep -n "Ubuntu Server is the reference"    -> no match
grep -n '^- \*\*Step '                      -> Steps 0..10, no gaps
```

Files changed, all three commits: a single file,
`docs/architecture/architecture-DEFINITIVE-v2.md`. Sections touched: §0,
§1, §2 (R5, R13), §4.1, §4.2, §4.4, §4.5.1, §4.7.1 (new), §5.1, §5.2,
§5.4, §7.3, §7.5, §12 (rewritten and renumbered), §14, §14.1, §15
(D16 row, D22 row new), §16, §16.1.

## Operator Feedback

- **Selective scope, stated tersely:** "Do 1, ignore 2, I dont think it is
  needed, assume 3 works for now, do 4." Waived items stay waived — the
  stayturgid #288/#289/#290 triage should not be re-raised unprompted.
- **Consistency is expected to be total:** "fix all of that and make it
  consistant."
- **Question protocol:** "If you need my input ask one question at a time
  and include practical implications." Honored — one question asked, with
  per-option practical implications and previews.
- **But questions must not smuggle in premises.** The one question asked
  was rejected for being scoped around the document's existing ordering;
  the operator's clarification reordered all three platforms.
- Standing from earlier in this chain, still in force: **auto-commit at
  natural checkpoints without asking** (memory
  `feedback_auto_commit_at_checkpoints`).

## Where We're Going

1. **START HERE: §12 Step 0 — the Site Model schemas.** Write JSON Schema
   for `services.yml` / `roles.yml` / `launchd-writers.yml` **including
   the three D16 fields** (`provides`/`requires` per type, `interlocks`
   per bundle, `comprehensive` + `opt_out_reason` per domain) and the D18
   row schema from §4.7.1 (release stamp; managed /`not-yet-migrated` /
   `deliberately-unmanaged` counted separately). The doc calls this the
   cheapest possible agent work and a good first task under the budget.
   Do **not** re-derive these field designs — they are decided; §4.1 is
   the contract.
2. **Transcribe current reality into the Site Model.** Expect nearly every
   domain to land as `not-yet-migrated`; that is the correct day-one state
   and its count is the build order's progress metric from then on.
3. **Then §12 Step 1 — macOS services adapter.** Render the Mac's
   `com.djbclark.*` / `com.stayturgid.*` launchd services as CFEngine
   promises. Dry-run first, enforce second. Explicitly **not** nix-darwin
   or anything substrate — that is Step 7.
4. **Decide the distro at Step 4, not before.** Open by operator
   direction. R5's hard half binds; Ubuntu Server LTS is the recorded
   default and what §5.1 is written against.
5. **Resolve §14.1 (nix-darwin yes/no) any time before Step 7.** Confirmed
   this session that it does *not* gate Step 1. Premium-token item.
6. **Create the `nix2cf` repo when Step 3 approaches.** Already-decided
   contract to build against: §4.1's three D16 fields, §4.7.1's two D18
   columns, §4.4's `buildfile` CLI.
7. **Watch at Step 4:** inference rules will have been co-designed on
   macOS + Android, both non-FHS-typical. Step 4 is their generality test;
   the doc says expect to revise rules there rather than be surprised.
8. **Accepted, unmitigated risk to revisit if it bites:** the daily driver
   is converged (Step 1) well before the typed executor and signed-release
   rollback machinery exist (Step 6). Current mitigation is posture and
   lint only. If Step 1 goes badly, moving Step 6 earlier is the lever.
9. **Still-unfilled gap, carried from 601f:** no architectural position on
   image-based atomic updates (RAUC / SWUpdate+hawkBit / OSTree) for
   appliance-class devices. §5.5 has an extension point, not a position.

## Quick Start

```bash
cd ~/src/tendcf
git log --oneline -5          # expect 94cbff0 at or near HEAD
git status -sb                # this handoff commit is LOCAL-ONLY, unpushed

# The one file that matters:
$EDITOR docs/architecture/architecture-DEFINITIVE-v2.md

# Orientation, in this order:
#   §0   six things to internalize (R13's local-vs-global rule is #6)
#   §12  build order, Steps 0-10 -- Step 0 is the next action
#   §4.1 the Site Model contract Step 0 implements
#   §15  decision register; D22 is the newest row
```

**Push status:** the three architecture commits (`2923935`, `51d2ae3`,
`94cbff0`) are pushed. **This handoff commit is committed locally and NOT
pushed** — `tendcf` has no `AGENTS.md`/`CLAUDE.md` declaring the
memory-is-data exception that lets `site-private` push handoffs
automatically, so per the handoff skill it waits for the operator. Push
with `git -C ~/src/tendcf push` whenever wanted.

Prior context in this chain, newest first:

- `docs/handoffs/HANDOFF_standalone-3fd9_nix2cf-split-communal-orchestration_2026-08-13_601f.md` (parent)
- `docs/handoffs/HANDOFF_standalone-3fd9_cfengine-nix-architecture_2026-08-13_05f4.md`
