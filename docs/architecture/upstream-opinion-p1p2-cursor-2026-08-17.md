# Independent adversarial review — P-1 / P-2 (`--simulate-keep-chroot`, `--simulate-json`)

Reviewer: Cursor Grok 4.6. Input frozen in
`docs/architecture/UPSTREAM-P1-P2-REVIEW-BRIEF.md`. Trees:
`/Users/djbclark/src/core-p1` @ `64e2ac1cb` (PR 6293 / discussion 6295),
`/Users/djbclark/src/core-p2` @ `05e18f038` (PR 6294 / discussion 6296).
Neither shared worktree was written to; `make` was never run in them.
Measurements live under `/tmp/p1p2-review/`.

---

## 1. Verdict

**P-1 — push a correction.** The happy path works: a short absolute
non-existent path is `mkdir`'d 0700, the tree is kept, the real files are
untouched, and the default (no option) still deletes. That is not enough to
leave in front of maintainers. The new option advertises “absolute, not
yet existing, up to `PATH_MAX-1`, created 0700, so copies of sensitive
files can never land in a looser directory.” Two of those claims are
false under measurement, and the `PATH_MAX` check the commit added
protects the wrong buffer.

**P-2 — push a correction.** File-level `--simulate=manifest` and
`--simulate=diff` prose, with the new flag off, matched P-1/master after
normalising workdir, PID, and timestamps. Do not withdraw on regression
fear. Do not ship the JSON either: a UTF-8 filename is emitted as
per-byte `\u00XX` so a standards-compliant parser returns a different
string than the file on disk — the defect a machine-readable changeset
exists to avoid — and a failed JSON write still exits 0.

Neither change should be withdrawn. Both need a follow-up commit (or a
force-push of the still-unreviewed PR) before a maintainer should merge
them.

### P-1 corrections, exactly

1. Bound the keep path so `keep + "/" + orig` cannot overflow or
   silently truncate `ToChangesChroot()`'s `PATH_MAX+1` buffer; fail
   closed. The `strlen(optarg) >= PATH_MAX` check in `CheckOpts` does
   not do this.
2. Retract or qualify the “never a looser directory” claim. `mkdir(path,
   0700)` does not inspect the parent. A 0777 parent without a sticky
   bit is accepted. Interior dirs are permission-mirrored (`/tmp` inside
   the keep tree was `41777`).
3. Tests for mode 0700, `EEXIST`, relative path, and a keep path long
   enough that `ToChangesChroot` would truncate. Stop treating
   `default_chroot_deleted` and `keep_requires_simulate` as coverage of
   the new behaviour.
4. `Ticket: #6295` is a GitHub Discussion. `CONTRIBUTING.md` wants a
   Jira `CFE-` / `ENT-` key.

### P-2 corrections, exactly

1. Filenames in the JSON document must round-trip through an RFC 8259
   parser (`json.loads`, `jq`) as the same bytes as the path on disk.
   Per-byte `\u00XX` does not.
2. `WriteChangesJson` failure must fail the process (non-zero exit).
   Measured: write-to-directory logs two errors and exits 0.
3. Do not overwrite an existing `FILE` (P-1's “must not already exist”
   is the right precedent). Measured: `safe_fopen(..., "w")` truncates
   and also follows a same-owner symlink onto its target.
4. Replace `CFE-XXXX` in `simulate_json.cf`. Same `Ticket: #6296` vs
   Jira issue as P-1.
5. `HashFile()` is unchecked; a failure leaves a zero digest and still
   emits a `sha256` field. Check the result or omit the field.
6. The commit/PR text “without the new option, nothing changes” /
   “prose renderers are unchanged” is false as written:
   `DiffPkgOperations()` was rewritten. File-level prose was measured
   identical; say that, and that package prose now renders from
   `CollectPkgOperations()` at print time.

---

## 2. Defects found

### P-1.1 `ToChangesChroot` silently truncates (and can size-underflow) for a keep path the new option accepts — **verified**

`libpromises/eval_context.c:3847–3899` (pre-existing helper, newly
reachable). `SetChangesChroot` copies the keep path into
`chrooted_path[PATH_MAX+1]` and adds a trailing slash.
`ToChangesChroot` then:

```c
strncpy(chrooted_path + chroot_len + offset, orig_path,
        (PATH_MAX - chroot_len - offset - 1));
```

Binaries are built `-O2 -DNDEBUG` (`CORE_CFLAGS` in the P-1 Makefile),
so the `assert(strlen(orig_path) <= (PATH_MAX - chroot_len - 1))` is
gone.

P-1's new check (`cf-agent/cf-agent.c:815–820`) only rejects
`strlen(optarg) >= PATH_MAX`. That stops `strlcpy` into
`KEEP_CHANGES_CHROOT[PATH_MAX]` from truncating the *keep path*. It does
not bound `keep + orig`.

Standalone replica of that arithmetic, compiled `-DNDEBUG` like the
worktree:

- keep length `PATH_MAX-1` (1023), no trailing slash → `chroot_len ==
  1024`, `strncpy` n = `18446744073709551615` (`SIZE_MAX`).
  **Underflow = YES.**
- Same replica under ASAN: `negative-size-param: (size=-1)` abort
  inside `strncpy`.
- keep length 801 + orig body 300 → `strncpy_n=221`, **truncate=YES**,
  **nul_terminate=NO**.

Live `cf-agent` (libtool wrapper in-place, isolated `-w` workdir), keep
path length **1016** (the longest Darwin `mkdir` would accept; 1017–1023
fail `ENAMETOOLONG` before `SetChangesChroot`):

- CheckOpts accepted it, `mkdir` succeeded, mode 0700.
- Subsequent work tried to use `KEEP/tmp` and `KEEP/tmp/p1`.
- `/tmp/p1p2-review/wd-trunc/target-file` after stripping the leading
  slash is `tmp/p1p2-review/...`; remaining room was 6 bytes → `tmp/p1`.
- Agent logged `Failed to get the state of the immutable bit from file
  'KEEP/tmp/p1'` and `Failed to make directory: KEEP/tmp (mkdir: File
  name too long)`.
- `rc=0` anyway; keep notice printed; keep dir empty of the promised
  files.

On Linux `PATH_MAX` is typically 4096, CheckOpts allows 4095, and
`mkdir` can succeed. The size-underflow case is then live, not just
Darwin-blocked by `ENAMETOOLONG`.

The default chroot (`GetStateDir()/PID.changes`) is short, so this was
not a practical `--simulate` bug until an operator-chosen keep path.

### P-1.2 “0700 so copies cannot land in a looser directory” is overstated — **verified** (parent / interior); **suspected** (TOCTOU)

`libpromises/generic_agent.c:1647` is `mkdir(keep_chroot, 0700)` with
no parent check, no `O_NOFOLLOW`, no dirfd held across later
`ToChangesChroot` uses.

Measured:

| case | result |
|---|---|
| umask 0000, 0022, 0077 | keep dir mode **700** (standalone `mkdir` and live `cf-agent`) |
| parent mode 0777, no sticky (`stat` `40777`) | accepted; child 700 |
| parent is a symlink | `mkdir` followed it; 700 dir created in the real parent |
| dangling symlink at PATH | `mkdir` → `EEXIST`; fail-closed |
| interior `/tmp` after a successful keep | `stat` `41777` (`drwxrwxrwt`) — the real `/tmp` permissions, mirrored |

`0700` on the *leaf* is the right mode and umask cannot loosen it
(`0700 & ~umask` is still `<= 0700`). It is not “enough”:

- The parent can be world-writable without sticky. After `mkdir`
  returns, the code uses the path as a string. A rename-swap of that
  0700 directory for a symlink, by anyone who can write the parent, is
  the classic window. `/tmp`'s sticky bit happens to close that race
  there; a 0777 directory the operator pointed at does not. Not
  live-raced (would need a second uid); the window is in the code.
- Permission-mirrored copies of `/etc/...` sit under interior dirs
  whose modes are the originals. The 0700 root is the only gate. That
  gate is real for “other users cannot `cd` in,” and it is not what the
  commit sentence claims.

### P-1.3 `IsAbsPath` is a first-byte check; `..` and trailing slashes pass — **verified**

`libpromises/files_names.c:214–224`: `return IsFileSep(*path)`.

- Relative `relative/path` → rejected, `rc=1`. Good.
- Trailing slash `$WD/trail.changes/` → accepted, dir created 700,
  keep notice logged the path *with* the slash.
- `$WD/../p1p2-dotdot-keep` → accepted as absolute; `mkdir` resolved
  `..` (the keep notice fired; the earlier “no /tmp/p1p2-dotdot-keep”
  in notes was a test-script path-arithmetic error, not a reject).
- Windows `C:\...` is **suspected** rejected (`'C'` is not a file
  separator). The new acceptance test is already `test_soft_fail` on
  windows, so this will not be caught there.

No `realpath`, no `..` rejection, no “must not be a symlink in any
component.”

### P-1.4 Failed run after a successful `mkdir` still keeps the (partial) tree — **verified**

`mkdir` happens in `GenericAgentInitialize` *before*
`CheckWorkingDirectories`. A 755 `ppkeys` then `FatalError`s
(`generic_agent.c:2399`). Cleanup already has `KeepChangesChroot`
registered (`generic_agent.c:1658`), so `FatalError` →
`DoCleanupAndExit` → notice + keep. Measured: keep dir left behind on
that path; notice printed.

That matches “keep,” but it is a partial/empty tree on a failed run,
and `FatalError` includes `mkdir: %s` / `GetErrorStr()` (the operator
who supplied PATH; not a privilege boundary unless something else
relays the log).

SIGINT/SIGTERM (`libpromises/signals.c:155–160`) also
`DoCleanupAndExit(0)`, so keep-on-signal is the same path. Not
live-signalled.

### P-1.5 Two of five acceptance conjuncts pass without the change — **suspected** (would need an unpatched binary; the mechanism is in the test)

`tests/acceptance/29_simulate_mode/keep_chroot.cf:69–80`:

- `default_chroot_deleted` asserts pre-existing default cleanup.
- `keep_requires_simulate` is `not(returnszero(... --simulate-keep-chroot=... without --simulate))`. An *unknown option* also
  fails, so this conjunct is true on master.

The overall `ok` still depends on `kept_copy_has_changes`, so the file
is not purely decorative. There is no test of 0700, `EEXIST`, relative
path, `PATH_MAX`, or parent mode. No unit test at all.

### P-2.1 UTF-8 filenames in the JSON document do not survive a real JSON parser — **verified**

`libntech/libutils/json.c:1015–1021` (`JsonEncodeStringWriter`): any
byte outside printable ASCII (`c >= ' ' && c <= '~'`) becomes
`\u%04x` of that **byte**. UTF-8 `é` is `c3 a9` → `\u00c3\u00a9`.

`HexStringToChar` (`json.c:1060–1068`) then treats `\u00c3` as a
single byte 0xC3 (`c > 255` is the only Unicode ceiling). So
CFEngine's own `JsonParseFile` round-trips the bug, which is why
`test_special_characters_in_path` (`tests/unit/simulate_mode_test.c:278–292`)
passes.

Live `--simulate-json` of a files promise on
`/tmp/.../wéird file.txt`, then `json.loads` (CPython 3.14):

- raw JSON: `"path": ".../w\u00c3\u00a9ird file.txt"`
- Python decoded path hex: `...77c383c2a9697264...` (`wÃ©ird`)
- original filename hex: `...77c3a9697264...` (`wéird`)
- **roundtrip_equal_to_filename: False**

Newlines and quotes *are* escaped (`\n`, `\"`) — standalone encoder
and the quotes in the unit-test path are fine. Invalid UTF-8 (`0xFF
0xFE`) becomes `\u00ff\u00fe`, i.e. U+00FF U+00FE, not the original
bytes. Control bytes `0x01 0x1f 0x7f` become `\u0001\u001f\u007f`,
which is legal JSON and a real parser will round-trip those as those
code points / bytes.

This is the defect that matters for P-2: the document is for programs
that are not CFEngine's JSON parser.

### P-2.2 JSON write failure does not fail the process — **verified**

`cf-agent/cf-agent.c:394–401`: on `!WriteChangesJson(...)` it logs
`LOG_LEVEL_ERR` and continues. `ret` is unchanged.

`--simulate-json` pointing at a directory: two errors (`Failed to open
... (fopen: Is a directory)`, `Failed to write the simulated change
set to ...`), **`rc=0`**.

### P-2.3 `--simulate-json=FILE` overwrites, including through a same-owner symlink — **verified**

Unlike P-1, there is no “must not already exist.” `WriteChangesJson`
uses `safe_fopen(output_file, "w")` (`simulate_mode.c` near the end of
`WriteChangesJson`). `safe_fopen` creates with `CF_PERMS_DEFAULT`
(0600) and **does follow a trusted/same-owner symlink**.

Measured: a file containing `PREEXISTING` was replaced with a JSON
document, `rc=0`. A symlink `link.json -> victim.json` caused
`victim.json` to be overwritten.

No `PATH_MAX` check at all (P-1 added one for the sibling option).

### P-2.4 `HashFile` failure still emits a `sha256` — **suspected**

`simulate_mode.c:1171`: `HashFile(chrooted_path, digest, HASH_METHOD_SHA256, false);`
return is void. On `fopen` failure `hash.c:441–468` `memset`s the
digest to zero and returns. `HashPrintSafe` will then emit 64 `0`
hex digits as if they were a content digest. Not live-forced (would
need a regular file `lstat` can see but `safe_fopen` cannot).

`readlink(..., sizeof(target)-1)` (`simulate_mode.c` symlink branch)
does not detect truncation if the target is exactly `PATH_MAX-1`
bytes. **Suspected.**

### P-2.5 `CFE-XXXX` and the “prose is unchanged” claim — **verified**

`tests/acceptance/29_simulate_mode/simulate_json.cf:26` is
`"description" -> { "CFE-XXXX" }`. Sibling tests in that directory use
real keys (`ENT-5302`). A maintainer will trip over this.

Commit and PR body: “The prose renderers are unchanged and remain the
default; without the new option, nothing changes.” `git diff -U0`
against `upstream/master` for `simulate_mode.c` rewrites
`DiffPkgOperations()` in place (extract to `CollectPkgOperations`,
store `PkgOperation` instead of a pre-rendered message, `GetPkgOperationMsg` +
`puts` at print time) and only *then* adds `WriteChangesJson`. File
manifest/diff functions have no hunks. So the sentence is false for
`--simulate=diff` package output and true for file prose — which is
the path every current `--simulate` user is on, and which was
measured identical (see Q5).

### P-2.6 Numbers in this document go through libntech's JSON writer — **verified**, not a B-10-class fatal on this write path

`ChangedFileAsJson` uses `JsonObjectAppendInteger` for `uid`/`gid`/
`format_version` and `JsonObjectAppendInteger64` for `size`
(`simulate_mode.c:1163–1168`, plus `format_version` in
`WriteChangesJson`). Those call `JsonIntegerCreate` / `JsonIntegerCreate64`
(`"%d"` / `PRIi64`) and `JsonWrite` emits the already-formatted
string (`json.c:1640–1653`, `1715–1738`).

Live document: `"format_version": 1`, `"uid": 501`, `"gid": 20`,
`"size": 16` — JSON numbers, `json.loads` typed them as `int`.

This is the “rebuild from a C type” shape of the repo's JSON-number
defect family, but the values originated as `stat` fields, not as
parsed JSON lexemes. The write path does not call
`StringToLongExitOnError`. A consumer that feeds this document back
into CFEngine's JSON parser could still hit that family on a huge
`size`; that is a property of stock libntech `5b5d04e1`, which this
PR is correctly built against.

---

## 3. The eight questions

### 1. P-1: is the chroot creation actually safe?

For a short path whose parent the operator already trusts: **the leaf
is 0700, umask cannot loosen it, `EEXIST` is fail-closed, dangling
symlink at the last component is fail-closed.** That is the intended
model and it holds under measurement.

It is not safe in the sense the commit claims:

- Parent permissions are unexamined (0777 no-sticky accepted).
- `mkdir` then string-wise use is a TOCTOU against a hostile parent.
- Interior nodes are permission-mirrored (`/tmp` → `41777`).
- A keep path near `PATH_MAX` is legal at CheckOpts and then
  `ToChangesChroot` truncates composed paths (P-1.1). On Linux the
  `strncpy` n underflow is reachable.

`0700` is the right *leaf* mode. It is not enough.

### 2. P-1: is the absolute-path requirement enforced where the commit says?

Yes, in `CheckOpts` (`cf-agent/cf-agent.c:808–813`), via `IsAbsPath`,
which is “first byte is `/` (or `\\` on Windows).” Trailing slashes
pass. `..` components pass. A path that is absolute but whose parent
is a symlink passes, and `mkdir` follows that parent. Not a
canonicalised absolute path.

### 3. P-1: what happens on failure paths?

`mkdir` failure is `FatalError` → log including `GetErrorStr()` →
`DoCleanupAndExit`. Keep is *not* yet registered, so a failed `mkdir`
does not leave a keep handler behind. Missing parent: `mkdir: No such
file or directory` (verified). Existing dir / dangling symlink:
`File exists` (verified).

After a successful `mkdir`, every later `FatalError`, `DoCleanupAndExit`,
SIGINT, SIGTERM, and the normal `CallCleanupFunctions` at the end of
`main` run `KeepChangesChroot` (a notice). The tree is kept, including
on a failed run. Default `--simulate` still registers
`DeleteChangesChroot` only; verified no leftover `*.changes` under the
isolated workdir's `state/`.

I did not find a path that deletes a keep tree or keeps a default
tree. `DeleteChangesChroot` always rebuilds
`GetStateDir()/PID.changes` and would not delete the keep path even if
both handlers were registered; they are `if/else`.

`GenericAgentFinalize` frees `config->simulate_keep_chroot` *before*
cleanup runs; `KeepChangesChroot` correctly logs the static
`KEEP_CHANGES_CHROOT` copy, not the freed pointer.

### 4. P-2: is the JSON output correct and safe?

Escaping of `"`, `\\`, and C0 controls through `JsonEncodeString` is
fine and produces well-formed JSON. UTF-8 is not (P-2.1): the document
is well-formed JSON of the *wrong string*. Invalid UTF-8 is well-formed
JSON of different code points.

Numbers: `format_version`, `uid`, `gid`, `size` are JSON numbers via
libntech's writer (see P-2.6). Keys are sorted by `JsonObjectWrite`
(`files`, `format_version`, `packages`, `renames`, `simulate_mode`),
which matches `simulate_json.cf.expected`.

`safe_fopen("w")` 0600 on create is fine; overwrite and symlink-follow
are not, given the sibling option's “must not exist” rule and given
that this is an operator-supplied path that can point at anything.

### 5. P-2: does the non-JSON path still behave exactly as before?

**File-level: yes, measured.** Isolated workdirs, already-built
libtool wrappers, no `make`. P-1 does not touch `simulate_mode.c`, so
its `cf-agent` is master behaviour for `--simulate`. Same policy
(modify one file, create another).

- `--simulate=manifest`: first diff was only `stat` timestamps (runs
  two seconds apart). After substituting `TIMESTAMP`, **byte-identical**.
- `--simulate=diff` with `/usr/bin/diff` symlinked into
  `workdir/bin` (because `-w` makes `GetBinDir()` `workdir/bin`):
  **identical including unified diffs.** Without that symlink both
  sides also matched, including the shared `Couldn't run
  'WORKDIR/bin/diff'` error.

**Package-level `--simulate=diff`:** `DiffPkgOperations` was rewritten
(P-2.5). `GetPkgOperationMsg` is unchanged; the reduction conditions
are the same predicates with `PkgOperation.{name,arch,version}` in
place of `PkgOperationRecord.{msg,pkg_ver}`. The test policy had no
package promises, so that `puts` path was **not** live-compared. Unit
tests cover the reduction only through JSON (`test_pkg_operations*`).
I am not willing to assert package prose is identical; I am willing to
say a mechanical read of the two functions does not show an intended
behaviour change.

`ManifestPkgOperations`, `ManifestChangedFiles`, `DiffChangedFiles`,
`ManifestAllFiles` have no diff hunks.

### 6. Memory, ownership, lifetime

**P-1.** `simulate_keep_chroot` is `xstrdup`'d into the config and
`free`d in `GenericAgentConfigDestroy`. Passing the option twice leaks
the first pointer (process is about to run or `DoCleanupAndExit`;
minor). `KEEP_CHANGES_CHROOT` is a `PATH_MAX` static; CheckOpts
prevents `strlcpy` truncation of *that* copy. Cleanup-after-finalize
is why the static exists; that part is correct. Unchecked
`xstrdup`/`xmalloc` elsewhere abort via `DoCleanupAndExit` as
elsewhere in this codebase.

**P-2.** `SIMULATE_JSON_FILE` is a file-scope `xstrdup` never freed and
not on the config object. Lifetime is process-exit. Same double-option
leak. `WriteChangesJson` `JsonDestroy`s on the failure paths before
open; after a successful `FileWriter` it `WriterClose`s and
`JsonDestroy`s. `CollectPkgOperations` map ownership in
`DiffPkgOperations` / `AddPkgOperationsToJson` is paired
`MapDestroy`. `AddChangedFilesToJson` either `StringSetAdd`s `path` or
`free`s it. `AddRenamedFilesToJson` frees both names; on a truncated
pair it still `free(orig_name)` after logging.

No double-free or UAF spotted in the new code. The KEEP static vs
config free ordering in P-1 is the one lifetime bug that *would* have
been real, and they avoided it.

### 7. Are the tests any good?

**P-1.** Acceptance only. The test as a whole would fail without the
option (unknown flag → no kept copy). Two of five conjuncts would
pass anyway (Q1/P-1.5). Nothing asserts mode 0700, `EEXIST`, relative
reject, or long paths — the things this review broke.

**P-2.** Unit + acceptance. `simulate_mode_test` is its own
`check_PROGRAMS` entry (not appended to `rlist_test`; trap 5 does not
apply). It would not compile without `WriteChangesJson`, so it is not
vacuous. It does not test the non-JSON path at all. `test_special_characters_in_path`
asserts round-trip through `JsonParseFile`, which shares the
byte-`\u00XX` bug, so it **cannot fail** the interoperability defect.
No newline-in-filename case, no invalid UTF-8 case, no “write failed
⇒ non-zero exit” case, no “do not overwrite” case. Acceptance
`simulate_json.cf` normalises `sha256`/`size`/`uid`/`gid` away, so it
would not catch a zero digest or a number-encoding bug; it does lock
the document shape against `promises.cf.sub`. `CFE-XXXX` is a
placeholder.

### 8. What would a maintainer push back on?

- **`Ticket: #6295` / `#6296`.** `CONTRIBUTING.md:225–241`: changelog
  entries “should also include a reference to a ticket” on
  `https://northerntech.atlassian.net/`, examples `CFE-1234` /
  `ENT-4586`. The repo has issues disabled; those numbers are
  Discussions. The PR comments already narrate the author removing
  then restoring the trailer after a 404 on the issues API. A
  maintainer can still say “that is not a Ticket.” `Changelog: Title`
  itself matches the guide (past-tense, user-facing title).
- **`CFE-XXXX`** in P-2's acceptance test.
- **False sentences** in both commit/PR bodies: P-1's “never a looser
  directory” / implied “`PATH_MAX` check means no truncation”; P-2's
  “prose renderers are unchanged; without the new option, nothing
  changes.”
- **Inconsistent option contracts:** P-1 refuses an existing path and
  caps length; P-2 overwrites and does not cap.
- **Log levels:** keep is `LOG_LEVEL_NOTICE` as promised; simulate still
  `LOG_LEVEL_WARNING` for the chroot banner (pre-existing). JSON write
  is `INFO` on success, `ERR` on failure that then exits 0.
- **Option naming** `--simulate-keep-chroot` / `--simulate-json` is
  consistent with `--simulate`. Fine.
- Fold at 78 columns / Allman: new C is in house style on a quick
  read; not scored.

---

## 4. How the traps were controlled

Every before/after claim used already-built libtool wrappers
**in place** (`core-p1/cf-agent/cf-agent`, `core-p2/cf-agent/cf-agent`).
No `make` in either shared tree. Scratch work was `/tmp/p1p2-review/`
(standalone C, isolated `-w` workdirs).

1. **`make check` in `tests/unit` does not rebuild libraries.** Not
   used. No unit-test rebuild. P-1 vs P-2 `--simulate` comparison
   executed the pre-built `cf-agent` binaries; P-2's
   `simulate_mode.c` is linked into `cf-agent` itself (`otool -L`
   shows `libpromises` from the configure prefix, not `libcf-agent`).
2. **`make -C tests/unit <test>` does not relink.** Not used. Did not
   run `simulate_mode_test` for a before/after.
3. **`git stash` of a committed file stashes nothing.** Not used.
   Master `DiffPkgOperations` came from
   `git show upstream/master:cf-agent/simulate_mode.c`. Diffs were
   `git diff upstream/master...HEAD`.
4. **`.libs/` binaries link the installed dylib.** `otool -L` on both
   `.libs/cf-agent`: `/Users/djbclark/opt/cfengine-dev/lib/libpromises.3.dylib`.
   Invoked the **wrapper**, which exports
   `DYLD_LIBRARY_PATH=.../libpromises/.libs`. Isolated `-w` workdirs
   had `bin/cf-promises` → the matching tree's wrapper (the wrapper
   re-sets `DYLD_*` after macOS strips it on exec). P-1 keep lives in
   `libpromises` (needs that DYLD). P-2 JSON/prose live in the
   `cf-agent` executable (the wrapper's binary).
5. **`rlist_test` XFAIL abort.** `simulate_mode_test` is a separate
   `check_PROGRAMS` entry (`tests/unit/Makefile.am:141`), not a case
   after `test_rval_to_scalar2`. Trap does not apply. Did not use
   `rlist_test`.

P-1 vs P-2 `--simulate` comparison additionally: same policy text,
separate workdirs, then normalised `WORKDIR`, `state/PID.changes`, and
`Access|Modify|Change` timestamps before `diff -u`.

---

## 5. What was not checked

- Live TOCTOU rename-swap against a 0777 parent from a second uid.
- Live `--simulate=diff` package prose (no package module / no
  `pkgs_ops` in the test policy). `CollectPkgOperations` vs old
  `DiffPkgOperations` was read, not executed on both binaries.
- `manifest-full`.
- Windows `IsAbsPath` / drive-letter keep paths (no Windows).
- `HashFile` failure and `readlink` truncation, live.
- Acceptance tests under `tests/acceptance` (not run; they need the
  project's test harness).
- Signals (SIGINT during a keep run).
- Whether `jq` agrees with `json.loads` on the UTF-8 document (Python
  only; the encoding is unambiguous).
- `/Users/djbclark/src/cfengine-core` (forbidden by the brief).
- Other reviewers' `upstream-opinion-*.md` files, `docs/handoffs/`,
  `docs/architecture/upstream-register.md`.
- Rebuilding either change against a patched libntech; both trees are
  on stock `5b5d04e1` as the brief states.

Hindsight knowledge-page search for this pair of PRs returned no
pages; nothing above is from that memory.
