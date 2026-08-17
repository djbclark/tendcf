---
schema_version: 1
handoff_id: 5749
parent_handoff_ids: [f1a4]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 6ac3e35986e0349ddf66bb890f6acf509f6343dc
created_at: 2026-08-17T16:06:28-0400
writer: claude-code
---

# Handoff — three PRs upstreamed, and task #2 turned out not to need Fable

## The Goal

Session opened with `/baton` to resume `f1a4`, whose owed next action was
**task #2: the six ticketed items with no upstream PR** — B-1 (CFE-4728),
B-2 (CFE-4729), B-8 (CFE-4726), B-10's core half (CFE-4725), B-12 (CFE-4723)
and the exec_timeout termination half (CFE-4727). `f1a4` recommended starting
with B-8, "the only true fail-open".

**Three PRs shipped.** The session also produced a structural correction to how
task #2 was framed, which is the single most useful thing to carry forward.

## Where We Are

`tendcf` clean at `6ac3e35`, pushed. **Zero stashes anywhere. Nothing in
flight.** Seven workspaces, all clean:

| workspace | branch | head | dirty |
|---|---|---|---|
| `/Users/djbclark/src/tendcf` | `master` | `6ac3e35` | no |
| `/Users/djbclark/src/core-acceptance` | `fix/exec-timeout-poll-deadline` | `179e95754` | no |
| `/Users/djbclark/src/libntech-fixes` | `fix/json-number-handling` | `eda43f0` | no |
| `/Users/djbclark/src/libntech-jsonstr` | `fix/json-string-codec` | `90cf8cc` | no |
| `/Users/djbclark/src/core-p1` | `simulate-keep-chroot` | `f6c06f9e2` | no |
| `/Users/djbclark/src/core-p2` | `simulate-json` | `b3a6c3da5` | no |
| `/Users/djbclark/src/core-json` | `fix/json-number-rendering` | `32c38f8ab` | no |

`core-acceptance` and `libntech-fixes` are now **built** — keep them until
their PRs resolve.

### Shipped — three upstream PRs, all OPEN and MERGEABLE

| PR | Item | Ticket | Head | Shape |
|---|---|---|---|---|
| [cfengine/core#6299](https://github.com/cfengine/core/pull/6299) | B-8, the `exec_timeout` fail-open | CFE-4726 | `0ab083c4d` | 2 commits, 5 new acceptance tests |
| [cfengine/core#6300](https://github.com/cfengine/core/pull/6300) | B-1, poll loops counting iterations | CFE-4728 | `179e95754` | 1 commit |
| [NorthernTechHQ/libntech#294](https://github.com/NorthernTechHQ/libntech/pull/294) | B-4 + B-10 + B-11, JSON numbers | CFE-4724 | `eda43f0` | 6 commits |

All three PR head SHAs were verified against the local branches at handoff
time and match exactly. Each ticket was updated and **verified by read-back**
(not by trusting the `HTTP 204`), and each fork issue was commented with an
idempotent guard and confirmed to hold **exactly one** such comment.

### THE STRUCTURAL CORRECTION — task #2 was never mostly new C

`f1a4` framed task #2 as PR-bound C requiring a `fable-deep` agent. **That was
wrong for four of the six items.** B-1, B-2, B-8 and B-10's core half already
had fixes written, committed to fork branches, and 3-or-4-model-panel reviewed.
What was `*pending*` was only *offering them upstream*. No new C, no Fable gate.

Only **B-12** and **CFE-4727** are genuinely unwritten.

And B-10's real blocker was not the core code at all: its libntech stack had
only ever been a **fork** PR (`djbclark/libntech#5`) and had **never been
offered to NorthernTechHQ**. Offering it (as `#294`) was the actual unblocking
move.

**Read the register's Upstream column before assuming an item needs code.**

### Register commits this session

- `d8ddf61` — B-8 offered as `#6299`; also corrected the register's own
  retracted "reported as **kept**" label to "compliant", filled the Fix cell
  with all four B-8 commits, and discharged two stale narrative claims.
- `e066721` — B-1 offered as `#6300`; B-2 recorded as **blocked on a merge**
  rather than merely pending.
- `6ac3e35` — B-4/B-10/B-11 libntech half offered as `#294`; core half
  re-scoped to a documented dependency.

### Files changed this session

**`tendcf`** — three commits, all pushed, **one file each**
(`docs/architecture/upstream-register.md`): `d8ddf61` (+11/−5), `e066721`
(+8/−7), `6ac3e35` (+3/−3). Plus this handoff document.

**No source file in any other repo was edited.** The three upstream branches
were built by cherry-picking already-reviewed commits onto fresh bases and
rewriting only their *messages* — every one was checked with
`git diff <fork-branch> --stat` returning empty before being pushed:

- `/Users/djbclark/src/core-acceptance` → new branch
  `fix/exec-timeout-promise-outcome` (`0ab083c4d`, 2 commits) and new branch
  `fix/exec-timeout-poll-deadline` (`179e95754`, 1 commit), both pushed to
  `origin` (the fork).
- `/Users/djbclark/src/libntech-fixes` → new branch `fix/json-number-handling`
  (`eda43f0`, 6 commits), pushed to the `fork` remote.

Transient-only: source files were reverted to stock and restored during each
discrimination run, every restore sha256-verified byte-identical with a clean
`git status` afterwards.

**No memory files written this session.**

## What We Tried

Failures and near-misses, chronological. These are the expensive ones.

1. **The first acceptance run FAILED all five tests in 2 seconds** — impossible
   for a suite containing a deliberately ~12-second test, which is what made me
   look instead of recording it. Cause: `--bindir` is wrong for an **in-tree
   build**; binaries live at `cf-agent/cf-agent`, not flat in one directory. The
   runtest log said `.../core-acceptance/cf-agent: is a directory`. Fixed by
   passing `--agent=` / `--cfpromises=` / `--cfserverd=` / … explicitly.
   **A suspiciously fast failure is a harness bug until proven otherwise.**

2. **A timing run showed 30.4s on the FIXED build** and looked like the B-1 fix
   had simply failed. It had not. The probe command was
   `sh -c "trap '' INT TERM; sleep 30"` — the shell is killed but its `sleep`
   **grandchild survives holding the pipe**, so `cf_pclose()` blocks for the
   full 30s. That measures **B-2/CFE-4729**, not B-1's ladder. Redone with a
   single-process command (`python3` ignoring both signals in-process), which
   gave the real numbers. **To measure the ladder you need a command with no
   surviving grandchild.**

3. **`cf-agent` silently fell back to failsafe and returned in 0.26s**, having
   never run the command — it could not find `cf-promises`. Two separate causes,
   found one after the other: the acceptance harness's
   `CFENGINE_TEST_OVERRIDE_WORKDIR` was not set, and then, once it was, the
   `cf-promises` copied into it was a **libtool wrapper script**, not a binary
   (`.libs/cf-promises` is the real one). The script now greps its own output
   for `failsafe` and reports `INVALID` rather than recording a fast, meaningless
   number.

4. **The `Changelog:` trailers were silently dropped from all six libntech
   commits.** `git log --format='%b'` emits the body with a trailing blank line,
   so appending `Ticket: CFE-4724` created a **second** trailer block — and git
   parses only the *last* block as trailers. `git log --format='%(trailers:only)'`
   showed only `Ticket:`. Caught by checking the trailers rather than assuming
   the commit took. Fixed by `rstrip("\n")` on the body first; the branch was
   deleted and rebuilt from scratch.

5. **Nearly shipped a withdrawn claim upstream.** B-1's commit `26634ac1f` body
   still asserted that the patch stops a timed-out command being reported as
   promise KEPT — the exact claim the 2026-08-16 panel **retracted**. Reusing the
   fork commit verbatim would have republished it on cfengine/core. Caught by
   reading the fork issue's *correction comments* before reusing anything from
   the body. This is the `never-refile-body-verbatim` lesson, now proven to
   apply to **commit messages**, not just issue bodies.

6. **The register carried its own retracted label.** B-8's Item cell still said
   "reported as **kept**" even though the panel's correction to "compliant" was
   months of work old. Our own record needs the same scrutiny as upstream's.

7. **A false OS claim was about to go public.** The fork issue and CFE-4726 both
   said "macOS 15 arm64"; `sw_vers` says **macOS 26.6.1**. Corrected on the
   ticket and kept out of all three PR bodies. Also dropped an unverified
   "3.27.1" claim rather than repeat a measurement I had not personally re-run.

## Key Decisions

- **Verified every claim myself rather than trusting the register or the fork
  issues.** All three PRs got a full build, a test run, and a *discrimination*
  run at the exact shipped content, with sha256-checked restores. Rejected:
  citing the recorded numbers, which is how the retracted claims survived this
  long in the first place.
- **Cut fresh upstream-facing branches instead of rebasing the fork branches.**
  Each new branch has a byte-identical tree to its reviewed counterpart
  (`git diff <fork-branch> --stat` empty, checked every time) but house-style
  commits. This preserves the fork branches and the SHAs the fork issues cite.
  Rejected: rebasing/force-pushing the fork branches.
- **Squashed review churn, kept genuinely distinct fixes separate.** B-8's three
  commits became one (commits 2 and 3 fixed defects in commit 1, found by our own
  review — upstream should not see a knowingly-buggy first commit); B-1's two
  became one; libntech's six stayed six, because those are four distinct defects
  with their own tests.
- **Matched upstream house style**, established by reading the last 300 commits:
  past-tense subjects ("Fixed …", "Added …"), `Ticket:` + `Changelog:` trailers,
  ticket key in the **PR title** but not the commit subject, and no
  `Co-Authored-By`.
- **Did NOT add `#include <platform.h>` to `timeout.h`.** The header declares
  `bool`-returning functions with no includes, and the peer `process_lib.h` does
  include `platform.h` — so it is a real (if latent) house-style gap. Chose to
  keep the shipped diff **byte-identical to what three reviewers examined**
  rather than add an unreviewed cosmetic change. Noted as an optional follow-up.
- **Based #6299/#6300 on `17eb78e6d` rather than current tip `22ce89322`.** The
  only drift is a libntech submodule bump touching nothing in these paths, and
  basing on the commit I actually built and tested is the more honest position.
  Stated explicitly in both PR bodies.
- **Stated every known limit up front in the PR bodies** rather than letting a
  reviewer find them: `background => "true"` unchanged, the residual
  `cf_pclose()`/alarm-disarm window, the `timeout_ns <= 0` semantic change, the
  `clock_gettime` mock's blast radius, the stale `assert`, and the fact that
  B-1's unit test **structurally cannot** demonstrate the overshoot.
- **Recorded B-2 as blocked rather than pending**, with the merge shape written
  down, instead of attempting the merge on Opus.

## Evidence & Data

**#6299 (B-8).** Built from scratch against stock libntech `5b5d04e1`:

```
make -j2                     rc=0; 2 warnings, both pre-existing upstream
                             (evalfunction.c:674, variable.c:296)
five acceptance tests        5 passed, 0 failed  (53s)
```

Discrimination — reverting **only** `cf-agent/verify_exec.c`,
`libpromises/timeout.c`, `libpromises/timeout.h` to stock `17eb78e6d`, keeping
the tests:

```
timeout_overrides_exit_zero              FAIL
within_timeout_normal_outcomes           Pass   <- correct; normal-path guard
timeout_overrides_kept_returncodes       FAIL
timeout_after_output_closed              FAIL
timeout_does_not_leak_to_next_promise    FAIL
```

Restore byte-identical (sha256), clean tree, clean rebuild.

**#6300 (B-1).** The unit test cannot show the overshoot — its `nanosleep` mock
advances a fake clock by the *requested* sleep, which is precisely the
accounting being removed — so the ladder was measured directly, three runs each,
single-process command ignoring `SIGINT`/`SIGTERM` under `exec_timeout => "2"`:

```
stock 17eb78e6d   11.36s / 10.80s / 10.90s
fixed branch       4.54s /  4.48s /  4.41s
```

An ~8.9s ladder becoming ~2.4s once the 2s timeout is subtracted — reproducing
the original claim independently.

```
make -j2                     rc=0, 0 warnings
tests/unit make check         rc=0, 64 PASS + 4 XFAIL = 68 (exact baseline)
process_terminate_unix_test   PASS
```

**#294 (B-4/B-10/B-11).** The sharpest discrimination of the three — reverting
only `libutils/json.c` and `libutils/mustache.c` to stock `0c0620d` makes the
library **terminate its own test binary**:

```
json_test rc=1 — the run never reports.
  test_real_renders_as_parsed                    Test failed
  test_real_created_in_memory_renders_as_stored  Test failed
  test_parse_exponent_numbers                    Test failed
  "0.00049" != "0.00"   /   "0.5000" != "0.50"
  test_primitive_to_string_numbers: Starting test
     error: Conversion error (34 - Overflow) on '9223372036854775808'
            (StringToLongExitOnError)
  <killed>
```

74 tests start unfixed; 76 start fixed and `All 75 tests passed`. Full suite
`39/39` binaries, `make -j2` rc=0 with 0 warnings. Restore byte-identical.

**Merge/conflict facts, measured not assumed:**

```
B-1  vs #6299 branch    disjoint file sets                    -> independent
B-2  vs #6299 branch    merge-tree rc=1, 10 conflict markers  -> BLOCKED
#294 vs #293            merge-tree rc=0, 0 markers            -> independent
upstream drift 17eb78e6d..22ce89322 = 2 commits, libntech submodule bump only
```

**One pre-existing warning** appears when building the libntech test binary —
`json_test.c:2618`, `JsonNullCreate` called without a prototype. Traced with
`git log -L` to upstream commit `1d26c08`; **not ours**.

**Upstream state at session end — no maintainer response on ANY of the five:**

```
core#6293    OPEN MERGEABLE f6c06f9e2
core#6294    OPEN MERGEABLE b3a6c3da5
core#6299    OPEN MERGEABLE 0ab083c4d   <- new
core#6300    OPEN MERGEABLE 179e95754   <- new
libntech#291 OPEN MERGEABLE e76700b05
libntech#293 OPEN MERGEABLE 90cf8cc
libntech#294 OPEN MERGEABLE eda43f0     <- new
```

**Quota at 15:56:** mit.edu 5h **81%** (resets 20:09), 7d 65%. gmail 5h 99%
(resets 16:19), Fable 67% (resets Aug 21).

## Operator Feedback

- **"Yes, proceed on that basis"** — approving the plan to do non-C preparation
  on the mit.edu account and hand new C to `fable-deep` once gmail's Fable
  recovered. The work overshot that basis in the good direction: three complete
  PRs, because it turned out almost none of it was new C.
- Standing, unchanged from `ee9c`: *"You do not need to wait for me to open PRs
  or send emails, however you do need to hold off for long enough to minimize
  the chances of posting something incomplete or wrong."* Honoured by verifying
  build + tests + discrimination + claim accuracy before each of the three.
- Standing, from `9997`: retest an inherited blocker before repeating it. This
  session inherited none that proved false, but it **did** inherit a framing
  (task #2 = new C) that was wrong, and inherited three *claims* that were wrong.

## Where We're Going

1. **THE NEXT ACTION — B-2 / CFE-4729, which needs a session on the gmail
   account.** It is blocked on a merge with `#6299`, not on effort:
   `git merge-tree` returns rc=1 with 10 conflict markers because both edit
   `SetTimeOut()`/`TimeOut()` in adjacent lines. The changes are
   **complementary**: `#6299` adds `TIMEOUT_FIRED`/`TIMEOUT_SIGNALLED` outcome
   reporting; B-2 adds `TIMEOUT_ARMED`, `ClearTimeOut()` and the process-group
   kill. A merged `SetTimeOut()` sets all three flags; a merged `TimeOut()` sets
   `FIRED`, clears `ARMED`, and inside the `ALARM_PID != -1` branch sets
   `SIGNALLED` and does the group kill.
   **HAZARD:** B-2's `ClearTimeOut()` replaces the open-coded
   `alarm(0); signal(SIGALRM, SIG_DFL)` in `verify_exec.c` that `#6299` samples
   its flag immediately *before* — the merged `ClearTimeOut()` **must not clear
   `TIMEOUT_FIRED`**.
2. **Fable is unreachable from a mit.edu session.** `djbclark@mit.edu` has **no
   Fable line at all**, and a subagent inherits the session's account. Run
   `cswap switch 2`, then start a **NEW** session — switching does not move an
   existing one.
3. **B-12 / CFE-4723** — `libenv/unix_iface.c:1425` declares
   `long lowest_metric = 0;` and never assigns it, so the default-route
   comparison is `metric_value < 0`, false for every real metric: CFEngine picks
   the *first* active default gateway, not the lowest-metric one. Unwritten,
   needs Fable.
4. **CFE-4727, the exec_timeout termination half** — unwritten, and **must start
   from the ALARM_PID theory**; its refutation is retracted. Needs Fable. This
   session incidentally produced fresh evidence for it (see What We Tried #2).
5. **B-10's core half (CFE-4725)** stays pending on a real dependency: `#294`
   must merge and cfengine/core must bump its libntech submodule
   ([core#7](https://github.com/djbclark/core/issues/7)). Do not offer it before
   then.
6. **B-14 / CFE-4731** still filed and unpatched; any fix must be coordinated
   with `#293`'s decoder. Unchanged from `f1a4`.
7. Housekeeping, still not urgent: `git worktree remove` for `core-p1`,
   `core-p2`, `libntech-b4`, `libntech-jsonstr`; `core-json` needs `make clean`
   first. **Keep `core-acceptance` and `libntech-fixes`** — both built, both
   backing live PRs.

## Quick Start

```bash
# 0. Model gate. Fable lives ONLY on gmail; mit.edu has no Fable line.
cswap list                      # then: cswap switch 2, then a NEW session

# 1. Live upstream state — five open PRs, none reviewed as of 2026-08-17
for p in 6293 6294 6299 6300; do gh pr view $p -R cfengine/core \
  --json number,state,mergeable,reviews --jq '"\(.number) \(.state) \(.mergeable) reviews=\(.reviews|length)"'; done
for p in 291 293 294; do gh pr view $p -R NorthernTechHQ/libntech \
  --json number,state,mergeable,reviews --jq '"\(.number) \(.state) \(.mergeable) reviews=\(.reviews|length)"'; done
# gh pr view uses graphql. If it 503s, REST still works:
#   gh api "repos/cfengine/core/pulls?state=all&per_page=50" --jq '.[] | "\(.number) \(.head.label)"'

# 2. Reproduce the B-2 conflict that blocks the next action
cd /Users/djbclark/src/cfengine-core
git merge-tree --write-tree fix/exec-timeout-promise-outcome fix/timeout-process-group >/dev/null 2>&1; echo "rc=$? (1 = conflicts)"
git diff 17eb78e6d..fix/timeout-process-group -- libpromises/timeout.c libpromises/timeout.h cf-agent/verify_exec.c

# 3. Rebuild/re-verify either live worktree. Scripts are in the session
#    scratchpad and encode the traps below; copy them forward if still present.
cd /Users/djbclark/src/core-acceptance && make -j2          # on fix/exec-timeout-poll-deadline
cd /Users/djbclark/src/libntech-fixes && make -j2 && (cd tests/unit && rm -f json_test json_test.o && make check)
#   ^ remove the .o too, not just the binary, or a stale object gets relinked

# 4. Acceptance tests: --bindir is WRONG for an in-tree build (all tests FAIL
#    in ~2s). Name each binary explicitly:
cd /Users/djbclark/src/core-acceptance/tests/acceptance
./testall --gainroot=env --agent=$PWD/../../cf-agent/cf-agent \
  --cfpromises=$PWD/../../cf-promises/cf-promises ... 08_commands/04_exec_timeout/*.cf

# 5. Jira (token via the broker only; never echo it). /api/2/search is HTTP 410.
TOKEN=$(sudo-secretspec get ATLASSIAN_CFENGINE_API_TOKEN --reason "<why>")
curl -sS -u "djbclark@gmail.com:$TOKEN" \
  "https://northerntech.atlassian.net/rest/api/2/issue/CFE-4729?fields=summary,status"
```

**Do not** build or modify `/Users/djbclark/src/cfengine-core` — other work uses
it and its libntech submodule must stay uncommitted. Builds at `-j2`/`-j4`,
never `-j8`.

**Running cf-agent by hand needs `CFENGINE_TEST_OVERRIDE_WORKDIR`, and the
`cf-promises` you put in its `bin/` must be `cf-promises/.libs/cf-promises`** —
the top-level one is a libtool wrapper script. Get either wrong and cf-agent
falls back to failsafe, returns in ~0.26s, and never runs your command.

**Check the register's Upstream column before assuming an item needs code.**
Four of task #2's six items already had reviewed fixes; only the offering was
missing. Two do not — B-12 and CFE-4727.

**Read a fork issue's correction comments before reusing ANY of it — including
its commit messages.** B-1's commit body still carried a claim the panel
retracted, and would have republished it on cfengine/core.

**Verify a trailer landed rather than assuming the commit took**
(`git log --format='%(trailers:only)'`). A blank line silently splits the
trailer block and git keeps only the last one.

**A suspiciously fast failure — or a suspiciously slow success — is a harness
bug until proven otherwise.** Both bit this session.
