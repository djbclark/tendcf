# Claims audit — the 2026-08-16 projector session

**Reviewer:** Grok 4.6 via Cursor, run headless via `cursor-agent -f -p`, 2026-08-16.
**Target:** commits 9325d0b..505393e and projector-reconciliation-2026-08-16.md.
**Prompt:** `prompt_claims-audit.txt`, beside this file.
**Brief:** verify every checkable factual claim; ignore style and judgement.
**Outcome:** the decisions all stood; several stated measurements did not.
Filed as C-2 in the reconciliation's register. Corrections to line citations
were applied to that document; commit-message errors could not be, since the
commits were already pushed, so C-2 is where they are recorded.

Dated artifact, pinned to the commits it reviewed. Do not edit to bring it
up to date.

---

| Claim | At | Verdict | Check |
|---|---|---|---|
| 645-byte golden | d699fd6, c9e4e0e, recon §8 | **TRUE** | `examples/host_specific.json` is 645 bytes, no trailing newline; matches the fenced JSON in the recon and Cursor’s JCS block. Grok states 645 twice. |
| 8 schemas, 59 negatives, 6 byte-class | all seven | **TRUE** | `schema/*.schema.json`=8; `examples/broken/*/`=59; `broken-bytes/*.json`=6. `schema_lint.py` prints this and exits 0. |
| 10 projection fixtures | d699fd6 onward | **TRUE** | `broken-projection/*.json`=10. Absent before d699fd6. |
| 52 findings → 0 (default) | b12ee79 | **TRUE** | Parent `0d175ef`: exit 1, **52** findings. `b12ee79` default: exit 0, **0** findings (`27 live, 49 frozen`). |
| `--all` still 52, “byte-identical to the output before” | b12ee79 | **TRUE** for the 52 finding lines; **FALSE** for full stdout | Finding lines match `0d175ef` exactly. Summary line changed: `76 documents, 544 sections, 52 finding(s).` → `76 documents linted, 544 sections indexed across 76 documents, 52 finding(s).` |
| 49 frozen / 27 linted | b12ee79 | **TRUE** at **b12ee79** | Later commits move this. |
| 28 live, 0 findings | c9e4e0e | **TRUE** at **c9e4e0e** | Frozen was **52**, not 53 (3 projector opinions added). |
| 28 live / 53 frozen | HEAD | **TRUE** from **630a4ed** | Review `.md` added. `xref_lint.py` now: `28 live, 53 frozen, 0 findings`. |
| 35 cells with a checked claim | 505393e | **TRUE** | 35 `schema (...)` rows with backticked tokens (cases 5, 13–43, 51, 56, 57). |
| 134 findings; 129 byte-identical; 5 `<root>` changed (11, 41, 51, 56, 57) | 0d175ef | **FALSE** (off by one) | `validate_loaded` over all 59 cases: **133** findings. **128** byte-identical, **5** changed, **0** rule-class changes. The five are exactly 11, 41, 51, 56, 57. After-text for 57 is `<root> (schema else/properties): False schema does not allow ['hunks/supervision/service/…']`. |
| 43 §19.x findings | b12ee79 | **FALSE** | **41** lines contain `§19.` (all in frozen reviews/E1). |
| “Four of the seven findings” in `docs/handoffs/*` are §9.12 | b12ee79 | **FALSE** | **8** handoff findings, **6** of them `§9.12`, in 4 files. |
| “had for weeks” (xref exit 1 / 52 findings) | b12ee79 | **FALSE** | `bin/xref_lint.py` first commit `aeb75d7` is **2026-08-15**; b12ee79 is **2026-08-16**. One day. |
| List-item `8. **Question?**` invents **279** ids; silently resolves `E1 §1.4` and `§6.6` | b12ee79 | **FALSE** on 279; **TRUE** on the two E1 ids | Same rule on the b12ee79 tree invents **253** ids (264 at HEAD). E1 has `## 1` / `## 6` and no `1.4`/`6.6`; the extra parser invents both. Guide §19 is an ordered list; `19.8` is item 8. |
| `grep '"number"' schema/*.json` empty | recon P-6.6 | **TRUE** | No `"number"` in `schema/*.json`. |
| Three `schema (pattern)` cells backticked | 505393e | **TRUE** | 31, 32, 35: `schema (pattern)` → `schema (\`pattern\`)`. |
| Five handoffs contain the grep | b12ee79 | **TRUE** | Five `HANDOFF_*.md` files contain `python3 bin/xref_lint.py \| grep -vE 'reviews/\|deprecated/\|handoffs/'`. |
| `check.yml` ran schema_lint alone until c6e317e | c6e317e, b12ee79 | **TRUE** | b12ee79 workflow has only Schema lint; c6e317e adds `bin/xref_lint.py`. |
| No document edited | b12ee79 | **TRUE** | `--stat`: `bin/xref_lint.py` only. |
| projector PEP-723 deps ⊂ schema_lint | c6e317e | **TRUE** | projector: `rfc8785`. schema_lint: `pyyaml`, `jsonschema>=4.21`, `rfc3339-validator`, `rfc8785`. Import is `importlib` by path. |
| Three of 27 live docs live in frozen directories | b12ee79 | **TRUE** | `docs/{handoffs,paper/reviews,architecture/deprecated}/README.md`. Still true at HEAD. |

---

## Eight mutations (d699fd6) — re-run in a throwaway copy of HEAD

All eight go red. Restore left that copy matching HEAD.

| Mut | Claimed | Reproduced |
|---|---|---|
| M1 one golden byte flipped | golden mismatch, 645 vs 645 | **TRUE** `645 bytes produced, 645 expected` |
| M2 `PROJECTING_DOMAIN` → `device-trust` | golden mismatch, 11 vs 645 | **TRUE** (`{"vars":{}}` is 11 bytes) |
| M3 `classes` beside `vars` | N-2, refused at source | **TRUE** `ProjectionRefused` … `top-level key 'classes' beside \`vars\` … (N-2)` |
| M4 tombstones dropped | golden mismatch, 599 vs 645 | **TRUE** (also a second N-1/empty-container finding) |
| M5 ids `.` → `_` | golden mismatch, 645 vs 645 | **TRUE** |
| M6 `rfc8785.dumps` → `json.dumps` | N-6, not its own JCS form | **TRUE** `projection bytes: bytes are not their own JCS canonical form … (N-6, P-6.1)` |
| M7 tombstones to a sibling | N-5/N-12, closed container set | **TRUE** `vars/tendcf_absent names no projecting kind … (N-5, N-12, P-1)` |
| M8 extra key on absent only | N-1, “a value decided the shape” | **TRUE** that string fires. Also golden 662 vs 645 (retired service already `absent`). |

---

## Four Caught-by mutations (505393e)

| Swap | Claimed | Reproduced |
|---|---|---|
| `required` → `minLength` (case 18) | red | **TRUE** `declares 'minLength' … reported ['required']` |
| `if/then` → `if/else` (case 16) | red | **TRUE** `declares 'if/else' … reported ['if/not', 'if/then', 'not', 'state_domain']` |
| `propertyNames` → `additionalProperties` (case 37) | red | **TRUE** `declares 'additionalProperties' … reported ['pattern', 'propertyNames']` |
| `abs_path` → `absent` (case 24) | stays green | **TRUE** `schema-lint: OK` |

`properties` / `additionalProperties` are absent from `APPLICATORS` in `bin/schema_lint.py` as claimed.

---

## CFEngine 3.27.1 (E-1..E-9)

Binary: `/opt/homebrew/bin/cf-agent` and `cf-promises`, **CFEngine Core 3.27.1**. Throwaway `--workdir` under `/tmp/tendcf-claims-audit/cf-probe`. `libpromises/cmdb.c`, `cmdb.h`, `var_expressions.h` are **byte-identical** between tag `3.27.1` and the local checkout.

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| **E-2** | `$(def.<key>)` does **not** expand for `host_specific.json` keys | **TRUE** (hardest check) | Live reports: `R: DEF_SVC=[$(def.tendcf_service)]` and `R: DEF_GEMINI=[$(def.tendcf[domains][supervision][entries][service][id][state])]` — literals. Same wrap **does** address: `R: DATA_GEMINI_STATE=[present]`. `--show-vars` has `data:variables.tendcf*` / `data:variables.tendcf_service`, no `def.tendcf*`. |
| E-2 cite | `scope="def"` only on def.json path at `generic_agent.c:453,573` | **FALSE line numbers for 3.27.1**; behavior true | On **3.27.1** those assignments are **447 and 567**. 453/573 are the local checkout (`3.28.0-111`). |
| E-1 | unscoped vars → `data:variables.<key>`, `source=cmdb` | **TRUE** | `--show-vars`: `data:variables.hyphen-key … source=cmdb`. `cmdb.c:96–118`, `cmdb.h:31`. Verbose: `Installing CMDB data container variable 'data:variables.tendcf_service'`. |
| E-3 | dotted flat key → scope path (`com` …) | **TRUE** | `data:com.dotted.key … source=cmdb`. |
| E-4 | top-level primitives stringify; typed only in a container | **TRUE** | Verbose: `Installing CMDB variable 'data:variables.KEEPALIVE=true'` / `EXIT=0` (string path). Containers: `Installing CMDB data container`. Reports: `KEEPALIVE=[true]`, `EXIT=[0]`, `INNER_BOOL=[true]`, `INNER_INT=[0]`. `cmdb.c:121,131,140,152` match 3.27.1. |
| E-5 | `$(` `${` `@{` `@(` anywhere fails the **entire** load | **TRUE** | Each of the four: `Invalid 'vars' CMDB data, cannot contain variable references` + `Failed to load CMDB data`. `--show-vars` after `@{` shows no `data:variables.good`. `var_expressions.h:90–97`, `cmdb.c:182`. |
| E-6 | only vars/classes/variables; others warn-and-skip | **TRUE** | `warning: Invalid key 'data' in the CMDB data file '…', skipping it`. `cmdb.c:542–546`. |
| E-7 | `variables` overwrites `vars` | **TRUE** | `data:variables.DUP  from_variables  source=cmdb` (vars had `from_vars`). `cmdb.c:550–560`. |
| E-8 | float `3.5` → string `"3.50"` | **TRUE** | `data:variables.afloat  3.50  source=cmdb`. |
| E-9 | 5 MiB hard failure | **TRUE** | File 5 242 899 bytes: `Could not parse JSON file … Unable to parse JSON without truncating` + `Failed to load CMDB data`. Under 5 MiB: no CMDB error. `cmdb.c:38,522–527`. |
| Hyphens legal | `HYPHEN=[hyp]` | **TRUE** | Report `HYPHEN=[hyp]`; `--show-vars` `data:variables.hyphen-key  hyp  source=cmdb`. |

---

## Provenance (630a4ed) — exact quotes

Fable `docs/architecture/goal-file-schema-opinion-fable.md:392–396`:

```392:396:docs/architecture/goal-file-schema-opinion-fable.md
What keeps this from quietly rebuilding Model A's interpreter: **the
projector must be policy-free**, a structural re-keying (entries →
`nix2cf_services`-style containers, tombstones → the negative-promise
lists the generic bundle iterates, trust entries → the validator's own
config). That is achievable only because entry bodies are already
```

2026-08-15 copy `docs/architecture/goal-file-schema-reconciliation-2026-08-15.md:525–529`:

```525:529:docs/architecture/goal-file-schema-reconciliation-2026-08-15.md
What keeps this from quietly rebuilding Model A's interpreter — the honest
cost of the decision, carried as residue R21: **the projector must be
policy-free**, a structural re-keying only (entries → the generic bundle's
containers, tombstones → the negative-promise lists, trust entries → the
agent's own config). That is achievable precisely because entry bodies are
```

Qualifier **“the generic bundle iterates”** is in Fable and gone in the 2026-08-15 copy. “validator's” → “agent's”. **TRUE.**

R21 register at `reconciliation:1233` has no arrows: “policy-free by discipline, not construction; value-inspecting structure decisions are the interpreter returning.” **TRUE.**

Fable arrow one is ``nix2cf_services`-style containers`` (same lines). C-9 demotes guide §16.A’s illustration as a shape that does not load. **TRUE.**

630a4ed “no code changes beyond one stale citation”: `--stat` is `bin/projector.py` `R21.1`→`C-1` (one line of comment), plus recon + two review files. Golden / ten fixtures / mapping code untouched. **TRUE.**

3-0 refusal of “tombstones → the negative-promise lists”: Gemini, Grok, Cursor all refuse a sibling absent-list / split on `state`. **TRUE.**

---

## Case 40 — “wrong since it was written”

`$defs.coverage` is a bare enum, no `type`:

```33:36:schema/goal-file.schema.json
    "coverage": {
      "description": "One enum, not common.schema.json's boolean+reason pair: ...
      "enum": ["comprehensive", "not-yet-migrated", "deliberately-unmanaged"]
    },
```

Fixture `40-boolean-reason-coverage-spelling` sets `coverage` to `{comprehensive: true, opt_out_reason: null}` — an object, so `enum` fails, not `type`.

History: first written in `9fdf437` (schema landing) as `schema (\`type\`)`. Coverage was already a bare enum **in that same commit**. Cell stayed `type` through d699fd6; `505393e` changed it to `enum`. **TRUE: wrong from the first commit, not later drift.**

---

## File:line citations (recon E-table and §0–§5)

| Cite | Verdict |
|---|---|
| `cmdb.c:96–118`, `cmdb.h:31` | **TRUE** on 3.27.1 |
| `generic_agent.c:453,573` | **FALSE** on 3.27.1 (447, 567). True on local HEAD. |
| `cmdb.c:121,131,140,152` | **TRUE** |
| `var_expressions.h:90–97`, `cmdb.c:182` | **TRUE** |
| `cmdb.c:542–546`, `550–560`, `38,522–527` | **TRUE** |
| `goal-file.schema.json:232` “validator and agent read … ONLY from here” | **TRUE** (trust_domain description) |
| `goal-file.schema.json:232` “vocabularies are closed and disjoint” | **FALSE** | Line 232 is trust_domain. Closed kinds are `state_entries` **54–64**. |
| `goal-file.schema.json:209` detector data | **TRUE** (`unit_writer_map`) |
| `goal-file.schema.json:77,122` id is promiser / launchd label | **TRUE** |
| `common.schema.json:174,178` env_map `^[A-Z][A-Z0-9_]*$` | **TRUE** |
| `reconciliation:336–340`, `343–345`, `347–355`, `358–360` | **TRUE** (spot-checked: tombstone-from-file, REMAINS vs unload, R4-reborn, interlock present-only) |
| jsonschema `descend()` short-circuits on `schema is False` without appending `path` | **TRUE** | `jsonschema/validators.py` `descend()` 406–414 `return`s before the `path`/`schema_path` appends at 442–445. Case 57 measured `path=[]`, `schema_path=['else','properties']`. |

---

## Where a message overstates what the code does

These are the traps:

1. **0d175ef’s 134 / 129** — the durable number is **133 / 128**. The five `<root>` cases and “no Caught-by row moves” are right.
2. **b12ee79’s 43, 279, “four of seven”, “for weeks”** — the scope-rule *behavior* is right (0 live, 52 on `--all`, README.md in archival dirs still linted). The ancillary measurements are not.
3. **E-2 line numbers** cite the local checkout, not 3.27.1. The live probe the whole mapping hangs on is still right: Gemini’s `$(def.tendcf[…])` does not expand; `$(data:variables.tendcf[…])` does.
4. **`goal-file.schema.json:232`** is used for two claims; only the trust-domain quote belongs there.

Not overstatements: projector mutations, Caught-by mutations, 645, 8/59/6/10, 35 cells, Fable vs 2026-08-15 quotes, case 40 history, E-1 and E-3–E-9, CI wiring.
