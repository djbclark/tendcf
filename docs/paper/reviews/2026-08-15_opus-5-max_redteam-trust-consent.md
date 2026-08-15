# Red-team: trust and consent layer (guide §§7, 8, 9, 14, 15)

- **Target:** `docs/paper/tendcf-architecture-guide.md`, sections 7, 8, 9, 14, 15.
- **Reviewer posture:** Adversarial and independent. Assume compromise, not
  operator error. I did not read the authors' intent from surrounding
  documents except where the guide points at them normatively.
- **Prior art accounted for:**
  `docs/architecture/deprecated/redteam-trust-layer-openai-v1.md` (RT-01…RT-09).
  Disposition of all nine is §6 of this document and is required reading
  alongside the findings.
- **Also consulted, as context only:** `architecture-DEFINITIVE-v3.md` (the
  guide names it as the implementer map that "must agree with this guide"),
  `schema/common.schema.json`, `examples/broken/`, `docs/architecture/deprecated/trust-layer-hardened-design-grok-v1.md`.
- **Date:** 2026-08-15. Reviewer: Opus 5 (max effort), single pass, no
  sub-agents.

**Standing caveat, stated once.** Nothing here is deployed (guide §18). Every
finding below is therefore a finding against *design text*. Where the guide is
silent on a point an attacker can exploit, I treat the silence as a finding and
say so explicitly, because the guide is the document that "wins on conflict"
and because §9 is itself an argument that unstated constraints do not survive
contact with the agents who will implement them. I have not filtered by
importance or confidence; ranking is the synthesis pass's job.

**Severity scale.** *Critical* — defeats the security property the section
claims, with no other described control in the way. *High* — defeats it given
one additional plausible precondition, or removes a control the rest of the
design leans on. *Medium* — meaningful weakening, information leak, or
unspecified behavior an implementer will plausibly get wrong. *Low* — clarity
or robustness.

**Confidence** is confidence that the attack works *against the design as
written*, not that an eventual implementation would be vulnerable.

---

## 1. The central finding

Section 8 asks: what does it mean that the person picks their own AI advisor
and we never see the model, the prompt, or the conversation? The honest answer
after reading §§7, 8, and 14 together is that it means less than the section
claims, because **every constraint in the trust layer is authored, delivered,
and evaluated by the party it exists to constrain.**

Enumerated from the guide's own text:

| The control | Where it lives | Who controls that |
| --- | --- | --- |
| Local trust policy (who may change me, do I need a local yes, who may act on me) | "in its signed release (authored in site-private)" — §14 | Operator |
| The advisor key itself | "they enroll an advisor key … in site-private" — §8 | Operator's repository |
| Extra advisor prompt | site-private, "extra advisor prompt" — §2 layer diagram | Operator |
| Default advisor prompt | tendcf, public file — §2, §8 | Upstream, publicly known |
| Resource legality (`resources` vs port/path registries) | compile time, in the compiler — §7 | Operator |
| The nonce the accept is bound to | issued with the plan — §7, §8 | Operator |
| The semantic briefing the advisor reads | "generated, cached" upstream of the device — §7 | Operator |
| The executor that enforces all of the above | shipped by the release — §7, §18 | Operator |

Section 14 says "A label in inventory does not enforce this. The executor
does." That line is doing more work than it can carry: the executor is code the
operator ships, running against a policy the operator authored, checking a
signature from a key enrolled in the operator's repository, over a nonce the
operator chose, about a briefing the operator generated. The one artifact the
consenting person genuinely contributes is a signature over the operator's
nonce.

That is not nothing — it defeats a *network* attacker and it creates an
auditable record. But §8's framing ("their AI, not ours"; §1: "should be able
to read a proposed change in ordinary language and refuse it") promises
sovereignty against the proposer, and the mechanism as described does not
deliver it. Most of the findings below are instances of this one.

The smallest design change that would fix the class, rather than the
instances: **name a device-local trust root that the release path cannot
write.** Concretely — the advisor key, the consent policy, the peer allowlist,
and the device's own resource policy are established at the first-run ceremony
into storage the executor can read but the release cannot modify; changing any
of them is a distinct capability that requires a signature from the *current*
advisor key plus a locally-authenticated human act, never a release alone. Once
that exists, most of §§7/8/14 becomes true as written. Without it, the trust
layer is a well-designed audit trail with the word "consent" on it.

---

## 2. Findings — §8 and the semantic layer of §7

### TC-01 — The semantic layer is a prompt-injection channel into the only entity that produces `accept`

- **Severity:** Critical · **Confidence:** High
- **Attack.** §7's semantic layer is "generated, cached, written for a language
  model to read," and it "briefs a person and their advisor." §7 also allows
  free prose where template-filling from typed fields is impossible. That prose
  is derived from Site Model content — service descriptions, interlock
  `description` blocks (see the multi-line free-text `description` in §16B),
  paths, package names, CVE text, commit text. An author plants instruction-shaped
  text in one of those fields. The generator renders it into the briefing. The
  advisor reads the briefing as its task input and returns `accept`. The
  executor then honors a validly signed grant.
- **Preconditions.** Write access to any free-text field that reaches the
  briefing. §9 states plainly that "most of this system's configuration will be
  written by AI agents" — so the population with that access is large, is not
  human, and is itself the documented weak link. No key compromise is required.
- **What it gets the attacker.** The `accept` signature on a `consented`
  device, i.e. the entire consent gate, from a position no more privileged than
  "can propose a config change."
- **Why the guide's defense does not hold.** §7 says the semantic layer "never
  authorizes." That is a statement about the *architecture graph*, not about
  *information flow*. The layer does not hold authority; it is the sole input to
  the entity whose signature is the authority. One hop of laundering makes the
  distinction cosmetic. The guide never analyzes this hop.
- **Smallest fix.** The advisor is briefed with the **typed plan only** — a
  canonical, schema-validated structure, not prose — and any free-text field is
  transported inside an explicitly-typed `untrusted_text` container that the
  default prompt names as proposer-supplied data with no instruction authority.
  Free prose that is *rendered for humans* is fine; free prose that is *fed to
  the deciding model* is the vulnerability. If prose to the advisor is kept, it
  must be a pure function of the typed plan (see TC-11) and free fields must be
  reduced to a fixed, non-instructional summary (kind + count + digest), never
  passed through.

### TC-02 — The `accept` signature binds to a proposer-chosen nonce, not to the plan and not to the briefing

- **Severity:** Critical · **Confidence:** High
- **Attack.** §8: "`accept | reject`, signed by the enrolled key, bound to that
  plan's nonce." §7: the nonce is a field the plan carries. So the signed
  statement is, in effect, "the holder of the advisor key said yes to nonce
  N" — where N was chosen by the proposer, and nothing in the signature covers
  the operations, the target, the resources, or the prose the advisor actually
  read. A proposer who issues two plans carrying the same nonce (nothing in the
  guide forbids it; there is no stated uniqueness scope) can have the advisor
  brief on one and the executor apply the other. Even without deliberate reuse,
  the *briefing* is uncovered: two renderings of one plan — an honest one for
  the advisor's fetch, a different one from a poisoned or stale cache — produce
  an equally valid accept.
- **Preconditions.** Control of plan generation or of the semantic-layer cache.
  For the cross-device variant, one advisor key enrolled on more than one
  device (the normal case for one person with a phone and a laptop) plus an
  accept that does not cover the `target`.
- **What it gets the attacker.** A person's genuine "yes" transferred onto an
  operation they never saw, or onto a device they were not asked about. This is
  the direct answer to "does the accept signature actually bind to what the
  person was shown": as specified, **no**.
- **Smallest fix.** The accept signs over
  `H(canonical_plan_bytes) || H(briefing_bytes) || device_nonce`, where
  `device_nonce` is generated by the executor at presentation time and
  `briefing_bytes` are the exact bytes the advisor was given. The executor
  refuses to apply unless it can recompute all three and they match the plan in
  front of it. The proposer's nonce becomes a replay guard for the transport,
  which is all a proposer-chosen value can honestly be.

### TC-03 — site-private supplies an "extra advisor prompt": operator-authored instruction text reaching the consented person's advisor

- **Severity:** Critical · **Confidence:** High
- **Attack.** §2's layer diagram assigns to site-private — "this site's facts:
  inventory, allocations, secret names, trust policy, **extra advisor prompt**."
  §8 says tendcf ships a default prompt "as a replaceable public file. They may
  append or replace it," where "they" is not disambiguated. Under §2's reading,
  the operator contributes prompt text to the model that is supposed to check
  the operator. No injection craft is needed; the channel is a named feature.
- **Preconditions.** None beyond being the site operator. This is the design
  operating as documented.
- **What it gets the attacker.** Direct instruction authority over the
  deciding model — strictly stronger than TC-01, which has to smuggle the same
  thing through a data field.
- **Smallest fix.** State in §8 that prompt content reaching a `consented`
  device's advisor comes from exactly two sources: the public tendcf default
  (pinned by digest, inspectable by the person) and the person's own additions,
  held device-side. Any site-private text about a change is delivered as
  *plan data* inside the untrusted container of TC-01, never as prompt. If
  §2's "extra advisor prompt" is meant for `operator`-tier hosts only, §2 and
  §8 must say so; as written the guide reads the other way.

### TC-04 — "(or a local app/socket)" silently voids the signature story

- **Severity:** High · **Confidence:** High
- **Attack.** §8: "they enroll an **advisor key** (or a local app/socket)."
  A socket has no cryptographic binding. Anything on the device that can
  connect to it can answer `accept`. On a `consented` device the operator's own
  agent code is on the device by construction, so the socket variant collapses
  the consent boundary into "the executor asks itself."
- **Preconditions.** The person chooses socket mode — plausible, since it is
  the frictionless option and is offered coequally with the key.
- **What it gets the attacker.** Everything the consent gate protects, from any
  local code execution, including code the operator shipped.
- **Smallest fix.** Socket mode still returns a signature from a key the
  executor cannot reach — OS keystore / Secure Enclave / Android Keystore with
  user-presence required — or the guide states that socket mode is convenience
  only and is not valid for the `consented` tier.

### TC-05 — The default prompt is a public file: one known, offline-attackable system prompt across every default deployment

- **Severity:** Medium · **Confidence:** High
- **Attack.** §2 and §8 make the default advisor prompt a public artifact of
  tendcf. An attacker can iterate against the exact instructions, with the
  exact briefing format, offline and unrate-limited, until a briefing reliably
  produces `accept` — then ship it once. Every deployment that did not replace
  the prompt shares the failure.
- **Preconditions.** The person kept the default (the common case for a
  default).
- **What it gets the attacker.** A reusable bypass with fleet-wide, indeed
  ecosystem-wide, reach; a monoculture failure.
- **Smallest fix.** Nothing about publishing the prompt is wrong — the fix is
  to stop the prompt from being the security boundary. State in §8 that the
  prompt is a usability artifact, that the enforceable properties are the typed
  plan and the executor allowlist, and pair the default prompt with an adversarial
  fixture suite (briefings that must produce `reject`) shipped in `examples/broken/`
  style, so a prompt regression is a test failure rather than a field incident.

### TC-06 — The advisor is briefed with prose; the analogy the section invokes briefs with types

- **Severity:** High · **Confidence:** High
- **Attack.** §8 claims the "same shape as a Kubernetes admission webhook."
  The analogy hides three inversions. (a) A K8s webhook receives a *typed*
  `AdmissionReview` object, not a generated natural-language summary; the guide
  describes only the semantic layer as briefing the advisor and never states
  that the typed ChangePlan is also delivered. (b) In K8s the webhook is run by
  the same authority as the API server; here it is run by the party the API
  server is acting *against*, which is the whole point and which makes the
  shipped-by-operator issues of §1 apply. (c) `failurePolicy: Fail` is a known
  cluster-wide denial-of-service vector in exactly the way §8's fail-closed
  rule is (TC-15).
- **Preconditions.** None; this is a reading of the design.
- **What it gets the attacker.** Wherever prose is the interface, TC-01 is
  available. Wherever the analogy is trusted, the reader stops looking.
- **Smallest fix.** Deliver the canonical typed plan to the advisor as the
  primary artifact and the semantic layer as an optional, clearly-labeled
  secondary; and drop or qualify the webhook analogy with the three inversions
  named, since as written it imports assurance the design does not have.

### TC-07 — The field-citation rule is the only stated defense for free prose, and it is forgeable by the proposer

- **Severity:** High · **Confidence:** High
- **Attack.** §7: "Where it has to be written freely, it must point at the
  exact fields it is summarizing." That is provenance, not fidelity. A briefing
  that cites `operations[3].resources[0]` accurately and then *characterizes* it
  falsely satisfies the rule completely. Worse, the rule teaches the advisor
  (via the public default prompt) that citations are the trust signal, so a
  proposer who emits well-formed citations is rewarded for it. The design's own
  quality heuristic becomes the attacker's checklist.
- **Preconditions.** Ability to influence the generated prose (TC-01's
  preconditions), or a compromised generator.
- **What it gets the attacker.** A briefing that passes the only stated
  content check while describing something other than the plan.
- **Smallest fix.** Make fidelity machine-checkable, not conventional — the
  guide already has the mechanism. §4 establishes that render is a pure
  function of the Site Model, "same input, same output," and makes that the
  basis of regression testing. Apply it: the briefing is a pure deterministic
  function of the canonical plan; the executor regenerates it and refuses to
  proceed if the bytes the advisor signed over differ. A briefing that cannot
  be regenerated is not shown.

### TC-08 — No bar on the advisor is expressible, and `consented` is read by the operator as assurance a human reviewed the change

- **Severity:** High · **Confidence:** High
- **Attack.** By construction tendcf cannot see the model, the prompt, or the
  conversation; therefore it cannot express or verify *any* minimum bar — not a
  model identity, not a version, not attestation, not "a human was present."
  A person may enroll a three-line script that signs `accept` unconditionally,
  and nothing distinguishes that from a careful review. §8 lists modes as
  "auto-review, or a conversation with them first," with auto-review first.
- **Preconditions.** A person who wants the prompts to stop, a cheap model
  chosen for cost, a compromised advisor host, or simply a default.
- **What it gets the attacker.** Consent becomes unfalsifiable. Two distinct
  harms: the person is not actually protected, and the *operator* is misled,
  because "this device is `consented`" is being used as evidence that a review
  happened. The design serves two masters here and never says so.
- **Smallest fix.** Separate "who decided" from "what we can prove." Apply-attestations
  (§8 already owes them) carry a person-controlled, self-declared advisor
  descriptor: mode (`auto` / `human-in-loop`), a stable advisor identity string,
  and its version. The person can lie; the point is that the record then shows a
  claim they made, and the site can require `human-in-loop` for a marked subset
  of capabilities (the person may still refuse — they just cannot silently
  auto-accept a privileged change while the record says otherwise).

### TC-09 — Consent fatigue and privilege splitting: the executor checks each operation, never the aggregate

- **Severity:** High · **Confidence:** High
- **Attack.** Two variants of one gap. (a) *Fatigue*: ship a high volume of
  trivially-fine plans, then the one that matters. Nothing in §§7/8 rate-limits
  offers, batches them, or gives the advisor any signal about offer frequency.
  (b) *Splitting*: decompose a privileged outcome into N individually-legal
  operations spread across N releases. Each passes its capability check; each
  briefing is honest; the resulting privilege state is never evaluated, because
  nothing in the design holds the aggregate.
- **Preconditions.** Ability to propose changes over time. No compromise.
- **What it gets the attacker.** Arbitrary privilege accumulation under a
  fully-consented, fully-attested audit trail.
- **Smallest fix.** Two cheap ones, both reusing existing machinery. Give the
  advisor the device's own recent history as briefing context — §6 already
  keeps a per-device JSONL record and a SQLite index precisely for "what
  happened here." And mark *transitions* rather than operations: a plan whose
  application makes a new privileged capability reachable from the device's
  current state is a distinct, always-human class, computed by the executor from
  local state, not by the proposer.

### TC-10 — All-or-nothing accept over a multi-operation plan is an omnibus-bundling primitive

- **Severity:** High · **Confidence:** High
- **Attack.** §7 defines a ChangePlan as "a list of operations." §8 defines the
  return path as `accept | reject` — one verdict for the whole list. Bundle the
  urgent TLS/CVE patch (the guide's own example prose) with the operation the
  person would refuse. Refusing costs them the patch; §8's fail-closed rule
  means there is no partial path.
- **Preconditions.** Control of plan composition, i.e. the ordinary proposer
  role.
- **What it gets the attacker.** Coerced consent, with the coercion invisible in
  the record — the person accepted, freely, as far as any log can tell.
- **Smallest fix.** The accept is a vector over operation IDs, and the executor
  applies exactly the accepted subset (the plan is already typed and
  per-operation, so this is nearly free); or, if per-operation apply breaks
  atomicity for some capability classes, a schema rule that a plan may carry
  operations of only one capability class, so bundling across classes is a
  compile error rather than a negotiation tactic.

### TC-11 — Advisor key scope is undefined: one key, several devices, one compromise

- **Severity:** High · **Confidence:** Medium
- **Attack.** §8 speaks of "an advisor key" enrolled at install. Nothing scopes
  it per device. The natural deployment for one person with a laptop, a phone,
  and a tablet is one advisor and one key. Combined with TC-02 (the accept does
  not cover the target), an accept for the tablet is an accept for the laptop.
  Independently, compromise of that one key is a total consent bypass across
  every device that person holds.
- **Preconditions.** One key reused, which the guide neither forbids nor
  discourages.
- **What it gets the attacker.** Consent bypass with a blast radius of "one
  person's entire device set" from a single key theft.
- **Smallest fix.** Per-device advisor subkeys derived at each device's
  first-run ceremony, with the accept covering the device public key (which
  TC-02's fix already does); and a stated rule that an accept is valid for
  exactly one `target`.

### TC-12 — Losing the advisor key returns the device to operator control

- **Severity:** High · **Confidence:** Medium
- **Attack.** The person's advisor key is lost, or the advisor app is
  reinstalled, or the phone is replaced. Installs now fail closed forever (§8).
  The only described re-enrollment path is §8's "they enroll an advisor key …
  in site-private" — an edit to the operator's repository. So key loss is
  resolved by asking the operator to install a new consent authority, which the
  operator authors. A hostile or merely impatient operator resolves it by
  enrolling a key they hold.
- **Preconditions.** Ordinary key loss. This is a *reliability* event that
  degrades directly into a security event.
- **What it gets the attacker.** A legitimate-looking path to becoming the
  consent authority for a device that is not theirs.
- **Smallest fix.** Re-enrollment is a local ceremony on the device requiring
  physical presence, mirroring the first-run root ceremony, and produces a
  record the person's own tools can see. Site-private may *record* the enrolled
  key; it must not be able to *establish* one.

### TC-13 — The person's advisor is a third party that receives the site's private inventory

- **Severity:** Medium · **Confidence:** High
- **Attack.** §3 is explicit that inventory is private by default and that USB
  serials, RFC1918 addresses, and the host list stay private. §7's ChangePlan
  carries exact resources — ports, paths — and the semantic layer renders them
  into prose. §8 sends that prose to an advisor of the *device holder's*
  unilateral choosing, which may be a commercial API. Privacy in the guide is
  analyzed in one direction only ("we never see their model, prompt, or
  conversation"); the reverse flow is not discussed anywhere in §§7/8/14.
- **Preconditions.** A remote advisor. No compromise.
- **What it gets the attacker.** A model provider — or anyone who compromises
  one — receives a continuous, structured feed of a private fleet's service
  names, ports, paths, secret *names*, and patch cadence, and can distinguish
  a security patch from routine change by reading it.
- **Smallest fix.** The briefing is subject to the same export policy §3
  already defines for site-shared: fields not marked exportable are redacted or
  tokenized in anything crossing to a remote advisor. Enrollment declares
  whether the advisor is local (socket/on-device) or remote (network key); the
  site policy may require local advisors for hosts carrying sensitive
  resources, and the person can see which of their devices is briefing whom.

### TC-14 — "Upstream-heal is a suggestion their agent evaluates" relocates RT-09 into the weakest component

- **Severity:** High · **Confidence:** High
- **Attack.** §8's personal-branch paragraph leaves the decision "is the
  upstream release equivalent to / better than my local fix?" to the advisor.
  That decision requires comparing two bodies of privileged code. The advisor
  is an LLM briefed with prose (TC-06), injectable (TC-01), possibly a
  yes-man (TC-08), and holding the accept signature (TC-02). An attacker who
  induces a failure, supplies a "fix," and later supplies a "healed upstream"
  wins at the third step by argument rather than by key.
- **Preconditions.** Ability to influence a failure or a purported upstream —
  RT-09's original preconditions, unchanged.
- **What it gets the attacker.** Persistence of an attacker patch, or
  substitution of a different payload, laundered through a legitimate consent
  event.
- **Smallest fix.** Equivalence is never argued, only computed: replacing a
  local fix requires either byte/derivation equivalence of the patched artifact
  or an explicit, separately-signed human approval of the semantic delta, with
  the local fix carrying a mandatory expiry from the moment it is applied. The
  advisor may present the evidence; it may not be the thing that decides
  equivalence.

---

## 3. Findings — fail-closed, emergency, and time (§7 × §8)

### TC-15 — Fail-closed installs plus a consent-free emergency channel is an attacker-drivable one-way ratchet

- **Severity:** High · **Confidence:** High
- **Attack.** §8: "Advisor down → fail closed for *installs* (revocation still
  applies, §7)." §7: revocation, "do not apply releases signed by K," freeze
  detection, and high-water rejection "do not need a local yes." Compose them.
  An attacker who can keep the advisor unreachable — DoS its endpoint, block
  the network, or simply be the person's ISP — freezes all installs
  indefinitely, while the one channel that still functions is the one that
  requires no consent and can only restrict. The device can be pushed
  monotonically toward "nothing may run" and has no path back, because the path
  back is an install.
- **Preconditions.** Network position against the advisor, or an advisor
  outage. For the second half, the emergency key (TC-16).
- **What it gets the attacker.** Indefinite denial of security patches to a
  consented device, and, with the emergency key, an irreversible lockdown. Note
  the perverse default: §7's pre-grant for emergency patches is "default off,"
  so the *safe* default guarantees an unpatched device whenever the advisor is
  down.
- **Smallest fix.** Define a bounded degraded mode. After a stated period of
  advisor unreachability, the executor escalates to a local human path — render
  the typed plan on-device and accept a locally-authenticated physical
  confirmation — rather than failing closed forever. "Advisor unreachable" is a
  reportable state in the §6 record and in the device's user-visible status, not
  a silent no-op; a device that has been unable to patch for N days is a
  visible condition.

### TC-16 — The emergency role is a single, consent-free, unexpiring, fleet-wide restrict channel with no reinstatement path

- **Severity:** Critical · **Confidence:** Medium-High
- **Attack.** §7 lists four TUF roles — "an offline root, release signatures, a
  snapshot … and an emergency role" — and states a threshold only for root
  *rotation* ("threshold of old **and** new keys"). The emergency role is
  described with no threshold, no expiry, and no reversal semantics, and it is
  the single role that explicitly bypasses the consent gate on `consented`
  devices. A holder of that key issues "do not apply releases signed by K" for
  every K, to every device. Every device is now permanently unable to install
  anything; §7 says the recovery for threshold compromise is "again out of
  band," which for other people's phones means physical visits.
- **Preconditions.** Theft or misuse of one key that must be usable quickly by
  definition (it is the emergency key) and is therefore the least likely to be
  kept fully offline in practice.
- **What it gets the attacker.** Fleet-wide brick, delivered through the
  channel specifically designed to need no local yes, against devices whose
  owners were promised a veto.
- **Smallest fix.** Three properties, all cheap to state: (a) emergency actions
  are thresholded like root, not single-key; (b) every emergency action carries
  a mandatory expiry, so a revocation that is never renewed lapses rather than
  bricking; (c) an emergency action may never leave a device with zero valid
  release signers — if it would, it requires a local yes, because at that point
  it is not tightening, it is terminating. Add: emergency actions are recorded
  locally in a form the person's own advisor tools can read, so "someone
  restricted my device without asking" is observable.

### TC-17 — "Tighten" is asserted of the mechanism, not of the impact

- **Severity:** High · **Confidence:** High
- **Attack.** §7's carve-out rests on the claim that revocation, freeze
  detection, and high-water rejection "tighten what may run" and therefore need
  no consent. The claim is true of the *mechanism* and false of the *effect*.
  Revoking the only key that can ship your security patch loosens your posture.
  Freezing a phone's management path is a safety event for its owner. For a
  device that is someone's daily driver, availability is a security property,
  and the guide's own §12 says so about VPN lockdown — the interlock exists
  precisely because a "tightening" change severs management paths.
- **Preconditions.** None; this is a flaw in the reasoning that authorizes the
  carve-out, which every attack in this subsection uses.
- **What it gets the attacker.** A consent-free channel to every consented
  device, justified by an argument the design elsewhere refutes.
- **Smallest fix.** Replace the tighten/loosen test with a bounded enumeration:
  name the exact metadata actions that may proceed without a local yes, require
  each to be reversible and expiring, and forbid any of them from altering
  *which* keys or policies govern consent (that is TC-25's rule seen from the
  metadata side).

### TC-18 — Freeze is claimed but not mechanized; expiry is unenforceable on the devices the design is built for

- **Severity:** High · **Confidence:** High
- **Attack.** §7 asserts that the per-client high-water mark makes "replay,
  freeze, and downgrade" all rejected. A high-water mark detects rollback. It
  cannot detect freeze — withholding new metadata leaves the mark untouched and
  the client content. Freeze detection in TUF is the timestamp role's job, and
  §7's role list contains no timestamp role. The alternative, per-plan
  `expiry`, requires trusted time on devices the design describes as "often
  offline," including Android handsets that get frozen and OOM-killed by OEM
  power management (§6's own concern) and hosts whose clocks reset. An attacker
  who can withhold metadata, or move a clock, holds a device at a vulnerable
  release indefinitely without forging anything.
- **Preconditions.** Network position or mirror control; or a device whose
  clock the attacker or the OEM controls.
- **What it gets the attacker.** Indefinite retention of a known-vulnerable
  state, with every signature valid and every check passing. Also, the converse:
  a fast-forward — serving a validly-signed far-future version once pushes the
  high-water mark above every legitimate future release, permanently denying
  updates, and §7 defines no reset path.
- **Smallest fix.** Either adopt the timestamp role (a short-expiry, frequently
  re-signed freshness object) and say so, or drop the freeze claim from §7 and
  state the residual risk honestly. Add monotonic-clock handling and a
  "metadata older than X" user-visible warning that does not depend on wall
  time. Define the fast-forward reset: a root version bump re-baselines the
  high-water mark, which is TUF's own answer.

### TC-19 — A `reject` is not stated to be durable

- **Severity:** High · **Confidence:** Medium
- **Attack.** §8 gives `accept | reject` and "timeout is deny." Neither the
  guide nor §14 says a rejection is *remembered*. Re-offer the same plan on the
  next release, and the next. Every offer is a fresh coin flip against a tired
  human or a stochastic model; refusal has to win every time, acceptance has to
  win once. RT-04 asked for refusal persistence explicitly; the current text
  does not carry it.
- **Preconditions.** Ability to re-propose. No compromise.
- **What it gets the attacker.** Any refused change, given patience.
- **Smallest fix.** Persist rejects keyed by canonical plan content hash. A
  re-offer of previously-rejected content is a distinct, visibly-labeled event
  ("you rejected this on DATE; it is being proposed again"), is rate-limited,
  and is recorded in the §6 log whether or not it is accepted. Re-offer counts
  are exactly the sort of thing the advisor should see (TC-09).

### TC-20 — "One-time nonce" with no stated store or eviction policy

- **Severity:** Low · **Confidence:** Medium
- **Attack.** Enforcing single use requires remembering every nonce ever seen,
  forever, on a device with bounded storage — or bounding the window, which
  creates a replay opportunity after eviction. The guide specifies neither.
- **Preconditions.** An implementer choosing a bounded cache, plus an attacker
  who can wait past eviction and re-present an old accepted plan.
- **What it gets the attacker.** Replay of an old grant, in the window the
  implementation forgot about.
- **Smallest fix.** Bind single-use to the monotonic release counter rather
  than to a set membership test: an accept is valid only for a plan whose
  release is exactly the device's current high-water + 1 (or its declared
  baseline, per TC-29), which makes the nonce store O(1).

### TC-21 — "Advisor down" is undefined, so the proposer can choose which branch it takes

- **Severity:** Medium · **Confidence:** Medium
- **Attack.** §8's rule has two branches with opposite outcomes and no
  definition of the predicate. Unreachable? Slow? TLS failure? Malformed
  response? Signature over the wrong nonce? Returns something that is neither
  accept nor reject? A proposer who can distinguish these — by timing, by
  payload size, by triggering a parse failure with an oversized briefing — picks
  the branch. If any of them is implemented as "treat as no decision, retry
  later" rather than "deny," the proposer has a retry loop (TC-19) they control.
- **Preconditions.** Influence over the briefing or the transport.
- **What it gets the attacker.** Control of the failure mode of the security
  gate.
- **Smallest fix.** One rule with no branches: anything that is not a
  well-formed, signature-valid `accept` covering the exact plan is a deny, and
  denies are recorded with their reason. "Advisor down" is not a special case;
  it is one of the ways an accept fails to arrive.

### TC-22 — Timeout duration is unspecified, and a short one converts conversation mode into auto-review

- **Severity:** Medium · **Confidence:** Medium
- **Attack.** §8 offers "a conversation with them first" as a mode and "timeout
  is deny" as a rule, with no duration. A timeout shorter than a human's
  realistic response window (asleep, at work, phone in a drawer) means
  conversation mode produces denials, denials block patches (TC-15), and the
  person switches to auto-review to make it stop — landing on the mode most
  exposed to TC-01.
- **Preconditions.** A default chosen for machine convenience.
- **What it gets the attacker.** Migration of the population toward the weakest
  mode, achieved by the design's own ergonomics.
- **Smallest fix.** Timeout is a per-device, person-settable value with a
  human-scale default (days, not minutes), and a timeout-deny is distinguished
  in the record from an explicit reject, so "we never reached them" does not
  read as "they refused."

---

## 4. Findings — what a signed plan actually constrains (§7)

### TC-23 — The executor can refuse declarations; it cannot refuse effects, and the guide names no confinement

- **Severity:** Critical · **Confidence:** High
- **Attack.** §7: "The on-device executor maps declared capabilities to an
  allowlist and **refuses any effect outside that set.**" Nothing in the design
  can do that. An executor validating a plan before acting constrains what it
  *launches*, not what launched code *does*. The design's own artifacts are
  Turing-complete at the point of launch: service records carry
  `command: [...]` with an arbitrary binary path and arguments (§16A), interlocks
  carry `pre_action.command` executed — per §16B's own rendering — via
  `returnszero(..., useshell)`, and package operations on every supported
  platform run maintainer scripts. A capability of `service.install` bound to a
  path and a launchd label is arbitrary code as `runs_as`, forever, at load.
- **Preconditions.** Any accepted plan carrying a capability that runs
  something. That is most of them.
- **What it gets the attacker.** Arbitrary code execution inside a fully
  capability-checked, fully consented, fully attested change. RT-03 in its
  original form.
- **Smallest fix.** Two parts, and the design needs both. (i) Correct the claim
  in §7 to "refuses any *operation* outside that set," so implementers are not
  told they have a property they do not. (ii) Name a per-platform confinement
  for operations that execute: sandbox-exec/Endpoint Security on macOS,
  seccomp+Landlock or systemd sandboxing directives on Linux, the app sandbox
  on Android — and make the confinement profile a rendered output of the
  capability, not an author-settable field (the same treatment §12 already gives
  interlock blast radius, which is the right precedent and is cited as such).

### TC-24 — The CFEngine policy channel sits outside the ChangePlan, and the escape hatch §19 Q8 fears is already a decision

- **Severity:** Critical · **Confidence:** High
- **Attack.** §7 says configuration reaches devices "only as a versioned,
  signed release" and that the plan is the constraint. §5 says each device
  "reads policy that arrived as part of the ordinary signed-release path,
  synced via git." Policy is CFEngine source. Even in the pure-data case the
  *generic bundle* — the interpreter for every operation — is code that ships
  with the release and is not itself a list of typed operations. §16B shows
  hand-written `.cf` with a shell-executed probe. The implementer map's decision
  register carries D30, "`.cf` escape hatch — prefer a grammar before lint-only,
  when that surface is exercised," i.e. freehand `.cf` is anticipated. So the
  answer to §19 question 8 ("the moment one exists, the mechanism is
  decorative") is that one exists now, in the register, and the guide does not
  mention it.
- **Preconditions.** Ability to change policy source in the release — the same
  ability that produces the release.
- **What it gets the attacker.** Everything, without ever appearing in a
  ChangePlan or a briefing.
- **Smallest fix.** Policy source is a plan resource with a content digest:
  the executor verifies that the CFEngine tree it is about to run hashes to
  exactly the value bound in the signed plan, and a change to policy source is
  its own high-privilege capability that is always shown to the advisor and
  always human-class on `consented` devices. §19 question 8 should be amended to
  name D30 as the existing hatch rather than a future pressure.

### TC-25 — Nothing forbids a plan from rewriting the trust policy, the advisor key, or the executor

- **Severity:** Critical · **Confidence:** High
- **Attack.** §14: "Each device carries a **local trust policy** in its signed
  release (authored in site-private)." §8: the advisor key is enrolled in
  site-private. §7: installing new targets requires consent. Put them together:
  one accepted release changes the consent policy, the enrolled advisor key,
  the peer allowlist, and the executor binary, because all of those are release
  content and none is called out as a distinct capability. The person consents
  once — plausibly to a briefing that describes the *other* nineteen operations
  in the plan (TC-10) — and the gate is gone. Every subsequent change
  self-approves.
- **Preconditions.** One accepted plan. Not even a compromise: this is the
  documented delivery mechanism for trust policy.
- **What it gets the attacker.** Permanent removal of the consent gate,
  through the consent gate.
- **Smallest fix.** A privileged-resource class that the plan may name but not
  unilaterally change: the trust policy, the enrolled advisor key(s), the peer
  allowlist, the root metadata, the executor binary, and the device's resource
  policy. Changes to any of them are a `trust.amend` capability that requires a
  signature from the *current* advisor key over a briefing that says, in the
  template layer and not in free prose, exactly which axis is changing and in
  which direction — plus a local physical confirmation when the change reduces
  the consent requirement. Self-amendment must cost more than ordinary change.

### TC-26 — The plan binds names, not bytes: no artifact digest anywhere in §7's field list

- **Severity:** High · **Confidence:** High
- **Attack.** §7 enumerates the fields of an operation: capability, resources,
  target, rollback, expiry, nonce. There is no content digest of what will be
  installed. Resources are "checked against the port and path registries" —
  registries of *names*. So a plan that says "install the binary at
  `/opt/homebrew/bin/caddy`" constrains the path and says nothing about the
  bytes. A compromised build, a substituted artifact, a different APK with the
  same declared identity: all satisfy the plan. RT-04 asked for a
  "user-verifiable payload digest" and RT-02 for "exact artifact length/digest";
  neither survived into the guide's field list.
- **Preconditions.** Control of any artifact-producing or artifact-serving
  step, which the design's own §18 step 10+ concedes is unhardened.
- **What it gets the attacker.** Substitution of content under a valid,
  consented plan. Also enables a time-of-check/time-of-use gap: §5 and §7
  describe a push that stages on a `consented` device and waits for consent, and
  nothing says the staged bytes are re-verified at apply time.
- **Smallest fix.** Add `digest` to every operation that installs or replaces
  content, make it part of what the accept signs over (TC-02), and have the
  executor re-verify immediately before apply, not at receipt.

### TC-27 — The resource check happens on the signer's side, where a compromised signer is

- **Severity:** High · **Confidence:** High
- **Attack.** §7: resources are "checked against the port and path registries."
  Registries are Site Model data; the check is a compile-time property of the
  operator's compiler. §14 says the device carries a local *trust policy* — not
  the registries. So the device cannot re-verify that a plan's resources are
  legal; it takes the signer's word for it. The whole purpose of the plan is to
  bound the effect of a signer who may be compromised, and the plan's principal
  content check is performed by that signer.
- **Preconditions.** A compromised or coerced compile step. RT-03's
  preconditions exactly.
- **What it gets the attacker.** Arbitrary resources, in a plan that looks
  fully checked.
- **Smallest fix.** Ship the device its own resource policy — the set of paths,
  ports, and unit prefixes this device permits, derived from the registry at
  enrollment and thereafter changed only through the `trust.amend` path of
  TC-25 — so the executor performs the check locally against a policy the
  release cannot silently widen.

### TC-28 — `rollback` is a second, unconstrained operation set that runs precisely when nobody is watching

- **Severity:** High · **Confidence:** Medium
- **Attack.** §7 lists `rollback` as a field of an operation and says nothing
  about what it is or what constrains it. If rollback is itself operations, does
  it pass the capability check? Is it briefed to the advisor? Does it need its
  own consent? It executes under failure — unattended, urgent, at the moment
  logging and attention are worst. Declare a benign forward operation with a
  malicious rollback, then induce the failure; §12's interlocks give an attacker
  a supported way to make a bundle fail (a `pre_action` that stops returning
  zero).
- **Preconditions.** Ability to author a plan; ability to induce or wait for a
  failure.
- **What it gets the attacker.** Execution of operations the person was never
  briefed on, under exactly the conditions that suppress scrutiny.
- **Smallest fix.** Rollback is expressed in the same typed operation
  vocabulary, is capability-checked identically, is included in the briefing
  ("if this fails, the following will run"), and is covered by the same accept.
  A rollback that cannot be expressed in the vocabulary is not a rollback; it is
  a second plan and needs its own consent.

### TC-29 — Pre-rendered per-release plans versus arbitrary device staleness: the briefing describes a delta from a baseline the device may not be at

- **Severity:** High · **Confidence:** High
- **Attack.** §17 states the model's rationale: "Ahead-of-time rendering
  optimizes for devices that are routinely unreachable at authoring time." So
  the per-host ChangePlan for release N is generated without knowing where the
  device actually is. A device that has been offline for months and jumps from
  N−7 to N receives a plan describing the change from N−1. The prose the person
  reads ("this bumps a TLS library across a CVE and restarts the public proxy")
  is accurate for a device at N−1 and can be arbitrarily wrong for a device at
  N−7, where the same apply also lands six other releases' worth of state.
  Nothing in §7 defines a baseline field or a refusal on mismatch.
- **Preconditions.** A stale device, which the design says is the normal case.
  An attacker who can delay a device makes this deterministic rather than
  incidental.
- **What it gets the attacker.** Consent obtained for a described change while
  a materially larger change lands — with no forgery, no compromise, and an
  honest generator.
- **Smallest fix.** Every plan declares the baseline release it assumes. The
  executor refuses to apply a plan whose baseline ≠ its current converged
  release, and either applies the intermediate plans in order (each briefed and
  each consented, which is honest but expensive) or requires a catch-up plan
  generated for that specific baseline. This collides with the ahead-of-time
  model on purpose: the collision is real and §7 currently resolves it by not
  mentioning it.

### TC-30 — Consent is modeled as an event; CFEngine enforcement is continuous, and there is no `revoke`

- **Severity:** High · **Confidence:** High
- **Attack.** §7 frames consent around installs ("Installing new targets still
  does [need a local yes]"). The mechanism underneath is CFEngine, which
  re-asserts promises on every run, forever. So a single accept creates a
  standing enforcement loop: the person deletes the file, and it returns on the
  next run; they stop the service, and it restarts. That is not an install, so
  by §7's own framing it needs no new yes. §8's return path is `accept | reject`
  — there is no verb for withdrawing an accept, and §14's axes have no row for
  it. A person cannot get off.
- **Preconditions.** None. This is the design working as specified.
- **What it gets the attacker.** Permanence. One accepted change is a
  permanent change, and "consent" that cannot be withdrawn is the thing consent
  frameworks specifically exclude.
- **Smallest fix.** Add a third signed verb, `withdraw`, and define its effect
  in vocabulary the design already has: withdrawal converts the affected domain
  to §11's `deliberately-unmanaged` locally, the executor stops enforcing, and
  the state is reported upward as a first-class outcome rather than as drift.
  Grants carry a lifetime; continued enforcement past it is a re-consent event,
  not a silent renewal.

### TC-31 — Unknown and deprecated capabilities are unspecified, and the vocabulary is unversioned

- **Severity:** High · **Confidence:** Medium
- **Attack.** §7 says capabilities are "drawn from a closed list" and the
  executor "maps declared capabilities to an allowlist." Nothing says what an
  executor does with a capability it does not recognize. Fail-open (treat as
  unconstrained) is a total bypass and is what a tired implementer writes.
  Fail-closed strands every device behind a vocabulary update. Meanwhile the
  vocabulary will accrete: a coarse early capability gets split into six narrow
  ones, and the coarse name stays accepted for compatibility — which is the
  escape hatch §19 question 8 describes, arriving by accretion rather than by
  decision.
- **Preconditions.** Version skew, which is guaranteed in a fleet of
  intermittently-connected devices.
- **What it gets the attacker.** Either a bypass or a brick, chosen by finding
  which devices run which executor.
- **Smallest fix.** The capability vocabulary carries a version; the version is
  bound in the signed root metadata; unknown *or* deprecated capability is
  always a refusal with a distinct, reported reason; and the device's accepted
  vocabulary version only moves forward. Deprecation is a removal with a date,
  never an alias.

### TC-32 — The closed capability list exists only as a phrase: no schema, no example, no negative fixture

- **Severity:** High · **Confidence:** High
- **Attack.** `schema/` contains `common`, `launchd-writers`, `report-row`,
  `roles`, `services`. There is no ChangePlan schema, no capability enum, no
  trust-policy schema. §18's step 0 "remaining" list names peer_actions,
  trust-policy shape, generic unit-writers, lookup stub, and YAML canonicalize —
  and does not name the capability vocabulary at all. §18 states the project's
  own rule that "the lint fails if a schema arrives without its example," and
  §9 states that a convention an agent must remember "is a convention it will
  eventually break silently." The most security-load-bearing vocabulary in the
  design is currently a convention in a sentence, and the design says such
  things do not survive.
- **Preconditions.** None. This is a present-state gap, verifiable in the repo.
- **What it gets the attacker.** Whatever the first implementer improvises —
  and the implementer map's §14.2 says explicitly "Do not improvise. Independent
  adversarial review before build," which means the gate is known and the
  artifact that would let it be reviewed does not exist.
- **Smallest fix.** Write the capability enum and the ChangePlan schema with
  paired examples and negative fixtures before anything else in the trust layer
  is built, and add the vocabulary to §18's step-0 remaining list. A closed list
  that is not machine-checkable is, by §9's own standard, already open.

### TC-33 — Rollback of state is a downgrade the high-water mark does not see; and high-water behavior on refusal is unspecified

- **Severity:** Medium · **Confidence:** Medium
- **Attack.** Two adjacent gaps. (a) §7's downgrade protection is about
  metadata versions. `rollback` restores *state* from an earlier release without
  moving metadata backwards, so the anti-downgrade control does not engage: an
  attacker who can trigger rollback reverts a security fix while the device
  reports itself converged to the current release (§6: "Every report row carries
  the release that produced it"), making the record actively misleading. (b) On
  a `consented` device that *rejects* a release, does the high-water mark
  advance? If it advances on seeing metadata rather than on applying, the person
  can never later accept what they once refused; if it never advances, the
  device stays eligible for older releases. §7 says "each client that applies a
  signed artifact keeps a high-water mark," which leaves the refuse case
  undefined.
- **Preconditions.** A triggerable rollback; or an ordinary rejection.
- **What it gets the attacker.** A silent downgrade with a clean report row; or
  a device wedged out of a release it might later want.
- **Smallest fix.** Rollback targets are versioned and compared against the
  high-water mark like anything else; a rollback below the mark requires the
  same authorization as a downgrade. Separate "highest metadata seen" from
  "highest applied," advance the first on verification and the second on apply,
  and let a person accept a previously-rejected plan whose version is between
  the two.

---

## 5. Findings — first-run root and the TOFU exclusion (§7)

### TC-34 — The artifact under question displays the fingerprint it is being checked against: TOFU is relocated, not eliminated

- **Severity:** High · **Confidence:** High
- **Attack.** §7: "TOFU is not used for consented devices. Install shows the
  root key IDs / fingerprint; the person compares that to a channel they
  already trust." The installer is the thing showing the fingerprint. A hostile
  installer displays the *expected* fingerprint while enrolling its own root;
  the person compares, matches, proceeds. The ceremony authenticates the root
  only if the installer is already authentic, and the guide names no mechanism
  that establishes that. So the design has not removed trust-on-first-use; it
  has moved it from the root key to the installer binary, one level down and out
  of sight.
- **Preconditions.** Control of the install artifact at first contact —
  precisely the moment RT-01's systemic-gap table flagged as undefended.
- **What it gets the attacker.** The device's release authority, permanently,
  with the person's active participation in a ritual that felt like
  verification.
- **Smallest fix.** Root distribution must ride a channel the device already
  authenticates independently of the installer: the OS app-store signature on
  Android (the APK signing certificate is exactly the right primitive and the
  design already touches it in §6), a notarized/signed helper on macOS,
  distribution packaging on Linux. State that the ceremony's assurance derives
  from that channel, and that a sideloaded installer with a hand-typed
  fingerprint is TOFU with extra steps.

### TC-35 — For the consented tier, the trusted comparison channel is the operator — which is circular

- **Severity:** High · **Confidence:** High
- **Attack.** §7 lists the channels the person compares against: "operator,
  printed card, published fingerprint." For a `consented` device, the operator
  is the party the consent gate exists to constrain. Printed cards are printed by
  the operator; published fingerprints are published by the operator. All three
  reduce to "ask the person you are trying not to have to trust." The
  sovereignty claim in §1 and §8 is bootstrapped off the operator's word in the
  default case.
- **Preconditions.** A hostile or compromised operator — which is the threat
  model §8 exists for, and the reason §14 says full-mesh operator root "is not
  tenable once devices belong to more than one person."
- **What it gets the attacker.** The root, on the tier where it matters most.
- **Smallest fix.** Name at least one comparison channel that does not
  terminate at the operator: a transparency log the person's own tools query, a
  fingerprint published where the operator cannot silently revise it, or
  attestation from a second person in the household who enrolled earlier. If no
  such channel exists in a given deployment, §7 should say that the consented
  tier's root trust is delegated to the operator in that deployment, which is an
  honest and much weaker claim than the current text.

### TC-36 — Long-offline devices and root rotation: the chain is required, the recovery is "out of band"

- **Severity:** Medium · **Confidence:** High
- **Attack.** §7: "Later root rotation is in-band (threshold of old **and** new
  keys). Threshold compromise of root is again out of band." A device offline
  across N→N+1→N+2 must chain every intermediate root object; if any is
  unavailable — lost, garbage-collected, never mirrored to that device's
  channel — the device is stranded and the only remedy is physical. In a fleet
  of other people's phones the practical response to that pressure is to add a
  bypass, and the emergency role is sitting right there (TC-16). Separately: the
  guide states a threshold only for *rotation*. It never states a threshold for
  the root itself. The implementer map says 2-of-3; the guide, which wins on
  conflict, does not — so the normative text permits a 1-of-1 root, i.e. RT-01
  unmitigated.
- **Preconditions.** Ordinary long absence; ordinary key loss.
- **What it gets the attacker.** Stranded devices as leverage, and a normative
  document that permits the single-key root the prior red-team called Critical.
- **Smallest fix.** State the root threshold in the guide, in numbers. Require
  every root version to be retained and served for the life of the deployment
  (they are small). Define, in one paragraph, the out-of-band recovery
  procedure — who does what, with what, in what order — because "out of band" is
  a category, not a runbook, and the design has now used it twice for its two
  worst cases.

### TC-37 — Fingerprint comparison ergonomics are unspecified

- **Severity:** Low · **Confidence:** High
- **Attack.** "Compare the fingerprint" is known-weak when humans do it: people
  check the first and last few characters. The guide specifies no encoding, no
  length, no word-list rendering, and offers no machine-assisted compare.
- **Preconditions.** A near-collision on the checked substring, which is cheap
  to grind for the first/last-4 case.
- **What it gets the attacker.** A fingerprint that passes casual comparison.
- **Smallest fix.** Specify a compare that is hard to fake and easy to do: a
  scannable code or a word-list rendering, compared machine-to-machine where
  both ends are present, with the hex string as a fallback rather than the
  primary.

---

## 6. Findings — per-device trust (§14)

### TC-38 — Peer groups resolve outside the target's policy, so membership changes widen the target's allowlist invisibly

- **Severity:** High · **Confidence:** High
- **Attack.** §14's Peer axis: "Nobody, unless listed. Prefer groups plus
  allowed verbs." A group is an indirection whose *membership* is defined where
  the target does not control it — site-private, per §14's own "authored in
  site-private." The target's policy says `group: household-helpers` and does
  not change when a new device joins that group. A diff of the target's trust
  policy shows nothing. The person reviewing changes to their own device sees
  nothing to review.
- **Preconditions.** Ability to edit the group definition, i.e. the operator
  role. The guide actively *recommends* the vulnerable form ("prefer groups").
- **What it gets the attacker.** New peers with rights over a device, granted
  without any change to that device's stated policy and without appearing in any
  briefing.
- **Smallest fix.** Groups are an authoring convenience that compiles away —
  exactly as §10 compiles `provides`/`requires` into explicit, attributed edges.
  The device's signed policy contains explicit device public keys, so a
  membership change *is* a change to the target's policy, appears in the target's
  plan diff, and passes through the target's consent path.

### TC-39 — "Allowed verbs" cannot be enforced over ADB or any remote-shell transport, and that path uses a different identity system

- **Severity:** High · **Confidence:** Medium-High
- **Attack.** §13's motivating example is a helper acting "over ADB." §14 says
  "Identity is the device public key." For the ADB path that is false: ADB
  identity is an RSA key trusted at pairing time, in a store the tendcf design
  does not own. And ADB is not verb-constrained — `adb shell` is arbitrary code,
  and on a Shizuku-class device it reaches system privileges. So a peer
  allowlist entry granting one narrow verb grants, mechanically, everything the
  transport can do. If the site uses a single fleet-wide ADB key (a pattern
  visible in the project's own historical secret handles), any holder of that one
  key is every device's peer and per-target allowlists are decorative.
- **Preconditions.** A peer relationship that uses ADB or SSH as its transport,
  which §13 and §14 both name.
- **What it gets the attacker.** Full control of a target from a peer that was
  granted one narrow capability.
- **Smallest fix.** Peer verbs must terminate at a constrained endpoint: a
  small daemon on the target that exposes exactly the named operations and
  authenticates the device public key. Where the fallback is a general remote
  shell, the guide must say plainly that a peer with ADB or SSH is equivalent to
  operator tier on that device and that the allowlist is advisory for that
  transport. Per-device ADB keys, never a fleet key.

### TC-40 — The enforcement point for peer help is the target, but peer help exists for targets that cannot act

- **Severity:** High · **Confidence:** High
- **Attack.** §14: "Peer actions check the **target's** peer allowlist." §13's
  example is "a device that cannot start its privileged helper itself." If the
  target's component is down, the component that checks the allowlist may be the
  one that is down. In practice enforcement falls to the helper (voluntary, so
  not enforcement) or to the target's OS (a different trust root, TC-39).
- **Preconditions.** The failure mode peer actions exist to address.
- **What it gets the attacker.** Peer rights over a target at exactly the
  moment the target cannot refuse — and "the target is unhealthy" is a state an
  attacker can often induce.
- **Smallest fix.** The allowlist check must live in a component whose
  availability is independent of what peer help repairs — the OS-level
  authorization on the receiving side, provisioned at enrollment with the peer
  keys — and §14 should state which component holds it for each transport rather
  than saying "the target."

### TC-41 — Web-of-trust attestation thresholds are Sybil-able by the operator's own fleet

- **Severity:** Medium · **Confidence:** High
- **Attack.** §14's Attestation axis and its closing line put WoT thresholds
  ("50% of people I trust have installed this") in the advisor plug-in. The
  operator generates all releases and holds all operator-tier devices, which
  apply automatically without consent. Those devices produce genuine
  apply-attestations first, every time. Any "N of my trusted set already
  installed this" signal is therefore satisfiable by the proposer, on demand,
  before any independent party has looked.
- **Preconditions.** An advisor plug-in that weights attestation counts —
  which is the feature §14 describes.
- **What it gets the attacker.** A manufactured herd signal that pushes the
  advisor toward accept, without touching the plan or the briefing.
- **Smallest fix.** Attestations are weighted by *independent release
  authority*, not by device count: all devices under one release root count as
  one voice. State this in §14, because a plug-in author reading the current
  text will count devices.

### TC-42 — The `managed` tier lets someone else choose whether a device holder gets a say, with no notice requirement

- **Severity:** Medium · **Confidence:** High
- **Attack.** §14's Consent axis: "`managed`: operator-chosen." So there is a
  tier in which whether a device's holder is consulted is decided by someone
  else, and nothing in §14 requires that the holder be *told* which tier their
  device is in or when it changes. Combined with TC-25 (tier is release-delivered
  policy), a device can be moved from `consented` to `managed` by a release.
- **Preconditions.** Operator action. No compromise.
- **What it gets the attacker.** Silent removal of a person's veto, in a design
  whose stated purpose is that veto.
- **Smallest fix.** Tier is displayed persistently in the device's own status,
  a tier change is always a `trust.amend` (TC-25) requiring the current advisor
  key, and downgrading `consented` → `managed` additionally requires local
  physical confirmation. A person should never learn their tier changed by
  noticing they stopped being asked.

---

## 7. Findings — token discovery (§15)

### TC-43 — The lookup CLI and the near-miss catalog are a designed-in enumeration oracle over private site data

- **Severity:** Medium · **Confidence:** High
- **Attack.** §15 specifies a lookup CLI (`who-provides`, `does-role exist`,
  `tokens kind=service`) and, on failure, "compile error listing near-misses
  and the catalog." §3 says inventory is private by default and that the full
  host list, RFC1918 addresses, and serials stay private. The lookup answers
  exactly the questions an attacker asks — who holds port 443, does this role
  exist — and the error path is designed to *dump* the catalog on demand. An
  author who cannot query directly provokes an error instead.
- **Preconditions.** Ability to run a compile or invoke the CLI. Since §9's
  premise is that AI agents author most configuration, and §2 admits foreign
  site-shared inputs, the population with that ability is not the operator alone.
- **What it gets the attacker.** The private site catalog, through the
  discoverability feature, with no compromise.
- **Smallest fix.** Scope lookup answers to the layer the caller is authoring
  in: an author working in a foreign or shared layer gets existence answers for
  tokens their layer may legitimately reference, never enumeration. Near-miss
  suggestions are restricted to the caller's own layer.

### TC-44 — `secret:` as a discoverable token kind makes RT-06's handle-injection interface auto-completing

- **Severity:** High · **Confidence:** High
- **Attack.** §15 makes `secret` a first-class token kind and gives authors a
  CLI to enumerate tokens by kind plus compile errors that list near-misses.
  RT-06's attack was "a malicious service contract gains the ability to *name* a
  handle." §15's discovery mechanism now tells an author *which handles exist*
  and helps them spell the name correctly. Meanwhile the only enforcement the
  guide names is §14's one-cell "secretspec resolver," with no stated policy at
  all — no binding of (service identity, host, capability, release) to an
  allowed handle. The repository's negative fixture in this area (`06-literal-secret`)
  catches a literal *value*, which is the narrow property RT-06 specifically said
  was too narrow.
- **Preconditions.** Ability to author a service record — the ordinary case,
  performed mostly by AI agents per §9.
- **What it gets the attacker.** A path from "can add a service" to "can name,
  and then receive, a privileged secret," with the design's own discovery tools
  assisting.
- **Smallest fix.** `secret:` is excluded from enumeration and from near-miss
  output entirely: the only answerable question about a secret handle is "does
  this exact handle exist and is this caller entitled to it," answered
  yes/no. And §14's secrets row is expanded into a stated deny-by-default rule
  keyed on service identity, host key, capability, and release, because a named
  enforcement point with no policy is not an enforcement point.

### TC-45 — Two closed lists share the word "capability," and §15's "closed enum" is printed with an ellipsis

- **Severity:** Medium · **Confidence:** High
- **Attack.** §7's `capability` is the ChangePlan operation vocabulary the
  executor enforces. §15's token kinds are a different closed set — and in
  `schema/common.schema.json` they are literally named `capability_token`, with
  the broken fixture called `07-typo-capability-kind`. An implementer told to
  "implement the closed capability list" has two candidates and one of them
  already exists. Compounding it, §15 writes the supposedly closed enum as
  "(`service`, `port`, `path`, `secret`, `class`, `network`, …)" — an ellipsis
  in a sentence asserting closure, and a list that omits `package` and `device`,
  both present in the schema.
- **Preconditions.** An implementer reading the guide, which §9 says is the
  design's primary risk surface.
- **What it gets the attacker.** Nothing directly — this is how the *defender*
  builds the wrong thing, which §9 argues is the dominant failure mode.
- **Smallest fix.** Rename one of them (the ChangePlan side to `operation
  capability`, or the token side to `token kind`, matching §15's own prose), and
  print closed enums in full or point at the schema rather than trailing an
  ellipsis.

### TC-46 — Provider pre-registration and alias binding are fleet-wide effects with no distinct review class

- **Severity:** Medium · **Confidence:** Medium
- **Attack.** §15 auto-provides `service:<name>`; §2 makes two peers claiming
  one identity a compile error resolvable only by site-private binding a winner
  (`caddy: from: alice`). Two consequences. (a) A record can claim a token that
  nothing currently provides; when a later record requires it, the squatter
  becomes an ordering prerequisite and runs *before* the thing that needed it —
  useful if the requirer is security-relevant. (b) The alias/binding line in
  site-private redirects a fleet-wide identity in one line, and nothing marks it
  as a higher-review-class edit than an ordinary field change.
- **Preconditions.** Ability to contribute a shared or foreign recipe, or to
  edit site-private.
- **What it gets the attacker.** Execution ordering ahead of a chosen service,
  or silent substitution of which record backs a well-known name.
- **Smallest fix.** Report new providers of previously-unprovided tokens as a
  change in the plan diff, the same way §10 reports authored/inferred edge
  coincidences rather than collapsing them; and mark binding/alias edits as a
  distinct review class in the same category as trust-policy edits.

---

## 8. Findings — the writing rule as a foundation for the trust layer (§9)

### TC-47 — §9's local-knowledge rule, applied to the trust layer, means nothing ever evaluates the global invariant

- **Severity:** High · **Confidence:** High
- **Attack.** §9's rule is "prefer designs that require only local knowledge
  over designs that require global knowledge." Security properties are global
  invariants: *no path exists by which an unprivileged writer reaches code
  execution as root.* The trust layer as designed is local everywhere — the
  executor checks one operation against one capability, the briefing summarizes
  one plan, the advisor evaluates one change, the peer check consults one
  allowlist. No component holds the aggregate, and TC-09 is the direct
  consequence. §9 is an excellent *authoring* rule and a dangerous
  *authorization* rule, and the guide never draws the line — §9 is stated
  globally and §§7/8/14 are built on it.
- **Preconditions.** None; this is the design's own foundation.
- **What it gets the attacker.** The composition attacks: split privilege
  across operations, plans, releases, and peers, each locally legal.
- **Smallest fix.** State the exemption in §9 itself: the rule governs the
  authoring surface; authorization decisions require whole-plan and
  whole-device-state context, and the design must name the component that holds
  it. The natural holder already exists — the executor, with §6's local record —
  and naming it turns TC-09's fix from new machinery into wiring.

### TC-48 — The trust layer's load-bearing claims are conventions, which §9 says do not survive

- **Severity:** Medium · **Confidence:** High
- **Attack.** §9: "A convention an agent must remember is a convention it will
  eventually break silently… If a comment says 'remember to…', that text belongs
  in a schema instead." Now inventory §§7/8: "It never authorizes." "The advisor
  never authorizes; the executor does." "Free prose must point at the exact
  fields it is summarizing." "Signing authenticates the author; only the plan
  constrains the effect." Every one of those is a remembered convention, and
  each is a security property. §12 shows the project knows how to do better —
  interlock blast radius and reporting are "required constants in the schema,
  not author-settable fields" — but that treatment is not applied to the
  consent layer, which is where it matters more.
- **Preconditions.** None. This is the guide judged by its own standard.
- **What it gets the attacker.** Whatever the implementer forgets, which §9
  argues is everything eventually.
- **Smallest fix.** Convert each claim into a check: "never authorizes" becomes
  "the executor's accept-verification path takes the typed plan as input and
  has no code path that reads semantic-layer bytes"; "prose cites fields"
  becomes TC-07's regenerate-and-compare; "only the plan constrains" becomes
  TC-23's confinement profile. Each is testable, and the project's negative-fixture
  habit (`examples/broken/`) is the right vehicle.

### TC-49 — §9's evidence predicts advisor failure at exactly the reasoning consent requires, and is cited in one direction only

- **Severity:** Medium · **Confidence:** High
- **Attack.** §9 marshals *Lost in the Middle* and the IaC error taxonomy to
  argue that models reason well locally and badly globally, and that "a
  distinct, substantial error category is *contextual reasoning failure* —
  missing or wrong cross-resource references." Evaluating a ChangePlan is
  entirely cross-resource reasoning: is this path privileged given what else is
  on this device, does restarting this proxy break that interlock, does this
  capability compose with the one accepted last week. §8 places a model in
  precisely that role, and §9's evidence is not applied to it anywhere. The
  guide uses its citations to design *around* model weakness when authoring and
  to design *onto* the same weakness when reviewing.
- **Preconditions.** None; this is an internal inconsistency between §9 and §8.
- **What it gets the attacker.** A reviewer that the design's own literature
  review predicts will miss cross-resource attacks — which is what TC-09,
  TC-25, TC-26, and TC-29 all are.
- **Smallest fix.** Say it out loud in §8 and mitigate structurally rather than
  by prompt: give the advisor the typed plan (TC-06), the device's recent
  history (TC-09), and a computed privilege-transition flag (TC-09), so the
  cross-resource reasoning is *performed by the executor and handed to the
  model as a fact*, rather than expected from the model. Add §9's own
  counter-example test to §19: if the advisor is where global reasoning must
  happen, the writing rule has a boundary the guide has not drawn.

---

## 9. Cross-cutting findings

### TC-50 — The build order offers consent (step 9) before artifact provenance (step 10+), which is what RT-08 said not to do

- **Severity:** High · **Confidence:** High
- **Attack.** §18's table: step 9 is "Consent / sovereignty — Advisor slot +
  default prompt"; step 10+ is "reproducible APK provenance." RT-08's
  conclusion was verbatim: "Do not offer consent for an opaque Shizuku-capable
  binary and call it informed approval." The current build order does exactly
  that, and TC-26 (no artifact digest in the plan) means the consent surface
  will not even carry the weaker digest-based assurance when it ships.
- **Preconditions.** Following the stated build order.
- **What it gets the attacker.** A consent ceremony over an opaque privileged
  binary, plus the legitimacy that ceremony confers.
- **Smallest fix.** Either move a narrow provenance gate — dependency lock,
  signing-certificate pin, per-release privilege/permission delta, artifact
  digest in the plan — ahead of step 9, or scope step 9's consent to capability
  classes whose artifacts are provenance-covered, and say in §18 that opaque
  privileged artifacts are outside the consent surface until step 10+ lands.

### TC-51 — The guide wins on conflict and is weaker than the implementer map on several security properties

- **Severity:** Medium · **Confidence:** High
- **Attack.** The guide's own preamble: "Where any other living document
  disagrees on the **current design**, **this guide wins**." Comparing §§7/14
  against `architecture-DEFINITIVE-v3.md`: the map states a 2-of-3 offline root
  and the guide states no root threshold at all (TC-36); the map states "NAR
  digests in the manifest (RT-05)" and the guide's §7 field list has no digest
  (TC-26); the map's §14.2/§14.3 name the ChangePlan IR and the advisor
  loop as "do not improvise, independent adversarial review before build," and
  the guide carries no equivalent gate. Under the stated precedence rule, the
  weaker text is the normative one, and mitigations the project believes it has
  are not in the document that governs.
- **Preconditions.** An implementer following the precedence rule as written.
- **What it gets the attacker.** Silently dropped mitigations, with a
  documentation policy that makes the drop authoritative.
- **Smallest fix.** Either promote the security-relevant specifics (root
  threshold, artifact digests, the §14.2/§14.3 build gates) into the guide, or
  add one sentence to the precedence rule: the guide wins on *design*, and named
  security parameters in the implementer map are floors the guide does not
  relax. The current rule is right for architecture and wrong for thresholds.

---

## 10. Required: disposition of the nine prior findings

Prior document: `docs/architecture/deprecated/redteam-trust-layer-openai-v1.md`.
Verdict per finding — **RESOLVED**, **RESTATED** (present in the current guide
in substantially its original form, however relabeled), or **MOOT** (the design
change removed the surface). Several are genuinely mixed; where so, I say which
half went which way rather than rounding.

### RT-01 (Critical) — One release key is fleet-root, no recovery protocol → **RESOLVED in kind, RESTATED in parameter, and re-instantiated in the emergency role**

The one-key model is gone. §7 now describes a TUF subset with an offline root,
release signatures, a snapshot binding, an emergency role, in-band rotation
under a threshold of old and new keys, and out-of-band handling for threshold
compromise. That is the shape RT-01 demanded, and the *class* of finding is
resolved.

Three residues. (a) The guide never states a threshold *number* for the root
itself — only for rotation — so the normative document still permits the 1-of-1
root RT-01 called Critical; the 2-of-3 lives only in the implementer map, which
loses on conflict (TC-36, TC-51). (b) "Out of band" is used twice for the two
worst cases and is a category, not a runbook; RT-01 asked for an incident
response channel and there is none (TC-36). (c) The emergency role is a new
instance of the original finding — a single, consent-bypassing, fleet-reaching
key with no stated threshold, expiry, or reversal (TC-16).

### RT-02 (High) — Replay, freeze, mix-and-match → **RESOLVED for replay and mix; RESTATED for freeze; new gaps in channel binding and fast-forward**

Replay and downgrade: resolved by the per-client high-water mark. Mix-and-match:
resolved by the snapshot that "binds the metadata set together." Both are
explicit in §7 and both are real.

Freeze is **not** resolved and is *asserted* to be, which is worse than
silence: §7 claims the high-water mark rejects freeze, and it cannot — freeze is
withholding, which leaves the mark untouched. The role list contains no
timestamp role, and per-plan `expiry` cannot be evaluated on devices the design
describes as routinely offline and clock-unreliable (TC-18). RT-02 also asked
for channel binding and exact artifact length/digest; neither appears in §7's
field list (TC-26). And the fast-forward direction — one validly-signed
far-future version permanently wedging a client — has no reset path.

### RT-03 (Critical) — Signed plans do not constrain execution → **RESOLVED in intent, RESTATED in substance; the provenance half was dropped entirely**

This is the finding the current design most visibly answers: §7's typed
ChangePlan with a closed capability list, exact resources, key-bound target,
rollback, expiry, and nonce is close to a transcription of RT-03's mitigation
("define a typed operation IR with declared preconditions, resources,
capabilities, rollback, and target key; make executors enforce that IR"). Credit
where due — the architecture moved.

But the property is claimed at a strength no mechanism delivers: "refuses any
effect outside that set" is unachievable without confinement, which the guide
never names, while service `command`, interlock `pre_action.command`, and
package scripts are all arbitrary code at the point of launch (TC-23). The
policy/`.cf`/generic-bundle channel is outside the plan entirely, and D30
already anticipates freehand `.cf` (TC-24). Resources are checked on the
signer's side, which is where the compromise RT-03 posits lives (TC-27). And
RT-03's *other* mitigation half — clean isolated signing checkouts, no signing
from task worktrees, two-person review of trust-boundary changes,
in-toto/SLSA-style attestations binding commits to artifacts — appears nowhere
in the guide, in any section. Source-to-signing is still outside the trusted
computing base as documented.

### RT-04 (High) — `offer()` is consent theater → **RESOLVED on most enumerated fields; RESTATED on three; and the binding it assumed does not hold**

RT-04 asked for: signed plan ID, target device public-key fingerprint, release
sequence, exact capability vector, artifact digest, expiry, single-use nonce,
rollback identity, timeout-is-deny, integrity-protected grant store, executor
comparison against the grant, and refusal persistence. §§7/8 now carry the
target binding, capability vector, expiry, nonce, rollback field, and
timeout-is-deny. That is most of the list and it is a real improvement.

Missing: **artifact digest** (TC-26), **refusal persistence** (TC-19), and any
statement that grants are stored integrity-protected or that the executor
compares against the *grant* rather than the plan. Beyond RT-04's own list, the
current design adds a binding failure RT-04 did not anticipate because it
assumed the grant would cover the operation: the accept is bound only to the
nonce, so it covers neither the plan bytes nor the briefing (TC-02), and there
is no `withdraw` (TC-30), no per-operation granularity (TC-10), and no
constraint on the advisor at all (TC-08). Net: the *fields* largely arrived; the
*binding* did not.

### RT-05 (Critical) — Builder/cache confused deputy → **MOOT by scope, with the mitigation recorded in the wrong document**

The private builder/cache surface is descoped to §18 step 10+ ("demand-driven"),
and §14's secrets/cache row restricts cache keys to `operator`. Within the
current design there is no live cache to attack, so the finding is moot *today*.

Two notes for the synthesis pass. The guide's total protection is one table
cell; the substantive controls RT-05 asked for — separated builder identity,
upload authority, serve authority, and release authorization; NAR inventory
verified before activation; reproducible independent rebuild of privileged
closures — exist only in the implementer map's "NAR digests in the manifest
(RT-05)," which loses on conflict (TC-51). And the descoping is what makes it
moot, so the moment step 10+ arrives the finding returns in full with nothing
written down.

### RT-06 (High) — SecretSpec handle injection → **RESTATED, and arguably worse**

Naming a handle is still the interface. §3 keeps environment as "names of
secrets"; §14 names an enforcement point ("secretspec resolver") with no stated
policy — no binding of service identity, host, capability, or release to an
allowed handle, which was the entire content of RT-06's mitigation. The
repository's negative fixture in this area catches literal secret *values*,
which is exactly the narrow property RT-06 identified as insufficient.

The escalation: §15 promotes `secret` to a first-class token kind inside a
discovery mechanism that enumerates tokens by kind and prints near-miss
catalogs on error (TC-44). RT-06's precondition was "gains the ability to name a
handle"; §15 now helps an author find the handle and spell it correctly.

### RT-07 (High) — Role mesh lease/fencing and converger DoS → **MOOT for locking; RESTATED for role disagreement; the DoS half is absent**

The locking half is genuinely moot by design change, and it is one of the
better changes in the current architecture: §13 explicitly renounces the
distributed lock and the fleet-stalling FSM, makes stall local, makes the FSM a
reconstructed view, and §18 keeps autonomous behavior out of the early build
order. RT-07's split-brain-over-a-lease scenario has no surface left.

Role *disagreement* is not moot. Role assignment is data in a signed release
(§3), releases reach devices at different times by design, and §5 lets "a host
that currently holds a deploy role" push. Two hosts holding different releases
therefore hold different beliefs about who holds the role — and disagreement is
the normal state, not the exceptional one. §§13/14 define no epoch, no fencing,
and no rule for resolving it. The converge-agent DoS half of RT-07 (download
limits, quotas, backoff, watchdog, kill switch) appears nowhere in the guide;
the implementer map mentions quotas once, in passing, for pull.

### RT-08 (High) — Android provenance → **RESTATED and deferred, and the deferral now contradicts the build order**

§6 hardens the Android *storage* boundary well (UID separation, agent owns
JSONL and SQLite in app-private storage, never "the agent opens Termux's
files"). Provenance is untouched: reproducible APK provenance is §18 step 10+,
there is no signing-certificate pin, no permission/privilege delta, and no
artifact digest in the plan (TC-26).

The new problem is ordering. Consent is step 9; provenance is step 10+. RT-08's
one-sentence conclusion was not to offer consent over an opaque privileged
binary. The build order schedules exactly that (TC-50).

### RT-09 (High) — local-fix / upstream-heal injection → **RESTATED, with the decision relocated into the least-defended component**

§8 retains the loop: "Personal branch: theirs, applied under their consent…
Upstream-heal is a suggestion their agent evaluates." Of RT-09's demanded
controls — patch digest, target list, capability delta, expiry, rollback,
mandatory human review, and never "version contains fix" — the guide carries
rollback and expiry as generic plan fields and none of the rest.

RT-09's final line was "an AI advisor must never be an authorization oracle."
The current design honors it nominally (§8: "The advisor never authorizes; the
executor does") while making the advisor's signature the sole authorization for
installs on the tier that matters, and then hands that advisor the
equivalence decision. Combined with TC-01 (the briefing is injectable), TC-07
(the fidelity rule is forgeable), and TC-08 (no bar on the advisor is
expressible), the relocation makes RT-09 *more* exploitable than the version
that just said "prefer upstream" — because now there is a component that can be
argued with (TC-14).

### Summary table

| Prior | Severity then | Disposition now | Where |
| --- | --- | --- | --- |
| RT-01 one key / no recovery | Critical | **RESOLVED** in kind; **RESTATED** on threshold + runbook; re-instantiated in the emergency role | TC-16, TC-36, TC-51 |
| RT-02 replay / freeze / mix | High | **RESOLVED** replay+mix; **RESTATED** freeze (and falsely claimed resolved); new fast-forward gap | TC-18, TC-26 |
| RT-03 plans don't constrain execution | Critical | **RESOLVED** in intent; **RESTATED** in substance; provenance half dropped | TC-23, TC-24, TC-26, TC-27 |
| RT-04 consent theater | High | **RESOLVED** on most fields; **RESTATED** on digest, refusal persistence, grant store; binding fails | TC-02, TC-10, TC-19, TC-26, TC-30 |
| RT-05 builder/cache | Critical | **MOOT** by scope; returns intact at step 10+; mitigation only in the non-winning document | TC-51 |
| RT-06 secret handle injection | High | **RESTATED**; §15 makes the naming interface discoverable | TC-44 |
| RT-07 lease/fencing + converger DoS | High | **MOOT** for locking; **RESTATED** for role disagreement; DoS half absent | §5/§13 gap; TC-51 |
| RT-08 Android provenance | High | **RESTATED**, deferred, and contradicted by the build order | TC-50, TC-26 |
| RT-09 local-fix / upstream-heal | High | **RESTATED**, relocated into the advisor | TC-14 |

Zero of the nine are cleanly resolved with no residue. Two (RT-05, RT-07) are
moot in the way that matters most — by *removing surface*, which is the
strongest form of fix and should be read as the design's best security work.
Three (RT-01, RT-03, RT-04) show real architectural movement toward the
mitigation with a gap between the claim and the mechanism. Four (RT-02 in part,
RT-06, RT-08, RT-09) are substantially where they were.

---

## 11. What I did not review

Sections 1–6, 10–13, 16–18 except where §§7/8/9/14/15 depend on them (§2's layer
diagram for the advisor prompt and site-private's contents; §5's push and
git-synced policy; §6's record as an available mitigation; §12's interlock
command field; §16's rendered examples; §17's ahead-of-time rationale; §18's
build order and built/not-built status; §19 question 8). I did not review the
compiler, ordering inference, extra-entry accounting, or the Bcfg2 lineage
claims. I did not attempt to verify any implementation, because per §18 there is
none — every finding is against design text, and I have flagged where a finding
rests on the guide's *silence* rather than on its statements.

---

**Findings: 51.** Critical 7 (TC-01, TC-02, TC-03, TC-16, TC-23, TC-24, TC-25) ·
High 28 · Medium 14 · Low 2.
