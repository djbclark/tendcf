---
schema_version: 1
handoff_id: 9796
parent_handoff_ids: [6916]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 316a07fc188c8f6ed7f1f994ad790b3fe37bb44a
created_at: 2026-08-22T14:53:14-0400
writer: claude-code
---

# Handoff — fork-is-the-destination migration, and the A1 exec_timeout investigation

## The Goal

Two operator instructions drove this session.

**First**, act on the fallout from the 2026-08-19 blanket rejection: correct the
corpus claims that were now false, and record the closure.

**Second, and the substantive change of direction:** *"we are going to replace
upstream with our fork, which we will be maintaining and using now, no longer
trying to get everything into upstream in a timely manner. So fix everything,
but against our github fork, and always open a pr or issue, but only against our
github fork issue/pr database. Do not send any email or use the Jira via the API
or otherwise without my specific request."*

The concrete next step named: copy all 26 now-closed Jira tickets into fork
issues, review them for anything needing a judgment call or upstream input, and
file one consolidated questions ticket. Then, later, merge fixes into larger
thematic PRs grouped by the code they touch, so a human reviewer does not read
the same function four times across four tickets.

Mid-session the operator asked to investigate **A1** — the one unresolved
technical objection in the set — with a view to leading the upstream restart
with it.

## Where We Are

tendcf is clean at `316a07f` on `master`, everything pushed. Two commits this
session, both docs.

The migration is **complete**. All 26 tickets are mirrored, the corpus no longer
asserts anything false about upstream state, and the policy memories are
retargeted.

A1 is **investigated and settled**, with a result that argues *against* the
operator's initial plan to lead with it. The operator has accepted that
conclusion and named a different candidate for the restart — see Where We're
Going.

## What We Tried

Chronological, with the failures, because they were expensive.

**Reproducing A1 needed a stock binary.** No worktree was at unpatched upstream.
Rather than a fresh build, checked whether any existing worktree's timeout-path
files were untouched: `core-cmdbnull` has `verify_exec.c`, `pipes_unix.c`,
`unix.c`, `timeout.c` byte-identical to `a0bca6aaf` (empty `git diff`). Used it.
Later found `/opt/homebrew/bin/cf-agent` is **stock CFEngine 3.27.1** — the exact
version the maintainer used, unrelated to this fork — which is strictly better
evidence and became the primary platform.

**Three failed attempts at a runnable policy**, each costing a cycle:
1. Ran `cf-agent --workdir=...` — fell to failsafe, "cf-promises needs to be
   installed in .../bin". `--workdir` is not the right lever.
2. Created `bin/cf-promises` symlink — still failsafe, no host key.
3. Ran `cf-key --workdir=...` — silently did nothing. The working mechanism is
   the environment variable **`CFENGINE_TEST_OVERRIDE_WORKDIR`**, which both
   `cf-key` and `cf-agent` honour and which keeps all state out of
   `/var/cfengine`.
4. Policy used `classes => results(...)` from stdlib and failed to parse
   (`Undefined body results with type classes`). Replaced with an inline
   `body classes` binding `promise_kept`/`promise_repaired`/`repair_failed`/
   `repair_timeout` — which turned out to be far better, because the unused
   `repair_timeout` binding became the cleanest proof of the defect.

**The mechanism was asserted wrongly, twice, and both times a reviewer caught
it.** Details in Key Decisions; this is the most important lesson in the doc.

**opencode/gpt-5.6-sol was unreachable** — the `opencode` provider has no
balance ("Insufficient balance"). sol 5.6 was reached instead through
`codex exec -m gpt-5.6-sol -c model_reasoning_effort="xhigh"`. Note `codex exec`
hangs reading stdin unless given `</dev/null`.

**grok's first run produced nothing usable** — it was launched in the scratchpad
with no source access and refused the brief, asking for the real files. That
refusal was itself the single most valuable output of the session (see below).
Relaunched with a read-only copy of four source files in `scratchpad/src-ro`,
after which it produced a full review.

## Key Decisions

**Read every ticket body AND every comment before mirroring; never copy
verbatim.** Vindicated repeatedly: CFE-4727 carried a retracted refutation,
CFE-4732 two severity corrections, CFE-4719 an inflated test count, and
CFE-4738/4739 both said "no patch offered" when later comments superseded it. A
verbatim copy would have republished withdrawn claims.

**Mirror by exception, not wholesale.** 15 of 26 tickets already had a fork
issue; those got a closure comment carrying the disposition plus ticket-only
content, rather than a duplicate issue. Only 11 needed creating. CFE-4725 got
none — it duplicates CFE-4737 and both map to core#13.

**Anonymous Jira GET is permitted; writes are not.** The operator's "do not use
the Jira via the API" was read as prohibiting *outbound* action, since the task
they assigned in the same message required reading the tickets. All 26 were
fetched read-only from `northerntech.atlassian.net`. No Jira write occurred.

**Rejected: leading the upstream restart with A1.** The operator proposed it;
this was argued against twice, on strengthening grounds. The maintainer's own
words are *"Start with the smallest bug fix you have which is easy to explain /
review"* — and A1 requires a signal ladder, a ~1s window, shell SIGINT semantics,
and an opening paragraph explaining why the reviewer's own test showed the
opposite. Operator agreed.

**Rejected: telling the maintainer he is "provably wrong".** He wrote only
*"Humm, When I spot check this against 3.27.1 I get abnormal termination, promise
not kept."* That is an observation about a test he built, hedged as a spot check,
and it reproduces exactly. There is no false statement to disprove. Two
independent reviewers, given a brief written to invite that conclusion, both
refused it.

**Rejected: hoping a correct finding would change his mind about the AI policy.**
His stated objection was review burden, not correctness. All 23 defects could be
real and the volume complaint would stand unchanged.

## Evidence & Data

**Migration.** 11 new issues — djbclark/core#15–22 (CFE-4727, 4732, 4733, 4734,
4735, 4736, 4738, 4739) and djbclark/libntech#6–8 (CFE-4730, 4731, 4740). 15
closure comments on pre-existing issues: core #2(4715) #3(4716) #4(4728) #5(4729)
#6(4726) #8(4719) #9(4720) #10(4721) #11(4722) #12(4718) #13(4737+4725)
#14(4723); libntech #2 and #4 (both CFE-4724) and #3(4717). Labels
`jira-migrated` and `needs-decision` created on both repos.

**djbclark/core#23** is the consolidated questions issue: 16 judgment calls in
five groups.

**A1 measurements — all on stock Homebrew CFEngine 3.27.1**, `exec_timeout=2`,
command ignoring SIGINT, only duration varying:

```
finishes at 1.5s   -> repaired   alarm fired: no    (correct)
finishes at 2.2s   -> repaired   alarm fired: YES
finishes at 2.4s   -> repaired   alarm fired: YES
finishes at 2.9s   -> repaired   alarm fired: YES
finishes at 3.2s   -> not_kept   alarm fired: YES
finishes at 10.4s  -> not_kept   alarm fired: YES   (the maintainer's case)
```

Boundary tracks the limit: timeout=4 flips between 4.9s and 5.3s; timeout=6
between 6.5s and 7.4s. Approximately `timeout + 1s`, not exactly.

**The shell dependency — the session's most consequential finding.** Identical
policy, command finishing at 2.4s:

| shell | untrapped | with `trap '' INT` |
|---|---|---|
| `/bin/sh` (bash 3.2, macOS) | repaired | repaired |
| `/bin/dash` | not kept | repaired |
| `/bin/zsh` | not kept | repaired |

Debian and Ubuntu ship dash as `/bin/sh`. **If the maintainer's `/bin/sh` is
dash, the original reproducer would have reported "not kept" on his host at any
sleep value** — his negative result would have been correct, for a reason absent
from the report. No Linux measurement has been taken.

Portable reproducer, verified on all three shells:
`"/bin/sh" arglist => { "-c", "trap '' INT; sleep 2.4; exit 0" }` with
`exec_timeout => "2"`.

**Every run bound `repair_timeout => { "cmd_timeout" }` and `cmd_timeout` never
fired once**, including with the alarm firing. That is the cleanest proof and it
replaces a false claim (below).

**Source facts.** `TimeOut()` (`timeout.c:38`) calls `GracefulTerminate(
ALARM_PID, PROCESS_START_TIME_UNKNOWN)` at `timeout.c:45`. `GracefulTerminate()`
(`process_unix.c:241`) is SIGINT → wait → SIGTERM → wait → SIGKILL. `Kill()` with
unknown start time (`:227`) is a plain `kill(2)` on the pid, never the group.
`STOP_WAIT_TIMEOUT` = `999999999L` ns (`:135`). `ProcessWaitUntilExited()`
(`:86`) polls every 10 ms decrementing a **fixed** 10 ms — issue #4 — so the
window widens under load. macOS `GetProcessState()` is `process_unix_stub.c`
(reports zombies as RUNNING); Linux `process_linux.c` reads `/proc` and sees `Z`.

**Three errors found in our own CFE-4726 text**, all to fix before resubmission:
1. "`if_ok` has no `repair_timeout` counterpart" is **false** — `repair_timeout`
   is real (`mod_common.c:113`, `attributes.c:790`) and `failsafe.cf:464` uses
   it. The true claim is stronger: the outcome exists and this path cannot reach
   it.
2. There is no "default `kept_returncodes`"; exit 0 defaults to REPAIRED.
3. The outcome is not always decided via `VerifyCommandRetcode()` — a signalled
   child makes `cf_pclose()` return -1, taking the abnormal-termination branch,
   which is exactly the branch the maintainer hit.

**Reproduction script: `~/src/exec_timeout_repro.sh`** — stock install, no root,
~90s, confines state via `CFENGINE_TEST_OVERRIDE_WORKDIR`. Demonstrates the
window, the boundary tracking, the shell dependency, verbose proof, and the
SIGINT behaviour.

**Severity, revised down.** Both reviewers noted CFEngine documents
`exec_timeout` as an attempt: *"This cannot be guaranteed as not all commands are
willing to be interrupted."* The "control failure" framing is not supportable.
The `repair_timeout`-is-unreachable framing is.

**Panel.** gpt-5.6-sol (xhigh) and grok-4.6, brief deliberately framed to invite
"provably wrong". Both refused; trap control passed by both. grok found the
dash/SIGINT portability failure and the job-control flaw in the SIGINT demo. sol
found the three ticket-text errors and that the timing sweep alone does not
discriminate between the two candidate ladders.

## Operator Feedback

- *"We are going to keep the policies in 3, but are going to replace upstream
  with our fork."* Fix everything, always open a PR/issue — fork only.
- *"Do not send any email or use the Jira via the API or otherwise without my
  specific request."*
- On human-in-the-loop: *"What we would do is get you to explain it to me to the
  point I can test it independently and explain it to him, so I would be in the
  loop."* This is why the reproduction script exists as a standalone artifact.
- On A1: *"You are right, this does seem like a bad thing to lead with."*
- Worry that motivated the A1 dig: that the maintainer might make a mistake if
  wrong, and that a correct AI finding might change his view of the AI work.
  Both addressed; the second was argued to be a poor reason to shape an approach.
- On the write-up: *"Write about all this in a detached, professional manner."*

## Where We're Going

1. **THE next action — investigate leading the upstream restart with the
   `--simulate-json` feature instead of a bug.** Operator's reasoning, verbatim:
   *"as if I did not have AI I would have done just that feature request as my
   one ticket, and also I believe having the simulate json flag helps debug or
   triggers a lot of the other problems."* Two things to establish: (a) whether
   it fits the maintainer's "smallest, easiest to explain / review" criterion
   better than a bug fix does, given it is a *feature* and CFE-4715/4716 were the
   only two of 26 resolved **Won't Do** rather than Done — that disposition
   difference is unexplained and matters; (b) whether the claim that
   `--simulate-json` surfaced or triggered other defects is supported by the
   record. Start from djbclark/core#3 and #1, the CFE-4716 ticket, and the
   register's provenance notes — CFE-4717's provenance correction says it was hit
   *"while building the --simulate work"*, and CFE-4730 was found *"while
   correcting CFE-4716"*, so there is real evidence for (b).
2. Answer the open decisions on **djbclark/core#23** (16 items, five groups).
   Nothing upstream moves before these.
3. If A1 is ever resubmitted: fix the three text errors, use the portable
   `trap '' INT` reproducer, adopt the `repair_timeout`-unreachable framing, and
   **measure on Linux first**.
4. Then the thematic-grouping pass. Visible clusters: ALARM_PID/exec_timeout
   hygiene (core#15/16/17/18/19), `cmdb.c` entry-loop handling (core#8/9/11/21),
   the JSON-null root cause across two loaders (core#21/22), libntech JSON codec
   (libntech#2/4/6/7).
5. Mirror `NorthernTechHQ/libntech#296` (MustacheRender unit tests) — the one
   item of the 26 with no Jira ticket and still no fork issue. Tracked as D14.

**Standing constraints:** file only on `djbclark/core` and `djbclark/libntech`;
no email and no Jira writes without a specific operator request; anonymous Jira
GET is fine and needs no token.

## Quick Start

```bash
cd ~/src/tendcf && git log --oneline -3        # expect 316a07f at HEAD, clean

# The A1 record, and the open-questions worklist
gh issue view 6  -R djbclark/core --comments | tail -200
gh issue view 23 -R djbclark/core

# Reproduce A1 from scratch (stock 3.27.1, no root, ~90s)
~/src/exec_timeout_repro.sh /opt/homebrew/bin

# Starting point for the next action (--simulate-json as the restart candidate)
gh issue view 3 -R djbclark/core
gh issue view 1 -R djbclark/core
curl -s "https://northerntech.atlassian.net/rest/api/2/issue/CFE-4716?fields=summary,status,resolution,description,comment"

# The maintainer's rejection, in full
gh api repos/cfengine/core/issues/comments/5340989869 -q .body

# Lints (never python3)
cd ~/src/tendcf && uv run bin/schema_lint.py && uv run bin/xref_lint.py
```

**Gotchas.** `gh pr list` state is unreliable — use `gh pr view <n>`.
`codex exec` needs `</dev/null` or it hangs on stdin. `grok` needs `-p`, not
stdin, and needs source files in its working directory or it will refuse the
task. Reviewer CLIs can edit the tree — give them a read-only copy.
CFEngine test runs need `CFENGINE_TEST_OVERRIDE_WORKDIR`, not `--workdir`.
