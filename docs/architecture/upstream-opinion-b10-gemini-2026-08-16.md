# Upstream Opinion: B-10 libntech JSON number handling

## 1. Verdict
**Ship as is** (for the `libntech` patch). The fix correctly repairs the rendering, copying, and serializing crashes in the library without introducing memory leaks. However, the twin bugs in `cfengine-core` need their own fixes.

## 2. Severity verdict
**security@**
A crash in `cf-promises` forces `cf-agent` to fall back to failsafe, disabling policy enforcement. Since external data sources, CMDB facts, and inputs to `readjson()` can be populated by unprivileged users or third-party systems, an attacker can feed a large integer or exponent number to cause a persistent denial of service. "Attacker-controlled" is an accurate assessment.

## 3. Defects found
* **Verified**: `cfengine-core/libpromises/generic_agent.c:2051` calls `JsonPrimitiveGetAsInteger(timestamp)`. If the `timestamp` field in the policy validated file exceeds `LONG_MAX`, the agent process unconditionally terminates.
* **Verified**: `cfengine-core/libpromises/rlist.c:1729` and `cfengine-core/libpromises/iteration.c:701` unconditionally call `JsonPrimitiveGetAsInteger(primitive)`, meaning your suspicion about them being vulnerable twins is correct.

## 4. The seven questions
1. **Is the severity right?** Yes. A persistent crash resulting in a fallback to "failsafe" mode means CFEngine stops applying policies. The threat model includes unauthenticated or low-privilege inputs (like facts or external JSON), making it a legitimate availability vulnerability.
2. **Is classifying exponent numbers as REAL correct?** Yes. Consumers such as `mustache.c`, `rlist.c`, and `iteration.c` branch on `JSON_PRIMITIVE_TYPE_REAL` and safely process them using `StringFromDouble(JsonPrimitiveGetAsReal())`. This avoids the crash, and formatting `2e0` via double conversion is compatible with existing real number handling.
3. **Is returning the raw lexeme safe?** Yes. The parser validates the input as a valid JSON numeric string before storing it. All other primitive constructors (e.g., `JsonIntegerCreate`, `JsonRealCreate`) build safe, well-formed numeric strings using `snprintf` or `xasprintf`, making them completely safe for verbatim emission.
4. **Is the `JsonPrimitiveCopy()` change complete and correct?** Yes. `JsonElementCreatePrimitive` takes a string pointer but does not copy it, so passing `xstrdup()` correctly passes ownership. `JsonDestroy` reliably frees primitive values (except `NULL` and `BOOL`). This prevents both memory leaks and double frees, whilst successfully preserving exact type and text.
5. **Is rendering `1e400` as `inf` acceptable?** Yes, it is consistent. Numbers with both a decimal and an exponent (e.g., `1.5e400`) were already parsed as `REAL` before the patch, and they natively formatted as `inf` via `StringFromDouble()`. This change ensures exponent-only numbers are treated the same way.
6. **What did the fix miss?** Your belief about `cfengine/core`'s `libpromises/rlist.c` and `libpromises/iteration.c` is correct; they are vulnerable twins. In addition, `libpromises/generic_agent.c` (line 2051) still uses `JsonPrimitiveGetAsInteger` on the `timestamp` element, missing a critical fix.
7. **Are the regression tests any good?** Yes. `CheckNumberIsReal("1e-8")` checks the type assertion directly, which correctly fails against the unfixed codebase. `CheckIntegerRendersAsParsed` actively crashes the unfixed test binary. The only noticeable gap is a missing test case covering `JsonSelect` with an all-digit array index larger than `LONG_MAX`.

## 5. What you did not check
* I did not build or dynamically test the `cfengine-core` repository.
* I did not review the separate `cfengine-core` branch where the twin bugs were supposedly fixed.
* I did not check whether upstream CFEngine maintains any alternative parser logic that branches outside of `libntech`.
