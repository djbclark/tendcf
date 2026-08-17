# Acceptance tests for the exec_timeout defects (B-8) — 2026-08-16

The tests promised to security@northern.tech alongside the three
`exec_timeout` reports, and asked for by all six panel reviewers. The set
is the one specified by the reviewer in the B-8 review.

## Where they live

Branch `fix/exec-timeout-promise-result`, commit `46be075d4`, in the
worktree `/Users/djbclark/src/core-acceptance` (added from
`/Users/djbclark/src/cfengine-core`; the main checkout stayed on
`tendcf-integration`, untouched, `libntech` still ` M`). Not pushed, no
PR — per instruction.

Directory: `tests/acceptance/08_commands/04_exec_timeout/`. Rationale:
`08_commands/` is the commands-promise suite and its layout is numbered
topic subdirectories (`01_modules`, `02_syntax`, `03_shells`); outcome
classification under `exec_timeout` is a new topic, so it gets the next
number rather than being mixed into an existing one. `CATEGORY_ID: 26`,
matching every other `08_commands` test (the single `27` there is the
persistent-classes test, a different category).

Conventions matched: `init/test/check` driver via
`default("$(this.promise_filename)")` with only `../../default.sub.cf`
in inputs (the dominant form — 1571 files; `default.sub.cf` already
pulls in `dcs.sub.cf` and `plucked.sub.cf`), `dcs_all_classes()` +
`dcs_passif_expected()` for outcome classes, `test_skip_unsupported =>
"windows"` (the tests drive `/bin/sh`; the reason stated in the files is
the shell, not exec_timeout support, because `SetTimeOut()` is armed on
Windows too), `### PROJECT_ID: core` footers, local `body contain`
with `exec_timeout` modeled on `10_files/13_file_dir/001.cf`.

## What each test asserts

1. `timeout_overrides_exit_zero.cf` — `/bin/sh -c "sleep 2.4; exit 0"`
   under `exec_timeout => "2"` yields `repair_timeout` and neither
   `promise_kept` nor `promise_repaired`. The command exits 0; the whole
   point is that a successful exit status no longer wins over a fired
   timeout. (Class-level equivalent of the 0%-compliance row in the
   email table: acceptance tests observe outcome classes, not the
   aggregate-compliance line, and TIMEOUT with kept/repaired absent is
   what 0% compliance decomposes to.)
2. `within_timeout_normal_outcomes.cf` — an armed timeout that does not
   fire leaves the outcome to the exit status: `sleep 1; exit 0` is
   repaired, `sleep 1; exit 3` is failed, neither is timeout. Normal-path
   regression guard. Parameters widened from the reviewer's sleep 0.5 /
   timeout 2 to sleep 1 / timeout 10 to remove CI-load flake risk; the
   semantics tested — armed, unfired timeout — are identical.
3. `timeout_overrides_kept_returncodes.cf` — same timed-out exit-0
   command with `kept_returncodes => { "0" }`: still `repair_timeout`,
   not resurrected to kept. Only deviation from `dcs_all_classes`: classes
   bodies cannot compose, so this test carries a local copy of that body
   with `kept_returncodes` added (precedent: the same move in
   `08_commands/staging/default_failed_returncodes.cf`).
4. `timeout_after_output_closed.cf` — `/bin/sh -c "exec 1>&- 2>&-;
   sleep 10; exit 0"`: output closes at t≈0, so the agent is already in
   `cf_pclose()` when the alarm fires — the shape that made an earlier
   fix draft sample the flag too early. Still `repair_timeout`. The fixed
   agent logs the "NOT terminated and ran to completion" branch here and
   the "was terminated" branch in tests 1/3/5, so both message paths of
   the fix are exercised.
5. `timeout_does_not_leak_to_next_promise.cf` — a timed-out promise
   followed by `/bin/sh -c "exit 0"` under its own (unfired)
   `exec_timeout => "10"`: first is `repair_timeout`, second is
   `promise_repaired` and not timeout. The second promise must carry its
   own timeout: sampling is gated on `a->contain.timeout != CF_NOINT`,
   so a leak could only ever surface on a promise that arms one.

## Stock vs fixed

Stock = `/opt/homebrew/bin/cf-agent` 3.27.1. Fixed =
`/Users/djbclark/src/cfengine-core/cf-agent/cf-agent` (tendcf-integration
build, run not rebuilt). Invocation mirrors `testall` exactly:
`bin/cf-agent -Klf <test> -D AUTO` under
`CFENGINE_TEST_OVERRIDE_WORKDIR`/`TEMP` pointing at a throwaway workdir
with `bin/{cf-agent,cf-promises}` symlinked in. Fixed run repeated
twice, stable.

| test | stock 3.27.1 | fixed | stock failure reason (verified via -D DEBUG) |
|---|---|---|---|
| timeout_overrides_exit_zero | FAIL (16s) | Pass (5s) | `promise_repaired` defined, `repair_timeout` missing — the fail-open itself |
| within_timeout_normal_outcomes | Pass (3s) | Pass (3s) | passes on stock **by design**: normal-path guard, valuable by failing if the fix overreaches |
| timeout_overrides_kept_returncodes | FAIL (14s) | Pass (5s) | `promise_kept` defined — kept_returncodes resurrected "kept" on a timed-out command |
| timeout_after_output_closed | FAIL (11s) | Pass (11s) | `promise_repaired` defined for the output-closed shape |
| timeout_does_not_leak_to_next_promise | FAIL (16s) | Pass (6s) | first promise `promise_repaired`, `repair_timeout` missing |

Every stock failure is the reported defect, not an incidental breakage.

## Runtime

Fixed build, whole set: ~29s wall (5+3+5+11+6). Stock: ~60s (its
termination ladder waits longer; irrelevant going forward). The slow one
is `timeout_after_output_closed.cf` (~11–12s, inherent: nothing is left
registered for the alarm to signal, so the child's full 10s sleep runs
out); flagged in the file header. The suite's slow-test convention
(`timed/` directories + `dcs_wait`) does not apply: it lets the runner
schedule other tests while a test *yields between agent passes*, whereas
these sleeps happen inside a single command execution with the agent
blocked.

## Not tested / caveats

- **B-8-only build**: verification used the integration build (B-1, B-2,
  B-8 all merged) — building the lone `fix/exec-timeout-promise-result`
  branch was out of scope. The classifications asserted are B-8's, but
  wall-clock and which process dies when are influenced by the
  process-group fix, so a B-8-only build should be spot-checked before
  the PR is opened.
- **`./testall` itself** was not run (needs a full build in the
  worktree); its invocation was mirrored instead, including `-D AUTO`
  and the override workdir.
- **Windows** path untested; tests skip there
  (`test_skip_unsupported => "windows"`).
- **Fractional sleep**: three tests use `sleep 2.4` (the reviewer's
  exact shape — exits during the termination ladder so the shell reaps
  and exits 0). Precedent exists (`05_processes/01_matching` uses
  `sleep 0.1`), but a platform whose sleep(1) rejects fractional
  arguments would exit the shell early and fail these tests even on a
  fixed agent. If upstream review objects, `sleep 3` works but degrades
  the stock failure from "repaired" to "failed by signal" — the sharper
  exit-0-wins shape is worth defending.
