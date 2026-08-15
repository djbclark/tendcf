# PR 3 filing package: libntech silent digest-initialization failure

**Status: reference record, kept in tendcf.** It documents work on the
`djbclark/libntech` fork and must NOT be committed to the libntech branch or
included in the upstream PR. Everything below is ready to paste.

## Where this stands

| Item | State |
|---|---|
| Fork | **`djbclark/libntech`** — created 2026-08-15 (did not exist before) |
| Branch | `silent-digest-failure`, one commit `da7d3d9`, **pushed to the fork** |
| Base | libntech master `0c0620d` — 1 ahead, **0 behind**, no rebase needed |
| Build | clean; `hash_test` 6/6 pass |
| Jira ticket | **BLOCKED** — needs an Atlassian API token (see "What is blocked") |
| Upstream PR | not opened; waits on the ticket number for the title |

Operator decisions taken 2026-08-15: file a real CFE Jira ticket (not
ticketless), and own the fork under `djbclark` (not `frdminc`).

## Where it must be filed, and why

libntech's own `CONTRIBUTING.md` is a one-line redirect to
[`cfengine/core`'s](https://github.com/cfengine/core/blob/master/CONTRIBUTING.md).
That document is the governing process:

- **Code** → pull request against `NorthernTechHQ/libntech` (GitHub).
- **Ticket** → `https://northerntech.atlassian.net/projects/CFE/issues/`.
  libntech's GitHub issue tracker is effectively unused — 3 issues in its
  entire history, all closed, last 2025-03 — so a GitHub issue would likely
  go unread. Jira is where the maintainers actually work.
- **PR title format** → `CFE-1234: Title`. Omit the `(3.12)` suffix for master.
- **`Changelog:` and `Ticket:` must be in the commit message, not the PR
  description.** Explicit in CONTRIBUTING.
- **A `Changelog:` entry requires a `Ticket:`** — "All changelog entries should
  also include a reference to a ticket." Confirmed by practice: of the last 60
  libntech commits, 23 carry no `Ticket:` line, and *every one of those*
  also carries no `Changelog:` line. The two travel together.

**Their AI policy permits this work and names you the author.** CONTRIBUTING
§"Use of AI/LLMs in contributions" allows AI in contributions, requires that a
human review, understand and correct the output, holds AI-assisted code to the
same quality bar, and states that "the person using the AI as a tool,
fact-checking / editing its output and ultimately submitting the code as a pull
request" *is the author*. This is why the commit carries no AI-attribution
trailer: not evasion, but their stated model of authorship.

**Outside contributors land PRs here routinely** — e.g. #268 (Bastian Triller,
Placetel) and #260 (Martin Hart). A fork PR from a non-employee is normal.

**No duplicate exists.** Five targeted `summary ~` searches against project CFE
(`EVP_DigestInit failure`, `silent hash failure`, `all-zero digest`,
`CryptoDeInitialize`, `libntech hash`) all returned zero issues; full-text
searches returned only unrelated hits (a Solaris compilation issue, an LMDB
segfault). No GitHub issue or PR upstream either.

---

## Part 1 — the Jira ticket, ready to file

**Project:** CFE   **Issue type:** Bug   **Component:** libntech / libutils

**Summary:**

```
Digest initialization failure is silently ignored in three hash functions, producing all-zero and meaningless digests
```

**Description:**

```
libntech's libutils/hash.c calls EVP_DigestInit() or EVP_DigestInit_ex()
in six places. Three of them do not handle failure, each in a different
way, and none of the three logs anything:

  * HashFile() (via the static HashFile_Stream()) and HashPubKey() zero
    their output digest up front and fill it in only on success. On
    failure the caller receives an all-zero digest that is
    indistinguishable from a real one. Both functions return void, so
    the digest buffer is the only channel and it carries no success
    indication.

  * HashNew() ignores the return value entirely and then calls
    EVP_DigestUpdate() and EVP_DigestFinal_ex() on an uninitialized
    context. It returns a non-NULL Hash whose digest is meaningless.

This is an oversight rather than a decision. All three functions arrived
in libntech in the same commit, f277970 (2019-10-03, "Added hash
functions from libpromises"). At that commit HashString() already had
the else-branch that logs LOG_LEVEL_ERR in exactly this case, while
HashFile_Stream() and HashPubKey() went straight to freeing the context
with no else at all. The asymmetry has been there for six years and is
still present on master (0c0620d).

Impact. The most serious of the three is HashPubKey(), which computes
the digest of a host's public key. In cfengine/core it feeds
libpromises/lastseen.c, libpromises/crypto.c, libenv/sysinfo.c,
cf-execd/cf-execd-runner.c, and is included by libcfnet/tls_generic.c
and libcfnet/client_protocol.c. A public key digest that silently
becomes a constant is a host identity that collides across every host
that hits the failure. HashFile() has 12 call sites in core.

Reachability. This is not theoretical. On OpenSSL 3,
CryptoDeInitialize() unloads the default provider, after which every
subsequent EVP_DigestInit() fails. Anything that hashes after that point
is silently affected. That is how this was found.

Reproduction. Call any of the three functions, then call
CryptoDeInitialize(), then call it again. Observed on the second call,
against unmodified master:

  HashFile     -> all-zero digest, nothing logged
  HashPubKey   -> all-zero digest, nothing logged
  HashNew      -> non-NULL Hash, meaningless digest, nothing logged

Suggested fix. Each of the three has a sibling in the same file that
already does the right thing: HashString() logs in exactly this case,
and HashNewFromDescriptor() logs, destroys the context and returns NULL.
Modelling each fix on its own in-file sibling keeps the change an
oversight repair rather than a new opinion. A pull request doing this is
linked below.
```

**Link to add after the PR is open:** the `NorthernTechHQ/libntech` PR URL.

---

## Part 2 — the pull request, ready to open

Target: `NorthernTechHQ/libntech` `master` ← `djbclark:silent-digest-failure`.

**Title** (fill in the real number once the ticket exists):

```
CFE-NNNN: Handle digest initialization failure when hashing
```

**Body:** per CONTRIBUTING, a single-commit PR's title and description must
match the commit's title and body — so the body is the commit message body
verbatim, *minus* the `Changelog:`/`Ticket:` trailers, which belong only in
the commit. The commit body is already written and needs no edit; read it with:

```sh
cd ~/src/cfengine-core/libntech && git log -1 --format=%B da7d3d9
```

**One edit is required before opening the PR:** the commit currently carries
the placeholder `Ticket: CFE-XXXX`. Amend it to the real number:

```sh
cd ~/src/cfengine-core/libntech
git commit --amend            # replace CFE-XXXX with the real CFE number
git push --force-with-lease fork silent-digest-failure
```

The commit keeps `Changelog: Title`, which is correct here — the behaviour
change is user-visible (a previously silent wrong answer now reports itself)
and it now has a ticket to reference.

### Two things a reviewer will raise, both answered in the commit already

1. **"The checklist says add tests."** Forcing `EVP_DigestInit()` to fail
   requires deinitializing the crypto library, and `CryptoDeInitialize()`
   lives in cfengine/core's libpromises — libntech's own tests cannot depend
   on it without inverting the dependency direction. A libntech-level test
   could only assert the all-zero digest that is returned either way. This is
   stated in the commit message rather than left for the reviewer to find.
2. **"Why not make failure detectable by callers?"** `HashFile()` and
   `HashPubKey()` return `void`, so logging is all that is available without
   changing both signatures and every caller across both repositories.
   Deliberately out of scope, and named as such in the commit. `HashNew()` is
   the exception: it already returns `Hash *` and already returns NULL on four
   other paths, so failing closed there costs nothing and breaks nobody.

---

## Part 3 — verification record

Re-derived from scratch on 2026-08-15, not carried over on trust.

**Call-site census.** `EVP_DigestInit*` appears 8 times in libntech outside
tests; 2 are comment lines, leaving **6 real call sites, all in
`libutils/hash.c`**. Before: 3 unguarded. After: **0 of 6**. Nothing unguarded
anywhere else in the repository.

| line | function | state |
|---|---|---|
| 150 | `HashNew` | fixed — `!= 1` → log, destroy, return NULL |
| 192 | `HashNewFromDescriptor` | pre-existing, already correct (the model) |
| 257 | `HashStringFromDescriptor`-path | pre-existing, already correct |
| 427 | `HashFile_Stream` | fixed — `else` → log, names the file |
| 524 | `HashString` | pre-existing, already correct (the model) |
| 575 | `HashPubKey` | fixed — `else` → log |

**Idiom consistency.** `HashNew` already used `EVP_MD_CTX_create` /
`EVP_MD_CTX_destroy`, so the added `EVP_MD_CTX_destroy` on the new failure
path matches both its own function and `HashNewFromDescriptor`. No deprecated-
API inconsistency is introduced. The two new log strings are modelled on
`HashString`'s existing `"Failed to initialize digest for hashing: '%s'"`.
`HashBasicInit()` was moved below the check so the failure path has nothing to
free, matching `HashNewFromDescriptor`'s ordering.

**Origin of the asymmetry, verified in the tree.** At `f277970` the site that
is now `HashString` already had `else { Log(LOG_LEVEL_ERR, …) }`; the sites
that are now `HashFile_Stream` and `HashPubKey` had no `else` at all.

**Caller census in cfengine/core**, which is what sets the severity:

- `HashPubKey` — `libpromises/lastseen.c:215`, `libpromises/crypto.c:312`,
  `:570`, `:583`, `cf-execd/cf-execd-runner.c:751`, `libenv/sysinfo.c:644`;
  included by `libcfnet/tls_generic.c` and `libcfnet/client_protocol.c`.
- `HashFile` — 12 call sites.
- `HashNew` — **zero callers in cfengine/core**; only its declaration in
  `hash.h` and libntech's own tests. The new NULL return is downstream-safe.

**Build and test.** `make -j8` clean (exit 0); `make check TESTS=hash_test` →
all 6 tests pass. Diff is 21 insertions, 3 deletions, one file.

**A/B behaviour**, measured with standalone probes (hash → `CryptoDeInitialize()`
→ hash). The probe recipe is in handoff `d199`, "What We Tried" item 4 —
`platform.h` will not compile outside the build system and `libpromises.a` does
not exist, only the `.dylib`.

| function | unmodified master | with this change |
|---|---|---|
| `HashFile` | all-zero digest, silent | logs, names the file |
| `HashPubKey` | all-zero digest, silent | logs |
| `HashNew` | non-NULL `Hash`, bogus digest, silent | returns NULL, logs |

---

## Part 4 — what is blocked, and on what

**Jira authentication is now RESOLVED.** The CFE project is publicly
*readable* without auth (`GET /rest/api/2/project/CFE` → 200, individual
issues → 200), but creation is not: anonymous `GET
/rest/api/3/issue/createmeta?projectKeys=CFE` returns an empty `projects`
array, which is Jira's way of saying the caller may not create issues here.

The account is a Google-SSO login, which has no password — so an API token,
minted at <https://id.atlassian.com/manage-profile/security/api-tokens>, is
the only way in. Basic auth is `email:token`:

- **Token** — `ATLASSIAN_CFENGINE_API_TOKEN`, declared and set through the
  privilege-separated broker. Read it with
  `sudo-secretspec get ATLASSIAN_CFENGINE_API_TOKEN --reason "<why>"`, never
  by touching the store, the manifest, or `secretspec` directly. **`get` and
  `export` stream values straight to stdout** — parse, never echo.
- **Email** — `djbclark@gmail.com`. Recorded here rather than declared as a
  credential: it is not secret, and a second declaration would be a second
  piece of manifest drift to reconcile for no protective benefit.

Filing is gated by the `~/.claude/hooks/upstream_review_gate.sh` PreToolUse
hook, which denies tracker writes and `gh` writes against non-`djbclark`/
`frdminc` repos. That gate is working as intended; approval is per-artifact.

**Outstanding: manifest drift.** Declaring the token via
`sudo-secretspec add` put the runtime manifest ahead of the tracked
declarations file, so `sudo-secretspec template-check` now exits 1. This does
NOT affect PR 3, the fork, the upstream PR, or the Jira ticket — it is purely
local bookkeeping between two files. Its one real consequence is that
`~/ops/stayturgid/control/bin/publish_secrets.sh` runs
`sudo -n "$WRAPPER" source-template-check`, which is a `cmp -s` of the same
two files, so **publishing fleet secrets from stayturgid will fail until the
drift is reconciled.** Resolve either by mirroring the declaration into the
tracked file (task worktree → PR → coordinated release; it cannot be edited
in `~/ops`) or, once filing is done, by
`sudo-secretspec delete ATLASSIAN_CFENGINE_API_TOKEN` followed by
`undeclare`, in that order.

**Then, in order:** amend `CFE-XXXX` → the real number, force-push to the
fork, open the PR against `NorthernTechHQ/libntech` with the `CFE-NNNN:`
title, and add the PR link back to the Jira ticket.

## Related records

- Handoff `d199` — `docs/handoffs/HANDOFF_standalone-3fd9_libntech-pr3-schema-panel_2026-08-15_d199.md`
- PR 2 report — `docs/architecture/cfengine-pr2-simulate-json-report-2026-08-15.md`
- PRs 1 and 2 live on `djbclark/core`, branches `simulate-keep-chroot`
  (`5dbd295f6`) and `simulate-json` (`071f85987`). **Both still carry
  `Ticket: CFE-XXXX` too.** Whether they share one ticket with each other, and
  whether PR 3 shares it despite being a different repo in a different org, is
  still an open operator decision.
