# Second opinion — CFE-4727 termination fix (`fix/exec-timeout-alarm-pid`, 254cbe593)

**Reviewer:** fable-deep (Claude Fable 5, xhigh), 2026-08-18.
**Repo reviewed:** `/Users/djbclark/src/core-alarmpid` at `254cbe593` (clean tree, verified
`git status --porcelain` empty of tracked changes before and after review; the only
untracked entry is a pre-existing `review.md` I did not touch).
**Method:** read every file the brief names in full plus `process_unix.c`, `unix.c`,
`cf-agent.c`, `cf-execd.c`, `server_common.c`, `evalfunction.c` excerpts, and the dcs
harness; ran the unit and acceptance tests myself in both fixed and reverted
configurations (reverted via a scratch-linked binary, never touching the worktree);
disassembled the built dylib to measure the residual window and the handler's codegen.
Every claim below is tagged measured (I ran/observed it) or reasoned (I read it).

**Verdict: ship with changes — two small ones (swap `sigprocmask()` for
`pthread_sigmask()`, soften one commit-message sentence), neither a correctness
blocker. The fix's mechanism is right, both tests genuinely discriminate (measured in
both directions), and the residual race is quantified below and acceptable.**

---

## Trap control

1. **Return codes through pipes:** every test/compile run wrote `RC=$?` to a distinct
   scratch file immediately after the command (`unit_fixed_rc.txt`, `unit_old_rc.txt`,
   `acc2_rc.txt`, `acc_old_rc.txt`, `accdir_rc.txt`, `cc_old_rc.txt`, `cc_new_rc.txt`,
   `link_*_rc.txt`); all numbers quoted below come from those files, not shell pipes.
   All compiled artifacts used distinct output filenames in the scratchpad.
2. **`--bindir`:** not used. I passed explicit `--agent=` and `--cfpromises=` paths.
   The trap fired for real anyway, differently than described: my first harness run
   died in **0.26s** with `fakeroot: command not found` (testall's default gainroot on
   a non-root host). Per the trap's rule that a ~2s failure is a harness bug, I did not
   report it as a result; `--gainroot=env` fixed it and the test then ran 19.41s.
3. **libtool wrappers:** `tests/unit/timeout_test` and the scratch-linked binaries are
   wrapper scripts (verified with `file`); I executed `.libs/` binaries directly.
   `--cfpromises` pointed at `cf-promises/.libs/cf-promises`. The harness sets
   `CFENGINE_TEST_OVERRIDE_WORKDIR` itself (testall line 480, verified).
4. **Single-process probes:** I wrote no wall-clock probe of my own; the commit's unit
   test payload chains `exec sleep 30` (single process, verified in source). The
   acceptance payload deliberately does *not* exec (see attack 7 — that is a feature,
   not a trap violation).
5. **Platform:** all measurements here are macOS 26.6.1 arm64 with the stub
   `GetProcessState()` and the CFE-4728 overshoot; measured wall clocks (19.41s
   terminated, 31.96s ran-to-completion) sit exactly in the band the commit predicts
   for Darwin. Linux behavior (~2+2s termination, glibc signal semantics) is reasoned,
   not measured. Where a claim depends on Linux specifics I say so inline.
6. **Pre-fork flake under load:** I ran the unit suite unloaded only (it passed 7/7);
   I did not attempt to reproduce the known pre-fork flake and treat it as documented.
   Nothing I saw suggests it manifests differently than described.

**Binary-provenance check (extra):** the test binary's load command points at an
*installed* prefix (`~/opt/cfengine-dev-4727/lib/libpromises.3.dylib`), not the build
tree. I verified by SHA-1 that the installed dylib is byte-identical to
`libpromises/.libs/libpromises.3.dylib`, and disassembled `cf_pclose` in it to confirm
the fix is present in the code actually executed (inlined `ClearAlarmedPid` with
sigset constant `0x2000` = bit 13 = SIGALRM). Without this check, a stale install
would have silently invalidated every "fixed" measurement.

---

## Attack points

### 1. Does `ClearAlarmedPid()` close the race or narrow it?

Narrows it — to a window I measured, and which is smaller than the harm model needs.

Measured (objdump of the built dylib): in the dangerous scenario (child exits
normally just under the wire; alarm expires after the reap), the instruction path
from `waitpid()` returning inside `cf_pwait` (0x65038) to the `sigprocmask(SIG_BLOCK)`
call in `cf_pclose` (0x65934) is: the EINTR-loop exit branch, the `WIFEXITED` check,
`WEXITSTATUS`, one **level-gated `Log(LOG_LEVEL_DEBUG)` call**, `cf_pwait`'s epilogue,
then 7 instructions of inlined `ClearAlarmedPid` setup — roughly **25 instructions
plus two function calls (Log early-out, libc sigprocmask wrapper) plus the syscall
entry**. The author's "handful of instructions" understates this by about 5x, and
with `-d` debug logging enabled the Log call does real formatting/I/O and the window
stretches to microseconds. The order of magnitude of the claim survives; the literal
wording doesn't.

Whether the window matters splits into two cases:

- **Alarm in window, pid NOT recycled** (the likelier variant, which the brief's
  framing skips): `TimeOut()` finds the stale pid, `getpgid()` fails with ESRCH (one
  WARNING log line), `GracefulTerminate` → `kill()` fails ESRCH harmlessly — but
  `TIMEOUT_SIGNALLED` is set, so verify_exec reports "was terminated" for a command
  that actually finished just under the wire. Cosmetic misreport; the pre-fix code
  produced the mirror-image misreport deterministically. Acceptable.
- **Alarm in window AND pid recycled**: `Kill()` with `PROCESS_START_TIME_UNKNOWN`
  does a plain `kill(2)` (process_unix.c:229-233, read) — an innocent process gets
  the INT/TERM/KILL ladder. But recycling requires the kernel's pid counter to wrap
  the entire pid space in the sub-microsecond between reap and block. Not credible
  outside deliberate pid-churn adversarial conditions, and even there it also
  requires the alarm to expire in that exact window. Reasoned, both platforms.

Also checked the inverse invariant: there is now **no** point in either closer where
`ALARM_PID` is cleared while the child is unreaped — the original bug shape cannot
recur through these functions. The claim that the alarm firing *during* the masked
section is handled correctly also holds: the pending SIGALRM is delivered on the
`SIG_SETMASK` restore, finds `ALARM_PID == -1`, and takes the benign no-process path
(reasoned from the code; consistent with the passing unit test).

One more window the fix slightly *extends* (reasoned, worth one line): `fclose()` in
`cf_pclose` now runs with `ALARM_PID` still set, so an alarm during `fclose` runs the
full multi-second ladder (with its non-async-signal-safe `Log()` calls) while the
main thread may hold stdio/heap locks. The identical exposure already existed for the
entire read loop pre-fix (alarm during `fgets`), so this is a marginal widening of a
pre-existing hazard class, not a new class.

### 2. `sigprocmask()` vs `pthread_sigmask()`

The multithreaded reachability is **real, not theoretical** — I verified `cf_pclose()`
is called from cf-serverd per-connection worker threads (`server_common.c:1827`,
threads spawned at `server.c:237`) and from cf-execd's `LocalExecThread`
(`cf-execd.c:850-866` → `cf-execd-runner.c:384`). So `ClearAlarmedPid`'s
`sigprocmask()` does execute on non-main threads of multithreaded processes, where
POSIX leaves its behavior unspecified.

It is still not a live defect, for a reason the author's stated rationale doesn't
quite reach: I grepped every `SetTimeOut()` caller (`verify_exec.c:308`, `nfs.c:403,
1121,1434,1459`, `history.c:242`) and every `alarm()`/SIGALRM registration — **no
thread in cf-serverd or cf-execd ever arms SIGALRM or installs `TimeOut`** (the only
other SIGALRM user in the codebase is cf-monitord's sniffer, single-threaded main
loop). With no SIGALRM ever pending, the mask operation is a per-thread no-op on
every real platform (Linux and macOS both implement `sigprocmask` as the calling
thread's mask). The author's supporting claim — nothing else in the main thread
blocks SIGALRM; the only other `sigprocmask` in the file runs in the forked child —
is verified true by grep (pipes_unix.c:239 is the only other use in the entire
libpromises/cf-agent/daemons tree).

**Recommend the one-word swap to `pthread_sigmask()` before offering upstream**: it
is unconditionally correct, costs nothing, and Northern.tech reviewers who know
cf_pclose's serverd reachability will otherwise ask.

Honesty note the author should not lose: in cf-agent itself, per-thread masking (by
*either* call) cannot guard against a process-directed SIGALRM being delivered to a
*different* thread — and cf-agent can transiently be multithreaded via
`isreadable()`'s worker thread (`evalfunction.c:9942`), which does not mask SIGALRM
(verified, lines 9796-9812: masking is Termux-only). Blocking SIGALRM in the closing
thread then actively redirects delivery to the worker. In that corner the guard
degrades to a plain unguarded post-reap clear — still strictly better than pre-fix.
The corner requires a lingering isreadable thread (hung read) coinciding with a timed
exec; no masking API fixes it; out of scope here, belongs with the handler-hardening
note under uncertainty 4.

### 3. The three error paths that now leave `ALARM_PID` set

Verified individually (all reasoned from source; paths are rare/unreachable so not
measured):

- **`fd >= MAX_FD` in `cf_pclose` (line 903):** practically unreachable —
  `ChildrenFDSet()` (line 142-148) grows `MAX_FD` to `fd+32` at popen time and it
  never shrinks, so a legitimately opened pipe cannot exceed it at close time. If
  reached anyway: the pid was never looked up, nobody reaps the child (see reaper
  check below), so either it is alive (alarm can still usefully kill it) or a zombie
  holds the pid (a signal to a zombie is a discarded no-op). The author's claim holds.
- **Failed `fclose()`:** the commit message's wording is loose here — in `cf_pclose`
  a failed `fclose` does **not** return early (line 917-922 logs and proceeds to the
  wait and the clear), so nothing is left set there. The early-return fclose/close
  failures live in `cf_pclose_full_duplex` (lines 1013-1049): child unreaped, pid
  unrecyclable, pending alarm keeps its target. Holds. (Pre-existing and unchanged:
  those paths also leak the write-side fd and the child becomes unreapable because
  its `CHILDREN[]` entries were already zeroed at lines 1003-1010.)
- **`pid == 0` in `cf_pclose_full_duplex` (line 1051):** returns before the wait;
  whatever child exists is unreaped; if `ALARM_PID` names it the alarm still works.
  Holds. Also note `ClearAlarmedPid(0)` can never falsely clear anything: `ALARM_PID`
  is only ever -1 or a positive fork return (all writers checked — see attack 4).

**Global-reaper check** (this is what the zombie-holds-pid argument actually rests
on): I grepped for `wait(NULL)`/`waitpid(-1)`. cf-execd's main loop has a
`waitpid(-1, WNOHANG)` reaper (`cf-execd.c:563`) and cf-agent has
`WaitForBackgroundProcesses()` (`cf-agent.c:2442-2461`, shutdown only). cf-execd
never arms an alarm, and the cf-agent reaper runs after evaluation ends, so in every
process where a pending alarm exists, nothing can reap these children behind the
error paths' backs. The argument is sound where it matters.

Residual wart, acknowledged as pre-existing: `cf_pclose` with `CHILDREN[fd] == 0`
(double-close) still calls `cf_pwait(0)` → `waitpid(0, ...)`, waiting on the whole
process group — identical pre-fix, out of scope.

### 4. `cf_pclose_full_duplex()` symmetry fix

I reran the author's grep independently and wider. `SetTimeOut()` callers are exactly
`verify_exec.c`, `nfs.c`, `cf-monitord/history.c` — and I read all four nfs.c sites
(including the remount paths, whose `VerifyMount`/`VerifyUnmount` internals at lines
940/1008 use `cf_popen`) and history.c's stream sampling: all half-duplex
`cf_popen*()`/`cf_pclose()`. The full-duplex closer's callers (`pipes.c:195,245`,
`evalfunction.c:4170` json_pipe, `mod_custom.c:443`) never arm a timeout. Confirmed:
no `exec_timeout`-guarded path reaches it.

"Does anything else set `ALARM_PID` some other way?" — yes, and the commit message
doesn't mention them: **`ShellCommandReturnsZero()` (`unix.c:225`) sets
`ALARM_PID = pid` in the parent and never clears it after its internal reap
(lines 236-269)**, and two forked children set it to -1 (`unix.c:184`,
`cf-agent.c:2239`) as hygiene. Every `GenericCreatePipeAndFork()` also publishes
unconditionally (line 272), so package-module/full-duplex children *do* sit in
`ALARM_PID` while open. None of these run under an armed timeout (cross-checked
against the SetTimeOut windows), so the symmetry fix changes nothing for them except
under an already-leaked alarm — the B-15/B-16 family, exactly as the author says. The
conditional clear is additionally *more* correct than the old unconditional pre-clear
for interleaved pipes (closing pipe A can no longer wipe a later-registered pipe B's
pid). Net-positive; ship it (see uncertainty 3).

### 5. The rewritten `TIMEOUT_SIGNALLED` comment

For what the comment literally enumerates — cases where the alarm fires with **no
process registered** (`ALARM_PID == -1`) — the two windows are accurate and, as far
as I could construct, complete: `SetTimeOut()` pre-clears and the fork publishes
(window 1, which also loosely covers fork *failure* — cf_popen returns with
`ALARM_PID` still -1), and the post-reap clear (window 2, including an alarm arriving
pended during the masked section and delivered on restore).

But there is a **third window of the dual kind — the alarm firing with a stale pid
still registered — that neither the comment nor the fix covers**, and it is the most
substantive thing I found: all four `cf_popen*` variants' parent-side
fdopen-failure paths (`pipes_unix.c:458-475, 588-605, 668-685, 787-804` — eight
early returns) call `cf_pwait(pid)` — a reap — and return NULL **without clearing
`ALARM_PID`**. `RepairExec()` then returns `ACTION_RESULT_FAILED` at
`verify_exec.c:371-375` **without calling `ClearTimeOut()`**, so the alarm stays
armed for up to the full `exec_timeout` with `ALARM_PID` naming a reaped, recyclable
pid — and `TimeOut()`'s `Kill(..., PROCESS_START_TIME_UNKNOWN)` is a plain unchecked
`kill(2)`. That is the same defect *class* this commit's rationale is built on
("deregistered only after the reap, guarded"), with a window measured in seconds to
minutes rather than instructions. It is **pre-existing and byte-for-byte unchanged
by this commit** (I diffed: the pre-fix paths were identical), it is gated on
`fdopen()` failing (rare — ENOMEM/EMFILE), and it intersects the known leaked-alarm
family (the missing `ClearTimeOut()` is a B-15/B-16 member). So: not a blocker, not a
reason to grow this commit — but the fix's invariant story ("ALARM_PID never names a
reaped pid while SIGALRM can fire") is only established for the two `cf_pclose`
closers, and the follow-up ticket should name these eight reap sites explicitly
(the mechanical fix is `ClearAlarmedPid(pid)` after each `cf_pwait` there, which this
commit's new function makes possible for the first time).
`ShellCommandReturnsZero()`'s uncleared post-reap registration (attack 4) is a ninth
member of the same family, dormant for the same reason.

The comment itself is not *wrong* — it describes the no-process cases and describes
them correctly. It should just not be read as a completeness claim about stale
registration.

### 6. The pre-fork race, left unfixed

Right scope call. Reasons: (a) different mechanism — arming order versus clearing
order — with a different fix shape (publish-under-block inside the fork path, or
re-order arm after fork, both touching `SetTimeOut()`'s contract with
`TimeOutIsArmed()`-driven `setpgid`, which is genuinely its own change); (b) it is
disclosed in three places (commit message, the rewritten timeout.c comment's first
window, the unit test's comment block); (c) folding it in would have made this
commit's discrimination testing ambiguous. The consequence when it fires is bad —
the command runs entirely unbounded, and `cf_pwait` blocks with no alarm left, the
very failure this commit's title names, via a different door — which is exactly why
it deserves its own ticket rather than a rider.

One wording objection: the commit message's first paragraph ends "this closes the
termination half, **so the guarantee itself holds**." While the pre-fork window is
open the guarantee does *not* unconditionally hold; the body admits this four
paragraphs later. Soften that sentence (e.g. "so the guarantee holds once the child's
pid is registered") before offering upstream. And the ticket must actually get filed
— the deferral is only defensible with the ticket in existence.

### 7. The tests

**Both discriminate; I measured both, in both directions, without modifying the
worktree** (method: extracted `HEAD~1:libpromises/pipes_unix.c` via `git show`,
compiled it with the project's exact flags — clean, 0 warnings, RCs to files — and
libtool-relinked both the unit test and cf-agent against the old object into the
scratchpad; `nm` confirmed the old `cf_pclose`/`cf_popen_sh`/`PipeToPid` bound
in-binary while everything else, including the comment-only-changed timeout.c, came
from the shared dylib, making the hybrid semantically HEAD~1 for these paths).

- Unit test, fixed: **7/7 pass, RC=0, 37.44s** (matches author's ~35s).
- Unit test, old pipes_unix: **fails exactly one test,
  `test_pclose_leaves_the_alarm_its_process`, at `timeout_test.c:144`
  (`TimeOutSignalledProcess()`), RC=1, 49.97s** — the payload's full 30s sleep ran
  out inside the wait, reproducing the defect. Note: the brief and author say the
  failure is at **:129**; :129 in the committed file is `SetTimeOut(2)`. The line
  number in the author's report is stale (almost certainly from the pre-reorder
  version of the test); the *assert* is the one claimed. Cosmetic, worth correcting
  in the register so nobody chases a phantom discrepancy later.
- Acceptance, fixed binaries: **Pass, 19.41s** (bound 25s).
- Acceptance, cf-agent relinked with old pipes_unix: **FAIL (UNEXPECTED FAILURE),
  31.96s** — the sleep ran to completion; matches the author's 32s.
- All six tests in `04_exec_timeout/`: run kicked off during this review; result
  recorded at the end of this file.

Could the acceptance test pass unfixed for an unrelated reason? No mechanism found:
unfixed, nothing signals the child (`ALARM_PID` cleared before the wait, and the
one-shot alarm is spent), so `oc_completed` necessarily gets touched at ~t=30 and
`elapsed >= 30 > 25` — both the `terminated` and `bounded` classes fail
independently. `dcs_passif_expected` (dcs.sub.cf:1065-1090, read) requires **all**
expected classes AND'd, so either failure alone fails the test. The init bundle's
marker deletion protects against stale-marker false passes across runs.

Two deliberate scope limits worth stating (neither is a defect): the unit test
registers the pid directly, so it never exercises the production arming order (that
is the point — avoiding the pre-fork race) nor the `setpgid`/group-kill path (child
forked with no timeout armed; `getpgid(child) != child`, so `TimeOut()` skips the
group kill — which is also why the test is safe to run: a group kill there would
have hit the test runner's own group). The acceptance test covers the production
arming order and the group-lead shape end-to-end. Conversely, the acceptance test's
`terminated` marker would tolerate a silently-failed *group* kill (an orphaned
grandchild `sleep` would touch `oc_completed` only after the check bundle has
already run) — termination of the direct child is what it pins, which is this
commit's subject; the descendants test next door pins the rest.

---

## The author's uncertainties, by name

**1. The residual pid-recycling race.** Agree with the acceptance, with the framing
corrected by measurement: the window is ~25 instructions **plus a level-gated Log()
call plus the libc wrapper and syscall entry** — "a handful of instructions" is about
5x optimistic, and debug-level logging stretches it to microseconds. It still doesn't
matter: harm requires pid-space wrap within that window, and the likelier
alarm-in-window-without-recycle variant costs only a wrong message variant in an
already-TIMEOUT-classified promise. Pre-fix dropped the guarantee deterministically;
this is strictly dominated. Accept.

**2. `sigprocmask()` thread-safety.** The author's stated reasoning ("nothing else in
this file blocks SIGALRM in the main thread") is true — I verified it — but it is not
the reason this is safe: `cf_pclose` demonstrably runs on cf-serverd and cf-execd
worker threads. It is safe because no thread in those daemons ever arms SIGALRM
(verified by exhaustive grep of `SetTimeOut`/`alarm`/SIGALRM registrations). Since
the defense rests on a usage invariant rather than the call's semantics, and
`pthread_sigmask` is a free strict improvement, **make the swap** — that is the
"changes" in my verdict. Also recorded under attack 2: no per-thread mask can stop
cross-thread delivery in the transiently-multithreaded cf-agent corner
(`isreadable()` worker); that residue is out of scope and survives either call.

**3. Full-duplex symmetry fix's blast radius.** Ship it. The widening exists only
under an already-leaked alarm, covers only the reap wait (the leaked alarm could
already kill the module child during its entire open lifetime, since every fork
publishes `ALARM_PID`), and the conditional clear is strictly more correct than the
old unconditional pre-clear under pipe interleaving. Waiting would preserve an
asymmetric pattern that invites the next person to copy the broken half.

**4. Non-volatile `ALARM_PID`.** For **this commit's clear site**, the
barrier argument is sound and I verified the codegen: the store sits strictly between
the two `sigprocmask` calls (0x65934…0x65960), and external calls pin ordering for an
external-linkage global; no plausible compilation regime (libc is outside any LTO
unit) breaks it. `volatile` is unnecessary *here*. But the disassembly of the
**pre-existing** `TimeOut()` handler shows why the global still deserves hardening in
a follow-up: the compiler reloads `ALARM_PID` at each use (0x5c950, 0x5c978, 0x5c9a8,
0x5c9b4 — forced by the interleaved opaque calls), and the group-kill guard compares
the saved `pgid` against a *fresh* reload. In the cross-thread-delivery corner from
uncertainty 2, `getpgid` failing on a stale pid (`pgid == -1`) plus a concurrent
clear reloaded as -1 makes the guard compare -1 == -1 and execute
`kill(-(-1)) = kill(1, SIGKILL)` at 0x5c9c0 — an attempted SIGKILL of pid 1 (which
kernels protect, but still). Single-threaded — the only configuration where
`TimeOut` is ever installed today — this is impossible; it needs the lingering
isreadable-thread pathology. Pre-existing, not this commit's regression, and this
commit *shrinks* the stale windows feeding it. Recommendation for the follow-up
family: `volatile`, plus read `ALARM_PID` once into a local at handler entry.

**5. The pre-fork race's scope decision.** Defensible and disclosed; see attack 6.
The commit's *title* is honestly scoped ("a command that closed its output"); the one
overreaching sentence ("so the guarantee itself holds") should be softened, and the
ticket actually filed. With those, no reader is misled about what is guaranteed.

---

## Pre-existing defects deliberately not fixed — deferral judgment

- **Pre-fork publish race:** defer, correctly (above). Entangled in subject but not
  in mechanism; disclosed everywhere it needs to be.
- **CFE-4728 / CFE-4718 (Darwin ladder overshoot, stub process state):** defer,
  correctly — they only inflate this fix's timing margins, and the tests budget for
  them honestly (measured: 19.41s against a 25s bound — ~5.6s headroom unloaded;
  the author additionally reconfirmed under 4×8-way load, which I did not repeat).
  The margin is adequate, not lavish; if CI hosts are slower than this laptop the
  first symptom will be this test brushing 25s, which is worth one sentence in the
  PR description.
- Newly named here, same family, defer to a named follow-up: the eight
  `cf_popen*` fdopen-failure reaps without `ClearAlarmedPid` + `RepairExec`'s
  missing `ClearTimeOut` on `pfp == NULL` (attack 5), and
  `ShellCommandReturnsZero`'s uncleared post-reap registration (attack 4). None is
  entangled enough to block: all are gated on rare failures or leaked alarms,
  all predate this commit, and this commit's new `ClearAlarmedPid()` is the tool a
  follow-up needs anyway. Shipping without them is coherent *provided the follow-up
  ticket names them* — silence would leave upstream believing the invariant is fully
  established when it is established for the two closers only.

---

## Result of the full-directory acceptance run

**Measured: all six tests in `08_commands/04_exec_timeout/` pass with the fixed
binaries — 6/6, RC=0, 90.40s total** (author claimed 6/6 in 89s), including
`timeout_kills_descendants.cf` and `timeout_does_not_leak_to_next_promise.cf`, the
two most likely to notice a regression from the changed clear ordering. Final
`git status --porcelain` on the worktree after all review activity: tracked files
untouched (sole entry is the pre-existing untracked `review.md`).

---

## Summary

| Claim | Status |
|---|---|
| Unit test 7/7 with fix (~35s) | **Measured: 7/7, RC=0, 37.44s** |
| Unit test fails only at `TimeOutSignalledProcess()` when fix reverted | **Measured: 1/7 fail, that assert — at :144, not the reported :129** |
| Acceptance test passes with fix (~18-20s) | **Measured: Pass, 19.41s** |
| Acceptance test fails at ~32s when fix reverted | **Measured: FAIL, 31.96s** |
| All 6 directory tests pass, ~89s | **Measured: 6/6, RC=0, 90.40s** |
| 0 new warnings in pipes_unix.c | **Measured: both versions compile warning-free, project flags** |
| timeout.c change comment-only | **Verified from diff** |
| `SetTimeOut` callers all half-duplex | **Verified by independent grep + reading all call sites** |
| Residual window "a handful of instructions" | **Measured ~25 insns + 2 calls + syscall — understated ~5x, conclusion survives** |
| cf_pclose unreachable from worker threads | **False as reachability (serverd/execd threads reach it) — but safe; swap to pthread_sigmask** |

**Ship with changes:** (1) `pthread_sigmask` swap in `ClearAlarmedPid()`; (2) soften
"so the guarantee itself holds" in the commit message; and file the pre-fork ticket
plus a follow-up naming the eight fdopen-failure reap sites and the
`pfp == NULL` `ClearTimeOut` leak. The fix itself is correct, minimal, and now has
its central claims independently measured on this host.
