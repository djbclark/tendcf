---
schema_version: 1
handoff_id: 29e5
parent_handoff_ids: [60a2]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 2064cc815c02b3c37699265f934fe9d08f0c0d52
created_at: 2026-08-17T18:11:58-0400
writer: claude-code
---

# Handoff — B-12 upstreamed, two advisories filed, B-2 deliberately deferred

## The Goal

Inherited from `60a2`: B-12 was panel-cleared and ready to offer; the B-2/#6299
merge was blocked on three named changes. `60a2` called B-2 "THE NEXT ACTION".

**This session did not do that, on purpose.** The session opened at 8% of the
5-hour quota window. B-2 needs a Fable subagent writing C in a signal path,
then a full rebuild, six acceptance tests, both discrimination directions and
sha256 restores, then a panel. That work cannot be safely stopped halfway. So
the goal was re-scoped, with the operator, to *everything else that was ready
and fits in a text-only budget*: offer B-12, file the two deferred advisory
defects, correct the register.

## Where We Are

`tendcf` master at `2064cc8`, clean tree, pushed.

**Done this session:**

| Item | Result |
|---|---|
| B-12 / CFE-4723 | **Offered upstream** as [cfengine/core#6302](https://github.com/cfengine/core/pull/6302) |
| B-15 / new | Filed [CFE-4732](https://northerntech.atlassian.net/browse/CFE-4732) |
| B-16 / new | Filed [CFE-4733](https://northerntech.atlassian.net/browse/CFE-4733) |
| Register | `2064cc8` — B-12 row corrected, B-15/B-16 rows added |
| Housekeeping | `libntech-b4`, `libntech-jsonstr` worktrees removed |

**Not done, still the next action:** B-2's three required changes.

**Files changed in this repo this session:** `docs/architecture/upstream-register.md`
(commit `2064cc8`) and this handoff. Nothing else — no source file in any core or
libntech worktree was touched. `core-b12`'s tree is byte-identical to what `60a2`
left; the commit offered as #6302 was already there.

**Tests run this session: none.** Deliberate — B-12's build, discrimination run
and sha256 restore were done and recorded last session (numbers reproduced under
Evidence below), and nothing was recompiled here. Everything this session did was
text: a PR body, three Jira writes, two GitHub comments, a register edit, and two
worktree removals. The only executions were `git`, `gh`, `curl` and `cswap`.

**Five PRs open upstream, none reviewed.** As of 2026-08-17 18:30, #6293,
#6294, #6299, #6300, #6302 are all `OPEN`, all `MERGEABLE`, all checks
`SUCCESS`, all `reviewDecision` empty. Every comment on #6293 (5) and #6294
(7) is ours. **No maintainer has responded to anything in this series yet.**
That is the single most important piece of external state, and it is not a
problem to fix — it is a fact to keep checking.

## What We Tried

1. **Read cswap backwards at session start.** The SessionStart hook reported
   `5h: 91%`. I stated a resume plan asserting there was plenty of headroom
   and proposing to spawn `fable-deep` on B-2 immediately. **The percentages
   are CONSUMED, not remaining** — there was 9% left, not 91%. The operator
   caught it ("We only have 8% tokens left"). Had this not been caught, the
   session would have started B-2 and died mid-verification, which is the
   worst possible stopping point for it. Memory `quota-check-use-cswap-not-aiuse`
   updated with an explicit "restate them as 'X% left'" rule.

2. **Copying fable's line numbers into the Jira filings.** Started to, stopped
   and re-derived them from `upstream/master` instead. fable's review said
   `nfs.c:1434` and `:1459`; on current master `22ce89322` the `SetTimeOut()`
   calls are at **`:1436` and `:1461`**. Master had moved since the review.
   This is the same failure as CFE-4731, where line numbers were read off a
   fixed branch instead of master and had to be corrected on the ticket after
   filing. Caught pre-publication this time.

3. **`session_log.py write` rejected the payload twice.** First `blockers`
   must be a list of strings, not a semicolon-joined string. Then it failed
   with `No such file or directory: /Users/djbclark/src/libntech-jsonstr` —
   the writer stats every `workspaces` entry, and I had just removed that
   worktree. Filter `workspaces` by `os.path.isdir()` before writing after any
   worktree removal.

4. **`git worktree remove` on `core-p1` / `core-p2` failed outright**:
   `fatal: working trees containing submodules cannot be moved or removed`.
   Both carry the libntech submodule. Handoff `60a2` item 8 listed them as
   routine cleanup alongside the two libntech worktrees; they are not the same
   operation. Needs a submodule deinit or `--force`. Not attempted — out of
   scope for the remaining budget, and not worth a forced delete unasked.

## Key Decisions

**Deferred B-2 rather than starting it.** Chosen because its verification is
indivisible. Rejected alternative: start the fable-deep run and let the next
session pick up the verification — rejected because a half-verified signal-path
patch sitting in a worktree is exactly the state that produces false confidence
later. The register and Tier 1 log now both say why it was skipped, so the next
session does not read the gap as neglect.

**Wrote #6302's body at roughly a third the length of #6300's.** A CFEngine
upstream dev asked, via the operator: *"see if you can get your llm to be a bit
more conservative on volume of words :)"*. #6300's body — sections for What
this does not fix, Measurement, The change, Things to push back on, Tests,
Notes — is the most likely proximate cause. #6302 keeps the substance (both
required caveats, the discrimination evidence, the platform disclosure) and
drops the elaboration. Rejected alternative: keep house style and treat the
request as applying only to chat. Rejected because the PR bodies are what the
reviewer actually reads.

**Filed B-15 and B-16 as two tickets, not one.** They share a failure chain —
a leaked alarm from B-15 is what would fire against B-16's stale `ALARM_PID` —
but the fixes are independent and in different files. Stated the reasoning in
the cross-link comment so a maintainer does not read it as duplicate noise.

**Cross-linked by URL in comments, not Jira issue links.** Settled constraint,
do not re-ask: there is no Link Issues permission in CFE.

**Did not rewrite B-12's commit message.** `60a2` said to "correct the commit
message's implied blast radius per Grok". On reading it, the final paragraph
already conditions the claim correctly ("On hosts with several active default
routes where a lower-metric route appears after a higher-metric one"). Rewriting
would have meant a force-push for no gain. The blast-radius framing went in the
PR body's Scope section instead.

## Evidence & Data

**B-12, verified last session and re-used here rather than re-run:** deleting
only the line `lowest_metric = metric_value;` builds clean (rc 0) and fails
exactly `test_lowest_metric_last` (`"192.168.0.1" != "192.168.0.3"`), test run
rc 1; restore byte-identical, sha256
`4e6bd587940c991015051581264b950180de547f59a537889d6108ed9359e843`; all 7 cases
pass again. `test_lowest_metric_first` is a deliberate control and passes
against the unfixed code too.

**B-15, verified this session against `upstream/master` `22ce89322`:**

```
cf-agent/nfs.c:1369   ReconcileMountOptions()
cf-agent/nfs.c:1436   SetTimeOut(timeout)     <- remount path
cf-agent/nfs.c:1461   SetTimeOut(timeout)     <- unmount_mount path
```

The only `alarm(0)` calls in the whole file are `:581` and `:1178`, pairing
with the `SetTimeOut()` at `:403` and `:1122`. Nothing disarms 1436/1461 on any
path. Introduced by `348722a06` "Added opt-in remount reconciliation for storage
mount options", Nick Anderson, 2026-07-12. Reachable only with the opt-in
`remount_method` attribute.

Distinction that makes it worth filing separately from the known leaks: this is
a **success-path** leak. The known family — `verify_exec.c:308` leaking on
`:330/:374/:393`, `nfs.c:403` on `:408/:427`, `nfs.c:1121` on `:1129`,
`history.c:242` on `:261/:304/:330/:348` — only leaks when something already
went wrong. These two leak on every ordinary run.

**B-16, verified this session against the same master:**

```
libpromises/unix.c:166  ShellCommandReturnsZero()
libpromises/unix.c:184  ALARM_PID = -1          <- before the fork
libpromises/unix.c:225  ALARM_PID = pid
libpromises/unix.c:238  waitpid(pid, &status, WNOHANG)   <- reaps
libpromises/unix.c:258  waitpid(pid, &status, 0)          <- reaps
```

No `ALARM_PID` assignment after `:225`. This is the counterexample to the
"pid cannot be recycled, the child is an unreaped zombie" argument that a
previous panel accepted as settled — here the child is *fully reaped* and the
pid is recyclable while `ALARM_PID` still names it. cf-agent typically runs as
root.

**PR status sweep, 2026-08-17 ~18:30:** #6293 5 comments / #6294 7 comments —
all authored by `djbclark`. #6299, #6300, #6302 zero comments. All five
`MERGEABLE`, checks `SUCCESS`, no `reviewDecision`.

**Worktree state.** Removed: `libntech-b4` (`fix/json-real-precision`, fork has
`cd545ab1` = local HEAD) and `libntech-jsonstr` (`fix/json-string-codec`, fork
has `90cf8cc0` = local HEAD). Both verified pushed before removal.

**`libntech-p3` has unpushed local work** — `fork/silent-digest-failure-v2` is
at `21364443ec8778db01c491cf5acd27c82ea4754a` but local HEAD is `e76700b`. Not
removed. Nobody has said what that delta is; find out before touching it.

Note libntech's remotes are inverted from core's: `origin` is
**NorthernTechHQ/libntech** (upstream) and `fork` is **djbclark/libntech**.
`git rev-list origin/<branch>` fails there for our branches — check `fork`.

## Operator Feedback

**Standing order, relayed from a CFEngine upstream dev over chat:** *"see if
you can get your llm to be a bit more conservative on volume of words :)"*
Applies everywhere — chat, PR bodies, ticket text, handoffs. Saved as memory
`be-terse-upstream-asked`. Terse is not the same as dropping caveats a claim
needs; #6302 is shorter than #6300 and still carries both required disclosures.

**The quota correction.** The operator supplied the real number when my resume
plan asserted the opposite, then twice redirected work into what would actually
fit ("anything we can be sure will get done within that constraint?", "I think
there is room to do the teo filings now"). The pattern to keep: when the window
is tight, text-only work — filings, PR bodies, register corrections — is what
finishes; anything requiring a build plus verification does not.

## Where We're Going

1. **THE NEXT ACTION — apply B-2's three required changes** in
   `/Users/djbclark/src/core-b2merge` on `fix/timeout-process-group-merged`.
   New C in a signal path, so `fable-deep` with `model: 'fable'`. **Needs a
   fresh 5h window — do not start below ~30% headroom.** Full rationale is in
   `60a2` "Where We're Going" item 1; the three changes are:
   1. `#ifndef __MINGW32__` around the `getpgid()` / `kill(-pid, SIGKILL)`
      block in `TimeOut()` (`libpromises/timeout.c`). **Blocking** — confirmed
      independently by grok, fable and gpt-5.6-sol. `timeout.c` compiles on
      MinGW and every other raw `kill()` in NT-compiled code is already fenced.
   2. `TIMEOUT_ARMED` → `volatile sig_atomic_t`. Required for coherence, not
      because it is a live bug — and note fable's honest counterweight: house
      style is actually plain-bool handler flags (`signals.c`
      `PENDING_TERMINATION`), and #6299 introduced the tree's first
      `sig_atomic_t`. Verify it cannot affect `cf_popen()`'s child gate.
   3. A ~50-line `tests/unit` probe pinning the `ClearTimeOut()` contract.
      fable **measured** that a flag-clearing variant passes all six acceptance
      tests (6/6, 61s), so the invariant the whole merge rests on is currently
      unpinned. It proved pinnable via a probe calling public `TimeOut()`
      directly — PIN-PASS on the merged lib, PIN-FAIL on the flag-clearing
      variant.
2. **Re-verify B-2 after the fixes** — build, 6/6 acceptance, **both**
   discrimination directions, sha256 restores — then a **small 2-seat panel**.
   The shape is already cleared; only the deltas need review.
3. **Watch the five open PRs for the first maintainer response.** Nothing has
   been reviewed yet. Command in Quick Start.
4. **CFE-4727**, the exec_timeout termination half. Still unwritten. **Must
   start from the ALARM_PID theory — its refutation is RETRACTED.** Residual
   defect is `cf_pclose()` clearing `ALARM_PID` before waiting, so an alarm
   firing in that window takes the `else` branch and the child is never
   terminated. Do this *after* B-2 lands — same signal path. CFE-4733/B-16 is
   now filed and is adjacent evidence.
5. **B-10's core half (CFE-4725)** still pending on libntech#294 merging AND
   cfengine/core bumping its libntech submodule (`djbclark/core#7`). Do not
   offer before then.
6. **B-14 / CFE-4731** still filed and unpatched; any fix must be coordinated
   with #293's decoder.
7. **Remaining housekeeping.** `core-p1`/`core-p2` need a submodule deinit or
   `--force` (plain `git worktree remove` refuses). `core-json` needs
   `make clean` first and has a nested libntech worktree at `core-json/libntech`.
   Resolve `libntech-p3`'s unpushed delta before removing it. Keep
   `core-acceptance`, `libntech-fixes`, `core-b12`, `core-b2merge`.

## Quick Start

```bash
# Where B-2 lives — the next action
git -C /Users/djbclark/src/core-b2merge log --oneline -1      # 3d8e90d68
git -C /Users/djbclark/src/core-b2merge status --porcelain    # empty
git -C /Users/djbclark/src/core-b2merge branch --show-current # fix/timeout-process-group-merged

# Read the panel before acting on it
ls /Users/djbclark/src/tendcf/docs/architecture/upstream-opinion-b2merge-*.md

# Has anyone upstream said anything yet?
for n in 6293 6294 6299 6300 6302; do
  gh pr view $n --repo cfengine/core \
    --json number,state,mergeable,reviewDecision,comments,statusCheckRollup \
    -q '"#\(.number) \(.state) mergeable=\(.mergeable) review=\(.reviewDecision // "none") comments=\(.comments|length)"'
done

# Quota FIRST — and the numbers are CONSUMED, not remaining
cswap list            # "5h: 93%" means 7% LEFT. Restate it as "X% left".

# Jira: comment on an issue
TOKEN=$(sudo-secretspec get ATLASSIAN_CFENGINE_API_TOKEN --reason "<why>")
curl -sS -u "djbclark@gmail.com:$TOKEN" -X POST -H "Content-Type: application/json" \
  --data @body.json \
  "https://northerntech.atlassian.net/rest/api/2/issue/CFE-4729/comment"
# Create an issue: drop the /<KEY>/comment suffix, POST to .../rest/api/2/issue
# with fields{project:{key:CFE}, issuetype:{name:Bug}, summary, description}.
# /api/2/search is HTTP 410 — use /rest/api/3/search/jql.

# Verify a line number against real upstream master before citing it anywhere
git -C /Users/djbclark/src/core-b12 fetch -q upstream master
git -C /Users/djbclark/src/core-b12 show upstream/master:cf-agent/nfs.c | sed -n '1430,1465p'
```

Build rules that still hold: `-j2`/`-j4`, never `-j8`. Do not build or modify
`/Users/djbclark/src/cfengine-core` — other work uses it and its libntech
submodule must stay uncommitted. `--bindir` is wrong for an in-tree acceptance
run; name `--agent=` / `--cfpromises=` explicitly. `cf-promises` in the build
tree is a libtool wrapper, not the binary — the real one is
`cf-promises/.libs/cf-promises`.
