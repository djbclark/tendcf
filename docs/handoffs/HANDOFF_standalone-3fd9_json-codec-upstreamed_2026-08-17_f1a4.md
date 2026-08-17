---
schema_version: 1
handoff_id: f1a4
parent_handoff_ids: [9997]
lineage: deterministic
chain: [standalone-3fd9]
repo: tendcf
workspace: main
branch: master
head_sha: 9262210015aa090694c6eac0d2c084a2f2e892a6
created_at: 2026-08-17T15:14:07-0400
writer: claude-code
---

# Handoff — the JSON codec fix went upstream, and it uncovered another defect

## The Goal

Session opened with `/baton` to resume `9997`, whose owed next action was
**task #10, CFE-4730**: libntech's JSON string codec, which silently corrupts
valid standard JSON on read. `9997` had left it filed but unfixed and called it
"the most serious open item in the register".

**That is now done end to end** — fixed, verified, and offered upstream as
[`NorthernTechHQ/libntech#293`](https://github.com/NorthernTechHQ/libntech/pull/293).

Along the way a **new, distinct defect** was found, verified and filed:
**CFE-4731 / register B-14**, the parser double-decode.

The operator paused mid-session and then resumed; the pause was clean and
nothing partial went out.

## Where We Are

`tendcf` clean at `9262210`, pushed. All five sibling worktrees clean, **zero
stashes anywhere**:

| workspace | branch | head | dirty |
|---|---|---|---|
| `/Users/djbclark/src/libntech-jsonstr` | `fix/json-string-codec` | `90cf8cc` | no |
| `/Users/djbclark/src/core-p1` | `simulate-keep-chroot` | `f6c06f9e2` | no |
| `/Users/djbclark/src/core-p2` | `simulate-json` | `b3a6c3da5` | no |
| `/Users/djbclark/src/libntech-fixes` | `fix/json-number-fatal-exit` | `11725b0` | no |
| `/Users/djbclark/src/core-json` | `fix/json-number-rendering` | `32c38f8ab` | no |

**Nothing is in flight.** No uncommitted work, no stashes, no running agents,
no pending background jobs.

### Done — CFE-4730 / B-13 fixed and upstreamed

[`NorthernTechHQ/libntech#293`](https://github.com/NorthernTechHQ/libntech/pull/293)
— **OPEN, MERGEABLE**, one commit `90cf8cc`, 2 files, **+376/−30**, trailer
`Ticket: CFE-4730`. Cut from upstream `master` `0c0620d`, *not* from the
existing `fix/json-number-fatal-exit` stack, so it is independently landable.

Both halves fixed together, which was the hard requirement — fixing only the
writer would have left libntech misreading its own files:

- **Encoder** now decodes its input as UTF-8 with strict validation and escapes
  the **code point**, surrogate-pairing outside the BMP. Output stays pure ASCII
  and is byte-identical for ASCII input. Invalid-UTF-8 bytes keep the historical
  per-byte `\u00XX` escape.
- **Decoder** handles the full BMP, emits UTF-8, combines surrogate pairs, and
  substitutes U+FFFD for an unpaired surrogate or malformed escape instead of
  corrupting it into literal text.
- `HexStringToChar()` → `FourHexDigitsToInt()`: no `strlen`, no `alloca`, no
  `isdigit()` negative-`char` UB.

### Done — the register, the ticket, and the sibling PR

- `tendcf` `03c3438` + `9262210` — `docs/architecture/upstream-register.md`:
  B-13 row moved to **done** with the full fix description and verification
  record, new **B-14** row inserted, CFE key table extended to CFE-4731, and a
  new subsection recording how B-13's fix interacts with P-2's workaround.
- **CFE-4730** updated: its stale *"No patch offered yet"* line corrected, the
  PR linked, the compatibility consequence stated, CFE-4731 cross-referenced.
  Verified by reading the stored description back, not by trusting the `204`.
- **`core#6294`** commented
  ([issuecomment-5319082783](https://github.com/cfengine/core/pull/6294#issuecomment-5319082783))
  pointing at the root-cause fix, stating the no-conflict finding, and offering
  to strip `RestoreUtf8InJson()` if maintainers prefer the libntech fix.
  Verified as **exactly one** such comment — the idempotent retry did not
  double-post.

### New — CFE-4731 / register item B-14

**The JSON parser double-decodes string escapes.** `JsonParseAsString()`
(`libutils/json.c:2184` **on upstream master `0c0620d`**) already performs a
complete unescaping pass — `\\`, `\"`, `\/` written literally, `\b \f \n \r \t`
written as control characters, only `\u` left verbatim — and the three call
sites (`:2405`, `:2479`, `:2668`) then run `JsonDecodeString()` over that
**already-decoded** text.

**Mind which tree you are citing.** On the B-13 branch the same code sits ~210
lines lower — `2394`, `2615`, `2689`, `2878` — because the fix adds helpers
earlier in the file. I filed CFE-4731 with the *branch* offsets by mistake and
corrected the ticket in the same session; **cite master offsets upstream**.

Measured on stock `0c0620d` **and again with B-13's fix applied**, identical
both times, so the fix neither causes nor cures it:

```
document:  {"p": "C:\\temp\\new"}     valid JSON for the path  C:\temp\new
python3:   'C:\\temp\\new'            43 3a 5c 74 65 6d 70 5c 6e 65 77
libntech:  'C:<TAB>emp<NL>ew'         43 3a 09 65 6d 70 0a 65 77
```

Filed as [CFE-4731](https://northerntech.atlassian.net/browse/CFE-4731).
**Not fixed.** Any Windows path, regex, or backslash-bearing string in JSON
data is silently corrupted.

### Blockers

**None.** The GitHub 503 outage described below **recovered** — both the PR and
the comment went through. Do not re-inherit it.

The only standing constraint is the model rule: PR-bound C goes to a
`fable-deep` subagent with `model` pinned to `'fable'`, because the main
session runs Opus 5.

### Files changed this session

**`tendcf`** — two commits, both pushed, one file:
- `03c3438` `docs/architecture/upstream-register.md` (+22/−2) — B-13 row to
  done, B-14 row added, CFE key table extended, P-2 interaction subsection.
- `9262210` same file — B-13's Upstream cell filled with PR 293.

**`/Users/djbclark/src/libntech-jsonstr`** — new worktree, committed into
`90cf8cc`, 2 files, +376/−30: `libutils/json.c` (+270/−30, adds
`Utf8DecodeCodePoint()`, `Utf8EncodeCodePointWriter()`, `FourHexDigitsToInt()`,
rewrites the encoder `default:` arm and the decoder `case 'u':` arm) and
`tests/unit/json_test.c` (+136, three new cases).

**No memory files written this session.**

## What We Tried

Failures and near-misses, chronological. These are the expensive ones.

1. **THE BIG ONE — a stale probe binary in the shared scratchpad nearly made me
   report the *unfixed* output as the fixed result.** I wrote a `probe.c`,
   compiled it with `cc ... 2>&1 | head -10`, saw `cc rc=0`, and ran
   `$S/probe` — which printed `city = u4e2du56fd`, i.e. the bug still present.

   Both halves of that were wrong. The `rc=0` came from **`head`, not the
   compiler** (the pipe swallowed `cc`'s status), and `$S/probe` was a
   **leftover binary the Fable subagent had built against the old library** —
   the subagent shares this session's scratchpad directory. My compile had
   actually failed with `platform.h`-not-found.

   **Rules: never read `rc` through a pipe, and never reuse a generic artifact
   name in the shared scratchpad — a subagent may have written one already.**
   Fixed by compiling with `-DHAVE_CONFIG_H` to a distinct name (`myprobe`) and
   checking `cc`'s own status. Had I not noticed, I would have reported a
   working fix as broken.

2. **`gh pr create` failed with HTTP 503 for ~20 minutes** — GitHub's
   **graphql** endpoint was down while **REST stayed healthy**. `gh pr create`
   and `gh pr list` both use graphql and both failed; `gh api repos/.../pulls`
   worked fine and confirmed no PR had been created, which is how I ruled out a
   duplicate before retrying. Later the REST **write** path went down too
   (`gh api user` failed) while reads recovered first.

   Handled with an **idempotent retry script** that checks for the artifact
   *before* every create attempt. That guard is why there is exactly one PR and
   exactly one comment despite retries and a mid-flight stop.
   `scratchpad/create_pr.sh` and `scratchpad/post_comment.sh`.

3. **The first `make check` run did not prove what I thought it proved.** I ran
   `rm -f json_test && make check` and got 39/39 — but `rm -f json_test` only
   removes the **linked binary**, not `json_test.o`, so a stale object could
   have been linked and the *new* tests might never have run. Re-ran with
   `rm -f json_test json_test.o`, which forced a real recompile and showed
   `json_test` going **69 → 72 cases**. Verify the artifact you think you
   rebuilt actually rebuilt.

4. **My first cross-check of the double-decode against python was garbage**,
   because shell quoting mangled the JSON document — python saw four
   backslashes where C saw two. Redone by writing the documents into a `.py`
   file rather than passing them through `bash -c`. **Do not hand-quote JSON
   containing backslashes through a shell.**

5. **The first CFE-4730 description patch would have left a falsehood
   standing.** My edit added "a patch is now offered" but left the existing
   sentence *"No patch offered yet."* two lines below it. Caught by reading the
   assembled text before the `PUT`. Anchor-and-replace the stale sentence, do
   not just append a newer one.

6. **I filed CFE-4731 with line numbers from the wrong tree.** The citations
   (`2394`, `2615`, `2689`, `2878`) came from `libntech-jsonstr`, which has
   B-13's fix applied and therefore ~210 extra lines above them. A maintainer
   reading the ticket against upstream `master` would have landed in the wrong
   function. Caught during this handoff's Quick Start verification, and
   corrected on the ticket (now `2184`/`2405`/`2479`/`2668` with a note about
   the branch offsets). **When citing line numbers on a public tracker, read
   them from the tree the reader will open, not the one you are working in.**

## Key Decisions

- **Verified every subagent claim myself rather than accepting the report** —
  rebuilt, re-ran the suite, and **redid the discrimination test my own way**
  (reverting `json.c` to pristine `0c0620d` and keeping the new tests, rather
  than repeating the agent's stash procedure). Also re-derived **all 29
  hard-coded test expectations** from python3. Rejected: trusting a clean
  report, which is exactly what put `#6293`/`#6294` in the hold-off state in
  the first place.
- **Encoder emits `\uXXXX` code-point escapes rather than raw UTF-8** (the
  agent's call, which I endorsed). Output alphabet stays pure ASCII, so
  consumers that already handled `\uXXXX` just get correct values instead of
  suddenly receiving raw multibyte where they always saw 7-bit ASCII. Rejected:
  raw-UTF-8 passthrough — it needs the same strict validator anyway, so it
  simplifies nothing while adding a transport-visible change. The PR body
  **explicitly offers to reverse this** if maintainers prefer.
- **Invalid-UTF-8 input keeps the per-byte `\u00XX` escape.** Rejected: U+FFFD
  substitution (destroys the byte value, bad for filenames) and erroring
  (`JsonEncodeStringWriter` is `void` and public; callers do not check).
- **No bug-compatibility mode for old-encoder output.** At the data level a
  reader cannot distinguish "old libntech wrote this" from "a conformant writer
  meant these code points", so a compat switch would just reintroduce the bug.
  Rejected: a compat flag; offered a one-off conversion tool instead.
- **Filed B-14 separately rather than folding it into #293.** Different
  function, independently reviewable, and the register's own rule is one branch
  per upstream contribution. Disclosed in the PR body regardless.
- **Dropped the `Co-Authored-By: Claude Opus 5` trailer** the harness mandates,
  and reordered to `Changelog:` then `Ticket:`. Prior upstream commits
  (`f6c06f9e2`, `b3a6c3da5`) carry **no** `Co-Authored-By` at all, and the
  attribution would have been inaccurate anyway since Fable wrote the code.
  Match the project's established convention on work sent to a third party.
- **Did not remove `RestoreUtf8InJson()` from `#6294`.** Nothing is decided
  upstream and `#293` may be reshaped or declined; `#6294` must stand alone.
- **Stopped the outward-facing retry when the operator said "pause"**, rather
  than letting a queued comment post itself. Confirmed nothing had gone out
  before reporting.

## Evidence & Data

**The defect, reproduced by the owning session before any delegation:**

```
$ printf '{"city": "\u4e2d\u56fd", "cafe": "caf\u00e9"}\n' > /tmp/data.json
$ python3 -c "import json; print(json.load(open('/tmp/data.json')))"
{'city': '中国', 'cafe': 'café'}
$ cf-promises -f /tmp/p.cf --show-vars | grep -E 'city|cafe|main\.d'
default:main.city   u4e2du56fd
default:main.cafe   <non-printable>
default:main.d      {"cafe":"caf\u00e9","city":"u4e2du56fd"}
```

The writer half, measured separately by feeding it **raw** UTF-8:

```
input:     raw UTF-8 中国  (e4 b8 ad e5 9b bd)
emitted:   {"city":"\u00e4\u00b8\u00ad\u00e5\u009b\u00bd"}
python3 reads that back as: 'ä¸\xadå\x9b½'      <- mojibake, round-trip FAIL
```

**Three reader defects, not one** — the register's B-13 row already had all
three; `9997`'s prose had compressed them:
1. code points > U+00FF → literal text (cursor never advances past the `u`)
2. code points ≤ U+00FF → a single raw byte, i.e. **Latin-1, not UTF-8**
3. no surrogate-pair handling at all

**Verification, all re-run by the owning session:**

```
make -j2                                rc=0, 0 warning: lines
tests/unit make check                   rc=0, 39/39 test binaries PASS
json_test (forced full recompile)       All 72 tests passed  (baseline 69)
```

**Discrimination, done my own way** (`git checkout 0c0620d -- libutils/json.c`,
new tests kept):

```
unfixed:  json_test rc=3,  "3 out of 72 tests failed!"
          exactly test_string_encode_unicode, test_string_decode_unicode,
          test_parse_unicode_strings
restored: sha256 b38c99e8eb5edcf50583c44934cbafada96ef6d086a947b663ea5cc77b43a76f
          (byte-identical), tree clean, json_test rc=0
pristine json.c sha256 = 73e2d81246b3efd5b3ea55ae15f1323a9055f929b03b222a7187f704741c028a
```

**All 29 test expectations independently re-derived from python3** — escape
forms, UTF-8 byte sequences, and every "this is/is not valid UTF-8" claim
(`80`, `e9 78`, `caf c3`, `c0 af`, `ed a0 80`, `f5 80` all confirmed rejected
by python's decoder). **0 failures.**

**End to end against the fixed library**, the original bug document:

```
city         = e4 b8 ad e5 9b bd   |中国|
cafe         = 63 61 66 c3 a9      |café|
reserialized = {"cafe":"caf\u00e9","city":"\u4e2d\u56fd"}
   -> python3 reads that back as {'cafe': 'café', 'city': '中国'}   PASS
```

**The UTF-8 validator was checked boundary by boundary** by the owning session:
`0xC0`/`0xC1` excluded, `0xE0`→`0xA0` overlong guard, `0xED`→`0x9F` surrogate
guard, `0xF0`→`0x90`, `0xF4`→`0x8F` cap, `0xF5+` rejected. NUL-safety holds
because `second_min` is always ≥ `0x80`, so a NUL at `s[1]` always fails the
range check before any further read. Reader surrogate path is likewise
over-read safe: `FourHexDigitsToInt(c+2)` succeeding guarantees `c[2..5]` are
non-NUL, so `c[6]` is in bounds and each later read is short-circuited.

**The P-2 interaction, read from source rather than executed:**
`GetJsonEscapedByte()` in `cf-agent/simulate_mode.c` ends with
`if (value > 0xff) return false;`. So a correct `\u4e2d` is not recognised and
passes through untouched — **no double-processing, no corruption if both
land**. Consequence: `--simulate=json` would emit `\u4e2d` escapes rather than
raw UTF-8, still conformant, but P-2's acceptance `.expected` asserts the raw
form and would need refreshing. **Not executed** — `core-p2` pins libntech at
`5b5d04e1` and rebuilding it was out of scope.

**Live upstream state at session end:**

```
core#6293   OPEN MERGEABLE f6c06f9e2   CLA pass   no maintainer response
core#6294   OPEN MERGEABLE b3a6c3da5   CLA pass   no maintainer response
libntech#291 OPEN MERGEABLE e76700b05              no maintainer response
libntech#293 OPEN MERGEABLE 90cf8cc     1 comment (mender-test-bot), 0 reviews
```

**`mender-test-bot` posted the same opaque pipeline error on `#293` that it
posted on `#291`** — a link to a GCP console we cannot open. Their CI
infrastructure, not our code. Not actionable; do not chase it.

**tendcf carries no non-ASCII.** `git ls-files` filtered to `.json`/`.cf` and
grepped for `[^\x00-\x7F]` returns **nothing**, so this codec fix cannot move
any tendcf measurement — the register's re-measure rule is discharged.

**Jira:** `CFE-4731` created (`POST /rest/api/2/issue`), description read back
at 3563 bytes with the repro and cross-reference intact. `CFE-4730` updated
twice, both `HTTP 204`, both verified by read-back.

**Quota at session end:** gmail active, 5h 73% / 7d 60% / Fable 63% (resets
Aug 21). One Fable agent consumed ~133K subagent tokens over ~19 minutes.

## Operator Feedback

- **"pause"** mid-session, then **"resume"**. On pause I stopped the one
  outward-facing action in flight (the queued `#6294` comment) rather than
  letting it fire, confirmed nothing had gone out, and wrote the Tier 1 log so
  the pause was durable. On resume it posted cleanly.
- **"go with the proposed plan"** — CFE-4730 first, then the six unfiled items.
- Standing, still in force from `ee9c`: *"You do not need to wait for me to open
  PRs or send emails, however you do need to hold off for long enough to
  minimize the chances of posting something incomplete or wrong."*
- Standing, from `9997`: retest an inherited blocker before repeating it. Two of
  `3a89`'s were false. This session inherited **none** that proved false.

## Where We're Going

1. **THE NEXT ACTION — task #2: the six ticketed items that still have no
   upstream PR.** B-1 (CFE-4728), B-2 (CFE-4729), **B-8 the only true fail-open
   (CFE-4726)**, core half of B-10 (CFE-4725), B-12 unwritten (CFE-4723), and
   the exec_timeout termination half (CFE-4727) — **start from the ALARM_PID
   theory, its refutation is retracted**. Recommend starting with **B-8**, the
   only true fail-open and the highest-value of the six. Then E-9 and
   `services:`. PR-bound C, so `fable-deep` with `model: 'fable'`.
2. **Watch `libntech#293`.** Its body explicitly offers to reverse the encoder
   trade-off (code-point escapes vs raw UTF-8) and to split things differently.
   If maintainers take it, `#6294`'s `RestoreUtf8InJson()` can come out —
   already offered in the comment. **Do not pre-emptively remove it.**
3. **B-14 / CFE-4731 is filed but unpatched.** Any fix must be coordinated with
   `#293`'s decoder, which **deliberately** omits `\/` handling and omits U+FFFD
   for unknown non-`u` escapes, because either would corrupt inputs the
   double-decode currently leaves intact by accident. Revisit both together.
4. **Watch `#6293`/`#6294`** for maintainer response — still none since
   2026-08-15.
5. Housekeeping, still not urgent: `git worktree remove` for `core-p1`,
   `core-p2`, `libntech-b4`, `libntech-jsonstr`; `core-json` needs
   `make clean` first. Disk is fine.

## Quick Start

```bash
# 0. Model gate — PR-bound C only via a fable-deep subagent, model pinned to 'fable'
cswap list                      # confirm Fable headroom before task #2

# 1. Live upstream state
gh pr view 293  -R NorthernTechHQ/libntech --json state,mergeable,comments,reviews
gh pr view 6293 -R cfengine/core --json state,mergeable,headRefOid   # expect f6c06f9e2
gh pr view 6294 -R cfengine/core --json state,mergeable,headRefOid   # expect b3a6c3da5
# NOTE: gh pr view/list use graphql. If it 503s, REST still works:
#   gh api "repos/NorthernTechHQ/libntech/pulls?state=all&per_page=50" --jq '.[] | "\(.number) \(.head.label)"'

# 2. The codec worktree (built, clean). Baseline: rc=0/0 warnings, 39/39, json_test 72
cd /Users/djbclark/src/libntech-jsonstr && git log --oneline -1   # 90cf8cc
make -j2 && (cd tests/unit && rm -f json_test json_test.o && make check)
#   ^ remove the .o too, not just the binary, or a stale object gets relinked

# 3. Reproduce B-14 / CFE-4731 (the unfixed one) in 20 seconds
cd /tmp && printf '{"p": "C:\\\\temp\\\\new"}\n' > dd.json
python3 -c "import json; print(repr(json.load(open('dd.json'))['p']))"   # 'C:\\temp\\new'
# libntech gives C:<TAB>emp<NL>ew — mechanism at libutils/json.c:2394 vs :2615/:2689/:2878

# 4. Jira (token via the broker only; never echo it). /api/2/search is HTTP 410.
TOKEN=$(sudo-secretspec get ATLASSIAN_CFENGINE_API_TOKEN --reason "<why>")
BASE=https://northerntech.atlassian.net
curl -sS -u "djbclark@gmail.com:$TOKEN" "$BASE/rest/api/2/issue/CFE-4731?fields=summary,status"
```

**Do not** build or modify `/Users/djbclark/src/cfengine-core` — other work uses
it and its libntech submodule must stay uncommitted. Builds at `-j2`/`-j4`,
never `-j8`.

**`diff_mode`, `manifest_mode` and `manifest_full_mode` fail on this host by
design** (core acceptance tests) — `.expected` hard-codes `Uid: (0/root)`,
`--gainroot=env` runs as uid 501, macOS has no `fakeroot`. Not a regression.

**Test a codec through a conformant decoder, never through its own** — python3's
`json` module. libntech's two halves were exact inverses, so a write-then-read
test passes on completely broken code. That trap hid B-13 for years.

**Retest any blocker you inherit from this document before repeating it.**
