# Independent post-flight audit — P-1 `#6293` and P-2 `#6294`

Auditor: grok. Date: 2026-08-17.
Trees: `core-p1` @ `64e2ac1cb`, `core-p2` @ `05e18f038`, both vs `upstream/master` `17eb78e6d`.
Neither PR has a human review (`reviews: []` on both). Measurements were taken in `/tmp/grok-review-p1p2`, not in the shared worktrees.

## 1. Verdict

**P-1 (`--simulate-keep-chroot`, `#6293`): push a correction.**

The option does what it says under a normal umask: it creates the requested directory, keeps it, announces it at `NOTICE`, and leaves the default delete path alone. It is not ready as-is because the commit, the PR body, and discussion `#6295` all claim the directory "is created with mode 0700" as the reason permission-mirrored copies of system files cannot land somewhere looser. That claim is false. `mkdir(path, 0700)` is umask-relative. With `umask 0777` the real `cf-agent` creates mode `0000`; the owner cannot write into it. One `chmod(path, 0700)` after a successful `mkdir` (what `mkdir -m 0700` does) fixes the claim. The parent-directory hole is real but narrower than a `/tmp` sticky-bit attack; document it or reject a group/world-writable parent. Do not withdraw.

Exact correction:

1. After `mkdir(keep_chroot, 0700)` succeeds, `chmod(keep_chroot, 0700)` (or `mkdirat` + `fchmod`). Fail the run if the chmod fails.
2. Either refuse a parent that is group/world-writable and not sticky, or drop the sentence that 0700 by itself prevents copies landing in a looser directory.
3. Add acceptance coverage for the created mode, an already-existing path, and a relative path. `keep_requires_simulate` is decorative (see Q7).

**P-2 (`--simulate-json`, `#6294`): push a correction.**

The file/manifest/diff prose path still behaves as it did — demonstrated, not asserted (Q5). The new JSON document is well-formed and useful for ASCII paths. It is not ready as a machine-readable API, which is the use discussion `#6296` sold, for three measured reasons: (a) the shared package-reduction function reports both install and remove for remove-then-install; (b) non-ASCII filenames are emitted as per-byte `\u00XX`, which `python`/`jq` decode as the wrong characters while the unit test's own parser round-trips them; (c) a failed JSON write logs `ERR` and still exits 0. Do not withdraw.

Exact correction:

1. In `CollectPkgOperations`, do not set `name_arch = NULL` before `MapRemove(removed, name_arch)`. Add a unit case `r,pkg,,\r\ni,pkg,1.0,\r\n` that requires a single install and no remove.
2. Do not send filenames through `JsonEncodeString`'s per-byte `\u00XX` path as the contract with standard consumers. Emit UTF-8 bytes inside the JSON string (legal) or real Unicode `\uXXXX` code points. Add a test that round-trips `é` through `python -c 'json.load(...)'`, not through `JsonParseFile`.
3. On `WriteChangesJson` failure, set a failing exit status. The discussion's CI-gate story is broken if the file is missing and the process still succeeds.
4. Replace the `CFE-XXXX` placeholder in `simulate_json.cf`.

---

## 2. Defects found

### D1 — P-1: `mkdir(path, 0700)` does not create mode 0700
- **Where:** `libpromises/generic_agent.c:1647` (`mkdir(keep_chroot, 0700)`). Claim in the commit body, the PR body, and discussion `#6295`.
- **What breaks:** The retained tree is advertised as 0700 so that permission-mirrored copies of sensitive files cannot land in a looser directory. `mkdir(2)` applies `mode & ~umask`. With `umask 0777` the directory is `0000`; the creating process cannot enter or write it. The run then continues (mkdir succeeded, so no `FatalError`), `KeepChangesChroot` still fires, and the operator is left with an empty unusable tree.
- **How to reproduce:** `/tmp/grok-review-p1p2/mkdir_probe` (standalone `mkdir(2)`): umask 0000/0022/0077 → 0700; umask 0777 → 0000. Then the real P-1 wrapper:

      umask 0777
      cf-agent --simulate=manifest --simulate-keep-chroot=/tmp/.../umask0000.changes ...

  Result: `mode=00`, `d---------`. A follow-up C probe (`write0000.c`) got `open(dir) errno=13` and `fopen(dir/x) errno=13`.
- **Status:** **verified** against both libc `mkdir` and the P-1 `cf-agent` binary.

### D2 — P-1: 0700 on the new directory does not bind the parent
- **Where:** `libpromises/generic_agent.c:1647–1658`. Same security sentence as D1.
- **What breaks:** After a successful `mkdir`, nothing holds a file descriptor on the new directory and nothing inspects the parent. If the parent is writable by someone else and is not sticky, that someone can `rename` the 0700 directory away and replace it with a 0777 directory or a symlink. Subsequent `PrepareChangesChroot` writes then land in the replacement. `/tmp` itself is sticky, so this is not a free attack on `--simulate-keep-chroot=/tmp/foo` as root. It is an attack on `--simulate-keep-chroot=/tmp/attacker-owned/foo` and on any group-writable destination the operator is talked into.
- **How to reproduce:** `mkdir_probe` rename-swap case: created 0700 `keep`, `rename` to `stolen`, `mkdir 0777 keep`, write `etc_shadow` into the replacement. The 0600 "secret" landed in the 0777 directory.
- **Status:** **verified** as a mechanism. **suspected** as a live exploit only when the operator chooses a writable non-sticky parent.

### D3 — P-2: `CollectPkgOperations` does not cancel a previous remove when it records an install
- **Where:** `cf-agent/simulate_mode.c:872–877`. Comment at 876: "Package installation cancels a previous removal (if any)."
- **What breaks:** On a successful insert, `name_arch` is set to `NULL` and then passed to `MapRemove(removed, name_arch)`. `StringHash(NULL)` is safe (treats NULL as empty); `StringEqual(existing_key, NULL)` is false; the remove is a no-op. A remove-then-install therefore yields *both* an install and a remove in the "net" set. JSON consumers and `--simulate=diff` package output both go through this function. The comment, the commit ("net set of install and remove operations"), and discussion `#6296` are all false for this sequence.
- **How to reproduce:** `/tmp/grok-review-p1p2/pkg_harness` linked against P-2 `libcf-agent.a` via the libtool wrapper (DYLD → worktree `libpromises`):

      CSV: r,pkg,,\r\ni,pkg,1.0,\r\n
      packages: [install pkg 1.0, remove pkg]

  The unit-tested cousins behave: `r` then `p` → empty; `i` then `a` matching → empty. Those are the only cancel cases the test file covers.
- **Status:** **verified**. Pre-existing in master's `DiffPkgOperations` (same `name_arch = NULL` then `MapRemove`). P-2 copied it into the function that now also feeds JSON. Not a non-JSON regression; it is a new JSON defect and a missed fix in a rewrite that claimed to share the reduction.

Related, also **verified** on the same harness, also pre-existing, also now in JSON: `i,pkg,1.0,\r\nr,pkg,1.0,\r\n` reports a remove, not empty, even though the comment at 889–895 says a matching install-then-remove is no change.

### D4 — P-2: non-ASCII filenames are not what a standard JSON parser returns
- **Where:** `libntech/libutils/json.c:1014–1022` (`JsonEncodeStringWriter`), called from `JsonWrite` ← `WriteChangesJson` (`cf-agent/simulate_mode.c:1438`). Unit test `tests/unit/simulate_mode_test.c:278–296` (`test_special_characters_in_path`).
- **What breaks:** Bytes outside printable ASCII are emitted as `\u00XX`. `é` (UTF-8 `C3 A9`) becomes `\u00c3\u00a9`. That is well-formed JSON. `json.loads` and `jq` decode it as `Ã©` (U+00C3 U+00A9), not `é` (U+00E9). `JsonParseFile` in the same library treats `\u00XX` as a raw byte, so the unit test asserts the original path and passes. Discussion `#6296` sells this document to CI gates and other programs. Those programs will not use libntech's parser.
- **How to reproduce:** `/tmp/grok-review-p1p2/json_harness` wrote a created-file record for `/simulate-test/wéird`. Raw field: `"path": "/simulate-test/w\u00c3\u00a9ird"`. libntech parse: matches input. `python json.loads` / `jq -r .path`: `'/simulate-test/wÃ©ird'`. Quotes, backslash, newline, tab, CR, and `\u0001` were fine.
- **Status:** **verified**. Invalid UTF-8 (`0xFF 0xFE`) could not be created as a file on APFS (`Illegal byte sequence`); the encoder still produced `\u00ff\u00fe` from the record string.

### D5 — P-2: JSON write failure does not fail the process
- **Where:** `cf-agent/cf-agent.c:394–401`.
- **What breaks:** `WriteChangesJson` returning false logs `ERR` twice and falls through. `main` still returns 0 if the rest of the run succeeded. A CI gate watching the exit code will accept a run that produced no document (or an unwritable dest).
- **How to reproduce:** `--simulate=manifest --simulate-json=/tmp/.../out` where `out` is a directory. Log: `Failed to open '.../out' ... (fopen: Is a directory)` then `Failed to write the simulated change set`. `rc=0`. Same result after a real file-creating policy (not just failsafe).
- **Status:** **verified**.

### D6 — P-2 acceptance test carries a placeholder ticket
- **Where:** `tests/acceptance/29_simulate_mode/simulate_json.cf:26` (`"description" -> { "CFE-XXXX" }`).
- **What breaks:** Nothing at runtime. It is a false ticket reference sitting in a PR that already had a round of "is this Ticket trailer real?" churn.
- **Status:** **verified** by reading the file.

---

## 3. The eight questions

### 1. P-1: is the chroot creation actually safe?

Safer than a first reading of `mkdir` + operator path suggests, and not as safe as the commit claims.

- **umask vs 0700.** `mkdir(2)` cannot *add* bits, but it can *drop owner bits*. Default umask 0022 → 0700 (measured). umask 0777 → 0000 (measured, including via the real agent). 0700 is the right *intended* mode for a tree that will hold permission-mirrored copies. It is not what the code guarantees. `chmod` after `mkdir` is the fix. See D1.
- **Parent permissions.** They matter. 0700 on the new directory stops other users walking *into* it. It does not stop a writer of the parent from renaming it. Sticky `/tmp` blocks that for a root-owned name; a non-sticky attacker-owned parent does not. See D2. The code never `lstat`s the parent and never holds an fd.
- **Symlinks / TOCTOU.** There is no check-then-create. `mkdir` is the existence test. A dangling symlink at `PATH` is a directory entry, so `mkdir` returns `EEXIST`. Measured with libc and with the real agent: the symlink target is **not** created. POSIX documents this (`EEXIST` "includes the case where pathname is a symbolic link, dangling or not"). The classic dangling-symlink-through-`mkdir` steal does not work here. A *post-mkdir* swap of the directory in a writable parent does (D2).
- **`PATH_MAX` / `strlcpy`.** CheckOpts rejects `strlen(optarg) >= PATH_MAX` (`cf-agent.c:816–820`). Measured: a 1100-byte path is rejected (`path longer than 1023 bytes`) before any `strlcpy`. A `PATH_MAX`-length string *would* truncate (`strlcpy` returned 1024, dest length 1023); that input cannot reach `strlcpy` given the check. A path of length `PATH_MAX-1` is accepted and fits. Residual: `ToChangesChroot` then joins this path with every mirrored file and `assert`s `strlen(orig) <= PATH_MAX - chroot_len - 1` (`eval_context.c:3875`); a keep-path that is merely *near* `PATH_MAX` will truncate those joins in a non-debug build. The default `$statedir/$pid.changes` is short; an operator-chosen near-`PATH_MAX` path is a new way to hit that pre-existing join.
- **Is 0700 enough?** As a ceiling on the *root* of the tree, yes, under a sane umask: mirrored `0755` directories underneath are still unreachable from other uids because they cannot search the root. As a complete story about "cannot land in a looser directory", no (D1, D2).

### 2. P-1: is the absolute-path requirement enforced where the commit says?

Yes, and only as a first-character check.

The check is `IsAbsPath(optarg)` in `cf-agent/cf-agent.c:809`, implemented as `IsFileSep(*path)` in `libpromises/files_names.c:214–224`. Measured / walked:

| input | `IsAbsPath` | what happens |
|---|---|---|
| `relative/path` | false | rejected at CheckOpts, rc=1 (real agent) |
| `""` | false (`*path == 0`) | rejected as relative |
| `/foo`, `/foo/`, `//foo` | true | accepted |
| `/foo/../bar` | true | accepted; `mkdir` walks the components. `$BASE/sub/../dotdot.changes` failed `ENOENT` because `sub` did not exist — `..` is not canonicalized first |
| `/foo/../../etc/passwd` | true | accepted by the check |
| trailing slash | true | real agent created `$BASE/trail.changes` (no trailing slash on disk), logged `Keeping .../trail.changes/` |
| path whose parent is a symlink | true | `mkdir` creates through the parent; measured |
| `C:\foo` | false | rejected (Windows is already `test_soft_fail` on this test) |

The commit's "has to be absolute" is enforced at the option parser, before `mkdir`. It is not a containment check. A path that is absolute and contains `..`, or whose parent is a symlink, is accepted.

### 3. P-1: what happens on failure paths?

- **`FatalError` on `mkdir` failure** (`generic_agent.c:1648–1653`). It logs `Fatal CFEngine error: Failed to create the directory '%s' ... (mkdir: %s)` with `GetErrorStr()`, then `DoCleanupAndExit`. Measured: existing directory → `File exists`; dangling symlink → `File exists`; missing parent → `No such file or directory`; relative path never reaches here. The audience is the operator who supplied the path. This is not an unprivileged-caller oracle. Using `FatalError` for a user error is louder and less consistent than the `Log` + `DoCleanupAndExit` used two screens up in CheckOpts; a maintainer can reasonably ask for the latter. It is the right *severity* (do not continue a simulate run whose retained tree does not exist).
- **Cleanup swap.** Keep path registers only `KeepChangesChroot` (`:1658`). Default path registers only `DeleteChangesChroot` (`:1663`). `KeepChangesChroot` (`:1833–1836`) logs `NOTICE` from the static `KEEP_CHANGES_CHROOT` buffer, which is `strlcpy`'d at create time and does not depend on `config` still being alive. `DeleteChangesChroot` still rebuilds `$statedir/$pid.changes` and does not know about the keep path, so even a mistaken call would not delete the kept tree (unless the operator pointed PATH at that exact default name).
- **Exit paths, measured or walked:**
  - `mkdir` fails: `KeepChangesChroot` is not registered. Nothing is created (or, for EEXIST, the pre-existing thing is left alone).
  - `mkdir` succeeds, later `FatalError` (first run: untrusted `ppkeys` 0755): `notice: Keeping changes chroot '...'` still printed; directory remains.
  - `SIGINT`/`SIGTERM`: `HandleSignalsForAgent` → `DoCleanupAndExit` → `KeepChangesChroot`. Kept. Not signal-tested live.
  - Normal success: measured. `Keeping changes chroot` at the end; 0700 tree contains the would-be file; the real file is absent; a default `--simulate` in the same workdir left no `*.changes`.
  - Failsafe / `--dry-run`-style abort after create: kept (see untrusted-keys run). Correct for the option.
- **Deleted when it should be kept / kept when it should be deleted.** Not observed. The two cleanup functions are registered exclusively. Default delete still works (measured: no leftover `*.changes` after a successful default run).

### 4. P-2: is the JSON output correct and safe?

Partly. Structure, `format_version`, file change/created/deleted/modified, permissions-as-string, SHA-256 of the *would-be* contents, symlink `target` rewritten out of the chroot, rename pairs, and ASCII paths are all fine. I generated a real created-file document with the P-2 agent and `python json.load` accepted it.

Problems:

- **Hostile filenames.** Quotes and backslash are escaped correctly (`\"`, `\\`). Newline/tab/CR become `\n`/`\t`/`\r` (valid JSON, correct after any parser). Control `0x01` becomes `\u0001` (valid and correct). Non-ASCII is D4. The unit test's "special characters" case is exactly the one that hides D4.
- **Malformed JSON.** I did not find a path that emits a truncated or unparseable document. On any collection failure `WriteChangesJson` destroys the object and returns false without writing (`:1416–1421`). A write-open failure also writes nothing. Good.
- **Numbers through libntech's JSON writer.** Yes, four of them:
  - `format_version` via `JsonObjectAppendInteger` (`simulate_mode.c:1400`) → `JsonIntegerCreate` → `xasprintf("%d")`.
  - `uid` / `gid` via `JsonObjectAppendInteger` (`:1163–1164`) after a cast to `int`.
  - `size` via `JsonObjectAppendInteger64` (`:1168`) → `JsonIntegerCreate64` → `PRIi64`.

  The live defect family on this machine (`fix/json-number-rendering` / `RlistFromContainer` + `StringToLongExitOnError`) is a *read* path: numbers a `long` cannot hold abort the process. These four values are *written*. `format_version` is 1. `uid`/`gid` fit in `int` for every uid this host will produce; a theoretical `uid > INT_MAX` would go negative. `size` uses the 64-bit writer, so a large file does not hit the `int` ceiling. I am not claiming a write-side overflow here. I am recording, as asked, that numbers do reach this output through that writer.

- **Package reduction.** D3. The JSON is only as "net" as `CollectPkgOperations`.
- **Overwrite / symlink dest.** `safe_fopen(output_file, "w")` (`:1427`). No `O_EXCL`, no "must not exist" (unlike P-1). Measured: a pre-existing file is replaced. A dest that is a directory fails open and still exits 0 (D5).

### 5. P-2: does the non-JSON path still behave exactly as before?

For every existing `--simulate` user who is looking at files: **yes, demonstrated.**

- `cf-agent/simulate_mode.c` lines 1–647 (everything through `DiffChangedFiles`) differ from master by three `#include`s and nothing else. `cmp` of P-1's `simulate_mode.c` (untouched by P-1) against `17eb78e6d:cf-agent/simulate_mode.c` is identical.
- `ManifestPkgOperations` vs master: empty `diff`.
- Same one-file policy (`create` + `content => "would-be content"`), P-1 wrapper vs P-2 wrapper, `--simulate=manifest` and `--simulate=diff`, workdir/pid/timestamp/size normalized: **`diff` exit 0 both times.** Real would-be contents appeared in both manifests. Installed `cf-promises` was placed in `$WORKDIR/bin` so the child exec did not depend on `DYLD_*` (trap 4).

For `--simulate=diff` *package* output: the renderer was rewritten. `DiffPkgOperations` now prints from `CollectPkgOperations` at the end instead of storing pre-rendered strings. The reduction steps are the same steps, including D3. I did not drive a live package-module promise (see §5). I did drive the on-disk CSV format those promises write, through the new function, and the bug that was already in master's `DiffPkgOperations` is still there. So the non-JSON package path behaves as before, including the lie in the comment. It does not behave as the comment says.

`GetPkgOperationMsg` still ends with `\n` and both old and new code `puts` it (double newline). Pre-existing, unchanged.

### 6. Memory, ownership, lifetime

**P-1.** `config->agent_specific.agent.simulate_keep_chroot` is `xstrdup`'d (`cf-agent.c:824`), initialized `NULL` (`generic_agent.c:2654`), `free`d in `GenericAgentConfigDestroy` (`:2703`). `KEEP_CHANGES_CHROOT` is a `PATH_MAX` static; no free, filled once, read at cleanup after `GenericAgentFinalize` has already destroyed `config`. That split is correct: the notice does not use the heap string. `xstrdup` / `xmalloc` abort on OOM. If CheckOpts fails after the `xstrdup` (e.g. option used without `--simulate`), `DoCleanupAndExit` does not destroy `config`; the string leaks and the process exits. Harmless. Specifying the option twice leaks the first `xstrdup`. Harmless.

**P-2.** `SIMULATE_JSON_FILE` is a file-scope `char *` (`cf-agent.c:115`), `xstrdup`'d (`:831`), used just before `GenericAgentFinalize`, never freed. Process-lifetime leak. It is *not* on `config->agent_specific`, so Q6's prompt about that field applies to P-1, not P-2. `WriteChangesJson` and the adders `free` what they allocate (`path` into the `StringSet` or `free` on duplicate; rename names; maps). `CollectPkgOperations` `free(name_arch)` is correct on the paths that do not insert; NULL after insert is a no-op `free`. No double-free observed. Unchecked allocations go through `xstrdup` / `xasprintf` / `xmalloc`.

No use-after-free on the keep buffer: cleanup runs after finalize and only reads the static.

### 7. Are the tests any good?

**P-1: acceptance only.** `keep_chroot.cf` + `.sub`. The overall `ok` class would fail without the change: the first command line contains `--simulate-keep-chroot`, which is an unknown option on master, so `kept_copy_has_changes` is false. Good enough that this is not decoration-as-a-whole.

Per conjunct, against master:

| class | without the change |
|---|---|
| `kept_copy_has_changes` | fail (the option does not exist) |
| `real_file_untouched` | pass (pre-existing `--simulate`) |
| `keep_notice_logged` | fail (no notice) |
| `default_chroot_deleted` | pass (pre-existing default) |
| `keep_requires_simulate` | **pass** (`not(returnszero(...))` is true for "unknown option" too) |

Two of five conjuncts assert pre-existing behaviour; one of those (`keep_requires_simulate`) is the exact "passes either way" shape called out in the brief. Nothing asserts the created mode, EEXIST, relative path, `PATH_MAX`, or a dangling symlink. `default_chroot_deleted` uses `findfiles($(sys.statedir)/*.changes)` length 0, which is only sound if the acceptance workdir is exclusive.

**P-2: unit + acceptance.** `simulate_mode_test` is its own `check_PROGRAMS` entry, not an append to `rlist_test`. I ran the already-built wrapper: `All 13 tests passed`. Those tests would not *link* without `WriteChangesJson`, so they are not decoration. The acceptance test would fail on master as an unknown option.

Gaps that match this work's already-seen failure mode:

- `test_pkg_operations_cancel` covers `r` then `p`, and `i` then `a`. It does not cover `r` then `i` (D3). A test that "covers cancel" and misses the broken cancel is decoration of the wrong path.
- `test_special_characters_in_path` covers `é`, quotes, and backslash, then parses with `JsonParseFile`. It would pass if every standard consumer on earth got the wrong string. It is a self-test of libntech, not of the document.
- No unit test of a write failure, of overwrite, of `WriteChangesJson` without `--simulate` (that's CheckOpts), of newline-in-path (which actually works), of package field order going *through* `RecordPkgOperationInChroot`.
- The CSV helper comment (`simulate_mode_test.c:98–99`) says the on-disk format is `op,name,version,architecture` "just like `RecordPkgOperationInChroot`". The function's *parameter names* are `(op, name, arch, version)`; every caller in `package_module.c` passes `(op, name, version, arch)`. The bytes on disk are version-then-arch, which is what the tests write. The comment is true of the callers and false of the prototype. The tests never call the writer.

### 8. What would a maintainer push back on?

- **`Ticket: #6295` / `Ticket: #6296`.** `CONTRIBUTING.md` says changelog entries carry `Ticket: CFE-1234` pointing at `https://northerntech.atlassian.net/`. These numbers are GitHub Discussions, not Jira, and `GET /repos/cfengine/core/issues/6295` is 404 because issues are disabled. The discussions exist (titles match the PRs; I fetched the bodies). The PR comments already narrate the 404-then-restore. A maintainer who greps Jira will still bounce them. Right trailer *shape*, wrong tracker for this repository's documented convention. Using a Discussion is defensible given issues are off; pretending it is a CFE ticket is not. There is no CFE ticket.
- **`Changelog: Title`.** Fine. Titles are past tense and user-facing.
- **False statements, the failure mode already caught twice:**
  - P-1 commit / PR / `#6295`: "created with mode 0700, so that the permission-mirrored copies ... can neither land in a directory prepared with looser permissions nor mix with the contents of a previous run." Mixing with a previous run is true (EEXIST). Mode 0700 is not guaranteed (D1). "Neither land in a looser directory" is not guaranteed (D2).
  - P-2 commit / PR / `#6296`: "The prose renderers are unchanged ... without the new option, nothing changes." True for files (measured). `DiffPkgOperations` *was* rewritten; behaviour of the reduction is unchanged, including D3.
  - P-2 commit: "net set of install and remove operations." False for remove-then-install (D3).
- **`CFE-XXXX`** in `simulate_json.cf:26`.
- **Option naming / dest semantics.** P-1 refuses an existing directory; P-2 overwrites an existing file. Worth one sentence in the man/help text. P-2 has no `PATH_MAX` check.
- **`FatalError` vs CheckOpts `Log`+exit** for a bad keep path (style).
- **Log levels.** Keep announcement at `NOTICE` is right. JSON-written-OK at `INFO` is fine. JSON-write-fail at `ERR` without a failing status is the problem (D5).
- **Force-push churn** already apologised for on both PRs. Tree-hash-only message rewrites; I did not re-check the hashes.
- **Commit hygiene.** One commit each, body wrapped, `Changelog` + `Ticket` present. Fine.

---

## 4. How the five traps were controlled

Every before/after claim below names the control. I never ran `make` in `core-p1`, `core-p2`, or `/Users/djbclark/src/cfengine-core`.

1. **`make check` in `tests/unit` does not rebuild libraries.** I did not run `make check`. `simulate_mode_test` was executed as the already-built wrapper. The package and JSON harnesses were compiled in `/tmp/grok-review-p1p2` and statically linked to P-2 `cf-agent/.libs/libcf-agent.a` (that archive contains `WriteChangesJson` / `CollectPkgOperations`).
2. **`make -C tests/unit <test>` does not relink.** I did not invoke that target. New binaries were produced by `libtool --mode=link` in `/tmp`.
3. **`git stash` of a committed file stashes nothing.** Before/after source was `git show 17eb78e6d:cf-agent/simulate_mode.c` and `cmp` against the P-1 file. P-1 `simulate_mode.c` is byte-identical to master; that is why the P-1 `cf-agent` wrapper is a valid "before" binary for Q5.
4. **`.libs/` binaries link the installed dylib.** `otool -L` on `core-p1/cf-agent/.libs/cf-agent`, `core-p2/cf-agent/.libs/cf-agent`, `tests/unit/.libs/simulate_mode_test`, and `/tmp/grok-review-p1p2/.libs/pkg_harness` all list `/Users/djbclark/opt/cfengine-dev/lib/libpromises.3.dylib`. Every measurement used the **libtool wrapper**, whose `DYLD_LIBRARY_PATH` is the matching worktree `libpromises/.libs`. For `cf-agent` spawning `cf-promises` (macOS strips `DYLD_*`), `$WORKDIR/bin/cf-promises` was a symlink to the **installed** `/Users/djbclark/opt/cfengine-dev/bin/cf-promises`, which does not need `DYLD_*`. Confirmed `cf-promises -cf policy.cf` rc=0 before the Q5 runs.
5. **`rlist_test` XFAIL / abort.** `simulate_mode_test` is a separate program (`tests/unit/Makefile.am`). Its 13 tests all ran (log: `All 13 tests passed`). Nothing I assessed is registered after `test_rval_to_scalar2`.

Additional controls for the Q5 identity claim: P-1 and P-2 wrappers, same policy file, same `CFENGINE_TEST_OVERRIDE_WORKDIR` layout, output normalized for workdir / `PID.changes` / timestamps / `Size:`, then `diff`. Both `--simulate=manifest` and `--simulate=diff` produced empty diffs. That is a file-promise run, not a package-module run.

---

## 5. What I did not check

- Windows / MinGW path layout (both tests already `test_soft_fail` there).
- A live package-module promise. D3 was measured against the CSV format `RecordPkgOperationInChroot`'s callers actually write, through the new `CollectPkgOperations`, not through `apt`/`yum`.
- Signal delivery against a running agent (cleanup path was read; `KeepChangesChroot` after `FatalError` was measured).
- ACL inheritance on the new directory, or Linux vs macOS `mkdir` beyond the POSIX `EEXIST`-on-symlink case (which I measured on macOS).
- A two-process race on the rename-swap; the swap was sequential, which is enough to show the window and not enough to time it against `PrepareChangesChroot`.
- The full acceptance suite, Enterprise, `manifest-full`, hard links, devices, or a JSON document from a real rename/package run (the unit test covers those records; the agent run I did produced one created file).
- Whether `HashFile` failure is surfaced or silently zeroes a digest.
- `uid > INT_MAX` (the cast at `simulate_mode.c:1163`).
- Reading the other panelists' `upstream-opinion-*.md` files, `docs/handoffs/`, or `docs/architecture/upstream-register.md`.
