# Independent review — libntech B-4 + B-10 stacked JSON-number series

**Reviewer:** Cursor Grok 4.6 (adversarial second-panel member).  
**Date:** 2026-08-17.  
**Trees:** `/Users/djbclark/src/libntech-fixes` @ `cc4a0d9` (`fix/json-number-fatal-exit`); `/Users/djbclark/src/core-json` @ `32c38f8ab` (`fix/json-number-rendering`); stock CFEngine Core 3.27.1 at `/opt/homebrew/bin/cf-{agent,promises}`.  
**Independence:** this file is the only write. No other `upstream-opinion-*.md`, no `docs/handoffs/`, no `b10-number-render-measurement-2026-08-17.md`. Prefer measurement; four listed build traps were controlled as noted in §Traps.

---

## 1. Verdict

**Ship with changes.**

The load-time severity claim is true. The stack is the right topology. B-4 is correct. I would not send this to Northern.tech until the three items below are done; none of them is a reason to unstack or to drop B-4.

1. **Add a `MustacheRender()` regression in libntech** (or land the equivalent as data in core's `tests/unit/data/mustache_extra.json` in the same coordinated change). `mustache.c` is patched and **no test under `tests/unit` calls `MustacheRender()`**. `json_test` covers the parallel `JsonPrimitiveToString()` path only. I measured mustache myself against the patched archive; the series as offered does not.
2. **Disclose the residual fatal API in the `security@` mail**, do not pretend the process-exit class is gone: `JsonPrimitiveGetAsInteger()` (and `JsonPrimitiveGetAsInt64ExitOnError()`) still call `StringToLongExitOnError()` / `StringToInt64ExitOnError()`. I confirmed the former still kills a process on `9223372036854775808` against the patched library. Production callers of the integer getter in **both** trees look clear after core's half; the function remains a footgun on the public header.
3. **Add `Changelog: None` (not a fake `Ticket:`)** before the PR, or be ready for CONTRIBUTING.md to bounce the series. Inventing a ticket number is still a mistake. `Changelog: None` is the documented escape hatch until an issue exists.

Do not land B-10 without B-4. Do not squash in a way that drops B-4's real-lexeme behaviour while keeping exponent-as-REAL classification.

---

## 2. Severity verdict

**`security@`, not the ordinary bug channel.** The load-time claim is right.

### Load-time claim — reproduced, not inferred

Policy used (verbatim from the brief), plus `numbers.json` containing `{"n": 9223372036854775808}`:

- Stock `/opt/homebrew/bin/cf-promises` **3.27.1**, default workdir `~/.cfagent` with **no** `host_specific.json`:
  ```
  error: Conversion error (34 - Overflow) on '9223372036854775808' (StringToLongExitOnError)
  exit=1
  ```
- Negative control, same policy, `{"n": 42}`: `cf-promises` exit 0.
- `lldb` breakpoint on `StringToLongExitOnError` conditioned on `$arg1 == "9223372036854775808"`:
  ```
  StringToLongExitOnError
  JsonCopy                 ; JsonPrimitiveCopy is static and inlined (JsonCopy + 316)
  JsonObjectCopy
  RvalNewRewriter
  VerifyVarPromise
  ExpandPromise
  BundleResolvePromiseType
  PolicyResolve
  LoadPolicyFile
  LoadPolicy
  main                     ; cf-promises
  ```
  Matches the offered stack. There is no mustache frame, no iteration frame, no `string_mustache()`.
- Stock `cf-agent -K -I` with `cf-promises` in the isolated workdir `bin/` (so validation is not skipped):
  ```
  error: Conversion error (34 - Overflow) on '9223372036854775808' (StringToLongExitOnError)
  error: Policy failed validation with command '"…/bin/cf-promises" -c "…/load.cf"'
  error: CFEngine was not able to get confirmation of promises from cf-promises, so going to failsafe
  R: FAILSAFE_RAN
  ```
- Core's half is **not sufficient**. `/Users/djbclark/src/core-json/cf-promises/cf-promises` (libtool wrapper, `DYLD_LIBRARY_PATH` → build-tree `libpromises` dated 2026-08-17 07:02, not the Aug 15 prefix) still dies on the same policy with the same overflow error. Vendored `core-json/libntech` is still stock.

Also fatal at **policy-load, declare-only** on stock 3.27.1, same shape (`readjson` + report `"loaded"` only):

| input | `cf-promises` |
|---|---|
| `1e-8` | `Conversion error (-83 - Not terminated) on '1e-8'` |
| `2e0` | same, `'2e0'` |
| `1e400` | same, `'1e400'` — stock never emits `inf`; it dies |

`readjson()` of a **bare** top-level number is not this bug: stock rejects `non-container` and exits 0. The object/array wrapper in the claim is required.

### A quieter bug is worse than the crash

`JsonPrimitiveCopy()` going through `JsonIntegerCreate(int)` silently narrows any integer that fits a `long` but not an `int`. Stock `cf-agent` reports, no failsafe:

| JSON number | reported `$(d[n])` |
|---|---|
| `2000000000000` | `-1454759936` |
| `9223372036854775807` (`LONG_MAX`) | `-1` |
| `1786965915908` (epoch **milliseconds**, this morning) | `259520772` |

That last one is not a synthetic overflow. Millisecond timestamps have been larger than `INT_MAX` since 2001. A `readjson()` of ordinary telemetry, a CMDB nested object, or an API payload that uses epoch-ms will load, validate, and then use the wrong number.

`host_specific.json` with an **innocent** policy (`safe.cf`, value 42) is enough on stock:

- `{"vars": {"huge": 9223372036854775808}}` — `cf-promises` dies (`JsonPrimitiveToString` → `StringToLongExitOnError`).
- `{"vars": {"huge": {"n": 9223372036854775808}}}` — same, via `JsonCopy`.
- `{"vars": {"tiny": 1e-8}}` — dies (`Not terminated`).
- `{"vars": {"meta": {"ts": 1786965915908}}}` — does **not** die; `cf-agent` reports `meta=259520772`.

A CMDB nested object containing a millisecond timestamp is silent corruption, not failsafe. A CMDB primitive that does not fit a `long`, or `1e-8` without a decimal point, is failsafe with no user `readjson()` at all.

### Channel and threat wording

Their wording is **honest, not overstated**:

> *"attacker-controlled" is overstated for a remote exploit; it is honest for a CMDB operator, a `readjson()` of third-party JSON, or an author who writes scientific notation by mistake.*

I would keep that sentence in the `security@` mail and add one concrete non-attacker integrity case: **epoch milliseconds inside a JSON object**. That does not need a hostile operator and does not failsafe.

`security@` is the right first contact because (a) `cf-promises` abort → `cf-agent` failsafe is a control-plane availability failure, (b) the input is often not the policy author (CMDB, `readjson` of vendor/cloud JSON), (c) the silent `int` narrowing is an integrity failure that looks like a successful run. An ordinary bug ticket will under-weight (c).

I did **not** reproduce the offered second stack (`EvalContextVariablePutSpecial` ← `DetectEnvironment`) with a huge `sys.*` value on this Mac. The code path is real (`VariableTablePut` → `RvalCopy` → `JsonCopy` for every container put, including `sys.inet`), but `unix_iface.c` fills those containers from `/proc` via `JsonObjectAppendInteger` (`int`), which cannot originate a `LONG_MAX+1` lexeme. Treat that trace as **code-plausible for any `sys.*` container that was itself parsed from JSON**, not as something I drove.

---

## 3. Topology verdict

**Keep the stack, B-4 under B-10. Do not ship B-10 alone. Do not combine into one commit unless upstream asks to squash at merge.**

Measured, not argued:

- **B-10-only real render** (patched `json.o` so `1e400` is `REAL`, stock `mustache.o` so reals still go through `StringFromDouble` / `"%.2f"`): `MustacheRender("{{n}}")` of `1e400` is **`inf`**. Same function on the full stack is **`1e400`**. Independently, against the patched library, `StringFromDouble(JsonPrimitiveGetAsReal("1e400"))` is `inf` while `JsonPrimitiveToString` is `1e400`. Stock never produced `inf`; it classified `1e400` as `INTEGER` and died. `inf` is introduced by classification-as-REAL without B-4's lexeme render.
- **B-10-only vs B-4+B-10 mustache** (patched parser + stock mustache vs full stack):

  | value | B-10-only mustache | full stack |
  |---|---|---|
  | `0.00049` | `0.00` | `0.00049` |
  | `1e-8` | `0.00` | `1e-8` |
  | `1.5e3` | `1500.00` | `1.5e3` |
  | `1e400` | `inf` | `1e400` |

  Matches the table in the brief. I did not run product-level `cf-agent` against a B-10-only **cf-promises** (that would have meant editing a tree). The mustache mix is the same functions `string_mustache()` calls.
- Core's `6a4216dad` fixing integers and reals in one commit is the right *core* shape because those two call sites are twins. Libntech has two different mistakes (classification/fatal integer vs `"%.2f"` real) that were recorded separately and that **break each other's tests** if reordered. Stacked commits are the right *libntech* shape. Upstream may squash; the PR description should say B-4 cannot be dropped.

---

## 4. Defects found

### In the unfixed product (this is the bug the series repairs)

| id | where | what | verified? |
|---|---|---|---|
| D1 | `libutils/json.c` `JsonPrimitiveCopy` (stock: INTEGER → `JsonIntegerCreate(JsonPrimitiveGetAsInteger)`, REAL → `JsonRealCreate`) | Copy of a parsed number rebuilds from a C type. Past `LONG_MAX` / `1e-8`: **process exit** at load via `RvalNewRewriter`. Fits `long` not `int`: **silent narrow**. Reals: `"%.4f"` rewrite (`0.00049` copies as `0.0005`). | **Verified** stock 3.27.1 + lldb; patched `JsonCopy` preserves lexeme and type. |
| D2 | `JsonPrimitiveToString` / mustache INTEGER (stock) | Same fatal conversion on render. | **Verified** stock `1e400`/`1e-8` at load (copy happens first). CMDB primitive uses ToString and dies on `9223372036854775808`. |
| D3 | `JsonPrimitiveToString` / mustache REAL (stock) | `"%.2f"` via `StringFromDouble`. `0.00049` → `0.00` (wrong value). | **Verified** stock `cf-agent`: `R: mustache=0.00`. Unfixed `ToString=0.00`, `WriteCompact=0.00049`. |
| D4 | `JsonParseAsNumber` (stock: `if (seen_dot)`) | Exponent without a dot stored as INTEGER. | **Verified** stock load of `1e-8`/`2e0`/`1e400`; unfixed `json_test` `test_parse_exponent_numbers` `7 != 6`. |
| D5 | `JsonSelect` array index via `StringToLongExitOnError` (stock) | Oversized all-digit index kills the process. | **Verified** against patched: returns NULL. Against unfixed `json_test`, the new test is registered after an aborting case (see D8) so I did **not** see that test body run on unfixed; the old call site is still in `0c0620d`. |
| D6 | `JsonIntegerCreate(int)` (unchanged public API) | Any C caller passing a `long` silently truncates. The copy bug is this API used on parsed lexemes. | **Verified** by calling the old copy path on the patched lib: `2000000000000` → stored `-1454759936`; `LONG_MAX` → `-1`. |

### In the patch series (things I would still change or call out)

| id | where | what | verified? |
|---|---|---|---|
| D7 | `libutils/mustache.c` 389–400 (`cc4a0d9` tree) | Behaviour change is right; **no `MustacheRender` test in libntech**. Data files `tests/unit/data/mustache_*.json` exist and are unused here; core's `mustache_test.c` is the consumer. | **Verified** grep: no `MustacheRender` under `tests/unit`. |
| D8 | `tests/unit/json_test.c` registration order | `test_primitive_to_string_numbers` aborts the **whole binary** on unfixed at `9223372036854775808`, so `test_copy_preserves_numbers`, `test_select_oversized_array_index`, and `test_real_renders_as_parsed` never run against the bug they describe. Against the **fixed** tree they all run (74/74 in `json_test`). CI on HEAD is fine; bisect / “does this test fail on unfixed?” is not, for anything after the first abort. | **Verified** unfixed `json_test`: exponent test fails, then ToString aborts, later tests skipped. Isolated unfixed program shows `0.00049` ToString `0.00`, copy `0.0005`. |
| D9 | `json.c:860` `JsonPrimitiveGetAsInteger` | Still fatal. No remaining production callers in libntech; core-json remaining production uses are comments plus `tests/unit/policy_test.c` (self-emitted line numbers). | **Verified** patched harness child dies. Census: grep both trees. |
| D10 | `JsonSelect` `json.c:968–975` | `StringIsNumeric("")` is true (empty loop). `StringToLong("")` fails → NULL. Harmless after the fix; on stock it would have been `ExitOnError`. Not worth a separate commit. | **Verified** `StringIsNumeric("")=1`, patched select NULL. |
| D11 | CONTRIBUTING.md (core, via libntech pointer) | No `Changelog:` / `Ticket:` trailers. Deliberate, but a likely bounce. Six commits vs “usually one”. | Inspection, not a runtime defect. |

I did not find a leak or double-free in `JsonPrimitiveCopy`. Numbers are `xstrdup`'d onto the heap; `JsonDestroy` frees non-bool/non-null primitive values. Bool/null still intern static strings and skip `free`. Type is preserved (`orig_type` == `copy_type` for INTEGER=6 and REAL=7 in the harness).

---

## 5. The eight questions

### 1. Is the load-time severity claim right?

**Yes.** Reproduced on stock 3.27.1 and on core-json (core's half + stock libntech). `security@` is the correct channel. Threat wording is honest; add epoch-ms as a non-attacker integrity example. See §2.

`type()` (not `datatype()` — the policy function is `type()`, detail bit → `"data int"` / `"data real"`) of `2e0` cannot be observed on stock: load dies first.

### 2. Is stacking B-4 under B-10 the right call?

**Yes**, versus combined, versus B-10 alone with `inf` disclosed.

`inf` is a defect B-10 **introduces** on the real axis and B-4 **removes**. Disclosing it is not an acceptable substitute for not emitting it. Combined would hide that split from review; core's one-commit half is a different file pair. Keep the stack; squash only if the maintainer asks.

### 3. Is B-4 correct at all?

**Yes.** Returning the parsed lexeme is the only render that (a) is not a wrong value for `0.00049`, (b) agrees with `JsonWriteCompact()`, (c) does not print `inf` for `1e400`, (d) does not invent decimal places (`0.5` → `0.50` under `"%.2f"`).

`1.5e3` rendering as `1.5e3` rather than `1500.00` is a **format** change, not a value change. Numeric consumers that `sscanf`/`strtod` still get 1500. String-equal consumers of `"1500.00"` will notice. The commit message already flags this. I would keep it: inventing `1500.00` was the bug.

`JsonRealCreate()` still uses `"%.4f"` for C-constructed reals. Out of scope; copy of those values now preserves that already-rounded string, which is copy-equals-original.

### 4. Is returning the raw lexeme safe for every producer of a primitive?

Producers audited:

| producer | stored text | emit-verbatim? |
|---|---|---|
| `JsonParseAsNumber` | JSON number token (`[minus] int [frac] [exp]`) | Yes. RFC 8259 lexeme. |
| YAML scalars (`json-yaml.c:107–118`) | Same parser when the scalar parses as a number | Yes. |
| `JsonIntegerCreate` / `Create64` | `"%d"` / `PRIi64` | Yes. Decimal digits. |
| `JsonRealCreate` | `"%.4f"`, non-finite coerced to `0.0` | Yes. Already a formatted decimal. |
| `JsonStringCreate` | `xstrdup` of caller text | Unchanged (string case already emitted the stored pointer). |
| `JsonBoolCreate` / `JsonNullCreate` | interned `"true"`/`"false"`/`"null"` | Unchanged; not on the new path. |

A stored number string is not HTML, not a mustache tag, not a shell word unless a **later** consumer fails to escape it — same as today for `JsonWriteCompact()`. Residual: JSON allows an arbitrarily long numeral; we now copy and emit it instead of crashing. That is availability-positive. Parser already accepted the document.

I do not want a parsed number lexeme fed to a shell without the escaping CFEngine already applies to scalars; that is not new.

### 5. Is the `JsonPrimitiveCopy()` change complete and correct?

**Yes**, for ownership, lifetime, and type.

```c
return JsonElementCreatePrimitive(type, xstrdup(primitive->primitive.value));
```

- Heap duplicate; original kept. `JsonDestroy` frees it.
- `type` is the original `JsonPrimitiveType`, so INTEGER stays INTEGER even when the lexeme does not fit a `long`.
- Callers of `JsonCopy` (object/array recursion, `RvalNewRewriter`, CMDB/augments container install, `JsonExpandElement` non-strings, `evalfunction.c` merges, `unix_iface.c` `default_route`) all take ownership of the new tree and destroy the old one as before.

No production path constructs a number primitive with a non-owned buffer except bool/null, which this change does not touch.

### 6. Is classifying exponent numbers as REAL a compatibility break?

Consumers of `JsonGetPrimitiveType()` INTEGER vs REAL in **core-json**:

- `type(..., "true")` / `DataTypeStringFromVarName` (`evalfunction.c:5963–5967`) — `"data int"` vs `"data real"`.
- `mustache.c` switch — both cases now emit the lexeme on the full stack.
- `rlist.c` / `iteration.c` — both cases already `GetAsString` after core's half.
- `unix_iface.c:1438` — metric must be INTEGER. Source is `/proc` hex/decimal captures, then compared with `StringToLong`. An exponent metric would skip the route; **not** a realistic `/proc` token.
- `eval_context.c:3714` — only special-cases STRING for expansion; numbers are `JsonCopy`.

On stock, `2e0` never survives a container put, so `"data int"` for exponent-without-dot was **not a live observable** for `readjson`/CMDB containers. Replacing a crash with `"data real"` is not worse. `1.5e3` was already REAL (has a dot); only its **render** changes (B-4).

### 7. What did the fix miss?

`JsonPrimitiveGetAsInteger()` is still fatal **by construction** (`json.c:866` → `StringToLongExitOnError`).

**libntech-fixes production:** definition only. Tests still call it on small integers.

**core-json production after their half:** no live calls. Remaining hits are comments in `rlist.c`, `generic_agent.c`, `unix_iface.c`, plus `tests/unit/policy_test.c` (line numbers from `PolicyToJson`, produced by CFEngine as small ints).

**Unpatched `cfengine-core` (not this series, census only):** `rlist.c`, `iteration.c`, `generic_agent.c` timestamp, `unix_iface.c` metric — the four sites core-json already fixes.

I agree those four were the twins. I did not find a fifth production caller of `JsonPrimitiveGetAsInteger` on parsed data in either tree.

Still-fatal cousins, tests-only: `JsonPrimitiveGetAsInt64ExitOnError`. `FnCallFold` uses `JsonPrimitiveToString` then `sscanf %lf` — after this fix, `sum()` of `1e400` becomes a non-fatal `inf` in the fold, which is a later evaluation quirk, not load-time death.

`JsonIntegerCreate(int)` remains a silent-narrow API. Not required for this series; worth a sentence in the mail so nobody “fixes” copy by going back to it.

### 8. Are the regression tests any good?

**Mostly, with one structural hole and one missing surface.**

Would they fail against unfixed code? Measured by linking HEAD `json_test.o` against `json.o`/`mustache.o` compiled from `0c0620d`, plus an isolated unfixed ToString program:

| test | against unfixed |
|---|---|
| `test_parse_exponent_numbers` | **Fails** (`REAL` expected, `INTEGER` got) without aborting. Good. |
| `test_primitive_to_string_numbers` | **Aborts** on `9223372036854775808`. Proves the defect; kills the rest of the file. |
| `test_copy_preserves_numbers` | Not reached after that abort. Isolated: copy of `0.00049` is `0.0005`. |
| `test_select_oversized_array_index` | Not reached. |
| `test_real_renders_as_parsed` | Not reached. Isolated: `0.00049` ToString `0.00`, `0.5` ToString `0.50`. |

Against the **fixed** tree, after top-level `make -j2` and `rm -f tests/unit/json_test` + relink: `json_test` 74/74, `make check` inside `tests/unit` **39/39**.

`libntech has no mustache test at all` is true for `MustacheRender()`. Proposing core's spec-driven `mustache_test.c` + new rows in `mustache_extra.json` is the **right move**, with one caveat: those rows will **abort `mustache_test`** until libntech is fixed, because `MustacheRender` on stock still converts integers through `GetAsInteger`. Land extra.json **with** the libntech bump, not before.

Core's `rlist_test.c` `test_from_container_numbers` is registered immediately after `test_copy` and **does run** (wrapper `DYLD_LIBRARY_PATH` → build-tree libpromises). It passed; then `test_rval_to_scalar2` aborted as documented. Appending it at the end of that file would have been vacuous. They placed it correctly.

---

## 6. Traps — how they were controlled

1. **`make check` inside `tests/unit` does not rebuild `../libutils`.** Top-level `make -j2` first (`libutils.a` already current, 07:13:41). Then `rm -f tests/unit/json_test` and `make -C tests/unit json_test` (relink 07:21:39). `otool -L json_test`: no libutils dylib, static archive + pcre/ssl/yaml.
2. **`make -C tests/unit <test>` does not relink on a changed archive.** Binary deleted before relink, as above.
3. **`git stash` of a committed file is a no-op.** Unfixed comparison used `git show 0c0620d:libutils/json.c` (and `mustache.c`) compiled in `/tmp`, never `checkout`/`stash` in the worktree.
4. **`.libs/` binaries vs installed prefix; `DYLD_*` stripped on `cf-agent`→`cf-promises`.**  
   - Stock measurements: `/opt/homebrew/bin/cf-*`, `otool -L` → Cellar 3.27.1. Isolated workdir with **symlink** of that `cf-promises` into `bin/` so the child is the same binary, not a missing validator.  
   - core-json: **wrapper** `cf-promises/cf-promises`, not `.libs/cf-promises`. Wrapper sets `DYLD_LIBRARY_PATH` to `libpromises/.libs` (07:02:11). Installed `/Users/djbclark/opt/cfengine-dev/lib/libpromises.3.dylib` is **Aug 15 17:01** and was not used for those runs.  
   - Patched libntech: custom `/tmp` executables linked to `libutils/.libs/libutils.a`, `otool -L` shows no CFEngine dylib.  
   - core-json `rlist_test`: wrapper, not `.libs/`.

`rlist_test` XFAIL abort after `test_rval_to_scalar2`: observed; the new test is before that point.

---

## 7. What you did not check

- Product-level **patched** `cf-promises`/`cf-agent` (would require relinking core against this libntech; I refused to modify `core-json`/`cfengine-core`). Load-time **fix** is inferred from `JsonCopy`/`MustacheRender` on the patched archive plus the stock crash on the exact `JsonCopy` path.
- Each of the six commits green **on its own** (would have meant checking out files in a git worktree). I only built/tested `HEAD`.
- 32-bit `long` (the crash becomes any integer past `2^31-1`; I only ran arm64 LP64).
- Windows / Linux.
- Enterprise / Mission Portal CMDB writers beyond `host_specific.json` shape.
- The `DetectEnvironment` / `sys.*` stack as a live huge-number trigger.
- `def.json` / augments (same `JsonPrimitiveToString` / `JsonCopy` shapes as CMDB; not driven).
- ASAN/LSAN (ownership reviewed, not instrumented).
- `json_test` death-test isolation (see D8).
- Whether a maintainer changelog linter fails without `Changelog:`.

---

## 8. Maintainer pushback to expect

- Six commits, CONTRIBUTING “usually one”; offer to squash at merge, keep B-4 visible in the PR body.
- `1.5e3` format change (already in the B-4 message).
- `Changelog: None` until a Jira/GitHub issue exists.
- `Co-Authored-By: Claude Opus 5` — fine if that is house style; some projects strip it.
- Comments are long; they are accurate. I would not shorten them into something that re-hides `JsonIntegerCreate(int)`.
- Residual public `JsonPrimitiveGetAsInteger()` still exits. Say so in the mail rather than wait for a reviewer to find it.

---

## 9. Suggested `security@` facts (measured here, usable verbatim)

On CFEngine 3.27.1 / current libntech, a JSON number is rebuilt from a C type on every copy. Storing a JSON object as a CFEngine data variable copies it at policy load (`VerifyVarPromise` → `RvalNewRewriter` → `JsonCopy` → `JsonPrimitiveCopy`). Therefore:

- `9223372036854775808` or `1e-8` in a file loaded by `readjson()`, or in `host_specific.json`, aborts `cf-promises` and sends `cf-agent` to failsafe. No mustache, no iteration, no use of the value is required.
- `1786965915908` (epoch milliseconds) in the same object loads successfully and becomes `259520772`.
- Core-only repairs of list/iteration rendering do not close the load-time copy.

That is the report. The patches under review close the copy, the render, the classification, and the `JsonSelect` index, if B-4 stays under B-10.
