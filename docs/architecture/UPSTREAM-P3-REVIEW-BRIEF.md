# UPSTREAM REVIEW BRIEF — P-3, libntech silent digest-initialization failure

**Frozen input, 2026-08-16.** Shared prompt given verbatim to each member of the
second-opinion panel for P-3. Do not edit it to reflect what the reviews found.

**This one is different from the earlier panels: the patch is ALREADY OPEN
UPSTREAM.** It is not a draft we are deciding whether to send. It is
[NorthernTechHQ/libntech#291](https://github.com/NorthernTechHQ/libntech/pull/291),
open and mergeable, with issue
[#290](https://github.com/NorthernTechHQ/libntech/issues/290) behind it. It was
filed without a second opinion, before the review rule existed. So the question
is not "should we ship this" but **"is there anything wrong with what we have
already put in front of maintainers, and does it need a correcting push?"** A
finding here costs a force-push to a live PR, which is worth paying; a missed
finding costs our credibility with the reviewer who finds it instead.

---

## Your role

You are an independent reviewer of a C patch that is open as a pull request
against libntech (Northern.tech). It was written by a different AI model. Your
job is **adversarial**: assume the patch is wrong and try to demonstrate it.
Finding nothing is a valid outcome, but only after a real attempt.

Prefer measurement over reasoning from memory. This panel exists because the
same author has twice recorded a confident conclusion that measurement later
overturned.

## Where the code is

The libntech checkout is a **git submodule** inside the core fork:

```sh
cd ~/src/cfengine-core/libntech
git log --oneline -1                        # dc85a6f, the patch
git show dc85a6f                            # the whole change, 21 insertions / 3 deletions
git log --oneline -1 origin/master          # 0c0620d, the base — 1 ahead, 0 behind
git diff origin/master..HEAD -- libutils/hash.c
```

Remotes here: `origin` = `NorthernTechHQ/libntech` (upstream), `fork` =
`djbclark/libntech`. The branch is `silent-digest-failure`.

The consumer that sets the severity is `~/src/cfengine-core` itself
(a fork of `cfengine/core`) — grep it for `HashPubKey`, `HashFile`, `HashNew`.

**Do not build in `~/src/cfengine-core` or its submodule** — a build is already
configured there for other work and a reconfigure will disturb it. If you need
to compile, copy to a scratch directory first. `libntech`'s own tests are under
`tests/unit` (`hash_test`).

You have read access to both repos and the web. **Write nothing except your own
output file. Do not commit, push, branch, amend, or modify any existing file in
either repository.**

## The defect being fixed

`libutils/hash.c` calls `EVP_DigestInit()` / `EVP_DigestInit_ex()` in six
places. Three did not handle failure, and none of the three logged anything:

- `HashFile_Stream()` (behind `HashFile()`) and `HashPubKey()` zero their output
  digest up front and fill it in only on success. On failure the caller gets an
  **all-zero digest indistinguishable from a real one**. Both return `void`, so
  the digest buffer is the only channel and it carries no success indication.
- `HashNew()` ignored the return value entirely, then called
  `EVP_DigestUpdate()` and `EVP_DigestFinal_ex()` on an **uninitialized
  context**, returning a non-NULL `Hash` whose digest is meaningless.

Three siblings in the same file already handled it correctly — `HashString()`,
`HashNewFromDescriptor()`, `HashNewFromKey()` — and each fix is modelled on its
own in-file sibling, so the change is meant to be an oversight repair rather
than a new opinion.

**Reachability.** On OpenSSL 3, `CryptoDeInitialize()` unloads the default
provider, after which every subsequent `EVP_DigestInit()` fails. That is how
this was found, so it is not theoretical.

**Claimed severity.** `HashPubKey()` computes the digest of a host's public key
and feeds `lastseen.c`, `crypto.c`, `sysinfo.c`, `cf-execd-runner.c` in core. A
public key digest that silently becomes a constant is a **host identity that
collides across every host hitting the failure**.

## The fix

`HashFile_Stream()` and `HashPubKey()` gain the `else` branch that
`HashString()` already has (log at `LOG_LEVEL_ERR`, name the file where one
exists). `HashNew()` logs and returns `NULL`, as `HashNewFromDescriptor()`
already does; `HashBasicInit()` was moved below the check so the failure path
has nothing to free.

## Questions to answer explicitly

1. **Is `HashNew()` returning NULL actually safe?** The commit argues it is
   because `HashNew()` has **zero callers in `cfengine/core`** and already
   returns NULL on four other paths. **Attack that argument specifically:
   libntech is a shared library used by more than cfengine/core** (Mender and
   other Northern.tech products consume it). "No callers in the one consumer I
   checked" is not "no callers". What is the real blast radius of a new NULL
   return on a public API, and is a behaviour change of that kind acceptable in
   a bug-fix commit at all?
2. **Is the logging right?** Level (`LOG_LEVEL_ERR` vs `WARNING`), message
   wording and style against the file's existing strings, and — importantly —
   **does any new message leak anything it should not** (a path, a key, host
   identity) or invite log flooding if the failure is persistent, which it is
   by construction once `CryptoDeInitialize()` has run?
3. **Is the memory handling correct on the new failure paths?** Check for double
   free, leak, or use-after-free around `EVP_MD_CTX_create` /
   `EVP_MD_CTX_destroy`, and confirm that moving `HashBasicInit()` below the
   check did not skip initialization something later depends on. Note the file
   mixes deprecated (`_create`/`_destroy`) and current (`_new`/`_free`) OpenSSL
   spellings — is the patch consistent with its surroundings, and does that
   matter?
4. **Is "log but do not change the signature" the right call?** `HashFile()` and
   `HashPubKey()` return `void`, so the caller still cannot *detect* failure —
   it only appears in a log nobody may be reading. The commit names this as
   deliberately out of scope. Is that defensible, or is a fix that leaves the
   caller unable to tell a real digest from a failed one merely a fix to the
   logging and not to the bug? Argue it either way, but decide.
5. **Is the "no unit test" justification sound?** The claim is that forcing
   `EVP_DigestInit()` to fail requires `CryptoDeInitialize()`, which lives in
   core's libpromises and is unavailable to libntech's own tests, and that a
   libntech-level test could only assert the all-zero digest returned either
   way. **Try to break this claim** — is there a way to make `EVP_DigestInit()`
   fail from inside libntech's test harness (provider manipulation, a bogus
   `EVP_MD *`, `OSSL_PROVIDER_unload`, a mocked/interposed symbol)? If there
   is, the justification is wrong and the PR needs a test.
6. **Severity.** Is the host-identity-collision claim for `HashPubKey()` real,
   or overstated? Trace it in `~/src/cfengine-core` and say what an attacker or
   an unlucky operator actually gets. Does this belong on `security@` rather
   than an ordinary PR — and given it is *already* a public PR, does that
   framing need correcting now?
7. **Completeness.** The commit claims 6 `EVP_DigestInit*` call sites in
   libntech, 3 previously unguarded, 0 unguarded after. **Verify the census
   yourself.** Are there other silent-failure patterns of the same shape in this
   file or nearby (`libutils/`) that the patch walks past — other OpenSSL
   returns ignored, other functions that zero a buffer and fill it only on
   success?

## Also worth checking, unprompted

- **Commit hygiene against `CONTRIBUTING.md`.** Note its *process* section is
  deliberately not followed here, but style, log levels and commit-message
  rules apply. The commit carries `Changelog: Title` and `Ticket: #290`;
  #290 is a real upstream libntech issue.
- Whether the PR description and the commit message match, which CONTRIBUTING
  requires for a single-commit PR.
- Anything about the patch that a maintainer would reasonably push back on.

## Deliverable

Write **one file**:
`docs/architecture/upstream-opinion-p3-<your-slug>-2026-08-16.md` in
`~/src/tendcf`, with `<slug>` from your launch prompt.

1. **Verdict** — *leave as is*, *push a correction* (list exactly what), or
   *withdraw the PR* (say why).
2. **Severity verdict** — ordinary bug, or `security@`-grade, with reasoning.
3. **Defects found**, each with file and line, what breaks, and how to
   reproduce. Distinguish **verified** from **suspected** — say which you
   actually ran.
4. **The seven questions**, answered by number.
5. **What you did not check.**

**Independence:** do not read any other `upstream-opinion-*.md` file, and do not
read `docs/handoffs/`. Everything else in either repository is fair game.
