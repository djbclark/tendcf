---
schema_version: 1
handoff_id: 6d19
parent_handoff_ids: [9692]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 222da45513eee86a1f412668d5fcdbad8e9415e7
created_at: 2026-08-18T20:14:35-0400
writer: claude-code
---

# Handoff — the generic bundle shipped, two backlog issues filed

## The Goal

Resumed via `/baton` from `9692` (tendcf@29825c8). Checked upstream PR/Jira
status first (routine, nothing new — see Where We Are), then the operator
asked to get back to "our actual schema lint work" — i.e. stop the ~2-day
CFEngine bug-hunting detour and resume tendcf's own architecture work. That
meant reading back through the handoff chain (not guessing) to find what
was actually still open, landing on `7c19`'s "Where We're Going" item 2:
**the generic bundle** — the `.cf` that reads `tendcf_service`/
`tendcf_interlock` and renders CFEngine promises from `state`. Named there
as "the biggest remaining deliverable, wants a full session." It was.

## Where We Are

master `222da45`, clean, pushed. One commit this session
(`policy: the generic bundle (v1, launchd only)`, 3 files, +212):

- `policy/tendcf_services.cf` — the bundle itself
- `policy/templates/launchd.plist.mustache` — plist render target
- `examples/policy/host_specific-interlock-blocked.json` — new fixture,
  a genuinely-failing interlock (`/bin/false`), for proving refusal for
  real rather than simulating it

Two issues filed on `frdminc/tendcf` (not code, but real backlog state a
future session needs to see):

- **[#3](https://github.com/frdminc/tendcf/issues/3)** — patch overlay
  for libntech/cfengine defects load-bearing on this bundle (mustache,
  JSON double-decode, CMDB one-bad-entry), with exact commits/branches
  and a sunset condition (drop each patch when its PR merges).
- **[#4](https://github.com/frdminc/tendcf/issues/4)** — nix2cf is
  correctly blocked on build-order Step 2 (Android/Termux, not started),
  not merely "forgotten" as the last three handoffs implied. Step 1
  (macOS services adapter) is what this session's bundle actually is.

`schema-lint`/`xref_lint` unaffected by any of this (re-measured after
adding the new fixture dir, not assumed): `schema-lint: OK (8 schemas, 59
negative fixtures, 6 byte-class fixtures, 27 projection fixtures)`;
`xref_lint: 0 findings`.

**Upstream status checked at session start, nothing new to act on:**
nickanderson (cfengine/core maintainer) functionally confirmed
cfengine/core#6302 works; `mender-test-bot` posted a generic "pipeline
error" comment on libntech#293/294/296/297/298 but `gh pr checks` shows
no actual checks attached — not gating anything. CFE-4736 (getopt RFC)
still open, unassigned, no maintainer reply. No worktrees deletable yet
(nothing merged).

## What We Tried

The `.cf` syntax was worked out empirically against a real build, not
from memory or docs — several assumptions were wrong on the first try,
and each is expensive enough to rediscover that it's recorded in full:

1. **CMDB scope is `data:variables.<key>`, not `def.<key>`.** First draft
   assumed `host_specific.json`'s `vars` object loads through the same
   `def.*` scope as `def.json` augments. Wrong loader entirely —
   `LoadCMDBData`/`ReadCMDBVars` (`libpromises/cmdb.c`), not
   `LoadAugmentsData`. Confirmed by reading `cmdb.c:GetCMDBVariableRef`:
   a bare (unprefixed) CMDB key defaults to namespace `data`, scope
   `variables`. Caught by running with `-vv` and grepping for
   "Installing CMDB data container variable" in the real log line, not
   by reading source alone.
2. **Data containers cannot be assigned to an indexed variable name.**
   `"cmd[$(id)]" data => '...';` fails with "Cannot assign a container to
   an indexed variable name... Should be assigned to 'cmd' instead" —
   reproduced on a minimal synthetic file before touching the real
   bundle. This blocks the obvious "build a per-key container array"
   idiom entirely; containers only live in bare names.
3. **Neither `@(x[y])` nor bare `$(x[y])` are valid non-scalar rvalues.**
   Both give a hard parse error ("Invalid r-value type") the moment a
   bracket-indexed path is used as a whole attribute value (e.g.
   `arglist => $(container[$(id)][path]);`). Bracket-path indexing only
   works *inside a quoted string* (interpolation) or *as a function
   argument string* (see next item) — never as a bare rvalue token.
4. **The working idiom: pass the bracket-path as a plain string to a
   function that resolves variable names.** `join(" ",
   "container[$(id)][path]")` and `getvalues("container[$(id)][path]")`
   both work — the function receives the *path text*, not a `$()`
   expansion of it, and resolves it internally. Confirmed with a minimal
   `cf-agent` run (not just `cf-promises` syntax-only) before trusting it.
5. **`template_data` needs `mergedata("path")`, not a raw string.**
   `storejson()` returns `CF_DATA_TYPE_STRING` and fails the attribute's
   static type check ("Function does not return the required type") even
   though a raw string literal is accepted syntactically and then fails
   at runtime with a JSON-parse error. `mergedata()` returns
   `CF_DATA_TYPE_CONTAINER` and is the one that actually renders.
6. **`commands:` promise `arglist` cannot take a container-typed
   function result either** — same static-type rejection as above, even
   from `mergedata()`. Its constraint is a real `CF_DATA_TYPE_STRING_LIST`,
   and containers don't implicitly coerce. Worked around by NOT using
   `arglist` at all for the interlock's `pre_action`: built a
   shell-joined command string via `join()` into a scalar-valued indexed
   array (`pre_action_cmd[$(id)]`, string values ARE fine in indexed
   arrays — only containers aren't), and ran it with `useshell => "true"`.
   Named as a real, live limitation in the bundle's own comments: argv
   elements containing spaces or shell metacharacters aren't isolated.
   Acceptable for now because `pre_action.command` is our own
   schema-validated output, not attacker input — but it's a limitation,
   not a non-issue.
7. **`edit_template` + `template_method => "mustache"` does NOT do
   CFEngine `$()` substitution inside the template file.** First attempt
   put `$(service_ids)` directly in the mustache template for the plist
   `Label`; it rendered as the *literal string* `$(service_ids)`, not
   the value. Fixed by injecting the id into `template_data` itself
   (`mergedata("path", '{"id": "$(service_ids)"}')`, two-arg merge) and
   using `{{id}}` in the template instead. Caught by actually reading the
   rendered output file, not by trusting the dry-run "Should create"
   line.
8. **CFEngine class names reject the characters the schema allows in
   ids/bundle tags.** A hyphenated interlock id (`caddy-config-valid`)
   used directly in a class name fails hard: "Context string is
   invalid/out of range." Fixed with `canonify()` — but nested
   `$(canonify($(id)))` inline silently produced garbage (no error, just
   didn't work); had to go through an intermediate scalar variable
   (`"canon" string => canonify("$(id)");`) instead. This is the second
   "silently wrong, not an error" trap this session hit (see also #1's
   note on trusting log output over source reading).
9. **`tidy` isn't a built-in body** — it's masterfiles stdlib, not
   available without `inputs`-ing the standard library. Wrote a
   two-line local `body delete tendcf_tidy` instead of pulling in the
   stdlib dependency for one attribute.

**Test harness built from scratch, also worth recording:** the libtool
wrapper scripts (`cf-agent`, `cf-promises`, `cf-key`) in
`~/src/core-cmdbkey/{cf-agent,cf-promises,cf-key}/` only resolve their
`libpromises.3.dylib` correctly when run from their own build directory
or with `DYLD_LIBRARY_PATH=~/src/core-cmdbkey/libpromises/.libs`
exported explicitly — copying the binaries elsewhere breaks dyld
resolution even via symlink, because the install-name is hardcoded to a
prefix (`~/opt/cfengine-dev-4719/lib/...`) that was never actually
installed. A real standalone `cf-agent -f <file>` run additionally needs:
a `CFENGINE_TEST_OVERRIDE_WORKDIR` (matching the acceptance-test
harness's own convention — grepped `tests/acceptance/testall` to confirm
rather than guessing the env var name); `ppkeys/` at mode 700 (`cf-agent`
fatal-errors otherwise); a key pair from `cf-key`; a `body common control`
naming a real `bundlesequence` (a bare `-f` on a library file with no
control body falls through to CFEngine's failsafe bootstrap and silently
ignores the target file entirely — the failure mode looks like network
bootstrap errors, not "wrong invocation").

## Key Decisions

- **Bundle-scoped interlock refusal without literal per-service
  `bundle agent`s.** The schema's `interlock_entry.bundle` field plus the
  guide's §7 "Interlocks are not edges... Bundle-scoped refusal" together
  imply refusal at the granularity of a whole CFEngine bundle — but
  nothing generates a separate `bundle agent` per service (that would
  defeat "generic"). Resolved as: one guard class per distinct `bundle`
  tag (`interlock_blocked_<tag>`), computed once per interlock and
  checked by every entry carrying that tag via `ifvarclass`. Reproduces
  the same observable refusal without dynamic bundle generation CFEngine
  doesn't support. Recorded in the bundle's own header comment with the
  citation, not left implicit.
- **v1 is launchd-only**, matching every worked example in the repo and
  the operator's own dev machine (the only one testable today). systemd/
  runit are schema-supported but named as explicit follow-up, not built.
- **`env` rendering is deliberately NOT in the v1 template.** Mustache
  can't cleanly iterate a JSON *object's* key/value pairs (sections push
  context for nested access, they don't give you `{key, value}` pairs
  the way array iteration does), and the fixture only has one env
  entry, which isn't enough to design the real mechanism against. Left
  out rather than special-cased for exactly one key. Named in the commit
  message and issue #3's context, not silently dropped.
- **No CI wiring for `cf-promises`/`cf-agent` this session.**
  `check.yml` only has `uv` (Python). Verification instead used the
  already-built binaries in this week's upstream worktrees
  (`~/src/core-cmdbkey`), which are one-per-fix and slated for deletion
  once their PRs merge (see #3's own point 4) — a real gap, named, not
  quietly worked around as if it were solved.
- **Filed two issues rather than only writing prose in this handoff**,
  per the operator's explicit ask this session: concrete multi-session
  backlog items (things a decision or action is owed on, not just
  narrative) go in `frdminc/tendcf` issues now; the handoff/register
  system stays for narrative and status, which the operator confirmed is
  already working well for me (I hit no retrieval friction this
  session — found everything via the Tier-1 log and
  `upstream-register.md`, no Hindsight gap identified).
- **nix2cf issue reframed the situation rather than restating it.**
  The prior handoffs' framing ("approved scope, never touched, don't
  forget a third time") was superseded by reading
  `architecture-DEFINITIVE-v3.md`'s own build-order table: nix2cf (Step
  3) explicitly needs Steps 1 and 2, Step 2 (Android/Termux) hasn't
  started, so nix2cf being untouched is the dependency chain working as
  designed, not drift. This is a genuine correction to carry forward,
  not just a duplicate of the old "revisit nix2cf" note.

## Evidence & Data

- `schema-lint: OK (8 schemas, 59 negative fixtures, 6 byte-class
  fixtures, 27 projection fixtures)` — unchanged, re-measured after
  adding `examples/policy/`.
- `xref_lint: 93 live documents linted, 82 frozen skipped, 839 sections
  indexed across 175 documents, 0 finding(s)`.
- `cf-promises -f policy/tendcf_services.cf` — exit 0 (via
  `~/src/core-cmdbkey/cf-promises/cf-promises`, with
  `DYLD_LIBRARY_PATH=~/src/core-cmdbkey/libpromises/.libs`).
- Real (non-dry-run) `cf-agent` run against `examples/host_specific.json`:
  `com.tendcf.caddy.retired` (state=absent) correctly skipped, file
  doesn't exist, "Would execute script '/bin/launchctl unload
  .../com.tendcf.caddy.retired.plist'"; `com.tendcf.caddy.main`
  (state=present) correctly gated behind its own interlock in real
  dry-run (interlock can't be classified without actually running, which
  dry-run won't do — expected conservative behavior, not a bug); forcing
  `interlock_ok_caddy_config_valid` via `-D` then shows "Should create
  file '/Library/LaunchDaemons/com.tendcf.caddy.main.plist'" and "Would
  execute script '/bin/launchctl load -w .../com.tendcf.caddy.main.plist'".
- Rendered plist content inspected directly (not just "Should create"):
  valid, `plutil -lint` clean XML with correct `ProgramArguments` array,
  `RunAtLoad`/`KeepAlive` booleans, and `Label` (via the `{{id}}`
  injection fix).
- Real (non-dry-run) run against `examples/policy/host_specific-interlock-blocked.json`
  (genuinely-failing `/bin/false` pre_action): `interlock_ok_*` never
  defined, `interlock_blocked_gated` set as a real (not simulated)
  private class, both the plist-create and `launchctl load` promises
  skipped, and the `reports:` promise fired: "R: tendcf: interlock
  'gate-always-fails' not satisfied, bundle 'gated' refused".
- **Discrimination, matching this repo's own mutation-testing
  discipline** (backed up the good file first, restored after each):
  - Mutation 1 — inverted `strcmp(..., "present")` to `"absent")`:
    real dry-run then wants to *unload* `com.tendcf.caddy.main` (the
    entry that's actually present) and marks `com.tendcf.caddy.retired`
    as the private "present" class — proves the dispatch is load-bearing.
  - Mutation 2 — stripped `!interlock_blocked_...` from the two
    interlock-guarded `ifvarclass` conditions: real run against the
    blocked fixture then wrongly proceeds — "Should create file
    '/Library/LaunchDaemons/com.tendcf.gated.main.plist'" despite the
    interlock genuinely failing — proves the guard is load-bearing.
  - Both reverted; `diff` against the pre-mutation backup confirmed
    clean restoration each time.

## Operator Feedback

- "I mean if we are finally through with all the cfengine bugs we can
  get back to our actull schema lint work we were doing before" — the
  instruction that reframed the whole session: stop the upstream detour,
  resume tendcf's own architecture backlog via the handoff chain, not
  from memory or a guess at "what we were doing."
- "Don't guess where we were, go back in time in the handoff docs." —
  mid-turn correction when the first approach (reconstructing from `git
  log` commit messages alone) risked skipping the actual handoff
  document's stated next-steps. Corrected by reading `7c19` directly.
  **Durable takeaway for future sessions: when resuming into "what's the
  real next work," read the handoff prose itself, don't infer it from
  commit message archaeology — the handoff is written specifically to
  answer that question and commit messages aren't.**
- Confirmed the CFEngine bug-hunt's origin story: agreed it wasn't
  `schema_lint.py` directly but the architecture's anticipated reliance
  on mustache templating — a correction to my own first framing that the
  operator caught and I fixed in the same turn.
- On process: explicitly floated using GitHub issues more for tendcf's
  own backlog and offered to expand Hindsight config if it would help me
  track things. Answered honestly rather than reflexively agreeing: the
  Tier-1/Tier-2/register system worked well this session with zero
  friction, Hindsight hasn't been used for tendcf at all and no gap was
  identified, and the concrete gain from issues is durability independent
  of any one session's context — which the two new issues now provide
  for the overlay plan and the nix2cf decision specifically. Confirmed
  via `AskUserQuestion`: yes to filing both, yes to using issues for
  concrete backlog items going forward (register/handoffs stay for
  narrative).

## Where We're Going

1. **THE NEXT ACTION: work `frdminc/tendcf#3`, the patch overlay.**
   Mechanically: one merge commit combining libntech's
   `fix/json-double-decode` and `fix/mustache-minor-defects` tips onto
   `0c0620d`, point cfengine/core's libntech submodule at that commit,
   build core at `8f0076b81`. Not started; the issue has the exact
   commits/branches. Picked over the alternatives below because it's the
   smallest, most self-contained unit of work and unblocks confident
   local testing of the bundle without depending on the ephemeral
   upstream worktrees. Not a hard requirement to do first — the operator
   left this genuinely open — but it's the recommended entry point.
   Other real options, not yet chosen:
   - Flesh out the generic bundle's named gaps (issue-worthy but not yet
     filed): `env` rendering in the mustache template, systemd/runit,
     the unit-writer extra-entry detector, real secretspec env
     resolution.
   - Periodic upstream PR/Jira check (routine, low urgency — nothing new
     as of this session's start-of-session sweep).
   - `frdminc/tendcf#4` stays closed/blocked until Step 2 (Android/
     Termux) has real code — don't start nix2cf before then.
2. Delete upstream worktrees as their PRs close: core-cmdbkey,
   core-mountleak, core-cmdbnull, core-cmdbdotted, core-evalint,
   core-defnull, libntech-doubledecode, libntech-mustachetest,
   libntech-mustachefix. None mergeable yet as of this session.
3. Unrelated, long-carried: confirm `track-issue-activity.yml`'s
   Discussion path fires in site-djbclark; `~/src/cfengine-core` still
   shows a dirty `libntech` submodule — do NOT commit it, libntech#291/
   cfengine/core#6293/#6294 are already filed from it.

## Quick Start

```bash
cd /Users/djbclark/src/tendcf && git log --oneline -5

# Re-verify the bundle (needs the core-cmdbkey worktree's binaries —
# still present as of this handoff, will need re-staging once deleted):
export DYLD_LIBRARY_PATH=/Users/djbclark/src/core-cmdbkey/libpromises/.libs
mkdir -p /tmp/tendcf_test_workdir/{data,bin,ppkeys} && chmod 700 /tmp/tendcf_test_workdir/ppkeys
ln -sf /Users/djbclark/src/core-cmdbkey/cf-promises/cf-promises /tmp/tendcf_test_workdir/bin/cf-promises
ln -sf /Users/djbclark/src/core-cmdbkey/cf-agent/cf-agent /tmp/tendcf_test_workdir/bin/cf-agent
ln -sf /Users/djbclark/src/core-cmdbkey/cf-key/cf-key /tmp/tendcf_test_workdir/bin/cf-key
CFENGINE_TEST_OVERRIDE_WORKDIR=/tmp/tendcf_test_workdir /tmp/tendcf_test_workdir/bin/cf-key
cp examples/host_specific.json /tmp/tendcf_test_workdir/data/host_specific.json
cat > /tmp/tendcf_driver.cf <<'CFEOF'
body common control { bundlesequence => { "tendcf_services" }; inputs => { "/Users/djbclark/src/tendcf/policy/tendcf_services.cf" }; }
CFEOF
CFENGINE_TEST_OVERRIDE_WORKDIR=/tmp/tendcf_test_workdir /tmp/tendcf_test_workdir/bin/cf-promises -f /tmp/tendcf_driver.cf
CFENGINE_TEST_OVERRIDE_WORKDIR=/tmp/tendcf_test_workdir /tmp/tendcf_test_workdir/bin/cf-agent -f /tmp/tendcf_driver.cf -K --no-lock --dry-run -D interlock_ok_caddy_config_valid

# The two filed issues:
gh issue view -R frdminc/tendcf 3
gh issue view -R frdminc/tendcf 4

# Routine upstream check:
gh pr list -R cfengine/core --author djbclark --json number,title,state,reviews,comments,updatedAt
gh pr list -R NorthernTechHQ/libntech --author djbclark --json number,title,state,reviews,comments,updatedAt
```
