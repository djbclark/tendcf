# PR 2 report: `--simulate-json` — JSON rendering of the simulated change set

**Status: reference record, kept in tendcf.** It documents work on the
temporary `djbclark/core` fork and must NOT be committed to the CFEngine
branch or included in the upstream PR. It is the handoff report for a reader
with zero context.

## What this is and where it lives

- **Branch:** `simulate-json`, one commit, `071f85987`
  ("Added --simulate-json option to write the simulated change set as JSON").
- **Base:** master at `17eb78e6d` (the same base PR 1 used). Deliberately NOT
  built on the `simulate-keep-chroot` branch — upstream wants two independent
  PRs, and the two branches share no files except the option tables in
  `cf-agent/cf-agent.c` (see "Design decisions", static vs. config field).
- **Statement of work:** <https://github.com/djbclark/core/issues/3> (PR 2).
  Investigation trail: issue #1. Companion change (retain the changes chroot):
  issue #2 / branch `simulate-keep-chroot` (commit `5dbd295f6`).
- **Division of labour with PR 1, which upstream will ask about:** the retained
  chroot is the would-be *bytes* (the files as they would be after the run);
  this JSON is the would-be *change set* (which paths, which kinds of change,
  which package operations). The SHA-256 digests in the JSON make the two
  mutually verifying: hash a file in the retained chroot and it must match the
  digest the JSON committed to. Neither substitutes for the other.
- **Constraints in force:** no push, no PR, no writes to any upstream tracker
  (a PreToolUse hook enforces this; tripping it is intended). `CFE-XXXX` in the
  commit message and in the acceptance test is a placeholder — filing the real
  Jira ticket is gated on djbclark's approval.

## The feature

```
cf-agent -K -f policy.cf --simulate=manifest --simulate-json=/path/changes.json
```

- `--simulate-json=FILE` writes the change set computed by a `--simulate` run
  to FILE as a single pretty-printed JSON document.
- Requires `--simulate` (any of manifest / manifest-full / diff); rejected
  otherwise at option-validation time.
- FILE must be an absolute path (mirrors PR 1's `--simulate-keep-chroot`
  validation; avoids any dependence on the agent's working directory).
- FILE is overwritten if it exists (it is a report file; unlike PR 1's chroot
  directory there is no stale-content-mixing hazard). Opened with
  `safe_fopen(path, "w")`.
- The existing prose renderers are untouched and remain the default. Without
  the new option, behaviour is bit-for-bit unchanged.
- On failure to produce the document, nothing is written (no partial JSON) and
  an error is logged; see "Residue" for the exit-code question.

### Document schema (`format_version` 1)

Keys are snake_case (the newer core idiom — `error_message`, `promise_type` —
rather than the older policy-dump camelCase). `JsonWrite()` sorts object keys
canonically, so key order in the file is alphabetical. Example, trimmed from a
real run:

```json
{
  "format_version": 1,
  "simulate_mode": "manifest",
  "files": [
    {
      "path": "/etc/motd",
      "change": "modified",
      "type": "regular file",
      "permissions": "0644",
      "uid": 0,
      "gid": 0,
      "size": 12,
      "sha256": "6a5f63424a0c878f..."
    },
    { "path": "/etc/gone", "change": "deleted" },
    {
      "path": "/etc/link",
      "change": "created",
      "type": "symbolic link",
      "permissions": "0755",
      "uid": 0,
      "gid": 0,
      "target": "/etc/motd"
    }
  ],
  "renames": [
    { "old_name": "/etc/old", "new_name": "/etc/new" }
  ],
  "packages": [
    { "operation": "install", "name": "caddy", "version": "2.0" },
    { "operation": "remove", "name": "unwanted" }
  ]
}
```

Field semantics:

- `files[].change`: `created` / `modified` / `deleted`, derived by `lstat()`ing
  the real path vs. its copy in the changes chroot (same derivation
  `DiffFile()` uses). Chrooted copy missing → `deleted`; real path missing →
  `created`; both present → `modified`.
- Everything else in a `files[]` entry describes the file **as it would be
  after the run** (the chroot copy): `type` via the same
  `GetFileTypeDescription()` the prose uses, `permissions` as a 4-digit octal
  string (`st_mode & 07777`), numeric `uid`/`gid`, and for regular files
  `size` plus `sha256` of the contents. Symlinks get `target`, mapped back out
  of the chroot with `ToNormalRoot()` when absolute. `architecture`/`version`
  on packages are omitted when not recorded (matching the prose message
  variants). No timestamps: atime/mtime/ctime of chroot artifacts reflect when
  the simulation ran, not any would-be future state, and omitting them keeps
  the output deterministic (which the acceptance test exploits).
- `packages[]` is the **net** change set — the same
  install/remove reduction the `--simulate=diff` prose performs (cancellation
  of install-then-absent, remove-then-present, version-mismatch handling),
  now literally the same code (see refactor notes).
- Arrays are present (possibly empty) in every document, so consumers get a
  stable shape.
- `simulate_mode` is provenance only. The document content is intentionally
  mode-independent: the change set is the change set. In particular,
  `manifest-full`'s "kept files" are *not* included — this is a change set,
  not an inventory (named as an open question below).
- **Interface boundary (matters upstream):** this document, versioned by
  `format_version`, is the supported machine interface to the change set. The
  four record files at the chroot root (`changed_files`, `renamed_files`,
  `kept_files`, `pkgs_ops` — `libpromises/changes_chroot.h:28-31`) remain
  internal and unstable. That is the same framing issue #2 uses for PR 1
  (the retained *tree* is the artifact of record, not the record files).

## Design decisions and reasoning

1. **Option spelling: `--simulate-json=FILE`**, not the
   `--simulate-output=json` floated in issue #1/#3. Two reasons. (a) A
   mode-style flag implies replacing the prose renderer, which would mean
   making existing output paths conditional — more invasive, worse for a
   possible fork-carry. The file flag is purely additive: prose still prints,
   JSON additionally lands in a file. (b) It bundles the destination decision
   (issue #3 open question 1) into the surface: anything on stdout has to
   survive interleaving with `Log()` output (which also goes to the console)
   to be parseable, which is exactly the fragility this PR exists to remove.
   A file is unambiguous. No `-` = stdout special case in v1 — trivial to add
   later if a maintainer wants it.
2. **Content commitment by digest** (issue #3 open question 2): each regular
   file carries `sha256` of its would-be content. This is the
   security-relevant property downstream — an approver can bind an approval
   to digests, and PR 1's retained chroot can be verified against them.
   Full stat detail beyond mode/owner (times, inode, nlink) was deliberately
   left out; see the timestamps rationale above.
3. **No diff representation** (issue #3 open question 3): the `diff -u` text
   is not embedded. `RunDiff()` resolves the `diff` binary from `GetBinDir()`
   — CFEngine's own bin directory, not `$PATH`
   (`cf-agent/simulate_mode.c`, `RunDiff()`), and no install tree examined so
   far ships one there, so on macOS `--simulate=diff` fails out of the box.
   Embedding its output would import both the external dependency and an
   unstable text format into the JSON. Consumers wanting byte-level diffs
   should use PR 1's retained chroot. (This also means `--simulate-json`
   makes simulate useful on platforms where diff mode silently degrades.)
4. **Stability contract** (issue #3 open question 4): explicit integer
   `format_version` (constant `CHANGES_JSON_FORMAT_VERSION` in
   `simulate_mode.c`, with a comment stating the bump rule). Whether upstream
   wants to *call* it supported is their decision; the mechanism is there.
5. **Option state as a `static` in cf-agent.c** (`SIMULATE_JSON_FILE`), not a
   `GenericAgentConfig` field like PR 1 used. PR 1 needed the field because
   `libpromises/generic_agent.c` consumes it at chroot-creation time; this
   option is consumed only by `main()` in cf-agent.c, and cf-agent.c already
   has that idiom (`ALLCLASSESREPORT`, `PERFORM_DB_CHECK`). Bonus: it keeps
   this branch out of `generic_agent.h`, so PR 1 and PR 2 cannot conflict
   with each other in the config struct.
6. **Hook placement in `main()`: immediately before `GenericAgentFinalize()`**
   — NOT beside the prose renderers further down. This was forced by a bug
   found only by running the binary (next section). A code comment at the
   call site records the constraint.
7. **Package reduction shared, not duplicated.** The JSON needs the same
   net-effect reduction of the recorded package operations that
   `DiffPkgOperations()` performs (install-after-remove cancels, absent-after-
   install cancels on version match, higher-version-wins, etc.). Duplicating
   ~120 lines of subtle cancellation logic would be flatly rejected upstream,
   so the reduction loop was extracted verbatim into
   `static CollectPkgOperations(Map **installed_out, Map **removed_out)`,
   storing a new `PkgOperation {name, arch, version}` struct instead of
   pre-rendered message strings; `DiffPkgOperations()` now renders its prose
   via `GetPkgOperationMsg()` at print time. `ManifestPkgOperations()` (the
   present/absent view) is untouched, and `PkgOperationRecord` still exists
   for it. This is the highest-conflict-risk hunk in the diff and the place
   where upstream-quality was consciously chosen over rebase-friendliness.
8. **Failure = no output.** If any section fails to build (unreadable record
   file, etc.), the document is not written at all: a partial change set that
   parses cleanly is worse than an absent file. Errors are logged at
   `LOG_LEVEL_ERR`; a "Writing the simulated change set to '%s'" line is
   logged at `LOG_LEVEL_INFO` (matching the prose renderers' banner level).
9. **Formatting judgment.** The checked-in `.clang-format` disagrees with
   `simulate_mode.c`'s actual style (the file is full of 90–120-column
   lines). New self-contained code is wrapped to ≤78 columns per
   CONTRIBUTING (the same call PR 1 made in its new code); moved/adapted
   reduction code keeps the original's shape so the move stays reviewable.
   Note the repo `.clang-format` gotcha: its settings live in a
   `Language: Cpp` document, so clang-format ≥ ~18 silently ignores it for
   `.c` files — always run with `--assume-filename=<file>.cpp`
   (`/opt/homebrew/opt/llvm/bin/clang-format`, v22, verified).

## Claims that did not survive contact with the running binary

This project has now been burned three times by source-only reasoning; two
were previous sessions (chroot lifetime; release-version-from-CHANGELOG), one
was this session:

- **OpenSSL is torn down before the simulate reporting block runs.**
  Issue #3's premise "the renderer already runs before cleanup, so there is no
  lifecycle obstacle" is true for the *chroot* but turned out to be false for
  *hashing*: `GenericAgentFinalize()` (which runs BEFORE the prose renderers
  in `main()`) calls `CryptoDeInitialize()`, which on OpenSSL 3 unloads the
  default provider. After that, `EVP_DigestInit()` fails **silently** —
  libntech's `HashFile_Stream()` has no else-branch on that failure — and
  `HashFile()` returns an all-zero digest with nothing logged. First live run
  produced `"sha256": "0000...0"`; a standalone probe linking the same
  libutils hashed the same file correctly, which isolated it to agent
  lifecycle. Fix: write the JSON before `GenericAgentFinalize()`. Digests then
  verified byte-for-byte against `shasum -a 256`.
- **`content =>` promises write no trailing newline.** The first digest
  mismatch during verification was not a bug: CFEngine wrote `new contents`
  (12 bytes), not `new contents\n`. Worth knowing when eyeballing digests.
- **Package operations are recorded only by the package-modules path.**
  `RecordPkgOperationInChroot()` is called exclusively from
  `cf-agent/package_module.c` (new-style `packages:` promises with a
  `package_module`). Old-style `package_method` promises never record, so
  they will never appear in `packages[]` (named in residue below).
- Observed but pre-existing: with the mock module,
  `error: Error installing package 'caddy'` is logged during *evaluation* in
  simulate mode. Provably unrelated to this change (evaluation happens in
  `KeepPromises()`; all code added here runs later, at reporting time).
- **`RecordPkgOperationInChroot()`'s last two parameter names are swapped**
  relative to actual use: the header declares
  `(op, name, arch, version)` (`changes_chroot.h:37`) and the CSV writer
  writes the parameters in that order, but every caller in
  `package_module.c` passes `(op, name, package_version,
  package_architecture)` — so the on-disk field order is
  `op,name,version,arch`, which is exactly what the reader in
  `simulate_mode.c` expects (`f2=ver, f3=arch`). The pipeline is consistent
  end-to-end (confirmed live: `version => "2.0"` arrives as `version` in
  both prose and JSON); only the header's parameter *names* lie. Pre-existing
  upstream wart, harmless, deliberately not fixed in this PR — a candidate
  one-line cleanup to mention upstream.
- **`MakeParentDirectory()` transparently re-maps paths into the changes
  chroot** whenever `ChrootChanges()` is true (as do other libpromises file
  helpers): passing it an already-chrooted path in simulate mode creates a
  double-chrooted tree and still returns success. Found when the first unit
  test run failed with ENOENT after a "successful" mkdir. Anything running
  with `EVAL_MODE` set to a simulate mode must pass such helpers the
  *original* path.

## What was actually run (evidence)

All on macOS (Darwin 25.6.0), non-root, `CFENGINE_TEST_OVERRIDE_WORKDIR`,
binaries from the `make install` tree (`~/opt/cfengine-dev`).

1. **Files/renames live run** — policy exercising modify (`content =>`),
   create, delete (`delete => tidy`), symlink (`link_from`), rename
   (`rename => newname`):
   - All five appear with the correct `change` kinds; real files untouched.
   - `sha256` of the modified file = `6a5f63424a0c878f...`, byte-identical to
     `printf 'new contents' | shasum -a 256`. The empty created file yields
     the canonical empty-input SHA-256 (`e3b0c442...`).
   - Symlink `target` correctly mapped out of the chroot.
   - Output parses with Python `json.load`.
2. **Package live runs** — mock module
   (`tests/acceptance/07_packages/default_package_module.cf.module` copied to
   `$WORKDIR/modules/packages/test_module_script.sh`), installed-list seeded
   with package `unwanted`; promises `caddy` present (also with
   `version => "2.0"` in a second run) and `unwanted` absent:
   - JSON: `install caddy` (with `"version": "2.0"` when specified),
     `remove unwanted`. Manifest prose (untouched path) unchanged.
   - `--simulate=diff` run: the **refactored** `DiffPkgOperations()` prints
     exactly the pre-refactor messages
     (`Package 'caddy [2.0]' would be installed`, blank-line spacing
     preserved), plus identical JSON from the same run.
3. **Option validation:** `--simulate-json` without `--simulate` → hard error;
   relative path → hard error; `--help` shows the new hint correctly paired
   with its row (the OPTIONS/HINTS arrays are positionally coupled).
4. **Acceptance test** `tests/acceptance/29_simulate_mode/simulate_json.cf`:
   runs the shared `promises.cf.sub` under `--simulate=manifest` with
   `--simulate-json`, normalizes volatile fields (workdir path, sha256, size,
   uid, gid) with sed in the suite's own normalize-bundle idiom, and
   `dcs_check_diff`s against `simulate_json.cf.expected` (18 file entries,
   1 rename, 0 packages; generated from a real run and reviewed line by
   line). **Passes**, both standalone and in the full `29_simulate_mode/`
   run. Because uid/gid are normalized it passes rootless AND should pass as
   root in CI (unverified on CI, obviously).
5. **Regression baseline:** full `29_simulate_mode/` = 2 pass
   (`simulate_json.cf`, `simulate_safe_functions.cf`), 3 fail (`diff_mode`,
   `manifest_mode`, `manifest_full_mode`). Those three fail **identically on
   pristine master** in this environment (expectations assume Uid 0/root;
   plus the macOS `RunDiff`/`GetBinDir` issue) — an established baseline, not
   regressions.
6. **Unit tests** `tests/unit/simulate_mode_test.c` (13 tests, all passing,
   run directly and via `make check TESTS=simulate_mode_test` to prove the
   Automake registration works). The seams already existed — no design
   changes were needed for testability: `WriteChangesJson()` is the public
   entry point, `SetChangesChroot()`/`ToChangesChroot()` are public,
   `EVAL_MODE` is a settable global, record files are written in their real
   formats (`WriteLenPrefixedString()` framing; CRLF-terminated CSV exactly
   as `CsvWriter` emits), and `tests/unit/Makefile.am` already links
   `../../cf-agent/libcf-agent.la` for two other tests. Covered, none of it
   reachable by the acceptance test:
   - empty change set (no record files → stable empty-arrays shape,
     `format_version`, `simulate_mode`),
   - created/deleted/modified derivation with digests asserted against
     externally computed SHA-256 constants ("digest is of the would-be
     contents, not the current ones"),
   - duplicate records reported once,
   - path with UTF-8 + double quote + backslash survives JSON escape/parse
     round-trip,
   - symlink target mapped back out of the chroot,
   - rename pairs,
   - package reduction semantics: version-carrying install, bare remove,
     higher-version-wins, absent-version-mismatch keeps the install,
     remove+present cancellation, install+absent cancellation (matching and
     empty version). This is the only test coverage the reduction logic has
     ever had.
   One chroot per process (the `SetChangesChroot()` once-only assert); tests
   share it and reset the record files between cases.
7. Build: `make -j` clean; the touched files recompile with **zero
   warnings**.

### Reproducing locally (cold session)

```sh
./autogen.sh
./configure --prefix="$HOME/opt/cfengine-dev" \
  --with-openssl=/opt/homebrew/opt/openssl@3 --with-pcre2=/opt/homebrew/opt/pcre2 \
  --with-lmdb=/opt/homebrew/opt/lmdb --with-libyaml=/opt/homebrew/opt/libyaml \
  --enable-maintainer-mode
make -j"$(sysctl -n hw.ncpu)" && make install
# cf-agent needs cf-promises from the INSTALLED tree in $WORKDIR/bin
# (the build-tree "binary" is a libtool wrapper script):
mkdir -p "$WORKDIR/bin" && cp ~/opt/cfengine-dev/bin/cf-promises "$WORKDIR/bin/"
CFENGINE_TEST_OVERRIDE_WORKDIR=$WORKDIR ~/opt/cfengine-dev/bin/cf-agent \
  -Kf policy.cf --simulate=manifest --simulate-json=/abs/path/changes.json
# acceptance:
cd tests/acceptance && ./testall --gainroot=env \
  --bindir=$HOME/opt/cfengine-dev/bin 29_simulate_mode/simulate_json.cf
```

(`chown` failures on the mirrored tree are normal rootless noise on macOS.
Use `--simulate=manifest`, not `diff`, for live checks on macOS.)

## Fork-maintenance hunk inventory

Assume upstream may reject this and the fork carries it across releases.

| # | File | Anchoring symbol / location | Conflict risk | What a future rebase must verify |
|---|------|-----------------------------|---------------|----------------------------------|
| 1 | `cf-agent/cf-agent.c` | `OPTIONS[]` and `HINTS[]`: one line each, appended right after the `"simulate"` entries | **High.** Upstream appends to these regularly and they are positionally coupled — a botched rebase mis-pairs help text silently, it does not fail to compile | Count entries: the `simulate-json` row must sit at the same index in both arrays. Check `cf-agent --help` output pairs correctly |
| 2 | `cf-agent/cf-agent.c` | `CheckOpts()`: `else if (StringEqual(option_name, "simulate-json"))` after the `"simulate"` branch; post-loop validation after the `--trust-server` check; `static char *SIMULATE_JSON_FILE` after `PERFORM_DB_CHECK` | Low — self-contained else-if and statics | Compiles; `--simulate-json` without `--simulate` still errors |
| 3 | `cf-agent/cf-agent.c` | `main()`: `if (SIMULATE_JSON_FILE != NULL) { WriteChangesJson(...) }` immediately before `GenericAgentFinalize(ctx, config)` | Medium — main() teardown ordering churns occasionally | The call must stay BEFORE `GenericAgentFinalize()` (else `CryptoDeInitialize()` silently zeroes every digest) and before `CallCleanupFunctions()` (chroot teardown). Do not eyeball this — run the acceptance test and check a digest is non-zero |
| 4 | `cf-agent/simulate_mode.c` | `PkgOperation` struct + `PkgOperationNew/Destroy` after `PkgOperationRecordDestroy`; reduction loop moved from `DiffPkgOperations()` into `CollectPkgOperations()`; `DiffPkgOperations()` rewritten to reduce-then-print | **Highest in this diff.** If upstream edits the reduction logic in their `DiffPkgOperations()`, the move-hunk conflicts and must be re-merged by hand | The moved loop is upstream's verbatim except: record type swap (`PkgOperationRecord`→`PkgOperation`), `insert_new_msg`→`insert_new_record`, three comment words "message"→"record", and message rendering moved to print time. Re-verify diff-mode prose is unchanged (live pkg run, section above) |
| 5 | `cf-agent/simulate_mode.c` | JSON section appended at EOF after `ManifestPkgOperations()`: `CHANGES_JSON_FORMAT_VERSION`, `ChangedFileAsJson`, `AddChangedFilesToJson`, `AddRenamedFilesToJson`, `JsonArrayAppendPkgOperations`, `AddPkgOperationsToJson`, `WriteChangesJson`; three `#include`s at top | Low — pure addition, new self-contained functions | Compile + acceptance test. If upstream changes the record-file formats (`ReadLenPrefixedString` framing, pkgs_ops CSV field order), the readers here must track `AuditChangedFiles()` / `ManifestRenamedFiles()` / the CSV comment in `RecordPkgOperationInChroot()` |
| 6 | `cf-agent/simulate_mode.h` | `bool WriteChangesJson(const char *output_file);` after `ManifestPkgOperations()` | Negligible | — |
| 7 | `tests/acceptance/29_simulate_mode/simulate_json.cf{,.expected}` | New files | None | If the shared `promises.cf.sub` / `prepare_files_for_simulate_tests.cf.sub` change, regenerate `.expected` from a reviewed `.actual` |
| 8 | `tests/unit/simulate_mode_test.c` | New file | None | — |
| 9 | `tests/unit/Makefile.am` | `simulate_mode_test \` in `check_PROGRAMS` after `files_properties_test`; `simulate_mode_test_LDADD` line after `files_properties_test_LDADD` | Low — one-line insertions in lists upstream appends to; a dropped line means the test silently stops being built/run | `make check TESTS=simulate_mode_test` still reports PASS (proves registration, not just compilation) |

## Residue a reviewer must resolve before upstream

1. **Jira ticket.** `CFE-XXXX` placeholder in the commit message
   (`Changelog: Title` / `Ticket:` trailers) and in the acceptance test's
   `description` meta. Plan of record (issue #1): ONE Jira ticket covering
   both PRs, referenced from both, so PR 2 reads as half of a disclosed plan.
   Filing is gated on djbclark.
2. **Exit status on JSON-write failure** — currently logs `LOG_LEVEL_ERR` and
   leaves the exit code alone, consistent with how the prose renderers fail.
   A machine consumer might reasonably want a nonzero exit. Maintainer call.
3. **Create-then-delete transients** report as `"deleted"` even though the
   file never existed before the run (the prose has the same wart:
   "no longer exists"). The record files cannot distinguish this today.
4. **`manifest-full` kept files** are not in the JSON (it is a change set).
   If a maintainer wants an inventory mode, it is an additive `"kept": []`
   section behind the same version bump.
5. **Old-style `package_method` promises** never appear in `packages[]`
   (they never call `RecordPkgOperationInChroot()`). Should be stated in the
   PR text so it is not discovered as a surprise.
6. **Stdout convenience (`--simulate-json=-`)** was consciously omitted; ask
   maintainers if they want it.
7. **Package acceptance coverage:** the acceptance test covers files/renames
   only; package JSON was verified live with the 07_packages mock module and
   the reduction semantics are unit-tested, but an *acceptance* test for
   packages-under-simulate would need module-install plumbing inside the
   simulate suite (none exists upstream either).
8. **Upstream timing:** target release is 3.29.0 (master is `3.29.0a` — from
   the binary, not the CHANGELOG); features must be merge-ready two months
   before its release date.
9. `simulate_json.cf.expected` embeds the canonical `JsonWrite` rendering; if
   libntech changes JSON pretty-printing, the expected file needs
   regenerating (same exposure as every `.expected` in the suite).

## File map of the change (commit 071f85987, single commit on `simulate-json`)

```
cf-agent/cf-agent.c      +43   option row+hint, parse branch, validation,
                               SIMULATE_JSON_FILE static, main() hook
cf-agent/simulate_mode.c +454/-31  includes; PkgOperation struct;
                               CollectPkgOperations() extraction;
                               DiffPkgOperations() reduced-record printing;
                               JSON section (7 functions + version macro)
cf-agent/simulate_mode.h +2    WriteChangesJson() prototype
tests/acceptance/29_simulate_mode/simulate_json.cf          +65  (new)
tests/acceptance/29_simulate_mode/simulate_json.cf.expected +170 (new)
tests/unit/simulate_mode_test.c                             +459 (new)
tests/unit/Makefile.am                                      +3
```

(An earlier version of this report referenced commit `8c3918ccf`; the unit
test was amended into the same commit, which is now `071f85987`.)
