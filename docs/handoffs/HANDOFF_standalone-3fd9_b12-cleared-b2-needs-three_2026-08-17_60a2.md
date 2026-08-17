---
schema_version: 1
handoff_id: 60a2
parent_handoff_ids: [5749]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 5dcaffc5a9ce6344956a25820fd6d6155a6310ca
created_at: 2026-08-17T17:50:25-04:00
writer: claude-code
---

# Handoff — B-12 cleared by panel; B-2 merge needs three bounded fixes

## The Goal

Continue the register in the order set by `5749`: **B-2/CFE-4729**, then
**B-12/CFE-4723**, then **CFE-4727**. Operator added two standing constraints
for this session:

1. **Every item gets at least two non-Claude AI reviews *plus* fable-deep.**
2. **Farm work out and parallelize.**

Later refined (see Operator Feedback): *"we should only get as many second
opinions as we need for you to feel confident; we don't always need to use 6."*

## Where We Are

Two items are written, independently verified, and panel-reviewed. **Nothing
has been offered upstream this session** — no PR, no ticket, no push to any
fork. All three worktrees are clean.

| Item | Worktree | Branch | Head | State |
|---|---|---|---|---|
| B-12 / CFE-4723 | `/Users/djbclark/src/core-b12` | `fix/default-route-lowest-metric` | `3d10206ee` | **Panel-cleared, ready to offer** |
| B-2 / CFE-4729 | `/Users/djbclark/src/core-b2merge` | `fix/timeout-process-group-merged` | `3d8e90d68` | **Blocked — 3 required changes** |

`tendcf` itself is at `5dcaffc` on `master`, with 11 untracked files in
`docs/architecture/` (2 frozen briefs + 9 reviews) pending their own commit.

The five older PRs remain OPEN / MERGEABLE with **zero reviews and no
maintainer response** as of 2026-08-17: `cfengine/core#6299`, `#6300`, `#6293`,
`#6294`, `NorthernTechHQ/libntech#293`, `#294`. (`#6293`/`#6294` carry 5 and 7
comments; `#293`/`#294` carry 1 each — the known mender-test-bot CI noise, not
actionable.)

### The inherited blocker was already gone

`5749` listed "FABLE IS UNREACHABLE FROM THIS SESSION" as the top blocker and
told the next session to `cswap switch 2` first. That had already happened —
this session started on `djbclark@gmail.com` with Fable at 67%. **Retest an
inherited blocker before repeating it** (the same lesson `9997` recorded twice).

## What We Tried

Failures and near-misses, chronological. The reviewer-roster ones are the
expensive ones and are the main reason this document exists.

1. **`codex` is dead until 2026-08-20.** `codex exec` returns
   `ERROR: You've hit your usage limit… try again at Aug 20th, 2026 5:00 AM`.
   It was the intended strongest independent non-Claude reviewer.

2. **The `gemini` CLI is not Gemini — it is Claude Sonnet 4.6.** Asked to name
   its own model, `gemini -p` replied `PONG Claude Sonnet 4.6 (Thinking)`. The
   binary at `~/.local/bin/gemini` (v1.1.13) is the **same build as `agy`**
   (`/opt/homebrew/bin/agy`, also v1.1.13), and with no `--model` it runs
   Claude. `agy models` lists `claude-sonnet-4-6` among its models; `aiuse`
   bills `agy` under two scopes, `agy/gemini` and `agy/claude,gpt`.
   **Consequence: the 2026-08-16 B-1/B-2 panel and the 2026-08-17 B-10/B-4
   panel were probably two non-Claude reviewers plus a Claude one, not three.**
   This also explains the recorded "gemini rubber-stamps" behaviour better than
   model quality did — it was Claude grading Claude-authored patches.
   Correction ingested to Hindsight.

3. **`cline` died mid-review on billing.** `Insufficient balance. Your Cline
   Credits balance is $-0.28`. The default `cline` provider bills pay-as-you-go
   credits; ClinePass was **not linked** (only provider `cline` appeared in
   `~/.cline/data/settings/providers.json`) despite `aiuse` showing a
   `clinepass` row at 0% used. Operator linked it mid-session; `cline --json`
   then reported `cline-pass/kimi-k3`. Kimi was doing real work when it died —
   it had independently reached the same question about whether `[[:xdigit:]]+`
   admits a `-` sign that fable later settled.

4. **`opencode` has two plans in one list and BOTH refused.** `opencode/…` is
   the "zen" pay-as-you-go plan (empty); `opencode-go/…` is the subscription.
   Operator pointed this out after the first failure. **Both prefixes failed
   identically** with `Insufficient balance` naming the *same* workspace id in
   both cases, so the block is at workspace level, not plan level. Two attempts,
   then stopped rather than keep chasing. Resolving it needs billing attention
   on the opencode workspace; nothing fixable from the CLI.

5. **`aiuse` rows are not proof a CLI can run.** It showed `clinepass` 0% used
   while ClinePass was unlinked, and `oc-go` with `$9.81 unused` while the
   workspace refused all work. Verify by making the tool actually answer.

6. **The `-p` flag trap, and it INVERTS between CLIs.** In `grok` and `agy`,
   `-p` takes the prompt as its *value*, so `-p --some-flag "…"` eats the flag
   and drops the prompt (this produced two zero-cost "reviews" on a prior
   panel). In **`cursor-agent`, `-p` is a BOOLEAN (`--print`) and the prompt is
   positional and must come last.** Getting either backwards yields a run that
   looks like a completion.

7. **A first `grok` launch failed with `Error: Device not configured (os error
   6)`** — that was interactive mode with no TTY. `grok -p "…"` works.

8. **The B-12 authoring agent ended its turn twice waiting on a build**, once
   after 592s and once after 712s, stalling the item. Fixed by instructing it to
   run builds in the **foreground** with an explicit long timeout (the Bash tool
   accepts up to 1800000 ms) rather than backgrounding and yielding.

9. **The B-12 agent's own first discrimination run was invalid and it said so.**
   It reverted the *whole* `unix_iface.c`, which removed the new helper, so the
   test failed to **compile** and the following run hit a **stale binary** and
   "passed". Its per-stage rc discipline caught it. This is the exact near-miss
   `f1a4` recorded; the fix is a one-line revert plus distinct output names.

10. **Reviewer probes leaked untracked files into the reviewed worktrees** —
    `test_getpgid`, `test_getpgid.c` in `core-b2merge`; `unix_iface_test.xml` in
    `core-b12`; `unix_iface_test.xml`, `xml_tmp_case`, `xml_tmp_suite` in
    `tendcf` root. None reached a commit, but this is exactly the shape of
    `9997`'s `git add -A tests` near-miss. All removed; all three trees verified
    clean.

## Key Decisions

- **Excluded `cursor-agent` from the panel as a *Grok* seat**, because it
  identifies as Grok 4.6 and would have duplicated the `grok` seat rather than
  adding a family. Later **used it anyway, pinned to `gpt-5.6-sol-xhigh`**, to
  fill the OpenAI seat that `codex` and `opencode` could not. Pinning is what
  makes the same CLI a different reviewer.
- **Pinned the model on every seat, always.** Written into the scripts with the
  reason. Rejected: relying on defaults — that is precisely how a Claude model
  sat on two prior panels uncounted.
- **Graded reviewers by falsifiable artifact, not wall-clock.** Gemini 3.1 Pro
  returned in 81s, matching the recorded rubber-stamp profile, but its
  trap-control section named `/tmp/unix_iface_test_rc.txt`; that file exists,
  contains `RC=0`, and is timestamped inside the panel window. It really ran the
  test — the short time is explained by an already-built tree. **Wall-clock is a
  weak signal; a named, checkable artifact is the real gate.**
- **Cut the panel back mid-flight on operator feedback**, from 7 seats to 4
  (B-12) and 5 (B-2), killing 4 running reviewers. Rationale: B-12's confidence
  was already settled once two labs independently refuted its sharpest
  uncertainty; further collection would have cost more in careless reading than
  it bought in coverage.
- **Deferred CFE-4727** rather than parallelizing it. It is the umbrella
  "termination half" ticket and its residual defect is the `ALARM_PID` window in
  `cf_pclose()` — the same signal path B-2's merge rewrites. Two agents editing
  that path concurrently would conflict.
- **Kept the merge commit faithful.** The author put the required
  `setpgid`/`getpgid` failure logging in a *separate* commit (`ade76f616`) so
  `8793f3747` remains a pure union + conflict resolution. Correct call; preserve
  it.

## Evidence & Data

### B-12 — commit `3d10206ee`

Defect confirmed at `17eb78e6d`: `libenv/unix_iface.c` declares
`long lowest_metric = 0;` and never assigns it, so once `default_route` is
non-NULL the guard is `metric < 0`, false for every real metric. Present since
the loop's introduction in 2016 (CFE-1991, first released 3.9.0).

Fix: selection loop lifted into static helper `FindLowestMetricDefaultRoute()`;
one behaviour change (record the selected metric). Ties stay first-wins. New
`tests/unit/unix_iface_test.c`, 7 cases, `#include <unix_iface.c>` per the
`sysinfo_test` precedent, `if !NT` guarded. Diffstat: 3 files, +185 / −23.

**Re-verified by me, not taken from the report:**

- Fixed tree: `make unix_iface_test` rc 0; run rc 0; **All 7 tests passed**.
- Deleting **only** `lowest_metric = metric_value;` (line 1434): build rc **0**
  (a real behaviour difference, not a compile failure), run rc **1**, exactly
  `test_lowest_metric_last` fails with `"192.168.0.1" != "192.168.0.3"` — the
  first route winning instead of the lowest.
- Restore byte-identical, sha256
  `4e6bd587940c991015051581264b950180de547f59a537889d6108ed9359e843` before and
  after — **matches the agent's independently reported hash**. Rebuild rc 0,
  7/7 pass.
- `test_lowest_metric_first` is a deliberate control: it passes even against the
  unfixed code.

Agent's own numbers: baseline `All 68 tests behaved as expected (4 expected
failures)` → post-fix `All 69`, 2 pre-existing compiler warnings unchanged
(`evalfunction.c:674`, `variable.c:296`), 0 new.

Hex-vs-decimal question **resolved, no second defect**: Linux v6.9
`net/ipv4/fib_trie.c` prints the metric (`fi->fib_priority`) with `%d` —
decimal, matching CFEngine's existing `hex_mode=false` parse. The
`[[:xdigit:]]+` capture is merely over-permissive. Deferred to a cosmetic patch,
keeping this to one behaviour change.

### B-2 merge — commits `8793f3747`, `ade76f616`, `3d8e90d68`

Branched from `0ab083c4d` (live head of `cfengine/core#6299`), merging
`847373cf6`. `git merge-tree` rc 1; conflicts in exactly `libpromises/timeout.c`
and `libpromises/timeout.h`. **`cf-agent/verify_exec.c` auto-merged textually**
— the dangerous one.

Resolution: `SetTimeOut()` sets all three flags; `TimeOut()` sets `FIRED`,
clears `ARMED`, sets `SIGNALLED` + group kill inside `ALARM_PID != -1`;
`ClearTimeOut()` clears **only** `ARMED`.

- Build rc 0/0, **2 warnings byte-identical to the #6299 baseline's 2**, zero new.
- Acceptance: **6/6 pass in 65s** (five from #6299 plus new
  `timeout_kills_descendants.cf`).
- Discrimination, both directions (the complementary one was run by the fable
  reviewer, not the author): minus `setpgid` hunk → FAIL 32.0s; minus group-kill
  hunk → FAIL 36.7s; restored byte-identical (sha256
  `7af027630c409cbd2b07c4e22c645c3d1e777231afd75bf58c46bf440a6ec4a6`) → Pass
  14.1–20s.
- The unconditional `setpgid(0,0)` the 2026-08-16 panel refused is **not**
  present; the child calls `setpgid` only under `if (TimeOutIsArmed())`
  (`pipes_unix.c:254`).

### The panel — 9 reviews, all in `docs/architecture/`

Verified roster (each CLI was made to name its own model):

| Lab | CLI | Invocation |
|---|---|---|
| xAI | `grok` | `grok -p "<prompt>" --reasoning-effort high` |
| Google | `agy` | `agy -p "<prompt>" --model gemini-3.1-pro-high` |
| DeepSeek | `cline` | `cline --auto-approve true --thinking high -m cline-pass/deepseek-v4-pro` |
| Moonshot | `cline` | `-m cline-pass/kimi-k3` |
| Alibaba | `cline` | `-m cline-pass/qwen3.8-max` |
| OpenAI | `cursor-agent` | `cursor-agent -p --force --model gpt-5.6-sol-xhigh "<prompt LAST>"` |
| Anthropic | `fable-deep` | Agent tool, `model: 'fable'` — verified `claude-fable-5` in trace |

**B-12 — unanimous clear.** Grok "Offer upstream"; fable "ship as is"; DeepSeek
V4 Pro "APPROVE, one advisory note"; Gemini 3.1 Pro no required changes.

The value was **convergence on mechanism, not on verdict**: fable and DeepSeek
independently found that a metric ≥ 2^31 prints with a leading `-`, which
`[[:xdigit:]]+` cannot match, so `StringCaptureData()` rejects the whole line
and the route is dropped *before selection ever sees it*. That **refutes the
author's own sharpest uncertainty (#4)** — the feared "negative metric beats
every normal route" is unreachable from real kernel output, and the failure mode
is identical pre- and post-patch. Grok said the same framing is wrong "in two
independent ways."

fable also found the FIB alias list is priority-ascending within a TOS class, so
`/proc/net/route` already lists ordinary default routes in ascending metric
order — meaning the bug was invisible on most real hosts and the patch's delta
is confined to TOS-tagged or synthetic tables. That *strengthens* the first-wins
tie-break. It further cleared two hidden risks: no ODR/duplicate-symbol hazard
from the `#include <unix_iface.c>` pattern (measured zero symbol overlap), and
the acceptance fixture `proc-net.cf` has exactly one active default route so the
committed `expected.json` cannot break.

**B-2 — do not offer.** Grok "would not offer as it stands"; fable "ship with
changes" (3 required); GPT-5.6 Sol "Request changes; do not offer this branch
upstream yet"; DeepSeek "the merge IS the right place to fix it".

Three independent labs converged on the **MinGW break** as blocking. Grok's
formulation is the sharpest and rebuts the author's own counterargument:
`timeout.c` is compiled on MinGW, the merge adds `getpgid()` and
`kill(-pid, SIGKILL)` with no `#ifndef __MINGW32__`, and *that is not the same
as master's existing `GracefulTerminate()` call* — master survives NT only
because its externals are already externally provided. fable added the decisive
tree evidence: every existing raw `kill()` in NT-compiled code is already fenced
`#ifndef __MINGW32__`.

Reassuringly, Grok **tried to break the resolution and could not**: it could not
make `ClearTimeOut()` eat `TIMEOUT_FIRED` on any path that reports a timeout
outcome, nor make the `pgid == ALARM_PID` guard fire a negative kill at the
agent's own group. The merge *shape* is right; the defects are at the edges.

New pre-existing defects surfaced by fable, advisory only:
- `nfs.c:1434` / `:1459` arm a timeout with **no disarm ever** — a success-path
  leak the PR walks past while converting nfs.c's other disarm sites.
- `ShellCommandReturnsZero()` (`unix.c:225`) reaps its child while leaving
  `ALARM_PID` set — **the one path where the earlier panel's
  unreaped-zombie/PID-recycling argument fails**, escalating post-merge to a
  possible group SIGKILL of a recycled leader.
- `RepairExec()` has three early returns that leak an armed alarm.

## Operator Feedback

- **"Remember for each item we want at least 2 reviews by non-claude AIs and
  also fable-deep. Also remember you can farm stuff out and parallelize."**
- **"for gemini-3.1-pro `agy` is probably preferable. for grok-4.6 either `grok`
  or `cursor-agent` are likely preferable."**
- **"Note there is a new provider, cline with clinepass"** + the ClinePass model
  roster (Moonshot Kimi K3/K2.7/K2.6; DeepSeek V4 Pro/Flash; Qwen 3.8 Max / 3.7
  Max / 3.7 Plus; GLM-5.2 / 5.3; MiMo V2.5 Pro / V2.5; MiniMax M3).
- **"opencode is confusing, they combine zen (paid) and go (subscription) in
  same list… The go ones are the ones we want."**
- **"Note cursor-agent has gpt-5.6 sol and very low usage."**
- **"BTW we should only get as many second opinions as we need to for you to
  feel confident; we don't always need to use 6."** — Right-size the panel to
  residual doubt, not to available options.

## Where We're Going

1. **THE NEXT ACTION — apply B-2's three required changes** in
   `/Users/djbclark/src/core-b2merge` on `fix/timeout-process-group-merged`.
   New C in a signal path, so `fable-deep` with `model: 'fable'`.
   1. **`#ifndef __MINGW32__` guard** around the `getpgid()` / `kill(-pid,
      SIGKILL)` block in `TimeOut()` (`libpromises/timeout.c`). Blocking, and
      confirmed by three independent labs. Match the fencing style already used
      for every other raw `kill()` in NT-compiled code.
   2. **`TIMEOUT_ARMED` → `volatile sig_atomic_t`.** It is written from the
      `SIGALRM` handler and sits beside two `volatile sig_atomic_t` siblings.
      "Already panel-reviewed" does **not** transfer — the earlier panel reviewed
      B-2 standalone, where those siblings did not exist; the merge creates the
      inconsistency. Note the honest counterweight fable found: house style is
      actually plain-bool handler flags (`signals.c` `PENDING_TERMINATION`), and
      #6299 introduced the tree's first `sig_atomic_t`. Required for coherence,
      not because it is a live bug. Verify it cannot affect `cf_popen()`'s child
      gate.
   3. **A unit test pinning the `ClearTimeOut()` contract.** fable *measured*
      that a flag-clearing variant passes all six acceptance tests (6/6, 61s), so
      the invariant the whole merge rests on is currently unpinned. It proved it
      is pinnable in ~50 lines via `tests/unit` with a probe calling public
      `TimeOut()` directly — PIN-PASS on the merged lib, PIN-FAIL on the
      flag-clearing variant.
2. **Re-verify B-2 after the fixes** (build, 6/6 acceptance, both discrimination
   directions, sha256 restores) and re-run a *small* panel — 2 seats is enough
   given the changes are bounded and the shape is already cleared.
3. **Offer B-12 upstream.** It is panel-cleared. Include the agreed cover-letter
   note: high `u32` metrics printed negative by `%d` are silently dropped by the
   regex, pre-existing and orthogonal, not addressed here. Also correct the
   commit message's implied blast radius per Grok — the kernel already emits
   ascending metrics, so the field impact is smaller than "CFEngine picks the
   wrong gateway" suggests. Fork issue `djbclark/core#14`, ticket CFE-4723.
4. **CFE-4727** — the exec_timeout termination half. Still unwritten. **Must
   start from the ALARM_PID theory; its refutation is retracted.** The residual
   defect is the window where `cf_pclose()` clears `ALARM_PID` before waiting, so
   an alarm firing there takes the `else` branch and the child is never
   terminated. Do this *after* B-2 lands — same signal path.
5. **Consider filing the two new advisory defects** fable found (`nfs.c` arm
   with no disarm; `ShellCommandReturnsZero()` reaping while `ALARM_PID` set).
   The second matters beyond this patch — it is a counterexample to reasoning a
   previous panel accepted as settled.
6. **B-10's core half (CFE-4725)** still pending on `#294` merging and core
   bumping its libntech submodule (`djbclark/core#7`). Do not offer before then.
7. **B-14 / CFE-4731** still filed and unpatched; any fix must be coordinated
   with `#293`'s decoder.
8. Housekeeping, not urgent: `git worktree remove` for `core-p1`, `core-p2`,
   `libntech-b4`, `libntech-jsonstr`; `core-json` needs `make clean` first. Keep
   `core-acceptance`, `libntech-fixes`, `core-b12`, `core-b2merge`.

## Quick Start

```bash
# Verify the two worktrees are where this handoff left them
git -C /Users/djbclark/src/core-b12      log --oneline -1   # 3d10206ee
git -C /Users/djbclark/src/core-b2merge  log --oneline -1   # 3d8e90d68
git -C /Users/djbclark/src/core-b12      status --porcelain # empty
git -C /Users/djbclark/src/core-b2merge  status --porcelain # empty

# Read the panel before acting on it
ls /Users/djbclark/src/tendcf/docs/architecture/upstream-opinion-b2merge-*.md
sed -n '/^## Verdict/,/^##[^#]/p' \
  /Users/djbclark/src/tendcf/docs/architecture/upstream-opinion-b2merge-grok-2026-08-17.md

# The frozen briefs (reusable; fill the "author's uncertainties" section)
#   docs/architecture/UPSTREAM-B2-MERGE-REVIEW-BRIEF.md
#   docs/architecture/UPSTREAM-B12-REVIEW-BRIEF.md

# Panel launchers, all model-pinned. Scratchpad of THIS session:
#   $S = /private/tmp/claude-501/-Users-djbclark-src-tendcf/\
#        b1a927fc-8eb9-48dc-81bd-1f2a36f70b30/scratchpad
#   $S/run_panel.sh <slug> <brief>            # grok + agy(gemini) + cline
#   $S/run_clinepass_reviewer.sh <slug> <brief> <model-id> <who>
#   $S/run_cursor_reviewer.sh   <slug> <brief> gpt-5.6-sol-xhigh gpt56sol
# Copy these forward; they encode the -p flag traps and the pinning rule.

# Build + test recipes (edit W= and L= before use)
#   $S/build_b8.sh  $S/run_b8_tests.sh  $S/build_b2m.sh

# PR watch — gh pr view uses graphql; on 503 use gh api repos/OWNER/REPO/pulls
for p in 6299 6300 6293 6294; do gh pr view $p -R cfengine/core \
  --json state,mergeable,reviews,comments; done
for p in 293 294; do gh pr view $p -R NorthernTechHQ/libntech \
  --json state,mergeable,reviews,comments; done
```

**Build traps that still bite** (all re-confirmed this session): never read an
rc through a pipe; `--bindir` is wrong for an in-tree build (pass `--agent=` /
`--cfpromises=` / … explicitly, and treat an all-fail-in-2s run as a harness
bug); `cf-promises` in the build tree is a **libtool wrapper**, use
`cf-promises/.libs/cf-promises`; a wall-clock ladder measurement needs a
**single-process** command or B-2's own defect dominates the timing.

**Reviewer traps:** pin every model; `-p` takes the prompt as its value in
`grok`/`agy` but is a **boolean** in `cursor-agent` (prompt positional, last);
grade a review by whether the artifact its trap-control section names actually
exists, not by wall-clock.
