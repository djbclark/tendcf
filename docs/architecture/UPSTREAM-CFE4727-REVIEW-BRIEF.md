# UPSTREAM REVIEW BRIEF — CFE-4727, CFEngine core exec_timeout termination half

**Frozen input, 2026-08-18.** This is the shared prompt given verbatim to each
member of the second-opinion panel. Do not edit it to reflect what the reviews
later find — the reviews are separate files, and the register records the
outcome.

---

## Your role

You are an independent reviewer of a C fix that is about to be offered to an
upstream open-source project (CFEngine Core, by Northern.tech). It was written
by a different AI model. Your job is **adversarial**: assume the fix is wrong
and try to demonstrate it. A review that finds nothing is a valid outcome, but
only after a real attempt.

This is **signal-handler code** (a `SIGALRM` handler races an `ALARM_PID`
global against `sigprocmask()`-guarded clears in the main thread). Weight
async-signal-safety, ordering and reentrancy accordingly.

The author's own uncertainties are listed at the bottom. Address each of them
explicitly and by name. Do not simply agree with the author's framing — the
framing may itself be the error.

## Where the code is

Repository: `/Users/djbclark/src/core-alarmpid`, a worktree of a fork of
`cfengine/core`, on branch `fix/exec-timeout-alarm-pid`, one commit
(`254cbe593`) ahead of `dbf759d16` (tip of the already-merged
`fix/timeout-process-group-merged`, i.e. it carries B-2/B-8's process-group
and flag work).

```
git -C /Users/djbclark/src/core-alarmpid log --oneline -5
git -C /Users/djbclark/src/core-alarmpid show 254cbe593
```

Read the surrounding files, not just the diff:

- `libpromises/pipes_unix.c` — new `ClearAlarmedPid()`, `cf_pclose()`,
  `cf_pclose_full_duplex()`, `cf_popen()`/`cf_popen_sh()` (where `ALARM_PID`
  is first set and the child forks), `cf_pwait()` (the blocking `waitpid()`)
- `libpromises/timeout.c` — `TimeOut()` (the `SIGALRM` handler itself),
  `SetTimeOut()`, `ClearTimeOut()`, the `TIMEOUT_SIGNALLED` comment this
  commit rewrote
- `cf-agent/verify_exec.c` — `RepairExec()`, the only `exec_timeout`-guarded
  caller of `SetTimeOut()`/`cf_popen()`/`cf_pclose()`
- `tests/unit/timeout_test.c` — the new unit test, and
  `test_clear_preserves_a_true_signalled_flag` (the existing test whose
  direct-registration pattern the new test's flake fix copies)
- `tests/acceptance/08_commands/04_exec_timeout/timeout_after_output_closed.cf`
  — rewritten to assert termination, not just detection

You have read access to the whole repo and the web. **Write nothing except
your own output file. Do not commit, push, branch, or modify any existing
file.**

## What the defect was

`cf_pclose()` cleared `ALARM_PID = -1` as its **first** action, before
`fclose()` and before `cf_pwait()`'s unbounded `waitpid()`. A command that
closes stdout/stderr but keeps running ends the agent's read loop at EOF, so
by the time the alarm fires the agent is already inside that wait — and
`TimeOut()`, finding `ALARM_PID == -1`, terminates nothing. The command ran
to completion, entirely unbounded by `exec_timeout`. CFE-4726 (already
merged) made the resulting error message honest ("was NOT terminated and ran
to completion") but left the actual gap open — `timeout.c` had a comment
explicitly documenting it as *accepted*, not a TODO.

## What the fix does

New `ClearAlarmedPid(pid)` in `pipes_unix.c`: blocks `SIGALRM`
(`sigprocmask(SIG_BLOCK, ...)`, saves the old mask), clears `ALARM_PID` only
if it still equals `pid`, unblocks by restoring the saved mask
(`SIG_SETMASK`). Called from both `cf_pclose()` and `cf_pclose_full_duplex()`
**after** `cf_pwait()` returns (i.e. after the reap), replacing the old
unconditional `ALARM_PID = -1;` that ran **before** the wait. The three error
paths in `cf_pclose()` that previously pre-cleared (`fd >= MAX_FD`, a failed
`fclose()`, `pid == 0`) now leave `ALARM_PID` set instead.

## What the review must attack

1. **Does `ClearAlarmedPid()` actually close the race, or just narrow it?**
   Walk the exact instruction sequence: `waitpid()` returns inside
   `cf_pwait()` → control returns to `cf_pclose()` → `ClearAlarmedPid(pid)`
   runs → `sigprocmask(SIG_BLOCK, ...)` takes effect. Is there truly a window
   between the reap and the block where a delivered `SIGALRM` could read
   `ALARM_PID` naming an already-recycled pid? Is the author's claim that
   this window is now merely a handful of instructions (versus the old
   code's deterministic gap) accurate, or understated?
2. **`sigprocmask()` vs `pthread_sigmask()`.** `cf_pclose()` is reachable
   from cf-serverd/cf-execd worker threads. POSIX leaves plain
   `sigprocmask()` in a multithreaded process unspecified per-thread.
   Determine whether this is a real defect for this specific call site (is
   `cf_pclose()` actually called from worker threads in practice?) or
   theoretical.
3. **The three error paths that now leave `ALARM_PID` set.** `fd >= MAX_FD`,
   a failed `fclose()`, and `pid == 0` all previously cleared `ALARM_PID`
   before returning early; now they don't. The author's claim is that the
   child is unreaped in each case (so the pid can't be recycled) and a
   pending alarm can still usefully terminate it. Verify this for each of
   the three paths individually — is the child actually still alive and
   unreaped on every one, or does any path leave a stale/wrong pid
   registered with nothing left to signal?
4. **`cf_pclose_full_duplex()`'s symmetry fix.** The author states no
   `exec_timeout`-guarded path reaches it (only `mapdata()`'s json_pipe mode,
   package modules, custom promise modules — verified via
   `grep -rln "SetTimeOut(" --include=*.c .` showing only `verify_exec.c`,
   `nfs.c`, `cf-monitord/history.c`, all half-duplex callers). Confirm this
   grep-based claim yourself rather than accepting it. If true, is applying
   the identical fix there anyway (for symmetry, not necessity) actually
   inert, or does it change behavior for a non-`exec_timeout` caller that
   happens to also set `ALARM_PID` some other way?
5. **The rewritten `TIMEOUT_SIGNALLED` comment in `timeout.c`.** It now
   attributes remaining "no process" cases to two windows: an alarm before
   `cf_popen()`'s fork publishes the pid, and one after `cf_pclose()`'s reap.
   Is that an accurate and complete list, or does the fix (or the pre-fix
   code) admit a third window the comment misses?
6. **The pre-fork race, deliberately left unfixed.** `SetTimeOut()` is
   called before `cf_popen()`'s fork publishes the child's pid into
   `ALARM_PID`; a short `exec_timeout` on a loaded host can fire in that
   window with nothing registered to terminate. The author found this
   *empirically* this session (a real flake under `make check`'s parallel
   load, not a theoretical concern) but chose not to fold a fix into this
   commit, leaving it for its own ticket. Is that the right scope call, or
   is it close enough to this commit's own subject matter that shipping
   CFE-4727 without it is misleading about what guarantee the fix actually
   provides?
7. **The tests.** Does the acceptance test
   (`timeout_after_output_closed.cf`) genuinely discriminate — fail without
   the fix, pass with it — or could it pass against the unfixed source for
   an unrelated reason (e.g. the termination ladder's other waits masking
   the gap)? Same question for the unit test's core assertions in
   `tests/unit/timeout_test.c`.

## Traps you must control for

These have burned prior work in this series. Your review must state what you
did about each.

1. **Never read a return code through a pipe.** A prior session reported a
   stale binary's output as a fixed result because a failed `cc`'s rc came
   from a pipe. Write `echo "RC=$?"` to a file immediately after the
   command; use distinct output filenames for anything you compile.
2. **`--bindir` is wrong for an in-tree acceptance-test build.** The harness
   needs explicit `--agent=` / `--cfpromises=` / `--cfserverd=` / … paths.
   All tests failing in ~2 seconds is a harness bug, not a real result — this
   suite contains a deliberately ~20-30s test and cannot fail that fast.
3. **`cf-promises` in the build tree is a libtool wrapper script**, not the
   binary; the real one is `cf-promises/.libs/cf-promises`. Using the
   wrapper makes `cf-agent` silently fall back to failsafe and return having
   run nothing. Also check `CFENGINE_TEST_OVERRIDE_WORKDIR` is set.
4. **A wall-clock probe needs a single-process command.** `sh -c "sleep 30"`
   spawns a grandchild that can survive termination of the immediate child
   and keep the pipe open — measuring a *different* defect than the one
   under test, and making a correct fix look broken. Prefer `exec sleep 30`
   (chained exec, single process) if you write your own probe, matching what
   this commit's own tests already do.
5. **Platform.** The host is **macOS 26.6.1 (25G76), arm64**. macOS has no
   `process_darwin.c`; `GetProcessState()` only distinguishes "exists" from
   "does not exist" via `kill(pid, 0)` and can never report `ZOMBIE` or
   `STOPPED` (CFE-4718, unfixed, unrelated). The termination ladder's waits
   are iteration-counted and overshoot several-fold on Darwin (CFE-4728,
   unfixed, unrelated) — expect terminated-command wall clock around
   15-20s, not the ~2s a fixed ladder would give. Say plainly which claims
   are measured here and which are reasoned about Linux.
6. **If you run the unit test under parallel/loaded conditions**
   (`make check`, or your own concurrent load), you may reproduce the
   pre-fork flake described in item 6 above — that is a **known, already-
   documented** finding, not a new bug, unless you find it manifests
   differently than described.

A review that asserts a before/after difference it did not measure is worth
less than one that says "I could not run this, here is what I read instead."

## What the author actually did

One commit, `254cbe593`, on `fix/exec-timeout-alarm-pid`
(4 files, 150 insertions, 22 deletions):

- `libpromises/pipes_unix.c` — new `ClearAlarmedPid()`; both `cf_pclose()`
  and `cf_pclose_full_duplex()` now clear `ALARM_PID` after `cf_pwait()`
  instead of before.
- `libpromises/timeout.c` — comment rewrite only, no logic change.
- `tests/acceptance/08_commands/04_exec_timeout/timeout_after_output_closed.cf`
  — rewritten from "detect and report" to "detect, terminate, and don't
  reach a post-sleep completion marker"; adds start/end mtime markers and a
  25s elapsed bound.
- `tests/unit/timeout_test.c` — new test driving real `cf_popen_sh()`/
  `cf_pclose()` under a 2s timeout, asserting `TimeOutSignalledProcess()`
  true, non-zero close status, `ALARM_PID` cleared after reap, bounded
  elapsed time. Registers the child by directly-known pid (not via
  `ALARM_PID` after `cf_popen()`) to avoid the pre-fork race window in the
  test's own setup.

Build: incremental, 0 new warnings. Unit tests: 7/7 pass, ~35s (dominated by
the new test's 30s-adjacent waits), reconfirmed under 4×(8-way CPU load).
Acceptance: target test 18s wall (25s bound), all 6 tests in the directory
6/6 pass, 89s total.

Discrimination: `git checkout HEAD~1 -- libpromises/pipes_unix.c
libpromises/timeout.c` (revert only the fix, keep the new tests), rebuilt,
reran — fails exactly at `timeout_test.c:129`'s `TimeOutSignalledProcess()`
assertion. Restored, rebuilt, reran clean, tree byte-identical
(`git status --porcelain` empty).

## The author's uncertainties

Address each explicitly and by name.

1. **The residual pid-recycling race** between `waitpid()` returning and
   `sigprocmask(SIG_BLOCK, ...)` taking effect inside `ClearAlarmedPid()` —
   the author calls it "a handful of instructions," reachable only if the
   alarm fires in exactly that window *and* the OS recycles the pid in the
   same microseconds. Judged acceptable given the pre-fix code dropped the
   guarantee deterministically. Do you agree with that risk framing?
2. **`sigprocmask()` thread-safety**, per attack point 2 above — the author
   left it as `sigprocmask()`, not `pthread_sigmask()`, judging it
   sufficient because nothing else in this file blocks `SIGALRM` in the
   main thread (the only other `sigprocmask()` in `pipes_unix.c` runs in
   the forked child). Is that reasoning sufficient, or does the multi-
   threaded reachability of `cf_pclose()` from server/exec workers make
   this a real defect regardless?
3. **The full-duplex symmetry fix's blast radius**, per attack point 4 —
   the author's own note is that it "marginally widens an already-existing
   leaked-alarm blast radius (B-15/B-16 family) during the reap window,"
   disappearing once those leaks are fixed. Judge whether shipping it
   anyway is net-positive or should wait.
4. **`ALARM_PID` remains a non-volatile `pid_t`**, relying on
   `sigprocmask()` calls as compiler barriers rather than `volatile`. Is
   that a real gap, or does the existing `sigprocmask()`-guarded
   read/write pattern make `volatile` unnecessary here?
5. **The pre-fork race's scope decision**, per attack point 6 — is leaving
   it for its own ticket defensible, or does this commit's subject line
   ("exec_timeout never terminating...") implicitly promise more than it
   delivers while that window remains open?

## Pre-existing defects the author found and deliberately did NOT fix

- The pre-fork `ALARM_PID`-publish race (attack point 6 / uncertainty 5) —
  empirically confirmed this session via a test flake under load, not
  previously verified, only theorized in a prior review document.
- CFE-4728 (termination ladder's iteration-counted waits overshoot on
  Darwin) and CFE-4718 (`GetProcessState()` blind to child death on
  platforms without `process_darwin.c`) — both pre-existing, both drive
  this fix's own test timing, neither touched here.

Judge whether deferring any of these is right, or whether one is entangled
enough with this fix that shipping without it is incoherent.
