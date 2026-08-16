---
schema_version: 1
handoff_id: 11e3
parent_handoff_ids: [4830]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: f2e215649dc5110ec918a1f723293e647b3c2618
created_at: 2026-08-16T00:35:00-0400
writer: claude-code
---

# Handoff — All three CFEngine PRs filed ticketless, Telegram-tracked

## The Goal

Resumed from `4830` via `/baton`. That handoff left PR 3 (libntech) filed
with a fork review PR but the upstream PR blocked on a Jira ticket number,
and PRs 1–2 (`djbclark/core`) untouched, same blocker. The operator wanted
to actually find a place to put the bug report given Jira was inaccessible,
then extended the same treatment to all three. That reframing is the whole
session: get all three CFEngine changes into real, trackable public state
without Jira, rather than waiting on it.

## Where We Are

| Workspace | Path | Branch | HEAD | State |
|---|---|---|---|---|
| tendcf | `~/src/tendcf` | `master` | `f2e2156` | clean, pushed |
| cfengine-core | `~/src/cfengine-core` | `simulate-json` | `9a7b861b5` | ` M libntech` — expected, do not commit |
| libntech | `~/src/cfengine-core/libntech` | `silent-digest-failure` | `da7d3d9` | clean |

`simulate-keep-chroot` branch (not checked out): `0ff86ae44`.

**All three CFEngine change sets are now filed:**

- **PR 3** (libntech silent-digest-failure): `djbclark/libntech#1` fork
  review PR open (unchanged from `4830`). Since Jira access stayed broken,
  filed **`NorthernTechHQ/libntech#290`** as a GitHub issue instead of a
  Jira ticket — libntech has GitHub Issues enabled and real maintainer
  precedent of linking Jira tickets from issues there (see Evidence).
  Upstream PR still not opened; still wants a ticket number for its title,
  or a decision to go ticketless too (see Where We're Going).
- **PR 1** (`--simulate-keep-chroot`, was `5dbd295f6`, now `0ff86ae44`
  after amend): opened directly as **`cfengine/core#6293`**, ticketless.
- **PR 2** (`--simulate-json`, was `071f85987`, now `9a7b861b5` after
  amend): opened directly as **`cfengine/core#6294`**, ticketless.

**All three are wired into site-djbclark's Telegram issue-tracking
matrix** (`track-issue-activity.yml`, hourly cron): `libntech-290` (PR
#155, merged), `cfengine-core-6293` and `cfengine-core-6294` (PR #156,
merged). Both were done as one-file task workspaces under
`~/src/ops-worktrees/`, squash-merged after a provenance check
(`git log`/`git diff` against `origin/master`), then removed per the
ops-worktrees cleanup convention — no leftover workspaces.

**Left over from `4830`, unchanged:** `sudo-secretspec` manifest drift,
handed to the stayturgid agent, explicitly not tendcf's problem. Schema
reconciliation pass still deferred (see Where We're Going).

## What We Tried

1. **Considered filing PR1/PR2 as GitHub issues, same as libntech.**
   Checked `cfengine/core`'s repo settings directly (`gh api repos/cfengine/core
   -q '{has_issues,has_discussions}'`): `has_issues: false`. GitHub Issues
   are disabled on that repo entirely — not a preference, a hard API fact.
   No issue-substitute route exists there. Discussions are enabled
   (`has_discussions: true`) but weren't used — not the right venue for a
   bug-fix PR.

2. **Verified libntech's issue route actually works before relying on
   it.** Pulled the two most recent real (non-PR) issues on
   `NorthernTechHQ/libntech` (#166, #159) and read their comment threads.
   Maintainer `olehermanse` responded to both, and on #159 linked a Jira
   ticket (`CFE-3798`) they created themselves in response to the GitHub
   issue. This is precedent, not speculation — filing #290 mirrors an
   established pattern, not a novel workaround.

3. **Chased whether `libntech` is even the "real" CFEngine repo**, since
   cfengine.com only links `github.com/cfengine` and libntech lives under
   `github.com/NorthernTechHQ`. Confirmed via `cfengine/core`'s own
   `.gitmodules`: it pulls `libntech` from that exact NorthernTechHQ URL as
   a submodule. Also `libntech`'s own commit log already cites `CFE-3629`.
   Not a stray fork — one hop removed from the org the marketing site
   links, nothing more.

4. **Confirmed the Atlassian site itself isn't down**, since the operator's
   framing shifted mid-session from "site is broken" to the more precise
   "login system is broken — says logged in, but every write acts logged
   out." Checked `tracker.mender.io/browse/CFE-3798` (a vanity redirect
   CFEngine uses) resolves fine to `northerntech.atlassian.net`, and the
   site root responds normally. The break is scoped to write-auth on the
   operator's account, not a service outage — consistent with `4830`'s
   401-on-`/rest/api/3/myself` finding, now confirmed to also affect the
   web UI's actual actions, not just the API.

5. **`echo`-wrapping a `gh pr create -R cfengine/core ...` command to just
   display it for the operator still tripped `upstream_review_gate.sh`.**
   The gate does raw-text scanning of the full bash command string, not
   execution-path analysis — it doesn't distinguish "run this" from "print
   this string." Worked around by presenting the commands as plain
   markdown code blocks instead of Bash-tool calls, which the operator
   then ran themselves with `!`. Not a bug worth fixing (the gate still
   did its job — surfaced the exact string for review — just via a
   clumsier UX than necessary), but worth knowing if it recurs.

## Key Decisions

**Ticketless for PR1/PR2, not just PR3** (operator decision, this
session). `4830` treated ticketless as PR3's fallback-of-last-resort;
this session extended it to all three once Jira's write-auth was
confirmed broken on both API and UI, not just flaky. CONTRIBUTING.md's
own Changelog section states `Changelog` and `Ticket` entries "must be in
a *commit message*" and that changelog entries "should also include a
reference to a ticket" — i.e. they're a pair, not independent. Amending
kept `Changelog: Title` bundled with `Ticket: CFE-XXXX` and dropped both
together, not just the ticket line.

**PR3 stays on the fork-PR-plus-tracked-issue holding pattern, not
ticketless-upstream yet.** Not explicitly re-litigated this session —
inherited from `4830` and not contradicted by anything new. Worth the
operator revisiting: since PR1/PR2 shipped ticketless, is there still a
reason PR3 should wait for a ticket via #290 rather than also just
opening the upstream PR now? Flagged as the top item below rather than
decided unilaterally, since `4830` treated "file a real ticket" as a
deliberate 3-option operator choice for this specific PR.

**Track PRs the same way as the issue, via the existing Telegram
matrix**, rather than building anything new — `track-issue-activity.yml`
polls via `gh api repos/.../issues/{number}`, and GitHub's issues API
returns PR data too (has a `pull_request` key), so no format change was
needed, just more matrix entries.

## Evidence & Data

- `gh api repos/cfengine/core -q '{has_issues,has_discussions}'` →
  `{"has_issues":false,"has_discussions":true}`.
- `gh api repos/NorthernTechHQ/libntech -q '{has_issues}'` → `true`;
  scanning its issues history found only 3 real (non-PR) issues among the
  last ~289 issue-endpoint entries, but both bug reports among those 3 got
  a same-day maintainer response and a linked Jira ticket.
- `curl -s https://raw.githubusercontent.com/cfengine/core/master/.gitmodules`
  confirms `libntech` submodule URL is `https://github.com/NorthernTechHQ/libntech`.
- Commit amend diff for both PR1/PR2: only the trailing
  `Changelog: Title` / `Ticket: CFE-XXXX` lines (plus the blank line
  before them) removed; commit bodies otherwise byte-identical. Old SHAs
  `5dbd295f6afc9fc5d49a594950fa1fb2c593524f` (PR1) and
  `071f85987c67b4534290ba212919794272ef090a` (PR2) are now orphaned —
  only referenced in `4830` and this doc, not in any open PR.
- Site-djbclark PRs: `#155` (libntech-290 matrix entry, merged
  `2026-08-16T00:20:19Z`), `#156` (cfengine-core-6293/6294 matrix entries,
  merged `2026-08-16T00:32:23Z`). Both squash-merged, both task workspaces
  removed (`~/src/ops-worktrees/track-libntech-issue-290`,
  `~/src/ops-worktrees/track-cfengine-core-prs` — neither exists anymore).

## Operator Feedback

- **"The site is just clearly broken."** → then, on being asked to be more
  specific: **"it is not that the site is down, it is that the login
  system is broken, it says you are logged in but when you try to do
  anything it says you are not logged in."** Correction worth preserving:
  don't accept "X is broken" at face value when it's actionable to ask
  which specific behavior failed — the more precise report changed how
  the write-up characterizes the blocker (auth/session bug, not outage).
- **"Can we just do an issue in the cfengine repo that links to the code?
  Then they can deal with getting it to the right place."** — the
  instinct behind PR3's #290. Correct in spirit; the actual repo with
  issues enabled is `libntech`, not `cfengine/core` (issues disabled
  there), which is why PR1/PR2 took a different route (ticketless PR, not
  an issue).
- **"Didn't we just do 1? Can we just do PR1 and PR2 against github as
  well?"** — read as "extend the same treatment," confirmed and executed
  as described above.
- **"Keep in mind we need to force the upcoming fable 5 run to use the
  djbclark@gmail.com account."** — not yet acted on (the schema
  reconciliation pass that would need it is still deferred), but saved to
  this session's memory (`project_fable5_account_routing.md`) since
  `cswap list` shows no Fable quota line under the mit.edu account this
  session runs as.
- **"yes merge then handoff"** — standard close-out pattern this session:
  review diff, merge, clean up workspace, no separate confirmation needed
  once a PR's content was already approved.

## Where We're Going

1. **THE NEXT ACTION is an operator decision, not a mechanical step:**
   now that PR1/PR2 are ticketless-and-open, should PR3's upstream PR
   also go ticketless now (open `NorthernTechHQ/libntech` PR directly,
   dropping the wait on `#290` yielding a ticket number), or keep waiting?
   Nothing technical blocks either choice — the fork PR (`djbclark/libntech#1`)
   and commit `da7d3d9` are ready either way; going ticketless just means
   amending out `Changelog:`/`Ticket:` the same way PR1/PR2 were.
2. **Schema reconciliation pass** (deferred twice now — first past a
   dead session timer, still not started): synthesize
   `docs/architecture/goal-file-schema-opinion-*.md` into a new doc, never
   editing the three opinion files. Needs Claude Fable 5 (`fable-deep`
   agent) at xhigh effort, and per the saved memory note, that must run
   under the **djbclark@gmail.com** cswap account (slot 2) — check
   `cswap list` for which account/session is actually invoking it before
   launching, since `cswap switch` only takes effect for new sessions.
3. **Batched doc cleanup**, three items, all in `tendcf`: de-stale
   `docs/paper/tendcf-architecture-paper.md` capability vocabulary
   (~line 311) and open question 8.8; fix the guide's §16
   `host_specific.json` example (its top-level `data` key is silently
   skipped by the parser); fix the guide's false claim that YAML is a
   valid Augments input.
4. **Optional:** the `-D`/`--dump-header` false positive in
   `~/.claude/hooks/upstream_review_gate.sh` noted in `4830`, still
   unfixed; this session surfaced a second, milder rough edge in the same
   hook (blocks `gh ... -R <repo>` text even inside an inert `echo`) —
   arguably correct behavior, not clearly a bug, but worth deciding either
   way if it comes up again.

**Traps, unchanged and still live:**

- `cfengine-core`'s `git status` still shows ` M libntech` — do not
  commit it, all three PRs are independent.
- If PR3 goes ticketless later, remember to also check whether `#290`
  should be closed/referenced from the new PR, so the issue doesn't sit
  open indefinitely once superseded.

## Quick Start

```sh
# Tier 1 pointer
~/.claude/hooks/handoff-tools/.venv/bin/python \
  ~/.claude/hooks/handoff-tools/session_log.py read \
  --state-root ~/.local/state/handoffs --dir ~/.local/state/handoffs/tendcf/main

# The three PRs / issue, for status
gh pr view 1 -R djbclark/libntech
gh issue view 290 -R NorthernTechHQ/libntech
gh pr view 6293 -R cfengine/core
gh pr view 6294 -R cfengine/core

# If going ticketless for PR3 too (mirrors what PR1/PR2 already did):
cd ~/src/cfengine-core/libntech
git log -1 --format=%B silent-digest-failure   # confirm current trailer
# strip Changelog:/Ticket: lines the same way, then:
git push --force-with-lease fork silent-digest-failure
# open the upstream PR — this trips the gate, surface the command for the operator

# Telegram tracking matrix, for reference
grep -A2 -B2 "cfengine/core\|libntech" ~/ops/site-djbclark/.github/workflows/track-issue-activity.yml

# The reconciliation inputs (still the deferred job)
cd ~/src/tendcf && ls docs/architecture/goal-file-schema-opinion-*.md
cat memory/project_fable5_account_routing.md 2>/dev/null || \
  cat /Users/djbclark/.claude-swap-backup/sessions/1-djbclark_mit.edu/projects/-Users-djbclark-src-tendcf/*/memory/project_fable5_account_routing.md
```
