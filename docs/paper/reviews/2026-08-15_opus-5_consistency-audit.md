# Documentation Audit — `docs/paper/tendcf-architecture-guide.md`

Pass A of the guide review plan. Run 2026-08-15 with Claude Opus 5 (effort
medium), not the planned Sonnet 5 / high — run in an existing session at the
operator's request. See "Residual risks" for what that costs.

**Verdict:** CONCERNS

## Scope and audiences

Audited:

- `docs/paper/tendcf-architecture-guide.md` (964 lines) — the canonical target.
- `docs/architecture/architecture-DEFINITIVE-v3.md` (652 lines) — the guide
  declares this "must agree with this guide".
- `schema/*.schema.json` (5 files), `examples/*.yml` (4 fixtures),
  `examples/broken/` (12 cases), `bin/schema_lint.py`, `bin/check_protected_docs.py`.

Audiences considered: a new contributor orienting from the guide; an AI coding
agent authoring Site Model files under §9's writing rule; a reviewer checking
whether §18's "built today" list is true.

Excluded as archival by their own headers: `docs/architecture/*-BRIEF.md`,
`docs/architecture/deprecated/`, `docs/paper/reviews/2026-08-13_*`,
`docs/handoffs/`. Consulted only to trace the origin of stale cross-references.

Not audited: `docs/paper/tendcf-architecture-paper.md` (1491 lines) — see
"Residual risks".

## Trust summary

| Area | Status | Evidence |
|---|---|---|
| Structure | PASS | 19 sections, no broken internal links, no orphan claims. Guide §18 build order and v3 §13 build order agree step-by-step (0–10+), including the step-3 sequencing and the two-platform gate on inference. |
| Coverage | PASS | §18 separates built from not-built; §19 names nine weaknesses without hedging. |
| Factual accuracy | CONCERNS | One safety-mechanism claim in §3 is not true of the lint (F1). One token-kind enumeration in §15 is incomplete (F4). |
| Durability and SSOT | CONCERNS | `common.schema.json` carries three cross-references into the guide/map; one is wrong and one is stale v2 numbering (F2, F3). |
| Comments and examples | CONCERNS | §16.B presents altered text as a fixture excerpt (F5). Lint docstring miscounts its own layers (F6). |

## Document actions

| Surface | Action | Evidence |
|---|---|---|
| `docs/paper/tendcf-architecture-guide.md` | UPDATE | §3 pairing claim (F1), §15 token kinds (F4), §16.B excerpt fidelity (F5) |
| `schema/common.schema.json` | UPDATE | Stale/incorrect cross-references (F2, F3) |
| `bin/schema_lint.py` | UPDATE | Either enforce the §3 pairing rule or stop the guide claiming it (F1); docstring count (F6) |
| `docs/architecture/architecture-DEFINITIVE-v3.md` | KEEP | Build order, trust tiers, token discovery, and interlock semantics all agree with the guide |
| `schema/services.schema.json`, `roles`, `launchd-writers`, `report-row` | KEEP | Verified against their fixtures and against guide §§3, 11, 12, 15 |
| `examples/broken/` | KEEP | 12 cases present; `EXPECTED_BROKEN = 12` matches guide §18's "Twelve" |

## Findings

| Priority | Problem | Evidence and justification | Required resolution |
|---|---|---|---|
| **P1** | Guide §3 claims the lint enforces schema↔example pairing in both directions. It enforces neither for new files. | Guide:167 — "Every schema is paired with a concrete example file. The lint fails if a schema arrives without its example, or the other way around." But `bin/schema_lint.py:49` drives pairing from a hardcoded `EXAMPLES` dict of four names. `check_schemas_valid` globs `schema/*.schema.json` for *validity only*. A new schema not added to the dict is never checked for a fixture; a new example not in the dict is never validated. `schema/common.schema.json` already has no fixture and is already exempt, unmentioned. Affected audience: the next author of §18 Step 0's remaining schemas (`peer_actions`, trust-policy shape, generic unit-writers, lookup stub) — per §9, likely an AI agent, acting on the guide's assurance that omission is caught. Not acceptable as-is because §9's own rule ("prefer machine-checkable to conventional") is exactly what this violates: the pairing is a hand-maintained dict, i.e. a convention. | Either (a) derive `EXAMPLES` from the filesystem and fail on any unpaired `schema/*.schema.json` or `examples/*.yml`, with an explicit allowlist for shared-definition schemas like `common`; or (b) reword §3 to state the rule holds for the four registered pairs and that adding a schema means registering it. (a) is preferred — it is the machine-checkable option. See [JSON Schema `$defs` / structuring](https://json-schema.org/understanding-json-schema/structuring) for why a shared-definitions schema legitimately has no instance of its own. |
| **P1** | `schema/common.schema.json` cites the wrong guide section for release stamping. | `common.schema.json` `$defs.release_stamp`: "Every reporting row carries it (guide §8; D19)". Guide §8 is "The person's own AI"; release stamping is guide §6:298 ("Every report row carries the release that produced it"). The same file's header asserts "Current-design facts follow docs/paper/tendcf-architecture-guide.md", so the citation is explicitly to the guide and explicitly wrong. Affected audience: an implementer or agent following the reference to check the rule lands in the consent chapter and concludes the schema is describing a different mechanism. A stale pointer in the canonical schema is worse than none, because it directs to a plausible-but-wrong section. | Change to `guide §6`. Consider citing section *titles* rather than numbers in schema descriptions — the numbers have already drifted once. |
| **P2** | `schema/common.schema.json` cites `§12 Step 0` for the build order; that is DEFINITIVE-**v2** numbering. | `$defs.domain_coverage`, `opt_out_reason.not-yet-migrated`: "this count is the build order's progress metric (§12 Step 0)". Build order is §13 in `architecture-DEFINITIVE-v3.md:526` and §18 in the guide. §12 in v3 is "Platforms"; §12 in the guide is "Interlocks". `docs/architecture/deprecated/architecture-DEFINITIVE-v2.md` uses `§12 Step 0`/`§12 Step 4` throughout — confirming this survived the v2→v3 renumbering. | Change to `guide §18` (or `map §13`) and qualify which document. Note `§0 rule 6`, cited in the same file and in `bin/schema_lint.py:20`, is **correct** against v3 §0 — do not "fix" it; it is only ambiguous because the file header points at the guide, which has no §0. |
| **P2** | Guide §15 under-enumerates the closed token-kind set and points nowhere canonical. | Guide:619 lists "`service`, `port`, `path`, `secret`, `class`, `network`, …". The schema pattern (`common.schema.json` `$defs.capability_token`) admits eight: `service\|port\|path\|class\|package\|device\|network\|secret`. The two omitted behind the ellipsis — `package` and `device` — are ones a Site Model author plausibly reaches for. §15's stated purpose is that discovery of names is the mechanism, and the guide is the authoritative document; a reader cannot learn the actual set from it, and the ellipsis reads as "and a few obvious others" rather than "two specific ones you must look up". | List all eight, or replace the list with a pointer to `schema/common.schema.json#/$defs/capability_token` as the canonical enum. The pointer is the durable fix: the set is explicitly "additive" per the schema, so any inline copy will drift again. |
| **P3** | §16.B presents altered text as a fixture excerpt. | Guide:632 — "The inputs below are excerpts from `examples/services.yml`". The §16.B interlock `description` reads "The mesh VPN must be authenticated… whose VPN is unauthenticated"; `examples/services.yml` reads "Tailscale must be authenticated… whose Tailscale is unauthenticated". §16.A's excerpts are faithful subsets (fields dropped, none reworded), so the reader has no reason to expect §16.B to be paraphrased. Likely a de-branding edit (cf. commit 4deab3d, "drop last-system layout language from fixtures") applied to the guide but not the fixture, or vice versa. Material only because §16's opening paragraph is a careful provenance statement — it distinguishes schema-validated YAML from hand-authored output, and this weakens that distinction. | Make them identical in whichever direction is wanted, or change §16's provenance sentence to say the YAML is excerpted *and lightly edited for the reader*. |
| **P3** | `bin/schema_lint.py` docstring says "Three layers" and lists four. | `bin/schema_lint.py:8` — "Three layers, cheapest first:" followed by numbered items 1–4, with item 4 (negative fixtures) load-bearing enough that the docstring itself argues for it two lines later ("Layer 4 is why we believe layer 3"). | Change to "Four layers". |

## Verified claims (no finding)

Recorded so later passes do not re-derive them:

- Guide §18 "Twelve deliberately broken fixtures in `examples/broken/`" — 12
  directories present; `schema_lint.py:45` `EXPECTED_BROKEN = 12`; the lint
  fails on a count mismatch.
- Guide §18 lint capabilities ("reference resolution, launchd labels checked
  against declared writer prefixes, no prefix nested inside another") — all
  three present in `check_cross_file`, plus service-name uniqueness the guide
  does not claim.
- Guide §12 / §16.B "`blocks` and `report` are constants in the schema. An
  author cannot narrow the blast radius or silence the report." — `common.schema.json`
  `$defs.interlock` declares `"blocks": {"const": "enclosing-bundle"}` and
  `"report": {"const": true}`, both in `required`, with `additionalProperties: false`. True.
- Guide §11 opt-out reasons are a closed set of exactly two, and the schema
  additionally rejects a reason on a comprehensive domain — stronger than the
  guide claims, not weaker.
- Guide §16.A's derived edge — `litellm-proxy.requires[0]` is `service:caddy`
  in the fixture, matching the illustrative JSON's
  `"source": {"field": "requires[0]"}`.
- Guide §18 build order vs map §13 build order — agree on all eleven rows,
  including step 3's internal ordering and the two-platform gate on inference.
- Both illustrative outputs in §16 carry explicit non-provenance markers
  (`ILLUSTRATIVE — not compiler output`, `rendered, not authored`), and §16's
  opening states the render stage does not exist. The "nothing described here
  is deployed" preamble is consistent with §18 throughout; no present-tense
  capability claim contradicts it.

## Unverified claims and residual risks

- **`docs/paper/tendcf-architecture-paper.md` was not audited.** The guide
  claims parity with it ("Same architecture as the technical paper, in plainer
  language"). At 1491 lines it is the largest unchecked surface, and commit
  1bef966 ("docs: align the architecture paper with the vetted guide") means
  alignment was attempted but is unverified here. **This is the largest gap in
  pass A** and should be closed before pass F.
- **External sources not checked.** ~20 citations in §§2–17 and Further
  reading — CFEngine Augments availability "since version 3.7", the TUF spec
  §5 claim, Bcfg2's `Total managed entries: 0 / Unmanaged entries: 2308`
  transcription. Marked `UNVERIFIED`; these belong to pass B/D, not a
  consistency audit.
- **The lint was not executed.** `bin/schema_lint.py` needs `uv` plus network
  for its inline dependencies; findings F1 and F6 are from static reading of
  the source, which is sufficient for both (F1 is a control-flow fact, F6 is a
  string). A run would confirm the four registered pairs still validate.
- **Model/effort deviation.** Run on Opus 5 at effort medium in a large
  existing session rather than Sonnet 5 at high in a clean one. Cost: the
  session's prior context includes my own framing of this document, so the
  audit is less independent than planned. Consistency auditing is the pass
  least sensitive to that (findings are file-anchored and re-checkable), but
  passes B, C, and E should be run clean as specified.

## Checklist: 31/35 complete

**Incomplete:**

- §1 "Define which code, configuration, schemas, tests, and external contracts
  can verify documentation claims" — partial; external contracts (CFEngine,
  TUF, Bcfg2 papers) were scoped out. Impact: citation accuracy unverified.
  Next action: fold into pass B or D.
- §4 "Use official sources for external APIs, deprecations, security standards,
  platform limits" — not done, same reason and same next action.
- §4 "Execute examples… otherwise inspect parsing" — statically verified only;
  the lint was not run. Impact: none for the findings reported. Next action:
  `bin/schema_lint.py` from repo root with network access.
- §3 "Trace requirements and architecture statements across documents" —
  complete for guide↔map↔schema↔lint, incomplete for guide↔paper. Impact: the
  parity claim in the guide's opening paragraph is unverified. Next action:
  audit the paper against the guide before pass F.
