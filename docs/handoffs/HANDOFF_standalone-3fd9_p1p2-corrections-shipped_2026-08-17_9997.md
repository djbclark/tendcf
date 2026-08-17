---
schema_version: 1
handoff_id: 9997
parent_handoff_ids: [3a89]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: eac0b057d13348257bbf8475ca539f0d9f677048
created_at: 2026-08-17T12:36:00-0400
writer: claude-code
---

# Handoff — the P-1/P-2 corrections shipped, and the worse bug they uncovered

## The Goal

Session opened with `/baton` to resume `3a89`, whose owed work was the **P-1/P-2
corrections**: two live upstream PRs (`cfengine/core#6293`, `#6294`) publicly
flagged *HOLD OFF MERGING* with fixes promised and unwritten. `3a89` had parked
them on Fable quota until ~11:20 EDT.

**That debt is now fully cleared.** The operator added one instruction mid-session
(drop the `Link Issues` request, use URL workarounds), which was also completed.

## Where We Are

`tendcf` clean at `eac0b05`, pushed. All four sibling worktrees clean:

| workspace | branch | head | dirty |
|---|---|---|---|
| `/Users/djbclark/src/core-p1` | `simulate-keep-chroot` | `f6c06f9e2` | no |
| `/Users/djbclark/src/core-p2` | `simulate-json` | `b3a6c3da5` | no |
| `/Users/djbclark/src/libntech-fixes` | `fix/json-number-fatal-exit` | `11725b0` | no |
| `/Users/djbclark/src/core-json` | `fix/json-number-rendering` | `32c38f8ab` | no |

**Nothing is in flight.** No uncommitted work anywhere, no stashes, no running
agents.

### Done — both PRs corrected and pushed

| PR | was → now | trailer | state |
|---|---|---|---|
| `core#6293` | `64e2ac1cb` → `f6c06f9e2` | `Ticket: CFE-4715` | OPEN, MERGEABLE |
| `core#6294` | `05e18f038` → `b3a6c3da5` | `Ticket: CFE-4716` | OPEN, MERGEABLE |

One amended commit each, force-pushed with `--force-with-lease`, `origin` heads
verified to match local. Hold-off notices superseded by
[issuecomment-5317643214](https://github.com/cfengine/core/pull/6293#issuecomment-5317643214)
and
[issuecomment-5317643473](https://github.com/cfengine/core/pull/6294#issuecomment-5317643473),
plus a CFE-4730 follow-up
([issuecomment-5317677474](https://github.com/cfengine/core/pull/6294#issuecomment-5317677474)).

**Three false claims of our own were deleted from the commit messages:**

| claim | why it was false |
|---|---|
| P-1: the tree "is created with mode 0700" | `mkdir`'s mode is masked by `umask`; under `umask 0777` the real agent produced mode **0000**, an unusable directory, no error |
| P-1: copies "can never end up in a directory with looser permissions" | `mkdir(0700)` does not inspect the **parent**. Now actually enforced rather than asserted |
| P-2: "the prose renderers are unchanged" | the package-cancellation fix changes `--simulate=diff` and `manifest` prose |

### Done — the 15 CFE tickets cross-linked with URLs

`Link Issues` is **permanently refused** (see Operator Feedback). Every one of the
15 tickets gained an `h3. References` section with sibling `browse/CFE-####` URLs,
`Public working record:` GitHub URLs, and a wiki-markup-linked JQL query for the
whole set. Verified by reading stored descriptions back, not by trusting the 204s.

### Done — three security@ threads pointed at their CFE keys

| thread | replied to | sent | keys |
|---|---|---|---|
| `1a00d22ac0d46c9b` | `1a00d44a2758b9ea` | `1a01090fc7a48723` | CFE-4726/4728/4729 **+4727** |
| `1a00f99c7e714823` | `1a00f99c7e714823` | `1a0109145ccf2df0` | CFE-4724/4725 **+4730** |
| `1a007e4362402bd9` | `1a00fb936fc1741f` | `1a010916dbcebd08` | CFE-4717 |

Thread `1a00d603be0b1dfe` ("Heads up: finding more security issues with Opus 5")
deliberately left alone — it reports no specific item, so there is no key to point at.

### New — CFE-4730 / register item B-13

**libntech's JSON string codec is non-conformant in both directions, and the read
half silently corrupts valid standard JSON.** Filed as
[CFE-4730](https://northerntech.atlassian.net/browse/CFE-4730), bidirectionally
linked with CFE-4716, disclosed on PR 6294 and to `security@`. **Not fixed.**
This is now the most serious open item in the register.

### Blockers

**None.** Both blockers inherited from `3a89` were false — see What We Tried #1.
The only standing constraint is the model rule: PR-bound C must go to a
`fable-deep` subagent with `model` pinned to `'fable'`, because the main session
runs Opus 5.

### Files changed this session

**`tendcf`** — two commits, both pushed:
- `7e5873c` `docs/architecture/upstream-register.md` (+61) — the issue-linking
  section, the permission table, the JQL URL, and a correction to the register's
  own record.
- `eac0b05` same file (+5/−5 plus a new `B-13` row) — P-1/P-2 shas and trailers,
  the CFE key table extended to CFE-4730, `B-13` inserted after `B-12`.

**`/Users/djbclark/src/core-p1`** — committed into `f6c06f9e2`, 13 files, +665/−7:
`cf-agent/cf-agent.c`, `libpromises/eval_context.c`, `libpromises/generic_agent.c`,
`tests/unit/eval_context_test.c` (+40), and three new acceptance tests with their
`.cf.sub` files (`keep_chroot_perms`, `keep_chroot_parent_perms`,
`keep_chroot_path_limits`).

**`/Users/djbclark/src/core-p2`** — committed into `b3a6c3da5`, 7 files, +1549/−37:
`cf-agent/simulate_mode.c` (+312 in the diff, incl. `RestoreUtf8InJson()` and
`ValidUtf8SequenceLength()`), `cf-agent/cf-agent.c`, `tests/unit/simulate_mode_test.c`
(13 → 17 cases), `tests/acceptance/29_simulate_mode/simulate_json.cf` and its
`.expected` (−12 masked lines).

**Memory** (`~/.claude/projects/-Users-djbclark-src-tendcf/memory/`): new
`jira-no-link-issues-permission.md` and `test-with-conformant-decoder.md`, two
`MEMORY.md` index lines appended.

## What We Tried

Failures and near-misses, chronological. These are the expensive ones.

1. **THE BIG ONE — two blockers inherited from `3a89` were both false, and I
   repeated both without retesting.**
   - *"Gmail MCP connector session EXPIRED."* It works fine. The operator had to
     say so twice ("We are using the claude gmail connector not any mcp thing",
     then "And claude UI says it is fine - how do I fix") before I tested it — and
     it worked on the first call. Three replies went out minutes later. There was
     never anything to fix.
   - *"Ask nickanderson for the `Link Issues` permission."* Already asked and
     already refused. Logged as a pending action item, which would have burned
     another round trip on a settled question.

   **Rule: retest an inherited blocker before repeating it as a blocker.** A
   handoff records what was true when written; a stale blocker is worse than no
   note, because it stops work that would otherwise succeed.

2. **Remote/web links are gated on the same permission as issue links** — this was
   the obvious workaround and it does not work. `POST
   /rest/api/2/issue/CFE-4715/remotelink` → **HTTP 403** `No Link Issue Permission`.
   Probed with a disposable `globalId` so the 403 meant nothing was created. Do not
   try this again.

3. **`/rest/api/2/search` is now HTTP 410.** The first JQL validation attempt used
   it. The live endpoint is `/rest/api/3/search/jql`.

4. **`git add -A tests` swept my own testall artifacts into the P-1 commit** —
   `diff_mode.cf.actual`, `.temp`, `manifest_full_mode.*`, `manifest_mode.*`, six
   files of test output that would have gone upstream. Caught by reading
   `git show --stat` on the amended commit *before* pushing, removed with
   `git rm --cached`, and re-amended. **Always read `git show --stat` after an
   `add -A` in a tree where acceptance tests have been run.**

5. **My own UTF-8 round-trip verification failed twice before it worked**, and
   neither failure was the code's fault. `cf-agent -f policy.cf` fell through to
   the built-in failsafe because `cf-promises` is not in the workdir `bin/`;
   copying it into a `CFENGINE_TEST_OVERRIDE_WORKDIR` did not fix it either. I
   stopped fighting the environment and verified through the acceptance test plus
   `cf-promises --show-vars` instead. Note the flag is **`--show-vars`**, not
   `--show-evaluated-vars` (which does not exist).

6. **The `29_simulate_mode` acceptance directory has three tests that fail on this
   host for environmental reasons** — `diff_mode`, `manifest_mode`,
   `manifest_full_mode`. Their `.expected` hard-codes `Uid: (0/root)` while
   `--gainroot=env` runs as uid 501, and macOS has no `fakeroot`. I proved they
   fail identically at HEAD before attributing them to the environment. **Do not
   read these three as a regression.**

7. **A local rerun trap the unfixed code creates** (found by the Fable agent): a
   failing unfixed run leaves keep dirs at mode `0000`, and macOS BSD `rm -rf` as
   non-root cannot traverse an unreadable directory, so `testall`'s workdir wipe
   silently fails and the *next* run false-fails on `EEXIST`. Not a CI risk — and
   it is a live demonstration of why the umask bug mattered.

## Key Decisions

- **Delegated all PR-bound C to `fable-deep` with `model: 'fable'`, and verified
  every claim myself rather than accepting the reports.** Two agents, both
  confirmed `claude-fable-5` at xhigh in their first line. Re-ran both builds, both
  suites, rebuilt the ASan harness from scratch, and proved test discrimination by
  stashing sources. Rejected: trusting the agent reports (the whole reason these PRs
  were flagged is unverified claims); writing the C on Opus (forbidden by
  `upstream-code-needs-top-models` + `stop-when-cannot-set-effort`).
- **Ran P-1 and P-2 agents in parallel** on independent worktrees rather than
  serially. Rejected: the handoff's sequential order — the PRs are independent and
  wall-clock mattered with Fable quota at 52%.
- **Backed up each working tree to a patch file with a sha256 before every
  `git stash` discrimination test**, and verified the restore matched the hash.
  Both restores were byte-identical. Rejected: skipping the stash test — a test
  that passes both ways is not a regression test, which is exactly what `ee9c`
  shipped last session.
- **Enforce, not retract, on P-1's parent-permission claim** (Fable's call, which I
  endorsed): refuse a group/world-writable non-sticky parent. Rejected: deleting the
  sentence from the commit message. Also chose plain `chmod` over libntech's
  `safe_chmod`, because `safe_chmod` opens the target `O_RDONLY` first and would
  fail `EACCES` on exactly the mode-`0000` directory the fix prevents.
- **Included P-2's eighth defect in `#6294`** (operator-confirmed): the identical
  dead-`MapRemove` in `ManifestPkgOperations()`. Rejected: a separate PR, and
  fork-only. The PR comment offers to split it out if maintainers prefer.
- **Shipped P-2's UTF-8 workaround in core AND filed the libntech root cause**
  (operator-confirmed). Rejected: fixing libntech instead — it is pinned at
  `5b5d04e1` for this branch, it changes output for every consumer, and it would
  couple two PRs.
- **No labels on the CFE tickets.** The reporter is already visible, so
  reporter-scoped JQL retrieves the set without adding a foreign label to someone
  else's board.
- **Dropped the "this project does not grant issue-link permission" explanation
  from the ticket boilerplate.** It would have appeared 15 times on someone else's
  public tracker. Said once, in the register, instead.

## Evidence & Data

**P-1 verification, all re-run by the owning session:**

```
make -j2                                   rc=0, 0 warning: lines
tests/unit make check                      All 68 tests behaved as expected (4 expected failures)
ASan old-overflow                          ERROR: negative-size-param: (size=-1)
ASan new-overflow / new-boundary-abort     DoCleanupAndExit(1), clean
ASan new-boundary-pass                     strlen=1023 == PATH_MAX-1
live: umask 0777                           drwx------
live: 0777 non-sticky parent               refused, nothing created
live: 1777 sticky parent                   allowed, drwx------
live: trailing slash                       works, drwx------
live: pre-existing dir                     mkdir: File exists, fatal
mechanism                                  mkdir(path,0700) under umask 0777 -> mode 0000
```

**P-1 discrimination** (`git stash` of the 3 source files, whole directory):
at HEAD **2 pass / 6 fail** with all three new tests failing and
`test_changes_chroot: Test failed`; fixed **5 pass / 3 fail** with all three new
tests passing. Working tree restored, `git diff | shasum -a 256` =
`28a333f961e33965647be79311bbe0e3f0931d253c25a6de3770fce0926faf21`.

**P-2 verification:** `make -j2` rc=0, 0 warnings; unit **17/17** (was 13);
full suite **All 69 tests behaved as expected (4 expected failures)**;
`29_simulate_mode/simulate_json.cf` **Pass**. Discrimination: with the two source
files stashed and the test file kept, `test_special_characters_in_path`,
`test_pkg_operations_cancel` and `test_output_symlink_not_followed` all fail,
binary **rc=3**. Restore hash
`ed3294364bd9d9e4e338442be187d12903a6c0c5800bea72c09a8f41b9277dd8`.

**Honest gaps, stated in the PR comments too:** the ASan run verifies the
*function's logic* via a harness built from verbatim extracted function text, not
the linked `cf-agent` object — a full ASan reconfigure would have destroyed the
tree's known-good configuration. Two P-1 sub-cases and two P-2 unit cases pass
either way and are kept deliberately (`test_write_failure` cannot see the `main()`
half from a unit test).

**CFE permissions**, `GET /rest/api/3/mypermissions?projectKey=CFE`:

```
YES  ADD_COMMENTS, BROWSE_PROJECTS, CREATE_ATTACHMENTS, CREATE_ISSUES,
     EDIT_ISSUES, TRANSITION_ISSUES
no   LINK_ISSUES, MANAGE_WATCHERS, SCHEDULE_ISSUES, SET_ISSUE_SECURITY
```

**The JQL grouping URL** (validated anonymously, HTTP 200, 15 keys; names keys
explicitly so it carries no Atlassian accountId and is safe in this public repo):

```
https://northerntech.atlassian.net/issues/?jql=key+in+(CFE-4715,+...,+CFE-4729)+ORDER+BY+key+ASC
```

**Cross-link audit result** (why the register needed correcting): only **6 of 15**
tickets had any sibling key — `4719`↔`4720` and `4724`↔`4725` both ways,
`4727`→`4726`, `4728`→`4726`, `4729`→`4728` one way — with **zero** browse URLs,
**zero** labels, and **seven** tickets (`4718`–`4723`, `4727`) carrying no GitHub
artifact link at all.

**CFE-4730, the new defect, with line references at libntech `5b5d04e1`:**

```
write: libutils/json.c:1015-1022  CharIsPrintableAscii else WriterWriteF("\\u%04x", (unsigned char) *c)
read:  libutils/json.c:1063       HexStringToChar rejects (c > 255)
read:  libutils/json.c:1108-1120  case 'u': breaks WITHOUT advancing c, so for(...;c++) lands on the 'u'
```

Repro, measured:

```
$ printf '{"city": "\\u4e2d\\u56fd", "cafe": "caf\\u00e9"}\n' > data.json
$ python3 -c "import json; print(json.load(open('data.json')))"
{'city': '中国', 'cafe': 'café'}
$ cf-promises -f p.cf --show-vars        # "d" data => readjson("data.json", 4096)
default:main.city   u4e2du56fd
default:main.cafe   <non-printable>
default:main.d      {"cafe":"café","city":"u4e2du56fd"}
```

`中国` becomes the seven-character literal `u4e2du56fd`, silently. The two halves
are exact inverses, so libntech round-trips its own output perfectly and no
write-then-read test can catch either.

**Quota at session end:** gmail active, 5h window fresh at session start (reset
11:19), Fable 52% used with 3d 18h remaining. Two Fable agents consumed ~452K
subagent tokens between them.

## Operator Feedback

- *"I asked for link issues - they don't give out that perm - use workarounds"*,
  then *"eg URls"*. Settled — Northern.tech does not grant that permission to
  community reporters. Saved as memory `jira-no-link-issues-permission`.
- *"We are using the claude gmail connector not any mcp thing."* then *"And claude
  UI says it is fine - how do I fix"*. The answer was that there was nothing to
  fix; the connector worked on the first call.
- Chose **"Include it in #6294"** for P-2's eighth defect.
- Chose **"Ship core workaround, file libntech root cause"** for the UTF-8 fix
  location.
- Standing, still in force from `ee9c`: *"You do not need to wait for me to open
  PRs or send emails, however you do need to hold off for long enough to minimize
  the chances of posting something incomplete or wrong."*

## Where We're Going

1. **THE NEXT ACTION — fix libntech's JSON string codec, CFE-4730 (task #10).**
   Both halves together: fixing only the writer leaves libntech misreading its own
   files. Writer at `libutils/json.c:1015-1022` should emit valid UTF-8 raw; reader
   at `:1108-1120` + `:1063` must decode `\uXXXX` across the BMP, handle surrogate
   pairs, and **never** fall through in a way that turns an unhandled escape into
   literal text. Regression tests **must** round-trip through
   `python3 -c 'import json; json.load(...)'`, never `JsonParseFile` — that decoder
   reverses its own corruption and is the trap that hid this. Per
   `upstream-fix-everything-policy`: fork branch + fork issue/PR + the CFE ticket
   (already filed). PR-bound C, so **Fable 5 xhigh only**. Worktree: cut a fresh
   branch from stock in `/Users/djbclark/src/libntech-fixes`, or a new worktree —
   do not build on `fix/json-number-fatal-exit` unless the change is meant to ship
   with that stack.
2. **Task #9 — six ticketed items still have no upstream PR.** B-1 (CFE-4728),
   B-2 (CFE-4729), B-8 the only true fail-open (CFE-4726), core half of B-10
   (CFE-4725), B-12 unwritten (CFE-4723), and the exec_timeout termination half
   (CFE-4727) — **start from the ALARM_PID theory, the refutation is retracted**.
   Then E-9 and `services:`.
3. **Watch both PRs for maintainer response.** `#6293` and `#6294` are corrected
   and MERGEABLE for the first time. If a maintainer asks to split P-2's eighth
   defect out, the PR comment already offered that.
4. **Consider whether CFE-4730 changes P-2's shape.** If maintainers prefer the
   libntech fix, `#6294`'s `RestoreUtf8InJson()` (~140 lines) comes out. Do not
   pre-emptively remove it.
5. Housekeeping, still not urgent: `git worktree remove` for `core-p1`, `core-p2`,
   `libntech-b4`; `core-json` needs `make clean` first. Disk is fine.

## Quick Start

```bash
# 0. Model gate — PR-bound C only via a fable-deep subagent, model pinned to 'fable'
cswap list                      # confirm Fable headroom before starting task #10

# 1. Reproduce CFE-4730 in 20 seconds (cf-promises, no workdir setup needed)
cd /tmp && printf '{"city": "\\u4e2d\\u56fd"}\n' > data.json
cat > p.cf <<'EOF'
bundle agent main
{
  vars:
      "d" data => readjson("/tmp/data.json", 4096);
      "city" string => "$(d[city])";
}
EOF
/Users/djbclark/src/core-p2/cf-promises/cf-promises -f p.cf --show-vars | grep city
# expect: default:main.city   u4e2du56fd      <- the bug. Flag is --show-vars.

# 2. The code
cd /Users/djbclark/src/core-p2/libntech && sed -n '1015,1022p;1060,1066p;1105,1122p' libutils/json.c

# 3. Baselines (measure, never assume — core-p2 is 69, not 68)
cd /Users/djbclark/src/core-p1 && make -j2 && rm -f tests/unit/eval_context_test && (cd tests/unit && make check)
cd /Users/djbclark/src/core-p2 && make -j2 && rm -f tests/unit/simulate_mode_test && (cd tests/unit && make check)

# 4. Live upstream state
gh pr view 6293 -R cfengine/core --json state,mergeable,headRefOid   # expect f6c06f9e2
gh pr view 6294 -R cfengine/core --json state,mergeable,headRefOid   # expect b3a6c3da5
gh pr view 291  -R NorthernTechHQ/libntech --json state,mergeable,headRefOid

# 5. Jira (token via the broker only; never echo it). NOTE: /api/2/search is HTTP 410.
TOKEN=$(sudo-secretspec get ATLASSIAN_CFENGINE_API_TOKEN --reason "<why>")
BASE=https://northerntech.atlassian.net
curl -sS -u "djbclark@gmail.com:$TOKEN" "$BASE/rest/api/2/issue/CFE-4730?fields=summary,status"
curl -sS -u "djbclark@gmail.com:$TOKEN" -G "$BASE/rest/api/3/search/jql" --data-urlencode "jql=project=CFE AND reporter=currentUser() ORDER BY key ASC" --data-urlencode "fields=key,summary"
```

**Do not** build or modify `/Users/djbclark/src/cfengine-core` — other work uses it
and its libntech submodule must stay uncommitted. Builds at `-j2`/`-j4`, never `-j8`.

**`diff_mode`, `manifest_mode` and `manifest_full_mode` fail on this host by
design** — their `.expected` hard-codes `Uid: (0/root)`, `--gainroot=env` runs as
uid 501, and macOS has no `fakeroot`. Proven identical at HEAD. Not a regression.

**Retest any blocker you inherit from this document before repeating it.** Two of
`3a89`'s were false and both cost real work — see What We Tried #1.
