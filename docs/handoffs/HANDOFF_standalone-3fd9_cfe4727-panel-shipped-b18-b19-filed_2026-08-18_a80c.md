---
schema_version: 1
handoff_id: a80c
parent_handoff_ids: [214a]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 1c9b9180c990f1f5b5910ccc1db344f870af8964
created_at: 2026-08-18T06:35:00-0400
writer: claude-code
---
# Handoff — CFE-4727 panel-reviewed and shipped; B-18/B-19 filed from panel findings

## The Goal

Resumed via `/baton` from `214a`. That handoff's #1 next action was: run
this project's standard multi-model adversarial review panel on the
already-committed-but-unpushed CFE-4727 fix (`254cbe593` in
`~/src/core-alarmpid`), then push, file, and record it — do not skip the
panel, this is signal-handling code in the same class as B-2/B-8, both of
which had real defects caught by review. Operator said "continue as you
will" — no new direction given, this session executed that plan in full.

## Where We Are

CFE-4727 (B-17) is fixed, panel-reviewed, pushed, and its Jira ticket is
updated. Two new pre-existing defects the panel surfaced are filed as
B-18/B-19. Register updated and pushed. Nothing is blocked; everything
planned for this session is done.

- `~/src/core-alarmpid`, branch `fix/exec-timeout-alarm-pid`, now at
  `8f4ebedbd` (amended from `254cbe593`), pushed to
  `djbclark/core` with upstream tracking set. Working tree clean except
  two harmless untracked leftovers (`review.md` pre-existing, not mine;
  `timeout_test.xml`-style JUnit artifacts already cleaned out of
  `tendcf`, did not check if `core-alarmpid` itself has similar litter —
  see Quick Start).
- `tendcf` at `1c9b9180c990f1f5b5910ccc1db344f870af8964` (this commit),
  pushed to `origin/master` (`frdminc/tendcf`).
- Jira: `CFE-4727` updated by two comments (fix description + panel
  outcome; follow-up naming the two new ticket keys). `CFE-4734` (B-18,
  pre-fork race) and `CFE-4735` (B-19, `fdopen()`-failure leak) filed
  fresh.

## What We Tried

- **Wrote a frozen review brief** (`docs/architecture/UPSTREAM-CFE4727-REVIEW-BRIEF.md`),
  following this repo's established brief/opinion naming and structure
  (modeled directly on `UPSTREAM-B2-MERGE-REVIEW-BRIEF.md`): role, where
  the code is, what the defect was/fix does, numbered attack points,
  traps to control for, what the author did, author's own uncertainties.
- **Dispatched three reviewers**: `gemini --model gemini-3.1-pro-high`,
  `grok --model grok-4.6` (both CLI, backgrounded — grok took ~9 min,
  matching prior-session experience that it's slow but not hung), and
  `fable-deep` via the `Agent` tool (standing authorization for
  upstream-bound code, per `[[fable-deep-always-authorized]]`).
  - **Gemini's first invocation produced empty output** — headless mode
    silently auto-denied a tool call needing the "command" permission.
    Re-ran with `--dangerously-skip-permissions` (matches the documented
    precedent in `HANDOFF_..._json-number-defects_..._e33c.md`), which
    then worked cleanly.
  - Grok ran to completion unattended in the background; its actual
    review content was written **directly to the repo** by the CLI
    itself (`docs/architecture/upstream-opinion-cfe4727-grok-2026-08-18.md`),
    not just piped to stdout — the captured stdout was only its
    tool-call narration plus a short verdict summary. Had to `Read` the
    file directly to see the full 400-line review.
- **Independently verified gemini's specific claims against the actual
  source** before trusting any of them, per `[[panel-reviewer-weighting]]`
  — this caught a real fabrication: gemini asserted a `pid == 0` early
  return had been silently removed from `cf_pclose()`, with a detailed
  (wrong) consequence chain (`waitpid(0, ...)` hijacking an unrelated
  child's exit status). **That check has never existed in `cf_pclose()`**
  — it exists only in `cf_pclose_full_duplex()`, unchanged by this
  commit. Confirmed by reading both the pre-fix and post-fix source
  directly (`git show HEAD~1:... ` vs `HEAD:...`). Grok and fable-deep
  independently reached the same correction without seeing gemini's
  review or each other's (grok: "The author attributed three
  `cf_pclose_full_duplex()` paths to `cf_pclose()`. One of the three is
  not an early return in either version of `cf_pclose()`").
- **Applied the one change all three panelists converged on**: swap
  `sigprocmask()` → `pthread_sigmask()` in the new `ClearAlarmedPid()`
  helper. Rebuilt (`make -C libpromises libpromises.la`, then full
  `make -j4`, both clean, 0 warnings) and reran everything: unit tests
  7/7 (`tests/unit/timeout_test`, 37.44s wall matching the amended
  commit's own later re-measurement), full `04_exec_timeout/` acceptance
  suite 6/6 in 86s via `./testall --gainroot=env --agent=... --cfpromises=...`.
  No regressions.
- **Amended the commit** (still unpushed at the time, so safe to rewrite
  per this project's established practice) rather than stacking a fixup:
  folded in the `pthread_sigmask()` code change, softened the commit
  message's "so the guarantee itself holds" overclaim (fable-deep's
  finding), corrected the "three `cf_pclose()` error paths" description
  to match what grok/fable-deep/my own reading actually found (one path
  is in `cf_pclose()`, two are in `cf_pclose_full_duplex()`), and added a
  paragraph naming the new fdopen-failure finding and crediting the
  panel by name with file references.
- **Verified CFE-4727 already existed on Jira** before deciding how to
  file the fix (`curl` GET via `sudo-secretspec run ... -- bash -c
  'curl -u djbclark@gmail.com:$ATLASSIAN_CFENGINE_API_TOKEN ...'`) —
  found it was filed in the original 2026-08-16/17 batch of 15 issues,
  status "Open", body said "No patch offered." This changed the plan
  from `214a`'s "file a fork issue" (written before the Jira-only
  convention was fully load-bearing for *this specific, pre-existing*
  ticket) to "comment on the existing Jira ticket" — no GitHub fork
  issue was filed, matching `[[upstream-channel-is-jira]]`'s Jira-only
  convention for new-era items. Confirmed via `gh issue list --repo
  djbclark/core` that no fork issue for this defect had ever existed
  (issue `#6` is the *sibling* CFE-4726 reporting defect, not this one).

## Key Decisions

- **Filed no GitHub fork issue for CFE-4727** — deviated from `214a`'s
  literal instruction ("file a fork issue") because that instruction
  predated confirming the ticket already lived on Jira. Posted two Jira
  comments instead (fix description + panel outcome). Judged this as
  applying the spirit of `214a`'s plan (get the fix recorded and linked
  upstream) rather than its letter, given new information the letter
  didn't anticipate.
- **Weighted gemini's review per `[[panel-reviewer-weighting]]`** rather
  than discarding it wholesale for the fabricated `pid == 0` claim or
  accepting it wholesale for its otherwise-detailed trap-control section.
  Verified each of its 7 numbered points individually against source;
  kept the real ones (pthread_sigmask, fdopen-failure comment gap),
  discarded the fabricated one, treated its severity framing
  ("catastrophic", "infinitely safer") as overstated relative to grok's
  measured, more calibrated version of the same underlying finding.
- **Did not fold B-18 (pre-fork race) or B-19 (fdopen leak) into this
  commit**, even though B-19 was newly discovered by this exact panel —
  matches the established pattern (B-15/B-16 were similarly discovered
  during other reviews and filed separately rather than grown into the
  commit under review). All three panelists explicitly endorsed this
  scoping.
- **Assigned B-17 to the previously-unlettered CFE-4727 entry.** The
  register's ticket-mapping table already listed "exec_timeout
  termination half → CFE-4727" without a letter (a gap noted explicitly
  in the register's own prose: "CFE-4727 is the first filing anywhere
  for the exec_timeout termination half"). Rather than reuse the
  mysterious skipped `B-9` slot (searched the whole register file for
  any explanation of that gap — found none), continued sequentially from
  `B-16` for all three new rows (B-17/B-18/B-19).
- **Cleaned up three stray files** (`timeout_test.xml`, `xml_tmp_case`,
  `xml_tmp_suite`) that a unit-test run accidentally wrote into
  `~/src/tendcf`'s root — an artifact of the Bash tool's cwd resetting to
  `tendcf` between calls while I ran `tests/unit/timeout_test` with a
  relative path from a previous `core-alarmpid` `cd`. Confirmed via
  `file`/`head` these were JUnit output before deleting; they were mine
  this session, not pre-existing operator work.

## Evidence & Data

- Commit: `djbclark/core@8f4ebedbd` (amended from `254cbe593`), branch
  `fix/exec-timeout-alarm-pid`, pushed with `-u`. 4 files, 156
  insertions/22 deletions (grew by 6 lines from the amendment's new
  code comment).
- Unit tests post-`pthread_sigmask`: `tests/unit/timeout_test`, **7/7
  pass, RC=0**.
- Acceptance post-`pthread_sigmask`: `08_commands/04_exec_timeout/`,
  **6/6 pass, RC=0, 86s total**, via
  `CFENGINE_TEST_OVERRIDE_WORKDIR=/tmp/cfe4727-repush/workdir
  TEMP=/tmp/cfe4727-repush/tmp ./testall --gainroot=env
  --agent=.../cf-agent/.libs/cf-agent
  --cfpromises=.../cf-promises/.libs/cf-promises
  --cfserverd=.../cf-serverd/.libs/cf-serverd 08_commands/04_exec_timeout`.
- Panel opinions, all in `tendcf`'s `docs/architecture/`:
  `upstream-opinion-cfe4727-gemini31pro-2026-08-18.md` (68 lines),
  `upstream-opinion-cfe4727-grok-2026-08-18.md` (400 lines, by far the
  most rigorous — host-specific C probes, `otool` disassembly, timing
  histograms with real sample counts), `upstream-opinion-cfe4727-fabledeep-2026-08-18.md`
  (412 lines, independently reran discrimination via a scratch-relinked
  binary without touching the worktree, caught a stale line-number
  citation in the original commit message: `:129` vs actual `:144`).
- Jira: `CFE-4727` comment ids `159402` (fix description) and `159403`
  (follow-up naming B-18/B-19). New tickets: `CFE-4734` (id `107672`),
  `CFE-4735` (id `107673`), both project `CFE`, issuetype `Bug`, filed
  via `POST .../rest/api/2/issue` with `fields{project,issuetype,summary,description}`.
- Register commit: `tendcf@1c9b918`, 5 files changed (register.md +
  brief + 3 opinion files), pushed to `origin/master`
  (`frdminc/tendcf`).
- PR-engagement recheck (all 8 open PRs): comment authors checked
  individually for `core#6293`/`#6294` (the two whose counts had grown
  since last check) — all `djbclark` or `CLAassistant`, zero maintainer
  comments anywhere, unchanged from every prior session's finding.

## Operator Feedback

None this session — operator said only "continue as you will" after the
resume-plan summary and did not intervene again. No corrections, no
new instructions. Treat the resume plan as fully operator-endorsed by
silence + non-intervention through a long, consequential session
(pushing to a public fork, filing three Jira tickets, amending a
commit).

## Where We're Going

1. **No urgent next action.** Everything `214a` queued is done. The
   natural next pickup is whichever of the below the operator wants,
   or a fresh `/baton` resume with no specific target — recheck PR/B-10
   status first since those are pure "has anything changed" checks.
2. **B-18 (CFE-4734) and B-19 (CFE-4735) are recorded, not patched.**
   Fix shapes are written into `docs/architecture/upstream-register.md`'s
   new rows: B-18 needs `SetTimeOut()`/fork-order redesign (own ticket,
   touches `TimeOutIsArmed()`-driven `setpgid()` contract — not a small
   patch). B-19 is mechanical: add `ClearAlarmedPid(pid)` after each of
   the 8 `cf_pwait()` calls at `pipes_unix.c:458,470,588,600,670,681,789,800`
   (B-17's new helper makes this a one-liner per site for the first
   time) plus one `ClearTimeOut()` call at `verify_exec.c:371`'s
   `pfp == NULL` branch.
3. **Recheck all 8 open PRs periodically** (unchanged command from every
   prior handoff in this chain):
   `for n in 6293 6294 6299 6300 6302 6305; do gh pr view $n --repo
   cfengine/core --json number,reviewDecision,comments -q '.number,
   (.comments|length)'; done` and `for n in 291 294; do gh pr view $n
   --repo NorthernTechHQ/libntech --json number,reviewDecision,comments
   -q '.number, (.comments|length)'; done` — if a count grows, check
   comment *authors*, not just the count (this session's own false
   alarm: #6293/#6294 grew but were all self-comments).
4. **B-10 core half** (`core-json`, fork ticket `djbclark/core#13`)
   still blocked on `libntech#294` merging AND `djbclark/core#7`
   (submodule bump), both still open — unchanged, recheck both.
5. **OpenAI reviewer seat still unresolved** (unchanged across several
   sessions): `cursor-agent` lists `gpt-5.3-codex-high` but
   self-identifies as Grok per `[[panel-reviewer-weighting]]`
   (unverified again this session — never actually invoked, gemini+grok+
   fable-deep were sufficient); `codex` quota-walled until 2026-08-20;
   `opencode` fails "Insufficient balance."
6. **Not urgent, worth a future look**: `~/src/core-alarmpid`'s untracked
   `review.md` (pre-existing per fable-deep's note, never inspected by
   me) and whether any of the other `core-*`/`libntech-*` worktrees
   accumulated similar test-run litter this session (only checked
   `tendcf` itself).

## Quick Start

```sh
# Confirm the shipped state:
cd /Users/djbclark/src/core-alarmpid
git log --oneline -3          # expect 8f4ebedbd at HEAD
git status --porcelain        # expect only untracked review.md
git log @{u}..HEAD            # expect empty -- pushed and in sync

cd /Users/djbclark/src/tendcf
git log --oneline -3          # expect 1c9b918 at HEAD, pushed
$EDITOR docs/architecture/upstream-register.md   # B-17/B-18/B-19 rows

# Re-verify the Jira tickets exist and read as expected:
TOKEN=$(sudo-secretspec run --reason 'spot-check CFE-4727/4734/4735' -- bash -c 'echo $ATLASSIAN_CFENGINE_API_TOKEN')
curl -sS -u djbclark@gmail.com:$TOKEN \
  "https://northerntech.atlassian.net/rest/api/2/issue/CFE-4727?fields=summary,status" | python3 -m json.tool

# PR engagement recheck (see Where We're Going item 3 for the full loop):
gh pr view 6293 --repo cfengine/core --json comments -q '.comments[].author.login'
```
