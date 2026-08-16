# Projector mapping reconciliation — 2026-08-16

Status: **decided**. This document closes the last open item of
`goal-file-schema-reconciliation-2026-08-15.md` §18 — the projector goldens
of §13, which could not be built because the mapping they were to be goldens
*of* had never been specified.

What was already decided and is **not** reopened here: the projector runs
device-side, inside tendcf-agent, after approval; its target is
`$(sys.workdir)/data/host_specific.json` and nothing else; its output is
`{"vars": {…}}` with no sibling keys (§9, and §13's adopted negative). What
this document adds is the mapping: which entries project, under what names,
in what bytes.

**Citation convention.** An unqualified `§N` here always means a section of
`goal-file-schema-reconciliation-2026-08-15.md`, the document this one
continues; the guide and the map are named where cited. This document's own
clauses are never `§N` — they are `P-n` (decisions), `N-n` (negatives), `E-n`
(measured CFEngine behaviour) and `C-n` / `R2n` (register), so a bare `§` never
points inward.

## 0. Method, and why the CFEngine claims here are load-bearing

Three independent opinions were collected cold — Gemini 3.1 Pro, Grok 4.6
(xAI), Cursor Grok 4.6 — each answering the same seven questions and each
required to print a complete worked projection so the positions would be
falsifiable rather than rhetorical. They are checked in beside this document
as `projector-opinion-{gemini,grok,cursor}.md`.

A fourth pass audited every citation in all three against the corpus and
against the **installed CFEngine 3.27.1 binary**, and this changed the
outcome. Two claims were refuted by live probe, one of them the mechanism the
minority position rested on. The probes below were re-run independently
before deciding; the CFEngine source they cite is byte-identical between
3.27.1 and the local checkout for `libpromises/cmdb.c`, `cmdb.h`, and
`var_expressions.h`.

The empirical findings that decide this document:

| # | Behaviour on 3.27.1 | Evidence |
|---|---|---|
| E-1 | An unscoped `vars` key lands at **`data:variables.<key>`**, tagged `source=cmdb`. | `cmdb.c:96–118`, `cmdb.h:31`; live `--show-vars` |
| E-2 | **`$(def.<key>)` does not expand** for `host_specific.json` keys. | Live: `DEF=[$(def.tendcf_service)]`, literal. `scope="def"` exists only on the `def.json` path (`generic_agent.c:453,573`) |
| E-3 | A **dotted** flat key is parsed as a scope path: `com.dotted.key` installs as `data:com.dotted.key`, scope `com`. | Live `--show-vars` |
| E-4 | Top-level primitives **stringify**; booleans and integers survive typed only **inside a container**. | `AddCMDBVariable`, `cmdb.c:121,131,140,152`; live `KEEPALIVE=[true]`, `EXIT=[0]` |
| E-5 | `$(`, `${`, `@{`, `@(` anywhere in `vars` fails the **entire** CMDB load, not just that key. | `var_expressions.h:90–97`, `cmdb.c:182`; live `error: Failed to load CMDB data` |
| E-6 | Only `vars`, `classes`, `variables` are legal top-level keys; others warn-and-skip. | `cmdb.c:542–546`; live `warning: Invalid key 'data' … skipping it` |
| E-7 | `variables` is loaded after `vars` and **overwrites** the same name. | `cmdb.c:550–560`; live `DUP=[from_variables]` |
| E-8 | A float `3.5` is installed as the **string** `"3.50"`. | live `Installing CMDB variable 'data:variables.afloat=3.50'` |
| E-9 | 5 MiB `HOST_SPECIFIC_DATA_MAX_SIZE` is a **hard** load failure. | `cmdb.c:38,522–527` |

One refutation is recorded against an opinion that otherwise won its
question: **hyphens are legal** in a `vars` key and expand correctly (live:
`HYPHEN=[hyp]`). Cursor's hyphen→underscore rule is adopted below, but *not*
for the reason Cursor gave, and the false justification is retired here so it
does not propagate.

## 1. P-1 — Only `supervision`'s `service` and `interlock` entries project

**Decision: the projection contains `supervision.entries.service` and
`supervision.entries.interlock`, and nothing else.** Not `device-trust`, not
`unit-writer`, not `coverage`, not `host`, not `schema_version`.

Grok and Cursor's position, adopted 2-1 over Gemini's whole-file wrap.

Gemini's argument is the serious one and deserves the answer: any include
table is a rule about what the data *means*, and a rule about meaning is
Model A's interpreter relocated rather than abolished. Three things defeat it.

1. **Its mechanism does not exist.** Gemini's addressing is
   `$(def.tendcf[domains][supervision][entries][service][id][state])`. Per
   E-2 that expands to nothing on 3.27.1; `def.` is the `def.json` scope, and
   `host_specific.json` lands under `data:variables`. The whole-file wrap is
   not merely more expensive than the alternative, it does not address.
2. **The filter is structural, not value-inspecting.** It keys on *domain
   class* and *kind* — positions in the schema whose vocabularies are closed
   and disjoint (`goal-file.schema.json:232`), fixed at schema-authoring time
   and never read from an entry body. R21's tripwire names inspection of
   entry **values**. A kind table is re-keying; that is exactly what R21
   licenses.
3. **The decided text already says trust does not go here.** R21's third
   arrow is `trust entries → the agent's own config`. The projector writes
   exactly one file and that file is not the agent's config, so the decided
   mapping routes trust entries *away* from the projection. Gemini's "project
   everything" contradicts R21 directly, which Gemini acknowledged.

The cost Gemini names is real and is accepted: whoever adds a future kind
must decide whether it projects. That editorial surface is the price, and it
is bounded by being a schema-level decision made once per kind, in the open,
rather than a per-entry one.

The confidentiality argument is upgraded from how the opinions put it. Per
E-1 every projected byte becomes an eval-context variable readable by every
bundle and dumped by `cf-promises --show-vars`. Projecting `device-trust`
would publish the advisor public key, the consent tier, the agent binary pin
and the policy-tree digest into the mutation engine's readable namespace —
creating a second read path for precisely the region
`goal-file.schema.json:232` reserves ("The validator and agent read their own
configuration ONLY from here"). That is a second source of truth, which the
corpus treats as a defect independent of whether anyone can write to it.

`unit-writer` does not project because it is detector data, not actuated
state (`goal-file.schema.json:209`); projecting the prefix registry would
invite a bundle to grow a sweeper over it, which is the extra-entry path the
corpus deliberately keeps report-only (§6, D16(d)).

## 2. P-2 — Two kind containers, `tendcf_service` and `tendcf_interlock`

**Decision: `vars` holds a closed set of kind containers named
`tendcf_<kind>`, each an object keyed by entry id, with the entry body copied
verbatim. Addressing is `$(data:variables.tendcf_service[<id>][<field>])`.**

Forced almost entirely by measurement rather than taste:

- Entry ids **must** be container indices, never key components. `E-3`: an id
  like `com.tendcf.caddy.main` in a flat key installs as scope `com`. Ids are
  reverse-DNS by construction, so this is not a corner case, it is every
  service.
- The container is **required for type fidelity**. E-4: `keep_alive: true`
  and `expect_exit: 0` survive as a boolean and an integer only inside a
  container; at top level they would stringify. A flat projection silently
  changes types.
- Ids are **not canonified**. They are the promiser and the launchd label
  (`goal-file.schema.json:77,122`); rewriting them would be a second spelling
  of identity. E-3 also confirms `getindices()` returns dotted indices intact,
  so nothing downstream needs the rewrite.
- The **kind token** is lowercased with `-`→`_`. Adopted as convention only.
  Cursor's stated reason — that hyphens are illegal in CFEngine identifiers —
  is **false on 3.27.1** and is retired here. The real reason is weaker and
  should be recorded as such: it keeps container names in one lexical class,
  and the rule is presently vacuous because neither projecting kind has a
  hyphen. It exists so a future hyphenated kind does not have to relitigate.

Gemini's single-container `tendcf` shape is rejected with its addressing, but
its warning against invented delimiters is honoured: there are none here.
Depth comes from real containers, and the only synthesised token is the fixed
`tendcf_` prefix.

## 3. P-3 — Tombstones stay in the same container, and R21's second arrow is clarified

**Decision: an entry with `state: "absent"` appears in its kind container
exactly like any other entry, with its `state` field copied. There is no
parallel absent-list, and no entry is dropped for being absent.**

All three opinions reached this independently and all three refused R21's
`tombstones → the negative-promise lists`. A 3-0 refusal of decided text is
not something to wave through, so the clause is resolved rather than ignored.

**The tension, stated exactly.** R21 says the projector is "a structural
re-keying only (entries → the generic bundle's containers, tombstones → the
negative-promise lists, trust entries → the agent's own config)" and, in the
same breath, that "any change that inspects entry *values* to decide output
*structure* is the interpreter returning". Routing on `state` is a conditional
on an entry value selecting an output container. Read as a specification of
projector output, the two halves cannot both hold.

**Resolution: C-1 — the second arrow is withdrawn as a sketch-promotion
error. It is an amendment, and is filed as one.**

An earlier draft of this document resolved the tension by reading R21's arrow
chain as system-level dataflow rather than projector output — arguing that
since arrow three ("trust entries → the agent's own config") cannot be
projector output, arrow two need not be either, so CFEngine renders the
negative promises from `state` at evaluation time. That reading was
adversarially reviewed and **refuted**. It is recorded here rather than
quietly deleted, because the refutation is the reason this clause is now an
amendment instead of a clarification.

It failed on three counts:

1. **The inference does not follow.** That arrow three is not projector output
   establishes only that the list is *not uniformly* an output spec. It does
   not select dataflow over the other candidates. The audit this document was
   built from said "if arrow three is not projector output, arrow two *need
   not* be either"; the draft upgraded that to "arrow two reads the same way".
   Possibility is not identity, and a heterogeneous list does not become
   uniformly dataflow because one member is.
2. **It was special pleading.** §1 of this document uses arrow three as a
   *binding output constraint* — the reason trust entries are routed away
   from the projection. §3 used the same arrow as proof the chain is *not* an
   output spec. The extra hop was granted only to the arrow that would
   otherwise force a tombstone split.
3. **Provenance inverts it.** The parenthetical is compressed from Fable's
   opinion, which reads "tombstones → the negative-promise lists **the generic
   bundle iterates**, trust entries → the *validator's* own config"
   (`goal-file-schema-opinion-fable.md:393–396`). "Iterates" names an *input
   the bundle walks* — projector output — not something the bundle renders at
   eval time. The 2026-08-15 copy dropped that qualifier
   (`reconciliation:527–529`). The dataflow reading does not recover a meaning
   the text always had; it inverts the words that were dropped.

The same provenance supplies the correct resolution. Fable's arrow one reads
"entries → `nix2cf_services`-style containers" — the guide §16.A preview-channel
vocabulary that this corpus has *already* demoted once, as C-9, for describing a
shape that does not load. The arrow chain is an illustrative sketch that was
promoted into decided prose without the ILLUSTRATIVE stamp §16.A received, and
lost a load-bearing qualifier on the way.

**So: the second arrow, read as a specification of projector output
containers, is withdrawn.** The tripwire in the same sentence is untouched and
keeps full force — it is now mechanical, as N-1. Arrow one stands and is what
P-2 implements. Arrow three stands and is what P-1 relies on. R21's filed
register entry (`reconciliation:1233`) already states the residue with **no
arrows at all** — "policy-free by discipline, not construction; value-inspecting
structure decisions are the interpreter returning" — so withdrawing the arrow
costs the register nothing.

This is an override of decided text, and calling it a clarification would have
been false: either the three opinions refused decided text, in which case the
operative meaning has changed, or they refused a misreading, in which case
"a 3-0 refusal of decided text" above would itself be wrong. The first is
true. C-1 is therefore filed in the same genre as the 2026-08-15 §15 register
(C-4 "corrected as written", C-9 the guide's Augments illustration), not
buried as a residue id — residue ids carry new costs, and are not the house
form for recording that yesterday's sentence has been overruled.

**P-3 does not depend on any of this.** It is independently forced, which is
why the mapping, the projector and the golden are unaffected by the refutation:

1. **C-4.** The tombstone persists in the goal file and the negative promise
   renders from the file; the projector is a function of the new goal file
   alone (`reconciliation:336–340`).
2. **R4 reborn if omitted.** Extra-entry detection reports and does not
   remove, so a comprehensive domain with no projected tombstone has a
   removal with no actuated path (`reconciliation:347–355`).
3. **Briefing honesty.** The distinction between "stops being managed; the
   thing REMAINS" and "will be stopped and unloaded"
   (`reconciliation:343–345`) is a lie if the mutation engine cannot see the
   tombstone.
4. **3-0 on the mapping**, reached on those grounds rather than on any reading
   of R21.

What the refutation removes is only the claim that R21 *already said* P-3. The
decided mapping does not move, and the tripwire is cleaner for having the
sketch retired rather than reinterpreted.

## 4. P-4 — Secrets project as names, and `@{` is now a load-breaking negative

**Decision: `env` values are copied verbatim as secretspec key names. The
projector never resolves a secret, and emits no `@{…}` or `$(…)` sequence.**

3-0, and the schema already forbids anything else:
`common.schema.json:174,178` constrain both key and value to
`^[A-Z][A-Z0-9_]*$`, which cannot spell a secret value or an `@{…}` reference.
The projector is a pure function of a goal file that contains no secret
values, and it has no resolver and no call site for one.

The audit escalates this from a style rule to a hard one. Per E-5, a single
`@{` anywhere in `vars` fails the **entire** CMDB load — not that key, the
whole file. Guide §16.A's illustrative `"@{secrets.LITELLM_MASTER_KEY}"`
would therefore not merely leak-by-convention if copied, it would silently
disable every projected variable on the host. §16.A is already labelled
ILLUSTRATIVE and already warns it does not load; that warning is now known to
be an understatement, and N-4 below makes it executable.

## 5. P-5 — Interlocks project, whole

**Decision: `supervision.entries.interlock` projects into `tendcf_interlock`
with the entry body copied whole, including `blocks`, `report`,
`defines_class` and the full `pre_action`.**

3-0 on substance. The ceremony argument is decisive and belongs in the record:
baking an interlock's argv into a `.cf` file would turn "the Caddyfile moved"
into a change to the policy-tree digest — a privileged ceremony class — when
it is an ordinary supervision edit. Keeping it in per-host Augments keeps the
change in the class the goal-file diff already reviews.

No field is dropped on the grounds that "the bundle knows" it; a hidden
default is the two-spellings defect. Interlocks are present-only in v1 — there
is no interlock tombstone (`reconciliation:358–360`) — so P-3 does not apply
to this container.

## 6. P-6 — Determinism

**Decision:**

1. Output is `rfc8785.dumps(...)` — JCS, RFC 8785 — and the **bytes are the
   contract**. Not `json.dumps(sort_keys=True)`.
2. No trailing newline, matching `examples/goal-file.json`'s §13 exemption.
3. `vars` is **always present**, even if every container is empty.
4. A kind container with no entries is **omitted entirely**. Omission is the
   goal file's own spelling of "none"; an empty object would be a second one.
5. Entry bodies are copied without reordering, reformatting, or renumbering;
   JCS supplies the ordering.
6. The goal file admits no floats at all (`grep '"number"' schema/*.json` is
   empty; the only numerics are `expect_exit` and `timeout_seconds`, both
   `integer`), so E-8's float-to-string laundering cannot arise from a
   conforming input — and a non-conforming one must be refused, not
   normalised (N-3).
7. Duplicate entry ids across projecting kinds are **refused**, not
   last-wins. Last-wins would be a silent interpreter.

`project()` is a pure function of the goal-file bytes: no clock, no
environment, no filesystem read, no subprocess.

## 7. P-7 — The negative suite

§13 already adopted "a projection with any top-level key other than `vars` is
a negative". That is the floor, per F-9b, not the ceiling. Adopted additions,
each grounded in a measured 3.27.1 behaviour rather than a style preference:

| # | The projector must refuse / the suite must catch | Grounded in |
|---|---|---|
| N-1 | Output structure that changes when only an entry's `state` flips `present`↔`absent` (the R21 tripwire, made mechanical) | R21 + P-3 |
| N-2 | A top-level `variables` or `classes` key — legal to CFEngine, so `vars`-only checking by envelope shape misses it, and `variables` silently overwrites `vars` | E-6, E-7 |
| N-3 | Any `$(`, `${`, `@{`, `@(` anywhere in the output — one occurrence kills the whole load | E-5 |
| N-4 | A resolved secret **value** in `env`, or an `@{secrets.…}` reference | P-4, E-5 |
| N-5 | Any `device-trust` content reaching `vars` | P-1 |
| N-6 | A projection that is not `rfc8785.dumps` of itself — pretty-printed, trailing newline, or non-NFC | P-6.1 |
| N-7 | A float anywhere in the output | E-8, P-6.6 |
| N-8 | Output exceeding 5 MiB | E-9 |
| N-9 | An entry id canonified, truncated, or otherwise rewritten | P-2 |
| N-10 | Duplicate entry id across projecting kinds | P-6.7 |
| N-11 | Non-determinism: two runs over identical bytes differing | P-6 |
| N-12 | A verbatim deep copy of the whole goal file under `vars` — i.e. the rejected P-1 minority shape, which passes a naive `vars`-only check | P-1 |

N-12 is worth keeping even though its position lost: it is the failure mode a
future editor reaches for when the include table feels arbitrary, and it
satisfies every check §13 had before this document.

## 8. The golden

`project(examples/goal-file.json)` is **645 bytes**, checked in as
`examples/host_specific.json`:

```json
{"vars":{"tendcf_interlock":{"caddy-config-valid":{"blocks":"enclosing-bundle","bundle":"caddy","defines_class":"caddy_config_ok","pre_action":{"command":["/opt/homebrew/bin/caddy","validate","--config","/etc/caddy/Caddyfile"],"expect_exit":0,"timeout_seconds":30},"report":true,"state":"present"}},"tendcf_service":{"com.tendcf.caddy.main":{"bundle":"caddy","command":["/opt/homebrew/bin/caddy","run","--config","/etc/caddy/Caddyfile"],"env":{"CADDY_ADMIN_TOKEN":"CADDY_ADMIN_TOKEN"},"run_as":"caddy","state":"present","unit":{"launchd":{"keep_alive":true,"run_at_load":true}},"working_dir":"/"},"com.tendcf.caddy.retired":{"state":"absent"}}}}
```

Note what is visible in it: the retired service is present as a tombstone
(P-3), the admin token appears as a name and not a value (P-4), `keep_alive`
and `expect_exit` are a real boolean and a real integer (P-2/E-4), and no
`device-trust` byte appears (P-1).

## 9. Where the code lives

`bin/projector.py`, beside the two linters, as the **normative reference
implementation**. §13 says "CI invokes the agent's own projector", and
tendcf-agent does not exist; this repo is contract-only. The reference
implementation is what §13's gate runs today and what tendcf-agent must
reproduce byte-for-byte when it exists. It puts nothing Augments-shaped on
the wire, so §9's rejection of a compiler-shipped sibling is not reopened.

This is a **second implementation site**, and that is a real cost carried as
residue: two implementations can drift. It is accepted because the golden is
the shared oracle — drift is exactly what the byte comparison catches, which
is the point of goldens.

## 10. Register

### Corrections

| id | Correction |
|---|---|
| C-1 | R21's second arrow, `tombstones → the negative-promise lists`, is **withdrawn** as a specification of projector output. The arrow chain is an illustrative sketch (Fable `:393–396`) promoted into decided prose without §16.A's ILLUSTRATIVE stamp, losing the qualifier "the generic bundle iterates" that made the lists projector *input*. Arrows one and three stand; the tripwire in the same sentence stands and is mechanical as N-1; R21's filed register entry (`reconciliation:1233`) carries no arrows and is unaffected. P-3 rests on C-4, R4-reborn and briefing honesty, not on this. |

### Residues

| id | Residue |
|---|---|
| R22 | The reference projector in `bin/` is a second implementation site to tendcf-agent's. The golden bytes are the anti-drift oracle. |
| R23 | The kind-token `-`→`_` rule is convention with no mechanical force; hyphens are legal in `vars` keys on 3.27.1 (measured). Do not re-derive a mechanical justification for it. |

## 11. What this does not decide

- The generic bundle itself. This document fixes the data contract the bundle
  reads; the `.cf` that consumes `tendcf_service` and renders promises from
  `state` is not written here.
- `device-trust`'s actual destination. P-1 removes it from the projection;
  R21's "the agent's own config" names where it goes, and that file's format
  is not specified anywhere yet. **This is now the next open question.**
- Whether a future kind projects. Decided per kind, at schema-authoring time.
