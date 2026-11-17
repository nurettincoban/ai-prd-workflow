# Cold read, RFC-006 (round 3)

Read: PRD.md (NFR-10, D-9, OQ 19-20 via search), FEATURES.md (F17 via search), RULES.md (not needed beyond the RFC's own citations), RFC-006, RFC-002 in full; RFC-001, 003, 004 only as cited by RFC-006.

## Verdict: passes

I found no guess that changes observable behavior or an interface.

What I checked in the changed text and found pinned:
- Round 1 and 2 fixes. The "held" retry set applies to `flock` only, and an `os.open` error is an immediate lock error (step 3, criterion 11). The parent check rule is pinned as RFC-001's, with a bare filename meaning the current directory, and the message starts with `str(path)` (step 1, criterion 8). The error-precedence order is stated, and criterion 9 tests it case by case. `data_lock` is a class with no `contextlib`. The no-`/`-or-`\` constraint on new string constants is stated. RFC-005 needs no edit.
- Interfaces: `LOCK_WAIT_SECONDS`, `MUTATING`, `data_lock(path)` (str or Path), the `with` placement in `main`, and `list` and bare `td` taking no lock are all fixed, and criteria 1, 3 and 4 test them.
- Exit codes and stderr shape: timeout and lock errors are exit 1, one `td:` line containing `str(path)` (criteria 4, 8, 11).

Residual points, none observable or none a guess (listed so the next reader does not rediscover them):
1. Criterion 1: how a test sees "a second data_lock in another process waits" is not spelled out (probably still running after a delay). A test-design detail, no behavior or interface differs.
2. A dangling symlink as `TD_FILE` or a race on the parent directory between the parent check and `os.open`: falls under the listed implementer's choice (symlink directory) or gives a lock error with exit 1 either way.
3. Criterion 11 says "data file unchanged" in a mode 0o300 directory, where the test cannot read it; a test-side detail.
