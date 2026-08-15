# Brief: design `schema/goal-file.schema.json`

**Status:** review brief, 2026-08-15. Sent to three models independently; each
answers cold, without seeing the others. Follows the convention of the other
`*-BRIEF.md` files in this directory.

## What you are being asked

`schema/goal-file.schema.json` **does not exist yet**. It is the next work item
after decision E1. Design it, and argue for your design.

This is not a request to write a large document. It is a request for a
**considered technical opinion** plus enough concrete schema to make the
opinion falsifiable.

## Read these first, in this order

1. `docs/architecture/e1-adjudication-xhigh-2026-08-15.md` — the binding
   decision. §5 closes seven sub-decisions the schema must satisfy; §7 is the
   residue register listing what is NOT solved; §8 sketches the schema family.
2. `docs/architecture/architecture-DEFINITIVE-v3.md` §9 — the normative
   architecture, already rewritten for Model B.
3. `docs/paper/tendcf-architecture-guide.md` §7 — the same thing in prose, for
   the reader's-eye view of what the person consents to.
4. `schema/common.schema.json`, `schema/roles.schema.json`,
   `schema/services.schema.json`, `schema/report-row.schema.json` — the house
   style you must match, and the existing `$defs` you should reuse rather than
   reinvent. Also `examples/` and `examples/broken/` for the fixture
   convention, and `bin/schema_lint.py` for what lint enforces.

## Context in one paragraph

tendcf compiles a site model into CFEngine data. Under Model B, each device
receives a **goal file**: a canonical JSON document describing that host's
complete intended state. The device computes a **diff** between the goal file
and its own stored, previously-approved baseline; a person approves that diff;
an on-device **validator** — a comparator, not an interpreter — checks that
what is about to be applied equals what was approved. The goal file is
therefore simultaneously the compiler's output, the consent object, and the
validator's input. Getting its schema right is load-bearing for all three.

## The hard parts — address these explicitly

1. **Canonicalization.** §5.2 requires RFC 8785, no defaults, no empty
   collections, refuse-never-normalize. What does that force on the schema
   itself? Where can a schema permit two spellings of one meaning, and how do
   you make that unrepresentable rather than merely discouraged?
2. **Entry identity.** Diffs are structural and entry-granular, addressed by
   `(domain, kind, id)`. What makes a stable `id`, and what happens when a
   rename is indistinguishable from a delete-plus-add? This determines whether
   a person sees "renamed" or a scary pair of unrelated changes.
3. **Coverage.** §5.7 says coverage travels in the goal file: the file must
   distinguish "comprehensive here" from "not yet migrated here", because
   silence otherwise means two different things. How is that expressed without
   inviting an escape hatch?
4. **Versioning.** §5.6: fail closed on unknown `schema_version` and unknown
   entry kinds; ignore-unknown is rejected. Two-phase ship. Note a real
   correction: the adjudication claims report rows already carry agent state —
   **they do not**; `schema/report-row.schema.json` has `release` and
   `converged_release` and no validator-version column, so per-host version
   tracking is a schema addition, not an existing field. Say what it should be.
5. **Privileged regions.** Trust policy, advisor keys, peer allowlist, policy
   tree digest, validator version, schema version. The validator holds this
   list, never the proposer. Does anything in the goal file's own structure
   make that easier or harder to get right?
6. **Fetched content.** Anything fetched binds by digest, not by name, and the
   digest is part of what was approved (DC-11, residue R12).
7. **The open question E1 did not settle:** is the goal file the same artifact
   as the CFEngine Augments JSON (`def.json` / `host_specific.json`), or a
   projection onto it? Take a position and justify it. This lands on whoever
   writes the schema, i.e. you.

## Constraints

- **CFEngine is the only mutation engine.** No new configuration-management
  system, re-use existing systems. A design needing a new engine is
  disqualified regardless of elegance.
- **One unfunded builder.** Cost is a first-class criterion, not a footnote.
- Nothing in §7's residue register may be presented as solved.

## Deliverable

- A concrete `goal-file.schema.json` sketch — real JSON Schema, not prose about
  one. Partial is fine if the omissions are named.
- Your position on each of the seven hard parts, with reasoning.
- What you would cut. The project's binding constraint is builder capacity, so
  an opinion about what NOT to build is as useful as the schema.
- Anything in the adjudication you think is wrong. It has one confirmed factual
  error already (item 4 above); it may have others. Disagreement that survives
  scrutiny is the most valuable thing you can return.

**Do not edit any file in the repo.** Return your answer as your response. A
separate pass will reconcile the three opinions.
