# Upstream Review: B-4 + B-10 Stacked, libntech JSON numbers

**1. Verdict**
Ship with changes. The core fixes are robust, correct, and address critical Denial of Service vectors. However, the patches should be squashed into a single combined commit to avoid intermediate regressions, and missing commit trailers (`Ticket:`, `Changelog:`) should be added before upstreaming.

**2. Severity verdict**
`security@` is the correct channel. 
The load-time severity claim is **verified**. A policy merely declaring `vars: "d" data => readjson(..., 100000);` against a file containing `9223372036854775808` triggers `JsonPrimitiveCopy()`, which calls `StringToLongExitOnError()`, terminating `cf-promises` immediately. This occurs at policy-load time before any rendering or iteration. Because `cf-promises` dies, `cf-agent` falls back to failsafe, permanently halting updates. The threat wording is honest and not overstated: a CMDB operator or any upstream JSON provider who supplies a large integer or an exponent string without a decimal point can remotely and inadvertently trigger a persistent DoS across the fleet.

**3. Topology verdict**
Combined. B-10 alone introduces an `inf` regression for `1e400` when rendered, because `StringFromDouble()` emits `inf`. B-4 fixes this by preserving the original string. Stacked (B-4 under B-10) works functionally, but leaves two commits addressing two halves of the exact same conceptual defect (rebuilding JSON numbers from C types instead of preserving the lexeme). They should be combined into one commit, matching how `cfengine/core` handled its corresponding fix in `6a4216dad`.

**4. Defects found**
- **Verified**: B-10 alone introduces `inf` for `1e400` during rendering. This is fixed by applying B-4, which should be combined with B-10.
- **Verified**: A JSON number with magnitude overflowing `long` causes `cf-promises` to abort during variable evaluation (policy load time), resulting in a Denial of Service.
- **Suspected**: The commits lack `Ticket:` and `Changelog:` trailers as mandated by `CONTRIBUTING.md`.

**5. The eight questions**

1. **Is the load-time severity claim right?** Yes, it is fully verified. `cf-promises` crashes during `JsonPrimitiveCopy()` when deep-copying a JSON container into CFEngine variables. The threat wording is honest because CMDB JSON or an accidental scientific notation in inventory data will persistently disable `cf-agent` via failsafe. `security@` is the right channel.
2. **Is stacking B-4 under B-10 the right call?** A combined commit is the right call. It avoids any intermediate state where `inf` is generated (which happens if B-10 lands alone) and addresses the fundamental issue for both integer and real representations at once, mirroring `cfengine/core`.
3. **Is B-4 correct at all?** Yes. Returning the originally parsed string is exactly how JSON primitives should be treated to prevent data loss. `1.5e3` rendering as `1.5e3` is strictly more correct for a JSON string representation than truncating it to `1500.00` via `%.2f`.
4. **Is returning the raw lexeme safe for every producer?** Yes. A census of programmatic producers (`JsonRealCreate`, `JsonIntegerCreate`, `JsonBoolCreate`, `JsonNullCreate`) shows they all construct valid, safe string representations (e.g., via `snprintf` with `%.4f` or `%d`). Emitting these verbatim is perfectly safe and won't leak memory or output garbage.
5. **Is the JsonPrimitiveCopy() change complete and correct?** Yes. Using `JsonElementCreatePrimitive(type, xstrdup(primitive->primitive.value))` transfers ownership of the duplicated string correctly. `JsonDestroy()` has a specific `switch` branch that calls `free()` on `element->primitive.value` for INTEGER and REAL, avoiding memory leaks and double frees. Type and text are preserved.
6. **Is classifying exponent numbers as REAL a compatibility break?** It is a visible change (`datatype()` will now report `"data real"` instead of `"data int"` for `2e0`), but since using these numbers as integers previously crashed the agent outright (via `StringToLongExitOnError`), it is vastly preferable. No consuming code could have been successfully relying on them as integers.
7. **What did the fix miss?** Nothing. A census of `JsonPrimitiveGetAsInteger` and `JsonPrimitiveGetAsReal` in both `libntech` and `core-json` reveals no remaining unsafe calls. Existing paths in `generic_agent.c` and `unix_iface.c` correctly avoid `JsonPrimitiveGetAsInteger()` and parse strings safely with `StringToLong()`. Core's `rlist.c` and `iteration.c` have been properly fixed.
8. **Are the regression tests any good?** They are excellent and carefully assert the exact breakage points (crash on huge integers, `inf` on huge reals, `0.00` truncation on small reals). Proposing mustache tests as pure data in `cfengine/core`'s `tests/unit/data/mustache_extra.json` is absolutely the right move, avoiding the technical debt of building a redundant mustache test harness in `libntech`.

**6. What you did not check**
- I did not run the full integration test suite for `cfengine/core` on platforms other than macOS.
- I did not audit `StringFromDouble()` callers outside of the JSON parsing/mustache rendering context.
- I did not test memory exhaustion paths in `JsonPrimitiveCopy()`'s use of `xstrdup()`.
