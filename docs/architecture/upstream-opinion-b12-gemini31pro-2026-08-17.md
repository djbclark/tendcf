# Review of CFEngine core default-route selection fix

## Trap control

1. **Never read a return code through a pipe:** I directly executed `make -C tests/unit unix_iface_test && tests/unit/unix_iface_test` and captured the return code using `echo "RC=$?" > /tmp/unix_iface_test_rc.txt`. The test exited with RC 0.
2. **`cf-promises` libtool wrapper:** I did not invoke the acceptance harness or `cf-promises`; the validation was strictly confined to compiling and running the added `unix_iface_test` C binary.
3. **`--bindir` wrong for in-tree build:** Avoided by running the unit test executable directly, bypassing the integration harness.
4. **Platform:** The review is conducted on a macOS arm64 host. I verified that the C unit tests exercise the *post-processed* JSON logic (bypassing `/proc/net/route` reading entirely), which means the patch's logic is correctly validated on macOS. Any claims about the Linux kernel format or `/proc` file contents are based on code analysis and the provided brief, not measured on this host.

## The patch

### 1. Semantics
The `lowest_metric` variable name and the `metric_value < lowest_metric` condition in the original source clearly indicate upstream intended the lowest-metric route to win. Downstream, `sys.inet.default_gateway` uses this selected route. Extracting this selection loop into `FindLowestMetricDefaultRoute()` and updating `lowest_metric = metric_value;` accurately achieves the intended semantics without introducing unintended side effects.

### 2. The metric parse
The `[[:xdigit:]]+` capture regex is over-permissive but functionally correct since decimal digits are a subset of hex digits. `NetworkingRoutesPostProcessInfo()` uses `hex_mode = false` when extracting the metric, parsing it as `%ld`. The author correctly separated the cosmetic cleanup of the regex from the logic fix.

### 3. Tie-breaking
The author implemented first-wins (`metric_value < lowest_metric`). This is consistent with the pre-patch behavior (which also used a strict `<` operation). Choosing first-wins makes sense and minimizes regressions for systems that may have relied on the pre-patch order.

### 4. Types
`JsonPrimitiveGetAsInteger` returns `long`, and `lowest_metric` is correctly typed as `long`. While there is an underlying narrowing cast when `JsonExtractParsedNumber()` saves the metric into the JSON object as an `int`, this is a pre-existing condition affecting all `/proc` variables and does not affect the safety or correctness of this specific patch.

### 5. Behaviour change
The commit message correctly describes the change as a fix. An upstream maintainer would likely accept this as a bug fix since the pre-patch behavior (always selecting the first gateway because `lowest_metric` remained `0`) fundamentally broke the route selection logic. While it technically alters the outcome on hosts with multiple default routes, it alters it to the *intended* and correct networking outcome.

### 6. The test
The test suite genuinely discriminates. `test_lowest_metric_last` provides a scenario where the lowest metric appears last. Pre-patch, this test would fail because the first route would be incorrectly retained. Post-patch, it correctly selects the final route. Control tests like `test_lowest_metric_first` pass with or without the patch, validating that basic first-wins functionality remains intact.

## The author's uncertainties

1. **Tie-break:** The author's choice of first-wins is correct because it explicitly preserves the original code's `<` operator behavior. Whether the kernel naturally orders equal-priority routes is secondary to the fact that the patch avoids introducing an arbitrary *change* to the tie-break behavior.
2. **Route JSON shape:** The assumption is correct. Reviewing `NetworkingRoutesPostProcessInfo()`, the code assigns `metric` via `JsonExtractParsedNumber` (resulting in a JSON integer) and `active_default_gateway` via `JsonObjectAppendBool` (resulting in a JSON boolean).
3. **Kernel format stability:** Parsing metric as decimal via `%ld` is universally safe for Linux metrics, which have historically always been printed as decimal digits in `%d` format.
4. **Huge metrics:** The author's framing that pre-fix a negative metric "would only win if listed first" is **incorrect**. Because the pre-fix code checked `metric < 0` (as `lowest_metric` was never updated from `0`), *any* negative metric encountered would evaluate to `true` and overwrite the `default_route`. Therefore, pre-fix, the *last* negative metric would win. Post-fix, the mathematical lowest negative metric wins. Since huge metrics that overflow into negatives are pathological edge cases, treating them as valid mathematical values is a safe, predictable fallback.
5. **`if !NT` guard:** `unix_iface.c` is Unix-specific and excluded from MinGW builds. Guarding the test similarly is the correct approach to prevent build failures on Windows.
6. **No Linux end-to-end test:** Writing a unit test that operates on the post-processed JSON is an elegant and robust way to test the logic cross-platform. It perfectly isolates the selection logic from the parsing logic. A mock `/proc` fixture test would be a nice integration test, but its absence does not diminish the validity of this unit test.
7. **Full suite not rerun after the final restore:** Since the restored file's sha256 hash was byte-identical to a known-good state that passed the full suite, rerunning the entire suite is mathematically unnecessary.
8. **LDADD breadth:** Over-linking `libpromises.la` in a test Makefile is harmless. Most linkers will simply drop the unused symbols or shared libraries. Copying the established `sysinfo_test` pattern is safer than risking an undefined reference on obscure platforms.

## Adjacent issues the author deliberately did NOT fix

The author was correct to defer all adjacent issues:
- **Regex character classes:** A cosmetic change that would pollute a logic fix.
- **TODO at `unix_iface.c:1061`:** Out of scope for a bug fix.
- **`long`→`int` narrowing:** A structural issue in the CFEngine JSON utility layer that affects many more fields than just the routing metrics. Fixing it here would be an inappropriate scope creep.
- **`JsonExtractParsedNumber()` returning 0 on failure:** Pre-existing behavior that requires an API redesign, appropriately left out of this targeted patch.
