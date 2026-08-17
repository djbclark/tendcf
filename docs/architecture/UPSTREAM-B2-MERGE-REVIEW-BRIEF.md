# UPSTREAM REVIEW BRIEF — B-2 merged with #6299, CFEngine core exec_timeout

**Frozen input, 2026-08-17.** This is the shared prompt given verbatim to each
member of the second-opinion panel. Do not edit it to reflect what the reviews
later found — the reviews are separate files, and the register records the
outcome.

---

## Your role

You are an independent reviewer of a C merge resolution that is about to be
offered to an upstream open-source project (CFEngine Core, by Northern.tech).
It was written by a different AI model. Your job is **adversarial**: assume the
resolution is wrong and try to demonstrate it. A review that finds nothing is a
valid outcome, but only after a real attempt.

This is **signal-handler code**. Weight async-signal-safety, ordering and
reentrancy accordingly.

The author's own uncertainties are listed at the bottom. Address each of them
explicitly and by name. Do not simply agree with the author's framing — the
framing may itself be the error.

## Where the code is

Repository: `/Users/djbclark/src/core-b2merge`, a worktree of a fork of
`cfengine/core`, on branch `fix/timeout-process-group-merged`.

It was branched from `0ab083c4d`, which is the head of the **live upstream PR
cfengine/core#6299**. The merge under review brings in branch
`fix/timeout-process-group` (`847373cf6`).

```
git -C /Users/djbclark/src/core-b2merge log --oneline master..HEAD
git -C /Users/djbclark/src/core-b2merge diff 0ab083c4d..HEAD

# the two sides, before the merge:
git -C /Users/djbclark/src/core-b2merge show 0ab083c4d:libpromises/timeout.c
git -C /Users/djbclark/src/core-b2merge show 847373cf6:libpromises/timeout.c
```

Read the surrounding files, not just the diff:

- `libpromises/timeout.c`, `libpromises/timeout.h` — where both conflicts were
- `cf-agent/verify_exec.c` — `RepairExec()`; **this file auto-merged textually,
  which is exactly why it is the dangerous one**
- `libpromises/pipes_unix.c` — `cf_popen()`'s child, `setpgid()`, `ALARM_PID`;
  and `cf_pclose()`, which clears `ALARM_PID` before waiting
- `libpromises/process_unix.c` — `GracefulTerminate()`'s SIGINT/SIGTERM/SIGKILL
  ladder
- `libpromises/locks.c` — the other caller of `GracefulTerminate()`

You have read access to the whole repo and the web. **Write nothing except your
own output file. Do not commit, push, branch, or modify any existing file.**

## What the two sides do

The changes are **complementary, not contradictory**, but they edit adjacent
lines of the same two functions, `SetTimeOut()` and `TimeOut()`.

- **#6299** adds `TIMEOUT_FIRED` / `TIMEOUT_SIGNALLED` (both
  `volatile sig_atomic_t`) so a `commands:` promise that exceeds `exec_timeout`
  is reported as failed rather than compliant. `TIMEOUT_SIGNALLED` exists
  specifically because the alarm can fire with `ALARM_PID` already cleared —
  `cf_pclose()` clears it before waiting — in which case the command timed out
  but was never terminated, and claiming otherwise would be a false statement in
  an error message.
- **B-2** adds `TIMEOUT_ARMED`, `ClearTimeOut()`, and a process-group kill, so
  descendants of a timed-out command are signalled. Without it a `sh` grandchild
  survives, holds the pipe open, and `exec_timeout` does not bound wall clock at
  all.

The intended merged shape: `SetTimeOut()` sets all three flags; `TimeOut()` sets
`FIRED`, clears `ARMED`, and **inside the `ALARM_PID != -1` branch** sets
`SIGNALLED` and does the group kill.

## What the review must attack

1. **The `ClearTimeOut()` / `TIMEOUT_FIRED` hazard.** B-2's `ClearTimeOut()`
   replaces an open-coded `alarm(0); signal(SIGALRM, SIG_DFL)` in
   `cf-agent/verify_exec.c` that #6299 samples its flag immediately **before**.
   If the merged `ClearTimeOut()` clears `TIMEOUT_FIRED`, #6299's outcome
   reporting silently regresses to reporting timed-out promises as compliant —
   and because `verify_exec.c` auto-merged, nothing warns you. Verify the actual
   ordering in `RepairExec()` yourself. Does the merged code sample before it
   clears, on **every** path?

2. **Async-signal-safety of `TIMEOUT_ARMED`.** On the B-2 side this flag is a
   plain `bool`, and it is written from inside `TimeOut()` — which *is* the
   `SIGALRM` handler. #6299's two flags are `volatile sig_atomic_t`. Determine
   whether the merged code fixed this or preserved it, and whether it matters in
   practice here. If the author changed the type, check they did not break
   `TimeOutIsArmed()`'s use in `cf_popen()`'s child.

3. **Stale `ALARM_PID` and the negative kill.** `TimeOut()` does
   `kill(-ALARM_PID, SIGKILL)` guarded on `getpgid(ALARM_PID) == ALARM_PID`.
   Attack that guard. Can `ALARM_PID` be stale by the time the guard runs? Can
   the group be gone and the pgid reused? Is reading `getpgid()` *before*
   `GracefulTerminate()` sufficient, as the comment claims? Note a prior panel
   argued PID recycling is impossible because the process is an unreaped zombie
   — decide for yourself whether that argument actually holds for the *group*.

4. **`setpgid()` scope.** An earlier version of B-2 called `setpgid(0,0)`
   unconditionally on every `cf_popen()` child, and all three reviewers on the
   2026-08-16 panel refused it. The committed version gives a group only to the
   timeout path, gated on `TimeOutIsArmed()`. Check the gate is actually correct
   and race-free between `SetTimeOut()` and the fork. Check `setpgid()` and
   `getpgid()` failures are logged rather than silently swallowed.

5. **Leaked `ARMED` state.** Is there any path — early return, error, a promise
   that finishes before the alarm — that leaves `TIMEOUT_ARMED` set, so that an
   unrelated later `cf_popen()` child needlessly leads a process group?

6. **The tests.** Five acceptance tests under
   `tests/acceptance/08_commands/04_exec_timeout/` come from #6299 and must
   still pass. Any test the author added for the descendant-kill behaviour must
   genuinely discriminate — fail without B-2's half, pass with it. Could it pass
   against the unmerged source?

## Traps you must control for

These have burned prior work in this series. Your review must state what you did
about each.

1. **Never read a return code through a pipe.** A prior session reported a stale
   binary's output as a fixed result because a failed `cc`'s rc came from a pipe.
   Write `echo "RC=$?"` to a file immediately after the command; use distinct
   output filenames for anything you compile.
2. **`--bindir` is wrong for an in-tree build.** The acceptance harness needs
   explicit `--agent=` / `--cfpromises=` / `--cfserverd=` / … paths. All five
   tests failing in ~2 seconds is a harness bug — the suite contains a
   deliberately ~12-second test and cannot fail that fast.
3. **`cf-promises` in the build tree is a libtool wrapper script**, not the
   binary; the real one is `cf-promises/.libs/cf-promises`. Using the wrapper
   makes `cf-agent` silently fall back to failsafe and return in ~0.26s having
   run nothing. Also check `CFENGINE_TEST_OVERRIDE_WORKDIR` is set.
4. **A wall-clock ladder measurement needs a single-process command.** A probe
   like `sh -c "trap '' INT TERM; sleep 30"` measures B-2's own defect — the
   surviving `sleep` grandchild holding the pipe — not the ladder, and will make
   a working fix look broken. A prior session lost time to exactly this,
   recording 30.4s on a correct build.
5. **Platform.** The host is **macOS 26.6.1 (25G76), arm64**. macOS has no
   `process_darwin.c`; `libpromises/Makefile.am` selects `process_unix_stub.c`
   for any platform that is not Linux/AIX/HP-UX/Solaris/FreeBSD, so
   `GetProcessState()` only distinguishes "exists" from "does not exist" via
   `kill(pid, 0)` and can never report `ZOMBIE` or `STOPPED`. Say plainly which
   claims are measured here and which are reasoned about Linux.

A review that asserts a before/after difference it did not measure is worth less
than one that says "I could not run this, here is what I read instead."

## What the author actually did

Three local commits on `fix/timeout-process-group-merged`:

- **`8793f3747`** — the merge itself, kept as a faithful union plus conflict
  resolution. `SetTimeOut()` sets all three flags; `TimeOut()` sets `FIRED`,
  clears `ARMED`, and does `SIGNALLED` + group kill inside the
  `ALARM_PID != -1` branch; `ClearTimeOut()` clears **only** `ARMED`, with the
  lifetime contract written into both `timeout.h` and the function body.
- **`ade76f616`** — the required `setpgid()`/`getpgid()` failure logging, kept
  out of the merge commit so the merge stays a faithful resolution.
- **`3d8e90d68`** — new acceptance test `timeout_kills_descendants.cf`.

Build: autogen rc 0, make rc 0, **2 warnings, byte-identical to the #6299
baseline's 2** (`evalfunction.c:674`, `variable.c:296`, neither file touched).
Zero new warnings.

Tests: 6/6 pass in 65s (the five from #6299 plus the new one).
Discrimination: removing only the `if (TimeOutIsArmed()) { setpgid... }` hunk
and rebuilding makes the new test **FAIL in a 32s run** (the `sleep 30`
grandchild holding the pipe dominates); restored byte-identically (sha256
`7af027630c409cbd2b07c4e22c645c3d1e777231afd75bf58c46bf440a6ec4a6` before and
after) and rebuilt, it **passes in 20s**.

The unconditional `setpgid(0,0)` the 2026-08-16 panel refused is **not** present:
the child calls `setpgid` only under `if (TimeOutIsArmed())`
(`pipes_unix.c:254`).

## The author's uncertainties

Address each explicitly and by name.

1. **The hazard is latent, not live.** With the merged ordering, a
   `ClearTimeOut()` that cleared `TIMEOUT_FIRED` would pass all six tests today,
   because `RepairExec()` consumes both flags before disarming. The resolution
   enforces the safer lifetime contract, but nothing executable pins it. Is that
   overcautious, or is an unpinned contract exactly what a reviewer should
   demand a test for?
2. **Windows/MinGW build unverified — the author's own biggest worry.**
   `timeout.c` is compiled unconditionally (`libpromises/Makefile.am:163`) while
   `pipes_unix.c` is `if !NT`. libntech has no `getpgid()` compat, MinGW has no
   `getpgid()`, and `platform.h` only defines a dummy `SIGKILL`. Master's
   `TimeOut()` already references `GracefulTerminate()` with no NT
   implementation, so core's NT linkage story predates this series — but B-2's
   `getpgid()`/`kill(-pid)` may break a Windows compile that master survives.
   No `#ifndef __MINGW32__` was added speculatively.
3. **`TIMEOUT_ARMED` is a plain `bool`** written from the `SIGALRM` handler and
   read from normal control flow, sitting beside two `volatile sig_atomic_t`
   siblings written in the same handler. The author kept it because it is B-2's
   committed, panel-reviewed content. **Weigh that reasoning critically:** the
   2026-08-16 panel reviewed B-2 *standalone*, where there were no
   `sig_atomic_t` siblings to be inconsistent with. It is the merge that creates
   the inconsistency, so "already reviewed" may not transfer. Decide whether the
   merge is the right place to fix it, and whether `TimeOutIsArmed()`'s use in
   `cf_popen()`'s child would be affected by a type change.
4. **`getpgid()` in a signal handler** is not on the POSIX async-signal-safe
   list (`setpgid` and `kill` are). Safe in fact on CFEngine's Unix platforms
   (thin syscall), formally unspecified.
5. **The child-side failure `Log()`** (`ade76f616`) sits in a block whose banner
   says "only call async-signal-safe functions in child". The author believes
   the branch unreachable and notes `cf_popen` children already `Log()` on
   dup2/exec failures nearby — but it is a deliberate exception, made to satisfy
   the must-log constraint.
6. **Timing margins of the new test:** pass side ~10–12s against a 20s
   threshold, fail side ~31s. ~9s margin each way, on macOS/arm64 only. A loaded
   CI runner stretching the termination ladder past 20s would flake it.
7. **The discrimination removed only the `setpgid()` hunk**, not the
   `TimeOut()` group-kill hunk. The complementary experiment was not run.
8. **The "before" test evidence is a prior session's log** of the same commit
   `0ab083c4d` in a different worktree; not rebuilt and rerun pre-merge here.
9. **`timeout_does_not_leak_to_next_promise.cf` still passes**, but its
   mechanism is the `a->contain.timeout != CF_NOINT` guard plus `SetTimeOut()`'s
   reset — not `ClearTimeOut()`. It cannot distinguish this `ClearTimeOut()`
   resolution from a flag-clearing one. See uncertainty 1.

## Pre-existing defects the author found and deliberately did NOT fix

Five, including `RepairExec()`'s three early returns that leak an armed alarm.
Judge whether deferring them is right, or whether any is so entangled with this
merge that shipping without it is incoherent.
