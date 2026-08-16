# Negative fixtures

Fifty-nine deliberately broken overlays, plus six byte-class fixtures in
the sibling `examples/broken-bytes/`. `bin/schema_lint.py` must catch
every one; a case that validates is a lint failure.

Each directory here replaces the happy-path file of the same name under
`examples/`. The rest of the Site Model (cases 1-12) or the goal-file
family (cases 13-65) stays as in the happy path.

**The "Caught by" column is executable.** `bin/schema_lint.py` reads these
tables back and requires each case to be caught by the class its row
declares — a case that fires only findings from some other layer is a lint
failure, as is a fixture with no row here or a row naming no fixture on
disk. "Something objected" was the weaker claim this harness used to make,
and it was weak where it mattered: a fixture that rewrites a file another
layer reads makes that layer object by construction, so a case could go on
passing after the rule it exists to test was deleted. Cases 13-43 are the
whole set that was in that position — each rewrites `goal-file.json`, which
the family layer reads — and the lint carried a special case standing that
layer down for them. That gate is gone; the declaration replaces it, and
without the gate's asymmetry (an overlaid *baseline* was never stood down,
so a schema negative written against `goal-file-baseline.json` would have
been masked exactly the way 13-43 would have been — it now is not).

The class is the cell text with any parenthetical dropped, except under
`family`, where the parenthetical is the class: `family (hash)`,
`family (apply)`, and `family (ceremony)` are three different rules and a
case must name the right one. Under `schema` the parenthetical is the
keyword or def under test — prose for a reader, since the lint cannot
produce it — so it is documentation and is not checked. The full
vocabulary is `RULE_CLASSES` in `bin/schema_lint.py`; a cell naming
anything else is a lint failure too.

| # | Case | Broken input | Caught by |
| --- | --- | --- | --- |
| 1 | `01-opt-out-no-reason` | `comprehensive: false` with no `opt_out_reason` | schema |
| 2 | `02-opt-out-on-comprehensive` | `comprehensive: true` **with** an `opt_out_reason` | schema |
| 3 | `03-rogue-launchd-label` | launchd label `com.rogue.caddy` under no declared prefix | cross-file |
| 4 | `04-nested-writer-prefix` | prefix `com.djbclark.caddy.*` nested in `com.djbclark.*` | cross-file |
| 5 | `05-macos-no-launchd` | macOS service with no `launchd` block | schema (`if/then`) |
| 6 | `06-literal-secret` | `OPENAI_API_KEY: sk-live-abc123` (literal, not a key name) | schema |
| 7 | `07-typo-token-kind` | `netwrok:tailnet` (typo'd token kind) | schema |
| 8 | `08-unknown-role` | `role: llm-gatway` (unknown role) | cross-file |
| 9 | `09-enforce-audit-outcome` | enforce-mode row with `outcome: compliant` | schema |
| 10 | `10-invalid-release-stamp` | `release: NOT-A-STAMP` (outside the identifier pattern) | schema |
| 11 | `11-coverage-missing-field` | `domain_coverage` row missing `deliberately_unmanaged` | schema |
| 12 | `12-unknown-row-type` | `row_type: converged` (unknown row type) | lint discriminator |

Cases 13-43 are `goal-file.schema.json`'s §10 negative list
(`goal-file-schema-reconciliation-2026-08-15.md` §10/§18 item 1), each a
full alternate `goal-file.json`, not a partial overlay — the goal file has
no other Site Model files to compose against.

| # | Case | Broken input | Caught by |
| --- | --- | --- | --- |
| 13 | `13-schema-version-bump` | `schema_version: 2` | schema (`const`) |
| 14 | `14-unknown-kind` | a `file` kind under `entries` | schema (`additionalProperties`) |
| 15 | `15-empty-entries` | `entries: {}` | schema (`minProperties`) |
| 16 | `16-entries-under-deliberately-unmanaged` | `deliberately-unmanaged` domain **with** entries | schema (`if/then`) |
| 17 | `17-tombstone-stale-body` | `state: absent` service carrying a stale `bundle` | schema (`absent` def) |
| 18 | `18-missing-device-trust` | `domains` with no `device-trust` | schema (`required`) |
| 19 | `19-non-comprehensive-device-trust` | `device-trust` coverage `not-yet-migrated` | schema (`const`) |
| 20 | `20-missing-policy-tree-digest` | `device-trust` entries with no `policy-tree` | schema (`required`) |
| 21 | `21-missing-agent-entry` | `device-trust` entries with no `agent` | schema (`required`) |
| 22 | `22-local-yes-required-without-advisor-key` | `local_yes_required: true`, no `advisor-key` | schema (`if/then`) |
| 23 | `23-missing-working-dir` | service present with no `working_dir` | schema (`required`) |
| 24 | `24-dot-dot-path` | `working_dir: "/foo/../bar"` | schema (`abs_path` pattern) |
| 25 | `25-trailing-slash-path` | `working_dir: "/foo/"` | schema (`abs_path` pattern) |
| 26 | `26-double-slash-path` | `working_dir: "/foo//bar"` | schema (`abs_path` pattern) |
| 27 | `27-two-unit-flavors` | `unit` carrying both `launchd` and `systemd` | schema (`oneOf`) |
| 28 | `28-missing-launchd-knob` | `launchd` with `run_at_load` but no `keep_alive` | schema (`required`) |
| 29 | `29-empty-argv` | `command: []` | schema (`minItems`) |
| 30 | `30-empty-env-map` | `env: {}` | schema (`minProperties`) |
| 31 | `31-unprefixed-host-key` | `host` with no `ed25519:` prefix | schema (`pattern`) |
| 32 | `32-uppercase-digest-hex` | `sha256:` digest with uppercase hex | schema (`pattern`) |
| 33 | `33-defaulted-expect-exit` | `pre_action` with no `expect_exit` | schema (`required`) |
| 34 | `34-silenced-interlock-report` | interlock `report: false` | schema (`const`) |
| 35 | `35-malformed-writer-prefix` | unit-writer prefix with no trailing `.*` | schema (`pattern`) |
| 36 | `36-unknown-writer` | `writer: custom-tool` | schema (`enum`) |
| 37 | `37-uppercase-domain` | domain key `Supervision` | schema (`propertyNames`) |
| 38 | `38-proposer-set-privileged-flag` | service entry with a `privileged: true` field | schema (`additionalProperties`) |
| 39 | `39-description-prose` | service entry with a `description` field | schema (`additionalProperties`) |
| 40 | `40-boolean-reason-coverage-spelling` | `coverage` as `{comprehensive, opt_out_reason}` | schema (`enum`) |
| 41 | `41-embedded-release-stamp` | a stray top-level `release_stamp` field | schema (`additionalProperties`) |
| 42 | `42-malformed-advisor-key-id` | advisor-key property name not `ed25519:`+hex | schema (`propertyNames`) |
| 43 | `43-float-timeout` | `timeout_seconds: 30.5` | schema (`type`) |

Cases 49-55 are the diff-class negatives. 49-53 are the five §13 names as
the floor; 54 and 55 go one step past it, refusing the no-op hunk and the
no-op coverage change — §11 says an empty diff is not a document, and a
hunk or transition that changes nothing is that same nothing smuggled
through as volume, spending the reviewer attention §16 iv is about.

Each overlays `goal-diff.json`, and — where isolating the rule under test
requires it — `goal-file-baseline.json` and both approval records too, so
that exactly one finding fires and it is the one the case name claims
(verified for all seven, and for 56 and 57).

The reject-record overlay is not decoration. The family layer holds every
record to the diff, so a case that corrects only the accept record leaves
the reject one disagreeing with that case's own diff — a second finding
about nothing the case claims. Each mirror asserts the **derived** ceremony
class and the case diff's own hashes, never the deliberate error the accept
overlay exists to make: cases 52 and 53 are about one record asserting
`ordinary` over a privileged change, so their mirrors correctly say
`privileged` and stay silent.

| # | Case | Broken input | Caught by |
| --- | --- | --- | --- |
| 49 | `49-baseline-hash-mismatch` | `baseline_sha256` naming no fixture on disk | family (hash) |
| 50 | `50-hunk-inconsistency` | a hunk's `new.working_dir` the proposed file does not carry | family (apply) |
| 51 | `51-non-empty-migration` | `version_bump` alongside `hunks` | schema (`if/then`) |
| 52 | `52-ordinary-over-privileged-hunk` | a `device-trust` hunk approved `ordinary` | family (ceremony) |
| 53 | `53-coverage-retreat-ordinary-class` | a domain leaving `comprehensive`, approved `ordinary` | family (ceremony) |
| 54 | `54-no-op-hunk` | a hunk stating the same entry as `old` and `new` | family (apply) |
| 55 | `55-no-op-coverage-change` | `comprehensive → comprehensive` | family (apply) |

Case 54 sits under `device-trust` because that is the only domain the
baseline carries, so its record is overlaid to assert `privileged` — the
class the validator correctly derives — leaving the no-op as the finding
rather than a ceremony mismatch on top of it.

Cases 56 and 57 close `approval-record.schema.json`'s refused-iff-reject
`if/then/else`, which until now had no fixture in **either** direction:
every approval record in the corpus said `accept`, so the `then` branch
had no instance to fail against and the `else` branch none to pass. §11
requires "a reject-with-annotations" fixture, and one accept record
cannot supply it — `refused` is present iff the verdict is reject, so the
happy path can only ever exercise one side of the rule it states.

The positive half of that pair is `examples/approval-record-reject.json`,
a second **valid** record answering the same ceremony as
`examples/approval-record.json`: same host, same nonce, same
`approval_seq`, same two hashes, differing in `verdict`, `refused`, and
`signature` and in nothing else. The shared nonce and counter are not a
DC-2 violation smuggled into the corpus — they are what makes the pair a
controlled comparison. These are the two possible answers to one device
challenge, not two records a validator would ever persist in sequence;
what a reviewer's decision changes is exactly what differs between the
files. Both are held to the family layer's record rules (§9.1's two
hashes, the derived ceremony class), so the reject cannot drift stale
while the accept stays honest.

| # | Case | Broken input | Caught by |
| --- | --- | --- | --- |
| 56 | `56-reject-without-annotations` | `verdict: reject` with no `refused` | schema (`if/then`) |
| 57 | `57-accept-with-annotations` | `verdict: accept` **with** a `refused` | schema (`if/else`) |
| 59 | `59-refused-path-names-no-hunk` | `refused` naming a hunk the diff lacks | family (refused) |
| 60 | `60-record-for-another-host` | a record signed for a different device | family (host) |

## The `Caught by` parentheticals are executable too

The head of each cell (`schema`, `goal cross-file`, `family (apply)`) has
been read back and checked since dddd31b. The parenthetical beside a
`schema` head was still prose until now, which meant ``schema (`const`)``
could sit on a case the `const` rule no longer touches and nothing would
notice — the more specific half of the claim was the unchecked one.

Now every **backticked** token inside a `schema (...)` parenthetical is
checked against what the validator actually objected with. Backticks are the
notation: a backticked token is a machine-checked claim, and a bare word
beside one is prose that makes the row read as English — the "pattern" in
``schema (`abs_path` pattern)``, the "def" in ``schema (`absent` def)``.

Keeping those readable names cost something to build, and it was worth it.
jsonschema resolves `$ref` before reporting, so the `abs_path` violation
arrives naming only `pattern` and the tombstone rule arrives naming only
`additionalProperties` — both true, both the message class D16(a) rules out,
because neither can be acted on without going and reading the schema. Rather
than degrade the cells to those keywords to make them checkable, the lint
walks the raw schema alongside the error and recovers the `$defs` names the
failure passed through. `propertyNames` needed the same treatment from the
other direction: a bad domain key reports `pattern` one level below the rule
a reader would name.

What this catches, and what it does not, measured by mutation: naming a rule
the validator never reached goes red (`required`->`minLength`,
`if/then`->`if/else`, `propertyNames`->`additionalProperties` all fail).
Naming the wrong sibling branch of a `oneOf` it *did* reach stays green —
swapping `abs_path` for `absent` on case 24 passes, because a service entry
is a `oneOf` over present/absent and the absent branch genuinely failed too.
Tightening that would mean ranking branch failures by relevance, which the
error does not carry.

Case 40 is the defect this found on its first run: it was declared
`schema (`type`)`, but `$defs.coverage` is a bare `enum` with no `type`, so
an object value fails `enum`. The cell had been wrong since it was written.

Case 57 is why the `else` branch is spelled `{"refused": false}` rather
than §11's more obvious `{"not": {"required": ["refused"]}}`. The two are
the same rule; the `not` form reports it by printing the entire record
back and saying it "should not be valid", which is the message class
D16(a) rules out — resolution needs a human, so the message has to name
what is wrong. The `false`-schema form names the offending annotation
array and nothing else. Neither form yields an instance path better than
`<root>` (jsonschema drops it for boolean subschemas), which is the
harness's problem rather than the schema's.

Case 59 is the rule that makes `refused` more than decoration. §11 makes
the annotation advisory — it does not change what was refused, which is
all of it (§9.3) — but it exists so the proposer knows what to re-render,
and a key-path resolving to no hunk and no coverage change tells them to
re-render nothing. It is also the shape a stale record takes once the diff
it answers has moved on. Both addressable sections count:
`hunks/<domain>/<kind>/<id>` and `coverage_changes/<domain>`, the latter
because §9.7 makes coverage a section of its own precisely so it cannot be
lost in entry noise — which makes it refusable on its own.

Cases 61-65 are the goal file's own cross-entry rules, which had no
fixtures at all until the class-coverage check below asked for them. Each
overlays `goal-file.json`, so the family layer objects too; the
declaration is what keeps that noise from standing in for the rule under
test.

| # | Case | Broken input | Caught by |
| --- | --- | --- | --- |
| 61 | `61-interlock-bundle-unused` | an interlock naming a bundle no present service uses | goal cross-file |
| 62 | `62-nested-unit-writer-prefix` | `com.tendcf.caddy.main.*` nested in `com.tendcf.caddy.*` | goal cross-file |
| 63 | `63-service-under-no-prefix` | a `com.rogue.*` service under no declared prefix | goal cross-file |
| 64 | `64-service-under-non-cfengine-writer` | a comprehensive-domain prefix with `writer: homebrew` | goal cross-file |
| 65 | `65-unit-writer-prefix-twice` | one prefix declared under two state domains | goal cross-file |

Both of those needed a second draft, and the reason is worth keeping. Case
64 first said `writer: launchd`, which is not in the writer enum at all —
so it was case 36 wearing a cross-file label, and the rule it claimed to
test could have been deleted with the case still red. `homebrew` is a
writer the schema admits and this rail does not. Case 65 first put the
duplicate prefix under `device-trust`, which is a `trust_domain` and
admits no `unit-writer` kind; expressing "one prefix, two domains" at all
needs a third state domain, which is why the fixture grows a `packaging`
one. A negative fixture that fails for a reason other than its own is the
thing this whole section exists to catch, and it caught these.

## Every class has a fixture

`check_class_coverage()` asks the declarations' question from the other
end: a rule class with no case behind it is a layer whose rules could all
be deleted without a red lint. Three classes are exempt, named with their
reason in `CLASSES_WITHOUT_FIXTURES` — `pairing`, `schema meta`, and
`harness` are about the corpus's shape rather than a document's content,
and this harness's unit is a document overlay held in memory. An overlay
cannot unpair a schema, delete a fixture from disk, or break the harness
running it. Everything else must have a case, which is where 58-65 came
from.

## Byte-class fixtures (`../broken-bytes/`)

The five §13 byte-class negatives, plus one for bytes that are not JSON. These are not overlays: each is a whole
alternate `goal-file.json` checked as **raw bytes, before the parse**, and
`bin/schema_lint.py` runs only its byte layer over them.

That narrowness is the point, and it is measured rather than assumed. Run
44, 45, 46 and 48 through every *other* layer in the lint — schema,
cross-file, family — and they produce **zero findings between them**,
because each parses to exactly the document the happy path parses to: a
trailing newline survives `json.loads`, a duplicate key is silently
resolved last-wins, and `30.0` is a JSON Schema `integer`. Nothing
downstream of the parse can see any of the four.

47 is the exception, and worth stating precisely rather than rounding off.
JCS does not normalize, so an NFD path *is* idempotent under
re-serialization — but it is a different document, so downstream layers do
see it: as a `proposed_sha256` disagreement between the goal file and the
diff that names it, and nothing more. The byte layer is what turns "some
hash does not match" into "`…/working_dir` is not NFC-normalized", which is
why §2.1 puts NFC in the lint rather than leaving it to the canonicalizer.

| # | Case | Broken input | Caught by |
| --- | --- | --- | --- |
| 44 | `44-pretty-printed-twin.json` | the happy goal file, indented | JCS idempotence |
| 45 | `45-trailing-newline.json` | canonical bytes plus `\n` | JCS idempotence |
| 46 | `46-duplicate-keys.json` | `schema_version` stated twice | duplicate-key parse |
| 47 | `47-non-nfc-path.json` | `working_dir` `/Users/josé/srv` in NFD | NFC check |
| 48 | `48-float-spelling-of-integer.json` | `"timeout_seconds":30.0` | JCS idempotence |
| 58 | `58-not-json.json` | a trailing comma — not JSON at all | parse |

Case 58 sits out of sequence with its neighbours because the numbering is
one series across both directories, and it was written last. It is 46's
sibling: both arrive through the same `except ValueError`, since
`JSONDecodeError` is one, and they are not the same finding. Bytes that
are not JSON are a proposer or transport bug; bytes that are two documents
in a trench coat are the §2.1 hazard, and rounding the second into the
first would lose exactly the distinction that layer exists to draw.

Case 48 is §13's "`15.0` spelling of `15`" instantiated on the integer this
fixture actually carries. Cases 44 and 48 are the pair §2.1 describes as
the joint float rule's two halves: the schema catches a true fraction
(case 43, `30.5`), byte identity catches the float *spelling* of an
integer — neither alone is enough.

## Projection class (`examples/broken-projection/`)

These are not broken *inputs*. Each is a broken **output** — a
`host_specific.json` a faulty or hostile projector might emit — and the
layer that refuses them is `validate_projection()` in `bin/projector.py`,
invoked over raw bytes for the same reason the byte class is: a
pretty-printed projection, a trailing newline and a float spelling all
parse to the document the golden parses to, so nothing downstream of the
parse can see them.

The mapping these enforce is decided in
`docs/architecture/projector-reconciliation-2026-08-16.md`; the `N-n` ids
below are that document's negatives.

| # | Case | Broken output | Caught by |
| --- | --- | --- | --- |
| 66 | `66-sibling-variables-key.json` | a `variables` key beside `vars` (N-2) | projection |
| 67 | `67-expansion-sequence.json` | a `$(` sequence in a value (N-3) | projection |
| 68 | `68-resolved-secret-value.json` | a real secret where a key name belongs (N-4) | projection |
| 69 | `69-device-trust-container.json` | trust content reaching `vars` (N-5) | projection |
| 70 | `70-pretty-printed-projection.json` | the golden, indented (N-6) | projection |
| 71 | `71-trailing-newline-projection.json` | golden bytes plus `\n` (N-6) | projection |
| 72 | `72-float-in-projection.json` | a float in the output (N-7) | projection |
| 73 | `73-canonified-interlock-id.json` | an entry id rewritten (N-9) | projection |
| 74 | `74-duplicate-id-across-containers.json` | one id under both kinds (N-10) | projection |
| 75 | `75-goal-file-under-vars.json` | the whole goal file under `vars` (N-12) | projection |
| 76 | `76-env-not-an-object.json` | `env` as an array carrying a real secret (N-4) | projection |
| 77 | `77-nan-not-representable.json` | `NaN` — accepted by `json`, unrepresentable in JCS (N-6) | projection |
| 78 | `78-decomposed-string-in-projection.json` | a decomposed (NFD) string, which JCS passes through (N-6) | projection |

Three of the twelve negatives have no row, and deliberately. N-1 (structure
must not change when only `state` flips) and N-11 (two runs agree) are
properties over *two* projections, not shapes one document can have; they
are checked by `check_projector_properties()` instead of being faked as
fixtures. N-8 is the 5 MiB ceiling, which a fixture could only express by
checking in a 5 MiB file.

Case 75 earns its place even though it is the shape a losing opinion
proposed: it is what a future editor reaches for when the include table
feels arbitrary, and it satisfies every check §13 had before the projector
layer existed.

Case 78 is the one case in this table that a *canonicalizer* cannot see.
Cases 70, 71 and 72 are caught by the JCS byte compare, because
re-canonicalizing them produces different bytes. Case 78 already **is** its
own JCS canonical form: JCS takes NFC as an input precondition and passes
anything else through untouched, so the byte compare agrees and only the
explicit NFC check dissents. Before it existed, deleting that check left
the whole gate green while `project()` emitted `cafe\xcc\x81` for a
`working_dir` of `/srv/café` — the ninth mutation the adversarial review at
`docs/paper/reviews/2026-08-16_opus-5-high_projector-gate-review.md` was
asked to find (its F3). It is deliberately the golden with one value
changed, so the NFC finding is the only one it produces and no second
defect can mask it.
