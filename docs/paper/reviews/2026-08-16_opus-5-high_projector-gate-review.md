# Adversarial implementation review — the projector gate

**Reviewer:** Claude Opus 5 at high effort, headless, 2026-08-16.
**Target:** `9325d0b..505393e`, chiefly `bin/projector.py` and the new
lint layers. **Prompt:** `prompt_projector-gate.txt`, beside this file.
**Brief:** can a projection be wrong under the reconciliation yet accepted,
or can the projector be changed to emit wrong bytes while `schema_lint`
still reports OK? Find a ninth mutation that does not bite.

**Outcome:** nine findings, four HIGH. F1 and F2 were reproduced and fixed
in `4971e05`, with fixtures 76 and 77 and mutations M9/M10 pinning them.
**F3-F9 remain OPEN** — see that commit message and the Tier 1 log.
F2 is the one to read first: a real secret value reached the projection
bytes with zero findings.

Dated artifact, pinned to the commits it reviewed. Do not edit to bring it
up to date.

---

## Adversarial review — `9325d0b..505393e`, `bin/projector.py` + linters

Reviewed against a clean `git archive 505393e` extracted to `/tmp/tendcf-review` (the live tree was dirty from a concurrent session, which has since landed `c94579e`/`10633fc` — those are outside this range and not reviewed). Nothing in `/Users/djbclark/src/tendcf` was modified.

---

### F1 — `validate_projection()` and `project()` crash instead of refusing, on JSON `json.loads` accepts · HIGH

`bin/projector.py:318` (`canonical = rfc8785.dumps(doc)`) and `:276` run before any guard. Python's `json` accepts `NaN`, `Infinity`, `-Infinity`, overflow literals (`1e999`), integers outside the IEEE-754 double domain, and lone surrogates — `rfc8785` raises on all of them.

```
$ ./bin/projector.py --check nan.json          # {"vars":{"tendcf_service":{"…":{"timeout":NaN}}}}
Traceback … rfc8785._impl.FloatDomainError: nan is not representable in JCS
$ ./bin/projector.py inf-goal.json             # goal file with Infinity
… FloatDomainError: inf is not representable in JCS          (not ProjectionRefused)
```
Fuzzing `project()` over plausible goal files also crashes on `2**70` (`IntegerDomainError`) and `"\ud800"` (`CanonicalizationError`).

Three consequences:
1. `main()` only catches `ProjectionRefused` (`:527`), so the docstring's contract — "a mapping bug becomes a refusal rather than a file on a device" (`:67`) — does not hold for this class. tendcf-agent reproducing this gets an uncaught exception device-side.
2. `validate_projection()` is documented as returning findings, "empty means OK" (`:476`). It raises.
3. `bin/schema_lint.py:717` calls `projector.validate_projection(case.read_bytes())` with **no** `try/except`. Dropping such a file into `examples/broken-projection/` aborts the whole lint mid-run — I verified `check_declaration_coverage()` and `check_class_coverage()` never execute. Ironically this is the N-7 class (floats), which is meant to be a *refusal*.

### F2 — N-4 defeated: a resolved secret in `env` passes when `env` is an array · HIGH

`bin/projector.py:419-420` guards the whole check with `if isinstance(env, dict):`. `project()` copies bodies verbatim (`:272`) and never schema-validates, so:

```python
"env": ["CADDY_ADMIN_TOKEN=sk-live-abc123"]
→ validate_projection(...) == []
```
Zero findings. This is attack 2 succeeding: a projection that is wrong under P-4/N-4 which `validate_projection()` accepts. The dict-value path is correctly strict (a non-string value *is* flagged) — it is only the container-type assumption that leaks.

### F3 — the ninth mutation: N-6's NFC half is unfixtured, so deleting it keeps the gate green · HIGH

There is no NFC case in `examples/broken-projection/` (66–75 cover N-2, N-3, N-4, N-5, N-6-JCS, N-7, N-9, N-10, N-12). Neutering `bin/projector.py:448` alone:

```
schema-lint: OK (8 schemas, 59 negative fixtures, 6 byte-class fixtures, 10 projection fixtures)
project(goal file with working_dir "/srv/café") → emits b"cafe\xcc\x81"   # decomposed
```
Lint green, projector emitting bytes N-6 forbids. The commit's eight mutations do not reach this check; it is guarded only by the golden, which contains no non-ASCII.

### F4 — `_shape()` is not sufficient for N-1: a `state` branch that rewrites list *order* is invisible · HIGH

`check_projector_properties()` compares `_shape()`, which erases leaf values and reduces a list to `[None]*len`. So a projector may branch on `state` and change output that `goal-file.schema.json:101` explicitly calls semantic ("An array because order is meaning"). Mutation applied at `bin/projector.py:272`:

```python
if _b.get("state") == "absent" and isinstance(_b.get("command"), list):
    _b["command"] = list(reversed(_b["command"]))
```
```
schema-lint: OK …                                    LINT EXIT=0
argv after state flip: ['/etc/caddy/Caddyfile', '--config', 'run', '/opt/homebrew/bin/caddy']
```
The golden cannot see it either: the example's only absent entry (`com.tendcf.caddy.retired`) is `state`-only, so it has no argv to permute. Direct answer to question 4: yes — a value decides real output, and N-1 as implemented cannot see it.

### F5 — N-9 defeated: Python's `$` matches before a trailing newline · MEDIUM

`bin/projector.py:139-142` restates the schema patterns using `re`, where `$` matches at end-of-string *or* before a final `\n`. JSON Schema `pattern` is ECMA-262, where it does not.

```
$ ./bin/projector.py --check nl-id.json      # interlock id "caddy-config-valid\n"
projector: OK (647 bytes)
```
An id no goal file can spell — the promiser and launchd label carrying a newline — is accepted. `SECRETSPEC_NAME` (`:147`) has the same quirk. Fix is `\Z`, not `$`. The docstring's claim that drift here "can only make the checker weaker than the schema" (`:86`) is true, and this is that weakness realized.

### F6 — a second hole in the `schema (...)` check, beyond the admitted `oneOf` one · MEDIUM

Two independent causes, both making wrong cells pass:

**(a) `_refs_along()` returns every `$defs` name stepped *through*, not the one that carries the failing keyword** (`schema_lint.py`, the `seen.add(name)` inside the walk). Ancestor container defs become claimable.
**(b) `items` in `APPLICATORS` is navigation, not a rule** — the same objection the comment raises to justify excluding `properties`/`additionalProperties`.

Verified green (each swap applied alone to `examples/broken/README.md`):

| case | declared | swapped to | result |
|---|---|---|---|
| 43 `float-timeout` | `type` | `` `state_domain` `` | OK, exit 0 |
| 34 `silenced-interlock-report` | `const` | `` `interlock_map` `` | OK, exit 0 |
| 5 `macos-no-launchd` | `if/then` | `` `items` `` | OK, exit 0 |

`state_domain` says nothing about why `timeout_seconds: 30.5` is caught. None of these is the `oneOf`-sibling case the commit documents. Evidence sets are wide generally — case 24 accepts 10 tokens, case 27 accepts 10.

### F7 — N-5's key-only trust check misses 3 of the corpus's own 4 device-trust bodies · MEDIUM

The docstring admits trust-in-a-value is not caught (`:73-76`), but understates the size. `TRUST_SHAPED_KEY` (`:152`) fires only on keys spelled `ed25519:`/`sha256:`. In `examples/goal-file.json`, only `advisor-key` puts the digest in key position; `agent` and `policy-tree` use key `"sha256"` with the digest in the *value*, and `trust-policy` has no digest at all. Verified:

```python
"tendcf-agent": {"sha256":"sha256:d4d4…","state":"present","version":"ops-v1.0.0"}
→ validate_projection(...) == []      # agent binary pin published to data:variables
```
So a naive "project device-trust too" regression is caught for 1 of 4 entry kinds, not for the domain.

### F8 — mutation coverage of `check_projection()` is 8/19; two N-5 mechanisms mutually mask each other · LOW

Neutering each `flag()` site in turn (bytecode caching disabled — it silently masked my first run):

| survives | site | rule |
|---|---|---|
| `:302` | >5 MiB | N-8 |
| `:312` `:315` `:335` `:367` `:384` `:417` | parse / type guards | — |
| `:358` | no top-level `vars` | P-6.3 |
| **`:373`** | **container not in `CONTAINERS`** | **N-5 / N-12 / P-1** |
| `:387` | empty container | P-6.4 |
| **`:449`** | **NFC** | **N-6** (F3) |
| **`:465`** | **trust-shaped key** | **N-5** |

`:373` and `:465` survive because fixtures `69-device-trust-container` and `75-goal-file-under-vars` each trip **both**. Deleting either leaves the lint green — so the closed-container rule that the commit's M7 credits with catching the tombstone-split ("caught… by the closed-container rule") is not independently guarded by any fixture.

### F9 — `check_family_canonical_bytes()`'s docstring is now false · LOW

`bin/schema_lint.py:382`: "Every `.json` fixture on disk is canonical bytes" — it iterates `EXAMPLES`, and `OUTPUT_ONLY_EXAMPLES` (`:117`) now removes `host_specific.json` from that set, so the induction that made the sentence true is gone. Substantively harmless: `check_projector_golden()` byte-compares against `rfc8785.dumps` output and runs `validate_projection(expected)`, which re-checks JCS, NFC and duplicate keys. It's the comment that's wrong, not the coverage.

---

## Attacks I tried that failed

**Against the gate (question 2), beyond F3/F4:** hiding `$(`/`@{` behind `\u0024`/`\u0040` escapes (caught twice — once after parse, once by the JCS byte compare); duplicate keys in projection bytes (`_reject_duplicate_keys`); a top-level `variables` or `classes` sibling; pretty-printing and trailing newline; a float anywhere; a non-string `env` value; a device-trust *container* name; the whole goal file under `vars`; a duplicate id across kinds. All refused. Mutating `PROJECTING_KINDS`, `CONTAINER_PREFIX`, `MAX_PROJECTION_BYTES` or the id patterns is caught by the golden or by a fixture.

**Over-strictness:** none found. `ENTRY_ID_PATTERNS`/`ENTRY_ID_MAX_LENGTH` (`:139-143`) are byte-identical to `goal-file.schema.json:79-80` and `common.schema.json#/$defs/identifier`; `SECRETSPEC_NAME` matches `env_map` exactly. An 18-case fuzz of malformed goal files produced no refusal of a schema-valid input.

**Question 3, `_refs_along()` walking wrong:** I could not make it walk into the wrong subtree or silently return nothing where a cell needed evidence — cross-document `$ref`s (`common.schema.json#/$defs/…`) terminate the walk, but no cell names one, so the documented limitation is real and currently untriggered. The holes I found (F6) are in what it *includes*, not where it goes.

**Question 5, linter weakening — the carve-outs hold.** `FROZEN` skips 53 of 81 documents, and I enumerated all of them: every one is under `docs/handoffs/`, `docs/paper/reviews/`, `docs/architecture/deprecated/`, or matches the opinion/adjudication patterns. No live document escapes. The `README.md` carve-in works (`frozen_reason()` returns `None` before pattern matching). `--all` still reports all 58 findings. Most importantly, I checked the self-serving case directly: `c9e4e0e` added the three `docs/architecture/projector-opinion-*.md` files **and** their `FROZEN` entry in the same commit — but those files have **zero** findings under `--all`, as does `2026-08-16_grok-4.6_r21-refutation.md`. The exemption hid nothing the session wrote. `OUTPUT_ONLY_EXAMPLES` likewise loses no real coverage (F9 is a comment defect, not a gap).

I did not find a case where `bin/projector.py` and the reconciliation's P-1..P-7 disagree on the mapping itself. P-6.3, P-6.4 and P-6.7 behave as specified under fuzzing, and the golden matches §8 at 645 bytes.
