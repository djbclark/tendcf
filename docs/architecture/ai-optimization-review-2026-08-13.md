# Further AI-authorship optimization: a literature-grounded review (2026-08-13)

> **Proposal doc, not a decision.** Per `architecture-DEFINITIVE-v2.md`'s own
> header: this is *not* an edit to that file. It is the "new review doc"
> route that header specifies. Nothing here is adopted until the operator
> says so — see `djbclark/tendcf#1`.
>
> **Correction, 2026-08-13 (same day, before adoption):** items 1, 3, and 4
> originally cited specific numbers that did not survive checking against
> the primary source directly (rather than search-summary paraphrase). Item
> 1's "100% vs 91.7%, 14% drop" and item 3's "0.66–0.82 to 0.22–0.39" are
> **withdrawn** — not supported by the papers they were attributed to. Item
> 4's claimed benefit is **reversed** — the actual dedicated study found no
> general benefit and a cost increase. Item 2's "2.7x" figure is retained
> but downgraded from academic-weight to its real source (an industry blog
> post). All four are corrected in place below; nothing citing these numbers
> should be copied elsewhere until reading the corrected version.

## Why this doc exists

R13 (§2, §0 rule 6) already made AI authorship a first-order design
constraint and derived "prefer local knowledge over global" and "prefer
machine-checkable over conventional" from it — argued in `architecture-
DEFINITIVE-v2.md` itself, and independently corroborated after the fact (see
`tendcf-architecture-paper.md` §3.1, added this session: Tratt's
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
  schema. Wang & Zhang (arXiv:2509.19931) found, for planning-language
  generation, that "examples consistently outperform descriptions," and
  that documentation bundling both dramatically outperforms either alone
  (for one model tested, correctness went from 0% with only descriptions or
  only examples to near-100% with the full documentation). That is weaker
  than the specific ablation number this doc originally claimed
  (corrected above) but still supports the same conclusion: `nix2cf`'s
  example/schema pairing is doing real work, not just tidiness. (Only
  follow-on below: make the pairing itself machine-checked, item 3.)
- **§7.5's IaC-generation caution** (arXiv 2404.00227: generation is
  well-studied, correctness verification is thin) is corroborated and
  sharpened by a more recent error taxonomy — see item 6 below for the
  sharpening, not a correction.
- **The two-layer ChangePlan split** (§7.3: verifiable layer authorizes,
  semantic layer only briefs) already anticipates the grounding/
  hallucination concern in item 7 below; item 7 proposes a generation
  *discipline* for the layer that already exists, not a new layer.

## New items

### 1. A canonicalizing check for the Site Model's actual current authoring path (not a JSON-over-YAML claim)

§4.3 states the Site Model's "canonical, at-rest representation" is JSON,
with Nix-module authoring as the preferred frontend and "plain YAML/JSON...
kept as a fallback." **In practice, today, YAML is not the fallback — it's
the only path**: `nix2cf/examples/services.yml`, `roles.yml`, and
`launchd-writers.yml` are all YAML, because D12's Nix-rendering pipeline
doesn't exist yet (that's Step 3+). Any agent drafting a Site Model instance
right now is writing YAML by hand.

**Correction:** this item originally claimed a controlled study
(arXiv:2408.02442) found JSON reliably beats YAML for LLM generation
(100% vs. 91.7% parse validity, ~14% accuracy gap). Checked directly
against the paper: that is not what it shows. Format performance there
varies by model and task with no consistent winner — in one case (Claude-3-
Haiku on GSM8K) YAML actually had *fewer* parsing errors than JSON. The
LLM-specific reliability claim is **withdrawn**.

What still stands, independent of any LLM-specific study: YAML's own spec
has well-documented structural footguns regardless of who or what is
authoring it — implicit type coercion (unquoted `no`/`yes`/`on`/`off`
parsing as booleans, the "Norway problem"), indentation sensitivity, and
alias/anchor ambiguity. These are exactly the shape of the (verified, item
6) "Structural Deficit" category — small in aggregate (1.5%) but real, and
JSON has strictly less syntax available to get wrong.

**Proposal, softened:** don't switch the authoring format on the strength
of an LLM-specific study — the evidence doesn't support that. Do add a
cheap canonicalizing pre-commit step (parse, re-serialize, diff against the
original) for the YAML fallback path, justified on the format's own known
ambiguity classes rather than a comparative LLM-reliability claim. Smaller
ask than the original proposal, still worth doing.

### 2. Registry lookups as a tool call, not a file to read

R13's local-knowledge rule shrinks what an agent must read, but a registry
check ("is port 8080 free," "does this role exist") still means opening
`ports.yml`/`roles.yml` in full today. Two things point the same direction,
at different evidence weights: a widely-cited industry benchmark (not a
peer-reviewed source — flagging that plainly, unlike this doc's original
framing) reports context stuffing costing roughly 2.7x the tokens and cost
of retrieval-as-a-tool for equivalent answer quality; and Wang & Zhang
(arXiv:2509.19931, academic, the same paper reused in item 3) found
retrieving just the relevant documentation fragment — not the whole spec —
improved planning-language generation directly, not merely cost. The
academic result supports the *direction* (targeted retrieval beats dumping
the whole file); the specific 2.7x multiplier is an industry figure, cited
as such.

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

### 4. `AGENTS.md`: adoption-convention value only — the performance claim is reversed

**Correction:** this item originally claimed a 2026 138-repo study found
`AGENTS.md` files raise task success ~4% and cut bugs 35–55%. That is
**wrong, and the actual finding is close to the opposite.** The dedicated
study (Gloaguen et al., ETH Zürich, "Evaluating AGENTS.md: Are
Repository-Level Context Files Helpful for Coding Agents?," arXiv:2602.11988,
Feb 2026) found context files — **both** LLM-generated and
developer-written — "do not generally improve task success rates," and
increase inference cost by over 20% on average. LLM-generated files
specifically *reduced* success versus no context file at all. The one
positive note: "instructions... are well followed," but "repository
overviews... are not helpful" even though every LLM-generated file in the
study included one.

`AGENTS.md` is still real as a cross-tool *discovery* convention — it was
formalized as an open spec in 2025 (OpenAI, Google, Cursor, Factory) and
donated to the Linux Foundation's Agentic AI Foundation in December 2025,
and is read natively by Claude Code, Codex CLI, Cursor, Aider, Devin,
Copilot, Gemini CLI, Windsurf, and Amazon Q. That's a real, verifiable fact
about tooling interop. It is not, on current evidence, a performance
intervention.

**Proposal, reversed:** do not adopt this on a performance rationale — there
isn't one. If a root `AGENTS.md` is added at all, the only defensible
reason is discoverability (a stranger's tool finds it without being told
where to look), and the study's actual finding argues for the opposite of
what was originally proposed: **keep it minimal and hand-curated, not
LLM-generated** (the study's LLM-generated files were the ones that hurt),
skip generic repository-overview content entirely (found unhelpful even
though universally included), and don't budget effort against R12
expecting a performance return, because the best current evidence says
there isn't one.

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

- Tam, Z. R., Wu, C.-K., Tsai, Y.-L., Lin, C.-Y., Lee, H., Chen, Y.-N. *Let
  Me Speak Freely? A Study on the Impact of Format Restrictions on
  Performance of Large Language Models.* arXiv:2408.02442, 2024. **Item 1
  correction:** checked directly — this paper does *not* show a consistent
  JSON-over-YAML advantage; format performance varies by model/task with no
  overall winner. Cited here only for that corrective finding, not for the
  withdrawn 100%/91.7%/14% claim.
- Wang, R., Zhang, L. *Documentation Retrieval Improves Planning Language
  Generation.* arXiv:2509.19931, 2025. (Confirmed: "examples consistently
  outperform descriptions"; full documentation dramatically outperforms
  either alone. Does *not* support the withdrawn 0.66–0.82 → 0.22–0.39
  ablation number in item 3's original text — corrected.)
- *RAG vs. Context Stuffing*, MarkTechPost, Feb 2026 — an industry
  benchmark writeup, not a peer-reviewed source, reporting ~2.7x
  token/cost and ~2x latency overhead for context stuffing. Cited as
  industry-weight evidence only (item 2); the directional claim is also
  independently supported by Wang & Zhang above.
- Gloaguen, T., Mündler, N., Müller, M., Raychev, V., Vechev, M.
  *Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for
  Coding Agents?* ETH Zürich, arXiv:2602.11988, Feb 2026. **Item 4
  correction:** the actual finding — context files (LLM-generated *and*
  developer-written) do not generally improve task success and increase
  inference cost 20%+. Replaces a withdrawn, incorrectly-positive claim.
- Citation-grounding literature (e.g. arXiv:2606.00898 and related 2026
  work on citation-grounded generation) — forcing citation to source
  reduces unsupported claims relative to free generation from the same
  facts. Cited for the general mechanism (item 7); the specific paper is
  about legal citations, not configuration management — the generalization
  is mine, not the paper's claim.
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
