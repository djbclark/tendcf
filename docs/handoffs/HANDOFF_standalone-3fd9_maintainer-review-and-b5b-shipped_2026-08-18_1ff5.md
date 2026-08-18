---
schema_version: 1
handoff_id: 1ff5
parent_handoff_ids: [7771]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 9fb55de52f1bb188d585327c19278c59cafa10d9
created_at: 2026-08-18T18:15:49-0400
writer: claude-code
---

# Handoff — First maintainer review handled, B-5b shipped

## The Goal

Continue the CFEngine/libntech upstream-contribution effort (tendcf's
core purpose): find defects, fix them, and get them merged upstream via
`djbclark/core`/`djbclark/libntech` fork branches → PRs against
`cfengine/core`/`NorthernTechHQ/libntech` → Jira (CFE project).

## Where We Are

Resumed from handoff 7771 (B-21 shipped). This session had two pieces of
real work:

1. **First actual maintainer review landed** — nickanderson (MEMBER) on
   PR #6308 (B-15/CFE-4732, nfs.c remount timeout leak):
   `CHANGES_REQUESTED`. Three asks: (a) commit message didn't follow
   cfengine's own style (past-tense subject, no `fix:` prefix,
   `Changelog:`/`Ticket:` trailers), (b) an inline suggestion collapsing
   a 6-line rationale comment to one line at `nfs.c:1476`, (c) a general
   complaint about prose volume ("100 characters of prose per character
   of code") plus new guidance: small PRs for demonstrated user-reported
   bugs land easier than large PRs for self-discovered ones.
   Fixed same session: commit rewritten and amended (`190f869a5` →
   `9dd5eb51c` in `~/src/core-mountleak`, force-pushed), the suggested
   comment applied, PR body cut to defect+fix+why-no-test, replied on
   the PR. #6305 had an *older* comment-density note from nickanderson
   that was already fixed pre-review (`0e06ad3d7`), no action needed
   there.

2. **B-5b/CFE-4720 shipped** — one CMDB entry with an unresolved
   variable reference no longer drops every other entry in its section.
   `CheckCMDBDataForUnexpandedVars()` in `libpromises/cmdb.c`
   (`~/src/core-cmdbkey`) pre-validated a whole `vars`/`variables`/
   `classes` section and aborted the entire section on the first bad
   entry. Refactored into `CheckCMDBEntryForUnexpandedVars()`, called
   per-entry inside each section's own install loop with `continue` on
   failure — matching this file's own pre-existing skip-and-continue
   idiom (already used for a missing `value` field, an invalid variable
   specification, etc.). New branch
   `fix/cmdb-one-bad-entry-skips-only-that-entry` (cut from
   `fix/cmdb-name-offending-key`, i.e. stacked on B-5a's already-open
   PR #6315, not master) — commit `8f0076b81`. PR
   [cfengine/core#6320](https://github.com/cfengine/core/pull/6320)
   opened, Jira CFE-4720 comment 159453, fork issue
   [djbclark/core#9](https://github.com/djbclark/core/issues/9) updated
   with an honest scope note: this only fixes the blast-radius half of
   the original report. The second half — "the agent reports no promise
   failures on a CMDB load error" — is a genuine design question the
   original filing deliberately left open (no patch attached), and
   still is.

Along the way, two new durable memories were saved (auto-memory, not
tendcf):
- `upstream-cfengine-commit-style.md` — the CONTRIBUTING.md commandments
  (commit trailers, title format, one-thing-per-commit, bite-sized-over-
  comprehensive) now confirmed live by an actual maintainer review.
- `be-terse-upstream-asked.md` updated with the second independent
  verbosity complaint and the small-PR guidance.

Register (`docs/architecture/upstream-register.md`) and Tier-1 session
log are both current as of `tendcf@9fb55de`.

## What We Tried

**Writing the B-5b acceptance test took three attempts before it
actually discriminated** — worth recording in detail since it's a real
gap in the test-writing playbook, not a one-off mistake:

1. First draft: two separate `dcs_passif_output()` calls in one
   `methods:` block (one asserting the bad entry is still rejected, one
   asserting the good entry installs). This reported **Pass on both
   patched AND unpatched code** — false positive. Root cause, read
   directly out of `testall`'s source (`testall:619`,
   `grep -E "R: .*$ESCAPED_TEST Pass"`): the harness only checks for the
   *presence* of a matching `Pass` report line, never for the *absence*
   of a `FAIL` line. Two independent checks in one file, one passing one
   failing, print both an `R: ... Pass` and an `R: ... FAIL` line, and
   the harness's first matching branch (`Pass`) wins. This is a real,
   general gotcha for this codebase's acceptance-test style, not
   specific to CMDB.
2. Second draft: combined both conditions into one `"ok" and => {...}"`
   class, called `dcs_passif("ok", $(test))` via `methods:` with no
   `inherit => "true"`. This built and ran, but `dcs_passif` reported
   `ok` as false even when both underlying debug-printed classes were
   true. Did not fully root-cause this (candidate: class visibility
   across the `usebundle` boundary without `inherit`) — abandoned rather
   than chase it further, since a known-good local pattern already
   existed in the same directory.
3. Final version: copied `01-vars.cf`'s proven pattern exactly — direct
   `reports:` promises (`ok::`/`!ok::`) in the same bundle that computed
   the class, no `dcs_passif` indirection. Also needed
   `depends_on => { "prepare_host_specific_data" }` on the `vars:`
   promises that call `execresult()`, matching `01-vars.cf`'s own
   comment ("ensure the sub-agent execution doesn't happen too early") —
   without it, `check`'s vars evaluated before `init`'s file-copy method
   had actually run, so the command saw no `host_specific.json` yet.
   This version discriminates correctly (verified by stashing the
   `cmdb.c` fix, rebuilding, and confirming the isolated test file FAILs
   on unpatched code, then restoring and confirming it PASSes).

Also hit and confirmed: CFEngine's `regcmp()` does a **full anchored
match**, not a substring search — a `--show-vars` line has trailing tag
content (`source=cmdb`) that must be included in the expected regex or
the match silently fails. `05-variables-tag-comment.cf`'s existing
pattern already showed this (it includes trailing tag/comment text) but
it wasn't obvious until reproduced by hand.

## Key Decisions

- **B-5b scoped to only the blast-radius half**, not the "silent
  failure" half. The original fork issue (#9) explicitly filed the
  silent-failure question "for discussion rather than with a patch
  attached" because it's a judgment call about intended behavior, not an
  obvious defect. Rather than guess at a design answer nobody asked for,
  shipped the uncontroversial, idiom-matching half and left a clear note
  that the rest is still open. This also aligns with nickanderson's
  freshly-stated preference for small, single-purpose PRs.
- **New branch/PR for B-5b rather than adding a second commit to the
  already-open #6315** — even though the register said "stack on
  `fix/cmdb-name-offending-key`", that meant build on top of the code,
  not pile a second, differently-ticketed fix into an open PR a
  maintainer hasn't reviewed yet. Branched from `fix/cmdb-name-offending-
  key` locally so the diff builds on B-5a's already-shipped work, but
  opened as its own PR (#6320) with an explicit "stacked on #6315" note
  in the body, since GitHub will show both commits until #6315 merges.
- **No panel review for B-5b** — deliberately skipped, recorded honestly
  in the register (`*skipped*`, with reasoning) rather than silently
  omitted or falsely marked done. Justification: small, mechanical,
  directly extends an idiom this exact file already used and had already
  been reviewed for (B-3/B-5a), with discrimination proven by hand
  instead of by panel.

## Evidence & Data

- `00_basics/06_host_specific_data` acceptance suite: 14/14 pass with
  the B-5b fix (was 13/13 before adding test 16; `ls *.cf | wc -l`
  confirms the count each time, per the acceptance-test-root-and-workdir
  memory's fresh-`BASE_WORKDIR` discipline).
- Discrimination proved twice this session by stash/rebuild/test/restore
  cycles: `libpromises/cmdb.c` (B-5b) and `cf-agent/nfs.c` (the #6308
  comment fix required no re-discrimination, it was a style-only
  change verified by clean rebuild only).
- `#6308` force-pushed commit: `9dd5eb51c` (was `190f869a5`).
- `B-5b` commit: `8f0076b81` on
  `fix/cmdb-one-bad-entry-skips-only-that-entry`.

## Operator Feedback

None explicit this session beyond continuing prior standing orders
([[upstream-fix-everything-policy]], [[when-in-doubt-open-pr-or-issue]],
[[be-terse-upstream-asked]]). The operator approved prioritizing #6308's
fix over starting B-5b via an `AskUserQuestion` at the top of the
session.

## Where We're Going

1. **Watch for further maintainer response** on #6308 (my reply is the
   last comment, nothing new from nickanderson yet as of this handoff)
   and on the brand-new #6320:
   `gh pr list -R cfengine/core --author djbclark --json number,title,state,reviews,comments,statusCheckRollup`
2. CFE-4736 (getopt RFC question) is still open/unassigned upstream —
   no response yet.
3. Delete worktrees once their PRs close:
   `~/src/core-defnull`, `core-cmdbkey`, `core-cmdbnull`,
   `core-cmdbdotted`, `core-evalint`, `core-mountleak`.
4. If upstream ever does weigh in on the B-5b "silent failure" design
   question (via CFE-4720 or issue #9), that's the trigger to revisit
   the second half — not before.
5. Acceptance-test playbook gap: consider writing up the
   `testall`-only-checks-for-Pass-not-absence-of-FAIL discovery
   somewhere durable (register or a memory) if it bites again — it was
   handled inline this session but isn't yet recorded outside this
   handoff.

## Quick Start

```bash
cd /Users/djbclark/src/tendcf && git log --oneline -5
gh pr view 6308 -R cfengine/core --json state,comments,reviews -q '.state, (.comments[-1].author.login + ": " + .comments[-1].body[0:200])'
gh pr view 6320 -R cfengine/core --json state,comments,reviews
cd ~/src/core-cmdbkey && git log --oneline -3
```
