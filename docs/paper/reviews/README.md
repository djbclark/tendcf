# AI reviews in this directory

Two rounds, of two different documents. They are **not** interchangeable —
read the round header before citing anything from either.

- **2026-08-15** — six-reviewer fan-out on the *vetted guide*
  ([`../tendcf-architecture-guide.md`](../tendcf-architecture-guide.md)), the
  document that wins on conflict. **Current.** See below.
- **2026-08-13** — three pre-reviews of an earlier draft of the *paper*.
  **Archival.** See further below.

---

# Six-reviewer fan-out on the vetted guide (2026-08-15)

**Current.** Reviews of `../tendcf-architecture-guide.md` as of commit
`37a37c4`. Findings are open unless a later commit says otherwise.

Six independent passes, each in its own session so no reviewer saw another's
findings, then a synthesis. Model and effort were chosen per task rather than
uniformly; the prompt for each is saved alongside as `prompt_<pass>.txt`.

| File | Model / effort | Pass |
| --- | --- | --- |
| `2026-08-15_opus-5_consistency-audit.md` | Opus 5 / medium | Guide vs implementer map vs `schema/` vs `bin/schema_lint.py` |
| `2026-08-15_opus-5_guide-paper-parity.md` | Opus 5 / medium | Guide vs the technical paper |
| `2026-08-15_opus-5-xhigh_skeptical-review.md` | Opus 5 / xhigh | Skeptical peer review, whole document |
| `2026-08-15_opus-5-max_redteam-trust-consent.md` | Opus 5 / **max** | Adversarial, §§7–9 and 14–15 |
| `2026-08-15_opus-5-high_premortem.md` | Opus 5 / high | Pre-mortem |
| `2026-08-15_sonnet-5_exposition-structure.md` | Sonnet 5 / medium | Structure, prose, citation checks |
| `2026-08-15_opus-5-xhigh_SYNTHESIS.md` | Opus 5 / xhigh | **Start here.** Merges and ranks all six. |

The two audits were run in the orchestrating session rather than a clean one;
both flag that deviation in their own residual-risks section. The other four
ran in dedicated panes, cold.

## Headline results

**44 design changes, 47 document changes.** The synthesis names five root
causes; the strongest, found four separate ways by four reviewers who could
not see each other, is that **the document's risk apparatus is inversely
correlated with its risk** — fifteen conceded weaknesses across §10, §17, and
§19, none of them touching signing, keys, root rotation, consent, refusal,
peer authorization, or release transport, which is exactly where the red-team
then found 51 findings including 7 Critical.

The red-team also dispositions all nine findings from the earlier
`../../architecture/deprecated/redteam-trust-layer-openai-v1.md`: **zero are
cleanly resolved.** Two are moot by removed surface, which it calls the
design's best security work.

**One result belongs to no single reviewer.** Synthesis finding **E1**: the
skeptical review (reasoning from security) and the pre-mortem (reasoning from
build cost) independently arrived at the same alternative architecture — drop
the capability vocabulary, render a complete goal file per host, make the
ChangePlan mechanically the diff. It is structurally immune to several
Critical findings rather than merely mitigating them. Neither source report
makes the argument, because neither had the other's list. Its CFEngine
feasibility is assessed separately in
[`../../architecture/cfengine-feasibility-of-diff-plan-2026-08-15.md`](../../architecture/cfengine-feasibility-of-diff-plan-2026-08-15.md).

## Verified during this round, so nobody re-derives it

- Guide §18 and map §13 build orders agree on all eleven rows.
- Interlock `blocks`/`report` really are `const` + `required` in the schema —
  stronger than the guide claims.
- `examples/broken/` holds exactly 12 cases; `EXPECTED_BROKEN = 12`.
- Both Bcfg2 numeric claims (the `0 / 2308` first-run figures and the FTE
  figures) confirmed exact against primary sources.
- The `§0 rule 6` references in `schema/common.schema.json` and
  `bin/schema_lint.py` are **correct** against `architecture-DEFINITIVE-v3.md`
  §0. Do not "fix" them — three neighbouring references in the same file are
  genuinely stale, which makes this one look wrong by association.

---

# AI pre-reviews of the architecture paper (2026-08-13)

> **Archival.** Reviews of an earlier draft of the paper. Not current design. On conflict,
> [`../tendcf-architecture-guide.md`](../tendcf-architecture-guide.md)
> wins. Do not rewrite these files to bring them up to date.

Three machine reviews of that earlier draft, run before sending it to a
human reviewer. Two prompts (operator-supplied, ICLR/OpenReviewer style
and PaperAudit-Bench style) against two model families.

| File | Model | Prompt |
| --- | --- | --- |
| `2026-08-13_gemini-3.1-pro_iclr-review.md` | Gemini 3.1 Pro | ICLR |
| `2026-08-13_gemini-3.1-pro_flaw-audit.md` | Gemini 3.1 Pro | PaperAudit |
| `2026-08-13_gpt-oss-120b_flaw-audit.md` | GPT-OSS 120B (medium) | PaperAudit |

**A fourth run was intended and could not be made.** Codex (GPT-5.x) was the
first-choice second vendor; its account hit a usage limit with a reset date of
2026-08-20, and buying credits requires operator approval that was not sought.
GPT-OSS 120B was substituted as the nearest available non-Google, non-Anthropic
lineage. The GPT-OSS run also came back partly malformed — a duplicated header
block and a row truncated mid-sentence — so it is the weakest of the three as
an artifact, independent of content.

Reviews were run against the paper with its References section stripped, per
the execution guidance the prompts came with. Both were run through the same
CLI; temperature was not controllable from that interface, so the "set
temperature to 0" tip was not applied.

## What survived triage

Findings judged real and not already self-declared by the paper:

1. **The §4.1 non sequitur.** The mis-ordered Android chain is offered as
   confirming evidence for a claim about *AI* authorship, but the paper itself
   says humans wrote it and humans missed it. Human fallibility at
   global-knowledge constraints is evidence for a broader and weaker claim
   than the one §3 needs. (Gemini audit #4.)
2. **Local-first record vs. the agent that needs a fleet view.** §3 optimizes
   for agents with bounded context; §2.4/§5.3 then decentralize the record so
   that no agent can get a fleet-wide answer. Verifying a security rollout is
   precisely a global-knowledge question. §8.5 raises local-first from the
   "no consumer" angle and misses this one. (Gemini ICLR Q3.)
3. **Capability-token discovery.** §5.1's second self-criticism says
   `provides`/`requires` may only relocate global knowledge into a shared
   vocabulary. The reviewer sharpens it into a question the paper does not
   answer: how does an agent discover the right token without the global
   context it is supposed not to need? (Gemini ICLR Q2.)
4. **Register inconsistency.** §3 states the design rule as a law; §8.2 admits
   it may be a hypothesis. Both registers are in the paper. (GPT-OSS #4.)

Findings that were accurate but already stated by the paper: the absence of
any deployment or numbers (§7 says so), and the cold-path problem under the
§5.4 negative result (§5.4 is titled "A negative result we have not earned").
Both reviewers independently led with these, which is weak evidence the
honesty is being read rather than skimmed.

One finding was simply wrong: GPT-OSS #5 claims the borrowed Bcfg2 ideas are
not enumerated. They are, in §6.1–§6.5, one per subsection.
