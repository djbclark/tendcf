---
schema_version: 1
handoff_id: e33c
parent_handoff_ids: [16b8]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 283c4cfd654859d31cd00e0c3618965f689c52ea
created_at: 2026-08-16T22:35:00-0400
writer: claude-code
---

# Handoff — the register was wrong about upstream, and B-4 was hiding a worse bug

## The Goal

Resume from 16b8 and, per the operator: fix the stale P-3 SHA "as you feel
appropriate", run P-3's missing second opinion followed by a fable-deep review,
**continue until B-4 is fixed**, and send an email update if the new information
made one plausibly useful.

All of that is done. Two things made the session much larger than the ask: the
stale SHA turned out to be the thread on a materially wrong register, and
measuring B-4 uncovered a far more serious defect underneath it.

## Where We Are

**tendcf** `master` at `283c4cf`, **clean, pushed**. Eight commits this session
(`cd415e1..283c4cf`).

**`djbclark/libntech`** — two new branches, both pushed:

| branch | head | what |
|---|---|---|
| `fix/json-real-precision` | `fe1ace9` | B-4, libntech half |
| `fix/json-number-fatal-exit` | `76856ee` | B-10, three commits + tests |

**`djbclark/core`** — one new branch plus two rewritten:

| branch | head | what |
|---|---|---|
| `fix/json-number-rendering` | `367c27fc5` | B-4 + B-10 core halves, **behaviourally UNVERIFIED** |
| `fix/exec-timeout-promise-result` | `46be075d4` | now carries the acceptance tests |
| `simulate-keep-chroot` | `ea439e0ad` | was `00c98bc8b`, phantom ticket dropped |
| `simulate-json` | `f5ce3a35d` | was `8ee015c42`, phantom ticket dropped |

**Fork issues filed:** [libntech#4](https://github.com/djbclark/libntech/issues/4)
(B-10), [core#13](https://github.com/djbclark/core/issues/13) (core halves);
[libntech#2](https://github.com/djbclark/libntech/issues/2) updated with B-4's fix.

**Five worktrees exist and should be cleaned up** once their branches are settled:
`/Users/djbclark/src/{libntech-fixes,libntech-b4,libntech-p3,core-json,core-acceptance}`.
`git -C ~/src/cfengine-core worktree list` and the same for `libntech` enumerate them.
`~/src/cfengine-core` itself is untouched, still on `tendcf-integration`, `libntech` still ` M`.

### THE BIG CORRECTION — upstream was never closed

The register opened by asserting every upstream channel was closed and that
"nothing is filed on an upstream tracker yet". **Both were false**, and the
error hid three live upstream contributions:

| verified via GitHub API | reality |
|---|---|
| `NorthernTechHQ/libntech` issues | **ENABLED** (`has_issues: true`) — the old claim was simply wrong |
| our upstream filings | [libntech#290](https://github.com/NorthernTechHQ/libntech/issues/290) (issue) + [#291](https://github.com/NorthernTechHQ/libntech/pull/291) (PR), [cfengine/core#6293](https://github.com/cfengine/core/pull/6293), [#6294](https://github.com/cfengine/core/pull/6294) — all open, mergeable, CLA signed |
| `cfengine/core` issues | genuinely disabled (`has_issues: false`) — that part was right |

All four were opened **by the operator manually on 2026-08-15 evening** and never
recorded. **Check the tracker before asserting it is closed.**

## What We Tried

### 1. Three stale SHAs, all orphaned the same way

Chasing P-3's `da7d3d9` found all three P-item SHAs stale: the commit was amended
after the SHA was written down, so the citation pointed at a commit no branch
reaches. Content was identical every time — only the message differed — so every
diff-based check passed. Only `git branch -a --contains <sha>` (empty output)
reveals it. P-1 and P-2 then moved **again** hours later, which is the argument
for citing branch names rather than SHAs.

### 2. Phantom ticket numbers on live upstream PRs

`Ticket: #6295` and `Ticket: #6296` — **neither exists** (both 404). `cfengine/core`
has issues disabled, so no such ticket could have been created; the numbers appear
to have been guessed as "the next ones after our PRs". Neither commit carried a
`Changelog:` line, and CONTRIBUTING only requires `Ticket:` alongside `Changelog:`,
so the repair was to **drop the trailer**, not invent another number. Fixed with
`git commit-tree` so no working tree moved; trees verified byte-identical.

### 3. Two claims of mine that were WRONG and are retracted

- **"The libntech test harness masks failures."** Told to the operator; **false**.
  `make check` reports failures correctly. Two things fooled me: running
  `./tests/unit/json_test` from the repo root, where two tests cannot find their
  data files, and the stale-archive trap below.
- **"`inf` is acceptable but disclose."** Waved through by me and two reviewers;
  grok is right that `1e400` rendering as `inf` emits a **non-JSON token** while
  `JsonWriteCompact()` still emits `1e400`. That is a defect, not a disclosure item.

### 4. Three false verifications from build-system traps — read this before measuring

Verifying "fails without the fix" took **three attempts**, each defeated differently:

1. **`make check` inside `tests/unit` does NOT rebuild `../libutils`.** The test
   binary silently links whatever `libutils.a` was last built. This produced both
   a false green and a false red.
2. **`make -C tests/unit json_test` alone does not relink** on a changed archive.
   You must `rm -f tests/unit/json_test` to force it.
3. **`git stash push libutils/json.c` stashes nothing once the file is committed** —
   so the "without fix" build still had the fix, and the test passed, appearing not
   to catch the bug. Use `git checkout <prev-commit> -- <file>` instead.

**The reliable recipe:** `git checkout <prev> -- <file>` → top-level `make` →
`rm -f tests/unit/<test>` → `make -C tests/unit <test>` → run **from inside
`tests/unit`**.

### 5. The machine ran out of disk mid-session

460Gi disk hit **100% full, 589Mi free**, and an `Edit` failed with `ENOSPC`.
The five worktrees were only ~130MB total — the disk was already near-full and
concurrent builds tipped it. `make clean` on the finished worktrees freed **8.1GB**.
`~/Library` (67G) and `~/src` (66G) are the bulk and need the operator's attention.
Also: load hit 15.9 on 8 cores with three agents building — use `-j2`/`-j4`, not `-j8`.

## Key Decisions

**One principle behind B-4 and B-10 both:** *render a JSON number from the text the
parser already kept, rather than converting it to a C numeric type and back.* That is
what `JsonWriteCompact()` already does, so it also removes render-vs-serialise
disagreement. Applied at six sites across two repos.

**Rejected:** changing `StringFromDouble()`'s `%.2f` to `%.4f` or `%.17g` — it takes a
`double`, so the lexeme is already gone; making the two agree at a different decimal
place moves the bug rather than removing it.

**Where the lexeme is NOT the answer:** `generic_agent.c` (timestamp) and
`unix_iface.c` (route metric) genuinely want an integer, so the repair is a
**non-fatal conversion** — an unreadable timestamp means "not validated" (the safe
direction, and what the code already did when the field was absent); an unreadable
metric simply does not win the comparison.

**B-10 filed separately from B-4** rather than folded in: independent severity
(availability vs correctness), independently landable.

**No `Ticket:`/`Changelog:` trailers on any new commit** — there is no verified
upstream issue number, and inventing one is a mistake already made and repaired
this session.

## Evidence & Data

### B-10 — a valid JSON number takes a host off its policy

Stock 3.27.1, `readjson()` file containing `1e-8`, rendered with `string_mustache()`:

```
error: Conversion error (-83 - Not terminated) on '1e-8' (StringToLongExitOnError)
error: CFEngine was not able to get confirmation of promises from cf-promises, so going to failsafe
```

Controls that pass on the same build: `0.00000001`, `2`, `1.5e3`, `42`, `9223372036854775807`.

Three defects, one root cause (`StringToLongExitOnError()` → `DoCleanupAndExit()`):

| | stock | fixed |
|---|---|---|
| `1e-8`, `2e0`, `1E5` rendered | **process exit** | renders |
| `9223372036854775808` rendered | **process exit** | exact |
| `2000000000000` **copied** | **`-1454759936`** | exact |
| `9223372036854775807` copied | **`-1`** | exact |
| `0.00049` copied | `0.0005` | exact |
| `3.14159265` copied | `3.1416` | exact |

The copy corruption is the worst because it is **silent**: `JsonIntegerCreate()` takes
an `int` while `JsonPrimitiveGetAsInteger()` returns a `long`. `2000000000000` is an
unremarkable value, and copying happens wherever data containers are merged.

### B-4 — reals truncated to two decimals

mustache render of a parsed value: `0.00049` → `0.00`, `0.001` → `0.00`,
`3.14159265` → `3.14`, `1234.1234` → `1234.12`; control `42` unchanged. After the
fix all render exactly. **One behaviour change:** `1.5e3` now renders `1.5e3`, not
`1500.00` — the same text `JsonWriteCompact()` already produces.

### Tests

- libntech `make check`: **39/39, no failures** (after a top-level `make`).
- Three new tests in `json_test.c`, all verified **in both directions**:
  `test_parse_exponent_numbers`, `test_primitive_to_string_numbers`,
  `test_copy_preserves_numbers`, plus `test_select_oversized_array_index`.
- exec_timeout acceptance tests, `08_commands/04_exec_timeout/`, ~29s total:

| test | stock | fixed |
|---|---|---|
| `timeout_overrides_exit_zero.cf` | **FAIL** | Pass |
| `within_timeout_normal_outcomes.cf` | Pass | Pass *(deliberate normal-path guard)* |
| `timeout_overrides_kept_returncodes.cf` | **FAIL** | Pass |
| `timeout_after_output_closed.cf` | **FAIL** | Pass |
| `timeout_does_not_leak_to_next_promise.cf` | **FAIL** | Pass |

### Panels

**P-3 (complete):** cursor, gemini, grok all *push a correction*; fable-deep
adjudicated **ordinary bug, not `security@`** — the zero digest is a colliding
*lookup handle*, not a bypassed cryptographic gate, since impersonation still needs
the matching private key. **Our PR #291 carries a false claim**: that this cannot be
unit-tested without core's `CryptoDeInitialize()`. Three reviewers refuted it by
doing it. fable-deep also caught what all three panellists got wrong — their
prescribed placement inside `hash_test.c` run last **does not work**, because after
prior EVP use the provider drain leaves `EVP_DigestInit_ex` returning 1.

**B-10 (complete):** fable-deep *needs changes* (found the copy corruption),
gemini *ship as is / `security@`*, cursor *ship with changes*, grok *ship with
changes / `security@`*. Consensus severity **`security@`** on availability.

grok's threat statement, which the filing should adopt verbatim:
> "attacker-controlled" is overstated for a remote exploit; it is honest for a CMDB
> operator, a `readjson()` of third-party JSON, or an author who writes scientific
> notation by mistake.

## Operator Feedback

- **"You are always authorized to delegate to fable-deep subagents."** Standing;
  recorded in agent memory as `fable-deep-always-authorized`.
- **Phantom tickets: "Drop the trailers, force-push"** — done.
- **B-10: "Upstream issue + PR, and email security@"** once the audit clears —
  **approved but NOT yet executed**, see next steps.
- **"Do not hesitate to send email update if it could be plausibly useful."**
  No email was sent: P-3's adjudication concluded P-3 was never emailed and needs a
  PR correction rather than a mail, and B-10's four open items are not closed.
- Carried and still live: fix every bug we find; three channels per bug; regression-test
  each fix; **no upstream send until EVERY commissioned review has reported**.

## Where We're Going

1. **THE NEXT ACTION — collect the P-3 correction agent's output.** It was still
   running at handoff and is building `tests/unit/hash_init_fail_test.c`, the amended
   `dc85a6f`, and three ready-to-paste texts, in worktree
   `/Users/djbclark/src/libntech-p3` (branch `silent-digest-failure-v2`, still at
   `dc85a6f` — it may not have finished). Its prescription: amend the commit with three
   prose changes (accurate consumer list; describe the added test; scope note on
   unchecked `EVP_DigestUpdate`/`Final`), keep `Ticket: #290`, match the PR body,
   comment on PR #291, and post a correcting comment on **issue #290** whose
   "worst-case impact" paragraph is wronger than the commit. **Outward steps were
   deliberately withheld pending a go/no-go** — force-pushing a live upstream PR is
   the operator's call.
2. **Close B-10's four remaining items, then file upstream + email `security@`**
   (operator pre-approved the route):
   a. Fix `1e400` → `inf`, which is not JSON, or deliberately pin it in a test.
   b. State plainly that exponent *reals* still render through `%.2f`, so `1e-8`
      mustaches to `0.00` — the fix turns a fatal into a **lossy** result and the
      filing must not overclaim.
   c. Propose mustache coverage upstream rather than inventing a test binary in this PR.
   d. **Verify `fix/json-number-rendering`** — it has only a syntax check. Until it
      lands, a CMDB *array* of `9223372036854775808` still kills the agent.
3. **B-4 needs its own full panel before any email.** Only B-10 was panelled; B-4's
   fix is committed on both sides but unreviewed.
4. **B-11 recorded, not fixed** — `JsonRealCreate()`'s `%.4f`. Largely subsumed by the
   `JsonPrimitiveCopy` fix; re-measure whether anything remains before filing.
5. **The termination half of exec_timeout is still open and unfiled.** Start from the
   ALARM_PID theory (`cf_pclose()` clears it before `cf_pwait()`); my earlier
   refutation is retracted.
6. **core#7's live box** — confirm #4/#5/#6 build and pass against **stock** libntech
   `5b5d04e1`, not our patched `dc85a6f`.
7. **Remove the five worktrees** once their branches are settled, and tell the operator
   about the disk: 460Gi at ~99%, `~/Library` 67G and `~/src` 66G.
8. Then E-9 and `services:`, then the generic bundle — still the only live bullet in
   projector-reconciliation §11.
9. Unrelated, carried: confirm `track-issue-activity.yml`'s Discussion path fires in
   site-djbclark.

## Quick Start

```bash
# State
cd ~/src/tendcf && git log --oneline -5 && git status -s
git -C ~/src/cfengine-core worktree list
git -C ~/src/cfengine-core/libntech worktree list

# Did the P-3 correction agent finish?
ls -la ~/src/libntech-p3/tests/unit/hash_init_fail_test.c 2>/dev/null
git -C ~/src/libntech-p3 log --oneline -2
sed -n '/^## /p' ~/src/tendcf/docs/architecture/upstream-p3-reconciliation-2026-08-16.md

# The panels
ls ~/src/tendcf/docs/architecture/upstream-opinion-{p3,b10}-*.md
sed -n '1,60p' ~/src/tendcf/docs/architecture/upstream-register.md

# Upstream reality -- check, do not assume
gh api repos/NorthernTechHQ/libntech --jq .has_issues     # true
gh api repos/cfengine/core --jq .has_issues               # false
for n in 6293 6294; do gh pr view $n --repo cfengine/core --json headRefOid,state --jq .; done
gh pr view 291 --repo NorthernTechHQ/libntech --json headRefOid,state --jq .

# libntech tests -- TOP-LEVEL make first, run from inside tests/unit
cd ~/src/libntech-fixes && make -j4 && cd tests/unit && make check   # expect 39/39

# To prove a test fails without a fix (three traps live here -- see What We Tried #4)
cd ~/src/libntech-fixes && git checkout <prev-sha> -- libutils/json.c
make -j4 && rm -f tests/unit/json_test && make -C tests/unit json_test -j4
cd tests/unit && ./json_test ; git -C ~/src/libntech-fixes checkout HEAD -- libutils/json.c

# Standalone libntech probe (platform.h will NOT compile without these)
#   -DHAVE_CONFIG_H -I<configured tree> -Ilibutils -Ilibcompat
#   -I/opt/homebrew/opt/{pcre2,openssl@3,libyaml}/include
#   link libutils/.libs/libutils.a libcompat/.libs/libcompat.a -lpcre2-8 -lssl -lcrypto -lyaml
#   compile a patched .c to .o and link it AHEAD of the archive to A/B without rebuilding

# Review CLIs -- each binds its prompt differently; a dropped prompt looks like success
#   grok   --always-approve --effort high --prompt-file FILE     (prompt is POSITIONAL)
#   gemini --dangerously-skip-permissions --effort high --print-timeout 40m -p "PROMPT"
#   cursor-agent -p --force "PROMPT"                             (-p is a BOOLEAN)

# Disk -- it hit 100% this session
df -h /System/Volumes/Data
```
