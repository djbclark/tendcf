---
schema_version: 1
handoff_id: a7c7
parent_handoff_ids: [8810]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 957a2f7d121bae9737fddf6e2e5f8fcb0f6d6574
created_at: 2026-08-15T11:24:18-0400
writer: claude-code
---

# Handoff — cheap corrections landed; CFEngine simulate has no machine-readable output

## The Goal

Two things, in the operator's stated order: "clean up little things that
don't require much thought first, and then move to what you think the
highest value things to do are." Plus a standing framing that governs every
judgement below:

> An overriding goal of tendcf is to re-use existing tools, and especially to
> use CFEngine as the actual on-machine change agent. We want to minimize the
> amount of code we need to maintain, and maximize the abilities for other
> people to plug in to our architecture to add features, eg the arbitrarily
> complex change acceptance measures users can choose to implement.

This session also took the orchestrator role for the other tendcf CLI
sessions.

## Where We Are

`master` at `957a2f7`, clean, **pushed**. Three commits this session, all
pushed to `origin/master`:

| SHA | What |
| --- | --- |
| `0163b70` | The thirteen cheap corrections (synthesis §6 item 5) + DOC-1 |
| `0b64c32` | Closed both open CFEngine questions — **partly wrong, superseded** |
| `957a2f7` | Corrected the above after actually running `cf-agent` |

`bin/schema_lint.py` passes: `OK (5 schemas, 12 negative fixtures)`.

The guide itself has now been edited for the first time since the review
round — previously every finding was still open.

## What We Tried

**Reasoning from source instead of running the binary — and getting it
wrong.** This is the expensive lesson of the session and the reason `0b64c32`
needed `957a2f7` on top of it.

I read `cf-agent/simulate_mode.c` and `libpromises/changes_chroot.c`, found
four structured record files in the changes chroot (`/changed_files`,
`/renamed_files`, `/kept_files`, `/pkgs_ops`), and concluded — reasonably, and
wrongly — that a briefing generator could read them and diff the chroot tree
instead of parsing `--simulate=diff` prose. Committed and pushed that.

Then ran it. `cf-agent.c` prints the report and calls
`CallCleanupFunctions()`, which **removes the chroot**. After exit,
`<workdir>/state/` holds no `*.changes` directory at all, and there is no
retain flag. The record files are real, well-structured, and unreachable to
any consumer that is not inside the process.

The source was not misread. It simply did not contain the fact that mattered,
which lived in the teardown path of a different file. **Where a binary is
installed, run it before writing the conclusion down.**

**`--simulate=manifest` as the machine-readable alternative — also no.** The
`#define DELIM_CHAR '='` and the `ManifestStatInfo()` key-ish output made
manifest mode look like it might be key=value. Ran it: it emits `stat(1)`-style
prose (`'<path>' is a regular file`, `Size: 23`, `Access: (0644/rw-r--r--)`,
`Contents of the file:`). Also a report, also not a format.

**First `--simulate` run dropped to failsafe.** `cf-promises` must be
symlinked into `<workdir>/bin` or cf-agent cannot pre-validate and falls back
to `failsafe.cf`, which then fails on missing keys and no policy server. Also
`RunDiff()` invokes `<bindir>/diff`, so `diff` needs to be there too. Repro is
in the note; not a blocker, just non-obvious.

**Peer polling needed the `[ref]` suffix.** Bare names from `ListAgents`
(`tendcf-e4`) were rejected; `SendMessage` required `tendcf-e4 [b7c98e]`.

## Key Decisions

**Chosen.**

- **DOC-4 deferred deliberately.** Renaming one of the two "capability" lists
  is entangled with synthesis finding E1, which may delete the capability
  vocabulary outright. Not a cheap correction until E1 is decided. Everything
  else in synthesis §6 item 5 was done.
- **Qualified every bare `§N` cross-reference as `guide §N` or `map §N`.** The
  reviews README notes the correct `§0 rule 6` reference "looks wrong by
  association" with genuinely stale neighbours. Ambiguity was the root cause,
  so the fix is disambiguation, not just correcting the stale ones. Verified
  against v3 first: `§0 rule 6`, `§4.1`, and `§14.1` were **right**; `guide §8`
  (×2), `guide §4.1`, `guide §6` in `services.schema.json`, and the two
  `§12`s were wrong.
- **Made §3's pairing claim true in code rather than weakening the prose.**
  `schema_lint.py` now derives schema↔example pairing from the filesystem with
  a `DEFINITION_ONLY_SCHEMAS = {"common.schema.json"}` allowlist. Both
  reviewers preferred the machine-checkable option; it is also the guide's own
  §9 rule 2 applied to the guide.
- **Recommended upstreaming a JSON output mode to CFEngine** as the way to
  close the simulate gap. Under "re-use existing systems, minimize maintained
  code, let others plug in," a rendering patch to a GPL project the design
  already depends on beats a parser tendcf owns forever — and it gives every
  CFEngine user a programmable simulate.

**Rejected.**

- **Parsing the simulate report.** Cheap to start, permanently fragile: the
  record separator is a dash rule sized from `$COLUMNS`, and the prose lines
  are printf format strings with no stability guarantee. This is the option
  that quietly becomes maintained code.
- **Reading the chroot from a wrapper mid-run.** The path is deterministic and
  announced on stderr (`<workdir>/state/<pid>.changes`), so it is *possible* —
  but it races cleanup on every run.
- **Editing `architecture-DEFINITIVE-v3.md`.** It carries the same dead LISA
  '05 URL at line 302 and is protected by `bin/check_protected_docs.py`
  (requires an `Approved-change:` trailer). Left for the operator. **Still open.**
- **Switching Claude accounts.** Possible without a restart, but pointless
  right now — see Evidence.

## Evidence & Data

**CFEngine, verified on this machine (not from docs):**

- `--simulate` is **Community**. `cf-agent/simulate_mode.c` is in
  `cfengine/core` under plain GPL-3 (the COSL line in its header is
  dual-licensing, not a feature gate); Homebrew's formula license has no
  commercial component; and **CFEngine Core 3.27.1 is installed** at
  `/opt/homebrew/bin/cf-agent`, whose `--help` lists
  `--simulate value - Run in simulate mode, either 'manifest', 'manifest-full' or 'diff'`.
- **No root needed.** `CFENGINE_TEST_OVERRIDE_WORKDIR` gives a writable workdir.
- **Chroot isolation works.** After a `--simulate diff` run that reported
  `-original line` / `+new line from cfengine`, the target file still contained
  `original line`.
- **No machine-readable output in any mode, as shipped.** Both `diff` and
  `manifest` emit human reports; the structured records die with the chroot.
- Unchanged from the earlier note: **only files and packages promises are
  simulated** — the "loaded and running" half of a service change never appears.

**Correcting the guide's own CFEngine claim (DOC-24):** the guide said
`def.json` *and* `host_specific.json` had been native since 3.7. Per the
version history on the page the guide already links: 3.7.0 put augments in the
MPF, 3.7.3 back-ported `def.json` into the core agent, but
**`host_specific.json` has only been parsed since 3.18.0**. Using both files
sets the CFEngine floor at **3.18**, not 3.7. No minimum version had been
stated anywhere in the project.

**Dead links (DOC-26) were broader than reported.** The synthesis named LISA
'05; LISA '06 is broken the same way. All four forms curl-tested:
`usenix.org/legacy/publications/library/...` → **404** for both;
`usenix.org/legacy/events/...` → **200** for both.

**Lint negative-tested, both directions:** a new schema with no example →
`schema/orphan.schema.json has no example: …`; a new example with no schema →
`examples/orphan.yml is paired with no schema — register it in EXAMPLES`.
Restored clean afterwards.

**Files changed this session** (17 in `0163b70`, 1 in the two CFEngine commits):

- `docs/paper/tendcf-architecture-guide.md` — DOC-1, 3, 20, 21, 23, 24, 26 + §3 pairing prose
- `bin/schema_lint.py` — `check_pairing()`, `DEFINITION_ONLY_SCHEMAS`, docstring now "Five layers"
- `schema/{common,report-row,launchd-writers,services,roles}.schema.json` — cross-reference drift
- `examples/services.yml` + 7 `examples/broken/*/` overlays — DOC-5 "the mesh VPN"
- `examples/launchd-writers.yml` + `examples/broken/04-*/` — `map §14.1`
- `docs/architecture/cfengine-feasibility-of-diff-plan-2026-08-15.md` — the addendum, then its correction

**Peer sessions.** Five idle tendcf peers, all polled. Two replied, both done,
both safe to close: **pre-mortem** (`..._opus-5-high_premortem.md`) and
**red-team** (`..._opus-5-max_redteam-trust-consent.md`). Three never replied
(skeptical, exposition, one other); their outputs are all committed and pushed,
so closing them is low-risk. **Nothing was closed.** One item that lived only
in the red-team's context, now captured here: TC-39's "historical secret
handles" cites `FLEET_ADBKEY`, from
`docs/architecture/deprecated/trust-layer-hardened-design-grok-v1.md`.

**Quota, live at handoff time** — these are percent **used**, higher is worse:
account 1 `djbclark@mit.edu` **99%** (5h, resets 13:50), account 2
`djbclark@gmail.com` **94%** (5h, resets 14:39). `cswap auto` moved the active
account from 2 to 1 mid-session. Both effectively spent.

## Operator Feedback

- **"Clean up little things that don't require much thought first, and then
  move to what you think the highest value things to do are."** Followed
  literally — cheap corrections first, then the two E1-gating questions.
- **"We did talk about this some, so do not re-do work there, but you should
  read everything with that in mind."** The reuse-CFEngine constraint is a
  reading lens for existing material, not a fresh research task.
- **"Don't want to lose the cfengine stuff."** Durability over further
  investigation when quota is short — write up first, explore second. This is
  why `0b64c32` was pushed before the empirical run rather than after.
- **Standing: commit and push without asking**, at milestones. Applied to all
  three commits and to this handoff.
- **New standing request: proactively flag good `/compact` moments** in words,
  at natural seams, rather than relying on the hook line. Saved to auto-memory
  as `flag-good-compact-moments`.

## Where We're Going

1. **Open a CFEngine upstream issue asking for machine-readable simulate
   output** — a `--simulate-output=json` flag, or a flag that retains the
   changes chroot. The data structures are already populated
   (`libpromises/changes_chroot.c`), so this is a rendering change, not a
   feature. **This gates what Step 3 builds**, and it is the single highest-
   leverage action available: if it lands, tendcf maintains zero lines of
   parsing and every CFEngine user gets a programmable simulate. Do this
   before writing any tendcf code that touches simulate.
2. **Write the ChangePlan schema for BOTH candidate models** — the current
   capability-vocabulary model and the E1 diff-derived model — with paired
   `examples/` fixtures and negative fixtures under `examples/broken/`, then
   exhibit one plan end-to-end in guide §16. Writing both drafts is how you
   learn which model is actually specifiable. Synthesis §6 item 1, re-scoped
   by `docs/architecture/cfengine-feasibility-of-diff-plan-2026-08-15.md`.
   Note item 1 above may change the answer, so sequence it after.
3. **Decide the `architecture-DEFINITIVE-v3.md:302` dead LISA '05 URL.** Same
   fix as the guide (`.../legacy/events/...`), but the file needs an
   `Approved-change:` trailer. Operator call.
4. **Reconcile the guide with the map on the parameters it drops** — DOC-1's
   precedence sentence has landed, but the underlying drift (the map's 2-of-3
   root and NAR digests, which the guide states only generally) has not been
   reconciled. Synthesis §6 item 2, second half.
5. **Extend guide §19 and rewrite §17** so the risk apparatus covers the
   trust/consent subsystem — synthesis root cause S1, the strongest
   convergence in the corpus, and pure writing. Synthesis §6 item 3.
6. **Decide DOC-4** (renaming one of the two "capability" lists) once E1 is
   settled — deferred this session on purpose.
7. **Close or keep the three unreplied tendcf peers.** All output is pushed.

**Carried warnings.**

- Do **not** "fix" the `map §0 rule 6` references in
  `schema/common.schema.json` or `bin/schema_lint.py` — correct against v3 §0,
  and now explicitly qualified so they stop looking stale.
- **c174's action items** (paper length decision, §4.1 non sequitur,
  bibliography verification against `~/src/bcfg2/doc/papers/`, Acknowledgements)
  were not done by this session either, and their status remains unverified.
- Check quota with `cswap list`, not `aiuse --json` alerts.

## Quick Start

```bash
cd /Users/djbclark/src/tendcf
git log --oneline -4          # expect 957a2f7 at HEAD, clean
bin/schema_lint.py            # expect: OK (5 schemas, 12 negative fixtures)

# The two documents that carry all open findings:
#   docs/paper/reviews/2026-08-15_opus-5-xhigh_SYNTHESIS.md   (§6 = the ordered list)
#   docs/architecture/cfengine-feasibility-of-diff-plan-2026-08-15.md  (read the addendum)

# Reproduce the CFEngine simulate finding (no root, nothing touched outside the scratch dir):
mkdir -p /tmp/cfsim/cfwork/{inputs,bin,modules,masterfiles} /tmp/cfsim/sim-target
export CFENGINE_TEST_OVERRIDE_WORKDIR=/tmp/cfsim/cfwork
ln -sf "$(command -v cf-promises)" /tmp/cfsim/cfwork/bin/cf-promises   # else it drops to failsafe
ln -sf "$(command -v diff)" /tmp/cfsim/cfwork/bin/diff                 # RunDiff() uses <bindir>/diff
echo "original line" > /tmp/cfsim/sim-target/motd
# ...write a files: promise targeting that path, then:
cf-agent --simulate diff -f /tmp/cfsim/cfwork/inputs/promises.cf
ls /tmp/cfsim/cfwork/state/*.changes   # expect: no such file — the chroot is gone
```

Peer sessions: `ListAgents`, then `SendMessage` with the **`name [ref]`** form
(bare names are rejected).
