---
schema_version: 1
handoff_id: b167
parent_handoff_ids: [6d19]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 235f1999ba350559746e5fd708a6ef976c0732d4
created_at: 2026-08-18T22:15:00-0400
writer: claude-code
---

# Handoff — libntech overlay shipped, then a full CFE-4715..4740 Jira staleness sweep

## The Goal

Resumed from `6d19` (generic bundle v1 shipped, issues #3/#4 filed). Session
had two parts: first, work `frdminc/tendcf#3` (the libntech patch overlay).
Then the operator noticed `CFE-4715`/`CFE-4716` still carried a stale "do
not merge" banner from filing time despite the fix having shipped, which
grew into a full staleness sweep of every Jira ticket this suite owns.

## Where We Are

`tendcf` clean at `235f199`, pushed. No uncommitted work anywhere. Two
worktrees kept alive on purpose (needed for `#3`, still open):
`~/src/libntech-overlay` (branch `overlay/tendcf-3`, tip `45c816c`) and
`~/src/core-cmdbkey` (branch `fix/cmdb-one-bad-entry-skips-only-that-entry`,
tip `8f0076b81`, **libntech submodule pointer dirty/uncommitted at
`45c816c` — deliberate**, local testing only per `#3`'s own scope). A third
throwaway worktree, `core-p2-utf8test`, was created for the
`RestoreUtf8InJson()` test and removed afterward (`git worktree remove
--force`) — nothing there was meant to persist.

### Part 1 — `frdminc/tendcf#3` shipped

Merged libntech's `fix/json-double-decode` + `fix/mustache-minor-defects`
onto `0c0620d` in a new worktree (`libntech-overlay`, branch
`overlay/tendcf-3`) — plain octopus merge, no conflicts, commit
`45c816cecafa38e9097995a3ccd2940ddccbd44a`. Pointed `core-cmdbkey`'s
`libntech` submodule at that commit (had to `git fetch` it in by local
filesystem path — see Gotchas) and did a full `make -j4` at tip
`8f0076b81`, clean. Verified all three defect fixes together, not just
compiled: `json_test` 74/74, `mustache_test` 17/17,
`00_basics/06_host_specific_data/` acceptance 14/14 (fakeroot, fresh
`BASE_WORKDIR`, deleted after). Documented as a comment on
[issue #3](https://github.com/frdminc/tendcf/issues/3#issuecomment-5335945484).

### Part 2 — the Jira staleness sweep

**Trigger.** Operator: "I don't think we ever got back to actually
implementing CFE-4715 or CFE-4716." Investigation showed P-1/P-2 (the
`--simulate-keep-chroot`/`--simulate-json` features) **were** implemented
and PR'd (`#6293`/`#6294`, since 2026-08-16/17) — not blocked by B-5b/B-6 as
first guessed (unrelated code paths). But both Jira tickets still displayed
"please do not merge yet, a correction is in progress" verbatim, with
**zero comments on either ticket since creation**, even though the pushed
corrections (`f6c06f9e2`/`b3a6c3da5`) were already panel-reviewed and the
PRs OPEN/MERGEABLE.

**Fixed CFE-4715/CFE-4716** via direct Jira REST `PUT` (token via
`sudo-secretspec run`, Basic auth `djbclark@gmail.com` +
`ATLASSIAN_CFENGINE_API_TOKEN`): rewrote both "Current state" sections to
DONE, added a CFE-4731 see-also to CFE-4716. Verified by re-`GET`, not
assumed from the 204 response.

**Operator, before the sweep**: "if the results of the [RestoreUtf8InJson]
test might affect one of the tickets, do it before the ticket sweep." So:

**Tested `RestoreUtf8InJson()`/B-13 interaction for real.** The register had
an *untested* claim that CFE-4716's `RestoreUtf8InJson()` workaround
"degrades to a no-op" once B-13's fixed libntech lands — never executed
because `core-p2` was pinned at old libntech. Built a throwaway `core-p2`
worktree, repointed its submodule at the merged overlay, ran
`tests/unit/simulate_mode_test`: **15/17 pass, 2 fail**
(`test_special_characters_in_path`, `test_invalid_utf8_in_path` — both
EXPECTED given the finding below, not bugs). Wrote a standalone probe
(`probe.c`, copied the three static functions verbatim, linked against the
real built `libutils.a`) to isolate exactly what happens. Result — **half
the register's claim was wrong**:

- Valid multi-byte UTF-8 ("é", `C3 A9`): the fixed encoder emits one
  `é` per code point instead of one `\u00XX` per UTF-8 byte, so
  `RestoreUtf8InJson()` never collects the 2+ consecutive escapes it looks
  for and passes the text through unchanged. **Confirmed safe — dead
  code, not corruption**, matching the register's claim.
- **Invalid lone byte `0xE9`** (e.g. a Latin-1 filename byte): encodes to
  the **identical** `é` escape as the valid case above —
  `RestoreUtf8InJson()` cannot tell them apart. A conformant parse of
  `é` (which the fixed libntech now IS) correctly decodes to "é" —
  **not the original byte**. The old test only ever "passed" because the
  old non-conformant writer and parser were exact inverses that canceled
  out — the same "codec round-trips its own corruption" trap this
  project's own testing discipline exists to catch. This is a real,
  pre-existing representational gap (a non-UTF-8-valid path byte cannot be
  exactly represented in a JSON string, conformant or not) that the old
  test accidentally papered over — not a new defect the workaround
  introduces.

Posted as a comment on CFE-4716 (`159456`), **not a new ticket** — the
operator asked mid-turn why, confirming the reasoning: the defect only
exists inside P-2's own unmerged branch/test, matching how the original 8
P-2 review defects were folded into CFE-4716's description rather than
filed separately. Register corrected with a `CORRECTED 2026-08-18` note
under the P-2/B-13 interaction section (commit `a79777e`).

**Then the full sweep**, per operator: "check all the other tickets...
everything from CFE-4715 to CFE-4740 is ours, that's 25 [26] issues."
Fetched all 26 via a Python/curl script, grepped for staleness markers,
then **read every flagged ticket in full** and separately verified PR-link
presence for all 26 with targeted grep, cross-checked against `gh pr view`
for live OPEN/MERGEABLE status before posting anything. Findings (all
fixed with a Jira comment, commit `235f199`):

- **9 tickets had an already-open PR the ticket itself never linked at
  all** (worse than CFE-4715/4716's stale-but-present link): CFE-4718
  (`#6307`), CFE-4727 (`#6310`), CFE-4729 (`#6305`), CFE-4732 (`#6308`),
  CFE-4733 (`#6309`), CFE-4734 (`#6311`), CFE-4735 (`#6312`), CFE-4736
  (`#6313`), CFE-4737 (`#6314`).
- **CFE-4729's description also names a stale branch**:
  `fix/timeout-process-group` (pre-merge-with-B-8), but `#6305` actually
  ships `fix/timeout-process-group-merged` — confirmed via
  `gh pr view 6305 --json headRefName`, not assumed from memory.
- **A real duplicate, not just staleness: CFE-4725 and CFE-4737 describe
  the identical defect and the identical branch**
  (`fix/json-number-rendering`). CFE-4725 filed first (2026-08-17), said
  the branch was blocked on CFE-4724/libntech#294, never revisited. The
  next day, after discovering that "blocked" assumption was wrong (see the
  register's `fix/json-number-rendering was never actually blocked`
  section), a **new** ticket CFE-4737 was filed for the same branch
  without checking CFE-4725 already existed. `#6314`'s PR body literally
  says `Ticket: CFE-4737` (verified via `gh pr view 6314 --json body`), so
  CFE-4737 is canonical; CFE-4725 got a comment marking it a duplicate.
  `Link Issues` permission is still unavailable (confirmed earlier in this
  chain), so a comment-with-URL is the only available mechanism.
- **Two tickets missing cross-links to their own follow-ups**: CFE-4727
  never linked CFE-4734/CFE-4735 (which its own review produced); CFE-4738
  said the augments-loader null-crash "wants its own ticket" but never
  linked CFE-4739, which is exactly that ticket, already shipped.
- **Confirmed clean, read in full**: CFE-4717, 4719–4724, 4726, 4728,
  4730, 4731, 4739, 4740 — all correctly link their PR and reflect current
  status, either directly or via a later comment that supersedes an
  earlier stale draft section.

**A near-miss worth recording**: drafted a CFE-4736 comment claiming the
ticket's two open design questions were "resolved (operator decision)"
before posting — then re-checked the register text and found they were
actually **deliberately left open, posed to upstream reviewers in the PR
itself**, not resolved internally. Caught and corrected before posting,
not after. The final comment states the questions remain open.

## What We Tried

- **`fakeroot ./testall`** (prefixing fakeroot manually) — fails with
  "nested operation not yet supported." `testall`'s own
  `DEFAULT_GAINROOT=fakeroot` already invokes it; run `./testall
  --base-workdir=...` bare.
- **Standalone `cf-agent -K -f policy.cf --simulate-json=...`** for the
  UTF-8 test — needs a full bootstrap (`cf-promises` copied into
  `$WORKDIR/bin`, a key pair via `cf-key`, etc.) that's disproportionate
  for a quick behavioral check. Abandoned in favor of rebuilding and
  running the existing `tests/unit/simulate_mode_test` binary directly,
  which is what actually produced the finding.

## Key Decisions

- **RestoreUtf8InJson() finding → a CFE-4716 comment, not a new CFE
  ticket.** The defect exists only inside P-2's own unmerged branch/test;
  there's no independent upstream code to file a ticket against yet.
  Matches the established pattern from the original 8 P-2 review defects.
- **CFE-4725/CFE-4737 duplicate → comment-based cross-link, not a formal
  merge/close.** `Link Issues` permission unavailable; no other mechanism
  exists with current Jira permissions.
- **Left `core-cmdbkey`'s libntech submodule pointer dirty/uncommitted.**
  Deliberate — local testing only, matches `#3`'s own stated scope ("no
  packaging yet").
- **Kept `libntech-overlay` and `core-cmdbkey` worktrees alive; deleted
  `core-p2-utf8test`.** The first two are reusable for `#3` until its three
  upstream PRs merge; the third was explicitly throwaway (said so in its
  own Jira comment).

## Evidence & Data

**Overlay build (Part 1):** `json_test` 74/74, `mustache_test` 17/17,
`00_basics/06_host_specific_data/` acceptance 14/14 including
`16-variable-references-good-entry-survives.cf`.

**UTF-8 probe (Part 2), exact hex dumps:**
```
valid "wéird" (77 c3 a9 69 72 64)
  -> libntech encode -> "wéird" (77 5c 75 30 30 65 39 69 72 64)
  -> RestoreUtf8InJson -> UNCHANGED

invalid lone 0xE9 "latin1-<E9>-name"
  -> libntech encode -> "latin1-é-name"  <- IDENTICAL escape shape
  -> RestoreUtf8InJson -> UNCHANGED
```
Both collapse to the same escape text — the mechanism that makes them
indistinguishable.

**`simulate_mode_test` under the fixed libntech:** 15/17 pass, 2 expected
failures (`test_special_characters_in_path` — cosmetic, asserts the old
raw-byte output shape; `test_invalid_utf8_in_path` — the real finding, a
mismatch between the original raw byte and the correctly-decoded "é").

**PRs verified live via `gh pr view` before any comment was posted**: all
of `6305, 6307, 6308, 6309, 6311, 6312, 6313, 6314, 6316` confirmed `OPEN`
`mergeable=MERGEABLE`, each title carrying its CFE number.

**11 Jira writes this session**: `CFE-4715` (description PUT), `CFE-4716`
(description PUT + comment `159456`), and comments on `CFE-4718, 4725,
4727, 4729, 4732, 4733, 4734, 4735, 4736, 4737, 4738`.

## Operator Feedback

- Corrected my first-pass read of CFE-4715/4716: not "no link to code at
  all" (there was a PR link) but a stale status banner making an already-
  fixed PR look unready — more precise diagnosis than my initial framing.
- "if the results of the test might affect one of the tickets, do it
  before the ticket sweep" — sequencing instruction, followed: UTF-8 test
  ran and its finding was posted before the broader sweep began.
- "It makes sense for this to be a comment, not a new issue?" — mid-turn
  check confirming the comment-vs-new-ticket judgment call was sound.
- Corrected the scope estimate mid-request: "I think there are
  significantly more than 13... everything from CFE-4715 to CFE-4740 is
  ours, that is 25 [26] issues" — the sweep had been about to stop at the
  original 15-ticket batch; widened to the full range as instructed.

## Where We're Going

1. **THE NEXT ACTION**: none mandatory — this is a genuinely closed,
   clean pause point. If resuming upstream work, a `gh pr list` sweep
   across both repos would be the natural next check, given the tickets
   are now all correctly linked and might prompt fresh review.
2. `frdminc/tendcf#3` stays open until `libntech#297`, `libntech#298`, and
   `cfengine/core#6320` all merge upstream — no local action needed until
   then; `libntech-overlay`/`core-cmdbkey` worktrees are kept alive for it.
3. The `RestoreUtf8InJson()` design question (replacement char? error out?
   separate raw/base64 field?) is now on record in CFE-4716 comment
   `159456` but has **no decision** — it belongs to whoever reviews P-2
   upstream, not to this session.
4. Other open, not-yet-chosen options: flesh out generic bundle gaps (env
   rendering, systemd/runit, unit-writer detector, secretspec);
   `frdminc/tendcf#4` stays blocked on Step 2/Android.

## Quick Start

```sh
cd ~/src/tendcf && git log --oneline -3   # expect 235f199 at HEAD

# Re-check the #3 overlay build state if resuming it:
cd ~/src/core-cmdbkey && git log --oneline -1 && git status --short
# expect: "M libntech" (submodule pointer dirty at 45c816c)
# if reset, re-fetch:
cd ~/src/core-cmdbkey/libntech && \
  git fetch /Users/djbclark/src/libntech-overlay overlay/tendcf-3 && \
  git checkout 45c816c

# Check for new upstream reviewer activity across the now-correctly-linked PRs:
gh pr list --repo cfengine/core --state open --search "CFE"
gh pr list --repo NorthernTechHQ/libntech --state open
```
