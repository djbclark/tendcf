# Goal-file schema: the reconciliation, and the binding design

**Date:** 2026-08-15. **Author:** Claude Fable 5 (xhigh), reconciliation pass
promised by `GOAL-FILE-SCHEMA-BRIEF.md`. **Status:** binding design for
`schema/goal-file.schema.json`. The three opinions
(`goal-file-schema-opinion-{fable,grok,gemini}.md`) are inputs and are
superseded by this document; where this document corrects
`e1-adjudication-xhigh-2026-08-15.md`, the corrections register in §15 is the
authority and E1 stands elsewhere. The schema itself is **not** created here —
landing `schema/goal-file.schema.json` is the follow-on work item and needs
operator sign-off (§18). **Method:** all three opinions, the brief, E1, map §9
and §4.1/§13/§16, guide §4/§7/§16, all five schemas, the lint, and the
fixtures were read in full. Three findings were pre-established as ground
truth by an earlier verification session (E1 §5.7-vs-§5.2 contradiction; CFE
3.27.1 warn-and-skip on `host_specific.json` unknown keys; report rows carry
no agent state) and are reconciled around, not re-litigated. Everything else
load-bearing was verified against the tree or empirically: the decided schema
in §10 was validated in a session scratchpad harness — valid JSON Schema
2020-12 against the repo's `common.schema.json` registry, two happy fixtures
validating, **31 adversarial negative fixtures all caught** — and the
zero-fraction-float pass-through, the JCS UTF-16-vs-code-point ordering
divergence, and the Fable sketch's unspellable-root-path gap were each
demonstrated by running code, not asserted. cf-agent 3.27.1 confirmed
installed at `/opt/homebrew/bin/cf-agent`.

---

## 0. The design in one screen

Numbered to the brief's seven hard parts. Each is a decision; the reasoning
and the losing positions are in §§2–9.

1. **Canonicalization.** RFC 8785 wire bytes; the schema leaves the
   canonicalizer almost nothing to decide: no defaults, no empty collections,
   no null, no floats (booleans allowed — E1 §5.2 corrected), one
   pattern-locked spelling per value class, no prose, no release stamp.
   Entries live in **maps keyed by identity**, not sorted arrays — a
   deliberate amendment of E1 §5.2's letter on E1's own criterion (§2.2).
2. **Entry identity.** The id is the **promiser** — the device-natural name
   the engine addresses (launchd label, systemd unit, prefix, key) — never the
   Site Model name. A rename honestly *is* remove+add because that is the
   actuation; "renamed" is a device-verifiable display pairing, never a hunk
   type. For keys, content is identity.
3. **Coverage.** One three-valued enum, not common's boolean+reason pair
   (ground truth 1). Entries nest **inside** their domain's coverage envelope,
   so entry-without-coverage and `deliberately-unmanaged`-with-entries are
   unrepresentable. An undeclared domain is a named third silence class.
   Coverage **retreat is privileged ceremony, not forbidden** (Grok's ratchet
   rows overruled, §4.3).
4. **Versioning.** `schema_version` is a `const` per schema revision; every
   shape change bumps; **one version for the whole family**. Fail closed on
   version and kind. The report-row fix: required `schema_ceiling` (integer)
   plus optional `validator_version` on `device_convergence`, added now while
   zero writers exist; a never-reported host renders at its
   first-adoption-enrolled version. The compiler's render-refusal rule **is**
   the two-phase enforcement; the separate release-lint check is cut.
5. **Privileged regions.** One reserved, required, const-comprehensive
   `device-trust` domain holds the floor: policy-tree digest, trust policy
   (tier + `local_yes_required`), advisor keys, and the **agent binary entry**
   (digest-bound; it is what makes the two-phase validator update expressible
   as a hunk at all). Privilege is derived by the validator, against the
   **baseline's** structure, from "any hunk under `device-trust`, plus the
   header" — in v1, nothing else. No flags in any format.
6. **Fetched content.** v1 fetches exactly two artifacts — the policy tree
   and the agent binary — and both bind by required digest. File-content
   machinery (inline/fetch) and the package-digest question are **deferred
   with their kinds**, which are not in v1 (§8).
7. **The open question.** The goal file is a **tendcf-owned schema, not the
   Augments JSON** — all three opinions converge, and the 3.27.1 parser
   evidence makes it ground rather than taste. The projector runs
   **device-side, inside tendcf-agent, after approval**: a policy-free
   re-keying of the approved file into `$(sys.workdir)/data/host_specific.json`
   as `{"vars": {…}}` only. `def.json` is never a per-host slot; nothing
   Augments-shaped ships on the wire; CI calls the *same* projector binary
   for golden tests, so there is one implementation (§9 — Grok's
   compiler-shipped sibling is rejected as a consent hole).

Plus one decision the brief did not number because none of the three opinions
fully owned it: **removal is a state, not an event** (`state: "absent"`
tombstones), correcting E1's R4 as literally written — including in
comprehensive domains, where Grok's prohibition is overruled because
extra-entry detection *reports* and does not remove (§6).

## 1. How the three opinions scored

**Fable's opinion carries the spine of the design**: the maps decision, the
nested-coverage structure, tombstones, the `device-trust` domain,
promiser-as-id, no-release-stamp, the single-enum coverage, the
`schema_ceiling` fix, the D-series corrections to E1 (all endorsed, §15.1),
and the empirically-tested method this reconciliation reused. It loses on
three points, two of them by its own criteria: the v1 kind set (`file` and
`package` violate its own "exactly what Steps 1–6 actuate" rule — F-2), the
optional `working_dir` (a hidden supervisor default, i.e. the two-spellings
defect its §1 exists to prevent — F-1), and delivery of the validator via a
package entry (evaporates once `package` is cut; replaced by the `agent`
trust kind).

**Grok's opinion contributes the empirical ground and the scope discipline**:
the 3.27.1 parser findings (one pre-verified as ground truth), the
`host_specific.json`-not-`def.json` slot with the `{"vars": …}`-only shape,
the narrow v1 kind set, the `unit-writer` kind (the device runs extra-entry
detection and does not have the Site Model — a real gap in the Fable sketch),
the validator-binary entry, and the guide corrections in its §8.5. It loses
on four points, three of them internal inconsistencies (§15.2, G-1…G-4):
the array-sort rule that silently diverges from JCS ordering, the
comprehensive-domain tombstone prohibition that reintroduces the very R4
defect its own §7 diagnosed, the header placement of `trust_tier` that
contradicts its own "only `schema_version` diffs in the header," and — the
big one — the compiler-shipped projection sibling, which reopens the
approved-equals-applied gap Model B exists to close (§9).

**Gemini's opinion contributes agreement-weight only.** Its two unanimous
positions (projection, rename-as-remove+add) stand, but on the strength of
the other two arguments plus the parser evidence, not its own. Every
distinctive position it took loses: the verbatim `domain_coverage` `$ref` is
ground-truth-contradicted; its `content` payload is an open
`patternProperties` bag — the escape hatch the brief's hard part 1 forbids —
with a free-string digest beside it; its projector targets `def.json`, the
slot where 3.27.1 drops unknown keys *silently*; its first-adoption
objection misreads the minimal-claim rule (§15.2, M-4); and its cut of
`explain-hunk` would leave R5 unmitigated at exactly the moment the proposer
is an AI rather than the person's own fresh memory (§14). The 109-line
length is not why it loses; the positions are.

Where all three converged — no rename hunk type, no attribution, fail-closed,
no privilege flags, projection — this pass re-derived each from the sources
before accepting it. All survive. One unanimous *absence* did not: none of
the three noticed that a consented-tier goal file with no advisor key is a
stall shipped as configuration; §10 makes it unrepresentable (N-1).

## 2. Canonicalization: the schema leaves the canonicalizer nothing to decide

### 2.1 The byte rules

Adopted from the Fable opinion §1, verbatim in substance:

- **Required scalars; collections present iff non-empty** (`minItems`/
  `minProperties: 1`, key optional). That pair is the whole absent-vs-empty
  story. Consequence found by this pass: *every* scalar with a "supervisor
  will default it" reading must be required — `working_dir` included (F-1).
- **No null, no empty strings, no floats.** Float enforcement is **joint**
  and was verified: JSON Schema 2020-12 `integer` accepts `15.0`
  (demonstrated against the decided schema — the harness prints the
  pass-through), and JCS serializes `15.0` as `15`, so byte-identity refuses
  the spelling. Schema catches true fractions; byte identity catches float
  spellings of integers. One negative fixture each.
- **Booleans are legal.** E1 §5.2's "integers and strings only" is corrected
  (C-3, Grok 8.4): JCS has canonical `true`/`false`, and forbidding them
  forces `"true"` strings — a second spelling waiting to happen.
- **One pattern-locked spelling per value class**: digests `sha256:` + 64
  lowercase hex; keys `ed25519:` + 64 lowercase hex; paths
  canonical-absolute with bare `/` admitted (F-1); package-pin rules recorded
  for when that kind lands (leading-digit rule, `unpinned` literal).
- **Nothing run-varying, including the release stamp.** The goal file is
  content-addressed; TUF binds release → hash; identical state re-released is
  identical bytes, `H(old) == H(new)`, no ceremony. (Fable's observation, now
  binding.)
- **No prose anywhere.** `description`/`note`/`platform_notes` are the DC-3
  intent channel and stay in the Site Model and briefing. This is why neither
  `domain_coverage` nor `interlock` can be `$ref`'d from `common` (C-1), and
  it is a tested negative fixture.
- **Byte-level definition, once:** JCS (RFC 8785) serialization, UTF-8, no
  trailing newline; parser rejects duplicate keys (`object_pairs_hook` —
  Python's default silently last-wins); NFC checked by validator and lint;
  use a real RFC 8785 implementation, because `json.dumps(sort_keys=True)`
  is not JCS for non-BMP strings (verified below). The `.json` fixtures are
  consciously exempt from newline-at-EOF conventions.

### 2.2 Maps keyed by identity, not sorted arrays (C-2 — E1 §5.2's letter amended)

This is the one place this document overrules both E1's letter and two of the
three opinions. The grounds are E1 §5.2's own stated purpose — one meaning,
one representation, enforced by the smallest possible trusted rule set — and
one verified fact:

- **RFC 8785 orders object members by UTF-16 code units.** An array "sorted
  by `(domain, kind, id)`" needs its own comparator, and the Grok opinion —
  the strongest array advocate — specified it wrong: "UTF-8 code points of
  the NFC form" diverges from JCS order wherever a non-BMP character meets
  U+E000–U+FFFF. Demonstrated in the harness: for U+FF01 vs U+1F600,
  code-point order and UTF-16 code-unit order disagree. Two orderings inside
  one canonical file, defined in two places, is exactly the class of defect
  §5.2 exists to prevent — and the array design *invites* it, since the
  strongest cold reader made the error unprompted. With maps there is no
  second definition: JCS's own member ordering **is** the entry ordering.
- **Uniqueness is structural.** Duplicate-key rejection is required for every
  object in the file regardless of this choice (I-JSON), so maps get
  `(domain, kind, id)` uniqueness from the parse itself; arrays need a
  separate lint/validator uniqueness rule.
- **Privilege derivation becomes a key-path prefix match.** "Any hunk under
  `/domains/device-trust`" is a pointer test. Array positions give the
  validator nothing.
- **Coverage nesting (§4) requires the map shape anyway**, and it is what
  makes two coverage violations unrepresentable rather than linted.

The addressing semantics of E1 §5.2 are preserved: hunks are still
entry-granular and addressed by `(domain, kind, id)` — realized as the key
path rather than as fields of a row. Two arrays survive because their order
is meaning (`command` argv, `pre_action.command`); one sorted string-set
array survives (`verbs`, when the peer-grant kind lands) with a single named
rule: ascending code-point order. If §14.2 review breaks the maps decision,
the Fable opinion §1 records the mechanical translation back to sorted
arrays; nothing else in this document changes.

## 3. Entry identity: the id is the promiser

Adopted from Fable §2 and Grok §2, which agree in substance:

- The id is the **device-natural actuation name** — launchd label, systemd
  unit, runit service dir, unit-writer prefix, advisor public key. The Site
  Model `name` never appears in the goal file: it is source-layer, and
  carrying it would make identical device states byte-different across
  refactors — the no-attribution rule E1 §5.5 already committed to, applied
  to a field E1 did not notice.
- **Rename is remove+add, honestly.** CFEngine has no rename primitive; a
  label change *is* unload+load. No rename hunk type, ever (all three
  opinions, plus three independent sufficient reasons in the record). The
  rescue for "scary pair of unrelated changes": under E1 §5.1 the device
  holds both full entries, so the briefing can pair a remove and an add with
  equal bodies and render "replaced under a new name — actuation: remove old,
  create new" with **device-verified** confidence. Briefing-layer work
  (Step 9), zero format cost.
- For `advisor-key` entries the id **is** the key: content is identity, and
  rotation is remove+add — the honest actuation of a rotation.
- Obligations carried: migration functions must be id-stable or §5.4's
  empty-diff rule breaks invisibly; id recycling across releases is a
  compiler/lint rule, residue; path aliasing via symlinks is R20.

## 4. Coverage: representable states are exactly the meaningful ones

### 4.1 Shape

- `coverage` is **one enum**: `comprehensive` / `not-yet-migrated` /
  `deliberately-unmanaged`. Ground truth 1 kills the verbatim `$ref`: the
  common def carries a `default`, an optional boolean (absent-vs-present-true
  is two spellings), required free prose, and if/then contradiction guards a
  single field does not need. Same three meanings; the Site Model keeps its
  authoring shape; the compiler resolves.
- Entries nest **inside** the domain envelope (`domains → <domain> →
  {coverage, entries}`), so an entry without stated coverage is
  unrepresentable and `deliberately-unmanaged`-with-entries is a schema
  violation, not a lint finding. `not-yet-migrated` **may** carry entries —
  that is what mid-migration looks like, and forbidding it would force
  one-big-flip migrations, the total-diff shape §5.4 exists to avoid.
- **A domain absent from the map is undeclared** — a third silence class E1
  §5.4/§5.7 does not name (friendly amendment, not contradiction): you cannot
  enumerate the unbounded unknown, and declaring a domain is precisely the
  act of naming a backlog item so it becomes countable. Site-Model-declared
  domains all appear in every goal file (as `not-yet-migrated` at minimum,
  per E1 §5.4's letter); domains nobody has named yet are undeclared, and a
  domain's first appearance is itself a reviewable `coverage_changes` item
  with `"old": "undeclared"`.

### 4.2 Where the escape hatch lives

Exactly where map §16 Q8 says: reclassification. The snapshot schema cannot
see the previous file; the ratchet lives in the **diff validator's ceremony
derivation** (Grok's correct structural insight), not in the snapshot.

### 4.3 The transition table — retreat is privileged, not forbidden

Grok's table forbids `comprehensive → not-yet-migrated` and
`deliberately-unmanaged → not-yet-migrated` outright. **Overruled.**
Sometimes retreat is the true state — a second writer is discovered, a
migration must be backed out — and a validator that forbids the honest
declaration forces either a lie (leave `comprehensive` while it is not) or a
permanent stall. The design principle throughout this corpus is *loud and
countable*, not *impossible*: cf. DC-37 treating `deliberately-unmanaged`
reclassification as a distinct review class rather than a prohibition.
Decided derivation rule, validator-held:

| Coverage transition | Ceremony class |
| --- | --- |
| undeclared → `not-yet-migrated` or → `comprehensive` | ordinary (declaring / tightening) |
| `not-yet-migrated` → `comprehensive` | ordinary (tightening) |
| any transition **into** `deliberately-unmanaged` | privileged (DC-37 class) |
| any transition **out of** `comprehensive` (incl. → undeclared) | privileged (retreat — Q8's escape hatch, made loud) |
| any transition **out of** `deliberately-unmanaged` | privileged (reversing a deliberate decision) |

One uniform rule the validator can hold: *a transition is privileged iff it
touches `deliberately-unmanaged` or leaves `comprehensive`*. This
operationalizes E1 §5.7's "distinct review class" through §9.8's
ceremony-class machinery — Fable D-7, adopted and extended. Retreats are
counted next to Q11's migration counter.

## 5. Versioning: everything additive is a bump, and the compiler is the enforcement point

- `schema_version` is a **`const`** per schema revision. A v2 file fails the
  v1 schema structurally; the validator dispatches on the value first and
  reports `version-above-ceiling` distinctly from `schema-invalid`; unknown
  kinds are additionally closed off by enumerated `properties` +
  `additionalProperties: false` — E1 §5.6's belt and braces, at zero cost.
- Be plain about what E1 understates: under `additionalProperties: false`
  and fail-closed refusal, **any additive field is as breaking as a new
  kind**. Every shape change bumps; every bump is a two-phase ship plus a
  migration release. Schema churn is expensive *by design*; Q11's counter is
  the meter, which is why v1 carries only what Steps 1–6 actuate (§8).
- **One `schema_version` for the family** (goal file, goal diff, approval
  record). Three version axes for one builder is a compatibility matrix
  nobody will maintain, and the other two documents embed goal-file entries
  anyway. (Fable §4, adopted.)
- **The report-row fix** — the brief's hard part 4, made concrete in §12:
  required `schema_ceiling` (integer, min 1) and optional `validator_version`
  (release_stamp, diagnostics) on `device_convergence`, added **now** while
  zero writers exist. Grok's required-`validator_version` variant is
  declined: the render rule reads the ceiling and the two-phase progress is
  visible as the ceiling moving N−1 → N, so the version string enforces
  nothing; one required column is the claim, the other is a courtesy.
- **A never-reported host renders at the version enrolled at its
  first-adoption ceremony** (Fable D-6's fix). Grok's "treat as ceiling 1" is
  correct only while 1 is the only version and wrong in general: a host
  enrolled at v3 that has never reported must render at v3, which the
  compiler knows and "assume 1" forbids.
- **The separate release-lint phase-order check is cut** (C-6, amending E1
  §5.6's last line): "the compiler refuses to render version N for a host
  whose reported ceiling is < N" *is* the two-phase enforcement, in the one
  place the per-host knowledge lives — a release-lint restatement would need
  the same report data and duplicate the same rule.
- The migration empty-diff rule becomes a mechanical predicate via the diff
  schema: a version bump is a **header change** (`version_bump`), not a
  hunk; a migration release is valid iff `version_bump` is present and
  `hunks`/`coverage_changes` are absent. Migration ceremony class is
  `baseline` per E1 §5.4.

## 6. Removal is a state: tombstones (C-4 — E1 R4 corrected as written)

Fable D-3 and Grok §7 found the same defect independently from opposite
directions, which is the strongest convergence in the corpus: **E1 R4/§9.8,
read literally, breaks convergence.** If the negative promise compiles from
the *diff*, the applied configuration is `f(goal file, diff)` — the diff has
acquired apply semantics (the exact ground on which §5.1 refused to ship
diffs), the applied state is no longer directly signed, and the removal is a
one-shot imperative that a crash, a re-run, or an N−7 → N catch-up loses.
Retry-until-stable cannot retry what exists only in a transient diff.

**Decision:** actuated entries carry `state: "present" | "absent"`. A
removal is a *replace* hunk (`present → absent`) whose tombstone persists in
the goal file; the negative promise renders from the **file** — idempotent,
crash-safe, re-release-safe, stale-catch-up-safe. The projector is thereby a
function of the new goal file alone (Grok's own §7 argument, which its
sibling-shipping needed and this design keeps). Consequences:

- E1 §8's negative fixture "removal expressed as a modify" **inverts**: a
  removal correctly *is* a modify of `state`. The real smuggling hazard is
  the **bare entry deletion**, which means "stop managing" — not "remove
  from device" — and the briefing must render the two distinctly ("stops
  being managed; the thing REMAINS" vs "will be stopped and unloaded").
- **Tombstones are legal in comprehensive domains — Grok's prohibition is
  overruled (G-2).** Grok's rule rests on "omission in a comprehensive
  domain means the sweeper's job," but there is no sweeper: extra-entry
  detection **reports** (D16(d): "reported as an extra entry"; the guide's
  §11 is titled *noticing* what shouldn't be there; `extra_entries` is a
  counter, a skew *signal*). Forbidding the tombstone there leaves a
  comprehensive domain with no actuated removal path at all — R4 reborn, in
  the domains that are supposed to be finished. If extra-entry handling ever
  gains an enforce mode, revisit; today report-only is the documented
  design.
- Tombstone kinds: `service` in v1 (plus future `file`/`package`).
  `interlock` and `unit-writer` are present-only — no device-state footprint
  to tombstone; deleting one is a remove hunk the briefing renders as "guard
  removed" / "writer declaration dropped."
- Tombstone lifecycle is new residue R19: dropping a tombstone is itself a
  change ("stop enforcing absence"), silent in non-comprehensive domains;
  the per-file tombstone count is a counter to watch beside Q10's diff
  sizes. Tombstone GC is a policy note, not a feature (§14).

## 7. Privileged regions: one address, derived against the baseline

- **A reserved `device-trust` domain, required and const-comprehensive**
  (Fable §5, adopted), holding four kinds: `policy-tree` (digest, singleton
  — R8's schema half paid on day one), `trust-policy` (tier +
  `local_yes_required`, both explicit), `advisor-key` (content-as-identity,
  revocation tombstones), and `agent`.
- **`trust_tier` is an entry, not a header field (G-3).** Grok put it at
  `/host/trust_tier` while also holding "the one header field that diffs is
  `schema_version`" — but re-tiering a device is a real, privileged change,
  which under header placement needs header-hunk machinery Grok elsewhere
  rejects. As a `device-trust` entry, a tier change is an ordinary privileged
  hunk and the diff schema's header carries exactly one changeable thing:
  `version_bump`. The header is `schema_version` + `host`, nothing else —
  no hostname (identity is the key), no platform (the unit flavor already
  states it; a second spelling otherwise, and the validator checks key
  equality, which is stronger).
- **The `agent` entry is load-bearing for E1 §5.6, not decoration (N-2).**
  The two-phase rule says the validator update arrives "as an ordinary diff
  under version N−1" — but a diff needs an entry to be a hunk *on*. With
  `package` cut from v1 (§8), the digest-bound `agent` entry is the only
  thing that makes the two-phase ship expressible. It also pays DC-11 for
  the one binary that matters most, rather than delegating the comparator's
  own bytes to a package-manager chain. Grok had the entry; neither opinion
  connected it to §5.6's expressibility. One binary, one entry — validator
  and projector version together.
- **Self-referential consumption is the enforcement trick:** validator and
  agent read their own configuration *only* from `device-trust`; trust
  content misfiled elsewhere is inert, not covert — and the trust kinds are
  structurally inexpressible outside the trust domain (disjoint kind sets).
- **Privilege is derived against the *baseline's* structure, never the
  proposal's** — otherwise one diff rewrites the rules and enjoys the
  rewrite in the same approval. E1 never states this ordering; it goes into
  the validator spec and §14.2 review target 3.
- **In v1 the compiled-in promiser list is empty.** Fable's list
  (`package:tendcf-agent`, `package:cfengine`, config paths) existed because
  its v1 had gate machinery arriving as ordinary package/file entries. With
  those kinds cut, the derivation collapses to "any hunk under
  `device-trust`, plus the header" — the shortest this list will ever be.
  It regrows when `package`/`file` land; that regrowth is R1, watched.
- **N-1, new in this pass:** `local_yes_required: true` with no
  `advisor-key` entries is a device nobody can say yes for — a stall shipped
  as configuration. The schema makes it unrepresentable (if/then in
  `trust_domain`; tested both directions). None of the three opinions
  caught it.
- Day one, the ceremony-derivation rules are compiled into the validator;
  the list-as-baseline-data design stays cut (§14). `device-resource-policy`
  and any trust-policy bag beyond `consent` stay out — empty placeholder
  kinds are how privilege flags come back (Grok's principle, adopted; DC-12
  remains open).

## 8. The v1 kind set, and fetched content

**Decided v1 kinds — state: `service`, `interlock`, `unit-writer`; trust:
`policy-tree`, `trust-policy`, `advisor-key`, `agent`. Seven, no more.**

The decision rule is Fable's own sentence — "v1 should carry exactly the
kinds Steps 1–6 actuate" — applied honestly, which Fable's own list fails
(F-2): Steps 1–5 are service adapters on three platforms plus
`buildfile`/conflict/extra-entry; Step 6 is the gate. Nothing in the Site
Model today declares a file or a package; a `file` kind whose domain never
migrates and a `package` kind nothing populates are speculative surface, and
under the strict bump rule speculative surface is not even cheap insurance —
it is an unreviewed claim about operations not yet transcribed (Grok §9,
cut 12, adopted). Named omissions, each a counted bump when it lands:

- **`file`** — and with it the entire inline/fetch content design (Fable §6:
  bounded inline xor digest+size fetch, with the deterministic
  inline-iff-UTF-8-under-cap rule). Recorded as the decided shape for when
  it lands; not in v1.
- **`package`** — and with it the delegation question. Both positions are
  recorded for that day: Fable's stated delegation (pin `(manager, name,
  exact version)`, bytes verified by the manager's own signed chain, TC-23
  already concedes maintainer scripts run as root) versus Grok's harder line
  (a digestless package kind presents R12 as closed). This reconciliation
  does not decide it, because deciding it now would be exactly the
  speculative surface the cut removes. R12 stays open for packages either
  way.
- **`peer-grant`** — cut from v1, overruling both Fable and Grok (G-4).
  Grok's own rule condemns its own `peer` kind: the verb enum is admitted
  guesswork ("a guess from architecture §10"), peer actions have no schema
  even in the Site Model (Step 0's remaining list), and a wrong-guessed
  closed enum in a consent schema must bump to be fixed anyway — so the
  guess buys nothing over the honest bump when D37 actually lands. The
  target-side allowlist shape (id = key or `group:` name, sorted `verbs`
  set) is recorded in the Fable opinion for that day.
- `directory`, symlinks, ACLs, xattrs, ordering edges (origin-stripped if
  ever — C-8), roles (compiler-resolved away), Homebrew cask/formula
  distinction — all as in Fable §8's omission list.

**`unit-writer` is in, from Grok (§1's real addition to Fable):** the device
runs extra-entry detection against the goal file, and the device does not
have the Site Model — so a comprehensive supervisor domain is only checkable
if the writer registry travels in the file. Present-only entries, prefix as
id, writer enum verbatim from `launchd-writers.schema.json`, `repo`/`note`
prose left behind, non-nesting rule carried into goal-file lint.

**Fetched content in v1** is therefore exactly two artifacts — policy tree
and agent binary — both digest-required in the schema, covered by the
accept, re-verified immediately before use (DC-11). The tree-digest byte
sequence (what exactly is hashed over a tree) must be specified before
Step 6 — R23, named by Grok, carried. Retrieval is TUF's job; no URLs, no
names-as-identity in the file.

## 9. The projection: device-side, one implementation, nothing Augments-shaped on the wire

All three opinions and the 3.27.1 evidence agree the goal file is not the
Augments JSON; that part is closed (warn-and-skip on unknown
`host_specific.json` keys is ignore-unknown semantics in the consent path —
disqualifying under E1 §5.6 — plus `vars`/`variables` dual spelling, float
laundering, and the shape conflict with the MPF). The genuine split is where
the projector runs, and it is the largest single adjudication in this
document.

**Decision: the projector is device-side, inside tendcf-agent, run after
approval — Fable's position — with Grok's empirical specifics adopted as the
projector's contract:** target is `$(sys.workdir)/data/host_specific.json`
and nothing else; output is `{"vars": {…}}` with no sibling keys — no
`variables`, no `classes`, no `inputs`, no top-level `data`; `def.json`
remains MPF glue under the policy-tree digest and is never a per-host slot
(3.27.1 drops its unknown keys *silently* — Gemini's `def.json` target was
wrong on the worst possible slot).

Why Grok's compiler-shipped sibling loses, stated fully because cost is
first-class and Grok's cost argument deserves the answer:

1. **It reopens the gap Model B exists to close.** Under
   ship-both-and-hash-bind, the accept covers `H(projected_augments)` but no
   one *reviews* the projection — the consent ceremony examines the
   goal-file diff while cf-agent eats the sibling. The device can verify the
   sibling's hash matches the approval; it cannot verify the sibling
   corresponds to the goal file without a projector, which is the component
   this option exists to avoid. A buggy or compromised release pipeline can
   ship goal file X with projection Y ≠ project(X): the advisor approves the
   X-diff, the ceremony proceeds normally, and Y runs. The compiler's
   *render* output enjoys no such gap because the render is what the diff
   review examines; the projection would be the one compiler output bound by
   an unreviewable hash. Grok saw the crack ("a real crack in the slogan …
   state it") and priced it as a footnote; it is not a footnote — it is the
   entire actuated surface.
2. **The cost argument dissolves on inspection.** "A second implementation
   of the same function on macos, Linux, and Termux" miscounts: the
   projector is one JSON-to-JSON re-keying, written once in the agent's
   language, running wherever the agent already runs — exactly like the
   validator. And the projector must exist *somewhere* under either option
   (Grok's compiler needs one too); the only question is whether its output
   is inside or outside the gate. Putting it in the agent and having **CI
   invoke the same agent binary for golden tests** yields one
   implementation, two call sites, and *less* machinery than the sibling
   option (no per-host TUF sibling targets, no approval-record hash
   extension, no wire delivery of a second artifact).
3. **Format authority and the wire follow.** The Augments file never appears
   on the wire; nothing reaches cf-agent that was not computed from the
   approved baseline by device-held code; and tendcf owns the consent
   format's semantics under `schema_version` alone (Fable's reason 1 —
   `host_specific.json` acquiring parsing at 3.18 is itself the proof that
   Augments semantics move with the engine).

What keeps this from quietly rebuilding Model A's interpreter — the honest
cost of the decision, carried as residue R21: **the projector must be
policy-free**, a structural re-keying only (entries → the generic bundle's
containers, tombstones → the negative-promise lists, trust entries → the
agent's own config). That is achievable precisely because entry bodies are
already engine-facing (§3). **Tripwire, a named §14.2 review target:** any
projector change that inspects entry *values* to decide output *structure*
is the interpreter returning, and gets treated the way E1 treats
label-widening. On Android the projector inherits the Termux/APK UID
boundary alongside R10's baseline storage — the platform where every hard
residue already lives; stated, not solved.

`augments_digest` inside the goal file stays rejected (circular — Grok,
right). No `mergedata()`, no YAML anywhere near the wire.

## 10. The decided schema

Empirically validated as described in the header (31 adversarial negatives
caught; happy and consented fixtures validating; harness preserved in the
session scratchpad). This is `schema_version: 1` — exactly what Steps 1–6
actuate. It goes to `schema/goal-file.schema.json` only after operator
sign-off and the §14.2 review sequencing of E1 §6.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/frdminc/tendcf/schema/goal-file.schema.json",
  "title": "Goal file — canonical per-host intended state (D43/D44)",
  "description": "DECIDED SKETCH from goal-file-schema-reconciliation-2026-08-15.md, not the landed schema. One fully resolved JSON document per host: compiler output, consent object, validator input (guide §7, map §9). Canonical form is RFC 8785 (JCS) plus the rules in the reconciliation §2; the validator refuses any file not byte-identical to the canonicalization of itself. No defaults anywhere: every scalar is required with its explicit value; collections are present iff non-empty; entries are maps keyed by device-natural id, so JCS member ordering IS the entry ordering and the hunk address (domain, kind, id) is the key path.",

  "type": "object",
  "properties": {
    "schema_version": {
      "description": "Goal-file family version (shared with goal-diff and approval-record). Stricter than contract_version: ANY shape change, additive included, bumps it (E1 §5.6). A const, so a file claiming any other version fails this schema structurally; the validator dispatches on the value first and reports version-above-ceiling distinctly from schema-invalid.",
      "const": 1
    },
    "host": {
      "description": "Device public key — host identity is the key, not the hostname (map §3). First-line cross-device replay check (TC-11): a validator refuses a goal file whose host is not itself before computing any diff. Immutable: re-keying is re-enrollment, a baseline ceremony (DC-22 residue). One spelling: fixed prefix, lowercase hex.",
      "type": "string",
      "pattern": "^ed25519:[0-9a-f]{64}$"
    },
    "domains": {
      "description": "Every domain this file makes claims about, each with its coverage stated. An entry cannot exist without its domain's coverage: 'silent because unchanged' vs 'silent because not described' is decided structurally (E1 §5.7). A domain absent from this map is UNDECLARED — semantically not-yet-migrated without a name; declaring it is the act of naming the backlog item, and its first appearance is a coverage_changes item in the diff. device-trust is always present and always comprehensive.",
      "type": "object",
      "propertyNames": { "$ref": "common.schema.json#/$defs/identifier" },
      "properties": {
        "device-trust": { "$ref": "#/$defs/trust_domain" }
      },
      "required": ["device-trust"],
      "additionalProperties": { "$ref": "#/$defs/state_domain" }
    }
  },
  "required": ["schema_version", "host", "domains"],
  "additionalProperties": false,

  "$defs": {
    "coverage": {
      "description": "One enum, not common.schema.json's boolean+reason pair: the goal file admits no defaults and no second spelling of one meaning (E1 §5.2 as corrected), and a single field makes the boolean/reason contradiction unrepresentable instead of if/then-guarded. Same three meanings as domain_coverage; the Site Model keeps its authoring shape and the compiler resolves to this one. No prose: signed prose is the intent channel DC-3 keeps out of the verifiable layer.",
      "enum": ["comprehensive", "not-yet-migrated", "deliberately-unmanaged"]
    },

    "state_domain": {
      "description": "A domain of device state. entries present iff at least one entry is described — omission is the only spelling of none (E1 §5.2). A deliberately-unmanaged domain cannot carry entries: 'not ours to describe', with descriptions in it, is a contradiction made unrepresentable.",
      "type": "object",
      "properties": {
        "coverage": { "$ref": "#/$defs/coverage" },
        "entries": { "$ref": "#/$defs/state_entries" }
      },
      "required": ["coverage"],
      "additionalProperties": false,
      "if": {
        "properties": { "coverage": { "const": "deliberately-unmanaged" } },
        "required": ["coverage"]
      },
      "then": { "not": { "required": ["entries"] } }
    },

    "state_entries": {
      "description": "kind -> id -> entry. Kinds are a closed set per schema_version: an unknown kind is a structural violation, the belt-and-braces half of fail-closed (E1 §5.6). v1 carries exactly what Steps 1–6 actuate: services, their interlocks, and the unit-writer registry the device-side extra-entry detector reads. file and package are named omissions (reconciliation §8), each a counted bump when it lands.",
      "type": "object",
      "properties": {
        "service": { "$ref": "#/$defs/service_map" },
        "interlock": { "$ref": "#/$defs/interlock_map" },
        "unit-writer": { "$ref": "#/$defs/unit_writer_map" }
      },
      "additionalProperties": false,
      "minProperties": 1
    },

    "absent": {
      "description": "A tombstone: this thing must not exist, converged on every run. Removal is a state, not an event — the negative promise renders from THIS file, so it survives crashes, re-runs, stale catch-up, and identical re-releases, which a diff-driven removal does not (reconciliation §6, correcting E1 R4). Valid in any coverage mode that admits entries: extra-entry detection in a comprehensive domain REPORTS, it does not remove, so the tombstone is the only actuated removal path there too. state is the only field: absent-with-a-stale-body would be a second spelling of absence.",
      "type": "object",
      "properties": { "state": { "const": "absent" } },
      "required": ["state"],
      "additionalProperties": false
    },

    "service_map": {
      "type": "object",
      "propertyNames": {
        "description": "The device-natural unit name — the promiser: launchd label, systemd unit, runit service dir. Not the Site Model service name, which is a source-layer concept (reconciliation §3). Modify-vs-remove+add in the diff then matches modify-vs-unload+load in actuation. Lint: on a comprehensive domain the id must fall under a unit-writer prefix whose writer is cfengine.",
        "type": "string",
        "pattern": "^[A-Za-z0-9][A-Za-z0-9@._-]*$",
        "maxLength": 128
      },
      "additionalProperties": {
        "oneOf": [
          { "$ref": "#/$defs/service_present" },
          { "$ref": "#/$defs/absent" }
        ]
      },
      "minProperties": 1
    },

    "service_present": {
      "type": "object",
      "properties": {
        "state": { "const": "present" },
        "bundle": {
          "description": "Re-verification scope and interlock blast radius (D16(c)). A bundle exists by being referenced; there is no bundle kind (reconciliation §8). Cross-checked by lint: every interlock's bundle is used by at least one entry.",
          "$ref": "common.schema.json#/$defs/identifier"
        },
        "run_as": { "type": "string", "pattern": "^[a-z_][a-z0-9_-]*$", "maxLength": 32 },
        "command": {
          "description": "argv. An array because order is meaning — with pre_action.command, the only arrays in the file whose order is semantic.",
          "type": "array",
          "items": { "type": "string", "minLength": 1 },
          "minItems": 1
        },
        "env": {
          "description": "Secret NAMES only, resolved by secretspec at run time — reused verbatim from common because env_map is canonical-safe (no defaults, no optional booleans).",
          "$ref": "common.schema.json#/$defs/env_map",
          "minProperties": 1
        },
        "working_dir": {
          "description": "REQUIRED, unlike the Site Model: an optional scalar whose omission means 'the supervisor's default' is a hidden default and a second spelling of that default's value (reconciliation §9, F-1). The compiler resolves the per-supervisor default ('/' for launchd and systemd system services, the service directory for runit) and states it.",
          "$ref": "#/$defs/abs_path"
        },
        "unit": { "$ref": "#/$defs/unit" }
      },
      "required": ["state", "bundle", "run_as", "command", "working_dir", "unit"],
      "additionalProperties": false
    },

    "unit": {
      "description": "Exactly one supervisor rendering, fully resolved: every knob the adapter renders is present with its explicit value. The unit's name is the entry id and is NOT repeated in the body — one source of identity (contrast the Site Model's launchd.label, which lint must otherwise force equal to the id). Growing any flavor's field set is a schema_version bump by the strict rule; that is Q11's meter working.",
      "oneOf": [
        {
          "type": "object",
          "properties": {
            "launchd": {
              "type": "object",
              "properties": {
                "run_at_load": { "type": "boolean" },
                "keep_alive": { "type": "boolean" }
              },
              "required": ["run_at_load", "keep_alive"],
              "additionalProperties": false
            }
          },
          "required": ["launchd"],
          "additionalProperties": false
        },
        {
          "type": "object",
          "properties": {
            "systemd": {
              "type": "object",
              "properties": {
                "enabled": { "type": "boolean" }
              },
              "required": ["enabled"],
              "additionalProperties": false
            }
          },
          "required": ["systemd"],
          "additionalProperties": false
        },
        {
          "type": "object",
          "properties": {
            "runit": {
              "type": "object",
              "properties": {
                "enabled": { "type": "boolean" }
              },
              "required": ["enabled"],
              "additionalProperties": false
            }
          },
          "required": ["runit"],
          "additionalProperties": false
        }
      ]
    },

    "interlock_map": {
      "type": "object",
      "propertyNames": { "$ref": "common.schema.json#/$defs/identifier" },
      "additionalProperties": { "$ref": "#/$defs/interlock_entry" },
      "minProperties": 1
    },

    "interlock_entry": {
      "description": "Same semantics as common.schema.json#/$defs/interlock, restated canonical-form: expect_exit and timeout_seconds lose their defaults and become required; description prose stays in the Site Model (that is why this cannot $ref the common def — reconciliation §15, C-1). blocks and report stay consts — a proposer cannot narrow the blast radius or silence the report by construction. Present-only: an interlock has no device-state footprint to tombstone; deleting one is a remove hunk the briefing must render as 'guard removed'.",
      "type": "object",
      "properties": {
        "state": { "const": "present" },
        "bundle": { "$ref": "common.schema.json#/$defs/identifier" },
        "pre_action": {
          "type": "object",
          "properties": {
            "command": {
              "type": "array",
              "items": { "type": "string", "minLength": 1 },
              "minItems": 1
            },
            "expect_exit": { "type": "integer", "minimum": 0, "maximum": 255 },
            "timeout_seconds": { "type": "integer", "minimum": 1, "maximum": 3600 }
          },
          "required": ["command", "expect_exit", "timeout_seconds"],
          "additionalProperties": false
        },
        "defines_class": { "type": "string", "pattern": "^[a-z][a-z0-9_]*$" },
        "blocks": { "const": "enclosing-bundle" },
        "report": { "const": true }
      },
      "required": ["state", "bundle", "pre_action", "defines_class", "blocks", "report"],
      "additionalProperties": false
    },

    "unit_writer_map": {
      "description": "One writer per unit-name prefix, carried in the goal file because the DEVICE runs extra-entry detection and the device does not have the Site Model (Grok opinion §10, adopted). Present-only: a writer declaration is detector data, not actuated state. repo/note prose stays in the Site Model. Lint: no prefix nests inside another — the existing rail, applied to the goal file.",
      "type": "object",
      "propertyNames": {
        "type": "string",
        "pattern": "^[a-z][a-z0-9]*(\\.[A-Za-z0-9][A-Za-z0-9_-]*)+\\.\\*$"
      },
      "additionalProperties": { "$ref": "#/$defs/unit_writer_entry" },
      "minProperties": 1
    },

    "unit_writer_entry": {
      "type": "object",
      "properties": {
        "state": { "const": "present" },
        "writer": {
          "enum": ["cfengine", "mise", "nix-darwin", "homebrew", "apple", "third-party"]
        }
      },
      "required": ["state", "writer"],
      "additionalProperties": false
    },

    "trust_domain": {
      "description": "The privileged region as one reserved, always-present, always-comprehensive domain. The validator's privilege derivation is 'any hunk under device-trust', plus the header — and in v1 nothing else, because no state kind carries gate machinery (reconciliation §7). Privilege is derived against the BASELINE's structure, never the proposal's. The validator and agent read their own configuration ONLY from here, so trust content misfiled elsewhere is inert, not covert; the trust kinds are structurally inexpressible outside this domain.",
      "type": "object",
      "properties": {
        "coverage": {
          "description": "Const: a device-trust domain that is not comprehensive is a hole in the gate.",
          "const": "comprehensive"
        },
        "entries": {
          "type": "object",
          "properties": {
            "policy-tree": { "$ref": "#/$defs/policy_tree_map" },
            "trust-policy": { "$ref": "#/$defs/trust_policy_map" },
            "advisor-key": { "$ref": "#/$defs/advisor_key_map" },
            "agent": { "$ref": "#/$defs/agent_map" }
          },
          "required": ["policy-tree", "trust-policy", "agent"],
          "additionalProperties": false,
          "if": {
            "properties": {
              "trust-policy": {
                "properties": {
                  "consent": {
                    "properties": { "local_yes_required": { "const": true } },
                    "required": ["local_yes_required"]
                  }
                },
                "required": ["consent"]
              }
            },
            "required": ["trust-policy"]
          },
          "then": {
            "required": ["advisor-key"],
            "$comment": "A device whose consent policy requires a local yes, with no enrolled advisor key, is a device nobody can say yes for — a stall shipped as configuration. Unrepresentable instead of discovered in the field. (Reconciliation §7, N-1; none of the three opinions caught this.)"
          }
        }
      },
      "required": ["coverage", "entries"],
      "additionalProperties": false
    },

    "policy_tree_map": {
      "description": "R8 paid at the schema layer: a goal file without a policy-tree digest is invalid, so the generic bundle and any .cf alongside it are bound — as bytes — into what the person approved. Singleton. The byte sequence the digest is computed over (tree serialization) MUST be specified before Step 6 and is named residue R23. Verification order (baseline first, tree at load) is validator work, R10-adjacent.",
      "type": "object",
      "propertyNames": { "const": "tree" },
      "additionalProperties": {
        "type": "object",
        "properties": {
          "state": { "const": "present" },
          "sha256": { "$ref": "#/$defs/sha256" }
        },
        "required": ["state", "sha256"],
        "additionalProperties": false
      },
      "minProperties": 1
    },

    "trust_policy_map": {
      "description": "The consent gate class, as an ordinary privileged entry rather than a header field: a tier change is then an ordinary (privileged) hunk, and the diff schema needs no header-hunk machinery beyond the migration version_bump (reconciliation §7, contra the Grok opinion's header placement).",
      "type": "object",
      "propertyNames": { "const": "consent" },
      "additionalProperties": {
        "type": "object",
        "properties": {
          "state": { "const": "present" },
          "tier": { "enum": ["operator", "managed", "consented"] },
          "local_yes_required": {
            "description": "Fully resolved: the tier's default is resolved by the compiler, both fields present, no implication left to the validator.",
            "type": "boolean"
          }
        },
        "required": ["state", "tier", "local_yes_required"],
        "additionalProperties": false
      },
      "minProperties": 1
    },

    "advisor_key_map": {
      "description": "id IS the key: for keys, content is identity, so rotation is remove+add — the honest actuation of a rotation, not a scary artifact of it. state 'absent' is a revocation tombstone.",
      "type": "object",
      "propertyNames": {
        "type": "string",
        "pattern": "^ed25519:[0-9a-f]{64}$"
      },
      "additionalProperties": {
        "type": "object",
        "properties": { "state": { "enum": ["present", "absent"] } },
        "required": ["state"],
        "additionalProperties": false
      },
      "minProperties": 1
    },

    "agent_map": {
      "description": "The comparator/projector binary itself — TC-25 class, digest-bound (DC-11 for the one binary that matters most; bytes arrive as a TUF target, not via a package-manager chain). This entry is what makes E1 §5.6's two-phase rule EXPRESSIBLE in v1: the validator update is a privileged hunk on this entry, riding as an ordinary diff under version N−1. Without a package kind there is otherwise nothing for that update to be a hunk ON (reconciliation §7, N-2). Present-only: removing the agent is leaving management, not a goal-file operation. One binary, one entry — validator and projector version together.",
      "type": "object",
      "propertyNames": { "const": "tendcf-agent" },
      "additionalProperties": {
        "type": "object",
        "properties": {
          "state": { "const": "present" },
          "version": { "$ref": "common.schema.json#/$defs/release_stamp" },
          "sha256": { "$ref": "#/$defs/sha256" }
        },
        "required": ["state", "version", "sha256"],
        "additionalProperties": false
      },
      "minProperties": 1
    },

    "abs_path": {
      "description": "Canonical absolute path: no '//', no trailing slash, no '.' or '..' segments — every path has one spelling. Bare '/' is admitted explicitly (the Fable sketch's pattern could not spell the filesystem root, which the required working_dir needs — reconciliation §15, F-1). Symlink aliasing cannot be excluded textually and is named residue R20; non-ASCII and control characters in segments are a §14.2 review target.",
      "type": "string",
      "pattern": "^/$|^(?!.*/\\.\\.?(/|$))(/[^/]+)+$",
      "maxLength": 1024
    },

    "sha256": {
      "type": "string",
      "pattern": "^sha256:[0-9a-f]{64}$"
    }
  }
}
```

The negative set the harness ran, carried into `examples/broken/` when the
schema lands: `schema_version: 2`; unknown kind; empty `entries`; entries
under `deliberately-unmanaged`; tombstone with stale body; missing
`device-trust`; non-comprehensive `device-trust`; missing policy-tree
digest; missing agent entry; `local_yes_required` without an advisor key;
missing `working_dir`; dot-dot / trailing-slash / double-slash paths; two
unit flavors; missing launchd knob; empty argv; empty env map; unprefixed
host key; uppercase digest hex; defaulted `expect_exit`; silenced interlock
report; malformed writer prefix; unknown writer; uppercase domain;
proposer-set `privileged` flag; `description` prose; boolean+reason
coverage spelling; embedded release stamp; malformed advisor key id; float
timeout. Plus the byte-class negatives only the new fixture mechanism can
carry (§13).

## 11. The other two family members, in outline

Both share the family `schema_version` and reuse the goal file's `$defs`.
Outlines, per E1 §8; not this document's tested surface.

**`goal-diff.schema.json`** — device-computed authority, compiler preview,
CI golden artifact. Canonical JCS itself, since §9.1's cross-check is hash
equality of a canonical form:

```jsonc
{
  "schema_version": 1,                 // const, family version
  "host": "ed25519:…",
  "baseline_sha256": "sha256:…",       // H(old canonical goal file)
  "proposed_sha256": "sha256:…",       // H(new canonical goal file)
  "version_bump": {"old": 1, "new": 2},  // present iff migration; the ONLY
                                         // header change a diff can carry
  "coverage_changes": {                // present iff non-empty; a DISTINCT
    "<domain>": {"old": "undeclared",  // section the briefing cannot fold
                 "new": "not-yet-migrated"}  // into entry noise; "undeclared"
  },                                   // legal on either side (§4)
  "hunks": {                           // present iff non-empty; mirrors the file
    "<domain>": { "<kind>": { "<id>": {
      "old": { /* full old entry */ }, // at least one of old/new; presence IS
      "new": { /* full new entry */ }  // the op — an "op" field would be a
    }}}                                // second spelling
  }
  // No attribution, no groups, no privilege flags (E1 §5.5, §9.8).
}
```

An empty diff is no document (hash equality short-circuits). A migration
diff is `version_bump` alone — §5.4's "empty apart from the bump" as a
mechanical predicate. The diff never ships in a release.

**`approval-record.schema.json`** — the signed object is the **JCS bytes of
the record with the `signature` member removed** (C-5, replacing E1 §5.1's
hash-concatenation, whose optional briefing member is an
encoding-ambiguity hazard). Fields: `schema_version`, `host` (target key),
`baseline_sha256` (absent only at first adoption — a named §14.2 target,
TC-11/TC-20 territory), `proposed_sha256`, `nonce` (device-issued),
`approval_seq` (monotonic, DC-2 single-use), optional `briefing_sha256`,
`verdict` (`accept` | `reject` | `withdraw`), `refused` (hunk key-paths,
present iff reject, annotation only), `ceremony_class`
(`ordinary` | `privileged` | `baseline`, asserted by the approver and
checked against the validator's *derived* requirement), `signature`. DC-2's
substance — per-target validity, nonce, counter, persisted rejects — is
unchanged. Grok's `H(projected_augments)` extension is **dropped**: with the
device-side projector there is no shipped projection to bind (§9). Fixtures
must include a reject-with-annotations and a wrong-ceremony-class negative.

**Ceremony derivation, validator-held, consolidated:** privileged iff any
hunk falls under `device-trust`, or any coverage transition matches §4.3's
privileged rows; `baseline` iff `version_bump` is present (migration) or no
baseline exists (first adoption); ordinary otherwise. Derived against the
baseline's structure (§7).

## 12. The report-row addition (specified here; edited only with sign-off)

On `schema/report-row.schema.json#/$defs/device_convergence`:

```jsonc
"schema_ceiling": {          // REQUIRED (add to "required")
  "description": "Highest goal-file schema_version this device's validator
    fully interprets. What the D44 render rule reads; integer, not a string,
    so comparison is never lexicographic. For a host that has NEVER
    reported, the compiler renders at the version enrolled at that host's
    first-adoption ceremony.",
  "type": "integer", "minimum": 1
},
"validator_version": {       // OPTIONAL (diagnostics only)
  "description": "tendcf-agent binary that produced this row. The ceiling is
    the claim; this is the courtesy.",
  "$ref": "common.schema.json#/$defs/release_stamp"
}
```

Required-now, not optional-then-required: nothing writes rows yet, and the
schema's own header says "one column now and a migration later." The
`examples/report-rows.yml` `device_convergence` row gains `schema_ceiling`
in the same change.

## 13. Lint and fixtures

- **Pairing goes bilingual:** the `EXAMPLES` map and pairing glob admit
  `.json`; `examples/goal-file.json` is the happy fixture **in canonical
  bytes** — the fixture *is* the canonicalization test — and is consciously
  exempt from newline-at-EOF conventions.
- **A byte-class fixture mechanism, new:** today's broken-fixture harness
  parses YAML overlays, and canonicalization violations are invisible after
  a parse. Goal-file negatives that live at the byte layer must be raw
  `.json` bytes compared before parsing: pretty-printed twin of the happy
  path, trailing newline, duplicate keys, non-NFC string, `15.0` spelling
  of `15`. The JCS idempotence check (refuse any fixture ≠
  canonicalize(fixture)) lands with it.
- **Goal-file cross-file rules:** every interlock's `bundle` used by ≥ 1
  service; on comprehensive domains every service id falls under a
  `unit-writer` prefix whose writer is `cfengine`; unit-writer prefixes do
  not nest (the existing rail, applied here); goal-file/goal-diff fixture
  consistency (applying hunks to old yields new); goal-file schema `$ref`s
  none of `contract_version` / `domain_coverage` / `interlock` (Grok 8.6's
  rule, adopted — a future editor who `$ref`s `contract_version` silently
  adopts ignore-unknown-on-add).
- **Projector goldens:** CI invokes the agent's own projector;
  `project(goal-file.json)` must byte-equal the checked-in
  `host_specific.json` golden; a projection with any top-level key other
  than `vars` is a negative (parser leniency as a backdoor — Grok's
  fixture, adopted).
- `EXPECTED_BROKEN` bumps as cases land; the §10 negative list plus the
  byte-class and diff-class negatives (baseline-hash mismatch, hunk
  inconsistency, non-empty migration, ordinary-class approval over a
  privileged hunk, coverage retreat without privileged class) are the
  floor, per F-9b, not the ceiling.

## 14. What not to build

One unfunded builder; descending order of saved effort. Merged from the
three cut lists, with disagreements adjudicated:

1. **A compiler-shipped projection sibling** (Grok §9.2–9.3) — rejected not
   deferred; it is a consent hole, not a saving (§9).
2. **Identity with Augments** in any form; `def.json` as a per-host slot;
   YAML on the wire; `variables`/`classes`/`inputs` in the projection;
   `mergedata()` for per-host data. (Unanimous or empirically forced.)
3. **`file` and `package` kinds in v1**, and with them the inline/fetch
   machinery, the package-digest resolver, and the delegation decision
   (§8 — both positions recorded for when the kinds land).
4. **`peer-grant` in v1**; `trust-policy` bags beyond `consent`;
   `device-resource-policy` placeholders. Empty or guessed kinds are how
   privilege flags come back.
5. **Multi-version render** until v2 approaches. Ship the `schema_ceiling`
   column now (free), the render-refusal rule now (one `if`), the window
   machinery when it has two versions to bridge.
6. **Approval-record runtime** until Step 9. Write the schema now — §14.2
   reviews the family and the ceremony shapes gate the validator — build no
   signing/verification runtime before the consent surface.
7. **The separate release-lint phase-order check** — subsumed by the
   compiler's render-refusal (C-6).
8. **Rename hunks, attribution fields, dependency groups with apply
   semantics, privilege flags, `x-*` extension bags** — never; each is a
   rejected mechanism returning under a new name. (`related_id`, `from`,
   `class`, `privileged` are the names to watch for.)
9. **Tombstone GC as a feature** — a policy note and a counter (R19), not
   machinery.
10. **The baseline-data privileged list** — ceremony rules stay compiled
    into the validator; the self-referential design is strictly later.
11. **`explain-hunk` before the schema family exists** — due before Step 9,
    per E1 §5.5. Gemini's *permanent* cut is rejected: "the proposer's
    memory is fresh" is exactly false in the design's central case, where
    the proposer is the person's own AI (guide §8) and the fan-out R5
    mitigates is machine-generated. Deferral yes, deletion no.
12. **Rename pairing and display grouping** — Step 9 briefing-layer, never
    format.

## 15. Corrections register

### 15.1 To E1 (and to the map/guide text that inherited it)

E1 remains the binding verdict; these amend it where it is wrong or
under-specified. C-1, C-4, and C-7 are errors; the rest are letter-level
amendments or completions.

- **C-1 (error; ground truth 1).** §5.7's "verbatim from
  `common.schema.json#/$defs/domain_coverage`" contradicts §5.2: that def
  carries a `default`, an optional boolean, required prose, and if/then
  guards. Resolution: the single enum (§4). Corollary: E1 §8's "reuse the
  existing `$defs`" holds only for canonical-safe defs (`identifier`,
  `host_name`, `release_stamp`, `env_map`); composite defs with defaults
  (`domain_coverage`, `interlock`) must be restated.
- **C-2 (letter amended).** §5.2's "every set-semantics collection is an
  array sorted by a schema-declared key" is replaced by identity-keyed
  maps, on §5.2's own criterion; addressing semantics preserved (§2.2, with
  the verified UTF-16/code-point divergence as evidence).
- **C-3 (error, minor).** §5.2's "integers and strings only" — booleans are
  legal and necessary; JCS gives them one spelling (Grok 8.4).
- **C-4 (error).** R4/§9.8's removal-as-diff-compilation breaks convergence
  and contradicts §5.1's directly-signed-state argument; removal is a
  state (§6). E1 §8's "removal expressed as a modify" negative fixture
  inverts; the smuggling hazard is bare deletion vs tombstone, and guide §7
  and map §9.8 need the same rewrite (§18).
- **C-5 (hazard).** §5.1's accept formula
  `Sig(H(old) ‖ H(new) ‖ nonce [‖ H(briefing)])` has an optional-member
  framing ambiguity; replaced by signing the JCS bytes of the approval
  record minus `signature` (§11). DC-2's substance unchanged.
- **C-6 (completion).** §5.6: no defined render version for a
  never-reported host (fixed: first-adoption-enrolled version), and
  "release lint enforces the phase order" duplicates the compiler's
  render-refusal — one enforcement point, the one with the knowledge.
- **C-7 (error; ground truth 3, pre-established).** §5.6's "§6's report
  rows already carry release and agent state" is false; the concrete
  addition is §12. (v3 §9.6 already records the correction; this document
  supplies the field spec.)
- **C-8 (collision, from Fable D-4).** Map §4.1's "edges in compiled output
  carry origin" collides with §9.5's no-attribution rule if the goal file
  is the compiled output. Resolution: origin-bearing edges are
  preview-channel; the goal file carries no edges in v1 and origin-stripped
  edges if ever. Guide §16.A's `nix2cf_edges` illustration is
  preview-channel material and — per C-9 — does not load as Augments
  anyway.
- **C-9 (corpus errors, from Grok 8.5, consistent with ground truth 2).**
  Guide §4's "YAML is a valid input" is false against CFE 3.27.1 (JSON
  only), and guide §16.A's illustrative `host_specific.json` (top-level
  `data` + `nix2cf_edges`) loads nothing — both keys are skipped. The
  working shape is `{"vars": {…}}`. E1 §1's "complete resolved state is
  what the Augments layer consumes" is directionally right and shape-wrong:
  complete resolved *consent* state is not what Augments consumes; the
  projection is.
- **C-10 (completion).** §5.4's "every other domain enters as
  `not-yet-migrated`" quantifies over Site-Model-declared domains only; the
  undeclared class (§4.1) is the honest name for the rest.

### 15.2 To the opinions

Findings this pass adds beyond the pre-established three; each was verified
against the text or by running code.

- **F-1 (Fable).** Optional `working_dir` is a hidden supervisor default —
  omission and the explicit default value are two spellings of one meaning,
  violating its own §1 rule. Latent in the sketch (the field was optional),
  live the moment the no-defaults rule is applied honestly. And its
  `abs_path` pattern cannot spell `/` (verified: the regex rejects the bare
  root), which the required `working_dir` needs. Both fixed in §10.
- **F-2 (Fable).** Its v1 kind set (`file`, `package`) violates its own
  "exactly what Steps 1–6 actuate" criterion — nothing in the Site Model or
  Steps 1–6 populates either. Cut (§8); its validator-delivery-via-package
  story is replaced by the `agent` entry.
- **G-1 (Grok).** Its array-sort rule ("UTF-8 code points of the NFC form")
  diverges from RFC 8785's UTF-16 code-unit member ordering (verified
  demonstration in §2.2). Harmless for ASCII ids, disqualifying as a
  *definition*, and the strongest single argument that the array design
  invites rule-duplication defects.
- **G-2 (Grok).** "`presence: absent` forbidden in comprehensive domains"
  reintroduces R4: extra-entry detection reports and does not remove
  (D16(d), guide §11, `extra_entries` as counter), so the prohibition
  leaves comprehensive domains with no actuated removal path. Overruled
  (§6).
- **G-3 (Grok).** `trust_tier` in the header contradicts its own "the one
  header field that diffs is `schema_version`" and would require the
  header-hunk machinery it rejects. Relocated to `device-trust` (§7).
- **G-4 (Grok).** Its `peer` kind with an admitted-guessed verb enum
  violates its own no-speculative-kinds rule (§9, cut 12). Cut (§8).
- **G-5 (Grok, the big one).** The compiler-shipped projection sibling
  binds the entire actuated surface by an unreviewable hash — the
  approved-equals-applied gap reopened — and its cost case miscounts the
  implementations (§9).
- **M-1 (Gemini).** `content` as an open `patternProperties: {"^.*$": {}}`
  bag is the escape hatch hard part 1 forbids; with it, unknown state rides
  inside known kinds and `additionalProperties: false` at the envelope is
  theater.
- **M-2 (Gemini).** `domain_coverage` `$ref` — ground truth 1, directly.
- **M-3 (Gemini).** Projection target `def.json` — the slot where unknown
  keys are dropped *silently* (worse than `host_specific.json`'s warn), and
  the per-host slot the design already rejected.
- **M-4 (Gemini).** The first-adoption objection misreads the minimal-claim
  rule: the operator may enumerate as many domains as they will genuinely
  review at the ceremony — the rule bounds *unenumerated* claims, and
  tendcf's first adoption is the enrollment of an already-running device
  being transcribed, not greenfield bootstrap. E1 §5.4 stands unmodified.
- **N-1 (all three).** Consented-tier-without-advisor-key was representable
  in every sketch. Now structurally impossible (§7, §10).
- **N-2 (all three).** None connected E1 §5.6's two-phase rule to the
  requirement that the validator binary be *an entry* — the update must be
  a hunk on something. §7 closes it.

## 16. The strongest case against this reconciliation, stated to be acted on

Four exposures, in descending order of how much this document has staked on
them. (i) **Maps-not-arrays overrules normative text and two of three cold
readers.** If §14.2 review finds a maps-specific defect — deep-nesting
validation errors that resist good reporting, or a JCS
member-ordering edge this pass missed — the fallback is the mechanical
translation to sorted arrays recorded in the Fable opinion, at the price of
a pinned comparator definition and two lint rules; nothing else here moves.
(ii) **The device-side projector** puts a new trusted component on the
platform where every hard residue already lives, and its policy-freedom is
a discipline, not a theorem (R21); the tripwire is named, but tripwires
require someone watching. If agent-language constraints make the projector
genuinely expensive, the honest retreat is *not* Grok's hash-bound sibling
— it is narrowing v1's actuated surface until the projector is trivial,
because the sibling's gap is architectural, not implementational.
(iii) **The narrow v1 kind set guarantees early bumps** — `file` and
`package` will arrive, each a two-phase ship plus a migration release, and
a critic can say this reconciliation chose ceremony over foresight. That is
the design working as specified: Q11's counter exists to price exactly
this, and a speculative kind that guessed wrong would cost the same bump
*plus* a wrong-guess migration. If migration events cluster in year one,
re-read this section before concluding the meter is broken.
(iv) **Tombstones grow the consent surface** (two reviewable events per
removal; R19) on a project already watching diff fatigue — the counter to
watch is tombstone count per file, and the falsifier is drops becoming
rubber stamps.

## 17. Residue register: carried and extended

Nothing in E1 §7 is presented as solved. R1–R18 are carried with these
status notes: R1 (privileged list) — at its v1 minimum ("device-trust +
header"), regrows with `file`/`package`; R2/R3 — decided here, §2; R4 —
**restated by C-4** (tombstones), not closed; R5 — unchanged
(`explain-hunk` deferred, not cut); R6 — decided, E1 §5.4 + C-10; R7 —
decided, E1 §5.3; R8 — the *schema half* is paid (required `policy-tree`
entry); verification order and load-time check remain open; R9 —
unchanged, permanent honesty clause; R10 — unchanged, now shared with the
projector on Android; R11 — decided, §4; R12 — paid for v1's two fetched
artifacts only; **open for packages**, deliberately out of the file; R13 —
decided, §11 (C-5 construction); R14 — unchanged; R15/R16/R17/R18 —
unchanged. Q10 (is a diff consentable at all) is untouched by everything
here.

New residue this reconciliation adds:

| # | Residue | Source |
| --- | --- | --- |
| R19 | Tombstone lifecycle: dropping one is a change; silent in non-comprehensive domains; count per file is a watched counter. | §6 |
| R20 | Path aliasing: symlinks make two textual identities one inode; the pattern cannot see it. | §3 |
| R21 | Projector discipline: policy-free by discipline, not construction; value-inspecting structure decisions are the interpreter returning. Android UID boundary shared with R10. | §9 |
| R22 | First adoption has no baseline hash; the approval record's no-baseline case interacts with replay (TC-11/TC-20). | §11 |
| R23 | The policy-tree digest's byte sequence (what is hashed over a tree) is unspecified; must exist before Step 6. | §8 |
| R24 | Id recycling across releases (same `(domain, kind, id)`, different thing) is a compiler/lint obligation no snapshot schema can see. | §3 |

**§14.2 review targets, extended** beyond E1 §6's eight: the maps decision
itself (deep-nesting error reporting; JCS ordering edges; non-ASCII and
control characters in path segments and ids); privilege derivation ordered
against the baseline; the no-baseline approval path (R22); the coverage
ceremony table (§4.3) for completeness against Q8; comprehensive-domain
tombstone semantics if extra-entry handling ever gains an enforce mode; and
the projector tripwire (R21). The reviewer must be outside the lineage that
wrote this document and the Fable opinion — which are the same lineage, and
say so.

## 18. Follow-on edits this document requires (all operator-gated; none made here)

1. Land `schema/goal-file.schema.json` from §10 with
   `examples/goal-file.json` in canonical bytes and the §10/§13 negative
   sets; then `goal-diff` and `approval-record` from §11; then the §14.2
   review, before any validator code (E1 §6 sequencing; map §13 note).
2. Edit `schema/report-row.schema.json` and `examples/report-rows.yml` per
   §12.
3. Amend `architecture-DEFINITIVE-v3.md`: §9.2 (maps, C-2/C-3), §9.7
   (single-enum coverage, C-1; undeclared class, C-10), §9.8 (tombstone
   restatement, C-4; ceremony table §4.3), §9.6 (drop the release-lint
   phase-order clause, C-6), §9.1 (C-5 signing construction), §9 preamble
   (the not-settled-by-E1 paragraph closes: projection, device-side, §9),
   §4.1 (edge-origin scope note, C-8).
4. Amend guide §4 (YAML claim, C-9), §7 (removals paragraph, C-4; the
   projection sentence), §16.A (mark the Augments illustration as
   preview-channel and non-loading, C-9).
5. Extend `bin/schema_lint.py` per §13 (`.json` pairing, byte-class
   fixtures, JCS idempotence, goal-file cross-file rules,
   no-`$ref`-of-defaulted-defs rule).

## Sources

All in-repo, read 2026-08-15: the three opinions (in full);
`GOAL-FILE-SCHEMA-BRIEF.md`; `e1-adjudication-xhigh-2026-08-15.md` (in
full); `architecture-DEFINITIVE-v3.md` §4, §5, §6, §9, §13, §14, §16;
`docs/paper/tendcf-architecture-guide.md` §4, §7, §16;
`schema/{common,roles,services,report-row,launchd-writers}.schema.json`;
`bin/schema_lint.py`; `examples/` and `examples/broken/`. Empirical:
validation harness and fixtures in the session scratchpad
(`goalfile/goal-file.schema.json`, `goalfile/test_goalfile.py` — 31/31
negatives caught); cf-agent 3.27.1 presence confirmed; JCS-ordering and
root-path demonstrations run in-session. The 3.27.1 Augments parser
behavior is cited from ground truth 2 and the Grok opinion's §0/§8.5 test
log; this pass did not re-run cf-agent against fixture Augments files.
