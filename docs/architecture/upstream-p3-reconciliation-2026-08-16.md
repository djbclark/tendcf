# P-3 reconciliation — adjudication of the second-opinion panel on libntech#291

**Date:** 2026-08-16
**Adjudicator:** fable (final reviewer; read all three opinions, the frozen
brief, the filing package, the live PR/issue, and re-measured the contested
claims independently)
**Subject:** [NorthernTechHQ/libntech#291](https://github.com/NorthernTechHQ/libntech/pull/291)
(`dc85a6f`, branch `silent-digest-failure`), issue
[#290](https://github.com/NorthernTechHQ/libntech/issues/290)
**Panel:** `upstream-opinion-p3-{cursor,gemini,grok}-2026-08-16.md`

---

## 1. Adjudicated verdict

**Push a correction. Do not withdraw.** Unanimous across the panel and
sustained here. The 21-line C change itself is sound — no panellist found a
functional defect in it, and I found none either. What is wrong is the *prose
around it*: the commit, the PR body, and issue #290 all carry a false claim
("no unit test is possible from libntech") and an overstated claim ("it feeds
… the TLS paths"). Both are things a competent maintainer will catch, and the
first one contradicts CONTRIBUTING's test expectation. One force-push fixes
both, and the PR gains the test it should have had.

## 2. Adjudicated severity

**Ordinary bug. Not `security@`.** Cursor and grok sustained; gemini rejected.
Two-against-one is not the reason — the traced code paths are. I re-traced all
of them in `~/src/cfengine-core` rather than trusting the panel:

- **The demonstrated trigger is process teardown only.** `CryptoDeInitialize()`
  has exactly two call sites: `cfnet_shut()` (`libcfnet/client_code.c:66`) and
  `GenericAgentFinalize()` (`libpromises/generic_agent.c:1809`). Verified by
  grep. Nothing trusts a peer after those run.
- **Every peer-facing trust decision fails closed already, without this
  patch.** TLS TOFU and lastseen writes for remote hosts flow through
  `KeyPrintableHash()` / `KeyNew()` → `HashNewFromKey()`
  (`libcfnet/tls_generic.c:363`, `client_protocol.c:525`,
  `cf-serverd/server_tls.c:592`, `server_classic.c:846`), and
  `HashNewFromKey()` has returned NULL on `EVP_DigestInit_ex` failure since
  before this PR (`libutils/hash.c:257`). `SavePublicKey()` on the network
  paths is fed exclusively by `KeyPrintableHash`. Verified by grep — there are
  zero `HashPubKey` calls in `libcfnet` or `cf-serverd`.
- **What `HashPubKey` actually feeds** is self-identity bookkeeping:
  `TrustKey`/`GetPubkeyDigest` (cf-key, local operator tool — and
  `GetPubkeyDigest` can never return NULL, so `TrustKey`'s NULL check is dead
  and it would file `ppkeys/<user>-SHA=0000….pub`; verified at
  `libpromises/crypto.c:578–586`), `PolicyHubUpdateKeys` (own key, at startup,
  right after `CryptoInitialize`), the localhost branch of `Address2Hostkey`,
  `sys.key_digest` inventory, and cf-execd's mail header.
- **The decisive point, which no panellist stated explicitly:** even in the
  worst *live* failure (provider missing for the whole process, FIPS rejecting
  an algorithm), the zero digest is a colliding **lookup handle**, not a
  bypassed **cryptographic gate**. The slot `SHA=0000…` holds the first
  writer's real public key; impersonating that identity still requires the
  matching private key, and TLS possession-of-key checks are untouched. An
  attacker gains no new primitive; they cannot induce the failure remotely.
  What an operator gets is misattributed inventory and first-writer-wins
  confusion in `ppkeys` — an integrity/diagnostics defect, loudly logged after
  this patch.

Gemini's `security@` case rests on `HashPubKey` being "the identity for TLS"
enabling "man-in-the-middle attacks" and on Mender needing advisories. The TLS
premise is refuted by measurement (above). The Mender premise is unsupported:
Mender is a Go stack; libntech's own README names CFEngine as the consumer, and
no panellist (or I) found any non-CFEngine linker of libntech. Finally, #290 is
already public and already carries an accurate caveat ("not something a remote
attacker can force directly today"); routing to `security@` now would add
process theater, not confidentiality.

**Strongest case against this conclusion, stated so it can be acted on:** a
fleet-wide live init failure would make every affected host inventory as the
same `SHA=0000…` identity, and an operator keying policy off `sys.key_digest`
could make trust-shaped decisions on colliding identities. If a maintainer
reads it that way and asks for a CVE-shaped writeup, do not fight them — but
nothing in the traced code makes that reachable by an adversary, so it does not
justify re-filing.

---

## 3. Findings sustained

| # | Finding | Raised by | Adjudication |
|---|---|---|---|
| S1 | **The "no unit test" claim is false.** | cursor (measured), grok (measured, two methods), gemini (asserted, not run) | **Sustained, now triple-measured.** I independently compiled probes in scratch linking the already-built patched `libutils.a` against OpenSSL 3.6.3. In a fresh process, explicit `OSSL_PROVIDER_load` of `default` (+`legacy` for fidelity) followed by one `OSSL_PROVIDER_unload` each makes `EVP_DigestInit_ex` return 0 **while `EVP_get_digestbyname("sha256")` stays non-NULL** — so it is the *new* branch that fires, not the pre-existing `md == NULL` path. Against the real patched library: `HashNew` → NULL + "Could not initialize openssl hash context"; `HashFile` → all-zero digest + "Failed to initialize digest for hashing file '/etc/hosts'". No cfengine/core code involved. The PR's justification is wrong and the PR needs the test. **But see M1 below — both sustaining opinions prescribed the test in a place where it does not work.** |
| S2 | **"Feeds the TLS paths" is overstated.** | cursor, grok | **Sustained, verified by my own grep.** Commit `dc85a6f`, the PR body, and — worse — issue #290's "Worst-case impact" paragraph ("`HashPubKey()`'s output … is the actual TLS trust-on-first-use identity: `SavePublicKey()` writes trusted keys…") all make a claim the code refutes: the TOFU/`SavePublicKey`/`LastSaw1` network paths use `KeyPrintableHash` → `HashNewFromKey`, which fails closed pre-patch. The lastseen claim survives only for the localhost branch of `Address2Hostkey`. |
| S3 | **PR body does not match the commit body** (CONTRIBUTING single-commit rule). | cursor | **Sustained, verified against the live PR.** The PR body drops the "Verified by…" and "Making failure detectable…" paragraphs. Fix while force-pushing. |
| S4 | **`EVP_DigestUpdate`/`EVP_DigestFinal` returns are ignored in the same functions.** | gemini (as a demanded correction), cursor and grok (both noted it in Q7 and ruled it out of scope) | **Sustained as an observation only** — see R2 for the disposition. Note the panel framing given to me ("the other two did not raise it") is wrong: all three raised it; only gemini elevated it. |
| S5 | Changelog title is implementer-facing, not user-facing. | grok | Sustained as a nit; fold into the amend if convenient, don't churn otherwise. |

Also sustained without contest: the C change has no memory defect on the new
paths, logging level/wording matches in-file siblings, `HashNew`→NULL is the
documented contract (`hash.h:45`) with zero production callers in core (my grep
confirms), and the 6-site census is exact (my grep: 6 real `EVP_DigestInit*`
sites, all in `libutils/hash.c`, 0 unguarded post-patch, no callers of the
three functions inside libntech outside `hash.c` itself).

## 4. Findings rejected

| # | Finding | Raised by | Why rejected |
|---|---|---|---|
| R1 | `security@`-grade severity; alert downstream (Mender) for advisories. | gemini | See §2. The TLS premise is factually wrong, the Mender premise is unsupported, the trigger is not attacker-inducible, and the report is already public with an accurate caveat. |
| R2 | Fold `EVP_DigestUpdate`/`Final` checks into this PR. | gemini | Wrong scope. The PR's honest selling point is "oversight repair modelled on in-file siblings" — no sibling checks Update/Final, so adding checks is a new design decision, exactly what the commit avoids. The failure class also differs: post-successful-init Update/Final failures produce a hash of partial data (not the all-zero signature), have no demonstrated trigger (grok found no cheap way to force them), and belong in a follow-up. Disposition: one scope sentence in the rewritten commit + a fork-tracked follow-up issue, so maintainers see it was noticed, not missed. |
| R3 | Change `HashFile`/`HashPubKey` (and `HashString`) signatures from `void` in this PR. | gemini | API/ABI break across libntech and every caller in core (grok counted 10 `HashFile` + 6 `HashPubKey` production sites); the commit already names this deliberately out of scope; CONTRIBUTING wants small single-issue PRs. Both other panellists argue this correctly. Right as a follow-up direction, wrong as a force-push to #291. |
| R4 | Add ratelimit/one-time logging to the new ERR messages. | gemini | No such facility is used anywhere in this file; `HashString` has had identical flood behavior for six years; the demonstrated trigger is teardown (bounded); and a persistently screaming log when crypto is broken is the desired behavior, not a defect. |
| R5 | Gemini's "verified" labels on its testability and severity claims. | gemini | Gemini ran nothing (its own §"did not check" admits no build/run), and its one-line recipe `OSSL_PROVIDER_unload(OSSL_PROVIDER_load(NULL, "default"))` is **measured not to work** in the very environment (inside the existing test binary, after prior EVP use) where it would run — see M1. Its `StringCopyTruncateAndHashIfNecessary` observation is real (verified, `hash.c:678`) but is the same pre-existing class as S4: out of scope, `HashString` untouched by this PR. |

Also adjudicated on S1's sub-claims: cursor's negative result ("a single
default load+unload is *not* enough") is environment-dependent, not general —
in a fresh process on this machine a single load+unload of `default` alone
already made `EVP_DigestInit_ex` fail. Cursor and grok did not make "the same
mistake" — different methods, consistent core result — but both mis-prescribed
the test's placement (M1).

---

## 5. The exact correction to PR #291

One force-push to `fork/silent-digest-failure`, carrying **both** the amended
commit message and the new test (the corrected text references the test, so
they must land together — do not stage the text edit first).

### A. Amend `dc85a6f`'s message

1. **Replace** "…is an identity that collides across hosts, and it feeds
   lastseen and the TLS paths." **with** (wording to taste, substance fixed):
   > …is an identity that collides across hosts. In cfengine/core that digest
   > reaches TrustKey/GetPubkeyDigest (cf-key), PolicyHubUpdateKeys,
   > sys.key_digest, cf-execd's mail header, and the localhost entry of
   > lastseen's Address2Hostkey. The TLS trust-on-first-use path hashes peer
   > keys via HashNewFromKey(), which already failed closed before this
   > change.
2. **Delete** the entire "No unit test: …" paragraph. **Replace** with:
   > A test is included: hash_init_fail_test drains the OpenSSL 3 default
   > provider before any digest use, which makes EVP_DigestInit() fail while
   > EVP_get_digestbyname() still succeeds, and asserts HashNew() returns
   > NULL (and that HashFile()/HashPubKey() log and leave an all-zero
   > digest).
3. **Add** one scope sentence next to the existing "deliberately left out"
   paragraph:
   > The return values of EVP_DigestUpdate() and EVP_DigestFinal() remain
   > unchecked throughout this file, as before; checking them is a separate
   > change.
4. Update the "Verified by exercising each function…" paragraph to mention the
   test now automates that exercise. Optionally sharpen `Changelog: Title`
   into a user-facing sentence (S5); keep `Ticket: #290`.

### B. Add the test — as a NEW dedicated test program, not inside `hash_test.c`

New file `tests/unit/hash_init_fail_test.c`, plus `Makefile.am` entries
(`check_PROGRAMS += hash_init_fail_test`;
`hash_init_fail_test_SOURCES = hash_init_fail_test.c`). Shape, verified end to
end in scratch against the built patched `libutils.a`:

- `#if OPENSSL_VERSION_NUMBER >= 0x30000000L`: **as the first
  OpenSSL-touching action in the process**, before any digest use:
  `OSSL_PROVIDER *legacy = OSSL_PROVIDER_load(NULL, "legacy");`
  `OSSL_PROVIDER *def = OSSL_PROVIDER_load(NULL, "default");` then
  `OSSL_PROVIDER_unload(legacy); OSSL_PROVIDER_unload(def);` — **exactly one
  unload per load, never more** (over-unloading segfaults; measured).
- **Precondition guard:** fetch `EVP_get_digestbyname("sha256")` and assert
  non-NULL (proves the test exercises the *new* branch, not the pre-existing
  `md == NULL` return); attempt `EVP_DigestInit_ex` on a scratch ctx; if it
  unexpectedly succeeds (config-activated provider, FIPS build), **skip the
  assertions** rather than fail — the drain's effectiveness is
  environment-sensitive (measured, see M1) and the test must not be flaky.
- Assert `HashNew("This is a message", 17, HASH_METHOD_SHA256) == NULL`.
- Optionally: `HashFile()` on an existing file → digest all zeros;
  `HashPubKey()` with an RSA key built as in `hash_test.c`'s
  `HashNewFromKey` case → zeros; capture the two new ERR strings via
  `StartLoggingIntoBuffer(LOG_LEVEL_ERR, LOG_LEVEL_ERR)`.
- `#else`: pass trivially (or add the `Makefile.am`-documented symbol-override
  variant for pre-3 coverage; optional).
- **Put a comment in the file saying why it is a separate program** (M1): once
  any EVP digest operation has run, OpenSSL activates the default provider as
  a fallback and an explicit load+unload no longer drains it, so this cannot
  live at the end of `hash_test.c`.

Before pushing: run the new test against the patched branch (must pass) **and**
against base `0c0620d` (must fail — `HashNew` returns non-NULL there), in a
scratch build, per the regression-test policy.

### C. Edit the PR #291 body

Make it the amended commit body verbatim minus the `Changelog:`/`Ticket:`
trailers, keeping the `Fixes #290` line and the fork-PR reference at the end
(CONTRIBUTING single-commit match rule; S3).

### D. Post a short PR comment after the force-push

Force-pushes hide the diff-of-the-diff from anyone who already read v1. One
honest paragraph: the commit previously claimed a libntech unit test was
impossible — that was wrong, a test is now included; and the severity sentence
overstated TLS — the TOFU path hashes peer keys via `HashNewFromKey()`, which
already failed closed; `HashPubKey`'s real consumers are
cf-key/hub-own-key/inventory/execd-header/lastseen-localhost.

### E. Post a correcting comment on issue #290

Its "Worst-case impact" paragraph states `HashPubKey()` **is** the TLS TOFU
identity feeding `SavePublicKey()` — stronger and wronger than the commit. A
comment (not a silent body edit) correcting that paragraph and the no-unit-test
paragraph. No panellist put this on their corrections list (M3).

### F. Nothing beyond GitHub

No `security@` mail, no maintainer email. Verified: the 2026-08-16 security@
email covered B-1/B-2/B-8 only; P-3 was never emailed, so there is no prior
private characterization to correct.

---

## 6. What the panel missed

**M1 — Both sustaining opinions prescribed the test in a place where it does
not work, and the mistake would fail spuriously on the *patched* code.**
Cursor: "add it to `tests/unit/hash_test.c`, run it last." Grok: "the new case
belongs there [hash_test.c]." Measured here: in `hash_test.c`'s real
environment — `OPENSSL_init_crypto(0, NULL)` at `main()` start and successful
digests in the earlier cases — the provider drain **does not take**:
`EVP_DigestInit_ex` still returns 1 after loading and unloading both providers,
because prior EVP use activates the default provider as an OpenSSL *fallback*,
which an explicit load+unload pair does not remove. An unguarded
`assert(HashNew(...) == NULL)` appended to `hash_test.c` would therefore fail
against the very patch it is meant to lock in. The same measurement explains
the cursor/grok/gemini discrepancies about which minimal recipe "works": it
depends entirely on whether any EVP operation preceded the explicit provider
load. Hence §5B: dedicated test program, drain first, precondition guard.

**M2 — The recipes' incantations are partly cargo cult, and one variant is
dangerous.** `EVP_cleanup()` and `ERR_free_strings()` have been compile-time
no-op macros since OpenSSL 1.1.0 (confirmed in the 3.6.3 header) — cursor's
recipe works despite them, not because of them; the operative ingredient is
solely "explicit provider load+unload before any EVP use." And grok's "unload
until `OSSL_PROVIDER_available` is 0" phrasing, taken literally (repeated
unloads on one handle), **segfaults** — measured. The upstream test must never
encode either.

**M3 — Issue #290 needs its own correction** (§5E). Cursor and grok both
noticed #290 repeats the false claims, but neither put a #290 correction in
their actionable list; all three corrections lists touch only the commit and
PR.

**M4 — The severity argument nobody quite landed:** the zero digest is a
colliding *lookup handle*, not a bypassed *cryptographic gate* — possession of
the matching private key still gates every peer-trust decision, so even
gemini's worst case yields misattribution, not impersonation (§2). Worth having
ready if a maintainer asks "why isn't this a CVE?".

## 7. What I did not check

- **Unpatched-side behavior was not re-run by me.** The in-tree built
  `libutils.a` is the patched one; my probes verify the patched branch's
  behavior. That the base returns non-NULL/all-zero rests on code reading plus
  cursor's mimic. §5B's "must fail against `0c0620d`" step covers this before
  the push.
- Did not run grok's symbol-override method myself (one of the two measured
  routes); I verified the provider-drain route with three probes instead.
- Did not test Linux/ELF, OpenSSL 1.1.1, LibreSSL, or FIPS builds. M1 makes
  the final test's cross-platform behavior genuinely uncertain — the
  precondition guard exists precisely for that, and upstream CI will be the
  real check.
- Did not investigate the exact crash site of the over-unload segfault or the
  OpenSSL-internal fallback mechanics; measured behavior only.
- Did not audit private Northern.tech/Enterprise trees for `HashNew` callers
  (same limitation as the whole panel).
- Did not re-run `hash_test` (grok ran the built binary: 6/6) and did not
  investigate the `mender-test-bot` pipeline comment on #291.
- Wrote nothing except this file; no repo, PR, issue, or email was touched.
