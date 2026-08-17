# Upstream second opinion — grok — 2026-08-16

Reviewed commits, not the dirty tree: `26634ac1f` (B-1) and `cb2561584`
(B-2) on `tendcf-integration`, branched from `17eb78e6d`. While this
review was running, uncommitted follow-up appeared in `process_unix.c`,
`timeout.c`, `timeout.h`, `pipes_unix.c`, `verify_exec.c`, and `nfs.c`.
That work is **out of scope**. Verdicts below are on the two frozen
commits only.

I assumed the patches were wrong and tried to demonstrate it. Several
author claims survived measurement. The fail-open story did not survive
in the form it is being sold.

---

## 1. Verdict per item

### B-1 — `26634ac1f` — **ship as is**

The poll loops were counting `nanosleep()` iterations. Replacing that
with a monotonic deadline is correct, matches an existing in-tree
pattern, and I reproduced the Darwin overshoot the commit describes.
Ship the code.

Do **not** tell `security@` that this commit closes the fail-open. It
shrinks a window; it does not close it. That is a filing defect, not a
code defect in the loops. See §4.

### B-2 — `cb2561584` — **ship with changes**

The descendant / stuck-pipe diagnosis is right, and the
`getpgid`-before-kill ordering is right. The group `SIGKILL` after the
leader's graceful ladder is acceptable. The unconditional `setpgid(0,0)`
on every `cf_popen()` child is the wrong call and is the change that
must not go upstream as written.

Required before offering this to upstream:

1. Do not put every `cf_popen()` child in its own process group. Only
   the timeout path needs a group. The author's "keep the timeout path
   structurally identical to the normal path" argument is backwards —
   see uncertainty 1.
2. Check `setpgid()` (and `getpgid()`). A failure should log and skip
   the group kill, which the `pgid == pid` guard already does; silence
   is still wrong.
3. Add an acceptance test of the documented repro (`/bin/sh -c "sleep
   30; exit 0"` under `exec_timeout => "2"`). `CONTRIBUTING.md` wants
   tests; B-2 has none.

---

## 2. Defects found

### Verified

**B-1 residual fail-open — `cf-agent/verify_exec.c` `RepairExec()`
(committed, ~449–460 and the `return ACTION_RESULT_OK` at ~495).**
`TimeOut()` runs, the command can still be reaped with exit 0, and the
promise is **kept**. I ran the just-built `cf-agent` (libtool wrapper,
throwaway workdir, committed bits — I did not rebuild against the dirty
tree):

| policy | wall clock | result |
|---|---|---|
| `/bin/sh -c "sleep 5; exit 0"`, `exec_timeout => "2"` | 5.11 s | `abnormal termination` (not kept), no leftover `sleep` |
| `/bin/sh -c "sleep 30; exit 0"`, `exec_timeout => "2"` | 4.39 s | not kept, no leftover `sleep` |
| `/bin/sh -c "sleep 2.4; exit 0"`, `exec_timeout => "2"` | ~4.4 s | **`Time out of process` then `returned code '0' defined as promise kept`**, `Promises kept in 't' = 1` |

The 2.4 s case is the fail-open, after both patches. Mechanism, measured
in `/tmp` probes, not inferred:

- `/bin/sh -c "sleep 5; exit 0"` + `SIGINT` to the shell only: shell
  lives, waits for `sleep`, **exits 0** (~4.8 s).
- Same + `SIGTERM` to the shell only: shell dies immediately,
  `WIFSIGNALED` / `SIGTERM`.
- A zombie that already exited 0, then `SIGTERM`/`SIGKILL`: `waitpid`
  still reports **exit 0**.
- Darwin stub (`process_unix_stub.c` 44–51): `kill(pid, 0)` on a
  **zombie succeeds**, so `GetProcessState()` returns
  `PROCESS_STATE_RUNNING` and each `ProcessWaitUntilExited()` always
  burns its full budget. `getpgid(zombie)` returns `ESRCH`.

So: timeout fires, `SIGINT` does not kill `sh`, `sh` + child run until
they finish or until `SIGTERM` one second later (after B-1) / ~4.5 s
later (before). If they finish first, `waitpid` sees 0,
`VerifyCommandRetcode()` with `kept_returncodes => { "0" }` reports
**kept**. `RepairExec()` never returns `ACTION_RESULT_TIMEOUT`; that
enum is dead in this file. `cf_pwait()` (`pipes_unix.c` 808–815) maps
any signalled death to `-1`, which becomes `PROMISE_RESULT_FAIL`, not
timeout.

The author's `sleep 5` / `exec_timeout => "2"` numbers (~11.2 s kept
before, ~5.2 s not kept after) match **this** path: before B-1, `SIGTERM`
arrives at ~t=6.5, after `sleep 5` has already exited 0; after B-1,
`SIGTERM` arrives at ~t=3 and kills `sh` first. I did not rerun the
unpatched agent (no branch operations). The 2.4 s run is the
after-the-fix counterexample.

Direct `/bin/sleep 5` (default `useshell` is `noshell`) dies on `SIGINT`
in 1 ms (`WIFSIGNALED` / `SIGINT`). That shape is **not** the fail-open.
The B-1 commit text saying "sleep 5" is ambiguous; the numbers only
work for a shell as the direct child. The B-2 commit's `/bin/sh` +
`arglist` repro is the one that fail-opens.

**B-2 unconditional `setpgid(0,0)` — `pipes_unix.c` 240–245 (committed).**
`GenericCreatePipeAndFork()` is the single fork used by `cf_popen`,
`cf_popen_select`, `cf_popensetuid`, `cf_popen_sh`,
`cf_popen_sh_select`, `cf_popen_shsetuid`, and
`cf_popen_full_duplex`. After this commit every one of those children
leaves the agent's process group. That is a behaviour change for far
more than `commands:` + `exec_timeout`. What breaks, from the source:

- Interactive `cf-agent`: `ThisAgentInit()` (`cf-agent.c` 945–947)
  calls `setsid()`. That fails with `EPERM` when the process is already
  a group leader, which an interactive-shell job normally is, so the
  agent stays in the terminal's foreground group. `HandleSignalsForAgent`
  (`signals.c` 155–160) on `SIGINT`/`SIGTERM` calls
  `DoCleanupAndExit(0)` immediately. Children in their own group do not
  see the terminal `SIGINT`. Ctrl-C therefore kills the agent and
  **orphans the command**. Before the patch those children inherited
  the agent's group and died with it. I did not type Ctrl-C at a live
  agent; this is from the handlers plus a probe that `SIGINT` to the
  process group kills `sh -c "sleep 5"` in 1 ms, while `SIGINT` to `sh`
  alone does not.
- `cf-execd` `agent_expireafter` (default 120 minutes,
  `exec-config.c` 138): `cf-execd-runner.c` 306–315 does
  `kill(-agent)` when `getpgid(agent) == agent`. `cf-agent` has
  already `setsid()`'d, so that group is the agent's session. Before
  B-2, `commands:` children live in that group and die with expireafter.
  After B-2 they do not. Expireafter then fails to kill the hung
  command that is the usual reason the agent was stuck — the same
  class of bug B-2 is fixing, now opened in the production watchdog.
- Same hole for every other `cf_popen` site: `evalfunction.c`
  (`execresult` and friends), `exec_tools.c`, `processes_select.c`
  (`ps`), `verify_packages.c`, `verify_users_pam.c`, `nfs.c`,
  `mod_custom.c`, `cf-execd-runner.c` itself (the shell that wraps
  `cf-agent`), `cf-execd-runagent.c`, `cf-serverd`, `libenv/sysinfo.c`,
  `libenv/unix_iface.c`, `cf-monitord` (`mon_processes`,
  `mon_network`, `mon_temp`, `mon_network_sniffer`, `history.c`).

`SetTimeOut()` is used in three places: `verify_exec.c`, `nfs.c`,
`cf-monitord/history.c`. Only those need a killable group.

**`setpgid` / `getpgid` / `kill` return values ignored —
`pipes_unix.c` 245, `timeout.c` 49 and 64.** `setpgid(0,0)` in a
freshly forked non-session-leader child returned 0 in a probe
(`pgid == pid`). If it ever fails, the child stays in the agent's
group, `getpgid` ≠ pid, the sweep is skipped, and B-2 silently
becomes a no-op. `getpgid` of a live leader works; `getpgid` of a
Darwin zombie is `ESRCH` (measured). `kill(-pgid, 0)` still succeeds
while a grandchild in that group is alive (measured: leader 7111
dead, grandchild 7112 alive, `kill(-7111, 0) == 0`).

**Darwin `nanosleep(10 ms)` overshoot — confirms the B-1 diagnosis.**
100 iterations requested 1.00 s, took **4.449 s** (44.49 ms/iter) on
this Darwin/arm64 host. Author's 4.41–4.66 s / ~45 ms stands.

### Suspected, not demonstrated in-process

- `TimeOut()` is a `SIGALRM` handler (`timeout.c` 31–32:
  `signal(SIGALRM, (void *) TimeOut)`) and already called
  `GracefulTerminate()`, which `Log()`s and reads process state.
  None of that is async-signal-safe. B-2 adds `getpgid` + `kill`,
  which *are* AS-safe. Pre-existing; B-2 does not make it worse in
  kind. I did not try to catch a reentrancy crash.
- PID-reuse window between `GracefulTerminate()` returning and
  `kill(-ALARM_PID, SIGKILL)`: if the old group is gone and a new
  process group leader is created with that pid, the sweep hits the
  new group. The `pgid == pid` predicate is computed before death and
  does not close this. The window is a handful of syscalls. I did not
  try to win the race.
- `CLOCK_REALTIME` fallback: an NTP step backwards makes
  `remaining_ns` huge and the loop waits for the wall clock to catch
  up. Same bug as `EvalContextEventStart()`. No supported platform I
  checked lacks `CLOCK_MONOTONIC` (Darwin has it; `clock_gettime`
  returned 0).
- Comment in the *uncommitted* tree claims `setpgid` also causes
  `SIGTTIN` stops on interactive terminal reads. I did not verify
  that; it is not in the frozen commits.

---

## 3. The three flagged uncertainties

### 1. `setpgid` versus Ctrl-C

The author's framing is the error.

They asked whether detaching every `cf_popen()` child is acceptable
because non-interactive agent runs do not see Ctrl-C, and because they
did not want the timeout path to differ from the normal path. The
timeout path **is** different: it has to kill a tree. The normal path
has to remain killable by the things that already kill trees —
terminal `SIGINT`, and `cf-execd`'s `agent_expireafter`. Unconditional
`setpgid` buys the first and breaks the second.

Call-site blast radius is above. The interesting ones, specifically
named as requested:

| caller | in a terminal? | what B-2 changes |
|---|---|---|
| `cf-agent` `commands:` | yes, when run from a shell | Ctrl-C kills the agent (`DoCleanupAndExit(0)`), orphans the command |
| `cf-runagent` | usually remote | the local `cf-execd-runagent.c` `cf_popen` of `cf-runagent` is now its own group; a foreground `cf-execd`/`cf-runagent` debug session has the same orphaning |
| `cf-execd`'s children | no (daemon); yes if `cf-execd -F` | the *shell* around `cf-agent` is now a group leader; `cf-agent` then `setsid()`s into its own session anyway, so expireafter's `kill(-agent)` still hits the agent. It no longer hits the agent's `cf_popen` children. That is the production hit. |
| every other `cf_popen` / `cf_popensetuid` | mixed | `execresult()`, package-list commands, `ps`, `getent`, monitord pipes, custom modules — all leave the agent's group |

Job control beyond Ctrl-C:

- **`SIGTSTP` (Ctrl-Z):** same as `SIGINT` — foreground group only.
  Agent stops, detached children keep running.
- **`SIGHUP` on terminal close:** delivered to the controlling
  session / foreground group. Detached children do not get it unless
  they have that terminal as controlling tty, which they will not
  after `setpgid` (and `setsid` in the agent already dropped it when
  `setsid` succeeded).
- **Orphaned process groups:** if the agent dies and any member of
  the child's group is stopped, POSIX sends `SIGHUP`+`SIGCONT` to the
  orphaned group. Running (not stopped) children just get reparented
  to init and keep going. That is the Ctrl-C orphan.
- **Terminal ownership:** `setpgid` does not call `setsid`; the child
  keeps the agent's session and controlling tty until something else
  changes that. A child that reads the tty while not in the foreground
  group is the `SIGTTIN` story. I did not measure it.

Right call: **no.** Scope `setpgid` to "a timeout is armed", even if
that means threading a flag into `GenericCreatePipeAndFork()` or
consulting the already-set alarm. Implementation symmetry is not a
safety property.

### 2. The unconditional group `SIGKILL`

Acceptable on the timeout path. By the time `TimeOut()` runs, the
promise has already given up. Descendants that never saw `SIGINT` /
`SIGTERM` die hard; that is what you want for `exec_timeout`.

The shared-function argument is **true**. `GracefulTerminate()` is
called from `locks.c` `KillLockHolder()` (line 630) against a
recorded lock-holder pid, with that lock's start time. That pid is a
`cf-agent` (or similar) in whatever group it happens to live in —
often `cf-execd`'s, or a session of its own after `setsid()`. Putting
group semantics inside `GracefulTerminate()` would let a stale-lock
reaper `kill(-agent)` and take down an entire execd generation. Do
not do that. The sweep belongs in `TimeOut()`, where it is.

Does `pgid == pid`, read before termination, close the recycle race?
**No.** It closes a different, real bug: `getpgid` after the leader
is gone is `ESRCH` on Darwin even while the group still exists
(measured). Reading first is mandatory or the sweep never runs. It
does **not** bind the pid against reuse after `GracefulTerminate()`
returns. Use of `PROCESS_START_TIME_UNKNOWN` in `TimeOut()` already
disables `SafeKill()`'s start-time check, so there is no second
factor on the final `kill(-pid)`. Practically the window is tiny; I
would not block on it. I would not claim it is closed.

`getpgid` of a leader that is **already** a zombie when `TimeOut()`
starts also returns `ESRCH` on Darwin, the guard fails, and the
sweep is skipped. Common case at timeout is "still running"; this is
a small race, not the ordinary path.

### 3. The test's clock mock

Acceptable in *this* binary. I ran
`tests/unit/process_terminate_unix_test`: **6/6**.

The test already replaces `kill`, `nanosleep`, `GetProcessState`, and
`GetProcessStartTime`. It links only `process_unix.c` + `libtest` +
`libutils` (`tests/unit/Makefile.am` 362–364). The new
`clock_gettime` (`process_terminate_unix_test.c` 269–277) ignores
`clk_id` and projects the existing `current_time` nanosecond counter.
Without it the loops read real time while the fake process reacts on
fake time; the commit message's account of
`test_kill_long_reacting_signal` failing 1/6 is credible, and I did
not re-stash to reconfirm (no git mutations).

Process-wide risk: `libutils/mutex.c` 82 uses `clock_gettime
(CLOCK_REALTIME)` for `pthread_cond_timedwait`. This test never
calls `ThreadWait`. `current_time` starts at 1 ns (`InitTime`), so
anything that *did* take a timed wait would see 1970 and expire
immediately. That is a landmine if the test later links more of
libpromises; it is not a bug in the current binary.

Less invasive alternative: a function pointer / weak
`ProcessPollTimeNs` in `process_unix.c`. That is more production
surface for a test that already interposes libc. Not worth it.

Does the amended test still test what it was written to test? **Yes.**
`test_kill_long_reacting_signal` still builds a process whose
reaction time is 2 s against a ~1 s wait, still requires that
`SafeKill` not leave it `SIGSTOP`'d, still expects
`GracefulTerminate` to return true after escalating to `SIGKILL`,
still expects the fake process to be alive because even `SIGKILL` has
not been given time to "land." It was not weakened to a tautology.

`current_time` is a `time_t` used as a nanosecond counter. Pre-existing,
not introduced by B-1. Fine at the magnitudes this test uses
(2e9 ns).

---

## 4. Anything the author missed

**The diagnosis of B-1's user-visible consequence is incomplete.**
The slow ladder is real (measured). The fail-open is real (measured).
The *mechanism* is not "the ladder is so slow that a command finishing
during it is reaped as success" in general. It is:

1. `RepairExec()` never classifies a timeout as a timeout.
2. `/bin/sh` ignores `SIGINT` while it waits for a foreground child.
3. If that child finishes before `SIGTERM`, `sh` exits 0 and that
   status survives later signals to the zombie.
4. B-1 only moves `SIGTERM` from ~4.5 s after `SIGINT` to ~1 s
   after. Commands that complete in `(exec_timeout, exec_timeout+~1s]`
   still fail open. `sleep 2.4` / `exec_timeout => "2"` is the
   witness, after both patches.

B-2 does not fix this either. `kill(-pid, SIGKILL)` after the ladder
does not change the leader's already-recorded exit 0.

The actual fail-open fix is: once `TimeOut()` has run, ignore
`waitpid` for classification and return `ACTION_RESULT_TIMEOUT` /
`PROMISE_RESULT_TIMEOUT`. The enum and the `VerifyExecPromise`
switch arm already exist (`verify_exec.c` 129–131). They are
unreachable today.

**B-3 (Darwin stub) is load-bearing for both timings.** On Linux,
`GetProcessState()` (`process_linux.c` 150–151) returns `ZOMBIE` and
`ProcessWaitUntilExited()` returns true immediately. On Darwin the
two waits always expire, so `TimeOut()` itself is ~2 s after B-1
(~8.9 s before). Author's 4.4–5.2 s "after" numbers are
`exec_timeout` + Darwin stub, not just the group kill. The stub is
why `TimeOut()` uses `PROCESS_START_TIME_UNKNOWN`: a real start time
would take `SafeKill()`, which `SIGSTOP`s, waits for `STOPPED`, never
sees it, `SIGCONT`s, and returns `ESRCH` without ever sending
`SIGINT`.

**`xclock_gettime()` already exists** (`libntech/libutils/misc_lib.c`
93–103) and checks the return value. Copying `EvalContextEventStart()`
instead is the right *call-site* choice: `ProcessPollTimeNs` runs
inside a signal handler, and `xclock_gettime` `Log()`s. Unchecked
`clock_gettime` is AS-safe. Do not "fix" this by calling
`xclock_gettime` from here.

**No new link dependency.** `libntech/configure.ac` already
`AC_CHECK_LIB(rt, clock_gettime)` and `AC_REPLACE_FUNCS(clock_gettime)`.
`CLOCK_MONOTONIC` is ifdef'd the same way as `eval_context.c` 3930–3935
and `libcfnet/net.c` 311–317. Fallback is the right one.

**Integer types / overflow / `assert`.** `deadline = ProcessPollTimeNs()
+ timeout_ns` with `timeout_ns` a `long` and the assert
`timeout_ns < 1000000000` only on `ProcessWaitUntilExited` (not
`ProcessWaitUntilStopped`). Both callers pass `STOP_WAIT_TIMEOUT`
(999999999L). After the `MIN` with `SLEEP_POLL_TIMEOUT_NS` (1e7),
`tv_nsec` cannot exceed 1e9 even if the assert is compiled out.
`int64_t` nanoseconds from boot will not overflow on any machine this
code will run on. No defect.

**`timeout_ns <= 0`.** Old: `while (timeout_ns > 0)` skipped the
body and returned false without looking at the process. New:
`while (true)` inspects state once, then sees `remaining_ns <= 0`
and returns false — unless the process already exited / is a zombie,
in which case `ProcessWaitUntilExited` now returns **true**. No
caller passes `<= 0`. Not user-visible. Mentioned because it is a
real behavioural change.

**`CONTRIBUTING.md` hygiene (process section excluded, as instructed).**

- Both commits have `Changelog: Title`. Neither has `Ticket: CFE-…`.
  The changelog section says every changelog entry should carry a
  ticket. Hygiene miss, not a code miss.
- Titles are under 80 characters and do not end with punctuation.
- B-1 is one change plus the test it breaks. Fine as one commit.
- B-2 is two files that must ship together (`setpgid` without the
  sweep is a behaviour change with no payoff; the sweep without
  `setpgid` never passes `pgid == pid`). Do not split them. Do
  split the *policy* of "every child is a group leader" from the
  timeout sweep — that is the required change, not a commit split.
- B-2 has no test. Style/hygiene miss.
- New C follows Allman-4, 4-space, braces on `if`, pointer star on
  the right. Comments are slightly chatty but factual.
- `Changelog: Title` will generate a user-facing entry from a title
  that names poll loops / process groups. Acceptable if rewritten to
  the behaviour change (`exec_timeout` waited several times too long;
  `exec_timeout` left descendants running). Past tense is preferred
  for changelog titles; these are present tense.

**B-1 is not doing two things.** B-2 is doing one thing the wrong
width.

---

## 5. What I did not check

- I did not run the unpatched agent (would have required a checkout).
  Before-numbers are the author's plus my standalone probes of
  `nanosleep`, `sh`+`SIGINT`/`SIGTERM`, zombies, and `getpgid`.
- I did not run the full unit suite or any acceptance test other
  than `process_terminate_unix_test` (6/6) and the four throwaway
  `cf-agent` policies above.
- I did not run on Linux. The Darwin stub dominates the timings I
  saw; Linux `GetProcessState` can short-circuit on `ZOMBIE` and
  the ladder will look much faster. The fail-open (shell + exit 0
  during the `SIGINT` wait) is not Darwin-specific.
- I did not type Ctrl-C at an interactive `cf-agent`, and I did not
  fire `agent_expireafter` for real. Those conclusions are from the
  signal handlers, `setsid()`, and `cf-execd-runner.c` 277–315.
- I did not audit Windows / `pipes_windows` / `SafeKill` on a
  platform with a real `GetProcessState`.
- I did not prove the PID-reuse race or a `setpgid` failure in
  production.
- I did not read POSIX from a purchased spec; `nanosleep` "at least
  as long as requested" was confirmed by measurement (4.449 s for
  1.00 s requested) and by the Linux `nanosleep(2)` page's statement
  of the POSIX requirement.
- I did not read any `upstream-opinion-*.md` or `docs/handoffs/`.
- I did not rebuild `cf-agent` after uncommitted edits appeared; the
  binary I executed was the 19:24 libtool build of the committed
  integration branch.

---

*Reviewer: grok. Adversarial read of `26634ac1f` and `cb2561584` only.*
