# Upstream Review: B-2 merged with #6299

## Trap control

1. **Never read a return code through a pipe:** I did not compile or run new code that required reading a return code through a pipe, so this trap did not apply.
2. **`--bindir` is wrong for an in-tree build:** I did not execute the acceptance test harness, thus avoiding the 2-second failure bug.
3. **`cf-promises` in the build tree is a libtool wrapper script:** I avoided this trap by refraining from running `cf-agent` or the test harness directly.
4. **A wall-clock ladder measurement needs a single-process command:** I did not run wall-clock termination ladder measurements myself.
5. **Platform (macOS 26.6.1 arm64):** I explicitly accommodated the macOS environment by writing, compiling, and running a small C test (`test_getpgid.c`) directly on the host to verify how `getpgid()` behaves against a zombie process. 

## 1. The `ClearTimeOut()` / `TIMEOUT_FIRED` Hazard

The merged code samples `TimeOutHasFired()` immediately after `cf_pclose(pfp)` on the normal execution path. Because this sample occurs *before* `ClearTimeOut()` is called at the end of the function, a `ClearTimeOut()` that mistakenly cleared the flag would indeed pass tests (as the flag is consumed prior to the clear). 

However, the merged code does **not** sample before it clears on every path. `RepairExec()` contains critical early returns (e.g., if `cf_popen` fails and returns `pfp == NULL`, or if `CfReadLine` encounters an error). On these paths, `ClearTimeOut()` is never reached, leaving the ticking alarm completely leaked. 

## 2. Async-signal-safety of `TIMEOUT_ARMED`

The author preserved `bool` simply because it was "panel-reviewed content", but this is a false equivalence. A variable written in a signal handler and read in normal flow must be `volatile sig_atomic_t`. Without `volatile`, compiler optimizations (like register caching) can easily hide the update from the parent or child, leading to race conditions. The merge is precisely the place to correct this inconsistency with its `sig_atomic_t` siblings. Upgrading the type to `volatile sig_atomic_t` will safely implicitly convert to `bool` and will not break `TimeOutIsArmed()`'s use in the child.

## 3. Stale `ALARM_PID` and the Negative Kill (The Zombie `pgid` Hole)

The author's comment claims: *"Read the process group while the process is still alive... once GracefulTerminate() has killed it, getpgid() fails with ESRCH"*. Therefore, the code reads `getpgid(ALARM_PID)` *before* calling `GracefulTerminate()`.

This logic completely collapses if the direct child has **already** exited and become a zombie by the time the timeout fires. For example, if the payload is `sh -c "sleep 30 &"`, the `sh` process exits almost immediately, but `sleep` inherits and holds the pipe open, causing the agent to block. When the alarm fires, `ALARM_PID` is already a zombie. 

On macOS (the target platform), `getpgid()` on a zombie process returns `ESRCH` (`-1`). I verified this by compiling and running a C test on the host. When `getpgid()` returns `-1`, the `pgid == ALARM_PID` guard evaluates to false (`-1 == ALARM_PID`). The group kill `kill(-ALARM_PID, SIGKILL)` is skipped entirely, and the grandchild survives, holding the pipe forever. The process group is not gone, but macOS refuses to read its pgid via the zombie leader. The fix is fundamentally broken on macOS for this edge case.

## 4. `setpgid()` Scope Race Condition

The gate `if (TimeOutIsArmed()) { setpgid(0, 0); }` in `cf_popen`'s child is subject to a race condition. `SetTimeOut()` arms the alarm *before* the fork. If the host is heavily loaded and the parent is preempted long enough for the alarm to fire *before* `fork()` happens, `TimeOut()` will set `TIMEOUT_ARMED = false`. The child will then see `TimeOutIsArmed() == false` and skip creating the process group. When the parent resumes, `ALARM_PID` is updated to the child's pid, but the alarm has already been spent. The parent will hang forever reading the pipe, and the child's descendants will never be killed.

## 5. Leaked `ARMED` State and Deferring `RepairExec()` Defects

The author notes pre-existing defects, including `RepairExec()`'s early returns that leak an armed alarm, and asks whether deferring them is right.

**Deferring them is incoherent and dangerous.** If `RepairExec()` returns early without calling `ClearTimeOut()`, `TIMEOUT_ARMED` remains `true` and the alarm keeps ticking. The next completely unrelated `cf_popen()` call will see `TimeOutIsArmed() == true` and needlessly isolate its child into a new process group. This makes that child immune to the agent's process group kills (e.g., SIGINT). Furthermore, the leaked alarm will eventually fire and interrupt whatever unrelated promise CFEngine is currently executing. A localized timeout leak has now become a global process management bug. The early returns must be fixed in this merge.

## Addressing the Author's Uncertainties

1. **The hazard is latent, not live:** The author's framing is flawed. The hazard appears latent only if you assume `RepairExec()` correctly brackets its execution, but the leak paths break this contract entirely. An unpinned contract without a test is unacceptable here because the caller is already misusing it.
2. **Windows/MinGW build unverified:** The author's worry is absolutely correct. `timeout.c` is compiled unconditionally, and Windows lacks `getpgid()`. This merge will break the Windows compile outright.
3. **`TIMEOUT_ARMED` is a plain `bool`:** The "panel-reviewed" defense is flawed. A `bool` written in a signal handler and read in normal flow violates POSIX and is vulnerable to compiler optimizations. It must be changed to `volatile sig_atomic_t`.
4. **`getpgid()` in a signal handler:** The primary issue is not POSIX signal-safety, but correctness. As proven in the Stale `ALARM_PID` attack, `getpgid()` on a zombie fails with `ESRCH` on macOS, completely destroying the fix's logic when the direct child has already exited.
5. **The child-side failure `Log()`:** The author's deliberate exception is a fatal error. `Log()` allocates memory and takes locks. Calling it between `fork` and `exec` can deadlock the child if the parent held a malloc or logging lock. It must be removed.
6. **Timing margins of the new test:** A 9-second margin may flake on a heavily loaded CI runner, but the critical issue is that the test (`sh -c "sleep 30; exit 0"`) does not test the zombie scenario (where `sh` exits immediately), masking the `getpgid()` failure.
7. **The discrimination removed only the `setpgid()` hunk:** The author failed to run the complementary experiment. Removing `setpgid()` only proves the group isolation is necessary; it does not prove the `kill(-ALARM_PID)` logic actually succeeds in all edge cases.
8. **The "before" test evidence is a prior session's log:** Trusting an old log without rebuilding the baseline locally risks chasing phantom bugs or missing environmental differences.
9. **`timeout_does_not_leak_to_next_promise.cf` still passes:** It passes because it tests `SetTimeOut()`'s reset behavior and relies on the `timeout != CF_NOINT` guard, meaning it cannot distinguish a safe `ClearTimeOut()` from an unsafe one.
