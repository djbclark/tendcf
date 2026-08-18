# UPSTREAM REVIEW BRIEF — CFE-4735, cf_popen*() fdopen()-failure ALARM_PID leak

**Frozen input, 2026-08-18.** This is the shared prompt given verbatim to each
member of the second-opinion panel. Do not edit it to reflect what the reviews
later find — the reviews are separate files, and the register records the
outcome.

---

## Your role

You are an independent reviewer of a small C fix that is about to be offered
to an upstream open-source project (CFEngine Core, by Northern.tech). It was
written by a different AI model. Your job is **adversarial**: assume the fix
is wrong and try to demonstrate it. A review that finds nothing is a valid
outcome, but only after a real attempt.

This is a **small delta on top of CFE-4727** (already shipped as
`djbclark/core@8f4ebedbd`, `fix/exec-timeout-alarm-pid`), reusing that
commit's `ClearAlarmedPid()` helper. Read CFE-4727's own review documents
first for context — `docs/architecture/upstream-opinion-cfe4727-{gemini31pro,grok,fabledeep}-2026-08-18.md`
in this repo — rather than re-deriving what that commit already established.

## Where the code is

Repository: `/Users/djbclark/src/core-alarmleak`, a worktree of a fork of
`cfengine/core`, on branch `fix/exec-timeout-alarm-leak`, one commit
(`89379323d`) ahead of `8f4ebedbd` (CFE-4727's tip).

```
git -C /Users/djbclark/src/core-alarmleak log --oneline -3
git -C /Users/djbclark/src/core-alarmleak show 89379323d
```

Read the surrounding files, not just the diff:

- `libpromises/pipes_unix.c` — `GenericCreatePipeAndFork()` (where `ALARM_PID`
  is published, unchanged by this commit), the four `cf_popen*()` parents
  (`cf_popen_select`, `cf_popensetuid`, `cf_popen_sh_select`,
  `cf_popen_shsetuid`) and their fdopen()-failure branches, `ClearAlarmedPid()`
  (CFE-4727's helper, unchanged here except the new forward declaration),
  `cf_pwait()`
- `cf-agent/verify_exec.c` — `RepairExec()` in full, both the new
  `pfp == NULL` branch and the pre-existing normal-completion `ClearTimeOut()`
  call this new one is modeled on

You have read access to the whole repo and the web. **Write nothing except
your own output file. Do not commit, push, branch, or modify any existing
file.**

## What the defect was

CFE-4727 fixed `cf_pclose()`/`cf_pclose_full_duplex()` so `ALARM_PID` stays
registered until the child is reaped, then clears it via `ClearAlarmedPid()`.
That helper was wired into those two closers only. The four `cf_popen*()`
parents have their own failure path, structurally identical eight times
(twice per function, once per pipe direction): if `fdopen()` fails on the
pipe fd `pipe()`+`fork()` just produced, each does `cf_pwait(pid); return
NULL;` — reaping the child but never producing a `FILE*` the caller could
later `cf_pclose()`. `ALARM_PID`, published by `GenericCreatePipeAndFork()`
right after the fork, was never cleared on this path — the alarm stays
pointed at a reaped, recyclable pid.

`RepairExec()` compounded it: when any `cf_popen*()` call returns `NULL`
(line 371 in the pre-fix source), it logs and returns
`ACTION_RESULT_FAILED` without reaching the function's only
`ClearTimeOut()` call (further down, on the normal-completion path). If a
timeout was armed for the promise, it stays armed with `ALARM_PID` stale.

## What the fix does

Eight call sites in `pipes_unix.c` (`cf_popen_select` at lines ~458/470,
`cf_popensetuid` at ~588/600, `cf_popen_sh_select` at ~670/681,
`cf_popen_shsetuid` at ~789/800 in the parent commit) each gain a
`ClearAlarmedPid(pid);` call immediately after `cf_pwait(pid);`. A new
forward declaration (`static void ClearAlarmedPid(pid_t pid);`, added next
to the existing `cf_pwait` forward declaration) makes the `static` helper
visible to these call sites, which all precede its definition later in the
file.

`RepairExec()`'s `pfp == NULL` branch in `verify_exec.c` gains:
```c
if (a->contain.timeout != CF_NOINT)
{
    ClearTimeOut();
}
```
before its `return ACTION_RESULT_FAILED;`, matching the exact gate the
function's normal-completion `ClearTimeOut()` call already uses.

## What the review must attack

1. **Correctness of the forward declaration and the eight insertions.**
   Is `ClearAlarmedPid(pid)` called with the *right* `pid` at every site —
   the same `pid` that `cf_pwait()` was just called with, matching the pid
   `GenericCreatePipeAndFork()` published? Check each of the eight sites
   individually; they are copy-pasted and a wrong-variable slip in one would
   be easy to miss by eye.
2. **Ordering.** `ClearAlarmedPid()` must run *after* `cf_pwait()`'s reap
   (matching CFE-4727's own established invariant — clearing before the reap
   would reopen the exact bug CFE-4727 fixed, on a new set of call sites).
   Confirm the insertion point in all eight cases.
3. **Is there a path where this now clears an `ALARM_PID` it shouldn't?**
   `ClearAlarmedPid()`'s guard (`if (ALARM_PID == pid) { ALARM_PID = -1; }`)
   protects against clearing a *different*, more-recently-registered pid.
   Attack whether any of these eight call sites could run when `ALARM_PID`
   already names something else — e.g. could a second `cf_popen*()` call
   happen concurrently (same thread reentrancy, or a different thread) such
   that this clear fires against a *newer* registration than the one that
   just failed? Is that guard sufficient here the same way it was sufficient
   for the two closers?
4. **`RepairExec()`'s new `ClearTimeOut()` call.** Is `a->contain.timeout !=
   CF_NOINT` definitely the same condition under which `SetTimeOut()` was
   armed for this call (line 308 in the pre-fix source)? Could `pfp == NULL`
   be reached on a path where `SetTimeOut()` was never called at all, making
   this a no-op `ClearTimeOut()` — safe, per `timeout.c`'s own contract that
   `ClearTimeOut()` is idempotent — or could it be reached in a state where
   calling it is actively wrong (e.g. clearing a *different*, unrelated
   promise's armed timeout)? `RepairExec()` runs promise-at-a-time,
   single-threaded per agent run — verify that assumption rather than taking
   it as given.
5. **Untested-branch claim.** The commit message asserts fdopen() failure on
   a fd `pipe()`+`fork()` just produced is impractical to force
   deterministically in a portable test, and that the pre-existing
   `fd >= MAX_FD` branch in `cf_pclose()` is in the same untested position
   for the same reason. Verify both halves of that claim: is there in fact
   no practical way to construct a discriminating test here (try, if you
   have an idea — `RLIMIT_NOFILE` manipulation, an `LD_PRELOAD`/`DYLD_INSERT_LIBRARIES`
   stub, anything), and is the `fd >= MAX_FD` comparison actually accurate?
6. **Blast radius if this is wrong.** If `ClearAlarmedPid(pid)` fired with
   the wrong `pid`, or fired when it shouldn't, what's the worst case? Trace
   it through to `TimeOut()`'s `Kill()` call the way CFE-4727's own review
   did for the closers.

## Traps you must control for

1. **Never read a return code through a pipe.** Write `echo "RC=$?"` to a
   file immediately after any command you compile/run; use distinct output
   filenames.
2. **This build needs an explicit `--prefix` and `make install`, not just
   `make`.** A bare `./autogen.sh` in a fresh worktree defaults to
   `/var/cfengine` and the resulting binaries fail at runtime with a `dyld`
   "Library not loaded" error unless installed there or run with
   `DYLD_LIBRARY_PATH` pointing at the in-tree `.libs/` directories. This
   session used `./configure --prefix=/Users/djbclark/opt/cfengine-dev-4735
   --with-openssl=/opt/homebrew/opt/openssl@3
   --with-pcre2=/opt/homebrew/opt/pcre2 --with-lmdb=/opt/homebrew/opt/lmdb
   --with-libyaml=/opt/homebrew/opt/libyaml --enable-maintainer-mode` then
   `make install` to that prefix. Use a **different** prefix than
   `~/opt/cfengine-dev-4727` (CFE-4727's own install) if you install this
   worktree too, so the two don't clobber each other.
3. **`cf-promises` in the build tree is a libtool wrapper script**, not the
   binary; the real one is `cf-promises/.libs/cf-promises`.
4. **Platform.** macOS 26.6.1 (25G76), arm64. Tag claims measured vs
   reasoned.

## What the author actually did

One commit, `89379323d`, on `fix/exec-timeout-alarm-leak` (2 files, 13
insertions, 0 deletions — pure addition, no line removed or changed).

Build: incremental and full rebuild both 0 warnings. Unit tests:
`tests/unit/timeout_test`, **7/7 pass**, unchanged from CFE-4727's own
result (this commit touches no code any existing unit test exercises
directly). Acceptance: all 6 tests in
`tests/acceptance/08_commands/04_exec_timeout/`, **6/6 pass, 89s**, via
`./testall --gainroot=env --agent=... --cfpromises=... --cfserverd=...
08_commands/04_exec_timeout` against the freshly configured+installed
build. No regression on any reachable path.

No discrimination was performed (see attack point 5 — the author's position
is that none is practically constructible) and no new test was added.

## The author's uncertainties

Address each explicitly and by name.

1. **No discriminating test exists for either new code path** (the eight
   `ClearAlarmedPid()` calls, or `RepairExec()`'s new `ClearTimeOut()`).
   The author judged constructing one impractical (see attack 5) rather
   than attempting something fragile. Agree or disagree, and if you
   disagree, say what you would actually build.
2. **The forward declaration adds `ClearAlarmedPid` to file-scope
   visibility earlier than before.** It was `static`, defined once, used
   only from the two closers, both later in the file. Now it's forward-
   declared at the top and used from code that runs *before* `cf_pclose()`
   would ever be reachable for that same pipe. Is there any static-analysis
   or maintainability concern with this pattern the author should have used
   instead (e.g., moving the function definition earlier, or a header
   declaration)? CFEngine's own `cf_pwait()` already uses the identical
   forward-declaration pattern one line above, which is why the author
   matched it — is that precedent actually a good one to follow here?

## Pre-existing defects the author found and deliberately did not fix

None new. This commit is a direct, mechanical extension of CFE-4727's own
fix to eight structurally identical error paths CFE-4727's review already
named as the same defect class (fable-deep's finding under CFE-4727's
attack point 5). Nothing else was found or deferred while making this
change.
