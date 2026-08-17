# Upstream second opinion — B-12, CFEngine default-route selection

**Reviewer:** grok
**Date:** 2026-08-17
**Subject:** `djbclark/core` branch `fix/default-route-lowest-metric`, commit `3d10206ee` (parent `17eb78e6d`)
**Worktree:** `/Users/djbclark/src/core-b12`
**Ticket:** CFE-4723 / fork issue `djbclark/core#14`

---

## Verdict

**Offer upstream.** The patch does the one thing the bug requires: it records the selected metric so a later, strictly smaller metric can win. That matches the variable name (`lowest_metric`), the comparison that has been sitting dead since CFE-1991 / 3.9.0, and the kernel's own preference among same-prefix IPv4 routes. The unit test discriminates. I did not find a second behaviour change hiding in the same commit.

I did find that the author's most-worried uncertainty (**Huge metrics**) is framed incorrectly in two independent ways, and that the field blast radius of both the bug and the fix is smaller than the commit message implies. Neither is a reason to withhold the patch. Both belong on the fork issue so upstream is not sold a bigger production change than the code will actually produce.

---

## What I actually did

Read, not just the diff:

- `libenv/unix_iface.c`: `JsonExtractParsedNumber()`, `NetworkingRoutesPostProcessInfo()`, the `/proc/net/route` regex, `FindLowestMetricDefaultRoute()`, `GetNetworkingInfo()`, and the IPv6 sibling that deliberately does *not* pick a default.
- `libntech/libutils/json.c` / `json.h`: `JsonObjectAppendInteger()` takes `int`; `JsonPrimitiveGetAsInteger()` returns `long`; `JsonIntegerCreate()` prints with `%d`; `StringCaptureData()` returns NULL on a failed match.
- `tests/unit/unix_iface_test.c` and the `if !NT` / LDADD wiring in `tests/unit/Makefile.am`.
- The existing Linux fixture path `tests/acceptance/00_basics/environment/proc/proc/net/route` and `proc-net.cf.sub.expected.json`.
- Downstream: `GetNetworkingInfo()` is called from `DetectEnvironment()`; the only C consumers of the chosen route are the two writes into `sys.inet` (`default_gateway` string, `default_route` copy). Hard class `ipv4_gw_*` is set for every up+gateway route in post-process and is independent of this selection. Published docs (`sys.inet` on docs.cfengine.com) say the default is "extracted", not "lowest metric".
- Git: CFE-1991 is commit `934950dc71`, present in tag `3.9.0` (ancestor check rc 0); the unassigned `lowest_metric` is already there at 3.9.0.
- Kernel sources, fetched this session: `fib_route_seq_show` in v6.9 and `fib_seq_show` in v2.6.32; `fib_priority` is `u32` in `include/net/ip_fib.h` (v4.19).

Measured on this host (see Trap control): the 7 unit tests against the committed tree; a standalone old-vs-new selection model; a userspace analog of kernel `%d` printing a `u32`; and whether `[[:xdigit:]]+` matches a leading minus.

Not executed: the Linux `/proc/net/route` open, `NetworkingRoutesPostProcessInfo()` (it is `# if defined (__linux__)`), the acceptance fixture harness, a MinGW build, a GNU-ld link, or the full 69-test suite.

---

## Trap control

Host, checked this session, not copied from the brief:

```
Darwin mac 25.6.0 ... RELEASE_ARM64_T8103 arm64
ProductName: macOS
ProductVersion: 26.6.1
BuildVersion: 25G76
Apple clang version 21.0.0 (clang-2100.1.1.101)
Target: arm64-apple-darwin25.6.0
```

1. **Never read a return code through a pipe.** Every compile and run wrote `echo "RC=$?"` to a distinct file in `/tmp/b12-grok-review/` immediately after the command, with no pipe on that command. Observed:
   - `select_model` compile `RC=0`, run `RC=0`
   - `kernel_printf_model` compile `RC=0`, run `RC=0`
   - unit test via libtool wrapper `RC=0`
   - unit test via `.libs/unix_iface_test` plus explicit `DYLD_LIBRARY_PATH` `RC=0`
   - first attempt to run `.libs/unix_iface_test` *without* a dylib path: `RC=134` (Abort trap 6), stderr `dyld: Library not loaded: /Users/djbclark/opt/cfengine-b12/lib/libpromises.3.dylib`. Prefix `lib/` is absent. That failure is recorded; it is not a test result.

2. **`cf-promises` in the build tree is a libtool wrapper.** I did not invoke `cf-promises`, `cf-agent`, or the acceptance harness. I did confirm `tests/unit/unix_iface_test` is a libtool wrapper script (`#!/bin/sh`, "temporary wrapper script for `.libs/unix_iface_test`") and that `.libs/unix_iface_test` is the Mach-O. For a *unit* test the wrapper is the right driver (`make check` uses it; it sets the in-tree dylib path). The failsafe-fallback trap is about treating the `cf-promises` wrapper as the agent binary. I did not do that.

3. **`--bindir` is wrong for an in-tree build.** I did not run `testall` or any acceptance test, so I did not pass `--bindir`. The existing `proc-net.cf` is Linux-only (`test_skip_unsupported` = `!linux`) and I am not on Linux.

4. **Platform.** Claims below are tagged **measured** (this macOS host) or **reasoned** (Linux `/proc` / kernel path, not executed here). I did not assert Linux, and I did not reuse an OS string from another session.

I did **not** delete `lowest_metric = metric_value;` in the worktree and rebuild. The brief forbids modifying existing files. Discrimination of the old vs new comparison was measured instead with `/tmp/b12-grok-review/select_model`, a standalone reproduction of the two guards. Current `libenv/unix_iface.c` sha256 is `4e6bd587940c991015051581264b950180de547f59a537889d6108ed9359e843`, matching the author's claimed restore hash. I ran the in-tree unit test against that file; all 7 passed. I did not rerun the full suite.

---

## 1. Semantics — is lower-metric-wins the right rule?

**Yes, as a description of what this C function was written to do. The published contract is weaker.**

`lowest_metric` has been in the loop since CFE-1991 (`934950dc71`, in 3.9.0). The comparison is `<`. The helper's new comment restates that. That is the code's intent, and it has been broken for the entire life of `sys.inet`.

Downstream of the selection there is no second policy. `GetNetworkingInfo()` copies the winner into:

- `sys.inet.default_gateway` — the gateway string
- `sys.inet.default_route` — a JSON copy of that one route object

`DetectEnvironment()` calls `GetNetworkingInfo()` unconditionally. I found no other C reader of those two keys. `ipv4_gw_<addr>` hard classes are applied in `NetworkingRoutesPostProcessInfo()` to every up+gateway route and do not depend on this choice. This is inventory, not forwarding.

The user-facing docs (CFEngine LTS `sys.inet`) say only that the default is "extracted" from the route table. They do not say "lowest metric". A maintainer who treats ten years of first-wins as the contract could call this a behaviour change. I would not: the identifier, the comparison, and the 3.9.0 changelog all describe a lowest-metric extraction that never worked.

Two caveats, both reasoned from kernel source, not measured on a live FIB:

- `/proc/net/route` dumps the **main** table only (`fa->tb_id != tb->tb_id` skipped). Policy-routing defaults in other tables are invisible before and after. Out of scope.
- Aliases for the same prefix are inserted in increasing `fib_priority` order (`fib_find_alias` + `hlist_add_before`). `fib_route_seq_show` walks that list. On a kernel-generated file, multiple `0.0.0.0/0` lines should already appear lowest-metric first, so **first-wins and lowest-metric-wins coincide for the common "two DHCP defaults, metrics 100 and 600" host**. The bug is real in the C; it is likely silent on stock `/proc/net/route`. The existing acceptance fixture has a single default (`metric 100` on `enp4s0`) and cannot tell the two rules apart.

TOS/DSCP-specific defaults are the one reasoned case where file order is *not* global-metric order (sorted by TOS, then priority). CFEngine ignores TOS and treats every `dest == 0.0.0.0 && UP && GATEWAY` row as a candidate. Post-fix it would prefer a later TOS-specific row with a smaller metric over an earlier TOS-0 row. Rare. Worth a sentence on the fork issue, not a rewrite.

Multipath: the kernel prints only `fib_info_nhc(fi, 0)`. Pre-existing, untouched.

IPv6: `NetworkingIPv6RoutesPostProcessInfo()` still has the TODO "figure out if we can grab any default gateway info here". Out of scope; the patch does not pretend to touch it.

---

## 2. The metric parse — hex capture, decimal field

**The author is right that this is not a second defect in the selection patch. The author is incomplete about what `[[:xdigit:]]+` actually rejects.**

Reasoned from kernel source, measured in userspace:

| Tree | Function | Metric print |
|---|---|---|
| Linux v2.6.32 `net/ipv4/fib_hash.c` `fib_seq_show` | `fi->fib_priority` with `%d` | decimal |
| Linux v6.9 `net/ipv4/fib_trie.c` `fib_route_seq_show` | `fi->fib_priority` with `%d` | decimal |

Same file, hex: dest/gw/mask `%08X`, flags `%04X`. The comment in both eras is that the `/proc/net/route` format is not supposed to change (legacy utilities). CFEngine's own regex comment shows `1024` in the metric column. `NetworkingRoutesPostProcessInfo()` already parses metric with `hex_mode=false` (`%ld`). IPv6 is the hex one (`raw_metric`, `hex_mode=true`).

So a normal metric `100` / `1024` is decimal, matches `[[:xdigit:]]+` because digits are a subset of xdigit, and parses as 100 / 1024. The existing fixture line `enp4s0 ... 100 ...` is that case. There is no silent hex-vs-decimal misparse on kernel output.

Leaving the character class alone is the right call for *this* commit. Editing it here would be a second behaviour change (which lines match). The brief is correct that bundling that in would be a finding.

What the author understated: `[[:xdigit:]]+` is not merely over-permissive. It is also **under-permissive for a signed decimal**, which is exactly what `%d` emits when `fib_priority >= 2^31`. Measured on this host with a reconstructed `/proc` line and a Python transcription of the capture:

```
MATCH  metric=100              line_metric_field=100
NOMATCH                        line_metric_field=-2147483648
NOMATCH                        line_metric_field=-1
```

`StringCaptureData()` returns NULL on a failed match; `GetProcFileInfo()` then skips the line. A high `u32` metric never becomes a JSON integer, never reaches `FindLowestMetricDefaultRoute()`, and never "beats every normal route". It disappears from `sys.inet.routes` entirely. That drop is pre-existing and is not on a line this patch edited.

IPv6's hex metric is a different file and a different `hex_mode`. Not this bug.

---

## 3. Tie-breaking

**First-wins on equal metrics is the right choice, and it is the pre-patch behaviour.**

Strict `<` plus "first assignment wins" is what the old loop did on ties (and on everything else, accidentally). The kernel alias list for equal priority keeps insertion order (unless `NLM_F_APPEND`). `test_equal_metrics_keep_first` encodes it. If upstream later wants last-wins or "any of a multipath group", that test is the tripwire. Do not change it in this patch.

The author's "kernel prefers the first matching FIB entry among equal-priority routes" is a reasonable reading of `fib_table_lookup` walking the hlist. I did not execute a kernel. I do not need to: preserving the old tie rule is the conservative option either way.

---

## 4. Types

**`long` is the right local type. The interesting narrowing is one call earlier, and this patch does not introduce it.**

- `JsonPrimitiveGetAsInteger()` returns `long` (`StringToLongExitOnError` on the stored text).
- `JsonObjectAppendInteger()` takes `int` and stores `printf("%d")`.
- `JsonExtractParsedNumber()` scans `%ld` into a `long`, then hands that `long` to `JsonObjectAppendInteger()`.

On this host, **measured**: `sizeof(int)=4`, `sizeof(long)=8`. The narrowing lives in `JsonExtractParsedNumber()`, which this commit does not touch, and it applies to every `/proc` integer, not just metric.

For kernel-printed metrics the string is produced by `%d`, so it is already in `int` range. The `long` in the new helper is lossless relative to what JSON actually stores. Switching the helper to `int` would match the store type and would also be fine; it is not required.

A hypothetical kernel that printed metric with `%u` would hand `"2147483648"` to `%ld` (fits in `long`) and then truncate to `int` (`-2147483648` on this ABI, measured). That is the pre-existing narrowing, not this patch.

---

## 5. Behaviour change and the commit message

**The commit message is honest about the C change. It oversells the likely production change.**

Accurate:

- The unassigned `lowest_metric` made `metric < 0` the only way a later route could win.
- That has been true since CFE-1991 / 3.9.0 (verified: tag `3.9.0` contains the unassigned variable).
- After the patch, a later strictly-smaller metric replaces the earlier choice.
- `sys.inet.default_route` and `sys.inet.default_gateway` are the variables that move.

Overstated, if read as a field report: "on hosts with several active default routes where a lower-metric route appears after a higher-metric one". That file order is what the unit test constructs. It is not what `fib_route_seq_show` normally emits for same-prefix aliases. An upstream maintainer who asks "will this flip `sys.inet.default_gateway` on a dual-homed NM laptop?" should hear **probably not, the file is already sorted; the patch makes the C match its name if the file is ever unsorted**.

That is an argument *for* offering: regression risk is low *because* the realistic file order already agrees with the intended rule. The leftover first-wins-on-ties keeps the one case that was previously well-defined.

I would treat this as a fix, not a feature, and I would not demand a docs change as a prerequisite. A one-line note in the PR that `sys.inet` docs currently say only "extracted" is enough.

---

## 6. The test

**It discriminates. It is not a thorough test of the pipeline.**

Independently modeled (not by editing the worktree). Old guard = never assign `lowest_metric`; new guard = assign. Same route tables as the unit test:

| Case | old | new | agrees with author? |
|---|---|---|---|
| lowest last (600, 100, 50) | `192.168.0.1` | `192.168.0.3` | yes — this is CFE-4723 |
| lowest first (100, 600) | first | first | yes — control, passes on unfixed |
| equal 100/100 | first | first | yes |
| first 0, later 50 | first | first | (not in the test; both keep 0) |

So `test_lowest_metric_last` fails on the unfixed comparison (`"192.168.0.1" != "192.168.0.3"` in the author's rebuild; my model produces the same pair). The other six cases do **not** discriminate. The author said so. That is acceptable as long as nobody cites "7 new tests" as 7 independent proofs.

Gaps I would not block on:

- No constructed JSON with a negative metric. Given §2, that input is not on the real parse path anyway.
- No string-typed leftover metric (`JsonExtractParsedNumber` failure). `test_inactive_and_incomplete_routes_are_skipped` covers a *missing* metric key, which is the same skip in the helper.
- Pointer equality plus a gateway-string check in the discriminating case is the right assertion shape.
- `#include <unix_iface.c>` matches `sysinfo_test`. Heavy, but it is the house style, and it compiled and ran here.

Could the committed test file pass against unfixed `unix_iface.c`? Only if `test_lowest_metric_last` were removed or weakened. As written, no.

---

## Author uncertainties, by name

### 1. Tie-break

The framing is fine. First-wins is pre-patch behaviour, matches the kernel alias-list rule as I read it, and is locked by `test_equal_metrics_keep_first`. "If upstream knows better about multipath" is the wrong fear: `/proc/net/route` never shows the extra nexthops (`fib_info_nhc(fi, 0)` only). Multipath cannot change this function's input shape. Keep strict `<`.

### 2. Route JSON shape

Reasoned from source, not executed on Linux, same as the author. `NetworkingRoutesPostProcessInfo()` is `# if defined (__linux__)`:

- `JsonExtractParsedNumber(..., "metric", "metric", false, false)` replaces the captured string with a JSON integer on successful `%ld`.
- `JsonObjectAppendBool(..., "active_default_gateway", is_default_route && is_up && is_gw)`.

On a failed metric parse the key remains a string; the helper then skips it (`JSON_PRIMITIVE_TYPE_INTEGER` required). The unit test constructs the post-process shape directly, which is legitimate for a selection-unit test and is exactly why it can run on macOS. The author should not have been more confident than "read the source". They were not.

### 3. Kernel format stability

The "v6.9 only" framing is too timid, and it is the one uncertainty I could actually widen. I fetched v2.6.32 `fib_seq_show` and v6.9 `fib_route_seq_show`. Both print `fib_priority` with `%d`. Both say the `/proc/net/route` format is not supposed to change. That covers the kernels CFEngine 3.9.0 through current would have seen. I did not walk every tag in between; I do not need to in order to say "this is not a v6.9 curiosity".

### 4. Huge metrics — the author's framing is the error

Attack this one, as requested. Three facts, two of them measured.

**A. Pre-fix already lets a later negative win.** The old comparison after the first selection is `metric < 0`, not `metric < selected`. A later printed-as-negative metric beats an earlier normal metric *before and after* this patch. Measured with the standalone model:

```
huge_later (100 then INT_MIN):  old=192.168.0.2 new=192.168.0.2 SAME
huge_first (INT_MIN then 100):  old=192.168.0.1 new=192.168.0.1 SAME
```

The author's sentence "post-fix would beat every normal route — where pre-fix it would only win if listed first" is **false**.

The only huge-vs-huge difference the assignment introduces, measured:

```
two_huge less-neg later (INT_MIN then -1): old=192.168.0.2 new=192.168.0.1 DIFFER
```

Pre-fix, any later negative replaces the current choice (`< 0`). Post-fix, the more negative value is kept. That is the comparison starting to work, not a new landmine.

**B. The real pipeline never delivers that integer.** `fib_priority` is `u32`. `%d` of `2^31` is `"-2147483648"`; of `UINT32_MAX` is `"-1"`. Measured on this ABI:

```
2^31     kernel_%d_print="-2147483648"  sscanf_%ld=-2147483648  stored_int=-2147483648
UINT32_MAX kernel_%d_print="-1"         sscanf_%ld=-1           stored_int=-1
```

The capture is `[[:xdigit:]]+`. A leading minus does not match. The line is dropped in `GetProcFileInfo` before post-process. Selection cannot prefer a route it never saw. Calling this "malformed-but-real kernel output" is also slightly wrong: it is well-defined kernel output of a well-defined `u32`, printed with the wrong conversion specifier. The malformation is in `seq_printf`, and CFEngine's regex already refuses it.

**C. Not special-casing it in this helper is correct**, but not for the author's reason. The reason is that the helper is not on that path. A follow-up that wants these routes in inventory has to accept an optional minus in the regex (and then decide whether to treat the value as signed or as the original `u32`). That is a different patch, and it *would* be a behaviour change (rows that currently vanish would appear, and would then win a signed `<` comparison). Do not fold it in here.

### 5. `if !NT` guard

Required, not just copied. `libenv/Makefile.am` adds `unix_iface.c` only under `if !NT`. The file is also wrapped in `#ifndef __MINGW32__`. The test `#include`s that `.c`. On MinGW the translation unit would not contain `FindLowestMetricDefaultRoute`. `nfs_test` is a cousin, not the reason. I did not run a MinGW build; the source-level dependency is enough. Enterprise supplies the Windows `GetNetworkingInfo` (comment in `sysinfo.c`). Community NT without that stub is a pre-existing link problem, not this test's.

### 6. No Linux end-to-end test

The framing "I cannot run Linux so I cannot ship an e2e test" skips the test that already exists. `tests/acceptance/00_basics/environment/proc-net.cf` is a `CFENGINE_TEST_OVERRIDE_PROCDIR` fixture test. It does not need a live routing table. It *does* skip on `!linux`, so the author could not have run it on this Mac. Adding a second default row with a *higher* metric listed first, and updating `proc-net.cf.sub.expected.json`, would have crossed regex + post-process + selection on Linux CI without anyone touching a real FIB.

Declining to ship an acceptance change they could not run is consistent with this series' "do not claim an unmeasured result" rule. I would not block the offer for it. I would put the fixture extension on the fork issue as the natural follow-up, and I would not describe the current unit tests as covering the parse.

### 7. Full suite not rerun after the final restore

Accepted. Current `unix_iface.c` is the stated sha256. I reran only `unix_iface_test` (7/7, rc 0) against that file. I did not rerun the other 68. A restore that is byte-identical to a state in which the suite passed is a hash argument, not a suite argument. Record it as such; do not inflate it.

### 8. LDADD breadth

`libenv.la` is very likely redundant as a *source* of `unix_iface.o` (the test already defines those symbols via the `#include`) and useful only if some other `libenv` object is pulled to satisfy `libpromises`. Traditional archive linking will not pull `unix_iface.o` from the `.a` if nothing remaining is undefined, so Apple ld and GNU ld should both be fine. I linked and ran on Apple ld only. Copying `sysinfo_test`'s LDADD is the conservative house style. Not a defect. A later cleanup that drops `libenv.la` should be its own measurement on GNU ld, not a rider here.

---

## Adjacent issues the author deliberately did not fix

| Deferred item | Correctly deferred? | Why |
|---|---|---|
| Regex classes (`metric`/`irtt` as `[[:xdigit:]]+`, `refcnt`/`use`/`mtu`/`window` as `\d+`) | **Yes.** | Two behaviour changes in one commit would be the finding. `irtt` is `%u` in the kernel; `metric` is `%d`. Tightening `metric` to `\d+` would still reject the signed high-`u32` case. A real fix is "optional minus + decimal" or "parse as `u32`", not a class tweak. |
| TODO at `unix_iface.c:1061` ("check that the metric and the others are decimal; ipv6_route uses hex") | **Yes as a code change; no as a comment.** | The TODO is now answerable from kernel source: IPv4 metric is decimal, IPv6 metric is hex and already parsed with `hex_mode=true`. Leaving a now-answered TODO next to a function this patch documents is slightly sloppy. Deleting or rewriting that one comment is not a second behaviour change and would have made the "no second defect" conclusion visible in tree. I would not hold the offer for it. |
| `long` → `int` narrowing in `JsonExtractParsedNumber` | **Yes.** | Pre-existing, global to `/proc` numbers, not on a line this patch must edit. Kernel `%d` output does not hit it. |
| `JsonExtractParsedNumber()` returning 0 on `sscanf` failure while leaving the raw string | **Yes.** | The helper already requires `JSON_PRIMITIVE_TYPE_INTEGER`, so a leftover string is skipped, not treated as metric 0. That is the correct interaction. Changing the extractor would affect every `/proc` field. |

The patch is coherent. It extracts a loop, adds the missing assignment, and tests that assignment. It does not silently step over a bug in a line it rewrote — the regex and the extractor were not rewritten.

---

## Recommendation for the fork issue

Offer `3d10206ee` as a fix for CFE-4723. Record on the issue, in the author's voice or the commissioning session's:

1. Independent review agrees the assignment is the defect and the test fails without it.
2. Independent review disagrees that a later huge/`%d`-negative metric is a *new* post-fix behaviour, and notes that the capture regex drops those lines before selection.
3. Production `/proc/net/route` almost certainly already lists same-prefix defaults in increasing-metric order, so most dual-default hosts will not change what they report.
4. Follow-up, not this PR: a `proc-net.cf` fixture with two active defaults, lowest metric last; optional comment refresh of the line-1061 TODO; optional later regex work for signed high `u32` metrics.

No code change required before the offer.
