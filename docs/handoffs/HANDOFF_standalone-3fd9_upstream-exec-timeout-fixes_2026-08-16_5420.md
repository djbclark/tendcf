---
schema_version: 1
handoff_id: 5420
parent_handoff_ids: [7c19]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: c01907bd2d6a2ed0f72ebb752ebf399a9adf7e20
created_at: 2026-08-16T19:38:00-0400
writer: claude-code
---

# Handoff — two CFEngine timeout bugs fixed upstream, and P-8 closed

## The Goal

The session opened on the generic bundle — the `.cf` that consumes
`tendcf_service` and `tendcf_interlock` and renders promises from `state`,
which `projector-reconciliation-2026-08-16.md` §11 explicitly leaves undecided
and which the previous handoff (7c19) named as THE next action.

It never got written, and that is the right outcome rather than a miss. Before
writing policy against the data contract, the contract was measured for
consumability; that measurement found a CFEngine defect; the operator's standing
instruction is to **fix upstream rather than design around**, so the session
became upstream work. Two bugs are now fixed, tested and filed.

Along the way, item 1 of the resumed plan — `device-trust`'s destination —
was also closed as P-8.

## Where We Are

**tendcf** `master` at `c01907bd2d6a2ed0f72ebb752ebf399a9adf7e20`, clean, pushed.
Six commits this session:

| sha | what |
|---|---|
| `1064def` | `check_trust_inexpressible()` — the schema's "structurally inexpressible" claim is now measured, not asserted |
| `bc74193` | P-8: `device-trust` has no destination; §11's "next open question" was never open |
| `76f7a8f` | filing package for the `exec_timeout` defect |
| `bd2b2d5` | survey of six upstream candidates, ranked by benefit to us |
| `51afbfe` | B-1 fixed on the fork; `upstream-register.md` created |
| `600afd7` | B-2 fixed and filed; branch layout and email duty recorded |
| `c01907b` | second opinion required before any upstream contact |

**CFEngine fork** `djbclark/core`, at `~/src/cfengine-core`, currently checked
out on `tendcf-integration` and **built**. Three branches pushed:

- `fix/exec-timeout-commands` — B-1, commit `26634ac1f`, off `master` `17eb78e6d`
- `fix/timeout-process-group` — B-2, commit `cb2561584`, off the same master
- `tendcf-integration` — merge of both; **this is what our builds come from**

Working tree there shows ` M libntech` — the submodule pointer, carried from the
PR-3 work. **Do not commit it.** It has survived every session so far by being
left alone.

**Nothing has reached upstream.** Two gates stand in front of the emails, in
order: second opinions (now required), then the Gmail connector.

## What We Tried

Chronological, including everything that failed. This is the expensive half.

### 1. Naive join for argv — wrong mechanism, abandoned

Started characterising how `commands:` handles a projected argv array by joining
it into the promiser string. Measured a lot of real behaviour: a naive join
re-splits on whitespace (`["--msg","hello world"]` arrives as 3 arguments, not
2); quote-wrapping *does* group (both `'` and `"`); backslash escaping does
**not** work (`hello\ world` → `hello\`, `world`); there is **no escape
mechanism**, so an argument containing both quote characters is unrepresentable;
and `argv[0]` must be bare because CFEngine checks the executable path before
stripping quotes, making an executable path with a space unrepresentable.

All true, and all irrelevant. `commands:` has an **`arglist`** attribute that
passes elements verbatim. Measured with a hostile payload: `hello world`,
`he said "hi" and it's fine` (both quote chars), `a; touch /tmp/...` (shell
metacharacters), an empty argument, and a real tab — **ARGC=5, every argument
byte-exact, no injection under `useshell => "noshell"`**.

**Consequence:** a schema constraint to refuse un-renderable argv was drafted and
then **thrown away as unnecessary**. Do not re-derive it. The rule is simply:
the bundle uses `arglist`, never a joined promiser string.

### 2. "exec_timeout is ignored outright" — refuted by my own later measurement

Claimed this after seeing 11 s for a 10 s command under a 2 s timeout. Wrong: I
had attributed a constant cost to the command. The timing matrix refuted it —
an unfired timeout is free (5.21 s vs 5.13 s), so there is no constant cost, and
the penalty tracks `exec_timeout` rather than the command.

### 3. "The ~9 s is cf-agent startup" — refuted by baseline

Also wrong. A trivial policy with no `commands:` costs **0.10 s**.

### 4. "SIGKILL is never delivered" — refuted by instrumentation

Believed because a payload trapping INT and TERM ran its full 30 s. Instrumented
build showed SIGKILL *is* sent, at 8.917 s. The 30 s residue was the orphaned
grandchild holding the pipe — a different defect, which became B-2.

### 5. B-2's first guard silently never fired — the worst kind of failure

The process-group sweep was guarded on `getpgid(ALARM_PID) == ALARM_PID`, read
**after** `GracefulTerminate()`. `getpgid()` returns **ESRCH** once the process
is dead, so the guard was always false, the sweep never ran, and the fix looked
like a non-fix (still 31 s). Instrumenting the guard printed
`getpgid=-1 errno=3` and settled it. Reading the pgid *before* terminating fixes
it. **Read process state before you destroy the process you want to ask about.**

### 6. Hyphenated ids cannot build CFEngine variable names

`"argv_$(ids)"` with an id like `caddy-config-valid` fails:
`Variable identifier 'argv_caddy-config-valid' is not legal`. Hyphens are legal
as **container index keys** but not in **variable identifiers**. Cost three
failed attempts. The idiom that works is a parameterized bundle invoked via
`methods:`, taking the id as a **parameter**, never as a name component. This is
distinct from R23 (which is about container *names*) and does not re-derive it.

### 7. `@(dynamic_$(id))` does not parse

`arglist => { @(rest_$(ids)) }` is a syntax error; the quoted form
`"@(bundle.rest_$(ids))"` gets past the parser but then hits failure 6. The
parameterized-bundle idiom solves both at once.

### 8. `eval()` cannot feed a count

`sublist("argv","tail", eval("$(n) - 1","math","infix"))` fails with
`Anomalous ending '.0' while parsing integer number: 4.000000`. `eval` returns
`%lf` even for integral results. Workaround is `format("%d", eval(...))`; the
real fix is B-6.

### 9. Three process conclusions the operator corrected

- **Composio is not the canonical email path.** The built-in Claude Gmail
  connector is. `hermes send` has no mail transport at all — `--list` shows only
  Discord, Signal and Telegram.
- **"Already public, so contact@ is fine" is wrong.** Our fork issues are public
  only in a personal repo nobody will find; that is not disclosure and does not
  discharge the duty to email upstream.
- **Second opinions are required before contacting upstream**, and neither #4 nor
  #5 has had one. Filing on the fork first is fine; emailing without a review is
  not.

## Key Decisions

**P-8 — `device-trust` has no destination** (`bc74193`). It is consumed in place
from the integrity-protected approved goal file. §11 called this the next open
question; §7 had already closed it. Fable defines "own config" as `device-trust`
itself (`goal-file-schema-opinion-fable.md:293`), so the file reading makes the
sentence circular; the only agent config *file* in the corpus is `:302`'s
privileged-promiser-list address, and §7 ruled that list **empty in v1**. Filed
C-3 with §11's bullet **struck rather than deleted**, because the error in it is
the correction. R24 records what *is* genuinely unspecified (device-authored
operational state), which is what made §11 look open.

**Rejected:** building an agent trust-config file. It would lose the domain, the
closed kind set, and the diff/ceremony/approval-record at once — a second gate,
not a format, and P-1's minority position under a different filename.

**B-1 fix: measure elapsed time, don't count iterations.** Both poll loops now
compute a deadline from a monotonic clock, matching `EvalContextEventStart()`'s
`CLOCK_MONOTONIC`-with-`CLOCK_REALTIME`-fallback.
**Rejected:** leaving the accounting and special-casing Darwin — the bug is
platform-independent; Darwin only has the granularity that exposes it.

**B-2 fix: `setpgid(0,0)` in `cf_popen`'s child, sweep the group in `TimeOut()`.**
Guarded on `pgid == pid`, read before termination.
**Rejected:** making `GracefulTerminate()` group-aware — it is shared with the
stale-lock path in `locks.c`, where group semantics are wrong.
**Rejected:** setting the process group only when an `exec_timeout` is present —
would make the timeout path structurally different from the normal one.

**Branch layout.** One independently-landable branch per contribution, cut from
`master`; `tendcf-integration` merges them and is what we build. Never develop on
the integration branch — cherry-pick onto a clean branch, so what we offer
upstream is never entangled with something upstream has not agreed to.

**Both emails go to security@.** B-1 is a fail-open. B-2 is availability-shaped,
and the operator's rule is *if in doubt, security@*.

## Evidence & Data

**B-1 mechanism, from the instrumented build:**

```
GT(pid=44939): ENTER
GT: SIGINT sent at 0.000s
wait(pid=44939): TIMED OUT after 4.459s, 100 iters -> false
GT: SIGTERM sent at 4.460s
wait(pid=44939): TIMED OUT after 4.457s, 100 iters -> false
GT: SIGKILL sent at 8.917s -> true
```

Each "one second" wait runs its full 100 iterations and takes 4.46 s.
Confirmed independently of CFEngine: 100 × `nanosleep(10 ms)` standalone takes
**4.41–4.66 s** (~45 ms per 10 ms request) on Darwin/arm64.

**Before/after:**

| case | before | after |
|---|---|---|
| `sleep 5`, `exec_timeout 2` | promise **KEPT**, 11.2 s | promise **not kept**, 5.2 s |
| `sh -c 'sleep 30'`, `exec_timeout 2` | 30.3 s, `sleep` orphaned | 5.0 s, no orphan |
| `trap '' INT TERM; sleep 30`, timeout 2 | 30.3 s | 4.4 s |
| `/bin/sleep 30`, `exec_timeout 2` | — | 4.4 s |
| `/bin/sleep 1`, `exec_timeout 2` | — | 1.2 s, no penalty |
| trivial policy, no `commands:` | 0.10 s | 0.10 s |

Defect A was **5/5 deterministic** before the fix, and the 22-line standalone
repro reproduced **3/3 on 3.27.1** and **1/1 on locally built 3.29.0a**.

**Regression, both fixes:**

- `tests/unit/process_terminate_unix_test` — 6/6.
- Full `make check` in `tests/unit` — **64 PASS, exit 0**, FAIL/ERROR/XFAIL set
  **identical** to baseline across both fixes (compared by stashing the patch).
  Pre-existing XFAILs: `process_test` (Darwin stub — `PROCESS_START_TIME_UNKNOWN`,
  `STOPPED` and `ZOMBIE` undetected) and the non-deterministic `mon_processes_test`.
- **B-1's fix genuinely broke `process_terminate_unix_test` (1/6)** before the
  test change. Baseline was 6/6, which is how it was known to be mine.

**tendcf gates, re-run against the FORK build:** projection contract probe
identical (14 report lines), `schema-lint: OK` (8 schemas, 59 negative, 6
byte-class, 27 projection), `xref_lint` 0 findings / 31 live / 565 sections,
`flag_coverage` 21/21.

**Measured CFEngine facts banked for the generic bundle:**

- Addressing `$(data:variables.tendcf_service[<id>][<field>])` **works**; dotted
  ids are fine as container indices, `getindices` returns them intact, nested
  `unit.launchd.keep_alive` reads, `expect_exit` reads as `0`.
- `arglist` is argv-verbatim; a joined promiser string is not.
- Interlock semantics otherwise work: a non-zero `expect_exit` defines its class
  via `kept_returncodes`, a wrong exit code blocks, a lone child is killed on time.
- `exec_timeout`'s syntax range is `1,3600` while the schema's `timeout_seconds`
  has no maximum — a contract/executor mismatch, still unfixed.

**Upstream survey numbers** (`cfengine-upstream-candidates-2026-08-16.md`):
JSON reals truncate to 2 dp — `0.00049` → `0.00`, `3.14159265` → `3.14` —
including through `string_mustache`; `StringFromDouble` is `%.2f`
(`string_lib.c:922`), `JsonRealCreate` is `%.4f` (`json.c:1664`). A CMDB file with
one bad value logs `Invalid 'vars' CMDB data, cannot contain variable references`
naming no key, and drops **every** variable on the host.

## Operator Feedback

- **Fix every bug we find** — ours or not, large or small, found deliberately or
  by accident. *"We want to be excellent open source citizens."* Fix even if the
  fix may not be canonically correct, **but say so when submitting**.
- **Maintain a fork of what upstream has not taken yet**, and test against it, so
  we never write workarounds. *"We do not want to maintain forked code long-term
  if at all possible."* It is a staging area, not a product.
- **Regression-test after each fix**, against everything built before that point.
- **Three reporting channels per bug**: fork branch, fork issue/PR, **and email**
  to contact@ / security@northern.tech. Emailing is *"100% needed"*.
- **`CONTRIBUTING.md` is out of date** and is not followed for process — no Jira
  step. Its code style and commit hygiene still apply.
- **Second opinions on everything before contacting upstream.** Already-filed
  fork items still need the review and an issue update if it finds anything.
- **If in doubt, choose security@.**
- **tendcf and nix2cf are separate repos**; work either or both, serially or in
  parallel. This was never an open question and should stop being carried as one.

## Where We're Going

1. **THE NEXT ACTION — get a second opinion on B-1 and B-2, before any upstream
   contact.** Use the corpus's own pattern: a non-Claude CLI panel, as in
   `docs/architecture/projector-opinion-{cursor,gemini,grok}.md`. Put the
   uncertainties already flagged in `#4`/`#5` in front of the reviewer
   explicitly — `setpgid` detaching every `cf_popen` child from the agent's
   process group (so a terminal Ctrl-C no longer reaches a running child), the
   unconditional group SIGKILL rather than a graceful escalation, and teaching
   `process_terminate_unix_test` to drive `clock_gettime` from its fake clock.
   Update the issues with whatever the review finds.
2. **Then send the emails.** B-1 and B-2 both to **security@northern.tech**, each
   carrying links to both the fork issue and the fork branch. Verify the
   connector is actually present first (`ToolSearch "+gmail"`); if it still
   resolves nothing, say so rather than substituting another transport.
3. **Then the remaining bugs**, in this order: **B-5** (CMDB rejection names no
   key, and one bad key drops every variable — highest correctness return for us;
   naming the key is nearly free because both `JsonWalk` callbacks already take a
   `void *data` declared `ARG_UNUSED`), **B-4** (float truncation, libntech),
   **B-6** (`eval` `%lf`), **B-3** (`process_darwin.c` — would flip existing
   `process_test` XFAILs to passing), **B-7** (dotted CMDB keys — *warn only*, do
   not change behaviour; P-2 already routes around it correctly). Each needs its
   own second opinion before its email.
4. **Then E-9 and `services:`** — the operator's stated goal for this stretch.
   E-9 (the 5 MiB `HOST_SPECIFIC_DATA_MAX_SIZE` hard load failure) has never been
   re-measured and has the same silent-total-loss shape as B-5. `services:` is
   the generic bundle's largest unwritten surface.
5. **Then the generic bundle itself** — still the only live bullet in §11, now
   with its mechanics measured (see Evidence).
6. Unrelated, carried: confirm `track-issue-activity.yml`'s Discussion path fires
   in site-djbclark.

## Quick Start

```bash
# State
cd ~/src/tendcf && git log --oneline -3 && git status -s
cd ~/src/cfengine-core && git branch --show-current && git status --porcelain
#   ' M libntech' is EXPECTED there and must stay uncommitted.

# The register gates everything upstream — read it first
sed -n '1,60p' ~/src/tendcf/docs/architecture/upstream-register.md

# The two filed items
gh issue view 4 --repo djbclark/core
gh issue view 5 --repo djbclark/core

# Rebuild the integration binary (already built; only if sources changed)
cd ~/src/cfengine-core && make -C libpromises -j8 && make -C cf-agent -j8

# Regression, after ANY cfengine change — baseline by stashing before blaming
cd ~/src/cfengine-core/tests/unit && ./process_terminate_unix_test
cd ~/src/cfengine-core/tests/unit && make check 2>&1 | grep -cE '^PASS: '   # expect 64

# tendcf gates
cd ~/src/tendcf && bin/schema_lint.py && bin/xref_lint.py && bin/flag_coverage.py

# The exec_timeout repro lives in the filing package, paste-ready
sed -n '/^## Repro, paste-ready/,/^## What the evidence/p' \
  ~/src/tendcf/docs/architecture/cfengine-exec-timeout-filing-package-2026-08-16.md
```
