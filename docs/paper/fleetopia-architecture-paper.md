# fleetopia: A Configuration Management Architecture for AI-Authored Configuration

**Draft for review — not published, not submitted.**
Prepared 2026-08-13 for Narayan Desai. Sections are numbered so comments can
cite them.

---

## Abstract

We describe the architecture of `fleetopia`, a configuration management
system for a small, heterogeneous personal fleet — Apple Silicon macOS,
Linux on x86_64 and aarch64, and Android devices running Termux — built on
an explicit premise: **most of this system's configuration will be written
by AI agents rather than by hand.** We treat that premise as a first-order
design constraint and derive a decision rule from it: prefer designs whose
correctness follows from information *local* to the file being edited over
designs that require *global* knowledge of what everyone else declared.
Applying that rule inverted two decisions we had already argued the other
way, and both inversions are the substance of this paper.

The architecture is a data spine (the Site Model), a pure compiler from that
spine to CFEngine's native JSON augments layer, per-device SQLite as the
authoritative record of what happened, and a signed release carrying a typed
operation plan that the on-device executor mechanically refuses to exceed.
Bcfg2 supplies four of its load-bearing ideas, credited in §6.

**Nothing described here is deployed.** No device has been provisioned from
factory reset by this automation; we have no operational numbers of any
kind, and one of our central negative results (§5.4) rests on reasoning
about a code path that has never been executed. The paper's purpose is to
expose the design to an expert reader who is likely to find the holes,
not to argue that it is right. §8 is a list of the places we think it is
weakest.

---

## 1. Motivation

The site is a personal fleet, not a data center: one Apple Silicon laptop
that is also the operator's daily driver, Linux hosts on two architectures,
and a set of Android devices managed through Termux, a forked Shizuku, and a
local agent. Three people hold root on the shared portion of it. There is no
deadline, no paying user, and no operational SLA. The project's stated goals
are to extend software freedom to configuration glue — the generic layer is
published, and a person should be able to clone it, supply their own facts,
and run it — and to give the eventual users of managed devices the ability
to *understand and refuse* a proposed change to their own computer.

That framing produces the usual requirements (portability, no permanent
control node, a signed update path) and one unusual one.

**The unusual requirement is who writes the configuration.** In this project
the answer is: AI agents, as the primary authorship model, with human
authorship as the exception rather than the rule. This is not a prediction
about the industry; it is a description of how this specific site is already
being operated. The consequence we care about is that the *cost structure of
a configuration language changes* when its principal author is a machine
with a bounded context window, and several design decisions that are settled
under human authorship become live again.

We state that as a requirement (R13 in the source document) with an
operational decision rule, and §4 is that rule.

The rest of the paper: §2 describes the architecture in enough detail to
argue about; §3 the design rule; §4 the two decisions it inverted; §5 where
we depart from Bcfg2 and why; §6 what we took from it; §7 an honest account
of validation status, which is thin; §8 the open questions we would most
like attacked.

---

## 2. Architecture

### 2.1 The Site Model: facts as data, one home

Every fact about the site — host inventory and taxonomy, port and path
allocation, service definitions, role assignments, trust tiers, signing key
identifiers — lives in a set of schema-validated JSON/YAML files called the
Site Model. Behavior lives in generic code that holds no facts and is
therefore publishable. Adapters translate between them.

The Site Model is deliberately not a tool's configuration format. Every
config tool in the system — CFEngine, the toolchain bootstrapper, Nix for
builds — is a *consumer* of that data and is individually replaceable. This
is the mechanism by which the same generic code runs on somebody else's
machines: they supply their own Site Model through the same schema.

Three record types matter for what follows. `services.yml` holds one record
per service (name, run-as user, argv command, environment as secret *names*
only, platform notes, role binding, owning writer); every launchd plist and
systemd unit in the fleet is a rendering of one such record. `roles.yml`
maps a feature role to `{main, backups[], peers[]}` — this is how "the
control node" is dissolved into data, since any host may hold any role.
`launchd-writers.yml` declares exactly one writer per launchd label prefix,
which kills a two-writers-on-one-plist hazard at the source.

The Site Model *may* be authored in the Nix module system — `mkOption`,
`types.*`, `mkIf`/`mkDefault`/`mkMerge` — and rendered to the same JSON
everything else consumes. That is an authoring frontend only; the rendered
JSON is what is schema-validated, signed, and read downstream, and a person
adopting the project is never required to know Nix in order to read or fork
their own site data. We use the Nix *language* here and not the Nix *build
system*: a service that should be running or a Termux package that should be
present is typed data, and nothing about it needs to become a derivation.
(The corresponding discipline is to avoid the nixpkgs option types that
assume a buildable output for concerns realized by CFEngine or by a package
manager that has no derivation at all.)

### 2.2 The compiler: a pure function into CFEngine's own data layer

A compiler (working name `nix2cf`) reads the Site Model and renders CFEngine
augments — `def.json` / `host_specific.json` — which CFEngine has accepted
as a native JSON data-injection layer since 3.7. The standard Masterfiles
Policy Framework is already substantially data-driven on top of that layer,
so for the common case the compiler emits *data*, not promise text: a
generic bundle written once handles "this package is present and pinned,
these directories exist, this service is loaded" for any entry in the data.
Only promise types the stock library does not cover need actual policy text,
and that is templated from typed option values rather than synthesized.

Merging of the site → role → host layers happens once, in the compiler,
before render. We do not additionally use CFEngine's own `mergedata()` for
this, on the same grounds we do not hand-maintain two type systems: one
merge engine, one source of truth.

The pipeline has four stages: merge, conflict check, dependency inference,
render. The conflict check is deliberately a *separate stage over
already-merged declarations* rather than logic fused into the type
definitions, so that adopting the Nix module system's priority algebra
(`mkDefault`/`mkForce`/`mkOverride`) later is a policy change at one stage
and not a schema redesign.

Because the render is a pure function of the Site Model, "show me exactly
what device X would receive, without touching device X" is nearly free. We
plan to build that affordance *first*, before the pipeline is finished, and
§6.2 explains why it earns its place three separate times over.

### 2.3 Deployment shape: no policy server, no push requirement

Every host runs its own `cf-serverd` and reads policy synced via git as part
of the ordinary signed-release mechanism. There is no dedicated central
policy host, no SSH dependency, and no push requirement. Push exists — an
operator host holding a deploy role can trigger an immediate convergence run
on a target rather than waiting for its next cycle — but it is one mode of
the same mechanism rather than a separate system.

This shape was scoped out of an earlier revision of the design on the belief
that CFEngine required dedicated policy-server infrastructure and an SSH
push model. Both beliefs were wrong, and had entered the design as an
analyst's unvalidated assumptions rather than as checked constraints. We
record that because it changed the answer: once the practical objections
dissolved, CFEngine was the better fit on its own terms, not an acceptable
substitute for what we had been using.

### 2.4 The record of truth is local

Each device owns a SQLite database, populated from CFEngine's local
promise-outcome log, and *that* is the authoritative record of what
converged. Any central or shared view is optional and eventually consistent.

The grounds are narrower than the local-first literature's, and worth
stating precisely because one of them is an operational fact about this
fleet rather than a principle. On CFEngine Community the local capture has
to be built regardless, so local-as-record is the null option and
central-as-record is a second system that must be kept complete and in sync.
Devices in this fleet demonstrably go unreachable — flaky ADB over wireless,
Android boot-recovery failures, offline peers — so any central copy fed by
best-effort sync is incomplete during exactly the windows one would want it.
And one SQLite file with one owning host has no concurrent-writer failure
mode, which is the same single-writer-per-node discipline we apply to Nix's
own store.

We keep the outcome vocabulary of `ncf` — Rudder's library of parameterized
CFEngine generic methods, which we vendor as a reference corpus rather than
depend on — verbatim: `success`/`repaired`/`error`/`n-a` in enforce mode,
`compliant`/`noncompliant`/`error`/`n-a` in audit mode. It is a well-tested
structured vocabulary and only the sink is changing.

### 2.5 Releases carry a typed plan the executor may not exceed

Configuration reaches devices only as a versioned, signed release. Each
release additionally publishes a per-host **typed ChangePlan**: a list of
operations, each declaring a `capability` drawn from a closed vocabulary,
the exact `resources` it may touch (checked against the port and path
registries), a `target` bound to the host's public key, plus rollback,
expiry, and nonce. The on-device executor maps declared capabilities to an
allowlist and **mechanically refuses any effect outside the declared set**.

The distinction we are drawing is between "apply this bundle because its
hash is signed" and "apply only these operations, on these resources,
because the plan says so." The first authenticates the author; only the
second constrains the effect. Signing is a TUF subset sized for one
operator: an offline 2-of-3 root, an offline targets role, snapshot to bind
the metadata set, an emergency revocation role, and a durable per-client
high-water mark so that replay, freeze, and downgrade are closed. Delegations,
mirrors, and online snapshot are left out.

Layered on the verifiable plan is a *semantic* layer — generated, cached,
and written for a language model to read: "this bumps a TLS library across a
CVE and restarts the public proxy." The semantic layer briefs a user and
their advisor agent; it never authorizes. Only the verifiable layer,
checked by the executor, authorizes. That separation is what lets the
eventual user-sovereignty feature — a person's own AI explaining a proposed
change in plain language, and maintaining their divergence from upstream if
they refuse it — sit on top of the trust layer without becoming part of it.

---

## 3. The design rule

The requirement is that most configuration here is machine-authored. The
rule we derive from it is:

> **Prefer designs that require only local knowledge over designs that
> require global knowledge.** A design whose correctness follows from
> information present at the point of authorship is one an agent can satisfy
> reliably. A design whose correctness depends on the author already knowing
> what everyone else declared is one an agent will violate *confidently and
> plausibly* — which is worse than violating it obviously.

And a second rule that is really a corollary: **prefer machine-checkable to
conventional.** A convention an agent must remember is a convention it will
eventually break silently; a schema, a type, or a compile-time check catches
it and reports it in a form the next agent can act on. In practice this
means that when we catch ourselves writing "remember to…" in a comment, that
text belongs in a schema instead.

The first rule is the interesting one because **it cuts against the
human-authorship intuition.** For a human maintainer, "just write down the
constraint you know about" is cheap and explicit — it is good practice. For
an agent working from a bounded context, the same instruction is precisely
the expensive thing, because the agent's problem is not willingness to write
the constraint but knowledge that the constraint exists. An error message
matters more for the same reason: its reader is now usually an agent that
cannot go exploring for the missing half, so a message that says only
"conflict" pushes the work onto whoever runs the build. We require that a
conflict error carry the resource identity, every writer that declared it
with source location, the conflicting values, and a statement of what a
resolution would look like.

We are aware this rule can be used to justify almost anything, and §8.2 asks
directly whether it is an argument or a hypothesis.

---

## 4. Two decisions the rule inverted

### 4.1 Dependency inference, which we had argued against

The ordering question decomposes into three levels: convergence fixpoint
alone; fixpoint plus explicit `depends_on` where a real constraint exists;
or an inference stage that derives ordering edges from what each declaration
*provides* and *consumes*. Under human authorship we had concluded the
middle option: explicit edges, written by the person who knows the
constraint, with the fixpoint underneath.

The rule inverts that. Explicit `depends_on` is a global-knowledge
mechanism — to write the edge, the author must already know that someone
else's resource exists and must run first. `provides`/`requires` is a
local-knowledge mechanism: each type states only what it supplies and what
it needs, answerable from inside one file by an agent that has never seen
the rest of the system. So the compiler additionally *derives* edges;
fixpoint remains the substrate and explicit `depends_on` remains available
and authoritative.

We have one piece of confirming evidence and it is not hypothetical. The
site's existing Android deploy chain hand-orders app installation *after*
privilege hardening, so an app added to the install list goes unhardened for
a full deploy cycle. The list contradicts its own stated install-before-harden
rule, humans wrote it, and humans did not catch it. That is what accreted
global-knowledge ordering looks like.

Three constraints on the build follow from the second rule rather than from
taste. Types first, inference second, and inference does not start until real
type definitions exist on **two** platforms — rules invented ahead of the
types they range over encode guesses. **Edge attribution is mandatory:**
every edge in the compiled output carries its provenance, authored (with
source location) or inferred (with the rule that produced it). And where an
authored and an inferred edge cover the same pair, the authored one wins and
the coincidence is *reported*, not silently collapsed.

Attribution is not a debugging nicety, and the reason is asymmetric. The
failure mode inference introduces is a **spurious** edge, which presents as
"why is this waiting?" — strictly harder to diagnose than a missing edge's
"why did this fail?", because nothing failed. Provenance in the explain
output is what turns that from an investigation into a query.

§5.1 is the argument that we should not be doing this at all.

### 4.2 Comprehensiveness, flipped from opt-in to default-on

Bcfg2's configuration goals are comprehensive by convention: the
specification describes every configuration entity on the client, so
anything present on the client and absent from the specification is
unintended by definition, and the client verifies in *both* directions —
no less than specified, and no more. Unspecified state surfaces as an
**extra entry**, a first-class reported category [1, §2.2].

We adopt this per *domain* rather than per client — the app list on a
device, `/etc/ssh`, the launchd services under a given prefix — because
adopting it fleet-wide on day one is not survivable in an environment that
was never built under it.

Our first decision was opt-in per domain. The rule flipped it to
**default-on with an explicit, reasoned opt-out**, because AI-authored drift
is exactly what extra-entry detection catches, so the safe default belongs on
the detecting side. A bare opt-out boolean would let an agent widen the
unmanaged surface silently; requiring a reason string makes every gap in
coverage a visible, greppable, reviewable decision rather than an absence.

The reason is drawn from a closed set of two, and keeping them distinct is
what makes default-on survivable:

- **`not-yet-migrated`** — real device state nobody has described yet. This
  is the normal day-one condition for everything, it is a *backlog item*, and
  it is countable.
- **`deliberately-unmanaged`** — state that is genuinely not ours to
  describe: user data, another tool's territory, device-generated caches.
  Permanent, and should be rare.

Without the split, default-on either buries the operator in day-one noise or
pushes everyone to opt out broadly and never come back — which is the
failure mode that makes comprehensiveness worthless in practice. With it,
the managed/unmanaged ratio per device is a real progress metric and the
`not-yet-migrated` count *is* the remaining work. We took that framing
directly from the booklet's first client run reporting `Total managed
entries: 0 / Unmanaged entries: 2308` [4]; the whole deployment story there
is grinding the second number down, and we expect our own first
transcription pass to look the same.

The schema records the counters separately, per domain, alongside the
release stamp (§6.3). Conflating backlog with permanent exclusion is what
makes the number stop meaning anything.

---

## 5. Where this departs from Bcfg2

### 5.1 We build dependency inference; Bcfg2 deliberately built no dependency graph

This is the sharpest disagreement in the paper and we would rather state it
at full strength than defend it.

Bcfg2's answer to ordering is to not have one. The client's apply loop
repeats while the number of pending operations decreases; bundles are the
collective re-verification scope; there is no dependency graph to resolve
and no ordering to get wrong. That is a *deliberate* design position, it is
simpler than what we are proposing, and it has two decades of production
behind it. We are adding machinery its author chose not to build.

Our entire justification is §3's rule: inference converts ordering from
something an author must know globally into something each type states
locally, and machine authors are specifically bad at the former. That is the
whole argument. It is an argument about *who writes the configuration*, not
about the semantics of convergence, and if the rule is wrong the machinery is
unjustified.

Three ways we can see it being wrong, offered rather than rebutted:

1. **The fixpoint may already be the local-knowledge answer.** Retry-until-
   stable requires no author to know anything about ordering at all — which
   is *more* local than `provides`/`requires`, not less. If that is right,
   we have argued ourselves into building a graph in order to achieve a
   property the thing underneath it already had.
2. **`provides`/`requires` may only relocate the global knowledge.** Naming
   a capability token that another type must name identically is a shared
   vocabulary; agreeing on a vocabulary across files is a coordination
   problem wearing local clothing. Our mitigation is a closed enumeration of
   token kinds, so a typo is a schema error rather than a silently
   unmatched edge — but the *token values* remain a namespace two authors
   must agree on.
3. **Spurious edges may be worse than we have priced in.** We claim
   provenance makes them a query. That claim is untested, and the failure
   mode is silent by construction: a spurious edge does not fail anything,
   it just makes something wait.

### 5.2 Render ahead of time into a release artifact, not on demand per client

The compile/apply split is Bcfg2's, and the reason we take it is Bcfg2's:
central processing keeps the complicated parts where they can be examined and
supervised, and the client does as little as possible — compare, decide, act,
report.

What we change is *when*. Bcfg2's server renders a client's goal on request;
our render happens ahead of time, into a signed release artifact, and the
client never needs a reachable server to obtain its goals at all. The split
transfers; the client/server topology does not. This follows from the fleet
being routinely unreachable and from wanting device-local autonomy, and it is
what makes the same mechanism serve both an operator push and a consented
pull.

The cost is that we lose the thing render-on-demand gives for free: the
server *knows*, at bind time, which clients exist and what each one asked
for. We are betting that the release stamp plus per-device local reporting
recovers enough of that. We are not certain it does.

### 5.3 Local-first record, where the papers centralized statistics

Bcfg2 uploads client statistics to the server, which is what makes nightly
network-wide reports possible and, per LISA '05, what actually bought
administrator trust. We invert the direction: the device's SQLite is
authoritative and any central view is an optional, best-effort push.

We are aware this is the decision most likely to be wrong. The grounds are in
§2.4, and the honest summary is that we currently have *no consumer* for a
central copy — the telemetry spine that would have consumed it was dropped
and there is no compliance UI requirement — so central-as-record would be
infrastructure without a customer. But "no consumer yet" is exactly the
reasoning that LISA '05 argues against elsewhere, which is why §6.4 records
the same paper telling us to build reporting *early*. We may be applying one
of its findings and ignoring another.

### 5.4 A negative result we have not earned

We evaluated compiling to a Puppet-style catalog — resolve into one
deterministic, provably ordered plan — for the subset of operations with
genuine sequencing constraints, and **rejected it.** The audit: all fourteen
service-owning roles across the site declare zero role dependencies and are
invoked as independent single-role plays; the one Android chain that looked
like a real dependency graph turned out to have every apparent intra-chain
prerequisite satisfied by an *earlier stage* rather than by an earlier role,
and five of its six steps share no execution context with each other at all.
Re-derived semantically, the real constraints sort into a strictly
sequential six-node transport bootstrap (which is a `bundlesequence`,
hand-authored), short independent per-app chains, and safety interlocks
(§6.1) that are not dependencies at all. Catalog compilation earns its keep
when chains interleave into a genuine DAG, and these do not.

**The methodological hole is large and we want it named.** Reading the
existing automation answers "what works on already-provisioned devices," not
"what a cold device requires." Convergent automation leaves no trace of a
constraint that fails on run 1 and succeeds on run 2 — and **no device in
this fleet has ever been provisioned from factory reset by this
automation.** The rejection therefore rests on reasoning about a cold path
that has never been executed. The three gaps we did find, we found by
reasoning rather than by running it, which is strong evidence the list is
incomplete.

---

## 6. What we took from Bcfg2, and where

### 6.1 Actions as the shape of an interlock

One class of constraint in this fleet is not a dependency: setting an
always-on VPN lockdown on a device whose VPN is *unauthenticated* severs
every management path to that device permanently. Nothing in the existing
codebase authenticates the VPN first; only a safe default and a comment
prevent it today. We had characterized this as inexpressible in a catalog,
which is true, and had left it there.

Bcfg2 Actions are the shipped precedent for exactly this shape: a command
bound to a bundle with timing, a `when` condition, and a status policy, where
— the load-bearing sentence [4, §A.2.1] — *unless exit status is ignored, a
failing pre-action prevents modification of entries in the enclosing bundle.*

That is a guard with a defined blast radius: not an edge in a graph, and not
a bare `if`. We make it a first-class Site Model field that compiles to a
CFEngine guard class plus a bundle-scoped refusal, which turns "the VPN must
be authenticated before lockdown may be enforced" from a safe default plus a
comment into a stated precondition. The bundle is simultaneously the
grouping unit and the re-verification scope, also following Bcfg2 [4, §2.2.1].

Because the blast radius and the reporting are the whole point, the schema
encodes them as required constants rather than author-settable fields — an
author who could narrow either one could reintroduce the bug the mechanism
exists to close.

### 6.2 `buildfile`, which turned out to earn its place three times

`bcfg2-info buildfile` renders exactly the artifact a named client would
receive, server-side, without touching the client; the `buildall` variant
diffs every client's output across server upgrades. For a pure compiler this
is nearly free, and we plan it first because three separate justifications
converge on it:

- It is the **agent self-check loop.** An agent that can ask "what does my
  change actually do to device X" verifies its own work locally instead of
  deploying to find out — the cheapest available form of catching mistakes
  automatically rather than by review.
- It is the **compiler's own regression test.** A compiler change that alters
  output for a device nobody touched is precisely the bug class this catches,
  and it needs no fleet to run against.
- It is **decision transparency**, which LISA '05 identifies as what actually
  buys administrator trust — directly applicable to a site with three
  root-holding admins.

### 6.3 Revision stamping

LISA '06's change is small and mechanical: stamp every generated client
configuration with the repository revision, keep a log of what was served
when, and carry that revision into every statistics upload. We already have
the identifier — the coordinated release tag and its manifest — so this is
one column in the row schema, not an integration. Every row records the
release that produced it and each device records which release it is
currently converged to.

What it buys, per the paper: the desired state of any device at any past time
becomes reconstructible; "did this break after the last release" becomes a
query rather than an argument; and "which hosts were exposed, over what
window, and when were they actually patched" becomes answerable. Given a
fleet whose devices are routinely unreachable, the reconstructibility is
worth more to us than it was in the paper's always-on cluster.

### 6.4 Deploy reporting early, and dry-run as the default posture

LISA '05's central finding is not technical: deployment took about four
months of one person's time, and the binding constraint throughout was
administrator *trust*, not tool correctness — with the stated pivot being
that client-side functionality was not sufficient, and that nearly all
subsequent development went into information presentation.

Two operational practices follow, and we adopt both. Their production servers
ran in dry-run nightly and mailed the resulting state to the responsible
administrator, with auto-apply reserved for workstations; we make dry-run
the standing posture for the first platform we bring under management, which
happens to be the operator's own laptop — the one machine that cannot easily
be reimaged. And "deploy reporting early, not last" reframes our local SQLite
plus a trivial "what changed, what is dirty, what am I converged to" view as
an **adoption requirement rather than an observability nicety**, which is the
argument against sequencing it last on the grounds that nothing consumes it
yet.

### 6.5 What did not transfer

XML as the configuration language and the plugin taxonomy built around it;
the client/server render-on-demand topology (§5.2); and LISA '06's FSM change
orchestration over repository revisions. The last one is the interesting
rejection: expressing cross-machine sequencing as a state machine over
*releases* rather than as edges in a per-host catalog fits our release train
unusually well, but the paper is honest that administrators must enumerate
all contingencies as discrete states, that time in any state is unbounded,
and that one down client can stall a workflow. For a fleet whose devices are
routinely unreachable, that last property is disqualifying as a default. We
have it filed as the shape to reach for *if* a real cross-device sequencing
need appears, and we are not building it on spec.

One piece we expect to want verbatim is `altsrc` — binding an entry as if it
had a different name, so that two paths share one source. Termux's
`$PREFIX`-relative layout against Linux and macOS absolutes is the same
problem `/etc/hosts` versus `/etc/inet/hosts` was.

---

## 7. Status and validation

**Implemented:** the Site Model schemas, including the fields §4 argues for
(`provides`/`requires` per type, `interlocks` per bundle, `comprehensive`
plus `opt_out_reason` per domain) and the report-row schema of §6.3. A lint
carries the cross-file rules JSON Schema cannot state alone — reference
resolution, launchd labels checked against the declared writer prefixes, no
prefix nested inside another.

**Validated only in the following narrow sense.** A lint that passes on
correct input demonstrates nothing about whether it catches incorrect input,
so the schemas were tested against twelve deliberately broken fixtures — an
opt-out with no reason, the contradictory comprehensive-plus-reason
combination, a rogue launchd label, a nested writer prefix, a literal secret
where a key name belongs, a typo'd capability token kind, an enforce-mode row
carrying an audit-mode outcome, a coverage row missing its counter — and each
is caught. Two of the twelve exposed error messages that were useless
(`is not valid under any of the given schemas`, with no field pointer), which
is the failure §3 rules out for the compiler and had not been applied to the
compiler's own tooling; the lint now discriminates on row type first.

**Not implemented, and this is most of it:** the compiler, all three platform
adapters, the signed release path, the ChangePlan executor, the consent
surface. **Nothing is deployed.** No device has been provisioned from factory
reset by this automation. We have no deployment time, no effort figure, no
managed/unmanaged ratio, and no failure data.

That gap is not incidental to how this paper should be read. The Bcfg2 papers
report deployment experience with numbers — four months, one person, roughly
three FTE of maintenance before and between a third and a half of an FTE
after, across a division of about two hundred people. We have the design and
the schemas and none of the evidence. Every claim here about what will be
cheaper or more reliable under machine authorship is, at this point, an
argument.

---

## 8. Open questions

These are the places we think the design is weakest, listed so a reader can
go at them directly rather than around them.

**8.1 Is inference justified, or are we rebuilding what Bcfg2 deliberately
declined?** §5.1 states our case and three ways it fails. The version of
this question we most want answered: is the convergence fixpoint *already*
the local-knowledge mechanism, making `provides`/`requires` a strictly worse
answer to a problem that was already solved?

**8.2 Is the machine-authorship cost inversion an argument or a hypothesis?**
We have one confirming instance (§4.1's hand-ordered chain contradicting its
own rule) and no counter-instances, which is a suspiciously good record for a
rule this load-bearing. What would a counter-instance even look like — a
place where forcing an author to state a global constraint is what *caught* a
bug?

**8.3 Do `not-yet-migrated` counts actually get ground down, or accumulate?**
The Bcfg2 deployment ground 2308 unmanaged entries down over months with a
person whose job that was. Ours is a personal fleet with no such person. If
the count only ever rises, the metric is decoration and default-on
comprehensiveness is a permanent tax with no payoff.

**8.4 Is per-domain the right granularity for comprehensiveness?** Bcfg2's is
per-client and by convention. We chose per-domain to make partial adoption
survivable, but a domain is a boundary someone has to draw, and a badly drawn
one hides drift inside itself just as effectively as opting out would.

**8.5 Is local-first the wrong call?** §5.3. We have no consumer for a
central copy today, but "no consumer yet" is precisely the reasoning LISA '05
warns against, and we are taking one of its findings while declining another.

**8.6 Does spurious-edge provenance actually work?** We claim attribution
turns "why is this waiting?" into a query. Nobody has run it. If it does not
work, inference has a silent failure mode and §5.1's argument gets much
worse.

**8.7 Does the ChangePlan's capability vocabulary survive contact with real
operations?** A closed vocabulary that the executor enforces is only as good
as its coverage; the pressure will be to add an escape-hatch capability, and
the moment one exists the mechanism is decorative.

**8.8 Is the whole premise the wrong shape?** The design optimizes for
machine authors on the assumption that they are the primary authors and that
their weakness is bounded context. If the real weakness turns out to be
something else — plausible-looking output that type systems do not catch,
say — then we have hardened the wrong surface, and the schemas are a
Maginot line.

---

## 9. Conclusion

We have described a configuration management architecture whose one genuinely
novel commitment is treating machine authorship as a first-order design
constraint, and deriving from it a rule — prefer local knowledge to global —
that inverted two decisions we had already settled. The rest is composition:
a data spine, a pure compiler into CFEngine's own data layer, per-device
local records, and a signed plan the executor may not exceed, with four of
its load-bearing ideas taken from Bcfg2 and credited above.

We think §4's rule is right and §5.1's departure is the honest cost of it.
We would rather be told otherwise now, while the schemas are two days old and
nothing is deployed, than after a fleet is running on it.

---

## Acknowledgements

*(To be written. At minimum: Narayan Desai, for review; and the Bcfg2
authors, whose four papers are the source of §6 in its entirety.)*

## References

> **Bibliography needs a verification pass before this leaves the building.**
> Titles, authors, venues, and years below were written from working notes and
> memory, not from the PDFs' own reference pages; several should be checked
> against the originals.

[1] N. Desai, A. Lusk, R. Bradshaw, and R. Evard. *BCFG: A Configuration
Management Tool for Heterogeneous Environments.* IEEE International
Conference on Cluster Computing (CLUSTER '03), 2003.

[2] N. Desai, R. Bradshaw, S. Matott, S. Bittner, S. Coghlan, R. Evard,
C. Lueninghoener, T. Leggett, J.-P. Navarro, G. Rackow, C. Stacey, and
T. Stacey. *A Case Study in Configuration Management Tool Deployment.*
19th Large Installation System Administration Conference (LISA '05), 2005.

[3] N. Desai et al. *Directing Change Using Bcfg2.* 20th Large Installation
System Administration Conference (LISA '06), 2006.

[4] N. Desai et al. *Configuration Management with Bcfg2.* SAGE Short Topics
in System Administration #19, USENIX Association, 2008.

[5] M. Burgess. *Cfengine: a site configuration engine.* USENIX Computing
Systems, 8(3), 1995.

[6] M. Burgess. *Promise Theory: Principles and Applications.* (With
J. Bergstra.) 2014.

[7] A. Couch, J. Hart, E. Greenlee, and D. Kallas. *On the Algebraic
Structure of Convergence.* DSOM 2003.

[8] W. Fu, R. Perera, P. Anderson, and J. Cheney. *µPuppet: A Declarative
Subset of the Puppet Configuration Language.* ECOOP 2017.

[9] M. Kleppmann, A. Wiggins, P. van Hardenberg, and M. McGranaghan.
*Local-first software: you own your data, in spite of the cloud.* Onward!
2019.

[10] J. Samuel, N. Mathewson, J. Cappos, and R. Dingledine. *Survivable Key
Compromise in Software Update Systems.* ACM CCS 2010. (The Update Framework.)

[11] E. Dolstra. *The Purely Functional Software Deployment Model.* PhD
thesis, Utrecht University, 2006.

[12] Survey of LLM-generated Infrastructure-as-Code, arXiv:2404.00227, 2024.
Background for §3: the field is weighted toward *generation* with correctness
verification left thin — evaluated largely by textual similarity to a
reference rather than by semantic or idempotence correctness. This is the
empirical basis for not trusting an agent to freehand policy text on the
grounds that it looks right.
