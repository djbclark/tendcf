---
schema_version: 1
handoff_id: 8b7f
parent_handoff_ids: [7833]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 3c947ca702a6adb896e46c055b976077acca479d
created_at: 2026-08-18T12:31:44-0400
writer: claude-code
---
# Handoff — B-18 shipped; B-15 started and its filed severity found wrong

## The Goal

Resumed from `7833` via `/baton`. That handoff's next action was the B-18
review panel and its follow-through. The operator picked the panel seats
(**grok + gemini, no Fable**) and later said "keep going", which moved the
session on to B-15.

**B-18 / CFE-4734 is fully shipped.** All five of `7833`'s next actions are
done. B-15 / CFE-4732 is **mid-flight** and has produced a finding that
matters more than its two-line patch: the filed ticket's severity is wrong.

## Where We Are

`tendcf` `master` at **`3c947ca`**, pushed. One untracked file:
`docs/architecture/UPSTREAM-CFE4732-REVIEW-BRIEF.md` (the B-15 brief, written
but its panel not yet launched).

**B-18 — done.** `~/src/core-prefork`, branch `fix/exec-timeout-prefork-race`,
at **`ab98a5df4`** (amended from `92531d60c`), clean, **pushed** to
`djbclark/core`. CFE-4734 updated by comment **159432**. Register B-18 row
rewritten from *not started* to done.

**B-15 — in progress.** New worktree **`~/src/core-mountleak`**, branch
`fix/mount-options-timeout-leak`, based on **`upstream/master a0bca6aaf`**
(not on our series — see Key Decisions). `cf-agent/nfs.c` modified, +9 lines,
**not committed**. Untracked `confdefs.h` / `conftest.c` / `conftest.err` are
live `configure` scratch, not work.

**A build was still running at handoff time**: background task `b9iqld2el`,
`./autogen.sh --prefix=$HOME/opt/cfengine-dev-4732 && make -j4` in
`~/src/core-mountleak`, logs at
`.../scratchpad/b15-autogen.log` and `b15-make.log`. Its result is unknown —
**check it first.**

Unchanged from `7833`: `~/src/core-b2merge` `0e06ad3d7`, `~/src/libntech-p3`
`8023f452a`, `~/src/core-alarmpid` `8f4ebedbd`, `~/src/core-alarmleak`
`453cc264d`, `~/src/core-acceptance` `179e95754`, `~/src/core-json`
`32c38f8ab`, `~/src/libntech-fixes` `eda43f00d`.

**Maintainer status: still nothing.** larsewi on `libntech#291` (last word
10:23Z) and nickanderson on `cfengine/core#6305` (12:28Z) remain unanswered
since my replies (15:00:05Z and 14:40Z). The other six PRs
(`core#6293/6294/6299/6300/6302`, `libntech#294`) have only `djbclark`,
`CLAassistant` and `mender-test-bot` comments. Verified `#291`'s head SHA is
`8023f452a` = local HEAD, so my "all addressed in 8023f45" reply is accurate.
`mender-test-bot`'s "error running your pipeline" has now fired **4×**
(08-16, 08-17, 08-18 ×2) including on pushes predating my changes — it is
their infra failing on fork PRs, logs behind a private GCP console. Not a
code signal; stop re-investigating it.

## What We Tried

**Three of my own claims were wrong this session. All three were caught by
checking rather than by argument.**

**1. I told the operator U1 was likely a required change. It was dead code.**
Reading the B-18 diff I found that `cf-monitord/history.c:242` arms a timeout
and its `stream_type => "file"` branch never forks, so `StartTimeOutClock()`
is never called and the timeout would never fire — where previously the alarm
`EINTR`-interrupted the read. I flagged it as a probable ship-blocker. grok
refuted it mid-run ("measurements never populate `contain.timeout`") and I
then verified independently: `VerifyMeasurementPromise()`
(`verify_measurements.c:46`) → `GetMeasurementAttributes()`
(`attributes.c:355`) starts from `ZeroAttributes` and fills only `.measure`,
`.transaction`, `.classes`; `.contain` is left zero by the designated-
initializer macro (`cf3.defs.h:1651`); that struct reaches `NovaReSample()`
(`history.c:184`) unchanged, so `a.contain.timeout` is **always 0** and the
guard at `:240` never passes. **Lesson: check reachability before calling
something a regression.** gemini made the identical mistake and made it its
*only* required change.

**2. I accused gemini of fabricating its trap-control section. It had not.**
Its artifact landed 258s after launch while claiming `make && make install`
plus both suites, which I called implausible. Wrong: the tree was already
built at 11:34, so `make` was a no-op. Its runs left real evidence —
`tests/unit/timeout_test.xml` (`tests="10" failures="0"`) at 11:50:08 and
`tests/acceptance/summary.log` (`Passed tests: 6`, 65s) at 11:51:25, both
after the 11:47:33 launch. **Lesson: "too fast to be real" needs the build
state checked before it is said out loud.**

**3. The stale-library trap nearly faked a negative discrimination result.**
Proving the rewritten `test_start_runs_the_clock_once` discriminates, I
installed a re-arming probe in `libpromises/timeout.c`, ran `make
timeout_test` in `tests/unit`, and got **all 10 passing** — which reads
exactly like "this test proves nothing". The cause: `make` reported
`'timeout_test' is up to date` and ran the **old** `libpromises`. After
`cd libpromises && make`, exactly 1 of 10 failed, the intended one. Saved as
auto-memory `libpromises-edit-needs-library-rebuild`.

**4. First B-15 build failed immediately**: `./libntech/libutils/sequence.h is
missing`. A fresh `git worktree add` does **not** populate submodules; needed
`git submodule update --init` (pulled `libntech` `0c0620d6c` and
`contrib/emacs-code-style`).

**5. Did not reuse `b18-brief.md`.** It is a *pre-implementation design* brief
and still contains the corrected one-caller error. Wrote a fresh review brief
against the actual commit instead.

## Key Decisions

**Panel seats: grok + gemini, no Fable** — operator's explicit choice, offered
because Fable sat at 93% with a 2026-08-21 reset. Fable was **not** touched
this session.

**Applied both of grok's required changes; took two of its optionals; rejected
one; rejected gemini's only required change.**

- *Required, applied:* `#ifdef __MINGW32__` → `#if defined(__MINGW32__) ||
  defined(__CYGWIN__)`. grok found a real platform bug nobody else saw:
  `AM_CONDITIONAL([NT])` is `mingw|cygwin` (`m4/cf3_platforms.m4:35`) and
  `pipes_unix.c` builds only under `!NT` (`libpromises/Makefile.am:179`), so a
  Cygwin build took the deferred POSIX branch with no starter and
  `exec_timeout` would have silently stopped working. `timeout_test` is also
  `!NT` (`tests/unit/Makefile.am:175`), so no CI job could have caught it.
  Verified all three facts myself before applying.
- *Required, applied:* the commit message's claim that a leaked armed timeout
  "now goes inert" is **false**, and B-18 makes the leak *worse*:
  `TIMEOUT_PENDING` stays set with no timer, so the next unrelated
  `GenericCreatePipeAndFork()` starts a **full** budget against whatever it
  forks, where the old leaked alarm could only spend its remainder. Message
  rewritten to say so.
- *Optional, applied (U4):* rewrote `test_start_runs_the_clock_once`. The old
  version's first `alarm(0)` cancelled the timer, so the second
  `StartTimeOutClock()` was never issued against a running clock — it never
  exercised the production sequence at `nfs.c:1459`.
- *Optional, applied (U7):* `Changelog: Commit` → a user-facing one-liner.
  `CONTRIBUTING.md:220` says implementation detail does not belong in the
  changelog, and `Changelog: Commit` dumps the whole body.
- *Optional, REJECTED (U6):* leaving `TIMEOUT_PENDING` a plain `int` rather
  than `volatile sig_atomic_t`. Reviewers split; **adjudicated for gemini
  against grok** — the variable has no handler interaction at all, so the
  annotation would imply concurrent signal state that does not exist. Weighting
  the stronger reviewer higher does not mean deferring to it on every point.
- *gemini's sole required change, REJECTED:* the `history.c` "real and severe
  regression" — unreachable, see What We Tried #1.

**B-15 is based on `upstream/master`, deliberately not on our series.**
`ClearTimeOut()` and `TimeOutIsArmed()` **do not exist upstream** — they are
introduced by our own in-flight branches. Using them would make the patch
un-landable on its own, so the fix uses the file's existing idiom,
`alarm(0); signal(SIGALRM, SIG_DFL);` (as at `nfs.c:581` and `:1178`).

**B-15 disarm placed *inside* the method loop, before `LiveMountConverged()`
— not "after the reconcile loop" as CFE-4732 suggests**, so the timeout bounds
the reconcile command rather than the convergence check. The `else`/`continue`
branch at `:1466–1469` is deliberately skipped: it never arms.

**Not posting the CFE-4732 correction until the panel validates it.** Getting
a public correction wrong on a filed tracker is worse than shipping a bad
two-line patch, so the brief asks for SAFE TO POST / NOT SAFE TO POST as a
verdict separate from ship/don't-ship.

## Evidence & Data

**B-18 final commit `ab98a5df4`** — 4 files, +145/−4 (`libpromises/timeout.c`,
`timeout.h`, `pipes_unix.c`, `tests/unit/timeout_test.c`).

| | before | after |
|---|---|---|
| `tests/unit/timeout_test` | 6/6 | **10/10** |
| acceptance `08_commands/04_exec_timeout` | 6/6, 62s | **6/6, 74s** |

Discrimination re-proved after the amend: with a **re-arming** probe
(`TIMEOUT_PENDING` not consumed) exactly **1 of 10** failed —
`test_start_runs_the_clock_once`, the intended target, nothing else. Probe
removed from the saved copy `scratchpad/timeout.c.good`, verified absent
(`grep -c DISCRIMINATION` = 0), rebuilt, 10/10 again.

**Panel artifacts** (`docs/architecture/`):
`upstream-opinion-cfe4734-grok-2026-08-18.md` — **20921 bytes, 697s**;
`upstream-opinion-cfe4734-gemini31pro-2026-08-18.md` — **5544 bytes, 258s**.
Both `SHIP-WITH-CHANGES`, rc 0. grok explicitly **declined to invent** the one
measurement it had not run (the pre-fix emulation) and said so in its trap
section — a stronger quality signal than gemini's complete-looking one.

**B-15 finding — the masking chain, verified against `a0bca6aaf`:**

1. Both arming branches (`remount` `:1417–1454`, `unmount_mount`
   `:1455–1464`) fall through to `LiveMountConverged()` at `:1472`; only the
   unknown-method `else` branch `continue`s past it, and it never arms.
2. `LiveMountConverged()` (`:1308`) calls `LoadMountInfo()` unconditionally —
   its only early return is `a == NULL`, already asserted at `:1371`.
3. `LoadMountInfo()` (`:386`) calls `SetTimeOut(RPCTIMEOUT)` at `:403`,
   **replacing** the leaked alarm, then `alarm(0); signal(SIGALRM, SIG_DFL);`
   at `:581`, **clearing** it.

So the alarm never escapes the function on a normal path. **CFE-4732's
"the window covers arbitrary subsequent agent work" and "these two leak every
ordinary run" are both wrong.** Residual defect: a window from the reconcile
command finishing until `LoadMountInfo()` re-arms, plus real fragility —
correctness depends on a callee's incidental side effect and would break
silently if `LiveMountConverged()` ever read `/proc/mounts` directly.

**Third early-return leak the ticket omits:** `LoadMountInfo()` `:487`, the
`strstr(vbuff, "RPC")` abort path — `cf_pclose(pp); free(vbuff); return
false;` with the alarm armed. CFE-4732 catalogues only `:408` and `:427`. It
is the *RPC timeout* path — the exact condition the alarm exists to catch —
that leaks it.

**B-15 line numbers re-derived against `a0bca6aaf` and unchanged** from the
`22ce89322` the ticket cites: `SetTimeOut` at `403`, `1122`, `1436`, `1461`;
`alarm(0)` at `581`, `1178`.

**Register cross-check (task closed, no ticket filed):** fable-deep's unfiled
leaked-armed-timeout finding is entirely covered by B-15/CFE-4732 —
`verify_exec.c:374`/`:393` (row lists `:330/:374/:393`), `nfs.c:405–409` (row
lists `nfs.c:403 on :408/:427`), `nfs.c:1434`/`1459` (row's `:1436`/`:1461`,
and the row explicitly notes fable's numbers had drifted). Duplicate — dropped.

**Scratchpad** (`/private/tmp/claude-501/-Users-djbclark-src-tendcf/1d86c32f-4f80-4a41-a71d-137efd39c3cb/scratchpad/`):
`run_panel_4734.sh`, `run_panel_4732.sh` (**written, not yet run**),
`b18-msg2.txt`, `timeout.c.good`, `b18.diff`, `cfe4734_comment.py`,
`b15-autogen.log`, `b15-make.log`, `tier1.json`.

## Operator Feedback

- **Panel seats: grok + gemini, no Fable.** Chosen explicitly when offered the
  three-way choice; Fable was at 93% with a 2026-08-21 reset and stayed
  untouched all session.
- **"Keep going"** after B-18 landed — which is what moved the session onto
  B-15 rather than stopping at the clean seam.
- Standing preferences that shaped the work and were *not* re-asked:
  commit-and-push at milestones without waiting for approval; Jira-only for
  upstream (no fork GitHub issues); terse output.

## Where We're Going

1. **NEXT ACTION — check background build `b9iqld2el`** (`~/src/core-mountleak`,
   `autogen.sh` + `make -j4`). Its outcome was unknown at handoff. If it
   failed, read `scratchpad/b15-make.log` / `b15-autogen.log`; if it
   succeeded, confirm `cf-agent/nfs.c` compiled clean.
2. **Then launch the B-15 panel**:
   `bash /private/tmp/claude-501/-Users-djbclark-src-tendcf/1d86c32f-4f80-4a41-a71d-137efd39c3cb/scratchpad/run_panel_4732.sh`
   (grok + gemini; brief already frozen at
   `docs/architecture/UPSTREAM-CFE4732-REVIEW-BRIEF.md`). **Weight Q1 and Q3
   hardest** — they gate the public correction.
3. **If the panel says SAFE TO POST:** commit the `nfs.c` fix, push
   `fix/mount-options-timeout-leak` to `djbclark/core`, and post a **correction
   comment** on CFE-4732 (comment, never a body rewrite — retractions must stay
   in the audit trail) covering the masking chain, the corrected severity, and
   the `:487` omission. **If NOT SAFE TO POST:** do not post; re-derive first.
4. **Then update the register B-15 row** (`docs/architecture/upstream-register.md`
   line 100) — it repeats the same wrong severity ("these leak every ordinary
   run", "Bounded: the leaked alarm eventually fires") and omits `:487`. Commit
   and push in `tendcf`.
5. **Then B-16 / CFE-4733** (`ShellCommandReturnsZero()` leaves `ALARM_PID`
   naming a reaped, recyclable pid; `unix.c:225` sets it, reaps at `:238`/`:258`,
   never resets). One-line fix. Register line 101.
6. **Periodic PR-engagement recheck** — commands in Quick Start.

## Quick Start

```bash
# 1. The unknown: did the B-15 build finish?
cat /private/tmp/claude-501/-Users-djbclark-src-tendcf/1d86c32f-4f80-4a41-a71d-137efd39c3cb/tasks/b9iqld2el.output
tail -20 /private/tmp/claude-501/-Users-djbclark-src-tendcf/1d86c32f-4f80-4a41-a71d-137efd39c3cb/scratchpad/b15-make.log

# 2. B-15 state (fix applied, NOT committed)
cd /Users/djbclark/src/core-mountleak
git log --oneline -1        # expect a0bca6aaf (upstream master, no commit yet)
git diff --stat             # expect cf-agent/nfs.c | 9 +++++++++
git diff cf-agent/nfs.c

# 3. B-18 state (done, pushed — nothing to do)
cd /Users/djbclark/src/core-prefork && git log --oneline -1   # expect ab98a5df4

# 4. Launch the B-15 panel
bash /private/tmp/claude-501/-Users-djbclark-src-tendcf/1d86c32f-4f80-4a41-a71d-137efd39c3cb/scratchpad/run_panel_4732.sh

# 5. Jira (CFE-4732 Open, 1 comment). Correction goes in a NEW comment.
TOKEN=$(sudo-secretspec run --reason 'CFE-4732' -- bash -c 'echo $ATLASSIAN_CFENGINE_API_TOKEN')
curl -sS -u djbclark@gmail.com:$TOKEN \
  "https://northerntech.atlassian.net/rest/api/2/issue/CFE-4732?fields=summary,status" | python3 -m json.tool

# 6. PR engagement recheck (all still silent as of this handoff)
gh api repos/NorthernTechHQ/libntech/issues/291/comments -q '.[]|"\(.created_at) \(.user.login)"'
gh api repos/cfengine/core/issues/6305/comments -q '.[]|"\(.created_at) \(.user.login)"'

# TRAPS. Editing libpromises/*.c then `make <x>_test` in tests/unit runs the
# OLD library ("up to date") -- cd libpromises && make first. A fresh
# `git worktree add` has NO submodules -- git submodule update --init.
# testall exits 0 even when every test fails -- read the passed count.
# Before any acceptance run: make && make install (install-prefix RPATH).
```
