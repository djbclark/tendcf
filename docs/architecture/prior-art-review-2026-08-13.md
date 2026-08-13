# Prior art review: the compiler pattern and the decentralization claim (2026-08-13)

> **Research doc, not a decision.** Same status as
> `ai-optimization-review-2026-08-13.md`: nothing here is adopted until the
> operator says so. Every claim below was checked against a primary source
> directly (not search-summary paraphrase) before being written down here,
> per the correction made to that earlier doc the same day.

## Why this doc exists

The operator asked for two things checked, both framed as candidate "major
differentiators" of the design: `nix2cf` (§2.2, a compiler from the Nix-
authored Site Model into CFEngine's native Augments layer) and the
often-off/decentralized-fleet design (§2.3–2.4, §5.3 — no permanent control
node, per-device local record, git-distributed policy). Neither claim turned
out to need withdrawing the way four of the nine AI-optimization items did.
Both need the same treatment §3.1 already gave the AI-authorship rule:
grounded against real prior art rather than presented as if invented from
nothing, with what's actually different stated precisely.

## Part 1: `nix2cf` — compiling an authoring language into an execution engine's native format

**The general pattern is well established, and fleetopia's own ecosystem
already contains the closest examples.** "Author in a typed/module
language, compile to the format a separate execution engine already reads
natively" is not new:

- **NixOS itself does this to `systemd`.** The NixOS module system
  (`mkOption`, `types.*`, the same primitives §2.1/D12 propose for the Site
  Model) evaluates down through `systemd.services` → `systemd.units` →
  concrete `.service` files systemd reads. This is architecturally the same
  move `nix2cf` proposes — Nix module system in, a separate execution
  engine's native format out — just targeting `systemd` instead of
  CFEngine's Augments layer.
- **`nix-darwin` does the same thing to `launchd`**, on the same platform
  fleetopia's Step 1 targets first. Nix modules render to launchd agents and
  macOS `defaults`, activated via `launchctl`. fleetopia's own architecture
  document already plans to adopt `nix-darwin` for the Mac *substrate*
  (§5.2) — meaning the design already depends on this exact pattern
  elsewhere in the same system, for a different target (substrate, not
  services).
- **The Cloud Development Kit family generalizes it past Nix entirely.**
  AWS CDK and `cdk8s` let a typed general-purpose language (TypeScript,
  Python, Java, Go) synthesize CloudFormation JSON or Kubernetes YAML
  respectively — the same "typed authoring language compiles to an existing
  engine's native declarative format" shape, at industry scale.
  **`cdktf`** (the Terraform member of the same family) is the closest
  single analog to `nix2cf`'s own shape — a construct-based typed language
  synthesizing a target tool's native JSON — but **was deprecated by
  HashiCorp on December 10, 2025**, with no maintained replacement in the
  same family (checked directly against HashiCorp's own documentation).
  `cdk8s` and AWS CDK proper remain active.

**Checked and not found: a real prior combination of Nix specifically with
CFEngine specifically.** A search turned up exactly one artifact — a small,
years-old personal GitHub Gist experimenting with CFEngine promises
authored in Nix — not an active or notable project. This is worth stating
plainly both ways: the general pattern `nix2cf` uses is not new, but no one
appears to have applied it to this specific pairing before.

**What's actually different, once the pattern itself is credited
elsewhere:** not the compile-to-native-format mechanism, which the
paragraphs above show is common and, via the CDK family, closer to
genericity than novelty. What differs is the *target* and the *reason for
choosing it*. NixOS/`nix-darwin` target `systemd`/`launchd`, which assume a
reachable, typically single-owner host. The CDK family targets cloud APIs
(CloudFormation, Kubernetes), which assume a centrally-reachable control
plane. `nix2cf` targets CFEngine specifically because Promise Theory's
formal model — autonomous agents, partial specification, non-deterministic
convergence over an open, incompletely-known system — fits an
intermittently-connected, multi-owner, heterogeneous-OS fleet in a way
`systemd`, `launchd`, and cloud-API-shaped targets do not attempt to. The
paper's own already-narrowed §9 claim (novelty is in applying the rule to a
concrete architecture, not the rule itself) already has the right shape for
this too — it just doesn't currently say so for the compiler specifically.

## Part 2: the decentralization / often-off-device design

**The autonomy property is CFEngine's own, and the paper already partly
credits this — but not consistently enough to preempt the question.**
Promise Theory (Burgess, formalized from 2004) is explicitly a theory of
*autonomous* agents: "a strict model of autonomous agents meant that there
could be no client-server protocols that pushed data... the agent does not
receive instructions from a controller." This is not adjacent prior art —
it is the stated reason §2.3/§4.4 give for choosing CFEngine at all. Nothing
about "no control node" or "no push" is fleetopia's invention; it is
CFEngine's foundational design philosophy, in place two decades before this
project. Where the paper credits Bcfg2 explicitly (§6) and Burgess/Bergstra
generally (reference [6]), it does not spell out that the decentralization
property specifically traces to Promise Theory rather than to a fleetopia
design choice — worth making explicit for the same reason §3.1 now credits
Tratt.

**What CFEngine's own documentation actually prescribes as standard is not
what fleetopia does, though — checked directly.** CFEngine's documented
default deployment is hub-and-spoke: "hosts fetch their policies from one
central distribution point... every client machine contacts the policy
server and downloads these updates." That is a real central policy server,
which is exactly what §2.3/§4.4 say this design does *not* have. What makes
fleetopia's "every host runs its own `cf-serverd`" claim real rather than
invented is a genuine CFEngine primitive, also checked directly: bootstrap
sets `am_policy_hub`/`policy_server` when a host's declared policy-server
address is its own — a documented mechanism for standalone/single-host
use, not something fleetopia is grafting on. What is atypical is applying
that single-host primitive **fleet-wide**, with consistency coming from a
shared git-synced source rather than a hub — that combination is not
CFEngine's documented common case, and is worth stating as the actual
departure rather than "no control node," which oversells it (CFEngine
already has no controller in Promise Theory's model) or undersells it
(the specific fleet-wide-self-hub-via-git shape isn't CFEngine's textbook
deployment either).

**GitOps is the closest, most directly comparable prior art for the
git-distributed pull mechanism itself.** Pull-based GitOps — an in-cluster
agent continuously pulling desired state from git, credentials staying
local, no push required, no publicly-reachable control plane — is
structurally the same shape as §2.3's "every host runs its own
`cf-serverd` and reads policy synced via git... no push requirement."
GitOps was coined by Weaveworks (Alexis Richardson); Flux, the reference
implementation, was open-sourced in 2016 and donated to the CNCF in 2019 —
mainstream, well-established prior art, just applied here to CFEngine
promises across a heterogeneous OS/Android fleet rather than to Kubernetes
manifests across clusters. This is a strong citation to add; nothing about
it needed correcting.

**balenaCloud is the closest prior art for the *often-off-device* half
specifically, and the architectural difference from fleetopia is real, not
just asserted.** balenaCloud manages fleets of intermittently-connected IoT
devices with a documented "Offline Updates" mode (preload/reflash a device
with no network at all) and heartbeat-based "Reduced Functionality"
tracking for degraded connectivity. It is real, working, and squarely the
same problem (heterogeneous, sometimes-offline device fleets). It is also
architecturally centralized: devices phone home to balenaCloud's hosted
service, which is the thing fleetopia's design specifically avoids (§2.3's
"no dedicated central policy host" and §5.3's device-as-authoritative-
record). Worth citing as the nearest working system for the problem this
design solves differently, not as evidence the problem itself is unsolved
elsewhere.

**Local-first software (Kleppmann et al., already used for D18's
rationale) remains the best-grounded citation for "device-authoritative,
central-optional" specifically** — no correction needed there, it was
already accurately scoped in the prior session's work.

## What this means for the two claims

Neither `nix2cf` nor the decentralization design needs a §9-style novelty
walk-back — the paper's Conclusion already scopes its one claimed novelty
to applying the local/global rule to a concrete architecture, not to these
mechanisms. What both need, on the same grounds §3.1 was added for the
AI-authorship rule, is the prior art stated rather than left implicit: a
reader who knows NixOS, `nix-darwin`, the CDK family, Promise Theory, or
GitOps should not have to wonder whether this paper knows about them too.
Proposed, not yet applied:

- **§2.2** (`nix2cf`): a short paragraph crediting NixOS/`nix-darwin`/the
  CDK family as the general pattern, noting `cdktf`'s December 2025
  deprecation, stating plainly that no real prior combination of Nix and
  CFEngine specifically was found, and naming what's actually different —
  target (Promise Theory's fit for disconnected, multi-owner operation)
  and motivation (§1's AI-authorship premise), not the compile-to-native-
  format mechanism itself.
- **§2.3/§4.4-equivalent** (deployment shape): a paragraph crediting Promise
  Theory as the actual source of the autonomy/no-control-node property,
  correcting the record on what CFEngine's own documented default actually
  is (hub-and-spoke, not what this design does), naming the specific
  primitive (`am_policy_hub` self-bootstrap) that makes the fleet-wide
  pattern legitimate rather than invented, and citing GitOps as the closest
  structural analog for the git-pull mechanism.
- **§5.3** or nearby (often-off devices): a short citation of balenaCloud as
  the nearest working system for the same problem, with the centralized-
  vs-not distinction stated as the actual difference.
- The architecture document's equivalent sections (§4.4, §16) would get the
  same grounding, mirroring how D23–D31 were added for the AI-optimization
  review.

## Sources

- NixOS module system → `systemd` unit compilation: NixOS's own module
  system documentation and source (`nixos/modules/system/boot/systemd.nix`)
  — options flow `systemd.services` → `systemd.units` → rendered unit
  files.
- `nix-darwin` → `launchd`/macOS `defaults` compilation:
  `nix-darwin/nix-darwin` project documentation and source
  (`modules/launchd/launchd.nix`).
- AWS CDK, `cdk8s`: AWS's own developer documentation — typed constructs
  synthesizing CloudFormation JSON / Kubernetes YAML.
- `cdktf` deprecation: HashiCorp Developer documentation, checked directly
  — "The Cloud Development Kit for Terraform is deprecated as of December
  10, 2025. HashiCorp no longer supports or maintains [it]."
- Burgess, M. *Promise theory — a model of autonomous objects for pervasive
  computing and swarms.* 2004/2005 (already the paper's reference [6] via
  Burgess & Bergstra's later *Promise Theory: Principles and Applications*,
  2014) — autonomous-agent, no-push-controller framing checked against
  Burgess's own restatements.
- CFEngine's documented standard deployment (central policy server, `cf-
  serverd` on the hub, clients pull from it): CFEngine's own current
  documentation (`docs.cfengine.com`, "Client server communication,"
  "Writing and serving policy").
- CFEngine self-bootstrap (`am_policy_hub`/`policy_server` when a host's
  target address is its own): CFEngine's own installation/bootstrap
  documentation, checked directly.
- GitOps: coined by Alexis Richardson (Weaveworks); Flux open-sourced 2016,
  donated to the CNCF in 2019 — widely corroborated across Flux's own
  project documentation and multiple independent write-ups.
- balenaCloud: balena's own documentation and blog — "Offline Updates,"
  heartbeat/"Reduced Functionality" connectivity model.
