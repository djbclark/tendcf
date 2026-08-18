---
schema_version: 1
handoff_id: a6e1
parent_handoff_ids: [92bb]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: dbe6b800ec9faf2fb8ccb0a27f8b8e2ebbcb21d4
created_at: 2026-08-18T15:42:00-0400
writer: claude-code
---

# Handoff — B-3 shipped, then everything unshared went out as PRs, then the test gaps closed

## The Goal

Resume the CFEngine upstream work from `92bb` and ship the next item (B-3 /
CFE-4718, no `process_darwin.c` on macOS).

Two larger goals emerged mid-session from operator direction and displaced the
original plan of moving straight on to B-5a/B-5b:

1. **Share everything already coded.** The operator questioned why finished
   code was sitting on fork branches, then issued a **standing order: "when in
   doubt, open a PR and/or issue."**
2. **Close the test gaps**, explicitly because "the number of issues makes
   [regressions] hard to track."

## Where We Are

`tendcf` `master` @ `dbe6b800ec9faf2fb8ccb0a27f8b8e2ebbcb21d4`, **clean tree**,
pushed. Nothing in flight, nothing uncommitted.

**14 PRs now open on `cfengine/core`, 3 on `NorthernTechHQ/libntech`.** Eight
of the core PRs were opened this session:

| PR | item | ticket | notes |
|---|---|---|---|
| [#6307](https://github.com/cfengine/core/pull/6307) | B-3 | CFE-4718 | `process_darwin.c`, shipped this session end to end |
| [#6308](https://github.com/cfengine/core/pull/6308) | B-15 | CFE-4732 | **the one PR with no test** — documented, see below |
| [#6309](https://github.com/cfengine/core/pull/6309) | B-16 | CFE-4733 | |
| [#6310](https://github.com/cfengine/core/pull/6310) | B-17 | CFE-4727 | stacked on #6305 |
| [#6311](https://github.com/cfengine/core/pull/6311) | B-18 | CFE-4734 | stacked on #6305 |
| [#6312](https://github.com/cfengine/core/pull/6312) | B-19 | CFE-4735 | stacked on #6310 |
| [#6313](https://github.com/cfengine/core/pull/6313) | getopt audit | **CFE-4736 (new)** | 12 commits + regression test |
| [#6314](https://github.com/cfengine/core/pull/6314) | core JSON numbers | **CFE-4737 (new)** | was wrongly believed blocked |

Pre-existing and untouched: #6293, #6294, #6299, #6300, #6302, #6305 (core);
#291, #293, #294 (libntech).

**Nothing is known-blocked upstream any more.** The only item previously marked
blocked turned out not to be — see "What We Tried" item 7.

Worktrees created this session, delete when their PRs close:
`~/src/core-darwin` (`fix/process-darwin`), `~/src/core-getopt`
(`pr-getopt-optstring-fixes`), `~/src/core-jsontest`
(`fix/json-number-rendering-master`).

## What We Tried

Chronological. The failures are the expensive part — several of these produced
*confident wrong answers* rather than errors.

**1. `grok` CLI with a piped prompt — silent failure, exit 0.**
`grok --model grok-4.6 < prompt.md` dies with `Error: Device not configured
(os error 6)` — it wants a TTY. It **exits 0**, so a backgrounded run looks
successful until you notice the output is ~500 bytes of nothing. Working form:
`grok --model grok-4.6 --always-approve -p "$(cat prompt.md)"`. (`gemini` is
the opposite: it takes stdin but needs `--dangerously-skip-permissions` or it
silently auto-denies tool calls.) Saved as auto-memory
`grok-cli-needs-p-flag-not-stdin`.

**2. The stale-library trap, in a nastier form than the one already in memory.**
Proving B-3's discrimination meant building with the stub. After reverting
`libpromises/Makefile.am`, `make` in `libpromises/` printed
`Nothing to be done for 'all-am'` and exited 0 — while `libpromises.la` still
contained the **stub** object. The generated `Makefile` was correct; the
archive was not, because the archive was newer than the object it should now
contain. This disguise is much better than the plain stale case, because
everything you would naturally check looks right. Required:

```
rm -f <plat>.lo libpromises.la && rm -rf .libs/libpromises* && make
```

Note also that `tests/unit/<x>_test` is a **libtool wrapper script**; the real
binary's recorded dylib path is the *install* prefix, which may not exist.
Verify with `otool -L tests/unit/.libs/<x>_test`. Existing auto-memory
`libpromises-edit-needs-library-rebuild` was updated with this sharper form.

**3. `proc_pidinfo()` as the Darwin process API — rejected on evidence.**
Probed it directly rather than reasoning about it. It fails `EPERM` for
processes owned by another user when unprivileged (pid 1 → "Operation not
permitted" as uid 501), and reports an **unreaped zombie as `ESRCH`**. The
latter is fatal: it cannot express `PROCESS_STATE_ZOMBIE`, which is half of
what CFE-4718 asks for.

**4. Transcribing `process_freebsd.c`'s success test verbatim — would have
shipped a regression.** On Darwin, `sysctl KERN_PROC_PID` for a **nonexistent
pid succeeds** (`rc=0`) and returns `len=0`, leaving the buffer untouched — it
does *not* fail with `ESRCH` as other BSDs do. FreeBSD's
`if (sysctl(...) == 0)` alone would parse an unwritten `kinfo_proc`, and grok
confirmed by poisoning the buffer with `0xAB` that the poison survives, so
`p_stat` is not even reliably 0. A dead process would have read as running
forever — strictly worse than the stub being replaced.

**5. gemini's `len < sizeof(psinfo)` suggestion — declined after analysis.**
Superficially free hardening. But a binary built against a newer SDK running on
an older kernel with a smaller struct would then reject **every** process,
failing toward `DOES_NOT_EXIST` — and grok demonstrated that direction is *not*
fail-closed, because `ProcessWaitUntilExited()` treats `DOES_NOT_EXIST` as
**success** (`process_unix.c:96`), so `GracefulTerminate()` would claim victory
after only a SIGINT. Took the zero-risk half instead: `memset` before the call,
which removes the uninitialised-read objection without changing behaviour.

**6. The getopt checker was wrong three times before it was trustworthy.**
This is the single most instructive sequence in the session.

- *Python audit, v1:* paired option strings to tables per **file**. Reported
  `cf-net`'s `-o/--output` and `-j/--jobs` as missing. False — they live in
  subcommand-local tables at `cf-net.c:805,1187` with their own option strings
  `"o:j:"` and `"o:"`. Fixing that "bug" would have been an embarrassing
  upstream regression.
- *Python audit, v2:* resolved the option-string variable to the **first**
  definition in the file rather than the nearest preceding one. Same class of
  false positive.
- *Shell/awk test, v1:* merged two tables **sharing the name `longopts`**.
  Caught on its first run against our own (fixed) branch.
- *Shell/awk test, v2:* **silently skipped most files** and looked healthy,
  reporting 6 of 10 known faults. Two parser bugs: `cf-testd`'s table ends
  `{NULL, 0, 0, '\0'}};` on one line, so the "table ends at `};`" rule never
  fired and table-mode swallowed the `getopt_long` call entirely; and
  `cf-execd`'s wrapped call has a trailing comma, so `split(...)>=4` was
  satisfied by an **empty** 4th field and the table could not be resolved.

The lasting fix for the *class*: the test now **exits 2** if a file calls
`getopt_long()` but yields no usable call site, so a degraded parser can never
pass quietly. Verified by renaming a table so the parser could not find it.

**7. Believing `fix/json-number-rendering` was blocked — wrong, and never
tested.** I marked it blocked on libntech#294 because it had been *developed*
against an unmerged libntech commit (`5b5d04e19`), and inferred a build
dependency. **"Developed against X" is not "requires X."**
`JsonPrimitiveGetAsString()` already exists on libntech master
(`libutils/json.h:246`), which already creates primitives from the parsed text
buffer (`json.c:2377`). Rebased onto master → submodule pointer matches
master's `0c0620d` exactly, diff is 5 source files with **no** submodule
change, builds clean, and the fix's own test passes. Shipped as #6314.

**8. "The nfs.c family isn't testable" — overstated.** `nfs_test` does exist
(`tests/unit/Makefile.am:421`). It covers only pure string helpers
(`MountOptionsFromLine()`, `OptionsSubsetMatches()`, `GetFstabEntryOptions()`)
and never touches alarms. The accurate claim is that *this function* is out of
reach, not the file.

**9. Suspected the remount branch ignores `DONTDO` — checked first, wrong.**
Was about to report it as a new bug. `ReconcileMountOptions()` is gated at
`nfs.c:1399` by `MakingInternalChanges()`, which returns early on a dry run.
No bug. (This *also* confirms the fix is unreachable from a unit test: under
`DONTDO` it returns before the arm/disarm code; without it, real mount
commands run.)

**10. Standalone timing harness failed to compile** until `-DHAVE_CONFIG_H` was
added — `platform.h` only includes `config.h` under that guard, so without it
you get a cascade of `unknown type name` errors that look like missing headers.

## Key Decisions

**Chosen:**

- `sysctl KERN_PROC_PID` for Darwin, modelled on `process_freebsd.c`, **plus an
  explicit length check** for the Darwin-only nonexistent-pid behaviour.
- **No `darwin_process_test.c`.** The `linux`/`aix`/`solaris` per-platform tests
  interpose `open`/`read` to feed synthetic `/proc`-style *text*; Darwin has no
  parsing to test, and faking `sysctl()` would only test our own `switch`
  against a struct we filled. FreeBSD likewise has no per-platform test.
- **Remove `process_test` from the macOS `XFAIL_TESTS`** — not optional. Once
  it passes, leaving it listed makes `make check` fail with XPASS.
- **Open the stacked PRs now**, with each body naming the single new commit and
  its dependency, rather than waiting for #6305 to merge.
- **Shell + awk for the getopt test, not python.** CFEngine targets
  AIX/Solaris/HP-UX and all three existing `check_SCRIPTS` are shell.
- **Do not manufacture a test for #6308.** A test that does not reach the fix
  is worse than none — it is precisely the false confidence the operator was
  asking about. Documented the blocker and the seam instead.

**Rejected:**

- `proc_pidinfo()` (item 3 above).
- `len < sizeof(psinfo)` (item 5).
- Patching `cf-agent`'s `-x/--self-diagnostics` and `cf-check`'s `-h/--help`.
  Both declare `optional_argument` against a bare character, but **neither
  handler reads `optarg`** (`cf-check.c:166`, `cf-agent.c:649` print and exit),
  so the *table* is the wrong side and the mechanical option-string fix would
  advertise an argument that is silently discarded. Both reconciliations are
  user-visible → raised as RFC questions in CFE-4736 instead.
- Adding `--manpage` universally. `-M` is handled in 9 of 10 binaries but only
  `cf-check`, `cf-net`, `cf-secret` declare the long form. Adding it is a
  behaviour *addition*, not a bug fix → also an RFC question.
- Restructuring `ReconcileMountOptions()` for testability inside a nine-line
  bug-fix PR. Offered, not done.

## Evidence & Data

**B-3 / CFE-4718 discrimination** (forced relink both ways):

| | `process_test` |
|---|---|
| stub | **4 FAIL, exit 1** — `process_test.c:91,92` (start time), `:149` (STOPPED), `:216` (ZOMBIE) |
| `process_darwin.c` | **0 FAIL, exit 0** |

`make check` in `tests/unit`: **66 PASS, 3 XFAIL, 1 SKIP, 0 FAIL, 0 XPASS**
(baseline 65/4). Stability: 12 serial + 8 concurrent runs, no flake.
Compiles clean under `-Werror -Wall -Wextra`.

**Cost of the B-3 defect** — `GracefulTerminate()` on an unreaped child:

| build | runs |
|---|---|
| stub | 7154 / 6884 / 7336 ms (grok measured ~12.5 s under its own load) |
| `process_darwin.c` | 16.5 / 49.9 / 0.7 ms |

Figure is host- and load-dependent (a 10 ms `nanosleep()` overshoots to
~35–77 ms here), so the commit says "several seconds", not "7.0 s".

**Darwin `sysctl KERN_PROC_PID`, uid 501, macOS 26.6.1 / Darwin 25.6.0, arm64,
`sizeof(struct kinfo_proc)` = 648** (same on the 15.0, 15.4, 26.0, 26.5 SDKs):
self/pid 1/running/SIGSTOP'd/zombie all `rc=0 len=648`; reaped and nonexistent
`rc=0 len=0`. Undersized buffer → `-1/ENOMEM` (not a partial read).

**getopt audit** — 10 faults on unpatched master across `cf-check`, `cf-net`,
`cf-secret`, `cf-testd`, `cf-serverd`, `cf-execd`, `cf-promises`. Functional
proof after fix: `cf-check -V` prints the version (was "unrecognized option"),
`cf-secret -v` enables verbose, `cf-testd -r` now correctly *demands* its
argument. `PASS: getopt_optstring_test.sh`, all 68 tests behaved as expected.

**Test-coverage audit: 16 of 17 branches ship tests** (15 before this session's
getopt test). Sole gap: #6308. The operator caught an arithmetic error here —
I reported 15/17 after closing a gap that made it 16/17; corrected in
`upstream-register.md` at the source, not just in conversation.

**Files created this session** (all committed and pushed):
`docs/architecture/UPSTREAM-CFE4718-REVIEW-BRIEF.md` (+ a post-freeze
corrections section), `upstream-opinion-cfe4718-grok-4.6-2026-08-18.md`,
`upstream-opinion-cfe4718-gemini-3.1-pro-2026-08-18.md`, and three appended
sections in `docs/architecture/upstream-register.md` (PR-sharing sweep, getopt
resolution, test-coverage audit).

**Panel outcome, CFE-4718** — grok-4.6 and gemini-3.1-pro-high, both SHIP, **no
required code changes**; required changes were to the commit message and were
applied. Per `[[panel-reviewer-weighting]]`, grok was much the deeper seat: it
force-relinked and ran `make check` itself, compiled under CI's `-Werror`,
censused 758 processes, and **found the impact the ticket, my brief and gemini
all missed** — custom promise modules cannot load on macOS at all, because
`mod_custom.c:504` fails the module when `GetProcessStartTime()` is unknown,
which on the stub is unconditional. Verified independently before it went
upstream. grok also refuted gemini's "ENOMEM fails closed" claim.

## Operator Feedback

- **Standing order: "when in doubt, open a PR and/or issue."** Finished code on
  a fork branch is not shared. Saved as auto-memory
  `when-in-doubt-open-pr-or-issue`. It supersedes the wait-for-instruction half
  of `[[upstream-artifacts-need-approval]]`; it does **not** cancel
  `[[upstream-email-wait-for-full-panel]]`.
- **Upstream understands the operator is not able to be hands-on himself and
  accepts the multi-AI vetting process.** So AI involvement was never the
  objection on the orphaned branch — only the **author field**.
- **Re-attribute to `Daniel Joseph Barnhart Clark <djbclark@gmail.com>`** (full
  name, not the `Daniel JB Clark` in git config).
- **"Def flush out the one before posting it"** — complete the audit rather
  than post a partial fix. This directly caused finding the two remaining
  duplicates *and* the two RFC items.
- **"We don't want regressions esp. as the number of issues makes them hard to
  track"** — the rationale for a class-killing test over a one-off.
- Caught my 15-vs-16 coverage arithmetic. He is checking the numbers.

## Where We're Going

1. **NEXT ACTION: start B-5a (issue #8) and B-5b (#9).** Both are CMDB
   error-reporting and may pair into one brief. Then B-6 (#10), B-7 (#11). See
   the rows in `docs/architecture/upstream-register.md`.
2. **Watch CI on the eight new PRs**, #6307 above all — upstream's macOS job
   builds with `MACOSX_DEPLOYMENT_TARGET=15.4` and runs `process_test` on a
   macOS other than this box, which is the one B-3 claim not testable locally.
3. **Watch CFE-4736** for a decision on the two RFC questions (`cf-agent -x`,
   `cf-check -h`, and whether `--manpage` should be universal). One-line change
   either way once upstream picks.
4. **Re-check `djbclark/core#7`'s premise** for any other branch it claims to
   cover — its "built against an unmerged libntech commit" assumption just
   failed for the one branch actually tested. Method: rebase onto
   `upstream/master`, confirm the submodule pointer matches, build.
5. If upstream asks for coverage on #6308, add the seam described in CFE-4732
   comment 159443 (lift arm/act/disarm into a helper taking the built command,
   assert `alarm(0) == 0`).
6. Delete `~/src/core-darwin`, `~/src/core-getopt`, `~/src/core-jsontest` when
   their PRs close.

## Quick Start

```bash
# Tier 1 first
cat ~/.local/state/handoffs/chains/standalone-3fd9/SESSION_LOG.md

# Quota BEFORE any panel work -- numbers are CONSUMED, not remaining
cswap list          # "5h: 93%" means 7% LEFT. Fable was ~93% used, resets 2026-08-21.

# CI on this session's PRs
for n in 6307 6308 6309 6310 6311 6312 6313 6314; do
  echo "== $n =="; gh pr checks $n -R cfengine/core 2>&1 | head -5
done

# Maintainer recheck
gh pr view 6305 -R cfengine/core --json reviews --jq '.reviews[-1]'
gh pr view 294 -R NorthernTechHQ/libntech --json comments --jq '.comments[-1]'

# Jira (token via sudo-secretspec, never inline)
TOKEN=$(sudo-secretspec get ATLASSIAN_CFENGINE_API_TOKEN --reason "<why>")
curl -sS -u "djbclark@gmail.com:$TOKEN" \
  "https://northerntech.atlassian.net/rest/api/2/issue/CFE-4736?fields=summary,status,comment" | python3 -m json.tool

# Next work item
gh issue view 8 -R djbclark/core     # B-5a
gh issue view 9 -R djbclark/core     # B-5b

# New worktree for it (submodules are NOT automatic)
cd ~/src/core-alarmreset && git fetch upstream master
git worktree add -b fix/<slug> ~/src/core-<slug> upstream/master
cd ~/src/core-<slug> && git submodule update --init

# Panel dispatch -- grok CANNOT take stdin
grok --model grok-4.6 --always-approve -p "$(cat prompt.md)"
gemini --model gemini-3.1-pro-high --dangerously-skip-permissions < prompt.md

# Rebuilding libpromises after a SOURCE-LIST change: 'make' lies (exit 0,
# "Nothing to be done") while the archive keeps the old object. Force it:
cd <worktree>/libpromises && rm -f <plat>.lo libpromises.la && rm -rf .libs/libpromises* && make
otool -L ../tests/unit/.libs/<x>_test   # confirm what actually linked

# testall exits 0 even when every test fails -- read the passed count.
```
