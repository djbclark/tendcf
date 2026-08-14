# How tendcf works

**A companion to the technical paper.** Same architecture, plainer language.
This version describes the system as it is designed today, and what is
planned next. It does not recount how the design was reached.

Draft for review — not published, not submitted.
Daniel Joseph Barnhart Clark (djbclark@mit.edu).
Prepared 2026-08-14; updated 2026-08-14 to match architecture v3.

The living architecture (decisions, build order, protection rules) is
[`architecture-DEFINITIVE-v3.md`](../architecture/architecture-DEFINITIVE-v3.md).
The technical paper, with citations and open questions in research form, is
[`tendcf-architecture-paper.md`](tendcf-architecture-paper.md).

**Nothing described here is deployed.** Some data formats exist and are
checked. The compiler, the on-device executor, and the screens a person
would use to accept or refuse a change are still to be built. No device has
been set up from factory reset by this automation.

A previous configuration stack on this fleet is **legacy reference only**.
It is not a dependency, not an upstream, and not copied into this project.
Patterns taken from it are described in generic terms.

---

## 1. What this is

`tendcf` is a design for keeping a mixed set of computers in an agreed
state: Apple Silicon Macs, Linux machines (Intel and ARM), and Android
devices reached through [Termux](https://termux.dev/). The computers are
often offline. More than one trusted person can act. There is no dedicated
operations staff, and no always-on central server that every device must
reach.

Most of the configuration will be written by AI coding agents, not typed by
a person. People still decide what should happen. A person whose computer is
managed should be able to read a proposed change in ordinary language and
refuse it — using **their** AI, not ours.

Two other goals sit alongside that:

- The generic machinery is publishable. Someone else should be able to
  supply their own facts and run the same code.
- The installed OS on a new Linux box is an ordinary distribution, not
  [NixOS](https://nixos.org/). Nix is used for builds and (later) as an
  optional way to *write* site data. It is not the thing a stranger has to
  install as their operating system.

---

## 2. The picture

```
  tendcf                 engine: schemas/types, generic adapters,
  (public)               default advisor prompt, compiler interface

  site-shared            reusable recipes (a Caddy role, an apt pattern).
  (optional, public)     Not live inventory.

  foreign site-shared    other people's recipes, listed as inputs.
  (read-only)

  site-private           this site's facts: inventory, allocations,
  (never an input)       secret names, trust policy, extra advisor prompt.
                         Holds the lockfile that pins everything else.

  tool forks (optional)  nix2cf, sudo-secretspec, Shizuku, … only if
                         patching them.

          │  Site Model instances (private) + recipes (shared)
          ▼
  nix2cf                 compiler: merge → conflict check → infer
  (tool)                 ordering → CFEngine Augments JSON.
                         Not the home of schemas or facts.

          ▼
  Signed release         manifest + per-host typed ChangePlan
                         (TUF-subset; executor refuses anything
                         outside the plan)

          ▼
  CFEngine +             each device is its own policy hub.
  tendcf-agent           Supervisors are adapters: systemd, launchd,
                         runit, Jobber, … from one service record.

          ▼
  JSONL log (capture)    append-only; the durable record
  SQLite (index)         tendcf-agent; rebuildable from JSONL
```

Git-repo count is not the composition mechanism. Layers are roles.
Site-private holds a lockfile (flake-style inputs) that pins tendcf,
nix2cf, site-shared, foreign shared sites, and optional tool forks. The
signed release is the deploy artifact. There is no lockstep of sibling
checkouts that must share one tag.

Collision of the same identity from two peer inputs is a **compile error**.
Only site-private may bind a winner (`caddy: from: alice`) or a short name.
Never silent last-wins.

Four ideas in this picture come from [Bcfg2](https://www.usenix.org/legacy/publications/library/proceedings/lisa05/tech/full_papers/desai/desai.pdf),
a configuration system built at Argonne and described in a series of papers
by Narayan Desai and colleagues. They are credited in the sections that use
them. [CFEngine](https://docs.cfengine.com) is the on-device engine; `tendcf`
does not replace it.

---

## 3. Facts live in layers

Every fact about *this* site lives in checked YAML/JSON files called the
**Site Model**. Behavior lives in generic code in tendcf that holds none of
those facts. Adapters translate. CFEngine, the toolchain bootstrapper, and
Nix-for-builds are *consumers*. Any one of them can be replaced without
moving the facts.

**Schemas and types live in tendcf**, not in the compiler. A schema change
is an interface change. A hostname change is site data. They do not move
together. (JSON Schema files still sit in [`nix2cf`](https://github.com/djbclark/nix2cf)
until that move finishes; they belong here.)

**Inventory is private by default.** Site-shared may ship device *kinds*,
example inventories, and **explicit exports** (public endpoints, role
advertisements) for fields the private site marked exportable. USB serials,
RFC1918 addresses, and the full host list stay private. Two foreign sites
both shipping a host named `mac` is a compile error unless private binds.

A host identity in trust and ChangePlans is the **device public key**, not
the hostname.

Foreign inputs are namespaced (`alice.caddy`) so auto-provided service
tokens do not collide. Private may alias a short name.

Three record types do most of the work.

**Services.** One record per service: name, run-as user, command,
environment as *names* of secrets (never the secret values), which role it
binds to, who owns it, which supervisor that host uses. Every systemd unit,
launchd plist, runit service, or Jobber job in the fleet is meant to be a
rendering of one such record.

**Roles.** A feature role maps to `{main, backups[], peers[]}`. “The control
node” is not a machine. It is a row in this file. Any eligible host can
hold any role.

**Unit writers.** Exactly one writer per unit-name prefix, for every
supervisor (launchd label, systemd instance, runit service, Jobber job).
Two tools writing the same unit is a class of outage this file is meant to
make impossible. launchd is one adapter, not the model.

The Site Model may later be *authored* in the Nix module system
(`mkOption`, `mkIf`, `mkDefault`) and rendered to the same JSON everything
else consumes. That is an authoring frontend only. Nobody adopting the
project has to know Nix. Until that frontend exists, the files are written
as YAML.

Every schema is paired with a concrete example file. The lint fails if a
schema arrives without its example, or the other way around. A lookup
command is planned so an agent can ask “who provides port 443?” without
reading the whole registry.

---

## 4. A compiler turns facts into CFEngine data

The compiler (working name `nix2cf`) reads the Site Model and writes
[CFEngine Augments](https://docs.cfengine.com/docs/3.21/reference-language-concepts-augments.html)
— JSON files (`def.json`, `host_specific.json`) that CFEngine has accepted
as a native data-injection layer since version 3.7. The name is historical;
YAML is a valid input. The compiler is a tool, not the home of schemas.

CFEngine’s [Masterfiles Policy Framework](https://github.com/cfengine/masterfiles)
is already largely data-driven on top of that layer. For the common case
the compiler therefore emits *data*, not CFEngine source text. A generic
bundle written once handles “this package is present and pinned, these
directories exist, this service is loaded” for any entry in the data.

The pipeline has four stages:

1. **Merge** site, role, and host layers into one picture per device.
2. **Conflict check** over that already-merged picture. Two writers claiming
   the same port or path is a build failure, not last-wins. The error names
   the resource, every writer that declared it and where, the conflicting
   values, and what a resolution would look like.
3. **Dependency inference** — see §9.
4. **Render** the Augments JSON.

Merge happens once, in the compiler, before render. CFEngine’s own
`mergedata()` is not used for this.

Because the render is a pure function of the Site Model — same input, same
output — “show me exactly what device X would receive, without touching
device X” is almost free. That command is planned as the first piece of
the compiler. It is how an agent checks its own work, how the compiler
regression-tests itself, and how a human sees a proposed change before it
lands. The shape is [Bcfg2 `buildfile`](https://docs.bcfg2.org/).

Compiling a typed description into an existing engine’s native format is a
known pattern. [NixOS](https://nixos.org/) does it into systemd units;
[nix-darwin](https://github.com/nix-darwin/nix-darwin) does it into
launchd agents; [cdk8s](https://cdk8s.io/) does it into Kubernetes YAML.
The pairing here is Site Model into CFEngine Augments, because of
[Promise Theory](https://markburgess.org/promises.html) and disconnected
multi-owner operation — not because the compiler mechanism is new.

**Where it runs:** operator machine or CI. Consented devices receive a
signed artifact. They do not run Nix or nix2cf.

---

## 5. Every device runs its own agent

Each computer runs CFEngine, including its own `cf-serverd`, and reads
policy that arrived as part of the ordinary signed-release path, synced
via git. There is no dedicated central policy host, no SSH requirement,
and no requirement to push.

Push still exists: a host that currently holds a deploy role can trigger
an immediate run on **operator** (and operator-chosen `managed`) hosts.
Push to a `consented` device still requires that device’s consent grant.
Push and pull are two modes of the same mechanism.

CFEngine’s usual textbook deployment is hub-and-spoke: one policy server,
clients pulling from it. The shape here is different and still supported:
a host may bootstrap as its own policy hub when its declared server
address is itself. Applied fleet-wide, off a shared git-synced source,
that is closer to [GitOps / Flux](https://fluxcd.io/) (an in-place agent
pulling desired state from git, no reachable control plane holding
credentials) than to CFEngine’s brochure diagram.

The “no control node” property is CFEngine’s own (Promise Theory: each
machine is an independent agent that keeps its own promises). What this
design adds is the fleet-wide self-hub plus git-synced source, the Site
Model that says who currently holds which role, and the consent gate.

**Supervisors are adapters.** A service record is one fact. The host’s
`supervisor` field (or a platform default) selects the renderer:
[systemd](https://systemd.io/), launchd (macOS example),
[runit](http://smarden.org/runit/) via [termux-services](https://github.com/termux/termux-services),
[Jobber](https://dshearer.github.io/jobber/), OpenRC / s6 / dinit when a
real host needs one. Packages on Linux come from CFEngine’s package
modules. File and service idioms are taken from
[ncf / Rudder generic methods](https://github.com/Normation/ncf) as a
vendored, stripped reference — not as a runtime.

---

## 6. Each device keeps its own record

Capture and index are different files.

1. **Capture:** append-only JSONL. One `write()`. If logging fails, a line
   is lost, not the history. [CFEngine Enterprise](https://docs.cfengine.com)
   already does this locally (`promise_log.jsonl`) before a hub copies it
   into SQL. Community needs the same glue.
2. **Index:** SQLite inside **tendcf-agent**, for queries, extra-entry
   counts, “what release am I on.” Rebuildable from JSONL. If the database
   is corrupt, history still exists.

CFEngine never opens SQLite. The agent tails (or receives) the log.

Two operational reasons the *device* is the record of truth:

- On CFEngine Community the local capture has to be built anyway, so
  local-as-record is the default and central-as-record is a second system.
- Devices in this fleet do go unreachable. A central copy fed by
  best-effort sync is incomplete during exactly the windows one would want
  it.

**Android:** Termux (`com.termux`) and tendcf-agent are different UIDs. The
APK cannot read `$PREFIX/...` as files.
[RUN_COMMAND](https://github.com/termux/termux-app/wiki/RUN_COMMAND-Intent)
is a user-granted bridge, not a shared log directory. tendcf-agent owns
**both** JSONL and SQLite in **app-private storage**. Either cf-agent runs
as a native helper of the agent (same UID), or a Termux-side reporter
*pushes* lines to the agent. Never “the agent opens Termux’s files.”

The outcome words are borrowed from Rudder’s `ncf` library, used here as a
reference vocabulary rather than as a runtime dependency:
`success` / `repaired` / `error` / `n-a` in enforce mode,
`compliant` / `noncompliant` / `error` / `n-a` in audit mode.

A path to a fleet-wide view already exists and costs nothing new to stand
up: a subset of each device’s index can push, best-effort, into an
observability stack (Vector / OpenObserve / Grafana). That view is never
the record of truth. When a question such as “did the security rollout land
everywhere?” needs a real yes or no, reachable devices are queried
directly and the rest are treated as unknown, not as a stale aggregate.

Every report row carries the release that produced it. Each device records
which release it is converged to.

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

Signing is a small subset of [The Update Framework](https://theupdateframework.io/),
sized for one operator: an offline root, release signatures, a snapshot
that binds the metadata set together, and an emergency role. Each client
that applies a signed artifact keeps a high-water mark so replay, freeze,
and downgrade are rejected.

**First-run root.** The [TUF spec](https://theupdateframework.github.io/specification/latest/)
assumes a good trusted `root.json` shipped with the updater, out of band.
TOFU (trust on first use) is not used for consented devices. Install shows
the root key IDs / fingerprint; the person compares that to a channel they
already trust (operator, printed card, published fingerprint). Later root
rotation is in-band (threshold of old **and** new keys). Threshold
compromise of root is again out of band.

**Emergency vs consent.** Revocation, “do not apply releases signed by K,”
freeze detection, and high-water rejection **tighten** what may run. They
do not need a local yes. Installing new targets still does, on
`consented` devices. An optional enrolled policy “I pre-grant emergency
security patches from role E” may exist; **default off**.

On top of the verifiable plan sits a *semantic* layer — generated, cached,
written for a language model to read: “this bumps a TLS library across a
CVE and restarts the public proxy.” That layer briefs a person and their
advisor. **It never authorizes.** Where the prose can be filled in from the
plan’s typed fields, it is. Where it has to be written freely, it must
point at the exact fields it is summarizing.

---

## 8. The person’s own AI

We never run their model, see their prompt, or see the conversation. We
offer a change and accept a signed yes/no. Same shape as a
[Kubernetes admission webhook](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/).

- At install they enroll an **advisor key** (or a local app/socket) in
  site-private.
- tendcf ships a **suggested default prompt** as a replaceable public file.
  They may append or replace it.
- Modes: auto-review, or a conversation with them first.
- Return path: `accept | reject`, signed by the enrolled key, bound to
  that plan’s nonce. Timeout is deny. Advisor down → fail closed for
  *installs* (revocation still applies, §7).
- Custom tools (OpenPGP web of trust, a transparency log, a chain, gossip
  of signed apply-attestations) are theirs. Consensus among “everyone
  waiting for everyone else” is a separate project that consumes
  attestations. tendcf owes: the ChangePlan, optional exportable
  apply-attestations, the `accept | reject` slot.

The proposing side and the consenting side are different programs. The
advisor never authorizes; the executor does, against the signed grant.

Personal branch: theirs, applied under their consent; never auto-merges
into anyone else’s trust domain. Upstream-heal is a suggestion their agent
evaluates.

None of this surface is built yet (§18).

---

## 9. The writing rule

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
provides and what it needs (§10), why conflict errors carry a resolution,
why “show me device X” is first in the compiler, and why generated
explanations must point at the plan they summarize.

The rule is a working hypothesis, not a law. §19 asks what would count
against it.

---

## 10. Ordering without a shared to-do list

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

A service named `caddy` **auto-provides** `service:caddy` unless it opts
out. Explicit `depends_on` still wins. See §15 for how an author finds
the name.

Three compiler rules follow:

- **Types first, inference second.** Inference does not start until real
  type definitions exist on two platforms.
- **Every edge carries its origin.** Authored (with source location) or
  inferred (with the rule that produced it). A bad inferred edge presents
  as “why is this waiting?” Origin information turns that from a search
  into a lookup.
- **Authored edges win.** If an authored edge and an inferred edge cover
  the same pair, the authored one is kept and the coincidence is
  *reported*, not silently collapsed.

Bcfg2 deliberately built no dependency graph. Its client repeats while
pending work decreases. That is simpler, and it has two decades of
production behind it. The extra machinery here is justified only if the
writing rule in §9 is right. Three ways it may not be:

1. Retry-until-stable may already *be* the local-knowledge answer — more
   local than `provides` / `requires`, not less.
2. `provides` / `requires` may only relocate the global knowledge. Naming
   a token that another type must name identically is a shared vocabulary.
   Auto-provide plus a lookup CLI (§15) is the mitigation. It is untested
   in use.
3. Spurious edges may be worse than priced in. Origin information is
   supposed to make them a query. That claim is untested.

This design does **not** compile everything into one fully ordered
Puppet-style catalog. The service-owning roles examined so far declare no
role-to-role dependencies and run as independent plays. Catalog
compilation earns its keep when chains interleave into a genuine web of
prerequisites. These, so far, do not.

That reading is of automation that already runs on provisioned devices. It
is not a reading of a cold device. Convergent automation leaves no trace
of a constraint that fails on run 1 and succeeds on run 2, and **no device
in this fleet has been provisioned from factory reset by this
automation.** The cold path is untested.

---

## 11. Extra entries: noticing what shouldn’t be there

Bcfg2’s configuration goals are comprehensive: the specification describes
every configuration entity on the client, so anything present on the
client and absent from the specification is unintended, and is reported as
an **extra entry**. The client verifies in both directions — no less than
specified, and no more.

This design adopts that **per domain**, not per client on day one.
Domains are slices such as “the app list on this device,” `/etc/ssh`, or
“services under this unit prefix.” Fleet-wide comprehensiveness on a
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

Keeping the two reasons distinct is what makes default-on livable. Bcfg2’s
booklet records a first client run of `Total managed entries: 0 /
Unmanaged entries: 2308`. The deployment story there is grinding the
second number down. The first transcription pass here is expected to look
the same.

This is also the only mechanism in the design that notices two writers
changing the same device without coordinating. CFEngine’s default posture
— promising only about what is mentioned — cannot detect that, by
construction.

---

## 12. Interlocks: “don’t do this until…”

Some constraints are not ordering. They are *preconditions*.

Setting always-on VPN lockdown on a device whose VPN is unauthenticated
severs every management path to that device. That is not “start B after
A.” It is “do not do B unless this probe still succeeds.”

[Bcfg2 Actions](https://www.usenix.org/legacy/publications/library/proceedings/lisa06/tech/full_papers/desai/desai.pdf)
are the shipped precedent: unless exit status is ignored, a failing
pre-action prevents modification of entries in the enclosing bundle. That
is a guard with a defined blast radius — not an edge in a graph, and not
a bare `if`.

This design makes that a first-class Site Model field. It compiles to a
CFEngine guard class plus a bundle-scoped refusal. The bundle is both the
grouping unit and the re-verification scope, also following Bcfg2.

Blast radius and reporting are required constants in the schema, not
author-settable fields. An author who could narrow either one could
reintroduce the bug the mechanism exists to close.

---

## 13. Peer actions: help without a global lock

Some operations a host cannot perform locally. Example from our last
system: a device that cannot start its privileged helper itself; any
healthy peer in its allowlist may do it over ADB; if every helper is
down, **only that device waits**.

That is a **peer action**: the target declares an operation it cannot do
locally; any helper with the capability **and** on the **target’s** peer
allowlist may do it. Helpers are fungible. Prefer **groups** (“household
helpers”) plus allowed verbs, not only individual keys. Stall is local.
Idempotent. Not a
[distributed lock](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html),
and not Bcfg2’s LISA ’06 state machine over *releases* — those stall the
*fleet* when one box is unreachable.

Cross-machine “wait until the server is serving the new export” is a
**local probe** (or a wait for a signed apply-attestation from the host
that holds that role). Bcfg2’s FSM is a **view** reconstructed from JSONL
plus optional attestations, never a coordinator.

[Bcfg2 `altsrc`](http://docs.bcfg2.org/) still transfers: Termux
`$PREFIX` versus Linux/macOS absolute paths sharing one source.

---

## 14. Per-device trust

`trust_tier` (`operator` | `managed` | `consented`) is a **class**: which
consent gate applies. It is not who trusts whom. Full-mesh “every device
has operator root to every sibling” is **not** the product default. It is
a site-private policy some operator-tier labs may still choose.

Each device carries a **local trust policy** in its signed release
(authored in site-private). It does not phone home to ask.

| Axis | Question | Default |
| --- | --- | --- |
| **Release** | Whose signatures may change me? | Site TUF root enrolled at the first-run ceremony |
| **Consent** | Do I also need a local yes? | `operator`: no. `consented`: yes (advisor key). `managed`: operator-chosen |
| **Peer** | Who may act *on* me (ADB, SSH, peer-help)? | Nobody, unless listed. Prefer groups plus allowed verbs |
| **Attestation** | Whose “I applied this” counts for my advisor tools? | Only sets that person configured |
| **Secrets / cache** | Who may receive this secret or substitute this store path? | secretspec resolver; cache keys `operator` only |

Peer actions check the **target’s** peer allowlist, not only “the helper
has a capability.” Identity is the device public key.

A label in inventory does not enforce this. The executor does.

Web-of-trust thresholds (“50% of people I trust have installed this”)
live in the **advisor plug-in**, not in the executor.

---

## 15. Token discovery

Inference removes “you must already know the *edge*.” Naming the *thing*
is a catalog, not a graph.

1. Auto-provide `service:<name>` unless the service opts out.
2. Lookup CLI against registries and compiled provides (`who-provides`,
   `does-role exist`, `tokens kind=service`).
3. Unknown token, unmatched `requires`, or two providers of the same
   token → compile error listing near-misses and the catalog.

Token *kinds* are a closed enum in the schema (`service`, `port`, `path`,
`secret`, `class`, `network`, …). Token *values* are instance data,
checked at compile time — not a schema enum that changes with every new
service.

If an author has never heard of the thing they need, lookup and the error
are the discovery path. The writing rule is “don’t require the graph,”
not “don’t require names.”

---

## 16. Two walkthroughs

The inputs below are excerpts from `nix2cf`’s
[`examples/services.yml`](https://github.com/djbclark/nix2cf/blob/master/examples/services.yml)
— a fixture, schema-validated, not live site data. The outputs
(CFEngine JSON, the launchd plist, the promise sketch) are hand-authored
to show the target shape. The compiler’s render stage does not exist yet,
so nothing below except the YAML was produced mechanically. launchd here
is one adapter; the same service record would render a systemd unit or a
runit service on another host.

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
`provides: [service:caddy, …]` (and would also match auto-provide of
`service:caddy` from the name alone). The compiler derives an ordering
edge from that match:

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
on-device artifact. For `caddy` on macOS, that is a launchd plist
CFEngine keeps present and loaded:

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

The `fleet-vpn` bundle carries the precondition in §12: lockdown may not
be enforced before the VPN authenticates.

```yaml
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

`blocks` and `report` are constants in the schema. An author cannot narrow
the blast radius or silence the report.

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
                       "fleet-vpn: blocked, VPN not authenticated");

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

## 17. Where a different design is a better fit

Every choice above is scoped to a specific envelope: a fleet small enough
that no single role is dedicated to operating it, mixed enough that no
OS-native tool covers it alone, and connected intermittently enough that
waiting on a reachable central server is not an option. Three ceilings
follow. Each names the point at which a *different* architecture — not a
variant of this one — is the better choice.

- **Local-first reporting stops paying for itself once a fleet-wide query
  becomes routine rather than exceptional.** A JSONL record per device is
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

## 18. What is built, and what is next

**Built today**

- Site Model schemas (currently in nix2cf; specified to live in tendcf),
  including `provides` / `requires` per type, `interlocks` per bundle, and
  `comprehensive` plus `opt_out_reason` per domain.
- The report-row schema (release stamp, separate managed /
  not-yet-migrated / deliberately-unmanaged counters).
- A lint that carries the cross-file rules JSON Schema cannot state
  alone: reference resolution, launchd labels checked against declared
  writer prefixes, no prefix nested inside another.
- Twelve deliberately broken fixtures used as a check that the lint
  catches bad input, not only that it accepts good input.

**Not built — this is most of it**

The compiler, all three platform adapters, the signed release path, the
ChangePlan executor, the consent surface, peer-action runtime, generic
supervisor switch. No operational numbers of any kind.

**Build order from here** (each step is meant to leave the system in a
coherent, describable state):

| Step | What | Notes |
| --- | --- | --- |
| 0 | Schemas in tendcf | provides/requires, interlocks, peer_actions, comprehensive, trust-policy shape, report-row. Lint, examples, lookup stub, YAML canonicalize. Transcribe reality (`not-yet-migrated` is the correct day-one state). |
| 1 | macOS services adapter | Render services as CFEngine promises from `services.yml` via the launchd adapter. Dry-run default. Not in this step: nix-darwin. |
| 2 | Android under the Site Model | Same vocabulary. Agent owns JSONL+SQLite in app-private storage. |
| 3 | `nix2cf` compiler | “What would device X receive?” first, then conflict check, extra-entry reporting, then inference. Inference waits until types exist on two platforms. |
| 4 | Linux reference path | A stock distro, not NixOS. Distro choice is open until this step; Ubuntu Server is the working default. |
| 5 | First real Linux host | A second node that can hold backup roles. Proves that roles are data. |
| 6 | Signed releases, push-only | TUF-subset ceremony; ChangePlan generation; capability-enforcing executor. Operator hosts only. |
| 7 | Mac substrate (optional) | nix-darwin + home-manager if that path is chosen. Reversible. Services remain CFEngine from step 1. |
| 8 | Pull | Any host with the role self-updates. The no-control-node end state, reached by editing `roles.yml`. |
| 9 | Consent / sovereignty | Advisor slot + default prompt. Their AI, our accept/reject. |
| 10+ | Demand-driven | Builder/cache, reproducible APK provenance, WoT as advisor tools, extracting the publishable layer when a second person runs it. |

On the first platform brought under management — the primary workstation,
which cannot easily be reimaged — dry-run is the standing posture.
Reporting (“what changed, what is dirty, what release am I on”) is an
adoption requirement, not an observability extra.

---

## 19. Open questions

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
6. **When a genuinely global question arrives, is querying reachable
   devices and treating the rest as unknown enough?**
7. **Does edge origin information actually work?** Nobody has run it. If
   it does not, inference has a silent failure mode.
8. **Does the ChangePlan’s capability list survive contact with real
   operations?** A closed list the executor enforces is only as good as
   its coverage. The pressure will be to add an escape hatch; the moment
   one exists, the mechanism is decorative.
9. **Is the whole premise the wrong shape?** The design hardens the
   surface where a machine author lacks global context. If the real
   weakness is plausible-looking output that type systems do not catch,
   the schemas are defending the wrong wall.

Token discovery (how an author finds the right name) is a mechanism
(§15), not an open question. Whether authors actually use the lookup and
the error catalog is still untested.

---

## Acknowledgements

Thanks to Narayan Desai and his co-authors on the four Bcfg2 papers this
work draws from — Andrew Lusk, Rick Bradshaw, Rémy Evard, Scott Matott,
Sandra Bittner, Susan Coghlan, Cory Lueninghoener, Ti Leggett, John-Paul
Navarro, Gene Rackow, Craig Stacey, Tisha Stacey, and Joey Hagedorn.
§11–§12 and several of the practices in §6 and §18 come from that work.

## Further reading

The technical paper has a full reference list. Load-bearing sources, with
links where they help:

1. N. Desai, A. Lusk, R. Bradshaw, and R. Evard. *BCFG: A Configuration
   Management Tool for Heterogeneous Environments.* CLUSTER ’03.
2. N. Desai, R. Bradshaw, et al. *A Case Study in Configuration Management
   Tool Deployment.* [LISA ’05](https://www.usenix.org/legacy/publications/library/proceedings/lisa05/tech/full_papers/desai/desai.pdf).
3. N. Desai, R. Bradshaw, J. Hagedorn, and C. Lueninghoener. *Directing
   Change Using Bcfg2.* LISA ’06. (Revision stamping; FSM over releases —
   used here as a view, not a coordinator.)
4. N. Desai and C. Lueninghoener. *Configuration Management with Bcfg2.*
   USENIX Short Topics #19, 2008. (Extra entries; Actions as bundle-scoped
   guards; `buildfile`.)
5. M. Burgess and J. A. Bergstra. *[Promise Theory](https://markburgess.org/promises.html).* 2014.
6. L. Tratt. *[Local Reasoning for Global Properties](https://tratt.net/laurie/blog/2026/local_reasoning_for_global_properties.html).* 2026.
7. N. F. Liu et al. *Lost in the Middle: How Language Models Use Long
   Contexts.* TACL 2023.
8. P. T. J. Kon et al. *IaC-Eval.* NeurIPS 2024.
9. R. Nekrasov et al. *IaC Generation with LLMs: An Error Taxonomy.*
   arXiv:2512.14792, 2025.
10. J. Samuel, N. Mathewson, J. Cappos, and R. Dingledine. *Survivable Key
    Compromise in Software Update Systems.* CCS 2010. ([The Update
    Framework](https://theupdateframework.io/).)
11. [Flux / GitOps Toolkit](https://fluxcd.io/).
12. [CFEngine documentation](https://docs.cfengine.com), client-server
    communication and self-bootstrap.
13. [TUF specification](https://theupdateframework.github.io/specification/latest/),
    §5 (trusted root out of band).
14. [Termux RUN_COMMAND](https://github.com/termux/termux-app/wiki/RUN_COMMAND-Intent).
15. [Kubernetes admission webhooks](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)
    (shape of the advisor slot).
