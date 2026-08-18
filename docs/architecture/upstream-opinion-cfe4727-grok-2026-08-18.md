# Upstream second opinion — CFE-4727, exec_timeout termination half

**Reviewer:** grok
**Date:** 2026-08-18
**Subject:** `djbclark/core` worktree `/Users/djbclark/src/core-alarmpid`, branch `fix/exec-timeout-alarm-pid`, commit `254cbe593` (parent `dbf759d16`)
**Ticket:** CFE-4727

This review assumes the fix is wrong and tries to show it. It is not a paraphrase of the author's notes.

---

## Verdict

**Offer upstream.** The defect is real, the wait-then-clear change is the right shape, and I independently reproduced both sides of the discrimination without touching the worktree. A command that closes its output and keeps running is unreachable under the old `ALARM_PID = -1` at the top of `cf_pclose()`, and reachable once that store moves to after `cf_pwait()`.

I would not describe this commit as closing *the* `exec_timeout` termination guarantee. It closes the deterministic gap that CFE-4726 had already documented as accepted. It leaves the pre-fork publish race, and it leaves a post-reap classification lie that the new `TIMEOUT_SIGNALLED` comment describes as a "no process" case when it is not.

The author's most-worried residual race is framed incorrectly: the window is not only a pid-recycling kill, and on the hang-after-EOF path the alarm has already been consumed by the time `waitpid()` returns. The author's `sigprocmask()` reasoning is also framed incorrectly — on this host a worker's `sigprocmask(SIG_BLOCK, SIGALRM)` writes the **process** mask, including the main thread. That is not a live `cf-agent` / `RepairExec()` bug. It is a real defect of a helper that now runs on every `cf_pclose()`, including `cf-serverd` / `cf-execd` worker threads.

Switch `ClearAlarmedPid()` to `pthread_sigmask()` in this series. Do not fold the pre-fork race, CFE-4728, or CFE-4718 into this commit.

---

## What I actually did

Read, not just the diff:

- `libpromises/pipes_unix.c`: `GenericCreatePipeAndFork()`, `ChildrenFDSet()`, every `cf_popen*` fdopen-failure `cf_pwait()`, `cf_pwait()`, `ClearAlarmedPid()`, `cf_pclose()`, `cf_pclose_full_duplex()`, `cf_pclose_nowait()`, `PipeToPid()`
- Parent (`dbf759d16`) `cf_pclose()` / `cf_pclose_full_duplex()` for the pre-clear
- `libpromises/timeout.c` / `timeout.h`: `SetTimeOut()`, `ClearTimeOut()`, `TimeOut()`, all three flags
- `cf-agent/verify_exec.c` `RepairExec()` in full
- `cf-agent/nfs.c` (all four `SetTimeOut()` sites) and `cf-monitord/history.c`
- `libpromises/unix.c` `ShellCommandReturnsZero()` (B-16)
- `libpromises/cf3globals.c` / `cf3.extern.h` (`ALARM_PID` storage)
- `libpromises/process_unix.c` `GracefulTerminate()` / `ProcessWaitUntilExited()`, `process_unix_stub.c`, `libpromises/Makefile.am` (Darwin links the stub)
- `cf-serverd/server.c` `HandleConnection()` + `server_common.c` `DoExec2()`, `cf-execd/cf-execd.c` `LocalExecThread()` + `cf-execd-runner.c` / `cf-execd-runagent.c`
- `libpromises/evalfunction.c` `ExecJSON_Pipe()`, `libpromises/pipes.c` `PipeWriteData()` / `PipeReadWriteData()`, `libpromises/mod_custom.c`
- `libntech/libutils/signal_lib.h`, `libcfnet/client_code.c` (house `pthread_sigmask()`)
- `tests/unit/timeout_test.c`, `tests/acceptance/08_commands/04_exec_timeout/timeout_after_output_closed.cf` and its parent

Confirmed `SetTimeOut(` myself (`*.c`): `verify_exec.c`, `nfs.c`, `cf-monitord/history.c`, `timeout.c`, `timeout_test.c`. No other callers.

Measured on this host (see Trap control): unit test 7/7; the rewritten acceptance test; standalone old-vs-new model; residual-window raise-after-reap; `signal()` / `waitpid()` SA_RESTART; worker `sigprocmask()` vs `pthread_sigmask()` vs the main thread's mask; post-`waitpid` window width; `sizeof(pid_t)` / `sig_atomic_t`.

Not executed: a Linux build, a MinGW build, `make check` under load, a worktree revert of `pipes_unix.c`, the other five `04_exec_timeout/` tests, or any path that actually delivers `SIGALRM` inside `cf-serverd`.

Did not read any other `upstream-opinion-*` file.

---

## Trap control

Host, checked this session, not copied from the brief:

```
ProductName: macOS
ProductVersion: 26.6.1
BuildVersion: 25G76
Darwin mac 25.6.0 ... RELEASE_ARM64_T8103 arm64
Apple clang version 21.0.0 (clang-2100.1.1.101)
Target: arm64-apple-darwin25.6.0
```

Every compile and every probe/agent/unit-test run wrote `echo "RC=$?"` to a distinct file under `/tmp/cfe4727-grok-review/` immediately after the command, with no pipe on that command. Observed `RC=0` for: six probe compiles, old-mode run, new-mode run, window / SA_RESTART / sigmask / sizes / window-ns runs, `timeout_test`, `cf-agent --version`, and the acceptance agent.

1. **Never read a return code through a pipe.** Done. Distinct stems: `cc_old_vs_new.rc`, `run_old.rc`, `run_new.rc`, `timeout_test.rc`, `acc-oc.rc`, `agent-version.rc`, etc.

2. **`--bindir` is wrong for an in-tree build.** I did not pass `--bindir`. I did not run `testall`. The acceptance case was `cf-agent -Klf <test> -D AUTO,DEBUG` with `CFENGINE_TEST_OVERRIDE_WORKDIR` and `TEMP` pointed at `/tmp/cfe4727-grok-review/acc-oc`. Wall clock **19.421 s**, marker elapsed **18.232 s**. This was not a ~2 s harness collapse.

3. **`cf-promises` libtool wrapper / `CFENGINE_TEST_OVERRIDE_WORKDIR`.** Workdir `bin/` held symlinks to the Mach-O binaries (`file` said so for `cf-agent` and `cf-promises`). `DYLD_LIBRARY_PATH` was the in-tree `libpromises/.libs`. Prefix `/Users/djbclark/opt/cfengine-dev-4727/lib/libpromises.3.dylib` is byte-identical to the in-tree dylib (`7f33b51d…`). `CFENGINE_TEST_OVERRIDE_WORKDIR` was set. Grep of the agent log for `failsafe`: **0**. Agent self-report: `CFEngine Core 3.29.0a.dbf759d16` — that is the configure-time parent SHA, not proof the binary lacks `254cbe593`. The behaviour is the proof: "was terminated", no `oc_completed`, 18 s not 30 s.

   Unit test was driven through the libtool wrapper (`tests/unit/timeout_test`), which is the correct driver for a unit test (`make check` uses it). `tests/unit/.libs/timeout_test` is the Mach-O.

4. **Wall-clock probe is a single process.** Standalone discrimination used `execl("/bin/sleep", "sleep", "30", NULL)` after closing fd 1/2 — no shell, no grandchild. The in-tree unit test already `exec sleep 30`. The acceptance payload is `/bin/sh -c "exec 1>&- 2>&-; sleep 30; touch …"` — **not** `exec sleep`. That is the commit's own test, not mine. Killing the shell is enough to prevent the completion marker; see §7.

5. **Platform.** This build links `process_unix.c` **and** `process_unix_stub.c` (`Makefile.am` `if !LINUX && !AIX && !HPUX && !SOLARIS && !FREEBSD`). `GetProcessState()` is the stub. Claims tagged **measured** (this macOS host) or **reasoned** (Linux / POSIX). I did not assert Linux numbers I did not run.

6. **Pre-fork flake under load.** I did not run `make check` or add concurrent load. I will not claim a new manifestation of that race.

I did **not** `git checkout HEAD~1 -- libpromises/pipes_unix.c`. The brief forbids modifying existing files. Discrimination of old vs new `ALARM_PID` lifetime was measured with `/tmp/cfe4727-grok-review/probe_old_vs_new` instead.

---

## 1. Does `ClearAlarmedPid()` close the race, or just narrow it?

**It closes the defect this ticket names. It narrows, not closes, the abstract pid-recycling race, and the author's instruction-count story is slightly small.**

Exact sequence on the success path, from the C and from `otool -tV` of this tree's `pipes_unix.o` (`ClearAlarmedPid` is static and was inlined into `cf_pclose`; there is no `_ClearAlarmedPid` symbol):

1. `waitpid(pid, &status, 0)` inside `cf_pwait()` returns the reaped child (or is kernel-restarted after `TimeOut()`; see below).
2. `WIFEXITED` / `WEXITSTATUS` (or the abnormal-exit `Log`).
3. `Log(LOG_LEVEL_DEBUG, "cf_pwait - process … exited …")`.
4. Return to `cf_pclose()`.
5. Inlined `ClearAlarmedPid`: store `0x2000` as a `sigset_t` (SIGALRM), `sigprocmask(SIG_BLOCK=1, …)`, compare `ALARM_PID` to `pid`, maybe store `-1`, `sigprocmask(SIG_SETMASK=3, saved, NULL)`.

Between (1) and the `SIG_BLOCK` taking effect, `ALARM_PID` still names a **reaped** pid. A `SIGALRM` delivered in that window runs `TimeOut()` against that number.

Is that "a handful of instructions"? **Without debug logging, yes, in the microseconds sense.** Measured 200 samples of "successful `waitpid` → `WIF*` → `sigprocmask(SIG_BLOCK)`" with no I/O:

```
samples=200 log=0 min_ns=0 avg_ns=870 max_ns=15000
```

With a `fprintf` standing in for the DEBUG `Log`:

```
samples=50 log=1 min_ns=3000 avg_ns=3800 max_ns=8000
```

Default agent log level will take the first path: `Log(DEBUG)` is a level check and return, still a call, still not a `syslog`. Calling it "a handful of instructions" undersells the `Log` + function epilogue, and oversells nothing important about duration. Moving the block to the first instruction after `waitpid()` succeeds — inside `cf_pwait()`, before `Log` — would make the claim literally true. I would not hold the offer for that.

The author's "only if the alarm fires in that window *and* the OS recycles the pid" is the framing error. Two different things live in the window:

| Alarm in the post-reap window | Recycle? | What `TimeOut()` does |
|---|---|---|
| yes | no | `TIMEOUT_SIGNALLED = 1`, `kill` of a reaped pid → `ESRCH`. Harmless as a kill. **False "was terminated".** |
| yes | yes | `TIMEOUT_SIGNALLED = 1`, `kill` / `kill(-pid)` of whoever inherited the number. The scary case. |

I measured the first row. After `waitpid` of an already-exited child, `raise(SIGALRM)` with `ALARM_PID` still set:

```
after_reap_raise fired=1 signalled=1 kill_rc=-1 kill_err=3 ESRCH=1
```

Same window, `ALARM_PID` pointed at a live decoy (recycle analogue; the decoy did **not** reuse the reaped number — `recycled_same=0`):

```
decoy_in_window fired=1 signalled=1 decoy_signalled=1 decoy_termsig=9
```

`TimeOut()` will signal whatever `ALARM_PID` currently names. It does not check that the pid is still a child, and it sets `TIMEOUT_SIGNALLED` **before** `getpgid` / `GracefulTerminate`. A just-under-the-wire child that `waitpid` has already reaped can be reported as "was terminated" without any recycle.

That classification lie does **not** require microseconds-scale pid wrap. It requires the alarm to be due in the same window the child finished. That is exactly the "finished just under the wire" case the new comment treats as a remaining *no-process* case.

And on the path this ticket actually fixes — alarm fires *during* the wait — the residual window is idle. `TimeOut()` runs, calls `alarm(0)`, kills the child, returns; `waitpid` then reaps (via `EINTR` retry or SA_RESTART; see below). There is no second alarm sitting there waiting to observe the reaped pid.

So: versus the old code's deterministic "clear, then wait forever", this is a real fix. The leftover race is a short, real, mostly-classification window on the just-under-the-wire path, plus a theoretical recycle kill I could not produce with a single fork after reap. Acceptable. Misdescribed.

**`waitpid` is not "interruptible" in the `EINTR` sense on this host.** `SetTimeOut()` uses `signal(SIGALRM, TimeOut)`. Darwin `signal(3)` installs `SA_RESTART` and names `wait(2)` as restarted. Measured:

```
waitpid_rc=child errno=0 eintr=0 hits=1 elapsed=3.076 child_exited=1
```

Handler ran at 1 s; `waitpid` of a 3 s `sleep` did not return `EINTR`. Linux glibc `signal()` is the same family (reasoned, not run). The fix does not depend on `EINTR`. It depends on the handler running *during* the blocked wait and still seeing `ALARM_PID`. That works with SA_RESTART: handler kills, syscall restarts, `waitpid` reaps the corpse. The author's "cf_pwait()'s waitpid() is interruptible by SIGALRM" is true as "the handler runs" and false as "the `EINTR` loop is what makes this work."

---

## 2. `sigprocmask()` vs `pthread_sigmask()`

**Theoretical on POSIX; measured and process-wide on this Darwin; not live for `RepairExec()`; the author's reason for keeping `sigprocmask()` is the wrong reason.**

POSIX: "The use of the `sigprocmask()` function is unspecified in a multi-threaded process." The specified call is `pthread_sigmask()`. This tree already uses it that way (`libntech/libutils/signal_lib.h` `MaskTerminationSignalsInThread()`, `libcfnet/client_code.c`). `HAVE_DECL_PTHREAD_SIGMASK` is 1.

Is `cf_pclose()` reached from worker threads? **Yes, in practice, not as a thought experiment.**

- `cf-serverd`: `pthread_create(..., HandleConnection, ...)` → `DoExec2()` → `cf_popen()` / `cf_pclose()`. `HandleConnection` does **not** call `MaskTerminationSignalsInThread()`.
- `cf-execd`: `LocalExecInThread()` → `LocalExec()` → `cf_popen_sh()` / `cf_pclose()`. `cf-execd-runagent.c` is another `cf_popen` / `cf_pclose` on whatever thread serves that request.

Those daemons never call `SetTimeOut()`. I grepped. So a worker `ClearAlarmedPid()` is protecting a global that `TimeOut()` will not run for, **unless** something else has armed `SIGALRM` (B-15 family, or a future caller).

The author's justification: "nothing else in this file blocks `SIGALRM` in the main thread (the only other `sigprocmask()` runs in the forked child)." That answers "is our `SIG_SETMASK` restore going to unmask something *this file* blocked on the main thread?" It does not answer "what does `sigprocmask` do when a worker calls it?"

On this host I measured the second question.

Worker calls `sigprocmask(SIG_BLOCK, SIGALRM)` and stays alive:

```
before worker: main_alrm_blocked=0
during worker sigprocmask: main_alrm_blocked=1
after join: main_alrm_blocked=1
```

Same experiment with `pthread_sigmask`:

```
before worker: main_alrm_blocked=0
during worker pthread_sigmask: main_alrm_blocked=0
after join: main_alrm_blocked=0
```

Process-directed `SIGALRM` while the worker holds that block, 5/5 runs:

```
sigprocmask:     hits=0,0,0,0,0
pthread_sigmask: hits=1,1,1,1,1
```

On macOS 26.6.1 arm64, `sigprocmask` in a worker writes the **process** mask. `pthread_sigmask` writes the calling thread's mask. Darwin's `sigprocmask(2)` man page does not mention threads (POSIX.1-1988). Linux `sigprocmask(2)` documents the multithreaded case as unspecified and points at `pthread_sigmask` (reasoned; I did not run Linux).

`ClearAlarmedPid()` does restore with `SIG_SETMASK` and the saved mask, so a *single* worker call is a process-wide block of SIGALRM for the duration of one compare-and-store, then a restore. That is short. Two overlapping `ClearAlarmedPid()` calls on Darwin are not: each saves whatever the process mask is at `SIG_BLOCK`, and the later `SIG_SETMASK` can restore a mask that still contains SIGALRM, leaving the process unable to receive the next `exec_timeout`. I did not construct that interleaving. It is the natural consequence of the measurement plus a helper that now runs on every close.

`RepairExec()` is single-threaded. For CFE-4727's own call site, `sigprocmask` is specified and sufficient. For the helper as written, in the file it lives in, it is the wrong API. The fix is one identifier.

---

## 3. The three error paths that now leave `ALARM_PID` set

**The author attributed three `cf_pclose_full_duplex()` paths to `cf_pclose()`. One of the three is not an early return in either version of `cf_pclose()`.**

Parent `cf_pclose()` (`dbf759d16`):

```c
ALARM_PID = -1;                 /* first action after CHILDREN == NULL */
if (fd >= MAX_FD) { fclose; return -1; }
pid = CHILDREN[fd];
if (fclose(pp) == EOF) { Log(...); }   /* does not return */
return cf_pwait(pid);
```

Parent `cf_pclose_full_duplex()`:

```c
ALARM_PID = -1;
pid_t pid = 0;
if (read_fd >= MAX_FD || write_fd >= MAX_FD) { Log; } else { pid = CHILDREN[read_fd]; ... }
if (fclose/close fails) return -1;
if (pid == 0) return -1;
return cf_pwait(pid);
```

### `fd >= MAX_FD` in `cf_pclose()`

Real early return. Child is **not** looked up, `CHILDREN[fd]` is not cleared, `fclose` happens, no `waitpid`. Child is unreaped. `ALARM_PID` still names whatever `GenericCreatePipeAndFork()` published — for a `cf_popen` child, that is this child. Leaving it set is right: a pending alarm can still kill it, and the pid cannot recycle.

Practically almost dead. `ChildrenFDSet()` grows `MAX_FD` (`new_max = fd + 32`) **before** a successful `cf_popen` returns the `FILE*`. A pipe that came from `cf_popen*` should not hit `fd >= MAX_FD` in `cf_pclose` unless someone passes a foreign `FILE*` while `CHILDREN` is non-NULL. Still the right behaviour on that path.

### Failed `fclose()` in `cf_pclose()`

**Not an early return, old or new.** Both versions log and fall through to `cf_pwait()`. The child is reaped. `ClearAlarmedPid` then runs. There is no "leave `ALARM_PID` set because we skipped the wait" change here. The author's claim that this path previously pre-cleared *and returned* is false for `cf_pclose()`.

It **is** an early return in `cf_pclose_full_duplex()` (any of the four `fclose`/`close` failures). There they have already zeroed `CHILDREN[]`. They do not wait. Child is unreaped. New code leaves `ALARM_PID` set. Author's "unreaped, alarm can still usefully terminate it" holds for **full-duplex** fclose failure.

### `pid == 0`

**Does not exist in `cf_pclose()`.** Only `cf_pclose_full_duplex()`. Two ways to get there:

1. `fd >= MAX_FD`: never copied `CHILDREN[read_fd]`, `pid` stays 0. Child still in the table, unreaped. `ALARM_PID` from fork still names it. Leave it. Correct.
2. `CHILDREN[read_fd] == 0` (double-close, never-registered slot). This close does not own a child. Leaving `ALARM_PID` alone is **better** than the old unconditional `ALARM_PID = -1`, which would wipe a registration that belongs to some other live `cf_popen`.

No path I walked leaves a *wrong* pid registered *because of this commit*. The full-duplex `pid == 0` path can leave a *stale* pid that was already stale (B-16, or a previous unreaped error). The old code papered that over by blasting `-1` at function entry. Hygiene, not a new stale store.

`cf_pclose()` of `CHILDREN[fd] == 0` is pre-existing and worse than the author noticed: it `cf_pwait(0)`, and `waitpid(0)` waits for any child in the process group. `ClearAlarmedPid(0)` is then a no-op unless someone put `0` in `ALARM_PID` (`GenericCreatePipeAndFork` never does). Not introduced here.

`CHILDREN == NULL` early return: never cleared `ALARM_PID` in either version (parent cleared *after* this check). Unchanged.

---

## 4. `cf_pclose_full_duplex()` symmetry

**The grep claim is true. The change is not inert. Shipping it is net-positive if the B-15 widening is named.**

Confirmed this session, not taken from the author:

`SetTimeOut(` in `*.c`: `verify_exec.c`, `nfs.c`, `cf-monitord/history.c`, plus the definition and the unit test. All three production callers use half-duplex `cf_popen*` / `cf_pclose()`.

Full-duplex open/close: `evalfunction.c` `ExecJSON_Pipe()` (`mapdata` `json_pipe`), `pipes.c` `PipeWriteData` / `PipeReadWriteData` (package modules), `mod_custom.c`. None arm `SetTimeOut()`. `PipeReadWriteData`'s `pipe_timeout_secs` is a userspace poll, not `SIGALRM`.

Not inert:

- `GenericCreatePipeAndFork()` sets `ALARM_PID` for **every** popen, including full-duplex. That is pre-existing. A leaked armed alarm (B-15 remount, any `RepairExec` early-return leak) could already kill a full-duplex child *during its run*.
- Old `cf_pclose_full_duplex()` set `ALARM_PID = -1` **before** `waitpid`. A leaked alarm that fired *during the wait* found nothing.
- New code leaves `ALARM_PID` set through the wait. A leaked alarm that fires there now terminates that child. That is the "marginally widens an already-existing leaked-alarm blast radius during the reap window."
- On the `pid == 0` / `MAX_FD` / fclose-failure returns, it no longer wipes a foreign `ALARM_PID`. That shrinks a different blast radius (don't disarm someone else's child).

I found no full-duplex caller that sets `ALARM_PID` by any means other than `GenericCreatePipeAndFork()`. `RepairExec()` does not nest a full-duplex popen inside an armed half-duplex wait.

Shipping the same helper on both closers is the right API. Splitting the commit to leave full-duplex pre-clearing would keep a known-wrong pattern next to the fixed one for no production `exec_timeout` reason. Do it, and write the B-15 sentence in the PR so nobody is surprised that a leaked remount alarm can now kill a package-module wait.

---

## 5. The rewritten `TIMEOUT_SIGNALLED` comment

**Incomplete, and one of its two "no process" windows is described at the wrong instant.**

The comment now says the alarm can fire with no process registered (a) before `cf_popen()` has forked, or (b) after `cf_pclose()` has reaped a child that finished just under the wire.

(a) is real. `SetTimeOut()` stores `ALARM_PID = -1` and *then* arms. `GenericCreatePipeAndFork()` publishes the pid after `pipe()` / `fork()` / a `sigaction(SIGCHLD)` that runs in both parent and child. The production order in `RepairExec()` is `SetTimeOut` → umask → maybe build argv → `cf_popen*`. That window is the pre-fork race (attack 6).

(b) is true only **after** `ClearAlarmedPid()`. Between successful `waitpid` and `SIG_BLOCK`, `ALARM_PID` still names the reaped child and `TimeOut()` will claim it signalled a process (§1). The comment describes the intent of the new design, not the residual window the commit message itself admits.

Missed windows where `TimeOut()` finds `ALARM_PID == -1` (or never runs):

1. **Parent after `fork()`, before `ALARM_PID = pid`.** A few instructions plus `sigaction(SIGCHLD)`. Same family as (a), later and smaller. Not listed.
2. **Any `SetTimeOut()` that never reaches a `cf_popen` that publishes a pid** — Powershell-on-Unix in `RepairExec()`, `pfp == NULL` after a failed open that never forked. Armed, `ALARM_PID == -1`. Same symptom as (a).
3. **Callers that `ClearTimeOut()` *before* `cf_pclose()`** — `LoadMountInfo()` (`nfs.c:581`) and `MountAll()` (`nfs.c:1177`). The alarm is cancelled before the wait. Hang-after-EOF on those paths is still unbounded. This commit does not help them. Not a `TIMEOUT_SIGNALLED` window (the handler never runs); it is a third *shape* of "timeout did not terminate" the comment's "two windows" list pretends is complete.

`TimeOut()` itself never clears `ALARM_PID`. After a successful kill during the wait, the flag stays set until `ClearAlarmedPid`. Correct, and not a third "no process" window.

---

## 6. The pre-fork race, deliberately left unfixed

**Right scope call. The subject line is not a lie. The 2 s acceptance test can still lose this race.**

`SetTimeOut()` before `cf_popen()` is the production order. A 2 s `exec_timeout` on a loaded host can fire before `ALARM_PID` is published. The child is then born with `TIMEOUT_ARMED` already cleared (the handler clears it), so it does not `setpgid`, and nothing will kill it. The author says they saw this as a unit-test flake under `make check`. I did not reproduce it (trap 6). I will treat the existence of the window as **read from the code** and the flake as **the author's measurement, not mine**.

This commit's subject is "never terminating a command that closed its output." That is the clear-before-wait gap. The pre-fork race is "never terminating a command that was not registered yet." Different instant, different fix (arm after publish, or publish-and-arm under a blocked `SIGALRM` around `fork`). Folding it here would be a second behaviour change and a different ticket. The body already says so.

It is close subject-matter. Shipping CFE-4727 without it is not incoherent, and is not silently claiming the guarantee is now total — provided the PR does not. The unit test *avoids* the production order on purpose. The acceptance test *uses* the production order with a 2 s timeout. That test can fail a correct fix the same way the first unit-test draft did. That is a test-quality leftover, not a reason to cram a publish-race fix into this SHA.

---

## 7. The tests

**Both discriminate the clear-before-wait gap. The acceptance test does not prove process-group kill, and can flake on the pre-fork race.**

### Unit test `test_pclose_leaves_the_alarm_its_process`

Core asserts: `TimeOutHasFired()`, `TimeOutSignalledProcess()`, `elapsed < 25`, `ret != 0`, `ALARM_PID == -1`.

I ran the committed binary via the libtool wrapper. 7/7, `RC=0`, wall **37.76 s**. The new case is in that run (`test_pclose_leaves_the_alarm_its_process: Test completed successfully.`).

I did not revert `pipes_unix.c`. Standalone model of the same lifetime, single-process `exec sleep 30`, 2 s alarm, raw `SIGKILL` (no Darwin ladder):

```
mode=NEW fired=1 signalled=1 elapsed=2.145 how=signalled wtermsig=9
mode=OLD fired=1 signalled=0 elapsed=30.129 how=exited   wexit=0
```

Unfixed, `TimeOutSignalledProcess()` is false, elapsed is ~30, `waitpid` reaps exit 0. All three of the test's load-bearing asserts fail. The author's "fails at `timeout_test.c:129`" is the first of those; I did not re-hit that line number and do not need to.

Could it pass unfixed? Only if the 2 s alarm landed in the milliseconds between `ALARM_PID = child` and the old `ALARM_PID = -1` at the top of `cf_pclose` (the `fgets` loop hits EOF immediately). That is the same class of needle as the residual window, against a 2 s timer. Not a realistic false pass.

The test forks **before** `SetTimeOut()`, then writes `ALARM_PID` by hand. `TimeOutIsArmed()` was false at `fork`, so the child did **not** `setpgid`. `TimeOut()`'s `pgid == ALARM_PID` guard therefore skips the group kill — necessary, or it might `kill(-test_pgid)`. This pins `ALARM_PID` lifetime through `cf_pclose`, not the production publish order, and not B-2. That is what the comment says it is for.

### Acceptance `timeout_after_output_closed.cf`

Parent test asserted only `output_closed_repair_timeout` — CFE-4726 detection, and it *expected* the child to run its sleep out. The rewrite requires `repair_timeout,bounded,terminated` and forbids kept/repaired.

I ran it against the committed agent. **Pass**, agent `RC=0`, wall **19.421 s**, marker elapsed **18.232 s**, no `oc_completed`, log line:

```
error: Command '/bin/sh' exceeded exec_timeout of 2 seconds and was terminated
```

`TimeOutSignalledProcess()` was true on the real `RepairExec()` path. Bound 25 s vs 18 s of markers is comfortable on this host *today*. It is not generous if CFE-4728/4718 overshoot grows; `islessthan("25","25")` is false, and `filestat` mtime is an integer second.

Could it pass unfixed? The termination ladder never runs if `TimeOut()` sees `-1`. The child is `/bin/sh -c "…; sleep 30; touch oc_completed; exit 0"`. Unfixed, `sh` waits out the sleep, touches the marker, exits 0; `terminated` fails, `bounded` fails (`elapsed ~ 30`). CFE-4726 still sets `repair_timeout`. The *old* test would pass. The *new* test would not. The ladder cannot mask the gap because the ladder is what the gap skips.

The payload is `sleep 30`, not `exec sleep 30`. `ALARM_PID` names the shell. `GracefulTerminate(sh)` is enough to prevent `touch oc_completed` even if B-2's group kill is skipped: the marker is the next command in the dying shell. An orphaned `sleep` can still be running when the test passes. This test discriminates CFE-4727. It does not discriminate "the sleep died." That is fine for this ticket and should not be sold as a descendant test.

Pre-fork flake: this test uses production order and a 2 s timeout. Under load it can fail a correct fix the way the unit test's first draft did. Sequential acceptance is less loaded than `make check`; I still would not call the 2 s / 25 s pair a load-proof pin of the production publish path.

---

## Author uncertainties, by name

### 1. The residual pid-recycling race

The "handful of instructions vs deterministic gap" comparison is the right *trade*, and the duration I measured is microseconds, not a hidden `fclose`. The framing that the window is only reachable if the alarm fires *and* the pid is recycled is the error. The likely residual effect is a false `TIMEOUT_SIGNALLED` on a child that already exited, which needs no recycle. On the hang-after-EOF path the alarm has already been consumed before `waitpid` returns, so this window is not how CFE-4727 fails. Acceptable. Tighten later by blocking immediately after a successful `waitpid`, or by setting `TIMEOUT_SIGNALLED` only after a successful kill.

### 2. `sigprocmask()` thread-safety

Not sufficient. "Nothing else in this file blocks SIGALRM on the main thread" is a different proposition from "this helper runs on worker threads." I measured process-wide `sigprocmask` on the ship-from-here Darwin. `cf_pclose()` is reached from `cf-serverd` / `cf-execd` workers. That is not a live `RepairExec()` bug. It is a real defect of the new helper. Use `pthread_sigmask()`. House style already does. One line.

### 3. Full-duplex symmetry blast radius

Net-positive. The grep is right; the change is not inert; the widening is exactly "leaked alarm can now kill a full-duplex child *during wait* as well as during run." That widening disappears when B-15/B-16 are fixed, and the `pid == 0` path is *narrower* than the old unconditional wipe. Ship it. Name it. Do not wait.

### 4. `ALARM_PID` remains a non-volatile `pid_t`

A real formal gap, and not a new one. `TimeOut()` has always read `ALARM_PID` from a handler. Storage is `pid_t ALARM_PID` in `cf3globals.c`. Measured: `sizeof(pid_t) == sizeof(sig_atomic_t) == 4`. Torn access is not the live issue. Missing `volatile` is: a compiler may assume a plain global does not change asynchronously across a loop that makes no calls. The new write sits between two `sigprocmask()` calls, which are opaque and sufficient as barriers for *that* store. The handler's read is in another translation unit and will load from memory. Promoting to `volatile sig_atomic_t` is the same one-line family as `TIMEOUT_ARMED` and would match the flags sitting next to the only reader. Do it when convenient. Do not block CFE-4727 on a type that predates this commit. Do not claim `sigprocmask` *replaces* `volatile`; it replaces a signal-delivery race around the store.

### 5. Pre-fork race's scope decision

Defensible. The subject line names the closed-output case. The body discloses the remaining race. The unit test no longer depends on winning it. The acceptance test still does, slightly. That is a test note, not a reason to enlarge this SHA. A PR that says "exec_timeout now always terminates" would be the lie, not this commit's actual subject.

---

## Pre-existing defects the author deferred

| Deferred | Right to defer? | Why |
|---|---|---|
| Pre-fork `ALARM_PID` publish | **Yes as a code change.** | Different instant, different fix, already named. Entangled with this commit only through the 2 s acceptance test's flake mode. |
| CFE-4728 (iteration-counted ladder waits) | **Yes.** | Drives Darwin wall clock (~18 s here, not ~2+2). Already filed. This commit's 25 s / 30 s numbers are a workaround, not a silent dependency in the C. |
| CFE-4718 (`GetProcessState()` stub on Darwin) | **Yes.** | Same: test timing, not the `ALARM_PID` lifetime. This build links `process_unix_stub.o`. |
| `TIMEOUT_ARMED` / `ALARM_PID` not `volatile sig_atomic_t` | **Yes for `ALARM_PID`; already done for `TIMEOUT_ARMED` on this branch** (`d004c19ab`). | See uncertainty 4. |
| `RepairExec()` / `nfs.c` / `history.c` armed-timeout leaks (B-15 and the error-path family) | **Yes.** | Pre-existing. This commit makes a leaked alarm *more* able to kill during `cf_pclose` wait, which is the intended direction for a still-registered child. Do not "fix" B-15 by putting the pre-clear back. |
| B-16 (`ShellCommandReturnsZero` leaves a reaped pid in `ALARM_PID`) | **Yes, with one sentence.** | Old `cf_pclose()` accidentally wiped that stale pid at entry. New `ClearAlarmedPid` only clears a matching pid, so a B-16 leftover survives a later close of a *different* pipe. Next `cf_popen` still overwrites it. Severity unchanged in practice; the accidental cleaner is gone. |
| `LoadMountInfo` / `MountAll` disarm before wait | **Yes.** | This commit cannot help a timeout that was cancelled before `cf_pwait()`. Separate bug. |
| `TimeOut()` is not async-signal-safe (`Log`, `GracefulTerminate` / `nanosleep`) | **Yes.** | Pre-existing. Same handler the read-loop timeout already used. |

None of these make wait-then-clear internally contradictory. The one thing this commit *introduced* that should not wait for its own ticket is `pthread_sigmask()` in `ClearAlarmedPid()`.

---

## Recommendation for the fork issue / PR

Offer `254cbe593` as the termination half of CFE-4727. Record, in the author's voice or the commissioning session's:

1. Independent review agrees the clear-before-wait store is the defect, and independently measured old ≈ 30 s / not signalled vs new ≈ 2 s / signalled on a single-process model, plus a Pass of the rewritten acceptance test at 18.2 s of markers with "was terminated" and no completion file.
2. Independent review disagrees that the residual post-reap window is only a pid-recycling kill. The live leftover is a false `TIMEOUT_SIGNALLED` if the alarm is due when `waitpid` has already succeeded. On the hang-after-EOF path the alarm is already consumed.
3. On macOS 26.6.1 arm64, `sigprocmask(SIG_BLOCK, SIGALRM)` in a worker writes the process mask (measured). `cf_pclose()` runs on `cf-serverd` / `cf-execd` workers. Switch `ClearAlarmedPid()` to `pthread_sigmask()` in this series. Not a reason to unwind wait-then-clear. Not a live `RepairExec()` bug.
4. The three "cf_pclose error paths" in the commit message are one `cf_pclose` path (`fd >= MAX_FD`) and two `cf_pclose_full_duplex` paths. Failed `fclose` in `cf_pclose` still waits. Fix the prose.
5. Full-duplex symmetry is fine; name the B-15 wait-window widening.
6. Pre-fork publish remains a separate ticket. Do not let the PR summary say the termination guarantee is now complete. The acceptance test still uses a 2 s production-order timeout and can flake the way the unit test's first draft did.

No other code change required before the offer. The `pthread_sigmask` switch is the one I would actually make in the same series rather than file and forget.
