---
schema_version: 1
handoff_id: 9692
parent_handoff_ids: [1ff5]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 1d63963d9b11eff7a5bfc543b8a9a115db4c8a07
created_at: 2026-08-18T18:50:50-04:00
writer: claude-code
---
# Handoff — B-14 double-decode fix, mustache test coverage, two bonus defect fixes

## The Goal

Continue the upstream CFEngine/libntech contribution effort (chain
`standalone-3fd9`). This session: resumed via `/baton`, checked all
14 open `cfengine/core` PRs and the CFE-4736 RFC ticket for new
reviewer activity (none), then picked up unblocked work from an
audit of `docs/architecture/upstream-register.md` against real
git/GitHub state.

## Where We Are

Three punch-list items shipped, all clean:

1. **B-14 / CFE-4731** — libntech JSON parser double-decode bug, fixed.
2. **B-22** — `mustache_test.c` unit coverage for libntech (zero
   coverage → 17 cases), a follow-up flagged by B-13's review panel.
3. **B-23 / CFE-4740** — two minor defects in `mustache.c`, found
   while writing B-22, fixed in a stacked follow-up PR.
4. Housekeeping: `djbclark/core#7` (stale libntech-dependency tracking
   issue) closed — its gate was already satisfied.

All four PRs are open upstream, none reviewed yet (too soon). Register
(`docs/architecture/upstream-register.md`) updated and pushed for all
of it. Working tree is clean at `1d63963`.

### B-14 / CFE-4731 — JSON parser double-decode

**Root cause** (confirmed by reading, not assumed): `JsonParseAsString()`
in `libutils/json.c` already unescapes `\\`, `\"`, `\/`, `\b\f\n\r\t`
during parsing, leaving only `\u` verbatim. The three call sites
(string value ×2, object property value ×1 — object property **name**
never called it, that's relevant below) then ran the result through
`JsonDecodeString()` **again**, which re-scans for `\` and reinterprets
any backslash the first pass produced (e.g. from an escaped `\\`) as a
fresh escape introducer. Concretely: JSON `"C:\\temp\\new"` → pass 1
produces `C:\temp\new` (real backslashes) → pass 2 sees `\t` and `\n`
in that intermediate text and decodes them into a literal TAB and
NEWLINE, corrupting the string to `C:<TAB>emp<NL>ew`.

**Fix**: ported the `\u` decode logic (surrogate pairs + malformed-escape
U+FFFD fallback, already present in `JsonDecodeStringWriter` from
B-13/CFE-4730) into `JsonParseAsString()` itself, then deleted the
three redundant `JsonDecodeString()` calls. Object property **names**
never called `JsonDecodeString()` at all (a separate, milder bug — keys
with `\u` escapes stayed as six literal characters) and now get `\u`
decoded for free, since they share the same parse function.

**Worktree**: `~/src/libntech-mustachefix`... no — `~/src/libntech-doubledecode`,
branch `fix/json-double-decode`, created from fork commit `90cf8cc`
(the B-13 fix tip) since CFE-4731's own ticket text says the two
defects mask each other and should be revisited together. `libntech.h`
build: `./autogen.sh` (no extra configure flags needed — auto-detected
openssl/pcre2/libyaml correctly). Two libntech worktrees already
existed (`libntech-fixes`, `libntech-p3`) sharing one underlying git
dir; this is a third, added via `git worktree add`.

**Tests**: 2 new `json_test.c` cases (`test_parse_string_not_double_decoded`,
`test_parse_object_key_unicode_escape`), full JSON-document parses (not
just `JsonDecodeString()` in isolation, which the existing
`assert_decodes_to` tests already exercised and which don't catch this
integration bug). Discrimination proven by hand: `git stash` the
`json.c` fix, force a clean relink (**hit the stale-library trap again**
— `make json_test` alone reported "up to date" and kept linking the
OLD `libutils.la`; had to `make -C libutils clean` + full rebuild + `rm
-f json_test` to get a real unpatched binary), ran — 2/74 tests failed
with exactly the corruption from the ticket. Restored the fix, rebuilt
clean — 74/74 pass, full unit suite 37/37 binaries pass.

PR: [NorthernTechHQ/libntech#297](https://github.com/NorthernTechHQ/libntech/pull/297),
stacked on #293 (B-13). Jira CFE-4731 commented with the PR link.

### B-22 — mustache_test.c coverage

Delegated to a background `general-purpose` agent (model: opus) since
it was independent of the B-14 work. `libutils/mustache.c` (916 lines,
sole public entry `MustacheRender()`) had zero unit coverage — flagged
by B-13's review panel as a proposed follow-up, not a bug fix. Agent
was explicitly instructed: pure coverage, no bug hunting, no silent
fixes if it found anything (report separately instead).

Result: 17 cmocka cases (~90 assertions) in a new worktree
`~/src/libntech-mustachetest`, branch `test/mustache-coverage`. Covers
variables (incl. whitespace-padded tags, ints, bools), missing/null/
non-object/NULL hash, HTML escaping (both unescaped forms), dotted
names, comments (incl. CRLF), boolean/array/object/inverted sections,
the CFEngine-specific extensions (`{{.}}`, `{{@}}`, `{{%x}}`, `{{$x}}`,
`{{-top-}}`), delimiter changes, standalone-tag line removal, malformed
templates, empty input. Wired into `tests/unit/Makefile.am`. Built
clean under `-Werror -Wextra -Wall` and separately under
`-fsanitize=address`; `make check` 40/40 binaries pass. `cfengine/core`
has its own `mustache_test.c` but covers only the generic Mustache
spec (comments/interpolation/sections/inverted/delimiters), not the
CFEngine extensions — called out in the PR body so it doesn't read as
duplicate work.

PR: [NorthernTechHQ/libntech#296](https://github.com/NorthernTechHQ/libntech/pull/296).
Test-only, no Jira ticket (not a defect).

### B-23 / CFE-4740 — two defects found while writing B-22's tests

The mustache agent found and *reported without fixing* (per its
instructions) two things while reading `mustache.c`:

1. `:284,297` — `Log(..., "... at '%20s'...", input)` uses `%20s`
   (minimum field width) where `%.20s` (precision/truncation) was
   clearly intended, per the trailing `"..."` literal in both message
   strings. Effect: short remaining-template strings get left-padded
   with spaces instead of shown plainly; long ones dump the **entire**
   remaining template into the log instead of a 20-char snippet.
2. `IsTagStandalone()` (`:74`) — `for (const char *cur = tag_start - 1;
   ...)` forms a pointer one before the start of the input buffer when
   a non-renderable tag (a `#section` or comment) begins at offset 0.
   The existing test `"{{#b}}yes{{/b}}"` (added in B-22) exercises
   this exact case.

User's explicit instruction mid-session: fix and file both even though
neither had an observed failure mode — "it might gain one later."

**Verification, done honestly rather than oversold**: built under
`-fsanitize=undefined,pointer-overflow` with the fix `git stash`ed —
**no UBSan report fired**. UBSan's pointer-overflow check tracks
address-space wraparound, not per-object bounds for a `char*` with no
statically-known size, and the loop's `cur >= start` guard means the
invalid pointer is formed but never dereferenced — so this genuinely
has no reproducing failure mode under current tooling. Fixed anyway
per the standard (constructing an OOB pointer is UB regardless of
dereference) and said so plainly in the commit/PR/ticket rather than
claiming false verification. The log-padding bug **is** directly
observable: same stash-rebuild-run cycle showed
`'                a{{v'...` (16 spaces of padding) unpatched vs.
`'a{{v'...` patched, in the existing `test_malformed_templates` case.

Worktree `~/src/libntech-mustachefix`, branch
`fix/mustache-minor-defects`, stacked on B-22's tip. Filed
[CFE-4740](https://northerntech.atlassian.net/browse/CFE-4740) before
opening the PR (this repo's convention: ticket first, then `Ticket:`
trailer references something that actually exists — see
[[verify-tickets-check-discussions]]). PR:
[NorthernTechHQ/libntech#298](https://github.com/NorthernTechHQ/libntech/pull/298),
stacked on #296.

### djbclark/core#7 closed

Background audit agent flagged this GitHub tracking issue (our own
fork, not upstream) as substantively stale: its checklist item "confirm
core branches build against stock libntech, not yet done for #4/#5/#6"
was actually already satisfied — #4 (B-1) and #6 (B-8) were verified
against stock libntech `5b5d04e1` in a prior session (`core-acceptance`
worktree), and #5 (B-2) doesn't touch libntech at all so the gate never
applied. P-3 (the libntech dependency itself) has since moved past the
fork-PR stage to a real upstream submission
([NorthernTechHQ/libntech#291](https://github.com/NorthernTechHQ/libntech/pull/291),
tracked as CFE-4717). Posted a comment summarizing all three resolved
points and closed the issue.

## What We Tried

- **First attempt at reverting/relinking for B-14 discrimination failed
  silently**: `git stash push -- libutils/json.c` then `make json_test`
  reported "up to date" and ran the **still-patched** binary (tests
  passed, looked like no bug existed). This is the same stale-library
  trap noted in memory [[libpromises-edit-needs-library-rebuild]], now
  confirmed for libntech's autotools build too — a library-only source
  change doesn't always trigger the test binary's relink. Fix: `make
  -C libutils clean` + full top-level rebuild + `rm -f json_test`
  before relinking, every time a discrimination run needs a real
  before/after.
- **Full-suite rebuild under `-Werror -Wextra -Wall` (mustache defects
  verification) broke on unrelated pre-existing files**
  (`file_lib.c:1011`, `cmockery.c:989` — both `-Wsign-compare`, neither
  touched this session). Overriding `CFLAGS=` on the `make` command
  line replaces the configured flags entirely rather than appending,
  so it lost whatever warning suppressions the project's own configure
  step had set up. Backed off to the default configured flags (which
  is what upstream CI actually uses) instead of hand-picking a stricter
  set — `make check` then passed 40/40 clean.
- **Claimed UBSan verification for the mustache pointer-arithmetic fix,
  then had to walk it back** when the sanitizer genuinely didn't fire
  on the unpatched code. Left the honest (non-)result in the PR rather
  than the stronger claim the mustache agent's original report implied
  ("would trip UBSan" — it doesn't, empirically).

## Key Decisions

- **B-14 built on top of B-13's fork branch, not upstream master** —
  CFE-4731's own ticket text says the two defects mask each other
  (B-13's decoder deliberately skips `\/` and skips U+FFFD substitution
  specifically because the double-decode currently leaves those inputs
  intact by accident) and should be revisited together. Branch stacking
  documented in both the PR body and the register.
- **Did not touch `JsonDecodeString()` itself** — it's a public API
  (`json.h`), used only internally at the three now-removed call sites
  within this repo, but external consumers could call it directly.
  Left it as dead-but-public code rather than removing it.
- **Chose to fix the two mustache defects rather than leave them as a
  report-only note** — reversed from the mustache agent's own
  instruction (don't fix, just report) after the operator explicitly
  said to fix-and-file even without an observed failure mode. Filed a
  real Jira ticket (CFE-4740) rather than skip it since it's "just
  test-only" — these are code fixes, not test additions, so they don't
  qualify for B-22's "no ticket needed" treatment.
- **Rejected doing the UBSan-flags full rebuild with hand-picked
  `-Werror -Wextra -Wall`** after it broke on unrelated files; used
  the project's own default configured flags for the final
  correctness check instead, since that's what actually matters for
  landing upstream.

## Evidence & Data

- B-14 discrimination: unpatched → `2 out of 74 tests failed!` (exact
  corruption strings matching the ticket's reproduction); patched →
  `All 74 tests passed`; full unit suite → 37/37 binaries PASS both
  before B-14 (baseline) and after.
- B-22: `make check` → `All 40 tests passed` (mustache_test 17/17
  within that). ASan rebuild: clean.
- B-23: UBSan pointer-overflow rebuild → no report, either patched or
  unpatched (documented as a non-finding, not hidden). Log-padding
  diff: unpatched `'                a{{v'...` vs. patched `'a{{v'...`,
  captured directly from `test_malformed_templates` output.
- All PR/ticket links: libntech#296, #297, #298 (all OPEN, stacked
  #296→#298 and #293→#297); Jira CFE-4731, CFE-4740 (both `Open`,
  linked from their PRs).

## Operator Feedback

- Picked "2" (queued/other work) over waiting on upstream review —
  confirms the standing preference for using idle upstream-review time
  productively rather than polling.
- Explicitly selected B-14 over the mustache-test and core#7 options
  when offered a menu — recorded as the chosen priority, not assumed.
- Mid-turn instruction: pursue items 2 and 3 in parallel with item 1
  rather than sequentially — background-agent delegation was the right
  read of that ask.
- Mid-turn instruction: fix-and-file defects found along the way **even
  without an observed failure mode**, "it might gain one later." This
  generalizes past this specific session — treat future drive-by
  findings the same way rather than defaulting to report-only.
- Chose "quick-fix both defects now, then handoff" when asked, over
  skipping the defects or deferring the handoff — confirms defects get
  fixed inline when small, and handoff timing follows a natural
  stopping point flagged by context size, not an arbitrary point.

## Where We're Going

1. **Check for reviewer activity across all 17 open upstream PRs**
   (14 from before this session + #296/#297/#298 new this session):
   `gh pr list -R cfengine/core --author djbclark --json
   number,title,state,reviews,comments,updatedAt` and `gh pr list -R
   NorthernTechHQ/libntech --author djbclark --json
   number,title,state,reviews,comments,updatedAt`. Compare `updatedAt`
   against this handoff's `created_at` — anything newer needs a
   response.
2. **CFE-4736** (getopt RFC question) — still `Open`, unassigned, no
   answer as of last check. Re-check periodically; no action until a
   maintainer responds.
3. When PRs close, delete their worktrees — accumulated this session:
   `~/src/libntech-doubledecode`, `~/src/libntech-mustachetest`,
   `~/src/libntech-mustachefix`, plus the six `core-*` worktrees listed
   in the prior handoff (1ff5), all still open.
4. Re-run the `upstream-register.md` vs. real-git/GH audit periodically
   — this session found three stale register claims (B-14 "in
   progress" when actually shipped as #6314 under a different bug
   number; B-2's stock-libntech gate marked "not yet done" when it
   doesn't apply; `djbclark/core#7`'s premise disproven). The register
   is large enough now that hand-tracking drifts from reality faster
   than it gets corrected in the normal course of shipping fixes.

## Quick Start

```bash
cd /Users/djbclark/src/tendcf
git log --oneline -5   # confirm HEAD is 1d63963 or later

# Check all upstream PR/ticket activity since this handoff
gh pr list -R cfengine/core --author djbclark --json number,title,state,reviews,comments,updatedAt
gh pr list -R NorthernTechHQ/libntech --author djbclark --json number,title,state,reviews,comments,updatedAt

# CFE-4736 RFC status
sudo-secretspec run --reason "check CFE-4736" -- bash -c '
curl -s -u "djbclark@gmail.com:${ATLASSIAN_CFENGINE_API_TOKEN}" \
  "https://northerntech.atlassian.net/rest/api/3/issue/CFE-4736?fields=status,comment"'
```
