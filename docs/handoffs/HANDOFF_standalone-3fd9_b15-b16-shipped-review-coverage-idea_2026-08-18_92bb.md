---
schema_version: 1
handoff_id: 92bb
parent_handoff_ids: [8b7f]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 0c0f332cc0bee71759a9891eb9e7a88a0dd452d6
created_at: 2026-08-18T13:29:19-0400
writer: claude-code
---

# Handoff — B-15 and B-16 shipped end to end; community-review-coverage idea captured, not started

## The Goal

Resume the CFEngine upstream fix queue from handoff 8b7f (B-18 shipped,
B-15's severity flagged wrong and mid-flight). Ship B-15 (CFE-4732)
correctly — including retracting the ticket's overstated severity — then
continue down the queue.

## Where We Are

**B-15 (CFE-4732) SHIPPED end to end.**
- Fix: `djbclark/core@190f869a5` on branch `fix/mount-options-timeout-leak`
  (`~/src/core-mountleak`), cut from upstream master `a0bca6aaf`. Two-line
  disarm inside the method loop in `ReconcileMountOptions()`
  (`cf-agent/nfs.c`), before `LiveMountConverged()`.
- Panel: 2-seat (grok-4.6, gemini-3.1-pro-high) against a frozen brief
  (`docs/architecture/UPSTREAM-CFE4732-REVIEW-BRIEF.md`, tendcf `9cf07d0`).
  Unanimous SHIP / SAFE TO POST on all 7 questions. Opinions at
  `docs/architecture/upstream-opinion-cfe4732-{grok,gemini31pro}-2026-08-18.md`.
- Jira: correction comment **159434** posted on CFE-4732. Wording matters
  here — grok's review insisted on saying "the *remount-timeout* does not
  escape `ReconcileMountOptions()`," not "the leak never escapes the
  function": `LoadMountInfo()`'s own `RPCTIMEOUT` alarm still escapes on
  its pre-existing `:408`/`:427`/`:487` error-path returns. That precise
  phrasing is in the posted comment.
- Also found and included in the same comment: a third `LoadMountInfo()`
  early-return leak at `:487` (`strstr(vbuff, "RPC")` abort) the original
  ticket catalogue omitted alongside `:408`/`:427`.
- Register row (`docs/architecture/upstream-register.md` line 100)
  corrected to match. tendcf commits: `3d0bab5` (register),
  `2832cdf` (frozen brief), `0c0f332` (panel opinions).

**B-16 (CFE-4733) SHIPPED end to end.**
- Fix: `djbclark/core@e7fd46c6d` on branch `fix/alarm-pid-reset-after-reap`
  (new worktree `~/src/core-alarmreset`, cut from upstream master
  `a0bca6aaf`). Two insertions in `ShellCommandReturnsZero()`
  (`libpromises/unix.c`): `ALARM_PID = -1` immediately after each of the
  function's two reap sites (`:238` WNOHANG-break, `:258` blocking drain
  on the pending-termination path).
- New test: `tests/unit/unix_test.c` (added to `Makefile.am`'s `if !NT`
  block next to `nfs_test`, links `libpromises.la`). Two cases
  (`true`/`false` via `SHELL_TYPE_USE`) assert `ALARM_PID == -1` post-reap.
  **This function is directly testable** (exported, no `EvalContext`/
  `Promise` fixture needed), unlike the `nfs.c` family.
- Discrimination proven by hand: `git stash` on just `unix.c`, full
  rebuild, both tests failed against unpatched code (`ALARM_PID` observed
  as the literal reaped pid, not `-1`); restored, rebuilt, both pass.
- Panel: same 2-seat roster against
  `docs/architecture/UPSTREAM-CFE4733-REVIEW-BRIEF.md`. Unanimous SHIP, no
  required changes. Opinions at
  `docs/architecture/upstream-opinion-cfe4733-{grok,gemini31pro}-2026-08-18.md`.
  Gemini engaged substantively this round (independently derived the same
  `ECHILD`-means-already-reaped reasoning grok gave), unlike its shallower
  pass on B-15.
- Jira: shipped comment **159435** on CFE-4733 (no correction needed —
  the filed ticket's severity and line numbers both checked out against
  current master, unlike B-15).
- Register row (line 101) updated. tendcf commits: `2832cdf` (brief),
  `fb93e94` (register), `0c0f332` (panel opinions, same commit as B-15's).

**Session log** already updated mid-session after B-15 shipped (before
B-16 started) via `session_log.py write` — canonical log at
`~/.local/state/handoffs/chains/standalone-3fd9/SESSION_LOG.md`. This
handoff supersedes that entry's "Active work" for B-16's completion; the
`workspaces` list there is missing `core-alarmreset` (didn't exist yet
when that write ran) — the next session log write should add it.

**Working tree**: clean. `HEAD` = `0c0f332`.

## What We Tried

- **First discrimination attempt for B-16's test nearly gave a false
  pass.** After `git stash` on `unix.c`, ran `make unix.lo` (object-only)
  in `libpromises/`, then rebuilt `unix_test` in `tests/unit/` — both
  tests still passed, because `unix_test`'s binary relinked against the
  *stale, already-archived* `libpromises.la` rather than the freshly
  compiled object. This is the exact stale-library trap from
  [[libpromises-edit-needs-library-rebuild]], and it would have faked a
  negative discrimination result (making the test look valid when it
  wasn't actually exercising the code change). Caught by noticing
  `make: 'unix_test' is up to date` in the output rather than trusting
  the green result. Fixed by running a full `make` (not a narrow target)
  in `libpromises/` to force the `.la` to relink, then force-deleting and
  rebuilding `unix_test`. Documented in both the frozen B-16 brief and
  the register row so it doesn't get re-discovered.
- **Considered testing B-16's `:258` blocking-drain path** (the
  pending-termination branch) with a real `SIGTERM` delivered mid-poll.
  Rejected by both the operator's reasoning and the panel: `HandleSignalsForDaemon`
  + `raise(SIGTERM)` + a long-running child would work in principle, but
  `ProcessSignalTerminate()` sleeps 1s/5s/1s on a child that doesn't die
  to `SIGINT`, `PENDING_TERMINATION` has no reset API (would leak across
  the rest of the test process), and it's the rarer daemon-only path
  anyway. Shipped with the identical one-line fix but no dedicated test;
  stated plainly in the brief, register, and Jira comment rather than
  invented or silently skipped.

## Key Decisions

- **Posted the CFE-4732 correction with precise wording**, chosen over
  the brief's own looser framing ("the leak never escapes the function")
  specifically because grok's review caught the imprecision: only the
  *remount-timeout* provably doesn't escape; `LoadMountInfo()`'s own alarm
  still does on its own error paths. Getting this wrong would have traded
  one overstated public claim for another.
- **Weighted grok's review over gemini's on B-15** (grok's trap-control
  and line-by-line walk were substantially deeper; gemini's Q7 answer
  was also off-target — attributed untestability to `EvalContext`/
  `Promise` scaffolding rather than grok's more precise observability
  argument) — consistent with [[panel-reviewer-weighting]]. On B-16,
  gemini's review was judged comparably strong to grok's this time and
  that's noted in the register, since the weighting habit is about
  grading substance each time, not a fixed discount on gemini.
  Confirmed before posting anything: verdict weighting shaped wording,
  not the ship/no-ship decision itself (both panels were unanimous
  either way).
- **Ran a full 2-seat panel for B-16 even though it's a tiny fix**,
  matching the house convention established by every prior "done" row in
  the register (every one has a panel, including B-19's similarly small
  hygiene fix) rather than skipping review because the diff is small.
- **Left `unix.c:249`'s failed-`waitpid()` path alone** (no `ALARM_PID`
  reset there) — both panelists independently agreed: no reap occurs on
  that path, so the zombie-holds-the-slot reasoning the ticket itself
  relies on still applies; resetting there would be the wrong fix.
- **Declined to build a C-source minifier / community review-coverage
  guide this session** — see the operator's idea below. Wrote it up as
  an idea-stage research doc instead of implementing anything, pending
  two unverified premises.

## Operator Feedback

Mid-session the operator raised an idea: before running ultrareview
broadly against `cfengine/core`, minify the C source (or otherwise pack
more code onto fewer lines) so more of the codebase fits under
ultrareview's 500-file/12,000-line cap, then publish a guide + minifier
so other CFEngine contributors can each spend their own ultrareview usage
covering different segments, for full community coverage.

Response given (not yet acted on beyond documentation): identifier-
renaming minifiers (`minify-C`, `shortC`) were rejected — they'd break
the `file.c:line` citation discipline this whole session's corrections
and register rely on. Whitespace/comment-only compactors (`cminify` by
Scylardor, `C-Minifier` by BaseMax) are the safer half — C only requires
newlines around preprocessor directives, so these preserve every
identifier and only cost the ability to cite line numbers directly
(mitigated by re-deriving the true line via `grep` on the name before
citing anything public). Two premises are unverified and block starting:
whether CFEngine contributors actually have any "free ultrareview
credits" to spend (the operator's framing; not confirmed to exist as a
real program), and whether a whitespace-only compactor's yield is even
worth it against already-dense cfengine C. Also flagged: near-zero
maintainer engagement so far this session argues for floating the idea
informally with an already-engaged maintainer before publishing a guide
and asking the wider contributor base to adopt new tooling.

Operator's own framing on scope, given after the pushback: "For now let's
just continue with our work queue, but create a research document so we
don't need to have this part of the conversation again." — i.e. capture
the idea, don't build it, don't lose the reasoning.

Captured at
`~/ops/site-djbclark/research/cfengine-community-review-coverage/README.md`
(site-djbclark commit `be8f658`, pushed — that repo's `research/` is a
push-in-place data exception per its own `AGENTS.md`, separate from
tendcf). Indexed in that repo's `research/README.md`. Status inside the
doc is explicitly "idea stage, not started," with the two premises listed
as blocking next steps if picked back up.

## Evidence & Data

- B-15 build: full `make -j4` clean, `nfs.lo` no warnings (confirmed
  earlier in the parent handoff, re-confirmed unaffected by this
  session's B-16 work in a different worktree).
- B-16 build: `NO_CONFIGURE=1 ./autogen.sh` + `./configure
  --prefix=$HOME/opt/cfengine-dev-4733 --with-openssl=/opt/homebrew/opt/openssl@3
  --with-pcre2=/opt/homebrew/opt/pcre2 --with-lmdb=/opt/homebrew/opt/lmdb
  --with-libyaml=/opt/homebrew/opt/libyaml --enable-maintainer-mode` +
  `make -j4`, exit 0, no new warnings. `tests/unit/unix_test`: 2/2 pass
  post-fix, 2/2 fail pre-fix (both observed directly, not asserted).
- Jira comment ids: CFE-4732 → 159434 (correction), CFE-4733 → 159435
  (shipped). Both posted via `POST
  https://northerntech.atlassian.net/rest/api/2/issue/<KEY>/comment` with
  `sudo-secretspec get ATLASSIAN_CFENGINE_API_TOKEN`.
- Maintainer-engagement recheck this session (via `gh`): no new activity.
  `cfengine/core#6305` last review still nickanderson `2026-08-18T12:28:39Z`
  (already answered by djbclark `14:40:23Z`, both pre-dating this
  session's work); `djbclark/core#7` and `NorthernTechHQ/libntech#294`
  unchanged, both still open and still the blockers for B-10/CFE-4725's
  core half. Do not reattempt that fix — it's genuinely blocked on those
  two merging, not on anything actionable locally.
- New worktree this session: `~/src/core-alarmreset` (branch
  `fix/alarm-pid-reset-after-reap`, pushed to `djbclark/core`). Needed
  `git submodule update --init` (fresh `git worktree add` has none) and
  its own `./configure`/`make -j4` — both done, tree is built and clean.

## Where We're Going

1. **NEXT ACTION**: Pick up the older, unstarted batch — B-3, B-5a, B-5b,
   B-6, B-7 (`docs/architecture/upstream-register.md`, rows below B-16).
   Each has a filed `djbclark/core` GitHub issue (#12, #8, #9, #10, #11
   respectively) but no branch or fix started. **B-3 in particular is
   real implementation work**, not a hygiene fix: macOS has no
   `process_darwin.c`, so `GetProcessState()` falls back to a stub that
   never reports ZOMBIE/STOPPED, disabling `SafeKill()`'s PID-recycling
   guard on Darwin. Scope that one out before starting — it may warrant
   its own frozen brief and panel before any code is written, given the
   size.
2. Maintainer recheck: `gh pr view 6305 -R cfengine/core --json reviews`
   and `gh pr view 294 -R NorthernTechHQ/libntech --json comments` for
   anything new since this handoff's timestamps above.
3. If the community-review-coverage idea comes back up: don't restart
   the discussion from scratch — read
   `~/ops/site-djbclark/research/cfengine-community-review-coverage/README.md`
   first, then move straight to its "Status" section's two blocking
   premises.
4. Fable is still ~93% used (resets 2026-08-21) — continue avoiding it
   for routine panel work; grok + gemini-3.1-pro-high has been sufficient
   for every panel this session.

## Quick Start

```bash
cd /Users/djbclark/src/tendcf && git status && git log --oneline -5
# Confirm clean tree at 0c0f332 or later.

sed -n '93,109p' docs/architecture/upstream-register.md
# Re-read B-3/B-5a/B-5b/B-6/B-7 rows before starting.

gh issue view 12 -R djbclark/core   # B-3, process_darwin.c
gh issue view 8  -R djbclark/core   # B-5a
gh issue view 9  -R djbclark/core   # B-5b
gh issue view 10 -R djbclark/core   # B-6
gh issue view 11 -R djbclark/core   # B-7

# Maintainer recheck:
gh pr view 6305 -R cfengine/core --json reviews --jq '.reviews[-1]'
gh pr view 294 -R NorthernTechHQ/libntech --json comments --jq '.comments[-1]'

# Community-review-coverage idea, if it resurfaces:
cat ~/ops/site-djbclark/research/cfengine-community-review-coverage/README.md
```
