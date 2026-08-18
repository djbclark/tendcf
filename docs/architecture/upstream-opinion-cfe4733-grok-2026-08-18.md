# CFE-4733 (B-16) review — grok — 2026-08-18

Worktree `/Users/djbclark/src/core-alarmreset`, branch `fix/alarm-pid-reset-after-reap`,
HEAD `e7fd46c6d` on upstream master `a0bca6aaf`. Reviewed the function against
`a0bca6aaf` (unpatched) and `e7fd46c6d` (patched), plus `TimeOut()`, the
`ALARM_PID` declaration/definition, the two `waitpid` sites, the new unit
test, and the `Makefile.am` hook.

## Q1. Are there exactly two reap sites?

Yes. Walked the whole of `ShellCommandReturnsZero()` at `a0bca6aaf`
`libpromises/unix.c:166-274`. The parent issues `waitpid` in exactly two
places, and those are the only reaps:

1. `:238` — `waitpid(pid, &status, WNOHANG)` inside the poll loop. A
   successful reap is `wait_result == pid` (`:239-241`). `wait_result == 0`
   means the child is still running (no reap). `wait_result < 0` is an
   error, not a reap (`:243-249`).
2. `:258` — blocking `waitpid(pid, &status, 0)` on the
   `IsPendingTermination()` path, after `ProcessSignalTerminate(pid)`.
   The `while (waitpid(...) < 0 && errno == EINTR)` loop is the drain.

No third `waitpid`/`wait`/`waitid`/`pclose` exists in the function. The
child never waits. Waiting on a specific pid cannot return some other
positive pid, so `wait_result == pid` is the complete success condition
for site 1.

The other returns are not reaps:

- `:171-175` PowerShell / `:177-180` fork-fail: no child.
- `:184` `ALARM_PID = -1` is in the child, before exec — a different
  address space; irrelevant to the parent's copy.
- `:249` `wait_result < 0 && errno != EINTR`: wait failed, no reap
  (see Q2).
- `:271` `return (WEXITSTATUS(status) == 0)` is after the `:241` break,
  i.e. after site 1 already reaped.
- `:274` trailing `return false` is unreachable from the parent after a
  successful fork (both arms of the `if/else if/else` return).

The two insertions land on the two reap sites and nowhere else.

## Q2. Leave `:249` (failed `waitpid`) alone?

Agree — do not reset `ALARM_PID` there.

`:243-249` is `wait_result < 0` after `WNOHANG`. `EINTR` continues the
loop. Anything else returns `false` without a reap. Resetting on that
return would drop the "this child is the current alarm target" signal
while the child may still be alive, which is the opposite of the ticket.

The brief's "zombie still holds the slot" framing is right for the
reachable non-`EINTR` picture of this function, with one footnote that
does not change the decision. POSIX `waitpid` errors are `EINTR`,
`ECHILD`, and `EINVAL`. `EINVAL` is not reachable with `WNOHANG` as the
only option. `ECHILD` would mean this pid is *not* an unreaped child —
the slot is already free, and leaving `ALARM_PID` set would then be
stale. I do not believe `ECHILD` is reachable here: there is no
`SIGCHLD` reaper (`cf-agent.c:953` explicitly refuses `SIG_IGN`;
`pipes_unix.c` installs `SIG_DFL`), and this function is the unique
waiter for the pid it just forked. Treating `:249` as "no reap, leave
the name in place" is the conservative and correct choice for this
ticket. If `ECHILD` ever became reachable it would be a separate leak,
not a reason to reset blindly on every `waitpid` failure.

## Q3. Any path that resets `ALARM_PID` without a reap?

No reachable harmful one.

Site 1 (`HEAD :241`) is inside `if (wait_result == pid)`. That is a
successful reap. No false negative.

Site 2 (`HEAD :263`) is immediately after the blocking-drain loop, not
inside a `waitpid == pid` check. The brief's "both insertions are
immediately after their respective successful `waitpid()` calls" is
slightly loose for site 2: the loop also exits when `waitpid` fails with
an errno other than `EINTR`. On POSIX that leftover errno is `ECHILD`
(child already gone) or the unreachable `EINVAL`. `ECHILD` means there
is no live child left to name, so resetting is still correct. There is
no POSIX errno that means "child still running" and also exits that
loop (`EINTR` retries).

The child's `:184` `ALARM_PID = -1` does not touch the parent. No other
assignment to `ALARM_PID` exists in the function. I did not find a path
that clears the parent's `ALARM_PID` while the child this call forked
is still unreaped.

(The residual race — `waitpid` has already reaped, `ALARM_PID` is not
yet `-1` — is a few instructions wide and inherent to "reap then
clear". Clearing first would be worse: a leaked `SIGALRM` during the
drain would no longer know which pid to stop.)

## Q4. Is the untested `:258` path acceptable to ship?

Yes. Do not block on a pending-termination test.

Both insertions are the same one-line idiom the file already uses at
`:184` and that `pipes_unix.c` / `timeout.c` already use (`ALARM_PID = -1`).
The untested site is not a different algorithm.

The "too timing-fragile" rationale is overstated. A nearly
deterministic unit test exists: install `HandleSignalsForDaemon`,
`raise(SIGTERM)` so `PENDING_TERMINATION` is already true, then call
`ShellCommandReturnsZero("sleep 5", SHELL_TYPE_USE)`. First `WNOHANG`
is almost certainly 0, and the function takes `:258`. That is not why I
would skip it. I would skip it because:

- `ProcessSignalTerminate()` (`unix.c:40-81`) does `sleep(1)` then
  `sleep(5)` then `sleep(1)` on a child that does not die to `SIGINT`.
  The test would take on the order of a second, and up to ~7s, in CI.
- `PENDING_TERMINATION` is process-global and has no reset API. The
  flag would stay true for the rest of the `unix_test` process.
- `cf-agent` itself uses `HandleSignalsForAgent`, which `_exit`s on
  `SIGTERM` rather than setting the flag. `:258` is a daemon path
  (the `generic_agent.c:1485` policy-validation call is the comment's
  motivating case). Worth covering eventually; not the common
  `returnszero` / `files_select` / `process_stop` path.

The two tests that did land (`true` / `false`, `SHELL_TYPE_USE`) both
exercise site 1, which is the path every successful or ordinary-nonzero
call takes. They are the right minimum. `SHELL_TYPE_NONE` is also
untested; it uses the same two reap sites, so it is the same gap, not a
second one.

I would take a cheap `:258` test if someone later extracts the
`sleep()`s out of `ProcessSignalTerminate` or adds a test-only way to
set the flag without the signal/`sleep` tax. I would not hold this
patch for that.

## Other notes (non-blocking)

- `unix_test` sits in the same `if !NT` block as `nfs_test`, links
  `libpromises.la`, and is on `TESTS = $(check_PROGRAMS)`, so `make
  check` will run it on Unix. `ALARM_PID` is visible through
  `exec_tools.h` → `cf3.defs.h:1744` → `cf3.extern.h`. The `-999`
  sentinel is a real discriminator: on the unpatched parent, `ALARM_PID`
  remains the positive child pid, never `-1` and never left at `-999`.
- The defect is real. `TimeOut()` (`timeout.c:42-46`) calls
  `GracefulTerminate(ALARM_PID, PROCESS_START_TIME_UNKNOWN)`, which
  `kill()`s without a start-time check. Combined with a reaped,
  recyclable pid and `cf-agent` typically running as root, this is the
  ticket as filed.
- Out of scope stays out of scope: `:249`, the CFE-4732 /
  `verify_exec.c` / `nfs.c` / `history.c` family, and the
  `nanosleep` poll design.

## Trap control

What I actually did:

- Read `ShellCommandReturnsZero()` in full at `a0bca6aaf` (via
  `git show`) and at `e7fd46c6d` (worktree `libpromises/unix.c:166-277`).
- Read the `a0bca6aaf..HEAD` diff for `unix.c`, `tests/unit/unix_test.c`,
  and `tests/unit/Makefile.am`.
- Read `timeout.c` (`TimeOut` / `SetTimeOut`), `cf3globals.c` /
  `cf3.extern.h` (`ALARM_PID`), `signals.c` (`IsPendingTermination`,
  daemon vs agent handlers), `unix.c:40-81` (`ProcessSignalTerminate`),
  `pipes_unix.c` (existing `ALARM_PID = -1` on `cf_pclose`),
  `exec_tools.h` (export + include chain), and the four call sites
  (`evalfunction.c`, `generic_agent.c`, `verify_processes.c`,
  `files_select.c`).
- Confirmed there is no `SIGCHLD` reaper that would make `ECHILD` at
  `:249` a live concern.
- Ran the already-built `./tests/unit/unix_test` libtool wrapper from
  `tests/unit/` twice. Both runs: 2/2 passed
  (`test_shell_command_resets_alarm_pid_on_success`,
  `test_shell_command_resets_alarm_pid_on_nonzero_exit`).
- The wrapper prepends
  `/Users/djbclark/src/core-alarmreset/libpromises/.libs` to
  `DYLD_LIBRARY_PATH`. `unix.c`, `unix.o`,
  `libpromises/.libs/libpromises.3.dylib`, and `unix_test` all timestamp
  at 2026-08-18 13:06, matching commit `e7fd46c6d`. I did not rebuild.
- I did not repeat the author's `git stash` discrimination run. The
  unpatched parent at `a0bca6aaf:225` sets `ALARM_PID = pid` and never
  assigns `-1` on the parent side, so the same two asserts must fail
  against unpatched code; that is from reading the pre-image, not from
  a rebuild I performed.
- I did not run a top-level `make` or `make check`. I did not execute
  the `:258` path.

## Verdict

**SHIP**
