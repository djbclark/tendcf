# Negative fixtures

Twelve deliberately broken overlays. `bin/schema_lint.py` must catch every
one; a case that validates is a lint failure.

Each directory replaces the happy-path file of the same name under
`examples/`. The rest of the Site Model stays as in the happy path.

| # | Case | Broken input | Caught by |
| --- | --- | --- | --- |
| 1 | `01-opt-out-no-reason` | `comprehensive: false` with no `opt_out_reason` | schema |
| 2 | `02-opt-out-on-comprehensive` | `comprehensive: true` **with** an `opt_out_reason` | schema |
| 3 | `03-rogue-launchd-label` | launchd label `com.rogue.caddy` under no declared prefix | cross-file |
| 4 | `04-nested-writer-prefix` | prefix `com.djbclark.caddy.*` nested in `com.djbclark.*` | cross-file |
| 5 | `05-macos-no-launchd` | macOS service with no `launchd` block | schema (`if/then`) |
| 6 | `06-literal-secret` | `OPENAI_API_KEY: sk-live-abc123` (literal, not a key name) | schema |
| 7 | `07-typo-capability-kind` | `netwrok:tailnet` (typo'd capability kind) | schema |
| 8 | `08-unknown-role` | `role: llm-gatway` (unknown role) | cross-file |
| 9 | `09-enforce-audit-outcome` | enforce-mode row with `outcome: compliant` | schema |
| 10 | `10-invalid-release-stamp` | `release: NOT-A-STAMP` (outside the identifier pattern) | schema |
| 11 | `11-coverage-missing-field` | `domain_coverage` row missing `deliberately_unmanaged` | schema |
| 12 | `12-unknown-row-type` | `row_type: converged` (unknown row type) | lint discriminator |
