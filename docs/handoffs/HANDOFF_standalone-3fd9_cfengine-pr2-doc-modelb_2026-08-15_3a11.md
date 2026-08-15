---
schema_version: 1
handoff_id: 3a11
parent_handoff_ids: [ac65]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: b46d6e91e78aac596e4844849c850b4c7e367550
created_at: 2026-08-15T16:50:17-04:00
writer: claude-code
---

# Handoff — CFEngine PR 1 + PR 2, guide/map Model B alignment, DOC-4

## The Goal

Two threads, both live:

1. **Upstream CFEngine.** tendcf's consent layer needs the simulated change
   set as *data*, not prose. Plan: two PRs to `cfengine/core` from the
   temporary fork `djbclark/core` (`~/src/cfengine-core`). PR 1 retains the
   changes chroot (the would-be **bytes**); PR 2 renders the change set as
   JSON (the would-be **change set**). They are complementary and upstream
   will ask why both — that argument must be made explicitly.
2. **tendcf docs.** Decision E1 is settled (Model B). The guide, map, and
   paper had to catch up, plus a naming decision (DOC-4).

**Both PRs are now prototyped and committed locally. Neither is pushed and
neither has a PR — that is correct and intended.**

## Where We Are

### Git state, all repos

| repo | path | branch | head | dirty |
|---|---|---|---|---|
| tendcf | `~/src/tendcf` | master | `b46d6e9` | clean, pushed |
| cfengine-core | `~/src/cfengine-core` | `simulate-json` | `8c3918cc` | see below |
| cfengine-core | (same) | `simulate-keep-chroot` | `5dbd295f` | PR 1, complete |

`cfengine-core` master is `17eb78e6d`. Both PR branches are cut from it
independently — PR 2 is **not** stacked on PR 1, because upstream wants two
separate PRs.

At handoff time `~/src/cfengine-core` had uncommitted work in progress from
an agent still running (below): `M tests/unit/Makefile.am`,
`?? tests/unit/simulate_mode_test.c`, `?? docs/PR2-REPORT.md`.

### tendcf commits this session

- `2cc5a1e` — guide + map aligned on Model B; two reconciliation items closed.
- `b46d6e9` — DOC-4: `$defs/capability_token` → `$defs/token`.

Both pushed to `origin/master`.

### RUNNING SUBPROCESSES — read this before doing anything else

Four Herdr panes in workspace **w1H** are or were live. **Re-establishing
control is not a problem** — Herdr panes are durable and survive this
session ending. Enumerate with `herdr agent list`, then drive with
`herdr agent prompt <name-or-pane-id> "..."`. In-process `Agent` subagents
would NOT survive, but none are running.

| pane | name | kind | state at handoff | what it owes you |
|---|---|---|---|---|
| `w1H:pN` | **(UNNAMED — use the pane id)** | claude | **working** | PR 2 unit tests + `docs/PR2-REPORT.md` |
| `w1H:pP` | `schema-codex` | codex | **done** | has NOT written its opinion file yet |
| `w1H:pQ` | `schema-gemini` | gemini | **blocked** | needs input to proceed |
| `w1H:pD` | (UNNAMED) | claude | working | the session writing this handoff |

`w1H:pN` runs on **account 2 (djbclark@gmail.com)** via `cswap run 2`, in an
isolated `CLAUDE_CONFIG_DIR` profile. Its transcripts are at
`~/.claude-swap-backup/sessions/2-djbclark_gmail.com/projects/`, **not**
`~/.claude/projects/`. Verify its model/effort there.

## What We Tried

Chronological, including what failed — this is the expensive part to
rediscover.

1. **Guessed the Hindsight hooks-disable config key.** Wrote
   `"hooksDisabled": true` into `~/.hindsight/coding-agent.json`.
   `hindsight_diagnose` showed `hooks_disabled: false` — the key does not
   exist. There is **no hooks-only config key**; `disabled` in that file
   kills the MCP tools too. The only targeted switch is the env var
   `HINDSIGHT_DISABLE_HOOKS`, checked by `runHook()` in `claude-hook.js`
   *before any I/O*. Reverted the bogus key.
2. **Ran two large doc agents on the account I was orchestrating from.**
   The guide agent (127K tokens) and map agent (138K) put **account 1
   (mit.edu) at 5h 100%**, which then **killed the DOC-4 agent mid-run** with
   "You've hit your session limit". It left a half-applied rename that had to
   be finished by hand. Lesson: budget the orchestrating account's window
   against the agents you launch on it.
3. **Created a Herdr tab in the wrong workspace.** `herdr tab create`
   without `--workspace` uses the **UI-focused** workspace (w1K), not the
   caller's. Closed and recreated with `--workspace w1H`. Always pass
   `--workspace`.
4. **Assumed `cswap switch` was the way to move PR 2 onto the Fable
   account.** Operator corrected: `cswap run 2` is better — it launches with
   an isolated `CLAUDE_CONFIG_DIR` and leaves every other session alone.
   `switch` is global and would have moved the other three sessions onto
   account 2, where they would have eaten the very 5h window PR 2 needed.
5. **Planned to wait until 16:11 to start PR 2.** Operator correctly pointed
   out the remaining ~10% of account 2's window was use-or-lose. Started
   early; PR 2 hit the wall, took a `continue`, and resumed cleanly on the
   fresh window.

## Key Decisions

### CFEngine PR 1 — `--simulate-keep-chroot=PATH` (commit `5dbd295f`)

- **Accumulation:** dissolved by *requiring* an explicit destination. Nothing
  is ever retained at the PID-named statedir path, and the caller knows the
  path without parsing log output — the property tendcf needs. *Rejected:* a
  bare boolean (re-creates both accumulation and log-parsing discovery), and
  relocate-on-exit (destroys the previous run's artifact, races concurrent
  agents).
- **Security:** opt-in only, `mkdir(path, 0700)` on a must-not-exist
  directory (so permission-mirrored copies of sensitive files cannot land
  somewhere pre-prepared or mix with stale content), `FatalError` rather than
  silent fallback, `LOG_LEVEL_NOTICE` at end of run. Windows: 0700 is a
  no-op — POSIX-only guarantee, flagged as residue.
- **Interface:** the retained **tree** is the artifact of record; the four
  record files stay internal and unstable, and the acceptance test
  deliberately never asserts on them.
- Default path is the original two lines moved verbatim into an `else`, so
  no-flag behaviour is byte-identical.

### tendcf docs

- Guide §7 / map §9 → Model B. Guide §17 rewritten so the risk apparatus
  covers the trust/consent subsystem (root cause S1). Guide §19 extended to
  sixteen questions from the residue register. Map gained **D43** and **D44**,
  with Model A struck through *in place* (D27 precedent: record reversals,
  don't erase).
- **2-of-3 offline root restored to guide §7.** Synthesis DC-20 requires the
  threshold in numbers *in the guide*; without it the precedence rule
  permitted a single-key root a red-team rated Critical.
- **NAR digests deliberately NOT promoted.** The phrase conflated the
  Nix-cache NAR inventory (Step 10+, subsystem does not exist) with the
  general "fetched artifacts bind bytes, not names" obligation (DC-11 / R12).
  The general rule went into guide §7; the cache inventory stays a map-side
  floor. Asserting a control over a nonexistent subsystem is worse than the gap.
- **DOC-4:** the *token catalogue* gives up the name; the *peer-action* sense
  keeps "capability" because it is the security sense. Done now because these
  names will appear thousands of times in generated config files and the
  goal-file schema family is about to multiply references. *Rejected:* keeping
  `capability_token` and naming the unwritten peer-action field
  `required_helper_verb` (zero files touched, but leaves the security word on
  a naming catalogue — the exact confusion TC-45 flagged).

### Operator decisions recorded

- The four org-move PRs (`frdminc/Shizuku#21`, `djbclark/stayturgid#292`,
  `site-djbclark#154`, `ops-djbclark#12`) are **no longer this chain's
  responsibility** — handed to the ops-specific agent. Do not re-adopt them.
- The CFEngine commits **correctly carry no AI-attribution trailer**. They are
  drafted for upstream. Confirmed by the operator; do not add one.

## Evidence & Data

### Verified by running, not by reading

- **PR 1 works.** Independently re-ran the installed binary: retention
  produced a `drwx------` tree containing the mirrored absolute path with the
  would-be bytes, real file untouched; a default run left **zero** `*.changes`
  in the statedir. `--help` pairs the new option with the right hint text.
- **Fable/effort verification.** PR 1's agent: `('claude-fable-5','xhigh')` on
  **all 224 turns**, read from harness transcripts, never by asking the agent.
- **`schema/report-row.schema.json` has NO agent/validator version column** —
  only `release` and `converged_release`. **The E1 adjudication §5.6 is wrong**
  where it claims report rows "already carry release and agent state". Found
  independently by both doc agents, then verified against the schema. The
  per-host version tracking that strandedness prevention depends on is a
  **schema addition D44 requires**, not an existing field.
- `schema-lint: OK (5 schemas, 12 negative fixtures)` after DOC-4 — unchanged
  counts, so `EXPECTED_BROKEN` was unaffected. **Run it with
  `uv run --with jsonschema bin/schema_lint.py`** — bare `python3` fails with
  `ModuleNotFoundError: jsonschema`.

### Quota mechanics (measured, and load-bearing)

- **Fable is an ADDITIONAL gate, not a separate allowance.**
  `relevant_windows()` in `claude_swap/oauth.py`: gating windows are "always
  the 5-hour and 7-day", with per-model `weekly_scoped` entries included *too*.
  Measured: a 211K-token Fable run moved the 5h **56% → 87%** while Fable
  moved only **5% → 10%**. **For Fable work the 5h binds first, ~6× over.**
  Claude Code's own banner agrees: "up to 50% of your weekly usage limit on
  Fable 5… draws down usage faster than Opus 5."
- **cswap auto-switching is OFF.** `com.djbclark.cswap-auto` was booted out,
  `launchctl disable`d, plist renamed `.plist.disabled`. It selected on 5h
  headroom alone and was **blind to per-model entitlement**: when account 2
  crossed 90% it moved the machine to account 1 (mit.edu), which has **no
  Fable line at all**, silently destroying Fable capability while every number
  looked healthy. Re-enabling requires `launchctl enable` *as well as*
  restoring the plist — the disable lives in launchd's override database.

### Hindsight (degraded — stopgap applied)

`hindsight-api` (PID was 70107, self-hosted `127.0.0.1:8888`, bank
`hermes-shared`) is **up but slow**. Measured 2026-08-15: bare `/health`
**6.08s**; `/tmp/hindsight-plugin.log` showed **10 `retain_failed` + 11
`reflect_failed`** in one day at 21–30s each, one `deepen_failed`, one
transient `ECONNREFUSED`. Process at 0.1% CPU — blocking, not spinning.

Symptom the operator saw: **UserPromptSubmit hook timed out**. Note that hook
failures appear in the operator's terminal but **never in the agent's
context** — the agent only receives hook *output*, so it cannot notice this
itself. Ask, or read the log.

Stopgap: three hooks in `~/.claude/settings.json` (SessionStart, Stop,
UserPromptSubmit) prefixed `HINDSIGHT_DISABLE_HOOKS=1`. Backup at
`~/.claude/settings.json.bak-2026-08-15`. **Cost while disabled: no memory
ingestion at all.**

### CFEngine gotchas already paid for — do not rediscover

1. **The checked-in `.clang-format` is silently DEAD for `.c` files** under
   clang-format ≥ ~18: its settings live in a `Language: Cpp` document, so
   `.c` falls back to `BasedOnStyle: Google` and naive formatting produces
   garbage diffs. Format with `--assume-filename=<file>.cpp`.
2. **Three acceptance tests fail identically with and without any change** —
   `diff_mode`, `manifest_mode`, `manifest_full_mode`. Environmental (expects
   `Uid: (0/root)`, plus the macOS diff issue). Baseline established by
   stashing and rebuilding pristine `17eb78e6d`. **Not regressions.**
3. **macOS `--simulate=diff` is broken independent of any change** —
   `RunDiff()` resolves `diff` from `GetBinDir()` not `$PATH`
   (`cf-agent/simulate_mode.c:363-364`). Use `--simulate=manifest` live.
4. **`SetChangesChroot()` has an unchecked `memcpy`** into a `PATH_MAX+1`
   buffer (`libpromises/eval_context.c:3849`) — latent overflow for any future
   caller with unvalidated input.
5. `cf-agent` needs `cf-promises` from the **installed** tree in
   `$WORKDIR/bin`; copying from the build tree yields a libtool wrapper.

### Fork-maintenance (PR 1, 11 hunks)

All logic is in `libpromises/generic_agent.c`; `cf-agent/cf-agent.c` carries
only parse/validate. **Exactly one modifying hunk**: the `if (ChrootChanges())`
block at `generic_agent.c:1634`. **Highest risk: the `OPTIONS[]` / `HINTS[]`
entries in `cf-agent.c` are positionally coupled — a botched rebase mis-pairs
help text SILENTLY rather than failing to compile.** Verify with
`~/opt/cfengine-dev/bin/cf-agent --help | grep -A1 simulate`. PR 2's inventory
is in `~/src/cfengine-core/docs/PR2-REPORT.md` (untracked, ~22KB).

## Operator Feedback

- **Design for upstream rejection.** Wanting upstream to take the patch is not
  assuming they will. Shape diffs so carrying them on a fork stays cheap:
  additive over modifying, few tight hunks on low-churn anchors, tests as new
  files, and **never reflow or opportunistically clean neighbouring code**.
  Where upstream-idiomatic and rebase-friendly conflict, **upstream quality
  wins** and the fork cost gets documented.
- **Prefer `cswap run` over `cswap switch`** — narrower blast radius.
- **Use a stranded window rather than waiting for reset.** If a run hits the
  wall, wait and tell it to continue; context persists.
- **Stay inside the caller's Herdr workspace** (w1H) and don't touch panes you
  didn't create.
- Get the words right when they will appear thousands of times in config files.
- Don't ask about the org-move PRs again; they belong to another agent.

## Where We're Going

**1. THE NEXT ACTION — launch the Fable 5 opinion on the goal-file schema.**
The operator asked for three independent opinions; codex and gemini are
already running (see below), Fable is the missing third. The brief is written:
`docs/architecture/GOAL-FILE-SCHEMA-BRIEF.md`. Note `schema/goal-file.schema.json`
**does not exist yet** — this is a design opinion, not a review. Run it on
**account 2** (the only Fable account) and verify entitlement first:
`cswap list` must show a `Fable:` line **and** 5h headroom on the *active*
account. Have it write to
`docs/architecture/goal-file-schema-opinion-fable.md`.

2. **Collect the two opinions already in flight.** `schema-codex` (pane
   `w1H:pP`) reported **done but has not written its file**; re-prompt it.
   `schema-gemini` (pane `w1H:pQ`) is **blocked** — read the pane and unblock
   it. Both were asked to write to
   `docs/architecture/goal-file-schema-opinion-{codex,gemini}.md`.

3. **Collect PR 2 and close its pane.** `w1H:pN` was writing unit tests
   (`tests/unit/simulate_mode_test.c`, with `tests/unit/Makefile.am`
   registration) and had already written `docs/PR2-REPORT.md`. It was told
   that if the testable seams don't exist, saying so is the right answer —
   **do not let it contort the design for coverage**. Read the report, verify
   the tests actually run, commit on `simulate-json`, then close the pane.

4. **MUST NOT BE FORGOTTEN — de-stale `docs/paper/tendcf-architecture-paper.md`.**
   It still describes the `capability` vocabulary (~line 311) and still carries
   "§8.8 Does the ChangePlan's capability vocabulary survive contact with real
   operations?" as an open question. This is a **design reversal, not a
   nuance**. Operator agreed to the timing: **batch it after the three schema
   opinions land**, since both touch the same Model B material.

5. **Hindsight: test, then re-enable if it meets the bar.** The operator's
   target is **~12s**. Test with
   `curl -s -o /dev/null -w "%{time_total}\n" http://127.0.0.1:8888/health`
   (it was **6.08s** for `/health` alone while failing 21–30s calls, so
   measure a real `retain`/`reflect` path too, not just health). **If it is
   around 12s or better, re-enable** by removing the three
   `HINDSIGHT_DISABLE_HOOKS=1 ` prefixes from `~/.claude/settings.json` (or
   restore `~/.claude/settings.json.bak-2026-08-15`). If it is still slow, the
   real fix is finding why the API blocks — the `deepen` job on
   `hermes-shared` failed at the same moment — then restarting
   `hindsight-api` when nothing is mid-flight.

6. **Upstream ticket for both PRs.** Draft it and show the operator — **he
   sends it**. `cfengine/core` has GitHub Issues DISABLED; feature requests go
   to the Northern Tech public tracker plus dev-cfengine, per `CONTRIBUTING.md`,
   and PR titles need a `CFE-1234:` prefix. **Both commits carry a placeholder
   `Ticket: CFE-XXXX` that must be amended with the real ID.** Filing is
   hook-gated on operator approval — do not route around the gate.

7. **Open design question E1 did not settle:** is the goal file the same
   artifact as the CFEngine Augments JSON (`def.json` / `host_specific.json`),
   or a projection onto it? Lands on whoever writes `goal-file.schema.json`.

8. Guide §14's "Each device carries a local trust policy in its signed
   release" sits in tension with §17's new "device-local trust root the
   release path cannot write". Judged accurate-today-plus-honest-limit rather
   than contradiction, and left alone deliberately — revisit only if you want
   §14 to point forward.

## Quick Start

```bash
# 1. Orient
cd ~/src/tendcf && git log --oneline -3 && git status -s
cd ~/src/cfengine-core && git branch && git status -s

# 2. See what is still running (panes survive session end)
herdr agent list
herdr pane read w1H:pN --source recent-unwrapped --lines 40   # PR 2
herdr pane read w1H:pQ --source recent-unwrapped --lines 30   # gemini, blocked
herdr agent prompt schema-codex "..."                          # by name
herdr agent prompt w1H:pN "..."                                # unnamed: pane id

# 3. Quota BEFORE any Fable launch — need a Fable line AND 5h headroom
cswap list

# 4. Read PR 2's own report (untracked, ~22KB)
cd ~/src/cfengine-core && cat docs/PR2-REPORT.md

# 5. Rebuild / re-verify CFEngine
cd ~/src/cfengine-core && make -j"$(sysctl -n hw.ncpu)" && make install
export CFENGINE_TEST_OVERRIDE_WORKDIR=/tmp/cfsim && mkdir -p "$CFENGINE_TEST_OVERRIDE_WORKDIR"
cd tests/acceptance && ./testall --gainroot=env --bindir=~/opt/cfengine-dev/bin 29_simulate_mode/keep_chroot.cf

# 6. tendcf schema lint (bare python3 FAILS — needs jsonschema)
cd ~/src/tendcf && uv run --with jsonschema bin/schema_lint.py

# 7. Verify a subagent's real model/effort from harness records, never by asking it
#    NOTE: pane w1H:pN uses an isolated profile:
#    ~/.claude-swap-backup/sessions/2-djbclark_gmail.com/projects/
python3 - <<'EOF'
import json,collections,glob
for p in glob.glob('/Users/djbclark/.claude/projects/-Users-djbclark-src-tendcf/*/subagents/agent-*.jsonl'):
    c=collections.Counter()
    for line in open(p):
        try: d=json.loads(line)
        except: continue
        m=d.get('message') or {}
        if isinstance(m,dict) and m.get('model'):
            c[(m['model'], d.get('effort') or m.get('effort'))]+=1
    if c: print(p.split('/')[-1], dict(c))
EOF
```

**Do not**: push either CFEngine branch, open a PR on `cfengine/core`, write
to the upstream tracker, or re-adopt the four org-move PRs.
