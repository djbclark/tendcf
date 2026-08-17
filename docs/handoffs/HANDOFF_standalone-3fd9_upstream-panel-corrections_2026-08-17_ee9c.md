---
schema_version: 1
handoff_id: ee9c
parent_handoff_ids: [e33c]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 0cfb2a61e02a0ff5a5b6fb85df9cdad18ff810e2
created_at: 2026-08-17T09:55:27-0400
writer: claude-code
---

# Handoff — upstream panels, and the corrections they forced

## The Goal

Resume B-10 (the JSON number defect family) from handoff `e33c`, close its four
open items, and file upstream. Then P-3, then "everything else" — which the
operator widened mid-session to *"make everything as correct as you can,
recontact or update if needed."*

That last instruction is what the back half of this session actually is: not new
features, but **auditing what we had already told upstream and repairing what
was wrong.** Three separate false claims of ours were found and corrected, two of
them in code or documents already in front of maintainers.

## Where We Are

Everything below is pushed. `tendcf` is clean at `0cfb2a6`.

### Closed this session

| item | state |
|---|---|
| **B-10 + B-4** | Panel 4/4 *ship with changes*, 4/4 `security@`. Six-commit stack, tip `11725b0`. Fork PR [djbclark/libntech#5](https://github.com/djbclark/libntech/pull/5). Emailed `security@northern.tech`, Gmail id `1a00f99c7e714823`. |
| **B-11** | Subsumed by B-10's copy commit `55f3eb3`; register row updated. |
| **B-12** | Filed as [djbclark/core#14](https://github.com/djbclark/core/issues/14). Not fixed. |
| **P-3** | Correction force-pushed. [NorthernTechHQ/libntech#291](https://github.com/NorthernTechHQ/libntech/pull/291) is now `e76700b`, **open, mergeable, one commit**. Correcting email `1a00fb936fc1741f`. |
| **P-1 / P-2 trailers** | `Ticket: #6295`/`#6296` **restored** — they were never phantom. `#6293` → `64e2ac1cb`, `#6294` → `05e18f038`, both open and mergeable. |
| **core#7** | Answered: `tendcf-integration` builds and passes **68/68 (4 expected failures)** against **stock** libntech `5b5d04e1`. |
| **Jira API** | **Now works.** `GET /rest/api/3/myself` → **HTTP 200** (was 401). Tested at operator request; nothing else done with it. |

### In flight — the thing the next session picks up

**P-1 and P-2 have been panelled and both live upstream PRs are publicly flagged
as defective, with a fix promised. The fixes are unwritten.** That is owed work,
not optional.

Three reviewers (cursor, grok, fable-as-`claude-fable-5`), unanimous **push a
correction** on both, **none** said withdraw. Opinions committed at
`docs/architecture/upstream-opinion-p1p2-{cursor,grok,fable}-2026-08-17.md`.

### Files changed this session

**`tendcf`** (17 commits, `fbb5078..0cfb2a6`, all pushed, tree clean):
`docs/architecture/upstream-register.md` (heavily — corrections to B-4, B-10,
B-11, B-12, B-1, B-2, B-8, P-1, P-2, P-3, the channels table and the SHA
mapping table); new `b10-number-render-measurement-2026-08-17.md`,
`b10b4-panel-reconciliation-2026-08-17.md`,
`b10b4-security-email-draft-2026-08-17.md`,
`UPSTREAM-B10-B4-STACKED-REVIEW-BRIEF.md`, `UPSTREAM-P1-P2-REVIEW-BRIEF.md`,
and seven `upstream-opinion-*` files (four for b10b4, three for p1p2).

**`libntech`** — `fix/json-number-fatal-exit` rebuilt from `0c0620d`
(`libutils/{json.c,mustache.c,string_lib.c}`, `tests/unit/json_test.c`);
`fix/json-real-precision` reset to `cd545ab`; `silent-digest-failure`
rewritten to `e76700b` (`libutils/hash.c` unchanged, new
`tests/unit/hash_init_fail_test.c` + `tests/unit/Makefile.am`).

**`core`** — `simulate-keep-chroot` and `simulate-json` commit **messages**
rewritten via `git commit-tree`; **trees byte-identical**, no source changed.

**Not modified:** `/Users/djbclark/src/cfengine-core`'s working tree or its
libntech submodule.

## What We Tried

Failed approaches and wrong conclusions, chronological. These are the expensive
ones to rediscover.

1. **`gh api repos/cfengine/core/issues/<n>` → 404 → "the ticket numbers were
   guessed."** Wrong method, and it produced a *fabricated motive* written into
   a durable document. `#6295`/`#6296` are **Discussions**, which is exactly what
   a repo with issues disabled uses, and the operator had opened them the same
   evening the PRs went up. On that bad evidence two live upstream PRs had their
   history rewritten to strip correct metadata. **Our own tooling already
   contradicted us** — `site-djbclark`'s `track-issue-activity.yml` had been
   polling both as `type: discussion` and succeeding hourly the whole time.
   Correct check now recorded: query the issues endpoint **and** GraphQL
   `repository.discussion(number:)`.

2. **The P-3 adjudication's §5F: "P-3 was never emailed, so there is no prior
   private characterization to correct."** False. Gmail thread
   `1a007e4362402bd9`, `contact@` at 2026-08-16T00:06Z, re-sent to `security@`
   at 00:10Z, reproducing #290 in full including *both* claims the panel
   retracted. Same failure shape as (1): a confident negative from a check that
   could not see the thing it ruled out. Verify claims about what was sent
   against the mail store.

3. **My own umask reasoning on P-1.** I looked at `mkdir(path, 0700)`, thought
   about umask, and concluded *"umask can only remove bits, so 0700 is a ceiling
   — safe."* True for **too loose**, blind to **too tight**. grok measured
   `umask 0777` producing a `0000` directory against the real `cf-agent` binary:
   the creating process cannot enter it, `mkdir` succeeded so nothing fails,
   `KeepChangesChroot` still announces success, operator gets an empty unusable
   tree.

4. **A `sed`/`python` global replace of two `*unknown*` register cells** stamped
   P-3's email thread onto P-1/P-2's rows. Caught and fixed in its own commit
   (`27851d4`) rather than folded in quietly. P-1/P-2 were **never** emailed —
   verified: only four threads to `northern.tech` exist.

5. **gemini as a panel member.** Produced its B-10 file **4m03s** after launch
   (less than `make -j2` takes), addressed **none** of the four build traps it
   was required to control for, called the catalogued `JsonIntegerCreate()`
   narrowing "perfectly safe", and answered "Nothing" to what the fix missed
   when the question text said otherwise. Recorded as one weak voice, not
   discarded silently. **Dropped from the P-1/P-2 panel.**

6. **`fable-deep` silently resolving to `claude-opus-4-8`.** Fixed by passing
   `model: "fable"` explicitly on the Agent call, and by instructing the agent to
   state its own model. It then confirmed `claude-fable-5`. Pin the model; do not
   trust the agent definition.

7. **Rebuilding the test binary without rebuilding `libutils`** — hit again this
   session while checking where `Log()` writes. Produced a completely misleading
   "no log output at all" result. This is trap #1 and it still bites.

## Key Decisions

- **Keep B-10's six-commit stack, one PR** — not squash. cursor, grok and fable
  favoured the stack; gemini said combine. The operative constraint all four
  shared was *one PR, landing together, never B-10 alone*. PR body offers to
  squash at merge.
- **`security@` for B-10, ordinary bug for P-3.** P-3's severity was settled by
  the adjudication: the zero digest is a colliding **lookup handle**, not a
  bypassed **cryptographic gate**. That downgrade was stated explicitly in the
  correcting email *because* the original had reached `security@`.
- **`contact@`, not `security@`, for P-1/P-2** — they are features.
- **Comment on the live PRs before writing the fixes.** Rejected alternative:
  wait until the corrections were ready. Leaving a known buffer overflow in a
  mergeable PR while writing a patch is worse than an early, honest comment.
- **Restore the trailers rather than leave them stripped** (operator decision),
  and add the `Changelog: Title` line they should have carried. Rejected: quietly
  reverting them again after reviewers flagged the Jira-vs-Discussion point.
- **Do not fix B-12 inside the JSON change.** Keeping one behaviour change per
  patch; filed separately instead.
- **`Changelog: Title` on fix commits, `Changelog: None` on test-only commits**,
  and **no `Ticket:`** on the libntech stack until a real upstream ticket exists.

## Evidence & Data

**B-10/B-4 final stack** (`fix/json-number-fatal-exit`, tip `11725b0`), every
commit built and tested **independently** — the gap all four reviewers left open:

```
11725b0  Do not exit the process when selecting an oversized JSON array index
55f3eb3  Copy a JSON number as it was parsed
df3a263  Add regression tests for JSON number classification and rendering
84843da  Do not exit the process when rendering a JSON number
cd545ab  Add a regression test for JSON real rendering
8923f79  Do not truncate JSON reals to two decimals when rendering
0c0620d  (upstream base)
```

Tip: `json_test` 75/75, suite 39/39. Pre-rework reviewed tip preserved as tag
`panel-reviewed-cc4a0d9`. **The rebuilt stack differs from what the panel
reviewed only in `tests/unit/json_test.c`** — the C files are byte-identical, so
no review conclusion was invalidated.

**Seven defects the B-10 panel found in our own series** (none in the fix):
bundled commit (`8aac759` carried both `JsonPrimitiveCopy` and `JsonSelect` under
a message naming one); registration order letting an abort mask three tests; a
stale comment the next test contradicted; no in-memory-producer coverage;
`Co-Authored-By` on 4 of 6; no `Changelog:` trailers; `mustache_extra.json`
sequencing hazard. All fixed.

**The severity finding that reframed B-10** — silent integrity loss, no crash,
no failsafe:

| JSON number | stored on stock 3.27.1 |
|---|---|
| `2000000000000` | `-1454759936` |
| `9223372036854775807` | `-1` |
| `1786965915908` (epoch ms) | `259520772` |
| `1755400000000` (epoch ms) | `-1241624064` |

**P-3**: `json_test` 40/40 on branch; the new `hash_init_fail_test` exits **3**
(all three cases failing) against the unfixed file. Getting there required a fix
the adjudication missed — see "Where We're Going" note.

**P-1/P-2 panel baselines**: `core-p1` 68 tests, `core-p2` **69** (P-2 adds
`simulate_mode_test`), `rc=0` both, on stock libntech `5b5d04e1`.

**The P-1 overflow** (`cf-agent/cf-agent.c:815` guard,
`libpromises/eval_context.c:3897` copy):

```c
strncpy(chrooted_path + chroot_len + offset, orig_path,
        (PATH_MAX - chroot_len - offset - 1));
```

Guard admits `PATH_MAX-1`; with `chroot_len == PATH_MAX-1` and `offset == 1` the
count is `-1` → `SIZE_MAX`. Unbounded copy into a static buffer on the first
mapped file. Verified by fable under AddressSanitizer **and** confirmed by
reading both sites. The in-function `assert` recomputes the same underflowed
bound and the build is `-DNDEBUG`.

**Gmail ids** (all verified against the mail store, not notes): B-1/B-2/B-8
`1a00d22ac0d46c9b` + follow-up `1a00d44a2758b9ea`; P-3 original thread
`1a007e4362402bd9`, correction `1a00fb936fc1741f`; B-10/B-4 `1a00f99c7e714823`.

**Disk**: 83%, 75Gi free — the handoff `e33c` warning of ~99% is **stale**.

## Operator Feedback

- *"Re-panel the new severity first"* and *"Stack B-10 on B-4"* — both followed.
- *"Go ahead with P-3, then continue with everything else."*
- *"Go ahead and restore them, make everything as correct as you can, recontact
  or update if needed."* — this is what drove the trailer restoration, the P-3
  email correction, and the P-1/P-2 panel.
- *"You do not need to wait for me to open PRs or send emails, however you do
  need to hold off for long enough to minimize the chances of posting something
  incomplete or wrong."* — standing authorization; the constraint is
  completeness, not permission.
- *"Make sure when you fable-deep you actually use fable, not opus."*
- Jira test: *"don't do anything else if it does [work]"* — honoured; only
  `/myself` was called.

## Where We're Going

1. **THE NEXT ACTION — write P-1's correction.** Bound the keep path so
   `keep + "/" + longest orig` can neither overflow nor silently truncate
   `ToChangesChroot()`. The existing `strlen(optarg) >= PATH_MAX` check guards
   the wrong buffer; the in-function `assert` is useless (same underflowed bound,
   `-DNDEBUG`). **Verify under AddressSanitizer.** Then: `chmod(keep_chroot,
   0700)` after a successful `mkdir`, failing the run if it fails; either reject
   a group/world-writable non-sticky parent or delete the "never lands somewhere
   looser" sentence; acceptance tests for created mode, `EEXIST`, relative path,
   and a truncating keep path (`keep_requires_simulate` and
   `default_chroot_deleted` do not cover the new behaviour).
2. **P-2's correction.** (a) `cf-agent/simulate_mode.c:872–877` sets
   `name_arch = NULL` **before** `MapRemove(removed, name_arch)`, so
   remove-then-install reports both — this reaches `--simulate=diff` prose too;
   add unit case `r,pkg,,\r\ni,pkg,1.0,\r\n` expecting one install and no remove.
   (b) Emit UTF-8 bytes or real `\uXXXX`, not per-byte `\u00XX`; **test the round
   trip with `python -c 'json.load(...)'`, not `JsonParseFile`** — the existing
   test hides the bug by using the same non-conformant decoder. (c) `uid_t`/
   `gid_t` cast to `int` prints uid 4294967294 as `-2`. (d) `WriteChangesJson`
   failure must exit non-zero; do not truncate an existing output file; do not
   follow a same-owner symlink. (e) `HashFile()` unchecked — check it or omit the
   `sha256` field. (f) Soften "the prose renderers are unchanged". (g) Replace
   the literal `CFE-XXXX` at `tests/acceptance/29_simulate_mode/simulate_json.cf:26`.
3. **Force-push both**, comment again on each PR saying the fix is up, then
   **email `contact@northern.tech`** carrying the findings.
4. **Decide the `Ticket:` question explicitly.** All three reviewers flagged that
   `#6295`/`#6296` are Discussions while `CONTRIBUTING.md` wants a Jira
   `CFE-`/`ENT-` key. **The Jira API now works (HTTP 200)**, so filing a real CFE
   ticket is possible for the first time. Do not silently revert the restored
   trailers.
5. **B-1/B-2/B-8**: fix, panel and `security@` mail all done; **no upstream PR**.
   That is the remaining step for all three.
6. **core's half of B-10**: `/Users/djbclark/src/core-json` branch
   `fix/json-number-rendering` (`6a4216dad`, `367c27fc5`, `32c38f8ab`) — four
   fatal sites, not two. Offer once libntech#5's direction is settled.
7. **B-12's fix** (core#14) — one line, but needs a test approach; the unit suite
   has no seam for the route container.
8. **exec_timeout termination half** — still open and unfiled. Start from the
   ALARM_PID theory (`cf_pclose()` clears it before `cf_pwait()`); the earlier
   refutation is **retracted**.
9. Then E-9 and `services:`, then the generic bundle.
10. Housekeeping: `git worktree remove` for `core-p1`, `core-p2`, and
    `libntech-b4` (redundant — its commits are the base of
    `fix/json-number-fatal-exit`). `core-json` is a full build: `make clean`
    first. Not urgent; disk is fine.

## Quick Start

```bash
# Read the panel's findings first — item 1 above is derived from these
cd /Users/djbclark/src/tendcf
ls docs/architecture/upstream-opinion-p1p2-*-2026-08-17.md

# P-1 worktree (built, stock libntech 5b5d04e1, baseline 68 tests rc=0)
cd /Users/djbclark/src/core-p1
sed -n '810,822p' cf-agent/cf-agent.c            # the wrong-bound guard
sed -n '3888,3900p' libpromises/eval_context.c   # the underflowing strncpy

# P-2 worktree (baseline 69 tests rc=0)
cd /Users/djbclark/src/core-p2
sed -n '866,882p' cf-agent/simulate_mode.c       # CollectPkgOperations

# Rebuild + test either (traps 1 and 2: top-level make first, force the relink)
make -j2 && rm -f tests/unit/<test> && (cd tests/unit && make check)

# Live upstream state
gh pr view 6293 -R cfengine/core --json state,mergeable,headRefOid
gh pr view 6294 -R cfengine/core --json state,mergeable,headRefOid
gh pr view 291  -R NorthernTechHQ/libntech --json state,mergeable,headRefOid

# Verify a ticket reference BOTH ways before calling it phantom
gh api repos/cfengine/core/issues/6295 || true
gh api graphql -f query='query{repository(owner:"cfengine",name:"core"){discussion(number:6295){title}}}'

# Jira now authenticates (200). Token via the broker only; never echo it.
# sudo-secretspec get ATLASSIAN_CFENGINE_API_TOKEN --reason "<why>"
```

**Do not** build or modify `/Users/djbclark/src/cfengine-core` — other work uses
it and its libntech submodule must stay uncommitted. Builds at `-j2`/`-j4`,
never `-j8`.
