# UPSTREAM REVIEW BRIEF — P-1 and P-2, `--simulate` features in cfengine/core

**Frozen input, 2026-08-17.** Given verbatim to each panel member. Do not edit
it to reflect what the reviews find.

## Why you are being asked, and what is unusual about it

These two changes are **already open on upstream `cfengine/core`** and have
been since 2026-08-15. They are the only items in this body of work that
reached maintainers **without any review at all**. Every other item was
panelled, and every panel found real defects — including a false claim sitting
in a live upstream PR, and seven problems in a patch series its author was
confident about.

So this is not a pre-flight check. It is a **post-flight audit of code already
in front of maintainers**. If you find something, the correction is public and
costs credibility, which is exactly why it is worth finding now rather than
having a maintainer find it.

| | PR | discussion | branch | worktree (pre-built) |
|---|---|---|---|---|
| P-1 | [cfengine/core#6293](https://github.com/cfengine/core/pull/6293) | [#6295](https://github.com/cfengine/core/discussions/6295) | `simulate-keep-chroot` @ `64e2ac1cb` | `/Users/djbclark/src/core-p1` |
| P-2 | [cfengine/core#6294](https://github.com/cfengine/core/pull/6294) | [#6296](https://github.com/cfengine/core/discussions/6296) | `simulate-json` @ `05e18f038` | `/Users/djbclark/src/core-p2` |

Base for both is upstream `master`. `origin` is `djbclark/core` (our fork);
`upstream` is `cfengine/core`.

## Your role

You are an independent adversarial reviewer. Assume both changes are wrong and
try to demonstrate it. Finding nothing is a valid outcome, but only after a
real attempt. **Prefer measurement to reasoning from the source.**

**Write nothing except your own output file. Do not commit, push, branch, or
modify any file in any repository.**

## What the two changes are

**P-1 — `--simulate-keep-chroot=PATH`** (183 insertions; `cf-agent/cf-agent.c`,
`libpromises/generic_agent.c`, plus acceptance tests). A `--simulate` run builds
a "changes chroot" — a tree of the files as they *would* be after the run,
including permission-mirrored copies of real system files — and normally
deletes it on exit. This option puts it at an operator-chosen path and keeps it.
The path must be absolute and must not already exist; it is created with
`mkdir(keep_chroot, 0700)`.

**P-2 — `--simulate-json`** (1165 insertions; 454 changed lines in
`cf-agent/simulate_mode.c`, a new 459-line `tests/unit/simulate_mode_test.c`,
plus acceptance tests). Writes the simulated change set as JSON instead of only
as prose meant for human eyes.

## Questions — answer by number

1. **P-1: is the chroot creation actually safe?** It holds copies of
   potentially sensitive system files with their permissions mirrored. Consider
   at least: `mkdir`'s mode versus the process umask; whether the *parent*
   directory's permissions matter and whether a hostile or group-writable
   parent changes anything; symlinks and TOCTOU between check and create; what
   happens if `PATH` is longer than `PATH_MAX` given `strlcpy()` truncates
   silently, and whether a truncated path can diverge from the directory
   actually created. Is `0700` the right mode, and is it enough?
2. **P-1: is the absolute-path requirement enforced where the commit says?**
   Find the check. Is it correct for every input — trailing slashes, `..`
   components, a path that is absolute but inside a symlinked parent?
3. **P-1: what happens on failure paths?** `FatalError()` on `mkdir` failure —
   is that the right response, and does it leak anything about the filesystem
   to an unprivileged caller? Is the cleanup-function swap
   (`KeepChangesChroot` vs `DeleteChangesChroot`) correct in every exit path,
   including early failure, signals, and `--dry-run`-style aborts? Can the
   chroot ever be deleted when it should be kept, or kept when it should be
   deleted?
4. **P-2: is the JSON output correct and safe?** It is machine-readable output
   of filenames and change data. Check escaping and encoding of hostile
   filenames (newlines, quotes, invalid UTF-8, control characters), and whether
   anything can produce malformed JSON. Note that this repository has a
   **separate, active defect family around JSON number handling** — if any
   number reaches this output through libntech's JSON writer, say so.
5. **P-2: 454 changed lines in `simulate_mode.c` is a large rewrite of existing
   behaviour.** Does the **non-JSON** path still behave exactly as before?
   That is the regression risk that matters most: every existing `--simulate`
   user is on that path. Demonstrate it rather than assert it.
6. **Memory, ownership and lifetime** in both changes. Leaks, double frees,
   use-after-free, unchecked allocations. P-2's `config->agent_specific` string
   handling and P-1's global `KEEP_CHANGES_CHROOT` buffer specifically.
7. **Are the tests any good?** P-1 ships **acceptance tests only, no unit
   test**; P-2 ships both. For each, would the test actually fail against the
   code without the change? A test that passes either way is decoration — this
   exact defect was found in another patch in this work, where two of three
   cases asserted pre-existing behaviour and so passed unfixed.
8. **What would a maintainer push back on?** `CONTRIBUTING.md` style, log
   levels, commit hygiene, option naming, documentation. Both commits now carry
   `Changelog: Title` and `Ticket: #6295`/`#6296`, which reference upstream
   **Discussions** (that repository has issues disabled). Is that the right
   trailer usage? Is anything in either commit message or PR body **false** —
   that is the specific failure mode already caught twice in this work.

## Build and test

Both worktrees are **already configured and built** against **stock libntech
`5b5d04e1`** (verified clean, not our patched submodule).

```sh
cd /Users/djbclark/src/core-p1     # or core-p2
make -j2                           # the machine is busy; do not exceed -j2
cd tests/unit && make check
```

Measured baselines, `rc=0` on both:

| tree | result |
|---|---|
| `core-p1` | `All 68 tests behaved as expected (4 expected failures)` |
| `core-p2` | `All 69 tests behaved as expected (4 expected failures)` — 69 because P-2 adds `simulate_mode_test` |

**Three reviewers are working concurrently.** `core-p1` and `core-p2` are
shared. Do **not** run `make` in a shared tree while experimenting — for any
before/after measurement, copy what you need to your own directory under
`/tmp` and build there, or you will corrupt another reviewer's results and your
own.

Do **not** build or modify `/Users/djbclark/src/cfengine-core` — other work
uses that checkout and its libntech submodule must stay uncommitted.

## Build traps that have each already produced a false verification here

State explicitly how you controlled for these if you assert a before/after
difference.

1. **`make check` inside `tests/unit` does not rebuild the libraries above it.**
   A test binary silently links whatever archive was last built.
2. **`make -C tests/unit <test>` does not relink** on a changed archive. `rm -f`
   the binary to force it.
3. **`git stash push <file>` stashes nothing once the file is committed.** Use
   `git show <sha>:<path>` into a scratch directory instead.
4. **Binaries copied out of `.libs/` link the *installed* dylib** at the
   configure prefix (`/Users/djbclark/opt/cfengine-dev`), not the build tree.
   `otool -L` whatever you are about to measure with. Also, `cf-agent` spawns
   `cf-promises` as a child and macOS strips `DYLD_*` across that exec.
5. **`tests/unit/rlist_test` is XFAIL on macOS and aborts at its sixth test**,
   so anything registered after `test_rval_to_scalar2` never runs. A test
   appended to the end of that file passes vacuously. Check whether any test
   you are assessing sits after an aborting one.

## Deliverable

Write **one file**:
`/Users/djbclark/src/tendcf/docs/architecture/upstream-opinion-p1p2-<slug>-2026-08-17.md`
with `<slug>` from your launch prompt.

1. **Verdict, separately for P-1 and P-2** — *leave as is*, *push a correction*
   (list exactly what), or *withdraw*.
2. **Defects found**, each with file and line, what breaks, how to reproduce.
   Mark each **verified** (you ran it) or **suspected** (you reasoned it).
3. **The eight questions**, answered by number.
4. **How you controlled for the traps**, for every before/after claim.
5. **What you did not check.**

**Independence:** do not read any other `upstream-opinion-*.md` file, and do not
read `docs/handoffs/` or `docs/architecture/upstream-register.md`.
