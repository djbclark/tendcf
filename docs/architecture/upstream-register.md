# Upstream register: every CFEngine/libntech defect and contribution we hold

**Living document. Update it in the same commit that changes an item's state.**

This exists because the channels we would normally file through are closed or
broken, so our reports live in places upstream does not read yet:

- `cfengine/core` has **GitHub Issues disabled** (Discussions only).
- `NorthernTechHQ/libntech` has **Issues disabled** too.
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
   bugs and **security@northern.tech** for security-relevant ones.

Nothing is filed on an upstream tracker yet, by necessity rather than choice.

## Register

Legend: **done** · *pending* · — not applicable.

| id | Item | Repo | Fix | Fork branch | Fork artifact | Email | Upstream |
|---|---|---|---|---|---|---|---|
| B-1 | Poll loops count iterations instead of measuring elapsed time; `exec_timeout` reports a timed-out command as *promise kept* | core | **done** `26634ac1f` | **done** [`fix/exec-timeout-commands`](https://github.com/djbclark/core/tree/fix/exec-timeout-commands) | **done** [#4](https://github.com/djbclark/core/issues/4) | *pending* — **security@**, see "Blocked on" | *pending* |
| B-2 | Descendants not signalled on timeout; grandchild holds the pipe, so `exec_timeout` does not bound wall clock | core | **done** `cb2561584` | **done** [`fix/timeout-process-group`](https://github.com/djbclark/core/tree/fix/timeout-process-group) | **done** [#5](https://github.com/djbclark/core/issues/5) | *pending* — **contact@** | *pending* |
| B-3 | No `process_darwin.c`; macOS uses the stub, so `GetProcessState()` never reports ZOMBIE/STOPPED and `SafeKill()`'s PID-recycling guard is disabled | core | *not started* | — | — | — | — |
| B-4 | JSON reals truncated to 2 decimals (`0.00049` → `0.00`), including through mustache templating; `%.2f` and `%.4f` disagree | libntech | *not started* | — | — | — | — |
| B-5 | Rejected CMDB file names no key/value/path, and one bad key drops every variable on the host | core | *not started* | — | — | — | — |
| B-6 | `eval()` returns `%lf` for integral results, so arithmetic cannot feed any function taking a count | core | *not started* | — | — | — | — |
| B-7 | Dotted CMDB keys silently become scope paths, with no warning | core | *not started* | — | — | — | — |
| P-1 | Retain the changes chroot after a `--simulate` run (feature) | core | **done** | `simulate-keep-chroot` `5dbd295f6` | **done** [#2](https://github.com/djbclark/core/issues/2) | *unknown* | *pending* |
| P-2 | `--simulate-json`: machine-readable rendering of the change set (feature) | core | **done** | `simulate-json` `071f85987` | **done** [#3](https://github.com/djbclark/core/issues/3) | *unknown* | *pending* |
| P-3 | Silent digest-initialization failure when hashing | libntech | **done** `da7d3d9` | `silent-digest-failure` | **done** [libntech#1](https://github.com/djbclark/libntech/pull/1) | **done** (operator, manually) | *pending* |

`djbclark/core` [#1](https://github.com/djbclark/core/issues/1) is the
investigation trail behind P-1/P-2 and is not itself a defect.

B-2 through B-7 are described, measured and sourced in
[`cfengine-upstream-candidates-2026-08-16.md`](cfengine-upstream-candidates-2026-08-16.md);
B-1's full evidence is in
[`cfengine-exec-timeout-filing-package-2026-08-16.md`](cfengine-exec-timeout-filing-package-2026-08-16.md).

## Blocked on

- **Email — the first action of the next session.** Emailing is **not optional**:
  operator, 2026-08-16, *"It is 100% needed to email the addresses I gave you for
  each bug, or set of bugs, we post issues and tickets for in our local repo."*
  Our fork issues are public only in a personal repository nobody is likely to
  find, so posting there is **not** disclosure and does not discharge the duty to
  tell upstream.

  Blocked in this session only: `hermes send` has no mail transport (Discord,
  Signal, Telegram only), and the Claude Gmail connector the operator set up
  mid-session is not visible to a session that was already running — MCP servers
  are fixed at startup. Deferred deliberately to the next session, where it is
  the **first thing to do** after the handoff/quit/baton cycle.
- **Which address.** B-1 is a fail-open — a guard whose verification timed out is
  reported as satisfied — so it goes to **security@northern.tech** unless the
  operator says otherwise; under-reporting is the worse error, and upstream can
  downgrade it. B-2 is a hang/resource-leak and goes to **contact@**. An earlier
  draft of this register argued B-1 could go to contact@ because the fork issue
  was already public; that reasoning was **wrong** and the operator corrected it.
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
