# B-10 / B-4 — what each branch actually renders, measured

**Date:** 2026-08-17
**Purpose:** close B-10's remaining items (a) `1e400` → `inf` and (b) the
residual `%.2f` lossiness, with measurement rather than reasoning, before
anything is offered upstream or sent to `security@`.

## Method

A probe (`numprobe.c`) parses `{"n": <lexeme>}` and reports, for one lexeme
per process:

| column | call |
|---|---|
| `type` | `JsonGetPrimitiveType()` |
| `compact` | `JsonWriteCompact()` — the lossless serialiser, the reference |
| `copy` | `JsonWriteCompact(JsonCopy(n))` — copy **fidelity**, deliberately measured through the lossless serialiser so copy fidelity and render fidelity stay separate axes |
| `toString` | `JsonPrimitiveToString()` |
| `mustache` | `MustacheRender()` of `{{n}}` |

One lexeme per process because on stock these paths call
`DoCleanupAndExit()`; the exit status *is* the measurement.

Three variants, all against the same configured tree so only the two source
files differ. Stock and combined were compiled to `.o` and linked **ahead of**
`libutils.a`, so the archive members are never pulled — no rebuild, no risk of
the stale-archive trap that produced three false verifications last session.

| variant | contents |
|---|---|
| `stock` | `0c0620d` — `libutils/{json,mustache}.c` as upstream has them |
| `b10` | branch `fix/json-number-fatal-exit` @ `76856ee` |
| `b10b4` | that branch **plus** `fix/json-real-precision`'s two REAL render sites |

## Result

Ordered so the two axes read separately. `EXIT` = process terminated.

| lexeme | stock type | stock copy | stock render | b10 render | b10+b4 render |
|---|---|---|---|---|---|
| `42` | INTEGER | `42` | `42` | `42` | `42` |
| `0.5` | REAL | **`0.5000`** | `0.50` | `0.50` | `0.5` |
| `0.00049` | REAL | **`0.0005`** | **`0.00`** | **`0.00`** | `0.00049` |
| `3.14159265` | REAL | **`3.1416`** | **`3.14`** | **`3.14`** | `3.14159265` |
| `1e-8` | **INTEGER** | — | **EXIT** | **`0.00`** | `1e-8` |
| `2e0` | **INTEGER** | — | **EXIT** | `2.00` | `2e0` |
| `1E5` | **INTEGER** | — | **EXIT** | `100000.00` | `1E5` |
| `1.5e3` | REAL | **`1500.0000`** | `1500.00` | `1500.00` | `1.5e3` |
| `9223372036854775807` | INTEGER | **`-1`** | `9223372036854775807` | exact | exact |
| `9223372036854775808` | INTEGER | — | **EXIT** | exact | exact |
| `2000000000000` | INTEGER | **`-1454759936`** | `2000000000000` | exact | exact |
| `1e400` | **INTEGER** | — | **EXIT** | **`inf`** | `1e400` |
| `-1e400` | **INTEGER** | — | **EXIT** | **`-inf`** | `-1e400` |

`toString` and `mustache` agreed on every row in every variant, so they are
collapsed into one `render` column. `compact` emitted the original lexeme
unchanged on every row of every variant — it is the path that was always right,
which is the whole argument for rendering from the lexeme.

## What this settles

### (a) `1e400` → `inf` — the register's framing was wrong, and so was mine

The register says earlier reviewers "waved `inf` through as *acceptable but
disclose*" and that grok was right to call it a defect. Both statements treat
`inf` as something stock already does. **It is not.**

On stock, `1e400` has no decimal point, so it is misclassified INTEGER and
**terminates the process** — it never reaches `strtod()` and never prints
`inf`. `inf` appears only once B-10's classification fix routes the value into
the REAL path, where `StringFromDouble()`'s `strtod("1e400")` returns
`HUGE_VAL`. So:

- `inf` is **introduced by B-10 applied alone**, not fixed by it;
- `fix/json-real-precision` (B-4) **removes it as a side effect** of not going
  through `double` at all — `1e400` renders as `1e400`;
- it is therefore **not a third patch to write**. It is a statement about
  which order these two land in.

Confirming the mechanism rather than assuming it: `JsonPrimitiveGetAsReal()`
is the only route to `strtod()` here, and it has exactly **two** in-tree
callers — `JsonPrimitiveToString()` and the mustache renderer — which are
precisely the two sites B-4 rewrites. It has **zero** callers in `cfengine/core`.
Once B-4 lands, nothing in either tree can produce `inf` from parsed JSON.

### (c) Mustache coverage — there is nothing to extend

Confirmed by search, not assumed: **no file under `tests/unit/` references
`MustacheRender` at all**, and `Makefile.am` has no `mustache_test` target. So
`libutils/mustache.c` has **zero** unit coverage in libntech today, and the
renderer half of both B-4 and B-10 is untestable in-tree.

The right move in the filing is therefore a *proposal* plus an offer, not an
invention inside this PR: our `json_test.c` additions cover
`JsonPrimitiveToString()`, which is the same defect on the same values reached
by the other site, and we can supply a `mustache_test` as a separate PR if
maintainers want one. Writing a new test binary into a defect-fix PR would
enlarge its review surface for no severity benefit.

### (b) The residual lossiness — real, but B-10 does not cause it

B-10 alone leaves every real rendering through `%.2f`, so `1e-8` mustaches to
`0.00`. The filing must say this plainly. But the fair framing is narrower
than "B-10 leaves a silent wrong value":

**`%.2f` truncation is a pre-existing stock defect** — `0.00049` → `0.00`
already, today, with no patch applied. B-10 does not introduce a bug class; it
moves exponent-form numbers out of a *fatal* path into an *already-broken*
lossy one. For those inputs that is a strict improvement (a wrong value is not
worse than a host dropping to failsafe) but it is **not a fix**, and a filing
that implies exponent numbers now render correctly would be false.

The one genuinely **new** output B-10 produces is `inf`/`-inf`, per (a).

### Recommended topology

B-10 and B-4 were recorded as "independently landable". On the evidence that
is true for the *integer* axis and false for the *real* axis: B-10 alone ships
a token that is not valid JSON. Landing B-4 first, or stacking B-10 on it,
makes every row of the table exact and removes `inf` without a third patch.

Note that `cfengine/core`'s half (`6a4216dad`) already does exactly this —
it fixes integers **and** reals together in the same commit, at
`RlistAppendJson()` and the iteration equivalent. The libntech half is the only
one split across two branches.

## The severity is higher than the register says, and the trigger is far more common

Verifying core's half against the **real product** produced the most important
result here. The register frames B-10 as a *rendering* defect: a value has to
reach `string_mustache()` or a list/iteration context before anything converts
it. That is wrong.

Built from `fix/json-number-rendering` (so **core's half is applied**) against
**stock** libntech, this policy is enough:

```cfengine
body common control { bundlesequence => { "test" }; }
bundle agent test
{
  vars:
      "d" data => readjson("$(sys.policy_entry_dirname)/numbers.json", 100000);
  reports:
      "loaded";
}
```

with `numbers.json` containing `9223372036854775808` anywhere inside it. There
is **no iteration, no mustache, and nothing that renders the value at all** —
the variable is merely declared. Result:

```
error: Conversion error (34 - Overflow) on '9223372036854775808' (StringToLongExitOnError)
error: Policy failed validation with command '".../cf-promises" -c ".../v1.cf"'
error: CFEngine was not able to get confirmation of promises from cf-promises, so going to failsafe
```

`cf-promises` dies at **policy-load time** and `cf-agent` drops to failsafe.
Stack, from `lldb` with a breakpoint conditioned on the value (not inferred):

```
StringToLongExitOnError(str="9223372036854775808")   string_lib.c:656
JsonCopy                                             <- JsonPrimitiveCopy, inlined
JsonCopy
JsonObjectCopy
RvalNewRewriter
VerifyVarPromise
ExpandPromise
BundleResolvePromiseType
PolicyResolve
LoadPolicy
cf-promises.c:156  main
```

**The fatal site is `JsonPrimitiveCopy()`, and it is reached because storing a
JSON container as a CFEngine variable deep-copies it.** A second trace, on the
`sys.*` containers, shows the same chain through
`EvalContextVariablePutSpecial` ← `DetectEnvironment` — i.e. it also runs
before any user policy is evaluated.

Three consequences:

1. **The register's "four call sites" table is incomplete.**
   `JsonPrimitiveCopy()` is a fifth, and it sits on the hottest path of the
   three: every variable store, not just rendering.
2. **Severity is understated.** The trigger is not "renders the value through
   mustache" but "loads the value at all". `readjson()` of a file with one
   large integer takes the host off its policy.
3. **This path is entirely inside libntech.** Core has no
   `JsonPrimitiveGetAsInteger()` call sites left on `fix/json-number-rendering`
   (only the comments that replaced them), and `JsonPrimitiveCopy()` is
   libntech's. So **`fix/json-number-fatal-exit` is the patch that matters**
   for the most common trigger.

### A FOURTH build trap — it invalidated two of my own results before I caught it

Binaries copied out of `.libs/` are **not** the build tree's binaries in the
sense that matters. `otool -L` on the copied `cf-promises` shows:

```
/Users/djbclark/opt/cfengine-dev/lib/libpromises.3.dylib
```

— the **installed** dylib at the `--prefix`, dated **Aug 15 17:01**, i.e. two
days old and predating every fix in this change set. Two measurements I had
already written down ("core's fix applied and it still dies", "both fixes
applied and it still dies") were made against that stale dylib and were
**wrong**; they tested nothing. Corrected results are below.

Worse, `cf-agent` spawns `cf-promises` as a **child process**, and macOS strips
`DYLD_*` across that exec — so setting `DYLD_LIBRARY_PATH` fixes a direct
`cf-promises` run but silently does **not** reach the child that `cf-agent`
actually validates with. The working recipe is `install_name_tool -change` on a
copy of each binary, rewriting every `opt/cfengine-dev/lib` dependency to the
build tree's `.libs`:

```bash
for b in cf-promises cf-agent; do
  cp $b/.libs/$b $WD/bin/$b
  for dep in $(otool -L $WD/bin/$b | awk '/opt\/cfengine-dev\/lib/ {print $1}'); do
    base=$(basename $dep)
    real=$(ls $PWD/lib*/.libs/$base $PWD/libntech/lib*/.libs/$base 2>/dev/null | head -1)
    [ -n "$real" ] && install_name_tool -change "$dep" "$real" $WD/bin/$b
  done
done
```

**Always `otool -L` the binary you are about to measure with.** The three traps
recorded last session were all about *stale objects*; this one is about a
*correctly built* binary loading someone else's library, and it looks identical
from the outside. Note also that the installed prefix is shared, so any
worktree's copied binaries resolve to it.

### Corrected product-level results

**The isolating measurement, re-run with correct linkage** (`otool -L` shows
zero references to the installed prefix). Policy `v1` is the one that only
declares `"d" data => readjson(...)`:

| build | `v1` (declare only) | `v3` (iterate) | `v5` (mustache) |
|---|---|---|---|
| stock libntech + **core fix** | **fatal → failsafe** | **fatal → failsafe** | **fatal → failsafe** |
| **libntech fix** + core fix | validates, rc=0 | validates, rc=0 | validates, rc=0 |

This restores — now honestly measured rather than measured against a stale
dylib — the claim that **core's half alone is not sufficient**. It also inverts
the emphasis the register carries from grok ("until core's branch lands, a CMDB
*array* still kills the agent even with the libntech patch"): the converse is
the stronger statement, because the libntech-side fatal fires on a policy that
does nothing but *declare* the variable, with no array indexing, no iteration
and no rendering at all.

### Full-fix product results

All rows run through `cf-agent` with `install_name_tool`-rewritten binaries, so
the linkage is the build tree's. `numbers.json` holds
`[42, 9223372036854775808, 10^30, 2000000000000, 0.00049, 3.14159265, 1e-8, 1.5e3, 1e400]`.

**Core's iteration path** (`reports: "ITER: $(d[vals])"`), with core's half and
libntech at `fix/json-number-fatal-exit` — every value exact:

```
42  9223372036854775808  1000000000000000000000000000000  2000000000000
0.00049  3.14159265  1e-8  1.5e3  1e400
```

Reals are exact here even without B-4, because core's `6a4216dad` fixes
integers **and** reals together in the same commit. The `%.2f` residue is
libntech's alone.

**libntech's mustache path** (`string_mustache()`), same build — this is where
items (a) and (b) actually show, and it is the honest picture for
`fix/json-number-fatal-exit` shipping by itself:

| value | B-10 only | B-10 + B-4 |
|---|---|---|
| `42` | `42` | `42` |
| `9223372036854775808` | `9223372036854775808` | same |
| `1000000000000000000000000000000` | exact | same |
| `2000000000000` | `2000000000000` | same |
| `0.00049` | **`0.00`** | `0.00049` |
| `3.14159265` | **`3.14`** | `3.14159265` |
| `1e-8` | **`0.00`** | `1e-8` |
| `1.5e3` | **`1500.00`** | `1.5e3` |
| `1e400` | **`inf`** | `1e400` |

So at product level: **B-10 alone removes every fatal and leaves every real
wrong on the mustache path, including a literal `inf` in rendered
configuration.** Adding B-4 makes all nine exact. This is the evidence for the
landing-order recommendation above, and it is what the filing must say rather
than implying exponent numbers now render correctly.

### Core's half, verified in both directions

Independent of the above, core's own two call sites are now behaviourally
verified rather than syntax-checked. A new `test_from_container_numbers` in
`tests/unit/rlist_test.c` builds an `Rlist` from a JSON array of ten numbers
via the public `RlistFromContainer()` and requires each to come back exactly as
written:

| | result |
|---|---|
| with `fix/json-number-rendering` | **passes** |
| with `libpromises/rlist.c` reverted to `17eb78e6d` | **process terminates** — `Conversion error (34 - Overflow) on '9223372036854775808' (StringToLongExitOnError)`, rc=1 |

**A trap worth recording:** `rlist_test` is `XFAIL` on this platform and
**aborts at its sixth test**, `test_rval_to_scalar2`, which is an
`expect_assert_failure(RvalScalarValue(rval))` death test that is not caught
here. Every test registered after it — about two thirds of the file — **never
runs**. A new test appended at the end of the list therefore passes vacuously.
`test_from_container_numbers` is deliberately registered immediately after
`test_copy`, ahead of the aborting test, and was confirmed to actually execute
before either direction was believed.

## Incidental finding — not B-10, recorded so it is not lost

`libenv/unix_iface.c` declares `long lowest_metric = 0;` at line 1425 and
**never assigns it**. The default-route comparison is therefore
`metric_value < 0`, which is false for every real metric, so the
`default_route == NULL` disjunct is what actually decides: CFEngine picks the
**first** active default gateway it sees, not the one with the lowest metric,
which is what the variable name and the comparison intend.

Pre-existing and untouched by our patch — `fix/json-number-rendering`
deliberately preserves the behaviour rather than smuggling a fix into an
unrelated change. Filed separately.

## Reproduction

```bash
SP=<scratchpad>
cd ~/src/libntech-fixes
INC="-DHAVE_CONFIG_H -I. -Ilibutils -Ilibcompat \
  -I/opt/homebrew/opt/pcre2/include -I/opt/homebrew/opt/openssl@3/include \
  -I/opt/homebrew/opt/libyaml/include"
LIB="-L/opt/homebrew/opt/pcre2/lib -L/opt/homebrew/opt/openssl@3/lib \
  -L/opt/homebrew/opt/libyaml/lib -lpcre2-8 -lssl -lcrypto -lyaml"

# stock: patched objects link AHEAD of the archive, so its members never load
git show 0c0620d:libutils/json.c > $SP/json_stock.c
git show 0c0620d:libutils/mustache.c > $SP/mustache_stock.c
cc $INC -c -o $SP/json_stock.o $SP/json_stock.c
cc $INC -c -o $SP/mustache_stock.o $SP/mustache_stock.c
cc $INC -o $SP/numprobe_stock $SP/numprobe.c $SP/json_stock.o $SP/mustache_stock.o \
   libutils/.libs/libutils.a libcompat/.libs/libcompat.a $LIB

# run from INSIDE tests/unit
cd tests/unit && $SP/numprobe_stock 1e-8 ; echo "rc=$?"
```

`make check` in `tests/unit` after a **top-level** `make`: **39/39 pass** on
`fix/json-number-fatal-exit`.
