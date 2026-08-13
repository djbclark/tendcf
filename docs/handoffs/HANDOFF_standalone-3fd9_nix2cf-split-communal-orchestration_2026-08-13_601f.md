---
schema_version: 1
handoff_id: 601f
parent_handoff_ids: [05f4]
lineage: deterministic
chain: [standalone-3fd9]
repo: fleetopia
workspace: N/A (plain repo checkout, not an ops-worktrees task workspace)
branch: master
head_sha: 08b7098cf0c1c50b8219c49d74e3309f1927205b
created_at: 2026-08-13T09:56:36-0400
writer: claude-code
---

# Handoff — nix2cf split, cold-device ordering audit, and the communal-management pivot

## The Goal

Resumed chain `standalone-3fd9` via `/baton` from parent handoff `05f4`, which
left three deferred items. All three are done. But the session ended somewhere
the parent could not have anticipated: the operator disclosed that **site-pika**
(his old fraternity house, likely **communally managed by the house**) is coming
soon, which makes multi-author contribution a real near-term requirement rather
than a hypothetical. That reopens the decision this session had just closed.

Three phases, in order:

1. **Close out `05f4`'s deferred items** — push the unpushed commit, fix the
   D-number cross-reference drift, run the `fleet/fleet.yml` Android-chain audit
   that gated D16.
2. **Resolve naming and project structure** — `fleetopia` → `nix2cf` for the
   compiler layer, with the Android/device modules split out separately.
3. **Research whether communal multi-author management changes the
   CFEngine-vs-Puppet decision** — including the Puppet and CFEngine
   site-level orchestrator landscape.

## Where We Are

- **Repo:** `djbclark/fleetopia`, local checkout `~/src/fleetopia`, `master`,
  HEAD `08b7098`, **clean, pushed to origin**. (Parent handoff left `a4f8582`
  unpushed; that is now pushed along with this session's `08b7098`.)
- **Architecture doc** (`docs/architecture/architecture-DEFINITIVE-v2.md`):
  D-number drift fixed, D16 resolved, D20 added. Details under Key Decisions.
- **D16's resolution is already provisional again.** It was recorded as
  "Puppet-catalog rejected pending confirmation by a real from-scratch
  provision." The site-pika disclosure arrived *after* that was committed and
  changes the premise — see "Where We're Going" item 2.
- **Three stayturgid issues filed:** `#288`, `#289`, `#290` (see Evidence).
- **Git signing permanently fixed** — `~/.local/bin/git-ssh-sign` wrapper +
  `gpg.ssh.program`. Commits now sign with no per-command workaround.
- **1Password is still wedged** and needs an operator-side restart. Signing no
  longer depends on it; interactive `ssh`/`rsync` through the agent still do.
- **Naming/structure decided but not yet implemented** — no repo has been
  created or renamed, no code moved. The split exists only as a decision.

## What We Tried

Chronological. The failures here are the expensive part — several were
corrected by the operator, and two of my own hypotheses tested false.

### 1. First `fleet.yml` audit — methodologically invalid, redone

The first pass read the current playbooks and concluded the six-role chain was
order-independent because every apparent prerequisite resolved to an earlier
`site.yml` playbook. **The operator rejected this**: *"I would not trust
stayturgid re ordering, we have never tried adding a new device from scratch.
Let's look at what it does, not how it currently does it."*

He was right, and the reason generalizes: **convergent automation destroys the
evidence of its own ordering constraints.** Anything that fails on run 1 and
succeeds on run 2 leaves no trace in the code. Every device in the fleet is
warm, so the code encodes the *warm* precondition set, which is nearly empty by
construction. Reading it answers "what works on provisioned devices," never
"what a cold device requires."

The audit was redone semantically — deriving what the operations *require* from
what they *do*. That second pass found three real cold-device gaps the first
pass structurally could not have found (`#288`/`#289`/`#290`).

**Carry this forward:** any future "is this ordering real?" question about
stayturgid must be answered from operation semantics, not from playbook order,
until a from-scratch provision has actually been run.

### 2. Git-signing diagnosis — my hypothesis was wrong, caught by testing

Observed that `user.signingkey` pointed at `git_signing_key.pub` and
hypothesized that with `gpg.format=ssh`, a *public* key tells `ssh-keygen -Y
sign` to delegate to the agent — so pointing at the private key would fix it.

**Tested it; false.** The private-key path hangs identically:

| test | `SSH_AUTH_SOCK` | key arg | exit |
|---|---|---|---|
| A | set | `git_signing_key.pub` | 124 (hang) |
| B | set | `git_signing_key` | **124 (hang)** |
| C | unset | `git_signing_key.pub` | 0 |
| D | unset | `git_signing_key` | 0 |

`ssh-keygen` consults the agent whenever `SSH_AUTH_SOCK` is set, **regardless of
which key form you name**. Unsetting the socket is the only lever. Had I
"fixed" it on the hypothesis without testing, the config would have looked
correct and still hung.

### 3. Graceful quit of 1Password — failed, app wedged deeper than expected

`osascript -e 'quit app "1Password"'` returned `AppleEvent timed out (-1712)`
and the process survived. `ps` then showed the real story: elapsed
**10 days 19:23:50**, still carrying `--silent --just-updated --should-restart`.
The app has been in post-update limbo for over ten days and answers neither the
agent socket nor AppleEvents. This is why the signing hang recurred across
multiple sessions and why `05f4`'s "a 1Password restart was suggested" never
resolved anything.

Did **not** escalate to `kill` — the operator had authorized "the app restart,"
and SIGKILLing a wedged password manager is a materially different action. Left
to the operator, who stated he wants to do GUI things himself.

### 4. Naming candidates rejected

- **`nixcf`** — rejected on collision. GitHub search: **275 repos match
  `nixcf`**, and the top hits (`colemickens/nixcfg` 488★, `MatthewCroughan/nixcfg`
  331★, `alyraffauf/nixcfg` 227★) are all personal NixOS dotfiles. One letter
  from `nixcfg`, the most generic name in the Nix ecosystem — permanent
  misidentification, unfixable by any amount of README.
- **`nix2json`** — the operator correctly noted both CFEngine Augments and
  Puppet catalogs consume JSON. Rejected anyway: Nix already emits JSON
  natively (`nix eval --json`, `builtins.toJSON`), so the name describes a
  built-in flag and invites "trivial wrapper." It names the serialization and
  hides the compiler — the value is the *schema* and D15's merge semantics.
- **"`cf` reads as generic configuration"** — checked; it does not. The generic
  abbreviations are `cfg`/`conf`; CFEngine's own file extension is literally
  `.cf` and its binaries are `cf-agent`/`cf-serverd`/`cf-promises`. Competing
  readings are Cloudflare and Cloud Foundry (whose CLI command is `cf`), not
  "configuration."

### 5. Two constraints I weighted that the operator overruled

Both were treated as blockers in my analysis and both were wrong. **This is the
second and third instance of the same pattern already recorded in
`project_cfengine_blockers_corrected` — an analyst's inferred constraint
mistaken for an operator constraint. Check before weighting.**

- **Rudder's PostgreSQL backend.** I carried forward D18's "no SQLite path
  exists" as a reason to reject Rudder. Operator: *"Postgres is fine I just
  have a general preference for sqlite. So don't let that effect anything."*
  **D18's stated rationale is therefore partly invalid and needs re-examining**
  — not merely annotating.
- **OpenVox fork risk.** I weighted "young volunteer-maintained fork" against
  adopting it. Operator: *"I am fine with using a young open source fork."*
  What he *does* rule out: *"we should def not use anything that arbitrarily
  limits nodes, etc. as IoT stuff may be added later"* — which disqualifies
  Perforce-Puppet (25-node commercial threshold) but explicitly not OpenVox.

## Key Decisions

### Naming and project structure

- **`nix2cf`** is the name for the Nix→CFEngine compiler layer. Chosen over
  `nixcf` (collision), `nix2json` (names the serialization), and keeping
  `fleetopia`. Rationale: the `X2Y` form names the *direction* — this is a
  transform, and encoding the arrow is free precision. It also lands inside the
  Nix ecosystem's own idiom (`node2nix`, `cabal2nix`, `poetry2nix`,
  `crate2nix`, `gomod2nix`, `dream2nix`) while deliberately running the
  unusual direction: everything else compiles *into* Nix, this compiles *out*.
  Verified free: **0 GitHub matches**, `github.com/djbclark/nix2cf` → 404.
- **The project splits in two**: `nix2cf` = the generic compiler layer;
  Android/device modules stay separate under a fleet-domain name (they are the
  real successor to stayturgid 2.0 and need no new name). Rationale: D19
  already made fleetopia's flake "the shared module-system library the other
  three repos import" — the split makes that dependency direction enforceable
  rather than conventional, and the audiences differ (a Nix→CFEngine compiler
  is useful to strangers; Termux/Shizuku modules are useful to one person).
- **Interim implementation: do NOT split the repo yet.** Keep one repo with a
  hard internal directory boundary plus a lint that fails if the compiler side
  imports anything fleet-specific; split when the interface stops churning.
  Rationale: the abstraction is currently n=1, and splitting before the
  interface stabilizes puts the boundary in the wrong place. Also, a repo split
  adds a cross-repo version boundary and `fleetopia#2` explicitly demands a
  *faster, more atomic* change process — the split is only cheap if D19
  resolves in favor of `flake.lock` being authoritative.
- **Open boundary question, not yet recorded in the doc:** Site Model
  *schemas* (`services.yml`/`roles.yml`/`launchd-writers.yml` per §12) belong
  in `nix2cf` as its contract; *instances* belong in the fleet repo. This is
  the call that actually defines the split.

### D16 — Puppet-catalog rejected (and already reopened)

Recorded in the doc as **rejected pending confirmation by a real from-scratch
provision** — deliberately not closed outright. Rejected alternative: build the
Puppet-catalog-JSON compiler.

Grounds: the real cold-device constraints sort into three kinds and none is
shaped like a resource DAG — (a) a strictly sequential six-node transport
bootstrap, which is a `bundlesequence`; (b) independent non-interleaving
per-app chains, expressible with CFEngine classes/`depends_on`; (c) safety
interlocks, which are guards a catalog cannot express at all.

**This is now provisional again.** The site-pika disclosure means multi-author
contribution is real, and autorequire — Puppet's one genuinely unique property
— goes from worthless to load-bearing. See "Where We're Going."

### D-number drift — sections renumbered to match the register

Direction chosen: renumber inline section headers to match the §15 register
(rejected: renumbering the register to match sections). Rationale: register
rows are what external notes and issues cite.

Applied: §4.4 → `(D13/D14/D15)`, §4.5 → `D16`, §4.6 → `D17`, §4.7 → `D18`,
§4.8 → `D20`; §4.8's internal "behind D17's local SQLite" → `D18's`;
bibliography range `D13–D19` → `D13–D20`. **D20 is new** — Nix store locality
had no register row at all, existing only as an aside inside D19; promoted to
its own row.

### Other decisions

- **`dpm set-device-owner` is permanently excluded** as a Tailscale-auth
  delivery path. Operator: *"that is a hard decision. Setting it is disruptive
  and prevents use of Island/Inland."* It consumes the device-owner slot
  Island/Insular needs. Issue `#289` was edited mid-session to record this.
- **Nothing that arbitrarily limits nodes** may be adopted (IoT growth
  expected). Disqualifies Perforce-Puppet at 25 nodes; does not disqualify
  OpenVox.
- **Git signing goes through a wrapper, not the agent** — permanent, and
  deliberately scoped to signing only so 1Password still serves interactive SSH.

## Evidence & Data

**Tests run: one.** A real signed commit in a scratch repo with the agent
socket still set and no `env` override → `Good "git" signature for
djbclark@gmail.com with ED25519 key SHA256:NOf/qpfDPyYOKOSto9KMSe6KhH7EfiKssVf6ltppa+A`.
No other suites exist — fleetopia is documentation-only, Step 0 has not started.

### The `fleet.yml` audit (the D16 gate)

Six roles: `termux_userland → shizuku_config → tailscale_vpn → play_store →
app_privileges → ensure_apps`.

- **Zero `dependencies:` in all six `meta/main.yml`.** Only `collections:`,
  which is namespace resolution, not ordering. Matches the earlier 14/15 result.
- **Five of six are `delegate_to: localhost`** control-node adb operations;
  only `termux_userland` executes on-device over SSH. No shared execution
  context to couple through.
- **`site.yml` is the real sequencer** — nine stages:
  `ensure-bootstrap-apks → verify-bootstrap-apks → ensure-shizuku → preflight
  → bootstrap → fleet.yml → post-ui → validate → control_node`.
- Every apparent intra-chain prerequisite resolves upstream of `fleet.yml`:

| looks like it needs | actually satisfied by |
|---|---|
| `rish.py install` → Shizuku APK (`pm path moe.shizuku.privileged.api`) | `bootstrap_apks`, stage 1 |
| `termux_userland` appops via `localhost:5555` | `ensure-shizuku`, stage 3 — `shizuku_start` "verifies the daemon is running and port 5555 is reachable" |
| `tailscale_vpn` comment "Prerequisite: `com.tailscale.ipn` installed" | `bootstrap_apks`, stage 1 |
| `app_privileges` comment "after packages are installed" | `bootstrap_apks`, stage 1 — **not** `ensure_apps` |

- `bootstrap_apks` installs 7 APKs: `org.stayturgid.agent`, `com.termux`,
  `com.termux.boot`, `com.termux.api`, `com.termux.x11`,
  `moe.shizuku.privileged.api`, `com.tailscale.ipn`.
- **Zero references to Tailscale authentication** anywhere in the repo — no
  authkey, no `tailscale up`, no login path. Grepped `ansible/`,
  `ansible_collections/`, `control/`, `docs/`.
- Defaults: `stayturgid_always_on_vpn: true`, `stayturgid_always_on_vpn_lockdown:
  false`. The safe default is the only thing preventing a severed device.

### Issues filed

- **[stayturgid#288](https://github.com/djbclark/stayturgid/issues/288)** —
  `ensure_apps` (pos 6) installs apps *after* `app_privileges` (pos 5) hardens
  them; new apps go unhardened for a full deploy cycle. `play_store` (4) →
  `app_privileges` (5) is correctly ordered, so **the chain contradicts its own
  only real rule** — strong evidence the order is accreted, not designed.
  One-line reorder fix.
- **[stayturgid#289](https://github.com/djbclark/stayturgid/issues/289)** —
  `always_on_vpn_lockdown` has no auth-state interlock. Setting it true on an
  unauthenticated device severs ADB-over-TCP, Termux SSH, and every other
  management path; recovery is physical. Edited mid-session to record the
  `set-device-owner` exclusion. Remaining candidate paths: Shizuku-injected app
  restrictions (unproven), or a documented one-time manual login.
- **[stayturgid#290](https://github.com/djbclark/stayturgid/issues/290)** —
  Termux unpacks `$PREFIX` on **first launch**, not at install; `pkg`/`run-as`
  are unusable until then. On a cold device that is the default state.
  `preflight.yml` handles it only as a best-effort *heal* for killed-Termux,
  never as a declared precondition.

### Git signing

Current global config: `user.signingkey=/Users/djbclark/.ssh/git_signing_key.pub`,
`gpg.format=ssh`, `commit.gpgsign=true`,
`gpg.ssh.allowedsignersfile=~/.ssh/allowed_signers`, and now
`gpg.ssh.program=/Users/djbclark/.local/bin/git-ssh-sign`.

The wrapper is three lines of substance: `exec env -u SSH_AUTH_SOCK ssh-keygen
"$@"`, with a comment block explaining why. Private key is unencrypted, so no
prompt. 1Password process: PID 5944, `STAT S`, elapsed `10-19:23:50`, args
`--silent --just-updated --should-restart`.

### Orchestrator research (2026-08-13, citation-backed)

- **Puppet went closed.** Perforce moved binaries/packages to a private
  location Nov 2024; **usage beyond 25 nodes requires a commercial license**.
  Vox Pupuli forked the Apache-2.0 code as **OpenVox** (Jan 2025), a "soft
  fork" drop-in replacement; `OpenVoxProject/openbolt` mirrors Bolt.
  → https://www.infoworld.com/article/3809889/puppet-open-source-fork-openvox-arrives.html
  → https://voxpupuli.org/blog/2025/05/19/perforce-eula/
  → https://voxpupuli.org/openvox/
- **Bolt** (`puppetlabs/bolt`, Apache-2.0) — agentless, SSH/WinRM, plans in
  YAML or Puppet language, reuses Forge modules. Agentless-over-SSH fits
  Termux. → https://github.com/puppetlabs/bolt
- **Choria** — MCollective successor; **`mcollectived` is no longer supported
  in any version**. Go, NATS-based, "known to support 50 000 nodes on a single
  compute node," production-ready in ~30 minutes.
  → https://choria.io/docs/about/
- **CFEngine `cf-runagent` — the decisive limitation, quoted:** it *"cannot be
  used to tell cf-agent what to do, it can only ask cf-serverd on the remote
  host to run the cf-agent with its existing policy."* That is **triggering,
  not orchestration** — no cross-host sequencing exists.
  → https://docs.cfengine.com/docs/3.20/reference-components-cf-runagent.html
- **CFEngine RBAC** exists in `cf-serverd`, defined in policy code — but it
  governs who may *trigger and query*, not who may *author* policy. Does not
  address communal contribution.
  → https://docs.cfengine.com/docs/archive/manuals/st-rbac.html
- **Tailscale Android** supports an **`AuthKey` system policy** via managed
  configuration — the client uses it automatically on launch unless already
  logged in. Normally requires a DPC (device-owner/profile-owner), which is
  unavailable here since `set-device-owner` is excluded.
  → https://tailscale.com/docs/integrations/mdm/android
- **NixOS trademark** is registered; a proposed Foundation policy says
  commercial projects should not use "Nix"/"NixOS" in their names. CFEngine is
  a registered trademark of Northern.tech. Relevant only if the compiler layer
  ever needs to be trademarkable — the split makes this the piece where it
  matters least. → https://discourse.nixos.org/t/announcing-nixos-trademark/78585

**Structural gap found:** neither ecosystem has a declarative *site-level*
orchestrator. Puppet's catalog is per-host; Bolt and Choria are imperative
overlays. CFEngine has triggering only. Cross-host ordering ("upgrade the
router before the APs") is unserved by both and belongs in the ChangePlan layer.

## Operator Feedback

- **Don't trust stayturgid on ordering** — *"we have never tried adding a new
  device from scratch. Let's look at what it does, not how it currently does
  it."* The single most important correction of the session; it invalidated an
  entire audit pass.
- **Postgres is fine.** *"I just have a general preference for sqlite. So don't
  let that effect anything."* Third recorded instance of a preference being
  mistaken for a hard constraint (see `project_cfengine_blockers_corrected`).
  **Ask before weighting a constraint as load-bearing.**
- **Young open-source forks are acceptable.** What is not: *"we should def not
  use anything that arbitrarily limits nodes, etc. as IoT stuff may be added
  later."*
- **`dpm set-device-owner` is a hard no** — disruptive, blocks Island/Insular.
- **GUI actions belong to the operator** — *"If it is a GUI thing I want to do
  it."* Scripted quit/relaunch was acceptable; escalating to `kill` was not
  assumed.
- **site-pika is coming** — an old fraternity house, *"may be communally
  managed by the house, so that would be a great feature."* This is the pivot
  that reopens D16.
- **Queued explicitly for after this conversation:** separate out the secretspec
  work, clean it up, attempt upstreaming.

## Where We're Going

**1. THE NEXT ACTION — second look at Rudder, Bolt, and Choria, then general
site-level-orchestration research.** Operator's explicit instruction, first
thing. Re-evaluate all three under the *corrected* constraints: Postgres is
fine, young forks are fine, node limits are disqualifying. Specifically:

- **Rudder** — D18 rejected it partly on "no SQLite path exists," which is now
  void. Re-examine its **authoring + RBAC layer** (distinct from its reporting
  DB): letting non-experts define policy through a web UI with real RBAC is
  *exactly* site-pika's shape. GPLv3 still blocks depending on it; D17 already
  treats it as a reference corpus.
- **Bolt** — evaluate its plan model as prior art for ordered operations in the
  §7.3 ChangePlan. Agentless SSH fits Termux.
- **Choria** — evaluate as real-time fleet command-and-control. Check the
  licensing and node-limit posture explicitly against the new hard constraint.
- **Then, more broadly:** site-level orchestration that is **not** based on
  running entire virtual machines. This is the open-ended part of the ask —
  the research so far only covered the Puppet and CFEngine ecosystems.

**2. Then — and only then — discuss how to reopen D16.** Operator: *"After
that additional research we should talk about how to reopen D16."* Do not
edit the register before that conversation. The substantive content for it:

- **Autorequire is a property of a typed resource model, not of Puppet.** D12
  already has the Nix module system authoring a typed Site Model; types are all
  autorequire needs (`file` → parent dir, `service` → package, `user` → group).
  The likely answer is not "adopt Puppet" but **"`nix2cf` grows a
  dependency-inference stage"** — inferring edges, topologically sorting, and
  detecting cycles at `nix eval` time, i.e. in CI on a contributor's PR rather
  than at catalog-compile time on a master.
- **Honest cost:** that makes `nix2cf` a real compiler rather than a thin
  Augments renderer.
- **Autorequire is the smallest of the changes communal management brings.**
  The larger ones are absent from the architecture entirely: *authorization*
  (who may change what — neither ecosystem answers this), *blast radius* (a
  house member must not brick devices or read secrets → §8.3's secretspec
  reference monitor becomes load-bearing), *review artifact* (the ChangePlan
  becomes required, not elegant), and *tenancy* (two sites with different trust
  models; the Site Model assumes one operator).

**3. Treat site-pika as a first-class architecture driver**, not a second site.

**4. Resolve D19** — `flake.lock` vs `ops-release.json`. Blocks Step 0 touching
release tooling *and* determines the cost of the nix2cf/fleet repo split.

**5. Record the Site Model boundary decision** (schemas in nix2cf, instances in
the fleet repo) in the architecture doc — decided this session, not yet written.

**6. Secretspec extraction + upstreaming** (operator-queued, not started). Two
pieces with different odds: the 1Password Service Account provider is a clean
upstream candidate; the `_secretspec` privilege-separation exec wrapper is
opinionated and may fit better as a documented pattern. **Ownership:**
`control/lib/secretspec_exec.py` belongs to orc/secretspec-canon per the
chain-`bfbf` handoff — coordinate, do not just extract. Check first whether its
live regression (wrapper exec'ing all of `ansible-playbook` as `_secretspec`,
whose `/var/empty` home is unwritable) was ever fixed.

**7. Triage stayturgid `#288`/`#289`/`#290`.** `#288` is a one-line fix.

**8. Fold `fleetopia#2`** (faster, more atomic change process) into the
architecture doc — still unaddressed, and the repo split makes it more urgent.

**9. Operator action: restart 1Password.** Wedged 10+ days. Signing no longer
depends on it; interactive `ssh`/`rsync` via the agent still do.

**10. Optional but decisive: run a from-scratch provision on one device.** The
only thing that settles D16's cold-device question, and the correct forcing
function for the transport-bootstrap and interlock designs regardless.

## Quick Start

```bash
cd ~/src/fleetopia
git log --oneline -5          # expect 08b7098 at HEAD, clean, == origin/master

# Item 1 — the research ask. Current state of the three candidates:
#   Rudder  : D17 (reference corpus, GPLv3), D18 (reporting rejected — Postgres
#             rationale now VOID). Re-read both rows before starting:
grep -n "^| D1[678]" docs/architecture/architecture-DEFINITIVE-v2.md
#   Bolt    : https://github.com/puppetlabs/bolt  (Apache-2.0, agentless)
#   Choria  : https://choria.io/docs/about/       (Go/NATS, MCollective successor)
# Hard constraint for all three: nothing that arbitrarily limits node count.

# Item 2 — the D16 conversation. Read the current resolution first:
sed -n '/^### 4.5 /,/^### 4.6 /p' docs/architecture/architecture-DEFINITIVE-v2.md

# The audit this session ran, if you need to re-verify any claim:
cd ~/src/ops-worktrees/stayturgid-2.0/stayturgid
cat ansible/playbooks/site.yml                    # the real 9-stage sequencer
cat ansible/playbooks/fleet/fleet.yml             # the six-role chain
grep -rn "id:" ansible_collections/stayturgid/android_common/roles/bootstrap_apks/defaults/main.yml

# Issues filed this session:
gh issue view 288 --repo djbclark/stayturgid      # ordering inversion (1-line fix)
gh issue view 289 --repo djbclark/stayturgid      # lockdown interlock (set-device-owner EXCLUDED)
gh issue view 290 --repo djbclark/stayturgid      # Termux first-launch precondition

# Git signing is FIXED — no workaround needed. Plain `git commit` signs.
# If it ever hangs again, the wrapper is the thing to check:
cat ~/.local/bin/git-ssh-sign
git config --global gpg.ssh.program

# 1Password is wedged (10+ days, --just-updated --should-restart). Operator
# restarts it. Verify afterwards with:
timeout 5 ssh-add -l     # 124 = still wedged; 0/1 = agent serving again
```
