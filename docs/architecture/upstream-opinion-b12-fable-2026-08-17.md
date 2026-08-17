# Second opinion — B-12 default-route lowest-metric fix (CFE-4723)

**Reviewer:** Claude Fable 5 (xhigh), adversarial independent review, 2026-08-17.
**Patch under review:** `/Users/djbclark/src/core-b12`, branch
`fix/default-route-lowest-metric`, commit `3d10206ee`, branched from upstream
master `17eb78e6d`. Files: `libenv/unix_iface.c`, `tests/unit/Makefile.am`,
`tests/unit/unix_iface_test.c` (new).
**Independence note:** I read the frozen brief and the repository only. I did
not read `docs/handoffs/` or any other `upstream-opinion-*` file.

## Verdict: ship as is

No required changes. The fix is minimal, correct, honestly described, and its
test genuinely discriminates (independently re-measured below, not taken on
faith). I found one place where the **author's own risk analysis is wrong —
uncertainty 4 — but wrong in the direction that makes the patch safer than the
author feared**, and one piece of kernel context the author missed that
*lowers* the regression risk further (fib alias ordering, below). Optional,
non-blocking suggestions are listed at the end.

Strongest case against my own verdict, stated so it can be acted on: (1) no
test executes the real Linux regex→post-process→selection pipeline, so the
claim that production JSON matches the test's constructed JSON rests on source
reading plus the committed Linux-generated `proc-net.cf.sub.expected.json`;
(2) a site that unknowingly depends on first-listed-route reporting under
TOS-tagged default routes would see the reported gateway change with only a
changelog-title's worth of warning. I judged both below the
required-change threshold; a maintainer who disagrees should ask for the
Linux fixture test (uncertainty 6) before merging, not for code changes.

## What is measured vs. read

Measured on this host — **macOS 26.6.1 (25G76), arm64, Apple clang 21.0.0
(clang-2100.1.1.101; the build's `gcc` is clang)**, verified via
`sw_vers`/`uname -m`/`gcc --version`, PCRE2 and other deps from Homebrew:

- Fresh compile+link+run of the shipped test (my own binaries, not the
  author's): all 7 pass, rc 0.
- Mutation experiment (single line `lowest_metric = metric_value;` deleted
  from a scratchpad copy, include-resolution proven with `-H`): rc 1, exactly
  `test_lowest_metric_last` fails with `"192.168.0.1" != "192.168.0.3"`.
  This independently reproduces the commissioning session's numbers.
- A probe driving the **real** `GetProcFileInfo()` and
  `JsonExtractParsedNumber()` (via the same `#include <unix_iface.c>`
  pattern) against hostile metric strings — results under uncertainty 4.
- Symbol-table analysis (`nm`) of the test object against every member of
  `libenv.a` — results under uncertainty 8 and "the include-TU pattern".
- `shasum -a 256 libenv/unix_iface.c` =
  `4e6bd587940c991015051581264b950180de547f59a537889d6108ed9359e843`,
  matching the author's claimed post-restore hash.

Read, not executed: everything Linux-runtime (the `#if defined(__linux__)`
post-processing body, real `/proc/net/route`), GNU-ld/gold/lld link behavior,
MinGW exclusion, and kernel behavior. Kernel claims are source reads of
`net/ipv4/fib_trie.c` at v6.9 and `net/ipv4/fib_hash.c` +
`net/ipv4/fib_semantics.c` at v2.6.32 (raw.githubusercontent.com), fetched
through a summarizing model but with the load-bearing format strings quoted
verbatim and cross-consistent with the author's independent v6.9 check.

## The defect and the fix

Confirmed against `17eb78e6d`: `lowest_metric` was declared `= 0` and never
assigned, so after the first selection the guard degenerates to
`metric < 0` and the first active default route always wins. The patch's
helper `FindLowestMetricDefaultRoute()` (unix_iface.c:1408) preserves every
guard of the old loop verbatim — same key checks, same type checks, same
short-circuit order, `JsonPrimitiveGetAsInteger` still called at most once
per candidate and side-effect-free — and adds exactly one behavioral line.
The mutant (that line deleted) is semantically identical to the pre-patch
loop, which is what makes the mutation experiment a valid before/after proxy.
`git log -S lowest_metric` confirms the loop arrived in `934950dc7`
(CFE-1991) and `git tag --contains` confirms 3.9.0 — the commit message's
history claims check out.

## The brief's six attack points

**1. Semantics.** Lower-metric-wins is the right rule: the kernel prefers the
lowest `fib_priority` among same-prefix routes, so the reported
`default_route` should be the route the kernel would actually use for
ordinary traffic. Downstream consumption is write-only within core: a repo
grep finds `default_gateway`/`default_route` produced only here
(unix_iface.c:1477-1478, into the `sys.inet` container) and consumed only by
the acceptance fixtures — no internal consumer's behavior changes.
One nuance the author missed, from kernel source: the FIB alias list — which
is what `/proc/net/route` prints — is ordered TOS/DSCP-descending, then
**priority-ascending** (v6.9 `fib_find_alias`/`fib_insert_alias`; same
invariant in v2.6.32 `fib_find_alias`, whose comment reads "Return the first
fib alias matching TOS with priority less than or equal to PRIO"). So on the
common all-TOS-0 host, `/proc/net/route` already lists default routes in
ascending metric order and the pre-patch first-wins bug was *invisible*. The
bug manifests when a TOS/DSCP-tagged default route (sorted first regardless
of metric) precedes the TOS-0 one, or with synthetic proc trees. In every
configuration I could construct on paper, the patched rule is right at least
as often as the old one, and `/proc/net/route` does not expose the TOS
column, so no better rule is available from this data source.

**2. The metric parse.** The kernel prints the metric in decimal (`%d` of
`fi->fib_priority`) — verbatim-confirmed at v6.9 (`fib_trie.c`,
`fib_route_seq_show`) *and* at v2.6.32 (`fib_hash.c`, `fib_seq_show`), which
brackets both FIB implementations across 15 years; the 11-column layout is
de facto userspace ABI (net-tools parses it). CFEngine's
`hex_mode=false`/`%ld` parse (unix_iface.c:1062, 1030) is therefore correct,
and the author's "no second defect" conclusion stands. The `[[:xdigit:]]+`
capture is over-permissive, but the author did **not** edit the regex line or
the parse lines, so the patch is not "leaving a known bug in a line it
edited" — the adjacent issue sits in untouched lines. Excluding the regex
cleanup was right, and my probe adds a reason the author didn't have:
tightening `[[:xdigit:]]+` to `\d+` is *not* purely cosmetic — today a
hex-garbage metric line ("de") still enters `sys.inet.routes` with a string
metric (measured), whereas the tightened regex would drop the line entirely.
That is a second behavior change and belongs in its own patch, exactly as
the author deferred it.

**3. Tie-breaking.** First-wins on equal metrics via strict `<`, unchanged
from pre-patch behavior on ties — and it *matches kernel semantics*: FIB
lookup walks the alias list in order and takes the first usable entry, so
among equal-priority same-TOS default routes the kernel's choice is the first
one listed in `/proc/net/route`. Source-verified (both kernel eras), not
runtime-measured. `test_equal_metrics_keep_first` pins the choice. Defensible
and consistent.

**4. Types.** `JsonPrimitiveGetAsInteger` returns `long`
(libntech/libutils/json.h:249); the patch stores it in `long metric_value`
and compares against `long lowest_metric`. No narrowing, no signedness
change introduced. The pre-existing `long`→`int` narrowing lives in
`JsonExtractParsedNumber`'s call to `JsonObjectAppendInteger(..., int)`
(json.h:307), is untouched by this patch, and is unreachable for real
metrics because `%d`-printed non-negative values are ≤ `INT_MAX`. The
`= 0` initializer on `lowest_metric` is now dead (every read is dominated by
a write via the `default_route == NULL` arm) but keeping it is correct
practice against `-Wmaybe-uninitialized`.

**5. Behaviour change.** The commit message states the defect, dates it
(CFE-1991, 3.9.0 — both verified), explicitly declares the user-visible
change with its precise trigger condition, and engages the changelog
mechanism (`Ticket: CFE-4723`, `Changelog: Title`, past-tense title in house
style). That is honest. My alias-ordering finding (point 1) means the change
is a no-op on most real hosts, which the message does not say — it
over-warns, which is the safe direction. A maintainer should read this as a
bug fix with a well-flagged, rarely-triggered behavior delta; the changelog
title is the release note. I also checked the one committed artifact that
could have silently pinned the old behavior: the acceptance fixture
`tests/acceptance/00_basics/environment/proc/proc/net/route` contains exactly
**one** active default route (metric 100, first line), so
`proc-net.cf.sub.expected.json` is unaffected by the patch — no hidden
test breakage.

**6. The test.** It discriminates, and I measured it rather than trusting the
brief: pristine build (my own compile, distinct filenames, rc captured to
files) passes 7/7; the single-line mutant fails exactly
`test_lowest_metric_last` with the first route winning. The
`test_lowest_metric_first` control passes in both builds, as designed — it
alone would *not* catch the bug, and the author correctly did not rely on it.
Test-construction fidelity is good: routes are built with the same
`JsonObjectAppendBool`/`JsonObjectAppendInteger` calls production uses, so
the JSON types match what `NetworkingRoutesPostProcessInfo()` produces on
Linux (see uncertainty 2). Registration is real: `TESTS = $(check_PROGRAMS)
$(check_SCRIPTS)` is a lazily-expanded make variable, so the later
`check_PROGRAMS += unix_iface_test` lands in `TESTS`; confirmed in the
generated `tests/unit/Makefile` (`am__append_10 = nfs_test unix_iface_test`,
active because NT is false here, comment-disabled when NT is true).

## The author's eight uncertainties, by name

**1. Tie-break.** Resolved in the patch's favor, and more strongly than the
author argued: kernel source (v2.6.32 and v6.9) shows the alias list is
priority-ascending within a TOS class and lookup takes the first match, so
first-wins-on-ties *is* the kernel's own preference, not just a
conservative default. Multipath is a non-issue for this code path: an ECMP
default route is a single alias whose `/proc` line shows only nexthop 0, so
it presents as one candidate. `test_equal_metrics_keep_first` correctly
encodes the choice. Source-verified, not runtime-measured.

**2. Route JSON shape.** Confirmed three ways: (a) source —
`JsonObjectAppendBool(route, "active_default_gateway", ...)` at
unix_iface.c:1085 and integer storage via `JsonExtractParsedNumber` →
`JsonObjectAppendInteger` at 1062/1041; (b) executed — my probe ran the real
`JsonExtractParsedNumber` on this host and got `JSON_PRIMITIVE_TYPE_INTEGER`
storage; (c) recorded Linux output — the committed
`proc-net.cf.sub.expected.json` shows `"active_default_gateway": true` (JSON
bool) and `"metric": 100` (JSON number) from a real Linux run. The author's
framing ("read from source, not executed on Linux") was accurate but the
committed fixture makes this materially stronger than they claimed.

**3. Kernel format stability.** Extended beyond the author's v6.9-only check:
v2.6.32 `fib_hash.c` prints the identical 11-column line with `%d` for
`fib_priority` (and literal `0` when `fi` is NULL). That covers both FIB
implementations from the RHEL6 era to 2024. Anything older than 2.6.32 is
irrelevant to a 2026 CFEngine release. Resolved; no patch change needed.

**4. Huge metrics — the author's framing is wrong.** The brief told me to
attack this hardest, and it falls over, but in the *safe* direction. The
claimed hazard — a metric ≥ 2^31 "prints negative, parses negative, and
post-fix would beat every normal route" — is **unreachable through the actual
pipeline**, because a `%d`-printed negative has a leading `-`, which
`[[:xdigit:]]+` cannot match, so `StringCaptureData()` rejects the entire
line and `GetProcFileInfo()` (unix_iface.c:1320-1322) drops the route before
any JSON exists. Measured on this host through the real functions: of five
fixture lines, `-1` and `-2147483648` metric lines were dropped; `600`,
`4294967295`, and `de` were captured. So on real kernel output there is *no*
behavior change at all for huge metrics, pre- or post-patch — the route is
simply invisible (absent even from `sys.inet.routes`), which is a
pre-existing parsing limitation, not this patch's concern. The author's
"treated as pathological input and not special-cased" reaches the right
decision for the wrong reason. Residual theoretical paths to a negative
integer metric in the JSON, all measured: an all-digit string in
(2^31, 2^32) parses via `%ld` and is truncated by `JsonObjectAppendInteger`'s
`long`→`int` to a negative (`"4294967295"` → stored integer `-1`), and
`sscanf` overflow saturates (`"99999999999999999999"` → `LONG_MAX` → `-1`
after truncation) — but the kernel prints the metric with `%d`, never `%u`,
in both verified eras, so digit-only values above `INT_MAX` cannot occur
outside a hand-crafted `CFENGINE_TEST_OVERRIDE_PROCDIR` fixture. Defending
against them in this patch would be dead code and a second behavior change;
correctly omitted. (Tasking item 3 answered: not reachable in practice; the
fix cannot make real-world behavior worse.)

**5. `if !NT` guard.** Verified end to end: `NT` is defined as
`mingw|cygwin` (m4/cf3_platforms.m4:35); `unix_iface.c` enters
`libenv_la_SOURCES` under the *same* `if !NT` (libenv/Makefile.am:32-35);
the test's block (tests/unit/Makefile.am:418-432) already contains
`nfs_test` and `init_script_test_helper`; and the generated Makefile shows
the conditional append mechanism working. On an NT build the test simply
does not exist, and no new compilation of `unix_iface.c` is introduced that
does not already happen. A MinGW build run would be testing automake, not
this patch — not required.

**6. No Linux end-to-end test.** Correctly deferred — shipping a test the
author could not run would violate this project's own review discipline.
Context the author didn't mention: the natural harness already exists
(`tests/acceptance/00_basics/environment/proc-net.cf` +
`CFENGINE_TEST_OVERRIDE_PROCDIR` + committed `expected.json`), and I verified
its fixture holds a single active default route, so this patch cannot change
its outcome. The right follow-up is a second fixture with a lower-metric
route listed *after* a higher-metric one, regenerated on a Linux host.

**7. Full suite not rerun after the final restore.** I did not rerun it
either — running `make check` writes into the repo tree, which this review
was forbidden to touch. Compensating evidence: the file hash matches the
state in which the author reports the 69-test suite passed (measured); my
fresh `-Wall` compile of the entire included TU produced zero diagnostics;
the helper is `static` and referenced nowhere else; the Makefile integration
was verified at the generated-Makefile level. Residual risk assessed low,
but it is honestly *unmeasured* — upstream CI will be the first full-suite
run of the exact final bytes, which is acceptable for a three-file patch of
this shape.

**8. LDADD breadth.** Settled by measurement: the test object's undefined
symbols intersect the exports of **no** member of `libenv.a` (all five
members: zero overlap), so `../../libenv/libenv.la` contributes nothing to
the link and archive-semantics linkers (GNU ld, gold, lld, ld64) will never
pull a member from it here — it is provably redundant today, harmless, and
byte-for-byte the `sysinfo_test` precedent. Keeping it is mildly
future-proof (if `unix_iface.c` ever grows a call into another libenv
member, the link keeps working in both static and shared configurations).
Non-Apple linkers reasoned about, not executed — but the reasoning reduces
to standard archive-resolution rules plus the measured empty intersection.
Leave as shipped.

## Adjacent issues deliberately not fixed — judgments

- **Regex classes (`metric`/`irtt` as `[[:xdigit:]]+` vs `\d+`):** correctly
  deferred, and the planned "cosmetic" follow-up should be re-labeled: my
  probe shows tightening the class changes what enters `sys.inet.routes`
  for garbage lines (kept-with-string-metric today vs dropped after), so it
  is a small behavior change and deserves its own commit and test.
- **TODO at unix_iface.c:1061:** now answered (IPv4 metric is decimal —
  verified across kernel eras; the IPv6 hex case is already handled via
  `hex_mode=true` at line 1107). Leaving the stale comment does not make the
  patch incoherent; folding a comment edit into a behavior patch was a
  judgment call and either choice is fine. Resolve it in the regex follow-up.
- **`long`→`int` narrowing in `JsonExtractParsedNumber`:** pre-existing,
  affects all `/proc` numeric fields, consequence measured
  (`4294967295` → `-1`), unreachable from real kernels. Correctly deferred;
  the honest fix is `JsonObjectAppendInteger64` (json.h:315) or a libntech
  change — much wider than this patch.
- **`JsonExtractParsedNumber` returning 0 on failure:** for `metric` the
  return value is unused and the failure mode (string left in place) is
  handled by the selection's type check — measured: a failed parse leaves a
  string the selection skips, identically pre- and post-patch. The
  ambiguity is only live for the `raw_flags` call at line 1070, pre-existing
  and unreachable (`%lx` on an xdigit capture). Correctly deferred.

## The include-TU pattern and the Makefile.am change (tasking item 1)

No duplicate-symbol or ODR hazard, in any configuration I could construct:

- The test object defines every symbol `unix_iface.o` exports (measured:
  zero missing), and its undefined symbols are satisfiable without pulling
  any `libenv.a` member (measured: zero overlap with all five members). An
  archive member is only loaded to resolve an undefined symbol, so
  `unix_iface.o` can never be dragged in beside the test's copy — the
  precondition for a duplicate-symbol error never arises.
- The final binary contains exactly one definition of each `unix_iface`
  extern (measured: one `T _GetNetworkingInfo`). A second copy of the code
  exists process-wide inside `libpromises.3.dylib` (whose LIBADD folds in
  the libenv convenience objects) — that is the identical topology
  `sysinfo_test` has shipped with for years, it survives even the
  `TESTS_ENVIRONMENT = DYLD_FORCE_FLAT_NAMESPACE=yes` the suite forces on
  macOS, and on ELF the executable's copy would interpose consistently.
  Both copies come from the same source text, so no observable divergence
  is possible.
- Masking analysis: `FindLowestMetricDefaultRoute` contains no conditional
  compilation — it is plain JSON-walking code — so compiling it under
  tests/unit's CPPFLAGS instead of libenv's cannot change the logic under
  test. The genuine, inherent limitation of the pattern is that the
  *production object* (`libenv/.libs/unix_iface.o`) is never executed by the
  unit test; that is equally true of `sysinfo_test` and is what the deferred
  Linux acceptance fixture would close.
- `unix_iface_test.c` is distributed unconditionally
  (`am__unix_iface_test_SOURCES_DIST` in the generated Makefile), so
  `make dist` from an NT-configured tree still packages it. The insertion
  point inside the existing `if !NT` block is coherent.

## Trap control

1. **Return codes through pipes:** every compile, link, and run in this
   review wrote `echo "RC=$?"` to a dedicated file
   (`rc_compile_pristine.txt`, `rc_link_pristine.txt`, `rc_run_pristine.txt`,
   `rc_compile_mutant.txt`, `rc_link_mutant.txt`, `rc_run_mutant.txt`,
   `rc_compile_probe.txt`, `rc_link_probe.txt`, `rc_run_probe.txt` under the
   session scratchpad's `b12review/`) as the immediately following command,
   never read through a pipe. All artifacts used distinct filenames
   (`uift_pristine*`, `uift_mutant*`, `regex_probe*`) so no stale binary
   could impersonate a fresh one; additionally the mutant's include
   resolution was proven with `gcc -H` (the mutated copy, not the repo file,
   was included) *before* interpreting its results.
2. **libtool wrapper:** I hit this trap live and controlled it: my linked
   `uift_pristine` was a 6,914-byte POSIX shell wrapper; executing the raw
   `.libs/uift_pristine` binary aborted (rc 134, dyld could not find the
   uninstalled `libpromises.3.dylib`). For *unit* tests the wrapper is the
   correct vehicle (it points dyld at the build tree) and running it gave
   rc 0 / 7 passes. I did not run `cf-promises` or `cf-agent` at all, so the
   failsafe-fallback failure mode could not occur.
3. **`--bindir` / acceptance harness:** not applicable — I ran no acceptance
   tests. The `proc-net.cf` analysis above is static (fixture file and
   committed `expected.json` read, not executed), and is labeled as such.
4. **Platform:** measured, not assumed: macOS 26.6.1 (25G76), arm64, Apple
   clang 21.0.0 (`gcc` resolves to clang), captured to `platform.txt` before
   any build. Every kernel-behavior claim in this review is a *source read*
   of a stated kernel version (v6.9, v2.6.32), fetched from
   raw.githubusercontent.com through a summarizing model with the
   load-bearing format strings quoted verbatim; none is presented as a Linux
   runtime measurement. The Linux-only post-processing body
   (`#if defined(__linux__)`) was never executed here and I have said so
   wherever it matters. I also did not run the full 69-test unit suite
   (see uncertainty 7) — that is an honest gap, not an asserted result.

## Non-blocking notes for the author

1. Housekeeping: an untracked `unix_iface_test.xml` sits at the worktree
   root (a test-run artifact, present before this review started). It is not
   in the commit and cannot enter the PR, but delete it before offering
   upstream.
2. Optional commit-message strengthener: one sentence noting that the kernel
   lists same-TOS default routes in ascending metric order, so most hosts
   see no change and the delta is confined to TOS-tagged or synthetic route
   tables. It converts the maintainer's "regression risk?" question into a
   pre-answered one. Not required — the message is already honest and errs
   toward over-warning.
3. When the deferred regex-class patch happens, do not label it cosmetic:
   tightening `[[:xdigit:]]+` to `\d+` changes whether garbage lines appear
   in `sys.inet.routes` at all (measured here). It also naturally closes the
   TODO at unix_iface.c:1061.
4. The natural Linux end-to-end follow-up is a second
   `CFENGINE_TEST_OVERRIDE_PROCDIR` acceptance fixture with a lower-metric
   default route listed after a higher-metric one; the existing
   `proc-net.cf` machinery already does everything needed and its current
   fixture is provably indifferent to this patch.
