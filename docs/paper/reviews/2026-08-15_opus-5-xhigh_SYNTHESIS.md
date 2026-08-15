# Synthesis of six independent reviews — `tendcf-architecture-guide.md`

**Date:** 2026-08-15. **Synthesist:** Opus 5 (xhigh). No sub-agents.
**Inputs:** the six reports dated 2026-08-15 in this directory, read in full,
plus the guide (964 lines) they target.

**Standing operator constraints applied throughout.** The planning-stage,
prose-first state is a decision, not a symptom: the pre-mortem's
documentation-to-code ratio framing is discounted (see §5). The documents stay
in confident present tense describing the designed system, with the existing
not-yet-deployed caveats where they are: no recommendation below asks for the
prose to be hedged into conditionals.

**Totals: 44 design changes, 47 document changes.** Nothing is silently
discarded; §5 lists every drop and every rejection with its reason.

---

## 1. The spine

Six reviewers, five root causes. The ordering below is by explanatory power —
how many independent findings each cause accounts for.

### S1. The document's risk apparatus is inversely correlated with its risk

**This is the strongest convergence in the corpus, found four ways by four
reviewers who did not see each other's work.**

- The **skeptical review** opens with it and calls it the reason the verdict is
  not an accept: fifteen conceded weaknesses across §10, §17, and §19, sorted by
  subsystem, give six to ordering/inference, three to comprehensiveness, three
  to local-first reporting — and **zero** to signing, keys, root rotation,
  consent, refusal, peer authorization, or release transport.
- The **red-team** produces the numerical confirmation without ever stating the
  thesis: 51 findings against §§7–9 and §§14–15, seven of them Critical, and
  §19 contains no open question corresponding to any of them.
- The **pre-mortem** organizes itself around exactly this split — Bucket 1
  ("already named," 11 causes, all in §17/§19) versus Buckets 2 and 3 ("not
  named," 25 causes). Its judgment on §19.9 is the sharpest statement of the
  mechanism: the guide's most honest line "is doing double duty as a lightning
  rod. It names a *technical* premise risk in a way that makes it feel like the
  premise has been examined."
- The **exposition review** arrives from the opposite end: the nine questions
  are unranked, so a reader cannot tell which would sink the design.

The generative mechanism is visible once the four are laid side by side: the
guide is humble precisely where Bcfg2 supplies a ready-made counter-argument,
and confident precisely where nothing external exists to argue back. The
concessions are real but they are the cheap ones. Every original,
security-critical, unbuilt mechanism is unbounded.

**Accounts for:** skeptical §0, §5.1–§5.4 (ceilings A–E), F-19a, G2, G9, G10;
the red-team's entire §§2–7 by absence; pre-mortem Buckets 2 and 3; exposition
3.2. **~40 findings.**

### S2. Every control in the trust layer is authored, delivered, and evaluated by the party it exists to constrain

The red-team's central finding, stated as a table of eight controls that all
terminate at the operator: local trust policy, the advisor key, the extra
advisor prompt, resource legality, the nonce, the semantic briefing, and the
executor itself. "A label in inventory does not enforce this. The executor
does" cannot carry the weight §14 puts on it, because the executor is operator
code running an operator policy checking an operator-enrolled key over an
operator-chosen nonce about an operator-generated briefing. The one artifact
the consenting person contributes is a signature over the proposer's nonce.

Two other reviewers reach the same wall from different sides. The **skeptical
review**'s G2 finds §1's "more than one trusted person can act" reconciled with
§7's "sized for one operator" nowhere, and its ceiling B names the trigger: the
second operator who must author a release without the first's key. The
**pre-mortem**'s U2 finds that no second human is named anywhere in 964 lines —
the consent surface has a user count of zero.

The red-team's class fix is the smallest change that makes most of §§7/8/14 true
as written: **a device-local trust root the release path cannot write.** Until
that exists, the trust layer is, in its own words, "a well-designed audit trail
with the word 'consent' on it."

**Accounts for:** TC-01 through TC-14, TC-25, TC-27, TC-35, TC-38, TC-42;
skeptical G1, G2, ceilings A and B; pre-mortem U2, N7. **~25 findings.**

### S3. §9's own standard is not applied to the document's own load-bearing claims

Three reviewers independently picked up §9 and used it against the guide.

- **Red-team TC-48** inventories the trust layer's security properties — "it
  never authorizes," "the advisor never authorizes; the executor does," "free
  prose must point at the exact fields it is summarizing," "only the plan
  constrains the effect" — and observes that every one is a remembered
  convention, which §9 says will eventually break silently. **TC-32** applies it
  to the capability vocabulary: the most security-load-bearing list in the
  design is currently a phrase in a sentence, with no schema, no example, and no
  negative fixture.
- **Consistency audit F1** finds the same defect in the one component that
  exists: §3 claims the lint enforces schema↔example pairing in both directions,
  but the pairing is a hand-maintained four-entry dict — "§9's own rule is
  exactly what this violates."
- **Skeptical F-3a** finds it independently, and adds the detail that makes it
  a drift instance too: the *paper* is explicit this is a fix to adopt
  ("nothing currently stops the pairing from silently lapsing"); the *guide*
  states it as existing behavior.
- **Pre-mortem U4** is the meta version: to execute Step 3 an agent must hold
  the 964-line guide, the 652-line map, 40 decisions, five schemas, twelve
  fixtures, and nine open questions simultaneously. The rule was applied
  rigorously to the Site Model and never once to the specification of the Site
  Model.

§12 is repeatedly cited — by the consistency audit as a verified claim, by the
red-team as the right precedent (TC-23, TC-48) — as the one place the project
did this correctly: `blocks` and `report` are schema constants. That precedent
was not extended to the layer where it matters more.

**Accounts for:** TC-32, TC-45, TC-48; F1, F4, parity P2; F-3a; U4; and the
form of the fix for TC-01, TC-07, TC-23. **~15 findings.**

### S4. The precedence rule makes the least-specified document normative

The guide declares "Where any other living document disagrees on the current
design, **this guide wins**." **Red-team TC-51** shows what that costs: the map
states a 2-of-3 offline root and the guide states no root threshold at all, so
the normative text permits the 1-of-1 root a prior red-team called Critical; the
map states NAR digests in the manifest and §7's field list has no digest at all;
the map's §14.2–14.4 flag the ChangePlan IR and advisor loop as "do not
improvise, independent adversarial review before build" and the guide carries no
equivalent gate.

**Skeptical §4** finds the same drift from the other direction, listing seven
hedges and figures that were present in the paper and absent from the guide —
including IaC-Eval's actual number, the paper's own "we are aware this rule can
be used to justify almost anything," and the only self-critical finding about
the one component that exists (two of twelve fixtures exposed useless error
messages). Individually compressions; together a systematic directional drift,
in the document that governs.

The **consistency audit**'s F2 and F3 are the same failure in miniature, running
the other way: `common.schema.json` cites guide §8 for a rule that lives in §6,
and cites `§12 Step 0` — DEFINITIVE-**v2** numbering — for a build order that is
now §18.

**Accounts for:** TC-51, TC-36, TC-26 (partly), RT-05's disposition, skeptical
§4's seven items, F2, F3. **~12 findings.** One sentence fixes the governance
half.

### S5. The riskiest and most falsifiable claims are scheduled last, so nothing that could refute the design gets tested

- **Pre-mortem A1/A2:** the build order puts validation of the project's claimed
  novel contribution at Step 3, behind two platform adapters; §9 is load-bearing
  for the entire schema-first strategy and there is no experiment in the plan
  that could tell you if it is wrong.
- **Pre-mortem N1:** Step 2 (Android) is a systems-programming research spike
  wearing a build-step's clothes, and it sits *upstream* of the compiler because
  inference "waits until types exist on two platforms." Its failure mode is
  total.
- **Skeptical F-18a:** signed releases and the ChangePlan executor are step 6,
  the consent surface step 9 — exactly the components the implementer map flags
  as premium residue — while steps 0–5 fix the schemas and rendered shapes those
  artifacts must later describe.
- **Red-team TC-50:** consent (step 9) ships before artifact provenance (step
  10+), which is verbatim what the prior red-team's RT-08 said not to do.
- **Skeptical Claim 1, evidence 4** and **F-10e:** the falsification protocol for
  §9 needs no fleet, no compiler, and no deployment — only the existing schemas
  and a rubric. Its untested status is therefore a choice, not a constraint.

**Accounts for:** A1, A2, A7, A11, N1, N2, N6, N10, the demotion and all three
cuts; F-18a, F-10e, Claim 1's evidence list; TC-50, TC-32. **~18 findings.**

---

## 2. What only appears when the six are read together

Four results no single reviewer could have produced.

### E1. Two reviewers independently designed the same alternative architecture, from opposite premises — and it structurally dissolves a large slice of the red-team's findings

The **skeptical review**'s Alternative A (arrived at from security-claim
analysis) and the **pre-mortem**'s CUT-1 + CUT-3 (arrived at from build-cost
analysis) are the same architecture:

- compiler does merge → conflict check → render only; no inference stage, no
  `nix2cf_edges`, no origin-tracking machinery (Alt A; CUT-3);
- what it renders per host is a complete, fully-resolved goal file;
- the ChangePlan is **mechanically the diff** between the host's currently-signed
  goal file and the proposed one — which CUT-1 independently names as the thing
  to keep ("the Step 3 'what would device X receive' render");
- the executor's allowlist is derived from that diff, not from a hand-maintained
  closed vocabulary.

Neither reviewer saw the other's findings. Put the red-team's list against it
and the diff-derived model is not merely cheaper, it is *structurally immune* to
several Critical and High findings rather than merely mitigating them:

| Red-team finding | Under the current model | Under a diff-derived plan |
| --- | --- | --- |
| TC-29 baseline mismatch on a stale device | Needs a new baseline field and a refusal rule | A diff **is** baseline-declaring by construction |
| TC-32 no capability vocabulary exists | Must be written, versioned, reviewed | No vocabulary to cover — what is not in the diff cannot be done |
| TC-31 unknown/deprecated capabilities | Needs versioning and skew policy | Same — no vocabulary, no skew |
| TC-10 all-or-nothing accept | Needs per-operation accept vectors | A diff is naturally per-hunk |
| TC-26 plan binds names, not bytes | Needs digests added to every operation | A complete goal file names values, not references |
| TC-25 a plan can rewrite the trust policy | Needs a privileged-resource class | Still needed — the diff can still touch it |
| TC-23 executor refuses declarations, not effects | Unsolved | **Still unsolved** — package installs still run vendor code |

Skeptical's own accounting agrees on the last two: "the enclosure problem
survives; the *vocabulary* problem does not."

This is the strongest design signal in the material and it is a synthesis
artifact — neither report makes this argument, because neither had the other's
findings list.

### E2. The red-team's fix for TC-43 breaks the justification §15 provides for inference

TC-43 finds the lookup CLI and the near-miss catalog to be a designed-in
enumeration oracle over private site data, and prescribes scoping answers to
the caller's own layer. But §10's *second* conceded objection — that
`provides`/`requires` may only relocate global knowledge — is answered in the
guide by "auto-provide plus a lookup CLI (§15) is the mitigation." A
layer-scoped lookup cannot answer a foreign or shared-layer author's discovery
question, which is precisely the case the mitigation exists to serve. **Privacy
and discoverability are in direct collision here and neither document notices.**
Pre-mortem N17 supplies the third leg: the mitigation is itself untested and is
parked below §19's numbered list.

### E3. The two-platform gate couples the project's most falsifiable claim to its riskiest platform step

§10 states "inference does not start until real type definitions exist on two
platforms." §18 makes Android the second platform. Pre-mortem N1 argues Android
may not be achievable at all, and skeptical F-10a argues an inferred edge may be
*unenforceable in CFEngine* regardless of platform count — CFEngine has no
general primitive for "wait for another promise" within a pass. So the design's
central novel claim is gated behind the step most likely to fail, for a reason
(two platforms) that does not address the mechanism's actual open question (is
the edge enforceable at all). The gate should be dropped or re-pointed at
Linux + macOS. The pre-mortem's demotion does this incidentally; it should be
done deliberately.

### E4. The guide's flagship interlock example is a cold-boot deadlock, which is direct evidence for the cold-path concession the guide files as a footnote

Skeptical F-16a: §16.B's probe is `tailscale status --json`, and the rendered
bundle guards `tailscaled`'s *start* on the class that probe defines — a device
where tailscaled is not running never defines the class and therefore never
starts tailscaled. §10 separately concedes "no device in this fleet has been
provisioned from factory reset by this automation. The cold path is untested."
Pre-mortem A11 notes that concession appears in the body but in neither §17 nor
§19 nor the build order. The interlock example is the concession's first
confirmed instance, discovered by reasoning, in the document's own worked
example.

---

## 3. The split

**Rule applied.** *Design change* = the thing has to change (architecture,
mechanism, schema, or plan) — including cases where the "fix" is one sentence,
if that sentence commits to a mechanism the design does not have. *Document
change* = the design is fine and the text is wrong, missing, or mis-scoped —
including rescoping a claim down to what the design actually delivers.

Where a finding admits both (build the mechanism, or shrink the claim), it is
listed as a design change with the document escape noted, because taking the
escape concedes a property the guide currently asserts. **Nine findings were
moved from document to design on this test and are marked `[MOVED]`.**

### 3.1 DESIGN CHANGES — 44

#### A. The trust root and the consent binding (S2's class fix)

| # | Change | Sources |
| --- | --- | --- |
| DC-1 | **Establish a device-local trust root the release path cannot write.** Advisor key, consent policy, peer allowlist, device resource policy are set at first-run into storage the executor reads and the release cannot modify; changing any is a `trust.amend` capability needing the *current* advisor key plus a local human act. | red-team central, TC-25, TC-12, TC-27, TC-38, TC-42 |
| DC-2 | **Bind the accept to `H(plan) ‖ H(briefing) ‖ executor-generated device nonce.** Per-device advisor subkeys; an accept valid for exactly one `target`; single-use bound to the monotonic release counter rather than to an unbounded nonce set. | TC-02, TC-11, TC-20 |
| DC-3 | **Brief the advisor with the typed plan.** Free text travels inside a labelled `untrusted_text` container with no instruction authority; prose to the deciding model is a pure deterministic function of the canonical plan, regenerated and compared by the executor; ship an adversarial briefing fixture suite that must produce `reject`. | TC-01, TC-03, TC-05, TC-06, TC-07, TC-49; skeptical §2 (semantic layer as persuasion channel) |
| DC-4 | **Advisor identity and privacy.** Socket mode returns a keystore-backed signature or is invalid for `consented`; attestations carry a self-declared advisor descriptor (mode/identity/version); briefings crossing to a remote advisor are subject to §3's export policy; attestation thresholds weight by independent release authority, not device count. | TC-04, TC-08, TC-13, TC-41 |
| DC-5 | **Post-refusal semantics.** Rejects persist keyed by plan content hash; a `withdraw` verb; divergence is a first-class device state (§11's `deliberately-unmanaged` is the existing vocabulary); separate "highest metadata seen" from "highest applied." | TC-19, TC-30, TC-33b; skeptical G1, ceiling A |
| DC-6 | **Anti-bundling.** Accept is a vector over operation IDs, or a schema rule that a plan carries one capability class. | TC-10 |
| DC-7 | **Someone must hold the aggregate.** The executor computes privilege transitions from local state and hands them to the advisor as facts, with device history from §6's existing record. | TC-09, TC-47 |
| DC-8 | **Bounded degraded mode.** One deny predicate with no branches; a human-scale, person-settable timeout; after N days of advisor unreachability, escalate to a local physical-confirmation path rather than failing closed forever; "advisor unreachable" is a reported, visible state. | TC-15, TC-21, TC-22 |

#### B. What a signed plan actually constrains

| # | Change | Sources |
| --- | --- | --- |
| DC-9 | **Name a per-platform confinement for operations that execute** (sandbox-exec/ES, seccomp+Landlock or systemd sandboxing, the app sandbox), rendered from the capability and not author-settable — **or** downgrade §7 to "refuses any *operation* outside that set." `[MOVED]` — the wording fix alone concedes the security core. | TC-23; skeptical Claim 2 |
| DC-10 | **Bind policy source by digest.** The CFEngine tree and generic bundle are plan resources with a content digest; a change to policy source is its own high-privilege, always-human capability. D30's `.cf` escape hatch already exists in the register. | TC-24 |
| DC-11 | **Artifact digests on every operation that installs or replaces content,** covered by the accept, re-verified immediately before apply (not at receipt). | TC-26; RT-02/RT-04 residue |
| DC-12 | **Ship the device its own resource policy** so the executor re-checks resources locally instead of taking the signer's word. | TC-27 |
| DC-13 | **Plans declare the baseline release they assume;** the executor refuses on mismatch. Collides with ahead-of-time rendering on purpose. | TC-29 |
| DC-14 | **Rollback in the typed vocabulary:** capability-checked, briefed ("if this fails, the following will run"), covered by the same accept; rollback targets compared against the high-water mark; state what happens when rollback is impossible or itself fails. | TC-28, TC-33a; skeptical F-7a |
| DC-15 | **Version the capability vocabulary,** bind the version in signed root metadata, refuse unknown *or* deprecated with a distinct reason, move the accepted version forward only, deprecate by removal-with-a-date never by alias. | TC-31 |
| DC-16 | **Write the ChangePlan schema, the capability enum, and the trust-policy shape, with paired examples and negative fixtures — and exhibit one plan end to end** (schema instance, semantic layer, signature envelope, an accept, a reject, and the device's state after refusal). | TC-32; skeptical Claim 2 evidence 3, recommendation 1 |
| DC-17 | **Source-to-signing provenance:** isolated signing checkouts, no signing from task worktrees, two-person review of trust-boundary changes, attestations binding commits to artifacts. Dropped wholesale between RT-03 and the guide. | red-team §10 (RT-03 disposition) |

#### C. Keys, root, and time

| # | Change | Sources |
| --- | --- | --- |
| DC-18 | **Emergency role:** thresholded like root, mandatory expiry so an unrenewed revocation lapses rather than bricking, never leaves a device with zero valid signers, recorded locally where the person's tools can read it. Replace the tighten/loosen test with a bounded enumeration of consent-free metadata actions. | TC-16, TC-17 |
| DC-19 | **Freeze:** adopt a timestamp role or drop the claim from §7; state metadata lifetimes, a maximum supported offline period, behavior on expired timestamp with valid root, monotonic-clock handling, and a fast-forward reset path. `[MOVED]` — "drop the claim" is a document edit that concedes a property §7 asserts today. | TC-18; skeptical Claim 2 |
| DC-20 | **First-run root.** Root rides a channel the device authenticates independently of the installer (APK signing cert, notarized helper, distro packaging); at least one comparison channel that does not terminate at the operator; the root threshold stated in numbers in the *guide*; every root version retained and served; a written out-of-band runbook; a fingerprint compare that is machine-assisted rather than eyeball-hex. | TC-34, TC-35, TC-36, TC-37 |
| DC-21 | **Multi-operator signing** — threshold, delegation, per-role scoping, co-operator revocation — **or** an explicit scope-down of §1's "more than one trusted person can act." `[MOVED]` — scoping §1 down is a document edit that retracts a stated product goal. | skeptical G2, ceiling B; pre-mortem N7 |
| DC-22 | **Model key↔host binding and re-enrollment.** Trust and ChangePlans key on the device public key while inventory and roles use hostnames; nothing says who binds them, or what happens after a factory reset changes the key and every role, allowlist, and attestation set referencing it goes stale. | skeptical F-7b |

#### D. Peers, roles, transport

| # | Change | Sources |
| --- | --- | --- |
| DC-23 | **Peer authorization mechanics.** Groups compile away to explicit device keys so membership changes appear in the target's plan diff; verbs terminate at a constrained endpoint, and where the fallback is a general remote shell say plainly that the peer is operator-equivalent; the allowlist check lives in a component whose availability is independent of what peer help repairs; per-device ADB keys, never a fleet key; nonce, expiry, and replay protection for peer actions. | TC-38, TC-39, TC-40; skeptical F-13a |
| DC-24 | **Role-assignment disagreement needs an epoch or fencing rule.** Role assignment is release data, releases arrive at different times by design, so disagreement about who holds a role is the normal state, not the exception. | red-team §10 (RT-07 disposition) |
| DC-25 | **Push authority becomes a sixth axis in §14 with a named enforcement point.** Whoever holds the deploy role can trigger immediate convergence on every operator host; that authority is granted by role data and is invisible in the trust model. | skeptical F-5a, Claim 3 |
| DC-26 | **Name the release and metadata transport per tier,** with its availability assumption and what breaks when it is unavailable for N days; say what `cf-serverd` on every host is for when no host serves another. | skeptical Claim 3, evidence 1 and 3 |
| DC-27 | **Converge-agent resource limits:** download limits, quotas, backoff, watchdog, kill switch. Absent from the guide entirely. | red-team §10 (RT-07 disposition) |

#### E. Site Model and compiler mechanics

| # | Change | Sources |
| --- | --- | --- |
| DC-28 | **The ordering machinery has five undefined semantics:** token namespace scope (site-wide trips the design's own backup-host redundancy model; host-local makes cross-host `requires` inexpressible), the cycle rule, how an inferred edge is *enforced* on-device at all, edge direction, and the three different obligations (`path` existence, `service` liveness, `secret` resolvability) that one rule collapses into one edge type. F-10a is a bigger threat to inference than any of §10's own three. | skeptical F-10a–d, F-16g, F-13b |
| DC-29 | **Interlock extent, not just expression.** `blocks: enclosing-bundle` is a `const`, but bundle membership is author-settable, so an author narrows the blast radius by choosing the bundle. Separately, §16.B's probe gates the very service that satisfies it. | skeptical G5, F-16a, F-16b |
| DC-30 | **Two missing schema affordances surfaced by §16:** no field distinguishes LaunchDaemon from LaunchAgent, and no privilege field explains how a `UserName`-scoped daemon binds ports 80/443; §16.B also renders CFEngine `services:` on a launchd host, which the map says does not work there. The supervisor abstraction is claimed at five and exhibited at one, in a form that already leaks (`launchd:` sub-object inside a supervisor-independent fact). | skeptical F-16c, F-16d, G3 |
| DC-31 | **The port/path/secret registries do not exist,** so under §15's rule 3 the shipped happy-path fixture would not compile — `path:/etc/caddy/Caddyfile` and `secret:LITELLM_MASTER_KEY` are required and provided by nothing. | skeptical F-16h |
| DC-32 | **Secrets and lookup scope.** A deny-by-default resolver policy keyed on (service identity, host key, capability, release) — §14's "secretspec resolver" cell names an enforcement point with no policy; `secret:` excluded from enumeration and near-miss output; lookup answers scoped to the caller's layer. **See E2 — this collides with §15's role as inference's mitigation.** | TC-43, TC-44; RT-06 |
| DC-33 | **Provider pre-registration and alias/binding edits become a distinct review class** and appear in the plan diff. | TC-46 |
| DC-34 | **JSONL retention, rotation, and the torn-tail reader rule.** When JSONL is the record of truth, retention is a correctness property; and an `O_APPEND` write can be short, so the tail line must be discarded on parse failure. §6's "one `write()`, a line is lost, not the history" is overstated as written. | skeptical F-6a, F-6b |
| DC-35 | **Canonicalization rule for the "show me device X" render,** without which the pure-function/regression-test claim fails: the plan carries a nonce and an expiry and the release carries signatures. | skeptical G7 |
| DC-36 | **Upstream-heal equivalence is computed, never argued:** byte/derivation equivalence or a separately-signed human approval of the semantic delta, with local fixes carrying a mandatory expiry. | TC-14; RT-09 |
| DC-37 | **Reclassification `not-yet-migrated` → `deliberately-unmanaged` becomes a reviewed act.** This is the collapse mechanism §19.3 does not name: under pressure nobody grinds the count down, they reclassify, and the two-reason design degrades to the bare on/off flag §11 rejects. | pre-mortem A3 |
| DC-38 | **Each §17 ceiling gets a metric the design itself emits.** All three are currently frequency thresholds with no metric, and the design cannot measure its approach to any of them — ceiling 1 is unfalsifiable inside its own architecture, since detecting it needs the central spine the design declines to build. | skeptical §5.2 |

#### F. Plan, sequencing, capacity

| # | Change | Sources |
| --- | --- | --- |
| DC-39 | **Resequence the build order.** `buildfile` render first (§4 already calls it "almost free" and "the first piece of the compiler"; it is currently buried inside Step 3 behind Android); Linux before Android; a provenance gate before consent; a ChangePlan prototype and one refusal round-trip on a single host before adapter #3; transcribe reality before finalizing schemas. Moves the first genuinely valuable outcome from ~month 14 to ~month 4. | pre-mortem demotion, N1, N2, N10, A11; skeptical F-18a; TC-50 |
| DC-40 | **Take the cuts the two independent reviewers converged on** (see E1): inference engine cut, fields kept; TUF-subset + capability executor kept as written spec, not built at Step 6; consent implementation kept as spec, not built at Step 9. Reduces the honest sizing from 2.5–5 years to 9–18 months of part-time work. | skeptical Alternative A; pre-mortem CUT-1, CUT-2, CUT-3 |
| DC-41 | **Run the §9 falsification experiment.** N agent-authored service records under `depends_on` + compiler-side completeness check versus `provides`/`requires`, scored by error class; plus a decision procedure applied to three mechanisms the design *rejected*. Needs no fleet, no compiler, no deployment. | skeptical Claim 1 evidence 1–4, F-10e; pre-mortem A2, A7 |
| DC-42 | **Test infrastructure beyond Step 0.** Twelve negative fixtures is good discipline for a validator and does not extend to a compiler (golden renders), an executor (device integration), or three adapters — and self-hubbed CFEngine on Termux CI is not buyable. | pre-mortem N11 |
| DC-43 | **De-concentrate the primary workstation,** which is currently the compiler host, the signing host, the operator-tier device, Step 1's target, and the development machine — and cannot be reimaged. | pre-mortem N8 |
| DC-44 | **Right-size the governance ceremony to one person.** A 40-decision register with an `Approved-change:` trailer gate where the approver is the author makes *changing your mind* expensive, which is exactly wrong for a design carrying nine open questions whose resolution requires reversing decisions. | pre-mortem N9, U8 |

### 3.2 DOCUMENT CHANGES — 47

#### Cheap and unambiguous (an afternoon, all of them)

| # | Change | Sources |
| --- | --- | --- |
| DOC-1 | **Amend the precedence rule:** the guide wins on *design*; named security parameters in the implementer map are floors the guide does not relax. One sentence. | TC-51 |
| DOC-2 | **§3's schema↔example pairing claim.** Derive `EXAMPLES` from the filesystem with an explicit allowlist for shared-definition schemas, or reword §3 to say the rule holds for the four registered pairs. Both reviewers prefer the machine-checkable option; the paper already treats it as a fix to adopt. | F1; skeptical F-3a |
| DOC-3 | **Token kinds** — the schema admits eight (`service` `port` `path` `class` `package` `device` `network` `secret`); guide §15 and paper §2.9 both print six and an ellipsis, in a sentence asserting closure. Point at `common.schema.json#/$defs/capability_token` rather than re-copying; the inline list has now drifted in two places at once. | F4, parity P2, TC-45 |
| DOC-4 | **Rename one of the two "capability" lists** (§7's operation vocabulary vs §15's token kinds, the latter literally named `capability_token` in the schema, with a fixture called `07-typo-capability-kind`). | TC-45 |
| DOC-5 | **Fixture wording.** Change `examples/services.yml` to say "the mesh VPN" so the guide's §16.B and the paper's §2.6 become the verbatim excerpts the paper explicitly guarantees. One edit; resolves both findings. Do **not** weaken the paper's provenance sentence. | F5, parity P1 |
| DOC-6 | `common.schema.json` `$defs.release_stamp` cites guide §8; release stamping is §6. | F2 |
| DOC-7 | `common.schema.json` cites `§12 Step 0` — v2 numbering. Build order is guide §18 / map §13. (`§0 rule 6` in the same file is correct against v3 — do not "fix" it.) | F3 |
| DOC-8 | `bin/schema_lint.py` docstring says "Three layers" and lists four. | F6 |
| DOC-20 | §16.A's illustrative augments carry only `LITELLM_MASTER_KEY`; the YAML declares `OPENAI_API_KEY` too. | skeptical F-16e |
| DOC-21 | §16.A omits the second edge its own rule must derive: `caddy` requires `service:tailscaled`, on the same host in the same fixture. | skeptical F-16f |
| DOC-23 | "Four ideas in this picture come from Bcfg2" undercounts — at least six are used (extra entries, Actions-as-interlocks, `buildfile`, revision stamping, `altsrc`, bundle-as-re-verification-scope). | skeptical F-2a |
| DOC-24 | Cite the "CFEngine has accepted Augments since 3.7" claim to a specific document; it is stated twice as fact and the citation discipline elsewhere is good enough that it stands out. | skeptical F-4a |
| DOC-26 | **Dead links.** §2 and Further Reading item 2 use `usenix.org/legacy/publications/library/...` for LISA '05, which 404s; the working form is `usenix.org/legacy/events/lisa05/...`. Verified by the exposition reviewer while confirming the numbers. | exposition §6 |

#### Claims that must be rescoped to what the design delivers

| # | Change | Sources |
| --- | --- | --- |
| DOC-14 | **Split "no inbound control plane and no central authority holding credentials"** (defensible, and what the design achieves) **from "no always-on central server"** (not supported: git sync implies a git remote, TUF implies a repository to poll). The Flux analogy is borrowed for the stronger claim; Flux requires an always-on git server. Fix the §2 diagram's bare arrow at the same time. | skeptical Claim 3 |
| DOC-15 | Say what `cf-serverd` on every host is for when each host is its own hub — either a no-op or the peer transport the document has not described. | skeptical Claim 3 evidence 3 |
| DOC-16 | §11's "the only mechanism in the design that notices two writers changing the same device" is false. A second writer that modifies *described* state is caught by ordinary convergence, and §6's outcome vocabulary already carries `repaired`. It makes default-on comprehensiveness look more load-bearing than it is. | skeptical G6 |
| DOC-17 | §6's "costs nothing new to stand up" kept the paper's conclusion and dropped its premise (the observability stack already runs for other purposes), leaving a bare cost claim over a receiver, a schema mapping, a transport, and authentication. | skeptical G8 |
| DOC-18 | §1 states publishability as a goal met while §18 makes extraction step 10+, "demand-driven" — with a chicken-and-egg: a second person cannot run it until it is extracted. | skeptical G10 |
| DOC-19 | §3 says the full host list stays private and then illustrates collisions with "two foreign sites both shipping a host named `mac`." If host lists are private, foreign sites do not ship hosts. Needs one worked example of which fields cross the boundary. | skeptical F-3b |
| DOC-22 | Strengthen §16's provenance framing, or mark the sketches as unvalidated in stronger terms than "ILLUSTRATIVE" — given DC-29/DC-30, the examples do not currently work as engineering. | F5; skeptical F-16a–h |
| DOC-25 | "Lost in the Middle" is a TACL 2023 result asserted flatly as a live premise in a 2026 document. Re-ground it or date-qualify it; long-context handling has moved. | skeptical F-9c |
| DOC-47 | §10's rejection of catalog compilation rests on an audit of a system §0 declares "legacy reference only… described in generic terms," so the reader cannot inspect the evidence for the design's single largest rejection — and it transfers a negative result about System A to System B, which has a different service model, platform mix, and machine authors. | skeptical G4 |

#### The risk apparatus (S1's fix — pure writing, highest value per hour)

| # | Change | Sources |
| --- | --- | --- |
| DOC-9 | **Restore the seven items dropped between paper and guide:** IaC-Eval's 19.36%; "we are aware this rule can be used to justify almost anything"; "a wrong explanation can still talk a person into accepting a change they would have refused"; "the three gaps we found, we found by reasoning… strong evidence the list is incomplete"; "we are aware this is the decision most likely to be wrong" on local-first; the two-of-twelve-fixtures finding; the observability-stack premise. **None of these is a conditional about whether the system works** — they are present-tense statements about evidence and confidence — so restoring them is compatible with the operator's prose constraint. | skeptical §4 |
| DOC-10 | **Extend §19 to the subsystem the document calls the point:** key management, co-operator revocation, post-refusal semantics, the semantic layer as an injection channel, protocol/version skew, cycles, the distribution transport, and build cost. Note also that §19.9 currently absorbs premise-risk attention while touching none of the four premise risks in the pre-mortem's Bucket 3. | skeptical F-19a, §0; pre-mortem A9 |
| DOC-11 | **Rewrite §17.** Fix the "every choice above… three ceilings follow" non-sequitur in its own first paragraph, and add the five ceilings that are actually load-bearing: consent (once refusal is exercised rather than offered), multi-operator, builder capacity, the AI-authorship premise in both directions, and the adversarial ceiling (a prompt-injected authoring agent producing a valid, signed, capability-conformant malicious plan). The three named ceilings bound exactly the three mechanisms borrowed from Bcfg2. | skeptical §5.1, §5.4 |
| DOC-12 | **Two of the three named ceilings are already crossed for this fleet.** For a household fleet the operator's recurring question *is* the fleet-wide query ("are all my phones up right now"), and patching the daily-driver Mac carries a bounded clock every single time. §17 states them in the abstract and never checks them against this fleet. Note also §19.6 is adequate for correctness and inadequate for morale, which is the binding constraint in a solo project. | pre-mortem A5, A6, A10 |
| DOC-13 | **Rank the nine open questions.** One sentence: 1, 2, and 9 would change the design if answered against it; the rest are calibration. | exposition 3.2 |
| DOC-35 | **Promote the cold-path concession** from §10's body into §19, §17, and the build order — see E4. | pre-mortem A11 |
| DOC-36 | **Connect §19.3 to §19.8.** The comprehensiveness backlog does not fail by rising; it fails by reclassification, which is §19.8's escape-hatch failure applied to §11. Say who draws domains, on a machine with tens of thousands of files, and at what budget (§19.4). | pre-mortem A3, A4 |
| DOC-40 | The lookup CLI's untested status sits *below* §19's numbered list. It is the stated mitigation for §10's second objection; a mitigation that is itself untested belongs inside the list. | pre-mortem N17 |

#### The argument (§9 and §10)

| # | Change | Sources |
| --- | --- | --- |
| DOC-27 | **Reframe §9's axis.** The design's own §4 stage-2 conflict checker is a *global* check that makes a globally-scoped constraint safe for an author who knows nothing about the rest of the system — so the operative axis is not local-vs-global knowledge but **who holds the global knowledge, the author or the checker**. Once that is on the table, `depends_on` + a compiler-side completeness check is a live competitor that the document never compares against, and §19.2's requested counter-example sits two sections earlier in the same document. Add: §15 concedes the rule is "don't require the graph, not don't require names," which is a much thinner distinction than local-vs-global; rules 1 and 2 are in tension rather than complementary; and auto-provide is the rule's own failure mode running backwards (a local rename with a global effect, caught only because rule 2 rescues rule 1). | skeptical Claim 1, F-9a |
| DOC-28 | **State §9's boundary.** It is an excellent authoring rule and a dangerous authorization rule: security properties are global invariants, and the design is local everywhere, which is what makes the composition attacks work. Say the rule governs the authoring surface and name the component that holds authorization context. | TC-47, TC-49 |
| DOC-29 | Of the twelve negative fixtures, roughly three test the reference/existence class and nine test schema shape — so the one component that exists is weighted toward the error category the guide's own cited evidence calls smallest. The map's D28 states the correct priority; the guide cites the evidence and does not act on it. | skeptical F-9b |
| DOC-30 | **§10's own counter-argument #1 is the strongest and is never answered** — "retry-until-stable may already *be* the local-knowledge answer" is raised in §10, repeated in §19.1, and rebutted nowhere. Answer it or say plainly that it is open. | skeptical F-10f |
| DOC-44 | Put the actual IaC-Eval number in §9. "First-try correctness is low" without a figure undercuts the persuasive force the paragraph is going for, and the paper had the number. | exposition 4.3; skeptical §4 |

#### The plan, honestly described

| # | Change | Sources |
| --- | --- | --- |
| DOC-31 | **Annotate §18 with honest sizing.** It reads as eleven comparable increments and is the only sequencing artifact the project has; steps 2, 3, and 6 consume more than half the total and each occupies one table row. Include the unbudgeted costs the pre-mortem names: CFEngine skill acquisition with no colleague to ask and near-zero macOS/Android corpus; maintaining the incumbent throughout; the ~12-project attention portfolio. | pre-mortem 3.1, N4, N6, N15, U3, U6 |
| DOC-32 | **State the cost of the incumbent-purity rule.** "Not a dependency, not an upstream, and not copied into this project" applied to a 919-commit, 33,067-file production stack means re-deriving Termux runtime, ADB reconnect, Shizuku gating, an SSH CA, and outage alerting from scratch. It buys publishability and cleanliness; it costs conservatively a year; the guide never states the trade. | pre-mortem N3 |
| DOC-33 | §2 lists "tool forks (optional) — nix2cf, sudo-secretspec, Shizuku" as if third-party. All three are the author's own, all three are on the critical path (secrets resolver, the §13 worked example, Step 3), and tendcf's schedule is the sum of four schedules through one person. | pre-mortem N5 |
| DOC-34 | **Step 0's "Remaining" cell holds two research problems, not chores** — trust-policy shape is schematizing §14's five-axis policy, the hardest design in the document; generic unit-writers is abstracting a launchd-only registry across systemd, runit, and Jobber with none implemented. Add the capability vocabulary to that cell; §18 does not name it at all. | pre-mortem N12; TC-32 |
| DOC-37 | **Price the publishability tax and state what problem tendcf solves that the incumbent does not.** Namespacing, foreign inputs, explicit exports, the engine/site split — much of the abstraction budget exists for a second adopter, extraction is step 10+, and a single-site version is meaningfully smaller and never costed as an alternative. The honest current answer is "better ideas," and no outage, scaling limit, or second operator is driving this. | pre-mortem N13, U5 |
| DOC-38 | The Nix authoring frontend is a whole second authoring system in a subordinate clause of §3; correctly deferred, but its presence keeps it alive as a future obligation and colours schema decisions now. | pre-mortem N14 |
| DOC-39 | Push-vs-pull is deferred to Step 8 but self-hub bootstrap semantics on three platforms are the substrate for both, so a wrinkle on macOS or Termux surfaces after everything is built on the assumption. | pre-mortem N16 |

#### Exposition and prose

| # | Change | Sources |
| --- | --- | --- |
| DOC-41 | **Opening.** Signal which §1 goal is load-bearing (the AI-authorship sentence is the seed of the thesis and sits unmarked among the Nix aside); consider leading with the refusal sentence, the most persuasive line in the introduction; gloss `TUF-subset`, `Augments`, Promise Theory, `ncf`, and `def.json`/`host_specific.json` on first use; add a one-sentence "how to read this" pointing at the load-bearing sections. | exposition 1.1–1.4, 2.5, 5.6, 5.8 |
| DOC-42 | **Structure.** Merge §12 and §13, or add an explicit bridge ("§12 was a single host waiting on itself; this is a host waiting on another host"); move §15 next to §10, which is where its question is raised; move §14 out from between them. | exposition 2.1–2.3 |
| DOC-43 | **§9's placement.** §3–§8 are read without the frame that justifies them, and §9 has to retrofit them. Add a forward-reference from §2 rather than promoting the rules — see contradiction C-4. | exposition 4.1, 4.2 (amended) |
| DOC-45 | **Prose.** Gloss `mergedata()` or cut it to the implementer map; expand "Stall is local. Idempotent." into a sentence with a subject; rewrite §11's "Fleet-wide comprehensiveness on a machine that was never built under it is not survivable"; split §17's compound bullets into claim + why. | exposition 5.1–5.3, 5.5, 2.4 |
| DOC-46 | Give §19 an explicit closing line rather than trailing off into the token-discovery aside. | exposition 3.3 |

---

## 4. De-duplication and contradictions

### 4.1 Merged — the same finding, found twice or more

| Finding | Reviewers | Note |
| --- | --- | --- |
| §3's pairing claim is false as implemented | consistency **F1** + skeptical **F-3a** | Independent; skeptical adds the drift detail (the paper says it is a fix *to adopt*), which promotes it into S4. |
| Token kinds under-enumerated | consistency **F4** + parity **P2** + red-team **TC-45** | Three reviewers, two documents, one schema. Confirms the pointer-not-copy fix. |
| §16.B/paper §2.6 vs the fixture | consistency **F5** + parity **P1** | Same string. Parity's reasoning is decisive on direction: the paper's stronger "verbatim excerpts" guarantee makes it a falsified guarantee there and a minor imprecision in the guide; fixing the fixture resolves both. |
| Executor "refuses any effect outside that set" is unachievable | skeptical **Claim 2** + red-team **TC-23** | Identical analysis, arrived at independently: package operations run vendor maintainer scripts as root; `command:` and `pre_action.command` are arbitrary code at launch. |
| TUF freeze/expiry contradicts "often offline" | skeptical **Claim 2** + red-team **TC-18** | Skeptical frames it as an offline-budget gap; red-team as a false claim (a high-water mark cannot detect withholding, and §7's role list has no timestamp role). Both correct; the red-team's is the sharper statement. |
| The semantic layer compromises the decision without authorizing it | skeptical **§2** + red-team **TC-01**, **TC-07** | Skeptical calls "it never authorizes" a category error; red-team supplies the injection path and shows the field-citation rule is forgeable by a generator that cites correctly and frames maliciously. |
| Post-refusal state is undefined | skeptical **G1** + **ceiling A** + red-team **TC-19**, **TC-30** | Skeptical from architecture (a personal branch never re-enters §4's conflict check); red-team from adversarial patience (re-offer until acceptance wins once) and from consent theory (no withdraw verb). |
| Multi-actor promised, single-operator signing delivered | skeptical **G2**, **ceiling B** + pre-mortem **N7**, **U2** | Skeptical: the goal is met by declaring it out of scope. Pre-mortem: there is no second person on this fleet at all. |
| Riskiest components scheduled last | skeptical **F-18a** + red-team **TC-50** + pre-mortem **A1**, **A2**, **N1** | Four routes to S5. |
| The trust layer's guarantees are conventions | red-team **TC-48**, **TC-32** + consistency **F1** + pre-mortem **U4** | §9 turned on the document, three ways. |
| The alternative architecture | skeptical **Alternative A** + pre-mortem **CUT-1 + CUT-3** | See E1. The single most important merge in this synthesis. |
| Bcfg2 numeric claims | exposition **§6** closes consistency's and parity's residual risk | Both checked against primary PDFs: the `0 / 2308` transcription and the paper's four-months/three-FTE/~200-person figures are exact. No finding. |

### 4.2 Contradictions — stated plainly, with my reading

**C-1. The pre-mortem wants §8 cut; the red-team wants §8 hardened with ~20
changes; the skeptical review calls §8 the point and says the document ignores
it.**
They are not opposed on sequencing — all three imply the consent surface should
not be *built* at Step 9. My reading: **cut the implementation, invest in the
specification.** The pre-mortem is right that §8 is the most expensive item in
the plan with zero identified users on this fleet, and right that building it
at Step 9 after a payoff-free year is how the project runs out of energy. It is
wrong to let "no user today" demote the *spec*, because the spec is the paper's
contribution and the operator has already decided the paper is a deliverable.
The correct move is the one all three converge on without saying so: write the
ChangePlan and the consent protocol properly, red-team them on paper, and do not
implement them until a second party exists. Do not claim their properties in
guarantee form in the meantime (DC-9, DC-19, DC-21).

**C-2. The consistency audit records "`blocks`/`report` are `const`, both
required, `additionalProperties: false` — the claim is true." The skeptical
review's G5 says the claim is nominal.**
G5 is right and the audit verified too narrowly. The audit checked the schema;
the guide's sentence is "an author cannot narrow the blast radius," and an
author narrows it by putting the risky promise in a bundle by itself, because
bundle membership is author-settable. The constant fixes the *expression* of
the blast radius and leaves its *extent* under author control — and §12's
security argument depends on the extent. The audit's verification stands as a
schema fact; the guide's sentence is false as written.

**C-3. The skeptical review offers Alternative B (per-actor signed feeds
gossiping over the mesh) as the design that makes "no central server," multiple
actors, and refusal all true. The pre-mortem's arithmetic says the current plan
is already 2.5–5 years for one person.**
Reject Alternative B on cost — its own author flags implementation cost as
"possibly disqualifying under §1's no-ops-staff constraint," and it trades away
compile-time global invariants, which is the best property the current design
has. Keep its diagnosis, which is not cost-dependent: the transport must be
named, the two "no central server" claims must be split, and refusal must be a
normal state rather than an unhandled divergence. And note the uncomfortable
part: Alternative B is what §8's promise actually implies, which is exactly what
ceiling A says. Rejecting it on cost is legitimate; §17 should then say so.

**C-4. The exposition review wants a compressed §9 moved to before §3. The
skeptical review calls §9 the document's most vulnerable claim; the pre-mortem
suspects it is post-hoc justification for a CFEngine choice made first.**
Adopt the diagnosis, not the remedy. Exposition 4.1 is correct that §3–§8 read
as arbitrary engineering preference without the frame, and §9's own text admits
the retrofit. But promoting an unfalsified thesis to the frame of the whole
document raises the cost of abandoning it, and abandoning it is a live outcome
of DC-41. Use exposition's own fallback: a forward-reference from §2. Revisit
promotion after the experiment.

**C-5. The two audits differ on which side of the §16.B/fixture mismatch to
fix.** Consistency says "whichever direction is wanted"; parity reasons it
through and prefers changing the fixture. Take parity's: one edit, and it
preserves the paper's "verbatim excerpts" guarantee, which is one of its
strongest credibility moves.

**C-6. Not a contradiction, worth stating: the pre-mortem's A1 predicts
inference "will be defended past its expiry" because it is the claimed novel
contribution — and then CUT-3 recommends cutting it.** The skeptical review's
Claim 1 independently argues the design already contains a better answer to the
problem inference solves. Four concessions inside the guide itself (§10's three
objections, §19.1, §19.7, §17's second ceiling) point the same way. That is six
independent pressures on one mechanism, and none of them is a refutation — which
is precisely why DC-41 (the experiment) should settle it rather than argument.

---

## 5. What I dropped, and why

**Dropped on operator instruction:**

1. **The pre-mortem's documentation-to-code ratio framing** — the 16:1 prose-to-
   code ratio, "53 of 55 commits are `docs:`", and **U1** as a whole
   ("the deliverable is the document") *as evidence of a failure mode*.
   Discounted per constraint. **Explicitly retained from the same report:** the
   observation that the `nix2cf` repo contains three files and has been
   refactored to zero; the entire §3.1 sizing table and every underestimation
   finding; all of Buckets 1 and 2; and U2–U8. **U7** (finishing the paper will
   feel like finishing the project) is retained but reclassified from defect to
   *priced risk*: the operator has already decided the paper is a legitimate
   deliverable, which converts U7 from a hidden failure mode into a known
   trade-off — the actionable half of it is DC-40's honest question of whether
   the cut version is still a paper.
2. **Skeptical F-0a** — "the guide's genre is unstable; §§3–15 are written in
   the present indicative while ~95% of the system does not exist." Dropped per
   the prose constraint. Note the underlying reader-protection concern is
   already met: the preamble carries "**Nothing described here is deployed**"
   with a specific list, and §18 is honest. No conditionalizing needed.

**Dropped as no-ops** (findings whose own author recommends no change; recorded
so they are not re-derived):

3. Exposition **3.1** — §19 does not oversell; read as a strength.
4. Exposition **3.4** — ending on Acknowledgements + Further Reading is right.
5. Exposition **5.7** — "confidently and plausibly" flagged as a positive
   example.

**Rejected on the merits, not dropped:**

6. **Alternative B** (skeptical §3) — rejected on cost per C-3; diagnosis
   retained as DC-26, DOC-14, DC-5.
7. **Exposition 4.2's remedy** (promote §9 before §3) — rejected per C-4;
   diagnosis retained as DOC-43.

**Not findings, so not ranked** (recorded for completeness): the consistency
audit's "verified claims" list and both audits' checklist/residual-risk
sections; the red-team's RT-01…RT-09 disposition table *as a table*. Three
residues buried in that table carry no `TC-` number and would otherwise have
been lost — they are surfaced above as **DC-17** (RT-03's dropped
source-to-signing provenance half), **DC-24** (RT-07's role-disagreement half),
and **DC-27** (RT-07's converger-DoS half). Two residual risks the audits flagged
are now **closed**: the paper was audited (parity pass, parity holds), and the
two load-bearing Bcfg2 numeric claims were verified against primary PDFs
(exposition §6).

---

## 6. The ordered list

One person, limited time, planning stage, no code yet. Ordered by what unblocks
or forecloses the most, not by cost — cost is noted per item.

### 1. Write the ChangePlan schema, the capability enum, and the trust-policy shape — with paired examples and negative fixtures — and exhibit one plan end to end in §16. Add all three to Step 0.
*Days. DC-16, DOC-34.*
This is the highest-priority item in the corpus. Roughly thirty of the
red-team's fifty-one findings are *about* this artifact, and not one of them can
be adjudicated while it remains a phrase in a sentence — TC-02, TC-10, TC-11,
TC-13, TC-15, TC-26, TC-28, TC-29, TC-31, TC-33 all become schema review the
moment it exists, and several may dissolve. The skeptical review names the same
item first for an independent reason: one end-to-end exhibit closes Claim 2, gap
G1, ceiling A, and F-19a together. It is the design's own §9 rule 2 applied to
its most security-load-bearing vocabulary, which is currently exactly the
"convention an agent must remember" the guide says will break silently. And it
needs no fleet, no compiler, and no code — it is the one piece of the trust
layer that is Step-0-shaped, in a project that is deliberately at Step 0.
Include the reject path and the device's state afterward; that is where DC-5
gets forced into the open.

### 2. Amend the precedence rule, then reconcile the guide with the map on the parameters it currently drops.
*An hour, then an afternoon. DOC-1, then DC-20's threshold and DC-11's digests.*
Right now the project *believes* it has a 2-of-3 offline root and NAR digests in
the manifest, and the document that governs says neither — so an implementer
building from the guide builds a 1-of-1 root and a plan that binds names rather
than bytes. This is the cheapest high-value item in the entire corpus and it
stops the drift in S4 from continuing to accumulate silently.

### 3. Extend §19 and rewrite §17 so the risk apparatus covers the subsystem the document calls the point.
*A day of writing. DOC-10, DOC-11, DOC-12, DOC-13, DOC-35, DOC-36.*
This is the strongest convergence in the material (S1) and it is pure prose. It
also does something structural for everything below it: once the trust layer's
risks are named in the document's own risk register, the long design list in
§3.1 reads as known and priced rather than as omission — which is what a
reviewer, an implementer, and a future agent all need. Rank the nine questions
while you are there; it costs one sentence.

### 4. Make the build-order decisions now, and write them into §18.
*A day of deciding, an hour of writing. DC-39, DC-40, DOC-31.*
Two independent reviewers converged on the same cut set from opposite premises
(E1), and a third of the corpus is sequencing findings (S5). Deciding at
planning stage is free; deciding after Step 2 costs the year the pre-mortem
narrates. The three moves that matter most: put the `buildfile` render first
(§4 already calls it "almost free" and "the first piece of the compiler," and it
is currently buried inside Step 3 behind Android); put Linux before Android; and
drop or re-point the two-platform gate on inference (E3). Then annotate §18 with
honest sizing so it stops reading as eleven comparable increments.

### 5. The thirteen cheap factual corrections.
*One afternoon. DOC-2 through DOC-8, DOC-20, DOC-21, DOC-23, DOC-24, DOC-26.*
Two of them (§3's pairing claim, the token-kind ellipsis) are places where the
document already fails its own standard, which is why they belong above prose
polish rather than in it. The rest are cross-reference and fixture drift that
will only get more expensive as the schema count grows.

### 6. Name the transport and split the two "no central server" claims.
*Half a day if the answer is "a git remote." DC-26, DOC-14, DOC-15.*
It is a §1 goal that the described mechanism does not deliver, and nothing else
in the document supplies it — the §2 diagram draws a bare arrow exactly where
the answer belongs. Cheap if the intended answer is a git remote plus mesh
sync; expensive if it is meant to be peer-to-peer, which is precisely why it
should be answered before more design is stacked on it. The claim needs
rescoping either way.

### 7. Resolve the §9 head-to-head, then decide inference's fate.
*A week, no fleet or compiler required. DOC-27, DC-41, DOC-30, DC-28.*
Six independent pressures now sit on one mechanism (C-6) and none of them is a
refutation. The experiment needs only the existing schemas, a prompt, and a
rubric, and it converts the project's thesis from an argument into a result. Run
the head-to-head first (what must an author know to write `depends_on: caddy`
versus `requires: service:caddy`, given §15's lookup?), because if the answer is
"the same lookup," inference needs a different justification and DC-40's cut
becomes obvious rather than contested. Answer §10's own objection #1 in the
document either way.

### 8. The trust-layer design decisions, in red-team severity order, informed by whatever item 1 revealed.
*Weeks to months; several are cuttable. DC-1 through DC-8, DC-9 through DC-22.*
Start with the class fix (DC-1, the device-local trust root) because the
red-team's central finding is that it collapses most of the instance-level
findings at once. Then DC-2 and DC-3, which are the two Criticals that make the
signature and the briefing mean what §8 says they mean. Expect to reject some of
this list on cost — say so in §17 and §19 when you do, which is what item 3 makes
possible.

### 9. Exposition and prose.
*A day. DOC-41 through DOC-46.*
Last deliberately: items 1, 3, 4, and 7 all change what the document says, and
editing the sentences before the structure settles is re-work. The one item
worth pulling forward is the "how to read this" note (DOC-41), because it is
also partial mitigation for the pre-mortem's U4.

---

**Summary line.** 44 design changes, 47 document changes, drawn from six
reports. The document changes should mostly just be done — items 2, 3, 5, and 6
above are roughly three days of work and address four of the five root causes.
The design changes divide into a class fix (DC-1) that collapses most of the
trust-layer instances, a sequencing decision (DC-39, DC-40) that two independent
reviewers converged on, and a long tail that should be triaged in §17 and §19
rather than silently carried.
