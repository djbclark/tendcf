# B-8 second opinion — cursor — 2026-08-16

Review of `326bcdb8d` (`fix/exec-timeout-promise-result` off `master` `17eb78e6d`)
alone, not the `tendcf-integration` merge. Built that commit's `verify_exec.c` +
`timeout.c` into a scratch `cf-agent` under `/tmp/b8-326` and ran throwaway
policy with `CFENGINE_TEST_OVERRIDE_WORKDIR`. Stock comparison is Homebrew
3.27.1.

The fork moved under this review (later commits, then a different branch).
Verdicts below are from `git show 326bcdb8d` and from a binary rebuilt from
that tree, not from whatever `cf-agent` happened to be sitting in the checkout.

---

## 1. Verdict

**Ship with changes.**

The patch does what it claims on the author's own repro (`sleep 2.4; exit 0`
under `exec_timeout => "2"`): stock reports the promise repaired at 100%
compliance; `326bcdb8d` reports it timed out at 0%. That path is no longer
fail-open, and a single commands: promise is counted once (not the 50%
double-count of the earlier draft).

It does **not** close the fail-open in general. The flag is sampled when the
output read loop ends, which is when the child closes stdout, not when it
exits. `cf_pclose()` then clears `ALARM_PID` and waits. An alarm that fires
during that wait is logged (`> Time out`) and ignored, and the promise is
still judged on the exit status. Measured: a command that closes both output
streams and then sleeps past the timeout is reported **repaired at 100%** on
`326bcdb8d`.

Do not send this commit upstream until the sample moves to after `cf_pclose()`
and there is an acceptance test for both shapes of command. Missing tests and
a `CONTRIBUTING.md` hygiene miss are secondary to that.

Required changes:

1. Read `TimeOutHasFired()` **after** `cf_pclose()` returns, still before the
   alarm is disarmed. The comment that the alarm "has already fired by now if
   it was going to: it is what interrupted the read loop" is false; delete it.
2. Add acceptance tests: (a) the author's `sleep 2.4; exit 0` repro, (b) a
   command that closes stdout/stderr and then outlives `exec_timeout`. Assert
   `Promise TIMED-OUT`, aggregate compliance 0%, and a `repair_timeout` class
   rather than `promise_repaired` / default-success.
3. Changelog/commit body: the default for exit 0 is **repaired**
   (`PROMISE_RESULT_CHANGE`), not kept. Stock logs `Promise REPAIRED`. The
   fail-open is "reported compliant", not specifically "kept".
4. `CONTRIBUTING.md` (style/hygiene, not process): add the tests; add
   `Ticket:`; prefer past tense in the title (`Reported` / `Fixed`).

Optional, not blocking if (1) lands:

- Block `SIGALRM`, then `alarm(0)`, then sample. After (1) there is still a
  short window between `cf_pclose()` returning and disarm where a just-on-time
  completion can be mis-labelled timeout.
- `timeout.h` uses `bool` without including `<stdbool.h>` / `platform.h`.

---

## 2. Severity verdict

**`security@northern.tech`.**

This is not memory unsafety, RCE, or an auth bypass. It is a **fail-open of a
control**: a `commands:` promise used as a check, bounded by `exec_timeout`,
is reported as succeeded when the check did not finish. A later promise that
keys off `promise_repaired`, `if_repaired`, `if_ok`, or default success
classes cannot tell "the check passed" from "the check never finished".
CFEngine's job is to enforce system state; reporting a timed-out verification
as compliant is a control failure, not a log-message nit.

What a policy can actually observe (measured / read in tree):

| Channel | Stock (timeout, exit 0) | `326bcdb8d` on author's repro | `326bcdb8d` on stdout-closed hang |
|---|---|---|---|
| Verbose banner | `Promise REPAIRED` | `Promise TIMED-OUT` | `Promise REPAIRED` |
| Outcome classes | `promise_repaired` fires; `repair_timeout` does not | reverse | `promise_repaired` still fires |
| `kept_returncodes => { "0" }` | would classify kept (source) | ignored; timeout wins | ignored only if the flag is seen, which it is not |
| Bundle compliance | 100% (1 repaired) | 0% (1 not kept) | 100% (1 repaired) |
| `cf-agent` exit status | 0 | 0 | 0 |
| `PromiseResultIsOK` | true (`CHANGE`) | false (`TIMEOUT`) | true (`CHANGE`) |

`cf-agent`'s process exit status is not a useful signal either before or
after: `main` only sets `ret` on eval abort / bootstrap failure. Enterprise
`TrackTotalCompliance` is a community stub; not checked. Making
`PROMISE_RESULT_TIMEOUT` (`'t'`) reachable for `commands:` is the intended
reporting change and will show up wherever that enum is stored.

A vendor may recategorize this as correctness rather than "security". Send it
to `security@` anyway: the contract of `exec_timeout` is that exceeding it is
not success, and the failure mode is a check reporting pass.

The remaining stdout-closed hole is narrower than the author's shell+sleep
repro but is not exotic (a script that daemonizes, or `exec >&-` before a
long piece of work). Until the sample point moves, the headline fail-open is
only partly closed.

---

## 3. Defects found

### D1 — Flag sampled before `cf_pclose()`; fail-open still open — **verified**

- **Where:** `cf-agent/verify_exec.c:444-446` (sample), `:455` (`cf_pclose`),
  `libpromises/pipes_unix.c:853` (`ALARM_PID = -1` at the start of
  `cf_pclose`, before `cf_pwait`).
- **What breaks:** A command that closes stdout (so the read loop ends) and
  then runs past `exec_timeout` is not classified as timed out. The alarm
  fires during the wait with `ALARM_PID` already `-1`, so `TimeOut()` logs
  `> Time out` and does **not** kill the child. `timed_out` was already
  captured as false, so `VerifyCommandRetcode()` sees exit 0 and reports
  repaired. The comment at `:444-445` stating the alarm has already fired if
  it was going to is false for this shape.
- **Repro** (scratch `cf-agent` built from `326bcdb8d` `verify_exec.c`,
  `CFENGINE_TEST_OVERRIDE_WORKDIR`, `exec_timeout => "2"`):

```cfengine3
body common control { bundlesequence => { "t" }; }
body contain c { useshell => "noshell"; exec_timeout => "2"; }
bundle agent t
{
  commands:
      "/bin/sh" arglist => { "-c", "exec >&- 2>&-; sleep 5; exit 0" }, contain => c;
}
```

  Result: wall ~5.7s, `verbose: > Time out`, then `Finished command ...
  succeeded`, `Promise REPAIRED`, aggregate **100.0%**. Contrast the author's
  repro on the same binary: `Time out of process`, `exceeded exec_timeout`,
  `Promise TIMED-OUT`, **0.0%**.

  Stock 3.27.1 on the author's repro: `Time out of process`, `Promise
  REPAIRED`, 100% — defect exists; `326bcdb8d` closes that shape only.

### D2 — No tests — **verified** (absence)

- **Where:** commit `326bcdb8d` (3 files, no `tests/`).
- **What breaks:** `CONTRIBUTING.md` requires acceptance tests for promise
  attributes. Without one, the stdout-closed hole (D1) is invisible to CI, and
  the next "we closed the fail-open" claim will not be mechanically
  refutable. The right tests are (a) and (b) in the verdict list; they are
  short, deterministic if you assert classification rather than wall-clock,
  and do not need to wait for B-1's Darwin overshoot to be fixed.

### D3 — Commit hygiene vs `CONTRIBUTING.md` — **verified**

- Title is present-tense (`Report a...`); past tense is preferred.
- `Changelog: Title` is present; `Ticket:` is missing. Changelog entries are
  required to carry a ticket.
- Process section of `CONTRIBUTING.md` is out of scope (operator instruction).

### D4 — Default path is repaired, not kept — **verified** (claim error, not a code bug)

- **Where:** commit message first paragraph ("kept_returncodes", "promise
  kept"); register line for B-8. Code: `cf-agent/retcode.c:97-104` default
  `retcode == 0` → `PROMISE_RESULT_CHANGE`. Stock log: `Promise REPAIRED`,
  `CLASS repaired` when a `classes` body is attached.
- **What breaks:** nothing in the binary. The write-up will confuse upstream
  about the observable (they will look for `_kept` and not find it). Fix the
  prose.

### D5 — `timeout.h` not self-contained — **suspected** (compiles in-tree)

- **Where:** `libpromises/timeout.h:33` (`bool TimeOutHasFired(void)`).
- No `#include <stdbool.h>`. Every current includer pulls `bool` in via other
  headers. Will bite the first file that includes `timeout.h` alone.

### D6 — Read error after `SIGALRM` bypasses the new path — **suspected** (not reproduced)

- **Where:** `cf-agent/verify_exec.c:385-393`. `CfReadLine` → `-1` and
  `!feof` returns `ACTION_RESULT_FAILED` without sampling `TimeOutHasFired()`,
  and without disarming the alarm (the `alarm(0)` at `:494` is skipped).
- If `getline` surfaces `EINTR` rather than EOF after `TimeOut()`, the promise
  is `FAIL` not `TIMEOUT` (wrong class, still not kept — fail-closed for
  compliance). Also leaves `SIGALRM` armed. Pre-existing early-return shape;
  the new flag makes the mis-classification more visible. Not seen on the
  author's repro (that path got EOF and the new `cfPS`).

Not counted as a `326bcdb8d` regression:

- `TimeOut()` calls `Log()` and `GracefulTerminate()` from a `signal(SIGALRM)`
  handler. Not async-signal-safe. Pre-existing. The new `TIMEOUT_FIRED = 1`
  write is the safe part.
- `background => "true"`: parent never waits, reports the promise kept, child
  may `cfPS(TIMEOUT)` into a forked copy. Measured on a later tree: parent
  `Promise was KEPT`, `Zero promises executed for bundle`, then after
  `WaitForBackgroundProcesses` the child's timeout log appears. Pre-existing
  parent-side fail-open; this patch does not fix it and does not make it
  worse in the parent.
- `--dry-run` / `action_policy => "warn"` return before the new branch.
  Unchanged.
- `cf-agent` exit status stays 0. Unchanged.

---

## 4. The six questions

**1. Is the severity claim right?**

Yes, as fail-open of a check, with the wording correction in D4. It belongs
on `security@`, not because it is a memory bug, but because a bounded
verification reporting success is a control failure. See §2. A policy with no
`classes` body only sees compliance counters and verbose banners; a policy
with `classes_generic` / `if_repaired` / `if_ok` / `kept_returncodes` sees a
success class. `cf-agent` exit status cannot tell the cases apart either
before or after.

**2. Is the flag read at the right point?**

No. See D1. `timed_out` is computed after the read loop and before the alarm
is disarmed, but **also before `cf_pclose()`**. The alarm can fire after that
read and be missed; that is not theoretical.

Stale flag: `SetTimeOut()` clears `TIMEOUT_FIRED` before arming. A commands:
promise without `exec_timeout` never reads the flag (`timeout != CF_NOINT`
guard). Other `SetTimeOut()` users (`nfs.c`, `cf-monitord/history.c`) do not
read `TimeOutHasFired()` in this commit, so they neither consume a stale
commands: timeout nor leave one that a later commands: promise will see
without a fresh `SetTimeOut()`. `cf-execd` includes `timeout.h` for
`SetReferenceTime`, not this path. Nested/looping promises: each timed
`RepairExec()` calls `SetTimeOut()` first. Background: parent and child have
separate address spaces after `fork()`; the parent's `timed_out` stays false.
Not a stale-flag bug. The live bug is sampling too early in the **same**
invocation.

**3. Is `volatile sig_atomic_t` the right type, and is the handler safe?**

The new flag is the right type and the write in `TimeOut()` is
async-signal-safe. Installing via `signal(SIGALRM, (void *) TimeOut)` with
`void TimeOut()` is pre-existing. This commit does not add a new
async-signal-safety problem; it also does not fix the existing one (`Log()` +
`GracefulTerminate()` in the handler, including ~1s poll loops). Do not make
that this patch's job.

**4. Does it change behaviour for commands that do not time out?**

On the paths measured with a `326bcdb8d` `verify_exec.o`, no:

- `exec_timeout` absent, `/usr/bin/true` → repaired, 100%.
- `exec_timeout => "5"`, `/usr/bin/true` → repaired, 100%.
- `exec_timeout => "5"`, `/usr/bin/false` → not kept, `returned 1`.
- `--dry-run` / `action_policy => "warn"` never reach the new branch
  (source + a later-tree run: `Would execute` / `only warning was promised`).
- `background => "true"`: parent still reports kept without waiting
  (pre-existing).
- Module: not successfully exercised (the throwaway module command was
  invalid sh and exited 2 immediately).

**5. Is classifying on the timeout instead of the exit status the right design?**

Yes. `exec_timeout` is a bound. A command that was signalled, or that ran
past the bound while its children drained, does not get to declare success
via `kept_returncodes` / default 0. Silently overriding `kept_returncodes` on
timeout is acceptable and is the fail-closed choice; a policy that wanted
"timed out but exited 0" as kept should not have set `exec_timeout`.
Reporting both (timeout class **and** retcode class) would re-open the
fail-open for any policy watching the success class. Opt-in via a new body
attribute would leave the default unsafe. Changelog should say the override
is intentional.

**6. Backward compatibility?**

`PROMISE_RESULT_TIMEOUT` was dead for `commands:`; making it reachable is the
fix. `PromiseResultIsOK` is false for `TIMEOUT`, so compliance and anything
that uses that helper will treat it as not-ok. `SetPromiseOutcomeClasses`
already maps it to `repair_timeout` / `cancel_notkept`. `BannerStatusEnd`
already has `Promise TIMED-OUT`. `UpdatePromiseCounters` already increments
`PR_NOTKEPT`. Community `TrackTotalCompliance` is a stub. `cf-agent` exit
status does not change. No in-tree acceptance test currently requires a timed
`commands:` promise to be kept/repaired, because that outcome was an accident.

`PromiseResultUpdate(TIMEOUT, TIMEOUT)` in `VerifyExecPromise` after
`RepairExec` already stored `TIMEOUT` is a no-op (actuator.c returns `prior`
for timeout). One `cfPS` → one `ClassAuditLog` → one counter tick. Measured
on the author's repro, commands-only: kept=0, repaired=0, not kept=1, 0.0%.
No 50% double-count.

---

## 5. What you did not check

- Windows / MinGW (`__MINGW32__` `cf_pclose_nowait` path).
- Enterprise reporting / Mission Portal / non-stub `TrackTotalCompliance`.
- A valid `module => "true"` command that actually times out (partial module
  protocol lines + timeout classification).
- `useshell => "useshell"` (only `noshell` + `arglist`).
- `make check` / existing acceptance suite.
- The `EINTR` / `!feof` early return (D6) by measurement.
- Blocking `SIGALRM` around sample+disarm (residual race after a correct
  sample point).
- `cf-execd` as a long-lived process, except by reading that it does not call
  `RepairExec`.
- The later follow-up that moves the sample after `cf_pclose` (seen only
  because the fork's HEAD moved during this review). This opinion is of
  `326bcdb8d`. That follow-up is evidence D1 is real; it is not a substitute
  for fixing the commit that will be offered, and it still lacked tests when
  noticed.

---

## Measurements (scratch)

Stock 3.27.1, author's repro: rc=0, wall ~10s (Darwin termination-ladder
overshoot, B-1), `Promise REPAIRED`, `CLASS repaired`, 100%.

`326bcdb8d` `verify_exec`, author's repro, commands-only: rc=0, wall ~8s,
`exceeded exec_timeout of 2 seconds`, `Promise TIMED-OUT`, not kept=1, 0.0%.

`326bcdb8d` `verify_exec`, stdout closed then `sleep 5`: rc=0, wall ~5.7s,
`> Time out`, `Finished command ... succeeded`, `Promise REPAIRED`, 100.0%.
This is D1.
