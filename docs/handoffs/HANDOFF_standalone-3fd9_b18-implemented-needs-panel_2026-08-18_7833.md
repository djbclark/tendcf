---
schema_version: 1
handoff_id: 7833
parent_handoff_ids: [2c25]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: ebe2145669814fe2ad234b7faeffff78e7a9663f
created_at: 2026-08-18T11:38:09-0400
writer: claude-code
---
# Handoff — B-18 (CFE-4734) designed, implemented, verified; awaiting review panel

## The Goal

Resumed from `2c25` via `/baton`. That handoff's next actions were (1) a
maintainer-reply recheck on the two live PRs and (2) B-18 / `CFE-4734`, the
pre-fork `ALARM_PID` publish race, described there as "the next substantive
item" and the thing Fable was being conserved for. The operator said "go
ahead". Both were done. **B-18 is now designed, implemented, tested and
committed — but deliberately NOT pushed**, because the house pattern is
panel-review-then-push.

## Where We Are

`tendcf` is untouched this session: `master` at `ebe2145`, clean, in sync with
`origin/master`. All B-18 work lives in a **new worktree**.

- **`~/src/core-prefork`**, branch `fix/exec-timeout-prefork-race`, at
  **`92531d60cc87885053aadd7889e384f0435e7e77`**, clean tree, **local only —
  no remote branch, nothing pushed.**
  Based on `dbf759d16`, a *sibling* of B-17/B-19, not stacked on them.
- A dev install exists at `~/opt/cfengine-dev-4734` (needed by the
  acceptance runner; see the dyld gotcha below).

Unchanged from `2c25`: `~/src/core-b2merge` `0e06ad3d7`, `~/src/libntech-p3`
`8023f452a`, `~/src/core-alarmpid` `8f4ebedbd`, `~/src/core-alarmleak`
`453cc264d`, `~/src/core-acceptance` `179e95754`, `~/src/core-json`
`32c38f8ab`, `~/src/libntech-fixes` `eda43f00d`.

**Maintainer status: no new engagement since `2c25`.** larsewi's review on
`libntech#291` (10:51Z) and nickanderson's on `cfengine/core#6305` (12:28Z)
are still the last maintainer words; my replies (15:00Z and 14:40Z) have no
response. All six other open PRs (`core#6293/6294/6299/6300/6302`,
`libntech#294`) unchanged. `CFE-4734` is Open with **zero** comments.

The two "dirty" worktrees flagged at resume are both benign and were left
alone: `core-alarmpid` has an untracked `review.md` (a B-17 panel opinion),
`core-json` shows a deleted `libntech` submodule dir from last session's
nested-worktree cleanup.

## What We Tried

**The `/handoff` that was refused at session start.** The operator's first
command was `/handoff`, before any work. HEAD was `ebe2145`, which *is* the
commit of handoff `2c25` — nothing had happened since. Writing one would have
appended a permanently content-free node to an append-only chain and
duplicated `2c25`'s "Where We're Going" verbatim. Refused with three options;
the operator then sent `/baton`. **Do the same next time** — a handoff with
nothing to mine is worse than no handoff.

**Acceptance run reported 0/6 with exit code 0.** First `testall` invocation
on the new worktree failed every test in 3 seconds. Cause was mine, not the
tree: `.libs/cf-agent` carries an install-prefix RPATH
(`~/opt/cfengine-dev-4734/lib/libpromises.3.dylib`) and I had not run
`make install`. Fixed by installing; the rerun gave 6/6 in 62s. **Gotcha
worth more than the fix: `testall` exited 0 while all six failed.** The known
note says `testall` is "vacuous on this machine — 0 passed / 2558 skipped,
exit 0"; this is a *second, different* instance of the same trap (aborting on
dyld, still exit 0). Never trust `testall`'s exit code — read the passed
count, every time.

**A wrong claim I put in the design brief.** I told the operator and wrote in
the frozen brief that `SetTimeOut()` had exactly one production caller
(`verify_exec.c:308`), and framed that as making the reorder tractable. It is
wrong — there are **six**: `verify_exec.c:308`, `nfs.c:403`, `nfs.c:1121`,
`nfs.c:1434`, `nfs.c:1459`, `cf-monitord/history.c:242`. My grep had a
`grep -v "^./tests/"` filter that never matched (paths print as `tests/...`,
no `./`) *and* a `head -20` that cut the real callers off. fable-deep caught
it against the tree. It changed the design materially: the clock-start had to
be centralized in `GenericCreatePipeAndFork()` rather than placed at a call
site. **Lesson: never `head` a grep whose purpose is completeness.**

**`raise(SIGALRM)` was considered and rejected as the discriminating test.**
It invokes the handler directly, bypassing the kernel timer — which is
precisely what the fix changes — so it cannot discriminate.

## Key Decisions

**Chosen: shape (b), "arm the alarm last", with the clock start centralized
in `GenericCreatePipeAndFork()`'s parent path, immediately after
`ALARM_PID = pid`. No signal masking anywhere.**

Why it wins: no alarm is pending until a pid is registered, so the race is
structurally impossible rather than narrowed; `TIMEOUT_ARMED` is still set
pre-fork, so the child's `setpgid()` decision — the crux — is untouched; zero
signal-mask surface; one edit covers all six arm sites; and the timeout now
bounds the command instead of the agent's own setup.

**Rejected — (a) block `SIGALRM` around the fork.** Closes only the window
from the block to the publish. The *wide* part — `umask()`, two `Log()`
calls, shell dispatch, arg marshaling at `verify_exec.c:311–366` and the
nfs.c/history.c equivalents — stays open. A narrowing, not a fix; a reviewer
who understands the race would ask why half of it survives.

**Rejected — (a′) block inside `SetTimeOut()`, unblock after publish.**
Closes the window but creates cross-module *mask* ownership with a worse
failure mode: if `fork()` fails, `SIGALRM` stays blocked in that thread
forever and all future timeouts are silently dead. Also needs
`pthread_sigmask()` discipline on every error path, and still lets the
deadline expire during setup so the child is killed at t=0 of its life.

**Rejected — snooze variant** (handler re-arms when `ALARM_PID == -1`):
cannot distinguish "pre-fork" from "stale fire after close", and re-rings
into unrelated promises.

**Scope calls.** `ShellCommandReturnsZero()` (`unix.c:225`), the second
`ALARM_PID` publish site, is explicitly out of scope — it arms nothing, so it
has no arming-order race. B-17 and B-19 were not folded in.

**Accepted cost, stated in the commit message rather than hidden:** a timeout
armed but never followed by a fork now never fires. Net strictly safer —
today such a leaked alarm can fire while a *later, unrelated* child is
registered and kill it; under the fix it degrades to an inert flag.

**Branch base.** Sibling off `dbf759d16` rather than stacked on B-17, matching
what B-19 did. Verified safe: B-17's only `timeout.c` change is a comment, and
the whole `TIMEOUT_ARMED`/`TimeOutIsArmed()`/setpgid machinery already exists
at `dbf759d16`.

**Not pushed.** B-17's panel produced a *required* code change
(`sigprocmask` → `pthread_sigmask`) that was amended in before its push.
Pushing pre-panel would just set up a force-push.

## Evidence & Data

**The commit — `92531d60c`, 4 files, +133/−4:**

- `libpromises/timeout.c` — new `static int TIMEOUT_PENDING`; `SetTimeOut()`
  sets the flags and installs the handler but calls `alarm(0)` and stashes the
  timeout instead of arming; new `StartTimeOutClock()` (one-shot: consumes
  `TIMEOUT_PENDING`, so a second fork under one timeout runs on remaining
  time); `ClearTimeOut()` also zeroes `TIMEOUT_PENDING`. Under `__MINGW32__`
  `SetTimeOut()` still calls `alarm(timeout)` directly — the Windows pipe
  implementation is outside this tree and could never call the starter, so
  deferring there would silently kill `exec_timeout` on Windows.
- `libpromises/timeout.h` — declares `StartTimeOutClock()`; restates
  `TimeOutIsArmed()` as "armed, whether or not the clock has started".
- `libpromises/pipes_unix.c` — `StartTimeOutClock()` right after
  `ALARM_PID = (pid != 0 ? pid : -1);`, guarded on `pid > 0`.
- `tests/unit/timeout_test.c` — 6 tests → 10.

**Test results, real numbers:**

| | baseline (unfixed `dbf759d16`) | fixed (`92531d60c`) |
|---|---|---|
| `tests/unit/timeout_test` | 6/6 | **10/10** (~25s) |
| `08_commands/04_exec_timeout` | 6/6, 62s | **6/6, 66s** |

**Discrimination was proved, not asserted.** `libpromises/timeout.c` was
temporarily edited to emulate pre-fix behaviour (`alarm(timeout);
TIMEOUT_PENDING = 0;` in the non-MinGW branch, leaving `StartTimeOutClock()`
a no-op), rebuilt, and rerun: **exactly 2 of 10 failed** —
`test_clock_does_not_run_before_the_fork` (assert at `timeout_test.c:137`,
`TimeOutHasFired()`) and `test_set_leaves_the_clock_stopped` (at `:160`,
`e10 != 0` — 0xe10 = 3600, the clock already running). The probe was then
reverted from the saved copy, verified absent (`grep -c DISCRIMINATION` = 0),
rebuilt, 10/10 again. The other 8 pass both ways: contract pins, not
discriminators.

The behavioural test deliberately waits **twice** the timeout (2s against a
1s timeout) before forking at all, so the old behaviour fires with certainty
rather than timing luck, and then runs `/bin/sleep 5` — 4s beyond its
timeout. Margins are gross, not races. It is **not** a fixed-wait liveness
check, which is the trap B-19 hit.

**New files (scratchpad, not in any repo):**
- `.../scratchpad/b18-brief.md` — the frozen design brief (contains the
  six-caller error; the design doc corrects it)
- `.../scratchpad/b18-design-fable.md` — fable-deep's full decision
- `.../scratchpad/b18-msg.txt` — the commit message
- `.../scratchpad/timeout.c.fixed` — the saved copy used to restore the probe

**Defect named by fable-deep but NOT patched or filed:** leaked armed
timeouts on error/early-return paths — `verify_exec.c:374`, `verify_exec.c:391–393`,
`nfs.c:405–409`, and `nfs.c:1434`/`nfs.c:1459` which have **no matching
`ClearTimeOut()` at all**. Suspected to be the already-registered B-15/B-16
family. **Confirm against `docs/architecture/upstream-register.md` before
filing anything** — a duplicate ticket is worse than none.

## Operator Feedback

- **`/ultrareview` has hard limits**, learned this session: the diff must be
  under **500 files and 12,000 lines changed**. A real refusal: "217 files,
  47,739 lines changed" — so the *line* cap bound at well under half the file
  cap. Lines bind first. Remedies it suggests: pass a closer base branch
  (`/code-review ultra <branch>`) or split. This qualifies the standing
  "scope it wide" advice — wide means *as wide as fits*. Auto-memory
  `ultrareview-scope-it-wide` and its `MEMORY.md` line were both updated.
- Fable budget is a live constraint the operator wanted visibility on: 91%
  used at session start, resetting 2026-08-21. It was spent on the *design
  adjudication only*, deliberately, with implementation and testing done on
  Opus to preserve the rest.

## Where We're Going

1. **NEXT ACTION — run the review panel on `92531d60c`** against a frozen
   brief, as B-17 and B-19 did. Seats: per auto-memory
   `panel-reviewer-weighting`, grade by the trap-control section, not the
   verdict; grok was by far the most rigorous on B-17 and gemini
   rubber-stamped (and fabricated a `pid == 0` early-return that did not
   exist). **Budget decision the operator has not yet made:** grok + gemini
   leaves Fable untouched; adding fable-deep is the stronger review but eats
   into the ~9% remaining. Ask before spending.
2. **Apply whatever the panel requires, amend `92531d60c`, then push** to the
   `djbclark/core` fork as `fix/exec-timeout-prefork-race`.
3. **Comment on `CFE-4734`** with the fix, branch, measurements and panel
   outcome — by comment, per the Jira-only convention; do not open a fork
   GitHub issue. Ticket is Open with 0 comments.
4. **Update `docs/architecture/upstream-register.md`** B-18 row (line 103),
   which currently reads *not started* — and commit/push that in `tendcf`.
5. **Confirm-or-drop the leaked-armed-timeout finding** in Evidence above
   against the register's B-15/B-16 entries before filing.
6. **Periodic PR-engagement recheck** — commands in Quick Start.

## Quick Start

```bash
# Where the work is (local only, nothing pushed):
cd /Users/djbclark/src/core-prefork
git log --oneline -1          # expect 92531d60c
git status -s                 # expect clean

# Re-verify the fix (unit, ~25s; expect "All 10 tests passed"):
cd /Users/djbclark/src/core-prefork/tests/unit && make timeout_test && ./timeout_test

# Re-verify acceptance (~66s; expect "Passed tests: 6").
# REQUIRED FIRST or every test dies on dyld with exit code 0:
cd /Users/djbclark/src/core-prefork && make && make install
cd tests/acceptance
rm -rf /tmp/cfe4734-fixed && mkdir -p /tmp/cfe4734-fixed/workdir /tmp/cfe4734-fixed/tmp
CFENGINE_TEST_OVERRIDE_WORKDIR=/tmp/cfe4734-fixed/workdir TEMP=/tmp/cfe4734-fixed/tmp \
  ./testall --gainroot=env \
  --agent=/Users/djbclark/src/core-prefork/cf-agent/.libs/cf-agent \
  --cfpromises=/Users/djbclark/src/core-prefork/cf-promises/.libs/cf-promises \
  --cfserverd=/Users/djbclark/src/core-prefork/cf-serverd/.libs/cf-serverd \
  08_commands/04_exec_timeout
# ALWAYS read the passed count. testall exits 0 even when all six fail.

# The design decision and frozen brief:
cat /private/tmp/claude-501/-Users-djbclark-src-tendcf/a36a015b-b107-42fa-8d5f-74b172e2c367/scratchpad/b18-design-fable.md

# Jira spot-check (CFE-4734 was Open, 0 comments):
TOKEN=$(sudo-secretspec run --reason 'spot-check CFE-4734' -- bash -c 'echo $ATLASSIAN_CFENGINE_API_TOKEN')
curl -sS -u djbclark@gmail.com:$TOKEN \
  "https://northerntech.atlassian.net/rest/api/2/issue/CFE-4734?fields=summary,status" | python3 -m json.tool

# PR engagement recheck:
gh api repos/NorthernTechHQ/libntech/pulls/291/comments -q '.[]|"\(.user.login): \(.body[0:120])"'
gh api repos/cfengine/core/pulls/6305/comments  -q '.[]|"\(.user.login): \(.body[0:120])"'
```
