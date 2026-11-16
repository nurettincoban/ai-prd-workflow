# Cold read, RFC-006 (Run Lock), round 1

Question: what would you have to guess to implement this RFC? Ranked, at most five.

1. Which usage errors beat a held lock (Technical approach, "Which error wins"; criteria 2, 4; RFC-003 criteria 3, 11, 12).
   The RFC says "a bad argument and a held lock together give exit 2 at once" but defines that only as "argparse errors". RFC-003 puts `td add ""`, `td add $'a\nb'` and `td done abc` in the handler (`UsageError`, step 5, inside the lock, after `load_store`). Guess A: only argparse errors skip the lock, so `td add ""` against a held lock waits and then exits 1 (timeout), or exits 2 only after the holder leaves. Guess B: handler-level validation is read as "bad argument" and runs before the lock, giving exit 2 at once. The exit code, the wait and the data file all differ. Criterion 9 (what is recorded for `add -x`) does not settle it for `add ""`.

2. Whether `contextlib` may be imported (Technical approach says `data_lock` may be a `contextlib.contextmanager`; criterion 1 says the `td` import scan finds "no other new import beyond `fcntl` and `time`").
   These conflict unless an earlier RFC's `td` already imports `contextlib`; RFC-001 to RFC-005 mention it only for tests. Guess A: use `contextlib` and fail criterion 1. Guess B: write a class. Whether criterion 1 passes depends on it. It is also unclear whether `time` counts as "new" if `td` already imports it.

3. Which `OSError` from `flock(LOCK_EX | LOCK_NB)` means "already locked" and keeps polling (step 3).
   The RFC says "any other `OSError`" fails at once with exit 1, but does not say which errnos are "already locked". Guess A: only `BlockingIOError` (EAGAIN/EWOULDBLOCK). Guess B: also `EACCES` (which some platforms raise for a held non-blocking lock) and perhaps `EINTR`. On a platform that raises EACCES a held lock either waits and times out or fails at once, with a different time and message. This also decides whether the timeout text or the "other error" text is used.

4. Behavior when the directory cannot be opened `O_RDONLY` but the run could otherwise save (step 3, assumption 2).
   An unreadable but writable-and-searchable directory (mode `-wx`), or a read-only mount where `td done 99` or `td add -x`-style failures used to exit 1 or 2 anyway, now fails with a lock error. Guess A: that is exit 1 naming `str(path)` as stated. Guess B: for a read-only filesystem the lock is skipped or the run proceeds. The RFC says "not a silent skip", but also says no RFC-001 to RFC-004 criterion changes; the two collide for permission cases, and the error text then differs from the one `load_store` or `save_store` would have given.

5. What "the directory of `os.path.realpath(path)`" means when `path` is a symlink or a relative bare filename, versus the parent check on "path as passed" (steps 1 and 3; criterion 8).
   The parent check uses `path` as passed, the lock uses the realpath directory. Guess A: a bare `tasks.json` has dirname `""`, which is treated as the current directory in both. Guess B: an empty dirname fails the parent check (RFC-001 may pin this, but the RFC does not say whether the lock step reuses that helper or recomputes it). For a symlinked `TD_FILE` whose target is in another directory, the observable difference is which directory is locked, so whether two runs through different names take turns, and what criterion 8 `os.listdir` sees. Lower rank because the test holder uses `data_lock(path)` with the same value, so the tests would not tell the readings apart.
