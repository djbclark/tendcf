# Independent adversarial review — P-1 (`--simulate-keep-chroot`) and P-2 (`--simulate-json`)

**Reviewing model: `claude-fable-5` (Fable 5, xhigh effort).** Confirmed at the
operator's request. If this had resolved to an Opus model I would have said so
here in place of this line; it did not.

Date: 2026-08-17. Post-flight audit of two changes already open on
`cfengine/core` (PR #6293 / branch `simulate-keep-chroot` @ `64e2ac1cb`; PR
#6294 / branch `simulate-json` @ `05e18f038`). Worktrees `/Users/djbclark/src/core-p1`
and `/Users/djbclark/src/core-p2`. I ran no `make` in either shared tree; all
building was done from copies under my own `/tmp` scratch dir.

---

## 1. Verdicts

**P-1 — `--simulate-keep-chroot`: PUSH A CORRECTION.**
The concept and the common path are sound, but the only guard on the
operator-supplied path (`strlen(optarg) >= PATH_MAX`) is the wrong bound. It
permits `chroot_len` to reach `PATH_MAX`, which makes `ToChangesChroot()`
underflow its `strncpy` length to `SIZE_MAX` and overflow the static
`chrooted_path` buffer on the very first file it maps (verified with
AddressSanitizer). Sub-threshold long paths don't overflow but silently
truncate, so two distinct sensitive system files map to the *same* chroot path
(verified). Both defeat the exact safety property the commit message sells. The
shipped build is `-DNDEBUG`, so the `assert()` that would otherwise catch this
in `ToChangesChroot()` is compiled out.

Required correction (one item, plus test/doc):
- Replace the `>= PATH_MAX` check with one that reserves headroom for the
  longest path that will be mapped into the chroot. The real invariant
  `ToChangesChroot()` needs is `chroot_len + strlen(orig_path) + 1 <= PATH_MAX`
  for every system path it maps; the destination budget must be a small
  fraction of `PATH_MAX`, not `PATH_MAX - 1`. At minimum reject anything that
  leaves less than a generous reserve (the existing state-dir chroot path is
  tens of bytes, so a limit of, say, a few hundred bytes is safe and ample).
- Add a unit test for the path-mapping bound and, ideally, assert the created
  directory's mode (`0700`) — the shipped acceptance test covers neither.

**P-2 — `--simulate-json`: PUSH A CORRECTION (small).**
The non-JSON path is preserved (demonstrated below), the document can never be
*malformed* JSON, and it does **not** trip the JSON-number-writer defect family
(its numbers go through libntech's string-based integer path, not the
real/double path). But it has one concrete correctness bug and one
interoperability defect that its own test hides:

Required corrections:
- **uid/gid `(int)` cast** (`simulate_mode.c:1163-1164`): high uids/gids are
  emitted as negative numbers. Verified on the review host: `nobody` = uid
  4294967294, which `(int)` renders as `-2`, so any `nobody`-owned file reports
  `"uid": -2, "gid": -2`. Use an unsigned-preserving path (e.g.
  `JsonObjectAppendInteger64(..., (int64_t)(uintmax_t) st.st_uid)`).
- **Non-ASCII / UTF-8 filenames are mis-encoded for external consumers.**
  libntech's writer escapes every byte `>= 0x80` as `\u00XX`. That is well-formed
  JSON but a *standard* parser decodes `\u00XX` to code point U+00XX, not to the
  original byte, so a UTF-8 filename comes back as mojibake and an invalid-UTF-8
  byte comes back as a different byte (verified against Python's `json`). Since
  the whole point of the feature is machine consumption of filenames, either
  document this limitation prominently or fix the encoding, and stop the unit
  test from asserting the path "survives ... untouched" — it only round-trips
  through libntech's own non-conformant decoder.
- **Housekeeping:** the acceptance test still carries the literal placeholder
  `"description" -> { "CFE-XXXX" }` (`simulate_json.cf:26`).

Neither PR should be *withdrawn*: both features are wanted, both compile and pass
their shipped tests, and the defects are fixable in place.

---

## 2. Defects found

### D1 (P-1, VERIFIED) — path-length guard allows a static-buffer overflow
- **Where:** guard at `cf-agent/cf-agent.c:815` (`strlen(optarg) >= PATH_MAX`);
  the overflow lands in `libpromises/eval_context.c:3897`
  (`strncpy(chrooted_path + chroot_len + offset, orig_path, (PATH_MAX - chroot_len - offset - 1))`),
  buffer declared at `eval_context.c:3847` as `char chrooted_path[PATH_MAX + 1]`.
- **What breaks:** P-1 accepts any absolute path with `strlen <= PATH_MAX - 1`.
  `SetChangesChroot()` sets `chroot_len = strlen + 1` when the path has no
  trailing separator, so a path of exactly `PATH_MAX - 1` bytes → `chroot_len ==
  PATH_MAX`. Then in `ToChangesChroot()` the count `PATH_MAX - chroot_len - 1`
  underflows (size_t) to `SIZE_MAX`, and the destination is `chrooted_path +
  PATH_MAX` — the last byte of a `PATH_MAX + 1` buffer. The first mapped path
  (e.g. the record file `/changed_files`) overflows the buffer. The `assert()`
  at `eval_context.c:3875` that would catch this computes the same underflowed
  bound (so it passes even in a debug build) — and the shipped build is
  `-DNDEBUG` anyway, so it is compiled out.
- **Reproduce:** faithful standalone copy of `SetChangesChroot`/`ToChangesChroot`
  compiled `-DNDEBUG -fsanitize=address`
  (`/private/tmp/.../scratchpad/tochroot_repro.c`). With a 1023-byte
  (`PATH_MAX-1` on this host, `getconf PATH_MAX / == 1024`) absolute path, no
  trailing slash: ASan reports
  `AddressSanitizer: negative-size-param (size=-1)` in `strncpy`, destination
  "1024 bytes inside of global variable 'chrooted_path' ... of size 1025".
- **End-to-end reachability:** requires the operator to pass a ~1023-char path
  whose parent already exists (so `mkdir` succeeds). Contrived but reachable
  (`mkdir -p` a deep tree). The lower-severity sibling (D2) needs only a
  moderately long path.

### D2 (P-1, VERIFIED) — sub-threshold long paths silently collide/mis-target
- **Where:** same `strncpy` at `eval_context.c:3897`, same guard `cf-agent.c:815`.
- **What breaks:** for a keep-chroot path long enough that
  `PATH_MAX - chroot_len - 1` is smaller than a real system path (e.g. a
  1000-byte path leaves only 22 bytes), `ToChangesChroot()` truncates every
  mapped path. Two different sensitive files that share a long-enough prefix are
  written to the *same* chroot destination — the permission-mirrored copies
  collide / land at the wrong path, silently, with no error and no `notice`.
- **Reproduce:** `/private/tmp/.../scratchpad/trunc_repro.c` (same verbatim
  functions, `-DNDEBUG`). With a 1000-byte chroot path,
  `/etc/security/opasswd-secretA` and `...secretB` both map to
  `.../etc/security/opasswd-s` → prints
  `two distinct files map to SAME chroot path: YES (collision/corruption)`.
- This is the practical face of D1: the guard's bound is simply wrong, and the
  failure mode is silent data corruption rather than a clean rejection.

### D3 (P-2, VERIFIED) — high uid/gid emitted as negative numbers
- **Where:** `cf-agent/simulate_mode.c:1163-1164`,
  `JsonObjectAppendInteger(file_info, "uid", (int) st.st_uid)` (and `gid`).
- **What breaks:** `uid_t`/`gid_t` are unsigned; the `(int)` cast turns any uid
  `> INT_MAX` negative. `JsonIntegerCreate()` renders `"%d"`, so the file gets
  `"uid": -2` etc.
- **Reproduce:** on the review host `id -u nobody == 4294967294`, and
  `(int)4294967294 == -2` (confirmed). Any `nobody`-owned file (common for
  dropped-privilege daemons, and the default on macOS/BSD) would report
  `"uid": -2, "gid": -2`. Marked verified because the cast, the `"%d"` writer,
  the platform value, and the arithmetic are all confirmed and deterministic; I
  did not additionally run cf-agent against a `nobody`-owned file end to end.
- The shipped unit test never catches it: `test_created_file` compares against
  the *runner's own* (small) uid.

### D4 (P-2, VERIFIED) — non-ASCII/UTF-8 filenames mis-decode for standard parsers
- **Where:** all filename/target/name strings go through
  `JsonObjectAppendString` → libntech `JsonEncodeStringWriter`
  (`libntech/libutils/json.c:980`), which emits `\u00XX` for every byte `>= 0x80`
  (and control chars not in the named-escape set).
- **What breaks:** `\u00XX` is valid JSON but denotes code point U+00XX. A
  conformant parser decodes `/tmp/café` (`caf C3 A9`) → written as
  `"/tmp/cafÃ©"` → parsed back as `/tmp/cafÃ©` (UTF-8 `C3 83 C2 A9`),
  and an invalid byte `0xFF` → `ÿ` → `ÿ` (`C3 BF`). The filename the
  consumer receives is not the filename on disk.
- **Reproduce:** `/private/tmp/.../scratchpad/jsonesc_repro.c` (faithful replica
  of `JsonEncodeStringWriter` + `CharIsPrintableAscii`) piped to `python3 -m
  json`: decoded `'/tmp/cafÃ©'` and `'/tmp/badÿname'`, i.e. corrupted.
- **Severity/scope:** inherited from libntech (all CFEngine JSON behaves this
  way), so it cannot be fully fixed inside P-2, but P-2 is the first surface to
  route arbitrary, security-relevant *filenames* into a document sold for
  external machine consumption. The unit test `test_special_characters_in_path`
  gives false confidence because it round-trips through libntech's own decoder,
  which reverses `\u00XX` back to byte `0xXX` — it proves internal round-trip,
  not interoperability.

### D5 (P-2, SUSPECTED, low) — `ToNormalRoot()` has no bounds check
- **Where:** `simulate_mode.c:1186` calls `ToNormalRoot(target)` on an absolute
  symlink target; `ToNormalRoot()` (`eval_context.c:3902`) returns
  `orig_path + chroot_len - 1` guarded only by an `assert` (compiled out under
  `-DNDEBUG`).
- **What breaks (only if the invariant is violated):** if a chroot symlink ever
  held an absolute target *not* under the chroot prefix and shorter than
  `chroot_len - 1`, the return pointer runs past the target string. In practice
  this does **not** happen: `MakeLink()` (`libpromises/files_links.c:574-580`)
  always runs link targets through `ToChangesChroot()`, so agent-created chroot
  symlinks always point under the chroot, and `ToNormalRoot()` reverses them
  correctly. Reported as defense-in-depth: the safety rests on an unenforced
  invariant with the only guard disabled in release builds.

### D6 (P-2, minor) — write failure is silent; leaked global
- `WriteChangesJson()` failure in `main()` (`cf-agent.c:396`) logs `LOG_LEVEL_ERR`
  but does **not** change the exit status, so a consumer that asked for JSON and
  got none sees a success exit. Consider failing the run.
- `SIMULATE_JSON_FILE` (`cf-agent.c:115`) is a file-scope `char *` set via
  `xstrdup` (`cf-agent.c:831`) and never freed — a trivial leak at exit, and a
  style inconsistency with P-1, which stores its option in
  `config->agent_specific.agent` and frees it in `GenericAgentConfigDestroy`.
- `HashFile()` returns `void` (`simulate_mode.c:1171`), so a failed hash cannot
  be detected; `digest` stays zeroed and a bogus all-zero SHA-256 is emitted.
  Only reachable for an unreadable regular file inside the chroot (unlikely).

---

## 3. The eight questions

**1. P-1: is the chroot creation actually safe?**
Partly. `mkdir(keep_chroot, 0700)` (`generic_agent.c:1647`) is safe against
umask on the loose side: `0700 & ~umask` can only *remove* owner bits, never add
group/other, so the top directory is at worst too strict, never too loose — the
commit's permission reasoning holds *for the directory itself*, and the
permission-mirrored copies inside (which can be world-readable, e.g. `0644`) are
protected by that `0700` top dir. There is **no** TOCTOU on the final
component: P-1 does not stat-then-create; it calls `mkdir` directly, which is
atomic and fails `EEXIST` on any pre-existing file/dir/symlink, so an attacker
cannot pre-plant a symlink at the target to redirect. The real hole is
**path length** (D1/D2): `mkdir`'s mode is fine, but the operator-supplied path
feeds `chroot_len` into `ToChangesChroot()` with no adequate bound, causing
overflow at the boundary and silent truncation/collision below it. `0700` is the
right mode; it is *not enough* on its own — safety also assumes every parent
component is trusted (a parent that is a symlink or is attacker-writable can
relocate the tree; the `0700` top dir still protects the *contents*, but the
location is no longer what the operator specified). P-1 does not verify parents.

**2. P-1: is the absolute-path requirement enforced where the commit says?**
Yes, the check exists (`cf-agent.c:808`, `IsAbsPath(optarg)`), but `IsAbsPath`
(`libpromises/files_names.c:214`) only tests that the first character is a
separator. It does **not** reject `..` components, trailing slashes, or a path
whose parent is a symlink. `/a/../b` and `/a/b/` both pass and resolve normally
via `mkdir`; a trailing slash also changes `SetChangesChroot()`'s length math
(no `chroot_len++`), which happens to *avoid* the D1 boundary but not the D2
truncation. "Absolute" here means "starts with `/`", nothing more — acceptable
for a root-run operator tool, but the commit's framing implies more validation
than is performed.

**3. P-1: what happens on failure paths?**
`FatalError()` on `mkdir` failure (`generic_agent.c:1649`) is reasonable and
safe: it runs before `RegisterCleanupFunction(KeepChangesChroot)`, so no chroot
cleanup is registered when creation fails, and nothing is left to leak or
wrongly delete. The message includes the path and `strerror`, a minor
info disclosure (path existence, `EACCES` vs `EEXIST`) to whoever runs the
command — cf-agent normally runs as root, so this is low-severity and
consistent with existing behavior. The cleanup swap is correct: exactly one of
`KeepChangesChroot` (log-only, `generic_agent.c:1658`) or `DeleteChangesChroot`
is registered, and `DeleteChangesChroot` computes its target independently from
the *state-dir* path, so even a hypothetical double-registration could not
delete the kept tree. The chroot therefore cannot be deleted when it should be
kept. It *can* be kept-and-announced even when the run aborts partway (a later
`FatalError` still triggers `KeepChangesChroot`), so an incomplete tree may be
retained and announced as the "artifact of record" — low severity. Under a
signal that bypasses cleanup handlers, the keep path is unaffected (nothing
deletes the tree regardless); the delete path's behavior under signals is
pre-existing and unchanged. `--simulate-keep-chroot` without `--simulate` is
correctly rejected (`cf-agent.c:857`).

**4. P-2: is the JSON output correct and safe?**
No malformed JSON is possible: strings are always escaped to valid tokens,
numbers are `%d`/`PRIi64`/octal-string, no reals (so no NaN/Inf). Two defects:
non-ASCII/invalid-UTF-8 filenames are mis-decoded by conformant parsers (D4),
and high uid/gid are emitted negative (D3). On the number-defect family
specifically: **P-2 does not trip it.** `format_version`, `uid`, `gid` use
`JsonObjectAppendInteger` and `size` uses `JsonObjectAppendInteger64`; both
create `JSON_PRIMITIVE_TYPE_INTEGER`, stored as the decimal *string* from
`xasprintf("%d"/"%"PRIi64)` (`json.c:1640-1654`) and written verbatim — none
reach the real/`double` writer where the "copies silently changed values" family
lives. Permissions are an octal *string* (`"%04jo"` into a 5-byte buffer, safe
because `st_mode & CHMOD_MODE_BITS <= 07777` = 4 digits). SHA-256 digest buffer
`CF_HOSTKEY_STRING_SIZE == 133` is ample for 64 hex chars.

**5. P-2: does the non-JSON path still behave exactly as before?** Yes —
demonstrated by exact source correspondence, not asserted. The rewrite splits
the old `DiffPkgOperations` loop into `CollectPkgOperations()` (the reduction)
plus a printer, and changes the stored value from a pre-rendered `msg` to
`{name, arch, version}` rendered at print time. I diffed the base
(`git show 17eb78e6d:cf-agent/simulate_mode.c`, saved to scratch) against the
committed version line by line:
  - Every install entry is inserted from `SafeStringDuplicate(pkg_name/arch/ver)`
    and printed via `GetPkgOperationMsg(CHROOT_PKG_OPERATION_CODE_INSTALL, name,
    arch, version)` (`simulate_mode.c:967`) — identical arguments to the old
    insert-time render (`base:829`). Same for remove (`new:976` vs `base:877`).
    `GetPkgOperationMsg` is a pure function of `(op, name, arch, ver)`, unchanged.
  - Iteration order is identical: same `StringHash_untyped` keys (`name_arch`),
    same insertion sequence, same install-then-remove print order — so the map
    walk yields the same order.
  - The three log lines and their conditions are preserved: "No package
    operations done by the agent run" (file absent → `installed == NULL`),
    "No differences in installed packages to report" (both maps empty),
    "Showing differences in installed packages". The only structural change is
    that the first log moved out of `CollectPkgOperations` into
    `DiffPkgOperations` under the exact same condition.
  - The print loop now `free(msg)` after `puts` (the old code freed via the
    record destructor) — no leak, no double free.
No other function in `simulate_mode.c` is touched (the diff's hunks are confined
to the pkg-operation block and the appended JSON code; `ManifestFile`,
`ManifestChangedFiles`, `DiffChangedFiles`, `ManifestPkgOperations` are
byte-for-byte unchanged, and `ManifestPkgOperations` still uses the old
`PkgOperationRecord`). `main()` only adds an `if (SIMULATE_JSON_FILE != NULL)`
block, so with the option absent — every existing `--simulate` user — nothing
changes. Corroborating: P-2 changed no existing acceptance `.expected` file. See
§4 for what I did *not* do (a full A/B binary diff) and why.

**6. Memory, ownership and lifetime.**
P-1's `KEEP_CHANGES_CHROOT[PATH_MAX]` (`generic_agent.c:94`) is filled by
`strlcpy` from a path validated `< PATH_MAX`, so it fits with the NUL; it is a
static, so no lifetime issue; it duplicates the value already in
`config->agent_specific.agent.simulate_keep_chroot`, which *is* freed
(`generic_agent.c` destroy). Fine. P-2 does **not** use
`config->agent_specific` for the option — it uses the file-scope global
`SIMULATE_JSON_FILE`, `xstrdup`'d and never freed (D6, trivial). The JSON
builders are leak-clean: `ReadLenPrefixedString`
(`libntech/.../string_sequence.c:285`) assigns `*string` only on success and
frees on error, so `AddChangedFilesToJson`/`AddRenamedFilesToJson` never leak or
read uninitialized; `WriteChangesJson` transfers each array into the root object
before any early return, so the single `JsonDestroy(json)` covers everything;
the new `PkgOperation` is freed via `PkgOperationDestroy`; the transient `msg`
in the diff printer is freed. No double-free, use-after-free, or unchecked
`xmalloc` (libntech's `x*` allocators abort on failure by contract).

**7. Are the tests any good?**
*P-1 (acceptance only):* `keep_chroot.cf` would genuinely fail without the
change — an unknown `--simulate-keep-chroot` aborts cf-agent, so the kept copy
never appears and `kept_copy_has_changes` is false. It also checks the notice
log, default deletion, and the require-`--simulate` guard — all real behavior.
But it covers **none** of the security-relevant properties the commit
emphasizes: not the `0700` mode, not umask, not path length. The defects D1/D2
sail straight through it. It needs a unit test.
*P-2 (unit + acceptance):* `simulate_mode_test` is its own `check_PROGRAM` with
its own `main()`, so it is **not** shadowed by the macOS `rlist_test` XFAIL-abort
trap (that trap only affects tests appended to `rlist_test`). Its cases exercise
created/modified/deleted, dedup, renames, and the package net-set reduction, and
those would fail without P-2 (they call `WriteChangesJson`, which does not exist
in base). But two cases assert properties that hold *either way* and so give
false confidence: `test_special_characters_in_path` round-trips through
libntech's own decoder and therefore cannot detect D4, and `test_created_file`
uses the runner's small uid and therefore cannot detect D3. This is the same
failure mode the brief flags — a test that passes whether or not the real
property (interoperable, correct output) holds.

**8. What would a maintainer push back on?**
- **False/loose claims:** P-1's commit says the tree is "created with mode 0700,
  so that the permission-mirrored copies ... can neither land in a directory
  prepared with looser permissions nor mix with the contents of a previous run."
  The `0700`/`EEXIST` reasoning is sound, but the promise is undercut by D1/D2:
  a long path silently corrupts or collides the copies. That is not a false
  *statement* per se, but a reviewer testing the security framing will find it
  does not hold at the path-length boundary. I found no outright false factual
  claim in either commit message (P-2's "written before `GenericAgentFinalize()`
  because ... crypto is deinitialized there" is accurate; the non-JSON default
  "nothing changes" is accurate).
- **Trailers:** both commits use `Ticket: #6295`/`#6296`, which are GitHub
  **Discussions** (issues are disabled on the repo; the PRs are #6293/#6294).
  CFEngine's `Ticket:` trailer conventionally references a tracker ID
  (`CFE-####`/`ENT-####`) or an issue, not a discussion; expect pushback or a
  request to drop/replace it. `Changelog: Title` is a valid CFEngine convention.
- **Placeholder:** `simulate_json.cf:26` still has `-> { "CFE-XXXX" }`.
- **Style:** P-2's use of a file-scope global for the option instead of
  `config->agent_specific` (and never freeing it) diverges from P-1 and from the
  surrounding code; a maintainer may ask for consistency.
- **Robustness:** P-2's silent JSON-write failure (no effect on exit status) is
  likely to draw a comment.
- Option naming (`--simulate-keep-chroot`, `--simulate-json`) and log levels
  (`notice` for retention, `info` for JSON write) are reasonable.

---

## 4. How I controlled for the build traps

- **Trap 1 & 2 (stale libs / no relink):** I did not attempt any before/after
  measurement inside `tests/unit`, and I did not rely on any pre-built binary
  for a differential claim.
- **Trap 3 (`git stash` of a committed file):** for the P-2 non-JSON
  comparison I used `git show 17eb78e6d:cf-agent/simulate_mode.c` into my scratch
  dir (not stash), then diffed against `git show 05e18f038:...` and the working
  tree — exactly the technique the brief prescribes.
- **Trap 4 (`.libs` binaries link the installed dylib; `DYLD_*` stripped across
  exec):** not applicable — my reproductions are self-contained C programs
  (`tochroot_repro`, `trunc_repro`, `jsonesc_repro`) compiled in
  `/private/tmp/.../scratchpad`, linking nothing from the trees. Each embeds the
  relevant upstream function **verbatim** (cited by file:line) so there is no
  dylib to mislink.
- **Trap 5 (`rlist_test` XFAIL abort shadows later tests):** checked and stated
  under Q7 — `simulate_mode_test` is a standalone `check_PROGRAM` with its own
  `main()`, so no test it contains is shadowed by `rlist_test`.
- **NDEBUG:** I read the actual build flags from `core-p2/config.log` and
  `cf-agent/Makefile` (`CORE_CFLAGS ... -O2 -DNDEBUG`; `DEBUG_CFLAGS='-O2
  -DNDEBUG'`) and compiled all reproductions with `-DNDEBUG` so the `assert`
  guards behave as they do in the shipped binary (i.e. absent). `PATH_MAX` taken
  from `getconf PATH_MAX / == 1024` on this host.

**On the one before/after claim I did not measure at the binary level (Q5):** I
did not build base and P-2 cf-agent binaries and diff `--simulate=diff` prose
output. The transformation is a mechanical refactor whose render inputs,
map-iteration order, and log conditions I established are identical by exact
source correspondence (§Q5), and no existing acceptance `.expected` changed. A
full A/B build would have required either building the whole tree twice or a
fragile custom link against the shared `.libs` (squarely inside Trap 4), with a
real risk of producing a *false* verification — the exact outcome the brief
warns against. I judged the source-level demonstration more trustworthy here and
am flagging the choice explicitly rather than dressing reasoning up as
measurement.

---

## 5. What I did not check

- I did not run cf-agent end-to-end for P-1 to trigger D1/D2 in the real binary
  (would require constructing a ~1000+ byte path tree as root); I verified the
  mechanism with faithful verbatim reproductions instead. Reachability of the
  exact `PATH_MAX-1` overflow depends on the operator constructing such a path;
  D2's truncation is reachable with shorter, more plausible paths.
- I did not run cf-agent against a `nobody`-owned file to see `"uid": -2` land
  in a real document (D3); the cast, writer, platform value, and arithmetic are
  each confirmed.
- I did not build or run the P-2 unit suite in a private copy to add adversarial
  cases; I reproduced the two gaps (D3, D4) with a faithful replica of the
  libntech encoder and a standard parser.
- P-2's behavior on genuinely corrupt record files (odd rename count, malformed
  length prefixes) I reasoned about (fails safe → no output) but did not fault-
  inject.
- Windows/`__MINGW32__` code paths (drive-letter chroot mapping, the
  symlink-excluded branch) were read but not exercised — no Windows here.
- I did not review the acceptance `.expected` for `simulate_json.cf` for content
  correctness beyond noting the normalizer masks sha256/size/uid/gid/workdir
  (which, incidentally, is *why* the acceptance test also cannot catch D3).
- Concurrency: I did not run anything that writes into the shared worktrees.
