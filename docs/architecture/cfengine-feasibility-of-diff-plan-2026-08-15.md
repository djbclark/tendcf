# Can the diff-derived ChangePlan be built on CFEngine, or does it need a new mutation engine?

**Date:** 2026-08-15. **Author:** Claude Opus 5 (effort medium), from CFEngine
primary documentation; **addendum** the same day (effort xhigh) from the
CFEngine Community source and the locally installed 3.27.1 binary.
**Status:** research note, not a decision.

> The addendum at the end closes both items this note originally left
> unverified, and was itself run against the local binary rather than reasoned
> from docs. `--simulate` is Community and works without root. But **CFEngine
> has no machine-readable simulate output in any mode** — the structured
> records exist only inside a chroot that is deleted on exit. The addendum
> recommends upstreaming a JSON output mode rather than parsing the report.
> Read it before acting on the body.

## Why this exists

`docs/paper/reviews/2026-08-15_opus-5-xhigh_SYNTHESIS.md` finding **E1**: two
independent reviewers, one reasoning from security and one from build cost,
arrived at the same alternative — drop the inference stage and the closed
capability vocabulary; render a complete resolved goal file per host; make the
ChangePlan **mechanically the diff** between the host's currently-signed goal
file and the proposed one; derive the executor's allowlist from that diff.

The operator's constraint, stated 2026-08-15, is the thing E1 must survive:

> We do not want to create an entirely new configuration management system. We
> want to re-use existing systems in novel ways with some glue between them. For
> actually modifying computers we are limited to what CFEngine can do, and
> preferably CFEngine without calling many shell scripts.

E1 is only adoptable if it is buildable on CFEngine primitives. This note checks
that against the CFEngine documentation rather than from memory.

**Verdict: E1 is more CFEngine-native than the current design, not less.** One
piece of guide §7 is not a CFEngine concept — but it is not a CFEngine concept
under the *current* design either, and E1 makes it dramatically cheaper to pay.

## What is free — already how CFEngine works

**A complete resolved goal file per host is not a new mechanism.** CFEngine is
convergent: the agent evaluates the whole policy every run and repairs whatever
does not match. It has never been a diff-applier. So "the compiler emits complete
resolved goal state as data, and a generic bundle enforces it" is exactly the
Augments + data-driven-MPF design already described in guide §4. E1 does not ask
this to change; it asks the project to *stop adding* the capability vocabulary on
top of it.

**Restricting enforcement to an approved set is ordinary data-driven policy.**
Data containers pass to bundles by reference with `@(varname)`, and promises
iterate over lists. A bundle that iterates only over approved entries never
instantiates the unapproved ones — there is no promise to keep, so nothing
happens. No shell.

## The find: `cf-agent --simulate`

`cf-agent` has a `--simulate` option, distinct from and stronger than
`--dry-run`. From the CFEngine docs:

> The `--simulate` option tries to identify changes to your system without making
> changes to the system, however it goes further than `--dry-run` by making
> changes in a chroot and making a distinction between safe and unsafe functions.

It takes one of three summary modes:

| Mode | Reports |
| --- | --- |
| `diff` | only what changed during the simulated run |
| `manifest` | files and packages changed by the simulated run |
| `manifest-full` | everything evaluated, including unchanged |

Promises using unsafe functions execute under `--simulate` only when tagged
`simulate_safe`.

**Why this matters more than as an implementation convenience.** It is a diff of
a policy run computed by the same engine that will do the enforcing, on the
device, against the device's actual state. That is a direct answer to red-team
**TC-29** (the briefing describes a delta from a baseline the device may not be
at): the delta is not predicted by a compiler that has never seen the device.

It may also bear on **S2**, the synthesis's second root cause — that every
control in the trust layer is authored, delivered, and evaluated by the party it
exists to constrain, including the semantic briefing the person reads. A
device-computed `--simulate=diff` is the one artifact in the consent flow the
proposer does not author. That does not fix S2 by itself (the executor, the
policy, and the key still come from the operator), but it moves the briefing
from the proposer's side of the line to the device's, which no other proposed
change does.

**The limitation, and it is load-bearing here:**

> Only files and packages promises are simulated currently.

Not services, not commands. Since tendcf renders every service as a file — a
launchd plist, a systemd unit — the *file* half of a service change simulates
cleanly and would appear in a diff. The "loaded and running" half would not. A
simulate-derived briefing is therefore honest about content and silent about
activation. State this in the design; it is a gap, not a blocker.

## What is genuinely not CFEngine, in either design

### 1. The §7 executor gate

Guide §7: "The on-device executor maps declared capabilities to an allowlist and
**refuses any effect outside that set.**"

There is no CFEngine implementation of this. There is no way to tell `cf-agent`
"refuse to keep promises outside set X," because keeping the promises it is given
is the entirety of what cf-agent is. **CFEngine has no runtime capability
confinement.**

This is equally true of the current design — E1 does not introduce the cost. What
E1 changes is where the gate can live:

| Where the gate lives | Under the current design | Under E1 |
| --- | --- | --- |
| **Pre-flight validation of the signed artifact, before cf-agent runs** | Requires writing an interpreter for the capability vocabulary *and* proving it corresponds to what the policy will actually do. A new mechanism. This is the artifact red-team **TC-32** says does not exist. | A comparison of two JSON goal files against an approved diff. A validator, not an executor. No policy interpretation. |
| **Runtime confinement** | Needs OS-level sandboxing or a new mutation engine. | Same. Do not. |

**This is the strongest argument for E1 under the operator's constraint, and it
is stronger than the argument either source reviewer made.** E1 converts the one
piece that would have required a new mechanism into glue.

### 2. Removals need generated negative promises

Convergence means absence of a promise is absence of enforcement, not reversal.
Drop an entry from the goal file and the thing keeps running. The diff must
compile removals into explicit negative promises — file `delete`, package
absent, `service_policy => "stop"`. CFEngine can express all of these. The work
lands in the compiler, which is where it belongs.

### 3. The shell cost is real, and is not about E1

CFEngine's `services` promise hands `service_policy` to a **service bundle**,
which decides what to actuate:

> It is up to the mapped `service_bundle` to determine which promises should be
> actuated in order to converge to the specified `service_policy`.

On Linux that is the shipped `standard_services`. On macOS launchd and Termux
runit there is no native bundle, so tendcf supplies one — and it will need
`commands` promises invoking `launchctl` and `sv`.

That is unavoidable under any architecture, but it is **bounded**: one adapter
bundle per supervisor, written once, not shell scattered through the policy.
Guide §5 currently says "supervisors are adapters" in a way that implies more
purity than the platform allows. Worth writing the cost in explicitly.

## What would actually be built

Not a configuration management system:

1. A compiler that emits complete per-host goal state — **already the plan** (§4).
2. A diff-and-validate step over two signed JSON artifacts — **new, small**, no
   policy interpretation.
3. Removal-promise generation from the diff — **compiler work**.
4. One service-adapter bundle per supervisor — **already the plan**, with an
   honest and bounded shell cost.

What gets **dropped**: the capability vocabulary, its schema, its versioning, its
skew policy, and the executor that interprets it — the artifact roughly thirty of
the red-team's fifty-one findings are about.

## What E1 does not fix

E1's own accounting in the synthesis is honest and holds up:

- **TC-25** (a plan can rewrite the trust policy, the advisor key, or the
  executor) — still needs a privileged-resource class. The diff can still touch
  those paths.
- **TC-23** (the executor can refuse declarations, it cannot refuse effects) —
  **still unsolved, and unsolvable at this layer.** A package install runs the
  vendor's postinst script. No CFEngine-level allowlist stops that, and neither
  does a diff. Closing it needs OS-level confinement, which is out of scope.

The synthesis quotes the skeptical review's summary, which is the right framing:
"the enclosure problem survives; the *vocabulary* problem does not."

## Consequence for the build order

This makes SYNTHESIS §6 item 1 (write the ChangePlan schema, capability enum, and
trust-policy shape) **partly conditional**. Under E1 there is no capability enum
to write, and the ChangePlan schema becomes a diff format plus an approval
record.

Item 1 should still go first, but re-scoped: **write the ChangePlan schema for
both candidate models and see which one is writable.** If the diff-derived
version is obviously easier to specify, that is the answer — and it is far
cheaper to learn that from two schema drafts than from an architecture debate.

## Sources

All accessed 2026-08-15.

- [cf-agent — CFEngine docs (LTS)](https://docs.cfengine.com/docs/lts/reference/components/cf-agent/) — `--dry-run`, `--simulate`, `--show-evaluated-classes`, `--show-evaluated-vars`
- [cf-agent — CFEngine 3.21](https://docs.cfengine.com/docs/3.21/reference-components-cf-agent.html) — `--simulate` modes and the files-and-packages-only limitation
- [vars / data containers — CFEngine 3.19](https://docs.cfengine.com/docs/3.19/reference-promise-types-vars.html) — `@(varname)` pass-by-reference, iteration order guarantees
- [methods — CFEngine docs](https://docs.cfengine.com/docs/master/reference/promise-types/methods/) — passing data containers to bundles
- [services — CFEngine 3.21](https://docs.cfengine.com/docs/3.21/reference-promise-types-services.html) — `service_policy`, `service_bundle` delegation
- [classes — CFEngine docs (LTS)](https://docs.cfengine.com/docs/lts/reference/promise-types/classes/) — class guards on promise actuation

## Addendum, 2026-08-15 — the two open items, now closed

The first version of this note ended with two unverified questions. Both are
answered, from the CFEngine Community source and from a CFEngine binary that
turns out to be installed on this machine. The answer to the second is better
than the question assumed.

### 1. `--simulate` is Community, not Enterprise

Three independent confirmations:

- `cf-agent/simulate_mode.c` lives in [`cfengine/core`](https://github.com/cfengine/core),
  which is the Community repository. Its header is plain GPL v3. (The header
  also notes that COSL *may* apply "to the extent this program is licensed as
  part of the Enterprise versions" — that is ordinary dual-licensing of the
  same file, not a feature gate.)
- **CFEngine Core 3.27.1 is installed locally** at `/opt/homebrew/bin/cf-agent`.
  `cf-agent --help` lists it:
  `--simulate value - Run in simulate mode, either 'manifest', 'manifest-full' or 'diff'`
- The Homebrew formula's license field is `BSD-3-Clause AND GPL-2.0-or-later AND
  GPL-3.0-only AND LGPL-2.0-or-later` — no commercial component.

**Consequence:** the strongest argument for E1 in this note — that a
device-computed diff moves the briefing from the proposer's side of the line to
the device's — does not depend on an Enterprise licence. It is available on
every platform tendcf targets, today. There is also now a real binary on this
machine to test against, which the build order should use rather than reasoning
further from documentation.

### 2. `--simulate=diff` stdout is *not* machine-readable — and that does not matter

The stdout is a human report. From `simulate_mode.c`:

- `RunDiff()` shells out to `<bindir>/diff -u --label 'original <path>' --label
  'changed  <path>'` and copies that process's stdout to cf-agent's stdout
  verbatim.
- It is interleaved with prose for the non-diffable cases: `'<path>' no longer
  exists`, `'<path>' changed type from <a> to <b>`, `'<path>' is a <type>`.
- Records are separated by `PrintDelimiter()`, which prints a run of dashes
  sized from `$COLUMNS` (minimum 80, less 5). That is the only record
  separator, and its width depends on the caller's environment.

A briefing generator parsing that would be parsing prose against a
terminal-width delimiter. Do not.

`--simulate=manifest` is no better. Empirically (see the run log below) it
emits `stat(1)`-style prose — `'<path>' is a regular file`, `Size: 23`,
`Access: (0644/rw-r--r--)`, then `Contents of the file:` and the bytes. Also a
report, also not a format.

**Structured records do exist — but they are internal to the run, not an
interface.** `libpromises/changes_chroot.h` defines four record files inside
the changes chroot:

| File | Format | Written by |
| --- | --- | --- |
| `/changed_files` | length-prefixed strings, one path each | `RecordFileChangedInChroot()` |
| `/renamed_files` | length-prefixed string *pairs* (old, new) | `RecordFileRenamedInChroot()` |
| `/kept_files` | length-prefixed strings | `RecordFileEvaluatedInChroot()` |
| `/pkgs_ops` | **CSV** — op, name, arch, version | `RecordPkgOperationInChroot()` |

Alongside them, the chroot tree holds the actual post-change file *contents*,
reachable by mapping any real path through `ToChangesChroot()`.

**The catch: the chroot does not survive the run.** `cf-agent.c` prints the
report and then calls `CallCleanupFunctions()`, which removes the chroot. Ran
it and checked: after exit, `<workdir>/state/` contains no `*.changes`
directory at all. There is no flag to retain it. So those four files are
implementation detail — real, well-structured, and unreachable by any consumer
that is not inside the process.

The chroot path *is* deterministic and announced on stderr at the start of the
run (`<workdir>/state/<pid>.changes`), so a wrapper could in principle read it
mid-flight. That races cleanup on every run. Do not build on it.

### What this means for the design

The honest conclusion is narrower than the previous draft claimed, and points
somewhere better:

**CFEngine's simulate mode has no machine-readable output, in any mode, as
shipped.** A device-computed change set is exactly the artifact E1 wants and
CFEngine computes it — it just renders it for a terminal and then throws the
structure away.

Three ways to close that, in the order they fit the project's own constraints
("re-use existing systems… minimize the code we maintain… let others plug in"):

1. **Upstream a machine-readable output mode** — a `--simulate-output=json`
   flag, or a flag that retains the chroot. The data structures already exist
   and are already populated; this is a rendering change to a GPL project, not
   a feature. It is the smallest patch, it is plausibly welcome upstream, and
   it leaves tendcf maintaining **zero** lines of parsing. If it lands, every
   other CFEngine user gets a programmable simulate too — which is the
   pluggability argument the project makes about itself, applied to its own
   dependency.
2. **Parse the report.** Cheap to start, permanently fragile: the record
   separator is a dash rule sized from `$COLUMNS`, and the prose lines are
   printf format strings with no stability guarantee. This is the option that
   quietly becomes maintained code.
3. **Compute the diff outside CFEngine**, from the two signed goal files, and
   use `--simulate` only as a human-facing confirmation. This needs no upstream
   change and is where E1 already points — but it gives up the specific
   property that made `--simulate` interesting, namely a delta computed by the
   engine against the device's *actual* state rather than predicted by a
   compiler that has never seen the device (red-team TC-29).

**Recommendation: 1, with 3 as the fallback and 2 never.** Option 1 is a small
contribution to a tool the project already depends on, which is the same trade
the design makes everywhere else. Worth an upstream issue before any tendcf
code is written — the answer changes what Step 3 builds.

### The run log, for whoever repeats this

CFEngine needs a writable workdir. `CFENGINE_TEST_OVERRIDE_WORKDIR` sets one,
no root required:

```bash
export CFENGINE_TEST_OVERRIDE_WORKDIR="$PWD/cfwork"
mkdir -p cfwork/{inputs,bin,modules,masterfiles}
ln -sf "$(command -v cf-promises)" cfwork/bin/cf-promises   # else it fails to failsafe
ln -sf "$(command -v diff)" cfwork/bin/diff                 # RunDiff() uses <bindir>/diff
cf-agent --simulate diff -f "$PWD/cfwork/inputs/promises.cf"
```

Against a one-line file the policy rewrites, that printed a dash rule and:

```
--- original /…/sim-target/motd
+++ changed  /…/sim-target/motd
@@ -1 +1 @@
-original line
+new line from cfengine
```

**The real file was unmodified afterwards** — the chroot isolation works as
documented. `--simulate manifest` on the same policy printed the `stat`-style
block quoted earlier. Neither invocation needed root.

Unchanged by any of this: **only files and packages promises are simulated.**
The "loaded and running" half of a service change still does not appear.

### Sources for the addendum

All accessed 2026-08-15. GitHub reads via `gh api`; local binary is Homebrew
`cfengine` 3.27.1.

- [`cfengine/core` — `cf-agent/simulate_mode.c`](https://github.com/cfengine/core/blob/master/cf-agent/simulate_mode.c) — `RunDiff()`, `DiffFile()`, `PrintDelimiter()`, licence header
- [`cfengine/core` — `libpromises/changes_chroot.h`](https://github.com/cfengine/core/blob/master/libpromises/changes_chroot.h) — the four record-file names
- [`cfengine/core` — `libpromises/changes_chroot.c`](https://github.com/cfengine/core/blob/master/libpromises/changes_chroot.c) — `WriteLenPrefixedString()` records; `CsvWriterField()` for package operations
- [`cfengine/core` — `libpromises/eval_context.c`](https://github.com/cfengine/core/blob/master/libpromises/eval_context.c) — `ToChangesChroot()`
- `/opt/homebrew/bin/cf-agent --version` → `CFEngine Core 3.27.1`; `--help` → the `--simulate` line quoted above
