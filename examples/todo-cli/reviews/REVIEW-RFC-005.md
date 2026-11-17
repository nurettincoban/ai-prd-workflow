# Review: RFC-005 Release checks

Reviewer context: fresh session, did not write the code or the tests. Commit reviewed: `a5b95d2 /implement-rfc RFC-005 (rerun)` (the first run is earlier; the rerun changed only the RFC's notes and RFCS.md, so the code under review is `tests/test_release.py`, the one file the RFC's **Files changed** list names, plus an unchanged `td`).

## Round 1 -- 2026-11-16

**Overall verdict: PASS with non-blocking findings. Overall risk: Low. Status set: Reviewed.** Criterion 8 (macOS run) is not met and cannot be met here; see the decision below.

Product type (PRD.md): CLI. Applied: install, exit codes, stdout vs stderr, scripting, cross-platform paths, speed. Skipped beyond the PRD's own list: none. FEATURES.md has no Status column, so nothing to update there.

Open conflicts in RFCS.md: Open conflict 1 is CLOSED. Conflicts 6, 7 and 8 touch RFC-005 (stricter import ban, separator scan, Features line understating criteria 4); all are notes or assumptions, none is a High conflict, none blocks. No new conflict found. Predecessors RFC-001, RFC-002, RFC-003 are Reviewed; RFC-006 is Reviewed and is not a predecessor.

### Step 0: run it

No build or typecheck step (single Python file). Suite run once per interpreter, with a directory holding a `python3` symlink first on PATH so the suite and the installed copy's `#!/usr/bin/env python3` use that interpreter:

```
Python 3.13 (default)  Ran 85 tests in 18.016s   OK (skipped=1)
Python 3.10.20         Ran 85 tests in 18.949s   OK (skipped=1)
Python 3.13 (symlink)  Ran 85 tests in 17.939s   OK (skipped=1)
```

I also ran 3.11 and 3.12 (the Implementation Notes record them; both passed, same count). The one skip is RFC-006's `test_11_unreadable_directory` (running as root), not an RFC-005 check. No `~/.td.json` exists afterwards. Linux only: no macOS here, so **macOS is unverified**.

### Acceptance criteria against tests, with deliberate breaks

Each break was made in a throwaway copy of the project (`scratchpad/m_*`); the real `td` and tests were never edited. "Caught" means a test failed in the full run.

| Break | Criterion | Result |
|---|---|---|
| `import yaml` added to `td` | 1 | caught (`test_1_imports_are_stdlib`; also a RFC-001 test) |
| `import socket` added | 2 | caught (`test_2`) |
| `os.system("true")` added | 2 | caught (`test_2`) |
| Shebang line deleted | 3, F14 | caught (`test_3`, `test_4`, `test_5` error; also `test_c1_shebang`) |
| `add` allocates `max(id)+1` instead of `next_id` | 4 (and RFC-001/003 id rules) | caught by the id-reuse tests; fixture `test_4` does not fail on this one (fixture `next_id` 5 equals max+1), see F3 |
| `list` prints in descending order | 4 | caught (`test_4_fixture_check` among 12 failures) |
| 1.2 second sleep in `save_store` (via `__import__`) | 5 | caught (`test_5`; `test_2` also fails, as designed) |
| Same sleep with a plain `import time` | 5 | caught (`test_5_speed_check`) |
| `except* ValueError` added to `td` | 7 | caught (`test_7_syntax_floor`) |
| `import tomllib` added, run on 3.13 | 1, 7 | **not caught** (85 OK): `tomllib` is in `sys.stdlib_module_names` on 3.13 and the parser accepts the import. This is what the RFC says (criterion 7 is partial) |
| Same `import tomllib`, run on 3.10 | 8 | caught (import fails, suite red). Only the 3.10 run guards the floor |
| `and/or` added to a help string | 9 | caught (`test_9_no_path_separators`) |
| `os.sep` used in `td` | 9 | caught (`test_9`) |
| A new test that calls `main(["add","leak"])` with `TD_FILE` unset | 6 | caught (`test_6_nested_suite_run`; the leaked `.td.json` in the temp `HOME` fails it) |

Properties a user relies on that this RFC owns: the file works as installed (3), a v1 file is read and its tasks survive an add (4), no delay on thousands of tasks (5), no real data file touched by tests (6). Each has a break that fails a test. Data-loss and exit-code properties belong to RFC-001 to RFC-003 and their reviews.

### Using the product

I copied `td` alone to a directory on `PATH` and ran it as `td`: `--help` (lists the five commands with help text), `add` (with non-ASCII text), `done`, `list`, `rm`, `clear`, bare `td` (lists), `done 9` (`td: no task with id 9`, exit 1), `add` with no text (`td: task text is empty`, exit 2), a file with `version` 2 (exit 1, `td:` line with the path, file unchanged), and a file missing a key (exit 1, names the key). Messages are one line and name the path. At 5,000 tasks, `list` takes about 0.07 s and `add`, `done`, `rm` about 0.05 s, so the 1 second budget has roughly a 15x margin and the speed check is not flaky on this machine. The goals this RFC serves (F13 to F16: nothing to install, one file, Linux and macOS, local and fast) hold on Linux.

## Dimension verdicts

1. **RFC adherence: PASS.** Criteria 1 to 7 and 9 are met and tested; criterion 8 is covered on Linux for 3.10, 3.11, 3.12 and 3.13 (I reproduced 3.10 and 3.13) and not for macOS. No extra features; `td` was not changed. The Implementation Notes record no deviation and one interpretation (the install directory holds only `td`), which is sound.
2. **Rules compliance: PASS.** STACK-1 to STACK-4, ARCH-1, SEC-1, SEC-2, PERF-2, TEST-8 and TEST-9 are each checked by a test or by the recorded runs. The test file uses `unittest` and the standard library only. TEST-8 holds: nested `HOME`, `TD_FILE` unset and the leak break above.
3. **Security: PASS.** The scans in criteria 1 and 2 ban network, process, eval and dynamic-import names. They are static and can be evaded by building a name at run time (F1); the RFC says so.
4. **Performance: PASS.** Criterion 5 measures whole-process time with a fresh copy per run and asserts exit 0.
5. **Maintainability: NEEDS WORK (non-blocking).** The module is readable and each test names its criterion. Gaps are F1 to F4 below.

**Blocking issues: none.** No unmet criterion other than the one decided below, no broken rule, no PRD goal broken, no open High conflict, and no test that passed when the behavior it covers was broken (the `tomllib` case is a documented limit of criterion 7, and the 3.10 run catches it).

**Decision on criterion 8 (macOS).** The criterion itself says "a release is not called done until all four are recorded, but the automated criteria above do not wait for it", and RFCS.md `## Release checklist` says such checks "do not block an RFC's Status". I followed both and did not treat the missing macOS run as blocking. It stays as item 1 of the release checklist, still unchecked: the release is not done, and nothing here says the suite passes on macOS. This is an assumption by the reviewer; the alternative is Changes requested until someone runs macOS.

## Follow-ups (also added to RFCS.md)

- **F1 (limit, note):** the criterion 2 scan is evaded by a computed name (`getattr(os, "sys" + "tem")`; I confirmed a concatenated name passes the scan). It is a regression guard, not a sandbox, as the RFC allows; nothing to change unless the ban is meant to be strict.
- **F2 (false green):** if the environment variable `TD_RELEASE_NESTED` is set in a developer's shell, criteria 5 and 6 skip silently and the suite still reports OK (a skip count of 1 becomes 3, which nobody reads). Consider failing if it is set in the top-level run, or using a name unlikely to be set by accident and printing it.
- **F3 (test gap):** the fixture's `next_id` (5) equals its highest id plus one, so the fixture check cannot tell whether `add` reads the stored `next_id`. Use a fixture with a gap (for example `next_id` 7) or add a case; the id-reuse tests in RFC-001 and RFC-003 cover the behavior today, so this is a regression-guard gap only. Changing the fixture changes RFC-001 criterion 7 as well.
- **F4 (cost):** the nested run doubles the suite's time (about 18 s total) and the one skipped test shows as a skip. Fine today; revisit if the suite grows.
- **F5 (release, still open):** macOS run not done (release checklist item 1). Also on that run: `flock` on a directory (RFC-006 F6) and a newer-than-3.10 library call that no scan catches.
