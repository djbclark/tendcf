# What the Bcfg2 papers offer this architecture (2026-08-13)

> **Archival (2026-08-13).** Snapshot of research as of that date. Not current design. On conflict, [`../paper/tendcf-architecture-guide.md`](../paper/tendcf-architecture-guide.md) wins. Do not rewrite this file to bring it up to date.

Source: `~/src/bcfg2/doc/papers/` — all four read end to end.

- `bcfg-cluster2003.pdf` — Desai, Lusk, Bradshaw, Evard, CLUSTER '03. The
  origin paper; the configuration-language requirements are here.
- `desai_lisa05.pdf` — LISA '05. Deployment case study, technical and
  social; the only cost/effort data in the set.
- `desai_lisa06.pdf` — LISA '06, "Directing Change Using Bcfg2". Time and
  change: revision-stamped configuration, FSM orchestration, change policy.
- `19_bcfg2.pdf` — SAGE Short Topics #19 (2008), the full architecture and
  reference manual.

This supersedes nothing. It extends
`orchestration-research-2026-08-13.md`, which had Bcfg2 only as
"its answer to ordering is to not have one." That is true of the *engine*
and it is the least interesting thing in these papers.

---

## 1. Two-way verification — the strongest transfer, and it lands on D16

Bcfg2's configuration goals are **comprehensive by convention**: the spec
describes every configuration entity on the client, and anything present
on the client but absent from the spec is *unintended by definition*. The
client therefore verifies in both directions — "the client configuration
contains no less than the configuration description specifies, and also
verifies that the client contains no more than specified" (CLUSTER '03
§2.2). Unspecified state is surfaced as **extra entries**, a first-class
reported category alongside bad and modified entries.

The papers are explicit about why this exists, and it is exactly our
problem: *"This capability allows BCFG to be effectively used in larger
administrator groups, as all changes can be detected, even if systems have
become configuration-skewed."*

This matters because it names something the D16 discussion has been
missing. Multi-writer composition has two halves:

1. **Composition** — do two authors' declarations combine into a coherent
   result? (This is the half we have been arguing about.)
2. **Detection** — if a third writer changes something out of band, or one
   author's change silently overlaps another's, does anything notice?

CFEngine's default posture answers (2) with "no": promises are made only
about what you mention, so unmentioned drift is invisible by construction.
Comprehensiveness is the property that makes multi-writer skew *detectable
at all*, and it is a design choice we have not yet made.

The practical form for us is **per-domain comprehensiveness**: declare, for
a bounded domain (the app list on a device, `/etc/ssh`, the `serverapp_*`
launchd plists), that the Site Model's description is complete, and have
the device report anything in that domain it did not expect. Adopt it
domain by domain rather than fleet-wide — which is also how Bcfg2 was
actually deployed (the booklet's first client run reports `Total managed
entries: 0 / Unmanaged entries: 2308`, and the stated goal is to grind that
second number down over time).

**Free side effect: an adoption metric.** The managed/unmanaged ratio per
device is a real, non-hand-wavy progress number for the Step 0→N build
order, and it costs nothing extra once the comprehensiveness machinery is
there.

## 2. The compile/apply split is already ours — and the papers name why it works

Bcfg2's server renders rules into client-specific goals with **all
ambiguity removed** before anything reaches a client; the client does as
little processing as possible; the client's only job is compare, decide,
act, report. The stated reason (booklet §2.2) is that *"central
configuration processing contains complicated processes on the server,
where they can be readily examined and supervised."*

That is precisely the nix2cf → Augments → `cf-agent` seam (D12/D13/D15),
with the one difference that our render happens **ahead of time into a
release artifact** rather than on demand per client request. Two consequences
worth taking:

- **Ambiguity is a compile-time error, not a runtime resolution.** In
  Bcfg2, exactly one plugin may provide content for a given entry; when
  two could, the server *"will refuse to bind entry contents and will
  produce an error message"* (booklet §5.1). It does not pick a winner.
  This is the right default for our conflict rule — see §6(a).
- **`bcfg2-info buildfile` is the affordance we should copy first.** It
  renders exactly the artifact a named client would receive, server-side,
  without touching the client — used in the papers for debugging templates
  and, via `buildall`, for regression-testing server upgrades. For a pure
  compiler like nix2cf this is nearly free, and §5 below explains why it is
  disproportionately valuable.

## 3. Revision-stamped everything (LISA '06) — cheap, and it fits our release train

The LISA '06 change is small and mechanical: the server integrates with the
revision-controlled repository, **stamps every generated client
configuration with the repository revision**, keeps a revision log of what
was served when, and **carries that revision into every client statistics
upload**. Consequences the paper claims, all of which we want:

- The desired configuration state of any client *at any past time* becomes
  reconstructible.
- Client reports become correlatable with changes: "users report failures
  after a batch of changes" becomes a query, not an argument.
- Security: which hosts were vulnerable, over what window, and when they
  were actually patched.

We already have the identifier this needs — the `ops-vMAJOR.MINOR.PATCH`
release tag and `ops-release.json`. **Recommendation: every row in D18's
per-device SQLite carries the release version that produced the artifact,
and the device records which release it is currently converged to.** This
is a schema decision, so it is cheapest to make before the schema exists.

The paper generalizes its own result to any declarative tool, and lists the
two required modifications: tight revision-control integration, and
revision information inside collected statistics. We get the first for free
and the second is one column.

## 4. Actions: a real precedent for interlocks (stayturgid#289)

§4.5 of the architecture argued that interlocks — the
`always_on_vpn_lockdown`-severs-management-channel class of constraint —
"are not dependencies at all" and that a catalog cannot express them. The
papers show a shipped mechanism for exactly this shape.

Bcfg2 **Actions** are commands bound to a Bundle with `timing`
(`pre`/`post`/`both`), `when` (`always`/`modified`), and `status`
(`ignore`/`check`). The load-bearing sentence (booklet §A.2.1): *"Actions
can also be used as a prerequisite to installation of entries in a Bundle.
Unless exit status is ignored, a failing pre-action will prevent
modification of entries in the enclosing Bundle."*

That is a guard with a blast radius — not an edge in a dependency graph,
and not a bare `if`. It says: *this check runs first; if it fails, nothing
in this unit is touched, and the failure is reported centrally.* Mapped to
our stack, an interlock becomes a first-class Site Model field that
compiles to a CFEngine guard class plus a bundle-scoped refusal, so
"Tailscale must be authenticated before lockdown may be enforced" is
expressed once in the model rather than surviving as a safe default and a
comment. This makes the §4.5 claim more precise: a *catalog* cannot express
it, but a promise engine with a first-class precondition can, and there is
prior art for the schema.

## 5. Trust is the adoption gate, and information is what buys it (LISA '05)

The case study's central finding is not technical. Deployment took ~4
months of one person's time (90% in six weeks, the long tail in ten), and
the binding constraint throughout was **administrator trust**, not tool
correctness. The pivot they describe:

> *"Our change in focus amounted to the realization that the tool
> client-side functionality was not sufficient. The tool must also provide
> enough information for administrators to make effective decisions as
> conveniently as possible. … From this point onward, nearly all
> development focused on an information presentation system."*

And on how trust is actually earned: *"This process can be accelerated,
however, through the exposure of tool decision information. If
administrators can easily examine the decision process each time they run
the tool, then their trust will grow more rapidly."*

Three operational practices fall out of this that are directly applicable
to **site-pika's three root-trusted admins**, who are precisely the
"larger administrator group" this paper is about:

- **Dry-run is the default posture on machines that matter.** Their
  production servers ran Bcfg2 in dry-run nightly and mailed the resulting
  state to the responsible administrator; only workstations auto-applied.
  This maps cleanly onto the ChangePlan/consent design in §7.3 and is a
  sane initial default for site-pika.
- **Reporting deployed early, not last.** Their explicit deployment tip.
  We currently have D18 as the record and no consumer; this reframes the
  local SQLite plus a trivial "what changed, what is dirty" view as an
  *adoption* requirement rather than an observability nicety.
- **Visualize the group/profile graph.** `bcfg2-admin viz` renders the
  group DAG; the booklet calls the diagrams *"invaluable"* for training new
  personnel and for working in unfamiliar areas. Our Site Model module
  system has the same structure and can render the same picture.

The efficiency figure, for calibration only: roughly three FTE of
workstation/server maintenance before, between one-third and one-half of an
FTE after, across a division of ~200 people and several hundred machines.

## 6. What the operator actually has to decide for D16

The papers do not close D16, but they sharpen it into four separable
decisions. Only (a) and (d) are genuinely load-bearing for a multi-writer
site; (b) and (c) can be deferred without blocking Step 0.

**(a) Same-resource conflict rule.** When two writers declare the same
resource, is the result an error, or a resolution? Bcfg2 errors (one
provider per entry, refuses to bind, reports). The Nix module system —
which we already adopted as the authoring frontend (D12) — ships the
alternative as a priority algebra (`mkDefault`, `mkForce`,
`mkOverride`) with a defined merge order.
*Recommendation:* compile-time error by default; explicit priority markers
as the only way to override. Silent last-wins is the one option to reject
outright, because it makes multi-writer skew invisible, which is the
failure mode §1 is trying to eliminate.

**(b) Ordering mechanism, and whether inference is in v1.** Three levels:
convergence fixpoint alone (CFEngine re-runs until stable — Bcfg2's answer,
and its client apply loop literally repeats while pending operations
decrease); fixpoint plus explicit `depends_on` where a real constraint
exists; or an AutoEdges-style inference stage in nix2cf that derives edges
from what each declaration provides and consumes.
*Recommendation:* the first two for v1. The decision needed now is only
whether inference is v1 scope or deferred — not which is better.

**(c) The collective re-verify unit, and whether interlocks are
first-class.** Bcfg2's Bundle is both the dependency-ish grouping and the
re-verification scope: entries in a bundle are validated collectively and
all get reverified when any one changes, and services in a bundle restart
when any member changes. Plus §4 above: a failing pre-action blocks the
whole bundle.
*Recommendation:* adopt the bundle-scoped precondition shape, and give the
Site Model an explicit `interlock`/`precondition` field. This is what
closes `stayturgid#289` structurally rather than by safe default.

**(d) Per-domain comprehensiveness.** Do we declare specific domains
complete, so unexpected state in them is reported as extra? This is the one
that determines whether multi-writer skew is detectable at all (§1), and it
is a Site Model schema property, so it is cheapest to decide before Step 0
writes the schemas.
*Recommendation:* yes, opt-in per domain, starting with the domains where
several people plausibly write — the app list, SSH configuration, the
launchd services.

## 7. What does not transfer

- **The client/server, render-on-demand topology.** Bcfg2 requires a
  reachable server to obtain goals at all; D14/D18 deliberately do not.
  Our compile output is a release artifact, not an HTTPS response. The
  *split* transfers, the topology does not.
- **XML as the configuration language,** and the plugin taxonomy built
  around it (Base/Bundler/Rules/Pkgmgr/Cfg/SGenshi/TCheetah). The typed Nix
  module system plus schema-validated JSON is the same idea with 2008's
  ergonomics removed. The one piece worth stealing verbatim is `altsrc`
  (bind an entry as if it had a different name, so `/etc/hosts` and
  `/etc/inet/hosts` share one source) — we will need the same trick for
  Termux's `$PREFIX`-relative paths versus Linux and macOS absolutes.
- **FSM change orchestration over repository revisions** (LISA '06).
  Genuinely interesting — cross-machine sequencing expressed as a state
  machine over *releases* rather than as edges in a per-host catalog, which
  fits our release train unusually well — but the paper is honest that
  administrators must enumerate all contingencies as discrete states, that
  time in any state is unbounded, and that one down client can stall a
  workflow. For a fleet whose devices are routinely unreachable, that is
  disqualifying as a default. Keep it filed as the shape to reach for *if*
  a real cross-device sequencing need appears; do not build it on spec.
- **Probes** — client-side scripts run before generation, whose output
  feeds server-side templates — are a good pattern we mostly already have:
  CFEngine's own classes and variables cover it, and §4.3.1 already
  discusses facts that cannot be known at compile time. Worth naming as the
  sanctioned answer for compile-time-unknowable facts rather than
  reinventing one.
