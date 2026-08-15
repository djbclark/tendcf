# Documentation Audit — guide ↔ paper parity

Pass A-2, closing the gap left by `2026-08-15_opus-5_consistency-audit.md`.
Run 2026-08-15, Claude Opus 5 (effort medium).

Question audited: the guide's opening claims it is the "Same architecture as
the technical paper, in plainer language," and commit `1bef966` says the paper
was aligned to the guide. Is that true, and does the paper make any
current-design claim the guide contradicts?

**Verdict:** CONCERNS — parity holds; one P1 provenance defect in the paper.

## Scope

`docs/paper/tendcf-architecture-paper.md` (1491 lines), read against the guide,
`examples/services.yml`, `schema/common.schema.json`, and `examples/broken/`.
Section-by-section comparison focused on the six surfaces where drift would be
most damaging: worked examples, status/validation, open questions, scope
ceilings, token discovery, trust.

## Parity result: holds

| Guide | Paper | Result |
|---|---|---|
| §17 three ceilings | §1.1 three ceilings | Same three, same order, same content. Paper adds section cross-refs and calls them "theoretical"; guide does not. Not material. |
| §19 nine open questions | §8.1–8.9 | Same nine, same order, same substance. |
| §18 built / not-built | §7 Status and validation | Agree on both lists, on the twelve fixtures, and on the identical Step 0 remainder (`peer_actions`, trust-policy shape, generic unit-writers, lookup stub, YAML canonicalize). Paper adds detail the guide omits (two of twelve fixtures exposed useless error messages) — enrichment, not contradiction. |
| §15 token discovery | §2.9 | Textually near-identical, including the same defect (below). |
| §16 worked examples | §2.6 | Same two examples, same fixture records, same illustrative-output markers. Paper additionally shows a Nix-frontend rendering, correctly marked unbuilt. |
| §12 interlock constants | §2.6, §6.1 | Both state `blocks`/`report` are `const`; both true against the schema. |

Six of six named broken fixtures in §7 ("an opt-out with no reason, a rogue
launchd label, a nested writer prefix, a literal secret where a key name
belongs, a typo'd capability token kind, an enforce-mode row carrying an
audit-mode outcome") map to real directories `01`, `03`, `04`, `06`, `07`,
`09`. Verified.

**No contradiction found on current design.** The parity claim in the guide's
opening paragraph is accurate.

## Findings

| Priority | Problem | Evidence and justification | Required resolution |
|---|---|---|---|
| **P1** | Paper §2.6 Example B is not a verbatim excerpt, under a preamble that stakes the reader's trust on exactly that distinction. | §2.6 opens: "**A note on provenance, because it matters for how to read these.** The *inputs* below are **verbatim excerpts** from `examples/services.yml`". Example A's fence repeats it: "excerpt from the real, schema-validated fixture; description/hosts/role/managed_by trimmed for space, **values unchanged**". Example A survives this — its omissions are dropped fields, no rewording. Example B does not: the interlock `description` reads "**The mesh VPN** must be authenticated… whose **VPN** is unauthenticated", where `examples/services.yml:39` reads "**Tailscale** must be authenticated… whose **Tailscale** is unauthenticated". Affected audience: a reviewer. The whole section exists to let a reader tell mechanically-produced input from hand-authored output, and §7 leans on that same distinction to keep the paper honest about having no running compiler. A reader who spot-checks the fixture finds the one explicitly-guaranteed claim false, which discredits the surrounding markers that *are* accurate. | One string, one edit — but decide which direction. **Note the docs are the consistent pair here:** guide §16.B and paper §2.6 both say "the mesh VPN"; the fixture is the outlier, consistent with commit `4deab3d` ("drop last-system layout language from fixtures") having reached the prose in both documents and missed this fixture string. Against that: "Tailscale" is not last-system branding here — it is the actual tool, and appears legitimately throughout the same fixture (`tailscaled`, `tailscale_authenticated`, the `pre_action` command, the interlock `id`). So generalizing only this one prose field was likely deliberate de-branding of *reader-facing* text. Either (a) change `examples/services.yml` to match the two documents, or (b) restore the fixture's wording in both documents. (a) is one edit and preserves the "verbatim" guarantee; (b) is two edits and keeps the fixture self-consistent. Do not resolve by weakening §2.6's provenance sentence — that sentence is one of the paper's strongest credibility moves. |
| **P2** | Paper §2.9 under-enumerates the closed token-kind set, identically to guide §15. | §2.9: "Token *kinds* are a closed enum in the schema (`service`, `port`, `path`, `secret`, `class`, `network`, …)". `schema/common.schema.json` `$defs.capability_token` admits eight: `service\|port\|path\|class\|package\|device\|network\|secret`. `package` and `device` sit behind the ellipsis in both documents. Same finding as F4 in the consistency audit; recorded here so the fix is applied to both. | Same resolution as F4: enumerate all eight, or point at `schema/common.schema.json#/$defs/capability_token` as canonical. Because the two documents duplicate this list verbatim, the pointer is the better fix — an inline copy has now drifted in two places at once. |

## Interaction with the consistency audit

The two P1s from pass A stand unchanged; neither is affected by the paper.
The guide's §16.B wording defect, filed there as **P3**, should be re-read in
light of this: the guide's provenance sentence ("The inputs below are
excerpts from `examples/services.yml`") is weaker than the paper's, so the
same underlying string mismatch is a minor imprecision in the guide and a
falsified explicit guarantee in the paper. **Fixing the fixture (option (a))
resolves both at once.**

Running total across pass A and A-2: three P1, three P2, two P3. All are
documentation or tooling defects. None is a design finding — that is passes
B, C, and E.

## Unverified claims and residual risks

- **§3, §3.1, §3.2 (the design rule and its nine instances), §5, §6 not
  audited in depth.** These are argument, not current-design claims, and are
  the proper subject of pass B. Skimmed only for contradiction against the
  guide; none found.
- **External citations still unverified** (~40 references in the paper's
  reference list, more than the guide's 15). Same disposition as pass A:
  belongs to pass B or D.
- **Numeric claims about Bcfg2 not checked against the source papers** —
  "four months, one person, roughly three FTE… across a division of about two
  hundred people" (§7), and the `Total managed entries: 0 / Unmanaged entries:
  2308` transcription (guide §11). Both are load-bearing comparisons. Assign
  to pass D.
- Same model/effort deviation as pass A: Opus 5 / medium in a large session
  rather than a clean Sonnet 5 / high run.

## Checklist: 30/35 complete

**Incomplete:**

- §1 / §4 external contracts and official sources — out of scope by design;
  next action: pass B or D.
- §4 "Verify numeric counts with a reproducible query" — the Bcfg2 FTE and
  managed-entry figures were not checked against the cited papers. Impact: two
  load-bearing comparisons unverified. Next action: pass D.
- §4 "Execute examples" — lint still not run (needs `uv` plus network).
- §3 "Judge content by document kind" — applied to the paper's current-design
  sections only, not to §§3–6 as argument. Impact: none for parity. Next
  action: pass B.
