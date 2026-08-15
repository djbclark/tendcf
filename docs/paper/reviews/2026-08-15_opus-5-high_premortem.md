# Pre-mortem: why tendcf was abandoned

**Date:** 2026-08-15
**Reviewer:** Opus 5 (high), acting as a sceptical engineering manager
**Subject:** `docs/paper/tendcf-architecture-guide.md`, especially §17, §18, §19
**Frame:** It is February 2028. tendcf is dead. This is the postmortem.

This is not a design review. I am not saying the architecture is wrong. Most of
it is better-argued than what I usually see. I am saying it did not get built,
and I am explaining why, working backwards.

---

## 0. What I looked at, and the two numbers that set my priors

Before the exercise, the repo state as of 2026-08-15:

| Measure | Value |
| --- | --- |
| Project age | 5 days (first commit 2026-08-10) |
| Total commits | 55 |
| Commits prefixed `docs:` | 53 of 55 (the other two are `ci:`) |
| Lines of prose under `docs/` | 16,276 across 48 files |
| Lines of code + schema | 1,024 (`bin/schema_lint.py` 364, `bin/check_protected_docs.py` 109, five schemas ~551) |
| Commits on 2026-08-13 alone | 43 of 55 |
| `nix2cf` repo (the compiler, Step 3) | 3 files: `LICENSE`, `README.md`, `.gitignore`. Six commits, all `docs:`. It has been refactored *to zero* — it used to hold the schemas and they were moved out. |
| Superseded architecture drafts in `docs/architecture/deprecated/` | 9 files, ~5,400 lines, from at least three different model families (`-grok-v1`, `-openai-v1`, plus Gemini reviews) |
| Paper reviews in `docs/paper/reviews/` | 6, three of them dated today |
| Incumbent (`~/ops/stayturgid`) | 919 commits, 33,067 files, shipped `ops-v1.3.20` on 2026-08-11 — four days before this guide |
| Sibling repos under `~/src` | 61, of which ~12 touched in the last two weeks |

Two ratios did most of the work in this pre-mortem:

1. **16:1 prose-to-code, in week one.** Not a criticism of the prose. A
   statement about which loop is closing.
2. **The compiler repo is empty and getting emptier.** Every commit to `nix2cf`
   so far has *removed* scope from it or renamed something. That is the shape
   of a project where the architecture is being tidied instead of executed.

I did not have to invent the failure modes below. Several are visible in the
commit graph already.

---

## 1. The narrative: February 2028

Nobody decided to stop. There was no bad meeting, no failed deploy, no moment
where it was clear this wasn't going to work. Here is the actual sequence.

**Months 0–3.** Step 0 finished, sort of. `peer_actions`, the trust-policy
shape, and the generic unit-writers each turned out to be a design problem
rather than a schema chore, and each generated its own decision record and its
own `Approved-change:` commit. The schema count went from five to eleven. The
negative fixture count went from twelve to thirty-one. The lint got good. It is
genuinely good — it is the best-tested part of the system and it validates
files that nothing consumes.

**Months 3–7.** Step 1, the macOS adapter. CFEngine Community got installed on
the primary workstation, which was the first real contact between the design
and a machine. Two things happened. First, the unit-writer registry met a
laptop with ~90 launchd jobs already on it — Homebrew services, the incumbent's
`control/bin` reconnect agents, vendor daemons — and the honest transcription
produced a `not-yet-migrated` count in the low thousands, exactly as §11
predicted and §19.3 worried about. Second, dry-run stayed on, because the box
can't be reimaged, so the loop was: change YAML → render → read a diff → decide
not to apply it. Four months of work whose entire output was a diff nobody
enforced. The reporting was built, as §18 said it must be. It reported on a
machine that tendcf was not managing.

**Months 7–11.** Step 2, Android. This is where the real time went. CFEngine
does not ship for Termux and the aarch64/bionic build needed patching; the
alternative — cf-agent as a native helper inside the agent APK at its own UID,
staying alive under Doze — is an Android systems project, not a config-
management step. Meanwhile, the incumbent already does all of this well: 919
commits of hard-won Termux/Shizuku/ADB knowledge, in production, on the same
fleet. Re-deriving it from scratch under a self-imposed rule that the incumbent
is "not a dependency, not an upstream, and not copied into this project" was
the least rewarding work in the plan, and it sat *before* the compiler in the
build order, so nothing downstream could start.

**Months 11–14.** Attention drifted to `sudo-secretspec` and `Shizuku` — which
are on tendcf's own critical path, so it didn't feel like drift — and to two
projects that aren't. `stayturgid` shipped `ops-v1.4.x`. It kept working. That
was the quiet problem: at no point in fourteen months did the fleet do anything
it couldn't do in August 2026.

**Months 14–18.** The paper got finished. It is good. It went out for review, it
got sharper, the ceilings in §17 held up, §19 got a tenth open question. The
guide is now 1,400 lines and the implementer map is 900. Somewhere in here the
project stopped being an infrastructure project that had a paper and became a
paper that had a repo. Nobody noticed the transition because every individual
week looked like progress on tendcf.

**The last commit** is a `docs:` commit.

The proximate cause of death is not any of the technical risks below. It is
that **the design phase produced its full psychological payoff — a coherent,
defensible, publishable artifact with an acknowledgements page — before a
single device was managed, and nothing downstream ever paid as well.**

---

## 2. Causes, bucketed

Confidence = how sure I am this is real for *this* project. Severity = how much
of the project it kills if it fires. No pre-filtering; low-probability items are
included and tagged as such.

### Bucket 1 — ALREADY NAMED (§17 ceilings or §19 open questions)

Credit where due: this document concedes more than most. The problem with these
is not that they're unnamed. It is that **naming a risk and scheduling its
resolution are different acts, and none of these has a date.** Every one of them
resolves at Step 3 or later, i.e. after 12+ months of work premised on the
answer being favourable.

| ID | Cause | Where named | Conf. | Sev. | The part that is *not* covered by the naming |
| --- | --- | --- | --- | --- | --- |
| A1 | Inference (`provides`/`requires` → edges) is extra machinery for a problem retry-until-stable already solved. It is also the project's claimed novel contribution, so it will be defended past its expiry. | §19.1, §10 (three ways it may be wrong), §17 ceiling 2 | High | High | The build order puts the *validation* of the contribution at Step 3, behind two platform adapters. The most falsifiable claim is scheduled last. |
| A2 | The writing rule (§9) is a hypothesis, not an argument; a counter-example would be a bug caught *because* a global constraint was forced. | §19.2 | High | High | §9 is load-bearing for the entire schema-first strategy. If it's wrong, Steps 0 and 3 were the wrong shape, and there is no experiment in the plan that could tell you. |
| A3 | `not-yet-migrated` counts accumulate instead of grinding down, because Bcfg2 had a person whose job that was and this fleet has nobody. | §19.3 | High | High | Not named: the *mechanism* of collapse. When the count is unbearable, the pressure isn't to grind it down — it's to reclassify. `deliberately-unmanaged` becomes the escape hatch, and the two-reason design that "makes default-on livable" degrades to a one-reason design, which is the bare on/off flag §11 rejects. This is §19.8's escape-hatch failure applied to §11, and the doc doesn't connect them. |
| A4 | Per-domain granularity: a badly drawn domain hides drift as effectively as opting out. | §19.4 | Med | Med | Who draws the domains, on a machine with 33k+ files, and with what budget. |
| A5 | Local-first reporting may be the wrong call; Bcfg2's operators found network-wide reports were what bought trust. | §19.5, §17 ceiling 1 | High | Med | The ceiling is stated in the abstract but never checked against this fleet. For a household fleet, the operator's *actual* recurring question — "are all my phones up right now" — is already the fleet-wide query. The design is at the ceiling on day one, not approaching it. |
| A6 | When a genuinely global question arrives, is "query reachable devices, treat the rest as unknown" enough? | §19.6 | Med | Med | It's enough for correctness and inadequate for morale, which is the binding constraint in a solo project. |
| A7 | Edge-origin information may not actually make bad inferred edges a lookup rather than a search. Nobody has run it. | §19.7 | Med | Med | Silent failure mode, correctly identified. Cost of finding out is building the whole inference engine first. |
| A8 | The ChangePlan capability list gets an escape hatch and the mechanism becomes decorative. | §19.8 | High | High | The doc frames this as a discipline problem. It is a *staffing* problem: the person who wants the escape hatch, the person who approves it, and the person who owns the security model are the same person, at 11pm, blocked. |
| A9 | The whole premise may be the wrong shape — if the real weakness is plausible-looking output type systems don't catch, the schemas defend the wrong wall. | §19.9 | High | High | This is the most honest line in the document and it is doing double duty as a lightning rod. It names a *technical* premise risk in a way that makes it feel like the premise has been examined. It does not touch any of the four premise risks in Bucket 3. |
| A10 | Signed-release-as-artifact stops being adequate under a bounded clock. | §17 ceiling 3 | Med | Med | Also already true: an operator patching their own daily-driver Mac has a bounded clock every single time. Ahead-of-time rendering is optimized for a fleet-reachability profile that the *primary* device does not have. |
| A11 | The cold path (factory reset → converged) is untested; convergent automation leaves no trace of a run-1 constraint. | §10, conceded — not in §17/§19 | High | High | Conceded in the body but absent from the risk sections and absent from the build order. Step 5 ("first real Linux host") is the first cold-boot test and it is the fifth step. Everything before it is being designed against a read of already-provisioned devices. |

### Bucket 2 — NOT NAMED (real, absent from §17 and §19)

| ID | Cause | Conf. | Sev. | Detail |
| --- | --- | --- | --- | --- |
| N1 | **Step 2 (Android) is a systems-programming research spike wearing a build-step's clothes, and it blocks the compiler.** | High | **Fatal** | §6 handles the Termux/agent UID split with real care — but only for *logging*. The guide never establishes that `cf-agent` builds and runs on Termux/aarch64/bionic at all, and there is no upstream Termux package. The two escape routes are (a) port and maintain a CFEngine build for Termux, or (b) ship cf-agent as a native helper inside the APK at the agent's UID, surviving Doze and background limits. Both are multi-month C/Android projects. This is Step 2 of 11. If it fails, Steps 3–10 never start, because the build order says inference waits for "types on two platforms." **The single most underestimated item in the document.** |
| N2 | **Steps 0–5 produce zero operator benefit.** | High | **Fatal** | Step 1's target is the box that can't be reimaged, so dry-run is standing posture — a diff nobody applies. Step 2 duplicates a capability the incumbent already delivers. Step 3 is a compiler with no consumer yet. The first moment tendcf does something for its operator that wasn't already being done is Step 5 at the earliest, realistically Step 8. For a solo project with no external deadline, a value-free first year is the failure mode, not a phase. §19.3 is adjacent (no one to grind the backlog) but is about a different thing. |
| N3 | **The purity rule against the incumbent is self-imposed, uncosted, and never justified.** | High | **Fatal** | "A previous configuration stack on this fleet is legacy reference only. It is not a dependency, not an upstream, and not copied into this project. Patterns taken from it are described in generic terms." That stack is 919 commits and 33,067 files, shipped `ops-v1.3.20` four days before this guide, and covers Termux runtime, ADB reconnect, Shizuku gating, an SSH CA, and outage alerting. The rule means every one of those is re-derived from scratch. It buys publishability (§1) and cleanliness. It costs, conservatively, a year. The guide never states the trade. |
| N4 | **Two live systems, one pair of hands.** | High | High | The incumbent does not stop needing maintenance during the migration, and its maintenance is *not* cheap: coordinated three-repo releases, `ops-vX.Y.Z` tags, published GitHub Releases, `ops-release.json` parity, memory sync, Tier-1/Tier-2 session handoffs. Every hour of that is an hour not spent on tendcf, and it is non-negotiable because it's what keeps the fleet running today. Classic migration arithmetic that this document does not do. |
| N5 | **The critical path runs through three of the author's own other projects.** | High | High | §2 lists "tool forks (optional) — nix2cf, sudo-secretspec, Shizuku" as if they were third-party. They are not. `sudo-secretspec` is the secrets resolver §3 and §14 depend on. `Shizuku` is literally the §13 peer-action worked example. `nix2cf` is Step 3. All three are maintained by the same person, alongside ~9 other repos touched in the same fortnight. tendcf's schedule is the *sum* of four schedules, all serialized through one person. |
| N6 | **Step 6 is a from-scratch TUF implementation, described as "a small subset."** | High | **Fatal** | Offline root, release signing, a snapshot binding the metadata set, an emergency role, per-client high-water marks against replay/freeze/downgrade, in-band root rotation requiring a threshold of *old and new* keys, and a first-run fingerprint ceremony. That is not a subset of TUF; that is TUF, minus delegation. Plus a capability-enforcing executor on three platforms. Real TUF clients took funded teams years and still ship CVEs. §19.8 names a *policy* risk in this area; the *implementation cost* is unnamed. Step 6 is plausibly larger than Steps 0–5 combined. |
| N7 | **Nobody has asked who performs the key ceremony.** | High | High | One operator, an offline root, an emergency role, threshold rotation. Realistically the root key ends up in a password manager on the same Mac that compiles, signs, holds the operator role, and is Step 1's target — at which point the ceremony is theatre and the threat model is decorative. And if it *is* genuinely offline and is lost, every `consented` device is permanently unupdatable with no recovery path in the design. Neither branch is addressed. |
| N8 | **Single point of everything: the workstation that cannot be reimaged.** | High | High | It is the compiler host, the signing host, the operator-tier device, Step 1's target, and the machine the whole project is developed on. §18 notes only that it can't be reimaged (hence dry-run). A macOS major upgrade, a disk failure, or one bad non-dry-run promise costs a week or a month of recovery that a no-deadline solo project never gets back. |
| N9 | **Governance sized for a team, applied to one person.** | High | Med | D27's `Approved-change:` trailer gate on the implementer map (with `bin/check_protected_docs.py` to enforce it), 40 numbered decisions, a decision register, an approval ritual where the approver is the author. This makes *changing your mind* expensive — precisely wrong for a project carrying nine open questions whose resolution requires reversing decisions. Every course correction now costs a ceremony. |
| N10 | **The schemas were finalized before a single real device was transcribed.** | High | High | §18 lists "Transcribe reality" as a Step 0 *remainder* while treating the schemas as built. The order is backwards: the first honest transcription of the Mac will invalidate schema decisions, and by then those decisions have D-numbers and an approval gate (N9). Ordering the contract before the data is the same mistake in a different register. |
| N11 | **There is no test infrastructure for anything past Step 0, and for two of three platforms there cannot easily be one.** | High | High | Twelve negative fixtures is a good discipline for a *validator*. It does not extend to a compiler (needs golden renders), an executor (needs device-level integration tests), or three adapters. macOS CI is buyable. Self-hubbed CFEngine on Termux/Android CI is not. From Step 1 onward, "does it work" becomes a manual check on the one machine that can't be reimaged. |
| N12 | **Step 0 is not as done as the table implies.** | High | Med | The "Remaining" cell lists `peer_actions`, trust-policy shape, generic unit-writers, lookup stub, YAML canonicalize. Trust-policy shape means schematizing §14's five-axis per-device policy — the hardest design in the document — and generic unit-writers means abstracting the launchd-only writer registry across systemd, runit, and Jobber without a single one of those implemented. Two research problems, one table cell, filed under "remaining." |
| N13 | **The publishability tax is paid continuously and collected never.** | Med | High | Namespacing (`alice.caddy`), foreign site-shared inputs, explicit exports, generic adapters, the whole engine/site split — much of the abstraction budget exists for a second adopter. Extracting the publishable layer is Step 10+, "demand-driven," i.e. after everything. A single-site version of this design is meaningfully smaller and is never costed as an alternative. |
| N14 | **The `Site Model in Nix module system` frontend (§3) is a whole second authoring system in a subordinate clause.** | Med | Med | "may later be *authored* in the Nix module system (`mkOption`, `mkIf`, `mkDefault`) and rendered to the same JSON." That is a NixOS-module-system-shaped project. It is correctly deferred, but its presence in the guide keeps it alive as a future obligation and colours schema decisions now. |
| N15 | **CFEngine skill acquisition is unbudgeted and unbuyable.** | Med | High | The incumbent is Ansible. CFEngine Community — self-bootstrapped as its own hub, on macOS and Termux, with hand-written generic bundles, `returnszero` class guards, and Augments — is specialist knowledge with a small living community, a thin macOS deployment corpus, and effectively no Android corpus. There is no colleague to ask. Every unfamiliar failure costs days, not hours. |
| N16 | **Push-vs-pull is deferred to Step 8 but shapes Steps 1–6.** | Low | Med | §5 says push and pull are two modes of one mechanism, and Step 6 is "push-only." Self-hub bootstrap semantics on three platforms are the substrate for both. If the self-hub model has a wrinkle on macOS or Termux, it surfaces at Step 8, after everything is built on the assumption. |
| N17 | **The lookup CLI is treated as a mechanism, not a risk, but §15 concedes nobody has used it.** | Low | Med | "Whether authors actually use the lookup and the error catalog is still untested" is parked *below* the open-questions section, outside the numbered list. It is the mitigation for §10's second objection. A mitigation that is itself untested is an open question. |

### Bucket 3 — UNSAYABLE

These are the ones the author is least likely to write down, because writing any
of them down puts the project's reason to exist in question rather than its
design. §19.9 ("is the whole premise the wrong shape?") looks like it covers
this ground. It does not: it asks whether the *schemas* defend the right wall.
It does not ask whether the wall needs defending, whether anyone is standing
behind it, or what the project is actually producing.

---

**U1. The deliverable is the document, and the document is nearly done.**
*Confidence: High. Severity: Fatal.*

53 of 55 commits are `docs:`. 16,276 lines of prose against 1,024 lines of code
and schema. Nine superseded architecture drafts. Six review documents, three
written today. `DEFINITIVE-v3` — meaning v1 and v2 were also definitive.

The prose loop closes in hours and pays immediately: an AI agent produces a
sharper section, the reasoning genuinely improves, the artifact is genuinely
better, and it feels exactly like progress on tendcf. The code loop closes in
weeks, on a machine that can't be reimaged, in a language with no community,
with no test harness, for no user. These two activities are not competing
fairly and one of them has already won 53–2.

Eighteen months out, the guide is excellent and there is no compiler. The reason
this is unsayable is that the honest version reads: *this is a writing project
wearing an infrastructure project's clothes, and the infrastructure is the
excuse for the writing rather than the other way round.*

---

**U2. The consent surface — the moral center of the design — has a user count
of zero, and the author knows who the fleet belongs to.**
*Confidence: High. Severity: Fatal to the thesis, not to the code.*

§8 is the most distinctive thing in the document: a person reads a proposed
change in ordinary language and refuses it *using their own AI*. It is the part
that makes tendcf a contribution rather than a config-management tool. §1 says
"more than one trusted person can act."

Who? The fleet is one person's Macs, Linux boxes, and Android phones. No second
human is named anywhere in 964 lines. The `consented` trust tier, the advisor
key enrollment, the signed accept/reject, the timeout-deny, the fail-closed
install path, the semantic layer written for a language model to read — all of
it is machinery for a party that does not exist on this fleet, scheduled at
Step 9, after the year of work that has no payoff either.

The unsayable part: **the feature that justifies the project has no user, and
the project is arranged so that this never has to be tested.** Step 9 is late
enough that the question "who is the second person?" never has to be answered
out loud. Naming this means conceding that the paper's contribution is
hypothetical and the system is, in practice, a single-user config manager with
an elaborate ethics surface bolted to its future.

---

**U3. The design optimized for AI authorship selected the engine AI authors know
least.**
*Confidence: High. Severity: High.*

§9 is the intellectual core: most configuration will be written by AI agents,
therefore prefer local knowledge, therefore prefer machine-checkable. The
citations are real (IaC-Eval, the error taxonomy, lost-in-the-middle) and the
reasoning is sound.

And the target is CFEngine. Of every config-management system in existence,
CFEngine has close to the thinnest representation in any model's training data —
orders of magnitude less than Ansible, Terraform, Kubernetes, or Puppet. On
macOS and Termux, near zero. So the project's answer to "AI agents write
plausible-but-wrong infrastructure code" is to point those agents at the
substrate where their priors are weakest and the corpus of correct examples is
smallest, and then to compensate with hand-built schemas and a hand-built lint.

There *is* a defensible answer — the schemas mean agents write Site Model YAML,
not CFEngine policy, and the compiler is the only thing that must speak CFEngine.
But that answer only holds if the compiler exists, and the compiler is Step 3,
and until then every adapter, every generic bundle, and every guard class is
hand-written CFEngine by an author and an agent who are both learning it. The
first two steps of an AI-authorship-optimized plan are the two steps AI is
worst at.

Unsayable because the alternative reading is that CFEngine was chosen first —
for Promise Theory, for the no-control-node property, for its genuine
intellectual appeal — and §9 was constructed afterwards to fit.

---

**U4. The architecture document is exactly the artifact §9 says agents cannot
use.**
*Confidence: High. Severity: High.*

The writing rule: *prefer designs that require only local knowledge over designs
that require global knowledge, because an agent sees the file in front of it,
not the invariants living in twelve other files it never opened.* The citation
is lost-in-the-middle — accuracy drops when the relevant fact sits mid-context.

To implement Step 3 correctly, an agent must simultaneously hold: this 964-line
guide, the 652-line implementer map, 40 numbered decisions, five schemas, twelve
negative fixtures, and §19's nine open questions about which parts are load-
bearing. That is a global-knowledge artifact of exactly the kind §9 identifies
as the failure mode, and it is the project's own build instructions.

The rule was applied rigorously to the Site Model and not once to the
specification of the Site Model. Every review pass made the document more
complete and therefore *less* usable by the authors it is written for. Nine
deprecated drafts from three model families is what that looks like from
outside: each round individually well-argued, cumulatively past the point any
single agent can execute from.

Unsayable because the thesis is self-refuting at the meta level and the document
is the evidence.

---

**U5. The fleet already works, and it will still work in February 2028.**
*Confidence: High. Severity: Fatal.*

`stayturgid` is at `ops-v1.3.20`, shipped four days before this guide was
prepared. 919 commits. 33,067 files. Termux runtime with boot loop and presence,
Ansible deploy, a launchd control node with outage alerting, a Kotlin native
agent, Shizuku gating, an SSH CA, a FIRERPA failsafe channel. It is not a
prototype. It is a released, versioned, coordinated three-repo suite with a
documented deploy discipline.

tendcf's honest value proposition against that incumbent is: *better ideas.*
Promise Theory instead of push. Typed records instead of playbooks. A compiler
instead of templates. Consent instead of trust-by-default. These are better
ideas. They are also, from the fleet's point of view, invisible: at the end of a
successful migration the phones stay up, the VPN stays authenticated, and the
proxy keeps serving — exactly as they do now.

**There is no operational pain driving this.** No outage caused it, no scaling
limit forced it, no second operator asked for it. It is a rewrite motivated by
the architecture being unsatisfying, and rewrites motivated by dissatisfaction
rather than pain have the worst completion rate of any category I have watched,
because the incumbent keeps working — which means the rewrite can always be
resumed later, which means it is always safe to not work on it this week, which
is how it dies.

Unsayable because the sentence is: *the best possible outcome of three years of
work is a fleet that behaves the same as it does today, built on nicer
principles.*

---

**U6. Nine live projects, and tendcf is the one with no due date.**
*Confidence: Med-High. Severity: High.*

61 repos under `~/src`, twelve touched in the last fortnight: `aiuse`,
`sudo-secretspec`, two Homebrew taps, `nix2cf`, `Shizuku`, `superbrain`,
`coderabbit-feeder`, `CodexBar`, `oh-my-pi`, `VESTI`, `OpenCLI`, plus the ops
suite. Several are genuinely on tendcf's critical path (N5), which makes working
on them feel like working on tendcf while producing nothing tendcf can use.

Every one of those projects has a shorter path to a working thing than tendcf's
eleven steps. When attention is the scarce resource and there is no external
deadline, attention goes where the loop closes. tendcf is structurally the
slowest-rewarding item in a portfolio of a dozen.

Unsayable because it is about the person, not the project, and because the
counter-argument ("I'll just prioritize it") is the thing everyone says and
nobody does.

---

**U7. Finishing the paper will feel like finishing the project.**
*Confidence: Med-High. Severity: High.*

There are two deliverables in this repo. One is a fleet under management. The
other is "Draft for review — not published, not submitted," with an
acknowledgements section thanking Desai and thirteen co-authors, a numbered
bibliography, and a `reviews/` directory containing an ICLR-style review.

The paper is finishable. It could be submitted in three months and would be a
real contribution — the Bcfg2 archaeology alone is worth publishing. The system
is not finishable in three years. And crucially, the paper does not require the
system: §16 already labels its outputs "ILLUSTRATIVE, not compiler output" and
"hand-authored to show the target shape," and §18 says "no operational numbers of
any kind." The paper has already been architected to survive without an
implementation.

So the likely 2028 outcome is not failure. It is a published paper about a
system that was never built, and a genuine, defensible feeling that tendcf
succeeded. That is the most dangerous outcome in this document, because it
removes the signal that would otherwise force a correction.

Unsayable because it is the good ending, and calling it a failure mode requires
admitting the two deliverables were in competition the whole time.

---

**U8. The rigor is load-bearing for something other than correctness.**
*Confidence: Med. Severity: Med-High.*

40 numbered decisions. A protected-doc lint requiring an `Approved-change:`
trailer, where the approver is the author. A decision register with a "silence =
proceed" clause, addressed to nobody. `DEFINITIVE-v3`. Twelve negative fixtures
before one positive integration test. A vetted guide that formally "wins" over
other living documents.

Some of this is real discipline and pays for itself. But the volume is
disproportionate to a five-day-old project with zero deployed code, and its
observable function is to make a solo project feel like an institution — to
supply the external accountability that a project with no team and no deadline
otherwise lacks. It works, in the sense that it produces the *feeling* of
answering to someone. It does not produce the thing that feeling is a proxy for,
which is someone who notices when you stop.

Unsayable because the process is the part that is working, and questioning it
means questioning the substitute for the missing team rather than the design.

---

## 3. How much work is this, really, for one person?

### 3.1 Honest sizing

Assuming evenings and weekends, competent AI assistance throughout, and the
~12-project portfolio continuing to exist. "Calendar" assumes the realistic
share of attention, not full-time.

| Step | What | Doc's framing | My estimate | Verdict |
| --- | --- | --- | --- | --- |
| 0 | Finish schemas | "Existing contract," 5 remainders | **1–3 months** | Underestimated. Trust-policy shape and generic unit-writers are design problems, not chores (N12). |
| 1 | macOS services adapter | One row | **3–5 months** | **Badly underestimated.** Includes learning CFEngine, installing and self-hubbing it on macOS, writing the generic bundle *and* the launchd renderer, and colliding with ~90 pre-existing launchd jobs. Output is a diff nobody applies (N2). |
| 2 | Android under the Site Model | One row | **4–10 months, or never** | **Worst estimate in the document.** May be a CFEngine port to Termux/bionic, or a native-helper-in-APK Android project. Unbounded risk, sitting upstream of everything (N1). |
| 3 | `nix2cf` compiler | One row | **4–8 months** | **Badly underestimated.** Merge + conflict check with resolution-carrying errors + extra-entry reporting + inference with origin tracking + render + golden tests. 5–15k lines. The repo currently contains three files. |
| 4 | Linux reference path | One row | **3–6 weeks** | Fairly estimated. Cheapest step in the plan. Also the only one where CFEngine is on native ground. |
| 5 | First real Linux host | One row | **1–2 months** | Slightly underestimated — this is the first cold-boot-from-factory-reset test in the entire plan (A11), and the cold path is conceded untested. First step with real value. |
| 6 | Signed releases + ChangePlan executor | One row | **6–14 months** | **Badly underestimated.** A TUF implementation plus a capability-enforcing executor on three platforms, security-critical, with no reviewer (N6, N7). |
| 7 | nix-darwin substrate | "optional" | — | Correctly optional. |
| 8 | Pull | One row | **1–3 months** | Roughly fair, but gated on 6. |
| 9 | Consent / sovereignty | One row | **3–6 months** | Underestimated (advisor enrollment, signed nonce-bound returns, fail-closed semantics, semantic-layer generator). Also possibly zero users (U2). |
| 10+ | Demand-driven | — | Unbounded | — |

**Total to Step 9: roughly 2.5 to 5 years of sustained part-time work, with wide
variance concentrated in Steps 2 and 6.**

Sanity check on that number: the incumbent is 919 commits and 33k files and
covers *strictly less* scope — Android only, no compiler, no signing path, no
consent surface, no cross-platform supervisor abstraction. tendcf starts from
zero, forbids itself from copying the incumbent (N3), and must keep the
incumbent running throughout (N4). "Several years" is if anything generous.

The three steps that consume more than half the total — 2, 3, and 6 — each
occupy exactly one table row and one sentence of Notes. The document's build
order is not a schedule and does not claim to be one; the implementer map says
so explicitly. But it *reads* as eleven comparable increments, and it is the
only sequencing artifact the project has.

### 3.2 The cuts

Three cuts, plus one demotion. I have deliberately chosen central things,
because the peripheral cuts don't move the number.

---

**CUT 1 — The TUF-subset signing path and the capability-enforcing executor
(Step 6). Largest single saving: 6–14 months.**

Replace with: a plain signed tag or `minisign`/`ssh-keygen -Y sign` over the
release tarball, verified once at fetch time, and **no on-device capability
enforcement**. Keep the ChangePlan as a *readable artifact* — it is the Step 3
"what would device X receive" render, which you are building anyway and which is
the highest-value item in the whole plan. Drop the runtime enforcement, the
nonces, the high-water marks, the emergency role, the offline root, and the
rotation ceremony.

Why this is defensible rather than reckless: the executor's enforcement value
exists only under a multi-party threat model. On a single-operator fleet,
whoever can sign a release can also just edit the Site Model — the capability
allowlist is defending against an author who is the same person as the
authorizer. §19.8 already predicts the escape hatch appears and the mechanism
becomes decorative. **Cut it while that is a design decision instead of
discovering it as a compromise.** Restore it when a second operator or a second
site actually exists, which is also when the threat model becomes real.

What is lost: the strongest security story in the paper. Keep the design
*written* in §7 — clearly marked as designed-and-unimplemented, which §18 already
does honestly for everything else.

---

**CUT 2 — The consent surface and advisor slot (§8, Step 9). Saving: 3–6 months,
plus a much larger second-order saving.**

Keep the *slot*: a documented `accept | reject` field in the plan format with
nothing behind it, and a written spec. Cut the advisor key enrollment, the
shipped default prompt, the signed return path, the timeout-deny and
fail-closed-for-installs logic, and the semantic-layer generator.

This is the cut I expect to be most resisted, because §8 is what makes tendcf a
contribution rather than a tool. That is exactly why it should go: **it is the
most expensive feature in the plan and the one with zero identified users on
this fleet (U2).** Building it for a hypothetical second person, at Step 9,
after a year with no payoff, is how the project runs out of energy before the
feature ever meets one.

The second-order saving is larger than the first: cutting §8 breaks the paper's
grip on the build order. Right now the build order is partly serving a
publication, and publications reward completeness of the *design*, not existence
of the *system* (U7).

---

**CUT 3 — Dependency inference. Keep the fields, cut the engine. Saving: 1–3
months of Step 3, and most of Step 3's risk.**

Keep `provides` / `requires` as schema fields and keep auto-provide — they are
cheap, they document intent, and they feed the lookup CLI. Cut the edge
derivation, the origin-tracking metadata, the authored-vs-inferred reconciliation
and coincidence reporting, and the "inference waits for types on two platforms"
gate that couples Step 3 to Step 2.

The document has already done the work of justifying this cut and then declined
to make it. §10 concedes retry-until-stable is the substrate, that it may
*already be* the local-knowledge answer, that `provides`/`requires` may only
relocate the global knowledge, and that spurious edges may be underpriced.
§19.1 asks outright whether inference is justified. §19.7 says nobody has run
the origin mechanism. §17's second ceiling says inference only pays where roles
are largely independent — and §10 then reports that the roles examined so far
"declare no role-to-role dependencies and run as independent plays."

That is four independent concessions pointing the same direction. Inference is
the project's claimed novel contribution, which is precisely why it should not
be on the critical path to a working system. Build it after something runs, when
you can measure whether retry-until-stable was insufficient.

---

**DEMOTION — Move Android from Step 2 to after the Linux path. Not a saving; a
de-risking, and the highest-leverage change in the list.**

Revised order: **0 → schemas · 1 → the `buildfile` render ("what would device X
receive") · 2 → Linux reference path · 3 → first real Linux host · 4 → macOS
adapter · 5+ → Android, reconsidered.**

Four reasons:

1. Android is where CFEngine is least likely to run at all (N1), and it
   currently sits *upstream* of the compiler, so its failure mode is total.
2. Android is where the incumbent is *strongest* — 919 commits of Termux,
   Shizuku, ADB, and SSH CA work, in production. Re-deriving your best existing
   capability first, from scratch, under a rule forbidding you to copy it (N3),
   is the worst possible ordering for morale and for value.
3. Linux is where CFEngine is native, where there is no incumbent to beat, where
   a machine can be reimaged freely, and where a cold-boot-from-factory-reset
   test — the untested path §10 concedes (A11) — is actually cheap to run.
4. It moves the first genuinely valuable outcome from month ~14 to month ~4.
   That single change does more for this project's survival than any technical
   decision in the document.

The `buildfile` render moving to Step 1 matters independently: it is the
cheapest item in the plan, it is how everything else becomes checkable, it is
useful before any adapter exists, and §4 already calls it "almost free" and
"planned as the first piece of the compiler." It is currently buried inside
Step 3, behind Android.

---

### 3.3 What the cuts leave

A single-site, single-operator config compiler that renders a typed Site Model
into CFEngine Augments, targets Linux first and macOS second, ships releases as
signed tarballs, reports honestly on what it manages and what it doesn't, and
has a written-but-unbuilt design for consent and capability enforcement that
can be implemented when a second party exists.

That is **9–18 months of part-time work** rather than 2.5–5 years, it produces a
converged real host inside the first four months, and every cut item is
recoverable — the design survives in the document, which, as U1 notes, is the
one thing this project has never had trouble producing.

Whether that is still a paper is a separate question, and one worth asking
deliberately rather than letting the build order answer by attrition.
