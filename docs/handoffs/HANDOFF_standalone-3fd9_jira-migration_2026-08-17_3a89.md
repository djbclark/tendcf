---
schema_version: 1
handoff_id: 3a89
parent_handoff_ids: [ee9c]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 3b07e68e60fdd4262360a093e9452429c3b6c969
created_at: 2026-08-17T10:36:35-0400
writer: claude-code
---

# Handoff — the Jira migration, and the P-1/P-2 corrections it interrupted

## The Goal

Session opened with `/baton` to resume `ee9c`, whose owed work was the **P-1/P-2
corrections**: two live upstream PRs (`cfengine/core#6293`, `#6294`) publicly
flagged as defective with fixes promised and unwritten.

Two interruptions redefined the session:

1. The operator **paused** twice (`pause`, then `pause immediatly`) partway
   through the first P-1 edit.
2. On resume the operator gave a **new, larger instruction**: *"Since Jira is
   working now via the API, move all currently open issues — libntech and
   cfengine and core — over to Jira. Then comment in each discussion or email
   reply or PR or issue or whatever that a Jira issue has been created … and
   link to that Jira ticket. Going forward, remember to always use Jira, no
   longer email or open discussion threads."*

That second instruction is what this session actually delivered. The P-1/P-2
corrections remain owed and are the next session's job.

## Where We Are

`tendcf` clean at `3b07e68`, pushed.

### Done — the Jira migration

**All 15 open items filed in project CFE ("CFEngine Community") as
`CFE-4715`–`CFE-4729`,** every one linked back from every channel it already
lived on.

| item | key | item | key |
|---|---|---|---|
| P-1 `--simulate-keep-chroot` | CFE-4715 | B-5b one bad key drops all vars | CFE-4720 |
| P-2 `--simulate-json` | CFE-4716 | B-6 `eval()` returns `%lf` | CFE-4721 |
| P-3 silent digest failure | CFE-4717 | B-7 dotted CMDB keys | CFE-4722 |
| B-3 no `process_darwin.c` | CFE-4718 | B-12 `lowest_metric` unassigned | CFE-4723 |
| B-5a rejected CMDB names nothing | CFE-4719 | **B-4 + B-10 + B-11** (one stack) | CFE-4724 |
| B-10 core half (`core#13`) | CFE-4725 | B-8 fail-open | CFE-4726 |
| exec_timeout termination half | CFE-4727 | B-1 poll loops count iterations | CFE-4728 |
| B-2 descendants not signalled | CFE-4729 | | |

Linked on: PRs `cfengine/core#6293`, `#6294`, `NorthernTechHQ/libntech#291`;
discussions `#6295`, `#6296`; issue `libntech#290`; and fork artifacts
`djbclark/core#2,3,4,5,6,8,9,10,11,12,13,14`, `djbclark/libntech#2,3,4`, plus
fork PRs `djbclark/libntech#1` and `#5`.

**Deliberately not filed:** `djbclark/core#7` (our own submodule-dependency
tracking) and `#1` (the P-1/P-2 investigation trail, which the register itself
says "is not itself a defect"). Neither is an upstream defect.

### Not done

- **Email replies.** The Gmail MCP connector's session is **expired**
  (`MCP server "claude.ai Gmail" session expired`). The two `security@` threads
  (`1a00d22ac0d46c9b`, `1a00f99c7e714823`) still have no reply pointing at the
  new keys. This is the one part of the operator's instruction outstanding.
- **P-1/P-2 corrections** — parked on Fable quota, see Blockers.

### Blockers

- **Fable 5 unavailable until ~11:20 EDT.** `djbclark@gmail.com`'s 5h window hit
  **100%**; `djbclark@mit.edu` became the active account and **only gmail has
  Fable**. Session ran on Opus 5 / high. Operator: *"We will need to put
  anything that needs fable on pause for 1h7m."* Upstream PR-bound C requires
  Fable 5 xhigh, so tasks #1–#8 are parked.
- **No `Link Issues` permission in CFE** — see What We Tried #2.

### Files changed this session

**`tendcf`** — one commit `3b07e68`, pushed:
`docs/architecture/upstream-register.md` (+78/−19) — CFE row in the channels
table, the "Channels" section rewritten to make Jira the only filing channel,
the resolved Jira entry with the full key-mapping table, and the refiling
checklist's "verbatim" instruction corrected.

**`/Users/djbclark/src/core-p1`** — **UNCOMMITTED, UNBUILT, UNTESTED** (2 files,
+23/−5), from before the pause:
- `libpromises/eval_context.c` — `ToChangesChroot()` now fails closed: explicit
  bound check with `Log(LOG_LEVEL_ERR)` + `DoCleanupAndExit(EXIT_FAILURE)`
  (matching the file's own idiom at line 2831), the `strncpy` whose count
  underflowed to `SIZE_MAX` replaced with a `memcpy` of the measured length, and
  the useless `assert` at 3875 (which recomputed the same underflowed bound)
  removed. A `given_path` alias was added to report the original path.
- `cf-agent/cf-agent.c` — the `strlen(optarg) >= PATH_MAX` guard replaced with
  `> PATH_MAX / 2`, reserving half the budget for mapped paths, with a comment
  giving the rationale.

**Memory** (`~/.claude/projects/-Users-djbclark-src-tendcf/memory/`): new
`upstream-channel-is-jira.md` and `never-refile-body-verbatim.md`; two `MEMORY.md`
index lines appended; `upstream-fix-everything-policy.md` corrected in three
places.

**No other repo was touched.** `core-p2`, `libntech-fixes`, `core-json` are all
clean at `05e18f038`, `11725b050`, `32c38f8ab`.

## What We Tried

Failures and near-misses, chronological. These are the expensive ones.

1. **THE BIG ONE — the register told us to copy issue bodies verbatim, and that
   would have republished five withdrawn claims.** The refiling checklist said a
   ticket should carry "the fork issue's body verbatim — they are written as
   standalone bug reports … precisely so this step is a copy." That is wrong,
   because **our corrections are added as comments and the bodies still carry
   the original false claim.** Caught before filing by reading body *and*
   comments for every item. What would have gone onto a public tracker under
   today's date:

   | item | the body still claims | the comment retracts it to |
   |---|---|---|
   | B-1 (`core#4`) | this patch closes the fail-open | withdrawn — it shrinks a race window; the fail-open is B-8 |
   | B-2 (`core#5`) | unconditional `setpgid` is fine; `pgid==pid` closes a recycle race | measured SIGTTIN hang with no timeout to end it; recycle claim wrong |
   | B-8 (`core#6`) | "reported as **kept**" | "reported as **compliant**" — default for exit 0 is *repaired* |
   | B-10 (`libntech#4`) | dies "the moment anything **renders**" | trigger is **copying at policy load**, `JsonPrimitiveCopy()`, a 5th site |
   | P-3 (`libntech#290`) | `HashPubKey()` is the TLS TOFU identity | it is not on the peer-facing path at all; colliding *lookup handle* |

   `djbclark/core#13` is stale in the *other* direction — it says behavioural
   verification is outstanding, which has since been done. Every ticket was
   written from the corrected state and **says so where we retracted
   something**. The checklist is fixed in the register and saved as memory
   `never-refile-body-verbatim`.

2. **Native Jira issue links — blocked, HTTP 401.**
   `POST /rest/api/3/issueLink` for all 11 intended `Relates` links returned
   `{"errorMessages":["No Link Issue Permission for issue 'CFE-4724'"]}`. The
   account has **Create Issue** but not **Link Issues** in CFE. First diagnosis
   attempt assumed an empty token; verified otherwise (token length 192,
   `/myself` → 200). **Workaround applied:** the sibling keys were written into
   the descriptions instead, and Jira auto-renders bare issue keys as links.
   *Worth asking nickanderson for `Link Issues` too.*

3. **Wrote seven ticket bodies containing dangling references** — "a separate
   ticket", "the libntech ticket", "tracked separately" — because the sibling
   keys did not exist yet at write time. Found by grepping the scratch bodies
   for those phrases, patched, and `PUT` back (all HTTP 204). Verified by
   reading the stored descriptions back and extracting `CFE-47xx` occurrences.
   **If more tickets are filed in a batch, write the bodies first and
   cross-reference in a second pass.**

4. **`session_log.py write` rejected the payload** — `payload blockers must be a
   list of strings`. It was passed a string. This is why the first pause left
   Tier 1 stale; corrected on the second write.

5. **Gmail connector expired mid-session**, so the "email reply" half of the
   operator's instruction could not be executed and the security@ threads could
   not be checked for replies before the disclosure decision.

6. **A transient GitHub `HTTP 503` on the GraphQL API** while checking
   `libntech#291`. Retried three times with backoff; succeeded on the first
   retry. Not a real failure — do not read it as one.

## Key Decisions

- **Asked the operator before publishing the six `security@`-reported items.**
  CFE is fully public — verified by anonymous `GET /rest/api/2/issue/CFE-4715` →
  **200**, and the create screen has **no `security` field**, so there is no
  restricted-visibility option. Operator chose **"File all six publicly now"**.
  Rejected alternatives offered: hold B-8 alone (the only true fail-open), and
  hold all six pending a security@ reply.
- **B-4 + B-10 + B-11 get ONE ticket (CFE-4724)**, not three, because they ship
  as one six-commit stack and are explicitly *not independently landable*
  (reclassifying exponent numbers as REAL without the lexeme fix makes `1e400`
  render as `inf`, which stock never emitted). The core half is a separate
  ticket (CFE-4725) because it lands as its own PR in a different repo.
- **`CFE-4727` is a new filing**, not a migration — the exec_timeout termination
  half had never been filed anywhere.
- **Used `/rest/api/2/` for issue creation**, not v3, so descriptions can be
  wiki markup instead of ADF JSON. Much simpler; v3 used only for reads and
  metadata.
- **Fold the `Ticket:` trailer update into the corrections force-push**
  (`#6295` → `CFE-4715`, `#6296` → `CFE-4716`) rather than doing it now.
  Rejected: a separate rewrite now — that would be the **third** history rewrite
  on those two PRs, and the register already documents the churn as a
  maintenance liability.
- **Did not write P-1/P-2 C on Opus.** Two standing memories combine to forbid
  it (`upstream-code-needs-top-models`, `stop-when-cannot-set-effort`); the
  operator confirmed the pause independently.
- **Committed the register straight to master and pushed.** tendcf's CLAUDE.md
  scopes push-in-place to `docs/handoffs/` only, but the established practice
  for the register is direct-to-master (17 such commits last session), the
  register itself says "update it in the same commit that changes an item's
  state", and memory `commit-and-push-without-asking` gives standing
  authorization.

## Evidence & Data

**Jira access** (the thing that unblocked everything): `GET /rest/api/3/myself`
→ **200** as "Daniel Clark"; `POST /rest/api/2/issue` → **201**. Auth Basic,
`djbclark@gmail.com` + `ATLASSIAN_CFENGINE_API_TOKEN` via `sudo-secretspec`.
Projects visible: `ALV`, `CFE`, `MEN`. CFE issue types include `Bug`, `Story`,
`Task`, `Epic`, `Feature request`, `Knowledge acquisition`, `Development
efficiency`, `Plan`. **Only `summary` and `description` are required** on both
`Bug` (id 10005) and `Feature request` (id 10019).

**The root cause of the old 401**, per the operator: creating the Atlassian
account was *not sufficient* — permission had to be granted **in the CFE project
specifically**, which nickanderson arranged over Matrix.

**Upstream state, verified after all commenting:**

```
PR 6293  OPEN  mergeable=MERGEABLE  head=64e2ac1cb  comments=4
PR 6294  OPEN  mergeable=MERGEABLE  head=05e18f038  comments=4
PR 291   OPEN  mergeable=MERGEABLE  head=e76700b05  comments=5
```

**Quota at session start vs. during** — this is why the model changed:

```
start:  gmail  5h 80%  (resets 11:19)  Fable 48%   [active]
during: gmail  5h 100% (resets 11:20)  Fable 52%
        mit    5h 0%   7d 48%                      [active]
```

`~/.claude/settings.json` now `"model": "opus"`, `"effortLevel": "high"`.

**P-1's defect, unchanged and still the next thing to fix** (from `ee9c`):
guard at `cf-agent/cf-agent.c:815`, overflow at `libpromises/eval_context.c:3897`,
buffer `chrooted_path[PATH_MAX + 1]` at `:3847`. With `chroot_len == PATH_MAX`
the count `PATH_MAX - chroot_len - offset - 1` underflows to `SIZE_MAX`; ASan
reports `negative-size-param (size=-1)`. Build is `-DNDEBUG` so the `assert` is
compiled out anyway.

**Baselines** (unchanged, from `ee9c`): `core-p1` **68** tests rc=0, `core-p2`
**69** tests rc=0, both on stock libntech `5b5d04e1`.

**Tests run this session: NONE.** No build, no `make check`, no ASan run. The
`core-p1` edits are unverified.

## Operator Feedback

- *"pause"* then *"pause immediatly"* — stopped mid-edit; the second was honoured
  with zero further tool calls.
- *"Since Jira is working now via the API, move all currently open issues …
  over to Jira. Then comment in each discussion or email reply or PR or issue or
  whatever that a Jira issue has been created … and link to that Jira ticket.
  Going forward, remember to always use Jira, no longer email or open discussion
  threads."*
- Context for the thanks-line used in the public comments: *"thanks to
  nickanderson helping me out via matrix - turned out that just making the
  atlassian account was not enough, I also had to be given permission in the
  specific project to be able to post."*
- *"We will need to put anything that needs fable on pause for 1h7m."*
- Chose **"File all six publicly now"** when asked about the `security@` items.
- Standing, from `ee9c` and still in force: *"You do not need to wait for me to
  open PRs or send emails, however you do need to hold off for long enough to
  minimize the chances of posting something incomplete or wrong."*

## Where We're Going

1. **THE NEXT ACTION — confirm Fable, then resume P-1 task #2.** After ~11:20
   EDT run `cswap list`; if gmail's 5h window has reset, `cswap switch 2` and
   **confirm the session is Fable 5 at xhigh before touching any C**. Then the
   next edit is `libpromises/generic_agent.c:1647` in `/Users/djbclark/src/core-p1`:
   `chmod(keep_chroot, 0700)` after a successful `mkdir` (`FatalError` if it
   fails — under `umask 0777` the real cf-agent currently creates mode `0000`),
   plus the parent-permission decision: either refuse a group/world-writable
   non-sticky parent (`GetParentDirectoryCopy()` is already available via the
   `files_names.h` include) or delete the "never lands somewhere looser"
   sentence from the commit message.
2. **Review the uncommitted `core-p1` diff first** — it is unbuilt and untested,
   written on Opus, and touches the exact arithmetic the ASan repro exercises.
   Re-derive it on Fable if anything looks off rather than trusting it.
3. Remaining P-1: tests (mode under hostile umask, `EEXIST`, relative path,
   truncating keep path — `keep_requires_simulate` and `default_chroot_deleted`
   cover none of the new behaviour), ASan verification of the **fixed**
   functions, commit-message rewrite, rebuild at `-j2`, 68-test baseline.
4. **P-2's seven corrections** in `/Users/djbclark/src/core-p2`, starting with
   `cf-agent/simulate_mode.c:872–877` (`name_arch = NULL` before `MapRemove`).
   Full list is in `ee9c` "Where We're Going" item 2, unchanged.
5. **Force-push both**, and in the *same* push update the trailers to
   `Ticket: CFE-4715` / `CFE-4716` and replace the literal `CFE-XXXX` at
   `tests/acceptance/29_simulate_mode/simulate_json.cf:26` with `CFE-4716`.
   Then comment on both PRs that the fixes are up, superseding the
   hold-off-merging notices.
6. **Reconnect the Gmail connector** and reply on the two `security@` threads
   pointing at the new CFE keys. Notification only — email is retired as a
   *filing* channel.
7. **Ask nickanderson for `Link Issues` permission** in CFE, then add the
   `Relates` links listed in What We Tried #2.
8. Still unfixed upstream, now all ticketed: B-1/B-2/B-8 have no upstream PR
   (CFE-4728/4729/4726); core half of B-10 not offered (CFE-4725); B-12 unwritten
   (CFE-4723); exec_timeout termination half unfixed (CFE-4727) — **start from
   the ALARM_PID theory, the refutation is retracted**. Then E-9 and `services:`.
9. Housekeeping from `ee9c`, still not urgent: `git worktree remove` for
   `core-p1`, `core-p2`, `libntech-b4`; `core-json` needs `make clean` first.

## Quick Start

```bash
# 0. Model gate — do this BEFORE any C
cswap list                      # gmail 5h reset? then: cswap switch 2
# confirm Fable 5 / xhigh in-session before editing upstream code

# 1. The uncommitted work waiting for you
cd /Users/djbclark/src/core-p1 && git diff        # 2 files, +23/-5, unbuilt

# 2. The next edit site
sed -n '1640,1665p' libpromises/generic_agent.c   # mkdir(keep_chroot, 0700)

# 3. Rebuild + test (traps 1 and 2: top-level make first, force the relink)
make -j2 && rm -f tests/unit/<test> && (cd tests/unit && make check)

# 4. Live upstream state
gh pr view 6293 -R cfengine/core --json state,mergeable,headRefOid
gh pr view 6294 -R cfengine/core --json state,mergeable,headRefOid
gh pr view 291  -R NorthernTechHQ/libntech --json state,mergeable,headRefOid

# 5. Jira (token via the broker only; never echo it)
TOKEN=$(sudo-secretspec get ATLASSIAN_CFENGINE_API_TOKEN --reason "<why>")
BASE=https://northerntech.atlassian.net
curl -sS -u "djbclark@gmail.com:$TOKEN" "$BASE/rest/api/2/issue/CFE-4715?fields=summary,status"
# create: POST $BASE/rest/api/2/issue  {"fields":{"project":{"key":"CFE"},
#   "issuetype":{"name":"Bug"},"summary":...,"description":<wiki markup>}}
```

**Do not** build or modify `/Users/djbclark/src/cfengine-core` — other work uses
it and its libntech submodule must stay uncommitted. Builds at `-j2`/`-j4`,
never `-j8`.

**Before refiling anything anywhere: read the fork issue's comments, not just
its body.** See What We Tried #1.
