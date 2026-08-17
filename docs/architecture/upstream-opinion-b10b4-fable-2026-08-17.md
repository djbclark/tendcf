# Independent adversarial review — B-4 + B-10 stacked (libntech JSON numbers)

Reviewer slug: `fable` (Claude Fable 5, xhigh). Date: 2026-08-17.
Role: independent adversarial gate before an upstream issue/PR to
`NorthernTechHQ/libntech` and a report to `security@northern.tech`.

Method note: I preferred measurement to memory throughout. Every before/after
claim below is backed by a run I did in this session, and I say where a claim
is reasoned rather than run. I did **not** read any other `upstream-opinion-*`
file, `docs/handoffs/`, or the `b10-number-render-measurement` working record.

---

## 1. Verdict — **SHIP WITH CHANGES**

The code is correct and the headline severity claim is real; I could not break
it. What holds it back from "ship as is" is packaging and coverage, not
correctness:

1. **Add the `Ticket:` and `Changelog:` trailers** once the upstream issue
   exists. core's `CONTRIBUTING.md` (the file libntech's own `CONTRIBUTING.md`
   defers to) requires both (lines 149–150, 177–178, 225–227). All six commits
   currently omit them. The brief says this omission is deliberate until an
   issue number exists — fine, but it is a hard pre-merge requirement, not
   optional, and a maintainer will bounce the PR without it.
2. **Resolve the `Co-Authored-By: Claude Opus 5` trailers.** They appear on
   four of six commits (`7034791`, `5da4c57`, `8aac759`, `cc4a0d9`) and are
   absent on the two earliest (`fe1ace9`, `bf57367`). core's CONTRIBUTING
   "Use of AI/LLMs" section (line 66) states the human using the AI is
   considered the author. Make them consistent — I would drop them for
   upstream, since Northern.tech's own policy treats AI as a tool and the human
   as author, but at minimum they must not be present on some commits and
   missing on others.
3. **libntech has no test for the mustache change.** Nothing under
   `tests/unit` references `MustacheRender()` (confirmed by grep), yet
   `bf57367` and `fe1ace9` both edit `libutils/mustache.c`. That code path is
   shipping untested in this repo. Adding a spec-driven mustache case (the
   brief's proposal to extend `cfengine/core`'s `tests/unit/mustache_test.c` +
   `data/mustache_extra.json`) is the right move; see Q8.
4. **Disclose the reals-formatting change in the PR body.** B-4 changes how
   *every* real renders, not just the broken ones (`0.5` → `0.5` instead of
   `0.50`; `3.14159` → `3.14159` instead of `3.14`). It is the correct change,
   but it is a visible behaviour change for working policies and the most
   likely thing a maintainer will question. Say so up front. (Details in Q3.)

Optional/minor: `8aac759` bundles two logically distinct source fixes
(`JsonPrimitiveCopy` **and** `JsonSelect`) under a message that mentions only
the copy, and defers the `JsonSelect` test to a separate later commit
(`cc4a0d9`). Consider splitting so each fix ships with its own test. Not
blocking.

None of these are correctness problems. The fix itself I would take as-is.

---

## 2. Severity verdict — **`security@` is the right first channel, at MEDIUM (availability / DoS). Not a memory-safety or code-execution issue.**

**The load-time claim is TRUE. I reproduced it, and I reproduced it three
different ways, having first caught the trap that would have made me report the
wrong stack.**

The minimal policy from the brief — a bundle that *declares*
`d data => readjson(...)` and does nothing else (`reports: "loaded"` never
references `d`) — kills stock `cf-promises` when `numbers.json` contains
`9223372036854775808`:

```
$ /opt/homebrew/bin/cf-promises -f promises.cf      # CFEngine Core 3.27.1
   error: Conversion error (34 - Overflow) on '9223372036854775808' (StringToLongExitOnError)
   EXIT=1
```

with the identical policy + a small integer exiting 0. `cf-promises` failing is
what sends `cf-agent` to failsafe, so this is loss of configuration
enforcement, triggered by a value that merely sits in a stored variable — no
iteration, no mustache, nothing that renders it.

**The trap I had to control for first.** `StringToLongExitOnError` is called
*benignly* during startup: even the control run (value `42`) hits it twice via
`GetSysVars`/`DetectEnvironment` → `JsonCopy` while deep-copying legitimate
`sys.*` container values. An unconditioned `lldb` breakpoint stops on that
benign call and prints a misleading `GetSysVars` stack. Conditioning the
breakpoint on the value (`strcmp($x0,"9223372036854775808")==0`, exactly as the
brief warns) gives the real fatal frame:

```
StringToLongExitOnError
JsonCopy + 316               <- JsonPrimitiveCopy, inlined
JsonObjectCopy
RvalNewRewriter
VerifyVarPromise
ExpandPromise
BundleResolvePromiseType
PolicyResolve
LoadPolicyFile / LoadPolicy
main
```

That is unambiguously **policy-load time**, inside `LoadPolicy`, and matches
the brief's primary trace. The fatal site is `JsonPrimitiveCopy()`
(inlined into `JsonCopy`), reached because storing a JSON container as a
CFEngine variable deep-copies it.

**Second and third independent confirmations, distinct entry paths, same sink:**

- **Augments (`def.json`)** — the most realistic operator/CMDB vector. A policy
  with *no* `readjson` at all, plus a `def.json` of
  `{"vars":{"danger":9223372036854775808}}`, crashes stock `cf-promises`
  identically. Value-conditioned stack:
  ```
  StringToLongExitOnError <- JsonCopy <- JsonExpandElement
    <- LoadAugmentsFiles <- LoadAugments <- GenericAgentDiscoverContext <- main
  ```
  This fires during agent context discovery, *before policy is parsed*.
- **`cfengine/core`'s own build** (`/Users/djbclark/src/core-json`, branch
  `fix/json-number-rendering`) whose `libntech` submodule is at `5b5d04e` —
  which is an **ancestor** of the fix base `0c0620d` and is **unpatched**
  (grep confirms stock `JsonPrimitiveCopy`) — also crashes on the same
  sentinel. This is the proof that **core's half does not fix the load-time
  crash**: `6a4216dad` touches only `rlist.c`/`iteration.c`, never
  `JsonPrimitiveCopy`, so a core built on stock libntech still dies at load.

**Is `security@` correct, or is this an ordinary bug?** My call: notify
`security@`, rated **medium — availability/denial of policy evaluation**, and
say plainly what it is *not*. It is a clean `exit(1)` via `DoCleanupAndExit`;
there is no memory corruption, no RCE, no info leak, no privilege change. What
earns the security channel is the **trust boundary the input crosses** combined
with **blast radius**: a single bad number written into shared CMDB /
`host_specific.json` / augments data drops *every* host that consumes it to
failsafe on its next run — a fleet-wide, data-driven loss of configuration
management from one write.

**Who realistically controls the input?** CMDB / `host_specific.json` /
`readjson()` input is controlled by: a Mission Portal / CMDB operator; whatever
feeds inventory or third-party data into those files; and the policy author.
The honest strongest counter-argument to a security rating is that all of these
are *already privileged* over the host's configuration — if your CMDB is
written only by trusted operators, this is "just" a robustness bug and the
normal bug tracker is enough. It becomes a security issue precisely when
CMDB/host_specific/augments data aggregates from a *less*-trusted source
(inventory scanners, third-party feeds, multi-tenant Mission Portal, a
`readjson()` of a vendor file) — which is common enough that I would not want
Northern.tech to hear about it first from an outsider.

**Your threat wording** —
> *"attacker-controlled" is overstated for a remote exploit; it is honest for a
> CMDB operator, a `readjson()` of third-party JSON, or an author who writes
> scientific notation by mistake.*

is **honest and I would ship it verbatim.** It correctly disclaims the remote
angle and correctly names the three realistic triggers. I would add only one
word of framing when you send it: this is availability/DoS, not memory safety.

---

## 3. Topology verdict — **STACKED is correct (B-4 under B-10). Combined would also be defensible; B-10-alone-with-`inf`-disclosed is NOT acceptable.**

I confirmed the coupling by measurement rather than argument. The patched tip
renders every value correctly through `MustacheRender()`
(`1e400`→`1e400`, `0.00049`→`0.00049`, `1.5e3`→`1.5e3`,
`9223372036854775808`→exact, `0.5`→`0.5`). The B-4-absent REAL render path
(`StringFromDouble(JsonPrimitiveGetAsReal(...))`, i.e. what B-10-alone would
still use) produces exactly:

| value  | B-10 alone (measured) | B-10 + B-4 (measured) |
|--------|-----------------------|-----------------------|
| 0.00049| `0.00`                | `0.00049`             |
| 1.5e3  | `1500.00`             | `1.5e3`               |
| 1e400  | `inf`                 | `1e400`               |
| 0.5    | `0.50`                | `0.5`                 |

This matches the brief's table. The mechanism is confirmed: B-10's exponent
reclassification (`bf57367`) routes `1e-8`/`1e400`/`2e0` onto the REAL render
path; without B-4 that path is still `"%.2f"`, which prints `inf` for a
magnitude that overflows `double`. So **B-10 alone *introduces* `inf`** (stock
crashed on these instead), and **B-4 removes it**. They are genuinely not
independently landable on the real axis — the brief's overturned conclusion is
right, and `inf` is a defect being shipped, not a curiosity to disclose.

Stacked vs combined: `cfengine/core`'s half fixes integers and reals together
in one commit (`6a4216dad`), so a single combined libntech commit would be
consistent with the sibling repo and arguably cleaner. I still favour the
two-commit stack because B-4 and B-10 have genuinely different blast radii and
rationales (a data-corruption fix vs a crash fix), and a bisect that lands on
one is more informative. Either is fine; **B-10 alone is not.**

---

## 4. Defects found

All "verified" items I ran in this session. Reproductions use the built trees
named in the brief.

### VERIFIED — the fix is correct and the stock defects are real

**D1. `JsonPrimitiveCopy()` was fatal / corrupting on copy.**
`libutils/json.c`, stock `JSON_PRIMITIVE_TYPE_INTEGER` case called
`JsonIntegerCreate(JsonPrimitiveGetAsInteger(...))`; REAL called
`JsonRealCreate(JsonPrimitiveGetAsReal(...))`. Fixed at lines 250–260 (both now
`JsonElementCreatePrimitive(type, xstrdup(value))`).
*Reproduced* with a hybrid archive built from the patched `libutils.a` with
only `json.o` reverted to `0c0620d` (isolating exactly the json.c change), run
against an identical harness that mirrors `cf-promises` (`JsonParse` an object,
`JsonCopy` it):

- stock `json.o`: exits 1 on `StringToLongExitOnError` at `9223372036854775808`.
- patched `json.o`: preserves all seven test values, exit 0.

The *silent* corruption below `LONG_MAX` is the underappreciated half — it
happens at **variable storage**, before any render:

| input (on copy)        | stock json.o | patched json.o |
|------------------------|--------------|----------------|
| `2000000000000`        | `-1454759936`| `2000000000000`|
| `9223372036854775807`  | `-1`         | exact          |
| `2147483648`           | `-2147483648`| exact          |
| `0.00049`              | `0.0005`     | `0.00049`      |
| `0.5`                  | `0.5000`     | `0.5`          |
| `3.14159265`           | `3.1416`     | `3.14159265`   |

So a policy that merely *stores* `d[c] = 2000000000000` already holds
`-1454759936` on stock, with no render anywhere. Integers `> LONG_MAX` crash;
integers `> INT_MAX` corrupt (int narrowing in `JsonIntegerCreate`); reals lose
precision past 4 decimals (`JsonRealCreate`'s `"%.4f"`).

**D2. Exponent-without-dot misclassified INTEGER.** `libutils/json.c:2402`
(`JsonParseAsNumber`) branched on `seen_dot` alone; fixed to
`seen_dot || seen_exponent`. Stock stored `1e-8`, `1E5`, `2e0` as INTEGER
holding a lexeme `strtol()` cannot read, so any later conversion hit
`StringToLongExitOnError`. Verified via the parse/copy harness (stock crashes on
`1e-8`/`1e400`; patched preserves).

**D3. Integers past `LONG_MAX` fatal on render.** `JsonPrimitiveToString()`
(`libutils/json.c:822`) and `RenderVariablePrimitive()` INTEGER case
(`libutils/mustache.c:389`) went through `JsonPrimitiveGetAsInteger` →
`StringToLongExitOnError`. Fixed to emit the parsed lexeme. Verified via
`MustacheRender("{{x}}", {"x":9223372036854775808})` → exact on patched.

**D4. Reals rendered through `"%.2f"` (B-4).** `StringFromDouble`
(`libutils/string_lib.c:922`) is `"%.2f"`. Verified stock vs patched
`JsonPrimitiveToString`:
`0.5`→`0.50`/`0.5`, `2.0`→`2.00`/`2.0`, `3.14159`→`3.14`/`3.14159`,
`0.00049`→`0.00`/`0.00049`. Wrong values, and disagreed with
`JsonWriteCompact()` (which always emitted the lexeme). Fixed at
`json.c:831–838` and `mustache.c:396–400`.

**D5. `JsonSelect()` fatal on an oversized numeric index.**
`libutils/json.c:962–982` — stock used `StringToLongExitOnError(index)`. Fixed
to `StringToLong` with a `NULL` return on failure. Note the *source* fix lives
in `8aac759` (not `cc4a0d9`, which only adds its test). Safe because
`StringIsNumeric()` guards to digits-only, so `i >= 0` whenever `StringToLong`
succeeds and the `(size_t)i` cast cannot wrap; empty/oversized/overflowing
indices now return `NULL` instead of exiting.

**Product-level, three entry paths, one sink** (all `→ JsonCopy →
JsonPrimitiveCopy → StringToLongExitOnError`):
`LoadPolicy`/`VerifyVarPromise` (readjson user var);
`GenericAgentDiscoverContext`/`LoadAugments` (augments def.json);
`DetectEnvironment`/`GetSysVars` (sys.* — benign for valid values, same code).
The single chokepoint is why fixing `JsonPrimitiveCopy` in libntech is the
correct and sufficient repair for the load-time crash.

### SUSPECTED / low-risk (not blocking)

**S1. `JsonPrimitiveToString` may now emit exponent notation.** For a REAL
lexeme like `1e-8`/`1e400`, ToString now returns the exponent form where stock
always returned plain `"%.2f"` decimal. Any consumer that fed ToString output
into a parser assuming "no exponent, ≤2 decimals" would see new input. I found
no such consumer in libntech or core, and any exponent value already crashed on
stock, so this is theoretical — but it is the kind of thing a maintainer may
ask about. Reasoned, not run.

**S2. `unix_iface.c` route-metric still gates on
`== JSON_PRIMITIVE_TYPE_INTEGER`** (core `libenv/unix_iface.c:1438`). If a
route metric ever arrived as exponent notation it would now classify REAL and
be skipped. Route metrics are built internally as integers from the OS, never
parsed from exponent text, so no live impact. Reasoned, not run.

---

## 5. The eight questions

**Q1 — Is the load-time severity claim right? Channel? Who controls the input?
Is the threat wording honest?**
Yes, verified three ways (§2). `security@` first, rated medium
availability/DoS, explicitly not memory-safety/RCE. Input controllers: CMDB /
Mission Portal operators, whatever feeds inventory/third-party JSON into
`host_specific.json`/augments, `readjson()` of vendor files, and policy
authors. The quoted threat wording is honest and shippable verbatim; the only
honest caveat to add is the availability-not-memory-safety framing, and the
fact that it is a real security issue *specifically* when those data files
aggregate less-trusted input. The augments/`def.json` path is the strongest
concrete demonstration and worth citing to `security@` — it needs no user
policy at all.

**Q2 — Stacking vs combined vs B-10 alone?**
Stacked is correct; combined is acceptable and matches core's single-commit
half; B-10 alone is not — it ships `inf` (measured, §3). See topology verdict.

**Q3 — Is B-4 correct at all (unreviewed)?**
Yes. It replaces a lossy `"%.2f"` truncation with the parsed lexeme, which is
what `JsonWriteCompact()` already emitted and what `JsonRealCreate()` stores at
`"%.4f"` — so it makes the library agree with itself. The one thing to flag
loudly: it changes rendered output for **every** real, not only broken ones.
Measured: `0.5`→`0.5` (was `0.50`), `2.0`→`2.0` (was `2.00`),
`3.14159`→`3.14159` (was `3.14`). Values authored with trailing zeros
(`1.50`, `100.00`) are preserved because the *lexeme* carried them. This is
correct (truncating `0.00049` to `0.00` is data corruption, not rounding) but
it is a compatibility surface: golden-file tests and downstream consumers that
expected 2-decimal normalisation will see differences. Disclose it in the PR.

**Q4 — Is returning the raw lexeme safe for every producer of a primitive?**
Yes. `JsonElementCreatePrimitive` is `static`, so only libntech's `json.c`
creates INTEGER/REAL primitives, and there are exactly four producers, each
storing a safe string:
(1) `JsonParseAsNumber` — a lexeme validated char-by-char to `[-+0-9.eE]`;
(2) `JsonIntegerCreate` (`"%d"`); (3) `JsonIntegerCreate64` (`"%" PRIi64`);
(4) `JsonRealCreate` (`"%.4f"`, with NaN/Inf mapped to `0.0`).
Critically, the **YAML** path also routes numeric scalars through the same
`JsonParseAsNumber` (`libutils/json-yaml.c:115`), so it inherits the same
validated lexeme — there is no second, looser number producer. A numeric lexeme
contains no HTML-significant character, so emitting it verbatim through mustache
(numbers bypass `RenderHTMLContent`) cannot inject markup; STRING primitives are
unchanged and still HTML-escaped in escaped mode. Nothing stores
attacker-controlled free text as an INTEGER/REAL. Safe.

**Q5 — Is the `JsonPrimitiveCopy()` change complete and correct (ownership,
lifetime, type)?**
Complete and correct. The new INTEGER/REAL arm `xstrdup`s the source value into
a fresh heap string owned by the new element; `JsonDestroy` frees
INTEGER/REAL/STRING values and skips BOOL/NULL (static), so the heap string is
released exactly once — no leak, no double-free (the source is `const` and
untouched). Type is preserved by passing `type` through. `JsonPrimitiveToString`
keeps its existing contract (caller frees; old and new both return heap). The
mustache change removes an alloc+free per number (it appends the borrowed
string into the buffer) — a small improvement, no ownership change. `JsonSelect`
returns a borrowed child or `NULL`, unchanged ownership. The differential
harness ran clean.

**Q6 — Is reclassifying exponents as REAL a compatibility break? What branches
INTEGER vs REAL? `datatype()` now says `"real"` for `2e0`.**
The only externally observable change is `datatype()` reporting the container
subtype as `"real"` instead of `"int"` for exponent-without-dot numbers
(`evalfunction.c:5963–5968`). Every other consumer that branches on the
distinction is unaffected: `rlist.c:1727` and `iteration.c:699` collapse
INTEGER and REAL into the same case; `unix_iface.c:1438` only ever sees
internally-built integers (S2). And the change is strictly an improvement: on
stock, `2e0` classified as `"int"` was an unusable, self-inconsistent state —
`datatype()` said int but *any* render/iteration/copy of it crashed. Reporting
`"real"` is both more correct (an exponent is conventionally a float) and
strictly better than the crash it replaces. Not a meaningful break.

**Q7 — What did the fix miss? Census remaining fatal callers in both repos.**
`JsonPrimitiveGetAsInteger` is indeed still fatal by construction
(`json.c:866` → `StringToLongExitOnError`); that is acceptable as long as no
path reachable from parsed data calls it. Census (excluding the libntech
submodule and test files):

- **libntech**: the only in-tree caller was `JsonPrimitiveCopy`, now removed.
  The public `JsonPrimitiveGetAsInteger` remains for callers who genuinely want
  an integer and accept the exit. No reachable-from-data caller remains.
- **core**: `rlist.c` and `iteration.c` fixed by `6a4216dad` (correct —
  `RlistAppendScalar` copies, so the intermediate alloc is gone;
  `SeqAppend` takes ownership, so `xstrdup` is kept). **Two more that the
  brief's "only twins" phrasing understates** were fixed by `367c27fc5`:
  `generic_agent.c:2051` (`ReadTimestampFromPolicyValidatedFile`) and
  `unix_iface.c:1438` (route metric) — both now use non-fatal `StringToLong`
  with safe fallbacks (0 = "not validated"; unreadable metric doesn't win).
  Both fixes are correct. So core's real total is four data-reachable sites
  fixed across `6a4216dad` + `367c27fc5`, not two.
- **Remaining `StringToLongExitOnError` callers in core are out of scope**:
  `cf-runagent.c` (`-b`, `-t`), `cf-key.c` (`-T`), `cf-serverd-functions.c`
  (`GRACEFUL`) all parse `optarg` — operator-typed CLI, not parsed JSON, where
  exiting on a bad integer is acceptable. `JsonPrimitiveGetAsInt64ExitOnError`
  and `StringToInt64ExitOnError` have no core callers on JSON data. The only
  residual `JsonPrimitiveGetAsInteger` uses are `policy_test.c` (trusted small
  `"line"` numbers in a test). The brief's belief is essentially right; the one
  correction is that it is four fixed sites, not two.

**Q8 — Are the regression tests any good? Would each fail against unfixed code?
The mustache gap.**
The tests are good and each fails against unfixed code, but by two different
mechanisms — worth understanding:
- `test_real_renders_as_parsed`, `test_primitive_to_string_numbers`,
  `test_parse_exponent_numbers` fail as **clean assertion failures** on stock
  (`0.00049 != 0.00`; type INTEGER != REAL — the exponent test deliberately
  checks classification *before* rendering so it asserts rather than crashes).
- `test_copy_preserves_numbers` and `test_select_oversized_array_index`
  **fail by crashing the test binary** on stock (the operation under test is
  the fatal one). That is a valid regression signal but crude — it aborts the
  process, so they can't all run to completion on stock at once. Inherent to
  testing a fatal-exit bug; acceptable.
I verified the tip is green: `json_test` 74/74, full `make check` 39/39
binaries PASS. (The alarming "Result: 409 out of 9092 tests failed" in the log
is `libcompat`'s printf thousands-separator self-test — a known, non-fatal
macOS diagnostic that prints "WARNING your system's printf() generates
different results"; it does not count toward the suite, which exits 0. So the
"harness masks failures" worry is unfounded from the other direction too: this
isn't masked, it's a deliberately informational check.)
Dependency ordering is clean — no test precedes its fix: `5da4c57`'s tests only
exercise `bf57367`/`fe1ace9` (render/classify, no copy); `8aac759` bundles the
copy fix with its test; `cc4a0d9`'s test covers the `JsonSelect` fix that
already landed in `8aac759`.
**The real gap: libntech ships a mustache change with zero mustache tests** —
confirmed nothing under `tests/unit` references `MustacheRender()`. I exercised
it myself (harness: patched `MustacheRender` renders `1e400`, `0.00049`,
`1.5e3`, and `LONG_MAX+1` correctly), but that coverage isn't in the repo.
Proposing to extend core's spec-driven `mustache_test.c` +
`data/mustache_extra.json` is the right move; ideally also drop a minimal
`MustacheRender` case into libntech's own `tests/unit` so the file it edits
isn't untested in the repo that owns it.

---

## How I controlled for the four build traps

- **Trap 1 (`make check` doesn't rebuild `../libutils`):** I ran top-level
  `make -j4` first; `libutils/.libs/libutils.a` timestamp is 07:13 (after the
  build), and only then ran tests.
- **Trap 2 (`make -C tests/unit` doesn't relink):** `rm -f json_test` before
  `make json_test`; confirmed the relink.
- **Trap 3 (`git stash push` of a committed file is a no-op):** I never
  stashed. Stock sources came from `git show 0c0620d:libutils/json.c`.
- **Trap 4 (binaries link the installed dylib; `DYLD_*` stripped across
  `cf-agent`→`cf-promises` exec):** I sidestepped the dylib entirely for the
  differential — my harnesses **statically** link `libutils.a` (`otool -L`
  shows no libntech/libpromises dylib, only pcre2/openssl/yaml). Product-level
  stock crashes used the self-contained Homebrew binary and core's libtool
  wrapper (not `.libs/` directly). `lldb` ran the Homebrew binary directly.
- **The extra trap the brief flagged — the benign `StringToLongExitOnError` in
  `GetSysVars`:** caught it (the control run hits it twice), and used a
  value-conditioned breakpoint for the real stack (§2). This is the single most
  important control in the whole review; an inferred breakpoint would have
  reported the wrong entry path.
- (core's `rlist_test` XFAIL-aborts-at-sixth-test hazard did not affect me — I
  read the `rlist.c`/`iteration.c` source fixes directly rather than relying on
  that test binary.)

---

## 6. What I did not check

- **I did not rebuild and run each of the six commits in isolation.** I
  established per-commit greenness by dependency analysis (no test precedes its
  fix) plus confirming `bf57367`'s reclassification breaks no pre-existing
  stock test (stock `test_parse_good_numbers` asserts only parseability of
  `[1203e10]` etc., never their INTEGER/REAL type) and `fe1ace9` breaks no
  pre-existing ToString assertion (the `JsonRealCreate` and `0.0000` tests
  assert type/write, not ToString). I did not physically `git checkout` each
  commit and run `make check` six times.
- **I did not build a `cf-promises` linked against the *patched* libntech.** The
  available core tree links the stock submodule (`5b5d04e`). I verified the fix
  at the library level instead — via the patched unit suite and via the
  isolated hybrid-archive harness that reverts only `json.o` — which exercises
  the exact `JsonCopy`→`JsonPrimitiveCopy` path the product crash uses. The
  product-level *fix* (a patched `cf-promises` loading the policy cleanly) is
  therefore inferred from an identical mechanism, not run end-to-end.
- **I did not run a memory-leak detector** (`leaks`/ASan). Ownership is
  argued from code in Q5 and the harness ran without crash; I did not
  instrument allocations.
- **Census scope was libntech (`fix/json-number-fatal-exit`) and core
  (`fix/json-number-rendering`) only.** Other CFEngine consumers of
  `JsonPrimitiveGetAsInteger` / mustache (masterfiles modules, enterprise
  components, out-of-tree policy) were not in scope and not searched.
- **I did not exercise the CMDB / Mission Portal path itself**, only the
  augments `def.json` and `readjson` surfaces that stand in for it; the crash
  mechanism is identical (same `JsonCopy` sink), but I did not run a real CMDB.
- **Per the routing note in my instructions:** nothing in this task was declined
  — it is a robustness/availability defect with no offensive-security or
  exploit-development dimension, so I completed all of it.
