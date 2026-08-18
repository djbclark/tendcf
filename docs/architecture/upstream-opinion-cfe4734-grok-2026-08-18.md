# Review: CFE-4734 (B-18) — `exec_timeout` armed its alarm before the child existed

Reviewer: grok
Date: 2026-08-18
Target: `92531d60cc87885053aadd7889e384f0435e7e77` on `fix/exec-timeout-prefork-race`
Worktree: `/Users/djbclark/src/core-prefork`
Base: `dbf759d16` (sibling, not stacked on B-17 / B-19)
Upstream: `cfengine/core`. Local only.

**Verdict: SHIP-WITH-CHANGES**

The POSIX `commands:` path is the right fix for a real, observed defect.
`SetTimeOut()` no longer consumes `SIGALRM` in the pre-`fork` window, the
clock starts only after `ALARM_PID` is published, one-shot reuse of a
budget across two forks is the same behaviour the old `alarm()` already
had, and the new unit tests actually fail the old arming order. I would
put this in front of CFEngine maintainers after two small corrections:
the MinGW split is the wrong axis (Cygwin takes the POSIX `SetTimeOut()`
and never compiles `pipes_unix.c`), and the commit's "leaked timeout
goes inert" sentence is false.

---

## Summary

The defect is real. `SetTimeOut()` used to call `alarm(timeout)` at
`timeout.c:58` (old line) and `GenericCreatePipeAndFork()` only wrote
`ALARM_PID` after `fork()` (`pipes_unix.c:272`). Between those two
points `verify_exec.c:311–366` does `umask()`, two `Log()`s, shell-type
dispatch and argument marshaling. If `SIGALRM` arrived in that window,
`TimeOut()` (`timeout.c:110`) took the `ALARM_PID == -1` branch, logged
`"Time out"`, set `TIMEOUT_FIRED` and cleared `TIMEOUT_ARMED`, and
killed nothing. The command then ran unbounded. That is exactly the
guarantee `exec_timeout` exists to provide.

The implementation matches the intended design:

- `SetTimeOut()` still sets the flags, installs the handler, and zeroes
  `ALARM_PID`. On POSIX it cancels any leftover timer and stashes the
  seconds in `TIMEOUT_PENDING`. On MinGW it still calls `alarm(timeout)`
  immediately.
- `StartTimeOutClock()` is one-shot: it consumes `TIMEOUT_PENDING` so a
  second fork under the same `SetTimeOut()` inherits remaining time.
- `GenericCreatePipeAndFork()` starts the clock immediately after
  `ALARM_PID = pid`, and only in the parent (`pid > 0`).
- `TIMEOUT_ARMED` is still set before the fork, so
  `TimeOutIsArmed()` — the child's `setpgid(0, 0)` decision — is
  unchanged on either side of the fork.
- `ClearTimeOut()` zeroes `TIMEOUT_PENDING`, so a timeout that is
  cleared before any fork cannot later be started.

I grepped production `SetTimeOut(` / `ALARM_PID` / `StartTimeOutClock(`
myself rather than trusting the brief. Six production `SetTimeOut()`
sites, two production `ALARM_PID` publishers
(`GenericCreatePipeAndFork` and `ShellCommandReturnsZero`). That census
is correct.

---

## Trap control

For each of the five build/measurement traps in the brief:

1. **`tests/acceptance/testall` exits 0 even when every test fails.**
   I did not trust the exit code. After `make && make install` I ran
   `08_commands/04_exec_timeout` and read the summary line:
   `Passed tests:    6` / `Failed tests:    0` / `Skipped tests:   0`
   / `Total tests:     6`. Wall time 71 seconds. Process exit was 0,
   which in this case matched the passed count, but the passed count
   is what I used.

2. **`.libs` binaries carry an install-prefix RPATH.**
   Confirmed before the run: `otool -L cf-agent/.libs/cf-agent` points
   at `/Users/djbclark/opt/cfengine-dev-4734/lib/libpromises.3.dylib`
   (`S["prefix"]` in `config.status`). I ran `make && make install`
   in the worktree immediately before the acceptance run, then invoked
   `testall` with the worktree `.libs` binaries as specified. I did
   not run acceptance against a stale prefix.

3. **`raise(SIGALRM)` cannot discriminate this fix.**
   I did not write or run any `raise()`-based probe. The unit tests I
   ran wait on the kernel timer (`WaitForAlarm()` / `nanosleep` loops
   and a real `cf_popen("/bin/sleep 5")`). Those are the right kind
   of test.

4. **`alarm(0)` reads and cancels.**
   Controlled by reading `test_start_runs_the_clock_once` against that
   rule, not by treating the test's comment as true. See U4. The other
   `alarm(0)` uses are intentional: `test_set_leaves_the_clock_stopped`
   wants "no timer", and `test_clear_retires_an_unstarted_clock` wants
   "still no timer after a start attempt". Those are not confounded.

5. **Asserting the new API exists is not discrimination.**
   I ran the fixed suite only. I did **not** rebuild with the brief's
   pre-fix emulation (`alarm(timeout); TIMEOUT_PENDING = 0;` in the
   non-MinGW branch) and so I did not independently re-prove that
   exactly two tests fail against the old behaviour. I will not invent
   that measurement. What I did run, against `92531d60c` after
   `make timeout_test` reported the binary up to date:

   - `tests/unit/timeout_test`: **All 10 tests passed**, exit 0, ~27 s
     wall including the make no-op.
   - acceptance `08_commands/04_exec_timeout`: **Passed tests: 6**,
     71 s, after a fresh `make && make install`.

---

## U1 — `cf-monitord/history.c` may lose its timeout entirely

The framing is the error. This is not a live regression.

`history.c:240–243` does arm a timeout when
`a.contain.timeout != 0`. The `"file"` branch then `stat()`s,
`safe_fopen()`s, and drains with `CfReadLine()` (`:247–274`, loop at
`:336`). `StartTimeOutClock()` is never called on that branch, so if
a timeout were actually armed the clock would never start and a
blocking open/read (including a FIFO, which is only `stat()`ed, never
checked with `S_ISREG`) would hang.

That path cannot arm a timeout today.

`VerifyMeasurementPromise()` (`verify_measurements.c:46`) builds
attributes with `GetMeasurementAttributes()`. That function
(`attributes.c:355–369`) starts from `ZeroAttributes` — which sets
`.contain = { 0 }` (`cf3.defs.h:1685`) — and never calls
`GetExecContainConstraints()`. Measurement syntax
(`mod_measurement.c:44–58`) has no `contain` body and no
`exec_timeout`. Common bodies (`mod_common.c:499–511`) do not add
one. A policy `contain =>` on a `measurements:` promise is a parse
error. `a.contain.timeout` is therefore **always 0** at
`history.c:240`, `SetTimeOut()` is never entered, and the
`"pipe"` / `"file"` distinction is irrelevant to this change.

The site looks like unfinished copy from `verify_exec.c`. It even
uses a different unset convention (`!= 0` vs `!= CF_NOINT`). The log
at `:235` will always print `timeout=0`.

Even in the hypothetical where someone later wires `contain` into
measurements, the author's "EINTR-interrupted that read" story is
weaker than it sounds:

- `CfReadLine()` is `getline()` with no `EINTR` retry of its own
  (`file_lib.c:1883–1898`).
- `SetTimeOut()` installs the handler with `signal()`
  (`timeout.c:57`). This tree already documents that
  `signal()` on Linux/glibc is `SA_RESTART`
  (`unix.c:227–229`). On Linux a blocking `read`/`open` of a FIFO
  would restart after `TimeOut()` returned; the handler does not
  `longjmp` or close the fd. The file-branch "timeout" already did
  not abort the read on the primary production OS.
- The file branch never consults `TimeOutHasFired()`. A fired alarm
  with `ALARM_PID == -1` only logged `"Time out"` and set flags
  nobody on this path reads.

So: not a regression, not a ship-blocker, and not a reason to start
the clock at non-forking sites or to keep `SetTimeOut()` arming
immediately. Do not "fix" history.c as part of this commit. If
measurements ever grow a real timeout, that is a separate change and
it needs a timeout that can interrupt I/O, not `SIGALRM` plus
`SA_RESTART`.

---

## U2 — is `GenericCreatePipeAndFork()` the right and complete choke point?

Yes, for the six `SetTimeOut()` callers. The author's scoping of
`ShellCommandReturnsZero()` is sound, but not for the reason the
question implies.

I grepped `ShellCommandReturnsZero(` in this tree. Production callers
are `files_select.c:526`, `verify_processes.c:232`,
`generic_agent.c:1485`, and `evalfunction.c:3053`. None of those is
reachable from a `SetTimeOut()` site with a timeout armed. The six
sites run their command via `cf_popen` / `cf_popen_shsetuid` /
`cf_popensetuid` (and the dead history `"file"` `fopen`). They do
not call `ShellCommandReturnsZero()`. `ModuleProtocol()` on the
`verify_exec` path only parses module-protocol lines; it does not
fork.

So there is no "command that was meant to be bounded" escaping
through `unix.c:225`. `ShellCommandReturnsZero()` publishing
`ALARM_PID` without starting the clock is correct: it never armed a
timeout, and starting one there would attach a *leaked* pending
timeout to an unrelated `getent`/process-stop child. That is the
opposite of what U2 is asking.

Other fork paths:

- Every `cf_popen*` variant and `cf_popen_full_duplex()` goes through
  `CreatePipeAndFork` / `CreatePipesAndFork` →
  `GenericCreatePipeAndFork`. The choke point is complete for the
  pipe machinery.
- `verify_exec.c:300` background `fork()` happens *before*
  `SetTimeOut()` (`:308`). The child then arms and `cf_popen`s. Fine.
- `cf-agent.c:2239` only clears `ALARM_PID` in a backgrounded files
  child.
- `dbm_lmdb.c` fork is corruption repair, not a timed command.

The choke point is right. Putting `StartTimeOutClock()` at individual
call sites would reopen a window between `ALARM_PID = pid` and
`fdopen`/return. Centralizing immediately after the assignment is
the correct place.

---

## U3 — one-shot semantics at `nfs.c:1459`

Same as before for the case that actually runs, and the DONTDO case
the brief asks about cannot happen at this site.

`ReconcileMountOptions()` (`nfs.c:1367`) computes
`timeout = remount_timeout` or `RPCTIMEOUT` (60). At `:1400` it
gates the whole method loop on `MakingInternalChanges()`. That
function (`eval_context.c:3465`) returns false for dry-run and for
`action_policy => "warn"`, and returns true only for
`EVAL_MODE_NORMAL && action != cfa_warn`. If it returns false, the
function exits at `:1407` **before** either `SetTimeOut()` at
`:1434` or `:1459`.

So "VerifyUnmount() returns early under DONTDO without forking" is
not reachable at `:1459`. Both `VerifyUnmount()` (`:1000`) and
`VerifyMount()` (`:918`) re-check `MakingInternalChanges()`, but if
we got to `:1459` the parent already got `true` from the same
predicate on the same `attr`. They will fork.

When both fork under one `SetTimeOut()`:

- The first successful `cf_popen` (unmount) starts the clock.
- The second (mount) sees `TIMEOUT_PENDING == 0` and inherits the
  remainder.
- That is the same as the old `alarm()`: one kernel timer, not reset
  at the second fork.

If the first command consumes the whole budget, `TimeOut()` clears
`TIMEOUT_ARMED`. The second `StartTimeOutClock()` is a no-op and the
mount runs unbounded. That is also the same as before: the single
alarm had already fired.

If unmount's `cf_popen` fails and mount's succeeds, the clock starts
at the first *successful* fork. Slightly more of the budget lands on
the mount than when `SetTimeOut()` started the timer earlier. That
is better, not worse.

The one-shot choice is the right one. Restarting the budget at
`VerifyMount()` would silently double `remount_timeout` for
`unmount_mount`.

The author's "inert leak" claim does not belong in this uncertainty,
but it is adjacent and it is false. See the out-of-scope note and
the required commit-message change.

---

## U4 — is `test_start_runs_the_clock_once` actually testing what it claims?

The comment overclaims. The test still discriminates the
implementation bug it needs to catch.

```c
SetTimeOut(3600);
StartTimeOutClock();
assert_true(alarm(0) > 0);   /* cancels the timer */

StartTimeOutClock();
assert_int_equal(alarm(0), 0);
```

The production one-shot is "consume `TIMEOUT_PENDING`". A re-arming
implementation that left `TIMEOUT_PENDING` set would, after the first
`alarm(0)` cancel, start a fresh 3600 s timer on the second call, and
the last assert would fail. So consume-vs-reuse is discriminated,
and that is the actual bug.

What the test does **not** show is "a running clock is left running".
The first assert already killed it. A hypothetical starter that
reset a live timer to the original budget, but only when a timer
was already ticking, would pass this test and still be wrong at
`nfs.c:1459`.

That is a test-quality issue, not a product bug. Optional rewrite,
not a ship-blocker:

```c
SetTimeOut(5);
StartTimeOutClock();
struct timespec ts = { .tv_sec = 1, .tv_nsec = 0 };
nanosleep(&ts, NULL);
StartTimeOutClock();           /* must not restore 5 s */
int left = alarm(0);
assert_true(left > 0);
assert_true(left <= 4);        /* still the remainder, not a restart */
```

Do not use `raise(SIGALRM)` for this.

---

## U5 — the MinGW divergence

The *idea* is right. The *axis* is wrong.

`pipes_unix.c` is added only under `if !NT` (`libpromises/Makefile.am:179`).
`NT` is `mingw|cygwin` (`m4/cf3_platforms.m4:35`). There is no
`cf_popen` implementation in this tree except `pipes_unix.c`. Windows
pipes live in enterprise, outside this review.

`SetTimeOut()` switches on `__MINGW32__` (`timeout.c:58`). Cygwin
does **not** define `__MINGW32__`. A Cygwin build therefore:

- takes the POSIX branch (defer, `TIMEOUT_PENDING = timeout`),
- does **not** compile `GenericCreatePipeAndFork()`,
- never calls `StartTimeOutClock()`,
- silently disables `exec_timeout`.

That is exactly the failure mode the MinGW comment exists to prevent.
`timeout_test` is also `if !NT`, so Cygwin would not catch it.

This is the one "is there a POSIX-branch build that never reaches
the starter?" the author asked about. The answer is yes.

A CFEngine maintainer will accept "Windows pipes are elsewhere, so
keep arming in `SetTimeOut()` there." They will not accept an
`#ifdef` that does not cover the other half of their own `NT`
conditional. Condition the immediate-arm path on the same platforms
that do not compile `pipes_unix.c`:

```c
#if defined(__MINGW32__) || defined(__CYGWIN__)
    alarm(timeout);
#else
    alarm(0);
    TIMEOUT_PENDING = timeout;
#endif
```

Do **not** make deferral unconditional and wait for an enterprise
Windows follow-up. That would ship a silent `exec_timeout` disable
on every Windows agent until nova is patched — a worse regression
than the prefork race, and on a first-class platform.

Unconditional deferral is the wrong answer. Matching the `NT` axis
is the right one.

---

## U6 — `TIMEOUT_PENDING` is a plain `int`

The author's justification is sufficient for this commit and
incomplete as a reason to leave it that way.

Verified: `TimeOut()` does not read or write `TIMEOUT_PENDING`.
`ClearTimeOut()` is not called from a handler (sites:
`nfs.c:581`, `nfs.c:1177`, `verify_exec.c:502`, `history.c:377`).
`StartTimeOutClock()` runs in ordinary process context after
`fork()`, with any previous timer already cancelled by
`SetTimeOut()`'s `alarm(0)`. There is no handler-vs-main race on
this variable today.

That does not make the type asymmetry free. The next person who
touches `TimeOut()` — and this file has been under active repair
for three stacked timeout tickets — will see three
`volatile sig_atomic_t` neighbours and a plain `int` whose comment
says "not touched from the handler." The cheap way to make that
comment hold is to use the same type as the others. `sig_atomic_t`
is wide enough for a timeout in `1..3600`.

Not a ship-blocker. Optional one-line type change. Do not treat
"the handler doesn't touch it" as a design invariant you can only
document; the type is the invariant.

---

## U7 — is the semantic change acceptable to upstream?

It is a fix, not an undocumented behaviour change, and
`Changelog: Commit` is the wrong metadata for it.

`mod_exec.c:36` documents `exec_timeout` as "Timeout in seconds for
**command completion**." Bounding `umask()` / `Log()` / argv
marshaling was never the contract. A promise that "timed out during
setup" under the old code did not time out the command: it burned
the alarm on `ALARM_PID == -1` and then ran the command with no
timer. That is the bug. After this change those promises get the
full `exec_timeout` on the command. They run longer because the
timeout now does what the manual says.

A user-visible changelog line is still warranted.
`CONTRIBUTING.md` says a changelog entry "explains the impact to
users" and that "references to implementation details are not
appropriate." `Changelog: Commit` dumps the whole body — `ALARM_PID`,
`StartTimeOutClock()`, MinGW pipes — into `CHANGELOG.md`. That is
the opposite of the project's own rule.

Use `Changelog: Title` (the title is already past tense and close
to user-facing) or, better:

```
Changelog: Fixed exec_timeout being consumed before the command started, leaving the command running with no timeout
```

Optional relative to safety. I would still change it before the PR;
maintainers notice changelog noise.

---

## U8 — test coupling

Acceptable. Do not move the discriminator to acceptance-only.

`timeout_test` already links `../../libpromises/libpromises.la`
(`tests/unit/Makefile.am:42`), which includes `pipes_unix.c` on this
build. `#include <pipes.h>` and one `cf_popen()` do not add a new
link dependency. They exercise the production arming order
(`ALARM_PID` then `StartTimeOutClock()`) instead of a test-only
`StartTimeOutClock()` call.

`test_clock_does_not_run_before_the_fork` is the test that would
have failed the old `SetTimeOut()`. It waits twice the timeout
before forking, then runs `/bin/sleep 5` against a 1 s budget. That
is a behavioural pin, not an API-existence check. Putting it only
in `08_commands/04_exec_timeout` would still be valuable and would
not prove that `SetTimeOut()` itself leaves the clock stopped — the
acceptance tests never wait out the timeout *before* the command.

The coupling is the price of pinning the race at the unit layer.
Worth it. Optional follow-up: a thinner helper that is not
`cf_popen` but still goes through `GenericCreatePipeAndFork` is
unnecessary complexity.

---

## Out of scope — leaked timeouts, with one new observation

The known leak family is still there: `verify_exec.c:374` (popen
fail), `verify_exec.c:391–393` (read error), `nfs.c:405–409`
(popen fail), and `nfs.c:1434` / `:1459` (no `ClearTimeOut()` even
on success). Do not fold a leak cleanup into this commit.

The commit message claims a leaked armed timeout "now goes inert
instead of firing into a later, unrelated child." That is false,
and this change makes the leak *more* reliable at killing the wrong
child.

After a `SetTimeOut()` that never reaches a successful
`GenericCreatePipeAndFork()`, POSIX now has `TIMEOUT_ARMED == 1`,
`TIMEOUT_PENDING == timeout`, and no kernel timer. The next
unrelated `cf_popen` — `ps` in `processes_select.c`, `execresult()`,
`getent` via `unix.c:298` — hits `StartTimeOutClock()`, starts a
**full** budget, and registers *that* child in `ALARM_PID`.

Before: the leaked `alarm()` was already ticking from `SetTimeOut()`.
If it expired while `ALARM_PID == -1`, `TimeOut()` logged and the
leak was spent. If a later child appeared first, that child could
die, but only on the *remaining* seconds.

After: a leak that would have expired harmlessly is revived in full
against the next pipe child.

That is not a reason to redesign the choke point — starting the
clock anywhere other than immediately after `ALARM_PID = pid`
reopens the original race. It is a reason not to tell maintainers
the leak got safer. Fixing the leaks is a follow-up (and
`nfs.c:1434`/`1459` still leave `TIMEOUT_ARMED` set after a
*successful* remount, which is the process-group leak, not this
ticket).

---

## Required changes

Do not push upstream without these:

1. **Condition the immediate-arm path on the same platforms that
   do not compile `pipes_unix.c`.** `__MINGW32__` alone leaves
   Cygwin on the POSIX `SetTimeOut()` with no starter. Use
   `__MINGW32__ || __CYGWIN__`, or a dedicated feature macro
   equivalent to Makefile `NT`. Do not invert this into
   "defer everywhere and fix Windows later."

2. **Remove or invert the "leaked timeout goes inert" sentence
   in the commit message** (and any comment that repeats it).
   State what the code actually does: a `SetTimeOut()` not
   followed by a successful `cf_popen` leaves `TIMEOUT_PENDING`
   set, and the next `GenericCreatePipeAndFork()` will start that
   budget against whatever it forks. The leak family is
   pre-existing; this commit must not claim it is now safe.

## Optional changes

- Rewrite `test_start_runs_the_clock_once` so the second
  `StartTimeOutClock()` is issued against a still-running clock
  (U4).
- Make `TIMEOUT_PENDING` a `volatile sig_atomic_t` (U6).
- Replace `Changelog: Commit` with `Changelog: Title` or a
  one-line user-facing `Changelog:` (U7).
- Do not add a history.c file-branch starter. The timeout there
  is dead (U1).

---

VERDICT: SHIP-WITH-CHANGES
