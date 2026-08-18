---
schema_version: 1
handoff_id: 7771
parent_handoff_ids: [be6d]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: bfe2d70b648a0ea6fde7015b2e9da1c164110e2e
created_at: 2026-08-18T17:33:00-0400
writer: claude-code
---

# Handoff — B-21/CFE-4739 shipped (def.json null crash + inputs truncation)

## The Goal

Ship B-21/CFE-4739, the queued next action from the parent handoff (be6d):
the augments (`def.json`) loader in `libpromises/generic_agent.c` has the
same JSON-null-crashes-cf-promises root cause that B-20/CFE-4738 already
fixed in `cmdb.c` (`host_specific.json`), at three sites: `vars` scalar,
`variables` bare-scalar, `classes` scalar.

## Where We Are

**Done, end to end.** PR [cfengine/core#6319](https://github.com/cfengine/core/pull/6319)
open, Jira [CFE-4739](https://northerntech.atlassian.net/browse/CFE-4739)
comment 159449 posted. Register row updated (`docs/architecture/upstream-register.md`
B-21, commit `bfe2d70`). tendcf `master` is clean at `bfe2d70`.

Fix worktree: `/Users/djbclark/src/core-defnull`, branch `fix/def-json-null-crash`,
commit `dd917f09d`, cut from upstream `a0bca6aaf`. Pushed to
`djbclark/core` as `origin/fix/def-json-null-crash`.

## What We Tried

1. **Scoped the fix from the handoff note's three sites, then found two more.**
   Read `libpromises/generic_agent.c` end to end (`LoadAugmentsData()`) and
   `libntech/libutils/json.c` to verify each claim before trusting it:
   - `JsonArrayContainsOnlyPrimitives()` treats a JSON null as a primitive
     (confirmed in `json.c:1599-1617`), so the `vars`/`variables` array
     paths (not just the three scalar sites) reach `RlistFromContainer()`.
   - `RlistFromContainer()` → `RlistAppendContainerPrimitive()` has a
     `JSON_PRIMITIVE_TYPE_NULL: break;` case (`rlist.c:1745-1746`) — no
     crash, but the installed list is silently shorter than the source
     array. Same defect class B-20 already fixed in `cmdb.c`, so fixed it
     here too for parity (2 extra sites: `vars` array, `variables` array).
   - Confirmed the three `skip_null=true` array paths (classes array,
     class_expressions/regular_expressions, further-augments-files) are
     genuinely already safe by reading `JsonIteratorNextValueByType()`
     itself (`json.c:677-695`) — it skips `JSON_TYPE_NULL` before the type
     filter ever runs.
2. **Wrote and ran an acceptance test that failed on the first try** —
   not because the fix was wrong, but because the test's expected regex
   assumed errors only show up in the section's own `--show-X` command.
   Wrong: `Log()` output goes to stdout on every `cf-promises` invocation
   regardless of `--show-vars` vs `--show-classes`, so both commands see
   all five error lines. Also assumed `good_vars` before `good_variables`
   in `--show-vars` output; actual order is `SeqSort()`'d, so
   `good_variables` sorts first. Fixed the regex to match observed output,
   not assumed output.
3. **Grok's panel review surfaced a sixth site mid-review**: the `"inputs"`
   array (`generic_agent.c` ~line 909, pre-fix) has the identical
   `RlistFromContainer()` truncation defect. Not a crash, and grok
   explicitly said "would not block the ticket on it" — but folded it into
   the same commit anyway for parity with B-20's own scope decision
   (B-20 bundled scalar-crash + array-truncation fixes in one commit
   rather than splitting further). Extended the test to cover it.
4. **Panel review, twice, on gemini's seat.** First attempt: gemini
   responded conversationally asking me to paste file contents instead of
   reading them from its own cwd — its `--dangerously-skip-permissions`
   run didn't proactively read files without an explicit instruction.
   Retried with an explicit "read these files from your cwd" instruction;
   that run failed differently, with gemini reporting its sandbox
   couldn't see the filesystem at all (`/Users/djbclark/.gemini/antigravity-cli`
   protected, scratch folder reported empty) — an environment/sandbox
   issue in **this** session, not a code problem. Did not retry a third
   time; shipped on grok's single-seat SHIP verdict per
   [[panel-reviewer-weighting]] (grok's trap-control — a full
   allocate/free table per new code path — was already the deeper seat in
   prior B-series panels even when gemini worked).

## Key Decisions

- **Bundled the `inputs` array fix into B-21/CFE-4739 rather than filing a
  separate ticket.** Same file, same root cause class, same commit as the
  two sites already being touched for the identical defect; matches how
  B-20 itself bundled scalar+array fixes into one CFE-4738 commit instead
  of splitting further. Rejected: a separate CFE-#### ticket (the CFE-4738/
  CFE-4739 split pattern) — that split was for a genuinely different
  crash-vs-no-crash class in a different file; this is the *same* class
  already in scope for this file.
- **Panel is single-seat (grok only) for this PR.** Rejected: retrying
  gemini a third time or blocking the ship on a second opinion — two
  failures were an environment problem local to this session (sandbox
  couldn't see the filesystem), not a signal to keep retrying, and grok's
  review already included a memory-leak table checked against every new
  early-return path plus an independent search for missed crash sites.
- **Jira posting used `sudo-secretspec` + direct `curl`, not Composio.**
  I initially assumed the CFE-4739 comment channel was Composio (no active
  Jira connection existed under this session's Composio identity,
  `djbclark@gmail.com`) and asked the operator how to proceed. Operator
  corrected: it was always the `ATLASSIAN_CFENGINE_API_TOKEN` secret via
  `sudo-secretspec run`, straight to the Jira REST API — which is also
  what the [[upstream-channel-is-jira]] memory already said. The mistake
  was not checking that memory before defaulting to Composio; no memory
  update was needed since the stored guidance was already correct.

## Evidence & Data

- **Discrimination, proved by hand, not asserted.** Unpatched rebuild
  (`git stash` the fix, `touch generic_agent.c`, `make -C libpromises &&
  make -C cf-promises && make -C cf-agent` to force the full relink —
  the [[libpromises-edit-needs-library-rebuild]] trap): running
  `cf-promises --show-vars` against the new test's `def.json` gave a real
  `Segmentation fault: 11`, `rc=139`. Patched rebuild: the same command
  produces the five (later six) expected error lines and installs every
  surviving `good_*`/`test_class_*` entry; `testall --gainroot=fakeroot`
  reports the new test **Pass** and all 21 pre-existing tests in
  `tests/acceptance/00_basics/def.json/` also **Pass** — zero regressions,
  22/22 total.
- Test workdir discipline followed: fresh `BASE_WORKDIR` per run (per
  [[acceptance-test-root-and-workdir]]), `--gainroot=fakeroot` passed to
  `testall` itself (not `fakeroot testall ...`, which double-wraps and
  produces "nested operation not yet supported").
- Panel copies made with `cp -a` to `$SCRATCHPAD/panel-grok` and
  `panel-gemini`, never the build tree; `git status --short` on the real
  `core-defnull` worktree confirmed clean (no seat edited it) before
  committing.
- Jira comment 159449 on CFE-4739, issue id 107681 (HTTP 201 from the
  REST call).

## Operator Feedback

- Corrected the Jira-posting-channel assumption above (Composio → actually
  `sudo-secretspec` direct API) — recorded under Key Decisions, no new
  memory needed since [[upstream-channel-is-jira]] already had it right.
- No other corrections this session; the operator's only input was
  "Resume" and the Jira-channel correction.

## Where We're Going

1. **NEXT ACTION: watch for the first maintainer response on any of
   #6307–#6319** (13 open PRs now). `gh pr view <n> -R cfengine/core --json
   comments,reviews,state,statusCheckRollup`. All CI on all 13 is still
   `action_required 0s` pending first-time-contributor workflow approval;
   nothing to do but check periodically. One approval likely unblocks CI
   for all of them at once (shared workflow gate).
2. **B-5b/CFE-4720** (one bad CMDB key drops every variable on the host) —
   the last unstarted item from the original B-series batch. Must stack on
   `fix/cmdb-name-offending-key` (not master): needs CFE-4719's offender
   identification to skip the bad entry, and cutting from master guarantees
   a `cmdb.c` merge conflict with PR #6315.
3. **CFE-4736's two RFC questions still unanswered**: `cf-agent -x` /
   `cf-check -h` declare `optional_argument` with no optarg reader; whether
   `--manpage` should be universal. Ticket open, unassigned, only the
   operator's own comment on it.
4. **4-5 acceptance tests need real root and nothing else gives it**
   (`getgroups`, `getgroupinfo`, `getusers_vararg`, `filestat_xattr`) —
   fakeroot's uid faking is broken by SIP on this machine. Do **not** add a
   NOPASSWD rule (settled: `testall:514` runs a user-writable script as
   root, so it would be `NOPASSWD:ALL` in practice). Raise
   `timestamp_timeout` or run `sudo -v` before a batch instead.
- Delete when their PRs close: `/Users/djbclark/src/core-defnull` (this
  session), `core-cmdbkey`, `core-cmdbnull`, `core-cmdbdotted`,
  `core-evalint`, plus older `core-darwin`, `core-getopt`, `core-jsontest`.
- Quota at session end (from `cswap list` at session start; re-check with
  `cswap list` before starting more work): gmail account 5h window was 20%
  *used* (i.e. 80% left, ~3.5h to reset); mit.edu account 5h was 48% used.
  Fable 93% used on gmail, resets 2026-08-21 — reserve per
  [[fable-deep-always-authorized]], don't default to it.

## Quick Start

```bash
cd /Users/djbclark/src/tendcf
git log --oneline -5              # confirm HEAD is bfe2d70 or later

# Check for maintainer engagement across all 13 open PRs
for n in 6307 6308 6309 6310 6311 6312 6313 6314 6315 6316 6317 6318 6319; do
  gh pr view $n --repo cfengine/core \
    --json number,state,mergeable,reviewDecision,comments,statusCheckRollup \
    -q '"#\(.number) \(.state) mergeable=\(.mergeable) review=\(.reviewDecision // "none") comments=\(.comments|length)"'
done

# Quota first
cswap list

# B-5b: stack on fix/cmdb-name-offending-key, NOT master
cd /Users/djbclark/src/core-cmdbkey && git log --oneline -3
# then branch a new worktree from THIS branch's tip, not upstream/master

# Jira comment recipe (sudo-secretspec, NOT composio)
sudo-secretspec run --reason "<why>" -- bash -c \
  'curl -sS -u "djbclark@gmail.com:$ATLASSIAN_CFENGINE_API_TOKEN" -X POST \
   -H "Content-Type: application/json" --data @body.json \
   "https://northerntech.atlassian.net/rest/api/2/issue/<KEY>/comment"'
```
