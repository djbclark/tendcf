# Upstream register: every CFEngine/libntech defect and contribution we hold

**Living document. Update it in the same commit that changes an item's state.**

**CORRECTED 2026-08-16 (later session).** This document previously opened by
asserting that every upstream channel was closed and that "nothing is filed on
an upstream tracker yet". **Both statements were false when written**, and the
error hid three live upstream contributions. What is actually true, verified
against the GitHub API rather than restated from these notes:

| channel | reality | verified by |
|---|---|---|
| `cfengine/core` Issues | genuinely **disabled** — but **Discussions are open and are what that repo uses instead**; we have two there ([6295](https://github.com/cfengine/core/discussions/6295), [6296](https://github.com/cfengine/core/discussions/6296)). Querying `/issues/<n>` 404s on a discussion, which misled this document once — see the 2026-08-17 correction below | `gh api repos/cfengine/core` → `has_issues: false`; discussions via GraphQL |
| `cfengine/core` Pull requests | **open, and we have two live there** | [#6293](https://github.com/cfengine/core/pull/6293), [#6294](https://github.com/cfengine/core/pull/6294) |
| `NorthernTechHQ/libntech` Issues | **ENABLED** — the old claim that they were disabled was simply wrong | `gh api repos/NorthernTechHQ/libntech` → `has_issues: true`; our [#290](https://github.com/NorthernTechHQ/libntech/issues/290) is filed there |
| `NorthernTechHQ/libntech` Pull requests | **open, and we have one live there** | [#291](https://github.com/NorthernTechHQ/libntech/pull/291) |
| CFE Jira | **WORKING as of 2026-08-17, and now the ONLY filing channel** — see the 2026-08-17 Jira entry below. All open items are filed as `CFE-4715`–`CFE-4730` (15 migrated 2026-08-17, plus `CFE-4730` filed the same day) | `POST /rest/api/2/issue` → 201; anonymous `GET` of `CFE-4715` → 200 |

So the premise that motivated the fork-plus-email workaround **does not hold for
ordinary bug reporting**. Upstream GitHub accepts our issues and our pull
requests today. The fork-issue-plus-email shape remains correct for anything we
are not ready to put in front of maintainers, and email remains the right
channel for security-relevant items (B-1/B-2/B-8), but "we cannot file
upstream" is not a reason available to us any more. **Check the tracker before
asserting it is closed.**

`CONTRIBUTING.md`'s contribution *process* is **out of date and deliberately not
followed** (operator instruction, 2026-08-16). The rest of that file — code
style, log levels, commit hygiene — still applies.

The register's remaining job is to make every item **refilable on demand**:
everything below should be submittable without re-deriving anything.

## Channels, and what "reported" currently means

**SUPERSEDED 2026-08-17 — step 3 is now Jira, not email.** Operator
instruction: *"Going forward, remember to always use Jira, no longer email or
open discussion threads."* Each item gets:

1. **Code** — a branch on our fork (`djbclark/core`, `djbclark/libntech`).
2. **A tracking artifact on the fork** — an issue where issues are enabled
   (`djbclark/core`), a pull request where they are not (`djbclark/libntech`).
3. **A ticket in the CFE Jira project**, which is the upstream reference of
   record. Do **not** open GitHub Discussions and do **not** email `contact@`
   or `security@northern.tech` as a filing channel any more.

Replying on an existing email thread, or commenting on an existing Discussion,
to point at the new Jira key is still correct — that is notification, not
filing.

The email history below is retained because it is what actually happened and
because two threads carry corrections that must not be lost:
`contact@`/`security@` for B-1/B-2/B-8 (`1a00d22ac0d46c9b`, follow-up
`1a00d44a2758b9ea`), B-10/B-4 (`1a00f99c7e714823`), and P-3
(`1a007e4362402bd9`, correction `1a00fb936fc1741f`). The old rule was *when in
doubt, security@* (operator, 2026-08-16); it no longer selects a channel, but
it still describes how severity should be *stated* in a ticket.

**A second opinion is required before upstream is contacted** (operator,
2026-08-16), and **every commissioned review must have reported before anything
is sent** (operator, 2026-08-16, after the fact — see below). A quorum is not
the gate; the whole panel is. This is the same adversarial-review discipline the corpus already
applies to its own decisions — see the `*-opinion-{fable,gemini,grok}.md` panels
and the refutations they produced. A fork issue filed without one is not a
problem in itself, because the fork is not upstream; the rule is that **no email
goes out until the item has been second-opinioned and the issue updated with
whatever that review found.**

**Timing rule, learned the expensive way.** The first email to security@ went
out with 2 of 3 B-8 reviews in, on the reasoning that both agreed and the third
would concur. The third landed minutes later carrying a false statement in our
own error string, a much sharper severity argument, and the evidence that
overturned a mechanism we had told upstream was ruled out — forcing a
correcting follow-up to an external security team. Wait for every reviewer. If
one must be abandoned, cancel it explicitly and say in the email how many
reviews informed the report; never send while one is still running.

**Three items ARE filed upstream** — P-1, P-2 and P-3, all opened by the
operator manually on 2026-08-15 evening and not recorded here until the
2026-08-16 correction. An earlier version of this line claimed the opposite.
Nothing is filed on the CFE Jira.

## Register

Legend: **done** · *pending* · — not applicable.

`2nd` is the required second opinion; an item may not be emailed until it is done.

| id | Item | Repo | Fix | Fork branch | Fork artifact | 2nd | Email | Upstream |
|---|---|---|---|---|---|---|---|---|
| B-1 | Poll loops count iterations instead of measuring elapsed time, so the termination ladder overshoots ~4.5x on Darwin | core | **done** `26634ac1f` + `943d5371f` | **done** [`fix/exec-timeout-commands`](https://github.com/djbclark/core/tree/fix/exec-timeout-commands) | **done** [#4](https://github.com/djbclark/core/issues/4) | **done** 3-model panel; found 2 defects, both fixed; **withdrew the fail-open claim** | **done** — `security@` 2026-08-17, Gmail id `1a00d22ac0d46c9b`, + correcting follow-up `1a00d44a2758b9ea` | **done** [cfengine/core#6300](https://github.com/cfengine/core/pull/6300) — OPEN, MERGEABLE, 1 commit, branch [`fix/exec-timeout-poll-deadline`](https://github.com/djbclark/core/tree/fix/exec-timeout-poll-deadline) cut from master `17eb78e6d`, trailers `Ticket: CFE-4728`. Byte-identical tree to `fix/exec-timeout-commands`, squashed, **and the withdrawn fail-open claim removed from the commit message** — `26634ac1f`'s body still asserted it. Re-measured independently: stock 11.36/10.80/10.90s vs branch 4.54/4.48/4.41s. Stock-libntech gate discharged | [CFE-4728](https://northerntech.atlassian.net/browse/CFE-4728) |
| B-2 | Descendants not signalled on timeout; grandchild holds the pipe, so `exec_timeout` does not bound wall clock | core | **done** `cb2561584` + `847373cf6` merged with B-8, + two required changes: MinGW guard on `getpgid()`/`kill(-pid,...)` (`timeout.c` builds unconditionally on Windows, `pipes_unix.c`'s `setpgid()` half does not) and `TIMEOUT_ARMED` → `volatile sig_atomic_t` (was a plain `bool` written from the `SIGALRM` handler, an oversight relative to `TIMEOUT_FIRED`/`TIMEOUT_SIGNALLED`), both `d004c19ab` | **done** [`fix/timeout-process-group-merged`](https://github.com/djbclark/core/tree/fix/timeout-process-group-merged) | **done** [#5](https://github.com/djbclark/core/issues/5) | **done** — merge-conflict resolution self-verified (no Fable needed, contrary to the earlier estimate): full rebuild clean, `tests/unit/timeout_test.c` added (6 cases, `dbf759d16`, unix-only) and all 6 acceptance tests in `04_exec_timeout/` re-pass. 2-seat delta panel (gemini-3.1-pro-high, grok-4.6): gemini cleared both the MinGW guard and the `sig_atomic_t` conversion outright; grok caught a real gap in the first test draft — no case exercised `TimeOutSignalledProcess()` being *true*, so a `ClearTimeOut()` that wiped a true `TIMEOUT_SIGNALLED` would have passed — fixed with a fork-based 6th case and confirmed by discrimination (breaks exactly that one test), then gemini re-reviewed the fix as sound | **done** — `security@` 2026-08-17, Gmail id `1a00d22ac0d46c9b` (same mail as B-1/B-8) | **done** [cfengine/core#6305](https://github.com/cfengine/core/pull/6305) — supersedes `#6299` (B-8 alone, still open, zero maintainer engagement); pointer comment left on `#6299`. If `#6299` merges separately first, `#6305` rebases down to the process-group commits alone | [CFE-4729](https://northerntech.atlassian.net/browse/CFE-4729) |
| B-3 | No `process_darwin.c`; macOS uses the stub, so `GetProcessState()` never reports ZOMBIE/STOPPED and `SafeKill()`'s PID-recycling guard is disabled. **Impact was understated as filed**: the ticket lists the recycling guard and the termination-wait cost, but the largest consequence is that **custom promise modules cannot run on macOS at all** — `PromiseModule_Load()` fails the module outright when `GetProcessStartTime()` returns unknown (`mod_custom.c:504`), which on the stub is unconditional. Conversely the "every `GracefulTerminate()` caller" phrasing is too broad *for the guard*: `timeout.c:45` passes `PROCESS_START_TIME_UNKNOWN` by design. The wait-budget effect does apply to every caller | core | **done** `68ac0d6f5`, cut from upstream master `a0bca6aaf`. New `libpromises/process_darwin.c` reading `sysctl KERN_PROC_PID`, modelled on `process_freebsd.c`, plus `if MACOSX` wiring and removal of `process_test` from the macOS XFAIL list. **The one Darwin-specific divergence**: for a nonexistent pid `KERN_PROC_PID` *succeeds* and returns length zero with the buffer untouched, rather than failing — so the buffer is zeroed and the length checked. Copying FreeBSD's `if (sysctl(...) == 0)` test alone would parse an unwritten `kinfo_proc` and report dead processes as running, worse than the stub. `proc_pidinfo(PROC_PIDTBSDINFO)` rejected on two counts: EPERM for other users' processes when unprivileged, and ESRCH for an unreaped zombie, so it cannot express `PROCESS_STATE_ZOMBIE`. Discrimination by rebuilding the library both ways with a forced relink: stub 4 FAIL/exit 1 (`process_test.c:91,92,149,216`) → 0 FAIL/exit 0. `process_test` therefore *must* leave `XFAIL_TESTS` or the macOS job XPASSes. `make check` 66 PASS/3 XFAIL/1 SKIP/0 FAIL (baseline 65/4); 20 runs, no flake; clean under `-Werror -Wall -Wextra` | **done** [`fix/process-darwin`](https://github.com/djbclark/core/tree/fix/process-darwin) | — (Jira only now) | **done** — 2-seat panel (grok-4.6, gemini-3.1-pro-high) against a frozen brief; both SHIP, **no required code changes**, required changes were to the commit message and were applied. grok was substantially the deeper seat per [[panel-reviewer-weighting]]: it force-relinked and ran `make check` itself, compiled under CI's `-Werror`, censused 758 processes, and **found the `mod_custom.c:504` impact that neither the ticket, the brief, nor gemini mentioned**. It also refuted gemini's "ENOMEM fails closed" claim — `ProcessWaitUntilExited()` treats `DOES_NOT_EXIST` as *success* (`process_unix.c:96`), so that path is not fail-closed — and flagged the commit's "~7.0 s" as host-specific false precision (grok measured ~12.5 s on the same box under load). gemini's sole suggestion, `len < sizeof(psinfo)`, was **declined**: an older/smaller kernel struct would then reject every process, failing toward `DOES_NOT_EXIST`, the dangerous direction. Took the zero-risk half instead (`memset` before the call) | — (Jira only now) | **done** [CFE-4718](https://northerntech.atlassian.net/browse/CFE-4718) — updated by comment 159439 with the fix, branch, the corrected impact, the rejected API, and the discrimination — **PR [#6307](https://github.com/cfengine/core/pull/6307)** opened 2026-08-18 |
| B-4 | JSON reals truncated to 2 decimals (`0.00049` → `0.00`), including through mustache templating; `%.2f` and `%.4f` disagree | libntech **+ core** | **done** both halves, now the **base of B-10's stack** (not independently landable): libntech `8923f79`+`cd545ab`, core `6a4216dad` | **done** [`fix/json-number-fatal-exit`](https://github.com/djbclark/libntech/tree/fix/json-number-fatal-exit) (B-4 is its bottom two commits) | **done** [libntech#2](https://github.com/djbclark/libntech/issues/2), corrected by comment 2026-08-17 | **done** — 4-member panel 2026-08-17; B-4 had never been reviewed before | **done** — covered by B-10's `security@` mail | **done** [NorthernTechHQ/libntech#294](https://github.com/NorthernTechHQ/libntech/pull/294) — OPEN, MERGEABLE, 6 commits, branch [`fix/json-number-handling`](https://github.com/djbclark/libntech/tree/fix/json-number-handling) cut from master `0c0620d` (current tip), every commit carrying `Ticket: CFE-4724`. Merges cleanly with `#293` (`merge-tree`, zero conflicts), so the two are independently landable. Was [djbclark/libntech#5](https://github.com/djbclark/libntech/pull/5) (fork PR, filed with B-10) |
| B-10 | A **valid JSON number terminates the process**: exponent form without a dot (`1e-8`, `2e0`) is misclassified INTEGER, and integers past `long` overflow; both reach `StringToLongExitOnError()` → `DoCleanupAndExit()`. Measured on stock 3.27.1: `cf-promises` dies and **cf-agent falls back to failsafe** | libntech **+ core** | **done** both halves: libntech `fix/json-number-fatal-exit` (6 commits, tip `11725b0`), core `fix/json-number-rendering` (`6a4216dad`+`367c27fc5`+`32c38f8ab`) -- core half **behaviourally verified** both directions | **done** [`fix/json-number-fatal-exit`](https://github.com/djbclark/libntech/tree/fix/json-number-fatal-exit) + [`fix/json-number-rendering`](https://github.com/djbclark/core/tree/fix/json-number-rendering) | **done** [libntech#4](https://github.com/djbclark/libntech/issues/4) + [core#13](https://github.com/djbclark/core/issues/13), #4 corrected by comment 2026-08-17 | **done** — 4-member panel 2026-08-17, 4/4 ship-with-changes and 4/4 `security@`; found 7 defects in our own series, all fixed | **done** — `security@northern.tech` 2026-08-17, Gmail id `1a00f99c7e714823` | **done — libntech half** [NorthernTechHQ/libntech#294](https://github.com/NorthernTechHQ/libntech/pull/294) (6 commits incl. B-4/B-11, `Ticket: CFE-4724`, merges cleanly with `#293`; was fork PR [djbclark/libntech#5](https://github.com/djbclark/libntech/pull/5)). **Core half still *pending*** — `fix/json-number-rendering` cannot land until `#294` merges and cfengine/core bumps its libntech submodule; that dependency is [core#7](https://github.com/djbclark/core/issues/7). Verified 2026-08-17: json_test 75/75, and reverting only `json.c`+`mustache.c` to stock makes the library **terminate its own test binary** at `test_primitive_to_string_numbers` |
| B-11 | `JsonRealCreate()` stores reals with `%.4f`, so **`JsonCopy()` changes a document's values**: `0.00049` → `0.0005`, `3.14159265` → `3.1416`. Measured; distinct from B-4, which is the render path | libntech | **done** — subsumed by B-10's copy commit `55f3eb3`, which makes `JsonPrimitiveCopy()` keep the parsed lexeme instead of rebuilding through `JsonRealCreate()`/`JsonIntegerCreate()`. The constructor still formats with `%.4f` for reals *built in memory*; that is pre-existing and out of scope, and is now pinned by `test_real_created_in_memory_renders_as_stored` | **done** [`fix/json-number-fatal-exit`](https://github.com/djbclark/libntech/tree/fix/json-number-fatal-exit) | **done** — folded into [libntech#4](https://github.com/djbclark/libntech/issues/4) | **done** — covered by B-10's panel | **done** — named in B-10's `security@` mail as the silent-corruption half | **done** [NorthernTechHQ/libntech#294](https://github.com/NorthernTechHQ/libntech/pull/294) — ships as that PR's `Fixed JsonCopy() changing a document's numeric values` commit (was fork PR [djbclark/libntech#5](https://github.com/djbclark/libntech/pull/5)) |
| B-12 | `GetNetworkingInfo()` declares `long lowest_metric = 0;` (`libenv/unix_iface.c:1425`) and **never assigns it**, so the default-route comparison is `metric_value < 0` — false for every real metric. CFEngine therefore picks the **first** active default gateway, not the lowest-metric one, contrary to the variable name and the comparison's intent. Found while verifying B-10's core half; pre-existing and deliberately **not** fixed there | core | **done** — commit `3d10206ee`, cut from master `17eb78e6d`. Records the selected route's metric so a strictly lower one replaces it; ties still keep the earlier entry. Selection loop lifted into a static `FindLowestMetricDefaultRoute()` so `tests/unit/unix_iface_test.c` (7 cases, `#include <unix_iface.c>` per the `sysinfo_test` precedent, `if !NT`) can drive it with constructed route data | **done** [`fix/default-route-lowest-metric`](https://github.com/djbclark/core/tree/fix/default-route-lowest-metric) | **done** [core#14](https://github.com/djbclark/core/issues/14) | **done** — panel-cleared **unanimously** across four labs (grok, fable, deepseek-v4-pro, gemini-3.1-pro), and discrimination re-run by the owning session rather than taken on report: deleting only the line `lowest_metric = metric_value;` builds clean and fails exactly `test_lowest_metric_last` (`"192.168.0.1" != "192.168.0.3"`), restore byte-identical `4e6bd587…9e843`. `test_lowest_metric_first` is a deliberate control and passes unfixed. **No end-to-end test crosses a real Linux `/proc/net/route`** — this was developed on macOS 26.6.1 arm64, and the PR says so | — (Jira only now) | **done** [cfengine/core#6302](https://github.com/cfengine/core/pull/6302) — body carries both agreed caveats: `fib_priority` is `u32` but `fib_trie.c` prints it `%d`, so a metric ≥ 2^31 renders with a leading `-` and the `[[:xdigit:]]+` capture drops the route line before selection (pre-existing, orthogonal, not addressed); and the blast radius is stated honestly, since the kernel emits default routes in ascending metric order so most hosts never hit it [CFE-4723](https://northerntech.atlassian.net/browse/CFE-4723) |
| B-13 | libntech's JSON string codec is non-conformant **both ways**. Reading: `HexStringToChar()` rejects code points above U+00FF (`libutils/json.c:1063`) and the `case 'u':` arm then `break`s **without advancing the cursor** (`:1108-1120`), so the enclosing `for (...; c++)` lands on the `u` and the escape becomes literal text with the backslash dropped — `readjson()` of `{"city":"中国"}` yields the string `u4e2du56fd`. Escapes in U+0080–U+00FF decode to a single raw byte, i.e. Latin-1, not UTF-8. Writing: `JsonEncodeStringWriter()` (`:1015-1022`) escapes each non-printable-ASCII **byte** as `\u%04x` of the byte value, so conformant parsers decode multi-byte UTF-8 as separate wrong characters. **The two halves are exact inverses, so libntech round-trips its own output perfectly and no write-then-read test can catch either** | libntech | **done** — both halves in one commit `90cf8cc`, cut from upstream `0c0620d`. Encoder decodes UTF-8 with strict validation (overlongs, encoded surrogates, >U+10FFFF, stray continuations, truncated tails all rejected) and escapes the **code point**, surrogate-pairing outside the BMP; output stays pure ASCII and is byte-identical for ASCII input. Invalid-UTF-8 bytes keep the historical per-byte `\u00XX`. Decoder handles the full BMP, emits UTF-8, combines surrogate pairs, and substitutes U+FFFD for unpaired surrogates/malformed escapes instead of corrupting them into literal text. `HexStringToChar()` → `FourHexDigitsToInt()`, no `strlen`/`alloca`, no `isdigit()` negative-`char` UB | **done** [`fix/json-string-codec`](https://github.com/djbclark/libntech/tree/fix/json-string-codec) | — (Jira only now) | **done** — written by Fable 5 xhigh, then **independently re-verified by the owning session**: rebuilt (rc=0, 0 warnings), 39/39 test binaries and `json_test` 69→72 cases, discrimination re-run from pristine `json.c` (exactly the 3 new cases fail, rc=3, restore byte-identical `b38c99e8…`), and all 29 hard-coded test expectations re-derived from python3 | — (Jira only now) | **done** [NorthernTechHQ/libntech#293](https://github.com/NorthernTechHQ/libntech/pull/293) — OPEN, MERGEABLE, 1 commit, +376/−30, trailer `Ticket: CFE-4730`. The PR body states the compatibility consequence and discloses B-14 | [CFE-4730](https://northerntech.atlassian.net/browse/CFE-4730) |
| B-14 | **The JSON parser double-decodes string escapes, silently corrupting valid JSON.** `JsonParseAsString()` (`libutils/json.c:2184` **on upstream master `0c0620d`**) already performs a complete unescaping pass — `\\`, `\"`, `\/` written literally, `\b \f \n \r \t` written as control characters, only `\u` left verbatim — and the three call sites (`:2405`, `:2479`, `:2668`) then run `JsonDecodeString()` over that **already-decoded** text. (On the B-13 branch the same code sits ~210 lines lower — `2394`, `2615`, `2689`, `2878` — because that fix adds helpers earlier in the file. **Cite the master offsets upstream**; the branch offsets are what you see locally in `libntech-jsonstr`.) A backslash produced by decoding `\\` becomes an escape introducer again on the second pass. Measured on stock `0c0620d`: the document `{"p": "C:\\temp\\new"}`, valid JSON for the ordinary Windows path `C:\temp\new`, parses to `C:<TAB>emp<NL>ew` (`43 3a 09 65 6d 70 0a 65 77` vs python's `43 3a 5c 74 65 6d 70 5c 6e 65 77`). Also `{"p":"\\u0041"}` → `A` instead of the literal `\u0041`, and `{"p":"a\\tb"}` → `a<TAB>b`. **Distinct from B-13**, in a different function; B-13's fix neither causes nor cures it, verified with the fix applied | libntech | **done** — `\u` handling (surrogate pairs + malformed-escape U+FFFD fallback, ported from B-13) moved into `JsonParseAsString()` itself; the three redundant `JsonDecodeString()` calls removed. Object property names, which never called `JsonDecodeString()` at all, now get `\u` decoded too as a side effect | **done** [`fix/json-double-decode`](https://github.com/djbclark/libntech/tree/fix/json-double-decode) — stacked on B-13 | — (Jira only now) | **done** — 2 new `json_test.c` cases; discrimination proven by reverting the fix (both fail with the exact corruption measured above) and restoring it (74/74 pass); full unit suite 37/37 binaries pass | — (Jira only now) | **done** [NorthernTechHQ/libntech#297](https://github.com/NorthernTechHQ/libntech/pull/297) — OPEN, stacked on #293, trailer `Ticket: CFE-4731` | [CFE-4731](https://northerntech.atlassian.net/browse/CFE-4731) |
| B-15 | **`ReconcileMountOptions()` arms an alarm at the remount/unmount_mount sites and never disarms it itself.** `cf-agent/nfs.c:1369` calls `SetTimeOut(timeout)` at `:1436` (remount path) and `:1461` (unmount_mount path); no path in the function disarms. **Severity corrected 2026-08-18, was overstated as filed**: both arming sites fall through unconditionally to `LiveMountConverged()` → `LoadMountInfo()`, which replaces the alarm (`SetTimeOut(RPCTIMEOUT)` at `:403`) and, on its normal path, clears it (`alarm(0)` at `:581`) — so on an ordinary run the remount-timeout does **not** survive the function's return or cover "arbitrary subsequent agent work." What's real: (1) a window from the reconcile command finishing until `:403` re-arms, during which the timeout is live over unrelated work (spurious `"Time out"` log if it fires); (2) fragility — the non-leak depends entirely on `LiveMountConverged()` happening to call `LoadMountInfo()`, an incidental side effect of a callee, not a guaranteed pairing. Also found: a **third** `LoadMountInfo()` early-return leak at `:487` (`strstr(vbuff, "RPC")` abort) the original catalogue omitted, alongside `:408`/`:427` — same pre-existing error-path family, not introduced by this ticket. Introduced by `348722a06` (Nick Anderson, 2026-07-12), reachable only with the opt-in `remount_method` attribute | core | **done** `190f869a5`, cut from upstream master `a0bca6aaf`. Two-line disarm (`alarm(0); signal(SIGALRM, SIG_DFL);`) placed *inside* the method loop, right after remount/unmount_mount dispatch and before `LiveMountConverged()` — not after the loop as originally filed, so a two-method list can't have method 1's leftover cover method 2 or the convergence check. Matches the file's own idiom at `:581`/`:1178`. Surfaced by fable during the B-2 merge review, severity re-derived against master by the owning session | **done** [`fix/mount-options-timeout-leak`](https://github.com/djbclark/core/tree/fix/mount-options-timeout-leak) | — (Jira only now) | **done** — 2-seat panel (grok-4.6, gemini-3.1-pro-high) against a frozen brief targeting the severity claim specifically; unanimous SHIP / SAFE TO POST on all seven questions. grok's trap-control and line-by-line walk were substantially deeper than gemini's (per [[panel-reviewer-weighting]]) and it caught a precision point gemini missed: the correction must say the *remount-timeout* doesn't escape, not that "the leak never escapes the function" — `LoadMountInfo()`'s own `RPCTIMEOUT` alarm still does, on the pre-existing `:408/:427/:487` error paths | — (Jira only now) | **done** [CFE-4732](https://northerntech.atlassian.net/browse/CFE-4732) — corrected by comment 159434 (2026-08-18) covering the masking chain, the corrected severity, and the omitted `:487` leak — **PR [#6308](https://github.com/cfengine/core/pull/6308)** opened 2026-08-18 |
| B-16 | **`ShellCommandReturnsZero()` leaves `ALARM_PID` naming a reaped, recyclable pid.** `libpromises/unix.c:166` sets `ALARM_PID = pid` at `:225`, reaps at `:238` (`waitpid` `WNOHANG` poll) and `:258` (blocking drain), and never resets it; the only `ALARM_PID = -1` in the function is `:184`, before the fork. **This is the one place the "pid cannot recycle, the child is an unreaped zombie" argument fails** — a previous panel accepted that reasoning as settled, and this is its counterexample. A leaked alarm (B-15, or any error-path leak) firing after such a call and before anything rewrites `ALARM_PID` runs `TimeOut()` against a possibly-recycled pid, as root. Chain is long (leak × no intervening rewrite × recycle × timing) so severity is low, but the one-line hygiene fix removes the exception and makes the stale-`ALARM_PID` reasoning sound again | core | **done** `e7fd46c6d`, cut from upstream master `a0bca6aaf` (ticket text and line numbers checked out exactly, no drift this time). Two insertions, one per reap site (`:238` WNOHANG break, `:258` blocking drain), matching the file's own `ALARM_PID = -1` idiom at `:184`. The third return point (`:249`, failed `waitpid()`) deliberately left alone — no reap occurs there, so the zombie-holds-the-slot reasoning still applies. New `tests/unit/unix_test.c`: unlike the `nfs.c` family this function is exported with no `EvalContext`/`Promise` dependency, so it's directly testable — two cases (`true`/`false` via `SHELL_TYPE_USE`) assert `ALARM_PID == -1` post-reap, discrimination confirmed by hand (both fail pre-fix, pass post-fix; first attempt at this nearly gave a false pass by relinking against a stale archived `.la` instead of rebuilding it — caught before it faked a result). The `:258` blocking-drain path ships with the identical fix but no dedicated test (real `SIGTERM` mid-poll judged too CI-fragile) | **done** [`fix/alarm-pid-reset-after-reap`](https://github.com/djbclark/core/tree/fix/alarm-pid-reset-after-reap) | — (Jira only now) | **done** — 2-seat panel (grok-4.6, gemini-3.1-pro-high) against a frozen brief; unanimous SHIP, no required changes. gemini engaged substantively this round — independently reached the same `ECHILD`-means-already-reaped reasoning grok gave for why resetting after the `:258` loop's failure exit is still correct, not just a rubber stamp | — (Jira only now) | **done** [CFE-4733](https://northerntech.atlassian.net/browse/CFE-4733) — updated by comment 159435 with the fix, branch, test, and panel outcome — **PR [#6309](https://github.com/cfengine/core/pull/6309)** opened 2026-08-18 |
| B-17 | **`cf_pclose()`/`cf_pclose_full_duplex()` cleared `ALARM_PID` before waiting for the child, so a command that closed its output but kept running was unreachable by the time the alarm fired.** `TimeOut()` found `ALARM_PID == -1` and terminated nothing; the command ran to completion, entirely unbounded by `exec_timeout`. Split out from B-8/CFE-4726 (the reporting fail-open) as its termination-half companion; CFE-4726's "was NOT terminated and ran to completion" wording exists because of this gap | core | **done** `8f4ebedbd`, cut from the tip of `fix/timeout-process-group-merged` (B-2). New `ClearAlarmedPid()` in `pipes_unix.c` clears `ALARM_PID` only *after* `cf_pwait()`'s reap, guarded with `pthread_sigmask()` (not `sigprocmask()` — see review) around the compare-and-clear. Measured on Darwin arm64: unfixed ~30s/not signalled, fixed ~2s/signalled; acceptance test (rewritten to assert termination, not just detection) 19.41s fixed vs 31.96s reverted; 6/6 in `04_exec_timeout/`; 7/7 unit tests including a new `test_pclose_leaves_the_alarm_its_process` | **done** [`fix/exec-timeout-alarm-pid`](https://github.com/djbclark/core/tree/fix/exec-timeout-alarm-pid) | — (Jira only now) | **done** — 3-model panel (gemini-3.1-pro-high, grok-4.6, fable-deep/Fable 5 xhigh) against a frozen brief, each with independent host measurements (C probes, `objdump`/`otool` disassembly, timing histograms), not paraphrase. Consensus ship-with-changes: swap `sigprocmask()` → `pthread_sigmask()` (applied, rebuilt, retested clean) since `cf_pclose()` is reached from cf-serverd/cf-execd worker threads and POSIX leaves plain `sigprocmask()` unspecified there (grok measured it as process-wide, not per-thread, on this Darwin build) — not a live bug today (no daemon thread ever arms `SIGALRM`), but the correct call regardless. Softened the commit message's "so the guarantee itself holds" overclaim. gemini's review also asserted a fabricated `pid == 0` early-return inside `cf_pclose()` itself (the check only exists in `cf_pclose_full_duplex()`) — independently refuted by both grok and fable-deep before being weighted out, per [[panel-reviewer-weighting]]. Surfaced two new pre-existing, out-of-scope defects, filed as B-18/B-19 below rather than folded in | — (Jira only now) | *pending* | **done** [CFE-4727](https://northerntech.atlassian.net/browse/CFE-4727) — updated by comment with the fix, branch, measurements and panel outcome (ticket pre-existed, filed 2026-08-16/17, previously "No patch offered") — **PR [#6310](https://github.com/cfengine/core/pull/6310)** opened 2026-08-18 |
| B-18 | **`SetTimeOut()` arms before `cf_popen()`'s fork publishes the child's pid**, so a short `exec_timeout` can fire in that window on a loaded host with nothing registered to terminate — the same failure B-17 closes, through a different door (arming order, not clearing order). `GenericCreatePipeAndFork()` publishes `ALARM_PID` at `pipes_unix.c:272`, after `SetTimeOut()` has already armed at `verify_exec.c:308`. Previously only a theoretical note in a prior review doc; **empirically confirmed this session** via a real flake in B-17's own unit test under parallel `make check` load, not reproduced on demand but observed directly | core | **done** `ab98a5df4`, cut as a sibling off `dbf759d16` (not stacked on B-17/B-19). `SetTimeOut()` stashes the timeout and leaves the clock stopped; new `StartTimeOutClock()` is called from `GenericCreatePipeAndFork()` immediately after `ALARM_PID = pid`, so no alarm can be pending without a process to kill. One-shot per `SetTimeOut()`, so a second fork under one timeout runs on the remaining time as before; `TIMEOUT_ARMED` is still set pre-fork, leaving the child's `setpgid()` decision untouched. Unit 6/6 → **10/10**, acceptance `08_commands/04_exec_timeout` 6/6 both sides (62s → 74s). Discrimination proved, not asserted: rebuilding with the pre-fix arming order emulated fails exactly 2 of 10 (`test_clock_does_not_run_before_the_fork`, `test_set_leaves_the_clock_stopped`), both passing again on revert | **done** [`fix/exec-timeout-prefork-race`](https://github.com/djbclark/core/tree/fix/exec-timeout-prefork-race) | — (Jira only now) | **done** — found by B-17's 3-model panel, then its own 2-seat panel (grok-4.6, gemini-3.1-pro-high) against a frozen brief; both ship-with-changes, both required changes applied pre-push. **grok found a real platform bug the author missed**: guarding the immediate-arm on `__MINGW32__` alone left **Cygwin** on the deferred path with no starter — `AM_CONDITIONAL([NT])` is `mingw|cygwin` and `pipes_unix.c` builds only under `!NT`, so `exec_timeout` would have silently stopped working there, and `timeout_test` is `!NT` too so no CI job would have caught it. Now `__MINGW32__ || __CYGWIN__`. grok also falsified the commit message's "a leaked armed timeout now goes inert" claim — `TIMEOUT_PENDING` stays set with no timer, and the next `GenericCreatePipeAndFork()` starts that **full** budget against an unrelated child, where the old leaked alarm could only spend its remainder; message corrected, leak sites left to B-15/CFE-4732. Took grok's optional U4 test rewrite (the second `StartTimeOutClock()` is now issued against a *running* clock; the old version's first `alarm(0)` cancelled the timer, so it never exercised the production sequence at `nfs.c:1459`) and its U7 changelog fix (`Changelog: Commit` dumps implementation detail, against `CONTRIBUTING.md`). Skipped U6 (`TIMEOUT_PENDING` → `volatile sig_atomic_t`) — reviewers split, adjudicated for gemini: the variable has no handler interaction, so the annotation would imply concurrent signal state that does not exist. gemini's sole required change was **rejected** on verification: it called the `cf-monitord/history.c:242` arm a "real and severe regression", but `GetMeasurementAttributes()` starts from `ZeroAttributes` and never populates `.contain`, so `a.contain.timeout` is always 0 and that `SetTimeOut()` is unreachable — grok caught this independently, per [[panel-reviewer-weighting]] | — (Jira only now) | **done** [CFE-4734](https://northerntech.atlassian.net/browse/CFE-4734) — updated by comment (159432) with the fix, branch, measurements, discrimination and panel outcome — **PR [#6311](https://github.com/cfengine/core/pull/6311)** opened 2026-08-18 |
| B-19 | **`cf_popen*()`'s eight `fdopen()`-failure paths reap the child but never clear `ALARM_PID`, and `RepairExec()`'s `pfp == NULL` branch never calls `ClearTimeOut()`.** `pipes_unix.c:458,470,588,600,670,681,789,800` all do `cf_pwait(pid); return NULL;` without the new `ClearAlarmedPid()`; `verify_exec.c:371-375` returns `ACTION_RESULT_FAILED` without reaching the function's only `ClearTimeOut()` at `:502`. An armed alarm can then stay pointed at a reaped, recyclable pid for up to the full `exec_timeout` — same defect class as B-17, but a window of seconds-to-minutes rather than instructions. Pre-existing, byte-identical to the pre-B-17 parent, gated on rare `fdopen()` failures (ENOMEM/EMFILE). A milder sibling of B-16 (`ShellCommandReturnsZero()`'s identical uncleared-post-reap shape) | core | **done** `453cc264d`, cut from B-17's tip (`8f4ebedbd`). Mechanical: `ClearAlarmedPid(pid)` after each of the eight `cf_pwait()` calls (new forward declaration makes the `static` helper visible), plus `ClearTimeOut()` on `RepairExec()`'s `pfp == NULL` path under the same `a->contain.timeout != CF_NOINT` gate the function's normal-completion path already uses. Panel disproved the original "untestable" claim: `tests/unit/timeout_test.c` gained `test_leftover_alarm_does_not_kill_next_child` (portable POSIX, `RLIMIT_NOFILE` forces a `pipe()` failure, no interposition needed), discriminated by hand (fails exactly at `TimeOutHasFired()` with the fix's `ClearTimeOut()` call removed) | **done** [`fix/exec-timeout-alarm-leak`](https://github.com/djbclark/core/tree/fix/exec-timeout-alarm-leak) | — (Jira only now) | **done** — found by B-17's 3-model panel (fable-deep), then its own 2-seat delta panel (gemini-3.1-pro-high, grok-4.6). grok proved the eight insertions correct by object-code inspection (compiler merges them into four shared tails) and found two more real-but-out-of-scope leaks (raw fd leak on `fdopen()` failure; two more `RepairExec()` early returns skipping `ClearTimeOut()`) that gemini also independently raised — both named in the commit message and left to the existing B-15 family rather than grown into this SHA | — (Jira only now) | **done** [CFE-4735](https://northerntech.atlassian.net/browse/CFE-4735) — updated by comment with the fix, branch, panel outcome and discrimination — **PR [#6312](https://github.com/cfengine/core/pull/6312)** opened 2026-08-18 |
| B-5a | Rejected CMDB file names no key, value or path — the `void *data` carrier already exists and is `ARG_UNUSED` | core | **done** `958d13949`, cut from upstream master `a0bca6aaf`. Both `JsonWalk()` visitors now use the previously-`ARG_UNUSED` carrier; the three sections (`vars`/`variables`/`classes`) share one `CheckCMDBDataForUnexpandedVars()` helper that also reports the file path. **Design point:** the helper walks each *top-level entry* separately, not the section as a whole — a single walk can only report the offending primitive's immediate property name, which is the metadata key `value` in the CFE-3633 `variables` format and nothing at all for an array element | **done** [`fix/cmdb-name-offending-key`](https://github.com/djbclark/core/tree/fix/cmdb-name-offending-key) | **done** [#8](https://github.com/djbclark/core/issues/8) | **done** — 2-seat panel (grok-4.6, gemini-3.1-pro-high) run on **disposable read-only copies** after gemini was caught editing the tree under review (see the reviewer-contamination note below). Both SHIP WITH CHANGES, unanimous on Q1–Q5. **grok found a real test gap**: test 12 uses a bare `vars` string whose primitive property name *is* the entry name, so folding the walk back into one section walk would still pass it. Added `15-variable-references-metadata-format.cf` and **proved the gap by simulating the regression** — 12 passes under it, 15 fails. Also took grok's `assert(data != NULL)` + dropped NULL guards, the `JsonGetPropertyAsString` naming consistency (5 uses vs my 1), and its correction that "no behaviour change" was false for the log text | — (Jira only now) | **done** [cfengine/core#6315](https://github.com/cfengine/core/pull/6315) — [CFE-4719](https://northerntech.atlassian.net/browse/CFE-4719), comment 159444 |
| B-5b | One bad key silently drops **every** variable on the host; agent then reports no failures | core | **partially done** `8f0076b81`, stacked on B-5a's `958d13949` (branch cut from `fix/cmdb-name-offending-key`, not master). Fixes only the blast-radius half: `CheckCMDBDataForUnexpandedVars()` rejected the whole `vars`/`variables`/`classes` section on the first bad entry, discarding every other entry in it; checked per entry now, matching the file's existing skip-and-continue idiom (same one B-5a/B-21 already used). The "agent reports no promise failures" half is a genuine design question, left open per the original filing | **done** [`fix/cmdb-one-bad-entry-skips-only-that-entry`](https://github.com/djbclark/core/tree/fix/cmdb-one-bad-entry-skips-only-that-entry) | **done** [#9](https://github.com/djbclark/core/issues/9), updated with the fix and scope note | *skipped* — small, mechanical, directly extends an idiom this file already uses elsewhere (B-3/B-5a); discrimination proven by hand instead (new acceptance test fails unpatched, passes patched, full `00_basics/06_host_specific_data` still 14/14) | — (Jira only now) | **done** [CFE-4720](https://northerntech.atlassian.net/browse/CFE-4720) — comment 159453 (2026-08-18) with the fix, branch, and PR — **PR [#6320](https://github.com/cfengine/core/pull/6320)** opened 2026-08-18, stacked on #6315 |
| B-6 | `eval()` returns `%lf` for integral results, so arithmetic cannot feed any function taking a count | core | **done** `b74e8f4cf`, cut from upstream master `a0bca6aaf`. New `FnReturnRealOrInt()` renders `%ld` when integral and in range. **Range check is the subtle part**: bounds are asymmetric because `LONG_MIN` is a power of two and converts to double exactly, but `(double) LONG_MAX` rounds *up* to `LONG_MAX + 1`, so `<=` would admit 2^63 and make the cast UB. `sum`/`product`/`mean`/`variance` deliberately untouched — all declared `CF_DATA_TYPE_REAL` with policy assigning them to `real =>` vars, whereas `eval` is `CF_DATA_TYPE_STRING` | **done** [`fix/eval-integral-result`](https://github.com/djbclark/core/tree/fix/eval-integral-result) | **done** [#10](https://github.com/djbclark/core/issues/10) | *not panelled* — written by an Opus 5 subagent with its own discrimination proof (`test_eval_integral_result` fails `"3" != "3.000000"` unpatched, passes patched, shared library forcibly relinked). **Known compatibility risk, stated in the PR**: bundled `eval.cf` was itself asserting `300.000000` etc. and its expectations are updated; any policy string-comparing `eval()` output is affected. Belongs in a minor, not a patch, release. Masterfiles/Enterprise consumers NOT surveyed | — (Jira only now) | **done** [cfengine/core#6318](https://github.com/cfengine/core/pull/6318) — [CFE-4721](https://northerntech.atlassian.net/browse/CFE-4721), comment 159447 |
| B-7 | Dotted CMDB keys silently become scope paths, with no warning (**warn only** — do not change behaviour) | core | **done** `ee1f9d60c`, cut from upstream master `a0bca6aaf`. New `LogCMDBVariableScope()` called from `GetCMDBVariableRef()`. **Two levels, to avoid log noise on working configs**: VERBOSE for the documented `[namespace:]bundle.variable` form (indistinguishable from deliberate scope qualification), WARNING only for keys that *cannot* be that form — empty scope (`.key`), empty lval (`key.`), or an lval still containing a dot (`com.dotted.key`). The dotted-lval case is empirically grounded: a `vars:` promise splits its promiser identically, so no policy can create a dot-containing variable name. **Also fixed** the three `Installing CMDB variable` verbose messages, which printed `'%s:%s.%s'` and so double-printed the scope (`data:com.com.dotted.key`) — the very address the operator needs | **done** [`fix/cmdb-dotted-key-warning`](https://github.com/djbclark/core/tree/fix/cmdb-dotted-key-warning) | **done** [#11](https://github.com/djbclark/core/issues/11) | *not panelled* — Opus 5 subagent, discrimination proved, **and independently re-verified by the owning session**: warnings fire on exactly the three malformed shapes, `myscope.myvar` is silent (false-positive guard holds), all five variables install at unchanged addresses. Behaviour non-regression proved by byte-identical `--show-vars`/`--show-classes` diffs. `classes` confirmed NOT affected (canonified, not scope-parsed) | — (Jira only now) | **done** [cfengine/core#6317](https://github.com/cfengine/core/pull/6317) — [CFE-4722](https://northerntech.atlassian.net/browse/CFE-4722), comment 159446 |
| B-20 | **A JSON `null` value in `host_specific.json` segfaults `cf-promises` and `cf-agent`.** Valid JSON, passes CFEngine's own unresolved-variable check. `JsonPrimitiveToString()` returns NULL for `JSON_PRIMITIVE_TYPE_NULL`; `AddCMDBVariable()` (`cmdb.c:136`) passes it straight in as the value → `RvalNewRewriter` → `xstrdup(NULL)` → `strlen(NULL)`. Agent dies in `GenericAgentDiscoverContext()` **before any promise is evaluated**, so the host falls to failsafe — same severity class as B-10. Found while edge-case-testing B-5a; **confirmed pre-existing on master by rebuilding with unpatched `cmdb.c`** | core | **done** `87490bb8f`. Two guards in `AddCMDBVariable()` plus a `JsonArrayContainsNull()` helper. **Skip-with-error, not reject-the-section** — verified against the file's own idiom, which `continue`s for every per-entry problem and reserves `return false` for section-level structural faults. Six inputs fixed, incl. two silent-corruption cases (`[1, null]` installed `{"1"}`; `[null]` installed an empty slist). Nulls inside data containers deliberately untouched (they render correctly); `classes` already safe because `JsonPrimitiveGetAsString()` returns the literal `"null"` | **done** [`fix/cmdb-null-value-crash`](https://github.com/djbclark/core/tree/fix/cmdb-null-value-crash) | — (Jira only now) | *not panelled* — Opus 5 subagent; discrimination proved with the stale-library trap defeated, and the unpatched rebuild confirmed to genuinely segfault (rc=139) first. Test pins skip-and-continue semantics, not merely absence of a crash | — (Jira only now) | **done** [cfengine/core#6316](https://github.com/cfengine/core/pull/6316) — [CFE-4738](https://northerntech.atlassian.net/browse/CFE-4738), comment 159445 |
| B-21 | **The augments loader (`def.json`) has the same null-crash root cause**, at three sites in `libpromises/generic_agent.c`: `:454` (`vars`), `:606` (`variables` — note `{"value": null}` is *safe* there, that path has a `NULL_JSON` guard `cmdb.c` lacks) and `:723` (`classes`, NULL into `CheckContextClassmatch()`). The array paths `:749`/`:792`/`:874` are safe because `JsonIteratorNextValueByType(..., skip_null=true)` filters nulls. Found while fixing B-20 | core | **done** `dd917f09d`, cut from upstream master `a0bca6aaf`. Five guards added in `LoadAugmentsData()`, following B-20's `cmdb.c` idiom exactly (skip-with-error-and-continue, not reject-the-section): the three scalar crash sites (`vars`, `variables` bare form, `classes`) plus the `vars`/`variables` array-truncation sites (`RlistFromContainer()` silently drops nulls, same non-crashing defect class B-20 also fixed). New file-local `JsonArrayContainsNull()` helper, verbatim copy of B-20's. Discrimination proved by hand, not asserted: unpatched rebuild (forced full `libpromises` relink, not just recompile) gave a real SIGSEGV (rc=139) loading the new test's `def.json`; patched rebuild passes it plus all 21 other tests in `00_basics/def.json/`, zero regressions | **done** [`fix/def-json-null-crash`](https://github.com/djbclark/core/tree/fix/def-json-null-crash) | — (Jira only now) | **done** — 1-seat panel (grok-4.6) on a disposable `cp -a` copy; gemini's seat failed twice in this environment (sandbox couldn't see the filesystem at all, unrelated to the code) so this is single-reviewer, weighted per [[panel-reviewer-weighting]]. SHIP: no leaks on the five early-return paths (verified against a memory-allocated/freed table for each), no missed null-crash site left in the function, `{"value": null}` confirmed already-safe pre-existing via `NULL_JSON()`, `--show-vars` survivor ordering matches `SeqSort()`. **grok independently surfaced a sixth site**: the `"inputs"` array has the identical `RlistFromContainer()` truncation defect (not a crash) as the two array sites already fixed; folded into this same commit rather than filed separately, matching B-20's own decision to bundle scalar+array fixes together | — (Jira only now) | **done** [cfengine/core#6319](https://github.com/cfengine/core/pull/6319) — [CFE-4739](https://northerntech.atlassian.net/browse/CFE-4739), comment 159449 |
| B-22 | **Not a bug — `libutils/mustache.c` (916 lines, sole entry point `MustacheRender()`) had zero unit test coverage**, flagged by B-13's review panel as a follow-up. `cfengine/core` has its own `mustache_test.c` + JSON spec fixtures, but they cover only comments/interpolation/sections/inverted/delimiters, none of the CFEngine-specific extensions | libntech | **done** — 17 cmocka cases (~90 assertions): variables (incl. whitespace-padded tags, ints, bools), missing/null/non-object/NULL hash, HTML escaping plus both unescaped forms, dotted names, comments (incl. CRLF), boolean/array/object/inverted sections, the CFEngine extensions `{{.}}`/`{{@}}`/`{{%x}}`/`{{$x}}`/`{{-top-}}`, delimiter changes, standalone-tag line removal, malformed templates, empty input. Wired into `tests/unit/Makefile.am` | **done** [`test/mustache-coverage`](https://github.com/djbclark/libntech/tree/test/mustache-coverage) | — (Jira only now) | **done** — built under `-Werror -Wextra -Wall` and separately under `-fsanitize=address`, both clean; `make check` 40/40 binaries pass | — (Jira only now) | **done** [NorthernTechHQ/libntech#296](https://github.com/NorthernTechHQ/libntech/pull/296) — pure coverage addition, no behavior change | — (test-only, no ticket) |
| B-23 | **Two minor defects in `mustache.c`, found while writing B-22's tests.** `:284,297` use `%20s` (min width) where `%.20s` (truncate) was meant, per the trailing `"..."` — short strings get left-padded, long ones dump the whole remaining template into the log. `IsTagStandalone()` (`:74`) forms `tag_start - 1` when a non-renderable tag starts at offset 0 (exercised by the existing `"{{#b}}yes{{/b}}"` case), pointing one before the input buffer — never dereferenced, so no observed failure under UBSan pointer-overflow or ASan, but UB to construct regardless | libntech | **done** — `%.20s` fix; guard added so the out-of-bounds pointer is never formed | **done** [`fix/mustache-minor-defects`](https://github.com/djbclark/libntech/tree/fix/mustache-minor-defects) — stacked on B-22 | — (Jira only now) | **done** — reverted-then-restored the `%20s` fix and observed the log-padding difference directly (padding present unpatched, absent patched); UB fix has **no reproducing failure mode** — stated plainly in the PR rather than claimed as verified | — (Jira only now) | **done** [NorthernTechHQ/libntech#298](https://github.com/NorthernTechHQ/libntech/pull/298) — stacked on #296 | [CFE-4740](https://northerntech.atlassian.net/browse/CFE-4740) |
| B-8 | `commands:` promise that exceeded `exec_timeout` is reported **compliant** — `RepairExec()` never returns `ACTION_RESULT_TIMEOUT`, so the promise is judged only on the child's exit status. **This is the actual fail-open**; B-1 only narrows its window. (Said "reported **kept**" until 2026-08-17; the panel's correction is that the default outcome for exit 0 is *repaired*, so the accurate word is **compliant** — 100% aggregate, `promise_repaired` set, `repair_timeout` not set, `PromiseResultIsOK()` true. Defect unchanged, our label was wrong) | core | **done** `326bcdb8d` + `7a32e3969` + `57ac8da22`, plus five acceptance tests in `46be075d4` | **done** [`fix/exec-timeout-promise-result`](https://github.com/djbclark/core/tree/fix/exec-timeout-promise-result) | **done** [#6](https://github.com/djbclark/core/issues/6) | **done** — its own 3-model panel (cursor/gemini/grok, 2026-08-16); grok found a real defect in the fix (the flag was sampled before `cf_pclose`), fixed in `7a32e3969`, and caught the unconditional "and was terminated" wording, fixed in `57ac8da22` | **done** — `security@` 2026-08-17, Gmail id `1a00d22ac0d46c9b`, + correcting follow-up `1a00d44a2758b9ea` carrying the retracted ALARM_PID refutation | **done** [cfengine/core#6299](https://github.com/cfengine/core/pull/6299) — OPEN, MERGEABLE, 2 commits, branch [`fix/exec-timeout-promise-outcome`](https://github.com/djbclark/core/tree/fix/exec-timeout-promise-outcome) cut from master `17eb78e6d`, trailers `Ticket: CFE-4726` + `Changelog:`. Byte-identical tree to `fix/exec-timeout-promise-result`, recommitted in the project's own style (past-tense subjects) with the two review defects squashed into the fix rather than shipped as separate correcting commits. PR body states all three known limits up front | [CFE-4726](https://northerntech.atlassian.net/browse/CFE-4726) |
| P-1 | Retain the changes chroot after a `--simulate` run (feature) | core | **done** `f6c06f9e2` (corrected 2026-08-17) | `simulate-keep-chroot` | **done** [#2](https://github.com/djbclark/core/issues/2) | *not done* | — not emailed; went straight to an upstream PR (operator, 2026-08-15). Verified 2026-08-17: only four threads to northern.tech exist and none concerns `--simulate` | **DONE** [cfengine/core#6293](https://github.com/cfengine/core/pull/6293) — open, mergeable, CLA signed |
| P-2 | `--simulate-json`: machine-readable rendering of the change set (feature) | core | **done** `b3a6c3da5` (corrected 2026-08-17) | `simulate-json` | **done** [#3](https://github.com/djbclark/core/issues/3) | *not done* | — not emailed; went straight to an upstream PR (operator, 2026-08-15). Verified 2026-08-17: only four threads to northern.tech exist and none concerns `--simulate` | **DONE** [cfengine/core#6294](https://github.com/cfengine/core/pull/6294) — open, mergeable, CLA signed |
| P-3 | Silent digest-initialization failure when hashing | libntech | **done** `e76700b` (was `dc85a6f`; corrected 2026-08-17) | `silent-digest-failure` | **done** [libntech#1](https://github.com/djbclark/libntech/pull/1) (PR) + [libntech#3](https://github.com/djbclark/libntech/issues/3) (issue) |  **done** — panel + fable adjudication, correction pushed `e76700b` | **done** (operator, manually) | **DONE** [NorthernTechHQ/libntech#290](https://github.com/NorthernTechHQ/libntech/issues/290) (issue) + [#291](https://github.com/NorthernTechHQ/libntech/pull/291) (PR) — open, mergeable, CLA signed |

`djbclark/core` [#7](https://github.com/djbclark/core/issues/7) tracks the
unmerged-libntech submodule dependency, and
[#1](https://github.com/djbclark/core/issues/1) is the
investigation trail behind P-1/P-2 and is not itself a defect.

B-2 through B-7 are described, measured and sourced in
[`cfengine-upstream-candidates-2026-08-16.md`](cfengine-upstream-candidates-2026-08-16.md);
B-1's full evidence is in
[`cfengine-exec-timeout-filing-package-2026-08-16.md`](cfengine-exec-timeout-filing-package-2026-08-16.md).

### Cite branch heads, not remembered SHAs

All three P-item SHAs in the table above were **wrong** until 2026-08-16, in the
same way: the commit was amended after the SHA was written down, so the register
pointed at a commit that no branch reaches. The content was identical each time
— only the message differed (P-3's amend replaced `Ticket: CFE-XXXX` with
`Ticket: #290`) — which is exactly why it went unnoticed: every diff-based check
passes, and only `git branch --contains` reveals it.

| item | register said | corrected to | current head |
|---|---|---|---|
| P-1 | `5dbd295f6` | `00c98bc8b` | **`f6c06f9e2`** — `ea439e0ad` stripped `Ticket: #6295`, 2026-08-17 **restored** it, then `64e2ac1cb` → `f6c06f9e2` carried the panel corrections and retrailered to `Ticket: CFE-4715` |
| P-2 | `071f85987` | `8ee015c42` | **`b3a6c3da5`** — `f5ce3a35d` stripped `Ticket: #6296`, 2026-08-17 **restored** it, then `05e18f038` → `b3a6c3da5` carried the panel corrections and retrailered to `Ticket: CFE-4716` |
| P-3 | `da7d3d9` | `dc85a6f` | **`e76700b`** (2026-08-17 correction: added the test, fixed the false no-test claim and the TLS overstatement) |

P-1 and P-2 moved *again* within hours of the correction, which is the point:
these SHAs are not stable and citing them is a maintenance liability.

The check that catches this, run against any SHA this document cites:

```sh
git branch -a --contains <sha>     # empty output = orphaned, the citation is dead
```

Prefer citing the **branch name** and resolving the head on demand. A SHA is
only worth pinning when the point being made is about that specific commit.

### Upstream CI on libntech#291

`mender-test-bot` posted *"There was an error running your pipeline"* on
[#291](https://github.com/NorthernTechHQ/libntech/pull/291), but **no check
status was ever reported** (`gh pr checks 291` → "no checks reported";
the combined status API returns `total_count: 0`). The linked log is a private
GCP console URL we cannot read. So this is unattributable from outside and is
most likely Northern.tech infrastructure rather than our patch — but it is
**not evidence that our patch passes CI**, and nothing in this register should
claim it does.

### 2026-08-18 — FIRST MAINTAINER ENGAGEMENT, on two PRs the same day

After weeks in which every open PR drew nothing but `CLAassistant`,
`mender-test-bot` and our own comments, two real Northern.tech maintainers
reviewed on 2026-08-18. **The "zero maintainer engagement" line that ran
through every prior session's notes is now false and must not be repeated.**

- **[libntech#291](https://github.com/NorthernTechHQ/libntech/pull/291) —
  `larsewi`, 10:51Z**, a substantive review: return `bool` from
  `HashFile_Stream`/`HashFile`; also check `EVP_DigestUpdate`/
  `EVP_DigestFinal_ex`; why did `HashBasicInit()` move; the test "seems a bit
  overkill for an error path that should never happen — how did you come
  across it?"; and **shorten the commit message**.

  All addressed and force-pushed as `8023f452a` (was `4642a502f`), reply
  [`#issuecomment-5330023350`](https://github.com/NorthernTechHQ/libntech/pull/291#issuecomment-5330023350).
  Commit message cut **70 lines → 19**.

  **`HashPubKey` was deliberately NOT converted**, and the reason is load-
  bearing: `cfengine/core` redefines it as `void` in three places
  (`tests/unit/lastseen_test.c:676`, `tests/unit/lastseen_migration_test.c:279`,
  `tests/load/lastseen_load.c:98`), so a signature change breaks core's build
  until a matching core PR lands. `HashFile` has **no** such stubs — verified
  for real by dropping the patch into core's vendored libntech, force-rebuilding
  all ten `HashFile` callers plus core's `tests/unit`, clean, then restoring the
  submodule.

  Provenance given to larsewi, corrected by the operator mid-session: this was
  **not** static analysis and **not** a field incident — it was hit while
  building the `--simulate` work now open as `#6293`/`#6294`, writing unit tests
  for a schema linter over that output, with hashes silently all-zero. Earlier
  drafts framed it as an audit finding; that framing was wrong.

- **[cfengine/core#6305](https://github.com/cfengine/core/pull/6305) —
  `nickanderson`, 12:28Z**, one inline note on `cf-agent/verify_exec.c:454`:
  *"It feels a bit comment heavy. Probably 'terse' comments will be sufficient
  in most cases."* Trimmed across the whole diff as `0e06ad3d7` (−37 lines,
  comment volume roughly halved), left as a **separate** commit so his thread
  stays anchored, with an offer to squash. Proved comment-only by comparing the
  comment-stripped token stream: byte-identical in all four files.

**Both reviewers independently asked for less verbosity.** With the earlier
"be terse" feedback that is three data points on one axis — treat word volume
as a defect, in commit messages, comments and PR replies alike.

### 2026-08-18 — the acceptance suite does not run on this machine

`tests/acceptance/testall` needs `fakeroot`, which is not installed: a run
reports **0 passed / 0 failed / 2558 skipped** and exit 0. That is a vacuous
green. Do not cite an acceptance run as evidence here without checking the
passed count is non-zero.

## Blocked on

- **Email — the remaining gate for B-1, B-2 and B-8.** Emailing is **not
  optional**: operator, 2026-08-16, *"It is 100% needed to email the addresses I
  gave you for each bug, or set of bugs, we post issues and tickets for in our
  local repo."* Our fork issues are public only in a personal repository nobody
  is likely to find, so posting there is **not** disclosure and does not
  discharge the duty to tell upstream.

  The transport blocker is **cleared**: the Claude Gmail connector
  (`mcp__claude_ai_Gmail__*`) is visible to a session started after the operator
  set it up. `hermes send` still has no mail transport (Discord, Signal,
  Telegram only) and Composio is not the canonical path.
- **Second opinions — DONE for B-1 and B-2** (2026-08-16). Panel of three
  non-Claude CLIs, brief frozen at
  [`UPSTREAM-B1-B2-REVIEW-BRIEF.md`](UPSTREAM-B1-B2-REVIEW-BRIEF.md), opinions
  at `upstream-opinion-{cursor,gemini,grok}-2026-08-16.md`, reconciled in
  [`upstream-b1-b2-reconciliation-2026-08-16.md`](upstream-b1-b2-reconciliation-2026-08-16.md).
  It paid for itself: it refuted B-1's headline claim, caught a hang B-2
  introduced, and turned up B-8. `#4` and `#5` are updated. ~~**B-8 still needs
  its own second opinion before its email**, per the standing rule — it was
  found *by* this panel, not reviewed by it.~~ **Discharged**: B-8 got its own
  3-model panel (cursor/gemini/grok, 2026-08-16), which found a real defect in
  the fix, and the email went 2026-08-17.
- **Which address.** All three go to **security@northern.tech**. B-8 is the
  fail-open — a check whose verification timed out is reported as satisfied.
  B-1 is the timing defect that narrows B-8's window and was originally filed
  as the fail-open itself; it travels with B-8 because the correction only
  makes sense alongside it. B-2 is availability-shaped (unbounded wait plus a
  leaked process), and the operator's rule is *if in doubt, security@*. An
  earlier draft of this register said B-2 goes to contact@, and separately
  argued B-1 could go to contact@ because the fork issue was already public;
  both were **wrong** and are superseded by the operator's instruction.
- **OPEN — a timed-out command is not always terminated. Mechanism SUPPORTED,
  and my earlier "refuted" verdict is RETRACTED.** A command that closes its
  output and then outlives `exec_timeout` runs to completion: `exec 1>&- 2>&-;
  sleep 10; exit 0` under `exec_timeout => "2"` takes ~10.2s on **stock
  3.27.1**. Gemini and Grok independently diagnosed `cf_pclose()` clearing
  `ALARM_PID` before `cf_pwait()`, so `TimeOut()` fires with nothing to signal.
  I implemented that change, saw no wall-clock movement, and **wrongly recorded
  the theory as refuted**. Grok supplied the discriminator I missed: the two
  branches of `TimeOut()` log differently, and this case prints `verbose: >
  Time out`, which **is** the `ALARM_PID == -1` branch — confirmed on our own
  build. **Start from the ALARM_PID theory; do not avoid it.** What was wrong
  with my experiment is not yet known. The *reporting* half is closed
  ([#6](https://github.com/djbclark/core/issues/6)); this is the *termination*
  half and is not yet filed as its own issue.
- **libntech submodule pointer stays uncommitted in `~/src/cfengine-core`** —
  not an external rule, and earlier notes overstated it as "required". The
  reason: the checkout sits at `dc85a6f` ("Handle digest initialization failure
  when hashing"), our own P-3 fix, which exists only on `fork/silent-digest-failure`
  and is **not upstream**. `cfengine/core` records `5b5d04e1`. Committing the
  bump would put an unresolvable submodule reference into every core branch we
  offer upstream and entangle two contributions meant to land separately.
- **Unmerged libntech dependency — [core#7](https://github.com/djbclark/core/issues/7).**
  Our core branches are built and tested against libntech `dc85a6f` (our P-3
  fix, `fork/silent-digest-failure`, offered as libntech PR #1 and not merged),
  while upstream records `5b5d04e1`. Before any core branch is offered upstream
  it must be confirmed to build and pass against **stock** libntech. **Done for
  B-8 and B-1** (2026-08-17): the `core-acceptance` worktree carries the stock
  submodule pointer `5b5d04e1` — exactly what upstream master `17eb78e6d`
  records — and both `#6299` (built `rc=0`, five acceptance tests green) and
  `#6300` (built `rc=0`/0 warnings, `tests/unit` 64 PASS + 4 XFAIL) were
  verified against it, each with its discrimination run done at the same
  pointer. **Not yet done for B-2.** The tracking issue lives on `djbclark/core`
  because that is where the submodule pointer bites.
- **B-10's panel is partly in. gemini: *ship as is*, severity `security@`** —
  it argues "attacker-controlled" is accurate, since CMDB facts, external data
  sources and `readjson()` inputs can be populated by unprivileged users or
  third-party systems, so a crafted number is a persistent denial of service.
  It confirmed our unverified belief that core's `rlist.c` and `iteration.c`
  are twins, and **found a site we had missed**:
  `libpromises/generic_agent.c:2051` reads `"timestamp"` from the
  policy-validated file through `JsonPrimitiveGetAsInteger()`. Confirming that
  turned up **a second one gemini also missed**, `libenv/unix_iface.c:1440`,
  which reads a route `"metric"` the same way. Both fixed in core `367c27fc5`
  — these two genuinely want an integer, so the repair is a non-fatal
  conversion rather than keeping the text: an unreadable timestamp means "not
  validated" and an unreadable metric simply does not win. gemini's one test
  gap — `JsonSelect()` with an oversized all-digit index — is closed in
  libntech `76856ee`.

  **cursor: *ship with changes*,** four of them, agreeing the three crashes are
  real and the fixes hold under measurement. Two are already done: the
  `JsonSelect` overflow test (`76856ee`), and its warning not to treat this as
  closing CFEngine because `rlist.c`/`iteration.c` still die until
  `fix/json-number-rendering` lands. **Two remain open:** pin `1e400` → `inf`
  versus lexeme in a test, whichever we actually mean; and say plainly, in the
  filing and the email, that exponent *reals* still render through `%.2f`, so
  `1e-8` mustaches to `0.00`, not `1e-8`. That last one matters — the fix turns
  a fatal into a *lossy* result, and claiming otherwise would repeat exactly
  the overstatement the P-3 panel caught us in.

  **grok: *ship with changes*, severity `security@`** — the panel is now
  **COMPLETE** (fable-deep, gemini, cursor, grok). Consensus severity is
  `security@` on availability, and grok sharpened the threat statement in a way
  the filing should adopt verbatim: *"attacker-controlled" is overstated for a
  remote exploit; it is honest for a CMDB operator, a `readjson()` of
  third-party JSON, or an author who writes scientific notation by mistake.*
  A primitive `1e-8` in `def.json` or `host_specific.json` is enough to make
  `cf-promises` exit before any promise body runs.

  **grok found one thing nobody else did, and it is a real defect, not a
  disclosure item: `1e400` now renders as `inf`, which is not JSON.**
  `JsonWriteCompact()` still emits `1e400`, so render and serialise disagree
  again — the exact class of inconsistency this whole change set exists to
  remove. Earlier reviewers waved `inf` through as "acceptable but disclose";
  grok is right that emitting a non-JSON token is worse than that.

  **CORRECTION (2026-08-17, measured):** the paragraph above — and grok's and my
  own framing of it — is wrong about *when* `inf` happens. Stock does **not**
  render `1e400` as `inf`: with no decimal point it is misclassified INTEGER and
  **terminates the process**, never reaching `strtod()`. `inf` appears only once
  B-10's classification fix routes the value into the REAL path. So `inf` is
  **introduced by B-10 applied alone** and **removed by B-4** (which stops going
  through `double` at all). It is not a third patch to write; it is a statement
  about landing order. Full three-variant measurement:
  [`b10-number-render-measurement-2026-08-17.md`](b10-number-render-measurement-2026-08-17.md).

  ### B-10's remaining work before it goes upstream or to `security@`

  All four are now **closed**; see the measurement document for the evidence.

  1. ~~**Fix `1e400` → `inf`**~~ — **resolved as a landing-order question, not a
     patch.** `JsonPrimitiveGetAsReal()` is the only route to `strtod()` here and
     has exactly **two** in-tree callers, both of which B-4 rewrites, and **zero**
     callers in core. Once B-4 lands nothing in either tree can produce `inf`
     from parsed JSON.
  2. ~~**Say plainly that exponent reals still render through `%.2f`**~~ —
     **measured and written down.** B-10 alone renders `1e-8` as `0.00`. But the
     fair framing is narrower than "B-10 leaves a silent wrong value": `%.2f`
     truncation is a **pre-existing stock defect** (`0.00049` → `0.00` today,
     unpatched). B-10 moves exponent forms out of a *fatal* path into an
     *already-broken* lossy one. The filing must not imply they now render
     correctly.
  3. ~~**Add mustache coverage**~~ — **confirmed there is none to extend.** No
     file under `tests/unit/` references `MustacheRender` at all, so
     `libutils/mustache.c` has **zero** unit coverage. Correct move is a
     proposal in the filing plus an offer of a separate `mustache_test` PR — not
     an invention inside this one.
  4. **Verify the core twin branch** `fix/json-number-rendering` — in progress;
     `~/src/core-json` is now configured and building against **stock** libntech
     `5b5d04e1`, which is the honest configuration since core's PR lands
     independently of the libntech one.

  ### The two libntech branches are NOT independent — measured

  Applying `fix/json-real-precision` on top of `fix/json-number-fatal-exit`
  **breaks the latter's own test suite**: `json_test.c:1336` asserts
  `assert_string_equal("0.50", str)`, pinning the `%.2f` rendering of `0.5`.
  With B-4 applied that becomes `"0.50" != "0.5"` and `json_test` exits 1
  (verified 2026-08-17, then reverted; tree clean, 39/39 restored).

  Whichever branch lands second must update that assertion. `cfengine/core`'s
  half (`6a4216dad`) already avoids the whole problem by fixing integers **and**
  reals together in one commit; the libntech half is the only one split in two.
  **Recommendation: land B-4 first, or stack B-10 on it.**
- **Two defects, four call sites, two repositories — and neither half is
  sufficient alone.** B-4 and B-10 are the same underlying mistake: *rendering a
  JSON number by converting it to a C numeric type and formatting it back,
  instead of using the text the parser already kept.* It appears at four sites
  reached by different routes, so fixing one repository leaves the other live:

  | site | repo | reals | integers | reached by |
  |---|---|---|---|---|
  | **`JsonPrimitiveCopy()`** | libntech | `%.4f` | **fatal** | **every variable store** — see below |
  | `JsonPrimitiveToString()` | libntech | truncated | fatal | rendering |
  | mustache renderer | libntech | truncated | fatal | `string_mustache()` |
  | `RlistAppendJson()` | core | truncated | fatal | list contexts |
  | iteration equivalent | core | truncated | fatal | `$(container[key])` |

  **CORRECTION (2026-08-17): the table above was missing its most important
  row, and the framing around it was wrong.** `JsonPrimitiveCopy()` is a fifth
  site and it is not a rendering path at all — storing a JSON container as a
  CFEngine variable deep-copies it, so the conversion happens on **every
  variable store**. Measured against a build carrying core's half and stock
  libntech: a policy whose only content is
  `"d" data => readjson(...)` — no iteration, no mustache, nothing that renders
  the value — kills `cf-promises` at **policy-load time** and sends `cf-agent`
  to failsafe. `lldb` stack: `LoadPolicy` → `PolicyResolve` →
  `ExpandPromise` → `VerifyVarPromise` → `RvalNewRewriter` → `JsonObjectCopy`
  → `JsonCopy` → `StringToLongExitOnError`. The trigger is therefore **loading
  the value, not rendering it**, and the whole path is inside libntech — core's
  half cannot help. Details:
  [`b10-number-render-measurement-2026-08-17.md`](b10-number-render-measurement-2026-08-17.md).

  mustache reaches JSON data by a different path than variables and iteration
  do, which is why the core half was invisible while measuring the libntech
  half. **The core half is committed but NOT behaviourally verified** — the
  build machine was saturated — and must not be offered upstream until it is.
- **P-3's panel has reported, unanimously: push a correction.** cursor, gemini
  and grok all say the 21-line C patch itself holds — none could break the
  control flow, the free handling or `hash_test`. What is wrong is the *package*
  already in front of maintainers on
  [#291](https://github.com/NorthernTechHQ/libntech/pull/291):
  **(a)** the claim that this cannot be unit-tested without core's
  `CryptoDeInitialize()` is **false** — cursor and grok independently forced
  `EVP_DigestInit` to fail from a libntech-only harness (symbol override, and
  an OpenSSL 3 provider drain), so the PR carries a false statement *and* is
  missing a test it could have; **(b)** "feeds the TLS paths" overstates it —
  peer TOFU uses `HashNewFromKey()`, which already fails closed; **(c)** gemini
  alone adds that the patch ignores `EVP_DigestUpdate`/`EVP_DigestFinal`
  failures in the very same functions. Severity is split 2–1 for ordinary bug
  over `security@`.
- **DONE 2026-08-17 — P-3's correction is pushed.** The fable adjudication that
  gated this did report: it is
  [`upstream-p3-reconciliation-2026-08-16.md`](upstream-p3-reconciliation-2026-08-16.md),
  which sustained "push a correction, do not withdraw" and settled severity at
  **ordinary bug, not `security@`** — the zero digest is a colliding *lookup
  handle*, not a bypassed *cryptographic gate*. Executed its §5 in full:
  `dc85a6f` → **`e76700b`** on `fork/silent-digest-failure`, force-pushed with
  a lease; [#291](https://github.com/NorthernTechHQ/libntech/pull/291) is still
  **open and mergeable** on the new head, now a single commit. The C change is
  **byte-identical** to what the panel reviewed — only the message and the test
  moved. PR body rewritten to match the commit; force-push explained in a PR
  comment; #290's "worst-case impact" paragraph corrected by comment rather
  than a silent body edit. No email, per §5F.

  The test the PR falsely said was impossible now exists:
  `tests/unit/hash_init_fail_test.c`, a **dedicated program** because the
  provider drain stops working once any EVP digest has run. Verified in both
  directions — 40/40 on the branch, and **exit 3, all three cases failing**,
  against the unfixed file.

  **One thing the adjudication did not catch, found by measuring:** the WIP
  draft's `HashFile`/`HashPubKey` cases asserted only the zeroed digest, which
  is *pre-existing* behaviour — they passed against unpatched code, so 2 of 3
  cases were decorative. The patch's only contribution for those two is the log
  message. The adjudication suggested `StartLoggingIntoBuffer()`, but its
  buffer is `static` with no public reader; `Log()` writes to **stdout** here,
  so the test captures that with `dup2` and asserts the message. That is what
  took it from 1-of-3 to 3-of-3 discriminating.

  **The adjudication's §5F was also wrong, and it cost a follow-up.** It said
  "No `security@` mail, no maintainer email. Verified: the 2026-08-16 security@
  email covered B-1/B-2/B-8 only; P-3 was never emailed, so there is no prior
  private characterization to correct." **P-3 was emailed** — Gmail thread
  `1a007e4362402bd9`, sent to `contact@northern.tech` 2026-08-16T00:06Z and
  re-sent to `contact@` + `security@` at 00:10Z. That mail reproduces #290 in
  full, including **both** claims the panel retracted: the "no unit test is
  possible" paragraph and an impact list stating the digest "is included by
  `libcfnet/tls_generic.c` and `libcfnet/client_protocol.c`".

  Correcting follow-up sent on that thread 2026-08-17, Gmail id
  `1a00fb936fc1741f`: both retractions, the severity downgrade stated
  explicitly *because* it reached `security@`, and the note that `da7d3d9` has
  been superseded twice. It also credits the half of that sentence which was
  **right** — that a libntech test "could only assert the all-zero digest that
  is returned either way" — since that is exactly the defect found in the WIP
  test above.

  **Method note:** §5F's error is the same shape as the `#6295` one below —
  a confident negative from a check that could not have seen the thing it ruled
  out. Verify claims about what was sent against the mail store, not against
  notes.
- **RESOLVED 2026-08-16 — P-1 and P-2 cited ticket numbers that did not exist.**
  `00c98bc8b` carried `Ticket: #6295` and `8ee015c42` carried `Ticket: #6296`;
  both **404** against `cfengine/core`, which has issues disabled and could not
  have had such tickets. They appear to have been guessed as "the next numbers
  after our PRs". Because those commits were the heads of live upstream PRs, a
  maintainer reading either one saw a dangling reference.

  Neither commit carried a `Changelog:` line, and per `CONTRIBUTING.md`
  (corroborated by 23 of the last 60 libntech commits) `Ticket:` is only
  required alongside `Changelog:` — so the repair was to **drop the trailer**,
  not to invent another number. Done with the operator's approval:
  messages rewritten with `git commit-tree` so no working tree was touched,
  trees verified byte-identical, force-pushed with `--force-with-lease`.
  `00c98bc8b` → `ea439e0ad`, `8ee015c42` → `f5ce3a35d`; both
  [#6293](https://github.com/cfengine/core/pull/6293) and
  [#6294](https://github.com/cfengine/core/pull/6294) confirmed still **open
  and mergeable** on the new heads.

  Contrast P-3, which got this right: `Ticket: #290` resolves to a real upstream
  issue. **The rule this leaves behind: never write a ticket trailer for a
  ticket you have not seen exist.**

  **OVERTURNED 2026-08-17 — the trailers were correct and we should not have
  removed them.** `#6295` and `#6296` are **real**, and they are ours:

  | | title | author | created |
  |---|---|---|---|
  | [6295](https://github.com/cfengine/core/discussions/6295) | Retain the `--simulate` changes chroot after a run (`--simulate-keep-chroot`) | `djbclark` | 2026-08-16T00:47Z |
  | [6296](https://github.com/cfengine/core/discussions/6296) | Write the `--simulate` change set as JSON (`--simulate-json`) | `djbclark` | 2026-08-16T00:48Z |

  They are **Discussions**, not Issues — which is precisely what a repository
  with issues disabled uses instead, and the operator opened them the same
  evening the PRs went up. They are the feature requests P-1 and P-2 implement.

  The verification that condemned them was
  `gh api repos/cfengine/core/issues/<n>`, which 404s on a discussion no matter
  how real it is. From that 404 this document concluded the numbers "appear to
  have been guessed as the next numbers after our PRs" — a fabricated motive
  for a correct reference. On that basis two live upstream PRs had their
  history rewritten to strip accurate metadata.

  The rule survives; the **method** was wrong. Restated: *never write a ticket
  trailer for a ticket you have not seen exist — and when the repository has
  issues disabled, look for a Discussion before concluding it does not exist.*

  ```sh
  gh api graphql -f query='query{repository(owner:"cfengine",name:"core"){
    discussion(number:6295){title closed}}}'
  ```

  Note also that `site-djbclark`'s `track-issue-activity.yml` has been tracking
  both of them as `type: discussion` and succeeding hourly throughout — the
  evidence was already in our own tooling while this document called them
  phantoms.

  **REPAIRED 2026-08-17** (operator approved). `Ticket: #6295` / `#6296`
  restored, and the `Changelog: Title` line they should have carried alongside
  added — the titles are already past-tense, user-facing feature descriptions,
  which is what `CONTRIBUTING.md` asks for. Rewritten with `git commit-tree`, so
  no working tree moved and `cfengine-core` stayed on `tendcf-integration` with
  its submodule untouched; **both trees verified byte-identical** before the
  push, and both refs updated with an explicit old-value guard.

  `ea439e0ad` → **`64e2ac1cb`** ([#6293](https://github.com/cfengine/core/pull/6293)),
  `f5ce3a35d` → **`05e18f038`** ([#6294](https://github.com/cfengine/core/pull/6294)).
  Both **open, mergeable, one commit**. Each PR body gained the
  "Requested in #6295/#6296" line it never had, and each carries a comment
  explaining the churn and stating plainly that the 404 was my error and no code
  changed in either direction.
- **RESOLVED 2026-08-17 — Jira works, and every open item is now filed there.**
  The blocker was never the token. Creating the Atlassian account was not
  sufficient on its own: the operator also had to be granted permission **in
  the CFE project specifically**, which nickanderson arranged over Matrix.
  `GET /rest/api/3/myself` → 200 and `POST /rest/api/2/issue` → 201.

  Auth is Basic, `djbclark@gmail.com` + `ATLASSIAN_CFENGINE_API_TOKEN` via
  `sudo-secretspec` (never echo it). Project **CFE** ("CFEngine Community");
  issue types include `Bug` and `Feature request`; only `summary` and
  `description` are required. Descriptions go through `/rest/api/2/` so they
  can be wiki markup rather than ADF.

  **CFE is fully public and offers no restricted-visibility option** — anonymous
  `GET` of an issue returns 200, and the create screen has no `security` field.
  The operator was asked and chose to file the six `security@`-reported items
  publicly anyway (2026-08-17).

  | item | CFE key | item | CFE key |
  |---|---|---|---|
  | P-1 `--simulate-keep-chroot` | [CFE-4715](https://northerntech.atlassian.net/browse/CFE-4715) | B-5b one bad key drops all vars | [CFE-4720](https://northerntech.atlassian.net/browse/CFE-4720) |
  | P-2 `--simulate-json` | [CFE-4716](https://northerntech.atlassian.net/browse/CFE-4716) | B-6 `eval()` returns `%lf` | [CFE-4721](https://northerntech.atlassian.net/browse/CFE-4721) |
  | P-3 silent digest failure | [CFE-4717](https://northerntech.atlassian.net/browse/CFE-4717) | B-7 dotted CMDB keys | [CFE-4722](https://northerntech.atlassian.net/browse/CFE-4722) |
  | B-3 no `process_darwin.c` | [CFE-4718](https://northerntech.atlassian.net/browse/CFE-4718) | B-12 `lowest_metric` unassigned | [CFE-4723](https://northerntech.atlassian.net/browse/CFE-4723) |
  | B-5a rejected CMDB names nothing | [CFE-4719](https://northerntech.atlassian.net/browse/CFE-4719) | **B-4 + B-10 + B-11** (one stack) | [CFE-4724](https://northerntech.atlassian.net/browse/CFE-4724) |
  | B-10 core half (`core#13`) | [CFE-4725](https://northerntech.atlassian.net/browse/CFE-4725) | B-8 fail-open | [CFE-4726](https://northerntech.atlassian.net/browse/CFE-4726) |
  | **B-17** exec_timeout termination half | [CFE-4727](https://northerntech.atlassian.net/browse/CFE-4727) | B-1 poll loops count iterations | [CFE-4728](https://northerntech.atlassian.net/browse/CFE-4728) |
  | B-2 descendants not signalled | [CFE-4729](https://northerntech.atlassian.net/browse/CFE-4729) | **B-13** libntech JSON codec non-conformant | [CFE-4730](https://northerntech.atlassian.net/browse/CFE-4730) |
  | **B-14** JSON parser double-decodes escapes | [CFE-4731](https://northerntech.atlassian.net/browse/CFE-4731) | **B-15** `ReconcileMountOptions()` never disarms | [CFE-4732](https://northerntech.atlassian.net/browse/CFE-4732) |
  | **B-16** stale `ALARM_PID` after reap | [CFE-4733](https://northerntech.atlassian.net/browse/CFE-4733) | **B-18** pre-fork `ALARM_PID` publish race | [CFE-4734](https://northerntech.atlassian.net/browse/CFE-4734) |
  | **B-19** `fdopen()`-failure `ALARM_PID` leak | [CFE-4735](https://northerntech.atlassian.net/browse/CFE-4735) | | |

  B-4, B-10 and B-11 share **one** ticket because they ship as one stack and are
  not independently landable. CFE-4727 is the first filing anywhere for the
  exec_timeout termination half; it went unlettered until this session assigned
  it **B-17** on shipping the fix. **CFE-4731 (B-14) was filed 2026-08-17 while
  fixing B-13** — the JQL link below names the original fifteen keys explicitly,
  so it does not include it. **CFE-4734 (B-18) and CFE-4735 (B-19) were filed
  2026-08-18**, surfaced by the 3-model panel reviewing B-17's fix — also not in
  that JQL.

  **Every ticket was written from the fork issue *plus its correction comments*,
  never from the body alone.** Five of the six security items carry retractions
  that live only in comments — B-1's withdrawn fail-open claim, B-2's
  unconditional-`setpgid` regression and PID-recycling correction, B-8's
  "kept" → "compliant" relabel, B-10's "rendering" → "copying at policy load"
  reframing, and P-3's trust-model overstatement. Copying any of those bodies
  verbatim would have republished a withdrawn claim onto a public tracker.
  `core#13`'s body is also stale where it says behavioural verification is
  outstanding; it has since been verified both directions against stock
  libntech `5b5d04e1`.

  Each CFE key is linked back from its upstream PR/Discussion/issue and from
  its fork artifact, so the two never diverge.

  ### Issue linking is not available to us — use URLs (2026-08-17)

  **`Link Issues` is refused, permanently. Do not ask again.** The operator
  asked Northern.tech and was told they do not grant that permission to
  community reporters. Enumerated rather than guessed —
  `GET /rest/api/3/mypermissions?projectKey=CFE`:

  | permission | granted |
  |---|---|
  | `CREATE_ISSUES`, `EDIT_ISSUES`, `ADD_COMMENTS` | **yes** |
  | `CREATE_ATTACHMENTS`, `TRANSITION_ISSUES`, `BROWSE_PROJECTS` | **yes** |
  | `LINK_ISSUES` | **no** |
  | `MANAGE_WATCHERS`, `SCHEDULE_ISSUES`, `SET_ISSUE_SECURITY` | no |

  **Remote/web links are gated on the same permission** — they are not a way
  round it. `POST /rest/api/2/issue/CFE-4715/remotelink` returns
  **HTTP 403** `No Link Issue Permission`. (Probed with a disposable
  `globalId`; the 403 meant nothing was created.)

  So relationships are carried as **plain URLs in the description**, which needs
  only `EDIT_ISSUES`. Every one of the 15 tickets now ends with an
  `h3. References` section holding, as appropriate: its related tickets as
  `browse/CFE-####` URLs, its `Public working record:` GitHub URLs, and a
  wiki-markup link to a JQL query returning the whole set. The query names the
  keys explicitly, so it carries **no Atlassian accountId** and is safe to
  reproduce in this public repo:

  ```
  https://northerntech.atlassian.net/issues/?jql=key+in+(CFE-4715,+...,+CFE-4729)+ORDER+BY+key+ASC
  ```

  Verified anonymously (HTTP 200, 15 keys) — and note **`/rest/api/2/search` is
  now HTTP 410**; the live endpoint is `/rest/api/3/search/jql`.

  The clusters the URLs encode, chosen where items share a code area or a
  landing dependency rather than merely a theme: `CFE-4715`+`CFE-4716`
  (`--simulate`); `CFE-4719`+`CFE-4720`+`CFE-4722` (CMDB);
  `CFE-4724`+`CFE-4725` (JSON numbers, two repos, two PRs);
  `CFE-4726`+`CFE-4727`+`CFE-4728`+`CFE-4729` (`exec_timeout`). `CFE-4717`,
  `CFE-4718`, `CFE-4721` and `CFE-4723` stand alone, with `CFE-4721` carrying a
  "see also" to `CFE-4724` as related-but-not-duplicate.

  **How B-13's fix interacts with P-2's workaround — determined, not assumed.**
  P-2 (`CFE-4716`, `core#6294`) carries `RestoreUtf8InJson()`, which undoes the
  *old* libntech writer's per-byte escaping locally in `cf-agent`. Its helper
  `GetJsonEscapedByte()` returns false for `value > 0xff`
  (`cf-agent/simulate_mode.c`), so once libntech emits a correct `中` the
  helper simply does not recognise it and the escape passes through verbatim.
  **There is therefore no double-processing and no corruption if both land** —
  the workaround degrades to a no-op for multi-byte code points. The one real
  consequence is that `--simulate=json` output would then contain `中`
  escapes rather than raw UTF-8 bytes; that is still correct, conformant JSON,
  but P-2's acceptance `.expected` asserts the raw form and would need
  refreshing when the submodule pin moves. Read from the source, not inferred
  from behaviour; not yet executed, because `core-p2` pins libntech at
  `5b5d04e1` and rebuilding it against the fix was out of scope. **Do not
  pre-emptively remove `RestoreUtf8InJson()`** — nothing is decided upstream.

  **CORRECTED 2026-08-18 — actually executed.** Built a fresh `core-p2`
  worktree (`core-p2-utf8test`) with its `libntech` submodule repointed at
  the merged overlay (`45c816c`, B-13+B-14+B-22+B-23) and ran
  `tests/unit/simulate_mode_test` for real, plus a standalone probe isolating
  `RestoreUtf8InJson()`/`GetJsonEscapedByte()`/`ValidUtf8SequenceLength()`
  against the fixed `JsonEncodeStringWriter()`. Two different results for the
  two claims above:

  - **Valid multi-byte UTF-8 (e.g. "é", U+00E9): confirmed safe, as
    predicted.** The fixed encoder emits one `é` escape per code point
    instead of one `\u00XX` per UTF-8 byte, so `RestoreUtf8InJson()` never
    collects the 2+ consecutive escapes it looks for and passes the text
    through unchanged — dead code for this case, not corruption.
    `test_special_characters_in_path`'s failure is cosmetic: it asserts the
    *old* raw-byte output shape, which a conformant parse no longer needs;
    the parsed value itself is correct.
  - **Invalid non-UTF-8 bytes (e.g. a lone 0xE9 filename byte): the "no
    corruption" claim does NOT hold, but not for the reason the workaround
    was written to guard against.** The probe shows a genuine `é` (U+00E9)
    and a lone invalid byte `0xE9` both encode to the **identical**
    `é` escape — `RestoreUtf8InJson()` cannot tell them apart and
    leaves both alone. `test_invalid_utf8_in_path` only ever "passed"
    because the *old* non-conformant parser and writer were exact inverses
    (this register's own B-13 language) and canceled each other out —
    exactly the "codec round-trips its own corruption" trap. Once the
    parser side is also conformant, `é` correctly decodes to `é`,
    which is **not** the original byte: a non-UTF-8-valid path byte cannot
    be represented exactly in a JSON string at all, conformant or not. This
    is a real, pre-existing representational gap that the old test
    accidentally papered over, not a new defect `RestoreUtf8InJson()`
    introduces. It needs a real upstream design decision (replacement
    character, error out, a separate raw/base64 field) before B-13 lands
    and this test starts failing for real. Documented as a comment on
    CFE-4716 rather than a new ticket, since it is P-2's own test gap, not
    an independent libntech defect.

  **Correction to this register's own record.** It previously said the sibling
  keys had been written into the descriptions as the workaround. Audited
  2026-08-17: that had only happened on **6 of 15** tickets, asymmetrically
  (`4719`↔`4720` and `4724`↔`4725` both ways; `4727`→`4726`, `4728`→`4726`,
  `4729`→`4728` one way only), with **zero** browse URLs, **zero** labels, and
  **seven** tickets — `4718`–`4723` and `4727` — carrying no GitHub artifact
  link at all. All of that is now filled in and read back from stored state.

  **Labels were deliberately not used.** A shared label would have been the
  other way to make the set retrievable, but the reporter is already visible on
  every ticket, so reporter-scoped JQL retrieves the same set without adding
  a foreign label to someone else's board.

## Refiling checklist

The tracker is open (CFE Jira, 2026-08-17). Each item needs, in this order:

1. A CFE ticket. **Do not copy the fork issue's body verbatim** — that
   instruction stood here until 2026-08-17 and it was wrong. Several fork
   issues carry claims we later *withdrew*, and the retraction lives in a
   **comment**, so a verbatim copy republishes a false claim onto a public
   tracker under a fresh date. Read the body **and every comment**, then write
   the ticket from the corrected state. Where we retracted something, say so in
   the ticket: it costs nothing and it is why maintainers can trust the rest.
2. A PR against the upstream repo from our branch, with `Ticket: CFE-####`
   in the commit trailer — and per the `#6295` lesson, never write a trailer
   for a ticket you have not seen exist.
3. This register updated in the same commit, and the fork artifact commented to
   point at the CFE key so the two never diverge.
4. An `h3. References` section on the ticket carrying its relationships as
   **URLs** — related `browse/CFE-####` keys, the `Public working record:`
   GitHub URLs, and the all-15 JQL link. Do **not** reach for
   `POST /rest/api/3/issueLink` or `/remotelink`: both need `Link Issues`,
   which Northern.tech does not grant us and which the operator has already
   asked for and been refused.

Do **not** rewrite history on the fork branches to suit a new tracker's
conventions — the fork commits are what our own builds are tested against, and
[R22](projector-reconciliation-2026-08-16.md)'s anti-drift argument applies to
these the same way it applies to the projector.

## The fork is a staging area, not a product

Operator instruction, 2026-08-16: *"We do not want to maintain forked code
long-term if at all possible. We totally want to maintain a fork that fixes
whatever issues are not currently fixed upstream."*

So the fork carries exactly what upstream has not taken yet, and every item here
is meant to leave it. That is also why the diff discipline from PR 1 still
governs every fix: additive over modifying, few tight hunks, no reflowing of
neighbouring code, so that carrying an item across upstream releases stays cheap
while it waits.

**Branch layout.** One branch per upstream contribution, each cut from `master`
and independently landable — `fix/exec-timeout-commands` (B-1) and
`fix/timeout-process-group` (B-2) touch disjoint files, and either can be taken
without the other. **`tendcf-integration`** merges all of them and is the branch
our builds are made from. Never develop on the integration branch; cherry-pick
onto a clean per-fix branch so what we offer upstream is never entangled with
something upstream has not agreed to.

**Our builds test against the fork**, so a fix landing here changes what tendcf
is measured against. Anything in the corpus that was measured on stock 3.27.1
and could be affected by one of our fixes must be re-measured and the number
re-stated, not assumed to have carried over.

## PR-sharing sweep, 2026-08-18

Standing order from the operator: **when in doubt, open a PR and/or issue.**
Finished code sitting on a fork branch is not shared. Audited every branch on
`djbclark/core` and `djbclark/libntech` against open PRs:

| branch | state |
|---|---|
| `fix/process-darwin` (B-3) | **PR [#6307](https://github.com/cfengine/core/pull/6307)** |
| `fix/mount-options-timeout-leak` (B-15) | **PR [#6308](https://github.com/cfengine/core/pull/6308)** |
| `fix/alarm-pid-reset-after-reap` (B-16) | **PR [#6309](https://github.com/cfengine/core/pull/6309)** |
| `fix/exec-timeout-alarm-pid` (B-17) | **PR [#6310](https://github.com/cfengine/core/pull/6310)** — stacked on #6305 |
| `fix/exec-timeout-prefork-race` (B-18) | **PR [#6311](https://github.com/cfengine/core/pull/6311)** — stacked on #6305 |
| `fix/exec-timeout-alarm-leak` (B-19) | **PR [#6312](https://github.com/cfengine/core/pull/6312)** — stacked on #6310 |
| `fix/exec-timeout-commands` | superseded — tree is **byte-identical** to `fix/exec-timeout-poll-deadline` (#6300) |
| `fix/exec-timeout-promise-result` | superseded — tree is **byte-identical** to `fix/exec-timeout-promise-outcome` (#6299) |
| `fix/timeout-process-group` | absorbed — both commits are in #6305 |
| `fix/json-number-rendering` | **PR [#6314](https://github.com/cfengine/core/pull/6314)**, ticket [CFE-4737](https://northerntech.atlassian.net/browse/CFE-4737). **My earlier "correctly blocked" call was wrong** — corrected same day, see below |
| `pr-getopt-optstring-fixes` | **PR [#6313](https://github.com/cfengine/core/pull/6313)**, ticket [CFE-4736](https://northerntech.atlassian.net/browse/CFE-4736) — re-authored, audited, extended and shipped 2026-08-18; see below |
| `tendcf-integration` | ours, never for upstream |
| libntech `silent-digest-failure` / `fix/json-string-codec` / `fix/json-number-handling` | already PRs #291 / #293 / #294 |

Three of the six above are **stacked** on #6305's series, so each shows 10–11
commits against master. Each PR body names the single commit that is actually
new and states what it depends on.

### `pr-getopt-optstring-fixes` — resolved, shipped as CFE-4736 / #6313

Ten commits from **2026-07-31**, predating this register: getopt short-option
string fixes across `cf-check`, `cf-execd`, `cf-monitord`, `cf-net`,
`cf-promises`, `cf-runagent`, `cf-secret`, `cf-serverd`, `cf-testd` (9 files,
+11/−9). The defect class is real — missing entries mean a documented long
option silently does nothing, and a missing `:` makes an option swallow the
wrong argument.

Not opened as a PR, because unlike the six above it has none of the
prerequisites:

1. **Every commit is authored `Claude <noreply@anthropic.com>`.** `CONTRIBUTING.md`
   is explicit that the human using the AI is the author and submitter. These
   need re-authoring before they can be offered.
2. **No Jira ticket** — the other items all carry a CFE-NNNN.
3. **Never reviewed and no evidence of testing** — no panel, no brief, no
   recorded build or test run.

It is not "in doubt", it is "known not ready", which is why the standing order
does not apply. Fixing 1–3 is a small task and should be scheduled.

**Resolution, same day.** The operator directed that the commits be re-attributed
to `Daniel Joseph Barnhart Clark <djbclark@gmail.com>` and confirmed that upstream
understands and accepts his multi-AI vetting process, which removes the authorship
objection (the AI involvement was never the problem; the author field was). All 12
commits now carry that single author.

Rather than post the partial fix, the audit was **completed first**. A checker was
written that pairs each `getopt_long()` call site with the `struct option` table it
actually references, resolving the option-string variable to its *nearest preceding*
definition. Both refinements mattered — pairing naively per file reports `cf-net`'s
`-o/--output` and `-j/--jobs` as missing when they are correctly declared in
subcommand-local tables with their own option strings. Two rounds of false positives
were found and removed this way before anything was filed.

Findings the original branch did **not** cover, now fixed: duplicate `V` and bare `g`
in `cf-execd`, duplicate `g:` in `cf-promises` (all provably dead — `getopt_long()`
matches the first occurrence, so behaviour is unchanged, and this was confirmed by
running the rebuilt binaries).

Two findings were deliberately **not** patched and were raised as questions instead.
`cf-agent`'s `-x/--self-diagnostics` and `cf-check`'s `-h/--help` both declare
`optional_argument` against a bare character in the option string — but **neither
handler reads `optarg`** (`cf-check.c:166`, `cf-agent.c:649` both print and exit).
So the *table* is the wrong side, and the mechanical "fix the option string to `h::`"
would have advertised an argument that is silently discarded, i.e. worse than the
status quo. Both reconciliations are user-visible, so the choice was left upstream.

Verified by running, not only reading: `cf-check -V` prints the version (previously
"unrecognized option"), `cf-secret -v` enables verbose logging, `cf-testd -r` now
correctly *demands* its argument, and `cf-execd -V` / `-g info` are unchanged after
the duplicate removal. `tests/acceptance/mock_package_manager.c` passes a literal
`""` and is intentionally long-options-only — excluded, not a defect.

### `fix/json-number-rendering` was never actually blocked

Recorded because the mistake is instructive. I marked this branch blocked on
libntech [#294](https://github.com/NorthernTechHQ/libntech/pull/294) because it had been *developed* against an
unmerged libntech commit (`5b5d04e19`), and inferred a build dependency from
that. I never tested the inference.

It does not hold. `JsonPrimitiveGetAsString()` — the function the fix switches
to — **already exists on libntech master** (`libutils/json.h:246`), and master
already creates primitives from the parsed text buffer (`json.c:2377`), which is
the property the fix relies on.

Verified rather than re-reasoned: rebased the three commits onto current
upstream master, which brings the `libntech` submodule pointer to master's own
`0c0620d` (the diff is then 5 source files and **no** submodule change), built
clean with zero errors, and ran the fix's own new test — `test_from_container_numbers`
passes against libntech master.

`rlist_test` does abort later at `rlist.c:135` in `test_rval_to_scalar2`, but a
control run on unpatched upstream master aborts at exactly the same place, which
is why `rlist_test` sits on the macOS `XFAIL_TESTS` list. Pre-existing, unrelated.

**Lesson:** "developed against X" is not the same claim as "requires X", and the
difference is one rebase and one build. [djbclark/core#7](https://github.com/djbclark/core/issues/7)'s premise should be
re-checked the same way for any other branch it covers, rather than assumed.

## Test-coverage audit, 2026-08-18

Operator asked whether we have been writing tests for what we find, given that
the number of open items makes regressions hard to track. Audited every
submitted branch rather than answering from memory.

**16 of 17 branches ship tests** — 15 when this audit started, plus the
regression test added to #6313 below. The single remaining gap is #6308, and it
is documented rather than closed, for the reason given there. `cfengine/core`
has 80 unit-test `.c` files
and 32 acceptance directories; `CONTRIBUTING.md` requires unit tests for C
functions and acceptance tests for promise types.

| branch / PR | test |
|---|---|
| #6309 B-16 | new `tests/unit/unix_test.c` |
| #6314 CFE-4737 | `test_from_container_numbers` in `rlist_test.c` |
| #6310 B-17 | `test_pclose_leaves_the_alarm_its_process` + acceptance |
| #6311 B-18 | unit 6/6 → 10/10 + acceptance |
| #6312 B-19 | `test_leftover_alarm_does_not_kill_next_child` |
| #6300 / #6302 | `process_terminate_unix_test.c` / new `unix_iface_test.c` |
| #6299, #6305, #6293, #6294 | acceptance tests |
| libntech #291 / #293 / #294 | new `hash_init_fail_test.c` / `json_test.c` additions |
| #6307 B-3 | no new test **by design** — removes `process_test` from the macOS `XFAIL_TESTS`, so an existing upstream test now guards the change. Arguably the strongest outcome, but a distinct category from "wrote a test" |
| **#6313 CFE-4736** | **gap closed this session** — see below |
| **#6308 B-15** | **gap documented, not closeable** — see below |

Beyond mere existence, the bar has been **discrimination**: proving the test
fails without the fix. B-19's panel disproved an "untestable" claim outright;
CFE-4737's test does not merely fail on unpatched code, it takes the process
down with `StringToLongExitOnError`.

### #6313 — closed with a class-killing test

`tests/unit/getopt_optstring_test.sh` (POSIX sh + awk, no python: CFEngine
targets AIX/Solaris/HP-UX and the existing `check_SCRIPTS` are all shell).
Parses each `getopt_long()` call site, pairs it with the table it *names*, and
requires every table character to be present in that call's option string.

Two design points, both learned by getting it wrong first:

1. **Pairing must be per call site, not per file.** `cf-net` has three call
   sites, two of whose tables share the name `longopts`; a file-wide compare
   reports its subcommand-local `-o`/`-j` as missing. Caught on the first run.
2. **Silent skips are the real hazard.** The parser skips what it cannot
   understand so it can never break the build — but a file that calls
   `getopt_long()` and yields no usable call site now **exits 2** rather than
   passing quietly. Verified by renaming a table so the parser could not find
   it. Without this the test would have reported success while checking almost
   nothing, which is how it behaved before two parser bugs were fixed
   (`cf-testd`'s `{NULL, …}};` sentinel sharing a line, and a trailing comma
   making a wrapped call look complete).

Discriminates: silent on the branch, reports **all ten** faults on unpatched
master. `PASS: getopt_optstring_test.sh`, all 68 tests behaved as expected.

### #6308 — not unit-testable, and said so upstream

Deliberately **not** given a manufactured test, because a test that does not
reach the fix is worse than none — it is exactly the false confidence this
audit was asking about. `ReconcileMountOptions()` links, but: under a dry run
it returns at `nfs.c:1399` via `MakingInternalChanges()` *before* the arm/disarm
code; without one it runs a real `mount -o remount`; `VMOUNTCOMM` is
`static const char *const` at `nfs.c:64` so it cannot be redirected; and
`nfs_test` covers only pure string helpers. Recorded on the PR and in
CFE-4732 (comment 159443) with the minimal seam that would make it testable,
left as upstream's call.

*Correction to an earlier claim in this register:* I had justified this as "the
nfs.c family isn't testable". Too strong — `nfs_test` exists
(`tests/unit/Makefile.am:421`). The accurate statement is that *this function*
is out of reach of the existing pattern.

## Reviewer-panel contamination — the method changed 2026-08-18

**A review seat rewrote the code it was reviewing.** `gemini --model
gemini-3.1-pro-high --dangerously-skip-permissions`, launched with cwd inside
the B-5a worktree, edited `libpromises/cmdb.c` on top of a commit that had
already been built and acceptance-tested. `grok --always-approve` has the same
capability and was running in the same directory concurrently.

Why it matters beyond the one incident:

- The tested tree and the shipped tree silently diverge. Build and test results
  reported before the edit describe code that is no longer on disk.
- A second seat reading the same directory reviews the **first seat's edits**,
  not the author's code, and neither one says so.
- Nothing warns you; it shows up only as a stray "file was modified" notice or
  a `git status` that should have been clean.

**The method now:** run each seat against its own disposable copy
(`cp -a` of the worktree), never the directory being built and committed from,
and never two seats in one directory. `git status` in the real worktree after
every panel run — dirty means the review is contaminated and the tree is not
what was tested. Judge any edits a seat made on their merits *separately* and
apply them yourself with a rebuild and re-test.

This was worth the trouble: on the clean re-run, grok found a real gap
(B-5a's first acceptance test did not lock the walk-split design) that the
contaminated run had not surfaced.

### grok stalls — partially diagnosed, not solved

Two grok runs stalled at ~400 bytes of output for 12+ minutes with no growth,
both while gemini was concurrently rewriting files in the same directory. The
run on an isolated read-only copy completed normally (12.5 KB, thorough), and
a later probe in the same previously-stalling worktree returned in 6.6 s, so
the directory is not cursed and there is no stale lock (`active_sessions.json`
is `[]`). grok does keep **per-directory sessions** with a lock
(`~/.grok/active_sessions.{json,lock}`; `--continue` resumes "the most recent
session for the current working directory"), so same-directory concurrency is
the plausible mechanism — but with n=2 stalls this is **correlation, not a
proven cause**. Use `--debug --debug-file <FILE>` (not `--log-file`) for
diagnostics next time one hangs.

### Test harness: use fakeroot with a FRESH workdir; no NOPASSWD rule

**Settled 2026-08-18 after measuring all three options.**

`--gainroot=fakeroot` (`brew install fakeroot`) is the right default — it is
the suite's own (`DEFAULT_GAINROOT=fakeroot` on every non-Windows platform).
With a clean workdir it runs `00_basics/06_host_specific_data` 13/13, exit 0,
and cleans up after itself. Its limit is real and measured: fakeroot's uid
faking is **broken by SIP** here (`fakeroot id -u` → 501, not 0) because it
works through `DYLD_INSERT_LIBRARIES`, which macOS strips when spawning
protected binaries like `/bin/sh`. So `getgroups`, `getgroupinfo`,
`getusers_vararg` and `filestat_xattr` still fail under it — those need real
root, and nothing but real sudo gives it.

**A dirty workdir inflates the reported pass count, and this put a wrong
number in a public PR.** `BASE_WORKDIR` defaults to `$(pwd)/workdir`; runs
under `--gainroot=sudo` leave root-owned files a later non-root run cannot
delete, and the stale entries get counted. B-5a's branch has 13 test files
but reported "17 passed", which reached PR #6315's body and the CFE-4719
comment before being caught and corrected (PR body edited, Jira comment
159448). Always:

```
export BASE_WORKDIR=<scratch>/wd; rm -rf $BASE_WORKDIR; mkdir -p $BASE_WORKDIR
```

and check the total against `ls *.cf | wc -l` before quoting it. `Permission
denied` on `rm` in the log means the count is not trustworthy.

**Do not add a NOPASSWD sudoers rule for the test suite.** `testall` line 514
is `$GAINROOT "$WORKDIR/runtest"`, and that path lives inside the checkout,
writable by the user — so a NOPASSWD rule on it is `NOPASSWD: ALL` in
practice. That is not theoretical here: reviewer CLIs and parallel subagents
demonstrably edit files in these worktrees unprompted (see the contamination
notes above), and this machine also holds the Atlassian token and the
secretspec broker. Contrast the existing `sudo-secretspec` rule, which is
safe because its target is a fixed root-owned binary the user cannot rewrite.
The actual cause of mid-session prompts is `timestamp_timeout=5`; raise that
in a `/etc/sudoers.d/` drop-in or run `sudo -v` before a batch, keeping
password auth as the real control.

### `--gainroot=env` is not a free substitute for sudo

The sudo credential cache expires mid-session, after which
`testall --gainroot=sudo` dies with **exit 144 and no output** — which reads as
a hang, not a failure. `--gainroot=env` works, but makes tests that need real
privilege **fail rather than skip**: `01_vars/02_functions` under it gives
300 passed / 5 failed, and those 5 (`getgroups`, `getgroupinfo`,
`getgroups_vararg`, `getusers_vararg`, `filestat_xattr`) are pre-existing
environmental failures, confirmed against unmodified upstream. A directory that
"passes" under `--gainroot=env` is only evidence for the subset not needing root.

## First maintainer review, 2026-08-18

nickanderson (MEMBER) reviewed two PRs same day. #6305 (B-17-family): inline
comment-density note on `verify_exec.c`, fixed same day in `0e06ad3d7`
(pushed before this review cycle), no further action. #6308 (B-15/CFE-4732):
**CHANGES_REQUESTED** — commit message didn't follow cfengine style
(past-tense subject, no `fix:` prefix, `Changelog:`/`Ticket:` trailers), plus
an inline suggestion collapsing a 6-line comment to one line, plus a general
comment on prose volume: "This one is like 100 characters of prose ... per
character of code... Bite sized PRs that are demonstrated issues (existing
bugs with reports from users) are likely to go in easier than PRs that are
very large which have not been reported by users."

Addressed same session: commit message rewritten and amended
(`190f869a5` → `9dd5eb51c`, force-pushed), comment shrunk per the suggestion,
PR description cut to defect + fix + why-no-test, replied on the PR. Recorded
as a standing rule (auto-memory `be-terse-upstream-asked`, now covers two
independent instances): terser prose everywhere upstream-facing, cfengine's
own commit trailer style (not ours), and a preference going forward for small
PRs on demonstrated user-reported bugs over large self-discovered ones.

### Cross-worktree contamination between parallel subagents

While three subagents worked in parallel worktrees, one agent's file was
overwritten with another branch's content (`core-cmdbnull/libpromises/cmdb.c`
briefly held `fix/cmdb-dotted-key-warning` code). The owning agent caught it,
reset to pristine upstream and re-applied only its own change. **All four
branches were verified isolated afterwards** — each contains only its own
change, none contains the others'. When running parallel agents on the same
file in different worktrees, verify isolation before pushing, e.g.
`grep -c <other-branch-symbol> <worktree>/<file>` for each pair.
