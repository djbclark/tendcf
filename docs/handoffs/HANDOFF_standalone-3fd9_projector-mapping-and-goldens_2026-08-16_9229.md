---
schema_version: 1
handoff_id: 9229
parent_handoff_ids: [ad4c]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: c94579ef79b5dc330b77f400217502d8a8177b3b
created_at: 2026-08-16T12:20:00-0400
writer: claude-code
---

# Handoff — projector mapping, goldens, and being wrong twice

## The Goal

Close reconciliation §18's last open item: the projector goldens of §13.
The operator asked for an autonomous orchestration run — "act almost
entirely as an orchestrator of other agent's work" — while they slept,
and answered four scoping questions up front (see Operator Feedback).

The item had been logged for several sessions as "blocked on missing
code". That framing was wrong, and finding out why was the first real
result: §9 decided everything about the projector **except what it maps**.
Target, shape, location and timing were all fixed; which entries project,
under what names, was never written down anywhere. No implementation could
be correct against an unspecified mapping, so the mapping had to be settled
before any code.

## Where We Are

**§18 is fully closed.** master at `c94579e`, clean, pushed. Eight commits:

| SHA | What |
|---|---|
| `0d175ef` | `validate()` falls back to `error.schema_path` when the instance path is empty |
| `b12ee79` | xref_lint scopes to the live corpus: 52 findings → 0 |
| `c9e4e0e` | the projector mapping, adjudicated, three opinions checked in |
| `d699fd6` | `bin/projector.py`, the 645-byte golden, 10 gated fixtures |
| `630a4ed` | R21.1 withdrawn, replaced by C-1 |
| `c6e317e` | CI gates on xref_lint as well as schema_lint |
| `505393e` | the `Caught by` parentheticals made executable |
| `c94579e` | C-2: the numbers this session asserted and got wrong |

Both linters clean: `schema-lint: OK (8 schemas, 59 negative fixtures, 6
byte-class fixtures, 10 projection fixtures)`; `xref_lint` 0 findings over
28 live documents, 54 frozen.

**One review still in flight at the time of writing:** an adversarial
implementation review asking "can you defeat the projector gate?" — brief at
`scratchpad/job-review-impl.md`, output to `scratchpad/review-impl.out`.
It had not returned. **Anything it finds is unhandled work.** See Where
We're Going item 1.

## What We Tried

Chronological, including what failed — this is the expensive part to
rediscover.

1. **`cswap run 1 -- claude -p "PROMPT"` — FAILED, silently, three times.**
   The wrapper does not forward the positional prompt. The child starts with
   an EMPTY prompt, replies "What would you like to work on?", and exits
   **0**. Three delegated jobs "completed" having done nothing; only `git
   status` revealed it. Reproduced four ways: positional, `--no-share`,
   stdin pipe, and with `--dangerously-skip-permissions`. Plain `claude -p
   "..."` works, so the fault is claude-swap 0.25.0's argument forwarding.
   **Workaround:** `cswap run` only sets `CLAUDE_CONFIG_DIR` to a per-account
   profile and execs claude, so set it directly. Launcher written at
   `scratchpad/mit.sh`. Saved to auto-memory as `cswap-run-drops-the-prompt`.
2. **The per-account profile later reported "Not logged in".** After the MIT
   account's 5h limit was hit and reset, `CLAUDE_CONFIG_DIR=...sessions/
   1-djbclark_mit.edu claude -p` returned `Not logged in · Please run
   /login`, even though `cswap list` showed the account healthy at 0%.
   Fell back to the active account via `scratchpad/here.sh`. Not diagnosed.
3. **`claude -p` waits on stdin** when launched from a background bash job,
   emits `Warning: no stdin data received in 3s`, and can produce nothing.
   `here.sh` now redirects `< /dev/null`. One review run was lost to this.
4. **Two background jobs writing the same output path** — the lost review's
   retry shared `review-impl.out` with the failed original, which truncated
   it on exit. Give each dispatch its own output file.
5. **R21.1 — my own argument, refuted.** Detailed under Key Decisions.
6. **A botched mutation (M4, first attempt).** Inserting `pass` as the first
   statement of a loop body changes nothing; the lint stayed green and for a
   moment that looked like a gate failing to bite. Rewrote it as a real
   tombstone filter. Worth remembering: a mutation that does not mutate is
   indistinguishable from a gate that does not fire.
7. **`git checkout examples/broken/README.md` to undo a mutation** reverted
   uncommitted real fixes in the same file. Use a scratch copy as the
   restore source when mutation-testing an edited-but-uncommitted file.

## Key Decisions

### The mapping (decided in `projector-reconciliation-2026-08-16.md`)

- **P-1** Only `supervision.entries.service` and `.interlock` project.
  Not device-trust, unit-writer, coverage, host, schema_version.
- **P-2** Two containers, `tendcf_service` / `tendcf_interlock`, keyed by
  entry id, bodies verbatim. Addressed `$(data:variables.tendcf_service[id][field])`.
- **P-3** Tombstones stay in their kind container with `state` copied.
- **P-4** `env` values are secretspec key names, never values.
- **P-5** Interlocks project whole, including `blocks`/`report`.
- **P-6** JCS bytes are the contract; `vars` always present; empty kind
  container omitted; duplicate ids across kinds refused, not last-wins.
- **P-7 / N-1..N-12** the negative suite.

**Rejected: Gemini's whole-file wrap** (everything under one `vars.tendcf`).
Its argument was the serious one — any include table is a rule about
meaning, and a rule about meaning is Model A's interpreter relocated. It
lost on **mechanism**: its addressing was `$(def.tendcf[...])`, and
`$(def.<key>)` does not expand for `host_specific.json` keys on 3.27.1.
Re-probed independently before deciding.

**Rejected: Cursor's stated reason** for hyphen→underscore on the kind
token (that hyphens are illegal in CFEngine identifiers). Live probe:
`HYPHEN=[hyp]` expands fine. The rule was kept as convention and the false
justification retired as R23 so it does not propagate.

### C-1 — R21's second arrow withdrawn (this is the one to read)

All three opinions independently refused R21's `tombstones → the
negative-promise lists`, because routing on `state` is a value deciding
output structure, which R21's own tripwire calls the interpreter returning.

**My first resolution (R21.1) was wrong and was withdrawn.** I argued the
arrow chain was system-level dataflow, not projector output — since arrow
three ("trust entries → the agent's own config") cannot be projector output,
arrow two need not be either. An adversarial review refuted it on three
counts, all correct:

1. **Affirming the consequent.** That arrow three is not output establishes
   only that the list is not *uniformly* output. The audit I built from said
   "need not be"; I upgraded it to "reads the same way".
2. **Special pleading.** My own §1 uses arrow three as a *binding output
   constraint*; my §3 used the same arrow as proof the chain is not an
   output spec. The extra hop went only to the arrow that would otherwise
   force a tombstone split.
3. **Provenance inverts it.** Fable's original reads "the negative-promise
   lists **the generic bundle iterates**"
   (`goal-file-schema-opinion-fable.md:393-396`); the 2026-08-15 copy dropped
   the qualifier. "Iterates" means projector *input*. I verified this quote
   myself before conceding.

**Replaced by C-1:** the second arrow is withdrawn as a sketch-promotion
error — Fable's arrow one used the `nix2cf_services` vocabulary already
demoted once as C-9. Filed as an **amendment**, not a clarification, because
"no decided text changes" and "a 3-0 refusal of decided text" cannot both be
true. **No code changed**: P-3 rests on C-4, R4-reborn, briefing honesty and
the 3-0 agreement, never on R21.1.

### C-2 — the numbers I got wrong

A claims audit found five commit-message figures and two citations wrong.
Decisions unaffected; the measurements were the defect. Corrected in-document:
E-2 cited the local 3.28 checkout's line numbers for a 3.27.1 claim (447/567,
not 453/573); §1 cited `:232` (trust_domain) for the closed-kinds claim
(it is `state_entries` at `:54`). Not correctable (pushed): `0d175ef`'s
134/129 is 133/128; `b12ee79`'s "43 §19.x" is method-dependent (41 or 33),
its "four of the seven" is eight/six/four-files, its "for weeks" was one day,
its "279 ids" is 253.

**The pattern is the lesson:** every wrong number came from a subagent's
report relayed into a commit message without being re-derived. Every number
that WAS re-measured verified true. Delegating the work was fine; delegating
the measurement and then asserting it in my own voice was not.

### Smaller decisions

- **One rule class `projection`, not two.** A stale golden and a violated
  N-invariant are the same defect; a second class would fire from one call
  site and need a fixture when the golden's fixture is the golden.
- **`OUTPUT_ONLY_EXAMPLES`**, mirroring `DEFINITION_ONLY_SCHEMAS`, because
  the pairing rail wants a schema per `examples/*.json` and the golden is
  produced, not authored. A schema for it would be a weaker second statement
  of the mapping that could drift while still passing.
- **xref_lint scope, not suppression.** Frozen = handoffs, reviews,
  deprecated, opinions, E1 adjudications. Each archival directory's own
  `README.md` stays IN scope — they are live indexes whose links rot.
  `--all` still reports everything.
- **Backticks are the notation** for a machine-checked claim in a
  `Caught by` parenthetical; bare words beside one are prose.
- **Rejected: teaching xref_lint to parse ordered-list section ids.** It
  would invent 253 ids and silently resolve two genuinely dangling E1 refs.
  Trading 2 false negatives for 41 false positives is backwards.

## Evidence & Data

Measured CFEngine 3.27.1 behaviour (`/opt/homebrew/bin/cf-agent`,
throwaway `--workdir`, needs `bin/cf-promises` symlinked in):

- `$(def.tendcf_service)` → literal, unexpanded. `data:variables.tendcf_service[id][state]` → `present`.
- Dotted flat key `com.dotted.key` → installs as `data:com.dotted.key`, scope `com`.
- `keep_alive` survives as typed `true` inside a container; primitives stringify at top level.
- `@{`/`$(` anywhere in `vars` fails the ENTIRE CMDB load.
- Float `3.5` → string `"3.50"`. 5 MiB is a hard failure.

Golden: **645 bytes**, computed independently, matching what two opinions
arrived at separately.

Eight mutations against the projector gate, each restored (`d699fd6`):
golden byte-flip; `PROJECTING_DOMAIN`→device-trust; sibling `classes` key;
tombstones dropped; ids canonified; `rfc8785`→`json.dumps`; tombstones
routed to a sibling container; an extra key on absent entries only. All bit.
**M8 exists because M7 revealed N-1 was not the rule catching the tripwire** —
without it N-1 would have been a check that never fires.

Four mutations against the parenthetical check (`505393e`): `required`→
`minLength`, `if/then`→`if/else`, `propertyNames`→`additionalProperties` all
go red; **`abs_path`→`absent` stays green** — the measured limit, since a
service entry is a `oneOf` and the absent branch genuinely failed too.

Real defect found by that check on first run: case 40 declared
`schema (type)` but `$defs.coverage` is a bare `enum`. Wrong since written.

Reviews checked in: `docs/paper/reviews/2026-08-16_grok-4.6_r21-refutation.md`
and `2026-08-16_cursor-grok-4.6_claims-audit.md`, with their prompts.

## Operator Feedback

Four answers given up front, all still binding:

1. **Settle the mapping by opinion panel, then adjudicate** — matching the
   existing `goal-file-schema-opinion-*` pattern.
2. **`bin/projector.py` as reference implementation**, not spec-only and not
   scaffolding tendcf-agent.
3. **Queue:** schema_path fallback, executable README parentheticals,
   xref_lint findings, adversarial review — all four wanted.
4. **Scope: tendcf + nix2cf**, "move to broad if you are really out of
   things to do, and you are confident the work will be useful."

Also: "keep subagents coding for the next 6 hours without me" and permission
to `/compact` at opportune moments. Standing authorization to commit and push
without asking (auto-memory `commit-and-push-without-asking`).

**Timeline note for honesty:** the session ran ~90 minutes of real
orchestration starting ~00:50, then the machine slept; the next turn resumed
at 12:11 the same day. The six hours passed as wall-clock, not as work.

## Where We're Going

1. **THE NEXT ACTION: collect and act on the in-flight implementation
   review.** `cat /private/tmp/claude-501/-Users-djbclark-src-tendcf/246829e6-1718-46fa-b3a7-5be2d0d1dc1a/scratchpad/review-impl.out`
   — if the scratchpad is gone, re-run it: `scratchpad/here.sh
   scratchpad/job-review-impl.md <out> opus high` (brief is also reproduced
   in that file). It asks the one question nothing else did: **can a
   projection be wrong under the reconciliation yet accepted by
   `validate_projection()`, or can `bin/projector.py` be changed to emit
   wrong bytes while `schema_lint` still says OK?** A ninth mutation that
   does not bite is a real hole. Nothing has verified this yet.
2. **`device-trust`'s destination** — now the top open design question, per
   `projector-reconciliation-2026-08-16.md` §11. P-1 removed it from the
   projection and R21's third arrow names "the agent's own config", but that
   file's format is specified nowhere in the corpus.
3. **The generic bundle.** The data contract is fixed; the `.cf` that reads
   `tendcf_service` and renders promises from `state` is unwritten. C-1 makes
   this load-bearing: the negative-promise lists are the bundle's to iterate.
4. **nix2cf** was in scope this session and never touched.
5. Unrelated, carried from ad4c/0b22/7b18/4a48/b0ff: confirm
   `track-issue-activity.yml`'s Discussion path fires in site-djbclark —
   last scheduled run predates PR #158's merge.
6. Unrelated: `~/src/cfengine-core` still shows ` M libntech` — do NOT
   commit it. libntech#291, cfengine/core#6293, #6294 are filed.

## Quick Start

```bash
cd /Users/djbclark/src/tendcf && git log --oneline -8
bin/schema_lint.py     # expect: OK (8 schemas, 59 negative, 6 byte-class, 10 projection)
bin/xref_lint.py       # expect: 0 findings, 28 live / 54 frozen
bin/xref_lint.py --why-frozen   # why each document is out of scope
bin/projector.py examples/goal-file.json | cmp - examples/host_specific.json  # silent

# The decided mapping, read this before touching bin/projector.py:
sed -n '1,60p' docs/architecture/projector-reconciliation-2026-08-16.md

# Delegating a headless Claude job — do NOT use `cswap run N -- claude -p`,
# it drops the prompt. Own output file per dispatch, and close stdin:
claude -p --model opus --effort high --dangerously-skip-permissions \
  "$(cat prompt.md)" < /dev/null > out.md 2>&1
# Then verify by ARTIFACTS (git log / git status), never by exit code.
```
