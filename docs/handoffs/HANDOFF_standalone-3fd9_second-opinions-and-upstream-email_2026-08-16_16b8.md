---
schema_version: 1
handoff_id: 16b8
parent_handoff_ids: [5420]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 91b3f4245eb260d5092df266e908945f03bd90c5
created_at: 2026-08-16T20:34:11-0400
writer: claude-code
---

# Handoff — the second-opinion gate fired, and three items reached upstream

## The Goal

5420 left two CFEngine fixes filed on the fork and **nothing sent upstream**,
behind two gates in order: second opinions (newly required), then the Gmail
connector. This session was to clear both and send.

Both cleared. **Three items are now emailed to security@northern.tech.** The
session's real result, though, is that the review gate invalidated the thing we
were about to send — twice — and turned up two further defects.

## Where We Are

**tendcf** `master` at `91b3f42`, clean, pushed. Three commits:

| sha | what |
|---|---|
| `532581a` | B-1/B-2 panel, reconciliation, register rewrite; B-8 filed |
| `91b3f42` | B-8 panel, its defect fixed, open items recorded |

(`9718b41` was 5420's own handoff commit, already present at session start.)

**CFEngine fork** `djbclark/core` at `~/src/cfengine-core`, on
`tendcf-integration` (`775fe5b1d`), built. **Four** branches pushed, each cut
from `master` `17eb78e6d` and independently landable:

- `fix/exec-timeout-commands` — B-1: `26634ac1f`, `943d5371f`
- `fix/timeout-process-group` — B-2: `cb2561584`, `847373cf6`
- `fix/exec-timeout-promise-result` — B-8: `326bcdb8d`, `7a32e3969`
- `tendcf-integration` — merge of all three; **what our builds come from**

**Tracked as [djbclark/core#7](https://github.com/djbclark/core/issues/7)**
(filed at the operator's request at the end of this session): our core branches
are built and tested against an unmerged libntech commit, which qualifies every
measurement taken against this fork and must be resolved before any core branch
is offered upstream. The tracking issue lives on `core` because that is where
the submodule pointer bites. **The operator enabled issues on
`djbclark/libntech` at the end of this session**, so libntech items now get the
same issue-plus-branch shape as core items — B-4 is the next one that needs it,
and P-3 currently exists only as fork PR #1.

`libntech` shows ` M` and **must stay uncommitted**. This is not an external
rule — earlier notes (including 5420) asserted it as "required" without saying
whose requirement it was, and the operator called that out. The real reason,
established this session: the submodule checkout is at `dc85a6f` ("Handle
digest initialization failure when hashing"), **our own P-3 fix**, which exists
only on `fork/silent-digest-failure` and is not upstream. `cfengine/core`
records `5b5d04e1`. Committing the bump would put an unresolvable submodule
reference into every core branch we offer upstream.

**Email sent** — Gmail message id `1a00d22ac0d46c9b`, to
security@northern.tech, one message covering B-1, B-2 and B-8.

## What We Tried

### 1. Both review CLIs silently ate the prompt

`grok -p --always-approve "…"` and `gemini -p --dangerously-skip-permissions "…"`
both failed: in each, `-p` takes the **prompt as its value**, so the next flag
was consumed as the prompt and the real prompt was dropped. Both "completed" in
seconds looking like successful runs. Fix: bind the prompt directly to `-p`, or
use `grok --prompt-file`. **A zero-cost completion is the signature of this.**

### 2. A synthetic pty harness that proved nothing

Trying to isolate the SIGTTIN mechanism with a hand-rolled `pty.fork()` +
inner-fork script, both the `setpgid` and non-`setpgid` arms hung, so it
distinguished nothing. Abandoned it and inspected the **real** hang with `ps`
instead, which settled it immediately. Don't rebuild the synthetic harness.

### 3. B-9 — a diagnosis that was refuted by implementing it

Gemini claimed `exec_timeout` never bounds a command that closes its output
because `cf_pclose()` sets `ALARM_PID = -1` (`pipes_unix.c:874`) before
`cf_pwait()`. The clear is real. I built the fix on a branch — and **wall clock
did not change** (10.3s vs stock 10.2s). Branch deleted, nothing filed. The
second `ALARM_PID = -1` at :962 is in `cf_pclose_full_duplex`, not on this path.
**Do not re-derive the ALARM_PID theory.** What survives is the measurement
only; see Evidence.

### 4. Classifying the timeout in the wrong place (50% compliance)

First B-8 draft called `cfPS()` for the timeout *in addition to*
`VerifyCommandRetcode()`, so one promise was classified twice and reported
**50%** compliance. Fixed by replacing the classification inside the
`cf_pclose()` branch rather than adding to it.

### 5. Sampling the timeout flag too early — the defect the B-8 panel caught

Second B-8 draft read `TimeOutHasFired()` when the output read loop ended. The
read loop ends when the command **closes its output**, which it can do long
before it exits, so an alarm firing during `cf_pclose()` was missed. Cursor and
Gemini found this independently; Grok was circling it. Reproduced against my own
patch and fixed in `7a32e3969` by sampling after `cf_pclose()` returns.

### 6. A masked linker error

`make -C cf-agent … | grep error; echo BUILD_OK` printed BUILD_OK over a real
`clang: error: linker command failed`. Cause was a stale `libpromises` after the
merge. **`echo BUILD_OK` after a grep-filtered build reports nothing useful** —
rebuild `libpromises` first after any merge.

## Key Decisions

**B-1's fail-open claim WITHDRAWN.** It does not close the fail-open; it shrinks
the window. The `sleep 5` / `exec_timeout 2` cell flipped only because SIGTERM
now lands before the command finishes. Cursor derived it, Grok measured it, I
re-measured on both builds. Issue #4 corrected in public.

**B-2 gated on an armed timeout** (`847373cf6`). Rejected the original
"structural symmetry" argument as backwards: the timeout path is the only one
that has to kill a tree; the normal path must stay reachable by things that
already kill trees. Rejected redirecting stdin from `/dev/null` (larger
behaviour change, doesn't restore Ctrl-C).

**B-8 filed as a separate item** rather than folded into B-1 — independent
cause, independently landable, and the honest structure for a security report.

**Second opinion required for B-8 too**, even though it was found *by* the
B-1/B-2 panel and the operator had said "just send". Reasoning: the operator's
"just send" answered draft-vs-send, not review-vs-no-review, and sending an
unreviewed fail-open claim immediately after a panel refuted the previous one
would be precisely the failure the rule exists to prevent. The panel then found
a real defect in B-8, so the call paid off.

**Sent one email covering all three, not three emails** — they are one story
about `exec_timeout` and easier to triage together. Operator's rule permits
"each bug, or set of bugs".

**Rejected** cursor's `<stdbool.h>` nit for `timeout.h`: in-tree convention is
that headers assume the includer has `cf3.defs.h`/`platform.h` — `timeout.h`
already used `time_t` that way, as do `locks.h` and `actuator.h`.

## Evidence & Data

**The fail-open, measured on stock 3.27.1 AND master** — `sleep 2.4` under
`exec_timeout => "2"`:

```
verbose: Time out of process 9943
verbose: A: Promise REPAIRED
verbose: A: Aggregate compliance (promises kept/repaired) for bundle 't' = 100.0%
```

Note the outcome is **REPAIRED, not KEPT** (cursor's correction; the accurate
phrase is "reported as compliant"). `ACTION_RESULT_TIMEOUT` is declared at
`verify_exec.c:52` and handled at `:129` but **never returned** — dead enum.

**The SIGTTIN hang B-2 introduced** (this session's own finding; no panel got
it). Under a pty, `sh -c 'read x; echo GOT-$x'`, **no `exec_timeout` at all**:

| build | result |
|---|---|
| stock 3.27.1 | 0.1s, prints `GOT-hello` |
| B-2 as filed | **hangs indefinitely** |

```
  PID  PPID  PGID TPGID STAT COMMAND
 2669  2667  2669  2669 Ss+  cf-agent -KI -f ...
 2710  2669  2710  2669 T    /bin/sh -c read x; echo GOT-$x
```

`PGID`=own pid, `TPGID`=agent's group, `STAT T`=stopped.

**Final matrix, integration build, `exec_timeout => "2"`:**

| payload | wall | compliance | timeout reported |
|---|---|---|---|
| `exec 1>&- 2>&-; sleep 10; exit 0` | 12.1s | 0.0% | yes |
| `sleep 2.4; exit 0` | 4.6s | 0.0% | yes |
| `sleep 30; exit 0` | 4.6s | 0.0% | yes |
| `trap '' INT TERM; sleep 30` | 4.6s | 0.0% | yes |
| `sleep 0.5; exit 0` | 1.1s | 100.0% | no |
| `sleep 0.5; exit 3` | 1.1s | 0.0% | no |
| `sleep 0.5; exit 0`, no timeout | 1.0s | 100.0% | no |

Zero orphans. Before the series, row 2 was 100% and `sleep 30` took 30.3s
leaving an orphan.

**OPEN, mechanism NOT established.** Row 1 above still takes ~12s, and **stock
3.27.1 takes 10.2s** for the same policy — so `exec_timeout` does not bound wall
clock for a command that closes its output before exiting. Pre-existing
upstream, not ours. Disclosed in the email as an observation only. See What We
Tried §3 for the refuted theory.

**Regression, every branch and the merge:** `tests/unit` — *all 68 behaved as
expected, 4 expected failures*, exit 0, identical to baseline.
`process_terminate_unix_test` 6/6.

**tendcf gates against the fork build:** `schema-lint: OK` (8 schemas, 59
negative, 6 byte-class, 27 projection); `xref_lint` 0 findings, 584 sections
across 96 documents; `flag_coverage` 21/21.

**Panel verdicts:**

| item | cursor | gemini | grok |
|---|---|---|---|
| B-1 | ship with changes | ship with changes | ship as is (filing is what's wrong) |
| B-2 | ship with changes | **do not ship** | ship with changes |
| B-8 | ship with changes | **do not ship** | (still running at session end) |

All reviewers who reported on B-8 rated it **security@** unprompted.

## Operator Feedback

- **"1 just send"** — do not prepare drafts for approval; send directly. (Asked
  in the context of the security@ emails.)
- **"If you find other bugs in the process of fixing bugs, please do not
  discuss them, but keep going until you find fixes for them, or at minimum
  record them so we can look at them later."** Stop narrating incidental
  findings; fix or record.
- **Challenged "libntech still uncommitted as required"** — "Who required
  that?" Correct challenge: it was inherited phrasing from 5420 stated as an
  external mandate. Say whose requirement a constraint is, or give the actual
  reason. Reason now recorded in the register.
- Carried from 5420 and still live: fix every bug we find; maintain the fork as
  a staging area, not a product; regression-test after each fix; three channels
  per bug (fork branch, fork artifact, email); `CONTRIBUTING.md` process is not
  followed but its style/hygiene is; if in doubt, security@.

## Where We're Going

1. **THE NEXT ACTION — collect Grok's B-8 opinion and fold it in.** It was
   still building a scratch clone of `326bcdb8d` at session end, i.e. the
   version **before** `7a32e3969`, so it will most likely re-report the
   already-fixed early-sample defect. Check
   `docs/architecture/upstream-opinion-b8-grok-2026-08-16.md`; if it landed,
   add anything new to issue #6 and to the register. If it found nothing new,
   say so and close the panel out.
2. **Write the acceptance tests all three reviewers asked for** — two shapes:
   `sleep 2.4; exit 0` and `exec 1>&- 2>&-; sleep 10; exit 0`, both under
   `exec_timeout => "2"`, asserting compliance 0% and a `repair_timeout` class.
   `CONTRIBUTING.md` asks for them and their absence is the top stated gap in
   the email. Existing `exec_timeout` usage in `tests/acceptance/` is only an
   unrelated 30s bound in `10_files/13_file_dir/001.cf`.
3. **Close the two accepted-but-unfixed items on #5**: unchecked
   `setpgid()`/`getpgid()` returns (silent no-op on failure), and the
   parent-side `setpgid(pid, pid)` POSIX both-sides pattern.
4. **Pin the mechanism for the open observation** (Evidence, last bullet)
   before filing anything about it. The ALARM_PID theory is refuted — start
   somewhere else.
5. **Work [djbclark/core#7](https://github.com/djbclark/core/issues/7)** — its
   first unchecked box is the live one: confirm #4/#5/#6 build and pass against
   **stock** libntech `5b5d04e1`, not only against our patched `dc85a6f`. Not
   yet done, and it gates offering those branches upstream cleanly.
6. **Watch for a reply from security@northern.tech** and answer it. Offered:
   PRs against cfengine/core, patches by email, or a tracker. Also offered to
   test on Linux.
7. **Then the remaining surveyed bugs — ALL NOW FILED as fork issues** at the
   operator's request at the end of this session, so each has a tracking
   artifact and none needs re-deriving from the survey. Each still needs a fix,
   its own second opinion, and then its email:
   - **B-5a** [core#8](https://github.com/djbclark/core/issues/8) — CMDB
     rejection names no key. Highest correctness return and nearly free: both
     `JsonWalk` callbacks already take a `void *data` declared `ARG_UNUSED`
     (`cmdb.c:70,78`), and the pattern repeats at `:281` and `:384`.
   - **B-5b** [core#9](https://github.com/djbclark/core/issues/9) — one bad key
     drops every variable. Filed separately because it is a judgement call
     about behaviour, not an obvious defect.
   - **B-4** [libntech#2](https://github.com/djbclark/libntech/issues/2) — JSON
     reals truncated to 2dp, including through mustache, so it corrupts
     rendered config. `StringFromDouble` `%.2f` (`string_lib.c:922`) vs
     `JsonRealCreate` `%.4f` (`json.c:1664`).
   - **B-6** [core#10](https://github.com/djbclark/core/issues/10) — `eval()`
     returns `%lf` (`evalfunction.c:7643`).
   - **B-7** [core#11](https://github.com/djbclark/core/issues/11) — dotted
     CMDB keys become scope paths. **Warn only; do not change behaviour.**
   - **B-3** [core#12](https://github.com/djbclark/core/issues/12) — no
     `process_darwin.c`. Platform-support work, not a bug fix, but it would
     flip existing `process_test` XFAILs to passing.
   - **P-3** now also has an issue,
     [libntech#3](https://github.com/djbclark/libntech/issues/3), alongside its
     PR #1, since issues are enabled on that fork now.
8. **Then E-9 and `services:`** — the operator's stated goal for this stretch;
   E-9 (5 MiB `HOST_SPECIFIC_DATA_MAX_SIZE` hard load failure) has never been
   re-measured.
9. **Then the generic bundle** — still the only live bullet in §11, mechanics
   already measured in 5420.
10. Unrelated, carried: confirm `track-issue-activity.yml`'s Discussion path
   fires in site-djbclark.

**Workflow rules that earned their place this session:** rebuild `libpromises`
before `cf-agent` after any merge, and never trust `echo BUILD_OK` after a
grep-filtered build; establish a baseline by stashing before blaming a test
failure on your patch; bind review-CLI prompts directly to `-p`; and measure a
claimed mechanism before filing it — two theories died that way this session.

## Quick Start

```bash
# State
cd ~/src/tendcf && git log --oneline -3 && git status -s
cd ~/src/cfengine-core && git branch -v | grep -E 'fix/|tendcf-int' && git status --porcelain
#   ' M libntech' is EXPECTED and must stay uncommitted (points at our
#   unmerged P-3 fix dc85a6f; core records 5b5d04e1).

# Did grok's B-8 review land?
ls ~/src/tendcf/docs/architecture/upstream-opinion-b8-*.md

# The gate document and the panel
sed -n '1,60p' ~/src/tendcf/docs/architecture/upstream-register.md
sed -n '1,40p' ~/src/tendcf/docs/architecture/upstream-b1-b2-reconciliation-2026-08-16.md

# The four filed items
for n in 4 5 6; do gh issue view $n --repo djbclark/core --comments | head -30; done

# Rebuild (libpromises FIRST after any merge)
cd ~/src/cfengine-core && make -C libpromises -j8 && make -C cf-agent -j8

# Regression — baseline by stashing before blaming your patch
cd ~/src/cfengine-core/tests/unit && ./process_terminate_unix_test    # expect 6/6
cd ~/src/cfengine-core/tests/unit && make check 2>&1 | tail -4        # expect "All 68 ... 4 expected failures"

# The behavioural matrix (throwaway workdir; needs bin/cf-promises symlinked in)
#   see docs/handoffs/ HANDOFF 16b8 "Evidence & Data" for expected numbers

# tendcf gates
cd ~/src/tendcf && bin/schema_lint.py && bin/xref_lint.py && bin/flag_coverage.py
```
