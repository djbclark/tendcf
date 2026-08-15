---
schema_version: 1
handoff_id: d199
parent_handoff_ids: [3a11]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 423a13165246875dba9b5d67e589584cac4ce443
created_at: 2026-08-15T17:49:26-0400
writer: claude-code
---

# Handoff — libntech PR 3 and the closed goal-file schema panel

## The Goal

Resumed from parent handoff `3a11` with three inherited jobs: collect the
CFEngine PR 2 agent's output, collect two stalled schema-opinion panes, and
launch the third (Fable) opinion on the goal-file schema. All three closed.
The operator then opened a fourth line of work mid-session — asking whether
the silent-zero-digest bug PR 2 had worked *around* had an upstream issue,
and if not, to fix it as a local PR 3. It did not, and PR 3 now exists.

Standing frame, unchanged: CFEngine work is drafted for upstream from a
temporary fork; nothing is pushed and no PR is opened, because a PreToolUse
hook gates upstream artifacts on operator approval and tripping it is
intended.

## Where We Are

Three workspaces, all clean:

| Workspace | Path | Branch | HEAD | State |
|---|---|---|---|---|
| tendcf | `~/src/tendcf` | `master` | `423a131` | clean, **pushed** |
| cfengine-core | `~/src/cfengine-core` | `simulate-json` | `071f85987` | `M libntech` (see below), unpushed |
| libntech | `~/src/cfengine-core/libntech` | `silent-digest-failure` | `da7d3d9` | clean, unpushed |

**The `M libntech` in cfengine-core is expected and must NOT be committed.**
It is only the submodule pointer noticing libntech is on `silent-digest-failure`
rather than its pinned commit. Committing it would bind PR 3 into PR 2's
branch; they are meant to be independent PRs against two different repos.

Four commits landed in tendcf this session, all pushed:

- `3b5f255` — the 406-line PR 2 implementation report, moved into tendcf
- `a8981c6` — Gemini 3.1 Pro goal-file schema opinion
- `77f9e9a` — Fable 5 (xhigh) goal-file schema opinion
- `423a131` — Grok 4.6 (xhigh) goal-file schema opinion

Three CFEngine PR branches now exist, none pushed, no PRs, all carrying a
placeholder `Ticket: CFE-XXXX`:

- PR 1 — `cfengine-core` `simulate-keep-chroot` `5dbd295f6`
- PR 2 — `cfengine-core` `simulate-json` `071f85987`
- PR 3 — `libntech` `silent-digest-failure` `da7d3d9`

## What We Tried

Chronological, including what did not work — this is the expensive part to
rediscover.

1. **Trusted the herdr `agent_status` field. Wrong.** `herdr agent list`
   reported `schema-codex` as `done`. It was not: it had hit an OpenAI
   usage limit (credits exhausted until Aug 20 05:00) and was parked on a
   "switch to gpt-5.6-luna?" prompt, having never written its deliverable.
   `agent_status: done` means "not currently generating", not "completed the
   task". **Always read the pane before believing the status field.**

2. **Flagged the PR 2 acceptance test's source-tree litter as a defect.
   Wrong, self-corrected.** `simulate_json.cf` leaves `.actual`,
   `.json.temp` and `.prose.temp` next to the source on a *passing* run. I
   compared it against `simulate_safe_functions.cf`, which leaves nothing,
   and called it a defect. Then I ran the pre-existing `manifest_mode.cf`,
   which litters identically — it is the suite's house idiom. No change made.
   The comparison test must be a sibling using the *same* pattern.

3. **Assumed the stray `simulate_mode_test.xml` needed a `.gitignore`
   entry. Wrong.** `.gitignore` line 77 has `class_test.xml`, which looked
   like a per-test-artifact convention worth extending. But `tests/.gitignore`
   already has a blanket `*.xml`; the file only appeared untracked because
   the previous agent ran the binary from the repo root instead of
   `tests/unit/`. Deleted it; zero PR noise. `class_test.xml` is a
   pre-existing wart, not a convention.

4. **First two probe builds failed to compile.** Including `platform.h`
   fails outside the build system (`unknown type name 'DIR'`, `strlcpy`
   macro collision on macOS) because it needs the build's config defines.
   And `libpromises/.libs/libpromises.a` does not exist — the build produces
   `libpromises.dylib` only. **Working recipe:** declare the handful of
   symbols `extern` yourself, link the `.dylib` plus
   `libntech/libutils/.libs/libutils.a`, and run with
   `DYLD_LIBRARY_PATH=~/src/cfengine-core/libpromises/.libs`.

5. **Nearly shipped PR 3 with only two of three sites fixed.** I fixed
   `HashFile_Stream()` and `HashPubKey()` and reported it complete. The
   operator asked whether the fix covered the second function "as a side
   effect", which prompted a completeness scan that found a **third** site,
   `HashNew()` — the worst of the three. Fixing two of three would have
   shipped. **The scan should have been the first step, not the last.**

6. **`session_log.py write` rejected `blockers` as a string.** It must be a
   list of strings. The error message is clear; the payload just has to match.

## Key Decisions

**PR 3 scope: log/fail-closed, do not change return types.** `HashFile()` and
`HashPubKey()` return `void`, so a caller cannot detect failure even once it
is logged. Making it detectable means changing both signatures, with callers
across `lastseen.c`, `crypto.c`, `cf-execd-runner.c`, `sysinfo.c`,
`tls_generic.c` and test stubs in both repos. *Rejected* as an API break far
out of proportion to the fix; named in the commit message as deliberate
scope, not oversight. `HashNew()` is the exception — it already returns
`Hash *` and already returns NULL on four other paths, so failing closed
there costs nothing.

**Each fix models its own in-file sibling rather than inventing a style.**
`HashString()` already logs in exactly this case; `HashNewFromDescriptor()`
already logs, destroys the context and returns NULL. Both fixes copy those
verbatim, including message wording. This is what makes the change
self-evidently an oversight repair rather than a new opinion.

**`HashBasicInit()` moved below the check in `HashNew()`** so the failure
path has nothing to free, matching `HashNewFromDescriptor()`'s ordering.
*Rejected*: adding a `free()` to the failure path, which would have kept the
diff smaller but diverged from the sibling.

**No unit test in PR 3, stated in the commit.** Forcing `EVP_DigestInit()` to
fail requires `CryptoDeInitialize()`, which lives in cfengine/core's
libpromises — libntech's own tests cannot depend on it (wrong direction), and
a libntech-level test could only assert the all-zero digest that is returned
either way. This follows the operator's standing rule that "the testable
seams do not exist" is an acceptable answer and the design must not be
contorted for coverage.

**Opinions are committed exactly as their authors wrote them.** Reviewer
findings — including a real bug in Gemini's sketch — go in the *commit
message*, never edited into the document. Set by `a8981c6` and followed by
`77f9e9a` and `423a131`.

**Codex dropped from the panel; Grok 4.6 substituted at the operator's
suggestion.** I had recommended dropping to a two-voice panel rather than
accepting a downgraded model on a load-bearing schema question. The operator
proposed Grok 4.6 via cursor-agent instead — better, because it preserves
three voices *and* adds vendor diversity (xAI alongside Google and
Anthropic). Run at `cursor-grok-4.6-xhigh` to match the panel's effort level.

**The PR 2 report moved out of the fork checkout into tendcf** (`3b5f255`).
It was untracked scratch in `~/src/cfengine-core/docs/`, where it was one
`git add -A` away from being swept into the upstream branch, and would be
lost on a re-clone.

**Hindsight hooks re-enabled** after measuring against the operator's ~12s
bar. Measured a *real* recall path, not just `/health`, because health was
the misleading signal last time — it read 6.08s while real calls failed at
21–30s.

## Evidence & Data

**PR 3 — the bug, verified three ways.**

No upstream issue exists: `NorthernTechHQ/libntech`'s GitHub tracker has 3
issues in its entire history, all closed, last 2025-03; `cfengine/core`
searches return nothing; no PR. Upstream tracks in Jira per core's
`CONTRIBUTING.md` → `https://northerntech.atlassian.net/` (project `CFE`).
Still live on libntech master (`0c0620d`) today.

Age and nature: `HashString()` has had the logging `else` since `f277970`
(2019-10-03, "Added hash functions from libpromises") — the commit that first
added all three. A six-year-old asymmetry, invisible until OpenSSL 3 provider
unloading made `EVP_DigestInit()` actually fail.

A/B measured with three standalone probes (hash → `CryptoDeInitialize()` →
hash), from the committed state:

| function | pristine upstream | with fix |
|---|---|---|
| `HashFile` | all-zero digest, **silent** | logs, names the file |
| `HashPubKey` | all-zero digest, **silent** | logs |
| `HashNew` | **non-NULL `Hash`, bogus digest, silent** | returns NULL, logs |

Site scan of `libutils/hash.c`: was 3 unguarded of 6 `EVP_DigestInit*` call
sites; now **0 of 6**. `libntech` `hash_test`: 6 tests, all pass (no
regression). `HashNew()` has **zero callers in cfengine/core** — only its
declaration and libntech's own tests — so the NULL return is downstream-safe.

Severity note: `HashPubKey()` feeds `lastseen.c`, `crypto.c`,
`libcfnet/tls_generic.c` and `client_protocol.c`. A public-key digest that
silently becomes a constant is a host identity that collides across every
host.

**PR 2 — independently re-verified, not taken on the agent's report.**

- 13 unit tests pass, direct and via `make check TESTS=simulate_mode_test`
  (which proves Automake registration, not just compilation).
- Acceptance test `29_simulate_mode/simulate_json.cf` → **Pass**.
- Live run: `sha256` = `6a5f63424a0c878f3b23b7a85dd453523605762e73f536f968f874e57f565d7e`,
  byte-identical to `printf 'new contents' | shasum -a 256`; real file left
  at `old contents`.
- `cf-agent --help` pairs the new `--simulate-json` row with its hint
  correctly (the OPTIONS/HINTS arrays are positionally coupled).

**TRAP, recorded in `3b5f255` and worth repeating:** neither PR 2 test can
catch a regression of the silent-zero-digest bug. The unit tests build their
own chroot without going through `GenericAgentFinalize()`, and the acceptance
test **normalizes `sha256` away** before comparing. The PR 2 report's own
advice ("run the acceptance test and check a digest is non-zero") therefore
does not work. Verify with a live run.

**The panel — three-way convergence, two claims verified by me.**

All three, written cold and without sight of each other, agree the goal file
is a **projection onto** the CFEngine Augments JSON, not the same artifact —
the question E1 explicitly left to whoever writes the schema. All three cut
`explain-hunk`. Fable and Grok *independently* reached the same §5.7-vs-§5.2
contradiction and *independently* arrived at tombstones.

Verified directly against `schema/common.schema.json`: its `domain_coverage`
`$def` has `default: true` on an **optional** `comprehensive` (so absent and
present-true are two spellings of one meaning), a **required** free-prose
`description`, a free-prose `note`, and two `if`/`then` contradiction guards.
E1 §5.7's "reuse verbatim" and §5.2's "no defaults, one spelling" cannot both
hold. **Confirmed, not a misreading.**

Verified against installed CFEngine Core 3.27.1: an unknown top-level key in
`host_specific.json` produces `warning: Invalid key '...' in the CMDB data
file ..., skipping it` and is dropped — ignore-unknown behaviour in the exact
file E1 §5.6 decided must fail closed. The same run showed `Invalid key
'data'`, which independently confirms Grok's other finding that **the guide
§16 illustrative `host_specific.json` loads nothing**, because it uses a
top-level `data` key.

Gemini's sketch has a real bug, recorded in `a8981c6`: its `content`
subschema pairs `additionalProperties: false` with
`patternProperties {"^.*$": {}}`, which cancel, leaving the object wide open —
the opposite of the strictness it argues for in its own position 1. Its cited
`$defs` (`domain_coverage`, `identifier`, `token`) do all genuinely exist.

Run costs: Fable 201,501 tokens / 23 tool uses / ~19m51s. Gemini 3.1 Pro
(high) delivered 109 lines; Fable 1,100; Grok 749.

**Hindsight:** `/health` 5ms; real recall `POST
/v1/default/banks/{bank}/memories/recall` → HTTP 200 in 0.66s
(`hermes-shared`) and 2.96s (`coding-agent::tendcf`). Against a ~12s bar and
a prior failing state of 21–30s. Three `HINDSIGHT_DISABLE_HOOKS=1` prefixes
removed from `~/.claude/settings.json`; JSON re-validated. Backups:
`~/.claude/settings.json.bak-2026-08-15` and `settings.json.bak-preenable-*`.

## Operator Feedback

- **"Go in your recommended order"** — approved collecting the cheap items
  before spending the Fable budget, rather than leading with the big run.
- **Proposed Grok 4.6 via cursor-agent** when I recommended dropping Codex
  and running a two-voice panel. Better call; adopted.
- **Asked whether the fix covered the second function "as a side effect."**
  It did not — it was a deliberate second hunk — but the question triggered
  the completeness scan that found the third site. Direct evidence that
  "did you check the rest?" is worth asking even when an answer looks
  complete.
- **Asked whether an account is needed to open an issue.** Answer given:
  the code is on GitHub (`NorthernTechHQ/libntech`, different repo *and* org
  from PR 1/2's `cfengine/core`), but the *ticket* lives in Northern.tech's
  Jira, which needs an Atlassian account; a GitHub issue there would likely
  go unread. **No fork exists** — `djbclark/libntech` and `frdminc/libntech`
  both 404 — and one is required before any PR.
- Standing, carried from the parent handoff: no AI-attribution trailer on the
  CFEngine commits (they are upstream-bound); tendcf's own commits do carry
  one. The four org-move PRs belong to the ops-specific agent — do not
  re-adopt them.

## Where We're Going

1. **THE NEXT ACTION: write the reconciliation pass over the three
   opinions.** Output a new doc under `docs/architecture/`. Do **not** edit
   the three opinion files — the precedent is that opinions land as written
   and reviewer findings go elsewhere. The inputs are already established
   and in Evidence above; do not re-derive them. The main unresolved split
   to adjudicate: Gemini and Grok follow E1's sorted arrays, Fable argues
   identity-keyed nested maps shrink the trusted canonicalizer — Fable flags
   this as a deviation from a closed decision and says it is mechanically
   reversible if the panel goes against it.
2. **Then the batched doc work**, which is now three items, not one:
   de-stale `docs/paper/tendcf-architecture-paper.md` (withdrawn capability
   vocabulary ~line 311, and its open question 8.8); fix the guide §16
   `host_specific.json` example, which loads nothing; and fix the guide's
   claim that YAML is a valid Augments input, which is false against 3.27.1.
3. **Decide the ticket story before any upstream filing.** All three commits
   carry `Ticket: CFE-XXXX`. The plan of record was ONE Jira ticket covering
   PRs 1–2; PR 3 is a different repo in a different org, so whether it shares
   that ticket is now an open operator decision. Filing is hook-gated.
4. **If PR 3 is to go upstream, a `libntech` fork must be created first** —
   none exists. That is an upstream artifact needing operator approval.
5. Optional cleanup: the panel left `w1H:pQ` (schema-gemini) alive. Panes
   `w1H:pN` and `w1H:pP` were closed this session.

## Quick Start

```sh
# Tier 1 pointer (read first)
~/.claude/hooks/handoff-tools/.venv/bin/python \
  ~/.claude/hooks/handoff-tools/session_log.py read \
  --state-root ~/.local/state/handoffs --dir ~/.local/state/handoffs/tendcf/main

# The three opinions to reconcile
cd ~/src/tendcf && ls docs/architecture/goal-file-schema-opinion-*.md
#   ...-gemini.md (109 lines)  ...-fable.md (1100)  ...-grok.md (749)
# The brief they answered, and the binding decision:
#   docs/architecture/GOAL-FILE-SCHEMA-BRIEF.md
#   docs/architecture/e1-adjudication-xhigh-2026-08-15.md

# Schema lint — MUST be run this way; bare python3 fails on jsonschema
uv run --with jsonschema bin/schema_lint.py

# PR 3
cd ~/src/cfengine-core/libntech && git log --oneline -1   # da7d3d9
git diff origin/master --stat                            # 21 insertions, 3 deletions
# NOTE: `git status` in ~/src/cfengine-core shows ` M libntech`. That is the
# submodule pointer only. Do NOT commit it — it would bind PR 3 into PR 2.

# Rebuild + re-run the PR 3 probes (probes are in this session's scratchpad;
# recreate from the recipe in "What We Tried" item 4 if that is gone)
cd ~/src/cfengine-core && make -j8
cd libntech/tests/unit && make check TESTS=hash_test    # 6 tests, all pass

# Re-verify PR 2 end to end
cd ~/src/cfengine-core/tests/unit && make check TESTS=simulate_mode_test
cd ~/src/cfengine-core/tests/acceptance && \
  ./testall --gainroot=env --bindir=$HOME/opt/cfengine-dev/bin \
  29_simulate_mode/simulate_json.cf

# Reproduce the Augments ignore-unknown finding (guide §16 fix)
# Put an unknown top-level key in $W/data/host_specific.json, then:
#   CFENGINE_TEST_OVERRIDE_WORKDIR=$W /opt/homebrew/bin/cf-agent \
#     -Kf $W/inputs/promises.cf --inform
```
