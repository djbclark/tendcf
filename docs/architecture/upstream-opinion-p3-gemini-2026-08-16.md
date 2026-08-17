# Verdict

*Push a correction.* The pull request only fixes the logging of the bug, not the bug itself. It leaves the logical vulnerability (host-identity collisions) untouched, misses identical silent failures on adjacent OpenSSL calls, and introduces a risk of log flooding. 

Specific corrections to push:
1. Change the signatures of `HashFile()`, `HashFile_Stream()`, `HashPubKey()`, and `HashString()` from `void` to a return type that indicates success/failure (e.g., `bool` or `int`), and update all upstream callers to handle the failure instead of proceeding with an all-zero digest.
2. Add return value checks for all calls to `EVP_DigestUpdate()`, `EVP_DigestFinal()`, and `EVP_DigestFinal_ex()` across `libutils/hash.c`.
3. Implement a ratelimit or one-time warning for the `LOG_LEVEL_ERR` messages to prevent disk exhaustion when the failure is persistent.
4. Add a unit test forcing `EVP_DigestInit` failure via OpenSSL provider manipulation or linker wrapping.

# Severity verdict

*`security@`-grade.* The bug causes silent host-identity collisions. `HashPubKey()` hashes a host's public key to generate its identity for TLS, crypto, and lastseen tracking. On failure, every affected host receives the exact same all-zero identity. In a fleet where `CryptoDeInitialize()` or another failure condition is hit, hosts will begin sharing an identity, potentially overwriting each other's keys, crossing data boundaries, or enabling man-in-the-middle attacks. Because the PR is already public, maintainers should be alerted to the security implications so that downstream consumers (including Mender) can issue advisories or patch out-of-band if necessary.

# Defects found

- **Verified:** `HashFile()` and `HashPubKey()` signatures remain `void` (`libutils/hash.c:454`, `libutils/hash.c:541`). The callers still receive and proceed with an all-zero digest upon hash initialization failure. *Reproduce:* Inspect the function signatures and observe that failure only logs an error without halting caller execution.
- **Verified:** Return values from `EVP_DigestUpdate()` and `EVP_DigestFinal[_ex]()` are ignored across `libutils/hash.c` (e.g., lines 158, 204, 269, 433, 526, 589). If updating or finalizing the digest fails, partial or zeroed digests are silently returned. *Reproduce:* Check OpenSSL documentation and the call sites in `hash.c`.
- **Verified:** `StringCopyTruncateAndHashIfNecessary()` (`libutils/hash.c:703`) calls `HashString()` and assumes success, appending an MD5 hash. If `HashString()` fails, it appends a hash of all zeros to the string, potentially causing unintended collisions for truncated strings.
- **Verified:** Persistent failures will cause log flooding. The new `LOG_LEVEL_ERR` in `HashPubKey()` inside a daemon loop will spam the logs endlessly once the OpenSSL provider is unloaded. *Reproduce:* Unload the provider and call `HashPubKey()` in a loop.

# The seven questions

1. **Is `HashNew()` returning NULL actually safe?**
   Yes, it is safe, though the commit's argument is incomplete. While it is true that `cfengine/core` has zero callers of `HashNew()`, Mender and other consumers use `libntech`. Changing a public API to return `NULL` risks a null pointer dereference if callers don't expect it. However, `HashNew()` *already* returns `NULL` on four other paths (e.g., OOM, unsupported algorithms). Callers adhering to the API contract must already be checking for `NULL`. A crash from an unprepared caller is still safer than the previous behavior of returning a valid `Hash` struct containing garbage memory.
   
2. **Is the logging right?**
   The log level (`LOG_LEVEL_ERR`) matches existing conventions (`HashString()`). The `filename` leaked in `HashFile_Stream()` is not a new risk, as `safe_fopen()` failing already logs the same filename just above it. However, placing a `LOG_LEVEL_ERR` on a persistent failure path inside a hot loop (like checking public keys) invites log flooding and disk exhaustion once `CryptoDeInitialize()` runs.
   
3. **Is the memory handling correct on the new failure paths?**
   Yes. `HashNew()` correctly uses `EVP_MD_CTX_destroy` (matching its local use of `_create`), and `HashFile_Stream()` correctly uses `EVP_MD_CTX_free` (matching its use of `_new`). Moving `HashBasicInit()` below the check is correct: it safely skips allocating a `Hash` struct that would otherwise have to be freed on the failure path, and no subsequent logic is skipped because the function returns early.

4. **Is "log but do not change the signature" the right call?**
   No, it is fundamentally the wrong call. Leaving the signature as `void` means the caller cannot detect the failure. The caller will proceed with the all-zero digest provided by the failure path. The patch only makes the bug visible in the logs; it does not fix the logic bug. The host-identity collision vulnerability remains fully intact. The signatures must be changed so the caller can abort.

5. **Is the "no unit test" justification sound?**
   The justification is unsound. A unit test in `libntech` can easily simulate `EVP_DigestInit` failure without needing `CryptoDeInitialize()`. Since `libntech` links against OpenSSL, the test could simply call `OSSL_PROVIDER_unload(OSSL_PROVIDER_load(NULL, "default"))` (on OpenSSL 3), or the test harness could use linker interposition (`-Wl,--wrap=EVP_DigestInit`) to mock the failure. 

6. **Severity.**
   The host-identity-collision claim is real. `HashPubKey()` provides the cryptographic identity of the host. If it silently zeroes out, any host hitting the error state assumes the identity "000...000". This guarantees identity collisions in `lastseen` and `crypto` modules across the fleet. Unlucky operators will see hosts overwriting each other's data, and attackers might exploit the predictable, uniform identity to forge requests or intercept traffic. This is a severe security issue (`security@`-grade) and its framing in a public PR underestimates the risk to the fleet.

7. **Completeness.**
   The census is incomplete. While the patch catches the 3 unguarded `EVP_DigestInit*` calls, it walks past identical silent-failure patterns in the very same functions: the returns of `EVP_DigestUpdate()` and `EVP_DigestFinal()` are completely ignored. If either fails, the functions silently return partial or zeroed digests.

# What you did not check

- I did not build the project or run the test suite to execute the proposed unit test mocking methods.
- I did not trace the exact downstream execution paths of the zero-digest in Mender or other Northern.tech products to determine their specific blast radius outside of `cfengine/core`.
- I did not check whether `cfengine/core` callers of `HashPubKey()` have any existing defensive checks for an all-zero digest (though it is highly unlikely given the nature of the bug).
