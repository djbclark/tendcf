# "Just do Rudder, and extend it for Termux" — what that gains and loses

> **Archival (2026-08-13).** Snapshot of research as of that date. Not current design. On conflict, [`../paper/tendcf-architecture-guide.md`](../paper/tendcf-architecture-guide.md) wins. Do not rewrite this file to bring it up to date.

Operator question, 2026-08-13, following the research leg in
`orchestration-research-2026-08-13.md`. Evaluates the option of dropping
the nix2cf/CFEngine-compile-target approach and instead standing up a
Rudder installation, adding custom work for Termux/Android and the other
non-standard platforms underneath Rudder's umbrella.

**Short answer: the umbrella does not reach the fleet.** Rudder's
platform matrix covers the smallest and easiest part of what needs
managing and none of the hard parts, and two of the gaps (macOS, Android)
cannot be closed by extension because Rudder's extension points assume an
agent that does not exist for those platforms. But the question surfaced
a real correction to D17 and a genuinely good fit for one specific site.

## 1. What "just do Rudder" would concretely mean

- **`rudder-server`** on a permanently-on Linux x86-64 host: Scala/Java
  webapp, PostgreSQL compliance database, Apache front end. 3–4 GB RAM
  for a fleet this size.
- **`rudder-agent`** on every managed node. This is not a new agent —
  it is a package bundling **CFEngine Community** (state in
  `/var/rudder/cfengine-community`) plus **FusionInventory** for
  inventory collection.
- **Custom generic methods** for the fleet's own operations, dropped in
  as CFEngine bundles under
  `/var/rudder/configuration-repository/ncf/30_generic_methods/`, then
  surfaced in the Technique Editor. This is the documented, supported
  extension path and it works well.

Note what that third bullet *is*: a way to extend **what an already-running
Rudder agent can do**. It is not a way to manage a node that cannot run
the agent. That distinction is the whole answer to this question.

## 2. What we would gain

**a) The entire reporting and compliance layer, free, today.** This is
the biggest one. D18 is currently a plan to hand-build a local-first
reporting story from CFEngine's promise-outcome log. Rudder ships a
finished version: compliance dashboards, drift detection, per-directive
per-node history, and hardware/software inventory via FusionInventory.
That is months of work already done and battle-tested.

**b) RBAC and multi-user, free, in Core — which is exactly what reopened
D16.** Per the research doc §1: `rudder-users.xml`, predefined roles,
custom roles as arbitrary permission unions, and the management UI are
all in Core since 8.2. site-pika's communal-management problem —
several co-admins, differentiated access, an audit trail — is a solved
problem inside Rudder and an unstarted one inside the current
architecture. Only LDAP/AD/OIDC identity federation costs money.

**c) A GUI authoring path for people who are not sysadmins.** The
Technique Editor lets a co-admin compose a technique from documented
generic methods without writing CFEngine policy or Nix. For a
fraternity house where the current state of the art is root passwords on
paper, this is not a nice-to-have — it is the difference between
"someone else can operate this" and "only the operator can."

**d) The ncf generic-method corpus as a live dependency instead of a
vendored fork.** D17 currently vendors and adapts individual bundle
bodies, stripping Rudder's reporting scaffolding. Under Rudder you get
the corpus maintained upstream, with the scaffolding being the point
rather than the thing to strip. No fork drift.

**e) D13 and D14 survive intact.** Rudder *is* CFEngine plus scaffolding.
Choosing Rudder is not choosing against CFEngine; the promise-theoretic
grounding that motivated D13 is unchanged underneath.

**f) Node bootstrap, key exchange, and registration are solved.** A real
and unglamorous chunk of work that the current architecture has not
started.

## 3. What we would lose

### a) ARM is subscription-gated — verified, not inferred

The supported-OS matrix lists `arm64` and `armhf` (Raspbian) only under
**"Subscription Support Only."** Rudder's own doc says Core-supported
platforms are the ones "available in the public repository," so I checked
the public repository directly rather than reasoning from the tier label:

```
9.0/bookworm  binary-arm64 -> HTTP 404
9.0/bookworm  binary-armhf -> HTTP 404
9.0/bookworm  binary-amd64 -> HTTP 200
8.3/bullseye  binary-arm64 -> HTTP 404
8.3/bullseye  binary-armhf -> HTTP 404
8.3/bullseye  binary-amd64 -> HTTP 200
```

Two release lines, no ARM packages, `amd64` and `i386` only. (The
`Release` file *declares* `Architectures: amd64 arm64 armhf i386`, which
is why the docs read ambiguously — but the `binary-arm64/` directories
do not exist.)

This does not violate the operator's hard constraint (2) literally —
there is no node *count* cap. It is arguably worse: it gates the exact
**direction of growth** the constraint exists to protect. An IoT fleet is
an ARM fleet. Under Rudder Core, every ARM device is either unmanaged or
a paid seat at €80–150/node/yr.

### b) No macOS agent, at any tier

macOS does not appear in the supported-OS matrix at all — not in Core,
not under subscription, not under extended support. The operator's own
Apple Silicon machine is a first-class managed node in §5.2 of the
architecture. Rudder cannot manage it. Whatever Rudder becomes, it does
not become the umbrella; there is a second system for the Mac by
construction.

### c) No Android agent, at any tier — and this is not extensible

Same absence, but the consequences are worse because Android is where the
actual fleet lives. "Add extra stuff for Termux under the Rudder
umbrella" would require:

1. Porting CFEngine Community to Android/Termux (plausible — stayturgid
   already has Android work, and D13 established the "no Android
   binaries" objection was an unvalidated assumption).
2. Porting FusionInventory, or forgoing inventory for those nodes.
3. Getting the Rudder server to accept, inventory, and report on a node
   type it has no OS profile for.
4. Maintaining all of that against a 3-month upgrade window (§3f).

Steps 2–4 are the expensive ones and none of them are what the generic-
methods extension point does. Custom generic methods extend a running
agent's vocabulary. They do not port an agent, and they do not teach the
server about a platform. The extension story is real but it operates one
layer above where the gap is.

### d) Topological inversion against D18

Rudder is hub-and-spoke with PostgreSQL as the authoritative compliance
record. D18 deliberately chose per-device SQLite, local-first, as the
record of truth. Adopting Rudder means abandoning D18 or running two
records with a reconciliation problem.

Be precise about which part of D18's rationale survives: the operator has
already voided the Postgres objection ("Postgres is fine, I just have a
general preference for sqlite, don't let that effect anything"). The
*topology* objection is the one that stands — local-first means a device
is debuggable and authoritative about itself when the server is
unreachable, which for a fleet of intermittently-connected mobile
devices is a functional requirement, not an aesthetic. That is a real
loss and it is not the loss D18 wrote down.

### e) A new always-on Linux server becomes load-bearing

3–4 GB RAM, Postgres, a JVM webapp, Linux x86-64 only. The operator's
control node is a Mac that is frequently off — that is precisely why the
scheduling-tier policy prefers GitHub Actions over local cron. Rudder
needs a machine that is always on and is not that Mac. That is new infra
the architecture does not currently require.

### f) The 3-month Core upgrade window becomes an obligation

Tolerable for a reference corpus. Different when the thing is the
control plane for every managed device.

### g) The compile-target thesis becomes a two-writers problem

nix2cf's premise is a typed Site Model (D12) compiled to a target (D15:
CFEngine Augments). Rudder's data model lives half in PostgreSQL and half
in a git-backed configuration repository, with the web UI as a live
writer. Compiling *into* Rudder is possible — the Augments path already
exists and Rudder consumes ncf — but you would be generating into
someone else's schema while a GUI edits the same state. This project has
already been bitten by two-writers hazards more than once, and here it
would be structural rather than incidental. You would also be choosing
between the Technique Editor and the Nix-authored Site Model as *the*
authoring surface, which partially unwinds D12 — and the Technique
Editor is one of the main things you came for (§2c).

## 4. A correction this question surfaced: D17's GPL blocker is narrower than stated

Rudder is GPLv3, and D17 treats that as the reason Rudder stays a
reference corpus rather than a dependency. That reasoning is sound for
*linking to or deriving from* Rudder's code. It does **not** apply to:

- **Running Rudder** and managing nodes with it. Use is not distribution.
- **Writing techniques and generic methods** for it. These are
  configuration data and CFEngine bundles, not derived works of the
  Rudder codebase.
- **Plugins.** Rudder adds an explicit exception to its GPLv3 allowing
  plugins built on top of Rudder to carry any licence, open or
  proprietary.

So "we can't use Rudder because GPLv3" is not correct, and D17 should not
be read that way. What blocks Rudder here is the platform matrix (§3a–c)
and the topology (§3d), not the licence. Worth fixing in the register
text when D17 is next touched, because a wrong reason recorded next to a
right conclusion is exactly the failure mode this project has already hit
three times.

(One caveat when evaluating specific plugins: the *source* for plugins
like `change-validation` and `api-authorizations` is in the public
`Normation/rudder-plugins` repo under GPLv3/ASLv2, but Rudder states the
licensing **framework** itself is not open source and plugins can gate
behaviour on runtime licence information. Public source is not by itself
proof a plugin runs unlicensed — check per plugin before relying on one.)

## 5. Verdict, and the option actually worth considering

**Rudder as the umbrella for the whole fleet: no.** It cannot manage the
Mac, cannot manage Android, and gates ARM behind a subscription. Those
are not the edges of the fleet — Android *is* the fleet, and ARM is where
it is growing. Adopting it would mean running Rudder for the easy nodes
and building the current architecture anyway for the hard ones, which is
strictly worse than either alone.

**Rudder for site-pika specifically: genuinely worth considering.** If
site-pika is x86-64 Linux boxes with several non-expert co-admins, that
is Rudder's home turf and it answers, out of the box and for free, the
four problems handoff `601f` identified as what communal management
actually brings — authorization, blast radius, a review artifact, and
tenancy — none of which the current architecture has started. The price
is running two systems, and the honest framing of that price is: site-pika
and the device fleet are different problems with different topologies and
different operators, and one system for both may have been the wrong goal
rather than an unmet one.

**The cheap version stays the default.** Taking Rudder's *ideas* without
its server — the ncf corpus (D17), the compliance-outcome vocabulary
(D18), and now the Core RBAC model as a design reference — is what the
architecture already does, and nothing found here argues against it.

**What would change this verdict:** an official macOS or Android agent,
or ARM packages moving into the Core repository. All three are worth
re-checking before any future decision that depends on this one.
