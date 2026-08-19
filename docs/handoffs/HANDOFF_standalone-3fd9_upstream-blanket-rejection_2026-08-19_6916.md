---
schema_version: 1
handoff_id: 6916
parent_handoff_ids: [5c31]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 14d1b16b970ae7f4537c554fcee8b4809e91c58a
created_at: 2026-08-19T11:15:00-0400
writer: claude-code
---

# Handoff — Upstream closed everything: 26 PRs, 26 tickets, restart at one

## The Goal

The session opened as a routine `/baton` resume of chain `standalone-3fd9`
from handoff `5c31`. The inherited plan was: decide where the paper and
guide get published, watch `cfengine/core#6308`, and optionally run a
review panel on the new material.

That plan is obsolete. Checking the one live watch item surfaced a
blanket upstream rejection of the entire contribution effort. The real
work of this session became establishing exactly what upstream did, with
evidence, so the next session starts from fact rather than from the
now-wrong figures in the paper, guide, and register.

**No upstream action was taken and none should be until the operator
decides the restart shape** — see Operator Feedback.

## Where We Are

Git state at handoff time (before the commit carrying this file):

- Branch `master`, `head_sha 14d1b16b970ae7f4537c554fcee8b4809e91c58a`,
  in sync with `origin/master`.
- **Working tree clean.** `git diff --stat` empty, `git status -s` empty.
- No files were modified this session prior to this handoff. No tests run.

The repository is untouched. Everything below is a finding about
external state.

### What upstream did, 2026-08-19 (all times UTC)

| Time | Event |
|---|---|
| 10:42:09 | olehermanse posts the rejection comment on `cfengine/core#6293` (`issuecomment-5340989869`) and closes it |
| 10:42–10:44 | **All 20 `cfengine/core` PRs closed by olehermanse** — #6293, #6294, #6299, #6300, #6302, #6305, #6307–#6320 |
| 12:47–12:50 | `CFE-4715`–`CFE-4729` moved to status **Rejected** |
| 14:10–14:12 | **All 6 `NorthernTechHQ/libntech` PRs closed** — #291, #293, #294, #296, #297, #298 |
| 14:11 | olehermanse comments on `libntech#293` pointing at the same core#6293 comment |
| 16:03–16:09 | `CFE-4730`–`CFE-4740` moved to status **Rejected** |

**Totals: 26 PRs closed, 26 Jira tickets rejected. Nothing of ours is
open upstream.**

### The rejection message (core#6293, `issuecomment-5340989869`)

Quoted rather than paraphrased, because the next session will need to
answer it precisely:

- He counts "20 PRs, 15 tickets, along with some stuff on email and
  GitHub Discussions" and says "the volume is too much" for the humans
  reviewing it.
- "I am going to reject all your PRs and tickets, and ask that you start
  small, with **1 bug report ticket and 1 PR fixing the bug**."
- Requirements for that one submission: "small, isolated changes, with
  short and accurate descriptions"; the ticket must say "how one
  encounters the bug (reproduces it)"; the PR must "show before and
  after with some output of your testing (terminal output or
  screenshots)". Lead with "the smallest bug fix you have which is easy
  to explain / review."
- Then: "wait for our review and feedback so you can incorporate it into
  your future work." Cadence going forward is one cherry-picked change
  at a time, "maybe a few in parallel in the future."
- He quotes the CONTRIBUTING AI policy and states the expectation
  directly: "we expect **@djbclark, the human, not the LLM**, to be in
  the loop for each PR, reviewing it and ensuring what you are
  submitting makes sense."
- He is explicit that working on the fork in parallel is fine — the
  constraint is on what gets *sent* upstream, not on what gets built.

He read the project: the comment links `frdminc/tendcf` and calls it
"sounds interesting!" This is a process complaint about volume and
review burden, not a rejection of the technical content. No PR was
closed with a "this is wrong" rationale; the Jira resolutions bear this
out (see below).

### Jira disposition detail

All 26 of `CFE-4715`–`CFE-4740` are status **Rejected**. The resolution
field splits, and the split is informative:

- `CFE-4715`, `CFE-4716` → resolution **"Won't Do"**. These are the two
  `--simulate` *feature* tickets (keep-chroot, JSON change set).
- The other 24 → resolution **"Done"**.

Do not over-read "Done" as acceptance — the status is Rejected on all of
them and the two channels closed within hours of each other. But the
Won't Do / Done split does line up exactly with feature-vs-defect, which
is at minimum consistent with the defects being considered real.

## What We Tried

Chronological, with why each failed. These are the expensive
rediscoveries.

1. **Anonymous Jira REST against `cfengine.atlassian.net` → HTTP 404.**
   The register (`docs/architecture/upstream-register.md:17`) documents
   anonymous `GET` of `CFE-4715` returning 200 as of 2026-08-17, so 404
   read as "our tickets were deleted."

2. **Authenticated retry with the brokered token → also 404.** Same host,
   valid 192-char `ATLASSIAN_CFENGINE_API_TOKEN` via
   `sudo-secretspec run`, Basic auth as `djbclark@gmail.com`. Still 404.
   Atlassian masks 403 as 404, so this still read as a permissions
   revocation.

3. **Control test on tickets that certainly exist and are certainly not
   ours — `CFE-3000`, `CFE-4000`, `CFE-4700`, `CFE-4714`.** All 404 too.
   That killed the permissions theory: it was not per-ticket masking.

4. **`GET /rest/api/2/myself` → 404**, and `https://cfengine.atlassian.net/`
   itself → 404 serving Atlassian's "Page Unavailable" notification page.
   The whole host is dead, not the project.

   **Resolution:** `https://tracker.mender.io/rest/api/2/issue/CFE-4715`
   returns 200 and redirects to **`northerntech.atlassian.net`**. That is
   the live host. Anonymous GET works there with no token at all.
   **The register's documented Jira base URL is stale and will send the
   next session down this same 45-minute path.**

5. **`gh pr list --state all` reported all 6 libntech PRs as `OPEN`**
   when they had already been closed ~50 minutes earlier. `gh pr list`
   goes through GitHub's search index, which lags. This produced a wrong
   statement to the operator mid-session ("the 6 libntech PRs are still
   open — different repo, apparently not swept"), corrected only when a
   per-PR query returned `closedAt` timestamps of 14:10–14:12Z.
   **Trust `gh pr view <n>` / `gh api .../timeline` for state; treat
   `gh pr list` state as advisory.**

## Key Decisions

**Chosen: stop and hand back rather than act upstream.** The maintainer
asked, in writing, for the human and not the LLM to be in the loop for
each PR. An agent immediately posting a reply, opening the replacement
ticket, or re-filing anything would violate the specific thing being
asked for, on the same day it was asked. Nothing was posted, filed,
replied to, or emailed this session.

*Rejected:* drafting and sending a short apology/acknowledgement reply
on core#6293. Tempting, and it would be polite, but it is one more
notification in the exact inbox he just said is over capacity, and it
would be LLM-authored contact after a request for human contact.

*Rejected:* immediately preparing the "one small bug" submission so it
is ready to go. Which bug leads is a judgment call with real
consequences for how the restart is received, and it is the operator's
to make — see Where We're Going item 1.

**Chosen: verify the ticket disposition even though it cost four failed
attempts.** "Were the tickets rejected too, or only the PRs?" changes
the shape of the restart, and leaving it as an open question would have
handed the next session a 45-minute host-hunt with no warning.

**Deferred, not decided:** the standing memories
`upstream-fix-everything-policy` ("fix every upstream bug we find — fork
branch + fork issue/PR + email") and `when-in-doubt-open-pr-or-issue`
("standing order") now conflict directly with an explicit maintainer
instruction. They should be corrected once the operator sets the new
policy — but rewriting the operator's own standing orders unilaterally,
on the strength of one upstream comment, is not an agent's call.

## Evidence & Data

Every figure here was re-derived live this session, not restated.

- **26 PRs closed.** `gh pr list --repo cfengine/core --author djbclark
  --state closed` → 20, all `closedAt` 2026-08-19T10:42.
  `NorthernTechHQ/libntech` → 6, `closedAt` 14:10:22–14:12:01Z.
- **Closed by olehermanse**, confirmed via
  `gh api repos/cfengine/core/issues/6308/timeline` → `{"by":
  "olehermanse", "at": "2026-08-19T10:44:49Z"}` and the same for #6293 at
  10:42:09Z.
- **26 tickets Rejected**, `CFE-4715`–`CFE-4740`, fetched anonymously
  from `northerntech.atlassian.net`. Two `Won't Do` (4715, 4716), 24
  `Done`.
- **Rejection comment**: `cfengine/core` issue comment id
  `5340989869`, authored 2026-08-19T10:42:09Z. Mirrored to Jira as a
  comment on CFE-4732 by "Ole Herman S. Elgesem" at 16:08.
- **Live Jira host**: `northerntech.atlassian.net`.
  `cfengine.atlassian.net` returns 404 sitewide including `/`.
  `tracker.mender.io` redirects correctly.
- **Our last upstream words**, both now unanswered and both from before
  the rejection: PR #6308 `issuecomment-5336528513` and CFE-4732 comment
  at 03:51Z — the correction retracting our own wrong untestability
  reason. Worth knowing the last thing he saw from us was us correcting
  our own error unprompted.

### Figures in our docs that are now false

Not yet fixed — no file was edited this session.

- **`docs/paper/tendcf-architecture-paper.md:1490`** (§7.1 "What we
  found") and **`docs/paper/tendcf-architecture-guide.md:1267`** both
  open with "As of 2026-08-18 [we have / there are] **twenty-six pull
  requests open** against `cfengine/core` (twenty) and
  `NorthernTechHQ/libntech` (six), tracked as `CFE-4715`–`CFE-4740`".
  Open PR count is now **0** and all 26 tickets are Rejected.
  **Grep warning: the numbers are spelled out as words.** `grep "26 open"`
  finds nothing; use `grep -i "twenty-six"`.
- The same two passages continue "**Twenty-two of the twenty-three defect
  fixes ship a test.**" That figure is still *true about the work* and
  should not be deleted — but "pull requests open" is now the wrong
  denominator to carry it, and the surrounding paragraph about the one
  unclosable exception is written in the present tense of an open PR.
- `docs/architecture/upstream-register.md:896` and `:992` carry the
  "22 of 23" figure in digits; those lines are about the audit itself and
  are still accurate, but the register has no record of the closure.
- `docs/architecture/upstream-register.md:17` states the CFE Jira is
  "**WORKING as of 2026-08-17, and now the ONLY filing channel**" with
  `cfengine.atlassian.net` implied as the base. Host is wrong (see What
  We Tried #4) and "working channel" now needs the volume constraint
  attached.
- Both paper and guide still carry "Draft, circulated for comment. Not
  submitted for publication." That banner is still accurate — nothing
  was ever published or sent.

## Operator Feedback

From this session, verbatim in substance: the operator ran `/baton` and
then `/handoff`, and gave **no direction on the upstream situation**. The
four questions put to them at the end of the resume briefing are all
still open. Nothing in this document should be read as the operator
having chosen anything.

Inherited from `5c31` and still open:

- Where the two documents get published. Operator decision, not a
  research task.
- Strike or keep the Narayan Desai acknowledgement in
  `docs/paper/tendcf-architecture-paper.md`. The "Prepared for"
  dedication was already removed; the acknowledgement was kept as
  scholarly credit for the Bcfg2 papers §6 builds on.

Standing preferences that bear on the restart, from memory:
`be-terse-upstream-asked` (a real reviewer already said our output is
too long — this is now the second, louder version of that same
feedback), `upstream-cfengine-commit-style`, and
`upstream-email-wait-for-full-panel`.

## Where We're Going

1. **THE next action — operator decides the restart shape.** Two
   questions, both blocking, neither answerable by an agent:
   (a) **Which single bug leads?** It must be the smallest and easiest
   to explain, with a clean reproduction and before/after terminal
   output. Strong candidates from the closed set, all defects with tests
   already written: `CFE-4736` (short option strings disagree with their
   long options — trivially explained, trivially shown),
   `CFE-4719`/`CFE-4720` (CMDB error reporting / one bad key dropping a
   section — very visible user-facing symptom, easy repro).
   `CFE-4732` is the *worst* candidate: we already established it has no
   observable difference and told him so.
   (b) **Who sends it?** He asked for djbclark the human in the loop per
   the AI policy. Decide whether an agent may prepare material for human
   review and sending, or whether it stays entirely hands-off.
   **Until (a) and (b) are answered, send nothing upstream.**

2. **Correct the now-false figures in our own docs.** Independent of the
   upstream decision; safe to do immediately. `docs/paper/`
   (paper §7.1 and guide §19) and `docs/architecture/upstream-register.md`
   all quote "26 open PRs" — now 0 — and the register's Jira host is
   dead. Add the disposition table from this handoff to the register so
   the record shows what happened, not just what we filed.

3. **Fix the register's Jira base URL.** `cfengine.atlassian.net` →
   `northerntech.atlassian.net`. Note that anonymous `GET` works there
   with no token, which makes most future status checks cheaper than the
   brokered-token path the register currently prescribes.

4. **Correct the two conflicting standing memories** once the operator
   rules: `upstream-fix-everything-policy` and
   `when-in-doubt-open-pr-or-issue` both instruct behavior the
   maintainer has now explicitly asked us to stop. Do not edit these
   before item 1 is answered.

5. **Still open from `5c31`, unchanged by any of this:** publication
   venue for the two documents; the Narayan Desai acknowledgement; and
   the optional review panel scoped to the new material only (paper §7
   and §1.1 trust/consent bullets, guide §19 and §16.C) — 13 review
   files already cover the rest. Read-only copy per
   `reviewer-clis-edit-the-tree`, pin models per
   `reviewer-seats-model-check`.

## Quick Start

```bash
cd /Users/djbclark/src/tendcf
git log --oneline -3          # expect 14d1b16 + this handoff commit
git status -s                 # expect clean

# Read the rejection in full — this is the whole context:
gh api repos/cfengine/core/issues/comments/5340989869 -q .body

# Confirm nothing of ours is open upstream (per-PR, NOT `gh pr list` —
# its search index lags and reported CLOSED PRs as OPEN this session):
gh pr list --repo cfengine/core --author djbclark --state open --json number -q length          # expect 0
gh pr list --repo NorthernTechHQ/libntech --author djbclark --state open --json number -q length # expect 0

# Jira: LIVE host is northerntech.atlassian.net. cfengine.atlassian.net
# 404s sitewide. Anonymous GET works — no token needed:
curl -s "https://northerntech.atlassian.net/rest/api/2/issue/CFE-4736?fields=status,resolution,summary" \
  | python3 -m json.tool

# Only if a write is needed (read does not require this):
#   TOKEN=$(sudo-secretspec run --reason '<why>' -- bash -c 'echo $ATLASSIAN_CFENGINE_API_TOKEN')
#   curl -u "djbclark@gmail.com:$TOKEN" https://northerntech.atlassian.net/rest/api/2/...

# Lints, if touching docs (uv run, never python3, per the register):
uv run bin/schema_lint.py
uv run bin/xref_lint.py
```

Parent handoff: `docs/handoffs/HANDOFF_standalone-3fd9_paper-destale-for-comment_2026-08-18_5c31.md`
