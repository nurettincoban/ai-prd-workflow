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

## Round 2 -- 2026-11-15

**Overall verdict: FAIL on two blocking issues (one broken rule, one unaccepted High conflict). Overall risk: Medium. Status set: Changes requested.**

Re-review under the updated review-rfc instructions, judged against Round 1. Reviewer context: fresh session, did not write the code; Status was Reviewed and was treated as acceptable for this purpose. The Files changed list in Implementation Notes (`td`, `tests/helpers.py`, `tests/test_storage.py`, `tests/fixtures/v1.json`, `.gitignore`) was the starting point; `td` has since grown by RFC-002 to RFC-004 and I read only the RFC-001 parts of it. Product type (PRD.md): CLI; same applied and skipped checks as Round 1. No Size section was found in PRD.md and the project is plainly Small, so no section below is padded.

Why the verdict changed: Round 1 called N1 (RecursionError on a deeply nested file) non-blocking. The updated instructions make a broken rule blocking however small the fix, and N1 breaks SAFE-3. They also make an open High conflict that touches the RFC, and that the user has not accepted in writing, blocking.

### Open conflicts (RFCS.md)

Conflict 1 (High): PRD G2 "never lose tasks" against F17 / DEV-3 (no lock). It touches this RFC directly: RFC-001 is where the read-modify-write is built without a lock. Searched PRD.md, PRD-REVIEW.md, FEATURES.md, RULES.md and WORKFLOW-STATUS.md: no written user acceptance exists, and WORKFLOW-STATUS.md records it as still needing a human decision. The code correctly follows the RFC (no lock), but the review cannot certify code that breaks a PRD goal on the RFC's say-so. **Blocking (B1).** Conflicts 4 and 9 followed as stated. No new conflicts found.

### Step 0: run it

No build step (single Python file). Test run, Python 3.13.18:

```
$ python3 -m unittest discover tests
Ran 66 tests in 2.913s
OK
```

`git status` clean after the run. Python 3.10 and macOS were not run by me (RFC-005's job; WORKFLOW-STATUS.md records Linux 3.10 to 3.13 runs by the implementer).

Break-it results, each run against the whole suite, file restored after each (diff against the original is empty):

| Break | Caught? |
|---|---|
| temp-file fsync removed | yes (8 failures) |
| `os.replace` skipped | yes |
| directory fsync removed | yes |
| directory fsync swallows every exception, not only OSError | yes |
| `save_store` validation removed | yes |
| `remove_task` lowers `next_id` | yes |
| `add_task` computes the id from the list | yes |
| `next_id <= id` check changed to `<` | yes |
| temp-file cleanup in `finally` disabled | yes |
| `realpath` replaced by `abspath` (symlink replaced) | yes |
| `bool` accepted as an integer | yes |
| parent-directory check in `load_store` removed | yes |
| `clear_done` removes everything | yes |
| `load_store` creates a missing file | yes |
| OSError on save no longer converted to TdError | yes |
| `remove_task` leaves the task | yes |
| `find_task` message changed | yes |
| version `>= 1` accepted | yes |
| extra top-level key accepted | yes |
| expanduser dropped | yes |
| mode forced to 0600 | yes |
| `task["id"] < 1` loosened to `< 0` (id 0 accepted) | **no** |
| `O_EXCL` dropped from the temp-file open | **no** |
| write encoding changed to ascii | no, but equivalent: `json.dumps` output is ASCII, so nothing differs today |

Criterion 6 lists no id of 0 or below, although the RFC's Validation section calls it corrupt; no test covers that behavior, so it is a coverage gap (F1 below), not a test that passes while the behavior it covers is broken. All 15 criteria still have a test that fails when their behavior breaks, except for that gap.

Used as the user: with `TD_FILE` in a temp path, `td`, `td add`, `td done`, `td rm`, `td add`, `td list` worked, ids were not reused (next_id 4 after removing id 2), the file is valid JSON, `td --help` is readable. Corrupt-file cases:

- 200000 `[` characters in the data file: `td list` prints `td: unexpected error: RecursionError: maximum recursion depth exceeded while decoding a JSON array from a unicode string` and exits 1. File unchanged. **The message does not name the file path.** (B2)
- 5000-digit `next_id`: `td: <path>: invalid JSON: Exceeds the limit (4300 digits) ...` exit 1, file named. Acceptable (the wording is odd but SAFE-3 is met).
- Duplicate `"version"` keys: loaded as valid (exit 0). Not in the RFC's corrupt list (F2 below).

### 1. RFC adherence: PASS
All 15 criteria are met and tested; interfaces match the RFC. Deviations in Implementation Notes are recorded and their reasoning holds (Round 1). One stale line: the Plan says no `reviews/REVIEW-RFC-001.md` exists; it does now (harmless).

### 2. Rules compliance: FAIL
SAFE-3 ("every command exits non-zero ... The error names the file path and the parse problem") is broken for a deeply nested file: `load_store` catches only `ValueError` around `json.loads`, so `RecursionError` escapes as a generic unexpected error without the path (B2). TEST-3 therefore has no case for it either. All other rules checked in Round 1 still hold (STACK-1/4, NAME-1/3, DATA-1 to 7, SAFE-1/2/4/5/7, SEC-3, DEV-1/2/4).

### 3. Security: PASS
No shell, eval or pickle. Temp file created with a random name; no sensitive data in messages. The nesting case cannot modify the file (verified byte for byte).

### 4. Performance: N/A for this RFC (no commands of its own); one read and one write per call, ids checked with a set. PASS.

### 5. Maintainability: PASS
Short functions, tests map to criteria. Test gaps are in F1 and F3.

### Blocking issues

- **B1: open High conflict 1 (G2 against no lock) touches this RFC and has no written user acceptance.** Needs the PRD owner: add a locking requirement (F17 becomes Must, new RFC) or reword G2 to "never lose tasks to a crash" and record that decision in PRD.md. No code change to RFC-001 clears this by itself; once the PRD is settled, this item is closed by a re-review that cites the decision.
- **B2: SAFE-3 broken by deeply nested JSON (Round 1 N1).** Fix: catch `RecursionError` alongside `ValueError` in `load_store` and raise `TdError(f"{path}: invalid JSON: nesting too deep")`; add a criterion 6 subtest (for example 200000 `[`), asserting the message starts with the path, exit code 1, bytes unchanged. Also add the same case to the command-level corrupt-file tests (TEST-3).

### Improvement suggestions (non-blocking, added to RFCS.md Follow-ups)

- F1: add `id` 0 and negative `id` cases to criterion 6 (and `version` -1); the mutation `id < 0` passes the suite.
- F2: duplicate JSON object keys load silently (last wins); consider `object_pairs_hook` to treat them as corrupt (Round 1 N2).
- F3: `O_EXCL` on the temp file is untested; no test fails if it is dropped. Low risk because the name is a uuid.
- F4: criterion 8 test with `next_id` far above the highest id after removing every task (Round 1 N4).
- F5: `save_store` of a store with an oversized `next_id` raises a raw `ValueError` from `json.dumps` (Round 1 N3); unreachable today.
- F6: the 4300-digit integer message surfaces Python's text; wording only.

Carried from Round 1 and still open: Python 3.10 and macOS runs are RFC-005's (N5); the Plan was never user-confirmed (N6).

### Summary

The storage core is well tested: 21 of 24 deliberate breaks were caught, the three that were not are minor (F1, F3, and an equivalent mutant). It cannot be marked Reviewed because a nested-JSON file breaks SAFE-3 (small fix) and the High G2 conflict that this RFC embodies has not been accepted by the user.

### FEATURES.md

No Status column, and the RFC is not Reviewed, so nothing to update.

## Round 3 -- 2026-11-15

**Overall verdict: NEEDS WORK, one blocking issue (a test that passes when the behavior it covers is broken). Overall risk: Low. Status set: Changes requested.**

Re-review after the fix round (`c567011 /implement-rfc RFC-001 (fix round)`), judged against Rounds 1 and 2. Reviewer context: fresh session, did not write the code. Product type (PRD.md): CLI; same applied and skipped checks as before. Project is plainly Small, so no section is padded.

### Round 2 blocking issues

- **B2 (SAFE-3, nested JSON): fixed.** `load_store` catches `RecursionError` and raises `TdError("<path>: invalid JSON: nesting too deep")`. Verified by hand: 200000 `[` gives `td: <path>: invalid JSON: nesting too deep`, exit 1, file unchanged. Covered by a criterion 6 case; breaking the `except` fails 6 tests.
- **B1 (open High conflict 1, G2 against no lock): judged not blocking any more.** The conflict is marked CLOSED by CR-001, accepted by the person running the example, not by the user in IDEA.md, who has not seen it. The instructions ask for acceptance by the user in writing, so I weighed whether that counts. It does not count as a user's acceptance, and I do not treat it as one. It does not need to: the blocking rule exists so a review does not certify code that breaks the PRD because an RFC said so, and what the user wrote is G2 ("never lose tasks"). The resolution sides with G2 and changes no user decision; the rejected option (rewording G2) is the one that would have needed the user. The artifacts now agree (PRD NFR-10 and D-9, F17 Must, SAFE-8, RFC-006), and RFC-001 itself loses nothing to overlapping runs by design: it builds the atomic load and save, and the lock around them is RFC-006's criterion. Residual risk, stated plainly: if the user rejects CR-001 and wants G2 reworded, RFC-006 and SAFE-8 are retired, nothing in RFC-001 changes. Until RFC-006 is implemented the program as a whole still drops a task under overlapping runs (verified by reading `main`: no lock exists); that is RFC-006's blocking item, not this one's, and it is tracked in the follow-ups.

### Step 0: run it

No build step (single Python file). Python 3.13.18:

```
$ python3 -m unittest discover tests
Ran 74 tests in 3.740s
OK
```

`git status` clean after the run. Python 3.10 and macOS were not run by me (RFC-005's job).

Break-it results (each run against the whole suite, `td` restored byte for byte afterwards, `diff` empty):

| Break | Caught? |
|---|---|
| `object_pairs_hook` removed (duplicate keys accepted) | yes (3 failures) |
| `except RecursionError` disabled | yes (6) |
| `O_EXCL` replaced by `O_TRUNC` | yes (2) |
| `task["id"] < 1` loosened to `< 0` | yes (2) |
| temp-file fsync removed | yes (8) |
| `json.dumps` `ValueError` conversion disabled | yes (2) |
| empty file accepted as an empty store | yes (2) |
| **`store["next_id"] < 1` loosened to `< 0`** | **no** |

The one survivor is a real gap, not an equivalent mutant. Criterion 6 lists `next_id` 0 and the case `next_id 0` exists, but it uses a store with tasks 1 and 2, which the separate `next_id <= id` check rejects anyway. With the positivity check broken, `{"version":1,"next_id":0,"tasks":[]}` loads, and the next `add` would hand out id 0 (the current code rejects it: `td list` on that file exits 1 with `key 'next_id' must be a positive integer`). No test pins that. This is round 2 F1's mutation for ids, left undone for `next_id`.

Used as the user: add, add, done 1, rm 2, add, list gave `1 [x] a` and `3 [ ] c`; listing and file correct, id 2 not reused (`next_id` 4), `td done 9` printed `td: no task with id 9`, exit 1. Nested file and `next_id` 0 file handled as above.

### Dimensions

1. RFC adherence: **NEEDS WORK.** All 15 criteria are met and have tests, except that criterion 6's `next_id` 0 case does not exercise the check it names (blocking item below). Duplicate-key rejection is an unapproved addition recorded in the RFC's fix-round notes and in criterion 6; the reasoning holds (a silent last-wins would hide damage, G2).
2. Rules compliance: **PASS.** SAFE-3 now holds. Earlier checks (STACK-1/4, NAME-1/3, DATA-1 to 7, SAFE-1/2/4/5/7, SEC-3, DEV-1/2/4) unchanged and still hold. DEV-3 now reads without "locking" per CR-001; the code adds none, as RFC-001 should.
3. Security: **PASS.** No shell, eval or pickle; random exclusive temp name; nesting and duplicate-key files rejected without modification.
4. Performance: **N/A** for this RFC beyond one read and one write per call (PERF-1); PASS.
5. Maintainability: **PASS.** Short functions, tests map to criteria, no dead code.

### Blocking issues

- **B3: criterion 6's `next_id` 0 case does not fail when the `next_id` positivity check is broken** (`< 1` to `< 0` passes all 74 tests), so a store with an empty task list and `next_id` 0 is untested although it is listed and would make `add` issue id 0 (DATA-3, DATA-6, TEST-3). Fix: add the case `{"version":1,"next_id":0,"tasks":[]}` (and `-1` with no tasks) to criterion 6, asserting path, `'next_id'`, bytes unchanged; re-run the mutation. No code change needed.

### Improvement suggestions (non-blocking, added to RFCS.md Follow-ups)

- F6 (carried from round 2): the 4300-digit integer text is Python's own; wording only.
- F7: `td` has no lock yet, so G2 is not met for overlapping runs until RFC-006 is implemented; RFC-001's Implementation Notes "Future" line is stale (it says locking was open). Reword it when RFC-006 lands.
- F8: CR-001 was accepted by the person running the example, not the user; ask the user to confirm D-9, or reverse it as the CR describes.

Carried and still open: Python 3.10 and macOS runs are RFC-005's; the Plan was never user-confirmed.

### Summary

The fix round closed B2 and the five follow-ups, and 7 of 8 new deliberate breaks were caught. The conflict is judged closed on its merits, though not by the user. One small test gap (empty store with `next_id` 0) keeps it from Reviewed.

### FEATURES.md

No Status column, and the RFC is not Reviewed, so nothing to update.

## Round 4 -- 2026-11-15

**Overall verdict: PASS with non-blocking findings. Overall risk: Low. Status set: Reviewed.**

Re-review after `adb9893 /implement-rfc RFC-001 (fix round 2)`, judged against Rounds 1 to 3. Reviewer context: fresh session, did not write the code. Product type (PRD.md): CLI; same applied and skipped checks as before. Project is plainly Small, so no section is padded. The fix round changed only `tests/test_storage.py` (two criterion 6 cases), the RFC's Implementation Notes and RFCS.md; `td` is unchanged.

### Round 3 blocking issue

- **B3 (criterion 6's `next_id` 0 case did not exercise the positivity check): fixed.** `test_corrupt_inputs` now has `{"version":1,"next_id":0,"tasks":[]}` and the same with `-1`. With no tasks the `next_id <= id` check cannot fire, so only the positivity check rejects them. I re-ran the mutation myself: `store["next_id"] < 1` loosened to `< 0` now fails 2 tests (it passed all 74 in round 3).

### Open conflicts (RFCS.md)

Conflict 1 is marked CLOSED by CR-001 (lock, built by RFC-006), accepted by the person running the example, not by the user in IDEA.md. I read `changes/CHANGE-REQUEST-001.md` and Round 3's judgment and agree with it, on its reasoning rather than on the acceptance. The rule exists so a review does not certify code that breaks the PRD because an RFC said so. Here the resolution sides with what the user wrote (G2), the other option (rewording G2) is the one that would have needed the user, and the artifacts agree (PRD NFR-10 and D-9, F17 Must, SAFE-8, RFC-006). RFC-001 builds the atomic load and save and by design no lock; the lock around them is RFC-006's criterion. It is not blocking here. Stated plainly: this is not the user's acceptance, and until RFC-006 is implemented the program as a whole can still drop a task under overlapping runs (`td` has no lock; checked by reading `main`). If the user reverses D-9, nothing in RFC-001 changes. Tracked in follow-ups F7 and F8. Conflicts 4 and 9 followed as stated. No new conflicts found.

### Step 0: run it

No build step (single Python file). Python 3.13.18:

```
$ python3 -m unittest discover tests
..........................................................................
Ran 74 tests in 3.478s

OK
```

`git status` clean after the run apart from `cold-reads/`, which belongs to another agent. Python 3.10 and macOS were not run (RFC-005's job).

Break-it results (each run against the whole suite; `td` restored byte for byte afterwards, `cmp` clean):

| Break | Caught? |
|---|---|
| `next_id < 1` loosened to `< 0` (round 3 survivor) | yes (2) |
| `next_id <= id` changed to `<` | yes (2) |
| `task["id"] < 1` loosened to `< 0` | yes (2) |
| `version != 1` check dropped | yes (8) |
| duplicate task id check off | yes (3) |
| `bool` accepted as an integer | yes (3) |
| `except RecursionError` disabled | yes (6) |
| duplicate-key hook removed | yes (3) |
| `O_EXCL` replaced by `O_TRUNC` | yes (2) |
| extra top-level key accepted | yes (2) |
| `next_id` type check dropped | yes (5) |
| temp-file fsync removed | yes (8) |
| directory fsync removed | yes (7) |
| `os.replace` skipped | yes (39) |
| `remove_task` lowers `next_id` | yes (8) |
| `add_task` stops incrementing `next_id` | yes (12) |
| `realpath` replaced by `abspath` | yes (5) |
| `clear_done` keeps nothing | yes (4) |
| parent-directory check removed | yes (3) |
| empty-file check (`text == ""`) disabled | **no**, see F9: the file is still rejected with exit 1 and the path, but with Python's `Expecting value` text instead of `empty file`. The RFC names `empty file` in Validation; criterion 6 only requires the path prefix. Wording, not a lost behavior |

19 of 20 breaks were caught; the survivor changes only message wording, so it is not a test that passes while a user-relied-on property is broken.

Used as the user (`TD_FILE` in a temp path): `add a`, `add b`, `done 1`, `rm 2`, `add c`, `list` gave `1 [x] a` and `3 [ ] c`, exit 0; `next_id` 4 in the file (id 2 not reused); `td done 9` printed `td: no task with id 9`, exit 1. A file with `next_id` 0 and no tasks: `td: <path>: key 'next_id' must be a positive integer`, exit 1. 200000 `[`: `td: <path>: invalid JSON: nesting too deep`, exit 1. The goals G2 (crash safety: kill tests pass), G4 (stderr message, exit code) hold; G2 for overlapping runs waits for RFC-006.

### Dimensions

1. RFC adherence: **PASS.** All 15 criteria are met and each has a test that fails on regression. Recorded deviations (round 1 list, duplicate-key rejection in the fix round notes) have reasoning that holds. The empty-file wording is untested (F9).
2. Rules compliance: **PASS.** SAFE-3 holds; STACK-1/4, NAME-1/3, DATA-1 to 7, SAFE-1/2/4/5/7, SEC-3, DEV-1/2/4 unchanged. DEV-3 reads without "locking" per CR-001; the code adds none, as RFC-001 should.
3. Security: **PASS.** No shell, eval or pickle; random exclusive temp name; hostile data files rejected without modification.
4. Performance: **N/A** for this RFC beyond one read and one write per call (PERF-1); PASS.
5. Maintainability: **PASS.** Short functions, tests map to criteria, no dead code.

### Blocking issues

None.

### Improvement suggestions (non-blocking, added to RFCS.md Follow-ups)

- F9 (new): no test asserts the `empty file` message; disabling the check still passes the suite because json reports the empty text as invalid JSON. Add an assertion for `empty file` to the criterion 6 case.
- F6 (carried): the 4300-digit integer text is Python's own; wording only.
- F7, F8 (carried): the RFC-001 Implementation Notes (Plan and Future lines) still describe locking as open and will be stale when RFC-006 lands; the user has not confirmed D-9.

Carried and still open: Python 3.10 and macOS runs are RFC-005's; the Plan was never user-confirmed.

### Summary

The fix round closed B3 and the mutation now fails as it should; 19 of 20 new deliberate breaks were caught and the one survivor is message wording. No blocking issue remains, so RFC-001 is Reviewed. Its Reviewed status certifies the storage core only: the program as a whole still has no lock until RFC-006, and the user has not confirmed CR-001.

### FEATURES.md

FEATURES.md has no Status column, so nothing to update.
