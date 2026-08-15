# E1 re-adjudicated at xhigh: Model B confirmed, the open choices closed

**Date:** 2026-08-15. **Author:** Claude Fable 5 (xhigh), independent pass.
**Method:** the full corpus (guide, map, red-team, skeptical review,
pre-mortem, synthesis, CFEngine feasibility note with its addendum treated as
controlling, `schema/` + `examples/` + `bin/schema_lint.py`) was read in full
and a complete verdict — including the convergence check, a dissolution-table
audit, a residue list, and all six schema-family decisions — was written down
**before** opening `e1-adjudication-2026-08-15.md`. §§1–3 and §5 of this note
are that unanchored pass, edited only for prose; §4 is the delta against the
prior verdict. **Status:** verdict plus binding design decisions for the
schema family. This note does not edit the guide or the map; it is the input
to those edits.

**Verdict: adopt Model B, independently re-derived.** Compiler = merge →
conflict-check → render of a complete per-host goal file; ChangePlan = the
diff between the currently-approved goal file and the proposed one; executor
= a pre-flight validator over that diff. The inference cut is endorsed and is
severable (the fields stay; DC-41's experiment can revive the engine; B does
not logically depend on the cut). The two adjudications converge on the
verdict, on the corrected convergence claim, and on most of the
dissolution-table audit — which is the outcome the second pass existed to
test. Where they diverge is in §4; the decisions the prior pass left open are
closed in §5.

---

## 1. The verdict, and why

**The decisive argument is feasibility under the operator's stated
constraint, not preference.** The constraint (2026-08-15): re-use existing
systems, CFEngine is the only mutation engine, no new configuration-management
system. CFEngine has no runtime capability confinement — confirmed against
source and the local 3.27.1 binary, not just docs. So Model A's §7 executor
("refuses any effect outside that set") can only exist as a pre-flight
*interpreter* of the capability vocabulary, plus a proof that the
vocabulary's descriptions correspond to what the rendered policy actually
does. That interpreter-plus-correspondence-proof is the artifact TC-32 says
does not exist and the feasibility note calls "a new mechanism." Model B's
executor is a comparison of two canonical JSON documents against an approved
diff — a validator, no policy interpretation. **The choice is between B and a
fictional A**: a verdict for A is a verdict for an artifact with no
implementation path inside the stated constraints.

Secondary arguments, in force order:

1. **Coverage closes by construction.** Compiler and validator share one
   goal-file schema: what cannot be expressed cannot be rendered *or*
   approved, and both sides fail together, closed. A's coverage gap — §19.8's
   escape-hatch pressure, TC-32's absence, TC-45's naming collision — has no
   analogue. The escape-hatch *dynamic* dissolves; the schema-must-exist
   obligation transfers to the goal file, which is the same kind of artifact
   (schema + fixtures + negative fixtures + lint) this project already knows
   how to build.
2. **TC-29 dissolves properly only under B with device-side diffing** (§5.1):
   the approved object equals the applied object at any staleness.
3. **Verified extent beats proposer-labeled intent.** A never delivered
   verified intent — capability names are proposer-chosen labels, and TC-07's
   forgeable-citation attack applies to them exactly. B delivers verified
   *extent*: the person can know precisely what changes and no more, with all
   intent-prose explicitly untrusted (DC-3). Verified extent + untrusted
   intent is strictly stronger than unverified extent + proposer-labeled
   intent.
4. **B is CFEngine-shaped.** Complete resolved state is what the Augments
   layer consumes; a per-release operation list is an imperative overlay on a
   declarative convergent engine, and someone must prove the overlay and the
   policy agree — that proof is A's hidden largest line item.
5. **Cost.** B drops the vocabulary, its versioning and skew policy, the
   interpreter executor, and (severably) the inference engine — the machinery
   roughly thirty of the red-team's fifty-one findings are about — on a
   project whose binding constraint is one unfunded builder.

**What B does not fix, and must not claim:** S2 in full (every control is
still operator-authored, -delivered, -evaluated; DC-1's device-local trust
root is untouched by this fork and still required), TC-23 (effects vs
declarations — enclosure needs OS confinement, out of scope), and TC-24
except insofar as the goal file binds the policy tree by digest (§7, R8).

## 2. The strongest case against, stated to be acted on

**B trades a reviewable statement of intent for a reviewable statement of
state, and consent is about intent.** "One `service.install`, nothing else"
is a sentence a person can hold; "41 hunks across your goal file" is not.
Everything that makes the diff holdable — canonicalization, attribution,
grouping, privileged-region labeling, briefing — is derived machinery that
collectively re-approaches the vocabulary's complexity under new names, while
the one thing A's vocabulary genuinely bought (a policy hook: "operations of
class `trust.amend` are always human") must be rebuilt anyway as the
privileged-region list. Meanwhile B's schema-migration story periodically
degrades the consent surface to "trust me, it's a migration," training
exactly the rubber stamp §8 exists to prevent. If schema churn runs high and
the labeling layer becomes load-bearing, A will have been rebuilt as an
unacknowledged derived taxonomy — without the honesty of having versioned and
reviewed it as DC-15/DC-16 specified.

The verdict holds against this for three reasons. (i) Every relocated
obligation shrinks by an order of magnitude: the privileged-region list is a
dozen enumerable paths in one document, not a total operation vocabulary;
coverage is closed by construction; the noise mitigations are advisory-layer
and deletable without losing soundness, where A's vocabulary was load-bearing
and had to be right. (ii) The failure modes are asymmetric (the prior
adjudication's §8 formulation, endorsed here): wrong derived labels degrade
review while enforcement stays intact; a wrong authored vocabulary keeps the
ceremony intact while enforcement silently misdescribes the change. (iii) A
builds B's render anyway — §4 calls it the compiler's first piece — so the
vocabulary is purchased *in addition to* everything B needs, to obtain labels
B can derive. The objection stays falsifiable: count migration events and
unattributed-hunk rates once real diffs exist, and hold the tripwire that
labels inform the advisor and never widen what the validator accepts.

## 3. The convergence claim, checked against the sources

The synthesis's claim that the skeptical review and the pre-mortem
"independently designed the same alternative architecture" is **partially
true and overstated** — the same finding as the prior adjudication, reached
independently, which settles it:

- **Real, independent convergence:** the complete per-host render as the
  artifact of record, and cutting the inference engine while keeping the
  fields. Two reviewers, opposite premises (security-claim analysis;
  build-cost analysis), same thread — pulled from the guide's own §4, which
  already commits to the render as "almost free" and "the first piece."
- **Not convergence:** the diff-as-enforced-plan with a validator executor is
  the skeptical review's Alternative A **alone**. Pre-mortem CUT-1 cuts
  on-device enforcement *entirely* — nonces, high-water marks, emergency
  role, offline root, rotation ceremony — on a single-operator threat-model
  argument. E1's executor half is one reviewer's design plus the synthesist's
  composition.
- **The addition this pass makes:** CUT-1's *reasoning* (the executor defends
  against an author who is the same person as the authorizer) is not answered
  by B — but its *conclusion* was priced against Model A's 6–14-month Step 6.
  B's validator collapses that cost to glue, so the cost-benefit that
  motivated CUT-1 no longer holds as stated. Keeping enforcement under B is
  cheap enough to be worth it even while the second party is hypothetical;
  CUT-1's further cut is explicitly **not** adopted, and the red-team's
  signing/consent corpus (TC-15…TC-22, TC-34…TC-37, DC-1…DC-8) applies to B
  in full.

The verdict never rested on the convergence claim; it rests on §1. The record
is corrected, twice now, and the correction changes nothing downstream.

## 4. Delta against the prior adjudication

Convergent, in one line each — these are settled and will not be restated:
the verdict; the convergence-claim correction (§3); the dissolution-table
direction with TC-31 **relocated not dissolved**, TC-10 **half-holding**,
TC-26 **split** (file content dissolves, fetched artifacts do not — DC-11
survives), TC-25 and TC-23 concessions accurate; "Model A = Model B + a
parallel vocabulary + a correspondence proof"; S2 untouched and DC-1 still
required; `--simulate` as confirmation-not-mechanism with the upstream JSON
flag worth filing; the §14.2 gate applying with fresh force; ship-full-file /
device-side diff / compiler-side preview (the prior recommended it; §5.1
below tests it rather than inheriting it, and it survives); the closing of
the "write both schemas and compare" hedge.

Divergences, adjudicated:

**D1 — The prior note is internally inconsistent about hunk attribution and
dependency groups, and the inconsistency conceals a real design error.** Its
§6.4 says "choose one" (dependency-groups *or* refuse-and-re-render); its
§6.2 prescribes hunk attribution as *the* fan-out mitigation, in the diff
format; and its §7 then defines the ChangePlan schema as "diff format (base
hash, hunks, **hunk attribution, dependency groups**)" — baking both
undecided mechanisms into the format. That collides with the same note's own
§5.2 recommendation: if the authoritative diff is computed **device-side**,
the device has no source layers and *cannot compute attribution* — so
attribution cannot be a field of the authoritative diff at all. In-format
attribution would be proposer-asserted provenance inside a security artifact
the device cannot verify: TC-07's forgeable-citation defect reborn at the
hunk level. **Who is right:** this pass. Attribution and dependency groups
are both excluded from the authoritative format — see §5.3 and §5.5 for what
replaces them.

**D2 — The prior §6 residue list is incomplete.** The user asked this
question specifically; the answer is no, four items are missing:

- **Removal semantics** (feasibility note, uncarried): a remove-hunk
  under-describes its actuation. Absence of a promise is absence of
  enforcement, not reversal — every removal must compile to explicit negative
  promises (file delete, package absent, `service_policy => "stop"`), and
  the briefing must render removals *as their actuation*, not as absence. A
  removal smuggled as a modify is a review-target case (§6).
- **Baseline integrity is the new root of the gate.** The device's stored
  currently-approved goal file is what every diff is computed against and
  what every approval binds to. Corrupt or swap that baseline and either the
  gate refuses everything (DoS) or — worse — the device presents a total
  "first-adoption-shaped" diff and launders an arbitrary state through the
  degenerate-diff ceremony. The baseline needs integrity-protected storage
  and its verification belongs in the validator's preconditions. Model A's
  analogous stored state was a high-water counter; B's is a whole document,
  and a more attractive target.
- **The activation gap as a stated design limit:** `--simulate` covers files
  and packages only; the "loaded and running" half of a service change is
  device-unconfirmable. The prior note mentions this while discussing
  `--simulate`; it belongs in the residue register as a permanent honesty
  clause on device-computed confirmations.
- **Goal-file completeness is a *contract*, not a given.** The diff is
  trustworthy exactly where the goal file is complete, and §11's per-domain
  comprehensiveness is that completeness contract. The goal file must carry
  the domain-coverage declarations so validator and advisor can distinguish
  "silent because unchanged" from "silent because `not-yet-migrated`." A diff
  over a non-comprehensive domain proves nothing about what else changed on
  the device. Neither source reviewer nor the prior pass stated this; it
  changes the schema (§5.7).

Minor additions to the register, carried in §7: re-render/counter-proposal
churn as a fatigue channel (TC-19 persistence applies to counter-proposals);
per-host diffs hide fleet-level intent (role moves elsewhere are invisible —
mostly acceptable because per-device trust content lives in the device's own
goal file); transition ordering (e.g. a port moving between services) rides
on retry-until-stable and can transit conflicting intermediate states —
roughly neutral versus A, but worth a line.

**D3 — Two dissolution-audit rows in the prior §3 need qualification.** Its
TC-24 row ("the generic bundle and any `.cf` **can be** entries in the goal
state") reads as a property B has; it is an obligation B makes natural — the
policy tree enters the goal file (or its digest does) only if the schema puts
it there, and it must (§7, R8). Its TC-28 row (rollback = revert to a prior
signed state) omits F-7a: a prior state is always well-*defined* as a target
and not always *achievable* as a transition (package downgrades, data
migrations); rollback-as-goal-state fixes the specification problem, not the
reversibility problem. **Who is right:** both passes on direction; the
qualifications stand.

**D4 — The prior pass left the schema family's design choices open; a
verdict that leaves them open does not unblock the next work item.** Its
§6.4 says "choose one; do not improvise"; its §3/TC-31 row names the
unknown-kind dilemma without resolving it; its §6.3 names migrate-then-diff
without the enforceable form; its first-adoption treatment names a ceremony
without bounding what the ceremony may claim. §5 closes all of them.

## 5. The decisions

Each is a decision, not an option survey. Costs are stated.

### 5.1 Where the briefed diff is computed

**Decision: the full canonical goal file is the signed wire artifact; the
authorizing diff is computed device-side, between the device's
currently-approved canonical goal file and the received one; the
compiler-side diff is a review-time preview, a CI regression artifact, and a
cross-check.** When the device's baseline equals the release's expected
baseline, the device-computed diff must equal the compiler's predicted diff;
inequality is a reportable integrity flag, not a silent condition.
`cf-agent --simulate` remains an optional human-facing confirmation of
actual-state delta; file the upstream `--simulate-output=json` issue before
Step 3 code, per the addendum.

This was the prior note's recommendation; here is the test rather than the
inheritance. Option (a), ship the diff as the artifact: the device must
reconstruct `new = old + patch`, which makes patch application a second
interpreter (the thing B exists to avoid), fails on any baseline drift, and
means the applied state is derived rather than directly signed. Option (b′),
device-side with no compiler preview: loses the author's pre-release review
and the golden-diff regression tests that make the compiler testable on day
one. Option (c) is the only variant in which the approved object equals the
applied object at *any* staleness — a device at N−7 briefs and approves the
one true diff from its actual signed baseline, which is TC-29 dissolved
properly instead of patched. Cost: the advisor round-trip happens after
device contact, and pre-generated briefings become previews rather than the
consent object. Accepted.

The accept binds per DC-2, instantiated for B:
`Sig_advisor( H(old_canonical) ‖ H(new_canonical) ‖ device_nonce [‖ H(briefing_bytes)] )`,
valid for exactly one target key; the validator recomputes every hash.

### 5.2 Canonicalization

Under B this stops being G7's testing nicety and becomes a consent property:
serialization noise is camouflage. **Decision:**

- **Wire format is JSON.** YAML remains an authoring format for Site Model
  sources only and never appears on the wire. (D23's parse/re-serialize/diff
  check was already the symptom of why.)
- **Canonical form = RFC 8785 (JCS)** plus structural rules JCS cannot give:
  every set-semantics collection is an array sorted by a schema-declared key
  (entries by `(domain, kind, id)`); strings NFC-normalized; no floats in the
  goal file (integers and strings only, by schema); signatures detached; no
  nonces, timestamps, or other run-varying fields inside the diffed object.
- **The goal file is fully resolved: the schema defines no defaults.** Every
  meaningful field is present with its explicit value; authoring-level
  defaults are resolved by the compiler before render. Empty collections are
  invalid — omission is the only representation of "none." Consequence: one
  meaning has exactly one byte representation, and a later change to an
  authoring default can never silently reinterpret an already-signed file.
- **Refuse, never normalize.** The validator (and the lint) rejects any goal
  file that is not byte-identical to the canonicalization of itself.
  Negative fixture: a semantically-equal-but-noncanonical file must be
  rejected.
- **The diff is structural, not textual:** hunks at *entry* granularity
  (addressed by the sort key), each carrying the full old and/or new entry;
  field-level display diffs are derived for presentation. A text diff of
  canonical bytes is a permitted rendering, never the authoritative object.
  Entry granularity is deliberate: field-level partial semantics would
  recreate the chimera problem of §5.3 one level down.

Cost: a canonicalization module with its own test surface, and `.json`
fixtures alongside the existing `.yml` ones (lint extension, §8). Accepted —
this is the cheapest of the load-bearing pieces and the one the §14.2 review
must hit hardest.

### 5.3 Partial accept

**Decision: refused-hunks → re-render → re-check. A partial accept is never
applied.** The accept verb is all-or-nothing per proposal. The advisor may
return a *refusal annotated with the hunks that drove it*; the proposer
withdraws the corresponding source-level changes, re-renders the complete
goal file, re-runs the conflict check, and offers a new diff. No device ever
applies a state the compiler did not render and conflict-check.

Dependency-grouped hunks are **rejected**: computing a correct dependency
relation over hunks requires exactly the provides/requires-grade global
knowledge the inference cut just removed, applied to the one artifact where a
wrong grouping *silently* produces an unchecked applied state — the worst §9
failure mode, in the consent path. Grouping may exist later as a *display*
aid in the preview layer; it never gains apply semantics.

This also restates the honest answer to TC-10: bundling is defeated not by
partial apply but by cheap counter-proposal — refusal costs the proposer a
re-render, not the person their patch. A proposer who re-offers the same
bundle after an annotated refusal is creating exactly the record TC-19's
persistence rule exists to surface. Cost: a round trip per contested
proposal, cheap at this fleet's scale; and the counter-proposal loop itself
becomes a fatigue channel to watch (§7, R15).

### 5.4 The two total-diff events

**Decision: name them baseline ceremonies — a distinct consent class with its
own rules — and bound what each may claim, instead of pretending a total diff
was reviewed.**

- **First adoption is governed by a minimal-claim rule.** The initial goal
  file, accepted at the physical first-run ceremony (D41's fingerprint
  ceremony is the venue), may manage only the domains the operator explicitly
  enumerates at that ceremony; every other domain enters as
  `not-yet-migrated`. The unreviewable total diff is thereby converted into a
  sequence of ordinary reviewable diffs — each later domain migration arrives
  as a normal hunk set — and §11's backlog counter doubles as the consent
  metric. The honest day-one goal file is *small in managed surface*, which
  the guide's §11 already says is the correct day-one state.
- **Schema migration must be semantics-preserving and mechanically checked.**
  The migration function ships in the validator update (which itself arrives
  as an ordinary diff under the old schema — §5.6's two-phase rule). A
  migration release is valid iff `diff(migrate(old), new)` is **empty** apart
  from the schema-version bump: a pure migration presents as a one-line
  reviewable change. Mixing migration and semantic change in one release is
  forbidden — split into two releases. Cost: migration functions must be
  shipped, deterministic, and tested; accepted, because the alternative is a
  recurring "everything changed, trust me" event, which is the §2 objection's
  sharpest tooth.

### 5.5 Hunk attribution

**Decision: not in the authoritative format — not day one, not later.** Three
independent reasons, any one sufficient: (i) under §5.1 the authoritative
diff is device-computed and the device has no source layers — attribution
there is impossible, and in the compiler's preview it is unverifiable
proposer-asserted provenance (TC-07 reborn); (ii) provenance plumbed through
merge/render is the origin-tracking machinery CUT-3 cut, returning at the
value level, as the fork briefing suspected; (iii) any attribution stored in
the canonical artifact makes semantically identical states byte-different
when sources are refactored — directly breaking §5.2's
one-meaning-one-representation property that consent now rests on.

What replaces it: attribution is a **query, not a field**. Render purity
makes it reconstructible on demand — re-render with a candidate source change
reverted, diff the renders, subtract; a small compiler-side tool
(`explain-hunk`) does this per hunk, and CI can attribute a whole preview
diff mechanically and *checkably* (against the actual renders, not against an
assertion). Its output travels in the preview/briefing channel as
DC-3-labeled untrusted context. The fan-out fatigue problem the prior note
aimed attribution at is real; its mitigation is this tool plus §5.3's
counter-proposal loop, not a signed field. Cost: fatigue mitigation arrives
with the tool rather than with the format — acceptable while
proposer-and-accepter are the same person, and the tool is due before the
consent surface (Step 9) is.

### 5.6 Schema versioning and unknown entry kinds

**Decision: fail closed, and prevent strandedness at the compiler, not the
device.**

- The goal file carries a `schema_version`. The goal-file contract is
  **stricter than** `common.schema.json`'s `contract_version` rule: *any*
  change to the entry-kind set — additive included — bumps the version,
  because unknown-kind handling is fail-closed and an old validator must be
  able to know, from the version alone, that it can fully interpret the file.
- A validator that sees a version above its ceiling, or (belt and braces,
  `additionalProperties: false` discipline) an entry kind it does not
  recognize, **refuses the entire goal file** with a distinct reported
  reason, and the device keeps converging on its last approved state.
  Refusal is not a brick; it is a visible, reportable stall.
- **Ignore-unknown is rejected outright:** an ignored unknown entry is an
  unreviewed change riding a reviewed diff — fail-open in precisely the sense
  the validator exists to prevent.
- Strandedness is prevented where the knowledge lives: goal files are
  per-host, so **the compiler renders each host's file at the highest schema
  version that host's last-reported validator supports** (§6's report rows
  already carry release and agent state). A schema bump ships in two phases:
  first the validator/agent update as an ordinary diff under version N−1 —
  this is a privileged-region hunk, TC-25 class — then the migration release
  under §5.4's empty-diff rule. A long-dark device is simply rendered at its
  old version until it reports back. Release lint enforces the phase order.

Cost: the compiler carries multi-version render ability for a window, and
per-host version tracking. Accepted — this is the price of a fleet that is
offline by design, and it is paid in the compiler (one place) rather than in
device-side leniency (every device, fail-open).

### 5.7 A schema decision surfaced by the audit: coverage travels in the goal file

The goal file schema **must include the per-domain coverage declarations**
(`comprehensive` / `opt_out_reason`, verbatim from
`common.schema.json#/$defs/domain_coverage`). The diff's meaning depends on
it: silence in a comprehensive domain means "no change"; silence in a
`not-yet-migrated` domain means "not described," and the validator and the
briefing must not let the two read alike. A coverage transition (a domain
becoming comprehensive, or — per DC-37 — a reclassification to
`deliberately-unmanaged`) is itself a hunk, and reclassification hunks are a
distinct review class.

## 6. The §14.2 gate

**It applies, with full force.** The map's clause names the artifact by its
Model-A description ("ChangePlan IR + executor capability vocabulary"), but
its function is: *the artifact the executor enforces and the person consents
over gets independent adversarial review before build*. Under B that artifact
is exactly this schema family. Dropping the gate because the vocabulary was
dropped would be rules-lawyering the map; both adjudication passes land here.

Sequencing: write the schemas and fixtures first, then run the review **on
the contract, before the validator is coded**. The review must be genuinely
independent (not the model lineage that wrote the schemas — the same
discipline this review corpus used) and pointed at, specifically:

1. **Canonicalization as an attack surface:** can two semantically different
   files canonicalize identically (collision), or one meaning admit two
   canonical forms (ambiguity = camouflage)? Unicode normalization edges,
   sort-key collisions, absence-vs-empty, integer bounds.
2. **The binding chain:** the §5.1 accept formula; where each hash is
   computed and by whom; cross-device replay (TC-11), cross-release replay
   (TC-20), and the refuse / withdraw / re-offer state machine (TC-19,
   TC-30, DC-5).
3. **The privileged-region list, for completeness** against TC-24/25/27:
   trust policy, advisor keys, peer allowlist, policy-tree digest,
   agent/validator binary and version, device resource policy,
   `schema_version` itself. The list is validator-held policy — the diff
   format carries no proposer-set privilege flags (forgeable); the validator
   derives privilege from its local list, and the approval record must carry
   a ceremony class adequate to the derived privilege.
4. **Removal semantics:** every remove-hunk renders to explicit negative
   promises; a removal cannot be smuggled as a modify; the briefing renders
   removals as their actuation.
5. **Baseline integrity:** can an attacker corrupt or swap the stored
   baseline to force the total-diff ceremony path or a bogus refusal?
   Storage, verification order, and recovery.
6. **The counter-proposal loop** (§5.3) as a fatigue/churn channel, with
   TC-19's persistence rules applied to re-offers of annotated-refused
   content.
7. **Version-skew behavior** per §5.6, including the two-phase rule's
   failure orders (migration release reaching a device before its validator
   update).
8. **Fixture adequacy:** adversarial negative fixtures, not shape errors —
   F-9b's lesson is that the current broken/ set is weighted toward the
   error class the project's own evidence calls smallest. The §8 list below
   is the floor, not the ceiling.

## 7. Consolidated residue register for Model B

Supersedes the prior note's §6. These are the conditions the verdict carries.

| # | Residue | Status / owner |
| --- | --- | --- |
| R1 | Privileged-region classification returns at the path level (TC-25/DC-1). Small, enumerable, validator-held — but vocabulary-shaped; watch it. | §5.7-adjacent; §6 item 3 |
| R2 | Canonicalization is security-critical; one meaning, one representation. | Decided, §5.2 |
| R3 | The diff is structural and schematized; text diffs are display only. | Decided, §5.2 |
| R4 | Removals compile to explicit negative promises; briefings render actuation. | **New vs prior §6**; §6 item 4 |
| R5 | Fan-out noise / value-level fatigue; big-diff rubber-stamping is TC-09 reborn. | Mitigated by `explain-hunk` + §5.3, not by format |
| R6 | First adoption and schema migration are total-diff events. | Decided, §5.4 |
| R7 | Partial accept synthesizes unrendered states. | Decided, §5.3 |
| R8 | The policy tree / generic bundle is code outside the goal file until the schema binds its digest as a privileged region (TC-24/DC-10). An obligation, not a property. | Schema requirement |
| R9 | Activation gap: `--simulate` covers files+packages; "loaded and running" is device-unconfirmable. Permanent honesty clause on confirmations. | **New vs prior §6** |
| R10 | Baseline integrity: the stored approved goal file is the root of the gate; integrity-protected storage, verified first. | **New vs prior §6**; §6 item 5 |
| R11 | Goal-file completeness contract = §11 coverage, carried in the file. | Decided, §5.7 |
| R12 | Fetched artifacts still bind names; digest fields (DC-11) are a schema obligation, covered by the accept, re-verified at apply. | Schema requirement |
| R13 | Approval-record discipline is DC-2 in full (per-target validity, device nonce, monotonic-counter single-use, persisted rejects). | Decided, §5.1 |
| R14 | TC-23 (effects) unsolved at this layer, in either model. | Carried, stated |
| R15 | The counter-proposal loop is itself a fatigue channel; TC-19 persistence applies to re-offers. | §6 item 6 |
| R16 | Per-host diffs hide fleet-level intent; briefing may need release-level context. Minor. | Briefing layer |
| R17 | Cross-entry transitions (port moves) ride retry-until-stable; transient conflicts possible. Neutral vs A; worth a line in the design. | Documentation |
| R18 | S2 untouched: B improves what the person is shown, not who authors the machinery. DC-1 still required. | Carried, stated |

## 8. What this unblocks: the schema family, concretely

Three schemas, following the existing contract conventions (`$id`, draft
2020-12, pairing, negative fixtures, cross-file lint rules):

- `schema/goal-file.schema.json` — canonical per-host goal file: header
  (`schema_version`, host public key, domain coverage per §5.7), entries by
  `(domain, kind, id)`, fully resolved (no defaults, no empty collections),
  digest fields on fetched content (R12), policy-tree digest (R8). Fixture:
  `examples/goal-file.json` — **JSON, in canonical bytes**; the fixture *is*
  a canonicalization test.
- `schema/goal-diff.schema.json` — baseline hash, proposed hash, entry-level
  hunks (add/remove/replace with full old/new entries). No attribution
  fields, no group fields, no privilege flags (all derived, §5.5/§6.3).
  Fixture: `examples/goal-diff.json`, consistent with the goal-file fixture
  pair it diffs.
- `schema/approval-record.schema.json` — target key, baseline + proposed
  hashes, device nonce, optional briefing hash, verdict
  (`accept` / `reject` with hunk annotations / `withdraw` per DC-5),
  ceremony class (ordinary / privileged / baseline per §5.4 and §6 item 3),
  advisor signature envelope. Fixture: `examples/approval-record.json` —
  include a reject with annotations, not only an accept.

Lint extensions: pair `.json` examples (the `EXAMPLES` map and the pairing
glob are `.yml`-only today); add the canonicalization idempotence check
(refuse any fixture ≠ canonicalize(fixture)); bump `EXPECTED_BROKEN` as
cases land (the constant asserts the count by design). Negative fixtures, as
the floor: non-canonical goal file; unknown entry kind; empty collection;
field-equal-to-authoring-default materialized; baseline-hash mismatch;
hunk/file inconsistency (diff does not take old to new); ordinary-class
approval over a privileged-region hunk; removal expressed as a modify;
migration release whose semantic diff is non-empty; approval whose hashes
don't match the files presented.

Then the §6 review, on the contract, before validator code.

## Sources

All in-repo, read in full 2026-08-15. The unanchored Part-1 draft (verdict,
convergence check, residue list, and all §5 decisions committed before the
prior adjudication was opened) is preserved in the session scratchpad;
nothing in the corpus was unreadable or declined.

- `docs/paper/tendcf-architecture-guide.md` (§4, §7, §8, §10, §11, §15, §18, §19)
- `docs/architecture/architecture-DEFINITIVE-v3.md` (§9, §13, §14.2, D23,
  D27, D30, D41/D42)
- `docs/paper/reviews/2026-08-15_opus-5-max_redteam-trust-consent.md`
  (TC-01…TC-51 and the RT dispositions, in full)
- `docs/paper/reviews/2026-08-15_opus-5-xhigh_skeptical-review.md`
  (Alternative A, Claims 1–3, G1, G5, G7, F-9b, F-10a–f, F-16a–h)
- `docs/paper/reviews/2026-08-15_opus-5-high_premortem.md` (CUT-1/2/3, the
  demotion, §3.1 sizing, A-/N-/U-series)
- `docs/paper/reviews/2026-08-15_opus-5-xhigh_SYNTHESIS.md` (E1, the
  dissolution table, S1–S5, DC-/DOC-series, §6 ordering)
- `docs/architecture/cfengine-feasibility-of-diff-plan-2026-08-15.md`
  (addendum controlling over body)
- `schema/*.schema.json`, `examples/`, `examples/broken/`,
  `bin/schema_lint.py` (the existing contract and its conventions)
- `docs/architecture/e1-adjudication-2026-08-15.md` (Part 2 only, opened
  after the §1–§3/§5 positions were written down)
