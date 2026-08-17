# Reconciliation — the B-1/B-2 second-opinion panel

**2026-08-16.** Adjudicates `upstream-opinion-{cursor,gemini,grok}-2026-08-16.md`
against the frozen brief [`UPSTREAM-B1-B2-REVIEW-BRIEF.md`](UPSTREAM-B1-B2-REVIEW-BRIEF.md).
The register's rule: no item is emailed upstream until it has been
second-opinioned and its fork issue updated with what the review found.

## §0 Provenance

Three non-Claude CLIs, run headless from `~/src/tendcf` on 2026-08-16, each
given the same brief and told not to read the others' output or
`docs/handoffs/`:

| slug | invocation | output |
|---|---|---|
| `gemini` | `gemini -p --effort high --add-dir ~/src/cfengine-core` | `upstream-opinion-gemini-2026-08-16.md` |
| `cursor` | `cursor-agent -f -p` | `upstream-opinion-cursor-2026-08-16.md` |
| `grok` | `grok --prompt-file --effort high` | `upstream-opinion-grok-2026-08-16.md` |

Grok noticed uncommitted follow-up appearing in the tree mid-review and
explicitly froze on the two reviewed SHAs instead. That was the right call and
is why its verdicts remain comparable with the other two.

A first launch of `grok -p` and `gemini -p` failed: in both CLIs `-p` takes the
prompt as its *value*, so `-p --always-approve "…"` consumed the next flag and
the prompt was dropped. Relaunched with the prompt bound to `-p` (or
`--prompt-file`). Noted because it produced two zero-cost "reviews" that looked
like completions.

## §1 The headline result — B-1 does not close the fail-open

**All three panels converged on this, and it is the reason the gate exists.**

B-1 was filed claiming that a timed-out `commands:` promise is no longer
reported as *promise kept*. That claim is **withdrawn**. It is true of the one
cell measured (`sleep 5` / `exec_timeout => "2"`) and false in general.

Why that cell flipped: before B-1, SIGTERM arrived at ~timeout + 4.5 s, by which
time `sleep 5` had finished and the shell had exited 0. After B-1, SIGTERM
arrives at ~timeout + 1 s and kills the shell first, so `cf_pwait()` returns -1
and the promise fails. **A race won by shrinking the window, not a timeout being
reported.**

- **cursor** derived it from the source (`RepairExec()` never returns
  `ACTION_RESULT_TIMEOUT`; the enum case is dead) and marked the decisive case
  *suspected, not re-run*.
- **grok** measured it: `sleep 2.4` under `exec_timeout => "2"` gave
  `Time out of process` followed by `returned code '0' defined as promise kept`,
  `Promises kept in 't' = 1`.
- **This session** re-measured it independently on both the fork build and stock
  3.27.1: `Promise REPAIRED`, **aggregate compliance 100.0%**, with the timeout
  logged and discarded. Confirmed upstream behaviour, not something we
  introduced.

The real cause is now **B-8**, filed as [djbclark/core#6](https://github.com/djbclark/core/issues/6)
and fixed on `fix/exec-timeout-promise-result` (`326bcdb8d`). Shortening the
ladder cannot close it: the exit status of a command that was killed is not a
reliable report of whether it was killed.

**What B-1 does fix stands.** The poll loops counted iterations rather than
measuring elapsed time; two reviewers independently reproduced the Darwin
`nanosleep` overshoot (4.229/4.348/4.385 s and 4.449 s per 100 × 10 ms, against
the original 4.41–4.66 s). A real timing defect, worth fixing on its own merits.

## §2 B-2 must not ship as written — and the reason is worse than flagged

All three refused the unconditional `setpgid(0, 0)`. The author's stated reason
for it — not wanting the timeout path to be structurally different from the
normal path — is **backwards**: the timeout path *is* different, because it is
the only one that has to kill a tree, and the normal path has to stay reachable
by the things that already kill trees.

Three independent consequences, in increasing order of severity:

1. **Ctrl-C orphans children** (gemini, cursor, grok). A terminal SIGINT reaches
   only the foreground group; cf-agent's handler exits immediately, so children
   that used to die with it now survive.
2. **`cf-execd`'s `agent_expireafter` stops working** (grok, the strongest
   argument of the three). It kills by process group; children detached from
   that group survive the watchdog that exists for precisely the hung command
   this patch is about — the same bug class, opened in the production watchdog.
3. **A new unbounded hang** — measured in this session, not found by any panel,
   and the decisive one. A child in its own process group is not in the
   terminal's foreground group, so it is stopped by **SIGTTIN** the first time
   it reads the terminal; type-`'r'` pipes do not redirect stdin. Under a pty,
   `sh -c 'read x; echo GOT-$x'` **with no `exec_timeout` at all**:

   | build | result |
   |---|---|
   | stock 3.27.1 | 0.1 s, prints `GOT-hello` |
   | B-2 as filed | **hangs indefinitely** |

   ```
     PID  PPID  PGID TPGID STAT COMMAND
    2669  2667  2669  2669 Ss+  cf-agent -KI -f ...
    2710  2669  2710  2669 T    /bin/sh -c read x; echo GOT-$x
   ```

   `PGID` = own pid (setpgid took effect), `TPGID` = the agent's group, `STAT T`
   = stopped. This is the same unbounded hang B-2 exists to remove,
   reintroduced on a path with no timeout to end it.

   cursor predicted SIGTTIN from the source and verified the stop in isolation;
   grok listed it as *"I did not measure it"*; gemini did not raise it. The
   pty measurement above is this session's own contribution and is what makes
   the case unarguable.

**Fix:** `847373cf6` — the process group is created only when a timeout is
armed. Both cursor and gemini proposed exactly this independently.

## §3 Where the panels disagreed, and who was right

**PID recycling.** gemini said the `pgid == pid` guard, plus the fact that
`GracefulTerminate()` never reaps, means the pid stays a zombie and cannot be
recycled — race closed. cursor and grok both said the guard closes a *different*
bug (`getpgid()` returns ESRCH once the leader is dead, so reading it first is
mandatory or the sweep never runs) and does **not** bind the pid against reuse
in the window between `GracefulTerminate()` returning and `kill(-pid, SIGKILL)`.

**cursor and grok are right**, and the original commit message was wrong to
claim the guard closes it. Neither would block the patch on the residual window
— it is a handful of syscalls — and neither would describe it as closed. The
issue is corrected rather than the commit message left standing.

**Test clock mock.** All three accepted it and agreed the test's intent is
preserved, not weakened. cursor and gemini both noted the same latent fragility:
`libutils`' `mutex.c` calls `clock_gettime(CLOCK_REALTIME)`, so a future timed
`pthread_cond_timedwait` in that binary would see 1970. `-Wl,--wrap=` was
suggested and not taken, to keep the production helper plain.

**B-1 ship verdict.** grok said *ship as is* (code correct; the filing is what
is wrong); cursor and gemini said *ship with changes*. Taking the stricter
reading — both changes they asked for are cheap and real.

## §4 Defects in our own patches, found and fixed

| # | Found by | Defect | Fixed in |
|---|---|---|---|
| 1 | this session (pty measurement) | `setpgid` → SIGTTIN → unbounded hang with no timeout | `847373cf6` |
| 2 | cursor, gemini, grok | `setpgid` breaks Ctrl-C and `agent_expireafter` | `847373cf6` |
| 3 | cursor | `ProcessPollTimeNs()` ignores `clock_gettime()`'s return, reads uninitialized `struct timespec` — UB, copied from `EvalContextEventStart()` | `943d5371f` (uses libntech's checked `xclock_gettime()`) |
| 4 | gemini, grok | `CLOCK_REALTIME` fallback: a backward NTP step extends the deadline unboundedly; iteration counting was naturally immune | `943d5371f` |
| 5 | cursor, grok | B-1's fail-open claim is false | issue #4 corrected; B-8 filed as the real cause |
| 6 | cursor, grok | `pgid == pid` does not close the PID-recycle race | issue #5 corrected |

Accepted and **not** fixed, recorded as open on #5: unchecked `setpgid()` /
`getpgid()` returns (silent no-op on failure); no parent-side
`setpgid(pid, pid)`; no acceptance test for either item.

Judged not to need action: `assert(timeout_ns < 1000000000)` (documents the
existing sub-1s API; `tv_nsec` can no longer overflow), and the `timeout_ns <= 0`
semantic change (flagged by cursor and gemini; the only caller passes
`STOP_WAIT_TIMEOUT`, so it is unreachable in production — noted on #4 rather
than papered over).

## §5 Branch layout after the panel

Each cut from `master` `17eb78e6d`, independently landable; `tendcf-integration`
(`58e0e916e`) merges all three and is what our builds come from.

| branch | commits | issue |
|---|---|---|
| `fix/exec-timeout-commands` | `26634ac1f`, `943d5371f` | [#4](https://github.com/djbclark/core/issues/4) |
| `fix/timeout-process-group` | `cb2561584`, `847373cf6` | [#5](https://github.com/djbclark/core/issues/5) |
| `fix/exec-timeout-promise-result` | `326bcdb8d` | [#6](https://github.com/djbclark/core/issues/6) |

Follow-ups are new commits, not rewrites — the register forbids rewriting fork
branch history, and the corrections are part of the record we are offering.

## §6 Verification after all three

Integration build, `commands:` matrix, `exec_timeout => "2"`:

| payload | wall clock | compliance | timeout reported |
|---|---|---|---|
| `sleep 2.4; exit 0` | 6.6 s | **0.0%** | yes |
| `sleep 5; exit 0` | 4.7 s | 0.0% | yes |
| `sleep 30; exit 0` | 4.7 s | 0.0% | yes |
| `trap '' INT TERM; sleep 30` | 5.2 s | 0.0% | yes |
| `sleep 0.5; exit 0` | 1.8 s | 100.0% | no |
| `sleep 0.5; exit 3` | 1.4 s | 0.0% | no |
| `sleep 0.5; exit 0`, no timeout | 2.2 s | 100.0% | no |

Zero orphaned processes. Before the series the first row was 100% compliant and
`sleep 30` took 30.3 s leaving an orphan.

- `tests/unit`: **all 68 behaved as expected, 4 expected failures**, identical
  to baseline, on each branch and on the merge.
- `process_terminate_unix_test`: 6/6.
- tendcf gates against the fork build: `schema-lint: OK` (8 schemas, 59
  negative, 6 byte-class, 27 projection); `xref_lint` 0 findings, 584 sections;
  `flag_coverage` 21/21.

## §7 What this changes about the email

The email must **not** tell `security@` that B-1 closes the fail-open. It sends
three items to `security@northern.tech`: B-8 as the fail-open, B-1 as the timing
defect that narrows its window (carrying the correction, since it was originally
filed as the fail-open itself), and B-2 as the unbounded wait plus leaked
process.

**B-8 has not been second-opinioned** — it was found *by* this panel, not
reviewed by it — so it is gated behind its own panel
([`UPSTREAM-B8-REVIEW-BRIEF.md`](UPSTREAM-B8-REVIEW-BRIEF.md)) before anything
is sent. Sending an unreviewed claim about a fail-open, immediately after a
panel refuted the last confident claim about this same fail-open, is precisely
what the rule exists to prevent.
