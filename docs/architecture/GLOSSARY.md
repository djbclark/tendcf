# Glossary — the contested words

**This file defines nothing.** Every entry points at the authority that
defines the term: a decision ID in `architecture-DEFINITIVE-v3.md`, a section
of the E1 adjudication or the goal-file reconciliation, or a `$defs` path in
`schema/`. Where this file and the cited authority disagree, **the authority
wins and this file is the bug** — and this file sits below both documents in
the precedence order `README.md` already sets: the guide wins over the
implementer map, which wins over this. That rule is the whole design: a glossary
that restates definitions becomes a fourth place to drift, alongside the
paper, the guide, and the normative document — and paper-drifting-from-
normative is a failure this project has already had (fixed in `48050f8`,
where §2.5 still described Model A in the present tense after E1 withdrew
it).

**Scope is deliberately narrow.** This is not a dictionary of the project.
It covers two classes of word only, because these are the ones that have cost
real time:

1. **Two live senses** — one word, two referents, at least one still current.
2. **A referent that moved** — the word survived a decision that changed what
   it points at, so old text using it is now false rather than merely dated.

An ordinary term with one stable meaning does not belong here. If you are
tempted to add one, that is how this file dies.

**Maintenance trigger:** when a decision withdraws a mechanism or renames a
concept, add or update the entry *in the same change*. Every entry below
exists because that did not happen at the time.

---

## Architecture

### capability

**Two senses. One was withdrawn; the surviving sense keeps the word.**

- **Current — a permission, in the security sense.** What a helper must hold
  to perform a peer action on another device's behalf. Checked against the
  *target's* peer allowlist, not merely asserted by the helper.
  Authority: `architecture-DEFINITIVE-v3.md` §7 (D16, D37);
  `tendcf-architecture-paper.md` §2.7, §2.8, §6.5.
- **Withdrawn — Model A's closed operation vocabulary.** A `capability` drawn
  from a fixed set, declared per operation in the ChangePlan, with an executor
  that refused any effect outside the declared set. Withdrawn by **D43 / E1**
  on 2026-08-15: CFEngine has no runtime capability confinement, so that
  executor could only be a pre-flight interpreter plus a correspondence proof
  that does not exist. The vocabulary, its versioning, and its skew policy are
  all dropped.

**Does not mean** a `token` (see below). Two unrelated things wore this word
until **DOC-4** (`b46d6e9`) split them. A blanket rename across the corpus
destroys the distinction — it has to be done site by site.

### token

A name a type supplies or needs, written `kind:name`. **A naming catalogue,
not a permission: holding a token grants nothing.** The kind set is closed so
a typo is a schema error rather than a silently-unmatched edge.

- **Was** `capability_token` until **DOC-4** (`b46d6e9`) took the word
  `capability` away from the catalogue sense.
- Authority: `schema/common.schema.json` `$defs.token` (D16(b)).

### ChangePlan

**The diff** between the goal file a device has already approved and the one
the release proposes.

- **Was**, under Model A, a per-host typed list of operations, each declaring
  a `capability` and the `resources` it may touch. **Changed by D43 / E1**,
  2026-08-15. Text that describes the ChangePlan as a list of operations is
  false, not just old.
- Authority: `architecture-DEFINITIVE-v3.md` §9 (D43),
  `e1-adjudication-xhigh-2026-08-15.md`.

### executor / validator

The on-device component that applies a release. Under Model B it is a
**validator**: a comparator that checks two canonical documents against an
approved diff and performs **no policy interpretation**.

**Does not mean** an interpreter. The distinction is not stylistic — it is
E1's entire argument for Model B, and calling it an interpreter concedes the
thing that made Model A impossible.
Authority: `architecture-DEFINITIVE-v3.md` §9 (D43).

### goal file

One fully resolved, canonical JSON document describing a single device's
**complete** managed state. It is simultaneously the compiler's output, the
consent object a person approves, and the validator's input — which is why
its schema is load-bearing three times over.
Authority: `architecture-DEFINITIVE-v3.md` §9;
`goal-file-schema-reconciliation-2026-08-15.md` §10.

### projection / projector

The **device-side** re-keying of an approved goal file into CFEngine Augments
form — `$(sys.workdir)/data/host_specific.json`, containing `{"vars": {…}}`
and no sibling keys. Runs inside `tendcf-agent` after approval.

**The goal file is not the Augments JSON**, and nothing Augments-shaped is
ever on the wire. This was the brief's hard part 7 and stayed open through
E1; closed by the reconciliation. Grounds: unknown top-level keys in
`host_specific.json` are warn-and-skipped by CFEngine 3.27.1, which is
ignore-unknown semantics in the consent path and disqualifying under E1 §5.6.
Authority: `goal-file-schema-reconciliation-2026-08-15.md` §9.

### coverage

**One enum, three values**: `comprehensive`, `not-yet-migrated`,
`deliberately-unmanaged`. Entries nest inside the domain's coverage envelope,
so an entry without stated coverage is *unrepresentable* rather than a lint
finding.
Authority: `goal-file-schema-reconciliation-2026-08-15.md` §4.1;
`schema/common.schema.json` `$defs.domain_coverage` (D16(d)) for the Site
Model's authoring shape, which differs and is resolved by the compiler.

### undeclared

A domain **absent from the map entirely** — the third silence class, named by
the reconciliation as a friendly amendment to E1 §5.4/§5.7.

**Not a fourth value of `coverage`.** You cannot enumerate the unbounded
unknown; declaring a domain is precisely the act that makes a backlog item
countable. A domain's first appearance is a reviewable change with
`"old": "undeclared"`.
Authority: `goal-file-schema-reconciliation-2026-08-15.md` §4.1.

### tombstone

An actuated entry carrying `state: "absent"` that **persists in the goal
file**. Removal is a *state*, not a diff event: the negative promise renders
from the file, so it is idempotent, crash-safe, and survives an N−7 → N
catch-up.

- **Corrects** E1 R4/§9.8 as written, which compiled the negative promise
  from the diff — giving the diff apply semantics, on exactly the ground E1
  §5.1 used to refuse shipping diffs.
- Authority: `goal-file-schema-reconciliation-2026-08-15.md` §6 (C-4).

### privileged / privilege

Not a flag on an entry. An entry is privileged **by address**: it sits under
the reserved, required, const-comprehensive `device-trust` domain, and
privilege is derived against the baseline rather than asserted. That domain
holds `policy-tree`, `trust-policy`, `advisor-key`, and `agent`.

**Consequence worth knowing:** `trust_tier` is an *entry*, not a header
field, so re-tiering a device is an ordinary privileged hunk.
Authority: `goal-file-schema-reconciliation-2026-08-15.md` §7.

### schema_ceiling

Required integer on `device_convergence` — the schema version a host can
render at. Two-phase rollout progress is visible as the ceiling moving
N−1 → N, which is why `validator_version` alongside it is optional
diagnostics and not a second required claim.
Authority: `goal-file-schema-reconciliation-2026-08-15.md` §12.

---

## Process

### ticket

**A GitHub issue or discussion number** (`#290`, `#6295`), not a Jira
`CFE-NNNN`. The three CFEngine contributions carry bare `Ticket: #NNNN`
trailers because Jira write-auth was broken and `cfengine/core` has Issues
disabled, so Discussions stand in.

`CONTRIBUTING.md` documents the Jira format and was deliberately disregarded
— the operator's call, framed as a belief ("99% sure it is decrepit") rather
than a verified fact, so **re-ask before relying on it again**.
Authority: handoff `ebe4`.

### ChangePlan vs. release

A **release** is the signed, versioned unit that reaches devices. The
**ChangePlan** is what the device computes from it. One is delivery, the
other is consent; they are not two names for the same artifact.
Authority: `architecture-DEFINITIVE-v3.md` §9, §9.11.
