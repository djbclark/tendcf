# E1 adjudicated: adopt the diff-derived ChangePlan, with a named residue

**Date:** 2026-08-15. **Author:** Claude Opus 5 (adjudication pass), from the
full 2026-08-15 review corpus, the guide, the map, and the CFEngine
feasibility note. **Status:** verdict, with conditions. This note decides the
fork; it does not edit the guide or the map, and the map's §14.2 gate
(independent adversarial review before the ChangePlan artifact is built)
still applies to what this verdict selects.

**Verdict: adopt Model B.** The compiler does merge → conflict-check →
render; the render is a complete per-host goal file; the ChangePlan is the
diff between the currently-signed goal file and the proposed one; the
executor is a pre-flight validator over that diff. The next work item becomes
**one** schema — the goal-file/diff/approval-record family — not two.

The verdict is conditional on the residue list in §5 being carried as design
obligations, because the synthesis's dissolution table is right in direction
and wrong in arithmetic: two of its seven rows overstate what dissolves, and
its concession list (TC-23, TC-25) is incomplete — **TC-31 belongs on it**,
relocated rather than dissolved. The strongest case against the verdict is
§6, and it is actionable.

---

## 1. The question, and the standard applied

The fork: Model A (guide §7 as written — inference stage, hand-maintained
closed capability vocabulary, executor gates operations against the
vocabulary) versus Model B (synthesis E1 — no inference, complete rendered
goal file per host, plan = diff of two signed goal files, allowlist derived
from the diff).

The standard: not "which did more reviewers like," but (a) is the claimed
independent convergence real or an artifact of a shared unexamined premise;
(b) does the dissolution table survive checking each row against the
red-team's actual text; (c) what does B cost that nobody priced, because both
source reviewers were arguing for cutting scope, not hunting B's own failure
modes; (d) how the CFEngine feasibility findings land on each model.

## 2. The convergence is real, but narrower than the synthesis says

The synthesis (E1) states that the skeptical review's Alternative A and the
pre-mortem's CUT-1 + CUT-3 "are the same architecture." Checked against the
source texts, they are the same **compiler** and not the same **executor**:

- **Agreed** (genuinely independent, from opposite premises): cut the
  inference engine and origin machinery, keep `provides`/`requires` as
  fields (CUT-3 explicitly; Alt A implicitly); the complete per-host render
  is the artifact of record; the plan is the diff of that render
  (Alt A: "mechanically derived"; CUT-1: "keep the ChangePlan as a readable
  artifact — it is the Step 3 render").
- **Not agreed:** Alternative A derives the *executor's allowlist* from the
  diff and keeps enforcement. CUT-1 cuts on-device enforcement **entirely**
  — plus the nonces, high-water marks, emergency role, offline root, and
  rotation ceremony — on the argument that enforcement has no value under a
  single-operator threat model. Model B as posed in the synthesis is
  Alternative A's executor grafted onto the jointly-agreed compiler. That
  graft is the synthesis author's composition, not a second independent
  arrival.

So: convergence on the compiler half is strong evidence — two reviewers, one
from "the security claims don't bind to anything the reader can inspect," one
from "the build cost is 2.5–5 years," both landed on *the render the design
already promises is the real object*. Convergence on the executor half is
**one** reviewer's design.

Was there a shared prior neither examined? The premise both reviewers share
is the guide's own §4: the render is a pure function producing a complete
per-host artifact, "almost free," "the first piece of the compiler." That is
the design's most-examined, most-buildable commitment, not a hidden
assumption — both reviewers pulled the same thread because the design
contains it. Which reframes the fork usefully: **the current design already
builds Model B's substrate.** The capability vocabulary is a second,
hand-maintained description of the same change, layered on top of a complete
mechanical one, plus an obligation to prove the two descriptions correspond.
Model A = Model B + a parallel vocabulary + a correspondence proof.

The genuinely unexamined shared assumption is different, and neither reviewer
tested it: **that the diff of a complete goal state is reviewable by the
person and their advisor at accept time.** Alternative A concedes "releases
get larger and diffs noisier" as a cost and never treats it as a security
problem. It is one — see §6.

## 3. The dissolution table, audited per row

Against the red-team's actual text (findings quoted by number from
`2026-08-15_opus-5-max_redteam-trust-consent.md`):

| Row | Synthesis's claim | Audit |
| --- | --- | --- |
| TC-29 (baseline mismatch on a stale device) | "A diff **is** baseline-declaring by construction" | **Holds, and is understated.** A diff of two signed goal files inherently names its base; base-hash refusal is DC-13 for free. Better: because goal states are total, a catch-up plan for a device at N−7 is `diff(goal[N−7], goal[N])` — well-defined without composing intermediate op-lists, which under Model A is not well-defined at all. Condition: the executor must actually check the base hash, and the design must pick where the diff is computed (see §5.2). |
| TC-32 (no capability vocabulary exists) | "No vocabulary to cover" | **Mostly holds.** The enum, its coverage problem, and the correspondence proof disappear. But "what is not in the diff cannot be done" repeats §7's overclaim one level down: what is not in the diff is not *proposed*; what is in the diff can still do anything at effect level (TC-23). And a goal-file schema, diff format, and approval record must still be written, with negative fixtures — TC-32's real demand ("write the artifact") is unchanged, just pointed at one schema instead of two. |
| TC-31 (unknown/deprecated capabilities, skew) | "Same — no vocabulary, no skew" | **Does not hold. Relocated, not dissolved.** The goal-file schema is itself versioned in effect. An old executor receiving a goal file with an entry kind it does not know faces exactly TC-31's dilemma: ignore-unknown is fail-open (the operator believes a state enforced that nothing enforces), refuse is fail-closed behind a schema update. Worse, a schema migration makes the cross-version diff *total* — every line changes, the briefing says "everything changed," and the person rubber-stamps it. DC-15's content (version the vocabulary, refuse unknown with a distinct reason, forward-only) transfers to the goal-file schema nearly verbatim. This row belongs in the concession list next to TC-23 and TC-25. |
| TC-10 (all-or-nothing accept) | "A diff is naturally per-hunk" | **Half holds.** True at the format level: hunk-vector accept is natural and kills the bundling *negotiation* (the proposer can no longer make refusing the rider cost the patch). But a partial accept synthesizes a goal state the compiler never rendered and never conflict-checked — the same defect skeptical G1 found in personal branches. Safe partial application needs hunk dependency-grouping or a refused-hunks → re-render → re-check loop. Real work, unpriced in the table. |
| TC-26 (plan binds names, not bytes) | "A complete goal file names values, not references" | **Holds for one class, fails for the class TC-26 was about.** File content: genuinely dissolved — content is in the goal state, the diff shows the bytes (or their digest). Packages and fetched artifacts: the goal file says `caddy 2.8.4`, which is a name and a version; the package manager fetches from a repo; the substituted-artifact attack of TC-26 ("a different APK with the same declared identity") is untouched. DC-11 survives as "digests in the goal file for everything fetched." |
| TC-25 (a plan can rewrite the trust policy) | "Still needed — the diff can still touch it" | **Concession accurate.** Note the *shape* of the residue: a privileged-resource classifier over goal-file paths and entries — i.e., a small vocabulary reappears (see §4). |
| TC-23 (refuses declarations, not effects) | "Still unsolved" | **Concession accurate**, and confirmed independently by the CFEngine note: no runtime confinement exists in either model; closing it needs OS-level sandboxing, out of scope. |

Two things the table omits that cut the other way — B has unclaimed
advantages inside the same findings list:

- **TC-09 / TC-47 (nobody holds the aggregate).** Under Model A the executor
  sees an op list; the aggregate privilege state is nowhere. Under Model B
  the executor holds, by construction, the complete current state and the
  complete proposed state — the aggregate *is* the artifact. DC-7's
  "executor computes privilege transitions and hands them to the advisor as
  facts" goes from new machinery to a function over two documents in hand.
- **TC-24 (policy channel outside the plan).** The generic bundle and any
  `.cf` are files; under B they can be entries in the goal state, so a policy
  change appears in the diff like anything else. Model A needs a separate
  digest-binding mechanism (DC-10) to get the same property.
- **TC-28 (rollback unconstrained).** Under B, rollback has a natural
  definition Model A lacks: revert to a prior *signed complete state*,
  briefable as a diff like any forward change.
- **TC-38 (group membership invisible in the target's diff).** The red-team's
  own fix — "groups compile away to explicit device keys so membership
  changes appear in the target's plan diff" — presupposes B's artifact. Under
  A there is no diff for it to appear in.
- **TC-45 (two lists named "capability")** half-dissolves: the operation
  vocabulary no longer exists to collide with `capability_token`.

Net: the table overstates three rows and omits four favorable ones. The
direction survives honest accounting; the arithmetic in "structurally
dissolves a large slice" does not, and anyone quoting the table should quote
this audit with it.

## 4. "No vocabulary, so nothing to attack" — relocated, and genuinely smaller

A diff of a goal file has a schema and semantics an executor must interpret.
The honest statement is: **the goal-file schema is the vocabulary.** Its
entry kinds (service, file, package, …) are the capability classes; its
semantics are whatever the generic bundle does with an entry; the validator
must understand at least entry identity and canonical form; and the TC-25
residue requires a policy naming which goal-file regions are privileged —
a vocabulary of privileged resources, reborn small.

Why this is still a large real win rather than an accounting trick:

1. **One schema instead of two plus a proof.** Model A maintains the render
   schema (needed regardless — it is what the device consumes), the
   operation vocabulary, *and* the correspondence between them ("does
   `service.install` on X actually describe what the policy will do to X?").
   That correspondence proof is the artifact the CFEngine note identifies as
   "a new mechanism" nobody has ever specified, and it is where TC-31's skew,
   TC-32's absence, and §19 Q8's escape hatch all live. Under B it does not
   exist because there is nothing to correspond: the reviewed object and the
   enforced object are the same bytes.
2. **The remaining vocabulary is a *policy over* a mechanical artifact, not a
   parallel *description of* it.** A wrong or missing privileged-path rule
   under B fails soft: the diff is still complete and accurate, just
   under-labeled. A wrong capability mapping under A fails hard: the plan
   misdescribes the change while the executor certifies the description.
3. The goal-file schema is on the build path under both models. B's schema
   count is A's minus one.

## 5. What the CFEngine note changes, checked

The note's core finding — CFEngine has no runtime capability confinement, so
the §7 gate must become a **pre-flight validator** under either model — was
worth checking because, if it equalized the models, it would remove B's
claimed executor advantage. It does not equalize them; it is the strongest
single argument *for* B, because the validator's cost is wildly asymmetric:
under A it is a capability-vocabulary interpreter plus the correspondence
proof of §4; under B it is a comparison of two JSON documents against an
approved diff, no policy interpretation. The note says this plainly and the
claim survives scrutiny.

Three caveats from the note that the E1 text glosses:

1. **`--simulate` is not the mechanism.** It covers files and packages only,
   is silent on service activation, and has no machine-readable output in any
   mode (the structured records die with the chroot). The device-computed
   diff, if wanted, is tendcf-agent code diffing two goal files (the note's
   option 3), with `--simulate` as human-facing confirmation and an upstream
   `--simulate-output=json` issue filed as the better long-term path.
2. **Where the diff is computed is an open design choice B must make.**
   Compiler-side (diff of two signed renders, base hash bound in the plan,
   executor refuses on mismatch) preserves ahead-of-time rendering and gets
   TC-29's refusal by construction; catch-up diffs are generable on demand.
   Device-side (release ships the full proposed goal file; the device diffs
   against its own current signed state and briefs on that) makes the
   briefing exact for any staleness and is the only variant that moves any
   artifact in the consent flow off the proposer's side of the line — but it
   kills pre-generated briefings and puts the advisor round-trip after
   device contact. Recommendation: **ship the full goal file as the release
   artifact; compute the briefed diff device-side; keep the compiler-side
   diff as the review-time preview.** The full-state artifact is what makes
   both available.
3. **S2 is not fixed and B should not claim it.** The diff-computing code,
   the validator, the policy, and the keys still all ship from the operator.
   B improves what the person is shown; it does not change who authors the
   machinery that shows it. The red-team's class fix (DC-1, the device-local
   trust root the release cannot write) is untouched by this fork and still
   required.

## 6. What Model B costs that Model A does not

These are B's own failure modes. Neither source reviewer was looking for
them; the synthesis does not carry them; they are the conditions on this
verdict.

1. **Canonicalization becomes a security property, not a testing nicety.**
   Skeptical G7 asked for a canonicalization rule so the pure-function claim
   is testable. Under B that rule is load-bearing for consent: two
   semantically identical goal files that serialize differently produce a
   diff full of noise, and noise is camouflage. The rule (stable key order,
   stable list order, fixed number/string forms, nonce/signature fields
   outside the diffed object) must be in the schema, with negative fixtures,
   before the first diff is briefed.
2. **Fan-out noise is a consent-fatigue and camouflage channel.** A shared
   fact touches N goal files; a one-line site change can legitimately produce
   a 400-hunk diff, inside which one malicious hunk hides — TC-09's fatigue
   attack rebuilt on B's own artifact. The mitigation is hunk *attribution*:
   each hunk carries which source-layer change produced it, so the briefing
   can say "397 hunks ← shared fact F changed in commit C; 3 hunks ←
   unattributed." Note honestly: this is origin-tracking reborn at the value
   level. Cheaper than edge-inference origin machinery, but not zero, and it
   was on CUT-3's cut list. It comes back, smaller.
3. **Two events produce a total diff, and a total diff is a rubber stamp:**
   first adoption of a host (the §11 transcription pass — the entire goal
   file is new), and any goal-file schema migration (§3, TC-31 row). Both
   need a distinct consent class — "this is a baseline/migration accept, the
   diff is not reviewable line-by-line, here is what that means" — rather
   than pretending a 5,000-hunk diff was reviewed. Migrations additionally
   need the rule: migrate-then-diff (compute the diff after applying the
   schema migration to the old state), so the briefed diff shows semantic
   change only. This must be specified in the schema family from day one.
4. **Per-hunk accept needs a coherence mechanism** (§3, TC-10 row): either
   hunk dependency-groups in the diff format, or the rule that a partial
   accept returns to the compiler as a constraint and a re-rendered,
   re-conflict-checked plan comes back. Choose one; do not improvise it in
   the executor.
5. **Packages still bind names.** Digest fields for fetched artifacts are
   still a schema obligation (TC-26 residue), and the accept must cover them.
6. **The classification layer will grow, and must be watched.** Briefing
   quality, TC-25's privileged class, TC-42's tier changes, and DC-33's
   binding edits all pull toward labeling hunks by kind. That is fine as a
   *derived, advisory* layer over the mechanical diff. The failure mode is
   letting labels become the thing the executor gates on — at which point the
   capability vocabulary has been rebuilt as a taxonomy with the same
   coverage problem, minus the honesty of having named it. The gate stays:
   approved diff, byte-for-byte, against base hash. Labels inform the
   advisor; they never widen what the validator accepts.

## 7. The verdict, and its edges

**Adopt Model B**, defined precisely as:

- Compiler: merge → conflict-check → render, complete per-host goal file.
  No inference stage, no `nix2cf_edges`, no edge-origin machinery.
  `provides`/`requires` remain as schema fields (documentation + lookup CLI
  + a future engine if the §9 experiment ever justifies one) — CUT-3's
  keep-the-fields form, exactly.
- Release artifact: the full signed goal file (per §5.2's recommendation),
  plus the compiler-side diff as the review-time plan.
- ChangePlan schema = canonical goal file + diff format (base hash, hunks,
  hunk attribution, dependency groups) + approval record (accept vector,
  advisor signature binding per DC-2). **One schema family. The "build both
  candidates and compare" hedge is closed.**
- Executor = pre-flight validator: current signed state + approved diff ⟹
  proposed state, byte-checked, base-hash-bound, privileged-region policy
  consulted, artifact digests re-verified at apply. No runtime confinement
  claimed (§7's "refuses any effect" is rescoped under either model —
  TC-23).
- Signing, TUF-subset, consent surface: **unchanged by this fork.** CUT-1's
  further cut (drop enforcement, nonces, root, high-water marks) is a
  threat-model retreat, not part of Model B, and is explicitly not adopted;
  the red-team corpus (TC-15…TC-22, TC-34…TC-37, DC-1…DC-8) applies to B
  in full.

Edges and follow-ons:

- The guide's §7, §10, §15-adjacent text and the map's §9/§14.2 wording
  describe Model A and will need edits under the map's `Approved-change`
  gate. Not done here; this note is the input to that change, not the
  change.
- The map's §14.2 rule — independent adversarial review before the ChangePlan
  artifact is built — applies to the diff-plan schema family with fresh
  force, because §6's failure modes (canonicalization, camouflage, total-diff
  rubber stamps) are exactly the kind of thing a red-team should hit before
  code exists.
- E3 (the two-platform inference gate) is mooted by cutting the engine;
  the §9 falsification experiment (DC-41) remains worth running someday, but
  it is no longer on the critical path and no longer gates anything.

## 8. The strongest case against, stated plainly

If you disagree with this verdict, the objection to act on is this:

**Model A's capability classes are semantic units of consent; Model B's hunks
are not.** "This plan performs one `service.install` and nothing else" is a
sentence a person can hold. "This plan is 41 hunks across your goal file" is
not, and everything that makes it holdable — canonicalization, attribution,
hunk classification, privileged-region labeling — is derived machinery that
§6 admits must be built and that collectively re-approaches the vocabulary's
complexity. Meanwhile B's skew story (§3, TC-31 row) is *worse* than a
versioned enum's: a fleet that is offline for months and a schema that is
young and changing means recurring migration events whose diffs are total,
and a consent surface that periodically degrades to "trust me, it's a
migration" is training the person to rubber-stamp — the precise failure §8
of the guide exists to prevent. If schema churn turns out high and the
labeling layer turns out load-bearing, you will have rebuilt Model A as an
unacknowledged derived layer, and the honest response would have been to
build the vocabulary deliberately, versioned and reviewed, as DC-15/DC-16
specified.

I land against this objection for one structural reason: the failure modes
are asymmetric. B's derived labels can be wrong and the underlying artifact
is still complete, mechanical, and checkable — degraded review, intact
enforcement. A's authored vocabulary can be wrong and the artifact itself
misdescribes the change while the executor certifies it — intact ceremony,
broken enforcement. And A must build B's render anyway (§4 calls it the
compiler's first piece), so the vocabulary is purchased *in addition to*
everything B needs, to obtain labels B can derive. But the objection is
real, it is falsifiable (count migration events and unattributed-hunk rates
once real diffs exist), and §6.6's rule — labels never widen what the
validator accepts — is the tripwire to watch.

## Sources

All in-repo, read in full 2026-08-15:

- `docs/paper/tendcf-architecture-guide.md` (the design; §4, §7, §10, §11,
  §15, §18, §19)
- `docs/architecture/architecture-DEFINITIVE-v3.md` (§9, §14.2, D30, D41/D42)
- `docs/paper/reviews/2026-08-15_opus-5-xhigh_SYNTHESIS.md` (E1 at §2, the
  dissolution table, DC-16/DC-40, §6 items 1 and 4)
- `docs/paper/reviews/2026-08-15_opus-5-xhigh_skeptical-review.md`
  (Alternative A, Claims 1–3, G1, G5, G7)
- `docs/paper/reviews/2026-08-15_opus-5-high_premortem.md` (CUT-1, CUT-2,
  CUT-3, the demotion, §3.3)
- `docs/paper/reviews/2026-08-15_opus-5-max_redteam-trust-consent.md`
  (TC-01…TC-51 read in full; rows audited in §3 quoted by number)
- `docs/architecture/cfengine-feasibility-of-diff-plan-2026-08-15.md`
  (body and addendum; addendum treated as controlling where they differ)
