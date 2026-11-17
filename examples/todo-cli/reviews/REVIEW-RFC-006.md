# Review: RFC-006 Lock for concurrent runs (CR-001)

Reviewer context: fresh session, did not write the code. Commit reviewed: `e607bff /implement-rfc RFC-006`. Its changed files match the **Files changed** list in the RFC's Implementation Notes (`td`, `tests/test_lock.py`, the RFC, `RFCS.md`, and three stale "no lock" lines in RFC-001 to RFC-003).

## Round 1 -- 2026-11-16

**Overall verdict: PASS with non-blocking findings. Overall risk: Low. Status set: Reviewed.**

Product type (PRD.md): CLI. Applied: exit codes, stdout vs stderr, scripting, environment handling, cross-process behavior. Skipped beyond the PRD's own list: none. FEATURES.md has no Status column, so nothing to update there.

Open conflicts in RFCS.md: Open conflict 1 (concurrent runs against G2) is CLOSED by CR-001 and this RFC is the fix; no open High conflict touches RFC-006. One caveat stays on the record: CR-001 and D-9 were accepted by the person running the example, not by the user (follow-up F8 of RFC-001, still open); that does not block this review, because the code follows PRD.md, RULES.md SAFE-8 and the RFC as written. Predecessors RFC-001 to RFC-004 are Reviewed. RFC-005 is In progress; it is not a predecessor and this RFC does not wait for it. No new conflicts found.

### Step 0: run it

No build or typecheck step (single Python file `td`, Python 3.13.18 here).

```
$ python3 -m unittest discover tests
.......................................s.............................................
Ran 85 tests in 18.526s

OK (skipped=1)
```

The one skip is criterion 11 (the suite ran as root). **I did run criterion 11 as an unprivileged user.** I copied the project to `/tmp/proj2-nobody` (read-only for others), made it unwritable for `nobody`, and ran:

```
$ runuser -u nobody -- env PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_lock -v
test_11_unreadable_directory ... ok
(all 11 tests) Ran 11 tests in 7.527s  OK
```

So criterion 11 ran, was not skipped, and passes: a mode `0o300` data directory gives exit 1, one `td:` line containing the path, empty stdout. macOS is not available: `flock` on a directory descriptor there is unverified (RFC-005 criterion 8).

### Using it as the PRD's user

With a temp `TD_FILE`: add, done, list and bare `td` behave as before. Six `td add` runs started together with `&` all exited 0 and left 8 lines with distinct ids and no stray file in the directory (`ls -a` shows only `t.json`). While another process held `flock` on the directory, `td add late` waited and exited 1 after 10.08 seconds with one line, `td: <path>: data file is in use by another td run (waited 10 seconds)`; `td list` in that state still works. A missing parent directory gives `td: <path>: directory ... does not exist or is not a directory`, exit 1. Help output is unchanged. G2 (never lose tasks) now holds for overlapping runs. This matches F17's text in FEATURES.md.

### Criteria against tests, with deliberate breaks

Every criterion 1 to 11 has a test in `tests/test_lock.py` (criterion 12 is the rest of the suite, which passes). I broke `td` on purpose, ran the tests, and restored it (the mutation copy was in `/tmp/mut`, the project's `td` was never edited; `git status` was clean before this review).

| Break | Criterion / property | Result |
|---|---|---|
| Replace the `flock` call with `pass` | no lost task, waiting | caught (23 failures) |
| On timeout, `break` and go on without the lock | timeout, no write (4) | caught (6) |
| Timeout exits 2 | exit code (4) | caught (5) |
| Print a `waiting` line to stderr in the poll loop | nothing written while waiting (2, 4) | caught (5) |
| Do not close the descriptor in `__exit__` | lock released (1) | caught (test 1 errors after the 10 second wait) |
| Load the store before taking the lock | lock before load (SAFE-8, 5, 6, 9) | caught (12) |
| `clear` removed from `MUTATING` | criteria 1, 2, 4, 6 | caught (6) |
| `done` removed from `MUTATING` | criteria 1, 2, 4, 6 | caught (11) |
| Skip the lock only when `fcntl` is None, but never skip (remove the `fcntl is None` branch) | criterion 10 | caught (1) |
| Retry an `os.open` error as "held" (run as `nobody`) | criterion 11, must not wait | caught (1; by the 10 second wait, not by message text, see F2) |
| Treat every `flock` error as "held" (`if False:` on the errno check) | RFC text, step 3 | **not caught** (85 OK) |
| Lock `dirname(path)` instead of the realpath directory | symlinked `TD_FILE` | **not caught** (85 OK; the RFC lists it as the implementer's choice, no criterion) |
| Drop `_check_parent` from `data_lock` | criterion 8 | **not caught**, and not a defect: the lock's own `os.open` error then names the same path with exit 1, and `load_store` still checks, so the observable rule holds |

The two surviving breaks are not acceptance criteria of the RFC (see F1 and F3), so they are follow-ups and not blocking.

## Dimension verdicts

1. **RFC adherence: PASS.** All 12 criteria are met by observation above. The Implementation Notes record the plan, the assumptions and three deviations; their reasoning holds (TEST-STRATEGY.md rows 1 and 9 predate the RFC's round 1 rewrite, and the RFC wins; criterion 11 skipped as root, which this review closed). No extra features. The one `main` edit (the `with data_lock(path):` around load and handler for names in `MUTATING`, lock released before output) is as specified; `load_store`, `save_store`, handlers and `COMMANDS` are unchanged.
2. **Rules compliance: PASS.** SAFE-8: one function takes the lock, stdlib only, directory not a `.lock` file, OS releases it on death, 10 second wait then exit 1 with one `td:` line, `list` takes none. ARCH-1 single file kept, DEV-4 docstring and why-comments present, no `/` or `\` in the new strings (RFC-005 criterion 9 passes in the full run). `import fcntl` is guarded; `errno` and `time` are stdlib.
3. **Security: PASS.** Nothing user-controlled reaches a shell or eval; the error text contains the path the user gave. The lock error cases fail closed (exit 1) rather than skipping the lock, as the RFC requires.
4. **Performance: PASS.** Poll every 0.05 seconds up to the limit, no threads or signals. An uncontended run adds one `open` and one `flock`. N/A beyond that (scalability skipped by the PRD).
5. **Maintainability: NEEDS WORK (non-blocking).** The code is small and readable. Gaps are in tests and notes: F1 to F5 below. The suite takes about 18 seconds, and RFC-005's nested run doubles it (recorded by the implementer as deviation 3).

**Blocking issues: none.** No unmet acceptance criterion, no broken rule, no PRD goal broken, no open High conflict, and no test that passes when the behavior it covers (as an RFC criterion) is broken.

## Follow-ups (also added to RFCS.md)

- **F1 (test gap):** no test makes `flock` itself fail with a non-"held" error, so treating every `flock` error as "held" passes. The RFC states the rule (step 3) but has no criterion for it. Add one by patching `fcntl.flock` to raise `OSError(errno.ENOLCK, ...)` and expecting exit 1 at once with one `td:` line; or add the criterion to the RFC.
- **F2 (test weak):** criterion 11's test asserts the path in the message but not "the OS error text" or that the run ends quickly. It only failed under the retry break because the 10 second wait exceeded the subprocess timeout. Assert the `strerror` text (for example `Permission denied`) and a time bound.
- **F3 (unspecified):** a symlinked `TD_FILE` locks the realpath directory; nothing tests it. If the symlink case matters, add a test (two links to one file in different directories must still take turns); otherwise leave as the RFC's implementer's choice.
- **F4 (stale text):** RFC-004's Implementation Notes (line 47) still say "no lock"; the implementer noted this and left it. Reword it as was done for RFC-001 to RFC-003. TEST-STRATEGY.md rows 1, 9 and 11 are also behind the RFC (the `ast` scan and recording wrappers were replaced by behavioral tests; criteria are numbered 1 to 12 now) and its totals count 11 criteria for RFC-006; run `/test-strategy` again or edit.
- **F5 (note):** test 2 does not assert that the waiting run wrote nothing while waiting (criterion 2 says so); the stderr-line mutation was still caught by test 4, but only because that test counts lines. Read the pipes after the half second, or assert `err == ""` after release.
- **F6 (note, unverified):** `flock` on a directory on macOS, and any network filesystem, are untested (RFC-005 criterion 8; PRD D-6). The default data file lives in the user's home directory, so every `td` run on the default file shares one lock on the home directory; harmless unless another tool locks that directory with `flock`.
