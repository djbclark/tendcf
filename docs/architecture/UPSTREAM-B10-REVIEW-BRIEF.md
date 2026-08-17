# UPSTREAM REVIEW BRIEF — B-10, libntech JSON number handling

**Frozen input, 2026-08-16.** Shared prompt given verbatim to each member of the
second-opinion panel for B-10. Do not edit it to reflect what the reviews found.

This item is **not yet upstream**. It is on our fork only, and it is headed for
`security@northern.tech` plus an upstream issue and PR. Nothing has been sent.
Your review is one of the gates it has to clear first.

---

## Your role

You are an independent reviewer of a C patch about to be offered to Northern.tech's
`libntech`. It was written by a different AI model. Your job is **adversarial**:
assume the patch is wrong and try to demonstrate it. Finding nothing is a valid
outcome, but only after a real attempt.

Prefer measurement over reasoning from memory. Two claims by this same author
have already been overturned by measurement in related work, and one earlier
verification in *this* item was wrong for a build-system reason (see "A trap
that already caught us" below).

## Where the code is

```sh
cd /Users/djbclark/src/libntech-fixes          # git worktree, branch fix/json-number-fatal-exit
git log --oneline origin/master..HEAD          # three commits
git diff origin/master..HEAD
```

`origin` is `NorthernTechHQ/libntech` (upstream, base `0c0620d`); `fork` is
`djbclark/libntech`. The tree is **already configured and built** — run
`make -j2` (the machine is busy), and run the unit tests from **inside**
`tests/unit`.

The consumer that sets severity is `/Users/djbclark/src/cfengine-core`, a fork
of `cfengine/core`. **Read it, but do not build or modify it** — its `libntech`
submodule must stay uncommitted and other work is using that checkout. Stock
CFEngine 3.27.1 is at `/opt/homebrew/bin/cf-agent` and `/opt/homebrew/bin/cf-promises`.

**Write nothing except your own output file. Do not commit, push, branch, or
modify any existing file in any repository.**

## The defects

All three are shapes of one mistake: *a JSON number is rebuilt from a C numeric
type instead of being taken as the text the parser already kept.*

**1. Exponent notation without a decimal point terminates the process.** The
number parser tracks `seen_exponent` but classified REAL vs INTEGER on
`seen_dot` alone, so `1e-8`, `1E5`, `-2e-3` and `2e0` became INTEGER primitives
holding a lexeme `strtol()` cannot read. Rendering one reaches
`StringToLongExitOnError()` → `DoCleanupAndExit()`.

**2. Integer magnitude beyond `long` terminates the process.** JSON sets no
limit on magnitude, so `9223372036854775808` and larger are valid input.

**3. `JsonPrimitiveCopy()` silently changed numbers.** `JsonIntegerCreate()`
takes an **`int`** while `JsonPrimitiveGetAsInteger()` returns a **`long`**, so
`2000000000000` copied as `-1454759936` and `LONG_MAX` copied as `-1`;
`JsonRealCreate()` formats `%.4f`, so `0.00049` copied as `0.0005`.
`JsonSelect()` had the same fatal conversion for an all-digit array index.

### Measured on stock 3.27.1

A `readjson()` data file containing `1e-8`, rendered with `string_mustache()`:

```
error: Conversion error (-83 - Not terminated) on '1e-8' (StringToLongExitOnError)
error: Policy failed validation with command '.../cf-promises'
error: CFEngine was not able to get confirmation of promises from cf-promises, so going to failsafe
```

**cf-agent cannot validate its policy and falls back to failsafe.** Controls
`0.00000001`, `2`, `1.5e3`, `42`, `9223372036854775807` all pass.

## The fix

Exponent-bearing numbers are classified REAL. `JsonPrimitiveToString()`,
mustache's integer case, `JsonPrimitiveCopy()` and `JsonSelect()` use the parsed
lexeme instead of converting — which is what `JsonWriteCompact()` already does
for the same element.

## Questions to answer explicitly

1. **Is the severity right?** We intend to send this to `security@` on an
   availability argument, on the standing rule "when in doubt, security@".
   Argue it either way and decide. How reachable is this in practice — who
   controls CMDB/`host_specific.json`/`readjson()` input on a real deployment,
   and is "attacker-controlled" honest or overstated?
2. **Is classifying exponent numbers as REAL correct, or a compatibility
   break?** What consumes `JsonGetPrimitiveType()` and branches INTEGER vs REAL?
   We know `datatype()` now reports `"data real"` for `2e0`. What else changes,
   and is any of it worse than the crash it replaces?
3. **Is returning the raw lexeme safe for every producer of a primitive**, not
   just the parser? Audit every path that constructs one. Can a primitive's
   stored string ever be something you would not want emitted verbatim —
   injection into rendered output, a value that is not valid JSON, anything?
4. **Is the `JsonPrimitiveCopy()` change complete and correct?** It now calls
   `JsonElementCreatePrimitive()` with `xstrdup()`. Check ownership and lifetime
   against every caller, and confirm no leak or double free. Does copying now
   preserve type as well as text in every case?
5. **`1e400` now parses as REAL and renders as `inf`.** Is that acceptable, or a
   new defect the fix introduces?
6. **What did the fix miss?** `JsonPrimitiveGetAsInteger()` is still fatal by
   construction. Census every remaining caller reachable from parsed data, in
   **both** repositories. We believe `cfengine/core`'s `libpromises/rlist.c` and
   `libpromises/iteration.c` are twins of this bug and have fixed them on a
   separate core branch, unverified — check whether that belief is right and
   whether anything else is left.
7. **Are the regression tests any good?** `tests/unit/json_test.c` gained
   `test_parse_exponent_numbers`, `test_primitive_to_string_numbers` and
   `test_copy_preserves_numbers`. Would each actually fail against the unfixed
   code? Is there a case they should cover and do not?

## A trap that already caught us

Running `make check` inside `tests/unit` does **not** rebuild `../libutils`, so
the test binary silently links whatever `libutils.a` was last built. This
produced both a false green and a false red during development before it was
noticed. **If you assert a before/after difference, do a top-level `make` first
and delete the test binary to force a relink**, or you will measure the wrong
library. Please say explicitly how you controlled for this.

## Also worth checking, unprompted

- `CONTRIBUTING.md` code style, log levels and commit hygiene. Its *process*
  section is deliberately not followed here. Note the commits deliberately carry
  **no `Ticket:` or `Changelog:` trailer** — there is no upstream issue number
  yet, and inventing one is a mistake we have already made and had to repair.
- Anything a maintainer would reasonably push back on.

## Deliverable

Write **one file**:
`docs/architecture/upstream-opinion-b10-<your-slug>-2026-08-16.md` in
`/Users/djbclark/src/tendcf`, with `<slug>` from your launch prompt.

1. **Verdict** — *ship as is*, *ship with changes* (list them), or *do not ship*
   (say why).
2. **Severity verdict** — `security@` or ordinary bug channel, with reasoning.
3. **Defects found**, each with file and line, what breaks, how to reproduce.
   Distinguish **verified** (you ran it) from **suspected**.
4. **The seven questions**, answered by number.
5. **What you did not check.**

**Independence:** do not read any other `upstream-opinion-*.md` file, and do not
read `docs/handoffs/`. Everything else in either repository is fair game.
