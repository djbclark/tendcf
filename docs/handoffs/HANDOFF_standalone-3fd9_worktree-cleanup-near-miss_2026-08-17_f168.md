---
schema_version: 1
handoff_id: f168
parent_handoff_ids: [290d]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: d3e524f98366d520ca2432182a9f5eccdb46e76a
created_at: 2026-08-17T22:39:00-04:00
writer: claude-code
---
# Handoff — Worktree cleanup, ticket corrections, and a caught near-miss

## The Goal

Resumed via `/baton` into chain `standalone-3fd9` (the ongoing B-series
CFEngine/libntech upstream work) to: recheck the six open `cfengine/core`
PRs for maintainer activity, do queued worktree housekeeping, and keep the
Tier 1 session log accurate as things were discovered.

## Where We Are

- Resumed via `/baton`: read the chain-canonical log at
  `~/.local/state/handoffs/chains/standalone-3fd9/SESSION_LOG.md`,
  verified every listed workspace's `head_sha` against real `git rev-parse
  HEAD` — all matched, no drift, briefing-grade.
- Rechecked all six open `cfengine/core` PRs (#6293 #6294 #6299 #6300
  #6302 #6305): **zero maintainer engagement on any of them**, still true
  at session end.
- Discovered #6293/#6294 already carried substantial self-review fixes
  from a *prior* session (a buffer overflow in #6293, eight distinct
  defects in #6294 — see Evidence) that had been force-pushed and already
  superseded their own "hold off merging" notices, but hadn't shown up in
  the log's Recent History because that section caps at 10 entries and
  had rolled the relevant bullets off. The `workspaces` head_shas stayed
  accurate throughout; only the narrative history was stale.
- Removed three worktrees, all clean and byte-identical to their open PR
  heads (operator confirmed each via AskUserQuestion): `core-b12` (PR
  #6302), `core-p1` (PR #6293), `core-p2` (PR #6294). Plain `git worktree
  remove` refuses on any tree carrying the `libntech` submodule even
  *after* `git submodule deinit -f --all` — `--force` is required and is
  safe once submodules are deinitialized and the tree is verified clean
  and matching remote/PR head.
- `core-json` housekeeping: `make clean` (107M→74M), removed its nested
  detached-HEAD `libntech` worktree (74M→61M — it was just the plain
  submodule pin at `5b5d04e`, no unique work). `core-json`'s own branch
  (`fix/json-number-rendering`, 3 commits) was left untouched.
- Investigated what looked like a fourth, previously-untracked worktree,
  `libntech-p3`: it turned out to be the **current head of already-open
  PR `libntech#291`** (fixing issue #290, both already tracked in Jira as
  CFE-4717). Not unshipped work as first assumed — corrected that framing
  in the log before it became an action item.
- Root-caused the original stale blocker note ("libntech-fixes has
  unpushed work at e76700b vs pushed 21364443"): it was actually about
  `libntech-p3`, not `libntech-fixes`, and the real cause was that
  `libntech-p3`'s local branch's git upstream tracking pointed at an
  *abandoned*, differently-named fork ref (`fork/silent-digest-failure-v2`,
  stuck at old commit `21364443`) while the actual PR-backing branch on
  the same fork (`fork/silent-digest-failure`) already held the current
  work (`e76700b`). Fixed the local branch's tracking ref to point at the
  real one.
- Fixed PR #291's commit trailer (`Ticket: #290` → `Ticket: CFE-4717`) via
  `commit --amend` + `push --force` to the correct fork branch. Verified
  tree hash byte-identical before/after. New PR head `4642a50`.
- **Near-miss, caught before acting:** was about to open a `cfengine/core`
  PR for `core-json`'s branch after mischaracterizing it across several
  log writes as generic "unoffered work." It's actually **B-10's core
  half** (register row `docs/architecture/upstream-register.md:95`,
  already carrying a 4-member review panel and a `security@` disclosure),
  and the register explicitly states it cannot land until `libntech#294`
  merges **and** `cfengine/core` bumps its `libntech` submodule pin
  (tracked as `djbclark/core#7`). Confirmed both still open via live `gh`
  checks. **Did not open the PR.**
- Checked whether `core-json`'s fix needed a new fork ticket: it didn't —
  `djbclark/core#13` already existed and already documented it in detail,
  just with a stale "Status" section (claimed verification was
  outstanding; the register says it's done, and the ticket never
  mentioned the real current blocker). Posted a correction **comment**
  (not a body edit, to preserve the audit trail, matching this session's
  established pattern) rather than opening a duplicate ticket:
  https://github.com/djbclark/core/issues/13#issuecomment-5322795550
- Checked on CFE-4727 (exec_timeout termination half): Jira ticket is
  Open, unassigned, zero comments — no progress, no maintainer
  engagement. Its blocker (#6305/#6299 settling) also hasn't cleared:
  #6305 still 0 comments/0 reviews, #6299 still just the 1 comment from
  before. Did **not** start writing the fix, per the existing "do after
  #6305/#6299 settle" gate.

## What We Tried

- `git worktree remove` (no force) on `core-b12` → failed: `fatal:
  working trees containing submodules cannot be moved or removed`, even
  *after* `git submodule deinit -f --all`. Git's check keys off
  `.gitmodules` presence in the tree, not actual submodule-init state.
  Had to add `--force`. Repeated the same two-step sequence
  (`deinit -f --all` then `worktree remove --force`) for `core-p1`,
  `core-p2`, and the nested worktree inside `core-json`.
- `git branch -d` before `git worktree remove` succeeded → failed with
  `cannot delete branch ... used by worktree`. Expected ordering issue,
  not a real failure — branch delete has to come *after* worktree
  removal completes.
- Initially concluded both `libntech-p3` and `core-json`'s branch were
  "never offered upstream." **Wrong for `libntech-p3`** (it's PR #291's
  current head — corrected within the same turn before it reached
  next-steps as an action item). **Wrong for `core-json`** in a more
  consequential way — the operator said "yes" to opening a PR for it
  based on that framing, and only cross-referencing the register
  (`upstream-register.md:95`) at that point revealed the real
  `libntech#294`/`core#7` blocker. Caught before the PR was actually
  created, but it was one message away from happening. Lesson recorded
  in the log: when a branch looks like generic "unoffered work," check
  the register for its actual entry before offering it — a branch not
  yet PR'd can be intentionally blocked, not merely forgotten.
- `gh api repos/NorthernTechHQ/libntech/commits/e76700b/pulls` returned
  `[]` even though `gh pr view 291 --json headRefOid` returned that exact
  commit as the PR's head. The commits→PRs association endpoint appears
  unreliable/lagged for fork-branch commits; `gh pr view <n> --json
  headRefOid` (or `gh api repos/.../pulls/<n> -q .head.sha` for a
  non-cached read) is the reliable source, not that endpoint.

## Key Decisions

- Removed `core-b12`/`core-p1`/`core-p2` (operator confirmed each via
  AskUserQuestion individually or in one small batch, not a blanket
  approval) — all three were clean and byte-identical to their open PR
  heads, so no risk of losing work.
- Did **not** remove `libntech-fixes` — it backs open PR `libntech#294`,
  which is the literal B-10 blocker; removing it would actively hurt
  tracking that dependency.
- Did **not** open a `cfengine/core` PR for `core-json` despite an
  earlier "yes" from the operator — the register-documented
  `libntech#294`/`core#7` dependency, confirmed still open, makes it
  premature; a maintainer couldn't merge it yet regardless.
- Corrected `djbclark/core#13` via a **comment**, not a body edit —
  matches the pattern used throughout this session's other
  self-corrections (#6293, #6294, #291 itself), preserving what was
  originally said and appending what changed and why, rather than
  silently rewriting.
- Fixed PR #291's trailer via `commit --amend` + `push --force` rather
  than a new commit — the PR has no other reviewers/collaborators who'd
  be disrupted by history rewriting, and only the trailer text needed to
  change (tree hash verified unchanged).

## Evidence & Data

- Worktree count before cleanup (`git -C cfengine-core worktree list`):
  7 (cfengine-core, core-acceptance, core-b12, core-b2merge, core-json,
  core-p1, core-p2). After: 4 (cfengine-core, core-acceptance,
  core-b2merge, core-json) — `core-b12`/`core-p1`/`core-p2` removed.
- `core-json` disk usage: 107M → 74M (`make clean`) → 61M (nested
  worktree removed).
- PR comment counts at session end (cfengine/core): #6293 had 5 (all
  self-review/CLA-bot), #6294 had 7 (same), #6299 = 1, #6300 = 0,
  #6302 = 0, #6305 = 0. Zero maintainer *reviews* on any of the six.
- `libntech#291`: CLA-assistant + two `mender-test-bot` CI failures
  (likely a fork-credentials gap, not a real test failure) + two
  self-correction comments. Zero maintainer reviews.
- PR #291 tree hash before/after trailer fix:
  `122bc2b07a2544613563fe43f6702bfb271635b3` (unchanged, confirmed both
  sides). Old head `e76700b05812ac327096443045d3e9264a52a398` → new head
  `4642a502f2c28783fca7bf8b6665169997f974b5`.
- Jira tickets confirmed live this session: **CFE-4717** (status Open,
  unassigned, 0 comments — matches `libntech#291`/issue #290) and
  **CFE-4727** (status Open, unassigned, 0 comments — exec_timeout
  termination half).
- Fork issue `djbclark/core#13` (B-10 core half, pre-existing) — status
  corrected via comment:
  https://github.com/djbclark/core/issues/13#issuecomment-5322795550
- Register citation that caught the near-miss:
  `docs/architecture/upstream-register.md:95` (B-10 row).
- `djbclark/core#7` (submodule-bump tracking issue) and
  `NorthernTechHQ/libntech#294` (PR) both confirmed **OPEN/unmerged** at
  session end via `gh issue view` / `gh pr view`.
- No files changed inside the `tendcf` repo itself this session (`git
  diff --stat` empty, working tree clean at `d3e524f`) — all actual
  changes were git/GitHub state in the other workspaces (worktree
  removal, one amended+force-pushed commit, GitHub comments) plus this
  session's Tier 1 log writes.

## Operator Feedback

- Operator confirmed each worktree removal individually via
  AskUserQuestion rather than blanket-authorizing all housekeeping at
  once — continue treating future worktree removals the same way
  (confirm per item or small batch), not as an implicit "safe to clean
  up" standing policy.
- Operator didn't catch the `core-json` near-miss directly (their "yes"
  was given based on the framing available at the time) — it was
  self-caught by cross-referencing the register before acting. Keep doing
  that cross-check even when a task looks like routine unfinished-work
  cleanup, especially right before any upstream-visible action (opening a
  PR, force-pushing to a shared branch).
- Session was flagged as getting large (154,754 cached tokens) via the
  UserPromptSubmit hook; operator responded by invoking `/handoff` rather
  than continuing — treat that as the natural wrap point for this thread.

## Where We're Going

1. **THE next action:** Watch for `libntech#294` merging and
   `djbclark/core#7`'s submodule bump landing — once **both** land,
   `core-json`'s `fix/json-number-rendering` becomes safe to offer as a
   `cfengine/core` PR (B-10 core half; fork ticket `djbclark/core#13`
   already documents it and now carries a current status comment). This
   is the actual trigger condition, not a time-based recheck.
2. Recheck all open PRs periodically for maintainer activity —
   cfengine/core: `for n in 6293 6294 6299 6300 6302 6305; do gh pr view
   $n --repo cfengine/core --json number,reviewDecision,comments -q
   '.number, (.comments|length)'; done`; libntech: `for n in 291 294; do
   gh pr view $n --repo NorthernTechHQ/libntech --json
   number,reviewDecision,comments -q '.number, (.comments|length)'; done`
3. CFE-4727 exec_timeout termination half: still unwritten, still gated
   on #6305/#6299 settling (no maintainer engagement yet). When it
   clears, start from the ALARM_PID theory: `cf_pclose()` clearing
   `ALARM_PID` before waiting is the suspected residual defect, same
   signal-path family as filed-but-unpatched CFE-4732/B-15 and
   CFE-4733/B-16.
4. `core-acceptance` worktree: also gated on #6299/#6305 settling (same
   as CFE-4727) — do not remove or act on it before then.
5. OpenAI reviewer seat still unresolved: `cursor-agent` lists
   `gpt-5.3-codex-high` but self-identifies as Grok per prior memory
   (unverified this session); `codex` quota-walled until 2026-08-20;
   `opencode` fails "Insufficient balance." Needed whenever a genuine
   independent-lab review panel is required again.

## Quick Start

- Resume via `/baton` or `/resume` — reads
  `~/.local/state/handoffs/tendcf/main/SESSION_LOG.md` → redirects to
  `~/.local/state/handoffs/chains/standalone-3fd9/SESSION_LOG.md`, which
  now points `latest_handoff` at this file.
- PR/maintainer-activity recheck commands: see "Where We're Going" item 2
  above.
- Jira write recipe: `TOKEN=$(sudo-secretspec get
  ATLASSIAN_CFENGINE_API_TOKEN --reason '<why>'); curl -sS -u
  djbclark@gmail.com:$TOKEN -X POST -H 'Content-Type: application/json'
  --data @file
  https://northerntech.atlassian.net/rest/api/2/issue/<KEY>/comment` —
  drop the `/<KEY>/comment` suffix and POST
  `fields{project,issuetype,summary,description}` to create a new ticket
  instead.
- Remaining tracked worktrees after this session:
  - `/Users/djbclark/src/tendcf` (`main`, this repo)
  - `/Users/djbclark/src/core-b2merge` (`fix/timeout-process-group-merged`, PR #6305)
  - `/Users/djbclark/src/core-acceptance` (`fix/exec-timeout-poll-deadline`, blocked on #6299/#6305 settling)
  - `/Users/djbclark/src/libntech-fixes` (`fix/json-number-handling`, PR #294 — B-10 blocker, do not remove)
  - `/Users/djbclark/src/core-json` (`fix/json-number-rendering`, B-10 core half, blocked on #294+core#7)
  - `/Users/djbclark/src/libntech-p3` (`silent-digest-failure-v2`, PR #291 — do not remove)
