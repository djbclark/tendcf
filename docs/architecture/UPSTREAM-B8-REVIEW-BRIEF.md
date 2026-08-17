# UPSTREAM REVIEW BRIEF — B-8, CFEngine core

**Frozen input, 2026-08-16.** Shared prompt given verbatim to each member of the
second-opinion panel for B-8. Do not edit it to reflect what the reviews found.

B-8 was discovered *by* the B-1/B-2 panel, so it has not itself been reviewed.
The register's rule is that no item is emailed upstream until it has been
second-opinioned.

---

## Your role

You are an independent reviewer of a C patch about to be offered to CFEngine
Core (Northern.tech). It was written by a different AI model. Your job is
**adversarial**: assume the patch is wrong and try to demonstrate it. Finding
nothing is a valid outcome, but only after a real attempt.

Prefer measurement over reasoning from memory. This patch exists because an
earlier confident claim by the same author — that a different patch closed this
same fail-open — was refuted by measurement.

## Where the code is

Repository: `~/src/cfengine-core`, a fork of `cfengine/core`.

```
git -C ~/src/cfengine-core show 326bcdb8d              # B-8, off master 17eb78e6d
git -C ~/src/cfengine-core log --oneline -1 master
```

The branch is `fix/exec-timeout-promise-result`, cut from `master` and
independently landable. `tendcf-integration` merges it with two other fixes;
review **B-8 alone**, off master, not the integration merge.

Relevant files: `cf-agent/verify_exec.c` (`RepairExec()`,
`VerifyExecPromise()`), `libpromises/timeout.c` / `timeout.h`,
`libpromises/actuator.c` (`PromiseResultUpdate`), `cf-agent/retcode.c`
(`VerifyCommandRetcode`).

A built `cf-agent` is at `~/src/cfengine-core/cf-agent/cf-agent`, but **it is
built from the integration branch**, not from B-8 alone — rebuild if you want
to measure B-8 in isolation. Stock 3.27.1 is at `/opt/homebrew/bin/cf-agent`.
To run a policy safely use a throwaway workdir:
`CFENGINE_TEST_OVERRIDE_WORKDIR=/tmp/somewhere` with `bin/cf-promises` symlinked
into it.

You have read access to the repo and the web. **Write nothing except your own
output file. Do not commit, push, branch, or modify any existing file.**

## The defect

A `commands:` promise whose `exec_timeout` fires can still be reported as
**promise kept**. `RepairExec()` hands the child's wait status to
`VerifyCommandRetcode()`, and with the default `kept_returncodes` an exit
status of 0 is "kept". Nothing consults whether the alarm fired.
`ACTION_RESULT_TIMEOUT` is declared and `VerifyExecPromise()` has a `case` for
it, but no path in the file ever returns it — the enum value is dead, so
`PROMISE_RESULT_TIMEOUT` is unreachable for this promise type.

Reproduced on stock 3.27.1 and on master:

```cfengine3
body common control { bundlesequence => { "t" }; }
body contain c { useshell => "noshell"; exec_timeout => "2"; }
bundle agent t
{
  commands:
      "/bin/sh" arglist => { "-c", "sleep 2.4; exit 0" }, contain => c;
}
```

```
verbose: Time out of process 9943
verbose: A: Promise REPAIRED
verbose: A: Aggregate compliance (promises kept/repaired) for bundle 't' = 100.0%
```

The claimed severity is a **fail-open**: a policy that runs a check under
`exec_timeout` and keys a later promise off the resulting class cannot tell
"the check passed" from "the check never finished".

## The fix

`TimeOut()` sets a `volatile sig_atomic_t` when the alarm fires;
`SetTimeOut()` clears it; `RepairExec()` reads it after the read loop and, when
set, classifies the promise as `PROMISE_RESULT_TIMEOUT` via `cfPS()` instead of
calling `VerifyCommandRetcode()`, and returns `ACTION_RESULT_TIMEOUT`.

## Questions to answer explicitly

1. **Is the severity claim right?** Is this genuinely a fail-open worth sending
   to `security@`, or is it a reporting/UX defect that belongs on a normal bug
   channel? Argue it either way, but decide. Consider what a policy can
   actually observe: classes from `kept_returncodes`, `PROMISE_RESULT_*`,
   `cf-agent` exit status, reporting/Enterprise data.
2. **Is the flag read at the right point?** `timed_out` is computed after the
   output read loop and before the alarm is disarmed. Can the alarm fire
   *after* that read and be missed? Can a *stale* flag from a previous command
   be observed — consider `background`, nested/looping promises, `cf-execd`'s
   long-lived process, and `nfs.c` / `cf-monitord/history.c`, the other
   `SetTimeOut()` users.
3. **Is `volatile sig_atomic_t` the right type and is the handler safe?**
   `TimeOut()` is installed with `signal(SIGALRM, ...)`. Does anything here
   introduce a new async-signal-safety problem?
4. **Does it change behaviour for commands that do NOT time out?** The claim is
   no. Verify it — including `exec_timeout` absent entirely, a command failing
   on its own merits, `background => "true"`, `action => "warn"`, `DONTDO`
   (`--dry-run`), and module (`a->module`) promises.
5. **Is classifying on the timeout instead of the exit status the right
   design?** Alternatives: report both; keep the retcode classification and add
   a class; make it opt-in via a body attribute. Is silently overriding a
   user's `kept_returncodes` acceptable when the command timed out? Could a
   policy legitimately *want* "timed out but exited 0" to be kept?
6. **Backward compatibility.** `PROMISE_RESULT_TIMEOUT` was previously
   unreachable for `commands:`. Does making it reachable break anything
   downstream — reporting, `cf-agent` exit codes, Enterprise data,
   `PromiseResultIsOK()`, acceptance tests that currently pass?

## Also worth checking, unprompted

- Whether `cfPS()` + `PromiseResultUpdate()` here can double-count a promise
  (an earlier draft placed the classification after `VerifyCommandRetcode()`
  had already classified, which produced 50% compliance for a single promise —
  the current patch replaces the classification rather than adding to it;
  confirm it really does).
- Anything in `CONTRIBUTING.md`'s code-style and commit-hygiene rules that the
  commit violates. Its *process* section is deliberately not followed.
- Missing tests, and what the right test would be.

## Deliverable

Write **one file**:
`docs/architecture/upstream-opinion-b8-<your-slug>-2026-08-16.md` in
`~/src/tendcf`, with `<slug>` from your launch prompt.

1. **Verdict** — *ship as is*, *ship with changes* (list them), or *do not
   ship* (say why).
2. **Severity verdict** — `security@` or ordinary bug channel, with reasoning.
3. **Defects found**, each with file and line, what breaks, and how to
   reproduce. Distinguish verified from suspected.
4. **The six questions**, answered by number.
5. **What you did not check.**

**Independence:** do not read any other `upstream-opinion-*.md` file, and do
not read `docs/handoffs/`. Everything else in either repo is fair game.
