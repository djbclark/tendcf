# tendcf — Architecture (v3, definitive)

> **PROTECTED DOCUMENT — AI agents: DO NOT MODIFY without explicit,
> specific human (operator) approval for a named change.** Blanket
> instructions ("fix docs", "update stale refs", "reconcile with the
> latest") do NOT authorize edits here. Propose changes as a new review
> doc or a comment on djbclark/tendcf#1. This file is the map, not the
> worksheet. Read §0 first.

- **Status:** Definitive architecture. Supersedes
  `deprecated/architecture-DEFINITIVE-v2.md` where they conflict (this
  document wins). Numbered v1/v2 files, panel drafts, and the v2 trust
  spec are archival — see `deprecated/README.md`.
- **Date:** 2026-08-14
- **Tracker:** djbclark/tendcf#1.

This document describes the **current design and what is planned next**.
It does not recount how the design was reached. A previous configuration
stack on this fleet is **legacy reference only** — not a dependency, not
an upstream, not a name in this architecture. Patterns taken from it are
described in generic terms (for example “peer ADB help for a device that
cannot start its own privileged helper”).

---

## 0. Orientation for the AI that implements this

1. **This is a freedom project.** Interesting and correct beats minimal
   and safe when they conflict. Token spend is the cost that matters
   (§13).
2. **The reference target is a stock Linux distro on bare metal**, not
   NixOS. Nix is used for builds, optional Site Model authoring, and
   (maybe) Mac substrate — never as the installed OS a stranger must
   adopt. Ubuntu Server LTS is the working default; the distro name is
   open until Step 4.
3. **The trust/consent layer is the point.** A person should understand a
   proposed change in ordinary language, refuse it, and keep a personal
   branch — using **their** AI, not ours.
4. **Facts live in site data; behavior lives in tendcf.** Every tool
   (CFEngine, mise, Nix-for-builds, tendcf-agent) is a replaceable
   consumer.
5. **When unsure, stop.** Items in §14 are not for a cheap model to
   improvise.
6. **Prefer local knowledge over global knowledge; prefer
   machine-checkable to conventional.** If a comment says “remember
   to…”, it belongs in a schema.
7. **Put what matters at the front or the back** of anything another
   agent will read.

---

## 1. The architecture in one screen

```
  tendcf                 engine: schemas/types, generic adapters,
  (public)               default advisor prompt, compiler interface

  site-shared            reusable recipes (a Caddy role, an apt pattern).
  (optional, public)     Not live inventory.

  foreign site-shared    other people's recipes, listed as inputs.
  (read-only)

  site-private           THIS site's facts: inventory, allocations,
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

Collision of the same identity from two peer inputs is a **compile
error**. Only site-private may bind a winner or a short name.

---

## 2. Requirements (normative)

- **R1** Targets: macOS/Apple Silicon, Linux x86_64, Linux aarch64,
  Android (Termux + tendcf-agent + a Shizuku-class helper). Intel Mac
  mini out of scope.
- **R2** No permanent control node. Feature roles
  `{main, backups[], peers[]}` are data.
- **R3** Resource efficiency; no fat containers; no VMs as the build
  substrate.
- **R4** Android keeps Termux (+api, +x11), the built-in Terminal app, a
  Shizuku-class helper, tendcf-agent, CFEngine. No nix-on-droid. Nix may
  build zero-on-device-footprint artifacts only.
- **R5** No bare-metal Nix. A mainstream stock distro is the reference.
  Ubuntu Server is the default answer, not the requirement.
- **R7 / R10** Push and pull. Pull becomes user sovereignty: the person's
  own AI, suggested default prompt plus their extras, auto-review or a
  conversation. Generic layer publishable (GPL-3.0-or-later for code).
- **R11** Preserve: worktrees for development; secretspec as sole secret
  authority; CFEngine; observability stack as optional sink.
- **R12** Token budget is real. Design so routine work is cheap.
- **R13** AI agents are the primary authors. Local knowledge; machine-
  checkable conventions.

---

## 3. On-disk and repo layout (D34, D35, D21 revised)

Git-repo count is not the composition mechanism. Layers are **roles**.
Site-private holds a **lockfile** (flake-style inputs) that pins tendcf,
nix2cf, site-shared, foreign shared sites, and optional tool forks. The
signed release is the deploy artifact. There is no lockstep of sibling
checkouts that must share one tag.

| Layer | Holds | Visibility |
| --- | --- | --- |
| **tendcf** | Engine, **schemas/types**, generic adapters, default advisor prompt | Public product |
| **nix2cf** | Compiler tool only (Site Model → CFEngine JSON) | Public tool; fork only to patch |
| **site-shared** | Reusable recipes | Public or shared |
| **site-private** | Inventory, allocations, secret *names*, trust policy, extra prompt, lockfile | Private |
| **foreign shared** | Other sites' recipes | Read-only inputs |
| **tool forks** | sudo-secretspec, Shizuku, … | Optional |

**Schemas live in tendcf**, not in nix2cf. A schema change is a tendcf
interface change. An instance change is site data. The JSON Schema files,
fixtures, and lint are `schema/`, `examples/`, and `bin/schema_lint.py`
in this repository.

**Inventory is private by default (D35).** Site-shared ships:

- device *kinds* (for example “tablet that cannot do local ADB and needs
  a peer helper”)
- example / template inventories
- **explicit exports**: public endpoints and role advertisements, only
  for fields the private site marked exportable

USB serials, RFC1918 addresses, and the full host list do not go in
site-shared. Two foreign sites both shipping a host named `mac` is a
compile error unless private binds.

A host identity in trust and ChangePlans is the **device public key**,
not the hostname.

**Lockfile composition (who wins):** same identity, same priority →
evaluation error (NixOS module-system rule). Private site may bind
`caddy: from: alice` or rename. Foreign inputs are namespaced
(`alice.caddy`) so auto-provided `service:caddy` tokens do not collide;
private may alias a short name. tendcf defaults lose to an explicit
private bind.

Development happens in task worktrees, not in a deploy checkout.

---

## 4. The Site Model

Facts and intent in data; behavior in generic code; adapters translate.

### 4.1 Contents

- **inventory** — hosts + taxonomy: `arch`, `platform`, `adapter`,
  `trust_tier` (`operator` | `managed` | `consented`). `trust_tier` is a
  **class** (which consent gate applies). Who trusts whom is §10.
- **ports / paths** — allocation authorities; existence-checked at
  compile time.
- **services** — one record per service: name, run-as, command, `env`
  (secret *names* only), platform notes, role binding, `managed_by`,
  `supervisor` (see §6). Rendered to whatever unit that OS uses.
- **roles** — `role → {main, backups[], peers[]}`. This file dissolves
  “the control node.”
- **unit-writers** — exactly one writer per unit-name prefix, for every
  supervisor (launchd label, systemd instance, runit service, Jobber
  job, …). Two writers on one unit is a lint failure.
- **trust policy** — per-device, §10. Lives in site-private; compiled
  into that host’s signed release.
- Schema + lint in tendcf; example fixture paired with every schema
  (D25). YAML fallback gets a parse/re-serialize/diff check (D23) until
  the Nix authoring frontend exists.
- Lookup CLI (D24, D40): `who-provides port:443`, `does-role exist`,
  `tokens kind=service` — a tool call, not a whole-file read.

**Fields that are schema, so they land at Step 0:**

- **`provides` / `requires`** per type. A service named `caddy`
  **auto-provides** `service:caddy` unless it opts out (D40). Explicit
  `depends_on` remains available and wins. Edges in compiled output
  carry origin (authored with location, or inferred with the rule).
- **`interlocks`** per bundle — precondition → CFEngine guard +
  bundle-scoped refusal. Blast radius and reporting are schema
  constants.
- **`peer_actions`** per host/type (D37) — an operation this host cannot
  perform locally, plus the capability a helper must hold, plus the
  target’s peer allowlist (§10). Helpers are fungible within the
  allowlist (preferably a **group**, not only individual keys). Stall is
  local. Idempotent. Not a distributed lock.
- **`comprehensive` + `opt_out_reason`** per domain — default on.
  Reasons: `not-yet-migrated` (backlog, countable) or
  `deliberately-unmanaged` (permanent, rare). Extra entries are the
  only detector of two writers drifting.

Optional Nix module frontend (`mkOption` / `mkIf` / `mkDefault`):
renders to the same JSON. JSON Schema is generated from the module
options; never hand-maintain both. Strangers need not know Nix.

### 4.2 Token discovery (D40 — closes former open question 15.9)

Inference removes “you must already know the *edge*.” Naming the *thing*
is a catalog, not a graph.

1. Auto-provide `service:<name>`.
2. Lookup CLI against registries and compiled provides.
3. Unknown token, unmatched `requires`, or two providers of the same
   token → compile error listing near-misses and the catalog.

Token *kinds* are a closed enum in the schema (`service`, `port`,
`path`, `secret`, `class`, `network`, …). Token *values* are instance
data, checked at compile time — not a schema enum that changes with
every new service.

If an author has never heard of the thing they need, lookup and the
error are the discovery path. The writing rule is “don’t require the
graph,” not “don’t require names.”

---

## 5. The compiler (`nix2cf`)

A **tool**: Site Model (YAML/JSON, or Nix frontend → JSON) → merge →
conflict check → inference → [CFEngine Augments](https://docs.cfengine.com/docs/3.21/reference-language-concepts-augments.html)
(`def.json` / `host_specific.json`).

CFEngine’s [Masterfiles Policy Framework](https://github.com/cfengine/masterfiles)
already consumes that data layer. Common case: emit data, not `.cf`
text. Merge once in the compiler; do not also use `mergedata()`.

Build **first** inside this pipeline: “exactly what device X would
receive, without touching X” ([Bcfg2 `buildfile`](https://docs.bcfg2.org/)
shape). Then conflict check, extra-entry reporting, then inference.
Inference waits until real types exist on **two** platforms.

Conflict errors name the resource, every writer and location, the
values, and what a resolution looks like.

Compile-to-native-format is an established pattern
([NixOS](https://nixos.org/) → systemd, [nix-darwin](https://github.com/nix-darwin/nix-darwin)
→ launchd, [cdk8s](https://cdk8s.io/) → Kubernetes YAML). The pairing
here is Site Model → CFEngine, because of
[Promise Theory](https://markburgess.org/promises.html) and disconnected
multi-owner operation — not because the compiler mechanism is new.

**Where it runs:** operator machine or CI. Consented devices receive a
signed artifact. They do not run Nix or nix2cf.

---

## 6. Supervisors, packages, and what we borrow (D36)

A service record is one fact. The host’s `supervisor` field (or a
platform default) selects the adapter. launchd is an example, not the
model.

**Take (code or a thin wrapper)**

| Need | Source |
| --- | --- |
| apt / yum / dnf / pkg | [CFEngine package modules](https://docs.cfengine.com/docs/3.21/reference-promise-types-packages.html) |
| systemd units / timers | [NixOS systemd modules](https://github.com/NixOS/nixpkgs/blob/master/nixos/modules/system/boot/systemd.nix) for shape; CFEngine `services:` to keep them loaded |
| File / package / service idioms | [ncf / Rudder generic methods](https://github.com/Normation/rudder/tree/master/policies/lib) — vendor, strip Rudder reporting |
| launchd plist fields | [nix-darwin launchd](https://github.com/nix-darwin/nix-darwin/blob/master/modules/launchd/default.nix) — pattern, not a runtime dependency |
| Termux daemons | [termux-services](https://github.com/termux/termux-services) ([runit](http://smarden.org/runit/)) |
| Termux at boot | [Termux:Boot](https://github.com/termux/termux-boot) |
| Signed updates | [TUF](https://theupdateframework.io/) (`python-tuf` / `go-tuf`) |
| Secret names vs values | [sudo-secretspec](https://github.com/djbclark/sudo-secretspec) |
| Android privilege / peer ADB | tendcf-agent + [Shizuku](https://github.com/RikkaApps/Shizuku) (our fork if we patch) |
| Toolchains | [mise](https://mise.jdx.dev/) |

**Pattern only**

| Need | Guidance |
| --- | --- |
| [Jobber](https://dshearer.github.io/jobber/) / other cron replacements | YAML jobfile we render. On systemd hosts, prefer timers. |
| Homebrew | nix-darwin Homebrew module if Mac substrate goes that way; else CFEngine around `brew bundle` |
| OpenRC / s6 / dinit / sysv | Same record, small renderer; only when a real host needs one |
| Extra entries, interlocks, `buildfile` | [Bcfg2](https://www.usenix.org/legacy/publications/library/proceedings/lisa05/tech/full_papers/desai/desai.pdf) ideas; reimplement |
| Git-synced policy, no hub | [Flux](https://fluxcd.io/) / GitOps shape on CFEngine |

**Ours**

- Multi-input merge + conflict-as-error
- `provides` / `requires` inference and origin
- ChangePlan executor
- Consent slot + default prompt (the advisor is theirs)
- JSONL capture + agent SQLite
- Generic bundle that picks a supervisor
- Peer actions as typed cross-machine help

ncf/Rudder has no macOS or Android. CFEngine `services:` talks
systemd/Windows/sysv, not launchd. Linux packages and systemd are mostly
assembly; launchd, Termux/runit, Jobber, and the supervisor switch are
original work with those projects as templates.

Deployment: every host runs its own `cf-serverd`, policy from the signed
release via git. [CFEngine’s documented default](https://docs.cfengine.com)
is hub-and-spoke; self-bootstrap when the declared server is itself is a
documented primitive, used here fleet-wide. Push (`cf-runagent`) is the
same mechanism, not a second system.

---

## 7. Ordering, interlocks, peer actions (D16, D37)

Retry-until-stable (CFEngine) is the substrate. Explicit `depends_on`
wins where present. Inference from `provides`/`requires` is the primary
authoring mechanism.

Do **not** compile everything into a Puppet-style catalog. Roles examined
so far are largely independent. A site whose roles interleave into a
real DAG would want a different design.

**Interlocks** are not edges: “do not enable always-on VPN lockdown until
the VPN is authenticated.” Bundle-scoped refusal; author cannot narrow
blast radius or silence the report.

**Peer actions (D37)** are the cross-machine shape that actually fits an
often-offline fleet. Example from our last system: a device that cannot
start its privileged helper locally; any healthy peer in its allowlist
may do it over ADB; if every helper is down, **only that device waits**.

This is not a [distributed lock](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html)
and not Bcfg2’s [LISA ’06 FSM](https://www.usenix.org/conference/lisa-06/directing-change-using-bcfg2)
over releases. Those stall the *fleet* when one box is unreachable.

Cross-machine “wait until the server is serving the new export” is a
**local probe** (or a wait for a signed apply-attestation from the host
that holds that role). Bcfg2’s FSM is a **view** reconstructed from JSONL
+ optional attestations, never a coordinator.

[Bcfg2 `altsrc`](http://docs.bcfg2.org/) still transfers: Termux
`$PREFIX` vs Linux/macOS absolute paths sharing one source.

---

## 8. Local record (D18 revised)

The local capture must exist on CFEngine Community anyway. The device’s
record is authoritative because devices go unreachable; a central copy
is incomplete in exactly those windows.

**Capture and index are different files:**

1. **Capture:** append-only JSONL. One `write()`. If logging fails, a
   line is lost, not the history. This is what
   [CFEngine Enterprise](https://docs.cfengine.com) already does locally
   (`promise_log.jsonl`) before a hub copies it into SQL. Community needs
   the same glue. [osquery](https://osquery.readthedocs.io/en/latest/deployment/logging/)
   likewise logs results as JSON lines.
2. **Index:** SQLite inside **tendcf-agent**, for queries, extra-entry
   counts, “what release am I on.” Rebuildable from JSONL. If the DB is
   corrupt, history still exists.

CFEngine never opens SQLite. The agent tails (or receives) the log.
Single writer to JSONL (engine or its wrapper); single writer to SQLite
(the agent).

**Android UID isolation (looked up, 2026-08-14).** Termux (`com.termux`)
and tendcf-agent are different UIDs. The APK **cannot** read
`$PREFIX/...` as files. [RUN_COMMAND](https://github.com/termux/termux-app/wiki/RUN_COMMAND-Intent)
is a user-granted bridge with stdout via `PendingIntent`, not a log
directory. Therefore:

- tendcf-agent owns **both** JSONL and SQLite in **app-private storage**.
- Either cf-agent runs as a native helper of the agent (same UID), or a
  Termux-side reporter **pushes** lines to the agent (localhost /
  ContentProvider). Never “agent opens Termux’s files.”
- [Room](https://developer.android.com/training/data-storage/room) /
  Android’s SQLite is the index path, not Termux `sqlite3`. Use
  `synchronous=FULL` if WAL is on; OEM freezers OOM-kill mid-commit.

Optional best-effort push of a subset into Vector / OpenObserve /
Grafana is never the record of truth. Fleet-wide yes/no questions query
reachable devices and treat the rest as unknown.

Every row carries the release stamp. Each device records which release
it is converged to.

---

## 9. Releases, ChangePlan, TUF (D41, D42)

Configuration reaches devices only as a versioned, signed release plus a
per-host **ChangePlan**: closed `capability` vocabulary, exact
`resources`, `target` bound to the host public key, rollback, expiry,
nonce, attributed ordering edges. The executor refuses anything outside
that set.

Signing: [TUF](https://theupdateframework.io/) subset sized for one
operator (offline root 2-of-3, targets, snapshot, emergency). High-water
mark on every applying client.

**First-run root (D41).** The [TUF spec](https://theupdateframework.github.io/specification/latest/)
assumes a good trusted `root.json` shipped with the updater, out of
band. TOFU is documented as an example in some clients; we do **not**
use it for consented devices. Install shows the root key IDs /
fingerprint; the person compares that to a channel they already trust
(operator, printed card, published fingerprint in site-shared). Later
root rotation is in-band (threshold of old **and** new keys). Threshold
compromise of root is again out of band.

**Emergency vs consent (D42).** Revocation, “do not apply releases signed
by K,” freeze detection, and high-water rejection **tighten** what may
run. They do not need a local yes. Installing new targets still does, on
`consented` devices. An optional enrolled policy “I pre-grant emergency
security patches from role E” may exist; **default off**.

Verifiable layer authorizes. Semantic layer (template-filled from IR
fields; free prose must cite those fields) briefs the advisor; never
authorizes.

Push: any host holding `deploy-origin`, to **operator** (and
operator-chosen `managed`) hosts. Push to a `consented` device still
requires that device’s consent grant. Pull: each host’s own schedule,
gated on timestamp role + quotas before it is autonomous.

---

## 10. Per-device trust (D38)

`trust_tier` is not the trust model. Full-mesh “every device has operator
root to every sibling” is **not** the product default. It is a
site-private policy some operator-tier labs may still choose. Our last
system did that; it is not tenable once devices belong to more than one
person.

Each device carries a **local trust policy** in its signed release
(authored in site-private). It does not phone home to ask.

| Axis | Question | Default |
| --- | --- | --- |
| **Release** | Whose signatures may change me? | Site TUF root enrolled at the first-run ceremony |
| **Consent** | Do I also need a local yes? | `operator`: no. `consented`: yes (advisor key). `managed`: operator-chosen |
| **Peer** | Who may act *on* me (ADB, SSH, peer-help)? | Nobody, unless listed. Prefer **groups** (“household helpers”) plus allowed verbs |
| **Attestation** | Whose “I applied this” counts for my advisor tools? | Only sets that person configured |
| **Secrets / cache** | Who may receive this secret or substitute this store path? | secretspec resolver; cache keys `operator` only |

Peer actions (§7) check the **target’s** peer allowlist, not only “the
helper has a capability.” Identity is the device public key.

A label in inventory does not enforce this. The executor does. That was
already a red-team finding; it still holds.

Web-of-trust thresholds (“50% of people I trust have installed this”)
live in the **advisor plug-in**, not in the executor.

---

## 11. The person’s own AI (D39)

We never run their model, see their prompt, or see the conversation. We
offer a change and accept a signed yes/no. Same shape as a
[Kubernetes admission webhook](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/).

- At install they enroll an **advisor key** (or a local app/socket) in
  site-private.
- tendcf ships a **suggested default prompt** as a replaceable public
  file. They may append or replace it.
- Modes: auto-review, or a conversation with them first.
- Return path: `accept | reject`, signed by the enrolled key, bound to
  that plan’s nonce. Timeout is deny. Advisor down → fail closed for
  *installs* (revocation still applies, §9).
- Custom tools (OpenPGP WoT, a transparency log, a chain, gossip of
  signed apply-attestations) are theirs. Deadlock among “everyone
  waiting for everyone else” is a separate project that consumes
  attestations. tendcf owes: the ChangePlan IR, optional exportable
  apply-attestations, the `accept | reject` slot.

Proposing side and consenting side are different programs. The advisor
never authorizes; the executor does, against the signed grant.

Personal branch: theirs, applied under their consent; never auto-merges
into anyone else’s trust domain. Upstream-heal is a suggestion their
agent evaluates.

---

## 12. Platforms

**macOS (adapter #1).** Services as CFEngine promises from `services.yml`
via the launchd adapter. Dry-run default. nix-darwin / home-manager are
**substrate only**, Step 7, gated on §14.1. Unit-writers lint is the
safety rail on a live daily driver.

**Android (adapter #2).** Same Site Model vocabulary. Runtime: Termux +
tendcf-agent + Shizuku-class helper + CFEngine. Agent owns logs (§8).
Peer actions cover devices that need external ADB help.

**Linux (adapter #3, adoptability keystone).** Stock distro; mise
toolchains + CFEngine everything else. Distro choice open until this
step.

Future classes (extension points, no build-out): OpenWrt; consented
iPhone/wearables that consume artifacts; firmware as Nix-built
artifacts; image-based appliances (RAUC / OSTree family).

Nix store: never a multi-host `NIX_STORE_DIR` (D20). Cache role is
`operator` only; NAR digests in the manifest (RT-05).

---

## 13. Build order

Each step leaves a coherent system. Not a schedule.

| Step | What |
| --- | --- |
| 0 | Schemas in **tendcf** (`schema/`, `examples/`, `bin/schema_lint.py` — provides/requires, interlocks, comprehensive, report-row). Remaining: peer_actions, trust-policy shape, generic unit-writers, lookup stub, YAML canonicalize. Transcribe reality (`not-yet-migrated` is the correct day-one state). |
| 1 | macOS services adapter. Dry-run default. No nix-darwin. |
| 2 | Android under the Site Model; Termux types; agent owns JSONL+SQLite. |
| 3 | nix2cf: `buildfile` first, conflict, extra-entry, then inference (needs steps 1–2). |
| 4 | Linux reference path on a stock distro. |
| 5 | First real Linux host; prove roles are data. |
| 6 | Signed releases, push-only, ChangePlan executor. Operator hosts. |
| 7 | Optional Mac substrate (nix-darwin) if §14.1 says yes. |
| 8 | Pull / self-update. |
| 9 | Consent surface + default prompt + advisor slot. |
| 10+ | Demand: builder/cache, APK provenance, WoT-as-advisor-tools, extracting the publishable layer when a second person runs it. |

Dry-run is the standing posture on the first platform (the machine that
cannot easily be reimaged). Reporting is an adoption requirement.

---

## 14. Premium-token residue

Cheap models execute this document everywhere except:

- **§14.1** nix-darwin on the Mac, yes or no (gates Step 7 only).
- **§14.2** ChangePlan IR + executor capability vocabulary. Do not
  improvise. Independent adversarial review before build.
- **§14.3** Advisor/personal-branch loop + AI-in-the-loop red-team
  (prompt injection, poisoned model, semantic layer as injection).
- **§14.4** TUF-subset ceremony + recovery runbook, including the
  first-run fingerprint check.

If a cheap model hits one of these unresolved, it writes a question doc
and stops.

---

## 15. Decision register (current)

Older “superseded by” archaeology lives in
`deprecated/architecture-DEFINITIVE-v2.md`. This table is what holds now.

| # | Decision | Resolution |
| --- | --- | --- |
| D2 | Site Model formality | Schemas at Step 0; writer-lint immediate. |
| D6 | Nix on bare metal | No. Builds / dev shells / optional Mac substrate / optional authoring frontend only. |
| D8 | Trust layer | Build it, gated. Sovereignty is the point. |
| D10 | Task runner | `just` for humans; mise for toolchains. |
| D12 | Authoring frontend | Nix modules MAY author the Site Model; YAML/JSON remains the wire format and the stranger path. |
| D13 | Service owner | CFEngine promises everywhere; mise toolchains only. |
| D14 | Deployment shape | Git-synced policy; `cf-serverd` on every host; push and pull are one mechanism. |
| D15 | Compile target | CFEngine Augments, not freehand `.cf`. |
| D16 | Ordering | No Puppet catalog. Inference + fixpoint + authored `depends_on`. Interlocks. Default-on comprehensiveness. |
| D17 | ncf | Vendor generic methods as a reference corpus; strip Rudder reporting. |
| D18 | Local record | JSONL is the durable capture; SQLite in tendcf-agent is the index. On Android the agent owns both in app-private storage. |
| D19 | Composition | Private-site lockfile pins inputs (DAG). Signed release is the deploy artifact. No sibling-repo tag lockstep. |
| D20 | Nix store locality | Single writer per host. |
| D21 | Schema home | **tendcf** owns schemas/types. nix2cf is the compiler. |
| D22 | Platform sequence | macOS, Android, Linux. |
| D23 | YAML canonicalize | Parse, re-serialize, diff on the YAML path. |
| D24 / D40 | Lookup + auto-provide | Registry/token CLI; default `service:<name>`; compile errors teach names. |
| D25 | Schema/example pairing | Lint fails if unpaired. |
| D26 | Root AGENTS.md | Not on a performance rationale. Discoverability-only if ever added, hand-written. |
| D27 | This file | CI/pre-commit fails diffs to this path without `Approved-change:` trailer. |
| D28 | Guardrail weight | Existence checks for the large IaC error class; extra entries for omission; schema for the tiny syntax class. |
| D29 | Semantic layer | Template-fill from IR; free prose cites IR fields. |
| D30 | `.cf` escape hatch | Prefer a grammar before lint-only, when that surface is exercised. |
| D31 | Front or back | Critical fields at start or end of agent-facing artifacts. |
| D32 | Compiler prior art | Mechanism common; Nix+CFEngine pairing not the novelty claim. |
| D33 | No control node | Promise Theory’s; GitOps is the closest shape. |
| D34 | Repo layers | tendcf / site-shared / site-private / foreign / optional tool forks. Conflict-as-error; private binds. |
| D35 | Inventory | Private by default; kinds, templates, explicit exports may be shared. |
| D36 | Supervisors | Generic; launchd is one adapter. See §6. |
| D37 | Peer actions | Typed cross-machine help; local stall; no distributed lock; FSM is a view. |
| D38 | Trust | Per-device policy, several axes. Full mesh is a site choice. Executor enforces. |
| D39 | Advisor | Their AI, their key, our slot. Default prompt replaceable. |
| D41 | TUF bootstrap | Ceremony + fingerprint; not TOFU on consented devices. |
| D42 | Emergency | Restrictive metadata without consent; new installs still gated. |

Silence = proceed from Step 0. Objections amend this register.

---

## 16. Open questions (remaining)

1. Is inference justified, or is retry-until-stable already the local
   answer?
2. Is the writing rule an argument or a hypothesis?
3. Do `not-yet-migrated` counts get ground down without a dedicated role?
4. Is per-domain the right granularity for comprehensiveness?
5. When a global yes/no arrives, is querying reachable devices and
   treating the rest as unknown enough?
6. Does edge origin information actually turn “why is this waiting?”
   into a query?
7. Does the ChangePlan capability list survive real operations without
   an escape hatch?
8. If the real AI failure mode is plausible-looking output that types
   do not catch, are we hardening the wrong surface?

Token discovery (old 15.9) is **D40**, not open. Trust-tier-as-label
(old confusion with full mesh) is **D38**.

---

## 17. Document map

- **This file** — authoritative architecture + build order.
- `README.md` — pointer.
- `deprecated/` — v1/v2 and panel drafts. Do not update them.
- Dated `*-2026-08-13.md` research notes in this directory — evidence
  trail for older decisions; v3 wins on conflict.
- `docs/paper/tendcf-architecture-guide.md` — same architecture, plainer
  language.
- `docs/paper/tendcf-architecture-paper.md` — technical paper.
- `schema/`, `examples/`, `bin/schema_lint.py` — Site Model contract.
- `djbclark/nix2cf` — compiler tool (Step 3). Consumes this contract.

Local prior-art clones (not dependencies): `~/src/config-mgmt-prior-art/`.
