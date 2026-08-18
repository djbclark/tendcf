---
schema_version: 1
handoff_id: be6d
parent_handoff_ids: [a6e1]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: d8086302454daf8732cd3ecc00a9b290b35bfa2a
created_at: 2026-08-18T16:47:12-0400
writer: claude-code
---

# Handoff — four PRs shipped, and a reviewer that rewrote the code it reviewed

## The Goal

Resume chain `standalone-3fd9` from handoff a6e1 and continue the unstarted
upstream batch: B-5a (CFE-4719), B-5b (CFE-4720), B-6 (CFE-4721), B-7
(CFE-4722). Two other next-steps from a6e1 — watching CI on PRs #6307–#6314
and waiting on CFE-4736's RFC questions — turned out to be dead ends and are
recorded as such below.

Mid-session the operator added: *"do all the work you can, remember you can
farm things out to do them in parallel"*, which authorised subagents.

## Where We Are

`tendcf@d808630`, branch `master`, working tree **clean**. Everything below is
pushed.

**Four PRs opened, all OPEN + MERGEABLE, each with a Jira comment:**

| PR | Ticket | Branch (fork `djbclark/core`) | Head |
|---|---|---|---|
| [#6315](https://github.com/cfengine/core/pull/6315) | CFE-4719 | `fix/cmdb-name-offending-key` | `958d13949` |
| [#6316](https://github.com/cfengine/core/pull/6316) | CFE-4738 | `fix/cmdb-null-value-crash` | `87490bb8f` |
| [#6317](https://github.com/cfengine/core/pull/6317) | CFE-4722 | `fix/cmdb-dotted-key-warning` | `ee1f9d60c` |
| [#6318](https://github.com/cfengine/core/pull/6318) | CFE-4721 | `fix/eval-integral-result` | `b74e8f4cf` |

All four cut from upstream master `a0bca6aaf`. Register rows updated for
B-5a/B-6/B-7 and new rows added for B-20/B-21.

**Two new tickets filed for defects found while testing** (neither existed at
session start):

- **CFE-4738** — a JSON `null` in `host_specific.json` segfaults
  `cf-promises`/`cf-agent`. Fixed and PR'd as #6316.
- **CFE-4739** — the *same* root cause in the augments (`def.json`) loader,
  three sites in `libpromises/generic_agent.c`. **Not started.**

Files changed in this repo this session: `docs/architecture/upstream-register.md`
(commits `f669531`, `d808630`) and this handoff. All upstream code lives in the
four `core-*` worktrees, not here.

## What We Tried

Failed approaches and dead ends, chronological — the expensive part to
rediscover.

1. **Watching CI on #6307–#6314 (a6e1's "next action") is impossible.** Every
   real workflow run sits at `action_required`, 0s duration; only
   `license/cla` executes. Upstream requires a maintainer to approve workflows
   for a first-time contributor. The macOS verification for #6307 that a6e1
   called "matters most" **cannot happen by waiting**. All 12 open PRs have
   zero comments and zero reviews.

2. **First panel run was contaminated and had to be thrown away.** I ran
   `gemini --dangerously-skip-permissions` with cwd *inside* the B-5a
   worktree. It did not just review — it **rewrote `libpromises/cmdb.c`** on
   top of a commit already built and acceptance-tested. `grok --always-approve`
   was running concurrently in the same directory. Discarded both, restored
   from the commit, re-ran on disposable `cp -a` copies.

3. **grok stalled twice, and I killed it prematurely the first time.** Both
   stalls (~400 bytes, 12+ min, no growth) happened while gemini was rewriting
   files in the same directory. On an isolated copy it completed normally
   (12.5 KB, thorough). A later probe in the same previously-stalling worktree
   returned in **6.6 s**, so the directory is not cursed and there is no stale
   lock (`~/.grok/active_sessions.json` is `[]`). grok does keep per-directory
   sessions with a lock, so same-directory concurrency is the plausible
   mechanism — but **n=2, correlation not proof**. Do not assert it as fact.
   Also: `grok --debug` needs `--debug-file`, not `--log-file`.

4. **`--gainroot=sudo` died silently mid-session.** The sudo credential cache
   expired (`timestamp_timeout=5`, five minutes). `testall` then exits **144
   with no output at all**, which reads as a hang rather than a failure. Cost
   two confusing runs before diagnosis.

5. **`--gainroot=env` was a bad substitute, and it corrupted a number I
   published.** It cannot delete root-owned files left by earlier sudo runs, so
   the workdir stayed dirty and `testall` counted stale entries: a branch with
   13 test files reported "17 passed". That 17 reached **PR #6315's body and
   the CFE-4719 Jira comment** before being caught. Corrected (PR body edited,
   Jira comment 159448). It also makes root-requiring tests *fail* rather than
   skip.

6. **fakeroot does not rescue the root-requiring tests.** Installed it and
   measured: `fakeroot id -u` returns **501, not 0** — its uid faking is broken
   by SIP, because it works via `DYLD_INSERT_LIBRARIES` and macOS strips
   `DYLD_*` when spawning protected binaries like `/bin/sh`. `getgroups`,
   `getgroupinfo`, `getusers_vararg`, `filestat_xattr` fail under it exactly as
   under `env`. It IS still the right default for everything else.

7. **My first B-5a design named the wrong thing, caught before commit.**
   Recording the offending primitive's own property name reports the metadata
   key `value` in the CFE-3633 `variables` format, and `NULL` for an array
   element. Restructured to walk each top-level entry separately.

8. **My first B-5a acceptance test did not test the design decision** — found
   by grok on the clean re-run. The fixture was a bare `vars` string whose
   primitive property name *is* the entry name, so folding the walk back into
   one section walk would still have passed it. Proved the gap by *building*
   the regression: test 12 passes under it, new test 15 fails.

9. **A parallel subagent's worktree was overwritten by another agent's
   branch content** (`core-cmdbnull/libpromises/cmdb.c` briefly held
   `fix/cmdb-dotted-key-warning` code). The owning agent caught it, reset to
   pristine upstream, re-applied only its own change. All four branches
   verified isolated before pushing.

## Key Decisions

**Chosen:**

- **Walk each top-level CMDB entry separately** rather than the section as a
  whole, so the *entry* an operator edits is named in every case. Costs a
  slightly larger diff; the alternative cannot name the variable in the
  CFE-3633 format at all.
- **Two acceptance tests for B-5a**, not one, because a single test provably
  fails to lock the design (see What We Tried #8).
- **Skip-with-error, not reject-the-section, for the null fix (B-20).**
  Verified against the file's own idiom: `cmdb.c` already `continue`s for every
  per-entry problem and reserves `return false` for section-level structural
  faults.
- **Two log levels for the dotted-key warning (B-7)** — VERBOSE for the
  documented `[namespace:]bundle.variable` form (indistinguishable from
  deliberate scope qualification), WARNING only for shapes that form cannot
  express. A warning every run on a working config would get the patch
  rejected.
- **Panels now run on disposable `cp -a` copies**, never the build tree, never
  two seats in one directory, with `git status` on the real worktree after.
- **`--gainroot=fakeroot` + a fresh `BASE_WORKDIR`** is the standing test
  recipe.
- **Corrected the "17 tests" claim publicly** rather than quietly editing it.

**Rejected:**

- **A NOPASSWD sudoers rule for the test suite** — operator asked directly.
  `testall:514` is `$GAINROOT "$WORKDIR/runtest"` and that path is inside the
  checkout, **writable by the user**, so a NOPASSWD rule on it is
  `NOPASSWD: ALL` in practice. Not theoretical: reviewer CLIs and subagents
  demonstrably edit files in these worktrees unprompted, and this box holds the
  Atlassian token and the secretspec broker. Contrast the existing
  `sudo-secretspec` rule, safe because its target is a fixed root-owned binary.
  Real fix for the prompting is `timestamp_timeout`, not NOPASSWD.
- **Changing `sum`/`product`/`mean`/`variance` in B-6** — all four are declared
  `CF_DATA_TYPE_REAL` and policy assigns them to `real =>` variables, so a real
  number is their documented contract. `eval` is `CF_DATA_TYPE_STRING`.
- **gemini's deletion of a pre-existing upstream comment** — gratuitous churn
  in a diff going to maintainers. Its other two edits were taken on merit.
- **Fixing CFE-4739 inside #6316** — different file, feature, and test
  directory.
- **Folding B-5b into B-5a** — B-5b is a behaviour change, B-5a is
  diagnosability. They were deliberately filed separately.

## Evidence & Data

**B-5a message shapes, all six verified on the final build:**

```
vars bad value       (offending value in entry 'key_with_unresolved_value': '$(sys.workdir)')
vars bad key         (offending key: 'key_$(with).a.ref')
variables metadata   (offending value in entry 'my_variable': '$(sys.uptime)')
array element        (offending value in entry 'my_list': '$(sys.workdir)')
nested bad key       (offending key in entry 'myvar': 'tag$(z)')
classes              (offending value in entry 'my_class': 'any.$(bad)')
```

**B-5a discrimination**, with the naive one-walk regression built deliberately:
test 12 **Pass**, test 15 **FAIL (UNEXPECTED FAILURE)**. With the real fix:
13 passed, 0 failed, 0 skipped, exit 0, fresh `BASE_WORKDIR`.

**B-20 null crash backtrace** (unpatched master, decoded from the macOS crash
report — line numbers match unpatched `cmdb.c` exactly):

```
AddCMDBVariable                          libpromises/cmdb.c:136
EvalContextVariablePutTagsSetWithComment libpromises/eval_context.c:2492
VariableTablePut                         libpromises/variable.c:255
RvalNewRewriter                          libntech/libutils/rlist.c:474
xstrdup                                  libntech/libutils/alloc.c:57
strdup -> _platform_strlen   <-- EXC_BAD_ACCESS, KERN_INVALID_ADDRESS at 0x0
```

Six inputs fixed, including two silent-corruption cases: `[1, null]` installed
`{"1"}`; `[null]` installed an empty slist.

**B-21 / CFE-4739 sites** (confirmed crashing, `libpromises/generic_agent.c`):
`:454` (`vars`), `:606` (`variables` — note `{"value": null}` is *safe* there,
that path has a `NULL_JSON` guard `cmdb.c` lacked), `:723` (`classes`, NULL
into `CheckContextClassmatch()`). Array paths `:749`/`:792`/`:874` are safe via
`JsonIteratorNextValueByType(..., skip_null=true)`.

**B-6 edge cases measured** (before → after): `4-1` `3.000000`→`3`; `10/4`
unchanged `2.500000`; `-1*0` `-0.000000`→`0`; `3/0` `inf` unchanged;
`sqrt(-1)` `nan` unchanged; `2^62` → integer form; `2^63` **stays** `%lf`;
`0-2^63` (`LONG_MIN`) → integer form.

**B-7 non-regression**: `--show-vars`/`--show-classes` filtered to
`source=cmdb`, byte-identical before/after across dotted, scoped,
ns-qualified, indexed and `.leading`/`trailing.`/`a..b` fixtures.

**Jira comments posted**: 159444 (CFE-4719), 159445 (CFE-4738), 159446
(CFE-4722), 159447 (CFE-4721), 159448 (CFE-4719 correction).

**fakeroot**: `00_basics/06_host_specific_data` 13/13 exit 0 clean;
`fakeroot id -u` → 501; the 4 root-requiring tests still FAIL.

## Operator Feedback

- **Rescinded the always-use-Fable standing order** (2026-08-18): *"We should
  remove the command to always use fable. Let's save it for when we are truly
  flummoxed by something."* Also flagged they may start running **Sonnet**
  normally, in which case **farm upstream code out to Opus 5**. Both memories
  updated (`fable-deep-always-authorized`, `upstream-code-needs-top-models`).
- **"Do all the work you can, remember you can farm things out to do them in
  parallel."** Authorised the three parallel subagents.
- **Asked to investigate the grok stalling** rather than route around it.
- **Asked whether a NOPASSWD sudo rule would defeat the purpose** — answered
  no on security grounds with the writable-target argument; they approved
  trying fakeroot instead.

## Where We're Going

1. **NEXT ACTION: B-21 / CFE-4739** — the augments `def.json` null segfaults,
   the one confirmed defect left unstarted. Fix the three sites in
   `libpromises/generic_agent.c` (`:454`, `:606`, `:723`); acceptance tests go
   in `tests/acceptance/00_basics/def.json/`. Model it on B-20:
   `cd /Users/djbclark/src/core-cmdbnull && git show 87490bb8f`.
2. **B-5b / CFE-4720** — last of the original batch, and a **behaviour**
   change (one bad key currently drops every variable). **Stack it on
   `fix/cmdb-name-offending-key`, not master** — you need CFE-4719's offender
   identification to skip the bad entry, and cutting from master guarantees a
   conflict with PR #6315.
3. **Watch for the first maintainer response** on any of #6307–#6318. One
   approval unblocks CI for all of them.
4. **Clean up worktrees when their PRs close**: `core-cmdbkey`, `core-cmdbnull`,
   `core-cmdbdotted`, `core-evalint`, plus older `core-darwin`, `core-getopt`,
   `core-jsontest`.

**Constraints for whoever picks this up:**

- Acceptance-test numbering in `00_basics/06_host_specific_data/` is taken
  through **15**: 12+15 on `fix/cmdb-name-offending-key`, 13 on
  `fix/cmdb-null-value-crash`, 14 on `fix/cmdb-dotted-key-warning`. Use 16+.
  These four branches **will conflict in `cmdb.c`** on merge — independent PRs
  off one master.
- Fable ~93% used, resets 2026-08-21. Per the rescinded order, do not reach for
  it unless genuinely stuck.

## Quick Start

```bash
# Tier 1 first
~/.claude/hooks/handoff-tools/.venv/bin/python \
  ~/.claude/hooks/handoff-tools/session_log.py read \
  --state-root ~/.local/state/handoffs --dir ~/.local/state/handoffs/tendcf/main

# PR / ticket state (expect: all OPEN, zero reviews, CI action_required)
for n in 6315 6316 6317 6318; do gh pr view $n -R cfengine/core \
  --json number,state,mergeable,comments,reviews \
  --jq '"#\(.number) \(.state) \(.mergeable) comments=\(.comments|length) reviews=\(.reviews|length)"'; done

# Start B-21 / CFE-4739
cd /Users/djbclark/src/core-darwin && git fetch upstream master
git worktree add /Users/djbclark/src/core-augnull -b fix/augments-null-value-crash upstream/master
cd /Users/djbclark/src/core-augnull && git submodule update --init libntech
./autogen.sh --prefix=/Users/djbclark/opt/cfengine-dev-augnull \
  --with-openssl=/opt/homebrew/opt/openssl@3 --with-pcre2=/opt/homebrew/opt/pcre2 \
  --with-lmdb=/opt/homebrew/opt/lmdb --with-libyaml=/opt/homebrew/opt/libyaml \
  --enable-maintainer-mode
make -j8

# Reproduce the crash (def.json, not host_specific.json)
WD=/tmp/augnull; mkdir -p $WD/inputs; : > $WD/inputs/promises.cf
printf '%s' '{"vars": {"k": null}}' > $WD/inputs/def.json
CFENGINE_TEST_OVERRIDE_WORKDIR="$WD" ./cf-promises/cf-promises -f $WD/inputs/promises.cf; echo "rc=$?"

# Run acceptance tests — ALWAYS fakeroot + a FRESH workdir, and check the
# total against `ls *.cf | wc -l` before quoting it anywhere
export BASE_WORKDIR=/tmp/augnull-wd; rm -rf $BASE_WORKDIR; mkdir -p $BASE_WORKDIR
cd tests/acceptance && ./testall --gainroot=fakeroot 00_basics/def.json

# Review panel — on a DISPOSABLE COPY, one seat per copy, never the build tree
cp -a /Users/djbclark/src/core-augnull /tmp/rc-grok
cd /tmp/rc-grok && grok --model grok-4.6 --always-approve -p "$(cat brief.md)"
cd /Users/djbclark/src/core-augnull && git status   # MUST be clean afterwards
```

**Traps, all bitten this session:**

- A libpromises edit needs a forced relink or the test runs the OLD library:
  `rm -f libpromises/<f>.lo libpromises/.libs/<f>.o libpromises/libpromises.la libpromises/.libs/libpromises*`
- `testall` exit code is unreliable — read the `Failed tests:` line.
- `--gainroot=sudo` with an expired credential exits **144 with no output**;
  looks like a hang, is a failure.
- A dirty `BASE_WORKDIR` **inflates the pass count**. It put a wrong number in
  a public PR this session.
- `grok --debug` needs `--debug-file`, not `--log-file`.
- `./cf-promises/cf-promises` is a libtool wrapper; the real binary in
  `.libs/` will not run standalone (use `./libtool --mode=execute`).
- Verify parallel-subagent worktree isolation before pushing:
  `grep -c <other-branch-symbol> <worktree>/<file>` per pair.
