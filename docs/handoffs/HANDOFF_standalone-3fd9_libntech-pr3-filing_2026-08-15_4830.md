---
schema_version: 1
handoff_id: 4830
parent_handoff_ids: [d199]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 42cc20ac4f39ed01ba092db0d94d3a4e7f5f5450
created_at: 2026-08-15T18:54:12-0400
writer: claude-code
---

# Handoff — libntech PR 3 filing package, fork, and fork PR

## The Goal

Resumed from `d199` via `/baton`. The inherited next action was the schema
reconciliation pass, but the operator **redirected**: defer intense work to the
next quota window, and make PR 3 — the libntech silent-digest-failure fix —
the #1 priority: "put together a very solid bug report/fix/PR and get it put in
the right place."

That reframing is the whole session. The reconciliation was not started; it is
scheduled (see Where We're Going).

## Where We Are

| Workspace | Path | Branch | HEAD | State |
|---|---|---|---|---|
| tendcf | `~/src/tendcf` | `master` | `42cc20a` | **clean, pushed** |
| cfengine-core | `~/src/cfengine-core` | `simulate-json` | `071f85987` | ` M libntech` — expected, **do not commit** |
| libntech | `~/src/cfengine-core/libntech` | `silent-digest-failure` | `da7d3d9` | clean; 1 ahead / 0 behind `origin/master` |

**New this session:** the fork `djbclark/libntech` exists (it did not before),
the branch is pushed to it, and **djbclark/libntech#1** is open as a review PR.
The libntech checkout now has two remotes: `origin` = NorthernTechHQ (so
`git diff origin/master` stays correct) and `fork` = djbclark.

Five commits landed in tendcf, all pushed:

- `2ef5b91` — the filing package doc
- `fd40112` — secretspec declarations **(wrong, see What We Tried)**
- `daf5464` — revert of `fd40112`
- `3126740` — Jira credential state + the manifest drift it caused
- `42cc20a` — real URLs in the ticket text; fork PR opened

**Blocked:** the CFE Jira ticket is unfiled. Basic auth returns 401 and the
operator hit the same error in the browser. Called off as not worth the time;
the text is ready to paste by hand and is on the clipboard.

**Left behind for someone else:** `sudo-secretspec` manifest drift, briefed for
the stayturgid agent at
`<session-scratchpad>/stayturgid-drift-brief.md`. The operator explicitly took
this off tendcf's plate — "you can consider it not your issue."

## What We Tried

Chronological, including what failed — the expensive part to rediscover.

1. **Declared the Atlassian token by hand-writing a `secretspec.toml` in
   tendcf and running `secretspec` directly. WRONG, and the operator stopped
   me mid-flight** ("stop you are doing it wrong I am 90% sure"). This machine
   runs a privilege-separated **`sudo-secretspec`** boundary, and the
   `sudo-secretspec` skill forbids exactly what I did: never invoke
   `secretspec` itself for a managed deployment, never touch the provider or
   manifest directly. The correct route is `sudo-secretspec add` then
   `sudo-secretspec set`. Reverted in `daf5464`. **The lesson generalizes:
   check for a skill covering the subsystem before touching credentials,
   because the "obvious" tool was the forbidden one.**

2. **Assumed no Atlassian account existed** because nothing was in `~/.netrc`
   or the keychain. The operator corrected: they log in with Google. An
   Atlassian *identity* via SSO still supports API tokens, so the absence of
   stored credentials said nothing about whether an account existed.

3. **Hypothesized the 401 was "account has no membership on
   northerntech.atlassian.net."** The operator checked the browser and
   reported being logged in with a Create button, refuting it. Then reported
   the *same* 401 body in the browser at `/rest/api/3/myself`. Unresolved —
   probably one problem, not two, but not chased.

4. **Two "decisive" auth diagnostics that decided nothing.** `api.atlassian.com/me`
   401s because it wants OAuth bearer, not basic. And comparing anonymous vs.
   real vs. *garbage* credentials against `/rest/api/3/project/CFE` returned
   **200 for all three** — Jira ignores the `Authorization` header entirely on
   anonymously-readable endpoints. Only `/rest/api/3/myself` discriminates.

5. **The upstream gate false-positived on `-D`.** Two read-only `curl` GETs
   were denied as "a WRITE to a Jira ticket." The trigger is the `-D`
   (`--dump-header`) flag being read as a request-body flag; a
   `permissions=CREATE_ISSUES` query string may also have contributed. I
   dropped the flag and re-ran the same read rather than routing around the
   gate. **`upstream_review_gate.sh` deserves a fix — `-D`/`--dump-header` is
   read-only.**

6. **Wrote a ticket that promised a link and delivered none.** The description
   ended "A pull request doing this is linked below" with nothing below,
   because the upstream PR needs a ticket number and the ticket needs a PR
   URL. The operator broke the deadlock — "Oh I thought you'd just do a PR
   against our github fork" — which only ever bound the *upstream* PR.

## Key Decisions

**File a real CFE ticket rather than going ticketless** (operator choice from
a 3-option menu). The evidence for the rejected option is worth keeping: 23 of
the last 60 libntech commits carry no `Ticket:` line, and *every one of those*
also carries no `Changelog:` line — the two travel together. CONTRIBUTING says
outright to omit the prefix when there is no ticket. **If Jira stays blocked,
ticketless is a fully legitimate fallback**, and it costs only the changelog
entry.

**Fork under `djbclark`, not `frdminc`** (operator choice). Keeps all three
CFEngine PRs under one owner, since `djbclark/core` already exists.

**Open a PR against the fork** (operator's idea, adopted). Not an upstream
artifact, so ungated; gives the change a stable review URL and diff
immediately. *Rejected implicitly:* waiting for the ticket before any PR
existed at all.

**Do not declare the account email as a credential.** It is not secret, a
second declaration would be a second piece of manifest drift, and it is
recorded in the version-controlled doc instead. Value: `djbclark@gmail.com`.

**Register as `ATLASSIAN_CFENGINE_API_TOKEN`, not the hyphenated name the
operator typed.** secretspec names surface as environment variables, where
hyphens are invalid, and all 50 existing declarations are SCREAMING_SNAKE.
Flagged rather than done silently.

**Ticket text points at code, not just prose.** Six permalinks pinned to
`0c0620d`. The entire argument is that the file already contains the correct
answer three times over; a reviewer should verify that in two clicks.

## Evidence & Data

**Re-derived from scratch, not carried from `d199`:**

- **6 real `EVP_DigestInit*` call sites** in libntech (8 grep hits, 2 are
  comments), all in `libutils/hash.c`. Was 3 unguarded, now **0 of 6**.
  Nothing unguarded elsewhere in the repo.
- **Upstream master `0c0620d` line numbers** — broken: `HashNew` L151,
  `HashFile_Stream` L420, `HashPubKey` L562. Correct siblings:
  `HashNewFromDescriptor` L186, `HashNewFromKey` L251, `HashString` L511.
- **The six-year asymmetry, verified in the tree.** At `f277970`
  (2019-10-03) the site that is now `HashString` already had
  `else { Log(LOG_LEVEL_ERR, …) }`; the sites that are now `HashFile_Stream`
  and `HashPubKey` had **no `else` at all**. Same commit, three functions.
- **Idiom check:** `HashNew` already used `EVP_MD_CTX_create`/`_destroy`, so
  the added `_destroy` on the failure path matches its own function and the
  sibling. No deprecated-API inconsistency introduced.
- **Caller census in cfengine/core** — `HashPubKey`: `lastseen.c:215`,
  `crypto.c:312/570/583`, `cf-execd-runner.c:751`, `sysinfo.c:644`, plus
  includes in `tls_generic.c` and `client_protocol.c`. `HashFile`: 12 sites.
  `HashNew`: **zero callers**, so the NULL return is downstream-safe.
- **Build and test:** `make -j8` exit 0; `make check TESTS=hash_test` → 6/6
  pass. Diff 21 insertions, 3 deletions, one file.
- **No duplicate ticket:** five targeted `summary ~` searches on CFE
  (`EVP_DigestInit failure`, `silent hash failure`, `all-zero digest`,
  `CryptoDeInitialize`, `libntech hash`) all returned zero.
- **All nine URLs in the ticket text fetched → HTTP 200.**

**Process findings from `cfengine/core`'s CONTRIBUTING** (libntech's own is a
one-line redirect to it):

- **§"Use of AI/LLMs in contributions"** permits AI use and states the person
  who reviews, fact-checks and submits **is the author**. The absence of an
  AI-attribution trailer on the upstream commits therefore matches their
  stated policy, not merely our preference.
- PR title format `CFE-1234: Title`; omit the prefix with no ticket, omit
  `(3.12)` for master. Single-commit PRs: title and body match the commit.
- `Changelog:`/`Ticket:` go in the **commit**, never the PR description.
- Outside contributors land PRs routinely — #268 (Bastian Triller, Placetel),
  #260 (Martin Hart).

**Jira auth state:** token declared and set via the broker
(`ATLASSIAN_CFENGINE_API_TOKEN`), well-formed — 192 chars, `ATATT` prefix, no
whitespace. `GET /rest/api/3/myself` → **401** with both candidate emails.
Anonymous `createmeta` returns an empty `projects` array. `sudo-secretspec
doctor` → OK; `template-check` → exit 1 (expected drift).

**The drift's one real consequence:**
`~/ops/stayturgid/control/bin/publish_secrets.sh:11` runs
`sudo -n "$WRAPPER" source-template-check`, which is a `cmp -s` of the same
two files — so **fleet secret publishing from stayturgid fails until it is
reconciled.** Nothing upstream is affected.

## Operator Feedback

- **"Stop you are doing it wrong I am 90% sure"** — on the direct `secretspec`
  use. Correct. Then pointed at the skill rather than explaining, which found
  it faster than any amount of my reasoning would have.
- **"Let's put off doing intense work until the next time window"** — quota
  discipline; a timer was set rather than starting the expensive pass.
- **"We can totally create a libntech fork, I'm not sure why you think we
  can't, I may have mistyped."** Worth preserving the correction to *my*
  framing: `d199` recorded that no fork existed and that creating one is a
  gated action, which I relayed in a way that read as a capability claim.
- **"It may be easiest for you to just feed me text"** then **"No you can use
  the token"** then, after the 401s, **"this isn't worth the time."** Pattern:
  the operator will spend a bounded amount on a side-quest and then cut it.
  Cut cleanly; don't keep offering to chase.
- **"Oh I thought you'd just do a PR against our github fork"** — better than
  my plan, and it dissolved the ticket/PR deadlock.
- **"That ticket doesn't have any URLs to the actual fixes/diffs we made"** —
  a real gap I had shipped past.
- **Drift is explicitly not tendcf's problem**: "copy the situation to the
  clipboard, I'll feed it to the stayturgid agent."
- Standing, carried: no AI-attribution trailer on CFEngine commits; tendcf's
  own commits do carry one.

## Where We're Going

1. **THE NEXT ACTION: nothing until 21:10**, when a one-shot timer fires the
   deferred schema reconciliation pass. **That timer is session-only and dies
   with this session** — if this session ended, re-create it or just run the
   work. Its prompt is the full brief; the job is to write the reconciliation
   over the three goal-file opinions as a **new** doc under
   `docs/architecture/`, never editing the three opinion files. Confirm
   reasoning effort with the operator first (the panel ran at xhigh) and
   re-check quota with `cswap list`.
2. **When the operator returns with a `CFE-NNNN`:** amend the
   `Ticket: CFE-XXXX` placeholder in `da7d3d9`, `git push --force-with-lease
   fork silent-digest-failure`, then open the upstream PR against
   `NorthernTechHQ/libntech` titled `CFE-NNNN: Handle digest initialization
   failure when hashing`. **That last step trips the gate — surface it for
   approval, do not route around it.**
3. **If Jira stays blocked**, propose the ticketless fallback: strip both
   `Changelog:` and `Ticket:` from the commit (they travel together) and open
   the PR with a bare title.
4. **Decide the ticket story for PRs 1 and 2** on `djbclark/core`
   (`simulate-keep-chroot` `5dbd295f6`, `simulate-json` `071f85987`). Both
   still carry `Ticket: CFE-XXXX`. Open operator decision, unchanged from
   `d199`.
5. **Then the batched doc work, three items:** de-stale
   `docs/paper/tendcf-architecture-paper.md` (capability vocabulary ~line 311,
   open question 8.8); fix the guide §16 `host_specific.json` example, which
   loads nothing because its top-level `data` key is skipped; fix the guide's
   false claim that YAML is a valid Augments input.
6. Optional: fix the `-D` false positive in
   `~/.claude/hooks/upstream_review_gate.sh`.
7. Optional cleanup: pane `w1H:pQ` (schema-gemini) is still alive.

**Traps, unchanged and still live:**

- `git status` in `~/src/cfengine-core` shows ` M libntech`. **Do NOT commit
  it** — it would bind PR 3 into PR 2's branch; they are independent PRs
  against two different repos.
- Neither of PR 2's tests can catch a regression of the silent-zero-digest
  bug (unit tests bypass `GenericAgentFinalize()`; the acceptance test
  normalizes `sha256` away). Verify with a live run.
- Do not trust herdr's `agent_status: done` — read the pane.

## Quick Start

```sh
# Tier 1 pointer
~/.claude/hooks/handoff-tools/.venv/bin/python \
  ~/.claude/hooks/handoff-tools/session_log.py read \
  --state-root ~/.local/state/handoffs --dir ~/.local/state/handoffs/tendcf/main

# The filing package — ticket text, PR shape, verification record
cd ~/src/tendcf && $EDITOR docs/architecture/libntech-pr3-digest-init-filing-package-2026-08-15.md

# PR 3
cd ~/src/cfengine-core/libntech
git log -1 --format=%B da7d3d9        # commit body == the upstream PR body
git diff origin/master --stat         # 21 insertions, 3 deletions
gh pr view 1 -R djbclark/libntech     # the fork review PR

# Rebuild + retest
cd ~/src/cfengine-core/libntech && make -j8 && cd tests/unit && make check TESTS=hash_test

# Credentials — ALWAYS through the broker, never `secretspec` directly
sudo-secretspec doctor
sudo-secretspec check --reason "<why>"
# get/export STREAM VALUES to stdout — parse, never echo

# The reconciliation inputs (the deferred 21:10 job)
cd ~/src/tendcf && ls docs/architecture/goal-file-schema-opinion-*.md
#   GOAL-FILE-SCHEMA-BRIEF.md and e1-adjudication-xhigh-2026-08-15.md are the brief

# Schema lint — MUST be run this way; bare python3 fails on jsonschema
uv run --with jsonschema bin/schema_lint.py
```
