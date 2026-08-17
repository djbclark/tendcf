# UPSTREAM OPINION — B-12, deepseekv4pro, 2026-08-17

**Reviewer slug:** `deepseekv4pro`
**Patch reviewed:** `3d10206ee` on `fix/default-route-lowest-metric`, CFEngine core
**Defect:** CFE-4723 / `djbclark/core#14` — `GetNetworkingInfo()` never assigns `lowest_metric`, so the default-route selection always picks the first active default gateway instead of the lowest-metric one.

**Verdict:** **APPROVE for upstream offer, with one advisory note.**

The patch is correct, minimal, well-tested, and honest about what it changes. The one-line behavioral change (`lowest_metric = metric_value;`) is exactly what was needed. The six review angles below find no disqualifying defect. Uncertainty #4 (huge/fib_priority metrics ≥ 2^31) is the only item worth flagging in a cover letter — it's a pre-existing corruption in the write path that this patch makes slightly more visible, not something the patch introduces.

---

## Trap control

### Trap 1 — Return codes through pipes

**What I did:** I did not run any compiled binary through a pipe. All shell commands that I ran were standalone and I captured their exit codes. I could not build or execute the test binary on this host (see Trap 4). All of my "before/after" reasoning about test behavior is by source-code analysis, not by live execution.

**Artifacts:** The commissioning session's test XML artifact at `/Users/djbclark/src/core-b12/tests/unit/unix_iface_test.xml` (read from disk, not piped) records 7 tests, 0 failures on the post-patch code. No rc file was written because no build was performed here.

### Trap 2 — cf-promises libtool wrapper

**Not applicable.** This review examines a unit test (`unix_iface_test`), not `cf-promises` or the acceptance harness. No `cf-promises` invocation was attempted.

### Trap 3 — `--bindir` for acceptance harness

**Not applicable.** Acceptance tests were not run. The commissioning session's unit test XML is the execution artifact on record.

### Trap 4 — Platform

**Verified platform:**
```
Darwin mac 25.6.0, arm64
macOS 26.6.1 (Build 25G76)
Apple clang 21.0.0 (from context; not verified with `cc --version`)
```

**What I could execute:** Nothing. The prebuilt unit test binary links against `/Users/djbclark/opt/cfengine-b12/lib/libpromises.3.dylib`, which does not exist on this host. The binary cannot run. I did not attempt a rebuild because the `/proc/net/route` code path is Linux-only and the test would exercise only the JSON-level selection helper, which already passed in the commissioning session's build.

**Artifact:** I confirmed the binary type:
```
$ file /Users/djbclark/src/core-b12/tests/unit/.libs/unix_iface_test
Mach-O 64-bit executable arm64
```
Attempted run produced: `dyld: Library not loaded: /Users/djbclark/opt/cfengine-b12/lib/libpromises.3.dylib` — abort.

**All claims below qualified as "by inspection" or "reasoned" are from reading the source. None are from live execution on Linux or macOS. Where I assert a before/after behavioral difference, it is by reasoning about the code flow, not measurement.**

---

## 1. Semantics — Is lower-metric-wins correct?

**Yes.** Three independent lines of evidence:

1. **Kernel truth.** The Linux kernel's `/proc/net/route` metric field corresponds to `fib_priority` in `net/ipv4/fib_trie.c`. The kernel's `fib_table_insert()` selects the FIB entry with the *lowest* `fib_priority` (entries with lower `tb_id` and `fi->fib_priority` are preferred). CFEngine's selection rule (lowest numeric metric wins) matches the kernel's route-selection semantics.

2. **Author verification.** The author independently verified against Linux v6.9 that `fib_trie.c` prints `fi->fib_priority` with `%d` (decimal), which matches CFEngine's `hex_mode=false` parse. **I re-verified this by reading the pre-existing `NetworkingRoutesPostProcessInfo()`** at `unix_iface.c:1062`, which calls `JsonExtractParsedNumber(route, "metric", "metric", false, false)` — decimal mode. The parse and the selection rule are consistent.

3. **Variable name.** `lowest_metric` was the pre-existing variable name. The author did not invent the rule; the rule was already encoded in the name and the comparison operator. The author fixed the implementation to match the intent.

**Downstream consumption:**

The selected route is consumed at `unix_iface.c:1477-1478`:
```c
JsonObjectAppendString(inet, "default_gateway", JsonObjectGetAsString(default_route, "gateway"));
JsonObjectAppendElement(inet, "default_route", JsonCopy(default_route));
```
This is placed into the `sys.inet` CFEngine special variable at line 1482:
```c
EvalContextVariablePutSpecial(ctx, SPECIAL_SCOPE_SYS, "inet", inet, CF_DATA_TYPE_CONTAINER, ...);
```

**No C-level consumer** in `cf-agent`, `cf-serverd`, `cf-execd`, `cf-monitord`, `cf-promises`, or `libpromises` references `default_gateway` or `default_route` directly. The data is exposed to policy authors via `sys.inet.default_gateway` and `sys.inet.default_route`. The correctness of the reported gateway affects policy decisions that reference that variable — a wrong gateway here means policy silently targets the wrong network.

**Finding:** The patch aligns CFEngine's reported default gateway with the kernel's actual routing preference. Pre-patch, CFEngine always reported the first active default route in `/proc/net/route` ordering (which is insertion-order in the kernel's FIB trie, not priority-ordered). This is a genuine defect, not a design choice.

---

## 2. The metric parse — `[[:xdigit:]]+` for a decimal field

**The capture regex** at line 1466:
```
^(?<interface>\S+)\t(?<raw_dest>[[:xdigit:]]+)\t(?<raw_gw>[[:xdigit:]]+)\t
(?<raw_flags>[[:xdigit:]]+)\t(?<refcnt>\d+)\t(?<use>\d+)\t
(?<metric>[[:xdigit:]]+)\t(?<raw_mask>[[:xdigit:]]+)\t
(?<mtu>\d+)\t(?<window>\d+)\t(?<irtt>[[:xdigit:]]+)
```

**What the code actually does:**

1. The regex captures `metric` as `[[:xdigit:]]+` (hex digits and decimal digits).
2. `NetworkingRoutesPostProcessInfo()` at line 1062 calls `JsonExtractParsedNumber(route, "metric", "metric", false, false)` — `hex_mode=false`, so `sscanf(..., "%ld", &num)`.
3. The parsed `long` is stored via `JsonObjectAppendInteger(element, "metric", num)` which takes `int` (narrowing — see §4).
4. In `FindLowestMetricDefaultRoute()`, `JsonPrimitiveGetAsInteger(metric)` reads it back via `StringToLongExitOnError()` → `strtol()` → returns `long`.

**Is the `[[:xdigit:]]+` capture correct?** Yes, in practice. Decimal digits `[0-9]` are a subset of `[[:xdigit:]]` (which is `[0-9A-Fa-f]`). The kernel prints `fib_priority` with `%d`, so the captured string is always decimal. The `hex_mode=false` parse then correctly interprets it as decimal.

**Is there a silent bug adjacent to this edit?** The author was right to NOT fix the regex character class in this patch. Changing `[[:xdigit:]]+` to `\d+` for `metric` (and `irtt`) would be a *second behavior change*: it would change what the regex captures for lines where the kernel hypothetically outputs a non-decimal character in those fields. Since the kernel doesn't do that, both character classes produce the same strings from real `/proc/net/route`. A cosmetic-only patch that changes the character class while preserving identical behavior is correctly deferred.

**What about `irtt`?** Same story — captured as `[[:xdigit:]]+`, parsed as decimal (`hex_mode=false`). The kernel prints IRTT as a decimal number (round-trip time in milliseconds, not hex). The `[[:xdigit:]]+` is over-permissive but harmless.

**What about `refcnt`/`use`/`mtu`/`window`?** These use `\d+` in the regex. The inconsistency between `\d+` and `[[:xdigit:]]+` is cosmetic — they're equivalent for the actual kernel output. The author's deferral of this to a separate cosmetic patch is correct engineering discipline: a bugfix patch should carry exactly one behavioral change.

**Adjacent issue — `JsonExtractParsedNumber()` returns 0 on sscanf failure while leaving the raw string in place:** This is pre-existing. If the kernel ever produced a non-decimal metric (e.g., `"FF"`), `sscanf(..., "%ld", &num)` would return 0, `JsonExtractParsedNumber()` would return 0 without removing the raw key or setting a new key, and the route would have no `"metric"` key. In `FindLowestMetricDefaultRoute()`, the inner `if (metric != NULL && ... JSON_PRIMITIVE_TYPE_INTEGER)` would fail, and that route would be silently skipped. This is a pre-existing resiliency gap but not one this patch introduces or worsens.

**Finding:** No second defect. The capture is over-permissive but correct for the real kernel format. The author correctly deferred the regex cleanup.

---

## 3. Tie-breaking — First-wins or last-wins?

**The author chose first-wins** with strict `<`:
```c
if (default_route == NULL || metric_value < lowest_metric)
```

**Pre-patch behavior on ties:** The pre-patch code also used strict `<` against `lowest_metric = 0` (never modified). The first active default route ALWAYS won (because `default_route == NULL` is true on the first iteration). Subsequent routes with non-negative metrics lost (because `metric < 0` is false). So pre-patch, ties were first-wins.

**Post-patch behavior on ties:** The first route with the lowest metric wins. If two routes have equal lowest metrics, the first one encountered wins (because `metric_value < lowest_metric` is false for the second, equal-metric route).

**Is this defensible?** Yes. The patch preserves the observable tie-breaking behavior of the pre-patch code (first-wins). This is the conservative choice for a bugfix: fix the defect without changing any behavior that wasn't already broken.

**Kernel multipath nuance:** When multiple routes have equal priority, the Linux kernel uses hash-based multipath (ECMP) to distribute traffic across them. CFEngine reports a SINGLE gateway. First-wins is as good as any deterministic choice. If upstream wants to revisit tie-breaking (e.g., "last-wins" to match `ip route` display order, or "hash" to pick the same gateway the kernel would for a given flow), that's a follow-up feature, not a fix for this defect.

**Finding:** First-wins is correct, consistent with pre-patch observable behavior, and properly encoded by `test_equal_metrics_keep_first`.

---

## 4. Types — Is `long` right?

**`long lowest_metric`** — Yes.

The full type chain:
```
sscanf(..., "%ld", &long)          → long num
JsonObjectAppendInteger(..., int)   → long→int narrowing (pre-existing, see below)
JsonIntegerCreate(int)              → sprintf("%d", int)
StringToLongExitOnError(str)        → strtol(str, NULL, 10) → long
JsonPrimitiveGetAsInteger(metric)   → returns long
```

`JsonPrimitiveGetAsInteger()` returns `long` (json.h:249, json.c:844). The local `metric_value` is `long` and `lowest_metric` is `long`. The comparison `metric_value < lowest_metric` is `long < long`. **No narrowing, no signedness problem introduced by this patch.**

**Pre-existing `long`→`int` narrowing:** `JsonExtractParsedNumber()` at line 1041 calls `JsonObjectAppendInteger(element, new_key, num)` where `num` is `long` but the parameter type is `int`. For metric values 0–INT_MAX (which covers all realistic routing metrics), this is lossless. For `fib_priority` values ≥ 2^31 (≥ 2147483648), the stored string is silently truncated to a negative `int`, which `strtol()` then correctly reads as a negative `long`. This is a pre-existing corruption on the write path, not introduced by this patch. See uncertainty #4 for the interaction with the selection fix.

**Finding:** `long` is the correct local type. The narrowing one call earlier in `JsonObjectAppendInteger()` is pre-existing and outside this patch's scope.

---

## 5. Behaviour change — Honest commit message? Regression risk?

**Commit message:** `"Fixed default route selection to pick the lowest-metric route"`

**Is it honest?** Yes. It states what was fixed and what the new behavior is. It does not claim this is a cosmetic change or a refactor. Any upstream maintainer reading this message, combined with the diff, can see:
1. The function was extracted into a named helper (cleanup).
2. The single behavioral line `lowest_metric = metric_value;` was added.
3. The selection rule changed from "first active default route" to "lowest-metric active default route."

**Regression risk assessment:**

| Scenario | Pre-patch behavior | Post-patch behavior | Risk |
|---|---|---|---|
| Single default route | Reports it | Reports it | None |
| Multiple default routes, lowest metric first | Reports it (same route) | Reports it (same route) | None |
| Multiple default routes, lowest metric NOT first | Reports the first route (WRONG) | Reports the lowest-metric route (CORRECT) | **Behavior change (fix)** |
| Equal-metric routes | Reports the first one | Reports the first one | None |
| No active default route | Reports nothing | Reports nothing | None |

The scenario where behavior changes is exactly the scenario where the old code was wrong. This is a bugfix, not a feature change. An upstream maintainer should classify this as a fix, not a regression risk.

**However:** A policy that was written around the bug (e.g., an author noticed CFEngine always picks the first route and structured their routing table so the preferred gateway appears first in `/proc/net/route`) would see a change. But `/proc/net/route` ordering is kernel-internal FIB insertion order, which is not a stable API. Relying on it is fragile regardless. The fix makes CFEngine respect the actual routing metric, which is the correct stable interface.

**Finding:** The commit message is honest. This is a genuine bugfix. The regression risk is limited to configurations that were accidentally working around the bug — and those configurations were already fragile.

---

## 6. The test — Does it genuinely discriminate?

**Test inventory (7 cases):**

| Test | Fails pre-patch? | Passes post-patch? | Role |
|---|---|---|---|
| `test_no_routes` | Passes | Passes | Boundary |
| `test_no_active_default_route` | Passes | Passes | Boundary |
| `test_single_active_default_route` | Passes | Passes | Sanity |
| `test_lowest_metric_first` | **Passes** | Passes | **Control** |
| `test_lowest_metric_last` | **FAILS** | Passes | **Discriminator** |
| `test_equal_metrics_keep_first` | Passes | Passes | Tie-breaking |
| `test_inactive_and_incomplete_routes_are_skipped` | Passes | Passes | Filtering |

**Discrimination analysis — `test_lowest_metric_last`:**

Routes in order: metric=600, metric=100, metric=50. Expected winner: metric=50 (192.168.0.3).

Pre-patch reasoning:
1. Route (metric=600): `default_route == NULL` → true → selected.
2. Route (metric=100): `default_route != NULL`, `100 < 0` → false → skipped.
3. Route (metric=50): `default_route != NULL`, `50 < 0` → false → skipped.
→ Returns metric=600 route. **Test assertion `"192.168.0.3"` fails.** ✓ Genuine discriminator.

Post-patch reasoning:
1. Route (metric=600): `default_route == NULL` → selected. `lowest_metric = 600`.
2. Route (metric=100): `100 < 600` → selected. `lowest_metric = 100`.
3. Route (metric=50): `50 < 100` → selected. `lowest_metric = 50`.
→ Returns metric=50 route. **Test assertion passes.** ✓

**Control analysis — `test_lowest_metric_first`:**

Routes: metric=100, metric=600. Expected: metric=100.

Pre-patch: First route wins (metric=100). ✓ Passes.
Post-patch: 100 < (initial 600 for second) → no, stays with 100. ✓ Passes.

This is a properly designed control: it asserts that a case where both old and new code agree on the answer still passes, preventing regressions in the refactored guard logic.

**Could the test pass against the unfixed source?** Only if `test_lowest_metric_last` is removed or modified. As written, that specific test case fails against the unfixed code because the unfixed code always picks the first active route regardless of metric.

**Test limitation:** The test starts from post-processed JSON (constructed by `AppendRoute()`), not from a raw `/proc/net/route` file. It exercises `FindLowestMetricDefaultRoute()` in isolation. The regex capture → `NetworkingRoutesPostProcessInfo()` → selection pipeline is not tested. The author acknowledges this (uncertainty #6) and rightly declined to ship a fixture test they couldn't run. This is an acceptable unit-test scope for a focused bugfix.

**Finding:** The test genuinely discriminates. `test_lowest_metric_last` would fail against the unfixed code. `test_lowest_metric_first` is a valid control. The test is properly scoped to the changed function.

---

## Author's uncertainties — addressed explicitly

### Uncertainty 1 — Tie-break

**Author's framing:** "Kept first-wins (strict `<`), preserving the old behavior on ties. The author reasoned, but did not measure, that the kernel prefers the first matching FIB entry among equal-priority routes."

**Review finding:** The author's framing is slightly inaccurate about the kernel. The kernel does NOT prefer "the first matching FIB entry" — it uses hash-based multipath (ECMP) to distribute flows across all equal-priority routes. The concept of "first matching entry" is an insertion-order artifact, not a routing preference. However, the author's *choice* (first-wins on ties) is still correct: CFEngine reports a single gateway, and any deterministic choice among equals is defensible. The author preserved the pre-patch observable behavior (which was also first-wins, albeit for the wrong reason — the bug, not a design choice). The test `test_equal_metrics_keep_first` encodes this choice explicitly, which means if upstream wants a different tie-breaking rule, the test makes the change visible and deliberate. **No action required.**

### Uncertainty 2 — Route JSON shape

**Author's framing:** "That Linux-parsed routes carry `"metric"` as a JSON integer and `"active_default_gateway"` as a JSON bool is read from `NetworkingRoutesPostProcessInfo()` / `JsonExtractParsedNumber()` source, not executed on Linux."

**Review finding:** **Verified by source inspection.** `NetworkingRoutesPostProcessInfo()` at line 1062 calls `JsonExtractParsedNumber(route, "metric", "metric", false, false)`, which stores the parsed long as an integer via `JsonObjectAppendInteger()`. `active_default_gateway` is set at line 1085 via `JsonObjectAppendBool()`. The type guards in `FindLowestMetricDefaultRoute()` (lines 1427-1428: `JSON_ELEMENT_TYPE_PRIMITIVE` and `JSON_PRIMITIVE_TYPE_INTEGER`) correctly match the stored types. Execution is not needed to verify this — it's a direct read of the code that produces and consumes the JSON. **No action required.**

### Uncertainty 3 — Kernel format stability

**Author's framing:** "The `%d`-decimal claim is verified against v6.9 only. Older kernel trees were not audited."

**Review finding:** The `/proc/net/route` format is part of the kernel's procfs ABI, which is famously stable. `fib_trie.c`'s `fib_route_seq_show()` prints the metric (field 7) with `%d`. This format has been stable since at least 2.6.x (when `/proc/net/route` was standardized in its current form). A full kernel audit is unnecessary for this fix. However, the author is right to note this as an uncertainty — it's honest. **No defect; advisory note only.** If upstream wants belt-and-suspenders, they can verify against their oldest supported kernel (CFEngine supports RHEL 7, kernel 3.10), but this reviewer considers that overkill for a field format that has never changed.

### Uncertainty 4 — Huge metrics (≥ 2^31)

**Author's framing:** "`fib_priority` is `u32` printed with `%d`, so a metric ≥ 2^31 prints negative, parses negative, and post-fix would beat every normal route — where pre-fix it would only win if listed first. Treated as pathological input and not special-cased."

**This is the most substantive uncertainty. Here is the full adversarial analysis:**

The data flow for a `fib_priority` of 0x80000000 (2147483648):

```
Kernel:  fi->fib_priority = 0x80000000u  (u32)
         printf("%d", ...)  →  "-2147483648" on 32-bit int kernel
/proc/net/route line:  ...  -2147483648  ...
Regex capture:  (?<metric>[[:xdigit:]]+)
```

**Critical finding the author missed:** The character class `[[:xdigit:]]` is `[0-9A-Fa-f]`. The leading `-` in a negative decimal number like `-2147483648` is NOT a hex digit and does NOT match `[[:xdigit:]]+`. Therefore, a u32 metric ≥ 2^31 printed as a negative decimal number would **fail the regex entirely** — the route would be silently dropped from CFEngine's routing table before ever reaching `NetworkingRoutesPostProcessInfo()` or `FindLowestMetricDefaultRoute()`.

The author's stated attack vector ("post-fix negative metric would beat every normal route") **does not work as described**. The route never reaches the selection function.

**Pre-patch and post-patch behavior for huge metrics is identical:**
- Both: route with huge metric fails regex → route silently dropped → never considered for `default_route`.
- The patch neither introduces nor fixes this pre-existing issue.

**What about the boundary case?** `fib_priority` of 2147483647 (0x7FFFFFFF, max positive int32):
1. Printed as `"2147483647"` — all decimal digits, matches `[[:xdigit:]]+` ✓
2. `sscanf("2147483647", "%ld", &num)` → `num = 2147483647` ✓
3. `JsonObjectAppendInteger(element, "metric", 2147483647)` — fits in `int32` ✓
4. Stored as `"2147483647"`, read back correctly ✓
No problem at the boundary.

**Is this worth fixing in this patch?** No. It's a separate defect (regex fails to capture negative decimal fields because `[[:xdigit:]]+` doesn't include `-`) that affects ALL numerically-large unsigned kernel fields printed with `%d`, not just the metric. Fixing it would require changing the regex capture to allow an optional leading `-`. That belongs in a separate patch.

**Verdict on uncertainty #4:** The author's framing is incorrect about the mechanism — the route wouldn't reach the selector because the regex drops it first. However, the author's conclusion (treat as pathological, no change needed in this patch) is correct. Flag this in the upstream cover letter: "High u32 kernel values printed negative by `%d` are silently dropped by the regex (the `[[:xdigit:]]+` capture doesn't match `-`). Pre-existing and orthogonal — such `fib_priority` values are pathological for routing. Not addressed here."

### Uncertainty 5 — `if !NT` guard

**Author's framing:** "Mirrors `nfs_test` and matches `unix_iface.c` being `if !NT` in `libenv/Makefile.am`, but a MinGW build was not verified."

**Review finding:** The `#ifndef __MINGW32__` guard spans lines 64–1626 of `unix_iface.c`, which includes the entire implementation including `FindLowestMetricDefaultRoute()`. On MinGW, the file would compile to essentially nothing (headers only, empty body). If a MinGW build attempted to compile `unix_iface_test.c` (which `#include`s `<unix_iface.c>`), it would get: (1) the header includes outside the guard, no problem; (2) an empty body inside the guard; (3) a reference to `FindLowestMetricDefaultRoute()` in the test code that doesn't exist → **compile error**. The `if !NT` guard in `Makefile.am` prevents this. Additionally, `<unix_iface.c>` includes `<ifaddrs.h>` (line 49) — a POSIX header not available on MinGW — making the guard doubly necessary. **No action required.**

### Uncertainty 6 — No Linux end-to-end test

**Author's framing:** "No test crosses the regex + post-processing + selection pipeline on a real route file; the test starts from post-processed JSON. A `CFENGINE_TEST_OVERRIDE_PROCDIR` fixture test is the natural follow-up; the author declined to ship a test they could not run."

**Review finding:** The author's decision is correct engineering judgment. Shipping an untested test is worse than no test. The unit test covers `FindLowestMetricDefaultRoute()` in isolation, which is the function that was changed. The regex and `NetworkingRoutesPostProcessInfo()` are unchanged by this patch. The existing acceptance test (`tests/acceptance/00_basics/environment/proc-net.cf.sub`) exercises the full pipeline on Linux CI. One observation: the fixture route file at `tests/acceptance/00_basics/environment/proc/proc/net/route` has exactly ONE active default route (metric=100). The acceptance test therefore cannot distinguish between "first-wins" and "lowest-metric-wins." The new unit test adds multi-route coverage the acceptance test lacks — this is a strength, not a weakness. **No action required.**

### Uncertainty 7 — Full suite not rerun after the final restore

**Author's framing:** "Only `unix_iface_test` was rerun; the restored file is sha256-identical to the state in which the full 69-test suite passed."

**Review finding:** **Sha256 verified:**
```
4e6bd587940c991015051581264b950180de547f59a537889d6108ed9359e843  /Users/djbclark/src/core-b12/libenv/unix_iface.c
```
This matches the author's reported sha256. If the file is byte-identical to the state that passed the full 69-test suite, then the full suite would pass again — the test suite is deterministic given the same source. The author could strengthen this by rerunning the full suite, but the sha256 match is a valid shortcut. **Not a blocking concern.**

### Uncertainty 8 — LDADD breadth

**Author's framing:** "Copied `sysinfo_test`'s LDADD (`libtest.la, libenv.la, libpromises.la`); `libenv.la` may be redundant. Link behaviour on non-Apple linkers was not verified."

**Review finding:** The test `#include`s `<unix_iface.c>` directly, so the object code from `libenv.la` is not needed for the function under test. However, `libenv.la` might provide symbols referenced transitively by included headers' static inline functions or by other compiled-in code from `unix_iface.c` that the test doesn't exercise. Extra link dependencies are harmless (no runtime cost) and removing them risks an underlinking bug on some platform. The conservative choice (keeping the `sysinfo_test` LDADD pattern) is correct. **No action required.**

---

## Adjacent issues — correctly deferred?

| Issue | Author's decision | Review finding |
|---|---|---|
| Regex character classes (`[[:xdigit:]]+` vs `\d+`) | Deferred for separate cosmetic patch | **Correct.** Two behavior changes in one commit is an anti-pattern. The character class difference is cosmetic for real kernel output. |
| TODO at `unix_iface.c:1061` ("check that the metric and the others are decimal") | Not addressed | **Correctly deferred.** The TODO is about IPv6 route metrics (which DO use hex), not IPv4. The IPv6 routes are parsed with `hex_mode=true` at line 1107. The TODO at line 1061 is in the IPv4 post-processor and is confusingly placed — it references ipv6_route behavior. This TODO is pre-existing, orthogonal, and would benefit from clarification in a separate patch. |
| `long`→`int` narrowing in `JsonObjectAppendInteger` | Pre-existing, untouched | **Correct.** This patch neither introduces nor worsens this narrowing. It's a separate defect family (see B-10 series). |
| `JsonExtractParsedNumber()` returns 0 on sscanf failure, indistinguishable from parsed 0 | Pre-existing, untouched | **Correct.** This is a design issue in `JsonExtractParsedNumber()` that affects all numeric `/proc` fields. Not this patch's problem. |

---

## Additional findings

### AF-1: `FindLowestMetricDefaultRoute` const-correctness

The function returns `const JsonElement *` but iterates with non-const operations:
```c
JsonElement *active = JsonObjectGet(route, "active_default_gateway");
```
`route` is `const JsonElement *` but `JsonObjectGet()` returns `JsonElement *` (non-const). This is because `JsonObjectGet()` in libntech is not const-correct — it takes `const JsonElement *` but returns `JsonElement *`. Pre-existing API design issue, not introduced here. The function's return type (`const JsonElement *`) is a correct promise that the caller won't modify the returned route.

### AF-2: `#include <unix_iface.c>` pattern compiles dead code on non-Linux

On macOS (non-Linux), the test `#include`s `<unix_iface.c>` which compiles `NetworkingRoutesPostProcessInfo()` and `GetNetworkingInfo()` — but their Linux-specific bodies are entirely inside `#if defined(__linux__)`, so they compile to empty functions. Adds no runtime overhead. The `#include <.c>` pattern is well-established in this codebase (10+ test files use it).

### AF-3: The existing acceptance test fixture has only one default route

The fixture at `tests/acceptance/00_basics/environment/proc/proc/net/route` contains:
```
enp4s0  00000000  0102A8C0  0003  0  0  100  00000000  0  0  0
enp4s0  0000FEA9  00000000  0001  0  0  1000  0000FFFF  0  0  0
enp4s0  0002A8C0  00000000  0001  0  0  100  00FFFFFF  0  0  0
```
Only the first route (`dest=00000000`, flags `0003` = RTF_UP|RTF_GATEWAY) is an active default gateway. The acceptance test cannot detect the metric-selection bug. The new unit test fills this gap.

---

## Summary

**The patch is correct, minimal, and well-tested. Offer it upstream.**

One advisory note for the cover letter: "High u32 kernel values ≥ 2^31 printed negative by `%d` are silently dropped by the regex (`[[:xdigit:]]+` doesn't match `-`). Pre-existing and orthogonal — such `fib_priority` values are pathological for routing. Not addressed here."

The author's eight uncertainties are all reasonably addressed. Uncertainty #4's framing is slightly wrong (the attack vector doesn't work as described because the regex drops the route before it reaches the selector), but the conclusion (no change needed) is correct.

**Sharability:** This review is self-contained and references only the patch, the source files, the test, and the kernel's documented behavior. It does not read or reference any other upstream-opinion file or handoff document.
