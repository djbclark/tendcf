# Filing package: `exec_timeout` does not bound a `commands:` promise on macOS

**Status: reference record, kept in tendcf.** Nothing here is committed to a
CFEngine branch yet. The repro and the ticket text below are ready to paste;
the fix is **not written**, deliberately — see "What is not yet established".

Found 2026-08-16 while measuring whether the projection contract fixed by
[`projector-reconciliation-2026-08-16.md`](projector-reconciliation-2026-08-16.md)
is consumable by a generic bundle. It is an upstream defect, not a tendcf one,
and it is filed as such rather than designed around.

## Where this stands

| Item | State |
|---|---|
| Repro | **22 lines of policy, no data file** — reproduces 3/3 on 3.27.1, 1/1 on 3.29.0a |
| Affected | CFEngine 3.27.1 (Homebrew, arm64 macOS) **and** 3.29.0a.17eb78e6d (local build) |
| Platform | macOS/Darwin. **Not tested on Linux** — and Linux takes a different code path (below), so it may not reproduce there |
| Root cause | **Narrowed, not pinned.** Two candidate early-return paths named below |
| Fix | **Not written.** Direction proposed; needs an instrumented build first |
| Jira ticket | not filed — same Atlassian API token blocker as [PR 3](libntech-pr3-digest-init-filing-package-2026-08-15.md) |
| Prior art | **Unverified.** CFEngine's tracker is Jira, not GitHub issues, so a `gh search` finding nothing means nothing |

## The two defects

Both from the same cause. The first is the dangerous one.

### A — a command that exceeds `exec_timeout` is reported as *promise kept*

`exec_timeout => "2"` with a command that takes 5 s. The command is not
stopped, runs to completion, exits `0`, and CFEngine reports:

```
info: Command related to promiser '…/rc.sh' returned code '0' defined as promise kept
```

**5 runs out of 5**, so this is deterministic, not a race. A caller that keys a
class off `kept_returncodes` therefore cannot distinguish "the check passed"
from "the check timed out". For anything using a command promise as a
*precondition*, that inverts the safety property: the guard is satisfied
precisely when its verification failed to complete.

### B — firing the timeout *adds* a fixed ~9.2 s stall

`cf-agent`'s baseline cost on this policy is **0.10 s**, and a timeout that is
never exceeded costs nothing (`exec_timeout => "10"` on a 5 s command: 5.21 s,
against 5.13 s with no timeout body at all).

But whenever the alarm actually fires, the run takes **`exec_timeout` + ~9.2 s**,
regardless of the command:

| `exec_timeout` | command | wall clock | overshoot |
|---|---|---|---|
| 1 | `sleep 3` | 10.24 s | +9.2 |
| 1 | `sleep 8` | 10.39 s | +9.4 |
| 2 | `sleep 3` | 10.90 s | +8.9 |
| 2 | `sleep 8` | 11.20 s | +9.2 |
| 3 | `sleep 8` | 12.12 s | +9.1 |
| 5 | `sleep 8` | 14.24 s | +9.2 |
| 3 | `sleep 3` | 3.15 s | not exceeded — no penalty |
| 5 | `sleep 3` | 3.18 s | not exceeded — no penalty |

So a timeout meant to *bound* a command reliably makes the agent slower than
having no timeout at all. Nine seconds is far more than the ladder in
`GracefulTerminate()` can account for, whose two waits are ~1 s each.

The command is also not reliably stopped. With a payload that ignores `SIGINT`
and `SIGTERM` (`trap '' INT TERM; sleep 30`, `exec_timeout => "2"`) the run
takes **30.25 s** — `SIGKILL` is never delivered, because `SIGKILL` cannot be
trapped and would have ended it at ~2 s.

And when the direct child *is* killed, its descendants are not: a `sleep 30`
grandchild was observed orphaned and still running 28 s after its parent shell
had been terminated, holding the pipe open with `cf-agent` blocked reading it.

Defect A follows from this stall: during those ~9 s the command keeps running,
so a command that finishes inside the window is reaped normally and its exit
status reported as if nothing had gone wrong.

## Repro, paste-ready

No `host_specific.json`, no augments, no data — this is the whole thing.

```cfengine
body common control { bundlesequence => { "timeout_repro" }; }

body contain two_second_timeout
{
      useshell     => "noshell";
      exec_timeout => "2";
}

body classes only_on_zero
{
      kept_returncodes => { "0" };
      promise_kept     => { "check_passed" };
      scope            => "namespace";
}

bundle agent timeout_repro
{
  commands:
      "/bin/sh"
        arglist => { "-c", "sleep 5; exit 0" },
        contain => two_second_timeout,
        classes => only_on_zero,
        comment => "command runs 5s but exec_timeout is 2s";

  reports:
      check_passed::
        "BUG: promise reported KEPT even though exec_timeout=2s was exceeded by a 5s command";
      !check_passed::
        "EXPECTED: promise not kept";
}
```

```
$ cf-agent -f ./repro.cf -K
R: BUG: promise reported KEPT even though exec_timeout=2s was exceeded by a 5s command
```

**Expected:** the command is terminated at 2 s and the promise is not kept.
**Actual:** the command runs 5 s, exits 0, and the promise is kept.

For defect B, replace the `arglist` payload with
`"trap '' INT TERM; sleep 30; exit 0"` and time the run: 30.25 s.

## What the evidence shows

Line numbers are from the **local checkout at 3.29.0a.17eb78e6d**, stated as
such because citing a checkout's lines for a claim about a released binary is
an error this corpus has already made once and recorded (`projector-reconciliation-2026-08-16.md`, C-2).
The *behaviour* above is measured on the 3.27.1 binary as well.

The timeout handler **does** fire and **does** reach the terminate call — at
verbosity the run prints `verbose: Time out of process 23095` at ~2 s, which is
emitted inside the `ALARM_PID != -1` branch immediately before
`GracefulTerminate()` (`libpromises/timeout.c:38–51`). So the alarm, the
handler, and `ALARM_PID` (set in `libpromises/pipes_unix.c:241`) are all fine.

What does not happen is `SIGKILL`. `GracefulTerminate()`
(`libpromises/process_unix.c:241`) is a ladder — `SIGINT`, wait, `SIGTERM`,
wait, `SIGKILL` — where each wait is `ProcessWaitUntilExited(pid, STOP_WAIT_TIMEOUT)`
and `STOP_WAIT_TIMEOUT` is `999999999L` **nanoseconds**, i.e. just under one
second (`process_unix.c:135`). With a child that traps `INT` and `TERM`, the
ladder must reach `SIGKILL` at roughly 2 s after the alarm. It measurably does
not.

The ladder can only exit early where `ProcessWaitUntilExited()` returns true,
which it does for `PROCESS_STATE_DOES_NOT_EXIST` **and for
`PROCESS_STATE_ZOMBIE`** (`process_unix.c:86–107`). On macOS that state comes
from `libpromises/process_unix_stub.c:38`, which distinguishes only "exists" from
"does not exist" via `kill(pid, 0)` and returns `PROCESS_STATE_RUNNING` for
everything alive.

**macOS uses the stub.** There is no `process_darwin.c`; `libpromises/Makefile.am:210–216`
selects `process_unix_stub.c` for any platform that is not Linux, AIX, HP-UX,
Solaris or FreeBSD. This is also why the Linux behaviour may differ and why
this report does not claim a Linux repro.

## What is not yet established

The mechanism is narrowed to "`GracefulTerminate()` returns before `SIGKILL`",
with exactly two candidate early-return paths — the `ProcessWaitUntilExited()`
true-return after `SIGINT`, or the one after `SIGTERM`. **Which one, and why,
is not proven**, and this document does not guess. Confirming it needs an
instrumented debug build logging each rung of the ladder and each
`GetProcessState()` result.

The ~9.2 s figure is the sharpest clue and does not currently have an
explanation. It is stable across `exec_timeout` values, so it is a fixed cost
of the alarm path rather than anything proportional; and it is roughly 9×, not
2×, the ~1 s `STOP_WAIT_TIMEOUT` that bounds each rung of the ladder. Whatever
accounts for those nine seconds is likely the same thing that swallows the
`SIGKILL`, so the number is worth explaining before anything is patched.

That is the next step, and it should happen **before** a patch is proposed,
because the obvious fix and the correct fix may differ:

- If the ladder is exiting early on a misread process state, the fix is in
  `GetProcessState()` on Darwin — a real `process_darwin.c` using `sysctl`/
  `proc_pidinfo`, which is a missing-platform-support gap rather than a logic bug.
- If the ladder is completing but signalling the wrong target, the fix is to
  make `cf_popen()` put the child in its own process group and signal the
  **group** — which would also fix the orphaned-grandchild half of defect B,
  but is an invasive change to a function used everywhere in the codebase.

The grandchild observation argues the process-group change is needed
*regardless* of which path causes defect A, since killing only the direct child
cannot bound a command that spawns anything.

## What this blocks in tendcf

The generic bundle — the `.cf` that consumes `tendcf_service` and
`tendcf_interlock`, left explicitly undecided by
[`projector-reconciliation-2026-08-16.md`](projector-reconciliation-2026-08-16.md) §11 —
**cannot use `exec_timeout` to enforce an interlock's `timeout_seconds`** on
macOS, which is most of this fleet.

This matters more here than it would in a generic policy, because of what an
interlock *is*. P-5 keeps `pre_action` argv in per-host Augments so that
"the Caddyfile moved" stays an ordinary supervision edit rather than a
privileged policy-tree change. The entry's whole purpose is to block a
dangerous promise when a precondition cannot be verified. Defect A makes a
pre-action that hangs indistinguishable from one that passed — the exact
inversion an interlock exists to prevent.

Three things follow, none of them decided here:

1. `timeout_seconds` currently has **no faithful executor** on macOS. Until
   this is fixed, a bundle that honours the field must implement the timeout
   itself rather than delegate to `exec_timeout`.
2. The schema's `timeout_seconds` has `"minimum": 1` and **no maximum**, while
   `exec_timeout`'s syntax range is `1,3600` (`libpromises/mod_exec.c:36`). A
   conforming goal file can therefore name a timeout the executor will reject.
   That is a contract/executor mismatch independent of this bug.
3. A wrapper (`timeout(1)`-style) inserted by the bundle would put an argv the
   person never approved in front of one they did, which the consent gate has
   to have an answer for before it is adopted.

## Verification record

| Claim | How measured |
|---|---|
| Defect A deterministic | 5/5 runs, `CLASS d_cls DEFINED`, 3.27.1 |
| Defect A on master | 1/1, locally built 3.29.0a.17eb78e6d |
| Defect A standalone | 3/3 with the 22-line repro, no data file |
| Defect B, ~9.2 s stall | 8-cell matrix over `exec_timeout` ∈ {1,2,3,5} × `sleep` ∈ {3,8} |
| Baseline is not the cause | trivial policy, no `commands:` → `real 0.10` |
| Unfired timeout is free | `exec_timeout 10` on `sleep 5` → 5.21 s vs 5.13 s with no timeout body |
| `SIGKILL` never delivered | `trap '' INT TERM; sleep 30` → `real 30.25` |
| Handler does fire | `verbose: Time out of process 23095` at ~2 s |
| Orphaned grandchild | `pgrep` sampling: `sleep 30` alive at t=29.8 s, parent shell gone |
| Direct binary is killed correctly | `/bin/sleep 10`, `exec_timeout 2` → process gone by t≈3 s |

The last row is the control: `exec_timeout` **is** honoured when the command is
a single process with no children, which is why this went unnoticed.

Two wrong readings were produced and discarded on the way here, recorded
because each was refuted by a measurement that is now a row above. The first
claimed `exec_timeout` was ignored outright, mistaking a constant cost for
command time; the timing matrix refutes it — an unfired timeout is free, so
there is no constant cost, and the penalty tracks `exec_timeout` rather than the
command. The second claimed the stall was cf-agent's startup; the 0.10 s
baseline refutes that. The defect is real but neither of those was its shape.

## Related records

- [`projector-reconciliation-2026-08-16.md`](projector-reconciliation-2026-08-16.md) — the data contract whose consumability this was measuring
- [`libntech-pr3-digest-init-filing-package-2026-08-15.md`](libntech-pr3-digest-init-filing-package-2026-08-15.md) — house form for this document, and the same Jira token blocker
- [`cfengine-pr2-simulate-json-report-2026-08-15.md`](cfengine-pr2-simulate-json-report-2026-08-15.md) — the other open upstream thread
