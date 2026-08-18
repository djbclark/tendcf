---
schema_version: 1
handoff_id: e0a0
parent_handoff_ids: [a80c]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: e1c5b903cf556afb4879a0b52c505666456ac6b6
created_at: 2026-08-18T07:35:00-0400
writer: claude-code
---
# Handoff — CFE-4735 (B-19) shipped; sudo-secretspec was intermittently broken mid-session

## The Goal

Continued from `a80c` ("no urgent next action"). User said "continue" — I
rechecked upstream state (nothing moved), then let the operator pick the
next task via `AskUserQuestion`: they chose **B-19's mechanical fix**
(pre-fork race B-18 was the harder alternative; the third option was
stopping). This session executed that choice in full, then hit and
recovered from an unrelated `sudo-secretspec` outage along the way.

## Where We Are

CFE-4735 (B-19) is fixed, panel-reviewed, discriminated by a genuine unit
test, pushed, and its Jira ticket is updated. `tendcf` and
`~/src/core-alarmleak` are both clean and pushed. Nothing is blocked.

- `~/src/core-alarmleak`, branch `fix/exec-timeout-alarm-leak`, at
  `453cc264d` (cut from B-17's tip `8f4ebedbd`), pushed to
  `djbclark/core` with upstream tracking set. Working tree clean.
- `tendcf` at `e1c5b903cf556afb4879a0b52c505666456ac6b6`, pushed to
  `origin/master` (`frdminc/tendcf`).
- Jira: `CFE-4735` updated by comment (fix description, panel outcome,
  discrimination). `CFE-4727`, `CFE-4734` unchanged from `a80c`.

## What We Tried

- **New worktree from scratch** (`~/src/core-alarmleak`, off
  `origin/fix/exec-timeout-alarm-pid`) needed a full `git submodule
  update --init --recursive` (libntech was missing) and its own
  `./configure --prefix=... --with-openssl=... --with-pcre2=...
  --with-lmdb=... --with-libyaml=... --enable-maintainer-mode` +
  `make install` — a bare `./autogen.sh` defaults to `/var/cfengine` and
  the resulting binaries fail at runtime with a `dyld` "Library not
  loaded" error. Used a **different** install prefix
  (`~/opt/cfengine-dev-4735`) than B-17's own
  (`~/opt/cfengine-dev-4727`) so the two installs don't clobber each
  other. This whole recipe is now written into
  `docs/architecture/UPSTREAM-CFE4735-REVIEW-BRIEF.md`'s traps section
  for the next worktree that needs it.
- **8 mechanical `ClearAlarmedPid(pid)` insertions** in `pipes_unix.c`
  (one per `fdopen()`-failure early return across the four `cf_popen*()`
  parents) plus a forward declaration, and **1 `ClearTimeOut()`
  insertion** in `verify_exec.c`'s `RepairExec()` `pfp == NULL` branch —
  done via a small Python script inserting at known, pre-verified line
  numbers in descending order (so earlier line numbers didn't shift),
  rather than by-hand `Edit` calls, since the 8 sites are textually
  identical in pairs and not uniquely addressable by string match.
- **Wrote a 2-seat delta review brief and dispatched gemini +
  grok**, modeled on the CFE-4727 brief. Gemini's review was long and
  detailed but split roughly 50/50 real-vs-overstated: it correctly
  found a genuine, pre-existing fd leak (POSIX `fdopen()` failure
  doesn't close the fd it failed to wrap) and two more `RepairExec()`
  early returns that skip `ClearTimeOut()` (powershell-on-Unix, a
  `CfReadLine` failure) — real, but out of B-19's specific scope, per
  grok's much sharper follow-on analysis. Grok's own review (400 lines)
  was exceptional: it read all three CFE-4727 opinions first as
  instructed, then **independently measured** rather than reasoned about
  almost everything — `otool` disassembly proving the compiler merged
  the eight source sites into four shared object-code tails (so a
  wrong-variable bug in one of a pair literally isn't representable in
  the binary), a `DYLD_INSERT_LIBRARIES` interpose forcing real
  `fdopen()` failure to compare `ALARM_PID` before/after the fix, and
  — the important one — **disproved my commit message's claim that no
  discriminating test was possible** by demonstrating a portable POSIX
  technique (`RLIMIT_NOFILE` low enough that `pipe()` itself fails, no
  interposition needed) that exercises `RepairExec()`'s new branch.
- **Built the discriminating test grok proved possible**
  (`test_leftover_alarm_does_not_kill_next_child` in
  `tests/unit/timeout_test.c`) — and it took **two failed attempts**
  before it actually discriminated:
  1. First attempt used a fixed 3-second wait then `kill(pid, 0)` to
     check the decoy survived. Passed even with the fix's
     `ClearTimeOut()` call manually commented out — a **false pass**.
     Root cause: `kill(pid, 0)` succeeds against a zombie exactly as it
     does against a live process, and 3 seconds isn't remotely long
     enough to observe Darwin's actual termination-ladder completion
     (CFE-4727 measured up to ~20s, driven by CFE-4728/CFE-4718).
  2. Second attempt extended the wait to a 25-second poll (matching
     CFE-4727's own bound) with a 30-second decoy sleep. **Also passed
     with `ClearTimeOut()` removed** — added `fprintf(stderr, ...)`
     debug instrumentation and found `TimeOutHasFired()` and
     `TimeOutSignalledProcess()` were both `1` after the poll (the
     leftover alarm genuinely fired and `TimeOut()` genuinely tried to
     act on the decoy) — but the decoy was still "alive" by `kill(pid,
     0)`, confirming the zombie-vs-alive ambiguity from attempt 1 was
     the actual problem, not test timing.
  3. **Final version** asserts directly on `TimeOutHasFired()` /
     `TimeOutSignalledProcess()` after a short 3-second wait instead of
     trying to observe the kill's real-world completion — unambiguous,
     doesn't depend on the termination ladder's timing at all, and
     genuinely discriminates: verified by hand (commented out the
     test's own `ClearTimeOut()` call, rebuilt, reran) that it fails
     exactly at the `TimeOutHasFired()` assertion, then restored and
     reconfirmed 8/8 pass.
- **`sudo-secretspec` broke mid-session**, unrelated to any of the above.
  First symptom: `sudo: a password is required` on every command
  including `doctor`. Reported to the operator via `AskUserQuestion`
  rather than attempting any workaround (matches the skill's explicit
  "on any broker failure, stop and report only the non-secret error; no
  fallback store, repair, or permission change" instruction). Operator
  worked on it across **three** rounds:
  1. First "should be fixed" — `doctor` still failed identically.
  2. Second "should be fixed" — `doctor` passed (`OK`, exit 0) but
     listed ~40 `PENDING_ROLLBACK` advisories, and the actual `run`
     invocation failed differently: `broker: cannot load secrets: IO
     error: Permission denied (os error 13)`.
  3. Third "try again" — `doctor` passed clean (no more
     `PENDING_ROLLBACK` entries), but `run` failed with yet a **third**
     distinct error: `broker: Secret 'TEST_AGENT_KEY' is required but
     not set` (an unrelated secret blocking the whole `run`), plus a new
     warning about the audit log path
     (`/var/empty/.local/state/secretspec/audit.log: Operation not
     permitted`).
  4. Fourth "try again" — worked cleanly: `doctor: OK`, `run` returned a
     192-character token, comment posted successfully
     (`CFE-4735` comment id `159422`).
  Each round I tested, reported the exact new error verbatim, and asked
  again rather than guessing at a fix myself — this is infrastructure
  the operator owns, not something in scope for me to repair.

## Key Decisions

- **Did not fold gemini's two extra findings (fd leak, two more
  `RepairExec()` leaks) into this commit**, following grok's more
  precise scope argument over gemini's more alarmist one: neither
  combines a *leaked alarm* with a *reaped pid* the way B-19's three
  sites do — the fd leak is unrelated to `ALARM_PID` entirely, and the
  other two early returns either never fork (so `ALARM_PID` is already
  `-1`) or already run through `cf_pclose()` (which already clears
  `ALARM_PID` via B-17) — only their `TIMEOUT_ARMED`/`alarm()` leak
  remains, which is the pre-existing, already-registered B-15 family.
  Both are named explicitly in the commit message and the Jira comment
  so the fix isn't misread as leaving `RepairExec()` fully leak-clean.
- **Chose a 2-seat panel (gemini + grok) rather than a 3-model one**
  for this smaller, mechanical delta — matches this project's
  established precedent (B-2's own incremental MinGW/`sig_atomic_t`
  delta used the same 2-seat pattern) rather than the full 3-model
  panel CFE-4727 itself used for a first-of-its-kind fix.
  `fable-deep` was not spent this session.
  - Fable is at 87% remaining per this session's start quota check
    (fable-deep-always-authorized memory notwithstanding — a 2-seat
    panel was judged sufficient for a mechanical, well-scoped delta,
    not a quota-conservation decision).
- **Corrected the commit message's own overclaim mid-session**: the
  first draft said no discriminating test was possible for either new
  code path. Once grok proved that wrong, amended the commit (still
  unpushed at the time) to describe the actual test added and credit
  grok's technique by name, rather than shipping a claim already known
  to be false.
- **Discriminated the new unit test by hand twice** (once per failed
  attempt) rather than trusting either version on the strength of "it
  passed" — this project's established discipline (never trust a green
  test without proving it goes red when the fix is reverted) caught two
  real test-design bugs that would otherwise have shipped as false
  confidence.

## Evidence & Data

- Commit: `djbclark/core@453cc264d` (amended once, from the original
  `89379323d`), branch `fix/exec-timeout-alarm-leak`, pushed with `-u`.
  3 files, 87 insertions (2 files code, 1 file the new unit test).
- Unit tests: `tests/unit/timeout_test`, **8/8 pass, RC=0** (7
  pre-existing plus the new case). Discrimination: commenting out the
  new test's own `ClearTimeOut()` call → fails exactly at
  `timeout_test.c`'s `TimeOutHasFired()` assertion (1 of 8 failing);
  restored → 8/8 clean again.
- Acceptance: `08_commands/04_exec_timeout/`, **6/6 pass, 54-89s**
  across several runs (fresh clean rebuild included), no regression.
- Panel opinions, all in `tendcf`'s `docs/architecture/`:
  `upstream-opinion-cfe4735-gemini31pro-2026-08-18.md` (63 lines),
  `upstream-opinion-cfe4735-grok-2026-08-18.md` (377 lines — the
  strongest review in this chain so far by a clear margin: real
  `otool`/`DYLD_INSERT_LIBRARIES` measurements throughout, not
  reasoning-from-the-diff).
- Jira: `CFE-4735` comment id `159422` (fix description, panel outcome,
  discrimination). Register commit `tendcf@e1c5b90`, 4 files (register
  + brief + 2 opinion files — grok wrote its own review file directly
  to the repo again, same as in the CFE-4727 session; gemini's was
  captured from stdout and copied in by hand).
- `sudo-secretspec` incident: three distinct error signatures across
  four `doctor`/`run` attempts (`sudo: a password is required` →
  `Permission denied (os error 13)` on secret load, ~40
  `PENDING_ROLLBACK` advisories present → `Secret 'TEST_AGENT_KEY' is
  required but not set` + an audit-log permission warning → clean).
  Whatever the operator did to fix it is **not visible to this
  session** — worth asking them directly if the root cause matters for
  future sessions, rather than assuming from the symptom sequence.

## Operator Feedback

- Asked to pick the next task via `AskUserQuestion` after confirming
  nothing moved upstream; chose "B-19 mechanical fix" over "B-18 design
  work" or "stop here" — confirms picking B-19 first when both are
  queued and B-19 is the shovel-ready one.
- Across the `sudo-secretspec` outage, said "I think sudo-secretspec is
  fixed now, please test" three times before it actually was, and
  "please test again" / "try again" for the following two rounds. No
  frustration expressed; testing-and-reporting-exactly-what-broke was
  clearly the right response each time — never guessed at a fix or
  tried to route around the broker myself.
- Confirmed wanting a handoff at this stopping point when asked
  directly ("yes").

## Where We're Going

1. **No urgent next action**, same as `a80c`. B-17 and B-19 are both
   fully shipped this session; B-18 (`CFE-4734`, the pre-fork race) is
   still the only recorded-but-unpatched item from this trio, and it's
   the harder one (needs a real design decision on `SetTimeOut()`'s
   arming order, not a mechanical patch) — the operator explicitly
   passed on it this session in favor of B-19.
2. **B-18 fix, when picked up**: two shapes were named in
   `docs/architecture/upstream-register.md`'s row — publish `ALARM_PID`
   under a `SIGALRM` block around the fork, or reorder to arm
   `SetTimeOut()` only after the fork returns. Either touches
   `SetTimeOut()`'s contract with `TimeOutIsArmed()`-driven `setpgid()`,
   so it's not a one-line change like B-19 was.
3. **Recheck all 8 open upstream PRs periodically** (unchanged
   command, still zero maintainer engagement as of `a80c`'s check):
   `for n in 6293 6294 6299 6300 6302 6305; do gh pr view $n --repo
   cfengine/core --json number,reviewDecision,comments -q '.number,
   (.comments|length)'; done` and the libntech `#291`/`#294` equivalent
   — check comment *authors* if a count grows, not just the count.
4. **B-10 core half** still blocked on `libntech#294` + `djbclark/core#7`
   — unchanged, recheck both.
5. **`~/src/core-alarmleak` worktree**: consider whether to remove it
   once `fix/exec-timeout-alarm-leak` lands or is confirmed abandoned
   upstream — it duplicates a full build tree
   (`~/opt/cfengine-dev-4735` install prefix too). Not urgent.
6. **Ask the operator what actually fixed `sudo-secretspec`** if the
   root cause matters for future sessions — this session only observed
   symptoms across four rounds, never the fix itself.

## Quick Start

```sh
# Confirm the shipped state:
cd /Users/djbclark/src/core-alarmleak
git log --oneline -3          # expect 453cc264d at HEAD
git status --porcelain        # expect empty
git log @{u}..HEAD            # expect empty -- pushed and in sync

cd /Users/djbclark/src/tendcf
git log --oneline -3          # expect e1c5b90 at HEAD, pushed
$EDITOR docs/architecture/upstream-register.md   # B-17/B-18/B-19 rows

# Re-run the new discriminating test if you want to re-verify it:
cd /Users/djbclark/src/core-alarmleak && tests/unit/timeout_test
# 8/8 expected; test_leftover_alarm_does_not_kill_next_child is #7

# Jira spot-check:
TOKEN=$(sudo-secretspec run --reason 'spot-check CFE-4735' -- bash -c 'echo $ATLASSIAN_CFENGINE_API_TOKEN')
curl -sS -u djbclark@gmail.com:$TOKEN \
  "https://northerntech.atlassian.net/rest/api/2/issue/CFE-4735?fields=summary,status" | python3 -m json.tool

# PR engagement recheck (see Where We're Going item 3):
gh pr view 6293 --repo cfengine/core --json comments -q '.comments[].author.login'
```
