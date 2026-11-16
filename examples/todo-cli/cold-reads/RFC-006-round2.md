# Cold read, RFC-006 (round 2)

Read: PRD.md, FEATURES.md, RULES.md, RFC-006, RFC-001 to RFC-004, in full (RFC-001 and RFC-003 partly via targeted sections).

Verdict: near pass. Round 1's fixes hold. Two guesses could still change observable behavior, both narrow; a third is a small interface question.

## Guesses, ranked

1. Does the "held" retry rule cover `os.open` of the directory? (Technical approach, step 3, vs criterion 11.)
   Step 3 says an `OSError` with `errno` `EACCES` or `EAGAIN` "means held by someone else" and is retried. It is written in the same sentence as both the `os.open` and the `flock` calls. An implementer who wraps open and flock in one retry loop will retry the `EACCES` that `os.open` raises on a mode `0o300` directory (criterion 11). That run then waits 10 seconds and reports "in use by another td run", not the OS error text, so criterion 11 fails. If the rule applies only to `flock`, it passes at once. Say so: the retry set applies to the `flock` call only; an error from `os.open` is always a lock error.

2. "Call the same code" as `load_store`'s parent check, but "does not touch `load_store`" (step 1 vs Implementation considerations).
   RFC-001 defines the parent check only as step (1) inside `load_store`; no separate function is exposed. The RFC says to call that code and not to recompute it, and also that `load_store` is not touched. The implementer must guess whether to extract a helper (editing `load_store`) or reimplement the rule. Observable difference: the pinned message form is only "starts with `str(path)`", so the text can differ between the lock's error and `load_store`'s. Other cases (bare filename, parent is a regular file, path is a directory) differ only if the reimplementation is sloppy. Impact is small because tests check only the prefix; naming the helper or allowing the extraction would close it.

3. RFC-005's import and ban-list checks (criterion 12, "which now see `fcntl` and `time`").
   Criterion 12 says RFC-005's checks "pass unchanged". It also says they now see two new imports. RFC-005 is not a dependency and I did not read it. If its check is an allowlist of imports without `fcntl`, this RFC must edit it. The RFC does not say whether that is in scope. Observable: the suite fails or passes at criterion 12.

## Not guesses (checked, pinned or immaterial)

- Which errors beat a held lock, `list` taking no lock, release before output, the `fcntl`-missing path, the killed-holder case, the timeout message start and exit code, the directory that is locked, and leaving no `.lock` file are all pinned.
- What `__enter__` returns and the poll interval change nothing observable.
- The symlink case is listed as the implementer's choice.
