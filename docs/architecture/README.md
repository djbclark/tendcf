# Architecture

**Start here (current design):**
[`../paper/tendcf-architecture-guide.md`](../paper/tendcf-architecture-guide.md)

That guide is the vetted current-state description. Where any other
living document disagrees on the current design, **the guide wins**.

Implementer map (decisions, build order, protection):
[`architecture-DEFINITIVE-v3.md`](architecture-DEFINITIVE-v3.md).
It must agree with the guide.

Technical paper:
[`../paper/tendcf-architecture-paper.md`](../paper/tendcf-architecture-paper.md)

Contested vocabulary — words with two senses, or whose referent moved under
a decision: [`GLOSSARY.md`](GLOSSARY.md). It defines nothing; it points at
whichever document is authoritative for each term.

Site Model contract (JSON Schema, fixtures, lint):
[`../../schema/`](../../schema/), [`../../examples/`](../../examples/),
[`../../bin/schema_lint.py`](../../bin/schema_lint.py).

Older numbered versions and panel drafts live in
[`deprecated/`](deprecated/). Dated `*-2026-08-13.md` notes in this
directory are an evidence trail. Briefs (`*-BRIEF.md`) and
[`ideas-dump-claude.md`](ideas-dump-claude.md) are prompts or dumps that
produced archived drafts. None of those are current design; do not
rewrite them to “bring them up to date.” On conflict, the guide wins.
