# UPSTREAM REVIEW BRIEF — B-1 and B-2, CFEngine core

**Frozen input, 2026-08-16.** This is the shared prompt given verbatim to each
member of the second-opinion panel. Do not edit it to reflect what the reviews
later found — the reviews are separate files, and the register records the
outcome.

Required by `upstream-register.md`: **no item is emailed upstream until it has
been second-opinioned and its fork issue updated with whatever the review
found.** Both items below were filed before that rule existed.

---

## Your role

You are an independent reviewer of two C patches that are about to be offered
to an upstream open-source project (CFEngine Core, by Northern.tech). They were
written by a different AI model. Your job is **adversarial**: assume the patches
are wrong and try to demonstrate it. A review that finds nothing is a valid
outcome, but only after a real attempt.

The author's own uncertainties are listed at the bottom. Address each of them
explicitly and by name. Do not simply agree with the author's framing of them —
the framing may itself be the error.

## Where the code is

Repository: `~/src/cfengine-core` — a fork of `cfengine/core`, currently checked
out on branch `tendcf-integration`, which merges both fixes. Upstream `master`
in that clone is at `17eb78e6d`; both fixes branch from it.

```
git -C ~/src/cfengine-core show 26634ac1f      # B-1
git -C ~/src/cfengine-core show cb2561584      # B-2
git -C ~/src/cfengine-core diff 17eb78e6d..tendcf-integration
```

Read the surrounding files, not just the diffs:

- `libpromises/process_unix.c` — B-1's poll loops
- `libpromises/process.h`, `libpromises/process_unix_stub.c` — `GetProcessState()`
  and why macOS uses the stub
- `tests/unit/process_terminate_unix_test.c` — B-1's test change
- `libpromises/pipes_unix.c` — B-2's `setpgid()`, in `GenericCreatePipeAndFork()`
- `libpromises/timeout.c` — B-2's `TimeOut()` sweep
- `libpromises/locks.c` — the other caller of `GracefulTerminate()`

You have read access to the whole repo and the web. **Write nothing except your
own output file. Do not commit, push, branch, or modify any existing file.**

## The two defects

### B-1 — poll loops count iterations instead of measuring elapsed time

`ProcessWaitUntilStopped()` and `ProcessWaitUntilExited()` in
`libpromises/process_unix.c` take a timeout in nanoseconds and budget it by
subtracting `SLEEP_POLL_TIMEOUT_NS` (10 ms) once per iteration — i.e. they
assume every `nanosleep()` costs exactly what was requested. POSIX only
guarantees `nanosleep()` sleeps *at least* as long as requested.

Measured on Darwin/arm64: a `nanosleep(10 ms)` request routinely takes ~45 ms
(100 iterations standalone = 4.41–4.66 s). So `STOP_WAIT_TIMEOUT`, documented as
"no more than … one second", really waits ~4.5 s, and `GracefulTerminate()`'s
SIGINT → SIGTERM → SIGKILL ladder takes ~8.9 s instead of ~2 s. Instrumented
build, before the fix:

```
GT: SIGINT sent at 0.000s
wait: TIMED OUT after 4.459s, 100 iters -> false
GT: SIGTERM sent at 4.460s
wait: TIMED OUT after 4.457s, 100 iters -> false
GT: SIGKILL sent at 8.917s -> true
```

**Why it matters (the reason this is being reported to security@):** in a
`commands:` promise with `exec_timeout`, the timeout fires but the ladder is so
slow that a command finishing during it is reaped normally and reported as
**promise KEPT** — indistinguishable from success. A policy that keys a class
off `kept_returncodes` to guard a later promise therefore treats "the check
timed out" as "the check passed". This is a **fail-open**. Reproduced 5/5 with
`sleep 5` under `exec_timeout => "2"`.

**The fix:** both loops compute a deadline from a monotonic clock and re-check
actual elapsed time each iteration, using the same `CLOCK_MONOTONIC`-with-
`CLOCK_REALTIME`-fallback pattern as `EvalContextEventStart()` in
`eval_context.c`.

### B-2 — descendants are not signalled on timeout

`TimeOut()` calls `GracefulTerminate(ALARM_PID, …)`, which signals only the
process CFEngine started. Anything that process spawned survives, still holding
the write end of the pipe, so the parent stays blocked in its read loop on a
command it has already given up on. `exec_timeout` therefore does not bound the
promise's wall clock at all. This is the ordinary case, not an exotic one — any
script that runs another program has this shape:

```
body contain c { useshell => "noshell"; exec_timeout => "2"; }
bundle agent t
{
  commands:
      "/bin/sh" arglist => { "-c", "sleep 30; exit 0" }, contain => c;
}
```

Before: 30.3 s, `sleep` orphaned. After: 5.2 s, no orphan. With
`trap '' INT TERM; sleep 30`: 30.3 s → 4.4 s.

**The fix:** `cf_popen()`'s child calls `setpgid(0, 0)` so the command and its
descendants form a group; `TimeOut()` reads the process group *before*
`GracefulTerminate()` and `kill(-pid, SIGKILL)`s the group after, guarded on
`pgid == pid`.

Reading the pgid first is not cosmetic. An earlier version of this fix read it
after termination, where `getpgid()` returns **ESRCH**, so the guard was always
false, the sweep never ran, and the fix looked like a non-fix.

## Uncertainties the author flagged — address each by name

1. **`setpgid` versus Ctrl-C.** `setpgid(0,0)` applies to *every* `cf_popen()`
   child, not only those with an `exec_timeout`. That detaches children from the
   agent's process group, so a terminal SIGINT (Ctrl-C) sent to the foreground
   process group no longer reaches a running child. The author judged this
   invisible for non-interactive agent runs and preferred it to making the
   timeout path structurally different from the normal path. Is that the right
   call? Consider `cf-runagent`, `cf-agent` run interactively from a shell,
   `cf-execd`'s children, and any caller of `cf_popen`/`cf_popensetuid` — the
   set of affected call sites is larger than `commands:` promises, and the
   review should establish how much larger. Consider also whether losing job
   control breaks anything else (SIGTSTP, orphaned process groups, terminal
   ownership, `SIGHUP` on terminal close).

2. **The unconditional group SIGKILL.** After the leader has been through the
   graceful ladder, the group gets a flat `SIGKILL` with no escalation. Gentler
   would be to escalate over the group, but that would change
   `GracefulTerminate()`, which is shared with the stale-lock path in
   `locks.c`, where group semantics are wrong. Is the unconditional kill
   acceptable, and is the shared-function argument actually true? Is there a
   race between `GracefulTerminate()` returning and the group kill in which the
   pid could be recycled — and does the `pgid == pid` guard, read before
   termination, actually close it?

3. **The test's clock mock.** `process_terminate_unix_test.c` mocks
   `nanosleep()` and advances a fake clock by the *requested* sleep — precisely
   the accounting B-1 removes. B-1's fix genuinely broke that test (1/6; the
   baseline was 6/6, confirmed by stashing the patch). The patch therefore also
   makes the fake clock drive `clock_gettime()`. Is overriding `clock_gettime()`
   process-wide in a unit test acceptable, or does it risk breaking unrelated
   code linked into the same binary? Is there a less invasive way to express the
   same test intent? Does the amended test still test what it was written to
   test, or has it been weakened to fit the patch?

## Also worth checking, unprompted

- Is B-1's monotonic-clock helper correct on platforms without
  `CLOCK_MONOTONIC`, and is the `#ifdef` fallback the right one? Does
  `clock_gettime` need a link-time guard on any supported platform?
- Integer types and overflow in the deadline arithmetic (`long timeout_ns` vs
  `int64_t`), and the `assert(timeout_ns < 1000000000)` that B-1 leaves in place.
- Whether removing `while (timeout_ns > 0)` changes behaviour for a caller
  passing `timeout_ns <= 0` — the loop body now runs at least once.
- Whether `setpgid(0,0)` can fail, and what happens if it does (the return value
  is not checked).
- Anything in `CONTRIBUTING.md`'s code-style and commit-hygiene rules that these
  commits violate. (Its *process* section is deliberately not followed — the
  operator's instruction — but style and hygiene still apply.)
- Whether either patch would be better split, or whether either is doing two
  things at once.

## Deliverable

Write **one file**: `docs/architecture/upstream-opinion-<your-slug>-2026-08-16.md`
in `~/src/tendcf`, where `<slug>` is given in your launch prompt.

Structure it as:

1. **Verdict per item** — for B-1 and B-2 separately, one of: *ship as is*,
   *ship with changes* (list them), *do not ship* (say why).
2. **Defects found**, each with the file and line, what breaks, and how to
   reproduce or demonstrate it. Distinguish what you verified from what you
   suspect.
3. **The three flagged uncertainties**, answered by name and number.
4. **Anything the author missed**, including whether the *diagnosis* is right,
   not just the fix — if the real mechanism is something else, say so.
5. **What you did not check**, so the gap is visible rather than assumed covered.

**Independence:** do not read any other `upstream-opinion-*.md` file, and do not
read `docs/handoffs/`. You may read anything else in either repo. Prefer
verifying against the code and, where you can, by building or running something
— assertions about C semantics are cheap and this review exists because two
earlier readings by the author were confidently wrong.
