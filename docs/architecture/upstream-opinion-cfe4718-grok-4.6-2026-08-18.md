# Review of CFE-4718 (`process_darwin.c`) — grok-4.6

**Patch:** `70caf5e5f` on `fix/process-darwin` in `/Users/djbclark/src/core-darwin`,
based on upstream `a0bca6aaf`.
**Reviewer machine:** macOS 26.6.1 (Darwin 25.6.0), arm64, uid 501.
**Verdict:** SHIP WITH CHANGES — the implementation is the right approach
and empirically correct; the commit message overclaims in two places a
maintainer will notice.

This is not a rubber stamp of the brief, and it is not a rubber stamp of
the sibling Gemini review that already SHIPed this with no required
changes. I opened the sources, compiled the new file under the CI warning
set, force-relinked `libpromises.la`, ran `process_test` ten times, ran
`make -C tests/unit check`, and wrote my own sysctl / `proc_pidinfo` /
`GracefulTerminate` probes. Several of the brief's numbers are
host-specific; one of its "fails closed" implications (repeated by
Gemini) is wrong.

---

## Q1. Is `len == 0` correct and sufficient? Is collapsing every
`sysctl` failure to `DOES_NOT_EXIST` the right error path?

**Verdict:** Yes to both, on current Darwin. Sufficient for "does this
pid exist?", not a general defence against a kernel that starts returning
partial structs. The EPERM behaviour change vs the stub is the right
one, and in practice it does not fire.

**Verified (opened + probed), not taken from the brief.**

`GetProcessStat()` does this (`libpromises/process_darwin.c:44-56`):

```c
    if (sysctl(mib, sizeof(mib)/sizeof(mib[0]), &psinfo, &len, NULL, 0) != 0)
    {
        return false;
    }
    if (len == 0)
    {
        return false;
    }
```

False becomes `PROCESS_START_TIME_UNKNOWN` / `PROCESS_STATE_DOES_NOT_EXIST`
(`process_darwin.c:89-92`, `110-113`).

Probe on this machine (`/tmp/cfe4718-probe.c`, uid 501):

| pid | `sysctl` rc | errno | out `len` | notes |
|---|---|---|---|---|
| self | 0 | 0 | 648 | `p_stat=SRUN`, real start time |
| 1 (launchd, root) | 0 | 0 | 648 | `p_stat=SRUN`, real start time |
| child, running | 0 | 0 | 648 | `p_stat=SRUN` |
| child, SIGSTOP | 0 | 0 | 648 | `p_stat=SSTOP` |
| child, killed, unreaped | 0 | 0 | 648 | `p_stat=SZOMB`; `kill(pid,0)` still succeeds |
| child, reaped | 0 | 0 | **0** | buffer poison (`0xAB`) untouched |
| 99998 / `-1` / `INT_MAX` | 0 | 0 | **0** | same, poison untouched |
| pid 0 (kernel_task) | 0 | 0 | 648 | live process, `p_stat=SRUN` |

So: a missing pid is signalled by success plus `len == 0`, not by
`ESRCH`. Without the length check the code would read an unwritten
`kinfo_proc`. I poisoned the buffer with `0xAB`; after a zero-length
success the poison was intact. `p_stat` of uninitialised memory is not
guaranteed to be 0 and therefore not guaranteed to hit `default:` →
`'X'` → `PROCESS_STATE_RUNNING` (`process_darwin.c:75-77`, `106-107`).
The brief's "would report a dead process as running" is the likely
case, not the only case. The comment at `process_darwin.c:49-52` is
still the right justification.

Is `len == 0` *sufficient* as a "the bytes are a live `kinfo_proc`"
check? On this kernel, yes, because Darwin does not return success
with a partial fill. Buffer-size matrix against self:

| in `len` | result |
|---|---|
| 0, `oldp=NULL` | rc=0, out `len`=3888 (padded size estimate, 6×648) |
| 1 … 647 | rc=-1, **`ENOMEM`**, out `len`=0 (does *not* report the needed size) |
| 648, 649, 1024 | rc=0, out `len`=648 |

There is no observed `0 < len < sizeof(kinfo_proc)` success path. A
`len < sizeof(psinfo)` check would be cheaper insurance, not a fix for
a bug I can demonstrate. It also does not help the ABI-growth case:
if Apple ever grows `kinfo_proc` by one byte, a binary compiled against
today's 648-byte header gets `ENOMEM` on every pid and never reaches
the length check.

**EPERM / collapsing failures.** I sampled `KERN_PROC_PID` for 30
other-uid processes: 30/30 succeeded, 0 `EPERM`, 0 `ENOMEM`.
`proc_pidinfo(PROC_PIDTBSDINFO)` on the same pids is `EPERM`.
`kill(pid, 0)` on them is `EPERM` (exists, not signalable). So the
stub's "EPERM means exists" path is not a path `sysctl` takes.

If `sysctl` *does* fail, collapsing to `DOES_NOT_EXIST` matches every
real platform file, not just FreeBSD:

- Linux maps `EACCES` to false (`process_linux.c:61-64`).
- Solaris documents the same choice for `EPERM` on `/proc/PID/status`
  (`process_solaris.c:162-166`).
- AIX treats a failed/`getprocs64` miss as unknown / does-not-exist
  (`process_aix.c:44-50`, `61-64`, `84-86`).

That *is* a behaviour change vs the stub (`process_unix_stub.c:44-51`),
and it is the right one: if you cannot inspect the process you cannot
run `SafeKill`'s identity check, and pretending it is `RUNNING` would
send `SIGSTOP` at a pid you cannot confirm.

**Residual, not a blocker.** `ProcessWaitUntilExited()` treats
`PROCESS_STATE_DOES_NOT_EXIST` as success (`process_unix.c:96-97`).
`ENOMEM` after a hypothetical `kinfo_proc` growth would therefore make
every wait return immediately ("already gone") while
`GetProcessStartTime()` returns 0. That is **not** "fails closed".
`SafeKill()` would refuse to signal (0 ≠ stored start time,
`process_unix.c:175-178`), and `KillLockHolder()` would then treat
`ESRCH` as "already killed" (`locks.c:639-644`). Mixed, and bad, and
also the same class of problem every `kinfo_proc` consumer has had
for twenty years. I would not block a platform file on Apple growing
a frozen compat struct.

---

## Q2. Is `kinfo_proc` / `p_stat` / `p_starttime` stable across
CFEngine's macOS range?

**Verdict:** Stable across the SDKs and kernels I can actually check
(macOS 15.4 headers through macOS 26.6.1 runtime). Still one
architecture (arm64). The brief was right to treat its macOS 15
measurement as a single data point; I added a second point, not a
matrix.

**Verified in headers and at runtime; support-range claim is
documented, not exhaustively tested.**

`p_starttime` is a union overlay on the run-queue pointers
(`sys/proc.h:91-101`):

```c
struct extern_proc {
    union {
        struct { struct proc *__p_forw; struct proc *__p_back; } p_st1;
        struct timeval __p_starttime;
    } p_un;
#define p_starttime p_un.__p_starttime
    ...
    char p_stat;
    pid_t p_pid;
```

Offsets on this SDK: `p_starttime` at 0, `p_stat` at 36, `p_pid` at 40.
`sizeof(struct kinfo_proc)` is **648** on every SDK installed here
(MacOSX15.sdk, MacOSX15.4.sdk, MacOSX26.sdk, MacOSX26.5.sdk) and at
runtime on Darwin 25.6.0. That matches the brief's macOS 15 number
exactly. Status values are still `SIDL=1 … SZOMB=5` (`sys/proc.h:148-152`);
there is no `SWAIT`/`SLOCK`.

A `KERN_PROC_ALL` dump of 758 processes: every `p_starttime.tv_sec`
nonzero, including 220 other-uid processes; no unknown `p_stat` values.
`KERN_PROC_PID` start time of a child was identical across running /
stopped / zombie. The union is being filled as a `timeval` for
userland, not left as queue pointers.

CFEngine's *official* supported-client table
(https://docs.cfengine.com/docs/3.24/release-notes/supported-platforms/)
does not list macOS at all. What this repo actually promises is the
macOS unit-test workflow (`.github/workflows/macos_unit_tests.yml`),
which builds with `MACOSX_DEPLOYMENT_TARGET=15.4`. I did not boot a
10.15 or 12 box. I would be surprised if `KERN_PROC_PID` + this
`kinfo_proc` layout were different there — it has been the `ps`
compat ABI for decades — but that is an expectation, not a
measurement.

Apple has been steering new code at `proc_pidinfo`. That API is still
the wrong one here (see Q1 table and the brief's rejection, which I
reproduced: EPERM on pid 1 and other-uid, ESRCH on an unreaped
zombie). `KERN_PROC` is the unprivileged interface `ps` uses. Using
it is correct, even if the header comments call un-locked sysctls
"legacy".

---

## Q3. Does mapping `SIDL` → `RUNNING` matter to any caller?

**Verdict:** No. Mapping it to `RUNNING` is the only safe choice among
the four `ProcessState` values. `processes_select.c` never sees it.

**Verified by opening the callers, not by catching a process in
`SIDL`.**

`SIDL` is "Process being created by fork" (`sys/proc.h:148`). The
Darwin file copies FreeBSD (`process_darwin.c:62-65`,
`process_freebsd.c:52-55`): `SIDL` and `SRUN` both become `'R'`, and
anything that is not `'T'`/`'Z'` is `PROCESS_STATE_RUNNING`
(`process_darwin.c:100-107`).

Callers of `GetProcessState()`:

| Caller | SIDL-as-RUNNING effect |
|---|---|
| `ProcessWaitUntilExited()` (`process_unix.c:94-95`) | keeps polling. Correct: the child is not gone. Mapping to `DOES_NOT_EXIST` would make `GracefulTerminate()` return success mid-fork. |
| `ProcessWaitUntilStopped()` (`process_unix.c:52-53`) | keeps polling. Correct: it is not stopped. Mapping to `STOPPED` would make `SafeKill()` believe `SIGSTOP` had taken and signal a process that is still coming up. |
| `process_test.c` | never looks at a forking child. |

`processes_select.c` does not call `GetProcessState` or mention
`SIDL`. Darwin process listing is `/bin/ps auxw`
(`systype.c:84,118`; `processes_select.c:99,1685-1687`). The
`processes:` promise type is a different path. `locks.c:630` is
`GracefulTerminate()` of a lock holder that stored
`GetProcessStartTime(getpid())` at acquire (`locks.c:193`). A lock
holder in `SIDL` is not a realistic state.

I did not observe `SIDL` in the 758-process snapshot (histogram:
758 `SRUN`, 0 of everything else, including `SSLEEP`). On modern
XNU, sleep is at thread level; `SSLEEP` may simply not appear.
The `SSLEEP` case in `process_darwin.c:69-71` is then dead and
harmless.

---

## Q4. Does `if !MACOSX` on the stub break anything? `MACOSX` vs `XNU`?

**Verdict:** Wiring is correct. `MACOSX` is the right conditional.
No dual-match platform, no special cross-compile footgun beyond what
every other `process_*.c` already has.

**Verified in `Makefile.am`, generated `Makefile`, and
`m4/cf3_platforms.m4`.**

```
if MACOSX
libpromises_la_SOURCES += \
	process_darwin.c
endif
```

plus `if !MACOSX` inside the existing `!LINUX !AIX !HPUX !SOLARIS
!FREEBSD` nest (`libpromises/Makefile.am:209-227`). Generated
`libpromises/Makefile` has `am__objects_7 = process_darwin.lo` and
`process_unix_stub.lo` commented out. `target_os` here is
`darwin25.6.0`; `MACOSX_TRUE` is set.

`MACOSX` and `XNU` are defined identically
(`m4/cf3_platforms.m4:33,41`, both `grep -q darwin`). The m4 comment
says to use the kernel conditional when the code depends on a kernel
feature. `KERN_PROC` is a kernel feature. Even so, every sibling
process file is keyed on the OS name (`LINUX`, `FREEBSD`, `AIX`, …),
and `XNU` is used once in this tree, to skip function-interposition
load tests (`tests/load/Makefile.am:33`). Keying this file on
`MACOSX` matches `process_freebsd.c` / `if FREEBSD`. If someone later
splits `MACOSX` from `XNU`, they have bigger problems than this
Makefile.

A platform cannot be both Darwin and Linux/`freebsd`/`aix`/`hpux`/`sunos`
under these greps. Cross-compiling *to* Darwin uses the *target* SDK's
`kinfo_proc`; that is the same rule as `process_linux.c` when
cross-compiling to Linux. `Makefile.in` is not in git; CI runs
`./autogen.sh` (`.github/workflows/macos_unit_tests.yml:19-21`). Not
committing it is correct.

`CONTRIBUTING.md:774` says "OS X: Use `__APPLE__`. Don't use `DARWIN`"
for C `#ifdef`s. This file has no such ifdef; the Makefile
conditional is the established pattern.

---

## Q5. Is `process_test` stable enough to leave the XFAIL list?

**Verdict:** It must come off the list, and I have no evidence it is
flaky. Leaving it XFAIL after this patch would fail CI with XPASS.

**Verified by forced rebuild + 10 runs + full `make check`. Still
one machine (plus the author's).**

Automake treats an unexpected pass of an `XFAIL_TESTS` entry as
XPASS, and `make check` fails. Once `process_darwin.c` is linked,
`process_test` passes, so `tests/unit/Makefile.am:184-187` *has* to
drop it. This is not a flake-risk judgement; it is required for a
green macOS job.

I force-relinked (touched `process_darwin.c`, `make -C libpromises
libpromises.la`, deleted `tests/unit/.libs/process_test`, relinked)
because a stale archive can keep the stub. `otool` of the dylib
shows `_GetProcessStartTime` calling `_sysctl`, not the stub's
`Log(...)` string. Then:

- `./process_test` × 10: 10 PASS, 0 FAIL.
- `make -C tests/unit check`: "All 69 tests behaved as expected
  (3 expected failures)", 1 SKIP (`tar_portability_test.sh`).
  `PASS: process_test`. Remaining XFAILs:
  `set_domainname_test`, `mon_processes_test`, `rlist_test`.

The test forks real children, `SIGSTOP`/`SIGCONT`, `sleep(2)`, and
asserts `PROCESS_STATE_ZOMBIE` with no retry
(`process_test.c:212-216`). That last assertion is the only one I
would watch under CI load. It did not flicker here. Linux and
FreeBSD already run this file as a real test; the XFAIL existed
because the stub failed it (`process_test.c:91-92,149,216`), not
because Darwin scheduling made it racy.

I did **not** rebuild the library with the stub and re-run
`process_test` to reproduce the brief's four FAIL lines. I opened
`process_unix_stub.c:29-51` and `process_test.c:91-92,149,216`; those
four assertions cannot pass on the stub. I am accepting the exact
FAIL text from the brief.

---

## Q6. Is `tv_sec` enough for `SafeKill()`?

**Verdict:** Yes. Same resolution as every other Unix implementation,
and the public API cannot carry more.

**Verified in the three platform files and `process_lib.h`.**

`GetProcessStartTime()` returns `time_t`
(`process_lib.h:43`). `PROCESS_START_TIME_UNKNOWN` is `((time_t) 0)`
(`process_lib.h:34`). Darwin uses `kp_proc.p_starttime.tv_sec`
(`process_darwin.c:58`). FreeBSD uses `ki_start.tv_sec`
(`process_freebsd.c:48`). Linux takes `/proc/pid/stat` starttime in
clock ticks and **divides** by `sysconf(_SC_CLK_TCK)`
(`process_linux.c:123`) — so the brief's "Linux returns
jiffies-derived seconds" is slightly loose: the kernel gives ticks,
CFEngine truncates to seconds. Same 1-second bucket either way.

Two processes recycling the same pid inside one second would compare
equal. `SafeKill()`'s SIGSTOP / re-read (`process_unix.c:181-209`)
does not help if the replacement has the same `tv_sec`. That is the
existing contract. Darwin actually has `tv_usec` and, better,
`proc_uniqueid` / pidversion; using them would mean changing
`time_t GetProcessStartTime()` and the lock DB. Out of scope, and
not worse than Linux or FreeBSD.

A live process with `tv_sec == 0` would be treated as unknown
(`process_unix.c:229-232`). None of 758 processes on this host had
that, including pid 0 / kernel_task.

---

## Q7. Does the commit message overstate, especially "~7.0 s → tens
of ms"?

**Verdict:** The *attribution* is sound. The *number* is over-precise,
and the Changelog line will be read as a `processes:` fix.

**Verified by timing both paths myself; commit text from `git show`.**

`GracefulTerminate()` (`process_unix.c:241-282`):

1. `Kill(SIGINT)` then `ProcessWaitUntilExited()`.
2. If still alive, `Kill(SIGTERM)` then wait again.
3. Then `SIGKILL` and return.

On the stub, `GetProcessState()` never returns `ZOMBIE`
(`process_unix_stub.c:44-51`), and `kill(pid, 0)` succeeds on a
zombie (probed). Both waits therefore run to `STOP_WAIT_TIMEOUT`
(`process_unix.c:135`, `261`, `271`). The patched file returns
`PROCESS_STATE_ZOMBIE` and the first wait returns immediately
(`process_unix.c:98-102`). That is the seconds.

I compiled `process_unix.c` + each platform file against
`libutils.a` (the `linux_process_test` pattern) and timed
`GracefulTerminate()` of an unreaped `/bin/sleep` child, three
runs, macOS 26.6.1:

| build | run 1 | run 2 | run 3 | start time passed in |
|---|---|---|---|---|
| stub | 12658 ms | 12071 ms | 12738 ms | 0 (`UNKNOWN`) |
| `process_darwin.c` | 48.9 ms | 86.3 ms | 78.8 ms | real `tv_sec` |

100 × 10 ms `nanosleep()` on this host cost **7675 ms** (76.7 ms/iter),
not the brief's ~35 ms. One wait is ~100 iterations; two waits plus
slop is ~12 s, which is what I measured. The brief's ~7 s is the
same mechanism on a machine whose `nanosleep` is cheaper. Putting
"~7.0 s" in a commit that will be read on other Macs overstates
precision. "Several seconds" is what the code guarantees.

The patched path *does* more work (`SafeKill`'s SIGSTOP/SIGCONT,
`process_unix.c:181-224`) and still wins by two orders of magnitude.
The commit body already says that. Good.

What I would change before a maintainer sees it:

- **Changelog** (`Changelog:` line of `70caf5e5f`): "Fixed cf-agent on
  macOS being unable to detect stopped or exited processes…" is what
  a user will take as the `processes:` promise type. That type uses
  `ps` (`processes_select.c:1685-1687`) and already reports `T`/`Z`.
  This patch does not touch it. `CONTRIBUTING.md:218-220` wants
  user-facing impact, not implementation. The PID-recycling clause
  is real for callers that pass a stored start time (`locks.c:193,630`,
  `mod_custom.c:504-510`) and is not real for `timeout.c:45`, which
  still calls `GracefulTerminate(ALARM_PID, PROCESS_START_TIME_UNKNOWN)`
  after this patch. The wait-budget clause applies to every
  `GracefulTerminate()` caller, including that one.
- **Understated user impact**, while we are here:
  `mod_custom.c:504-510` (since `4f8837846`, 2023) *refuses to load
  a custom promise module* if `GetProcessStartTime()` returns
  unknown. On the stub that is unconditional. This patch makes
  custom modules start on macOS. The brief and the commit do not
  mention it. I verified the code path, not a live module.

---

## Trap control

### Files I opened

Opened and read, not taken on trust:

- `docs/architecture/UPSTREAM-CFE4718-REVIEW-BRIEF.md`
- `git -C /Users/djbclark/src/core-darwin show 70caf5e5f` (full diff
  and commit message)
- `libpromises/process_darwin.c` (all 114 lines)
- `libpromises/process_freebsd.c`, `process_unix_stub.c`,
  `process_linux.c`, `process_solaris.c`, `process_hpux.c`,
  `process_aix.c`
- `libpromises/process_unix.c` (all of `SafeKill` / `Kill` /
  `GracefulTerminate` / both wait loops)
- `libpromises/process_lib.h`, `process_unix_priv.h`
- `libpromises/Makefile.am:180-227` and the generated
  `libpromises/Makefile` object lists
- `libpromises/locks.c:189-196,590-654`
- `libpromises/timeout.c:38-46`
- `libpromises/mod_custom.c:498-510`
- `libpromises/processes_select.c` (header, column algorithm,
  `GetProcessOptions`, `LoadProcessTable`); `libpromises/systype.c:84,118`
- `m4/cf3_platforms.m4:25-41`
- `tests/unit/Makefile.am:182-187,323` and
  `tests/unit/process_test.c` (all of it)
- `tests/load/Makefile.am:31-33`
- `CONTRIBUTING.md` (PR/commit/changelog/platform-macro sections)
- `INSTALL` (supported-OS paragraph)
- `.github/workflows/macos_unit_tests.yml`
- SDK headers: `sys/proc.h`, `sys/sysctl.h`, `sys/proc_info.h`
- https://github.com/djbclark/core/issues/12
- https://docs.cfengine.com/docs/3.24/release-notes/supported-platforms/

I also opened the sibling
`docs/architecture/upstream-opinion-cfe4718-gemini-3.1-pro-2026-08-18.md`
after I had the sources and the first half of the probe plan. Where
we overlap I re-checked rather than adopting its conclusions. I
disagree with its "ENOMEM fails closed" and with SHIP / no required
changes.

### What I built and ran

- `cc -Werror -Wall -Wextra -Wno-sign-compare` of
  `libpromises/process_darwin.c` with the project's include path:
  clean.
- `/tmp/cfe4718-probe.c`: `KERN_PROC_PID` table, buffer-size matrix,
  `proc_pidinfo` comparison, `KERN_PROC_ALL` census, other-uid
  sample, `nanosleep` slop.
- `/tmp/term-darwin` and `/tmp/term-stub`: `process_unix.c` plus each
  platform file, linked against `libntech/libutils/.libs/libutils.a`.
- Forced `libpromises.la` relink + `process_test` × 10.
- `make -C tests/unit check` after that relink.

I did **not**:

- Rebuild `libpromises` with the stub and re-run `process_test` (the
  four FAIL lines are accepted from the brief + stub source).
- Run a custom promise module to watch `mod_custom.c:504-510` die on
  the stub.
- Boot an older macOS. SDKs for 15.4 and 26.5 only.
- Open Jira CFE-4718 (private).
- Find `fill_kinfo_proc` in the XNU drop I fetched (`kern_proc.c`
  does not contain the sysctl copy-out; I relied on the runtime
  probe for `p_starttime` being a real `timeval`).

### What in the brief is wrong, weak, or overstated

1. **"~7.0 s"** is one host's `nanosleep` slop, not a property of the
   stub. I measured ~12.5 s on macOS 26.6.1. The mechanism is right;
   the figure does not belong in the commit as if it were portable.
2. **"len == 0 is sufficient"** is sufficient *for Darwin as it
   behaves today* (I never saw a partial success). It is not a
   defence against a grown `kinfo_proc` — that path is `ENOMEM`, and
   that path is **not** fail-closed for `ProcessWaitUntilExited()`.
   The brief (and Gemini) overclaim sufficiency / closed-ness.
3. **"Unable to detect stopped or exited processes"** in the
   Changelog will be read as `processes:`. That type already can,
   via `ps`.
4. **"Linux returns jiffies-derived seconds"** — the kernel returns
   ticks; `process_linux.c:123` divides.
5. **Custom promise modules** have been unloadable on macOS since
   2023 (`mod_custom.c:504-510`). That is a larger user-visible
   bug than a 7-second wait, and the brief does not mention it.
6. **"Every `GracefulTerminate()` caller" loses the PID-recycling
   guard** is true *before* the patch. After it, `timeout.c:45`
   still passes `PROCESS_START_TIME_UNKNOWN`. The wait-budget fix
   still applies there.
7. **macOS 15 is not "the" Darwin.** I am on 26.6.1 and the
   behaviour matched. Good for the author, but the brief should
   keep saying "one machine" (it does, for Q2; it forgets for the
   timing table).

I do **not** think the approach is wrong. `sysctl KERN_PROC_PID` is
the unprivileged API that can see other users' processes *and*
zombies. `proc_pidinfo` cannot. Cloning `process_freebsd.c` and
adding the Darwin length check is the smallest correct file.

---

## REQUIRED CHANGES

Code: none.

Commit message, before the PR:

1. **Changelog line of `70caf5e5f`.** Replace

   > Fixed cf-agent on macOS being unable to detect stopped or exited
   > processes, which disabled the PID-recycling safety check when
   > signalling and made process termination take seconds longer than
   > necessary

   with something a `CHANGELOG.md` reader will not confuse with
   `processes:`, for example:

   > Fixed macOS process start-time and stopped/zombie lookup used
   > when signalling, so recycled PIDs are not signalled and
   > termination does not wait several extra seconds after a child
   > has already exited

   Optionally add that custom promise modules can start again
   (`mod_custom.c:504-510`).

2. **Commit body, the "~7.0 s" sentence.** Say "several seconds"
   (or give the range and the host). Do not publish 7.0 as if it
   were a constant. Keep the attribution to zombie visibility; that
   part is right.

---

## OPTIONAL

- `process_darwin.c:53`: `if (len < sizeof(psinfo))` instead of
  `len == 0`. Zero-cost, does not fix ABI growth, does close a
  hole I could not demonstrate.
- Zero `psinfo` before `sysctl`, or check
  `psinfo.kp_proc.p_pid == pid` after success (AIX does the pid
  check in `process_aix.c:50` because `getprocs64` can return the
  wrong process; Darwin `KERN_PROC_PID` did not, in my sample).
- Retry `EINTR` on `sysctl`. FreeBSD does not. Low value.
- `SSLEEP` appears unused on this kernel. Leave the case; it
  matches FreeBSD and costs nothing.
- Copyright year is 2024, copied from the sibling files. Leave it;
  Northern.tech bumps these in a sweep.

---

## VERDICT

**SHIP WITH CHANGES** — the Darwin file and the Makefile wiring are
correct and should go upstream; rewrite the Changelog line and drop
the false-precision "7.0 s" before a maintainer has to ask.
