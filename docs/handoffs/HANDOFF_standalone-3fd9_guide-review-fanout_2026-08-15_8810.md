---
schema_version: 1
handoff_id: 8810
parent_handoff_ids: [c174]
lineage: inferred
chain: [standalone-3fd9]
repo: tendcf
workspace: N/A (plain repo checkout, not an ops-worktrees task workspace)
branch: master
head_sha: 37a37c4a664032f47de79b67ff2660103274b3db
created_at: 2026-08-15T10:12:52-0400
writer: claude-code
---

# Handoff — six-reviewer fan-out on the vetted guide, and the synthesis

**Lineage note.** `parent_handoff_ids: [c174]` is *inferred*, not deterministic.
This session did not start from a resume prompt. `c174`
(`architecture-paper-ai-reviews`, 2026-08-13) is the prior AI-review round on
these same documents, and this is the next such round, so it is recorded as the
parent. **c174's own "Where We're Going" items were NOT done by this session** —
see Open Questions.

## The Goal

Review `docs/paper/tendcf-architecture-guide.md` (964 lines, 19 sections), the
document that declares itself authoritative over every other living document on
current design. It had never been reviewed: every brief in `docs/architecture/`
and all three reviews in `docs/paper/reviews/` are marked Archival and target
either the technical paper or now-deprecated proposal drafts, all dated
2026-08-13. The guide is dated 2026-08-14.

Secondary goal, added mid-session by the operator: farm the review passes out to
separate Herdr panes running specific Claude models at specific effort levels,
rather than running them in one session.

## Where We Are

**The guide itself is untouched.** No tracked file changed. Working tree carries
seven untracked files, all review output:

```
docs/paper/reviews/2026-08-15_opus-5_consistency-audit.md          13K
docs/paper/reviews/2026-08-15_opus-5_guide-paper-parity.md          8K
docs/paper/reviews/2026-08-15_sonnet-5_exposition-structure.md     19K
docs/paper/reviews/2026-08-15_opus-5-xhigh_skeptical-review.md     52K
docs/paper/reviews/2026-08-15_opus-5-max_redteam-trust-consent.md  90K
docs/paper/reviews/2026-08-15_opus-5-high_premortem.md             40K
docs/paper/reviews/2026-08-15_opus-5-xhigh_SYNTHESIS.md            61K
```

Plus this handoff. All seven review docs are **uncommitted** at time of writing.

Six passes ran. Two (A, A-2) in the orchestrator session; four in dedicated
Herdr panes; one synthesis in a seventh pane on the second Claude account.

| Pass | Agent | Model / effort | Result |
| --- | --- | --- | --- |
| A consistency audit | (orchestrator) | opus-5 / medium | CONCERNS — 2×P1, 3×P2, 2×P3 |
| A-2 guide↔paper parity | (orchestrator) | opus-5 / medium | CONCERNS — parity holds, 1×P1 |
| B skeptical review | `peerreview` | opus-5 / xhigh | **major revision** |
| C red-team §§7-9,14-15 | `redteam` | opus-5 / **max** | 51 findings: 7 Crit / 28 High / 14 Med / 2 Low |
| D exposition + citations | `exposition` | sonnet-5 / medium | both numeric claims verified exact |
| E pre-mortem | `premortem` | opus-5 / high | 36 causes in 3 buckets |
| F synthesis | `synthesis` | opus-5 / xhigh | 44 design changes, 47 document changes |

Herdr layout, all panes idle, none closed (operator convention: minimize, never
close):

```
tab orc  ├ orc                (this session)
         ├ review-redteam     w1H:pE
         ├ review-exposition  w1H:pF
         ├ review-peer        w1H:pG
         ├ review-premortem   w1H:pH
         └ review-synthesis   w1H:pJ
```

Foreign tabs also renamed this session (they were `1`–`5`): `shell-tendcf`,
`cursor-effort`, `claude-aiuse`, `shell-aiuse`. Nothing inside them was touched.

## What We Tried

Failed approaches and near-misses, chronological. These are the expensive ones
to rediscover.

1. **Nearly filed `§0 rule 6` as a stale cross-reference.** `common.schema.json`
   and `bin/schema_lint.py:20` both cite it. Three *other* cross-references in
   the same file are genuinely wrong, so the fourth looked wrong by association.
   It is correct — `architecture-DEFINITIVE-v3.md` §0 rule 6 really is "prefer
   machine-checkable to conventional." **Do not "fix" it.** The consistency
   audit says so explicitly, in the P2 row.

2. **`aiuse --json`'s `conserve` alert caused an over-cautious staging decision.**
   Both Claude accounts showed `conserve` ("projected to run out before reset"),
   so only 2 of 4 reviewers were launched initially. `cswap list` then showed the
   real numbers: weekly at 4% and 16% used. The alert is a *pace projection*
   extrapolating today's burn across the week, not a depletion measure.
   **Read `cswap list` / `cswap status` directly for go/no-go; treat aiuse's
   alerts as advisory only.** Operator confirmed this correction.

3. **`aiuse --json` does not emit clean JSON on stdout.** It prefixes progress
   lines ("Collecting usage from local tools…", "Saved snapshot to …"). Pipe
   through `sed -n '/^{/,$p'` before `json.load`, or it throws
   `JSONDecodeError: Expecting value: line 1 column 1`.

4. **`herdr agent prompt --timeout` requires `--wait`.** Passing `--timeout`
   alone exits 2 with `--timeout requires --wait`. Prompts were then sent with
   `--wait --timeout 15000`; the resulting `timeout` error is *expected and not a
   failure* (per the herdr-orchestration skill) — verify with `herdr agent get`
   that status is `working`.

5. **First `herdr agent start` on a freshly split pane returned no `result` key.**
   Happened for both `peerreview` and `premortem`. A bare retry ~2s later
   succeeded both times. Add a `sleep 2` between `pane split` and `agent start`.

6. **Cited the prior red-team at the wrong path in the pass-A report.** It is
   `docs/architecture/deprecated/redteam-trust-layer-openai-v1.md`, not
   `docs/architecture/`. The DEFENSIVE-PASS brief's prose has the old location.
   The prompt sent to `redteam` used the correct path; the pass-A report body
   still has the wrong one.

7. **Rejected two candidate skills after reading them in full** — see Key
   Decisions. Reading them was not wasted; it is why `paper-review` was not
   installed.

## Key Decisions

**Chosen: one Claude session per review pass, in its own Herdr pane.** Passes B,
C, and E are only worth running if they are independent. Sharing the
orchestrator's context would have given them my framing to confirm rather than
attack. Confirmed working: `peerreview`'s report states it did not open the
other review files.

**Chosen: model and effort per pass, on task shape not uniformly.**

- `sonnet-5 / medium` for D (structure + citation checks) — evidence gathering,
  not judgment. Completed in 3m16s.
- `opus-5 / xhigh` for B and F — whole-document judgment and synthesis.
- `opus-5 / max` for C only. Justified because correctness mattered more than
  cost on the trust layer. **This was the best-spent quota of the day**: the
  narrow scope (§§7-9, 14-15) returned 51 findings and became the synthesis
  spine. Narrow scope + max effort beat broad scope + high effort.
- `opus-5 / high` for E.

**Chosen: three standing prompt rules for every Opus 5 reviewer**, from the
`claude-api` skill's Opus 5 migration guidance:
1. Report everything with self-assigned confidence + severity; do **not**
   pre-filter. (Opus 5 follows "only report high-severity" literally and
   measured recall drops.)
2. No verification/double-check step. (Opus 5 verifies unprompted; instructing
   it causes over-verification with no accuracy gain — inverts the usual advice.)
3. Deliverable is findings, not edits. (Opus 5 expands scope.)

**Chosen: install 2 review skills, reject 1.** Installed to `~/.claude/skills/`
with `PROVENANCE.md` + LICENSE: `ln-21-documentation-auditor` and
`ln-11-plan-reviewer`, both MIT, from
`levnikolaevich/claude-code-skills` @ `5bf66c5` (2026-08-07), copied unmodified.

**Rejected: `lcrawfurd/claude-skills` `paper-review`.** Read all 304 lines.
Three of its five frameworks are empirical-economics methodology (causal
identification, p-values, clustered standard errors) with no bearing on a
systems design doc. Repo has **no LICENSE**. Only the Edmans triad and the
Evans/Bellemare structural check transfer; both were folded into passes B and D
by hand instead.

**Rejected: `ln-24-architecture-auditor`** (same repo as the two installed). Its
own description says it audits "the architecture the system *actually
executes*" and explicitly not current-state documentation. Nothing is deployed,
so it has nothing to audit. Revisit after Step 1.

**Rejected: `awesome-skills/code-review-skill`.** 21k lines of per-language code
review; duplicates built-in `/code-review` and does nothing for a design doc.

**Operator decisions, recorded as constraints — do not re-litigate:**
- The planning-stage, prose-first state is **accepted, not a symptom.** The
  pre-mortem's documentation-to-code ratio framing (53 of 55 commits `docs:`;
  16,276 lines prose vs 1,024 lines code) is discounted. Its *other* findings
  stand, including the empty `nix2cf` repo and the underestimated build steps.
- **Documents stay in confident present tense** describing the designed system,
  with existing not-yet-deployed caveats where they are. No hedging into
  conditionals.
- Synthesis ran on Claude account 2 via `cswap switch 2` (operator chose option
  1 — global switch — over a per-pane `cswap run` wrapper).

**Deviation, recorded:** passes A and A-2 ran in the orchestrator session on
`opus-5 / medium`, not the planned `sonnet-5 / high` in a clean session, at
operator request ("run it"). Both reports flag this in their residual-risks
section. Acceptable for consistency auditing (findings are file-anchored and
re-checkable); would not have been acceptable for B/C/E.

## Evidence & Data

**Findings that are verified fact, not opinion** (checked against the repo this
session — a later reader can trust these without re-deriving):

- `bin/schema_lint.py:49` drives schema↔example pairing from a hardcoded
  four-entry `EXAMPLES` dict. `check_schemas_valid` globs `schema/*.schema.json`
  for validity only. **A new schema with no fixture is not caught**, and neither
  is a new example not registered in the dict. `schema/common.schema.json`
  already has no fixture and is an unmentioned exception. Guide §3:167 claims
  the lint fails in both directions. It does not. (Pass A, P1.)
- `schema/common.schema.json` `$defs.release_stamp` cites `guide §8` for release
  stamping. Guide §8 is "The person's own AI"; release stamping is guide §6:298.
  (Pass A, P1.)
- Same file, `$defs.domain_coverage` cites `§12 Step 0` — DEFINITIVE-**v2**
  numbering. Build order is §13 in v3, §18 in the guide. `deprecated/architecture-DEFINITIVE-v2.md`
  uses `§12 Step 0`/`§12 Step 4` throughout, confirming it survived the v2→v3
  renumbering. (Pass A, P2.)
- Guide §15 and paper §2.9 both list six token kinds plus an ellipsis. The
  schema's `capability_token` pattern admits **eight**:
  `service|port|path|class|package|device|network|secret`. `package` and
  `device` are hidden behind the ellipsis in both documents. (Pass A F4 / A-2 P2;
  the red-team found this independently as TC-45 and additionally caught that
  two different closed lists both use the word "capability".)
- Paper §2.6 promises "**verbatim excerpts**" and "values unchanged", then
  Example B's interlock description reads "**The mesh VPN** must be
  authenticated…" where `examples/services.yml:39` reads "**Tailscale** must be
  authenticated…". Guide §16.B has the same altered wording under a weaker
  provenance claim. **The two documents agree; the fixture is the outlier.**
  One string, either direction. (Pass A-2, P1.)
- **Verified correct, do not re-check:** guide §18 build order and map §13 build
  order agree on all eleven rows. Interlock `blocks`/`report` really are `const`
  + `required` + `additionalProperties: false` in the schema — stronger than the
  guide claims. `examples/broken/` has exactly 12 cases; `EXPECTED_BROKEN = 12`.
  Six of six broken fixtures named in paper §7 map to real directories. Both
  Bcfg2 numeric claims (the `0 / 2308` first-run transcription and the FTE
  figures) confirmed exact against primary sources by pass D.

**The synthesis spine — five root causes, ~91 findings:**

- **S1** (strongest convergence; four reviewers, independently): the document's
  risk apparatus is inversely correlated with its risk. Fifteen conceded
  weaknesses across §10/§17/§19 — six to ordering, three to comprehensiveness,
  three to local-first reporting, **zero** to signing, keys, root rotation,
  consent, refusal, peer authorization, or transport. The red-team then produced
  51 findings there. Mechanism: *the guide is humble where Bcfg2 supplies a
  ready-made counter-argument, and confident where nothing external exists to
  argue back.* ~40 findings.
- **S2**: every control in the trust layer is authored, delivered, and evaluated
  by the party it exists to constrain. Class fix proposed: a device-local trust
  root the release path cannot write.
- **S3**: §9's own standard never applied to the document's own load-bearing
  claims.
- **S4**: the precedence rule makes the least-specified document normative (the
  guide wins on conflict and is weaker than the map on several security
  properties — red-team TC-51, promoted to root cause).
- **S5**: the riskiest, most falsifiable claims are scheduled last.

**E1 — the synthesis-only result.** The skeptical review's Alternative A
(reached from security analysis) and the pre-mortem's CUT-1 + CUT-3 (reached
from build-cost analysis) are the same architecture: no inference stage; render
a complete resolved goal file per host; **the ChangePlan is mechanically the
diff** between the host's currently-signed goal file and the proposed one;
executor allowlist derived from the diff rather than a hand-maintained
vocabulary. Structurally immune (not merely mitigating) to TC-29, TC-32, TC-31,
TC-10, TC-26. Two survive: TC-25, and TC-23 ("package installs still run vendor
code"). **Neither source report makes this argument** — it exists only because
the two were read side by side.

**Prior red-team disposition (RT-01…RT-09):** zero cleanly resolved. Two
(RT-05 builder/cache, RT-07 lease/fencing) moot *by removing surface* — the
red-team calls this the design's best security work. Three show real movement
with a claim-vs-mechanism gap. Four substantially unchanged. RT-02's freeze half
is flagged as **falsely claimed resolved**.

**Quota consumed** (both accounts, 2026-08-15):
- Account 1 `djbclark@mit.edu`: 5h window 36% → 82% (four reviewers + two
  in-session audits). Weekly 4% → 9%. Resets 13:49.
- Account 2 `djbclark@gmail.com`: 5h window 0% → 36% (synthesis alone). Weekly
  16% → 19%. Resets 14:40.

## Operator Feedback

- "Using up today's quota for just this is fine." Read `cswap` directly rather
  than trusting aiuse's pace alerts.
- "Name all the herdr panes things that make sense." Done — see layout above.
- Prose-first planning state is accepted; discount the docs-to-code framing.
- "We should write as though the project is working" — confident present tense.
- Preference confirmed by the herdr-orchestration skill and honored: **never
  close panes or tabs**, minimize instead.
- Wanted an ELI5 executive summary of findings for non-technical reading; one
  was delivered conversationally and is **not** written to a file. Worth
  producing as an artifact if it is wanted durably.

## Where We're Going

1. **START HERE — write the ChangePlan schema, the capability enum, and the
   trust-policy shape, with paired examples and negative fixtures, and exhibit
   one plan end to end in guide §16. Add all three to Step 0.** Days of work.
   This is the synthesis's #1 of 8 and the highest-priority item in the corpus:
   ~30 of the red-team's 51 findings are *about* this artifact and cannot be
   adjudicated while it remains a phrase in a sentence (TC-02, TC-10, TC-11,
   TC-13, TC-15, TC-26, TC-28, TC-29, TC-31, TC-33 all become schema review the
   moment it exists, and several may dissolve). It needs no fleet, no compiler,
   no code — it is the one piece of the trust layer that is Step-0-shaped, in a
   project deliberately at Step 0. Include the reject path and the device's
   state afterward. Note the irony worth stating in the commit message: guide §9
   rule 2 says a convention an agent must remember will break silently, and this
   vocabulary is currently exactly that.
2. **Commit the seven review documents** (see Quick Start) and add a section to
   `docs/paper/reviews/README.md` for the 2026-08-15 guide reviews — do **not**
   fold them into the 2026-08-13 table, which is Archival and reviews a
   different document. Save each pass's prompt as `prompt_<pass>.txt` alongside,
   matching the existing `prompt_audit.txt` / `prompt_iclr.txt` convention.
3. **Amend the precedence rule (S4), then reconcile the guide with the map** on
   the parameters the guide drops. Synthesis item 2: an hour, then an afternoon.
4. **The thirteen cheap factual corrections** (synthesis item 5), which include
   every P1/P2 from passes A and A-2. The lint pairing P1 is the one with a real
   design choice inside it: derive `EXAMPLES` from the filesystem with an
   explicit allowlist for shared-definition schemas, or reword guide §3.
5. **Extend §19 and rewrite §17 so the risk apparatus covers the trust layer**
   (S1's fix — pure writing, highest value per hour).
6. **Decide E1** — adopt the diff-derived ChangePlan model or not. This is a
   real architecture call and should be made in a **fresh session at `xhigh`**
   reading the synthesis cold. Item 1 will change what this decision looks like,
   so do item 1 first.

## Open Questions

- **c174's action items were not done by this session and their status is
  unknown.** Its next actions were: resolve the paper length question (~5800 vs
  ~3000 words), fix the §4.1 non sequitur, add two findings to §8, reconcile the
  §3 register, verify the bibliography against source PDFs in `~/src/bcfg2/doc/papers/`
  and remove the References warning block, and write Acknowledgements. Commit
  `1bef966` ("align the architecture paper with the vetted guide") landed after
  c174 and may have done some of it. The paper now has an Acknowledgements
  section. **Verify before assuming any of it is done.**
- **Tier 1 is a dangling pointer.** `~/.local/state/handoffs/tendcf/main/SESSION_LOG.md`
  redirects to `chains/standalone-3fd9/SESSION_LOG.md`, which does not exist.
  Created this session — see Step 7 note below.
- The lint was never executed (needs `uv` + network). All findings against it
  are from static reading, which is sufficient for the two reported, but a run
  would confirm the four registered pairs still validate.
- ~40 external citations in the paper and 15 in the guide remain unverified
  beyond the two numeric claims pass D checked.

## Quick Start

```bash
cd /Users/djbclark/src/tendcf
git log --oneline -3            # expect 37a37c4 at HEAD
git status -s                   # expect the 7 untracked review docs + this handoff

# Read in this order — synthesis first, sources only as needed:
$PAGER docs/paper/reviews/2026-08-15_opus-5-xhigh_SYNTHESIS.md   # spine, split, ordered list
$PAGER docs/paper/reviews/2026-08-15_opus-5-max_redteam-trust-consent.md  # §1 and §10 only, unless acting on a specific TC

# Commit the review corpus (item 2 above):
git add docs/paper/reviews/ docs/handoffs/
git commit -m "docs: six-reviewer audit of the vetted guide, plus synthesis"

# Quota before launching more reviewers:
cswap list                      # NOT aiuse --json alerts; see What We Tried #2

# The review panes are still live and idle:
herdr agent list
herdr pane zoom w1H:pE --on     # redteam pane is small; zoom to read, then --off
```

**To re-run any pass**, the exact model/effort invocations were:

```bash
herdr agent start <name> --kind claude --pane <id> -- --model claude-opus-5 --effort max    # C
herdr agent start <name> --kind claude --pane <id> -- --model claude-opus-5 --effort xhigh  # B, F
herdr agent start <name> --kind claude --pane <id> -- --model claude-opus-5 --effort high   # E
herdr agent start <name> --kind claude --pane <id> -- --model claude-sonnet-5 --effort medium # D
```

Sleep ~2s between `pane split` and `agent start`. Send prompts with
`--wait --timeout 15000`; a `timeout` error is expected — confirm with
`herdr agent get <name>` that status is `working`. Single-quote or heredoc
prompt bodies: backticks in a double-quoted `herdr agent prompt "..."` are
expanded by the orchestrator's own shell before Herdr sees them.
