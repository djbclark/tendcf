# Further AI-authorship optimization: a literature-grounded review (2026-08-13)

> **Proposal doc, not a decision.** Per `architecture-DEFINITIVE-v2.md`'s own
> header: this is *not* an edit to that file. It is the "new review doc"
> route that header specifies. Nothing here is adopted until the operator
> says so — see `djbclark/fleetopia#1`.

## Why this doc exists

R13 (§2, §0 rule 6) already made AI authorship a first-order design
constraint and derived "prefer local knowledge over global" and "prefer
machine-checkable over conventional" from it — argued in `architecture-
DEFINITIVE-v2.md` itself, and independently corroborated after the fact (see
`fleetopia-architecture-paper.md` §3.1, added this session: Tratt's
concurrent blog post, the region-logic lineage, and empirical LLM-IaC
literature). The operator asked, separately, whether reading more of that
literature surfaces further concrete optimizations — not just grounding for
claims already made. This doc is that pass: the full architecture document
(all 16 sections) and the paper, re-read against a wider literature sweep
than the one that produced the paper's §3.1/§9 edit.

**Headline finding: R13 is already unusually well-developed.** Most of what
a literature review would normally recommend (local over global,
machine-checkable over conventional, self-check loops, edge-provenance
tracking, budget-aware model routing, freehand-generation guardrails scoped
by where verification is thin) is already decided and dated 2026-08-13.
The items below are what's left after that — either genuinely new
mechanisms, or existing decisions that turn out to have stronger empirical
grounding than what motivated them originally.

## Already validated by this literature pass (no action — noted for the record)

- **Canonical example co-located with schema.** `nix2cf/examples/*.yml`
  sits directly next to `nix2cf/schema/*.schema.json`, one fixture per
  schema. A study on documentation retrieval for code generation found
  removing worked examples from documentation drops generation accuracy
  from 0.66–0.82 to 0.22–0.39 — the single largest effect size found in this
  entire search. `nix2cf`'s pairing already does the thing the literature
  says matters most. (Only follow-on below: make the pairing itself
  machine-checked, item 3.)
- **§7.5's IaC-generation caution** (arXiv 2404.00227: generation is
  well-studied, correctness verification is thin) is corroborated and
  sharpened by a more recent error taxonomy — see item 6 below for the
  sharpening, not a correction.
- **The two-layer ChangePlan split** (§7.3: verifiable layer authorizes,
  semantic layer only briefs) already anticipates the grounding/
  hallucination concern in item 7 below; item 7 proposes a generation
  *discipline* for the layer that already exists, not a new layer.

## New items

### 1. JSON over YAML for the Site Model's actual current authoring path

§4.3 states the Site Model's "canonical, at-rest representation" is JSON,
with Nix-module authoring as the preferred frontend and "plain YAML/JSON...
kept as a fallback." **In practice, today, YAML is not the fallback — it's
the only path**: `nix2cf/examples/services.yml`, `roles.yml`, and
`launchd-writers.yml` are all YAML, because D12's Nix-rendering pipeline
doesn't exist yet (that's Step 3+). Any agent drafting a Site Model instance
right now is writing YAML by hand.

A controlled study on structured-output formats (arXiv 2408.02442) found
JSON reaches 100% parse validity against YAML's 91.7%, and YAML shows
roughly a 14% drop in generation accuracy despite using ~30% fewer tokens.
The YAML failures cluster exactly where CFEngine/Ansible-adjacent config
tends to bite: incorrect alias/anchor use, inconsistent indentation, and
unescaped colons inside long strings — not coincidentally, close cousins of
the "Structural Deficit" category in item 6's taxonomy.

**Proposal:** either (a) make JSON the primary fallback-authoring format
ahead of Nix (YAML demoted to "also accepted, canonicalized on write"), or
(b) if YAML stays primary for human ergonomics, add a cheap canonicalizing
pre-commit step — parse, re-serialize, diff against the original — that
catches anchor/indentation/colon-ambiguity drift before `schema_lint.py`
ever sees it. Either is small; (b) is smaller and doesn't touch the
authoring experience.

### 2. Registry lookups as a tool call, not a file to read

R13's local-knowledge rule shrinks what an agent must read, but a registry
check ("is port 8080 free," "does this role exist") still means opening
`ports.yml`/`roles.yml` in full today. Two independent findings point the
same direction: a comparison of context-stuffing against retrieval-as-a-tool
found context stuffing costs ~2.7x the tokens, ~2x the latency, and ~2.7x
the cost for the same answer quality; and a paper on documentation
retrieval for planning-language generation found retrieving just the
relevant fragment (vs. dumping the whole spec) improved generation
directly, not just cost.

**Proposal:** a `nix2cf registry check <domain> <field> <value>` CLI (or
equivalent) that answers a single lookup without the agent reading the
whole registry file — same shape and rationale as the already-decided
`buildfile`-style "what does device X receive" self-check CLI (§4.4), just
aimed at authoring-time lookups instead of render-time verification. This
is one of the few places a single mechanism serves **both** R13 (accuracy)
and R12 (the $60/month token budget) at once — worth flagging because
those two objectives are usually in tension elsewhere in the document
(§14's premium-model gating exists precisely because they aren't always
free to satisfy together).

### 3. Machine-enforce the example/schema pairing that already exists

Item "already validated" above notes `examples/` and `schema/` are already
paired by convention. R13's second rule is explicit that a convention an
agent must remember is one it will eventually break silently. **Proposal:**
extend `bin/schema_lint.py` to fail if any `schema/*.schema.json` lacks a
matching `examples/*.yml` (or vice versa) — turning a good habit into a
checked invariant, at near-zero cost since the lint tooling and the pairing
both already exist.

### 4. `AGENTS.md` at repo root, once there's code to point at

`AGENTS.md` was formalized as an open cross-tool spec in 2025 (OpenAI,
Google, Cursor, Factory) and donated to the Linux Foundation's Agentic AI
Foundation in December 2025; by early 2026 it's read natively by Claude
Code, Codex CLI, Cursor, Aider, Devin, Copilot, Gemini CLI, Windsurf, and
Amazon Q, with a 2026 study across 138 repos finding developer-written
`AGENTS.md` files raise agent task success ~4% and cut agent-introduced
bugs 35–55%. `architecture-DEFINITIVE-v2.md` §0 already *is* this content —
"read this first," six numbered orientation points, explicit protection
notice — but it lives at a path no tool discovers automatically; an agent
has to already know to look for it.

**Proposal:** once Step 0 lands real code (not yet — both `fleetopia` and
`nix2cf` are docs/schema-only today), add a thin root `AGENTS.md` per repo
that points to §0 as the authoritative orientation rather than duplicating
it — a pointer, so it can't drift out of sync with the source of truth the
way a second copy would. Low priority; there's nothing to orient into yet.

### 5. Turn the DEFINITIVE doc's own protection notice into a machine check

This one is self-referential and worth calling out plainly: the doc's own
header — "AI agents: DO NOT MODIFY without explicit, specific human
approval" — is prose. R13's second rule names exactly this pattern as the
one to avoid ("a convention an agent must remember is a convention it will
eventually break silently"), and §8.1 already applies the fix to a
different surface (the 2026-08-06 double-merge incident → an automated
`git log`/`git diff` range gate, "not prose"). The header hasn't had the
same treatment applied to itself yet.

**Proposal:** a pre-commit/CI check that fails any diff touching
`architecture-DEFINITIVE-v2.md` unless the commit carries an explicit
marker (e.g. a `Approved-change:` trailer) — mechanically the same pattern
§8.1 already uses, applied to this file. Cheap, and closes the one place in
the document where its own stated principle isn't yet applied to itself.

### 6. Weight guardrail investment by the actual empirical error distribution

The IaC error taxonomy cited in the paper's new §3.1 (Nekrasov et al.,
arXiv:2512.14792) breaks real LLM-generated infrastructure-as-code errors
into four categories: **Factual Incorrectness** (invalid/nonexistent/
deprecated/incompatible elements) at 65% of technical errors,
**Incompleteness** at 26.5%, **Contextual Reasoning Failure**
(cross-resource/global-dependency errors — the category §4.5.1(b)'s
inference stage targets) at 7%, and **Structural Deficit** (syntax,
nesting) at just 1.5%.

Schema validation — the design's main current automated guardrail — is
aimed squarely at the smallest category. Two things already in the design
turn out to be better-aimed than their original justification suggests,
which is worth recording even though it changes nothing:

- The registries' eval-time asserts (ports/paths, §4.1) are exactly a
  Factual-Incorrectness guardrail ("does this value actually exist"), just
  not framed as one. Worth extending the same treatment to every
  enum-like/reference field across `services.yml`/`roles.yml`/
  `launchd-writers.yml`, not only ports/paths — that's where 65% of the
  empirical error mass sits.
- D16(d)'s default-on comprehensiveness / extra-entry detection (§4.5.1(d))
  was justified on multi-writer-skew-detection grounds, but it is also
  structurally the right answer to Incompleteness (26.5%, the
  second-largest category) — an agent's omission and a second writer's
  silent drift produce the same observable (an undescribed entry), and the
  same mechanism that catches one catches the other. No design change; this
  is reinforcing evidence for a decision already made, recorded so the next
  reader doesn't have to re-derive it.

**Proposal:** when Step 0's registries are extended (services/roles/
launchd-writers), prioritize Factual-Incorrectness-shaped checks
(existence/currency of referenced values) over additional structural
schema constraints — the marginal schema tightening is defending the
smallest category.

### 7. Generation discipline for the semantic layer (§7.3/§9)

The semantic layer ("this bumps openssl across a CVE and restarts the
public proxy") is advisory-only by design and never authorizes — but a
hallucinated claim there can still mislead the human or their advisor AI,
which is the actual sovereignty guarantee §9 is trying to protect, even
though it can't cause an unauthorized action directly. This is exactly the
shape of problem the citation-grounding literature addresses: forcing a
model to cite the specific source it's summarizing measurably reduces
unsupported claims, versus free generation from the same underlying facts.

**Proposal:** generate the semantic layer primarily by template-filling
from the verifiable IR's typed fields (`capability`, `resources`, `target`)
wherever a template covers the case, reserving free LLM generation for
genuinely novel/compound changes — and where free generation is used,
require it to quote or reference the specific IR fields it describes
inline, so a human or their advisor AI can mechanically check the prose
against the ground truth it claims to summarize, the same way the paper's
own worked examples (§2.6) are labeled against their real source. This is a
generation-discipline addition to a layer that already exists, not a new
mechanism.

### 8. Grammar-constrained decoding for the CFEngine escape hatch

§7.5 already flags freehand `.cf` text (the `commands` escape hatch, novel
promise types MPF/ncf don't cover) as the design's worst-covered surface —
"no schema to check against... exactly the category the empirical IaC-bug
literature identifies as where idempotence bugs concentrate." Grammar-
constrained decoding has matured since that section was written: current
implementations (e.g. arXiv:2502.05111) make token-level grammar
enforcement efficient enough for production use, not just a research
curiosity. A formal CFEngine promise-body grammar, written once, could
constrain *generation itself* at exactly this surface — stronger than
post-hoc lint, because invalid promise syntax becomes unrepresentable
rather than merely detectable.

**Proposal:** not urgent (§7.5's escape hatch isn't exercised until later
build-order steps), but worth a design note for whoever implements that
guardrail: check whether a CFEngine promise-body grammar exists or is
cheap to write before defaulting to a lint-only guardrail for this surface.

### 9. Name the "front-or-back, never buried in the middle" convention explicitly

`architecture-DEFINITIVE-v2.md` already does this at the document level —
§0 is literally titled "read this first," warnings sit at the very top —
but it reads as good instinct, not a stated rule. The empirical grounding
is direct: Liu et al. (TACL 2023, cited in the paper's new §3.1) show LLM
accuracy degrades sharply when relevant information sits mid-context rather
than at the start or end, even for long-context models.

**Proposal:** name it as a house convention (a short addition to R13 or a
new style note) so it's applied deliberately to future agent-facing
artifacts, not just this one document by accident of good habit — in
particular, rendered outputs (`def.json`/`host_specific.json`, the
ChangePlan) should put the highest-stakes fields (capability boundaries,
expiry, rollback) at a fixed, predictable position rather than wherever the
renderer happens to emit them.

### 10. `bcfg3/bcfg3` — a maintained fork, upgrades Bcfg2 from papers-only to a reference codebase

Operator note (this session): [`bcfg3/bcfg3`](https://github.com/bcfg3/bcfg3)
is an active fork of the original `Bcfg2/bcfg2` (Argonne National Lab),
maintained through Python 3.12/3.13 (removed-stdlib-module fixes, SSL API
changes), a Django 4 port of the reporting web interface, and current Debian
packaging — i.e. it is what actually runs Bcfg2 today, where upstream may
not. Checked: it is a real fork (2 forks, 3 open issues, commits into
2026-05), not an abandoned rename.

This matters because `architecture-DEFINITIVE-v2.md`'s References/§16
currently treat Bcfg2 as **papers only** — [1]–[4] are cited as "archival
reasoning," and every Bcfg2-derived decision (the `buildfile` CLI in §4.4,
Actions/interlocks semantics in §4.5.1(c), extra-entry/comprehensiveness in
§4.5.1(d), revision stamping in §4.7.1) is re-derived from the papers'
prose, not read from a working implementation. D17 already draws exactly
this distinction for Rudder/ncf — "reuse the code, not the project" — vendor
the hardened generic-method bundles as a reference corpus rather than
re-deriving them from scratch. `bcfg3` makes the same move available for
Bcfg2 itself: a runnable reference for `bcfg2-info buildfile`'s actual
implementation, the real Augments (`def.json`/`host_specific.json`) reader/
writer code, and the reporting DB schema behind `Total managed entries: 0 /
Unmanaged entries: 2308` — all currently reasoned about from paper prose in
this design, all available as working code to check that reasoning against
before `nix2cf` builds its own version at Step 3–4.

**Proposal:** when Step 3 (`nix2cf` compiler stages) or Step 4 (Linux
reference path) actually implement the `buildfile`-equivalent CLI, the
Augments render/read path, or D18's SQLite reporting schema, check
`bcfg3/bcfg3`'s implementation first — same "reference corpus, not a
dependency" posture D17 already established for Rudder, no new licensing
question (Bcfg2 is 2-clause BSD, strictly more permissive than Rudder's
GPLv3/plugin-exception situation D17 already worked through).

## Sources (additional to the paper's §3.1 references)

- Tang, X. et al. *Let Me Speak Freely? A Study on the Impact of Format
  Restrictions on Performance of Large Language Models.* arXiv:2408.02442,
  2024. (JSON vs. YAML parse validity and generation accuracy.)
- *Documentation Retrieval Improves Planning Language Generation.*
  arXiv:2509.19931, 2025. (Worked-example removal drops accuracy from
  0.66–0.82 to 0.22–0.39; retrieval-as-tool beats context-stuffing for
  planning-language generation specifically.)
- *RAG vs. Context Stuffing* (industry writeup summarizing multiple 2025/26
  benchmarks) and related agentic-RAG-vs-context-window comparisons:
  ~2.7x token/cost and ~2x latency overhead for context stuffing at equal
  answer quality.
- AGENTS.md specification and adoption data — Linux Foundation Agentic AI
  Foundation donation (Dec 2025); 2026 138-repo study on task-success and
  bug-rate effects.
- Citation-grounding literature (e.g. arXiv:2606.00898 and related 2026
  work on citation-grounded generation) — forcing citation to source
  reduces unsupported claims relative to free generation from the same
  facts.
- Park, K., Zhou, T., D'Antoni, L. *Flexible and Efficient
  Grammar-Constrained Decoding.* arXiv:2502.05111, 2025. (Already in the
  paper's §3.1 references as [14]; reused here for item 8's specific
  application.)
- Liu, N. F. et al. *Lost in the Middle: How Language Models Use Long
  Contexts.* TACL, 2023. arXiv:2307.03172. (Already in the paper's §3.1
  references as [11]; reused here for item 9.)
- Nekrasov, R. et al. *IaC Generation with LLMs: An Error Taxonomy and A
  Study on Configuration Knowledge Injection.* arXiv:2512.14792, 2025.
  (Already in the paper's §3.1 references as [13]; reused here for item 6's
  percentage breakdown.)
