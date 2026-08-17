# Second panel on B-4 + B-10 — reconciliation and what it changed

**2026-08-17.** Four reviewers, brief frozen at
`UPSTREAM-B10-B4-STACKED-REVIEW-BRIEF.md`. This file records what they
agreed on, what they overturned, and what I changed in response. The
opinions themselves are committed unedited alongside it.

## Weighting

| reviewer | independent measurement | weight |
|---|---|---|
| grok | yes — stock 3.27.1, lldb, three source trees rebuilt into `/tmp` archives | full |
| cursor (Grok 4.6) | yes — stock 3.27.1, lldb, isolated workdir, `otool -L` on every binary | full |
| fable (ran on `claude-opus-4-8`, not Fable 5) | yes — hybrid archive reverting only `json.o`, statically linked harness | full |
| gemini | **no** | low — see below |

**gemini's opinion is a paraphrase of the brief, not a review.** It asserts
before/after differences ("Verified: ... causes `cf-promises` to abort") while
addressing none of the four build traps the brief required it to control for,
and it wrote its file 4m03s after launch — less time than `make -j2` takes on
this machine. Two of its answers contradict material the brief handed it: it
calls `JsonIntegerCreate()`'s construction "perfectly safe" when that function
is one of the catalogued defects, and answers "Nothing" to what the fix missed
when the question text itself states `JsonPrimitiveGetAsInteger()` stays fatal.
Recorded, not discarded; counted as one weak voice, not a quarter of a quorum.

Note also that cursor identifies itself as Grok 4.6, so two of four members are
Grok-family. The panel is less independent than its headcount suggests.

## Unanimous

- **Verdict: ship with changes.** All four. Nobody said do-not-ship; nobody
  found a correctness defect in the fix itself.
- **Severity: `security@` is the right first channel.** All four.
- **The load-time claim is true.** The three measuring reviewers each
  reproduced it independently, with matching `lldb` stacks
  (`StringToLongExitOnError` ← `JsonCopy` ← `JsonObjectCopy` ←
  `RvalNewRewriter` ← `VerifyVarPromise` ← `LoadPolicy`), each with a
  small-integer control that exits 0.
- **The threat wording ships verbatim.** All four called it honest and not
  overstated.
- **B-10 must never land without B-4.** All four.

## Trigger surface is wider than we filed for

Two reviewers independently drove entry paths we had not measured:

- **augments `def.json`** kills stock `cf-promises` with *no user policy at
  all* — `JsonCopy` ← `JsonExpandElement` ← `LoadAugmentsFiles` ←
  `GenericAgentDiscoverContext`, during context discovery, before policy is
  parsed. (grok, fable.) This is the strongest concrete demonstration and
  belongs in the report.
- **`host_specific.json` / CMDB** with an otherwise innocent policy. (grok,
  cursor.)

## The finding that reframes the severity — epoch milliseconds

cursor drove it, grok corroborated with a different value:

| JSON number | stored on stock |
|---|---|
| `2000000000000` | `-1454759936` |
| `9223372036854775807` | `-1` |
| `1786965915908` (epoch-ms) | `259520772` |
| `1755400000000` (epoch-ms) | `-1241624064` |

This loads clean, validates clean, does **not** failsafe, and silently
substitutes a wrong number. Millisecond timestamps have exceeded `INT_MAX`
since 2001, so it needs no hostile operator and no exotic value. The crash is
the loud half; this is the quiet one, and an ordinary bug ticket would
under-weight it.

## Corrections to our own record

1. **Core fixes four data-reachable sites, not two.** The brief said "rlist and
   iteration are the only twins". `6a4216dad` fixes `rlist.c` + `iteration.c`;
   `367c27fc5` also fixes `generic_agent.c:2051` and `unix_iface.c:1438`. Both
   fable and grok caught this. The work was already done — the *description*
   of it was wrong.
2. **The policy function is `type()`, not `datatype()`.** `evalfunction.c:12108`
   registers `"type"`; `FnCallDatatype` is only the internal handler name. No
   `datatype()` function is registered. (cursor; verified.)
3. **Narrow the `sys.*` claim.** grok confirmed the copy path *does* run at
   start-up (`DetectEnvironment` → `GetSysVars` → `EvalContextVariablePutSpecial`
   → `JsonCopy`, breakpoint hit with `x0 == "501"`, a uid), but cursor is right
   that `/proc`-sourced containers are filled via `JsonObjectAppendInteger(int)`
   and cannot originate a `LONG_MAX+1` lexeme. **Code-plausible for any `sys.*`
   container itself parsed from JSON; not driveable from `/proc`.** File it that
   way, not as a driven crash.
4. **`Changelog: None` is documented** (`CONTRIBUTING.md:216`), so there is a
   legitimate trailer to use before an issue number exists.
5. **The "409 out of 9092 tests failed" line is not a masked failure.** It is
   `libcompat`'s printf thousands-separator self-test, a known informational
   macOS diagnostic; the suite still exits 0. (fable.) This retires the
   "harness masks failures" worry from the opposite direction to the earlier
   retraction.
6. **A benign `StringToLongExitOnError` fires during start-up even on a clean
   run.** An unconditioned lldb breakpoint stops there and prints a misleading
   `GetSysVars` stack. fable caught this before reporting and calls the
   value-conditioned breakpoint "the single most important control in the whole
   review". Worth carrying into the brief for any future panel.

## Defects the panel found in our own patch series — all fixed

| # | finding | by | fix |
|---|---|---|---|
| 1 | `8aac759` bundled the `JsonPrimitiveCopy` and `JsonSelect` source fixes under a message describing only the copy, with the `JsonSelect` test deferred to a later commit | fable | split into two commits, each shipping with its own test |
| 2 | Registration order: the aborting test ran before three others, so on unfixed code they never demonstrated their defects | cursor | assertion-failing tests registered first, fatal-conversion tests last, with a comment saying why |
| 3 | Stale comment claiming rendered-real formatting "belongs to `StringFromDouble()` and is not asserted here" — false once B-4 is below it | grok | comment corrected **and** the assertion strengthened to require the rendered form to equal the parsed lexeme |
| 4 | No test exercised the in-memory producer; a regression breaking only `JsonRealCreate` → `ToString` would stay green | grok | added `test_real_created_in_memory_renders_as_stored` pinning `JsonRealCreate(0.5)` → `"0.5000"` |
| 5 | `Co-Authored-By` present on 4 of 6 commits | fable | dropped from all six — core's CONTRIBUTING (line 66) treats the human as author |
| 6 | No `Changelog:` trailers | all four | `Changelog: Title` on the four fix commits, `Changelog: None` on the two test commits. No `Ticket:` until the issue exists |
| 7 | `mustache_extra.json` cases would abort core's `mustache_test` until the submodule bump | cursor, grok | recorded as a sequencing constraint: land the data **after** core takes a libntech carrying this change, never before |

## Topology — decided

gemini said combine; cursor, grok and fable said keep the stack (grok and fable
both adding that combining is defensible). The operative constraint all four
share is not stack-vs-squash but **one PR, landing together**. Decision: keep
the six-commit stack, one PR, PR body states B-4 cannot be dropped and offers
to squash at merge.

## What the rework did *not* touch

The rebuilt stack differs from the reviewed tip `cc4a0d9` **only** in
`tests/unit/json_test.c`. `libutils/json.c`, `libutils/mustache.c` and
`libutils/string_lib.c` are byte-identical to what all four reviewers examined,
so no review conclusion is invalidated by the rework.

## Verification of the rebuilt stack

Every one of the six commits was checked out, built with a top-level `make -j2`,
had `tests/unit/json_test` deleted to force a relink, and ran the full
`tests/unit` suite — **all six pass independently**. This closes the one gap all
four reviewers explicitly left open ("I did not rebuild each of the six commits
in isolation"). Tip: `json_test` 75/75, full suite 39/39.

Rebuilt stack (`fix/json-number-fatal-exit`, pushed to `fork`):

```
11725b0  Do not exit the process when selecting an oversized JSON array index
55f3eb3  Copy a JSON number as it was parsed
df3a263  Add regression tests for JSON number classification and rendering
84843da  Do not exit the process when rendering a JSON number
cd545ab  Add a regression test for JSON real rendering
8923f79  Do not truncate JSON reals to two decimals when rendering
0c0620d  (upstream base)
```

The pre-rework reviewed tip is preserved as tag `panel-reviewed-cc4a0d9`.
