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
don't need apex context to do good work. Six things to internalize before
you touch anything:

1. **This is a freedom project, not a product.** The operator is doing this
   for fun and to get reacquainted with the tech, and to extend software
   freedom to configuration/sysadmin glue. There is no deadline, no paying
   user, no "MVP." "Interesting and correct" beats "minimal and safe" every
   time they conflict — the operator has said this explicitly and repeatedly.
   Do not propose conservative scope cuts to save effort; effort is not a
   cost here. **Token spend is the only cost that matters** (§13).

2. **The reference target is a stock Linux distro on bare metal — this is a
   hard constraint, not a preference.** The operator will NOT run bare-metal
   Nix. The reason is _adoptability_: a stranger who wants to try this
   project should start from what they already have (a normal Linux box),
   and asking them to install duplicate packages is fine while asking them
   to replace their OS is not. Every design decision inherits this. Nix is
   still used heavily — but never as the thing a person installs on bare
   metal (§5). _Ubuntu Server LTS is the working default and what §5.1 is
   written against; which mainstream distro it ends up being is open until
   §12 Step 4 (D22). The constraint is "stock distro, not NixOS" — the
   distro's name is not the load-bearing part._

   **Note the build order does not start here.** Linux is platform adapter
   #3; macOS is first and Android second (D22, §12). Being the *reference*
   target and being the *first* target are different roles, and this
   document previously conflated them.

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

6. **You are the primary author, not the exception — so prefer local
   knowledge over global knowledge (R13, §2).** Most of this system will be
   written by agents like you. The operative rule: a design is good here if
   you can satisfy it correctly from *the file in front of you*, and bad if
   correctness depends on invariants living in twelve files you never
   opened. When you have a choice, state what a thing provides and needs
   locally and let the compiler derive the rest, rather than hand-writing a
   cross-file constraint you'd have to already know about. Second rule:
   **prefer machine-checkable to conventional** — if you find yourself
   writing "remember to…", that belongs in a schema or a compile-time check
   instead. This is not style advice; it decided §4.5.1(b) and (d).

7. **Put what matters at the front or the back, never buried in the middle
   — for what you read and what you write (D31).** Long-context models
   measurably lose information placed mid-document; this section is
   literally "read this first" for exactly that reason. Apply it to
   anything you generate for another agent to read: rendered Augments, a
   ChangePlan, a commit message. Two related affordances, once built: a
   registry-lookup CLI (D24, §4.4) so you query a fact instead of reading a
   whole registry file, and a root `AGENTS.md` (§16) — checked against the
   actual evidence before being added, see that section.

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
  │  schemas owned by nix2cf (D21); instances live in site repos  │
  └───────────────┬───────────────────────────────────────────────┘
                  │  consumed by (never authored by) ↓
                  ▼
  ┌───────────────────────────────────────────────────────────────┐
  │            nix2cf  — the compile layer (§4.3–4.5)              │
  │  merge → conflict check (error, never last-wins) → dependency  │
  │  inference (AutoEdges-style, authored edges win) → render      │
  │  → CFEngine Augments (def.json/host_specific.json, D15)        │
  └───────────────┬───────────────────────────────────────────────┘
                  │
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
   every domain is comprehensive unless it opts out with a reason (§4.5.1d)
   → anything on the device and not in the model is an EXTRA ENTRY
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
- **R5 → HARD FACT:** **The operator will not run bare-metal Nix. A stock
  mainstream Linux distro is the reference target.** Rationale is
  adoptability, not exit cost: the reference deployment must resemble what a
  stranger already runs. Nix lives at every level _except_ the installed
  base OS. **Two halves, different strengths (clarified 2026-08-13, D22):**
  no-bare-metal-Nix and must-resemble-a-stranger's-box are hard and binding;
  **Ubuntu Server specifically is the default answer, not the requirement** —
  any mainstream stock distro satisfies R5, and the choice is open until
  §12 Step 4, where the reference host actually gets built. NixOS remains
  excluded by the first half regardless.
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
- **R13 (AI authorship is the primary authorship model — operator-stated
  2026-08-13):** **most of this system's configuration and code will be
  written by AI agents, not by hand.** The project therefore optimizes, as a
  first-order objective on par with the others in this list, for two things:
  making it as easy as possible for an agent to write something correctly,
  and catching mistakes automatically rather than by review. This
  generalizes §7.5, which previously scoped the concern to the compile
  targets alone, into a project-wide objective.

  **The decision rule this yields, which is what makes R13 operational
  rather than a slogan: prefer designs that require only _local_ knowledge
  over designs that require _global_ knowledge.** An agent's context window
  bounds what it can know; it sees the file in front of it, not the
  invariants living in twelve other files it never opened. A design where
  correctness follows from information present at the point of authorship
  is one an agent can satisfy reliably. A design where correctness depends
  on the author already knowing what everyone else declared is one an agent
  will violate confidently and plausibly — which is worse than violating it
  obviously. Note this cuts against the usual human-authorship intuition,
  where "just write down the constraint you know about" is cheap; for an
  agent it is precisely the expensive thing.

  Second rule: **prefer machine-checkable to conventional.** A convention an
  agent must remember is a convention it will eventually break silently; a
  schema, a type, or a compile-time check catches it for free and reports it
  in a form the next agent can act on.

  R13 re-weights decisions already recorded rather than reopening them:
  D12's typed Site Model becomes the cheapest available error-catcher for a
  generator, not merely an ergonomic authoring choice; §4.5.1(a)'s
  requirement that conflict errors carry full resolution context hardens,
  because the reader of that message is now usually an agent that cannot
  go exploring for the missing half; the `buildfile`-style "show me exactly
  what device X receives" affordance (`bcfg2-papers-2026-08-13.md` §2)
  becomes an agent's self-check loop rather than a debugging convenience;
  and R9's literate-programming widening is reinforced, since prose that
  states intent is what lets an agent tell a deliberate oddity from a bug.
  **Resolved the same day, in this order:** R13 decided §4.5.1(b) — the
  ordering mechanism — on its first rule, and the inversion is the clearest
  worked example of what R13 does to an already-argued decision. Explicit
  `depends_on` is global-knowledge and dependency inference is
  local-knowledge, so the cost analysis that favoured explicit ordering
  under human authorship flips under R13, and `nix2cf` builds the inference
  stage. R13's second application was to flip §4.5.1(d)'s per-domain
  comprehensiveness from opt-in to **default-on with explicit, reasoned
  opt-out** — AI-authored drift is exactly what extra-entry detection
  catches, so the safe default belongs on the detecting side, and a bare
  opt-out boolean would let an agent widen the unmanaged surface silently.

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
  `adapter` (`ubuntu-mise` | `android` | `macos`), `trust_tier`
  (`operator` | `managed` | `consented`). _(The `ansible` adapter was
  removed from this enum by D13 — Ansible is gone from service ownership
  and from host baseline/bootstrap alike, so it is not a value any host can
  legally hold.)_
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
- **Example fixtures are mandatory, not just customary (D25, new).**
  `nix2cf/examples/*.yml` already pairs one fixture per
  `nix2cf/schema/*.schema.json`. Wang & Zhang (arXiv:2509.19931) found, for
  planning-language generation, that "examples consistently outperform
  descriptions" and that documentation bundling both dramatically
  outperforms either alone (`ai-optimization-review-2026-08-13.md` item 3).
  Extend `bin/schema_lint.py` to fail if any schema lacks a matching
  example (or vice versa) — the pairing already exists; this makes it
  checked rather than customary, per rule 6/R13's second clause.
- **Existence checks extend past ports/paths (D28, new).** A 2025 error
  taxonomy of real LLM-generated IaC (Nekrasov et al., cited in the paper's
  §3.1) found 65% of technical errors are *factual incorrectness* —
  referencing a value that is invalid, nonexistent, deprecated, or
  incompatible — against 1.5% for structural/syntax errors
  (`ai-optimization-review-2026-08-13.md` item 6). `ports.yml`/`paths.yml`
  already carry eval-time asserts for exactly this reason; extend the same
  treatment to every enum-like or cross-reference field in
  `services.yml`/`roles.yml`/`launchd-writers.yml`. Schema-shape validation
  alone defends the smallest error category; this is what defends the
  largest one.

**Fields mandated by D16's composition half (§4.5.1) — these are schema, so
they land in Step 0, not later.** All three were decided 2026-08-13 and are
listed here because §4.5.1 argues them but this is the section that says
what the Site Model actually contains:

- **`provides` / `requires`, per type** (from (b)) — what a type supplies
  and what it needs, stated locally, from which `nix2cf` infers ordering
  edges. Deliberately *not* a cross-file `depends_on` list as the primary
  mechanism: explicit `depends_on` remains available and authoritative, but
  requiring it everywhere is the global-knowledge design R13 rejects. Edges
  in the compiled output carry provenance — authored (with source location)
  or inferred (with the rule that produced it).
- **`interlocks`, per bundle** (from (c)) — a stated precondition compiling
  to a CFEngine guard class plus a bundle-scoped refusal: a failing
  pre-action blocks modification of every entry in the enclosing bundle and
  is reported. The bundle is simultaneously the grouping unit and the
  re-verify scope.
- **`comprehensive` + `opt_out_reason`, per domain** (from (d)) — a domain
  is comprehensive unless it declares otherwise, and opting out requires a
  reason drawn from a closed set: `not-yet-migrated` (backlog, countable —
  this count *is* the build order's progress metric) or
  `deliberately-unmanaged` (permanent, rare). A bare boolean is
  insufficient by decision, not by oversight: the reason string is what
  keeps an agent from silently widening the unmanaged surface.

Anything present on the device and absent from a comprehensive domain's
description is reported as an **extra entry**. This is the only mechanism in
the design that detects multi-writer skew at all — CFEngine's default
posture, promising only about what is mentioned, cannot detect it by
construction.

### 4.2 Placement & consumption

Site Model lives in `site-<n>` (site data). Generic code lives fact-free
under `freeops/` (§11). **Boundary (decided 2026-08-13, recorded as
D21):** the Site Model *schemas* — the module-system type definitions and
the JSON Schema they render-validate against — belong to `nix2cf` (the
compiler layer's working name) as its public contract; the *instances*
(concrete site data, including site-pika's) live in the fleet/site repos
and are supplied through that contract. A schema change is a `nix2cf`
interface change; an instance change is site data.
**The repo exists as of 2026-08-13** — `djbclark/nix2cf`, created at Step 0
rather than Step 3 because this boundary leaves the schemas no other legal
home, and staging them somewhere else would have guaranteed a later move.
It currently holds the contract and its lint, and nothing else. Ubuntu/mise reads the model via a small generator
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

**Until D12's Nix frontend exists, the fallback path is the only path — add
a canonicalizing check there (D23, new).** `nix2cf/examples/services.yml`,
`roles.yml`, and `launchd-writers.yml` are all YAML today, because the
Nix-rendering pipeline is Step 3+ work, not yet built. **Checked directly
and correcting an earlier draft of this proposal:** no controlled study
found supports a general "LLMs generate JSON more reliably than YAML"
claim — format performance varies by model and task with no consistent
winner. What *is* real, independent of any LLM-specific study: YAML's own
spec has documented structural footguns regardless of author — implicit
type coercion (unquoted `no`/`yes`/`on`/`off` parsing as booleans),
indentation sensitivity, and alias/anchor ambiguity, which are exactly the
shape of the (real, §4.1/D28) "Structural Deficit" error class. Add a cheap
canonicalizing pre-commit step for the YAML fallback path — parse,
re-serialize, diff against the original — justified on the format's own
known ambiguity classes, not a comparative LLM-reliability claim
(`ai-optimization-review-2026-08-13.md` item 1).

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

**Required CLI affordance: render exactly what a named device would
receive, without touching it** (Bcfg2's `bcfg2-info buildfile`,
`bcfg2-papers-2026-08-13.md` §2). Because the render is a pure function of
the Site Model, this is nearly free for `nix2cf` — the same evaluation that
produces `def.json` for a deploy, parameterized by hostname and run
locally. It is worth building **first**, before the pipeline is complete,
for three separate reasons that happen to converge:

- **It is the agent self-check loop (R13).** An agent that can ask "what
  does this change actually do to device X" can verify its own work
  locally instead of guessing or deploying to find out — which is the
  cheapest possible form of catching mistakes automatically rather than by
  review.
- **It is the regression test for the compiler itself.** Bcfg2 used the
  `buildall` variant to diff every client's rendered output across server
  upgrades. A `nix2cf` change that alters output for a device nobody
  touched is exactly the bug class this catches, and it needs no fleet to
  run against.
- **It is decision transparency, which LISA '05 identifies as what
  actually buys administrator trust** — the binding constraint on their
  adoption, and directly applicable to site-pika's three admins.

**A second, complementary self-check affordance: registry lookups as a
tool call, not a file to read (D24, new).** `buildfile` answers "what does
device X receive"; this answers a smaller, more frequent question — "is
port 8080 free," "does this role exist" — without an agent reading
`ports.yml`/`roles.yml` in full. A `nix2cf registry check <domain> <field>
<value>` CLI (or equivalent) serves R13 (a targeted lookup is less
error-prone than skimming a whole file for one fact) and R12 at once: an
academic result on documentation retrieval (Wang & Zhang, arXiv:2509.19931)
found retrieving just the relevant fragment improves generation directly,
not only cost, and a widely-cited industry benchmark (not peer-reviewed,
cited at that weight) puts context-stuffing at roughly 2.7x the token/cost
of retrieval-as-a-tool for equivalent answer quality
(`ai-optimization-review-2026-08-13.md` item 2). Serving both R13 and R12
with one mechanism is unusual — those two objectives are more often in
tension elsewhere in this document (§14 exists because they aren't always
free to satisfy together).

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

#### 4.5.1 The multi-writer composition half of D16 (operator decisions, 2026-08-13)

The site-pika requirement change withdrew D16's governance half, leaving a
purely technical composition question. The Bcfg2 papers
(`bcfg2-papers-2026-08-13.md` §6) decomposed that into four sub-decisions.
**All four are now decided** — (a), (c) and (d) below, then (b), which R13
settled last and which is presented last because its argument depends on
the other three being in place. The schema consequences are recorded in
§4.1; the build-order consequences in §12 Step 0 and Step 3.

**(a) Same-resource conflict rule — DECIDED: compile-time error, with an
actionable message; leave room for a priority algebra.** When two writers
declare the same resource, `nix2cf` fails the build rather than resolving.
This follows Bcfg2's precedent (one plugin may provide content for a given
entry; on ambiguity the server *refuses to bind* and reports, rather than
picking a winner — booklet §5.1) and rejects silent last-wins outright,
because last-wins makes multi-writer skew invisible, which is the exact
failure (d) exists to catch.

The error is not merely a rejection: **resolution requires human input, so
the message must contain what a human needs to resolve it** — the resource
identity, every writer that declared it with source location, the
conflicting values, and a statement of what a resolution would look like.
An error that says only "conflict" pushes the work back onto whoever runs
the build; that is the opposite of the decision-transparency LISA '05
identifies as the thing that buys administrator trust (§5 of the papers
doc).

**Explicitly reserved:** the Nix module system already ships a priority
algebra (`mkDefault` / `mkForce` / `mkOverride`) with defined merge
semantics, and D12 already adopted that module system as the authoring
frontend. Type definitions must therefore be written so that adopting the
priority algebra later is a change of policy at the merge step, **not** a
schema redesign — the conflict check is a distinct compiler stage over
already-merged declarations, not logic fused into the type definitions.

**(c) Collective re-verify unit and interlocks — DECIDED: adopt Bcfg2's
model.** The bundle is both the grouping and the re-verification scope:
entries in a bundle are validated collectively, all member entries are
reverified when any one is modified, and services in a bundle are
restarted when any member changes (booklet §2.2.1). Interlocks become a
**first-class Site Model field** compiling to a CFEngine guard class plus a
bundle-scoped refusal, following Bcfg2 Actions' semantics: a failing
pre-action prevents modification of every entry in the enclosing bundle,
and the failure is reported centrally (booklet §A.2.1). This is what closes
`stayturgid#289` structurally — "Tailscale must be authenticated before
lockdown may be enforced" becomes a stated precondition with a defined
blast radius, rather than surviving as a safe default plus a comment.

**(d) Per-domain comprehensiveness — DECIDED: default-on, explicit
opt-out** (revised from opt-in later the same day on R13 grounds). A domain
is **comprehensive unless it declares otherwise**: anything present on the
device and absent from the Site Model's description of that domain is
reported as an **extra entry** (Bcfg2's two-way verification, CLUSTER '03
§2.2). This is the property that makes multi-writer skew detectable at all
— CFEngine's default posture, promising only about what is mentioned,
cannot detect it by construction — and under R13 it is also the primary
defence against AI-authored drift, which is why the default flipped.

**Opting out is explicit, per domain, and carries a stated reason.** A bare
boolean would let an agent widen the unmanaged surface silently, which is
precisely the R13 failure mode; requiring a reason string makes every gap
in coverage a visible, greppable, reviewable decision rather than an
absence.

**The distinction that makes default-on survivable:** an opted-out domain
is in one of two states, and they must not be conflated.

- **`not-yet-migrated`** — the domain has real device state nobody has
  described yet. This is the normal starting condition for everything, and
  it is a *backlog item*. Bcfg2's first client run reports
  `Total managed entries: 0 / Unmanaged entries: 2308`; the entire
  deployment story is grinding that second number down. Recording the
  migration state as a reason makes that backlog explicit and countable
  instead of invisible.
- **`deliberately-unmanaged`** — the domain holds state that is genuinely
  not ours to describe (user data, another tool's territory,
  device-generated caches). This one is permanent and should be rare.

Without that split, default-on either buries the operator in day-one noise
or pushes everyone to opt out broadly and never return — the failure mode
that makes comprehensiveness worthless in practice. With it, the
managed/unmanaged ratio per device is the build order's progress metric and
the `not-yet-migrated` count *is* the remaining work.

Sequencing is unchanged by the flip: bring domains under description
starting where several people plausibly write — the device app list, SSH
configuration, the `serverapp_*` launchd services.

**(b) Ordering mechanism — DECIDED: build the inference stage (AutoEdges
level), in v1, sequenced after the first two platform adapters exist.**
Convergence fixpoint remains the substrate underneath either way — CFEngine
re-runs and re-converges whether or not anything is ordered — and explicit
`depends_on` remains available and authoritative. The decision is that
`nix2cf` additionally *derives* edges, rather than relying on authors to
write every one.

**The reasoning is R13, and it inverts the cost analysis that pointed the
other way under human authorship.** Explicit `depends_on` is a
**global-knowledge** mechanism: to write the constraint, the author must
already know that someone else's resource exists and must run first.
Inference is a **local-knowledge** mechanism: each type states only what it
provides and what it needs, which is answerable from inside a single file
by an agent that has never seen the rest of the system. Under R13 that is
the whole ballgame — inference converts the one thing agents are reliably
bad at into the one thing they are reliably good at.

`stayturgid#288` is the confirming evidence and it is not hypothetical: a
hand-authored order in which `ensure_apps` installs after `app_privileges`
hardens, so anything added there goes unhardened for a full deploy cycle. A
list that contradicts its own stated rule is what accreted global-knowledge
ordering looks like, and the humans writing it did not catch it. Nor was
the cost side of the original analysis robust: "implement provides/requires
per type across every platform adapter" is mechanical, locally scoped,
well-specified work — the profile AI authorship is cheapest at, not most
expensive at.

Three constraints on the build, all of which follow from R13's second rule
rather than being separate preferences:

- **Sequencing: types first, inference second, both inside v1.** Useful
  provides/requires semantics cannot be designed before real type
  definitions exist on at least two platforms — inference rules invented
  ahead of the types they range over will encode guesses. This orders work
  within v1; it is not a deferral.
- **Edge attribution is mandatory, not a debugging nicety.** Every edge in
  the compiled output carries its provenance: authored (with source
  location) or inferred (with the rule that produced it). The failure mode
  inference introduces is a *spurious* edge, which presents as "why is this
  waiting?" and is harder to diagnose than a missing edge's "why did this
  fail?" — unless provenance makes it a query instead of an investigation.
- **Authored edges win, and are never silently duplicated or overridden by
  inferred ones.** Where both exist for the same pair, the authored edge is
  authoritative and the coincidence is reported, not hidden.

The residual risk R13 does not remove is **false confidence**: inference
that is mostly right invites authors, human and AI alike, to stop stating
constraints and trust the compiler. The mitigations are already decided
elsewhere — inferred edges are visible in dry-run/explain output (§7.3's
ChangePlan), and (d)'s two-way verification catches the residue that
ordering gets wrong.

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

**What this decision does NOT rest on (rationale corrected 2026-08-13):**
the licence. GPLv3 restricts depending on or deriving from Rudder's
*code*; it does not restrict running Rudder, managing nodes with it, or
authoring techniques/generic methods for it (configuration data, not
derived works), and Rudder grants an explicit plugin-licence exception
besides. Vendoring the bundle bodies is itself unproblematic — the
generic layer here is GPL-3.0-or-later anyway (§11). What keeps Rudder a
reference corpus rather than anything more is the platform matrix (no
macOS or Android agent at any tier; ARM absent from the Core repository,
checked directly against `repository.rudder.io`) and ncf's archived,
no-independent-release status. Full correction:
`rudder-as-umbrella-evaluation-2026-08-13.md` §4.
**Zero coverage for the actual hardest part:** ncf/Rudder targets Linux
and Windows only — no macOS/launchd story, no Android/Termux story. The
`serverapp_*` launchd-plist-and-brew pattern was always fleetopia-original
work regardless of this decision.

### 4.7 Local-first reporting: per-device SQLite is the record of truth (D18, new)

**Re-decided 2026-08-13 — same decision, new grounds.** The two rationales
originally recorded here are both off the record: the objection to
Rudder's Postgres-backed compliance DB is void (operator: "Postgres is
fine"), and local-first debuggability as a hard requirement was withdrawn
by the operator (2026-08-13, `bolt-choria-as-umbrella-2026-08-13.md`).
The decision stands on what actually survives:

1. **The local capture must exist regardless.** On CFEngine Community
   (the edition in scope) promise outcomes are captured by on-device glue
   either way (below); the local store is built no matter what. Promoting
   anything *else* to authoritative therefore adds a second system that
   must be kept complete and in sync — and as of 2026-08-13 that second
   system has **no consumer**: Choria's telemetry spine is dropped
   (`research-answers-and-corrections-2026-08-13.md`) and site-pika has no
   compliance UI requirement. Central-as-record is infrastructure without
   a customer; local-as-record is the null option.
2. **Completeness.** Devices in this fleet demonstrably go unreachable
   (Fire OS boot-recovery failures, flaky ADB-over-wireless, offline
   peers). Any central copy fed by best-effort sync is incomplete during
   exactly those windows; only the local copy is guaranteed complete.
   This is an operational fact about the fleet, not the withdrawn
   debuggability *requirement* — it makes the local copy the only
   candidate for "record," whether or not anyone requires debugging there.
3. **Single-writer-per-node symmetry (D20).** One SQLite file, one
   owning host, no concurrent-writer failure modes — the same principle
   the Nix store decision applies, not a new one.
4. **Weight class.** SQLite is trivially available on Termux with no
   server process — consistent with the adoptability instinct behind D6.

The local-first framing (Kleppmann, Hardy, Kaffman & van Hardenberg,
Ink & Switch 2019) remains the right *description* of the design — each
device holds its own authoritative copy; any central/shared view is
optional and eventually-consistent — it is just no longer load-bearing
as a requirement. (Same theoretical family as Couch's algebra and
Promise Theory — convergent, order-independent state.)

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

#### 4.7.1 Two schema requirements from the Bcfg2 papers (2026-08-13)

Both are recorded here rather than left to `nix2cf`'s future repo for the
same reason the §4.1 fields were: they are **schema**, and schema is
cheapest to get right before there are rows to migrate. Neither needs
`nix2cf` to exist.

- **Every row carries the release that produced it, and the device
  records which release it is currently converged to** (LISA '06's
  revision-stamping, `bcfg2-papers-2026-08-13.md` §3). Bcfg2 stamps every
  generated client configuration with the repository revision and carries
  it into every statistics upload; we already have the identifier —
  `ops-vMAJOR.MINOR.PATCH` and `ops-release.json` — so this is one column,
  not an integration. What it buys: the desired state of any device at any
  past time becomes reconstructible, "did this break after the last
  release" becomes a query rather than an argument, and "which devices
  were exposed, over what window, and when were they actually patched"
  becomes answerable. Given a fleet whose devices are routinely
  unreachable (ground 2 above), the reconstructibility is worth more here
  than it was in the paper's always-on cluster.
- **A managed/unmanaged counter per domain, not just a list of
  discrepancies.** §4.5.1(d) makes extra entries detectable; this makes
  the *ratio* a first-class recorded quantity, which is what turns
  comprehensiveness from a lint into a progress metric. Bcfg2's first
  client run reports `Total managed entries: 0 / Unmanaged entries: 2308`
  and the whole deployment story is grinding that second number down. Keep
  `not-yet-migrated` and `deliberately-unmanaged` counted **separately** —
  conflating them is what makes the number stop meaning anything, since
  one is backlog and the other is permanent by design.

**One reframing that follows, and it bears on ground 1 above.** D18's
first surviving ground is that central-as-record has no consumer. LISA
'05's deployment finding cuts the other way for the *local* store:
reporting deployed early was their explicit tip, and administrator trust —
not tool correctness — was the binding constraint on adoption for
precisely the multi-admin situation site-pika is in. So the local SQLite
plus a trivial "what changed, what is dirty, what am I converged to" view
is an **adoption requirement, not an observability nicety**, and it should
not be sequenced last on the grounds that nothing consumes it yet.

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

### 5.1 Linux — a stock mainstream distro is the reference (R5 hard fact)

> **Build-order note (2026-08-13):** Linux is **platform adapter #3**
> (§12 Step 4), after macOS and Android. It remains the *adoptability*
> keystone — the portability claim lives here — it is simply no longer the
> first thing built. **Which distro is open at that step.** R5's binding
> half is "no bare-metal Nix, and the reference must resemble what a
> stranger already runs"; Ubuntu Server LTS is the default answer to that
> and everything below is written for it, but any mainstream stock distro
> satisfies R5 equally (operator, 2026-08-13). Nothing before Step 4
> depends on the choice, so it is a decision to make with the reference
> host in front of you, not now.

- **Base OS:** Ubuntu Server LTS (default; see the note above), installed
  normally. No NixOS, no nixos-anywhere, no bare-metal Nix. A stranger
  clones the project onto their existing box and it works.
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

> **Build-order note (2026-08-13):** macOS is **platform adapter #1**
> (§12 Step 1) — the first platform brought under the Site Model. **This
> splits the section in two, and the split is what makes going first
> possible.** The *services* half (launchd services as CFEngine promises,
> §5.3) is Step 1 and depends on nothing unresolved. The *substrate* half
> below — nix-darwin, home-manager — is Step 7 and stays gated on §14.1.
> Read every "[NEEDS FABLE-5]" marker in this section as applying to the
> substrate half only.

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

> **Build-order note (2026-08-13):** Android is **platform adapter #2**
> (§12 Step 2). "Unchanged stack" below describes the *runtime* — nothing
> here is being replaced — but Android is no longer untouched build-order
> work: Step 2 brings the existing services under `services.yml` and types
> them with `provides`/`requires`, which is what supplies the second
> platform §12 Step 3 gates on. The stack stays; its *description* is new.

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
flashing as a task. Appliance-class devices → image-based atomic updates
(RAUC / SWUpdate+hawkBit / OSTree family): the whole image is a Nix-built
artifact, the flash/switch is a task, and the device is inventory — not a
new convergence path. Recorded as an extension point rather than a
D-number by operator decision 2026-08-13: "IoT growth" does mean
appliance-class devices, but as a nice-to-have, not a hard requirement.
All are Site Model inventory entries + artifacts, not new architecture.

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
`ops-release.json` already tracks. **Answered 2026-08-13
(`research-answers-and-corrections-2026-08-13.md` §3): parallel, keep
both.** `ops-release.json` is a three-field suite-coherence marker across
co-equal repos; `flake.lock` pins build inputs. `flake.lock` structurally
cannot express the former — it would require making one repo the root and
the others inputs, and the peer relationship is mutually referential,
which flake inputs (a DAG) cannot encode. The release check gains one
line (verify each repo's `flake.lock` is committed and clean at tag
time); nothing else changes.

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

**Ordering provenance (required by §4.5.1(b), recorded here because that
decision names this section as where the mitigation lives).** Each operation
additionally carries the ordering edges that constrain it, and every edge
carries its origin: `authored` (with source location) or `inferred` (with
the inference rule that produced it). This is not a debugging nicety. The
failure mode dependency inference introduces is a *spurious* edge, which
presents as "why is this waiting?" — strictly harder to diagnose than a
missing edge's "why did this fail?" — and provenance in the dry-run/explain
output is what turns that from an investigation into a query. Where an
authored and an inferred edge cover the same pair, the authored one is
authoritative and the coincidence is **reported, not silently collapsed**.
The exact encoding of edges in the IR is inside §14.2's scope along with the
rest of this schema; that they are present and attributed is not open.

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

**Generation discipline for the semantic layer (D29, new).** "Never
authorizes" bounds the blast radius but not the harm: a hallucinated claim
here can still mislead the human or their advisor AI, which is the actual
sovereignty guarantee §9 depends on. Citation-grounding research shows
forcing a model to cite the specific source it's summarizing measurably
reduces unsupported claims relative to free generation from the same facts
(general finding; the specific paper reused here, arXiv:2606.00898, is
about legal citations, not configuration management — the generalization is
this design's, not that paper's claim; `ai-optimization-review-2026-08-13.md`
item 7). Generate the semantic layer primarily by template-filling from the
verifiable IR's typed fields (`capability`, `resources`, `target`) wherever
a template covers the case; where free generation is used for a
novel/compound change, require it to quote or reference the specific IR
fields it describes, so a human or their advisor AI can mechanically check
the prose against the ground truth it claims to summarize.

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

> **Scope note (R13, 2026-08-13):** this section was written when
> AI-authorship risk was understood as a compile-target concern. **R13
> promoted it to a project-wide, first-order objective** — the guardrail
> thinking below now applies everywhere, and R13's two rules (prefer local
> knowledge to global; prefer machine-checkable to conventional) are the
> generalized form of it. Read this section as the worked example for the
> compile targets specifically, not as the boundary of the concern.

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
- ~~The §4.5 dependency audit (classifying `fleet.yml`'s role transitions
  as real dependencies or habit)~~ — **done 2026-08-13, and it validated
  the category.** All six roles declared zero real dependencies and the
  chain was found to contradict its own install-before-harden rule
  (`stayturgid#288`). Kept here as the worked precedent for this class of
  task: tedious for a human, mechanical for an AI, falsifiable by testing
  whether a role actually breaks without its predecessor.
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

**Sharper empirical grounding for the guardrail split above (D28, new; see
also §4.1).** A 2025 error taxonomy of real LLM-generated IaC (Nekrasov et
al., cited in the paper's §3.1) breaks failures into four categories:
factual incorrectness (invalid/nonexistent/deprecated/incompatible values)
at 65%, incompleteness at 26.5%, contextual reasoning failure
(cross-resource — the category §4.5.1(b)'s inference stage targets) at 7%,
and structural deficit (syntax) at just 1.5%. Schema validation, this
design's main automated guardrail, defends the smallest category; §4.1's
registry existence-checks (extended under D28) defend the largest one; and
D16(d)'s default-on comprehensiveness (§4.5.1(d)) already happens to be the
right structural answer to the second-largest, for reasons unrelated to why
it was originally decided. No design change here — this is why the
guardrails already chosen are aimed where they are, made explicit
(`ai-optimization-review-2026-08-13.md` item 6).

**Grammar-constrained decoding, worth a look when this guardrail is
actually built (D30, new).** The "no schema to check against" gap above is
narrower than it was when this section was written: grammar-constrained
decoding is now efficient enough for production use (Park, Zhou, D'Antoni,
arXiv:2502.05111), and a formal CFEngine promise-body grammar, written
once, could constrain *generation itself* at exactly this surface —
stronger than post-hoc lint, since invalid promise syntax becomes
unrepresentable rather than merely detectable
(`ai-optimization-review-2026-08-13.md` item 8). Not urgent — this escape
hatch isn't exercised until later build-order steps — but check for an
existing grammar or the cost of writing one before defaulting to lint-only
for this surface.

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

**The same fix applies to this document's own header (D27, new).** The
protection notice at the top of this file — "AI agents: DO NOT MODIFY
without explicit, specific human approval" — is currently prose, which is
precisely the pattern rule 6/R13's second clause warns against: a
convention an agent must remember is one it will eventually break silently
(`ai-optimization-review-2026-08-13.md` item 5). A pre-commit/CI check that
fails any diff touching `architecture-DEFINITIVE-v2.md` unless the commit
carries an explicit marker (e.g. an `Approved-change:` trailer) is the same
mechanism as the paragraph above, applied reflexively to this file.

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
and coherence_ order.

**Platform sequence: macOS, then Android, then Linux (operator decision,
2026-08-13).** This **reverses the pre-mortem correction this section
previously carried** ("prove the Ubuntu path before investing in Mac Nix").
That correction was reasoning about *Mac Nix* — the nix-darwin substrate
question — and it still holds for that, which is why the substrate step
remains late (Step 7). It does not bind the *macOS adapter*, and the two
were being conflated. §5.3 makes services CFEngine-owned on every platform
and §5.2 scopes nix-darwin to substrate only, so bringing macOS services
under the Site Model is fully separable from §14.1 and needs none of it
resolved.

Two consequences of the sequence, both deliberate:

- **The adoptability keystone is now proven third, not first.** Linux is
  where the portability claim lives (a stranger starts from a normal box),
  so it goes longest unvalidated. Accepted; the mitigation is that Step 4
  is a *reference* path built from an already-working compiler, not a
  from-scratch bring-up.
- **The first target converged is the one machine that cannot easily be
  reimaged** (§5.2). Step 1 therefore runs dry-run-first as a standing
  posture, not a courtesy — see the step. This is the same LISA '05
  finding §4.7.1 records: on machines that matter, dry-run and report is
  the default and auto-apply is the exception.

- **Step 0 — Site Model + fences (pure data, no runtime change).** Schemas
  for `services.yml`/`roles.yml`/`launchd-writers.yml`, **including the
  three D16 fields from §4.1** — `provides`/`requires` per type,
  `interlocks` per bundle, `comprehensive`/`opt_out_reason` per domain.
  _Schemas written 2026-08-13 and living in `djbclark/nix2cf` per D21
  (§4.2), alongside a `bin/schema_lint.py` carrying the cross-file rules
  JSON Schema cannot state on its own — reference resolution, launchd
  labels against the writer prefixes, no prefix nested in another. The
  remaining Step 0 work is transcription and the provenance gate, below._
  Those are schema decisions, so getting them in now is much cheaper than
  retrofitting them across transcribed reality later; nothing *consumes*
  them until Step 3, which is fine. Transcribe current reality — expect
  nearly every domain to start at `not-yet-migrated`, which is the normal
  day-one state (Bcfg2's first client run reports 0 managed / 2308
  unmanaged), and that count is the progress metric from here on. Lint in
  CI + pre-commit — including D25's schema/example-pairing check and D28's
  extended existence-checks; automate the worktree provenance gate (§8.1)
  and D27's self-protection check for this file; settle D23's YAML
  canonicalization step and stub D24's registry-lookup CLI here too, since
  all four are schema/tooling work with no runtime dependency, the same
  reason the original three D16 fields landed in this step. Settle
  D18's row schema here too (§4.7.1) even though nothing writes rows yet —
  the release stamp and the separated managed/`not-yet-migrated`/
  `deliberately-unmanaged` counters are one column each now and a migration
  later. Coherent stop: same system, now with a truthful data spine and a
  provenance gate. _Also the cheapest possible agent work — good first task
  under the budget._
- **Step 1 — macOS services adapter (platform adapter #1).** Render the
  Mac's `com.djbclark.*` / `com.stayturgid.*` launchd services as CFEngine
  promises from `services.yml` (§5.3). **Explicitly *not* in this step:
  nix-darwin, home-manager, or anything substrate — that is Step 7 and is
  gated on §14.1.** Keeping the boundary sharp here is what makes macOS
  viable as the first adapter at all; blur it and this step inherits an
  unresolved premium-token decision it does not need.
  **Dry-run is the default posture and it starts here** (§12 intro): render,
  diff, read the report, and only then enforce. The `launchd-writers.yml`
  lint is the safety rail that makes this survivable on a live daily driver
  — a promise that would write outside CFEngine's declared label prefix
  fails the lint before it reaches the machine. Coherent stop: the Mac's
  services are declarative and reproducible, with every other part of the
  Mac untouched and unmanaged.
- **Step 2 — Android under the Site Model (platform adapter #2).** Bring
  the existing Termux/stayturgid-agent/CFEngine stack (§5.4) under the same
  `services.yml` description the Mac now uses, and write `provides`/
  `requires` for the Termux types. CFEngine already runs on Termux in
  production, so this is mostly transcribing reality and typing it, not a
  bring-up. Expect the honest first-run numbers here — most Android domains
  land as `not-yet-migrated` (§4.1), and that count is the backlog. Coherent
  stop: two platforms describe themselves in one vocabulary, which is the
  precondition the next step needs.
- **Step 3 — `nix2cf` compiler stages (gate: Steps 1–2 complete).** The
  merge → conflict-check → inference → render pipeline of §4.5.1, in v1.
  **Sequencing is a decision, not a preference:** types first, inference
  second, and inference does not start until real type definitions exist on
  **two** platforms — satisfied by macOS + Android. Inference rules invented
  ahead of the types they range over encode guesses; two adapters is the
  minimum that exposes which `provides`/`requires` relations are general and
  which were one-platform-shaped. _macOS + Android is a deliberately
  wide-apart pair — launchd and Termux share almost no assumptions — so
  rules that survive both are unlikely to be parochial. The residual risk
  runs the other way: rules co-designed on two non-FHS-typical platforms may
  need revisiting when Linux lands at Step 4. Treat Step 4 as the
  generality test for inference, and expect to revise rules there rather
  than being surprised by it._ Order within the step: (0) the
  `buildfile`-style render-what-device-X-receives CLI (§4.4) — first,
  because it is the self-check loop and the compiler's own regression test,
  so everything after it is cheaper to verify; (1) conflict check as a
  distinct compiler stage over already-merged declarations — never fused
  into the type definitions, so the Nix priority algebra can be adopted
  later as a policy change rather than a schema redesign; (2) extra-entry
  reporting, which needs no inference and starts paying immediately; (3) the
  AutoEdges-style inference stage with mandatory edge attribution. Coherent
  stop: the Site Model compiles, conflicts fail the build with resolvable
  messages, and skew is visible — with or without inference finished.
- **Step 4 — Linux reference path (platform adapter #3, the adoptability
  keystone).** mise `bootstrap` (toolchains only) + `nix2cf`-rendered
  CFEngine promises bring up a real Linux host from the Site Model. This is
  where the portability claim gets proven, and where inference rules meet a
  filesystem layout that neither earlier adapter has. Do it before you own a
  VPS, by rendering + dry-running against a throwaway box or container-like
  target. **Open at this step: which distro.** R5's hard half — no
  bare-metal Nix, the reference must resemble what a stranger already runs
  — is untouched and binding. Which mainstream distro satisfies it is
  revisitable (operator, 2026-08-13: "Ubuntu, or maybe a different
  distro"); §5.1 still reads Ubuntu Server as the default and nothing before
  this step depends on the answer. Coherent stop: the reference deployment
  provably works on a stock distro install.
- **Step 5 — First real Linux host.** Provision a VPS (Hetzner); give it
  backup/shadow roles (observability mirror, backup) — **not** obs-main yet.
  Proves R2 (flip a role's main to it and back) and gives the role mesh a
  second real node. Coherent stop: a genuine second host; destroy it and the
  Mac/fleet are unchanged.
- **Step 6 — Signed releases (push-only) + typed executor.** TUF-subset root
  ceremony; manifest + ChangePlan generation in `ops-release-*` (the
  ChangePlan now carries the ordering provenance of §7.3, since Step 3's
  inference is what makes attribution necessary); the capability-enforcing
  executor on CFEngine (§7.3, §8). Push-only, operator hosts. Coherent stop:
  every deploy is a signed, execution-constrained plan; no autonomous
  anything yet.
- **Step 7 — Mac substrate (the interesting, optional Nix step).** If §14.1
  resolves toward nix-darwin: bring the Mac substrate under nix-darwin +
  home-manager, services still CFEngine from Step 1. Fully reversible
  (`darwin-rebuild --rollback`). This is the step the pre-mortem's
  "exit-before-Mac-Nix" caution was always actually about, and it stays late
  for exactly that reason. Coherent stop: Mac substrate is declarative;
  nothing depends on it that couldn't run on the mise path.
- **Step 8 — Pull convergence.** Converge agent with the full §7.2 client
  protocol + §8 quotas. Any host with the role self-updates. Coherent stop:
  the no-control-node end state exists as data.
- **Step 9 — Consent/sovereignty v1 (agent 2.0).** The consent surface on one
  fleet device, then the advisor and personal-branch loop (§9), each behind
  its §8 gate. This is the payoff — the freedom feature — built on everything
  below it.
- **Step 10+ — demand-driven.** builder/cache (when a non-substitutable
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

**How this squares with R13, since they can look opposed:** R13 says AI
authorship is the primary model and the design must optimize for it; this
section says four things need premium models. Both hold, because they act
on different variables. R13 governs **how the system is designed** — local
knowledge over global, machine-checkable over conventional — so that a
cheap model authoring against it succeeds by construction. §14 governs
**where the design itself is still undetermined**, and a cheap model's
failure there is not an authorship error a schema could catch; it is an
unmade decision being improvised. R13 is what makes the "everywhere else"
in the sentence above large; §14 is the residue R13 cannot shrink. The two
compound rather than compete: every §14 item resolved *well* makes more of
the system safely cheap to author.

- **§14.1 — nix-darwin on the Mac, yes or no.** The fun/coherence fork (§5.2).
  Multi-AI, low security stakes; a Nix-idiom specialist pass would help.
  **Not urgent, and specifically *not* a prerequisite for macOS going first
  in the build order** — it gates the Mac *substrate* (§12 Step 7), not the
  macOS services adapter (Step 1), which needs none of it. Resolvable any
  time before Step 7.
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
| D15 (new) | Nix→CFEngine compile target | **CFEngine's native Augments layer (`def.json`/`host_specific.json`), not raw `.cf` synthesis** (§4.4). Merging happens once, in Nix, before render — CFEngine's `mergedata()` is not used for this, to avoid a second, divergent merge engine. Still unprototyped as of 2026-08-13; the augments-load-under-standalone-`cf-agent -f` precondition (`research-answers-and-corrections-2026-08-13.md`) is **assumed satisfied by operator decision 2026-08-13** — verifying it stays on the task list as validation, not as a gate. |
| D16 (new) | Order-dependent operations | **Puppet-catalog-JSON rejected — do not build it** (§4.5). The gating `fleet/fleet.yml` Android-chain audit (2026-08-13) came back negative: all six roles declare zero dependencies, every apparent intra-chain prerequisite is satisfied by an earlier `site.yml` playbook, and the chain contradicts its own install-before-harden rule (`stayturgid#288`). Re-derived semantically, the real cold-device constraints are a strictly sequential six-node transport bootstrap (a `bundlesequence`), independent non-interleaving per-app chains (CFEngine classes/`depends_on`), and safety interlocks that a catalog cannot express at all (`stayturgid#289`, `#290`). **Rejected; semantic verdict accepted as a working assumption by operator decision 2026-08-13** — a real from-scratch provision remains the validation step (and the right forcing function for the bootstrap/interlock designs) but is no longer a gate on proceeding. The surviving **multi-writer composition** half is fully decided (§4.5.1, operator 2026-08-13; schema consequences in §4.1, build-order consequences in §12 Step 0 and Step 3): **(a)** same-resource conflict is a compile-time error carrying enough detail for a human to resolve it, with the Nix priority algebra explicitly reserved as a later policy change rather than a schema redesign; **(c)** the bundle is the collective re-verify unit and interlocks are a first-class Site Model field compiling to a CFEngine guard class with bundle-scoped refusal (Bcfg2 Actions' semantics — closes `stayturgid#289` structurally); **(d)** per-domain comprehensiveness is **default-on with explicit, reasoned opt-out** (revised from opt-in on R13 grounds), making out-of-band and cross-writer skew visible as extra entries; opt-out reasons split `not-yet-migrated` (backlog, countable, the build order's progress metric) from `deliberately-unmanaged` (permanent, rare). **(b)** `nix2cf` builds an AutoEdges-style dependency-inference stage, in v1, sequenced after the first two platform adapters (macOS then Android, per the 2026-08-13 platform sequence — §12 Steps 1–2); fixpoint stays the substrate and explicit `depends_on` stays authoritative, with mandatory edge attribution (authored vs inferred) and authored-wins on collision. Decided on **R13** grounds: explicit ordering is a global-knowledge mechanism and inference is a local-knowledge one, which inverts the cost analysis under AI authorship — `stayturgid#288` is the confirming instance of hand-authored global ordering failing. **D16's composition half is now fully decided.** |
| D17 (new) | ncf/Rudder reuse            | **Vendor and adapt individual generic-method bundle bodies as a reference corpus, strip Rudder's reporting scaffolding** (§4.6). Not a dependency — `ncf` is archived, folded into the Rudder monorepo, no independent release to track. Zero coverage for macOS/Android; that work was always fleetopia-original. **Rationale corrected 2026-08-13:** the licence is *not* what limits Rudder use — GPLv3 restricts deriving from Rudder's code, not running it or authoring techniques for it, and Rudder grants a plugin-licence exception; the platform matrix and ncf's archived status are the real limits (§4.6, `rudder-as-umbrella-evaluation-2026-08-13.md` §4). |
| D18 (new) | Local-first reporting        | **Per-device SQLite (owned by `stayturgid-agent`) is the authoritative record, not the central observability stack** (§4.7). **Re-decided 2026-08-13 on new grounds** — the original rationales are off the record (Postgres objection void per operator; local-first debuggability withdrawn as a hard requirement). Surviving grounds: the local capture must exist anyway on CFEngine Community, so local-as-record is the null option while central-as-record is a second system with no remaining consumer (Choria telemetry spine dropped, no site-pika compliance UI); only the local copy is guaranteed complete across this fleet's real unreachability windows; single-writer-per-node symmetry with D20; SQLite's weight class fits Termux. Sync to Vector/OpenObserve/Grafana stays optional and best-effort. |
| D19 (new) | Nix Flakes + flake-parts     | **Adopted** (§6.1) — one flake per repo, `fleetopia`'s flake as the shared module-system library the other three repos import, flake-parts for internal composition. `flake.lock` vs. `ops-release.json` overlap **answered 2026-08-13: parallel, keep both** — `ops-release.json` is a suite-coherence marker across co-equal repos, which `flake.lock` (a DAG of inputs under one root) structurally cannot express; the release check gains one line (§6.1, `research-answers-and-corrections-2026-08-13.md` §3). Nix store locality (D20, §4.8) applies to every flake `packages` build. |
| D20 (new) | Nix store locality             | **Never point `NIX_STORE_DIR` or the store's `db.sqlite` at shared/network storage written by more than one host** (§4.8). Single-writer-per-host is Nix's own default and its documented failure mode under multi-host writes (NixOS/nix#378). Same principle as D18's local-first SQLite, applied to Nix's own store. Previously recorded only as an aside inside D19; promoted to its own row 2026-08-13. |
| D21 (new) | Site Model schema/instance boundary | **Schemas belong to `nix2cf` as its public contract; instances live in the fleet/site repos** (§4.2, §6.1). The module-system type definitions and the JSON Schema they validate against are the compiler layer's interface — versioned and released with `nix2cf`; concrete site data (including site-pika's) is supplied through that interface from each site repo. Decided 2026-08-13 (recorded 2026-08-13; `nix2cf` remains the working name until naming is finalized). |

| D22 (new) | Platform build sequence      | **macOS first, Android second, Linux third** (§12; notes in §5.1/§5.2/§5.4). Operator decision 2026-08-13. **Reverses the pre-mortem's "prove the Ubuntu path before investing in Mac Nix"** as applied to the macOS *adapter* — that caution was reasoning about the nix-darwin *substrate*, which remains late (Step 7) and remains gated on §14.1. The two had been conflated; §5.3 (services are CFEngine-owned on every platform) and §5.2 (nix-darwin owns substrate only) are what make them separable, so Step 1 needs no premium-token decision resolved. Accepted consequences: the adoptability keystone is proven third rather than first, and the first machine converged is the one that cannot easily be reimaged — mitigated by dry-run-first posture and the `launchd-writers.yml` lint, not by reordering. **Also softens R5's distro half:** "no bare-metal Nix, must resemble what a stranger runs" binds; *which* mainstream distro is open until Step 4 (operator: "Ubuntu, or maybe a different distro"). |

| # | Decision | Resolution |
| --- | --- | --- |
| D23 (new) | Site Model fallback-authoring format | **Add a canonicalizing pre-commit check (parse, re-serialize, diff) for the YAML fallback path** (§4.3) — until D12's Nix frontend exists, YAML is the only authoring path in practice (`nix2cf/examples/*.yml`). Originally proposed as "prefer JSON, LLMs generate it more reliably"; checked directly against the cited study and **that claim does not hold** — no consistent format winner across models/tasks. Kept on YAML's own documented spec ambiguities (type coercion, indentation, anchors) instead, independent of any LLM-specific claim. |
| D24 (new) | Registry lookup CLI | **A `nix2cf registry check` (or equivalent) tool-call lookup, alongside the `buildfile` self-check CLI** (§4.4) — answers a single registry fact without an agent reading the whole file. Serves R13 (accuracy) and R12 (token budget) simultaneously — one of the few places those objectives aren't in tension. |
| D25 (new) | Schema/example pairing enforcement | **`bin/schema_lint.py` fails if any `schema/*.schema.json` lacks a matching `examples/*.yml`, or vice versa** (§4.1) — the pairing already exists in `nix2cf`; this makes it checked, not customary. |
| D26 (new) | Root `AGENTS.md` per repo | **Checked, not adopted on a performance rationale — see §16.** The dedicated study found context files do not generally improve task success and raise cost 20%+; recorded so this isn't re-proposed and re-researched later. If ever added, discoverability only, minimal, hand-curated. |
| D27 (new) | This document's own edit-protection, mechanized | **A pre-commit/CI check fails any diff touching `architecture-DEFINITIVE-v2.md` without an explicit `Approved-change:` trailer** (§8.1) — the same automated-check-not-prose treatment §8.1 already gives the worktree-provenance problem, applied to this file's own header notice. |
| D28 (new) | Guardrails weighted by the real IaC error distribution | **No design change; makes explicit why existing guardrails are aimed where they are** (§4.1, §4.5.1(d), §7.5). Real LLM-IaC errors: 65% factual incorrectness, 26.5% incompleteness, 7% contextual reasoning failure, 1.5% structural (Nekrasov et al., paper §3.1; percentages re-verified directly against the paper's table). Registry existence-checks (extended past ports/paths) defend the largest category; D16(d)'s default-on comprehensiveness already happens to defend the second-largest; schema validation alone defends the smallest. |
| D29 (new) | Semantic-layer generation discipline | **Template-fill the ChangePlan's semantic layer from the verifiable IR's typed fields wherever a template covers the case; free generation must quote/reference the specific IR fields it describes** (§7.3). "Never authorizes" bounds the blast radius, not the harm — a hallucinated claim can still mislead the human or their advisor AI, which is the sovereignty guarantee §9 actually depends on. |
| D30 (new) | Grammar-constrained decoding for the CFEngine escape hatch | **Check for or write a formal CFEngine promise-body grammar before defaulting to lint-only for `commands`-type freehand text** (§7.5) — grammar-constrained decoding is now efficient enough for production use, turning "no schema to check against" into a real option. Not urgent; this surface isn't exercised until later build-order steps. |
| D31 (new) | Front-or-back positional convention, named | **Critical information goes at the very start or very end of any agent-facing artifact, never buried mid-document** (§0 rule 7). Already practiced here (§0 is "read this first"); apply deliberately to rendered outputs (`def.json`/`host_specific.json`, the ChangePlan) going forward. |

**D23–D31 provenance:** proposed in `ai-optimization-review-2026-08-13.md`
(literature review, requested by the operator to find further concrete
AI-authorship optimizations beyond R13's existing scope); four of the nine
original claims (1, 2, 3, 4 — now D23, D24, D25, D26) were corrected in
place the same day after direct source verification found the original
numbers didn't hold up, D26 most substantially (the proposed benefit was
reversed by its own primary source). **Adopted in full, including D26's
negative result, by operator decision 2026-08-13.**

Silence = proceed from Step 0. Objections amend this register, not the
archived documents.

---

## 16. Document map (for the next AI)

**D26, new: root `AGENTS.md` — checked, and not adopted on a performance
rationale.** `AGENTS.md` is a real Linux-Foundation-governed cross-tool
discovery convention (read natively by Claude Code, Codex CLI, Cursor,
Aider, Devin, Copilot, Gemini CLI, Windsurf, Amazon Q). It was proposed here
on a performance claim that did not survive checking against its primary
source: the dedicated study (Gloaguen et al., ETH Zürich, arXiv:2602.11988)
found context files — LLM-generated *and* developer-written — do not
generally improve task success and increase inference cost 20%+;
LLM-generated files specifically *reduced* success versus no context file
at all (`ai-optimization-review-2026-08-13.md` item 4, corrected in place
2026-08-13). **Decision: do not add one on the strength of a performance
argument, because there isn't one.** If a root `AGENTS.md` is ever added —
`fleetopia`/`nix2cf`/eventually the site repos, once Step 0+ lands real
code — the only defensible reason is discoverability, and it must be
minimal and hand-curated pointing to §0, never LLM-generated boilerplate or
a repository-overview dump (the study's specific failure mode). Recorded
here so a future agent doesn't re-propose this and re-run the same research
to the same answer.

- `ai-optimization-review-2026-08-13.md` — the literature pass behind D23,
  D24, D25, D26 (above), D27, D28, D29, D30, D31. **Adopted in full by
  operator decision 2026-08-13**, including item 4/D26's negative result.
  Full rationale, citations, and the correction history (four claims
  fixed same-day after direct source verification) live there; not
  duplicated here.
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
  apply; its _logical_ points (coherent stops, two-writers,
  no-consent-UI-before-executor) are kept and live in §8/§12.
  **Its exit-before-Mac-Nix point was narrowed 2026-08-13:** it holds for
  the nix-darwin *substrate* (§12 Step 7, still late) but was being applied
  to the macOS *adapter*, which is a different thing and now goes first
  (Step 1). The distinction is §5.2's build-order note.
- `orchestration-research-2026-08-13.md` — the non-VM orchestration research
  leg: Rudder's Core-vs-plugin RBAC split (resolved), Bolt/Choria against the
  operator's two hard constraints, Bcfg2's fixpoint-loop answer to ordering,
  `mgmt`'s AutoEdges as a shipped dependency-inference precedent, and the
  image-based-update gap. Was evidence for the then-pending D16
  conversation; **D16 has since been decided in full** (§4.5.1) and
  AutoEdges is now the adopted model for (b). Amends no decision itself.
- `rudder-as-umbrella-evaluation-2026-08-13.md` — evaluates adopting Rudder
  wholesale and extending it for Termux/Android. Verdict: no (no macOS or
  Android agent at any tier; ARM packages absent from the Core repository,
  checked directly). Contains a **correction to D17's stated rationale** —
  GPLv3 blocks depending on Rudder's *code*, not running it or writing
  techniques for it, and Rudder grants a plugin exception. Amends no
  decision; **the D17 text was corrected 2026-08-13 (commit `2dd3264`) —
  no longer outstanding.**
- `bolt-choria-as-umbrella-2026-08-13.md` — the same question asked of Bolt
  and Choria, plus the operator's withdrawal of local-first debuggability as
  a hard requirement. Bolt: no (inherits the puppet-agent matrix and the
  25-node packaging EULA via `bolt apply`, push-only). **Choria: the only
  candidate that reaches every platform in the fleet** — `darwin/arm64` and
  `linux/arm64` are first-class FOSS build targets — but it fills D14's
  transport slot, not D13's convergence slot. Choria was subsequently
  **dropped** (see `research-answers-and-corrections` below). Its
  observation that **D18 had no surviving stated rationale** was acted on:
  D18 was **re-decided on new grounds 2026-08-13** (commit `2dd3264`) and
  the register row now carries those, not the void ones.
- `site-pika-requirement-change-2026-08-13.md` — **read this before the other
  two umbrella docs**, it supersedes their site-pika assumptions. Three
  root-trusted admins, no GUI ⇒ **Rudder drops out entirely** and the
  "two systems" conclusion reverses to one. D16 narrows to a
  composition-only question; blast radius and multi-author composition
  survive, authorization and tenancy do not.
- `research-answers-and-corrections-2026-08-13.md` — **the current head of
  this chain; read it before the three docs above, it corrects them.**
  CFEngine on Termux is in production (closes that item); Choria is
  **dropped** — its sole justification was platform reach and
  `cf-runagent-wrapper.sh` already exists; D19's open question is answered
  (`flake.lock` and `ops-release.json` are parallel, keep both); `mgmt`
  AutoEdges mechanism documented; **D15 is unprototyped and has a new
  precondition** — verify augments load under standalone `cf-agent -f`.
- `bcfg2-papers-2026-08-13.md` — all four Bcfg2 papers (CLUSTER '03,
  LISA '05, LISA '06, SAGE booklet #19) read and mapped onto this design.
  Extends the one-line Bcfg2 entry in `orchestration-research`. Headline:
  **two-way verification / per-domain comprehensiveness** is the property
  that makes multi-writer skew detectable at all, and it is a Site Model
  schema decision — so it belongs in the D16 conversation and before
  Step 0. Also: revision-stamped client reports (maps onto `ops-v*` tags
  for D18's SQLite), Bcfg2 Actions' bundle-blocking pre-actions as the
  interlock precedent for `stayturgid#289`, `bcfg2-info buildfile` as a
  nix2cf CLI affordance, and LISA '05's finding that trust — bought with
  dry-run plus reporting — is the adoption gate. **Its §6 decomposition of
  D16 into four operator decisions was the agenda that D16 was then decided
  against** — so, unusually for a research doc here, this one is *upstream
  of an amendment*: §4.5.1 and the §4.1 schema fields are its output, and
  its comprehensiveness recommendation landed in Step 0 as predicted.
- `ideas-dump-claude.md` — unprotected; the two-agent-consent control, the
  semantic/verifiable plan split, the role-mesh-is-consensus flag, and the
  model/vendor notes all graduated into this document.

### 16.1 Prior-art bibliography (D13–D21 research, 2026-08-13 session)

Not archived as separate documents — captured here so the D13–D21 decisions
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
