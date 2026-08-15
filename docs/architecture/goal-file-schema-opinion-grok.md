# Goal-file schema opinion

**Author:** Cursor Grok 4.6, independent cold pass, 2026-08-15.
**Brief:** `docs/architecture/GOAL-FILE-SCHEMA-BRIEF.md`.
**Binding inputs:** E1 xhigh adjudication; architecture-DEFINITIVE-v3 §9; guide §7; `schema/`, `examples/`, `bin/schema_lint.py`.
**Empirical extra:** CFEngine Core 3.27.1 (`/opt/homebrew/bin/cf-agent`) against `def.json` / `host_specific.json`. Not in the brief’s reading list; used only to settle hard part 7 with a running parser rather than the docs about it.

This note does not edit any schema, fixture, or architecture document other than itself. `schema/goal-file.schema.json` is not created. The sketch in §10 is the falsifiable artifact.

---

## 0. Position in one screen

The goal file is tendcf’s consent object: one fully-resolved, RFC 8785-canonical JSON document per host, diffed at entry granularity, fail-closed on unknown `schema_version` and unknown `kind`. It is **not** CFEngine Augments JSON. It is a **projection source**. The mutation engine consumes `$(sys.workdir)/data/host_specific.json` (CFEngine ≥ 3.18.0; that is the floor), produced by a pure projector and shipped as a TUF sibling of the goal file. `def.json` stays MPF glue and lives under the policy-tree digest, not in the per-host consent object.

That split is forced by the running parser, not by taste. Against 3.27.1:

- Unknown top-level keys in `host_specific.json` are **skipped with a warning** (`Invalid key '…', skipping it`). That is ignore-unknown, which E1 §5.6 just rejected for the validator.
- Unknown top-level keys in `def.json` are **dropped silently**. Worse.
- `vars` and `variables` are two spellings of one meaning; when both set `phone`, `variables` wins.
- Floats are legal and display-reformatted (`3.5` → `3.50`).
- YAML `def.json` is **not** accepted (`Could not parse JSON file`). The guide’s “YAML is a valid input” is false against this binary.
- The guide §16 illustrative `host_specific.json` (top-level `data` + `nix2cf_edges`) loads **nothing**. Both keys are skipped.

So identity (“the goal file *is* Augments”) either (a) puts consent fields where CFEngine will ignore them, recreating the coverage hole inside one file, or (b) stuffs the consent document under `vars` and couples generic bundles to the consent schema on every bump. Projection is the cheaper of those, and it is the only one that keeps “one meaning, one representation” as a property of a document *we* own.

Cost is the other half of the verdict. v1 of this schema is a closed, small `kind` enum, a three-valued coverage field, tombstones on actuated entries, digest-bound fetches for the two artifacts we can actually pin, and two new columns on `device_convergence`. It is not a kitchen-sink encoding of the Site Model. Most of what the Site Model carries must not appear here.

---

## 1. Canonicalization — what it forces on the schema

E1 §5.2 is right that this is a consent property, and right that JSON Schema cannot do the whole job. Split the work:

**Schema (make the illegal state unrepresentable):**

- `additionalProperties: false` on every object. No proposer-set `privileged`, `origin`, `group`, `note`, `description`, or “for forward compatibility” bags.
- No `default` keywords anywhere in *this* schema. Authoring defaults stay in the Site Model and are resolved by the compiler. Consequence: you cannot `$ref` `common.schema.json#/$defs/domain_coverage` or `#/$defs/interlock` — both carry `default` (see §8.1).
- No empty collections: a present array has `minItems: 1`; a present map has `minProperties: 1`; “none” is omission of the key. Empty string is invalid (`minLength: 1`).
- No `null`. No `number` (only `integer` and `string`). Booleans are allowed; E1 §5.2’s “integers and strings only” is slightly wrong — JCS has a canonical `true`/`false`, and coverage/launchd flags are booleans-or-enums. Where a boolean plus a second field can contradict, replace both with one enum (coverage, below).
- Closed enums, not open strings, for `kind`, coverage `mode`, `trust_tier`, digest `alg`, key `alg`, unit-writer `writer`, `presence`.
- One spelling of a digest: `alg` is the const `"sha256"`; `hex` is `^[0-9a-f]{64}$`. Not `SHA-256`, not base64, not uppercase.
- One spelling of a public key: `ed25519` + lowercase hex. Not raw vs base64 vs ssh-wire as alternatives.
- Discriminated `kind` via `oneOf` + `const`. A service object cannot carry file fields; a coverage object cannot carry `command`.
- `schema_version` is `"const": 1` in the v1 schema document. A v2 file is invalid against this schema rather than “valid with unknown bits.”

**Lint (schema cannot say these):**

- Byte-identity with RFC 8785 (JCS). Refuse, never normalize. The happy-path fixture *is* this test.
- NFC on every string before JCS. Schema cannot see normalization form.
- `entries` sorted by `(domain, kind, id)` using the same string order JCS uses (UTF-8 code points of the NFC form). JSON Schema cannot require array order by key.
- Uniqueness of `(domain, kind, id)`.
- Adapter-block presence vs `host.platform` (launchd on macos, systemd on linux, termux on android). Putting `platform` on each service as well as on `host` would be two spellings; omit it on entries and leave the check to lint, matching how `bin/schema_lint.py` already does launchd-prefix membership.

**Where two spellings still leak if we are sloppy:**

| Dual spelling | Make it unrepresentable by |
| --- | --- |
| `comprehensive: true` plus `opt_out_reason`, or `false` without one | One enum, three values; do not `$ref` `domain_coverage` |
| `vars` vs `variables` (CFEngine) | Do not use Augments as the consent document |
| Empty array vs omitted key | `minItems: 1` and key not required |
| `1` vs `"1"` vs `1.0` | `integer`, no `number` |
| Description-only edits as hunks | No `description` / `note` / `platform_notes` in the goal file (those belong to the briefing, DC-3) |
| `provides`/`requires`/`depends_on` vs resolved service | Authoring graph stays in the Site Model; the goal file has device state |
| `host.trust_tier` vs a copy inside a trust-policy blob | `trust_tier` lives in exactly one place (`/host/trust_tier`) |
| Coverage `id` equal to `domain` | Coverage `id` is the const `"declaration"`; identity is `(domain, coverage, declaration)` |
| Locator URL plus digest as competing identities for a fetch | Digest only in the goal file; retrieval is TUF’s job |

JCS itself does not sort arrays and does not NFC. Those two structural rules are why a schema-valid file can still fail canonicalization, and why lint layer 5 needs a non-canonical happy-path twin as a *negative* fixture, not only as a prose rule.

---

## 2. Entry identity

Address is `(domain, kind, id)`. That triple is the hunk key. It is not a UUID, and it is not the Site Model’s authoring name when those diverge.

**What `id` is:** the actuation key inside `(domain, kind)`.

- `coverage`: `id` is the const `"declaration"` (one per domain).
- `bundle`: Site Model bundle identifier.
- `service`: the supervisor’s unit name (launchd label / systemd unit / runit service), not the Site Model `name`. Changing `com.djbclark.caddy` to `org.tendcf.caddy` *is* unload-old-plus-load-new. Encoding that as a field change on a stable nickname would lie about actuation.
- `unit-writer`: the prefix string.
- `advisor-key`: key id (hex of the key, or a stable keyid derived from it — pick one in lint; I use 64-char lowercase hex of the raw key, matching `host.public_key_hex`, so id *is* the key).
- `peer`: the peer’s public key hex.
- `policy-tree`: const `"tree"`.
- `validator`: const `"binary"`.

**Rename is delete-plus-add.** Do not add a rename hunk type. Reasons, any one sufficient:

1. For files and units, a rename *is* two actuations (R4). A “rename” hunk would hide that.
2. Device-side diffs have no source layers; a rename is an inferred correspondence, i.e. the attribution problem E1 §5.5 just ejected from the format.
3. Two spellings of “this unit moved” (rename hunk vs remove+add) is camouflage.

The briefing layer MAY guess a rename when a remove and an add have identical bodies and adjacent ids, labelled DC-3 untrusted. The validator never sees it.

**When delete-plus-add is the scary pair the brief worries about:** a Site Model *name* change that does not change the unit. That is why `id` is the unit, not `caddy`. The nickname, if we even keep it, is a non-identity field and a replace hunk. v1: do not keep it. The unit name is what the person needs to see.

Do not recycle an `id` inside a `(domain, kind)` for a different thing. That is a compiler/lint rule across releases, not a snapshot-schema rule. Residue, not solved.

---

## 3. Coverage — in the file, without an escape hatch

E1 §5.7 is right that coverage must travel in the goal file, and wrong that it should be “verbatim from `domain_coverage`.” Verbatim imports a defaulted boolean plus a second field that can contradict it. The goal file is fully resolved; the three states are a single enum:

```text
mode ∈ { comprehensive, not-yet-migrated, deliberately-unmanaged }
```

Each domain this host knows about is exactly one `coverage` entry. Silence then has one meaning, determined by that entry. A coverage transition *is* a hunk on `(domain, coverage, declaration)`.

**What would invite an escape hatch, and is therefore not in the schema:**

- A fourth mode (`partial`, `except`, `best-effort`).
- A per-entry `unmanaged: true` flag. That is a quieter `not-yet-migrated` with no backlog counter.
- Omitting a domain that has other entries (lint: every `entries[].domain` has a coverage declaration; every coverage domain is one of the host’s known domains).
- Reusing Site Model `description` / `note` on coverage (noise, and a place to smuggle intent).

**The real escape hatch is not a schema hole.** It is a coverage *transition*: flipping `comprehensive` → `not-yet-migrated` to get a change out without describing it. Architecture v3 §16 Q8 already re-poses this. The snapshot schema cannot see the previous file. Put the ratchet on the **diff validator**, not here:

| Transition | Ceremony |
| --- | --- |
| `not-yet-migrated` → `comprehensive` | ordinary (tightening) |
| `not-yet-migrated` → `deliberately-unmanaged` | privileged (DC-37 class) |
| `comprehensive` → `deliberately-unmanaged` | privileged |
| `comprehensive` → `not-yet-migrated` | **forbidden** |
| `deliberately-unmanaged` → `comprehensive` | ordinary (reclaim) |
| `deliberately-unmanaged` → `not-yet-migrated` | **forbidden** |

First adoption remains E1 §5.4: the operator enumerates the domains that start comprehensive; every other *site* domain enters as `not-yet-migrated`. Engine domains `trust` and `engine` are always `comprehensive` from minute one — they are not backlog, they are the gate. That is a compiler obligation, not a default keyword.

Coverage entries do not carry `presence`. They are declarations, not actuated artifacts.

---

## 4. Versioning, and what the report row should grow

Fail closed, as E1 §5.6 says. Ignore-unknown is disqualified; the 3.27.1 Augments parser is a working demonstration of why (it *is* ignore-unknown).

- The file carries `schema_version`. In the v1 schema document it is `const: 1`. Any change to the `kind` enum, including additive, is a new schema document and a bumped const. That is stricter than `contract_version` in `common.schema.json`, which is why this field must not `$ref` that def.
- A validator whose ceiling is below the file’s version, or whose kind table does not contain a present `kind`, refuses the whole file with a distinct reason and keeps the last approved baseline. Not a brick.
- Two-phase bump: privileged validator/binary hunk under N, then a migration release whose `diff(migrate(old), new)` is empty apart from the version const. Mixing those is a release-lint failure, not a schema-shape failure.

**Report rows do not carry agent/validator state today.** `schema/report-row.schema.json` `device_convergence` has `release`, `converged_release`, `converged_at`, `complete`. Nothing else. E1 §5.6’s claim is false; architecture v3 §9.6 already records the correction. The compiler cannot render “at the highest version that host last reported” until a column exists.

Add two fields to `device_convergence` only (not to `promise_outcome` or `domain_coverage` — those are per-entry/per-domain noise):

| Field | Type | Meaning |
| --- | --- | --- |
| `validator_version` | `release_stamp` | Version of the on-device binary that contains the validator (and, v1, the projector’s *spec* as golden tests; the binary is the ceiling). |
| `schema_ceiling` | `integer`, `minimum: 1` | Highest `schema_version` that binary will accept. |

Do not also add `agent_version`. One binary, one field. Do not add `approved_goal_schema_version`; the device already has the baseline file.

**Absent report:** treat as `schema_ceiling: 1`. A host that has never reported is rendered at v1, which is also the first-adoption schema. Fail closed, not fail “latest.”

**Stale report:** a host that upgraded the validator offline and has not yet reported will be under-rendered (old schema) until it reports; a host whose last report claimed a ceiling it no longer has will be refused on device (visible stall). Both are acceptable. Do not build a second, speculative channel.

The example fixture `examples/report-rows.yml` will need those two fields on its `device_convergence` row when someone actually edits the schema. This pass does not.

---

## 5. Privileged regions — structure that helps the validator

Privilege is validator-held. The schema’s job is to put privileged facts at **stable JSON Pointers or closed kinds**, and to make a proposer-set privilege flag unrepresentable (`additionalProperties: false`; no such property in any `$defs`).

v1 privileged set, matching what the sketch actually contains:

| Path / kind | Why it is privileged |
| --- | --- |
| `/schema_version` | Changes what every other field means |
| `/host/trust_tier` | `consented` → `operator` turns the local yes off |
| `/host/public_key_alg`, `/host/public_key_hex` | Re-enrollment (DC-22 is open; still a ceremony) |
| `kind: advisor-key` | Who may say yes |
| `kind: peer` | Who may act on this device |
| `kind: policy-tree` | Code outside the entries (R8 / DC-10) |
| `kind: validator` | The comparator itself (TC-25) |

Header is only what you must read in order to parse and to name the host: `schema_version`, `host`. Everything else that diffs is an entry, so the existing “hunks are entry-granular” rule covers coverage transitions, key adds, and the validator binary without inventing header-hunks in the goal-file schema. The one header field that diffs is `schema_version`; that is E1 §5.4’s one-line migration review. `goal-diff.schema.json` (not drawn here) needs a header slot for that single field, or a synthetic triple `(_header, schema, version)` in the diff — pick one when that schema is written, not now.

**What would make this harder:** an untyped `content` / `extra` object on entries. Then the validator cannot path-match. Every kind has a closed shape.

**Not in v1, on purpose:** `device-resource-policy` (DC-12) and a catch-all `trust-policy` blob. The adjudication lists them. Inventing a bag so the list looks complete is how privilege flags come back. Add kinds when the axes have fields; that bump is a schema_version and a two-phase ship. Until then the validator’s local list simply does not include them, and a file cannot carry them.

Ceremony class lives on the approval record, derived by the validator from this list plus the hunk set. Not a field on the hunk.

---

## 6. Fetched content

DC-11 / R12: bind bytes, covered by the accept, re-verified immediately before apply. The schema obligation is a required `content_digest` on every kind that is retrieved rather than stated inline.

v1 kinds that fetch: `policy-tree`, `validator`. Both require `#/$defs/content_digest`. No URL, no filename, no package-version-as-identity. Retrieval is TUF. A name in this file would be exactly the binding TC-26 objected to.

**Packages are not solved by putting a digest field on a package kind we do not yet have.** Distro packages still bind names. E1’s own dissolution table already split TC-26 this way. Do not add `kind: package` in v1 with a decorative digest; that would present R12 as closed. Leave packages out of the consent object until there is a pin we can actually re-verify on macos, Termux, and a stock Linux distro. Residue R12 remains residue.

Inline file *content* (a Caddyfile whose bytes live in the entry) is not a fetch; if that kind is added later, the bytes or their digest are the field, not a path on a CDN. Not in v1.

Re-verify-before-apply is a validator procedure, not a schema keyword. Named so it is not forgotten; not solved here.

---

## 7. Goal file vs Augments — projection, and not onto `def.json`

**Position:** the goal file is a projection *source*. The projection *target* is `$(sys.workdir)/data/host_specific.json`, CFEngine ≥ 3.18.0. `def.json` is not a per-host consent object.

### Why not the same artifact

Steelmanning identity, because one builder would prefer one file: put the entire tendcf document under `host_specific.json`’s `vars` (so CFEngine does not see unknown keys), `additionalProperties: false` at the envelope, generic bundles iterate the consent-shaped arrays. No projector. Approved bytes are installed bytes.

That fails four independent tests:

1. **Ignore-unknown.** A tendcf-shaped document at the top level of `host_specific.json` is skipped key-by-key. Consent fields would not be inputs to the mutation engine; CFEngine would converge on whatever `vars`/`classes` happened to also be present. That is two meanings in one file, which is the thing canonicalization exists to forbid. Embedding under `vars` avoids the skip, but see (2)–(4).
2. **Dual spellings CFEngine owns.** `vars` vs `variables`; `classes` as array or dict; `def.json` vs `def_preferred.json`; floats; non-canonical whitespace (empirically loaded). A consent object cannot be a document whose host parser treats those as equivalent.
3. **Shape conflict.** Consent wants a sorted array of discriminated entries, no attribution, no empty collections, coverage as data. Generic bundles want maps keyed by unit name with `service_policy`, and the MPF wants `inputs` / `control_common_bundlesequence_end`. The guide’s own illustration is already the bundle shape, not the consent shape — and as written (`data`, `nix2cf_edges`) it does not load. Forcing one document to be both couples every `schema_version` bump to the `.cf` tree (itself a privileged digest). That is the correspondence-proof cost Model B was adopted to avoid, relocated.
4. **`def.json` `augments` chaining is `mergedata()`.** The project already refused a second merge engine for the Site Model. Per-host state in `def.json` would re-open it. `host_specific.json` does not support the `augments` key, is loaded first, and tags vars `source=cmdb` in `data:variables.*`. That is the right CFEngine slot. It is still the wrong consent document.

D15 (“compile target is Augments, not freehand `.cf`”) survives. The pipeline becomes Site Model → **goal file** → **projector** → `host_specific.json`. D15 names the last arrow, not the middle document. E1 left this open; the running parser closes it.

### How the projection is bound (and what not to build)

Do **not** put `augments_digest` inside the goal file. The projector is a function of the goal file; inserting the digest of its own output is circular unless the projector is specified to ignore that field, which is a second spelling of “this field is not really in the document.”

Do **not** build an on-device projector in v1. It is the theoretically cleaner “approved bytes generate applied bytes,” and it is a second implementation of the same function on macos, Linux, and Termux, in whatever language `tendcf-agent` is. One builder does not need that until a correspondence bug exists.

v1 binding, cheapest:

1. Compiler renders the canonical goal file.
2. Compiler projects `host_specific.json` as `{ "vars": { …bundle-shaped data… } }` only — no sibling keys, no `variables`, no `classes`, no `inputs`. That is a *subset* of Augments, owned by us, golden-tested.
3. Both files are TUF targets. CI asserts `project(goal-file.json) == examples/host-specific.json` (byte-identical, JCS).
4. When `approval-record.schema.json` is written, extend the E1 §5.1 accept formula with `H(projected_augments)`. The device recomputes that hash. A mismatched sibling is a refuse, not a projection. This is a one-field addition to a schema that does not exist yet, not a goal-file field.

That is a real crack in the slogan “the approved object equals the applied object.” State it: **the approved object is the goal file; the applied object is a digest-bound projection of it.** TC-29 stays dissolved for the consent object (device-side diff of baselines). It does not require the mutation engine to parse the consent object.

Removals (next paragraph) are why the projector cannot be “map the new file and forget the diff.”

### Removals, stale catch-up, and why the snapshot needs tombstones

R4 is correct that absence of a promise is not reversal, and incomplete about where the negative promise *lives*.

If negatives are compiled only from the diff, they exist for one apply. The next `cf-agent` run consumes the projection of the new goal file alone. In a `not-yet-migrated` domain there is no extra-entry sweeper, so a removed unit that was only negatively promised on the transition can come back, and a device jumping from N−7 to N in one accept has only the N snapshot to project from unless tombstones persist in N.

Therefore, for kinds CFEngine actuates (`service` in v1), the snapshot carries `presence: present | absent`. An `absent` entry is a tombstone: still addressed by `(domain, kind, id)`, still a hunk when it appears, still projects to `service_policy => "stop"` / unit unload. Omission in a `not-yet-migrated` domain means *undescribed*, not deleted. Omission in a `comprehensive` domain means the sweeper’s job; lint **forbids** `presence: absent` there (two spellings of absent). Promoting a domain to `comprehensive` strips that domain’s tombstones; that strip is part of the coverage-transition release and must satisfy E1 §5.4’s empty-diff check against `migrate(old)`.

v1 will be almost all `not-yet-migrated`. Tombstones are the removal mechanism until a domain actually goes comprehensive. Do not build tombstone GC as a separate feature; it is a lint rule on one transition.

This also means the projector is a function of the **new goal file alone** (tombstones are in it), which is what makes compiler-side projection plus a sibling hash work for stale devices. The device-computed *diff* is still the consent object; the projection is of the new file the person just approved.

---

## 8. What else in the adjudication is wrong

The report-row error is not unique. These survived reading the schemas, the lint, the fixtures, and the 3.27.1 parser.

### 8.1 §5.7 vs §5.2 (schema contradiction)

“Coverage verbatim from `domain_coverage`” cannot coexist with “the schema defines no defaults.” `common.schema.json` lines 116–158: `comprehensive` has `"default": true`; `required` is only `["description"]`. The same applies to `interlock.pre_action.expect_exit` (default 0) and `timeout_seconds` (default 30). Goal-file coverage is a three-valued enum; goal-file interlocks, if present, have every field required. Do not `$ref` those defs.

### 8.2 “Approved object equals applied object”

True of the validator’s two canonical goal files. False of CFEngine’s input unless identity holds. Identity does not hold (§7). The slogan should be restated before someone implements a validator that copies the goal file onto `host_specific.json` and watches CFEngine skip every key.

### 8.3 R4 as “compiler of the diff”

Necessary but not sufficient. Negatives that do not persist in the snapshot fail on the second run and on stale catch-up in non-comprehensive domains. Tombstones in the snapshot, sweeper in comprehensive domains, ratchet on coverage transitions.

### 8.4 “Integers and strings only”

Booleans (or enums) are required. JCS handles them. Forbidding them would force `comprehensive: "true"` as a string, which is a second spelling waiting to happen.

### 8.5 Guide Augments claims the adjudication treated as ground

Not E1’s text, but E1’s corpus. Two load-bearing factual errors:

- Guide §4: “YAML is a valid input.” 3.27.1: YAML `def.json` fails to parse. CFEngine’s own Augments page calls them JSON data files.
- Guide §16 illustrative `host_specific.json` uses `data` and `nix2cf_edges`. 3.27.1 skips both. The working encoding is `{ "vars": { "nix2cf_services": {…} } }`, which lands at `data:variables.nix2cf_services` tagged `source=cmdb`.

E1 §1.4 “B is CFEngine-shaped. Complete resolved state is what the Augments layer consumes” is directionally right and specific-shape wrong. Complete resolved *consent* state is not what the Augments layer consumes.

### 8.6 `contract_version` vs `schema_version` is under-sold

E1 says the goal-file rule is stricter. The operational consequence is: **you cannot share a versioning def, you cannot share a migration policy, and you cannot treat an additive kind like an additive Site Model field.** A reader of `common.schema.json` who `$ref`s `contract_version` into the goal file would silently adopt ignore-unknown-on-add. Worth a lint rule when the schema exists: goal-file schema must not `$ref` `contract_version`.

### 8.7 Header sketch in E1 §8 omits `trust_tier` and `platform`

It names `schema_version`, host public key, domain coverage. The consent gate *class* is `trust_tier`. It belongs in the header, privileged. Platform belongs there too (lint of adapter blocks; not a hunk anyone should hide in a service).

### 8.8 What I am not claiming is wrong

Device-side diff, refuse-never-normalize, no attribution in the format, no dependency-grouped apply, fail-closed unknown kinds, two-phase bumps, coverage in the file, privilege validator-held, CUT-1 not adopted, inference cut severable. Those hold.

---

## 9. What not to build

One unfunded builder. Cuts, in the order they save the most:

1. **Identity with Augments.** Would look like less glue and would be a new correspondence-plus-leniency problem. §7.
2. **On-device projector, v1.** Compiler projector + TUF sibling + `H(projected_augments)` on the approval record later.
3. **`augments_digest` inside the goal file.** Circular. See §7.
4. **Rename hunks, attribution fields, dependency groups, privilege flags.** Already rejected; do not sneak back as `related_id`, `from`, `class`, `privileged`.
5. **Site Model fields in the goal file.** `description`, `note`, `platform_notes`, `provides`, `requires`, `depends_on`, `source_location`, `hosts`, `role`, `managed_by`, `contract_version`. Authoring and briefing, not consented device state. Inference stays severable in the Site Model; DC-41 can revive it without a goal-file bump.
6. **`kind: package` and `kind: file` in v1.** No honest digest story for distro packages; no migrated file domain yet. Adding a kind is a schema_version on purpose — do not pre-enumerate.
7. **`kind: trust-policy` and `kind: device-resource-policy` placeholders.** Empty bags. DC-12 remains open.
8. **Per-entry unmanaged flags; a fourth coverage mode; tombstone GC as a feature.** §3 and §7.
9. **YAML goal files; `variables` / `classes` / `inputs` on the projected Augments; `mergedata()` for per-host data; `def.json` as the per-host slot.**
10. **`explain-hunk` before the schema family exists.** Due before Step 9, not before §14.2 review of this contract.
11. **Validator code, now.** Architecture §9.9 / §14.2: contract and fixtures first, independent review, then code. This opinion is input to the contract, not a substitute for that review.
12. **A fat v1 `kind` enum “so we don’t have to bump.”** Additive kinds *must* bump. A fat enum is an unreviewed claim about operations we have not transcribed.

Build, and only these, for the schema pass:

- `goal-file.schema.json` as in §10, plus `examples/goal-file.json` in actual JCS bytes.
- Two new columns on `device_convergence` (later edit; specified in §4).
- Lint: `.json` pairing, JCS idempotence, entry sort/uniqueness, coverage completeness, adapter-vs-platform, no `$ref` of `contract_version` / `domain_coverage` / `interlock` from the goal-file schema.
- Negative fixtures listed in §12.
- `goal-diff` and `approval-record` as follow-on schemas, not this document. Do not wait on them to land the goal-file contract; do not implement either.

---

## 10. Schema sketch

House style: draft 2020-12, `$id` on `github.com/frdminc/tendcf` (matches the existing files), `$ref` into `common.schema.json` only for defs that do not carry defaults or the wrong versioning rule, `additionalProperties: false`, `allOf`/`if`/`then` as in `services.schema.json`, `$comment` for why.

Partial: kinds not listed are omitted on purpose (§9.6–9.7). Cross-entry constraints marked `$comment` + lint.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/frdminc/tendcf/schema/goal-file.schema.json",
  "title": "tendcf — canonical per-host goal file (v1)",
  "description": "The consent object. Fully resolved; no defaults; no empty collections; RFC 8785 bytes on the wire. Not CFEngine Augments: a projector emits host_specific.json from this document. schema_version is const 1; any kind-set change is a new schema document.",

  "type": "object",
  "properties": {
    "schema_version": {
      "description": "Fail-closed. Stricter than common.schema.json contract_version: additive kinds bump this. An old validator that sees a value above its ceiling refuses the file.",
      "const": 1
    },
    "host": { "$ref": "#/$defs/host" },
    "entries": {
      "description": "Set-semantics. Lint: sorted by (domain, kind, id) under JCS string order of NFC forms; unique on that triple. Schema cannot say the sort.",
      "type": "array",
      "minItems": 1,
      "items": {
        "oneOf": [
          { "$ref": "#/$defs/coverage_entry" },
          { "$ref": "#/$defs/bundle_entry" },
          { "$ref": "#/$defs/service_entry" },
          { "$ref": "#/$defs/unit_writer_entry" },
          { "$ref": "#/$defs/advisor_key_entry" },
          { "$ref": "#/$defs/peer_entry" },
          { "$ref": "#/$defs/policy_tree_entry" },
          { "$ref": "#/$defs/validator_entry" }
        ]
      }
    }
  },
  "required": ["schema_version", "host", "entries"],
  "additionalProperties": false,

  "$defs": {
    "content_digest": {
      "description": "DC-11 / R12. One algorithm, one encoding. Locator is TUF's job, not a field here.",
      "type": "object",
      "properties": {
        "alg": { "const": "sha256" },
        "hex": { "type": "string", "pattern": "^[0-9a-f]{64}$" }
      },
      "required": ["alg", "hex"],
      "additionalProperties": false
    },

    "host": {
      "type": "object",
      "properties": {
        "name": { "$ref": "common.schema.json#/$defs/host_name" },
        "platform": { "enum": ["macos", "android", "linux"] },
        "trust_tier": {
          "description": "Privileged. consented→operator turns the local yes off. The only spelling of this fact.",
          "enum": ["operator", "managed", "consented"]
        },
        "public_key_alg": { "const": "ed25519" },
        "public_key_hex": {
          "description": "32-byte key, lowercase hex. Privileged (re-enrollment).",
          "type": "string",
          "pattern": "^[0-9a-f]{64}$"
        }
      },
      "required": ["name", "platform", "trust_tier", "public_key_alg", "public_key_hex"],
      "additionalProperties": false
    },

    "entry_envelope": {
      "type": "object",
      "properties": {
        "domain": { "$ref": "common.schema.json#/$defs/identifier" },
        "kind": { "type": "string" },
        "id": {
          "description": "Actuation key inside (domain, kind). Pattern is kind-specific; this is the shared floor.",
          "type": "string",
          "minLength": 1,
          "maxLength": 256
        }
      },
      "required": ["domain", "kind", "id"]
    },

    "coverage_entry": {
      "allOf": [{ "$ref": "#/$defs/entry_envelope" }],
      "properties": {
        "domain": true,
        "kind": { "const": "coverage" },
        "id": { "const": "declaration" },
        "mode": {
          "description": "Single field so comprehensive+reason and false-without-reason are unrepresentable. Not a $ref of domain_coverage (that def has defaults).",
          "enum": ["comprehensive", "not-yet-migrated", "deliberately-unmanaged"]
        }
      },
      "required": ["domain", "kind", "id", "mode"],
      "additionalProperties": false
    },

    "interlock": {
      "description": "Resolved. Do not $ref common interlock (defaults on expect_exit and timeout_seconds). description omitted: briefing layer.",
      "type": "object",
      "properties": {
        "id": { "$ref": "common.schema.json#/$defs/identifier" },
        "pre_action": {
          "type": "object",
          "properties": {
            "command": {
              "type": "array",
              "items": { "type": "string", "minLength": 1 },
              "minItems": 1
            },
            "expect_exit": { "type": "integer", "minimum": 0 },
            "timeout_seconds": { "type": "integer", "minimum": 1 }
          },
          "required": ["command", "expect_exit", "timeout_seconds"],
          "additionalProperties": false
        },
        "defines_class": { "type": "string", "pattern": "^[a-z][a-z0-9_]*$" },
        "blocks": { "const": "enclosing-bundle" },
        "report": { "const": true }
      },
      "required": ["id", "pre_action", "defines_class", "blocks", "report"],
      "additionalProperties": false
    },

    "bundle_entry": {
      "allOf": [{ "$ref": "#/$defs/entry_envelope" }],
      "properties": {
        "domain": true,
        "kind": { "const": "bundle" },
        "id": { "$ref": "common.schema.json#/$defs/identifier" },
        "interlocks": {
          "type": "array",
          "items": { "$ref": "#/$defs/interlock" },
          "minItems": 1
        }
      },
      "required": ["domain", "kind", "id"],
      "additionalProperties": false
    },

    "service_entry": {
      "description": "id is the supervisor unit name (launchd label / systemd unit / runit name), not the Site Model service name. Lint: exactly one adapter block, matching host.platform. Lint: presence=absent forbidden in a comprehensive domain.",
      "allOf": [{ "$ref": "#/$defs/entry_envelope" }],
      "properties": {
        "domain": true,
        "kind": { "const": "service" },
        "id": {
          "type": "string",
          "pattern": "^[A-Za-z0-9][A-Za-z0-9._@-]*$",
          "maxLength": 256
        },
        "presence": { "enum": ["present", "absent"] },
        "bundle": { "$ref": "common.schema.json#/$defs/identifier" },
        "runs_as": { "type": "string", "pattern": "^[a-z_][a-z0-9_-]*$" },
        "command": {
          "type": "array",
          "items": { "type": "string", "minLength": 1 },
          "minItems": 1
        },
        "working_dir": { "type": "string", "minLength": 1 },
        "env": { "$ref": "common.schema.json#/$defs/env_map" },
        "launchd": {
          "type": "object",
          "properties": {
            "label": {
              "type": "string",
              "pattern": "^[a-z][a-z0-9]*(\\.[A-Za-z0-9][A-Za-z0-9_-]*)+$"
            },
            "run_at_load": { "type": "boolean" },
            "keep_alive": { "type": "boolean" }
          },
          "required": ["label", "run_at_load", "keep_alive"],
          "additionalProperties": false
        },
        "systemd": {
          "type": "object",
          "properties": {
            "unit": { "type": "string", "pattern": "^[A-Za-z0-9@._-]+\\.(service|timer|socket)$" }
          },
          "required": ["unit"],
          "additionalProperties": false
        },
        "termux": {
          "type": "object",
          "properties": {
            "service_name": { "type": "string", "pattern": "^[A-Za-z0-9._-]+$" }
          },
          "required": ["service_name"],
          "additionalProperties": false
        }
      },
      "required": ["domain", "kind", "id", "presence", "bundle", "runs_as", "command"],
      "additionalProperties": false
    },

    "unit_writer_entry": {
      "description": "Who may write a unit prefix on this host. Extra-entry detection reads this, not the Site Model, because the device does not have the Site Model.",
      "allOf": [{ "$ref": "#/$defs/entry_envelope" }],
      "properties": {
        "domain": true,
        "kind": { "const": "unit-writer" },
        "id": {
          "type": "string",
          "pattern": "^[a-z][a-z0-9]*(\\.[A-Za-z0-9][A-Za-z0-9_-]*)+\\.\\*$"
        },
        "writer": {
          "enum": ["cfengine", "mise", "nix-darwin", "homebrew", "apple", "third-party"]
        }
      },
      "required": ["domain", "kind", "id", "writer"],
      "additionalProperties": false
    },

    "advisor_key_entry": {
      "allOf": [{ "$ref": "#/$defs/entry_envelope" }],
      "properties": {
        "domain": { "const": "trust" },
        "kind": { "const": "advisor-key" },
        "id": { "type": "string", "pattern": "^[0-9a-f]{64}$" },
        "alg": { "const": "ed25519" }
      },
      "required": ["domain", "kind", "id", "alg"],
      "additionalProperties": false
    },

    "peer_entry": {
      "description": "One peer per entry so add/remove is one hunk. Empty allowlist is omission of all peer entries, not [].",
      "allOf": [{ "$ref": "#/$defs/entry_envelope" }],
      "properties": {
        "domain": { "const": "trust" },
        "kind": { "const": "peer" },
        "id": { "type": "string", "pattern": "^[0-9a-f]{64}$" },
        "alg": { "const": "ed25519" },
        "verbs": {
          "type": "array",
          "items": { "enum": ["adb", "ssh", "peer-help"] },
          "minItems": 1,
          "uniqueItems": true
        }
      },
      "required": ["domain", "kind", "id", "alg", "verbs"],
      "additionalProperties": false
    },

    "policy_tree_entry": {
      "description": "R8 / DC-10. Singleton. How the digest is computed over the tree is validator-held and must be specified before Step 6; v1 pins the alg name only.",
      "allOf": [{ "$ref": "#/$defs/entry_envelope" }],
      "properties": {
        "domain": { "const": "engine" },
        "kind": { "const": "policy-tree" },
        "id": { "const": "tree" },
        "tree_hash_alg": { "const": "sha256-git-tree" },
        "digest": { "$ref": "#/$defs/content_digest" }
      },
      "required": ["domain", "kind", "id", "tree_hash_alg", "digest"],
      "additionalProperties": false
    },

    "validator_entry": {
      "description": "The comparator binary. Privileged, fetched, two-phase with schema bumps.",
      "allOf": [{ "$ref": "#/$defs/entry_envelope" }],
      "properties": {
        "domain": { "const": "engine" },
        "kind": { "const": "validator" },
        "id": { "const": "binary" },
        "version": { "$ref": "common.schema.json#/$defs/release_stamp" },
        "digest": { "$ref": "#/$defs/content_digest" }
      },
      "required": ["domain", "kind", "id", "version", "digest"],
      "additionalProperties": false
    }
  }
}
```

### Canonical instance (shape, not JCS-checked bytes)

Omitted keys are omitted. `entries` shown in sort order. A real fixture must be the JCS serialization of this object, no pretty-print.

```json
{
  "schema_version": 1,
  "host": {
    "name": "mac",
    "platform": "macos",
    "public_key_alg": "ed25519",
    "public_key_hex": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "trust_tier": "operator"
  },
  "entries": [
    {
      "domain": "engine",
      "id": "declaration",
      "kind": "coverage",
      "mode": "comprehensive"
    },
    {
      "domain": "engine",
      "id": "tree",
      "kind": "policy-tree",
      "digest": { "alg": "sha256", "hex": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" },
      "tree_hash_alg": "sha256-git-tree"
    },
    {
      "domain": "engine",
      "id": "binary",
      "kind": "validator",
      "digest": { "alg": "sha256", "hex": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc" },
      "version": "tendcf-agent-0.0.1"
    },
    {
      "domain": "macos-launchd-services",
      "id": "edge-http",
      "kind": "bundle"
    },
    {
      "domain": "macos-launchd-services",
      "id": "declaration",
      "kind": "coverage",
      "mode": "not-yet-migrated"
    },
    {
      "domain": "macos-launchd-services",
      "id": "com.djbclark.caddy",
      "kind": "service",
      "bundle": "edge-http",
      "command": ["/opt/homebrew/bin/caddy", "run", "--config", "/etc/caddy/Caddyfile"],
      "launchd": { "keep_alive": true, "label": "com.djbclark.caddy", "run_at_load": true },
      "presence": "present",
      "runs_as": "djbclark"
    },
    {
      "domain": "macos-launchd-services",
      "id": "com.djbclark.*",
      "kind": "unit-writer",
      "writer": "cfengine"
    },
    {
      "domain": "trust",
      "id": "declaration",
      "kind": "coverage",
      "mode": "comprehensive"
    }
  ]
}
```

First-adoption for this host would drop the `caddy` service and the `edge-http` bundle, keep coverage as `not-yet-migrated` for `macos-launchd-services`, and still carry `engine` + `trust` coverage, policy-tree, and validator. That is the minimal-claim file. The instance above is a later, still-small, reviewable diff.

Lint that this sketch cannot express, inherited from `bin/schema_lint.py` layer 4:

- `(domain, kind, id)` unique and sorted.
- Every entry’s `domain` has a `coverage` declaration; `trust` and `engine` are `comprehensive`.
- Service `bundle` names a `bundle` entry in the same domain.
- Service adapter block matches `host.platform`; `launchd.label` equals `id` on macos (two spellings of the unit name otherwise — **make them match or drop `launchd.label` in a later tightening**; v1 keeps the nested object to match `services.schema.json` shape the projector will want, and lint forces equality).
- `presence: absent` only in non-comprehensive domains.
- `env` if present has `minProperties: 1` (the common def does not say this).
- `schema_ceiling` / `validator_version` on `device_convergence` once that schema is edited.
- Projector golden: this file → `{ "vars": { … } }` with no other top-level keys.

---

## 11. Report-row addition (specified, not edited)

On `schema/report-row.schema.json` `#/$defs/device_convergence`, add to `properties` and `required`:

```json
"validator_version": {
  "description": "tendcf-agent / validator binary that produced this row. The compiler renders the host at this binary's schema_ceiling. Absent in historical rows: treat as schema_ceiling 1.",
  "$ref": "common.schema.json#/$defs/release_stamp"
},
"schema_ceiling": {
  "description": "Highest goal-file schema_version this validator will accept. Integer, not a string, so comparison is not lexicographic.",
  "type": "integer",
  "minimum": 1
}
```

If making them required breaks the Step 0 fixture before anything writes rows, ship them optional with the compiler treating absence as ceiling 1, then require them when the agent starts writing. Prefer required-plus-fixture-edit: the file’s own comment says “one column now and a migration later.”

---

## 12. Named omissions and the negative-fixture floor

**Omitted from the sketch, named:**

- `goal-diff.schema.json` and `approval-record.schema.json` (family members; not this brief). Diff must include a slot for `/schema_version`. Approval should add `H(projected_augments)` to the E1 §5.1 formula.
- `kind: file`, `kind: package`, `kind: trust-policy`, `kind: device-resource-policy`.
- Tree-hash *algorithm definition* for `sha256-git-tree` (name is pinned; byte sequence is not). Must exist before Step 6.
- NFC / JCS as schema keywords (impossible; lint).
- Coverage ratchet across files (diff validator).
- Peer verb set is a guess from architecture §10 (`adb`, `ssh`, `peer-help`). Closed, so a new verb is a bump — better than an open string.

**Negative fixtures the later schema pass must add** (E1 §8 floor, plus what this opinion makes newly possible). Do not create them here.

| Case | Why it is not a shape error |
| --- | --- |
| Non-canonical pretty-printed twin of the happy path | Refuse-never-normalize |
| Empty `entries: []` | Omission vs empty |
| `comprehensive`-style boolean + `opt_out_reason` if anyone reintroduces two fields | Unrepresentable enum |
| Unknown `kind` | Fail closed |
| `schema_version: 2` against the v1 schema | Fail closed |
| Empty `command: []` or omitted required `presence` | No defaults |
| `presence: absent` in a `comprehensive` domain | Two spellings of absent |
| Duplicate `(domain, kind, id)` | Identity |
| Unsorted `entries` | Camouflage |
| `description` / `origin` / `privileged` extra key | additionalProperties |
| Digest `hex` uppercase, or `alg: "SHA-256"` | Dual spelling |
| Service with both `launchd` and `systemd` | Dual adapter |
| `launchd.label` ≠ `id` | Dual spelling of the unit |
| Coverage missing for a domain that has a service | Completeness contract |
| `comprehensive` → `not-yet-migrated` (diff fixture) | Escape hatch |
| Migration whose semantic diff is non-empty | E1 §5.4 |
| Projected `host_specific.json` with a top-level `data` or `classes` key | Parser leniency as a backdoor |
| Guide-shaped `{data, nix2cf_edges}` accepted as a projection | Regression of §8.5 |

F-9b still applies: these are the floor. The §14.2 review is on the contract, before validator code, by a lineage that did not write the schema.

---

## 13. Residue this opinion does not close

R1 (privileged list will grow), R5 (fan-out; `explain-hunk` is later), R9 (activation gap), R10 (baseline storage is platform-specific), R12 for distro packages, R14 (TC-23), R15 (counter-proposal fatigue), R16–R18, DC-1, DC-12, DC-22, the tree-hash byte sequence, and architecture §16 Q10 (whether a person can actually consent to a diff). Nothing above presents those as solved.
