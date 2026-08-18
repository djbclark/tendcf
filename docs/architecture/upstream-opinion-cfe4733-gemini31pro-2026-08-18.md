## Trap control

I verified the branch by examining the working directory in `/Users/djbclark/src/core-alarmreset`. I ran `git status` and `git show e7fd46c6d` to view the commit and the exact diff. I then used a file viewer to read the entire `ShellCommandReturnsZero()` function in `libpromises/unix.c` to confirm the surrounding context and check for any additional `wait` calls. Finally, I compiled the test suite using `make check -j4` in `tests/unit` and executed the newly added `./unix_test` directly, which passed both `test_shell_command_resets_alarm_pid_on_success` and `test_shell_command_resets_alarm_pid_on_nonzero_exit`.

## Q1

Yes, there are exactly two reap sites. I walked the entire `ShellCommandReturnsZero()` function against the current codebase. The process forks at line 177. The parent code executes a `while(true)` polling loop starting at line 236. The first `waitpid` is the `WNOHANG` call at line 238, and the second is the blocking `waitpid` drain loop at line 259 inside the `IsPendingTermination()` check. There are no other ways the child process is reaped in this function.

## Q2

Agree. At line 249, `waitpid()` has returned `< 0` and `errno != EINTR`. This indicates a failure to wait on the process. In this case, since we didn't successfully reap the process ourselves, it may still exist as a zombie holding the PID slot. Resetting `ALARM_PID` here would be incorrect for exactly the reasons the ticket mentions, so leaving it untouched is the right call. 

## Q3

Technically, yes, but practically it is safe. The first insertion is explicitly guarded by `if (wait_result == pid)`, guaranteeing a successful reap. 

However, the second insertion happens after:
`while (waitpid(pid, &status, 0) < 0 && errno == EINTR)`

This loop exits either when `waitpid` successfully reaps the child (`> 0`) OR when `waitpid` fails (`< 0` and `errno != EINTR`). If it fails, `ALARM_PID` is still reset to `-1`. But since we are waiting on a known valid child PID, the only realistic failure here is `ECHILD`, which means the child has *already* been reaped by something else. If it was already reaped, the PID is recyclable, and resetting `ALARM_PID` to `-1` is precisely the correct action. So while it resets without this specific call doing the reaping, there is no false negative.

## Q4

Acceptable. The `IsPendingTermination()` path only executes if a `SIGTERM` (or similar) arrives while the shell command is running. Testing this reliably requires orchestrating a signal delivery exactly during the polling loop, which is notoriously flaky in C test suites and would likely lead to spurious CI failures. Since the one-line fix is logically identical to the tested `WNOHANG` path, the risk is minimal. It's better to leave it untested than to introduce a flaky test.

**SHIP**
