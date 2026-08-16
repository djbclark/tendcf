# tendcf — Architecture (v3, definitive)

> This file is the map, not the worksheet — it records decisions and
> build order rather than working notes. It is freely editable: keep it
> current rather than proposing changes elsewhere. Read §0 first.

- **Status:** Implementer map (decisions, build order, protection).
  Supersedes `deprecated/architecture-DEFINITIVE-v2.md` where they
  conflict. The vetted current-state description is
  `docs/paper/tendcf-architecture-guide.md`; where this file and that
  guide disagree on the current design, **the guide wins**. Numbered
  v1/v2 files, panel drafts, and the v2 trust spec are archival — see
  `deprecated/README.md`.
- **Date:** 2026-08-15 (§9 rewritten for Model B; D43/D44 added)
- **Tracker:** frdminc/tendcf#1.

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
  Signed release         manifest + per-host canonical goal file
                         (TUF-subset; the device diffs it against its
                         approved baseline and the validator refuses
                         anything outside the approved diff — §9)

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
- **R7 / R10** Push and pull. Pull becomes user sovereignty: the person’s
  own AI, suggested default prompt plus their extras, auto-review or a
  conversation. Generic layer publishable (GPL-3.0-or-later for code).
- **R11** Preserve: worktrees for development; secretspec as sole secret
  authority; CFEngine; observability stack as optional sink.
- **R12** Token budget is real. Design so routine work is cheap.
- **R13** AI agents are the primary authors. Local knowledge; machine-
  checkable conventions.

---

## 3. On-disk and repo layout (D34, D35, D21)

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
  `depends_on` remains available and wins. Origin-bearing edges
  (authored with location, or inferred with the rule) are **preview-channel
  only** — compiler output the person and the advisor see, never the goal
  file (corrected from this section's earlier text, which said edges in
  compiled output carry origin without scoping which compiled output:
  that collides with §9.5's no-attribution rule once the goal file is the
  compiled output the device consumes. Resolution: the goal file carries
  no edges in v1, and origin-stripped edges at most if edges are ever
  added to it; C-8, reconciliation §8).
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

### 4.2 Token discovery (D40)

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
- Goal-file render, canonicalization, and the ChangePlan validator (§9)
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

## 8. Local record (D18)

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

## 9. Releases, ChangePlan, TUF (D41, D42, D43, D44)

Configuration reaches devices only as a versioned, signed release. The
per-host payload of that release is the host’s **complete canonical goal
file**: one fully resolved JSON document describing the whole managed
state of that device. The **ChangePlan is the diff** between the goal
file the device has already approved and the one the release proposes,
and the on-device executor is a **validator** over that diff — it
compares two canonical documents against an approved diff and performs
no policy interpretation (**D43**).

**Model A is superseded.** The former text of this section — a closed
`capability` vocabulary, per-operation `resources`, and an executor that
“refuses any effect outside that set” — is withdrawn, together with the
vocabulary’s versioning and skew policy. CFEngine has no runtime
capability confinement, so that executor could only exist as a pre-flight
*interpreter* of the vocabulary plus a proof that the vocabulary
describes what the rendered policy actually does; neither artifact exists
nor is in budget. Authority: `e1-adjudication-xhigh-2026-08-15.md`, which
is final and supersedes `e1-adjudication-2026-08-15.md`. Section
references below of the form **E1 §5.x** are to that note.

The compiler (§5) therefore gains a **render** stage: merge → conflict
check → render of the complete per-host goal file. **Decided** (this
paragraph left open until the schema family landed; closed by
`goal-file-schema-reconciliation-2026-08-15.md` §9): the goal file and
the CFEngine Augments JSON (`def.json` / `host_specific.json`) are not
one document. The goal file is the signed wire artifact and the object
consent binds to; Augments JSON is produced from it by a **device-side
projection**, run inside tendcf-agent after approval, and never appears
on the wire. The projector's target is
`$(sys.workdir)/data/host_specific.json` and nothing else; its output is
`{"vars": {…}}` with no sibling keys — no `variables`, no `classes`, no
`inputs`, no top-level `data`. `def.json` remains MPF glue under the
policy-tree digest (§9.8) and is never a per-host slot: 3.27.1 drops its
unknown keys silently, the worst of the candidate targets. A
compiler-shipped projection sibling, hash-bound on the approval record,
was considered and rejected — it reopens the approved-equals-applied gap
Model B exists to close, since no one *reviews* a hash-bound sibling the
way the goal-file diff is reviewed, and the projector must exist under
either option, so putting it device-side costs one implementation with
two call sites (the agent binary, invoked directly and by CI for golden
tests) rather than a second wire artifact, a per-host TUF sibling target,
and an approval-record hash extension. The projector **MUST be
policy-free** — a structural re-keying only (entries → the generic
bundle's containers, tombstones → the negative-promise lists, trust
entries → the agent's own config) — carried as residue R21; any change
that inspects entry *values* to decide output *structure* is the
interpreter returning and is a named §14.2 review target. `def.json`'s
own digest binding is unmoved (§9.8); `augments_digest` inside the goal
file stays rejected as circular.

### 9.1 Where the diff is computed (E1 §5.1)

- The **full canonical goal file MUST be the signed wire artifact.** The
  diff MUST NOT be shipped as the artifact: reconstructing
  `new = old + patch` on the device would make patch application a second
  interpreter, and would make the applied state derived rather than
  directly signed.
- The **authorizing diff MUST be computed device-side**, between the
  device’s currently-approved goal file and the received one. This is
  what makes the approved object equal the applied object at *any*
  staleness: a device seven releases behind briefs and approves the one
  true diff from its own signed baseline.
- The **compiler-side diff is a preview** — author review, CI regression
  artifact, cross-check. It MUST NOT be the object consent binds to.
- When the device’s baseline equals the release’s expected baseline, the
  device-computed diff MUST equal the compiler’s predicted diff.
  Inequality is a **reportable integrity flag**, never a silent
  condition.
- Consequence, accepted: the advisor round trip happens **after** device
  contact, and pre-generated briefings are previews rather than the
  consent object.
- **Baseline integrity is the root of the gate.** The stored approved
  goal file MUST be integrity-protected and its verification MUST be a
  validator precondition, ordered before the diff is computed. Corrupting
  or swapping it either denies service or launders arbitrary state
  through the baseline ceremony of §9.4.
- The accept binds per DC-2, instantiated for the goal file as an
  **approval record**, not a hash concatenation (corrected from this
  section's earlier formula
  `Sig_advisor( H(old_canonical) ‖ H(new_canonical) ‖ device_nonce [‖ H(briefing_bytes)] )`,
  whose optional briefing member was an encoding-ambiguity hazard — a
  variable-arity concatenation does not fix which bytes were signed when
  the optional member is absent; C-5, reconciliation §11). The signed
  object is the **JCS bytes of the approval record with the `signature`
  member removed**. The record carries: `schema_version`, `host` (the
  target key), `baseline_sha256` (absent only at first adoption, a named
  §14.2 review target), `proposed_sha256`, `nonce` (device-issued),
  `approval_seq` (monotonic, DC-2 single-use), optional
  `briefing_sha256`, `verdict` (`accept` | `reject` | `withdraw`),
  `refused` (hunk key-paths, present iff reject, annotation only),
  `ceremony_class` (`ordinary` | `privileged` | `baseline`, asserted by
  the approver and checked against the validator's own derived
  requirement, §9.8), and `signature`, valid for exactly one target key.
  The validator MUST recompute every hash. DC-2 applies in full:
  per-target validity, device nonce, monotonic-counter single use,
  persisted rejects.
- `cf-agent --simulate` remains an **optional human-facing confirmation**
  of actual-state delta, never a mechanism of the gate. File the upstream
  `--simulate-output=json` issue before Step 3 code.

### 9.2 Canonicalization and the shape of the diff (E1 §5.2)

Serialization noise is camouflage, so canonicalization is a consent
property, not a testing nicety.

- **Wire format is JSON.** YAML stays an authoring format for Site Model
  sources and never appears on the wire (D23’s parse/re-serialize/diff
  check was the symptom of why).
- **Canonical form is RFC 8785 (JCS)** plus the structural rules JCS does
  not give: every set-semantics collection is a **map keyed by identity**
  — entries addressed by the `(domain, kind, id)` key path, nested
  `domains → <domain> → <kind> → <id>` — rather than an array sorted by a
  schema-declared key (corrected from this section's earlier text:
  RFC 8785 orders object members by UTF-16 code units, so a
  `(domain, kind, id)`-sorted array needs its own comparator definition, a
  second ordering rule alongside JCS's that the corpus's own review caught
  disagreeing with it at a non-BMP boundary; a map has no second
  definition to get wrong, and duplicate-key rejection gives uniqueness
  from the parse itself instead of a separate lint rule — reconciliation
  §2.2, C-2). Two positional arrays survive where order is meaning
  (`command` argv, `pre_action.command`); one sorted string-set array
  (`verbs`, ascending code-point order) survives for when the peer-grant
  kind lands. Strings are NFC normalized; no floats anywhere in the goal
  file; **booleans are legal** — JCS gives them one canonical spelling,
  and forbidding them would only force a second spelling as `"true"` /
  `"false"` strings (C-3); signatures detached; and no nonces, timestamps,
  or other run-varying fields inside the diffed object.
- **The goal file is fully resolved and the schema defines no defaults.**
  Every meaningful field is present with its explicit value; authoring
  defaults are resolved by the compiler before render; empty collections
  are invalid, so omission is the only representation of “none.” One
  meaning therefore has exactly one byte representation, and a later
  change to an authoring default can never reinterpret an already-signed
  file.
- **Refuse, never normalize.** Validator and lint MUST reject any goal
  file that is not byte-identical to the canonicalization of itself.
- **The diff is structural, not textual.** Hunks are at **entry**
  granularity, addressed by the `(domain, kind, id)` key path, each
  carrying the full old and/or new entry. Field-level diffs are derived
  for display. A text diff of canonical bytes is a permitted rendering
  and never the authoritative object.

### 9.3 Accept is all-or-nothing (E1 §5.3)

- A **partial accept MUST NOT be applied.** The accept verb is
  all-or-nothing per proposal. No device applies a state the compiler did
  not render and conflict-check.
- The advisor MAY return a **refusal annotated with the hunks that drove
  it**. The proposer then withdraws the corresponding source-level
  changes, re-renders the complete goal file, re-runs the conflict check,
  and offers a new diff.
- **Dependency-grouped hunks are rejected** and MUST NOT carry apply
  semantics. A correct dependency relation over hunks needs exactly the
  global `provides`/`requires` knowledge the inference cut removed, and a
  wrong grouping silently produces an unchecked applied state. Grouping
  MAY exist later as a *display* aid in the preview layer only.
- Bundling is defeated by cheap counter-proposal, not by partial apply:
  refusal costs the proposer a re-render, not the person their patch. A
  proposer who re-offers an annotated-refused bundle creates exactly the
  record TC-19’s persistence rule exists to surface. The counter-proposal
  loop is itself a fatigue channel to watch.

### 9.4 The two total-diff events are baseline ceremonies (E1 §5.4)

First adoption and schema migration present a total diff. They are a
distinct consent class with their own rules, and what each may claim is
bounded rather than pretended-reviewed.

- **First adoption is governed by a minimal-claim rule.** The initial
  goal file, accepted at D41’s first-run fingerprint ceremony, MAY manage
  only the domains the operator explicitly enumerates at that ceremony.
  Every other domain enters as `not-yet-migrated`. Each later domain
  migration then arrives as an ordinary reviewable hunk set, and the
  `not-yet-migrated` backlog counter (§4.1; guide §11) doubles as the
  consent metric. The honest day-one goal file is small in **managed
  surface**, which is already the correct day-one state.
- **Schema migration MUST be semantics-preserving and mechanically
  checked.** A migration release is valid iff `diff(migrate(old), new)`
  is **empty** apart from the schema-version bump — a pure migration
  presents as a one-line reviewable change. Mixing migration and semantic
  change in one release is **forbidden**; split into two releases. The
  migration function ships in the validator update, which itself arrives
  as an ordinary diff under the old schema (§9.6).
- The approval record MUST carry a **ceremony class** — ordinary,
  privileged, or baseline — adequate to what is being approved.

### 9.5 Hunk attribution is a query, not a field (E1 §5.5)

Attribution (“which source layer produced this hunk”) **MUST NOT appear
in the authoritative format** — not day one, not later. Three independent
reasons, any one sufficient:

1. It is **impossible** where the authoritative diff is computed: under
   §9.1 the device computes it and the device has no source layers. In
   the compiler’s preview it is proposer-asserted provenance the device
   cannot verify — TC-07’s forgeable citation at the hunk level.
2. Provenance plumbed through merge and render is the origin-tracking
   machinery CUT-3 cut, returning at the value level.
3. Attribution stored in the canonical artifact makes semantically
   identical states byte-different when sources are refactored, breaking
   §9.2’s one-meaning-one-representation property.

What replaces it: render purity makes attribution **reconstructible on
demand**. A compiler-side `explain-hunk` tool re-renders with a candidate
source change reverted, diffs the renders, and subtracts; CI can
attribute a whole preview diff mechanically and checkably, against actual
renders rather than an assertion. Its output travels in the
preview/briefing channel as DC-3-labelled untrusted context. The tool is
due before the consent surface (Step 9). Fan-out fatigue is real and is
mitigated here plus by §9.3’s counter-proposal loop — not by a signed
field.

### 9.6 Schema version and unknown entry kinds: fail closed (E1 §5.6)

- The goal file carries a `schema_version`. Its contract is **stricter
  than** `common.schema.json`’s `contract_version` rule: *any* change to
  the entry-kind set, additive included, MUST bump the version, so that
  an old validator can tell from the version alone whether it can fully
  interpret the file.
- A validator that sees a version above its ceiling, or an entry kind it
  does not recognize, **MUST refuse the entire goal file** with a
  distinct reported reason; the device keeps converging on its last
  approved state. Refusal is a visible, reportable stall, not a brick.
- **Ignore-unknown is rejected outright.** An ignored unknown entry is an
  unreviewed change riding a reviewed diff — fail-open in exactly the
  sense the validator exists to prevent.
- Strandedness is prevented at the compiler, not the device: goal files
  are per-host, so the compiler MUST render each host’s file at the
  highest schema version that host’s **last-reported** validator supports.
  A long-dark device is rendered at its old version until it reports back.
  *Correction to E1 §5.6, which says the report rows already carry this:*
  they do not. `report-row.schema.json` carries `release` and
  `converged_release` but has no validator/agent version column, so the
  reported field is a **schema addition D44 requires**, not an existing
  property to read.
- A schema bump ships in **two phases**: first the validator/agent update
  as an ordinary diff under version N−1 — a privileged-region hunk, TC-25
  class — then the migration release under §9.4’s empty-diff rule. There
  is no separate release-lint phase-order check (cut from this section’s
  earlier text, C-6, reconciliation §5): "the compiler refuses to render
  version N for a host whose reported ceiling is < N" *is* the two-phase
  enforcement, in the one place the per-host knowledge already lives — a
  release-lint restatement would need the same report data and duplicate
  the same rule.

Cost, accepted: the compiler carries multi-version render ability for a
window and tracks per-host versions. The price is paid in one place
rather than as device-side leniency on every device.

### 9.7 Coverage travels in the goal file (E1 §5.7)

The goal-file schema **MUST include the per-domain coverage
declaration**, restated as a **single enum** —
`comprehensive` / `not-yet-migrated` / `deliberately-unmanaged` — never a
verbatim `$ref` of `common.schema.json#/$defs/domain_coverage` (§4.1):
that def carries a `default`, an optional boolean where
absent-vs-present-true is two spellings of one meaning, required free
prose, and if/then contradiction guards a single field does not need.
Same three meanings; the Site Model keeps its authoring shape; the
compiler resolves to the enum (corrected from this section’s earlier
text, which named the `$ref`; C-1, reconciliation §4.1). Entries nest
**inside** the domain envelope
(`domains → <domain> → {coverage, entries}`), so an entry without stated
coverage is unrepresentable and `deliberately-unmanaged`-with-entries is
a schema violation, not a lint finding.

The diff’s meaning depends on coverage, and there are **three** silence
classes, not two: silence in a `comprehensive` domain means “no change”;
silence in a `not-yet-migrated` domain means “not described”; and a
**domain absent from the map entirely is `undeclared`** — a third class
E1 §5.7 does not name, because the unbounded unknown cannot be
enumerated and declaring a domain is precisely the act of naming a
backlog item so it becomes countable (C-10, reconciliation §4.1).
Site-Model-declared domains all appear in every goal file, at minimum as
`not-yet-migrated`; a domain’s first appearance is itself a reviewable
`coverage_changes` item with `"old": "undeclared"`. Validator and
briefing MUST NOT let any two of the three read alike. A coverage
transition is itself a hunk, and reclassification to
`deliberately-unmanaged` (DC-37) is a distinct review class; the full
transition-to-ceremony derivation is §9.8.

Goal-file completeness is a **contract, not a given**: a diff over a
non-comprehensive domain proves nothing about what else changed on the
device.

### 9.8 Privileged regions, removals, fetched content

- **Privilege is validator-held, never proposer-set.** The diff format
  carries no privilege flags — those would be forgeable. The validator
  derives privilege from its own local list, whose floor is: trust
  policy, advisor keys, peer allowlist, policy-tree digest,
  agent/validator binary and version, device resource policy, and
  `schema_version` itself. The approval record MUST carry a ceremony
  class adequate to the derived privilege (§9.4). Coverage transitions
  (§9.7) derive their ceremony class the same way — retreat is
  privileged, not forbidden, because forcing a stall or a lie is worse
  than a loud, reviewable step backward:

  | Coverage transition | Ceremony class |
  | --- | --- |
  | `undeclared` → `not-yet-migrated` or → `comprehensive` | ordinary (declaring / tightening) |
  | `not-yet-migrated` → `comprehensive` | ordinary (tightening) |
  | any transition **into** `deliberately-unmanaged` | privileged (DC-37 class) |
  | any transition **out of** `comprehensive` (incl. → `undeclared`) | privileged (retreat) |
  | any transition **out of** `deliberately-unmanaged` | privileged (reversing a deliberate decision) |

  One uniform rule the validator holds: a coverage transition is
  privileged iff it touches `deliberately-unmanaged` or leaves
  `comprehensive`. Retreats are counted next to Q11’s migration counter
  (reconciliation §4.3).
- **Removal is a state, not a diff-compiled actuation** (corrected from
  this section’s earlier text, which had the negative promise compile
  from the diff itself — read literally, that breaks convergence: the
  applied configuration becomes a function of the diff as well as the
  goal file, the diff has acquired apply semantics on the exact ground
  §9.1 refused to ship diffs on, and a one-shot imperative is lost by a
  crash, a re-run, or a stale device’s N−7 → N catch-up; C-4,
  reconciliation §6). Actuated entries carry `state: "present" |
  "absent"`. A removal is a **replace hunk** (`present → absent`) whose
  tombstone persists in the goal file, and the negative promise (file
  delete, package absent, `service_policy => "stop"`) renders from the
  **file**, not the diff — idempotent, crash-safe, re-release-safe,
  stale-catch-up-safe. A removal correctly *is* a modify of `state`; the
  real smuggling hazard is the **bare entry deletion**, which means “stop
  managing,” not “remove from device” — the briefing MUST render the two
  distinctly (“stops being managed; the thing REMAINS” vs “will be
  stopped and unloaded”). Tombstones are legal in `comprehensive`
  domains: there is no sweeper, only extra-entry *reporting*, so
  forbidding the tombstone there would leave a finished domain with no
  actuated removal path at all. Tombstone kinds are present-state kinds
  only (`service` in v1, plus `file`/`package` when they land);
  `interlock` and `unit-writer` are present-only, with no device-state
  footprint to tombstone — deleting one is an ordinary remove hunk the
  briefing renders as “guard removed” / “writer declaration dropped.” A
  dropped tombstone is itself a change (“stop enforcing absence”), silent
  in non-comprehensive domains; per-file tombstone count is a residue
  counter to watch beside diff-size (R19). Tombstone GC is a policy note,
  not a v1 feature.
- **Fetched content binds bytes, not names.** Digest fields on fetched
  artifacts (DC-11) are a schema obligation, covered by the accept and
  re-verified immediately before apply. The policy tree / generic bundle
  is code outside the goal file until the schema binds its digest as a
  privileged region; that is an obligation this design takes on, not a
  property it already has.

### 9.9 The schema family, and the gate on it

Three schemas, following the existing contract conventions (`$id`, draft
2020-12, schema/example pairing, negative fixtures, cross-file lint):
`schema/goal-file.schema.json`, `schema/goal-diff.schema.json`,
`schema/approval-record.schema.json`, with `.json` fixtures **in
canonical bytes** (the fixture is itself a canonicalization test). The
goal-diff schema carries no attribution fields, no group fields, and no
privilege flags — all three are derived. Lint gains `.json` example
pairing and a canonicalization-idempotence check.

**§14.2’s gate applies to this family with full force.** That clause
originally named the artifact by its Model A description and has been
restated; its function is unchanged and is what carries over — *the
artifact the executor enforces and the person consents over gets
independent adversarial review before build*. Write the schemas and
fixtures first, then run that review **on the contract, before the
validator is coded**, with a reviewer outside the lineage that wrote the
schemas.

### 9.10 What this does not fix

Model B improves what the person is shown; it does not change who authors
the machinery. These MUST NOT be presented as closed — the residue
register R1–R18 of `e1-adjudication-xhigh-2026-08-15.md` §7 is the
authority:

- Every control is still operator-authored, -delivered, and -evaluated.
  DC-1’s device-local trust root is untouched by this decision and is
  still required.
- **Effects versus declarations** (TC-23) is unsolved at this layer in
  either model; enclosure needs OS confinement and is out of scope.
- **The activation gap:** `--simulate` covers files and packages only.
  The “loaded and running” half of a service change is
  device-unconfirmable. This is a permanent honesty clause on
  device-computed confirmations.
- **Rollback** to a prior signed state fixes the *specification* problem,
  not the *reversibility* problem: a prior state is always well-defined
  as a target and not always achievable as a transition (package
  downgrades, data migrations).
- Per-host diffs hide fleet-level intent, and cross-entry transitions
  (a port moving between services) ride retry-until-stable and can
  transit conflicting intermediate states.

### 9.11 Signing and delivery (D41, D42)

Signing: [TUF](https://theupdateframework.io/) subset sized for one
operator (offline root 2-of-3, targets, snapshot, emergency). High-water
mark on every applying client. This layer authenticates the release; the
goal file, its diff, and the approval record are what authorize a change
to the device.

The 2-of-3 is a **floor**, and it is a parameter, not a runbook. Two
questions under it are open and belong to §14.4: whether a 2-of-3
ceremony held by one operator means anything if all three keys live on
the machine that also compiles and signs, and what the recovery path is
when a genuinely offline root is lost and every `consented` device
becomes unupdatable. DC-20 also asks for every root version to be
retained and served, a written out-of-band runbook, and a
machine-assisted fingerprint compare rather than an eyeball-hex one.
None of those is built.

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

Verifiable layer authorizes. Semantic layer (template-filled from the
goal file and diff fields; free prose must cite those fields, and travels
as DC-3-labelled untrusted text) briefs the advisor; never authorizes.
Under §9.1 the briefing is generated over the **device-computed** diff,
so a briefing produced at release time is a preview, not the object the
accept binds to.

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

A label in inventory does not enforce this. The executor does.

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
- Return path: `accept | reject | withdraw` (DC-5), signed by the
  enrolled key, bound to the baseline and proposed goal-file hashes and
  the device nonce (§9.1). A reject MAY carry the hunks that drove it;
  accept is all-or-nothing (§9.3). Timeout is deny. Advisor down → fail
  closed for *installs* (revocation still applies, §9).
- Custom tools (OpenPGP WoT, a transparency log, a chain, gossip of
  signed apply-attestations) are theirs. Deadlock among “everyone
  waiting for everyone else” is a separate project that consumes
  attestations. tendcf owes: the goal file and its diff (§9), optional
  exportable apply-attestations, the `accept | reject` slot.

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
`operator` only; NAR digests in the manifest (RT-05) — a floor for the
builder/cache when it lands at Step 10+, not a control that exists today.
The live, general form of that requirement is DC-11/§9.8: **every**
fetched artifact binds a digest, covered by the accept and re-verified
before apply.

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
| 6 | Signed releases, push-only; goal-file render + diff + on-device validator (§9). Operator hosts. |
| 7 | Optional Mac substrate (nix-darwin) if §14.1 says yes. |
| 8 | Pull / self-update. |
| 9 | Consent surface + default prompt + advisor slot. |
| 10+ | Demand: builder/cache, APK provenance, WoT-as-advisor-tools, extracting the publishable layer when a second person runs it. |

Dry-run is the standing posture on the first platform (the machine that
cannot easily be reimaged). Reporting is an adoption requirement.

The §9.9 schema family and the §14.2 review of it **MUST** land before the
Step 6 validator is coded. Nothing else gates them — no fleet, no
compiler — so they may be written as soon as someone is free to write
them.

---

## 14. Premium-token residue

Cheap models execute this document everywhere except:

- **§14.1** nix-darwin on the Mac, yes or no (gates Step 7 only).
- **§14.2** The artifact the executor enforces and the person consents
  over. Under D43 that is the §9.9 schema family — goal file, goal diff,
  approval record — not the withdrawn capability vocabulary this clause
  originally named. Do not improvise. Independent adversarial review on
  the contract, before the validator is coded.
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
| D27 | This file | ~~Edit protection via `Approved-change:` trailer.~~ **Reversed 2026-08-15:** every document here is mutable; no approval ceremony. Rationale: pre-mortem N9 / synthesis DC-44 — a trailer gate whose approver is the author makes changing your mind expensive, which is wrong for a design carrying open questions. |
| D28 | Guardrail weight | Existence checks for the large IaC error class; extra entries for omission; schema for the tiny syntax class. |
| D29 | Semantic layer | Template-fill from the goal file and diff fields; free prose cites those fields and travels as DC-3-labelled untrusted text. Briefs; never authorizes. |
| D30 | `.cf` escape hatch | Prefer a grammar before lint-only, when that surface is exercised. Re-scoped by D43: goal-file coverage is closed by construction, so the *escape-hatch pressure* the capability vocabulary created is gone; what remains is the policy tree as code outside the goal file until the schema binds its digest as a privileged region (§9.8). |
| D31 | Front or back | Critical fields at start or end of agent-facing artifacts. |
| D32 | Compiler prior art | Mechanism common; Site Model → CFEngine is the pairing, not a novel compiler mechanism. |
| D33 | No control node | Promise Theory’s; GitOps is the closest shape. |
| D34 | Repo layers | tendcf / site-shared / site-private / foreign / optional tool forks. Conflict-as-error; private binds. |
| D35 | Inventory | Private by default; kinds, templates, explicit exports may be shared. |
| D36 | Supervisors | Generic; launchd is one adapter. See §6. |
| D37 | Peer actions | Typed cross-machine help; local stall; no distributed lock; FSM is a view. |
| D38 | Trust | Per-device policy, several axes. Full mesh is a site choice. Executor enforces. |
| D39 | Advisor | Their AI, their key, our slot. Default prompt replaceable. |
| D41 | TUF bootstrap | Ceremony + fingerprint; not TOFU on consented devices. |
| D42 | Emergency | Restrictive metadata without consent; new installs still gated. |
| D43 | ChangePlan model | ~~Model A: a closed `capability` vocabulary per operation, executor refuses effects outside the declared set.~~ **Superseded 2026-08-15 by Model B** (synthesis finding E1, adjudicated in `e1-adjudication-xhigh-2026-08-15.md`, which is final and supersedes `e1-adjudication-2026-08-15.md`): the wire artifact is the complete canonical per-host **goal file**; the ChangePlan is the **diff** against the device’s approved baseline; the executor is a **validator** over that diff, not an interpreter. Rationale: CFEngine has no runtime capability confinement, so Model A’s executor requires an interpreter plus a vocabulary-to-policy correspondence proof that does not exist and is not in budget; and coverage closes by construction when compiler and validator share one schema. The vocabulary, its versioning, and its skew policy are dropped. See §9. |
| D44 | Goal-file schema family | The consent artifact is three paired schemas (goal file, goal diff, approval record) with canonical-byte fixtures. Binding sub-decisions, all from E1 §5 and normative in §9: diff computed **device-side**, full file on the wire, compiler diff is preview (§9.1 / E1 §5.1); RFC 8785 canonical JSON, no defaults, no empty collections, refuse-never-normalize, entry-granular structural hunks (§9.2 / E1 §5.2); accept is all-or-nothing, refusal annotated, no dependency groups (§9.3 / E1 §5.3); first adoption and schema migration are bounded **baseline ceremonies**, migration must diff to empty (§9.4 / E1 §5.4); hunk attribution is **excluded from the format** — impossible device-side — and replaced by an `explain-hunk` query (§9.5 / E1 §5.5); `schema_version` fails closed on unknown kinds, strandedness prevented at the compiler, two-phase bumps (§9.6 / E1 §5.6); per-domain coverage travels **in** the goal file (§9.7 / E1 §5.7). §14.2’s pre-build review applies to this family. |

Silence = proceed from Step 0. Objections amend this register.

---

## 16. Open questions (remaining)

Compressed from guide §19, in its order and numbering; the guide’s text
governs. It ran to nine while §9 was Model A; D43 dissolved question 8
**as posed** and added seven more, drawn from the residue register of
`e1-adjudication-xhigh-2026-08-15.md` §7. None of those seven is closed
by D43 — they are what Model B carries, and stating them as resolved
would misrepresent the adjudication.

1. Is inference justified, or is retry-until-stable already the local
   answer? (E1 endorses the inference *cut* as severable — the fields
   stay, D43 does not depend on the cut, and DC-41’s experiment can
   revive the engine. The question itself is still open.)
2. Is the writing rule an argument or a hypothesis?
3. Do `not-yet-migrated` counts get ground down without a dedicated role?
4. Is per-domain the right granularity for comprehensiveness?
5. Is local-first the wrong call? Network-wide reports are what bought
   administrator trust in the Bcfg2 deployment.
6. When a global yes/no arrives, is querying reachable devices and
   treating the rest as unknown enough?
7. Does edge origin information actually turn “why is this waiting?”
   into a query?
8. ~~Does the ChangePlan capability list survive real operations without
   an escape hatch?~~ **Re-posed 2026-08-15 by D43:** does the *goal-file
   schema* keep up with real operations? There is no capability list, and
   coverage closes by construction — compiler and validator share one
   schema and fail together — so the escape-hatch pressure relocates to
   declaring a domain `not-yet-migrated` to get a change out. That is
   question 3 wearing a different hat.
9. If the real AI failure mode is plausible-looking output that types
   do not catch, are we hardening the wrong surface?
10. Is a diff something a person can actually consent to? Everything that
    makes a large diff holdable (`explain-hunk`, display grouping, the
    briefing) is advisory machinery that never widens what the validator
    accepts — which is what keeps it safe and what makes it the first
    thing dropped under pressure. Countable once real diffs exist.
11. Do the total-diff events stay rare? Count migration releases per year;
    a project with high schema churn hands its reviewer a recurring
    “everything moved, this one is fine” event (§9.4).
12. Does refusing actually cost the proposer anything? Nothing stops the
    same bundle being re-offered; the answer is that persistent re-offers
    are visible in the record (§9.3, TC-19).
13. What protects the stored baseline (§9.1)? Integrity-protected storage
    is platform-specific to build, and Android under Termux is the awkward
    case — the same ownership problem §8 already has.
14. The policy tree is still code arriving outside the reviewed state,
    until the goal file carries its digest as a privileged region (§9.8,
    D30). An obligation on an unwritten schema, not a property.
15. Nothing here changes who authors the machinery (§9.10). Whether a
    device-local trust root the release path cannot write is buildable
    across macOS, Linux, and Android by one person is open, and the rest
    of the consent layer rests on the answer.
16. What confirms that a change took effect? `--simulate` covers files and
    packages; “loaded and running” is device-unconfirmable, permanently at
    this layer (§9.10).

Token discovery is **D40**, not open. Trust-tier-as-label (confusion
with full mesh) is **D38**.

---

## 17. Document map

- `docs/paper/tendcf-architecture-guide.md` — vetted current-state
  description. Wins on conflict about the current design.
- **This file** — implementer map (decisions, build order, protection).
  Must agree with the guide.
- `README.md` — pointer.
- `deprecated/` — v1/v2 and panel drafts. Do not update them.
- `e1-adjudication-xhigh-2026-08-15.md` — the binding adjudication of
  E1 (Model B) and of the schema-family decisions recorded as D43/D44.
  Final; supersedes `e1-adjudication-2026-08-15.md`, which is kept for
  delta context only. Its §7 residue register is the authority on what
  Model B does **not** fix.
- `cfengine-feasibility-of-diff-plan-2026-08-15.md` — the feasibility
  evidence D43 rests on; its addendum controls over its body.
- Dated `*-2026-08-13.md` research notes in this directory — evidence
  trail; the guide wins on conflict.
- `docs/paper/tendcf-architecture-paper.md` — technical paper; the guide
  wins on conflict.
- `schema/`, `examples/`, `bin/schema_lint.py` — Site Model contract.
- `frdminc/nix2cf` — compiler tool (Step 3). Consumes this contract.

Local prior-art clones (not dependencies): `~/src/config-mgmt-prior-art/`.
