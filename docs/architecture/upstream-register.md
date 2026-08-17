# Upstream register: every CFEngine/libntech defect and contribution we hold

**Living document. Update it in the same commit that changes an item's state.**

**CORRECTED 2026-08-16 (later session).** This document previously opened by
asserting that every upstream channel was closed and that "nothing is filed on
an upstream tracker yet". **Both statements were false when written**, and the
error hid three live upstream contributions. What is actually true, verified
against the GitHub API rather than restated from these notes:

| channel | reality | verified by |
|---|---|---|
| `cfengine/core` Issues | genuinely **disabled** | `gh api repos/cfengine/core` → `has_issues: false` |
| `cfengine/core` Pull requests | **open, and we have two live there** | [#6293](https://github.com/cfengine/core/pull/6293), [#6294](https://github.com/cfengine/core/pull/6294) |
| `NorthernTechHQ/libntech` Issues | **ENABLED** — the old claim that they were disabled was simply wrong | `gh api repos/NorthernTechHQ/libntech` → `has_issues: true`; our [#290](https://github.com/NorthernTechHQ/libntech/issues/290) is filed there |
| `NorthernTechHQ/libntech` Pull requests | **open, and we have one live there** | [#291](https://github.com/NorthernTechHQ/libntech/pull/291) |
| CFE Jira | still needs an Atlassian API token, and is **no longer on the critical path** — GitHub took all three items | — |

So the premise that motivated the fork-plus-email workaround **does not hold for
ordinary bug reporting**. Upstream GitHub accepts our issues and our pull
requests today. The fork-issue-plus-email shape remains correct for anything we
are not ready to put in front of maintainers, and email remains the right
channel for security-relevant items (B-1/B-2/B-8), but "we cannot file
upstream" is not a reason available to us any more. **Check the tracker before
asserting it is closed.**

`CONTRIBUTING.md`'s contribution *process* is **out of date and deliberately not
followed** (operator instruction, 2026-08-16). The rest of that file — code
style, log levels, commit hygiene — still applies.

The register's remaining job is to make every item **refilable on demand**:
everything below should be submittable without re-deriving anything.

## Channels, and what "reported" currently means

Per the operator, each item gets the same treatment PR 3 got:

1. **Code** — a branch on our fork (`djbclark/core`, `djbclark/libntech`).
2. **A tracking artifact on the fork** — an issue where issues are enabled
   (`djbclark/core`), a pull request where they are not (`djbclark/libntech`).
3. **Email** — links to both, sent to **contact@northern.tech** for ordinary
   bugs and **security@northern.tech** for security-relevant ones. **When in
   doubt, security@** (operator, 2026-08-16).

**A second opinion is required before upstream is contacted** (operator,
2026-08-16), and **every commissioned review must have reported before anything
is sent** (operator, 2026-08-16, after the fact — see below). A quorum is not
the gate; the whole panel is. This is the same adversarial-review discipline the corpus already
applies to its own decisions — see the `*-opinion-{fable,gemini,grok}.md` panels
and the refutations they produced. A fork issue filed without one is not a
problem in itself, because the fork is not upstream; the rule is that **no email
goes out until the item has been second-opinioned and the issue updated with
whatever that review found.**

**Timing rule, learned the expensive way.** The first email to security@ went
out with 2 of 3 B-8 reviews in, on the reasoning that both agreed and the third
would concur. The third landed minutes later carrying a false statement in our
own error string, a much sharper severity argument, and the evidence that
overturned a mechanism we had told upstream was ruled out — forcing a
correcting follow-up to an external security team. Wait for every reviewer. If
one must be abandoned, cancel it explicitly and say in the email how many
reviews informed the report; never send while one is still running.

**Three items ARE filed upstream** — P-1, P-2 and P-3, all opened by the
operator manually on 2026-08-15 evening and not recorded here until the
2026-08-16 correction. An earlier version of this line claimed the opposite.
Nothing is filed on the CFE Jira.

## Register

Legend: **done** · *pending* · — not applicable.

`2nd` is the required second opinion; an item may not be emailed until it is done.

| id | Item | Repo | Fix | Fork branch | Fork artifact | 2nd | Email | Upstream |
|---|---|---|---|---|---|---|---|---|
| B-1 | Poll loops count iterations instead of measuring elapsed time, so the termination ladder overshoots ~4.5x on Darwin | core | **done** `26634ac1f` + `943d5371f` | **done** [`fix/exec-timeout-commands`](https://github.com/djbclark/core/tree/fix/exec-timeout-commands) | **done** [#4](https://github.com/djbclark/core/issues/4) | **done** 3-model panel; found 2 defects, both fixed; **withdrew the fail-open claim** | *pending* — **security@** | *pending* |
| B-2 | Descendants not signalled on timeout; grandchild holds the pipe, so `exec_timeout` does not bound wall clock | core | **done** `cb2561584` + `847373cf6` | **done** [`fix/timeout-process-group`](https://github.com/djbclark/core/tree/fix/timeout-process-group) | **done** [#5](https://github.com/djbclark/core/issues/5) | **done** 3-model panel; all three refused the unconditional `setpgid`; regression found and fixed | *pending* — **security@** (in doubt → security) | *pending* |
| B-3 | No `process_darwin.c`; macOS uses the stub, so `GetProcessState()` never reports ZOMBIE/STOPPED and `SafeKill()`'s PID-recycling guard is disabled | core | *not started* | — | **done** [#12](https://github.com/djbclark/core/issues/12) | *pending* | *pending* | *pending* |
| B-4 | JSON reals truncated to 2 decimals (`0.00049` → `0.00`), including through mustache templating; `%.2f` and `%.4f` disagree | libntech **+ core** | **done** both halves, now the **base of B-10's stack** (not independently landable): libntech `8923f79`+`cd545ab`, core `6a4216dad` | **done** [`fix/json-number-fatal-exit`](https://github.com/djbclark/libntech/tree/fix/json-number-fatal-exit) (B-4 is its bottom two commits) | **done** [libntech#2](https://github.com/djbclark/libntech/issues/2), corrected by comment 2026-08-17 | **done** — 4-member panel 2026-08-17; B-4 had never been reviewed before | **done** — covered by B-10's `security@` mail | **done** [djbclark/libntech#5](https://github.com/djbclark/libntech/pull/5) (fork PR, filed with B-10) |
| B-10 | A **valid JSON number terminates the process**: exponent form without a dot (`1e-8`, `2e0`) is misclassified INTEGER, and integers past `long` overflow; both reach `StringToLongExitOnError()` → `DoCleanupAndExit()`. Measured on stock 3.27.1: `cf-promises` dies and **cf-agent falls back to failsafe** | libntech **+ core** | **done** both halves: libntech `fix/json-number-fatal-exit` (6 commits, tip `11725b0`), core `fix/json-number-rendering` (`6a4216dad`+`367c27fc5`+`32c38f8ab`) -- core half **behaviourally verified** both directions | **done** [`fix/json-number-fatal-exit`](https://github.com/djbclark/libntech/tree/fix/json-number-fatal-exit) + [`fix/json-number-rendering`](https://github.com/djbclark/core/tree/fix/json-number-rendering) | **done** [libntech#4](https://github.com/djbclark/libntech/issues/4) + [core#13](https://github.com/djbclark/core/issues/13), #4 corrected by comment 2026-08-17 | **done** — 4-member panel 2026-08-17, 4/4 ship-with-changes and 4/4 `security@`; found 7 defects in our own series, all fixed | **done** — `security@northern.tech` 2026-08-17, Gmail id `1a00f99c7e714823` | **done** [djbclark/libntech#5](https://github.com/djbclark/libntech/pull/5) (fork PR, six commits incl. B-4) |
| B-11 | `JsonRealCreate()` stores reals with `%.4f`, so **`JsonCopy()` changes a document's values**: `0.00049` → `0.0005`, `3.14159265` → `3.1416`. Measured; distinct from B-4, which is the render path | libntech | **done** — subsumed by B-10's copy commit `55f3eb3`, which makes `JsonPrimitiveCopy()` keep the parsed lexeme instead of rebuilding through `JsonRealCreate()`/`JsonIntegerCreate()`. The constructor still formats with `%.4f` for reals *built in memory*; that is pre-existing and out of scope, and is now pinned by `test_real_created_in_memory_renders_as_stored` | **done** [`fix/json-number-fatal-exit`](https://github.com/djbclark/libntech/tree/fix/json-number-fatal-exit) | **done** — folded into [libntech#4](https://github.com/djbclark/libntech/issues/4) | **done** — covered by B-10's panel | **done** — named in B-10's `security@` mail as the silent-corruption half | **done** [djbclark/libntech#5](https://github.com/djbclark/libntech/pull/5) |
| B-12 | `GetNetworkingInfo()` declares `long lowest_metric = 0;` (`libenv/unix_iface.c:1425`) and **never assigns it**, so the default-route comparison is `metric_value < 0` — false for every real metric. CFEngine therefore picks the **first** active default gateway, not the lowest-metric one, contrary to the variable name and the comparison's intent. Found while verifying B-10's core half; pre-existing and deliberately **not** fixed there | core | *not started* — recorded, not patched | — | *pending* | *pending* | *pending* | *pending* |
| B-5a | Rejected CMDB file names no key, value or path — the `void *data` carrier already exists and is `ARG_UNUSED` | core | *not started* | — | **done** [#8](https://github.com/djbclark/core/issues/8) | *pending* | *pending* | *pending* |
| B-5b | One bad key silently drops **every** variable on the host; agent then reports no failures | core | *not started* | — | **done** [#9](https://github.com/djbclark/core/issues/9) | *pending* | *pending* | *pending* |
| B-6 | `eval()` returns `%lf` for integral results, so arithmetic cannot feed any function taking a count | core | *not started* | — | **done** [#10](https://github.com/djbclark/core/issues/10) | *pending* | *pending* | *pending* |
| B-7 | Dotted CMDB keys silently become scope paths, with no warning (**warn only** — do not change behaviour) | core | *not started* | — | **done** [#11](https://github.com/djbclark/core/issues/11) | *pending* | *pending* | *pending* |
| B-8 | `commands:` promise that exceeded `exec_timeout` is reported **kept** — `RepairExec()` never returns `ACTION_RESULT_TIMEOUT`, so the promise is judged only on the child's exit status. **This is the actual fail-open**; B-1 only narrows its window | core | **done** `326bcdb8d` | **done** [`fix/exec-timeout-promise-result`](https://github.com/djbclark/core/tree/fix/exec-timeout-promise-result) | **done** [#6](https://github.com/djbclark/core/issues/6) | *pending* — found **by** the B-1/B-2 panel | *pending* — **security@** | *pending* |
| P-1 | Retain the changes chroot after a `--simulate` run (feature) | core | **done** `ea439e0ad` | `simulate-keep-chroot` | **done** [#2](https://github.com/djbclark/core/issues/2) | *not done* | *unknown* | **DONE** [cfengine/core#6293](https://github.com/cfengine/core/pull/6293) — open, mergeable, CLA signed |
| P-2 | `--simulate-json`: machine-readable rendering of the change set (feature) | core | **done** `f5ce3a35d` | `simulate-json` | **done** [#3](https://github.com/djbclark/core/issues/3) | *not done* | *unknown* | **DONE** [cfengine/core#6294](https://github.com/cfengine/core/pull/6294) — open, mergeable, CLA signed |
| P-3 | Silent digest-initialization failure when hashing | libntech | **done** `dc85a6f` | `silent-digest-failure` | **done** [libntech#1](https://github.com/djbclark/libntech/pull/1) (PR) + [libntech#3](https://github.com/djbclark/libntech/issues/3) (issue) |  **done** — panel + fable adjudication, correction pushed `e76700b` | **done** (operator, manually) | **DONE** [NorthernTechHQ/libntech#290](https://github.com/NorthernTechHQ/libntech/issues/290) (issue) + [#291](https://github.com/NorthernTechHQ/libntech/pull/291) (PR) — open, mergeable, CLA signed |

`djbclark/core` [#7](https://github.com/djbclark/core/issues/7) tracks the
unmerged-libntech submodule dependency, and
[#1](https://github.com/djbclark/core/issues/1) is the
investigation trail behind P-1/P-2 and is not itself a defect.

B-2 through B-7 are described, measured and sourced in
[`cfengine-upstream-candidates-2026-08-16.md`](cfengine-upstream-candidates-2026-08-16.md);
B-1's full evidence is in
[`cfengine-exec-timeout-filing-package-2026-08-16.md`](cfengine-exec-timeout-filing-package-2026-08-16.md).

### Cite branch heads, not remembered SHAs

All three P-item SHAs in the table above were **wrong** until 2026-08-16, in the
same way: the commit was amended after the SHA was written down, so the register
pointed at a commit that no branch reaches. The content was identical each time
— only the message differed (P-3's amend replaced `Ticket: CFE-XXXX` with
`Ticket: #290`) — which is exactly why it went unnoticed: every diff-based check
passes, and only `git branch --contains` reveals it.

| item | register said | corrected to | current head |
|---|---|---|---|
| P-1 | `5dbd295f6` | `00c98bc8b` | **`ea439e0ad`** (ticket-trailer repair, same day) |
| P-2 | `071f85987` | `8ee015c42` | **`f5ce3a35d`** (ticket-trailer repair, same day) |
| P-3 | `da7d3d9` | `dc85a6f` | `dc85a6f` |

P-1 and P-2 moved *again* within hours of the correction, which is the point:
these SHAs are not stable and citing them is a maintenance liability.

The check that catches this, run against any SHA this document cites:

```sh
git branch -a --contains <sha>     # empty output = orphaned, the citation is dead
```

Prefer citing the **branch name** and resolving the head on demand. A SHA is
only worth pinning when the point being made is about that specific commit.

### Upstream CI on libntech#291

`mender-test-bot` posted *"There was an error running your pipeline"* on
[#291](https://github.com/NorthernTechHQ/libntech/pull/291), but **no check
status was ever reported** (`gh pr checks 291` → "no checks reported";
the combined status API returns `total_count: 0`). The linked log is a private
GCP console URL we cannot read. So this is unattributable from outside and is
most likely Northern.tech infrastructure rather than our patch — but it is
**not evidence that our patch passes CI**, and nothing in this register should
claim it does.

## Blocked on

- **Email — the remaining gate for B-1, B-2 and B-8.** Emailing is **not
  optional**: operator, 2026-08-16, *"It is 100% needed to email the addresses I
  gave you for each bug, or set of bugs, we post issues and tickets for in our
  local repo."* Our fork issues are public only in a personal repository nobody
  is likely to find, so posting there is **not** disclosure and does not
  discharge the duty to tell upstream.

  The transport blocker is **cleared**: the Claude Gmail connector
  (`mcp__claude_ai_Gmail__*`) is visible to a session started after the operator
  set it up. `hermes send` still has no mail transport (Discord, Signal,
  Telegram only) and Composio is not the canonical path.
- **Second opinions — DONE for B-1 and B-2** (2026-08-16). Panel of three
  non-Claude CLIs, brief frozen at
  [`UPSTREAM-B1-B2-REVIEW-BRIEF.md`](UPSTREAM-B1-B2-REVIEW-BRIEF.md), opinions
  at `upstream-opinion-{cursor,gemini,grok}-2026-08-16.md`, reconciled in
  [`upstream-b1-b2-reconciliation-2026-08-16.md`](upstream-b1-b2-reconciliation-2026-08-16.md).
  It paid for itself: it refuted B-1's headline claim, caught a hang B-2
  introduced, and turned up B-8. `#4` and `#5` are updated. **B-8 still needs
  its own second opinion before its email**, per the standing rule — it was
  found *by* this panel, not reviewed by it.
- **Which address.** All three go to **security@northern.tech**. B-8 is the
  fail-open — a check whose verification timed out is reported as satisfied.
  B-1 is the timing defect that narrows B-8's window and was originally filed
  as the fail-open itself; it travels with B-8 because the correction only
  makes sense alongside it. B-2 is availability-shaped (unbounded wait plus a
  leaked process), and the operator's rule is *if in doubt, security@*. An
  earlier draft of this register said B-2 goes to contact@, and separately
  argued B-1 could go to contact@ because the fork issue was already public;
  both were **wrong** and are superseded by the operator's instruction.
- **OPEN — a timed-out command is not always terminated. Mechanism SUPPORTED,
  and my earlier "refuted" verdict is RETRACTED.** A command that closes its
  output and then outlives `exec_timeout` runs to completion: `exec 1>&- 2>&-;
  sleep 10; exit 0` under `exec_timeout => "2"` takes ~10.2s on **stock
  3.27.1**. Gemini and Grok independently diagnosed `cf_pclose()` clearing
  `ALARM_PID` before `cf_pwait()`, so `TimeOut()` fires with nothing to signal.
  I implemented that change, saw no wall-clock movement, and **wrongly recorded
  the theory as refuted**. Grok supplied the discriminator I missed: the two
  branches of `TimeOut()` log differently, and this case prints `verbose: >
  Time out`, which **is** the `ALARM_PID == -1` branch — confirmed on our own
  build. **Start from the ALARM_PID theory; do not avoid it.** What was wrong
  with my experiment is not yet known. The *reporting* half is closed
  ([#6](https://github.com/djbclark/core/issues/6)); this is the *termination*
  half and is not yet filed as its own issue.
- **libntech submodule pointer stays uncommitted in `~/src/cfengine-core`** —
  not an external rule, and earlier notes overstated it as "required". The
  reason: the checkout sits at `dc85a6f` ("Handle digest initialization failure
  when hashing"), our own P-3 fix, which exists only on `fork/silent-digest-failure`
  and is **not upstream**. `cfengine/core` records `5b5d04e1`. Committing the
  bump would put an unresolvable submodule reference into every core branch we
  offer upstream and entangle two contributions meant to land separately.
- **Unmerged libntech dependency — [core#7](https://github.com/djbclark/core/issues/7).**
  Our core branches are built and tested against libntech `dc85a6f` (our P-3
  fix, `fork/silent-digest-failure`, offered as libntech PR #1 and not merged),
  while upstream records `5b5d04e1`. Before any core branch is offered upstream
  it must be confirmed to build and pass against **stock** libntech — not yet
  done for B-1, B-2 or B-8. The tracking issue lives on `djbclark/core`
  because that is where the submodule pointer bites.
- **B-10's panel is partly in. gemini: *ship as is*, severity `security@`** —
  it argues "attacker-controlled" is accurate, since CMDB facts, external data
  sources and `readjson()` inputs can be populated by unprivileged users or
  third-party systems, so a crafted number is a persistent denial of service.
  It confirmed our unverified belief that core's `rlist.c` and `iteration.c`
  are twins, and **found a site we had missed**:
  `libpromises/generic_agent.c:2051` reads `"timestamp"` from the
  policy-validated file through `JsonPrimitiveGetAsInteger()`. Confirming that
  turned up **a second one gemini also missed**, `libenv/unix_iface.c:1440`,
  which reads a route `"metric"` the same way. Both fixed in core `367c27fc5`
  — these two genuinely want an integer, so the repair is a non-fatal
  conversion rather than keeping the text: an unreadable timestamp means "not
  validated" and an unreadable metric simply does not win. gemini's one test
  gap — `JsonSelect()` with an oversized all-digit index — is closed in
  libntech `76856ee`.

  **cursor: *ship with changes*,** four of them, agreeing the three crashes are
  real and the fixes hold under measurement. Two are already done: the
  `JsonSelect` overflow test (`76856ee`), and its warning not to treat this as
  closing CFEngine because `rlist.c`/`iteration.c` still die until
  `fix/json-number-rendering` lands. **Two remain open:** pin `1e400` → `inf`
  versus lexeme in a test, whichever we actually mean; and say plainly, in the
  filing and the email, that exponent *reals* still render through `%.2f`, so
  `1e-8` mustaches to `0.00`, not `1e-8`. That last one matters — the fix turns
  a fatal into a *lossy* result, and claiming otherwise would repeat exactly
  the overstatement the P-3 panel caught us in.

  **grok: *ship with changes*, severity `security@`** — the panel is now
  **COMPLETE** (fable-deep, gemini, cursor, grok). Consensus severity is
  `security@` on availability, and grok sharpened the threat statement in a way
  the filing should adopt verbatim: *"attacker-controlled" is overstated for a
  remote exploit; it is honest for a CMDB operator, a `readjson()` of
  third-party JSON, or an author who writes scientific notation by mistake.*
  A primitive `1e-8` in `def.json` or `host_specific.json` is enough to make
  `cf-promises` exit before any promise body runs.

  **grok found one thing nobody else did, and it is a real defect, not a
  disclosure item: `1e400` now renders as `inf`, which is not JSON.**
  `JsonWriteCompact()` still emits `1e400`, so render and serialise disagree
  again — the exact class of inconsistency this whole change set exists to
  remove. Earlier reviewers waved `inf` through as "acceptable but disclose";
  grok is right that emitting a non-JSON token is worse than that.

  **CORRECTION (2026-08-17, measured):** the paragraph above — and grok's and my
  own framing of it — is wrong about *when* `inf` happens. Stock does **not**
  render `1e400` as `inf`: with no decimal point it is misclassified INTEGER and
  **terminates the process**, never reaching `strtod()`. `inf` appears only once
  B-10's classification fix routes the value into the REAL path. So `inf` is
  **introduced by B-10 applied alone** and **removed by B-4** (which stops going
  through `double` at all). It is not a third patch to write; it is a statement
  about landing order. Full three-variant measurement:
  [`b10-number-render-measurement-2026-08-17.md`](b10-number-render-measurement-2026-08-17.md).

  ### B-10's remaining work before it goes upstream or to `security@`

  All four are now **closed**; see the measurement document for the evidence.

  1. ~~**Fix `1e400` → `inf`**~~ — **resolved as a landing-order question, not a
     patch.** `JsonPrimitiveGetAsReal()` is the only route to `strtod()` here and
     has exactly **two** in-tree callers, both of which B-4 rewrites, and **zero**
     callers in core. Once B-4 lands nothing in either tree can produce `inf`
     from parsed JSON.
  2. ~~**Say plainly that exponent reals still render through `%.2f`**~~ —
     **measured and written down.** B-10 alone renders `1e-8` as `0.00`. But the
     fair framing is narrower than "B-10 leaves a silent wrong value": `%.2f`
     truncation is a **pre-existing stock defect** (`0.00049` → `0.00` today,
     unpatched). B-10 moves exponent forms out of a *fatal* path into an
     *already-broken* lossy one. The filing must not imply they now render
     correctly.
  3. ~~**Add mustache coverage**~~ — **confirmed there is none to extend.** No
     file under `tests/unit/` references `MustacheRender` at all, so
     `libutils/mustache.c` has **zero** unit coverage. Correct move is a
     proposal in the filing plus an offer of a separate `mustache_test` PR — not
     an invention inside this one.
  4. **Verify the core twin branch** `fix/json-number-rendering` — in progress;
     `~/src/core-json` is now configured and building against **stock** libntech
     `5b5d04e1`, which is the honest configuration since core's PR lands
     independently of the libntech one.

  ### The two libntech branches are NOT independent — measured

  Applying `fix/json-real-precision` on top of `fix/json-number-fatal-exit`
  **breaks the latter's own test suite**: `json_test.c:1336` asserts
  `assert_string_equal("0.50", str)`, pinning the `%.2f` rendering of `0.5`.
  With B-4 applied that becomes `"0.50" != "0.5"` and `json_test` exits 1
  (verified 2026-08-17, then reverted; tree clean, 39/39 restored).

  Whichever branch lands second must update that assertion. `cfengine/core`'s
  half (`6a4216dad`) already avoids the whole problem by fixing integers **and**
  reals together in one commit; the libntech half is the only one split in two.
  **Recommendation: land B-4 first, or stack B-10 on it.**
- **Two defects, four call sites, two repositories — and neither half is
  sufficient alone.** B-4 and B-10 are the same underlying mistake: *rendering a
  JSON number by converting it to a C numeric type and formatting it back,
  instead of using the text the parser already kept.* It appears at four sites
  reached by different routes, so fixing one repository leaves the other live:

  | site | repo | reals | integers | reached by |
  |---|---|---|---|---|
  | **`JsonPrimitiveCopy()`** | libntech | `%.4f` | **fatal** | **every variable store** — see below |
  | `JsonPrimitiveToString()` | libntech | truncated | fatal | rendering |
  | mustache renderer | libntech | truncated | fatal | `string_mustache()` |
  | `RlistAppendJson()` | core | truncated | fatal | list contexts |
  | iteration equivalent | core | truncated | fatal | `$(container[key])` |

  **CORRECTION (2026-08-17): the table above was missing its most important
  row, and the framing around it was wrong.** `JsonPrimitiveCopy()` is a fifth
  site and it is not a rendering path at all — storing a JSON container as a
  CFEngine variable deep-copies it, so the conversion happens on **every
  variable store**. Measured against a build carrying core's half and stock
  libntech: a policy whose only content is
  `"d" data => readjson(...)` — no iteration, no mustache, nothing that renders
  the value — kills `cf-promises` at **policy-load time** and sends `cf-agent`
  to failsafe. `lldb` stack: `LoadPolicy` → `PolicyResolve` →
  `ExpandPromise` → `VerifyVarPromise` → `RvalNewRewriter` → `JsonObjectCopy`
  → `JsonCopy` → `StringToLongExitOnError`. The trigger is therefore **loading
  the value, not rendering it**, and the whole path is inside libntech — core's
  half cannot help. Details:
  [`b10-number-render-measurement-2026-08-17.md`](b10-number-render-measurement-2026-08-17.md).

  mustache reaches JSON data by a different path than variables and iteration
  do, which is why the core half was invisible while measuring the libntech
  half. **The core half is committed but NOT behaviourally verified** — the
  build machine was saturated — and must not be offered upstream until it is.
- **P-3's panel has reported, unanimously: push a correction.** cursor, gemini
  and grok all say the 21-line C patch itself holds — none could break the
  control flow, the free handling or `hash_test`. What is wrong is the *package*
  already in front of maintainers on
  [#291](https://github.com/NorthernTechHQ/libntech/pull/291):
  **(a)** the claim that this cannot be unit-tested without core's
  `CryptoDeInitialize()` is **false** — cursor and grok independently forced
  `EVP_DigestInit` to fail from a libntech-only harness (symbol override, and
  an OpenSSL 3 provider drain), so the PR carries a false statement *and* is
  missing a test it could have; **(b)** "feeds the TLS paths" overstates it —
  peer TOFU uses `HashNewFromKey()`, which already fails closed; **(c)** gemini
  alone adds that the patch ignores `EVP_DigestUpdate`/`EVP_DigestFinal`
  failures in the very same functions. Severity is split 2–1 for ordinary bug
  over `security@`.
- **DONE 2026-08-17 — P-3's correction is pushed.** The fable adjudication that
  gated this did report: it is
  [`upstream-p3-reconciliation-2026-08-16.md`](upstream-p3-reconciliation-2026-08-16.md),
  which sustained "push a correction, do not withdraw" and settled severity at
  **ordinary bug, not `security@`** — the zero digest is a colliding *lookup
  handle*, not a bypassed *cryptographic gate*. Executed its §5 in full:
  `dc85a6f` → **`e76700b`** on `fork/silent-digest-failure`, force-pushed with
  a lease; [#291](https://github.com/NorthernTechHQ/libntech/pull/291) is still
  **open and mergeable** on the new head, now a single commit. The C change is
  **byte-identical** to what the panel reviewed — only the message and the test
  moved. PR body rewritten to match the commit; force-push explained in a PR
  comment; #290's "worst-case impact" paragraph corrected by comment rather
  than a silent body edit. No email, per §5F.

  The test the PR falsely said was impossible now exists:
  `tests/unit/hash_init_fail_test.c`, a **dedicated program** because the
  provider drain stops working once any EVP digest has run. Verified in both
  directions — 40/40 on the branch, and **exit 3, all three cases failing**,
  against the unfixed file.

  **One thing the adjudication did not catch, found by measuring:** the WIP
  draft's `HashFile`/`HashPubKey` cases asserted only the zeroed digest, which
  is *pre-existing* behaviour — they passed against unpatched code, so 2 of 3
  cases were decorative. The patch's only contribution for those two is the log
  message. The adjudication suggested `StartLoggingIntoBuffer()`, but its
  buffer is `static` with no public reader; `Log()` writes to **stdout** here,
  so the test captures that with `dup2` and asserts the message. That is what
  took it from 1-of-3 to 3-of-3 discriminating.
- **RESOLVED 2026-08-16 — P-1 and P-2 cited ticket numbers that did not exist.**
  `00c98bc8b` carried `Ticket: #6295` and `8ee015c42` carried `Ticket: #6296`;
  both **404** against `cfengine/core`, which has issues disabled and could not
  have had such tickets. They appear to have been guessed as "the next numbers
  after our PRs". Because those commits were the heads of live upstream PRs, a
  maintainer reading either one saw a dangling reference.

  Neither commit carried a `Changelog:` line, and per `CONTRIBUTING.md`
  (corroborated by 23 of the last 60 libntech commits) `Ticket:` is only
  required alongside `Changelog:` — so the repair was to **drop the trailer**,
  not to invent another number. Done with the operator's approval:
  messages rewritten with `git commit-tree` so no working tree was touched,
  trees verified byte-identical, force-pushed with `--force-with-lease`.
  `00c98bc8b` → `ea439e0ad`, `8ee015c42` → `f5ce3a35d`; both
  [#6293](https://github.com/cfengine/core/pull/6293) and
  [#6294](https://github.com/cfengine/core/pull/6294) confirmed still **open
  and mergeable** on the new heads.

  Contrast P-3, which got this right: `Ticket: #290` resolves to a real upstream
  issue. **The rule this leaves behind: never write a ticket trailer for a
  ticket you have not seen exist.**
- **Jira — no longer on the critical path.** P-1, P-2 and P-3 all reached
  upstream through GitHub without it. The Atlassian API token recorded against
  [PR 3](libntech-pr3-digest-init-filing-package-2026-08-15.md) is still
  unavailable, and that now costs us nothing for these items. Do not treat a
  missing Jira token as a reason an item cannot be filed.

## Refiling checklist

When a real tracker opens, each item needs, in this order:

1. A ticket carrying the fork issue's body verbatim — they are written as
   standalone bug reports, not as notes to ourselves, precisely so this step is
   a copy.
2. A PR against the upstream repo from our branch, titled with the new ticket
   id if the tracker assigns one.
3. This register updated in the same commit, and the fork artifact edited to
   point at the upstream one so the two never diverge.

Do **not** rewrite history on the fork branches to suit a new tracker's
conventions — the fork commits are what our own builds are tested against, and
[R22](projector-reconciliation-2026-08-16.md)'s anti-drift argument applies to
these the same way it applies to the projector.

## The fork is a staging area, not a product

Operator instruction, 2026-08-16: *"We do not want to maintain forked code
long-term if at all possible. We totally want to maintain a fork that fixes
whatever issues are not currently fixed upstream."*

So the fork carries exactly what upstream has not taken yet, and every item here
is meant to leave it. That is also why the diff discipline from PR 1 still
governs every fix: additive over modifying, few tight hunks, no reflowing of
neighbouring code, so that carrying an item across upstream releases stays cheap
while it waits.

**Branch layout.** One branch per upstream contribution, each cut from `master`
and independently landable — `fix/exec-timeout-commands` (B-1) and
`fix/timeout-process-group` (B-2) touch disjoint files, and either can be taken
without the other. **`tendcf-integration`** merges all of them and is the branch
our builds are made from. Never develop on the integration branch; cherry-pick
onto a clean per-fix branch so what we offer upstream is never entangled with
something upstream has not agreed to.

**Our builds test against the fork**, so a fix landing here changes what tendcf
is measured against. Anything in the corpus that was measured on stock 3.27.1
and could be affected by one of our fixes must be re-measured and the number
re-stated, not assumed to have carried over.
