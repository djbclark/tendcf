---
schema_version: 1
handoff_id: 9a80
parent_handoff_ids: [2939]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: d88e4f733227597683cedd39d66b44e4c50f74b0
created_at: 2026-08-15T12:58:09-0400
writer: claude-code
---

# Handoff — E1 re-adjudicated at xhigh; CFEngine forked for two upstream PRs

## The Goal

Three things, in the order they came up:

1. **Re-run the E1 adjudication with Fable 5 at `xhigh`**, which the previous
   session intended but could not do (the Agent tool has no effort parameter, so
   it silently ran at the session's `high`). The operator asked explicitly to
   **double-check that Fable was actually running in the intended mode** before
   spending the run, and to improve the prompt rather than re-issue it verbatim.
2. **Fork CFEngine and investigate how hard it will be to get machine-readable
   `--simulate` output** — the thing tendcf's consent layer needs. The operator's
   framing: we probably cannot convince upstream to do the work, but if we do it,
   they may integrate and maintain it. **The fork is temporary; carrying a fork
   is the failure mode, not the plan.**
3. **Put a hard gate in front of anything upstream can see**, so the operator
   reviews Jira tickets and PRs before they exist.

## Where We Are

`master` at `d88e4f7`, clean, in sync with origin. Nothing in flight.

**E1 is settled twice over.** Two independent passes, different models, both
adopt Model B. `docs/architecture/e1-adjudication-xhigh-2026-08-15.md` (552
lines, 8 sections) is the new one; the prior `e1-adjudication-2026-08-15.md` is
untouched so both stay on record.

**CFEngine work is fully staged but no code is written yet.** The fork exists,
builds, runs, and the plan is recorded in three GitHub issues that are readable
cold. Nothing has been sent upstream.

- Fork: <https://github.com/djbclark/core> (issues enabled, which forks disable
  by default)
- Clone: `~/src/cfengine-core`, `origin`=fork, `upstream`=cfengine/core, at
  `17eb78e6d`
- Built and installed to `~/opt/cfengine-dev`; `libntech` submodule initialized
- <https://github.com/djbclark/core/issues/1> — umbrella
- <https://github.com/djbclark/core/issues/2> — PR 1: retain the changes chroot
- <https://github.com/djbclark/core/issues/3> — PR 2: JSON rendering

**The upstream gate is live and tested** (see Key Decisions).

## What We Tried

Failed approaches, chronological, because rediscovering these costs real time.

**Verifying Fable's effort by asking Fable.** The smoke-test agent reported
"model `claude-fable-5`, effort `xhigh`, stated in system context" — which is
worthless as evidence, because the `fable-deep` agent's own prompt body opens
with "You are running as Claude Fable 5 at `xhigh` effort." Pure circularity.
The fix was to read the **harness-written** records instead:
`~/.claude/projects/<proj>/<session>/subagents/agent-<id>.jsonl` stamps
`model` and `effort` on every assistant turn. Those are written by the runtime,
not the model.

**Grepping the CLI binary for effort handling** first returned 42KB of noise
(every `output_config={"effort": ...}` in the bundled claude-api docs). Narrowing
to `strings | grep -oE "effort[A-Za-z]*" | sort | uniq -c` then locating the
schema doc string was what actually confirmed `effort` is a real subagent
frontmatter key with `xhigh` in its enum.

**`WebFetch` on `cfengine.com/product/supported-versions/`** returned an empty
page — no release schedule obtainable that way. The version question was
answered later, correctly, by building the binary.

**Jira REST API v2 is gone.** `/rest/api/2/search` returns "The requested API
has been removed." The working endpoint is
**`/rest/api/3/search/jql`**, and it is anonymously queryable — no account
needed to read the CFE project.

**`git submodule update --init libntech --quiet`** fails with "pathspec
'--quiet' did not match any file(s)" — flag must precede the path, or be
omitted.

**Copying `cf-promises` out of the build tree gets a libtool wrapper script,
not a binary.** First attempt produced `.libs/cf-promises does not exist / This
script is just a wrapper`. Copying `.libs/cf-promises` directly then failed with
a dyld error for `libpromises.3.dylib`. **The fix is `make install` and using
the installed tree.**

**The first simulate run fell back to failsafe policy** because `cf-promises`
was missing from `$WORKDIR/bin` — the agent will not run your policy at all
without it, and the failure is 30 lines of unrelated policy-hub errors that look
like a networking problem.

**The first test policy used stdlib bodies** (`edit_defaults => empty`,
`insert_lines(...)`) and died on `Undefined body empty with type edit_defaults`.
A stdlib-free policy using the built-in `content =>` attribute works.

**Inferring the release train from `CHANGELOG.md` was wrong.** Its top section
is `## 3.28.0`, so issue #1 originally said the target release is 3.28.0. The
built binary reports **`CFEngine Core 3.29.0a.17eb78e6d`** and `CFVERSION` says
`3.29.0a` — 3.28.0 is the section being *closed*. Corrected in issue #1. This is
the second time in this chain that source/document reasoning about CFEngine beat
running the thing and lost.

**`ask` permission rules would have been a silently useless gate.**
`~/.claude/settings.json` has `"defaultMode": "bypassPermissions"`, under which
`ask` rules never prompt. Only `deny` holds. Prefix rules were also inadequate:
they match only the start of a command (so `cd /tmp && gh pr create` evades
them) and cannot distinguish a fork from an owned repo.

## Key Decisions

**Verify subagent effort from harness records, never self-report.** Chosen after
the circularity above. Rejected: trusting the agent's statement; rejected:
setting up a `SubagentStop` hook to capture `effort` (heavier, and mid-session
hook changes may not load).

**Three-part prompt, with Part 1 unanchored.** The re-run was explicitly
forbidden from opening the prior verdict until it had written its own. Rejected:
re-issuing the original prompt (would mostly reproduce the prior verdict at
higher cost); rejected: a purely anchored audit of the prior verdict (anchoring
would have destroyed the convergence signal, which was the entire point). Part 3
forced closure on the six design questions blocking the schema family, on the
reasoning that a verdict leaving them open unblocks nothing.

**Two separate PRs, PR 1 (chroot retention) first as a deliberate probe.** They
are complementary, not redundant — the chroot carries the would-be *bytes*, the
JSON carries the would-be *change set*, and neither substitutes for the other.
PR 1 is small enough to be judged in one pass, so putting it through the whole
pipeline (Jira, CLA, CI, review cadence) reveals what upstream is like at low
stakes. **Known risk:** landing retention first invites "JSON is unnecessary
now." Mitigation is one Jira ticket describing both pieces, referenced from both
PRs. Rejected: a single combined PR; rejected: JSON first.

**Gate scope: only repos not owned by `djbclark`.** The operator chose this over
the literal "every PR everywhere" reading, because a blanket deny would put a
hard stop in the middle of the prompt-free ops-djbclark release workflow
(`Bash(gh pr merge *)` is globally allowed, and `gh pr create *` / `gh pr merge
*` are in `autoMode.allow`).

**A `PreToolUse(Bash)` hook, not permission rules.** Reasons under What We Tried.
Reads are deliberately allowed — `gh pr view/list/diff`, `gh repo fork`, and
Jira REST GETs are how this research gets done.

**Issue split: #1 umbrella, #2/#3 per PR, each with an ELI5 section** at the
operator's request. Rejected: one ticket carrying everything.

**`CLAUDE.md` in the fork is excluded via `.git/info/exclude`.** Rejected:
committing it — it could leak into an upstream PR, which is exactly the class of
mistake the gate exists to prevent.

**The Northern.tech contributor statement is accepted** (operator decision):
joint copyright assignment plus patent grant, not a bare DCO.

## Evidence & Data

**Fable 5 xhigh run** — 231,267 subagent tokens, 19 tool uses, 685,268 ms
(~11m24s), zero refusals despite the trust/consent corpus. Effort confirmed as
`('claude-fable-5', 'xhigh')` on every assistant turn in the harness transcript,
checked both on a 23,670-token smoke test and again on the live run. For
comparison, the prior session's run at `high` cost 147,328 tokens.

**Its findings, beyond agreeing on Model B:** it caught a real internal
contradiction in the prior verdict — §6.2 mandates hunk attribution in the diff
format, §7 bakes in both attribution and dependency groups, §6.4 says "choose
one," and §5.2 recommends device-side diff computation, but **a device holds the
two goal files and not the source layers, so it cannot attribute hunks**. I
verified this against the prior document's text; the contradiction is real. Its
resolution: attribution is a query (`explain-hunk` via re-render-and-subtract),
never a field. It also named four residues the prior §6 list missed, including a
goal-file **completeness contract** so "silent because unchanged" and "silent
because not-yet-migrated" cannot read alike — which neither pass caught first
time.

**CFEngine source facts, all verified against `17eb78e6d`:**

- Four record files: `libpromises/changes_chroot.h:28-31` — `/changed_files`,
  `/renamed_files`, `/kept_files` (length-prefixed strings), `/pkgs_ops` (CSV:
  op, name, arch, version, with op from the `ChrootPkgOperationCode` enum at
  `cf-agent/simulate_mode.h:38-43`).
- **The renderer runs before cleanup.** `cf-agent/cf-agent.c:392-428` dispatches
  the manifest/diff renderers; `cf-agent.c:435` then calls
  `CallCleanupFunctions()`, which runs `DeleteChangesChroot` (registered
  `libpromises/generic_agent.c:1634`, deletes at `:1793`). **This corrects the
  earlier tendcf note's framing** — the chroot teardown is not an obstacle to an
  in-process JSON renderer, only to external consumers.
- Chroot path is `$statedir/<pid>.changes` (`generic_agent.c:1785`), already
  logged at `LOG_LEVEL_WARNING` (`generic_agent.c:1635`).
- JSON API already in-tree at `libntech/libutils/json.h` (`JsonObjectCreate`,
  `JsonArrayCreate`, `JsonObjectAppendString`, `JsonWrite`) → **single-repo
  change**, no coordinated libntech PR.
- **`--simulate=diff` is broken out of the box on macOS.** `RunDiff()` at
  `cf-agent/simulate_mode.c:363-364` builds the diff path from `GetBinDir()`,
  **not `$PATH`**. Neither the `make install` tree nor the Homebrew `cfengine`
  package puts a `diff` there. Observed error: `Couldn't run
  '.../workdir/bin/diff'. (execv: No such file or directory)`. **Unverified:
  whether Linux packages ship one** — the finding is about the lookup path.

**Simulate behaviour, observed not inferred:** real files untouched (modified
file kept `original line`, created file never appeared outside the chroot);
chroot deleted after exit (nothing matching `*.changes` in the state dir);
`--simulate=manifest` works where `diff` mode fails.

**Upstream context:** `cfengine/core` has **GitHub Issues disabled**
(`has_issues: false`) — upstream feature requests go to the Jira plus
dev-cfengine, per `CONTRIBUTING.md`. No existing ticket requests structured
simulate output (searched `simulate`, `machine-readable`, `JSON output`).
Nearest: CFE-1929 "Console output greppability" (open since 2015), CFE-3505,
CFE-3548. Simulate mode was built Nov 2020–Mar 2021 and went quiet; **PR #6242
(ENT-3787, merged 2026-07-23) deleted the aspirational audit-mode acceptance
tests** because those messages "were never implemented."

**Build recipe that works** (`~/src/cfengine-core`), after
`brew install autoconf automake` (GNU libtool was already present as
`glibtool`):

```sh
NO_CONFIGURE=1 ./autogen.sh
./configure --prefix="$HOME/opt/cfengine-dev" \
  --with-openssl=/opt/homebrew/opt/openssl@3 \
  --with-pcre2=/opt/homebrew/opt/pcre2 \
  --with-lmdb=/opt/homebrew/opt/lmdb \
  --with-libyaml=/opt/homebrew/opt/libyaml \
  --enable-maintainer-mode
make -j"$(sysctl -n hw.ncpu)" && make install
```

Build exit 0, no errors. Binary reports `CFEngine Core 3.29.0a.17eb78e6d`.

**Gate test results:** 17 cases, all correct — 7 denied (`gh pr create -R
cfengine/core`, bare `gh pr create` in the fork, `cd /tmp && gh pr create` in
the fork, `gh pr merge -R cfengine/core`, `gh issue comment -R cfengine/core`,
`curl -X POST ...atlassian.net -d`, `composio execute JIRA_CREATE_ISSUE`) and 10
passed (including `gh pr merge -R djbclark/stayturgid`, `gh pr view -R
cfengine/core`, `gh repo fork`, and a `--data-urlencode` Jira GET). Then
live-fire: an anonymous Jira POST — harmless 401 had the gate been dead — was
blocked by the running hook.

**Tests run:** no tendcf test suite was run this session (documentation and
investigation only). CFEngine's own suites were not run; only a hand-built
simulate smoke test.

## Operator Feedback

- **"Double check that fable 5 is actually running in the mode you want."** Acted
  on before spending the run; this is the standing expectation, and it follows
  the prior session's mistake of launching at the wrong effort.
- **"For any upstream work that cfengine will need to accept, please tend to use
  more advanced models and thinking levels; we want code that not only works, but
  that is understandable and looks pretty to humans, and follows the style of the
  rest of the project's code."** Saved as memory `upstream-code-needs-top-models`.
- **"You can brew install or otherwise install anything you need."** Standing.
- **"The AUTHORS copyright is fine with me."**
- **"Include a reddit explain it like i am 5 section"** in each ticket.
- **"Put a hard gate that you need to ask me before creating or modifying any
  northerntech.atlassian.net ticket or DPR or PR. I want to review things before
  they are seen by upstream."**
- On the fork's purpose: *"The plan is to try to avoid maintaining our own fork,
  but we need the fork temporarily to get there."*

## Where We're Going

1. **THE NEXT ACTION: prototype PR 1 — chroot retention — on a branch of
   `~/src/cfengine-core`.** Read <https://github.com/djbclark/core/issues/2>
   first; it carries the implementation sketch and three design points. Per
   operator instruction, write it with `Agent(subagent_type: "fable-deep")` at
   `xhigh`, and **verify the effort from the harness records before trusting the
   run** (see Quick Start). Do not open a PR — the gate will stop you, and that
   is intended.
2. Get a maintainer opinion on the two questions issue #2 flags as theirs to
   answer: retained chroots accumulate as `$statedir/<pid>.changes`, and
   retention has a security cost that deletion currently prevents.
3. **Open the upstream Jira ticket** covering *both* PRs — the operator created a
   `northerntech.atlassian.net` account via Google auth for djbclark@gmail.com.
   **Requires operator approval first (hard gate).** Draft it, show it, let him
   send it.
4. Post to dev-cfengine referencing the ticket, asking preferences on the
   retention path question and the JSON surface.
5. Verify whether Linux CFEngine packages ship a `diff` in the bindir before
   saying anything upstream about `--simulate=diff` being broken.
6. **Back in tendcf:** the guide and map still describe Model A. Edit guide §7
   and map §9 to match Model B; extend guide §19 and rewrite §17 so the risk
   apparatus covers the trust/consent subsystem (root cause S1) — **keep that on
   Opus 5, not Fable**, whose classifiers target exactly that content.
7. Reconcile the guide with the map on dropped parameters (2-of-3 offline root,
   NAR digests are still only general in the guide).
8. Decide DOC-4 (renaming one of the two "capability" lists), now doubly
   relevant since the xhigh pass ruled labels must never widen what the validator
   accepts.
9. Three tendcf peer sessions from an earlier session never answered a status
   poll and were never closed. `ListAgents` then `SendMessage` using the
   `name [ref]` form — bare names are rejected.

## Quick Start

```sh
# tendcf — clean, in sync, nothing in flight
cd ~/src/tendcf && git log --oneline -3 && git status -sb

# read both E1 verdicts; the xhigh one is authoritative on the open decisions
sed -n '1,60p'   docs/architecture/e1-adjudication-xhigh-2026-08-15.md
grep -n '^## \|^### ' docs/architecture/e1-adjudication-xhigh-2026-08-15.md

# the CFEngine fork
cd ~/src/cfengine-core && git log --oneline -1 && git remote -v
gh issue view 2 --repo djbclark/core     # <- PR 1, the next action
gh issue view 1 --repo djbclark/core     # umbrella + build notes
gh issue view 3 --repo djbclark/core     # PR 2

# rebuild if needed (already built and installed to ~/opt/cfengine-dev)
make -j"$(sysctl -n hw.ncpu)" && make install

# reproduce the simulate smoke test (workdir needs cf-promises from the
# INSTALLED tree — the build tree gives you a libtool wrapper)
S=/tmp/cfsim; rm -rf "$S"; mkdir -p "$S/workdir/bin" "$S/target"
cp ~/opt/cfengine-dev/bin/cf-promises "$S/workdir/bin/"
printf 'original line\n' > "$S/target/demo.txt"
cat > "$S/test.cf" <<EOF
body common control { bundlesequence => { "main" }; }
bundle agent main
{
  files:
      "$S/target/demo.txt" content => "changed\n";
      "$S/target/newfile.txt" create => "true";
}
EOF
CFENGINE_TEST_OVERRIDE_WORKDIR="$S/workdir" \
  ~/opt/cfengine-dev/bin/cf-agent -f "$S/test.cf" --simulate=diff -I

# verify a fable-deep subagent's ACTUAL model+effort (never ask the agent)
ls -t ~/.claude/projects/-Users-djbclark-src-tendcf/*/subagents/*.jsonl | head -1
python3 -c "
import json,sys,glob,collections
f=sorted(glob.glob('$HOME/.claude/projects/-Users-djbclark-src-tendcf/*/subagents/agent-*.jsonl'))[-1]
c=collections.Counter()
for line in open(f):
    try: d=json.loads(line)
    except: continue
    m=d.get('message') or {}
    if m.get('model'): c[(m['model'], d.get('effort'))]+=1
print(f.split('/')[-1], dict(c))"

# the upstream gate (expect a deny, that is the point)
bash ~/.claude/hooks/upstream_review_gate.sh <<'EOF'
{"tool_input":{"command":"gh pr create -R cfengine/core --title x"},"cwd":"/Users/djbclark/src/cfengine-core"}
EOF
```
