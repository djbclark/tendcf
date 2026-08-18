---
schema_version: 1
handoff_id: 214a
parent_handoff_ids: [f168]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: b6e467c232b30e2f41b73f87fca07d58b5016500
created_at: 2026-08-18T00:05:00-0400
writer: claude-code
---
# Handoff — CFE-4727 (exec_timeout termination half) fixed, committed, unpushed

## The Goal

Resumed via `/baton` from `f168`. Operator picked "start CFE-4727" (the
exec_timeout termination half) from a menu of next-steps. This ticket was
explicitly gated in every prior session's notes — "start after #6299/#6305
settle upstream" — because the fix touches the same `timeout.c`/`cf_pclose()`
code as those two open, zero-engagement PRs. Neither had moved (rechecked
this session: #6299 still 1 comment, #6305 still 0). Flagged the conflict via
AskUserQuestion; operator chose **override the gate, start now**, accepting
the rebase risk.

## Where We Are

CFE-4727 is fixed, tested, discriminated, and committed — but **not pushed,
not filed as a fork issue, not panel-reviewed, not emailed**. That's the next
session's work, per this project's standing "second opinion required before
upstream is contacted" rule.

Commit `254cbe593` on branch `fix/exec-timeout-alarm-pid`, worktree
`~/src/core-alarmpid` (new this session — created via `git worktree add` from
`~/src/cfengine-core`, based on `dbf759d16` = tip of `fix/timeout-process-group-merged`,
i.e. it carries all merged B-2/B-8 fixes). Working tree there is clean at
that commit.

## What We Tried

- **Investigated the defect from first principles**, reading `timeout.c`,
  `pipes_unix.c`'s `cf_pclose()`/`cf_pclose_full_duplex()`, and
  `verify_exec.c`'s sampling point, before delegating — confirmed the theory
  from `f168`'s notes was right: `cf_pclose()` clears `ALARM_PID = -1` as its
  first action, before the blocking `waitpid()` inside `cf_pwait()`. A
  command that closes stdout/stderr but keeps running ends the agent's read
  loop at EOF; if the alarm fires while blocked in that wait, `TimeOut()`
  finds `ALARM_PID == -1` and does nothing. B-8's fix (already merged) made
  the eventual error message honest about this ("was NOT terminated and ran
  to completion") but never closed the actual gap — `libpromises/timeout.c`
  had a comment explicitly documenting it as accepted, not a TODO.
- **Delegated implementation to `fable-deep`** (standing authorization for
  upstream/PR-bound code) with the fix design pre-derived: defer the
  `ALARM_PID` clear until after `cf_pwait()` returns, guarded by
  `sigprocmask(SIG_BLOCK, ...)` around the clear to close the pid-recycling
  race that deferring the clear would otherwise reopen.
- **The subagent stalled three times** — kicked off a full `autogen.sh &&
  configure && make` chain via background Bash, then ended its own turn
  reporting "waiting for the build" instead of actually blocking on it. Each
  resume cost 130–190K tokens for what should have been "wait, then report."
  Worth remembering for next time: for a long build, tell it up front to use
  a blocking wait (Monitor-style poll loop inside its own turn), not a
  fire-and-forget background command it then abandons.
- **On the third stall, took over verification directly** rather than
  bouncing the agent a fourth time — read the committed diff, then
  independently reran everything myself: unit tests standalone, a manual
  discriminating revert/rebuild/test/restore cycle (not trusting the
  subagent's claimed result), the specific acceptance test, and all 5 sibling
  acceptance tests in the same directory. All confirmed clean.
- **Sent a stop message** telling the subagent its remaining `make check` run
  (rebuilding the entire unrelated test matrix) was unnecessary. That
  in-flight run had already been launched, though, and turned up a real
  finding before the stop landed (see below) — good thing it wasn't killed
  outright.

## Key Decisions

- **Overrode the "wait for #6299/#6305" gate**, operator's explicit call
  after seeing the conflict surfaced. Accepted rebase risk rather than
  refusing outright or silently proceeding without flagging it.
- **Branched `fix/exec-timeout-alarm-pid` from `fix/timeout-process-group-merged`
  (`dbf759d16`)**, not from upstream `master` — this fix's reasoning
  (`TimeOutSignalledProcess()`, the honest error message) only exists on
  that branch.
- **`cf_pclose_full_duplex()` fixed too, for symmetry, not necessity** —
  verified via `grep -rln "SetTimeOut(" --include=*.c .`: only
  `verify_exec.c`, `nfs.c`, `cf-monitord/history.c` call `SetTimeOut()`, and
  all three run commands through the half-duplex `cf_popen*()`/`cf_pclose()`
  path. No `exec_timeout`-guarded path reaches the full-duplex closer
  (`mapdata()`'s json_pipe mode, package modules, custom promise modules).
  Confirmed this myself, not just accepted the subagent's claim.
- **Amended the commit rather than stacking a fixup**, after finding and
  fixing the test flake (below). Justification: the commit is local,
  unpushed, unreviewed — pure work-in-progress, no public record to
  preserve by keeping a separate "oops" commit. This is different from the
  project's established "correct via comment, never rewrite a public body"
  rule, which applies to artifacts others may have already seen.
- **Did not fix the deeper pre-fork race** the flake exposed (see Evidence)
  in this same commit — it's a distinct defect from CFE-4727's scope, and
  folding an unplanned second fix into an already-large commit was judged
  worse than documenting it clearly and leaving it for its own ticket.

## Evidence & Data

- Commit: `254cbe593a5dd22fccf937e2ba4e296feda60968`, "Fixed exec_timeout
  never terminating a command that closed its output", `Ticket: CFE-4727`.
  4 files changed, 150 insertions, 22 deletions:
  `libpromises/pipes_unix.c`, `libpromises/timeout.c`,
  `tests/acceptance/08_commands/04_exec_timeout/timeout_after_output_closed.cf`,
  `tests/unit/timeout_test.c`.
- **The fix**: new `ClearAlarmedPid(pid)` helper in `pipes_unix.c` — blocks
  `SIGALRM` (`sigprocmask(SIG_BLOCK, ...)`, restores via `SIG_SETMASK` with
  the saved mask), clears `ALARM_PID` only if it still equals `pid` (guards
  against a since-changed registration), then unblocks. Called from both
  `cf_pclose()` and `cf_pclose_full_duplex()` *after* `cf_pwait()` returns,
  replacing the old unconditional `ALARM_PID = -1;` that ran *before* the
  wait.
- **Residual race, documented not fixed**: a handful of instructions between
  `waitpid()` returning inside `cf_pwait()` and the `sigprocmask()` block
  taking effect in `ClearAlarmedPid()` — reachable only if the alarm expires
  in exactly that window AND the OS recycles the just-reaped pid in the same
  microseconds. Judged acceptable; the pre-fix code dropped the termination
  guarantee deterministically instead.
- **Unit test build/run**: `tests/unit/timeout_test` — 7/7 pass, ~35s
  (dominated by the new test's 30s sleep + termination ladder). Verified
  standalone by me directly (not just the subagent's claim), and again after
  the flake fix, and again under artificial 8-way `yes > /dev/null` CPU load
  ×4 runs, all clean.
- **Discrimination, done independently**: `git checkout HEAD~1 --
  libpromises/pipes_unix.c libpromises/timeout.c` (revert only the fix, keep
  the new test), rebuilt `libpromises` + `cf-agent` + `timeout_test`
  incrementally, reran — **fails exactly as claimed**:
  `ERROR: timeout_test.c:129 Failure! ... TimeOutSignalledProcess()`.
  Restored (`git checkout HEAD --`), rebuilt, reran — 7/7 pass, tree clean
  (`git status --porcelain` empty).
- **Acceptance test**, real build installed to `~/opt/cfengine-dev-4727`,
  run via `testall --gainroot=env --bindir=...`:
  `08_commands/04_exec_timeout/timeout_after_output_closed.cf` — **Pass**,
  18s wall (test's own bound is 25s; commit message's earlier measurement
  was 20s/32s-reverted). All 6 tests in that directory (the target plus 5
  siblings) — **6/6 pass**, 89s total, no regressions.
- **The flake, found by the subagent's own `make check` run under load,
  after I'd already told it to stop**: the new unit test originally armed
  `SetTimeOut(2)` *before* `cf_popen_sh()`, mirroring `verify_exec.c`'s real
  call order. Under `make check`'s full parallel build/test load, more than
  2s could elapse between arming and the fork actually publishing the
  child's pid into `ALARM_PID` — the alarm fired while `ALARM_PID` was still
  the `-1` `SetTimeOut()` itself sets, so the test hit the *same* assert
  the reverted fix hits (`TimeOutSignalledProcess()`), a false failure of a
  passing fix. Reproduced only under load; passed 7/7 standalone every time,
  by both the subagent and me, before that.
- **The flake fix** (folded into the amended commit): reordered the test to
  `cf_popen_sh()` first, `PipeToPid(&child, pfp)` to read the already-known
  pid, *then* `SetTimeOut(2); ALARM_PID = child;` — the same direct-registration
  pattern an existing test in that file (`test_clear_preserves_a_true_signalled_flag`)
  already uses. Payload changed to `exec 1>&- 2>&-; exec sleep 30` (chained
  `exec`, single process, no intermediate shell) since the child is now
  known by exact pid rather than discovered via `ALARM_PID` after
  `cf_popen()`'s own registration. Verified clean standalone and under
  4×(8-way CPU load) after the reorder.
- **A genuinely new, unfiled defect this session found but did not fix**:
  the race the flake exposed is real in production, not just a test
  artifact — `SetTimeOut()` arms *before* `cf_popen()`'s fork publishes the
  child's pid, so on a sufficiently loaded host a short `exec_timeout` can
  fire before there's anything registered to terminate. Previously only a
  theoretical note in one review document,
  `docs/architecture/upstream-opinion-b2merge-gpt56sol-2026-08-17.md:33`
  ("Blocking: the alarm can fire before `ALARM_PID` is published") — never
  filed as its own register row or ticket. This session's flake is the
  first *empirical* confirmation. Documented in the amended commit message
  and in `timeout.c`'s comment, but genuinely unfixed.
- **Three smaller audit notes from the subagent's self-review**, none
  acted on: (1) `cf_pclose()` is reachable from cf-serverd/cf-execd worker
  threads, where POSIX leaves plain `sigprocmask()` unspecified per-thread —
  `pthread_sigmask()` would be the defensive choice if a reviewer objects;
  (2) the full-duplex symmetry fix marginally widens an already-existing
  leaked-alarm blast radius (B-15/B-16 family) during the reap window —
  disappears once those leaks are fixed; (3) `ALARM_PID` remains a
  non-volatile `pid_t` by deliberate scope restraint, relying on
  `sigprocmask()` calls as compiler barriers rather than `volatile`.

## Operator Feedback

- Asked "options? please number" after the resume summary — numbered-menu
  format preferred for next-step choices, not prose.
- Explicitly chose to override a standing sequencing gate after it was
  surfaced, rather than have it silently respected or silently ignored —
  confirms the right move when a new instruction conflicts with prior
  session notes is to flag the conflict and let the operator decide, not
  pick either side unilaterally.
- No pushback on taking over verification directly after the third
  subagent stall, or on amending vs. stacking a fixup commit.

## Where We're Going

1. **THE next action**: push `fix/exec-timeout-alarm-pid` to
   `djbclark/core`, file a fork issue documenting CFE-4727's fix (matching
   the pattern of every other B-item: defect description, before/after
   measurements, the residual-race caveat, the flake finding), and run this
   project's standard multi-model adversarial review panel before anything
   goes to `security@` or upstream. Do **not** skip the panel — this is a
   signal-handling change to security-relevant termination code, same
   class as B-2/B-8 which both got real defects caught by review.
2. **File the pre-fork race as its own register row / ticket** before or
   alongside the panel — it's real, empirically confirmed this session, and
   currently exists only as a paragraph in a commit message and a stale
   review doc, not tracked anywhere durable. Suggest querying whether it
   should be B-17 or similar, alongside B-15 (CFE-4732)/B-16 (CFE-4733) as
   the same "ALARM_PID hygiene" family.
3. Recheck all 8 previously-open PRs for maintainer activity (unchanged
   command from prior handoffs): `for n in 6293 6294 6299 6300 6302 6305; do
   gh pr view $n --repo cfengine/core --json number,reviewDecision,comments
   -q '.number, (.comments|length)'; done` and `for n in 291 294; do gh pr
   view $n --repo NorthernTechHQ/libntech --json
   number,reviewDecision,comments -q '.number, (.comments|length)'; done`.
4. B-10 core half (`core-json`, fork ticket `djbclark/core#13`) still
   blocked on `libntech#294` merging AND `djbclark/core#7`'s submodule bump
   — unchanged, recheck both.
5. OpenAI reviewer seat still unresolved (unchanged from `f168`):
   `cursor-agent` lists `gpt-5.3-codex-high` but self-identifies as Grok
   per prior memory (unverified); `codex` quota-walled until 2026-08-20;
   `opencode` fails "Insufficient balance." Needed for a genuine
   4-model panel on CFE-4727.

## Quick Start

```sh
cd /Users/djbclark/src/core-alarmpid
git log --oneline -3          # confirm HEAD is 254cbe593
git status --porcelain        # should be empty
git show HEAD --stat          # review the fix before pushing

# Recheck the flake fix survives fresh eyes / a fresh machine state:
make -C tests/unit timeout_test && tests/unit/timeout_test

# Then: push, file the fork issue, run the review panel.
git push -u origin fix/exec-timeout-alarm-pid
```
