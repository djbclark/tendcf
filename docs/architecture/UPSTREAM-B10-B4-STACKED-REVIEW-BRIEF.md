# UPSTREAM REVIEW BRIEF — B-4 + B-10 stacked, libntech JSON numbers

**Frozen input, 2026-08-17.** Shared prompt given verbatim to each member of
the second-opinion panel. Do not edit it to reflect what the reviews find.

This is the **second** panel on this material. The first one reviewed B-10
alone and reported complete (`ship with changes`, severity `security@`). Two
things changed afterwards and are why you are being asked:

1. **The severity claim the first panel assessed was wrong — too narrow.** They
   reviewed a *rendering* defect. It is a *load-time* defect. See "What is new"
   below.
2. **B-4 and B-10 are now one stack**, because measurement showed they are not
   independently landable. B-4 has **never been reviewed by anyone**.

Nothing has been sent upstream. No issue, no PR, no email. Your review is a
gate this has to clear first, and the standing rule here is that **no upstream
contact happens until every commissioned review has reported** — a previous
item was sent at a 2-of-3 quorum and the third review landed with material that
forced a correcting follow-up to `security@`.

---

## Your role

You are an independent reviewer of a C patch series about to be offered to
Northern.tech's `libntech`, and reported to `security@northern.tech`. It was
written by a different AI model. Your job is **adversarial**: assume the patch
and its severity claim are wrong, and try to demonstrate it. Finding nothing is
a valid outcome, but only after a real attempt.

Prefer measurement over reasoning from memory. This author has had **four**
conclusions overturned by measurement in this work, and **four separate
build-system traps** have each produced a false verification. Both lists are
below — read them before you assert any before/after difference.

## Where the code is

```sh
cd /Users/djbclark/src/libntech-fixes     # git worktree, branch fix/json-number-fatal-exit
git log --oneline 0c0620d..HEAD           # six commits: B-4 (2) then B-10 (4)
git diff 0c0620d..HEAD
```

The stack, oldest first:

| commit | what |
|---|---|
| `fe1ace9` | **B-4** — do not truncate JSON reals to two decimals when rendering |
| `7034791` | **B-4** — its regression test (added 2026-08-17; B-4 had none) |
| `bf57367` | **B-10** — do not exit the process when rendering a JSON number |
| `5da4c57` | **B-10** — regression tests for classification and rendering |
| `8aac759` | **B-10** — copy a JSON number as it was parsed |
| `cc4a0d9` | **B-10** — cover `JsonSelect()` with an oversized array index |

`origin` is `NorthernTechHQ/libntech` (upstream, base `0c0620d`); `fork` is
`djbclark/libntech`. The tree is **already configured and built** — run
`make -j2` (the machine is busy), and run unit tests from **inside**
`tests/unit`. Expect 39/39.

The consumer that sets severity is `cfengine/core`. There is a **built** core
tree at `/Users/djbclark/src/core-json` (branch `fix/json-number-rendering`,
which carries core's half of the same defect plus a new regression test). You
may build and run it. Do **not** modify `/Users/djbclark/src/cfengine-core` —
other work uses that checkout. Stock CFEngine 3.27.1 is at
`/opt/homebrew/bin/cf-{agent,promises}`.

**Write nothing except your own output file. Do not commit, push, branch, or
modify any existing file in any repository.**

## What is new since the first panel — the thing you are really here to check

The first panel was told, and agreed, that the trigger is *rendering*: a value
has to reach `string_mustache()` or a list/iteration context before anything
converts it and dies.

That is wrong. Measured 2026-08-17 against a build carrying **core's** half and
**stock** libntech, this policy is sufficient:

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

with `9223372036854775808` anywhere in `numbers.json`. There is **no
iteration, no mustache, and nothing that renders the value**. The variable is
merely declared. Result: `cf-promises` dies at **policy-load time** and
`cf-agent` falls back to failsafe. Stack, from `lldb` with the breakpoint
conditioned on the value rather than inferred:

```
StringToLongExitOnError(str="9223372036854775808")   string_lib.c:656
JsonCopy                        <- JsonPrimitiveCopy, inlined
JsonCopy
JsonObjectCopy
RvalNewRewriter
VerifyVarPromise
ExpandPromise
BundleResolvePromiseType
PolicyResolve
LoadPolicy
main                            cf-promises.c:156
```

The fatal site is **`JsonPrimitiveCopy()`**, reached because storing a JSON
container as a CFEngine variable deep-copies it. A second trace shows the same
chain via `EvalContextVariablePutSpecial` ← `DetectEnvironment`, i.e. it also
runs on `sys.*` containers before any user policy is evaluated.

**Your first job is to try to break that claim.**

## The defects, as we now understand them

All are shapes of one mistake: *a JSON number is rebuilt from a C numeric type
instead of being taken as the text the parser already kept.*

1. **`JsonPrimitiveCopy()` converts on every copy.** Fatal for magnitudes past
   `LONG_MAX`; silently corrupting past `INT_MAX` because `JsonIntegerCreate()`
   takes an `int` (`2000000000000` copied as `-1454759936`, `LONG_MAX` as `-1`);
   lossy for reals via `JsonRealCreate()`'s `"%.4f"`.
2. **Exponent notation without a decimal point is misclassified INTEGER.**
   `JsonParseAsNumber()` branched on `seen_dot` alone, so `1e-8`, `1E5`, `2e0`
   became integer primitives holding a lexeme `strtol()` cannot read.
3. **Integers past `LONG_MAX` are fatal on render.** JSON puts no limit on
   magnitude.
4. **Reals render through `"%.2f"`** (B-4), so `0.00049` renders as `0.00` — a
   wrong value, not a rounded one — and it disagrees with `JsonWriteCompact()`.

## Why the two are stacked, and what to check about that

They were recorded as independently landable. That is true for the integer axis
and **false** for the real axis, which was measured, not argued:

- Applying B-4 on top of B-10 **broke B-10's own test suite** — the old
  `json_test.c:1336` pinned `assert_string_equal("0.50", str)`. Corrected in
  `5da4c57`.
- B-10 alone emits **`inf`** for `1e400` through `string_mustache()` —
  confirmed at product level. Stock never did this: with no decimal point
  `1e400` is misclassified INTEGER and **terminates the process** instead, so
  `inf` is *introduced* by B-10 alone and *removed* by B-4.

Measured mustache output, `cf-agent`, both configurations:

| value | B-10 only | B-10 + B-4 |
|---|---|---|
| `0.00049` | `0.00` | `0.00049` |
| `1e-8` | `0.00` | `1e-8` |
| `1.5e3` | `1500.00` | `1.5e3` |
| `1e400` | `inf` | `1e400` |
| integers incl. `10^30` | exact | exact |

## Questions — answer by number

1. **Is the load-time severity claim right?** Reproduce it or refute it. Is
   `security@` the correct channel, or is this an ordinary bug? Who realistically
   controls CMDB / `host_specific.json` / `readjson()` input on a real
   deployment? Our threat wording, which we intend to use verbatim, is:
   *"attacker-controlled" is overstated for a remote exploit; it is honest for a
   CMDB operator, a `readjson()` of third-party JSON, or an author who writes
   scientific notation by mistake.* Is that honest, or still overstated?
2. **Is stacking B-4 under B-10 the right call**, versus one combined commit,
   versus shipping B-10 alone with the `inf` disclosed? Note `cfengine/core`'s
   half (`6a4216dad`) fixes integers and reals together in one commit.
3. **Is B-4 correct at all?** Nobody has reviewed it. It is now the base of the
   stack and everything above inherits its behaviour change: `1.5e3` renders as
   `1.5e3`, not `1500.00`.
4. **Is returning the raw lexeme safe for every producer of a primitive**, not
   just the parser? Audit every path that constructs one. Can a stored string
   ever be something you would not want emitted verbatim?
5. **Is the `JsonPrimitiveCopy()` change complete and correct?** Ownership and
   lifetime against every caller; no leak, no double free; type preserved as
   well as text.
6. **Is classifying exponent numbers as REAL a compatibility break?** What
   consumes `JsonGetPrimitiveType()` and branches INTEGER vs REAL? `datatype()`
   now reports `"data real"` for `2e0`. What else changes, and is any of it
   worse than the crash it replaces?
7. **What did the fix miss?** `JsonPrimitiveGetAsInteger()` is still fatal by
   construction. Census every remaining caller reachable from parsed data in
   **both** repositories. We believe core's `rlist.c` and `iteration.c` are the
   only twins and have fixed them; check whether that is right.
8. **Are the regression tests any good?** Would each fail against the unfixed
   code? Note `libntech has no mustache test at all` — nothing under
   `tests/unit` references `MustacheRender()` — while `cfengine/core`'s
   spec-driven `tests/unit/mustache_test.c` does, and takes new cases as pure
   data in `tests/unit/data/mustache_extra.json`. Is proposing that the right
   move?

## Four traps that have each already produced a false verification

Say explicitly how you controlled for these if you assert a before/after
difference.

1. **`make check` inside `tests/unit` does not rebuild `../libutils`.** The test
   binary silently links whatever `libutils.a` was last built.
2. **`make -C tests/unit <test>` does not relink** on a changed archive. `rm -f`
   the binary to force it.
3. **`git stash push <file>` stashes nothing once the file is committed.** Use
   `git checkout <prev> -- <file>`.
4. **Binaries copied out of `.libs/` link against the *installed* dylib** at the
   configure prefix, not the build tree — here that was two days stale, and it
   invalidated two results before it was caught. `otool -L` the binary you are
   about to measure with. Also, `cf-agent` spawns `cf-promises` as a child and
   macOS strips `DYLD_*` across that exec, so `DYLD_LIBRARY_PATH` silently fails
   to reach the process that actually validates. Use `install_name_tool -change`.

Also: `rlist_test` in core is `XFAIL` on macOS and **aborts at its sixth test**,
so anything registered after `test_rval_to_scalar2` never runs. A test appended
at the end of that file passes vacuously.

## Four conclusions of ours that measurement overturned

Offered so you weight our claims correctly, not as settled fact:

- "The libntech test harness masks failures." **False** — retracted.
- "`inf` is acceptable but disclose." **Wrong twice over**: it is a defect, and
  it is one B-10 *introduces* rather than one stock exhibits.
- "B-4 and B-10 are independently landable." **False** on the real axis.
- "Core's half and libntech's half are twins of equal weight." The libntech half
  fires on a policy that merely declares the variable; core's needs a list or
  iteration context.

## Also worth checking, unprompted

- `CONTRIBUTING.md` code style, log levels, commit hygiene. Its *process*
  section is deliberately not followed here. The commits deliberately carry
  **no `Ticket:` or `Changelog:` trailer** — there is no upstream issue number
  yet, and inventing one is a mistake already made and repaired in this work.
- Whether every commit in the stack builds and tests green on its own.
- Anything a maintainer would reasonably push back on.

## Deliverable

Write **one file**:
`docs/architecture/upstream-opinion-b10b4-<your-slug>-2026-08-17.md` in
`/Users/djbclark/src/tendcf`, with `<slug>` from your launch prompt.

1. **Verdict** — *ship as is*, *ship with changes* (list them), or *do not ship*.
2. **Severity verdict** — `security@` or ordinary bug channel, with reasoning,
   explicitly addressing the load-time claim.
3. **Topology verdict** — stacked, combined, or B-10 alone.
4. **Defects found**, each with file and line, what breaks, how to reproduce.
   Distinguish **verified** (you ran it) from **suspected**.
5. **The eight questions**, answered by number.
6. **What you did not check.**

**Independence:** do not read any other `upstream-opinion-*.md` file, and do not
read `docs/handoffs/` or
`docs/architecture/b10-number-render-measurement-2026-08-17.md` — that last one
is our own working record of the claims you are being asked to test.
