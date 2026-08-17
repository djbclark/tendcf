# B-10 audit — json-number-fatal-exit — fable — 2026-08-16

Adversarial completeness audit of `f92cd1c` ("Do not exit the process when
rendering a JSON number") on `fix/json-number-fatal-exit` in
`/Users/djbclark/src/libntech-fixes`, plus the regression tests added on top
of it (`19c5ee8`, `tests/unit/json_test.c`).

Everything marked **verified** was executed against the fixed branch via a
scratch harness compiled against the worktree's built `libutils.a`
(`audit_probe.c` in this session's scratchpad; probe numbers below), or by
reverting the fix in the working tree and re-running the test binary.
`cfengine-core` findings are **by inspection only** — building that tree was
prohibited during this session.

---

## Verdict

**Fix needs changes.** What the commit changes is correct — verified against
every control the review demanded, and the new regression tests fail against
the pre-fix code exactly as intended — but the same document that no longer
kills the process when *rendered* still kills it when *copied*, from the same
file the fix touches. Two changes before this goes upstream:

1. **Required: `JsonPrimitiveCopy()` (libutils/json.c:250-251) needs the same
   lexeme treatment.** `JsonCopy()` of a parsed `9223372036854775808` still
   reaches `StringToLongExitOnError()` and exits (probe 1, exit 1). Worse,
   for integers that *do* fit in a long the copy path truncates through
   `JsonIntegerCreate(int)`: copying `9223372036854775807` yields `-1`
   (probe 2) and `2000000000000` yields `-1454759936` (probe 8) — silent
   corruption, arguably worse than the crash. The natural fix is what a copy
   should have been all along:
   `JsonElementCreatePrimitive(type, xstrdup(value))` for INTEGER (and it
   fixes the truncation for free). `JsonCopy()` on data containers is
   pervasive in core — `RvalCopy` (libpromises/rlist.c:484), `mergedata()`
   (libpromises/evalfunction.c:4658, 4665), custom promise modules
   (libpromises/mod_custom.c:696), eval_context.c:3724, policy.c:1693 — so
   a data file that survives rendering after this fix still takes the host
   down the moment the container is merged or copied. Shipping a commit whose
   message says large integers "survive" while `JsonCopy` of the same value
   exits is the first thing an upstream reviewer will find.

2. **Recommended, could be a separate commit: `JsonSelect()`
   (libutils/json.c:952-954).** An all-digit array index larger than
   `LONG_MAX` passes `StringIsNumeric()` and then exits in
   `StringToLongExitOnError()` (probe 3, exit 1). Reachable from core via
   `EvalContextVariableGet()` (libpromises/eval_context.c:2676) with
   `ref->indices` — i.e. `$(data[$(i)])` where the index is policy- or
   data-derived. An out-of-range index should simply not resolve
   (`return NULL`), same as a too-large in-range one already does.

The strongest case against this verdict: minimal-PR discipline. The rendering
fix stands alone, fixes the measured cf-promises-failsafe scenario, and
`JsonPrimitiveCopy` could be its own PR. I don't buy it here — the copy defect
is in the same file, same input class, same one-line technique, and the fix's
own commit message ("survive") over-claims without it. Second commit, same PR.

The core-side twins (below) cannot be fixed from libntech and belong in the
upstream email, not this PR.

---

## Defects found

| # | Where | What breaks | Status |
|---|-------|-------------|--------|
| D1 | libutils/json.c:250-251 `JsonPrimitiveCopy` | `JsonCopy` of integer > long range → `StringToLongExitOnError` → process exit. Repro: `JsonCopy` of parsed `[9223372036854775808]` (probe 1, exit 1, "Conversion error (34 - Overflow)"). Reachable from core via mergedata/RvalCopy/mod_custom (paths above). | **Verified** |
| D2 | same lines | `JsonIntegerCreate` takes `int`; copying any integer > `INT_MAX` that fits a long silently corrupts: `9223372036854775807` → `-1` (probe 2), `2000000000000` → `-1454759936` (probe 8). Pre-existing, not introduced by the fix; same family; fixed for free by the D1 lexeme copy. | **Verified** |
| D3 | libutils/json.c:952-954 `JsonSelect` | all-digit index > `LONG_MAX` → process exit (probe 3). Core reach: eval_context.c:2676. Needs absurd index, so lower severity, but same fatal family on shaped input. | **Verified** (libntech); core reach by inspection |
| D4 | libpromises/rlist.c:1729, libpromises/iteration.c:701 (core) | `StringFromLong(JsonPrimitiveGetAsInteger(...))` — the exact pattern the fix removed from mustache.c — on data-container integers. `getvalues()` or iterating a container holding `9223372036854775808` exits cf-agent. Note the exponent reclassification incidentally rescues `1e-8` here (takes the REAL branch now), but big integers remain fatal. Needs the core-side twin of this patch. | **By inspection** (building core prohibited) |
| D5 | libpromises/generic_agent.c:2051 (core) | `validated_at = JsonPrimitiveGetAsInteger(timestamp)` from `cf_promises_validated` — a corrupt local state file exits the agent. Local file, low severity. | **By inspection** |
| D6 | libenv/unix_iface.c:1440 (core) | route metric via fatal accessor on JSON built from `ip` output; only plausibly fatal on 32-bit longs with metric > 2^31. Theoretical. | **By inspection** |

Not defects, but observable behavior changes to disclose in the PR/email:

- **`datatype(x, "true")` now reports `"data real"` instead of `"data int"`
  for exponent-form numbers** (libpromises/evalfunction.c:5963). This is the
  only found case where previously *working* policy behavior changes —
  `datatype()` inspects the type without rendering, so it never hit the fatal
  path. JSON-correct, but release-note it. `JsonPrimitiveTypeToString()`
  reports "number" for both, so no change there; `JsonCompare` checks type
  then `strcmp` of the lexeme, so equality semantics are unchanged for
  same-source documents; YAML scalars route through `JsonParseAsNumber()` and
  reclassify consistently.
- **Exponent forms now render through the REAL formatter,
  `StringFromDouble()` = `"%.2f"`**: `1e-8` renders `0.00`, `2e0` renders
  `2.00`, in both `JsonPrimitiveToString()` and mustache (probes 5, 6). Not a
  regression — every one of these inputs was a process exit before — but the
  motivating value now renders as a wrong-looking `0.00`. That is the
  pre-existing REAL wart (`0.001` has rendered `0.00` forever), newly visible.
  A follow-up worth raising upstream: render REAL as parsed too, which
  `JsonWriteCompact` already does — but that changes output for every
  existing policy (`0.5` → `"0.50"` today), so it does not belong in this PR.
- **`JsonCopy` of `1e-8` yields `0.0000`** (probe 7) — `JsonRealCreate`'s
  `"%.4f"`, pre-existing REAL copy behavior; before the fix this same input
  was *fatal* on copy, so strictly an improvement.

---

## The audit questions answered

**Other reachable fatal converters on data-controlled input?** Yes — D1
(libntech, `JsonPrimitiveCopy`), D3 (libntech, `JsonSelect`), D4 (core, rlist
+ iteration), D5/D6 (core, minor). Full sweep: `JsonPrimitiveGetAsInteger`
has exactly one libntech caller left (json.c:251) and four core callers
(rlist.c:1729, iteration.c:701, generic_agent.c:2051, unix_iface.c:1440).
`StringToLongExitOnError` in json.c: lines 855 (the accessor) and 954
(`JsonSelect`). All other core `*ExitOnError` string converters are on
command-line options (cf-runagent, cf-key, cf-serverd) — acceptable use.
`JsonPrimitiveGetAsInt64ExitOnError` has no non-test callers. No direct
`DoCleanupAndExit` in json.c.

**Does INTEGER→REAL reclassification break anything?** Consumers branching on
the distinction: `JsonPrimitiveCopy` (REAL branch is non-fatal, lossy —
pre-existing), `JsonPrimitiveToString`/mustache (REAL branch renders `%.2f` —
see D6 notes), core's rlist.c/iteration.c (REAL branch non-fatal, `%.2f`),
unix_iface.c (skips non-INTEGER metrics — an exponent-form metric would now
be ignored rather than compared; `ip` does not emit exponent metrics), and
`datatype()` (the one visible change, above). Nothing that previously worked
now takes a *worse* path; several previously-fatal paths now take a survivable
one.

**Is `1e400` → REAL → renders `inf` acceptable?** Acceptable, disclose it.
Serialization is unaffected — `JsonWriteCompact` emits `1e400` verbatim
(probe 9), so documents round-trip. Only `JsonPrimitiveToString`/mustache
render `inf` (probe 4), via `strtod` → `HUGE_VAL` → `"%.2f"`. `1.0e400`
behaved identically *before* the fix, so this is an inherited wart with
slightly wider reach, not a new defect class. (`strtod`'s ERANGE consumes the
whole lexeme, so `StringToDouble`'s debug assert does not fire.)

**Is returning the raw lexeme safe for every INTEGER producer?** Yes,
enumerated exhaustively: `JsonElementCreatePrimitive` is static to json.c, so
INTEGER primitives are produced only by `JsonParseAsNumber` (parser-validated
lexeme; after this fix an INTEGER lexeme matches `-?[0-9]+` — anything with
`.`/`e`/`E` is REAL), `JsonIntegerCreate` (`"%d"`), and `JsonIntegerCreate64`
(`PRIi64`). All 38 core integer-append call sites route through those two
constructors. Digits-and-minus need no HTML escaping, so mustache's
escape-bypass on the INTEGER branch stays safe.

**The process-exit failure mode and test design.** The regression cannot
always fail gracefully: on regressed code the fatal conversion kills the test
binary, not just the test. Conclusions, verified by reverting
`f92cd1c` in the working tree and re-running `json_test`:
`test_parse_exponent_numbers` asserts the REAL classification *before*
anything renders, so the classification regression fails as a normal cmockery
assertion ("Test failed.", binary continues). The large-integer cases in
`test_primitive_to_string_numbers` cannot be shielded that way — on regressed
code the binary dies at `9223372036854775808` with the conversion error and
exit 1 — but the automake harness reports that as a suite failure, which is
the guarantee a regression test owes CI. I considered fork()-and-waitpid
isolation and rejected it: no precedent in this suite for exit-status testing
(file_lock_test's fork is for lock semantics), and it would not survive the
MinGW build. The exact-lexeme assertions are deliberately platform-independent:
after the fix no conversion happens, so `9223372036854775807` renders verbatim
even where `long` is 32-bit.

**Where mustache coverage belongs.** There is no mustache test binary in
libntech's tests/unit; the render paths are covered here indirectly through
`JsonPrimitiveToString` (same expression the mustache INTEGER branch now
uses). Probe 6 verified the mustache render directly
(`1e-8|9223372036854775808|2e0` → `0.00|9223372036854775808|2.00`). A proper
`tests/unit/mustache_test.c` is a reasonable upstream proposal but a separate
one; the cf-promises-failsafe scenario itself belongs in core's acceptance
suite, not in this libntech PR.

**Test results.** Suite before change: 39/39 PASS. After adding the two
tests: 39/39 PASS, `json_test` now 71/71 internally. Against reverted code:
both new tests fail (assertion / process exit, as designed). The only build
warning in `json_test.c` is pre-existing (line ~2527, `JsonNullCreate(true)`
against a non-prototype declaration).

---

## What I did not check

- **cfengine-core was never built or executed** (prohibited this session).
  D4-D6 and all core reachability claims are code reading, not measurement.
  Before emailing, D4 deserves a live repro on the 3.27.1 build the way the
  mustache case was measured.
- **Windows/MinGW compilation of the new tests** — no cross toolchain here;
  they use only APIs already used by neighboring tests in the same file.
- **Non-core consumers of libntech** (Mender or other Northern.tech products)
  that might branch on INTEGER-vs-REAL for exponent-form numbers.
- **NDEBUG behavior of `StringToDouble`'s partial-parse assert** — no
  reachable input found that trips it, but I did not prove none exists.
- **cf-serverd/enterprise JSON paths outside the public core repo.**
- The `tests/acceptance` suites of either repo.
