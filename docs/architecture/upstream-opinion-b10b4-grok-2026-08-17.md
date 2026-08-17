# Second-panel opinion — B-4 + B-10 stacked (libntech JSON numbers)

**Reviewer:** grok (independent adversarial gate).
**Date:** 2026-08-17.
**Tree:** `/Users/djbclark/src/libntech-fixes`, branch `fix/json-number-fatal-exit`, `0c0620d..cc4a0d9` (six commits).
**Consumer tree used for source census only:** `/Users/djbclark/src/core-json`, branch `fix/json-number-rendering`.
**Product baseline:** stock CFEngine 3.27.1 at `/opt/homebrew/bin/cf-{promises,agent}` (otool: Cellar `libpromises.3.dylib`).
**Nothing sent upstream.** This file is the only write.

I did not read any other `upstream-opinion-*.md`, `docs/handoffs/`, or `docs/architecture/b10-number-render-measurement-2026-08-17.md`.

---

## 1. Verdict

**Ship with changes.**

The load-time severity claim is right. The stack fixes the defects it names. I could not make the unfixed library or stock 3.27.1 survive a policy that merely declares `data => readjson(...)` of `9223372036854775808`, and I could not make the stacked library die or corrupt the same values.

Do not ship until these are done:

1. **Do not offer B-10 without B-4, and do not present the six commits as independently landable.** Full B-10 (classify + integer lexeme render + copy, no B-4) introduces `1e400 → inf` on `JsonPrimitiveToString()` / mustache and turns `1e-8` into `0.00`. I measured that. The stack already has B-4 at the bottom; the filing and the PR description have to say the real-axis commits land together.
2. **Fix the stale comment** in `tests/unit/json_test.c` (`CheckNumberIsReal`, currently lines 1278–1281). It still says rendered-real formatting “belongs to `StringFromDouble()` and is not asserted here.” After B-4 that is false; the next commit in the same stack asserts the opposite.
3. **Pin the in-memory producer path.** Every new test parses a lexeme. After this stack, `JsonRealCreate(0.5)` renders as `0.5000` (the stored `"%.4f"`), not `0.50`. I measured both sides. That is the intended invariant (agree with `JsonWriteCompact`), but nothing in the new tests would catch a regression that only broke `JsonRealCreate` → `ToString` / mustache.

Non-blocking, but a maintainer will reasonably say it: six commits and no `Changelog:` / `Ticket:` trailer. Omitting a phantom ticket is correct. Expect a request to squash toward “one fix + tests” and to add trailers once an issue number exists.

---

## 2. Severity verdict

**`security@northern.tech`, not the ordinary bug channel.**

The load-time claim is **verified**, not inferred.

Stock 3.27.1, policy that only declares a `data` variable (no iteration, no mustache, no render of the value):

```
body common control { bundlesequence => { "test" }; }
bundle agent test
{
  vars:
      "d" data => readjson("$(sys.policy_entry_dirname)/numbers.json", 100000);
  reports:
      "loaded";
}
```

with `numbers.json` = `{"n": 9223372036854775808}`:

| binary | result |
|---|---|
| `cf-promises -f load.cf` | `Conversion error (34 - Overflow) on '9223372036854775808' (StringToLongExitOnError)`, **exit 1** |
| `cf-agent --workdir /tmp/b10b4-wd -K -f load.cf` (cf-promises installed in that workdir’s `bin/`) | same conversion error from the child, then `Policy failed validation` → **failsafe** |
| same agent, same workdir, `{"n": 42}` | `R: loaded`, exit 0 |

lldb, breakpoint on `StringToLongExitOnError` conditioned on `x0 == "9223372036854775808"` (ARM64, return type of `strcmp` cast):

```
StringToLongExitOnError
JsonCopy                          /* JsonPrimitiveCopy inlined */
JsonObjectCopy
RvalNewRewriter
VerifyVarPromise
ExpandPromise
BundleResolvePromiseType
PolicyResolve
LoadPolicyFile
LoadPolicy
main                              /* cf-promises */
```

Argument at the fatal frame: `"9223372036854775808"`. That is the claimed stack.

The same conversion error also fires, still at load, with no user policy that names the value:

- `host_specific.json` / CMDB: `--workdir` + `/data/host_specific.json` `{"vars":{"evil":9223372036854775808}}` → verbose `Loaded CMDB data file '...', installing contents` then the overflow. **exit 1.**
- `def.json` next to the policy: same death.

An unconditioned breakpoint hits earlier, on `DetectEnvironment` → `GetSysVars` → `EvalContextVariablePutSpecial` → `JsonCopy`, with `x0 == "501"` (a uid). That is the same copy path running on `sys.*` containers before any user policy. It is not the crash; it shows the copy sits on the start-up path for every agent.

The crash is not the only load-time effect. On stock, `cf-promises --show-vars` of a successfully loaded container already holds the silently narrowed copy:

| input | stored in `default:test.d` on stock 3.27.1 |
|---|---|
| `2000000000000` | `-1454759936` |
| `9223372036854775807` (`LONG_MAX`) | `-1` |
| `1755400000000` (a current millisecond timestamp) | `-1241624064` |
| `4294967296` (`2^32`) | `0` (library probe of the unfixed copy) |
| `0.00049` | `0.0005` (and mustache of the same value is `0.00`) |
| `3.14159265` | `3.1416` |

`1e-8` and `1e400` also kill `cf-promises` at load on stock (`Conversion error (-83 - Not terminated)`), because they are classified INTEGER and the copy goes through `StringToLongExitOnError`. The first panel’s “rendering defect” framing is too narrow for those as well.

**Threat wording.** The proposed sentence is honest and not overstated:

> *"attacker-controlled" is overstated for a remote exploit; it is honest for a CMDB operator, a `readjson()` of third-party JSON, or an author who writes scientific notation by mistake.*

Who actually controls the input, on a real deployment:

- **CMDB / `host_specific.json`:** Mission Portal / an operator with CMDB write. I killed stock `cf-promises` with that file alone.
- **`def.json` augments:** policy authors and whoever can write the input directory.
- **`readjson()` of third-party JSON:** package indexes, cloud metadata, API dumps, CMDB exports. A millisecond timestamp is not exotic; stock already stores `1755400000000` as `-1241624064`.
- **Scientific notation by mistake:** `1e-8` is a load-time death on stock, not a later render surprise.
- **Remote unauthenticated attacker:** only if they can already write one of those files. That is not a network RCE. It is still a trusted-data availability + integrity failure of the configuration engine.

`security@` is the right first inbox so Northern.tech can choose embargo vs public issue. It is CWE-681 / CWE-190 sitting on the policy-load and CMDB-install path, plus failsafe. It is not a remote exploit and the filing must not say it is.

The silent `int` narrowing is the worse everyday bug. The overflow death is the one that takes a host off policy. Both belong in the same note.

---

## 3. Topology verdict

**Stacked, one PR, land together. Not B-10 alone. Combining the two fix commits is acceptable; shipping B-10 first with `inf` disclosed is not.**

I rebuilt `json.c` + `mustache.c` from three SHAs into throwaway archives in `/tmp` (object member names `json.o` / `mustache.o`, so `ar r` actually replaced the HEAD members) and ran the same probe:

| value | unfixed `0c0620d` | B-10 full `811d159` (copy + classify, no B-4) | stacked `cc4a0d9` |
|---|---|---|---|
| `0.00049` | to_string/mustache `0.00`, copy `0.0005` | to_string/mustache `0.00`, copy `0.00049` | `0.00049` throughout |
| `1e-8` | type INTEGER, **exits** | type REAL, to_string/mustache `0.00`, copy `1e-8` | `1e-8` throughout |
| `1.5e3` | to_string/mustache `1500.00`, copy `1500.0000` | to_string/mustache `1500.00`, copy `1.5e3` | `1.5e3` throughout |
| `1e400` | type INTEGER, **exits** | type REAL, to_string/mustache **`inf`**, copy `1e400` | `1e400` throughout |
| `9223372036854775808` | **exits** on ToString | exact, copy survives | exact |
| `2000000000000` | copy `-1454759936` | copy exact | copy exact |

B-10’s first commit alone (`f92cd1c`, no copy) is worse than that table: oversized integers still die on `JsonCopy`, and `1e400` **copies as `0.0000`** because `JsonRealCreate` maps non-finite doubles to `0.0`. The copy commit is the load-time fix. B-4 is what stops B-10 from introducing `inf` and from turning `1e-8` into `0.00`.

HEAD’s new tests against the B-10-full archive fail exactly two cases, both real rendering: `test_primitive_to_string_numbers` and `test_real_renders_as_parsed` (`"0.00049" != "0.00"`), exit 2. That is the measured reason they are not independently landable on the real axis.

core’s half (`6a4216dad`) already fixes integers and reals in one commit. A combined libntech fix commit would match that. A stack of “B-4, B-4 test, B-10, B-10 tests, copy, select-test” is reviewable and is what I reviewed. Either shape is fine. Two PRs, or B-10 merged first, is not.

---

## 4. Defects found

### Verified — in unfixed stock / `0c0620d` (the bugs the stack exists to fix)

| what | where | how I reproduced |
|---|---|---|
| Load-time death on oversized integer via `JsonPrimitiveCopy` | stock `libpromises` `JsonCopy`; source `json.c:JsonPrimitiveCopy` → `JsonPrimitiveGetAsInteger` → `StringToLongExitOnError` | policy above; lldb stack; exit 1 |
| Same death on `1e-8` / `1e400` / `2e0` (classified INTEGER) | `JsonParseAsNumber` branched on `seen_dot` only | stock `cf-promises`, and unfixed probe (`type=6`, then exit `-83 Not terminated`) |
| Same death from CMDB / augments | `host_specific.json`, `def.json` | `--workdir` and policy-dir `def.json` |
| cf-agent failsafe | stock agent, isolated workdir | dying policy → failsafe; `{"n":42}` → `R: loaded` |
| Silent `int` narrowing on copy | `JsonIntegerCreate(int)` vs `GetAsInteger()` → `long` | stock `--show-vars`: `2000000000000`→`-1454759936`, `LONG_MAX`→`-1`, `1755400000000`→`-1241624064` |
| Real copy via `"%.4f"` | `JsonRealCreate` | stock `--show-vars`: `0.00049`→`0.0005`, `3.14159265`→`3.1416` |
| Real render via `"%.2f"` | `JsonPrimitiveToString` / mustache | stock mustache: `tiny=0.00` for `0.00049` |
| `JsonSelect` death on oversized all-digit index | unfixed `json.c` `StringToLongExitOnError(index)` | unfixed probe: select of `9223372036854775808` exits |

### Verified — introduced by B-10 if B-4 is omitted

| what | where | how I reproduced |
|---|---|---|
| `1e400` / `-1e400` render as `inf` / `-inf` | `JsonPrimitiveToString` / mustache still go through `StringFromDouble` | probe against `811d159`; `write` stays `1e400` (serializer already used the lexeme) |
| `1e-8` renders as `0.00` | same | same probe |
| B-10’s first commit without the copy commit zeros `1e400` on copy | `JsonRealCreate` maps `!isfinite` to `0.0` | probe against `f92cd1c`: `1e400` copy=`0.0000` |

### Verified — in the stacked patch (fix these before sending)

| what | file:line | what breaks | how I reproduced |
|---|---|---|---|
| Stale comment: rendered reals still “belong to `StringFromDouble()`” | `tests/unit/json_test.c:1278–1281` | next reader, and the very next test in the file, are told the opposite of what the stack does | read; `CheckRealRendersAsParsed("1e-8")` in the following test asserts lexeme equality |
| New tests only parse text, never `JsonRealCreate` | `tests/unit/json_test.c` new cases | a regression that broke only the in-memory producer would stay green | probe: stacked `JsonRealCreate(0.5)` → to_string=`0.5000`; unfixed → `0.50`. No new test mentions `0.5000`. |

### Suspected — not blocking

- `JsonPrimitiveGetAsInteger()` is still `StringToLongExitOnError` (`json.c:860–866`). Any remaining or future caller on parsed data still kills the process. I found no remaining *production* caller on parsed user JSON in these two trees after core’s half (see Q7). Enterprise and out-of-tree are unchecked.
- `JsonRealCreate` is still `"%.4f"` (`json.c:1679–1689`). In-memory reals stay lossy at create time. The stack makes ToString/mustache/copy emit that stored text instead of going through `"%.2f"` again. Pre-existing constructor, newly user-visible on the render path.
- `unix_iface.c:1426` still has `lowest_metric = 0` and never assigns it (their B-12). Not this patch. I only note I saw it while reading the core twin.

I did not find a leak, double-free, or type-drop in `JsonPrimitiveCopy`. See Q5.

---

## 5. The eight questions

### 1. Is the load-time severity claim right?

**Yes.** Reproduced on stock 3.27.1. lldb stack matches. cf-agent failsafe confirmed in an isolated `--workdir` with `cf-promises` in `bin/` (a first attempt without that workdir went to failsafe because `~/.cfagent/bin` had no `cf-promises` — that is not the defect). CMDB and `def.json` are sufficient triggers.

`security@` is the correct channel. The threat wording is honest. See §2.

### 2. Is stacking B-4 under B-10 the right call?

**Yes, versus B-10 alone.** B-10 alone is a defect introduction on the real axis (`inf`, `0.00`). I measured it.

**Versus one combined commit:** also fine, and closer to CONTRIBUTING (“usually a PR will have only one commit”) and to core `6a4216dad`. I would not block a six-commit stack that lands as one PR. I would block two PRs or “merge B-10 now, B-4 later.”

### 3. Is B-4 correct at all?

**Yes, with a visible behaviour change that is the point of the change.**

Returning the parsed lexeme makes `JsonPrimitiveToString`, mustache, and `JsonWriteCompact` agree. That is the right invariant. Measured on the stacked library: `0.00049`, `1e-8`, `1.5e3`, `1e400` all render as written.

The change a mustache user will see:

- `0.5` → `0.5` (was `0.50`)
- `1.5e3` → `1.5e3` (was `1500.00`)
- `JsonRealCreate(0.5)` → `0.5000` (was `0.50`)

The third is the one the commit message under-sells. Production `JsonObjectAppendReal` in core is `cf-check/dump.c` diagnostics, not config templating, so the product risk is low. Still pin it (verdict item 3).

I would not keep `"%.2f"` for mustache and lexeme for ToString. That recreates the serializer/renderer split this work is removing.

### 4. Is returning the raw lexeme safe for every producer of a primitive?

**For numbers, yes, with the `JsonRealCreate` caveat above.**

Census of `JsonElementCreatePrimitive` callers in `json.c`:

| producer | what is stored | emitting it verbatim |
|---|---|---|
| `JsonParseAsNumber` | the input lexeme (`StringWriterClose`) | what you want |
| YAML scalars (`json-yaml.c:115`) | same, via `JsonParseAsNumber` | same |
| `JsonIntegerCreate` | `xasprintf("%d")` | exact for an `int` |
| `JsonIntegerCreate64` | `PRIi64` | exact for an `int64_t` |
| `JsonRealCreate` | `snprintf("%.4f")`, non-finite forced to `0.0` | `"0.5000"`, `"0.0005"`; this is the stored value, already what `JsonWrite` emitted |
| `JsonStringCreate` / parser string paths | heap string / `JsonDecodeString` | unchanged by this patch |
| `JsonBoolCreate` / `JsonNullCreate` | static `JSON_TRUE` / `JSON_FALSE` / `JSON_NULL` | not on the new path; `JsonDestroy` still skips `free` for those types |

`JsonPrimitiveCopy` of INTEGER/REAL now `xstrdup`s that stored pointer and keeps `type`. It cannot emit a string the constructor did not already own. I do not see a path that puts a secret, a path, or an internal sentinel in an INTEGER/REAL `primitive.value`.

### 5. Is the `JsonPrimitiveCopy()` change complete and correct?

**Yes, for ownership, lifetime, and type.**

```c
return JsonElementCreatePrimitive(
    type, xstrdup(primitive->primitive.value));
```

- Type is the original `primitive->primitive.type` (INTEGER stays INTEGER, REAL stays REAL).
- New heap string; `JsonDestroy` frees INTEGER/REAL/STRING and not BOOL/NULL (`json.c:448–452`). Matches every other number constructor.
- Callers of `JsonCopy` take ownership of the new tree and already destroy it. I walked `JsonArrayCopy` / `JsonObjectCopy` / `JsonMerge*` / core `RvalNewRewriter` / `EvalContextVariablePut*` — they copy, then the original is destroyed by its owner.
- No aliasing of the source pointer, so no double-free when both trees die.
- BOOL still goes through `JsonBoolCreate` (static). STRING still through `JsonStringCreate` (`xstrdup` of the accessor). Unchanged.

I did not run a leak sanitizer (see §6).

### 6. Is classifying exponent numbers as REAL a compatibility break?

**A real type change, smaller than the crash it replaces, and mostly hidden on 3.27.1.**

Stock 3.27.1 does not expose `datatype()` (`cf-promises --syntax-description json` has no such function). Current core’s `FnCallDatatype` (`evalfunction.c:5963–5968`) will report `"data real"` for `2e0` once this lands and core is new enough to have the function. I did not product-measure that function (see §6).

Consumers of `JsonGetPrimitiveType()` INTEGER vs REAL in these trees, after core’s half:

- `evalfunction.c` `datatype()` — the user-visible one.
- `unix_iface.c:1438` — metric must be INTEGER. A metric written `1e2` would now be REAL and lose the comparison. Route metrics come from parsed `netstat`/`/proc`, not user JSON; if they ever were exponent form, skipping them is safer than dying.
- `rlist.c` / `iteration.c` / mustache / `JsonPrimitiveToString` — INTEGER and REAL now take the same lexeme path.
- `JsonCompare` compares primitive **strings only**, not the INTEGER/REAL tag (`json.c:416–423`). `2e0` compared to `2e0` is unchanged.

Worse than the crash? No. The crash is a process death on valid JSON. The type change is “this is a real,” which is what `1e-8` is.

### 7. What did the fix miss? Census of remaining `JsonPrimitiveGetAsInteger` on parsed data.

**Their “rlist + iteration are the only twins” is incomplete but the extras are already fixed in `core-json`.** After both halves I do not have another production caller on *user* JSON in these two repositories.

`JsonPrimitiveGetAsInteger` is still fatal by construction (`json.c:866`). Remaining references:

**libntech (`libntech-fixes`):**

- `json.c:860` — the function itself.
- `json_test.c:535`, `:803` — tests, small integers the test just built.

**core (`core-json`), production:**

- `libpromises/rlist.c:1732` — comment only; the INTEGER/REAL arm now uses `JsonPrimitiveGetAsString`.
- `libpromises/iteration.c:699–704` — same, lexeme + `xstrdup`.
- `libpromises/generic_agent.c:2051–2060` — `ReadTimestampFromPolicyValidatedFile` now `StringToLong` + fail-to-0 (“not validated”).
- `libenv/unix_iface.c:1440–1448` — route metric now `StringToLong` + skip on error.

**core, tests only:**

- `tests/unit/policy_test.c:289–330` — line numbers from CFEngine-serialized policy JSON. Not user `readjson` input. A crafted huge `"line"` would still kill that test binary. Not an agent path.

**core, bundled unfixed libntech** (this tree’s submodule is still `5b5d04e`): old `json.c` / `mustache.c` still have the fatal copy and render. That is expected until core bumps the submodule. I did not treat those as remaining *core* callers.

**`StringToLongExitOnError` on other JSON data:** `JsonSelect` is converted. Remaining `StringToLongExitOnError` in core are CLI `optarg` parsers (`cf-key`, `cf-serverd`, `cf-runagent`) and tests.

**`JsonPrimitiveGetAsInt64ExitOnError`:** definition + `json_test.c` only.

**`JsonPrimitiveGetAsReal`:** definition + `json_test.c`. After this stack, ToString/mustache/copy do not call it. `1e400` through `GetAsReal` would still be `inf` if someone calls it.

I did not search CFEngine Enterprise / Mission Portal / other Northern.tech repos.

### 8. Are the regression tests any good?

**Yes, as death-or-fail tests against the unfixed library. Incomplete on the in-memory producer and on mustache.**

I relinked HEAD `json_test.o` against the unfixed archive (`lib-old.a` *before* `libtest.a` so the first `Json*` definition wins) and ran it from `tests/unit`:

- `test_parse_exponent_numbers` — **fails** on the type assertion (does not exit). As designed.
- `test_primitive_to_string_numbers` — process **exits 1** on `9223372036854775808`. `make check` would report that as a failed binary. Later cases in that function never run.
- `test_copy_preserves_numbers` / `test_select_oversized_array_index` / `test_real_renders_as_parsed` — not reached because the process died. Probe shows each would fail or exit if reached (`2000000000000` copies as `-1454759936`; select exits; `0.00049` ToString is `0.00`).

Against B-10-full (no B-4): `test_parse_exponent_numbers` passes; `test_copy_preserves_numbers` and `test_select_oversized_array_index` pass; `test_primitive_to_string_numbers` and `test_real_renders_as_parsed` fail on `"0.00049" != "0.00"`; exit 2.

libntech `tests/unit` has no `MustacheRender` reference. I grepped. core’s `tests/unit/mustache_test.c` is spec-driven over `tests/unit/data/mustache_*.json`, including `mustache_extra.json`. Adding number cases there is data-only. **That is the right offer**, as a follow-up on core after the libntech bump — not inside this libntech PR. Until the submodule moves, a `mustache_extra.json` case of `9223372036854775808` will kill core’s `mustache_test` the same way HEAD’s `json_test` dies against `0c0620d`.

`rlist_test` on macOS is XFAIL and dies at `test_rval_to_scalar2`. I did not add or run a test at the end of that file. Their note is consistent with the source; I did not re-verify the abort.

---

## 6. What you did not check

- I did not rebuild `cf-promises` / `cf-agent` against the patched libntech. Product-level **after** is library-level only (probe + `json_test`). Product-level **before** is stock 3.27.1.
- I did not use `/Users/djbclark/src/core-json/cf-promises/.libs/cf-promises`. `otool -L` shows it links `/Users/djbclark/opt/cfengine-dev/lib/libpromises.3.dylib` (trap 4). I left it alone.
- I did not product-measure `datatype()` (absent on 3.27.1) or core’s rlist/iteration path. On stock, load dies before those run. After a libntech-only fix, unfixed core would still die in `RlistAppendContainerPrimitive` / `SeqAppendContainerPrimitive` on iteration; that is from reading `17eb78e6d` vs `6a4216dad`, not from running it.
- I did not run each of the six commits’ full unit suite on its own. I compiled `json.c` from `0c0620d`, `f92cd1c`, `811d159`, and HEAD, and I ran the full `tests/unit` suite only at HEAD (`All 39 tests passed`; `json_test` 74/74 after top-level `make -j2` and a forced relink).
- No ASan/LSan, no 32-bit, no mingw, no Linux.
- No CFEngine Enterprise, Mission Portal, or other out-of-tree `JsonPrimitiveGetAsInteger` callers.
- I did not re-run core `rlist_test` to watch the sixth-test abort.
- I did not read other panel opinions.

---

## Trap controls (every before/after I asserted)

1. **`make check` inside `tests/unit` does not rebuild `../libutils`.** Top-level `make -j2` first. `json_test` was then `rm -f`’d and relinked. Suite result: 39/39.
2. **`make -C tests/unit <test>` does not relink on a changed archive.** Forced `rm -f tests/unit/json_test`.
3. **`git stash` of a committed file stashes nothing.** I never stashed and never checked out into the worktree. Unfixed / B-10-only / B-10-full sources were `git show <sha>:libutils/{json,mustache}.c` into `/tmp/b10b4-lib`.
4. **`.libs/` binaries vs installed dylib; `DYLD_*` stripped on `cf-agent` → `cf-promises`.** `otool -L` on every binary I measured:
   - stock `/opt/homebrew/bin/cf-promises` → Cellar `libpromises.3.dylib` (stock).
   - `tests/unit/json_test` → static libutils (only pcre2, openssl, libyaml, libSystem).
   - probes → the `/tmp` archives I built; `ar r` used member names `json.o` / `mustache.o`. A first attempt named `json-b10full.o` *added* a member and left HEAD’s `json.o` in place; I discarded those numbers and rebuilt.
   - cf-agent failsafe: `--workdir /tmp/b10b4-wd` with copies of the stock binaries in `bin/`. No `DYLD_LIBRARY_PATH`.

---

## Maintainer pushback I would expect (not defects)

- No `Changelog:` / `Ticket:`. Correct until an issue exists; add both after filing. Do not invent a CFE number.
- Six commits for one mistake. Fine for review; they may ask to squash to “fix + tests.”
- `Co-Authored-By: Claude Opus 5` — allowed under current core CONTRIBUTING AI rules if a human is the submitting author.
- Long block comments in `json.c` / `mustache.c`. They match the tone of this stack; they are not style-breaking.
- Process section of CONTRIBUTING (Jira first, one commit, changelog in the commit) is deliberately not followed. Say that in the PR, as the brief already plans to.
