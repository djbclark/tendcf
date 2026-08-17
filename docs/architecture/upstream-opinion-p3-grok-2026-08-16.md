# Upstream opinion — P-3, libntech silent digest-initialization failure

**Reviewer:** grok
**Date:** 2026-08-16
**Subject:** [NorthernTechHQ/libntech#291](https://github.com/NorthernTechHQ/libntech/pull/291) (`dc85a6f` on `silent-digest-failure`, base `origin/master` = `0c0620d`)
**Role:** adversarial second opinion of an already-open upstream PR. Not a should-we-ship decision.

---

## 1. Verdict

**Push a correction.** The 21-line change in `libutils/hash.c` is an oversight repair that matches in-file siblings, does not leak or double-free on the new paths, and I could not break the new control flow. What is already in front of maintainers is still wrong in two package-level ways that a force-push should fix together:

1. **Add a unit test** in `tests/unit/hash_test.c` that forces `EVP_DigestInit_ex` / `EVP_DigestInit` to fail and asserts `HashNew()` returns `NULL`. Optionally also assert that `HashFile()` / `HashPubKey()` leave an all-zero buffer (that half is weaker; see Q5).
2. **Delete the commit/PR sentence** that says forcing `EVP_DigestInit()` to fail requires `CryptoDeInitialize()` in `cfengine/core` and is therefore unavailable to libntech's tests. That sentence is false. I forced the failure from a libntech-shaped harness in two independent ways (Q5).
3. **While rewriting that commit message**, correct "it feeds lastseen and the TLS paths." `HashPubKey()` does feed lastseen (localhost only), `TrustKey` / `GetPubkeyDigest`, `PolicyHubUpdateKeys`, `sys.key_digest`, and the cf-execd mail header. The TLS TOFU / `SavePublicKey` / `LastSaw1` network path uses `KeyPrintableHash()` → `HashNewFromKey()`, which already failed closed before this PR.

Do not change the `HashFile` / `HashPubKey` signatures in this PR. Do not withdraw. Do not refile via `security@` — the issue is already public as severity *normal*, and that framing is the right one.

---

## 2. Severity verdict

**Ordinary bug, not `security@`-grade.**

The all-zero public-key digest is a real integrity hole *if* `EVP_DigestInit` fails while identity work is still running. What I actually traced:

- The demonstrated trigger is process teardown. `CryptoDeInitialize()` has two call sites, both shutdown: `cfnet_shut()` (`libcfnet/client_code.c:63`) and `GenericAgentFinalize()` (`libpromises/generic_agent.c:1809`). I replicated CFEngine's OpenSSL 3 load/unload dance in a scratch program; after that replica, `EVP_DigestInit` returns 0. So the trigger is real — and it fires when the process is going away, not while it is trusting peers.
- The live TLS / TOFU identity is **not** `HashPubKey()`. `libcfnet/tls_generic.c:38` includes `hash.h` with a stale `/* HashPubKey */` comment; every production identity string on that path is `KeyPrintableHash()` → `HashNewFromKey()`. That sibling already returns `NULL` on `EVP_DigestInit_ex` failure (`hash.c:257-261`); `KeyNew()` already treats that as fatal (`libcfnet/key.c:46-50`). A failed digest there does not write `ppkeys/<user>-SHA=0000….pub`.
- `HashPubKey()` *can* still persist an all-zero identity on live (non-teardown) paths if init fails for some other reason (provider missing for the whole process, FIPS vs MD5, OOM inside init): `TrustKey()` → `GetPubkeyDigest()` (`crypto.c:578-586`, `607`) never sees a NULL from `HashPubKey` and will `SavePublicKey()` a `SHA=0000000000000000000000000000000000000000000000000000000000000000` string (measured via `HashPrintSafe` of a zero buffer). `GetPubkeyDigest()`'s documented-looking NULL check in `TrustKey` is dead — the function always returns a malloc'd string. First writer of `ppkeys/<user>-SHA=0000….pub` wins; later keys hash to the same slot and `SavePublicKey` says "already exists, not rewriting."
- That live collision is "crypto cannot hash and we used to hide it," not a demonstrated remote exploit. Issue #290 already says this. The public PR does not need to be pulled and refiled.

---

## 3. Defects found

### D1 — False "no unit test" justification, and the missing test
**Kind:** package / process, not a functional bug in the 21 lines
**Where:** commit `dc85a6f` body; PR #291 description (same paragraph); `tests/unit/hash_test.c` (no new case)
**What breaks:** CONTRIBUTING.md (core, which libntech defers to) says C functions should have unit tests. The commit tells maintainers a test is impossible. It is not. A reviewer who knows the `tests/unit/Makefile.am` mock note, or OpenSSL 3 providers, will find this before merge.
**Repro (verified, scratch programs in `/tmp`, linked against the already-built `libutils.a` — no rebuild of the submodule):**

- **Symbol override** (the pattern `tests/unit/Makefile.am` documents at lines 35-38): define `EVP_DigestInit_ex` to return 0. `HashNew("This is a message", …, HASH_METHOD_SHA256)` returned `NULL` and logged `Could not initialize openssl hash context`. Same override of `EVP_DigestInit` made `HashFile` leave a 32-byte all-zero digest and log `Failed to initialize digest for hashing file '…'`.
- **Provider drain:** after a faithful `CryptoInitialize`/`CryptoDeInitialize` replica (`OSSL_PROVIDER_load` of `legacy`+`default`, then `EVP_cleanup` + unload those handles), `EVP_get_digestbyname("sha256")` stayed non-NULL and `EVP_DigestInit` returned 0 (`error:0308010C:…:unsupported`). The new branches are therefore the ones that fire; this is not the pre-existing `md == NULL` path. `HashNew` returned `NULL`; `HashFile` / `HashPubKey` returned all-zero and emitted the new `LOG_LEVEL_ERR` strings.

A libntech test can do either. The second is OpenSSL-3-only; the first is not.

### D2 — TLS coupling overstated in the commit/PR
**Kind:** commit-message inaccuracy
**Where:** `dc85a6f` ("…it feeds lastseen and the TLS paths"); PR body, same sentence
**What breaks:** nothing in the binary. Maintainers reading the pitch will look at `tls_generic.c` / `SavePublicKey` and find `HashNewFromKey`, not this change.
**Repro (verified by grep of `~/src/cfengine-core`):** `HashPubKey(` production call sites are `libenv/sysinfo.c:644`, `libpromises/crypto.c:312,570,583`, `libpromises/lastseen.c:215` (localhost branch of `Address2Hostkey` only), `cf-execd/cf-execd-runner.c:751`. Network TOFU is `KeyPrintableHash`.

### No functional defect in the patch
I tried to find a double-free, leak, use-after-free, NULL deref on the new `filename` argument, format-string issue, or skipped `HashBasicInit` that a later path needed. I did not find one. Existing `hash_test` (already-built binary on this branch) still reports **6/6 passed**.

---

## 4. The seven questions

### 1. Is `HashNew()` returning NULL actually safe?

Yes. The commit's "zero callers in `cfengine/core`" argument is incomplete but the conclusion holds for a stronger reason.

- `hash.h:45` already documents `NULL in case of error`. The new branch is the fifth NULL return, not a new contract. The four pre-existing ones are `!data || length == 0`, `method >= HASH_METHOD_NONE`, `md == NULL`, `context == NULL` (`hash.c:124-149`). The "four other paths" count is accurate.
- The previous behaviour was not "return a slightly wrong hash." It called `EVP_DigestUpdate` / `EVP_DigestFinal_ex` on a context whose init had failed — undefined as far as OpenSSL is concerned — and handed the caller a non-NULL `Hash`. Moving to NULL is a bug-fix toward the documented API, not a behaviour change of a success path.
- Sibling `HashNewFromKey()` has returned NULL on this exact failure since before this PR (`hash.c:257-261`) **and has the real callers**: `KeyNew` / `KeySetHashMethod` in `libcfnet/key.c`. Those callers already fail closed. Modelling `HashNew` on `HashNewFromDescriptor` (log + destroy + NULL) is the conservative choice; `HashNewFromKey` is actually *less* talkative (NULL, no log).
- Blast radius outside core: I grepped `HashNew(` across `~/src/cfengine-core` (only `hash.c` / `hash.h` / `hash_test.c`), `~/src/cfengine`, and the rest of `~/src` excluding those. No production callers. libntech's own `README.md` names CFEngine as the consumer. GitHub code search (`gh api search/code` over `cfengine`, `NorthernTechHQ`, `mendersoftware`) returned empty or errored; I cannot certify the entire Northern.tech private surface. An out-of-tree caller that ignores NULL was already wrong on four other paths. That is the real residual, and it is acceptable in a bug-fix commit.

"No callers in the one consumer I checked" would have been a bad sole argument. It is not the sole argument.

### 2. Is the logging right?

Yes, with two caveats that are pre-existing rather than introduced.

- **Level.** All three new messages are `LOG_LEVEL_ERR`, matching `HashString` (`hash.c:531-534`) and `HashNewFromDescriptor` (`hash.c:192-196`). `HashFile`'s fopen failure is `INFO`; the new file-hash init failure is louder. That matches "hashing is broken" vs "file missing," and matches the sibling that already handled init failure.
- **Wording.** `HashNew` copies `HashNewFromDescriptor` verbatim (`Could not initialize openssl hash context`). `HashFile_Stream` is the `HashString` sentence with `file '%s'` instead of the hashed buffer. `HashPubKey` is the same sentence without a payload. Style is in-family.
- **Leak.** `HashPubKey` does **not** print key material. `HashFile_Stream` prints the path; `HashFile` already prints that same path on fopen failure (`hash.c:476-479`). `HashString` — untouched — logs the buffer being hashed (`Failed to initialize digest for hashing: '%s'`). I watched that fire in the provider-drain probe with `This is a message`. If anyone ever `HashString`s a secret and init fails, the secret goes to the log. Pre-existing, not this PR; the new `HashPubKey` message correctly does not copy that mistake.
- **Flood.** Once the default provider is gone, every subsequent hash logs ERR. I confirmed the messages actually emit (probe stderr). The demonstrated trigger is teardown, and `GenericAgentFinalize` does not call `HashFile` / `HashPubKey` after `cfnet_shut()`. A *persistent* init failure (provider missing for the process lifetime) would ERR on every file in change-detection (`cf-agent/verify_files_hashes.c:51-52`, `verify_files_utils.c:3713`, `cf-serverd/server_common.c:909`). That is the right noise: hashing is broken. Same flood already existed for `HashString`.

No new secret, no new path that wasn't already logged, no format-string issue (`filename` is an argument, not the format).

### 3. Is the memory handling correct on the new failure paths?

Yes.

- `HashNew` (`hash.c:150-155`): on init failure it `EVP_MD_CTX_destroy`s the context and returns NULL *before* `HashBasicInit`. Nothing allocated with `xcalloc` to free. The move of `HashBasicInit` below the check is exactly so the failure path has nothing to free; `HashCalculatePrintableRepresentation` only runs on the success path (`hash.c:163`). I did not find a later reader that assumes `HashBasicInit` ran on a failed `HashNew` — the caller gets NULL.
- `HashFile_Stream` (`hash.c:439-446`): both arms fall through to `EVP_MD_CTX_free`. Digest remains the zeros `HashFile` wrote at `hash.c:463`. Early returns for `md == NULL` / `context == NULL` were already like that.
- `HashPubKey` (`hash.c:599-605`): same free-on-both-arms shape as `HashString`.
- `EVP_MD_CTX_destroy` on a context whose `DigestInit_ex` failed is the same sequence `HashNewFromDescriptor` already uses. OpenSSL allows it.
- Deprecated `_create`/`_destroy` vs current `_new`/`_free`: `HashNew` / `HashNewFromDescriptor` already used the old pair; the patch stays on that pair. `HashFile_Stream` / `HashPubKey` already used the new pair; the patch does not switch them. Consistent with surroundings. It does not matter for this bug.

No leak, no double-free, no UAF on the new paths. I did not run ASan (see §5).

### 4. Is "log but do not change the signature" the right call?

**Yes, for this PR.** It is a logging fix of a silent failure, plus a real fail-closed for `HashNew`. It is not a full fix of "caller cannot tell a real digest from a failed one" — and that is the pre-existing `void` contract, not something this oversight-repair invented.

Decide, not waffle:

- `HashFile` already zeros the buffer and returns on fopen failure. Callers already cannot distinguish "could not hash" from "hash of something that produced zeros." `HashString` is also `void` and already only logs on init failure. Changing two `void` functions to `bool` is an ABI/API break across libntech *and* every core caller (I counted 10 production `HashFile(` sites and 6 production `HashPubKey(` sites in `cfengine-core`). That is a different, larger PR, and it is not required to make this an honest sibling-matching repair.
- `HashNew` *did* grow a detectable failure, because that API already had a NULL channel. That is the right split.
- Residual, and I want it on the record: `verify_files_hashes.c:51-60` treats two all-zero digests as "files were identical." `CompareLocalHash` (`server_common.c:911`) will report a match if the server could not hash and the client's digest is also zeros. After this PR those paths at least scream ERR. They still do the wrong *comparison*. Out of scope, but it is why I will not call the void-API leftover "the bug is fully fixed."

Do not expand #291 to change signatures.

### 5. Is the "no unit test" justification sound?

**No. Broken by measurement.** The PR needs a test.

The claim has two parts. Both fail.

1. *"Forcing `EVP_DigestInit()` to fail requires `CryptoDeInitialize()`."* False. I forced it with (a) a local `EVP_DigestInit_ex` that returns 0, which is how this test directory is designed to mock, and (b) `OSSL_PROVIDER` load/unload of `default` until `OSSL_PROVIDER_available(NULL, "default")` is 0. After (b), `EVP_get_digestbyname` still returns a pointer — so a test of `HashNew` is hitting the *new* branch, not the old `md == NULL` return. A one-line `OSSL_PROVIDER_unload` is *not* enough (implicit ref stays; I measured `DigestInit` still succeeding). Draining, or mocking, is.
2. *"A libntech-level test could only assert the all-zero digest returned either way."* True of `HashFile` / `HashPubKey` *if* you refuse to mock and refuse to look at logs. False of `HashNew`: before the patch it returned non-NULL; after it returns NULL. That is a one-assert test. I ran it.

`hash_test.c` already calls `OPENSSL_init_crypto`, already includes `openssl/evp.h`, already has a "Negative cases" block for `HashNew`. The new case belongs there.

I did not add the test. This review is not allowed to touch the libntech tree.

### 6. Severity. Is the host-identity-collision claim for `HashPubKey()` real, or overstated?

**Real as a class of bug, overstated as a description of the demonstrated trigger and of TLS.**

What an unlucky operator actually gets:

| Path | Uses | On init failure, after this PR |
|---|---|---|
| TLS TOFU / `SavePublicKey` of a peer | `HashNewFromKey` | `KeyNew` returns NULL; no `ppkeys` write. Unchanged by this PR. Still silent (no log). |
| `cf-key --trust-key` (`TrustKey`) | `HashPubKey` via `GetPubkeyDigest` | Logs ERR, then still writes `ppkeys/<user>-SHA=0000….pub` and lastseen. First key wins the slot. |
| Policy hub copies `localhost.pub` to `ppkeys/root-<digest>.pub` | `HashPubKey` | Same all-zero filename, now with a log. Runs just after `CryptoInitialize` (`generic_agent.c:1737-1748`), so the *teardown* trigger does not hit it. |
| `sys.key_digest` / class `PK_*` | `HashPubKey` | Every host with a broken digest init inventories as the same CFEngine ID. |
| `Address2Hostkey` of 127.0.0.1 / `::1` / `VIPADDRESS` | `HashPubKey` | Localhost lastseen key becomes `SHA=0000…`. Remote IPs do not go through `HashPubKey`. |
| cf-execd `X-CFEngine` mail header | `HashPubKey` | `pkhash="SHA=0000…"` |

An attacker who cannot make `EVP_DigestInit` fail does not get a new primitive from this bug. An operator whose OpenSSL 3 default provider never loaded gets colliding inventory IDs and a first-come `ppkeys` slot, and used to get that with no log. That is worth fixing. It is not a `security@` report, and given #290 and #291 are already public as *normal*, that framing does **not** need correcting now beyond the TLS wording in the commit.

### 7. Completeness. Is the census true? Anything walked past?

**Census: true.** Whole-tree grep of `~/src/cfengine-core/libntech` for `EVP_DigestInit` finds six call sites and two comment lines, all in `libutils/hash.c`:

| Site | Before | After |
|---|---|---|
| `HashNew` `:150` | ignored | log ERR, destroy, NULL |
| `HashNewFromDescriptor` `:192` | already guarded | unchanged |
| `HashNewFromKey` `:257` | already NULL, **no log** | unchanged |
| `HashFile_Stream` `:427` | no else | log ERR with path |
| `HashString` `:524` | already logs (and leaks the buffer) | unchanged |
| `HashPubKey` `:575` | no else | log ERR, no key material |

Zero unguarded `EVP_DigestInit*` remain. No other file under `libutils/` calls `EVP_*` digest init.

Same-shape leftovers this PR walks past, none of them introduced:

- `HashNewFromKey` fails closed **silently**. That is the function TLS actually uses. A drive-by log there would have been more valuable than logging `HashNew`, which has no production callers. Out of scope if we keep this an oversight repair; worth a sentence in the PR so a maintainer does not think it was missed by accident.
- `EVP_DigestUpdate` / `EVP_DigestFinal*` are unchecked at all six sites. If init succeeds and update/final fail, `HashFile` / `HashPubKey` still publish a buffer and do not log. I did not find a cheap way to force that without mocking those symbols too.
- `HashFile` fopen failure: zeros + `INFO`. Same undetectable digest, already the API.

I would not grow #291 to sweep those.

---

## 5. Also checked, unprompted

**CONTRIBUTING.md** (core; libntech's file is a pointer):

- Process section (Jira-first, `CFE-1234:` PR title) is deliberately not followed; #290 explains the broken Jira access. Fine.
- Style: 4-space Allman, pointer stars on the name, new `Log` calls wrapped like their siblings, no tab, no 78-column string split of a literal. Matches the file.
- Commit title is 49 characters, no trailing punctuation. Body wraps at ≤72. `Changelog: Title` and `Ticket: #290` are present in the *commit* (where CONTRIBUTING says they belong). #290 exists and is the right issue.
- Changelog title "Handle digest initialization failure when hashing" is implement-y; CONTRIBUTING wants user-facing impact. A better Title would name the silent all-zero digest. Not a blocker.
- Single-commit PR: title matches the commit title. Description is a *shortened* commit body (drops the "Verified by…" paragraph and the "deliberately left out of this change" paragraph) plus `Fixes #290` and a fork-PR link. CONTRIBUTING wants title *and* description to match a one-commit PR. Minor. Fix it when rewriting the commit for D1/D2.
- CLA bot: signed. `mender-test-bot`: "error running your pipeline" pointing at a GCP log I cannot read. `statusCheckRollup` via `gh` was empty. I am not treating the bot failure as a patch defect.

**Maintainer push-back I would expect, in order:** (1) "where is the test?" (2) "TLS?" (3) "why not change the `void` returns?" — (3) is answerable from the commit as written; (1) and (2) are why I want a force-push.

---

## 6. What you did not check

- Did not read any other `upstream-opinion-*.md` or anything under `docs/handoffs/`.
- Did not build or reconfigure `~/src/cfengine-core` or the libntech submodule. Probes linked the already-built `libutils.a` / `libcompat.a` and ran the already-built `hash_test`.
- Did not run the author's exact "call X, `CryptoDeInitialize()`, call X again" binary inside a CFEngine agent. I replicated the OpenSSL 3 half of that function and I traced its only two call sites.
- Did not run ASan/UBSan, valgrind, or a Windows/`text_mode` `HashFile` path.
- Did not exercise FIPS-mode MD5 rejection as another live init-failure.
- Did not inspect `mender-test-bot`'s GCP logs.
- Did not search Northern.tech private remotes I do not have. Public GitHub code search was unusable from this environment (empty or `invalid character` errors).
- Did not re-audit `EVP_DigestUpdate`/`Final` failure as a live bug; I only noted the ignored returns.
- Did not verify OpenSSL 1.1.1 (no providers). The mock test does not need them; the provider-drain test does.

---

*End of opinion. One file, nothing committed.*
