# Independent skeptical review — `tendcf-architecture-guide.md`

**Reviewer:** Claude Opus 5 (xhigh), acting as an independent reviewer.
**Date:** 2026-08-15.
**Target:** `docs/paper/tendcf-architecture-guide.md` (the vetted current-state
guide, declared to win over all other living documents).
**Background consulted, not reviewed:** `tendcf-architecture-paper.md`,
`docs/architecture/architecture-DEFINITIVE-v3.md`, plus the repository
artifacts the guide makes factual claims about (`schema/`, `examples/`,
`examples/broken/`, `bin/schema_lint.py`).
**Independence:** I did not open the other review files in this directory.
Findings here are my own; overlap with other reviewers is coincidental.

**Verdict: major revision.** The architecture is coherent and the engineering
instincts are good. The document, however, states conclusions its design does
not yet support, and — decisively — its three self-critique sections (§10,
§17, §19) are drawn entirely around the mechanical subsystems and never touch
the trust/consent subsystem the document itself calls the point. Everything I
found is fixable by rescoping claims, adding one worked example, and moving
the risk register; none of it invalidates the design.

Findings are tagged `[C: confidence / S: severity]`. Per instructions I have
filtered nothing.

---

## 0. The one observation that organizes the rest

The guide contains three separate self-critique sections: §10's three ways the
writing rule may be wrong, §17's three ceilings, §19's nine open questions.
Fifteen conceded weaknesses in total.

Sort them by subsystem:

| Subsystem | Conceded weaknesses |
| --- | --- |
| Ordering / inference (§10, §15) | 6 |
| Comprehensiveness / extra entries (§11) | 3 |
| Local-first reporting (§6) | 3 |
| Release model / render timing (§4, §7) | 1 (§17 third ceiling) |
| ChangePlan capability vocabulary (§7) | 1 (§19.8) |
| The premise itself (§9) | 1 (§19.9) |
| **Signing, keys, root rotation, ceremony (§7)** | **0** |
| **Consent, refusal, the advisor slot (§8)** | **0** |
| **Per-device trust, peer authorization (§13, §14)** | **0** |
| **Release distribution / transport** | **0** |

The document is maximally humble about the parts with two decades of prior art
(Bcfg2's ordering, Bcfg2's extra entries, Bcfg2's statistics spine) and
completely silent about the parts that are novel, unbuilt, security-critical,
and — per the implementer map's own §0.3 and §14.2–14.4 — flagged internally as
"do not improvise, independent adversarial review before build." A reviewer
reads that pattern as concessions offered where they are cheap. That is the
single strongest reason this is not an accept. `[C: high / S: high]`

---

## 1. The three most vulnerable claims

### Claim 1 — §9: that "prefer local knowledge over global knowledge" justifies the inference machinery

The rule is the document's thesis and carries §10 (inference), §11 (default-on
comprehensiveness), §15 (lookup CLI), the conflict-error format, and the
semantic-layer citation requirement. It is vulnerable because, as stated, it
cannot lose an argument, and because the design already contains a better
answer to the problem the rule poses.

**The design's own conflict checker refutes the framing.** §4 stage 2 is a
*global* check — two writers claiming the same port or path is a build failure
— performed by the compiler, over already-merged data, with an error that
names every writer and a resolution. That mechanism does exactly what §9 says
is impossible: it makes a globally-scoped constraint safe for an author who
knows nothing about the rest of the system. So the operative axis is not
local-vs-global *knowledge*; it is **who holds the global knowledge, the author
or the checker**. Once that reframing is on the table, `depends_on` plus a
compiler-side completeness check is a live competitor to inference, and the
document never compares against it. §19.2 asks "what would a counter-example
look like" while the counter-example sits two sections earlier in the same
document. `[C: high / S: high]`

**§15 collapses the distinction the rule depends on.** §15 concedes "the
writing rule is 'don't require the graph,' not 'don't require names.'" But
with the lookup CLI in hand, writing `depends_on: caddy` and writing
`requires: service:caddy` demand the *same* discovery act: find out caddy
exists and matters to me. The residual difference — that `requires` names a
need while `depends_on` names a relation — is real but much thinner than
"local vs global," and it is not the difference §9 argues for. `[C: high / S: high]`

**The two rules are in tension, not complementary.** Rule 2 ("prefer
machine-checkable to conventional") says make every constraint a compile-time
check. If rule 2 succeeds, rule 1's premium on locality mostly evaporates: a
confidently-wrong global assumption that the compiler rejects is no worse than
an obviously-wrong one, since both are caught before they ship. If rule 2
fails, rule 1's own mechanisms — which are themselves compile-time checks —
fail with it. §9's claim that plausible violation "is worse than violating it
obviously" is asserted, never argued, and only holds for the class of
violations rule 2 was supposed to eliminate. `[C: high / S: medium]`

**The cited evidence measures a different authoring mode than the design
uses.** IaC-Eval and the error taxonomy measure one-shot, unassisted
generation against a cloud API. tendcf's authoring model is agentic and
*tool-mediated*: schema, lint, lookup CLI, teaching compile errors, and a
"show me device X" affordance. Nothing cited measures the failure rate of that
loop. If tools close the gap, the empirical support for the rule weakens
exactly where it currently reads strongest. `[C: high / S: medium]`

**The guide is less hedged than the paper it derives from.** The paper says
"We are aware this rule can be used to justify almost anything." The guide
reduces that to "a working hypothesis, not a law." The strongest
self-criticism available was dropped on the way into the document that wins on
conflict. `[C: high / S: medium]`

**Evidence that would defend Claim 1** (all obtainable today, with nothing
deployed — which is why its untested status reads as a choice):

1. A **decision procedure** that classifies a mechanism as local or global,
   applied to at least three mechanisms the design *rejected*. Right now the
   rule only ever confirms. A rule that has never ruled anything out has not
   been shown to have content.
2. A **head-to-head on the same fixture**: enumerate precisely what an author
   must know to write `depends_on: caddy` vs `requires: service:caddy`, given
   §15's lookup CLI. If the answer is "the same lookup," inference needs a
   different justification and should get one.
3. The **missing comparison**: authored `depends_on` + a compiler-side check
   that every referenced target exists and every ordering-relevant pair is
   covered, versus inference. Both put the global knowledge in the checker.
   Say why inference wins.
4. A **falsification protocol**: N agent-authored service records under both
   regimes, scored by error class. This requires no fleet, no compiler and no
   deployment — only a prompt, the existing schemas, and a rubric. Running it
   would convert the thesis from an argument into a result.

### Claim 2 — §7: that the executor "refuses any effect outside that set"

This is the security core, and it is stated as a mechanical guarantee. Two
independent problems.

**Capability enclosure is unspecified where it is hardest.** A `capability`
drawn from a closed list, with `resources` checked against port and path
registries, bounds effect only if each capability's *implementation* is
bounded. The obvious member of any such vocabulary — install or upgrade a
package — executes vendor maintainer scripts as root on Linux, touching
arbitrary paths, spawning arbitrary processes, and enabling arbitrary units.
The plan can declare `resources: [/usr/bin/foo]`; `apt` will not honor it. So
either the executor sandboxes package operations (a large, unstated,
platform-specific engineering commitment) or the guarantee is nominal for the
most common operation in the fleet. The document does not distinguish
capabilities that can be mechanically enclosed from those that can only be
*declared*. §19.8 worries about the vocabulary's coverage and about escape
hatches; the deeper problem is that some entries are escape hatches by
construction. `[C: high / S: high]`

**TUF freeze/expiry protection contradicts "often offline."** §1's fleet is
routinely unreachable. §7 buys freeze detection and downgrade rejection from a
TUF subset with a per-client high-water mark. TUF's freeze protection works
through *metadata expiry*: timestamp and snapshot roles carry short lifetimes
precisely so a withholding attacker cannot pin a client to old state. A device
offline past that window has expired metadata and, under a correct TUF client,
refuses to install anything until it can refresh. Combine that with §8's
"timeout is deny" and a per-plan `expiry`, and a consented device that is
offline longer than the shortest of those windows converges to a device that
can accept nothing at all — the exact device class the architecture exists to
serve. No expiry budget, refresh policy, offline-tolerance figure, or
"expired-but-root-valid" behavior appears anywhere. `[C: high / S: high]`

**Evidence that would defend Claim 2:**

1. The **capability vocabulary enumerated**, each entry annotated with its
   enclosure mechanism: mediated syscall/path interposition, a wrapper that
   can actually refuse, or an honest "declared, not enforced." Any entry in
   the third bucket must be visible to the person's advisor as such, because
   consenting to "install package X" is consenting to arbitrary root code.
2. An **expiry/offline budget**: metadata lifetimes for each TUF role, the
   maximum supported offline period, the client behavior on expired
   timestamp/snapshot with valid root, and how freeze detection distinguishes
   "the operator published nothing for 90 days" — normal for a one-operator
   site — from active withholding. The design has an unusual advantage here
   (a per-device local record and peer attestations) and should use it, but it
   must be argued.
3. **One end-to-end ChangePlan example.** The guide has none. §16 exhibits an
   ordering edge and an interlock — the two least novel mechanisms — while the
   artifact on which signing, capability enforcement, the semantic layer, the
   advisor, and the entire sovereignty story depend is described only in
   prose. A reviewer cannot assess a schema they have not been shown.
4. A **threat model** naming the AI authoring path and the semantic layer as
   attack surfaces (see §2, gap G1 below).

### Claim 3 — §1/§5: "no always-on central server that every device must reach"

§1 states it as a goal met. §5 explains the mechanism: every host runs its own
`cf-serverd`, policy "arrived as part of the ordinary signed-release path,
synced via git," and the shape is "closer to GitOps / Flux … no reachable
control plane holding credentials."

**The transport is never named.** Nothing in the guide — including the §2
diagram, which draws a bare arrow from "Signed release" to "CFEngine +
tendcf-agent" — says how a release and its TUF metadata reach a device. Git
sync implies a git remote. TUF implies a repository to poll. Both are
always-on central servers that every device must reach. `[C: high / S: high]`

**The Flux analogy proves less than it is used for.** Flux's claim is *no
inbound control plane* — no push, no credentials held centrally. Flux
absolutely requires an always-on, reachable git server. Borrowing Flux's
authority for the stronger claim conflates two different properties. The
design has the weaker one (which is genuinely valuable and correctly argued);
the guide asserts the stronger one. `[C: high / S: high]`

**Push reintroduces inbound reachability and an unmodeled authority.** §5's
push path requires the target to accept an inbound trigger from whoever holds
the deploy role. §14's trust table has axes for release signatures, consent,
peer action, attestation, and secrets — but none for "who may cause my agent
to run now." Whoever holds the deploy role can trigger immediate convergence
on every operator host; that authority is granted by role data in a signed
release and is not visible in the trust model. `[C: high / S: medium]`

**Evidence that would defend Claim 3:**

1. A **named transport per tier**, with its availability assumption stated:
   git remote, peer gossip over the mesh, sneakernet USB, or all three with a
   priority order — and what breaks when each is unavailable for N days.
2. A **restatement that separates the two properties**: "no inbound control
   plane and no central authority holding credentials" (defensible, and what
   the design achieves) from "no always-on central server" (not supported as
   written). If the stronger claim is intended, the transport must be
   peer-to-peer and that becomes a first-class subsystem, not an omission.
3. A statement of **what `cf-serverd` on every host is for** when each host is
   its own hub. Self-bootstrap is a documented CFEngine primitive; a
   fleet-wide self-hub arrangement where no host serves another makes
   `cf-serverd` either a no-op or the peer-transport the document has not
   described. Either answer is interesting; neither is given.

---

## 2. The gap: where the argument reaches past its premises

**G1 — From "we provide an `accept | reject` slot" to "a person can refuse a
change" (§1, §8).** This is the largest gap in the document, because it is the
document's stated purpose.

The design supports *declining*. It does not describe *refusing while
remaining a participant*. Nothing states what a refused device's state is
afterward: does the plan re-present each release (a nag loop that converts
consent into fatigue, with "timeout is deny" ensuring the device silently
stops converging)? Does the refusal persist as a durable local policy? What
happens when the refused change is a prerequisite of a later accepted one?
Roles are data with `{main, backups[], peers[]}` — what happens when a device
holding a role refuses the release that reassigns it? A device can refuse for
a year; the ChangePlan IR, capability vocabulary, augments keys, and
attestation format will all move in that year, and there is no protocol
version, no compatibility window, and no skew policy anywhere in the document.
§8 offers "personal branch: theirs" — but a personal branch never re-enters
§4's conflict check, so the design's strongest invariant (one writer per unit
prefix, no port collisions) holds only over the non-refusing subset. Refusal,
the feature, silently disables the guarantee the rest of the architecture is
built to provide. `[C: high / S: high]`

Related and separately serious: **the semantic layer is a persuasion channel
into the consent decision, and "it never authorizes" is a category error as a
defense.** The semantic layer is generated prose, fed directly to the
decision-maker's language model, whose signed output is the authorization. It
does not need to authorize in order to compromise the decision. The paper says
this plainly ("a wrong explanation can still talk a person into accepting a
change they would have refused"); the guide keeps the mechanism and drops the
risk. The mitigation offered — free prose must cite the fields it summarizes
— constrains *sloppiness*, not *adversarial content*, and the field-citation
rule is unenforceable against a generator that cites correctly and frames
maliciously. `[C: high / S: high]`

**G2 — From "a TUF subset sized for one operator" (§7) to "more than one
trusted person can act" (§1).** The guide asserts both, four pages apart,
without reconciling them. §14's Release axis names a single site TUF root.
§18's build order contains no step for co-operator key enrollment, threshold
signing, delegation, or removing a co-operator who leaves. Multi-actor is real
in this design for *push authority* (a role in data) and absent for *signing
authority*. Web-of-trust across actors is explicitly punted to "the advisor
plug-in" and "a separate project." A stated goal of §1 is thereby met by
declaring it out of scope in §8 and §14. `[C: high / S: high]`

**G3 — From "supervisors are adapters, one service record is one fact" (§3,
§5) to a demonstration at one supervisor.** The fixture's service records carry
a `launchd:` block — a supervisor-specific sub-object inside the fact the
design says is supervisor-independent. The only cross-file lint rail is
launchd-label-specific. And the record has no field for the distinction that
matters most on the one platform shown: LaunchDaemon vs LaunchAgent (system vs
per-user session, with entirely different capabilities). The abstraction is
claimed at five supervisors and exhibited at one, in a form that already leaks.
§10's own rule — "inference does not start until real type definitions exist
on two platforms" — is the authors conceding they do not yet know the
abstraction holds; §3 and §5 nonetheless assert it. `[C: high / S: medium]`

**G4 — From "the roles examined so far declare no role-to-role dependencies"
(§10) to "catalog compilation is not needed."** Three problems stack. (a) The
audit is of the *legacy stack*, which §0 of this same document declares "legacy
reference only … not copied into this project" and describes only in generic
terms — so the reader cannot inspect the evidence for the design's single
largest rejection. (b) The guide correctly concedes the cold path is untested
but drops the paper's sharper admission that the three gaps found were found by
reasoning, "which is strong evidence the list is incomplete." (c) A negative
result about System A is being used to justify an architectural choice in
System B, which has a different service model, a different platform mix, and
machine authors. `[C: high / S: medium]`

**G5 — From "blast radius is a schema constant" to "an author cannot narrow
it" (§12, §16B).** `blocks: enclosing-bundle` is a `const`. But *bundle
membership is author-settable* — the fixture assigns `bundle: edge-http` and
`bundle: fleet-vpn` per service record. An author who wants a narrower blast
radius simply puts the risky promise in a bundle by itself. The schema
constant fixes the *expression* of the blast radius while leaving its *extent*
fully under author control, and the security argument in §12 depends on the
extent. `[C: high / S: medium]`

**G6 — From "extra entries detect uncoordinated writers" to "the only
mechanism in the design that notices two writers changing the same device"
(§11).** Extra-entry detection notices *unmentioned* state. A second writer
that modifies state the model *does* describe — rewrites a plist, edits a
managed config file — is caught by ordinary convergence: CFEngine repairs it
and reports a repair, and a resource that repairs on every run is the classic
uncoordinated-writer signal. §6's report rows carry `repaired` in the outcome
vocabulary, so the design already collects it. "The only mechanism" is false,
and it makes default-on comprehensiveness look more load-bearing than it is.
`[C: high / S: medium]`

**G7 — From "the render is a pure function" to "the compiler regression-tests
itself" (§4).** The render may be pure; the *plan* is not — it carries a
one-time nonce and an expiry (§7), and the release carries signatures. So
"show me exactly what device X would receive" cannot be byte-compared across
runs without a canonicalization rule that strips or fixes the
non-deterministic fields. That rule is unstated, and the regression-test claim
depends on it. `[C: medium / S: low]`

**G8 — From "a path to a fleet-wide view exists" to "costs nothing new to
stand up" (§6).** The paper justifies this — the observability stack already
runs for other purposes. The guide keeps the conclusion and drops the premise,
leaving a bare cost claim covering a receiver, a schema mapping, a transport,
and authentication. `[C: high / S: low]`

**G9 — From §17's "Every choice above is scoped to a specific envelope" to
three ceilings.** See §5 of this review. `[C: high / S: medium]`

**G10 — From "the generic machinery is publishable" (§1, stated as a goal) to
§18's step 10+, "extracting the publishable layer when a second person runs
it."** Publishability is a §1 goal and a demand-driven maybe in the build
order, with a chicken-and-egg: a second person cannot run it until it is
extracted. `[C: high / S: low]`

---

## 3. Two alternative designs that meet §1's goals

Both meet all seven constraints: mixed fleet, often offline, multiple trusted
actors, no ops staff, no always-on central server, AI-authored configuration,
and refusal-by-your-own-AI.

### Alternative A — "The rendered goal file *is* the artifact, the plan, and the review object"

Keep the Site Model, the schemas, the lint, and CFEngine. Delete the inference
stage, the `nix2cf_edges` indirection, and the separately-authored ChangePlan.
The compiler's only jobs are merge, conflict check, and render — and what it
renders per host is a single, complete, fully-resolved desired-state document:
every file, package, service, and value, nothing left to look up. One generic
convergent bundle consumes it. The **ChangePlan is mechanically derived as the
diff** between the host's currently-signed goal file and the proposed one. The
executor's allowlist is derived from that diff rather than from a
hand-maintained closed vocabulary.

**What it does better.**
- *The sovereignty story gets a real object.* Today the person's AI is asked
  to reason about a plan the reader has never seen, briefed by generated
  prose. Here it reviews a complete diff between two exact states. The
  semantic layer becomes a summary that is checkable line-by-line against the
  diff — which is the accountability property §7 wants and cannot currently
  deliver, since a summary of a partial description cannot be checked against
  anything complete.
- *§19.8 mostly evaporates.* A closed capability vocabulary is only as good as
  its coverage, and the pressure to add an escape hatch is real. A
  diff-derived allowlist has no coverage problem: what is not in the diff
  cannot be done. (The enclosure problem from Claim 2 survives — package
  installs still run vendor code — but the *vocabulary* problem does not.)
- *It is more faithful to §9's own rule than the design derived from it.* The
  artifact an agent must reason about is complete and self-contained: the
  maximally local object.
- *Build cost drops by a full stage and by the entire inference/origin
  machinery*, on a project whose binding constraint is one unfunded builder.
- *Purity is testable on day one* — goal file in, goal file out, no fleet.

**What it gives up.**
- Derived ordering entirely; you fall back to retry-until-stable plus authored
  `depends_on`, which §10 already calls the substrate. If §9's rule is right,
  this is a real loss.
- Fan-out: a shared fact touches N goal files. They are generated, so no human
  edits N files — but releases get larger and diffs noisier, and content
  addressing becomes necessary rather than optional.
- Some of the "publishable generic engine" story: more behavior lives in the
  renderer, less in reusable data, so site-shared recipes have a thinner
  contract.
- Cross-site recipe composition (§2's foreign inputs) needs a different design,
  because merging happens over recipes, not over rendered goals.

### Alternative B — "Authenticated replicated log over the mesh the fleet already runs"

Replace the release train with per-actor signed feeds. Each trusted person
publishes an append-only, signed sequence of content-addressed policy bundles.
Feeds gossip over the existing mesh VPN and, for long-dark devices, over
sneakernet. Each device keeps a local view: it applies the subset of events
whose authors satisfy its own local trust policy and whose plans its advisor
accepted, and publishes its own signed apply-attestations into its own feed.
Refusal is a durable local filter entry.

**What it does better.**
- *"No central server" becomes true rather than unstated.* The transport gap
  in Claim 3 stops being an omission and becomes the architecture.
- *Multiple trusted actors is native.* Per-actor feeds with per-device
  thresholds are exactly the multi-signer model §1 promises and §7 does not
  provide. The web-of-trust logic §14 punts to "the advisor plug-in" becomes
  expressible in the same substrate rather than in a separate project.
- *Refusal becomes coherent.* A device's applied set is its own view by
  construction, so refusing is a normal state rather than an unhandled
  divergence — the direct fix for gap G1.
- *It answers §19.5 and §19.6, and dissolves §17's first ceiling.* Fleet-wide
  answers come from replicated attestations, so "unknown" *shrinks* as devices
  sync rather than being permanent. Bounded-staleness fleet queries stop
  requiring a central statistics spine — which means §17's first ceiling is not
  a ceiling on local-first reporting at all, only on *unreplicated* local-first
  reporting.
- *Long-offline devices are the design center*, not a case in tension with
  metadata expiry.

**What it gives up.**
- The design's best current property: compile-time global invariants. With no
  single compile over the whole site, port/path/unit-writer conflicts become
  detect-after-the-fact, not prevent-before-ship. That is a direct trade of
  §4's conflict-as-error rule — arguably the most valuable thing in the
  current design — for offline and multi-actor fidelity.
- Revocation and key rotation get materially harder than TUF's, which is a
  solved, specified, reviewed problem.
- Causal ordering across feeds needs explicit machinery (vector clocks, or an
  ordering discipline), and the mental model is heavier.
- Implementation cost is higher than the current design, which already has
  more unbuilt than one person can plausibly ship — this may be disqualifying
  under §1's "no ops staff" constraint, and the guide should say so if it
  rejects this path.
- Gossip leaks metadata across trust domains unless carefully scoped, cutting
  against §3's "inventory is private by default."

---

## 4. The most likely reason for a major-revision verdict

**A document that declares itself authoritative and current-state is less
hedged than the paper it derives from, and its risk register is drawn around
everything except the subsystem it calls the point.**

The header says "Where any other living document disagrees on the current
design, this guide wins." That elevates it above the paper. Yet on the way from
paper to guide, the following were removed:

- "We are aware this rule can be used to justify almost anything" → "a working
  hypothesis, not a law." (§9)
- "A wrong explanation can still talk a person into accepting a change they
  would have refused" → "**It never authorizes.**" (§7)
- IaC-Eval's 19.36% → "first-try correctness … is low." (§9)
- "The three gaps we did find, we found by reasoning … strong evidence the
  list is incomplete" → dropped. (§10)
- "We are aware this is the decision most likely to be wrong" (local-first) →
  dropped from §6; survives only as one of nine open questions.
- "Two of the twelve exposed error messages that were useless — the failure §3
  rules out for the compiler, which we had not applied to the compiler's own
  tooling" → dropped from §18. That was the only self-critical finding about
  the one component that exists.
- "The observability stack this fleet already runs for other purposes" → the
  premise dropped, the "costs nothing new" conclusion kept. (§6)

Individually these are compressions. Together they are a systematic
directional drift, and the governance rule ("this guide wins") makes the
least-hedged of the three documents the one that governs. Combined with §0's
observation — fifteen conceded weaknesses, zero touching signing, keys,
consent, refusal, or peer authorization — a reviewer cannot accept the
conclusions as written.

It is a *major revision* and not a reject because every problem I found is a
claims-and-scoping problem: restate three claims to what the design supports,
move the risk register to cover the trust subsystem, exhibit one ChangePlan
end to end, and name the transport. None of that requires redesigning
anything. `[C: high / S: —]`

---

## 5. §17 pressed hard: are these the real ceilings?

### 5.1 The section's opening sentence overclaims its own coverage

"Every choice above is scoped to a specific envelope … Three ceilings follow."
Three ceilings are then given, for local-first reporting, derived edges, and
the release model. Untouched by any ceiling: the ChangePlan and executor, the
TUF subset, per-device trust, the consent/advisor mechanism, peer actions,
comprehensiveness, interlocks, the Site Model itself, and the choice of
CFEngine. "Every choice" → three is a non-sequitur in the section's first
paragraph. `[C: high / S: medium]`

### 5.2 All three ceilings are undetectable from inside this architecture

Each ceiling is a frequency threshold — "routine rather than exceptional,"
"the common case rather than the exception," "a bounded clock" — with no
metric and no trigger. Worse, the design cannot measure its own approach to
any of them:

- Ceiling 1 fires when fleet-wide queries become routine. Detecting that
  requires fleet-wide query telemetry, which is precisely the central spine
  the design declines to build. **Ceiling 1 is unfalsifiable inside its own
  architecture.**
- Ceiling 2 fires when role interleaving becomes common. Detecting that
  requires the compiled edge graph, produced by a compiler that does not exist
  and whose inference stage is explicitly last (§18, step 3).
- Ceiling 3 fires when changes must land on a bounded clock. Detecting that
  requires fleet-wide release-to-converged latency — ceiling 1's telemetry
  again.

A limit you cannot observe yourself crossing is a disclaimer, not a ceiling.
This is the single most fixable weakness in §17: give each ceiling a metric the
design itself emits, with a threshold. Concretely — ratio of fleet-scope to
host-scope queries served per month; ratio of inferred cross-role edges to
total edges; p95 release-to-converged latency by trust tier, with the count of
devices never reached. `[C: high / S: high]`

### 5.3 All three ceilings are re-runs of open questions the authors already hold

Ceiling 1 is §19.5. Ceiling 2 is §19.1. Ceiling 3 is the render-timing
trade-off. Each is a doubt the authors already carry, restated as a boundary —
which converts an admission of uncertainty into a claim of scoping discipline.
And each threshold is one the authors' own fleet, by construction (small,
no ops staff, offline), will never cross. Three concessions that cost nothing.
`[C: high / S: medium]`

### 5.4 The ceilings that are actually load-bearing and are not named

**Ceiling A — the consent ceiling: this architecture stops working when
refusal is exercised rather than merely offered.** Every mechanism in the
document assumes convergence toward one authored intent. The stated purpose is
to let people diverge from it. There is no reconciliation path, no protocol
version, no skew budget, and no re-entry of a personal branch into the
conflict check (G1). The honest ceiling is: *once refusal is common rather than
exceptional, the fleet needs a design where per-device divergence is the
normal state and shared invariants are negotiated rather than compiled* —
Alternative B's shape, or an explicitly per-device-sovereign model. That this
ceiling is missing from a section about where a different architecture wins,
in a document whose implementer map opens with "the trust/consent layer is the
point," is the most conspicuous omission in the review. `[C: high / S: high]`

**Ceiling B — the multi-operator ceiling.** §1 promises multiple trusted
actors; §7 sizes the signing model for one. The ceiling is at the *second
operator who must author a release without the first's key*: threshold
signing, delegation, per-role scoping, and co-operator revocation. That is not
a variant of the current design; it is a different trust architecture, and it
is triggered by a condition §1 states as already true. `[C: high / S: high]`

**Ceiling C — the builder-capacity ceiling.** Every named ceiling assumes the
system exists. §18 says the compiler, all three adapters, the release path,
the executor, the consent surface, the peer-action runtime, and the supervisor
switch are unbuilt, with no ops staff and one author. The binding constraint is
engineering budget, not fleet size. The honest ceiling — and the one a reader
deciding whether to adopt most needs — is *below some build budget, a signed
tarball of rendered state plus a convergent applier (or plain Ansible over the
mesh) delivers most of this design's value at a fraction of the cost.*
Alternative A is roughly that boundary. `[C: high / S: high]`

**Ceiling D — the premise ceiling.** §17 never names a limit on the
AI-authorship premise itself. Both directions matter: if agents become
reliable over long contexts and tool-mediated lookup is cheap, the entire
local-knowledge scaffolding is unnecessary and an ordinary catalog compiler
wins. If agents are worse than assumed — fluent, schema-conformant, and
semantically wrong — then types are the wrong defense and what is needed is a
review/test loop (property tests over rendered output, differential runs
against the previous release). §19.9 asks this as an open question; §17 never
converts it into a boundary, which is where it belongs, since it is the one
condition under which a *different architecture entirely* wins. `[C: high / S: high]`

**Ceiling E — the adversarial ceiling.** No ceiling names the point at which
the threat model outgrows the design. The novel exposure is not a compromised
release channel — TUF covers that — but a compromised or prompt-injected
*authoring* agent producing a Site Model that compiles to a valid, signed,
capability-conformant, malicious plan, briefed to the reviewer's own LLM by a
generated semantic layer. At that point the answer is not this architecture
plus more schema; it is two-party authoring review, reproducible builds of the
release from the Site Model by an independent party, or attestation-based
n-of-m sign-off. `[C: high / S: high]`

**Verdict on §17: the three named ceilings are the comfortable ones.** They
bound the three mechanisms borrowed from Bcfg2 — the parts with prior art, the
parts a reader can check — and leave every original, unreviewed,
security-critical mechanism unbounded. `[C: high / S: high]`

---

## 6. §9 assessed: is the local-knowledge rule load-bearing or convenient?

Covered as Claim 1 above; three additions.

**F-9a — The rule is applied asymmetrically to the design's own choices.**
Auto-provide (§10, §15) means a *local* rename of a service silently breaks
every distant `requires` naming it — a local edit with a global effect, the
rule's own failure mode running backwards. It is caught at compile, which is
the right answer, but that is rule 2 rescuing rule 1, which is the tension
above. `[C: high / S: medium]`

**F-9b — The build order contradicts the cited error distribution.** §9 cites
the taxonomy finding that invalid/nonexistent-reference errors are the largest
category by a wide margin and syntax/schema the smallest. Of the twelve
negative fixtures, by my reading of `examples/broken/`, roughly three
(`08-unknown-role`, `03-rogue-launchd-label`, `04-nested-writer-prefix`) test
the reference/existence class; the other nine test schema shape. The one
component that exists is thus weighted toward the category the guide's own
evidence calls smallest. The implementer map's D28 states the correct
priority; the guide cites the evidence and does not act on it. `[C: high / S: medium]`

**F-9c — "Lost in the Middle" is a 2023 result asserted as a live premise in a
2026 document.** The guide states it flatly ("accuracy drops when the relevant
fact sits in the middle of the window") without a currency check, and drops the
paper's specificity. Long-context handling has moved materially since TACL
2023. If the premise is still true it should be re-grounded; if it is weaker
now, §9's empirical support thins. `[C: medium / S: medium]`

---

## 7. §10 assessed: are those three the strongest counter-arguments?

**No — they are the three that concede *necessity* while leaving *feasibility,
semantics, and safety* untouched.** All three ask "is inference needed?" None
asks "does inference work, and is it well-defined?" The stronger
counter-arguments the section omits:

**F-10a — The mechanism may be inert in the chosen engine.** §16A emits edges
as augments *data* (`nix2cf_edges`). CFEngine has no general primitive for
"wait for another promise" within a pass; its model is convergence plus
classes plus `bundlesequence`. The guide never says how an inferred edge is
*enforced* on-device. Either it reduces to bundlesequence ordering (which
cannot express intra-bundle pairs like caddy→litellm), or to guard classes
driven by probes (which is §13's mechanism, not inference), or to nothing. This
is a bigger threat to inference than any of the three listed, and it is
absent. `[C: high / S: high]`

**F-10b — `provides`/`requires` conflates three different obligations into one
edge type.** In the fixture, `requires` covers a path (`path:/etc/caddy/Caddyfile`
— resource existence), a service (`service:caddy` — runtime liveness), and a
secret (`secret:LITELLM_MASTER_KEY` — resolvability). One rule,
`requires-matches-provides`, produces the same edge from all three. They have
different failure semantics and different repair actions. Worse, *started* is
not *ready*: caddy started ≠ caddy serving :443, which is why systemd grew
`After=`/`Requires=`/socket activation and why §13 reaches for local probes.
The design already contains the correct mechanism for liveness in §13 and does
not reconcile it with §10. `[C: high / S: high]`

**F-10c — Cycles are undefined.** With auto-provide on by default, accidental
`requires` cycles are likely. Under retry-until-stable a cycle is harmless.
Under inference it is either a compile error — meaning the feature *rejects*
configurations the substrate handled fine, a regression introduced by the
mechanism — or a silently dropped edge. The guide says nothing. `[C: high / S: high]`

**F-10d — The token namespace has no stated scope, and every reading breaks
something.** §15 rule 3 makes "two providers of the same token" a compile
error. §3 namespaces foreign inputs "so auto-provided service tokens do not
collide," implying a site-wide namespace. But §3's roles are
`{main, backups[], peers[]}` — a backup host runs the same service and
therefore auto-provides the same `service:<name>` token. **The design's own
redundancy model trips its own uniqueness rule** under the site-wide reading.
Under a per-host reading, cross-host `requires` cannot be expressed at all,
inference is host-local only (never stated), and §13's probes become the only
cross-host mechanism. The guide does not say which. `[C: high / S: high]`

**F-10e — No falsification protocol.** Two of the three listed
counter-arguments end in "untested," with no experiment proposed. For a
document that treats its rule as a hypothesis, the absence of a test design is
the gap, not the absence of results. `[C: high / S: medium]`

**F-10f — The listed counter-argument #1 is the strongest one and is not
answered.** "Retry-until-stable may already *be* the local-knowledge answer"
is correct as far as it goes and receives no rebuttal anywhere in the guide —
it is raised in §10, repeated in §19.1, and never engaged. Listing an
unanswered objection twice is not the same as addressing it. `[C: high / S: medium]`

---

## 8. Findings register (everything else)

Concrete, checkable defects. These matter disproportionately because §16 is the
document's only demonstration of anything.

**F-16a — §16B's rendered guard is circular and would deadlock a cold
device.** The interlock's probe is `tailscale status --json`, exit 0. The
rendered bundle then guards `tailscaled`'s *start* on the class that probe
defines. A device where tailscaled is not running fails the probe, never
defines the class, and therefore never starts tailscaled. The precondition can
only be satisfied by the thing it gates. `[C: high / S: high]`

**F-16b — §16B guards the wrong entity, and the const blast radius is why.**
The stated constraint is "lockdown may not be enforced before the VPN
authenticates." The bundle `fleet-vpn` contains the VPN *transport*; the
lockdown policy does not appear in the fixture at all. With
`blocks: enclosing-bundle` fixed as a const, the guard's blast radius
necessarily includes the transport whose liveness the probe requires. The
mechanism's flagship example demonstrates the mechanism blocking its own
precondition. Combined with F-16a, this is the strongest available argument
that hand-authored illustrative output is not a substitute for a render stage.
`[C: high / S: high]`

**F-16c — §16B uses a CFEngine promise type that does not work on the platform
in the example.** The sketch renders `services: "tailscaled" service_policy => "start"`
inside a bundle whose domain is `macos-launchd-services`. The implementer map
states plainly that CFEngine `services:` "talks systemd/Windows/sysv, not
launchd." §16A, on the same platform, correctly uses a rendered plist kept
present and loaded. So the guide's two worked examples use two different and
mutually inconsistent mechanisms for the same job on the same platform, and one
of them is contradicted by the map — which the guide overrides on conflict.
`[C: high / S: medium]` (The sketch also uses `ifvarclass`, superseded by `if`
in modern CFEngine; cosmetic, but a reader checking the sketch will notice.)

**F-16d — §16A's rendered plist is probably non-functional.** A LaunchDaemon
with `UserName djbclark` runs caddy as a non-root user, while the same record
declares `provides: [port:443, port:80]`. Binding ports below 1024 on macOS
requires root, and macOS has no `CAP_NET_BIND_SERVICE` equivalent. Either the
record needs a privilege field the schema does not have, or the example does
not work. `[C: medium-high / S: medium]`

**F-16e — §16A's illustrative augments contradict its own input.** The YAML
declares `env: {LITELLM_MASTER_KEY, OPENAI_API_KEY}`; the rendered JSON carries
only `LITELLM_MASTER_KEY`. `[C: high / S: low]`

**F-16f — §16A demonstrates one of the two edges its own rule must derive.**
`caddy` declares `requires: service:tailscaled`, and `tailscaled` is a service
on the same host in the same fixture, so `requires-matches-provides` must
produce a second edge. Neither the edge nor `tailscaled` appears in the
illustrative `host_specific.json` for host `mac`. The example under-demonstrates
its own mechanism at exactly the point where cross-bundle behavior (and
therefore F-16a/F-16b's interlock interaction) would become visible.
`[C: high / S: medium]`

**F-16g — Edge direction is undefined.** `{"from": "litellm-proxy", "to": "caddy"}`
does not say whether the arrow means "runs after" or "must precede." For a data
format whose stated purpose is to be read by agents, and in a design that
demands attribution precisely so an agent can act on it, the semantics of the
principal field must be stated. `[C: high / S: low]`

**F-16h — Under §15's rule 3, the shipped happy-path fixture would not
compile.** `caddy` requires `path:/etc/caddy/Caddyfile` and `litellm-proxy`
requires `secret:LITELLM_MASTER_KEY`; nothing in `examples/` provides either,
and there is no port/path/secret registry schema in `schema/`. §15 says
"unmatched `requires` → compile error." The design's only worked example fails
the design's own stated rule. This is defensible (the registries are site-private
and unbuilt) but it needs saying, because §16's framing invites the reader to
treat the fixture as compilable input. `[C: high / S: medium]`

**F-3a — §3's schema/example pairing claim is false as implemented.** "The lint
fails if a schema arrives without its example, or the other way around." In
`bin/schema_lint.py` the pairing is a hardcoded four-entry `EXAMPLES` dict;
schemas are loaded by glob and never checked for a fixture. A new
`schema/foo.schema.json` with no example passes. `schema/common.schema.json`
already has no paired example, which proves the rule cannot hold as stated. The
paper is explicit that this is a fix *to adopt* ("nothing currently stops the
pairing from silently lapsing"); the guide states it as existing behavior. This
matters more than its size: §18's "Built today" is the document's entire
factual base, and one of its claims does not survive a two-minute check.
`[C: high / S: medium]`

**F-6a — "One `write()`. If logging fails, a line is lost, not the history."**
Overstated. An `O_APPEND` write to a regular file is atomic with respect to
offset but can be short — on a full disk, on a signal, or on an OEM freezer
kill mid-write (which §6 itself anticipates on Android). The result is a torn
final line, not a clean loss. The durability claim needs the accompanying
reader rule: the tail line may be truncated and must be discarded on parse
failure. `[C: high / S: low]`

**F-6b — No retention, rotation, or size policy for the JSONL capture.** An
append-only durable record on a phone grows without bound, and §6 also says the
agent "tails (or receives)" the log — tailing across rotation is a classic
source of silent loss. Since JSONL is *the* record of truth and SQLite is
merely an index, the retention policy is a correctness property, not an
operational detail. `[C: high / S: medium]`

**F-7a — "Rollback" is declared per operation but not analyzed.** Package
upgrades, service restarts, and destructive path writes are not generally
reversible. A `rollback` field does not make an effect undoable, and the
document does not say what happens when rollback is impossible or itself
fails. `[C: high / S: medium]`

**F-7b — Key↔host binding and re-enrollment are unmodeled.** §3 states host
identity in trust and ChangePlans is the device public key, while inventory and
roles use hostnames (`hosts: [mac]`). Who binds key to host, and with what
integrity? What happens after the event the document explicitly names as
untested — a factory reset — when the device key changes and every role
assignment, peer allowlist, and attestation set referencing it is stale? No
mechanism appears. `[C: high / S: high]`

**F-13a — Concurrent peer actions rest entirely on an assumed idempotence.**
Helpers are fungible, allowlisted by group, and there is deliberately no
distributed lock. Two helpers may therefore act simultaneously. "Idempotent" is
the whole answer, and it is an obligation placed on every future peer
operation, including ones (ADB installs, privileged helper starts) that are not
idempotent under concurrency. Peer actions also have no stated nonce, expiry,
or replay protection, unlike ChangePlans. `[C: high / S: medium]`

**F-13b — Whether a stall is actually local depends on F-10d.** "Stall is
local" holds if tokens are host-scoped. If they are site-scoped — which §3's
foreign-namespacing rationale implies — a stalled host's unmet `provides` can
propagate through inferred edges, and stall is not local. The guide asserts the
conclusion without fixing the premise. `[C: medium-high / S: medium]`

**F-3b — The private/shared inventory example is self-contradicting.** §3 says
the full host list stays private, then illustrates collisions with "two foreign
sites both shipping a host named `mac`." If host lists are private, foreign
sites do not ship hosts. The export model needs one worked example showing
exactly which fields cross the boundary. `[C: high / S: low]`

**F-5a — Push authority has no axis in the trust table.** See Claim 3. The
deploy role is fleet-wide immediate-execution authority over every operator
host, granted by role data, invisible in §14. `[C: high / S: medium]`

**F-18a — The riskiest components are scheduled last.** Signed releases and
the ChangePlan executor are step 6; the consent surface is step 9. The
implementer map flags exactly those as premium residue requiring adversarial
review. Steps 0–5 nonetheless fix the schemas, vocabulary, and rendered shapes
the ChangePlan IR and the semantic layer must later describe — so the artifact
that carries the project's stated purpose will be designed around whatever the
adapters happened to need. Risk-first ordering would prototype the ChangePlan
and one refusal round-trip early, on a single host, before adapter #3.
`[C: high / S: medium]`

**F-4a — The CFEngine augments version claim is stated twice as fact and is
uncited to a specific document.** "CFEngine has accepted as a native
data-injection layer since version 3.7." Plausible, but a reviewer will check
it, and the guide's citation discipline elsewhere is good enough that this one
stands out. `[C: low / S: low]`

**F-2a — "Four ideas in this picture come from Bcfg2" undercounts the
document's own usage.** By my count the guide uses at least six: extra entries
(§11), Actions-as-interlocks (§12), `buildfile` (§4), revision stamping
(§6/§18), `altsrc` (§13), and bundle-as-re-verification-scope (§12). The
acknowledgements are gracious and specific; the headline number is not.
`[C: medium / S: low]`

**F-19a — The open-questions list inherits §17's blind spot.** Nine questions,
none about key management, co-operator revocation, post-refusal semantics, the
semantic layer as an injection channel, protocol/version skew, cycles, the
distribution transport, or build cost. Adding those would do more for the
document's credibility than any other single change. `[C: high / S: high]`

**F-0a — The guide's genre is unstable, and it matters.** The title is "How
tendcf works" and the framing is current-state, while ~95% of the described
system does not exist. §18 is honest about this, but §§3–15 are written in the
present indicative ("Each computer runs CFEngine," "The on-device executor
maps declared capabilities to an allowlist and refuses…"). A reader who starts
at §3 will not learn until §18 that none of it runs. Given that this document
is declared to win over all others, present-tense description of unbuilt
behavior is a correctness hazard for the next agent that reads it — which is
precisely the failure mode §9 exists to prevent. `[C: high / S: medium]`

---

## 9. What would most improve the document

In descending order of value per unit of effort:

1. **Exhibit one ChangePlan end to end** — schema instance, semantic layer,
   signature envelope, an advisor `accept`, and an advisor `reject` with the
   device's state after refusal. This single addition addresses Claim 2, gap
   G1, ceiling A, and F-19a.
2. **Rewrite §17** so that the ceilings cover the trust/consent subsystem, each
   carries a metric the design itself emits, and at least one names the
   builder-capacity boundary.
3. **Name the release transport**, and split "no inbound control plane" from
   "no always-on central server."
4. **Reconcile §1's multiple trusted actors with §7's one-operator signing** —
   either scope §1 down or add the multi-signer story to §18.
5. **Fix §16's two examples** (F-16a through F-16h) or mark them as
   unvalidated sketches in stronger terms than "ILLUSTRATIVE."
6. **State the token namespace scope** (F-10d) and the cycle rule (F-10c).
7. **Restore the paper's hedges** listed in §4 of this review, since the guide
   governs.
8. **Run the §9 experiment.** It needs no fleet, no compiler, and no deployment
   — only the existing schemas and a rubric. The thesis is currently the least
   tested part of a document that could test it this week.
