---
schema_version: 1
handoff_id: 290d
parent_handoff_ids: [29e5]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: c449b24a345cbdeb2ea5d6c68750cf43faecbc6f
created_at: 2026-08-17T22:08:30-0400
writer: claude-code
---
# Handoff — B-2 shipped as core#6305 without Fable; six PRs now open, zero maintainer engagement

## The Goal

Resume the CFEngine upstream-fixing project from handoff `29e5`
(`b12-upstreamed-b2-deferred`). That handoff's THE NEXT ACTION was: apply
B-2/CFE-4729's three previously-required changes in
`/Users/djbclark/src/core-b2merge` (blocked pending a fresh 5h window and
`fable-deep`), re-verify, run a small 2-seat panel on the deltas, and decide
whether to offer upstream.

Early in this session the operator changed the constraint: *"Okay you are
allowed to not use fable now. Conserve it, use only if you really need
it."* That reframed the whole session — the work below was done end to end
without a single Fable call.

## Where We Are

**B-2/CFE-4729 is fully shipped**, offered upstream as
[cfengine/core#6305](https://github.com/cfengine/core/pull/6305).

- Branch `fix/timeout-process-group-merged` in `/Users/djbclark/src/core-b2merge`,
  now pushed to `origin` (`djbclark/core`), tip `dbf759d16ae5d085fdafc7176eccc07c77b7a48a`.
- Two new commits on top of the already-merged B-8+B-2 base (`3d8e90d68`):
  - `d004c19ab` — MinGW guard (`#ifndef __MINGW32__`) around `getpgid()`/
    `kill(-pid, SIGKILL)` in `libpromises/timeout.c` (that file builds
    unconditionally on Windows; the `setpgid()` child-side half in
    `pipes_unix.c` is `if !NT` only, confirmed by reading
    `libpromises/Makefile.am`), plus converting `TIMEOUT_ARMED` from a plain
    `bool` to `volatile sig_atomic_t` (it is written from `TimeOut()`, a
    `SIGALRM` handler, same as `TIMEOUT_FIRED`/`TIMEOUT_SIGNALLED` already
    were — an oversight in the original series).
  - `dbf759d16` — `tests/unit/timeout_test.c`, 6 cases pinning
    `SetTimeOut()`/`ClearTimeOut()`/`TimeOut()`'s armed/fired/signalled
    contract (`if !NT` in `tests/unit/Makefile.am` — it waits on a real
    `SIGALRM` and Windows has no `alarm()` implementation in this tree).
- `docs/architecture/upstream-register.md` (this repo) updated: B-2's row now
  reflects "done" across the board, pushed as `c449b24`.
- Left a pointer comment on the already-open `#6299`
  (`https://github.com/cfengine/core/pull/6299#issuecomment-5322521891`)
  noting `#6305` supersedes it, since `core-b2merge` is a merge of B-8
  (`#6299`'s own commits `6e522a730`/`0ab083c4d`) with B-2's process-group
  fix.
- Tier 1 session log (`~/.local/state/handoffs/chains/standalone-3fd9/`)
  updated via `session_log.py write` with the new state and workspace list.
- New memory saved (and then corrected once):
  `reviewer-seats-model-check.md` — how to get review seats when conserving
  Fable, with an explicit caution that `cursor-agent`'s "OpenAI" seat is
  unverified this session (prior memory `panel-reviewer-weighting.md` says
  it self-identifies as Grok despite listing `gpt-5.3-codex-*` models).

**Upstream PR landscape as of this session (rechecked twice, ~2 hours apart):
six open PRs, zero maintainer comments or reviews on any of them.**
`#6293 #6294 #6299 #6300 #6302 #6305`. Every existing comment on
`#6293`/`#6294` is ours; every review count is 0.

## What We Tried

- **First grok invocation timed out.** `grok --model grok-4.6 -p "$(cat
  packet.txt)"` with a 280s foreground timeout returned rc=124 with empty
  output. Retried the identical command backgrounded (Bash
  `run_in_background: true`, no timeout cap) — it was actively tool-calling
  through the repo the whole time (confirmed via `ps aux` and reading the
  partial output file), just slow on a multi-file packet. Completed in full
  on the second, unbounded attempt. **Lesson:** a slow CLI reviewer is not a
  hung one; check process state and output growth before assuming failure.
- **Tried an ad-hoc ladder-timing repro** (`sleep 30` under a 10s
  `exec_timeout`, run via `cf-agent -Kf <policy> --no-lock`) to re-confirm
  the bounded-wall-clock behavior independently of the acceptance suite.
  It hit the failsafe bootstrap path instead of running the custom policy
  (no policy hub reachable) and produced nothing useful. **Abandoned** —
  the six acceptance tests already in `tests/acceptance/08_commands/
  04_exec_timeout/` (including `timeout_kills_descendants.cf`) exercise
  exactly this scenario and had already passed 6/6, so the ad-hoc repro
  was redundant, not a real gap.
- **First unit-test draft had a real, reviewer-caught gap.** The original
  5 cases never exercised `TimeOutSignalledProcess()` being **TRUE** and
  surviving `ClearTimeOut()` — every case that reached `ClearTimeOut()`
  after a fire had `ALARM_PID == -1` (no process signalled), so the flag
  was always already `false`. A `ClearTimeOut()` that wiped a *true*
  `TIMEOUT_SIGNALLED` would have passed all 5 tests. **grok-4.6 caught
  this**; gemini's independent review of the same draft did not. Fixed
  with a 6th case (`test_clear_preserves_a_true_signalled_flag`) that
  forks a real child, arms a 1s timeout, sets `ALARM_PID` to the child's
  pid (matching the real ordering in `cf-agent/verify_exec.c`: `SetTimeOut()`
  first, `ALARM_PID` assigned after), waits for the alarm, asserts the flag
  is true, calls `ClearTimeOut()`, asserts it is *still* true, then
  `waitpid()`s to reap. Verified by discrimination (see Evidence).

## Key Decisions

- **2-seat panel with pinned `gemini-3.1-pro-high` + `grok-4.6` instead of
  Fable**, per the operator's explicit "conserve Fable" instruction this
  session. `cursor-agent --model gpt-5.3-codex-high` was identified as a
  possible third/fallback OpenAI seat (`codex` itself is quota-walled until
  2026-08-20, `opencode` returns "Insufficient balance") but was **never
  actually invoked** — grok's backgrounded retry succeeded before it was
  needed. Its reliability as a genuine non-Grok seat remains unverified this
  session; see the new `reviewer-seats-model-check` memory.
- **Amended commits rather than stacking fixup commits.** Both `d004c19ab`
  and `dbf759d16` were amended in place (once each) after review findings,
  because the branch had not yet been pushed anywhere — safe to rewrite.
  Confirmed via `git log @{u}` erroring "no upstream configured" before
  amending.
- **Asked the operator rather than deciding solo how to relate the combined
  branch to the already-open `#6299`.** `core-b2merge` contains B-8's two
  commits (already open standalone as `#6299`, zero engagement) merged with
  B-2's process-group fix — pushing it as a new PR duplicates those commits
  into a second, unreviewed PR. Presented three options via
  `AskUserQuestion`; operator chose **"open as new PR, note supersedes
  #6299"** over waiting for `#6299` to merge first or pushing silently. This
  is a direct instance of the standing `upstream-artifacts-need-approval`
  memory (ambiguous + hard-to-reverse public action → ask first).
- **Register update committed and pushed directly to `master`**, matching
  the established pattern in this repo's session history (prior sessions'
  `2064cc8`, `7d74269`, etc. did the same) even though `docs/architecture/`
  is not literally inside `docs/handoffs/`'s narrow push-in-place carve-out
  per this repo's `CLAUDE.md`. Followed established practice rather than
  re-litigating repo policy mid-task; flagged here for the record in case a
  future session should tighten this.

## Evidence & Data

- Pristine `libpromises/timeout.c` sha256 (before and after every
  discrimination round, always restored):
  `a5d947a2d9a587ddf3428fbe59aa16586499bbfb5f1ac9feaa6b57a3b1f9682d`
- Full rebuild: `make -j4` clean, 0 warnings, both after the first two
  commits and again after the test-fix amendment.
- Unit tests: `tests/unit/timeout_test.c`, 6/6 pass, ~12s wall time (dominated
  by the two 1s-alarm cases plus the 5s-sleep fork case).
- Acceptance tests: `tests/acceptance/08_commands/04_exec_timeout/`, 6/6
  pass, run twice (~63s and ~71s), via
  `./testall --gainroot=env --agent=... --cfpromises=... [...] 08_commands/04_exec_timeout/`.
- Discrimination (4 independent perturbations, each via `perl -0pi` on a
  pristine copy, each restored and reconfirmed byte-identical afterward):
  1. `ClearTimeOut()` also clears `TIMEOUT_FIRED`/`TIMEOUT_SIGNALLED` →
     fails exactly `test_clear_preserves_the_record`.
  2. `ClearTimeOut()` forgets to disarm → fails exactly `test_clear_disarms`.
  3. The signal handler forgets to disarm → fails exactly
     `test_fired_alarm_without_a_process`.
  4. `ClearTimeOut()` clears a **true** `TIMEOUT_SIGNALLED` (the bug the 6th
     case targets) → fails exactly `test_clear_preserves_a_true_signalled_flag`.
- Gemini's clean review of the original delta (4 questions: MinGW guard
  placement/sufficiency, `sig_atomic_t` necessity, test contract fidelity,
  other bugs) — no issues on any point.
- Grok's review of the same delta — no issues on points 1/2/4; point 3
  (test contract fidelity) correctly identified the gap described above.
- Gemini's follow-up review of the fixed 6th test case — confirmed safe on
  all three specific concerns raised (cmockery/signal interaction,
  `waitpid()` race safety, CI flakiness risk); flagged one theoretical
  microsecond-scale race between `SetTimeOut(1)` and `ALARM_PID = child`
  as "effectively zero" real-world risk.
- PR: [cfengine/core#6305](https://github.com/cfengine/core/pull/6305),
  title "CFE-4729: Kill a timed-out command's whole process group", body
  written in the terse house style established by `#6302` (per the
  standing "be terse" upstream feedback), explicitly documents the
  supersedes-`#6299` relationship and the discrimination results.
- Six-PR recheck (twice, before and after this session's work): zero
  maintainer comments or `reviewDecision` on any of `#6293 #6294 #6299
  #6300 #6302 #6305`.

## Operator Feedback

- *"Okay you are allowed to not use fable now. Conserve it, use only if you
  really need to."* — direct instruction that reshaped the whole session;
  the work was completed without any Fable call, using pinned gemini/grok
  instead for review.
- `AskUserQuestion` on the `#6299` overlap: operator selected **"Open as new
  PR, note supersedes #6299 (Recommended)"** over waiting for `#6299` to
  merge first, or pushing without flagging the overlap.
- `/handoff` invoked at a natural stopping point after a UserPromptSubmit
  hook flagged context size (~192K cached tokens) and suggested wrapping up.

## Where We're Going

1. **THE NEXT ACTION** — recheck all six open PRs for any maintainer
   activity before doing anything else:
   ```
   for n in 6293 6294 6299 6300 6302 6305; do
     gh pr view $n --repo cfengine/core --json number,reviewDecision,comments -q '.number, (.comments|length)'
   done
   ```
2. **CFE-4727** (exec_timeout termination half) is still unwritten. Start
   from the `ALARM_PID` theory: `cf_pclose()` clears `ALARM_PID` before
   waiting, which is the residual defect (its earlier refutation was
   retracted — see prior handoffs). Do this **after** `#6305`/`#6299`
   settle upstream — same signal-path family. `CFE-4732`/B-15 (armed alarm
   never disarmed in `ReconcileMountOptions()`) and `CFE-4733`/B-16 (stale
   `ALARM_PID` after reap in `ShellCommandReturnsZero()`) are filed but
   unpatched, and are adjacent evidence in the same file family — revisit
   together.
3. **Worktree housekeeping**, all deferred across multiple sessions now:
   - `core-json` — needs `make clean`; has a nested `libntech` worktree at
     `core-json/libntech` that also needs handling.
   - `core-p1`/`core-p2` — `git worktree remove` refuses ("working trees
     containing submodules cannot be moved or removed") because each
     carries the `libntech` submodule. Needs `git submodule deinit` first,
     or `--force`.
   - `core-acceptance` — holds B-8's acceptance-test commit; safe to remove
     once `#6299`/`#6305` settle upstream.
   - `core-b12` — B-12/`#6302` already offered; safe to remove now.
   - `libntech-fixes` (formerly `libntech-p3`) — **has unpushed local work**:
     local HEAD `e76700b` vs pushed `fork/silent-digest-failure-v2` at
     `21364443`. **Diff the delta before touching this worktree at all.**
4. Jira write recipe, for filing/commenting on CFE tickets:
   ```
   TOKEN=$(sudo-secretspec get ATLASSIAN_CFENGINE_API_TOKEN --reason '<why>')
   curl -sS -u djbclark@gmail.com:$TOKEN -X POST -H 'Content-Type: application/json' \
     --data @file https://northerntech.atlassian.net/rest/api/2/issue/<KEY>/comment
   ```
   Drop the `/<KEY>/comment` suffix and POST `fields{project,issuetype,summary,description}` to create instead of comment.

## Quick Start

```bash
# Resume: read the Tier 1 pointer, it will redirect here.
~/.claude/hooks/handoff-tools/.venv/bin/python \
  ~/.claude/hooks/handoff-tools/session_log.py read \
  --state-root ~/.local/state/handoffs --dir ~/.local/state/handoffs/tendcf/main

# THE NEXT ACTION:
for n in 6293 6294 6299 6300 6302 6305; do
  gh pr view $n --repo cfengine/core --json number,reviewDecision,comments -q '.number, (.comments|length)'
done

# Register and PR for reference:
sed -n '92p' /Users/djbclark/src/tendcf/docs/architecture/upstream-register.md
gh pr view 6305 --repo cfengine/core --json url,state,mergeable -q '.'
```
