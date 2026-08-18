# Review brief — CFE-4734 (B-18): `exec_timeout` armed its alarm before the child existed

Frozen 2026-08-18. Review target: commit **`92531d60cc87885053aadd7889e384f0435e7e77`**
on branch `fix/exec-timeout-prefork-race` in worktree `/Users/djbclark/src/core-prefork`.
Base: `dbf759d16` (a *sibling* of the B-17 and B-19 branches, not stacked on them).
Local only — nothing is pushed. Upstream project: `cfengine/core`. Jira: CFE-4734, Open, 0 comments.

You are reviewing a fix that is already implemented and tested. The question is
**ship / ship-with-changes / do-not-ship**, and specifically whether this change is
safe and correct enough to put in front of CFEngine maintainers.

---

## 1. The defect

`SetTimeOut(int timeout)` in `libpromises/timeout.c` called `alarm(timeout)`
immediately. But the process the alarm is supposed to kill is only registered in
the global `ALARM_PID` **after** `fork()`, in `GenericCreatePipeAndFork()`
(`libpromises/pipes_unix.c:272`).

Between those two points the caller does real work. At `cf-agent/verify_exec.c:308`
the arm site is followed by `umask()`, two `Log()` calls, shell-type dispatch and
argument marshaling before `cf_popen*()` is even entered
(`verify_exec.c:311–366`); the `nfs.c` and `cf-monitord/history.c` sites are
similar.

If `SIGALRM` is delivered in that window, `TimeOut()` (`timeout.c:110`) finds
`ALARM_PID == -1`, takes the `else` branch, logs `"Time out"`, sets
`TIMEOUT_FIRED = 1` and `TIMEOUT_ARMED = 0` — and kills nothing. The alarm is
consumed. The command then forks and **runs to completion with no timeout at
all**, which is precisely the guarantee `exec_timeout` exists to provide.

This was not theorised from reading. It was observed as a real flake in
`tests/unit/timeout_test` under parallel `make check` load.

## 2. The fix as implemented

`SetTimeOut()` stops arming the clock. It still sets the flags and installs the
handler, but calls `alarm(0)` and stashes the requested seconds in a new
`static int TIMEOUT_PENDING`. A new `StartTimeOutClock()` starts the real timer,
and `GenericCreatePipeAndFork()` calls it immediately after `ALARM_PID = pid`,
guarded on `pid > 0`.

`StartTimeOutClock()` is one-shot: it consumes `TIMEOUT_PENDING`, so a second
fork under a single `SetTimeOut()` runs on the time already ticking rather than
restarting the command's budget. `ClearTimeOut()` also zeroes `TIMEOUT_PENDING`,
so a timeout that is cleared before any fork cannot later be started.

Under `__MINGW32__`, `SetTimeOut()` still calls `alarm(timeout)` directly: the
Windows pipe implementation lives outside this tree and could never call the
starter, so deferring there would silently disable `exec_timeout` on Windows.

`TIMEOUT_ARMED` is still set **before** the fork, so `TimeOutIsArmed()` — which
the child consults to decide whether it needs a process group of its own — is
unchanged either side of the fork.

### Accepted, stated cost

A timeout that is armed but never followed by a fork now **never fires**. This is
stated in the commit message rather than hidden. The author's argument for it
being net-safer: today such a leaked alarm can fire while a *later, unrelated*
child is registered in `ALARM_PID` and kill that child; under the fix it degrades
to an inert flag. Uncertainty 1 below asks you to test that argument, because
there is at least one call site where it may not hold.

## 3. Facts you should not have to re-derive (but may verify)

`SetTimeOut()` has **six** production callers, not one:

| site | forks via `cf_popen*()`? |
|---|---|
| `cf-agent/verify_exec.c:308` | yes |
| `cf-agent/nfs.c:403` | yes, `cf_popen` at `:405` |
| `cf-agent/nfs.c:1121` | yes, `cf_popen` at `:1125` |
| `cf-agent/nfs.c:1434` | yes, `cf_popen` at `:1436` |
| `cf-agent/nfs.c:1459` | indirectly — `VerifyUnmount()` (`cf_popen` at `:1008`) then `VerifyMount()` (`cf_popen` at `:940`), i.e. **two** forks under one `SetTimeOut()` |
| `cf-monitord/history.c:242` | **depends on the branch taken** — see uncertainty 1 |

`ALARM_PID` is assigned in exactly two production places: `pipes_unix.c:272`
(`GenericCreatePipeAndFork`, which every `cf_popen*` variant routes through) and
`libpromises/unix.c:225` (`ShellCommandReturnsZero`, which forks directly and does
**not** go through `GenericCreatePipeAndFork`). The author scoped
`ShellCommandReturnsZero` out on the grounds that it arms nothing itself.

`ClearTimeOut()` is called from `nfs.c:581`, `nfs.c:1177`, `verify_exec.c:502`,
`history.c:377` — none of them a signal handler. `TimeOut()` does not call it.

An earlier version of this brief claimed `SetTimeOut()` had exactly one caller.
That was wrong (a `grep -v "^./tests/"` filter that never matched, plus a
truncating `head -20`) and it changed the design: the clock start had to be
centralized in `GenericCreatePipeAndFork()` rather than placed at one call site.
It is corrected here. Do not trust a claim in this brief you can cheaply check.

## 4. The diff

```
diff --git a/libpromises/pipes_unix.c b/libpromises/pipes_unix.c
index 71dc90266..163783290 100644
--- a/libpromises/pipes_unix.c
+++ b/libpromises/pipes_unix.c
@@ -271,6 +271,15 @@ static pid_t GenericCreatePipeAndFork(IOPipe *pipes)
 
     ALARM_PID = (pid != 0 ? pid : -1);
 
+    if (pid > 0)
+    {
+        /* Only now is there a process for TimeOut() to terminate. Starting the
+         * clock any earlier -- as SetTimeOut() used to -- lets the alarm fire
+         * in the window before this assignment, where it finds nothing
+         * registered and the command then runs unbounded. */
+        StartTimeOutClock();
+    }
+
     return pid;
 }
 
diff --git a/libpromises/timeout.c b/libpromises/timeout.c
index dccdb466a..f9b39de06 100644
--- a/libpromises/timeout.c
+++ b/libpromises/timeout.c
@@ -43,6 +43,11 @@ static volatile sig_atomic_t TIMEOUT_SIGNALLED = 0; /* GLOBAL_X */
  * well as from ClearTimeOut(), hence volatile sig_atomic_t. */
 static volatile sig_atomic_t TIMEOUT_ARMED = 0; /* GLOBAL_X */
 
+/* Seconds requested by SetTimeOut(), held until StartTimeOutClock() arms the
+ * real timer once cf_popen() has a pid to kill. Not touched from the
+ * handler. */
+static int TIMEOUT_PENDING = 0; /* GLOBAL_X */
+
 void SetTimeOut(int timeout)
 {
     ALARM_PID = -1;
@@ -50,7 +55,28 @@ void SetTimeOut(int timeout)
     TIMEOUT_SIGNALLED = 0;
     TIMEOUT_ARMED = 1;
     signal(SIGALRM, (void *) TimeOut);
+#ifdef __MINGW32__
+    /* The Windows pipe implementation is outside this tree and cannot start
+     * the clock at the fork, so keep starting it here. */
     alarm(timeout);
+#else
+    /* Hold the clock until there is a process registered to terminate. Cancel
+     * any timer leaked by an earlier caller first, so it cannot fire as ours. */
+    alarm(0);
+    TIMEOUT_PENDING = timeout;
+#endif
+}
+
+void StartTimeOutClock(void)
+{
+    /* One-shot: a second fork under the same timeout runs on the time already
+     * ticking, rather than restarting the command's budget. */
+    if ((TIMEOUT_ARMED != 0) && (TIMEOUT_PENDING > 0))
+    {
+        int seconds = TIMEOUT_PENDING;
+        TIMEOUT_PENDING = 0;
+        alarm(seconds);
+    }
 }
 
 void ClearTimeOut(void)
@@ -61,6 +87,7 @@ void ClearTimeOut(void)
     alarm(0);
     signal(SIGALRM, SIG_DFL);
     TIMEOUT_ARMED = 0;
+    TIMEOUT_PENDING = 0;
 }
 
 bool TimeOutIsArmed(void)
diff --git a/libpromises/timeout.h b/libpromises/timeout.h
index a0738df71..c73264e2e 100644
--- a/libpromises/timeout.h
+++ b/libpromises/timeout.h
@@ -25,8 +25,16 @@
 #ifndef CFENGINE_TIMEOUT_H
 #define CFENGINE_TIMEOUT_H
 
+/* Arm a timeout, but leave its clock stopped: on POSIX the alarm is started by
+ * StartTimeOutClock() once there is a child to terminate. */
 void SetTimeOut(int timeout);
 
+/* Start the clock armed by SetTimeOut(). Called by cf_popen() right after the
+ * child's pid reaches ALARM_PID, so an alarm can never be pending with nothing
+ * registered to kill. No-op when no timeout is armed, or when the clock is
+ * already running. */
+void StartTimeOutClock(void);
+
 /* Cancel a pending alarm and restore the default handler. Callers used to
  * open-code this; it also has to clear the armed flag, so that a command which
  * completes in time does not leave it set for the next, unrelated, child. It
@@ -34,9 +42,11 @@ void SetTimeOut(int timeout);
  * that record stays readable after the disarm, until the next SetTimeOut(). */
 void ClearTimeOut(void);
 
-/* True between SetTimeOut() arming the alarm and the alarm being disarmed.
- * Consulted by code that forks a child which the timeout may have to
- * terminate, to decide whether that child needs a process group of its own. */
+/* True between SetTimeOut() arming the timeout and it being disarmed, whether
+ * or not its clock has started. Consulted by code that forks a child which the
+ * timeout may have to terminate, to decide whether that child needs a process
+ * group of its own -- a question that has the same answer either side of the
+ * fork that starts the clock. */
 bool TimeOutIsArmed(void);
 
 /* True if the alarm armed by the last SetTimeOut() actually fired. Lets a
diff --git a/tests/unit/timeout_test.c b/tests/unit/timeout_test.c
index e9cf95c5c..d3ee01af0 100644
--- a/tests/unit/timeout_test.c
+++ b/tests/unit/timeout_test.c
@@ -2,6 +2,7 @@
 
 #include <cf3.defs.h>
 #include <cf3.extern.h>
+#include <pipes.h>
 #include <timeout.h>
 
 /* The alarm handler interrupts the sleep, so this normally returns as soon as
@@ -38,6 +39,9 @@ static void test_clear_disarms(void)
 static void test_fired_alarm_without_a_process(void)
 {
     SetTimeOut(1);
+    /* Production starts the clock only once a pid is registered; start it by
+     * hand to reach the handler's no-process branch. */
+    StartTimeOutClock();
     WaitForAlarm();
 
     assert_true(TimeOutHasFired());
@@ -54,6 +58,7 @@ static void test_fired_alarm_without_a_process(void)
 static void test_clear_preserves_the_record(void)
 {
     SetTimeOut(1);
+    StartTimeOutClock();
     WaitForAlarm();
     assert_true(TimeOutHasFired());
 
@@ -81,6 +86,8 @@ static void test_clear_preserves_a_true_signalled_flag(void)
 
     SetTimeOut(1);
     ALARM_PID = child;
+    /* Same order as cf_popen(): publish the pid, then start the clock. */
+    StartTimeOutClock();
     WaitForAlarm();
 
     assert_true(TimeOutHasFired());
@@ -97,6 +104,7 @@ static void test_clear_preserves_a_true_signalled_flag(void)
 static void test_next_set_resets_the_record(void)
 {
     SetTimeOut(1);
+    StartTimeOutClock();
     WaitForAlarm();
     assert_true(TimeOutHasFired());
 
@@ -107,6 +115,77 @@ static void test_next_set_resets_the_record(void)
     ClearTimeOut();
 }
 
+/* The arming-order half of the timeout guarantee: the clock must not run
+ * before cf_popen() has a pid to kill. Arming immediately, as SetTimeOut()
+ * used to, lets the alarm fire during the caller's own setup -- umask(),
+ * logging, cf_popen dispatch -- and burn the whole timeout on nothing, after
+ * which the command runs unbounded.
+ *
+ * Deliberately not a fixed-wait liveness check: it waits twice the timeout
+ * before forking at all, so the old behaviour fires with certainty rather than
+ * by timing luck, and the command it then runs outlives its timeout by 4s. */
+static void test_clock_does_not_run_before_the_fork(void)
+{
+    SetTimeOut(1);
+
+    for (int i = 0; (i < 20) && !TimeOutHasFired(); i++)
+    {
+        struct timespec ts = { .tv_sec = 0, .tv_nsec = 100 * 1000 * 1000 };
+        nanosleep(&ts, NULL);
+    }
+    /* Two seconds into a one-second timeout, with no child yet. */
+    assert_false(TimeOutHasFired());
+
+    FILE *pp = cf_popen("/bin/sleep 5", "r", true);
+    assert_true(pp != NULL);
+
+    /* Ends at EOF, which arrives when the alarm terminates the child. */
+    char buf[64];
+    while (fread(buf, 1, sizeof(buf), pp) > 0)
+    {
+    }
+    cf_pclose(pp);
+
+    assert_true(TimeOutHasFired());
+    assert_true(TimeOutSignalledProcess());
+    ClearTimeOut();
+}
+
+static void test_set_leaves_the_clock_stopped(void)
+{
+    SetTimeOut(3600);
+    assert_true(TimeOutIsArmed());
+    /* alarm(0) returns the seconds left on a running clock, and 0 if none is
+     * running. Armed, but not yet ticking. */
+    assert_int_equal(alarm(0), 0);
+    ClearTimeOut();
+}
+
+static void test_start_runs_the_clock_once(void)
+{
+    SetTimeOut(3600);
+    StartTimeOutClock();
+    assert_true(alarm(0) > 0);
+
+    /* One-shot: a second fork under the same timeout runs on the time already
+     * ticking, so this must not restart the command's budget. */
+    StartTimeOutClock();
+    assert_int_equal(alarm(0), 0);
+    ClearTimeOut();
+}
+
+/* A timeout armed but never followed by a fork -- cf_popen() failing, or a
+ * caller returning early -- must be fully retired, not left able to start. */
+static void test_clear_retires_an_unstarted_clock(void)
+{
+    SetTimeOut(3600);
+    ClearTimeOut();
+
+    StartTimeOutClock();
+    assert_int_equal(alarm(0), 0);
+    assert_false(TimeOutIsArmed());
+}
+
 int main()
 {
     const UnitTest tests[] =
@@ -116,7 +195,11 @@ int main()
         unit_test(test_fired_alarm_without_a_process),
         unit_test(test_clear_preserves_the_record),
         unit_test(test_clear_preserves_a_true_signalled_flag),
-        unit_test(test_next_set_resets_the_record)
+        unit_test(test_next_set_resets_the_record),
+        unit_test(test_clock_does_not_run_before_the_fork),
+        unit_test(test_set_leaves_the_clock_stopped),
+        unit_test(test_start_runs_the_clock_once),
+        unit_test(test_clear_retires_an_unstarted_clock)
     };
 
     PRINT_TEST_BANNER();
```

## 5. Measurements already taken

| | baseline (unfixed `dbf759d16`) | fixed (`92531d60c`) |
|---|---|---|
| `tests/unit/timeout_test` | 6/6 | **10/10**, ~25s |
| acceptance `08_commands/04_exec_timeout` | 6/6, 62s | **6/6**, 66s |

**Discrimination was proved, not asserted.** `libpromises/timeout.c` was
temporarily edited to emulate pre-fix behaviour (`alarm(timeout); TIMEOUT_PENDING = 0;`
in the non-MinGW branch, leaving `StartTimeOutClock()` a no-op), rebuilt and
rerun: **exactly 2 of 10 failed** — `test_clock_does_not_run_before_the_fork`
(assert at `timeout_test.c:137`) and `test_set_leaves_the_clock_stopped`
(at `:160`, `0xe10` = 3600, i.e. the clock was already running). The probe was
then reverted from a saved copy, verified absent, rebuilt, 10/10 again. The other
8 pass both ways — they are contract pins, not discriminators.

`test_clock_does_not_run_before_the_fork` deliberately waits **twice** the timeout
(2s against a 1s timeout) before forking at all, so the old behaviour fires with
certainty rather than by timing luck, then runs `/bin/sleep 5` — 4s beyond its
timeout. Margins are gross, not races. It is deliberately **not** a fixed-wait
liveness check.

## 6. Build and measurement traps — control for these explicitly

1. **`tests/acceptance/testall` exits 0 even when every test fails.** Seen twice
   on this machine, with two different causes (vacuous skip; dyld abort). The
   exit code is worthless. **Read the passed count.**
2. **`.libs` binaries carry an install-prefix RPATH.** You must run
   `make && make install` in the worktree before any acceptance run, or every
   test dies on dyld — with exit code 0, per trap 1.
3. **`raise(SIGALRM)` cannot discriminate this fix.** It invokes the handler
   directly and bypasses the kernel timer, which is exactly the thing the fix
   changes. Any test built on `raise()` proves nothing here.
4. **`alarm(0)` reads *and cancels*.** An assertion that inspects the clock
   destroys it. This matters for reading the new unit tests — see uncertainty 4.
5. **Asserting the new API exists is not discrimination.** A test only counts if
   it fails against pre-fix behaviour. State whether you ran anything; "I did not
   build" is an acceptable answer, an invented measurement is not.

Reproduce (unit, ~25s, expect "All 10 tests passed"):

```bash
cd /Users/djbclark/src/core-prefork/tests/unit && make timeout_test && ./timeout_test
```

Acceptance (~66s, expect "Passed tests: 6"):

```bash
cd /Users/djbclark/src/core-prefork && make && make install
cd tests/acceptance
rm -rf /tmp/cfe4734-rev && mkdir -p /tmp/cfe4734-rev/workdir /tmp/cfe4734-rev/tmp
CFENGINE_TEST_OVERRIDE_WORKDIR=/tmp/cfe4734-rev/workdir TEMP=/tmp/cfe4734-rev/tmp \
  ./testall --gainroot=env \
  --agent=/Users/djbclark/src/core-prefork/cf-agent/.libs/cf-agent \
  --cfpromises=/Users/djbclark/src/core-prefork/cf-promises/.libs/cf-promises \
  --cfserverd=/Users/djbclark/src/core-prefork/cf-serverd/.libs/cf-serverd \
  08_commands/04_exec_timeout
```

## 7. The author's numbered uncertainties

Address every one **by number and by name**. Do not accept the framing — the
framing may be the error.

**U1 — `cf-monitord/history.c` may lose its timeout entirely.** `history.c:242`
arms a timeout, then branches on `stream_type`. The `"pipe"` branch forks
(`cf_popensetuid` / `cf_popen_shsetuid`, both routing through
`GenericCreatePipeAndFork`) and is fine. The **`"file"` branch does not fork at
all** — it `safe_fopen()`s the promiser and drains it with `CfReadLine()`
(`history.c:262–274`, read loop at `:333`). Before this change, the alarm fired
and `EINTR`-interrupted that read. After it, `StartTimeOutClock()` is never
called, so no alarm is ever set and a blocking open/read (the promiser is only
`stat()`ed, not checked for `S_ISREG`, so a FIFO reaches this path) hangs
forever. Is this a real regression? If so, is it severe enough to block the
change, and what is the right remedy — start the clock at the non-forking sites
too, keep `SetTimeOut()` arming and add a separate deferred entry point, or
something else? Answer with reference to the actual code, not the author's
summary.

**U2 — is `GenericCreatePipeAndFork()` the right and complete choke point?**
`ShellCommandReturnsZero()` (`unix.c:225`) publishes `ALARM_PID` from a direct
fork that bypasses `GenericCreatePipeAndFork()`. The author scoped it out because
it arms nothing. Is that sound — can any of the six `SetTimeOut()` callers reach
`ShellCommandReturnsZero()` with a timeout armed and unstarted, so that the
command it runs escapes the timeout that was meant to bound it? Are there other
fork paths that should start the clock and don't?

**U3 — one-shot semantics at `nfs.c:1459`.** That site arms once and then forks
**twice** (`VerifyUnmount()` then `VerifyMount()`). Under the fix the first fork
starts the clock and the second runs on the remainder. Is that the same
behaviour as before, better, or worse? Consider the case where the first fork
consumes the whole budget, and the case where `VerifyUnmount()` returns early
under `DONTDO` without forking at all.

**U4 — is `test_start_runs_the_clock_once` actually testing what it claims?**
It asserts `alarm(0) > 0`, which *cancels* the timer, then calls
`StartTimeOutClock()` again and asserts `alarm(0) == 0`. Because the first
assertion already killed the clock, does the second assertion still discriminate
a one-shot starter from a re-arming one? If it is confounded, propose a test that
is not.

**U5 — the MinGW divergence.** `SetTimeOut()` behaves differently under
`__MINGW32__` (arms immediately) than on POSIX (defers). Is conditioning on the
compiler the right axis here, or should the deferral be unconditional with the
Windows pipe implementation fixed separately upstream? Is there any way a build
gets the POSIX branch without ever reaching `GenericCreatePipeAndFork()`? Would a
CFEngine maintainer accept this asymmetry?

**U6 — `TIMEOUT_PENDING` is a plain `int`**, while its neighbours `TIMEOUT_FIRED`,
`TIMEOUT_SIGNALLED` and `TIMEOUT_ARMED` are `volatile sig_atomic_t`. The author's
justification is that nothing in the handler touches it and `ClearTimeOut()` is
never called from a handler (verified — see §3). Is that sufficient, or does the
asymmetry itself invite a future bug?

**U7 — is the semantic change acceptable to upstream?** `exec_timeout` now bounds
the *command* rather than the agent's own setup plus the command. Promises that
previously timed out during setup will now run longer. Is that a fix or an
undocumented behaviour change, and does it need a changelog entry beyond
`Changelog: Commit`?

**U8 — test coupling.** `tests/unit/timeout_test.c` now `#include <pipes.h>` and
calls `cf_popen()`, so a unit test for `timeout.c` links and exercises the pipe
machinery. Acceptable, or should the behavioural test live in acceptance only?

## 8. Out of scope

- B-17 (`CFE-4727`) and B-19 (`CFE-4735`) are separate, already-pushed branches.
  This is a sibling off `dbf759d16`, deliberately not stacked. Do not propose
  folding them together.
- A separate, already-known defect family: armed timeouts leaked on error and
  early-return paths (`verify_exec.c:374`, `verify_exec.c:391–393`,
  `nfs.c:405–409`, and `nfs.c:1434`/`nfs.c:1459` which have no matching
  `ClearTimeOut()` at all). If you have something new to say about it, say it in
  a clearly marked "out of scope" section — do not let it displace U1–U8.
