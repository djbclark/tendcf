---
schema_version: 1
handoff_id: b0ff
parent_handoff_ids: [ebe4, 4830]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: aeb75d762f3353a38eaee74af2508c747ad319fa
created_at: 2026-08-15T22:14:05-0400
writer: claude-code
---

# Handoff — Schema reconciliation landed; glossary and xref lint built

## The Goal

Resumed from `4830` via `/baton`. The inherited next action was the deferred
schema reconciliation pass, gated behind a 21:10 timer that had died with its
session. The operator's first instruction was to make that timer live again;
everything else followed from what the timer's job produced.

Two parents, both real. `4830` is the one this session resumed from. `ebe4`
was written by a *different* session running concurrently under the mit.edu
account, and the operator pasted its close-out into this session mid-flight —
so this session's later work descends from it directly, not just
chronologically.

## Where We Are

| Workspace | Path | Branch | HEAD | State |
|---|---|---|---|---|
| tendcf | `~/src/tendcf` | `master` | `aeb75d7` | clean, **pushed** |
| cfengine-core | `~/src/cfengine-core` | `simulate-keep-chroot` | `00c98bc8b` | ` M libntech` — expected, do not commit |
| libntech | `~/src/cfengine-core/libntech` | `silent-digest-failure` | `dc85a6f5` | clean |

Six commits landed, all pushed:

- `131158f` — `ebe4`'s handoff, committed by the other session and left local;
  pushed from here at the operator's word.
- `48050f8` — paper de-staled for Model B.
- `2fcb366` — the goal-file schema reconciliation.
- `0e4eada` — `docs/architecture/GLOSSARY.md` + README pointer.
- `d0c306f` — guide corrections C-9 and C-4.
- `aeb75d7` — `bin/xref_lint.py`.

**The reconciliation is the headline.** `fable-deep` (claude-fable-5, xhigh)
produced `docs/architecture/goal-file-schema-reconciliation-2026-08-15.md`,
1282 lines, adjudicating the three cold opinions into one binding design for
`schema/goal-file.schema.json`. The schema file itself was deliberately **not
created** — that is `§18 item 1`, still gated.

**A live inconsistency was created on purpose and must be closed.** The guide
now describes removals as tombstones (C-4); `architecture-DEFINITIVE-v3.md`
still describes removal-as-diff-compilation. `README.md` makes the guide the
top authority and says the map must agree with it, so the map is currently
wrong by the repo's own precedence rule. Closing it is `§18 item 3` and is the
next action.

## What We Tried

Chronological, including what failed.

1. **Re-created the timer with `CronCreate`, which is also session-only.**
   Its `durable` parameter is explicitly a no-op. Flagged to the operator
   rather than presented as a fix; it fired correctly at 21:10 and the job
   ran. A durable equivalent (launchd/`at` firing a desktop notification to
   run `/baton`) was offered and not taken up.
2. **The cron brief I wrote was stale by the time it fired.** It was composed
   against `4830`, and between 19:08 and 21:10 another session filed all three
   CFEngine PRs and wrote two more handoffs. The gates in the brief (re-read
   Tier 1, re-read the handoff it *names*) caught this — but only because they
   said "the handoff it names" rather than naming `4830` outright. **Write
   deferred-job briefs to re-derive state, never to carry it.**
3. **`cswap list` served a stale pre-reset snapshot and nearly produced a
   wrong go/no-go.** At 21:10 it reported account 2's 5h at **97%** with
   "resets 21:10 in 0m" — a ~3-minute-old cache straddling the reset boundary.
   Two consecutive `cswap list` calls agreed with each other and were both
   wrong. `cswap status` returned the fresh number: **1%**, a full 4h58m
   window. There is no `--refresh` flag, and `cswap current` is not a
   subcommand (it is `cswap status`).
4. **First `xref_lint.py` draft reported 123 findings, ~75 of them false.**
   `§14.2` appeared broken in every document citing it, which is the tell: one
   document disagreeing with a tool is a finding, the whole corpus disagreeing
   is a bug in the tool. The map defines those subsections as `- **§14.2**`
   list items, a heading form the extractor did not know. Two further
   extractor bugs: the qualifier window was loose enough to read `E1 R4/§9.8`
   as an E1 reference when `§9.8` belongs to the map, and the three opinion
   files were not registered as citable at all. 123 → 48 → 47.
5. **Wrote a bad cross-reference while writing the guide's YAML fix** — cited
   `§14` for the Site Model's authoring format; `§14` is "Per-device trust."
   Caught and corrected to `§7` before committing. This was the *second* bad
   ref of the session and is what prompted the lint.
6. **Duplicated a word mid-edit** (`a typo'd / typo'd token kind`) when
   replacing text that spanned a line break. Caught on the next read.
7. **Held two guide edits while Fable was running.** Items 2 and 3 of the
   batched doc work both edit `tendcf-architecture-guide.md`, which was in
   Fable's corpus (§7), and both concern `host_specific.json` — the exact
   subject of its hard part 7. Deferred until it finished rather than risk
   colliding with an active reader or doing work its adjudication would
   supersede. Correct call: `§18 item 4` did change what those edits should say.

## Key Decisions

**The reconciliation was launched at `fable-deep`/xhigh on account 2, and the
effort was verified rather than assumed** — `~/.claude/agents/fable-deep.md`
carries `model: claude-fable-5` and `effort: xhigh` in frontmatter, so the
effort could not be silently wrong. Account routing mattered: account 1
(mit.edu) has no Fable entitlement, and `cswap switch` only affects new
sessions, so this session was the only one that could run it.

**The glossary is a pointer index, not a second source of truth.** Each entry
cites an authority and defines nothing; the file places itself *below* the
guide and the map in `README.md`'s existing precedence order. Rejected: a
conventional glossary that restates definitions — that is a fourth place to
drift alongside the paper, guide, and map, which is the failure `48050f8`
had just repaired.

**Glossary scope is deliberately narrow** — only words with two live senses,
and words whose referent moved under a decision. Rejected: a general project
dictionary. Admitting ordinary stable terms is how a glossary stops being
read.

**`xref_lint.py` was built but fixes nothing.** Splitting "build and measure"
from "fix what it finds" was the point: it converts an open-ended idea into a
sized work item. Rejected: fixing the 47 findings in the same pass, which had
unknown size before measuring.

**Three things deliberately not done**, all gated: `schema/goal-file.schema.json`
(`§18 item 1`); the 47 xref findings; and `§18 item 4`'s "projection sentence" for guide
§7 — the guide has no such sentence, so that item reads as an *addition*
rather than a fix and needs the author's intent confirmed.

**Auto-memory corrected, not just noted.** `upstream-artifacts-need-approval`
claimed the upstream PR/Jira gate was hook-enforced. It was removed on
2026-08-15. Verified independently before rewriting: zero `upstream_review_gate`
references in live `settings.json` or `settings.local.json`, no `hooks` key in
the latter, nothing replacing it. The script still sits on disk at
`~/.claude/hooks/upstream_review_gate.sh` **unwired** — its presence is not
evidence it runs. The memory now says asking is judgment, not enforcement.

## Evidence & Data

- **Fable run:** 222,183 tokens, 31 tool uses, 1,211,247 ms (~20 min). Output
  1282 lines. Scope verified: the three opinion files, the brief, and the E1
  adjudication are byte-untouched (`git diff --stat HEAD` empty for all five),
  and `schema/` gained nothing.
- **RFC 8785 claim verified independently**, since the maps-over-arrays
  overrule rests on it: JCS sorts object members by UTF-16 code units, not
  UTF-8 bytes. `U+E000` vs `U+1F600` invert between the two orderings —
  demonstrated by running it, not reasoned about.
- **`xref_lint.py` clean run:** 71 documents, 544 sections, **47 findings**.
  Most are in `reviews/` and `deprecated/`, which `README.md` marks as an
  evidence trail not to be rewritten. Five are in live design documents.
- **Two of those five are real:** the reconciliation cites `Grok §9.12` at
  lines 430 and 1159; the Grok opinion has top-level sections 0–13 and the
  string `9.12` appears nowhere in it. Both citations carry weight ("violates
  its own no-speculative-kinds rule (§9.12)").
- **Quota at the 21:10 reset:** account 2 (gmail) 5h 97% → **1%**, resets
  02:10, 4h58m window; 7d 20%; Fable 22%. Account 1 (mit.edu) 5h 48%, no Fable
  line.
- **Telegram Discussion path still unexercised:** last scheduled run of
  `track-issue-activity.yml` was `2026-08-16T00:53:46Z`; PR `#158` merged
  `00:55:02Z`. It missed by **76 seconds**, so every green run predates the
  new GraphQL code path. Operator explicitly deprioritized: "we can just wait
  for the issue tracker to fire, it's not that important."
- **Paper de-stale was mischaracterized in prior handoffs** as a "capability
  vocabulary rename." It was not: §2.5 described **Model A in the present
  tense** — a typed ChangePlan whose operations each declare a `capability`,
  with an executor refusing effects outside the declared set — a design D43/E1
  withdrew. Eight `capability` sites classified by hand; three at paper
  §2.7/§2.8/§6.5 are the *security* sense and keep the word per DOC-4
  (`b46d6e9`). A blanket rename destroys exactly the distinction DOC-4 drew.
- **Tests run:** no test suites. `bin/xref_lint.py` exercised against the real
  corpus (its own false-positive rate was the test, and drove three fixes).
  `bin/schema_lint.py` not run — no schema changed this session.

## Operator Feedback

- **"Make the cron job timer live again."** Done, with the session-only
  caveat stated up front rather than after.
- **"We can just wait for the issue tracker to fire, it's not that
  important."** Explicit deprioritization of `ebe4`'s stated next action.
- **"What can we do while we are waiting for fable?"** — an invitation to
  propose, not an instruction. Answered with an assessment of what would and
  would not collide with the running agent.
- **"Would it make sense to put a glossary ... somewhere?"** Answered as a
  question and deliberately **not acted on**, per `ebe4`'s recorded pattern
  that this operator distinguishes "explain it to me" from "act on it." The
  instruction came separately: **"Make the glossary, and commit the
  reconciliation."** The pattern held and is worth preserving.
- **"should this be done now, or put in as the first thing to do next time
  and then do a handoff?"** — the operator asks genuine either/or scoping
  questions and wants a recommendation with reasoning, not a silent pick.
- **"Push it yourself whenever you want"** (re: `131158f`) — pushing tendcf is
  fine; `11e3`'s no-push-in-place reasoning does not bind.

## Where We're Going

1. **THE NEXT ACTION: land `§18 item 3`, the seven `architecture-DEFINITIVE-v3.md`
   amendments.** This is not optional cleanup — the guide moved to tombstones
   in `d0c306f` and the map still says removal-as-diff-compilation, so by
   `README.md`'s own precedence rule the map is currently wrong. The seven, as
   the reconciliation lists them: §9.2 (maps, C-2/C-3), §9.7 (single-enum
   coverage C-1, undeclared class C-10), §9.8 (tombstone restatement C-4,
   ceremony table §4.3), §9.6 (drop the release-lint phase-order clause C-6),
   §9.1 (C-5 signing construction), the §9 preamble (the not-settled-by-E1
   paragraph closes: projection is device-side, §9), §4.1 (edge-origin scope
   note, C-8).
2. **Fix the two real xref findings** — `Grok §9.12` at
   `goal-file-schema-reconciliation-2026-08-15.md:430` and `:1159`. Determine
   what Grok section was actually meant before editing; do **not** edit the
   opinion file to match.
3. **`§18 item 1`: land `schema/goal-file.schema.json`** from the reconciliation's
   §10, with `examples/goal-file.json` in canonical bytes and the §10/§13
   negative sets; then `goal-diff` and `approval-record` from §11; then the
   §14.2 review — before any validator code.
4. **`§18 item 2`:** edit `schema/report-row.schema.json` and
   `examples/report-rows.yml` per §12 (required `schema_ceiling`, optional
   `validator_version` on `device_convergence`).
5. **`§18 item 5`:** extend `bin/schema_lint.py` per §13.
6. **`§18 item 4` leftover:** the "projection sentence" for guide §7. Confirm
   intent first — §7 has no such sentence, so this is an addition.
7. **Confirm the Telegram Discussion path fires** on a real scheduled run.
   Low priority per the operator.
8. **Read the reconciliation's §16 and §18 properly.** §16 is written as the
   strongest case *against* its own design (maps fallback path, projector-on-
   Android exposure, guaranteed early bumps, tombstone fatigue counter). It
   was committed unreviewed by a human or by me line-by-line.

**Traps, live:**

- `~/src/cfengine-core` shows ` M libntech` — **do not commit it**; the three
  CFEngine PRs are independent.
- **`cswap list` can serve a stale cached snapshot across a reset boundary**,
  and repeating it does not help. Use `cswap status` for the authoritative
  number when timing matters.
- **`xref_lint.py` catches dangling refs, not mis-aimed ones.** A `§14` that
  should be `§7` resolves fine and passes silently — the class that actually
  bit this repo. The lint is a floor, not a substitute for reading the target.
- **Never edit the three `goal-file-schema-opinion-*.md` files.** They are the
  record of what each model said cold.
- **`xref_lint.py` reports three findings against *this handoff*, all
  `§9.12`.** They are deliberate quotations of the real defect in item 2
  above — a document that records a broken reference necessarily contains
  one. Do not "fix" them; fixing them destroys the record. They clear on
  their own once item 2 lands.
- `reviews/` and `deprecated/` xref findings are an evidence trail; `README.md`
  says do not rewrite them to bring them up to date.

## Quick Start

```sh
# Tier 1 pointer
~/.claude/hooks/handoff-tools/.venv/bin/python \
  ~/.claude/hooks/handoff-tools/session_log.py read \
  --state-root ~/.local/state/handoffs --dir ~/.local/state/handoffs/tendcf/main

# The next action's inputs
cd ~/src/tendcf
sed -n '1248,1268p' docs/architecture/goal-file-schema-reconciliation-2026-08-15.md  # §18
sed -n '1073,1182p' docs/architecture/goal-file-schema-reconciliation-2026-08-15.md  # §15 corrections
grep -nE '^### 9\.' docs/architecture/architecture-DEFINITIVE-v3.md                  # the seven targets

# Cross-reference lint (stdlib only, no uv needed)
python3 bin/xref_lint.py
python3 bin/xref_lint.py | grep -vE 'reviews/|deprecated/|handoffs/'   # live docs only

# Schema lint — MUST run this way; bare python3 fails on jsonschema
uv run --with jsonschema bin/schema_lint.py

# Quota — `cswap list` can be stale across a reset; this is authoritative
cswap status

# Telegram Discussion path, when someone cares
gh run list --workflow=track-issue-activity.yml -R djbclark/site-djbclark -L 3
gh workflow run track-issue-activity.yml -R djbclark/site-djbclark -f notify_even_if_unchanged=true
```
