# Adversarial second opinion — B-10, libntech JSON number handling

Reviewer: grok (Grok 4.6), 2026-08-16.
Subject: `/Users/djbclark/src/libntech-fixes`, branch `fix/json-number-fatal-exit`.
Base: `origin/master` = `0c0620d` (NorthernTechHQ/libntech).
Reviewed HEAD: `76856ee` (four commits; the brief froze the tree at three —
`811d159` was HEAD when this review started; `76856ee` landed during the
run and is included).

This is one gate on a patch that has not been sent. Nothing goes to
`security@northern.tech` or to an upstream issue/PR on the strength of
this file alone.

## 1. Verdict

**Ship with changes.**

The crash fixes are real, the copy rewrite is correct, and the new
classification of exponent-bearing numbers as REAL is the right type
decision. I could not make the patched library abort on the three
shapes the brief named. I could, however, make the primary
user-visible path — the one they measured on stock 3.27.1 — return
the wrong value instead of the parsed number, and I could make
`JsonPrimitiveToString()` / mustache emit `inf`, which is not JSON.

Do not ship the advisory or the first commit message in a form that
can be read as "1e-8 now renders as 1e-8". It does not, except via
`JsonWriteCompact()` and `JsonCopy()`.

Required before this is offered upstream:

1. **State the REAL-renderer consequence in the issue and in the
   first commit body, in numbers, not in "survive".** After this
   patch, `JsonPrimitiveToString()` and mustache turn `1e-8` into
   `0.00`, `2e0` into `2.00`, `-2e-3` into `-0.00`, and `1e400`
   into `inf`. Those are the CMDB / `def.json` / `string_mustache()`
   paths. `JsonWriteCompact()` still emits the lexeme. That split
   is the patch, not a footnote.
2. **Add a mustache test.** `libutils/mustache.c` is one of the two
   production files in the crash-fix commit. There is still no
   mustache test. The motivating repro was `string_mustache()`.
   Record the actual output (`1e-8` → `0.00`, huge integer →
   lexeme) so a later REAL-precision change cannot land unnoticed
   and so the advisory cannot drift from the binary.
3. **Name the remaining fatal converters in the advisory.**
   `JsonPrimitiveGetAsInteger()` is still `DoCleanupAndExit()`.
   On current `cfengine-core` (`tendcf-integration`) that is still
   reachable from parsed data through `libpromises/rlist.c` and
   `libpromises/iteration.c`. A CMDB / augments *array* of
   `9223372036854775808` still kills the agent after this
   libntech-only patch. The separate core branch
   `fix/json-number-rendering` (`6a4216dad`) is the right shape
   and its own commit says behavioural verification is still
   outstanding.

Recommended, not required for the mail:

4. Either fold the REAL-lexeme change
   (`fix/json-real-precision`, `fe1ace9`) into this patch, or
   sequence it immediately after and say so. Shipping B-10 alone
   turns the measured crash into a silent zero on every primitive
   CMDB / augments / mustache use of `1e-8`. That branch already
   describes `0.00049` → `0.00` as "a wrong value rather than a
   rounded one". `1e-8` joins that club the moment this lands.
5. `JsonSelect("")` on an array used to exit (`StringIsNumeric("")`
   is true; `StringToLong` returns "no digits"). It now returns
   NULL. Cheap extra case for `test_select_oversized_array_index`
   if you want the bonus fix locked in.

The code as written is not a reason to hold the crash fix. The
write-up, the missing mustache test, and the remaining core
callers are.

## 2. Severity verdict

**`security@`.** Availability, not memory unsafety. "When in doubt,
security@" is the right default here and I am not in doubt about
the availability claim.

What I actually ran on stock CFEngine 3.27.1
(`/opt/homebrew/bin/cf-promises`, isolated `-w` workdirs):

| Input | Path | Result |
|---|---|---|
| `parsejson` + `string_mustache` of `1e-8` | policy | exit 1, `Conversion error (-83 - Not terminated) on '1e-8'` |
| same, `2e0` | policy | exit 1, `-83` on `'2e0'` |
| same, `9223372036854775808` | policy | exit 1, `Conversion error (34 - Overflow)` |
| same, `0.00000001` / `2` / `1.5e3` / `42` / `9223372036854775807` | policy | exit 0 |
| `def.json` `{"vars":{"rate":1e-8}}` | augments, agent startup | exit 1, `-83` on `'1e-8'` |
| `def.json` `{"vars":{"n":9223372036854775808}}` | augments, agent startup | exit 1, overflow |
| `data/host_specific.json` `{"vars":{"n":1e-8}}` | CMDB, agent startup | exit 1, `-83` on `'1e-8'` |

`GenericAgentDiscoverContext()` loads CMDB and then augments
(`libpromises/generic_agent.c:1158`, `:1164`). That function is
called from `cf-promises`, `cf-agent`, `cf-execd`, `cf-serverd`,
`cf-monitord`, `cf-runagent`, and `cf-key`. A single primitive
number in `inputs/def.json` or `data/host_specific.json` is enough.
No `string_mustache()` in policy is required. I did not re-run the
cf-agent failsafe fallback; I did confirm `cf-promises` exits
non-zero, which is the documented reason the agent cannot validate
and falls back to failsafe.

Who can put that number there:

- **Site admin / policy author** writing `def.json` in masterfiles.
  Fleet-wide. A scientific-notation rate or a uint64 from an
  inventory feed is ordinary input, not an exploit payload.
- **Enterprise CMDB operator** writing `host_specific.json` (or
  whatever Mission Portal serialises into it). That person is not
  necessarily a policy author and cannot already run arbitrary
  promises.
- **Anyone the policy `readjson()`s / `readyaml()`s.** Third-party
  JSON. YAML numbers go through the same `JsonParseAsNumber()`
  (`libutils/json-yaml.c:115`).
- **A local user who can write those files.** On a default install
  that is already a privileged position.

"Attacker-controlled" is overstated if it is meant to sound like a
remote unauthenticated bug. It is honest if it means "the agent
aborts on valid JSON that a non-author of policy can introduce,
and also on JSON an author introduces by mistake." The second
clause is the one that will actually take hosts off policy. Valid
RFC 8259 input, parser accepts it, first render path calls
`DoCleanupAndExit()`. That is an availability defect in a
configuration-management agent and it belongs at `security@`.

It is not a memory-corruption report. Do not dress it up as one.

## 3. Defects found

### V1 — exponent-without-dot now renders as `%.2f`, not as parsed
**Verified.** Introduced by this patch.

`libutils/json.c:2397` classifies `seen_exponent` as REAL.
`JsonPrimitiveToString()` (`json.c:831`) and mustache
(`mustache.c:396-400`) still go through
`StringFromDouble(JsonPrimitiveGetAsReal())` → `"%.2f"`.

Measured against the freshly rebuilt library (see §Build control):

| Input | type | ToString / mustache | WriteCompact / copy |
|---|---|---|---|
| `1e-8` | REAL | `0.00` | `1e-8` |
| `2e0` | REAL | `2.00` | `2e0` |
| `-2e-3` | REAL | `-0.00` | `-2e-3` |
| `1E5` | REAL | `100000.00` | `1E5` |
| `1.0e-8` | REAL | `0.00` | `1.0e-8` (this one was already REAL) |
| `0.00049` | REAL | `0.00` | `0.00049` (pre-existing) |

`AddCMDBVariable` (`cfengine-core/libpromises/cmdb.c:133`) and
augments (`generic_agent.c:454`) both call `JsonPrimitiveToString`
for a primitive value. After this patch a CMDB / `def.json` var
of `1e-8` is installed as the string `0.00`. Before, the process
exited. The tests deliberately do not assert the rendered form
(`json_test.c`, `CheckNumberIsReal`: "The formatting of a rendered
real belongs to StringFromDouble() and is not asserted here").

This is better than failsafe. It is also a silent wrong value on
the exact repro that motivates the report. A rate, a threshold or
a scientific constant becomes zero in every rendered config that
goes through mustache, CMDB or augments.

### V2 — `1e400` now renders as `inf`
**Verified.** Introduced by this patch.

Same path. Measured: parse `1e400` → type REAL, lexeme `1e400`,
`JsonPrimitiveToString` = `inf`, mustache = `inf`,
`JsonWriteCompact` = `1e400`, copy preserves `1e400`.
`-1e400` → `-inf`. `1e309` → `inf`. `1e-400` → `0.00`.

`inf` is not valid JSON. `JsonRealCreate()` of an overflow double
already sanitises to `0.0000` (`json.c:1676-1682`; existing test
`test_show_array_infinity` expects `0.0000`). Parsed overflow
therefore disagrees with the library's own inf policy *and* with
serialisation of the same element.

Unfixed, `1e400` was INTEGER and `ToString`/mustache/copy exited
(`-83`). So this is a new residual, not a missed old crash.

`1e308` (still finite in IEEE 754) ToString-expands to a ~300
digit `%.2f` string. Pre-existing for `1.0e308`; new for the
no-dot form.

### V3 — `JsonPrimitiveGetAsInteger()` is still fatal, and still
reachable from parsed data in core
**Verified.**

`json.c:855-861` is unchanged: `StringToLongExitOnError()`.
Built with `-DNDEBUG`, so the `assert(type == INTEGER)` is gone.
A caller that does not check the type still dies on a REAL lexeme:

```
GETASINT 9223372036854775808  → exit 1, Overflow
GETASINT 1e-8                 → exit 1, Not terminated
GETASINT 2e0                  → exit 1, Not terminated
```

Product callers of `JsonPrimitiveGetAsInteger` in
`cfengine-core` excluding `libntech/` and tests:

| File | Parsed-data? | After this libntech patch |
|---|---|---|
| `libpromises/rlist.c:1729` | yes — CMDB/augments arrays, slist conversion | 1e-8 becomes REAL → `0.00`, no crash; oversized integer still exits |
| `libpromises/iteration.c:701` | yes — iteration over a data container | same |
| `libpromises/generic_agent.c:2051` | `cf_promises_validated` timestamp, CFEngine-written | still fatal if the field is oversized or (in NDEBUG) a REAL |
| `libenv/unix_iface.c:1440` | no — `/proc` via `JsonExtractParsedNumber` → `JsonObjectAppendInteger` | type-checked INTEGER; not user JSON |

`rlist.c` / `iteration.c` on `tendcf-integration` still convert
through `long` / `double`. The twin fix is
`cfengine-core` `fix/json-number-rendering` @ `6a4216dad`
("Render JSON numbers from their parsed text in list and iteration
contexts"). I read that commit. I did not build core (brief
forbids it). The commit itself says syntax-checked only,
"Behavioural verification against a full build is still
outstanding."

So the belief in the brief is right about the twins and right
that they live on a separate branch, and the "unverified" tag is
still accurate.

### V4 — copy of a number used to silently change the value
**Verified, fixed.** Not a remaining defect.

Unfixed `JsonCopy` of a parsed integer went through
`JsonIntegerCreate(int)`:

| Input | unfixed copy | patched copy |
|---|---|---|
| `2000000000000` | `-1454759936` | `2000000000000` |
| `9223372036854775807` | `-1` | `9223372036854775807` |
| `0.00049` | `0.0005` | `0.00049` |
| `0.5` | `0.5000` | `0.5` |
| `3.14159265` | `3.1416` | `3.14159265` |
| `9223372036854775808` | process exit | `9223372036854775808` |
| `1e-8` | process exit | `1e-8` (type REAL) |

Type is preserved (INTEGER stays INTEGER, REAL stays REAL).
Destroying the original and then serialising the copy still works
(measured). Ownership is `xstrdup` into
`JsonElementCreatePrimitive`; `JsonDestroy` frees non-bool/null
`primitive.value` (`json.c:448-451`). No aliasing with the
original, no double-free on destroy-of-copy.

### V5 — `JsonSelect` overflow used to exit
**Verified, fixed.** Covered by `test_select_oversized_array_index`
in `76856ee`.

Unfixed: index `9223372036854775808` → Overflow + exit 1.
Unfixed: index `""` → `-81 No digits` + exit 1
(`StringIsNumeric("")` is vacuously true).
Patched: both return NULL. In-range `0` still hits. `1e2` is not
all-digit so it never entered the conversion (NULL both sides).

`JsonSelect` is how `EvalContextVariableGet` indexes a data
container (`eval_context.c:2676`). The index comes from the
variable reference, i.e. policy, i.e. data.

### No leak / double-free found in the copy rewrite
**Verified by ownership audit + lifetime probe, not by ASan.**

Every INTEGER/REAL constructor either `xasprintf`s, `snprintf`s
into `xcalloc`, or takes `StringWriterClose()`. Copy now
`xstrdup`s. BOOL/NULL still use static `JSON_TRUE` / `JSON_FALSE`
/ `JSON_NULL` and are not freed. YAML numbers are parsed by
`JsonParseAsNumber` and then `JsonCopy`'d
(`json-yaml.c:357`); the holder is destroyed. That is the
correct pairing with the new copy.

I did not run ASan or valgrind. Mark that as unchecked, not as a
finding.

## 4. The seven questions

### 1. Is the severity right?

Yes. `security@`, on availability. See §2.

Reachable in practice without writing a `string_mustache()`
promise: `def.json` and `host_specific.json` both call
`JsonPrimitiveToString` on primitives while the agent is still in
`GenericAgentDiscoverContext`. I reproduced both on 3.27.1.

"Attacker-controlled" is the wrong headline. "Valid JSON in a
first-class, documented data file takes every binary that calls
`GenericAgentDiscoverContext` down, and takes `cf-agent` to
failsafe" is the right one. A CMDB operator or a `readjson()` of
vendor data is the least-privileged person who can trigger it on
purpose. An author who writes `1e-8` because that is the number
is the person who will trigger it by accident.

If the report is framed as a remote RCE-adjacent issue it will be
rightly downgraded. If it is framed as process abort + failsafe
on accepted input, it will stand.

### 2. Is classifying exponent numbers as REAL correct, or a
compatibility break?

Correct, and a small compatibility break that is better than the
crash.

Consumers of `JsonGetPrimitiveType()` / `JsonGetType()` that
branch INTEGER vs REAL, in both trees, excluding tests and the
patched files themselves:

- `libpromises/evalfunction.c:5963` — `type(..., "true")` (the
  function is `type`, not `datatype`). A top-level `2e0` becomes
  `"data real"` instead of `"data int"`. `is_type()` sits next to
  it. I did not run `type()` on stock (the 3.27.1 policy parser
  rejected my `datatype()` spelling; I did not want to invent a
  second attempt after that). The code change is mechanical.
- `libpromises/rlist.c` and `iteration.c` — INTEGER used
  `GetAsInteger` (fatal on `2e0` *before* this patch, so there is
  no working INTEGER consumer of `2e0` to break). After this
  patch they take the REAL arm and emit `2.00`.
- `libenv/unix_iface.c:1438` — INTEGER-only, `/proc` metrics
  created with `JsonObjectAppendInteger`. Unaffected.
- mustache INTEGER vs REAL — this is V1.
- `JsonPrimitiveTypeToString` treats both as `"number"`. No
  change.

Nothing else in either tree switches on the two types. I grepped
`JSON_PRIMITIVE_TYPE_INTEGER`, `JSON_PRIMITIVE_TYPE_REAL`,
`JSON_TYPE_INTEGER`, `JSON_TYPE_REAL`.

`2e0` as INTEGER was already unusable anywhere that converted it.
The only live behaviour change for a previously-working consumer
is `type()` reporting `"data real"`, plus V1 for anything that
renders via ToString/mustache. Neither is worse than
`DoCleanupAndExit`. The silent-zero half of V1 is the one that
can be *as* bad as the crash for a threshold.

### 3. Is returning the raw lexeme safe for every producer of a
primitive?

Yes, for the producers that this patch now emits verbatim
(INTEGER ToString, INTEGER mustache, INTEGER/REAL copy).

Census of `JsonElementCreatePrimitive` (static):

| Producer | What is stored | Emitted verbatim? |
|---|---|---|
| `JsonParseAsNumber` | writer buffer of the accepted lexeme | INTEGER: yes after this patch. REAL: WriteCompact/copy only |
| `JsonIntegerCreate` | `xasprintf("%d")` | yes |
| `JsonIntegerCreate64` | `xasprintf("%" PRIi64)` | yes |
| `JsonRealCreate` | `snprintf("%.4f")`, nan/inf forced to 0.0 | copy/WriteCompact only |
| `JsonStringCreate` | `xstrdup` of caller text | already was; not in this change |
| `JsonBoolCreate` / `JsonNullCreate` | static `"true"`/`"false"`/`"null"` | not this change |
| string-parse paths (`json.c:2426`, `:2500`, `:2688`) | `JsonDecodeString` | already was |
| YAML (`json-yaml.c:115`) | `JsonParseAsNumber` or `JsonStringCreate` | same as parse |
| `JsonPrimitiveCopy` | `xstrdup` of the above | the change |

The number parser is strict enough that a stored INTEGER/REAL
lexeme is a JSON number: leading `+` rejected except in an
exponent, leading zeros rejected, must end on a digit, only one
dot, only one exponent. I did not find a way to get a quote, a
space, HTML, or `inf` into a parsed number's lexeme.

So emitting the INTEGER lexeme into mustache or a string context
is not an injection. Emitting it back into JSON is what
`JsonWrite` already did. The unsafe emission I actually produced
is V2: `inf` from the *double* renderer, not from the lexeme.

There is no public constructor that lets a caller stuff an
arbitrary C string into an INTEGER/REAL primitive.

### 4. Is the `JsonPrimitiveCopy()` change complete and correct?

Yes.

It now calls `JsonElementCreatePrimitive(type, xstrdup(...))` for
INTEGER and REAL together (`json.c:250-260`). Type is the
original type. Lifetime is independent of the original (measured:
destroy original, `JsonWriteCompact` of copy still matches).
Destroy frees the strdup. Callers of `JsonCopy` /
`JsonMerge` / `JsonObjectMergeDeep` in core do not need to change.

BOOL/STRING/NULL still go through the typed constructors. That is
fine: BOOL/NULL are static, STRING already `xstrdup`s.

Copy now preserves type *and* text in every case I ran, including
YAML-parsed `1e-8` / `9223372036854775808` / `1e400`.

What it does not do: it does not make `JsonPrimitiveToString` of
the copy any better than ToString of the original. A copied
`1e400` still ToString-s as `inf`. That is V2, not a copy bug.

### 5. `1e400` now parses as REAL and renders as `inf`. Acceptable?

Acceptable as "the process no longer dies." Not acceptable as the
steady state, and not acceptable to leave out of the issue.

It is a new residual of V1's REAL renderer, not of the
classification itself. `JsonWriteCompact("1e400")` is already
correct. Using the lexeme in ToString/mustache (the same move
this patch already made for INTEGER, and that
`fix/json-real-precision` makes for REAL) removes `inf` without
inventing a new policy. Clamping to `0.0000` to match
`JsonRealCreate` would be the other consistent choice and would
be worse.

Do not let the advisory say overflow exponents "just work."

### 6. What did the fix miss?

`JsonPrimitiveGetAsInteger()` — still fatal, see V3.

Census, both repositories, reachable from parsed data:

**libntech (this tree), production:** no remaining caller except
the function itself. `JsonPrimitiveToString`, mustache INTEGER,
`JsonPrimitiveCopy`, and `JsonSelect` were the four, and they are
the patch. `JsonPrimitiveGetAsInt64ExitOnError` is tests only.

**cfengine-core product code** (excluding the vendored
`libntech/` and tests): the four rows in V3. The two that matter
for the same bug are `rlist.c` and `iteration.c`. Those are
twins, they are still present on `tendcf-integration`, and they
are patched (unverified) on `fix/json-number-rendering`.

Also still converting reals through `StringFromDouble`:
mustache REAL, `JsonPrimitiveToString` REAL, and the same two
core twins. That is how V1 happens.

`generic_agent.c:2051` will still abort the agent if
`cf_promises_validated`'s `timestamp` is not a `long`. That file
is written by CFEngine as an integer. Low reachability; mention
it, do not lead with it.

I did not find a fifth production `GetAsInteger` on parsed JSON.

### 7. Are the regression tests any good?

Mostly. They test what they claim. They do not test the path that
motivated the report.

Would each new test fail against the unfixed library? I relinked
`json_test.o` (from HEAD) against `origin/master`'s `json.o` +
`mustache.o` placed *before* `libutils.a`, and I also ran
per-case binaries.

| Test | Against unfixed | Notes |
|---|---|---|
| `test_parse_exponent_numbers` | **Fails** on the type assert (`1e-8` is INTEGER). Does not reach a process exit. | As designed. Measured: `Test failed.` |
| `test_primitive_to_string_numbers` | **Kills the binary** on `9223372036854775808` (`Overflow`). | Measured. The harness stops; later tests in the same file never run. |
| `test_copy_preserves_numbers` | **Would fail.** `2000000000000` copies as `-1454759936`; huge ints exit. | Never reached in a full `json_test` run against unfixed, because the previous test already exited. Measured independently via `JsonCopy`. |
| `test_select_oversized_array_index` | **Would kill the binary.** | Same: not reached in a full unfixed `json_test` run. Measured independently: `select 9223372036854775808` → Overflow + exit 1. |

So the commit messages are right that each test fails against the
old code, and slightly optimistic that a single `./json_test` run
against the old library exercises all four — the first fatal
conversion ends the process. That is still a red result. It is
not four independent red results unless you run them in
isolation.

Gaps that are actually missing:

- **No mustache test at all**, despite `mustache.c` being half of
  the crash-fix commit and the whole of the 3.27.1 repro.
- **No assertion of ToString for an exponent.** Deliberate, and
  the reason V1 can land without a red test.
- **No `1e400` / `inf` case.**
- **No `1e+8`**, no empty-string `JsonSelect`, no YAML number.
- Copy test checks `JsonWriteCompact` of the copy, not
  `JsonGetPrimitiveType`. That would have been enough to miss a
  type flip if WriteCompact did not already emit the lexeme for
  both types. It does, so this is minor.

`76856ee` closing the JsonSelect hole is the right addition. Do
the same for mustache.

## 5. What you did not check

- Address sanitizer, valgrind, or any leak detector. Ownership
  was audited and a destroy-original-keep-copy probe was run;
  that is not ASan.
- 32-bit `long`, Windows, or big-endian. This machine is
  arm64 macOS, `long` is 64-bit, build uses `-DNDEBUG`.
- Building or running `cfengine-core`. Brief forbids it. The
  `fix/json-number-rendering` twin was read, not executed.
- cf-agent failsafe fallback. I confirmed `cf-promises` exits
  1 on stock 3.27.1; I did not invoke `cf-agent`.
- Enterprise Mission Portal / hub serialisation of CMDB. I
  traced `host_specific.json` on the agent side only.
- `JsonExpandElement`, `mapdata`/`maparray` beyond noting they
  use `JsonPrimitiveGetAsString` (lexeme, safe) rather than
  `JsonPrimitiveToString`.
- Full `make check` of every unit test binary. I ran `json_test`
  (73/73 after the fourth commit) with a forced relink.
- The contents of any other `upstream-opinion-*.md` or anything
  under `docs/handoffs/`.
- Whether `type("x", "true")` on stock 3.27.1 currently prints
  `"data int"` for `2e0`. The code says it would; I did not get a
  clean stock run of that function.

## Build control (the trap)

`make check` inside `tests/unit` does not rebuild `../libutils`.
I treated that as load-bearing.

1. Deleted `libutils/json.lo`, `libutils/mustache.lo`,
   `libutils/.libs/{json.o,mustache.o,libutils.a}`.
2. Top-level `make -j2` — rebuilt `json.lo` / `mustache.lo` /
   `libutils.la` at 22:21, then again after `76856ee`.
3. Deleted `tests/unit/json_test` and `json_test.o`.
4. `make -C tests/unit json_test` — relinked against the new
   archive.
5. `./json_test` → 72/72 at `811d159`, 73/73 at `76856ee`.

Unfixed comparisons did **not** use that test binary. I extracted
`origin/master:libutils/json.c` and `mustache.c` into `/tmp`,
compiled them to `.o`, and linked probes with those objects
*ahead of* `libutils.a` so the old definitions won. Stock 3.27.1
was a separate binary under isolated `-w` workdirs.

If a later reviewer only runs `make check` in `tests/unit` after
toggling the patch, they will measure whichever `libutils.a` was
last built. That is the trap that already caught this item once.

## Maintainer pushback I would expect (and agree with)

- "Show me `string_mustache('{{n}}', parsejson('{n:1e-8}'))` after
  this patch." It is `0.00`. If the issue says the inputs
  "render", a reviewer who measures that will bounce the PR.
- "Why is mustache untested?" No good answer.
- "Changelog: / Ticket:" — absent on purpose; do not invent a
  CFE number. Once the upstream issue exists, add the trailers
  in a follow-up commit, not by rewriting history of a sent
  patch.
- `Co-Authored-By: Claude Opus 5` is honest under core
  `CONTRIBUTING.md` §Use of AI. Leave it.
- Three (now four) commits vs "usually one commit per PR" —
  each commit is a valid change. Keep the split.
- Folding REAL lexeme rendering into *this* security patch vs
  landing `fix/json-real-precision` right after. I would rather
  they sequence than silently ship `1e-8` → `0.00` as the
  security fix. If they refuse to fold, the advisory has to say
  the zero out loud.

Style: Allman-4, comments wrapped, no new log calls, no invented
`Ticket:`. The process section of `CONTRIBUTING.md` is
deliberately not followed, as the brief said.

I found nothing that makes the crash fix itself wrong. I found
enough about what the fix *turns the crash into* that shipping
the current write-up unchanged would be the mistake.
