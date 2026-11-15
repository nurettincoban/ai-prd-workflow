# Review: RFC-001 Storage core

Reviewer context: fresh session, did not write the code. Commit reviewed: `51f0d37 /implement-rfc RFC-001` (Files changed list in Implementation Notes: `td`, `tests/helpers.py`, `tests/test_storage.py`, `tests/fixtures/v1.json`, `.gitignore`).

## Round 1 -- 2026-11-15

**Overall verdict: PASS with non-blocking findings. Overall risk: Low. Status set: Reviewed.**

Product type (PRD.md): CLI. Applied: exit codes on the error classes, data-file handling, environment and path handling, cross-platform paths. Skipped: command/flag design, stdout/stderr, piping (no command exists until RFC-002); UI, accessibility, SEO, sessions, auth, scalability, caching (PRD records them as skipped; plain-text single-user tool).

Open conflicts in RFCS.md: conflict 1 (no lock) touches this RFC; the code correctly builds no lock (DEV-3, F17). Conflicts 4 and 9 were followed as stated. No new conflicts found.

### Step 0: run it

No build step (single Python file, no `main` yet). Test run:

```
$ python3 -m unittest discover tests
.........................
----------------------------------------------------------------------
Ran 25 tests in 0.244s

OK
```

Python 3.13.18. Python 3.10 and macOS were not run (STACK-2 / TEST-9 / F15 are unverified here; RFC-005's job). `git status` clean after the run.

Criterion coverage (does a test fail if the behavior regresses?). I checked by reading each assertion against the code:

| Crit | Test | Would fail on regression? |
|---|---|---|
| 1 | `test_resolve_path` (changes env between calls, so a cache fails it) | yes |
| 2 | `test_names_defined_once` (ast, exact list of two hits) | yes |
| 3 | `test_bad_locations`, both functions, asserts exit code, path in message, no dir created; `test_dangling_symlink` | yes |
| 4 | `test_missing_file_is_empty_and_creates_nothing` | yes |
| 5 | round trip, exact keys, umask 022/077 | yes |
| 6 | 19 subtests, quoted key, startswith path, JSONDecodeError text, bytes unchanged | yes |
| 7 | `test_fixture` literal dict + id 5 | yes |
| 8 | `test_ids`, `test_remove_all_then_add`, `test_missing_id`, `test_clear_done` | yes (one gap, see N4) |
| 9 | real subprocess at 3 points with/without previous file; injected OSError and KeyError | yes; uses `S_ISDIR(fstat)` as required |
| 10 | listing before/after, stray file survives load and save | yes |
| 11 | absolute, relative, chain symlinks | yes |
| 12 | order recorded; dir fsync OSError, `os.open` failure, other exception | yes |
| 13 | bad stores rejected, bytes and listing unchanged, invalid store reported before missing dir | yes |
| 14, 15 | error classes; `temp_env` restore; stdlib-only ast scan | yes |

All 15 criteria have a test. All planned TEST-STRATEGY.md rows for RFC-001 exist (the strategy marks them "proposed"; they are now implemented). No planned test is missing.

### 1. RFC adherence -- PASS
- Every criterion is met (above). Interfaces match the RFC signatures: `TdError(message, exit_code=1)`, `UsageError`, `resolve_path`, `load_store`, `save_store`, `add_task`, `find_task`, `remove_task`, `clear_done`. Check order in `load_store` and `save_store` matches (parent check, then missing file, then validate; validate store, then directory).
- Implementation Notes deviations: (1) `discover tests` needed, not bare `discover`: follows the RFC's no-`__init__.py` rule; reasoning holds, and later RFCs/TEST-STRATEGY should say `discover tests`. (2) ast scan for stdlib-only: reasoning holds. (3) no shebang: correct, RFC-002 adds it. (4) `.gitignore` added: harmless, justified by the `SourceFileLoader` `__pycache__`. (5) message wording: allowed by the RFC. All recorded; none is a defect.
- No extra features. No lock added.

### 2. Rules compliance -- PASS
STACK-1/4 (stdlib only, verified by test), NAME-1, NAME-3 (constants once, no other literals; docstrings do not spell them), DATA-1 to DATA-7, SAFE-1 (one writer; the only `os.replace` is in `save_store`), SAFE-2 (only `OSError` skipped, `os.close` in `finally`), SAFE-4 (`realpath`), SAFE-5 (`finally` removes the temp file), SAFE-7 (nothing deletes the data file), SEC-3 (mode 0o666 with umask, no chmod), DEV-1 (no TODO or stubs), DEV-2 (assumption comments present), DEV-4 (public functions have docstrings).

### 3. Security -- PASS
No shell, eval or pickle (SEC-2). Temp file uses `O_EXCL` with a uuid name, so no clobbering or predictable-name attack. Data parsed only with `json`. No sensitive data in messages beyond the path the user supplied.

### 4. Performance -- N/A beyond one check, PASS
No commands yet. One read, one write per call (PERF-1). The task-id check in `_validate` uses a set, so it is linear.

### 5. Maintainability -- PASS
Single file, short functions, tests map to criteria by comment. No dead code or unused imports (`uuid`, `json`, `os`, `pathlib` all used).

### Blocking issues

None.

### Non-blocking issues

- **N1 (SAFE-3, OUT-7): deeply nested JSON escapes as `RecursionError`.** `load_store` only catches `ValueError` from `json.loads`. A corrupt file such as 200000 `[` characters raises `RecursionError` (reproduced), which is not a `TdError`, so the message does not name the file path as SAFE-3 and F4 require; at best `main` reports it as an unexpected error. The file is still not modified. Fix: also catch `RecursionError` in `load_store` and raise `TdError(f"{path}: invalid JSON: nesting too deep")`, plus a criterion 6 subtest. Reachable only by a hand-damaged file, so not blocking.
- **N2: duplicate keys in a JSON object are accepted silently** (`{"version":1,"version":1,...}` loads; the last value wins). Not covered by the RFC's corrupt list. Low value; mention for a future `object_pairs_hook`.
- **N3: `save_store` with a non-serializable or oversized value** (for example `next_id` of 5000 digits) raises a raw `ValueError` from `json.dumps` after validation passes. Unreachable from `load_store` (which rejects it) and from `add_task`; ignore unless a later RFC builds stores from outside input.
- **N4: test gap on criterion 8.** "After removing every task, `add_task` returns exactly the store's `next_id`" is tested only with `next_id` 3 derived from the helper; it does not try a store whose `next_id` is far above its highest id (the fixture case). `test_fixture` covers add on such a store, so the behavior is guarded, just not after removing all tasks.
- **N5: unverified platforms.** Python 3.10 floor (STACK-2), macOS (F15) and real power loss are not run; Implementation Notes say so. Tracked by RFC-005 and TEST-STRATEGY.md.
- **N6: the Implementation Notes' Plan was never confirmed by a user** (nobody was available). The assumptions in it are the RFC's own and unchanged.

### Summary

The implementation satisfies all 15 acceptance criteria with tests that would catch regressions, follows RULES.md, and records its deviations. The only real weakness is the unhandled `RecursionError` on a pathological corrupt file (N1). Merge-ready.

### FEATURES.md

FEATURES.md has no Status column, so nothing to update there.
