# Upstream second opinion — CFE-4735, cf_popen*() fdopen()-failure ALARM_PID leak

**Reviewer:** grok
**Date:** 2026-08-18
**Subject:** `djbclark/core` worktree `/Users/djbclark/src/core-alarmleak`, branch `fix/exec-timeout-alarm-leak`, commit `89379323d` (parent `8f4ebedbd`, CFE-4727's tip)
**Ticket:** CFE-4735

This review assumes the fix is wrong and tries to show it. It is not a paraphrase of the author's notes. CFE-4727's three 2026-08-18 reviews were read first, as the brief required, and are treated as settled on `ClearAlarmedPid()`'s contract (wait, then compare-and-clear under `pthread_sigmask`). This commit is judged only as a delta on that helper.

---

## Verdict

**Offer upstream.** The eight insertions pass the pid and the order, `RepairExec()`'s new `ClearTimeOut()` is gated on the same condition that armed the alarm, and I independently discriminated both new behaviours without touching the worktree.

I disagree with the author on the test claim, not on the C. There *is* a portable discriminator for `RepairExec()`'s leftover-alarm half (`RLIMIT_NOFILE` so `pipe()` fails, then a later child published into `ALARM_PID`), and there *is* a Darwin-only discriminator for the eight `ClearAlarmedPid()` sites (`DYLD_INSERT_LIBRARIES` failing `fdopen()`). I ran both. The first is what I would actually add to `timeout_test`. I would not hold the offer for it.

Do not fold the remaining `RepairExec()` armed-timeout leaks (`powershell` on Unix, `CfReadLine` error) or `history.c` / `nfs.c` into this SHA. They are the already-filed B-15 family. This ticket is the one path that combined a leaked alarm with a *reaped* pid.

---

## What I actually did

Read, not just the diff:

- CFE-4727 panel: `docs/architecture/upstream-opinion-cfe4727-{gemini31pro,grok,fabledeep}-2026-08-18.md` (fable-deep's attack 5 is the finding this commit implements)
- `libpromises/pipes_unix.c`: `GenericCreatePipeAndFork()`, `CreatePipeAndFork()`, all four `cf_popen*` parents and both wrappers, `cf_popen_full_duplex()`, `cf_pwait()`, `ClearAlarmedPid()`, both closers, `cf_pclose_nowait()`, `ChildrenFDSet()`
- `libpromises/pipes.c` `PipeTypeIsOk()` and `cf_popen_full_duplex_streams()` (the other `fdopen` after a successful fork)
- `libpromises/timeout.c` / `timeout.h`: `SetTimeOut()`, `ClearTimeOut()`, `TimeOut()`
- `cf-agent/verify_exec.c` `RepairExec()` in full, including the pre-existing `ClearTimeOut()` at the bottom and every early return after line 308
- `libpromises/mod_exec.c` (`exec_timeout` syntax `"1,3600"`), `attributes.c` `GetExecContainConstraints()`, `policy.c` `PromiseGetConstraintAsInt()`, `cf3.defs.h` `CF_NOINT`
- `libpromises/process_unix.c` `Kill()` / `SafeKill()` / `GracefulTerminate()`
- `cf-monitord/history.c` and `cf-agent/nfs.c` (the other `SetTimeOut` + `cf_popen == NULL` siblings)
- `cf-serverd/server.c` / `server_common.c` `DoExec2()`, `cf-execd/cf-execd.c` `LocalExecThread()` (threaded `cf_popen` without `SetTimeOut`)
- `tests/unit/timeout_test.c`

Grep: every `cf_pwait(` and `fdopen(` in the tree; every `SetTimeOut(`; `pthread_create` under `cf-agent/` (none); `contain.timeout`.

Measured on this host (see Trap control):

- `timeout_test` 7/7 against the already-installed 4735 prefix
- `otool -tV` of this tree's `pipes_unix.o`: the compiler merged the eight source sites into four wait-then-clear tails, one per function, each comparing `ALARM_PID` to the same register `cf_pwait` just took
- Standalone leftover-alarm model of `RepairExec()`'s `pfp == NULL` after `pipe()` failure, both with and without `ClearTimeOut()`
- `RLIMIT_NOFILE` / 20 000 `FILE*`s / `F_DUPFD 2048` probes of the author's "untestable" claim
- Real `cf_popen_sh("/bin/true")` with an interposed `fdopen()` that returns `ENOMEM`, against **both** installed dylibs

Not executed: a rebuild, `make check`, the six `04_exec_timeout/` acceptance tests, a Linux or MinGW build, or any path that actually delivers `SIGALRM` inside `cf-serverd`. I did not revert `pipes_unix.c`.

Did not commit, push, branch, or modify any file in either repo other than this review.

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

Every compile and every probe/unit-test run wrote `echo "RC=$?"` to a distinct file under `/tmp/cfe4735-grok-review/` immediately after the command, with no pipe on that command.

1. **Never read a return code through a pipe.** Done. Distinct stems: `timeout_test.rc`, `cc_*.rc`, `fdopen_construct.rc`, `maxfd.rc`, `repair_{noclear,clear}2.rc`, `real_{4735,4727}_fail.rc`, `cmp_dylib.rc`.

2. **`--prefix` / `make install`.** I did not configure or install. I used the author's already-installed `/Users/djbclark/opt/cfengine-dev-4735` and, for discrimination only, `/Users/djbclark/opt/cfengine-dev-4727`. `cmp` of the in-tree `libpromises/.libs/libpromises.3.dylib` against the 4735 prefix dylib: **identical** (`RC=0`). The 4727 and 4735 prefix dylibs differ. I did not write to `~/opt/cfengine-dev-4727`.

3. **`cf-promises` libtool wrapper.** Unit test was driven through `tests/unit/timeout_test` (the wrapper). That is what `make check` uses. I did not invoke `cf-promises`.

4. **Platform.** This build links `process_unix.c` **and** `process_unix_stub.c` (same as CFE-4727). Claims tagged **measured** (this macOS host) or **reasoned** (Linux / POSIX / unrun paths).

Worktree dirty only with the pre-existing untracked `timeout_test.xml`. I did not create, edit, or delete anything under `/Users/djbclark/src/core-alarmleak`.

---

## 1. The forward declaration and the eight insertions

**Every site passes the `pid` that `CreatePipeAndFork()` returned and that `cf_pwait()` just reaped. The compiler merged the eight source sites into four tails, so a wrong-variable slip in one of a pair is not even representable in this object file.**

`GenericCreatePipeAndFork()` publishes `ALARM_PID = (pid != 0 ? pid : -1)` in the parent after `fork()` succeeds. Each of the four functions:

1. Calls `CreatePipeAndFork()` into a local `pid`.
2. Returns `NULL` immediately on `pid == (pid_t) -1` — **before** any `fdopen`, so these insertions are not reached on pipe/fork failure. `ALARM_PID` is not published on that path (the `ALARM_PID =` store sits after the failed-fork `return`).
3. Sends `pid == 0` into the child branch.
4. In the parent (`pid > 0`), `switch (*type)`: `'r'` closes `pd[1]` and `fdopen`s `pd[0]`; `'w'` closes `pd[0]` and `fdopen`s `pd[1]`.

I read all eight source sites individually:

| # | Function | Direction | `cf_pwait` then `ClearAlarmedPid` | Argument |
|---|---|---|---|---|
| 1 | `cf_popen_select` | `'r'` | 461 then 462 | local `pid` |
| 2 | `cf_popen_select` | `'w'` | 474 then 475 | local `pid` |
| 3 | `cf_popensetuid` | `'r'` | 593 then 594 | local `pid` |
| 4 | `cf_popensetuid` | `'w'` | 606 then 607 | local `pid` |
| 5 | `cf_popen_sh_select` | `'r'` | 677 then 678 | local `pid` |
| 6 | `cf_popen_sh_select` | `'w'` | 689 then 690 | local `pid` |
| 7 | `cf_popen_shsetuid` | `'r'` | 798 then 799 | local `pid` |
| 8 | `cf_popen_shsetuid` | `'w'` | 810 then 811 | local `pid` |

No shadowed `pid`. No `CHILDREN[fd]` lookup (that table is only written on the success path, after `fdopen` returns non-NULL). No `pd[0]`/`pd[1]` mixed up into the wait. `cf_popen()` and `cf_popen_sh()` are one-line wrappers around the `_select` variants; they do not have their own copies.

`PipeTypeIsOk()` rejects anything whose first character is not `'r'` or `'w'` *before* `pipe()`/`fork()`, so a parent cannot reach `fdopen` with a type the `switch` does not handle. RepairExec uses `"r"` or `"rt"`; both take the `'r'` arm.

`otool -tV` of `libpromises/.libs/pipes_unix.o` (**measured**): `ClearAlarmedPid` has no symbol (static, inlined). There are exactly six `mov w8, #0x2000` sites in the file — the SIGALRM mask, one per inlined helper. Four of them sit in the popen parents, two in the closers CFE-4727 already added. In every popen function the `'r'` and `'w'` `fdopen` failures `cbz` to the **same** tail:

```
mov x0, <pid-reg>
bl  cf_pwait
mov w8, #0x2000          ; sigaddset(SIGALRM)
...
mov w0, #0x1             ; SIG_BLOCK
bl  pthread_sigmask
ldr w9, [ALARM_PID]
cmp w9, <pid-reg>        ; same register
b.ne skip
mov w9, #-0x1
str w9, [ALARM_PID]
mov w0, #0x3             ; SIG_SETMASK
bl  pthread_sigmask
```

| Function | pid register through wait **and** compare |
|---|---|
| `cf_popen_select` | `x20` / `w20` |
| `cf_popensetuid` | `x24` / `w24` |
| `cf_popen_sh_select` | `x19` / `w19` |
| `cf_popen_shsetuid` | `x24` / `w24` |

That is the `CreatePipeAndFork()` return, saved before the `switch`. I could not construct a wrong-variable bug that the source has and the object hides: the two directions share a tail.

`cf_pwait`'s return is ignored, same as before this commit. A `-1` from `waitpid` (typically `ECHILD`, already reaped) or from an abnormal `WIFEXITED` still means the pid is not a live child we own. Clearing a matching `ALARM_PID` is the right action either way. A live child whose `waitpid` failed for some other reason is not a case I can name with this `waitpid(pid, &status, 0)` call.

No ninth `cf_pwait` in the tree. `cf_popen_full_duplex()` never `fdopen`s. `cf_popen_full_duplex_streams()` does `fdopen` the raw fds after a successful fork, and on failure it **does not reap** — it returns the `IOData` with a NULL stream and a live child still registered in `ALARM_PID`. Different shape, not this defect, not introduced here.

---

## 2. Ordering

**Wait, then clear, on all four object tails. Reversing it would reopen CFE-4727 on these sites. The author did not reverse it.**

Source: `cf_pwait(pid);` immediately followed by `ClearAlarmedPid(pid);` at all eight sites. Nothing between them except the compiler's inlined helper.

Object: every `mov w8, #0x2000` in a popen parent is the first instruction after the `bl` to `cf_pwait`. The compare-and-store of `ALARM_PID` is after `SIG_BLOCK`, matching CFE-4727.

The residual post-reap window CFE-4727 already accepted is still here: between a successful `waitpid` inside `cf_pwait` and `pthread_sigmask(SIG_BLOCK)` there is `cf_pwait`'s `WIF*` / `Log` and the return. An alarm in that window still sees a reaped pid. Same window, same size class, same mostly-classification leftover (false `TIMEOUT_SIGNALLED` without a recycle; a recycle kill if the number was reused). On the hang-after-`fdopen` path the alarm is consumed *during* the wait, so this window is idle afterwards — same argument as for the closers.

I will not demand that this commit move the block to the first instruction after `waitpid`. CFE-4727 did not, and the panel accepted that.

---

## 3. Clearing an `ALARM_PID` this path should not touch

**The `ALARM_PID == pid` guard is sufficient here the same way it was sufficient for the two closers. I could not construct a same-thread reentrancy that makes the guard fire against a newer registration. Cross-thread overwrite is real in `cf-serverd` / `cf-execd` and is exactly what the guard is for.**

Same-thread, `RepairExec()`:

- `cf-agent` contains **no** `pthread_create` (grep, this session).
- Backgrounded commands `fork()` *before* `SetTimeOut()`. The parent never arms, never hits `pfp == NULL`. The child is a separate address space with its own `ALARM_PID`.
- `TimeOut()` is the only thing that can run asynchronously during `cf_pwait`. It does not call `cf_popen*`. It does not write `ALARM_PID`.
- So when `ClearAlarmedPid(pid)` runs on this path in `cf-agent`, `ALARM_PID` is still the pid `GenericCreatePipeAndFork()` published for *this* call, or `-1` if something else already cleared it. The compare either succeeds (this was ours) or is a no-op.

Cross-thread, `cf-serverd` / `cf-execd`:

- `HandleConnection` → `DoExec2()` → `cf_popen` / `cf_pclose`.
- `LocalExecThread()` → `cf_popen_sh` / `cf_pclose`.
- Those threads do **not** call `SetTimeOut()` (unchanged from CFE-4727). They still run `GenericCreatePipeAndFork()`, which still writes the global `ALARM_PID`, and they now run `ClearAlarmedPid` on `fdopen` failure as well as on close.

Interleaving:

1. Thread A forks, `ALARM_PID = pidA`, `fdopen` fails, blocks in `cf_pwait(pidA)`.
2. Thread B forks, `ALARM_PID = pidB`.
3. Thread A reaps, `ClearAlarmedPid(pidA)`: `ALARM_PID == pidA`? No. Leaves `pidB`. Correct.
4. Recycle: Thread A reaps `pidA`, the kernel reuses that number for Thread B's child, Thread B publishes `ALARM_PID = pidA` (new process, old number), Thread A then `ClearAlarmedPid(pidA)` and wipes B's live registration.

Step 4 is CFE-4727's residual post-reap window, now also present on the `fdopen`-failure path. It is not new, it is not larger than the closer's window in instruction count, and on this path `cf_pwait` can last a long time (see pre-existing hang below), which makes a concurrent `cf_popen` from another thread *more* likely to land in the window. The guard still does the right thing for every case except recycle-of-the-just-reaped-number, which no compare-and-clear of a pid can solve. Same as the closers.

`cf_popensetuid` / `cf_popen_shsetuid` already document "single-threaded code only" because of `safe_chdir` in the child. RepairExec is that caller. The threaded daemons use the non-setuid variants.

I found no path where this commit's clear fires against a *newer* registration of a *different* number. The guard rejects that.

---

## 4. `RepairExec()`'s new `ClearTimeOut()`

**The gate is the same condition that armed the alarm. `pfp == NULL` after a no-timeout promise is a no-op, which is correct. `pfp == NULL` after a timed promise cannot see some other promise's still-live timeout: `SetTimeOut()` already replaced it.**

Arm:

```c
if (a->contain.timeout != CF_NOINT)
{
    SetTimeOut(a->contain.timeout);
}
```

New disarm, same function, same `const Attributes *a`:

```c
if (a->contain.timeout != CF_NOINT)
{
    ClearTimeOut();
}
```

`exec_timeout` is syntax `"1,3600"`. Unset is `PromiseGetConstraintAsInt` → `CF_NOINT` (`-678L`). A policy cannot produce `0` here. The bottom-of-function `ClearTimeOut()` uses the identical test. `history.c` uses `timeout != 0`; that is a different caller with a different sentinel, not a reason to change this one.

Every way to reach the new branch:

| How `pfp` became NULL | Did this call `SetTimeOut()`? | `ClearTimeOut()`? | `ClearAlarmedPid` already ran? |
|---|---|---|---|
| `timeout == CF_NOINT`, then pipe/fork/`fdopen` fail | no | no (gate) | only on `fdopen` fail |
| `timeout != CF_NOINT`, pipe() or fork() fail | yes | yes | no (never published; `ALARM_PID` is still `-1` from `SetTimeOut`) |
| `timeout != CF_NOINT`, `fdopen` fail | yes | yes | yes (the eight sites) |

The middle row is why **both** halves of this commit are required. `ClearAlarmedPid` does not run when `fork` never happened; `ClearTimeOut` is what cancels the ticking alarm. The last row is why `ClearAlarmedPid` alone is not enough: `ClearTimeOut` is `alarm(0)` + `SIG_DFL` + `TIMEOUT_ARMED = 0`. Leaving the alarm armed after a failed open is how the *next* command gets killed (attack 6, measured).

`ClearTimeOut()` is documented idempotent and does not touch `TIMEOUT_FIRED` / `TIMEOUT_SIGNALLED`. Calling it when `SetTimeOut` ran is the intended pair. Calling it when `SetTimeOut` did not run is gated out.

Could this clear a *different* promise's timeout?

- `RepairExec` is promise-at-a-time. `cf-agent` has no worker threads.
- `SetTimeOut()` is process-global: it writes `ALARM_PID = -1` and replaces the pending `alarm()`. If this promise had a timeout, it already clobbered any previous one at line 308. Clearing it is restoring "no timeout", which is the state the next promise expects unless *it* arms.
- Nested `RepairExec` would require a `commands:` promise to start another `commands:` promise on the same stack. The `pfp == NULL` branch never reaches `ModuleProtocol` / the read loop. I found no call from `TimeOut()` or from a signal handler into `RepairExec`.
- Background: `fork()` is *before* `SetTimeOut()`. The parent skips the whole `do_work_here` block, never hits this branch, and later runs the pre-existing bottom `ClearTimeOut()` — a no-op, because the parent never armed. The child that fails `cf_popen*` now `ClearTimeOut()`s its own alarm and `return`s. That `return` still does not `_exit`, so the child continues in `VerifyExecPromise` as a second agent — **pre-existing**, not introduced, and out of scope.

The two *other* post-`SetTimeOut` early returns in this function are still leaks, and the author did not claim to close them:

- Line 330, powershell on Unix: `SetTimeOut` then `return ACTION_RESULT_FAILED` with no `ClearTimeOut`. Never forked. `ALARM_PID` is `-1`. Pure B-15.
- Lines 395–397, `CfReadLine` error: `cf_pclose` (which now `ClearAlarmedPid`s) then `return` without `ClearTimeOut`. Alarm stays armed. B-15, already named in the register as `:393`.

B-19's write-up asked only for the `pfp == NULL` path, because that is the one that also left a *reaped* pid in `ALARM_PID`. Scope is right. The PR should say the other two returns are still B-15, so nobody thinks `RepairExec` is now leak-clean.

`timeout.c`'s contract that `ClearTimeOut()` is safe to call when nothing is armed is used only hypothetically here: the gate prevents that call. I still walked `ClearTimeOut()`: `alarm(0)`, `signal(SIGALRM, SIG_DFL)`, `TIMEOUT_ARMED = 0`. Harmless if it ever ran extra.

---

## 5. The untested-branch claim

**Half right, half overstated, and the two new paths are not in the same bucket.** I tried the things the brief named.

### `fdopen()` after a successful `pipe()`+`fork()`

On this Darwin (**measured**):

- `fdopen` of a pipe fd does **not** allocate a new fd (`orig=4`, next `open` returned `6`, the write end is `5`).
- `FOPEN_MAX` is 20; `sysconf(_SC_STREAM_MAX)` is 1 048 576. `fopen("/dev/null")` 20 000 times succeeded; the subsequent `pipe`+`fork`+`fdopen` still succeeded. There is no small static `FILE` table to exhaust.
- `RLIMIT_NOFILE = 5` and `= 3` both failed at `pipe()`, never reached `fdopen`. Starving fds does not isolate this branch.

So the author's "starving real fds crashes the harness / fails earlier" is **true** as a reason `RLIMIT_NOFILE` cannot hit these eight sites. FILE* exhaustion is **not** a portable substitute on this libc.

What *does* hit them: a test double for `fdopen`. I compiled a `__DATA,__interpose` dylib that returns `NULL`/`ENOMEM` when `CFE4735_FDOPEN_FAIL` is set, and drove the **real** `cf_popen_sh("/bin/true", "r")` against both installed dylibs.

| dylib | `cf_popen_sh` | `errno` | `ALARM_PID` after |
|---|---|---|---|
| 4735 (`89379323d`) | `NULL` | 12 `ENOMEM` | **-1** |
| 4727 (`8f4ebedbd`) | `NULL` | 12 `ENOMEM` | **17966** (the just-reaped child) |

`SetTimeOut(30)` had set `ALARM_PID = -1` before the call. A leftover `-1` on 4735 could have been "never published." The 4727 column proves publication happened: the same interpose, the same `/bin/true`, a positive pid still registered after the reap. 4735 cleared it. That is a discriminating test of one of the eight sites (`cf_popen_sh` → `cf_popen_sh_select` `'r'`). The other three functions' tails are the same inlined sequence (attack 1).

This is Darwin-specific (`DYLD_INSERT_LIBRARIES` + interpose section; Linux would be `LD_PRELOAD`). A control run with the dylib inserted but the env unset SIGSEGV'd — I will not recommend shipping that exact stub. The fail-env path was clean (`RC=0` both dylibs).

The author listed `LD_PRELOAD` / `DYLD_INSERT_LIBRARIES` in the brief and then called a test "impractical." I disagree that it is impractical. I agree it is a poor *portable in-tree* test, and I would not make it the only one.

### `fd >= MAX_FD` in `cf_pclose()`

The author's second sentence: the pre-existing `fd >= MAX_FD` branch "is in the same untested position for the same reason, per CFE-4727's own review."

CFE-4727's reviews said that branch is **practically dead for a `FILE*` that came from `cf_popen*`**, because `ChildrenFDSet()` grows `MAX_FD` before a successful open returns. They did not say it is untestable, and they did not say it is untestable *for the same reason as `fdopen` failure*.

It is not the same reason. `MAX_FD` starts at 2048. **Measured:** `fcntl(nullfd, F_DUPFD, 2048)` returned 2048 and `fdopen` of that fd succeeded (`fileno=2048`). A unit test that does one successful `cf_popen`/`cf_pclose` (to initialise `CHILDREN`), `F_DUPFD`s past `MAX_FD`, `fdopen`s, and passes that `FILE*` to `cf_pclose` will enter the branch. No stdio internals, no interposition, no starving the harness.

Whether anyone *should* write that test is a different question. Citing it as precedent that the eight sites cannot be tested is a misread of CFE-4727.

### `RepairExec()`'s `ClearTimeOut()`

This is the half I would actually put in the tree, and it does not need `fdopen` to fail.

`pipe()`-failure is enough: `SetTimeOut` has already armed, `GenericCreatePipeAndFork` never published, `ClearAlarmedPid` never runs, and the new `ClearTimeOut` is the only thing that cancels the alarm. `RLIMIT_NOFILE = 3` makes `pipe()` fail deterministically (`errno=24`, **measured**). That is POSIX. `timeout_test` already links `libpromises` and already calls `SetTimeOut` / `cf_popen_sh`.

Standalone model, same host, leftover 2 s `SIGALRM`, then a decoy `sleep 10` published into `ALARM_PID` (the decoy cancelled the *inherited* timer so only the parent leftover could kill it):

| After failed `pipe()` | leftover fired | `TIMEOUT_SIGNALLED` analogue | decoy |
|---|---|---|---|
| no `ClearTimeOut` | 1 | 1 | reaped, `WTERMSIG=9` |
| `ClearTimeOut` | 0 | 0 | still running at T+3 s |

That is the production failure mode of *not* having this `RepairExec` branch: the next command, which never asked for a timeout, is registered by `GenericCreatePipeAndFork` and then killed by the previous promise's alarm. I would add this as an eighth `timeout_test` case (setrlimit / `cf_popen_sh` returns NULL / restore rlimit / `ClearTimeOut` / second `cf_popen_sh("exec sleep 10")` / wait 3 s / child still alive / `cf_pclose`). A sibling that *skips* `ClearTimeOut` and asserts the decoy dies would pin the defect, but is optional once the positive case exists.

It does not execute the eight `ClearAlarmedPid` lines. Those stay Darwin-interpose or untested. That is acceptable for a resource-exhaustion arm that the closers also do not unit-test, **provided** the PR does not claim the eight sites were shown by `timeout_test` 7/7. They were not. I re-ran that binary: **7/7, `RC=0`**, and it does not touch this commit's new lines.

---

## 6. Blast radius if this is wrong

Trace is the same `TimeOut()` → `GracefulTerminate(..., PROCESS_START_TIME_UNKNOWN)` → `Kill()` → plain `kill(2)` path CFE-4727 already walked. `PROCESS_START_TIME_UNKNOWN` skips `SafeKill()`'s start-time check (**read**, `process_unix.c:227–233`). On Darwin this build also has no `GetProcessState()`, so even a known start time would not save you. If `getpgid(ALARM_PID) == ALARM_PID`, `TimeOut()` then `kill(-ALARM_PID, SIGKILL)`.

| If the new code… | What `TimeOut()` does | Worst case |
|---|---|---|
| `ClearAlarmedPid(wrong)` where `wrong != ALARM_PID` | never entered; guard is a no-op | the old leak remains (reaped pid still registered) |
| `ClearAlarmedPid(pid)` where `pid` was recycled onto a live other child | finds `-1` on the next fire | that other command is **unbounded**; CFE-4726 reports "NOT terminated" |
| clears **before** `cf_pwait` (author did not) | finds `-1` during the wait | CFE-4727 itself, on a new set of sites: command that has not exited is unreachable |
| does not run at all (the pre-fix) | `ALARM_PID` names a reaped, recyclable pid for up to `exec_timeout` | `kill` / `kill(-pid, SIGKILL)` of whoever inherited the number, as root, plus a false "was terminated" |
| `RepairExec` `ClearTimeOut` does not run (the pre-fix, `pipe`/`fork` fail *or* `fdopen` fail) | leftover alarm fires during the **next** command, whose `cf_popen` has just published its pid | the next command is killed even if it has no `exec_timeout`. **Measured** in the standalone model (`WTERMSIG=9`) |
| `RepairExec` `ClearTimeOut` runs when this promise never armed | gated out | — |
| `RepairExec` `ClearTimeOut` runs and there *was* a previous promise's alarm | `SetTimeOut` at line 308 already replaced it | clearing is what this promise is supposed to do |

The scary case this commit actually closes is the last-but-two row combined with a reaped pid (the eight sites) and the leftover-alarm kill of an innocent later command (`RepairExec`). Both are real. The recycle kill of a stranger requires the alarm to fire in the seconds-to-minutes window *and* the kernel to reuse the number; the leftover-alarm kill of the *next* `cf_popen` child does not need recycle at all. That is why `ClearTimeOut` on this path is not cosmetic.

If the insertions had used the wrong pid, the object-level shared tail would have had to compare a register that was not the `CreatePipeAndFork` return. It compares that register. I cannot make this commit's blast radius worse than the pre-fix without rewriting the tails.

---

## Author uncertainties, by name

### 1. No discriminating test exists for either new path

Disagree that none exists. Agree that none is in the tree, and agree that a *portable, non-interposing* test of the eight `fdopen`-failure sites is ugly on this libc.

What I would actually build, in this series or as the next commit, not as a blocker:

1. **`timeout_test` leftover-alarm case** (portable POSIX). `SetTimeOut(2)`; drop `RLIMIT_NOFILE` to 3; `cf_popen_sh("true","r")` is NULL; restore the limit; `ClearTimeOut()`; `cf_popen_sh("exec sleep 10","r")`; wait 3 s; `kill(child, 0) == 0`; `cf_pclose`. That is RepairExec's new branch's load-bearing effect. I have the out-of-tree model already; it discriminates.
2. **Do not** add the DYLD/LD_PRELOAD `fdopen` stub as the in-tree pin of the eight sites unless someone wants a `// ifdef __APPLE__` / Linux twin and is willing to own the extra failure modes (my env-unset control SIGSEGV'd). The four inlined tails plus the 4727-vs-4735 interpose run are enough review evidence.

`timeout_test` 7/7 and `04_exec_timeout/` 6/6 are regression tests of the *old* paths. They do not, and cannot, underwrite the new ones. The commit message should not be read as saying they do. "Verified by the full existing regression suite instead, proving no regression on the paths that are reachable" is the accurate sentence; I independently confirmed the first half (7/7) and did not re-run the second.

### 2. Forward declaration vs moving the definition vs a header

No static-analysis or runtime concern. Match `cf_pwait`.

`ClearAlarmedPid` is `static`. A header declaration would be wrong: it is not part of `pipes.h`. Moving the definition to sit above the four parents would also compile and would remove a prototype that has to stay in sync. Either is fine. The author matched the file's existing `static int cf_pwait(pid_t pid);` one line above. That precedent is the right one to follow *in this file*: `cf_pwait` is the other helper these exact sites already call, it is also `static`, and it is also defined after the parents. Introducing a different pattern for the sibling helper would be the maintainability cost.

"Used from code that runs before `cf_pclose` would be reachable for that same pipe" is a sequencing observation, not a C visibility problem. The compiler only needs a declaration before the call. The inlined object does not even have a `_ClearAlarmedPid` symbol to get out of order.

`-Wmissing-prototypes` does not apply to `static`. An unused forward declaration would warn only if every call site disappeared and the definition remained; the closers still call it.

I would not move it. I would not put it in a header. The one-line prototype is the smallest change that makes the eight sites legal C.

---

## Pre-existing defects, including ones the author did not list

The author said none new were found. These are pre-existing and correctly left alone. Two of them are worth naming in the PR so the "RepairExec is now clean" reading cannot start.

| Item | Right to defer? | Why |
|---|---|---|
| `RepairExec` powershell-on-Unix (line 330) and `CfReadLine` error (397) still skip `ClearTimeOut` | **Yes.** | B-15 family, already on the register as `:330` / `:393`. Neither leaves a reaped pid in `ALARM_PID` after CFE-4727 (330 never forks; 397 goes through `cf_pclose`). Not B-19. |
| `history.c:323` and `nfs.c:405` / `:1125`: `SetTimeOut` then `cf_popen == NULL` without `ClearTimeOut` | **Yes.** | Same family, different binaries. `history.c` even uses `timeout != 0` rather than `CF_NOINT`. |
| On `fdopen` failure the remaining pipe fd is not `close`d | **Yes.** | POSIX `fdopen` failure leaves the fd open. Pre-existing leak of one fd per failure. Not this commit's job. |
| That leaked fd is the child's stdout (or the parent's unused write end). `cf_pwait` can then block until the child exits or, if the child writes enough to fill the pipe, **forever** if no timeout is armed | **Yes.** | Pre-existing hang. With a timeout, CFE-4727's wait-then-clear is what makes `TimeOut()` able to kill the child *during this new `cf_pwait`*, which is exactly why the insertions had to be after the wait. |
| Background child that fails `cf_popen*` `return`s into `VerifyExecPromise` instead of `_exit` | **Yes.** | Pre-existing second-agent bug. The new `ClearTimeOut` in that child is still the right local action. |
| B-16 (`ShellCommandReturnsZero` leaves a reaped pid) | **Yes.** | Different function. Same defect class, already filed. |
| B-18 pre-fork publish race | **Yes.** | Different instant. This commit does not touch arming order. |
| `ALARM_PID` still a non-`volatile` `pid_t` | **Yes.** | Unchanged; CFE-4727 already recorded it. |
| `cf_pclose_nowait` still neither waits nor clears | **Yes.** | Unix `RepairExec` does not call it. |

None of these make wait-then-clear-then-`ClearTimeOut` internally contradictory.

---

## Recommendation for the fork issue / PR

Offer `89379323d` as CFE-4735. Record, in the author's voice or the commissioning session's:

1. Independent review agrees the eight sites are the defect fable-deep named under CFE-4727 attack 5, that each insertion uses the `CreatePipeAndFork` pid after `cf_pwait`, and that the object file has four shared tails (not eight independent copies) each comparing `ALARM_PID` to that same register under `pthread_sigmask`.
2. Independent review agrees `RepairExec`'s gate is the same `!= CF_NOINT` that armed, and that `cf-agent` is single-threaded (no `pthread_create` in that tree). The new `ClearTimeOut` cannot see another live promise's timeout because `SetTimeOut` already replaced it.
3. Independent review **disagrees** that neither path can be discriminated. Out of tree, without modifying the worktree:
   - Interposed `fdopen` → `ENOMEM`: 4727 leaves `ALARM_PID=17966`, 4735 leaves `ALARM_PID=-1`.
   - `RLIMIT_NOFILE` so `pipe()` fails, leftover 2 s alarm, next child published: without `ClearTimeOut` the decoy dies `SIGKILL`; with it, the decoy is still running at 3 s.
4. Add the portable leftover-alarm case to `timeout_test` when convenient. Do not block the offer. Do not tell upstream that 7/7 + 6/6 executed the new lines.
5. `fd >= MAX_FD` is *not* untestable for the same reason; `F_DUPFD 2048` works on this host. Drop that sentence from the commit message / PR, or qualify it.
6. Name the two remaining `RepairExec` early-return leaks as still-B-15, so this is not read as closing every armed-timeout hole in that function.

No code change required before the offer.
