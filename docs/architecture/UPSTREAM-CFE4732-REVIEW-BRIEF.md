# Review brief — CFE-4732 (B-15): `ReconcileMountOptions()` arms a timeout and never disarms it

Frozen 2026-08-18. Worktree `/Users/djbclark/src/core-mountleak`, branch
`fix/mount-options-timeout-leak`, based on **upstream master `a0bca6aaf`**.
Local only, nothing pushed. Upstream: `cfengine/core`. Jira: CFE-4732, Open,
1 comment.

**This review has an unusual centre of gravity.** The code fix is two lines and
almost certainly uncontroversial. What needs adversarial attention is a claim
that **contradicts the filed ticket**: I believe CFE-4732 overstates the impact,
and I intend to post a correction to a public tracker on the strength of that
belief. If the correction is wrong, that is far more damaging than shipping a
two-line patch would be. Attack the claim in §3 first.

---

## 1. The defect as filed

`ReconcileMountOptions()` (`cf-agent/nfs.c:1369`) calls `SetTimeOut(timeout)` at
`:1436` (remount path) and `:1461` (unmount_mount path). No path in the function
disarms. The only `alarm(0)` calls in `nfs.c` are `:581` and `:1178`, which pair
with the `SetTimeOut()` calls at `:403` and `:1122` in *other* functions.

Introduced by `348722a06` ("Added opt-in remount reconciliation for storage
mount options"), reachable only with the opt-in `remount_method` attribute.

Line numbers re-derived against `a0bca6aaf` and are unchanged from the
`22ce89322` the ticket cites.

## 2. The fix

One insertion inside the method loop, after the method dispatch and before the
convergence check, matching the file's own existing disarm idiom
(`alarm(0); signal(SIGALRM, SIG_DFL);` as at `:581` and `:1178`):

```c
        /* Both methods above arm a timeout and neither disarms it. It bounds
         * the reconcile command, so retire it here rather than letting it run
         * on into the convergence check and the next method. Until now it only
         * ever stopped because LiveMountConverged() -> LoadMountInfo() happens
         * to arm and disarm one of its own; nothing should depend on a callee
         * for that. */
        alarm(0);
        signal(SIGALRM, SIG_DFL);
```

Placed *inside* the loop rather than after it (which is what the ticket
suggests) so that the timeout bounds the reconcile command only, not
`LiveMountConverged()`. The `else`/`continue` branch at `:1466–1469` is skipped
deliberately — that path never arms.

**Deliberately based on upstream master, not on our own unmerged timeout
series.** `ClearTimeOut()` and `TimeOutIsArmed()` do **not** exist on
`upstream/master` — they are introduced by our in-flight branches (CFE-4727 /
CFE-4734 / CFE-4735). Using them here would make this patch un-landable on its
own. Hence the raw `alarm(0)` + `signal()` pair, which is what the file already
does twice.

## 3. THE CLAIM TO ATTACK — the ticket overstates the impact

CFE-4732 currently says:

> Consequence: the alarm outlives the operation. It fires later against
> unrelated work, where `TimeOut()` acts on whatever `ALARM_PID` names at that
> moment. Bounded [...] but **the window covers arbitrary subsequent agent
> work.**
>
> This is a **success-path leak** [...] Those only leak when something already
> went wrong; **these two leak every ordinary run.**

I believe both bolded statements are **false**, and that the leak never escapes
`ReconcileMountOptions()` on any normal path. My reasoning:

1. Both arming branches (`remount` at `:1417–1454`, `unmount_mount` at
   `:1455–1464`) fall through to `LiveMountConverged(name, a)` at `:1472`. Only
   the unknown-method `else` branch `continue`s past it, and that branch never
   arms.
2. `LiveMountConverged()` (`:1308`) calls `LoadMountInfo(tmp)` unconditionally
   (its only early return is `a == NULL`, which `ReconcileMountOptions()`
   already asserted against at `:1371`).
3. `LoadMountInfo()` (`:386`) calls `SetTimeOut(RPCTIMEOUT)` at `:403` — which
   **replaces** the leaked alarm — and then `alarm(0); signal(SIGALRM,
   SIG_DFL);` at `:581` on its normal path, **disarming it**.

So by the time `ReconcileMountOptions()` returns, the alarm it armed has been
superseded and cleared as a side effect of the convergence check. It does not
survive into "arbitrary subsequent agent work."

If that is right, the residual defect is narrower but still real:

- **A window**, from the reconcile command finishing (`cf_pclose()` at `:1452`,
  or `VerifyMount()` returning at `:1463`) until `LoadMountInfo()` re-arms at
  `:403`, during which the reconcile timeout is live over work it was never
  meant to bound. `ALARM_PID` has normally been cleared by `cf_pclose()` by
  then, so a fire there logs `"Time out"` and does nothing — but the budget is
  spent on the wrong thing.
- **Fragility**: correctness depends entirely on a callee's incidental side
  effect. Change `LiveMountConverged()` to read `/proc/mounts` directly instead
  of calling `LoadMountInfo()` and the leak becomes real and unbounded
  immediately, with no local sign that anything broke.

**Questions — answer each explicitly:**

- **Q1.** Is the masking chain in (1)–(3) actually correct? Walk it yourself
  against `a0bca6aaf`. Is there *any* reachable path on which
  `ReconcileMountOptions()` returns with its own alarm still armed?
- **Q2.** If `LoadMountInfo()` takes one of its early returns (`:408`, `:427`,
  `:487`) the alarm *does* escape — but armed by `LoadMountInfo()`'s own
  `SetTimeOut()`, not by `ReconcileMountOptions()`. Is it fair to attribute
  that escape to the pre-existing error-path family rather than to B-15? Or
  does `ReconcileMountOptions()` bear some responsibility for calling into a
  function that leaks?
- **Q3.** Is the residual defect enough to justify the patch at all, or should
  this be closed as "correct as written, relies on a callee"? I think the patch
  is still right on fragility grounds; argue me out of it if you disagree.
- **Q4.** Is my proposed *placement* (inside the loop, before
  `LiveMountConverged()`) better or worse than the ticket's suggestion (after
  the loop)? Consider a two-method list where method 1 fails to converge.
- **Q5.** Should the correction be posted as a **comment** on CFE-4732 (house
  convention: never rewrite a filed body, so retractions stay in the audit
  trail), or does a claim this central warrant editing the description too?

## 4. A third early-return leak the ticket omits

CFE-4732's catalogue says `nfs.c:403 leaks on :408/:427`. There is a **third**:
`:487`, the `strstr(vbuff, "RPC")` abort path, which does `cf_pclose(pp); free(vbuff);
return false;` with the alarm still armed. Note the irony — it is the *RPC
timeout* path, the very condition the alarm exists to catch, that leaks it.

**Q6.** Confirm or refute `:487`. If confirmed, should it go in the same
correction comment, or does it need its own ticket? It belongs to the
error-path family (which has no ticket of its own — it is only catalogued
inside CFE-4732's description), so there may be nowhere else to put it.

## 5. Testing — and why I am not offering a discriminating test

I am not offering an automated test, and I want that challenged rather than
accepted.

- `tests/unit/nfs_test.c` exists and links `libpromises.la`, but covers only
  pure string helpers (`MatchFSInFstab`, `OptionsSubsetMatches`,
  `OptionStringExpandDefaults`, `MountOptionsFromLine`, `GetFstabEntryOptions`).
  It has no `EvalContext` / `Promise` scaffolding.
- `ReconcileMountOptions()` needs an `EvalContext`, a `Promise`, mount
  attributes, and would actually execute `mount -o remount` against a real
  filesystem. Not portable, not safe in CI.
- `tests/acceptance/06_storage` exists but for the same reason cannot exercise a
  real remount on a test host.

**Q7.** A previous panel in this series disproved an "untestable" claim of mine
by finding a portable angle I had missed (forcing `pipe()` failure with
`RLIMIT_NOFILE`). Do the same here if you can. Is there a way to pin the
arm/disarm contract of this function — or of the masking chain in §3 — without
mounting anything? If there genuinely is not, say so plainly; that is an
acceptable answer, an invented test is not.

## 6. Build and measurement traps

1. **This worktree needed `git submodule update --init`** before `autogen.sh`
   would run (`./libntech/libutils/sequence.h is missing`). A fresh `git
   worktree add` does not populate submodules.
2. **`tests/acceptance/testall` exits 0 even when every test fails** — seen
   twice on this machine, two different causes. Read the passed count, never the
   exit code.
3. **`.libs` binaries carry an install-prefix RPATH**; `make && make install` is
   required before any acceptance run or everything dies on dyld (and still
   exits 0, per trap 2).
4. **Editing `libpromises/*.c` and then running `make <x>_test` in `tests/unit`
   silently runs the OLD library** — `make` reports "up to date". Rebuild
   `libpromises` first. This one faked a negative discrimination result earlier
   today. (It bites `cf-agent/nfs.c` less directly, but the same staleness
   applies to any cross-directory edit.)

State in a `## Trap control` section what you did about each, and what you
observed. "I did not build" is acceptable; an invented measurement is not.

## 7. Out of scope

- The other timeout tickets in flight (CFE-4727, CFE-4734, CFE-4735) are
  separate branches. Do not propose folding them together, and do not propose
  using `ClearTimeOut()` here — see §2.
- The `verify_exec.c` / `history.c` members of the error-path leak family.
- Whether `remount_method` is a good feature. It shipped; this is about its
  timeout handling only.

End with an explicit verdict line: **SHIP**, **SHIP-WITH-CHANGES**, or
**DO-NOT-SHIP**, and separately state whether the §3 correction to CFE-4732 is
**SAFE TO POST** or **NOT SAFE TO POST**.
