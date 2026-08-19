---
schema_version: 1
handoff_id: 5c31
parent_handoff_ids: [b167]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: de7ae6335838098dd56a640889ad193825bd8ffa
created_at: 2026-08-18T21:52:38-0400
writer: claude-code
---

# Handoff — de-stale the paper and guide for public comment

## The Goal

Operator: *"We need to make sure `/Users/djbclark/src/tendcf/docs/paper/*.md`
are up-to-date with all of the stuff that has happened and been discovered
since they were last edited. I think it is time I actually ask for comments
on them."*

Two documents in scope — `tendcf-architecture-paper.md` and
`tendcf-architecture-guide.md`. `docs/paper/reviews/` is a subdirectory and
`*.md` does not match it; it was correctly left alone.

## Where We Are

Clean tree, `master`, `de7ae63`. Four commits this session, all pushed:

| SHA | What |
|---|---|
| `01ea593` | De-stale both documents (the bulk) |
| `68a933f` | Extend the test-coverage audit to every open PR |
| `99c37df` | Prove the #6308 gap cannot be closed; our own reason was wrong |
| `de7ae63` | Record the upstream corrections posted to both channels |

Files changed this session (`git diff --stat a92f603..HEAD`) — three, plus
this handoff:

```
 docs/architecture/upstream-register.md  | 102 ++++-
 docs/paper/tendcf-architecture-guide.md | 340 ++++++++++++++--
 docs/paper/tendcf-architecture-paper.md | 664 +++++++++++++++++++++++++++-----
 3 files changed, 970 insertions(+), 136 deletions(-)
```

No code, schemas, fixtures or policy were touched — this was a documentation
and upstream-communication session end to end.

Both lints pass and were run after every edit batch:
`uv run bin/xref_lint.py` → 93 live documents, 84 frozen skipped, 854
sections, **0 findings**. `uv run bin/schema_lint.py` → **OK (8 schemas, 59
negative fixtures, 6 byte-class fixtures, 27 projection fixtures)**.

The documents are done. Nothing has been published or sent — that is the
open half of the operator's request and the reason item 1 below is item 1.

### Staleness that was found

Paper last edited **2026-08-15 21:25** (`48050f8`), guide **2026-08-15
23:09** (`64df1ea`). Everything from 2026-08-16 onward was missing: the
reference projector, the generic bundle, and the entire upstream CFEngine
campaign. The paper was additionally ~2h staler than the guide and had never
received corrections the guide already carried.

**Five claims were false, not merely stale** — worth separating, because
"out of date" undersells it:

1. Paper §2.2: *"YAML and JSON are valid inputs"* to Augments. **YAML is
   not**; the agent reads JSON only. Guide had this right.
2. Paper §2.2: version floor stated as **3.7**. `host_specific.json` has only
   been parsed since **3.18**.
3. Both: *"twelve deliberately broken fixtures."* There are **92**.
4. Guide §19: *"goal file, diff, approval record — are not written yet."*
   They landed 2026-08-15 (`9fdf437`), before that very edit.
5. Paper §2.6's `host_specific.json` example does not load as Augments (top
   level `data` / `nix2cf_edges` are both skipped) and said nothing about it.
   The guide already carried that flag.

### Parity gaps closed (paper had drifted behind the vetted guide)

- **Projection step absent entirely** from the paper. Guide had it in §7 and
  §16.A since `64df1ea`. Added to paper §2.5.
- **§1.1 had 3 scope limits; guide §17 had 10.** The 7 missing ones are the
  trust-and-consent group, including the consent-gate admission ("every
  control is authored, delivered and evaluated by the party it exists to
  constrain") — arguably the design's most important weakness, and it was
  missing from the document going to expert readers. 6 added.
- **Paper open questions stopped at 9; guide had 16.** Added 9.10–9.16.

## What We Tried

Chronological, with why each was abandoned. These are the expensive ones to
rediscover.

**Over-generalized the test-coverage claim, caught mid-task.** First wrote
"Every fix ships with a regression test that was shown to fail without it,
except one." The register's audit covered **17 branches**, not the 23 defect
fixes — and those 17 *included* the two P-item features. Corrected to "16 of
17" before the first commit, then superseded entirely by the extension below.
This is the exact failure mode reconciliation item C-2 records; it recurred
within one session of reading C-2.

**Considered avoiding the §7 renumber** by making the substrate material
subsections of "Status and validation" instead of a top-level section.
Rejected: the operator explicitly chose "new section," and counting the
cross-references first showed only 9 refs to §7/§8/§9 in the paper and 2 to
§19 in the guide. `xref_lint` makes renumbering mechanically safe, so the
caution was unfounded.

**#6308 — four routes to a test, all dead:**

1. **`RLIMIT_NOFILE` to force `cf_popen()` failure** (B-19's own proven
   technique). *This works* for reachability — reaches the arm at `:1436`
   and the disarm at `:1472` without running `mount`. Dead for a different
   reason: nothing to observe (below).
2. **Macro-substitute `LiveMountConverged` before `#include <nfs.c>`**
   (following B-12's `unix_iface_test.c` precedent). Rejected — the macro
   would also mangle the function's own definition, and upstream would
   rightly refuse it.
3. **Acceptance test.** Mount operations need privilege; CI cannot run them.
4. **Lift the two disarm lines into a static helper and test that.**
   Rejected as manufactured — it tests the helper, not the placement, which
   is precisely the false confidence the audit was asking about.

**Tooling gotchas, both cost a cycle:**

- `python3 bin/schema_lint.py` → `ModuleNotFoundError: rfc8785`. The script
  is a `uv` PEP-723 script; **must** be `uv run bin/schema_lint.py`.
- `sudo-secretspec run -- …` → usage error. **`--reason <REASON>` is
  mandatory**, before the `--`.
- `session_log.py write` rejects a string `blockers`; it must be a **list of
  strings**.

## Key Decisions

**New top-level section, not a status note.** Operator's explicit choice from
three offered. Paper §7 "Building on CFEngine: what the substrate cost"
(§7.1–7.5); guide §19 "What we found underneath". Rejected alternatives: a
paragraph in the validation section, and folding it into §2.3's
substrate-choice argument as risk disclosure.

**Dropped the dedication, kept the acknowledgement.** Operator: *"You
shouldn't mention Narayan Desai directly… He hasn't seen any version yet and
I want his unguided reaction."* So `Prepared 2026-08-13 for Narayan Desai`
was removed from the front matter. The Acknowledgements still thank him by
name alongside 13 Bcfg2 co-authors — judged ordinary scholarly credit for
cited work rather than a cue, since §6 is built entirely on those papers.
**Flagged to the operator as their call; still undecided.**

**Added §7.4 "Who wrote the fixes."** Discloses that the defects were found
and mostly drafted by AI agents, and what the discrimination-proof and
review-panel gate had to catch — including two of *our own* overstated
claims to upstream. Reasoning: the linked register already discloses it, the
paper's thesis is machine authorship, and a reader who clicks through would
read the omission as concealment. Flagged as easy to cut.

**22 of 23, not 23 of 23.** Refused to manufacture a test for #6308. A green
test asserting a difference the build cannot express is the same fault as
B-13's self-consistent codec — see `test-with-conformant-decoder`.

**Offered nickanderson the option to close #6308.** Both correction comments
end by saying closing it on the fragility-removal basis is reasonable, with a
commitment not to re-open. Rationale: he complained about volume on this exact
PR, and we had just downgraded it from bug fix to hygiene.

## Evidence & Data

**Test-coverage audit, extended from 17 branches to all 26 open PRs.**
Verified from `gh pr view <n> --repo <r> --json files`, not from register
prose. All eight previously-unaudited defect PRs already ship tests:

| PR | Test files in diff |
|---|---|
| #6315 | `12-variable-references-name-offender.cf{,.json}`, `15-…-metadata-format.cf{,.json}` |
| #6316 | `13-null-values.cf{,.json}` |
| #6317 | `14-dotted-keys.cf{,.json}` |
| #6318 | `tests/unit/evalfunction_test.c`, `01_vars/02_functions/eval.cf` |
| #6319 | `00_basics/def.json/null_values.cf{,.json}` |
| #6320 | adds `16-variable-references-good-entry-survives.cf{,.json}` |
| libntech#297 | `tests/unit/json_test.c` |
| libntech#298 | `tests/unit/mustache_test.c` |

`#6307` touches only `libpromises/*` + `tests/unit/Makefile.am` — no new
test, but takes `process_test` off the macOS XFAIL list, so upstream's own
suite now guards it. `#6308` touches **only `cf-agent/nfs.c`** — the one
genuine gap.

**Counting note that keeps causing errors:** 26 open PRs = **23 defect fixes
+ 2 features (#6293/#6294) + 1 pure test coverage (libntech#296)**. Core 20,
libntech 6, verified live twice with
`gh pr list --repo <r> --state open --author djbclark --json number -q length`.

**#6308 is unobservable, and this is the load-bearing finding.** Read from
`/Users/djbclark/src/core-mountleak` on branch `fix/mount-options-timeout-leak`
(`9dd5eb51c`):

| line | what | conditional? |
|---|---|---|
| `nfs.c:1436` / `:1461` | `SetTimeOut(timeout)` — the arm | per method |
| `nfs.c:1472` | `alarm(0); signal(SIGALRM, SIG_DFL);` — **the fix** | unconditional |
| `nfs.c:1476` | `LiveMountConverged()` → `LoadMountInfo()` | unconditional fall-through |
| `nfs.c:403` | `SetTimeOut(RPCTIMEOUT)` — **re-arms** | **unconditional, ahead of early returns at `:408`, `:427`, `:487`** |
| `nfs.c:581` | `alarm(0); signal(SIGALRM, SIG_DFL);` | normal path only |

Because `:403` precedes every one of `LoadMountInfo()`'s own early returns, it
overwrites the alarm state on **every** path. Patched and unpatched builds are
indistinguishable outside `ReconcileMountOptions()`. The severity correction
(comment 159434) said this for the normal path; it holds for all of them.

**Upstream corrections posted:**
- `cfengine/core#6308` → `issuecomment-5336528513`
- `CFE-4732` → comment **159468**, HTTP 201, author "Daniel Clark" confirmed
  from the response body.

**Lints, final:** `xref_lint` 854 sections / 0 findings; `schema_lint` OK
(8 / 59 / 6 / 27 = 92 negative fixtures).

**Document sizes** after the main pass: guide 11,886 words, paper 16,664.

## Operator Feedback

- **Weighting:** *"New section — it's the empirical result"* — chosen over a
  status note or a substrate-risk framing in §2.2/§2.3.
- **Audience:** *"It is for both the public and Narayan Desai. You shouldn't
  mention Narayan Desai directly, but you should keep in mind he is the
  primary target, so still mention Bcfg2 stuff. He hasn't seen any version
  yet and I want his unguided reaction so no need for a cover note."*
- **On the audit:** *"Would it make sense to improve the audit to also cover
  the 6 uncovered branches, so we can say all 23?"* — the "6" was inferred
  from 23−17; the true figure was 8, because the 17 included two features.
- **On the gap:** *"Look into closing the gap so we can just say all of
  them :-)"* — investigated properly rather than complied with; it cannot be
  closed, and saying so was the better outcome.
- **On upstream:** *"Yes, please post correction to both."*
- Standing, from memory and confirmed in practice: commit and push at
  milestones without asking; be terse (three independent upstream data
  points now, two of them maintainers on the same day).

## Where We're Going

1. **THE NEXT ACTION — decide where these documents actually go.** Nothing
   has been posted or sent. Both now carry *"Draft, circulated for comment.
   Not submitted for publication."* in their front matter. That banner,
   `README.md`, and the repo's public-facing framing likely need one more
   pass once a venue exists. This is the half of the original request that
   is still open, and it is the operator's decision, not a research task.
2. **Operator's call, deliberately left open:** strike the Acknowledgements
   mention of Narayan Desai, or keep it? Kept as scholarly credit; the
   dedication line was removed. If even the acknowledgement is too much of a
   cue for an unguided reaction, remove it from
   `docs/paper/tendcf-architecture-paper.md` (Acknowledgements section).
3. **Watch `cfengine/core#6308`.** The correction offers nickanderson the
   option of closing it as fragility removal, with a commitment not to
   re-open. If he closes it, B-15 drops out of the 23 and the audit becomes
   **22 of 22** — update paper §7.1, guide §19, and the register's
   test-coverage section together.
   `gh pr view 6308 --repo cfengine/core --json state,comments`
4. **Optional: a review panel scoped to the NEW material only** — paper §7
   and §1.1's trust/consent bullets, guide §19 and §16.C. The other 13
   review files under `docs/paper/reviews/` already cover the rest, so a
   whole-document panel would mostly re-tread. Run on a read-only copy per
   `reviewer-clis-edit-the-tree`; pin models per `reviewer-seats-model-check`.
5. **Standing:** 26 upstream PRs open, CI green on all, awaiting reviewer
   action. Nothing blocked on us.

## Quick Start

```bash
cd /Users/djbclark/src/tendcf
git log --oneline -5                      # expect de7ae63 at HEAD, clean tree

# Both lints — must stay green. NOTE: uv run, not python3.
uv run bin/xref_lint.py                   # 854 sections, 0 findings
uv run bin/schema_lint.py                 # 8 schemas, 59/6/27 fixtures

# The two documents this session rewrote
$EDITOR docs/paper/tendcf-architecture-paper.md   # new §7; §9.10-9.16; §1.1 limits
$EDITOR docs/paper/tendcf-architecture-guide.md   # new §19; §16.C; §18 rewrite

# Is the last open upstream question resolved?
gh pr view 6308 --repo cfengine/core --json state,reviewDecision,comments

# Re-derive before re-asserting ANY figure — all are date-stamped 2026-08-18
gh pr list --repo cfengine/core --state open --author djbclark --json number -q length        # 20
gh pr list --repo NorthernTechHQ/libntech --state open --author djbclark --json number -q length  # 6
```

Jira, if a ticket needs updating (never echo the token):

```bash
sudo-secretspec run --reason "<why>" -- sh -c \
  'curl -sS -u "djbclark@gmail.com:$ATLASSIAN_CFENGINE_API_TOKEN" \
    -H "Content-Type: application/json" -X POST \
    "https://northerntech.atlassian.net/rest/api/2/issue/CFE-XXXX/comment" \
    --data @payload.json'
```

Key context files, in the order worth reading them:

- `docs/architecture/upstream-register.md` — the campaign's source of truth;
  §"Test-coverage audit" and §"#6308 — not unit-testable" both rewritten
  this session.
- `docs/architecture/architecture-DEFINITIVE-v3.md` — implementer map; must
  agree with the guide.
- `docs/paper/reviews/README.md` — the 13 existing review passes.
- `/Users/djbclark/src/core-mountleak` — B-15/#6308 worktree, still alive.
