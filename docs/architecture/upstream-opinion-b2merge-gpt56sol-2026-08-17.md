# Independent review: B-2 merged with CFEngine Core #6299

Reviewer: `gpt56sol`  
Reviewed head: `3d8e90d68`  
Base: `0ab083c4d`

## Verdict

**Request changes; do not offer this branch upstream yet.**

The merge resolution preserves #6299's successful-path ordering, and the
negative process-group kill is not vulnerable to ordinary PGID reuse while the
direct child remains unreaped. However, the branch has four upstream-facing
problems:

1. Unix-only `getpgid()`/negative-`kill()` code is compiled unconditionally,
   with no MinGW compatibility implementation.
2. `TIMEOUT_ARMED` is a plain `bool` modified by a signal handler. That is not
   valid ISO C signal-handler communication.
3. `SIGALRM` can fire before the parent publishes the forked PID. The handler
   then cancels the alarm without killing anything, after which the command is
   still launched and can run without a bound.
4. Existing post-arm early returns now leak state which directly controls the
   new `setpgid()` behavior. This is no longer safely dismissible as unrelated
   pre-existing cleanup debt.

The added child-side `Log()` and handler-side `getpgid()` also deliberately add
operations which POSIX does not guarantee safe in their respective contexts.
That is the wrong direction for signal/fork code.

## Findings

### 1. Blocking: the alarm can fire before `ALARM_PID` is published

`RepairExec()` calls `SetTimeOut()` before entering the `cf_popen()` stack.
`SetTimeOut()` sets `ALARM_PID = -1` and arms the alarm. The eventual fork does
not assign the child's PID to `ALARM_PID` in the parent until
`GenericCreatePipeAndFork()` returns from `fork()` and reaches
`pipes_unix.c:272`.

There are therefore two real windows:

- The alarm can fire during argument splitting, pipe setup, or `fork()`.
- It can fire in the parent after `fork()` returns but before line 272.

In either window `TimeOut()` observes `ALARM_PID == -1`, records a timeout,
sets `TIMEOUT_ARMED` false, cancels the alarm, and returns. Execution then
continues: the command is launched, the parent publishes its PID, but there is
no alarm left to terminate it. Eventually the promise may be *reported* as
timed out, but `exec_timeout` did not bound its execution.

The child gate is consequently not race-free between `SetTimeOut()` and the
fork. A robust design should block `SIGALRM` across arming, fork, process-group
establishment, and parent-side PID publication, then unblock it. POSIX's
`setpgid()` rationale recommends that both parent and child attempt `setpgid()`
to close process-group establishment races. That also gives the parent a safe
place to report failure.

### 2. Blocking: the MinGW source is not portable

`libpromises/Makefile.am:163` compiles `timeout.c` unconditionally, while
`process_unix.c` and `pipes_unix.c` are under `if !NT`. The new handler code
nevertheless calls `getpgid()` and `kill(-pid, SIGKILL)` without an NT guard.
The tree has no `getpgid()` declaration or implementation for MinGW;
`platform.h` only supplies dummy signal numbers.

Master's already-questionable reference to Unix-only `GracefulTerminate()` is
not a defense for adding another unavailable symbol. It may depend on a build
configuration or expose an older defect, but it does not make this addition
portable. Guard the process-group portion for Unix (or provide a genuine NT
implementation) and run an actual MinGW compile before submission.

### 3. High: `TIMEOUT_ARMED` has undefined signal-handler behavior

`TIMEOUT_ARMED` remains a plain `bool` at `timeout.c:43`; `TimeOut()` writes it
at line 86. ISO C only permits this style of communication through
`volatile sig_atomic_t` (or a suitable lock-free atomic). The adjacent
`TIMEOUT_FIRED` and `TIMEOUT_SIGNALLED` correctly use
`volatile sig_atomic_t`.

This matters even if current compilers happen to emit a byte store. Signal
safety is a language guarantee, not a prediction about today's assembly.
Change it to `static volatile sig_atomic_t TIMEOUT_ARMED`, assign `0`/`1`, and
have `TimeOutIsArmed()` return `TIMEOUT_ARMED != 0`.

That change does not harm the forked child. The child inherits the value at
fork, does not inherit the parent's alarm timer, reads it once, and converts it
to `bool`.

The review should also acknowledge that `ALARM_PID` is a plain `pid_t` shared
with the handler. That is pre-existing, but it is the more consequential
signal-shared value and should be made safe or protected as part of a proper
signal-mask redesign. `TimeOut()` should at least take one local snapshot
instead of rereading the global for the check, log, lookup, direct kill, and
negative kill.

### 4. High: leaked armed state is directly entangled with B-2

After `SetTimeOut()`, `RepairExec()` has three returns which bypass
`ClearTimeOut()`:

- unsupported PowerShell on Unix (`verify_exec.c:329-330`);
- `cf_popen()` failure (`verify_exec.c:371-375`);
- non-EOF read failure (`verify_exec.c:386-394`).

The first two leave the alarm and `ALARM_PID` state armed. The third calls
`cf_pclose()` but still leaves the alarm/armed flag uncleared. A later unrelated
`cf_popen()` can consequently create a new process group merely because
`TimeOutIsArmed()` is stale. A still-pending old alarm can also act on the
later child through the global `ALARM_PID`.

This was already bad timeout cleanup, but B-2 makes the stale flag an input to
generic pipe creation. Deferring these paths while claiming that
`ClearTimeOut()` prevents leakage is incoherent. Use one cleanup exit after
arming and add failure-path coverage.

The problem is broader than the stated three returns. `LoadMountInfo()`,
`MountAll()`, and `MonMeasurementPromise()` also have post-`SetTimeOut()` error
returns which skip `ClearTimeOut()`. Because this branch exposes armed state to
all `cf_popen()` children, all callers need an audit, or the process-group
request must be passed explicitly instead of inferred from global state.

### 5. High: the new failure logging violates the fork-child safety contract

`pipes_unix.c:265-267` calls `Log()` and `GetErrorStr()` in the child between
`fork()` and `exec()`. The file's own banner correctly says only
async-signal-safe functions are allowed there. In a multithreaded parent,
logging or allocator locks can have been held by a thread which no longer
exists in the child, producing a permanent deadlock.

Calling the branch "unreachable" does not help: failure handling is precisely
what executes when platform assumptions fail. Existing unsafe `Log()` calls on
dup/exec errors are debt, not a precedent for adding another one.

Have the parent also call `setpgid(child, child)` and log its result in normal
process context. If child-to-parent reporting remains necessary, use an
async-signal-safe `write()` over a dedicated status pipe and log in the parent.

### 6. High: `getpgid()` is not POSIX async-signal-safe

POSIX Issue 8 lists `setpgid()` and `kill()` as async-signal-safe, but not
`getpgid()`. Calling it from `TimeOut()` is therefore formally unspecified
across the supported Unix platforms. “It is a thin syscall here” is not an
upstream portability contract.

Record successful process-group establishment before unblocking `SIGALRM`, in
signal-safe state, so the handler only needs a recorded PID/group-ready bit and
`kill()`. The handler also needs to save and restore `errno`. Existing
`Log()`/`GracefulTerminate()` calls already make this handler far from strictly
async-signal-safe, but adding another non-guaranteed interface should not be
accepted merely because the old code is already unsafe.

The literal logging requirement is met for `setpgid()` and `getpgid()`
failures, but `kill(-ALARM_PID, SIGKILL)` still ignores its return value. Thus
the operation which actually provides B-2's guarantee can fail silently while
the promise says the process “was terminated.” Moving group setup/termination
bookkeeping out of the handler is the clean way to make truthful reporting
possible.

### 7. The negative-kill reuse attack does not succeed under the normal ownership model

I did not find an ordinary PID/PGID-reuse path in the intended single-owner
flow:

- `cf_pclose()` is the code which reaps the direct child, and it has not run
  while the read loop is blocked.
- If the direct child exits first, it remains an unreaped zombie under the
  installed `SIGCHLD` disposition.
- A process ID cannot be reused during that process's lifetime. POSIX also
  prevents reuse while a process group with that numeric ID still exists.
- `GracefulTerminate()` does not reap the child, so the leader/PID remains
  reserved through the subsequent negative `kill()`.

Accordingly, the earlier zombie argument extends to the group: the group cannot
be replaced with an unrelated group while its ID remains reserved.

The comment at `timeout.c:93-95` is nevertheless misleading. Killing the child
does not normally make `getpgid()` immediately fail; an unreaped zombie remains
queryable on relevant systems. Reading before the ladder is useful to establish
identity, but not for the reason stated.

Safety still depends on exclusive ownership. A competing reaper, an inherited
`SA_NOCLDWAIT` race, or another thread mutating global `ALARM_PID` would break
the proof. The code should snapshot the PID and document/enforce the
single-owner assumption.

### 8. `ClearTimeOut()` preserves the successful-path result, but the contract is unpinned

On the ordinary waited path, `RepairExec()` does the right thing:

1. `cf_pclose()` returns;
2. `TimeOutHasFired()` is sampled;
3. `TimeOutSignalledProcess()` is used while reporting;
4. `ClearTimeOut()` is called later.

Thus a hypothetical flag-clearing `ClearTimeOut()` would not break today's six
acceptance tests. It would make the public lifetime contract false and create a
future ordering trap.

The answer to “on every path?” is still **no**. The Unix early returns neither
sample nor clear. The Windows background path calls `cf_pclose_nowait()`,
does not sample, and later clears. Those paths do not invalidate the current
normal-path outcome fix, but they show why prose alone is inadequate.

Add a focused unit test which fires a timeout, disarms it, and proves both
result accessors retain their values until the next `SetTimeOut()`. Better
still, make disarming return a timeout-result snapshot, so the API itself owns
the ordering and can reset all state deterministically.

## Test assessment

The new acceptance test has the right basic discriminator. Without a new
process group, `getpgid(child) != child`, so the retained group-kill hunk is
inert; the direct shell can die while its `sleep` keeps the pipe open. Removing
only the `setpgid()` hunk is therefore a meaningful test of the combined
behavior, not a meaningless mutant. Removing only the group-kill hunk should
still be run to prove the other half independently.

The test is not completely portable across Unix shells because it relies on
the shell not forwarding the direct SIGINT/SIGTERM to its foreground child.
Make the payload explicitly ignore INT and TERM before spawning the sleeper;
then only the final process-group SIGKILL can release the inherited pipe.

The 20-second threshold is also tight relative to the author's reported
10-12-second pass and 31-second failure. Loaded CI can consume that margin.
Use a substantially longer sleeper and a threshold with a larger gap, or a
non-timing witness if the acceptance framework can provide one.

Statically, the unmerged source has no mechanism to kill the sleeper's group,
so the test should fail there. I did not independently execute that baseline,
the branch, or either mutant. The author's setpgid-removal run is stronger than
the cited old baseline log for the narrow behavior, but the complementary
mutation and a fresh baseline run remain desirable.

The five #6299 tests cover outcome classification, not the new signal-safety,
publication race, cleanup failures, or `ClearTimeOut()` lifetime contract.
`timeout_does_not_leak_to_next_promise.cf` resets state through the second
promise's `SetTimeOut()` and does not exercise any post-arm failure return.

## Author's uncertainties

1. **“The hazard is latent, not live.”** Correct only for the current
   successful waited path. It is not overcautious to preserve the result across
   disarm, but an untested public lifetime contract is insufficient. Add a unit
   test or redesign disarm to return the result snapshot.

2. **“Windows/MinGW build unverified — the author's own biggest worry.”**
   This is a stop-ship item. Static source inspection shows an unconditional
   Unix-only symbol reference and no compatibility implementation. Guard it
   and cross-build.

3. **“`TIMEOUT_ARMED` is a plain `bool`.”** Prior standalone review does not
   transfer. The merged code makes the inconsistency obvious, and the type is
   invalid for handler communication. Fix it in this series.
   `TimeOutIsArmed()`'s child use is unaffected by conversion to
   `volatile sig_atomic_t`.

4. **“`getpgid()` in a signal handler.”** Formally unsafe and unnecessary if
   group creation is recorded before unblocking the alarm. Do not waive it on
   the assumption that every supported libc will forever implement it as a
   bare syscall.

5. **“The child-side failure `Log()`.”** Reject this addition. An unlikely
   branch can still deadlock, and nearby violations do not make it safe. Report
   from the parent.

6. **“Timing margins of the new test.”** The roughly nine-second margins are
   not comfortable for heterogeneous loaded CI. Increase the separation and
   make shell signal behavior explicit.

7. **“The discrimination removed only the `setpgid()` hunk.”** The experiment
   is still meaningful because the group-kill guard becomes false, making the
   retained kill inert. Run the complementary mutation as well.

8. **“The ‘before’ test evidence is a prior session's log.”** I do not count it
   as an independently measured before result. Static control flow predicts
   failure; a fresh baseline run should establish it empirically.

9. **“`timeout_does_not_leak_to_next_promise.cf` still passes.”** It does not
   test `ClearTimeOut()` and does not reach an early-return leak. It cannot
   support either claim. Add direct contract and failure-path tests.

## Pre-existing defects and scope

The brief says there are five pre-existing defects but names only the three
`RepairExec()` early returns, so the exact five cannot be independently judged
from the brief as written. Source inspection found more than five post-arm
cleanup exits across `verify_exec.c`, `nfs.c`, and `history.c`.

The three `RepairExec()` leaks should not be deferred: B-2 newly consumes the
leaked state in generic child setup. The same reasoning calls for auditing the
other `SetTimeOut()` callers touched by the `ClearTimeOut()` conversion.

Two other existing limitations can reasonably remain separate if documented:

- `cf_pclose()` clears `ALARM_PID` before waiting, so a command which closes all
  output before its timeout can still run to completion; #6299 deliberately
  reports that it was not terminated.
- NFS paths disarm before `cf_pclose()` on normal completion, so their final
  wait is not bounded after output closes.

Those limitations predate B-2 and do not make descendant group-killing
worthless. They do mean the contribution must not claim that `exec_timeout`
universally bounds wall clock.

## Trap control

1. **Never read a return code through a pipe.** I did not compile, build, or run
   a test command, so I produced no return-code artifact and made no measured
   return-code claim. No piped return code was used.

2. **`--bindir` is wrong for an in-tree build.** I did not invoke the acceptance
   harness. I therefore produced no harness log and do not claim that the six
   tests passed independently.

3. **The build-tree `cf-promises` wrapper and
   `CFENGINE_TEST_OVERRIDE_WORKDIR`.** I did not launch `cf-agent` or
   `cf-promises`; neither path selection nor the override variable was used.
   There is no runtime artifact from this review.

4. **A ladder measurement needs a single-process command.** I performed no
   wall-clock probe. In particular, I did not use the descendant-bearing test
   command to infer the direct-process ladder duration. All timing numbers
   above are explicitly the author's reported numbers, not my measurements.

5. **Platform.** I performed no platform runtime measurement. The macOS
   discussion is source reasoning from `process_unix_stub.c`, where
   `GetProcessState()` maps every extant PID—including a zombie—to
   `PROCESS_STATE_RUNNING`. Linux zombie behavior is reasoned from the
   platform-specific design and POSIX process/PID lifetime rules, not measured
   on this macOS host. I created no rc file, log, binary, or sha256 because the
   instruction allowed writing only this review file.

## Minimum changes before upstream submission

1. Guard or implement the Unix process-group code for MinGW and cross-build it.
2. Convert `TIMEOUT_ARMED` to signal-safe storage; address `ALARM_PID` in the
   same signal-state audit.
3. Close the pre-publication alarm race with signal masking plus parent/child
   process-group establishment.
4. Remove post-fork `Log()` and handler-side `getpgid()` from the new paths.
5. Route every post-arm exit through cleanup.
6. Add tests for the disarm-result contract and failure-path armed-state leaks;
   harden and complement the descendant acceptance test.
