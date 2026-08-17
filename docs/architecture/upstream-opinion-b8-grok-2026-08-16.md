# B-8 second opinion (grok) — 2026-08-16

Review of `326bcdb8d` (`fix/exec-timeout-promise-result`) **alone**, off
`master` `17eb78e6d`. Not the `tendcf-integration` merge. Source was read via
`git show 326bcdb8d` and a scratch clone at `/tmp/cfengine-b8-src`. The live
`~/src/cfengine-core` checkout moved under this review (master ↔
`tendcf-integration`); nothing in that repo was modified.

Measured against:

- stock Homebrew **3.27.1** (`/opt/homebrew/bin/cf-agent`)
- isolated rebuild of **3.29.0a.326bcdb8d** (`/tmp/cfengine-b8-src/cf-agent/cf-agent`,
  configured without `--enable-debug`, throwaway
  `CFENGINE_TEST_OVERRIDE_WORKDIR`)

`--enable-debug` on the first scratch build aborted in `LmdbEnvOpen`
(`mdb_env_get_maxkeysize(env) == 511`) against Homebrew LMDB. That assert is
pre-existing and unrelated to this patch.

---

## 1. Verdict

**Ship with changes.**

The common-case fail-open is real, and this patch closes it: a
`commands:` promise whose `exec_timeout` fires while the child still holds
stdout is no longer judged on the wait status. Isolated B-8 turns the
author's own repro from `Promise REPAIRED` / 100% into `Promise TIMED-OUT` /
0%, and it does so without a second `cfPS` (no 50% double-count).

Do not ship the commit as written. The sample point is wrong, the comment
justifying it is false, the log line lies when the child was not killed, and
there is no test. Those are not style nits — I reproduced the remaining
fail-open.

Required before offering this upstream:

1. **Read `TimeOutHasFired()` after `cf_pclose()`, not before.** The comment
   at `verify_exec.c:444–446` claims the alarm "is what interrupted the read
   loop" and so has already fired. That is false. `cf_pclose()` clears
   `ALARM_PID` and then `waitpid`s; the alarm can fire in that window, set
   the flag too late, and take the `ALARM_PID == -1` branch so the child is
   not even signalled. Isolated B-8, 3/3:

   ```
   exec >/dev/null 2>&1; sleep 5; exit 0   +  exec_timeout => "2"
   verbose: > Time out
   verbose: Finished command related to promiser '/bin/sh' -- succeeded
   A: Promise REPAIRED
   aggregate 100%
   wall ~5.5–7.5s
   ```

   Sampling after `cf_pclose()` makes the official repro and this case the
   same check.

2. **Do not log "and was terminated" unless it was.** That string is
   unconditional on the flag. In the stdout-closed case the child ran to
   completion. Tie the wording to `ALARM_PID` having been set when
   `TimeOut()` ran, or split "alarm fired" from "we signalled the child".

3. **Add an acceptance test.** `CONTRIBUTING.md` requires one for a promise
   attribute behaviour change; this commit adds none. Minimum:

   - `sleep 2.4; exit 0` + `exec_timeout => "2"` → `repair_timeout` class,
     not repaired/kept, bundle compliance 0% for that promise
   - same command finishing inside the timeout → still repaired on exit 0,
     still failed on exit ≠ 0
   - `kept_returncodes => { "0" }` must not resurrect "kept" on timeout
   - command that closes stdout then sleeps past the timeout → timeout, not
     repaired (this is what the current sample point gets wrong)
   - two sequential `commands:` (timeout then a fast exit 0) → second is
     still repaired (flag must not leak)

4. **Fix the commit body's false statement** that default `kept_returncodes`
   treat exit 0 as "promise kept". `VerifyCommandRetcode()` defaults exit 0
   to `PROMISE_RESULT_CHANGE` (repaired). The commit's own repro prints
   `Promise REPAIRED`. Changelog title is present tense; `CONTRIBUTING.md`
   prefers past tense when `Changelog: Title` is used. No `Ticket:` line.

Optional, not blocking if called out in the PR rather than papered over:

- Module protocol lines received before the timeout still define classes
  (`+module_said_ok` survived on B-8 while the promise itself became
  `TIMED-OUT`). Worth a sentence in the commit, not a redesign.
- `background => "true"` is unchanged: the parent still reports the promise
  kept. Pre-existing, but anyone citing this as "exec_timeout is now
  visible" is wrong for that path.

---

## 2. Severity verdict

**`security@northern.tech`.**

This is not a CFEngine memory-safety bug and not a privilege boundary in
the agent itself. It is a **promise-result integrity fail-open**: a check
that did not finish is reported as satisfied.

What a policy can actually observe, measured:

| Observable | Stock 3.27.1 on the official repro | Isolated B-8 |
|---|---|---|
| Default exit 0 | `Promise REPAIRED`, `Finished command -- succeeded` | `Promise TIMED-OUT`, no retcode path |
| `kept_returncodes => { "0" }` + `promise_kept` | `CLASS:kept`, 100% | `CLASS:timeout` |
| `if_ok("x")` / `promise_repaired` | class defined | class not defined |
| `classes_generic` / `results()` `_ok` | defined | `_timeout` + `_not_ok` instead |
| `depends_on` | dependent **runs** (stock: `DEPENDENT_RAN`) | dependent **stays skipped** all passes |
| Bundle compliance (commands only) | 100% repaired | **0.0%**, 1 not-kept |
| `cf-agent` process exit | 0 | 0 (pre-existing: failed promises do not fail the process) |
| Verbose `Time out of process` | already printed, then discarded | printed, then classified |
| `background => "true"` parent | `Promise was KEPT`, 100%, `CLASS:none` | same parent result; child now logs the new error line |
| Module `+class` lines | persist **and** promise repaired | persist **and** promise timed-out |
| stdout closed, then sleep past timeout | repaired, 100%, child not killed | **still repaired, 100%, child not killed** |

`if_ok` only lists `promise_kept` / `promise_repaired`. It has no
`repair_timeout`. A CIS/package/malware check written

```
commands:
    "/usr/bin/check" contain => short_timeout, classes => if_ok("safe");
```

currently defines `safe` when the check never finished. After this patch,
for the common (stdout still open) case, it does not. `depends_on` currently
releases the dependent; after the patch it does not.

`cf-agent` exiting 0 is not a reason to downgrade this. That is how every
not-kept promise already works. The classes, `depends_on`, compliance, and
(Enterprise) result char `'t'` are what later promises and Mission Portal
consume.

The remaining stdout-closed hole is the **same** fail-open for a narrower
command shape. It does not make the common-case bug "just UX". It means the
fix is incomplete.

Ordinary-bug arguments that do not hold: "the timeout is already logged" —
automation does not parse `verbose: Time out of process`. "Default is
repaired not kept" — `PromiseResultIsOK()` is true for both; `if_ok` fires
for both; compliance counts both.

---

## 3. Defects found

### V1 — sample is before `cf_pclose()`; alarm after the read is missed

**Verified.** `cf-agent/verify_exec.c:444–446` (326bcdb8d), then
`libpromises/pipes_unix.c:853` (`ALARM_PID = -1` at the start of
`cf_pclose`) and `:876` (`cf_pwait`).

What breaks: a command that closes stdout (or otherwise EOF the pipe) and
then runs past `exec_timeout` is still classified on the wait status. On
the default path that is repaired / 100%. The child is not signalled
(`TimeOut()` sees `ALARM_PID == -1` and logs `> Time out` only).

Repro (isolated 326bcdb8d, 3/3; stock 3.27.1 same shape):

```cfengine3
body common control { bundlesequence => { "t" }; }
body contain c { useshell => "noshell"; exec_timeout => "2"; }
body classes oc {
  promise_repaired => { "saw_repaired" };
  repair_timeout   => { "saw_timeout" };
}
bundle agent t {
  commands:
    "/bin/sh" arglist => { "-c", "exec >/dev/null 2>&1; sleep 5; exit 0" },
      contain => c, classes => oc;
}
```

The author's comment at 444–446 is the defect, not a description of the
code. I also saw one earlier run of a same-commit binary classify this as
timeout; isolated 326bcdb8d did not. The sample is load-sensitive. After
`cf_pclose()` it would not be.

### V2 — log line claims termination that did not happen

**Verified**, same repro as V1. `verify_exec.c:467–469`:

```
Command '%s' exceeded exec_timeout of %d seconds and was terminated
```

On V1 the child is not terminated. Wall clock is the full `sleep 5`. Anyone
grepping that error as "the bound held" will be lied to.

### V3 — no tests

**Verified.** Diff is three files, no `tests/`. `CONTRIBUTING.md` ("Add
tests", "Promise types, attributes, and functions should have acceptance
tests") is violated. The previous confident fail-open claim on this same
mechanism was refuted by measurement; shipping this without a test that
would have caught V1 is how that happens again.

### V4 — commit text is wrong about the default outcome

**Verified.** Body: *'with the default kept_returncodes an exit status of 0
is "promise kept"'*. `cf-agent/retcode.c:97–104` defaults exit 0 to
`PROMISE_RESULT_CHANGE`. Stock and B-8 both print `Promise REPAIRED` for
that default. The fail-open is real either way; the explanation is not.

### S1 — `CfReadLine` error path never consults the flag

**Suspected, not hit in these runs.** `verify_exec.c:386–393`: `getline`
returning −1 without `feof` closes the pipe and `return ACTION_RESULT_FAILED`
before the sample. If `SIGALRM` interrupts the read with `EINTR` and
stdio surfaces it, a timeout becomes a generic read failure. Not observed
on Darwin with the official repro (the handler runs `GracefulTerminate`
synchronously, then the pipe EOFs). Still a hole if anyone ever makes
`TimeOut()` return quickly.

### S2 — module protocol classes persist across a timed-out promise

**Verified as behaviour, design question rather than a regression.** Isolated
B-8, module that prints `+module_said_ok` then `sleep 2.4`: both
`CLASS:module_said_ok` and `CLASS:timeout` are defined. The promise is
correctly not-kept; any later promise keyed off the module class still
sees "the check said OK". Pre-existing protocol apply-as-you-read; the
patch does not roll it back. Call it out, do not silently claim the
fail-open is gone for `module => "true"`.

### S3 — `background => "true"` parent is still fail-open

**Verified, pre-existing.** Parent forks, returns `ACTION_RESULT_OK` with
`timed_out == false`, reports `Promise was KEPT` / 100% / `CLASS:none`.
The child now `cfPS`es `TIMEOUT` and `_exit`s; those counters and classes
die with it. The parent's log *does* show the new error line (shared fd)
after the parent has already accounted the promise as kept. Not introduced
by this patch; not fixed by it.

---

## 4. The six questions

### 1. Is the severity claim right?

Yes, as a fail-open of **user-policy checks**, not as a CFEngine RCE. Send
it to `security@`. See §2. The author's wording "promise kept" overstates
the default (it is repaired) and understates `depends_on` (stock actually
runs the dependent). Both are fail-open. `cf-agent` exit status cannot tell
the cases apart before or after; ignore it.

### 2. Is the flag read at the right point?

**No.** See V1.

- After the read, before `alarm(0)`: necessary but not sufficient. The
  alarm is also live across `cf_pclose()`'s `waitpid`.
- Stale flag from a previous command: **not observed.** `SetTimeOut()`
  clears `TIMEOUT_FIRED`. Isolated B-8, timeout then `exit 0` with the same
  contain body: `FIRST:timeout`, `SECOND:repaired`.
- Command without `exec_timeout` after a timeout: `SetTimeOut` is not
  called, but neither is `TimeOutHasFired()` (`timeout != CF_NOINT` is the
  guard). The previous `RepairExec` already did `alarm(0)` /
  `signal(SIGALRM, SIG_DFL)`.
- `background`: only the child calls `SetTimeOut`; COW means the parent's
  flag is untouched. Parent never reads it.
- `cf-execd`: `TIMEOUT_FIRED` is process-local; `cf-agent` is typically
  one-shot. Not a cross-run leak.
- Other `SetTimeOut()` users (`cf-agent/nfs.c` four call sites,
  `cf-monitord/history.c:242`): they now also zero the flag. They never
  call `TimeOutHasFired()`. No new read of a stale value. A commands
  promise after an NFS RPC timeout still `SetTimeOut`s first if it has
  `exec_timeout`.

### 3. Is `volatile sig_atomic_t` right, and is the handler safe?

The **new** write is fine. `TIMEOUT_FIRED = 1` / `= 0` is the textbook
async-signal-safe way to publish "the handler ran". `TimeOutHasFired()`
only reads it.

This patch does **not** make `TimeOut()` async-signal-safe. The handler
already called `Log()` and `GracefulTerminate()` (the latter blocks in
`nanosleep` for the whole ladder — ~17 s on this Darwin box without B-1).
That is pre-existing. Adding one `sig_atomic_t` store does not add a new
async-signal-safety problem. `signal(SIGALRM, (void *) TimeOut)` is also
pre-existing.

`CONTRIBUTING.md` frowns on mutable statics. This one is the same
`GLOBAL_X` pattern as `ALARM_PID` and is required for a `signal()` handler.

### 4. Does it change behaviour for commands that do not time out?

**No, on the cases I ran.** Isolated 326bcdb8d vs stock 3.27.1:

| Case | Stock | B-8 |
|---|---|---|
| `exec_timeout` set, command `exit 0` in time | repaired | repaired |
| `exec_timeout` set, command `exit 7` in time | failed, retcode 7 | failed, retcode 7 |
| no `exec_timeout`, `exit 0` | repaired | repaired |
| no `exec_timeout`, `exit 3` | failed | failed |
| `action_policy => "warn"` | not executed, WARN → failure classes | identical |
| `--dry-run` / `DONTDO` | `Would execute`, WARN | identical |
| `background => "true"` parent result | KEPT / 100% / no outcome class | identical (child log text only) |
| `module => "true"` that finishes in time | not separately timed; the in-time paths above apply | same |

`a->module` promises that **do** time out change, by design (see S2).

### 5. Is classifying on the timeout instead of the exit status the right design?

**Yes**, as the default. The alternatives:

- **Report both / classify after `VerifyCommandRetcode`:** that is the
  draft that produced 50% for one promise (two `cfPS` / two
  `UpdatePromiseCounters`). This commit correctly *replaces* the
  classification. Isolated commands-only: 1 not-kept, 0 repaired, 0.0%.
- **Keep retcode, add a class:** leaves `if_ok` / default repaired fail-open.
  That is the bug.
- **Opt-in body attribute:** same, the dangerous default stays.
- **Honour `kept_returncodes` on a timed-out 0:** a policy *could* want
  "we sent SIGTERM and it still exited 0, call it kept". That is a
  specialist reading of a kill window, not a reason to keep the default
  fail-open. Isolated B-8 already overrides `kept_returncodes => { "0" }`
  with timeout; that is the correct override. If someone needs the old
  reading they can drop `exec_timeout` or treat `repair_timeout` as
  success themselves.

Silently overriding `kept_returncodes` is acceptable **because the exit
status is not a report of whether the command completed**. That is the
commit's actual argument, and the measurements back it for the stdout-open
case.

### 6. Backward compatibility?

`PROMISE_RESULT_TIMEOUT` (`'t'`) was already a first-class result:
`SetPromiseOutcomeClasses` has a `repair_timeout` arm, `UpdatePromiseCounters`
counts it as not-kept, `BannerStatusEnd` prints `Promise TIMED-OUT`,
`DoSummarizeTransaction` writes `log_failed`, `PromiseResultIsOK('t')` is
false, `NotifyDependantPromises` does not release dependents. Making it
reachable for `commands:` is using the enum for the thing it was declared
for. `VerifyExecPromise` already had the `ACTION_RESULT_TIMEOUT` case;
it was dead.

What changes for a policy that never saw `'t'` from `commands:`:

- `if_ok` / `promise_repaired` / default repaired **stop firing** on
  timeout. That is the fix. Anyone who treated "command with
  `exec_timeout` returned 0" as success will see a behaviour change.
  They should.
- Enterprise `TrackTotalCompliance` (stub in community) will start seeing
  `'t'` for this promise type. Dashboards that never handled timeout on
  commands will grow a not-kept bucket. Correct.
- `cf-agent` exit code: unchanged (still 0).
- Community acceptance tree: I found no test that asserts a timed-out
  `commands:` promise is kept/repaired. Nothing obvious to break. Absence
  of a test is V3, not proof none exist under a name I did not grep.

`PromiseResultUpdate(TIMEOUT, TIMEOUT)` in `VerifyExecPromise` after
`RepairExec` already stored TIMEOUT is redundant and harmless (prior
wins). Counters increment only in `cfPS` → `ClassAuditLog`. One
classification, not two.

---

## 5. What I did not check

- Linux, Windows, AIX, or any non-Darwin `GetProcessState` / `process_*.c`.
  B-8's flag logic is platform-agnostic; the termination ladder and
  `SA_RESTART` behaviour are not. V1 may be easier or harder to hit
  elsewhere.
- Enterprise reporting / Mission Portal / `TrackTotalCompliance` beyond
  the community stub.
- A real `cf-execd` long-running process (reasoned from the flag being
  process-local only).
- Nested `SetTimeOut()` while a `commands:` read loop is live (NFS mount
  from inside `RepairExec`). I do not believe that stack exists.
- `preview` / `no_output` / `useshell => "powershell"`.
- Whether `getline` on this libSystem ever returns `EINTR` to
  `CfReadLine` (S1).
- Full `make check` / existing acceptance suite on 326bcdb8d.
- The `tendcf-integration` merge of B-1+B-2+B-8. Out of scope.

---

## Evidence appendix (isolated 326bcdb8d unless noted)

Official repro, commands + reports: `CLASS:timeout`, `Promise TIMED-OUT`,
50% (the reports promise is kept). Commands only: **0.0%**,
`Promises not kept in 't' = 1`, `Promises repaired in 't' = 0`. Wall
~17–18 s (B-1 not in this commit; ladder still overshoots). Stock 3.27.1
same policy: `Promise REPAIRED`, 100%, `Finished command -- succeeded`,
`Time out of process` already logged and ignored.

`kept_returncodes => { "0" }`: stock `CLASS:kept`; B-8 `CLASS:timeout`.

`depends_on`: stock runs `/bin/echo DEPENDENT_RAN` on the second pass;
B-8 skips the dependent on every pass.

Stdout-closed: B-8 3/3 `CLASS:repaired`, `> Time out`, no
`Time out of process`, wall 5.5–7.5 s. Stock identical shape.

Sequential timeout then in-time `exit 0`: `FIRST:timeout SECOND:repaired`.
