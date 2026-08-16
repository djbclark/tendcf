# Negative fixtures

Forty-three deliberately broken overlays. `bin/schema_lint.py` must catch
every one; a case that validates is a lint failure.

Each directory replaces the happy-path file of the same name under
`examples/`. The rest of the Site Model (cases 1-12) or the goal-file
family (cases 13-43) stays as in the happy path.

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
| 31 | `31-unprefixed-host-key` | `host` with no `ed25519:` prefix | schema (pattern) |
| 32 | `32-uppercase-digest-hex` | `sha256:` digest with uppercase hex | schema (pattern) |
| 33 | `33-defaulted-expect-exit` | `pre_action` with no `expect_exit` | schema (`required`) |
| 34 | `34-silenced-interlock-report` | interlock `report: false` | schema (`const`) |
| 35 | `35-malformed-writer-prefix` | unit-writer prefix with no trailing `.*` | schema (pattern) |
| 36 | `36-unknown-writer` | `writer: custom-tool` | schema (`enum`) |
| 37 | `37-uppercase-domain` | domain key `Supervision` | schema (`propertyNames`) |
| 38 | `38-proposer-set-privileged-flag` | service entry with a `privileged: true` field | schema (`additionalProperties`) |
| 39 | `39-description-prose` | service entry with a `description` field | schema (`additionalProperties`) |
| 40 | `40-boolean-reason-coverage-spelling` | `coverage` as `{comprehensive, opt_out_reason}` | schema (`type`) |
| 41 | `41-embedded-release-stamp` | a stray top-level `release_stamp` field | schema (`additionalProperties`) |
| 42 | `42-malformed-advisor-key-id` | advisor-key property name not `ed25519:`+hex | schema (`propertyNames`) |
| 43 | `43-float-timeout` | `timeout_seconds: 30.5` | schema (`type`) |

The byte-class negatives reconciliation §13 also names (pretty-printed
twin, duplicate keys, non-NFC strings, `15.0` spelling of `15`) need the
new byte-class fixture mechanism §13 describes — raw bytes compared before
parsing — which is not built yet (§18 item 5, not this pass). They are not
in this table.
