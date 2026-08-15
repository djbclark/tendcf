# Goal-file schema: independent opinion (Fable pass)

**Date:** 2026-08-15. **Author:** Claude Fable 5 (xhigh), cold pass per
`GOAL-FILE-SCHEMA-BRIEF.md`. **Status:** opinion, one of three written
independently; a later pass reconciles. The sibling opinions were not
opened. **Method:** the brief's reading order was followed in full
(adjudication, map §9 and surroundings, guide §7, all four schemas, the
lint, the fixtures, the feasibility note with addendum). The schema sketch
in §8 is not prose-shaped JSON: it was checked empirically in a session
scratchpad — valid JSON Schema 2020-12 against the repo's `common.schema.json`
registry, a happy fixture validating, and twenty adversarial negative
fixtures all caught. One of those twenty caught a hole in my own first
draft (`version: "latest"` matched the pin pattern), which is the
project's own F-9b lesson landing on this document.

---

## 0. Position in one screen

1. **Canonicalization** forces a schema in which the canonicalizer has
   nothing left to decide: required scalars, collections present iff
   non-empty, maps keyed by identity instead of sorted arrays, no null, no
   empty string, no floats, one pattern-locked spelling for every
   machine-readable value, no prose, no release stamp. The goal file is
   content-addressed; identical state is identical bytes across releases.
2. **Entry identity**: the id is the *promiser* — the device-natural name
   the convergent engine addresses (launchd label, absolute path, package
   name) — never the Site Model name, never content-derived (keys
   excepted, where content *is* identity). A rename then honestly *is*
   remove+add, because that is the actuation; "renamed" is a display
   pairing the device itself can verify, not a hunk type.
3. **Coverage**: entries nest *under* their domain's coverage declaration,
   so an entry without a stated coverage is unrepresentable, and
   `deliberately-unmanaged`-with-entries is unrepresentable. Coverage is
   one enum, not common's boolean+reason pair. The escape hatch
   (reclassification) stays possible but becomes loud, countable, and —
   my recommendation — ceremony-classed on retreat.
4. **Versioning**: `schema_version` is a `const` in each schema revision;
   under `additionalProperties: false` + fail-closed, *every* additive
   change is a bump, by design. The report-row fix: add a **required
   `schema_ceiling`** to the `device_convergence` row **now**, while zero
   writers exist.
5. **Privileged regions**: one reserved, required, const-comprehensive
   `device-trust` domain holds most of the floor list, the validator reads
   its own configuration only from there (misfiled trust content is inert),
   privilege is derived against the **baseline**, and the day-one path
   list is compiled into the validator, not data.
6. **Fetched content**: a `content` object that is deterministically
   inline xor fetched, digest and size required, re-verified before apply.
   Package bytes are delegated to the package manager's own verification
   chain — a scoped, stated delegation, not coverage.
7. **The open question**: the goal file is **not** the Augments JSON. It
   is a tendcf-owned schema, and `host_specific.json` is a **device-side
   projection** of the approved goal file by a deliberately dumb projector
   inside tendcf-agent. The Augments file never appears on the wire.

The adjudication is binding and mostly right. I depart from it in eight
places (§13), two of which I consider genuine internal inconsistencies of
the same class as the one it already confirmed: the "verbatim
`domain_coverage`" instruction contradicts its own §5.2, and its removal
semantics, read literally, contradict its own §5.1. The single largest
thing this pass adds is **tombstones** (`state: "absent"` as goal-file
state), which is what makes removals convergent instead of diff-driven.

---

## 1. Canonicalization: what refuse-never-normalize forces on the schema

The validator's byte-identity check (`bytes == canonicalize(bytes)`) is
what enforces canonical form. The schema cannot state that check. What the
schema *can* do — and therefore must do — is leave the canonicalizer
nothing to decide. Every place a schema tolerates two spellings of one
meaning becomes either a camouflage channel or an extra rule the
canonicalizer must hold; both are costs, and the second is the subtler
one, because every extra canonicalization rule is code inside the trusted
comparator. So the design goal is: **minimize the rule set that lives
outside JCS.**

Concretely:

- **Required scalars, present-iff-non-empty collections.** "No defaults"
  means every scalar field is `required` with its explicit value. "Empty
  collections are invalid; omission is the only spelling of none" means
  every collection is *optional* with `minItems`/`minProperties: 1`.
  These two rules together are the whole absent-vs-empty story, and the
  sketch applies them uniformly.
- **Maps keyed by identity, not arrays sorted by a declared key.** This
  is a deliberate deviation from the *letter* of E1 §5.2 ("every
  set-semantics collection is an array sorted by a schema-declared key")
  in service of its *purpose*. With `entries` as nested maps
  (`domain → kind → id → entry`), RFC 8785's own member ordering *is* the
  entry ordering; id uniqueness is structural rather than lint-checked;
  the hunk address is a JSON Pointer; and the canonicalizer sheds the
  "arrays sorted by composite key" rule entirely. One string-set array
  survives (`verbs`, sorted ascending by code point — a single named
  rule); `command` stays an array because argv order is meaning. If the
  reconciliation pass holds E1's letter, everything in this opinion
  survives translation to sorted arrays — the addressing is isomorphic —
  at the price of two extra canonicalizer rules and a lint sortedness
  check. I recommend the maps.
- **No null anywhere, no empty strings** (`minLength: 1` on every free
  string), **no floats**. On floats, note the enforcement is *joint*:
  JSON Schema's `integer` accepts `15.0` (zero-fraction numbers pass),
  but JCS serializes `15.0` as `15`, so the byte-identity check refuses
  the file. Schema types catch true fractions; byte identity catches
  float spellings of integers. Neither alone suffices — worth a negative
  fixture each.
- **One spelling per value class, pattern-locked:** file modes are
  exactly four octal digits (`"0644"`, never `644`, never an integer);
  digests are `sha256:` + 64 lowercase hex; keys are `ed25519:` + 64
  lowercase hex; package versions are an exact pin **starting with a
  digit** or the literal `unpinned` — the leading-digit rule is what
  structurally excludes `latest`/`stable`/`newest` instead of
  blocklisting them (this is the hole my own first draft had and the
  test harness caught); paths are canonical-absolute (no `//`, no
  trailing `/`, no `.`/`..` segments) by regex.
- **Nothing run-varying, and that includes the release stamp.** A goal
  file carrying `release:` would make every re-release of identical
  state a spurious hunk. Exclude it: the TUF targets metadata binds
  release → goal-file hash, the goal file is content-addressed, and
  identical intended state across releases is identical bytes — so a
  device receiving a re-release sees `H(old) == H(new)` and no ceremony.
  That is a feature the adjudication implies but never states.
- **No prose.** Descriptions and notes are the intent channel, and DC-3
  keeps intent out of the verifiable layer. Signed prose in the consent
  artifact would also make wording edits into hunks. Domain descriptions,
  service descriptions, interlock descriptions all stay in the Site
  Model and the briefing.
- **Byte-level definition, written down once:** the canonical encoding is
  the JCS serialization of the value, UTF-8, **no trailing newline**;
  hashes are over exactly those bytes. (Consequence: the `.json` fixture
  will trip no-newline-at-EOF linters; exempt it consciously.) The
  parser must **reject duplicate object keys** — Python's `json.loads`
  silently last-wins, so the implementation needs `object_pairs_hook`;
  and `json.dumps(sort_keys=True)` is *not* JCS for non-BMP strings
  (code-point vs UTF-16 code-unit order). Use a real RFC 8785
  implementation. NFC is checked by the validator; the schema keeps most
  strings inside ASCII patterns so the NFC rule has a small blast radius.

What the schema cannot make unrepresentable, the lint must fixture:
non-canonical key order, trailing newline, duplicate keys, NFC
violations. Those fixtures must be **raw `.json` bytes**, which the
current YAML-overlay broken-fixture mechanism cannot carry — see §11.

## 2. Entry identity: the id is the promiser

**What makes a stable id:** it is authored (or fixed by the world), never
generated, and it is the *device-natural* name — the string by which the
convergent engine will address the thing. In CFEngine terms, the
promiser: the launchd label for a launchd service, the systemd unit name,
the absolute path for a file, the package name for a package. The sketch
pins a per-kind id pattern via `propertyNames`.

Two consequences, both load-bearing:

- **The Site Model `name` field does not appear in the goal file.** It is
  a source-layer concept, and E1 §5.5's third reason applies to it
  verbatim: carrying it would make semantically identical device states
  byte-different when sources are refactored. This is an application of
  the no-attribution rule the adjudication did not notice it had already
  committed to. Mapping a hunk back to the source record is
  `explain-hunk`'s job, in the untrusted channel.
- **A "modify" in the diff corresponds to a modify in actuation, and a
  remove+add corresponds to a remove+add.** This is the honest answer to
  the rename question. At the device there are no renames: a service
  moving from label `com.x.a` to `com.x.b` is genuinely unload-old +
  load-new; a file moving paths is genuinely delete + create. CFEngine
  has no rename primitive. So the authoritative diff *should* present
  the pair, because the pair is what will happen. What rescues the
  person from "a scary pair of unrelated changes" is that under E1 §5.1
  the device holds *both full entries*: the presentation layer can pair
  a remove and an add whose bodies are equal (modulo id) and render
  "replaced under a new name — actuation: remove old, create new" with
  **device-verified** confidence. No proposer assertion, no hunk type,
  no format field. Rename detection is briefing-layer work (Step 9) over
  data the validator already possesses.

Exception that proves the rule: for `advisor-key` entries the id *is* the
key material, because for keys content is identity. Rotation is then
remove+add — which is, again, the honest actuation of a rotation.

Two obligations elsewhere: schema **migration functions must be
id-stable**, or §5.4's empty-diff rule breaks for reasons invisible to
the person; and path aliasing (two spellings of one inode via symlinks)
cannot be excluded textually — the conflict check catches textual
duplicates only. New residue, §14.

## 3. Coverage: representable states are exactly the meaningful ones

The sketch nests `entries` *inside* each domain object, whose `coverage`
field is required. That single structural choice does most of the work
E1 §5.7 asks for:

- An entry cannot exist without its domain's coverage being stated —
  "silence means two things, and the file says which" becomes
  unrepresentable to violate, not a discipline.
- `coverage` is **one enum** (`comprehensive` / `not-yet-migrated` /
  `deliberately-unmanaged`), not common's `comprehensive` boolean +
  `opt_out_reason` pair. The pair needs if/then machinery to forbid its
  own contradictions; one field has no contradictions to forbid. (Why
  the common `$def` cannot be reused verbatim: §13, D-2.)
- `deliberately-unmanaged` with entries is schema-invalid: "not ours to
  describe," with descriptions in it, is a contradiction.
  `not-yet-migrated` **may** carry entries — that is what a domain
  mid-migration looks like (describe entries one by one, then flip to
  comprehensive), and forbidding it would force migrations to be one big
  flip, which is the total-diff shape §5.4 exists to avoid.
- A domain absent from the map is **unclaimed** — a third silence class
  the adjudication does not name. It is semantically
  not-yet-migrated-without-a-name; you cannot force enumeration of the
  unbounded unknown, and declaring the domain is precisely the act of
  naming a backlog item so it becomes countable. The diff schema handles
  it: `coverage_changes` admits `"undeclared"` as an old value, so a
  domain's first appearance is itself a reviewable transition.

Where is the escape hatch? Exactly where map §16 Q8 says: reclassifying
comprehensive → not-yet-migrated to get a change out. The schema cannot
forbid that and should not try (it is sometimes the true state). It can
make it loud: the transition is a `coverage_changes` item in the diff, in
a distinct section the briefing cannot fold into entry noise, and I
recommend the validator's ceremony-class derivation treat **coverage
retreat** (comprehensive → anything) as above-ordinary. E1 §5.7 already
calls reclassification "a distinct review class" without operationalizing
it; §9.8's ceremony-class derivation is where review classes are
operationalized; connect the two (§13, D-7).

## 4. Versioning: everything additive is a bump, and that is the point

- `schema_version` is a **`const`** in each schema revision. A version-2
  file fails the version-1 schema structurally; the validator reads the
  version first and reports `version-above-ceiling` distinctly from
  `schema-invalid`, but even a validator that forgot to dispatch fails
  closed. Unknown kinds are closed off by enumerated `properties` +
  `additionalProperties: false` at the kind level — the belt-and-braces
  E1 asks for, at zero marginal cost.
- Be plain about the consequence the adjudication understates: under
  `additionalProperties: false` and fail-closed refusal, **any additive
  field is as breaking as a new kind** — an old validator will refuse a
  file containing it. So the bump rule is not "kind-set changes bump"; it
  is *every* shape change bumps, and each bump is a two-phase ship plus a
  migration release. Schema churn is expensive **by design**; map §16
  Q11's migration counter is the meter, and v1 should therefore carry
  exactly the kinds Steps 1–6 actuate (four state kinds + four trust
  kinds in the sketch) and no speculative surface.
- **One `schema_version` for the family.** Goal file, goal diff, and
  approval record version together. Three independent version axes for
  one builder is a compatibility matrix nobody will maintain; the diff
  and approval record embed goal-file entries anyway.
- **The report-row correction, made concrete** (the brief's hard part 4):
  the `device_convergence` row gains a **required** field:

  ```jsonc
  "schema_ceiling": {
    "description": "Highest goal-file schema_version this device's
      validator can fully interpret. What D44's per-host render rule
      reads; absent history means 'render at the version enrolled at
      first adoption'.",
    "type": "integer", "minimum": 1
  }
  ```

  Add it **now**. The report-row schema's own description says it is
  settled early precisely because "one column now" beats "a migration
  later," and today there are zero writers, so a required column is
  free. (An optional `validator_build` string for diagnostics is
  harmless; the required datum is the ceiling.) This also fills a hole
  E1 §5.6 leaves open: the render rule needs a defined default for a
  host that has *never* reported — use the version enrolled at that
  host's first-adoption ceremony, which the compiler side knows.
- **Cut the separate release-lint phase-order check.** "Compiler refuses
  to render version N for a host whose reported ceiling is < N" *is* the
  two-phase enforcement, in the one place the knowledge lives. A second
  check in release lint re-states the same rule; keep one.
- The migration empty-diff rule needs the precision the diff schema
  gives it: a version bump is a **header change** (`version_bump` in the
  diff), not a hunk; a migration release is valid iff `hunks` is absent
  and `version_bump` is the only change. "Empty apart from the bump" is
  then a mechanical predicate, not a judgment.

## 5. Privileged regions: one address for most of the floor

The list is validator-held; the file carries no flags. The file's
structure can still make the list short, and short is what keeps R1 from
becoming vocabulary-shaped:

- **A reserved `device-trust` domain, required and const-comprehensive.**
  Trust policy, advisor keys, peer allowlist, policy-tree digest live
  there as ordinary entries of trust kinds, so most of §9.8's floor is
  the single derivation rule "any hunk under `device-trust`", plus the
  header (`schema_version`, `host` — touched only by migration and
  never, respectively).
- **Self-referential consumption is the enforcement trick:** the
  validator and agent read their own configuration *only* from
  `device-trust`. Trust content misfiled anywhere else is not smuggled —
  it is inert, because nothing reads it. The schema helps by making the
  trust kinds structurally inexpressible outside the trust domain
  (`state_entries` and `trust_entries` are disjoint kind sets).
- **What the domain cannot absorb keeps the list from being one line:**
  the validator/agent and CFEngine arrive as *package* and *file* entries
  in ordinary domains. Those are privileged by promiser, not by path
  shape — a short compiled-in list of addresses (`package:tendcf-agent`,
  `package:cfengine`, the agent's own config path). The structure makes
  the list short; nothing makes it empty. That is R1 carried, not
  closed.
- **Privilege is derived against the *baseline's* structure, not the
  proposal's.** Otherwise one diff could rewrite the rules and enjoy the
  rewrite in the same approval. The adjudication never states this
  ordering; it belongs in the validator spec and in §14.2's review
  target 3.
- **Day one, the list is compiled into the validator binary** and
  changes ride the agent-update path, which is already privileged
  (TC-25 class). A list-as-baseline-data design (self-referentially
  reviewable) is elegant and deferrable; see the cut list.
- **The policy-tree digest is schema-required** (`policy-tree` kind,
  non-empty, inside `device-trust`): a goal file without it is invalid.
  That pays R8's schema half on day one — the generic bundle and any
  `.cf` beside it are bound as bytes into what was approved. The other
  half (verify baseline first, verify tree at load) is validator work
  and remains residue; and the digest binds *which code*, not *what the
  code does* — TC-23/TC-24 stay open exactly as §9.10 says.

## 6. Fetched content: bind bytes, and say which bytes you cannot bind

File content is a `content` object, exactly one of:

- `{"inline": "<utf-8 text>"}` — bounded (4 KiB in the sketch);
- `{"fetch": {"source", "sha256", "size_bytes"}}` — all three required,
  digest re-verified immediately before apply (DC-11; the accept covers
  it because the digest is inside the signed file).

The subtlety is that inline-vs-fetch is itself a two-spellings channel:
the same bytes representable both ways would make one meaning two
representations. The fix is a **deterministic choice rule** — valid
UTF-8 text at or under the cap MUST be inline, everything else MUST be
fetched — enforced by compiler and lint. The schema bounds the inline
form; the iff-rule lives in lint (schema cannot see bytes).

**Packages are a stated delegation, not a coverage claim.** The goal
file pins `(manager, name, exact version)`; the bytes are verified by
apt's/brew's own signed chains. Putting per-package digests in the goal
file would fight arch variance and repo churn for little gain, because
TC-23 already concedes the maintainer scripts run as root regardless of
who verified the bytes. This is a scoped position a reviewer may attack;
it should be attacked at §14.2 rather than silently assumed either way.
The strict-DC-11 reading ("every fetched artifact" includes packages) is
the honest alternative; it costs a resolver that pins digests per
arch×repo×version, which I judge not affordable now (§12).

## 7. The open question: projection, and the projector lives on the device

**Position: the goal file is not the Augments JSON. It is a tendcf-owned
schema; `host_specific.json` is derived from the approved goal file, on
the device, by a small deterministic projector inside tendcf-agent; the
Augments file never appears on the wire.** CFEngine 3.18 remains the
floor — the projection targets `host_specific.json`, and the project
established by running the software that only 3.18+ parses it.

Why not "same artifact":

1. **Model B's coverage argument requires tendcf to own the format.**
   "Compiler and validator share one schema and fail together" is only
   true if the schema authority is one project. The Augments format is
   CFEngine's: its meaning moves with the engine (`host_specific.json`
   acquiring parsing at 3.18 is itself the proof), so a goal file *in*
   that format has semantics fixed by `(schema_version, engine version)`
   — a two-variable consent object. The goal file's meaning must be
   fixed by `schema_version` alone.
2. **Augments carries engine-semantic escape hatches.** `inputs` loads
   policy files; `classes` defines class expressions. A consent artifact
   in that format must forbid those keys, at which point it is a
   restricted subset of someone else's format — their evolution, our
   restrictions, and every CFEngine upgrade a potential forced
   schema_version bump. Subsetting a foreign format is the worst of both
   options.
3. **The consent machinery has no Augments spelling.** Header, host key,
   coverage declarations, tombstones, trust entries, digests — all of it
   would ride as inert `vars`, i.e. a tendcf schema wearing an Augments
   costume, with cf-agent materializing consent metadata as runtime
   variables for no reason.

Why the projector must run **device-side, after approval**: if the
compiler shipped both artifacts, the engine's actual input would be the
one the validator never checked — a gap between the approved object and
the applied object, which is the exact property Model B exists to
deliver. Deriving on-device closes it: nothing reaches cf-agent that was
not computed from the approved file by device-held code. The projector
joins the validator in the trusted base (both already on the privileged
list as the agent binary), and the compiler emits the same projection as
a CI artifact so golden tests can compare the two — the same
cross-check-and-flag pattern as §9.1's diff equality.

What keeps this from quietly rebuilding Model A's interpreter: **the
projector must be policy-free**, a structural re-keying (entries →
`nix2cf_services`-style containers, tombstones → the negative-promise
lists the generic bundle iterates, trust entries → the validator's own
config). That is achievable only because entry bodies are already
engine-facing (§2) — the compiler resolved all semantics upstream.
**Tripwire, and it belongs in the §14.2 review:** any projector change
that inspects entry *values* to decide output *structure* is the
interpreter returning, and should be treated the way E1 treats
label-widening.

The strongest case against this position: it adds a component to the
device trusted base, its "dumbness" is a discipline rather than a
theorem, and on Android the projector inherits §8's ownership problem
(the agent must write where cf-agent reads, across the Termux/APK UID
boundary — the same awkward case as R10's baseline storage). I hold the
position because every alternative is worse in kind, not degree: "same
artifact" gives up format authority (reason 1 is decisive on its own);
"compiler ships both" gives up the approved-equals-applied property,
which is the verdict's core.

---

## 8. The sketch

Empirically validated as described in the header. Omissions are named
after the listing. This is `schema_version: 1` = what Steps 1–6 actuate:
services, files, packages, interlocks, and the trust kinds — nothing
speculative.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/frdminc/tendcf/schema/goal-file.schema.json",
  "title": "Goal file — canonical per-host intended state (D43/D44)",
  "description": "SKETCH from goal-file-schema-opinion-fable.md, not the landed schema. One fully resolved JSON document per host: compiler output, consent object, validator input (guide §7, map §9). Canonical form is RFC 8785 plus the rules in the opinion; the validator refuses any file not byte-identical to the canonicalization of itself. No defaults anywhere; scalars are required, collections are present iff non-empty; entries are maps keyed by device-natural id so JCS key ordering IS the entry ordering.",

  "type": "object",
  "properties": {
    "schema_version": {
      "description": "Goal-file family version. Stricter than contract_version: ANY change to the kind set or any field set, additive included, bumps it (E1 §5.6). A const, so a file claiming any other version fails this schema structurally; the validator dispatches on the value before validating and reports version-above-ceiling distinctly.",
      "const": 1
    },
    "host": {
      "description": "Device public key — host identity is the key, not the hostname (map §3). First-line cross-device replay check (TC-11): a validator refuses a goal file whose host is not itself before computing any diff. Single spelling: lowercase hex, fixed prefix.",
      "type": "string",
      "pattern": "^ed25519:[0-9a-f]{64}$"
    },
    "domains": {
      "description": "Every domain this file makes claims about, each with its coverage stated. An entry cannot exist without its domain's coverage: 'silent because unchanged' vs 'silent because not described' is decided structurally (E1 §5.7). A domain absent from this map is unclaimed — semantically not-yet-migrated without a name; declaring it is the act of naming the backlog item. device-trust is always present and always comprehensive.",
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
      "description": "One enum, not common.schema.json's boolean+reason pair: the goal file admits no defaults and no second spelling of one meaning (E1 §5.2), and a single field makes the boolean/reason contradiction unrepresentable instead of if/then-guarded. Same three meanings as domain_coverage; the Site Model keeps its authoring shape and the compiler resolves to this one. No prose fields: signed prose is the intent channel DC-3 keeps out of the verifiable layer.",
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
      "description": "kind -> id -> entry. Kinds are a closed set per schema_version: an unknown kind is a structural violation, the belt-and-braces half of fail-closed (E1 §5.6). Maps rather than sorted arrays: id uniqueness is structural, JCS gives the ordering, and the canonicalizer holds fewer rules (opinion, hard part 1).",
      "type": "object",
      "properties": {
        "service": { "$ref": "#/$defs/service_map" },
        "file": { "$ref": "#/$defs/file_map" },
        "package": { "$ref": "#/$defs/package_map" },
        "interlock": { "$ref": "#/$defs/interlock_map" }
      },
      "additionalProperties": false,
      "minProperties": 1
    },

    "absent": {
      "description": "A tombstone: this thing must not exist, converged on every run. Removal is a state, not an event — the negative promise renders from THIS file, so it survives crashes, re-runs, and identical re-releases, which a diff-driven removal does not (opinion, disagreement D-3). state is the only field: absent-with-a-stale-body would be a second spelling of absence.",
      "type": "object",
      "properties": { "state": { "const": "absent" } },
      "required": ["state"],
      "additionalProperties": false
    },

    "service_map": {
      "type": "object",
      "propertyNames": {
        "description": "The device-natural unit name — the promiser: launchd label, systemd unit, runit service dir. Not the Site Model service name, which is a source-layer concept (opinion, hard part 2). Modify-vs-remove+add in the diff then matches modify-vs-unload+load in actuation.",
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
          "description": "Re-verification scope and interlock blast radius (D16(c)). Cross-checked by lint: every interlock's bundle is used by at least one entry.",
          "$ref": "common.schema.json#/$defs/identifier"
        },
        "run_as": { "type": "string", "pattern": "^[a-z_][a-z0-9_-]*$", "maxLength": 32 },
        "command": {
          "description": "argv. An array because order is meaning — the only collections that stay arrays.",
          "type": "array",
          "items": { "type": "string", "minLength": 1 },
          "minItems": 1
        },
        "env": {
          "description": "Secret NAMES only, resolved by secretspec at run time — reused verbatim from common because env_map is already canonical-safe (no defaults, no optional booleans).",
          "$ref": "common.schema.json#/$defs/env_map",
          "minProperties": 1
        },
        "working_dir": { "$ref": "#/$defs/abs_path" },
        "unit": { "$ref": "#/$defs/unit" }
      },
      "required": ["state", "bundle", "run_as", "command", "unit"],
      "additionalProperties": false
    },

    "unit": {
      "description": "Exactly one supervisor rendering, fully resolved: every knob the adapter renders is present with its explicit value — run_at_load has no default here because the schema defines none (E1 §5.2). The unit's name is the entry id and is NOT repeated in the body: one source of identity. Growing any flavor's field set is a schema_version bump by the strict rule.",
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

    "file_map": {
      "type": "object",
      "propertyNames": { "$ref": "#/$defs/abs_path" },
      "additionalProperties": {
        "oneOf": [
          { "$ref": "#/$defs/file_present" },
          { "$ref": "#/$defs/absent" }
        ]
      },
      "minProperties": 1
    },

    "file_present": {
      "description": "A regular file. Directories, symlinks, ACLs, and xattrs are named omissions of v1 (opinion §8).",
      "type": "object",
      "properties": {
        "state": { "const": "present" },
        "bundle": { "$ref": "common.schema.json#/$defs/identifier" },
        "owner": { "type": "string", "pattern": "^[a-z_][a-z0-9_-]*$", "maxLength": 32 },
        "group": { "type": "string", "pattern": "^[a-z_][a-z0-9_-]*$", "maxLength": 32 },
        "mode": {
          "description": "Exactly four octal digits, zero-padded ('0644', '4755'). One spelling: no integer form, no variable width, no '0o' prefix.",
          "type": "string",
          "pattern": "^[0-7]{4}$"
        },
        "content": { "$ref": "#/$defs/content" }
      },
      "required": ["state", "bundle", "owner", "group", "mode", "content"],
      "additionalProperties": false
    },

    "content": {
      "description": "Exactly one of inline text or fetched bytes, and WHICH is not the compiler's mood: valid UTF-8 text up to the inline cap MUST be inline, everything else MUST be fetched — a deterministic rule, so one file content has one representation (opinion, hard part 1). Fetched binds bytes, not names: the digest is part of what was approved and is re-verified immediately before apply (DC-11, R12).",
      "oneOf": [
        {
          "type": "object",
          "properties": {
            "inline": { "type": "string", "maxLength": 4096 }
          },
          "required": ["inline"],
          "additionalProperties": false
        },
        {
          "type": "object",
          "properties": {
            "fetch": {
              "type": "object",
              "properties": {
                "source": { "type": "string", "minLength": 1, "maxLength": 2048 },
                "sha256": { "$ref": "#/$defs/sha256" },
                "size_bytes": { "type": "integer", "minimum": 0, "maximum": 9007199254740991 }
              },
              "required": ["source", "sha256", "size_bytes"],
              "additionalProperties": false
            }
          },
          "required": ["fetch"],
          "additionalProperties": false
        }
      ]
    },

    "package_map": {
      "type": "object",
      "propertyNames": {
        "type": "string",
        "pattern": "^[A-Za-z0-9][A-Za-z0-9.+_-]*$",
        "maxLength": 128
      },
      "additionalProperties": {
        "oneOf": [
          { "$ref": "#/$defs/package_present" },
          { "$ref": "#/$defs/absent" }
        ]
      },
      "minProperties": 1
    },

    "package_present": {
      "type": "object",
      "properties": {
        "state": { "const": "present" },
        "manager": { "enum": ["apt", "brew", "termux-pkg"] },
        "version": {
          "description": "An exact pin, or the literal 'unpinned' as an explicit, reviewable choice. Ranges and 'latest' are banned: they resolve differently on different days, which is a run-varying field wearing a version string (E1 §5.2). A pin must start with a digit — that is what structurally excludes 'latest', 'stable', 'newest' rather than blocklisting them; the compiler strips any leading 'v'. Consequence, accepted: an upgrade is a change, and a change is approved.",
          "type": "string",
          "pattern": "^(unpinned|[0-9][A-Za-z0-9:.+~_-]*)$",
          "maxLength": 128
        }
      },
      "required": ["state", "manager", "version"],
      "additionalProperties": false
    },

    "interlock_map": {
      "type": "object",
      "propertyNames": { "$ref": "common.schema.json#/$defs/identifier" },
      "additionalProperties": { "$ref": "#/$defs/interlock_entry" },
      "minProperties": 1
    },

    "interlock_entry": {
      "description": "Same semantics as common.schema.json#/$defs/interlock, restated canonical-form: expect_exit and timeout_seconds lose their defaults and become required; description prose stays in the Site Model. blocks and report stay consts — a proposer cannot narrow the blast radius or silence the report by construction. Present-only: an interlock has no device-state footprint to tombstone; deleting one is a remove hunk the briefing must render as 'guard removed'.",
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

    "trust_domain": {
      "description": "The privileged region as one reserved, always-present, always-comprehensive domain. The validator's privilege derivation starts as 'any hunk under device-trust', plus the header, plus the short compiled-in promiser list for gate machinery living in ordinary domains (opinion, hard part 5). The validator reads its own configuration ONLY from here, so trust content misfiled elsewhere is inert, not covert.",
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
            "peer-grant": { "$ref": "#/$defs/peer_grant_map" }
          },
          "required": ["policy-tree", "trust-policy"],
          "additionalProperties": false
        }
      },
      "required": ["coverage", "entries"],
      "additionalProperties": false
    },

    "policy_tree_map": {
      "description": "R8 paid at the schema layer: a goal file without a policy-tree digest is invalid, so the generic bundle and any .cf alongside it are bound — as bytes — into what the person approved. Verification order (baseline first, tree at load) is validator work and stays residue R10-adjacent.",
      "type": "object",
      "propertyNames": { "$ref": "common.schema.json#/$defs/identifier" },
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
      "description": "id IS the key: for keys, the content is the identity, so rotation is remove+add — which is the honest actuation, not a scary artifact of it. state 'absent' is a revocation tombstone.",
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

    "peer_grant_map": {
      "description": "Target-side peer allowlist (map §10): who may act on this device, with which verbs. Prefer groups.",
      "type": "object",
      "propertyNames": {
        "type": "string",
        "pattern": "^(group:[a-z0-9][a-z0-9-]*|ed25519:[0-9a-f]{64})$"
      },
      "additionalProperties": {
        "oneOf": [
          {
            "type": "object",
            "properties": {
              "state": { "const": "present" },
              "verbs": {
                "description": "The one string-set array in the file: sorted ascending by code point, no duplicates. Sortedness is a canonicalizer rule (schema cannot state it); uniqueness is schema.",
                "type": "array",
                "items": { "$ref": "common.schema.json#/$defs/identifier" },
                "minItems": 1,
                "uniqueItems": true
              }
            },
            "required": ["state", "verbs"],
            "additionalProperties": false
          },
          { "$ref": "#/$defs/absent" }
        ]
      },
      "minProperties": 1
    },

    "abs_path": {
      "description": "Canonical absolute path: no '//', no trailing slash, no '.' or '..' segments — every path has one spelling. Symlink aliasing cannot be excluded textually and is a named residue.",
      "type": "string",
      "pattern": "^(?!.*/\\.\\.?(/|$))(/[^/]+)+$",
      "maxLength": 1024
    },

    "sha256": {
      "type": "string",
      "pattern": "^sha256:[0-9a-f]{64}$"
    }
  }
}
```

**Named omissions of v1** (each is a schema_version bump when it lands,
priced accordingly): directories, symlinks, ACLs, xattrs, and file
`state: running`-style activation nuance beyond the supervisor booleans;
ordering **edges** (none in the goal file — retry-until-stable is the
substrate until inference exists, and when edges do land they enter
*stripped of origin*, see §13 D-4); peer-action *definitions* (only the
target-side allowlist is trust content; the action catalog rides the
policy tree); roles (resolved away by the compiler — a role move shows
up as service entries appearing/disappearing per host, which R16 already
notes hides fleet intent); Homebrew casks vs formulae distinction; the
`termux-pkg`/runit specifics beyond a boolean. The `unit` flavor bodies
are deliberately minimal — real adapters will grow them, each growth a
counted bump; that is Q11's meter working as intended.

## 9. The other two family members, in outline

Both share the family `schema_version` and reuse the goal file's entry
`$defs`. These are outlines, not tested sketches; the goal file is the
load-bearing artifact and the brief's focus.

**`goal-diff.schema.json`** — device-computed authority, compiler-side
preview, CI golden artifact. Canonical too (JCS + the same rules), since
§9.1's "device diff MUST equal compiler diff" is only checkable as byte
or hash equality of a canonical form:

```jsonc
{
  "schema_version": 1,              // const
  "host": "ed25519:…",
  "baseline_sha256": "sha256:…",    // H(old canonical goal file)
  "proposed_sha256": "sha256:…",    // H(new canonical goal file)
  "version_bump": {"old": 1, "new": 2},   // present iff migration; the ONLY
                                          // header change a diff can carry
  "coverage_changes": {             // present iff non-empty; distinct section:
    "<domain>": {"old": "undeclared" /* or a coverage value */, "new": "…"}
  },
  "hunks": {                        // present iff non-empty; mirrors the file:
    "<domain>": { "<kind>": { "<id>": {
      "old": { /* full old entry */ },   // at least one of old/new;
      "new": { /* full new entry */ }    // no "op" field — presence IS the op,
    }}}                                  // a second spelling otherwise.
  }
  // No attribution, no groups, no privilege flags (E1 §5.5, §9.8).
}
```

An empty diff is **no diff document** (hash equality short-circuits). A
migration diff is `version_bump` present and `hunks`/`coverage_changes`
absent — §5.4's "empty apart from the bump" as a mechanical predicate.
The diff never ships in a release; it exists as a preview/CI/annotation
format and as the thing whose hash the cross-check compares.

**`approval-record.schema.json`** — the signed object is the JCS bytes of
the record with the `signature` member removed; this replaces §5.1's
hash-concatenation formula, which has an ambiguity hazard around its
optional briefing-hash member (§13, D-5). Fields: `schema_version`,
`host` (target key), `baseline_sha256` (absent only at first adoption —
the no-baseline case is a named §14.2 review target, TC-11/TC-20
territory), `proposed_sha256`, `nonce` (device-issued), `approval_seq`
(monotonic, DC-2 single-use), optional `briefing_sha256`, `verdict`
(`accept` | `reject` | `withdraw`), `refused` (hunk addresses, present
iff reject, annotation only), `ceremony_class`
(`ordinary` | `privileged` | `baseline` — asserted by the approver,
checked by the validator against its *derived* requirement), `signature`
(key id + signature). The fixture set must include a reject-with-
annotations and a wrong-ceremony-class negative, per E1 §8.

## 10. Lint and fixture extensions

Beyond E1 §8's list (which stands):

- **A byte-level fixture class.** The broken-fixture mechanism today
  parses YAML overlays; canonicalization fixtures are meaningless after
  a parse. Goal-file fixtures — happy and broken — must be raw `.json`
  bytes, compared and rejected at the byte layer: wrong key order,
  trailing newline, duplicate keys (needs `object_pairs_hook`; Python's
  default parser silently last-wins), non-NFC strings, `15.0` spellings.
- The happy fixture **is** the canonicalization test (E1 §8 says this;
  the byte-class point above is what makes it executable), and it is
  exempt from newline-at-EOF conventions by decision.
- Cross-file rules: every interlock's `bundle` is used by ≥ 1 entry;
  inline/fetch cap rule (§6); goal-file/goal-diff fixture consistency
  (applying the hunks to old yields new — E1 §8's "hunk/file
  inconsistency" fixture).
- The sketch's own twenty negative cases (fail-closed version, unknown
  kind, tombstone-with-body, entries under deliberately-unmanaged,
  missing/non-comprehensive device-trust, missing policy-tree digest,
  three-digit mode, `latest` version, empty collections, silenced
  interlock report, defaulted `expect_exit`, dot-dot path, float,
  uppercase key, missing launchd knob, embedded release stamp,
  boolean+reason coverage spelling, digestless fetch) are a floor to
  carry into `examples/broken/` when the schema lands; `EXPECTED_BROKEN`
  bumps accordingly.

## 11. What I would cut

The binding constraint is one unfunded builder. In descending order of
saved effort:

1. **Multi-version render.** Until schema_version 2 exists there is
   nothing to multi-render. Ship the `schema_ceiling` report column now
   (free), the render-refusal rule now (one `if`), and build
   version-window rendering when v2 is actually approaching. Fail-closed
   protects the gap: worst case a stale device stalls visibly.
2. **Approval-record runtime.** Step 6 is operator hosts, push-only, no
   advisor. Write the schema now — §14.2 reviews the *family*, and the
   privileged/baseline ceremony shapes must be reviewed before the
   validator is coded — but build no signing/verification runtime until
   Step 9.
3. **The strict-DC-11 package resolver** (per-package digests across
   arch×repo×version). Delegate to the manager chains, state the
   delegation (§6), revisit if a §14.2 reviewer breaks the delegation
   argument.
4. **The baseline-data privileged list.** Compile the list into the
   validator. A self-referential list-as-data design is strictly later.
5. **Ordering edges in the goal file.** None in v1. CFEngine's
   substrate carries Steps 1–6; inference output stays a compiler
   artifact until D16's own two-platform gate, and its goal-file entry
   (origin-stripped) is a future bump.
6. **Rename pairing, display grouping, `explain-hunk`.** All Step 9
   briefing-layer, none in the format (E1 already says this for the
   latter two; §2 extends it to renames). Nothing here blocks Step 6.
7. **The separate release-lint phase-order check** — subsumed by the
   compiler's render-refusal rule (§4).
8. **Never build:** a generic extension/`x-*` field ("for
   forward-compatibility") — that is ignore-unknown reborn inside the
   schema; YAML anywhere on the wire; semver strings for
   `schema_version`; content-hash entry ids; privilege or provenance
   flags in any family member.

What I would **not** cut, though it is the newest cost this opinion
introduces: tombstones (§13 D-3 — they are what keeps removals
convergent) and the device-side projector (§7 — the alternatives forfeit
either format authority or approved-equals-applied).

## 12. Disagreement register: where the adjudication is wrong or under-specified

The brief asks for surviving disagreement. D-2 and D-3 are, in my
judgment, internal inconsistencies of the same class E1's own §4 D1
found in the prior pass — format details colliding with the
canonicalization rules the same document decided. The rest are holes or
frictions, not errors.

- **D-1 (confirmed error, extended).** Report rows carry no agent state;
  the brief already establishes this. My addition is the concrete fix
  and its timing: required `schema_ceiling` on `device_convergence`,
  added **now** while zero writers exist (§4), plus the defined default
  for never-reported hosts (first-adoption version) that E1 §5.6's
  render rule silently needs.
- **D-2. §5.7's "verbatim from `common.schema.json#/$defs/domain_coverage`"
  contradicts §5.2.** That `$def` has a `default` (`comprehensive:
  true`), an optional boolean (absent-vs-present-true: two spellings of
  one meaning), free-prose `description`/`note` fields (signed intent
  prose in the consent artifact, against DC-3's separation), and if/then
  contradiction guards a canonical form doesn't need. "Verbatim" and "no
  defaults" cannot both hold. Resolution: same three *semantics*,
  goal-file-local single-enum `$def` (§3). Corollary: E1 §8's "reuse the
  existing `$defs`" needs qualifying — only canonical-safe defs
  (`identifier`, `host_name`, `env_map`) are reusable as-is; composite
  defs with defaults (`domain_coverage`, `interlock`) must be restated.
- **D-3. The removal decision, read literally, contradicts §5.1 and
  breaks convergence.** R4/D2 says every remove-hunk "compiles to
  explicit negative promises" — but compiled *from what, persisted
  where*? If the negative promise derives from the **diff**, then the
  applied configuration is `f(goal file, diff)`: the diff has acquired
  apply semantics beyond authorization, the applied state is no longer
  directly signed (the exact ground on which §5.1 rejected shipping the
  diff), and the removal is a one-shot imperative — a device that
  crashes mid-removal, or re-converges next week from the same goal
  file, has nothing left to re-drive it. Retry-until-stable cannot retry
  what exists only in a transient diff. The convergent resolution is
  **removal as state**: entries carry `state: present | absent`, a
  removal is a *replace* hunk (`present → absent`) whose tombstone
  persists in the goal file, and the negative promise renders from the
  file — idempotent, crash-safe, re-release-safe. Three consequences:
  (i) E1 §8's negative fixture "removal expressed as a modify" inverts —
  a removal correctly *is* a modify of `state`; (ii) the real smuggling
  hazard is the **bare entry deletion**, which means "stop managing,"
  not "remove from device" — two meanings a stateless diff conflates and
  the briefing must render distinctly ("stops being managed; the thing
  REMAINS"); (iii) tombstone lifecycle is new residue (§13a below).
- **D-4. Map §4.1 vs §9.5 collision on edge origin.** §4.1: "Edges in
  compiled output carry origin (authored with location, or inferred with
  the rule)." §9.5: attribution must not appear in the canonical
  artifact, for three sufficient reasons. If the goal file is the
  compiled output, these collide. Resolution: origin-bearing edge output
  is the *preview channel's*; the goal file carries no edges in v1 and
  origin-stripped edges if ever (§8 omissions). The map's sentence needs
  a scope note when it is next edited.
- **D-5. The §5.1 accept formula has an encoding ambiguity hazard.**
  `Sig( H(old) ‖ H(new) ‖ nonce [‖ H(briefing)] )` with an optional
  member and no framing is the kind of construction that grows
  cross-protocol confusions. The family already has a canonical
  encoding; use it: sign the JCS bytes of the approval record minus its
  `signature` member (§9). DC-2's substance — per-target validity,
  nonce, counter, persisted rejects — is unchanged; only the message
  construction is.
- **D-6. §5.6's render rule is under-specified and its lint rule is
  redundant.** No defined behavior for a host that never reported a
  ceiling (fix: first-adoption version, §4); and "release lint enforces
  the phase order" duplicates what the compiler's render-refusal rule
  already enforces in the place the knowledge lives — keep one.
- **D-7. Coverage retreat is named but not operationalized.** §5.7 calls
  reclassification "a distinct review class"; the ceremony-class
  machinery in §9.8 is where review classes bind; nothing connects them.
  Recommend: comprehensive→anything transitions derive an
  above-ordinary ceremony class (§3). Friendly amendment, not error.
- **D-8. "Entries by `(domain, kind, id)` as sorted arrays" is the
  letter I deviate from** (§1): nested maps achieve §5.2's stated
  purpose with a strictly smaller trusted rule set. Flagged prominently
  because it is a deviation from a closed decision, argued on that
  decision's own criterion, and reversible mechanically if the
  reconciliation holds the letter.

## 13. Residue this opinion adds (nothing above closes any of R1–R18)

- **(a) Tombstone lifecycle.** `state: absent` entries accumulate;
  dropping one is itself a change ("stop enforcing absence") and in a
  comprehensive domain re-exposes the extra-entry detector, but in a
  non-comprehensive domain it is silent. When a tombstone may be dropped
  is policy, not schema; the tombstone count per file is a counter to
  watch alongside Q10's diff sizes.
- **(b) Path aliasing.** Symlinks make two textual identities one inode;
  the schema's canonical-path pattern cannot see it; the conflict check
  catches textual duplicates only.
- **(c) Projector discipline.** The device-side projector (§7) is
  policy-free by discipline, not construction. Tripwire for §14.2 and
  for every future change: structure decisions from entry values = the
  interpreter returning. On Android it also inherits §8's UID-boundary
  ownership problem, alongside R10's baseline storage.
- **(d) The inline/fetch determinism rule** (§6) is compiler+lint
  enforced, not schema-enforced; a compiler bug here reopens a
  two-spellings channel. Negative fixture: same bytes both ways.
- **(e) First adoption has no baseline hash**; the approval record's
  no-baseline case interacts with replay (TC-11/TC-20) and belongs
  explicitly in §14.2 review target 2.
- **(f) Package bytes are delegated** (§6): the goal file binds
  `(manager, name, version)`, not bytes, for packages. Stated so nobody
  reads R12 as fully paid.

## 14. The strongest case against this opinion, stated to be acted on

Its three departures are its three exposures. **Tombstones** grow the
consent surface: every removal now produces two reviewable events
(present→absent, then the eventual tombstone drop), on a project already
watching diff fatigue (R5) — if tombstone counts climb and drops become
rubber stamps, the mechanism is spending the ceremony it was meant to
protect. **Maps-not-arrays** deviates from a closed decision; if the
other two opinions follow E1's letter, reconciliation must either
translate this design (mechanical, but work) or overrule two-of-three.
**The device-side projector** adds a trusted component whose safety is a
discipline, and puts new code on the platform (Android) where every
other hard residue (R10, §8 ownership) already lives. Each departure was
taken because the alternative fails on the adjudication's own criteria —
diff-driven removals violate §5.1's directly-signed-state argument,
sorted arrays enlarge the trusted canonicalizer §5.2 exists to shrink,
and both non-projection options forfeit either format authority or
approved-equals-applied — but all three are falsifiable at §14.2, and
the reviewer should be pointed at them by name.
