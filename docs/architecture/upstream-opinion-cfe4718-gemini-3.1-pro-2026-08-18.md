# Review of CFE-4718 (process_darwin.c)

## Q1. `len == 0` check
**Verdict:** Acceptable, but theoretically fragile.
**Reasoning:** I verified via a C program probing `sysctl(CTL_KERN, KERN_PROC, KERN_PROC_PID, pid)` that a nonexistent PID indeed returns `rc=0` and `len=0` on macOS. It does not fail with an errno. So checking for a 0 length is the correct way to identify a non-existent process. If `sysctl` fails with an errno (like `ENOMEM`), the prior check `sysctl(...) != 0` catches it and correctly maps it to `PROCESS_STATE_DOES_NOT_EXIST`.
However, the brief asserts this check is *sufficient*. Because `psinfo` is not zeroed prior to the call (`process_darwin.c:41`), if a future kernel returns a partial struct (`len > 0` but `len < sizeof(psinfo)`), reading `psinfo.kp_proc.p_starttime.tv_sec` would read uninitialized stack memory. It is safer to check `len < sizeof(psinfo)` rather than `len == 0`.

## Q2. Struct layout changes
**Verdict:** Safe (fails closed).
**Reasoning:** I verified empirically that if a caller provides a `len` smaller than the kernel's `kinfo_proc` size, `sysctl` fails with `ENOMEM` (errno 12). If Apple ever expands the struct and a legacy CFEngine binary requests the old size, `sysctl(...) != 0` will trigger and return `false`, safely falling back to `PROCESS_STATE_DOES_NOT_EXIST`. The `len == 0` check remains valid for the success path.

## Q3. `SIDL` mapping
**Verdict:** Correct.
**Reasoning:** `SIDL` means the process is being created by fork. Mapping this to `'R'` (RUNNING) means `ProcessWaitUntilExited` (`process_unix.c:95`) will correctly continue polling (`break; /* retry in a while */`) rather than immediately aborting. This is exactly what we want when waiting for a process to become killable or to finish exiting.

## Q4. Build wiring
**Verdict:** Correct.
**Reasoning:** I checked `m4/cf3_platforms.m4:33,41`. Both `MACOSX` and `XNU` are aliases for exactly the same check (`echo ${target_os} | grep -q darwin`). Using `MACOSX` matches the convention in `libpromises/Makefile.am:209`. Adding `if !MACOSX` to the stub guard chain prevents multiple definitions and correctly isolates the build.

## Q5. `process_test` XFAIL
**Verdict:** Correct to remove.
**Reasoning:** The test relies on `SIGSTOP`/`SIGCONT` and zombie detection, which the stub failed to handle. Now that `process_darwin.c` implements `PROCESS_STATE_STOPPED` and `PROCESS_STATE_ZOMBIE`, the test passes. Since this test runs reliably in CI for Linux and FreeBSD, there is no inherent flakiness that warrants keeping it XFAIL'd on macOS.

## Q6. Start time resolution
**Verdict:** Sufficient.
**Reasoning:** I verified `process_linux.c:123` manually degrades Linux's clock-tick resolution down to seconds (`starttime / sysconf(_SC_CLK_TCK)`). `tv_sec` on Darwin exactly matches the 1-second resolution of Linux and FreeBSD implementations in CFEngine. A 1-second race condition on PID reuse is an accepted limitation of the overarching API.

## Q7. Commit message attribution
**Verdict:** Sound.
**Reasoning:** I verified the logic in `GracefulTerminate()` (`process_unix.c:261`). When a zombie is correctly identified, `ProcessWaitUntilExited` returns `true` immediately (`process_unix.c:102`). The previous stub reported zombies as `RUNNING`, causing `ProcessWaitUntilExited` to poll until exhaustion (1 second per call). The ~7s wait was entirely due to the stub's inability to recognize zombies. The attribution to zombie visibility is accurate.

## Trap control
- **Files opened/checked:** I opened `UPSTREAM-CFE4718-REVIEW-BRIEF.md`, `libpromises/process_unix.c`, `libpromises/locks.c`, `libpromises/process_linux.c`, and `libpromises/Makefile.am`. I used grep to check `m4/cf3_platforms.m4` and `tests/unit/Makefile.am`. I used `git show` to examine the patch itself.
- **Probes run:** I wrote and compiled several C programs using `clang` to empirically test `sysctl` and `proc_pidinfo` for self, pid 1, stopped, zombie, reaped, and nonexistent processes. I also specifically tested `sysctl` behavior when passed a truncated `len`. I did **not** build CFEngine or run the test suite, taking the test pass counts on trust.
- **Overstated/Wrong:** The brief confidently claims the `len == 0` check is sufficient. While it distinguishes existence from non-existence, it neglects the fact that `psinfo` is uninitialized on the stack. If `sysctl` ever returns a partial struct, the code would read stack garbage. A more robust check is `len < sizeof(psinfo)`. Also, the brief suggests Linux returns "jiffies-derived seconds" natively; Linux actually provides clock ticks (jiffies), and it is CFEngine's `process_linux.c` that downsamples this to seconds.

## REQUIRED CHANGES
*(None)*

## OPTIONAL
- **`libpromises/process_darwin.c:53`**: Change `if (len == 0)` to `if (len < sizeof(psinfo))`. This protects against the hypothetical scenario where a future kernel returns a partial struct, preventing CFEngine from reading uninitialized stack memory.

## VERDICT
SHIP
(Ship with the optional change applied if possible, as it is a zero-cost defensive improvement, but the core logic is sound and heavily improves macOS process handling).
