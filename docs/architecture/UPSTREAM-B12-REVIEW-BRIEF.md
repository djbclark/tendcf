# UPSTREAM REVIEW BRIEF — B-12, CFEngine core default-route selection

**Frozen input, 2026-08-17.** This is the shared prompt given verbatim to each
member of the second-opinion panel. Do not edit it to reflect what the reviews
later found — the reviews are separate files, and the register records the
outcome.

Required by `upstream-register.md`: **no item is offered upstream until it has
been second-opinioned and its fork issue updated with whatever the review
found.**

---

## Your role

You are an independent reviewer of a C patch that is about to be offered to an
upstream open-source project (CFEngine Core, by Northern.tech). It was written
by a different AI model. Your job is **adversarial**: assume the patch is wrong
and try to demonstrate it. A review that finds nothing is a valid outcome, but
only after a real attempt.

The author's own uncertainties are listed at the bottom. Address each of them
explicitly and by name. Do not simply agree with the author's framing of them —
the framing may itself be the error.

## Where the code is

Repository: `/Users/djbclark/src/core-b12`, a worktree of a fork of
`cfengine/core`, on branch `fix/default-route-lowest-metric`, branched from
upstream master `17eb78e6d`.

```
git -C /Users/djbclark/src/core-b12 log --oneline 17eb78e6d..HEAD
git -C /Users/djbclark/src/core-b12 diff 17eb78e6d..HEAD
```

Read the surrounding file, not just the diff:

- `libenv/unix_iface.c` — `GetNetworkingInfo()` and the `/proc/net/route`
  parsing around it
- whatever test file the diff touches under `tests/unit/`
- how the selected `default_route` is consumed downstream

You have read access to the whole repo and the web. **Write nothing except your
own output file. Do not commit, push, branch, or modify any existing file.**

## The defect

`GetNetworkingInfo()` in `libenv/unix_iface.c` (around line 1425 at
`17eb78e6d`) declares:

```c
long lowest_metric = 0;
```

and **never assigns it**. The route-selection guard is:

```c
(default_route == NULL || JsonPrimitiveGetAsInteger(metric) < lowest_metric)
```

So once `default_route` is non-NULL, the comparison is `metric_value < 0` —
false for every real metric. CFEngine therefore selects the **first** active
default gateway it encounters, not the lowest-metric one, contrary to both the
variable's name and the comparison's evident intent.

Tracked as CFE-4723 / fork issue `djbclark/core#14`.

## What the review must attack

Do not stop at "does the patch assign the variable". Specifically:

1. **Semantics.** Is lower-metric-wins actually the right rule here, and is that
   what upstream intends? Check how `default_route` is consumed downstream.
2. **The metric parse.** The capture regex takes `metric` as `[[:xdigit:]]+`.
   `/proc/net/route` writes most fields in hex but the metric in **decimal**.
   Determine what the code actually does with the captured string, whether that
   is correct, and whether the author was right to include or exclude a fix for
   it. A patch that carries two behaviour changes at once is a review finding;
   so is one that silently leaves a known adjacent bug in a line it edited.
3. **Tie-breaking.** First-wins or last-wins on equal metrics, and is the
   author's choice defensible and consistent with the pre-patch behaviour?
4. **Types.** Is `long` right given what `JsonPrimitiveGetAsInteger()` returns?
   Look for narrowing or signedness problems.
5. **Behaviour change.** This changes which gateway CFEngine reports on a
   multi-default-gateway host. Is the commit message honest about that? Would
   an upstream maintainer consider it a fix or a regression risk?
6. **The test.** Does it genuinely discriminate — fail before, pass after — or
   does it merely exercise the code? Could it pass against the unfixed source?

## Traps you must control for

These have burned prior work in this series. Your review must state what you did
about each of them.

1. **Never read a return code through a pipe.** `rc` from a pipeline is the last
   command's. A prior session reported a stale binary's output as a fixed result
   because a failed `cc`'s rc came from a pipe. Write `echo "RC=$?"` to a file
   immediately after the command, and use distinct output filenames for anything
   you compile.
2. **`cf-promises` in the build tree is a libtool wrapper script**, not the
   binary. The real one is `cf-promises/.libs/cf-promises`. Using the wrapper
   makes `cf-agent` silently fall back to failsafe and return in ~0.26s having
   run nothing.
3. **`--bindir` is wrong for an in-tree build.** The acceptance harness needs
   explicit `--agent=` / `--cfpromises=` / … paths. All tests failing in ~2
   seconds is a harness bug, not a result.
4. **Platform.** This is a Linux `/proc/net/route` code path and the host is
   **macOS 26.6.1 (25G76), arm64, Apple clang 21.0.0**. State plainly which of
   your claims are measured here and which are reasoned about a path you cannot
   execute. A prior session in this series published a wrong OS string and had
   to correct it publicly — do not assert a platform you did not check.

A review that asserts a before/after difference it did not measure is worth less
than one that says "I could not run this, here is what I read instead."

## What the author actually did

Commit `3d10206ee` on `fix/default-route-lowest-metric`. The selection loop was
lifted out of `GetNetworkingInfo()` into a new static helper
`FindLowestMetricDefaultRoute()`, whose single behaviour change is recording the
selected route's metric (`lowest_metric = metric_value;`) so that a later,
strictly-lower-metric route can win. Ties remain first-wins. A new
`tests/unit/unix_iface_test.c` adds 7 cases via the `#include <unix_iface.c>`
pattern, following the `sysinfo_test` precedent, guarded by `if !NT`.

The author resolved the hex-vs-decimal question against Linux v6.9 sources:
`net/ipv4/fib_trie.c` prints the metric (`fi->fib_priority`) with `%d`, i.e.
decimal, which matches CFEngine's existing `hex_mode=false` parse. Conclusion:
**no second defect**; the `[[:xdigit:]]+` capture is merely over-permissive
(decimal is a subset of xdigit) and was left for a separate cosmetic patch.

Independently re-verified by the commissioning session, not merely reported:
building with only the line `lowest_metric = metric_value;` deleted gives build
rc 0 and test run rc 1, with exactly `test_lowest_metric_last` failing
(`"192.168.0.1" != "192.168.0.3"` — the first route winning instead of the
lowest). Restore is byte-identical, sha256
`4e6bd587940c991015051581264b950180de547f59a537889d6108ed9359e843`, and all 7
pass again. Note `test_lowest_metric_first` is a deliberate control: it passes
even against the unfixed code.

## The author's uncertainties

Address each explicitly and by name.

1. **Tie-break.** Kept first-wins (strict `<`), preserving the old behaviour on
   ties. The author reasoned, but did not measure, that the kernel prefers the
   first matching FIB entry among equal-priority routes. If upstream knows
   better (multipath nuances), `test_equal_metrics_keep_first` encodes the
   choice and would have to change with it.
2. **Route JSON shape.** That Linux-parsed routes carry `"metric"` as a JSON
   integer and `"active_default_gateway"` as a JSON bool is read from
   `NetworkingRoutesPostProcessInfo()` / `JsonExtractParsedNumber()` source, not
   executed on Linux.
3. **Kernel format stability.** The `%d`-decimal claim is verified against v6.9
   only. Older kernel trees were not audited.
4. **Huge metrics.** `fib_priority` is `u32` printed with `%d`, so a metric
   ≥ 2^31 prints negative, parses negative, and **post-fix would beat every
   normal route** — where pre-fix it would only win if listed first. Treated as
   pathological input and not special-cased. *Attack this one hardest: it is a
   behaviour change on malformed-but-real kernel output.*
5. **`if !NT` guard.** Mirrors `nfs_test` and matches `unix_iface.c` being
   `if !NT` in `libenv/Makefile.am`, but a MinGW build was not verified.
6. **No Linux end-to-end test.** No test crosses the regex + post-processing +
   selection pipeline on a real route file; the test starts from post-processed
   JSON. A `CFENGINE_TEST_OVERRIDE_PROCDIR` fixture test is the natural
   follow-up; the author declined to ship a test they could not run.
7. **Full suite not rerun after the final restore.** Only `unix_iface_test` was
   rerun; the restored file is sha256-identical to the state in which the full
   69-test suite passed.
8. **LDADD breadth.** Copied `sysinfo_test`'s LDADD (`libtest.la, libenv.la,
   libpromises.la`); `libenv.la` may be redundant. Link behaviour on non-Apple
   linkers was not verified.

## Adjacent issues the author deliberately did NOT fix

Judge whether each was correctly deferred, or whether leaving it makes the patch
incoherent:

- Regex character classes: `metric` and `irtt` are decimal fields captured as
  `[[:xdigit:]]+`, while `refcnt`/`use`/`mtu`/`window` use `\d+`.
- The TODO at `unix_iface.c:1061`, now answerable.
- `long`→`int` narrowing: `JsonExtractParsedNumber()` parses `%ld` but stores via
  `JsonObjectAppendInteger(..., int)`. Pre-existing, affects all `/proc` numeric
  fields.
- `JsonExtractParsedNumber()` returns 0 on sscanf failure while leaving the raw
  string in place, indistinguishable from a parsed 0.
