# Second opinion — P-3, libntech#291 (slug: cursor)

**Subject:** NorthernTechHQ/libntech#291 (`dc85a6f`, `silent-digest-failure`)
**Issue:** NorthernTechHQ/libntech#290
**Date:** 2026-08-16
**Reviewer:** cursor, adversarial panel member
**Method:** read the live PR, the commit, `libutils/hash.c` on that SHA, `hash.h`, `hash_test.c`, `CONTRIBUTING.md` via core, and the `HashPubKey` / `HashNew` / `KeyNew` call chains in `~/src/cfengine-core`. Compiled OpenSSL 3.6.3 probes in `/tmp/p3-review-scratch` (not in the core/libntech trees). Did not read other `upstream-opinion-*.md` files or `docs/handoffs/`.

---

## 1. Verdict

**Push a correction.** The C change is sound and should stay. What is already in front of maintainers is wrong in one place that they are likely to catch: the “no unit test” paragraph is false, and CONTRIBUTING requires tests for C functions.

Exact correction:

1. **Add an OpenSSL-3-gated test to `tests/unit/hash_test.c`, and run it last.** Load the default (and, matching core, legacy) provider, then `EVP_cleanup()` + `OSSL_PROVIDER_unload()` — the same two OpenSSL calls `CryptoDeInitialize()` makes. Assert `HashNew(...)` returns `NULL`. That is the one assertion that distinguishes patched from unpatched behaviour. `HashFile` / `HashPubKey` still return all-zero on this path, so they are a weaker test of the new `else` branches; a log-buffer assertion via `StartLoggingIntoBuffer(LOG_LEVEL_ERR, LOG_LEVEL_ERR)` would cover those if wanted. Reload/skip is not needed if the test is last; `EVP_cleanup()` is process-global.
2. **While rewriting the commit, drop “and it feeds lastseen and the TLS paths.”** Live TLS TOFU hashes the peer key with `HashNewFromKey` via `KeyNew`, not `HashPubKey`. Leave the lastseen / `TrustKey` / `sys.key_digest` claim; those are real `HashPubKey` consumers.
3. **Edit the GitHub PR body to match the commit** (CONTRIBUTING rule for a single-commit PR). That edit does not need a force-push; (1) and (2) do.

Do **not** change the `HashFile` / `HashPubKey` signatures in this PR. Do **not** withdraw.

---

## 2. Severity verdict

**Ordinary bug, not `security@`.** Do not refile privately; the PR is already public and the issue already states the demonstrated trigger is an internal call-ordering condition, not a remote exploit. That framing is the right one. Leave it.

The host-identity-collision story is real for some `HashPubKey` callers and overstated for TLS. Details under question 6. A silent all-zero digest in a TOFU filename is an integrity hole in the trust *model*, but the only measured trigger is hashing after `CryptoDeInitialize()`, which in core is shutdown (`cfnet_shut` / `GenericAgentFinalize`). Live TLS already failed closed on this failure via `HashNewFromKey`. That is not a security@-grade report.

---

## 3. Defects found

### Verified

**D1. The “no unit test / CryptoDeInitialize lives in core” justification is false.**
- Where: commit `dc85a6f` body (last prose paragraph); PR #291 description (same claim); issue #290 (same).
- What breaks: a reviewer who knows OpenSSL 3 can reject the PR on CONTRIBUTING’s “C functions should have unit tests” rule, using a recipe that does not involve core.
- How reproduced (ran, OpenSSL 3.6.3, `/tmp/p3-review-scratch/digest_fail2.c` and `hashnew_mimic.c`):

  `OSSL_PROVIDER_unload` of the default provider **alone** is not enough — `OSSL_PROVIDER_available(NULL, "default")` stayed 1 and `EVP_DigestInit` kept succeeding. Mimicking `CryptoDeInitialize()` **does** work, and it only uses libcrypto:

  ```
  OSSL_PROVIDER_load(NULL, "legacy");
  OSSL_PROVIDER_load(NULL, "default");
  EVP_cleanup();
  ERR_free_strings();
  OSSL_PROVIDER_unload(legacy);
  OSSL_PROVIDER_unload(default);
  ```

  After that: `EVP_get_digestbyname("sha256")` still returns non-NULL (so `HashNew` / `HashFile_Stream` / `HashPubKey` pass their `md == NULL` guards), `OSSL_PROVIDER_available(default)` is 0, `EVP_DigestInit` / `EVP_DigestInit_ex` return 0 (`digital envelope routines::unsupported` / `initialization error`). Unpatched-HashNew mimic: init=0, update=0, final=0, `len=0`, digest left as it was (calloc zeros in the real function). Patched `HashNew` would take the new `!= 1` branch and return `NULL`. HashFile-style memset-then-init-fail leaves 32 bytes of zeros.

  `hash_test.c` already calls `OPENSSL_init_crypto(0, NULL)` and links `libutils.a` plus libcrypto. It can include `<openssl/provider.h>` the same way core does. Core’s `CryptoDeInitialize()` is not required.

**D2. Commit overclaims the TLS path.**
- Where: `dc85a6f` (“it feeds lastseen and the TLS paths”); issue #290 similarly lists `tls_generic.c` / `client_protocol.c` as `HashPubKey` consumers.
- What breaks: a maintainer who greps those files will find `KeyPrintableHash` / `KeyNew` / `HashNewFromKey`, not `HashPubKey`, and will discount the severity paragraph.
- How reproduced: grep of `~/src/cfengine-core`. TLS verify/save paths:

  - `libcfnet/tls_generic.c:363` `KeyNew(remote_key, CF_DEFAULT_DIGEST)`
  - `libcfnet/client_protocol.c:525` same
  - `cf-serverd/server_tls.c:592` `SavePublicKey(..., KeyPrintableHash(...), ...)`

  `KeyNew` (`libcfnet/key.c:46`) calls `HashNewFromKey` and already returns `NULL` on digest-init failure (pre-existing, not this patch). `HashPubKey` is a different function.

**D3. PR body does not match the commit body.**
- Where: GitHub PR #291 vs `dc85a6f`.
- What: CONTRIBUTING (core, which libntech points at) requires a single-commit PR’s title and description to match the commit. Title matches. Body does not: the PR drops the “Verified by…” and “Making failure detectable…” paragraphs and the `Changelog` / `Ticket` trailer, and adds `Fixes #290` / fork-PR boilerplate the commit does not have.
- Ran: `gh pr view 291` vs `git show dc85a6f`. Process nit; fix by editing the PR text. Not a code defect.

### Suspected (not run)

None that I would put on the PR as blocking. Pre-existing patterns the patch walks past are under question 7.

### Code defects in the patch itself

**None found.** I tried: leak/UAF on the new `HashNew` path (context is `EVP_MD_CTX_destroy`’d; `HashBasicInit` is after the check so there is nothing to free), `filename` format-string injection (it is a `%s` argument), NULL `filename` (`HashFile` asserts non-NULL; only caller), OpenSSL `_create`/`_destroy` vs `_new`/`_free` inconsistency (the patch matches the function it edits), and a sixth unguarded `EVP_DigestInit*` (census is exact).

I did **not** rebuild `hash_test` or libntech — the brief forbids building in `~/src/cfengine-core` or the submodule, and a full copy-and-configure was not needed once the OpenSSL probe showed the new branch is taken.

---

## 4. The seven questions

### 1. Is `HashNew()` returning NULL actually safe?

**Yes, as a bug-fix on this public API.** Attack the “no callers in core” argument all you like — it is not a proof — but the blast radius of a *new* NULL is still small, and the change is the one the header already documents.

- `hash.h:45`: “A structure of type Hash or NULL in case of error.”
- Four other NULL paths already exist in `HashNew` (NULL data, zero length, `HASH_METHOD_NONE`, `EVP_get_digestbyname` failure). `hash_test.c` already asserts several of those.
- `HashNewFromDescriptor` has returned NULL on this exact `EVP_DigestInit_ex != 1` check since before this patch. The new path is a sibling, not a new contract.
- Grep of `~/src/cfengine-core` (excluding libntech itself): **zero production callers** of `HashNew(`; only `tests/unit/hash_test.c`. `HashNewFromKey` is what core actually uses (`libcfnet/key.c`).
- Broader consumers: libntech’s own README describes it as “a lightweight C library used in CFEngine.” Northern.tech’s public GitHub org does not show another C product linking it (Mender is a different stack). `libntech-example` exists as a sample, not a HashNew user I could confirm. I did not get a useful hit from `gh search code` (empty results — GitHub code search is not evidence of absence). I did not search private Enterprise trees. So: **not proven empty outside core**, but any out-of-tree caller that dereferences `HashNew` without a NULL check was already wrong on four paths. Adding a fifth error return for “OpenSSL could not initialise a digest” is the documented ABI, not a behaviour change on the success path.

A behaviour change of this kind **is** acceptable in a bug-fix commit when the function already returns NULL on error and the alternative is returning a non-NULL object whose digest is zeros. Fail closed is the repair; fail open was the bug.

### 2. Is the logging right?

**Yes, for what this PR is.**

- Level: `LOG_LEVEL_ERR`, matching `HashString` (`hash.c:531`) and `HashNewFromDescriptor` (`hash.c:194`). `HashNew`’s new string is copied from that sibling (“Could not initialize openssl hash context”), not invented.
- `HashFile_Stream` names the file, like `HashFile` already does on `fopen` failure (`hash.c:476`, `LOG_LEVEL_INFO`). Path-in-log is normal in this file and in core. It is a `%s` argument, not interpolated into the format string.
- `HashPubKey` logs no key material, no digest, no host identity. Good.
- Flooding: once `CryptoDeInitialize()` has run, every subsequent hash logs ERR. That is by construction. In core that function is shutdown (`libpromises/crypto.c:98`, called from `cfnet_shut` and `GenericAgentFinalize`). A burst of ERR at process teardown is acceptable. If digest init failed *during* a live agent run (broken provider, FIPS rejecting the algorithm), flooding ERR on every `HashFile` is the behaviour you want; crypto is broken. I would not drop this to WARNING.
- Pre-existing, not introduced: `HashString` logs the *buffer* on this failure (`hash.c:531–533`). That can be file contents or other caller data. This patch does not add a similar leak.

### 3. Is the memory handling correct on the new failure paths?

**Yes.**

- `HashNew`: on `EVP_DigestInit_ex != 1`, destroy the context, return NULL, never call `HashBasicInit`. No `Hash` to leak, no double-free, no use-after-free. `HashNewFromDescriptor` already does this at `hash.c:192–196`.
- Moving `HashBasicInit` below the check does not skip anything a later success-path step depends on: `HashCalculatePrintableRepresentation` still runs only after `EVP_DigestFinal_ex`, on a hash that was allocated after a successful init.
- `HashFile_Stream` / `HashPubKey`: the new `else` only logs; `EVP_MD_CTX_free(context)` still runs after the if/else. Digest remains the zeros `HashFile` / `HashPubKey` wrote up front.
- Deprecated `_create`/`_destroy` vs current `_new`/`_free`: `HashNew` and `HashNewFromDescriptor` already used create/destroy; `HashFile_Stream`, `HashString`, `HashPubKey`, `HashNewFromKey` already used new/free. The patch is consistent with its surroundings. It does not matter for correctness.

### 4. Is “log but do not change the signature” the right call?

**Defensible for this PR; it is a logging fix for `HashFile`/`HashPubKey`, not a fix to the undetectable-digest bug.** Decide: **keep the void signatures here.**

`HashFile` and `HashPubKey` still return `void`. On failure the caller still gets an all-zero buffer. `GetPubkeyDigest` (`libpromises/crypto.c:578`) always `HashPrintSafe`s that buffer and returns a string — its `if (digest == NULL)` in `TrustKey` is dead for this failure, because `GetPubkeyDigest` never returns NULL after `xmalloc`. `TrustKey` will still `SavePublicKey` a `SHA=0000…` identity. This patch does not close that hole; it only makes it audible.

That is still the right scope for *this* already-open PR:

- The whole commit is sold as an oversight repair modelled on in-file siblings. `HashString` logs and leaves zeros. Matching it is the conservative change.
- Turning two `void` functions into `bool` (or similar) is an API break with callers in both repositories. CONTRIBUTING wants small, single-issue PRs. That follow-up belongs in a separate libntech+core pair, not a force-push on #291.
- Leaving a sentinel other than zeros (e.g. `0xff`) would still be a colliding constant and would still print as an identity. It is not a substitute for a detectable return.

So: ship the log, say so honestly, and do not pretend the identity-collision is fixed for `HashPubKey` callers. A later change should make `GetPubkeyDigest` / `LoadPubkeyDigest` return NULL when the digest is uninitialised — that is a core change, not this one.

### 5. Is the “no unit test” justification sound?

**No. Broken by measurement.** See D1.

Ways that work from inside libntech’s harness, without core:

| Approach | Result (OpenSSL 3.6.3, ran) |
|---|---|
| `OSSL_PROVIDER_unload` of a just-loaded default provider, no `EVP_cleanup` | DigestInit still succeeds; `available(default)` stays 1 |
| `EVP_cleanup` + unload of the providers this process loaded (core’s sequence) | DigestInit returns 0; `get_digestbyname` still non-NULL |
| `EVP_DigestInit(ctx, NULL)` | Returns 0, but public `Hash*` APIs never pass a NULL `md` |
| `OPENSSL_cleanup()` | Subsequent lookup returns NULL (hits the *existing* `md == NULL` path, not the new branch) |
| Interposing `EVP_DigestInit_ex` | Not tried. `libutils` is `noinst`/`libutils.a`, so `--wrap` would work on ELF CI. Unnecessary given the provider recipe. |

The justification is wrong and the PR needs a test. Gate it on `OPENSSL_VERSION_NUMBER >= 0x30000000L`, put it last in `main`, assert `HashNew` is NULL. That is enough to lock the behaviour the commit claims to have verified by hand.

### 6. Severity. Is the host-identity-collision claim for `HashPubKey()` real, or overstated?

**Real for some callers, overstated for TLS, not attacker-driven on the measured trigger.**

What an unlucky operator actually gets, traced in core:

| Call site | Uses | On DigestInit failure after this patch |
|---|---|---|
| `libpromises/crypto.c:570,583` `LoadPubkeyDigest` / `GetPubkeyDigest` | `HashPubKey` | Still returns `SHA=0000…`. `TrustKey` (`cf-key`) still `SavePublicKey`s `ppkeys/<user>-SHA=0000….pub` and may `LastSaw1` that digest. First writer occupies the slot (`SavePublicKey` refuses overwrite). **This is the collision.** Logging is new; fail-closed is not. |
| `libpromises/crypto.c:312` `PolicyHubUpdateKeys` | `HashPubKey` then `LastSaw` | Hub copies `localhost.pub` to `root-SHA=0000….pub` if that name is missing. Startup path, crypto is initialised; the deinit trigger does not hit it. |
| `libpromises/lastseen.c:215` `Address2Hostkey` | `HashPubKey` of *local* `PUBKEY` only (127.0.0.1 / ::1 / VIPADDRESS) | Local identity string becomes zeros. Remote lastseen entries are written from `KeyPrintableHash`, not this. |
| `libenv/sysinfo.c:644` | `HashPubKey` | `sys.key_digest` / `PK_*` class become the zero digest. Inventory collision, not auth. |
| `cf-execd/cf-execd-runner.c:751` | `HashPubKey` | `X-CFEngine: pkhash=` header becomes zeros. |
| TLS TOFU (`tls_generic.c`, `client_protocol.c`, `server_tls.c`) | **`HashNewFromKey` / `KeyNew`** | Already NULL / no `Key` on this failure, before this PR. `SavePublicKey` on those paths never sees a zero digest from `HashPubKey`. |

Attacker: cannot force `CryptoDeInitialize()` remotely. I did not find another live `EVP_DigestInit` failure I could drive from a peer. FIPS-rejecting MD5, a missing provider at process start, or a future OpenSSL bug could hit the same branches without deinit; those are misconfiguration / local integrity, not a demonstrated exploit.

`security@`: no. Already-public PR: do not withdraw, do not try to make it unpublished. Soften the TLS sentence (D2) if the commit is rewritten for D1.

### 7. Completeness. Census of `EVP_DigestInit*`?

**Verified: 6 call sites in libntech, all in `libutils/hash.c`. Three were unguarded; zero are unguarded after this patch.**

| Line (post-patch) | Function | Guard |
|---|---|---|
| 150 | `HashNew` | **new** `!= 1` → log, destroy, NULL |
| 192 | `HashNewFromDescriptor` | already `!= 1` → log, destroy, NULL |
| 257 | `HashNewFromKey` | already `!= 1` → destroy, NULL, **no log** |
| 427 | `HashFile_Stream` | **new** `else` → log filename |
| 524 | `HashString` | already `else` → log buffer |
| 575 | `HashPubKey` | **new** `else` → log |

No other `EVP_DigestInit*` in libntech (`rg` over the submodule).

Same-shape patterns the patch correctly does **not** expand into:

- `HashNewFromKey` still silent on init failure (returns NULL). Pre-existing. TLS already depends on that NULL. A log there would be a drive-by; mention it, don’t pile it onto #291.
- Every `EVP_DigestUpdate` / `EVP_DigestFinal*` in this file ignores its return. Pre-existing, same class, out of scope.
- `HashFile` `fopen` failure: zeros, `LOG_LEVEL_INFO`, still indistinguishable from a real zero digest. Pre-existing.
- `memset(digest, 0)` then fill-on-success is the void-API shape itself (`HashFile`, `HashString`, `HashPubKey`). This PR cannot fix that without signatures.

---

## 5. What I did not check

- Did not build or run `hash_test` / libntech / core (forbidden in the configured trees; did not copy the whole project to scratch).
- Did not re-run the author’s `CryptoDeInitialize()` exercise inside a cf-agent binary; the OpenSSL mimic is the same two calls and produced the same DigestInit failure.
- Did not test OpenSSL 1.1.1 / LibreSSL. The new branches are version-agnostic; the test recipe is OpenSSL 3-specific.
- Did not audit private Northern.tech / Enterprise trees for `HashNew` callers. Public org + local core grep only.
- Did not try `LD_PRELOAD` / `--wrap` mocks (unnecessary after the provider measurement).
- Did not evaluate whether #290 should also be a Jira `CFE-` ticket (CONTRIBUTING prefers that; the issue already explains the reporter’s Jira access is broken). `Ticket: #290` is a real libntech issue.
- Did not investigate the `mender-test-bot` “error running your pipeline” comment on #291; looks like their runner, not this diff. CI via `gh pr checks` reported no checks on the branch.
- Did not read other panel opinions or `docs/handoffs/`.
