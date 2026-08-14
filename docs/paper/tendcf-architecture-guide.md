# How tendcf works

**A companion to the technical paper.** Same architecture, plainer language.
This version describes the system as it is designed today, and what is
planned next. It does not recount how the design was reached.

Draft for review — not published, not submitted.
Daniel Joseph Barnhart Clark (djbclark@mit.edu).
Prepared 2026-08-14.

The technical paper, with citations and open questions in research form, is
[`tendcf-architecture-paper.md`](tendcf-architecture-paper.md).

**Nothing described here is deployed.** The data formats exist and are
checked. The compiler, the on-device executor, and the screens a person
would use to accept or refuse a change are still to be built. No device has
been set up from factory reset by this automation.

---

## 1. What this is

`tendcf` is a design for keeping a mixed set of computers in an agreed
state: Apple Silicon Macs, Linux machines (Intel and ARM), and Android
devices reached through Termux. The computers are often offline. More than
one trusted person can act. There is no dedicated operations staff, and no
always-on central server that every device must reach.

Most of the configuration will be written by AI coding agents, not typed by
a person. People still decide what should happen. A person whose computer is
managed should be able to read a proposed change in ordinary language and
refuse it.

Two other goals sit alongside that:

- The generic machinery is publishable. Someone else should be able to
  supply their own facts and run the same code.
- The installed OS on a new Linux box is an ordinary distribution, not
  NixOS. Nix is used for builds and (later) as an optional way to *write*
  site data. It is not the thing a stranger has to install as their
  operating system.

---

## 2. The picture

```
  Site Model          facts about the fleet (inventory, ports, paths,
  (data files)        services, roles, keys). Schema-checked. No behavior.

          │
          ▼
  nix2cf              merge layers → catch conflicts → derive ordering
  (compiler)          → emit CFEngine JSON data. Pure: same input, same
                      output. Can show what device X would get without
                      touching device X.

          │
          ▼
  Signed release      a versioned, signed package: the rendered data plus
                      a typed plan of allowed operations for each host.

          │
     ┌────┴────┐
     ▼         ▼
   push       pull     same mechanism. An operator can trigger a run now;
                       a device can also pick up the next signed release
                       on its own schedule.

          │
          ▼
  CFEngine on         already-existing engine. Checks the machine, fixes
  every device        what is wrong, checks again. Each device runs its
                      own copy. No dedicated policy server.

          │
          ▼
  Local SQLite        that device's record of what actually happened.
                      Any shared dashboard is optional and can be stale.
```

Four ideas in this picture come from Bcfg2, a configuration system built at
Argonne and described in a series of papers by Narayan Desai and
colleagues. They are credited in the sections that use them. CFEngine is
the on-device engine; `tendcf` does not replace it.

---

## 3. Facts live in one place

Every fact about the site lives in a set of checked YAML/JSON files called
the **Site Model**:

- which computers exist, and what kind they are
- which ports and paths are allocated
- what services run, as which user, with which command
- which host currently holds which role (including “may deploy”)
- who is allowed to write which family of macOS launchd jobs
- signing-key identifiers and trust tiers

Behavior lives in generic code that holds none of those facts. Adapters
translate. CFEngine, the toolchain bootstrapper, and Nix-for-builds are
*consumers* of the Site Model. Any one of them can be replaced without
moving the facts.

That split is what makes the generic layer publishable: another person
brings their own Site Model, through the same schema, and the code does not
need to know their hostnames.

Three record types do most of the work.

**Services.** One record per service: name, run-as user, command,
environment as *names* of secrets (never the secret values), which role it
binds to, who owns it. Every launchd plist and systemd unit in the fleet is
meant to be a rendering of one such record.

**Roles.** A feature role maps to `{main, backups[], peers[]}`. “The control
node” is not a machine. It is a row in this file. Any eligible host can
hold any role.

**Launchd writers.** Exactly one writer per launchd label prefix
(`com.djbclark.*`, `com.stayturgid.*`, and so on). Two tools writing the
same plist is a class of outage this file is meant to make impossible.

The Site Model may later be *authored* in the Nix module system
(`mkOption`, `mkIf`, `mkDefault`) and rendered to the same JSON everything
else consumes. That is an authoring frontend only. The rendered JSON is
what is schema-checked, signed, and read downstream. Nobody adopting the
project has to know Nix to read or fork their own site data. Until that
frontend exists, the files are written as YAML.

Schemas live in a separate repository, [`nix2cf`](https://github.com/djbclark/nix2cf).
Concrete site files live in the site’s own repos. A schema change is an
interface change; a hostname change is site data. They do not move
together.

Every schema is paired with a concrete example file. The lint fails if a
schema arrives without its example, or the other way around. A lookup
command is planned so an agent can ask “is port 8080 free?” without reading
the whole registry.

---

## 4. A compiler turns facts into CFEngine data

The compiler (working name `nix2cf`) reads the Site Model and writes
**CFEngine Augments** — JSON files (`def.json`, `host_specific.json`) that
CFEngine has accepted as a native data-injection layer since version 3.7.

CFEngine’s standard library is already largely data-driven on top of that
layer. For the common case the compiler therefore emits *data*, not
CFEngine source text. A generic bundle written once handles “this package
is present and pinned, these directories exist, this service is loaded”
for any entry in the data. Only promise types the stock library does not
cover need policy text, and that text is filled in from typed option
values, not invented freely.

The pipeline has four stages:

1. **Merge** site, role, and host layers into one picture per device.
2. **Conflict check** over that already-merged picture. Two writers claiming
   the same port or path is a build failure, not last-wins. The error names
   the resource, every writer that declared it and where, the conflicting
   values, and what a resolution would look like. The reader of that
   message is usually an agent that cannot go exploring for the missing
   half.
3. **Dependency inference** — see §9.
4. **Render** the Augments JSON.

Merge happens once, in the compiler, before render. CFEngine’s own
`mergedata()` is not used for this, so there is one merge engine rather
than two.

Because the render is a pure function of the Site Model — same input, same
output — “show me exactly what device X would receive, without touching
device X” is almost free. That command is planned as the first piece of
the compiler, before the rest of the pipeline is finished. It is:

- how an agent checks its own work locally
- how the compiler regression-tests itself (a compiler change that alters
  output for a device nobody touched is exactly the bug it catches)
- how a human sees a proposed change before it lands

Compiling a typed description into an existing engine’s native format is a
known pattern. NixOS does it into systemd units; nix-darwin does it into
launchd agents; cdk8s does it into Kubernetes YAML. The pairing here is
Nix-or-YAML site data into CFEngine Augments. The reason for that target
is CFEngine’s fit to disconnected, multi-owner operation (§5), not the
compiler mechanism itself.

---

## 5. Every device runs its own agent

Each computer runs CFEngine, including its own `cf-serverd`, and reads
policy that arrived as part of the ordinary signed-release path, synced
via git. There is no dedicated central policy host, no SSH requirement,
and no requirement to push.

Push still exists: a host that currently holds a deploy role can trigger
an immediate run on a target, rather than waiting for that target’s next
cycle. Push and pull are two modes of the same mechanism.

CFEngine’s usual textbook deployment is hub-and-spoke: one policy server,
clients pulling from it. The shape here is different and still supported:
a host may bootstrap as its own policy hub when its declared server
address is itself. Applied fleet-wide, off a shared git-synced source,
that is closer to GitOps (an in-place agent pulling desired state from
git, no push, no reachable control plane holding credentials) than to
CFEngine’s brochure diagram. balenaCloud is the closest working system
for the often-offline half — offline-tolerant updates, tracking of
degraded connectivity — with one architectural difference: its devices
phone home to a hosted service. This design has nothing to phone home to.

The “no control node” property is CFEngine’s own (Promise Theory: each
machine is an independent agent that keeps its own promises). What this
design adds is the fleet-wide self-hub plus git-synced source, and the
Site Model that says who currently holds which role.

---

## 6. Each device keeps its own record

Each device owns a SQLite database, filled from CFEngine’s local
promise-outcome log. **That database is the authoritative record of what
converged on that device.** Any central or shared view is optional and
eventually consistent.

Two reasons, both operational:

- On CFEngine Community the local capture has to be built anyway, so
  local-as-record is the default and central-as-record is a second system
  to keep complete and in sync.
- Devices in this fleet do go unreachable — flaky wireless debugging,
  Android boot-recovery failures, peers that are simply off. A central
  copy fed by best-effort sync is incomplete during exactly the windows
  one would want it.

The outcome words are borrowed from Rudder’s `ncf` library, used here as a
reference vocabulary rather than as a runtime dependency:
`success` / `repaired` / `error` / `n-a` in enforce mode,
`compliant` / `noncompliant` / `error` / `n-a` in audit mode.

A path to a fleet-wide view already exists and costs nothing new to stand
up: a subset of each device’s SQLite can push, best-effort, into the
observability stack this fleet already runs (Vector / OpenObserve /
Grafana). That view is never the record of truth. When a question such as
“did the security rollout land everywhere?” needs a real yes or no,
reachable devices are queried directly and the rest are treated as
unknown, not as a stale aggregate.

Every report row carries the release that produced it. Each device records
which release it is converged to. The desired state of a device at a past
time is then reconstructible, and “did this break after the last release”
is a query.

---

## 7. Changes arrive as signed plans

Configuration reaches devices only as a versioned, signed release. Each
release also publishes a per-host **ChangePlan**: a list of operations,
each declaring

- a `capability` drawn from a closed list
- the exact `resources` it may touch (checked against the port and path
  registries)
- a `target` bound to the host’s public key
- rollback, expiry, and a one-time nonce

The on-device executor maps declared capabilities to an allowlist and
**refuses any effect outside that set.** Signing the bundle authenticates
the author. Only the plan constrains the effect.

Signing is a small subset of The Update Framework, sized for one operator:
an offline root, release signatures, a snapshot that binds the metadata
set together, and an emergency role. Each client that applies a signed
artifact keeps a high-water mark so replay, freeze, and downgrade are
rejected.

On top of the verifiable plan sits a *semantic* layer — generated, cached,
written for a language model to read: “this bumps a TLS library across a
CVE and restarts the public proxy.” That layer briefs a person and their
advisor agent. **It never authorizes.** Only the verifiable layer, checked
by the executor, authorizes. Where the prose can be filled in from the
plan’s typed fields, it is. Where it has to be written freely, it must
point at the exact fields it is summarizing, so a skeptical reader (or
their agent) can check the explanation against the plan.

That split is what the eventual **user-sovereignty** feature sits on. A
person — family, friend, or a stranger who cloned the repo — receives a
proposed change. Their own AI agent reads the semantic layer and explains
it in ordinary language. If they do not want it, they say so in ordinary
language; their agent keeps a personal branch that diverges from upstream,
and they never need to know the words “branch” or “merge.” When upstream
moves again, their agent re-evaluates against their stated preferences.
The proposing side and the consenting side are meant to run different
models; disagreement escalates to the human. None of this is built yet
(§14).

---

## 8. The writing rule

Most of this system’s configuration will be written by AI agents. An
agent sees the file in front of it, not the invariants living in twelve
other files it never opened. From that, two working rules:

> **Prefer designs that require only local knowledge over designs that
> require global knowledge.** If correctness follows from information
> present at the point of authorship, an agent can satisfy it. If
> correctness depends on already knowing what everyone else declared, an
> agent will violate it *confidently and plausibly* — which is worse than
> violating it obviously.

> **Prefer machine-checkable to conventional.** A convention an agent must
> remember is a convention it will eventually break silently. A schema, a
> type, or a compile-time check catches it and reports it in a form the
> next agent can act on. If a comment says “remember to…”, that text
> belongs in a schema instead.

For a human maintainer, “just write down the constraint you know about”
is cheap and explicit. For an agent with a bounded context, that is
exactly the expensive thing. The agent’s problem is not willingness to
write the constraint. It is knowledge that the constraint exists.

The same pattern shows up outside this project. Programming-language
research has long asked how local reasoning can guarantee a global
property. Recent writing on AI-generated code makes the same move: models
are reliably better at local (function-level) reasoning than at global
reasoning, so a language that lets a local author discharge a global
property helps generated code the same way it helps verified code.
Empirical work on language models using long contexts shows accuracy
drops when the relevant fact sits in the middle of the window. Benchmarks
of AI-generated infrastructure-as-code find that first-try correctness on
real cloud scenarios is low, and that a distinct, substantial error
category is *contextual reasoning failure* — missing or wrong
cross-resource references. Schema and syntax errors, the category
ordinary validation is best at, are the smallest slice.

Those findings are why the Site Model asks each record to state what it
provides and what it needs (§9), why conflict errors carry a resolution,
why “show me device X” is first in the compiler, and why generated
explanations must point at the plan they summarize.

The rule is a working hypothesis, not a law. §15 asks what would count
against it.

---

## 9. Ordering without a shared to-do list

Services have to start in a workable order. There are three levels of
ambition:

- **Retry until stable.** Keep applying until the number of unfinished
  jobs stops shrinking. CFEngine already does this. No author has to know
  anything about ordering.
- **Plus explicit `depends_on`**, written by someone who already knows
  that someone else’s resource exists and must run first.
- **Plus inference.** Each type states only what it *provides* and what it
  *requires*. The compiler derives ordering edges from those matches.

This design uses all three. Retry-until-stable is the substrate. Explicit
`depends_on` remains available and wins where it exists. The primary
authoring mechanism is `provides` / `requires`, because each is answerable
from inside one file by an author that has never seen the rest of the
system.

`depends_on` is a global-knowledge mechanism. `provides` / `requires` is a
local-knowledge mechanism. That is the whole argument for inference, and
it is an argument about *who writes the configuration*, not about the
semantics of convergence.

Three compiler rules follow:

- **Types first, inference second.** Inference does not start until real
  type definitions exist on two platforms. Rules invented ahead of the
  types they range over encode guesses.
- **Every edge carries its origin.** Authored (with source location) or
  inferred (with the rule that produced it). A bad inferred edge presents
  as “why is this waiting?” — nothing failed — which is harder to diagnose
  than a missing edge’s “why did this fail?” Origin information turns that
  from a search into a lookup.
- **Authored edges win.** If an authored edge and an inferred edge cover
  the same pair, the authored one is kept and the coincidence is
  *reported*, not silently collapsed.

Bcfg2 deliberately built no dependency graph. Its client repeats while
pending work decreases; there is no graph to resolve and no ordering to
get wrong. That is simpler, and it has two decades of production behind
it. The extra machinery here is justified only if the writing rule in §8
is right. Three ways it may not be:

1. Retry-until-stable may already *be* the local-knowledge answer — more
   local than `provides` / `requires`, not less.
2. `provides` / `requires` may only relocate the global knowledge. Naming
   a token that another type must name identically is a shared vocabulary.
   A closed list of token *kinds* (`service:`, `port:`, `path:`, …) makes
   a typo a schema error rather than a silently unmatched edge. It does
   not tell an author which token names the resource they actually need.
3. Spurious edges may be worse than priced in. Origin information is
   supposed to make them a query. That claim is untested.

This design does **not** compile everything into one fully ordered
Puppet-style catalog. The service-owning roles examined so far declare no
role-to-role dependencies and run as independent plays. The real
constraints sort into a short hand-authored bootstrap sequence, short
independent per-app chains, and safety interlocks (§11) that are not
dependencies at all. Catalog compilation earns its keep when chains
interleave into a genuine web of prerequisites. These, so far, do not.

That reading is of automation that already runs on provisioned devices. It
is not a reading of a cold device. Convergent automation leaves no trace
of a constraint that fails on run 1 and succeeds on run 2, and **no device
in this fleet has been provisioned from factory reset by this
automation.** The cold path is untested.

---

## 10. Extra entries: noticing what shouldn’t be there

Bcfg2’s configuration goals are comprehensive: the specification describes
every configuration entity on the client, so anything present on the
client and absent from the specification is unintended, and is reported as
an **extra entry**. The client verifies in both directions — no less than
specified, and no more.

This design adopts that **per domain**, not per client on day one.
Domains are slices such as “the app list on this device,” `/etc/ssh`, or
“launchd services under this prefix.” Fleet-wide comprehensiveness on a
machine that was never built under it is not survivable.

A domain is comprehensive unless it opts out, and opting out requires a
reason from a closed set of two:

- **`not-yet-migrated`** — real device state nobody has described yet.
  Normal on day one. A backlog item, and countable. That count *is* the
  remaining work.
- **`deliberately-unmanaged`** — state that is genuinely not ours to
  describe: user data, another tool’s territory, device-generated caches.
  Permanent, and should be rare.

A bare on/off flag would let an agent widen the unmanaged surface
silently. The reason string makes every gap a visible, searchable
decision.

Keeping the two reasons distinct is what makes default-on livable. Without
the split, either the operator is buried in day-one noise, or everyone
opts out broadly and never comes back. With it, the managed / unmanaged
ratio per device is a real progress metric. Bcfg2’s booklet records a
first client run of `Total managed entries: 0 / Unmanaged entries: 2308`.
The deployment story there is grinding the second number down. The first
transcription pass here is expected to look the same.

The schema records the two counters separately, per domain, next to the
release stamp. Conflating backlog with permanent exclusion is what makes
the number stop meaning anything.

This is also the only mechanism in the design that notices two writers
changing the same device without coordinating. CFEngine’s default posture
— promising only about what is mentioned — cannot detect that, by
construction. An AI agent’s accidental omission and a second writer’s
uncoordinated drift produce the same observable: something present on the
device that nothing describes.

---

## 11. Interlocks: “don’t do this until…”

Some constraints are not ordering. They are *preconditions*.

Setting always-on VPN lockdown on a device whose VPN is unauthenticated
severs every management path to that device. Nothing in the existing
codebase authenticates the VPN first; only a safe default and a comment
prevent it today.

Bcfg2 Actions are the shipped precedent: unless exit status is ignored, a
failing pre-action prevents modification of entries in the enclosing
bundle. That is a guard with a defined blast radius — not an edge in a
graph, and not a bare `if`.

This design makes that a first-class Site Model field. It compiles to a
CFEngine guard class plus a bundle-scoped refusal. The bundle is both the
grouping unit and the re-verification scope, also following Bcfg2.

Blast radius and reporting are required constants in the schema, not
author-settable fields. An author who could narrow either one could
reintroduce the bug the mechanism exists to close.

---

## 12. Two walkthroughs

The inputs below are excerpts from `nix2cf`’s
[`examples/services.yml`](https://github.com/djbclark/nix2cf/blob/master/examples/services.yml)
— a real fixture, schema-validated, not live site data. The outputs
(CFEngine JSON, the launchd plist, the promise sketch) are hand-authored
to show the target shape. The compiler’s render stage does not exist yet,
so nothing below except the YAML was produced mechanically.

### A. An ordering edge nobody wrote

`caddy` and `litellm-proxy` sit in the same `edge-http` bundle.
`litellm-proxy` states only what it needs. Nothing in either record says
“start after caddy.”

```yaml
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

`litellm-proxy`’s `requires: [service:caddy, …]` matches `caddy`’s
`provides: [service:caddy, …]`. The compiler derives an ordering edge from
that match alone:

```jsonc
// host_specific.json — ILLUSTRATIVE, not compiler output
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

`origin` says this edge was never authored. `rule` names the mechanism.
`source` points at the exact `requires` entry. If the edge is wrong, the
question is “does this rule apply to this pair?” — a lookup — not “where
did this ordering come from?” — a search.

The generic bundle behind `nix2cf_services` is what materializes the
on-device artifact. For `caddy`, that is a launchd plist CFEngine keeps
present and loaded:

```xml
<!-- /Library/LaunchDaemons/com.djbclark.caddy.plist — rendered, not authored -->
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
```

### B. An interlock, from schema to guard

The `fleet-vpn` bundle carries the precondition in §11: lockdown may not
be enforced before Tailscale authenticates.

```yaml
bundles:
  fleet-vpn:
    description: "VPN transport and the lockdown policy that depends on it"
    domain: macos-launchd-services
    interlocks:
      - id: tailscale-authenticated-before-lockdown
        description: >-
          Tailscale must be authenticated before always-on VPN lockdown may be
          enforced. Setting lockdown on a device whose Tailscale is
          unauthenticated severs every management path to it.
        pre_action:
          command: ["tailscale", "status", "--json"]
          expect_exit: 0
          timeout_seconds: 15
        defines_class: tailscale_authenticated
        blocks: enclosing-bundle
        report: true
```

`blocks` and `report` are constants in the schema. An author cannot narrow
the blast radius or silence the report, so there is no branch in the
render stage where it could either.

```cfengine
# ILLUSTRATIVE — not compiler output
bundle agent fleet_vpn
{
  classes:
      "tailscale_authenticated"
        expression => returnszero("/usr/local/bin/tailscale status --json", useshell);

  methods:
      "guard"
        usebundle => report_if_missing_class("tailscale_authenticated",
                       "fleet-vpn: blocked, Tailscale not authenticated");

  services:
      "tailscaled"
        service_policy => "start",
        ifvarclass => "tailscale_authenticated";
}
```

The guard is attached once, at the bundle, and inherited by every promise
in it — because the schema gave the render stage no field to read a
narrower scope from.

---

## 13. Where a different design is a better fit

Every choice above is scoped to a specific envelope: a fleet small enough
that no single role is dedicated to operating it, mixed enough that no
OS-native tool covers it alone, and connected intermittently enough that
waiting on a reachable central server is not an option. Three ceilings
follow. Each names the point at which a *different* architecture — not a
variant of this one — is the better choice.

- **Local-first reporting stops paying for itself once a fleet-wide query
  becomes routine rather than exceptional.** A SQLite record per device is
  free for as long as “did host X converge” is the dominant question. Once
  “did the rollout land everywhere” needs an answer with bounded staleness
  often enough to matter, the honest fix is a central statistics spine
  (the shape Bcfg2 already builds), not a federation layer retrofitted
  onto a local-first design.
- **Derived dependency edges stop being the cheaper mechanism once role
  interleaving is the common case rather than the exception.** Inference
  earns its keep where explicit edges would otherwise be rare, which is
  where roles are largely independent. A site where most roles genuinely
  depend on several others has an ordering problem that has become
  Puppet’s catalog-compilation problem, and a design built to resolve one
  true graph deterministically is then the better fit.
- **The signed-release-as-artifact model stops being adequate once changes
  must land on a bounded clock across the whole fleet** — an
  active-incident patch under a compliance deadline, for instance.
  Ahead-of-time rendering optimizes for devices that are routinely
  unreachable at authoring time. A fleet whose devices are reliably
  reachable and whose changes carry real time pressure is better served by
  render-on-request (Bcfg2’s model) or a push-capable policy server.

---

## 14. What is built, and what is next

**Built today**

- Site Model schemas, including `provides` / `requires` per type,
  `interlocks` per bundle, and `comprehensive` plus `opt_out_reason` per
  domain.
- The report-row schema (release stamp, separate managed /
  not-yet-migrated / deliberately-unmanaged counters).
- A lint that carries the cross-file rules JSON Schema cannot state
  alone: reference resolution, launchd labels checked against declared
  writer prefixes, no prefix nested inside another.
- Twelve deliberately broken fixtures used as a check that the lint
  catches bad input, not only that it accepts good input.

**Not built — this is most of it**

The compiler, all three platform adapters, the signed release path, the
ChangePlan executor, the consent surface. No operational numbers of any
kind: no deployment time, no managed/unmanaged ratio, no failure data.

**Build order from here** (each step is meant to leave the system in a
coherent, describable state):

| Step | What | Notes |
| --- | --- | --- |
| 0 | Site Model + fences | Schemas exist. Remaining work: transcribe reality (expect almost every domain to start as `not-yet-migrated`), pairing-check, existence-checks, a YAML round-trip check, a registry-lookup command. |
| 1 | macOS services adapter | Render the Mac’s launchd services as CFEngine promises from `services.yml`. Dry-run is the default. Not in this step: nix-darwin / home-manager. |
| 2 | Android under the Site Model | Same vocabulary as the Mac, on the existing Termux / agent / CFEngine stack. |
| 3 | `nix2cf` compiler | “What would device X receive?” first, then conflict check, extra-entry reporting, then inference. Inference waits until types exist on two platforms (steps 1 and 2). |
| 4 | Linux reference path | A stock distro, not NixOS. This is where “someone else can run this” is proven. Distro choice is open until this step; Ubuntu Server is the working default. |
| 5 | First real Linux host | A second node that can hold backup roles. Proves that roles are data. |
| 6 | Signed releases, push-only | TUF-subset root; ChangePlan generation; capability-enforcing executor. Operator hosts only. |
| 7 | Mac substrate (optional) | nix-darwin + home-manager if that path is chosen. Reversible. Services remain CFEngine from step 1. |
| 8 | Pull | Any host with the role self-updates. The no-control-node end state, reached by editing `roles.yml`. |
| 9 | Consent / sovereignty | The surface a person uses to understand, refuse, or keep a personal branch. |
| 10+ | Demand-driven | Builder/cache, reproducible APK provenance, web of trust, extracting the publishable layer when a second person runs it. |

On the first platform brought under management — the primary workstation,
which cannot easily be reimaged — dry-run is the standing posture.
Reporting (“what changed, what is dirty, what release am I on”) is an
adoption requirement, not an observability extra.

One Bcfg2 idea that does not transfer as a default: expressing
cross-machine sequencing as a state machine over *releases*. Time in any
state is unbounded, and one down client can stall a workflow. For a fleet
whose devices are routinely unreachable, that last property is
disqualifying as a default. It remains the shape to reach for if a real
cross-device sequencing need appears.

A smaller idea that does transfer later: Bcfg2’s `altsrc` — bind an entry
as if it had a different name, so two paths share one source. Termux’s
`$PREFIX`-relative layout against Linux and macOS absolutes is the same
problem `/etc/hosts` versus `/etc/inet/hosts` was.

---

## 15. Open questions

These are the places the current design is weakest.

1. **Is inference justified?** Retry-until-stable already requires no
   author to know anything about ordering. If that is already the
   local-knowledge mechanism, `provides` / `requires` is extra machinery
   for a problem that was already solved.
2. **Is the writing rule an argument or a hypothesis?** A counter-example
   would be a place where forcing an author to state a global constraint
   is what *caught* a bug.
3. **Do `not-yet-migrated` counts actually get ground down, or
   accumulate?** Bcfg2’s deployment had a person whose job that was. A
   fleet in this envelope has no such role. If the count only ever rises,
   default-on comprehensiveness is a permanent tax with no payoff.
4. **Is per-domain the right granularity?** A domain is a boundary someone
   has to draw. A badly drawn one hides drift inside itself as effectively
   as opting out would.
5. **Is local-first the wrong call?** Bcfg2’s operators found that
   network-wide reports were what actually bought administrator trust.
   “No consumer yet for a central copy” is exactly the reasoning that
   finding warns against.
6. **When a genuinely global question arrives, is a best-effort dashboard
   enough?** “Did the security rollout land everywhere?” is a yes/no
   question. An eventually-consistent view is incomplete for the devices
   most likely to matter, because they are the unreachable ones.
7. **Does edge origin information actually work?** Nobody has run it. If
   it does not, inference has a silent failure mode.
8. **Does the ChangePlan’s capability list survive contact with real
   operations?** A closed list the executor enforces is only as good as
   its coverage. The pressure will be to add an escape hatch; the moment
   one exists, the mechanism is decorative.
9. **How does an author find the right `provides` / `requires` token
   without the global context they are not supposed to need?** A closed
   list of kinds catches typos. It does not name the resource.
10. **Is the whole premise the wrong shape?** The design hardens the
    surface where a machine author lacks global context. If the real
    weakness is plausible-looking output that type systems do not catch,
    the schemas are defending the wrong wall.

---

## Acknowledgements

Thanks to Narayan Desai and his co-authors on the four Bcfg2 papers this
work draws from — Andrew Lusk, Rick Bradshaw, Rémy Evard, Scott Matott,
Sandra Bittner, Susan Coghlan, Cory Lueninghoener, Ti Leggett, John-Paul
Navarro, Gene Rackow, Craig Stacey, Tisha Stacey, and Joey Hagedorn.
§10–§11 and several of the practices in §6 and §14 come from that work.

## Further reading

The technical paper has a full reference list. The load-bearing sources
for this guide:

1. N. Desai, A. Lusk, R. Bradshaw, and R. Evard. *BCFG: A Configuration
   Management Tool for Heterogeneous Environments.* CLUSTER ’03.
2. N. Desai, R. Bradshaw, et al. *A Case Study in Configuration Management
   Tool Deployment.* LISA ’05. (Reporting early; dry-run as the default
   posture; what actually bought administrator trust.)
3. N. Desai, R. Bradshaw, J. Hagedorn, and C. Lueninghoener. *Directing
   Change Using Bcfg2.* LISA ’06. (Revision stamping.)
4. N. Desai and C. Lueninghoener. *Configuration Management with Bcfg2.*
   USENIX Short Topics #19, 2008. (Extra entries; Actions as bundle-scoped
   guards; `buildfile`.)
5. M. Burgess and J. A. Bergstra. *Promise Theory: Principles and
   Applications.* 2014.
6. L. Tratt. *Local Reasoning for Global Properties.* 2026.
   https://tratt.net/laurie/blog/2026/local_reasoning_for_global_properties.html
7. N. F. Liu et al. *Lost in the Middle: How Language Models Use Long
   Contexts.* TACL 2023.
8. P. T. J. Kon et al. *IaC-Eval.* NeurIPS 2024. (First-try correctness of
   LLM-generated Terraform on real AWS scenarios.)
9. R. Nekrasov et al. *IaC Generation with LLMs: An Error Taxonomy.*
   arXiv:2512.14792, 2025.
10. J. Samuel, N. Mathewson, J. Cappos, and R. Dingledine. *Survivable Key
    Compromise in Software Update Systems.* CCS 2010. (The Update
    Framework.)
11. Flux / GitOps Toolkit. https://github.com/fluxcd/flux2
12. CFEngine documentation, client-server communication and
    self-bootstrap. https://docs.cfengine.com
