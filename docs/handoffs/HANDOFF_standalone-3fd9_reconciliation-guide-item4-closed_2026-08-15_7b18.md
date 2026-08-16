---
schema_version: 1
handoff_id: 7b18
parent_handoff_ids: [4a48]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 64df1ea9bb8c629ae50fc7f19bbe386400f95068
created_at: 2026-08-15T23:10:21-0400
writer: claude-code
---

# Handoff — closing reconciliation §18 item 4 (guide amendments)

## The Goal

`goal-file-schema-reconciliation-2026-08-15.md` §18 lists five follow-on
edits, operator-gated, landed one at a time across several sessions. Prior
session (handoff `4a48`) landed items 1–3 and logged item 4 (amend
`docs/paper/tendcf-architecture-guide.md` §4/§7/§16.A) as "not started."
This session resumed via `/baton` from `4a48` to work item 4.

## Where We Are

Clean tree, `master` at `64df1ea`, one commit ahead of where this session
started (`7af5e06`, which itself was a local-only handoff commit from the
prior session — now pushed as a side effect of this session's push):

- `64df1ea` — the §7 projection sentence, closing §18 item 4 in full.

`bin/schema_lint.py`: `schema-lint: OK (8 schemas, 43 negative fixtures)`.
`bin/xref_lint.py`: 3 findings, all pre-existing and unrelated (same three
named in handoff `4a48`, confirmed unchanged: two in the E1 adjudication
docs, one in the Grok opinion).

§18 item 4 is now **fully closed**: §4 (YAML claim), §7 (removals
paragraph + projection sentence), and §16.A (preview-channel marking) are
all landed. Item 5 (extend `bin/schema_lint.py` per §13) is the only
remaining item and is **not started**.

## What We Tried

Nothing failed this session, but the starting assumption needed correction:

- **The `4a48` handoff's "item 4 not started" claim was stale, not
  current.** Before writing anything, `git log --oneline -20` and
  `merge-base --is-ancestor` showed a commit `d0c306f` ("docs: guide
  corrections C-9 and C-4 from the reconciliation", dated *before* the
  `4a48` session's own work, at `21:45:42` vs. `4a48`'s `22:53:42`) was
  already an ancestor of `HEAD`. Reading its diff showed it had already
  landed 3 of the 4 guide edits §18 item 4 asks for. The `4a48` handoff
  either predates that commit's landing in its own awareness or simply
  didn't re-check before writing "not started" — either way, the fix was
  to verify against `git log`, not trust the log's claim, per the
  session-handoff skill's own staleness-check step.

## Key Decisions

- **§7's "projection sentence" needed an explicit operator call, not a
  unilateral decision.** `d0c306f`'s own commit message flagged this
  precisely: "§18.4 also lists 'the projection sentence' for §7, but §7
  has no such sentence — the guide never carried E1 §1's 'Augments layer
  consumes' phrasing that C-9 corrects. That item reads as an addition
  rather than a fix, so it is left for whoever confirms the intent." This
  session confirmed the gap was real (`grep -n Augments` on the guide
  showed §7 never mentions Augments at all) and asked the operator via
  `AskUserQuestion` rather than deciding silently, since it's a *new*
  claim being added, not a correction of existing wrong text. Operator
  chose: add it.
- **Where the sentence went.** Inserted into §7's validator paragraph,
  right after "Then it lets CFEngine converge on the new state." — the
  exact point where the prose hands off to CFEngine, which is where the
  goal-file/Augments-shape distinction is load-bearing. Cross-references
  §16.A rather than repeating its `{"vars": {…}}` illustration verbatim.
- **Rejected: leaving item 4 marked "3/4 done, one deferred" indefinitely.**
  The prior commit's own message named this as "left for whoever confirms
  the intent" — an explicit invitation to resolve it, not a permanent
  residue. Since the operator was available and the ambiguity was narrow
  (add one sentence, yes/no), resolving it now was cheaper than writing a
  fourth handoff bullet asking a future session to ask the same question.

## Evidence & Data

- `git merge-base --is-ancestor d0c306f HEAD` → true (exit 0), confirming
  `d0c306f` (guide corrections C-9/C-4) was already landed, contra `4a48`'s
  "not started" claim.
- `uv run bin/schema_lint.py` → `schema-lint: OK (8 schemas, 43 negative
  fixtures)` (confirmed after the commit).
- `python3 bin/xref_lint.py | grep -vE 'reviews/|deprecated/|handoffs/'` →
  3 findings, all pre-existing (unchanged from `4a48`'s baseline):
  `docs/architecture/e1-adjudication-2026-08-15.md:316`,
  `docs/architecture/e1-adjudication-xhigh-2026-08-15.md:49`,
  `docs/architecture/goal-file-schema-opinion-grok.md:278`.
- `git diff --stat` for `64df1ea`: 1 file changed, 7 insertions(+), 1
  deletion(-) in `docs/paper/tendcf-architecture-guide.md`.
- The added text (guide §7, after the validator paragraph's CFEngine
  hand-off sentence): "CFEngine's Augments layer never sees the goal
  file; a policy-free projection step, run only after approval, re-keys
  the approved state into the narrow `{"vars": {…}}` shape Augments
  actually consumes (§16.A). The goal file is the object consent binds
  to; the projection is derived from it, not signed itself, and is not
  the whole document."

## Operator Feedback

- Asked via `AskUserQuestion` whether to add the projection sentence now
  (recommended) or leave it as named residue. Operator: "Add it" —
  confirming the standing pattern from `4a48`'s log (finish small,
  well-scoped items when asked, rather than deferring by default).

## Where We're Going

1. **THE NEXT ACTION — §18 item 5: extend `bin/schema_lint.py` per
   reconciliation §13.** Byte-class fixture mechanism (raw bytes compared
   before parsing — pretty-printed twins, duplicate keys, non-NFC
   strings, a `15.0` spelling of `15`), JCS idempotence checking as a
   lint layer (not just the one-off script used during fixture
   authoring), goal-file/goal-diff hunk-consistency cross-check ("applying
   hunks to old yields new"), and projector goldens (blocked on an actual
   projector implementation, which doesn't exist yet — skip that part
   until it does). This is real engineering, not a doc edit; start fresh,
   per `4a48`'s own guidance, not tacked onto a doc-edit session. Read
   reconciliation §13 in full before starting:
   `sed -n '/^## 13\./,/^## 14\./p' docs/architecture/goal-file-schema-reconciliation-2026-08-15.md`.
2. Once items 4 and 5 land, `goal-diff.schema.json` and
   `approval-record.schema.json` are candidates for a proper adversarial
   fixture set (currently outline-only, per `4a48`'s Key Decisions) — not
   blocking, worth revisiting once the byte-class harness exists to reuse.
3. Unrelated, low-priority, carried from `4a48`/`b0ff`: confirm
   `track-issue-activity.yml`'s Discussion path fires in site-djbclark —
   last scheduled run predates PR #158's merge, so it has never run live.
4. Unrelated to this repo: `~/src/cfengine-core` still shows a dirty
   `libntech` submodule — do not commit it. The three CFEngine PRs
   (`libntech#291`, `cfengine/core#6293`, `#6294`) are independent and
   all filed; no action needed there.

## Quick Start

```bash
cd ~/src/tendcf
git log --oneline -5   # confirm HEAD is 64df1ea or a descendant
uv run bin/schema_lint.py   # expect: schema-lint: OK (8 schemas, 43 negative fixtures)
python3 bin/xref_lint.py | grep -vE 'reviews/|deprecated/|handoffs/'   # expect: 3 pre-existing findings, unrelated

# Start item 5 (extend schema_lint.py per §13):
sed -n '/^## 13\./,/^## 14\./p' docs/architecture/goal-file-schema-reconciliation-2026-08-15.md
cat bin/schema_lint.py   # current lint surface to extend
```
