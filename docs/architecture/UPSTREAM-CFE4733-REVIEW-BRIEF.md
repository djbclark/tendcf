# Review brief — CFE-4733 (B-16): `ShellCommandReturnsZero()` never resets `ALARM_PID` after reaping

Frozen 2026-08-18. Worktree `/Users/djbclark/src/core-alarmreset`, branch
`fix/alarm-pid-reset-after-reap`, based on **upstream master `a0bca6aaf`**,
commit `e7fd46c6d`. Upstream: `cfengine/core`. Jira: CFE-4733, Open, 0 comments
(ticket text matches current master exactly, no line drift this time —
verified before patching).

## 1. The defect as filed

`libpromises/unix.c:166` `ShellCommandReturnsZero()` sets `ALARM_PID = pid` at
`:225` (parent, after fork), then reaps the child at `:238` (`waitpid`
`WNOHANG` poll loop, normal exit) or `:258` (blocking drain, on the
pending-termination path). Neither reap site resets `ALARM_PID`. The only
`ALARM_PID = -1` in the function is at `:184`, in the *child*, before exec —
irrelevant to the parent's copy.

Once reaped, the pid is immediately recyclable. The usual reassurance for a
stale `ALARM_PID` — "the process is still an unreaped zombie holding its
slot" — does not hold here, because this call site is the one that reaps.
A leaked alarm from elsewhere (CFE-4732, or the `verify_exec.c` /
`nfs.c:403`/`history.c` error-path family) firing after this call, before
anything else rewrites `ALARM_PID`, runs `TimeOut()` against a pid that may
now name an unrelated process. `cf-agent` typically runs as root.

## 2. The fix

Two insertions, one per reap site, matching the file's existing
`ALARM_PID = -1` idiom at `:184`:

```c
            if (wait_result == pid)
            {
                ALARM_PID = -1; /* reaped: pid can be recycled, stop naming it */
                break;
            }
```

```c
                while (waitpid(pid, &status, 0) < 0 && errno == EINTR)
                {
                    /* Child has been signalled; just reap it. */
                }
                ALARM_PID = -1; /* reaped: pid can be recycled, stop naming it */
                return false;
```

**Q1.** Are there exactly two reap sites, or did I miss one? Walk the whole
function against `a0bca6aaf`.

**Q2.** The third return point, `:249` (`wait_result < 0` and `errno !=
EINTR`, i.e. `waitpid()` itself failed) — I left this one alone: no reap
happened there, so the zombie-holds-the-slot reasoning the ticket itself
relies on still applies, and resetting `ALARM_PID` there would be wrong
(the child may still exist). Agree or disagree?

**Q3.** Any reachable path where `ALARM_PID` is reset to `-1` *without* the
child actually having been reaped (a false negative that would let a
still-live child recycle nothing, but silently drop the "this call is
outstanding" signal a concurrent alarm might depend on)? I don't see one —
both insertions are immediately after their respective successful
`waitpid()` calls, not before.

## 3. Test — and why I think it's actually testable this time

Unlike CFE-4732's `ReconcileMountOptions()` (`static`, needs `EvalContext`/
`Promise`, executes a real mount), `ShellCommandReturnsZero()` is exported
(declared in `exec_tools.h`, called from `evalfunction.c`, `generic_agent.c`,
`verify_processes.c`, `files_select.c`) and only needs a command string and a
`ShellType`. Added `tests/unit/unix_test.c` (mirrors `nfs_test`'s `if !NT`
guard and `libpromises.la` linkage), two cases:

- `ShellCommandReturnsZero("true", SHELL_TYPE_USE)` → asserts `ALARM_PID ==
  -1` after a successful exit.
- `ShellCommandReturnsZero("false", SHELL_TYPE_USE)` → asserts `ALARM_PID ==
  -1` after a nonzero exit (same reap site, different return value).

Both exercise the `:238` WNOHANG-break path (the common case); neither
exercises the `:258` pending-termination path (would need a real `SIGTERM`
delivered mid-poll and a registered handler setting `PENDING_TERMINATION` —
judged too timing-fragile for CI, so not attempted; flagging this rather
than silently skipping it).

Discrimination run by hand, not asserted: `git stash` on just `unix.c`,
rebuilt `libpromises` (full `make`, not just the `.lo` — the first attempt at
this reused a stale archived `.la` and both tests passed against the
*unpatched* code, which would have been a faked negative result; forcing a
full library rebuild before relinking the test surfaced the real failure),
relinked `unix_test`: both cases failed (`ALARM_PID` observed as the
reaped/exited child's literal pid, not `-1`). Restored the fix, rebuilt,
both pass. Full top-level `make -j4` afterwards, clean, no new warnings.

**Q4.** Is the `:258` gap (pending-termination path untested) acceptable to
ship with, or does it need a real test before this lands? I lean acceptable
— it's the rarer path (requires `IsPendingTermination()` true mid-poll,
i.e. a `SIGTERM` arriving while a shell command promise/function is
running), and both reap sites get the *same* one-line fix, so the risk of
the untested one being wrong while the tested one is right is low, but
argue me out of it if you disagree.

## 4. Out of scope

- `:249` (see Q2) — not part of this ticket, no reap occurs there.
- The other `ALARM_PID`/timeout leak family members (CFE-4732, the
  `verify_exec.c`/`nfs.c`/`history.c` error paths) — separate tickets.
- Whether polling with `nanosleep()` instead of blocking `waitpid()` is the
  right design — pre-existing, not touched.

End with an explicit verdict line: **SHIP**, **SHIP-WITH-CHANGES**, or
**DO-NOT-SHIP**. No public correction is being posted this time (the filed
ticket's severity and line numbers both check out against current master),
so there is no second "SAFE TO POST" line needed — just the ship verdict.
