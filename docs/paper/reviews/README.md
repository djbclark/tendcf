# AI pre-reviews of the architecture paper (2026-08-13)

Three machine reviews of `../tendcf-architecture-paper.md` (reviewed under
its prior name, `fleetopia-architecture-paper.md`), run before
sending it to a human reviewer. Two prompts (operator-supplied, ICLR/
OpenReviewer style and PaperAudit-Bench style) against two model families.

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
