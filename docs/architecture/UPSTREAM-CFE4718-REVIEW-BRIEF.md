# Review brief — CFE-4718 (B-3): no `process_darwin.c`, macOS runs on the process stub

Frozen 2026-08-18. Worktree `/Users/djbclark/src/core-darwin`, branch
`fix/process-darwin`, based on **upstream master `a0bca6aaf`**, commit
`70caf5e5f`. Upstream: `cfengine/core`. Jira: CFE-4718. Fork issue:
[djbclark/core#12](https://github.com/djbclark/core/issues/12).

This is **platform-support work, not a bug fix** — a new file implementing an
interface that already exists, rather than a change to existing logic. Review
it accordingly: the risk is in the new file being wrong on Darwin, and in the
build wiring silently selecting the wrong source on some platform.

## 1. The gap as filed

`libpromises/Makefile.am:209-220` selects `process_unix_stub.c` for any
platform that is not Linux, AIX, HP-UX, Solaris or FreeBSD. macOS is therefore
on the stub, where (`process_unix_stub.c:29,38`):

- `GetProcessStartTime()` returns `PROCESS_START_TIME_UNKNOWN` unconditionally.
- `GetProcessState()` distinguishes only "exists" from "does not exist" via
  `kill(pid, 0)`, so it can never return `PROCESS_STATE_ZOMBIE` or
  `PROCESS_STATE_STOPPED`.

Two consequences, both confirmed empirically this session rather than argued:

**(a) The PID-recycling guard is bypassed.** `Kill()`
(`process_unix.c:227-236`) falls back to a plain `kill(2)` whenever the start
time is `PROCESS_START_TIME_UNKNOWN`, so `SafeKill()` never runs on macOS.
Every `GracefulTerminate()` caller inherits that, including the stale-lock path
at `locks.c:630`. Narrow window, not known to have bitten anything.

**(b) Termination waits burn their full budget.** `kill(pid, 0)` succeeds on a
zombie, so a child that has already exited reads as `PROCESS_STATE_RUNNING`.
`ProcessWaitUntilExited()` returns immediately on `PROCESS_STATE_ZOMBIE`
(`process_unix.c:98-102`) — a return the stub can never produce — so both of
`GracefulTerminate()`'s `ProcessWaitUntilExited(pid, STOP_WAIT_TIMEOUT)` calls
poll to exhaustion before the SIGKILL fallthrough.

Measured, macOS 15 (arm64), child killed and left unreaped, three runs each,
`GracefulTerminate()` wall time:

| build | run 1 | run 2 | run 3 |
|---|---|---|---|
| `process_unix_stub.c` (today) | 7154 ms | 6884 ms | 7336 ms |
| `process_darwin.c` (this patch) | 16.5 ms | 49.9 ms | 0.7 ms |

`STOP_WAIT_TIMEOUT` is 999999999 ns polled in 10 ms steps, which predicts ~1 s
per call and ~2 s total; the observed ~7 s is because a 10 ms `nanosleep()`
costs roughly 35 ms in practice on this platform. Note the patched build does
*more* work per terminate, not less — it now has a real start time, so it takes
the `SafeKill()` SIGSTOP/SIGCONT path instead of a plain `kill(2)` — and still
finishes in tens of milliseconds. The seconds are the poll loops.

Harness: `/private/tmp/.../scratchpad/terminate_timing.c`, compiled twice
against `process_unix.c` plus each platform file directly, the pattern
`linux_process_test` already uses.

## 2. The implementation

New `libpromises/process_darwin.c`, modelled on `process_freebsd.c` (same
`ProcessStat` struct, same two-function shape, same `sysctl` approach), with
one Darwin-specific correction:

```c
    if (sysctl(mib, sizeof(mib)/sizeof(mib[0]), &psinfo, &len, NULL, 0) != 0)
    {
        return false;
    }

    /* Unlike other BSDs, KERN_PROC_PID on Darwin reports a pid that does not
     * exist by succeeding and setting the returned length to zero, rather than
     * by failing with ESRCH. Without this check we would read a stale or
     * uninitialised kinfo_proc and report a dead process as running. */
    if (len == 0)
    {
        return false;
    }
```

Measured behaviour of `sysctl(CTL_KERN, KERN_PROC, KERN_PROC_PID, pid)` on
macOS 15, unprivileged (uid 501):

| pid | rc | errno | len | `p_stat` |
|---|---|---|---|---|
| self | 0 | 0 | 648 | 2 `SRUN` |
| 1 (launchd, **root-owned**) | 0 | 0 | 648 | 2 `SRUN` |
| child, SIGSTOP'd | 0 | 0 | 648 | 4 `SSTOP` |
| child, killed, **unreaped** | 0 | 0 | 648 | 5 `SZOMB` |
| child, killed, reaped | 0 | 0 | **0** | — |
| 99998 (nonexistent) | 0 | 0 | **0** | — |

So: state and start time are both available unprivileged, including for other
users' processes; `SSTOP` and `SZOMB` are both reported; and **a nonexistent
pid is signalled by `len == 0`, not by a failure return**. Transcribing the
FreeBSD `if (sysctl(...) == 0)` test alone would take the success branch on a
zeroed `kinfo_proc`, giving `p_stat == 0`, which falls to `default:` → `'X'` →
`PROCESS_STATE_RUNNING`. A dead process would read as running forever, i.e.
strictly worse than the stub it replaces.

Start time is `psinfo.kp_proc.p_starttime.tv_sec` (`struct timeval`), stable
across the child's state changes in the probe above.

### API rejected

`proc_pidinfo(pid, PROC_PIDTBSDINFO, ...)` from `<libproc.h>`, same probes:

| pid | result |
|---|---|
| self | ok, `status=2`, `start=…` |
| 1 (root-owned) | **EPERM**, "Operation not permitted" |
| child, SIGSTOP'd | ok, `status=4` |
| child, killed, **unreaped** | **ESRCH**, "No such process" |
| 99998 | ESRCH |

Disqualified twice over: it cannot see other users' processes unprivileged
(worse than the stub, whose `kill(pid, 0)` at least separates `EPERM` from
`ESRCH`), and it reports an unreaped zombie as nonexistent, so it *cannot*
implement `PROCESS_STATE_ZOMBIE` — half of what the ticket asks for.

### Build wiring

```
if MACOSX
libpromises_la_SOURCES += \
	process_darwin.c
endif
```

plus `if !MACOSX` added to the stub's existing guard chain. `MACOSX` is
already defined unconditionally at `m4/cf3_platforms.m4:33`
(`echo ${target_os} | grep -q darwin`), so no `configure.ac` change is needed
— unlike `FREEBSD`, which is `AM_CONDITIONAL`'d inside a `case` branch.
Verified in the generated `libpromises/Makefile`: `am__objects_7 =
process_darwin.lo`, with `process_unix_stub.lo` commented out.

### Tests

`tests/unit/Makefile.am:184-189` XFAIL'd `process_test` wholesale on macOS;
that line is removed. No `darwin_process_test.c` was added — the
`linux_process_test` / `aix_process_test` / `solaris_process_test` pattern
interposes `open`/`read` to feed synthetic `/proc`-style *text*, and Darwin has
no parsing to test; faking `sysctl()` would only test our own `switch` against
a struct we filled ourselves. FreeBSD likewise has no per-platform test.

Discrimination, by rebuilding the library both ways (full `make` in
`libpromises/` plus a forced relink — a partial rebuild leaves the archive
holding the old platform object and silently fakes a pass):

| | `process_test` |
|---|---|
| stub | **4 FAIL, exit 1** |
| `process_darwin.c` | **0 FAIL, exit 0** |

The four stub failures are exactly the ticket's three claims:

```
FAIL: newproc_starttime == PROCESS_START_TIME_UNKNOWN [0 == 0] (process_test.c:91)
FAIL: newproc_starttime >= THIS_STARTTIME + 1 is FALSE  (process_test.c:92)
FAIL: state != PROCESS_STATE_STOPPED [0 != 1]           (process_test.c:149)
FAIL: state != PROCESS_STATE_ZOMBIE  [0 != 2]           (process_test.c:216)
```

Full `make check` in `tests/unit` with the patch: **66 PASS, 3 XFAIL, 1 SKIP,
0 FAIL, 0 XPASS**, `PASS: process_test`. Baseline was 65 PASS / 4 XFAIL. The
remaining macOS XFAILs (`set_domainname_test`, `mon_processes_test`,
`rlist_test`) are untouched and still fail as expected.

## Questions

**Q1.** Is the `len == 0` check correct *and sufficient* as the
does-not-exist signal on Darwin? Specifically: is there a pid for which
`sysctl` succeeds with `len == sizeof(kinfo_proc)` but the contents are not a
live process, or one where it fails with an errno I should be distinguishing
(`EPERM`? `ENOMEM`?) rather than collapsing to `DOES_NOT_EXIST`? Collapsing
every failure to `DOES_NOT_EXIST` is what `process_freebsd.c` does, but on the
stub an `EPERM` would have read as "exists", so this is a behaviour change on
an error path — is it the right one?

**Q2.** `p_stat` / `p_starttime` come from `struct extern_proc` inside
`kinfo_proc`. Apple has been marking parts of that structure legacy for years.
Is there a macOS version in CFEngine's support range where `KERN_PROC_PID`
returns a differently-laid-out or truncated `kinfo_proc`, and would the
`len == 0` test still hold there? I verified one machine (macOS 15, arm64,
`sizeof(struct kinfo_proc) == 648`) — that is a single data point and I am
treating it as such.

**Q3.** The `SIDL` case is mapped to `'R'` → `RUNNING`, copied from
`process_freebsd.c`. A process being created is arguably not yet running.
Does that matter to any caller? I claim not — `ProcessWaitUntilExited()` just
keeps polling — but check `processes_select.c` and the `locks.c:630` path.

**Q4.** Build wiring. Does adding `if !MACOSX` to the stub's guard chain break
any platform that is *both* macOS and one of the other five (impossible, I
think), or any cross-compilation case where `target_os` is darwin but the
`sysctl` layout is the host's? Note `MACOSX` and `XNU` are separate
conditionals defined identically at `m4/cf3_platforms.m4:33,41` — is `MACOSX`
the right one to key on, or does upstream mean `XNU` for kernel-interface
code?

**Q5.** Removing `process_test` from `XFAIL_TESTS` makes macOS CI fail loudly
if this regresses, which is the point — but it also means any *pre-existing*
flake in `process_test` now breaks the macOS build. The test forks real
children, uses `SIGSTOP`/`SIGCONT`, and sleeps 2 s. Is it stable enough to be
promoted out of XFAIL, or should it stay XFAIL with the improvement noted?
I ran it repeatedly without a flake, but on one machine only.

**Q6.** Is `GetProcessStartTime()` returning `tv_sec` sufficient resolution
for `SafeKill()`'s comparison? Linux returns jiffies-derived seconds and
FreeBSD returns `ki_start.tv_sec`, so this matches — but on a fast machine two
processes recycling the same pid inside one second would compare equal. Is
that a real concern, and is it any worse than the existing platforms?

**Q7.** Anything in the commit message that overstates the case? In
particular the "~7.0 s → tens of ms" figure: I attribute the difference to
zombie visibility, while acknowledging the patched path also takes the
`SafeKill()` route. Is that attribution sound, or should the message be
narrower?

## Trap control

Answer honestly and show your work; I would rather have a "did not verify"
than a confident guess.

- Which of the file/line references above did you actually open, and which did
  you take on trust?
- Did you build anything, or run any of the probes? If you did not, say so —
  several of the claims here are empirical and I want to know which ones you
  are accepting rather than checking.
- Name at least one thing in this brief you think is wrong, weakly supported,
  or overstated. If you genuinely find nothing, say that explicitly rather
  than inventing something.
