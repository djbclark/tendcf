# Review: CFE-4732 (B-15) — `ReconcileMountOptions()` timeout leak

Reviewer: grok
Date: 2026-08-18
Worktree: `/Users/djbclark/src/core-mountleak`
Branch: `fix/mount-options-timeout-leak`
HEAD: `a0bca6aaf` (`upstream/master`)
Patch: unstaged `+9` at `cf-agent/nfs.c` (two executable lines + comment)
Independence: walked `a0bca6aaf` and the working-tree diff only. Did not read other `upstream-opinion-*` files or `docs/handoffs/`.

---

## Attack on §3 — the ticket overstates the impact

Both bolded sentences in the filed CFE-4732 text are false on every path that
actually completes an ordinary reconcile. The leak as filed — "the alarm
outlives the operation" and "covers arbitrary subsequent agent work"; "these
two leak every ordinary run" — does not describe what `a0bca6aaf` does.

I tried to break the masking chain in (1)–(3). I could not. Details are Q1.
The residual defect the author names (a short mis-aimed window, plus
correctness hanging off a callee's side effect) is the real one. That is
narrower than the ticket, and it is still worth the two-line patch.

A correction that says the two bolded claims are overstated is **safe to
post**, provided it does **not** say the defect is imaginary or that the
function is correct as written. The unpaired `SetTimeOut()` is real. What is
wrong is the claimed blast radius.

---

## Q1. Is the masking chain actually correct?

**Yes.** Walked against `a0bca6aaf` (`git show a0bca6aaf:cf-agent/nfs.c`),
not against the patched buffer.

`SetTimeOut()` (`libpromises/timeout.c:29–34`) is a full replacement, not an
add:

```c
ALARM_PID = -1;
signal(SIGALRM, (void *) TimeOut);
alarm(timeout);
```

POSIX `alarm(n)` cancels any pending alarm and starts a new one. After
`LoadMountInfo()` executes line 403, the remount-timeout is gone. What
remains is `RPCTIMEOUT` (60) with `TimeOut` as the handler.

### Every arming path falls through to `LiveMountConverged()`

`ReconcileMountOptions()` (`:1369`) arms in exactly two places:

| Site | What happens next |
|---|---|
| `:1436` `remount` | `cf_popen` / drain / `cf_pclose` or popen-fail log. **No `return`.** |
| `:1461` `unmount_mount` | `VerifyUnmount` then `VerifyMount`. **No `return`.** |
| `:1465–1469` unknown method | `continue`. **Never arms.** |

Early exits *before* the method loop (`a == NULL` at `:1372–1375`;
`MakingInternalChanges` false at `:1402–1409`) never reach a `SetTimeOut`.
An empty `remount_methods` list never enters an arming branch.

I read `VerifyUnmount` (`:988–1047`) and `VerifyMount` (`:892–984`). Both
return on every path they have (including `MakingInternalChanges` false,
popen fail, busy, read error). Neither calls `exit`/`abort`/`longjmp`.
Neither skips the caller’s fall-through to `:1472`.

`TimeOut()` itself (`timeout.c:38–51`) calls `alarm(0)`. A fire *during* the
reconcile command therefore also leaves no remount-timeout behind; the
handler has already cancelled it. The process then continues into
`LiveMountConverged()`, which re-arms `LoadMountInfo`’s own timer.

### `LiveMountConverged()` always calls `LoadMountInfo()` from this caller

`:1308–1318`: the only skip is `a == NULL`. `ReconcileMountOptions()`
already returned on that case at `:1372`, and this function is `static` —
the only caller is `:1472`. After the `a` check it always does
`LoadMountInfo(tmp)`. `SeqNew` is `xmalloc`; it does not return an empty
failure that would skip the call.

### `LoadMountInfo()` replaces, then (on success) disarms

`:396–403` copy `VMOUNTCOMM[VSYSTEMHARDCLASS]` up to the first space
(so Linux `/bin/mount -va` becomes `/bin/mount`), then `SetTimeOut(RPCTIMEOUT)`.
That is unconditional. There is no `#ifdef` around it.

Normal completion at `:580–584`:

```c
free(vbuff);
alarm(0);
signal(SIGALRM, SIG_DFL);
cf_pclose(pp);
return true;
```

So on the success path, by the time `ReconcileMountOptions()` returns — after
the `!converged` `cfPS` and the two frees — **its own remount-timeout is not
armed**. The handler is `SIG_DFL`. Subsequent agent work is not sitting under
that alarm.

This is the usual path into the function, not a curiosity. The only caller is
`verify_storage.c:531`, and it is only reached when `a->mount.remount` is
true *and* something is already mounted at the promiser but not as promised.
`VerifyStoragePromise` (`:129–135`) refuses to proceed if the first
`LoadMountInfo()` of the run fails and the global list is still empty. So
every entry into `ReconcileMountOptions()` is preceded, this process, by at
least one successful `LoadMountInfo()`. The second call, from
`LiveMountConverged()`, is the same command (`/bin/mount` / `/sbin/mount`
with no args — a table listing, not an NFS RPC). Ordinary hosts succeed and
disarm.

### Is there any reachable return with *this function's* alarm still armed?

**No.** "Its own alarm" meaning the `SetTimeOut(timeout)` at `:1436` or
`:1461`, with that remount-timeout still counting.

I could not construct a return that skips `LoadMountInfo()`’s `:403`
replacement after an arm. The candidates I tried:

- `cf_popen` failure on remount (`:1439–1442`): still falls through to `:1472`.
- `VerifyUnmount` / `VerifyMount` failure: still falls through to `:1472`.
- `timeout == 0` (`remount_timeout` is `0`, which is not `CF_NOINT` (`-678`)):
  `SetTimeOut(0)` is `alarm(0)`. There is no live remount-timeout to leak.
- Alarm fires during the command: `TimeOut()` already did `alarm(0)`.
- Two-method list, method 1 fails to converge: method 1’s timer is replaced
  (and, on success, disarmed) inside that iteration’s `LoadMountInfo()`
  *before* method 2 arms a fresh one.

### What *does* escape, and what must not be said

`ReconcileMountOptions()` **can** return with *an* alarm armed:
`LoadMountInfo()` early-returns at `:408`, `:427`, and `:487` after its own
`:403` `SetTimeOut`, without `alarm(0)`. That is a different alarm
(`RPCTIMEOUT`, handler `TimeOut`) and a different function. It is Q2 / Q6,
not a hole in (1)–(3).

Do **not** write in the tracker that "the leak never escapes the function."
Write that **the remount-timeout does not**. On `LoadMountInfo` error the
process *does* return into later agent work with a live `SIGALRM`. That
escape is the pre-existing error-path family, and it is not "every ordinary
run."

### Small qualification of the residual window, not of the claim

On the remount path, `cf_pclose()` at `:1452` sets `ALARM_PID = -1`
(`pipes_unix.c:853`). A fire in the window before `:403` then logs
`"Time out"` and does not kill. That matches the author’s description.

On `unmount_mount` it is slightly worse than that sentence. `VerifyUnmount`’s
success path (`:1044–1046`) never `cf_pclose`s, so `ALARM_PID` can still name
the umount child until `VerifyMount`’s `cf_pclose` (`:975`) or until
`LoadMountInfo`’s `SetTimeOut` resets it. If `VerifyMount`’s `cf_popen` also
fails (`:941–946`), the window can still hold a live pid. A fire then calls
`GracefulTerminate`. That is a pre-existing `VerifyUnmount` pairing bug, not
B-15, and it does not put the remount-timeout past `ReconcileMountOptions()`’s
return. Mention it only if the correction describes `ALARM_PID` as "always
cleared by then." Say "normally, on the remount path."

---

## Q2. LoadMountInfo early-return escape — whose leak is it?

**Attribute it to the pre-existing error-path family, not to B-15.**

`:408` (`cf_popen` failed), `:427` (`CfReadLine` error), and `:487` (`"RPC"`
in the listing) all return with `LoadMountInfo`’s own `SetTimeOut(RPCTIMEOUT)`
still live. The remount-timeout has already been replaced. The same three
returns are reachable from `verify_storage.c:129` on every storage promise
that finds an empty global list, with no `ReconcileMountOptions()` in the
stack at all.

B-15 is the unpaired `SetTimeOut` *in* `ReconcileMountOptions`. Calling a
function that already leaks on its error paths does not transfer that leak’s
ownership. Every other `LoadMountInfo` caller has the same exposure.
`MountAll()` (`:1122` / `:1130`) is the same family in the same file.

After this patch the situation is unchanged: the new `alarm(0)` runs, then
`LiveMountConverged()` → `LoadMountInfo()` re-arms, then `:408/:427/:487`
can still leak *that* arm. Anyone who tests "alarm remaining after
`ReconcileMountOptions` under forced popen failure" will see a live alarm
both before and after the patch. That is `LoadMountInfo`, not a failed B-15
fix.

`ReconcileMountOptions` is not innocent in the weak sense that it is one
more amplification site. That is not a reason to file the error-path family
under this ticket number.

---

## Q3. Residual defect — ship the patch, or close as "relies on a callee"?

**Ship the patch. Do not close.** I am not going to argue the author out of
it.

The residual is enough:

1. **A real window.** From remount `cf_pclose()` (`:1452`) or
   `VerifyMount` returning (`:1463`) until `LoadMountInfo:403`. The
   remount-timeout is live over work it was not written to bound (building
   the listing command, and, on `unmount_mount`, whatever
   `VerifyUnmount`/`VerifyMount` did not already consume). If the remount
   burned 59 of 60 seconds, the leftover can fire as a spurious
   `"Time out"` log during the listing setup. The budget is spent on the
   wrong thing. That is a defect even when nothing is killed.

2. **The pairing is the file’s own contract.** `:581` and `:1178` exist
   because the author of those functions did not want their `SetTimeOut` to
   outlive them. `:1436` and `:1461` are the same primitive, left unpaired.
   "A callee happens to save us" is not a pairing.

3. **The callee is allowed to change.** `LiveMountConverged()` exists
   specifically because remount’s exit status is not trusted (`:1298–1306`).
   Replacing `LoadMountInfo()` with a `/proc/mounts` read — the comment at
   `:387–388` already calls the `mount` listing "the most portable way" with
   visible distaste — would make the filed ticket accurate overnight, with
   no local signal at the `SetTimeOut` sites.

4. **Cost is two lines in the file’s existing idiom**, on a function that
   is already opt-in (`remount` defaults false, `mod_storage.c:51`). Not
   using in-flight `ClearTimeOut()` is the right landability constraint.

Closing as "correct as written, relies on a callee" would encode the
accident as the interface. `remount_timeout` is documented as "Timeout in
seconds for each remount_method." That is the command, not "the command and
whatever `LiveMountConverged` happens to do, unless it changes." Disarming
before the convergence check is the reading that matches the attribute.

---

## Q4. Placement: inside the loop, before `LiveMountConverged()`

**Better than the ticket’s "after the loop."** The `else`/`continue` skip is
correct; that branch never arms.

Two-method list, method 1 does not converge:

| | Inside loop, before verify (this patch) | After the loop (ticket) |
|---|---|---|
| Method 1 leftover covers `LiveMountConverged` | No. Disarmed first. Listing uses `LoadMountInfo`’s own 60s. | Yes, until `:403` replaces it. The leftover-fire window in Q3 stays. |
| Method 2 gets a fresh `SetTimeOut` | Yes (`:1461`). | Yes (`:1461`). After-loop does not help this. |
| Method 1 leftover can cover method 2 if `LoadMountInfo` stops calling `SetTimeOut` | No. | Yes. That is the fragility case. |
| Last-iteration `LoadMountInfo` `:408/:427/:487` leak cleaned on the way out | No. | Yes, accidentally. |

After-loop is an exit barrier. It is the right shape for "do not return
armed," and it would paper over `LoadMountInfo`’s error-path leak *for this
caller only*, on the last iteration only. It is the wrong shape for "this
timeout bounds this remount_method."

Inside the loop, before the verify, is the pairing. Method 2 cannot inherit
method 1’s leftover. `LoadMountInfo` keeps its own `RPCTIMEOUT`, so a user
who set `remount_timeout => "5"` does not have a 5-second leftover firing
during the listing.

I would not add a second `alarm(0)` after the loop. That would hide
`:408/:427/:487` only here, and this ticket is not the error-path ticket.
One pairing, at the arming sites’ join point, is the whole patch.

---

## Q5. Comment or rewrite the description?

**Post a comment. Do not rewrite the filed body.**

The two sentences being retracted are the ticket’s centre of gravity. That
is an argument for leaving them in place with a dated correction underneath,
not for editing them out. A silent rewrite makes the next reader think the
ticket was always the narrower claim. The audit trail is the point of the
house rule.

If the tracker can *append* a "Correction (2026-08-18)" block without
deleting the original text, that is optional and useful — people who only
read the description will otherwise keep quoting the overstated blast
radius. It is not required for the correction to be legitimate. The comment
is.

Do not close, do not retitle as invalid, do not soften the summary to
"timeout hygiene." The unpaired `SetTimeOut` is still the bug.

---

## Q6. Confirm or refute `:487`

**Confirmed**, against `a0bca6aaf`.

```c
if (strstr(vbuff, "RPC"))                         /* :480 */
{
    Log(LOG_LEVEL_INFO, "There was an RPC timeout. Aborting mount operations.");
    ...
    cf_pclose(pp);
    free(vbuff);
    return false;                                 /* :487, alarm still armed */
}
```

Same shape as `:408` and `:427`: resources for the pipe are released, the
timer is not. The irony the author notes is real — this is the listing
saying "RPC timeout," which is the condition the alarm exists to bound, and
the abort leaves the alarm running.

Put it in the **same correction comment**, as a catalogue fix: "CFE-4732
says `:403` leaks on `:408/:427`; it also leaks on `:487`." It is the same
function and the same family. The family has no ticket of its own. Do not
open a ticket just for `:487`. If an error-path ticket is filed later, move
the catalogue there; until then CFE-4732’s description is where the
catalogue already lives.

`MountAll:1130` (`SetTimeOut` at `:1122`, popen-fail return, no disarm) is
the same family and is also omitted. Same rule: mention in the comment if
the catalogue is being repaired, do not open a third ticket.

---

## Q7. Is there a portable discriminating test?

**No black-box test that pins B-15 without mounting, and the previous
panel’s `RLIMIT_NOFILE` trick would lie here.** I looked. I am not offering
one.

Why a post-condition on `ReconcileMountOptions()` cannot discriminate:

- **Success.** `LiveMountConverged()` → `LoadMountInfo()` success does
  `alarm(0)` at `:581`. Remaining-alarm is 0 with or without the patch.
- **Forced popen failure (`RLIMIT_NOFILE`, or a stub).** Remount’s
  `cf_popen` fails, then `LoadMountInfo:405` fails the same way, then
  `:408` returns with `RPCTIMEOUT` armed. Remaining-alarm is live with or
  without the patch. A "still armed ⇒ leak still present" reading is a
  false negative on the patch and a false positive on B-15.

The observable window is *between* remount finishing and `LoadMountInfo:403`.
Nothing outside the function can see it without a hook inside the function.

`tests/unit/nfs_test.c` already `#include`s `nfs.c`, so a white-box stunt
is possible in principle: `#define alarm` (and, to avoid executing mount,
a `cf_popen` that returns `NULL`) before the include, and count `alarm(0)`
calls originating in this TU. Unpatched remount+popen-fail: 0. Patched: 1.
That counts a local statement, not the POSIX alarm after return — because
`LoadMountInfo:403` will have re-armed the real timer. The fixture is also
easy to get wrong (`remount_timeout` of `0` is not `CF_NOINT`, so a
zeroed `Attributes` never arms; `cfPS` on the fail path wants a real
`Promise *`; `#define cf_popen` rewrites `pipes.h` prototypes). That is a
harness trick, not a contract test. I will not require it, and I will not
write it from here.

Calling `LoadMountInfo()` itself from `nfs_test` and asserting `alarm(0)==0`
would pin the *masking* chain, not B-15. It needs `VSYSTEMHARDCLASS` set to
a platform whose `VMOUNTCOMM` exists (`UNKNOWN` is `""`, which takes `:408`
and *leaves* the alarm armed). It runs a real `mount` listing. That is not
a remount and it is not "mounting anything," but it is host-dependent and
it would pass on `a0bca6aaf` unchanged. Useful as documentation of the
side-effect the correction relies on; not a B-15 test.

Acceptance `06_storage` still cannot do this. Even a Linux tmpfs remount
would not make the leftover timer visible to the test runner.

The author’s decision not to offer a test is acceptable. An invented
discriminating test would be worse.

---

## The patch itself

Unstaged, two executable lines, sitting at the join of the two arming
branches, after the unknown-method `continue`, before
`LiveMountConverged()`. Matches `:581` and `:1178`. Does not pull in
`ClearTimeOut()` / `TimeOutIsArmed()` from the in-flight series. Based on
`upstream/master` `a0bca6aaf` as claimed.

```c
        alarm(0);
        signal(SIGALRM, SIG_DFL);
```

Comment is slightly stronger than Q1 quite allows — "it only ever stopped
because `LiveMountConverged()` → `LoadMountInfo()` happens to arm *and
disarm* one of its own" is the success path, not `:408/:427/:487`. Not a
blocker. I would leave it; the next sentence ("nothing should depend on a
callee for that") is the actual justification.

No other file is touched. Reachability remains gated on `remount`
(default false). `remount_methods` is not itself the opt-in; if it is
unset the function defaults to `"remount"`. The brief’s "opt-in
`remount_method` attribute" is the `remount` boolean. Irrelevant to the
timeout pairing.

I did not compile the patch (see Trap control). The two calls are the
same ones the file already uses.

---

## Trap control

I did not run `autogen.sh`, `make`, `make install`, `tests/acceptance/testall`,
or any unit test. I did not rebuild `libpromises` or `nfs_test`. No
measurement of the patch exists in this review.

1. **Submodule / `sequence.h`.** Observed, did not repair. In this
   worktree `libntech` is checked out at `0c0620d6c` and
   `libntech/libutils/sequence.h` is present (10840 bytes, dated
   2026-08-18 12:20). A fresh `git worktree add` would not have that;
   this worktree already does. I did not run `git submodule update --init`.

2. **`testall` exit 0.** I did not run it, so I did not observe the
   "every test fails, exit 0" behaviour. I read
   `tests/acceptance/testall`. A top-level invocation exits 0 when
   `FAILED_TESTS <= SUPPRESSED_FAILURES` (`:1411–1418`). The
   `USE_INOTIFYWATCH` / `USE_INOTIFYWAIT` probes exit 0 at `:1356` and
   `:1370` without running tests if the binary is missing. I treated
   those as reasons not to trust an exit code I never produced.

3. **Install-prefix RPATH.** I did not run acceptance. I did inspect the
   already-built `cf-agent/.libs/cf-agent` (mtime 2026-08-18 12:29).
   `otool -L` shows it linked against
   `/Users/djbclark/opt/cfengine-dev-4732/lib/libpromises.3.dylib`.
   The `cf-agent/cf-agent` path is a libtool wrapper script, not a Mach-O.
   That is the trap, already visible in this tree. I did not `make install`.

4. **Stale `.libs` / `make nfs_test`.** I did not run `make nfs_test`.
   `tests/unit/Makefile.am` has `nfs_test_SOURCES = nfs_test.c` and
   `nfs_test_LDADD = ../../libpromises/libpromises.la libtest.la`. The
   test `#include`s `nfs.c` but does not list it as a source.
   `tests/unit/.deps/nfs_test.Po` exists and is empty, so `make` has no
   recorded dependency from `nfs_test` onto `cf-agent/nfs.c`. Editing
   `nfs.c` and typing `make nfs_test` can report "up to date" and rerun
   a binary that never saw the patch. I did not demonstrate that; I am
   not using a unit-test result.

---

## Verdict

**SHIP**

**SAFE TO POST**
