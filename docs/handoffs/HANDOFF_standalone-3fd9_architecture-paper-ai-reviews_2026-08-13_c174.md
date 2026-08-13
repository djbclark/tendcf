---
schema_version: 1
handoff_id: c174
parent_handoff_ids: [405e]
lineage: deterministic
chain: [standalone-3fd9]
repo: fleetopia
workspace: N/A (plain repo checkout, not an ops-worktrees task workspace)
branch: master
head_sha: f9f8f876631c11dc37e40cf123f81f44d0b53ff9
created_at: 2026-08-13T13:35:04-0400
writer: claude-code
---

# Handoff — the architecture paper, and what three AI reviews found in it

## The Goal

Resume chain `standalone-3fd9` from `405e` and execute **its item 1**, which
was not Step 0's remainder: **write an academic paper about the fleetopia
architecture**, in the style of the four Bcfg2 papers in
`~/src/bcfg2/doc/papers/`, **not too long**, for review by **Narayan Desai** —
Bcfg2's author, co-author of three of those four papers, and a friend of the
operator who "would see holes in the plans even AI might miss."

`405e` had already established the framing, and it is the load-bearing part:
the audience is one specific expert, so **the paper's job is to expose the
design to a hole-finder, not to sell it.** A version that reads as advocacy
wastes the review.

Mid-session the operator added a second goal: **get comments from two
non-Claude AIs**, supplying two review prompts (ICLR/OpenReviewer style and
PaperAudit-Bench style) plus execution guidance.

## Where We Are

**Paper written, reviewed three times, everything pushed.** Working tree
clean, `master` in sync with `origin/master`.

| Commit | What |
| --- | --- |
| `c7aaefd` | The paper draft |
| `4242cb7` | Trim pass (~5850 words) |
| `f9f8f87` | Three AI reviews + prompts + triage README |

Also pushed `43b344e` — the previous session's handoff commit, which `405e`
had deliberately left local. Operator approved pushing explicitly this
session, so the "fleetopia declares no memory-is-data exception" posture is
now **operator-overridden for content but not automated**: this handoff is
again committed locally and NOT pushed, per the skill's default.

`~/src/nix2cf` untouched this session, clean at `f5f01e0`.

**Files created:**

```
docs/paper/fleetopia-architecture-paper.md     the paper (~5850 words)
docs/paper/reviews/README.md                   triage: what survived, what didn't
docs/paper/reviews/2026-08-13_gemini-3.1-pro_iclr-review.md
docs/paper/reviews/2026-08-13_gemini-3.1-pro_flaw-audit.md
docs/paper/reviews/2026-08-13_gpt-oss-120b_flaw-audit.md
docs/paper/reviews/prompt_iclr.txt             operator-supplied, verbatim
docs/paper/reviews/prompt_audit.txt            operator-supplied, verbatim
```

**Three open items, none blocking:**

1. The **bibliography is unverified** and the paper carries a visible warning
   block saying so. This is deliberate, not an oversight — see Key Decisions.
2. **Acknowledgements is a stub.**
3. **Four review findings are triaged but not folded in.** The operator was
   given a recommendation and had not answered when the session wound down.

## What We Tried

1. **Nearly picked the paper's format by assumption.** The obvious move was
   Markdown, and it is what the operator chose — but checking first was what
   made it a real question rather than a default. There is **no LaTeX source
   anywhere in `~/src/bcfg2/doc`** (the four sources are PDFs only), and this
   machine has **no pdflatex, xelatex, tectonic, pandoc, or typst** (`which`
   on all five, all absent). So "in the style of" could not be satisfied by
   copying a skeleton; the phrase had to mean rhetorical form — abstract,
   numbered sections, related work, honest limitations — which is the part
   that actually matters for a review. Operator chose "Markdown now, PDF
   later," so the PDF half is still unpaid work.

2. **Wrote the first draft at 6010 words and it was too long for the brief.**
   The operator said "not too long" and the source papers are short conference
   papers (CLUSTER '03 is ~2800 words; the LISA papers are longer). One trim
   pass took it to ~5850 by compressing §2 (the reviewer knows what a CM
   system looks like), the TUF detail, and the borrowed-ideas recitals —
   deliberately **not** touching §5 or §8, since the departures and the open
   questions are the paper's entire job. **It is still LISA-length, not
   CLUSTER-length, and the operator never ruled on whether that clears "not
   too long."** That question is still open.

3. **Codex was the intended second reviewer and could not run.** `codex exec`
   returned `You've hit your usage limit … try again at Aug 20th, 2026`.
   Buying credits requires operator approval (standing rule), which was not
   sought. **Do not retry Codex before 2026-08-20.**

4. **`agy` and `gemini` turned out to be the same CLI**, with identical help
   output and near-identical model rosters — so "use agy instead" would have
   bought no vendor diversity at all. What rescued it: both expose
   `gpt-oss-120b-medium` in their model list, which is an OpenAI open-weights
   lineage reachable without spending anything. That is how reviewer #2
   happened despite Codex being dead.

5. **The GPT-OSS run came back partly malformed** — a duplicated header block
   and a table row truncated mid-sentence (`§5.1 … failure-mode` then
   nothing). Content was also the weakest of the three: mostly restating what
   the paper already declares about itself, plus "run a controlled experiment"
   fixes that do not apply to a design paper with nothing deployed. One of its
   findings was **flatly wrong** — it claimed the borrowed Bcfg2 ideas are not
   enumerated, when they are, one per subsection in §6.1–§6.5.

6. **The `--temperature 0` execution tip could not be applied.** The Gemini
   CLI's print mode exposes `--effort` but no temperature control. Noted in
   the reviews README so nobody assumes it was done.

## Key Decisions

### The paper leads with the departure, not the design (this session)

§5.1 states the sharpest disagreement at full strength and then lists three
ways it fails, rather than defending it: **we build a dependency inference
stage; Bcfg2 deliberately built no dependency graph at all.** The three
self-criticisms are the substance, and the first is the one that most
undercuts the project:

- **The convergence fixpoint may already be the local-knowledge mechanism** —
  retry-until-stable requires an author to know *nothing* about ordering,
  which is more local than `provides`/`requires`, not less. If that is right,
  the design argued itself into building a graph to obtain a property the
  substrate already had.
- `provides`/`requires` may only **relocate** the global knowledge into a
  shared vocabulary two authors must agree on.
- Spurious edges are **silent by construction** — nothing fails, something
  just waits — and the claim that provenance turns that into a query is
  untested.

### The empirical position is stated in the abstract, not buried (this session)

The abstract's third paragraph says nothing is deployed, no device has been
provisioned from factory reset, there are no numbers of any kind, and §5.4's
negative result rests on a cold path never executed. §7 then leads with what
is *not* implemented before what is. Rejected: putting limitations last, the
conventional placement — a hole-finder who discovers it himself has already
stopped trusting the rest of the document.

### The bibliography is left unverified, and says so, rather than looking checked

References were written from working notes and memory, not from the source
PDFs' own reference pages. Rather than silently ship them, the References
section carries an explicit warning block. Least confident, in order: **[8]
µPuppet author list**, **[6] Promise Theory book year/authorship**, **[9]
local-first author list**. Sending a wrong author list to a co-author of three
of the four cited papers is a specific and avoidable embarrassment, and it is
worth a verification pass before the paper leaves the building.

### Vendor diversity was preserved by substituting a lineage, not a CLI

**Chosen:** GPT-OSS 120B via the Gemini CLI's roster. **Rejected:** (a)
buying Codex credits — standing rule requires asking, and the ask was not
worth making for a review; (b) `agy` — same CLI, same vendor, zero diversity;
(c) `opencode` with a paid model — same credit-spend problem, and its
`-free` tier was untested. Also **rejected: running only one reviewer** —
the operator asked for two, and one Google model reviewing alone would have
made prompt-vs-vendor effects unseparable.

### Both prompts were run against Gemini, only one against GPT-OSS

Deliberate, to keep prompt and vendor partially separable given that Codex's
absence had already cost one cell of the 2x2. Gemini got both prompts; GPT-OSS
got the flaw audit only.

## Evidence & Data

**Tests run: none.** No code was written this session. `schema_lint.py` in
`nix2cf` was not re-run; it was last green at `f5f01e0` (`OK (5 schemas)`).

**Word counts:** draft 6010 → 5855 → **5815** after the trim pass (`wc -w`).
CLUSTER '03 is ~2800 words for calibration; the LISA papers run longer.

**Review outcomes:**

| Model | Prompt | Verdict |
| --- | --- | --- |
| Gemini 3.1 Pro | ICLR | **Presentation 4/4, Contribution 3/4** |
| Gemini 3.1 Pro | PaperAudit | 4 findings |
| GPT-OSS 120B (medium) | PaperAudit | 6 findings, output truncated |

Gemini's contribution rationale, quoted because it is the fair summary of the
paper's current status: *"functions as a strong 'vision' paper or
architectural proposal rather than a completed systems research paper,"*
bottlenecked by the complete lack of implementation.

**The four findings that survived triage** (full text in
`docs/paper/reviews/README.md`, which is the artifact to read, not this
summary):

1. **§4.1 contains a non sequitur.** The mis-ordered Android chain
   (`stayturgid#288`) is offered as confirming evidence for a claim about *AI*
   authorship, but the paper says in the same breath that humans wrote it and
   humans missed it. That is evidence for "global-knowledge ordering is
   error-prone for everyone" — broader and weaker than what §3 needs. §8.2
   does **not** cover this: the problem is not thin evidence, it is evidence
   for a different proposition.
2. **Two halves of the design contradict each other.** §3 optimizes for agents
   with bounded context; §2.4/§5.3 then decentralize the record so no agent
   can obtain a fleet-wide answer. "Verify this security rollout landed
   everywhere" is precisely a global-knowledge question, and the architecture
   removed the place to ask it. §8.5 raises local-first from the no-consumer
   angle and misses this entirely. **This is the highest-value fix** — Desai
   will reach it, and it is far better as a stated §8 question than as a
   caught omission.
3. **Capability-token discovery is unanswered.** §5.1 admits the vocabulary
   problem; the reviewer sharpens it into the question the paper ducks — how
   does an agent discover the right token without the global context it is
   supposed not to need? A closed enumeration catches typos, not disagreement
   about names.
4. **Register inconsistency.** §3 states the rule as a law; §8.2 concedes it
   may be a hypothesis. Both registers are in the text.

**Findings that were accurate but already self-declared:** the total absence
of deployment data (§7 says so) and the cold-path hole (§5.4 is *titled* "A
negative result we have not earned"). Both reviewers led with these, which is
weak evidence the honesty is being read rather than skimmed.

## Operator Feedback

- **The paper brief itself** came from `405e` and was followed: expose rather
  than sell, lead with the Bcfg2 departures, state the empirical weakness
  first, credit borrowings precisely.
- **"go ahead and push"** — explicit, and applied to the paper commits. This
  overrides `405e`'s hold-local posture *for that content*; it did not
  establish a standing exception, so this handoff is committed locally per the
  skill default.
- **Two review prompts supplied verbatim**, with execution guidance (convert
  to Markdown, strip references, temperature 0, watch for prompt injection).
  The strip-references step was applied; temperature was not controllable.
- **Format decision:** "Markdown now, PDF later," chosen from three options
  after being told no TeX/pandoc/typst exists on the machine.
- **Standing, still in force:** never spend usage credits without asking
  (`feedback_never_use_credits_without_asking`) — this bound the Codex
  decision directly; auto-commit at natural checkpoints
  (`feedback_auto_commit_at_checkpoints`); `~/ops` is deploy-only, code work
  in `~/src/ops-worktrees` (`feedback_ops_worktrees_only`); Issues stay
  enabled on all repos.

## Where We're Going

1. **START HERE — decide the length question, then fold in the review
   findings.** These are coupled: findings 2 and 3 *add* text to §8, so if the
   paper also has to shrink, the cuts have to come from §2 and §6. The
   operator was given a recommendation and never answered it, so **ask before
   editing**: keep ~5800 (LISA length), or cut toward ~3000 (CLUSTER length)?
   Then apply, in this order:
   - **Fix the §4.1 non sequitur** (finding 1). Either drop "confirming
     evidence" and reframe `stayturgid#288` as motivation, or state plainly
     that it evidences the broader claim and that the AI-specific claim rests
     on the argument in §3 alone. The second is more honest and cheaper.
   - **Add finding 2 to §8 as a new open question** — the agent that needs a
     fleet-wide view versus the record that has no center. This is the one
     worth not being caught on.
   - **Add finding 3** to §8 or fold it into §5.1's second self-criticism,
     which already gestures at it.
   - **Reconcile the register** (finding 4): §3 should say "rule we are
     adopting and testing," not state a law that §8.2 then retracts.
2. **Verify the bibliography against the source PDFs.** `ls
   ~/src/bcfg2/doc/papers/`, then read each paper's own References page.
   Correct entries [1]–[4] especially, then [6], [8], [9]. **Remove the
   warning block from the References section once done** — it is there to
   prevent the paper going out looking checked when it is not.
3. **Write the Acknowledgements section** — currently a parenthetical stub.
   Minimum: Narayan Desai for review, and the Bcfg2 authors, whose four papers
   are the source of §6 in its entirety.
4. **Optional PDF pass** (the deferred half of the operator's format choice).
   `brew install typst` or `tectonic` — neither is present. Sources are PDFs,
   so a two-column USENIX-ish template would have to be written, not copied.
   Do this only after the content settles; converting a moving draft twice is
   waste.
5. **Rest of §12 Step 0 — transcribe reality into instances.**
   `registry/services.yml`, `roles.yml`, `launchd-writers.yml` in
   `site-djbclark`, validated against `~/src/nix2cf/schema/`. **In an
   `~/src/ops-worktrees/` task workspace, never in `~/ops`.** Expect nearly
   every domain to land `comprehensive: false` /
   `opt_out_reason: not-yet-migrated`; that count is the progress metric.
6. **Wire the schemas into the existing gate.** Extend
   `site-djbclark/bin/registry_lint.py` (add a `jsonschema` dep) so the three
   new registry files are gated in CI and pre-commit the way `ports.yml` and
   `paths.yml` already are.
7. **Automate the §8.1 worktree provenance gate** — the other half of Step 0,
   still untouched across three sessions now.
8. **Then §12 Step 1 — macOS services adapter.** Dry-run first, enforce
   second. Explicitly **not** nix-darwin or substrate (Step 7, gated on
   §14.1).
9. **Unchanged carries:** distro choice open until Step 4; §14.1 does not gate
   Step 1; `stayturgid#288/#289/#290` stay waived and should not be re-raised
   unprompted; still no architectural position on image-based atomic updates
   (RAUC / SWUpdate+hawkBit / OSTree) — §5.5 has an extension point, not a
   position.

## Quick Start

```bash
# The paper, and the reviews of it (read the README first — it is the triage):
$EDITOR ~/src/fleetopia/docs/paper/reviews/README.md
$EDITOR ~/src/fleetopia/docs/paper/fleetopia-architecture-paper.md
wc -w ~/src/fleetopia/docs/paper/fleetopia-architecture-paper.md   # 5815

# Bibliography verification source material:
ls ~/src/bcfg2/doc/papers/
#   bcfg-cluster2003.pdf  desai_lisa05.pdf  desai_lisa06.pdf  19_bcfg2.pdf

# The architecture the paper describes (PROTECTED — do not edit without
# specific operator approval for a named change):
$EDITOR ~/src/fleetopia/docs/architecture/architecture-DEFINITIVE-v2.md
#   §4.1 / §4.5.1  Site Model contract + the four D16 sub-decisions
#   §12  build order, Steps 0-10
#   §15  decision register (D22 newest)
# Already-mined Bcfg2 notes — do NOT redo this reading:
$EDITOR ~/src/fleetopia/docs/architecture/bcfg2-papers-2026-08-13.md

# Re-running an AI review (Codex is quota-dead until 2026-08-20):
cd /tmp && awk '/^## References/{exit} {print}' \
  ~/src/fleetopia/docs/paper/fleetopia-architecture-paper.md > paper.md
cat ~/src/fleetopia/docs/paper/reviews/prompt_audit.txt paper.md > full.txt
gemini --model gpt-oss-120b-medium --print-timeout 10m -p "$(cat full.txt)"
# omit --model for Gemini 3.1 Pro (the default)

# State:
cd ~/src/fleetopia && git log --oneline -4   # f9f8f87 at HEAD, clean, pushed
cd ~/src/nix2cf && ./bin/schema_lint.py      # expect: OK (5 schemas), exit 0
```

Two gotchas worth not rediscovering: `session_log.py write` requires
`blockers` as a **list of strings**, not a string (it exits 1 otherwise); and
`agy` is the same CLI as `gemini`, so reaching for it to get a second vendor
gets you the same one.

Prior context in this chain, newest first:

- `docs/handoffs/HANDOFF_standalone-3fd9_step0-schemas-nix2cf-repo_2026-08-13_405e.md` (parent)
- `docs/handoffs/HANDOFF_standalone-3fd9_r13-d16-backprop-platform-reorder_2026-08-13_8671.md`
- `docs/handoffs/HANDOFF_standalone-3fd9_nix2cf-split-communal-orchestration_2026-08-13_601f.md`
- `docs/handoffs/HANDOFF_standalone-3fd9_cfengine-nix-architecture_2026-08-13_05f4.md`
