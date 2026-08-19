# tendcf: A Configuration Management Architecture for AI-Authored Configuration

**Draft, circulated for comment. Not submitted for publication.**
Daniel Joseph Barnhart Clark (djbclark@mit.edu).
Drafted 2026-08-13; facts re-checked against the vetted current-state guide
and against the repository on 2026-08-18. Sections are numbered so comments
can cite them. Every count and measurement below was re-derived for this
revision rather than carried forward — an earlier pass asserted several
numbers it had not re-run, and an audit caught them.

The vetted current-state description is
[`tendcf-architecture-guide.md`](tendcf-architecture-guide.md). The
implementer map is
[`docs/architecture/architecture-DEFINITIVE-v3.md`](../architecture/architecture-DEFINITIVE-v3.md)
and must agree with that guide. Where this paper and the guide disagree
on the current design, the guide wins.

---

## Abstract

We describe the architecture of `tendcf`, a configuration management
system for a heterogeneous, intermittently-connected fleet — Apple Silicon
macOS, Linux on x86_64 and aarch64, and Android devices running Termux —
built on an explicit premise: **most of this system's configuration will be written
by AI agents rather than by hand.** We treat that premise as a first-order
design constraint and derive a decision rule from it: prefer designs whose
correctness follows from information *local* to the file being edited over
designs that require *global* knowledge of what everyone else declared.
That rule shapes the Site Model: types state what they provide and require,
and domains are comprehensive unless they opt out with a reason.

The architecture is a data spine (the Site Model), a pure compiler from that
spine to CFEngine's native JSON augments layer, append-only JSONL as the
durable local capture with a rebuildable SQLite index in tendcf-agent, and a
signed release carrying a typed operation plan that the on-device executor
mechanically refuses to exceed. Bcfg2 supplies four of its load-bearing
ideas, credited in §6.

**Nothing described here is deployed.** No device has been provisioned from
factory reset by this automation; we have no operational numbers of any
kind, and one of our central negative results (§5.4) rests on reasoning
about a code path that has never been executed. What we do have is an
unplanned empirical result, and it is about the substrate rather than about
us: putting real weight on CFEngine's JSON data-injection layer — the layer
this whole design compiles into — surfaced defects in it faster than we
could build on it. Twenty-three defect fixes are now open as pull requests
against `cfengine/core` and `NorthernTechHQ/libntech`, ten of them in that
data layer, three of which stop the run before a single promise is
evaluated — dropping the host to failsafe — on input this design's compiler
would legitimately emit (§7). The paper's purpose is to
expose the design to an expert reader who is likely to find the holes, not
to argue that it is right. §9 is a list of the places we think it is
weakest.

---

## 1. Motivation

The site is heterogeneous rather than uniform — Apple Silicon macOS, Linux
across at least two architectures, and Android devices reached through
Termux, a forked Shizuku, and a local agent — and it is held by more than one
trusted operator rather than administered by a single authority. The design's
stated goals are to extend software freedom to configuration glue — the
generic layer is publishable, and an adopter should be able to supply their
own facts and run it unmodified — and to give the eventual users of managed
devices the ability to *understand and refuse* a proposed change to their own
computer — using **their** AI, not ours. We never run their model, see their
prompt, or see the conversation.

That framing produces the usual requirements (portability, no permanent
control node, a signed update path) and one unusual one.

**The unusual requirement is who writes the configuration.** Here the answer
is: AI agents, as the primary authorship model, with human authorship as the
exception. This is not a prediction about the industry; it is the operating
assumption this design is built under. The consequence we care about is that
the *cost structure of a configuration language changes* when its principal
author is a machine with a bounded context window, and several decisions that
are settled under human authorship become live again.

### 1.1 Scope, and where it stops applying

Every design choice below is scoped to a specific envelope: a fleet small
enough that no single role is dedicated to operating it, heterogeneous enough
that no OS-native tool covers it alone, and connected intermittently enough
that waiting on a reachable central server is not an option.

Two groups of limits follow. The first three bound the mechanisms borrowed
from Bcfg2: there is prior art, a reader can check them, and this fleet is
arguably already over two of them. Each names the point at which a different
architecture — not a variant of this one — is the better choice.

- **Local-first reporting (§2.4, §5.3) stops paying for itself once a
  fleet-wide query becomes routine rather than exceptional.** A JSONL record
  per device is free — CFEngine's local promise-outcome log must be captured
  regardless — for as long as "did host X converge" is the dominant question.
  Once "did the rollout land everywhere" (§9.6) needs an answer with bounded
  staleness often enough to matter, the honest fix is the central statistics
  spine Bcfg2 already builds, not a federation layer retrofitted onto a
  local-first design.
- **Derived dependency edges (§4.1, §5.1) stop being the cheaper mechanism
  once role interleaving is the common case rather than the exception.**
  §5.4's audit found no genuine cross-role DAG in the roles examined;
  inference earns its keep precisely where explicit edges would otherwise be
  rare, which is where roles are largely independent. A site where most
  roles genuinely depend on several others has an ordering problem that has
  become Puppet's catalog-compilation problem, and a design built to resolve
  one true DAG deterministically is then the better fit.
- **The signed-release-as-artifact model (§2.5, §5.2) stops being adequate
  once changes must land on a bounded clock across the whole fleet** — an
  active-incident patch under a compliance deadline, for instance.
  Ahead-of-time rendering optimizes for devices that are routinely
  unreachable at authoring time; a fleet whose devices are reliably reachable
  and whose changes carry real time pressure is better served by Bcfg2's
  render-on-request model (§5.2) or a push-capable policy server, where the
  server's live knowledge of what each client needs is exactly what this
  design gives up.

The second group bounds the trust and consent layer — the part with no prior
art, and the part with the most to lose. These are less comfortable, and one
of them is a standing limit rather than one this fleet grows into.

- **The consent gate does not yet mean what §2.5 says it means.** Every
  control in the gate is authored, delivered, and evaluated by the party it
  exists to constrain: the trust policy arrives in the release, the advisor
  key is enrolled in site-private, the briefing is generated upstream, and
  the nonce and the validator ship from the same place as the change. The
  one artifact the consenting person genuinely contributes is a signature.
  That defeats a network attacker and produces an honest audit trail; it is
  not sovereignty against the proposer. The smallest change that fixes the
  class rather than the instances is a **device-local trust root the release
  path cannot write** — advisor key, consent policy and peer allowlist
  established at first run into storage the validator reads and no release
  can modify. Until that exists, a site that needs the property §2.5
  describes needs a different trust architecture, not a better schema.
- **Refusal is offered, not exercised.** Every mechanism converges toward one
  authored intent; the stated purpose is to let people diverge from it. There
  is no reconciliation path, no skew budget, and no re-entry of a personal
  branch into the conflict check. Once per-device divergence is normal rather
  than exceptional, the fleet needs a design where shared invariants are
  negotiated between sovereign devices rather than compiled from one source.
- **The signing model is sized for one operator, and §1 promises more than
  one.** The limit is the second operator who must author a release without
  the first's key: threshold signing, delegation, per-role scoping,
  co-operator revocation. That is a different trust architecture, triggered
  by a condition §1 states as *already true*.
- **A comparison of two documents bounds what is described, not what happens
  on the way there.** A package install runs the vendor's maintainer scripts
  as root; a `command:` is arbitrary code at launch. Where the threat is
  hostile effects rather than hostile declarations, the answer is OS-level
  confinement — a different enclosure, not a different plan format — and this
  design does not have one.
- **The threat model outgrows this design at the compromised authoring
  agent.** Most of the configuration is written by AI agents (§3). A
  prompt-injected authoring agent that produces a Site Model compiling to a
  valid, signed goal file, briefed to the reviewer's own model by a generated
  semantic layer, is inside every control described here. Past that point the
  answer is two-party authoring review, an independent party reproducing the
  release from the Site Model, or n-of-m sign-off — none of which is this.
- **Below some engineering budget, a much smaller system delivers most of
  this.** Every limit above assumes the system exists; §8 says most of it does
  not, and there is one builder. A signed tarball of rendered per-host state
  plus a convergent applier is a large fraction of the value at a fraction of
  the cost. A reader deciding whether to adopt needs that boundary more than
  any of the others.

None of these is a claim that the design fails outside its envelope — each is
a claim about where a *different* design starts winning on its own terms,
which is the comparison §5 and §9 return to throughout.

The rest of the paper: §2 describes the architecture in enough detail to
argue about (including composition layers, per-device trust, peer actions,
and token discovery); §3 the design rule we derive; §4 two places that
rule shows up in the Site Model; §5 where we depart from Bcfg2 and why;
§6 what we took from it; §7 what building on CFEngine actually cost, which
is the only empirical result here; §8 an honest account of validation
status, which is otherwise thin; §9 the open questions we would most like
attacked.

---

## 2. Architecture

### 2.1 The Site Model: facts in layers, behavior in tendcf

Git-repo count is not the composition mechanism. Layers are roles:

- **tendcf** (public) — engine, schemas/types, generic adapters, default
  advisor prompt, compiler interface.
- **site-shared** (optional, public) — reusable recipes, not live inventory.
- **foreign site-shared** — other people's recipes, listed as read-only inputs.
- **site-private** (never an input) — this site's facts: inventory,
  allocations, secret *names*, trust policy, extra advisor prompt. Holds the
  lockfile that pins everything else.
- **tool forks** (optional) — nix2cf, sudo-secretspec, Shizuku, only if
  patching them.

Site-private holds a lockfile (flake-style inputs) that pins tendcf, nix2cf,
site-shared, foreign shared sites, and optional tool forks. The signed
release is the deploy artifact. There is no lockstep of sibling checkouts
that must share one tag. Collision of the same identity from two peer inputs
is a **compile error**. Only site-private may bind a winner
(`caddy: from: alice`) or a short name. Never silent last-wins. Foreign
inputs are namespaced (`alice.caddy`) so auto-provided service tokens do not
collide.

Every fact about *this* site lives in schema-validated JSON/YAML files called
the Site Model. Behavior lives in generic code in tendcf that holds no facts
and is therefore publishable. Adapters translate. Every config tool —
CFEngine, the toolchain bootstrapper, Nix for builds — is a *consumer* of
that data and is individually replaceable. An adopter supplies their own Site
Model through the same schema.

**Inventory is private by default.** Site-shared may ship device *kinds*,
example inventories, and explicit exports (public endpoints, role
advertisements) only for fields the private site marked exportable. A host
identity in trust and ChangePlans is the **device public key**, not the
hostname.

Three record types matter for what follows. `services.yml` holds one record
per service (name, run-as user, argv command, environment as secret *names*
only, role binding, owning writer, supervisor); every systemd unit, launchd
plist, runit service, or Jobber job in the fleet is a rendering of one such
record. `roles.yml` maps a feature role to `{main, backups[], peers[]}` —
this is how "the control node" is dissolved into data, since any host may
hold any role. Unit-writer registries declare exactly one writer per
unit-name prefix for every supervisor, killing a two-writers hazard at the
source. launchd is one adapter, not the model.

Schemas and types belong in tendcf (`schema/`, `examples/`,
`bin/schema_lint.py`). The compiler (`nix2cf`) is a tool; it is not the
home of the contract. A schema change is a tendcf interface change; a
hostname change is site data.

The Site Model *may* be authored in the Nix module system — `mkOption`,
`types.*`, `mkIf`/`mkDefault`/`mkMerge` — and rendered to the same JSON
everything else consumes. That is an authoring frontend only; the rendered
JSON is what is schema-validated, signed, and read downstream, and a person
adopting the project is never required to know Nix to read or fork their own
site data. We use the Nix *language* and not the Nix *build system*: a
service that should be running is typed data, and nothing about it needs to
become a derivation.

### 2.2 The compiler: a pure function into CFEngine's own data layer

A compiler (working name `nix2cf`) reads the Site Model and renders CFEngine
augments — `def.json` / `host_specific.json` — CFEngine's native JSON
data-injection layer. The name `nix2cf` is historical; an optional Nix module
frontend may author the same JSON later. The compiler is a tool, not the home
of schemas.

Two details of that layer are load-bearing and neither is obvious from the
documentation; we state them because we got both wrong first. **The version
floor is 3.18, not 3.7.** 3.7.0 put augments into the Masterfiles Policy
Framework and 3.7.3 back-ported `def.json` parsing into the core agent, but
`$(sys.workdir)/data/host_specific.json` has only been parsed since 3.18.0,
so a design using both files inherits the later floor. **And despite the
name, YAML is not a valid augments input** — the agent reads JSON only.
YAML remains an authoring format for the Site Model and never reaches a
device.

More consequential: **the two files are read by two different loaders into
two different variable scopes.** `def.json` goes through `LoadAugmentsData()`
and lands under `def.*`; `host_specific.json` goes through CFEngine's CMDB
loader (`LoadCMDBData`/`ReadCMDBVars` in `libpromises/cmdb.c`), and a bare,
unprefixed key there defaults to namespace `data`, scope `variables` — so a
policy reads it as `$(data:variables.<key>)`, not `$(def.<key>)`. Our first
draft of the generic bundle assumed the augments scope for both and was
silently wrong: the variables simply did not exist, with no error. That is
the §3.2-item-1 problem in its natural habitat, and it is why every
non-obvious claim in this section was confirmed against a running build
rather than read off a page.

The standard Masterfiles Policy Framework is already substantially
data-driven on top of that layer, so for the common case the compiler emits
*data*, not promise text: a generic bundle written once handles "this
package is present and pinned, these directories exist, this service is
loaded" for any entry in the data. Only promise types the stock library does
not cover need policy text, and that is templated from typed option values
rather than synthesized. A first version of that bundle now exists and runs
(§8); it is launchd-only, which is a real limit and not a placeholder.

Merging of the site → role → host layers happens once, in the compiler,
before render — we do not additionally use CFEngine's `mergedata()`, on the
same grounds we do not hand-maintain two type systems.

The pipeline has four stages: merge, conflict check, dependency inference,
render. The conflict check is deliberately a *separate stage over
already-merged declarations* rather than logic fused into the type
definitions, so that adopting the Nix module system's priority algebra
(`mkDefault`/`mkForce`/`mkOverride`) later is a policy change at one stage
and not a schema redesign.

Because the render is a pure function of the Site Model — the same purity
Nix's own build model is named for [27] — "show me exactly what device X
would receive, without touching device X" is nearly free. We
plan to build that affordance *first*, before the pipeline is finished, and
§6.2 explains why it earns its place three separate times over.

**Where it runs:** operator machine or CI. Consented devices receive a
signed artifact. They do not run Nix or nix2cf.

**This compile-to-native-format shape is not new.** A typed or module-based
authoring language compiling to an existing execution engine's native format
is an established pattern: NixOS's own module system compiles down to
`systemd` unit files [18], `nix-darwin` compiles Nix modules to `launchd`
agents and macOS `defaults` [19], and `cdk8s` synthesizes typed code into
Kubernetes YAML [20] (`cdktf` did the same into Terraform JSON before
HashiCorp deprecated it in December 2025 [21]). The pairing here is Site
Model (YAML/JSON, or an optional Nix frontend) into CFEngine Augments,
because of Promise Theory and disconnected multi-owner operation (§2.3) —
not because the compiler mechanism is new. NixOS / nix-darwin remain
optional Mac *substrate*, Step 7, not a runtime dependency of the compiler.

### 2.3 Deployment shape: no policy server, push and pull as one mechanism

Every host runs its own `cf-serverd` and reads policy synced via git as part
of the ordinary signed-release mechanism. There is no dedicated central
policy host, no SSH dependency, and no push requirement. Push exists — a
host holding a deploy role can trigger an immediate convergence run on
**operator** (and operator-chosen `managed`) hosts rather than waiting for
the next cycle. Push to a `consented` device still requires that device's
consent grant. Push and pull are two modes of the same mechanism.

**Supervisors are adapters.** A service record is one fact. The host's
`supervisor` field (or a platform default) selects the renderer: systemd,
launchd (macOS example), runit via termux-services, Jobber, OpenRC / s6 /
dinit when a real host needs one. Packages on Linux come from CFEngine's
package modules. File and service idioms are taken from ncf / Rudder generic
methods as a vendored, stripped reference — not as a runtime.

This shape was scoped out of an earlier revision on the belief that CFEngine
required dedicated policy-server infrastructure and an SSH push model. Both
beliefs were wrong, and had entered the design as an analyst's unvalidated
assumptions rather than as checked constraints. We record it because it
changed the answer: once the practical objections dissolved, CFEngine was
the better fit on its own terms, not an acceptable substitute.

**The no-control-node property is CFEngine's own, not ours.** Promise
Theory was formalized as a model of autonomous agents specifically to rule
out client-server protocols that push data to a controller [6]; nothing
about "no control node" is this paper's invention, and it is the actual
reason §2 chooses CFEngine over the alternatives. What CFEngine's own
documentation prescribes as its standard deployment, though, is not this:
it is hub-and-spoke, one policy server, clients pulling from it [23]. What
makes "every host runs its own `cf-serverd`" a real option rather than a
misreading is a documented CFEngine primitive for exactly this — bootstrap
sets a host as its own policy hub when its declared server address is
itself [23] — applied here fleet-wide, off a shared git-synced source,
which is not CFEngine's textbook case either. The closest prior art for
that specific combination — an in-place agent pulling desired state from
git, no push, no reachable control plane holding credentials — is GitOps,
coined by Weaveworks and carried forward by Flux under the CNCF since 2019
[22], structurally the same shape applied here to CFEngine promises across
a heterogeneous OS/Android fleet instead of to Kubernetes manifests across
clusters. For the often-off-device half specifically, balenaCloud is the
closest working system solving the same problem — offline-tolerant
updates, connectivity-degradation tracking [24] — with one real
architectural difference from what we do: it is centralized, and devices
phone home to it; this design has no equivalent to phone home to at all.

### 2.4 The record of truth is local

Capture and index are different files. The durable capture is append-only
JSONL, one `write()` per event, filled from CFEngine's local promise-outcome
log. The queryable index is SQLite inside tendcf-agent, rebuildable from
JSONL. CFEngine never opens SQLite. If the index is corrupt, history still
exists. Any central or shared view is optional and eventually consistent.

The grounds are narrower than the local-first literature's [25], and one of them
is an operational fact about this fleet rather than a principle. On CFEngine
Community the local capture must be built regardless, so local-as-record is
the null option and central-as-record is a second system to keep complete and
in sync. And devices in this fleet demonstrably go unreachable — flaky ADB
over wireless, Android boot-recovery failures, offline peers — so any central
copy fed by best-effort sync is incomplete during exactly the windows one
would want it.

On Android, Termux and tendcf-agent are different UIDs; the APK cannot read
Termux private directories as files. The agent owns both JSONL and SQLite in
app-private storage. Either cf-agent runs as a native helper of the agent, or
a Termux-side reporter pushes lines to the agent. Never "the agent opens
Termux's files."

We keep the outcome vocabulary of `ncf` — Rudder's library of parameterized
CFEngine generic methods, which we vendor as a reference corpus rather than
depend on — verbatim: `success`/`repaired`/`error`/`n-a` in enforce mode,
`compliant`/`noncompliant`/`error`/`n-a` in audit mode. It is a well-tested
structured vocabulary and only the sink is changing.

### 2.5 Releases carry a goal file; the device applies only an approved diff

Configuration reaches devices only as a versioned, signed release. The
per-host payload of that release is the device's **complete canonical goal
file**: one fully resolved JSON document describing the whole managed state
of that host. The device computes the **diff** between the goal file it has
already approved and the one the release proposes — that diff *is* the
ChangePlan — and the on-device executor is a **validator** over it,
comparing two canonical documents against the approved diff and performing
no policy interpretation.

**CFEngine never reads the goal file.** The goal file is the object consent
binds to, and it is the wrong shape for the agent: augments consumes a
narrow `{"vars": {…}}` document and skips every other top-level key in
silence. So a **projection** step, running device-side and only after
approval, re-keys the approved state into that shape. The projection is
policy-free by construction — it copies each entry's declared `state`
verbatim and decides nothing — which is what keeps the decisions that
matter (present versus absent, whether an interlock's guard is met) inside
the reviewed policy rather than inside an unreviewed transform. The
projection is derived from the goal file, is not itself signed, and is not
the whole document. Getting this wrong in the obvious way — signing what
the agent reads instead of what the person approved — would put the
consent gate on the wrong artifact, so the split is deliberate. A reference
projector exists and CI gates it against golden bytes (§8).

An earlier design put a closed `capability` vocabulary and per-operation
`resources` in the plan and had the executor refuse any effect outside the
declared set. It is withdrawn. CFEngine has no runtime capability
confinement, so such an executor could only be a pre-flight *interpreter* of
the vocabulary plus a proof that the vocabulary describes what the rendered
policy actually does; neither artifact exists, and neither is in budget for
one unfunded builder. Coverage instead closes by construction: compiler and
validator share one schema and fail together.

The distinction we are drawing is between "apply this bundle because its
hash is signed" and "apply only this difference, because a person approved
exactly it." The first authenticates the author; only the
second constrains the effect. Signing itself is an unremarkable TUF [26]
subset sized for one operator, plus a durable per-client high-water mark so
replay, freeze, and downgrade are closed. The first trusted root is enrolled
out of band: install shows the fingerprint, and the person compares it to a
channel they already trust. TOFU is not used for consented devices. Later
root rotation is in-band (threshold of old **and** new keys). Threshold
compromise of root is again out of band. Revocation, freeze detection, and
high-water rejection tighten what may run and do not need a local yes;
installing new targets on a consented device still does. An optional enrolled
policy "I pre-grant emergency security patches from role E" may exist;
**default off**.

Layered on the verifiable plan is a *semantic* layer — generated, cached,
and written for a language model to read: "this bumps a TLS library across a
CVE and restarts the public proxy." The semantic layer briefs a user and
their advisor; it never authorizes. Only the verifiable layer, checked by
the executor, authorizes. Where the prose can be filled in from the plan's
typed fields, it is. Where it has to be written freely, it must point at the
exact fields it is summarizing.

We never run their model, see their prompt, or see the conversation. We
offer a change and accept a signed yes/no, the same shape as a Kubernetes
admission webhook. At install they enroll an **advisor key** (or a local
app/socket) in site-private. tendcf ships a suggested default prompt as a
replaceable public file; they may append or replace it. Modes: auto-review,
or a conversation with them first. Return path: `accept | reject`, signed by
the enrolled key, bound to that plan's nonce. Timeout is deny. Advisor down
→ fail closed for *installs* (revocation still applies). Custom tools
(OpenPGP web of trust, a transparency log, a chain, gossip of signed
apply-attestations) are theirs. Consensus among "everyone waiting for
everyone else" is a separate project that consumes attestations. tendcf
owes: the ChangePlan, optional exportable apply-attestations, the
`accept | reject` slot. The proposing side and the consenting side are
different programs. The advisor never authorizes; the executor does, against
the signed grant. A personal branch is theirs, applied under their consent;
it never auto-merges into anyone else's trust domain.

### 2.6 Three worked examples: input to output

The rest of §2 describes the pipeline in the abstract. This section shows it
on two concrete Site Model records, chosen because they are the two
mechanisms §4 and §6 argue hardest for: an inferred dependency edge with
mandatory attribution, and an interlock. A third example follows the two,
showing the same interlock as running code rather than as intent.

**A note on provenance, because it matters for how to read these.** The
*inputs* below are verbatim excerpts from
[`examples/services.yml`](../../examples/services.yml)
— a real fixture, schema-validated by `bin/schema_lint.py` against
`schema/services.schema.json`, though still a fixture and not live site data
(§8). launchd here is one adapter; the same service record would render a
systemd unit or a runit service on another host. The *outputs* — the
CFEngine augments and the rendered promise text — are hand-authored by us
to show the target shape, as is the Nix rendering of the same input shown
partway through Example A. `nix2cf`'s render stage and its Nix authoring
frontend do not exist yet (§6.5, §8), so nothing in Example A except the
YAML was produced mechanically.

**One further warning, and it is the kind of thing this paper exists to
surface.** The augments document shown in Example A is *pedagogically*
right and *mechanically* wrong: its two top-level keys, `data` and
`nix2cf_edges`, are both keys the agent silently skips. As written it
injects nothing. We keep it because it shows the derivation legibly, which
is what the example is for, and we flag it because an illustration that
would not run is exactly the sort of claim a reader should be able to
catch us on. The shape the agent actually consumes is `{"vars": {…}}` and
nothing else, reached by the device-side projection of §2.5; that shape,
and a generic bundle that reads it, both exist and are shown at the end of
this section.

**Example A — an edge nobody wrote.** `caddy` and `litellm-proxy` are two
records in the same `edge-http` bundle. `litellm-proxy` states only what it
needs; nothing in either record says "start after caddy."

```yaml
# examples/services.yml — excerpt from the real, schema-validated fixture;
# description/hosts/role/managed_by trimmed for space, values unchanged
  - name: caddy
    domain: macos-launchd-services
    bundle: edge-http
    platform: macos
    runs_as: djbclark
    command: ["/opt/homebrew/bin/caddy", "run", "--config", "/etc/caddy/Caddyfile"]
    launchd:
      label: com.djbclark.caddy
      run_at_load: true
      keep_alive: true
    provides:
      - service:caddy
      - port:443
      - port:80
    requires:
      - path:/etc/caddy/Caddyfile
      - service:tailscaled

  - name: litellm-proxy
    domain: macos-launchd-services
    bundle: edge-http
    platform: macos
    runs_as: djbclark
    command: ["/opt/homebrew/bin/litellm", "--config", "/etc/litellm/config.yaml"]
    env:
      LITELLM_MASTER_KEY: LITELLM_MASTER_KEY
      OPENAI_API_KEY: OPENAI_API_KEY
    launchd:
      label: com.djbclark.litellm
    provides:
      - service:litellm
      - port:4000
    requires:
      - service:caddy
      - secret:LITELLM_MASTER_KEY
```

§2.1 states that the Site Model may instead be authored through the Nix
module system and rendered to the same JSON. That frontend does not exist
yet either, so this is the same illustrative-output caveat as the augments
and plist below — but it shows what `caddy`'s record above would look like
as typed options rather than as YAML, `mkOption`/`types.*` and all:

```nix
# site/services/edge-http.nix — the same caddy record via the Nix authoring
# frontend §2.1 describes; would render to the identical YAML/JSON above.
# ILLUSTRATIVE — the frontend is unbuilt (§6.5), values match the fixture.
{ lib, ... }:
let
  inherit (lib) mkOption types;
in
{
  options.siteModel.services.caddy = {
    description = mkOption {
      type = types.str;
      default = "Site reverse proxy and HTTPS terminator";
    };
    domain = mkOption { type = types.str; default = "macos-launchd-services"; };
    bundle = mkOption { type = types.str; default = "edge-http"; };
    platform = mkOption {
      type = types.enum [ "macos" "android" "linux" "any" ];
      default = "macos";
    };
    runsAs = mkOption { type = types.str; default = "djbclark"; };
    command = mkOption {
      type = types.listOf types.str;
      default = [ "/opt/homebrew/bin/caddy" "run" "--config" "/etc/caddy/Caddyfile" ];
    };
    launchd = {
      label = mkOption { type = types.str; default = "com.djbclark.caddy"; };
      runAtLoad = mkOption { type = types.bool; default = true; };
      keepAlive = mkOption { type = types.bool; default = true; };
    };
    # provides/requires are typed the same way regardless of frontend (D16(b)):
    # local knowledge lives in the option, not in which language declared it.
    provides = mkOption {
      type = types.listOf types.str;
      default = [ "service:caddy" "port:443" "port:80" ];
    };
    requires = mkOption {
      type = types.listOf types.str;
      default = [ "path:/etc/caddy/Caddyfile" "service:tailscaled" ];
    };
  };
}
```

The module system buys `mkIf`/`mkDefault`/`mkMerge` for authors who want
them; nothing about §4's rule changes with the frontend, because the merge
still happens once, in the compiler, before render (§2.2) — the priority
algebra is a policy choice at that stage, not a second type system to keep
in sync with the schema.

`litellm-proxy`'s `requires: [service:caddy, ...]` matches `caddy`'s
`provides: [service:caddy, ...]` (and would also match auto-provide of
`service:caddy` from the name alone, §2.9). The compiler derives an ordering
edge from that match alone — no author declared it — and §4.1 requires the
edge to carry its own provenance rather than appear as a bare ordering fact:

```jsonc
// host_specific.json (host: mac) — ILLUSTRATIVE ONLY, hand-authored.
// Does NOT load as Augments: top-level `data` and `nix2cf_edges` are both
// skipped by the agent. Shown for the derivation, not to be copied.
{
  "data": {
    "nix2cf_services": {
      "caddy": {
        "service_policy": "start",
        "launchd_label": "com.djbclark.caddy",
        "command": ["/opt/homebrew/bin/caddy", "run", "--config", "/etc/caddy/Caddyfile"],
        "run_as": "djbclark"
      },
      "litellm-proxy": {
        "service_policy": "start",
        "launchd_label": "com.djbclark.litellm",
        "command": ["/opt/homebrew/bin/litellm", "--config", "/etc/litellm/config.yaml"],
        "run_as": "djbclark",
        "env": { "LITELLM_MASTER_KEY": "@{secrets.LITELLM_MASTER_KEY}" }
      }
    }
  },
  "nix2cf_edges": [
    {
      "from": "litellm-proxy",
      "to": "caddy",
      "on": "service:caddy",
      "origin": "inferred",
      "rule": "requires-matches-provides",
      "source": { "file": "services.yml", "service": "litellm-proxy", "field": "requires[0]" }
    }
  ]
}
```

The generic bundle behind `nix2cf_services` is what materializes the actual
on-device artifact — for `caddy`, the launchd plist CFEngine keeps present
and loaded:

```xml
<!-- /Library/LaunchDaemons/com.djbclark.caddy.plist — rendered, not authored -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.djbclark.caddy</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/caddy</string>
        <string>run</string>
        <string>--config</string>
        <string>/etc/caddy/Caddyfile</string>
    </array>
    <key>UserName</key>
    <string>djbclark</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

`nix2cf_edges[0]` is what §4.1 means by mandatory attribution: `origin` says
this edge was never authored, `rule` names the mechanism that produced it,
and `source` points at the exact `requires` entry responsible. If this edge
turns out to be spurious, the question it presents is "does `rule` correctly
apply to this pair" — a lookup — rather than "where did this ordering
constraint come from" — a search.

**Example B — an interlock, from schema to guard.** The `fleet-vpn` bundle
carries the precondition §6.1 takes from Bcfg2 Actions: lockdown may not be
enforced before the VPN authenticates.

```yaml
# examples/services.yml — excerpt; launchd is one adapter
bundles:
  fleet-vpn:
    description: "VPN transport and the lockdown policy that depends on it"
    domain: macos-launchd-services
    interlocks:
      - id: tailscale-authenticated-before-lockdown
        description: >-
          The mesh VPN must be authenticated before always-on VPN lockdown
          may be enforced. Setting lockdown on a device whose VPN is
          unauthenticated severs every management path to it.
        pre_action:
          command: ["tailscale", "status", "--json"]
          expect_exit: 0
          timeout_seconds: 15
        defines_class: tailscale_authenticated
        blocks: enclosing-bundle
        report: true
```

`blocks` and `report` are `const` in the schema (§2.1's common definitions) —
an author cannot narrow the blast radius or silence the report, so there is
no branch in the render stage where it could either. The illustrative
rendering:

```cfengine
# ILLUSTRATIVE — hand-authored CFEngine promise sketch, not compiler output
bundle agent fleet_vpn
{
  classes:
      "tailscale_authenticated"
        expression => returnszero("/usr/local/bin/tailscale status --json", useshell);

  methods:
      "guard"
        usebundle => report_if_missing_class("tailscale_authenticated",
                       "fleet-vpn: blocked, VPN not authenticated");

  services:
      # every promise in this bundle carries the same guard —
      # blast radius is the whole bundle, not a per-promise choice,
      # because the schema fixed "blocks": "enclosing-bundle" as a const.
      "tailscaled"
        service_policy => "start",
        ifvarclass => "tailscale_authenticated";
}
```

The guard is attached once, at the bundle, and inherited by every promise in
it — mechanically, because the schema gave the render stage no field to read
a narrower scope from. That is the sense in which §6.1's claim ("an author
who could narrow either one could reintroduce the bug the mechanism exists
to close") is enforced by omission rather than by convention.

**Example C — the same interlock, this time for real.** Examples A and B
show intent. This one shows the two artifacts that were subsequently built
and run, so a reader can tell which parts of this paper are argument and
which are code. Neither existed when §2.6 was first written.

The projection of §2.5, applied to a goal file, produces
[`examples/host_specific.json`](../../examples/host_specific.json). It is
JCS-canonical bytes on disk — one line, sorted keys — shown pretty-printed
here and abbreviated to the interlock and one service:

```json
{
  "vars": {
    "tendcf_interlock": {
      "caddy-config-valid": {
        "blocks": "enclosing-bundle",
        "bundle": "caddy",
        "defines_class": "caddy_config_ok",
        "pre_action": {
          "command": ["/opt/homebrew/bin/caddy", "validate",
                      "--config", "/etc/caddy/Caddyfile"],
          "expect_exit": 0,
          "timeout_seconds": 30
        },
        "report": true,
        "state": "present"
      }
    },
    "tendcf_service": {
      "com.tendcf.caddy.main": {
        "bundle": "caddy",
        "command": ["/opt/homebrew/bin/caddy", "run",
                    "--config", "/etc/caddy/Caddyfile"],
        "env": { "CADDY_ADMIN_TOKEN": "CADDY_ADMIN_TOKEN" },
        "run_as": "caddy",
        "state": "present",
        "unit": { "launchd": { "keep_alive": true, "run_at_load": true } },
        "working_dir": "/"
      },
      "com.tendcf.caddy.retired": { "state": "absent" }
    }
  }
}
```

Two things in that document are the design's claims made concrete rather
than described. `com.tendcf.caddy.retired` carries `"state": "absent"` and
is still *present in the file* — the tombstone of §2.5, which is what makes
removal converge instead of evaporating when a device catches up across
several releases. And `env` maps a variable name to a secret *name*, never
a value; the projector treats a resolved secret in that position as a
load-breaking error rather than a warning.

The bundle that reads it,
[`policy/tendcf_services.cf`](../../policy/tendcf_services.cf), is where
every decision lives, because the projection makes none. Its two
non-obvious mechanics were both forced by the substrate rather than chosen:

```cfengine
# policy/tendcf_services.cf — real, runs. Abbreviated.
  vars:
      "service_ids"   slist => getindices("data:variables.tendcf_service");
      # Entry ids are launchd labels ("com.tendcf.caddy.main") and bundle
      # tags are kebab-case; CFEngine class names accept neither dots nor
      # hyphens. Anything that becomes part of a class name is canonified
      # first; the raw id is kept for data lookups and the plist Label.
      "service_canon[$(service_ids)]" string => canonify("$(service_ids)");

  classes:
      "service_$(service_canon[$(service_ids)])_present"
        expression => strcmp(
          "$(data:variables.tendcf_service[$(service_ids)][state])", "present");

      # Blast radius is the bundle tag, not the referencing service, so N
      # interlocks sharing a tag OR together with no join against the
      # service list. This is §6.1's "enclosing-bundle" const, mechanically.
      "interlock_blocked_$(interlock_bundle_canon[$(interlock_ids)])"
        expression => "!interlock_ok_$(interlock_canon[$(interlock_ids)])";
```

**The refusal was tested for real, not simulated.**
[`examples/policy/host_specific-interlock-blocked.json`](../../examples/policy/host_specific-interlock-blocked.json)
declares a service whose bundle carries an interlock whose `pre_action` is
`/bin/false` — a command that genuinely fails, not a mocked failure — and a
non-dry-run `cf-agent` run confirms the gated service's promises are
skipped and the refusal reported. That is a small result, and it is the
only place in this paper where a mechanism is demonstrated rather than
argued.

Three limits, stated because the bundle is v1 and the temptation is to
report it as more than it is. It is **launchd-only**: systemd, runit and
Jobber are unwritten, so "supervisors are adapters" (§2.3) remains a claim
about a design and not about running code. It renders the plist through
`edit_template`/mustache, which does **not** perform CFEngine's own `$()`
substitution, so anything needing expansion must be expanded before it
reaches the template. And `pre_action.command` is reassembled into a
shell string via `join()`, because CFEngine will not accept an indexed
container element as a non-scalar attribute — an argv element containing a
space or a shell metacharacter is not currently isolated. That input comes
from our own schema-validated goal file rather than from an attacker, so it
is a limitation rather than a vulnerability, but it is a limitation we
would rather a reader find here than in the code.

### 2.7 Peer actions: help without a global lock

Some operations a host cannot perform locally. Example from our last system:
a device that cannot start its privileged helper itself; any healthy peer in
its allowlist may do it over ADB; if every helper is down, **only that
device waits**.

That is a **peer action**: the target declares an operation it cannot do
locally; any helper with the capability **and** on the **target's** peer
allowlist may do it. Helpers are fungible. Prefer **groups** ("household
helpers") plus allowed verbs, not only individual keys. Stall is local.
Idempotent. Not a distributed lock, and not Bcfg2's LISA '06 state machine
over *releases* — those stall the *fleet* when one box is unreachable.

Cross-machine "wait until the server is serving the new export" is a **local
probe** (or a wait for a signed apply-attestation from the host that holds
that role). Bcfg2's FSM is a **view** reconstructed from JSONL plus optional
attestations, never a coordinator. §6.5 records the Bcfg2 comparison.

### 2.8 Per-device trust

`trust_tier` (`operator` | `managed` | `consented`) is a **class**: which
consent gate applies. It is not who trusts whom. Full-mesh "every device has
operator root to every sibling" is **not** the product default. It is a
site-private policy some operator-tier labs may still choose.

Each device carries a **local trust policy** in its signed release (authored
in site-private). It does not phone home to ask.

| Axis | Question | Default |
| --- | --- | --- |
| **Release** | Whose signatures may change me? | Site TUF root enrolled at the first-run ceremony |
| **Consent** | Do I also need a local yes? | `operator`: no. `consented`: yes (advisor key). `managed`: operator-chosen |
| **Peer** | Who may act *on* me (ADB, SSH, peer-help)? | Nobody, unless listed. Prefer groups plus allowed verbs |
| **Attestation** | Whose "I applied this" counts for my advisor tools? | Only sets that person configured |
| **Secrets / cache** | Who may receive this secret or substitute this store path? | secretspec resolver; cache keys `operator` only |

Peer actions check the **target's** peer allowlist, not only "the helper has
a capability." Identity is the device public key. A label in inventory does
not enforce this. The executor does. Web-of-trust thresholds ("50% of people
I trust have installed this") live in the **advisor plug-in**, not in the
executor.

### 2.9 Token discovery

Inference removes "you must already know the *edge*." Naming the *thing* is
a catalog, not a graph.

1. Auto-provide `service:<name>` unless the service opts out.
2. Lookup CLI against registries and compiled provides (`who-provides`,
   `does-role exist`, `tokens kind=service`).
3. Unknown token, unmatched `requires`, or two providers of the same token
   → compile error listing near-misses and the catalog.

Token *kinds* are a closed enum in the schema (`service`, `port`, `path`,
`secret`, `class`, `network`, …). Token *values* are instance data, checked
at compile time — not a schema enum that changes with every new service. The
writing rule is "don't require the graph," not "don't require names." Token
discovery is a mechanism, not an open question; whether authors actually use
the lookup is untested.

---

## 3. The design rule

The requirement is that most configuration here is machine-authored. The
rule we derive from it — a rule we are adopting and testing, not one we
consider settled — is:

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

We are aware this rule can be used to justify almost anything, and §9.2 asks
directly whether it is an argument or a hypothesis.

### 3.1 This rule is not new; the reason for it is

Local reasoning about global properties is not a new idea in programming-language
theory. It is the organizing idea behind separation logic and, more directly,
Banerjee, Naumann, and Rosenberg's region logic [9], which derives global
heap invariants from purely local reasoning about mutation and separation.
What differs here is the cost function: those logics discharge a
bounded-context *verifier*. We are designing for a bounded-context *author*.
Tratt [10] makes a closely related argument from the language-design side,
independently and roughly concurrently with this draft: AI code generation is
reliably good at local (e.g., function-level) reasoning and unreliable at
global reasoning, so a language that lets a local author discharge a global
property — his example is Rust's ownership system enforcing data-race
freedom through local signatures — benefits AI-generated code the same way
it benefits human-verified code. We did not originate this framing; §10
returns to what we think our actual contribution is.

That the failure mode motivating this is real, not just plausible, has
empirical support in exactly this domain. Liu et al. [11] show LLM accuracy
degrades sharply once relevant information sits away from the start or end
of the context window — the bounded-context premise this paper assumes,
measured rather than asserted. Kon et al.'s IaC-Eval [12] found GPT-4
produces a correct Terraform configuration on the first try only 19.36% of
the time on real-world AWS scenarios; Nekrasov et al.'s error taxonomy of
LLM-generated infrastructure-as-code [13] isolates why, naming "Contextual
Reasoning Failure" — missing or incorrect cross-resource references, i.e.
exactly the global-knowledge dependency §4.1 discusses below — as a
distinct, substantial failure category separate from syntax or schema
errors. Grammar-constrained decoding [14] is a parallel response to the same
underlying problem at a different layer: instead of designing the language
so a local author cannot express an inconsistent global state, it constrains
the decoder so the model cannot emit tokens outside a formal grammar in the
first place. Both approaches assume the same premise — a machine author's
failure mode is disproportionately about consistency with information it
cannot see, not syntax it cannot produce.

### 3.2 Nine concrete instances

Grounding the rule in prior work (§3.1) answers whether the idea is
defensible. It does not show whether it pays for itself in a real design.
Extending the same search past this paper's own claims, into the
architecture document `tendcf` is built from
([`architecture-DEFINITIVE-v3.md`](../architecture/architecture-DEFINITIVE-v3.md)),
surfaced nine concrete
applications of §3's rule, each checked directly against its cited source
rather than a summary of it.

**1. A targeted lookup instead of a whole-file read.** An agent that needs
to know whether a given port is already claimed, or whether a named role
exists, has today exactly one option: open the registry file that holds
that fact and read the whole thing to find one line. That is a small
version of the same global-knowledge cost §3 argues against — the fact the
agent needs is local and small, but the file it has to open to get it is
neither. A single-purpose lookup — ask the one question, get the one
answer — is a smaller, more literal application of the rule than the
Site Model's schema design, and closely analogous work on generating
planning-language code found that retrieving just the relevant fragment of
documentation, instead of the whole specification, improves the generated
result directly, not merely the cost of producing it [15].

**2. Worked examples belong beside their schema, enforced, not customary.**
The same study finds worked examples consistently outperform prose
description as a way of telling a generator what correct output looks like
[15]. The project's schema set already pairs one
concrete, validated example file with every schema it defines — a
convention adopted before this literature search, for ordinary
documentation reasons, that turns out to be exactly the intervention the
literature says matters most. The pairing lives in this repository
(`schema/` next to `examples/`). The gap this closes is not that the pairing
is missing; it is that nothing currently stops the pairing from silently
lapsing as new schemas are added. Making the build fail when a schema
arrives without its paired example is the same move §3 makes generally:
convert a habit that depends on someone remembering into a check that
does not.

**3. A document's warning about itself should be a check, not prose.** The
architecture document this paper describes (`architecture-DEFINITIVE-v3.md`)
carries, at its own top, an
instruction telling any AI agent reading it not to modify the document
without a human's explicit approval. That instruction is exactly the
shape of thing §3's second clause warns about: a convention a reader must
remember, stated in prose, with nothing enforcing it. The fix is not
subtle — a repository-level check that refuses any change to that file
unless the commit carries an explicit marker recording that a human
approved it, mechanically the same treatment already given to a separate,
unrelated incident earlier in the project's history, where an agent's
edit landed in another agent's unreviewed workspace. What makes this
instance worth naming on its own is not the mechanism, which is ordinary,
but where it was found: the rule caught a document failing to apply the
rule to itself, in the document that states the rule.

**4. Guardrail investment should match the measured error distribution,
not intuition.** The error taxonomy already cited in §3.1 [13] does not
just show that cross-resource, global-knowledge errors are real (§3.1's
point); it ranks every error category by how often it actually occurs in
real machine-generated infrastructure code. Errors that reference
something invalid, outdated, or nonexistent are the largest category by a
wide margin, at roughly two-thirds of all technical errors; errors of
simple omission are the second-largest, at roughly a quarter; syntax and
structural errors — the category schema validation is best at catching —
are the smallest, at under two percent. This produces two findings, not
one. First, the mechanical checks worth adding next are the ones that
verify a referenced value actually exists and is current, since that is
where most real errors are, not additional structural strictness, since
that is where almost none of them are. Second, and unplanned: a design
decision made for an unrelated reason — detecting when two contributors
change the same device without coordinating — turns out to already be
close to the correct structural answer to the second-largest error
category, because an AI agent's accidental omission and a second writer's
uncoordinated drift produce the identical observable symptom: something
present on the device that nothing describes. That alignment was not
designed in; it was found by checking a decision already made against
data that did not exist when the decision was made.

**5. A generated summary that cannot authorize an action can still
mislead the person reading it.** Part of this design's sovereignty
feature (§2.5) works by generating, for the person receiving a proposed
change to their own device, a plain-language explanation of what the
change does — separate from, and strictly weaker than, the exact,
machine-checked description that actually governs what the change is
allowed to do. The explanation cannot authorize anything by itself. But a
wrong explanation can still talk a person into accepting a change they
would have refused, or into refusing one they would have wanted, even
though it never touches the authority to act — which is precisely the
harm the design's consent mechanism exists to prevent. This is the same
shape of problem addressed by a broader body of work on grounding
generated text in retrieved or cited source material, which finds that
requiring a generated claim to point at the specific fact it summarizes
measurably reduces unsupported claims relative to generating freely from
the same underlying facts. Filling the explanation in from the same exact
fields the machine-checked description already carries, wherever a fixed
phrasing can say it, and requiring any explanation written in free prose
to cite the exact field it is describing, gives a skeptical reader
something to check the explanation against — the same discipline a
citation gives a claim in a paper.

**6. Grammar-constrained decoding narrows the design's weakest-guarded
surface.** One part of this design still permits an agent to author a
small amount of raw, low-level configuration text by hand, for cases the
higher-level schema does not yet cover — and that surface is already
flagged elsewhere as the design's least-verified corner, precisely because
there is no schema there to check the output against, unlike everywhere
else machine authorship touches this system — the same gap the broader
LLM-for-IaC literature has at the field level, where verification is
generally thin, evaluated by textual similarity to a reference rather than
by semantic or idempotence correctness [28], which is exactly why we do
not trust an agent to freehand policy text here on the grounds that it
looks right. A recent line of work makes
it practical to constrain what a model can generate, token by token, to a
formal grammar, efficiently enough for production use rather than only as
a research demonstration [14] (§3.1). That line of work did not exist in
a mature form when this design's guardrail for that surface was first
specified as a lint check run after generation. If a grammar for that
low-level language were written once, incorrect output would become
impossible to produce rather than merely possible to catch afterward —
worth reopening now that the tooling exists to make it real, not just a
nice idea.

**7. Put what matters at the front or the back, never the middle — and
name it.** A model working with a long document reliably favors
information at the very start or the very end, and loses accuracy on
information placed in the middle, even when the entire document fits
comfortably inside its context window [11] (§3.1). Both this paper and
the internal document it describes already followed that instinct without
naming it: warnings and orientation material sit at the top of each, not
partway through a numbered list where a careful reader would still find
them but a skimming one might not. Naming the convention explicitly is
what makes it something the project can apply forward, deliberately,
rather than something it happens to have gotten right twice by habit — in
particular to things the system generates for another agent to read
later, where a rendered configuration file or the plan behind a proposed
change should place its highest-stakes fields, what it is allowed to
touch and when it expires, at a fixed, predictable position, rather than
wherever the code producing the file happens to emit them.

**8. No format shows a consistent generation-reliability advantage —
guard YAML's own ambiguities instead of switching formats.** A controlled
comparison of structured-output formats across several models and tasks
finds no format that wins consistently; in at least one tested case YAML
outperformed JSON [16]. That rules out a blanket format-preference
argument for the Site Model's fallback-authoring path — used as plain
YAML today, pending the Nix-based authoring frontend of §2.1 — but does
not remove a format-preference-independent reason for caution: YAML's
specification carries ambiguities that have nothing to do with who or
what is writing it. An unquoted `no` parses as the boolean value false
rather than the word; indentation carries meaning invisibly; a key can be
silently redefined through aliasing. A small mechanical check — parse the
file, re-serialize it, and diff against the original — catches exactly
that class of drift before it reaches the compiler, independent of any
comparative claim about model reliability.

**9. A standard agent-orientation file is worth adopting for
interoperability, not for a performance gain it does not have.** A short,
conventionally-named file at a repository's root that briefs an AI coding
agent before it starts work is now read natively by essentially every
major coding agent — a real, verifiable adoption fact. The dedicated study
of whether such files actually improve agent performance found they
generally do not: task success was not improved by either developer-
written or model-generated context files, inference cost rose by more
than a fifth on average, and model-generated files specifically performed
worse than supplying no context file at all [17]. Where such a file is
added, the interoperability benefit alone justifies it, and it should be
minimal and hand-written rather than generated — but it should not be
budgeted for, or defended, as a productivity intervention, because on
current evidence it is not one.

Together, these nine are the concrete shape §3's rule takes once applied
past the level of a general design principle. Most strengthen a mechanism
already in place; one (item 3) catches a place the rule was not yet
applied to itself; and one (item 9) is a caution against a plausible-
sounding practice that does not, on the evidence, do what it is commonly
assumed to do — worth stating alongside the other eight for the same
reason §5.4 records a negative result rather than only positive ones:
what a design rule rules out is as much a product of applying it
carefully as what it recommends.

---

## 4. Two places the rule shows up

### 4.1 Dependency inference

The ordering question decomposes into three levels: convergence fixpoint
alone; fixpoint plus explicit `depends_on` where a real constraint exists;
or an inference stage that derives ordering edges from what each declaration
*provides* and *consumes*. This design uses all three. Retry-until-stable is
the substrate. Explicit `depends_on` remains available and wins where it
exists. The primary authoring mechanism is `provides`/`requires`.

Explicit `depends_on` is a global-knowledge
mechanism — to write the edge, the author must already know that someone
else's resource exists and must run first. `provides`/`requires` is a
local-knowledge mechanism: each type states only what it supplies and what
it needs, answerable from inside one file by an agent that has never seen
the rest of the system. A service named `caddy` **auto-provides**
`service:caddy` unless it opts out (§2.9). So the compiler additionally
*derives* edges. §2.6, Example A works this through on a
real fixture pair, attribution and all.

We have one piece of evidence, and it is not hypothetical, though it is worth
being precise about what it evidences. The site's existing Android deploy
chain hand-orders app installation *after* privilege hardening, so an app
added to the install list goes unhardened for a full deploy cycle. The list
contradicts its own stated install-before-harden rule, humans wrote it, and
humans did not catch it. That evidences the broader, weaker claim that
global-knowledge ordering is error-prone for *any* author, machine or human —
not, on its own, that it is specifically worse for machine authors. The
narrower, AI-specific claim rests on §3's argument alone, not on this
instance.

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

### 4.2 Comprehensiveness, default-on with a reasoned opt-out

Bcfg2's configuration goals are comprehensive by convention: the
specification describes every configuration entity on the client, so
anything present on the client and absent from the specification is
unintended by definition, and the client verifies in *both* directions —
no less than specified, and no more. Unspecified state surfaces as an
**extra entry**, a first-class reported category [1, §2.2].

We adopt this per *domain* rather than per client — the app list on a
device, `/etc/ssh`, the services under a given unit-name prefix — because
adopting it fleet-wide on day one is not survivable in an environment that
was never built under it.

A domain is comprehensive unless it opts out, and opting out requires a
reason. AI-authored drift is exactly what extra-entry detection catches,
so the safe default belongs on the detecting side. A bare opt-out boolean
would let an agent widen the unmanaged surface silently; requiring a reason
string makes every gap in coverage a visible, greppable decision rather than
an absence.

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
   a token that another type must name identically is a shared
   vocabulary; agreeing on a vocabulary across files is a coordination
   problem wearing local clothing. The mitigation is auto-provide of
   `service:<name>`, a lookup CLI against the compiled catalog, and compile
   errors that list near-misses (§2.9). Token *kinds* stay a closed enum;
   token *values* stay instance data. That answers "how does an agent find
   the right name" as a mechanism. Whether authors actually use the lookup
   instead of guessing is untested.
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
administrator trust. Here the device's JSONL capture
(and the agent's rebuildable SQLite index) is authoritative and any central
view is an optional, best-effort push.

We are aware this is the decision most likely to be wrong. The grounds are in
§2.4, and the honest summary is that we currently have *no consumer* for a
central copy: no compliance requirement obliges a queryable fleet-wide view,
so building one out would be infrastructure without a customer at this
design's scale (§1.1) — not that one is unbuildable. A path to a fleet-wide
view already exists and costs nothing new to stand up: a subset of each
device's local index pushes, best-effort and eventually consistent, into
the observability stack (Vector/OpenObserve/Grafana) this fleet already
runs for other purposes. What makes the device the record of truth is that
this path is optional and never authoritative, not that it is absent. "No
consumer yet" is exactly the reasoning that LISA '05 argues against
elsewhere, which is why §6.4 records the same paper telling us to build
reporting *early*. We may be applying one of its findings and ignoring
another.

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
every management path to that device permanently. Without an interlock,
only a safe default and a comment would prevent it. We had characterized
this as inexpressible in a catalog, which is true, and had left it there.

Bcfg2 Actions are the shipped precedent for exactly this shape — the
load-bearing sentence [4, §A.2.1]: *unless exit status is ignored, a failing
pre-action prevents modification of entries in the enclosing bundle.*

That is a guard with a defined blast radius: not an edge in a graph, and not
a bare `if`. We make it a first-class Site Model field compiling to a
CFEngine guard class plus a bundle-scoped refusal, which turns "the VPN must
be authenticated before lockdown may be enforced" from a safe default plus a
comment into a stated precondition. The bundle is simultaneously the
grouping unit and the re-verification scope, also following Bcfg2 [4, §2.2.1].

Because the blast radius and the reporting are the whole point, the schema
encodes them as required constants rather than author-settable fields — an
author who could narrow either one could reintroduce the bug the mechanism
exists to close. §2.6, Example B renders this one end to end, from the
schema instance to the guard, and Example C is the same mechanism executing:
a real, non-dry-run `cf-agent` run refusing a gated service because its
precondition genuinely failed. It is the only claim in this paper that has
been demonstrated rather than argued.

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
  buys administrator trust — directly applicable to any site where more than
  one administrator can act unilaterally on shared infrastructure.

### 6.3 Revision stamping

LISA '06's change is small and mechanical: stamp every generated client
configuration with the repository revision, keep a log of what was served
when, and carry that revision into every statistics upload. We already have
the identifier — the signed release and its manifest — so this is
one column in the row schema, not an integration. Every row records the
release that produced it and each device records which release it is
converged to.

What it buys, per the paper: the desired state of any device at any past time
becomes reconstructible, "did this break after the last release" becomes a
query rather than an argument, and "which hosts were exposed, over what
window, and when were they patched" becomes answerable. Given a fleet whose
devices are routinely unreachable, the reconstructibility is worth more here
than in the paper's always-on cluster.

### 6.4 Deploy reporting early, and dry-run as the default posture

LISA '05's central finding is not technical: deployment took about four
months of one person's time, and the binding constraint throughout was
administrator *trust*, not tool correctness — with the stated pivot being
that client-side functionality was not sufficient, and that nearly all
subsequent development went into information presentation.

Two practices follow and we adopt both. Their production servers ran in
dry-run nightly and mailed the resulting state to the responsible
administrator, auto-apply reserved for workstations; we make dry-run the
standing posture for the first platform class brought under management: the
primary workstation, which is also the machine that cannot easily be
reimaged. And "deploy reporting early, not last" reframes our local JSONL
capture plus a trivial "what changed, what is dirty, what am I converged to"
view as an **adoption requirement rather than an observability nicety** —
which is the argument against sequencing it last because nothing consumes it
yet.

### 6.5 What did not transfer

XML as the configuration language and the plugin taxonomy built around it;
the client/server render-on-demand topology (§5.2); and LISA '06's FSM change
orchestration over repository revisions *as a coordinator*. The last one is
the interesting rejection: expressing cross-machine sequencing as a state
machine over *releases* rather than as edges in a per-host catalog fits our
release train unusually well, but the paper is honest that administrators
must enumerate all contingencies as discrete states, that time in any state
is unbounded, and that one down client can stall a workflow. For a fleet
whose devices are routinely unreachable, that last property is disqualifying
as a coordinator. Cross-machine help is instead a **peer action**: the
target declares an operation it cannot do locally; any helper with the
capability and on the target's peer allowlist may do it; stall is local.
The FSM is a *view* reconstructed from JSONL plus optional attestations,
never a lock. "Wait until the server is serving the new export" is a local
probe or a wait for a signed apply-attestation, not a distributed lock.

One piece we expect to want verbatim is `altsrc` — binding an entry as if it
had a different name, so that two paths share one source. Termux's
`$PREFIX`-relative layout against Linux and macOS absolutes is the same
problem `/etc/hosts` versus `/etc/inet/hosts` was.

---

## 7. Building on CFEngine: what the substrate cost

This section reports the only measurement in this paper. It is not a
measurement of our design, and we did not set out to make it.

§2.2 commits this architecture to a single bet: that the right place to put
a compiler's output is CFEngine's own JSON data-injection layer, so that the
promise text stays generic and every site-specific fact arrives as data.
Making that bet concrete meant pushing more traffic through `def.json` and
`host_specific.json` than a textbook CFEngine deployment does, where a
policy server distributes policy *text* and augments carry a comparatively
thin slice of variables. Each time we leaned on the layer, it broke.

### 7.1 What we found

As of 2026-08-18 we have **twenty-six pull requests open** against
`cfengine/core` (twenty) and `NorthernTechHQ/libntech` (six), tracked as
`CFE-4715`–`CFE-4740` in the upstream Jira. Twenty-three carry a defect fix;
two are features (`--simulate-json`, and retaining the simulate chroot) and
one is pure test coverage. An audit of every branch submitted as of that
date found sixteen of seventeen shipping a test, with the single gap
documented on the pull request rather than quietly left; the bar throughout
has been **discrimination** — showing the test fails without the fix and
passes with it — rather than the test's mere existence. The complete
register, with measurements, branches, review panels and the corrections our
own claims needed, is
[`docs/architecture/upstream-register.md`](../architecture/upstream-register.md).

**Ten of the defects are in the data path this design depends on.** Three of
those stop the run before a single promise is evaluated, dropping the host to
failsafe, on input a correct compiler would legitimately emit:

| Ticket | Defect | Offered as |
| --- | --- | --- |
| CFE-4738 | A JSON `null` value in `host_specific.json` segfaults `cf-promises` and `cf-agent` *before any promise is evaluated*, so the host falls to failsafe. Valid JSON; passes CFEngine's own unresolved-variable check | core#6316 |
| CFE-4739 | The same root cause in the `def.json` augments loader, at three separate sites, plus silent array truncation at three more | core#6319 |
| CFE-4724 | A **valid** JSON number in exponent form without a decimal point (`1e-8`, `2e0`) is misclassified as an integer and reaches an exit-on-error path; integers past `long` do the same. Measured on stock 3.27.1: `cf-promises` dies and `cf-agent` falls back to failsafe | libntech#294 |
| CFE-4724 | JSON reals are rendered `%.2f`, so `0.00049` becomes `0.00` — including through mustache templating, which is how this design renders unit files | libntech#294 |
| — | `JsonCopy()` rebuilt reals through a `%.4f` constructor, so *copying* a document changed its values: `3.14159265` → `3.1416` | libntech#294 |
| CFE-4720 | One malformed CMDB entry discards **every other entry in its section**, and the agent then reports no promise failures | core#6320 |
| CFE-4719 | Rejected CMDB data names no key, no value and no file path — the operator is told something was wrong, not what | core#6315 |
| CFE-4722 | A CMDB key containing a dot silently becomes a scope path, with no warning; the verbose log that would reveal the address double-printed the scope | core#6317 |
| CFE-4730 | The JSON string codec is non-conformant in **both** directions: `\uXXXX` above U+00FF is rejected, the escape arm fails to advance the cursor so `{"city":"中国"}` reads back as the literal `u4e2du56fd`, and the writer escapes each UTF-8 *byte* rather than the code point | libntech#293 |
| CFE-4731 | The JSON parser decodes string escapes **twice**, so `{"p": "C:\\temp\\new"}` — valid JSON for an ordinary Windows path — parses to `C:<TAB>emp<NL>ew` | libntech#297 |

The rest are outside the data layer and were found the same way, by needing
something to work: `exec_timeout` not bounding a `commands:` promise on
macOS at all, a promise reported *compliant* after its timeout fired, macOS
having no `process_darwin.c` (which, as a reviewer found and we had not,
means custom promise modules cannot run on macOS at all), and a family of
alarm-lifetime defects around process termination.

### 7.2 Why they were there

The uncomfortable part is not the count. It is that most of these defects
are old, shallow, and in code with tests.

Two mechanisms explain it, and both are instances of this paper's own §3
corollary — prefer machine-checkable to conventional — observed from the
outside rather than applied by us.

**A codec tested only against itself cannot detect a fault its two halves
share.** CFE-4730's reader and writer are exact inverses: the writer emits
per-byte `\uXXXX` escapes and the reader decodes them back to the same
bytes. The library therefore round-trips its own output perfectly, and *no
write-then-read test can catch either half*. The bug is only visible from
outside, against a conformant decoder. There was a test suite; it was
measuring self-consistency and reporting it as correctness. We hold this as
the sharpest practical lesson of the whole exercise, and it generalizes well
past JSON.

**Coverage was absent exactly where this design leans hardest.**
`libutils/mustache.c` is 916 lines with a single entry point, and had **zero
unit tests** — while being the renderer our generic bundle uses to
materialize every unit file. Writing seventeen test cases for it (offered as
libntech#296) surfaced two further defects immediately, which is roughly
what one should expect of any untested nine hundred lines.

Neither observation is a criticism of the maintainers, who have been
responsive; both are observations about where testing effort lands. Paths a
project's own deployment shape exercises heavily get tested. A design that
routes its traffic differently is, in effect, a new test suite — and ours
ran red.

### 7.3 What this does to the argument

We do not think this invalidates §2.3's choice. The properties that made
CFEngine the right substrate — autonomous agents, no required control node,
convergent semantics, a native data layer to compile into — are all still
there, and none of the defects above is architectural. But the choice now
carries a cost line it did not carry when §2.3 was written, and a reader
weighing the same decision deserves both halves:

- **The design currently depends on a fork.** Our builds are made from a
  branch that merges all twenty-three fixes. If none of them merge, `tendcf`
  ships against a patched CFEngine, and that is a maintenance liability we
  would be taking on permanently rather than temporarily.
- **The channel is open but slow.** For weeks the pull requests drew nothing
  but bots. On 2026-08-18 two Northern.tech maintainers reviewed
  substantively, which is the first real engagement and makes the earlier
  "no upstream response" framing false. Both, independently, asked for less
  verbosity. Neither has merged anything yet.
- **We cannot tell you whether twenty-three is a lot.** We have no base
  rate — no comparable count for what a similarly intense month against any
  other mature configuration engine would produce. Anyone reading this as
  "CFEngine is unusually buggy" is reading more than the data supports. The
  defensible claim is narrower and, we think, more interesting: *a
  compile-to-data architecture stresses a different surface than the tool's
  own deployment model does, and that surface was less exercised.*

### 7.4 Who wrote the fixes

This paper's premise is that machine authorship is the primary authorship
model (§3), and §7 is the largest body of work this project has produced. It
would be strange to report it without saying how it was made, so: the defects
were found by AI agents doing ordinary development work against the
substrate, and most of the fixes were drafted by them too.

What made them submittable was not the drafting. It was the gate placed after
it. Every fix had to carry a **discrimination proof** — revert it, watch the
test fail with the exact symptom the ticket describes, restore it, watch it
pass — and most went through an adversarial review panel of two to four
independent models working from a frozen brief, whose findings were binding
rather than advisory. Those panels changed real outcomes. They caught a fix
that sampled a flag before the call that sets it; a platform guard that would
have silently disabled `exec_timeout` on Cygwin, where no CI job would have
noticed; a test that could not have failed for the reason it claimed to
test; and — the category a reviewer should care most about — several of *our
own claims to upstream* that were overstated, including one that forced a
correcting follow-up to an external security team, and one severity
assessment we had to retract and rewrite after re-deriving it.

The bearing on §3 is direct, and it cuts both ways. Machine authors did
produce twenty-three reviewable patches to a mature C codebase, which is more
than we would have predicted. They also produced a steady stream of
confident, plausible, wrong assertions — about severity, about line numbers,
about what had been tested and what merely looked tested. That is precisely
the failure mode §3 names, showing up in prose rather than in configuration,
and it is why this paper's front matter says every number here was
re-derived. The thing that worked was not better authorship. It was making
each claim mechanically checkable and then actually running the check.

### 7.5 The honest reading

Two of this paper's weaknesses got worse, not better, in light of the above.

The first is scheduling. Every hour spent on the substrate is an hour not
spent on the compiler, the executor, or the consent surface — the parts §8
says do not exist. A single unfunded builder who responds to every defect
by fixing it upstream has chosen a research contribution over a working
system, and §9.10's worry about mechanisms that are "the first thing dropped
under pressure" applies with equal force to the schedule itself.

The second is §9.9, the question of whether the whole premise is the wrong
shape. It is worth noticing that none of the ten data-layer defects would
have been caught by any amount of schema design at our layer. They are
faults *below* the surface the schemas defend. If the argument of §3 is that
machine authors fail at global consistency and types are the answer, this
section is a reminder that the types only bind the layer they are written
for, and that everything underneath is still ordinary software with ordinary
bugs.

---

## 8. Status and validation

**Implemented.** Eight schemas in this repository (`schema/`, `examples/`,
`bin/schema_lint.py`). Five are the Site Model and its reporting — including
the fields §4 argues for (`provides`/`requires` per type, `interlocks` per
bundle, `comprehensive` plus `opt_out_reason` per domain) and the report-row
schema of §6.3. Three are the consent contract of §2.5: the goal file, the
structural diff, and the approval record. A lint carries the cross-file
rules JSON Schema cannot state alone — reference resolution, launchd labels
checked against the declared writer prefixes, no prefix nested inside
another — and a second lint checks that every cross-reference in the
document corpus resolves.

Beyond the schemas, two pieces of running code: the **reference projector**
(`bin/projector.py`), which performs §2.5's goal-file-to-augments projection
and is gated in CI against golden bytes so that the agent's eventual second
implementation has an oracle to agree with; and the **generic bundle**
(`policy/tendcf_services.cf`, v1, launchd only), which is the first thing in
this project that CFEngine actually executes.

**Validated in the following narrow but no longer trivial sense.** A lint
that passes on correct input demonstrates nothing about whether it catches
incorrect input, so the contracts are tested against **ninety-two
deliberately broken fixtures**, each of which must be caught, and the lint
fails if any is accepted: fifty-nine schema-level negatives (an opt-out with
no reason, a rogue launchd label, a nested writer prefix, a literal secret
where a key name belongs, a typo'd token kind, an enforce-mode row carrying
an audit-mode outcome, a proposer setting a privileged flag, a migration
that is not a no-op), six byte-level negatives that exist because
canonicalization violations are invisible after a parse (a pretty-printed
twin, duplicate keys, a non-NFC path, `15.0` where `15` belongs), and
twenty-seven projection negatives (a resolved secret value where a name
belongs, a canonified interlock id, a goal file smuggled under `vars`, an
`env` that is not an object). Each rule in the projector's checker has a
fixture that trips **it alone**, which is a stronger property than
per-fixture coverage and was built deliberately: a negative suite where one
fixture trips three rules cannot tell you the other two work.

Two of the original twelve fixtures exposed error messages that were useless
(`is not valid under any of the given schemas`, with no field pointer): the
failure §3 rules out for the compiler, which we had not applied to the
compiler's own tooling.

**Not implemented, and this is still most of it:** the compiler `nix2cf`
itself — merge, conflict check, inference, render — the signed release path,
the on-device validator, the consent surface, peer-action runtime, and every
supervisor adapter except launchd. Remaining Step 0 work: `peer_actions`,
trust-policy shape, generic unit-writers, lookup stub, YAML canonicalize,
and transcribing existing reality as `not-yet-migrated`.

**Nothing is deployed.** No device has been provisioned from factory reset by
this automation. We have no deployment time, no effort figure, no
managed/unmanaged ratio, and no failure data. Examples A and B in §2.6 remain
hand-authored to show the target rendering; only Example C is real.

That gap is not incidental to how this paper should be read. The Bcfg2 papers
report deployment experience with numbers — four months, one person, roughly
three FTE of maintenance before and between a third and a half of an FTE
after, across a division of about two hundred people. We have the design, the
schemas, one bundle, and the substrate findings of §7. On the question that
actually matters — whether any of this is cheaper or more reliable under
machine authorship — we still have an argument and not evidence.

---

## 9. Open questions

These are the places we think the design is weakest, listed so a reader can
go at them directly rather than around them.

**9.1 Is inference justified, or are we rebuilding what Bcfg2 deliberately
declined?** §5.1 states our case and three ways it fails. The version of
this question we most want answered: is the convergence fixpoint *already*
the local-knowledge mechanism, making `provides`/`requires` a strictly worse
answer to a problem that was already solved?

**9.2 Is the writing rule an argument or a hypothesis?**
We have one confirming instance (§4.1's hand-ordered chain contradicting its
own rule) and no counter-instances, which is a suspiciously good record for a
rule this load-bearing. What would a counter-instance even look like — a
place where forcing an author to state a global constraint is what *caught* a
bug?

**9.3 Do `not-yet-migrated` counts actually get ground down, or accumulate?**
The Bcfg2 deployment ground 2308 unmanaged entries down over months with a
person whose job that was. A fleet within this design's envelope (§1.1) has
no such role by construction. If the count only ever rises, the metric is
decoration and default-on comprehensiveness is a permanent tax with no
payoff.

**9.4 Is per-domain the right granularity for comprehensiveness?** Bcfg2's is
per-client and by convention. We chose per-domain to make partial adoption
survivable, but a domain is a boundary someone has to draw, and a badly drawn
one hides drift inside itself just as effectively as opting out would.

**9.5 Is local-first the wrong call?** §5.3. We have no consumer for a
central copy today, but "no consumer yet" is precisely the reasoning LISA '05
warns against, and we are taking one of its findings while declining another.

**9.6 When a genuinely global question arrives, is querying reachable
devices and treating the rest as unknown enough?** The design already
chooses that path over trusting a stale aggregate (§2.4). The best-effort
Vector/OpenObserve/Grafana sync exists and is explicitly not authoritative.
The open question is whether the chosen answer is *sufficient* for a
question with a real yes/no, not whether a dashboard should be the record
of truth.

**9.7 Does spurious-edge provenance actually work?** We claim attribution
turns "why is this waiting?" into a query. Nobody has run it. If it does not
work, inference has a silent failure mode and §5.1's argument gets much
worse.

**9.8 Does the goal-file schema keep up with real operations?** There is no
capability list to outgrow, and coverage closes by construction — compiler
and validator share one schema and fail together — so the escape-hatch
pressure does not disappear, it relocates: the way to get a change out
without extending the schema is to declare a domain `not-yet-migrated`. That
is question 8.3 wearing a different hat.

**9.9 Is the whole premise the wrong shape?** The design optimizes for
machine authors on the assumption that they are the primary authors and that
their weakness is bounded context. If the real weakness turns out to be
something else — plausible-looking output that type systems do not catch,
say — then we have hardened the wrong surface, and the schemas are a
Maginot line. §7.4 is one reason to take this seriously: none of the ten
data-layer defects found under this design would have been caught by any
amount of schema work at our layer.

**9.10 Is a diff something a person can actually consent to?** "One service
installed, nothing else" is a sentence someone can hold in their head.
"Forty-one entries changed across your goal file" is not. Everything that
makes a large diff holdable — the on-demand provenance query, display
grouping, the briefing itself — is advisory machinery that never widens what
the validator accepts. That is what keeps it safe, and also what makes it the
first thing dropped under pressure. The test is countable once real diffs
exist: how many entries a typical release touches, and how often a person
reads past the first screen.

**9.11 Do the total-diff events stay rare?** First adoption is bounded by what
it may claim, and a schema migration is valid only if it changes nothing. But
a project with high schema churn still hands its reviewer a recurring
"everything moved, this one is fine" event, which is training for exactly the
rubber stamp the consent gate exists to prevent. Count migration releases per
year; if that number is not small, the ceremony is being spent.

**9.12 Does refusing actually cost the proposer anything?** A refusal buys a
re-render, not a stalemate — deliberately, since the alternative is a partial
apply of a state nobody checked. But nothing stops the same bundle being
offered again, and a patient proposer wins once. Our answer is that persistent
re-offers are visible in the record. Whether visibility is enough when the
proposer and the person are the same operator is untested.

**9.13 What protects the stored baseline?** The device's copy of the
currently-approved goal file is the root of the gate: everything is diffed
against it and every approval binds to it. Corrupt or swap it and the device
either refuses everything or — worse — presents a first-adoption-shaped total
diff and launders an arbitrary state through the ceremony meant for day one.
Integrity-protected storage is easy to write down and platform-specific to
build, and Android under Termux is the awkward case.

**9.14 What holds the policy tree — which is code — inside the reviewed
state?** The generic bundle of §2.6, and any hand-written policy alongside it,
are what turn a goal file into promises. Nothing about the diff constrains
them unless the goal file carries the policy tree's digest as a privileged
region. That is an obligation on a schema not yet written, not a property the
design has today — and §7 makes it sharper, since that policy tree now sits on
top of a patched substrate.

**9.15 Can the consent gate be made to mean what it says?** §1.1 states the
limit and names the smallest fix. Whether a device-local trust root the
release path cannot write is buildable across macOS, Linux and Android by one
person is open, and the rest of the consent layer rests on the answer.

**9.16 What confirms that a change took effect?** A device can compare
documents, and CFEngine can show what a run would change to files and
packages, but "the new unit is loaded and running" is not something the device
can confirm back to the person who approved it. That gap is permanent at this
layer, and every confirmation this design offers has to be read with it in
mind.

Token discovery (how an author finds the right name) is a mechanism
(§2.9), not an open question. Whether authors actually use the lookup and
the error catalog is still untested.

---

## 10. Conclusion

We have described a configuration management architecture built on treating
machine authorship as a first-order design constraint, and deriving from it
a rule: prefer local knowledge to global. That rule itself is not novel: it is a
machine-authorship instance of a local-reasoning-for-global-properties
pattern with decades of standing in programming-language theory [9], and
Tratt [10] argues the same design move for AI-generated code in general,
independently of and roughly concurrently with this draft (§3.1). What we
claim as new is narrower — applying that rule to a concrete
configuration-management architecture for a heterogeneous fleet. The rest is
composition:
a data spine in layered repos, a pure compiler into CFEngine's own data
layer, per-device JSONL capture with an agent-owned SQLite index, a signed
plan the executor may not exceed, per-device trust, peer actions, and a
BYO advisor slot, with four of its load-bearing ideas taken from Bcfg2 and
credited above. We do not claim
that composition itself as novel, only as uncommon: compiling into an
existing tool's native data layer, rather than shipping a new client, is not
the path most configuration-management projects take.

One thing did change while this was being written, and it was not something
the design predicted. §7 reports twenty-three defect fixes now open against
the substrate, ten of them in the exact data layer this architecture compiles
into and three of them fatal to a run before it evaluates anything. We offer that less as a result
about CFEngine — we have no base rate, and say so — than as a result about
compile-to-data as a strategy: routing a tool's traffic through a path its own
deployment model uses lightly is, in practice, a way of discovering that path
was under-tested. If there is a transferable finding in this paper, it is
probably that one and not §3's rule.

We think §4's rule is right and §5.1's departure is the honest cost of it. We
would rather be told otherwise now, while the schemas are days old and nothing
is deployed, than after a fleet is running on it.

---

## Acknowledgements

Thanks to Narayan Desai and his co-authors on the four Bcfg2 papers this
work draws from — Andrew Lusk, Rick Bradshaw, Rémy Evard, Scott Matott,
Sandra Bittner, Susan Coghlan, Cory Lueninghoener, Ti Leggett, John-Paul
Navarro, Gene Rackow, Craig Stacey, Tisha Stacey, and Joey Hagedorn — whose
work is the source of §6 in its entirety and much of the design vocabulary
used throughout.

## References

[1] N. Desai, A. Lusk, R. Bradshaw, and R. Evard. *BCFG: A Configuration
Management Tool for Heterogeneous Environments.* IEEE International
Conference on Cluster Computing (CLUSTER '03), 2003.

[2] N. Desai, R. Bradshaw, S. Matott, S. Bittner, S. Coghlan, R. Evard,
C. Lueninghoener, T. Leggett, J.-P. Navarro, G. Rackow, C. Stacey, and
T. Stacey. *A Case Study in Configuration Management Tool Deployment.*
19th Large Installation System Administration Conference (LISA '05), 2005.

[3] N. Desai, R. Bradshaw, J. Hagedorn, and C. Lueninghoener. *Directing
Change Using Bcfg2.* 20th Large Installation System Administration
Conference (LISA '06), 2006.

[4] N. Desai and C. Lueninghoener. *Configuration Management with Bcfg2.*
Short Topics in System Administration #19, USENIX Association, 2008.

[5] M. Burgess. *Cfengine: a site configuration engine.* USENIX Computing
Systems, 8(3), 1995.

[6] M. Burgess and J. A. Bergstra. *Promise Theory: Principles and
Applications.* 2014.

[7] A. Couch and Y. Sun. *On the Algebraic Structure of Convergence.*
DSOM 2003.

[8] W. Fu, R. Perera, P. Anderson, and J. Cheney. *µPuppet: A Declarative
Subset of the Puppet Configuration Language.* ECOOP 2017.

[9] A. Banerjee, D. A. Naumann, and S. Rosenberg. *Local Reasoning for Global
Invariants, Part I: Region Logic.* Journal of the ACM, 60(3), Article 18,
2013.

[10] L. Tratt. *Local Reasoning for Global Properties.* tratt.net blog, July
2026. https://tratt.net/laurie/blog/2026/local_reasoning_for_global_properties.html

[11] N. F. Liu, K. Lin, J. Hewitt, A. Paranjape, M. Bevilacqua, F. Petroni,
and P. Liang. *Lost in the Middle: How Language Models Use Long Contexts.*
Transactions of the Association for Computational Linguistics, 2023.
arXiv:2307.03172.

[12] P. T. J. Kon, J. Liu, Y. Qiu, W. Fan, T. He, L. Lin, H. Zhang, O. M.
Park, G. S. Elengikal, Y. Kang, A. Chen, M. Chowdhury, M. Lee, and X. Wang.
*IaC-Eval: A Code Generation Benchmark for Cloud Infrastructure-as-Code
Programs.* Advances in Neural Information Processing Systems 37 (NeurIPS
2024), Datasets and Benchmarks Track, pp. 134488–134506.

[13] R. Nekrasov, S. Fossati, I. Kumara, D. A. Tamburri, and W.-J. van den
Heuvel. *IaC Generation with LLMs: An Error Taxonomy and A Study on
Configuration Knowledge Injection.* arXiv:2512.14792, December 2025.

[14] K. Park, T. Zhou, and L. D'Antoni. *Flexible and Efficient
Grammar-Constrained Decoding.* arXiv:2502.05111, 2025.

[15] R. Wang and L. Zhang. *Documentation Retrieval Improves Planning
Language Generation.* arXiv:2509.19931, 2025.

[16] Z. R. Tam, C.-K. Wu, Y.-L. Tsai, C.-Y. Lin, H. Lee, and Y.-N. Chen.
*Let Me Speak Freely? A Study on the Impact of Format Restrictions on
Performance of Large Language Models.* arXiv:2408.02442, 2024.

[17] T. Gloaguen, N. Mündler, M. Müller, V. Raychev, and M. Vechev.
*Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for
Coding Agents?* ETH Zürich, arXiv:2602.11988, 2026.

[18] NixOS project. Module system compiling to `systemd` unit files
(`nixos/modules/system/boot/systemd.nix`). https://github.com/NixOS/nixpkgs

[19] `nix-darwin` project. Nix module system compiling to `launchd` agents
and macOS `defaults`. https://github.com/nix-darwin/nix-darwin

[20] `cdk8s` project. Typed-language synthesis to Kubernetes YAML.
https://github.com/cdk8s-team/cdk8s

[21] HashiCorp. *CDK for Terraform (cdktf).*
https://github.com/hashicorp/terraform-cdk — deprecated December 10, 2025.

[22] Flux / GitOps Toolkit (Weaveworks; CNCF since 2019). Pull-based,
git-synced deployment with no push and no externally-reachable control
plane. https://github.com/fluxcd/flux2

[23] CFEngine documentation. "Client server communication" (standard
hub-and-spoke deployment) and installation/bootstrap documentation
(self-bootstrap to policy hub). https://docs.cfengine.com

[24] balena. *Offline Updates: Update balena Devices Without Internet.*
https://blog.balena.io/offline-updates-make-it-easier-to-update-balena-devices-without-the-internet/

[25] M. Kleppmann, A. Wiggins, P. van Hardenberg, and M. McGranaghan.
*Local-first software: you own your data, in spite of the cloud.* Onward!
2019.

[26] J. Samuel, N. Mathewson, J. Cappos, and R. Dingledine. *Survivable Key
Compromise in Software Update Systems.* ACM CCS 2010. (The Update Framework.)

[27] E. Dolstra. *The Purely Functional Software Deployment Model.* PhD
thesis, Utrecht University, 2006.

[28] K. G. Srivatsa, S. Mukhopadhyay, G. Katrapati, and M. Shrivastava.
*A Survey of using Large Language Models for Generating Infrastructure as
Code.* arXiv:2404.00227, 2024.

[29] The defects and contributions of §7, filed as CFE-4715–CFE-4740 in the
CFEngine Jira (https://northerntech.atlassian.net/browse/CFE-4715) and offered
as pull requests against https://github.com/cfengine/core and
https://github.com/NorthernTechHQ/libntech during August 2026. Measurements,
branches, review panels and the corrections our own claims required are in
[`docs/architecture/upstream-register.md`](../architecture/upstream-register.md).
