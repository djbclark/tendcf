# Upstream register: every CFEngine/libntech defect and contribution we hold

**Living document. Update it in the same commit that changes an item's state.**

This exists because the channels we would normally file through are closed or
broken, so our reports live in places upstream does not read yet:

- `cfengine/core` has **GitHub Issues disabled** (Discussions only).
- `NorthernTechHQ/libntech` has **Issues disabled** too. (Our own fork
  `djbclark/libntech` had them disabled as well, which is why P-3 was filed as
  a PR; the operator **enabled issues there on 2026-08-16**, so libntech items
  from now on get the same issue-plus-branch shape as core items — B-4 is the
  next one that needs it.)
- The CFE Jira (`northerntech.atlassian.net`) needs an Atlassian API token we do
  not have.
- `CONTRIBUTING.md`'s contribution process is **out of date and deliberately not
  followed** (operator instruction, 2026-08-16). The rest of that file — code
  style, log levels, commit hygiene — still applies.

So the register's job is to make every item **refilable on demand**: if Jira
starts working, or upstream opens an issue tracker, everything below should be
submittable without re-deriving anything.

## Channels, and what "reported" currently means

Per the operator, each item gets the same treatment PR 3 got:

1. **Code** — a branch on our fork (`djbclark/core`, `djbclark/libntech`).
2. **A tracking artifact on the fork** — an issue where issues are enabled
   (`djbclark/core`), a pull request where they are not (`djbclark/libntech`).
3. **Email** — links to both, sent to **contact@northern.tech** for ordinary
   bugs and **security@northern.tech** for security-relevant ones. **When in
   doubt, security@** (operator, 2026-08-16).

**A second opinion is required before upstream is contacted** (operator,
2026-08-16). This is the same adversarial-review discipline the corpus already
applies to its own decisions — see the `*-opinion-{fable,gemini,grok}.md` panels
and the refutations they produced. A fork issue filed without one is not a
problem in itself, because the fork is not upstream; the rule is that **no email
goes out until the item has been second-opinioned and the issue updated with
whatever that review found.**

Nothing is filed on an upstream tracker yet, by necessity rather than choice.

## Register

Legend: **done** · *pending* · — not applicable.

`2nd` is the required second opinion; an item may not be emailed until it is done.

| id | Item | Repo | Fix | Fork branch | Fork artifact | 2nd | Email | Upstream |
|---|---|---|---|---|---|---|---|---|
| B-1 | Poll loops count iterations instead of measuring elapsed time, so the termination ladder overshoots ~4.5x on Darwin | core | **done** `26634ac1f` + `943d5371f` | **done** [`fix/exec-timeout-commands`](https://github.com/djbclark/core/tree/fix/exec-timeout-commands) | **done** [#4](https://github.com/djbclark/core/issues/4) | **done** 3-model panel; found 2 defects, both fixed; **withdrew the fail-open claim** | *pending* — **security@** | *pending* |
| B-2 | Descendants not signalled on timeout; grandchild holds the pipe, so `exec_timeout` does not bound wall clock | core | **done** `cb2561584` + `847373cf6` | **done** [`fix/timeout-process-group`](https://github.com/djbclark/core/tree/fix/timeout-process-group) | **done** [#5](https://github.com/djbclark/core/issues/5) | **done** 3-model panel; all three refused the unconditional `setpgid`; regression found and fixed | *pending* — **security@** (in doubt → security) | *pending* |
| B-3 | No `process_darwin.c`; macOS uses the stub, so `GetProcessState()` never reports ZOMBIE/STOPPED and `SafeKill()`'s PID-recycling guard is disabled | core | *not started* | — | **done** [#12](https://github.com/djbclark/core/issues/12) | *pending* | *pending* | *pending* |
| B-4 | JSON reals truncated to 2 decimals (`0.00049` → `0.00`), including through mustache templating; `%.2f` and `%.4f` disagree | libntech | *not started* | — | **done** [libntech#2](https://github.com/djbclark/libntech/issues/2) | *pending* | *pending* | *pending* |
| B-5a | Rejected CMDB file names no key, value or path — the `void *data` carrier already exists and is `ARG_UNUSED` | core | *not started* | — | **done** [#8](https://github.com/djbclark/core/issues/8) | *pending* | *pending* | *pending* |
| B-5b | One bad key silently drops **every** variable on the host; agent then reports no failures | core | *not started* | — | **done** [#9](https://github.com/djbclark/core/issues/9) | *pending* | *pending* | *pending* |
| B-6 | `eval()` returns `%lf` for integral results, so arithmetic cannot feed any function taking a count | core | *not started* | — | **done** [#10](https://github.com/djbclark/core/issues/10) | *pending* | *pending* | *pending* |
| B-7 | Dotted CMDB keys silently become scope paths, with no warning (**warn only** — do not change behaviour) | core | *not started* | — | **done** [#11](https://github.com/djbclark/core/issues/11) | *pending* | *pending* | *pending* |
| B-8 | `commands:` promise that exceeded `exec_timeout` is reported **kept** — `RepairExec()` never returns `ACTION_RESULT_TIMEOUT`, so the promise is judged only on the child's exit status. **This is the actual fail-open**; B-1 only narrows its window | core | **done** `326bcdb8d` | **done** [`fix/exec-timeout-promise-result`](https://github.com/djbclark/core/tree/fix/exec-timeout-promise-result) | **done** [#6](https://github.com/djbclark/core/issues/6) | *pending* — found **by** the B-1/B-2 panel | *pending* — **security@** | *pending* |
| P-1 | Retain the changes chroot after a `--simulate` run (feature) | core | **done** | `simulate-keep-chroot` `5dbd295f6` | **done** [#2](https://github.com/djbclark/core/issues/2) | *not done* | *unknown* | *pending* |
| P-2 | `--simulate-json`: machine-readable rendering of the change set (feature) | core | **done** | `simulate-json` `071f85987` | **done** [#3](https://github.com/djbclark/core/issues/3) | *not done* | *unknown* | *pending* |
| P-3 | Silent digest-initialization failure when hashing | libntech | **done** `da7d3d9` | `silent-digest-failure` | **done** [libntech#1](https://github.com/djbclark/libntech/pull/1) (PR) + [libntech#3](https://github.com/djbclark/libntech/issues/3) (issue) | *not done* | **done** (operator, manually) | *pending* |

`djbclark/core` [#7](https://github.com/djbclark/core/issues/7) tracks the
unmerged-libntech submodule dependency, and
[#1](https://github.com/djbclark/core/issues/1) is the
investigation trail behind P-1/P-2 and is not itself a defect.

B-2 through B-7 are described, measured and sourced in
[`cfengine-upstream-candidates-2026-08-16.md`](cfengine-upstream-candidates-2026-08-16.md);
B-1's full evidence is in
[`cfengine-exec-timeout-filing-package-2026-08-16.md`](cfengine-exec-timeout-filing-package-2026-08-16.md).

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
- **OPEN, mechanism not established — `exec_timeout` may not bound wall clock
  at all for a command that closes its output before it exits.** Measured:
  `"/bin/sh" arglist => { "-c", "exec 1>&- 2>&-; sleep 10; exit 0" }` under
  `exec_timeout => "2"` takes **~10.2s on stock 3.27.1** and ~12.1s on the
  integration build. The read loop ends at EOF, so the wait happens inside
  `cf_pclose()`/`cf_pwait()`. Gemini proposed `cf_pclose()`'s
  `ALARM_PID = -1` (`pipes_unix.c:874`), which precedes `cf_pwait()`, as the
  cause. That clear is real, **but the fix was implemented and measured and the
  behaviour did not change** (10.3s), so the diagnosis is refuted and the
  branch was discarded unfiled. Do not re-derive the ALARM_PID theory. Recorded
  in [#6](https://github.com/djbclark/core/issues/6) and disclosed in the
  security@ email as an observation only. Next step is to pin the actual
  mechanism before filing anything.
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
- **Jira.** Every *pending* in the Upstream column is waiting on the same
  Atlassian API token recorded against
  [PR 3](libntech-pr3-digest-init-filing-package-2026-08-15.md).

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
