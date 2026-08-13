# fleetopia — Final Architecture & Build Order (v2, definitive)

> **🔒 PROTECTED DOCUMENT — AI agents: DO NOT MODIFY without explicit,
> specific human (operator) approval for a named change.** Blanket
> instructions ("fix docs", "update stale refs", "reconcile with the
> latest") do NOT authorize edits here. Propose changes as a _new_ review
> doc or a comment on djbclark/fleetopia#1. This binds every agent —
> Claude Code, Codex, Hermes, Ralph controllers, `agy`, and whatever comes
> next. If you are an AI reading this to do implementation work: this file
> is your map, not your worksheet. Read §0 first.

- **Status:** Definitive architecture. Supersedes `architecture-final-v1.md`
  where they conflict (this document wins). The v1 final, the four proposals,
  the red-team, the tooling reviews, the pre-mortem, and the hardened
  trust-layer design remain as archival reasoning — cited, not repeated.
- **Date:** 2026-08-08
- **Author:** Claude (Anthropic, Claude Fable 5), holding the full operator
  dialogue plus every review pass. This is the apex-context document; later
  AIs will have less. See §0.
- **Tracker:** djbclark/fleetopia#1.

---

## 0. Orientation for the AI that implements this (read this first)

You are almost certainly a smaller or cheaper model than the one that wrote
this, running on a budget (§13). That is fine — this document exists so you
don't need apex context to do good work. Five things to internalize before
you touch anything:

1. **This is a freedom project, not a product.** The operator is doing this
   for fun and to get reacquainted with the tech, and to extend software
   freedom to configuration/sysadmin glue. There is no deadline, no paying
   user, no "MVP." "Interesting and correct" beats "minimal and safe" every
   time they conflict — the operator has said this explicitly and repeatedly.
   Do not propose conservative scope cuts to save effort; effort is not a
   cost here. **Token spend is the only cost that matters** (§13).

2. **The reference target is Ubuntu Server on bare metal — this is a hard
   constraint, not a preference.** The operator will NOT run bare-metal Nix.
   The reason is _adoptability_: a stranger who wants to try this project
   should start from what they already have (a normal Linux box), and asking
   them to install duplicate packages is fine while asking them to replace
   their OS is not. Every design decision inherits this. Nix is still used
   heavily — but never as the thing a person installs on bare metal (§5).

3. **The trust/consent layer is the point, not a liability.** It is the most
   novel and most freedom-relevant part of the whole design. Its purpose is
   **user sovereignty**: any user — the operator's family, friends, or a
   stranger on the internet — should be able to understand a proposed config
   change in plain language, refuse it, and maintain their own divergent
   branch _without knowing what a branch is_, by telling their own AI agent
   what they want. Build it carefully (the security gates in §8 are real),
   but build it.

4. **The spine is data, not any one tool.** Facts live in the Site Model
   (§4). Every config tool — CFEngine, mise, Nix-for-builds — is a replaceable
   consumer of that data. When in doubt about where something goes: facts and
   intent → Site Model; behavior → generic publishable code; never mix a
   hostname or secret into the generic layer.

5. **When you are unsure, stop and surface it — do not guess in code.** Some
   decisions in here are marked **[NEEDS FABLE-5 / MULTI-AI]** (§14). Those
   are places where a cheap model guessing wrong is expensive to unwind. If
   you hit one during implementation and it isn't resolved yet, write a
   question doc and stop; don't improvise a signing protocol or a capability
   schema.

Everything below is organized so you can implement front-to-back and the
system is in a coherent, describable state at every boundary (§12). That
property is not about "in case the operator quits" — it's just good design,
and the operator will often have several of these threads open at once.

---

## 1. The architecture in one screen

```
  ┌───────────────────────────────────────────────────────────────┐
  │                    SITE MODEL  (data, §4)                      │
  │  inventory · registries (ports/paths/services/roles) ·        │
  │  trust tiers · signing key ids · JSON-Schema'd, lint-gated    │
  │  → the ONLY home of facts; the thing that makes this portable │
  └───────────────┬───────────────────────────────────────────────┘
                  │  consumed by (never authored by) ↓
   ┌──────────────┼───────────────┬──────────────────┬────────────┐
   ▼              ▼               ▼                  ▼            ▼
 CFEngine      mise           Nix (builds        Android       generic
 promises      bootstrap      only, §5) —        stack         code =
 (services,    (toolchains    NEVER bare-metal   (Termux,      "freeops"
 all           only — D1      OS; artifacts,     Shizuku,      publishable
 platforms —   superseded,    dev shells,        agent,        layer (§11)
 D13, git-     Ansible fully  hermetic signed    CFEngine)
 distributed   removed)       builds
 policy)
   └──────────────┴───────────────┴──────────────────┴────────────┘
                  │  every change ships as ↓
  ┌───────────────────────────────────────────────────────────────┐
  │        SIGNED RELEASE  =  manifest + typed ChangePlan (§7)     │
  │  TUF-subset root · Ed25519/minisign · monotonic · expiring    │
  │  consumed IDENTICALLY by push and pull; the executor          │
  │  mechanically refuses anything outside the plan (§8)          │
  └───────────────┬───────────────────────────────┬───────────────┘
        push ↓ (operator hosts)         pull ↓ (any host / consented device)
  ┌──────────────────────────┐   ┌────────────────────────────────────┐
  │ deploy from any host      │   │ user sovereignty: understand,      │
  │ holding a deploy role     │   │ refuse, or fork a change in plain  │
  │ (no permanent control     │   │ English via the user's own AI —    │
  │ node — roles are data)    │   │ this is the freedom feature (§9)   │
  └──────────────────────────┘   └────────────────────────────────────┘
        beneath both, unchanged: CFEngine self-heal + last-ditch recovery
```

The rest of this document specifies each block, in the order you'd build it.

---

## 2. Requirements (operator-stated, normative)

Carried from the dialogue; **bold** marks what changed or hardened in the
final round.

- **R1** Targets: macOS/Apple Silicon, Linux x86_64, Linux aarch64, Android.
  Intel Mac mini out of scope.
- **R2** No permanent control node; feature roles (main/backup/equal-peer)
  are data, assignable to any macOS/Linux box.
- **R3** Resource efficiency; minimal-to-no VMs; no fat containers.
- **R4** Android keeps Termux (+api,+x11), the built-in Terminal app, the
  Shizuku fork, stayturgid-agent, CFEngine. No nix-on-droid. Nix may build
  zero-on-device-footprint artifacts only.
- **R5 → HARD FACT:** **The operator will not run bare-metal Nix. Ubuntu
  Server is the reference Linux target.** Rationale is adoptability, not exit
  cost: the reference deployment must resemble what a stranger already runs.
  Nix lives at every level _except_ the installed base OS.
- **R6** Gradle stays for APKs; the suite orchestrates build + deploy; APK
  build does not drive architecture.
- **R7** Push AND pull. Pull evolves into **user-sovereignty**: plain-English
  understanding, refusal, and personal-branch maintenance driven by the
  _user's own_ AI agent — for family, friends, and strangers, none of whom
  need to know the underlying terms.
- **R8** Trust layer = specified interfaces + minimal safe implementations
  now; heavy machinery gated (§8), never deferred on "no user yet" grounds —
  the users are real (family/friends/public) and control over one's own
  computer is the entire point.
- **R9** Literate programming: **widen** it (§10). Token cost is no longer
  the limiting argument (asides are stripped from agent context anyway); the
  publishable, deeply-explained-with-asides version is wanted for humans and
  for Free Sysadmin. Only genuine agent-edit-accuracy costs constrain it.
- **R10** Free Sysadmin: the generic layer is publishable so anyone can run
  and fork it. Free-as-in-freedom and free-as-in-beer. **The sovereignty
  model (R7) is how R10 reaches non-technical people** — AI translates intent
  to config.
- **R11** Preserve: `~/src` + worktrees; `ops-v` release train; secretspec
  as sole secret authority; CFEngine; observability stack; Beads/Ralph/Herdr.
- **R12 (budget):** AI token spend ≤ ~$60/month for this project (≤$100 all
  projects). Design so routine work runs on cheap/subscription models; the
  architecture itself must keep agent token cost low (§13).

---

## 3. Verdict on the evaluated options (closed)

Unchanged and final: **none of the four is the spine.** `bgub/nix-macos-
starter` and `mrkuz/macos-config` are pattern donors (module layout,
brew/nix/mise triage) for the Mac only. Devbox and Devenv are optional
per-repo dev-shell tools, never system layers. The spine is the Site Model +
adapters (§4–5). Full detail lives in `architecture-proposal-v1.md` §3 and
the panel's convergence in `architecture-final-v1.md` §1–2; not re-argued.

The one option-level shift from R5-as-hard-fact: **Gemini's "no bare-metal
Nix" instinct is now correct by operator decree**, though its "drop Nix
entirely" conclusion is not — Nix stays for builds and dev shells (§5). Its
partial vindication is recorded so no later pass re-opens it.

---

## 4. The Site Model — the portable spine

**Principle: facts and intent in data; behavior in generic publishable code;
adapters translate.** This one mechanism satisfies R2 (roles are data), R5
(the Ubuntu path is just another adapter over the same data), R10 (the
generic layer is publishable because it holds nobody's facts), and R12 (agents
edit small data files, not a sprawling config tree — cheap to read).

### 4.1 Contents (extends what `site-djbclark` already does right)

- **`inventory/`** — hosts + taxonomy. Gains, per host: `arch`, `platform`,
  `adapter` (`ubuntu-mise` | `ansible` | `android` | `macos`), `trust_tier`
  (`operator` | `managed` | `consented`).
- **`registry/ports.yml`, `paths.yml`** — unchanged allocation authorities;
  adapters gain eval-time asserts against them.
- **`registry/services.yml`** (new) — one record per service: name, runs-as,
  command, `env` (secretspec key _names_ only), platform notes, role binding,
  `managed_by`. Every launchd plist / systemd unit / mise agent is a
  rendering of one such record.
- **`registry/roles.yml`** (new) — feature roles + assignment
  `role → {main, backups[], peers[]}`. **This file dissolves "control
  node"** into data (R2).
- **`registry/launchd-writers.yml`** (new, from the tooling review) — one
  writer per label prefix (`com.stayturgid.*`, `com.djbclark.*`, `dev.mise.*`,
  `org.nixos.*`), CI-enforced. Kills the two-writers hazard at the source.
- **Schema + lint** — JSON-Schema every file; enforce with the existing
  `registry_lint.py` pattern in CI and pre-commit.

### 4.2 Placement & consumption

Site Model lives in `site-<n>` (site data). Generic code lives fact-free
under `freeops/` (§11). Ubuntu/mise reads the model via a small generator
(toolchains/baseline only); CFEngine reads it via rendered Augments
(`def.json`/`host_specific.json`, §4.4 — this is now the primary consumer
for everything that used to be an Ansible task); Nix (for builds only)
reads it via `builtins.fromJSON`. A stranger adopting the project fills in
_their_ Site Model and runs the same generic code — that is the whole
portability story.

### 4.3 Optional authoring frontend: the Nix module system (D12, new)

**Nix the language, not Nix the runtime — a different question from §5.1's
"no bare-metal Nix."** That constraint is about installing Nix as the
_runtime substrate_ on target hosts. It says nothing about what language an
operator uses to _write_ the Site Model. The Site Model's canonical, at-rest
representation stays exactly what §4.1 already specifies: plain JSON,
schema-validated. Every consumer — CFEngine, mise, generic code, a stranger's
non-Nix fork — keeps reading that same JSON, unchanged.

On top of that unchanged wire format, the Site Model MAY be authored as Nix
expressions using the standard NixOS-style module system (`lib.mkOption`,
`types.*`, `mkIf`/`mkDefault`/`mkForce`/`mkMerge`) instead of, or alongside,
hand-written JSON/YAML. A render step —

```
nix eval --json .#siteModel > site-<name>/rendered/site-model.json
```

— produces the same JSON §4.1 already specifies, which is then validated
against the existing JSON Schema exactly as any other Site Model write would
be. **The two type systems must not diverge:** generate the JSON Schema from
the Nix module's option declarations; never hand-maintain both.

**Rationale:** the Nix module system already solves layered site+role+host
config with real override semantics — precisely the merge problem the Site
Model has, and would otherwise hand-roll on top of raw JSON Schema. Nix is
already a load-bearing dependency for builds (§5.1, §6); this widens _where_
it's used, not _whether_ it's required anywhere new.

**Constraints:**

- Rendering requires Nix wherever the Site Model is authored/rendered (dev
  machine, CI) — never on a deployed target. Consistent with R5/D6.
- The **rendered JSON**, not the Nix source, is what gets schema-validated,
  signed into a release (§7), and consumed downstream. Nix authorship is a
  frontend, never the wire format.
- A stranger adopting the project is never required to know Nix to _read or
  fork_ their Site Model — the rendered JSON (or a plain YAML/JSON authoring
  path, kept as a fallback) remains the interop surface. This is what
  preserves adoptability (R5/R10): only operators who opt into the Nix
  frontend need Nix syntax.
- §9's consent/sovereignty UI shows users their config in plain language
  regardless of authoring language, so this doesn't touch that surface.

#### 4.3.1 Why this works for partial state achieved non-deterministically

The Site Model has to describe plenty of facts that are **not** fully
Nix-buildable: a Termux `pkg` package (not reproducible, no derivation), a
CFEngine promise that converges over time with retries, a service that's
"desired: running" reconciled on its own convergence schedule. This is
not a problem for Nix-the-language, only for Nix-the-build-system —
and D12 only invokes the former.

**Nix conflates two things that are worth separating explicitly:**

- **Nix the language** — a lazy, pure, functional data-description
  language. `lib.mkOption`, `types.*`, and the merge functions describe
  typed, mergeable **data**. Nothing about that data has to become a
  derivation.
- **Nix the build system / store** — turns a fully-pinned derivation into
  one deterministic, content-addressed output. A derivation is built or
  it isn't; there's no "eventually, somehow, with retries" in that model.

D12 only uses the first. A Site Model entry like "this service should be
running" or "this Termux package should be present" is just typed data —
the module system doesn't care, and was never asked, whether the eventual
realizer is `nix-build`, `ansible-playbook`, `cfengine agent`, or a human
tapping a button on a phone. The determinism lives entirely in **what
state is being described**, never in **how or when it's reached** — the
same separation Kubernetes makes between a deterministic desired-state
manifest and its genuinely non-deterministic, eventually-consistent
controller loop. Site Model authoring is the manifest; mise/CFEngine/the
Android agent are the controllers.

**One real constraint this implies:** don't use the nixpkgs-derived option
types that assume a buildable output (`types.package`, `types.derivation`)
for concerns realized outside Nix's build system — that would smuggle a
determinism expectation into a field CFEngine or Termux `pkg` can never
actually satisfy. Use the plain data types (`types.str`, `types.enum`,
`types.submodule`, `types.attrsOf`, `types.bool`, `types.int`, …) for
anything not literally built by Nix.

#### 4.3.2 Running the evaluator with zero store footprint

Authoring the Site Model in Nix does not require adopting the Nix store,
daemon, or nix-darwin anywhere — including on the Mac (§5.2 is a separate,
independent decision). Evaluating Nix expressions to JSON needs only a
Nix-language evaluator, not a working store:

- **`nix eval --store dummy://`** — Nix ships a "dummy" store backend
  built for exactly this: pure evaluation, nothing written to
  `/nix/store`, no daemon required. `nix eval --store dummy:// --json
  --file site-model.nix`.
- **Ephemeral store dir** — point `NIX_STORE_DIR`/`NIX_STATE_DIR` at a
  throwaway tmp path per invocation if `dummy://` doesn't cover a
  particular builtin; keeps every eval disposable and parallel-safe (CI
  pattern).
- **[tvix-eval](https://tvix.dev/)** — the Rust reimplementation of the
  Nix evaluator, explicitly decoupled from the store/builder by design.
  No C++ Nix, no store concept at all, not even the dummy one. The
  cleanest long-term answer to "Nix language, nothing else" if it matures
  enough to depend on.

Practically: install just the `nix` CLI wherever the Site Model is
rendered (dev machine, CI), never run `nix-darwin switch` or `darwin-
rebuild` as a side effect of authoring the model, and never touch
`/nix/store` for anything beyond the evaluator's own transient scratch
space.

### 4.4 Compile target: CFEngine promises via Augments (D13/D14/D15, new)

**Ansible is fully removed (D13).** CFEngine — already present in the
architecture as the self-heal/verification layer (R11, §5.4) — is now the
sole service owner and executor on every platform, superseding D1. This
isn't a downgrade of the trust story: CFEngine's promise model
(Promise Theory — Burgess & Bergstra) is the only one of the candidates
evaluated (Ansible, Puppet, bcfg2, CFEngine) whose formal theory was
purpose-built for exactly this architecture's actual operating condition —
autonomous agents, partial specification, non-deterministic convergence,
open (incompletely-known) systems. Couch's convergence algebra ("On the
Algebraic Structure of Convergence," DSOM 2003) formalizes why: if every
promise is idempotent, the fleet reaches the same fixed point regardless
of execution order or how much of a given device's state is unknown at
deploy time — which is the actual shape of a heterogeneous, sometimes-
offline Android fleet, not a hypothetical.

**Deployment shape: git-distributed policy, a `cf-serverd` on every
client, no central policy host.** This was previously scoped out on the
belief that CFEngine needed dedicated policy-server infrastructure and an
SSH/push model incompatible with stayturgid's architecture — both
corrected 2026-08-13 (see `djbclark/stayturgid`
`docs/research/evaluations/cfengine-evaluation-2026-07-12.md`, corrected
in place). Neither constraint is real: there is no SSH/push requirement,
and CFEngine is lightweight enough that each device runs its own
`cf-serverd` reading policy synced via git (the same signed-release
mechanism as everything else, §7) — no dedicated central policy host, no
push, no SSH dependency at all. This is a **better** fit for §9's
sovereignty model than Ansible's push-from-a-host approach ever was: each
device pulling and applying its own signed policy locally is the same
shape already planned for consent-driven Android deploys, just universal
instead of Android-specific.

**Compile target: CFEngine's own Augments layer, not raw `.cf` synthesis.**
CFEngine has shipped a native JSON data-injection layer since 3.7
(`def.json`/`host_specific.json`, moved into the core agent at 3.8.1),
and its standard library (the Masterfiles Policy Framework, MPF) is
already largely data-driven on top of it (`services/autorun` self-
registers class-tagged bundles from data). This means the Nix→CFEngine
compiler does **not** need to generate bundle/promise text for the common
case — it renders the Site Model straight into the Augments JSON shape
CFEngine already defines and MPF-style generic bundles already consume:

```
nix eval --store dummy:// --json .#cfengineAugments > def.json
```

A generic bundle (see §4.6) reads a `serverapps` (or equivalent) data
structure and handles "ensure this package is present and pinned, these
directories exist, this service is loaded" for **any** entry in the data —
written once, not once per service. Merging (site → role → host layers)
happens entirely in Nix (`mkDefault`/`mkForce`/`mkMerge`) before render;
CFEngine's own `mergedata()` is not used for this to avoid the same
"two type systems diverge" risk already called out for the JSON Schema in
§4.3 — one merge engine, one source of truth.

Only promise types MPF's stock library doesn't cover need actual `.cf`
text, and even that is templated from typed Nix option values, not
synthesized. **Guard, matching §4.3.1's `types.package`/`types.derivation`
warning:** any module option that bottoms out in CFEngine's `commands`
escape hatch (an arbitrary shell invocation, CFEngine's equivalent of
Ansible's `shell`/`command` modules) must be flagged, not treated as safe
merely because it came from a typed schema — rendering from Nix makes
authorship deterministic, it does not make the underlying operation
idempotent.

### 4.5 Narrow, deferred: Puppet-catalog-JSON for genuinely ordered operations (D16, new)

Not every operation reduces to an order-independent promise. Puppet's
catalog compiler (formal semantics: µPuppet, ECOOP 2017) solves a
**different, stronger** problem — resolve into one deterministic, provably
ordered plan — which is the right tool exactly where a real sequencing
constraint exists and the wrong default everywhere else (over-specifying
order nothing requires).

**The practical audit (2026-08-13) found this surface is small.** Checked
every service-owning role across `stayturgid` and `site-djbclark` (14
roles: `control_node`, 8 `serverapp_*`, `goose`, `hindsight`, `litellm`,
`open_webui`, `site_agents`): **all 14 declare zero Ansible role
dependencies** (`meta/dependencies: []` on every one) and are invoked as
independent, single-role playbooks by an external orchestrator — already
order-independent by construction, with zero use of Ansible's own
ordering primitives (`notify`/`handlers`) anywhere in either repo. The
**one confirmed, explicitly documented hard ordering constraint** in the
whole surface is a bootstrap precondition in `site.yml`: "ensure
intentionally precedes verify — a factory-reset device has no APKs to
verify until the normal deploy installs the immutable locks." **The Android chain audit (2026-08-13) came back negative.** The
`fleet/fleet.yml` six-role chain (`termux_userland → shizuku_config →
tailscale_vpn → play_store → app_privileges → ensure_apps`) was the one
candidate for a real dependency graph. All six declare zero role
dependencies, and every prerequisite that looks intra-chain is in fact
satisfied by an earlier **playbook** in `site.yml`'s pipeline, not by an
earlier role: `rish` extraction and the `localhost:5555` appops grant
need the Shizuku APK and a running Shizuku daemon (stages 1 and 3,
`ensure-bootstrap-apks` / `ensure-shizuku`); `tailscale_vpn` and
`app_privileges` both carry comments naming a prerequisite that resolves
to `bootstrap_apks` at stage 1. Five of the six are control-node
`delegate_to: localhost` adb operations that share no execution context
with each other at all.

The chain also **contradicts its own only real rule**: `play_store` →
`app_privileges` correctly installs before hardening, but `ensure_apps`
installs *after* `app_privileges` runs, so an app added there goes
unhardened for a full deploy cycle (filed as `stayturgid#288`). A list
that encoded genuine dependencies would not disagree with itself; this is
accreted order, not designed order.

**Methodological caveat, load-bearing.** Reading the current playbooks
answers "what works on already-provisioned devices," not "what a cold
device requires" — convergent automation leaves no trace of any constraint
that fails on run 1 and succeeds on run 2, and **no device in this fleet
has ever been provisioned from factory reset by the automation.** Re-derived
semantically from what the operations *do*, the real constraints sort into
three kinds, and only one of them is even shaped like a dependency graph:

- **Transport bootstrap — strictly sequential, unreorderable.** ADB
  reachable → APKs installed → Termux foregrounded once (it unpacks
  `$PREFIX` on first launch; `pkg`/`run-as` are unusable until then, and
  this is handled today only as a best-effort *heal*, filed as
  `stayturgid#290`) → `sshd` + keys delivered over ADB → Shizuku started
  and port 5555 open. Six nodes, one path.
- **Per-app chains — short, independent, non-interleaving.** `install →
  configure → privileges → verify`, one per app, no cross-talk.
- **Interlocks — not dependencies at all.** `always_on_vpn_lockdown` set
  on a device whose Tailscale is unauthenticated severs every management
  path to it; nothing in that codebase authenticates Tailscale, and only a
  safe default (`lockdown: false`) prevents it today (filed as
  `stayturgid#289`). This is a safety guard, not an edge in a resource
  graph, and a catalog cannot express it.

**Decision: do not build the Puppet-catalog compiler.** A strict six-node
path is a `bundlesequence`, hand-authored — dependency resolution over it
is machinery without a job. Independent per-app chains are expressible
with CFEngine classes/`depends_on` directly; catalog compilation earns its
keep only when chains interleave into a genuine DAG, and these do not.
Interlocks need guarded promises, which is CFEngine's model rather than
Puppet's. Puppet's real value — automatic resolution plus autorequire over
a large heterogeneous graph — has no corresponding problem here.

**Status: rejected on semantic analysis, pending confirmation by a real
from-scratch provision.** Not closed outright: the negative verdict rests
on reasoning about a cold path that has never been executed, and the
three gaps found above were found by reasoning rather than by running it,
so the list is very unlikely to be complete. Provisioning one device from
factory reset is what settles this — and it is the correct forcing
function for the transport-bootstrap and interlock designs regardless of
how D16 lands. If that trial surfaces genuine interleaving dependencies,
that becomes the entire scope of the Puppet path: small and targeted, not
a parallel general-purpose system built on spec.

### 4.6 ncf/Rudder: reuse the code, not the project (D17, new)

Rudder — originally built directly on CFEngine as one of two execution
backends (the other: PowerShell/DSC for Windows) — is real, substantial,
shipping-for-a-decade prior art for exactly this design's shape: a
higher-level declarative layer (Rudder Language, plus a no-code Technique
Editor built on **ncf**, a library of parameterized "generic methods")
compiled down to CFEngine promises. It validates the Nix-module→generic-
bundle pattern independently of anything built here.

**Degree of reuse, checked directly:** `ncf` as an independent project is
gone — archived, folded into the Rudder monorepo
(`Normation/rudder/tree/master/policies/lib`), GPLv3 (not a concern per
operator). Its generic-method bundles (`package_present`, file/line
management, symlink management, service state — a broad, hardened
catalog) are **ordinary CFEngine** — standard `files:`/`classes:` promise
types, runnable under plain `cf-agent` with no Rudder server, GUI, or
database required. But every bundle body has Rudder's own reporting
convention woven directly into the promise logic (`_log_v3`, canonicalized
`class_prefix`, standardized `<method>_<param>_{success|repaired|error}`
outcome-class naming) — not an external dependency, but not free either.

**Decision:** vendor and adapt individual generic-method bundles as a
reference corpus — years of hardened CFEngine idiom for common file/
package/service operations, worth lifting rather than re-deriving — while
stripping the Rudder-specific reporting scaffolding and replacing it with
fleetopia's own (§4.7). Not a dependency to track upstream (no
independent release exists anymore); a one-time, per-method adaptation.
**Zero coverage for the actual hardest part:** ncf/Rudder targets Linux
and Windows only — no macOS/launchd story, no Android/Termux story. The
`serverapp_*` launchd-plist-and-brew pattern was always fleetopia-original
work regardless of this decision.

### 4.7 Local-first reporting: per-device SQLite is the record of truth (D18, new)

The centralized-shipping design (ship every promise outcome to the
existing Vector/OpenObserve/VictoriaMetrics/Grafana stack, treat that as
the record) is the wrong default for this fleet specifically: the
documented operational history (Fire OS boot-recovery failures, flaky
ADB-over-wireless, the peer-help mesh for offline devices) means a device
is often unreachable from any hub exactly when its own debug history
matters most. The relevant framing is **local-first software**
(Kleppmann, Hardy, Kaffman & van Hardenberg, Ink & Switch 2019): each
device holds its own authoritative copy, works fully offline, and any
central/shared view is optional and eventually-consistent, never required
for the device's own operation. (Same theoretical family as Couch's
algebra and Promise Theory — convergent, order-independent state, not a
new pattern.)

**Design:** `stayturgid-agent` owns a local SQLite database per device as
the authoritative record, populated from CFEngine's local promise-outcome
log. On CFEngine Enterprise this is close to free — every promise outcome
already writes to `$(sys.statedir)/promise_log.jsonl` automatically since
3.9.0. On CFEngine **Community** (the edition actually in scope — GPLv3,
matching D13/D14's licensing posture; Enterprise's COSL license was never
part of this design), that local capture isn't automatic and needs a small
piece of glue — a local syslog receiver or a thin `reports:` wrapper
around the generic-method bundles' outcome logging (§4.6) that appends a
structured line to a local file for `stayturgid-agent` to ingest. Keep
ncf's outcome-state vocabulary (`success`/`repaired`/`error`/`n-a`,
enforce mode; `compliant`/`noncompliant`/`error`/`n-a`, audit mode) — it's
a well-tested structured vocabulary independent of where the output goes;
only the sink changes.

Rudder's own compliance database (PostgreSQL, no SQLite path — checked
directly, no documented alternative-backend support) is **not** adopted
even as a pattern-to-imitate-in-full: its per-node/per-directive/per-
component report shape and its rule-compliance-as-a-query-over-raw-events
model are worth keeping; its centralized root-server-plus-Postgres
topology is structurally hub-and-spoke, the opposite of what this section
decides. SQLite is also the right weight class for Termux specifically —
no server process, already trivially available — consistent with the
same adoptability instinct behind D6.

Syncing a subset of local SQLite to the existing Vector/OpenObserve/
Grafana stack is an optional, best-effort push **from** the device when
reachable, never the record of truth.

### 4.8 Nix store locality (D20, new)

Wherever a real Nix store is used (the Termux artifact builder, §6; the
Mac if nix-darwin is adopted, §5.2) — **never point `NIX_STORE_DIR` or
the store's SQLite metadata DB (`db.sqlite`) at shared/network storage
written by more than one host.** This is not a hypothetical risk: it is
Nix's own documented failure mode (NixOS/nix#378 and related issues) —
the store metadata DB is fine as a local, single-writer-per-host file
(its normal, default behavior) and corrupts under concurrent multi-host
writes. This is the same single-writer-per-node principle behind D18's
local SQLite design, applied to Nix's own store rather than reinvented —
keep every store strictly local to the host that owns it.


---

## 5. Platform layers (Nix everywhere except bare metal)

### 5.1 Linux — Ubuntu Server is the reference (R5 hard fact)

- **Base OS:** Ubuntu Server LTS, installed normally. No NixOS, no
  nixos-anywhere, no bare-metal Nix. A stranger clones the project onto their
  existing Ubuntu box and it works.
- **Host baseline and services** (packages, users, ssh, tailscale, firewall,
  services like Vector/Caddy/etc.): **mise `bootstrap` (toolchains only) +
  CFEngine promises (everything else — D13/D14, §4.4).** Ansible is fully
  removed (D13): it owned this split in v1/v2-draft; CFEngine's promises,
  rendered from the Site Model via Augments, now own both host baseline and
  services on every platform, closing the "two adapters, one boundary" shape
  Ansible/mise used to require. `comin` stays rejected (generic git-pull
  activation with no signed-update protocol — the trust layer §7 replaces it
  properly; CFEngine's git-distributed policy, §4.4, is signed and typed
  where `comin` was neither).
- **Nix on these boxes** is optional and _additive_: install multi-user Nix
  if you want it for building artifacts or dev shells, exactly as a stranger
  might `apt install` a tool. Never required for the runtime.

### 5.2 macOS (Apple Silicon) — the operator's own machine, a different case

The Mac is not a stranger's machine, so the adoptability constraint doesn't
bind it. **nix-darwin + home-manager MAY own the Mac substrate** (packages,
shell, dotfiles, defaults, declarative Homebrew) because generations and
rollback genuinely help on the one machine you can't easily reimage, and
because it's interesting. **[NEEDS FABLE-5 / MULTI-AI — see §14.1]:** whether
to go nix-darwin on the Mac at all, given that keeping the Mac on the same
mise+CFEngine path as Ubuntu maximizes code sharing and keeps _one_ mental
model. This is a real fork — the fun answer (nix-darwin, learn the tech) and
the coherence answer (mise+CFEngine everywhere) diverge, and the operator
said go the interesting route, so the default is **nix-darwin on the Mac**
unless a review pass shows it fractures the Site Model. Services on the Mac
stay CFEngine-owned regardless (§5.3) — nix-darwin, if adopted, owns
substrate only, exactly as it would have owned substrate-only alongside
Ansible before D13.

### 5.3 Services — CFEngine owns them, everywhere, permanently (D1 superseded by D13)

**Production services (`com.stayturgid.*`, `com.djbclark.*` and their
systemd twins) are rendered as CFEngine promises from `services.yml`, on
every platform — Linux, macOS, and Android.** This replaces the panel's
original D1 (Ansible, permanently). D1 is not "wrong, corrected" so much
as it was decided before CFEngine's actual practical blockers were
checked: the original disqualifiers (no Android binaries, SSH/push
incompatibility, needing dedicated policy-server infrastructure) were
never real requirements for this project, only unvalidated assumptions in
an earlier evaluation, corrected 2026-08-13. Once cleared, CFEngine is
the theoretically better fit on its own terms (§4.4) — not merely an
acceptable substitute for Ansible.

**Deployment shape (§4.4):** each host runs its own `cf-serverd`, reading
policy synced via git as part of the normal signed-release mechanism
(§7) — no dedicated central policy host, no push, no SSH dependency. The
Site Model renders to Augments (`def.json`/`host_specific.json`); MPF-
style generic bundles (§4.6) consume it. nix-darwin (if adopted, §5.2)
owns Mac _substrate_, never services — the same boundary Ansible used to
respect, now enforced by CFEngine instead. The `launchd-writers.yml` lint
still enforces the writer-namespace boundary, unchanged by this decision.

**What does not change:** CFEngine's role as the self-heal/last-ditch
recovery layer (R11) — that role now merges with its role as primary
service owner, since both are the same convergent-promise mechanism
rather than two separate systems (previously: Ansible deploys, CFEngine
independently verifies underneath it; now: CFEngine's own promises are
both the deploy mechanism and their own verification, closing a
previously-real gap where the verify layer could drift from the deploy
layer, §4.7).

### 5.4 Android — unchanged stack, plus the artifact lane (R4/R6)

Termux, Shizuku fork, stayturgid-agent, CFEngine, FIRERPA, SSH CA, Tailscale
— all unchanged. Two additions:

- **Artifact lane:** Nix cross-builds static aarch64/Termux-target binaries
  on a builder; they deploy as ordinary files via CFEngine's pull (§4.4),
  content-addressed, hash recorded in the manifest. Zero on-device Nix. Use
  selectively (pin a
  fussy tool fleet-wide; ship what Termux `pkg` lacks — and note `pkg` is not
  reproducible, which is the actual justification).
- **stayturgid-agent 2.0** grows the **consent/sovereignty surface** (§9) and
  **peer-display** (device-from-device screen use — the parked
  `tablet-control-phone` experiment becomes the `peer-display` role, unblocked
  as data).

### 5.5 Future device classes (extension points, no build-out)

Routers → OpenWrt uci rendered from the Site Model (same adapter contract; no
bare-metal Nix there either, consistent with R5's spirit). iPhone / wearables
/ glasses → `trust_tier: consented` endpoints; consume services + artifacts,
never converge-managed. Microcontrollers → firmware as a Nix-built artifact,
flashing as a task. All are Site Model inventory entries + artifacts, not new
architecture.

---

## 6. Build & distribution topology (no VMs — R3)

- **Ubuntu closures/artifacts:** built natively on a Linux box, or
  substituted. Since the base OS is Ubuntu (not NixOS), there is _no system
  closure to build_ — Nix only builds the artifacts and dev shells you opt
  into, which mostly substitute from cache.nixos.org. This makes R3 almost
  free: the resource-heavy "build a whole system closure" problem the v1
  design worried about **no longer exists** on the reference path.
- **Cross-built artifacts (Android/firmware/pinned tools):** a `builder`
  role on real Linux hardware (ARM + x86 cover both arches natively). Declared
  in `roles.yml`. No VM on the Mac; the nix-darwin `linux-builder` VM stays
  rejected.
- **Cache:** only when a `builder` exists and produces non-substitutable
  artifacts. `harmonia` first (simplest, read-only serve). **Cache trust is
  total and is a real hazard (red-team RT-05):** a trusted cache key can
  substitute any store path. So the cache role is `trust_tier: operator` only,
  keys are separated from release keys, and NAR digests are pinned in the
  manifest and verified before activation. This is **CLOSE-BY-SCOPE** for the
  first 90 days of work — don't build a private cache until an artifact
  actually can't be substituted.
- **Explicitly rejected:** `nix.linux-builder` VM; Docker as build/run
  substrate; emulation builds in the deploy path.

### 6.1 Nix Flakes + flake-parts (D19, new)

**One flake per repo, not a monorepo.** `fleetopia`, `stayturgid`,
`site-djbclark`, and `site-private` stay separate git repos, coordinated
by matching `ops-vX.Y.Z` tags (unchanged, R11). Each declares its own
`flake.nix`; `stayturgid`/`site-djbclark`/`site-private` declare
`fleetopia` as a flake input (`inputs.fleetopia.url =
"github:djbclark/fleetopia?ref=<tag>"`), pinned exactly by `flake.lock` —
which doubles as machine-readable cross-repo provenance for a release,
close to free reproducibility documentation on top of what
`ops-release.json` already tracks. **Open question, not yet resolved:**
whether `flake.lock` can replace part of what `ops-release.json` tracks,
or should stay a parallel, separately-maintained pin — needs a decision
before Step 0 work on this touches release tooling.

**fleetopia's flake is the one the others import, not the reverse.** The
Site Model module-system _type definitions_ (D12/§4.3) live in
fleetopia's flake outputs (`fleetopia.lib.siteModel` or equivalent) —
public, generic, holds nobody's facts, same split as `freeops/` vs.
`site-<n>` (§4.2). The concrete _values_ (site-specific facts) live in
each site repo, supplying data through the module system fleetopia
defines.

**Concrete flake outputs:**

- **`devShells`** — pinned toolchains for every task workspace under
  `~/src/ops-worktrees/`, replacing the per-worktree `.venv-test`/
  `node_modules` drift already flagged in prior research
  (`dashboard-framework-evaluation`, tooling-review threads).
- **`packages`** — the Termux cross-build artifact lane (§5.4/§6):
  built once, content-addressed, shipped as ordinary files. The
  least controversial use — this is what Nix is for, no store-free
  tricks needed since builds happen on a Linux builder, never on-device.
- **A Site-Model-rendering output** (e.g. `fleetopia.siteModel`) — the
  actual D12/§4.4 compile step, `nix eval --json`, via `--store dummy://`
  (§4.3.2) so it runs anywhere without a real store, including CI.
- **`checks`** — `nix flake check` as the CI hook for the JSON-Schema/
  lint gates already planned (the `registry_lint.py` pattern, §4.1):
  schema validation, the "two type systems must not diverge" check
  (§4.3, §4.4), and eventually idempotence property tests, so `nix flake
  check` is the single command that gates whether a Site Model change is
  safe to sign into a release.

**Structural choice: flake-parts for the flake's own internal
composition** — consistent with leaning on the module-system idiom
everywhere else in this design (D12, the Site Model itself), rather than
hand-rolled `outputs = { self, nixpkgs, ... }: { ... }` boilerplate.
Community guidance worth following deliberately: keep `flake.nix` thin,
do the real logic in plain importable `.nix` files the flake wraps — the
Site Model module system should not need to know or care that it's being
invoked from a flake at all.

**Status:** flakes remain formally "experimental" upstream, no committed
stabilization timeline, but stable in practice since 2021 with few
breaking CLI changes; Determinate Nix (already referenced, §5.1) ships
them as stable. Not a bet on unreleased functionality.

**Known gotchas, worth documenting before they cost debugging time:**
flake evaluation is sandboxed to git-tracked files only (a new file must
be `git add`ed before `nix eval` inside the flake sees it); pure
evaluation disables `currentTime`/`currentSystem` and ambient filesystem
access — correct behavior for a reproducible renderer, but anything
needing wall-clock time (release-expiry windows, §7.2) must be passed in
explicitly, never read ambiently; `flake.lock` updates
(`nix flake update`) should go through the same review/consent gate as
any other Site Model change (§7/§8), not be a silent side effect of
running a command.

**Nix store locality (§4.8) applies here too:** wherever `packages`
outputs actually build (the Linux `builder` role, or the Mac if
nix-darwin is adopted), the store stays strictly local to that host —
never shared/network storage across builders.

---

## 7. Releases, manifests, and the typed ChangePlan (the core of the trust layer)

This section is the heart of the design and the part most changed by the
red-team + defensive passes. The full buildable spec lives in
`trust-layer-hardened-design-grok-v1.md`; this is the authoritative summary
and the decisions.

### 7.1 The release train (unchanged contract, richer payload)

`ops-vMAJOR.MINOR.PATCH` stays the only path to deploy checkouts. Each release
additionally publishes a **signed manifest + per-host typed ChangePlan**.

### 7.2 Signing: a TUF _subset_ sized for a solo operator (answers RT-01/02)

Do **not** ship one minisign key as fleet-root. Minisign stays the Ed25519
_signature primitive_ (offline-verifiable on Termux); it is not the update
system. Take this TUF subset, leave the rest:

- **root** — 2-of-3, offline. Three Ed25519 keys; two signatures change root
  or any other role. Shares on physically separate devices (laptop keyfile /
  phone or second machine / cold USB or paper), each password-sealed, not
  co-backed-up. Survives theft of the laptop _or_ any one share.
- **targets (release)** — 1-of-1 or 1-of-2, offline laptop ceremony (~15 min).
- **snapshot** — binds the exact metadata set (anti mix-and-match).
- **emergency** — 2-of-3, offline: security downgrade, key revocation,
  "do not apply releases signed by K."
- **timestamp** — **deferred while push-only**; required before pull timers.
- **Leave out:** delegations, mirrors role, online snapshot, path-hash
  delegation.

Every client that _applies_ a signed artifact (push targets included) keeps a
durable **high-water mark** (monotonic version + hash) and rejects
regressions, expired metadata, wrong channel, or wrong target — closing
replay/freeze/downgrade (RT-02). Root ships **out-of-band with the OS/agent
image** (no first-contact mirror trust — TOFU handled at install).

### 7.3 The typed ChangePlan operation IR (answers RT-03/04 — highest-value artifact)

A signed plan must _constrain execution_, not merely describe it. This is the
single most important thing to build correctly, and the one place a cheap
model must not improvise. **[NEEDS FABLE-5 / MULTI-AI — §14.2].**

The plan is a list of **typed operations**, each declaring: `capability`
(from a closed vocabulary), `resources` (exact ports/paths/packages/units it
may touch — checked against the registries), `target` (bound to the host's
public key), `rollback`, `expiry`, `nonce`. The **executor on each platform
mechanically refuses any effect outside the declared set**:

- **CFEngine/Ubuntu+macOS+Android:** a wrapper that maps declared
  capabilities to an allowlist of promise types/classes/paths; a promise
  touching an undeclared port/path/unit fails closed. (Not "apply the
  bundle because its hash is signed" — that is RT-03, and it applies
  identically to CFEngine's bundle/promise surface as it did to Ansible's
  task surface.)
- **Android agent:** operations map to a closed set of agent verbs; anything
  outside is refused; Shizuku actions are individually enumerated, never
  "run this APK."
- **Nix-built artifacts:** addressed by content hash; the manifest is the
  only name→hash binding.

The two-layer plan (from the ideas dump, adopted): a **verifiable layer**
(the exact operation IR + closure/artifact digests — ground truth) and a
**semantic layer** (generated, cached, LLM-legible: "this bumps openssl
across a CVE and restarts the public proxy"). The semantic layer briefs the
user and their advisor AI; it never authorizes — only the verifiable layer,
checked by the executor, authorizes.

### 7.4 Push and pull (both first-class, both now CFEngine — D13)

Post-D13, push and pull are two modes of the **same** mechanism (CFEngine's
own convergence), not two separate systems as in the Ansible-push /
CFEngine-verify-underneath split this section previously described:

- **Push:** from any host holding a `deploy-origin` role (plural — R2), via
  `cf-runagent` (or the `just cf-run` wrapper around it) to trigger an
  immediate convergence run on a target instead of waiting for its next
  periodic pull, plus (on any Nix-artifact steps) content-addressed fetch.
  This is the **v1 path** and it is safe with §7.2–7.3 alone. **The
  remote-exec channel is both the recovery path and an attack surface**
  (tooling review, unchanged from the earlier assessment): authenticate,
  authorize, and rate-limit `cf-runagent`; prefer SSH-mediated `just
  cf-run` over an open channel.
- **Pull:** each host's own `cf-serverd`/`cf-execd` on its normal
  convergence schedule, reading policy synced via git (§4.4) —
  **CLOSE-BY-SCOPE until the full §7.2 client protocol + resource quotas
  exist** (red-team RT-07 DoS). A fleet where every host pulls and none is
  ever pushed _is_ the no-control-node end state, reached by editing
  `roles.yml`. Build it, gated.
- **Latency caveat (§4.7):** CFEngine's default convergence interval
  (~5 min) is fine for most facts, wrong for anything time-critical (e.g.
  a signed emergency revocation) — that needs the explicit push path
  above, not "wait for the next cycle."

### 7.5 AI-authorship guardrails for the compile targets (D13/D14, new)

Relevant finding: a survey of LLM-generated infrastructure-as-code
(arXiv 2404.00227) found the field heavily weighted toward *generation*
(natural language → Ansible YAML, e.g. Ansible Lightspeed) with
*correctness verification* left thin — evaluated mostly by textual
similarity to a reference (BLEU, CodeBERTScore), not semantic/idempotence
correctness. Load-bearing conclusion: **don't trust an AI to freehand
policy text and assume it's fine because it looks right** — the same
caution that already applies to AI-authored `shell`/`command` Ansible
tasks applies at least as strongly to CFEngine's `commands` escape hatch
(§4.4), since it's newer, less-reviewed surface with no equivalent
history of production scrutiny.

**Good fits for AI, because the output is mechanically checkable:**

- Drafting Nix module option schemas from an existing example (e.g. "here's
  `serverapp_grafana`'s Ansible tasks, draft the equivalent typed
  options") — checkable against `nix eval` succeeding and the JSON Schema
  validating.
- The §4.5 dependency audit (classifying `fleet.yml`'s role transitions as
  real dependencies or habit) — tedious for a human, mechanical for an AI,
  falsifiable by testing whether a role actually breaks without its
  predecessor.
- Generating idempotence test harnesses ("apply twice, assert the second
  application is a no-op") for a rendered promise or generic method —
  checkable pass/fail output, mirroring the academic idempotence-testing
  literature.
- A static gate scanning proposed module additions for the escape-hatch
  trap (`commands`-type promises, `types.package`/`types.derivation`
  misuse per §4.3.1) before merge — bounded pattern-matching, not
  open-ended generation.

**Poor fit without heavy guardrails:** freehand-authoring `.cf` text for a
genuinely novel promise type MPF/ncf (§4.6) doesn't already cover — no
schema to check against, no formal semantics to verify against (unlike
Puppet's µPuppet fragment, §4.5), and exactly the category the empirical
IaC-bug literature identifies as where idempotence bugs concentrate.

---

## 8. Security gates (what must hold before each capability opens)

These are correctness constraints, not budget or effort ones. They are the
distilled "blockers" from the red-team, dispositioned by the defensive pass.
Do not open a capability before its gate.

| Capability                                      | Gate (all must hold)                                                                                                                                                                                               |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Signed push to operator hosts** (v1 baseline) | TUF-subset root + targets/snapshot + high-water marks + typed ChangePlan executor enforcing on CFEngine + source-to-signing hygiene (§8.1)                                                                          |
| **Autonomous pull (timers)**                    | above + timestamp role + converge resource quotas/backoff/kill-switch + hostile-mirror tests                                                                                                                       |
| **Consented devices**                           | above + device-key-bound, single-use, expiring consent grants + capability-enforcing agent executor + **Android artifact provenance** (dep locks, SBOM, signing-cert pin; independent rebuild for privileged APKs) |
| **Private cache / builder scale-out**           | separated build/upload/serve/release authorities + NAR-digest verification before activation + revocable-without-fleet-reinstall                                                                                   |
| **Autonomous role failover**                    | a real lease/fencing/quorum design + partition tests. **Until then: single designated owner + operator-signed plan for every single-writer mutation.** No YAML-ordering pseudo-HA.                                 |
| **local-fix → upstream-heal**                   | **never automated.** Advisory only; human (threshold) approval for any override; deterministic patch-equivalence, never "version claims to contain fix" (RT-09).                                                   |

### 8.1 Source-to-signing hygiene (answers RT-03 precondition + the 2026-08-06 incident)

The 2026-08-06 double-merge (an agent committed into another's worktree,
another merged 231 unreviewed lines) is **in-scope threat evidence**, not
trivia. Therefore, from day one: signing happens only from a clean, isolated,
reviewed checkout — **never a task worktree**; and the worktree
ownership/provenance rules become **automated deterministic checks** (a
`git log`/`git diff` range gate that fails closed under YOLO), not prose. This
is also the correct home for the **OpenHands technique** (§8.2).

### 8.2 OpenHands security — adopt the technique for agents, never as the fleet gate

Two surfaces, two verdicts (both reviewers concurred):

- **Surface A — the AI coding agents that build/deploy the fleet:** adopt the
  _deterministic-analyzer pattern_ (Pattern + PolicyRail + Ensemble
  max-severity), **vendored, not the SDK** — wired into shell/`git`/`gh`
  wrappers and Ralph step gates, because it doesn't depend on possibly-
  manipulated model judgment. This directly mitigates RT-03 and the
  double-merge class. Do not embed the full OpenHands `Conversation` harness.
- **Surface B — the fleet trust layer:** OpenHands analyzers _classify,
  don't hard-deny_, and `execute_tool()` bypasses them. They have **no role
  as an authorization gate** (that's the typed executor, §7.3). At most a
  future non-authorizing advisor input (§9), layered above the deterministic
  gate, never able to approve and never required to deny.

### 8.3 SecretSpec reference monitor (answers RT-06)

secretspec stays the sole declaration authority (R11). Add a deny-by-default
resolver: a signed policy maps `(service identity, host role, capability)` →
allowed handle; everything else is refused with a non-secret audit event.
Secrets delivered as per-service non-inherited runtime files, not ambient
env. Bootstrap material (SSH-CA key, cache key) is a minimal separate root,
not mixed with normal site secrets.

---

## 9. User sovereignty — the freedom feature (R7/R10, the interesting part)

This is what the trust layer is _for_, and it is where this project is
genuinely novel. Frame everything here as giving a person control over their
own computer, not as protecting the fleet from them.

**The interaction the whole design serves:** a user — the operator's parent,
a friend, a stranger who cloned the repo — receives a proposed config change.
Their _own_ AI agent reads the semantic layer of the ChangePlan (§7.3) and
explains, in plain language, what it does and why they might or might not want
it. If they don't want it, they say so in plain English; their agent
maintains a **personal branch** that diverges from upstream — and they never
need to know the words "branch," "merge," or "systemd." When upstream changes
again, their agent re-evaluates against their stated preferences and keeps
their divergence coherent.

Concretely, staged:

- **Consent surface v1 (agent 2.0):** `offer(manifest, plan) → accept |
reject | timeout(deny)`; device-key-bound, single-use nonce, expiring;
  protected local receipt. Gated per §8. The _interface_ is specified now so
  later phases can't regress it.
- **Advisor (T2):** the user's chosen model reads the semantic layer and
  advises. Never authorizes (RT-09). **The two-agent pattern (ideas dump,
  adopted as a first-class control):** the _proposing_ side and the
  _consenting_ side run different models; disagreement escalates to the
  human. This is vendor-diversity-as-a-safety-mechanism — exactly what this
  whole review process did by hand, formalized into the product.
- **Personal branch maintenance (T4, reframed):** the red-team correctly
  called "local-fix auto-merge" an injection vector _under the fleet-safety
  framing_. Under the sovereignty framing it is the product — but the
  security requirement is unchanged: the user's branch is _theirs_, applied
  under _their_ consent; it never auto-merges into anyone else's trust domain,
  and upstream-heal is a suggestion their agent evaluates, never an automatic
  authority. **[NEEDS FABLE-5 / MULTI-AI — §14.3]:** the branch-maintenance +
  advisor loop is the subtlest and most novel machinery in the project and
  deserves a dedicated design pass, including a red-team of the AI-in-the-loop
  attack surface (prompt injection into the advisor, poisoned model in the
  two-agent loop, the semantic layer as an injection vector).
- **Web of trust (T5):** graded trust ("anyone two members of set S vouch for
  at level X, with safeguards Y"), TUF-style thresholds evaluated against an
  attestation log, human-ritual attestations (the phone-call vouch) as
  first-class entries. Roadmap; interfaces shaped by §7 so it attaches
  cleanly.

The transparency-log (T1, Rekor-style, not a blockchain) and reproducible-
artifact provenance (T6/SLSA-style) remain roadmap, gated per §8, never
authorizing on their own.

---

## 10. Literate programming (R9 — widened)

The v1 policy kept entangle narrow, partly on token cost. Token cost is no
longer the governing argument (asides are stripped from agent context;
budget is managed by model routing, §13). So **widen literate coverage** to
everything where the explanation is genuinely part of the artifact —
especially the freedom-relevant glue that Free Sysadmin will publish:

1. **Two prose classes, mechanically separated** (unchanged, load-bearing):
   _rationale_ (intent/invariants/interdependencies) sits with code and is
   agent-visible; _narrative_ (the deep explanations, humor, historical
   asides the operator wants) lives in blocks the agent-facing tangle strips
   and the human/publish weave keeps. Full richness for people; agents don't
   pay for it.
2. **Widened scope:** the Site Model schema, the CFEngine failsafe policies,
   the SSH-CA flows, the ChangePlan IR + executor, the consent/sovereignty
   machinery, the converge agent — all literate. The subtle, freedom-relevant,
   publishable glue is exactly what benefits.
3. **`stitch`** lets agents edit tangled plain files cheaply; the literate
   source absorbs changes. **[stitch under parallel YOLO agents needs an
   ownership lock]** (ideas dump) — extend the worktree ownership rules to
   "who may stitch this doc now."
4. **Structure:** file-aligned chunks, minimal noweb indirection, CI tangle-
   parity gate, plus source-map comments in generated output (Gemini's idea)
   so errors trace to the literate source.
5. The remaining constraint is only agent-edit-accuracy: if a literate file
   measurably degrades agent edits, narrow _that file_. Otherwise, go rich.

---

## 11. Free Sysadmin publishing (R10)

- **Quarantine from day one:** everything under `freeops/` is written fact-
  free, reviewed as if public. Site facts enter only via Site Model
  instantiation. Because the reference target is plain Ubuntu (R5), the
  published artifact is _directly runnable by a stranger_ — the adoptability
  constraint and the publishing goal are the same constraint. Extraction to a
  standalone public repo when it has real consumers (in-tree until then).
- **Licensing:** generic code **GPL-3.0-or-later** (copyleft is the point —
  the freedom being extended is the glue itself); literate docs
  **CC-BY-SA-4.0**; interop _schemas_ (ChangePlan, registry JSON-Schema)
  permissive/**CC0** so the sovereignty ecosystem can interoperate; networked
  trust services **AGPL-3.0**. Audit current LICENSE files before any change
  — direction, never silent relicense.
- **The story this enables:** a person clones the generic layer + Site Model
  schema, fills in their own facts, and runs it on their own Ubuntu box —
  with their own AI helping them understand and diverge from upstream config
  they don't want (§9). That is "Free Configuration Management," and it is the
  same mechanism as the adoptability constraint and the sovereignty feature.
  Three goals, one design.

---

## 12. Build order (coherent state at every boundary)

Ordered so each step delivers standalone value and leaves the system
describable. Not a schedule (effort/time are not costs here) — a _dependency
and coherence_ order. The one correction kept from the pre-mortem on purely
logical grounds: **prove the Ubuntu path before investing in Mac Nix**,
because it de-risks the reference target that everything else depends on.

- **Step 0 — Site Model + fences (pure data, no runtime change).** Schemas
  for `services.yml`/`roles.yml`/`launchd-writers.yml`; transcribe current
  reality; lint in CI + pre-commit; automate the worktree provenance gate
  (§8.1). Coherent stop: same system, now with a truthful data spine and a
  provenance gate. _Also the cheapest possible agent work — good first task
  under the budget._
- **Step 1 — Ubuntu reference path.** mise `bootstrap` + CFEngine promises
  render a real Ubuntu host from the Site Model. This is the adoptability
  keystone; do it early even before you own a VPS, by rendering + dry-running
  against a throwaway box or container-like target. Coherent stop: the
  reference deployment provably works on vanilla Ubuntu.
- **Step 2 — First real Linux host.** Provision a VPS (Hetzner) as Ubuntu;
  give it backup/shadow roles (observability mirror, backup) — **not**
  obs-main yet. Proves R2 (flip a role's main to it and back) and gives the
  role mesh a second real node. Coherent stop: a genuine second host; destroy
  it and the Mac/fleet are unchanged.
- **Step 3 — Signed releases (push-only) + typed executor.** TUF-subset root
  ceremony; manifest + ChangePlan generation in `ops-release-*`; the
  capability-enforcing executor on CFEngine (§7.3, §8). Push-only, operator
  hosts. Coherent stop: every deploy is a signed, execution-constrained plan;
  no autonomous anything yet.
- **Step 4 — Mac substrate (the interesting, optional Nix step).** If §14.1
  resolves toward nix-darwin: bring the Mac substrate under nix-darwin +
  home-manager, services still CFEngine. Fully reversible (`darwin-rebuild
--rollback`). Coherent stop: Mac substrate is declarative; nothing depends
  on it that couldn't run on the mise path.
- **Step 5 — Pull convergence.** Converge agent with the full §7.2 client
  protocol + §8 quotas. Any host with the role self-updates. Coherent stop:
  the no-control-node end state exists as data.
- **Step 6 — Consent/sovereignty v1 (agent 2.0).** The consent surface on one
  fleet device, then the advisor and personal-branch loop (§9), each behind
  its §8 gate. This is the payoff — the freedom feature — built on everything
  below it.
- **Step 7+ — demand-driven.** builder/cache (when a non-substitutable
  artifact appears), reproducible-APK provenance (before any consented device
  runs privileged APKs), WoT/transparency-log, freeops extraction (when a
  second person runs it).

Every step's rollback is its own coherent stop above it.

---

## 13. Token budget as an architectural constraint (R12)

$60/month for this project is real and the architecture must respect it —
this is the one cost that counts. Design and workflow implications, to be
followed by every implementing agent:

- **The Site Model spine is itself a cost control:** agents edit small
  schema'd data files instead of reading a sprawling config tree; the
  literate strip-asides mechanism keeps agent-facing context lean. A big
  reason the data-spine design wins is that it makes routine agent work cheap.
- **Model routing (use `aiuse` to enforce):** routine implementation on
  cheap/subscription seats (Sonnet-class, DeepSeek v4 Pro, the subscription-
  covered Codex/Grok/Gemini seats), **not** metered Fable-5-xhigh. Reserve
  Fable 5 / high-effort / multi-vendor for the marked decisions (§14) and
  security-critical review only.
- **This architecture session was a deliberate one-time spend** (five agent
  passes, three vendors). That is not the operating mode. Steady-state
  implementation should be near-free against the budget if routed as above.
- **A plan step that clearly implies heavy recurring model spend is a
  smell** — prefer designs where the expensive thinking is done once and
  captured in a document (like this one) that cheap models then execute.

---

## 14. Points that would benefit from Fable 5 and/or multiple AIs

Everywhere else, a cheap model executing this document is fine. These are the
exceptions — places where a wrong guess is expensive to unwind, flagged per
the operator's request. Spend the premium budget here, nowhere else.

- **§14.1 — nix-darwin on the Mac, yes or no.** The fun/coherence fork (§5.2).
  Multi-AI, low security stakes; a Nix-idiom specialist pass would help. Not
  urgent — resolvable at Step 4.
- **§14.2 — the typed ChangePlan operation IR + executor enforcement (§7.3).**
  The highest-value and highest-risk artifact in the whole project. A cheap
  model must not improvise a capability vocabulary or an enforcement boundary.
  **Fable 5 for the design + an independent adversarial review** (different
  vendor) before it's built. This is the thing to spend premium tokens on.
- **§14.3 — the sovereignty/advisor/personal-branch loop + its AI-specific
  red-team (§9).** The most novel machinery; the attack surface (prompt
  injection into the advisor, poisoned model in the two-agent consent loop,
  the semantic layer as an injection vector) is genuinely new territory and
  under-reviewed. Fable 5 design + a dedicated AI-in-the-loop red-team, ideally
  a vendor not yet used adversarially here.
- **§14.4 — the solo-operator TUF-subset key ceremony + recovery runbook
  (§7.2).** Security-critical and easy to get subtly wrong. One careful Fable
  5 pass + one independent review; verify every protocol claim against current
  TUF/minisign docs, never training memory.

Everything not in this list: a cheap model following this document is
expected to do well. When such a model hits one of these four and it's
unresolved, it should write a question doc and stop, not improvise.

---

## 15. Decision register (operator sign-off)

| #         | Decision                 | Resolution                                                                                                                                                                                         |
| --------- | ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1        | Production service owner | **SUPERSEDED by D13 (2026-08-13).** Was: Ansible, permanently, all platforms.                                                                                                                      |
| D2        | Site Model formality     | Schemas at Step 0; generation gradual; writer-lint immediate.                                                                                                                                      |
| D3        | Ubuntu reference path    | **mise baseline (toolchains) + CFEngine services is the PRIMARY Linux path** (revised by D13; promoted from "exit" originally).                                                                    |
| D5        | Literate scope           | **Widened** (§10); token cost no longer the limiter.                                                                                                                                               |
| D6        | Nix on bare metal        | **NO — hard fact.** Nix for builds/dev-shells/Mac-substrate only.                                                                                                                                  |
| D8 (new)  | Trust layer disposition  | **Build it, gated (§8).** The "defer indefinitely" option is rejected — sovereignty is the point.                                                                                                  |
| D9 (new)  | OpenHands                | Vendor the analyzer _technique_ for coding agents (§8.2 Surface A); no role as fleet gate (Surface B).                                                                                             |
| D10 (new) | Task runner              | **Keep `just`** as the human verb surface; start using its dependency support; mise stays scoped to toolchains/baseline. Both reviewers concurred; a real DAG need is the only trigger to revisit. |
| D11 (new) | Trust-layer scope cuts   | Per the defensive pass: FIX-IN-V1 the root/executor/high-water/secret-monitor; CLOSE-BY-SCOPE consent/cache/failover/APK-provenance behind §8 gates; never automate local-fix.                     |
| D12 (new) | Site Model authoring language | **Nix module system MAY author the Site Model** (§4.3), rendered to the same schema-validated JSON everything already consumes. Distinct from D6: this is about the authoring frontend, not the runtime substrate — D6's "no bare-metal Nix" is unchanged. Non-Nix JSON/YAML authoring stays a supported fallback for adoptability. |
| D13 (new) | Ansible removal / service owner | **Ansible is fully removed — from service ownership AND host-baseline/bootstrap.** CFEngine (promises) + mise (toolchains only) replace it everywhere, all platforms, superseding D1 (§5.3, §5.1). The original Ansible-over-CFEngine blockers (no Android binaries, SSH/push incompatibility, needing dedicated policy-server infra, GPLv3) were an earlier analyst's unvalidated assumptions, corrected 2026-08-13 — not real constraints. Purely on theoretical fit (Promise Theory/Couch's algebra vs. no comparable formal grounding for Ansible), CFEngine was always the better answer; D1 reflected an unchecked practicality objection, not a considered rejection. |
| D14 (new) | CFEngine deployment shape | **Git-distributed policy, `cf-serverd` on every client, no dedicated central policy host, no push/SSH requirement** (§4.4, §7.4). Push (via `cf-runagent`/`just cf-run`) and pull (each host's own convergence schedule) are both first-class, same mechanism. |
| D15 (new) | Nix→CFEngine compile target | **CFEngine's native Augments layer (`def.json`/`host_specific.json`), not raw `.cf` synthesis** (§4.4). Merging happens once, in Nix, before render — CFEngine's `mergedata()` is not used for this, to avoid a second, divergent merge engine. |
| D16 (new) | Order-dependent operations | **Puppet-catalog-JSON rejected — do not build it** (§4.5). The gating `fleet/fleet.yml` Android-chain audit (2026-08-13) came back negative: all six roles declare zero dependencies, every apparent intra-chain prerequisite is satisfied by an earlier `site.yml` playbook, and the chain contradicts its own install-before-harden rule (`stayturgid#288`). Re-derived semantically, the real cold-device constraints are a strictly sequential six-node transport bootstrap (a `bundlesequence`), independent non-interleaving per-app chains (CFEngine classes/`depends_on`), and safety interlocks that a catalog cannot express at all (`stayturgid#289`, `#290`). **Rejected pending confirmation by a real from-scratch provision** — the verdict reasons about a cold path that has never been executed, so it is not closed outright. |
| D17 (new) | ncf/Rudder reuse            | **Vendor and adapt individual generic-method bundle bodies as a reference corpus, strip Rudder's reporting scaffolding** (§4.6). Not a dependency — `ncf` is archived, folded into the Rudder monorepo, no independent release to track. Zero coverage for macOS/Android; that work was always fleetopia-original. |
| D18 (new) | Local-first reporting        | **Per-device SQLite (owned by `stayturgid-agent`) is the authoritative record, not the central observability stack** (§4.7). Populated from CFEngine's local promise-outcome log; ncf's outcome-state vocabulary retained; sync to Vector/OpenObserve/Grafana is optional and best-effort, never required for local debugging. Rudder's own Postgres-backed compliance DB is explicitly not adopted (no SQLite path exists; its hub-and-spoke topology is the wrong shape here). |
| D19 (new) | Nix Flakes + flake-parts     | **Adopted** (§6.1) — one flake per repo, `fleetopia`'s flake as the shared module-system library the other three repos import, flake-parts for internal composition. `flake.lock` vs. `ops-release.json` overlap is an **open question**, not yet resolved — needs a decision before Step 0 work touches release tooling. Nix store locality (D20, §4.8) applies to every flake `packages` build. |
| D20 (new) | Nix store locality             | **Never point `NIX_STORE_DIR` or the store's `db.sqlite` at shared/network storage written by more than one host** (§4.8). Single-writer-per-host is Nix's own default and its documented failure mode under multi-host writes (NixOS/nix#378). Same principle as D18's local-first SQLite, applied to Nix's own store. Previously recorded only as an aside inside D19; promoted to its own row 2026-08-13. |

Silence = proceed from Step 0. Objections amend this register, not the
archived documents.

---

## 16. Document map (for the next AI)

- **This file** — authoritative architecture + build order. Start here.
- `architecture-final-v1.md` — prior synthesis; superseded where they differ.
- `architecture-proposal-v1.md` — Claude's detailed §7–8/§12 (manifest/consent
  detail still useful).
- `architecture-proposal-{openai,gemini,grok}-v1.md` — the independent panel;
  archival positions, do not edit.
- `redteam-trust-layer-openai-v1.md` — the nine findings; §8 here is their
  disposition.
- `trust-layer-hardened-design-grok-v1.md` — the _buildable_ trust-layer
  spec; §7–8 here summarize and decide, that doc implements.
- `tooling-assumptions-review-{openai,grok}-v1.md` — per-tool verdicts;
  source for D9/D10 and the CFEngine/Tailscale-ACL hardening notes.
- `premortem-scope-realism-openai-v1.md` — read with the correction in mind:
  its effort estimates assume a commercial objective function that does not
  apply; its _logical_ points (exit-before-Mac-Nix, coherent stops, two-
  writers, no-consent-UI-before-executor) are kept and live in §8/§12.
- `orchestration-research-2026-08-13.md` — the non-VM orchestration research
  leg: Rudder's Core-vs-plugin RBAC split (resolved), Bolt/Choria against the
  operator's two hard constraints, Bcfg2's fixpoint-loop answer to ordering,
  `mgmt`'s AutoEdges as a shipped dependency-inference precedent, and the
  image-based-update gap. Evidence for the pending D16 conversation; amends
  no decision.
- `rudder-as-umbrella-evaluation-2026-08-13.md` — evaluates adopting Rudder
  wholesale and extending it for Termux/Android. Verdict: no (no macOS or
  Android agent at any tier; ARM packages absent from the Core repository,
  checked directly). Contains a **correction to D17's stated rationale** —
  GPLv3 blocks depending on Rudder's *code*, not running it or writing
  techniques for it, and Rudder grants a plugin exception. Amends no
  decision; fix the D17 text when it is next touched.
- `bolt-choria-as-umbrella-2026-08-13.md` — the same question asked of Bolt
  and Choria, plus the operator's withdrawal of local-first debuggability as
  a hard requirement. Bolt: no (inherits the puppet-agent matrix and the
  25-node packaging EULA via `bolt apply`, push-only). **Choria: the only
  candidate that reaches every platform in the fleet** — `darwin/arm64` and
  `linux/arm64` are first-class FOSS build targets — but it fills D14's
  transport slot, not D13's convergence slot. Gated on an unrun Termux test.
  Notes that **D18 now has no surviving stated rationale**.
- `site-pika-requirement-change-2026-08-13.md` — **read this before the other
  two umbrella docs**, it supersedes their site-pika assumptions. Three
  root-trusted admins, no GUI ⇒ **Rudder drops out entirely** and the
  "two systems" conclusion reverses to one. D16 narrows to a
  composition-only question; blast radius and multi-author composition
  survive, authorization and tenancy do not.
- `ideas-dump-claude.md` — unprotected; the two-agent-consent control, the
  semantic/verifiable plan split, the role-mesh-is-consensus flag, and the
  model/vendor notes all graduated into this document.

### 16.1 Prior-art bibliography (D13–D20 research, 2026-08-13 session)

Not archived as separate documents — captured here so the D13–D20 decisions
aren't re-derived from scratch by a future reader. Full citations and the
research trail live in the session transcript; key names, for follow-up:

- **Convergence/promise theory:** Alva Couch & Yizhan Sun, "On the
  Algebraic Structure of Convergence" (DSOM 2003); Mark Burgess & Jan
  Bergstra, Promise Theory (formalized ~2005) — the formal grounding for
  D13/D14.
- **Formal semantics of config languages:** µPuppet (Edinburgh, ECOOP
  2017; arXiv 1608.04999) — the bar CFEngine's `.cf` language doesn't
  clear, why §4.5's Puppet-catalog path stays narrow rather than becoming
  the default.
- **Declarative-to-imperative deployment synthesis (harder, rejected as a
  general approach):** Aeolus/Zephyrus/Zephyrus2 (Di Cosmo, Mauro,
  Zacchiroli et al.), Engage (Fischer, Majumdar, Esmaeilsabzali), METIS —
  academically real, never achieved broad practical traction; evidence for
  why §4.4/§4.5 scope down instead of attempting general synthesis.
- **Network-config synthesis (the version of this pattern that shipped in
  production):** NetKAT (Foster, Kozen et al.), Merlin, Propane, Genesis —
  worked because the target (flow tables, routing) is narrow and
  algebraically clean, unlike general host config.
- **Refinement calculus (the math-side ancestor):** Ralph-Johan Back
  (1978); Carroll Morgan, *Programming from Specifications*.
- **AI planning / IT-specific:** Bylander, "Computational Complexity of
  Propositional STRIPS Planning" (PSPACE-complete, 1994); Erol/Hendler/Nau
  HTN planning, SHOP2 — the paradigm actually matching hand-authored
  Ansible-roles/CFEngine-bundles/Puppet-classes; Srivastava & Kambhampati,
  "The Case for Automated Planning in Autonomic Computing" (ICAC 2005);
  CHAMPS (Keller et al., IBM Research, NOMS 2004) — real deployment
  planning system, framed the underlying problem as "mathematically
  intractable," solved via domain-specific heuristics, not general search.
- **Rudder/ncf (D17):** Rudder (Normation) — Technique Editor + Rudder
  Language compiling to CFEngine (and PowerShell/DSC) promises; `ncf`
  generic methods, archived into `Normation/rudder/tree/master/policies/
  lib`; CFBS (CFEngine Build System) — JSON-based module composition,
  official.
- **Local-first (D18):** Kleppmann, Hardy, Kaffman & van Hardenberg,
  "Local-first software: you own your data, in spite of the cloud" (Ink &
  Switch, 2019).
- **LLM-authored IaC risk profile (§7.5):** survey at arXiv 2404.00227 —
  generation well-studied, correctness verification thin.
- **Empirical IaC bug taxonomy (motivates §4.4's `commands`-escape-hatch
  guard):** "When Your Infrastructure Is a Buggy Program: Understanding
  Faults in Infrastructure as Code Ecosystems" (ACM PACMPL 2024).
- **stayturgid's own corrected research:** `djbclark/stayturgid`
  `docs/research/evaluations/cfengine-evaluation-2026-07-12.md` (corrected
  in place, 2026-08-13, commit `3cfd3fa` on `feature/stayturgid-2.0`) and
  `docs/research/evaluations/bcfg2-evaluation-2026-07-12.md`.

_Filed under djbclark/fleetopia#1. Amend via this register; treat the
archived reviews as immutable record._
