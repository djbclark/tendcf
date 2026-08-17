# Upstream second opinion — B-1 and B-2

Reviewer slug: `cursor`. Date: 2026-08-16.
Repository reviewed: `/Users/djbclark/src/cfengine-core` on `tendcf-integration`
(`0b5899a8c`), patches `26634ac1f` (B-1) and `cb2561584` (B-2), against
upstream `master` at `17eb78e6d`.

Adversarial reading. Claims below are marked **verified** (read or measured
on this Darwin/arm64 machine) or **suspected** (not demonstrated). I did not
read any other `upstream-opinion-*.md` file or anything under `docs/handoffs/`.

---

## 1. Verdict per item

**B-1 — ship with changes.** The poll loops really were counting iterations,
and a monotonic deadline is the right repair. Two things should change before
this is offered as a security fix:

1. `ProcessPollTimeNs()` must not use `ts` if `clock_gettime` fails. As
   written that is uninitialized-value UB on the failure path.
2. The commit message must stop saying the fail-open is gone. The 5 s / 2 s
   case is fixed on Darwin because SIGTERM now arrives before `sleep` finishes,
   not because `exec_timeout` reports a timeout. `RepairExec()` still cannot
   return `ACTION_RESULT_TIMEOUT`. A command that exits 0 in
   `(exec_timeout, exec_timeout + first wait]` is still promise KEPT.

The loop arithmetic itself can ship once (1) is done. Do not hold B-1 for a
full timeout-result plumbing patch — that is a follow-up, not this diff.

**B-2 — ship with changes.** Killing the timed-out tree is the right idea and
the `getpgid`-before-terminate order is correct. Do not ship the
unconditional `setpgid(0, 0)` on every `cf_popen` child. That is a job-control
change to the entire popen surface, and it is user-visible from a terminal.
Gate `setpgid` on an armed `exec_timeout` (or otherwise keep non-timeout
children in the agent's group), have the parent call `setpgid(pid, pid)` as
well, and add a test of the `sh -c 'sleep 30'` shape. The flat group SIGKILL
after the leader's ladder is acceptable.

---

## 2. Defects found

### D1 — B-1 does not close the fail-open it is being sold as fixing

**Verified** by reading `cf-agent/verify_exec.c` and by measuring `/bin/sh`
on this machine.

`VerifyExecPromise()` has a case for `ACTION_RESULT_TIMEOUT`
(`verify_exec.c:129–130`), but `RepairExec()` never returns that value. Every
successful path falls through to `return ACTION_RESULT_OK` at
`verify_exec.c:495`. After `cf_pclose()`, the promise result is solely
`VerifyCommandRetcode()` of the child's `waitpid` status
(`verify_exec.c:449–458`, `cf-agent/retcode.c:32–116`). If the child
`exit(0)`s, the log line is the one in the filing package — "returned code '0'
defined as promise kept" — whether or not SIGALRM fired.

The 5 s / 2 s repro is `noshell` `/bin/sh -c "sleep 5; exit 0"`. Measured
here, Darwin `/bin/sh` is bash 3.2.57, and **SIGINT to that shell is a no-op
while it waits for `sleep`**: the shell prints its success path and
`waitpid` returns `exited 0`. SIGTERM does kill it (`signaled 15`). Direct
`/bin/sleep` dies on SIGINT (`signaled 2`). So the ladder's first rung does
not stop this command; the second rung does.

Before B-1, SIGTERM arrives at ~timeout + 4.5 s (measured by the author;
nanosleep overshoot **verified** here: 100 × `nanosleep(10 ms)` =
4.229 / 4.348 / 4.385 s). `sleep 5` has already finished. After B-1, SIGTERM
arrives at ~timeout + 1 s. `sleep 5` is still running, the shell is
signalled, `cf_pwait` returns -1, and the promise is not kept. That is why
the author's 5 s / 2 s cell flipped. It is a race won by shrinking the
window, not a timeout result.

**Suspected, not re-run under cf-agent:** `sleep 2.5` / `exec_timeout => "2"`
still KEPT after B-1, because the command can exit 0 during the first
`ProcessWaitUntilExited` wait, before SIGTERM. The author's after-fix table
did not include a command in that window (the closest before-fix cell is
`sleep 3` / timeout 2, which took 10.90 s).

This is not a reason to drop the deadline change. It is a reason not to tell
security@ that "the check timed out" is now distinguishable from "the check
passed" in general.

### D2 — Unconditional `setpgid(0, 0)` breaks job control (B-2)

**Verified.** `GenericCreatePipeAndFork()` (`libpromises/pipes_unix.c:245`)
calls `setpgid(0, 0)` in every child of every popen variant, not only
`commands:` with `exec_timeout`.

With a real controlling terminal (pty): a child that `setpgid(0, 0)`s and
then `read()`s the tty is **stopped by SIGTTIN (signal 21)**. Before the
patch, that child is in the agent's foreground group and the read is legal.
`cf_popensetuid` / `cf_popen` in type `'r'` do not redirect stdin
(`pipes_unix.c:500–509`, `397–415`); the child inherits the terminal.

Consequences, all from POSIX job-control plus the measurement above:

- Interactive `cf-agent` (the `cf-agent -Kf ./foo.cf` workflow) plus any
  type-`'r'` child that reads stdin can stop and hang the agent's read loop.
- Ctrl-C sends SIGINT to the foreground group. `HandleSignalsForAgent()`
  then `DoCleanupAndExit`s (`libpromises/signals.c:156–160`). Children that
  used to share that group and die with the agent now survive as orphans.
- Terminal close / SIGHUP goes to the foreground group. Detached popen
  children in other groups of the same session do not get it.

Non-interactive `cf-execd` runs usually have no controlling terminal;
`tcgetpgrp` is -1 and SIGTTIN does not apply. The author's "invisible for
non-interactive agent runs" is true for that case and false for the
interactive one.

The affected surface is the whole popen family, because they all go through
`GenericCreatePipeAndFork`: `cf_popen`, `cf_popen_select`,
`cf_popen_full_duplex`, `cf_popensetuid`, `cf_popen_sh`,
`cf_popen_sh_select`, `cf_popen_shsetuid`. Callers include, besides
`commands:` (`cf-agent/verify_exec.c`):

- `cf-execd/cf-execd-runner.c` — the `sh -c` that launches `cf-agent`
- `cf-execd/cf-execd-runagent.c`
- `cf-agent/verify_packages.c`, `vercmp.c`, `verify_users_pam.c`,
  `verify_files_utils.c`, `files_select.c`, `nfs.c`, `simulate_mode.c`
- `libpromises/evalfunction.c`, `exec_tools.c`, `processes_select.c`,
  `mod_custom.c`, `unix.c` (`getent`)
- `libenv/sysinfo.c`, `unix_iface.c`
- `cf-monitord` (`history.c`, `mon_processes.c`, `mon_network.c`,
  `mon_temp.c`, `mon_network_sniffer.c`)
- `cf-serverd/server_common.c`, `cf-serverd-functions.c`

`unix.c`'s non-popen `fork`/`exec` path (`unix.c:178–225`) does **not**
call `setpgid`. B-2's TimeOut sweep will not group-kill that child
(`getpgid` will not equal pid unless something else already made it a
leader).

Required change: do not detach children that are not going to be group-killed
on timeout. Smallest fix is a flag set by `SetTimeOut()` and tested in the
child, plus `setpgid(pid, pid)` in the parent before exec (POSIX both-sides
pattern; only the child calls it today, so a timeout that fires before the
child runs `setpgid` skips the sweep — **suspected**, timeout ≥ 1 s makes it
unlikely). Redirecting stdin from `/dev/null` in type-`'r'` children would
also prevent SIGTTIN but is a larger behavior change and does not restore
Ctrl-C.

### D3 — `clock_gettime` failure leaves `ts` uninitialized (B-1)

**Verified** as a code path; **not observed** on this machine (CLOCK_MONOTONIC
succeeds).

```48:56:libpromises/process_unix.c
static int64_t ProcessPollTimeNs(void)
{
    struct timespec ts;
#ifdef CLOCK_MONOTONIC
    clock_gettime(CLOCK_MONOTONIC, &ts);
#else
    clock_gettime(CLOCK_REALTIME, &ts);
#endif
    return (int64_t) ts.tv_sec * 1000000000LL + ts.tv_nsec;
}
```

`ts` is uninitialized. POSIX `clock_gettime` can return -1. A failed call
does not promise to leave `ts` untouched (on this Darwin, a bogus `clockid_t`
left the previous contents in place; a first-call failure would be garbage).
The helper is copied from `EvalContextEventStart()` (`eval_context.c:3927–3937`),
which has the same bug. New code should not copy it. `xclock_gettime()` in
`libntech/libutils/misc_lib.c:93–103` already checks the return and falls
back to `time()`; `process_unix.c` already includes `misc_lib.h`. Use that,
or zero `ts` and check the return. No extra link-time guard is needed:
`HAVE_CLOCK_GETTIME` is 1 here, `eval_context.c` already calls it, and
`libcompat` provides a `time()`-based stand-in via `LTLIBOBJS` when libc
does not.

`#ifdef CLOCK_MONOTONIC` is the right compile-time fallback and matches
`libcfnet/net.c`. CLOCK_MONOTONIC is 6 on this Darwin. Platforms without the
macro use REALTIME and can slip if the clock steps; that is the documented
limitation of the pattern, not a B-1 invention.

### D4 — `setpgid` / `getpgid` errors are silent (B-2)

**Verified** by reading. `setpgid(0, 0)` at `pipes_unix.c:245` ignores the
return. `getpgid(ALARM_PID)` at `timeout.c:49` ignores the return. On
failure `pgid` is `(pid_t)-1`, the `pgid == ALARM_PID` guard is false, and
the sweep is skipped. B-2 then looks like a non-fix for that child, with no
log line. `setpgid(0, 0)` in a freshly forked, non-session-leader child
almost never fails; still check it. **Verified on Darwin:** `getpgid` of a
zombie that has not been reaped returns ESRCH. That is why reading the pgid
before `GracefulTerminate()` is mandatory here, not cosmetic.

### D5 — B-2 has no test; B-1 has no acceptance test

**Verified.** CONTRIBUTING.md (style/hygiene, which still apply) requires
tests: C functions get unit tests, promise attributes get acceptance tests.
The only existing `exec_timeout` in `tests/acceptance/` is an unrelated
30-second bound in `10_files/13_file_dir/001.cf`. B-1 updates
`process_terminate_unix_test.c` (6/6 **verified** on the built binary). B-2
adds nothing. The `sh -c 'sleep 30'` wall-clock/orphan case is exactly an
acceptance test.

### D6 — leftover `assert(timeout_ns < 1000000000)` is not a bug

**Verified.** `ProcessWaitUntilExited` still asserts `timeout_ns < 1e9`
(`process_unix.c:117`). `tv_nsec` is now `MIN(SLEEP_POLL_TIMEOUT_NS,
remaining_ns)`, so a larger timeout would not overflow `tv_nsec`. The assert
documents the existing "timeouts < 1 s" API (`STOP_WAIT_TIMEOUT` is
`999999999L`). Leave it. `ProcessWaitUntilStopped` has never had the assert;
pre-existing.

### D7 — `timeout_ns <= 0` now enters the loop once

**Verified** by reading, not by a unit test. Old loops were
`while (timeout_ns > 0)` and skipped the body. New loops are `while (true)`,
call `GetProcessState` once, then `remaining_ns <= 0` and break. If the
process has already exited, `ProcessWaitUntilExited` can now return true
where it previously returned false without looking. The only caller passes
`STOP_WAIT_TIMEOUT`. Not a production bug. Worth a one-line comment or an
early `if (timeout_ns <= 0)` if they want the old skip-everything behavior.

Integer overflow of `ProcessPollTimeNs() + timeout_ns` is not a problem at
the asserted range: monotonic ns since boot plus < 1e9 fits in `int64_t`;
REALTIME ns in 2026 is ~1.8e18 against `INT64_MAX` 9.2e18.

---

## 3. The three flagged uncertainties

### 1. `setpgid` versus Ctrl-C

The author's framing is the error. This is not an acceptable invisible
tradeoff.

- **Verified:** Darwin `/bin/sh -c` children stay in the parent's process
  group (`pgid` of `sh` and `sleep` equalled the test parent's pgid).
  `setpgid(0, 0)` is what detaches them.
- **Verified:** SIGTTIN stop after that detach, on a controlling terminal.
- **Verified:** `cf-agent` handles SIGINT by exiting from the handler
  (`signals.c:156–160`). It does not walk or kill popen children. Same-group
  children used to get the terminal's SIGINT for free. After B-2 they do not.
- **Verified:** the call-site set is the entire popen family listed in D2,
  including `cf-execd`'s `cf_popen_sh` of `cf-agent`
  (`cf-execd-runner.c:239`). `cf-runagent` is in that set
  (`cf-execd-runagent.c:101`). `cf-execd` itself is a daemon handler
  (`HandleSignalsForDaemon` sets a flag; it does not `exit` from SIGINT).
- **Verified, and it does not regress the path the author of
  `cf-execd-runner.c` thought they had:** that file already does
  `getpgid(pid)==pid` then `kill(-pid)` (`cf-execd-runner.c:306–315`),
  claiming "the shell creates a new process group (PGID equal to the PID of
  the child)". On this Darwin, `sh -c` does **not** do that, so the
  group-kill already did not fire for the agent-found path (agent pgid ≠
  agent pid). After B-2 the agent inherits the *shell's* new group, so
  `getpgid(agent)==agent_pid` is still false. Fallback `pid_to_kill =
  pid_shell` **would** start matching (`getpgid(shell)==shell_pid`) and
  signal the whole group. That fallback change is real; it is probably
  beneficial; it is untested.
- SIGTSTP / orphaned process groups / terminal ownership / SIGHUP: see D2.
  Running children in a now-orphaned group are not sent SIGHUP just for
  becoming orphaned; stopped ones are (SIGHUP+SIGCONT). **Suspected** from
  POSIX, not measured beyond the SIGTTIN stop.

Right call: gate `setpgid` on timeout, or keep children in the agent's group
and find another way to name the tree at timeout. Making the timeout path
"structurally different" is cheaper than breaking job control for `ps`,
`ifconfig`, package list commands, and `cf-execd`'s agent launch.

### 2. The unconditional group SIGKILL

Acceptable on the timeout path. The shared-function argument is **true**.

`GracefulTerminate()` is also called from `KillLockHolder()` in
`locks.c:630` with a stored CFEngine PID and `process_start_time`. That PID
is a lock holder, not a popen child, and is typically in the daemon's own
group. Teaching `GracefulTerminate` group semantics would SIGKILL whatever
shares that group (other `cf-execd` children, the agent, unrelated
processes). Do not do that. A flat `kill(-pgid, SIGKILL)` after the leader
has been through INT/TERM/KILL, guarded on `pgid == pid` captured while
alive, is the right split.

Gentler group escalation would be nicer for a script that traps INT/TERM in
the leader but whose grandchildren would have exited on SIGTERM. Timeout is
allowed to be rude. Wall-clock bound wins.

**PID recycle:** the author's claim that `pgid == pid`, read before
terminate, "closes" a recycle race is **false**. That guard closes a
different bug: "do not `kill(-n)` if `n` is not a group leader, because we
might signal our own group." **Verified** as the intent in the comment at
`timeout.c:57–61`.

What the guard does not close: we remember that pid X led group X, then
`GracefulTerminate` waits ~2 s (after B-1), then `kill(-X, SIGKILL)`. That
signals **process group X**, not process X. If group X still has descendants,
that is the fix. If group X is empty, ESRCH, harmless. If in that window a
new process has become leader of a new group numbered X — the natural
outcome of `fork` recycling X plus B-2's own `setpgid(0, 0)` — we SIGKILL
that new tree. The `pgid == pid` snapshot cannot see that. Unlikely at
normal fork rates; the window is seconds, not microseconds; I would not
block the patch on it. I would not describe the guard as closing it. Using
`PROCESS_START_TIME_UNKNOWN` (`timeout.c:51`) also means the leader kill
itself has no start-time check; pre-existing for `TimeOut`.

`TimeOut` is a `SIGALRM` handler (`timeout.c:32`, `signal(SIGALRM, …)`).
`getpgid` and `kill` are async-signal-safe. `GracefulTerminate` → `Log` /
`GetProcessState` was already not. B-2 does not make that worse in kind.
Pre-existing, not a B-2 defect.

### 3. The test's clock mock

Acceptable. It is not a weakening of what that test was written to test.

`process_terminate_unix_test.c` already mocks `kill`, `GetProcessState`,
`GetProcessStartTime`, and `nanosleep`, and uses `current_time` as a
nanosecond counter. B-1's loops now read `clock_gettime`, so the fake
process (which reacts on `current_time`) and the loops (which would otherwise
read wall time) disagree. **Verified:** the author is right that this is why
`test_kill_long_reacting_signal` broke; 6/6 pass with the mock, on the
binary in `tests/unit/`.

That test's intent is "a process that takes 2 s of fake time to react is not
left SIGSTOP'd, and still exists after the ladder" (`process_terminate_unix_test.c:311–324`),
not "nanosleep overshoot is bounded". Driving `clock_gettime` from the same
fake clock preserves that intent. It reintroduces "sleep costs what was
requested" **inside the test**, which is what a deterministic unit test of
the ladder should do.

Process-wide override: the test links `process_unix.c` and `libutils.la`
(`tests/unit/Makefile.am:362–364`). `libutils` `mutex.c:82` calls
`clock_gettime(CLOCK_REALTIME)` for `pthread_cond_timedwait`. A timed wait
during a test would see 1970-ish time (`InitTime` sets `current_time = 1`).
These six tests do not take that path. **Suspected** harmless; same shape as
the existing `nanosleep`/`kill` overrides. A function pointer in
`ProcessPollTimeNs` would be less invasive and uglier in production code. I
would not ask for it. I would ask for a separate acceptance test that the
deadline tracks wall time under real oversleeping nanosleep — the unit test
cannot say that.

`current_time` is `time_t` used as nanoseconds. On 32-bit `time_t` that
overflows at ~2.1 s of fake time. Pre-existing. This Darwin is 64-bit
`time_t` (`HAVE_64BIT_TIME_T`).

---

## 4. Anything the author missed

**The fail-open diagnosis is right about the stall and wrong about what
"fixed" means.** Iteration counting **verified** (nanosleep overshoot 4.2–4.4 s
per 100 × 10 ms here; matches the author's 4.41–4.66 s). The user-visible
KEPT is not "the ladder is so slow that a killed command is reaped as
success". A SIGINT-killed `/bin/sleep` is `WIFSIGNALED` and `cf_pwait`
returns -1 (`pipes_unix.c:808–815`), which is FAIL, not KEPT. The KEPT path
is: Darwin `/bin/sh -c` **ignores SIGINT**, continues to wait for `sleep`,
`exit 0`s if `sleep` finishes during the wait, and `VerifyCommandRetcode`
treats 0 as kept. B-3 (stub never reports ZOMBIE) makes every wait run to
the deadline even when the leader *did* die; that inflates the stall for
direct `/bin/sleep` (author's 4.4 s after B-1) but is not required for the
`sh -c` KEPT case. Linux `GetProcessState` can return ZOMBIE
(`process_linux.c:150–151`). I did not measure Linux `sh -c` vs SIGINT; the
author correctly did not claim a Linux repro.

**`RepairExec` never reports timeout**, so even a perfect killer would
surface as FAIL / abnormal termination (`verify_exec.c:451–454`), not
`PROMISE_RESULT_TIMEOUT`, unless `waitpid` still sees `exit 0`. The TIMEOUT
enum case is dead. `cf-monitord/history.c:343–345` does set
`PROMISE_RESULT_TIMEOUT` on a failed `fread`, which is a different promise
type and still not a flag from `TimeOut()`.

**B-2's diagnosis of the hang is right.** Parent blocked in `CfReadLine` /
`fread` with BSD `signal()` restart (`SA_RESTART`); grandchild holds the
write end; EOF never comes. Killing only the shell orphans `sleep`. I did
not re-orphan under cf-agent; the POSIX shape and the author's 30.3 s
measurement are enough to believe it. Closing the parent's read end would
unhang without `setpgid` and would leave orphans; for a timeout that is
supposed to *stop the command*, group kill is the right repair. The mistake
is applying `setpgid` where no timeout will ever group-kill.

**`TimeOut` does not set a "we timed out" flag.** Combined with D1, that is
the actual missing security patch: `TimeOut` should record that SIGALRM
fired, and `RepairExec` should return `ACTION_RESULT_TIMEOUT` even if the
child later `exit 0`s. Neither B-1 nor B-2 does this.

**cf-execd already had the `pgid == pid` then `kill(-pid)` pattern**
(`cf-execd-runner.c:306–315`). B-2 is consistent with in-tree practice. The
comment there about the shell creating a group named after the agent is
false on this Darwin; worth not copying the myth.

**CONTRIBUTING hygiene (process section ignored per operator):** both
commits have `Changelog: Title` and no `Ticket:` line. B-1's title is an
implementation sentence; CONTRIBUTING wants user-facing changelog text
("exec_timeout overshot on coarse `nanosleep`" or similar). New comments
have several lines past 78 columns. Not blocking. B-2 doing `setpgid` for
all popen plus a TimeOut sweep is two behavior changes in one commit; if
`setpgid` is gated to timeout they belong together.

**Split:** the two commits are correctly split from each other. Do not merge
them. Do not fold B-3 (Darwin `GetProcessState` stub) into B-1; the author
was right to keep that separate. The remaining fail-open (timeout result not
plumbed) should also stay separate, and should be mentioned in the B-1
writeup so security@ is not told a lie.

---

## 5. What I did not check

- Linux (or any non-Darwin) `sh -c` vs SIGINT, `getpgid` on zombies, or
  `nanosleep` granularity. B-1's overshoot and B-2's SIGINT-noop-on-shell
  may be Darwin-shaped. The iteration-counting bug is real on any platform
  whose `nanosleep` overshoots; the factor is not.
- A live `cf-agent` run of the 22-line policy. I did not use the built
  `cf-agent` against `~/.cfagent` after a naive `-Kf` invocation started
  failsafe update. Mechanism checks were standalone C programs and source.
- Whether `sleep 2.5` / `exec_timeout 2` is still KEPT after B-1 (suspected
  in D1).
- `cf-runagent` interactively, `cf-execd` `agent_expireafter` after B-2, or
  a real Ctrl-C of `cf-agent -Kf` with an in-flight command.
- Whether any type-`'r'` popen caller in tree actually reads stdin in
  production (SIGTTIN is demonstrated; the set of *hurt* commands is not
  enumerated).
- Windows / mingw paths (`pipes` on NT, `SetTimeOut` in `nfs.c`).
- Nested SIGALRM, `exec_timeout` of 1 s under heavy load racing child's
  `setpgid`, or PID reuse in the GracefulTerminate window (reasoned, not
  forced).
- Full unit suite, acceptance suite, or `clang-format` against
  `.clang-format`.
- `libcompat/clock_gettime.c` on a host that lacks the libc function (this
  host has it). The fallback returns 1-second resolution via `time()`;
  deadline math would be coarse there. Pre-existing for `EvalContextEventStart`.
- Async-signal-safety of the pre-existing `TimeOut` → `GracefulTerminate` →
  `Log` path, beyond noting it.
