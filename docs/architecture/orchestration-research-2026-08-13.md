# Orchestration research — non-VM site management, dependency ordering, and the hard constraints

Session of 2026-08-13 (continued). Completes the research leg opened in
handoff `601f` and left half-done: the Rudder RBAC question, the Bolt and
Choria licensing checks, and the open-ended "site orchestration that isn't
based on running whole virtual machines" half of the operator's ask. Adds
Bcfg2's ordering model (operator request, mid-session) and `mgmt`'s
automatic dependency inference, both of which bear directly on D16.

## 0. The two hard constraints

Operator, 2026-08-13. Every candidate below is scored against both:

1. **Must be self-hostable.** A dependency on someone else's web service
   is disqualifying.
2. **No arbitrary node-count limit.** IoT growth is expected, so a
   licence that caps devices is disqualifying regardless of price.

A third filter emerged from D17 and applies to anything considered as
*code* rather than as a *reference corpus*: GPLv3 in a dependency is a
problem for this project's distribution model. It is not a problem for
reading a project's design and reimplementing the idea.

## 1. Rudder — the open question, resolved

**The question:** does RBAC / multi-user management live in Rudder Core,
or is it an Enterprise plugin? Load-bearing for site-pika, which is
communally managed.

**The answer: local RBAC is in Core, and has been since Rudder 8.2.**
Only *directory-backed* authentication costs money.

| Capability | Where it lives |
| --- | --- |
| `rudder-users.xml` — the user/role config file | Core |
| Predefined roles (`administrator`, `user`, `configuration`, …) | Core |
| **Custom roles** — "union set of any permissions" | Core |
| User-management **UI** in the Administration menu | Core as of 8.2 (was a plugin) |
| External auth: LDAP / AD / OAuth2 / OIDC / SSO | **Licensed** (`authentication-backends`) |
| Per-user API tokens, fine-grained API ACLs | **Licensed** (`api-authorizations`) |
| Multi-tenancy | **Licensed** |

Evidence for the version move, which matters because the docs contradict
each other across versions and it is easy to reach the wrong conclusion:

- The 8.1 plugin page still says the `administrator` role is *"the only
  one enabled without the `user-management` plugin"* — i.e. in 8.x, RBAC
  genuinely was paywalled.
- `docs.rudder.io/reference/current/plugins/user-management.html` now
  **404s** — the plugin no longer exists.
- `reference/current/administration/users.html` documents predefined and
  custom roles as base-server functionality, naming plugins only for
  external auth and API tokens.

**Consequence for site-pika:** the operator's stated position was that
all-access-for-everyone is acceptable for now (root passwords currently
live on paper next to the machine). It turns out differentiated local
roles are available for free anyway, so the "future seam" is cheaper than
assumed — the seam that actually costs money is *centralised identity*
(LDAP/SSO), not *authorization*. Worth separating those two in any future
design: they were being treated as one item.

**Unchanged:** Rudder Core has no node limit, ships the complete web UI,
and Core is a strict subset of the paid product delivered as plugins on
the same packages (no reinstall to upgrade). Its one real Core constraint
remains the **3-month upgrade window** — a maintenance obligation, not a
cap. D17 stands: GPLv3 keeps Rudder a reference corpus, not a dependency.

## 2. Bolt — passes both constraints

- **Licence:** Apache 2.0, `puppetlabs/bolt`.
- **Node limit:** none. Bolt is a workstation CLI that connects out over
  SSH/WinRM with no agent required, so there is nothing to count.
- **Self-hostable:** trivially — it runs on the operator's laptop.
- **Alive:** yes. 5.x line, releases through mid-2026, Ruby 3/4 support.

**The Perforce caveat, and why it does *not* bite here.** Puppet's 2025
change moved *new binaries and packages* to a private hardened repo under
a EULA permitting **development use up to 25 nodes**; above that needs a
commercial licence. Source stays Apache 2.0. That is what fails constraint
(2) for Puppet-the-agent, and it is why `OpenVoxProject` exists — including
`openbolt`, a community rebuild of Bolt. Bolt itself is not agent
software and is not licensed per node, but if the packaging channel ever
matters, `openbolt` is the fallback that keeps constraint (1) intact.

## 3. Choria — passes both constraints

- **Licence:** Apache 2.0.
- **Self-hosted:** entirely. Choria Server (on nodes), its own
  NATS-compatible Network Broker, CLI, Streams, Scout, Autonomous Agents.
  Nothing phones home.
- **Node limit:** none, and the scale headroom is absurd for this fleet —
  documented at 50,000 nodes on a single compute node, tested past
  100,000, and explicitly supported down to "just a Raspberry Pi."
- **Puppet dependency:** **none required.** Choria descends from
  MCollective and integrates with Puppet, but runs standalone; the docs
  explicitly address non-Puppet users in an IoT framing.

Choria is the strongest of the three on paper for a growing IoT fleet:
it is the only candidate designed as a *message bus with autonomous
agents* rather than a runner, which is a different shape from both
CFEngine's convergence loop and Bolt's imperative push.

## 4. Bcfg2's ordering model (operator request)

Bcfg2 is worth reading precisely because it answers the D16 question
**by refusing to answer it**. It has no dependency graph and no ordering
declaration. Three mechanisms substitute for one:

**a) A fixpoint loop, not a topological sort.** The client verifies
everything, then:

> "The Bcfg2 client **loops while progress is made** in the correction of
> these incorrect configuration entries. This loop results in the client
> being able to accomplish all it will be able to during one execution.
> Once all entries are fixed, or no progress is being made, the loop
> terminates."

Order is *discovered at runtime by retrying*, not computed in advance.
This is the cheapest possible correct answer when dependencies are real
but unknown, and it degrades honestly: unsatisfiable entries are reported
as uncorrectable rather than silently mis-ordered.

**b) Bundles as an inter-dependence *scope*, not a sequence.** A bundle
declares a set of entries "assumed to be inter-dependent." Membership
buys two behaviours ("bundle magic"):

> "Contained entries are assumed to be inter-dependent. To address this,
> the client **re-verifies each entry in any bundle containing an updated
> configuration entry.** Also, services contained in modified bundles are
> restarted."

So a bundle is a *re-check unit and a restart-blast-radius*, which is
exactly the thing a `notify`/`subscribe` edge encodes in Puppet — but
declared once per group instead of once per edge. Entries inside a bundle
are explicitly **not** ordered relative to each other. `independent="true"`
on the bundle opts out of all magic (the 1.4 replacement for the old
`Base` plugin).

**c) Set-inclusion dependencies, not ordering dependencies.**
`<RequiredBundle name="nfs-client"/>` pulls another bundle into the
client's configuration. Note the semantics carefully:

> "The dependent bundle is added to **the list of bundles sent to the
> client**, not to the parent bundle itself."

It changes *what is in scope*, not *what runs first*. Modification
propagation is opt-in per edge (`inherit_modification="true"`), which is
a genuinely nice separation: "A needs B to exist" and "A must restart
when B changes" are different claims, and Bcfg2 lets you make the first
without the second. The server-side `Deps` plugin does the same thing at
entry granularity ("Package X requires Package Y") — again pure
set-closure, and explicitly *not* usable on groupings like bundles.

**Why this matters for nix2cf.** The D16 audit concluded the real
constraints are a strictly sequential transport bootstrap plus
independent non-interleaving per-app chains plus safety interlocks. Bcfg2
says: only the first of those needs ordering at all; the second is a
re-verify scope; and the third it cannot express either (same finding as
the Puppet-catalog rejection). If nix2cf ever needs an ordering story,
"a `bundlesequence` for the bootstrap + a fixpoint retry loop for
everything else" is a smaller and better-evidenced design than a general
dependency graph.

**Status:** Bcfg2 is effectively dormant — docs last built 2016, last
repo push 2023-11. Reference corpus only, same disposition as Rudder
under D17. A prior evaluation already exists at `djbclark/stayturgid`
`docs/research/evaluations/bcfg2-evaluation-2026-07-12.md`; this section
is new material on top of it, and that file predates the 2026-08-13
correction pass, so treat its conclusions with the same suspicion applied
to the CFEngine evaluation.

## 5. `mgmt` — automatic dependency inference, already built

The most directly relevant find of this leg. `purpleidea/mgmt` is an
actively developed (commits within the last week) distributed,
event-driven, parallel config-management engine in Go, with an embedded
self-clustering etcd. Two features are the thing D16's reopening was
groping toward:

**AutoEdges — dependency inference from resource semantics:**

> "Automatic edges, or AutoEdges, is the mechanism in mgmt by which it
> will automatically create dependencies for you between resources."

> "since mgmt can discover which files are installed by a package it will
> automatically ensure that any file resource you declare that matches a
> file installed by your package resource will only be processed after
> the package is installed."

This is Puppet's `autorequire`, generalised and made a first-class
property of the resource type rather than a per-type hardcoding — and
crucially it is **inferred from what the system knows** (the package's
file manifest), not from what the author declared. It is per-resource
disableable (`autoedge => false`), with a documented reason that is a
real-world footgun worth stealing: packages that auto-start a service
before its config file has been written.

**AutoGrouping — batching for cost, not correctness:**

> "Automatic grouping or AutoGroup is the mechanism in mgmt by which it
> will automatically group multiple resource vertices into a single one."

Motivated by amortising the fixed cost of package operations (repo
download/verify) across many installs in one transaction.

**Why this is the important one.** Handoff `601f` predicted the answer to
communal management is "not 'adopt Puppet' but 'nix2cf grows a
dependency-inference stage' (autorequire is a property of a typed model,
and D12 already has one)." `mgmt` is an existence proof that this works,
in an actively maintained Apache-licensed codebase, with the inference
sourced from package metadata rather than from a hand-maintained table.
It should be read before that stage is designed, and it belongs in the
D16 conversation as evidence rather than as another candidate to adopt.

## 6. Non-VM site orchestration — the landscape

The open-ended half of the ask. Grouped by *shape*, since the useful
distinction is not vendor but what unit of change each one moves.

### 6a. Nix-native fleet deployers — closest to nix2cf's own grain

All are thin, stateless, self-hosted by construction (they run from a
workstation or from the node itself), Apache/MIT-class licensed, and have
no node concept to limit:

- **Colmena** (`nix-community`, Rust) — stateless, modelled on NixOps and
  morph, a thin wrapper over `nix-instantiate` / `nix-copy-closure`, with
  parallel deployment. The trade-off is explicit: being thin, it lacks
  built-in rollback and stateful monitoring.
- **deploy-rs** (Serokell) — multi-profile flake deploy tool. Its
  distinguishing feature is directly relevant to a remote fleet: it
  **connects back after activation to confirm the node is still
  reachable, and auto-rolls-back if not.** That is the exact
  self-severing-action hazard that has bitten this operator before.
- **bento** — pull-based ("KISS") NixOS fleet updater for servers and
  workstations. Pull shape matches D14's CFEngine topology better than
  the push tools do.
- **krops** — lightweight, stateless NixOps alternative with better
  secret management.

These matter because D19 adopts flakes and D12 lets the Nix module system
author the Site Model. If a node is ever NixOS, one of these is a
zero-new-concepts deploy path — but note D6: Nix is explicitly *not* the
bare-metal runtime here, so these are relevant to the Mac substrate and
to build hosts, not to the Ubuntu/Android fleet.

### 6b. Agent + bus (the Choria shape)

- **Choria** — §3 above.
- **Salt** — Apache 2.0, self-hosted master or masterless, no node limit.
  Governance is the caveat, not the licence: SaltStack → VMware (2020) →
  Broadcom (2023), with core contributors now Broadcom employees. Given
  what Perforce did to Puppet's packaging one acquisition later, the
  relevant risk is not today's licence but the packaging channel in two
  years. Still open source, still shipping (3008.x, 2026).
- **Uyuni** — Salt-based, self-hosted, GPLv2, adds a web UI and
  lifecycle management. Same GPL disposition as Rudder: read it, do not
  depend on it.

### 6c. Image / atomic-update (the IoT-growth shape)

Not VM-based and worth naming explicitly, because the operator's
constraint (2) is motivated by IoT growth and this is the family built
for exactly that:

- **RAUC** — cleanest A/B partition management with cryptographic
  verification.
- **SWUpdate** — handler-pipeline architecture, maximum flexibility, most
  setup effort; pairs with **Eclipse hawkBit** (self-hostable update
  server: rollout campaigns, device registration, artifact management)
  over the DDI protocol.
- **OSTree** — single standalone binary, native delta updates, several
  fleet backends.
- **Mender** — the most integrated out-of-box experience, but an
  open-core product with a commercial hosted tier; check constraint (1)
  carefully before adopting.
- **openBalena** — the self-hosted form of Balena; hosted Balena itself
  fails constraint (1).

The honest framing: this family solves *whole-image atomic update with
rollback*, which is a different problem from *converging configuration on
a running heterogeneous fleet*. It is a complement to CFEngine, not a
competitor — the natural seam is that image-based updates own the base OS
on appliance-class devices while CFEngine owns configuration everywhere.
Nothing in the current architecture claims that seam, which is a gap
worth noting now that IoT growth is a stated expectation.

### 6d. Agentless push (for completeness)

**pyinfra** (Python, agentless, fast) and **Bolt** (§2) occupy the slot
Ansible vacated under D13. Neither is proposed here — D13 removed push
orchestration as the primary shape deliberately, and D14 already provides
push via `cf-runagent`. Recorded so the next reader does not re-derive
whether an Ansible replacement is needed. It is not.

## 7. What this changes

- **The Rudder RBAC question is closed.** Local RBAC is free; only
  centralised identity costs money. site-pika's "future seam" splits into
  two seams of very different price.
- **Bolt and Choria both clear the hard constraints**, Choria more
  convincingly for a growing device fleet. Neither displaces CFEngine
  (D13); both remain available as adjuncts.
- **Bcfg2 and `mgmt` are the substantive additions to the D16
  conversation** — one showing that ordering can be replaced by a
  fixpoint loop plus a re-verify scope, the other showing that
  dependency *inference* from a typed model is a shipped, maintained
  technique rather than a research idea.
- **A real gap surfaced:** the architecture has no position on
  image-based atomic updates for appliance-class devices, despite IoT
  growth being an explicit constraint driver.

None of this amends the decision register. D16 still awaits the operator
conversation, and per handoff `601f` the register is not to be edited
before it.
