# Second opinion: B-2 merged with #6299 (`fix/timeout-process-group-merged`)

**Reviewer:** Claude Fable 5 (xhigh), adversarial independent review, 2026-08-17.
**Code reviewed:** `/Users/djbclark/src/core-b2merge`, branch
`fix/timeout-process-group-merged`, HEAD `3d8e90d68` (three commits on
`0ab083c4d`, the live head of cfengine/core#6299).
**Method:** full read of both sides and all surrounding files named in the
brief, plus an independent from-source build and test campaign in a scratchpad
copy (macOS 26.6.1 arm64, Apple clang 21.0.0). I wrote nothing into the
reviewed worktree; all builds and edits happened in my own copy. I did not
read any handoff or any other panel member's opinion.

## Verdict: ship with changes

The merge resolution itself is correct. Both sides' semantics survive intact,
the conflict decisions are the right ones, and I independently reproduced the
build (rc 0, exactly the two pre-existing warnings, zero new), the 6/6
acceptance pass (63.6s), and — in **both** directions, including the one the
author skipped — the discrimination of the new test. I also measured the thing
the author only asserted: the flag-clearing (wrong) `ClearTimeOut()` variant
passes all six acceptance tests, so the resolution's central invariant really
is invisible to the shipped test suite.

Required changes, in priority order:

1. **Guard the `getpgid()`/`kill(-pid)` block in `TimeOut()` for MinGW**
   (e.g. `#ifndef __MINGW32__` around `libpromises/timeout.c:93-118`, keeping
   `GracefulTerminate()` outside the guard). Evidence below (Uncertainty 2)
   that this merge very likely breaks a Windows compile/link that master
   survives: `timeout.c` is compiled unconditionally
   (`libpromises/Makefile.am:163`), nothing in core or libntech declares or
   provides `getpgid()` on NT, and every existing raw `kill()` call in
   NT-compiled translation units is fenced with `#ifndef __MINGW32__` —
   strong evidence the tree treats `kill()` as unavailable there. The guard
   is semantically free: the guarded block is meaningless on a platform with
   no `cf_popen()`/`setpgid()` path.

2. **Make `TIMEOUT_ARMED` a `volatile sig_atomic_t`** (two lines:
   declaration, and `return TIMEOUT_ARMED != 0;` in `TimeOutIsArmed()`).
   Full reasoning under Uncertainty 3. The type change cannot affect
   `cf_popen()`'s child gate — verified: `TimeOutIsArmed()` is called exactly
   once in the tree (`pipes_unix.c:256`), in the forked child, reading a
   fork-time snapshot with no concurrent writer; nothing takes the flag's
   address; the function's `bool` return type is unchanged.

3. **Add a unit test pinning the `ClearTimeOut()` contract.** I demonstrated
   (measured, not argued) that this is cheap and discriminating: a ~50-line
   probe calling `SetTimeOut()`, `TimeOut()` (public in `timeout.h` — no
   restructuring needed), then `ClearTimeOut()`, and asserting
   `TimeOutHasFired()` still returns true, passes on the merged code and
   fails on the flag-clearing variant. `tests/unit`'s default
   `LDADD = ../../libpromises/libpromises.la` links everything required.
   Given that the entire conflict resolution hangs on this unpinned
   invariant and I measured the acceptance suite passing 6/6 against the
   wrong variant, shipping the contract with only a comment is not enough.

Advisory (not blockers, but should be named in the PR or fixed as separate
commits):

4. `cf-agent/nfs.c:1434` and `:1459` call `SetTimeOut()` with **no disarm on
   any path** — a pre-existing upstream defect (commit `348722a06`, in
   cfengine/core master before this series). The PR converts nfs.c's two
   open-coded disarms to `ClearTimeOut()` and walks past these two; an
   upstream reviewer will ask why. Post-merge, this success-path leak also
   leaves `TIMEOUT_ARMED` set, so subsequent unrelated `cf_popen()` children
   lead their own process groups until the leaked alarm fires — a leak-path
   resurrection of exactly the unconditional-`setpgid` behavior the
   2026-08-16 panel refused. A `ClearTimeOut()` after the reconcile loop is
   a two-line fix the merge's own API finally makes clean.

5. `ShellCommandReturnsZero()` (`libpromises/unix.c:225`) sets
   `ALARM_PID = pid`, **reaps** the child (`waitpid`, lines 238/258), and
   never clears `ALARM_PID`. This is the one place the "PID recycling is
   impossible because the process is an unreaped zombie" argument fails: the
   pid is fully reaped and recyclable while `ALARM_PID` still names it. A
   leaked alarm (from any of the sites in item 4 or the early-return leaks)
   firing after such a call and before anything rewrites `ALARM_PID` runs
   `TimeOut()` against a recycled pid. Pre-merge that was already a wrong
   `GracefulTerminate()`; post-merge, if the recycled pid happens to be a
   process-group leader (`getpgid(pid) == pid`), it escalates to
   `kill(-pid, SIGKILL)` of an innocent group, as root. The chain is long
   (leak x no intervening rewrite x recycle x leader), but the one-line
   hygiene fix (`ALARM_PID = -1` after reaping) is worth a follow-up, and
   the defect register should name it. I did not find this in the author's
   listed uncertainties or deferrals.

## The author's nine uncertainties, by name

### Uncertainty 1 — "the hazard is latent, not live"

The author's framing is accurate but stops one step short. I verified the
ordering claim in `RepairExec()` directly: the single sample point is
`verify_exec.c:460` (after `cf_pclose()`, deliberately — the comment at
454-459 is right that sampling earlier would miss the alarm firing during the
reap), consumption of `TIMEOUT_SIGNALLED` at :472, and the only
`ClearTimeOut()` at :502. Sample-before-clear holds on every path that
reaches reporting; the three early returns (:330, :374, :393) skip both
sample and clear (pre-existing leak family, below). So yes: a flag-clearing
`ClearTimeOut()` would pass everything today. I did not take that on faith —
I built the flag-clearing variant and ran the full six-test suite against it:
**6/6 pass, 61s.** The hazard is exactly as latent as claimed.

But "nothing executable pins it" conflates "the shipped tests don't" with
"no test can." A test can, without restructuring: `TimeOut()` is a public
function, so a unit test simulates the alarm by calling it (with `ALARM_PID`
at -1 it takes the no-process branch — precisely the state after
`cf_pclose()` clears the pid). I wrote that probe, linked it against the
built `libpromises`, and got PIN-PASS on the merged code and
`PIN-FAIL: ClearTimeOut() cleared TIMEOUT_FIRED` on the wrong variant. An
unpinned invariant that (a) the whole resolution rests on, (b) silently
regresses — this is the auto-merged-file trap the brief opens with — and
(c) costs ~50 lines to pin, is exactly what a reviewer should demand a test
for. Hence required change 3. Not overcaution; the author's instinct to
enforce the safer contract was right, and the missing test is the only gap.

### Uncertainty 2 — Windows/MinGW build

Settled from the build system and headers, as far as it can be without a
MinGW toolchain (I do not have one; stated plainly in trap control):

- `timeout.c` is unconditional (`libpromises/Makefile.am:163`);
  `pipes_unix.c` and `process_unix.c` are under `if !NT`.
- `getpgid()`: no declaration anywhere for NT — not in
  `libntech/libutils/platform.h`, no `AC_CHECK_DECLS(getpgid)` in either
  configure.ac, no libcompat implementation, and MinGW headers do not have
  it. On NT this is an implicit function declaration (hard error on GCC >= 14,
  warning-then-link-failure earlier) with no symbol to link.
- `kill()`: same absence of declaration/compat, and — the decisive
  empirical point — **every** raw `kill()` call in code compiled on NT is
  fenced with `#ifndef __MINGW32__`: `libpromises/unix.c` (whole body fenced,
  :35-:605), `cf-agent/verify_processes.c` (:292 guard before :342),
  `cf-execd/cf-execd.c` (:879 guard before :906), `cf-execd/cf-execd-runner.c`,
  `cf-watchd/cf-watchd.c`. A codebase whose Windows build had a `kill()`
  would not fence it everywhere.
- Master's `timeout.c` compiles on NT because its externals are covered:
  `alarm()` declared via `!HAVE_DECL_ALARM` in platform.h, `SIGALRM`/`SIGKILL`
  as dummies (platform.h:779/:782), and `GracefulTerminate()` an
  already-external NT link dependency (also referenced unconditionally by
  `mod_custom.c:1214` and `locks.c:630`, so some Enterprise-side provider
  demonstrably exists). The merge adds two *new* unprovided symbols.

Conclusion: the author's "biggest worry" is warranted; this very likely
breaks a Windows compile that master survives, and the fix is a trivially
safe guard. Note this defect is B-2's committed content (`847373cf6`), not a
merge artifact — the 2026-08-16 panel missed it — but the merged branch is
what ships, so it must be fixed here. The new acceptance test already carries
`test_skip_unsupported windows`, so only the compile is at issue. Required
change 1.

### Uncertainty 3 — plain `bool` `TIMEOUT_ARMED`

Pressed hard, in both directions, and the honest answer is more nuanced than
either "hazard" or "aesthetic":

- **"Already reviewed" does not transfer.** The 2026-08-16 panel reviewed a
  file with no `sig_atomic_t` in it. The merge produces a file whose comment
  at lines 29-31 says "Written from a signal handler, hence
  `volatile sig_atomic_t`" and whose line 43 declares a plain `bool` written
  from the same handler eleven lines of context later (`TimeOut()`, :86).
  The patch as summed teaches a rule and then breaks it. That inconsistency
  did not exist in either reviewed input; it is a property of the merge, so
  the merge is where it gets fixed. The author's grounds for keeping it are
  the framing error the brief warned about.
- **Is it a live bug? No.** All parent-side writes (`SetTimeOut()`,
  `ClearTimeOut()`, normal flow) and the handler write are in the same
  thread on the cf-agent path, so the handler runs atomically relative to
  them; the only reader, `cf_popen()`'s child (`pipes_unix.c:256`), reads a
  fork-time snapshot with no concurrent writer (POSIX clears pending alarms
  in the child, and the child's memory is a copy). Formally, writing any
  static object that is not `volatile sig_atomic_t` (or a lock-free atomic)
  from an async handler is UB per C11 7.14.1.1p5 — but a one-byte store on
  every real target this code runs on does not tear or misorder observably
  here.
- **House style cuts against my own instinct, and I checked it:** the only
  `sig_atomic_t` in the entire tree is #6299's own two flags.
  `signals.c:31` `PENDING_TERMINATION` is a plain `bool` written from
  `HandleSignalsForDaemon()` (:209) — a signal handler. So a CFEngine
  maintainer might well not blink at the bool. But that same maintainer,
  reading *this* diff, sees the sig_atomic_t rationale and the exception to
  it in one hunk and has to ask; the two-line change costs less than the
  question. `TimeOutIsArmed()`'s use in the child is provably unaffected
  (return type unchanged, `!= 0` conversion identical, no address taken).

Verdict: required change 2 — required for the patch's internal coherence and
formal correctness, not because I can construct a miscompile. If the author
prefers to keep the bool, the minimum alternative is a comment on line 43
explaining why this flag deliberately differs from its siblings; silence is
the one option that should not ship.

### Uncertainty 4 — `getpgid()` in a signal handler

The author's characterization is correct: `setpgid()` and `kill()` are on
the POSIX async-signal-safe list; `getpgid()` is not (`getpgrp()` is, but is
useless here — wrong process). In context this is acceptable: the same
handler already calls `Log()`, `GetErrorStr()`, `GracefulTerminate()` (which
`nanosleep()`s in a loop for up to ~2s) — all far less safe than a thin
`getpgid` syscall, and all pre-existing master behavior. Anyone who wants
formal purity here has to redesign the handler wholesale (e.g. parent-side
`setpgid()` mirror after fork with the pgid recorded in a `sig_atomic_t`),
which is a legitimate upstream discussion but not this merge's job. No
change required.

### Uncertainty 5 — the child-side failure `Log()`

Verified the precedent claim: `cf_popen()` children already call `Log()`
after fork on dup2/exec failure (`pipes_unix.c` full-duplex child, and
`unix.c` `ShellCommandReturnsZero()`'s child), directly under the same
"only async-signal-safe functions" banner. The branch is also unreachable in
practice: `setpgid(0,0)` from a fresh fork child can fail only with EPERM
(caller is a session leader — impossible for a new fork child whose pid is
not the session id) — EACCES and EINVAL do not apply. So this is dead code
kept to satisfy the prior panel's must-log constraint, in a file where the
pattern is established. Acceptable. A stricter alternative — a static-string
`write(STDERR_FILENO, ...)`, which is async-signal-safe — would be more
honest than an exception comment, but I do not require it.

### Uncertainty 6 — timing margins

My measurements corroborate the author's: merged single-test run 14.1s wall
(harness included), fail-side runs 36.7s and 32.0s, against a 20s in-test
threshold and the sleep's natural 30s. On macOS the margin is structurally
eaten by the stub platform: `GetProcessState()` cannot see a zombie, so each
`ProcessWaitUntilExited()` rung burns its full ~1s (`STOP_WAIT_TIMEOUT`
999999999ns) even though the SIGINT child died instantly. On Linux,
`process_linux.c` sees the zombie immediately and the ladder returns early,
so the pass side lands even further from 20s. To flake, CI must add ~15s of
scheduling delay to a ~4-5s critical path — the same exposure class as
#6299's existing `timeout_after_output_closed.cf`, which upstream already
accepted. Acceptable; not worth loosening the threshold, which would erode
the fail-side separation (30s natural release vs 20s).

### Uncertainty 7 — the missing complementary discrimination experiment

The gap mattered, so I closed it rather than adjudicating it. In my
scratchpad build I removed **only** the `TimeOut()` group-kill hunk (getpgid
+ guard + `kill(-pid)`), keeping the child `setpgid()`, rebuilt, reinstalled,
and confirmed the installed dylib had actually changed (the getpgid warning
string was gone — stale-binary control): `timeout_kills_descendants.cf`
**FAIL in a 36.7s run**. I then restored `timeout.c` byte-identically
(sha256 `71e1198b...`) and removed only the `setpgid()` hunk — independently
replicating the author's direction: **FAIL in a 32.0s run**. Restored both
(sha256s `71e1198b...` / `7af02763...` matching the reviewed tree), rebuilt:
**Pass, 14.1s**. Both halves are independently load-bearing and the test
discriminates each. The author's one-direction result is now a two-direction
measured result.

### Uncertainty 8 — "before" evidence is a prior session's log

True, and after my runs it barely matters. The claims that need evidence are
about the *merged* state, which I rebuilt from source and measured fresh
(6/6, 63.6s). The pre-merge questions the missing baseline could answer are
bracketed by my experiments: experiment B (merged minus `setpgid`) is
behaviorally equivalent to `0ab083c4d` for the new test — FAIL — so the new
test could not pass against the unmerged #6299 source. Against B-2 alone
(`847373cf6`) it also cannot pass, for a different, read-not-run reason: the
expected `desc_timed_repair_timeout` class requires #6299's
`PROMISE_RESULT_TIMEOUT` classification, which that side lacks. The new test
therefore genuinely requires the union — it is a merge test, not a B-2 test,
which is stronger than what the author claimed for it.

### Uncertainty 9 — `timeout_does_not_leak_to_next_promise.cf`

Confirmed by reading the test: the second promise carries its own
`exec_timeout => "10"`, so the flag reset it exercises is `SetTimeOut()`'s,
not `ClearTimeOut()`'s. It cannot distinguish this resolution from a
flag-clearing one — my flag-clearing run measured it passing. Also note the
inverse blind spot: a promise *without* a timeout never samples the flags at
all (`verify_exec.c:460` gates on `a->contain.timeout != CF_NOINT`), so no
acceptance-level arrangement can observe a leaked or preserved flag. The
pinning must be a unit test; see required change 3.

## The brief's six attack points not already covered

1. **`ClearTimeOut()`/`TIMEOUT_FIRED` ordering** — verified line-by-line;
   see Uncertainty 1. Sample (:460) strictly precedes clear (:502) on every
   reporting path; the merge commit message's reasoning matches the code.
2. **Async-signal-safety of `TIMEOUT_ARMED`** — see Uncertainty 3.
3. **Stale `ALARM_PID` / negative kill.** The prior panel's zombie argument
   holds on the `cf_popen()` path, and extends to the group: `cf_pclose()`
   clears `ALARM_PID` *before* reaping, so while `ALARM_PID` is nonzero the
   child is alive or an unreaped zombie; POSIX forbids reusing a pid that is
   the pid of an existing process (zombies included) or the pgid of an
   existing group, so `kill(-ALARM_PID)` can only reach the original group
   or fail ESRCH. Within one thread the handler cannot interleave with
   `cf_pclose()`'s clear (it runs wholly before or wholly after). The
   reading-`getpgid()`-before-`GracefulTerminate()` order is the
   conservative choice (on Linux `getpgid()` works on zombies; on macOS I
   found no getpgid warnings in any of my test-run logs, so the question
   never surfaced in practice). **Where the argument genuinely fails** is
   the `ShellCommandReturnsZero()` path (advisory 5): reaped child, stale
   `ALARM_PID`, recyclable pid — reachable only via a leaked alarm, root
   cause pre-existing. The guard also earns its keep on live paths I traced:
   a child started by `ShellCommandReturnsZero()` under an armed timeout
   (the nfs remount path arms and then mounts) never calls `setpgid`, so
   `pgid != pid` correctly suppresses the group kill rather than SIGKILLing
   the agent's own group.
4. **`setpgid()` scope and the gate.** The refused unconditional variant is
   confirmed absent; the gate reads a fork-snapshot and is race-free against
   the parent (Uncertainty 3). Two windows exist and both degrade safely:
   the alarm firing between `SetTimeOut()` and fork (>= 1s granularity makes
   this theoretical; result is merely no group), and the alarm firing after
   fork but before the child's `setpgid()` lands (guard sees old pgid,
   skips group kill — falls back to exact #6299 behavior). Failures are
   logged per the panel requirement (`ade76f616`); note the getpgid-failure
   `Log()` is *inside* the signal handler, consistent with the handler's
   pre-existing `Log()` calls. The textbook parent-side `setpgid(pid, pid)`
   mirror would close the second window and let a future revision drop
   `getpgid()` from the handler entirely — worth mentioning in the PR as a
   possible follow-up, not required.
5. **Leaked ARMED state.** Audited every `SetTimeOut()` site in the tree:
   `verify_exec.c:308` (cleared :502; leaks on early returns :330/:374/:393),
   `nfs.c:403` (cleared :581; leaks on :408/:427), `nfs.c:1121` (cleared
   :1177; leaks on :1129), `nfs.c:1434/:1459` (**never cleared** — advisory
   4), `history.c:242` (cf-monitord; cleared :377; leaks on :261/:304/:330/
   :348). Every leak is bounded: the leaked alarm eventually fires and
   `TimeOut()` clears ARMED, and any later `SetTimeOut()`/`ClearTimeOut()`
   supersedes it. But within the window, unrelated `cf_popen()` children
   lead process groups (the refused behavior, by leakage), and a leaked
   alarm firing mid-run escalates per advisory 5. All root causes
   pre-existing; the merge widens consequences. Deferral is coherent for
   the error-path leaks; the nfs success-path sites deserve the two-line
   fix or explicit mention.
6. **The tests** — measured: 6/6 on the merged build; the new test fails
   without either half (both directions run by me); it cannot pass against
   either unmerged side (one measured-equivalent, one reasoned — class
   `repair_timeout` requires #6299).

## Pre-existing defects and the deferral judgment

The author deferred five including `RepairExec()`'s three early returns. My
own audit (list above) found the same early-return family plus two things
that deserve to be on the register if they are not: the never-disarmed
`nfs.c:1434/:1459` (success path, not error path — a different severity
class) and the `ShellCommandReturnsZero()` stale-`ALARM_PID`-after-reap
hole in the zombie argument. Deferring the early-return leaks is right —
they are rare error paths, pre-existing, and fixing them properly (a
scope-guard or arming discipline) is its own change. Shipping the merge
without them is coherent because every new behavior degrades safely when the
invariant is violated: a leaked ARMED makes a child lead a group it did not
need (annoying, the refused behavior, but bounded), and the pgid guard keeps
the group kill away from un-grouped innocents. The two additions above are
the ones close enough to this merge's blast radius that the PR text should
name them even if the code does not fix them.

## Trap control

1. **Never read a return code through a pipe.** Every build and test
   command wrote its rc to a distinct file in the scratchpad immediately
   after execution (`autogen_rc.txt`, `make_baseline_rc.txt`,
   `make_expA_rc.txt`, `make_expB_rc.txt`, `make_expC_rc.txt`,
   `make_restore_rc.txt`, `make_final_rc.txt`, `testrun_*_rc.txt`,
   `pin_probe_cc_rc.txt`); probe outputs went to distinct filenames
   (`pin_probe_merged.out`, `pin_probe_flagclearing.out`,
   `pin_probe_final.out`). Additionally, before every experiment's test run
   I verified the *installed* dylib had actually changed by grepping it for
   the presence/absence of the variant's distinctive message strings —
   which matters doubly here because the `.libs` binaries load the dylib
   from the install prefix, a second place staleness can hide.
2. **`--bindir`.** Not used. I passed explicit `--agent=`, `--cfpromises=`,
   `--cfserverd=`, `--cfexecd=`, `--cfkey=`, `--cfnet=`, `--cfcheck=`. I
   hit the trap's signature twice anyway — six FAILs in 0.8s (missing
   `fakeroot` on macOS; fixed with `--gainroot=env`) and six FAILs in 2.7s
   (raw `.libs` binaries aborting on a missing dylib at the configured
   prefix; fixed with `make install` into my scratch prefix) — and treated
   both as harness bugs per the trap, never as results. A >60s six-test run
   was the plausibility bar for accepting any suite outcome.
3. **libtool wrappers / failsafe fallback.** `--cfpromises` pointed at
   `cf-promises/.libs/cf-promises` (the real Mach-O), `--agent` at
   `cf-agent/.libs/cf-agent`; `cf-check` has no `.libs` binary in this
   layout (it links statically at `cf-check/cf-check`, verified Mach-O with
   `file`). `CFENGINE_TEST_OVERRIDE_WORKDIR` is exported by the harness
   itself (`testall:480`) — verified in the script, and per-test workdirs
   confirmed it took effect.
4. **Single-process ladder probes.** Not applicable as I ran no ad-hoc
   wall-clock ladder probes; all timing came from the acceptance test,
   whose multi-process shape is the point of the test, not a confound. The
   32-36s fail-side times are the surviving `sleep 30` holding the pipe —
   which in these experiments is the *measured effect*, not the trap.
5. **Platform.** Everything measured here is macOS 26.6.1 (25G76) arm64,
   Apple clang 21.0.0, stub process layer (`process_unix_stub.c` — cannot
   see ZOMBIE/STOPPED, so every ladder rung waits its full ~1s). Reasoned
   about but **not** measured: all Linux behavior (zombie-aware ladder
   early-exit, `getpgid()` on zombies, tighter pass-side margins), and the
   entire MinGW/Windows analysis in Uncertainty 2, which comes from
   Makefile conditionals, configure checks, platform.h, and the tree-wide
   `kill()` fencing pattern — I have no MinGW toolchain and ran no Windows
   compile. The claim there is "very likely breaks", not "measured broken".
   Also read-not-run: the assertion that the new test would fail against
   B-2-alone (`847373cf6`) — reasoned from the missing `repair_timeout`
   class, not built.

## What I measured, in one table

| Build variant | Test | Result | Wall |
|---|---|---|---|
| Merged (HEAD `3d8e90d68`) | all six acceptance | 6/6 Pass | 63.6s |
| Merged | pin probe | PIN-PASS | — |
| Minus `TimeOut()` group-kill hunk only (exp. A — the direction the author skipped) | `timeout_kills_descendants.cf` | FAIL | 36.7s |
| Minus child `setpgid()` hunk only (exp. B — replicating the author) | `timeout_kills_descendants.cf` | FAIL | 32.0s |
| Restored byte-identical (shas match reviewed tree) | `timeout_kills_descendants.cf` | Pass | 14.1s |
| `ClearTimeOut()` clearing all flags (wrong resolution, exp. C) | all six acceptance | 6/6 Pass | 61.2s |
| Exp. C | pin probe | PIN-FAIL (`cleared TIMEOUT_FIRED`) | — |

Build health: independent from-source build rc 0; exactly 2 warnings
(`evalfunction.c:674`, `variable.c:296`), matching the author's report;
zero new.

One nit for the register: the brief cites the `setpgid` gate at
`pipes_unix.c:254`; in the reviewed tree it is at :256-258.
