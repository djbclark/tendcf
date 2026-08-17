# Draft email to security@northern.tech — B-10 + B-4

**Status: NOT SENT.** Drafted 2026-08-17 after the four-member panel closed.
Awaiting operator go. Send via the built-in Claude Gmail connector, not
Composio. New message, not a reply to the exec_timeout thread — different
defect.

**To:** security@northern.tech
**Subject:** A valid JSON number takes CFEngine hosts to failsafe at policy load, and silently corrupts others

---

Hello,

I've found a defect in libntech's JSON number handling that drops CFEngine hosts to failsafe, and a quieter one beside it that changes values without any error. Both are fixed on a branch; details and patches below. Nothing about this is public beyond my own fork.

**What it is not**, first, so you can triage it correctly: this is an availability and integrity problem, not memory safety. There is no corruption, no code execution, no information leak, no privilege change. The crash is a clean `exit(1)` through `DoCleanupAndExit`.

## The crash

`JsonPrimitiveCopy()` in `libutils/json.c` rebuilds every number from a C numeric type instead of keeping the text the parser already stored. For a magnitude no `long` can hold, that reaches `StringToLongExitOnError()`, which exits the process.

Storing a JSON container as a CFEngine variable deep-copies it, so this runs at **policy load**, on every data variable. On stock CFEngine 3.27.1, this policy is enough:

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

with `9223372036854775808` anywhere in `numbers.json`. `reports:` never references `d`. No iteration, no mustache, nothing that renders the value — declaring the variable is sufficient. `cf-promises` exits inside `LoadPolicy`, so `cf-agent` cannot confirm promises and falls back to failsafe. The host stops applying its policy.

```
StringToLongExitOnError          <- "9223372036854775808"
JsonCopy                          (JsonPrimitiveCopy, inlined)
JsonObjectCopy
RvalNewRewriter
VerifyVarPromise
ExpandPromise
BundleResolvePromiseType
PolicyResolve
LoadPolicy
main                              (cf-promises)
```

Two other entry paths reach the same sink with **no user policy at all**:

- **Augments.** A `def.json` of `{"vars":{"danger":9223372036854775808}}` beside the policy dies in `LoadAugmentsFiles` during `GenericAgentDiscoverContext` — before policy is parsed.
- **`host_specific.json` / CMDB.** Same result.

Exponent notation without a decimal point does the same thing for a different reason: the parser classifies REAL vs INTEGER on `seen_dot` alone, so `1e-8`, `1E5` and `2e0` become integer primitives holding a lexeme `strtol()` cannot read. `1e-8` in a CMDB file is a failsafe.

## The quieter one

`JsonIntegerCreate()` takes an `int` while `JsonPrimitiveGetAsInteger()` returns a `long`, so copying silently narrows anything between them — at variable storage, before any render, with no error and no log:

| JSON number | stored |
|---|---|
| `2000000000000` | `-1454759936` |
| `9223372036854775807` | `-1` |
| `1786965915908` (epoch milliseconds) | `259520772` |

Millisecond timestamps have exceeded `INT_MAX` since 2001. A `readjson()` of ordinary telemetry, an API dump or a CMDB export loads, validates, does not failsafe, and quietly uses a different number. I think this is the more likely one to be hit in practice and the harder one to notice.

Reals lose precision the same way (`JsonRealCreate()` formats with `"%.4f"`, so `0.00049` copies as `0.0005`), and rendering truncated them further through `"%.2f"` — `0.00049` reached a rendered configuration file as `0.00`.

## Who controls the input

I want to be accurate rather than dramatic about this. "Attacker-controlled" is overstated for a remote exploit; it is honest for a CMDB operator, a `readjson()` of third-party JSON, or an author who writes scientific notation by mistake.

Everyone who can write these files is already privileged over the host's configuration, so if your CMDB is written only by trusted operators this is a robustness bug and the normal tracker is the right place. It becomes a security matter when that data aggregates from something less trusted — inventory scanners, third-party feeds, vendor JSON, multi-tenant Mission Portal — because one bad value written once drops every host that consumes it. That is why I'm writing here first rather than opening a public issue, and I'm happy to be told this belongs in the ordinary tracker.

## Fix

Branch: https://github.com/djbclark/libntech/tree/fix/json-number-fatal-exit
PR with full write-up: https://github.com/djbclark/libntech/pull/5

Six commits. They render, copy and serialise a number from the text it was parsed from, which is what `JsonWriteCompact()` already did — the bug is that everything else disagreed with it. Each commit builds and passes `tests/unit` on its own; the tip is 39/39 with `json_test` at 75/75.

`cfengine/core` needs a matching change — four call sites there reach the same fatal conversion from parsed data (`rlist.c`, `iteration.c`, `generic_agent.c`, `unix_iface.c`). I have those ready and will offer them separately. Note that core's fixes alone are not sufficient: a `cf-promises` built from them on a stock libntech still dies at load, because `JsonPrimitiveCopy()` is in libntech.

Two things that cost me real time, in case they cost yours:

- `make check` inside `tests/unit` does not rebuild `../libutils`, so a test binary can silently link the previous archive and report a false result.
- `StringToLongExitOnError` is also called benignly during start-up via `GetSysVars`, so an unconditioned debugger breakpoint stops there and prints a misleading stack. It has to be conditioned on the value.

One thing the patches deliberately leave alone: `JsonPrimitiveGetAsInteger()` is still fatal by construction. Nothing reachable from parsed data calls it any more, but it remains a footgun on the public header, and I'd rather flag it than quietly change a public API's behaviour.

Happy to rework any of this to your conventions, or to hold off on the public PR if you'd prefer to handle it privately first — just say which.

Best,
Daniel
