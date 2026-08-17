# B-10 second opinion — cursor — 2026-08-16

Reviewer: cursor (this panel seat).
Subject: `libntech` branch `fix/json-number-fatal-exit` at `811d159`
(`origin/master` = NorthernTechHQ/libntech `0c0620d`).
Tree: `/Users/djbclark/src/libntech-fixes`. Consumer read-only:
`/Users/djbclark/src/cfengine-core` (checkout `tendcf-integration`;
`libntech` submodule left untouched).

## 1. Verdict

**Ship with changes.**

The three claimed defects are real, the INTEGER-rendering and copy fixes
are correct, and I could not make the patched library exit on the
mustache / `JsonPrimitiveToString` / `JsonCopy` / `JsonSelect` paths that
used to. Do not send it as if REAL rendering were now exact, and do not
send it without the companion core change for list/iteration conversion.

Changes before `security@` / the upstream PR:

1. **Add a regression test for `JsonSelect()`.** The all-digit overflow
   path is a real process-exit on unfixed code and a silent NULL after
   the patch. Nothing in `tests/unit/json_test.c` covers it. Empty-string
   index (`""`) is the same class of bug and is also untested.
2. **Pin `1e400` (and `1.0e400`) in a test**, whichever behaviour you
   intend. Today `JsonPrimitiveToString` / mustache emit `inf`;
   `JsonWriteCompact` emits the lexeme. That split is currently
   untested. A one-line assertion stops it drifting.
3. **State in the writeup, not just the commit body, that exponent
   reals still render through `StringFromDouble()` (`%.2f`).** After this
   patch, mustache of `1e-8` is `0.00`, not `1e-8`. That is better than
   failsafe, and it is also a silent zero. The commit's "the same inputs
   render" is true only in the "does not exit" sense.
4. **Ship `cfengine/core` `fix/json-number-rendering` with this, or
   say plainly that it is not closed in CFEngine yet.** On the core
   checkout I was given, `libpromises/rlist.c` and
   `libpromises/iteration.c` still call `JsonPrimitiveGetAsInteger()`
   for INTEGER primitives. Huge integers in a data list / `foreach` /
   CMDB slist still terminate the process. The companion branch already
   exists and is the right fix; this libntech patch does not replace it.

I would not block on rewriting REAL `ToString` to the lexeme. That would
change `0.5` from `"0.50"` to `"0.5"`, and
`test_primitive_to_string_numbers` currently asserts the `0.50` form on
purpose. Treat that as a follow-up, not a gate.

## 2. Severity verdict

**`security@northern.tech`**, on availability, with the "attacker
controlled" claim narrowed.

What I measured on stock CFEngine 3.27.1
(`/opt/homebrew/bin/cf-promises`): a standalone policy that
`readjson()`s `{"n": 1e-8}` and `string_mustache("{{n}}", d)` exits:

```
error: Conversion error (-83 - Not terminated) on '1e-8' (StringToLongExitOnError)
```

Same for `9223372036854775808` (overflow) and `1e400` (not terminated).
`{"n": 42}`, `{"n": 0.00000001}`, and `{"n": 1.5e3}` validate. That
matches the brief. `cf-promises` dying during validation is the
documented path to failsafe, which is a host walking off its policy.

Reachability, honestly:

- `readjson()` of a file the policy names: whoever can write that file.
  Sometimes that is the policy author. Sometimes it is an inventory /
  API dump the policy consumes. Calling every such file
  "attacker-controlled" overstates a typical community deploy and
  understates a deploy that slurps JSON from a less-trusted source.
- `$(sys.workdir)/data/host_specific.json` (CMDB): loaded at agent
  start, before augments (`libpromises/generic_agent.c` /
  `libpromises/cmdb.c`). Primitive values go through
  `JsonPrimitiveToString()`. An exponent primitive in that file crashes
  stock 3.27.1 at load, not merely during some later render. In
  Enterprise this file is fed by Mission Portal; in community it is an
  admin-placed file. A CMDB operator is not a remote unauthenticated
  attacker. They are also not "only root on that host."
- Inline JSON in policy: the policy author.
- libntech itself does not authenticate callers. The library will
  happily parse RFC-valid numbers and then exit.

This is not RCE and not memory corruption. It is "valid JSON takes the
agent to failsafe." Failsafe is a security-relevant state, the standing
rule is "when in doubt, security@," and I would send it there with that
framing rather than as a remote exploit.

## 3. Defects found

### Verified (I ran it)

**V1. REAL rendering is still `%.2f`, so the exponent crash is replaced
by a silent zero or by `inf`.**
`libutils/json.c:831-832` (`JsonPrimitiveToString`),
`libutils/mustache.c:396-401` (`RenderVariablePrimitive`).

Patched library, throwaway probe linked against
`libutils/.libs/libutils.a` after a top-level `make -j2`:

| input     | type after patch | `ToString` / mustache | `JsonWriteCompact` |
|-----------|------------------|-----------------------|--------------------|
| `1e-8`    | REAL             | `0.00`                | `1e-8`             |
| `-2e-3`   | REAL             | `-0.00`               | `-2e-3`            |
| `1E5`     | REAL             | `100000.00`           | `1E5`              |
| `2e0`     | REAL             | `2.00`                | `2e0`              |
| `1e400`   | REAL             | `inf`                 | `1e400`            |
| `-1e400`  | REAL             | `-inf`                | `-1e400`           |
| `1e-400`  | REAL             | `0.00`                | `1e-400`           |
| `0.00049` | REAL             | `0.00`                | `0.00049`          |

`0.00049` → `0.00` via `ToString` is pre-existing (already REAL). `1e-8`
joining that path is new: stock 3.27.1 exits instead. `1.0e400` was
already REAL on unfixed code and already `ToString`'d as `inf`; `1e400`
(no dot) is newly on that path.

This is not a residual process exit on the render path. It is a residual
correctness hole the tests deliberately do not look at (`CheckNumberIsReal`
says so). Repro: parse `1e-8`, call `JsonPrimitiveToString` or
`MustacheRender(out, "{{n}}", obj)`.

**V2. `JsonPrimitiveGetAsInteger()` is still fatal, including on a REAL,
because this build is `NDEBUG`.**
`libutils/json.c:855-861`.

```
/tmp/b10-probe-new getasint 1e-8
# type=REAL lexeme='1e-8'
# error: Conversion error (-83 - Not terminated) on '1e-8' (StringToLongExitOnError)
# exit 1

/tmp/b10-probe-new getasint 9223372036854775808
# type=INTEGER
# error: Conversion error (34 - Overflow) on '9223372036854775808'
# exit 1
```

The `assert(type == INTEGER)` is compiled out (`CORE_CFLAGS` contains
`-DNDEBUG`). Classification as REAL does not make `GetAsInteger` safe;
it only helps callers that switch on type first. Repro: call
`JsonPrimitiveGetAsInteger` on a parsed `1e-8` or on an integer that
does not fit in `long`.

**V3. Twin remaining crashes in `cfengine/core`, unfixed on the checkout
I was told to read.**
`libpromises/rlist.c:1727-1732` (`RlistAppendContainerPrimitive`),
`libpromises/iteration.c:699-703` (`SeqAppendContainerPrimitive`).

Both still do `StringFromLong(JsonPrimitiveGetAsInteger(...))` for
INTEGER. After this libntech patch, exponent numbers take the REAL
branch (lossy `%.2f`, no exit). Integers larger than `long` still take
the INTEGER branch and still `DoCleanupAndExit`. Reachable from parsed
data: `RlistFromContainer` (CMDB slist of primitives, any slist-from-
container conversion) and `foreach` over a data container.

The belief in the brief is right: branch `fix/json-number-rendering`
(`6a4216dad` on this fork) switches both sites to
`JsonPrimitiveGetAsString()`. I diffed it against `origin/master`. I did
not build that branch. Current `tendcf-integration` does not contain it.

**V4. `JsonSelect` overflow / empty index: fix is real, test is missing.**
`libutils/json.c:957-976`.

Unfixed `json.o`: `JsonSelect([10,20,30], "9223372036854775808")` and
`JsonSelect(..., "")` both hit `StringToLongExitOnError` and exit
(overflow / no digits). Patched: both return NULL. Existing
`test_select` only uses `"0"`, `"1"`, `"2"`, `"x"`. The empty-string
case is a side effect of `StringIsNumeric("")` returning true.

**V5. The new tests do fail against unfixed `json.c`.** Linked
`json_test.o` (new tests) with `origin/master`'s `json.c` /
`mustache.c` and ran from `tests/unit`:

- `test_parse_exponent_numbers` failed at `json_test.c:1253`
  (`7 != 6`, REAL vs INTEGER) without exiting the binary.
- `test_primitive_to_string_numbers` then exited on
  `'9223372036854775808'` (`Conversion error (34 - Overflow)`).
- `test_copy_preserves_numbers` never ran in that process because the
  previous test aborted it. Separately, unfixed `JsonCopy("2000000000000")`
  produced `'-1454759936'` and `JsonCopy("9223372036854775807")`
  produced `'-1'`, so the copy test's non-fatal cases would fail if
  they were reached.

**V6. Unfixed copy of overflow REAL silently becomes zero.** Not
introduced by this patch; the patch *fixes* it. Recording it because
the brief asked about `1e400`. Unfixed: `1.0e400` is already REAL,
`JsonCopy` goes through `JsonRealCreate(inf)` which clamps to `0.0`,
compact form `'0.0000'`. Patched copy keeps `'1.0e400'`. `ToString`
is `inf` on both, for the dotted form.

### Suspected (read, not run in a CFEngine binary)

**S1. `generic_agent.c:2051` (`ReadTimestampFromPolicyValidatedFile`)**
calls `JsonPrimitiveGetAsInteger(timestamp)` with no type check. The
writer of that file uses `JsonObjectAppendInteger(..., time())`, so
normal values fit. A hand-edited `policy_validated.json` with `1e9` or a
20-digit timestamp still exits after this patch (V2). Whoever can write
that file already owns the workdir.

**S2. `unix_iface.c:1435-1440`** calls `GetAsInteger` on `metric` after
checking `JSON_PRIMITIVE_TYPE_INTEGER`. The integer was built with
`JsonObjectAppendInteger` from `sscanf %ld` truncated to `int`, from
`/proc`, not from a JSON document. Not a parsed-JSON crash path.

**S3. `cmdb.c:131-138`.** Primitive CMDB vars use `JsonPrimitiveToString`.
After this patch an exponent primitive installs as `"0.00"` rather than
crashing. An oversized integer primitive installs as the lexeme (good).
An array of oversized integers still goes through `RlistFromContainer`
(V3).

I did not rebuild `cf-agent` / `cf-promises` against the patched
libntech (brief: do not build that checkout). End-to-end "failsafe
gone" is inferred from `MustacheRender` + `JsonPrimitiveToString` on
the patched `libutils.a`, plus stock 3.27.1 as the before.

## 4. The seven questions

### 1. Is the severity right?

Yes, send to `security@`, as availability. See §2. "Attacker-controlled
CMDB" is a stretch for a single-admin community host and a fair
description of a multi-user Enterprise CMDB or any `readjson()` of a
file the host does not solely write. The honest sentence is: *a valid
JSON number, from any input `JsonParse` accepts, can take cf-promises
off the air and the agent into failsafe.* That is enough.

### 2. Is classifying exponent numbers as REAL correct, or a compatibility break?

Correct, and it does change `type(..., "true")` / `is_type(..., "data int")`.

`DataTypeStringFromVarName` (`libpromises/evalfunction.c:5947-5979`)
maps `JSON_PRIMITIVE_TYPE_INTEGER` → `"data int"` and
`JSON_PRIMITIVE_TYPE_REAL` → `"data real"`. `2e0` will report `"data
real"`. Other type-switchers in core: `rlist.c`, `iteration.c`,
mustache, `eval_context.c` (strings only), `unix_iface.c` (integers it
created itself).

JSON has one number type. `2e0` is not a `strtol` integer. Keeping it
as INTEGER would leave `GetAsInteger` fatal for any caller that does
not use the lexeme. Classification as REAL is the change that makes
the still-unfixed rlist/iteration INTEGER branch stop applying to
`1e-8`.

What gets worse than the crash: `is_type(x, "data int")` on a data
cell that used to be an exponent-without-dot integer. Those cells
previously did not crash on `type()` itself (it does not convert), so
this is a real compatibility change for inspection, replacing a crash
on render. I have not found a caller for which that is worse than
failsafe. Policy that string-compares a mustache'd `1e-8` against
`"1e-8"` will now see `"0.00"` (V1).

### 3. Is returning the raw lexeme safe for every producer of a primitive?

For INTEGER, yes. I walked every constructor:

| producer | stored string | owned? | emitted by INTEGER lexeme path |
|---|---|---|---|
| `JsonParseAsNumber` | parser-validated `[0-9eE+.-]` lexeme | `StringWriterClose` | only if no dot and no exponent, after this patch |
| YAML scalar (`json-yaml.c:107-118`) | same, via `JsonParseAsNumber` | same | same |
| `JsonIntegerCreate` | `"%d"` | `xasprintf` | yes, always a JSON integer |
| `JsonIntegerCreate64` | `PRIi64` | `xasprintf` | yes |
| `JsonRealCreate` | `"%.4f"`, inf/nan clamped to `0.0` | heap | not INTEGER |
| `JsonStringCreate` / parse-as-string | decoded text | heap | not INTEGER; `JsonWrite` JSON-encodes |
| `JsonBoolCreate` / `JsonNullCreate` | static `"true"`/`"false"`/`"null"` | not freed | not INTEGER |
| `JsonPrimitiveCopy` after this patch | `xstrdup` of the above | new heap | type preserved |

`JsonElementCreatePrimitive` is static. Nothing outside `json.c` can
stuff an arbitrary C string into an INTEGER. Mustache does not
HTML-escape numbers; the INTEGER charset cannot carry `<>&"`.
`JsonWrite` / `JsonWriteCompact` already emitted the lexeme for
non-strings (`JsonPrimitiveWrite`, `json.c:1733-1756`).

The unsafe-looking leftover is REAL, which this patch does *not* take
as a lexeme (V1): `inf` is not valid JSON if a caller treats `ToString`
as a JSON fragment. That is pre-existing for `1.0e400` and newly
reachable for `1e400`.

### 4. Is the `JsonPrimitiveCopy()` change complete and correct?

Yes for INTEGER and REAL.

```c
return JsonElementCreatePrimitive(
    type, xstrdup(primitive->primitive.value));
```

`JsonDestroy` frees `primitive.value` for every type except BOOL and
NULL (`json.c:448-452`). Copy allocates a new string; original and copy
do not alias. BOOL/NULL still go through `JsonBoolCreate` /
`JsonNullCreate` (static storage, not freed). STRING still goes through
`JsonStringCreate` (`xstrdup` of the decoded value). I did not run
ASan/leaks; the ownership is the same pattern as `JsonStringCreate`.

Type is preserved (measured: copy of `1e-8` stays REAL, copy of
`2000000000000` stays INTEGER). `CheckNumberSurvivesCopy` only asserts
`JsonWriteCompact` of the copy, not `JsonGetPrimitiveType`. That is a
test gap, not a code gap.

Callers of `JsonCopy` (merge, expand, CMDB container install, etc.)
now get a number that still equals the original under `JsonCompare`,
which compares lexemes. Unfixed, `JsonCopy("0.5")` compared unequal
(`'0.5'` vs `'0.5000'`). Measured.

### 5. `1e400` now parses as REAL and renders as `inf`. Acceptable?

Acceptable as "does not exit," not acceptable as "renders the number."
It is also not a new class of bug: unfixed `1.0e400` already did this
(`ToString='inf'`, and copy became `0.0000`). The patch makes the
no-dot spelling join the dotted one, and makes *copy* of both keep the
lexeme (an improvement). `JsonWriteCompact("1e400")` stays valid JSON.

If the security mail says "rendering is exact," that sentence is false
for this input. If it says "the process no longer exits," that is true.
Pin it in a test (change 2).

`JsonRealCreate(inf)` still clamps to `0.0` (`json.c:1676-1679`);
`test_show_array_infinity` expects that. Parsed overflow and created
overflow remain inconsistent. Pre-existing for dotted overflow;
worth one sentence in the writeup.

### 6. What did the fix miss?

Census of `JsonPrimitiveGetAsInteger` in both trees, excluding the
libntech submodule copy inside core and excluding tests:

| site | type-checked? | parsed-JSON reachable? | after this patch |
|---|---|---|---|
| `json.c:855` definition | assert, compiled out in `NDEBUG` | n/a | still fatal |
| `mustache.c` INTEGER case | switch | yes | **fixed** (lexeme) |
| `json.c` `JsonPrimitiveToString` INTEGER | switch | yes | **fixed** (lexeme) |
| `json.c` `JsonPrimitiveCopy` INTEGER | switch | yes | **fixed** (lexeme) |
| `json.c` `JsonSelect` | `StringIsNumeric` then `StringToLong` | index from data | **fixed** (NULL) |
| `rlist.c:1729` | switch | yes (container → slist) | **still fatal** for huge INTEGER |
| `iteration.c:701` | switch | yes (`foreach`) | **still fatal** for huge INTEGER |
| `generic_agent.c:2051` | no | only if `policy_validated.json` is weird | still fatal (S1) |
| `unix_iface.c:1440` | yes | no (self-made int from `/proc`) | not a JSON-parse crash |

`JsonPrimitiveGetAsInt64ExitOnError` has no production callers in core;
tests only.

The rlist/iteration twins are real and already patched on
`fix/json-number-rendering`. Exponent numbers are mitigated there by
classification (REAL branch) even without that core patch. Huge
integers are not.

`FnCallFold` (`sum`/`mean`/…) uses `JsonPrimitiveToString` then
`sscanf %lf`. After this patch, `sum` of `[1e-8]` is a silent 0, and
`sum` of `[1e400]` is inf, with no exit. Same REAL `%.2f` hole.

### 7. Are the regression tests any good?

They test what they claim, and they fail against unfixed code (V5).
They do not test what the brief's "the same inputs render" can be
misread as.

- `test_parse_exponent_numbers`: good structure (type first, so a
  classification regression does not abort the process). Does not
  assert `ToString`. Would not catch V1.
- `test_primitive_to_string_numbers`: good for INTEGER lexeme,
  including magnitudes that cannot fail except by process exit. The
  REAL case only checks `0.5` → `"0.50"`, i.e. the old `%.2f` contract.
  No `1e-8`, no `1e400`, no `JsonSelect`.
- `test_copy_preserves_numbers`: good values, including the silent
  `int` narrowing. Does not assert copy type. Against fully unfixed
  code it is unreachable because the previous new test already exited
  (test order). Against a ToString-only partial fix it would fire.
  No `1e400` copy (which is the interesting REAL-overflow case).

Missing and worth adding: `JsonSelect` overflow and `""`; `1e400` /
`1.0e400` ToString vs compact; copy type; maybe mustache `1e-8` if you
want the `0.00` behaviour to be a decision rather than an accident.

## 5. What I did not check

- I did not build or modify `/Users/djbclark/src/cfengine-core`, and I
  did not run patched `cf-promises` / `cf-agent`. Stock 3.27.1 was the
  only full binary. Patched behaviour in CFEngine is inferred from
  `libutils.a`.
- I did not run the core branch `fix/json-number-rendering`; I only
  read its diff.
- No ASan, valgrind, or leak run. Ownership is by inspection.
- No YAML parse executed; YAML numbers call `JsonParseAsNumber` (read
  `json-yaml.c:107-118`).
- No 32-bit `long`, no Windows.
- No fuzz of the number parser (leading zeros, `+`, `0e0` are handled
  by existing parse tests; I did not add cases).
- No Enterprise Mission Portal / live CMDB.
- `make check` inside `tests/unit` after the forced relink: **39/39
  PASS**, including `json_test` 72/72. I did not run
  `tests/static-check`.
- Mustache has no dedicated unit binary in this tree; I called
  `MustacheRender` from a probe.

## Build-trap control

`CORE_CFLAGS` is `-DNDEBUG`. `make check` in `tests/unit` does not
rebuild `../libutils`.

I ran `make -j2` at the libntech top level first (already up to date:
`json.o` 22:13, `json.c` 22:02). Then `rm tests/unit/json_test` and
`make -C tests/unit json_test` to force a relink. Running that binary
from the **repo root** produced two false failures
(`test_copy_compare`, `test_json_walk`) because `TESTDATADIR` is
`./data`. Running it from `tests/unit`, as the brief says, was 72/72.
Full `make -j2 check` from `tests/unit` was 39/39.

Before/after numbers in this file were taken from two probes:
`/tmp/b10-probe-new` linked only against the rebuilt `libutils.a`, and
`/tmp/b10-probe-old` / `/tmp/b10-oldcases` with
`origin/master`'s `json.c` and `mustache.c` compiled to `.o` and listed
**before** `libutils.a` so they override the archive. I did not modify
any file in any repository to do that.

## Maintainer notes (unprompted)

- `CONTRIBUTING.md` in libntech points at core. Coding style of the
  patch is consistent with `json.c` (Allman braces, 4 spaces, `/* */`
  comments folded). I am not going to bikeshed 78-column comments.
- Commit titles and bodies wrap at 80. No `Ticket:` / `Changelog:`
  trailers — correct until an upstream issue exists; do not invent
  one. Add `Changelog: Title` and the ticket once Northern.tech
  assigns one, or the generated changelog will drop the user-facing
  fix.
- Three commits is a better split than one: classification+render,
  tests that fail on the previous commit, then copy+select. Core
  CONTRIBUTING prefers small PRs; I would not squash the tests into
  the first commit.
- `Co-Authored-By: Claude Opus 5` matches core's AI policy if a human
  is the submitter and has actually reviewed this.
- First commit claims `tests/unit: 39/39 pass`. That is the number of
  test *programs*, not `json_test` cases. It is accurate.
- `JsonIntegerCreate(int)` vs `JsonPrimitiveGetAsInteger() → long`
  remains a footgun for any future copy-like code. The copy path no
  longer trips it. Fixing the `int` argument is a separate API change
  and should not be mixed into this patch.
- Do not describe this as "rendering now always matches
  `JsonWriteCompact`." That is true for INTEGER and false for REAL.
