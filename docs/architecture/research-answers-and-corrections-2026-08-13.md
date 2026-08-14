# Research answers, and two corrections

> **Archival (2026-08-13).** Snapshot of research as of that date. Not current design. On conflict, [`../paper/tendcf-architecture-guide.md`](../paper/tendcf-architecture-guide.md) wins. Do not rewrite this file to bring it up to date.

Operator session, 2026-08-13, continuing from
`site-pika-requirement-change-2026-08-13.md`. Answers the four research
items the operator selected (Tier 2 #3, Tier 3 #5/#6/#8) and corrects two
things I got wrong in the preceding docs.

## 0. Correction 1 — CFEngine on Termux is not an open question

I recorded "CFEngine on Termux has never been built" as the single
highest-value unknown, and built a bifurcation risk on top of it. **That
was wrong.** Per the operator, CFEngine has been running on Termux for
weeks. The repository confirms it —
`stayturgid/device/termux/cfengine/` contains:

- a `cfbs` (CFEngine Build System) project, `policy/` as source of truth,
  rendering to `out/masterfiles/`;
- `stayturgid.cf`, a working Tier 3a self-heal policy annotated
  `@heals: SSHD-RUNNING BOOTLOOP-ALIVE NATIVE-AGENT-RUNNING OTELCOL-RUNNING`,
  with `processes:`/`restart_class` promises against real Termux paths
  (`/data/data/com.termux/files/usr`);
- `cf-serverd.cf` and `cf-runagent-wrapper.sh` — i.e. **the push channel
  is already built and in production.**

Release lag is the only real friction (a week or two for new upstream
releases), and self-compiling covers it. Not a constraint.

Two consequences. First, the Tier 1 research item is closed, not open.
Second, I labelled this a "fourth instance" of the withdrawn-objection-
treated-as-proven-negative pattern; that label was misapplied here. D13's
withdrawal of the "no Android CFEngine binaries" objection was not merely
unevidenced-removal — it was **correct and independently validated in
production**. The pattern is real elsewhere; this was not an instance of it.

## 1. Correction 2 — the two-daemon objection is right, and goes further

The operator's point: if config already arrives by git and CFEngine
already converges, running a second persistent daemon just to trigger a
run is unnecessary. Correct — and the reasoning extends past what was
asked.

**Choria's entire justification in the previous doc was platform reach.**
It was the only candidate whose FOSS builds covered Apple Silicon and
ARM64 Linux, and that mattered *because* CFEngine was assumed not to
reach Android. CFEngine does reach Android. The premise is gone, so the
conclusion goes with it.

More concretely, the thing Choria was going to be adopted *to do* already
exists in the repository: `cf-runagent-wrapper.sh`, invoked from the Mac,
is the live push/kick-off channel. D14 already specifies exactly this
shape — git-distributed policy, `cf-serverd` on every client, push via
`cf-runagent`, no dedicated policy host. **It is already built and
working.**

What Choria would still add, honestly weighed:

| Claimed gain | Verdict |
| --- | --- |
| Reach Android/macOS/ARM | **Void** — CFEngine already does |
| Outbound-only NAT traversal (no VPN) | **Redundant** — Tailscale already in the stack |
| Event-driven / real-time vs CFEngine's poll interval | Real but small; the self-heal loop is already the fast path |
| Telemetry spine (Streams/Scout) | Real, but D18 is unresolved and there is no compliance UI to feed since site-pika dropped its GUI requirement |

**Recommendation: drop Choria from the architecture.** Not "adopt as a
trigger" — the trigger already exists. D14 stands as written. Revisit only
if a concrete need appears that `cf-runagent` + Tailscale + git demonstrably
cannot meet; "uniformity" is not such a need when the uniform thing is
already uniform.

This also means the recommended architecture returns to **two** layers,
not three: nix2cf compiles, CFEngine converges and carries. One agent per
node.

## 2. Tier 2 #3 — Choria identity and enrolment without Puppet

Answered for completeness, though §1 makes it non-load-bearing. Recording
it so it is not re-researched if Choria ever comes back.

Choria's v2 security model is **anonymous TLS plus ed25519 keypairs plus
signed JWTs**, with an **Organization Issuer** as root of trust. Puppet is
not required — the docs describe a "complete Configuration Management free
deployment model."

Key structural points:

- The **Organization Issuer can sign Clients and Servers directly.** The
  Choria Provisioner and AAA Service are *delegated, optional* authorities
  for low-touch auto-enrolment; without them the Issuer signs directly and
  the network still works.
- The Issuer **can be kept offline**, which is a good property — it maps
  onto the TUF-subset thinking in §7.2 rather than fighting it.
- The **`file` security provider explicitly does not support enrolling** —
  it is for placing credentials by other means at arbitrary paths. So
  "just drop files on the node" is supported, but you own enrolment.

Net: it would *not* have been a bad fit for the trust layer — an offline
issuer signing ed25519 identities is close to what §7.2 wants anyway. It
simply is not needed.

## 3. Tier 3 #5 — `flake.lock` vs `ops-release.json` (D19's open question)

**Answer: they are parallel, not alternatives. D19's open question
resolves to "keep both."**

The live `ops-release.json` in all three repos is three fields:

```json
{ "schema": 1, "suite": "djbclark-ops", "version": "1.3.20" }
```

That is a **suite-coherence marker**: it asserts "this repo is at
coordinated release 1.3.20 of the `djbclark-ops` suite," and the release
tooling checks all three match. `flake.lock` answers a completely
different question: "exactly which revision of each flake *input* did this
build resolve to."

They cannot substitute for each other:

- `flake.lock` **cannot express suite coherence** across three co-equal
  repos. To make it try, one repo's flake would have to become the root
  and the other two its inputs — turning a flat suite of three peers
  released together into a dependency tree. That is a much larger
  architectural change than D19 contemplates, and it breaks the release
  model in `OPS-RELEASES.md`, where all three carry the same tag.
- Worse, the current relationship is **mutually referential** (D19 already
  has `fleetopia`'s flake as a shared library the others import, while the
  suite as a whole releases together). Flake inputs form a DAG; **circular
  inputs are not expressible**, so a lock file structurally cannot encode
  a peer relationship.
- `ops-release.json` conversely says nothing about *what a build consumed*
  and never could.

**Recommendation:** `flake.lock` pins build inputs, `ops-release.json`
pins suite coordination, and the release check gains one line — verify the
`flake.lock` files are committed and unmodified at tag time, the same way
it already verifies version equality. This unblocks Step 0 touching
release tooling.

## 4. Tier 3 #6 — how `mgmt` AutoEdges actually works

The mechanism is a **two-sided declaration matched by the engine**, not a
hardcoded per-type dependency table. Each resource implements:

```go
UIDs() []engine.ResUID
AutoEdges(ctx context.Context) (engine.AutoEdge, error)
```

- `UIDs()` returns identifiers that "represent the particular resource
  uniquely" — effectively *what this resource provides or is*.
- `AutoEdges()` returns a matcher used "to match other resources that
  might be relevant dependencies" — *what this resource would depend on if
  present*.

The engine compares `ResUID` values across all resources at graph-
construction time and inserts edges where a provider matches a dependant.
Package resources supply file-path UIDs derived from the package manifest,
which is how "file X is managed by package Y, so order Y before X" is
inferred without anyone declaring it.

**Why this is the right shape for nix2cf.** The valuable property is that
inference is a **per-type interface** rather than compiler-side special-
casing: each typed resource in the Site Model would declare its provides-
identifiers and its match-patterns, and the compiler builds edges
generically. That keeps D12's typed model as the single place knowledge
lives, and it means adding a new resource type does not require touching
the ordering logic. Also worth copying: the per-resource `autoedge =>
false` escape hatch, which exists for a real reason (packages that
auto-start a service before its config file is written).

## 5. Tier 3 #8 — has the D15 Augments path been prototyped?

**No. There is no `def.json`, no `host_specific.json`, and no Augments
usage anywhere in the estate.** D15 is entirely unexercised.

What exists instead is a *different* compile pipeline, already working:

- `cfbs.json` declares a `policy-set` with a single local build step
  (`copy ./ ./`), no remote CFBS modules — deliberately, per the README.
- `just cfbs-validate` / `just cfbs-build` render `policy/` →
  `out/masterfiles/`.
- Deployment is by the **Ansible `termux_userland` role**.

Three findings fall out of that, and the third is the important one:

1. **There is a live Ansible dependency inside the CFEngine deploy path.**
   D13 removes Ansible entirely; that removal must therefore replace this
   role, not just the service-management roles. Worth confirming this is
   on the D13 work list — it is the kind of thing that gets missed because
   it sits *underneath* CFEngine rather than beside it.
2. **`cf-serverd.cf` is simultaneously valid CFEngine policy and an
   Ansible Jinja2 template** — its `allowusers` entry is a `{{ ... }}`
   expression rendered from inventory so the public repo carries no
   operator username. That dual-purpose hack is exactly the kind of thing
   nix2cf exists to replace with a typed parameter, and it is a good,
   small, concrete first compile target.
3. **The deployment deliberately does not use the Masterfiles Policy
   Framework.** Termux runs `cf-agent -f` and `cf-serverd -f` against
   explicit entry points, with no hub. Augments/`def.json` is a
   core CFEngine feature rather than strictly an MPF one, but it is
   conventionally loaded relative to a `promises.cf` entry point and is
   overwhelmingly exercised through MPF. **Before committing to D15,
   verify that an augments file actually loads under a standalone
   `cf-agent -f <file>` invocation** — that is a ten-minute test, and D15's
   whole premise ("compile to Augments, not raw `.cf` synthesis") depends
   on the answer.

That test now displaces the closed CFEngine-on-Termux item as the cheapest
high-value unknown in the queue.

## 6. Revised picture

**Architecture (two layers, one agent per node):**

1. **nix2cf** — typed Site Model in the Nix module system → schema-
   validated JSON → per-platform artifacts. First concrete target: the
   `cf-serverd.cf` dual-template hack (§5.2).
2. **CFEngine** — converges *and* carries. git-distributed policy,
   `cf-serverd` per client, `cf-runagent` push. D14 as written, already
   built.

Choria: dropped (§1). Rudder: dropped (site-pika change). Bolt: dropped.

**Open items, reordered:**

| | Item | Status |
| --- | --- | --- |
| 1 | Does an augments file load under standalone `cf-agent -f`? | **New Tier 1** — D15 depends on it |
| 2 | Real cold-device provision from factory reset | Tier 1, unchanged; D16 hangs on it |
| 3 | Does D13's Ansible removal cover the `termux_userland` deploy role? | **New** — confirm scope |
| 4 | D18 has no surviving stated rationale | Re-decide, do not annotate |
| 5 | D16 composition-only question | Gate: operator conversation |
| ~~6~~ | ~~CFEngine on Termux~~ | **Closed — works, in production** |
| ~~7~~ | ~~Choria enrolment / Streams sizing~~ | **Closed — Choria dropped** |
| ~~8~~ | ~~`flake.lock` vs `ops-release.json`~~ | **Answered — keep both (§3)** |
| ~~9~~ | ~~How AutoEdges works~~ | **Answered (§4)** |

Amends no decision. The register is still untouched pending the D16
conversation, but D19's open question now has a recommended answer (§3)
and D15 has a new precondition (§5.3).
