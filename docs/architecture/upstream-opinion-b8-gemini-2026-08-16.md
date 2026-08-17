# Upstream Review: B-8 (exec_timeout fail-open)

## 1. Verdict
**Do not ship.** 

While the patch correctly identifies a fail-open condition and the approach of classifying on `TIMEOUT_FIRED` is sound, the implementation has a critical race condition that causes the timeout to be entirely missed if the command closes its output streams but continues running. Furthermore, an underlying issue in `cf_pclose` prevents the child from being killed at all in this scenario.

## 2. Severity verdict
**Ship to security@.**

This is a genuine fail-open that compromises the integrity of policy evaluation. If a security-critical check (e.g., verifying a malicious process isn't running, or validating a downloaded payload) hangs, the timeout firing can currently result in a "kept" promise (0% non-compliance). A subsequent promise that depends on this check's success class will execute, assuming the system is safe when it is actually in an unknown state. This violates the core CFEngine contract that a kept promise indicates the desired state was successfully verified.

## 3. Defects found

### Verified Defect 1: Timeout flag evaluated too early
- **File:** `cf-agent/verify_exec.c`
- **Line:** ~445 (`timed_out = (a->contain.timeout != CF_NOINT) && TimeOutHasFired();`)
- **Impact:** If the child process closes its `stdout` and `stderr` (or redirects them to `/dev/null`) but continues running, the `CfReadLine` loop reaches `EOF` and exits. The code then evaluates `timed_out` as `false` and blocks in `cf_pclose()` (which calls `waitpid`). If the timeout expires while waiting in `cf_pclose()`, the `TIMEOUT_FIRED` flag is set, but `timed_out` is already `false`. The timeout is missed, and the command's eventual exit status is used for classification, reproducing the fail-open.
- **Reproducer:** 
  ```cfengine3
  body common control { bundlesequence => { "t" }; }
  body contain c { useshell => "noshell"; exec_timeout => "2"; }
  bundle agent t {
    commands:
        "/bin/sh" arglist => { "-c", "exec >&- 2>&-; sleep 4; exit 0" }, contain => c;
  }
  ```

### Verified Defect 2: Child is not killed if timeout fires during `cf_pclose`
- **File:** `libpromises/pipes_unix.c` (pre-existing, but breaks the patch's intent)
- **Line:** ~853 (`ALARM_PID = -1;` in `cf_pclose()`)
- **Impact:** Before `cf_pclose()` calls `cf_pwait(pid)`, it unconditionally clears `ALARM_PID`. If the command has closed its output streams (triggering the read loop to exit early) and the timeout fires while blocking in `cf_pclose`, `TimeOut()` sees `ALARM_PID == -1` and does nothing. The child process is never sent `SIGKILL` and is allowed to run indefinitely, completely defeating the `exec_timeout` mechanism.

## 4. The six questions

1. **Is the severity claim right?**
   Yes. It is a fail-open that warrants reporting to `security@`. The exit status of a timed-out command is inherently unreliable (especially if the shell reaps its killed child and exits 0). Trusting it allows policies to execute dependent actions based on false premises.
2. **Is the flag read at the right point?**
   No. It is read before `cf_pclose()`. It must be read after `cf_pclose()` to account for timeouts that expire while waiting for the child process to exit. 
3. **Is `volatile sig_atomic_t` the right type and is the handler safe?**
   Yes. The patch actually *improves* async-signal-safety by removing the unsafe `Log()` and `GracefulTerminate()` calls from the signal handler and replacing them with a safe `kill(..., SIGKILL)` and a `sig_atomic_t` flag.
4. **Does it change behaviour for commands that do NOT time out?**
   No. Commands without timeouts (`CF_NOINT`) bypass the flag check. Commands that fail naturally or are backgrounded behave as before.
5. **Is classifying on the timeout instead of the exit status the right design?**
   Yes. A timeout means the check failed to complete within the required constraints. Overriding the user's `kept_returncodes` is correct because the exit status of a terminated command is meaningless; honoring it would perpetuate the fail-open.
6. **Backward compatibility.**
   No downstream issues identified. `PROMISE_RESULT_TIMEOUT` is already handled gracefully by the reporting pipeline and `PromiseResultIsOK()`.

## 5. What you did not check
- I did not verify if `TimeOut()` in `cf-serverd` or `cf-execd` might be impacted by the changes to `TimeOut()`, although they appear to rely on the same `timeout.c` logic.
- I did not check if the removal of `GracefulTerminate()` (and its termination ladder) causes zombie processes or orphaned grandchildren in edge cases, though `SIGKILL` is standard for hard timeouts.
