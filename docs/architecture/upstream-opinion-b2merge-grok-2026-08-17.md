# Independent review: B-2 merged onto cfengine/core#6299

Reviewer: grok
Date: 2026-08-17
Subject: `/Users/djbclark/src/core-b2merge`, branch `fix/timeout-process-group-merged`
HEAD: `3d8e90d68` (merge `8793f3747` + logging `ade76f616` + test `3d8e90d68`)
Baseline: `0ab083c4d` (live #6299)
Incoming: `847373cf6` (`fix/timeout-process-group`)

This review assumes the resolution is wrong and tries to show it. It is not a paraphrase of the author's notes.

## Verdict

The two-sided union in `timeout.c` / `timeout.h` is the intended shape, and the dangerous auto-merge of `cf-agent/verify_exec.c` kept #6299's sample-then-disarm order. I could not make `ClearTimeOut()` eat `TIMEOUT_FIRED` on any path that reports a timeout outcome. I could not make the `pgid == ALARM_PID` guard fire a negative kill at the agent's own group on the intended path. The new descendant test does discriminate, and both halves of B-2 are required for it.

I would not offer this to Northern.tech as it stands. `timeout.c` is compiled on MinGW. The merge adds `getpgid()` and `kill(-pid, SIGKILL)` there with no `#ifndef __MINGW32__`. That is a new undeclared POSIX pair in a file master already ships to NT; it is not the same as master's existing `GracefulTerminate()` call. The rest is smaller: `TIMEOUT_ARMED` should have become `volatile sig_atomic_t` in the merge, and B-2's `TimeOutIsArmed()` gate re-prices three pre-existing `RepairExec()` leaks. Those last two are one-line / three-line follow-ups, not a reason to unwind the union.

## What I actually read

Both pre-merge `timeout.c` / `timeout.h` (`0ab083c4d`, `847373cf6`), the merged files, `8793f3747`/`ade76f616`/`3d8e90d68` messages, `cf-agent/verify_exec.c` (`RepairExec` in full, plus the three-way diff), `libpromises/pipes_unix.c` (`GenericCreatePipeAndFork`, `cf_popen*`, `cf_pclose`/`cf_pwait`), `libpromises/process_unix.c` (`GracefulTerminate` / `ProcessWaitUntilExited` / `SafeKill`), `libpromises/process_unix_stub.c`, `libpromises/process_lib.h`, `libpromises/locks.c` (`KillLockHolder`), `libpromises/Makefile.am`, `libntech/libutils/platform.h` (dummy `SIGKILL`), `cf-execd/cf-execd-runner.c` (the existing `getpgid`/`kill(-pid)` `#ifndef`), `cf-agent/nfs.c` and `cf-monitord/history.c` (the other `SetTimeOut`/`ClearTimeOut` callers), `libpromises/unix.c` (`ALARM_PID` around `ShellCommandReturnsZero`), `libpromises/cf3globals.c` (`ALARM_PID` definition), all six tests under `tests/acceptance/08_commands/04_exec_timeout/`. I did not read any other `upstream-opinion-*` file or anything under `docs/handoffs/`.

## 1. `ClearTimeOut()` / `TIMEOUT_FIRED`

The hazard is real in the abstract and not live in the merged `RepairExec()`.

`verify_exec.c` auto-merged because the two sides touched different lines. #6299 samples after `cf_pclose()` and before the disarm; B-2 replaces that disarm with `ClearTimeOut()`. The merge kept both. The actual order on the only path that reports a timeout outcome is:

1. `cf_pclose()` (which sets `ALARM_PID = -1` before `waitpid`)
2. `timed_out = (timeout != CF_NOINT) && TimeOutHasFired()`
3. if timed out, `TimeOutSignalledProcess()` chooses the error string
4. later, `ClearTimeOut()`
5. `return timed_out ? ACTION_RESULT_TIMEOUT : ACTION_RESULT_OK`

`ClearTimeOut()` writes only `TIMEOUT_ARMED`. `TIMEOUT_FIRED` and `TIMEOUT_SIGNALLED` stay readable until the next `SetTimeOut()`. That is written in the function body and in `timeout.h`.

There is no path that reports a timeout after a disarm. There are three paths that neither sample nor disarm — see §Deferred. Those paths return `ACTION_RESULT_FAILED` and never consult the flags, so a `ClearTimeOut()` that wiped `TIMEOUT_FIRED` would not change them either.

`history.c` and `nfs.c` never read the flags. They cannot regress #6299's classification even if `ClearTimeOut()` were the wrong function.

So: the author did not silently revert timed-out promises to compliant. The auto-merge did the right textual thing. A future caller that disarms and then samples would still be saved by the lifetime contract. Today's six tests would not notice if that contract were inverted. That is a pinning gap, not a live bug. See uncertainty 1.

## 2. Async-signal-safety of `TIMEOUT_ARMED`

The merged code preserved B-2's `static bool TIMEOUT_ARMED`. It did not promote it. `nm` on `libpromises/.libs/timeout.o` shows `_TIMEOUT_ARMED` next to the two `sig_atomic_t` siblings. On this host `sizeof(bool) == 1` and `sizeof(sig_atomic_t) == 4`.

It matters formally. `TimeOut()` is the `SIGALRM` handler and writes the flag; `SetTimeOut()` / `ClearTimeOut()` write it from ordinary control flow; `TimeOutIsArmed()` reads it. POSIX only blesses `volatile sig_atomic_t` for that pattern. A torn 1-byte store is not a realistic failure on CFEngine's Unix platforms. Missing `volatile` is the sharper issue: a compiler is entitled to cache the value across a window in which a signal can fire. Nothing in the current callers loops on `TimeOutIsArmed()`, so I could not turn that into a concrete miscompile. It is still the wrong type to leave sitting beside two correctly typed siblings that the same handler writes.

`TimeOutIsArmed()` in `cf_popen()`'s child is not a reason to keep `bool`. The child reads a copy of the parent's address space after `fork()`. That read is ordinary. Changing the storage to `volatile sig_atomic_t` and returning `TIMEOUT_ARMED != 0` does not change the child's decision. The author's "already reviewed on 2026-08-16" reason does not transfer: that panel reviewed B-2 alone, with no `sig_atomic_t` neighbours. The merge is what creates the inconsistency, so the merge (or a one-line follow-up next to `ade76f616`) is the right place to fix it.

I would not unwind the union over this. I would not ship the inconsistency on purpose either.

## 3. Stale `ALARM_PID` and the negative kill

The guard is `getpgid(ALARM_PID)` first, then `GracefulTerminate(ALARM_PID, PROCESS_START_TIME_UNKNOWN)`, then `if (pgid == ALARM_PID) kill(-ALARM_PID, SIGKILL)`.

What the comment claims: after `GracefulTerminate()`, `getpgid()` fails with `ESRCH`, so the group must be read first.

What I measured on this host (macOS 26.6.1 arm64), throwaway `/tmp/b2merge-review/probe_getpgid`:

| state | `getpgid` | `kill(pid, 0)` |
|---|---|---|
| unreaped child after `_exit` | `-1` `ESRCH` | `0` (exists) |
| live child | pgid, success | `0` |
| unreaped child after `SIGKILL` | `-1` `ESRCH` | `0` (exists) |
| after `waitpid` | `-1` `ESRCH` | `-1` `ESRCH` |

So on macOS the comment is true, and stronger than written: `getpgid` fails on an unreaped zombie even when the child just `_exit`ed, no kill required. Reading the group *before* `GracefulTerminate()` is necessary here. A post-kill `getpgid` would skip the group kill on every timeout and the descendant test would fail.

I did not measure Linux. On Linux `getpgid` of an unreaped zombie is generally reported to succeed. The "read first" order is still the safer one; it is not optional padding.

The prior-panel claim that PID recycling is impossible because the process is an unreaped zombie: **true for the PID, false as a reason to getpgid after the kill.** `kill(pid, 0)` succeeding is exactly what `process_unix_stub.c` uses as "exists", so a macOS zombie keeps its PID reserved. A new process cannot take `ALARM_PID` until someone `wait`s. `TimeOut()` does not wait. `cf_pclose()` sets `ALARM_PID = -1` *before* it waits. I found no `waitpid(-1)` in `libpromises`; the waiters are `cf_pwait(pid)` and `ShellCommandReturnsZero`'s specific pid. On the intended path the leader stays an unreaped zombie through the group kill, the PID is reserved, and because a group leader's pgid equals its pid the **group id is reserved too**. The zombie argument holds for group reuse. It does not hold for "therefore `getpgid` after `GracefulTerminate` is fine."

Attacks that do not land on the intended path:

- `pgid == ALARM_PID` is "this pid leads its own group", which is what `setpgid(0,0)` in the child establishes. If `setpgid` failed, the child is still in the agent's group, `pgid != ALARM_PID`, and the negative kill is skipped. That is the case the guard exists for. I did not find a way for a live `cf_popen` child to have `pgid == pid` without having called `setpgid`.
- `kill(-ALARM_PID)` vs `kill(-pgid)` is the same number when the guard passes.
- `ALARM_PID == 0` would make `kill(-0)` mean "signal my group". `getpgid(0)` is self, not 0, so the guard does not pass. `SetTimeOut()` also sets `ALARM_PID = -1` before arming.

Attack that lands only if `ALARM_PID` is not our unreaped child: a recycled pid that happens to be a group leader. `GracefulTerminate` then `kill(-pid)` would destroy that tree. That requires a foreign waiter plus pid wrap inside the ~2 s ladder. I could not construct it from this tree. It is the same class of hole `SafeKill` exists to close, and `TimeOut()` already calls `GracefulTerminate(..., PROCESS_START_TIME_UNKNOWN)`, so the start-time check is off. Pre-existing. On this host `GetProcessStartTime()` is the stub and always returns `UNKNOWN` anyway; that claim is measured here. The Linux `SafeKill` path was read, not run.

`ALARM_PID` itself is a plain `pid_t` in `cf3globals.c`, not `volatile sig_atomic_t`, and `TimeOut()` reads it. Pre-existing, same family as `TIMEOUT_ARMED`.

## 4. `setpgid()` scope

The unconditional `setpgid(0,0)` the 2026-08-16 panel refused is not in this tree. The child does:

```c
if (TimeOutIsArmed()) {
    if (setpgid(0, 0) != 0) {
        Log(LOG_LEVEL_WARNING, "...");
    }
}
```

at `pipes_unix.c:256`. `sha256` of that file is `7af027630c409cbd2b07c4e22c645c3d1e777231afd75bf58c46bf440a6ec4a6`, the hash the author quoted after restoring the hunk.

The gate is the right predicate: "will this timeout have to kill this child as a tree?" `RepairExec()` / `nfs.c` / `history.c` call `SetTimeOut()` on the same thread before `cf_popen()`. The child inherits `TIMEOUT_ARMED` at `fork()`. That is not a data race. The remaining window is the pre-existing one: `SetTimeOut()` sets `ALARM_PID = -1` and arms the clock, then the parent does umask / argv work, then forks. If the alarm fires in that window, `TimeOut()` sees `ALARM_PID == -1`, does not kill, and the child is born with `TIMEOUT_ARMED == false` (the handler already cleared it). That child does not `setpgid`, and nothing will kill it. #6299 already documents that case as "timed out but was never terminated." B-2 does not make it worse.

A smaller window: alarm fires after `fork()` returns in the parent and before the child runs `setpgid`. `getpgid` then sees the inherited group, the guard skips, descendants survive. Classic fix is parent+child `setpgid`. They only do the child. For `exec_timeout >= 1` the remaining time at `fork` is almost the full timeout; I could not turn this into a practical failure. It is a residual race, not a reason to restore unconditional `setpgid`.

Failures are logged. `setpgid` failure: `LOG_LEVEL_WARNING` in the child, command stays in the agent's group, guard skips the negative kill. `getpgid` failure: `LOG_LEVEL_WARNING` in the handler, group kill skipped. The silent-swallow complaint from the earlier pass is gone.

## 5. Leaked `ARMED` state

Yes. `TIMEOUT_ARMED` is set by `SetTimeOut()` and cleared by `ClearTimeOut()` or by `TimeOut()`. Any `SetTimeOut()` that does not reach a `ClearTimeOut()` and whose alarm has not fired leaves the next `cf_popen` child leading a process group. That is exactly the behaviour the 2026-08-16 panel refused to apply unconditionally: `SIGTTIN` on an interactive read, and the child drops out of the group `cf-execd` / the terminal would signal.

`RepairExec()` after `SetTimeOut()`:

1. Powershell on Unix — `return ACTION_RESULT_FAILED` at the "Powershell is only supported on Windows" branch.
2. `pfp == NULL` after `cf_popen*`.
3. `CfReadLine` error — `cf_pclose` (so `ALARM_PID = -1`) then `return ACTION_RESULT_FAILED`.

Those are the three early returns the author named. They leak the armed alarm as well as `ARMED`. The leftover alarm is pre-existing and already able to fire into a later `cf_popen`'s `ALARM_PID`. B-2 adds the `setpgid` consequence.

Other leaks I found, not just those three:

- `LoadMountInfo()`: `SetTimeOut` then `cf_popen` failure, and the `CfReadLine` error return. Both skip the success-path `ClearTimeOut()`.
- `MountAll()`: `SetTimeOut` then `cf_popen` failure returns without `ClearTimeOut()`.
- Remount / `unmount_mount` in `nfs.c`: `SetTimeOut(timeout)` on the success path with **no** matching `ClearTimeOut()` at all. This is not an early return. After a remount, `ARMED` stays true until something else disarms or the leftover alarm fires.
- `history.c` `NovaReSample()`: `SetTimeOut` then several returns (stat failure, Powershell on Unix, `fin == NULL`, read error) that never reach `ClearTimeOut()`.

A promise that finishes before the alarm does **not** leak, on the paths that call `ClearTimeOut()`. That is the function's reason to exist.

See §Deferred for whether shipping without the `RepairExec` trio is coherent.

## 6. The tests

I ran all six against the existing in-tree build (not rebuilt by me). Harness details are in §Trap control. Results, each `RC` written to its own file immediately after the agent:

| test | outcome | agent rc | wall s |
|---|---|---|---|
| `timeout_overrides_exit_zero.cf` | Pass | 0 | 11.613 |
| `timeout_overrides_kept_returncodes.cf` | Pass | 0 | 11.001 |
| `timeout_does_not_leak_to_next_promise.cf` | Pass | 0 | 11.490 |
| `within_timeout_normal_outcomes.cf` | Pass | 0 | 2.732 |
| `timeout_after_output_closed.cf` | Pass | 0 | 10.632 |
| `timeout_kills_descendants.cf` | Pass | 0 | 10.706 |

Sum 58.2 s. `timeout_after_output_closed` is the deliberate ~10–12 s test; it ran for 10.6 s and printed `it was NOT terminated and ran to completion`. This was not a failsafe / `--bindir` / wrapper collapse.

`timeout_kills_descendants.cf` also printed `exceeded exec_timeout of 2 seconds and was terminated`. Marker files in the per-test workdir:

- `desc_start` mtime 1787001152.641
- `desc_end` mtime 1787001162.794
- marker elapsed **10.154 s**, under the test's 20 s bound

The test's `dcs_passif_expected` requires `desc_timed_repair_timeout` and `bounded`, and forbids kept/repaired. That needs #6299's classification *and* B-2's kill. I did not rebuild `0ab083c4d` to prove the fail-without-B-2 side on the real agent. I did run a standalone probe that is the same shape (`sh -c "sleep 30"` holding a pipe, INT/TERM/KILL ladder, optional `setpgid`, optional `kill(-pid)`):

| variant | elapsed s |
|---|---|
| no `setpgid`, group-kill guarded on `pgid == pid` | 30.016 |
| `setpgid`, no group kill | 30.124 |
| both halves | 7.204 |

So the new test cannot pass against #6299 alone (pipe held ~30 s, `bounded` fails). It also cannot pass against B-2's `setpgid` half alone: that is the complementary experiment the author did not run, and it is a 30 s fail. Both hunks are load-bearing. A 20 s bound sits ~10 s above the pass I measured on the real agent and ~10 s below the fail I measured on the probe. See uncertainty 6.

Could the new test pass against the unmerged source? Not if "unmerged" means `0ab083c4d`. I did not rerun that tree (uncertainty 8). The probe is why I am willing to say so anyway.

`timeout_does_not_leak_to_next_promise.cf` still passes and still cannot see `ClearTimeOut()`'s flag contract. The second promise calls `SetTimeOut(10)`, which zeroes `TIMEOUT_FIRED` itself. See uncertainties 1 and 9.

## Author's uncertainties

### 1. "The hazard is latent, not live."

The latency claim is true. The framing that this is a question of over-caution about the *contract* is the error. Leaving `TIMEOUT_FIRED` set across `ClearTimeOut()` is not caution, it is the only contract that does not make every future caller order-dependent. The thing that is unpinned is the contract, not the current `RepairExec()` order.

A reviewer should demand that the contract be *stated* (it is, in two places) and should not pretend the six tests prove it. A reviewer should not block the merge for lack of a unit test of an eight-line function. If they want a pin, the pin is a unit test of `ClearTimeOut()` / `TimeOutHasFired()`, not another `commands:` acceptance test. `timeout_does_not_leak_to_next_promise.cf` cannot do that job (uncertainty 9).

### 2. "Windows/MinGW build unverified — the author's own biggest worry."

The worry is right. The soothing comparison to master's `GracefulTerminate()` is the error.

- `libpromises/Makefile.am:163` compiles `timeout.c` unconditionally.
- `pipes_unix.c` (the `setpgid` half) is `if !NT`.
- `platform.h` defines a dummy `SIGKILL` of 6 under `__MINGW32__` and does not provide `getpgid`.
- libntech has no `getpgid` compat.
- `cf-execd/cf-execd-runner.c:277-314` already wraps **the same two calls** (`getpgid`, `kill(-pid)`) in `#ifndef __MINGW32__`. That is this repo's pattern for this exact POSIX pair.
- master's `TimeOut()` calling `GracefulTerminate()` is a different symbol. `process_lib.h` even says the Windows implementation is not in this tree ("once windows implementation is merged"). Enterprise can satisfy `GracefulTerminate`. It will not satisfy a raw `getpgid()`.

I did not compile with MinGW. There is no MinGW toolchain on this host (`command -v x86_64-w64-mingw32-gcc` empty). The claim is reasoned, not a recorded compiler error. It is still enough to require an `#ifndef __MINGW32__` around the `getpgid` / `kill(-pid)` block in `TimeOut()` before this is offered upstream. That is not speculative decoration. Adding it in a follow-up next to `ade76f616` is fine; offering without it is not.

### 3. "`TIMEOUT_ARMED` is a plain `bool`"

Addressed in §2. The "already reviewed" reason does not transfer. The merge is the right place to change the type. `TimeOutIsArmed()` in the child is unaffected.

### 4. "`getpgid()` in a signal handler"

Correct: it is not on the POSIX async-signal-safe list; `setpgid` and `kill` are. `TimeOut()` already calls `Log()` and `GracefulTerminate()` (the latter does `nanosleep`, `GetProcessState`, and more `Log()`). Adding `getpgid` does not create a new class of unsafety. On this host it is a thin syscall that works on a live process and fails on a zombie (measured). Formally unspecified. I would mention it in the PR, not block on it. Putting it *before* `GracefulTerminate()` is required on macOS (measured), so the formal hole cannot be removed by moving the call.

### 5. "The child-side failure `Log()`"

The banner at `pipes_unix.c:226` does say "only call async-signal-safe functions in child." The author's claim that nearby `cf_popen` children already `Log()` is true: `execv`, `chroot`, and `chdir` failures in `cf_popensetuid` all `Log()` and `_exit`. This is the house style, not a new exception.

"Unreachable" is slightly oversold. `setpgid(0,0)` on a freshly forked non-session-leader child has no remaining documented failure I can name either, but "no documented error" is not "unreachable." Confining `Log()` to the failure branch is the least-bad way to meet the must-log constraint. I would not revert the log.

### 6. "Timing margins of the new test"

The author's 10–12 s pass / ~31 s fail picture is the right quantity: I measured **10.154 s** of marker elapsed on the real agent, and **30.0–30.1 s** on each failing half of the standalone probe. The 20 s bound has ~10 s of room each way on this host, not a thin 9 s invented from testall wall clock.

What I will not accept is the implication that 10 s is "timeout plus the INT/TERM/KILL ladder." A single-process ladder (process ignores INT/TERM, no grandchild; trap 4) took **2.122 s** on this host. The extra ~8 s on the real test is macOS-specific waste in `GracefulTerminate` plus whatever delay sits between the group kill and pipe EOF. `process_unix_stub.c` is what this build links (`process_unix_stub.o` present, `process_linux.o` absent). `GetProcessState()` cannot report `ZOMBIE`; `kill(pid, 0)` on a zombie succeeds (measured). Each `ProcessWaitUntilExited(~1s)` therefore burns the full second on a process that is already dead. That 2 s is measured behaviour of the stub, not of Linux.

A loaded Linux CI runner will see a *shorter* pass (zombie ends the first wait immediately) and the same ~30 s fail. The flake mode that would hurt is a runner so slow that the pass climbs through 20 s. Possible. I would not tighten the bound. I would not block. I would not describe 20 s as generous on a 10 s pass either; it is adequate.

### 7. "The discrimination removed only the `setpgid()` hunk"

Correct, and it was the weaker of the two experiments. I could not patch the worktree. The standalone complementary run is in §6: `setpgid` without the group kill is a 30.124 s fail. Removing only the `TimeOut()` `kill(-pid)` hunk would make the author's test fail for the same reason. Both hunks are required.

### 8. "The 'before' test evidence is a prior session's log"

I did not rebuild or rerun `0ab083c4d`. I will not confirm that the five #6299 tests passed on that commit in this session. I did run them on the merge, and they passed. I did not use a prior session's log as evidence of a before/after difference.

### 9. "`timeout_does_not_leak_to_next_promise.cf` still passes"

Confirmed by reading the test. Promise 2 has its own `exec_timeout => "10"`, so `RepairExec()` calls `SetTimeOut()`, which zeroes both flags. A `ClearTimeOut()` that wiped `TIMEOUT_FIRED` would still leave promise 1 classified (it samples first) and promise 2 starting from a clean `SetTimeOut()`. The test cannot distinguish the two `ClearTimeOut()` implementations. The author's framing here is accurate.

## Pre-existing defects the author deferred

I do not have the author's list of five. I will not invent it. These are the ones I found that touch this merge, and whether deferring them is coherent.

**The three `RepairExec()` early returns.** Deferring them is coherent as a merge-resolution choice — they predate both sides — and slightly incoherent as a *B-2* choice. B-2 introduced `TimeOutIsArmed()` specifically so only a child that might have to be group-killed leads a group. These three returns leave `ARMED` set, so the next `cf_popen` child `setpgid`s even when its promise has no timeout. That is the panel-refused behaviour, now reachable from an error path in the file that auto-merged. The fix is `ClearTimeOut()` on those three returns (and probably `umask` restore, also skipped). I would have done it in this series. I would not call the union invalid without it.

**`nfs.c` remount / `unmount_mount`.** Worse than the early returns: `SetTimeOut()` on the success path, no `ClearTimeOut()` at all. Pre-existing missing `alarm(0)`. After B-2 it also leaks `ARMED` into every later `cf_popen`. This is not entangled with `exec_timeout` classification and is outside the files that conflicted. Deferring it is coherent if it is named. Leaving it unnamed in an upstream write-up is not.

**The other `nfs.c` / `history.c` error-path leaks.** Same family, same judgement: pre-existing, now more expensive, not a reason to reject the union.

**`TimeOut()` is not async-signal-safe.** Pre-existing (Log, GracefulTerminate, nanosleep). B-2 adds `getpgid`. See uncertainty 4. Do not "fix" this in the merge by rewriting the handler.

**`ALARM_PID` is not `volatile sig_atomic_t`.** Pre-existing. Same family as `TIMEOUT_ARMED`. Not this merge's job, except that the merge is already touching the flag block.

**Parent does not `setpgid` the child.** Residual race, §4. Do not reopen unconditional `setpgid` to close it.

None of these make the union of #6299 and B-2 internally contradictory. The Windows `getpgid` is the one that does.

## Trap control

1. **Never read a return code through a pipe.** Every compile and every agent/probe run wrote `RC=$?` (or `CC_RC=$?`) to its own file under `/tmp/b2merge-review/` immediately after the command. Distinct stems: `probe_getpgid.cc.rc`, `probe_getpgid.run.rc`, `probe_descendants.cc.rc`, `probe_descendants.run.rc`, `probe_sizes.cc.rc`, `probe_ladder.cc.rc`, `acc-<test>.rc`, `agent-version.rc`, etc. I did not parse a compiler's status out of a pipeline.

2. **`--bindir` is wrong for an in-tree build.** I did not use `--bindir`. I did not use `testall`. Each test was `cf-agent -Klf <test> -D AUTO,DEBUG` with `CFENGINE_TEST_OVERRIDE_WORKDIR` pointed at a per-test directory whose `bin/` held individual symlinks. The ~12 s test (`timeout_after_output_closed.cf`) took 10.632 s and reported the "NOT terminated" string. The suite did not collapse in ~2 s.

3. **`cf-promises` libtool wrapper / `CFENGINE_TEST_OVERRIDE_WORKDIR`.** I used the real Mach-O binaries (`file` said so) with `DYLD_LIBRARY_PATH=/Users/djbclark/src/core-b2merge/libpromises/.libs`. The in-tree `.libs/cf-agent` is linked against a non-existent `/Users/djbclark/opt/cfengine-b2m/lib/libpromises.3.dylib`; without `DYLD_LIBRARY_PATH` it `Abort trap: 6` in 0.037 s (`failsafe-noddyld-real.rc` is `RC=134`). I did **not** reproduce the brief's "wrapper cf-promises → failsafe in 0.26 s" on this host: invoking the libtool wrapper as `workdir/bin/cf-promises` ran `within_timeout_normal_outcomes.cf` to Pass in 2.8–4.4 s, no failsafe string. I still did not use wrappers for the six-test run. `CFENGINE_TEST_OVERRIDE_WORKDIR` was set on every agent invocation. Agent self-report: `CFEngine Core 3.29.0a.ade76f616` (the logging commit; the test-only commit does not change the binary). `timeout.o` is newer than `timeout.c`; `libpromises.3.dylib` and `cf-agent` are 16:53; `nm` shows `ClearTimeOut`, `TimeOutIsArmed`, `TIMEOUT_ARMED`, undefined `getpgid`.

4. **Wall-clock ladder vs descendant hang.** I did not time the ladder with `sh -c "trap '' INT TERM; sleep 30"`. The single-process ladder (ignore INT/TERM, no grandchild) took 2.122 s. The descendant probe uses `sh -c "sleep 30; exit 0"` on purpose, because that *is* B-2's bug. Those 30.0 s / 30.1 s / 7.2 s numbers are pipe-hold times, not ladder times.

5. **Platform.** Host is macOS 26.6.1 (25G76), Darwin 25.6.0, arm64. This build links `process_unix_stub.c` (`process_unix_stub.o` 16:49, no `process_linux.o`). Claims measured here: `getpgid`/`kill(0)` on zombies; descendant pipe-hold with and without each B-2 half; single-process ladder; the six acceptance tests; `sizeof(bool)` / `sizeof(sig_atomic_t)`; stub linkage; `pipes_unix.c` sha256. Claims reasoned about Linux, not run there: `getpgid` of a zombie succeeding; `GetProcessState()` returning `ZOMBIE` and cutting `GracefulTerminate` short; PID/pgid recycling windows under a real `/proc` implementation. Windows claims are from the source (`Makefile.am`, `platform.h`, `cf-execd-runner.c`); no MinGW compile was run.

I did not run `autogen` or `make`. I did not rebuild. I did not patch the worktree to repeat the author's in-tree discrimination. I did not rebuild `0ab083c4d`. Those absences are why some before/after sentences above are marked reasoned rather than measured.

## What I would send back

Before this is offered upstream:

1. `#ifndef __MINGW32__` around `getpgid` / `kill(-pid)` in `TimeOut()`, matching `cf-execd-runner.c`. Do not analogise this to `GracefulTerminate()`.
2. `TIMEOUT_ARMED` → `volatile sig_atomic_t`. One line. The merge created the inconsistency.

Optional in the same series, not merge-blockers:

3. `ClearTimeOut()` on `RepairExec()`'s three post-`SetTimeOut` early returns. B-2 made those leaks do something the last panel refused.
4. Name the `nfs.c` remount success-path leak in the write-up if it is not being fixed.
5. A unit test of `ClearTimeOut()`'s flag contract, if anyone is going to claim the six tests pin it. They do not.

I would not revert the union, the `ClearTimeOut()` lifetime, the `TimeOutIsArmed()` gate, the `getpgid`-before-kill order, or the descendant test.
