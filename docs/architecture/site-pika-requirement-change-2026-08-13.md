# site-pika requirement change — three root-trusted admins, no GUI

> **Archival (2026-08-13).** Snapshot of research as of that date. Not current design. On conflict, [`../paper/tendcf-architecture-guide.md`](../paper/tendcf-architecture-guide.md) wins. Do not rewrite this file to bring it up to date.

Operator, 2026-08-13, superseding the site-pika assumptions used in
`rudder-as-umbrella-evaluation-2026-08-13.md` and
`bolt-choria-as-umbrella-2026-08-13.md`.

**New requirement:** site-pika has **three people, all trusted with root
access**, and **no GUI is needed**.

**Consequence: Rudder drops out entirely** — not "no for the fleet, maybe
for site-pika," but no, full stop. And the conclusion this research leg
reached three separate times — that one system for both the fleet and
site-pika was the wrong goal — **is reversed**. One architecture now
covers both.

## 1. What this kills

Every gain Rudder offered for site-pika was a consequence of the old
assumptions. Against the new requirement:

| Rudder's gain for site-pika | Status now |
| --- | --- |
| RBAC / differentiated per-person access (free in Core) | **Moot** — all three are root-trusted |
| Multi-tenancy | **Moot** — one tenant |
| Technique Editor: GUI authoring for non-sysadmins | **Moot** — no GUI needed |
| Compliance dashboards / web UI | **Moot** — no GUI needed |
| FusionInventory node inventory | Marginal; not worth a JVM and a Postgres for |

That is the whole list. Nothing survives that justifies standing up a
Scala webapp, a PostgreSQL database, and an always-on x86-64 Linux server
with a 3-month upgrade obligation.

**Honest note on the research:** the Rudder-RBAC-is-free-in-Core finding
(§1 of the orchestration research doc) was the most effortful result of
this leg and it is now **not decision-relevant**. It was still worth
having — it is what allowed site-pika to be evaluated correctly rather
than dismissed on a wrong assumption about cost — but it should not be
defended or leaned on going forward. Recording that plainly so a future
reader does not resurrect Rudder on the strength of a finding that no
longer bears on anything.

## 2. What this does *not* kill

Handoff `601f` identified four things communal management brings. Be
precise about which the new requirement actually removes:

- **Authorization** — removed. Everyone is root.
- **Tenancy** — removed. One site, one tenant.
- **Review artifact** — mostly removed as a *governance* need, but three
  people editing shared config still want to see each other's changes.
  Git already provides this for free (branches, PRs, signed commits, and
  `git log` as the audit trail). No additional system required.
- **Blast radius — NOT removed, and arguably worse.** Three people with
  root on shared infrastructure means any one of them can break the
  house for all three. Universal root removes the *authorization*
  question while leaving the *consequences* question entirely intact.
  This is the one that still needs an architectural answer, and it is
  the same answer the fleet needs: a typed ChangePlan, a dry-run, and a
  rollback path (§7.3). Not a permissions model.

- **Multi-author composition — NOT removed.** This is the D16-relevant
  one. Three people authoring config independently still means config
  that must compose correctly without each author knowing the others'
  ordering assumptions. Autorequire-style dependency inference was never
  about *authorization*; it was about *authoring ergonomics under
  multiple writers*. That pressure is unchanged.

## 3. Effect on D16

D16's reopening **narrows sharply but does not close.**

What reopened it was site-pika making multi-author contribution real.
Multi-author contribution is *still* real — three people is three
writers. What has changed is that the question is now **purely
technical** (does independently-authored config compose without explicit
ordering?) rather than **partly governance** (who may change what, who
approves, what is the tenancy boundary).

That is a genuine simplification: it removes the half of D16 that the
architecture had no answer for at all, and leaves the half that already
has a candidate answer — a dependency-inference stage over the typed
Site Model, with `mgmt`'s AutoEdges as the shipped precedent.

Recommended framing for the operator conversation, which is still the
gate: **D16 no longer needs a governance answer, only a composition
answer, and the composition answer does not require Puppet.**

## 4. The architecture I would now recommend

Unchanged from the previous recommendation except that the fourth layer
collapses into the first three:

1. **Compile — nix2cf.** Typed Site Model in the Nix module system,
   rendered to schema-validated JSON, compiled to per-platform artifacts.
   D12/D15/D19 intact. site-pika becomes *another site instance* in the
   same model — which is exactly the boundary decided this session and
   still unwritten: schemas in nix2cf, instances in the fleet repo.
2. **Convergence — CFEngine.** D13 intact. Still gated on the unrun
   Termux/Android build question (see §5).
3. **Reach and telemetry — Choria.** D14's transport slot. Assuming the
   Termux result holds, uniform across Ubuntu, macOS, ARM, Android — and
   now site-pika too, which is the least demanding consumer of it.
4. ~~site-pika as a separate Rudder site~~ — **deleted.**

site-pika is now the *easiest* environment in the estate: no GUI, no
RBAC, no exotic platforms, three cooperating admins, and git as the
coordination mechanism they already understand. If anything it is a good
**first** target — a lower-risk place to exercise the compile → converge
→ report path than the Android fleet.

## 5. Effect on the research queue

**Promoted:**
- Nothing. The Tier 1 items are unchanged and still dominate: **CFEngine
  on Termux/Android** (the asymmetric-risk test — a Go cross-compile is
  near-certain, a C/autotools port against Bionic is not), and **a real
  cold-device provision from factory reset**.

**Demoted or dropped:**
- *Scope site-pika's hardware/OS before deciding Rudder fits it* —
  **dropped**, no longer a Rudder decision. Still worth knowing what the
  hardware is, but now as ordinary site-instance modelling, not as a
  gating question.
- *Choria Streams retention/sizing* — **demoted**. With no compliance UI
  to feed anywhere, telemetry requirements shrink to whatever debugging
  actually needs.
- *Rudder Core RBAC follow-ups* — **dropped entirely** (§1).

**Unchanged:**
- Choria's identity/enrolment model without Puppet (trust-layer change,
  §7.2/§8).
- `flake.lock` vs `ops-release.json` (D19), still blocking Step 0.
- Read `mgmt`'s AutoEdges before designing the inference stage — now
  *more* relevant, since composition is the surviving half of D16.
- Has the D15 Augments path been prototyped at all? Still load-bearing,
  still unexercised.
- Image-based atomic updates: still depends on whether "IoT growth" means
  appliance-class devices or more Androids and Pis.

## 6. Register implications (still not applied — D16 conversation first)

- **D16** narrows to a composition-only question; the governance half is
  withdrawn by this requirement change.
- **D17** — the GPL rationale correction still stands, but Rudder's
  disposition is now simply "reference corpus," with no live adoption
  question attached to it in any scope.
- **D18** still has no surviving stated rationale (Postgres void,
  local-first withdrawn). Unaffected by this change; still needs
  re-deciding.
- **D14** would still change substantially if Choria is adopted.
