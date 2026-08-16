# Upstream CFEngine candidates: where a small fix would simplify or correct this work

**Status: reference record, kept in tendcf.** A survey, not a filing package.
Each item below is re-measured on the installed **3.27.1** binary rather than
carried over from the corpus, because relaying an unverified number is the
defect [`projector-reconciliation-2026-08-16.md`](projector-reconciliation-2026-08-16.md)
records as C-2. Where a fix site is named, the line numbers are from the local
checkout at **3.29.0a.17eb78e6d** and are labelled as such.

Prompted by the operator, 2026-08-16: *"Review other decisions up to this point
and see if there are any other situations we encountered where a simple change,
addition, or bug fix to upstream cfengine would simplify or make more correct
our work."*

Already in flight, and deliberately not repeated here: `--simulate-keep-chroot`
(PR 1), [`--simulate-json`](cfengine-pr2-simulate-json-report-2026-08-15.md)
(PR 2), and [libntech's silent digest-initialization failure](libntech-pr3-digest-init-filing-package-2026-08-15.md)
(PR 3). Those are the diff/preview path. Everything below is on the two paths
they do not touch: **CMDB/Augments data in**, and **command execution out**.

## Ranked by benefit to this project

Ranking is by what it would do for tendcf, which is what was asked. General
value to CFEngine is noted separately, and for U-1 the two diverge sharply.

| id | What | Fix effort | tendcf benefit | General value |
|---|---|---|---|---|
| U-1 | JSON reals silently truncated to 2 decimals | Small | Low | **High** |
| U-2 | A rejected CMDB file names no key, and one bad key drops every variable | Small (a) / arguable (b) | **High** | High |
| U-3 | `exec_timeout` does not bound a `commands:` promise (filed) | Unknown | **High** | High |
| U-4 | `eval()` returns `%lf` even when the result is integral | Small | Medium | Medium |
| U-5 | Dotted CMDB keys silently become scope paths | Small (warn) | Low | Medium |
| U-6 | No `process_darwin.c`; macOS falls back to the stub | Large | Medium | Medium |

## U-1 — JSON reals are silently truncated to two decimals

The strongest *general* bug found, and the weakest case for tendcf — recorded
that way rather than talked up.

Measured on 3.27.1, reading a data container out of `host_specific.json`:

```
R: IN-CONTAINER tiny=[0.00] pi=[3.14] money=[19.99]
R: VIA-MUSTACHE tiny=0.00 pi=3.14 money=19.99
```

The inputs were `0.00049`, `3.14159265`, `19.99`. **A nonzero value became
zero**, and `pi` lost six digits. `19.99` survives only because it already had
two decimals. The same truncation appears at top level (`--show-vars` shows
`data:variables.pi = 3.14`) and, more seriously, through
`string_mustache` — mustache being the mechanism CFEngine uses to render
configuration files, so this corrupts rendered config, not just reports.

Two hardcoded formats, which disagree with each other:

- `StringFromDouble()` is `"%.2f"` — `libntech/libutils/string_lib.c:922`.
  Reached from `JsonPrimitiveToString` (`json.c:821`), and also from
  `libpromises/rlist.c:1736`, `libpromises/iteration.c:707` and
  `libntech/libutils/mustache.c:399` — so container iteration, JSON-to-slist
  conversion and templating all share it.
- `JsonRealCreate()` is `"%.4f"` — `libntech/libutils/json.c:1664`. This is why
  a container round-trips `3.5` as `3.5000` while a top-level key gives `3.50`.

`JsonRealCreate` also coerces NaN and infinity to `0.0` silently, in the same
function.

**Fix:** a round-trip-safe format (`%.17g`, or shortest-round-trip) in both
places. It lands in **libntech**, the same repository as PR 3, so the process
and the AI-contribution policy are already established.

**Why tendcf gains little.** The goal file admits no floats at all — P-6.6, and
negatives `43-float-timeout`, `48-float-spelling-of-integer`,
`72-float-in-projection` enforce it — so no conforming input can reach this
path. That ban rests on JCS determinism and would not be lifted by a fix. This
is worth filing because it is a real data-corruption bug affecting everyone
else, not because it unblocks us.

## U-2 — A rejected CMDB file names no key, and one bad key drops every variable

**The item with the most direct effect on tendcf's correctness.**

Measured: a `host_specific.json` containing one good key and one value holding
`$(sys.workdir)` produces

```
error: Invalid 'vars' CMDB data, cannot contain variable references
error: Failed to load CMDB data
```

and then **every** variable is gone — the good key included, expanding to the
literal `$(data:variables.good)`. The message names no key, no value, and no
file path.

Two separable asks, and they should be filed separately because one is
uncontroversial and the other is a judgement call:

**(a) Name the offending key.** Trivial and self-contained. The walk is
`JsonWalk(vars, CheckObjectForUnexpandedVars, NULL, CheckPrimitiveForUnexpandedVars, NULL)`
(`libpromises/cmdb.c:180`), and both callbacks already take a `void *data`
parameter that is declared `ARG_UNUSED` (`cmdb.c:70,78`). The carrier for the
offending key exists and is simply unused; the same pattern repeats verbatim at
`cmdb.c:281` for `variables` and `cmdb.c:384` for `classes`.

**(b) Reconsider the blast radius.** One bad key silently disables the host's
entire projected configuration. For a fleet-management tool that is close to
the worst available failure mode: the agent keeps running, reports no promise
failures, and simply behaves as though nothing was ever configured.

**Why this matters here specifically.** E-5 is the measured behaviour that N-4
exists to prevent, and P-4 escalated `@{` from a style rule to a hard negative
precisely because of it. But N-4 guards the *projector*, and the projector is
one of two implementation sites — R22 records that tendcf-agent will be the
other. A defect in the second implementation, or a future kind carrying an
unexpected value, still lands on this behaviour, and (a) is the difference
between a one-line diagnosis and a silent fleet-wide misconfiguration.

## U-3 — `exec_timeout` does not bound a `commands:` promise

Filed today as [`cfengine-exec-timeout-filing-package-2026-08-16.md`](cfengine-exec-timeout-filing-package-2026-08-16.md)
(commit `76f7a8f`). Listed here only so this register is complete: a command
exceeding its timeout is reported as *promise kept*, which inverts the safety
property of an interlock, and firing the timeout adds a fixed ~9.2 s stall.
Mechanism not yet pinned; no patch proposed.

## U-4 — `eval()` returns `%lf` even when the result is integral

Measured on 3.27.1:

```
R: eval(4-1)=[3.000000] eval(2+2)=[4.000000] eval(10/4)=[2.500000]
```

`FnReturnF("%lf", result)` at `libpromises/evalfunction.c:7643`. The same
`"%lf"` is used for `sum`, `product`, `mean` and `variance`
(`evalfunction.c:5886,5890,5894,5912`).

The consequence is that arithmetic cannot be fed to any function taking a
count. `sublist(list, "tail", eval("$(n) - 1", "math", "infix"))` fails with
`Anomalous ending '.0' while parsing integer number: 4.000000`, and the working
form is `format("%d", eval(...))`. This cost real time in this session.

**Fix:** return an integer representation when the result is integral and fits
a long. Small and low-risk.

**Benefit here:** the generic bundle is unwritten and will be full of index
arithmetic over `getindices`/`getvalues` results. This is a papercut that would
otherwise be paid repeatedly, and it is the kind of thing that produces
copy-pasted `format("%d", ...)` wrappers that later readers cannot explain.

## U-5 — Dotted CMDB keys silently become scope paths

Measured: `{"vars": {"com.dotted.key": "v"}}` installs as `data:com.dotted.key`,
scope `com` — not as a variable named `com.dotted.key`. No warning is issued.
An author who writes a dotted flat key gets a variable at an address they did
not write and cannot find.

This is the measurement (E-3) that forced P-2's "entry ids **must** be container
indices, never key components", since every tendcf service id is reverse-DNS.
That decision is right independently — ids are the promiser and the launchd
label, and P-2 also needs containers for type fidelity — so **tendcf is not
blocked by this and should not ask for a behaviour change.** The ask is a
warning on a dotted CMDB key, which is diagnosability only.

## U-6 — No `process_darwin.c`; macOS falls back to the stub

`libpromises/Makefile.am:210–216` selects `process_unix_stub.c` for any platform
that is not Linux, AIX, HP-UX, Solaris or FreeBSD. macOS is therefore on the
stub, where (`process_unix_stub.c:29,38`):

- `GetProcessStartTime()` returns `PROCESS_START_TIME_UNKNOWN` unconditionally.
- `GetProcessState()` distinguishes only "exists" from "does not exist" via
  `kill(pid, 0)`, and can never report `ZOMBIE` or `STOPPED`.

The first has a consequence beyond U-3: `Kill()` falls back to a plain
`kill(2)` whenever the start time is unknown (`process_unix.c:227–236`),
bypassing `SafeKill`'s PID-recycling guard. Every `GracefulTerminate()` caller
on macOS inherits that, including the stale-lock path at
`libpromises/locks.c:630`. The window is narrow and it is not known to have bitten
anything here, so this is recorded as a real gap rather than an incident.

**Effort is the problem.** A genuine `process_darwin.c` means `sysctl`
`KERN_PROC_PID` or `proc_pidinfo` for start time and state. That is a
platform-support contribution, not a bug fix, and it should not be attempted
before U-3's mechanism is understood — U-3 may turn out to be a symptom of
exactly this, in which case the two are one piece of work rather than two.

## What this survey did not find

Worth stating, so the absence is not mistaken for an unfinished search:

- **The argv path is clean.** `commands:` with `arglist` passes elements
  verbatim — spaces, both quote characters, shell metacharacters, empty
  arguments and tabs all survive intact under `useshell => "noshell"`. An
  earlier line of work in this session was heading toward a schema constraint
  to refuse un-renderable argv; measurement showed the constraint was
  unnecessary and no upstream change is wanted here.
- **Hyphens in identifiers are not a bug.** CFEngine rejects `argv_ok-zero` as a
  variable identifier while accepting hyphens as container index keys. That
  asymmetry is ordinary language design, the error message is clear, and R23
  already warns against re-deriving a mechanical justification for the kind-token
  rule. Nothing to file.
- **Interlock semantics otherwise work.** A non-zero `expect_exit` defines its
  class via `kept_returncodes`, a wrong exit code blocks, and a command with no
  children is terminated on time. U-3 is a specific defect, not a broken
  mechanism.

## Suggested order

1. **U-2(a)** — smallest diff, highest correctness return here, and it stands
   alone without needing U-2(b) settled.
2. **U-1** — small, high general value, lands in libntech where PR 3 already
   established the process.
3. **U-4** — small, and paid back immediately once the generic bundle is written.
4. **U-3** — needs the instrumented build first; do not patch before the ~9.2 s
   is explained.
5. **U-6** — only after U-3, and possibly as the same piece of work.
6. **U-5** — file whenever convenient; nothing here depends on it.

## Coverage, and where to resume

This batch is **not** an exhaustive audit, and the boundary is recorded here so
a later pass extends the sweep instead of repeating it.

**Swept, with fresh measurement on 3.27.1:**

- The CMDB/Augments load path — `libpromises/cmdb.c` end to end: key parsing,
  type handling, the unexpanded-variable rejection, container vs top-level
  placement. Produced U-1, U-2, U-5.
- The command execution path — `commands:` promises with `arglist`, `args`,
  `body contain` (`useshell`, `exec_timeout`) and `body classes`
  (`kept_returncodes`, `promise_kept`, `scope`). Produced U-3, and the three
  negative findings above.
- `eval()` and the arithmetic family. Produced U-4.

**Re-measured from the E-series:** E-3 (dotted keys), E-4 (top-level
stringification), E-5 (load blast radius), E-8 (float laundering). All four
confirmed as recorded.

**Carried unverified — not re-measured this pass**, and therefore not proposed:
E-1 (`data:variables.<key>`, `source=cmdb`), E-2 (`$(def.<key>)` does not
expand), E-6 (illegal top-level keys warn-and-skip), E-7 (`variables` overwrites
`vars`), E-9 (the 5 MiB `HOST_SPECIFIC_DATA_MAX_SIZE` hard failure). E-9 in
particular is a plausible U-candidate — a hard load failure on a size limit has
the same silent-total-loss shape as U-2 — and is the first thing to measure next.

**Never swept at all.** These are where the next batch should look, roughly in
the order the build will need them:

- **`services:` promises**, and the launchd/systemd/Termux service abstraction.
  The generic bundle's largest unwritten surface, and the premortem's N15 names
  the thin macOS corpus as a top risk. Nothing here has been exercised once.
- **`files:` promises** — templating (`template_method => "mustache"` is already
  implicated by U-1), `edit_line`, permissions, and the `unit-writer` render
  path.
- **Locking and scheduling** — `ifelapsed`, `expireafter`, the lock database,
  and `GracefulTerminate`'s stale-lock caller named in U-6.
- **`packages:` promises.** Cut from v1 by §8, so not urgent, but R1 watches for
  their return and the privileged promiser list regrows with them.
- **Non-macOS platforms.** Every measurement in this document is arm64 macOS.
  The fleet is also Linux (x86_64 and aarch64) and Android via Termux, and U-6
  establishes that the platform split is load-bearing — Linux takes a different
  `process_*.c` entirely, so U-3 may not even reproduce there.
- **`--simulate` correctness** beyond PR 2's JSON rendering, which added an
  output format without auditing what it reports.
