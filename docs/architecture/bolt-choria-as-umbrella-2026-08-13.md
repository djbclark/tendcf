# Bolt or Choria as the umbrella — and what dropping local-first changes

Operator follow-up, 2026-08-13, to `rudder-as-umbrella-evaluation-2026-08-13.md`.
Two instructions: **local-first debuggability is no longer a hard
requirement**, and: could everything live under the umbrella of one of the
other two candidates (Bolt, Choria) instead?

**Short answer:** Bolt cannot be the umbrella — it inherits the exact
Puppet-agent platform matrix and packaging EULA that disqualified Rudder,
plus it is push-only from a control node that is frequently off. Choria
**can** reach every platform in the fleet, including Apple Silicon and
ARM, with FOSS builds and no cap — it is the first candidate that does.
But Choria is not a configuration-management system and does not claim to
be, so "everything under Choria" means something different from what it
meant for Rudder.

## 0. First: what dropping local-first actually changes

It does **not** rescue Rudder. The Rudder verdict rested on two
independent objections and only one of them was topology:

- **Platform coverage** (§3a–c of the Rudder eval): no macOS agent, no
  Android agent, ARM absent from the Core repo. **Binding, unchanged.**
- **Topology** (§3d): hub-and-spoke Postgres vs. local-first SQLite.
  **Now withdrawn by the operator.**

Removing the second leaves the first standing on its own, and the first
was always the stronger of the two. Rudder still cannot manage the Mac or
the Android fleet. So the answer to "does this reopen Rudder?" is no —
worth stating plainly in case the concession was offered in the
expectation that it would.

What it *does* change, and this is genuinely useful:

- **D18 gets much cheaper.** A central reporting store is now acceptable,
  so the per-device SQLite record no longer has to be built as the
  authoritative one. This removes real work from the critical path.
- **It makes Choria's data plane usable.** Choria Streams and Scout
  (§2d) are central-store designs. Under the old requirement they would
  have been a second, non-authoritative copy. Now they can just be the
  reporting layer.
- **D18's row needs rewriting, not annotating.** Its Postgres rationale
  was already void (operator: "Postgres is fine"). Its topology rationale
  is now withdrawn too. That leaves D18 with **no surviving stated
  reason** — the decision may still be right for other reasons, but it
  currently has none on the record. Flag for the D16 conversation.

## 1. The structural point: Rudder was the only full stack

This is why the question does not transfer cleanly. Rudder bundles
configuration management **and** reporting **and** RBAC **and** a web UI
**and** inventory in one product. That is what made "just do Rudder"
a coherent proposition, and what made losing it expensive.

Bolt and Choria are **layers, not stacks**:

| | Bolt | Choria | Rudder |
| --- | --- | --- | --- |
| Convergence / desired state | via `bolt apply` (Puppet) | **no** | yes (CFEngine) |
| Ad-hoc orchestration | yes | yes | weak |
| Continuous on-node operation | **no** (push only) | yes (autonomous agents) | yes |
| Reporting / compliance | no | partial (Scout, Streams) | yes |
| RBAC / multi-user | no | AAA + OPA policies | yes (free in Core) |
| Inventory | plugins | yes (facts, registration) | yes (FusionInventory) |
| Web UI | no | no | yes |

So neither can be an umbrella in the sense Rudder would have been. The
real question is which slot each one fills in the existing architecture,
and whether one of them can fill its slot **for every platform at once** —
which is the thing that actually failed for Rudder.

## 2. Choria — the one that reaches the whole fleet

### a) The platform matrix, from the FOSS build spec

`packager/buildspec.yaml`, under the `foss:` compile targets:

| Target | GOOS/GOARCH |
| --- | --- |
| `64bit_linux` | linux/amd64 |
| `32bit_linux` | linux/386 |
| `armv5_linux` | linux/arm v5 |
| `armv7_linux` | linux/arm v7 |
| `aarch64_linux` | **linux/arm64** |
| `ppc64le_linux` | linux/ppc64le |
| `darwin_arm64` | **darwin/arm64** |
| `64bit_windows` | windows/amd64 |

This is exactly the complement of Rudder's gap. **Apple Silicon macOS
and 64-bit ARM Linux are both first-class FOSS targets** — not
subscription tiers, not community gists. That is the operator's own
machine and the entire direction of IoT growth, covered by the free
build, because Choria is a single static Go binary rather than a C
codebase plus a Perl inventory agent plus distro packaging.

### b) No cap, and the one number that looks like a cap isn't

`build/build.go` carries `maxBrokerClients = "50000"`. It is a
**build-time linker flag** (`flags_map` in the buildspec) in an
Apache-2.0 codebase you can rebuild. It is an engineering default, not a
licence term, and it is self-modifiable. Constraint (2) is satisfied
without qualification — which is more than can be said for any Puppet-
derived option.

### c) It runs without Puppet

Confirmed in the research doc: Choria descends from MCollective and
integrates with Puppet, but runs standalone, with the docs explicitly
addressing non-Puppet users in an IoT framing. No Puppet server, no
puppet-agent, therefore none of the Perforce packaging exposure.

### d) What it would actually give the fleet

- **Uniform transport and orchestration** across Ubuntu, macOS, ARM and
  (pending §2e) Android — one mechanism, one identity model, one set of
  ACLs. Today D14 gets this from `cf-runagent` plus git, which does not
  reach the Android fleet at all.
- **Autonomous Agents** — continuous on-node processes that run "without
  the need to initiate actions via RPC calls": watch files, react to
  events, run scheduled tasks with event-driven overrides, health-check
  and remediate. This is a genuine local control loop on every platform.
- **Scout** for monitoring and **Streams** (NATS JetStream) for events
  and data — now usable as *the* reporting layer rather than a
  non-authoritative copy, per §0.
- **AAA with OPA policies** for authorization — relevant to site-pika's
  communal-management problem, though without Rudder's web UI or its
  approachability for non-sysadmin co-admins.
- **Self-hosted broker**, far lighter than Rudder's JVM + PostgreSQL. It
  still wants an always-on host, but a Pi or small VPS will do, not a
  3–4 GB Linux server.

### e) The one thing that must be tested before relying on this

**Android/Termux is plausible but unverified.** Termux is a Linux
userland on an ARM64 kernel, and a static `linux/arm64` Go binary is the
most likely thing to just work there. But nobody has run it, and two
Android-specific hazards are real:

1. Go binaries under Bionic/Termux occasionally hit seccomp or dynamic-
   linker issues that do not appear on glibc ARM64.
2. Android aggressively kills background processes. A long-running
   Choria Server needs Termux:Boot and a wakelock, which is the same
   lifecycle problem the existing stack already has to solve.

This is a **cheap and decisive test**: drop the `aarch64_linux` binary on
one Termux device, point it at a broker, see if it registers and survives
a screen-off. Do that before any decision leans on Choria. Note the
standing constraint from memory — no device has ever been provisioned
from factory reset by the automation, so nothing here should be assumed
from reasoning alone.

### f) What Choria does not do

It is **not** configuration management, and its own docs say so: the
autonomous agents are "not designed to replace entire systems like
Puppet" and integrate with existing tools "via shell interfaces and exit
codes." There is no desired-state model, no convergence algebra, no
promise theory — which is the whole reason D13 chose CFEngine. Choria
would fill D14's **transport/orchestration** slot, not D13's
**convergence** slot.

So "everything under Choria" is not a replacement for the current
architecture. It is: **CFEngine keeps converging (D13 unchanged), and
Choria replaces `cf-runagent`+git as the way policy and commands reach
nodes — with the crucial gain that it reaches *all* of them.**

## 3. Bolt — cannot be the umbrella

Bolt looks attractive at first because it is agentless: SSH to Ubuntu,
SSH to macOS, and Termux can run `sshd`, so `bolt command run`,
`bolt script run` and `bolt task run` would reach every device in the
fleet with nothing installed. That much is true.

The problem is that this is only the *runner*. The moment you want
desired state, you need `bolt apply`, and:

- **`bolt apply` requires puppet-agent on the target.** `apply_prep`
  identifies targets without an agent and runs `puppet_agent::install`.
  So Bolt's configuration-management capability inherits the entire
  Puppet agent platform matrix — **no Android** — and the Perforce
  packaging position, where hardened packages sit behind a EULA capped at
  **25 nodes for development use**. That is the node cap the operator's
  hard constraint (2) exists to exclude, arriving through the back door.
- **Push-only, from a control node.** Bolt runs from a workstation. The
  operator's control node is a Mac that is frequently off — which is
  exactly why the scheduling-tier policy prefers GitHub Actions over
  local cron. Bolt has no on-node loop, so a device that is offline when
  Bolt runs simply does not get the change, and nothing on the device
  will notice or retry. For an intermittently-connected mobile fleet
  that is a poor fit independent of everything else.
- **No convergence, no reporting, no inventory, no RBAC.** Everything
  Rudder was attractive *for* (§2 of the Rudder eval) is absent.

Bolt remains a good ad-hoc tool and a reasonable thing to have on the
laptop. It is not a fleet management system and does not claim to be.

## 4. Where this leaves things

Ranked against the actual constraint — reach every platform in the fleet
with one mechanism, self-hosted, no cap:

1. **Choria** — the only candidate that clears it, and the first
   option examined in this whole research leg that covers macOS and ARM
   in the free build. Fills the transport/orchestration slot; CFEngine
   still owns convergence. Gated on the Termux test (§2e).
2. **Rudder** — strong product, wrong platform matrix. Still worth
   considering **for site-pika alone**, where the nodes are x86-64 Linux
   and the co-admins are not sysadmins.
3. **Bolt** — a useful laptop tool, not an umbrella.

The honest framing that keeps recurring: one system for the whole fleet
*and* site-pika may be the wrong goal. site-pika wants a web UI, RBAC and
approachability for non-experts; the device fleet wants uniform reach
across four platforms and offline-tolerant convergence. Those are
different products, and the research keeps finding that no single tool is
good at both.

## 5. Register implications (do not apply before the D16 conversation)

- **D18 now has no surviving stated rationale** — Postgres void,
  topology withdrawn. Rewrite the row or re-decide it.
- **D14** would change substantially if Choria is adopted: the
  git-distributed / `cf-runagent` transport becomes Choria. D13 and D15
  are unaffected.
- **D17's GPL rationale** still needs the correction recorded in the
  Rudder eval §4.
- Nothing here is applied. Per handoff `601f`, the register is not edited
  before the operator conversation.
