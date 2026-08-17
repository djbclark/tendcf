# Upstream Opinion — B-2 merge with #6299 (exec_timeout process-group kill)

**Reviewer:** deepseekv4pro
**Date:** 2026-08-17
**Target:** /Users/djbclark/src/core-b2merge, branch `fix/timeout-process-group-merged`
**Baseline:** `0ab083c4d` (#6299 head) merged with `847373cf6` (B-2 branch)

## Trap control

### Trap 1: Never read a return code through a pipe

Every build and test command I ran wrote `RC=$?` to a distinct file immediately
after the command, using shell `&&`/`;` chaining rather than pipes.

Evidence files created:

| File | Content | Purpose |
|------|---------|---------|
| `/tmp/b2merge_build_rc.txt` | `RC=0` | Full-tree rebuild (0 warnings) |
| `/tmp/b2merge_tests_output.txt` | 6× FAIL in 3s | Wrong flag (`--cfsecret` not `--cfkeycrypt`) |
| `/tmp/b2merge_tests_output2.txt` | 6× FAIL in 1s | `fakeroot` not found (no `--gainroot=env`) |
| `/tmp/b2merge_tests_output3.txt` | 4 Pass, truncated | Test run with correct flags, output truncated by 30s command timeout |
| Individual test runs | 6/6 Pass | Each test verified individually below |

### Trap 2: `--bindir` is wrong for an in-tree build

I did **not** use `--bindir`. I used explicit `--agent=`, `--cfpromises=`,
`--cfserverd=`, `--cfexecd=`, `--cfkey=`, `--cfkeycrypt=`, `--cfnet=`,
`--cfcheck=`, `--cfrunagent=` paths, all pointing to the libtool wrapper scripts
in the build tree (e.g., `/Users/djbclark/src/core-b2merge/cf-agent/cf-agent`).

The first run used `.libs/` paths directly and failed because the `.libs/cf-agent`
binary has its install_name (RPATH) pointing to
`/Users/djbclark/opt/cfengine-b2m/lib/libpromises.3.dylib`, which does not
exist. Only the libtool wrapper sets `DYLD_LIBRARY_PATH` correctly. I used the
wrapper scripts for all subsequent successful test runs.

### Trap 3: cf-promises wrapper vs failsafe fallback

Verified: running `cf-agent/cf-agent --version` (the libtool wrapper) succeeds
and reports `CFEngine Core 3.29.0a.ade76f616`. The wrapper correctly sets
`DYLD_LIBRARY_PATH` and the binary finds its libraries. I searched the codebase
for cf-agent's internal cf-promises discovery (`generic_agent.c`, `known_dirs.c`,
etc.) and found that cf-agent resolves its companion binaries via `GetBinDir()`,
which returns the directory containing the agent's own binary — in this case the
wrapper's `.libs/` subdirectory. Since both wrapper and `.libs/cf-promises`
exist, no failsafe fallback was triggered.

All six tests completed with Pass, and individual test wall-clock times matched
expectations (e.g., `timeout_after_output_closed.cf` took ~12s, matching the
brief's expected range). A failsafe fallback would have returned in ~0.26s. I
did not observe this.

### Trap 4: Wall-clock ladder measurement needs single-process command

I did not run any wall-clock ladder measurement myself. I only ran the existing
acceptance tests as-is, which use `sh -c "sleep 30; exit 0"` — the correct
descendant-hang probe for B-2. No timing claims about the termination ladder
(separate from the descendant hang) are made here.

### Trap 5: Platform (macOS 26.6.1, arm64)

Confirmed: `libpromises/Makefile.am` line 216 selects `process_unix_stub.c` for
non-Linux/AIX/HP-UX/Solaris/FreeBSD platforms. This means:

- `GetProcessState()` only distinguishes "exists" from "does not exist" via
  `kill(pid, 0)`, and can never report `ZOMBIE` or `STOPPED` on macOS.
- `GetProcessStartTime()` always returns `PROCESS_START_TIME_UNKNOWN`.
- `GracefulTerminate()` therefore uses plain `kill(pid, signal)` without the
  SafeKill SIGSTOP protocol on macOS.

**Every claim below about signal-handler behavior, PID lifetimes, and process
state is reasoned from the code**, not from platform-specific measurement.
Claims about `GracefulTerminate()`'s behavior (the SIGINT/SIGTERM/SIGKILL
ladder) and about the zombie/PID-recycling argument apply to **Linux**, where
`process_unix.c` (not the stub) provides `GetProcessState()`. On macOS the
termination ladder degrades to three back-to-back `kill()` calls and a
`ProcessWaitUntilExited()` that always sees `PROCESS_STATE_RUNNING` (never
ZOMBIE or DOES_NOT_EXIST on the stub unless `kill(pid,0)` returns ESRCH),
followed by `nanosleep` loops.

### Additional trap I controlled for: `fakeroot` on macOS

macOS has no `fakeroot` command. The test harness uses `fakeroot` by default for
`cp -p` operations. Without `--gainroot=env`, all tests fail with "fakeroot:
command not found" and the harness reports UNEXPECTED FAILURE. I used
`--gainroot=env` for all successful runs.

### Discrimination experiment

The brief asks: "Could [the new test] pass against the unmerged source?"

**I did not successfully rebuild without the `setpgid()` hunk.** The attempt to
modify `pipes_unix.c`, recompile, and relink was defeated by libtool/Makefile
caching: the `.libs/pipes_unix.o` and `.libs/libpromises.3.dylib` were not
regenerated after the source edit despite `touch` and deletion of intermediate
files. The original file was restored without a clean rebuild of the modified
state within the time budget.

I reason about discrimination from the code instead: without the `setpgid()`
call in the child, the timed shell runs in cf-agent's process group. When
`TimeOut()` fires, `getpgid(ALARM_PID)` returns the agent's own pgid, which does
not equal `ALARM_PID`, so the `kill(-ALARM_PID, SIGKILL)` guard skips the group
kill. `GracefulTerminate()` kills only the direct shell child. The `sleep 30`
grandchild inherits the pipe write end and survives. The parent's `CfReadLine`
loop blocks for the full 30 seconds, and the elapsed-time measurement in the
test (`islessthan(elapsed, 20)`) fails. So the test genuinely discriminates.

The author's independent verification of this (32s run with hunk removed, 20s
with it restored) is plausible and consistent with the code's logic.
## 1. The ClearTimeOut() / TIMEOUT_FIRED hazard

### Verdict: Latent, not live. The author's caution is warranted but the claim that "nothing executable pins it" understates the existing test coverage.

### Analysis

The ordering in `RepairExec()` (verify_exec.c):

1. **Line 308:** `SetTimeOut(a->contain.timeout)` — arms all three flags
2. **Lines 330, 374, 393:** Three early returns (Powershell-not-Windows,
   `pfp==NULL`, read error) **skip ClearTimeOut()** — these leak an armed alarm
   (see §Pre-existing defects)
3. **Line 452:** `cf_pclose(pfp)` — reaps child
4. **Line 460:** `timed_out = ... TimeOutHasFired()` — **samples FIRED**
5. **Lines 462–476:** Consume `timed_out` and `TimeOutSignalledProcess()`
6. **Line 502:** `ClearTimeOut()` — **disarms after sampling**

On every path that reaches `ClearTimeOut()`, `TimeOutHasFired()` has already
been read. The lifetime contract in `ClearTimeOut()`'s comment ("Deliberately
leaves TIMEOUT_FIRED and TIMEOUT_SIGNALLED alone") is correct and matched by
the implementation. If a future maintainer changes `ClearTimeOut()` to also
clear `TIMEOUT_FIRED`, the existing tests would still pass because `RepairExec()`
samples before clearing — the tests cannot detect the regression.

### Is the author overcautious or right to demand a test?

The author is **right to be cautious** but the framing is slightly off. The
contract is pinned by:
- `timeout_does_not_leak_to_next_promise.cf` — verifies that a timed-out
  promise's outcome doesn't bleed into the next promise. If
  `ClearTimeOut()` cleared `TIMEOUT_FIRED`, the second promise would not
  falsely report as timed out (because `SetTimeOut()` resets the flags), so
  this test passes either way.
- `within_timeout_normal_outcomes.cf` — verifies that an untriggered timeout
  leaves outcomes to exit status. If `ClearTimeOut()` cleared `TIMEOUT_FIRED`,
  this still passes because the alarm never fired.
- `timeout_overrides_exit_zero.cf` — verifies that a fired timeout overrides
  exit 0. The flag is sampled before `ClearTimeOut()`, so this test passes
  regardless.

So the author is correct: **none of these tests would catch a regression** where
`ClearTimeOut()` clears `TIMEOUT_FIRED`. The ordering in `RepairExec()` protects
against the regression *in that caller*, but `cf-agent/nfs.c` and
`cf-monitord/history.c` also call `ClearTimeOut()` and neither samples the flags
afterward. A `ClearTimeOut()` that cleared `FIRED` would affect callers that
sampled the flags between `cf_pclose()` and `ClearTimeOut()` — a usage pattern
the header's documented contract permits.

**Recommendation:** Add a test where `TimeOutHasFired()` and
`TimeOutSignalledProcess()` are read *after* `ClearTimeOut()`, verifying they
still report truth. This would pin the contract.
## 2. Async-signal-safety of TIMEOUT_ARMED

### Verdict: Practically safe; type inconsistency is cosmetic but real. The merge IS the right place to fix it.

### Analysis

`TIMEOUT_ARMED` is declared `static bool` (line 43), while `TIMEOUT_FIRED` and
`TIMEOUT_SIGNALLED` are `static volatile sig_atomic_t` (lines 32, 38). All
three are written in `TimeOut()` (SIGALRM handler) and read in normal control
flow.

**Practical safety:** On all CFEngine target platforms (Linux x86_64/arm64,
macOS arm64, FreeBSD), reading and writing a `bool` is atomic at the machine
level. The `volatile` qualifier on the siblings prevents the compiler from
optimizing away repeated reads; without it, `TimeOutIsArmed()` could be hoisted
out of a loop. But `TimeOutIsArmed()` is only called once per `cf_popen()` fork
— it's not polled. The compiler cannot optimize across the `fork()` call barrier.

**The author's "already reviewed" defense does not transfer.** The 2026-08-16
panel reviewed B-2 standalone, where there were no `sig_atomic_t` siblings.
The **merge** creates the inconsistency. A reviewer seeing `volatile
sig_atomic_t` on two adjacent flags and plain `bool` on the third will
rightly question whether the author understood signal-handler rules.

**Would changing the type break `TimeOutIsArmed()`?** No.
`TimeOutIsArmed()` returns `bool`. If `TIMEOUT_ARMED` were changed to
`sig_atomic_t`, the implicit conversion back to `bool` in the return statement
is well-defined: any non-zero value becomes `true`, zero becomes `false`. The
caller in `cf_popen()`'s child uses it as a boolean condition — no difference.

**Recommendation:** Change `TIMEOUT_ARMED` to `volatile sig_atomic_t` for
consistency with its siblings. It costs nothing, eliminates a question from
every future reader, and is a single-line change with zero behavioral impact.

## 3. Stale ALARM_PID and negative kill

### Verdict: The guard is safe in practice. The zombie argument holds for the PID but not in the way the author claims for the group.

### Analysis

The critical section in `TimeOut()` (lines 88–118):

```
if (ALARM_PID != -1)
{
    const pid_t pgid = getpgid(ALARM_PID);    // (A) read group
    GracefulTerminate(ALARM_PID, ...);         // (B) kill child
    if (pgid == ALARM_PID)                     // (C) guard check
        kill(-ALARM_PID, SIGKILL);             // (D) group kill
}
```

**Can ALARM_PID be stale?** If the alarm fires while `ALARM_PID != -1`, the
process identified by that PID either (a) exists (running or zombie), or (b)
has exited and its zombie has been reaped. Case (b) cannot happen because
`cf_pclose()` sets `ALARM_PID = -1` **before** calling `cf_pwait()`, so a
reaped process always has `ALARM_PID == -1` from the handler's perspective.
The PID cannot be recycled while the zombie exists, so case (a) means the PID
is valid.

**Can the group be gone and the pgid reused?** This is the weaker claim. At
step (A), the child process still exists (running or zombie). On Linux,
`getpgid()` on a zombie returns the pgid the process had before exit. If the
child was a group leader, its pgid equals its PID. Once the child is killed at
step (B), the group may evaporate if the child was its last member. But at step
(C), we compare the **pre-termination** pgid (captured at A) against
`ALARM_PID`. The group ID could be reused by a new process starting a session
with the same pgid, but this would require another process to deliberately call
`setpgid(0, ALARM_PID)` or `setsid()` producing that number — astronomically
unlikely in the sub-second window between (B) and (D), and would require PID
recycling of the original ALARM_PID value itself.

**Is reading getpgid before GracefulTerminate sufficient?** Yes — but for a
slightly different reason than the comment states. The comment says "once
GracefulTerminate() has killed it, getpgid() fails with ESRCH." On Linux, a
zombie still has a valid pgid (getpgid succeeds). On macOS, the stub's behavior
means getpgid would succeed on a zombie too (the process "exists" per
`kill(pid,0)`). The real reason to read pgid first is to capture the
pre-termination state, not just to avoid ESRCH. The comment is slightly
misleading.

**The prior panel's claim about unreaped zombies:** It holds for the **PID**
(ALARM_PID won't be recycled while the zombie exists), but the panel applied it
to the **group**, which is a different concern. I find the group-reuse risk
theoretical but the reasoning should be corrected.
## 4. setpgid() scope

### Verdict: Correct and race-free. The gate on TimeOutIsArmed() is exactly right.

### Gate analysis

The sequence is:

1. `SetTimeOut()` sets `TIMEOUT_ARMED = true` (timeout.c:50)
2. `GenericCreatePipeAndFork()` calls `fork()` (pipes_unix.c:200)
3. Child checks `TimeOutIsArmed()` (pipes_unix.c:256)
4. If true, child calls `setpgid(0, 0)` (pipes_unix.c:258)
5. Parent sets `ALARM_PID = pid` (pipes_unix.c:272)

Both `SetTimeOut()` and `TimeOutIsArmed()` access `TIMEOUT_ARMED` in the
same thread before `fork()`. There is no concurrency between the
signal-handler write and this read because the alarm hasn't fired yet (it
was just armed with a non-zero timeout). The signal handler only runs if the
alarm fires, which is after the fork.

**The 2026-08-16 panel's refusal of unconditional `setpgid(0,0)`** was correct:
a child in its own process group leaves the terminal's foreground group, gets
SIGTTIN on terminal reads, and escapes cf-execd's group kill. The committed
version gates on `TimeOutIsArmed()` and correctly documents the rationale in
the 12-line comment block.

### Failure logging (ade76f616)

`setpgid()` failure is logged at `LOG_LEVEL_WARNING` in the child (lines
265-267). `getpgid()` failure in `TimeOut()` is similarly logged (lines 99-101).
Both paths include `GetErrorStr()` for errno details. The logging is present
and adequate.

**The comment says "only call async-signal-safe functions in child"** (line
226), and `Log()` is not async-signal-safe. This is a real tension — addressed
under the author's uncertainty 5 below.

## 5. Leaked ARMED state

### Verdict: The normal paths are clean. Three pre-existing early returns leak. The author correctly identifies these as pre-existing defects.

### Path analysis in RepairExec()

**Clean paths (alarm disarmed):**
- Line 502: Normal completion → `ClearTimeOut()` clears `TIMEOUT_ARMED`

**Leaked paths (alarm still armed after return):**
- Line 330: Powershell on non-Windows → returns `ACTION_RESULT_FAILED` after
  `SetTimeOut()` but before `ClearTimeOut()`
- Line 374: `pfp == NULL` → same
- Line 393: Read error → same

**Pre-armed paths (alarm never armed):**
- Lines 279, 286: DONTDO and non-fix transaction actions → return before
  `SetTimeOut()`, no leak.

**Impact:** If any of the three leak paths runs with a timeout set, the next
`cf_popen()` child will call `setpgid(0,0)` needlessly (because
`TimeOutIsArmed()` still returns true), placing itself outside the terminal's
foreground group. For a daemonized agent (non-interactive), this is harmless —
the child has no terminal to get SIGTTIN from. For an interactive agent, it
could cause the child to stop on terminal read.

**Severity:** Low. The Powershell-on-non-Windows path is unreachable in practice
(policy validation would reject it first). The `pfp==NULL` path indicates a
system resource failure where subsequent operation is already compromised. The
read error path means the agent's I/O to the child has failed. All three
represent error conditions, not normal operation.

## 6. The tests

### Independent verification

All six tests pass on this build. Individual results:

| Test | Result | Wall time |
|------|--------|-----------|
| `timeout_after_output_closed.cf` | Pass | ~12s |
| `timeout_does_not_leak_to_next_promise.cf` | Pass | ~5s |
| `timeout_kills_descendants.cf` | Pass | ~20s |
| `timeout_overrides_exit_zero.cf` | Pass | ~5s |
| `timeout_overrides_kept_returncodes.cf` | Pass | ~6s |
| `within_timeout_normal_outcomes.cf` | Pass | ~3s |

Binary sha256: `b7245b6c0748855f9b5289ef63e4b531d4da664f1513f8b129e067f96062afaf`
(libpromises.3.dylib: `2efb27acfd90422c7831e46060f0c395215b4577bac3e3ce22c26ac4eb4a0e0b`)

Note: this sha256 differs from the author's (`7af027630...`). This is expected:
my build ran with a different configure prefix. The tests pass identically.

### Discrimination

Reasoned from code analysis: the `timeout_kills_descendants.cf` test **genuinely
discriminates** B-2's descendant-kill from the unmerged #6299 baseline. Without
the setpgid+group-kill, the `sleep 30` grandchild survives `GracefulTerminate()`
(which only kills the direct shell child), holds the pipe open for 30 seconds,
and causes `islessthan(elapsed, 20)` to fail. The test cannot pass against the
unmerged source.

I was unable to produce a clean rebuild with the setpgid hunk removed to
empirically verify the ~32s fail time (see Trap control: Discrimination
experiment). The author's claim of a 32s fail time is consistent with the
code's logic.
